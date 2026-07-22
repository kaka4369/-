import base64
import asyncio
import hashlib
import hmac
import ipaddress
import io
import json
import os
import re
import secrets
import shutil
import socket
import sqlite3
import subprocess
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote, unquote, urljoin, urlparse

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
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
VERSIONED_STATIC_CACHE_CONTROL = "public, max-age=31536000, immutable"
DEMO_MEDIA_FILES = {
    "image": STATIC_DIR / "demo" / "yunzhi-generated-character.png",
    "video": STATIC_DIR / "demo" / "yunzhi-seedance-story.mp4",
}
FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#102126"/><stop offset="1" stop-color="#168f87"/></linearGradient></defs>
  <rect width="64" height="64" rx="16" fill="url(#g)"/>
  <circle cx="22" cy="17" r="8" fill="#31d5c8"/>
  <circle cx="42" cy="17" r="8" fill="#31d5c8"/>
  <text x="32" y="46" text-anchor="middle" font-family="sans-serif" font-size="32" font-weight="800" fill="#ffffff">云</text>
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
VIDEO_REFERENCE_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
VIDEO_REFERENCE_INLINE_MAX_SIDE = 1024
VIDEO_REFERENCE_INLINE_MAX_BYTES = 900 * 1024
LINGJING_LEGACY_VIDEO_MODELS = {
    "seedance-2.0",
    "seedance-2.0-1080",
    "seedance-2.0-vision-1080",
}
LINGJING_DEFAULT_VIDEO_MODEL = "cdance2.0-0611"
VERIFIED_VIDEO_REFERENCE_MODELS = {"doubao-seedance-2-0-260128"}
VIDEO_STRONG_REFERENCE_ALIASES = {"主体", "场景", "道具", "风格"}
VIDEO_REFERENCE_ROLE_KEYS = (
    ("first_frame", "first_frame_asset_id"),
    ("reference_image", "strong_reference_asset_id"),
    ("last_frame", "last_frame_asset_id"),
)
AUTH_RATE_ATTEMPTS: Dict[str, list[float]] = {}
WORKER_ID = uuid.uuid4().hex
TASK_QUEUE_EVENT: Optional[asyncio.Event] = None
PROVIDER_PREFIXES = {
    "llm": {"国禾API": "LLM", "OpenAI兼容": "OPENAI_LLM", "自定义": "CUSTOM_LLM"},
    "image": {"国禾API": "IMAGE", "OpenAI兼容": "OPENAI_IMAGE", "自定义": "CUSTOM_IMAGE"},
    "video": {"灵境API": "VIDEO", "火山引擎": "VOLCANO_VIDEO", "自定义": "CUSTOM_VIDEO"},
}
DEFAULT_PROVIDERS = {"llm": "国禾API", "image": "国禾API", "video": "灵境API"}
PROVIDER_SETTING_PREFIX = "provider_config"
MAX_PROVIDER_MODELS = 100
ECOMMERCE_MODEL_MANIFEST = STATIC_DIR / "ecommerce" / "models" / "manifest.json"
ECOMMERCE_MODEL_ROOT = ECOMMERCE_MODEL_MANIFEST.parent
ECOMMERCE_SCENE_PRESETS = (
    {
        "id": "mediterranean-terrace",
        "name": "地中海露台",
        "prompt": "明亮的地中海白色石墙露台，蓝天与柔和海景，干净的自然日光",
        "preview_image": "/static/ecommerce/scenes/outdoor-scenes-contact-sheet.png",
        "preview_index": 0,
    },
    {
        "id": "sunset-garden",
        "name": "落日花园",
        "prompt": "高级住宅花园的落日金色时刻，绿植层次丰富，柔和逆光与自然阴影",
        "preview_image": "/static/ecommerce/scenes/outdoor-scenes-contact-sheet.png",
        "preview_index": 1,
    },
    {
        "id": "villa-courtyard",
        "name": "别墅庭院",
        "prompt": "现代别墅庭院，浅色石材、克制绿植与高级自然光，背景整洁",
        "preview_image": "/static/ecommerce/scenes/outdoor-scenes-contact-sheet.png",
        "preview_index": 2,
    },
    {
        "id": "paris-rooftop",
        "name": "巴黎屋顶",
        "prompt": "巴黎城市屋顶露台，远景建筑虚化，阴天柔光，时装大片氛围",
        "preview_image": "/static/ecommerce/scenes/outdoor-scenes-contact-sheet.png",
        "preview_index": 3,
    },
    {
        "id": "seaside-estate",
        "name": "海边庄园",
        "prompt": "临海庄园步道，海面与远景轻微虚化，通透日光，优雅度假氛围",
        "preview_image": "/static/ecommerce/scenes/outdoor-scenes-contact-sheet.png",
        "preview_index": 4,
    },
    {
        "id": "city-terrace",
        "name": "都市露台",
        "prompt": "现代都市高层露台，玻璃与浅色建筑线条，柔和天光，高级商业摄影",
        "preview_image": "/static/ecommerce/scenes/outdoor-scenes-contact-sheet.png",
        "preview_index": 5,
    },
)
ECOMMERCE_SHOTS = {
    "full": "正面全身照，从头到脚完整入镜，服装轮廓和下摆清晰可见",
    "half": "正面半身照，突出领口、肩部、袖型、门襟和面料细节",
    "detail": "服装细节近景，准确呈现面料纹理、工艺、印花和装饰位置",
    "back": "背面全身照，模特自然背对镜头，完整展示服装后背结构和下摆",
}
ECOMMERCE_RATIO_PRESETS = {
    "3:4": "竖版电商主图，适合完整展示模特与服装",
    "1:1": "方形电商主图，适合商品列表与平台封面",
    "4:5": "竖版详情图，适合移动端商品详情与社交媒体",
    "2:3": "标准全身人像比例，保留更多头脚空间",
    "9:16": "移动端全屏竖图，适合短视频平台封面",
    "4:3": "横版详情图，适合并排展示人物与环境",
    "3:2": "横版商业摄影比例，适合场景化棚拍",
    "16:9": "宽幅横版场景图，适合店铺横幅与展示页",
}
ECOMMERCE_POSE_NAMES = {
    "front": "正面站姿",
    "three-quarter": "四分之三侧转",
    "side": "侧面站姿",
    "back": "背面站姿",
    "weight-shift": "重心侧移",
    "walking": "自然行走",
    "arms-open": "展袖站姿",
    "turn-look": "转身回望",
}
ECOMMERCE_POSES = {
    "front": "自然正面站姿，肩线端正，双臂不过度遮挡服装",
    "three-quarter": "身体朝镜头自然转约 45 度，脸部看向镜头，双臂放松，清楚展示服装正面与侧面廓形",
    "side": "自然侧身站姿，清楚展示服装侧面廓形与腰线",
    "back": "自然背面站姿，完整展示后背结构、肩线和下摆",
    "weight-shift": "重心自然落在一侧，一条腿略微前伸，双臂自然下垂，形成轻松稳定的站姿",
    "walking": "自然向前行走的动态抓拍，步态轻松，服装垂坠与运动感真实",
    "arms-open": "双臂与身体略微分开，双手自然放松，不遮挡袖型、腰线和侧缝",
    "turn-look": "身体背向镜头约四分之三，头部自然回望镜头，同时展示服装后背与侧面轮廓",
}
ECOMMERCE_WHITE_BACKGROUND_CONTRACT = "neutral-white-srgb-v1"


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class EcommerceWhiteBackgroundQualityError(RuntimeError):
    def __init__(self, metrics: Dict[str, Any]):
        self.metrics = metrics
        super().__init__(
            "白底质量检查未通过：背景不是均匀的中性纯白，系统已阻止交付暖白或偏黄结果"
        )


def now_ms() -> int:
    return int(time.time() * 1000)


def bundled_demo_media(kind: str) -> Path:
    normalized = str(kind or "").strip().lower()
    target = DEMO_MEDIA_FILES.get(normalized)
    if not target:
        raise AppError("不支持的演示媒体类型", 404)
    if not target.is_file():
        raise AppError("演示媒体暂不可用", 503)
    return target


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


def provider_setting_key(kind: str, provider: str) -> str:
    normalized_kind = str(kind or "").strip().lower()
    _selected, prefix = provider_prefix(normalized_kind, provider)
    return f"{PROVIDER_SETTING_PREFIX}:{normalized_kind}:{prefix}"


def normalize_provider_models(values: Any, limit: int = MAX_PROVIDER_MODELS) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        raise AppError("模型列表格式不正确", 400)
    models: list[str] = []
    seen: set[str] = set()
    for value in values:
        model = str(value or "").strip()
        if not model or model in seen:
            continue
        if len(model) > 120:
            raise AppError("模型 ID 不能超过 120 个字符", 400)
        if any(ord(char) < 32 or ord(char) == 127 for char in model):
            raise AppError("模型 ID 不能包含控制字符", 400)
        if len(models) >= limit:
            raise AppError(f"每个供应商最多保存 {limit} 个模型", 400)
        seen.add(model)
        models.append(model)
    return models


def load_provider_override(kind: str, provider: str) -> Dict[str, Any]:
    key = provider_setting_key(kind, provider)
    try:
        with db() as conn:
            row = conn.execute(
                "SELECT value_json, updated_at FROM app_settings WHERE key = ?",
                (key,),
            ).fetchone()
    except sqlite3.OperationalError:
        return {}
    if not row:
        return {}
    try:
        value = json.loads(row["value_json"] or "{}")
    except Exception:
        return {}
    if not isinstance(value, dict):
        return {}
    value["updated_at"] = int(row["updated_at"] or 0)
    return value


def save_provider_override(kind: str, provider: str, value: Dict[str, Any]) -> int:
    key = provider_setting_key(kind, provider)
    ts = now_ms()
    stored = {item_key: item_value for item_key, item_value in value.items() if item_key != "updated_at"}
    with db() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at
            """,
            (key, json.dumps(stored, ensure_ascii=False), ts),
        )
    return ts


def config_secret_cipher(require_explicit: bool = False) -> Optional[Fernet]:
    configured = str(os.getenv("CONFIG_ENCRYPTION_KEY") or "").strip()
    if not configured:
        if production_mode():
            if require_explicit:
                raise AppError("生产环境保存 API 密钥前必须配置 CONFIG_ENCRYPTION_KEY", 500)
            return None
        configured = session_secret()
    if production_mode() and len(configured) < 32:
        if require_explicit:
            raise AppError("生产环境的 CONFIG_ENCRYPTION_KEY 必须至少 32 位", 500)
        return None
    derived = base64.urlsafe_b64encode(hashlib.sha256(configured.encode("utf-8")).digest())
    return Fernet(derived)


def encrypt_provider_secret(value: str) -> str:
    cipher = config_secret_cipher(require_explicit=True)
    return cipher.encrypt(str(value or "").encode("utf-8")).decode("ascii")


def decrypt_provider_secret(value: str) -> str:
    cipher = config_secret_cipher()
    if not cipher or not value:
        return ""
    try:
        return cipher.decrypt(str(value).encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeError):
        return ""


def mask_provider_secret(value: str) -> str:
    secret = str(value or "")
    if not secret:
        return ""
    return "••••" if len(secret) <= 4 else f"••••{secret[-4:]}"


def validate_provider_url(value: str, label: str = "接口地址", require_task_id: bool = False) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    hostname = str(parsed.hostname or "").strip().lower().rstrip(".")
    if parsed.scheme not in {"http", "https"} or not hostname:
        raise AppError(f"{label}必须使用 http:// 或 https://", 400)
    if parsed.username or parsed.password:
        raise AppError(f"{label}不能包含用户名或密码", 400)
    if parsed.fragment:
        raise AppError(f"{label}不能包含片段标识", 400)
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        raise AppError(f"{label}不能指向本机或内网地址", 400)
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise AppError(f"{label}不能指向本机或内网地址", 400)
    if require_task_id and "{task_id}" not in text:
        raise AppError("视频状态查询地址必须包含 {task_id}", 400)
    return text


def resolve_provider_config(kind: str, provider: str = "") -> Dict[str, Any]:
    normalized_kind = str(kind or "").strip().lower()
    selected, prefix = provider_prefix(normalized_kind, provider)
    api_key = str(os.getenv(f"{prefix}_API_KEY") or "").strip()
    model = str(os.getenv(f"{prefix}_MODEL") or "").strip()
    models = [model] if model else []
    base_url = ""
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
    override = load_provider_override(normalized_kind, selected)
    if "models" in override:
        models = normalize_provider_models(override.get("models"))
        model = str(override.get("model") or "").strip()
        if model not in models:
            model = models[0] if models else ""
    elif "model" in override:
        model = str(override.get("model") or "").strip()
        models = [model] if model else []
    if normalized_kind == "llm" and "base_url" in override:
        base_url = str(override.get("base_url") or "").strip().rstrip("/")
        if "url" not in override:
            url = f"{base_url}/chat/completions" if base_url else ""
    if "url" in override:
        url = str(override.get("url") or "").strip()
    if normalized_kind == "video" and "status_url_template" in override:
        status_url_template = str(override.get("status_url_template") or "").strip()
    if override.get("api_key_cleared"):
        api_key = ""
    elif override.get("api_key_ciphertext"):
        api_key = decrypt_provider_secret(str(override.get("api_key_ciphertext") or ""))
    return {
        "kind": normalized_kind,
        "provider": selected,
        "prefix": prefix,
        "api_key": api_key,
        "base_url": base_url,
        "url": url,
        "model": model,
        "models": models,
        "status_url_template": status_url_template,
        "configured": bool(api_key and url and models),
        "source": "admin" if override else "env",
        "updated_at": int(override.get("updated_at") or 0) if override else None,
    }


def public_provider_config(kind: str, provider: str) -> Dict[str, Any]:
    config = resolve_provider_config(kind, provider)
    return {
        "kind": config["kind"],
        "provider": config["provider"],
        "configured": config["configured"],
        "has_api_key": bool(config["api_key"]),
        "key_preview": mask_provider_secret(config["api_key"]),
        "base_url": config["base_url"],
        "url": config["url"],
        "model": config["model"],
        "models": config["models"],
        "status_url_template": config["status_url_template"],
        "source": config["source"],
        "updated_at": config["updated_at"],
    }


def list_public_provider_configs() -> list[Dict[str, Any]]:
    return [
        public_provider_config(kind, provider)
        for kind, providers in PROVIDER_PREFIXES.items()
        for provider in providers
    ]


def runtime_provider_model(kind: str, config: Dict[str, Any]) -> str:
    model = str(config.get("model") or "").strip()
    if (
        str(kind or "").strip().lower() == "video"
        and config.get("provider") == "灵境API"
        and model in LINGJING_LEGACY_VIDEO_MODELS
    ):
        return LINGJING_DEFAULT_VIDEO_MODEL
    return model


def video_model_capability(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return only member-safe capabilities implemented by this adapter."""
    model = runtime_provider_model("video", config).lower()
    supports_lingjing_references = (
        config.get("provider") == "灵境API"
        and model in VERIFIED_VIDEO_REFERENCE_MODELS
    )
    return {
        "image_to_video": supports_lingjing_references,
        "strong_reference": supports_lingjing_references,
        "first_last_frame": supports_lingjing_references,
        # The gateway accepts either first+last frames or reference media, never both.
        "max_images": 2 if supports_lingjing_references else 0,
    }


