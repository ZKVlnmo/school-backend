from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_teacher
from app.schemas.task import TaskCreate, Task
from app.crud import task as crud_task

router = APIRouter()

# Только учитель может создавать
@router.post("/", response_model=Task)
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_teacher)
):
    return crud_task.create_task(db, task_in, teacher_id=current_user.id)

# Ученик — видит все задачи, учитель — только свои
@router.get("/", response_model=list[Task])
def read_tasks(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role == "teacher":
        return crud_task.get_tasks_by_teacher(db, current_user.id)
    else:
        return crud_task.get_all_tasks(db)