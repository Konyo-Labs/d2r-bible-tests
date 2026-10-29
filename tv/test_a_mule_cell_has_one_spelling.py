# -*- coding: utf-8 -*-
"""REG-3062 (#144(a)'s sibling) - ONE MULE CELL, ONE SPELLING: "[Mule 2 · ]Personal stash · col 3 · row 1", FROM ONE HELPER.

After REG-3005 gave the shared stash one spelling, a mule's own cell was still spelled several ways:
  * the MOVE row "UNI-ARMOR (3,1)" / "UNI-ARMOR · Mule 2 (9,3)", its expand "UNI-ARMOR private stash (3,1)";
  * FIND, its move-target words and the organizer "Mule 2 · Personal stash · col 3 · row 1";
  * the mule window's list "STASH col 3 · row 1" / "GEMS col ..." / "INVENTORY col ...";
  * a refused hand spot "Personal · Mule 1 · col 6 · row 6", the item database door "Inventory · col 3 · row 1 · Mule 2"
    (the area before the mule page, or the page last);
  * the hand placement's task reason "you placed it at col 7 · row 6 by hand" (no area at all).
Now _muleSpotSay (beside _sharedSpotSay, in its shape: the locker's mule page when the caller names one, the area, col,
row) is the one spelling, and every surface asks it. Whether a surface names Mule 1 stays the caller's (FIND and the
organizer name it when the locker spans pages, the MOVE row from Mule 2 on). This law holds the helper's words and the
join: each surface's own line calls it, and the old spellings are gone. The surfaces themselves are driven in node by the
laws re-aimed at the same words (test_a_full_locker_spills_to_its_next_mule, test_the_mule_window_places_by_hand,
test_a_saved_target_never_moves_unless_he_moves_it), and on CI by the browser laws. RED_PROOF below.
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
HELPER = "  function _muleAreaSay(area, page){"
CALLS = {
    "FIND's move-target words": "return _muleSpotSay(ca.loc, ca.x, ca.y, ca.page);",
    "the organizer": "cells[q.n] = _muleSpotSay('personal', q.x, q.y, mp);",
    "FIND, a WAR mule's copy": "put(wm.name + ' · ' + _muleSpotSay('personal', p.x, p.y, mp));",
    "FIND's filed answer": "_put(_muleSpotSay('personal', p.x, p.y, mp));",
    "FIND's would answer": "_putW(_muleSpotSay('personal', p.x, p.y, mpW));",
    "the move list's cell words": "if (ca) return String(cell) + ' · ' + _muleSpotSay(ca.loc, ca.x, ca.y, ca.page > 0 ? ca.page : null);",
    "the MOVE row": "if (_ca) return h + ' · ' + _muleSpotSay(_ca.loc, _ca.x, _ca.y, _ca.page > 0 ? _ca.page : null);",
    "the MOVE row's expand": "return nm + ' · ' + _muleSpotSay(c.loc, c.x, c.y, c.mule > 0 ? c.mule : null); }",
    "a WAR mule's expand": "return nm + ' (SHARED STASH · overflow) · ' + _muleSpotSay(c.loc, c.x, c.y, c.mule > 0 ? c.mule : null);",
    "a refused hand spot": "var _sp = _muleSpotSay(p.tab, _int(x) ? x : 0, _int(y) ? y : 0, _int(pg) ? pg : 0);",
    "a refused database spot": "var _sp = _muleSpotSay('inv', (e && _mpWhole(e.x)) ? e.x : 0, (e && _mpWhole(e.y)) ? e.y : 0, _mpWhole(pg) ? pg : 0);",
    "the item database door": "where: _muleSpotSay('inv', at.x, at.y, _muleTotalPages > 1 ? at.page : null),",
    "the mule window's grid label": "label: _muleAreaSay(area, _muleTotalPages > 1 ? _mulePage : null),",
    "the mule window's list": "esc(_muleSpotSay('personal', p.x, p.y, _lp))",
    "the hand placement's spot": "function _mpSpotSay(s){ return _muleSpotSay(s.tab, s.x, s.y, s.page); }",
    "the hand placement's task reason": "'you placed it at ' + _muleSpotSay(spot.tab, x, y, pg > 0 ? pg : null) + ' by hand'",
}


def _src():
    with open(PAGE, encoding="utf-8") as fh:
        return fh.read()


def _code(src):
    src = re.sub(r"/\*.{0,4000}?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(^|[^:\\'\"])//[^\n]*", r"\1", src)


class AMuleCellHasOneSpelling(unittest.TestCase):

    @unittest.skipUnless(NODE, "node is absent on this machine - the helper's words are UNMEASURED here, never a pass")
    def test_the_helper_says_mule_area_col_row(self):
        s = _src()
        self.assertEqual(s.count(HELPER), 1, "the one helper is gone - re-point this law")
        i = s.index(HELPER)
        j = s.index("\n", s.index("function _muleSpotSay(", i))
        areas = ("var MULE_AREAS = { personal: [10, 10, 'Personal'], shared: [10, 10, 'Shared'], gems: [10, 10, 'Gems'],"
                 " materials: [10, 10, 'Materials'], runes: [10, 10, 'Runes'], inv: [10, 4, 'Inventory'] };\n")
        prog = areas + s[i:j] + "\nprocess.stdout.write(JSON.stringify([_muleSpotSay('stash', 2, 0, null), _muleSpotSay('inventory', 0, 3, 1)," \
            " _muleSpotSay('gems', 4, 5, 0), _muleAreaSay('inv', null), _muleSpotSay('personal', 6, 5, null)]));"
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        self.assertEqual(json.loads(r.stdout), ["Personal stash · col 3 · row 1", "Mule 2 · Inventory · col 1 · row 4",
                                                "Mule 1 · Gems stash · col 5 · row 6", "Inventory",
                                                "Personal stash · col 7 · row 6"])

    def test_every_surface_asks_the_one_helper(self):
        code = _code(_src())
        bad = ["%s: %d (%r)" % (what, code.count(call), call[:80]) for what, call in CALLS.items() if code.count(call) != 1]
        self.assertEqual(bad, [], "a surface no longer asks the helper (expected each call once): %r" % bad)

    def test_the_old_spellings_are_gone(self):
        code = _code(_src())
        for pat, what in ((r"vl-slot\">(?:STASH|INVENTORY) '\+slotName", "the mule window's 'STASH col 3 · row 1'"),
                          (r"toUpperCase\(\)\+' '\+slotName", "the mule window's 'GEMS col 3 · row 1'"),
                          (r"' · Mule ' \+ \(_ca\.page \+ 1\) \+ ' \('", "the MOVE row's 'Mule 2 (9,3)'"),
                          (r"\+ ' \(' \+ \(c\.x \+ 1\) \+ ','", "the expand's '(3,1)'"),
                          (r"tagW? \+ '(?:Personal stash|Inventory) · col '", "a second 'Personal stash · col' builder"),
                          (r"' stash' \) \+ ' · Mule ' \+", "the area-before-the-mule order")):
            self.assertIsNone(re.search(pat, code), "%s is back in the code" % what)


RED_PROOF = [
    {"why": "REG-3062 - the MOVE row spells a mule cell '(3,1)' again",
     "file": "bible.html",
     "find": "      if (_ca) return h + ' · ' + _muleSpotSay(_ca.loc, _ca.x, _ca.y, _ca.page > 0 ? _ca.page : null);",
     "replace": "      if (_ca) return h + ' (' + (_ca.x + 1) + ',' + (_ca.y + 1) + ')';",
     "matches": 1},
    {"why": "REG-3062 - the mule window's list says 'STASH col 3 · row 1' again",
     "file": "bible.html",
     "find": "' → <span class=\"vl-slot\">'+esc(_muleSpotSay('personal', p.x, p.y, _lp))+'</span>'",
     "replace": "' → <span class=\"vl-slot\">STASH '+slotName(p)+'</span>'",
     "matches": 1},
    {"why": "REG-3062 - the helper puts the area before the mule page again",
     "file": "bible.html",
     "find": "    return (page == null ? '' : 'Mule ' + ((+page || 0) + 1) + ' \\u00b7 ') + (A ? A[2] + (t === 'inv' ? '' : ' stash') : String(area));",
     "replace": "    return (A ? A[2] + (t === 'inv' ? '' : ' stash') : String(area)) + (page == null ? '' : ' \\u00b7 Mule ' + ((+page || 0) + 1));",
     "matches": 1, "needs": "node"},
    {"why": "REG-3062 - the expand spells a mule cell 'private stash (3,1)' again",
     "file": "bible.html",
     "find": "      return nm + ' · ' + _muleSpotSay(c.loc, c.x, c.y, c.mule > 0 ? c.mule : null); }",
     "replace": "      return nm + (c.mule > 0 ? ' · Mule ' + (c.mule + 1) : '') + ' ' + (_vaultMoveStashSay(place.location) || c.loc) + ' (' + (c.x + 1) + ',' + (c.y + 1) + ')'; }",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
