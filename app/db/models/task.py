from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    subject = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    due_date = Column(DateTime, nullable=True)
    grade = Column(String, nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    enable_ai_analysis = Column(Boolean, default=False, nullable=False)

    # Связи
    teacher = relationship("User", back_populates="created_tasks")
    student_tasks = relationship("StudentTask", back_populates="task", cascade="all, delete-orphan")