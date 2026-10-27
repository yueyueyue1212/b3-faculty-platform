"""Pytest fixtures for the B3 platform.

The test database is configured *before* importing app modules so that the
SQLAlchemy engine never touches the demo database under backend/data/app.db.
"""
import os
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DB = BACKEND_DIR / "data" / "test_b3.db"
for suffix in ("", "-wal", "-shm"):
    candidate = Path(str(TEST_DB) + suffix)
    if candidate.exists():
        candidate.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["AUTO_SEED_ON_STARTUP"] = "true"
os.environ["LLM_API_KEY"] = ""
os.environ["LLM_ALLOW_PERSONAL_DATA"] = "false"
os.environ["TOKEN_EXPIRE_MINUTES"] = "60"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402


def login(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(TEST_DB) + suffix)
        if candidate.exists():
            try:
                candidate.unlink()
            except PermissionError:
                pass


@pytest.fixture(scope="session")
def admin_headers(client):
    return login(client, "admin", "admin123")


@pytest.fixture(scope="session")
def manager_headers(client):
    return login(client, "manager", "manager123")


@pytest.fixture(scope="session")
def viewer_headers(client):
    return login(client, "viewer", "viewer123")
