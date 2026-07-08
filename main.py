import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Request, Response, UploadFile
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

SESSION_COOKIE = "canvas_saas_session"
SESSION_MAX_AGE = 30 * 24 * 60 * 60


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


def int_env(name: str, default: int) -> int:
    try:
        return int(float(str(os.getenv(name) or default).strip()))
    except Exception:
        return default


def invite_code() -> str:
    return str(os.getenv("INVITE_CODE") or "canvasv1").strip()


def session_secret() -> str:
    return str(os.getenv("SESSION_SECRET") or os.getenv("INVITE_CODE") or "local-dev-session-secret")


def default_credits() -> int:
    return max(0, int_env("DEFAULT_CREDITS", 100))


def task_cost(kind: str) -> int:
    defaults = {"llm": 1, "image": 5, "video": 40}
    return max(0, int_env(f"COST_{str(kind or '').upper()}", defaults.get(kind, 1)))


def clean_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "", str(value or ""))[:80]


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
            """
        )
        ensure_columns(
            conn,
            "tasks",
            {
                "canvas_id": "TEXT NOT NULL DEFAULT ''",
                "node_id": "TEXT NOT NULL DEFAULT ''",
            },
        )


def normalize_email(email: str) -> str:
    value = str(email or "").strip().lower()
    if len(value) > 254 or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
        raise AppError("请输入有效邮箱")
    return value


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


def credit_balance(user_id: str) -> int:
    with db() as conn:
        row = conn.execute("SELECT credits FROM users WHERE id = ?", (clean_id(user_id),)).fetchone()
    return int(row["credits"]) if row else 0


def adjust_credits(user_id: str, delta: int, reason: str, actor_id: str = "") -> int:
    clean = clean_id(user_id)
    with db() as conn:
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


def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    email = normalize_email(email)
    with db() as conn:
        user = row_dict(conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone())
    if not user or not verify_password(password, str(user.get("password_hash") or "")):
        raise AppError("账号或密码不正确", 401)
    user_storage_path(user["id"])
    return public_user(user)


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


def save_canvas_state(user_id: str, canvas_id: str, state: Dict[str, Any], name: str = "") -> Dict[str, Any]:
    if not get_canvas(user_id, canvas_id):
        raise AppError("画布不存在", 404)
    ts = now_ms()
    payload = json.dumps(state or {}, ensure_ascii=False)
    with db() as conn:
        if name:
            conn.execute(
                "UPDATE canvases SET state_json = ?, name = ?, updated_at = ? WHERE user_id = ? AND id = ?",
                (payload, str(name).strip()[:80], ts, clean_id(user_id), clean_id(canvas_id)),
            )
        else:
            conn.execute(
                "UPDATE canvases SET state_json = ?, updated_at = ? WHERE user_id = ? AND id = ?",
                (payload, ts, clean_id(user_id), clean_id(canvas_id)),
            )
    return get_canvas(user_id, canvas_id) or {}


def create_task(user_id: str, kind: str, prompt: str, cost: int, canvas_id: str = "", node_id: str = "") -> Dict[str, Any]:
    clean = clean_id(user_id)
    kind = str(kind or "").strip().lower()
    if kind not in {"llm", "image", "video"}:
        raise AppError("不支持的任务类型")
    cost = max(0, int(cost or 0))
    if cost:
        adjust_credits(clean, -cost, f"{kind} 任务扣费")
    task_id = uuid.uuid4().hex
    ts = now_ms()
    with db() as conn:
        conn.execute(
            "INSERT INTO tasks (id, user_id, kind, prompt, cost, status, canvas_id, node_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (task_id, clean, kind, str(prompt or "")[:20000], cost, "queued", clean_id(canvas_id), clean_id(node_id), ts, ts),
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
    if not row:
        return None
    try:
        row["result"] = json.loads(row.get("result_json") or "{}")
    except Exception:
        row["result"] = {}
    row.pop("result_json", None)
    row["refunded"] = bool(row.get("refunded"))
    return row


def list_tasks(user_id: str) -> list[Dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT 100",
            (clean_id(user_id),),
        ).fetchall()
    tasks = []
    for row in rows:
        item = dict(row)
        try:
            item["result"] = json.loads(item.get("result_json") or "{}")
        except Exception:
            item["result"] = {}
        item.pop("result_json", None)
        item["refunded"] = bool(item.get("refunded"))
        tasks.append(item)
    return tasks


def update_task_status(task_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: str = "") -> None:
    with db() as conn:
        conn.execute(
            "UPDATE tasks SET status = ?, result_json = ?, error = ?, updated_at = ? WHERE id = ?",
            (status, json.dumps(result or {}, ensure_ascii=False), str(error or "")[:2000], now_ms(), clean_id(task_id)),
        )


def complete_task(task_id: str, result: Dict[str, Any]) -> None:
    update_task_status(task_id, "succeeded", result=result, error="")


def fail_task(task_id: str, error: str) -> None:
    clean = clean_id(task_id)
    with db() as conn:
        row = conn.execute("SELECT user_id, cost, refunded FROM tasks WHERE id = ?", (clean,)).fetchone()
        if not row:
            return
        conn.execute(
            "UPDATE tasks SET status = ?, error = ?, updated_at = ? WHERE id = ?",
            ("failed", str(error or "任务失败")[:2000], now_ms(), clean),
        )
    if int(row["cost"] or 0) > 0 and not bool(row["refunded"]):
        adjust_credits(row["user_id"], int(row["cost"]), "任务失败返还")
        with db() as conn:
            conn.execute("UPDATE tasks SET refunded = 1, updated_at = ? WHERE id = ?", (now_ms(), clean))


async def run_generation_task(task_id: str) -> None:
    task = None
    with db() as conn:
        task = row_dict(conn.execute("SELECT * FROM tasks WHERE id = ?", (clean_id(task_id),)).fetchone())
    if not task:
        return
    update_task_status(task_id, "running")
    try:
        if task["kind"] == "llm":
            result = await call_llm(task["prompt"])
        elif task["kind"] == "image":
            result = await call_image(task["prompt"])
        else:
            result = await call_video(task["prompt"])
        complete_task(task_id, result)
    except Exception as exc:
        fail_task(task_id, str(exc))


async def call_llm(prompt: str) -> Dict[str, Any]:
    api_key = str(os.getenv("LLM_API_KEY") or "").strip()
    base_url = str(os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = str(os.getenv("LLM_MODEL") or "gpt-4o-mini").strip()
    if not api_key:
        raise RuntimeError("未配置 LLM_API_KEY")
    url = str(os.getenv("LLM_CHAT_URL") or f"{base_url}/chat/completions")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise production assistant."},
            {"role": "user", "content": prompt},
        ],
    }
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        resp = await client.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
        resp.raise_for_status()
        data = resp.json()
    text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return {"text": text, "raw": data}


async def call_image(prompt: str) -> Dict[str, Any]:
    api_key = str(os.getenv("IMAGE_API_KEY") or "").strip()
    url = str(os.getenv("IMAGE_GENERATION_URL") or "").strip()
    model = str(os.getenv("IMAGE_MODEL") or "gpt-image-1").strip()
    if not api_key or not url:
        raise RuntimeError("未配置 IMAGE_API_KEY 或 IMAGE_GENERATION_URL")
    payload: Dict[str, Any] = {"prompt": prompt, "n": 1}
    if model and "/deployments/" not in url:
        payload["model"] = model
    async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
        resp = await client.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
        resp.raise_for_status()
        data = resp.json()
    return {"raw": data, "items": data.get("data") or []}


async def call_video(prompt: str) -> Dict[str, Any]:
    api_key = str(os.getenv("VIDEO_API_KEY") or "").strip()
    url = str(os.getenv("VIDEO_GENERATION_URL") or "").strip()
    model = str(os.getenv("VIDEO_MODEL") or "seedance-2.0").strip()
    if not api_key or not url:
        raise RuntimeError("未配置 VIDEO_API_KEY 或 VIDEO_GENERATION_URL")
    async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
        resp = await client.post(url, headers={"Authorization": f"Bearer {api_key}"}, json={"model": model, "prompt": prompt})
        resp.raise_for_status()
        data = resp.json()
    return {"raw": data}


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


class NamePayload(BaseModel):
    name: str = Field(default="", max_length=100)


class CanvasSavePayload(BaseModel):
    name: str = ""
    state: Dict[str, Any] = Field(default_factory=dict)


class TaskPayload(BaseModel):
    kind: str
    prompt: str = Field(min_length=1, max_length=20000)
    canvas_id: str = ""
    node_id: str = ""


class CreditPayload(BaseModel):
    delta: int
    reason: str = "后台手动调整"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Canvas SaaS Commercial", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)


@app.get("/")
async def home(request: Request):
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
async def api_register(payload: RegisterPayload):
    user = register_user(payload.email, payload.password, payload.invite_code)
    response = JSONResponse({"user": user})
    set_session_cookie(response, user["id"])
    return response


@app.post("/api/auth/login")
async def api_login(payload: LoginPayload):
    user = authenticate_user(payload.email, payload.password)
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
    return {"user": user}


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
    return {"canvas": save_canvas_state(user["id"], canvas_id, payload.state, payload.name)}


@app.post("/api/uploads")
async def api_upload(request: Request, file: UploadFile = File(...), project_id: str = "", canvas_id: str = ""):
    user = require_user(request)
    folder = Path(user_storage_path(user["id"])) / "uploads"
    suffix = Path(file.filename or "upload.bin").suffix[:16]
    asset_id = uuid.uuid4().hex
    filename = f"{asset_id}{suffix or '.bin'}"
    target = folder / filename
    content = await file.read()
    target.write_bytes(content)
    content_type = str(file.content_type or "")
    if content_type.startswith("image/"):
        kind = "image"
    elif content_type.startswith("video/"):
        kind = "video"
    else:
        kind = "file"
    url = f"/api/assets/{asset_id}"
    ts = now_ms()
    with db() as conn:
        conn.execute(
            "INSERT INTO assets (id, user_id, project_id, canvas_id, name, kind, path, url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (asset_id, user["id"], clean_id(project_id), clean_id(canvas_id), file.filename or filename, kind, str(target), url, ts),
        )
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
    return FileResponse(row["path"], filename=row["name"])


@app.post("/api/tasks")
async def api_create_task(payload: TaskPayload, request: Request, background: BackgroundTasks):
    user = require_user(request)
    task = create_task(user["id"], payload.kind, payload.prompt, task_cost(payload.kind), payload.canvas_id, payload.node_id)
    background.add_task(run_generation_task, task["id"])
    return {"task": task, "balance": credit_balance(user["id"])}


@app.get("/api/tasks")
async def api_tasks(request: Request):
    user = require_user(request)
    return {"tasks": list_tasks(user["id"])}


@app.get("/api/tasks/{task_id}")
async def api_task(task_id: str, request: Request):
    user = require_user(request)
    task = get_task(user["id"], task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"task": task, "balance": credit_balance(user["id"])}


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


if __name__ == "__main__":
    import uvicorn

    init_db()
    uvicorn.run(app, host="127.0.0.1", port=int_env("PORT", 3020))

