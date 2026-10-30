from fastapi import APIRouter, Depends, HTTPException
from backend.calculations import attendance_percentage, summarize
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

@router.get("/student/analytics")
def my_analytics(current_user: dict = Depends(require_role("student"))):
    connection = get_connection()

    try:
        monthly_rows = connection.execute(
            """
            SELECT strftime('%Y-%m', sess.session_date) AS month,
                   COUNT(*) AS conducted,
                   SUM(ar.status = 'present') AS attended
            FROM attendance_records ar
            JOIN attendance_sessions sess ON sess.id = ar.session_id
            WHERE ar.student_id = ? AND sess.status = 'finalized'
            GROUP BY month
            ORDER BY month
            """,
            (current_user["id"],),
        ).fetchall()

        type_rows = connection.execute(
            """
            SELECT s.subject_type,
                   COUNT(*) AS conducted,
                   SUM(ar.status = 'present') AS attended
            FROM attendance_records ar
            JOIN attendance_sessions sess ON sess.id = ar.session_id
            JOIN subjects s ON s.id = sess.subject_id
            WHERE ar.student_id = ? AND sess.status = 'finalized'
            GROUP BY s.subject_type
            ORDER BY s.subject_type
            """,
            (current_user["id"],),
        ).fetchall()

        absence_rows = connection.execute(
            """
            SELECT sess.session_date, sess.start_time,
                   s.subject_code, s.subject_name
            FROM attendance_records ar
            JOIN attendance_sessions sess ON sess.id = ar.session_id
            JOIN subjects s ON s.id = sess.subject_id
            WHERE ar.student_id = ?
              AND sess.status = 'finalized'
              AND ar.status = 'absent'
            ORDER BY sess.session_date DESC, sess.start_time DESC
            LIMIT 5
            """,
            (current_user["id"],),
        ).fetchall()

        monthly = []
        total_attended = 0
        total_conducted = 0

        for row in monthly_rows:
            total_attended += row["attended"]
            total_conducted += row["conducted"]
            monthly.append(
                {
                    "month": row["month"],
                    "attended": row["attended"],
                    "conducted": row["conducted"],
                    "percentage": attendance_percentage(
                        row["attended"], row["conducted"]
                    ),
                }
            )

        by_subject_type = [
            {
                "subject_type": row["subject_type"],
                "attended": row["attended"],
                "conducted": row["conducted"],
                "percentage": attendance_percentage(
                    row["attended"], row["conducted"]
                ),
            }
            for row in type_rows
        ]

        return {
            "overall": summarize(total_attended, total_conducted),
            "classes_missed": total_conducted - total_attended,
            "monthly": monthly,
            "by_subject_type": by_subject_type,
            "recent_absences": [dict(row) for row in absence_rows],
        }

    finally:
        connection.close()