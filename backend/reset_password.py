from getpass import getpass

from backend.auth import hash_password
from backend.database import get_connection


def reset_password():
    email = input("Account email: ").strip().lower()
    password = getpass("New password (min 8 chars): ")

    if len(password) < 8:
        print("Password must be at least 8 characters. Nothing was changed.")
        return

    connection = get_connection()

    try:
        cursor = connection.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (hash_password(password), email),
        )
        connection.commit()

        if cursor.rowcount == 0:
            print("No account found with that email.")
        else:
            print("Password updated.")

    finally:
        connection.close()


if __name__ == "__main__":
    reset_password()