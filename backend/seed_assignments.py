from backend.database import get_connection, initialize_database
from backend.migrations import run_migrations

DOMAIN = "faculty.example.com"

EMAILS = {
    "SS": "sanjiv.sharma",
    "PJ": "punit.johari",
    "VS": "vikas.sejwar",
    "RKS": "rajeev.singh",
    "NB": "neha.bhardwaj",
    "VR": "vikram.rajpoot",
    "GS": "gulshan.soni",
    "KD": "kumud.dixit",
    "SG": "surbhi.gupta",
    "AP": "anand.pawar",
}

# (subject_code, section, [faculty initials])
ASSIGNMENTS = [
    ("16252101", "A", ["AP"]),
    ("16252101", "B", ["AP"]),
    ("16252102", "A", ["KD"]),
    ("16252102", "B", ["KD"]),
    ("16252103", "A", ["PJ"]),
    ("16252103", "B", ["PJ"]),
    ("16252104", "A", ["SS"]),
    ("16252104", "B", ["SS"]),
    ("16252105", "A", ["GS"]),
    ("16252105", "B", ["GS"]),
    ("16252112", "A", ["SG"]),
    ("16252112", "B", ["SG"]),
    ("16252111", "A", ["SS", "VR", "VS"]),
    ("16252111", "B", ["RKS", "NB"]),
    ("16252109", "A", ["VR", "GS"]),
    ("16252109", "B", ["SG", "PJ"]),
]


def seed_assignments():
    initialize_database()
    run_migrations()
    connection = get_connection()

    try:
        subject_ids = {
            row["subject_code"]: row["id"]
            for row in connection.execute("SELECT id, subject_code FROM subjects")
        }
        faculty_ids = {
            row["email"]: row["id"]
            for row in connection.execute(
                "SELECT id, email FROM users WHERE role = 'faculty'"
            )
        }

        rows = []
        for code, section, initials_list in ASSIGNMENTS:
            if code not in subject_ids:
                print(f"Missing subject {code}. Run backend/subjects.py first.")
                return
            for initials in initials_list:
                email = f"{EMAILS[initials]}@{DOMAIN}"
                if email not in faculty_ids:
                    print(f"Missing faculty {email}. Run backend/seed_faculty.py first.")
                    return
                rows.append((faculty_ids[email], subject_ids[code], section))

        added = 0
        for row in rows:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO faculty_assignments
                    (faculty_id, subject_id, section)
                VALUES (?, ?, ?)
                """,
                row,
            )
            added += cursor.rowcount
        connection.commit()
        print(f"Assignments added: {added} (already existing: {len(rows) - added})")

    finally:
        connection.close()


if __name__ == "__main__":
    seed_assignments()