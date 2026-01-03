from app.models.task import Task as TaskModel
from app.models.student_task import StudentTask

def create_task(db: Session, task_ dict):
    # Создаём задачу
    db_task = TaskModel(
        title=task_data["title"],
        description=task_data["description"],
        subject=task_data["subject"],
        reason=task_data["reason"],
        due_date=task_data.get("due_date"),
        grade=task_data["grade"],
        teacher_id=task_data["teacher_id"]
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    # Привязываем учеников
    for student_id in task_data.get("student_ids", []):
        db_student_task = StudentTask(task_id=db_task.id, student_id=student_id)
        db.add(db_student_task)

    db.commit()
    db.refresh(db_task)
    return db_task