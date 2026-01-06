from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class TaskCreateRequest(BaseModel):
    title: str
    description: str
    subject: str
    reason: str
    due_date: Optional[datetime] = None
    student_ids: List[int]
    grade: str
    enable_ai_analysis: bool = False


class TaskUpdateRequest(BaseModel):
    title: str
    description: str
    subject: str
    reason: str
    due_date: Optional[datetime] = None
    student_ids: List[int]
    enable_ai_analysis: bool = False


class Task(BaseModel):
    id: int
    title: str
    description: str
    subject: str
    reason: str
    due_date: Optional[datetime] = None
    grade: str
    teacher_id: int
    enable_ai_analysis: bool

    class Config:
        from_attributes = True


class TaskWithSubmissionStatus(BaseModel):
    id: int
    title: str
    description: str
    subject: str
    reason: str
    due_date: Optional[datetime] = None
    grade: str
    teacher_name: str
    files: List[str] = []
    is_submitted: bool = False
    submitted_at: Optional[datetime] = None
    status: str = "assigned"
    teacher_comment: Optional[str] = None
    teacher_grade: Optional[int] = None
    comment: Optional[str] = None
    student_files: List[str] = []

    class Config:
        from_attributes = True