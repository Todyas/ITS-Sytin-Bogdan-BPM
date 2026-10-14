"""ДЗ 3. Бродилка по лабиринту с инвентарём (терминал, только стандартная библиотека).

Запуск:
    python maze.py               лабиринт 7 x 10
    python maze.py 10 15         свой размер n x m
    python maze.py --seed 42     один и тот же лабиринт при каждом запуске
    python maze.py --no-color    без цветов (если терминал их не понимает)

Цель: найти золотой ключ (K) и выйти через дверь (E), не потеряв все hp.

Где какие операции со списками (задания с доски):
    1) собрать предметы ............ append  -> Inventory.add
                                     extend  -> Inventory.add_many (сундук, «взять»)
    2) выбросить предметы .......... remove  -> Inventory.drop_named
                                     pop     -> Inventory.drop_at / ловушка-воришка
    3) сортировать инвентарь ....... sort    -> Inventory.sort
                                     reverse -> Inventory.sort(..., reverse) / команда rev
    4) найти ключевой предмет ...... in      -> Inventory.__contains__
                                     index   -> Inventory.find
    5*) копировать и менять списки . copy    -> Inventory.snapshot, команда copy
                                     slice   -> Inventory.top, пары порталов, срезы в copy
    6**) итераторы коллекций ....... Inventory.__iter__, Maze.__iter__, генераторы
                                     neighbors / weapons, iter()+next() при расстановке
                                     комнат, zip, enumerate, itertools.groupby
"""

import argparse
import itertools
import os
import random
import sys
from collections import deque
from dataclasses import dataclass, field, replace

# ---------------------------------------------------------------- предметы

WEAPON = "оружие"
POTION = "зелье"
TREASURE = "сокровище"
TOOL = "инструмент"
KEY = "ключ"
JUNK = "хлам"

GOLDEN_KEY = "Золотой ключ"
PHOENIX = "Перо феникса"
WHETSTONE = "Точильный камень"


@dataclass
class Item:
    name: str
    kind: str
    value: int = 0       # цена в золоте
    power: int = 0       # урон оружия или сколько лечит зелье
    weight: int = 1
    durability: int = 0  # прочность оружия, тратится в бою

    def __str__(self):
        info = [self.kind]
        if self.kind == WEAPON:
            info.append(f"урон {self.power}, прочность {self.durability}")
        elif self.kind == POTION:
            info.append(f"+{self.power} hp")
        if self.value:
            info.append(f"{self.value} зол.")
        info.append(f"вес {self.weight}")
        return f"{self.name} ({', '.join(info)})"


# Шаблоны предметов. В игру всегда попадает копия (replace), иначе заточив
# один меч, мы бы «заточили» все мечи в лабиринте разом.
TEMPLATES = {item.name: item for item in [
    Item("Ржавый меч", WEAPON, value=5, power=6, weight=4, durability=8),
    Item("Боевой топор", WEAPON, value=15, power=9, weight=6, durability=6),
    Item("Кинжал", WEAPON, value=8, power=4, weight=1, durability=15),
    Item("Посох мага", WEAPON, value=30, power=13, weight=3, durability=4),
    Item("Малое зелье", POTION, value=5, power=20, weight=1),
    Item("Большое зелье", POTION, value=15, power=50, weight=2),
    Item("Золотая монета", TREASURE, value=10, weight=0),
    Item("Рубин", TREASURE, value=50, weight=1),
    Item("Корона", TREASURE, value=120, weight=5),
    Item(WHETSTONE, TOOL, value=3, weight=2),
    Item(PHOENIX, TOOL, value=40, weight=0),
    Item("Старый сапог", JUNK, weight=2),
    Item("Кость", JUNK, weight=1),
    Item("Булыжник", JUNK, weight=4),
    Item(GOLDEN_KEY, KEY, value=0, weight=1),
]}

# Насколько часто что выпадает из сундуков и монстров
LOOT_CHANCES = {
    "Ржавый меч": 6, "Боевой топор": 4, "Кинжал": 6, "Посох мага": 2,
    "Малое зелье": 10, "Большое зелье": 4,
    "Золотая монета": 14, "Рубин": 5, "Корона": 1,
    WHETSTONE: 4, PHOENIX: 1,
    "Старый сапог": 5, "Кость": 6, "Булыжник": 4,
}


