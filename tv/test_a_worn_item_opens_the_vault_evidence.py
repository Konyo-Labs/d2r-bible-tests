# -*- coding: utf-8 -*-
"""v3855 - A WORN ITEM OPENS THE VAULT'S EVIDENCE (Elad 2026-11-02).

The Characters tab is the in-game read of what each character has EQUIPPED, per character, synced as its worn (locked)
items - only that: no finds, no session stats (test_reads_name_who_found_it_where_its_needed guards those). Every worn
item, on the card's slot list and in the doll window's cells, carries the Vault's magnifier: the Vault's own chip
renderer (window._vaultEvidenceChip) opening the Vault's evidence panel (window._vaultEvidenceOpen) - the looks behind
WATCHED / PROVEN / HARDENED, the look count, last seen, the pictures opening full size; UNKNOWN / no picture when none.
Never a copy of the panel, and no price or pencil here. RED_PROOF below.
"""
import json
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


STUBS = ("var _SLOT_WORD = {'off-hand': 'Off-hand'}, _TIER_FACE = {WATCHED: '👁 WATCHED'}, _CHX_WORD = {WATCHED: 'Not confirmed yet'};"
         " function _looks(n){ return n + (n === 1 ? ' look' : ' looks'); }"
         " function _chxJs(s){ return String(s).replace(/'/g, \"\\\\'\"); }\n")
CHIP = ("window._vaultEvidenceChip = function(n, c){ return '<button class=\"' + c + '\" data-n=\"' + n + '\"'"
        " + ' onclick=\"event.stopPropagation();window._vaultEvidenceOpen(\\'' + n + '\\')\"></button>'; };")


def _chx_fns():
    src = _src()
    i = src.index("  function _chxEv(item, t, s){")
    j = src.index("  window._chxWornOf = function(key)", i)
    return src[i:src.index("\n", j) + 1]


def _ev(item, chip, t=None, s=None, tail=""):
    js = ("const window = {}; " + (CHIP if chip else "") + STUBS + _chx_fns()
          + "\nconst out = _chxEv(%s, %s, %s);%s\nprocess.stdout.write(JSON.stringify(out));" % (json.dumps(item), json.dumps(t), json.dumps(s), tail))
    r = subprocess.run([BASE.NODE or "node", "-"], input=js, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-600:])
    return r.stdout


