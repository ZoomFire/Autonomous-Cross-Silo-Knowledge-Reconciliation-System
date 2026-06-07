import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import re

try:
    from passlib.context import CryptContext
except Exception:  # pragma: no cover - fallback for constrained environments
    CryptContext = None

from config import USE_DATABASE
from config import SESSION_EXPIRE_HOURS


AUTH_DIR = Path(__file__).resolve().parent / "storage" / "auth"
USERS_DIR = AUTH_DIR / "users"
SESSIONS_DIR = AUTH_DIR / "sessions"
VALID_ROLES = {"admin", "engineer", "reviewer", "viewer"}
LOCKOUT_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
PASSWORD_POLICY_MESSAGE = "Password must be at least 8 characters and include at least one letter and one number."
try:
    import bcrypt as _bcrypt_module
except Exception:  # pragma: no cover
    _bcrypt_module = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") if CryptContext and getattr(_bcrypt_module, "__about__", None) else None
if pwd_context:
    try:
        pwd_context.hash("Passw0rd!")
    except Exception:
        # Some bcrypt/passlib combinations are incompatible. Keep auth working
        # with the existing salted SHA256 fallback when bcrypt cannot initialize.
        pwd_context = None


def ensure_auth_dirs():
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _read_json(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, payload: dict):
    ensure_auth_dirs()
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def sanitize_user(user: dict) -> dict:
    return {key: value for key, value in user.items() if key not in {"password_hash", "salt"}}


def validate_password_policy(password: str) -> None:
    if len(password or "") < 8 or not re.search(r"[A-Za-z]", password or "") or not re.search(r"\d", password or ""):
        raise ValueError(PASSWORD_POLICY_MESSAGE)


def hash_password(password: str, salt: str) -> str:
    if pwd_context:
        return pwd_context.hash(password)
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    if str(password_hash).startswith("$2") and pwd_context:
        try:
            return pwd_context.verify(password, password_hash)
        except Exception:
            return False
    return secrets.compare_digest(hash_password(password, salt), password_hash)


def mask_token(token: str) -> str:
    token = token or ""
    return "****" if len(token) < 8 else f"{token[:4]}...{token[-4:]}"


def list_users(include_private: bool = False) -> list[dict]:
    if USE_DATABASE:
        from database.repositories import UserRepository

        return UserRepository.list(include_private=include_private)
    ensure_auth_dirs()
    users = []
    for path in USERS_DIR.glob("*.json"):
        user = _read_json(path)
        if user:
            users.append(user if include_private else sanitize_user(user))
    return sorted(users, key=lambda item: item.get("created_at", ""))


def has_users() -> bool:
    return bool(list_users(include_private=True))


def _find_user_by_email(email: str) -> dict | None:
    normalized = email.strip().lower()
    return next((user for user in list_users(include_private=True) if user.get("email") == normalized), None)


def get_user(user_id: str) -> dict | None:
    if USE_DATABASE:
        from database.repositories import UserRepository

        return UserRepository.get_by_id(user_id)
    ensure_auth_dirs()
    return _read_json(USERS_DIR / f"{user_id}.json")


def create_user(name: str, email: str, password: str, role: str = "viewer") -> dict:
    ensure_auth_dirs()
    if role not in VALID_ROLES:
        raise ValueError("Invalid role.")
    if _find_user_by_email(email):
        raise ValueError("A user with this email already exists.")
    if not name.strip() or not email.strip() or not password:
        raise ValueError("Name, email, and password are required.")
    validate_password_policy(password)

    salt = secrets.token_hex(16)
    now = _now_iso()
    user = {
        "user_id": str(uuid4()),
        "name": name.strip(),
        "email": email.strip().lower(),
        "password_hash": hash_password(password, salt),
        "salt": salt,
        "role": role,
        "created_at": now,
        "updated_at": now,
        "failed_login_attempts": 0,
        "locked_until": "",
        "last_failed_login_at": "",
        "last_login_at": "",
    }
    if USE_DATABASE:
        from database.repositories import UserRepository

        UserRepository.create(user)
    else:
        _write_json(USERS_DIR / f"{user['user_id']}.json", user)
    return sanitize_user(user)


def authenticate_user(email: str, password: str) -> dict | None:
    user = _find_user_by_email(email)
    if not user:
        return None
    if _is_locked(user):
        return {"locked": True, **sanitize_user(user)}
    if not verify_password(password, user.get("salt", ""), user.get("password_hash", "")):
        record_failed_login(user)
        return None
    updates = {"failed_login_attempts": 0, "locked_until": "", "last_login_at": _now_iso(), "updated_at": _now_iso()}
    if not str(user.get("password_hash", "")).startswith("$2") and pwd_context:
        updates.update({"password_hash": hash_password(password, user.get("salt", "")), "salt": ""})
    _update_user_security_fields(user["user_id"], updates)
    return sanitize_user(user)


