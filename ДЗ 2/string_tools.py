"""Практика по строковым методам (задания 1-5 с доски).

Для каждого задания есть пример текста из задания; можно ввести свой.
"""

text_1 = "пРиВет_МИР"
text_2 = "Ботать_это_круто_Очень_круто"
text_3 = "1,2,3,4"
text_4a = "1234*&:1}"
text_4b = "----abc1234___"
text_5 = "......Python is AWESome...."


def task_1(text):
    """upper(), lower(), capitalize()"""
    print("upper():     ", text.upper())
    print("lower():     ", text.lower())
    print("capitalize():", text.capitalize())


def task_2(text):
    """find(), replace(), count(), *index()"""
    word = "круто"

    pos = text.find(word)
    print(f"1) Позиция первого '{word}': {pos}")
    # index() делает то же самое, но вместо -1 бросает ValueError
    try:
        print(f"   index(): {text.index(word)}")
    except ValueError:
        print("   index(): подстрока не найдена")

    print(f"2) Замена '{word}' на '*': {text.replace(word, '*')}")
    print(f"3) Количество букв 'о': {text.lower().count('о')}")


def task_3(text):
    """split(), join()"""
    parts = text.split(",")
    print("split(','):", parts)
    print("join('-'): ", "-".join(parts))
    if all(p.strip().isdigit() for p in parts):
        print("сумма:     ", sum(int(p) for p in parts))


def task_4(text):
    """isdigit(), isalpha(), strip(), *format, f-строки"""
    print(f"isdigit(): {text.isdigit()}, isalpha(): {text.isalpha()}")

    # strip() убирает указанные символы только по краям
    cleaned = text.strip("-_*&:}{ ")
    print(f"strip(...): '{cleaned}'")
    print("format():   '{}' -> '{}'".format(text, cleaned))
    print(f"f-строка:   {text!r} -> {cleaned!r}, длина {len(cleaned)}")


def task_5(text):
    """Очистка: убрать точки по краям и поправить регистр"""
    cleaned = text.strip(".")
    print("strip('.'):", cleaned)
    print("swapcase():", cleaned.swapcase())
    print("title():   ", cleaned.title())
    print("слова:     ", cleaned.split())


TASKS = {
    "1": (task_1, text_1),
    "2": (task_2, text_2),
    "3": (task_3, text_3),
    "4": (task_4, None),  # два примера, см. ниже
    "5": (task_5, text_5),
}


def main():
    print("Строковые задания. Выберите номер 1-5 (q — выход).")
    while True:
        choice = input("\nЗадание: ").strip().lower()
        if choice in ("q", "exit"):
            break
        if choice not in TASKS:
            print("Введите число от 1 до 5.")
            continue

        func, sample = TASKS[choice]
        if choice == "4":
            samples = [text_4a, text_4b]
        else:
            custom = input(f"Свой текст (Enter — пример '{sample}'): ")
            samples = [custom or sample]

        for s in samples:
            print(f"\n--- {s!r} ---")
            func(s)

    print("Пока!")


if __name__ == "__main__":
    main()
