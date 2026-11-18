# RaiseHand — веб-деплой (Flet web)
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir flet httpx requests pygame discord.py

COPY . .

ENV RH_WEB=1
EXPOSE 8550

# Веб-режим Flet. Для APK/EXE локально: flet build apk / flet build windows
# Веб: flet run --web. Для APK/EXE локально: flet build apk / flet build windows
CMD ["python", "-c", "import flet as ft; from flet_app.main import main; ft.run(main, view=ft.AppView.WEB_BROWSER, port=8550)"]
