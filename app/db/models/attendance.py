# app/db/models/attendance.py
from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import date


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)  # например, 2025-09-15
    quarter = Column(Integer, nullable=False)  # 1, 2, 3, 4
    grade = Column(String, nullable=False)  # "10-МАТ"

    # Статус посещения:
    # None — не отмечено
    # "present" — присутствовал
    # "absent_excused" — отсутствует (уважительная)
    # "absent_unexcused" — отсутствует (неуважительная)
    # "late" — опоздал
    status = Column(String, nullable=True)

    student = relationship("User", back_populates="attendance_records")