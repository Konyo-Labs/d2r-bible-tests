# -*- coding: utf-8 -*-
"""v3855 - A WORN ITEM OPENS THE VAULT'S EVIDENCE (Elad 2026-11-02).

The Characters tab is the in-game read of what each character has EQUIPPED, per character, synced as its worn (locked)
items - only that: no finds, no session stats (test_reads_name_who_found_it_where_its_needed guards those). Every worn
item, on the card's slot list and in the doll window's cells, carries the Vault's magnifier: the Vault's own chip
renderer (window._vaultEvidenceChip) opening the Vault's evidence panel (window._vaultEvidenceOpen) - the looks behind
WATCHED / PROVEN / HARDENED, the look count, last seen, the pictures opening full size; UNKNOWN / no picture when none.
Never a copy of the panel, and no price or pencil here. RED_PROOF below.
"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import test_a_shadow_shelf_says_playtime_and_plays_served_frames as BASE  # noqa: E402

BIBLE = os.path.join(HERE, "..", "bible.html")


def _src():
    return open(BIBLE, encoding="utf-8").read()


def _cut(src, start, end="\n  }\n"):
    i = src.index(start)
    return src[i:src.index(end, i) + len(end)]


def _ev(item, chip):
    js = ("const window = {}; " + ("window._vaultEvidenceChip = function(n, c){ return '<button class=\"' + c + '\" data-n=\"' + n + '\"></button>'; };" if chip else "")
          + _cut(_src(), "  function _chxEv(item){") + "\nprocess.stdout.write(JSON.stringify(_chxEv(%r)));" % item)
    r = subprocess.run([BASE.NODE or "node", "-"], input=js, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-600:])
    return r.stdout


class EveryWornItemHasTheMagnifier(unittest.TestCase):

    def test_it_is_the_vaults_own_chip(self):
        self.assertIn('class=\\"chx-ev\\" data-n=\\"Splendor\\"', _ev("Splendor", True))

    def test_no_vault_or_no_item_draws_nothing(self):
        self.assertEqual(_ev("Splendor", False), '""')
        self.assertEqual(_ev("", True), '""')

    def test_the_card_and_the_doll_both_draw_it(self):
        src = _src()
        self.assertIn("        + _chxEv(s.item) + '</span></li>';", src)
        self.assertIn("      var ev = _chxEv(s.item);", src)
        self.assertIn("    return window._mpDollHtml(function(worn, row){", src)

    def test_never_a_copy_of_the_panel(self):
        body = _cut(_src(), "  function _chxEv(item){")
        for w in ("_vaultEvidenceHtml", "_vaultEvidenceOf", "innerHTML", "$", "pencil", "price"):
            self.assertNotIn(w, body)


class TheProofsNameOnePlace(unittest.TestCase):

    def test_each_find_matches_once(self):
        for proof in RED_PROOF:
            src = open(os.path.join(HERE, "..", proof["file"]), encoding="utf-8").read()
            self.assertEqual(src.count(proof["find"]), proof["matches"], proof["why"])


RED_PROOF = [
    {"why": "the card's worn items have no magnifier",
     "file": "bible.html",
     "find": "        + _chxEv(s.item) + '</span></li>';",
     "replace": "        + '</span></li>';",
     "matches": 1},
    {"why": "the doll window's cells have no magnifier",
     "file": "bible.html",
     "find": "      var ev = _chxEv(s.item);",
     "replace": "      var ev = '';",
     "matches": 1},
    {"why": "the magnifier is not the Vault's chip",
     "file": "bible.html",
     "find": "    try { return window._vaultEvidenceChip(item, 'chx-ev'); } catch (e) { return ''; }\n",
     "replace": "    return '<button class=\"chx-ev\"></button>';\n",
     "matches": 1, "needs": "node"},
    {"why": "a missing Vault throws instead of drawing nothing",
     "file": "bible.html",
     "find": "    if (!item || typeof window._vaultEvidenceChip !== 'function') return '';\n",
     "replace": "    if (!item) return '';\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main()
