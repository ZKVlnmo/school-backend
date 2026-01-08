from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import List

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.attendance import Attendance
from app.schemas.attendance import AttendanceOut, AttendanceCreate

router = APIRouter()

# Получить всех учеников класса
def get_students_in_grade(db: Session, grade: str):
    return db.query(User).filter(User.role == "student", User.grade == grade).all()

# Получить все записи посещаемости для класса и четверти
@router.get("/{grade}/quarter/{quarter}", response_model=List[AttendanceOut])
def get_attendance_for_quarter(
    grade: str,
    quarter: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Только для учителей")
    records = db.query(Attendance).filter(
        Attendance.grade == grade,
        Attendance.quarter == quarter
    ).all()
    return records

# Обновить статус посещения
@router.post("/{grade}/record", response_model=AttendanceOut)
def update_attendance_record(
    grade: str,
    record: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Только для учителей")

    # Проверяем, что ученик учится в этом классе
    student = db.query(User).filter(
        User.id == record.student_id,
        User.grade == grade
    ).first()
    if not student:
        raise HTTPException(status_code=400, detail="Ученик не найден в классе")

    # Находим или создаём запись
    existing = db.query(Attendance).filter(
        Attendance.student_id == record.student_id,
        Attendance.date == record.date,
        Attendance.grade == grade
    ).first()

    if existing:
        existing.status = record.status
    else:
        existing = Attendance(
            student_id=record.student_id,
            date=record.date,
            quarter=record.quarter,
            grade=grade,
            status=record.status
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing

