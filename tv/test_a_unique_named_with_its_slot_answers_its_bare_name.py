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


def _fn(src, head):
    """The whole `function head(...){...}` from the page, by brace matching (strings and regex literals in it hold no
    braces that matter: the matcher counts only code braces outside quotes)."""
    a = src.index(head)
    i = src.index("{", a)
    depth, q, k = 0, None, i
    while k < len(src):
        c = src[k]
        if q:
            if c == "\\":
                k += 2
                continue
            if c == q:
                q = None
        elif c in "'\"":
            q = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[a:k + 1]
        k += 1
    raise AssertionError("PREMISE: %s did not close" % head)


def _item_tip(src):
    a = src.index("const ITEM_TIP = ")
    b = src.index("\nwindow.ITEM_TIP", a)
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

    def test_the_floating_card_of_a_bare_name_carries_its_mods(self):
        """REG-3320 (#100) - THE HOVER PATH ITSELF. REG-3312 aliased ITEM_CODEX and its law read only that table; GrokBot
        hovered Gull on his window and the floating card had no mods, because the hover reads ITEM_TIP. Here the page's
        own resolver (_arttipResolveCatalogue + _slotCanonName) runs in node over the page's own ITEM_TIP and
        CODEX_SLOT_ALIASES; only the card painter is a stub that prints the mods it was handed."""
        if not NODE:
            self.skipTest("no node - the hover resolver is not driven here (UNMEASURED)")
        prog = ("var window = {};\n" + _item_tip(self.src) + ";\n"
                + re.search(r"var CODEX_SLOT_ALIASES = \[[^\]]*\];", self.src).group(0) + "\n"
                + "var SUNDER_TIP = {}, _SUN_BASES = {};\n"
                + "function _plannerBuiltTip(){ return null; }\n"
                + "function _itemTipHtml(t){ return 'MODS:' + JSON.stringify(t.l || []); }\n"
                + _fn(self.src, "function _slotCanonName(nm){") + "\n"
                + _fn(self.src, "function _arttipResolveCatalogue(nm){") + "\n"
                + "var out = {};\n"
                + "['Gull', 'Harlequin Crest', 'Crescent Moon'].forEach(function(n){ var r = _arttipResolveCatalogue(n);"
                + " out[n] = r ? { desc: String(r.desc || ''), art: String(r.artName || '') } : null; });\n"
                + "process.stdout.write(JSON.stringify(out));")
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        o = json.loads(r.stdout)
        self.assertIsNotNone(o["Gull"], "the hover resolver found nothing for Gull")
        self.assertIn("Better Chance of Getting Magic Items", o["Gull"]["desc"], "Gull's floating card carries no mods: %r" % o["Gull"])
        self.assertIn("To All Skills", (o["Harlequin Crest"] or {}).get("desc", ""), "the Shako's floating card carries no mods")
        self.assertNotIn("Getting Magic Items", json.dumps(o.get("Crescent Moon")), "a name no slot key holds took one")

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
    {"why": "REG-3320 - the hover resolver never maps the bare name: Gull's floating card has no mods again",
     "file": "bible.html",
     "find": "  nm = _slotCanonName(nm);   /* REG-3320 (#100) - the game prints \"Gull\"; the catalogue keys \"Gull (dagger)\" */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3312 - Gull's floating card carries no mods again (the codex answers only 'Gull (dagger)')",
     "file": "bible.html",
     "find": "var CODEX_SLOT_ALIASES = ['Gull (dagger)', 'Harlequin Crest (Shako)'];",
     "replace": "var CODEX_SLOT_ALIASES = ['Harlequin Crest (Shako)'];",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
