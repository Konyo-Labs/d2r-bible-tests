# -*- coding: utf-8 -*-
"""REG-2024 - A RARE'S ROLLED NAME GOES TO MAGIC & RARE, NEVER TO A SLOT DRAWER BY ONE WORD. #269, GrokBot ticks 411/412.

GrokBot on his v3616 board: Dread Grasp in UNI-ARMOR and Storm Scarab in UNI-WEAPONS, each tipped "Base item · TV-vaulted
· Not a grail item". MEASURED on the shipped page: Dread Grasp -> uni-armor ("armor slot — base: name match"); Storm
Scarab, Death Loop, Viper Eye, Bitter Spiral, Doom Spiral -> uni-weap ("nothing on the board recognises this name"). They
are rares - one RarePrefix word + one RareSuffix word (RARE_NAME_PREFIXES / RARE_NAME_POOLS, the board's own v332 tables) -
and rolled-name keepers live in MAGIC & RARE. The rule asks only when NO catalogue knows the name, so a real item (Raven
Frost: "Raven" is a rare prefix too) keeps its own route, and a white base keeps its throw-out advice.
⚠ The catalogue check has NO live subject today: measured over ITEM_REGISTRY + ITEMS, the one catalogued name in the rare
shape is Rune Master, and the router files it by its base (BASE_DB) before this rule. A sabotage of the check cannot go red,
so it is not declared as a red-proof - it stays as a guard for a future catalogue name, said here rather than counted.
NO CHROME AT ALL = a declared skip, never a pass.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import test_a_sweep_never_reticks_what_he_unticked as H  # noqa: E402  (its Board drives the shipped page)

_B = {}
ROLLED = ("Dread Grasp", "Storm Scarab", "Death Loop", "Viper Eye", "Bitter Spiral", "Doom Spiral")
MAGIC = ("Ruby Jewel of Fervor", "Cobalt Jewel of Fervor")
# REG-2895 (his ruling 2026-10-28) - a charm is no rolled-name keeper of MAGIC & RARE any more: it has its own rule
CHARMS = {"Chaotic Grand Charm of Greed": "charms", "Grand Charm of Inertia": "shared", "Steel Grand Charm of Balance": "shared",
          "Fine Grand Charm of Life": "shared", "Small Charm of Vita": "shared"}
# REG-2054 - the stub branch's LIVE subject (measured 2026-11-03 over every rare suffix and magic base, branch defeated):
# a magic ring / amulet whose stub base is its grammar base falls to the curated slot route (UNI-SMALL, "jewelry/charm -
# base: Ring") without it; the rares and "Shimmering Jewel of Fervor" are caught by the grammar further down either way
STUBBED = ("Grim Loop", "Skull Scarab", "Blood Spiral", "Shimmering Jewel of Fervor", "Cobalt Ring of Fervor",
           "Cobalt Amulet of Fervor")


def board():
    if "b" not in _B:
        _B["b"] = H.Board().open()
    return _B["b"]


def tearDownModule():
    b = _B.pop("b", None)
    if b is not None:
        b.close()


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class ARolledRareNameGoesToMagicAndRare(unittest.TestCase):

    def test_the_rolled_names_go_to_magic_and_rare_and_real_items_keep_their_route(self):
        o = board().run("OUT.r = {}; %s.forEach(function(n){ var s = window.suggestMule(n); OUT.r[n] = s ? s.id : null; });"
                        % repr(list(ROLLED) + list(MAGIC) + list(CHARMS) + ["Raven Frost", "Heavy Belt", "Nokozan Relic"]).replace("'", '"'))["r"]
        for n in ROLLED:
            self.assertEqual(o[n], "magic-rare", "%s - a rare's rolled name - was filed into %r by one word" % (n, o[n]))
        for n in MAGIC:   # REG-2054 (#269, tick 416 K05) - a magic jewel is a rolled-name keeper too
            self.assertEqual(o[n], "magic-rare", "%s - a magic jewel - was filed into %r" % (n, o[n]))
        for n, home in CHARMS.items():   # REG-2895 - the charm rule's home, never MAGIC & RARE
            self.assertEqual(o[n], home, "%s - a charm - was filed into %r, not %r" % (n, o[n], home))
        self.assertEqual(o["Raven Frost"], "shared", "a real item that shares a rare prefix lost its own route")
        self.assertEqual(o["Heavy Belt"], "__throwout", "a white base lost its throw-out advice")
        self.assertEqual(o["Nokozan Relic"], "uni-small", "the control: a catalogued unique amulet moved")


    def test_a_name_tv_already_registered_routes_the_same(self):
        # REG-2054 (GrokBot tick 419 K10) - HIS board, not a fresh one: every one of these was registered by TV first, as a
        # stub whose base is its own name. The rule asked `!base`, the stub answered with the name, and nothing moved.
        # ⚠ ITS OWN NAMES: the board is shared, and a stub left behind on a fresh-board name would answer the other case
        # through this path - heart2 measured that (the fresh case stayed green with its own branch defeated).
        # REG-2895 - the charms that taught this case have their own rule now; the stub is minted as the TV writer
        # mints it (a magic name's base is the grammar's: "Jewel"), so a magic jewel's stub still needs this branch
        names = list(STUBBED)
        o = board().run("OUT.r = {}; %s.forEach(function(n){ var rq = window._rolledQuality(n); "
                        "window._tvExtraRemember(n, { rarity: rq ? rq.q : 'basic', base: (rq && rq.base) ? rq.base : n, "
                        "cat: 'TV-vaulted', val: 'tv' }); var s = window.suggestMule(n); OUT.r[n] = s ? s.id : null; });"
                        % repr(names).replace("'", '"'))["r"]
        for n in names:
            self.assertEqual(o[n], "magic-rare", "%s - registered by TV as a stub - was filed into %r" % (n, o[n]))


RED_PROOF = [
    {"why": "REG-2054 - a TV stub answers through the curated-EXTRA branch again (a magic grand charm -> UNI-SMALL)",
     "file": "bible.html",
     "find": "      if (ex && ex.val === 'tv' && !((_itip0 && _itip0.b) || (tip && tip.base)) && typeof _rolledQuality === 'function'){\n",
     "replace": "      if (false){\n",
     "matches": 1},
    # the router's own rare door, not the hand-pool grammar: since v3849 the CB_DB tables (_intakeRoute) type the same
    # names when the pool is defeated, so a tamper of the pool alone stayed green (measured 2026-11-03)
    {"why": "REG-2024 - a rare's rolled name is filed into a slot drawer by one word again",
     "file": "bible.html",
     "find": "      if (_rq && _rq.q === 'rare' && muleById('magic-rare')) return _rolledRoute(_rq);\n",
     "replace": "      if (false) return _rolledRoute(_rq);\n",
     "matches": 1},
    {"why": "REG-2054 - a magic jewel falls past the rolled-name grammar again",
     "file": "bible.html",
     "find": "      if (_rq && _rq.q === 'magic' && muleById('magic-rare'))\n",
     "replace": "      if (false)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
