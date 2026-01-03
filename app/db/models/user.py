from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    grade = Column(String, nullable=True)

    # ← ОБЯЗАТЕЛЬНО добавьте эти две строки:
    created_tasks = relationship("Task", back_populates="teacher")
    assigned_tasks = relationship("StudentTask", back_populates="student")