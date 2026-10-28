# -*- coding: utf-8 -*-
"""BOTH SIDES OF A SUBTRACTION MUST BE MEASURED, OR THE DIFFERENCE IS FICTION.

`vault_autosort` counts the mule-assignment store, presses `vaultAutoAssign()`, counts again, and
reports the difference. v3224 noticed that an unreadable store yields a count of **0** and added
`okBefore` so a failed read could not masquerade as an empty vault — and applied it to exactly one
of the two identical reads. The `after` read kept `var after=0` behind an EMPTY catch.

So with his real numbers, a store that reads fine before the press and fails after:

    assignedBefore: 173      assignedAfter: 0      newlyAssigned: -173

**A large negative number that reads as mass un-assignment, and an `assignedAfter: 0` that reads
as an emptied vault — both from a read that never happened.** The comment sitting beside it named
the hazard exactly (*"`before` would read 0 if the store were unreadable"*) while guarding one
side of it. Found by a cross-family review of v3224, the version that added the half-guard.
[[zero-needs-a-denominator]] [[copy-drift]]

⚠⚠ THIS GATE EXECUTES THE FRAGMENT, AND ITS FIRST VERSION DID NOT — WHICH IS WHY IT PASSED ITS
OWN SABOTAGE. That version asserted the token `okAfter` was PRESENT. Deleting the declaration left
the token in the return expression, so the text was unchanged and the gate went green over code
that would now throw a ReferenceError. A green sabotage means the sabotage is wrong OR the gate
is — here it was the gate, in the file whose docstring warns about exactly this.
[[sabotage-is-usually-the-wrong-one]]

It now runs the real fragment in node against a stubbed board whose second read throws, and reads
the JSON that comes back.

⚠ THE FRAGMENT IS EXTRACTED, NOT RETYPED. The subject is a JS fragment held in a Python string, and
the thing being asserted is its STRUCTURE. `ast.literal_eval` gets the real fragment and
`node --check` proves it is a program — a text search would pass on the same bytes inside a
comment. [[source-reading-guard]] [[feedback-comments-vs-code]]
"""
import ast
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass


def _js_of(func_name, var="js"):
    with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == func_name), None)
    if fn is None:
        return None
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == var for t in node.targets):
            try:
                return ast.literal_eval(node.value)
            except Exception:
                return None
    return None


