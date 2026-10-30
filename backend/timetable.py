import sqlite3
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.database import get_connection
from backend.security import require_role

router = APIRouter()

TIME_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"

DAY_NAMES = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday",
}


class TimetableCreate(BaseModel):
    subject_id: int
    section: Literal["A", "B"]
    faculty_id: Optional[int] = None
    day_of_week: int = Field(ge=1, le=7)
    start_time: str = Field(pattern=TIME_PATTERN)
    end_time: str = Field(pattern=TIME_PATTERN)
    room: Optional[str] = None


@router.post("/admin/timetable", status_code=201)
def create_timetable_entry(
    entry: TimetableCreate,
    current_user: dict = Depends(require_role("admin")),
):
    if entry.end_time <= entry.start_time:
        raise HTTPException(
            status_code=400,
            detail="end_time must be later than start_time",
        )

    room = entry.room.strip() if entry.room else None

    connection = get_connection()

    try:
        subject = connection.execute(
            "SELECT id, section FROM subjects WHERE id = ?",
            (entry.subject_id,),
        ).fetchone()

        if subject is None:
            raise HTTPException(status_code=404, detail="Subject not found")

        if subject["section"] is not None and subject["section"] != entry.section:
            raise HTTPException(
                status_code=400,
                detail="This subject is not taught to that section",
            )

        if entry.faculty_id is not None:
            faculty = connection.execute(
                "SELECT id FROM users WHERE id = ? AND role = 'faculty'",
                (entry.faculty_id,),
            ).fetchone()

            if faculty is None:
                raise HTTPException(status_code=404, detail="Faculty member not found")

            assigned = connection.execute(
                """
                SELECT id FROM faculty_assignments
                WHERE faculty_id = ? AND subject_id = ? AND section = ?
                """,
                (entry.faculty_id, entry.subject_id, entry.section),
            ).fetchone()

            if assigned is None:
                raise HTTPException(
                    status_code=400,
                    detail="This faculty member is not assigned to that subject and section",
                )

        cursor = connection.execute(
            """
            INSERT INTO timetable_entries
                (subject_id, section, faculty_id, day_of_week,
                 start_time, end_time, room)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.subject_id,
                entry.section,
                entry.faculty_id,
                entry.day_of_week,
                entry.start_time,
                entry.end_time,
                room,
            ),
        )
        connection.commit()

        return {
            "message": "Timetable entry created",
            "entry": {
                "id": cursor.lastrowid,
                "subject_id": entry.subject_id,
                "section": entry.section,
                "faculty_id": entry.faculty_id,
                "day_of_week": entry.day_of_week,
                "start_time": entry.start_time,
                "end_time": entry.end_time,
                "room": room,
            },
        }

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Clash: this section or this faculty member already has a class at that day and time",
        )

    finally:
        connection.close()

@router.get("/admin/timetable")
def list_timetable(
    section: Optional[Literal["A", "B"]] = None,
    day_of_week: Optional[int] = Query(default=None, ge=1, le=7),
    current_user: dict = Depends(require_role("admin")),
):
    conditions = []
    values = []

    if section is not None:
        conditions.append("t.section = ?")
        values.append(section)

    if day_of_week is not None:
        conditions.append("t.day_of_week = ?")
        values.append(day_of_week)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    connection = get_connection()

    try:
        rows = connection.execute(
            f"""
            SELECT t.id, t.section, t.day_of_week, t.start_time, t.end_time,
                   t.room, t.subject_id, s.subject_code, s.subject_name,
                   t.faculty_id, u.name AS faculty_name
            FROM timetable_entries t
            JOIN subjects s ON s.id = t.subject_id
            LEFT JOIN users u ON u.id = t.faculty_id
            {where_clause}
            ORDER BY t.section, t.day_of_week, t.start_time
            """,
            values,
        ).fetchall()

        return {"timetable": [dict(row) for row in rows]}

    finally:
        connection.close()


class TimetableUpdate(BaseModel):
    subject_id: Optional[int] = None
    section: Optional[Literal["A", "B"]] = None
    faculty_id: Optional[int] = None
    day_of_week: Optional[int] = Field(default=None, ge=1, le=7)
    start_time: Optional[str] = Field(default=None, pattern=TIME_PATTERN)
    end_time: Optional[str] = Field(default=None, pattern=TIME_PATTERN)
    room: Optional[str] = None


@router.patch("/admin/timetable/{entry_id}")
def update_timetable_entry(
    entry_id: int,
    update: TimetableUpdate,
    current_user: dict = Depends(require_role("admin")),
):
    changes = update.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")

    for field in ("subject_id", "section", "day_of_week", "start_time", "end_time"):
        if field in changes and changes[field] is None:
            raise HTTPException(status_code=400, detail=f"{field} cannot be empty")

    connection = get_connection()

    try:
        existing = connection.execute(
            """
            SELECT id, subject_id, section, faculty_id, day_of_week,
                   start_time, end_time, room
            FROM timetable_entries
            WHERE id = ?
            """,
            (entry_id,),
        ).fetchone()

        if existing is None:
            raise HTTPException(status_code=404, detail="Timetable entry not found")

        updated = dict(existing)
        updated.update(changes)
        updated["room"] = updated["room"].strip() if updated["room"] else None

        if updated["end_time"] <= updated["start_time"]:
            raise HTTPException(
                status_code=400,
                detail="end_time must be later than start_time",
            )

        subject = connection.execute(
            "SELECT id, section FROM subjects WHERE id = ?",
            (updated["subject_id"],),
        ).fetchone()

        if subject is None:
            raise HTTPException(status_code=404, detail="Subject not found")

        if subject["section"] is not None and subject["section"] != updated["section"]:
            raise HTTPException(
                status_code=400,
                detail="This subject is not taught to that section",
            )

        if updated["faculty_id"] is not None:
            faculty = connection.execute(
                "SELECT id FROM users WHERE id = ? AND role = 'faculty'",
                (updated["faculty_id"],),
            ).fetchone()

            if faculty is None:
                raise HTTPException(status_code=404, detail="Faculty member not found")

            assigned = connection.execute(
                """
                SELECT id FROM faculty_assignments
                WHERE faculty_id = ? AND subject_id = ? AND section = ?
                """,
                (updated["faculty_id"], updated["subject_id"], updated["section"]),
            ).fetchone()

            if assigned is None:
                raise HTTPException(
                    status_code=400,
                    detail="This faculty member is not assigned to that subject and section",
                )

        connection.execute(
            """
            UPDATE timetable_entries
            SET subject_id = ?, section = ?, faculty_id = ?, day_of_week = ?,
                start_time = ?, end_time = ?, room = ?
            WHERE id = ?
            """,
            (
                updated["subject_id"],
                updated["section"],
                updated["faculty_id"],
                updated["day_of_week"],
                updated["start_time"],
                updated["end_time"],
                updated["room"],
                entry_id,
            ),
        )
        connection.commit()

        return {"message": "Timetable entry updated", "entry": updated}

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Clash: this section or this faculty member already has a class at that day and time",
        )

    finally:
        connection.close()

@router.get("/student/timetable")
def my_timetable(current_user: dict = Depends(require_role("student"))):
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT t.id, t.day_of_week, t.start_time, t.end_time, t.room,
                   s.id AS subject_id, s.subject_code, s.subject_name,
                   s.subject_type, u.name AS faculty_name
            FROM timetable_entries t
            JOIN subjects s ON s.id = t.subject_id
            LEFT JOIN users u ON u.id = t.faculty_id
            WHERE t.section = ?
            ORDER BY t.day_of_week, t.start_time
            """,
            (current_user["section"],),
        ).fetchall()

        classes_by_day = {day: [] for day in range(1, 8)}

        for row in rows:
            classes_by_day[row["day_of_week"]].append(
                {
                    "entry_id": row["id"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "room": row["room"],
                    "subject_id": row["subject_id"],
                    "subject_code": row["subject_code"],
                    "subject_name": row["subject_name"],
                    "subject_type": row["subject_type"],
                    "faculty_name": row["faculty_name"],
                }
            )

        return {
            "section": current_user["section"],
            "today": date.today().isoweekday(),
            "days": [
                {
                    "day_of_week": day,
                    "day_name": DAY_NAMES[day],
                    "classes": classes_by_day[day],
                }
                for day in range(1, 8)
            ],
        }

    finally:
        connection.close()