from fastapi import APIRouter, Depends, HTTPException

from backend.calculations import summarize
from backend.database import get_connection
from backend.security import require_role

router = APIRouter()


@router.get("/student/attendance")
def my_attendance(current_user: dict = Depends(require_role("student"))):
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT s.id, s.subject_code, s.subject_name, s.subject_type,
                   COUNT(ar.id) AS conducted,
                   COALESCE(SUM(ar.status = 'present'), 0) AS attended
            FROM subjects s
            LEFT JOIN attendance_sessions sess
                ON sess.subject_id = s.id
               AND sess.status = 'finalized'
               AND sess.section = ?
            LEFT JOIN attendance_records ar
                ON ar.session_id = sess.id
               AND ar.student_id = ?
            WHERE s.section IS NULL OR s.section = ?
            GROUP BY s.id
            ORDER BY s.subject_code
            """,
            (current_user["section"], current_user["id"], current_user["section"]),
        ).fetchall()

        subjects = []
        warnings = []
        total_attended = 0
        total_conducted = 0

        for row in rows:
            summary = summarize(row["attended"], row["conducted"])
            total_attended += row["attended"]
            total_conducted += row["conducted"]

            item = {
                "subject_id": row["id"],
                "subject_code": row["subject_code"],
                "subject_name": row["subject_name"],
                "subject_type": row["subject_type"],
                **summary,
            }
            subjects.append(item)

            if summary["status"] in ("short", "borderline"):
                warnings.append(
                    {
                        "subject_code": row["subject_code"],
                        "subject_name": row["subject_name"],
                        "status": summary["status"],
                        "message": summary["message"],
                    }
                )

        return {
            "overall": summarize(total_attended, total_conducted),
            "subjects": subjects,
            "warnings": warnings,
        }

    finally:
        connection.close()


@router.get("/student/attendance/{subject_id}")
def my_subject_attendance(
    subject_id: int,
    current_user: dict = Depends(require_role("student")),
):
    connection = get_connection()

    try:
        subject = connection.execute(
            """
            SELECT id, subject_code, subject_name, subject_type
            FROM subjects
            WHERE id = ? AND (section IS NULL OR section = ?)
            """,
            (subject_id, current_user["section"]),
        ).fetchone()

        if subject is None:
            raise HTTPException(status_code=404, detail="Subject not found")

        history = connection.execute(
            """
            SELECT sess.session_date, sess.start_time, sess.end_time, ar.status
            FROM attendance_sessions sess
            JOIN attendance_records ar
                ON ar.session_id = sess.id AND ar.student_id = ?
            WHERE sess.subject_id = ? AND sess.status = 'finalized'
            ORDER BY sess.session_date DESC, sess.start_time DESC
            """,
            (current_user["id"], subject_id),
        ).fetchall()

        attended = sum(1 for row in history if row["status"] == "present")

        return {
            "subject": dict(subject),
            "summary": summarize(attended, len(history)),
            "history": [dict(row) for row in history],
        }

    finally:
        connection.close()