def _is_locked(user: dict) -> bool:
    locked_until = user.get("locked_until") or ""
    if not locked_until:
        return False
    try:
        if datetime.fromisoformat(locked_until) > _now():
            return True
    except ValueError:
        return False
    _update_user_security_fields(user["user_id"], {"locked_until": "", "failed_login_attempts": 0, "updated_at": _now_iso()})
    return False


def record_failed_login(user: dict) -> dict:
    attempts = int(user.get("failed_login_attempts") or 0) + 1
    updates = {"failed_login_attempts": attempts, "last_failed_login_at": _now_iso(), "updated_at": _now_iso()}
    if attempts >= LOCKOUT_ATTEMPTS:
        updates["locked_until"] = (_now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
    return _update_user_security_fields(user["user_id"], updates) or user


def _update_user_security_fields(user_id: str, updates: dict) -> dict | None:
    if USE_DATABASE:
        from database.repositories import UserRepository

        return UserRepository.update_security_fields(user_id, updates)
    user = get_user(user_id)
    if not user:
        return None
    user.update(updates)
    _write_json(USERS_DIR / f"{user_id}.json", user)
    return sanitize_user(user)


def create_session(user_id: str) -> dict:
    ensure_auth_dirs()
    token = secrets.token_urlsafe(32)
    session = {
        "token": token,
        "user_id": user_id,
        "created_at": _now_iso(),
        "expires_at": (_now() + timedelta(hours=SESSION_EXPIRE_HOURS)).isoformat(),
    }
    if USE_DATABASE:
        from database.repositories import SessionRepository

        SessionRepository.create(session)
    else:
        _write_json(SESSIONS_DIR / f"{token}.json", session)
    return session


def list_user_sessions(user_id: str) -> list[dict]:
    ensure_auth_dirs()
    if USE_DATABASE:
        from database.repositories import SessionRepository

        sessions = SessionRepository.list_by_user(user_id)
    else:
        sessions = [session for session in (_read_json(path) for path in SESSIONS_DIR.glob("*.json")) if session and session.get("user_id") == user_id]
    now = _now()
    active = []
    for session in sessions:
        try:
            if datetime.fromisoformat(session.get("expires_at", "")) < now:
                logout_session(session.get("token", ""))
                continue
        except ValueError:
            continue
        active.append({**session, "session_id": session.get("token", ""), "masked_token": mask_token(session.get("token", ""))})
    return [{key: value for key, value in item.items() if key != "token"} for item in active]


def get_current_user(token: str) -> dict | None:
    ensure_auth_dirs()
    if not token:
        return None
    if USE_DATABASE:
        from database.repositories import SessionRepository

        session = SessionRepository.get_by_token(token)
        path = None
    else:
        path = SESSIONS_DIR / f"{token}.json"
        session = _read_json(path)
    if not session:
        return None
    try:
        expires_at = datetime.fromisoformat(session["expires_at"])
    except (KeyError, ValueError):
        if path:
            path.unlink(missing_ok=True)
        elif USE_DATABASE:
            logout_session(token)
        return None
    if expires_at < _now():
        if path:
            path.unlink(missing_ok=True)
        elif USE_DATABASE:
            logout_session(token)
        return None
    user = get_user(session.get("user_id", ""))
    return sanitize_user(user) if user else None


def logout_session(token: str) -> bool:
    if USE_DATABASE:
        from database.repositories import SessionRepository

        return SessionRepository.delete(token)
    path = SESSIONS_DIR / f"{token}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def update_user_role(user_id: str, role: str) -> dict | None:
    if role not in VALID_ROLES:
        raise ValueError("Invalid role.")
    user = get_user(user_id)
    if not user:
        return None
    if user.get("role") == "admin" and role != "admin" and _admin_count() <= 1:
        raise ValueError("Cannot remove the last admin.")
    if USE_DATABASE:
        from database.repositories import UserRepository

        return sanitize_user(UserRepository.update_role(user_id, role))
    user["role"] = role
    user["updated_at"] = _now_iso()
    _write_json(USERS_DIR / f"{user_id}.json", user)
    return sanitize_user(user)


def _admin_count() -> int:
    return sum(1 for user in list_users(include_private=True) if user.get("role") == "admin")


def delete_user(user_id: str) -> bool:
    user = get_user(user_id)
    if not user:
        return False
    if user.get("role") == "admin" and _admin_count() <= 1:
        raise ValueError("Cannot delete the last admin.")
    if USE_DATABASE:
        from database.repositories import SessionRepository, UserRepository

        SessionRepository.delete_for_user(user_id)
        return UserRepository.delete(user_id)
    (USERS_DIR / f"{user_id}.json").unlink()
    for session_path in SESSIONS_DIR.glob("*.json"):
        session = _read_json(session_path)
        if session and session.get("user_id") == user_id:
            session_path.unlink(missing_ok=True)
    return True
