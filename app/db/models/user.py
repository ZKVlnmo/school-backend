from sqlalchemy import Column, Integer, String, Enum
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum("teacher", "student", name="user_role"), nullable=False)  # только эти роли
    full_name = Column(String, nullable=False)