def make_item(name):
    return replace(TEMPLATES[name])


def random_loot(rng, count):
    names = rng.choices(list(LOOT_CHANCES), weights=list(LOOT_CHANCES.values()), k=count)
    return [make_item(name) for name in names]


# ---------------------------------------------------------------- инвентарь

class Inventory:
    SORT_KEYS = {
        "имя": lambda item: item.name,
        "цена": lambda item: item.value,
        "вес": lambda item: item.weight,
        "сила": lambda item: item.power,
        "тип": lambda item: item.kind,
    }

    def __init__(self, max_weight=25):
        self.items = []
        self.max_weight = max_weight

    # --- итерация: по инвентарю можно ходить for-ом, как по списку
    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __contains__(self, name):
        return name in self.names()  # in

    def names(self):
        return [item.name for item in self.items]

    def weight(self):
        return sum(item.weight for item in self.items)

    # --- 1) собрать
    def add(self, item):
        if self.weight() + item.weight > self.max_weight:
            return False
        self.items.append(item)  # append
        return True

    def add_many(self, items):
        """Кладёт всё, что влезает по весу. Возвращает (взяли, не влезло)."""
        taken, rest = [], []
        free = self.max_weight - self.weight()
        for item in items:
            if item.weight <= free:
                taken.append(item)
                free -= item.weight
            else:
                rest.append(item)
        self.items.extend(taken)  # extend
        return taken, rest

    # --- 2) выбросить
    def drop_at(self, index):
        return self.items.pop(index)  # pop

    def drop_named(self, name):
        for item in self.items:
            if item.name.lower().startswith(name.lower()):
                self.items.remove(item)  # remove
                return item
        return None

    # --- 3) сортировать
    def sort(self, by, reverse=False):
        self.items.sort(key=self.SORT_KEYS[by])  # sort
        if reverse:
            self.items.reverse()  # reverse

    # --- 4) найти
    def find(self, name):
        """Позиция предмета (с нуля) или None."""
        if name not in self:  # in
            return None
        return self.names().index(name)  # index

    # --- 5) копии и срезы
    def snapshot(self):
        """Глубокая копия: новый список и новые предметы внутри."""
        return [replace(item) for item in self.items]

    def top(self, n=3):
        """n самых дорогих: сортируем копию и берём срез."""
        return sorted(self.items, key=lambda item: item.value, reverse=True)[:n]

    # --- 6) генераторы
    def weapons(self):
        return (item for item in self.items if item.kind == WEAPON)

    def best_weapon(self):
        return max(self.weapons(), key=lambda item: item.power, default=None)

    def grouped(self):
        by_kind = sorted(self.items, key=lambda item: item.kind)
        for kind, group in itertools.groupby(by_kind, key=lambda item: item.kind):
            yield kind, list(group)


# ---------------------------------------------------------------- лабиринт

EMPTY = "пусто"
CHEST = "сундук"
MONSTER = "монстр"
TRAP = "ловушка"
PORTAL = "портал"
EXIT = "выход"

DIRECTIONS = {
    "w": (-1, 0), "ц": (-1, 0),
    "s": (1, 0), "ы": (1, 0),
    "a": (0, -1), "ф": (0, -1),
    "d": (0, 1), "в": (0, 1),
}


@dataclass
class Monster:
    name: str
    hp: int
    damage: int
    loot: int


MONSTERS = [
    Monster("Крыса", 8, 3, 1),
    Monster("Скелет", 18, 6, 2),
    Monster("Гоблин", 14, 5, 2),
    Monster("Призрак", 22, 8, 2),
    Monster("Огр", 35, 11, 3),
]


@dataclass
class Room:
    kind: str = EMPTY
    items: list = field(default_factory=list)  # что лежит на полу
    monster: Monster = None
    portal_to: tuple = None
    trap_found: bool = False


