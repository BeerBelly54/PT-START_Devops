# bot_image Dockerfile
FROM python:3.10
RUN pip install --upgrade pip

# Установка зависимостей
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip list 

# Копирование кода
WORKDIR /TG_Bot
COPY . .

# Запуск бота
CMD ["python", "TG_Bot.py"]