def provider_model_variants(kind: str, config: Dict[str, Any]) -> list[Dict[str, Any]]:
    models = config.get("models")
    if not isinstance(models, list):
        fallback = str(config.get("model") or "").strip()
        models = [fallback] if fallback else []
    default_model = str(config.get("model") or "").strip()
    ordered_models = ([default_model] if default_model in models else []) + [
        model for model in models if model != default_model
    ]
    variants: list[Dict[str, Any]] = []
    for model in ordered_models:
        variant = dict(config)
        variant["model"] = model
        variants.append(variant)
    return variants


def configured_provider_configs(kind: str) -> list[Dict[str, Any]]:
    normalized_kind = str(kind or "").strip().lower()
    providers = PROVIDER_PREFIXES.get(normalized_kind)
    if not providers:
        raise RuntimeError(f"不支持的生成类型：{normalized_kind or '未指定'}")
    return [
        config
        for provider in providers
        if (config := resolve_provider_config(normalized_kind, provider))["configured"]
    ]


def resolve_generation_provider_config(kind: str, model: str = "") -> Dict[str, Any]:
    normalized_kind = str(kind or "").strip().lower()
    configs = configured_provider_configs(normalized_kind)
    kind_label = {"llm": "文本生成", "image": "图片生成", "video": "视频生成"}.get(
        normalized_kind,
        "生成",
    )
    if not configs:
        raise RuntimeError(f"后台尚未配置可用的{kind_label}模型")

    variants = [variant for config in configs for variant in provider_model_variants(normalized_kind, config)]
    requested_model = str(model or "").strip()
    if requested_model:
        for variant in variants:
            if requested_model == runtime_provider_model(normalized_kind, variant):
                return variant
        for variant in variants:
            if requested_model == str(variant.get("model") or "").strip():
                return variant
    default_provider = DEFAULT_PROVIDERS.get(normalized_kind, "")
    return next((variant for variant in variants if variant["provider"] == default_provider), variants[0])


def update_provider_config(kind: str, provider: str, payload: Any) -> Dict[str, Any]:
    normalized_kind = str(kind or "").strip().lower()
    selected, _prefix = provider_prefix(normalized_kind, provider)
    value = load_provider_override(normalized_kind, selected)
    value.pop("updated_at", None)

    base_url = getattr(payload, "base_url", None)
    url = getattr(payload, "url", None)
    model = getattr(payload, "model", None)
    models = getattr(payload, "models", None)
    status_url_template = getattr(payload, "status_url_template", None)
    if base_url is not None:
        if normalized_kind != "llm" and str(base_url or "").strip():
            raise AppError("只有 LLM 供应商支持 Base URL", 400)
        value["base_url"] = validate_provider_url(base_url, "Base URL").rstrip("/")
    if url is not None:
        value["url"] = validate_provider_url(url, "接口地址")
    if models is not None:
        clean_models = normalize_provider_models(models)
        clean_default = str(model or "").strip() if model is not None else ""
        if len(clean_default) > 120 or any(ord(char) < 32 or ord(char) == 127 for char in clean_default):
            raise AppError("默认模型 ID 格式不正确", 400)
        if clean_default and clean_default not in clean_models:
            raise AppError("默认模型必须在已选模型列表中", 400)
        if not clean_default and clean_models:
            previous_default = str(value.get("model") or "").strip()
            clean_default = previous_default if previous_default in clean_models else clean_models[0]
        value["models"] = clean_models
        value["model"] = clean_default if clean_models else ""
    elif model is not None:
        clean_models = normalize_provider_models([model])
        value["models"] = clean_models
        value["model"] = clean_models[0] if clean_models else ""
    if status_url_template is not None:
        clean_status_url = str(status_url_template or "").strip()
        if normalized_kind != "video" and clean_status_url:
            raise AppError("只有视频供应商支持状态查询地址", 400)
        value["status_url_template"] = validate_provider_url(
            clean_status_url,
            "视频状态查询地址",
            require_task_id=bool(clean_status_url),
        )

    api_key = str(getattr(payload, "api_key", None) or "").strip()
    if bool(getattr(payload, "clear_api_key", False)):
        value.pop("api_key_ciphertext", None)
        value["api_key_cleared"] = True
    elif api_key:
        value["api_key_ciphertext"] = encrypt_provider_secret(api_key)
        value.pop("api_key_cleared", None)

    save_provider_override(normalized_kind, selected, value)
    return public_provider_config(normalized_kind, selected)


def provider_deployment_model(config: Dict[str, Any]) -> str:
    for candidate in (config.get("url"), config.get("base_url")):
        path = urlparse(str(candidate or "")).path
        match = re.search(r"/deployments/([^/]+)", path, flags=re.IGNORECASE)
        if not match:
            continue
        model = unquote(match.group(1)).strip()
        if model and len(model) <= 120 and not any(ord(char) < 32 or ord(char) == 127 for char in model):
            return model
    return ""


def provider_models_url(config: Dict[str, Any]) -> str:
    kind = str(config.get("kind") or "").strip().lower()
    candidate = str(config.get("url") or config.get("base_url") or "").strip()
    if not candidate:
        raise AppError("请先保存服务商请求地址", 400)
    candidate = validate_provider_url(candidate, "模型列表地址")
    parsed = urlparse(candidate)
    path = parsed.path.rstrip("/")
    lower_path = path.lower()
    if lower_path.endswith("/models"):
        models_path = path
    else:
        models_path = ""
        for suffix in (
            "/chat/completions",
            "/images/generations",
            "/image/generations",
            "/videos/generations",
            "/video/generations",
            "/contents/generations/tasks",
            "/generations",
        ):
            if lower_path.endswith(suffix):
                models_path = f"{path[:-len(suffix)].rstrip('/')}/models"
                break
        if not models_path and (lower_path.endswith(("/v1", "/v1beta", "/api/v3")) or kind == "llm"):
            models_path = f"{path}/models"
        if not models_path:
            raise AppError("当前请求地址无法推导标准模型列表接口，请手动填写模型 ID", 400)
    return parsed._replace(path=models_path, params="", fragment="").geturl()


async def validate_provider_models_url(url: str) -> None:
    target = validate_provider_url(url, "模型列表地址")
    parsed = urlparse(target)
    hostname = str(parsed.hostname or "").strip().lower()
    try:
        addresses = [ipaddress.ip_address(hostname)]
    except ValueError:
        try:
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
        except ValueError as exc:
            raise AppError("模型列表地址端口无效；也可以先手动添加模型 ID", 400) from exc
        try:
            resolved = await asyncio.wait_for(
                asyncio.to_thread(socket.getaddrinfo, hostname, port, type=socket.SOCK_STREAM),
                timeout=3,
            )
        except asyncio.TimeoutError as exc:
            raise AppError(
                f"服务器解析域名 {hostname} 超时，请检查服务器 DNS 或网络；也可以先手动添加模型 ID",
                400,
            ) from exc
        except socket.gaierror as exc:
            raise AppError(
                f"服务器无法解析域名 {hostname}，请确认域名拼写或公网 DNS 记录；也可以先手动添加模型 ID",
                400,
            ) from exc
        except OSError as exc:
            raise AppError(
                f"服务器解析域名 {hostname} 失败，请检查服务器 DNS 或网络；也可以先手动添加模型 ID",
                400,
            ) from exc
        addresses = []
        for entry in resolved:
            try:
                addresses.append(ipaddress.ip_address(entry[4][0]))
            except (ValueError, IndexError):
                continue
    if not addresses or any(not address.is_global for address in addresses):
        raise AppError("模型列表地址不能指向本机或内网", 400)


def provider_model_metadata_kinds(item: Any) -> set[str]:
    if not isinstance(item, dict):
        return set()
    values: list[str] = []

    def append_value(value: Any) -> None:
        if value in (None, "", [], {}):
            return
        if isinstance(value, str):
            values.append(value)
            return
        try:
            values.append(json.dumps(value, ensure_ascii=False))
        except (TypeError, ValueError):
            values.append(str(value))

    for key in (
        "type",
        "task_type",
        "category",
        "output_type",
        "output_modality",
        "output_modalities",
    ):
        append_value(item.get(key))

    modalities = item.get("modalities")
    if isinstance(modalities, dict):
        for key in ("output", "outputs", "response", "result"):
            append_value(modalities.get(key))

    capabilities = item.get("capabilities")
    if isinstance(capabilities, dict):
        for key in ("output", "outputs", "response", "result", "output_modalities"):
            append_value(capabilities.get(key))
        for capability, enabled in capabilities.items():
            if enabled and re.search(
                r"(?:generation|generate|text[-_ ]?to|image[-_ ]?to|video[-_ ]?to|chat|completion)",
                str(capability),
                flags=re.IGNORECASE,
            ):
                values.append(str(capability))
    elif capabilities not in (None, "", [], {}):
        try:
            capability_text = json.dumps(capabilities, ensure_ascii=False)
        except (TypeError, ValueError):
            capability_text = str(capabilities)
        if re.search(
            r"(?:generation|generate|text[-_ ]?to|image[-_ ]?to|video[-_ ]?to|chat|completion)",
            capability_text,
            flags=re.IGNORECASE,
        ):
            values.append(capability_text)
    metadata = " ".join(values).lower()
    kinds: set[str] = set()
    video_task_pattern = r"(?:text|image)[-_ ]?to[-_ ]?video"
    image_task_pattern = r"text[-_ ]?to[-_ ]?image"
    if re.search(video_task_pattern, metadata):
        kinds.add("video")
    if re.search(image_task_pattern, metadata):
        kinds.add("image")
    remaining = re.sub(video_task_pattern, " ", metadata)
    remaining = re.sub(image_task_pattern, " ", remaining)
    if re.search(r"(?:^|[^a-z])video(?:$|[^a-z])", remaining):
        kinds.add("video")
    if re.search(r"(?:^|[^a-z])image(?:$|[^a-z])", remaining):
        kinds.add("image")
    if re.search(r"(?:^|[^a-z])(llm|chat|completion|language|text)(?:$|[^a-z])", remaining):
        kinds.add("llm")
    return kinds


def provider_model_name_kind(model: str) -> str:
    value = str(model or "").strip().lower()
    if re.search(
        r"(?:^|[-_/])(cdance|seedance|veo|sora|kling|hunyuan[-_]?video|cogvideo|ltx[-_]?video|runway|hailuo|vidu|pixverse|pika|wan(?:\d|[-_.]))",
        value,
    ):
        return "video"
    if re.search(
        r"(?:^|[-_/])(gpt[-_]?image|image(?:n|[-_.]?\d)|dall[-_]?e|flux|ideogram|midjourney|stable[-_]?diffusion|sdxl)(?:$|[-_.\d])",
        value,
    ):
        return "image"
    return ""


def provider_model_matches_kind(kind: str, provider: str, item: Any, model: str) -> bool:
    normalized_kind = str(kind or "").strip().lower()
    metadata_kinds = provider_model_metadata_kinds(item)
    if metadata_kinds:
        return normalized_kind in metadata_kinds

    value = str(model or "").strip().lower()
    if normalized_kind == "video" and provider == "灵境API":
        return bool(re.match(r"^(?:cdance|seedance)", value))

    name_kind = provider_model_name_kind(value)
    if normalized_kind in {"video", "image"}:
        return name_kind == normalized_kind
    if normalized_kind == "llm":
        return name_kind not in {"video", "image"}
    return False


