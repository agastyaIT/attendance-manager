import getpass
import sqlite3

from backend.auth import hash_password
from backend.database import get_connection, initialize_database


def create_admin():
    initialize_database()

    name = input("Admin name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass.getpass("Admin password (min 8 characters): ")
    confirm = getpass.getpass("Confirm password: ")

    if not name or not email:
        print("Name and email are required.")
        return

    if len(password) < 8:
        print("Password must be at least 8 characters.")
        return

    if password != confirm:
        print("Passwords do not match.")
        return

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO users (name, email, password_hash, role, section)
            VALUES (?, ?, ?, 'admin', NULL)
            """,
            (name, email, hash_password(password)),
        )
        connection.commit()
        print("Admin account created.")

    except sqlite3.IntegrityError:
        print("An account with this email already exists.")

    finally:
        connection.close()


if __name__ == "__main__":
    create_admin()