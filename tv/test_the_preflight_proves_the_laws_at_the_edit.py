# -*- coding: utf-8 -*-
"""v3902 (REG-3785, #200 card #218) - OVER THE CAP, THE PRE-FLIGHT PROVES THE LAWS WHOSE RED-PROOFS SIT AT THE EDIT.

MEASURED 11-12: v3901 changed 1,426 laws since origin/main, over the 40 the pre-flight proves on this PC, so it proved NONE
and its GREEN line said "the changed laws are proven". GitHub's proof shard 9 then read
test_a_version_is_preflighted_before_github_grades_it[4] BLIND: the REG-3310 red-proof cut `_Tab(` out of BROWSER_CALLS, a
pattern REG-3764 had left with no reader, and the hunk that made it dead began ONE line below the anchor (git diff -U0
e0513929e..3cd26bce4 -- tv/preflight.py: "@@ -52,0 +53,6 @@"; the anchor was line 52). A proof goes blind or invalid where
the code around its anchor moved: of v3901's 4,749 proofs that tamper a changed file, 67 in 39 laws sit within 10 lines of
a changed hunk. Now, over the cap, those laws are proved here, nearest first, capped at PROVE_MAX; under the cap nothing
changes; and the GREEN line says how many changed laws were proven here, never "the changed laws are proven".

Fixtures only: fake git diffs, fake gates and proofs, a fake prover. RED_PROOF below.
"""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import preflight as PF  # noqa: E402

#: the real hunk headers of v3901's tv/preflight.py change (e0513929e..3cd26bce4), the first three
V3901_DIFF = ("diff --git a/tv/preflight.py b/tv/preflight.py\n"
              "@@ -52,0 +53,6 @@ BROWSER_CALLS = re.compile(\n+x\n"
              "@@ -83 +89 @@ def read_costs(path=COSTS):\n-a\n+b\n"
              "@@ -96,0 +103,30 @@ def code_text(src):\n+y\n")
PF_KEY = "tv/preflight.py"     # a proof's `file` as heart2 resolves it, repo-relative


def _text(anchor_line, anchor, lines=300):
    rows = ["line %d" % i for i in range(1, lines + 1)]
    rows[anchor_line - 1] = anchor
    return "\n".join(rows) + "\n"


def _git(diffs, names="tv/preflight.py\n"):
    def g(*args):
        if args[0] == "rev-parse":
            return True, args[-1]
        if args[0] == "merge-base":
            return True, ""
        if args[0] == "diff" and "--name-only" in args:
            return True, names
        if args[0] == "diff":
            f = args[-1]
            return (f in diffs), diffs.get(f, "")
        return False, ""
    return g


class TheHunksAreReadInHeadsNumbering(unittest.TestCase):

    def test_v3901s_real_hunks(self):
        h = PF.changed_hunks("origin/main", [PF_KEY], _git({PF_KEY: V3901_DIFF}))
        self.assertEqual(h[PF_KEY], [(53, 58), (89, 89), (103, 132)])

    def test_a_pure_deletion_marks_the_line_after_it(self):
        h = PF.changed_hunks("origin/main", ["a.py"], _git({"a.py": "@@ -20,3 +19,0 @@\n-x\n-y\n-z\n"}))
        self.assertEqual(h["a.py"], [(20, 20)])

    def test_a_diff_that_will_not_read_is_unknown_never_unchanged(self):
        h = PF.changed_hunks("origin/main", ["gone.py"], _git({}))
        self.assertIsNone(h["gone.py"], "an unread diff read as 'nothing changed there'")


