# -*- coding: utf-8 -*-
"""Бот обрабатывает кнопки Одобрить / Отклонить."""
from __future__ import annotations

import json
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import discord
from discord.ext import commands

from core.config import DATA_DIR, SETTINGS


def set_status(app_id: str, status: str) -> bool:
    path = os.path.join(DATA_DIR, "teacher_apps", f"{app_id}.json")
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data["status"] = status
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True


# 1. Включаем нужные интенты и создаем Бота (а не просто Client)
intents = discord.Intents.default()
intents.message_content = True  # Обязательно для чтения команд!
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Бот онлайн: {bot.user} — кнопки активны")


@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    cid = (interaction.data or {}).get("custom_id") or ""
    if ":" not in cid:
        return
    action, app_id = cid.split(":", 1)
    if action == "approve":
        ok = set_status(app_id, "approved")
        text = f"**#{app_id} — одобрено**" if ok else f"Заявка #{app_id} не найдена"
    elif action == "reject":
        ok = set_status(app_id, "rejected")
        text = f"**#{app_id} — отклонено**" if ok else f"Заявка #{app_id} не найдена"
    else:
        return
    try:
        await interaction.response.edit_message(content=text, view=None, attachments=[])
    except Exception:
        await interaction.response.send_message(text, ephemeral=True)


# 2. Команда должна быть объявлена ДО запуска бота
@bot.command(name="send_rules")
@commands.has_permissions(administrator=True)  # Только админы могут вызвать команду
async def send_rules(ctx):
    # Удаляем команду, чтобы никто не видел, что ты ее вводил
    await ctx.message.delete()

    embed = discord.Embed(
        title="📜 Правила сервера RaiseHand",
        description=(
            "**Добро пожаловать на официальный сервер приложения RaiseHand!** 👋\n"
            "Именно здесь каждый может пообщаться и узнать множество новой информации о нашем приложении. "
            "Чтобы всем было комфортно, пожалуйста, соблюдайте несколько простых правил.\n\n"

            "**1. 🤝 Уважение и вежливость**\n"
            "Общайтесь друг с другом уважительно. Запрещены оскорбления, травля и конфликты на любой почве.\n\n"

            "**2. 🚫 Без спама и рекламы**\n"
            "Не флудите в чатах и не присылайте ссылки на сторонние сервера без разрешения администрации.\n\n"

            "**3. 🔞 Запрещенный контент**\n"
            "Строго запрещен контент 18+ (NSFW) и любые материалы, нарушающие правила Discord. За отправку пользователь будет заблокирован на определенный промежуток.\n\n"

            "**4. 🛠️ Техническая поддержка**\n"
            "Возникли проблемы или нашли баг? Пишите в специальные каналы (`#помощь` или `#баг-репорты`). Не нужно тегать админов в личке.\n\n"

            "**5. 📝 Анкеты и регистрация**\n"
            "Если вы подали анкету (например, на роль учителя), пожалуйста, ожидайте. Проверка занимает время, не нужно спамить.\n\n"

            "**6. 🔒 Конфиденциальность**\n"
            "Уважайте чужую приватность. Запрещено публиковать личные данные других участников без их согласия. За отправку пользователь будет заблокирован.\n\n"

            "**7. 🚫 Продажа и перекуп**\n"
            "Продажа и перепродажа аккаунтов полностью запрещена. Если будет замечена продажа или перепродажа аккаунтов, то как на сервере Discord, так и в приложении RaiseHand оба пользователя будут заблокированы перманентно.\n\n"

            "**8. ⚖️ Слушайте администрацию**\n"
            "У модераторов есть последнее слово. Если вы не согласны — решайте это в ЛС с владельцем сервера.\n\n"

            "> **Нажимая на реакцию ✅ ниже, вы соглашаетесь с правилами сервера и обязуетесь их соблюдать.**"
        ),
        color=0x907FEC  # Твой сиреневый цвет
    )

    # Добавляем иконку сервера в качестве миниатюры (если есть)
    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)

    embed.set_footer(text="RaiseHand • Безопасность и комфорт")

    # Отправляем сообщение
    msg = await ctx.send(embed=embed)

    # Добавляем реакцию-галочку для Carl-bot
    await msg.add_reaction("✅")


# 3. Запуск бота (теперь он происходит ПОСЛЕ того, как команда зарегистрирована)
def main():
    token = (SETTINGS.get("discord") or {}).get("bot_token") or ""
    if not token:
        raise SystemExit("Укажите discord.bot_token")
    bot.run(token)


import asyncio
from aiohttp import web  # <--- ДОБАВЬ ЭТОТ ИМПОРТ


# ... (твой существующий код: set_status, intents, bot = commands.Bot(...) и т.д.) ...

# --- НОВЫЙ БЛОК: Веб-сервер для Netrun ---
async def handle(request):
    return web.Response(text="Bot is alive!")


async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("Веб-сервер запущен на порту 8080")


# --- Меняем функцию main() ---
def main():
    # Сначала ищем токен в переменных окружения хостинга
    token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")

    # Если там пусто, ищем в settings.json
    if not token:
        token = (SETTINGS.get("discord") or {}).get("bot_token") or ""

    if not token:
        raise SystemExit("Ошибка: Токен не найден ни в переменных, ни в settings.json")

    print("=== ЗАПУСК БОТА С ТОКЕНОМ ===")
    bot.run(token)
