from sqlalchemy.orm import Session
from app.db.models.task import Task

def create_task(db: Session, task_data, teacher_id: int):
    db_task = Task(**task_data.dict(), teacher_id=teacher_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_tasks_by_teacher(db: Session, teacher_id: int):
    return db.query(Task).filter(Task.teacher_id == teacher_id).all()

def get_all_tasks(db: Session):
    return db.query(Task).all()