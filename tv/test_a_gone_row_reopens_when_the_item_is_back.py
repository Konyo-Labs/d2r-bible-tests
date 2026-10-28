# -*- coding: utf-8 -*-
"""#153.8 (GrokBot's vault sweep) - A ROW CLOSED AS "GONE" REOPENS WHEN THE ITEM IS SEEN BACK IN ITS CELL.

The drain closes a move row after VAULT_GONE_SESSIONS sessions whose frames show its first-witnessed container without
the item ("gone 5/5 sessions"). A later frame that showed the item right back in that cell changed nothing: the row
stayed closed. That look is direct proof the close was wrong, so the row reopens with its count cleared. A row closed
another way (seen on the ground) stays closed.

Driven on the whole page in node through window._vaultGoneObserve, the same frames the drain reads.
RED_PROOF below.
"""
import json
import os
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

import vault_page_node as VPN  # noqa: E402

HEAD = "Arcanna's Head (helm)"


def _prov(holder, loc, cell, n=2):
    return {"kind": "owned", "source": "tv", "seen": n,
            "looks": [{"session": "w%d" % i, "frame": "f%d" % i, "holder": holder, "loc": loc, "cell": cell} for i in range(n)]}


SEED = ("localStorage.setItem('d2r_ownerClaim', '*');"
        "localStorage.setItem('d2r_owned', %s);"
        "localStorage.setItem('d2r_muleAssign', '{}');"
        "localStorage.setItem('d2r_vaultProv', %s);" % (json.dumps(json.dumps([HEAD])),
                                                          json.dumps(json.dumps({HEAD: _prov("MAIN", "stash", "c0r0")}))))


def frame(session, items=(), ground=()):
    # REG-2861 - a whole read of MAIN's stash: only a frame that read its container whole may count an item gone
    return json.dumps({"session": session, "holder": "MAIN", "location": "stash", "complete": True,
                       "items": [{"name": n, "cell": c} for n, c in items], "ground": list(ground)})


BODY = r"""
(function(){
var W = window, NAME = %(name)s;
function bag(){ var m = {}; try { (JSON.parse(localStorage.getItem('d2r_vaultRecords') || '{}').records || []).forEach(function(r){ if (r.move) m[r.name] = r.move; }); } catch (e) {} return m; }
W._vaultAutoIntakeSet && W._vaultAutoIntakeSet(false);
W._movePaintBusy = false; W._vaultMovePaint();
OUT.start = bag()[NAME] || null;
%(gone)s
OUT.closed = bag()[NAME] || null;
W._vaultGoneObserve(%(back)s);
OUT.back = bag()[NAME] || null;
%(gone2)s
W._vaultGoneObserve(%(ground)s);
OUT.ground = bag()[NAME] || null;
W._vaultGoneObserve(%(back2)s);
OUT.groundBack = bag()[NAME] || null;
})();
"""


def _body():
    gone = "".join("W._vaultGoneObserve(%s);" % frame("g%d" % i) for i in range(1, 6))
    gone2 = "W._vaultGoneObserve(%s);" % frame("h1")   # it left its cell once - then it is read on the ground
    return BODY % {"name": json.dumps(HEAD), "gone": gone, "back": frame("b1", items=[(HEAD, "c0r0")]),
                   "gone2": gone2, "ground": frame("k1", ground=[HEAD]), "back2": frame("b2", items=[(HEAD, "c0r0")])}


_RUNS = {}


def page():
    if "p" not in _RUNS:
        _RUNS["p"] = VPN.run(_body(), prelude=SEED, timeout=300)
    return _RUNS["p"]


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AGoneRowReopensWhenTheItemIsBack(unittest.TestCase):

    def test_the_premise_a_row_that_drains_to_gone(self):
        o = page()
        self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
        self.assertIsNotNone(o["start"], "PREMISE: no move row was made for the sighted item")
        self.assertEqual(o["closed"]["status"], "closed", "PREMISE: five sessions without it did not close the row: %r" % o["closed"])
        self.assertRegex(o["closed"].get("closedBy") or "", r"^gone 5/5")

    def test_seen_back_in_its_cell_it_reopens(self):
        o = page()
        self.assertEqual(o["back"]["status"], "to-move", "a GONE row stayed closed with the item back in its cell: %r" % o["back"])
        self.assertIsNone(o["back"].get("gone"), o["back"])
        self.assertIsNone(o["back"].get("closedBy"), o["back"])

    def test_a_row_closed_on_the_ground_stays_closed(self):
        o = page()
        self.assertEqual((o["ground"]["status"], o["ground"].get("closedBy")), ("closed", "seen on the ground"),
                         "PREMISE: the throw-out row was not closed on the ground: %r" % o["ground"])
        self.assertEqual(o["groundBack"]["status"], "closed", "a row closed ON THE GROUND reopened: %r" % o["groundBack"])


RED_PROOF = [
    {"why": "#153.8 - a GONE row stays closed with the item back in its cell again",
     "file": "bible.html",
     "find": "        if (/^gone \\d/.test(String(t.closedBy || '')) && shows(t.from) && here(name, t.from.cell)) {\n",
     "replace": "        if (false) {\n", "matches": 1, "needs": "node"},
    {"why": "#153.8 - any closed row reopens on a sighting, a ground close included",
     "file": "bible.html",
     "find": "        if (/^gone \\d/.test(String(t.closedBy || '')) && shows(t.from) && here(name, t.from.cell)) {\n",
     "replace": "        if (shows(t.from) && here(name, t.from.cell)) {\n", "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
