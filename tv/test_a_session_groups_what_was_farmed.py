# -*- coding: utf-8 -*-
"""v3850 (Elad 2026-11-01 02:55/03:05 IDT) - A SESSION CARD SAYS WHAT WAS FARMED, GROUPED AND COUNTED; NO POTIONS.

His words: "a more organized summary of the farmed items" and "should not be registered potions". A session card
listed every read word in one line (Greater Mana Potion, Key, Super Mana Potion beside a Large Axe). farmed_names.group
is the one rule: snapped names grouped as uniques / sets / runewords / runes / charms / jewels / rings & amulets / gems /
bases, each with a pickup count (consecutive reads of one item are one pickup). Potions, scrolls, tomes, keys, gold,
arrows and bolts are never registered. shadow_sessions.digest publishes it as `farmed`; the card draws it.

RED_PROOF below.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import farmed_names as F  # noqa: E402
import shadow_sessions as SS  # noqa: E402

RED_PROOF = [
    {"why": "v3850 - an uber key or organ is filed as nothing farmed",
     "file": "farmed_names.py",
     "find": "    if n in UBERS:\n        return \"ubers\"\n",
     "replace": "",
     "matches": 1},
    {"why": "v3850 - the card has no label for keys and organs, so their group never draws",
     "file": "control_ui.html",
     "find": " ubers: 'Keys & organs',",
     "replace": "",
     "matches": 1},
    {"why": "potions are registered as farmed items again",
     "file": "farmed_names.py",
     "find": "    return bool(group) and not _CONSUMABLE.search(name or \"\")\n",
     "replace": "    return True\n",
     "matches": 1},
    {"why": "one item read on consecutive frames counts as many pickups",
     "file": "farmed_names.py",
     "find": "            if hit not in prev:\n",
     "replace": "            if True:\n",
     "matches": 1},
    {"why": "the digest stops publishing the grouped summary",
     "file": "shadow_sessions.py",
     "find": '             "farmed": farmed,\n',
     "replace": '',
     "matches": 1},
    {"why": "the card stops drawing the groups",
     "file": "control_ui.html",
     "find": "      + (farmed ? '<div class=\"ssv-names ssv-farmed\">' + farmed + '</div>' : '<div class=\"ssv-names\">' + names + '</div>')\n",
     "replace": "      + '<div class=\"ssv-names\">' + names + '</div>'\n",
     "matches": 1},
]


class TheGroups(unittest.TestCase):
    def test_grouped_and_counted(self):
        g = F.group([["Harlequin Crest", "Ber Rune"], ["Ber Rune"], [], ["Ber Rune", "Grand Charm", "Large Axe"],
                     ["Jewel", "Grief", "Ring"]])
        self.assertEqual(g, {"uniques": [["Harlequin Crest", 1]], "runewords": [["Grief", 1]], "runes": [["Ber Rune", 2]],
                             "charms": [["Grand Charm", 1]], "jewels": [["Jewel", 1]], "jewelry": [["Ring", 1]],
                             "bases": [["Large Axe", 1]]})
        self.assertEqual(list(g), [k for k in F.GROUPS if k in g], "groups keep the card's order")

    def test_potions_and_pickup_noise_are_never_registered(self):
        noise = [["Greater Mana Potion", "Super Mana Potion", "GREATER HEALING P a TlaN", "Key", "Scroll of Town Portal",
                  "Full Rejuvenation Potion", "Tome of Identify", "Arrows", "Gold"]]
        self.assertEqual(F.group(noise), {})
        self.assertEqual(F.clean(noise[0]), [])


class TheCardDrawsIt(unittest.TestCase):
    def test_a_key_organ_or_essence_run_shows_what_it_farmed(self):
        # v3850 - a Countess/Summoner/Nihlathak key run, or an uber organ run, farmed nothing by the old consumable rule
        g = F.group([["Key of Terror"], ["Twisted Essence of Suffering", "Super Healing Potion"], ["Mephisto's Brain"]])
        self.assertEqual(sorted(n for n, _ in g.get("ubers", [])),
                         ["Key of Terror", "Mephisto's Brain", "Twisted Essence of Suffering"], g)
        self.assertNotIn("Super Healing Potion", str(g))
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as f:
            self.assertIn("ubers: 'Keys & organs'", f.read())

    def test_the_digest_publishes_it(self):
        rows = [{"t": 1792000000000 + i * 1000, "frameId": "f%d" % i, "names": n}
                for i, n in enumerate([["Shako", "Super Mana Potion"], ["Shako"], ["Ber Rune"]])]
        d = SS.digest(rows, "/nonexistent", lambda r: True, 1792000100000, make=lambda a, b: False)
        self.assertEqual(d["sessions"][0]["farmed"], {"runes": [["Ber Rune", 1]], "bases": [["Shako", 1]]})

    def test_the_card_draws_the_groups(self):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as f:
            ui = f.read()
        i = ui.index("  function _shadowSessionRow(s, ix){")
        body = ui[i:ui.index("\n  }\n", i)]
        self.assertIn("ssv-farmed", body)
        for g in F.GROUPS:
            self.assertIn(g + ":", body, "the card has no label for %s" % g)


if __name__ == "__main__":
    unittest.main(verbosity=2)
