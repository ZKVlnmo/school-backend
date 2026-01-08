# app/schemas/user.py

from pydantic import BaseModel
from typing import Optional

class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    is_verified: bool

    class Config:
        from_attributes = True