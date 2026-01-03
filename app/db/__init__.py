# app/db/__init__.py
# Этот файл гарантирует, что все модели импортированы при первом импорте app.db

from app.db.base import Base
from app.db.models.user import User
from app.db.models.task import Task
from app.db.models.student_task import StudentTask

# Экспортируем Base и модели наружу
__all__ = ["Base", "User", "Task", "StudentTask"]