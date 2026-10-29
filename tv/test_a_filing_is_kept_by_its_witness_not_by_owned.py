# -*- coding: utf-8 -*-
"""#246 L12 — A FILING IS KEPT BY ITS WITNESS, NOT BY `owned`.

The render prune in renderVault used to keep a mule filing for exactly as long as its name sat in the owned pool
— and d2r_owned means ticked or found-ever. So `owned` was the only thing a filing answered to: a found-ever name
kept a false filing alive, and a WITNESSED filing whose name left `owned` (a grail un-tick deletes it) was thrown
away with nothing but a found-ever list having spoken.

WHAT THIS LAW HOLDS, driven on the SHIPPED prune statement (cut from bible.html between its own markers, run in
node, never re-typed):
  · a WITNESSED filing (a d2r_vaultProv row) stands when its name is no longer in the pool;
  · an UNWITNESSED filing whose name left the pool goes, as before;
  · an unwitnessed filing still in the pool is NOT deleted here — the fresh vault is his ruling, backed up first —
    and is left for the tile's NO WITNESS tag and the doctor's 'vault provenance' row to call out;
  · a home that is not a mule goes whatever it carries, and __keep stays.
RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

NODE = shutil.which("node")
BIBLE = os.path.join(ROOT, "bible.html")
START = "    var _pvLive = _provAll();\n"
END = "    // v360 — shared-stash items"


def _prune():
    with io.open(BIBLE, encoding="utf-8") as f:
        s = f.read()
    assert s.count(START) == 1 and s.count(END) == 1, "the prune is not where this law cuts it (%d, %d)" % (
        s.count(START), s.count(END))
    i = s.index(START)
    return s[i:s.index(END, i)]


PROG = r"""
var window = {};
var PROV = %(prov)s;
function _provAll(){ return JSON.parse(JSON.stringify(PROV)); }
var ROSTER = { 'uni-armor': 1, 'uni-small': 1 };
function muleById(id){ return ROSTER[id] ? { id: id } : null; }
var pool = %(pool)s;
var poolAll = pool;   /* REG-3099 - the prune's "still owned" is the whole owned pool; this fixture's pool is all owned */
var assign = %(assign)s;
%(prune)s
process.stdout.write(JSON.stringify(assign));
"""


def _run(assign, pool, prov):
    prog = PROG % {"assign": json.dumps(assign), "pool": json.dumps(pool), "prov": json.dumps(prov),
                   "prune": _prune()}
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("the shipped prune would not execute: %s" % (r.stderr or r.stdout)[-600:])
    return json.loads(r.stdout)


@unittest.skipIf(NODE is None, "node is absent — this law runs the SHIPPED prune; UNMEASURED, not passing")
class AFilingIsKeptByItsWitnessNotByOwned(unittest.TestCase):

    def test_the_prune_answers_to_the_witness(self):
        assign = {"Witnessed Out": "uni-armor", "Unwitnessed Out": "uni-armor", "Legacy In": "uni-small",
                  "Gone Home": "m_deleted", "Kept Inventory": "__keep"}
        prov = {"Witnessed Out": {"source": "stash", "mule": "uni-armor"},
                "Gone Home": {"source": "hand", "mule": "m_deleted"}}
        pool = ["Legacy In", "Kept Inventory", "Gone Home"]
        got = _run(assign, pool, prov)
        self.assertEqual("uni-armor", got.get("Witnessed Out"),
                         "a WITNESSED filing was thrown away because its name left `owned`")
        self.assertNotIn("Unwitnessed Out", got, "an unwitnessed filing outside the pool survived")
        self.assertEqual("uni-small", got.get("Legacy In"),
                         "an unwitnessed filing in the pool was deleted by a render — that is his fresh-vault ruling")
        self.assertNotIn("Gone Home", got, "a filing to a mule that does not exist survived")
        self.assertEqual("__keep", got.get("Kept Inventory"))


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "#246 W6 - the prune answers to `owned` alone again: a witnessed filing is dropped when its name leaves the pool",
        "file": "bible.html",
        "find": "      if (Object.prototype.hasOwnProperty.call(_pvW6, n)) return;\n",
        "replace": "",
        "matches": 1,
    },
]
