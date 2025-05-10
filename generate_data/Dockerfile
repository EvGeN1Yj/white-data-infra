# Используем официальный образ Python
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости и скрипт
COPY requirements.txt .
COPY data_generator.py .
COPY init_db.sql .
COPY main.py .
COPY create.sql .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Создаем папку для логов
RUN mkdir -p /app/logs

# Запускаем генератор при старте контейнера
CMD sleep 40 && python main.py