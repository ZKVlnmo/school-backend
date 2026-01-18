from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, date
import httpx
import re
from typing import List, Optional
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.db.models.user import User
from app.core.config import settings

router = APIRouter()

TEACHER_LNO_CREDENTIALS = {
    1: {
        "username": settings.LNO_ZDEKH_USERNAME,
        "password": settings.LNO_ZDEKH_PASSWORD,
    },
    2: {
        "username": settings.LNO_VASILIEVA_USERNAME,
        "password": settings.LNO_VASILIEVA_PASSWORD,
    }
}


class CourseGradeInfo(BaseModel):
    course_title: str
    class_name: Optional[str]
    last_grade_date: Optional[str]  # YYYY-MM-DD
    days_since_last_grade: Optional[int]


def _should_include_course(course: dict, teacher_id: Optional[int]) -> bool:
    if teacher_id != 2:
        return True
    class_name = course.get("for_class")
    if not isinstance(class_name, str):
        return False
    class_name = class_name.strip()
    if not class_name:
        return False
    match = re.match(r'^[\s\-–]*([56])', class_name)
    return bool(match)


@router.get("/courses-with-last-grade", response_model=List[CourseGradeInfo])
async def get_courses_with_last_grade(
    teacher_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Только для администраторов")

    LNO_API_BASE_URL = settings.LNO_API_BASE_URL
    if not LNO_API_BASE_URL:
        raise HTTPException(500, "Не задан LNO_API_BASE_URL в .env")

    if teacher_id is not None:
        if teacher_id not in TEACHER_LNO_CREDENTIALS:
            raise HTTPException(400, f"Нет LNO-учётной записи для teacher_id={teacher_id}")
        creds = TEACHER_LNO_CREDENTIALS[teacher_id]
        LNO_USERNAME = creds["username"]
        LNO_PASSWORD = creds["password"]
    else:
        LNO_USERNAME = settings.LNO_USERNAME
        LNO_PASSWORD = settings.LNO_PASSWORD

    if not all([LNO_USERNAME, LNO_PASSWORD]):
        raise HTTPException(500, "Не заданы LNO_USERNAME и LNO_PASSWORD")

    timeout = httpx.Timeout(10.0, read=15.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        # 1. Авторизация
        try:
            auth_resp = await client.post(
                f"{LNO_API_BASE_URL}/api/user/login/",
                json={"username": LNO_USERNAME, "password": LNO_PASSWORD}
            )
            auth_resp.raise_for_status()
            lno_token = auth_resp.json().get("key")
            if not lno_token:
                raise HTTPException(500, "LNO API не вернул токен")
        except Exception as e:
            raise HTTPException(500, f"Ошибка авторизации в LNO: {str(e)}")

        headers = {"Authorization": f"Token {lno_token}"}

        # 2. Получаем все курсы
        courses = []
        next_url = f"{LNO_API_BASE_URL}/api/course/"
        while next_url:
            try:
                resp = await client.get(next_url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                courses.extend(data.get("results", []))
                next_url = data.get("next")
            except Exception:
                break

        # 3. Фильтруем курсы (для Васильевой — только 5-6 классы)
        filtered_courses = [
            course for course in courses
            if _should_include_course(course, teacher_id)
        ]

        result = []
        today = date.today()

        for course in filtered_courses:
            course_id = course["id"]
            title = course["title"]
            class_name = course.get("for_class")

            # 🔍 Отладочный вывод — НЕ фильтруем по 6-м классам!

            # Загружаем ВСЕ оценки с пагинацией
            marks = []
            next_url_marks = f"{LNO_API_BASE_URL}/api/mark/?activity__course={course_id}&page_size=1000"
            page_count = 0
            while next_url_marks:
                try:
                    marks_resp = await client.get(next_url_marks, headers=headers)
                    marks_resp.raise_for_status()
                    data = marks_resp.json()
                    page_marks = data.get("results", [])
                    marks.extend(page_marks)
                    next_url_marks = data.get("next")
                    page_count += 1
                except Exception as e:
                    print(f"  ⚠️ Ошибка загрузки оценок: {e}")
                    break


            valid_marks = [
                m for m in marks
                if m.get("value") and m["value"] != "Н" and m.get("activity")
            ]

            if not valid_marks:
                print("  ➤ Нет валидных оценок → last_grade_date = null")
                result.append(CourseGradeInfo(
                    course_title=title,
                    class_name=class_name,
                    last_grade_date=None,
                    days_since_last_grade=None
                ))
                continue

            # Получаем даты активностей
            activity_ids = {m["activity"] for m in valid_marks}
            activity_date_map = {}
            future_count = 0

            for aid in activity_ids:
                try:
                    act_resp = await client.get(
                        f"{LNO_API_BASE_URL}/api/activity/{aid}/",
                        headers=headers
                    )
                    if act_resp.status_code == 200:
                        act_data = act_resp.json()
                        act_date_str = act_data.get("date")
                        if act_date_str:
                            try:
                                act_date = datetime.strptime(act_date_str, "%Y-%m-%d").date()
                                if act_date > today:
                                    future_count += 1
                                else:
                                    activity_date_map[aid] = act_date_str
                            except ValueError:
                                pass
                except Exception:
                    continue

            if future_count:
                print(f"  ➤ Игнорировано оценок из будущего: {future_count}")

            # Находим последнюю дату
            latest_activity_date = None
            for mark in valid_marks:
                aid = mark["activity"]
                date_str = activity_date_map.get(aid)
                if not date_str:
                    continue
                try:
                    act_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    if latest_activity_date is None or act_date > latest_activity_date:
                        latest_activity_date = act_date
                except Exception:
                    continue

            if latest_activity_date:
                days = (today - latest_activity_date).days
                print(f"  ✅ Последняя оценка: {latest_activity_date.strftime('%d.%m.%Y')} ({days} дней назад)")
                result.append(CourseGradeInfo(
                    course_title=title,
                    class_name=class_name,
                    last_grade_date=latest_activity_date.isoformat(),
                    days_since_last_grade=days
                ))
            else:
                print("  ❌ Не удалось определить дату последней оценки")
                result.append(CourseGradeInfo(
                    course_title=title,
                    class_name=class_name,
                    last_grade_date=None,
                    days_since_last_grade=None
                ))

        return result