def parse_provider_models(
    payload: Any,
    kind: str = "llm",
    provider: str = "",
    limit: int = 500,
) -> tuple[list[str], bool, int, int]:
    if not isinstance(payload, dict):
        raise AppError("模型列表接口返回了无法识别的数据格式", 502)
    items = payload.get("data")
    if not isinstance(items, list):
        items = payload.get("models")
    if not isinstance(items, list):
        items = payload.get("list")
    if not isinstance(items, list):
        raise AppError("模型列表接口未返回标准模型数组", 502)
    models: list[str] = []
    seen: set[str] = set()
    truncated = False
    discovered_count = 0
    filtered_out = 0
    for item in items:
        if isinstance(item, str):
            value = item
        elif isinstance(item, dict):
            value = item.get("id") or item.get("name") or item.get("model")
        else:
            value = ""
        model = str(value or "").strip()
        if not model or len(model) > 120 or any(ord(char) < 32 or ord(char) == 127 for char in model) or model in seen:
            continue
        seen.add(model)
        discovered_count += 1
        if not provider_model_matches_kind(kind, provider, item, model):
            filtered_out += 1
            continue
        if len(models) >= limit:
            truncated = True
            continue
        models.append(model)
    return models, truncated, discovered_count, filtered_out


async def fetch_provider_models(kind: str, provider: str) -> Dict[str, Any]:
    config = resolve_provider_config(kind, provider)
    deployment_model = provider_deployment_model(config)
    if deployment_model:
        return {
            "models": [deployment_model],
            "count": 1,
            "discovered_count": 1,
            "filtered_out": 0,
            "source": "deployment_path",
            "complete": False,
            "truncated": False,
            "message": "已从部署地址识别当前模型；该结果不是服务商完整模型列表",
        }
    if not config.get("api_key"):
        raise AppError("请先保存 API Key，再拉取模型列表", 400)

    models_url = provider_models_url(config)
    await validate_provider_models_url(models_url)
    headers = request_headers(str(config.get("api_key") or ""), url=models_url)
    headers["Accept"] = "application/json"
    timeout = httpx.Timeout(10.0, connect=5.0, read=10.0, write=5.0, pool=5.0)
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            async with client.stream("GET", models_url, headers=headers) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    raise AppError("模型列表接口发生重定向，请检查服务商请求地址", 400)
                if response.status_code in {401, 403}:
                    raise AppError("API Key 无效或无权读取模型列表", 400)
                if response.status_code == 404:
                    raise AppError("当前服务商不提供标准模型列表，请手动填写模型 ID", 400)
                if response.status_code == 429:
                    raise AppError("模型列表请求过于频繁，请稍后重试", 429)
                if response.status_code >= 400:
                    raise AppError("模型列表服务暂时不可用，请稍后重试", 502)
                content_length = response.headers.get("content-length", "")
                try:
                    if content_length and int(content_length) > 1024 * 1024:
                        raise AppError("模型列表响应过大，已停止读取", 413)
                except ValueError:
                    pass
                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > 1024 * 1024:
                        raise AppError("模型列表响应过大，已停止读取", 413)
                    chunks.append(chunk)
                raw = b"".join(chunks)
                content_type = str(response.headers.get("content-type") or "").lower()
    except AppError:
        raise
    except httpx.TimeoutException as exc:
        raise AppError("模型列表请求超时，请检查地址或稍后重试", 504) from exc
    except httpx.RequestError as exc:
        raise AppError("无法连接模型列表服务，请检查请求地址", 502) from exc

    if "text/html" in content_type or raw.lstrip().startswith(b"<"):
        raise AppError("模型列表地址返回了网页内容，请检查 API 请求地址", 400)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AppError("模型列表接口返回了无效 JSON", 502) from exc
    models, truncated, discovered_count, filtered_out = parse_provider_models(
        payload,
        kind=str(config.get("kind") or ""),
        provider=str(config.get("provider") or ""),
    )
    complete = not truncated and not bool(payload.get("has_more"))
    kind_label = {"llm": "文本", "image": "生图", "video": "视频"}.get(str(config.get("kind") or ""), "")
    if models:
        message = f"已拉取 {len(models)} 个{kind_label}模型"
        if filtered_out:
            message += f"，已隐藏 {filtered_out} 个非{kind_label}模型"
        message += "，请选择后保存"
    elif discovered_count:
        message = f"接口返回了 {discovered_count} 个模型，但未识别到{kind_label}模型；仍可手动输入"
    else:
        message = "接口可访问，但没有返回模型列表；仍可手动输入"
    return {
        "models": models,
        "count": len(models),
        "discovered_count": discovered_count,
        "filtered_out": filtered_out,
        "source": "models_endpoint",
        "complete": complete,
        "truncated": truncated,
        "message": message,
    }


def provider_generation_capabilities() -> Dict[str, Any]:
    capabilities: Dict[str, Any] = {}
    for kind, providers in PROVIDER_PREFIXES.items():
        provider_states: Dict[str, Any] = {}
        for provider in providers:
            config = resolve_provider_config(kind, provider)
            provider_states[provider] = {
                "configured": config["configured"],
                "model": config["model"],
                "models": config["models"],
                "supports_async_status": bool(config["status_url_template"]) if kind == "video" else False,
            }
        capabilities[kind] = {
            "configured": any(item["configured"] for item in provider_states.values()),
            "providers": provider_states,
        }
    return capabilities


def generation_capabilities() -> Dict[str, Any]:
    capabilities: Dict[str, Any] = {}
    for kind in PROVIDER_PREFIXES:
        configs = configured_provider_configs(kind)
        models: list[str] = []
        model_capabilities: Dict[str, Any] = {}
        for config in configs:
            for variant in provider_model_variants(kind, config):
                model = runtime_provider_model(kind, variant)
                if model and model not in models:
                    models.append(model)
                    if kind == "video":
                        model_capabilities[model] = video_model_capability(variant)
        kind_capabilities: Dict[str, Any] = {
            "configured": bool(configs),
            "models": models,
        }
        if kind == "video":
            kind_capabilities["model_capabilities"] = model_capabilities
        capabilities[kind] = kind_capabilities
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


def configured_admin_host() -> str:
    return str(os.getenv("ADMIN_HOST") or "").strip().lower().rstrip(".")


def is_admin_portal_request(request: Request) -> bool:
    host = configured_admin_host()
    return bool(host and str(request.url.hostname or "").lower().rstrip(".") == host)


def require_admin_portal(request: Request) -> None:
    if configured_admin_host() and not is_admin_portal_request(request):
        raise HTTPException(status_code=404, detail="页面不存在")


def admin_entry_url(request: Request) -> str:
    host = configured_admin_host()
    if not host:
        return "/admin"
    scheme = "https" if production_mode() else request.url.scheme
    return f"{scheme}://{host}/admin"


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


