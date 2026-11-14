FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# ВОТ ЗДЕСЬ МЕНЯЕМ ПУТЬ (убираем discord_bot/):
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip uninstall -y discord discord.py py-cord || true
RUN pip install --no-cache-dir --force-reinstall discord.py==2.3.2

COPY core /app/core
COPY discord_bot /app
COPY config /app/config

EXPOSE 8080

CMD ["python", "bot.py"]