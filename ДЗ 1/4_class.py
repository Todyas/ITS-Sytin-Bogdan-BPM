"""Калькулятор №4: через класс.

Операции — методы класса, плюс история вычислений.
"""


class Calculator:
    def __init__(self):
        self.history = []
        self.operations = {
            "+": self.add,
            "-": self.subtract,
            "*": self.multiply,
            "/": self.divide,
            "**": self.power,
            "%": self.modulo,
            "//": self.floor_divide,
        }

    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    def multiply(self, a, b):
        return a * b

    def divide(self, a, b):
        return a / b

    def power(self, a, b):
        return a ** b

    def modulo(self, a, b):
        return a % b

    def floor_divide(self, a, b):
        return a // b

    def calculate(self, a, op, b):
        if op not in self.operations:
            raise ValueError("Неизвестная операция")
        result = self.operations[op](a, b)
        self.history.append(f"{self.format(a)} {op} {self.format(b)} = {self.format(result)}")
        return result

    @staticmethod
    def format(x):
        return str(int(x)) if x.is_integer() else str(x)

    @staticmethod
    def read_number(prompt):
        while True:
            raw = input(prompt).strip().replace(",", ".")
            if raw.lower() == "q":
                return None
            try:
                return float(raw)
            except ValueError:
                print("Это не число, попробуйте ещё раз.")

    def run(self):
        print("Калькулятор. Операции:", " ".join(self.operations))
        print("Для выхода введите q, для истории — h.\n")

        while True:
            a = self.read_number("Первое число: ")
            if a is None:
                break

            op = input("Операция: ").strip()
            if op.lower() == "q":
                break
            if op.lower() == "h":
                print("\n".join(self.history) or "История пуста.", "\n")
                continue

            b = self.read_number("Второе число: ")
            if b is None:
                break

            try:
                result = self.calculate(a, op, b)
            except ValueError as e:
                print(f"Ошибка: {e}.\n")
                continue
            except ZeroDivisionError:
                print("Ошибка: деление на ноль.\n")
                continue
            except OverflowError:
                print("Ошибка: слишком большое число.\n")
                continue

            print(self.history[-1], "\n")

        print("Пока!")


if __name__ == "__main__":
    Calculator().run()