class EveryWornItemHasTheMagnifier(unittest.TestCase):

    def test_it_is_the_vaults_own_chip(self):
        self.assertIn('class=\\"chx-ev\\" data-n=\\"Splendor\\"', _ev("Splendor", True))

    def test_a_worn_item_opens_with_its_own_looks(self):
        t = {"key": "seen:konyorush", "name": "KonyoRush"}
        s = {"slot": "off-hand", "item": "Splendor", "tier": "WATCHED", "sightings": 2, "ts": 5,
             "reel": "s_9", "frames": ["f_1", "f_2"]}
        out = json.loads(_ev("Splendor", True, t, s, " out2 = JSON.stringify(window._chxWornOf('seen:konyorush|off-hand'));"
                                                        " process.stdout.write(JSON.stringify([out, JSON.parse(out2)])); process.exit(0);"))
        chip, worn = out
        self.assertIn("window._vaultEvidenceOpen('Splendor',window._chxWornOf(", chip)
        self.assertEqual([k["frame"] for k in worn["looks"]], ["f_2", "f_1"], "newest look first")
        self.assertEqual(worn["looks"][0]["session"], "s_9")
        self.assertEqual(worn["tierSay"], "Not confirmed yet · 2 looks")
        self.assertEqual(worn["lastTs"], 5)

    def test_the_gear_ledger_hands_its_frames(self):
        import equipped_ledger as EL
        d = {"characters": {"KonyoRush": {"slots": {"off-hand": {"item": "Splendor", "sightings": 2, "frames": ["f_1", "f_2"],
                                                                  "ts": 5, "reel": "s_9"}}}}}
        g = EL.gear_by_key(d, lambda n: n.lower(), {"proven": 10, "hardened": 20})
        row = [r for r in g["konyorush"]["slots"] if r["slot"] == "off-hand"][0]
        self.assertEqual(row["frames"], ["f_1", "f_2"])

    def test_the_panel_reads_the_worn_looks_first(self):
        src = _src()
        fn = _cut(src, "  window._vaultEvidenceWithWorn = function(m, worn){", "\n  };\n")
        js = ("const window = {}; function _evWhen(v){ return 'at ' + v; }\n" + fn
              + "\nconst a = window._vaultEvidenceWithWorn({has: false, unknown: true, looks: [], who: null, when: null, tierSay: null},"
                " {who: 'seen worn by KonyoRush (Off-hand)', tierSay: 'WATCHED · 2 looks', lastTs: 5, looks: [{frame: 'f_2', session: 's_9'}]});"
                "\nconst b = window._vaultEvidenceWithWorn({has: false, unknown: true, looks: []}, {looks: []});"
                "\nprocess.stdout.write(JSON.stringify([a, b]));")
        r = subprocess.run([BASE.NODE or "node", "-"], input=js, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        a, b = json.loads(r.stdout)
        self.assertEqual((a["has"], a["unknown"], a["who"], a["tierSay"], a["when"], a["session"], a["tallySay"]),
                         (True, False, "seen worn by KonyoRush (Off-hand)", "WATCHED · 2 looks", "at 5", "s_9", "1 look"))
        self.assertFalse(b["has"], "no worn look made a record out of nothing")
        self.assertIn("    if (worn) m = window._vaultEvidenceWithWorn(m, worn);", src)

    def test_no_vault_or_no_item_draws_nothing(self):
        self.assertEqual(_ev("Splendor", False), '""')
        self.assertEqual(_ev("", True), '""')

    def test_the_card_and_the_doll_both_draw_it(self):
        src = _src()
        self.assertIn("        + _chxEv(s.item, t, s) + '</span></li>';", src)
        self.assertIn("      var ev = _chxEv(s.item, _chxT, s);", src)
        self.assertIn("    return window._mpDollHtml(function(worn, row){", src)

    def test_never_a_copy_of_the_panel(self):
        body = _cut(_src(), "  function _chxEv(item, t, s){")
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
     "find": "        + _chxEv(s.item, t, s) + '</span></li>';",
     "replace": "        + '</span></li>';",
     "matches": 1},
    {"why": "the doll window's cells have no magnifier",
     "file": "bible.html",
     "find": "      var ev = _chxEv(s.item, _chxT, s);",
     "replace": "      var ev = '';",
     "matches": 1},
    {"why": "the magnifier is not the Vault's chip",
     "file": "bible.html",
     "find": "    try { chip = window._vaultEvidenceChip(item, 'chx-ev'); } catch (e) { return ''; }\n",
     "replace": "    chip = '<button class=chx-ev></button>';\n",
     "matches": 1, "needs": "node"},
    {"why": "a missing Vault throws instead of drawing nothing",
     "file": "bible.html",
     "find": "    if (!item || typeof window._vaultEvidenceChip !== 'function') return '';\n",
     "replace": "    if (!item) return '';\n",
     "matches": 1, "needs": "node"},
    {"why": "the gear ledger hides the frames behind a worn item's tier",
     "file": "tv/equipped_ledger.py",
     "find": "                         \"frames\": [str(f) for f in ((cur or {}).get(\"frames\") or []) if f][-_FRAMES_KEPT:]})",
     "replace": "                         \"frames\": []})",
     "matches": 1},
    {"why": "the panel opens without the worn item's own looks",
     "file": "bible.html",
     "find": "    if (worn) m = window._vaultEvidenceWithWorn(m, worn);",
     "replace": "    if (false) m = window._vaultEvidenceWithWorn(m, worn);",
     "matches": 1},
    {"why": "a worn look with no frame is drawn as a picture",
     "file": "bible.html",
     "find": "    var wl = (worn && Array.isArray(worn.looks)) ? worn.looks.filter(function(k){ return k && k.frame; }) : [];\n",
     "replace": "    var wl = (worn && Array.isArray(worn.looks)) ? worn.looks.concat([{}]) : [];\n",
     "matches": 1, "needs": "node"},
    {"why": "the chip opens the Vault's record only, not the worn item's looks",
     "file": "bible.html",
     "find": "    if (!t || !s) return chip;\n",
     "replace": "    return chip;\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main()
