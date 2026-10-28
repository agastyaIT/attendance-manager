from backend.database import get_connection, initialize_database

SUBJECTS = [
    ("16252101", "Transforms and Vector Calculus (MACS)", "theory"),
    ("16252102", "Design and Analysis of Algorithms (DAA)", "theory"),
    ("16252103", "Database Management System (DBMS)", "theory"),
    ("16252104", "Operating Systems (OS)", "theory"),
    ("16252105", "Computer Networks (CN)", "theory"),
    ("16252112", "Cyber Security", "theory"),
    ("16252106", "DAA Lab", "lab"),
    ("16252107", "DBMS Lab", "lab"),
    ("16252108", "OS Lab", "lab"),
    ("16252109", "Macro Project-I", "project"),
    ("16252110", "Semester Proficiency", "seminar"),
    ("16252111", "Self-learning/Presentation", "seminar"),
]


def seed_subjects():
    initialize_database()
    connection = get_connection()

    try:
        cursor = connection.executemany(
            """
            INSERT OR IGNORE INTO subjects
                (subject_code, subject_name, subject_type, section)
            VALUES (?, ?, ?, NULL)
            """,
            SUBJECTS,
        )
        connection.commit()
        print(f"Subjects added: {cursor.rowcount}")

    finally:
        connection.close()


if __name__ == "__main__":
    seed_subjects()