import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-only-for-automated-tests-123456")

import pytest
from fastapi.testclient import TestClient

import backend.database as database
from backend.auth import hash_password
from backend.migrations import run_migrations


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    database.initialize_database()
    run_migrations()

    from backend.main import app

    return TestClient(app)


@pytest.fixture()
def make_user(client):
    def _make(email, role, section=None, password="password123"):
        connection = database.get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO users (name, email, password_hash, role, section)
                VALUES (?, ?, ?, ?, ?)
                """,
                (email.split("@")[0], email, hash_password(password), role, section),
            )
            connection.commit()
            return cursor.lastrowid
        finally:
            connection.close()

    return _make


@pytest.fixture()
def auth_headers(client):
    def _headers(email, password="password123"):
        response = client.post("/login", json={"email": email, "password": password})
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _headers