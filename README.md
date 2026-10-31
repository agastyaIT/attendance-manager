# Attendance Manager

A web application for the IT department at MITS, Gwalior. Students can see their
subject-wise attendance, how many classes they can still skip, and how many they
must attend in a row to get back to 75%. Faculty record and finalize attendance,
and administrators manage users, subjects and assignments.

## Features

- Student registration and login (JWT tokens, Argon2 password hashing)
- Three roles: student, faculty, admin, with server-side permission checks
- Attendance sessions per subject, section, date and time
- Draft and finalized sessions; finalized sessions are locked
- Admin-only corrections, saved with a reason in an audit table
- Percentage, "classes you can skip" and "classes to recover" calculations
- Warnings and an overall percentage, based on finalized sessions only
- Browser interface for students, faculty and admins (HTML, CSS, JavaScript)

## Tech stack

Python, FastAPI, SQLite (`sqlite3`), Pydantic, pwdlib (Argon2), PyJWT,
python-dotenv, plain HTML/CSS/JavaScript.

## Setup (Windows, PowerShell)

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Install the dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Create a file named `.env` in the project root (see `.env.example`):

   ```
   JWT_SECRET_KEY=your-long-random-string
   ```

   You can generate a value with:

   ```powershell
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. Create the first administrator (asks for a name, email and password):

   ```powershell
   python -m backend.create_admin
   ```

5. Load the twelve subjects:

   ```powershell
   python -m backend.seed_subjects
   ```

6. Start the server:

   ```powershell
   uvicorn backend.main:app --reload
   ```

7. Open `http://127.0.0.1:8000/app/` in a browser. If port 8000 is busy, add
   `--port 8001` to the command and use that port in the address.

The database file is created automatically on first start.

## First use

1. Log in as the admin and create a faculty account (Add Faculty).
2. Assign the faculty member to a subject and section (Assignments).
3. Students register themselves on the registration page.
4. The faculty member logs in, starts a session, ticks the students who are
   present, and finalizes it.
5. Students see their results on their dashboard.

## API documentation

With the server running, open `http://127.0.0.1:8000/docs`.

## Tests

```powershell
python -m unittest tests.test_calculations -v
```

## Project structure

```
backend/     FastAPI application, database, security, attendance, calculations
frontend/    login, registration, admin, faculty and student pages
tests/       unit tests for the attendance calculations
```

## Security notes

- Passwords are stored only as Argon2 hashes.
- Access tokens expire after 30 minutes and are signed with the secret in `.env`.
- Permissions are checked on the server for every protected request.
- All SQL uses parameter placeholders.
- `.env` and the database file are excluded from Git.

## Limitations

- Email addresses are not verified at registration.
- No timetable or analytics screens yet.
- Intended for local use; a real deployment needs HTTPS and a stronger session setup.

## Authors

Aeshna Jain and Agastya Sadaphale, under the guidance of Dr. Abhilash Sonkar,
School of Information Technology, MITS Gwalior.
