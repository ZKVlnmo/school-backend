from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
from pathlib import Path
from fastapi.responses import FileResponse

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.task import Task as TaskModel
from app.db.models.student_task import StudentTask

from app.schemas.task import (
    Task,
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskWithSubmissionStatus
)
from app.crud.task import create_task as crud_create_task
from app.crud.task import update_task as crud_update_task

router = APIRouter()

SUBMISSION_UPLOAD_DIR = Path("uploads/submissions")
SUBMISSION_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_DIR = Path("uploads/tasks")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_REASONS = {"homework", "illness", "not_submitted"}


@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task_endpoint(
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

    task_data = task_in.dict()
    task_data["teacher_id"] = current_user.id
    task_data["grade"] = grade

    db_task = crud_create_task(db, task_data)
    return db_task


@router.put("/{task_id}", response_model=Task)
def update_task_endpoint(
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

    grade = task.grade
    for student_id in task_in.student_ids:
        student = db.query(User).filter(
            User.id == student_id,
            User.role == "student",
            User.grade == grade
        ).first()
        if not student:
            raise HTTPException(status_code=400, detail=f"Ученик {student_id} не найден")

    task_data = task_in.dict()
    task_data["grade"] = grade

    updated_task = crud_update_task(db, task_id, task_data)
    if not updated_task:
        raise HTTPException(status_code=404, detail="Не удалось обновить задание")
    return updated_task


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

    total = query.count()
    tasks = query.order_by(TaskModel.id.desc()).offset((page - 1) * size).limit(size).all()

    result = []
    for task in tasks:
        teacher = db.query(User.full_name).filter(User.id == task.teacher_id).first()
        student_ids = [st.student_id for st in task.student_tasks]

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
            "files": task_files,
            "enable_ai_analysis": task.enable_ai_analysis
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, (total + size - 1) // size)
    }


# === ФАЙЛОВЫЕ ОПЕРАЦИИ ===

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

    for file in files:
        if file.filename:
            ext = file.filename.split('.')[-1] if '.' in file.filename else ''
            safe_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
            with open(task_dir / safe_name, "wb") as f:
                f.write(file.file.read())

    return {"uploaded": len(files)}


@router.get("/{task_id}/files/{filename}")
def download_task_file(task_id: int, filename: str):
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Недопустимое имя файла")
    file_path = UPLOAD_DIR / str(task_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(file_path, filename=filename)


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
    files = [f.name for f in task_dir.iterdir() if f.is_file()] if task_dir.exists() else []
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


# === ПРОВЕРКА ЗАДАНИЙ ===

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
        submission_dir = SUBMISSION_UPLOAD_DIR / str(sub.task_id) / str(sub.student_id)
        student_files = [f.name for f in submission_dir.iterdir() if f.is_file()] if submission_dir.exists() else []
        teacher = db.query(User.full_name).filter(User.id == sub.task.teacher_id).first()

        result.append({
            "id": sub.id,
            "task_id": sub.task_id,
            "task_title": sub.task.title,
            "description": sub.task.description,  # ← добавлено
            "subject": sub.task.subject,  # ← добавлено
            "teacher_name": teacher[0] if teacher else "—",  # ← добавлено
            "task_enable_ai_analysis": sub.task.enable_ai_analysis,
            "student_name": sub.student.full_name,
            "grade": sub.task.grade,
            "student_comment": sub.comment,
            "student_files": student_files,
            "ai_analysis": sub.ai_analysis,
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
        raise HTTPException(status_code=404, detail="Работа не найдена")

    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Недопустимое имя файла")

    file_path = SUBMISSION_UPLOAD_DIR / str(student_task.task_id) / str(student_task.student_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")

    return FileResponse(file_path, filename=filename, content_disposition_type="inline")


@router.post("/submissions/{submission_id}/accept")
def accept_submission(
    submission_id: int,
    grade: int = Form(...),
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
    student_task.grade = grade
    student_task.teacher_comment = comment
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
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

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
        teacher = db.query(User.full_name).filter(User.id == sub.task.teacher_id).first()

        result.append({
            "id": sub.id,
            "task_id": sub.task_id,
            "task_title": sub.task.title,
            "description": sub.task.description,  # ← добавьте
            "subject": sub.task.subject,  # ← добавьте
            "teacher_name": teacher[0] if teacher else "—",  # ← добавьте
            "student_name": sub.student.full_name if sub.student else "—",
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


@router.delete("/{task_id}")
def delete_task(
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

    # Удаляем связанные файлы задания
    task_dir = UPLOAD_DIR / str(task_id)
    if task_dir.exists():
        import shutil
        shutil.rmtree(task_dir)

    # Удаляем все работы учеников
    db.query(StudentTask).filter(StudentTask.task_id == task_id).delete()

    # Удаляем само задание
    db.delete(task)
    db.commit()

    return {"detail": "Задание удалено"}


@router.get("/grades/{grade}")
def get_grades_table(
    grade: str,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Только для учителей")

    # 1. Все ученики класса
    students = db.query(User).filter(
        User.grade == grade,
        User.role == "student"
    ).order_by(User.full_name).all()

    if not students:
        return {
            "students": [],
            "tasks": [],
            "cells": {}
        }

    student_ids_list = [s.id for s in students]

    # 2. Все задания для класса
    task_query = db.query(TaskModel).filter(
        TaskModel.grade == grade,
        TaskModel.teacher_id == current_user.id
    )
    if subject and subject != "Все предметы":
        task_query = task_query.filter(TaskModel.subject == subject)

    tasks = task_query.order_by(TaskModel.due_date.desc()).all()

    # 3. Загружаем student_ids для каждого задания
    # Используем связь через StudentTask
    task_student_map = {}
    if tasks:
        task_ids = [t.id for t in tasks]
        student_assignments = db.query(StudentTask.task_id, StudentTask.student_id).filter(
            StudentTask.task_id.in_(task_ids)
        ).all()
        for task_id, student_id in student_assignments:
            if task_id not in task_student_map:
                task_student_map[task_id] = set()
            task_student_map[task_id].add(student_id)

    # 4. Все работы учеников (присланные + принятые)
    student_tasks = db.query(StudentTask).filter(
        StudentTask.task_id.in_([t.id for t in tasks]),
        StudentTask.student_id.in_(student_ids_list)
    ).all()

    st_map = {
        (st.task_id, st.student_id): st
        for st in student_tasks
    }

    # 5. Формируем cells
    cells = {}
    for task in tasks:
        assigned_students = task_student_map.get(task.id, set())
        for student in students:
            key = f"{task.id}-{student.id}"
            st = st_map.get((task.id, student.id))
            if st:
                cells[key] = {
                    "status": st.status,
                    "grade": st.grade if st.status == "accepted" else None,
                    "submission_id": st.id
                }
            elif student.id in assigned_students:
                cells[key] = {
                    "status": "assigned",
                    "grade": None,
                    "submission_id": None
                }
            else:
                cells[key] = {
                    "status": "not_assigned",
                    "grade": None,
                    "submission_id": None
                }

    return {
        "students": [
            {"id": s.id, "full_name": s.full_name}
            for s in students
        ],
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "subject": t.subject,
                "due_date": t.due_date
            }
            for t in tasks
        ],
        "cells": cells
    }

@router.get("/submission/detail")
def get_submission_detail(
    task_id: int,
    student_id: int,
    grade: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Только для учителей")

    # Проверка, что задание принадлежит учителю и классу
    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.teacher_id == current_user.id,
        TaskModel.grade == grade
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    # Ищем в присланных (status = 'submitted')
    submission = db.query(StudentTask).filter(
        StudentTask.task_id == task_id,
        StudentTask.student_id == student_id
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Работа не найдена")

    # Собираем данные
    submission_dir = SUBMISSION_UPLOAD_DIR / str(task_id) / str(student_id)
    student_files = [f.name for f in submission_dir.iterdir() if f.is_file()] if submission_dir.exists() else []
    teacher = db.query(User.full_name).filter(User.id == task.teacher_id).first()

    return {
        "id": submission.id,
        "task_id": task_id,
        "student_id": student_id,
        "task_title": task.title,
        "description": task.description,
        "subject": task.subject,
        "teacher_name": teacher[0] if teacher else "—",
        "task_enable_ai_analysis": task.enable_ai_analysis,
        "student_name": submission.student.full_name if submission.student else "—",
        "grade": task.grade,
        "student_comment": submission.comment,
        "teacher_comment": submission.teacher_comment,  # ← ДОБАВЛЕНО
        "ai_analysis": submission.ai_analysis,  # ← УЖЕ БЫЛО
        "student_files": student_files,
        "status": submission.status,
        "teacher_grade": submission.grade if submission.status == "accepted" else None,
    }
@router.get("/students/{student_id}/grades")
def get_student_grades(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # === 1. Проверка прав доступа ===
    if current_user.role == "student":
        # Ученик может смотреть ТОЛЬКО СЕБЯ
        if current_user.id != student_id:
            raise HTTPException(status_code=403, detail="Нет доступа к чужому журналу")
        student = current_user  # используем самого пользователя
    elif current_user.role == "teacher":
        # Учитель может смотреть ученика, только если тот в его классе
        student = db.query(User).filter(
            User.id == student_id,
            User.role == "student"
        ).first()
        if not student:
            raise HTTPException(status_code=404, detail="Ученик не найден")

        # Проверяем, что ученик из класса учителя (через задания)
        # Получаем хотя бы одно задание учителя для этого класса
        exists = db.query(TaskModel).filter(
            TaskModel.grade == student.grade,
            TaskModel.teacher_id == current_user.id
        ).first()
        if not exists:
            raise HTTPException(status_code=403, detail="Ученик не в вашем классе")
    else:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    # === 2. Загрузка заданий ===
    # Все задания для класса ученика
    task_query = db.query(TaskModel).filter(TaskModel.grade == student.grade)
    if current_user.role == "teacher":
        # Учитель видит только свои задания
        task_query = task_query.filter(TaskModel.teacher_id == current_user.id)
    # Ученик видит задания от всех учителей своего класса — так и оставляем

    tasks = task_query.all()
    task_ids = [t.id for t in tasks]

    # === 3. Загрузка работ ученика ===
    submissions = db.query(StudentTask).filter(
        StudentTask.student_id == student_id,
        StudentTask.task_id.in_(task_ids)
    ).all()
    submission_map = {s.task_id: s for s in submissions}

    # === 4. Группировка по предметам ===
    subjects = {}
    for task in tasks:
        if task.subject not in subjects:
            subjects[task.subject] = []
        submission = submission_map.get(task.id)
        subjects[task.subject].append({
            "task_id": task.id,
            "title": task.title,
            "due_date": task.due_date,
            "status": submission.status if submission else "assigned",
            "grade": submission.grade if submission and submission.status == "accepted" else None,
            "has_submission": submission is not None,
            "submission_id": submission.id if submission else None
        })

    return {
        "student": {
            "id": student.id,
            "full_name": student.full_name,
            "grade": student.grade
        },
        "subjects": subjects
    }