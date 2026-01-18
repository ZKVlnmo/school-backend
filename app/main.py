from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Импортируем из app.api, а не из app.routers!
from app.api import auth, tasks, students, ai, admin, attendance, admin_stats

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "http://178.72.149.182",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем admin_stats с префиксом /api/admin
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(students.router, prefix="/api/students", tags=["students"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["attendance"])

# 👇 Вот так правильно:
app.include_router(admin_stats.router, prefix="/api/admin", tags=["admin"])