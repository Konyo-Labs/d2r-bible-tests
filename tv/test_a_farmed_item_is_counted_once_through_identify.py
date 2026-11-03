# -*- coding: utf-8 -*-
"""v3859 (#230): the session route's FARM and IDENTIFY paths (tv/session_route.py).

FARM: an unidentified item seen on the floor and then in the inventory is one farmed item, never two; a floor sighting
nobody picked up is only seen. IDENTIFY: the same item read identified (its name over its base) keeps the farmed count
where it was and takes its new name.

RED_PROOF below: each one, applied, turns this law red."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()


def R(t, scene, lines):
    return {"ts": t, "captureTs": t, "scene": scene, "raw_lines": lines, "names": lines}


FLOOR = R(1000, "ground", ["Shako", "Unidentified"])
INV = R(2000, "inventory", ["Shako", "Unidentified", "Defense: 120"])
INV2 = R(2500, "inventory", ["Shako", "Unidentified"])
IDENT = R(3000, "inventory", ["Harlequin Crest", "Shako", "Defense: 141"])
IDENT2 = R(3500, "inventory", ["Harlequin Crest", "Shako"])
FLOOR_ONLY = R(4000, "ground", ["Ber Rune"])


class TheFarmPath(unittest.TestCase):

    def test_floor_then_inventory_is_one_item(self):
        import session_route as sr
        r = sr.route([FLOOR, INV, INV2])
        print("farm: %s" % r)
        self.assertEqual(1, r["itemsFarmed"], "one Shako seen on the floor and then carried was counted %d times"
                         % r["itemsFarmed"])
        self.assertEqual({"bases": [["Shako", 1]]}, r["farmed"])

    def test_a_floor_sighting_nobody_picked_up_is_only_seen(self):
        import session_route as sr
        r = sr.route([FLOOR_ONLY])
        self.assertEqual(0, r["itemsFarmed"], "a rune left on the floor was called farmed")
        self.assertEqual(["Ber Rune"], r["seen"])


    def test_a_session_with_no_placed_read_is_unknown_never_zero(self):
        import session_route as sr
        r = sr.route([{"ts": 1, "names": ["Shako"]}, {"ts": 2, "scene": "chronicle", "names": ["Shako"]}])
        self.assertIsNone(r["itemsFarmed"], "an older journal with no scene was called 0 farmed")
        self.assertIsNone(r["farmed"])


class TheIdentifyPath(unittest.TestCase):

    def test_identify_never_changes_the_farmed_count(self):
        import session_route as sr
        r = sr.route([FLOOR, INV, IDENT, IDENT2])
        print("identify: %s" % r)
        self.assertEqual(1, r["itemsFarmed"], "identifying the Shako made it a second farmed item")
        self.assertEqual({"uniques": [["Harlequin Crest", 1]]}, r["farmed"],
                         "the identified item does not carry its new name")


RED_PROOF = [
    {"why": "a session nobody placed is called zero farmed",
     "file": "tv/session_route.py",
     "find": "    if not any(place(r) for r in rows or [] if isinstance(r, dict)):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "every inventory read becomes a new farmed item (floor then inventory counts twice)",
     "file": "tv/session_route.py",
     "find": "        for h in hits:\n            it = _find(items, h, (\"floor\", \"inventory\", \"other\"))\n",
     "replace": "        for h in hits:\n            it = None\n",
     "matches": 1},
    {"why": "a floor sighting is farmed without being picked up",
     "file": "tv/session_route.py",
     "find": "            if where == \"inventory\" and it.at in (\"floor\", \"inventory\"):\n",
     "replace": "            if it.at in (\"floor\", \"inventory\"):\n",
     "matches": 1},
    {"why": "the identify link is gone: the identified name is a second item",
     "file": "tv/session_route.py",
     "find": "                if it is not None and it.unid and named:\n",
     "replace": "                if False:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
