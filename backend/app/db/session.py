import json
import sqlite3
from sqlalchemy import ARRAY, JSON, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import declarative_base, sessionmaker
from pgvector.sqlalchemy import Vector

from app.core.config import get_settings

sqlite3.register_adapter(list, json.dumps)

@compiles(ARRAY, "sqlite")
def compile_array(type_, compiler, **kw):
    return "JSON"

@compiles(Vector, "sqlite")
def compile_vector(type_, compiler, **kw):
    return "JSON"

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=not settings.DATABASE_URL.startswith("sqlite"),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session per-request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
