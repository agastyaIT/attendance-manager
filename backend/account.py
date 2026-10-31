from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth import hash_password, verify_password
from backend.database import get_connection
from backend.security import get_current_user

router = APIRouter()


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


@router.post("/me/password")
def change_password(
    data: PasswordChange,
    current_user: dict = Depends(get_current_user),
):
    connection = get_connection()

    try:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (current_user["id"],),
        ).fetchone()

        if row is None or not verify_password(
            data.current_password, row["password_hash"]
        ):
            raise HTTPException(
                status_code=400, detail="Current password is incorrect"
            )

        if data.new_password == data.current_password:
            raise HTTPException(
                status_code=400,
                detail="New password must be different from the current one",
            )

        connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(data.new_password), current_user["id"]),
        )
        connection.commit()

        return {"message": "Password changed"}

    finally:
        connection.close()