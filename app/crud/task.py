# app/crud/task.py
from sqlalchemy.orm import Session
from app.db.models.task import Task as TaskModel
from app.db.models.student_task import StudentTask


def create_task(db: Session, task_data: dict) -> TaskModel:
    db_task = TaskModel(
        title=task_data["title"],
        description=task_data["description"],
        subject=task_data["subject"],
        reason=task_data["reason"],
        due_date=task_data.get("due_date"),
        grade=task_data["grade"],
        teacher_id=task_data["teacher_id"],
        enable_ai_analysis=task_data.get("enable_ai_analysis", False)
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    for student_id in task_data.get("student_ids", []):
        db_student_task = StudentTask(task_id=db_task.id, student_id=student_id)
        db.add(db_student_task)

    db.commit()
    return db_task


def update_task(db: Session, task_id: int, task_data: dict) -> TaskModel:
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        return None

    # 1. Обновляем скалярные поля задачи (title, description и т.д.)
    for key, value in task_data.items():
        if key != "student_ids":
            setattr(task, key, value)

    # 2. Обновляем список учеников ТОЛЬКО если он передан
    if "student_ids" in task_data:
        new_student_ids = set(task_data["student_ids"])
        existing_records = {st.student_id: st for st in task.student_tasks}

        # Добавляем новых учеников (которых ещё нет)
        for sid in new_student_ids - existing_records.keys():
            db.add(StudentTask(task_id=task_id, student_id=sid, status="assigned"))

        # Удаляем учеников, которых убрали из списка — НО ТОЛЬКО ЕСЛИ СТАТУС = 'assigned'
        for sid, record in existing_records.items():
            if sid not in new_student_ids:
                if record.status == "assigned":
                    db.delete(record)
                else:
                    # Ученик уже что-то прислал — нельзя удалить!
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Нельзя удалить ученика {sid}: есть присланная или проверенная работа"
                    )

    db.commit()
    db.refresh(task)
    return task