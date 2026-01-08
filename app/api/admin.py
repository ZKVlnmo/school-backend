# app/api/v1/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.schemas.user import UserOut  # или создайте схему

router = APIRouter()

@router.get("/teachers", response_model=List[UserOut])
def get_teachers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Только админ может видеть учителей
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Только для администраторов")

    teachers = db.query(User).filter(User.role == "teacher").all()
    return teachers


@router.post("/teachers/{teacher_id}/approve", response_model=UserOut)
def approve_teacher(
        teacher_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Только для администраторов")

    teacher = db.query(User).filter(
        User.id == teacher_id,
        User.role == "teacher"
    ).first()

    if not teacher:
        raise HTTPException(status_code=404, detail="Учитель не найден")

    if teacher.is_verified:
        raise HTTPException(status_code=400, detail="Учитель уже подтверждён")

    teacher.is_verified = True
    db.commit()
    db.refresh(teacher)

    return teacher  # ← Возвращаем обновлённого учителя