# -*- coding: utf-8 -*-
"""#111 (reviewers C2/E/D) - A COPY CELL'S X SAYS EVERY COPY GOES.

The X on ONE copy's cell called vaultUnassign(name) - every copy of the item went back to the dock - and its hover said only
"send back to the unsorted dock". Copies of one item share one filing (d2r_muleAssign is per name; #76's per-copy record
store is still dormant), so one copy cannot leave alone yet: on a cell whose item has more than one copy, the X says so.
A single copy, a hardened lock and an unreadable lock store read as before.

Driven on the whole page in node (window._vaultCellXTitle), and the cell paints its X through it. RED_PROOF below.
"""
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

BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
BODY = r"""
(function(){
var T = window._vaultCellXTitle;
OUT.two = T('Harlequin Crest', 2, null);
OUT.one = T('Harlequin Crest', 1, null);
OUT.locked = T('Harlequin Crest', 3, { tier: 'HARDENED' });
OUT.unk = T('Harlequin Crest', 3, { unknown: true });
})();
"""


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class ACopyCellSaysEveryCopyGoes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, timeout=300)

    def test_the_page_booted(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])

    def test_a_multi_copy_cell_says_all_copies_go(self):
        self.assertIn("ALL 2 copies of Harlequin Crest go together", self.o["two"],
                      "the X on one copy still hides that every copy goes (#111): %r" % self.o["two"])
        self.assertEqual(self.o["one"], "send back to the unsorted dock")
        self.assertIn("locked in this locker", self.o["locked"])
        self.assertIn("UNKNOWN", self.o["unk"])

    def test_the_cell_paints_its_x_through_it(self):
        with open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count("        var _xTitle = _vaultCellXTitle(n, _cc, _hlk);"), 1,
                         "the copy cell no longer asks _vaultCellXTitle for its X")


RED_PROOF = [
    {"why": "#111 - a multi-copy cell's X hides that every copy goes again",
     "file": "bible.html",
     "find": "    return gridActSay('', 'send back to the unsorted dock' + ((typeof cc === 'number' && cc > 1)\n",
     "replace": "    return gridActSay('', 'send back to the unsorted dock' + ((false)\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
