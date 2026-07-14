import base64
import asyncio
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import socket
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote, urljoin, urlparse

import httpx
from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parent


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file(ROOT / ".env")
DATA_DIR = Path(os.getenv("DATA_DIR") or (ROOT / "data"))
STORAGE_DIR = Path(os.getenv("STORAGE_DIR") or (ROOT / "storage"))
DB_PATH = DATA_DIR / "app.db"
STATIC_DIR = ROOT / "static"
FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#101827"/>
  <circle cx="32" cy="32" r="18" fill="none" stroke="#ffffff" stroke-width="6"/>
  <path d="M16 47 28 28l9 13 6-8 7 14z" fill="#ffffff"/>
</svg>"""

SESSION_COOKIE = "canvas_saas_session"
SESSION_MAX_AGE = 30 * 24 * 60 * 60
IMAGE_UPLOAD_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
VIDEO_UPLOAD_EXTENSIONS = {".mp4", ".webm", ".mov", ".mpeg", ".mpg"}
UPLOAD_MIME_SUFFIXES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/mpeg": ".mpeg",
}
AUTH_RATE_ATTEMPTS: Dict[str, list[float]] = {}
WORKER_ID = uuid.uuid4().hex
TASK_QUEUE_EVENT: Optional[asyncio.Event] = None
PROVIDER_PREFIXES = {
    "llm": {"国禾API": "LLM", "OpenAI兼容": "OPENAI_LLM", "自定义": "CUSTOM_LLM"},
    "image": {"国禾API": "IMAGE", "OpenAI兼容": "OPENAI_IMAGE", "自定义": "CUSTOM_IMAGE"},
    "video": {"灵境API": "VIDEO", "火山引擎": "VOLCANO_VIDEO", "自定义": "CUSTOM_VIDEO"},
}
DEFAULT_PROVIDERS = {"llm": "国禾API", "image": "国禾API", "video": "灵境API"}


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def now_ms() -> int:
    return int(time.time() * 1000)


def configure_paths(data_dir: str, storage_dir: str) -> None:
    global DATA_DIR, STORAGE_DIR, DB_PATH
    DATA_DIR = Path(data_dir)
    STORAGE_DIR = Path(storage_dir)
    DB_PATH = DATA_DIR / "app.db"


def env_flag(name: str, default: str = "") -> bool:
    return str(os.getenv(name) or default).strip().lower() in {"1", "true", "yes", "on"}


def production_mode() -> bool:
    env_name = str(os.getenv("APP_ENV") or os.getenv("ENV") or "").strip().lower()
    return env_name in {"prod", "production"} or env_flag("CANVAS_PRODUCTION", "0")


def int_env(name: str, default: int) -> int:
    try:
        return int(float(str(os.getenv(name) or default).strip()))
    except Exception:
        return default


def float_env(name: str, default: float) -> float:
    try:
        return float(str(os.getenv(name) or default).strip())
    except Exception:
        return default


def provider_prefix(kind: str, provider: str = "") -> tuple[str, str]:
    normalized_kind = str(kind or "").strip().lower()
    providers = PROVIDER_PREFIXES.get(normalized_kind) or {}
    selected = str(provider or "").strip() or DEFAULT_PROVIDERS.get(normalized_kind, "")
    prefix = providers.get(selected)
    if not prefix:
        raise RuntimeError(f"不支持的{normalized_kind}供应商：{selected or '未指定'}")
    return selected, prefix


def resolve_provider_config(kind: str, provider: str = "") -> Dict[str, Any]:
    normalized_kind = str(kind or "").strip().lower()
    selected, prefix = provider_prefix(normalized_kind, provider)
    api_key = str(os.getenv(f"{prefix}_API_KEY") or "").strip()
    model = str(os.getenv(f"{prefix}_MODEL") or "").strip()
    status_url_template = ""
    if normalized_kind == "llm":
        base_url = str(os.getenv(f"{prefix}_BASE_URL") or "").strip().rstrip("/")
        if prefix == "LLM" and not base_url:
            base_url = "https://api.openai.com/v1"
        url = str(os.getenv(f"{prefix}_CHAT_URL") or "").strip()
        if not url and base_url:
            url = f"{base_url}/chat/completions"
    else:
        url = str(os.getenv(f"{prefix}_GENERATION_URL") or "").strip()
        if normalized_kind == "video":
            status_url_template = str(os.getenv(f"{prefix}_STATUS_URL_TEMPLATE") or "").strip()
    return {
        "kind": normalized_kind,
        "provider": selected,
        "prefix": prefix,
        "api_key": api_key,
        "url": url,
        "model": model,
        "status_url_template": status_url_template,
        "configured": bool(api_key and url),
    }


def generation_capabilities() -> Dict[str, Any]:
    capabilities: Dict[str, Any] = {}
    for kind, providers in PROVIDER_PREFIXES.items():
        provider_states: Dict[str, Any] = {}
        for provider in providers:
            config = resolve_provider_config(kind, provider)
            provider_states[provider] = {
                "configured": config["configured"],
                "model": config["model"],
                "supports_async_status": bool(config["status_url_template"]) if kind == "video" else False,
            }
        capabilities[kind] = {
            "configured": any(item["configured"] for item in provider_states.values()),
            "providers": provider_states,
        }
    return capabilities


def invite_code() -> str:
    return str(os.getenv("INVITE_CODE") or "canvasv1").strip()


def session_secret() -> str:
    configured = str(os.getenv("SESSION_SECRET") or "").strip()
    if configured:
        return configured
    if production_mode():
        raise AppError("生产环境必须配置 SESSION_SECRET", 500)
    return str(os.getenv("INVITE_CODE") or "local-dev-session-secret")


def validate_runtime_config() -> None:
    if not production_mode():
        return
    secret = str(os.getenv("SESSION_SECRET") or "").strip()
    invite = invite_code()
    if not secret or len(secret) < 32 or secret in {"replace-with-a-long-random-secret", "local-dev-session-secret"}:
        raise AppError("生产环境必须配置至少 32 位的 SESSION_SECRET", 500)
    if not invite or len(invite) < 12 or invite in {"canvasv1", "change-me", "changeme"}:
        raise AppError("生产环境必须配置私有邀请码", 500)
    if hmac.compare_digest(secret, invite):
        raise AppError("SESSION_SECRET 不能与邀请码相同", 500)
    if env_flag("AUTO_ADMIN_FIRST_USER", "1"):
        raise AppError("生产环境必须关闭 AUTO_ADMIN_FIRST_USER 并手动初始化管理员", 500)
    if not env_flag("COOKIE_SECURE", "0"):
        raise AppError("生产环境必须设置 COOKIE_SECURE=1", 500)


def default_credits() -> int:
    return max(0, int_env("DEFAULT_CREDITS", 100))


def max_upload_bytes() -> int:
    return max(1, int_env("MAX_UPLOAD_MB", 50)) * 1024 * 1024


def max_output_bytes() -> int:
    return max(1, int_env("MAX_OUTPUT_MB", 500)) * 1024 * 1024


def max_user_storage_bytes() -> int:
    return max(1, int_env("MAX_USER_STORAGE_MB", 2048)) * 1024 * 1024


def task_cost(kind: str) -> int:
    defaults = {"llm": 1, "image": 5, "video": 40}
    return max(0, int_env(f"COST_{str(kind or '').upper()}", defaults.get(kind, 1)))


def clean_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "", str(value or ""))[:80]


def classify_upload(filename: str, content_type: str) -> tuple[str, str]:
    mime = str(content_type or "").split(";", 1)[0].strip().lower()
    suffix = Path(filename or "").suffix.lower()
    if mime in UPLOAD_MIME_SUFFIXES:
        default_suffix = UPLOAD_MIME_SUFFIXES[mime]
        kind = "image" if mime.startswith("image/") else "video"
    elif mime.startswith("image/") and suffix in IMAGE_UPLOAD_EXTENSIONS:
        default_suffix = suffix
        kind = "image"
    elif mime.startswith("video/") and suffix in VIDEO_UPLOAD_EXTENSIONS:
        default_suffix = suffix
        kind = "video"
    else:
        raise AppError("仅支持上传图片或视频文件", 415)

    allowed_suffixes = IMAGE_UPLOAD_EXTENSIONS if kind == "image" else VIDEO_UPLOAD_EXTENSIONS
    if suffix and suffix not in allowed_suffixes:
        raise AppError("文件扩展名与上传类型不匹配", 415)
    return kind, suffix or default_suffix


def validate_upload_content(kind: str, suffix: str, content: bytes) -> None:
    data = content or b""
    suffix = str(suffix or "").lower()
    if not data:
        raise AppError("上传文件为空", 415)

    image_signatures = {
        ".png": lambda value: value.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": lambda value: value.startswith(b"\xff\xd8\xff"),
        ".jpeg": lambda value: value.startswith(b"\xff\xd8\xff"),
        ".gif": lambda value: value.startswith((b"GIF87a", b"GIF89a")),
        ".webp": lambda value: len(value) >= 12 and value[:4] == b"RIFF" and value[8:12] == b"WEBP",
        ".avif": lambda value: len(value) >= 16 and value[4:8] == b"ftyp" and any(brand in value[8:32] for brand in (b"avif", b"avis")),
    }
    video_signatures = {
        ".mp4": lambda value: len(value) >= 12 and value[4:8] == b"ftyp",
        ".mov": lambda value: len(value) >= 12 and value[4:8] == b"ftyp",
        ".m4v": lambda value: len(value) >= 12 and value[4:8] == b"ftyp",
        ".webm": lambda value: value.startswith(b"\x1a\x45\xdf\xa3"),
        ".mkv": lambda value: value.startswith(b"\x1a\x45\xdf\xa3"),
        ".mpeg": lambda value: value.startswith((b"\x00\x00\x01\xba", b"\x00\x00\x01\xb3")),
        ".mpg": lambda value: value.startswith((b"\x00\x00\x01\xba", b"\x00\x00\x01\xb3")),
    }
    validators = image_signatures if kind == "image" else video_signatures
    validator = validators.get(suffix)
    if not validator or not validator(data):
        raise AppError("上传内容与文件类型不匹配", 415)


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    return dict(row) if row else None


def ensure_columns(conn: sqlite3.Connection, table: str, columns: Dict[str, str]) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                credits INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS credit_events (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                delta INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                reason TEXT NOT NULL,
                actor_id TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                deleted_at INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS canvases (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                state_json TEXT NOT NULL DEFAULT '{}',
                revision INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                project_id TEXT NOT NULL DEFAULT '',
                canvas_id TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                path TEXT NOT NULL,
                url TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'upload',
                task_id TEXT NOT NULL DEFAULT '',
                node_id TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                prompt TEXT NOT NULL,
                cost INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                canvas_id TEXT NOT NULL DEFAULT '',
                node_id TEXT NOT NULL DEFAULT '',
                options_json TEXT NOT NULL DEFAULT '{}',
                request_id TEXT NOT NULL DEFAULT '',
                attempt_count INTEGER NOT NULL DEFAULT 0,
                lease_until INTEGER NOT NULL DEFAULT 0,
                worker_id TEXT NOT NULL DEFAULT '',
                result_json TEXT NOT NULL DEFAULT '{}',
                error TEXT NOT NULL DEFAULT '',
                refunded INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workflow_templates (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                node_count INTEGER NOT NULL DEFAULT 0,
                edge_count INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )
        ensure_columns(
            conn,
            "canvases",
            {"revision": "INTEGER NOT NULL DEFAULT 1"},
        )
        ensure_columns(
            conn,
            "assets",
            {
                "source": "TEXT NOT NULL DEFAULT 'upload'",
                "task_id": "TEXT NOT NULL DEFAULT ''",
                "node_id": "TEXT NOT NULL DEFAULT ''",
            },
        )
        ensure_columns(
            conn,
            "tasks",
            {
                "canvas_id": "TEXT NOT NULL DEFAULT ''",
                "node_id": "TEXT NOT NULL DEFAULT ''",
                "options_json": "TEXT NOT NULL DEFAULT '{}'",
                "request_id": "TEXT NOT NULL DEFAULT ''",
                "attempt_count": "INTEGER NOT NULL DEFAULT 0",
                "lease_until": "INTEGER NOT NULL DEFAULT 0",
                "worker_id": "TEXT NOT NULL DEFAULT ''",
            },
        )
    recover_interrupted_tasks()


def normalize_email(email: str) -> str:
    value = str(email or "").strip().lower()
    if len(value) > 254 or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
        raise AppError("请输入有效邮箱")
    return value


def auth_rate_key(request: Request, email: str) -> str:
    host = request.client.host if request.client else "unknown"
    try:
        normalized = normalize_email(email)
    except AppError:
        normalized = str(email or "").strip().lower()[:254]
    return f"{host}:{normalized}"


def record_auth_attempt(request: Request, email: str) -> str:
    max_attempts = max(1, int_env("AUTH_RATE_LIMIT_MAX", 8))
    window = max(1, int_env("AUTH_RATE_LIMIT_WINDOW_SECONDS", 300))
    current = time.time()
    key = auth_rate_key(request, email)
    attempts = [stamp for stamp in AUTH_RATE_ATTEMPTS.get(key, []) if current - stamp < window]
    if len(attempts) >= max_attempts:
        AUTH_RATE_ATTEMPTS[key] = attempts
        raise AppError("尝试次数过多，请稍后再试", 429)
    attempts.append(current)
    AUTH_RATE_ATTEMPTS[key] = attempts
    return key


def clear_auth_attempts(key: str) -> None:
    AUTH_RATE_ATTEMPTS.pop(key, None)


def hash_password(password: str, salt: str = "") -> str:
    if not salt:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", str(password or "").encode("utf-8"), salt.encode("utf-8"), 200_000).hex()
    return f"pbkdf2_sha256$200000${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, rounds, salt, digest = str(stored or "").split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        check = hashlib.pbkdf2_hmac("sha256", str(password or "").encode("utf-8"), salt.encode("utf-8"), int(rounds)).hex()
        return hmac.compare_digest(check, digest)
    except Exception:
        return False


def user_storage_path(user_id: str) -> str:
    user_id = clean_id(user_id)
    path = STORAGE_DIR / "users" / user_id
    for child in ("uploads", "outputs", "tasks"):
        (path / child).mkdir(parents=True, exist_ok=True)
    return str(path)


def user_storage_usage_bytes(user_id: str) -> int:
    root = Path(user_storage_path(user_id))
    total = 0
    for path in root.rglob("*"):
        if path.is_file():
            try:
                total += path.stat().st_size
            except OSError:
                continue
    return total


def ensure_user_storage_capacity(user_id: str, incoming_bytes: int) -> None:
    incoming = max(0, int(incoming_bytes or 0))
    if user_storage_usage_bytes(user_id) + incoming > max_user_storage_bytes():
        raise AppError(f"用户存储空间不足，当前上限为 {int_env('MAX_USER_STORAGE_MB', 2048)}MB", 413)


def user_storage_summary(user_id: str) -> Dict[str, Any]:
    used = user_storage_usage_bytes(user_id)
    limit = max_user_storage_bytes()
    return {
        "used_bytes": used,
        "limit_bytes": limit,
        "percent": round(min(100.0, used / limit * 100), 1),
    }


def credit_balance(user_id: str) -> int:
    with db() as conn:
        row = conn.execute("SELECT credits FROM users WHERE id = ?", (clean_id(user_id),)).fetchone()
    return int(row["credits"]) if row else 0


def adjust_credits(user_id: str, delta: int, reason: str, actor_id: str = "") -> int:
    clean = clean_id(user_id)
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT credits FROM users WHERE id = ?", (clean,)).fetchone()
        if not row:
            raise AppError("用户不存在", 404)
        balance = int(row["credits"]) + int(delta)
        if balance < 0:
            raise AppError("点数不足", 402)
        ts = now_ms()
        conn.execute("UPDATE users SET credits = ?, updated_at = ? WHERE id = ?", (balance, ts, clean))
        conn.execute(
            "INSERT INTO credit_events (id, user_id, delta, balance_after, reason, actor_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (uuid.uuid4().hex, clean, int(delta), balance, str(reason or "")[:300], clean_id(actor_id), ts),
        )
    return balance


def is_first_user(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
    return int(row["count"]) == 0


def register_user(email: str, password: str, invite: str) -> Dict[str, Any]:
    validate_runtime_config()
    if not hmac.compare_digest(str(invite or "").strip(), invite_code()):
        raise AppError("邀请码不正确", 401)
    email = normalize_email(email)
    if len(str(password or "")) < 6:
        raise AppError("密码至少 6 位")
    user_id = uuid.uuid4().hex
    ts = now_ms()
    with db() as conn:
        if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            raise AppError("邮箱已注册", 409)
        admin = 1 if (env_flag("AUTO_ADMIN_FIRST_USER", "1") and is_first_user(conn)) else 0
        conn.execute(
            "INSERT INTO users (id, email, password_hash, is_admin, credits, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, email, hash_password(password), admin, default_credits(), ts, ts),
        )
        conn.execute(
            "INSERT INTO credit_events (id, user_id, delta, balance_after, reason, actor_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (uuid.uuid4().hex, user_id, default_credits(), default_credits(), "初始点数", "", ts),
        )
    user_storage_path(user_id)
    return public_user(get_user(user_id) or {})


def create_admin_user(email: str, password: str) -> Dict[str, Any]:
    validate_runtime_config()
    email = normalize_email(email)
    if len(str(password or "")) < 6:
        raise AppError("密码至少 6 位")
    ts = now_ms()
    with db() as conn:
        existing = row_dict(conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone())
        password_hash = hash_password(password)
        if existing:
            user_id = existing["id"]
            conn.execute(
                "UPDATE users SET password_hash = ?, is_admin = 1, updated_at = ? WHERE id = ?",
                (password_hash, ts, user_id),
            )
        else:
            user_id = uuid.uuid4().hex
            credits = default_credits()
            conn.execute(
                "INSERT INTO users (id, email, password_hash, is_admin, credits, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, email, password_hash, 1, credits, ts, ts),
            )
            conn.execute(
                "INSERT INTO credit_events (id, user_id, delta, balance_after, reason, actor_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (uuid.uuid4().hex, user_id, credits, credits, "管理员初始化", "", ts),
            )
    user_storage_path(user_id)
    return public_user(get_user(user_id) or {})


def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    email = normalize_email(email)
    with db() as conn:
        user = row_dict(conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone())
    if not user or not verify_password(password, str(user.get("password_hash") or "")):
        raise AppError("账号或密码不正确", 401)
    user_storage_path(user["id"])
    return public_user(user)


def change_password(user_id: str, current_password: str, new_password: str) -> None:
    clean = clean_id(user_id)
    user = get_user(clean)
    if not user or not verify_password(current_password, str(user.get("password_hash") or "")):
        raise AppError("当前密码不正确", 401)
    if len(str(new_password or "")) < 6:
        raise AppError("新密码至少 6 位")
    if hmac.compare_digest(str(current_password or ""), str(new_password or "")):
        raise AppError("新密码不能与当前密码相同")
    with db() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (hash_password(new_password), now_ms(), clean),
        )


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    with db() as conn:
        return row_dict(conn.execute("SELECT * FROM users WHERE id = ?", (clean_id(user_id),)).fetchone())


def public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": clean_id(user.get("id")),
        "email": str(user.get("email") or ""),
        "is_admin": bool(user.get("is_admin")),
        "credits": int(user.get("credits") or 0),
        "created_at": int(user.get("created_at") or 0),
    }


def session_signature(user_id: str, issued_at: str) -> str:
    message = f"{clean_id(user_id)}.{issued_at}"
    return hmac.new(session_secret().encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def create_session_token(user_id: str) -> str:
    issued_at = str(int(time.time()))
    return f"{clean_id(user_id)}.{issued_at}.{session_signature(user_id, issued_at)}"


def user_from_session_token(token: str) -> Optional[Dict[str, Any]]:
    parts = str(token or "").split(".")
    if len(parts) != 3:
        return None
    user_id, issued_at, signature = parts
    if not clean_id(user_id) or not issued_at.isdigit():
        return None
    if int(time.time()) - int(issued_at) > SESSION_MAX_AGE:
        return None
    if not hmac.compare_digest(signature, session_signature(user_id, issued_at)):
        return None
    user = get_user(user_id)
    return public_user(user) if user else None


def create_project(user_id: str, name: str) -> Dict[str, Any]:
    project_id = uuid.uuid4().hex
    ts = now_ms()
    clean = clean_id(user_id)
    with db() as conn:
        conn.execute(
            "INSERT INTO projects (id, user_id, name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (project_id, clean, str(name or "新项目").strip()[:80] or "新项目", ts, ts),
        )
    return get_project(clean, project_id) or {}


def get_project(user_id: str, project_id: str) -> Optional[Dict[str, Any]]:
    with db() as conn:
        return row_dict(
            conn.execute(
                "SELECT * FROM projects WHERE user_id = ? AND id = ? AND deleted_at = 0",
                (clean_id(user_id), clean_id(project_id)),
            ).fetchone()
        )


def list_projects(user_id: str) -> list[Dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT p.*, (SELECT COUNT(*) FROM canvases c WHERE c.project_id = p.id) AS canvas_count FROM projects p WHERE p.user_id = ? AND p.deleted_at = 0 ORDER BY p.updated_at DESC",
            (clean_id(user_id),),
        ).fetchall()
    return [dict(row) for row in rows]


def create_canvas(user_id: str, project_id: str, name: str) -> Dict[str, Any]:
    clean = clean_id(user_id)
    if not get_project(clean, project_id):
        raise AppError("项目不存在", 404)
    canvas_id = uuid.uuid4().hex
    ts = now_ms()
    state = {"nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "scale": 1}}
    with db() as conn:
        conn.execute(
            "INSERT INTO canvases (id, user_id, project_id, name, state_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (canvas_id, clean, clean_id(project_id), str(name or "新画布").strip()[:80] or "新画布", json.dumps(state, ensure_ascii=False), ts, ts),
        )
    return get_canvas(clean, canvas_id) or {}


def get_canvas(user_id: str, canvas_id: str) -> Optional[Dict[str, Any]]:
    with db() as conn:
        row = row_dict(
            conn.execute(
                "SELECT * FROM canvases WHERE user_id = ? AND id = ?",
                (clean_id(user_id), clean_id(canvas_id)),
            ).fetchone()
        )
    if not row:
        return None
    try:
        row["state"] = json.loads(row.get("state_json") or "{}")
    except Exception:
        row["state"] = {}
    row.pop("state_json", None)
    return row


def list_canvases(user_id: str, project_id: str) -> list[Dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT id, user_id, project_id, name, created_at, updated_at FROM canvases WHERE user_id = ? AND project_id = ? ORDER BY updated_at DESC",
            (clean_id(user_id), clean_id(project_id)),
        ).fetchall()
    return [dict(row) for row in rows]


def save_canvas_state(
    user_id: str,
    canvas_id: str,
    state: Dict[str, Any],
    name: str = "",
    expected_revision: Optional[int] = None,
) -> Dict[str, Any]:
    current = get_canvas(user_id, canvas_id)
    if not current:
        raise AppError("画布不存在", 404)
    current_revision = int(current.get("revision") or 1)
    if expected_revision is not None and int(expected_revision) != current_revision:
        raise AppError("画布已在其他页面更新，请刷新后重试", 409)
    ts = now_ms()
    payload = json.dumps(state or {}, ensure_ascii=False)
    with db() as conn:
        if name:
            cursor = conn.execute(
                "UPDATE canvases SET state_json = ?, name = ?, revision = revision + 1, updated_at = ? "
                "WHERE user_id = ? AND id = ? AND revision = ?",
                (payload, str(name).strip()[:80], ts, clean_id(user_id), clean_id(canvas_id), current_revision),
            )
        else:
            cursor = conn.execute(
                "UPDATE canvases SET state_json = ?, revision = revision + 1, updated_at = ? "
                "WHERE user_id = ? AND id = ? AND revision = ?",
                (payload, ts, clean_id(user_id), clean_id(canvas_id), current_revision),
            )
        if cursor.rowcount != 1:
            raise AppError("画布已在其他页面更新，请刷新后重试", 409)
    return get_canvas(user_id, canvas_id) or {}


def normalize_workflow_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise AppError("工作流 payload 必须是对象")
    nodes = payload.get("nodes") or []
    edges = payload.get("edges") or []
    if not isinstance(nodes, list) or not nodes:
        raise AppError("工作流节点不能为空")
    if not isinstance(edges, list):
        raise AppError("工作流连线必须是数组")
    if len(nodes) > 500 or len(edges) > 1200:
        raise AppError("工作流过大，请拆分后保存")
    clean_payload = dict(payload)
    clean_payload["nodes"] = nodes
    clean_payload["edges"] = edges
    encoded = json.dumps(clean_payload, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > 8 * 1024 * 1024:
        raise AppError("工作流 JSON 体积过大")
    return clean_payload


def workflow_template_from_row(row: sqlite3.Row, include_payload: bool = False) -> Dict[str, Any]:
    item = dict(row)
    payload_json = item.pop("payload_json", "{}")
    if include_payload:
        try:
            item["payload"] = json.loads(payload_json or "{}")
        except Exception:
            item["payload"] = {}
    return item


def create_workflow_template(user_id: str, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    clean_payload = normalize_workflow_payload(payload)
    nodes = clean_payload.get("nodes") or []
    edges = clean_payload.get("edges") or []
    template_id = uuid.uuid4().hex
    template_name = str(name or "").strip()[:100] or "工作流模板"
    ts = now_ms()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO workflow_templates
            (id, user_id, name, payload_json, node_count, edge_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                template_id,
                clean_id(user_id),
                template_name,
                json.dumps(clean_payload, ensure_ascii=False),
                len(nodes),
                len(edges),
                ts,
                ts,
            ),
        )
    return get_workflow_template(user_id, template_id) or {}


def list_workflow_templates(user_id: str) -> list[Dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, name, payload_json, node_count, edge_count, created_at, updated_at
            FROM workflow_templates
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT 100
            """,
            (clean_id(user_id),),
        ).fetchall()
    return [workflow_template_from_row(row) for row in rows]