class TheLawsAtTheEditAreFound(unittest.TestCase):

    def _laws(self, proofs, text, hunks=None, pad=PF.EDIT_PAD):
        gates = [(n, n + ".py") for n in proofs]
        return PF.edit_laws(hunks if hunks is not None else {PF_KEY: [(53, 58), (89, 89), (103, 132)]}, HERE, pad,
                            _gates=lambda: gates, _proofs=lambda fn: proofs[fn[:-3]], _read=lambda k: text[k])

    def test_the_reg_3784_blind_proof_is_one_line_from_its_edit(self):
        """* THE POINT - the anchor v3901's GitHub round read BLIND sat on line 52, the dead-making hunk began on 53"""
        text = {PF_KEY: _text(52, "BROWSER_CALLS = dead")}
        got = self._laws({"test_a_version_law": [{"file": "tv/preflight.py", "find": "BROWSER_CALLS = dead",
                                                   "replace": "x", "matches": 1}]}, text)
        self.assertEqual(got, [(1, "test_a_version_law")])

    def test_far_from_every_edit_is_left_to_github(self):
        text = {PF_KEY: _text(250, "far = 1")}
        got = self._laws({"test_far": [{"file": "tv/preflight.py", "find": "far = 1", "replace": "x", "matches": 1}]}, text)
        self.assertEqual(got, [], "PREMISE: a proof 118 lines from any edit was picked - the case would not distinguish")

    def test_nearest_first_and_a_law_counts_its_nearest_proof(self):
        text = {PF_KEY: _text(52, "a52", 300)}
        rows = text[PF_KEY].split("\n")
        rows[94 - 1], rows[110 - 1], rows[140 - 1] = "a94", "a110", "a140"
        text[PF_KEY] = "\n".join(rows)
        proofs = {"test_inside": [{"file": "tv/preflight.py", "find": "a110"}],
                  "test_five_off": [{"file": "tv/preflight.py", "find": "a94"}],
                  "test_two_proofs": [{"file": "tv/preflight.py", "find": "a140"}, {"file": "tv/preflight.py", "find": "a52"}]}
        self.assertEqual(self._laws(proofs, text), [(0, "test_inside"), (1, "test_two_proofs"), (5, "test_five_off")])

    def test_nothing_changed_reads_no_gate(self):
        def boom():
            raise AssertionError("the gates were read with no hunk to sit beside")
        self.assertEqual(PF.edit_laws({PF_KEY: []}, HERE, _gates=boom), [])


class OverTheCapItProvesThoseLaws(unittest.TestCase):

    def _prove(self, names, near, prove_max=3):
        said, ran = [], []
        out = PF.prove_changed("v3903", here=tempfile.gettempdir(), prove_max=prove_max, say=said.append,
                               _git_=_git({PF_KEY: V3901_DIFF}), _gates=lambda ch: list(names), _edit=lambda: list(near),
                               _run=lambda a, **k: ran.append(a) or subprocess.CompletedProcess(a, 0, "", ""))
        return out, said, ran

    def test_baseline_under_the_cap_every_changed_law_is_proved(self):
        (owed, names, why), _said, ran = self._prove(["test_p1", "test_p2"], [(9, "test_p2")], prove_max=10)
        self.assertEqual(names, ["test_p1", "test_p2"])
        self.assertEqual(ran[0][-2:], ["test_p1", "test_p2"])

    def test_over_the_cap_the_laws_at_the_edit_are_proved_nearest_first(self):
        """* THE POINT - v3901: 1,426 changed, 0 proved; the one that went BLIND sat 1 line from its edit"""
        names = ["test_p%d" % i for i in range(8)]
        (owed, proved, why), said, ran = self._prove(names, [(0, "test_p5"), (1, "test_p2"), (4, "not_changed"),
                                                             (6, "test_p7"), (9, "test_p0")])
        self.assertEqual(proved, ["test_p5", "test_p2", "test_p7"], "the laws at the edit were not proved, nearest first")
        self.assertEqual(ran[0][-3:], ["test_p5", "test_p2", "test_p7"])
        line = [l for l in said if "REG-3785" in l]
        self.assertEqual(len(line), 1, said)
        self.assertIn("proving the 3 whose red-proofs sit within", line[0])
        self.assertIn("GitHub proves the other 5", line[0])

    def test_over_the_cap_with_none_at_the_edit_it_says_github_proves_them(self):
        (owed, proved, why), said, ran = self._prove(["test_p%d" % i for i in range(8)], [])
        self.assertEqual((owed, proved, why, ran), ([], [], None, []))
        self.assertTrue(any("none has a red-proof at the edit" in l for l in said), said)

    def test_a_blind_proof_at_the_edit_is_owed(self):
        said = []
        owed, proved, why = PF.prove_changed(
            "v3903", here=tempfile.gettempdir(), prove_max=1, say=said.append, _git_=_git({PF_KEY: V3901_DIFF}),
            _gates=lambda ch: ["test_a", "test_b"], _edit=lambda: [(1, "test_b")],
            _run=lambda a, **k: subprocess.CompletedProcess(a, 1, "     test_b[4]   BLIND <- stayed GREEN\n", ""))
        self.assertEqual(proved, ["test_b"])
        self.assertEqual(len(owed), 1, "a BLIND proof at the edit was not owed: %r" % owed)