def _verify_directory_writable(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    probe = directory / f".ready-{uuid.uuid4().hex}.tmp"
    try:
        with probe.open("xb") as handle:
            handle.write(b"ok")
            handle.flush()
    finally:
        probe.unlink(missing_ok=True)


def runtime_ready() -> bool:
    try:
        _verify_directory_writable(DATA_DIR)
        _verify_directory_writable(STORAGE_DIR)
        with db() as conn:
            row = conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
        return bool(row and row[0] >= 0)
    except Exception:
        return False


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

            CREATE TABLE IF NOT EXISTS generation_batches (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                client_request_id TEXT NOT NULL,
                canvas_id TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                total_items INTEGER NOT NULL,
                total_cost INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                UNIQUE(user_id, client_request_id)
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
                "batch_id": "TEXT NOT NULL DEFAULT ''",
                "batch_item_key": "TEXT NOT NULL DEFAULT ''",
            },
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_batch_item "
            "ON tasks(batch_id, batch_item_key) WHERE batch_id <> '' AND batch_item_key <> ''"
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


def adjust_credits_in_transaction(
    conn: sqlite3.Connection,
    user_id: str,
    delta: int,
    reason: str,
    actor_id: str = "",
) -> int:
    clean = clean_id(user_id)
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


def adjust_credits(user_id: str, delta: int, reason: str, actor_id: str = "") -> int:
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        return adjust_credits_in_transaction(conn, user_id, delta, reason, actor_id)


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
    clean_project = clean_id(project_id)
    canvas_id = uuid.uuid4().hex
    ts = now_ms()
    canvas_name = str(name or "新画布").strip()[:80] or "新画布"
    state = {"nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "scale": 1}}
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        project = conn.execute(
            "SELECT id FROM projects WHERE user_id = ? AND id = ? AND deleted_at = 0",
            (clean, clean_project),
        ).fetchone()
        if not project:
            raise AppError("项目不存在", 404)
        conn.execute(
            "INSERT INTO canvases (id, user_id, project_id, name, state_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (canvas_id, clean, clean_project, canvas_name, json.dumps(state, ensure_ascii=False), ts, ts),
        )
    return {
        "id": canvas_id,
        "user_id": clean,
        "project_id": clean_project,
        "name": canvas_name,
        "state": state,
        "revision": 1,
        "created_at": ts,
        "updated_at": ts,
    }


def get_canvas(user_id: str, canvas_id: str) -> Optional[Dict[str, Any]]:
    with db() as conn:
        row = row_dict(
            conn.execute(
                "SELECT c.* FROM canvases c JOIN projects p ON p.id = c.project_id AND p.user_id = c.user_id "
                "WHERE c.user_id = ? AND c.id = ? AND p.deleted_at = 0",
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
            "SELECT c.id, c.user_id, c.project_id, c.name, c.created_at, c.updated_at FROM canvases c "
            "JOIN projects p ON p.id = c.project_id AND p.user_id = c.user_id "
            "WHERE c.user_id = ? AND c.project_id = ? AND p.deleted_at = 0 ORDER BY c.updated_at DESC",
            (clean_id(user_id), clean_id(project_id)),
        ).fetchall()
    return [dict(row) for row in rows]


def resolve_active_workspace_target(
    conn: sqlite3.Connection,
    user_id: str,
    project_id: str = "",
    canvas_id: str = "",
) -> tuple[str, str]:
    clean_user = clean_id(user_id)
    clean_project = clean_id(project_id)
    clean_canvas = clean_id(canvas_id)
    if clean_canvas:
        canvas = conn.execute(
            "SELECT c.id, c.project_id FROM canvases c "
            "JOIN projects p ON p.id = c.project_id AND p.user_id = c.user_id "
            "WHERE c.user_id = ? AND c.id = ? AND p.deleted_at = 0",
            (clean_user, clean_canvas),
        ).fetchone()
        if not canvas or (clean_project and clean_project != canvas["project_id"]):
            raise AppError("项目或画布不存在", 404)
        return canvas["project_id"], canvas["id"]
    if clean_project:
        project = conn.execute(
            "SELECT id FROM projects WHERE user_id = ? AND id = ? AND deleted_at = 0",
            (clean_user, clean_project),
        ).fetchone()
        if not project:
            raise AppError("项目不存在", 404)
    return clean_project, ""


def active_canvas_task_count(conn: sqlite3.Connection, user_id: str, canvas_ids: list[str]) -> int:
    clean_canvas_ids = [clean_id(canvas_id) for canvas_id in canvas_ids if clean_id(canvas_id)]
    if not clean_canvas_ids:
        return 0
    placeholders = ", ".join("?" for _canvas_id in clean_canvas_ids)
    row = conn.execute(
        f"SELECT COUNT(*) AS task_count FROM tasks WHERE user_id = ? AND canvas_id IN ({placeholders}) "
        "AND status IN ('queued', 'running')",
        (clean_id(user_id), *clean_canvas_ids),
    ).fetchone()
    return int(row["task_count"] or 0)


def delete_canvas(user_id: str, canvas_id: str) -> bool:
    clean_user = clean_id(user_id)
    clean_canvas = clean_id(canvas_id)
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        canvas = conn.execute(
            "SELECT c.id, c.project_id FROM canvases c "
            "JOIN projects p ON p.id = c.project_id AND p.user_id = c.user_id "
            "WHERE c.user_id = ? AND c.id = ? AND p.deleted_at = 0",
            (clean_user, clean_canvas),
        ).fetchone()
        if not canvas:
            raise AppError("画布不存在", 404)
        if active_canvas_task_count(conn, clean_user, [clean_canvas]):
            raise AppError("画布有任务正在运行，请完成后再删除", 409)

        conn.execute(
            "UPDATE tasks SET canvas_id = '', node_id = '' WHERE user_id = ? AND canvas_id = ?",
            (clean_user, clean_canvas),
        )
        conn.execute(
            "UPDATE assets SET canvas_id = '', node_id = '' WHERE user_id = ? AND canvas_id = ?",
            (clean_user, clean_canvas),
        )
        conn.execute("DELETE FROM canvases WHERE user_id = ? AND id = ?", (clean_user, clean_canvas))
        conn.execute(
            "UPDATE projects SET updated_at = ? WHERE user_id = ? AND id = ? AND deleted_at = 0",
            (now_ms(), clean_user, canvas["project_id"]),
        )
    return True


def delete_project(user_id: str, project_id: str) -> int:
    clean_user = clean_id(user_id)
    clean_project = clean_id(project_id)
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        project = conn.execute(
            "SELECT id FROM projects WHERE user_id = ? AND id = ? AND deleted_at = 0",
            (clean_user, clean_project),
        ).fetchone()
        if not project:
            raise AppError("项目不存在", 404)

        canvas_ids = [
            row["id"]
            for row in conn.execute(
                "SELECT id FROM canvases WHERE user_id = ? AND project_id = ?",
                (clean_user, clean_project),
            ).fetchall()
        ]
        if active_canvas_task_count(conn, clean_user, canvas_ids):
            raise AppError("项目中有任务正在运行，请完成后再删除", 409)

        if canvas_ids:
            placeholders = ", ".join("?" for _canvas_id in canvas_ids)
            conn.execute(
                f"UPDATE tasks SET canvas_id = '', node_id = '' WHERE user_id = ? AND canvas_id IN ({placeholders})",
                (clean_user, *canvas_ids),
            )
            conn.execute(
                f"UPDATE assets SET project_id = '', canvas_id = '', node_id = '' "
                f"WHERE user_id = ? AND (project_id = ? OR canvas_id IN ({placeholders}))",
                (clean_user, clean_project, *canvas_ids),
            )
        else:
            conn.execute(
                "UPDATE assets SET project_id = '', canvas_id = '', node_id = '' WHERE user_id = ? AND project_id = ?",
                (clean_user, clean_project),
            )

        conn.execute("DELETE FROM canvases WHERE user_id = ? AND project_id = ?", (clean_user, clean_project))
        timestamp = now_ms()
        conn.execute(
            "UPDATE projects SET deleted_at = ?, updated_at = ? WHERE user_id = ? AND id = ? AND deleted_at = 0",
            (timestamp, timestamp, clean_user, clean_project),
        )
    return len(canvas_ids)


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


def normalize_strong_reference_alias(value: Any) -> str:
    alias = option_text(value, 20).lstrip("@").strip()
    alias = re.sub(r"\d+$", "", alias).strip()
    return alias if alias in VIDEO_STRONG_REFERENCE_ALIASES else ""


def normalized_video_reference_asset_roles(source: Dict[str, Any]) -> Dict[str, str]:
    legacy_ids: list[str] = []
    raw_legacy_ids = source.get("reference_asset_ids")
    for value in raw_legacy_ids if isinstance(raw_legacy_ids, list) else []:
        asset_id = clean_id(value)
        if asset_id and asset_id not in legacy_ids:
            legacy_ids.append(asset_id)
        if len(legacy_ids) >= 3:
            break

    first_frame = clean_id(source.get("first_frame_asset_id"))
    strong_reference = clean_id(source.get("strong_reference_asset_id"))
    last_frame = clean_id(source.get("last_frame_asset_id"))
    first_last_frame = option_bool(source.get("first_last_frame")) or bool(last_frame)

    if not first_frame and legacy_ids:
        first_frame = legacy_ids[0]
    remaining = [asset_id for asset_id in legacy_ids if asset_id != first_frame]
    if first_last_frame:
        if not last_frame:
            last_frame = next((asset_id for asset_id in remaining if asset_id != strong_reference), "")
    elif not strong_reference:
        strong_reference = next((asset_id for asset_id in remaining if asset_id != last_frame), "")

    return {
        "first_frame": first_frame,
        "reference_image": strong_reference,
        "last_frame": last_frame,
    }


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
        if option_text(source.get("operation"), 20) == "edit":
            raw_references = source.get("reference_inputs") if isinstance(source.get("reference_inputs"), dict) else {}
            product_asset_id = clean_id(raw_references.get("product_asset_id"))
            model_preset_id = clean_id(raw_references.get("model_preset_id"))
            if product_asset_id:
                normalized["operation"] = "edit"
                normalized["count"] = 1
                normalized["reference_inputs"] = {
                    "product_asset_id": product_asset_id,
                    "model_preset_id": model_preset_id,
                }
        raw_ecommerce = source.get("ecommerce") if isinstance(source.get("ecommerce"), dict) else {}
        if raw_ecommerce:
            environment = option_text(raw_ecommerce.get("environment"), 20)
            shot = option_text(raw_ecommerce.get("shot"), 20)
            pose = option_text(raw_ecommerce.get("pose"), 20)
            normalized["ecommerce"] = {
                "environment": environment if environment in {"white", "outdoor"} else "white",
                "shot": shot if shot in ECOMMERCE_SHOTS else "full",
                "pose": pose if pose in ECOMMERCE_POSES else "",
                "scene_preset_id": clean_id(raw_ecommerce.get("scene_preset_id")),
                "model_preset_id": clean_id(raw_ecommerce.get("model_preset_id")),
                "background_contract": (
                    ECOMMERCE_WHITE_BACKGROUND_CONTRACT
                    if environment == "white"
                    and option_text(raw_ecommerce.get("background_contract"), 50)
                    == ECOMMERCE_WHITE_BACKGROUND_CONTRACT
                    else ""
                ),
                "item_index": option_int(raw_ecommerce.get("item_index"), 0, 0, 19),
            }
    elif kind == "video":
        mode = option_text(source.get("mode")) or "text_to_video"
        aspect_ratio = option_text(source.get("aspect_ratio")) or "16:9"
        resolution = option_text(source.get("resolution")) or "Auto"
        output_fps = option_int(source.get("output_fps"), 0, 0, 60)
        reference_roles = normalized_video_reference_asset_roles(source)
        reference_asset_ids: list[str] = []
        for role, _option_key in VIDEO_REFERENCE_ROLE_KEYS:
            asset_id = reference_roles[role]
            if asset_id and asset_id not in reference_asset_ids:
                reference_asset_ids.append(asset_id)
        strong_reference_alias = normalize_strong_reference_alias(source.get("strong_reference_alias"))
        if reference_roles["reference_image"] and not strong_reference_alias:
            strong_reference_alias = "主体"
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
                "first_last_frame": option_bool(source.get("first_last_frame")) or bool(reference_roles["last_frame"]),
                "reference_asset_ids": reference_asset_ids,
                "first_frame_asset_id": reference_roles["first_frame"],
                "strong_reference_asset_id": reference_roles["reference_image"],
                "last_frame_asset_id": reference_roles["last_frame"],
                "strong_reference_alias": strong_reference_alias,
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


def load_ecommerce_catalog() -> Dict[str, Any]:
    try:
        payload = json.loads(ECOMMERCE_MODEL_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AppError("电商模特资源暂不可用", 503) from exc
    raw_models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(raw_models, list) or len(raw_models) != 20:
        raise AppError("电商模特资源不完整", 503)

    root = ECOMMERCE_MODEL_ROOT.resolve()
    models: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_models:
        if not isinstance(raw, dict):
            raise AppError("电商模特资源格式不正确", 503)
        preset_id = clean_id(raw.get("id"))
        group = option_text(raw.get("group"), 30)
        gender = option_text(raw.get("gender"), 20)
        image_url = str(raw.get("image") or "").strip()
        if (
            not preset_id
            or preset_id in seen
            or group not in {"domestic", "international"}
            or gender not in {"female", "male"}
        ):
            raise AppError("电商模特资源格式不正确", 503)
        parsed_path = unquote(urlparse(image_url).path)
        if not parsed_path.startswith("/static/ecommerce/models/"):
            raise AppError("电商模特资源路径不安全", 503)
        target = (ROOT / parsed_path.lstrip("/")).resolve()
        if not target.is_relative_to(root) or not target.is_file() or target.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            raise AppError("电商模特资源文件缺失", 503)
        models.append(
            {
                "id": preset_id,
                "group": group,
                "gender": gender,
                "display_name": option_text(raw.get("display_name"), 80) or preset_id,
                "tags": [option_text(tag, 30) for tag in raw.get("tags", []) if option_text(tag, 30)][:8],
                "image": image_url,
                "_path": str(target),
            }
        )
        seen.add(preset_id)
    distribution = {
        (group, gender): sum(
            model["group"] == group and model["gender"] == gender
            for model in models
        )
        for group in ("domestic", "international")
        for gender in ("female", "male")
    }
    if any(count != 5 for count in distribution.values()):
        raise AppError("电商模特资源性别分布不完整", 503)
    return {
        "models": models,
        "scenes": [dict(scene) for scene in ECOMMERCE_SCENE_PRESETS],
        "shots": [{"id": key, "name": value} for key, value in ECOMMERCE_SHOTS.items()],
        "ratios": [
            {"id": key, "name": key, "description": value}
            for key, value in ECOMMERCE_RATIO_PRESETS.items()
        ],
        "poses": [
            {"id": "auto", "name": "自动", "description": "根据商品版型自动选择不遮挡服装的自然姿势"}
        ]
        + [
            {"id": key, "name": ECOMMERCE_POSE_NAMES[key], "description": value}
            for key, value in ECOMMERCE_POSES.items()
        ],
        "image_cost": task_cost("image"),
        "max_batch_items": 20,
    }


def public_ecommerce_catalog() -> Dict[str, Any]:
    catalog = load_ecommerce_catalog()
    return {
        **catalog,
        "models": [
            {
                **{key: value for key, value in model.items() if key not in {"_path", "image"}},
                "image_url": model["image"],
            }
            for model in catalog["models"]
        ],
    }


def ecommerce_prompt(item: Dict[str, Any], catalog: Dict[str, Any]) -> str:
    model_preset_id = clean_id(item.get("model_preset_id"))
    custom_model_prompt = option_text(item.get("custom_model_prompt"), 800)
    environment = option_text(item.get("environment"), 20)
    scene_preset_id = clean_id(item.get("scene_preset_id"))
    custom_scene_prompt = option_text(item.get("custom_scene_prompt"), 800)
    shot = option_text(item.get("shot"), 20)
    pose = option_text(item.get("pose"), 20)

    if model_preset_id:
        model_instruction = "严格保持第二张参考图中成年模特的脸部、发型、体型、肤色与身份一致"
    else:
        model_instruction = f"创建并固定一位成年服装模特，性别与人物特征严格遵循人物设定：{custom_model_prompt}"
    if environment == "white":
        environment_instruction = (
            "纯白无缝电商影棚背景；背景必须是完全均匀的中性纯白（sRGB #FFFFFF，"
            "R=255、G=255、B=255），四角与主体周围亮度一致。采用约 5500K 的中性色温均匀柔光；"
            "禁止暖白、米白、奶油色、灰白、淡黄或其他色偏，禁止渐变、纹理、环境色、"
            "彩色反射、彩色投影与黄光污染；仅允许模特脚下非常轻微、低饱和的中性灰接触阴影"
        )
    else:
        scenes = {scene["id"]: scene for scene in catalog["scenes"]}
        scene_text = custom_scene_prompt or str((scenes.get(scene_preset_id) or {}).get("prompt") or "")
        environment_instruction = f"户外商业时装拍摄场景：{scene_text}。人物与服装是画面主体，背景自然虚化但可辨识"
    shot_instruction = ECOMMERCE_SHOTS.get(shot, ECOMMERCE_SHOTS["full"])
    pose_instruction = (
        f"姿势要求：{ECOMMERCE_POSES[pose]}"
        if pose in ECOMMERCE_POSES
        else "姿势自然、克制，手臂不遮挡服装关键结构"
    )

    return (
        "生成一张写实、高级、可直接用于电商详情页的服装模特摄影图。\n"
        "参考图规则：第一张图片是唯一商品款式依据；"
        + ("第二张图片是唯一模特身份依据。\n" if model_preset_id else "不提供模特参考图。\n")
        + "商品锁定：完整保留第一张商品图的颜色、面料质感、廓形、领口、袖型、门襟、纽扣、口袋、腰线、下摆、印花、刺绣、珠饰和透明度；不得新增、删除、移动、替换或重新设计任何商品细节。\n"
        + f"模特锁定：{model_instruction}；同一批次中保持身份稳定。\n"
        + f"拍摄环境：{environment_instruction}。\n"
        + f"镜头构图：{shot_instruction}。{pose_instruction}。\n"
        + "画质要求：真实皮肤与织物纹理，准确比例，专业电商摄影，主体清晰，无水印、无文字、无边框。\n"
        + "负向约束：不要改变服装款式或颜色，不要额外配饰，不要畸形肢体、重复人物、错误手指、遮挡商品、拼贴画、商品平铺图或假人台。"
        + (
            "白底附加禁令：不得使用暖黄、米黄、奶油色、灰白或渐变背景，不得产生有色投影、彩色反光或背景色带。"
            if environment == "white"
            else ""
        )
    )[:20000]


def _validate_ecommerce_product_asset(conn: sqlite3.Connection, user_id: str, asset_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id, kind, path FROM assets WHERE user_id = ? AND id = ?",
        (clean_id(user_id), clean_id(asset_id)),
    ).fetchone()
    if not row:
        raise AppError("商品图片不存在或无权使用", 404)
    if row["kind"] != "image":
        raise AppError("商品素材必须是图片")
    root = Path(user_storage_path(user_id)).resolve()
    target = Path(str(row["path"] or "")).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise AppError("商品图片文件不存在", 404)
    return row


def _normalize_ecommerce_item(item: Dict[str, Any], catalog: Dict[str, Any]) -> Dict[str, Any]:
    product_asset_id = clean_id(item.get("product_asset_id"))
    model_preset_id = clean_id(item.get("model_preset_id"))
    custom_model_prompt = option_text(item.get("custom_model_prompt"), 800)
    environment = option_text(item.get("environment"), 20)
    scene_preset_id = clean_id(item.get("scene_preset_id"))
    custom_scene_prompt = option_text(item.get("custom_scene_prompt"), 800)
    shot = option_text(item.get("shot"), 20) or "full"
    pose = option_text(item.get("pose"), 20)
    if pose == "auto":
        pose = ""
    ratio = option_text(item.get("ratio"), 20) or "3:4"
    image_size = option_text(item.get("image_size"), 20) or "2K"
    if not product_asset_id:
        raise AppError("请选择商品图片")
    model_ids = {model["id"] for model in catalog["models"]}
    if bool(model_preset_id) == bool(custom_model_prompt):
        raise AppError("请选择一个内置模特，或填写自定义模特提示词")
    if model_preset_id and model_preset_id not in model_ids:
        raise AppError("所选模特不存在", 404)
    if environment not in {"white", "outdoor"}:
        raise AppError("拍摄环境不正确")
    if environment == "outdoor":
        scene_ids = {scene["id"] for scene in catalog["scenes"]}
        if bool(scene_preset_id) == bool(custom_scene_prompt):
            raise AppError("室外拍摄请选择一个场景，或填写自定义场景提示词")
        if scene_preset_id and scene_preset_id not in scene_ids:
            raise AppError("所选场景不存在", 404)
    else:
        scene_preset_id = ""
        custom_scene_prompt = ""
    if shot not in ECOMMERCE_SHOTS:
        raise AppError("拍摄镜头不正确")
    if pose and pose not in ECOMMERCE_POSES:
        raise AppError("模特姿势不正确")
    if ratio not in ECOMMERCE_RATIO_PRESETS:
        raise AppError("图片比例不正确")
    if image_size not in {"自适应", "auto", "1K", "2K", "4K"}:
        raise AppError("图片尺寸不正确")
    return {
        "product_asset_id": product_asset_id,
        "model_preset_id": model_preset_id,
        "custom_model_prompt": custom_model_prompt,
        "environment": environment,
        "scene_preset_id": scene_preset_id,
        "custom_scene_prompt": custom_scene_prompt,
        "shot": shot,
        "pose": pose,
        "ratio": ratio,
        "image_size": image_size,
    }


def create_ecommerce_batch(
    user_id: str,
    client_request_id: str,
    items: list[Dict[str, Any]],
    canvas_id: str = "",
    model: str = "",
) -> tuple[Dict[str, Any], bool]:
    clean_user = clean_id(user_id)
    request_key = str(client_request_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", request_key):
        raise AppError("client_request_id 格式不正确")
    if not isinstance(items, list) or not 1 <= len(items) <= 20:
        raise AppError("每批必须包含 1 到 20 个款式")
    catalog = load_ecommerce_catalog()
    normalized_items = [_normalize_ecommerce_item(item, catalog) for item in items]
    selected_model = option_text(model, 120)
    batch_id = uuid.uuid4().hex
    cost_each = task_cost("image")
    total_cost = cost_each * len(normalized_items)
    ts = now_ms()
    created = False

    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT id FROM generation_batches WHERE user_id = ? AND client_request_id = ?",
            (clean_user, request_key),
        ).fetchone()
        if existing:
            batch_id = existing["id"]
        else:
            _project_id, target_canvas_id = resolve_active_workspace_target(
                conn,
                clean_user,
                canvas_id=canvas_id,
            )
            for item in normalized_items:
                _validate_ecommerce_product_asset(conn, clean_user, item["product_asset_id"])
            if total_cost:
                adjust_credits_in_transaction(
                    conn,
                    clean_user,
                    -total_cost,
                    f"电商拍摄批次扣费（{len(normalized_items)} 张）",
                )
            conn.execute(
                "INSERT INTO generation_batches "
                "(id, user_id, client_request_id, canvas_id, model, total_items, total_cost, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (batch_id, clean_user, request_key, target_canvas_id, selected_model, len(normalized_items), total_cost, ts, ts),
            )
            for index, item in enumerate(normalized_items):
                task_id = uuid.uuid4().hex
                item_key = f"item-{index + 1:03d}"
                options = normalize_task_options(
                    "image",
                    {
                        "operation": "edit",
                        "model": selected_model,
                        "ratio": item["ratio"],
                        "image_size": item["image_size"],
                        "count": 1,
                        "reference_inputs": {
                            "product_asset_id": item["product_asset_id"],
                            "model_preset_id": item["model_preset_id"],
                        },
                        "ecommerce": {
                            "environment": item["environment"],
                            "shot": item["shot"],
                            "pose": item["pose"],
                            "scene_preset_id": item["scene_preset_id"],
                            "model_preset_id": item["model_preset_id"],
                            "background_contract": (
                                ECOMMERCE_WHITE_BACKGROUND_CONTRACT
                                if item["environment"] == "white"
                                else ""
                            ),
                            "item_index": index,
                        },
                    },
                )
                conn.execute(
                    "INSERT INTO tasks "
                    "(id, user_id, kind, prompt, cost, status, canvas_id, node_id, options_json, request_id, "
                    "batch_id, batch_item_key, created_at, updated_at) "
                    "VALUES (?, ?, 'image', ?, ?, 'queued', ?, '', ?, ?, ?, ?, ?, ?)",
                    (
                        task_id,
                        clean_user,
                        ecommerce_prompt(item, catalog),
                        cost_each,
                        target_canvas_id,
                        json.dumps(options, ensure_ascii=False),
                        uuid.uuid4().hex,
                        batch_id,
                        item_key,
                        ts + index,
                        ts + index,
                    ),
                )
            created = True
    batch = get_ecommerce_batch(clean_user, batch_id)
    if not batch:
        raise AppError("电商拍摄批次创建失败", 500)
    return batch, created


def get_ecommerce_batch(user_id: str, batch_id: str) -> Optional[Dict[str, Any]]:
    clean_user = clean_id(user_id)
    clean_batch = clean_id(batch_id)
    with db() as conn:
        batch = conn.execute(
            "SELECT * FROM generation_batches WHERE user_id = ? AND id = ?",
            (clean_user, clean_batch),
        ).fetchone()
        if not batch:
            return None
        rows = conn.execute(
            "SELECT * FROM tasks WHERE user_id = ? AND batch_id = ? ORDER BY batch_item_key",
            (clean_user, clean_batch),
        ).fetchall()
    tasks = [task for row in rows if (task := task_from_row(row))]
    counts = {status: sum(task.get("status") == status for task in tasks) for status in ("queued", "running", "succeeded", "failed")}
    if tasks and counts["succeeded"] == len(tasks):
        status = "succeeded"
    elif tasks and counts["failed"] == len(tasks):
        status = "failed"
    elif counts["queued"] or counts["running"]:
        status = "running" if counts["running"] or counts["succeeded"] or counts["failed"] else "queued"
    else:
        status = "partial"
    safe_tasks = []
    for task in tasks:
        task_options = task.get("options") or {}
        reference_inputs = task_options.get("reference_inputs") or {}
        safe_tasks.append(
            {
                "id": task["id"],
                "batch_item_key": task.get("batch_item_key", ""),
                "status": task["status"],
                "cost": task["cost"],
                "error": task.get("error", ""),
                "result": task.get("result") or {},
                "product_asset_id": clean_id(reference_inputs.get("product_asset_id")),
                "ecommerce": task_options.get("ecommerce") or {},
                "created_at": task["created_at"],
                "updated_at": task["updated_at"],
            }
        )
    return {
        "id": batch["id"],
        "client_request_id": batch["client_request_id"],
        "canvas_id": batch["canvas_id"],
        "model": batch["model"],
        "total_items": batch["total_items"],
        "total_cost": batch["total_cost"],
        "status": status,
        "counts": counts,
        "tasks": safe_tasks,
        "created_at": batch["created_at"],
        "updated_at": batch["updated_at"],
    }


def list_ecommerce_batches(
    user_id: str,
    canvas_id: str = "",
    active_only: bool = False,
    limit: int = 10,
) -> list[Dict[str, Any]]:
    clean_user = clean_id(user_id)
    clean_canvas = clean_id(canvas_id)
    safe_limit = max(1, min(int(limit), 20))
    clauses = ["batch.user_id = ?"]
    params: list[Any] = [clean_user]
    if clean_canvas:
        clauses.append("batch.canvas_id = ?")
        params.append(clean_canvas)
    if active_only:
        clauses.append(
            "EXISTS ("
            "SELECT 1 FROM tasks task "
            "WHERE task.user_id = batch.user_id AND task.batch_id = batch.id "
            "AND task.status IN ('queued', 'running')"
            ")"
        )
    params.append(safe_limit)
    with db() as conn:
        rows = conn.execute(
            "SELECT batch.id FROM generation_batches batch "
            f"WHERE {' AND '.join(clauses)} "
            "ORDER BY batch.created_at DESC, batch.id DESC LIMIT ?",
            tuple(params),
        ).fetchall()
    batches = []
    for row in rows:
        batch = get_ecommerce_batch(clean_user, row["id"])
        if batch and (not active_only or batch["status"] in {"queued", "running"}):
            batches.append(batch)
    return batches


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
    task_id = uuid.uuid4().hex
    request_id = uuid.uuid4().hex
    ts = now_ms()
    normalized_options = normalize_task_options(kind, options)
    normalized_options.pop("provider", None)
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        _project_id, target_canvas_id = resolve_active_workspace_target(
            conn,
            clean,
            canvas_id=canvas_id,
        )
        if cost:
            adjust_credits_in_transaction(conn, clean, -cost, f"{kind} 任务扣费")
        conn.execute(
            "INSERT INTO tasks (id, user_id, kind, prompt, cost, status, canvas_id, node_id, options_json, request_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                task_id,
                clean,
                kind,
                str(prompt or "")[:20000],
                cost,
                "queued",
                target_canvas_id,
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


def normalize_video_output_fps(value: Any) -> int:
    try:
        fps = int(float(value or 0))
    except (TypeError, ValueError):
        return 0
    return fps if fps in {30, 60} else 0


def local_ffmpeg_exe() -> str:
    executable = shutil.which("ffmpeg")
    if executable:
        return executable
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return ""


def interpolate_video_file_sync(source: Path, target: Path, target_fps: int) -> None:
    fps = normalize_video_output_fps(target_fps)
    if not fps:
        raise RuntimeError("视频补帧仅支持 30fps 或 60fps")
    ffmpeg = local_ffmpeg_exe()
    if not ffmpeg:
        raise RuntimeError("缺少 FFmpeg，无法完成 30/60fps 补帧")
    target.parent.mkdir(parents=True, exist_ok=True)
    filter_value = f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        filter_value,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(target),
    ]
    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=max(30, int_env("VIDEO_INTERPOLATION_TIMEOUT_SECONDS", 1800)),
    )
    if process.returncode != 0:
        target.unlink(missing_ok=True)
        detail = str(process.stderr or process.stdout or "")[-1200:].strip()
        raise RuntimeError(f"视频补帧失败：{detail or 'FFmpeg 执行失败'}")
    if not target.is_file() or target.stat().st_size <= 0:
        target.unlink(missing_ok=True)
        raise RuntimeError("视频补帧失败：输出文件为空")
    if target.stat().st_size > max_output_bytes():
        target.unlink(missing_ok=True)
        raise RuntimeError(f"补帧结果超过 {int_env('MAX_OUTPUT_MB', 500)}MB")


async def interpolate_video_file(source: Path, target: Path, target_fps: int) -> None:
    await asyncio.to_thread(interpolate_video_file_sync, source, target, target_fps)


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


def ecommerce_task_requires_neutral_white(task: Dict[str, Any]) -> bool:
    if task.get("kind") != "image":
        return False
    options = normalize_task_options("image", task.get("options") or {})
    ecommerce = options.get("ecommerce") if isinstance(options.get("ecommerce"), dict) else {}
    return (
        ecommerce.get("environment") == "white"
        and ecommerce.get("background_contract") == ECOMMERCE_WHITE_BACKGROUND_CONTRACT
    )


def inspect_ecommerce_white_background(path: Path) -> Dict[str, Any]:
    """Gate delivery using only the outer background; never recolor product pixels."""
    try:
        with Image.open(path) as source:
            source.seek(0)
            image = ImageOps.exif_transpose(source).convert("RGB")
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise RuntimeError("白底质量检查无法读取生成图片") from exc

    image.thumbnail((320, 320), Image.Resampling.LANCZOS)
    width, height = image.size
    if width < 16 or height < 16:
        raise RuntimeError("白底质量检查无法处理尺寸过小的生成图片")

    patch_width = max(2, int(round(width * 0.08)))
    patch_height = max(2, int(round(height * 0.08)))
    corner_regions = (
        (0, 0, patch_width, patch_height),
        (width - patch_width, 0, width, patch_height),
        (0, height - patch_height, patch_width, height),
        (width - patch_width, height - patch_height, width, height),
    )
    edge_thickness = max(2, int(round(min(width, height) * 0.04)))
    perimeter_regions = (
        (0, 0, width, edge_thickness),
        (0, height - edge_thickness, width, height),
        (0, edge_thickness, edge_thickness, height - edge_thickness),
        (width - edge_thickness, edge_thickness, width, height - edge_thickness),
    )

    def pixel_metrics(pixel: tuple[int, int, int]) -> tuple[float, float, float]:
        red, green, blue = pixel
        luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        channel_spread = float(max(pixel) - min(pixel))
        yellow_bias = ((red + green) / 2.0) - blue
        return luminance, channel_spread, yellow_bias

    def flattened_pixels(crop: Image.Image) -> list[tuple[int, int, int]]:
        return list(
            crop.get_flattened_data()
            if hasattr(crop, "get_flattened_data")
            else crop.getdata()
        )

    def region_report(pixels: list[tuple[int, int, int]]) -> Dict[str, Any]:
        values = [pixel_metrics(pixel) for pixel in pixels]
        count = max(1, len(values))
        return {
            "mean_luminance": round(sum(value[0] for value in values) / count, 2),
            "mean_channel_spread": round(sum(value[1] for value in values) / count, 2),
            "mean_yellow_bias": round(sum(value[2] for value in values) / count, 2),
            "neutral_white_coverage": round(
                sum(
                    value[0] >= 242.0 and value[1] <= 10.0 and abs(value[2]) <= 7.0
                    for value in values
                )
                / count,
                4,
            ),
        }

    corner_reports = []
    for region in corner_regions:
        crop = image.crop(region)
        corner_reports.append(region_report(flattened_pixels(crop)))

    perimeter_pixels: list[tuple[int, int, int]] = []
    for region in perimeter_regions:
        perimeter_pixels.extend(flattened_pixels(image.crop(region)))
    values = [pixel_metrics(pixel) for pixel in perimeter_pixels]
    count = max(1, len(values))
    coverage = sum(
        value[0] >= 242.0 and value[1] <= 10.0 and abs(value[2]) <= 7.0
        for value in values
    ) / count
    mean_luminance = sum(value[0] for value in values) / count
    mean_channel_spread = sum(value[1] for value in values) / count
    mean_yellow_bias = sum(value[2] for value in values) / count
    passed = (
        coverage >= 0.9
        and mean_luminance >= 244.0
        and mean_channel_spread <= 8.0
        and abs(mean_yellow_bias) <= 5.0
        and all(
            report["mean_luminance"] >= 241.0
            and report["mean_channel_spread"] <= 10.0
            and abs(report["mean_yellow_bias"]) <= 7.0
            and report["neutral_white_coverage"] >= 0.78
            for report in corner_reports
        )
    )
    return {
        "contract": ECOMMERCE_WHITE_BACKGROUND_CONTRACT,
        "passed": passed,
        "sample": "perimeter-4-percent-plus-four-corners-8-percent",
        "edge_thickness_percent": 0.04,
        "mean_luminance": round(mean_luminance, 2),
        "mean_channel_spread": round(mean_channel_spread, 2),
        "mean_yellow_bias": round(mean_yellow_bias, 2),
        "neutral_white_coverage": round(coverage, 4),
        "corners": corner_reports,
    }


async def persist_generated_assets(task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    if task.get("kind") == "video" and str(result.get("video_url") or "").strip():
        media_items = [{"url": str(result["video_url"]).strip(), "kind": "video"}]
    else:
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
    output_fps = normalize_video_output_fps((task.get("options") or {}).get("output_fps"))
    requires_neutral_white = ecommerce_task_requires_neutral_white(task)
    persisted: list[Dict[str, Any]] = []
    staged: list[Dict[str, Any]] = []
    try:
        for index, media in enumerate(media_items):
            kind = media.get("kind") if media.get("kind") in {"image", "video"} else task.get("kind")
            asset_id = clean_id(f"task_{task['id']}_{index}")
            temporary = output_dir / f".{asset_id}.{uuid.uuid4().hex}.part"
            interpolated: Optional[Path] = None
            try:
                suffix, _size = await stream_generated_media_to_path(media["url"], kind, temporary, user_id)
                white_background_quality = None
                if kind == "image" and requires_neutral_white:
                    white_background_quality = await asyncio.to_thread(
                        inspect_ecommerce_white_background,
                        temporary,
                    )
                    if not white_background_quality["passed"]:
                        raise EcommerceWhiteBackgroundQualityError(white_background_quality)
                if kind == "video" and output_fps:
                    interpolated = output_dir / f".{asset_id}.{uuid.uuid4().hex}.interpolated.mp4"
                    await interpolate_video_file(temporary, interpolated, output_fps)
                    temporary.unlink(missing_ok=True)
                    temporary = interpolated
                    suffix = ".mp4"
                    if user_storage_usage_bytes(user_id) > max_user_storage_bytes():
                        raise AppError(
                            f"用户存储空间不足，当前上限为 {int_env('MAX_USER_STORAGE_MB', 2048)}MB",
                            413,
                        )
            except Exception:
                temporary.unlink(missing_ok=True)
                if interpolated and interpolated != temporary:
                    interpolated.unlink(missing_ok=True)
                raise
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
                    "white_background_quality": white_background_quality,
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
    response = {"items": persisted, "raw": sanitized_upstream_result(result)}
    if requires_neutral_white:
        response["white_background_quality"] = {
            "contract": ECOMMERCE_WHITE_BACKGROUND_CONTRACT,
            "status": "passed",
            "items": [
                item["white_background_quality"]
                for item in staged
                if item.get("white_background_quality")
            ],
        }
    if output_fps and any(item["kind"] == "video" for item in persisted):
        response["frame_interpolation"] = {
            "target_fps": output_fps,
            "method": "ffmpeg_minterpolate",
        }
    return response


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


def encode_video_reference_image(path: Path) -> str:
    """Create a provider-safe inline JPEG instead of forwarding large source files."""
    def validate_dimensions(image: Image.Image) -> None:
        width, height = image.size
        if width <= 0 or height <= 0:
            raise AppError("视频参考图尺寸无效")
        if width > 8192 or height > 8192 or width * height > 24_000_000:
            raise AppError("视频参考图尺寸过大，宽高不能超过 8192px 且总像素不能超过 2400 万", 413)
        ratio = width / height
        if ratio < 0.4 or ratio > 2.5:
            raise AppError("视频参考图宽高比必须在 0.4 到 2.5 之间")

    try:
        with Image.open(path) as source:
            source.seek(0)
            validate_dimensions(source)
            image = ImageOps.exif_transpose(source)
            validate_dimensions(image)
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise AppError("视频参考图无法读取，请重新上传 JPG、PNG 或 WebP 图片") from exc

    image.thumbnail(
        (VIDEO_REFERENCE_INLINE_MAX_SIDE, VIDEO_REFERENCE_INLINE_MAX_SIDE),
        Image.Resampling.LANCZOS,
    )
    if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
        rgba = image.convert("RGBA")
        flattened = Image.new("RGB", rgba.size, "white")
        flattened.paste(rgba, mask=rgba.getchannel("A"))
        image = flattened
    else:
        image = image.convert("RGB")

    encoded = b""
    quality = 84
    while True:
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=quality, optimize=True)
        encoded = output.getvalue()
        if len(encoded) <= VIDEO_REFERENCE_INLINE_MAX_BYTES:
            break
        if quality > 60:
            quality -= 8
            continue
        width, height = image.size
        if max(width, height) <= 512:
            raise AppError("视频参考图压缩后仍过大，请换用尺寸更小的图片", 413)
        image = image.resize(
            (max(1, int(width * 0.8)), max(1, int(height * 0.8))),
            Image.Resampling.LANCZOS,
        )
        quality = 76

    return f"data:image/jpeg;base64,{base64.b64encode(encoded).decode('ascii')}"


def resolve_video_reference_images(user_id: str, asset_ids: Any) -> list[str]:
    requested = []
    for value in asset_ids if isinstance(asset_ids, list) else []:
        asset_id = clean_id(value)
        if asset_id and asset_id not in requested:
            requested.append(asset_id)
        if len(requested) >= 3:
            break
    if not requested:
        return []

    root = Path(user_storage_path(user_id)).resolve()
    references = []
    with db() as conn:
        for asset_id in requested:
            row = conn.execute(
                "SELECT kind, path FROM assets WHERE user_id = ? AND id = ?",
                (clean_id(user_id), asset_id),
            ).fetchone()
            if not row:
                raise AppError(f"参考素材不存在：{asset_id}", 404)
            if row["kind"] != "image":
                raise AppError("视频参考素材必须是图片")
            target = Path(str(row["path"] or "")).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                raise AppError(f"参考素材不存在：{asset_id}", 404)
            if target.suffix.lower() not in VIDEO_REFERENCE_MIME_TYPES:
                raise AppError("视频参考图仅支持 JPG、PNG 或 WebP")
            if target.stat().st_size > 30 * 1024 * 1024:
                raise AppError("视频参考图不能超过 30MB", 413)
            references.append(encode_video_reference_image(target))
    return references


def resolve_video_reference_image_roles(user_id: str, options: Optional[Dict[str, Any]]) -> Dict[str, str]:
    values = normalize_task_options("video", options)
    resolved: Dict[str, str] = {}
    for role, option_key in VIDEO_REFERENCE_ROLE_KEYS:
        asset_id = values.get(option_key, "")
        if not asset_id:
            continue
        resolved[role] = resolve_video_reference_images(user_id, [asset_id])[0]
    return resolved


def validate_video_task_submission(user_id: str, options: Optional[Dict[str, Any]]) -> None:
    values = normalize_task_options("video", options)
    try:
        config = resolve_generation_provider_config("video", values.get("model", ""))
    except RuntimeError as exc:
        raise AppError(str(exc), 400) from exc
    asset_roles = {
        role: values[option_key]
        for role, option_key in VIDEO_REFERENCE_ROLE_KEYS
        if values.get(option_key)
    }
    validate_video_reference_capabilities(values, config, asset_roles)
    if asset_roles:
        resolve_video_reference_image_roles(user_id, values)


def update_task_status(task_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: str = "") -> None:
    terminal = status in {"succeeded", "failed"}
    with db() as conn:
        ts = now_ms()
        conn.execute(
            "UPDATE tasks SET status = ?, result_json = ?, error = ?, lease_until = ?, worker_id = ?, updated_at = ? WHERE id = ?",
            (
                status,
                json.dumps(result or {}, ensure_ascii=False),
                str(error or "")[:2000],
                0 if terminal else ts + int_env("TASK_LEASE_SECONDS", 120) * 1000,
                "" if terminal else WORKER_ID,
                ts,
                clean_id(task_id),
            ),
        )
        conn.execute(
            "UPDATE generation_batches SET updated_at = ? WHERE id = "
            "(SELECT batch_id FROM tasks WHERE id = ?) AND (SELECT batch_id FROM tasks WHERE id = ?) <> ''",
            (ts, clean_id(task_id), clean_id(task_id)),
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
        conn.execute(
            "UPDATE generation_batches SET updated_at = ? WHERE id = "
            "(SELECT batch_id FROM tasks WHERE id = ?) AND (SELECT batch_id FROM tasks WHERE id = ?) <> ''",
            (ts, clean, clean),
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
            normalized_image_options = normalize_task_options("image", options)
            requires_neutral_white = ecommerce_task_requires_neutral_white(task)
            attempts = 2 if requires_neutral_white else 1
            reference_paths = (
                resolve_image_edit_reference_paths(task["user_id"], options)
                if normalized_image_options.get("operation") == "edit"
                else []
            )
            for attempt_index in range(attempts):
                attempt_request_id = request_id if attempt_index == 0 else f"{request_id}-white-retry"
                attempt_prompt = task["prompt"]
                if attempt_index:
                    attempt_prompt += (
                        "\n白底质量重试：上一结果未通过中性纯白检测。背景必须均匀为 sRGB #FFFFFF，"
                        "禁止暖白、米黄、奶油色、灰白、渐变和任何黄色光污染。"
                    )
                try:
                    if normalized_image_options.get("operation") == "edit":
                        result = await call_image_edit(
                            attempt_prompt,
                            options,
                            reference_paths,
                            attempt_request_id,
                        )
                    else:
                        result = await call_image(attempt_prompt, options, attempt_request_id)
                    result = await persist_generated_assets(task, result)
                    break
                except EcommerceWhiteBackgroundQualityError:
                    if attempt_index + 1 >= attempts:
                        raise
        else:
            reference_images = resolve_video_reference_image_roles(task["user_id"], options)
            result = await call_video(task["prompt"], options, request_id, reference_images)
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


def is_deployment_url(url: str) -> bool:
    return "/deployments/" in urlparse(str(url or "")).path


def request_headers(api_key: str, request_id: str = "", url: str = "") -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    if is_deployment_url(url):
        headers["api-key"] = api_key
    if request_id:
        headers["Idempotency-Key"] = request_id
        headers["X-Request-ID"] = request_id
    return headers


def build_llm_payload(prompt: str, options: Optional[Dict[str, Any]] = None, url: str = "") -> Dict[str, Any]:
    values = normalize_task_options("llm", options)
    model = values.get("model") or str(os.getenv("LLM_MODEL") or "gpt-4o-mini").strip()
    system_prompt = values.get("system_prompt") or "You are a concise production assistant."
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    }
    if model and not is_deployment_url(url):
        payload["model"] = model
    return payload


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


def image_edit_url(generation_url: str) -> str:
    parsed = urlparse(str(generation_url or "").strip())
    path = parsed.path.rstrip("/")
    if not path.endswith("/images/generations"):
        raise AppError(
            "当前生图供应商未配置兼容的 images/generations 地址，无法使用电商拍摄编辑能力",
            400,
        )
    edit_path = path[: -len("generations")] + "edits"
    return parsed._replace(path=edit_path).geturl()


def resolve_image_edit_reference_paths(user_id: str, options: Optional[Dict[str, Any]]) -> list[Path]:
    values = normalize_task_options("image", options)
    if values.get("operation") != "edit":
        return []
    references = values.get("reference_inputs") if isinstance(values.get("reference_inputs"), dict) else {}
    product_asset_id = clean_id(references.get("product_asset_id"))
    if not product_asset_id:
        raise AppError("电商拍摄缺少商品参考图")
    with db() as conn:
        row = _validate_ecommerce_product_asset(conn, user_id, product_asset_id)
    paths = [Path(str(row["path"])).resolve()]
    model_preset_id = clean_id(references.get("model_preset_id"))
    if model_preset_id:
        model = next((entry for entry in load_ecommerce_catalog()["models"] if entry["id"] == model_preset_id), None)
        if not model:
            raise AppError("电商模特参考图不存在", 404)
        model_path = Path(model["_path"]).resolve()
        if not model_path.is_relative_to(ECOMMERCE_MODEL_ROOT.resolve()) or not model_path.is_file():
            raise AppError("电商模特参考图路径不安全", 503)
        paths.append(model_path)
    return paths


def provider_image_part(path: Path, index: int) -> tuple[str, bytes, str]:
    target = Path(path).resolve()
    if not target.is_file():
        raise AppError("图片参考文件不存在", 404)
    if target.stat().st_size > 50 * 1024 * 1024:
        raise AppError("单张图片参考不能超过 50MB", 413)
    suffix = target.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return (target.name or f"reference-{index}.jpg", target.read_bytes(), "image/jpeg")
    if suffix == ".png":
        return (target.name or f"reference-{index}.png", target.read_bytes(), "image/png")
    try:
        with Image.open(target) as source:
            source.seek(0)
            image = ImageOps.exif_transpose(source).convert("RGBA")
            output = io.BytesIO()
            image.save(output, format="PNG", optimize=True)
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise AppError("图片参考无法读取，请重新上传 JPG、PNG、WebP 或 AVIF 图片") from exc
    encoded = output.getvalue()
    if len(encoded) > 50 * 1024 * 1024:
        raise AppError("图片参考转换后超过 50MB", 413)
    return (f"reference-{index}.png", encoded, "image/png")


def known_image_response_items(data: Any) -> list[Dict[str, str]]:
    raw_items = data.get("data") if isinstance(data, dict) else None
    items: list[Dict[str, str]] = []
    for raw in raw_items if isinstance(raw_items, list) else []:
        if not isinstance(raw, dict):
            continue
        item: Dict[str, str] = {}
        for key in ("b64_json", "url", "revised_prompt"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                item[key] = value.strip()
        if item.get("b64_json") or item.get("url"):
            items.append(item)
    return items


async def call_image_edit(
    prompt: str,
    options: Optional[Dict[str, Any]],
    reference_paths: list[Path],
    request_id: str = "",
) -> Dict[str, Any]:
    if not reference_paths:
        raise AppError("电商拍摄缺少图片参考")
    values = normalize_task_options("image", options)
    config = resolve_generation_provider_config("image", values.get("model", ""))
    if runtime_provider_model("image", config):
        values["model"] = runtime_provider_model("image", config)
    url = image_edit_url(config["url"])
    data: Dict[str, str] = {"prompt": str(prompt or ""), "n": "1"}
    size = image_dimensions(values.get("ratio", "1:1"), values.get("image_size", "自适应"))
    if size:
        data["size"] = size
    model = values.get("model") or str(os.getenv("IMAGE_MODEL") or "gpt-image-1").strip()
    if model and not is_deployment_url(url):
        data["model"] = model
    files = [
        ("image[]", provider_image_part(path, index))
        for index, path in enumerate(reference_paths, start=1)
    ]
    try:
        async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
            resp = await client.post(
                url,
                headers=request_headers(config["api_key"], request_id, url),
                data=data,
                files=files,
            )
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPStatusError as exc:
        status = int(exc.response.status_code)
        detail = str(exc.response.text or "").strip()[:600]
        unsupported = status in {404, 405, 501} or any(
            phrase in detail.lower() for phrase in ("not supported", "unsupported", "unknown endpoint")
        )
        if unsupported:
            raise RuntimeError(
                "当前生图供应商或模型不支持图片编辑（images/edits），请在管理员后台配置支持编辑的接口"
            ) from exc
        raise RuntimeError(f"图片编辑请求失败（HTTP {status}）：{detail or '供应商未返回错误详情'}") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError(f"图片编辑请求失败：{str(exc)[:600]}") from exc
    items = known_image_response_items(payload)
    if not items:
        raise RuntimeError("图片编辑接口未返回可用的图片结果")
    return {"raw": {"data": items}, "items": items}


def normalized_video_reference_image_roles(
    options: Optional[Dict[str, Any]],
    reference_images: Any,
) -> Dict[str, str]:
    values = normalize_task_options("video", options)
    if isinstance(reference_images, dict):
        roles: Dict[str, str] = {}
        for role, _option_key in VIDEO_REFERENCE_ROLE_KEYS:
            value = reference_images.get(role)
            if role == "reference_image" and not value:
                value = reference_images.get("strong_reference")
            clean_value = str(value or "").strip()
            if clean_value:
                roles[role] = clean_value
        return roles

    references = [str(value or "").strip() for value in reference_images or [] if str(value or "").strip()]
    if not references:
        return {}
    roles = {"first_frame": references[0]}
    if len(references) > 1:
        roles["last_frame" if values.get("first_last_frame") else "reference_image"] = references[1]
    if len(references) > 2:
        roles["last_frame"] = references[2]
    return roles


def video_prompt_with_strong_reference_alias(
    prompt: str,
    options: Optional[Dict[str, Any]],
    reference_images: Dict[str, str],
) -> str:
    rendered = " ".join(str(prompt or "").splitlines()).strip()
    alias_pattern = "|".join(re.escape(alias) for alias in sorted(VIDEO_STRONG_REFERENCE_ALIASES))
    semantic_token = rf"@(?:{alias_pattern})1(?!\d)"
    has_strong_reference = bool(reference_images.get("first_frame") and reference_images.get("reference_image"))
    if not has_strong_reference:
        return re.sub(rf"\s*{semantic_token}\s*", " ", rendered).strip()

    rendered = re.sub(semantic_token, "@图片2", rendered)
    prefix: list[str] = []
    if "@图片1" not in rendered:
        prefix.append("以 @图片1 为画面参考")
    if "@图片2" not in rendered:
        alias = normalize_task_options("video", options).get("strong_reference_alias", "主体") or "主体"
        prefix.append(f"保持 @图片2 的{alias}特征一致")
    if prefix:
        rendered = "，".join(prefix) + "。" + rendered
    return rendered


def video_output_url(data: Any) -> str:
    """Extract only an explicit generated video URL, never echoed input media."""
    if not isinstance(data, dict):
        return ""
    containers = [data]
    for key in ("data", "result", "output"):
        value = data.get(key)
        if isinstance(value, dict):
            containers.append(value)
    for container in containers:
        candidates: list[Any] = [
            container.get("video_url"),
            container.get("output_url"),
            container.get("download_url"),
        ]
        content = container.get("content")
        if isinstance(content, dict):
            candidates.extend(
                [
                    content.get("video_url"),
                    content.get("output_url"),
                    content.get("download_url"),
                ]
            )
        for candidate in candidates:
            url = str(candidate or "").strip()
            if url.startswith("data:video") or re.match(r"^https?://", url) or url.startswith("/api/assets/"):
                return url
    return ""


def validate_video_reference_capabilities(
    options: Optional[Dict[str, Any]],
    config: Dict[str, Any],
    reference_images: Dict[str, str],
) -> None:
    values = normalize_task_options("video", options)
    capabilities = video_model_capability(config)
    model = runtime_provider_model("video", config) or values.get("model") or "当前模型"
    mode = values.get("mode", "text_to_video")

    if mode == "image_to_video" and not capabilities["image_to_video"]:
        raise AppError(f"视频模型 {model} 暂不支持图生视频", 400)
    if reference_images and not capabilities["image_to_video"]:
        raise AppError(f"视频模型 {model} 暂不支持图片参考", 400)
    if reference_images and mode != "image_to_video":
        raise AppError("包含图片参考的任务必须使用图生视频模式", 400)
    if mode == "image_to_video" and not reference_images.get("first_frame"):
        raise AppError("图生视频必须提供首帧图片", 400)
    if reference_images.get("reference_image"):
        if not capabilities["strong_reference"]:
            raise AppError(f"视频模型 {model} 暂不支持强参考", 400)
        if not reference_images.get("first_frame"):
            raise AppError("强参考必须与首帧图片一起使用", 400)
        if values.get("first_last_frame") or reference_images.get("last_frame"):
            raise AppError("强参考不能与首尾帧模式同时使用", 400)
    if values.get("first_last_frame") or reference_images.get("last_frame"):
        if not capabilities["first_last_frame"]:
            raise AppError(f"视频模型 {model} 暂不支持首尾帧", 400)
        if not reference_images.get("first_frame") or not reference_images.get("last_frame"):
            raise AppError("首尾帧模式必须同时提供首帧和尾帧图片", 400)
    if len(reference_images) > capabilities["max_images"]:
        raise AppError(f"视频模型 {model} 最多支持 {capabilities['max_images']} 张图片", 400)


def build_video_payload(
    prompt: str,
    options: Optional[Dict[str, Any]] = None,
    reference_images: Any = None,
) -> Dict[str, Any]:
    values = normalize_task_options("video", options)
    model = values.get("model") or str(os.getenv("VIDEO_MODEL") or "seedance-2.0").strip()
    reference_roles = normalized_video_reference_image_roles(values, reference_images)
    rendered_prompt = video_prompt_with_strong_reference_alias(prompt, values, reference_roles)
    if values.get("provider") == "灵境API":
        validate_video_reference_capabilities(
            values,
            {"provider": "灵境API", "model": model},
            reference_roles,
        )
        content: list[Dict[str, Any]] = [{"type": "text", "text": rendered_prompt}]
        if reference_roles.get("reference_image"):
            image_content = [
                ("reference_image", reference_roles.get("first_frame")),
                ("reference_image", reference_roles.get("reference_image")),
            ]
        else:
            image_content = [
                ("first_frame", reference_roles.get("first_frame")),
                ("last_frame", reference_roles.get("last_frame")),
            ]
        for role, url in image_content:
            if not url:
                continue
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": url},
                    "role": role,
                }
            )
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": rendered_prompt,
            "content": content,
            "duration": values.get("duration", 5),
            "ratio": values.get("aspect_ratio", "16:9"),
            "generate_audio": bool(values.get("generate_audio")),
            "watermark": False,
        }
        resolution = values.get("resolution", "Auto")
        if resolution not in {"", "Auto", "auto"}:
            payload["resolution"] = resolution
        if values.get("fixed_camera"):
            payload["camerafixed"] = True
        return payload

    if reference_roles:
        raise AppError(f"视频模型 {model} 的当前供应商暂不支持图片参考", 400)

    payload: Dict[str, Any] = {
        "model": model,
        "prompt": str(prompt or ""),
        "mode": values.get("mode", "text_to_video"),
        "duration": values.get("duration", 5),
        "aspect_ratio": values.get("aspect_ratio", "16:9"),
    }
    resolution = values.get("resolution", "Auto")
    if resolution not in {"", "Auto", "auto"}:
        payload["resolution"] = resolution
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
    config = resolve_generation_provider_config("llm", values.get("model", ""))
    if runtime_provider_model("llm", config):
        values["model"] = runtime_provider_model("llm", config)
    payload = build_llm_payload(prompt, values, config["url"])
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        resp = await client.post(
            config["url"],
            headers=request_headers(config["api_key"], request_id, config["url"]),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
    text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return {"text": text, "raw": data}


async def call_image(prompt: str, options: Optional[Dict[str, Any]] = None, request_id: str = "") -> Dict[str, Any]:
    values = normalize_task_options("image", options)
    config = resolve_generation_provider_config("image", values.get("model", ""))
    if runtime_provider_model("image", config):
        values["model"] = runtime_provider_model("image", config)
    payload = build_image_payload(prompt, values, config["url"])
    async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
        resp = await client.post(
            config["url"],
            headers=request_headers(config["api_key"], request_id, config["url"]),
            json=payload,
        )
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
    message_keys = (
        "message",
        "error_message",
        "detail",
        "fail_reason",
        "failure_reason",
        "reason",
    )

    def find_message(value: Any, depth: int = 0) -> str:
        if depth > 5:
            return ""
        if isinstance(value, dict):
            for key in message_keys:
                candidate = value.get(key)
                if isinstance(candidate, (str, int, float)):
                    message = str(candidate).strip()
                    if message:
                        return message[:1000]
            for child in value.values():
                message = find_message(child, depth + 1)
                if message:
                    return message
        elif isinstance(value, list):
            for child in value[:20]:
                message = find_message(child, depth + 1)
                if message:
                    return message
        return ""

    message = find_message(data)
    if message:
        return message
    return "上游视频任务失败"


def video_http_error(response: httpx.Response, action: str) -> RuntimeError:
    try:
        data = response.json()
    except Exception:
        data = {}
    detail = video_error_message(data) if isinstance(data, dict) and data else str(response.text or "").strip()
    detail = detail or f"HTTP {response.status_code}"
    return RuntimeError(f"{action}失败（HTTP {response.status_code}）：{detail[:1000]}")


async def call_video(
    prompt: str,
    options: Optional[Dict[str, Any]] = None,
    request_id: str = "",
    reference_images: Any = None,
) -> Dict[str, Any]:
    values = normalize_task_options("video", options)
    config = resolve_generation_provider_config("video", values.get("model", ""))
    values["provider"] = config["provider"]
    if runtime_provider_model("video", config):
        values["model"] = runtime_provider_model("video", config)
    reference_roles = normalized_video_reference_image_roles(values, reference_images)
    validate_video_reference_capabilities(values, config, reference_roles)
    payload = build_video_payload(prompt, values, reference_roles)
    async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
        resp = await client.post(config["url"], headers=request_headers(config["api_key"], request_id), json=payload)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise video_http_error(resp, "提交视频任务") from exc
        data = resp.json()
        task_id = video_task_id(data)
        if not task_id:
            direct_url = video_output_url(data)
            if direct_url:
                return {"video_url": direct_url, "raw": data, "task_id": ""}
            raise RuntimeError("上游视频接口未返回任务 ID 或视频结果")
        template = config["status_url_template"]
        if not template:
            raise RuntimeError("后台视频服务缺少状态查询地址")
        if "{task_id}" not in template:
            raise RuntimeError("视频状态查询地址必须包含 {task_id}")
        status_url = template.replace("{task_id}", quote(task_id, safe=""))
        deadline = time.monotonic() + max(1.0, float_env("VIDEO_POLL_TIMEOUT_SECONDS", 900.0))
        interval = max(0.0, float_env("VIDEO_POLL_INTERVAL_SECONDS", 3.0))
        failed_states = {"failed", "error", "cancelled", "canceled", "rejected", "expired"}
        succeeded_states = {"succeeded", "success", "completed", "done"}
        while time.monotonic() < deadline:
            try:
                status_response = await client.get(status_url, headers=request_headers(config["api_key"], request_id))
            except httpx.RequestError:
                await asyncio.sleep(interval)
                continue
            status_code = int(getattr(status_response, "status_code", 200) or 200)
            if status_code == 408 or status_code == 429 or status_code >= 500:
                await asyncio.sleep(interval)
                continue
            try:
                status_response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise video_http_error(status_response, "查询视频任务") from exc
            try:
                status_data = status_response.json()
            except Exception:
                await asyncio.sleep(interval)
                continue
            status = video_task_status(status_data)
            if status in failed_states:
                raise RuntimeError(f"{video_error_message(status_data)}（任务 ID：{task_id}）")
            output_url = video_output_url(status_data)
            if status in succeeded_states:
                if not output_url:
                    raise RuntimeError("视频任务已完成，但上游未返回视频地址")
                return {"video_url": output_url, "raw": status_data, "task_id": task_id}
            if not status and output_url:
                return {"video_url": output_url, "raw": status_data, "task_id": task_id}
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


class EcommerceBatchItemPayload(BaseModel):
    product_asset_id: str = Field(min_length=1, max_length=80)
    model_preset_id: str = Field(default="", max_length=80)
    custom_model_prompt: str = Field(default="", max_length=800)
    environment: str = Field(default="white", max_length=20)
    scene_preset_id: str = Field(default="", max_length=80)
    custom_scene_prompt: str = Field(default="", max_length=800)
    shot: str = Field(default="full", max_length=20)
    pose: str = Field(default="", max_length=400)
    ratio: str = Field(default="3:4", max_length=20)
    image_size: str = Field(default="2K", max_length=20)


class EcommerceBatchPayload(BaseModel):
    client_request_id: str = Field(min_length=1, max_length=80)
    canvas_id: str = Field(default="", max_length=80)
    items: list[EcommerceBatchItemPayload] = Field(min_length=1, max_length=20)
    model: str = Field(default="", max_length=120)


class WorkflowTemplatePayload(BaseModel):
    name: str = Field(default="", max_length=100)
    payload: Dict[str, Any] = Field(default_factory=dict)


class CreditPayload(BaseModel):
    delta: int
    reason: str = "后台手动调整"


class ProviderConfigPayload(BaseModel):
    api_key: Optional[str] = Field(default=None, max_length=2000)
    clear_api_key: bool = False
    base_url: Optional[str] = Field(default=None, max_length=2000)
    url: Optional[str] = Field(default=None, max_length=4000)
    model: Optional[str] = Field(default=None, max_length=120)
    models: Optional[list[str]] = None
    status_url_template: Optional[str] = Field(default=None, max_length=4000)


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


app = FastAPI(title="云芝画布", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    if (
        request.url.path.startswith("/static/")
        and request.query_params.get("v")
        and (200 <= response.status_code < 300 or response.status_code == 304)
    ):
        response.headers["Cache-Control"] = VERSIONED_STATIC_CACHE_CONTROL
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


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
async def readyz():
    try:
        ready = runtime_ready()
    except Exception:
        ready = False
    if not ready:
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return {"status": "ok"}


@app.get("/favicon.ico")
async def favicon():
    return Response(FAVICON_SVG, media_type="image/svg+xml")


@app.get("/")
async def home(request: Request):
    if is_admin_portal_request(request):
        return RedirectResponse("/admin", status_code=303)
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/assets")
@app.get("/account")
@app.get("/logs")
async def secondary_page(request: Request):
    if is_admin_portal_request(request):
        return RedirectResponse("/admin", status_code=303)
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/login")
async def login_page(request: Request):
    user = current_user(request)
    if user:
        destination = "/admin" if is_admin_portal_request(request) and user.get("is_admin") else "/"
        return RedirectResponse(destination, status_code=303)
    return FileResponse(STATIC_DIR / "auth.html")


@app.get("/register")
async def register_page(request: Request):
    if is_admin_portal_request(request):
        return RedirectResponse("/login", status_code=303)
    if current_user(request):
        return RedirectResponse("/", status_code=303)
    return FileResponse(STATIC_DIR / "auth.html")


@app.get("/admin")
async def admin_page(request: Request):
    require_admin_portal(request)
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    require_admin(request)
    return FileResponse(STATIC_DIR / "admin.html")


@app.post("/api/auth/register")
async def api_register(request: Request, payload: RegisterPayload):
    if is_admin_portal_request(request):
        raise HTTPException(status_code=404, detail="页面不存在")
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
    if is_admin_portal_request(request) and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="仅管理员可以登录此后台")
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
    return {
        "user": user,
        "storage": user_storage_summary(user["id"]) if user else None,
        "admin_url": admin_entry_url(request) if user and user.get("is_admin") else None,
    }


@app.post("/api/account/password")
async def api_change_password(payload: PasswordChangePayload, request: Request):
    user = require_user(request)
    change_password(user["id"], payload.current_password, payload.new_password)
    return {"ok": True}


@app.get("/api/capabilities")
async def api_capabilities(request: Request):
    require_user(request)
    return {"generation": generation_capabilities()}


@app.post("/api/demo/generations/{kind}")
async def api_demo_generation(kind: str, request: Request):
    user = require_user(request)
    target = bundled_demo_media(kind)
    normalized = kind.strip().lower()
    return {
        "asset": {
            "kind": normalized,
            "name": target.name,
            "url": f"/api/demo/media/{normalized}?v={now_ms()}",
        },
        "balance": credit_balance(user["id"]),
        "demo": True,
    }


@app.get("/api/demo/media/{kind}")
async def api_demo_media(kind: str, request: Request):
    require_user(request)
    target = bundled_demo_media(kind)
    response = FileResponse(target, filename=target.name, content_disposition_type="inline")
    response.headers["Cache-Control"] = "private, no-store"
    return response


@app.get("/api/projects")
async def api_projects(request: Request):
    user = require_user(request)
    return {"projects": list_projects(user["id"])}


@app.post("/api/projects")
async def api_create_project(payload: NamePayload, request: Request):
    user = require_user(request)
    return {"project": create_project(user["id"], payload.name)}


@app.delete("/api/projects/{project_id}")
async def api_delete_project(project_id: str, request: Request):
    user = require_user(request)
    deleted_canvas_count = delete_project(user["id"], project_id)
    return {"ok": True, "deleted_canvas_count": deleted_canvas_count}


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


@app.delete("/api/canvases/{canvas_id}")
async def api_delete_canvas(canvas_id: str, request: Request):
    user = require_user(request)
    delete_canvas(user["id"], canvas_id)
    return {"ok": True}


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
            conn.execute("BEGIN IMMEDIATE")
            target_project_id, target_canvas_id = resolve_active_workspace_target(
                conn,
                user["id"],
                project_id=project_id,
                canvas_id=canvas_id,
            )
            conn.execute(
                "INSERT INTO assets (id, user_id, project_id, canvas_id, name, kind, path, url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (asset_id, user["id"], target_project_id, target_canvas_id, file.filename or filename, kind, str(target), url, ts),
            )
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {"asset": {"id": asset_id, "name": file.filename or filename, "kind": kind, "url": url}}


@app.get("/api/assets/{asset_id}")
async def api_asset(asset_id: str, request: Request, download: bool = False):
    user = require_user(request)
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM assets WHERE user_id = ? AND id = ?",
            (user["id"], clean_id(asset_id)),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="素材不存在")
    download_name = str(row["name"] or Path(row["path"]).name).strip()
    suffix = Path(row["path"]).suffix
    if suffix and not download_name.lower().endswith(suffix.lower()):
        download_name = f"{download_name}{suffix}"
    return FileResponse(
        row["path"],
        filename=download_name,
        content_disposition_type="attachment" if download else "inline",
    )


@app.delete("/api/assets/{asset_id}")
async def api_delete_asset(asset_id: str, request: Request):
    user = require_user(request)
    if not delete_asset(user["id"], asset_id):
        raise HTTPException(status_code=404, detail="素材不存在")
    return {"ok": True, "storage": user_storage_summary(user["id"])}


@app.get("/api/ecommerce/catalog")
async def api_ecommerce_catalog(request: Request):
    require_user(request)
    return public_ecommerce_catalog()


@app.post("/api/ecommerce/batches")
async def api_create_ecommerce_batch(payload: EcommerceBatchPayload, request: Request):
    user = require_user(request)
    item_payloads = [
        item.model_dump() if hasattr(item, "model_dump") else item.dict()
        for item in payload.items
    ]
    batch, created = create_ecommerce_batch(
        user["id"],
        payload.client_request_id,
        item_payloads,
        canvas_id=payload.canvas_id,
        model=payload.model,
    )
    if created:
        wake_task_worker()
    return {
        "batch": batch,
        "created": created,
        "balance": credit_balance(user["id"]),
    }


@app.get("/api/ecommerce/batches")
async def api_ecommerce_batches(
    request: Request,
    canvas_id: str = "",
    active_only: bool = False,
    limit: int = Query(default=10, ge=1, le=20),
):
    user = require_user(request)
    return {
        "batches": list_ecommerce_batches(
            user["id"],
            canvas_id=canvas_id,
            active_only=active_only,
            limit=limit,
        ),
        "balance": credit_balance(user["id"]),
    }


@app.get("/api/ecommerce/batches/{batch_id}")
async def api_ecommerce_batch(batch_id: str, request: Request):
    user = require_user(request)
    batch = get_ecommerce_batch(user["id"], batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="电商拍摄批次不存在")
    return {"batch": batch, "balance": credit_balance(user["id"])}


@app.post("/api/tasks")
async def api_create_task(payload: TaskPayload, request: Request):
    user = require_user(request)
    if str(payload.kind or "").strip().lower() == "video":
        validate_video_task_submission(user["id"], payload.options)
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
    require_admin_portal(request)
    require_admin(request)
    with db() as conn:
        rows = conn.execute(
            """
            SELECT
                u.id,
                u.email,
                u.is_admin,
                u.credits,
                u.created_at,
                COUNT(t.id) AS task_count,
                COALESCE(SUM(CASE WHEN t.status = 'succeeded' THEN 1 ELSE 0 END), 0) AS succeeded_count,
                COALESCE(SUM(CASE WHEN t.status = 'failed' THEN 1 ELSE 0 END), 0) AS failed_count,
                COALESCE(SUM(CASE WHEN t.status IN ('queued', 'running') THEN 1 ELSE 0 END), 0) AS active_count,
                COALESCE(SUM(CASE WHEN t.status = 'succeeded' THEN t.cost ELSE 0 END), 0) AS consumed_credits,
                COALESCE(SUM(CASE WHEN t.status IN ('queued', 'running') AND t.refunded = 0 THEN t.cost ELSE 0 END), 0) AS pending_credits,
                COALESCE(SUM(CASE WHEN t.refunded = 1 THEN t.cost ELSE 0 END), 0) AS refunded_credits,
                COALESCE(SUM(CASE WHEN t.status = 'succeeded' AND t.kind = 'llm' THEN t.cost ELSE 0 END), 0) AS llm_credits,
                COALESCE(SUM(CASE WHEN t.status = 'succeeded' AND t.kind = 'image' THEN t.cost ELSE 0 END), 0) AS image_credits,
                COALESCE(SUM(CASE WHEN t.status = 'succeeded' AND t.kind = 'video' THEN t.cost ELSE 0 END), 0) AS video_credits,
                MAX(t.created_at) AS last_task_at
            FROM users u
            LEFT JOIN tasks t ON t.user_id = u.id
            GROUP BY u.id, u.email, u.is_admin, u.credits, u.created_at
            ORDER BY u.created_at DESC
            """
        ).fetchall()
    users = []
    usage_fields = (
        "task_count",
        "succeeded_count",
        "failed_count",
        "active_count",
        "consumed_credits",
        "pending_credits",
        "refunded_credits",
        "llm_credits",
        "image_credits",
        "video_credits",
    )
    for row in rows:
        raw = dict(row)
        user = public_user(raw)
        user.update({field: int(raw.get(field) or 0) for field in usage_fields})
        user["last_task_at"] = int(raw["last_task_at"]) if raw.get("last_task_at") is not None else None
        users.append(user)
    return {"users": users}


@app.post("/api/admin/users/{user_id}/credits")
async def api_admin_credits(user_id: str, payload: CreditPayload, request: Request):
    require_admin_portal(request)
    admin = require_admin(request)
    balance = adjust_credits(user_id, payload.delta, payload.reason, actor_id=admin["id"])
    return {"balance": balance}


@app.get("/api/admin/providers")
async def api_admin_providers(request: Request):
    require_admin_portal(request)
    require_admin(request)
    return {
        "providers": list_public_provider_configs(),
        "capabilities": provider_generation_capabilities(),
    }


@app.put("/api/admin/providers/{kind}/{provider}")
async def api_admin_update_provider(
    kind: str,
    provider: str,
    payload: ProviderConfigPayload,
    request: Request,
):
    require_admin_portal(request)
    require_admin(request)
    try:
        updated = update_provider_config(kind, provider, payload)
    except RuntimeError as exc:
        raise AppError(str(exc), 400) from exc
    return {
        "provider": updated,
        "capabilities": provider_generation_capabilities(),
    }


@app.post("/api/admin/providers/{kind}/{provider}/models")
async def api_admin_provider_models(kind: str, provider: str, request: Request):
    require_admin_portal(request)
    require_admin(request)
    try:
        return await fetch_provider_models(kind, provider)
    except RuntimeError as exc:
        raise AppError(str(exc), 400) from exc


@app.get("/api/admin/config")
async def api_admin_config(request: Request):
    require_admin_portal(request)
    require_admin(request)
    capabilities = generation_capabilities()
    return {
        "llm_configured": capabilities["llm"]["configured"],
        "image_configured": capabilities["image"]["configured"],
        "video_configured": capabilities["video"]["configured"],
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

