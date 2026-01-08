from pydantic import BaseModel
from datetime import date
from typing import Optional

class AttendanceBase(BaseModel):
    date: date
    quarter: int
    grade: str
    status: Optional[str] = None

class AttendanceCreate(AttendanceBase):
    student_id: int

class AttendanceOut(AttendanceBase):
    id: int
    student_id: int

    class Config:
        from_attributes = True