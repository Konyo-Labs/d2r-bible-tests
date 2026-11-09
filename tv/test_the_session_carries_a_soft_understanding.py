# -*- coding: utf-8 -*-
"""v3893 (REG-3563) - A SESSION CARRIES A SOFT UNDERSTANDING ON TOP OF ITS SEALS.

games, focused runs, town/field from the already-read area, and per-boss farm
counts ride on the digest as `understanding`. Session splitting, say_games and
the existing character seal are unchanged. Unclear patterns stay unknown.
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


class TheSessionCarriesASoftUnderstanding(unittest.TestCase):

    def test_the_layer_joins_runs_town_and_bosses(self):
        rows = [
            {"gameName": "Morph1", "area": "Catacombs Level 4"},
            {"gameName": "Morph2", "area": "Catacombs Level 4"},
            {"gameName": "Morph3", "area": "Rogue Encampment"},
        ]
        got = RI.soft_understanding(rows)
        self.assertEqual(got["games"], ["Morph1", "Morph2", "Morph3"])
        self.assertEqual(got["gameCount"], 3)
        self.assertEqual(got["runs"], [{"kind": "focused", "stem": "Morph", "start": 1, "end": 3,
                                        "names": ["Morph1", "Morph2", "Morph3"]}])
        self.assertEqual(got["town"]["kind"], "town")
        self.assertEqual(got["town"]["act"], 1)
        self.assertEqual(got["bosses"].get("Andariel"), 2)

    def test_the_digest_carries_it_and_say_games_stays(self):
        with open(os.path.join(HERE, "shadow_sessions.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('s["understanding"] = soft_understanding(g)', src)
        self.assertIn('s["gamesSay"] = say_games(games) if games else None', src)
        self.assertIn('s["character"] = who_at(ident, s["t0"])', src)


RED_PROOF = [
    {"why": "v3893 (REG-3563) - the digest no longer carries the soft understanding",
     "file": "tv/shadow_sessions.py",
     "find": "        s[\"understanding\"] = soft_understanding(g)\n",
     "replace": "        s[\"understanding\"] = {}\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
