from getpass import getpass

from backend.auth import hash_password
from backend.database import get_connection, initialize_database

FACULTY = [
    ("Dr. Akhilesh Tiwari", "akhilesh.tiwari@faculty.example.com"),
    ("Dr. Sanjiv Sharma", "sanjiv.sharma@faculty.example.com"),
    ("Dr. Punit Kumar Johari", "punit.johari@faculty.example.com"),
    ("Dr. Abhilash Sonker", "abhilash.sonker@faculty.example.com"),
    ("Vikas Sejwar", "vikas.sejwar@faculty.example.com"),
    ("Dr. Rajeev K. Singh", "rajeev.singh@faculty.example.com"),
    ("Neha Bhardwaj", "neha.bhardwaj@faculty.example.com"),
    ("Dr. Vikram Rajpoot", "vikram.rajpoot@faculty.example.com"),
    ("Dr. Gulshan Soni", "gulshan.soni@faculty.example.com"),
    ("Aradhana Saxena", "aradhana.saxena@faculty.example.com"),
    ("Shubham Sharma", "shubham.sharma@faculty.example.com"),
    ("Kumud Dixit", "kumud.dixit@faculty.example.com"),
    ("Surbhi Gupta", "surbhi.gupta@faculty.example.com"),
    ("Mrs. Tanuja Sharma", "tanuja.sharma@faculty.example.com"),
    ("Anand Pawar", "anand.pawar@faculty.example.com"),
]


def seed_faculty():
    initialize_database()

    password = getpass("Temporary password for all faculty (min 8 chars): ")
    if len(password) < 8:
        print("Password must be at least 8 characters. Nothing was added.")
        return

    password_hash = hash_password(password)
    connection = get_connection()

    try:
        added = 0
        for name, email in FACULTY:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO users
                    (name, email, password_hash, role, section)
                VALUES (?, ?, ?, 'faculty', NULL)
                """,
                (name, email, password_hash),
            )
            added += cursor.rowcount
        connection.commit()
        print(f"Faculty accounts added: {added} (already existing: {len(FACULTY) - added})")

    finally:
        connection.close()


if __name__ == "__main__":
    seed_faculty()