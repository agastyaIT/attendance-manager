from datetime import date, timedelta

import pytest

import backend.database as database


def session_body(subject_id, section="A", days_ago=1, start="10:00", end="11:00"):
    return {
        "subject_id": subject_id,
        "section": section,
        "session_date": (date.today() - timedelta(days=days_ago)).isoformat(),
        "start_time": start,
        "end_time": end,
    }


@pytest.fixture()
def env(client, make_user, auth_headers):
    make_user("boss@example.com", "admin")
    fac_id = make_user("fac@example.com", "faculty")
    make_user("fac2@example.com", "faculty")
    s1 = make_user("s1@example.com", "student", "A")
    s2 = make_user("s2@example.com", "student", "A")
    s3 = make_user("s3@example.com", "student", "B")

    connection = database.get_connection()
    try:
        cursor = connection.execute(
            """
            INSERT INTO subjects (subject_code, subject_name, subject_type, section)
            VALUES ('T1', 'Test Subject', 'theory', NULL)
            """
        )
        subject_id = cursor.lastrowid
        connection.execute(
            """
            INSERT INTO faculty_assignments (faculty_id, subject_id, section)
            VALUES (?, ?, 'A')
            """,
            (fac_id, subject_id),
        )
        connection.commit()
    finally:
        connection.close()

    return {
        "subject_id": subject_id,
        "s1": s1,
        "s2": s2,
        "s3": s3,
        "admin": auth_headers("boss@example.com"),
        "fac": auth_headers("fac@example.com"),
        "fac2": auth_headers("fac2@example.com"),
        "student": auth_headers("s1@example.com"),
    }


def create_session(client, env, **kwargs):
    response = client.post(
        "/faculty/attendance-sessions",
        json=session_body(env["subject_id"], **kwargs),
        headers=env["fac"],
    )
    assert response.status_code == 201
    return response.json()["session"]["id"]


def mark(client, env, session_id, s1="present", s2="present"):
    response = client.put(
        f"/faculty/attendance-sessions/{session_id}/records",
        json={
            "records": [
                {"student_id": env["s1"], "status": s1},
                {"student_id": env["s2"], "status": s2},
            ]
        },
        headers=env["fac"],
    )
    assert response.status_code == 200


def finalize(client, env, session_id):
    return client.post(
        f"/faculty/attendance-sessions/{session_id}/finalize",
        headers=env["fac"],
    )


def subject_row(client, env):
    data = client.get("/student/attendance", headers=env["student"]).json()
    return next(s for s in data["subjects"] if s["subject_id"] == env["subject_id"])


# ---------- creating sessions ----------

def test_faculty_creates_draft_session(client, env):
    response = client.post(
        "/faculty/attendance-sessions",
        json=session_body(env["subject_id"]),
        headers=env["fac"],
    )
    assert response.status_code == 201
    assert response.json()["session"]["status"] == "draft"


def test_duplicate_session_rejected(client, env):
    create_session(client, env)
    response = client.post(
        "/faculty/attendance-sessions",
        json=session_body(env["subject_id"]),
        headers=env["fac"],
    )
    assert response.status_code == 409


def test_future_session_rejected(client, env):
    response = client.post(
        "/faculty/attendance-sessions",
        json=session_body(env["subject_id"], days_ago=-1),
        headers=env["fac"],
    )
    assert response.status_code == 400


def test_end_before_start_rejected(client, env):
    response = client.post(
        "/faculty/attendance-sessions",
        json=session_body(env["subject_id"], start="11:00", end="10:00"),
        headers=env["fac"],
    )
    assert response.status_code == 400


def test_faculty_cannot_create_session_for_unassigned_section(client, env):
    response = client.post(
        "/faculty/attendance-sessions",
        json=session_body(env["subject_id"], section="B"),
        headers=env["fac"],
    )
    assert response.status_code == 403


def test_unassigned_faculty_cannot_create_session(client, env):
    response = client.post(
        "/faculty/attendance-sessions",
        json=session_body(env["subject_id"]),
        headers=env["fac2"],
    )
    assert response.status_code == 403


