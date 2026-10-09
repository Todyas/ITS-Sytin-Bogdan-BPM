from math import *

while (True):
    a = input("Введите выражение: ")
    if a == "q":
        break
    print(eval(a))