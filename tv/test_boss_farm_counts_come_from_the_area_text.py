# -*- coding: utf-8 -*-
"""v3893 (REG-3562) - PER-BOSS FARM COUNTS COME FROM THE ALREADY-READ AREA TEXT.

The silospen set-mf table already pairs each boss with its lair
(Andariel -> Catacombs Level 4). A visit is counted once per game name
(via game_name_of_row); repeats of the same lair in the same game are one
visit. With no game name, a visit is counted when the area transitions into
that lair. A zone the table does not name is unknown (not counted).
RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import read_identity as RI  # noqa: E402


class BossFarmCountsComeFromTheAreaText(unittest.TestCase):

    def test_lairs_come_from_the_silospen_table(self):
        lairs = RI.farm_lairs()
        self.assertIn("Catacombs Level 4", lairs["Andariel"])
        self.assertIn("The Chaos Sanctuary", lairs["Diablo"])
        self.assertIn("Tal Rasha's Chamber", lairs["Duriel"])
        self.assertIn("The Worldstone Chamber", lairs["Baal"])

    def test_one_visit_per_game_and_a_return_without_a_game_name(self):
        two = RI.boss_farm_counts([
            {"gameName": "Morph1", "area": "Catacombs Level 4"},
            {"gameName": "Morph1", "area": "Catacombs Level 4"},
            {"gameName": "Morph2", "area": "Catacombs Level 4"},
        ])
        self.assertEqual(two.get("Andariel"), 2, two)
        back = RI.boss_farm_counts([
            {"area": "Catacombs Level 4"},
            {"area": "Rogue Encampment"},
            {"area": "Catacombs Level 4"},
        ])
        self.assertEqual(back.get("Andariel"), 2, back)
        self.assertEqual(RI.boss_farm_counts([{"area": "Rogue Encampment"}]), {})


RED_PROOF = [
    {"why": "v3893 (REG-3562) - a lair visit no longer increments the boss count",
     "file": "tv/read_identity.py",
     "find": "                    counts[boss] = counts.get(boss, 0) + 1\n",
     "replace": "                    counts[boss] = counts.get(boss, 0)\n",
     "matches": 2},
]


if __name__ == "__main__":
    unittest.main()
