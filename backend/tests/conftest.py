import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models.user import User

# SQLite in-memory keeps the auth-flow tests fast and dependency-free.
# Only the `users` table is created here — Report/Match use pgvector's
# Vector column, which is Postgres-specific, so those are exercised
# against a real Postgres (see backend/scripts/dev.sh + docker-compose.yml)
# rather than in this lightweight suite.
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # single shared connection so the in-memory DB persists across sessions
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    User.__table__.create(bind=engine, checkfirst=True)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        User.__table__.drop(bind=engine, checkfirst=True)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
