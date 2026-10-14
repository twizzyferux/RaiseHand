"""Проба путей для файлов: работают ли они на iOS.

Зачем
-----
Папка с данными на ПК лежит рядом с кодом, но на iOS папка приложения
только для чтения, и запись в неё падает. core/config.py переносит
данные в записываемое место, но «на глаз» это не проверить: нужно
убедиться, что при платформе ios папка уезжает из поставки, настройки
всё равно читаются, а на ПК ничего не изменилось.

Как читать
----------
Строка ИТОГ в _shots/ios_paths.log.
"""

import os
import json
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "_shots", "ios_paths.log")
PY = os.path.join(BASE, ".venv312", "Scripts", "python.exe")

# Код, который выполняется в отдельном процессе с подменённой
# платформой: иначе core.config уже успел бы импортироваться с
# настоящей платформой.
CHILD = r'''
import sys, os, json
import kivy.utils
kivy.utils.platform = sys.argv[1]
sys.path.insert(0, %r)
os.chdir(%r)
import core.config as c

out = {
    "platform": kivy.utils.platform,
    "BASE_DIR": c.BASE_DIR,
    "CONFIG_DIR": c.CONFIG_DIR,
    "DATA_DIR": c.DATA_DIR,
    "in_bundle": c.DATA_DIR.startswith(c.BASE_DIR + os.sep),
    "writable": False,
    "settings_ok": False,
    "font_ok": False,
    "read_from": c._config_path("settings.json"),
}
try:
    probe = os.path.join(c.DATA_DIR, ".probe")
    with open(probe, "w") as f:
        f.write("1")
    os.remove(probe)
    out["writable"] = True
except OSError:
    pass
out["settings_ok"] = bool(c.SETTINGS.get("texts"))
font = c.SETTINGS.get("font", {}).get("file", "")
# Так же, как в main.py: имя файла само по себе, полный путь собирается
# от папки поставки через assets/fonts.
font_path = os.path.join(c.BASE_DIR, "assets", "fonts", font) if font else ""
out["font_ok"] = bool(font_path) and os.path.exists(font_path)
print(json.dumps(out))
''' % (BASE, BASE)


# Тот же импорт, но с заведомо испорченной файловой системой: любая
# попытка создать папку падает. Именно этот случай убивал приложение на
# телефоне — все кандидаты для данных недоступны, и модуль ронял весь
# запуск исключением при импорте.
CHILD_NO_WRITE = r'''
import sys, os, json, errno
import kivy.utils
kivy.utils.platform = "ios"
sys.path.insert(0, __BASE__)
os.chdir(__BASE__)

_real_makedirs = os.makedirs
_real_open = open

def deny_makedirs(path, *a, **kw):
    raise OSError(errno.EROFS, "Read-only file system")

def deny_open(path, mode="r", *a, **kw):
    if "w" in mode or "a" in mode or "+" in mode:
        raise OSError(errno.EROFS, "Read-only file system")
    return _real_open(path, mode, *a, **kw)

os.makedirs = deny_makedirs
import builtins
builtins.open = deny_open

out = {"raised": None}
try:
    import core.config as c
    out["data_dir"] = c.DATA_DIR
    out["config_dir"] = c.CONFIG_DIR
except BaseException as e:
    out["raised"] = "%s: %s" % (type(e).__name__, e)
os.makedirs = _real_makedirs
builtins.open = _real_open
print(json.dumps(out))
'''.replace("__BASE__", repr(BASE))


def run(platform):
    code = CHILD
    proc = subprocess.run(
        [PY, "-X", "utf8", "-c", code, platform],
        capture_output=True, text=True, encoding="utf-8", cwd=BASE,
    )
    if proc.returncode != 0:
        raise RuntimeError("дочерний процесс упал: %s" % proc.stderr[-1500:])
    line = [x for x in proc.stdout.splitlines() if x.startswith("{")][-1]
    return json.loads(line)


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    lines = []
    problems = []

    pc = run("win")
    ios = run("ios")

    lines.append("=== ПК ===")
    for key in ("CONFIG_DIR", "DATA_DIR", "in_bundle", "writable",
                "settings_ok", "font_ok"):
        lines.append("%-12s %s" % (key, pc[key]))
    lines.append("")
    lines.append("=== iOS ===")
    for key in ("CONFIG_DIR", "DATA_DIR", "in_bundle", "writable",
                "settings_ok", "font_ok"):
        lines.append("%-12s %s" % (key, ios[key]))
    lines.append("")

    # На ПК поведение не должно измениться: папки остались рядом с кодом.
    if pc["DATA_DIR"] != os.path.join(pc["BASE_DIR"], "data"):
        problems.append("на ПК папка данных уехала из папки кода")
    if pc["CONFIG_DIR"] != os.path.join(pc["BASE_DIR"], "config"):
        problems.append("на ПК папка настроек уехала из папки кода")

    # На iOS папка данных обязана быть вне поставки и записываемой.
    if ios["in_bundle"]:
        problems.append("на iOS данные остались в папке приложения")
    if not ios["writable"]:
        problems.append("на iOS папка данных недоступна для записи")

    # Главный случай, который ронял приложение: записи нет никуда.
    nowrap = json.loads([
        x for x in subprocess.run(
            [PY, "-X", "utf8", "-c", CHILD_NO_WRITE],
            capture_output=True, text=True, encoding="utf-8", cwd=BASE,
        ).stdout.splitlines() if x.startswith("{")][-1])
    if nowrap.get("raised"):
        problems.append("при полностью недоступной записи импорт падает: %s"
                        % nowrap["raised"])
    lines.append("запись закрыта полностью: исключение = %s"
                 % (nowrap.get("raised") or "нет"))

    # Настройки и шрифт читаются на обеих платформах.
    for tag, res in (("ПК", pc), ("iOS", ios)):
        if not res["settings_ok"]:
            problems.append("%s: настройки не прочитались" % tag)
        if not res["font_ok"]:
            problems.append("%s: шрифт не найден по пути поставки" % tag)

    lines.append("ПК: папка в поставке = %s, записывается = %s"
                 % (pc["in_bundle"], pc["writable"]))
    lines.append("iOS: папка в поставке = %s, записывается = %s"
                 % (ios["in_bundle"], ios["writable"]))
    lines.append("")
    lines.append("ИТОГ: %s" % ("всё в порядке" if not problems else "проблемы"))
    for p in problems:
        lines.append("  - %s" % p)

    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()