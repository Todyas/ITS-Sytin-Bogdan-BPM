OPERATIONS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
    "**": lambda a, b: a ** b,
    "%": lambda a, b: a % b,
    "//": lambda a, b: a // b,
}


def read_number(prompt):
    while True:
        raw = input(prompt).strip().replace(",", ".")
        if raw.lower() in ("q", "exit"):
            return None
        try:
            return float(raw)
        except ValueError:
            print("Это не число, попробуйте ещё раз.")


def format_number(x):
    return str(int(x)) if x == int(x) else str(x)


def main():
    print("Калькулятор. Операции:", " ".join(OPERATIONS))
    print("Для выхода введите q.\n")

    while True:
        a = read_number("Первое число: ")
        if a is None:
            break

        op = input("Операция: ").strip()
        if op.lower() in ("q", "exit"):
            break
        if op not in OPERATIONS:
            print("Неизвестная операция.\n")
            continue

        b = read_number("Второе число: ")
        if b is None:
            break

        try:
            result = OPERATIONS[op](a, b)
        except ZeroDivisionError:
            print("Ошибка: деление на ноль.\n")
            continue
        except OverflowError:
            print("Ошибка: слишком большое число.\n")
            continue

        print(f"{format_number(a)} {op} {format_number(b)} = {format_number(result)}\n")

    print("Пока!")


if __name__ == "__main__":
    main()
