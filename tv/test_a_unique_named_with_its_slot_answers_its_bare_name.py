# -*- coding: utf-8 -*-
"""REG-3312 (his 11-06 report: "for GULL i saw that the image doesnt carry any mods ... the other items have mods already")
- A UNIQUE THE CODEX KEYS WITH ITS SLOT ANSWERS THE NAME THE GAME PRINTS.

ITEM_CODEX keys two unique items with a slot disambiguator - "Gull (dagger)" and "Harlequin Crest (Shako)" - while every
card (the floating hover card, the drop rows, the vault) looks an item up by the name the game prints: "Gull". The lookup
missed and Gull's card came up with no mods. The page now aliases those two by their bare names (beside the older
Bul-Kathos apostrophe alias).

Held here, driving the page's own codex and alias block in node:
  * Gull and Harlequin Crest answer their bare names, with their props;
  * "Crescent Moon" is NOT aliased - the codex holds only the amulet, and Crescent Moon is also a runeword, so the bare name
    would put the amulet's mods on the runeword's card;
  * the class is closed: every unique keyed "<name> (<slot>)" whose bare name is free and names no runeword is aliased.
RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NODE = shutil.which("node") or shutil.which("nodejs")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    import console_safe  # noqa: F401 - this law prints non-ASCII item names; a cp1255 console must not crash reporting
except Exception:
    pass


def _read():
    with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


def _codex_slice(src):
    a = src.index("var CODEX_SLOT_ALIASES = [")
    b = src.index("const ITEM_INFO = {", a)
    return src[a:b]


class AUniqueNamedWithItsSlotAnswersItsBareName(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _read()
        cls.slice = _codex_slice(cls.src)

    def test_gull_and_the_shako_answer_their_bare_names_with_their_mods(self):
        if not NODE:
            self.skipTest("no node - the page's codex is not driven here (UNMEASURED)")
        prog = ("var window = {};\n" + self.slice + "\nprocess.stdout.write(JSON.stringify({"
                "gull: ITEM_CODEX['Gull'] || null, shako: ITEM_CODEX['Harlequin Crest'] || null,"
                "moon: ITEM_CODEX['Crescent Moon'] || null }));")
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        o = json.loads(r.stdout)
        self.assertIsNotNone(o["gull"], "Gull's card still finds no codex entry - its mods stay blank")
        self.assertTrue(o["gull"].get("props") or o["gull"].get("stats"), "Gull answers, but carries no mods: %r" % o["gull"])
        self.assertEqual(o["gull"].get("base"), "Dagger")
        self.assertIsNotNone(o["shako"], "Harlequin Crest's card finds no codex entry")
        self.assertIsNone(o["moon"], "Crescent Moon was aliased to the amulet - the runeword's card would carry its mods")

    def test_every_unique_keyed_with_its_slot_is_aliased(self):
        st = self.src.index("const ITEM_CODEX = {")
        en = self.src.index("};\n", st)
        rows = re.findall(r'"([^"]+)":\{"rarity":"([^"]*)"', self.src[st:en])
        keys = set(k for k, _r in rows)
        runewords = set(re.findall(r'"([^"]+)":\{l:\[', self.src))
        self.assertGreater(len(runewords), 50, "PREMISE: the runeword table did not read")
        owed = []
        for k, rarity in rows:
            m = re.match(r"^(.*?)\s*\(([^)]*)\)$", k)
            if not m or rarity != "unique" or m.group(2).lower() in ("set piece", "any", "any piece", "set"):
                continue
            bare = m.group(1)
            if bare in keys or bare in runewords:
                continue
            owed.append(k)
        aliases = json.loads(re.search(r"var CODEX_SLOT_ALIASES = (\[[^\]]*\]);", self.src).group(1).replace("'", '"'))
        self.assertEqual(sorted(owed), sorted(aliases), "a unique keyed with its slot is not aliased (or one that should not be is)")


RED_PROOF = [
    {"why": "REG-3312 - Gull's floating card carries no mods again (the codex answers only 'Gull (dagger)')",
     "file": "bible.html",
     "find": "var CODEX_SLOT_ALIASES = ['Gull (dagger)', 'Harlequin Crest (Shako)'];",
     "replace": "var CODEX_SLOT_ALIASES = ['Harlequin Crest (Shako)'];",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
