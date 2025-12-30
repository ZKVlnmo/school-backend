from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: Optional[str] = None

class Task(TaskCreate):
    id: int
    teacher_id: int
    created_at: datetime

    class Config:
        from_attributes = True