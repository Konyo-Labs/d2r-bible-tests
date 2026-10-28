# -*- coding: utf-8 -*-
"""REG-2886 (#137, his ruling 2026-10-28: "3 copies if it was witnessed in other areas and coordinates.. its logical yea i
do have three im pretty sure") - THE VAULT'S POPULATION LINE COUNTS COPIES FROM THE EVIDENCE.

MEASURED before (whole page in node): the line under the vault toolbar counted NAMES only. Three Stormshields read
"1 owned · 1 filed to mules", and a copy he added moved no number (GrokBot v3740: "header 224/222/2 -> 226/223/3, the 6
copy-N adds did not count").

Now the line says "1 owned · 3 copies" when the evidence holds three. The number is the records count the card, the window
and FIND already use (_vaultRecordsHeader: one record per copy). That count is the distinct cells he was seen in (v3767)
plus the copies his hand typed (REG-2786). It is never a re-read of one cell and never copies[] alone. When nothing shows a
second copy the line stays "1 owned", with no guessed number. Whole page in node; the looks are fixtures in the shape the
reader writes. Never a browser. RED_PROOF below.
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

STORM, GRIF, LIGHT = "Stormshield", "Griffon's Eye", "Lightsabre"


def _look(i, x, session=None):
    return {"id": session or ("s_law_%d" % i), "frame": "%d_100" % i, "conf": None, "at": "2026-10-2%dT08:00:00.000Z" % (i % 8),
            "loc": "stash", "scene": "stash", "holder": "MULE1", "cell": {"x": x, "y": 0, "container": "stash"}}


def _prelude(items):
    """items: {name: (mule, copies, looks)} on a fresh store"""
    prov = {n: {"mule": m, "source": "tv", "by": "tv", "at": "2026-10-20T08:00:00.000Z", "looks": looks, "kind": "filing"}
            for n, (m, c, looks) in items.items() if looks}
    copies = {n: c for n, (m, c, looks) in items.items() if c > 1}
    return ("localStorage.setItem('d2r_ownerClaim', '*');\n"
            "localStorage.setItem('d2r_owned', %s);\n" % json.dumps(json.dumps(sorted(items)))
            + "localStorage.setItem('d2r_copies', %s);\n" % json.dumps(json.dumps(copies))
            + "localStorage.setItem('d2r_muleAssign', %s);\n" % json.dumps(json.dumps({n: v[0] for n, v in items.items()}))
            + "localStorage.setItem('d2r_vaultProv', %s);\n" % json.dumps(json.dumps(prov)))


POP = r"""
var W = window;
function pop(){ W.renderVault(); H.flush(60, 3); return ((document.getElementById('vault-pop') || {}).textContent || '').replace(/\s+/g, ' ').trim(); }
"""

CASES = {
    # seen in three cells: three copies
    "cells": (_prelude({STORM: ("uni-armor", 3, [_look(1, 0), _look(2, 2), _look(3, 4)])}),
              POP + "OUT.pop = pop(); OUT.span = W._vaultPresenceSpan(%s, copyCount(%s));" % (json.dumps(STORM), json.dumps(STORM))),
    # seen three times in ONE cell, while re-reads climbed copies[] to 3: one copy. (A name with a keeper target, as
    # Stormshield's 2, counts a re-read under its target as a real copy - his v3767 rule, the same count the card draws.)
    "oneCell": (_prelude({GRIF: ("uni-armor", 3, [_look(4, 1, "r1"), _look(5, 1, "r2"), _look(6, 1, "r3")])}),
                POP + "OUT.pop = pop(); OUT.have = copyCount(%s); OUT.target = multiTarget(%s);" % (json.dumps(GRIF), json.dumps(GRIF))),
    # typed by hand three times, never seen: three copies; one plain item beside it adds a name, not a copy figure of its own
    "hand": ("localStorage.setItem('d2r_ownerClaim', '*');\n",
             POP + "W._vaultAutoIntakeSet(false); OUT.before = pop();"
             "W.vaultHandAdd('Stormshield'); OUT.one = pop();"
             "W.vaultHandAdd('Stormshield'); W.vaultHandAdd('Stormshield'); OUT.three = pop();"
             "W.vaultHandAdd(%s); OUT.plus = pop();" % json.dumps(LIGHT)),
}


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class TheVaultHeaderCountsCopiesFromEvidence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = {k: VPN.run("(function(){" + body + "\nOUT.errors = H.errors.slice();})();", prelude=pre, timeout=300)
                 for k, (pre, body) in CASES.items()}

    def test_premise_the_pages_booted(self):
        for k, o in self.o.items():
            self.assertEqual(o["__boot"]["errors"], [], (k, o["__boot"]))

    def test_three_cells_read_three_copies(self):
        c = self.o["cells"]
        self.assertEqual(c["span"], 3, "PREMISE: the three cells are not three copies: %r" % c)
        self.assertTrue(c["pop"].startswith("1 owned · 3 copies · "), c["pop"])

    def test_one_cell_seen_three_times_reads_one_owned_and_no_copy_figure(self):
        o = self.o["oneCell"]
        self.assertEqual((o["have"], o["target"]), (3, 1), "PREMISE: copies[] did not climb, or the name carries a target: %r" % o)
        self.assertTrue(o["pop"].startswith("1 owned · "), o["pop"])
        self.assertNotIn("copies", o["pop"], "a re-read of one cell became copies: %r" % o["pop"])

    def test_copies_his_hand_typed_count_and_one_copy_says_no_figure(self):
        h = self.o["hand"]
        self.assertTrue(h["before"].startswith("0 owned · "), "PREMISE: %r" % h["before"])
        self.assertNotIn("copies", h["one"], "one copy grew a copy figure: %r" % h["one"])
        self.assertTrue(h["three"].startswith("1 owned · 3 copies · "), h["three"])
        self.assertTrue(h["plus"].startswith("2 owned · 4 copies · "), h["plus"])


RED_PROOF = [
    {"why": "REG-2886 - the line counts names only again (three Stormshields read 1 owned)",
     "file": "bible.html",
     "find": "    if (typeof header.copies === 'number') o.copies = header.copies;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2886 - the copy figure is copies[] alone (a re-read of one cell becomes copies)",
     "file": "bible.html",
     "find": "    if (typeof header.copies === 'number') o.copies = header.copies;\n",
     "replace": "    if (typeof header.copies === 'number') o.copies = Object.keys(copies || {}).reduce(function(s, k){ return s + Math.max(0, (copies[k] | 0) - 1); }, header.owned);\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2886 - one copy of each name still prints a copy figure (a number with nothing to add)",
     "file": "bible.html",
     "find": "    if (typeof p.copies === 'number' && p.copies > (+p.owned || 0)) bits.push(n(p.copies) + ' copies');",
     "replace": "    if (typeof p.copies === 'number') bits.push(n(p.copies) + ' copies');",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
