# -*- coding: utf-8 -*-
import asyncio, os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import flet as ft

variants = ft.Column(spacing=20, controls=[
    ft.TextField(label="A no-border", filled=True, fill_color="#EFEFF4",
                 border=ft.NoInputBorder(), border_radius=26, height=52),
    ft.TextField(label="B outline0", filled=True, fill_color="#EFEFF4",
                 border=ft.OutlineInputBorder(border_radius=26, side=ft.BorderSide(0, "transparent")),
                 height=52),
    ft.TextField(label="C underline0", filled=True, fill_color="#EFEFF4",
                 border=ft.UnderlineInputBorder(border_radius=26, border_side=ft.BorderSide(0, "transparent")),
                 height=52),
    ft.TextField(label="D old", filled=True, bgcolor="#EFEFF4",
                 border_radius=26, border_color="transparent", height=52),
])


async def shoot(page: ft.Page):
    await asyncio.sleep(1.5)
    data = await page.take_screenshot(pixel_ratio=2)
    with open("_flet_shots/fieldtest.png", "wb") as f:
        f.write(data)
    try:
        await page.window.close()
    except Exception:
        pass


def main(page: ft.Page):
    page.bgcolor = "#FFFBF7"
    page.padding = 24
    page.enable_screenshots = True
    page.window.width = 420
    page.window.height = 420
    page.add(variants)
    page.run_task(shoot)


ft.run(main)
