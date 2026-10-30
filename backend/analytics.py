from fastapi import APIRouter, Depends

from backend.calculations import attendance_percentage, summarize
from backend.database import get_connection
from backend.security import require_role

router = APIRouter()


@router.get("/admin/analytics")
def admin_analytics(current_user: dict = Depends(require_role("admin"))):
    connection = get_connection()

    try:
        role_rows = connection.execute(
            "SELECT role, COUNT(*) AS total FROM users GROUP BY role"
        ).fetchall()

        section_rows = connection.execute(
            """
            SELECT section, COUNT(*) AS total
            FROM users
            WHERE role = 'student'
            GROUP BY section
            """
        ).fetchall()

        session_rows = connection.execute(
            "SELECT status, COUNT(*) AS total FROM attendance_sessions GROUP BY status"
        ).fetchall()

        subject_count = connection.execute(
            "SELECT COUNT(*) AS total FROM subjects"
        ).fetchone()["total"]

        subject_rows = connection.execute(
            """
            SELECT sess.section, s.id AS subject_id, s.subject_code,
                   s.subject_name,
                   COUNT(DISTINCT sess.id) AS sessions_held,
                   COUNT(ar.id) AS records,
                   COALESCE(SUM(ar.status = 'present'), 0) AS attended
            FROM attendance_sessions sess
            JOIN subjects s ON s.id = sess.subject_id
            LEFT JOIN attendance_records ar ON ar.session_id = sess.id
            WHERE sess.status = 'finalized'
            GROUP BY sess.section, s.id
            ORDER BY sess.section, s.subject_code
            """
        ).fetchall()

        student_rows = connection.execute(
            """
            SELECT u.id, u.name, u.email, u.section,
                   COUNT(ar.id) AS conducted,
                   COALESCE(SUM(ar.status = 'present'), 0) AS attended
            FROM users u
            JOIN attendance_records ar ON ar.student_id = u.id
            JOIN attendance_sessions sess
                ON sess.id = ar.session_id AND sess.status = 'finalized'
            WHERE u.role = 'student'
            GROUP BY u.id
            """
        ).fetchall()

        users_by_role = {"admin": 0, "faculty": 0, "student": 0}
        for row in role_rows:
            users_by_role[row["role"]] = row["total"]

        students_by_section = {"A": 0, "B": 0}
        for row in section_rows:
            if row["section"] in students_by_section:
                students_by_section[row["section"]] = row["total"]

        sessions = {"draft": 0, "finalized": 0}
        for row in session_rows:
            sessions[row["status"]] = row["total"]

        sections = {}
        for row in subject_rows:
            block = sections.setdefault(
                row["section"],
                {"section": row["section"], "attended": 0, "records": 0, "subjects": []},
            )
            block["attended"] += row["attended"]
            block["records"] += row["records"]
            block["subjects"].append(
                {
                    "subject_id": row["subject_id"],
                    "subject_code": row["subject_code"],
                    "subject_name": row["subject_name"],
                    "sessions_held": row["sessions_held"],
                    "attended": row["attended"],
                    "records": row["records"],
                    "percentage": attendance_percentage(
                        row["attended"], row["records"]
                    ),
                }
            )

        attendance_by_section = []
        for key in sorted(sections):
            block = sections[key]
            block["percentage"] = attendance_percentage(
                block["attended"], block["records"]
            )
            attendance_by_section.append(block)

        short_students = []
        for row in student_rows:
            summary = summarize(row["attended"], row["conducted"])
            if summary["status"] == "short":
                short_students.append(
                    {
                        "student_id": row["id"],
                        "name": row["name"],
                        "email": row["email"],
                        "section": row["section"],
                        "percentage": summary["percentage"],
                        "classes_to_recover": summary["classes_to_recover"],
                    }
                )

        short_students.sort(key=lambda s: s["percentage"])

        return {
            "totals": {
                "users_by_role": users_by_role,
                "students_by_section": students_by_section,
                "subjects": subject_count,
                "sessions": sessions,
            },
            "attendance_by_section": attendance_by_section,
            "short_attendance_students": short_students,
        }

    finally:
        connection.close()