class TheGreenLineSaysWhatWasProven(unittest.TestCase):

    def test_it_counts_the_proven_never_all(self):
        import json
        import shutil
        d = tempfile.mkdtemp(prefix="preflight-edit-law-")
        try:
            with open(os.path.join(d, "test_a.py"), "w") as fh:
                fh.write("x = 1\n")
            with open(os.path.join(d, "gate_costs.json"), "w") as fh:
                json.dump({"test_a": 1.0}, fh)
            said = []
            no = lambda: (False, "not under test here")  # noqa: E731
            code, _r = PF.preflight(here=d, say=said.append, _demos_due=no, _render_due=no,
                                    _second_eye=lambda: ("same", "not under test here"),
                                    _laws=lambda n: [(x, "ok", "") for x in n], _anchors=lambda: (True, ""),
                                    _prove=lambda: ([], ["test_p5", "test_p2"], None))
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertEqual(code, 0, said)
        green = [l for l in said if l.startswith("preflight: GREEN")]
        self.assertEqual(len(green), 1, said)
        self.assertIn("2 changed law(s) proven here", green[0])
        self.assertNotIn("the changed laws are proven", green[0], "the GREEN line claimed every changed law was proven")


RED_PROOF = [
    {"why": "REG-3785 - over the cap the pre-flight proves nothing again (v3901: 1,426 changed, 0 proved, a BLIND on GitHub)",
     "file": "tv/preflight.py",
     "find": "        picked = [n for _d, n in (near or []) if n in allowed][:prove_max]\n",
     "replace": "        picked = []\n",
     "matches": 1},
    {"why": "REG-3785 - the laws at the edit are not ordered nearest first",
     "file": "tv/preflight.py",
     "find": "    return sorted((d, n) for n, d in best.items())\n",
     "replace": "    return sorted(((d, n) for n, d in best.items()), key=lambda r: r[1])\n",
     "matches": 1},
    {"why": "REG-3785 - a proof one line from its edit is not counted at the edit (the REG-3784 blind one)",
     "file": "tv/preflight.py",
     "find": "            d = min(0 if (lo <= b and a <= hi) else min(abs(lo - b), abs(a - hi)) for lo, hi in spans)\n",
     "replace": "            d = min(0 if (lo <= b and a <= hi) else pad + 1 for lo, hi in spans)\n",
     "matches": 1},
    {"why": "REG-3785 - a diff that will not read is read as nothing changed",
     "file": "tv/preflight.py",
     "find": "        if not ok:\n            out[f] = None\n            continue\n",
     "replace": "        if not ok:\n            out[f] = []\n            continue\n",
     "matches": 1},
    {"why": "REG-3785 - a pure deletion's hunk is lost",
     "file": "tv/preflight.py",
     "find": "            spans.append((lo, lo + max(n, 1) - 1) if n else (lo + 1, lo + 1))\n",
     "replace": "            spans.append((lo, lo + n - 1))\n",
     "matches": 1},
    {"why": "REG-3785 - the GREEN line claims every changed law was proven again",
     "file": "tv/preflight.py",
     "find": "        (\", %d changed law(s) proven here (the rest, if any, are GitHub's - said above)\" % len(proved or [])) if prove\n",
     "replace": "        \", the changed laws are proven\" if prove\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
