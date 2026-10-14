"""Калькулятор №2: через функции.

Каждая операция, ввод и вывод вынесены в отдельные функции.
"""


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ZeroDivisionError
    return a / b


def power(a, b):
    return a ** b


def modulo(a, b):
    return a % b


def floor_divide(a, b):
    return a // b


OPERATIONS = {
    "+": add,
    "-": subtract,
    "*": multiply,
    "/": divide,
    "**": power,
    "%": modulo,
    "//": floor_divide,
}


def read_number(prompt):
    raw = input(prompt).strip().replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        print("Это не число.")
        return None


def read_operation():
    op = input("Операция (" + " ".join(OPERATIONS) + "): ").strip()
    if op not in OPERATIONS:
        print("Неизвестная операция.")
        return None
    return op


def format_number(x):
    return str(int(x)) if x.is_integer() else str(x)


def calculate(a, op, b):
    try:
        return OPERATIONS[op](a, b)
    except ZeroDivisionError:
        print("Ошибка: деление на ноль.")
    except OverflowError:
        print("Ошибка: слишком большое число.")
    return None


def main():
    a = read_number("Первое число: ")
    if a is None:
        return
    op = read_operation()
    if op is None:
        return
    b = read_number("Второе число: ")
    if b is None:
        return

    result = calculate(a, op, b)
    if result is not None:
        print(f"{format_number(a)} {op} {format_number(b)} = {format_number(result)}")


if __name__ == "__main__":
    main()
