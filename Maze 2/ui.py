"""Вывод в терминал: цвета, сообщения, ввод."""

COLORS = {
    "wall": "90", "player": "1;93", "monster": "1;91", "boss": "1;95",
    "chest": "33", "portal": "1;95", "exit": "1;92", "stairs": "1;92",
    "key": "1;93", "item": "36", "trap": "31", "merchant": "1;96",
    "fountain": "1;94", "good": "92", "bad": "91", "dim": "90",
    "title": "1;96", "gold": "93", "poison": "32", "rage": "1;31",
}

use_color = True


def paint(text, color):
    if not use_color or color is None:
        return text
    return f"\033[{COLORS[color]}m{text}\033[0m"


def say(text, color=None):
    print(paint(text, color))


def ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        return "q"


def bar(value, maximum, width=10, color="good"):
    filled = max(0, min(width, round(width * value / maximum)))
    return paint("█" * filled, color) + paint("░" * (width - filled), "dim")
