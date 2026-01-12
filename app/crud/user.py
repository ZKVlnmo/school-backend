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

def generate_student_credentials(grade: str, count: int = 30) -> list:
    """Генерирует список учеников с ФИО, email и паролем"""
    students = []
    for i in range(1, count + 1):
        # Генерация ФИО: Ученик Иванов N
        last_name = f"Ученик{i}"
        first_name = "Иван"
        middle_name = "Иванович"
        full_name = f"{last_name} {first_name} {middle_name}"

        # Email: student{N}@school.local
        email = f"student{i}.{grade.replace(' ', '').lower()}@school.local"

        # Пароль: 8 случайных символов
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(8))

        students.append({
            "full_name": full_name,
            "email": email,
            "password": password,
            "grade": grade
        })
    return students

def create_students_bulk(db: Session, students_data: list):
    created = []
    for data in students_data:
        # Проверяем, не существует ли уже
        existing = db.query(User).filter(User.email == data["email"]).first()
        if existing:
            continue  # пропускаем дубликаты

        user = User(
            email=data["email"],
            hashed_password=get_password_hash(data["password"]),
            full_name=data["full_name"],
            role="student",
            grade=data["grade"],
            is_verified=True  # Ученики сразу активны!
        )
        db.add(user)
        created.append({
            "full_name": data["full_name"],
            "email": data["email"],
            "password": data["password"]
        })
    db.commit()
    return created