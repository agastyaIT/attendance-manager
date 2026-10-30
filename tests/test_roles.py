import pytest

ADMIN_ENDPOINTS = [
    ("GET", "/admin/users", None),
    ("PATCH", "/admin/users/1", {"name": "X"}),
    (
        "POST",
        "/admin/faculty",
        {"name": "F", "email": "f@example.com", "password": "password123"},
    ),
    ("GET", "/admin/subjects", None),
    (
        "POST",
        "/admin/subjects",
        {"subject_code": "X1", "subject_name": "X", "subject_type": "theory"},
    ),
    ("PATCH", "/admin/subjects/1", {"subject_name": "X"}),
    ("GET", "/admin/assignments", None),
    ("POST", "/admin/assignments", {"faculty_id": 1, "subject_id": 1, "section": "A"}),
    ("DELETE", "/admin/assignments/1", None),
    ("GET", "/admin/timetable", None),
    (
        "POST",
        "/admin/timetable",
        {
            "subject_id": 1,
            "section": "A",
            "day_of_week": 1,
            "start_time": "10:00",
            "end_time": "11:00",
        },
    ),
    ("PATCH", "/admin/timetable/1", {"room": "1"}),
    ("GET", "/admin/analytics", None),
]

STUDENT_ENDPOINTS = [
    ("GET", "/student/attendance", None),
    ("GET", "/student/attendance/1", None),
    ("GET", "/student/timetable", None),
    ("GET", "/student/analytics", None),
]


@pytest.mark.parametrize("method,path,body", ADMIN_ENDPOINTS + STUDENT_ENDPOINTS)
def test_no_token_is_rejected(client, method, path, body):
    response = client.request(method, path, json=body)
    assert response.status_code == 401


@pytest.mark.parametrize("method,path,body", ADMIN_ENDPOINTS)
def test_student_blocked_from_admin(client, make_user, auth_headers, method, path, body):
    make_user("stu@example.com", "student", "A")
    headers = auth_headers("stu@example.com")
    response = client.request(method, path, json=body, headers=headers)
    assert response.status_code == 403


@pytest.mark.parametrize("method,path,body", ADMIN_ENDPOINTS)
def test_faculty_blocked_from_admin(client, make_user, auth_headers, method, path, body):
    make_user("fac@example.com", "faculty")
    headers = auth_headers("fac@example.com")
    response = client.request(method, path, json=body, headers=headers)
    assert response.status_code == 403


@pytest.mark.parametrize("method,path,body", STUDENT_ENDPOINTS)
def test_admin_blocked_from_student_endpoints(
    client, make_user, auth_headers, method, path, body
):
    make_user("boss@example.com", "admin")
    headers = auth_headers("boss@example.com")
    response = client.request(method, path, json=body, headers=headers)
    assert response.status_code == 403


@pytest.mark.parametrize("method,path,body", STUDENT_ENDPOINTS)
def test_faculty_blocked_from_student_endpoints(
    client, make_user, auth_headers, method, path, body
):
    make_user("fac@example.com", "faculty")
    headers = auth_headers("fac@example.com")
    response = client.request(method, path, json=body, headers=headers)
    assert response.status_code == 403


def test_admin_user_list_hides_password_hashes(client, make_user, auth_headers):
    make_user("boss@example.com", "admin")
    make_user("stu@example.com", "student", "A")
    response = client.get("/admin/users", headers=auth_headers("boss@example.com"))
    assert response.status_code == 200
    users = response.json()["users"]
    assert len(users) == 2
    for user in users:
        assert "password_hash" not in user


def test_admin_cannot_change_role_through_user_update(client, make_user, auth_headers):
    make_user("boss@example.com", "admin")
    student_id = make_user("stu@example.com", "student", "A")
    headers = auth_headers("boss@example.com")

    response = client.patch(
        f"/admin/users/{student_id}", json={"role": "admin"}, headers=headers
    )
    assert response.status_code == 400

    users = client.get("/admin/users?role=student", headers=headers).json()["users"]
    assert users[0]["role"] == "student"


def test_student_sees_only_own_section_timetable(client, make_user, auth_headers):
    make_user("boss@example.com", "admin")
    make_user("stu_a@example.com", "student", "A")
    make_user("stu_b@example.com", "student", "B")
    admin_headers = auth_headers("boss@example.com")

    subject = client.post(
        "/admin/subjects",
        json={"subject_code": "T1", "subject_name": "Test", "subject_type": "theory"},
        headers=admin_headers,
    )
    subject_id = subject.json()["subject"]["id"]

    created = client.post(
        "/admin/timetable",
        json={
            "subject_id": subject_id,
            "section": "A",
            "day_of_week": 1,
            "start_time": "10:00",
            "end_time": "11:00",
        },
        headers=admin_headers,
    )
    assert created.status_code == 201

    def total_classes(email):
        data = client.get("/student/timetable", headers=auth_headers(email)).json()
        return sum(len(day["classes"]) for day in data["days"])

    assert total_classes("stu_a@example.com") == 1
    assert total_classes("stu_b@example.com") == 0
    