import sqlite3
from datetime import date, time
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.database import get_connection
from backend.security import require_role

router = APIRouter()


class SessionCreate(BaseModel):
    subject_id: int
    section: Literal["A", "B"]
    session_date: date
    start_time: time
    end_time: time


class RecordItem(BaseModel):
    student_id: int
    status: Literal["present", "absent"]


class RecordsUpdate(BaseModel):
    records: List[RecordItem] = Field(min_length=1)


class CorrectionRequest(BaseModel):
    status: Literal["present", "absent"]
    reason: str = Field(min_length=3)


def get_own_session(connection, session_id: int, faculty_id: int):
    session = connection.execute(
        """
        SELECT id, subject_id, section, session_date,
               start_time, end_time, status
        FROM attendance_sessions
        WHERE id = ? AND faculty_id = ?
        """,
        (session_id, faculty_id),
    ).fetchone()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@router.get("/faculty/classes")
def my_classes(current_user: dict = Depends(require_role("faculty"))):
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT fa.id AS assignment_id, fa.section,
                   s.id AS subject_id, s.subject_code,
                   s.subject_name, s.subject_type
            FROM faculty_assignments fa
            JOIN subjects s ON s.id = fa.subject_id
            WHERE fa.faculty_id = ?
            ORDER BY s.subject_code, fa.section
            """,
            (current_user["id"],),
        ).fetchall()

        return {"classes": [dict(row) for row in rows]}

    finally:
        connection.close()


@router.post("/faculty/attendance-sessions", status_code=201)
def create_session(
    data: SessionCreate,
    current_user: dict = Depends(require_role("faculty")),
):
    if data.end_time <= data.start_time:
        raise HTTPException(
            status_code=400, detail="End time must be after start time"
        )

    if data.session_date > date.today():
        raise HTTPException(
            status_code=400, detail="Cannot create a session in the future"
        )

    connection = get_connection()

    try:
        assigned = connection.execute(
            """
            SELECT id FROM faculty_assignments
            WHERE faculty_id = ? AND subject_id = ? AND section = ?
            """,
            (current_user["id"], data.subject_id, data.section),
        ).fetchone()

        if assigned is None:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to this subject and section",
            )

        cursor = connection.execute(
            """
            INSERT INTO attendance_sessions
                (subject_id, section, faculty_id,
                 session_date, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data.subject_id,
                data.section,
                current_user["id"],
                data.session_date.isoformat(),
                data.start_time.isoformat(),
                data.end_time.isoformat(),
            ),
        )
        connection.commit()

        return {
            "message": "Session created",
            "session": {
                "id": cursor.lastrowid,
                "subject_id": data.subject_id,
                "section": data.section,
                "session_date": data.session_date.isoformat(),
                "start_time": data.start_time.isoformat(),
                "end_time": data.end_time.isoformat(),
                "status": "draft",
            },
        }

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="A session already exists for this subject, section, date and start time",
        )

    finally:
        connection.close()


@router.get("/faculty/attendance-sessions/{session_id}/students")
def session_roster(
    session_id: int,
    current_user: dict = Depends(require_role("faculty")),
):
    connection = get_connection()

    try:
        session = get_own_session(connection, session_id, current_user["id"])

        rows = connection.execute(
            """
            SELECT u.id AS student_id, u.name, u.email, ar.status
            FROM users u
            LEFT JOIN attendance_records ar
                ON ar.student_id = u.id AND ar.session_id = ?
            WHERE u.role = 'student' AND u.section = ?
            ORDER BY u.name
            """,
            (session_id, session["section"]),
        ).fetchall()

        return {
            "session": dict(session),
            "students": [dict(row) for row in rows],
        }

    finally:
        connection.close()


@router.put("/faculty/attendance-sessions/{session_id}/records")
def save_records(
    session_id: int,
    data: RecordsUpdate,
    current_user: dict = Depends(require_role("faculty")),
):
    connection = get_connection()

    try:
        session = get_own_session(connection, session_id, current_user["id"])

        if session["status"] != "draft":
            raise HTTPException(
                status_code=409,
                detail="Session is finalized and cannot be changed",
            )

        valid_ids = {
            row["id"]
            for row in connection.execute(
                "SELECT id FROM users WHERE role = 'student' AND section = ?",
                (session["section"],),
            ).fetchall()
        }

        for item in data.records:
            if item.student_id not in valid_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Student {item.student_id} is not in section {session['section']}",
                )

        for item in data.records:
            connection.execute(
                """
                INSERT INTO attendance_records (session_id, student_id, status)
                VALUES (?, ?, ?)
                ON CONFLICT (session_id, student_id)
                DO UPDATE SET status = excluded.status
                """,
                (session_id, item.student_id, item.status),
            )

        connection.commit()

        return {"message": "Attendance saved", "saved": len(data.records)}

    finally:
        connection.close()


@router.post("/faculty/attendance-sessions/{session_id}/finalize")
def finalize_session(
    session_id: int,
    current_user: dict = Depends(require_role("faculty")),
):
    connection = get_connection()

    try:
        session = get_own_session(connection, session_id, current_user["id"])

        if session["status"] != "draft":
            raise HTTPException(
                status_code=409, detail="Session is already finalized"
            )

        total = connection.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'student' AND section = ?",
            (session["section"],),
        ).fetchone()[0]

        if total == 0:
            raise HTTPException(
                status_code=400, detail="There are no students in this section"
            )

        counts = connection.execute(
            """
            SELECT COUNT(*) AS marked,
                   COALESCE(SUM(status = 'present'), 0) AS present
            FROM attendance_records
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()

        if counts["marked"] < total:
            raise HTTPException(
                status_code=400,
                detail=f"{total - counts['marked']} student(s) are not marked yet",
            )

        cursor = connection.execute(
            """
            UPDATE attendance_sessions
            SET status = 'finalized', finalized_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'draft'
            """,
            (session_id,),
        )
        connection.commit()

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=409, detail="Session is already finalized"
            )

        return {
            "message": "Session finalized",
            "present": counts["present"],
            "absent": counts["marked"] - counts["present"],
        }

    finally:
        connection.close()


@router.put("/admin/attendance-sessions/{session_id}/records/{student_id}")
def correct_record(
    session_id: int,
    student_id: int,
    data: CorrectionRequest,
    current_user: dict = Depends(require_role("admin")),
):
    connection = get_connection()

    try:
        session = connection.execute(
            "SELECT status FROM attendance_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()

        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")

        if session["status"] != "finalized":
            raise HTTPException(
                status_code=400,
                detail="Only finalized sessions need corrections",
            )

        record = connection.execute(
            """
            SELECT id, status FROM attendance_records
            WHERE session_id = ? AND student_id = ?
            """,
            (session_id, student_id),
        ).fetchone()

        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")

        if record["status"] == data.status:
            raise HTTPException(
                status_code=400, detail="Record already has this status"
            )

        connection.execute(
            "UPDATE attendance_records SET status = ? WHERE id = ?",
            (data.status, record["id"]),
        )
        connection.execute(
            """
            INSERT INTO attendance_corrections
                (session_id, student_id, old_status, new_status,
                 reason, corrected_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                student_id,
                record["status"],
                data.status,
                data.reason.strip(),
                current_user["id"],
            ),
        )
        connection.commit()

        return {
            "message": "Attendance corrected",
            "old_status": record["status"],
            "new_status": data.status,
        }

    finally:
        connection.close()