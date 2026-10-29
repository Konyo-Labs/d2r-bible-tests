# -*- coding: utf-8 -*-
"""#76 INC-2 (v3757) — FIND + GRAIL-DUPES DERIVE FROM THE ONE-RECORD MODEL, AT PARITY WITH THE LIVE VIEWS.

The design's PHASE 1 (ONE_RECORD_DESIGN_2026-10-15): re-express the views through _vaultRecords() and prove
byte-parity with the live direct-from-store path, so INC-3 (gated, his confirm) can swap the records SOURCE to
a persisted per-copy store and the live views flip to these with NO behaviour change.

This law extracts the SHIPPED functions out of bible.html and runs them in node on a seeded fixture:

  · _vaultRecordsOverflow()  must EQUAL the live _vaultSharedOverflowNames()  (GRAIL-DUPES trade-stock names).
  · _vaultRecordsFind(name)  must EQUAL assign[name] for a FILED name (its home mule) — the invariant the live
    _vaultWhereIs(name).mule guarantees; null for a non-filed name; and it never invents a home.
  · FIDELITY: the one-record index carries copyCount(name) records per name — so the overflow derived from the
    index can never silently drift from the copies[] the live view reads.

NOT vacuous: records.index[n].length is built from copyCount in _vaultRecords and record.mule from assign, so a
parity miss means the RECORDS MODEL drifted from the stores it mirrors — exactly what must hold before INC-3
swaps the source. Read-only: nothing is stored. A missing node raises — this law does not skip. RED_PROOF below.
[[the-unjoined-end]] [[unknown-stays-unknown]] [[heart-first]]
"""
import json
import os
import re
import shutil
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

BIBLE = os.path.join(HERE, "..", "bible.html")
NODE = os.environ.get("NODE") or shutil.which("node")


def _fn(src, name):
    """Extract `function NAME(...){ ...balanced... }` by brace-balancing from the first match."""
    m = re.search(r"\bfunction %s\s*\(" % re.escape(name), src)
    if not m:
        raise AssertionError("could not find function %s in bible.html" % name)
    i = src.index("{", m.start())
    depth, j = 0, i
    while j < len(src):
        c = src[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
        j += 1
    raise AssertionError("unbalanced braces extracting %s" % name)


# the functions under test + the live overflow chain they are proven against (all short, pure-ish)
EXTRACT = ["_sharedNames", "_sharedCopyCount", "_sharedCappedCopies", "_vaultSharedOverflowCells",
           "_vaultSharedOverflowNames", "_vaultSameMuleCopies", "_vaultRecords", "_vaultRecordsSource", "_vrSourceChoice",
           "_vrRecHome", "_vaultRecordsFind", "_vaultRecordsOverflow"]


class TestV3757RecordsFindAndOverflowParity(unittest.TestCase):
    def _run(self, extra=""):
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        with open(BIBLE, encoding="utf-8") as f:
            src = f.read()
        fns = "\n".join(_fn(src, n) for n in EXTRACT)
        prog = r"""
var window = globalThis;
// ── fixture: A filed to mule1; B shared(1); C shared(4 -> overflow 2); E shared(3 -> overflow 1);
//    F shared(2 == cap, the BOUNDARY -> NO overflow, so a `>= cap` bug would wrongly fill dupes); D loose ──
var assign = { A:'mule1', B:'shared', C:'shared', E:'shared', F:'shared' };   // D unassigned -> loose
var copies = { C:4, E:3, F:2 };                                    // A,B default 1
var OWNED  = ['A','B','C','D','E','F'];
// ── stubs for the deps _vaultRecords reads (kept consistent with the fixture) ──
var _SHARED_COPY_CAP = 2, _MULE_COPY_CAP = 3;
function ownedPool(){ return OWNED.slice(); }
function copyCount(n){ var c = copies[n]; return (c && c > 0) ? c : (OWNED.indexOf(n) >= 0 ? 1 : 0); }
function isSharedStash(n){ return assign[n] === 'shared'; }         // fixture: shared-assigned == shared-stash
function muleById(id){ return (id === 'mule1') ? { id:'mule1', name:'Mule One' } : null; }
function _dockNames(){ return ['D']; }                             // D is loose
window._carriedNames = function(){ return []; };                   // nothing carried
var KEEP_IN_INVENTORY = /Annihilus|Hellfire Torch|Gheed/;
function _keepName(n){ return n; }
""" + fns + r"""
// ── assertions ──
var out = {
  recOverflow:  _vaultRecordsOverflow(),
  liveOverflow: _vaultSharedOverflowNames(),
  findA: _vaultRecordsFind('A'),   // filed -> 'mule1'
  findB: _vaultRecordsFind('B'),   // shared locker -> 'shared'
  findD: _vaultRecordsFind('D'),   // loose  -> null
  findZ: _vaultRecordsFind('ZZ'),  // unknown -> null (no index)
  idxLen: (function(){ var r = _vaultRecords(); var o = {}; OWNED.forEach(function(n){ o[n] = (r.index[n]||[]).length; }); return o; })()
};
""" + extra + r"""
process.stdout.write(JSON.stringify(out));
"""
        import subprocess
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-2000:])
        return json.loads(p.stdout)

    def test_find_and_overflow_derive_from_records_at_parity(self):
        o = self._run()
        # same mule (Elad 2026-10-18 13:18 IDT): no name is GRAIL-DUPES trade stock, and the two lists agree
        self.assertEqual(o["recOverflow"], [], "records overflow is wrong: %r" % o["recOverflow"])
        self.assertEqual(o["recOverflow"], o["liveOverflow"],
                         "records overflow != live _vaultSharedOverflowNames: %r vs %r" % (o["recOverflow"], o["liveOverflow"]))
        # FIND: a filed name resolves to its home mule; a non-filed / unknown name never invents a home
        self.assertEqual(o["findA"], "mule1", "a filed name did not resolve to its mule via records")
        self.assertEqual(o["findB"], "shared", "a shared-locker name did not home on the shared locker")
        self.assertIsNone(o["findD"], "a LOOSE name was given a mule home")
        self.assertIsNone(o["findZ"], "an unknown name was given a home")
        # FIDELITY: the index carries copyCount records per name (so overflow can't drift from copies[])
        self.assertEqual(o["idxLen"], {"A": 1, "B": 1, "C": 4, "D": 1, "E": 3, "F": 2},
                         "the one-record index miscounts copies: %r" % o["idxLen"])


RED_PROOF = [
    {
        "why": "Nothing is GRAIL-DUPES trade stock. Returning a name fills the dupes list and breaks parity with the empty live view.",
        "file": "bible.html",
        "find": "return []; /* v3767 no dupes list */",
        "replace": "return ['C']; /* v3767 no dupes list */",
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main()
