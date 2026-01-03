# app/db/models/student_task.py
from sqlalchemy import Column, Integer, ForeignKey, Boolean, DateTime, Text, String
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class StudentTask(Base):
    __tablename__ = "student_task"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Новые поля для отслеживания выполнения
    is_submitted = Column(Boolean, default=False, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    comment = Column(Text, nullable=True)

    # Связи (опционально, но полезно)
    task = relationship("Task", back_populates="student_tasks")
    student = relationship("User", back_populates="assigned_tasks")
    status = Column(String, default="assigned")  # assigned → submitted → accepted/rejected
    teacher_comment = Column(Text, nullable=True)  # комментарий учителя при возврате
    grade = Column(Integer, nullable=True)