# -*- coding: utf-8 -*-
"""REG-2020 - THE VAULT FINDER NAMES THE MULE AND THE CELL, THE SAME ANSWER THE MULE WINDOW DRAWS. #264, his ask 2026-10-07.

His words: "i need the auto assembler logically telling me and tasking me per say by image organizing the items where they
should be.. that way i also can just type it in the console and find the mule related". The finder (vaultFind, v236) said a
mule's name, or "unsorted · in the dock" for everything else - including a charm sitting in MAGIC & RARE and the armour his
MAIN was wearing. Now _vaultWhereIs asks the packer the mule window uses (_muleLoad with the doll's worn copies; _sharedPack
for the shared tabs), and the finder prints the mule AND the cell; a dock item says where it WOULD go; an item his MAIN wore
or carried when last seen says so; anything else says the router's own answer.

The corroboration: the finder's cell is compared with the line the MULE WINDOW itself prints ("Obedience -> STASH col x ·
row y") - two surfaces, one packer, and a disagreement is the defect. Driven on the SHIPPED page in a scratch Chrome.
NO CHROME AT ALL = a declared skip, never a pass.
"""
import json
import os
import re
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
import test_his_auto_sort_click_fills_the_mules as S  # noqa: E402  (its dock and seed: one fixture, not two)

_B = {}


def board():
    if "b" not in _B:
        _B["b"] = H.Board().open()
        S._B["b"] = _B["b"]          # S._seed() seeds through S.board(): the same page
    return _B["b"]


def tearDownModule():
    b = _B.pop("b", None)
    S._B.pop("b", None)
    if b is not None:
        b.close()


