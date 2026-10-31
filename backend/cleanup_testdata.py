from backend.database import get_connection

connection = get_connection()

try:
    rows = connection.execute(
        "SELECT id FROM attendance_sessions WHERE end_time LIKE '23:59%'"
    ).fetchall()
    ids = [row["id"] for row in rows]

    print("Test sessions found:", len(ids))

    if not ids:
        raise SystemExit

    if input("Type DELETE to remove them and their records: ") != "DELETE":
        print("Cancelled")
        raise SystemExit

    marks = ",".join("?" * len(ids))

    connection.execute(
        f"DELETE FROM attendance_corrections WHERE session_id IN ({marks})", ids
    )
    connection.execute(
        f"DELETE FROM attendance_records WHERE session_id IN ({marks})", ids
    )
    connection.execute(
        f"DELETE FROM attendance_sessions WHERE id IN ({marks})", ids
    )
    connection.commit()
    print("Deleted", len(ids), "test sessions")

finally:
    connection.close()