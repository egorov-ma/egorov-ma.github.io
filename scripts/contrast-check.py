#!/usr/bin/env python3
"""Контраст палитры сайта по двум стандартам: WCAG 2.x (отношение яркостей) и APCA (Lc, APCA-W3 0.0.98G-4g).

Цвета читаются из :root в src/styles/global.css, полупрозрачные смешиваются с фоном.
Пороги APCA — по роли текста (bronze-уровень): основной текст Lc 75 (желательно 90),
вторичный мелкий текст Lc 60, крупный жирный текст Lc 45, подписи-ориентиры Lc 30, нетекстовые элементы Lc 15.
Lc 60 для мелкого вторичного текста (даты, номера разделов, метки 12–15 px) мягче таблицы шрифтов APCA (там Lc 75):
осознанное послабление для текста, который пробегают глазами, — иначе вторичный цвет сливается с основным
и пропадает иерархия; решение 2026-10-30.
Фон закреплён (background-attachment: fixed), поэтому синее свечение проходит под любым контентом —
каждый текст проверяется и на чистом фоне, и под свечением.
Выход: таблица; rc 1, если хоть одна пара ниже порога любого из стандартов.
"""
import re
import sys
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "src" / "styles" / "global.css"


def tokens():
    root = re.search(r":root\s*\{(.*?)\n\}", CSS.read_text(encoding="utf-8"), re.S).group(1)
    out = {}
    for name, val in re.findall(r"--([\w-]+):\s*([^;]+);", root):
        val = val.strip()
        if m := re.fullmatch(r"#([0-9a-fA-F]{6})", val):
            h = m.group(1)
            out[name] = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
        elif m := re.fullmatch(r"rgb\((\d+)\s+(\d+)\s+(\d+)\s*/\s*([\d.]+)\)", val):
            out[name] = (int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4)))
    return out


def over(fg, bg):
    """Полупрозрачный цвет поверх непрозрачного фона."""
    a = fg[3]
    return tuple(round(fg[i] * a + bg[i] * (1 - a)) for i in range(3)) + (1.0,)


def rel_lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def wcag(txt, bg):
    a, b = sorted((rel_lum(txt), rel_lum(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def apca(txt, bg):
    def y(c):
        v = 0.2126729 * (c[0] / 255) ** 2.4 + 0.7151522 * (c[1] / 255) ** 2.4 + 0.0721750 * (c[2] / 255) ** 2.4
        return v + (0.022 - v) ** 1.414 if v < 0.022 else v
    yt, yb = y(txt), y(bg)
    if abs(yb - yt) < 0.0005:
        return 0.0
    if yb > yt:  # тёмный текст на светлом
        s = (yb ** 0.56 - yt ** 0.57) * 1.14
        return 0.0 if s < 0.1 else (s - 0.027) * 100
    s = (yb ** 0.65 - yt ** 0.62) * 1.14  # светлый текст на тёмном — своя формула
    return 0.0 if s > -0.1 else (s + 0.027) * 100


def main():
    t = tokens()
    bg = t["bg"]
    glow = over(t["glow"], bg)                       # худшая точка под синим свечением
    soft = over(t["accent-soft"], bg)                # выделенные карточки, плашка контакта
    soft_glow = over(t["accent-soft"], glow)         # они же под свечением
    tag = over(t["tag"], bg)                         # метки стека
    tag_glow = over(t["tag"], glow)
    btn, btn_hover = t.get("btn"), t.get("btn-hover")  # основная кнопка, монограмма, иконки подвала
    # (текст, фон, роль, WCAG-порог, APCA-порог)
    pairs = [
        ("ink", "bg", bg, "заголовки, крупный жирный", 3.0, 45),
        ("ink", "свечение", glow, "заголовки, крупный жирный", 3.0, 45),
        ("ink-2", "bg", bg, "основной текст 17px", 4.5, 75),
        ("ink-2", "свечение", glow, "основной текст 17px", 4.5, 75),
        ("ink-2", "accent-soft", soft, "текст в выделенной карточке", 4.5, 75),
        ("ink-2", "soft+свечение", soft_glow, "текст в выделенной карточке", 4.5, 75),
        ("ink-2", "tag", tag, "метки стека 14px", 4.5, 75),
        ("ink-2", "tag+свечение", tag_glow, "метки стека 14px", 4.5, 75),
        ("muted", "bg", bg, "вторичный мелкий (даты, подписи)", 4.5, 60),
        ("muted", "свечение", glow, "вторичный мелкий (даты, подписи)", 4.5, 60),
        ("muted", "accent-soft", soft, "вторичный мелкий на подложке", 4.5, 60),
        ("muted", "soft+свечение", soft_glow, "вторичный мелкий на подложке", 4.5, 60),
        ("link", "bg", bg, "ссылки в тексте", 4.5, 75),
        ("link", "свечение", glow, "ссылки, номера разделов 12.5px моно", 4.5, 60),
        ("link", "accent-soft", soft, "метка избранной карточки, бейдж", 4.5, 60),
        ("link", "soft+свечение", soft_glow, "метка избранной карточки, бейдж", 4.5, 60),
        ("accent", "bg", bg, "цифры достижений 40px жирные", 3.0, 45),
        ("accent", "свечение", glow, "цифры достижений 40px жирные", 3.0, 45),
        ("accent-ink", "btn", btn, "кнопка 16px/600, монограмма, иконки подвала", 4.5, 60),
        ("accent-ink", "btn-hover", btn_hover, "кнопка при наведении", 4.5, 60),
        ("edge", "bg", bg, "контур карточек и кнопок (нетекст)", 3.0, 15),
        ("accent", "bg", bg, "черта под заголовком, фокус (нетекст)", 3.0, 15),
    ]
    fails = 0
    print(f"{'текст':<11} {'фон':<12} {'WCAG':>6} {'APCA Lc':>8}  роль")
    for txt, bg_name, bg_rgb, role, w_min, l_min in pairs:
        if bg_rgb is None or txt not in t:
            print(f"{txt:<11} {bg_name:<12} — токен не найден")
            fails += 1
            continue
        fg = over(t[txt], bg_rgb)
        w, lc = wcag(fg, bg_rgb), abs(apca(fg, bg_rgb))
        bad = []
        if w < w_min:
            bad.append(f"WCAG<{w_min}")
        if lc < l_min:
            bad.append(f"Lc<{l_min}")
        fails += bool(bad)
        mark = "FAIL " + ",".join(bad) if bad else "ok"
        print(f"{txt:<11} {bg_name:<12} {w:>6.2f} {lc:>8.1f}  {role} — {mark}")
    print("ИТОГ:", "ok" if not fails else f"ниже порога пар: {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
