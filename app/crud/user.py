from sqlalchemy.orm import Session
from app.db.models.user import User
from app.core.security import get_password_hash

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_data):

    db_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        grade=user_data.grade
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
def get_students_by_grade(db: Session, grade: str):
    return db.query(User).filter(
        User.role == "student",
        User.grade == grade
    ).all()