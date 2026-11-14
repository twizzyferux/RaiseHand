import sys
import os

# Добавляем пути к корню и к папке с ботом, чтобы импорты работали
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, 'discord_bot'))

print("=== ЗАПУСК ЧЕРЕЗ MAIN.PY ===")

# Импортируем функцию main из твоего bot.py
from discord_bot.bot import main

if __name__ == "__main__":
    main()