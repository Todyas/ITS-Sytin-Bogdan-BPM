"""Лабиринт, комнаты, монстры и генерация этажей."""

import itertools
from collections import deque
from dataclasses import dataclass, field, replace

from items import COIN, FLOOR_KEY, MATERIAL, TREASURE, make_item, random_loot

EMPTY = "пусто"
CHEST = "сундук"
MIMIC = "мимик"          # выглядит как сундук, но кусается
TRAP = "ловушка"
POISON_TRAP = "ядовитая ловушка"
PORTAL = "портал"
STAIRS = "лестница"
EXIT = "выход"
MERCHANT = "торговец"
FOUNTAIN = "фонтан"

STEPS = {"w": (-1, 0), "s": (1, 0), "a": (0, -1), "d": (0, 1)}


@dataclass(eq=False)
class Monster:
    name: str
    symbol: str
    hp: int
    damage: int
    xp: int
    loot: int = 1
    drops: tuple = ()        # что выпадает всегда
    poison: bool = False     # может отравить
    lifesteal: bool = False  # лечится, когда кусает
    boss: bool = False       # стоит на месте и не убегает
    pos: tuple = (0, 0)
    max_hp: int = 0

    def __post_init__(self):
        self.max_hp = self.max_hp or self.hp


# какие монстры живут на каком этаже
BESTIARY = {
    1: [Monster("Крыса", "r", 10, 3, 4, drops=("Кость",)),
        Monster("Паук", "s", 12, 4, 6, drops=("Тряпка",), poison=True),
        Monster("Гоблин", "g", 16, 5, 8, loot=2)],
    2: [Monster("Скелет", "k", 20, 6, 12, drops=("Кость", "Кость")),
        Monster("Слизень", "j", 22, 5, 12, drops=("Слизь",)),
        Monster("Призрак", "h", 20, 7, 15, loot=2)],
    3: [Monster("Огр", "o", 32, 9, 22, loot=3),
        Monster("Тролль", "t", 36, 8, 24, drops=("Гриб",), loot=2),
        Monster("Вампир", "v", 28, 9, 26, lifesteal=True, loot=2)],
}
BOSS = Monster("Минотавр", "M", 90, 12, 100, loot=4, drops=("Корона",), boss=True)


@dataclass
class Room:
    kind: str = EMPTY
    items: list = field(default_factory=list)
    portal_to: tuple = None
    trap_found: bool = False
    used: bool = False       # фонтан выпит, сундук открыт и т.п.
    stock: list = field(default_factory=list)  # товары торговца


class Maze:
    """rows x cols комнат. В сетке символов комната (r, c) лежит в (2r+1, 2c+1),
    между соседними комнатами — клетка, которая либо стена "#", либо проход " "."""

    def __init__(self, rows, cols, rng):
        self.rows, self.cols = rows, cols
        self.grid = [["#"] * (2 * cols + 1) for _ in range(2 * rows + 1)]
        self.rooms = {(r, c): Room() for r in range(rows) for c in range(cols)}
        self._carve(rng)
        self._add_loops(rng)

    def __iter__(self):
        return iter(self.rooms.items())

    def around(self, pos):
        r, c = pos
        for dr, dc in STEPS.values():
            if 0 <= r + dr < self.rows and 0 <= c + dc < self.cols:
                yield r + dr, c + dc

    def neighbors(self, pos):
        return (other for other in self.around(pos) if self.is_open(pos, other))

    @staticmethod
    def wall_between(a, b):
        return a[0] + b[0] + 1, a[1] + b[1] + 1

    def is_open(self, a, b):
        r, c = self.wall_between(a, b)
        return self.grid[r][c] == " "

    def link(self, a, b):
        for r, c in (self.wall_between(a, b), (2 * a[0] + 1, 2 * a[1] + 1), (2 * b[0] + 1, 2 * b[1] + 1)):
            self.grid[r][c] = " "

    def _carve(self, rng):
        stack = [(0, 0)]
        visited = {(0, 0)}
        while stack:
            current = stack[-1]
            fresh = [p for p in self.around(current) if p not in visited]
            if not fresh:
                stack.pop()
                continue
            nxt = rng.choice(fresh)
            self.link(current, nxt)
            visited.add(nxt)
            stack.append(nxt)

    def _add_loops(self, rng):
        for pos in self.rooms:
            for other in self.around(pos):
                if rng.random() < 0.05:
                    self.link(pos, other)

    def distances(self, start, limit=None):
        """BFS: сколько шагов от start до каждой комнаты (не дальше limit)."""
        dist = {start: 0}
        queue = deque([start])
        while queue:
            pos = queue.popleft()
            if limit is not None and dist[pos] >= limit:
                continue
            for other in self.neighbors(pos):
                if other not in dist:
                    dist[other] = dist[pos] + 1
                    queue.append(other)
        return dist


class Floor:
    def __init__(self, depth, total, rows, cols, rng):
        self.depth = depth
        self.is_last = depth == total
        self.maze = Maze(rows, cols, rng)
        self.rooms = self.maze.rooms
        self.monsters = []
        self.seen = set()
        self.start = (0, 0)
        self._populate(rng)

    def monster_at(self, pos):
        return next((m for m in self.monsters if m.pos == pos), None)

    def _populate(self, rng):
        dist = self.maze.distances(self.start)
        by_distance = sorted(dist, key=dist.get)
        self.goal = by_distance[-1]
        goal_room = self.rooms[self.goal]
        if self.is_last:
            goal_room.kind = EXIT
            self.monsters.append(replace(BOSS, pos=self.goal))
            key_pos = None
        else:
            goal_room.kind = STAIRS
            key_pos = rng.choice(by_distance[len(by_distance) // 2:-1])
            self.rooms[key_pos].items.append(make_item(FLOOR_KEY))

        free = [pos for pos in self.rooms if pos not in (self.start, self.goal, key_pos)]
        rng.shuffle(free)
        area = len(self.rooms)

        pairs = max(1, area // 40)
        portal_cells = free[:pairs * 2]
        for a, b in zip(portal_cells[::2], portal_cells[1::2]):
            self.rooms[a].kind = self.rooms[b].kind = PORTAL
            self.rooms[a].portal_to, self.rooms[b].portal_to = b, a

        cells = iter(free[pairs * 2:])
        plan = [(MERCHANT, 1), (FOUNTAIN, max(1, area // 45)), (CHEST, area // 10),
                (MIMIC, max(1, area // 60)), (TRAP, area // 12), (POISON_TRAP, area // 20)]
        for kind, count in plan:
            for pos in itertools.islice(cells, count):
                self.rooms[pos].kind = kind
                if kind == MERCHANT:
                    goods = random_loot(rng, 20, self.depth + 1)
                    self.rooms[pos].stock = [item for item in goods if item.kind not in (TREASURE, MATERIAL)][:5]

        kinds = BESTIARY[min(self.depth, max(BESTIARY))]
        near_start = {pos for pos, d in dist.items() if d <= 2}
        for pos in itertools.islice(cells, area // 9):
            if pos in near_start:
                continue
            self.monsters.append(replace(rng.choice(kinds), pos=pos))

        for pos in itertools.islice(cells, area // 10):
            self.rooms[pos].items.extend(random_loot(rng, 1, self.depth))
        # пара монет просто валяется на полу
        for pos in itertools.islice(cells, area // 15):
            self.rooms[pos].items.append(make_item(COIN))


def floor_size(depth, rows, cols):
    """Каждый следующий этаж побольше."""
    return rows + depth - 1, cols + 2 * (depth - 1)
