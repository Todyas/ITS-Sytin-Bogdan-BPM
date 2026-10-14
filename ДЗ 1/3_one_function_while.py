"""Калькулятор №3: одна функция и цикл while.

Вся логика внутри одной функции, считает, пока не введут q.
"""


def calculator():
    print("Калькулятор. Операции: + - * / ** % //")
    print("Для выхода введите q.\n")

    while True:
        raw = input("Первое число: ").strip().replace(",", ".")
        if raw.lower() == "q":
            break
        try:
            a = float(raw)
        except ValueError:
            print("Это не число, попробуйте ещё раз.\n")
            continue

        op = input("Операция: ").strip()
        if op.lower() == "q":
            break

        raw = input("Второе число: ").strip().replace(",", ".")
        if raw.lower() == "q":
            break
        try:
            b = float(raw)
        except ValueError:
            print("Это не число, попробуйте ещё раз.\n")
            continue

        try:
            if op == "+":
                result = a + b
            elif op == "-":
                result = a - b
            elif op == "*":
                result = a * b
            elif op == "/":
                result = a / b
            elif op == "**":
                result = a ** b
            elif op == "%":
                result = a % b
            elif op == "//":
                result = a // b
            else:
                print("Неизвестная операция.\n")
                continue
        except ZeroDivisionError:
            print("Ошибка: деление на ноль.\n")
            continue
        except OverflowError:
            print("Ошибка: слишком большое число.\n")
            continue

        print("Результат:", result, "\n")

    print("Пока!")


calculator()
