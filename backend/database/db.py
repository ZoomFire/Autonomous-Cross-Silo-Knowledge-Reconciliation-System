from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL, STORAGE_DIR


STORAGE_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = STORAGE_DIR / "driftguard.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
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
    if DATABASE_URL.startswith("sqlite"):
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
