# app/api/students.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, Path, Form, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path as SysPath
from datetime import datetime
import logging
import httpx
logger = logging.getLogger(__name__)
# Исправлена опечатка: deps (не deeps!)
from app.api.deps import get_db, get_current_user
from app.crud.user import get_students_by_grade
from app.schemas.user import UserOut
from app.db.models.user import User
from app.db.models.task import Task as TaskModel
from app.db.models.student_task import StudentTask
from app.core.ai_service import analyze_and_save_ai
import asyncio

router = APIRouter()

UPLOAD_DIR = SysPath("uploads/tasks")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SUBMISSION_UPLOAD_DIR = SysPath("uploads/submissions")
SUBMISSION_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/grade/{grade}", response_model=List[UserOut])
def get_students_by_grade_endpoint(
    grade: str = Path(..., description="Номер класса, например: 10А, 9Б"),
    db: Session = Depends(get_db),
):
    students = get_students_by_grade(db, grade)
    return students

@router.get("/tasks")
def get_student_tasks(
    page: int = 1,
    size: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Только для учеников")

    # Подсчёт общего количества заданий для ученика
    total = db.query(StudentTask).filter(
        StudentTask.student_id == current_user.id
    ).count()

    # Получаем студент_таски с пагинацией
    student_tasks = (
        db.query(StudentTask)
        .filter(StudentTask.student_id == current_user.id)
        .order_by(StudentTask.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    result = []
    for st in student_tasks:
        task = st.task
        if not task:
            continue  # пропускаем, если задание удалено

        teacher = db.query(User.full_name).filter(User.id == task.teacher_id).first()
        teacher_name = teacher[0] if teacher else "—"

        # Файлы задания
        task_files = []
        task_dir = UPLOAD_DIR / str(task.id)
        if task_dir.exists():
            task_files = [f.name for f in task_dir.iterdir() if f.is_file()]

        # Файлы ученика
        student_files = []
        submission_dir = SUBMISSION_UPLOAD_DIR / str(task.id) / str(current_user.id)
        if submission_dir.exists():
            student_files = [f.name for f in submission_dir.iterdir() if f.is_file()]

        result.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "subject": task.subject,
            "reason": task.reason,
            "due_date": task.due_date,
            "grade": task.grade,
            "teacher_name": teacher_name,
            "files": task_files,
            "submitted_at": st.submitted_at,
            "status": st.status,
            "teacher_comment": st.teacher_comment,
            "teacher_grade": st.grade,
            "comment": st.comment,
            "student_files": student_files,
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, (total + size - 1) // size)
    }

@router.post("/tasks/{task_id}/submit")
async def submit_task(
        task_id: int,
        comment: Optional[str] = Form(default=None),
        files: List[UploadFile] = File(default_factory=list),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Только для учеников")

    student_task = db.query(StudentTask).filter(
        StudentTask.task_id == task_id,
        StudentTask.student_id == current_user.id
    ).first()

    if not student_task:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    # Сохраняем отправку
    student_task.is_submitted = True
    student_task.submitted_at = datetime.utcnow()
    student_task.comment = comment
    student_task.status = "submitted"
    student_task.teacher_comment = None

    # Загружаем файлы
    if files:
        task_dir = SUBMISSION_UPLOAD_DIR / str(task_id) / str(current_user.id)
        task_dir.mkdir(parents=True, exist_ok=True)
        for file in files:
            if file.filename:
                ext = file.filename.split('.')[-1] if '.' in file.filename else ''
                safe_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
                content = await file.read()
                with open(task_dir / safe_name, "wb") as f:
                    f.write(content)

    db.commit()

    # После db.commit() в submit_task

    # === ВЫЗОВ ИИ, ЕСЛИ ВКЛЮЧЁН ===
    if student_task.task.enable_ai_analysis:
        logger.info(f"🚀 [Students] Запуск ИИ в фоне для submission_id={student_task.id}")

        # Создаём новую сессию БД для фоновой задачи
        from app.db.session import SessionLocal  # ← убедитесь, что у вас есть такой файл
        bg_db = SessionLocal()

        # Запускаем без await → не блокирует ответ
        asyncio.create_task(
            analyze_and_save_ai(
                db=bg_db,
                student_task_id=student_task.id,
                teacher_task=student_task.task.description,
                student_answer=student_task.comment or ""
            )
        )
    return {"status": "submitted", "message": "Задание отправлено на проверку"}


