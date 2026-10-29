from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
import sqlite3
from backend.database import initialize_database, get_connection
from backend.auth import hash_password, verify_password
from backend.security import create_access_token
from backend.security import get_current_user, require_role
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional
from backend.migrations import run_migrations
from backend.attendance import router as attendance_router


app = FastAPI(title="Attendance Manager API")

app.include_router(attendance_router)

@app.on_event("startup")
def startup():
    initialize_database()
    run_migrations()


class StudentRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    section: str

class StudentLogin(BaseModel):
    email: EmailStr
    password: str

class FacultyCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=8)


@app.get("/")
def home():
    return {"message": "Attendance Manager API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "database": "initialized"}


@app.post("/register")
def register_student(student: StudentRegister):
    if len(student.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long"
        )

    if student.section not in ["A", "B"]:
        raise HTTPException(
            status_code=400,
            detail="Section must be A or B"
        )

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO users (name, email, password_hash, role, section)
            VALUES (?, ?, ?, 'student', ?)
            """,
            (
                student.name.strip(),
                str(student.email).lower(),
                hash_password(student.password),
                student.section
            )
        )

        connection.commit()

        return {"message": "Student registered successfully"}

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists"
        )

    finally:
        connection.close()



@app.post("/login")
def login_student(credentials: StudentLogin):
    connection = get_connection()

    try:
        user = connection.execute(
            """
            SELECT id, name, email, password_hash, role, section
            FROM users
            WHERE email = ?
            """,
            (str(credentials.email).lower(),)
        ).fetchone()

        if user is None or not verify_password(
            credentials.password, user["password_hash"]
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        access_token = create_access_token(
            user_id=user["id"],
            role=user["role"]
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "section": user["section"]
            }
        }

    finally:
        connection.close()

@app.get("/me")
def read_current_user(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}


@app.post("/token")
def login_for_docs(form_data: OAuth2PasswordRequestForm = Depends()):
    connection = get_connection()

    try:
        user = connection.execute(
            "SELECT id, password_hash, role FROM users WHERE email = ?",
            (form_data.username.lower(),)
        ).fetchone()

        if user is None or not verify_password(
            form_data.password, user["password_hash"]
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        access_token = create_access_token(
            user_id=user["id"],
            role=user["role"]
        )

        return {"access_token": access_token, "token_type": "bearer"}

    finally:
        connection.close()


@app.post("/admin/faculty", status_code=201)
def create_faculty(
    faculty: FacultyCreate,
    current_user: dict = Depends(require_role("admin")),
):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO users (name, email, password_hash, role, section)
            VALUES (?, ?, ?, 'faculty', NULL)
            """,
            (
                faculty.name.strip(),
                str(faculty.email).lower(),
                hash_password(faculty.password),
            ),
        )
        connection.commit()

        return {
            "message": "Faculty account created",
            "user": {
                "id": cursor.lastrowid,
                "name": faculty.name.strip(),
                "email": str(faculty.email).lower(),
                "role": "faculty",
            },
        }

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists",
        )

    finally:
        connection.close()

class SubjectCreate(BaseModel):
    subject_code: str = Field(min_length=1)
    subject_name: str = Field(min_length=1)
    subject_type: Literal["theory", "lab", "project", "seminar"]
    section: Optional[Literal["A", "B"]] = None

@app.get("/admin/subjects")
def list_subjects(current_user: dict = Depends(require_role("admin"))):
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT id, subject_code, subject_name, subject_type, section
            FROM subjects
            ORDER BY subject_code
            """
        ).fetchall()

        return {"subjects": [dict(row) for row in rows]}

    finally:
        connection.close()

class SubjectUpdate(BaseModel):
    subject_name: Optional[str] = Field(default=None, min_length=1)
    subject_type: Optional[Literal["theory", "lab", "project", "seminar"]] = None
    section: Optional[Literal["A", "B"]] = None


@app.post("/admin/subjects", status_code=201)
def create_subject(
    subject: SubjectCreate,
    current_user: dict = Depends(require_role("admin")),
):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO subjects
                (subject_code, subject_name, subject_type, section)
            VALUES (?, ?, ?, ?)
            """,
            (
                subject.subject_code.strip(),
                subject.subject_name.strip(),
                subject.subject_type,
                subject.section,
            ),
        )
        connection.commit()

        return {
            "message": "Subject created",
            "subject": {
                "id": cursor.lastrowid,
                "subject_code": subject.subject_code.strip(),
                "subject_name": subject.subject_name.strip(),
                "subject_type": subject.subject_type,
                "section": subject.section,
            },
        }

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="A subject with this code already exists",
        )

    finally:
        connection.close()


