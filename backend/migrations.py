from backend.database import get_connection


def run_migrations():
    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS faculty_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                faculty_id INTEGER NOT NULL REFERENCES users(id),
                subject_id INTEGER NOT NULL REFERENCES subjects(id),
                section TEXT NOT NULL CHECK (section IN ('A', 'B')),
                UNIQUE (faculty_id, subject_id, section)
            )
            """
        )
        connection.commit()

    finally:
        connection.close()