"""Предметы, лут, рецепты крафта и инвентарь."""

import itertools
from collections import Counter
from dataclasses import dataclass, replace

WEAPON = "оружие"
ARMOR = "броня"
POTION = "зелье"
SCROLL = "свиток"
TREASURE = "сокровище"
TOOL = "инструмент"
MATERIAL = "материал"
KEY = "ключ"

COIN = "Золотая монета"
FLOOR_KEY = "Ключ от лестницы"
PHOENIX = "Перо феникса"
TORCH = "Факел"
BOMB = "Бомба"
WHETSTONE = "Точильный камень"
ANTIDOTE = "Противоядие"
RAGE = "Зелье ярости"
MAP_SCROLL = "Свиток карты"
TELEPORT_SCROLL = "Свиток телепорта"
FIRE_SCROLL = "Свиток огня"


# eq=False: предметы сравниваются «по личности», а не по полям. Иначе два
# одинаковых кинжала были бы равны, и remove() мог бы выкинуть не тот,
# что у игрока в руках.
@dataclass(eq=False)
class Item:
    name: str
    kind: str
    value: int = 0       # цена в золоте
    power: int = 0       # урон оружия / защита брони / сила зелья или свитка
    weight: int = 1
    durability: int = 0  # прочность оружия и брони, для факела — сколько ходов горит

    def __str__(self):
        info = [self.kind]
        if self.kind == WEAPON:
            info.append(f"урон {self.power}, прочность {self.durability}")
        elif self.kind == ARMOR:
            info.append(f"защита {self.power}, прочность {self.durability}")
        elif self.name == TORCH:
            info.append(f"горит {self.durability} ходов")
        elif self.kind == POTION and self.name != RAGE and self.power:
            info.append(f"+{self.power} hp")
        elif self.power:
            info.append(f"сила {self.power}")
        if self.value:
            info.append(f"{self.value} зол.")
        info.append(f"вес {self.weight}")
        return f"{self.name} ({', '.join(info)})"


TEMPLATES = {item.name: item for item in [
    Item("Кинжал", WEAPON, value=8, power=4, weight=1, durability=15),
    Item("Ржавый меч", WEAPON, value=12, power=6, weight=4, durability=10),
    Item("Костяное копьё", WEAPON, value=20, power=8, weight=3, durability=12),
    Item("Боевой топор", WEAPON, value=25, power=10, weight=6, durability=8),
    Item("Посох мага", WEAPON, value=35, power=12, weight=3, durability=6),
    Item("Двуручный меч", WEAPON, value=60, power=15, weight=7, durability=12),
    Item("Рубиновый посох", WEAPON, value=120, power=20, weight=3, durability=12),

    Item("Кожаная куртка", ARMOR, value=15, power=2, weight=3, durability=15),
    Item("Костяной доспех", ARMOR, value=30, power=3, weight=5, durability=14),
    Item("Кольчуга", ARMOR, value=70, power=5, weight=6, durability=20),

    Item("Малое зелье", POTION, value=8, power=25, weight=1),
    Item("Большое зелье", POTION, value=25, power=60, weight=2),
    Item(ANTIDOTE, POTION, value=12, weight=1),
    Item(RAGE, POTION, value=30, power=4, weight=1),  # power — сколько раундов ярости

    Item(MAP_SCROLL, SCROLL, value=20, weight=0),
    Item(TELEPORT_SCROLL, SCROLL, value=25, weight=0),
    Item(FIRE_SCROLL, SCROLL, value=30, power=25, weight=0),

    Item(COIN, TREASURE, value=10, weight=0),
    Item("Рубин", TREASURE, value=50, weight=1),
    Item("Изумруд", TREASURE, value=80, weight=1),
    Item("Корона", TREASURE, value=150, weight=5),

    Item(TORCH, TOOL, value=6, weight=1, durability=40),
    Item(BOMB, TOOL, value=20, weight=2),
    Item(WHETSTONE, TOOL, value=10, weight=2),
    Item(PHOENIX, TOOL, value=60, weight=0),

    Item("Палка", MATERIAL, value=1, weight=1),
    Item("Тряпка", MATERIAL, value=1, weight=0),
    Item("Кость", MATERIAL, value=1, weight=1),
    Item("Булыжник", MATERIAL, weight=3),
    Item("Слизь", MATERIAL, value=2, weight=1),
    Item("Гриб", MATERIAL, value=2, weight=0),

    Item(FLOOR_KEY, KEY, weight=0),
]}

