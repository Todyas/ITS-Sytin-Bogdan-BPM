"""Maze 2: спуск в подземелье Минотавра.

Запуск:
    python main.py                 3 этажа, первый 6 x 9
    python main.py 8 12            свой размер первого этажа
    python main.py --floors 5      больше этажей
    python main.py --seed 42       один и тот же мир
    python main.py --load          продолжить сохранённую игру
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

import ui
from game import HELP, SAVE_FILE, Game
from ui import say

RECORDS_FILE = Path(__file__).with_name("records.json")


def load_records():
    try:
        return json.loads(RECORDS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def save_record(game):
    name = ui.ask("Как вас записать в таблицу рекордов? ") or "Безымянный"
    records = load_records()
    records.append({"name": name, "score": game.score(), "floor": game.depth,
                    "won": game.won, "date": date.today().isoformat()})
    records.sort(key=lambda record: record["score"], reverse=True)
    records = records[:10]  # срезом оставляем десятку лучших
    RECORDS_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    say("\nТаблица рекордов", "title")
    for place, record in enumerate(records, start=1):
        result = "выбрался" if record["won"] else f"этаж {record['floor']}"
        line = f"  {place:>2}. {record['name']:<14} {record['score']:>6}  {result:<10} {record['date']}"
        say(line, "gold" if record["name"] == name and record["score"] == game.score() else None)


def main():
    parser = argparse.ArgumentParser(description="Maze 2: спуск в подземелье Минотавра")
    parser.add_argument("rows", nargs="?", type=int, default=6, help="строк комнат на первом этаже")
    parser.add_argument("cols", nargs="?", type=int, default=9, help="столбцов комнат на первом этаже")
    parser.add_argument("--floors", type=int, default=3, help="сколько этажей (последний — с боссом)")
    parser.add_argument("--seed", type=int, help="зерно генератора")
    parser.add_argument("--load", action="store_true", help="продолжить сохранённую игру")
    parser.add_argument("--no-color", action="store_true", help="без цветов")
    args = parser.parse_args()
    if args.rows < 4 or args.cols < 4 or args.floors < 1:
        parser.error("нужно хотя бы 4 x 4 комнаты и 1 этаж")

    ui.use_color = not args.no_color and sys.stdout.isatty()
    if ui.use_color and os.name == "nt":
        os.system("")  # включает ANSI-цвета в консоли Windows

    if args.load:
        if not SAVE_FILE.exists():
            parser.error("сохранения нет")
        game = Game.load()
        say("С возвращением!", "title")
    else:
        game = Game(args.rows, args.cols, args.floors, args.seed)
        say("MAZE 2: спуск в подземелье Минотавра", "title")
        print(f"Спуститесь на {args.floors}-й этаж, найдя на каждом ключ от лестницы (>),\n"
              "победите Минотавра и выйдите через E. Монстры теперь ходят и чуют вас.")
        print(HELP)

    game.run()
    if getattr(game, "saved", False):
        return
    say(f"\nЭтаж {game.depth}, уровень {game.level}, монстров: {game.stats['убито']}, "
        f"золото: {game.gold}. Очки: {game.score()}", "title")
    for name, why in game.achievements():
        say(f"  ★ {name} — {why}", "gold")
    save_record(game)


if __name__ == "__main__":
    main()