WHERE = "OUT.w = {}; %s.forEach(function(n){ OUT.w[n] = window._vaultWhereIs(n); });"
NAMES = ["Grief", "Obedience", "Nokozan Relic", "Enigma", "Isenhart's Case (armor)", "Harpoonist's Grand Charm"]


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class TheVaultFinderNamesTheMuleAndTheCell(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        board()
        S._seed()
        cls.before = board().run(WHERE % json.dumps(NAMES))["w"]
        o = board().run("window.vaultAutoSortByHand();" + (WHERE % json.dumps(NAMES))
                        + "window.openMuleCard('runewords');"
                        + "OUT.rwList = (document.querySelector('#vault-detail .vd-list') || document.getElementById('vault-detail') || {}).textContent || '';"
                        + "window.vaultCloseCard && window.vaultCloseCard();"
                        # #144.10 shared half (REG-2801): the shared stash is its 5 pages - open the one FIND names for Grief
                        + "window.openMuleCard('shared'); var _gp = /^Page (\\d) /.exec((window._vaultWhereIs('Grief') || {}).cell || '');"
                        + "window._sharedSetPage(_gp ? +_gp[1] - 1 : 0);"
                        + "OUT.shList = (document.getElementById('vault-detail') || {}).textContent || '';"
                        + "window.vaultCloseCard && window.vaultCloseCard();"
                        + "window.vaultFind('grief'); OUT.find = (document.getElementById('vault-find-results') || {}).textContent || '';")
        cls.after, cls.rwList, cls.shList, cls.find = o["w"], o["rwList"], o["shList"], o["find"]

    def test_a_dock_item_says_where_it_would_go(self):
        w = self.before["Nokozan Relic"]
        self.assertEqual((w or {}).get("kind"), "would", "a loose amulet did not say where it would go: %r" % w)
        self.assertEqual(w.get("mule"), "uni-small", w)

    def test_a_filed_item_names_its_mule_and_a_cell(self):
        g, o = self.after["Grief"], self.after["Obedience"]
        self.assertEqual((g or {}).get("mule"), "shared", g)
        self.assertTrue(re.match(r"^Page [1-5] · col \d+ · row \d+$", g.get("cell") or ""), "Grief has no shared-page cell: %r" % g)
        self.assertEqual((o or {}).get("mule"), "runewords", o)
        self.assertTrue(re.search(r"Personal stash · col \d+ · row \d+$", o.get("cell") or ""), "Obedience has no stash cell: %r" % o)

    def test_the_finder_and_the_mule_window_agree_on_the_cell(self):
        o = self.after["Obedience"]
        m = re.search(r"col (\d+) · row (\d+)$", o.get("cell") or "")
        self.assertTrue(m, o)
        self.assertIn("Obedience → STASH col %s · row %s" % m.groups(), self.rwList,
                      "the finder and the mule window name different cells for the same item")
        g = re.search(r"^Page ([1-5]) · col (\d+) · row (\d+)$", self.after["Grief"].get("cell") or "")
        self.assertTrue(g, self.after["Grief"])
        self.assertIn("Grief → Page %s · col %s · row %s" % g.groups(), self.shList,   # REG-3005 the one spelling
                      "the finder and the shared stash window name different cells for Grief")

    def test_magic_and_rare_and_his_main_and_a_discard_each_say_their_own_answer(self):
        # REG-2992 - his 2026-10-28 charm ruling (REG-2895) homes a skiller grand charm on the CHARMS mule, and MAGIC & RARE holds
        # no charms: his magic find is FILED there, never loose. Both halves: REG-2020's proof leaves the mule "charms" and
        # flips only the kind to "would" (measured in node on the shipped page), so a mule-only check would be blind to it.
        h = self.after["Harpoonist's Grand Charm"]
        self.assertEqual(((h or {}).get("kind"), (h or {}).get("mule")), ("filed", "charms"),
                         "his magic-find charm read as loose, or off its charm-rule home, in the finder: %r" % h)
        e = self.after["Enigma"]
        self.assertEqual((e or {}).get("kind"), "main", "armour his MAIN wore when last seen was offered a mule: %r" % e)
        i = self.after["Isenhart's Case (armor)"]
        self.assertEqual((i or {}).get("kind"), "dock", i)
        self.assertTrue(i.get("why"), "a dock item said nothing about why it stays: %r" % i)

    def test_the_finder_prints_the_cell(self):
        self.assertIn("SHARED STASH", self.find, self.find)
        # REG-2789 - the shared stash is its 5 pages (his 2026-10-28 ruling, REG-2801), never the by-slot tabs
        self.assertRegex(self.find, r"SHARED STASH · Page [1-5] · col \d+ · row \d+",
                         "the finder still prints only a mule name, or the old by-slot tab: %r" % self.find)


RED_PROOF = [
    {"why": "REG-2020 - his magic-find charm reads as loose in the finder again (kind would, not filed on its CHARMS home)",
     "file": "bible.html",
     "find": "    try { return typeof magicFinds === 'object' && !!magicFinds && Object.prototype.hasOwnProperty.call(magicFinds, n); }\n",
     "replace": "    try { return false; }\n",
     "matches": 1},
    # REG-2376 - RE-AIMED at the branch this law reaches. v3767 homes an auto-sorted item through the records seam
    # and writes no `assign` (test_his_auto_sort_click_fills_the_mules asserts it), so after the hand auto-sort
    # _vaultWhereIs answers Grief and Obedience from its "would" branch, which packs the cell itself. Both proofs
    # deleted the FILED branch's cell lines, which no case here reaches: each stayed green, BLIND on his census.
    {"why": "REG-2020 - the finder names no shared-tab cell",
     "file": "bible.html",
     "find": "          layW.pages.forEach(function(pgW, pi){ pgW.forEach(function(p){ if (p.n === nm) _putW(_sharedSpotSay(pi, p.x, p.y)); }); });   /* REG-3005 */\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2020 - the finder names no mule-stash cell",
     "file": "bible.html",
     "find": "            (mu.stash || []).forEach(function(p){ if (p.n === nm) _putW(tagW + 'Personal stash · col ' + (p.x + 1) + ' · row ' + (p.y + 1)); });\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2020 - armour his MAIN wears is offered a mule in the finder",
     "file": "bible.html",
     "find": "    if (mainLoc) return { kind: 'main', mule: null, muleName: null, cell: null, why: (mainLoc === 'equipped' ? 'worn' : 'carried in your ' + mainLoc) + ' by your MAIN when last seen' };\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2020 - the finder stops asking _vaultFindHome, so the row no longer names the mule and the cell",
     "file": "bible.html",
     "find": "      var w = (typeof _vaultFindHome === 'function') ? _vaultFindHome(n) : ((typeof window._vaultWhereIs === 'function') ? window._vaultWhereIs(n) : null);\n",
     "replace": "      var w = null;\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
