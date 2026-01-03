from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, tasks, students
from app.db.base import Base
from app.db.session import engine



app = FastAPI(title="School Todo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://178.72.149.182"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(students.router, prefix="/api/students", tags=["students"])
