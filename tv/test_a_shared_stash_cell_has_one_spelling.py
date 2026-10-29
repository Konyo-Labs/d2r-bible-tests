# -*- coding: utf-8 -*-
"""REG-3005 (#144(a)) - ONE SHARED-STASH CELL, ONE SPELLING: "Page 1 · col 3 · row 1", FROM ONE HELPER, ON EVERY SURFACE.

The same fact was spelled four ways: the shared stash window's per-item list "→ PAGE 1 col 3 · row 1"; FIND, its
move-target words and the plan's cell map "Page 1 · col 3 · row 1"; the MOVE row and its expand "SHARED STASH page 1
(3,1)"; and the move list's cell words read a shared cell raw - a page-2 cell said "shared:c2r10 · col 3 · row 11", no
page and a row a 10-row page does not have. Now _sharedSpotSay (beside _vaultCellAt) is the one spelling, and every
surface that prints a shared stash page and cell asks it. This law holds the helper's words and the join: each surface's
own line calls it, and the old spellings are gone from the code. The surfaces themselves are driven on a page-2 copy in
node by test_the_shared_stash_draws_the_plans_pages (re-aimed at the same words). RED_PROOF below.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

PAGE = os.path.join(os.path.dirname(HERE), "bible.html")
NODE = shutil.which("node")
HELPER = "  function _sharedSpotSay(page, x, y){"
# each surface's own line, and the call it must make (REG-3005)
SURFACES = {
    "the shared stash window's list": ("var list = pg.map(function(p){ return '<div>' + esc(p.n) + ' → <span class=\"vl-slot\">'", "_sharedSpotSay(_sharedPage, p.x, p.y)"),
    "FIND's filed answer": ("layF.pages.forEach(function(pgF, pi){", "_put(_sharedSpotSay(pi, p.x, p.y))"),
    "FIND's would answer": ("layW.pages.forEach(function(pgW, pi){", "_putW(_sharedSpotSay(pi, p.x, p.y))"),
    "FIND's move-target words": ("if (ca.loc === 'shared') return ", "_sharedSpotSay(ca.page, ca.x, ca.y)"),
    "the plan's cell map": ("if (planned.indexOf(q.n) >= 0 && !cells[q.n]) cells[q.n] = _sharedSpotSay", "_sharedSpotSay(pi, q.x, q.y)"),
    "the move list's cell words": ("if (ca && ca.loc === 'shared') return String(cell)", "_sharedSpotSay(ca.page, ca.x, ca.y)"),
    "the MOVE row": ("return h + ' · ' + _sharedSpotSay(", "_sharedSpotSay(Math.floor((+m[2]) / 10), +m[1], (+m[2]) % 10)"),
    "the MOVE row's expand": ("if (c.page != null) return nm + ' · '", "_sharedSpotSay(c.page, c.x, c.y)"),
}


def _src():
    with open(PAGE, encoding="utf-8") as fh:
        return fh.read()


def _code(src):
    src = re.sub(r"/\*.{0,4000}?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(^|[^:\\'\"])//[^\n]*", r"\1", src)


class ASharedStashCellHasOneSpelling(unittest.TestCase):

    @unittest.skipUnless(NODE, "node is absent on this machine - the helper's words are UNMEASURED here, never a pass")
    def test_the_helper_says_page_col_row(self):
        s = _src()
        self.assertEqual(s.count(HELPER), 1, "the one helper is gone - re-point this law")
        i = s.index(HELPER)
        fn = s[i:s.index("\n", s.index("return", i))]
        prog = fn + "\nprocess.stdout.write(JSON.stringify([_sharedSpotSay(0, 2, 0), _sharedSpotSay(1, 0, 2), _sharedSpotSay(4, 9, 9)]));"
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        self.assertEqual(json.loads(r.stdout), ["Page 1 · col 3 · row 1", "Page 2 · col 1 · row 3",
                                                "Page 5 · col 10 · row 10"])

    def test_every_surface_asks_the_one_helper(self):
        code = _code(_src())
        bad = []
        for what, (anchor, call) in SURFACES.items():
            n = code.count(anchor)
            if n != 1:
                bad.append("%s: its line matched %d times (%r)" % (what, n, anchor[:60]))
                continue
            i = code.index(anchor)
            line = code[code.rfind("\n", 0, i):code.index("\n", i)]
            if call not in line:
                bad.append("%s does not ask the helper: %r" % (what, line.strip()[:160]))
        self.assertEqual(bad, [], "a surface spells a shared stash cell its own way: %r" % bad)

    def test_the_old_spellings_are_gone(self):
        code = _code(_src())
        for pat, what in ((r"vl-slot\">PAGE ' \+", "the window's 'PAGE 1 col 3 · row 1'"),
                          (r"' page ' \+ \(Math\.floor", "the MOVE row's 'page 1 (3,1)'"),
                          (r"'page ' \+ \(c\.page \+ 1\)", "the expand's 'page 1 (3,1)'"),
                          (r"'Page ' \+ \((?:pi|ca\.page) \+ 1\) \+ ' · ", "a second 'Page ...' builder")):
            self.assertIsNone(re.search(pat, code), "%s is back in the code" % what)


RED_PROOF = [
    {"why": "REG-3005 - the shared stash window's list spells its cell its own way again ('PAGE 1 col 3 · row 1')",
     "file": "bible.html",
     "find": "' → <span class=\"vl-slot\">' + esc(_sharedSpotSay(_sharedPage, p.x, p.y)) + '</span></div>'",
     "replace": "' → <span class=\"vl-slot\">PAGE ' + (_sharedPage + 1) + ' ' + slotName(p) + '</span></div>'",
     "matches": 1},
    {"why": "REG-3005 - the MOVE row says 'page 1 (3,1)' again",
     "file": "bible.html",
     "find": "        return h + ' · ' + _sharedSpotSay(Math.floor((+m[2]) / 10), +m[1], (+m[2]) % 10);",
     "replace": "        return h + ' page ' + (Math.floor((+m[2]) / 10) + 1) + ' (' + ((+m[1]) + 1) + ',' + ((+m[2]) % 10 + 1) + ')';",
     "matches": 1},
    {"why": "REG-3005 - the helper writes another spelling",
     "file": "bible.html",
     "find": "return 'Page ' + ((+page || 0) + 1) + ' \\u00b7 col ' + ((+x || 0) + 1) + ' \\u00b7 row ' + ((+y || 0) + 1); }",
     "replace": "return 'PAGE ' + ((+page || 0) + 1) + ' col ' + ((+x || 0) + 1) + ' \\u00b7 row ' + ((+y || 0) + 1); }",
     "matches": 1, "needs": "node"},
    {"why": "REG-3005 - the move list's cell words read a shared cell raw again (no page, row 11 of a 10-row page)",
     "file": "bible.html",
     "find": "    if (ca && ca.loc === 'shared') return String(cell) + ' · ' + _sharedSpotSay(ca.page, ca.x, ca.y);",
     "replace": "    if (false) return String(cell);",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
