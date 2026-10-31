import pytest

import backend.database as database


def change(client, headers, current="password123", new="newpassword456"):
    return client.post(
        "/me/password",
        json={"current_password": current, "new_password": new},
        headers=headers,
    )


def login(client, email, password):
    return client.post("/login", json={"email": email, "password": password})


@pytest.mark.parametrize(
    "role,section", [("student", "A"), ("faculty", None), ("admin", None)]
)
def test_any_role_can_change_own_password(
    client, make_user, auth_headers, role, section
):
    make_user("u@example.com", role, section)
    headers = auth_headers("u@example.com")

    assert change(client, headers).status_code == 200
    assert login(client, "u@example.com", "password123").status_code == 401
    assert login(client, "u@example.com", "newpassword456").status_code == 200


def test_wrong_current_password_rejected_and_nothing_changes(
    client, make_user, auth_headers
):
    make_user("u@example.com", "student", "A")
    headers = auth_headers("u@example.com")

    response = change(client, headers, current="not-my-password")
    assert response.status_code == 400
    assert login(client, "u@example.com", "password123").status_code == 200


def test_short_new_password_rejected(client, make_user, auth_headers):
    make_user("u@example.com", "student", "A")
    headers = auth_headers("u@example.com")
    assert change(client, headers, new="short").status_code == 422


def test_new_password_must_differ(client, make_user, auth_headers):
    make_user("u@example.com", "student", "A")
    headers = auth_headers("u@example.com")
    assert change(client, headers, new="password123").status_code == 400


def test_password_change_needs_login(client):
    response = client.post(
        "/me/password",
        json={"current_password": "password123", "new_password": "newpassword456"},
    )
    assert response.status_code == 401


def test_changing_one_password_does_not_affect_others(
    client, make_user, auth_headers
):
    make_user("a@example.com", "student", "A")
    make_user("b@example.com", "student", "A")

    assert change(client, auth_headers("a@example.com")).status_code == 200
    assert login(client, "b@example.com", "password123").status_code == 200


def test_new_password_is_stored_hashed(client, make_user, auth_headers):
    make_user("u@example.com", "student", "A")
    change(client, auth_headers("u@example.com"))

    connection = database.get_connection()
    try:
        stored = connection.execute(
            "SELECT password_hash FROM users WHERE email = 'u@example.com'"
        ).fetchone()["password_hash"]
    finally:
        connection.close()

    assert stored != "newpassword456"
    assert stored.startswith("$argon2")