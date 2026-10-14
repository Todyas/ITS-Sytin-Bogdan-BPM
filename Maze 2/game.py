"""Сама игра: игрок, ходы, бой, торговля, крафт."""

import pickle
import random
from collections import Counter
from pathlib import Path

import ui
from ui import bar, paint, say
from items import (
    ANTIDOTE, ARMOR, BOMB, COIN, FIRE_SCROLL, FLOOR_KEY, KEY, MAP_SCROLL, PHOENIX,
    POTION, RAGE, RECIPES, TELEPORT_SCROLL, TORCH, WEAPON, WHETSTONE,
    Inventory, make_item, random_loot,
)
from world import (
    CHEST, EXIT, FOUNTAIN, MERCHANT, MIMIC, POISON_TRAP, PORTAL, STAIRS, STEPS, TRAP,
    EMPTY, Floor, Monster, floor_size,
)

SAVE_FILE = Path(__file__).with_name("save.pkl")

# русская раскладка тоже работает
KEYS = {"w": "w", "a": "a", "s": "s", "d": "d", "ц": "w", "ф": "a", "ы": "s", "в": "d"}

HELP = """
Ходьба: w a s d (или ц ф ы в), можно сразу несколько шагов: ddd
  i  инвентарь          g  по типам          t  взять с пола
  use N    использовать (зелье, свиток, факел, точило)
  equip N  взять в руки оружие / надеть броню
  drop N | drop имя | drop    выбросить        sort цена [-] | rev
  find [имя]  найти       top [N]  самые ценные
  craft       рецепты     craft N  скрафтить
  bomb w/a/s/d  взорвать стену рядом
  buy N / sell N  торговля (только у торговца &)
  save  сохраниться и выйти     h  помощь     q  сдаться
Карта: @ вы  $ сундук  & торговец  ≈ фонтан  O портал  K ключ  * вещи
       ^ ловушка  > лестница вниз  E выход  буквы — монстры (M — босс)
"""


