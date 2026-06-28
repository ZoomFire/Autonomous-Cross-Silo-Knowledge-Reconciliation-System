from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL, STORAGE_DIR


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


STORAGE_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = STORAGE_DIR / "driftguard.db"
SQLALCHEMY_DATABASE_URL = _normalize_database_url(DATABASE_URL)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=not SQLALCHEMY_DATABASE_URL.startswith("sqlite"),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        with engine.begin() as connection:
            user_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(users)")).fetchall()}
            for name, sql_type, default in [
                ("failed_login_attempts", "INTEGER", "0"),
                ("locked_until", "TEXT", "''"),
                ("last_failed_login_at", "TEXT", "''"),
                ("last_login_at", "TEXT", "''"),
            ]:
                if name not in user_columns:
                    connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {sql_type} DEFAULT {default}"))
