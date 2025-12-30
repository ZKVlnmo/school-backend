from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: str  # "teacher" или "student"

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