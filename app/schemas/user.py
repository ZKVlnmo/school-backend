from pydantic import BaseModel, validator
from typing import Optional

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: str  # "teacher" или "student"
    grade: Optional[str] = None  # ← теперь опционально

    @validator("grade", always=True)
    def grade_required_for_students(cls, v, values):
        role = values.get("role")
        if role == "student" and not v:
            raise ValueError("Поле 'grade' обязательно для учеников")
        if role == "teacher" and v:
            raise ValueError("Учителям не нужно указывать класс")
        return v

class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    id: int
    email: str
    full_name: str
    role: str

    class Config:
        from_attributes = True

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    grade: Optional[str] = None

    class Config:
        from_attributes = True  # для SQL