# ---------- roster and ownership ----------

def test_roster_shows_only_section_students(client, env):
    session_id = create_session(client, env)
    response = client.get(
        f"/faculty/attendance-sessions/{session_id}/students",
        headers=env["fac"],
    )
    assert response.status_code == 200
    emails = sorted(s["email"] for s in response.json()["students"])
    assert emails == ["s1@example.com", "s2@example.com"]


def test_other_faculty_cannot_access_session(client, env):
    session_id = create_session(client, env)
    base = f"/faculty/attendance-sessions/{session_id}"

    roster = client.get(f"{base}/students", headers=env["fac2"])
    save = client.put(
        f"{base}/records",
        json={"records": [{"student_id": env["s1"], "status": "present"}]},
        headers=env["fac2"],
    )
    final = client.post(f"{base}/finalize", headers=env["fac2"])

    assert roster.status_code == 404
    assert save.status_code == 404
    assert final.status_code == 404


# ---------- marking ----------

def test_cannot_mark_student_from_other_section(client, env):
    session_id = create_session(client, env)
    response = client.put(
        f"/faculty/attendance-sessions/{session_id}/records",
        json={"records": [{"student_id": env["s3"], "status": "present"}]},
        headers=env["fac"],
    )
    assert response.status_code == 400


def test_empty_records_rejected(client, env):
    session_id = create_session(client, env)
    response = client.put(
        f"/faculty/attendance-sessions/{session_id}/records",
        json={"records": []},
        headers=env["fac"],
    )
    assert response.status_code == 422


def test_marking_again_overwrites_without_duplicates(client, env):
    session_id = create_session(client, env)
    mark(client, env, session_id, s1="present", s2="present")
    mark(client, env, session_id, s1="absent", s2="present")

    roster = client.get(
        f"/faculty/attendance-sessions/{session_id}/students",
        headers=env["fac"],
    ).json()["students"]
    status_by_email = {s["email"]: s["status"] for s in roster}
    assert status_by_email["s1@example.com"] == "absent"

    connection = database.get_connection()
    try:
        total = connection.execute(
            "SELECT COUNT(*) FROM attendance_records WHERE session_id = ?",
            (session_id,),
        ).fetchone()[0]
    finally:
        connection.close()
    assert total == 2


# ---------- finalizing ----------

def test_finalize_requires_everyone_marked(client, env):
    session_id = create_session(client, env)
    client.put(
        f"/faculty/attendance-sessions/{session_id}/records",
        json={"records": [{"student_id": env["s1"], "status": "present"}]},
        headers=env["fac"],
    )
    response = finalize(client, env, session_id)
    assert response.status_code == 400
    assert "1 student(s)" in response.json()["detail"]


def test_finalize_returns_counts(client, env):
    session_id = create_session(client, env)
    mark(client, env, session_id, s1="present", s2="absent")
    response = finalize(client, env, session_id)
    assert response.status_code == 200
    assert response.json()["present"] == 1
    assert response.json()["absent"] == 1


def test_finalized_session_is_locked(client, env):
    session_id = create_session(client, env)
    mark(client, env, session_id, s1="present", s2="present")
    assert finalize(client, env, session_id).status_code == 200

    edit = client.put(
        f"/faculty/attendance-sessions/{session_id}/records",
        json={"records": [{"student_id": env["s1"], "status": "absent"}]},
        headers=env["fac"],
    )
    again = finalize(client, env, session_id)
    assert edit.status_code == 409
    assert again.status_code == 409

    roster = client.get(
        f"/faculty/attendance-sessions/{session_id}/students",
        headers=env["fac"],
    ).json()["students"]
    status_by_email = {s["email"]: s["status"] for s in roster}
    assert status_by_email["s1@example.com"] == "present"


def test_draft_attendance_not_counted_until_finalized(client, env):
    session_id = create_session(client, env)
    mark(client, env, session_id, s1="present", s2="present")

    before = subject_row(client, env)
    assert before["conducted"] == 0

    finalize(client, env, session_id)

    after = subject_row(client, env)
    assert after["conducted"] == 1
    assert after["attended"] == 1
    assert after["percentage"] == 100.0


