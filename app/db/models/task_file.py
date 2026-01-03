from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class TaskFile(Base):
    __tablename__ = "task_files"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    original_name = Column(String, nullable=False)
    filename = Column(String, nullable=False)  # безопасное имя
    path = Column(String, nullable=False)  # путь на диске

    task = relationship("Task", back_populates="files")