# (предмет, вес в розыгрыше, с какого этажа встречается)
LOOT_TABLE = [
    ("Кинжал", 5, 1), ("Ржавый меч", 5, 1), ("Боевой топор", 3, 1),
    ("Посох мага", 2, 2), ("Двуручный меч", 2, 3),
    ("Кожаная куртка", 4, 1), ("Кольчуга", 2, 2),
    ("Малое зелье", 12, 1), ("Большое зелье", 4, 2), (ANTIDOTE, 4, 1), (RAGE, 2, 1),
    (MAP_SCROLL, 3, 1), (TELEPORT_SCROLL, 3, 1), (FIRE_SCROLL, 3, 1),
    (COIN, 16, 1), ("Рубин", 5, 1), ("Изумруд", 3, 2), ("Корона", 1, 2),
    (TORCH, 5, 1), (BOMB, 3, 1), (WHETSTONE, 3, 1), (PHOENIX, 1, 2),
    ("Палка", 7, 1), ("Тряпка", 7, 1), ("Кость", 7, 1), ("Булыжник", 4, 1),
    ("Слизь", 3, 1), ("Гриб", 5, 1),
]

RECIPES = [
    (["Палка", "Тряпка"], TORCH),
    (["Малое зелье", "Малое зелье"], "Большое зелье"),
    (["Гриб", "Малое зелье"], ANTIDOTE),
    (["Палка", "Кость", "Кость"], "Костяное копьё"),
    (["Кость", "Кость", "Кость", "Тряпка"], "Костяной доспех"),
    (["Булыжник", "Слизь", "Тряпка"], BOMB),
    (["Гриб", "Гриб", "Слизь"], RAGE),
    (["Посох мага", "Рубин"], "Рубиновый посох"),
]


def make_item(name):
    """Каждый предмет в игре — копия шаблона (replace), шаблоны не трогаем."""
    return replace(TEMPLATES[name])


def random_loot(rng, count, depth):
    pool = [(name, weight) for name, weight, min_depth in LOOT_TABLE if depth >= min_depth]
    names, weights = zip(*pool)  # «распаковка» списка пар в два кортежа
    return [make_item(name) for name in rng.choices(names, weights=weights, k=count)]


class Inventory:
    SORT_KEYS = {
        "имя": lambda item: item.name,
        "цена": lambda item: item.value,
        "вес": lambda item: item.weight,
        "сила": lambda item: item.power,
        "тип": lambda item: item.kind,
    }

    def __init__(self, max_weight=30):
        self.items = []
        self.max_weight = max_weight

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __contains__(self, name):
        return name in self.names()

    def __getitem__(self, index):
        return self.items[index]

    def names(self):
        return [item.name for item in self.items]

    def weight(self):
        return sum(item.weight for item in self.items)

    def free(self):
        return self.max_weight - self.weight()

    # --- собрать: append / extend
    def add(self, item):
        if item.weight > self.free():
            return False
        self.items.append(item)
        return True

    def add_many(self, items):
        taken, rest = [], []
        free = self.free()
        for item in items:
            if item.weight <= free:
                taken.append(item)
                free -= item.weight
            else:
                rest.append(item)
        self.items.extend(taken)
        return taken, rest

    # --- выбросить: pop / remove
    def pop(self, index=-1):
        return self.items.pop(index)

    def remove(self, item):
        self.items.remove(item)

    def take_named(self, name):
        """Убирает первый предмет, чьё имя начинается с name."""
        item = self.first(name)
        if item is not None:
            self.items.remove(item)
        return item

    # --- сортировка: sort / reverse
    def sort(self, by, reverse=False):
        self.items.sort(key=self.SORT_KEYS[by])
        if reverse:
            self.items.reverse()

    # --- поиск: in / index
    def find(self, name):
        if name not in self:
            return None
        return self.names().index(name)

    def first(self, prefix):
        prefix = prefix.lower()
        return next((item for item in self.items if item.name.lower().startswith(prefix)), None)

    def of_kind(self, kind):
        return (item for item in self.items if item.kind == kind)

    def best(self, kind):
        return max(self.of_kind(kind), key=lambda item: item.power, default=None)

    def top(self, n=3):
        return sorted(self.items, key=lambda item: item.value, reverse=True)[:n]

    def grouped(self):
        by_kind = sorted(self.items, key=lambda item: item.kind)
        for kind, group in itertools.groupby(by_kind, key=lambda item: item.kind):
            yield kind, list(group)

    def counts(self):
        return Counter(self.names())

    # --- крафт: копия списка имён, из которой вычёркиваем ингредиенты
    def can_craft(self, ingredients):
        left = self.names().copy()
        for name in ingredients:
            if name not in left:
                return False
            left.remove(name)
        return True

    def craft(self, ingredients, result):
        """Возвращает новый предмет или строку с причиной отказа."""
        if not self.can_craft(ingredients):
            return "не хватает ингредиентов"
        used = []
        for name in ingredients:
            item = next(item for item in self.items if item.name == name and item not in used)
            used.append(item)
        item = make_item(result)
        if item.weight > self.free() + sum(part.weight for part in used):
            return "результат не влезет в рюкзак"
        for part in used:
            self.items.remove(part)
        self.items.append(item)
        return item