def get_workflow_template(user_id: str, template_id: str) -> Optional[Dict[str, Any]]:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM workflow_templates WHERE user_id = ? AND id = ?",
            (clean_id(user_id), clean_id(template_id)),
        ).fetchone()
    return workflow_template_from_row(row, include_payload=True) if row else None


def delete_workflow_template(user_id: str, template_id: str) -> bool:
    with db() as conn:
        cursor = conn.execute(
            "DELETE FROM workflow_templates WHERE user_id = ? AND id = ?",
            (clean_id(user_id), clean_id(template_id)),
        )
    return cursor.rowcount > 0


def option_text(value: Any, limit: int = 120) -> str:
    return str(value or "").strip()[:limit]


def option_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(float(value))
    except Exception:
        parsed = default
    return max(minimum, min(maximum, parsed))


def option_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def normalize_task_options(kind: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    source = options if isinstance(options, dict) else {}
    normalized: Dict[str, Any] = {}
    provider = option_text(source.get("provider"))
    model = option_text(source.get("model"))
    if provider:
        normalized["provider"] = provider
    if model:
        normalized["model"] = model
    if kind == "llm":
        system_prompt = option_text(source.get("system_prompt"), 4000)
        if system_prompt:
            normalized["system_prompt"] = system_prompt
    elif kind == "image":
        ratio = option_text(source.get("ratio")) or "1:1"
        image_size = option_text(source.get("image_size")) or "自适应"
        normalized.update(
            {
                "ratio": ratio if ratio in {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"} else "1:1",
                "image_size": image_size if image_size in {"自适应", "auto", "1K", "2K", "4K"} else "自适应",
                "image_scale": option_int(source.get("image_scale"), 1, 1, 4),
                "count": option_int(source.get("count"), 1, 1, 4),
            }
        )
    elif kind == "video":
        mode = option_text(source.get("mode")) or "text_to_video"
        aspect_ratio = option_text(source.get("aspect_ratio")) or "16:9"
        resolution = option_text(source.get("resolution")) or "Auto"
        output_fps = option_int(source.get("output_fps"), 0, 0, 60)
        normalized.update(
            {
                "mode": mode if mode in {"text_to_video", "image_to_video", "video_to_video"} else "text_to_video",
                "duration": option_int(source.get("duration"), 5, 1, 30),
                "aspect_ratio": aspect_ratio if aspect_ratio in {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"} else "16:9",
                "resolution": resolution if resolution in {"Auto", "auto", "720p", "1080p"} else "Auto",
                "output_fps": output_fps if output_fps in {0, 24, 25, 30, 50, 60} else 0,
                "enhance_prompt": option_bool(source.get("enhance_prompt")),
                "fixed_camera": option_bool(source.get("fixed_camera")),
                "generate_audio": option_bool(source.get("generate_audio")),
                "first_last_frame": option_bool(source.get("first_last_frame")),
            }
        )
    return normalized


def task_from_row(row: Any) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    item = dict(row)
    for source_key, target_key in (("result_json", "result"), ("options_json", "options")):
        try:
            item[target_key] = json.loads(item.get(source_key) or "{}")
        except Exception:
            item[target_key] = {}
        item.pop(source_key, None)
    item["refunded"] = bool(item.get("refunded"))
    return item


def create_task(
    user_id: str,
    kind: str,
    prompt: str,
    cost: int,
    canvas_id: str = "",
    node_id: str = "",
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    clean = clean_id(user_id)
    kind = str(kind or "").strip().lower()
    if kind not in {"llm", "image", "video"}:
        raise AppError("不支持的任务类型")
    cost = max(0, int(cost or 0))
    if cost:
        adjust_credits(clean, -cost, f"{kind} 任务扣费")
    task_id = uuid.uuid4().hex
    request_id = uuid.uuid4().hex
    ts = now_ms()
    normalized_options = normalize_task_options(kind, options)
    with db() as conn:
        conn.execute(
            "INSERT INTO tasks (id, user_id, kind, prompt, cost, status, canvas_id, node_id, options_json, request_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                task_id,
                clean,
                kind,
                str(prompt or "")[:20000],
                cost,
                "queued",
                clean_id(canvas_id),
                clean_id(node_id),
                json.dumps(normalized_options, ensure_ascii=False),
                request_id,
                ts,
                ts,
            ),
        )
    return get_task(clean, task_id) or {}


def get_task(user_id: str, task_id: str) -> Optional[Dict[str, Any]]:
    with db() as conn:
        row = row_dict(
            conn.execute(
                "SELECT * FROM tasks WHERE user_id = ? AND id = ?",
                (clean_id(user_id), clean_id(task_id)),
            ).fetchone()
        )
    return task_from_row(row)


def list_tasks(user_id: str) -> list[Dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT 100",
            (clean_id(user_id),),
        ).fetchall()
    return [task for row in rows if (task := task_from_row(row))]


def media_kind_for_url(url: str, fallback: str = "") -> str:
    value = str(url or "").lower()
    if fallback in {"image", "video"}:
        return fallback
    if value.startswith("data:video") or re.search(r"\.(mp4|webm|mov|m4v|mkv)(\?|$)", value):
        return "video"
    return "image"


def extract_result_assets(value: Any, fallback_kind: str = "") -> list[Dict[str, str]]:
    assets: list[Dict[str, str]] = []
    seen: set[str] = set()

    def add_url(url: str, kind: str = "") -> None:
        clean_url = str(url or "").strip()
        if not clean_url or clean_url in seen:
            return
        if not re.match(r"^(https?:|data:|/api/assets/)", clean_url):
            return
        seen.add(clean_url)
        assets.append({"url": clean_url, "kind": media_kind_for_url(clean_url, kind or fallback_kind)})

    def walk(item: Any) -> None:
        if isinstance(item, str):
            add_url(item)
            return
        if isinstance(item, list):
            for child in item:
                walk(child)
            return
        if not isinstance(item, dict):
            return
        for key in ("url", "image_url", "video_url", "output_url", "download_url"):
            if isinstance(item.get(key), str):
                add_url(item[key])
        for key in ("b64_json", "base64", "image_base64"):
            if isinstance(item.get(key), str):
                add_url(f"data:image/png;base64,{item[key]}", "image")
        for child in item.values():
            walk(child)

    walk(value)
    return assets


def generated_media_suffix(kind: str, url: str = "", content_type: str = "") -> str:
    mime = str(content_type or "").split(";", 1)[0].strip().lower()
    by_mime = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/avif": ".avif",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "video/mpeg": ".mpeg",
    }
    if mime in by_mime:
        return by_mime[mime]
    suffix = Path(urlparse(str(url or "")).path).suffix.lower()
    allowed = IMAGE_UPLOAD_EXTENSIONS if kind == "image" else VIDEO_UPLOAD_EXTENSIONS
    if suffix in allowed:
        return suffix
    return ".png" if kind == "image" else ".mp4"


async def validate_generated_media_url(url: str) -> None:
    parsed = urlparse(str(url or ""))
    hostname = str(parsed.hostname or "").strip().lower()
    if parsed.scheme not in {"http", "https"} or not hostname:
        raise RuntimeError("生成结果包含无效媒体地址")
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        raise RuntimeError("不允许保存内网地址")
    try:
        addresses = [ipaddress.ip_address(hostname)]
    except ValueError:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            resolved = await asyncio.to_thread(socket.getaddrinfo, hostname, port, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise RuntimeError("无法解析生成结果地址") from exc
        addresses = []
        for entry in resolved:
            try:
                addresses.append(ipaddress.ip_address(entry[4][0]))
            except ValueError:
                continue
    if not addresses or any(not address.is_global for address in addresses):
        raise RuntimeError("不允许保存内网地址")


async def read_generated_media(url: str, kind: str) -> tuple[bytes, str]:
    source = str(url or "").strip()
    content_type = ""
    if source.startswith("data:"):
        header, separator, encoded = source.partition(",")
        if not separator or ";base64" not in header.lower():
            raise RuntimeError("生成结果包含不支持的数据 URI")
        content_type = header[5:].split(";", 1)[0]
        try:
            content = base64.b64decode(re.sub(r"\s+", "", encoded), validate=True)
        except Exception as exc:
            raise RuntimeError("生成结果的 Base64 数据无效") from exc
    elif source.startswith(("http://", "https://")):
        chunks: list[bytes] = []
        total = 0
        current_url = source
        async with httpx.AsyncClient(timeout=180, follow_redirects=False) as client:
            for _redirect in range(6):
                await validate_generated_media_url(current_url)
                async with client.stream("GET", current_url) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location", "")
                        if not location:
                            response.raise_for_status()
                        current_url = urljoin(current_url, location)
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "")
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > max_output_bytes():
                            raise RuntimeError(f"生成结果超过 {int_env('MAX_OUTPUT_MB', 500)}MB")
                        chunks.append(chunk)
                    break
            else:
                raise RuntimeError("生成结果重定向次数过多")
        content = b"".join(chunks)
    else:
        raise RuntimeError("生成结果没有可持久化的媒体地址")
    if len(content) > max_output_bytes():
        raise RuntimeError(f"生成结果超过 {int_env('MAX_OUTPUT_MB', 500)}MB")
    suffix = generated_media_suffix(kind, source, content_type)
    validate_upload_content(kind, suffix, content)
    return content, suffix


async def stream_generated_media_to_path(url: str, kind: str, temporary: Path, user_id: str) -> tuple[str, int]:
    source = str(url or "").strip()
    content_type = ""
    total = 0
    header = bytearray()
    existing_usage = user_storage_usage_bytes(user_id)

    def write_chunk(output, chunk: bytes) -> None:
        nonlocal total
        if not chunk:
            return
        total += len(chunk)
        if total > max_output_bytes():
            raise RuntimeError(f"生成结果超过 {int_env('MAX_OUTPUT_MB', 500)}MB")
        if existing_usage + total > max_user_storage_bytes():
            raise AppError(f"用户存储空间不足，当前上限为 {int_env('MAX_USER_STORAGE_MB', 2048)}MB", 413)
        if len(header) < 64:
            header.extend(chunk[: 64 - len(header)])
        output.write(chunk)

    temporary.parent.mkdir(parents=True, exist_ok=True)
    try:
        with temporary.open("wb") as output:
            if source.startswith("data:"):
                data_header, separator, encoded = source.partition(",")
                if not separator or ";base64" not in data_header.lower():
                    raise RuntimeError("生成结果包含不支持的数据 URI")
                content_type = data_header[5:].split(";", 1)[0]
                compact = re.sub(r"\s+", "", encoded)
                if len(compact) % 4:
                    raise RuntimeError("生成结果的 Base64 数据无效")
                try:
                    block_size = 4 * 4096
                    for offset in range(0, len(compact), block_size):
                        write_chunk(output, base64.b64decode(compact[offset : offset + block_size], validate=True))
                except AppError:
                    raise
                except Exception as exc:
                    raise RuntimeError("生成结果的 Base64 数据无效") from exc
            elif source.startswith(("http://", "https://")):
                current_url = source
                async with httpx.AsyncClient(timeout=180, follow_redirects=False) as client:
                    for _redirect in range(6):
                        await validate_generated_media_url(current_url)
                        async with client.stream("GET", current_url) as response:
                            if response.status_code in {301, 302, 303, 307, 308}:
                                location = response.headers.get("location", "")
                                if not location:
                                    response.raise_for_status()
                                current_url = urljoin(current_url, location)
                                continue
                            response.raise_for_status()
                            content_type = response.headers.get("content-type", "")
                            content_length = int(response.headers.get("content-length") or 0)
                            if content_length > max_output_bytes():
                                raise RuntimeError(f"生成结果超过 {int_env('MAX_OUTPUT_MB', 500)}MB")
                            if content_length and existing_usage + content_length > max_user_storage_bytes():
                                raise AppError(
                                    f"用户存储空间不足，当前上限为 {int_env('MAX_USER_STORAGE_MB', 2048)}MB",
                                    413,
                                )
                            async for chunk in response.aiter_bytes():
                                write_chunk(output, chunk)
                            source = current_url
                            break
                    else:
                        raise RuntimeError("生成结果重定向次数过多")
            else:
                raise RuntimeError("生成结果没有可持久化的媒体地址")
        suffix = generated_media_suffix(kind, source, content_type)
        validate_upload_content(kind, suffix, bytes(header))
        return suffix, total
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def sanitized_upstream_result(value: Any) -> Any:
    if isinstance(value, str):
        return "[media persisted]" if value.startswith("data:") else value
    if isinstance(value, list):
        return [sanitized_upstream_result(item) for item in value]
    if isinstance(value, dict):
        return {
            key: sanitized_upstream_result(item)
            for key, item in value.items()
            if key not in {"b64_json", "base64", "image_base64"}
        }
    return value


async def persist_generated_assets(task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    media_items = extract_result_assets(result, task.get("kind") or "")
    if not media_items:
        return result
    user_id = clean_id(task.get("user_id") or "")
    if not user_id:
        raise RuntimeError("任务缺少用户信息，无法保存生成结果")
    output_dir = Path(user_storage_path(user_id)) / "outputs"
    with db() as conn:
        canvas = conn.execute(
            "SELECT project_id FROM canvases WHERE user_id = ? AND id = ?",
            (user_id, clean_id(task.get("canvas_id") or "")),
        ).fetchone()
    project_id = canvas["project_id"] if canvas else ""
    persisted: list[Dict[str, Any]] = []
    staged: list[Dict[str, Any]] = []
    try:
        for index, media in enumerate(media_items):
            kind = media.get("kind") if media.get("kind") in {"image", "video"} else task.get("kind")
            asset_id = clean_id(f"task_{task['id']}_{index}")
            temporary = output_dir / f".{asset_id}.{uuid.uuid4().hex}.part"
            suffix, _size = await stream_generated_media_to_path(media["url"], kind, temporary, user_id)
            filename = f"{asset_id}{suffix}"
            target = output_dir / filename
            local_url = f"/api/assets/{asset_id}"
            title = str(task.get("prompt") or filename).strip()[:80] or filename
            staged.append(
                {
                    "id": asset_id,
                    "kind": kind,
                    "name": title,
                    "url": local_url,
                    "target": target,
                    "temporary": temporary,
                    "target_existed": target.exists(),
                }
            )
        for item in staged:
            item["temporary"].replace(item["target"])
        with db() as conn:
            for item in staged:
                conn.execute(
                    """
                    INSERT INTO assets (id, user_id, project_id, canvas_id, name, kind, path, url, source, task_id, node_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'task', ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        project_id = excluded.project_id,
                        canvas_id = excluded.canvas_id,
                        name = excluded.name,
                        kind = excluded.kind,
                        path = excluded.path,
                        url = excluded.url,
                        source = 'task',
                        task_id = excluded.task_id,
                        node_id = excluded.node_id
                    """,
                    (
                        item["id"],
                        user_id,
                        clean_id(project_id),
                        clean_id(task.get("canvas_id") or ""),
                        item["name"],
                        item["kind"],
                        str(item["target"]),
                        item["url"],
                        clean_id(task.get("id") or ""),
                        clean_id(task.get("node_id") or ""),
                        now_ms(),
                    ),
                )
        persisted = [
            {"id": item["id"], "url": item["url"], "kind": item["kind"], "name": item["name"]}
            for item in staged
        ]
    except Exception:
        for item in staged:
            item["temporary"].unlink(missing_ok=True)
            if not item["target_existed"]:
                item["target"].unlink(missing_ok=True)
        raise
    return {"items": persisted, "raw": sanitized_upstream_result(result)}


def find_task_target(user_id: str, task_id: str) -> Optional[Dict[str, str]]:
    clean_user = clean_id(user_id)
    clean_task = clean_id(task_id)
    task = get_task(clean_user, clean_task)
    if not task:
        return None
    if task.get("canvas_id") or task.get("node_id"):
        canvas_id = clean_id(task.get("canvas_id") or "")
        project_id = ""
        if canvas_id:
            with db() as conn:
                canvas = conn.execute(
                    "SELECT project_id FROM canvases WHERE user_id = ? AND id = ?",
                    (clean_user, canvas_id),
                ).fetchone()
            if canvas:
                project_id = clean_id(canvas["project_id"] or "")
        return {
            "project_id": project_id,
            "canvas_id": canvas_id,
            "node_id": clean_id(task.get("node_id") or ""),
        }
    with db() as conn:
        rows = conn.execute(
            "SELECT id, project_id, state_json FROM canvases WHERE user_id = ? ORDER BY updated_at DESC",
            (clean_user,),
        ).fetchall()
    for row in rows:
        try:
            state = json.loads(row["state_json"] or "{}")
        except Exception:
            state = {}
        for node in state.get("nodes") or []:
            if isinstance(node, dict) and clean_id(node.get("taskId") or "") == clean_task:
                return {
                    "project_id": clean_id(row["project_id"] or ""),
                    "canvas_id": row["id"],
                    "node_id": clean_id(node.get("id") or ""),
                }
    return None


def list_assets(user_id: str) -> list[Dict[str, Any]]:
    clean = clean_id(user_id)
    assets: list[Dict[str, Any]] = []
    with db() as conn:
        uploaded = conn.execute(
            "SELECT id, project_id, canvas_id, name, kind, path, url, source, task_id, node_id, created_at FROM assets WHERE user_id = ? ORDER BY created_at DESC LIMIT 300",
            (clean,),
        ).fetchall()
        tasks = conn.execute(
            "SELECT id, kind, prompt, canvas_id, node_id, result_json, created_at FROM tasks WHERE user_id = ? AND status = 'succeeded' ORDER BY created_at DESC LIMIT 300",
            (clean,),
        ).fetchall()
    persisted_task_ids = {row["task_id"] for row in uploaded if row["source"] == "task" and row["task_id"]}
    for row in uploaded:
        assets.append(
            {
                "id": row["id"],
                "source": row["source"] or "upload",
                "title": row["name"],
                "kind": row["kind"],
                "path": row["path"],
                "url": row["url"],
                "project_id": row["project_id"],
                "canvas_id": row["canvas_id"],
                "node_id": row["node_id"],
                "task_id": row["task_id"],
                "created_at": row["created_at"],
            }
        )
    for row in tasks:
        if row["id"] in persisted_task_ids:
            continue
        try:
            result = json.loads(row["result_json"] or "{}")
        except Exception:
            result = {}
        for index, media in enumerate(extract_result_assets(result, row["kind"])):
            if media["url"].startswith("/api/assets/"):
                continue
            assets.append(
                {
                    "id": f"task_{row['id']}_{index}",
                    "source": "task",
                    "title": str(row["prompt"] or row["kind"])[:80],
                    "kind": media["kind"],
                    "path": "",
                    "url": media["url"],
                    "project_id": "",
                    "canvas_id": row["canvas_id"],
                    "node_id": row["node_id"],
                    "task_id": row["id"],
                    "created_at": row["created_at"],
                }
            )
    assets.sort(key=lambda item: int(item.get("created_at") or 0), reverse=True)
    return assets


def delete_asset(user_id: str, asset_id: str) -> bool:
    clean_user = clean_id(user_id)
    clean_asset = clean_id(asset_id)
    with db() as conn:
        row = conn.execute(
            "SELECT path FROM assets WHERE user_id = ? AND id = ?",
            (clean_user, clean_asset),
        ).fetchone()
        if not row:
            return False
        conn.execute("DELETE FROM assets WHERE user_id = ? AND id = ?", (clean_user, clean_asset))

    raw_path = str(row["path"] or "").strip()
    if raw_path:
        root = Path(user_storage_path(clean_user)).resolve()
        target = Path(raw_path).resolve()
        if target.is_relative_to(root):
            target.unlink(missing_ok=True)
    return True


def update_task_status(task_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: str = "") -> None:
    terminal = status in {"succeeded", "failed"}
    with db() as conn:
        conn.execute(
            "UPDATE tasks SET status = ?, result_json = ?, error = ?, lease_until = ?, worker_id = ?, updated_at = ? WHERE id = ?",
            (
                status,
                json.dumps(result or {}, ensure_ascii=False),
                str(error or "")[:2000],
                0 if terminal else now_ms() + int_env("TASK_LEASE_SECONDS", 120) * 1000,
                "" if terminal else WORKER_ID,
                now_ms(),
                clean_id(task_id),
            ),
        )


def complete_task(task_id: str, result: Dict[str, Any]) -> None:
    update_task_status(task_id, "succeeded", result=result, error="")


def fail_task(task_id: str, error: str) -> None:
    clean = clean_id(task_id)
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT user_id, cost, refunded FROM tasks WHERE id = ?", (clean,)).fetchone()
        if not row:
            return
        ts = now_ms()
        conn.execute(
            "UPDATE tasks SET status = ?, error = ?, lease_until = 0, worker_id = '', updated_at = ? WHERE id = ?",
            ("failed", str(error or "任务失败")[:2000], ts, clean),
        )
        cost = int(row["cost"] or 0)
        if cost > 0 and not bool(row["refunded"]):
            user = conn.execute("SELECT credits FROM users WHERE id = ?", (row["user_id"],)).fetchone()
            if not user:
                raise AppError("任务用户不存在", 404)
            balance = int(user["credits"] or 0) + cost
            conn.execute("UPDATE users SET credits = ?, updated_at = ? WHERE id = ?", (balance, ts, row["user_id"]))
            conn.execute(
                "INSERT INTO credit_events (id, user_id, delta, balance_after, reason, actor_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (uuid.uuid4().hex, row["user_id"], cost, balance, "任务失败返还", "", ts),
            )
            conn.execute("UPDATE tasks SET refunded = 1, updated_at = ? WHERE id = ?", (ts, clean))


def requeue_expired_tasks(current_ms: Optional[int] = None) -> int:
    current = int(current_ms if current_ms is not None else now_ms())
    max_attempts = max(1, int_env("TASK_MAX_ATTEMPTS", 3))
    with db() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET status = 'queued', lease_until = 0, worker_id = '', updated_at = ? "
            "WHERE status = 'running' AND lease_until <= ? AND attempt_count < ?",
            (current, current, max_attempts),
        )
    return cursor.rowcount


def recover_expired_tasks(current_ms: Optional[int] = None) -> Dict[str, int]:
    current = int(current_ms if current_ms is not None else now_ms())
    max_attempts = max(1, int_env("TASK_MAX_ATTEMPTS", 3))
    with db() as conn:
        rows = conn.execute(
            "SELECT id FROM tasks WHERE status = 'running' AND lease_until <= ? AND attempt_count >= ?",
            (current, max_attempts),
        ).fetchall()
    for row in rows:
        fail_task(row["id"], f"任务已达到最大尝试次数（{max_attempts}）")
    return {"requeued": requeue_expired_tasks(current), "failed": len(rows)}


def recover_interrupted_tasks() -> None:
    recover_expired_tasks()


def claim_next_task(worker_id: str = WORKER_ID, lease_ms: Optional[int] = None) -> Optional[Dict[str, Any]]:
    clean_worker = clean_id(worker_id) or WORKER_ID
    lease = max(1000, int(lease_ms or int_env("TASK_LEASE_SECONDS", 120) * 1000))
    current = now_ms()
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT id FROM tasks WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1").fetchone()
        if not row:
            return None
        task_id = row["id"]
        conn.execute(
            """
            UPDATE tasks
            SET status = 'running', worker_id = ?, lease_until = ?, attempt_count = attempt_count + 1,
                request_id = CASE WHEN request_id = '' THEN lower(hex(randomblob(16))) ELSE request_id END,
                error = '', updated_at = ?
            WHERE id = ? AND status = 'queued'
            """,
            (clean_worker, current + lease, current, task_id),
        )
        claimed = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return task_from_row(claimed)


def claim_task(task_id: str, worker_id: str = WORKER_ID, lease_ms: Optional[int] = None) -> Optional[Dict[str, Any]]:
    clean_task = clean_id(task_id)
    clean_worker = clean_id(worker_id) or WORKER_ID
    lease = max(1000, int(lease_ms or int_env("TASK_LEASE_SECONDS", 120) * 1000))
    current = now_ms()
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute(
            """
            UPDATE tasks
            SET status = 'running', worker_id = ?, lease_until = ?, attempt_count = attempt_count + 1,
                request_id = CASE WHEN request_id = '' THEN lower(hex(randomblob(16))) ELSE request_id END,
                error = '', updated_at = ?
            WHERE id = ? AND status = 'queued'
            """,
            (clean_worker, current + lease, current, clean_task),
        )
        if cursor.rowcount != 1:
            return None
        claimed = conn.execute("SELECT * FROM tasks WHERE id = ?", (clean_task,)).fetchone()
    return task_from_row(claimed)


def renew_task_lease(task_id: str, worker_id: str = WORKER_ID) -> bool:
    current = now_ms()
    with db() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET lease_until = ?, updated_at = ? WHERE id = ? AND status = 'running' AND worker_id = ?",
            (
                current + int_env("TASK_LEASE_SECONDS", 120) * 1000,
                current,
                clean_id(task_id),
                clean_id(worker_id) or WORKER_ID,
            ),
        )
    return cursor.rowcount == 1


async def task_lease_heartbeat(task_id: str, worker_id: str) -> None:
    interval = max(5, int_env("TASK_LEASE_HEARTBEAT_SECONDS", 30))
    while True:
        await asyncio.sleep(interval)
        if not renew_task_lease(task_id, worker_id):
            return


async def execute_claimed_task(task: Dict[str, Any], worker_id: str = WORKER_ID) -> None:
    heartbeat = asyncio.create_task(task_lease_heartbeat(task["id"], worker_id))
    try:
        options = task.get("options") or {}
        request_id = task.get("request_id") or task["id"]
        if task["kind"] == "llm":
            result = await call_llm(task["prompt"], options, request_id)
        elif task["kind"] == "image":
            result = await call_image(task["prompt"], options, request_id)
            result = await persist_generated_assets(task, result)
        else:
            result = await call_video(task["prompt"], options, request_id)
            result = await persist_generated_assets(task, result)
        complete_task(task["id"], result)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        fail_task(task["id"], str(exc))
    finally:
        heartbeat.cancel()
        await asyncio.gather(heartbeat, return_exceptions=True)


async def run_generation_task(task_id: str) -> None:
    task = claim_task(task_id, WORKER_ID)
    if task:
        await execute_claimed_task(task, WORKER_ID)


def wake_task_worker() -> None:
    if TASK_QUEUE_EVENT is not None:
        TASK_QUEUE_EVENT.set()


async def task_worker_loop(worker_id: str = WORKER_ID) -> None:
    while True:
        recover_expired_tasks()
        task = claim_next_task(worker_id)
        if task:
            await execute_claimed_task(task, worker_id)
            continue
        if TASK_QUEUE_EVENT is None:
            await asyncio.sleep(0.75)
            continue
        TASK_QUEUE_EVENT.clear()
        try:
            await asyncio.wait_for(TASK_QUEUE_EVENT.wait(), timeout=0.75)
        except asyncio.TimeoutError:
            pass


def request_headers(api_key: str, request_id: str = "") -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    if request_id:
        headers["Idempotency-Key"] = request_id
        headers["X-Request-ID"] = request_id
    return headers


def build_llm_payload(prompt: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    values = normalize_task_options("llm", options)
    model = values.get("model") or str(os.getenv("LLM_MODEL") or "gpt-4o-mini").strip()
    system_prompt = values.get("system_prompt") or "You are a concise production assistant."
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    }


def image_dimensions(ratio: str, image_size: str) -> str:
    if image_size in {"", "auto", "自适应"}:
        return ""
    long_side = {"1K": 1024, "2K": 2048, "4K": 4096}.get(image_size)
    if not long_side:
        return ""
    try:
        width_ratio, height_ratio = (max(1, int(part)) for part in ratio.split(":", 1))
    except Exception:
        width_ratio, height_ratio = 1, 1
    if width_ratio >= height_ratio:
        width = long_side
        height = max(64, round((long_side * height_ratio / width_ratio) / 64) * 64)
    else:
        height = long_side
        width = max(64, round((long_side * width_ratio / height_ratio) / 64) * 64)
    return f"{width}x{height}"


def build_image_payload(prompt: str, options: Optional[Dict[str, Any]], url: str) -> Dict[str, Any]:
    values = normalize_task_options("image", options)
    model = values.get("model") or str(os.getenv("IMAGE_MODEL") or "gpt-image-1").strip()
    payload: Dict[str, Any] = {"prompt": prompt, "n": values.get("count", 1)}
    size = image_dimensions(values.get("ratio", "1:1"), values.get("image_size", "自适应"))
    if size:
        payload["size"] = size
    if model and "/deployments/" not in str(url or ""):
        payload["model"] = model
    return payload


def build_video_payload(prompt: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    values = normalize_task_options("video", options)
    payload: Dict[str, Any] = {
        "model": values.get("model") or str(os.getenv("VIDEO_MODEL") or "seedance-2.0").strip(),
        "prompt": prompt,
        "mode": values.get("mode", "text_to_video"),
        "duration": values.get("duration", 5),
        "aspect_ratio": values.get("aspect_ratio", "16:9"),
    }
    resolution = values.get("resolution", "Auto")
    if resolution not in {"", "Auto", "auto"}:
        payload["resolution"] = resolution
    if values.get("output_fps"):
        payload["fps"] = values["output_fps"]
    for source, target in (
        ("enhance_prompt", "enhance_prompt"),
        ("fixed_camera", "fixed_camera"),
        ("generate_audio", "generate_audio"),
        ("first_last_frame", "first_last_frame"),
    ):
        if values.get(source):
            payload[target] = True
    return payload


async def call_llm(prompt: str, options: Optional[Dict[str, Any]] = None, request_id: str = "") -> Dict[str, Any]:
    values = normalize_task_options("llm", options)
    config = resolve_provider_config("llm", values.get("provider", ""))
    if not config["configured"]:
        raise RuntimeError(f"供应商“{config['provider']}”未配置 LLM API")
    if not values.get("model") and config["model"]:
        values["model"] = config["model"]
    payload = build_llm_payload(prompt, values)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        resp = await client.post(config["url"], headers=request_headers(config["api_key"], request_id), json=payload)
        resp.raise_for_status()
        data = resp.json()
    text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return {"text": text, "raw": data}


async def call_image(prompt: str, options: Optional[Dict[str, Any]] = None, request_id: str = "") -> Dict[str, Any]:
    values = normalize_task_options("image", options)
    config = resolve_provider_config("image", values.get("provider", ""))
    if not config["configured"]:
        raise RuntimeError(f"供应商“{config['provider']}”未配置生图 API")
    if not values.get("model") and config["model"]:
        values["model"] = config["model"]
    payload = build_image_payload(prompt, values, config["url"])
    async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
        resp = await client.post(config["url"], headers=request_headers(config["api_key"], request_id), json=payload)
        resp.raise_for_status()
        data = resp.json()
    return {"raw": data, "items": data.get("data") or []}


def video_task_id(data: Dict[str, Any]) -> str:
    for container in (data, data.get("data") or {}, data.get("result") or {}, data.get("output") or {}):
        if not isinstance(container, dict):
            continue
        for key in ("task_id", "id", "request_id"):
            value = str(container.get(key) or "").strip()
            if value:
                return value
    return ""


def video_task_status(data: Dict[str, Any]) -> str:
    for container in (data, data.get("data") or {}, data.get("result") or {}, data.get("output") or {}):
        if not isinstance(container, dict):
            continue
        value = str(container.get("status") or container.get("state") or "").strip().lower()
        if value:
            return value
    return ""


def video_error_message(data: Dict[str, Any]) -> str:
    for container in (data, data.get("error") or {}, data.get("data") or {}):
        if isinstance(container, dict):
            value = container.get("message") or container.get("error_message") or container.get("detail")
            if value:
                return str(value)
    return "上游视频任务失败"


async def call_video(prompt: str, options: Optional[Dict[str, Any]] = None, request_id: str = "") -> Dict[str, Any]:
    values = normalize_task_options("video", options)
    config = resolve_provider_config("video", values.get("provider", ""))
    if not config["configured"]:
        raise RuntimeError(f"供应商“{config['provider']}”未配置视频 API")
    if not values.get("model") and config["model"]:
        values["model"] = config["model"]
    payload = build_video_payload(prompt, values)
    async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
        resp = await client.post(config["url"], headers=request_headers(config["api_key"], request_id), json=payload)
        resp.raise_for_status()
        data = resp.json()
        task_id = video_task_id(data)
        if extract_result_assets(data, "video"):
            return {"raw": data, "task_id": task_id}
        if not task_id:
            raise RuntimeError("上游视频接口未返回任务 ID 或视频结果")
        template = config["status_url_template"]
        if not template:
            raise RuntimeError(f"供应商“{config['provider']}”缺少视频状态查询地址")
        if "{task_id}" not in template:
            raise RuntimeError("视频状态查询地址必须包含 {task_id}")
        status_url = template.replace("{task_id}", quote(task_id, safe=""))
        deadline = time.monotonic() + max(1.0, float_env("VIDEO_POLL_TIMEOUT_SECONDS", 900.0))
        interval = max(0.0, float_env("VIDEO_POLL_INTERVAL_SECONDS", 3.0))
        failed_states = {"failed", "error", "cancelled", "canceled", "rejected", "expired"}
        while time.monotonic() < deadline:
            status_response = await client.get(status_url, headers=request_headers(config["api_key"], request_id))
            status_response.raise_for_status()
            status_data = status_response.json()
            status = video_task_status(status_data)
            if status in failed_states:
                raise RuntimeError(video_error_message(status_data))
            if extract_result_assets(status_data, "video"):
                return {"raw": status_data, "task_id": task_id}
            await asyncio.sleep(interval)
    raise RuntimeError(f"视频生成超时：{task_id}")


def set_session_cookie(response: Response, user_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user_id),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=env_flag("COOKIE_SECURE", "0"),
        samesite="lax",
    )


def current_user(request: Request) -> Optional[Dict[str, Any]]:
    return user_from_session_token(request.cookies.get(SESSION_COOKIE, ""))


def require_user(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def require_admin(request: Request) -> Dict[str, Any]:
    user = require_user(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def handle_app_error(exc: AppError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


class RegisterPayload(BaseModel):
    email: str
    password: str
    invite_code: str


class LoginPayload(BaseModel):
    email: str
    password: str


class PasswordChangePayload(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=200)


class NamePayload(BaseModel):
    name: str = Field(default="", max_length=100)


class CanvasSavePayload(BaseModel):
    name: str = ""
    state: Dict[str, Any] = Field(default_factory=dict)
    revision: Optional[int] = None


class TaskPayload(BaseModel):
    kind: str
    prompt: str = Field(min_length=1, max_length=20000)
    canvas_id: str = ""
    node_id: str = ""
    options: Dict[str, Any] = Field(default_factory=dict)


class WorkflowTemplatePayload(BaseModel):
    name: str = Field(default="", max_length=100)
    payload: Dict[str, Any] = Field(default_factory=dict)


class CreditPayload(BaseModel):
    delta: int
    reason: str = "后台手动调整"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global TASK_QUEUE_EVENT
    validate_runtime_config()
    init_db()
    workers: list[asyncio.Task] = []
    if env_flag("TASK_WORKER_ENABLED", "1"):
        TASK_QUEUE_EVENT = asyncio.Event()
        worker_count = max(1, min(8, int_env("TASK_WORKER_CONCURRENCY", 2)))
        workers = [asyncio.create_task(task_worker_loop(f"{WORKER_ID}-{index + 1}")) for index in range(worker_count)]
        wake_task_worker()
    try:
        yield
    finally:
        for worker in workers:
            worker.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)
        TASK_QUEUE_EVENT = None


app = FastAPI(title="Canvas SaaS Commercial", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "media-src 'self' data: https:; "
        "connect-src 'self' https:; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'",
    )
    if production_mode():
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)


@app.get("/favicon.ico")
async def favicon():
    return Response(FAVICON_SVG, media_type="image/svg+xml")


@app.get("/")
async def home(request: Request):
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/assets")
@app.get("/account")
@app.get("/logs")
async def secondary_page(request: Request):
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/login")
async def login_page(request: Request):
    if current_user(request):
        return RedirectResponse("/", status_code=303)
    return FileResponse(STATIC_DIR / "auth.html")


@app.get("/register")
async def register_page(request: Request):
    if current_user(request):
        return RedirectResponse("/", status_code=303)
    return FileResponse(STATIC_DIR / "auth.html")


@app.get("/admin")
async def admin_page(request: Request):
    require_admin(request)
    return FileResponse(STATIC_DIR / "admin.html")


@app.post("/api/auth/register")
async def api_register(request: Request, payload: RegisterPayload):
    auth_key = record_auth_attempt(request, payload.email)
    user = register_user(payload.email, payload.password, payload.invite_code)
    clear_auth_attempts(auth_key)
    response = JSONResponse({"user": user})
    set_session_cookie(response, user["id"])
    return response


@app.post("/api/auth/login")
async def api_login(request: Request, payload: LoginPayload):
    auth_key = record_auth_attempt(request, payload.email)
    user = authenticate_user(payload.email, payload.password)
    clear_auth_attempts(auth_key)
    response = JSONResponse({"user": user})
    set_session_cookie(response, user["id"])
    return response


@app.post("/api/auth/logout")
async def api_logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/api/me")
async def api_me(request: Request):
    user = current_user(request)
    return {"user": user, "storage": user_storage_summary(user["id"]) if user else None}


@app.post("/api/account/password")
async def api_change_password(payload: PasswordChangePayload, request: Request):
    user = require_user(request)
    change_password(user["id"], payload.current_password, payload.new_password)
    return {"ok": True}


@app.get("/api/capabilities")
async def api_capabilities(request: Request):
    require_user(request)
    return {"generation": generation_capabilities()}


@app.get("/api/projects")
async def api_projects(request: Request):
    user = require_user(request)
    return {"projects": list_projects(user["id"])}


@app.post("/api/projects")
async def api_create_project(payload: NamePayload, request: Request):
    user = require_user(request)
    return {"project": create_project(user["id"], payload.name)}


@app.get("/api/projects/{project_id}/canvases")
async def api_canvases(project_id: str, request: Request):
    user = require_user(request)
    return {"canvases": list_canvases(user["id"], project_id)}


@app.post("/api/projects/{project_id}/canvases")
async def api_create_canvas(project_id: str, payload: NamePayload, request: Request):
    user = require_user(request)
    return {"canvas": create_canvas(user["id"], project_id, payload.name)}


@app.get("/api/canvases/{canvas_id}")
async def api_get_canvas(canvas_id: str, request: Request):
    user = require_user(request)
    canvas = get_canvas(user["id"], canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="画布不存在")
    return {"canvas": canvas}


@app.put("/api/canvases/{canvas_id}")
async def api_save_canvas(canvas_id: str, payload: CanvasSavePayload, request: Request):
    user = require_user(request)
    return {
        "canvas": save_canvas_state(
            user["id"],
            canvas_id,
            payload.state,
            payload.name,
            expected_revision=payload.revision,
        )
    }


@app.post("/api/uploads")
async def api_upload(request: Request, file: UploadFile = File(...), project_id: str = "", canvas_id: str = ""):
    user = require_user(request)
    folder = Path(user_storage_path(user["id"])) / "uploads"
    kind, suffix = classify_upload(file.filename or "", file.content_type or "")
    asset_id = uuid.uuid4().hex
    filename = f"{asset_id}{suffix}"
    target = folder / filename
    temporary = folder / f".{filename}.{uuid.uuid4().hex}.part"
    total = 0
    header = bytearray()
    existing_usage = user_storage_usage_bytes(user["id"])
    try:
        with temporary.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_upload_bytes():
                    raise AppError(f"文件大小不能超过 {int_env('MAX_UPLOAD_MB', 50)}MB", 413)
                if existing_usage + total > max_user_storage_bytes():
                    raise AppError(f"用户存储空间不足，当前上限为 {int_env('MAX_USER_STORAGE_MB', 2048)}MB", 413)
                if len(header) < 64:
                    header.extend(chunk[: 64 - len(header)])
                output.write(chunk)
        validate_upload_content(kind, suffix, bytes(header))
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    url = f"/api/assets/{asset_id}"
    ts = now_ms()
    try:
        with db() as conn:
            conn.execute(
                "INSERT INTO assets (id, user_id, project_id, canvas_id, name, kind, path, url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (asset_id, user["id"], clean_id(project_id), clean_id(canvas_id), file.filename or filename, kind, str(target), url, ts),
            )
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {"asset": {"id": asset_id, "name": file.filename or filename, "kind": kind, "url": url}}


@app.get("/api/assets/{asset_id}")
async def api_asset(asset_id: str, request: Request):
    user = require_user(request)
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM assets WHERE user_id = ? AND id = ?",
            (user["id"], clean_id(asset_id)),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="素材不存在")
    return FileResponse(
        row["path"],
        filename=row["name"],
        content_disposition_type="inline",
    )


@app.delete("/api/assets/{asset_id}")
async def api_delete_asset(asset_id: str, request: Request):
    user = require_user(request)
    if not delete_asset(user["id"], asset_id):
        raise HTTPException(status_code=404, detail="素材不存在")
    return {"ok": True, "storage": user_storage_summary(user["id"])}


@app.post("/api/tasks")
async def api_create_task(payload: TaskPayload, request: Request):
    user = require_user(request)
    task = create_task(
        user["id"],
        payload.kind,
        payload.prompt,
        task_cost(payload.kind),
        payload.canvas_id,
        payload.node_id,
        payload.options,
    )
    wake_task_worker()
    return {"task": task, "balance": credit_balance(user["id"])}


@app.get("/api/tasks")
async def api_tasks(request: Request):
    user = require_user(request)
    return {"tasks": list_tasks(user["id"])}


@app.get("/api/tasks/{task_id}/target")
async def api_task_target(task_id: str, request: Request):
    user = require_user(request)
    return {"target": find_task_target(user["id"], task_id)}


@app.get("/api/tasks/{task_id}")
async def api_task(task_id: str, request: Request):
    user = require_user(request)
    task = get_task(user["id"], task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"task": task, "balance": credit_balance(user["id"])}


@app.get("/api/assets")
async def api_assets(request: Request):
    user = require_user(request)
    assets = list_assets(user["id"])
    return {"assets": [{key: value for key, value in asset.items() if key != "path"} for asset in assets]}


@app.get("/api/workflows")
async def api_workflows(request: Request):
    user = require_user(request)
    return {"workflows": list_workflow_templates(user["id"])}


@app.post("/api/workflows")
async def api_create_workflow(payload: WorkflowTemplatePayload, request: Request):
    user = require_user(request)
    return {"workflow": create_workflow_template(user["id"], payload.name, payload.payload)}


@app.get("/api/workflows/{workflow_id}")
async def api_workflow(workflow_id: str, request: Request):
    user = require_user(request)
    workflow = get_workflow_template(user["id"], workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流模板不存在")
    return {"workflow": workflow}


@app.delete("/api/workflows/{workflow_id}")
async def api_delete_workflow(workflow_id: str, request: Request):
    user = require_user(request)
    if not delete_workflow_template(user["id"], workflow_id):
        raise HTTPException(status_code=404, detail="工作流模板不存在")
    return {"ok": True}


@app.get("/api/admin/users")
async def api_admin_users(request: Request):
    require_admin(request)
    with db() as conn:
        users = [public_user(dict(row)) for row in conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()]
    return {"users": users}


@app.post("/api/admin/users/{user_id}/credits")
async def api_admin_credits(user_id: str, payload: CreditPayload, request: Request):
    admin = require_admin(request)
    balance = adjust_credits(user_id, payload.delta, payload.reason, actor_id=admin["id"])
    return {"balance": balance}


@app.get("/api/admin/config")
async def api_admin_config(request: Request):
    require_admin(request)
    return {
        "llm_configured": bool(os.getenv("LLM_API_KEY")),
        "image_configured": bool(os.getenv("IMAGE_API_KEY") and os.getenv("IMAGE_GENERATION_URL")),
        "video_configured": bool(os.getenv("VIDEO_API_KEY") and os.getenv("VIDEO_GENERATION_URL")),
        "costs": {"llm": task_cost("llm"), "image": task_cost("image"), "video": task_cost("video")},
    }


def run_cli() -> bool:
    import sys

    if len(sys.argv) < 2:
        return False
    command = sys.argv[1].strip()
    if command != "create-admin":
        return False
    if len(sys.argv) != 4:
        print("Usage: python main.py create-admin <email> <password>")
        raise SystemExit(2)
    validate_runtime_config()
    init_db()
    admin = create_admin_user(sys.argv[2], sys.argv[3])
    print(f"Admin ready: {admin['email']}")
    return True


if __name__ == "__main__":
    import uvicorn

    if not run_cli():
        validate_runtime_config()
        init_db()
        uvicorn.run(app, host="127.0.0.1", port=int_env("PORT", 3020))