class Game:
    def __init__(self, rows=6, cols=9, floors=3, seed=None):
        self.rng = random.Random(seed)
        self.base_rows, self.base_cols = rows, cols
        self.total_floors = floors
        self.depth = 0
        self.hp = self.max_hp = 100
        self.level, self.xp, self.gold = 1, 0, 0
        self.base_damage = 3
        self.inventory = Inventory()
        self.weapon = make_item("Кинжал")
        self.armor = None
        self.torch = make_item(TORCH)
        self.poison = 0
        self.rage = 0
        self.inventory.add_many([self.weapon, make_item("Малое зелье"), self.torch])
        self.stats = Counter()
        self.over = False
        self.won = False
        self.next_floor()

    # ------------------------------------------------------------ этажи и карта
    def next_floor(self):
        self.depth += 1
        rows, cols = floor_size(self.depth, self.base_rows, self.base_cols)
        self.floor = Floor(self.depth, self.total_floors, rows, cols, self.rng)
        self.pos = self.floor.start
        self.look()

    def light_radius(self):
        return 4 if self.torch else 2

    def visible(self):
        return set(self.floor.maze.distances(self.pos, limit=self.light_radius()))

    def look(self):
        self.floor.seen |= self.visible()

    def room_symbol(self, pos, lit):
        if pos == self.pos:
            return paint("@", "player")
        monster = self.floor.monster_at(pos) if lit else None
        if monster:
            return paint(monster.symbol, "boss" if monster.boss else "monster")
        room = self.floor.rooms[pos]
        symbols = {
            CHEST: ("$", "chest"), MIMIC: ("$", "chest"), MERCHANT: ("&", "merchant"),
            PORTAL: ("O", "portal"), STAIRS: (">", "stairs"), EXIT: ("E", "exit"),
        }
        if room.kind in symbols:
            return paint(*symbols[room.kind])
        if room.kind == FOUNTAIN:
            return paint("≈", "dim" if room.used else "fountain")
        if any(item.name == FLOOR_KEY for item in room.items):
            return paint("K", "key")
        if room.items:
            return paint("*", "item")
        if room.kind in (TRAP, POISON_TRAP) and room.trap_found:
            return paint("^", "trap")
        return " "

    def draw(self):
        lit = self.visible()
        seen = self.floor.seen
        out = []
        for gr, row in enumerate(self.floor.maze.grid):
            line = []
            for gc, ch in enumerate(row):
                near = {((gr + dr - 1) // 2, (gc + dc - 1) // 2)
                        for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                        if (gr + dr) % 2 and (gc + dc) % 2}
                if not near & seen:
                    line.append("  ")
                elif ch == "#":
                    line.append(paint("██", "wall" if near & lit else "dim"))
                elif gr % 2 and gc % 2:
                    pos = (gr // 2, gc // 2)
                    line.append(self.room_symbol(pos, pos in lit) + " ")
                else:
                    line.append("  ")
            out.append("".join(line))
        print("\n".join(out))

    def status(self):
        effects = []
        if self.poison:
            effects.append(paint(f"отравлен ({self.poison})", "poison"))
        if self.rage:
            effects.append(paint(f"ярость ({self.rage})", "rage"))
        if self.torch:
            effects.append(f"факел {self.torch.durability}")
        key = paint("ключ", "key") if FLOOR_KEY in self.inventory else ""
        print(f"Этаж {self.depth}/{self.total_floors}  hp {bar(self.hp, self.max_hp, color='good' if self.hp > 30 else 'bad')} "
              f"{self.hp}/{self.max_hp}  ур. {self.level} ({self.xp}/{self.xp_needed()} xp)  "
              + paint(f"{self.gold} зол.", "gold") + f"  (x, y) = ({self.pos[1]}, {self.pos[0]})")
        print(f"  оружие: {self.weapon.name if self.weapon else 'кулаки'}  "
              f"броня: {self.armor.name if self.armor else 'нет'}  "
              f"рюкзак {self.inventory.weight()}/{self.inventory.max_weight}  "
              + "  ".join(effects + [key]))

    # ------------------------------------------------------------ ход игрока
    def handle(self, line):
        command, _, arg = line.strip().partition(" ")
        command, arg = command.lower(), arg.strip()
        if command and all(ch in KEYS for ch in command):
            for ch in command:
                if self.move(STEPS[KEYS[ch]]) or self.over:
                    break
            self.sync_equipment()
            return
        simple = {"i": self.show_inventory, "g": self.show_grouped, "t": self.take,
                  "rev": self.reverse, "h": lambda: print(HELP), "help": lambda: print(HELP)}
        with_arg = {"use": self.use, "equip": self.equip, "drop": self.drop, "sort": self.sort,
                    "find": self.find, "top": self.top, "craft": self.craft, "bomb": self.bomb,
                    "buy": self.buy, "sell": self.sell}
        if command in simple:
            simple[command]()
        elif command in with_arg:
            with_arg[command](arg)
        elif command == "save":
            self.save()
        elif command in ("q", "quit"):
            if ui.ask("Точно сдаться? (y/n) ").lower().startswith(("y", "д", "н")):
                self.over = True
        elif command:
            say("Не понял. Помощь: h", "dim")
        self.sync_equipment()

    def move(self, step):
        """Возвращает True, если серию шагов пора прервать."""
        target = (self.pos[0] + step[0], self.pos[1] + step[1])
        if target not in self.floor.rooms or not self.floor.maze.is_open(self.pos, target):
            say("Там стена.", "dim")
            return True
        room = self.floor.rooms[target]
        if room.kind == MIMIC:
            room.kind = EMPTY
            say("Сундук распахивает пасть, полную зубов. Это мимик!", "monster")
            mimic = Monster("Мимик", "m", 18 + 6 * self.depth, 5 + 2 * self.depth, 15 * self.depth,
                            loot=3, boss=True, pos=target)
            self.floor.monsters.append(mimic)
            self.fight(mimic, player_first=False, retreat=self.pos)
            return True
        monster = self.floor.monster_at(target)
        if monster:
            self.fight(monster, player_first=True, retreat=self.pos)
            return True
        came_from, self.pos = self.pos, target
        self.stats["шагов"] += 1
        event = self.enter_room(came_from)
        if not self.over:
            event = self.tick() or event
        self.look()
        return event

    def enter_room(self, came_from):
        room = self.floor.rooms[self.pos]
        event = True
        if room.kind == TRAP and not room.trap_found:
            room.trap_found = True
            damage = self.rng.randint(8, 14) + 2 * self.depth
            self.hurt(damage, f"Щёлк! Ловушка, -{damage} hp.")
            if self.inventory and self.rng.random() < 0.35:
                lost = self.inventory.pop(self.rng.randrange(len(self.inventory)))
                room.items.append(lost)
                say(f"Из рюкзака вывалился «{lost.name}».", "bad")
        elif room.kind == POISON_TRAP and not room.trap_found:
            room.trap_found = True
            self.poison = max(self.poison, 6)
            self.hurt(5, "Из стены брызнул яд! -5 hp, вы отравлены.")
        elif room.kind == CHEST:
            room.kind = EMPTY
            loot = random_loot(self.rng, self.rng.randint(2, 4), self.depth)
            say("Сундук! Внутри: " + ", ".join(item.name for item in loot), "chest")
            room.items.extend(self.pickup(loot))
            self.stats["сундуков"] += 1
        elif room.kind == PORTAL:
            self.pos = room.portal_to
            say(f"Портал швыряет вас в ({self.pos[1]}, {self.pos[0]}).", "portal")
            monster = self.floor.monster_at(self.pos)
            if monster:
                say(f"...прямо в лапы к существу «{monster.name}»!", "monster")
                self.fight(monster, player_first=False, retreat=None)
        elif room.kind == FOUNTAIN and not room.used:
            self.fountain(room)
        elif room.kind == MERCHANT:
            self.show_shop()
        elif room.kind == STAIRS:
            self.try_stairs()
        elif room.kind == EXIT:
            say("Свет! Вы выбрались из лабиринта!", "exit")
            self.won = self.over = True
        else:
            event = False
        here = self.floor.rooms[self.pos]
        if here.items and not self.over:
            say("На полу: " + ", ".join(item.name for item in here.items) + ". Взять: t", "item")
            event = True
        return event

    def try_stairs(self):
        index = self.inventory.find(FLOOR_KEY)
        if index is None:
            say("Решётка над лестницей заперта. Нужен ключ с этого этажа.", "stairs")
            return
        self.inventory.pop(index)
        say("Ключ подходит! Вы спускаетесь глубже...", "stairs")
        self.next_floor()
        say(f"Этаж {self.depth}. Здесь темнее и опаснее.", "title")
        if self.floor.is_last:
            say("Где-то в глубине ревёт Минотавр. Он стережёт выход.", "boss")

    def fountain(self, room):
        if not ui.ask("Тут фонтан с мутной водой. Выпить? (y/n) ").lower().startswith(("y", "д", "н")):
            return
        room.used = True
        roll = self.rng.choice(["heal", "max", "poison", "gold", "teleport"])
        if roll == "heal":
            self.hp = self.max_hp
            say("Вода живая! hp полностью восстановлено.", "good")
        elif roll == "max":
            self.max_hp += 10
            self.hp += 10
            say("Вы чувствуете себя крепче: +10 к максимуму hp.", "good")
        elif roll == "poison":
            self.poison = max(self.poison, 5)
            say("Фу, вода протухла. Вы отравились.", "poison")
        elif roll == "gold":
            self.gold += 30
            say("На дне блестят монеты: +30 золота.", "gold")
        else:
            self.random_teleport()
            say("Вода закрутилась воронкой и куда-то вас унесла!", "portal")

    def random_teleport(self):
        options = [pos for pos, room in self.floor.maze
                   if room.kind == EMPTY and not self.floor.monster_at(pos)]
        self.pos = self.rng.choice(options)
        self.look()

    # ------------------------------------------------------------ время идёт
    def tick(self):
        """Яд, факел и монстры. True, если что-то произошло."""
        event = False
        self.sync_equipment()
        if self.poison:
            self.poison -= 1
            self.hurt(2, "Яд жжёт: -2 hp.")
            event = True
        if self.torch:
            self.torch.durability -= 1
            if self.torch.durability <= 0:
                self.inventory.remove(self.torch)
                self.torch = None
                say("Факел догорел. Стало темно.", "dim")
                event = True
        if not self.over:
            event = self.move_monsters() or event
        return event

    def move_monsters(self):
        smell = self.floor.maze.distances(self.pos, limit=5)
        for monster in list(self.floor.monsters):
            if self.over:
                return True
            if monster.boss or monster not in self.floor.monsters:
                continue
            options = [p for p in self.floor.maze.neighbors(monster.pos)
                       if self.floor.rooms[p].kind not in (MERCHANT, MIMIC) and not self.floor.monster_at(p)]
            if monster.pos in smell:
                # учуял: идём в соседнюю комнату, которая ближе к игроку
                options = [p for p in options if smell.get(p, 99) < smell[monster.pos]]
            elif self.rng.random() > 0.3:
                continue
            if not options:
                continue
            target = self.rng.choice(options)
            if target == self.pos:
                say(f"{monster.name} выскакивает из темноты!", "monster")
                self.fight(monster, player_first=False, retreat=None)
                return True
            monster.pos = target
        return False

    # ------------------------------------------------------------ бой
    def fight(self, monster, player_first, retreat):
        self.sync_equipment()
        say(f"Бой! {monster.name}: hp {monster.hp}, урон ~{monster.damage}", "boss" if monster.boss else "monster")
        if not player_first:
            self.monster_attack(monster)
        while monster.hp > 0 and not self.over:
            print(f"  вы {bar(self.hp, self.max_hp, 8)} {self.hp}   "
                  f"{monster.name} {bar(monster.hp, monster.max_hp, 8, 'bad')} {monster.hp}")
            choice = ui.ask("  [f] бить  [use N] предмет  [r] бежать > ").lower()
            if choice in ("", "f", "а"):
                self.player_attack(monster)
            elif choice.startswith("use"):
                if not self.use(choice[3:].strip(), monster):
                    continue
            elif choice in ("r", "к"):
                if self.rng.random() < 0.6:
                    self.flee(retreat)
                    return
                say("  Сбежать не вышло!", "bad")
            elif choice == "i":
                self.show_inventory()
                continue
            else:
                say("  f — бить, use N — предмет, r — бежать, i — инвентарь", "dim")
                continue
            if monster.hp > 0:
                self.monster_attack(monster)
        if monster.hp <= 0:
            self.win_fight(monster)

    def player_attack(self, monster):
        damage = self.base_damage + (self.weapon.power if self.weapon else 0) + self.rng.randint(-1, 2)
        text = ""
        if self.rng.random() < 0.12:
            damage = damage * 3 // 2
            text = paint(" Крит!", "rage")
        if self.rage:
            damage *= 2
            self.rage -= 1
            text += paint(" (ярость)", "rage")
        monster.hp -= damage
        print(f"  Вы бьёте на {damage}.{text}")
        if self.weapon:
            self.weapon.durability -= 1
            if self.weapon.durability <= 0:
                say(f"  «{self.weapon.name}» ломается!", "bad")
                self.inventory.remove(self.weapon)
                self.weapon = None
                self.auto_equip()

    def monster_attack(self, monster):
        damage = max(1, monster.damage + self.rng.randint(-2, 2))
        if self.armor:
            damage = max(1, damage - self.armor.power)
            self.armor.durability -= 1
            if self.armor.durability <= 0:
                say(f"  «{self.armor.name}» разваливается!", "bad")
                self.inventory.remove(self.armor)
                self.armor = None
        if monster.lifesteal:
            monster.hp = min(monster.max_hp, monster.hp + damage // 2)
        self.hurt(damage, f"  {monster.name} бьёт на {damage}.")
        if monster.poison and not self.over and self.rng.random() < 0.35:
            self.poison = max(self.poison, 4)
            say("  Укус ядовитый, вы отравлены.", "poison")

    def flee(self, retreat):
        if retreat is None:
            options = [p for p in self.floor.maze.neighbors(self.pos) if not self.floor.monster_at(p)]
            retreat = self.rng.choice(options) if options else self.pos
        self.pos = retreat
        self.look()
        say("Вы удрали.", "dim")

    def win_fight(self, monster):
        self.floor.monsters.remove(monster)
        self.stats["убито"] += 1
        if monster.boss and monster.name == "Минотавр":
            self.stats["минотавр"] += 1
        loot = random_loot(self.rng, monster.loot, self.depth) + [make_item(name) for name in monster.drops]
        self.floor.rooms[monster.pos].items.extend(loot)
        say(f"Победа над существом «{monster.name}»! +{monster.xp} xp. Выпало: "
            + ", ".join(item.name for item in loot), "good")
        self.gain_xp(monster.xp)

    def xp_needed(self):
        return 15 * self.level

    def gain_xp(self, amount):
        self.xp += amount
        while self.xp >= self.xp_needed():
            self.xp -= self.xp_needed()
            self.level += 1
            self.max_hp += 15
            self.hp = min(self.max_hp, self.hp + 30)
            self.base_damage += 2
            say(f"Новый уровень: {self.level}! +15 к макс. hp, +2 к урону.", "title")

    def hurt(self, damage, message):
        self.hp -= damage
        say(message, "bad")
        if self.hp > 0:
            return
        if PHOENIX in self.inventory:
            self.inventory.take_named(PHOENIX)
            self.hp = self.max_hp // 2
            self.poison = 0
            say("Перо феникса вспыхивает, и вы восстаёте из пепла!", "key")
            return
        self.hp = 0
        self.over = True
        say("Вы пали в лабиринте...", "bad")

    # ------------------------------------------------------------ предметы
    def pickup(self, items):
        """Монеты сразу в кошелёк, остальное в рюкзак. Возвращает то, что не влезло."""
        coins = [item for item in items if item.name == COIN]
        if coins:
            self.gold += sum(item.value for item in coins)
            say(f"+{sum(item.value for item in coins)} золота", "gold")
        taken, rest = self.inventory.add_many([item for item in items if item.name != COIN])
        if taken:
            say("Взяли: " + ", ".join(item.name for item in taken), "good")
        if rest:
            say("Не влезло (рюкзак полон): " + ", ".join(item.name for item in rest), "bad")
        self.auto_equip()
        return rest

    def take(self):
        room = self.floor.rooms[self.pos]
        if not room.items:
            say("На полу ничего нет.", "dim")
            return
        room.items = self.pickup(room.items)

    def auto_equip(self):
        if self.weapon is None:
            self.weapon = self.inventory.best(WEAPON)
        if self.armor is None:
            self.armor = self.inventory.best(ARMOR)

    def sync_equipment(self):
        # если предмет пропал из рюкзака (продали, выбросили, скрафтили) — снимаем
        if self.weapon not in self.inventory.items:
            self.weapon = None
        if self.armor not in self.inventory.items:
            self.armor = None
        if self.torch not in self.inventory.items:
            self.torch = None

    def pick(self, arg):
        if not arg.isdigit() or not 1 <= int(arg) <= len(self.inventory):
            say("Укажите номер предмета из инвентаря (i).", "dim")
            return None
        return self.inventory[int(arg) - 1]

    def use(self, arg, monster=None):
        """True, если действие потратило ход."""
        item = self.pick(arg)
        if item is None:
            return False
        if item.kind == POTION:
            self.inventory.remove(item)
            if item.name == ANTIDOTE:
                self.poison = 0
                say("Яд больше не действует.", "good")
            elif item.name == RAGE:
                self.rage += item.power
                say(f"Глаза наливаются кровью: двойной урон на {item.power} удара.", "rage")
            else:
                healed = min(item.power, self.max_hp - self.hp)
                self.hp += healed
                say(f"+{healed} hp", "good")
            return True
        if item.name == FIRE_SCROLL:
            if monster is None:
                say("Огненный свиток пригодится в бою.", "dim")
                return False
            self.inventory.remove(item)
            monster.hp -= item.power
            say(f"  Огненный шар! {monster.name} получает {item.power}.", "rage")
            return True
        if item.name == MAP_SCROLL:
            self.inventory.remove(item)
            self.floor.seen = set(self.floor.rooms)
            say("Свиток рассыпается, а карта этажа отпечатывается у вас в голове.", "good")
            return True
        if item.name == TELEPORT_SCROLL:
            if monster is not None:
                say("Сосредоточиться на телепорте в бою не выйдет.", "dim")
                return False
            self.inventory.remove(item)
            self.random_teleport()
            say(f"Хлоп! Вы в ({self.pos[1]}, {self.pos[0]}).", "portal")
            return True
        if item.name == TORCH:
            if self.torch is item:
                say("Этот факел уже горит.", "dim")
                return False
            self.torch = item
            say("Факел зажжён: видно дальше.", "good")
            return True
        if item.name == WHETSTONE:
            if self.weapon is None:
                say("Точить нечего.", "dim")
                return False
            self.inventory.remove(item)
            self.weapon.power += 2
            self.weapon.durability += 5
            say(f"«{self.weapon.name}»: урон {self.weapon.power}, прочность {self.weapon.durability}.", "good")
            return True
        if item.kind in (WEAPON, ARMOR):
            return self.equip(arg)
        hints = {BOMB: "Бомба: bomb w/a/s/d рядом со стеной.",
                 PHOENIX: "Перо сработает само, если hp упадёт до нуля.",
                 FLOOR_KEY: "Ключ откроет лестницу вниз (>)."}
        say(hints.get(item.name, f"«{item.name}» можно продать или пустить на крафт (craft)."), "dim")
        return False

    def equip(self, arg):
        item = self.pick(arg)
        if item is None:
            return False
        if item.kind == WEAPON:
            self.weapon = item
        elif item.kind == ARMOR:
            self.armor = item
        else:
            say("Это нельзя надеть.", "dim")
            return False
        say(f"Теперь у вас: {item}", "good")
        return True

    def bomb(self, arg):
        if arg not in KEYS:
            say("Куда взрывать? bomb w / a / s / d", "dim")
            return
        if BOMB not in self.inventory:
            say("Бомб нет. Крафт: Булыжник + Слизь + Тряпка.", "dim")
            return
        dr, dc = STEPS[KEYS[arg]]
        target = (self.pos[0] + dr, self.pos[1] + dc)
        if target not in self.floor.rooms:
            say("Это внешняя стена, её не пробить.", "dim")
            return
        if self.floor.maze.is_open(self.pos, target):
            say("Там и так проход.", "dim")
            return
        self.inventory.take_named(BOMB)
        self.floor.maze.link(self.pos, target)
        self.stats["взрывов"] += 1
        say("БАБАХ! В стене зияет дыра.", "rage")
        monster = self.floor.monster_at(target)
        if monster:
            monster.hp -= 15
            say(f"{monster.name} задело взрывом: -15 hp.", "rage")
            if monster.hp <= 0:
                self.win_fight(monster)
        self.look()

    def craft(self, arg):
        if not arg:
            for number, (parts, result) in enumerate(RECIPES, start=1):
                ok = paint("можно", "good") if self.inventory.can_craft(parts) else paint("нет", "dim")
                print(f"  {number}. {result:<16} = {' + '.join(parts):<36} [{ok}]")
            print("  craft N — скрафтить рецепт N")
            return
        if not arg.isdigit() or not 1 <= int(arg) <= len(RECIPES):
            say("Нет такого рецепта. Список: craft", "dim")
            return
        parts, result = RECIPES[int(arg) - 1]
        item = self.inventory.craft(parts, result)
        if isinstance(item, str):
            say(f"Не получилось: {item}.", "dim")
            return
        self.stats["скрафчено"] += 1
        say(f"Скрафтили: {item}", "good")
        self.sync_equipment()
        self.auto_equip()

    # ------------------------------------------------------------ торговля
    def merchant(self):
        room = self.floor.rooms[self.pos]
        if room.kind != MERCHANT:
            say("Торговать можно только с торговцем (&).", "dim")
            return None
        return room

    @staticmethod
    def price(item):
        return max(5, item.value * 2)

    def show_shop(self):
        room = self.floor.rooms[self.pos]
        say("Торговец: «Заходи, путник! Тут не дерутся. Что берёшь?»", "merchant")
        for number, item in enumerate(room.stock, start=1):
            print(f"  {number}. {item}  — " + paint(f"{self.price(item)} зол.", "gold"))
        print("  buy N — купить,  sell N — продать (номер из инвентаря)")

    def buy(self, arg):
        room = self.merchant()
        if room is None:
            return
        if not arg.isdigit() or not 1 <= int(arg) <= len(room.stock):
            self.show_shop()
            return
        item = room.stock[int(arg) - 1]
        if self.gold < self.price(item):
            say("«Денег маловато, дружище.»", "merchant")
            return
        if not self.inventory.add(item):
            say("Не влезет в рюкзак.", "bad")
            return
        self.gold -= self.price(item)
        room.stock.pop(int(arg) - 1)
        say(f"Купили «{item.name}».", "good")
        self.auto_equip()

    def sell(self, arg):
        room = self.merchant()
        if room is None:
            return
        item = self.pick(arg)
        if item is None:
            return
        if item.kind == KEY:
            say("«Ключ оставь себе, он тебе нужнее.»", "merchant")
            return
        self.inventory.remove(item)
        room.stock.append(item)
        self.gold += item.value
        self.stats["продано"] += 1
        say(f"Продали «{item.name}» за {item.value} зол.", "gold")

    # ------------------------------------------------------------ инвентарь
    def show_inventory(self):
        if not self.inventory:
            say("Рюкзак пуст.", "dim")
            return
        for number, item in enumerate(self.inventory, start=1):
            mark = ""
            if item is self.weapon or item is self.armor:
                mark = paint(" [в руках]" if item is self.weapon else " [надето]", "good")
            elif item is self.torch:
                mark = paint(" [горит]", "rage")
            print(f"  {number:>2}. {item}{mark}")
        print(f"  вес {self.inventory.weight()}/{self.inventory.max_weight}, золото {self.gold}")

    def show_grouped(self):
        for kind, items in self.inventory.grouped():
            counts = Counter(item.name for item in items)
            print(f"  {kind}: " + ", ".join(f"{name} x{n}" if n > 1 else name for name, n in counts.items()))

    def drop(self, arg):
        if not self.inventory:
            say("Нечего выбрасывать.", "dim")
            return
        if not arg:
            item = self.inventory.pop()
        elif arg.isdigit():
            item = self.pick(arg)
            if item is None:
                return
            self.inventory.remove(item)
        else:
            item = self.inventory.take_named(arg)
            if item is None:
                say(f"В рюкзаке нет «{arg}».", "dim")
                return
        self.floor.rooms[self.pos].items.append(item)
        say(f"Выбросили «{item.name}».")

    def sort(self, arg):
        parts = arg.split()
        by = parts[0] if parts else "имя"
        if by not in Inventory.SORT_KEYS:
            say("Сортировать можно по: " + ", ".join(Inventory.SORT_KEYS), "dim")
            return
        self.inventory.sort(by, reverse="-" in parts)
        self.show_inventory()

    def reverse(self):
        self.inventory.items.reverse()
        self.show_inventory()

    def find(self, arg):
        item = self.inventory.first(arg or FLOOR_KEY)
        if item is None:
            say(f"«{arg or FLOOR_KEY}» в рюкзаке нет.", "dim")
            return
        say(f"«{item.name}» лежит под номером {self.inventory.find(item.name) + 1}.", "good")

    def top(self, arg):
        for item in self.inventory.top(int(arg) if arg.isdigit() else 3):
            print(f"  {item.value:>4} зол.  {item.name}")

    # ------------------------------------------------------------ итоги
    def score(self):
        loot = sum(item.value for item in self.inventory)
        return self.gold + loot + 10 * self.stats["убито"] + 50 * (self.depth - 1) + (500 if self.won else 0)

    def achievements(self):
        rules = [
            (self.won, "Свобода", "выбраться из лабиринта"),
            (self.stats["минотавр"] > 0, "Тесей", "победить Минотавра"),
            (self.stats["убито"] >= 15, "Мясник", "победить 15 монстров"),
            (self.won and self.stats["убито"] <= 3, "Тихоня", "выиграть, победив не больше 3 монстров"),
            (self.gold >= 300, "Богач", "накопить 300 золота"),
            (self.stats["скрафчено"] >= 3, "Алхимик", "скрафтить 3 вещи"),
            (self.stats["взрывов"] >= 3, "Подрывник", "взорвать 3 стены"),
            (self.level >= 5, "Ветеран", "дорасти до 5 уровня"),
        ]
        return [(name, why) for done, name, why in rules if done]

    def save(self):
        with open(SAVE_FILE, "wb") as file:
            pickle.dump(self, file)
        say(f"Игра сохранена в {SAVE_FILE.name}. Продолжить: python main.py --load", "good")
        self.over = True
        self.saved = True

    @staticmethod
    def load():
        with open(SAVE_FILE, "rb") as file:
            game = pickle.load(file)
        game.over = False
        game.saved = False
        return game

    def run(self):
        while not self.over:
            print()
            self.draw()
            self.status()
            self.handle(ui.ask("> "))
        if getattr(self, "saved", False):
            return
        SAVE_FILE.unlink(missing_ok=True)  # умер — сохранение сгорает, всё по-честному
        print()
        self.draw()