class Maze:
    """n x m комнат. В сетке символов комната (r, c) лежит в (2r+1, 2c+1),
    а между соседними комнатами клетка-стена, которую можно «пробить»."""

    def __init__(self, rows, cols, rng):
        self.rows, self.cols = rows, cols
        self.grid = [["#"] * (2 * cols + 1) for _ in range(2 * rows + 1)]
        self.rooms = {(r, c): Room() for r in range(rows) for c in range(cols)}
        self._carve(rng)
        self._add_loops(rng)

    def __iter__(self):
        return iter(self.rooms.items())

    def around(self, pos):
        """Все соседние комнаты в пределах поля (генератор)."""
        r, c = pos
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            if 0 <= r + dr < self.rows and 0 <= c + dc < self.cols:
                yield r + dr, c + dc

    def neighbors(self, pos):
        """Соседи, в которые реально можно пройти (без стены)."""
        return (other for other in self.around(pos) if self.is_open(pos, other))

    def _wall(self, a, b):
        return a[0] + b[0] + 1, a[1] + b[1] + 1

    def is_open(self, a, b):
        r, c = self._wall(a, b)
        return self.grid[r][c] == " "

    def _link(self, a, b):
        for r, c in (self._wall(a, b), (2 * a[0] + 1, 2 * a[1] + 1), (2 * b[0] + 1, 2 * b[1] + 1)):
            self.grid[r][c] = " "

    def _carve(self, rng):
        # «Рекурсивный» бэктрекинг на явном стеке: идём в случайного
        # непосещённого соседа, а в тупике откатываемся назад (pop)
        stack = [(0, 0)]
        visited = {(0, 0)}
        while stack:
            current = stack[-1]
            fresh = [p for p in self.around(current) if p not in visited]
            if not fresh:
                stack.pop()
                continue
            nxt = rng.choice(fresh)
            self._link(current, nxt)
            visited.add(nxt)
            stack.append(nxt)

    def _add_loops(self, rng):
        # Идеальный лабиринт без циклов скучноват: пробьём несколько лишних стен
        for pos in self.rooms:
            for other in self.around(pos):
                if rng.random() < 0.06:
                    self._link(pos, other)

    def distances(self, start):
        dist = {start: 0}
        queue = deque([start])
        while queue:
            pos = queue.popleft()
            for other in self.neighbors(pos):
                if other not in dist:
                    dist[other] = dist[pos] + 1
                    queue.append(other)
        return dist


