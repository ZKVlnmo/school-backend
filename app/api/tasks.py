from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
from pathlib import Path
from fastapi.responses import FileResponse
from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.task import Task as TaskModel
from app.db.models.student_task import StudentTask
from app.schemas.task import Task, TaskWithSubmissionStatus

router = APIRouter()

SUBMISSION_UPLOAD_DIR = Path("uploads/submissions")
SUBMISSION_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_DIR = Path("uploads/tasks")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class TaskCreateRequest(BaseModel):
    title: str
    description: str
    subject: str
    reason: str
    due_date: Optional[datetime] = None
    student_ids: List[int]
    grade: str


class TaskUpdateRequest(BaseModel):
    title: str
    description: str
    subject: str
    reason: str
    due_date: Optional[datetime] = None
    student_ids: List[int]


ALLOWED_REASONS = {"homework", "illness", "not_submitted"}


@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(
        task_in: TaskCreateRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Только учитель")

    if task_in.reason not in ALLOWED_REASONS:
        raise HTTPException(status_code=422, detail="Недопустимое значение 'reason'")

    if not task_in.student_ids:
        raise HTTPException(status_code=400, detail="Выберите учеников")

    students = []
    grade = None
    for student_id in task_in.student_ids:
        student = db.query(User).filter(
            User.id == student_id,
            User.role == "student"
        ).first()
        if not student:
            raise HTTPException(status_code=400, detail=f"Ученик {student_id} не найден")
        students.append(student)
        if grade is None:
            grade = student.grade
        elif student.grade != grade:
            raise HTTPException(status_code=400, detail="Ученики из разных классов")

    if grade != task_in.grade:
        raise HTTPException(status_code=400, detail="Несоответствие класса")

    db_task = TaskModel(
        title=task_in.title,
        description=task_in.description,
        subject=task_in.subject,
        reason=task_in.reason,
        due_date=task_in.due_date,
        grade=grade,
        teacher_id=current_user.id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    for student in students:
        db_student_task = StudentTask(task_id=db_task.id, student_id=student.id)
        db.add(db_student_task)
    db.commit()

    return db_task


@router.put("/{task_id}", response_model=Task)
def update_task(
        task_id: int,
        task_in: TaskUpdateRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Только учитель")

    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.teacher_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    for key, value in task_in.dict().items():
        if key != "student_ids":
            setattr(task, key, value)

    db.query(StudentTask).filter(StudentTask.task_id == task_id).delete()

    students = []
    grade = task.grade
    for student_id in task_in.student_ids:
        student = db.query(User).filter(
            User.id == student_id,
            User.role == "student",
            User.grade == grade
        ).first()
        if not student:
            raise HTTPException(status_code=400, detail=f"Ученик {student_id} не найден")
        students.append(student)

    for student in students:
        db_student_task = StudentTask(task_id=task_id, student_id=student.id)
        db.add(db_student_task)

    db.commit()
    db.refresh(task)
    return task

@router.get("/by-grade/{grade}")
def get_tasks_by_grade(
        grade: str,
        scope: str = "mine",
        page: int = 1,
        size: int = 10,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Только учитель")

    query = db.query(TaskModel).filter(TaskModel.grade == grade)

    if scope == "mine":
        query = query.filter(TaskModel.teacher_id == current_user.id)
    elif scope != "all":
        raise HTTPException(status_code=400, detail="scope must be 'mine' or 'all'")

    query = query.order_by(TaskModel.id.desc())
    total = query.count()
    tasks = query.offset((page - 1) * size).limit(size).all()

    result = []
    for task in tasks:
        teacher = db.query(User.full_name).filter(User.id == task.teacher_id).first()
        student_ids = db.query(StudentTask.student_id).filter(StudentTask.task_id == task.id).all()
        student_ids = [sid[0] for sid in student_ids]

        # 🔽 ЗАГРУЖАЕМ ФАЙЛЫ ЗАДАНИЯ
        task_files = []
        task_dir = UPLOAD_DIR / str(task.id)
        if task_dir.exists():
            task_files = [f.name for f in task_dir.iterdir() if f.is_file()]

        result.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "subject": task.subject,
            "reason": task.reason,
            "due_date": task.due_date,
            "grade": task.grade,
            "teacher_id": task.teacher_id,
            "teacher_name": teacher[0] if teacher else "—",
            "student_ids": student_ids,
            "files": task_files  # ← теперь есть!
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if size > 0 else 1
    }

@router.post("/{task_id}/upload")
def upload_task_files(
        task_id: int,
        files: List[UploadFile] = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Только учитель")

    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.teacher_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Максимум 5 файлов")

    task_dir = UPLOAD_DIR / str(task_id)
    task_dir.mkdir(exist_ok=True)

    uploaded = []
    for file in files:
        if not file.filename:
            continue
        ext = file.filename.split('.')[-1] if '.' in file.filename else ''
        safe_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
        with open(task_dir / safe_name, "wb") as f:
            f.write(file.file.read())
        uploaded.append(file.filename)

    return {"uploaded": len(uploaded)}


@router.get("/{task_id}/files/{filename}")
def download_task_file(task_id: int, filename: str):
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Недопустимое имя файла")
    file_path = UPLOAD_DIR / str(task_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(file_path)


# === НОВЫЕ ЭНДПОИНТЫ ДЛЯ ПРОВЕРКИ ЗАДАНИЙ ===

@router.get("/submissions")
def get_submissions(
        grade: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Только для учителей")

    query = db.query(StudentTask).join(TaskModel).filter(
        StudentTask.status == "submitted",
        TaskModel.teacher_id == current_user.id
    )

    if grade:
        query = query.filter(TaskModel.grade == grade)

    submissions = query.all()
    result = []

    for sub in submissions:
        student_files = []
        submission_dir = SUBMISSION_UPLOAD_DIR / str(sub.task_id) / str(sub.student_id)
        if submission_dir.exists():
            student_files = [f.name for f in submission_dir.iterdir() if f.is_file()]

        result.append({
            "id": sub.id,
            "task_title": sub.task.title,
            "student_name": sub.student.full_name,
            "grade": sub.task.grade,
            "student_comment": sub.comment,
            "student_files": student_files,
        })

    return result


@router.get("/submissions/{submission_id}/files/{filename}")
def download_student_file(
        submission_id: int,
        filename: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Только для учителей")

    student_task = db.query(StudentTask).join(TaskModel).filter(
        StudentTask.id == submission_id,
        TaskModel.teacher_id == current_user.id
    ).first()

    if not student_task:
        raise HTTPException(status_code=404, detail="Файл не найден")

    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Недопустимое имя файла")

    file_path = SUBMISSION_UPLOAD_DIR / str(student_task.task_id) / str(student_task.student_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")

    response = FileResponse(
        file_path,
        filename=filename,
        content_disposition_type="inline"  # ← КЛЮЧЕВОЕ: открывать в браузере
    )
    return response


@router.post("/submissions/{submission_id}/accept")
def accept_submission(
    submission_id: int,
    grade: int = Form(...),  # ← теперь используем
    comment: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Только для учителей")

    student_task = db.query(StudentTask).join(TaskModel).filter(
        StudentTask.id == submission_id,
        TaskModel.teacher_id == current_user.id
    ).first()

    if not student_task:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    if grade not in [2, 3, 4, 5]:
        raise HTTPException(status_code=400, detail="Оценка должна быть от 2 до 5")

    student_task.status = "accepted"
    student_task.teacher_comment = comment
    student_task.grade = grade  # ← сохраняем оценку
    db.commit()

    return {"status": "accepted"}


@router.post("/submissions/{submission_id}/reject")
def reject_submission(
        submission_id: int,
        comment: str = Form(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Только для учителей")

    student_task = db.query(StudentTask).join(TaskModel).filter(
        StudentTask.id == submission_id,
        TaskModel.teacher_id == current_user.id
    ).first()

    if not student_task:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    if not comment.strip():
        raise HTTPException(status_code=400, detail="Комментарий обязателен")

    student_task.status = "rejected"
    student_task.teacher_comment = comment
    db.commit()

    return {"status": "rejected"}

@router.get("/accepted")
def get_accepted_tasks(
    page: int = 1,
    size: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "student":
        raise HTTPException(403, "Только для учеников")

    total = db.query(TaskModel).join(StudentTask).filter(
        StudentTask.student_id == current_user.id,
        StudentTask.status == "accepted"
    ).count()

    tasks = (
        db.query(TaskModel)
        .join(StudentTask)
        .filter(
            StudentTask.student_id == current_user.id,
            StudentTask.status == "accepted"
        )
        .order_by(TaskModel.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    result = []
    for task in tasks:
        student_task = db.query(StudentTask).filter(
            StudentTask.task_id == task.id,
            StudentTask.student_id == current_user.id
        ).first()

        teacher = db.query(User.full_name).filter(User.id == task.teacher_id).first()
        teacher_name = teacher[0] if teacher else "—"

        task_files = []
        task_dir = UPLOAD_DIR / str(task.id)
        if task_dir.exists():
            task_files = [f.name for f in task_dir.iterdir() if f.is_file()]

        student_files = []
        submission_dir = SUBMISSION_UPLOAD_DIR / str(task.id) / str(current_user.id)
        if submission_dir.exists():
            student_files = [f.name for f in submission_dir.iterdir() if f.is_file()]

        result.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "subject": task.subject,
            "grade": task.grade,
            "teacher_name": teacher_name,
            "teacher_grade": student_task.grade if student_task else None,
            "teacher_comment": student_task.teacher_comment if student_task else None,
            "comment": student_task.comment if student_task else None,
            "student_files": student_files,
            "files": task_files,
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, (total + size - 1) // size)
    }
from sqlalchemy.orm import joinedload  # ← добавьте в импорты
@router.get("/submissions/accepted")
def get_accepted_submissions(
    grade: Optional[str] = None,
    page: int = 1,
    size: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Только для учителей")

    query = db.query(StudentTask).join(TaskModel).filter(
        StudentTask.status == "accepted",
        TaskModel.teacher_id == current_user.id
    )

    if grade:
        query = query.filter(TaskModel.grade == grade)

    total = query.count()
    submissions = (
        query.order_by(StudentTask.id.desc())
        .options(joinedload(StudentTask.student), joinedload(StudentTask.task))
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    # 👇 ЛОГИРУЕМ, ЧТО ПРИХОДИТ
    for sub in submissions:
        print(f"Student ID: {sub.student_id}, Full Name: {sub.student.full_name if sub.student else 'NO STUDENT'}")

    result = []
    for sub in submissions:
        task_files = []
        task_dir = UPLOAD_DIR / str(sub.task_id)
        if task_dir.exists():
            task_files = [f.name for f in task_dir.iterdir() if f.is_file()]

        student_files = []
        submission_dir = SUBMISSION_UPLOAD_DIR / str(sub.task_id) / str(sub.student_id)
        if submission_dir.exists():
            student_files = [f.name for f in submission_dir.iterdir() if f.is_file()]

        result.append({
            "id": sub.id,
            "task_id": sub.task_id,
            "task_title": sub.task.title,
            "student_name": sub.student.full_name if sub.student else "—",  # ← безопасно
            "grade": sub.task.grade,
            "teacher_grade": sub.grade,
            "teacher_comment": sub.teacher_comment,
            "student_comment": sub.comment,
            "submitted_at": sub.submitted_at,
            "student_files": student_files,
            "task_files": task_files,
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, (total + size - 1) // size)
    }
@router.get("/{task_id}/files")
def list_task_files(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Только учитель")

    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.teacher_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    task_dir = UPLOAD_DIR / str(task_id)
    files = []
    if task_dir.exists():
        files = [f.name for f in task_dir.iterdir() if f.is_file()]

    return {"files": files}


@router.delete("/{task_id}/files/{filename}")
def delete_task_file(
    task_id: int,
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Только учитель")

    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.teacher_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Недопустимое имя файла")

    file_path = UPLOAD_DIR / str(task_id) / filename
    if file_path.exists():
        file_path.unlink()

    return {"detail": "Файл удалён"}