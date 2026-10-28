# -*- coding: utf-8 -*-
"""REG-2861 - A FRAME THAT DID NOT READ ITS CONTAINER WHOLE NEVER COUNTS AN ITEM GONE.

The drain (_vaultGoneObserve, REG-2300) closes a throw-out or a move row after VAULT_GONE_SESSIONS sessions whose frames
showed its first-witnessed container WITHOUT the item. That is proof only when the frame's `items` is everything in the
container. Every read that reaches the board is one item - a stash look is a hover tooltip (#197: the read cell is the
hover point) - so a frame of a stash tab names the hovered item and nothing else. Wired to those reads as it stood, every
hover of a NEIGHBOUR would have counted a session in which each other row in that tab was "gone", and five sessions of
hovering would have closed them "gone 5/5" on the absence of a READ - against his ruling that a not-seen item is asked
about, never dropped on its own when in doubt.

So absence now counts only from a frame that says `complete: true` (a sweep that read the container whole). Any other
frame still does what its positive evidence proves: an item seen in its cell resets the count. No reader hands the door
a complete frame yet - the guided sweep is that producer - and this law does not pretend one exists.

Driven on the whole page in node (vault_page_node), on a fixture world. RED_PROOF below.
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

HEAD = "Arcanna's Head (helm)"     # an unruled set piece: the page makes it a THROW OUT row (REG-2300's own fixture)
NEIGHBOUR = ("Harlequin Crest", "c5r5")


def _prov(holder, loc, cell, n=2):
    return {"kind": "owned", "source": "tv", "seen": n,
            "looks": [{"session": "w%d" % i, "frame": "f%d" % i, "holder": holder, "loc": loc, "cell": cell} for i in range(n)]}


SEED = ("localStorage.setItem('d2r_ownerClaim', '*');"
        "localStorage.setItem('d2r_owned', %s);"
        "localStorage.setItem('d2r_muleAssign', '{}');"
        "localStorage.setItem('d2r_vaultProv', %s);" % (json.dumps(json.dumps([HEAD])),
                                                          json.dumps(json.dumps({HEAD: _prov("MAIN", "stash", "c0r0")}))))


def frame(session, items=(), complete=False):
    f = {"session": session, "holder": "MAIN", "location": "stash",
         "items": [{"name": n, "cell": c} for n, c in items], "ground": []}
    if complete:
        f["complete"] = True
    return json.dumps(f)


def _body():
    hover = "".join("OUT.say = W._vaultGoneObserve(%s).absence;" % frame("h%d" % i, items=[NEIGHBOUR]) for i in range(1, 6))
    whole2 = "".join("W._vaultGoneObserve(%s);" % frame("w%d" % i, complete=True) for i in (1, 2))
    seen = "OUT.seenSay = W._vaultGoneObserve(%s).absence;" % frame("b1", items=[(HEAD, "c0r0")])
    whole5 = "".join("W._vaultGoneObserve(%s);" % frame("v%d" % i, complete=True) for i in range(1, 6))
    return r"""
(function(){
var W = window, NAME = %(name)s;
function bag(){ var m = {}; try { (JSON.parse(localStorage.getItem('d2r_vaultRecords') || '{}').records || []).forEach(function(r){ if (r.move) m[r.name] = r.move; }); } catch (e) {} return m; }
W._vaultAutoIntakeSet && W._vaultAutoIntakeSet(false);
W._movePaintBusy = false; W._vaultMovePaint();
OUT.start = bag()[NAME] || null;
%(hover)s
OUT.afterHover = bag()[NAME] || null;
%(whole2)s
OUT.afterTwo = bag()[NAME] || null;
%(seen)s
OUT.afterSeen = bag()[NAME] || null;
%(whole5)s
OUT.afterFive = bag()[NAME] || null;
})();
""" % {"name": json.dumps(HEAD), "hover": hover, "whole2": whole2, "seen": seen, "whole5": whole5}


_RUNS = {}


def page():
    if "p" not in _RUNS:
        _RUNS["p"] = VPN.run(_body(), prelude=SEED, timeout=300)
    return _RUNS["p"]


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AHoverReadNeverCountsAnItemGone(unittest.TestCase):

    def test_the_premise_a_row_with_a_first_witnessed_cell(self):
        o = page()
        self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
        st = o["start"]
        self.assertIsNotNone(st, "PREMISE: no row was made for the sighted item")
        self.assertEqual(((st.get("from") or {}).get("cell"), st.get("status")), ("c0r0", "to-move"),
                         "PREMISE: the row does not start from its witnessed cell: %r" % st)

    def test_five_sessions_of_hovering_a_neighbour_count_nothing(self):
        o = page()
        a = o["afterHover"]
        self.assertEqual(a["status"], "to-move", "hovering a neighbour drained the row: %r" % a)
        self.assertFalse(a.get("gone"), "a hover read counted a session the item was gone: %r" % a)
        self.assertFalse(a.get("left"), "a hover read marked the item as having left its cell: %r" % a)
        self.assertIn("not counted", o["say"] or "", "the drain does not say why that absence counted nothing")

    def test_a_whole_read_without_it_still_counts(self):
        o = page()
        self.assertEqual(len(o["afterTwo"].get("gone") or []), 2, "two whole reads without the item counted %r" % o["afterTwo"])

    def test_seeing_it_in_its_cell_resets_the_count_from_any_read(self):
        o = page()
        b = o["afterSeen"]
        self.assertFalse(b.get("gone") or b.get("left"), "the item seen back in its cell did not reset the count: %r" % b)
        self.assertEqual(b["status"], "to-move")

    def test_five_whole_reads_without_it_close_the_row(self):
        o = page()
        f = o["afterFive"]
        self.assertEqual(f["status"], "closed", "five whole reads without the item did not drain it: %r" % f)
        self.assertRegex(f.get("closedBy") or "", r"^gone 5/5")


RED_PROOF = [
    {"why": "REG-2861 - every frame counts its absence again, so hovering a neighbour drains the row",
     "file": "bible.html",
     "find": "    var whole = frame.complete === true;   /* REG-2861 */\n",
     "replace": "    var whole = true;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2861 - the absence branch ignores whether the frame read its container whole",
     "file": "bible.html",
     "find": "        else if (whole) {   /* REG-2861 - a missing READ is not a missing item */\n",
     "replace": "        else {\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2861 - a whole read no longer counts, so nothing can ever drain",
     "file": "bible.html",
     "find": "    var whole = frame.complete === true;   /* REG-2861 */\n",
     "replace": "    var whole = false;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2861 - the drain stops saying why an absence counted nothing",
     "file": "bible.html",
     "find": ": 'not counted - the frame does not say it read its container whole (complete:true), and a missing read is not a missing item' };",
     "replace": ": '' };",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
