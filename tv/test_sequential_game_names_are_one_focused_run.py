# -*- coding: utf-8 -*-
"""v3893 (REG-3560) - CONSECUTIVE NUMBERED GAME NAMES ARE ONE FOCUSED RUN.

Morph1 -> Morph2 -> Morph3 (read via game_name_of_row, in order) is one focused run.
A gap (Morph1 then Morph3), a name with no number, or a single numbered name is
unknown: we do not invent a run. say_games and game_runs are not rewritten.
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


class SequentialGameNamesAreOneFocusedRun(unittest.TestCase):

    def test_a_counting_series_is_one_focused_run(self):
        rows = [{"gameName": n} for n in ("Morph1", "Morph2", "Morph3")]
        self.assertEqual(RI.ordered_game_names(rows), ["Morph1", "Morph2", "Morph3"])
        got = RI.sequential_focused_runs(RI.ordered_game_names(rows))
        self.assertEqual(got, [{"kind": "focused", "stem": "Morph", "start": 1, "end": 3,
                                "names": ["Morph1", "Morph2", "Morph3"]}])

    def test_a_gap_or_a_lone_name_is_unknown(self):
        self.assertEqual(RI.sequential_focused_runs(["Morph1", "Morph3"]),
                         [{"kind": "unknown", "names": ["Morph1"]},
                          {"kind": "unknown", "names": ["Morph3"]}])
        self.assertEqual(RI.sequential_focused_runs(["Morph1"]),
                         [{"kind": "unknown", "names": ["Morph1"]}])
        self.assertEqual(RI.sequential_focused_runs(["Konyo", "Other"]),
                         [{"kind": "unknown", "names": ["Konyo"]},
                          {"kind": "unknown", "names": ["Other"]}])

    def test_say_games_still_counts_unique_names(self):
        # the old identity law pins Morph1, Morph2, Morph7 as "3 games" - this layer must not rewrite that
        self.assertEqual(RI.say_games(["Morph1", "Morph2", "Morph7"]), "Morph1-Morph7 (3 games)")
        with open(os.path.join(HERE, "read_identity.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("Does not rewrite say_games or game_runs.", src)


RED_PROOF = [
    {"why": "v3893 (REG-3560) - a counting series is no longer linked as one focused run",
     "file": "tv/read_identity.py",
     "find": "            and all(ns[i] + 1 == ns[i + 1] for i in range(len(ns) - 1))\n",
     "replace": "            and False\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
