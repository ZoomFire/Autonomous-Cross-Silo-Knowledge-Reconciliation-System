import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback for minimal local environments
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    if load_dotenv:
        load_dotenv(env_path)
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def _unique(items: list[str]) -> list[str]:
    result = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result


_load_dotenv()

APP_NAME = os.getenv("APP_NAME", "DriftGuard AI")
APP_ENV = os.getenv("APP_ENV", "development")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = _int("APP_PORT", 8001)
USE_DATABASE = _bool("USE_DATABASE", True)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./storage/driftguard.db")
STORAGE_DIR = BASE_DIR / "storage"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").strip()
CORS_ORIGINS = _unique([
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://autonomous-cross-silo-knowledge-rec.vercel.app",
    FRONTEND_URL,
    *_list("CORS_ORIGINS", []),
])
CORS_ALLOW_ALL = _bool("CORS_ALLOW_ALL", False)
SESSION_EXPIRE_HOURS = _int("SESSION_EXPIRE_HOURS", 24)
MAX_UPLOAD_SIZE_MB = _int("MAX_UPLOAD_SIZE_MB", 25)
ENABLE_OPTIONAL_LLM = _bool("ENABLE_OPTIONAL_LLM", False)
DEFAULT_REASONING_MODE = os.getenv("DEFAULT_REASONING_MODE", "local_only")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
RATE_LIMIT_ENABLED = _bool("RATE_LIMIT_ENABLED", True)
LOGIN_RATE_LIMIT_PER_MINUTE = _int("LOGIN_RATE_LIMIT_PER_MINUTE", 10)
SIGNUP_RATE_LIMIT_PER_MINUTE = _int("SIGNUP_RATE_LIMIT_PER_MINUTE", 5)
RAG_RATE_LIMIT_PER_MINUTE = _int("RAG_RATE_LIMIT_PER_MINUTE", 30)
AGENT_RATE_LIMIT_PER_HOUR = _int("AGENT_RATE_LIMIT_PER_HOUR", 10)
UPLOAD_RATE_LIMIT_PER_HOUR = _int("UPLOAD_RATE_LIMIT_PER_HOUR", 20)
INCIDENT_AUTO_CREATE_ENABLED = _bool("INCIDENT_AUTO_CREATE_ENABLED", False)
INCIDENT_AUTO_CREATE_SEVERITIES = _list("INCIDENT_AUTO_CREATE_SEVERITIES", ["Critical", "High"])
WEBHOOK_TIMEOUT_SECONDS = _int("WEBHOOK_TIMEOUT_SECONDS", 5)
