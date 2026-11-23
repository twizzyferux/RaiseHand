# -*- coding: utf-8 -*-
"""Звуки чата: входящий notification и короткий исходящий клик.

Входящий: ``notification_sound.wav`` в корне проекта (приоритет),
иначе assets/sounds/ding.wav или сгенерированный тон.
"""

from __future__ import annotations

import math
import os
import struct
import threading
import wave

from core.config import BASE_DIR, DATA_DIR

# Пользовательский звук уведомления в корне репозитория
_ROOT_NOTIFY_WAV = os.path.join(BASE_DIR, "notification_sound.wav")
_CUSTOM_DING = os.path.join(BASE_DIR, "assets", "sounds", "ding.wav")
_CUSTOM_SEND = os.path.join(BASE_DIR, "assets", "sounds", "send.wav")
_GENERATED_DING = os.path.join(DATA_DIR, "ding.wav")
_GENERATED_SEND = os.path.join(DATA_DIR, "send.wav")
_INITED = False
_LOCK = threading.Lock()


def _write_tone(
    path: str,
    *,
    freq: float,
    duration: float,
    amp: float = 0.35,
    rate: int = 22050,
) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    n = int(rate * duration)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            t = i / rate
            envelope = amp * (1.0 - t / duration)
            sample = int(envelope * 32767 * math.sin(2 * math.pi * freq * t))
            frames += struct.pack("<h", sample)
        wf.writeframes(frames)
    return path


def _ensure_wav(custom: str, generated: str, *, freq: float, duration: float, amp: float) -> str:
    if os.path.isfile(custom) and os.path.getsize(custom) > 44:
        return custom
    if os.path.isfile(generated) and os.path.getsize(generated) > 44:
        return generated
    return _write_tone(generated, freq=freq, duration=duration, amp=amp)


def ding_path() -> str:
    """Звук входящего уведомления."""
    if os.path.isfile(_ROOT_NOTIFY_WAV) and os.path.getsize(_ROOT_NOTIFY_WAV) > 0:
        return _ROOT_NOTIFY_WAV
    return _ensure_wav(
        _CUSTOM_DING,
        _GENERATED_DING,
        freq=880.0,
        duration=0.18,
        amp=0.35,
    )


def send_path() -> str:
    return _ensure_wav(
        _CUSTOM_SEND,
        _GENERATED_SEND,
        freq=1240.0,
        duration=0.09,
        amp=0.22,
    )


def _play_file(path: str, *, volume: float, wait: float = 0.25) -> None:
    def _run():
        global _INITED
        try:
            import time

            import pygame

            vol = max(0.0, min(1.0, float(volume)))
            with _LOCK:
                if not _INITED:
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
                    _INITED = True
                sound = pygame.mixer.Sound(path)
                try:
                    sound.set_volume(vol)
                except Exception:
                    pass
                channel = sound.play()
                # дождаться конца или таймаута
                deadline = time.time() + max(wait, 0.2)
                if channel is not None:
                    while channel.get_busy() and time.time() < deadline:
                        time.sleep(0.03)
                else:
                    time.sleep(wait)
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


def play_ding(*, force: bool = False) -> None:
    """Входящее сообщение. force=True — для кнопки «Прослушать»."""
    try:
        from core import prefs

        if not force:
            if not prefs.sounds_enabled() or not prefs.sound_incoming():
                return
            if prefs.notif_sound_name() == "none":
                return
        volume = prefs.sound_volume()
        if prefs.notif_sound_name() == "soft":
            volume *= 0.45
    except Exception:
        volume = 0.7
    path = ding_path()
    # notification_sound.wav может быть длиннее короткого тона
    wait = 3.0 if os.path.basename(path).lower() == "notification_sound.wav" else 0.25
    _play_file(path, volume=volume, wait=wait)


def play_send(*, force: bool = False) -> None:
    """Короткий звук исходящего (если включён в настройках)."""
    try:
        from core import prefs

        if not force:
            if not prefs.sounds_enabled() or not prefs.sound_outgoing():
                return
        volume = prefs.sound_volume() * 0.85
    except Exception:
        volume = 0.55
    _play_file(send_path(), volume=volume, wait=0.14)
