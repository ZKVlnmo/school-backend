from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from app.api.deps import get_db
from app.schemas.user import (
    UserCreate,
    UserLogin,
    Token,
    StudentGenerationRequest,
    StudentGenerationResponse
)
from app.crud import user as crud_user
from app.core.security import verify_password, create_access_token, decode_access_token

router = APIRouter()

# Настройка OAuth2 схемы
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user_from_token(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = crud_user.get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=Token)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if crud_user.get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    if user_in.role not in ["teacher", "student"]:
        raise HTTPException(status_code=400, detail="Роль должна быть 'teacher' или 'student'")

    user = crud_user.create_user(db, user_in)
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login")
def login(form: UserLogin, db: Session = Depends(get_db)):
    user = crud_user.get_user_by_email(db, form.email)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    access_token = create_access_token(data={"sub": user.email, "role": user.role})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "grade": user.grade,
            "is_verified": user.is_verified
        }
    }


@router.post("/generate-students", response_model=StudentGenerationResponse)
def generate_students_for_grade(
    request: StudentGenerationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_from_token)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Только учитель может создавать учеников")

    # Генерируем 30 учеников
    students_data = crud_user.generate_student_credentials(request.grade, count=30)
    created = crud_user.create_students_bulk(db, students_data)

    return {"students": created}