@app.patch("/admin/subjects/{subject_id}")
def update_subject(
    subject_id: int,
    update: SubjectUpdate,
    current_user: dict = Depends(require_role("admin")),
):
    changes = update.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")

    if changes.get("subject_name", "x") is None or changes.get("subject_type", "x") is None:
        raise HTTPException(
            status_code=400,
            detail="subject_name and subject_type cannot be empty",
        )

    connection = get_connection()

    try:
        subject = connection.execute(
            """
            SELECT id, subject_code, subject_name, subject_type, section
            FROM subjects
            WHERE id = ?
            """,
            (subject_id,),
        ).fetchone()

        if subject is None:
            raise HTTPException(status_code=404, detail="Subject not found")

        updated = dict(subject)
        updated.update(changes)
        updated["subject_name"] = updated["subject_name"].strip()

        connection.execute(
            """
            UPDATE subjects
            SET subject_name = ?, subject_type = ?, section = ?
            WHERE id = ?
            """,
            (
                updated["subject_name"],
                updated["subject_type"],
                updated["section"],
                subject_id,
            ),
        )
        connection.commit()

        return {"message": "Subject updated", "subject": updated}

    finally:
        connection.close()


class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    section: Optional[Literal["A", "B"]] = None


class AssignmentCreate(BaseModel):
    faculty_id: int
    subject_id: int
    section: Literal["A", "B"]


@app.get("/admin/users")
def list_users(
    role: Optional[Literal["admin", "faculty", "student"]] = None,
    current_user: dict = Depends(require_role("admin")),
):
    connection = get_connection()

    try:
        if role is None:
            rows = connection.execute(
                "SELECT id, name, email, role, section FROM users ORDER BY id"
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, name, email, role, section
                FROM users
                WHERE role = ?
                ORDER BY id
                """,
                (role,),
            ).fetchall()

        return {"users": [dict(row) for row in rows]}

    finally:
        connection.close()


@app.patch("/admin/users/{user_id}")
def update_user(
    user_id: int,
    update: UserUpdate,
    current_user: dict = Depends(require_role("admin")),
):
    changes = update.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "name" in changes and changes["name"] is None:
        raise HTTPException(status_code=400, detail="Name cannot be empty")

    connection = get_connection()

    try:
        user = connection.execute(
            "SELECT id, name, email, role, section FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        if "section" in changes:
            if user["role"] != "student":
                raise HTTPException(
                    status_code=400,
                    detail="Only students have a section",
                )
            if changes["section"] is None:
                raise HTTPException(
                    status_code=400,
                    detail="A student's section cannot be cleared",
                )

        updated = dict(user)
        updated.update(changes)
        updated["name"] = updated["name"].strip()

        connection.execute(
            "UPDATE users SET name = ?, section = ? WHERE id = ?",
            (updated["name"], updated["section"], user_id),
        )
        connection.commit()

        return {"message": "User updated", "user": updated}

    finally:
        connection.close()


@app.post("/admin/assignments", status_code=201)
def create_assignment(
    assignment: AssignmentCreate,
    current_user: dict = Depends(require_role("admin")),
):
    connection = get_connection()

    try:
        faculty = connection.execute(
            "SELECT id FROM users WHERE id = ? AND role = 'faculty'",
            (assignment.faculty_id,),
        ).fetchone()

        if faculty is None:
            raise HTTPException(status_code=404, detail="Faculty member not found")

        subject = connection.execute(
            "SELECT id, section FROM subjects WHERE id = ?",
            (assignment.subject_id,),
        ).fetchone()

        if subject is None:
            raise HTTPException(status_code=404, detail="Subject not found")

        if subject["section"] is not None and subject["section"] != assignment.section:
            raise HTTPException(
                status_code=400,
                detail="This subject is not taught to that section",
            )

        cursor = connection.execute(
            """
            INSERT INTO faculty_assignments (faculty_id, subject_id, section)
            VALUES (?, ?, ?)
            """,
            (assignment.faculty_id, assignment.subject_id, assignment.section),
        )
        connection.commit()

        return {
            "message": "Assignment created",
            "assignment": {
                "id": cursor.lastrowid,
                "faculty_id": assignment.faculty_id,
                "subject_id": assignment.subject_id,
                "section": assignment.section,
            },
        }

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="This assignment already exists",
        )

    finally:
        connection.close()


@app.get("/admin/assignments")
def list_assignments(current_user: dict = Depends(require_role("admin"))):
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT fa.id, fa.section,
                   u.id AS faculty_id, u.name AS faculty_name,
                   s.id AS subject_id, s.subject_code, s.subject_name
            FROM faculty_assignments fa
            JOIN users u ON u.id = fa.faculty_id
            JOIN subjects s ON s.id = fa.subject_id
            ORDER BY s.subject_code, fa.section
            """
        ).fetchall()

        return {"assignments": [dict(row) for row in rows]}

    finally:
        connection.close()


@app.delete("/admin/assignments/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    current_user: dict = Depends(require_role("admin")),
):
    connection = get_connection()

    try:
        cursor = connection.execute(
            "DELETE FROM faculty_assignments WHERE id = ?",
            (assignment_id,),
        )
        connection.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Assignment not found")

        return {"message": "Assignment deleted"}

    finally:
        connection.close()