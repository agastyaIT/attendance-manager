from datetime import datetime, timedelta, timezone

import jwt

from backend.security import ALGORITHM, SECRET_KEY


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_register_then_login(client):
    registered = client.post(
        "/register",
        json={
            "name": "Asha",
            "email": "asha@example.com",
            "password": "password123",
            "section": "A",
        },
    )
    assert registered.status_code == 200

    login = client.post(
        "/login", json={"email": "asha@example.com", "password": "password123"}
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["user"]["role"] == "student"


def test_register_cannot_choose_role(client):
    client.post(
        "/register",
        json={
            "name": "Sneaky",
            "email": "sneaky@example.com",
            "password": "password123",
            "section": "A",
            "role": "admin",
        },
    )
    login = client.post(
        "/login", json={"email": "sneaky@example.com", "password": "password123"}
    )
    assert login.json()["user"]["role"] == "student"


def test_login_wrong_password(client, make_user):
    make_user("kiran@example.com", "student", "A")
    response = client.post(
        "/login", json={"email": "kiran@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/me").status_code == 401


def test_me_rejects_invalid_token(client):
    headers = {"Authorization": "Bearer not.a.real.token"}
    assert client.get("/me", headers=headers).status_code == 401


def test_me_rejects_expired_token(client, make_user):
    user_id = make_user("old@example.com", "student", "A")
    expired = jwt.encode(
        {
            "sub": str(user_id),
            "role": "student",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    response = client.get("/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_me_hides_password_hash(client, make_user, auth_headers):
    make_user("meera@example.com", "student", "B")
    response = client.get("/me", headers=auth_headers("meera@example.com"))
    assert response.status_code == 200
    user = response.json()["user"]
    assert user["email"] == "meera@example.com"
    assert "password_hash" not in user