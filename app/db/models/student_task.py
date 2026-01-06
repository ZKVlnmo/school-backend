# app/db/models/student_task.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base

class StudentTask(Base):
    __tablename__ = "student_task"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    student_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="assigned")
    comment = Column(Text, nullable=True)
    grade = Column(Integer, nullable=True)
    teacher_comment = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    ai_analysis = Column(Text, nullable=True)

    # Связи
    task = relationship("Task", back_populates="student_tasks")
    student = relationship("User", back_populates="student_tasks")  # ← ссылается на User.student_tasks