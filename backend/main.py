from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
import sqlite3
from backend.database import initialize_database, get_connection
from backend.auth import hash_password, verify_password
from backend.security import create_access_token
from backend.security import get_current_user, require_role
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm


app = FastAPI(title="Attendance Manager API")


@app.on_event("startup")
def startup():
    initialize_database()


class StudentRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    section: str

class StudentLogin(BaseModel):
    email: EmailStr
    password: str


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


@app.get("/admin/ping")
def admin_ping(current_user: dict = Depends(require_role("admin"))):
    return {"message": "Admin access granted", "user": current_user["name"]}