class TestADifferenceNeedsBothItsTerms(unittest.TestCase):

    def setUp(self):
        self.js = _js_of("vault_autosort")
        self.assertIsNotNone(self.js, "could not extract vault_autosort's JS — re-anchor this gate")

    # ── THE LAW, BY EXECUTION ────────────────────────────────────────────────────────────────
    HARNESS = """
const fs = require('fs');
const js = fs.readFileSync(process.argv[2], 'utf8');
const mode = process.argv[3] || 'both-ok';
const store = { Shako: 'mule1', Occulus: 'mule2', Tals: 'mule1' };
let reads = 0;
globalThis.document = { getElementById: () => null };
globalThis.window = {
  vaultAutoAssign() { store.Griffons = 'mule3'; },
  LSR: { getItem() {
    reads++;
    if (mode === 'after-fails'  && reads === 2) return '{ this is not json';
    if (mode === 'before-fails' && reads === 1) return '{ this is not json';
    return JSON.stringify(store);
  } }
};
console.log(eval(js));
"""

    def _run(self, mode):
        import json
        # ⚠ NOT IN THE SOURCE TREE. These were written to tv/.t_both_terms/ — untracked, not
        # gitignored, and cleaned up only by addCleanup, so a crash between the write and the
        # cleanup leaves scratch JS sitting in the repo. In THIS repo that is not merely untidy:
        # tv/ is scanned by frame_authority and graded by the pre-push gate. Temp dir instead.
        d = tempfile.mkdtemp(prefix="both_terms_")
        self.addCleanup(shutil.rmtree, d, True)
        frag = os.path.join(d, "frag.js")
        harn = os.path.join(d, "harness.js")
        with io.open(frag, "w", encoding="utf-8") as f:
            f.write(self.js)
        with io.open(harn, "w", encoding="utf-8") as f:
            f.write(self.HARNESS)
        r = subprocess.run(["node", harn, frag, mode], capture_output=True)
        self.assertEqual(r.returncode, 0,
                         "the fragment threw under %s:\n%s"
                         % (mode, r.stderr.decode("utf-8", "replace")[:600]))
        return json.loads(r.stdout.decode("utf-8", "replace").strip())

    @unittest.skipIf(shutil.which("node") is None, "node unavailable — a skip is NOT a pass")
    def test_a_good_pass_reports_the_real_delta(self):
        """⚠ THE BASELINE. A guard that refuses everything is as useless as one that refuses
        nothing — this proves the honest path still produces a number."""
        out = self._run("both-ok")
        self.assertEqual((out["assignedBefore"], out["assignedAfter"], out["newlyAssigned"]),
                         (3, 4, 1),
                         "the ordinary path stopped reporting a real delta: %r" % out)
        self.assertTrue(out["readBefore"] and out["readAfter"])

    @unittest.skipIf(shutil.which("node") is None, "node unavailable — a skip is NOT a pass")
    def test_an_unreadable_AFTER_store_reports_nothing_not_zero(self):
        """★ THE DEFECT: before=3, after unreadable -> assignedAfter 0 and newlyAssigned -3."""
        out = self._run("after-fails")
        self.assertIsNone(out["assignedAfter"],
                          "an unreadable store after the press was reported as %r — on his panel "
                          "that reads as an EMPTIED vault" % (out["assignedAfter"],))
        self.assertIsNone(out["newlyAssigned"],
                          "newlyAssigned is %r. With his real numbers (before=173) that is -173: "
                          "a number naming mass un-assignment, measured from a read that never "
                          "happened" % (out["newlyAssigned"],))
        self.assertFalse(out["readAfter"], "the failure must be SAID, not only implied by a null")
        self.assertEqual(out["assignedBefore"], 3,
                         "the half that DID succeed must still be reported — refusing both is "
                         "throwing away a real measurement")

    @unittest.skipIf(shutil.which("node") is None, "node unavailable — a skip is NOT a pass")
    def test_an_unreadable_BEFORE_store_reports_nothing_not_zero(self):
        """The symmetric case — v3224 guarded this one and only this one."""
        out = self._run("before-fails")
        self.assertIsNone(out["assignedBefore"])
        self.assertIsNone(out["newlyAssigned"],
                          "a difference is a measurement only when BOTH terms were measured: %r"
                          % (out["newlyAssigned"],))
        self.assertFalse(out["readBefore"])
        # ⚠ THE SYMMETRY GATE WAS ITSELF ASYMMETRIC, and a cross-family review of v3230 caught it.
        # The after-fails case pins that the surviving count is still reported; this case did not,
        # so "refusing both throws away a real measurement" was enforced in one direction only —
        # the exact half-application this whole file exists to punish. [[copy-drift]]
        self.assertEqual(out["assignedAfter"], 4,
                         "the half that DID succeed must still be reported — a failed BEFORE read "
                         "must not suppress a good AFTER count: %r" % out)

    # ── AND IT MUST STILL BE A PROGRAM ──────────────────────────────────────────────────────
    @unittest.skipIf(shutil.which("node") is None, "node unavailable — a skip is NOT a pass")
    def test_the_fragment_is_valid_javascript(self):
        """A hop that does not parse is a dead render, and this one runs inside his board."""
        d = tempfile.mkdtemp(prefix="both_terms_")
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "frag.js")
        with io.open(p, "w", encoding="utf-8") as f:
            f.write(self.js)
        r = subprocess.run(["node", "--check", p], capture_output=True)
        self.assertEqual(r.returncode, 0,
                         "vault_autosort's JS does not parse:\n%s"
                         % r.stderr.decode("utf-8", "replace")[:600])

RED_PROOF = [
    {"why": "v3230 - an unreadable AFTER read reports 0, so newlyAssigned reads -173: mass un-assignment from a read that never happened",
     "file": "tv/control_app.py",
     "find": "          \"assignedAfter:(okAfter?after:null),readBefore:okBefore,readAfter:okAfter,\"\n          \"newlyAssigned:((okBefore&&okAfter)?(after-before):null)});\"\n",
     "replace": "          \"assignedAfter:after,readBefore:okBefore,readAfter:okAfter,\"\n          \"newlyAssigned:(okBefore?(after-before):null)});\"\n",
     "matches": 1},
    {"why": "v3224 - an unreadable BEFORE read reports 0, so the difference is fiction on the other side",
     "file": "tv/control_app.py",
     "find": "          \"return JSON.stringify({ok:true,assignedBefore:(okBefore?before:null),\"\n",
     "replace": "          \"return JSON.stringify({ok:true,assignedBefore:before,\"\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
