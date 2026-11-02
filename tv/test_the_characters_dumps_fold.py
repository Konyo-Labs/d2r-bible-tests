# -*- coding: utf-8 -*-
"""v3855 - THE CHARACTERS TAB'S DIAGNOSTIC DUMPS FOLD (Elad pt1210u, 2026-11-02: "this data/informational area...
organized and properly structured and hidden/collapsed with an option to see it if clicked").

Below the in-game cards, "Named on the lobby or the character panel" and the lobby-size counts were one run-on
paragraph and a long bullet list. Each is now a <details>, CLOSED by default, with one plain summary line
("Character names read · 14 characters · 120 frames", "Lobby size checks · 40 sizes · 2 matched"). Names: one row per
character (name · class · level · lobby / c-panel · frame count), its frame files only when that row opens. Lobby: a
compact table, most-checked first; the sizes nobody has looked at are one line. Open / closed is remembered per browser.
test_the_lobby_names_the_character keeps the REG-1760/1874 words. RED_PROOF below.
"""
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import test_the_lobby_names_the_character as LOBBY  # noqa: E402

BIBLE = os.path.join(HERE, "..", "bible.html")
UNSEEN = "nobody has looked at this size, so whether the bands see the lobby here is UNKNOWN"


def _paint(call, learned, remembered=False):
    page = open(BIBLE, encoding="utf-8").read()
    fns = "\n".join(LOBBY._js_fn(page, sig) for sig in ("function _dumpOpen(key)", "function _dumpWrap(key, sub, summary, body)",
                                                          "function _surfaceWitnessHtml()", "function _lobbySizeHtml()"))
    drv = ("function esc(s){ return String(s == null ? '' : s); }\n"
           "var window = { _cbLearnedNow: function(){ return LEARNED; }, _chxDumpOpen: function(){ return %s; } };\n"
           "var LEARNED = %s;\n%s\nprocess.stdout.write(%s());\n") % ("true" if remembered else "false", json.dumps(learned), fns, call)
    r = subprocess.run([LOBBY.NODE or "node", "-"], input=drv, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-500:])
    return r.stdout


W = [{"name": "Konyolock", "cls": "Warlock", "level": 94, "kind": "lobby", "image": "f_1.jpg", "confluence": 1.0},
     {"name": "Konyolock", "cls": "Warlock", "level": 94, "kind": "c-panel", "image": "f_2.jpg", "confluence": 1.0},
     {"name": "Armor", "cls": "Barbarian", "level": 1, "kind": "lobby", "image": "f_3.jpg"}]
SIZES = [{"size": "800x450", "checked": 4, "matched": 1},
         {"size": "1440x1326", "checked": 14, "matched": 0, "seen": UNSEEN},
         {"size": "1024x600", "checked": 7, "matched": 0, "seen": UNSEEN},
         {"size": "800x400", "checked": 9733, "matched": 0, "seen": "no game is drawn at this size"}]


class TheNamesFold(unittest.TestCase):

    def test_closed_with_one_summary_line(self):
        h = _paint("_surfaceWitnessHtml", {"ok": True, "surfaceWitnesses": W})
        self.assertTrue(h.startswith('<details class="chx-sec-sub chx-dump" data-sub="surface-witnesses" data-dump="names" ontoggle='), h[:200])
        self.assertIn("<summary>Character names read · 2 characters · 3 frames</summary>", h)

    def test_one_row_per_character_frames_inside_it(self):
        h = _paint("_surfaceWitnessHtml", {"ok": True, "surfaceWitnesses": W})
        self.assertIn("<summary>Konyolock · Warlock · level 94 · lobby / c-panel · 2 frames</summary>", h)
        for row in re.findall(r'<details class="chx-wit"><summary>(.*?)</summary>', h):
            self.assertNotIn("f_", row, "a frame file sits on the row instead of inside it")

    def test_remembered_open(self):
        self.assertIn('data-dump="names" open ', _paint("_surfaceWitnessHtml", {"ok": True, "surfaceWitnesses": W}, True))


class TheLobbyChecksFold(unittest.TestCase):

    def test_a_sorted_table_and_one_unseen_line(self):
        h = _paint("_lobbySizeHtml", {"ok": True, "lobbyBySize": SIZES})
        self.assertIn("<summary>Lobby size checks · 4 sizes · 1 matched</summary>", h)
        self.assertNotIn(' open ', h)
        self.assertLess(h.index('<tr data-size="800x400">'), h.index('<tr data-size="800x450">'), "the table is not most-checked first")
        self.assertNotIn('<tr data-size="1440x1326">', h, "a size nobody looked at took its own row")
        self.assertEqual(h.count("nobody has looked"), 1, "the unseen sizes are not one line")
        self.assertIn('data-sizes-unseen="2"', h)
        self.assertIn("1440x1326 (checked 14)", h)


class TheProofsNameOnePlace(unittest.TestCase):

    def test_each_find_matches_once(self):
        for proof in RED_PROOF:
            src = open(os.path.join(HERE, "..", proof["file"]), encoding="utf-8").read()
            self.assertEqual(src.count(proof["find"]), proof["matches"], proof["why"])


RED_PROOF = [
    {"why": "the dumps are open by default",
     "file": "bible.html",
     "find": "    try { return (typeof window._chxDumpOpen === 'function' && window._chxDumpOpen(key)) ? ' open' : ''; } catch (e) { return ''; }\n",
     "replace": "    return ' open';\n",
     "matches": 1, "needs": "node"},
    {"why": "the open state is not remembered",
     "file": "bible.html",
     "find": "  window._chxDumpToggle = function(key, open){ try { window.localStorage.setItem('d2r_chxDump.' + key, open ? '1' : '0'); } catch (e) {} return !!open; };\n",
     "replace": "  window._chxDumpToggle = function(key, open){ return !!open; };\n",
     "matches": 1},
    {"why": "each frame is its own row again (no per-character grouping)",
     "file": "bible.html",
     "find": "      var k = String(w.name).toLowerCase() + '|' + (w.cls || '') + '|' + ((typeof w.level === 'number') ? (w.level | 0) : '');\n",
     "replace": "      var k = String(w.image);\n",
     "matches": 1, "needs": "node"},
    {"why": "the lobby table is not sorted most-checked first",
     "file": "bible.html",
     "find": "        .sort(function(a, b){ return (b.checked - a.checked) || (a.size < b.size ? -1 : 1); });\n",
     "replace": ";\n",
     "matches": 1, "needs": "node"},
    {"why": "each size nobody looked at takes its own row",
     "file": "bible.html",
     "find": "      var unseen = ok.filter(function(r){ return !(r.matched | 0) && typeof r.seen === 'string' && /^nobody has looked/.test(r.seen); });\n",
     "replace": "      var unseen = [];\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main()
