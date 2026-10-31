from backend.database import get_connection, initialize_database
from backend.migrations import run_migrations

R = "116"

# (section, day_of_week, start, end, subject_code, room)   Monday = 1
ENTRIES = [
    # ----- Section A -----
    ("A", 1, "11:00", "12:00", "16252101", R),
    ("A", 1, "12:00", "13:00", "16252105", R),
    ("A", 1, "16:00", "17:00", "16252103", R),
    ("A", 1, "17:00", "18:00", "16252102", R),
    ("A", 2, "10:00", "11:00", "16252103", R),
    ("A", 2, "14:00", "15:00", "16252101", R),
    ("A", 2, "15:00", "17:00", "16252111", R),
    ("A", 2, "17:00", "18:00", "16252104", R),
    ("A", 3, "10:00", "11:00", "16252105", "NRGF"),
    ("A", 3, "14:00", "15:00", "16252102", "115"),
    ("A", 3, "15:00", "16:00", "16252101", "115"),
    ("A", 3, "16:00", "18:00", "16252109", "SH-5"),
    ("A", 4, "10:00", "11:00", "16252112", "NRGF"),
    ("A", 4, "14:00", "15:00", "16252103", R),
    ("A", 4, "15:00", "16:00", "16252104", R),
    ("A", 4, "16:00", "17:00", "16252102", R),
    ("A", 5, "14:00", "15:00", "16252104", R),
    ("A", 5, "15:00", "16:00", "16252105", R),
    ("A", 5, "16:00", "17:00", "16252112", R),
    # ----- Section B -----
    ("B", 1, "10:00", "11:00", "16252105", R),
    ("B", 1, "14:00", "15:00", "16252101", R),
    ("B", 1, "15:00", "16:00", "16252104", R),
    ("B", 2, "10:00", "11:00", "16252105", "NRGF"),
    ("B", 3, "10:00", "11:00", "16252103", R),
    ("B", 3, "11:00", "12:00", "16252101", R),
    ("B", 3, "12:00", "13:00", "16252102", R),
    ("B", 3, "14:00", "15:00", "16252104", R),
    ("B", 3, "15:00", "16:00", "16252105", R),
    ("B", 3, "16:00", "18:00", "16252111", R),
    ("B", 4, "10:00", "11:00", "16252104", R),
    ("B", 4, "11:00", "12:00", "16252103", R),
    ("B", 4, "12:00", "13:00", "16252102", R),
    ("B", 4, "14:00", "15:00", "16252112", "115"),
    ("B", 4, "15:00", "17:00", "16252109", "115"),
    ("B", 5, "10:00", "11:00", "16252101", R),
    ("B", 5, "11:00", "12:00", "16252112", R),
    ("B", 5, "12:00", "13:00", "16252103", R),
    ("B", 5, "16:00", "17:00", "16252102", "SH-5"),
]


def seed_timetable():
    initialize_database()
    run_migrations()
    connection = get_connection()

    try:
        subject_ids = {
            row["subject_code"]: row["id"]
            for row in connection.execute("SELECT id, subject_code FROM subjects")
        }

        missing = sorted({entry[4] for entry in ENTRIES} - set(subject_ids))
        if missing:
            print(f"Missing subjects {missing}. Run backend/subjects.py first.")
            return

        connection.execute("DELETE FROM timetable_entries")
        connection.executemany(
            """
            INSERT INTO timetable_entries
                (subject_id, section, faculty_id, day_of_week,
                 start_time, end_time, room)
            VALUES (?, ?, NULL, ?, ?, ?, ?)
            """,
            [
                (subject_ids[code], section, day, start, end, room)
                for section, day, start, end, code, room in ENTRIES
            ],
        )
        connection.commit()
        print(f"Timetable entries added: {len(ENTRIES)}")

    finally:
        connection.close()


if __name__ == "__main__":
    seed_timetable()