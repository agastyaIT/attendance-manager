from backend.database import get_connection

MIGRATIONS = [

        """
    CREATE TABLE IF NOT EXISTS timetable_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL REFERENCES subjects(id),
        section TEXT NOT NULL CHECK (section IN ('A', 'B')),
        faculty_id INTEGER REFERENCES users(id),
        day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        room TEXT,
        UNIQUE (section, day_of_week, start_time),
        UNIQUE (faculty_id, day_of_week, start_time)
    )
    """,
    
    """
    CREATE TABLE IF NOT EXISTS faculty_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        faculty_id INTEGER NOT NULL REFERENCES users(id),
        subject_id INTEGER NOT NULL REFERENCES subjects(id),
        section TEXT NOT NULL CHECK (section IN ('A', 'B')),
        UNIQUE (faculty_id, subject_id, section)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS attendance_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL REFERENCES subjects(id),
        section TEXT NOT NULL CHECK (section IN ('A', 'B')),
        faculty_id INTEGER NOT NULL REFERENCES users(id),
        session_date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft'
            CHECK (status IN ('draft', 'finalized')),
        finalized_at TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (subject_id, section, session_date, start_time)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS attendance_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL REFERENCES attendance_sessions(id),
        student_id INTEGER NOT NULL REFERENCES users(id),
        status TEXT NOT NULL CHECK (status IN ('present', 'absent')),
        UNIQUE (session_id, student_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_records_student
    ON attendance_records (student_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS attendance_corrections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL REFERENCES attendance_sessions(id),
        student_id INTEGER NOT NULL REFERENCES users(id),
        old_status TEXT NOT NULL,
        new_status TEXT NOT NULL,
        reason TEXT NOT NULL,
        corrected_by INTEGER NOT NULL REFERENCES users(id),
        corrected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


def run_migrations():
    connection = get_connection()

    try:
        for statement in MIGRATIONS:
            connection.execute(statement)
        connection.commit()

    finally:
        connection.close()