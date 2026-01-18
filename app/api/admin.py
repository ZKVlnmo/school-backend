# app/api/v1/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from typing import Optional

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.schemas.user import UserOut
from app.core.security import get_password_hash

router = APIRouter()

# Схема для обновления ученика
class StudentUpdate(BaseModel):
    full_name: str
    grade: str
    password: Optional[str] = None  # опционально

# Валидные классы (то же, что и на фронтенде)
VALID_GRADES = {
    # Академические
    '5-1', '5-2', '5-3',
    '6-1', '6-2', '6-3', '6-4',
    # Профильные
    '7-БИО', '8-БИО', '9-БИО', '10-БИО', '11-БИО',
    '7-ЛИН', '8-ЛИН', '9-ЛИН', '10-ЛИН', '11-ЛИН',
    '7-МАТ', '8-МАТ', '9-МАТ', '10-МАТ', '11-МАТ',
    '7-ИТ', '8-ИТ', '9-ИТ', '10-ИТ', '11-ИТ',
    '7-ИНЖ', '8-ИНЖ', '9-ИНЖ', '10-ИНЖ', '11-ИНЖ',
    # РОНТЕД
    '5', '6', '7', '8', '9', '10', '11'
}


@router.get("/teachers", response_model=List[UserOut])
def get_teachers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
    return teacher


@router.get("/students")
def get_students_by_grade(
    grade: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Только для администраторов")

    if grade not in VALID_GRADES:
        raise HTTPException(status_code=400, detail=f"Недопустимый класс: {grade}")

    students = db.query(User).filter(User.role == "student", User.grade == grade).all()
    return [
        {
            "id": s.id,
            "full_name": s.full_name,
            "grade": s.grade,
            "email": s.email
        }
        for s in students
    ]


@router.put("/students/{student_id}")
def update_student(
    student_id: int,
    student_update: StudentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    print(f"🎯 Получен запрос на обновление ученика ID={student_id}")
    print(f"   Данные: {student_update.dict()}")

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Только для администраторов")

    if student_update.grade not in VALID_GRADES:
        print(f"❌ Недопустимый класс: {student_update.grade}")
        raise HTTPException(status_code=400, detail=f"Недопустимый класс: {student_update.grade}")

    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        print("❌ Ученик не найден")
        raise HTTPException(status_code=404, detail="Ученик не найден")

    print(f"✅ Найден ученик: {student.full_name} (ID={student.id})")
    print(f"   Новое ФИО: {student_update.full_name}")
    print(f"   Новый класс: {student_update.grade}")
    print(f"   Пароль задан: {bool(student_update.password)}")

    try:
        # Обновляем данные
        student.full_name = student_update.full_name
        student.grade = student_update.grade
        if student_update.password:
            student.hashed_password = get_password_hash(student_update.password)
            print("   🔑 Пароль обновлён")

        print("💾 Выполняю commit...")
        db.commit()
        db.refresh(student)
        print("✅ Изменения успешно сохранены в БД")
    except Exception as e:
        print(f"💥 Ошибка при сохранении: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при сохранении данных")

    return {"message": "Ученик обновлён"}


@router.delete("/students/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Только для администраторов")

    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Ученик не найден")

    db.delete(student)
    db.commit()
    return {"message": "Ученик удалён"}