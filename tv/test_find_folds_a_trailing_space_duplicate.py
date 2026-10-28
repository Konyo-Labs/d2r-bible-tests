# -*- coding: utf-8 -*-
"""ALT inject run 2026-10-24 (bug 6) - FIND SHOWS ONE ROW FOR NAMES THAT DIFFER ONLY BY OUTER OR DOUBLED SPACES.

GrokBot's ALT edge batch owned `GBL-TEST-Dup` and `GBL-TEST-Dup ` and FIND printed two identical rows. vaultFind
already collapses one item's name forms to one row (#76, keyed on _vfCanon); the key now also folds whitespace
(trim + runs of spaces to one), and the trimmed spelling is the one the row shows. Nothing in the stores changes.

Whole page in node (tv/vault_page_node.py).
RED_PROOF: key the collapse on the bare _vfCanon again and FIND shows two rows.
"""
import os
import re
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

PRELUDE = r"""
Object.defineProperty(navigator, 'webdriver', { get: function(){ return true; }, configurable: true });
location.protocol = 'file:'; location.href = 'file:///spec/bible.html'; location.origin = 'null'; location.host = ''; location.hostname = '';
localStorage.setItem('d2r_ownerClaim', '*');
localStorage.setItem('d2r_muleRoster', JSON.stringify([{ id: 'm1', name: 'MULE1' }]));
var tx = {}, ma = {}, ow = [];
['GBL-TEST-Dup ', 'GBL-TEST-Dup', 'GBL-TEST-Other'].forEach(function(n){ tx[n] = { rarity: 'basic', base: n, cat: 'x', val: 'tv', desc: 'law' }; ma[n] = 'm1'; ow.push(n); });
localStorage.setItem('d2r_tvExtraItems', JSON.stringify(tx));
localStorage.setItem('d2r_muleAssign', JSON.stringify(ma));
localStorage.setItem('d2r_owned', JSON.stringify(ow));
"""
BODY = r"""
H.flush(60, 3);
window.vaultFind('Dup'); OUT.dup = (document.getElementById('vault-find-results') || {}).innerHTML || '';
window.vaultFind('GBL-TEST'); OUT.all = (document.getElementById('vault-find-results') || {}).innerHTML || '';
"""


def _rows(html):
    return re.findall(r'<div class="vfr-row" title="([^"]*)"', html)


class FindFoldsATrailingSpaceDuplicate(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = VPN.run(BODY, prelude=PRELUDE, timeout=300)

    def test_one_row_for_a_trailing_space_twin(self):
        self.assertEqual(_rows(self.out["dup"]), ["GBL-TEST-Dup"],
                         "bug 6: FIND showed %r for two names that differ only by a trailing space" % _rows(self.out["dup"]))

    def test_a_different_name_still_has_its_row(self):
        self.assertEqual(sorted(_rows(self.out["all"])), ["GBL-TEST-Dup", "GBL-TEST-Other"])

RED_PROOF = [
    {"why": "ALT inject run (bug 6) - FIND keys the collapse on the bare canon again, so two names that differ only by a trailing space are two rows",
     "file": "bible.html",
     "find": "        var c = String(c0).replace(/\\s+/g, ' ').trim();   /* ALT inject run bug 6: 'X' and 'X ' are one row */\n",
     "replace": "        var c = String(c0);   /* ALT inject run bug 6: 'X' and 'X ' are one row */\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