def populate(maze, rng):
    start = (0, 0)
    dist = maze.distances(start)
    by_distance = sorted(dist, key=dist.get)
    exit_pos = by_distance[-1]
    maze.rooms[exit_pos].kind = EXIT

    # ключ где-то в дальней половине, но не на выходе
    far_half = by_distance[len(by_distance) // 2:-1]
    key_pos = rng.choice(far_half)
    maze.rooms[key_pos].items.append(make_item(GOLDEN_KEY))

    free = [pos for pos in maze.rooms if pos not in (start, exit_pos, key_pos)]
    rng.shuffle(free)
    area = maze.rows * maze.cols

    # порталы: берём чётное число клеток и склеиваем их попарно срезами + zip
    pairs = max(1, area // 35)
    portal_cells = free[:pairs * 2]
    for a, b in zip(portal_cells[::2], portal_cells[1::2]):
        maze.rooms[a].kind = maze.rooms[b].kind = PORTAL
        maze.rooms[a].portal_to, maze.rooms[b].portal_to = b, a

    # остальное раздаём по очереди из одного итератора: next() выдаёт
    # следующую свободную клетку, и одна клетка не достанется двоим
    cells = iter(free[pairs * 2:])
    plan = [(CHEST, area // 10), (MONSTER, area // 7), (TRAP, area // 9)]
    for kind, count in plan:
        for pos in itertools.islice(cells, count):
            room = maze.rooms[pos]
            room.kind = kind
            if kind == MONSTER:
                # чем дальше от входа, тем злее монстры
                tier = min(len(MONSTERS) - 1, dist[pos] * len(MONSTERS) // (dist[exit_pos] + 1))
                tier = max(0, tier - rng.randint(0, 1))
                room.monster = replace(MONSTERS[tier])
    # немного хлама и монет просто на полу
    for pos in itertools.islice(cells, area // 12):
        maze.rooms[pos].items.extend(random_loot(rng, 1))
    return start, exit_pos


# ---------------------------------------------------------------- вывод

COLORS = {"wall": "90", "player": "1;93", "monster": "1;91", "chest": "33",
          "portal": "1;95", "exit": "1;92", "key": "1;93", "item": "36",
          "trap": "31", "good": "92", "bad": "91", "dim": "90", "title": "1;96"}
USE_COLOR = True


def paint(text, color):
    if not USE_COLOR:
        return text
    return f"\033[{COLORS[color]}m{text}\033[0m"


def say(text, color=None):
    print(paint(text, color) if color else text)


HELP = """
Ходьба: w a s d (можно и ц ф ы в, и сразу несколько: ddd)
  i            инвентарь              g          инвентарь по типам
  t            взять всё с пола       use N      использовать предмет N
  drop N       выбросить предмет N    drop имя   выбросить по названию
  drop         выбросить последний    top [N]    N самых ценных
  sort поле    сортировать (имя/цена/вес/сила/тип), «sort цена -» по убыванию
  rev          перевернуть порядок    find [имя] найти предмет (по умолчанию ключ)
  copy         показать, чем копия отличается от «копии»
  h            помощь                 q          выйти
Легенда: @ вы  $ сундук  M монстр  O портал  E выход  K ключ  * вещи  ^ ловушка
"""


# ---------------------------------------------------------------- игра

class Game:
    def __init__(self, rows, cols, seed):
        self.rng = random.Random(seed)
        self.maze = Maze(rows, cols, self.rng)
        self.pos, self.exit_pos = populate(self.maze, self.rng)
        self.hp = self.max_hp = 100
        self.inventory = Inventory()
        self.inventory.add_many([make_item("Кинжал"), make_item("Малое зелье")])
        self.seen = set()
        self.turns = 0
        self.kills = 0
        self.over = False
        self.won = False
        self.reveal(self.pos)

    @property
    def x(self):
        return self.pos[1]

    @property
    def y(self):
        return self.pos[0]

    # --- карта
    def reveal(self, pos):
        self.seen.add(pos)
        self.seen.update(self.maze.neighbors(pos))

    def room_symbol(self, pos):
        if pos == self.pos:
            return paint("@", "player")
        room = self.maze.rooms[pos]
        if room.kind == MONSTER:
            return paint("M", "monster")
        if room.kind == CHEST:
            return paint("$", "chest")
        if room.kind == PORTAL:
            return paint("O", "portal")
        if room.kind == EXIT:
            return paint("E", "exit")
        if any(item.name == GOLDEN_KEY for item in room.items):
            return paint("K", "key")
        if room.items:
            return paint("*", "item")
        if room.kind == TRAP and room.trap_found:
            return paint("^", "trap")
        return " "

    def draw(self):
        lines = []
        for gr, row in enumerate(self.maze.grid):
            line = []
            for gc, ch in enumerate(row):
                # клетку сетки видно, если рядом есть увиденная комната
                near = {((gr + dr - 1) // 2, (gc + dc - 1) // 2)
                        for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                        if (gr + dr) % 2 and (gc + dc) % 2}
                if not near & self.seen:
                    line.append("  ")
                elif ch == "#":
                    line.append(paint("██", "wall"))
                elif gr % 2 and gc % 2:
                    line.append(self.room_symbol((gr // 2, gc // 2)) + " ")
                else:
                    line.append("  ")
            lines.append("".join(line))
        print("\n".join(lines))

    def status(self):
        filled = round(10 * self.hp / self.max_hp)
        bar = paint("█" * filled, "good" if self.hp > 30 else "bad") + paint("░" * (10 - filled), "dim")
        weapon = self.inventory.best_weapon()
        key = paint("есть", "key") if GOLDEN_KEY in self.inventory else "нет"
        print(f"hp {bar} {self.hp:>3}/{self.max_hp}   (x, y) = ({self.x}, {self.y})   "
              f"оружие: {weapon.name if weapon else 'кулаки'}   ключ: {key}   "
              f"рюкзак {self.inventory.weight()}/{self.inventory.max_weight}")

    # --- движение
    def move(self, dr, dc):
        target = (self.pos[0] + dr, self.pos[1] + dc)
        if target not in self.maze.rooms or not self.maze.is_open(self.pos, target):
            say("Там стена.", "dim")
            return True
        came_from, self.pos = self.pos, target
        self.turns += 1
        self.reveal(target)
        return self.enter_room(came_from)

    def enter_room(self, came_from):
        """True, если в комнате что-то случилось и серию шагов (ddd) пора прервать."""
        room = self.maze.rooms[self.pos]
        event = False
        if room.kind == TRAP and not room.trap_found:
            self.spring_trap(room)
            event = True
        elif room.kind == MONSTER:
            self.encounter(room, came_from)
            event = True
        elif room.kind == CHEST:
            self.open_chest(room)
            event = True
        elif room.kind == PORTAL:
            self.teleport(room)
            event = True
        elif room.kind == EXIT:
            self.try_exit()
            event = True
        if room.items and not self.over:
            listing = ", ".join(item.name for item in room.items)
            say(f"На полу: {listing}. Взять: t", "item")
            event = True
        return event

    def spring_trap(self, room):
        room.trap_found = True
        damage = self.rng.randint(8, 20)
        self.hurt(damage, f"Щёлк! Ловушка, -{damage} hp.")
        # иногда ловушка ещё и вытряхивает случайную вещь из рюкзака (pop)
        if self.inventory and self.rng.random() < 0.4:
            lost = self.inventory.drop_at(self.rng.randrange(len(self.inventory)))
            room.items.append(lost)
            say(f"Из рюкзака вывалился «{lost.name}» и остался лежать тут.", "bad")

    def open_chest(self, room):
        loot = random_loot(self.rng, self.rng.randint(2, 4))
        taken, rest = self.inventory.add_many(loot)
        room.kind = EMPTY
        say("Сундук! Внутри: " + ", ".join(item.name for item in loot), "chest")
        if taken:
            say("Забрали: " + ", ".join(item.name for item in taken), "good")
        if rest:
            room.items.extend(rest)
            say("Не влезло в рюкзак, осталось на полу: " + ", ".join(item.name for item in rest), "bad")

    def teleport(self, room):
        self.pos = room.portal_to
        self.reveal(self.pos)
        say(f"Портал засасывает вас... и выплёвывает в ({self.x}, {self.y}).", "portal")

    def try_exit(self):
        index = self.inventory.find(GOLDEN_KEY)
        if index is None:
            say("Массивная дверь заперта. Нужен золотой ключ.", "exit")
            return
        self.inventory.drop_at(index)
        say("Ключ щёлкает в замке, дверь открывается. Вы выбрались!", "exit")
        self.won = self.over = True

    # --- бой
    def encounter(self, room, came_from):
        monster = room.monster
        weapon = self.inventory.best_weapon()
        say(f"{monster.name}! (hp {monster.hp}, урон ~{monster.damage})", "monster")
        say(f"Ваше оружие: {weapon or 'кулаки'}")
        choice = ask("Драться (f) или бежать (r)? ")
        if choice.startswith(("r", "к", "б")):
            hit = self.rng.randint(0, monster.damage)
            self.pos = came_from
            self.hurt(hit, f"Вы удрали обратно, получив в спину {hit}.")
            return
        self.fight(room, monster)

    def fight(self, room, monster):
        while monster.hp > 0 and not self.over:
            weapon = self.inventory.best_weapon()
            damage = (weapon.power if weapon else 2) + self.rng.randint(-1, 2)
            monster.hp -= damage
            text = f"  Вы бьёте на {damage}"
            if weapon:
                weapon.durability -= 1  # меняем свойство предмета прямо в инвентаре
                if weapon.durability <= 0:
                    self.inventory.items.remove(weapon)
                    text += paint(f", «{weapon.name}» сломался!", "bad")
            print(text)
            if monster.hp <= 0:
                break
            hit = max(0, monster.damage + self.rng.randint(-2, 2))
            self.hurt(hit, f"  {monster.name} бьёт на {hit}")
        if self.over:
            return
        self.kills += 1
        loot = random_loot(self.rng, monster.loot)
        room.kind, room.monster = EMPTY, None
        room.items.extend(loot)
        say(f"{monster.name} повержен! Выпало: " + ", ".join(item.name for item in loot), "good")

    def hurt(self, damage, message):
        self.hp -= damage
        say(message, "bad")
        if self.hp > 0:
            return
        if PHOENIX in self.inventory:
            self.inventory.drop_named(PHOENIX)
            self.hp = self.max_hp // 2
            say("Перо феникса вспыхивает, и вы встаёте с 50 hp!", "key")
            return
        self.hp = 0
        self.over = True
        say("Вы пали в лабиринте...", "bad")

    # --- команды инвентаря
    def show_inventory(self):
        if not self.inventory:
            say("Рюкзак пуст.", "dim")
            return
        for number, item in enumerate(self.inventory, start=1):
            print(f"  {number:>2}. {item}")
        print(f"  вес {self.inventory.weight()}/{self.inventory.max_weight}")

    def show_grouped(self):
        for kind, items in self.inventory.grouped():
            print(f"  {kind}: " + ", ".join(item.name for item in items))

    def take(self):
        room = self.maze.rooms[self.pos]
        if not room.items:
            say("На полу ничего нет.", "dim")
            return
        taken, rest = self.inventory.add_many(room.items)
        room.items = rest
        if taken:
            say("Взяли: " + ", ".join(item.name for item in taken), "good")
        if rest:
            say("Не влезло: " + ", ".join(item.name for item in rest) + ". Выбросьте что-нибудь (drop).", "bad")

    def item_index(self, arg):
        if not arg.isdigit() or not 1 <= int(arg) <= len(self.inventory):
            say(f"Нет предмета с номером {arg}. Посмотрите номера в инвентаре: i", "dim")
            return None
        return int(arg) - 1

    def drop(self, arg):
        if not self.inventory:
            say("Нечего выбрасывать.", "dim")
            return
        if not arg:
            item = self.inventory.drop_at(-1)  # pop() без номера — последний
        elif arg.isdigit():
            index = self.item_index(arg)
            if index is None:
                return
            item = self.inventory.drop_at(index)
        else:
            item = self.inventory.drop_named(arg)
            if item is None:
                say(f"В рюкзаке нет «{arg}».", "dim")
                return
        self.maze.rooms[self.pos].items.append(item)
        say(f"Выбросили «{item.name}». Он лежит здесь на полу.")

    def sort(self, arg):
        parts = arg.split()
        by = parts[0] if parts else "имя"
        if by not in Inventory.SORT_KEYS:
            say("Сортировать можно по: " + ", ".join(Inventory.SORT_KEYS), "dim")
            return
        self.inventory.sort(by, reverse="-" in parts)
        self.show_inventory()

    def use(self, arg):
        index = self.item_index(arg)
        if index is None:
            return
        item = self.inventory.items[index]
        if item.kind == POTION:
            self.inventory.drop_at(index)
            healed = min(item.power, self.max_hp - self.hp)
            self.hp += healed
            say(f"Выпили «{item.name}»: +{healed} hp.", "good")
        elif item.name == WHETSTONE:
            weapon = self.inventory.best_weapon()
            if weapon is None:
                say("Точить нечего: оружия нет.", "dim")
                return
            self.inventory.items.remove(item)
            weapon.power += 2
            weapon.durability += 5
            say(f"Заточили «{weapon.name}»: урон {weapon.power}, прочность {weapon.durability}.", "good")
        elif item.kind == WEAPON:
            say("Оружие используется само: в бою берётся самое сильное.", "dim")
        elif item.kind == KEY:
            say("Этот ключ открывает дверь E.", "dim")
        elif item.name == PHOENIX:
            say("Перо сработает само, если hp упадёт до нуля.", "dim")
        else:
            say(f"«{item.name}» ни на что не годится. Разве что продать.", "dim")

    def find(self, arg):
        name = arg or GOLDEN_KEY
        matches = [item.name for item in self.inventory if item.name.lower().startswith(name.lower())]
        if not matches:
            say(f"«{name}» в рюкзаке нет.", "dim")
            return
        index = self.inventory.find(matches[0])
        say(f"«{matches[0]}» лежит под номером {index + 1}.", "good")

    def top(self, arg):
        n = int(arg) if arg.isdigit() else 3
        for item in self.inventory.top(n):
            print(f"  {item.value:>4} зол.  {item.name}")

    def copy_demo(self):
        if not self.inventory:
            say("Положите что-нибудь в рюкзак, чтобы было что копировать.", "dim")
            return
        deep = self.inventory.snapshot()  # новые объекты-предметы
        shallow = deep.copy()             # новый список, но предметы те же
        sliced = deep[:]                  # срез [:] — тоже поверхностная копия
        shallow.append(make_item("Кость"))
        shallow[0].name += " (изменён)"
        print("  Сделали глубокую копию рюкзака, потом её поверхностную копию.")
        print("  В поверхностную копию добавили кость и переименовали первый предмет.")
        print(f"  поверхностная копия: {len(shallow)} шт., первый: {shallow[0].name}")
        print(f"  глубокая копия:      {len(deep)} шт., первый: {deep[0].name}  <- имя тоже поменялось!")
        print(f"  срез [:]:            {len(sliced)} шт., первый: {sliced[0].name}")
        print(f"  настоящий рюкзак:    {len(self.inventory)} шт., первый: {self.inventory.items[0].name}  <- не тронут")
        print("  Вывод: list.copy() и [:] копируют только список, а предметы внутри общие.")

    # --- главный цикл
    def handle(self, line):
        command, _, arg = line.strip().partition(" ")
        command, arg = command.lower(), arg.strip()
        if command and all(ch in DIRECTIONS for ch in command):
            for ch in command:
                if self.move(*DIRECTIONS[ch]) or self.over:
                    break
            return
        actions = {
            "i": self.show_inventory, "g": self.show_grouped, "t": self.take,
            "copy": self.copy_demo, "rev": self.reverse,
            "h": lambda: print(HELP), "help": lambda: print(HELP),
        }
        with_arg = {"drop": self.drop, "sort": self.sort, "use": self.use,
                    "find": self.find, "top": self.top}
        if command in actions:
            actions[command]()
        elif command in with_arg:
            with_arg[command](arg)
        elif command in ("q", "quit", "exit"):
            self.over = True
        elif command:
            say("Не понял. Помощь: h", "dim")

    def reverse(self):
        self.inventory.items.reverse()
        self.show_inventory()

    def score(self):
        gold = sum(item.value for item in self.inventory)
        return gold + self.hp + self.kills * 10 + (200 if self.won else 0)

    def run(self):
        say(f"Лабиринт {self.maze.rows} x {self.maze.cols}. Найдите золотой ключ и выход E.", "title")
        print(HELP)
        while not self.over:
            print()
            self.draw()
            self.status()
            self.handle(ask("> "))
        print()
        self.draw()
        say(f"Ходов: {self.turns}, монстров побеждено: {self.kills}, очки: {self.score()}", "title")


def ask(prompt):
    try:
        return input(prompt)
    except EOFError:
        return "q"


def main():
    global USE_COLOR
    parser = argparse.ArgumentParser(description="Бродилка по лабиринту с инвентарём")
    parser.add_argument("rows", nargs="?", type=int, default=7, help="n: строк комнат")
    parser.add_argument("cols", nargs="?", type=int, default=10, help="m: столбцов комнат")
    parser.add_argument("--seed", type=int, help="зерно генератора, чтобы лабиринт повторялся")
    parser.add_argument("--no-color", action="store_true", help="без ANSI-цветов")
    args = parser.parse_args()
    if args.rows < 3 or args.cols < 3:
        parser.error("лабиринт должен быть хотя бы 3 x 3")

    USE_COLOR = not args.no_color and sys.stdout.isatty()
    if USE_COLOR and os.name == "nt":
        os.system("")  # включает ANSI-цвета в консоли Windows
    Game(args.rows, args.cols, args.seed).run()


if __name__ == "__main__":
    main()
