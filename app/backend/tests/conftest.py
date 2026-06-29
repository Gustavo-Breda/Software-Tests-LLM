import os
import pytest

from fastapi.testclient import TestClient

from src.main import create_app

os.environ["DATABASE_URL"] = "sqlite:////tmp/test_qa_poc.db"
os.environ["RESET_DB_ON_STARTUP"] = "1"
os.environ.setdefault("JWT_SECRET", "test-secret")

@pytest.fixture()
def client():
    with TestClient(create_app()) as c:
        yield c


def auth_header(client: TestClient, email: str, password: str) -> dict[str, str]:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login as {email} failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
