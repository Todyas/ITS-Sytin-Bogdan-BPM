"""Проверки: python -m unittest tests.py"""

import contextlib
import io
import random
import unittest

import ui
from game import Game
from items import BOMB, FLOOR_KEY, TORCH, Inventory, make_item
from world import EXIT, STAIRS, Floor

ui.use_color = False


class InventoryTest(unittest.TestCase):
    def test_add_respects_weight(self):
        inventory = Inventory(max_weight=5)
        taken, rest = inventory.add_many([make_item("Булыжник"), make_item("Булыжник")])
        self.assertEqual(len(taken), 1)
        self.assertEqual(len(rest), 1)
        self.assertFalse(inventory.add(make_item("Булыжник")))

    def test_sort_find_and_remove(self):
        inventory = Inventory()
        inventory.add_many([make_item("Кость"), make_item("Рубин"), make_item("Кинжал")])
        inventory.sort("цена", reverse=True)
        self.assertEqual(inventory.names()[0], "Рубин")
        self.assertEqual(inventory.find("Кинжал"), 1)
        self.assertIsNone(inventory.find("Корона"))
        self.assertEqual(inventory.take_named("кос").name, "Кость")
        self.assertNotIn("Кость", inventory)

    def test_craft_uses_exact_ingredients(self):
        inventory = Inventory()
        inventory.add_many([make_item("Булыжник"), make_item("Слизь"), make_item("Тряпка"), make_item("Кость")])
        result = inventory.craft(["Булыжник", "Слизь", "Тряпка"], BOMB)
        self.assertEqual(result.name, BOMB)
        self.assertEqual(sorted(inventory.names()), sorted([BOMB, "Кость"]))
        self.assertIsInstance(inventory.craft(["Палка", "Тряпка"], TORCH), str)


class WorldTest(unittest.TestCase):
    def test_floors_are_connected_and_have_goal(self):
        for seed in range(30):
            rng = random.Random(seed)
            floor = Floor(1, 2, 6, 9, rng)
            self.assertEqual(len(floor.maze.distances(floor.start)), len(floor.rooms))
            self.assertEqual(floor.rooms[floor.goal].kind, STAIRS)
            keys = [pos for pos, room in floor.maze if any(item.name == FLOOR_KEY for item in room.items)]
            self.assertEqual(len(keys), 1)

    def test_last_floor_has_boss_on_exit(self):
        floor = Floor(3, 3, 6, 9, random.Random(1))
        self.assertEqual(floor.rooms[floor.goal].kind, EXIT)
        self.assertTrue(floor.monster_at(floor.goal).boss)


class SmokeTest(unittest.TestCase):
    def test_random_games_do_not_crash(self):
        for seed in range(40):
            rng = random.Random(seed)
            ui.ask = lambda prompt: rng.choice(["f", "f", "r", "use 1", "y", "n"])
            game = Game(5, 6, 2, seed)
            commands = list("wasd") * 6 + ["t", "i", "g", "craft 1", "use 2", "equip 1", "drop",
                                           "sort вес", "rev", "top", "find", "bomb d", "buy 1", "sell 1"]
            with contextlib.redirect_stdout(io.StringIO()):
                for _ in range(400):
                    if game.over:
                        break
                    game.handle(rng.choice(commands))
                    self.assertLessEqual(game.inventory.weight(), game.inventory.max_weight)
                    self.assertTrue(game.weapon is None or game.weapon in game.inventory.items)


if __name__ == "__main__":
    unittest.main()
