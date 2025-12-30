# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости отдельно — для кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .

# Запуск
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]