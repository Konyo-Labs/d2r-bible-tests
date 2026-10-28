# -*- coding: utf-8 -*-
"""ALT inject run 2026-10-24 (bugs 1 and 5) - THE PAGE-LOAD SEAM RECONCILES d2r_vaultRecords WITH THE NAME STORES.

GrokBot's ALT batch run on v3795 found two faces of one hole:
  * bug 1: a name removed from d2r_owned / d2r_muleAssign / d2r_tvExtraItems between two loads kept its
    d2r_vaultRecords row (12 GBL-TEST rows left after the strip);
  * bug 5: a lone d2r_tvExtraItems item filed to a mule between two loads read "not filed" (the mule said 0),
    because FIND and the mule window trust the records store first.
The cause: _vaultRecordsArm, the one page-load call, ran _vaultRecordsMigrate, which answers `already` when the
stamp and the store are there and persists nothing. A store edited by anything but the page's own doors (a restore,
another tab, a harness, a sync) was never reconciled. The arm now asks the EXISTING _vaultRecordsRefresh on
`already` - the same signature compare and guarded re-persist the write doors already use.

Two loads of the WHOLE page in node (tv/vault_page_node.py), the storage of the first handed to the second.
RED_PROOF: drop the refresh from the `already` branch of _vaultRecordsArm and both tests fail.
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

AUTOMATED = r"""
Object.defineProperty(navigator, 'webdriver', { get: function(){ return true; }, configurable: true });
location.protocol = 'file:'; location.href = 'file:///spec/bible.html'; location.origin = 'null'; location.host = ''; location.hostname = '';
"""
FIRST = AUTOMATED + r"""
localStorage.setItem('d2r_ownerClaim', '*');
localStorage.setItem('d2r_muleRoster', JSON.stringify([{ id: 'm1', name: 'MULE1' }]));
"""
# load 1: two names through the real hand-add door, the records armed and stamped, then the stores edited
# outside the page (as a restore, a sync or a harness does) and the storage handed on
LOAD1 = r"""
H.flush(60, 3);
['Harlequin Crest', 'Stone of Jordan'].forEach(function(n){ window.vaultHandAdd(n); H.flush(60, 3); });
var a = window._vaultRecordsArm();
OUT.armed = !!(a && (a.stamped || a.already));
function J(k, d){ try { return JSON.parse(window.LSR.getItem(k) || d); } catch (e) { return JSON.parse(d); } }
var ow = J('d2r_owned', '[]'), ma = J('d2r_muleAssign', '{}'), tx = J('d2r_tvExtraItems', '{}');
OUT.ownedBefore = ow.slice();
__EDIT__
window.LSR.setItem('d2r_owned', JSON.stringify(ow));
window.LSR.setItem('d2r_muleAssign', JSON.stringify(ma));
window.LSR.setItem('d2r_tvExtraItems', JSON.stringify(tx));
OUT.raw = {}; H.RAW.forEach(function(v, k){ OUT.raw[k] = v; });
"""
LOAD2 = r"""
H.flush(60, 3);
window._vaultRecordsArm();   /* the page-load seam (idempotent: a second ask after the boot's own is a no-op) */
H.flush(60, 3);
var s = null; try { s = JSON.parse(window.LSR.getItem('d2r_vaultRecords') || 'null'); } catch (e) { s = 'UNREADABLE'; }
OUT.names = (s && s.records) ? s.records.map(function(r){ return r.name; }) : s;
OUT.ring = window._vaultRecordsFind('GBL-TEST-Ring');
"""
DROP = "ow = ow.filter(function(n){ return n !== 'The Stone of Jordan'; }); delete ma['The Stone of Jordan'];"
ADD = ("tx['GBL-TEST-Ring'] = { rarity: 'basic', base: 'GBL-TEST-Ring', cat: 'x', val: 'tv', desc: 'law' };"
       " ma['GBL-TEST-Ring'] = 'm1'; ow.push('GBL-TEST-Ring');")


def _two_loads(edit):
    one = VPN.run(LOAD1.replace("__EDIT__", edit), prelude=FIRST, timeout=300)
    assert one.get("armed"), "load 1 never armed the records: %r" % one
    seed = "".join("localStorage.setItem(%s, %s);\n" % (json.dumps(k), json.dumps(v)) for k, v in one["raw"].items())
    return one, VPN.run(LOAD2, prelude=AUTOMATED + seed, timeout=300)


class AReloadReconcilesTheVaultRecords(unittest.TestCase):

    def test_a_name_removed_between_loads_leaves_no_record(self):
        one, two = _two_loads(DROP)
        self.assertIn("The Stone of Jordan", one["ownedBefore"], "the seed never owned the name")
        self.assertIsInstance(two["names"], list, two)
        self.assertNotIn("The Stone of Jordan", two["names"],
                         "bug 1: a name gone from owned/assign kept its d2r_vaultRecords row across a reload")
        self.assertIn("Harlequin Crest (Shako)", two["names"], "the reconcile dropped a name it should keep")

    def test_a_lone_extra_filed_between_loads_reads_filed(self):
        _one, two = _two_loads(ADD)
        self.assertEqual(two["ring"], "m1",
                         "bug 5: a lone TV extra filed to a mule between loads read not-filed (%r)" % (two["ring"],))
        self.assertIn("GBL-TEST-Ring", two["names"])

    def test_an_unknown_live_model_keeps_the_stamp_and_the_bytes(self):
        """Grok review r1 (HIGH): with the mule map UNKNOWN the refresh's guarded persist refuses and marks the store
        dirty, which drops the migrate stamp. The arm must not ask the refresh then."""
        one = VPN.run(LOAD1.replace("__EDIT__", ""), prelude=FIRST, timeout=300)
        raw = dict(one["raw"])
        raw["d2r_muleAssign"] = "{not json"
        seed = "".join("localStorage.setItem(%s, %s);\n" % (json.dumps(k), json.dumps(v)) for k, v in raw.items())
        two = VPN.run(LOAD2 + "OUT.stamp = window.LSR.getItem('d2r_vaultRecordsMigrate');"
                      "OUT.dirty = window.LSR.getItem('d2r_vaultRecordsDirty');"
                      "OUT.bytes = window.LSR.getItem('d2r_vaultRecords');",
                      prelude=AUTOMATED + seed, timeout=300)
        self.assertEqual(two["stamp"], raw.get("d2r_vaultRecordsMigrate"), "an UNKNOWN mule map dropped the records stamp: %r" % two)
        self.assertIsNone(two["dirty"], "an UNKNOWN mule map marked the records dirty")
        self.assertEqual(two["bytes"], raw.get("d2r_vaultRecords"), "an UNKNOWN mule map rewrote the records")

RED_PROOF = [
    {"why": "ALT inject run (bugs 1 + 5) - the page-load seam stops reconciling the records on `already`: a removed name keeps its row and a newly filed extra reads not filed",
     "file": "bible.html",
     "find": "      } else if (r.already && typeof _vaultRecordsRefresh === 'function') {\n",
     "replace": "      } else if (false && r.already && typeof _vaultRecordsRefresh === 'function') {\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
