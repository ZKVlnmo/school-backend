# app/schemas/task.py
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class Task(BaseModel):
    id: int
    title: str
    description: str
    subject: str
    reason: str
    due_date: Optional[datetime] = None
    grade: str
    teacher_id: int

    class Config:
        from_attributes = True


class TaskWithSubmissionStatus(BaseModel):
    id: int
    title: str
    description: str
    subject: str
    reason: str
    due_date: Optional[datetime] = None
    grade: str  # ← класс задания (7А, 9Б)
    teacher_name: str
    files: List[str] = []
    is_submitted: bool = False
    submitted_at: Optional[datetime] = None
    status: str = "assigned"
    teacher_comment: Optional[str] = None
    teacher_grade: Optional[int] = None  # оценка от учителя
    comment: Optional[str] = None        # ← ваш комментарий
    student_files: List[str] = []        # ← ваши файлы
    class Config:
        from_attributes = True