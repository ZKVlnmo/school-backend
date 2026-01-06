# app/db/models/user.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "student", "teacher"
    grade = Column(String, nullable=True)  # только для учеников

    # Связи
    created_tasks = relationship("Task", back_populates="teacher")
    student_tasks = relationship("StudentTask", back_populates="student")  # ← ОБЯЗАТЕЛЬНО!