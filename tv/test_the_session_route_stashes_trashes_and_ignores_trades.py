# -*- coding: utf-8 -*-
"""v3859 (#230): the session route's STASH, TRASH and OTHER-ROUTE paths (tv/session_route.py).

STASH: only items this run farmed count as stashed - the rest of the stash was there before. TRASH: a farmed item put
back on the floor and never stashed is trashed and stays farmed. OTHER: a trade window, a vendor or the shared stash
never counts toward the session; an item that came from one is carried, never farmed.

RED_PROOF below: each one, applied, turns this law red."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()


def R(t, scene, lines, **kw):
    d = {"ts": t, "captureTs": t, "scene": scene, "raw_lines": lines, "names": lines}
    d.update(kw)
    return d


FARM = [R(1000, "ground", ["Shako", "Unidentified"]), R(2000, "inventory", ["Shako", "Unidentified"]),
        R(3000, "inventory", ["Harlequin Crest", "Shako"])]


class TheStashPath(unittest.TestCase):

    def test_only_this_runs_farmed_items_are_stashed(self):
        import session_route as sr
        rows = FARM + [R(4000, "stash", ["Harlequin Crest", "The Stone of Jordan"], stashTab="personal"),
                       R(4100, "stash", ["Ber Rune"], stashTab="runes")]
        r = sr.route(rows)
        print("stash: %s" % r)
        self.assertEqual({"uniques": [["Harlequin Crest", 1]]}, r["stashed"],
                         "an item already in the stash was called stashed on this run")
        self.assertEqual(1, r["itemsFarmed"], "stashing changed the farmed count")

    def test_the_stash_counts_against_the_original_unidentified_sighting(self):
        import session_route as sr
        rows = FARM[:2] + [R(4000, "stash", ["Shako", "Unidentified"], stashTab="personal")]
        r = sr.route(rows)
        self.assertEqual({"bases": [["Shako", 1]]}, r["stashed"], "the unidentified Shako put away was not stashed")


class TheTrashPath(unittest.TestCase):

    def test_a_farmed_item_dropped_again_is_trashed_and_still_farmed(self):
        import session_route as sr
        rows = [R(1000, "ground", ["Swirling Crystal"]), R(2000, "inventory", ["Swirling Crystal"]),
                R(3000, "ground", ["Swirling Crystal"])]
        r = sr.route(rows)
        print("trash: %s" % r)
        self.assertEqual(1, r["itemsFarmed"], "a trashed item stopped being farmed")
        self.assertEqual(["Swirling Crystal"], r["trashed"])
        self.assertEqual({}, r["stashed"], "a trashed item was called stashed")


class TheOtherRoutes(unittest.TestCase):

    def test_a_trade_window_and_the_shared_stash_never_count(self):
        import session_route as sr
        rows = [R(1000, "trade", ["The Stone of Jordan"]), R(2000, "inventory", ["The Stone of Jordan"]),
                R(3000, "stash", ["Ber Rune"], stashTab="shared 1"), R(3500, "inventory", ["Ber Rune"]),
                R(4000, "stash", ["The Stone of Jordan"], stashTab="personal")]
        r = sr.route(rows)
        print("other: %s" % r)
        self.assertEqual(0, r["itemsFarmed"], "a traded or shared-stash item was counted as farmed")
        self.assertEqual({}, r["stashed"], "an item that came by trade was counted as stashed this run")


RED_PROOF = [
    {"why": "anything read in the stash counts as stashed",
     "file": "tv/session_route.py",
     "find": "                if it is not None and it.farmed:\n                    it.at = \"stash\"\n",
     "replace": "                if it is None:\n                    it = _Item(h[0], h[1], None, unid, \"inventory\"); items.append(it); it.farmed = True\n                it.at = \"stash\"\n",
     "matches": 1},
    {"why": "a farmed item dropped again is not trashed",
     "file": "tv/session_route.py",
     "find": "                it.at = \"trash\"\n",
     "replace": "                pass\n",
     "matches": 1},
    {"why": "the shared stash is read as his own stash",
     "file": "tv/session_route.py",
     "find": "    if sc in OTHER_SCENES or tabn.startswith(\"shared\"):\n",
     "replace": "    if sc in OTHER_SCENES:\n",
     "matches": 1},
    {"why": "an item that came by trade is farmed when it reaches the inventory",
     "file": "tv/session_route.py",
     "find": "                    it.at = \"carried\"          # came from a trade or the shared stash: carried, never farmed\n                continue\n",
     "replace": "                    it.at = \"floor\"\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
