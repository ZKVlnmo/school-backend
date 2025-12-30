from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.user import UserCreate, UserLogin, Token
from app.crud import user as crud_user
from app.core.security import verify_password, create_access_token

router = APIRouter()


@router.post("/register", response_model=Token)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if crud_user.get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    if user_in.role not in ["teacher", "student"]:
        raise HTTPException(status_code=400, detail="Роль должна быть 'teacher' или 'student'")

    user = crud_user.create_user(db, user_in)
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
def login(form: UserLogin, db: Session = Depends(get_db)):
    user = crud_user.get_user_by_email(db, form.email)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}