# ---------- corrections ----------

def test_admin_correction_updates_record_and_is_logged(client, env):
    session_id = create_session(client, env)
    mark(client, env, session_id, s1="present", s2="present")
    finalize(client, env, session_id)

    response = client.put(
        f"/admin/attendance-sessions/{session_id}/records/{env['s1']}",
        json={"status": "absent", "reason": "Marked by mistake"},
        headers=env["admin"],
    )
    assert response.status_code == 200
    assert response.json()["old_status"] == "present"
    assert response.json()["new_status"] == "absent"

    row = subject_row(client, env)
    assert row["attended"] == 0
    assert row["conducted"] == 1

    connection = database.get_connection()
    try:
        logs = connection.execute(
            "SELECT old_status, new_status, reason FROM attendance_corrections"
        ).fetchall()
    finally:
        connection.close()
    assert len(logs) == 1
    assert logs[0]["old_status"] == "present"
    assert logs[0]["new_status"] == "absent"
    assert logs[0]["reason"] == "Marked by mistake"


def test_correction_on_draft_session_rejected(client, env):
    session_id = create_session(client, env)
    mark(client, env, session_id)
    response = client.put(
        f"/admin/attendance-sessions/{session_id}/records/{env['s1']}",
        json={"status": "absent", "reason": "Trying early"},
        headers=env["admin"],
    )
    assert response.status_code == 400


def test_correction_with_same_status_rejected(client, env):
    session_id = create_session(client, env)
    mark(client, env, session_id, s1="present", s2="present")
    finalize(client, env, session_id)
    response = client.put(
        f"/admin/attendance-sessions/{session_id}/records/{env['s1']}",
        json={"status": "present", "reason": "No real change"},
        headers=env["admin"],
    )
    assert response.status_code == 400


def test_correction_needs_a_reason(client, env):
    session_id = create_session(client, env)
    mark(client, env, session_id)
    finalize(client, env, session_id)
    response = client.put(
        f"/admin/attendance-sessions/{session_id}/records/{env['s1']}",
        json={"status": "absent", "reason": "x"},
        headers=env["admin"],
    )
    assert response.status_code == 422


# ---------- role checks for these endpoints ----------

FACULTY_ENDPOINTS = [
    ("GET", "/faculty/classes", None),
    (
        "POST",
        "/faculty/attendance-sessions",
        {
            "subject_id": 1,
            "section": "A",
            "session_date": "2026-01-01",
            "start_time": "10:00",
            "end_time": "11:00",
        },
    ),
    ("GET", "/faculty/attendance-sessions/1/students", None),
    (
        "PUT",
        "/faculty/attendance-sessions/1/records",
        {"records": [{"student_id": 1, "status": "present"}]},
    ),
    ("POST", "/faculty/attendance-sessions/1/finalize", None),
]

CORRECTION_ENDPOINT = (
    "PUT",
    "/admin/attendance-sessions/1/records/1",
    {"status": "absent", "reason": "test reason"},
)


@pytest.mark.parametrize(
    "method,path,body", FACULTY_ENDPOINTS + [CORRECTION_ENDPOINT]
)
def test_no_token_rejected(client, method, path, body):
    assert client.request(method, path, json=body).status_code == 401


@pytest.mark.parametrize(
    "method,path,body", FACULTY_ENDPOINTS + [CORRECTION_ENDPOINT]
)
def test_student_cannot_mark_or_correct_attendance(client, env, method, path, body):
    response = client.request(method, path, json=body, headers=env["student"])
    assert response.status_code == 403


@pytest.mark.parametrize("method,path,body", FACULTY_ENDPOINTS)
def test_admin_blocked_from_faculty_endpoints(client, env, method, path, body):
    response = client.request(method, path, json=body, headers=env["admin"])
    assert response.status_code == 403


def test_faculty_cannot_correct_attendance(client, env):
    method, path, body = CORRECTION_ENDPOINT
    response = client.request(method, path, json=body, headers=env["fac"])
    assert response.status_code == 403