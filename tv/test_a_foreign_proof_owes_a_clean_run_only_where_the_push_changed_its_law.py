# -*- coding: utf-8 -*-
"""REG-2599 (#242 narrowed) - A PROOF ANOTHER TREE BANKED OWES A CLEAN RUN HERE ONLY WHEN THE PUSH CHANGES ITS LAW.

#242 / REG-2587 made every gate served from another tree (a CI census shard, the box) run one untampered run in THIS
tree before its PROVENs were kept. Elad, 2026-10-23: proofs banked elsewhere must become HITS in the Mac pre-push hook,
and a clean run per served gate is most of what a hit saves. Keep the guard where it guards something: a gate whose OWN
law file this push changes still owes its clean run here; a gate in the push for any other reason is kept on the other
tree's word, over byte-identical inputs. What the push changes being UNKNOWN keeps the old guard for every gate.

  1. _direct_laws: the gates whose own law file is in the push's changed set; None when that set is unknown;
  2. the main pass: law not changed -> no clean run, PROVENs kept, said once; law changed / unknown -> one clean run;
  3. the clean wave: a gate served whole from another tree is skipped when its law is not changed, asked when it is;
  4. _prove_push reads what the push changes and says how many gates still owe a clean run; a failed read owes all.
Drives the REAL _prove_gate / _wave_gate / _prove_push paths over a temp gate and a temp cache.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402  (its docstrings carry non-ASCII)
_console_safe_enable()
import test_an_imported_gate_runs_clean_here_on_a_small_push as B  # noqa: E402  (contains the fixture tmp)
import test_a_push_proof_runs_only_where_its_defect_shows as P  # noqa: E402
H = B.H
OTHER = "/some/other/worktree"


def _rel(filename):
    return os.path.relpath(os.path.join(H.HERE, filename), H.REPO).replace(os.sep, "/")


class TheChangedLaws(unittest.TestCase):

    def test_only_a_gate_whose_own_law_file_changed_is_direct(self):
        have = [("g1", "test_one.py", []), ("g2", "test_two.py", [])]
        self.assertEqual(H._direct_laws(have, {_rel("test_one.py"), "tv/heart2.py"}), {"g1"})
        self.assertEqual(H._direct_laws(have, set()), set())
        self.assertEqual(H._direct_laws(have, {"test_one.py"}), set(),
                         "a bare basename matched a repo path - the changed set is repo-relative")

    def test_an_unknown_change_is_unknown_not_empty(self):
        self.assertIsNone(H._direct_laws([("g1", "test_one.py", [])], None))
        run = H._PushRun(order={}, browser=(), cache=None)
        self.assertIsNone(run.direct, "a run nobody told what changed must owe every clean run")
        self.assertTrue(H._owes_here(run, "anything"))
        run.direct = set()
        self.assertFalse(H._owes_here(run, "anything"))


class TheMainPass(B.AnImportedGateRunsCleanHere):
    """The REG-2587 fixture, with the push's changed laws set before the gate is proved."""

    def push(self, tree, clean, wave=None, direct=None):
        real = H._PushRun

        def _run(*a, **k):
            r = real(*a, **k)
            r.direct = direct
            return r
        H._PushRun = _run
        try:
            return B.AnImportedGateRunsCleanHere.push(self, tree, clean, wave)
        finally:
            H._PushRun = real

    def test_a_gate_whose_law_the_push_did_not_change_keeps_its_proofs_without_a_run(self):
        run, per = self.push(OTHER, [False], direct={"some-other-gate"})
        self.assertEqual(self.runs.clean, 0, "a gate whose law this push did not change still ran clean here")
        self.assertEqual(per, [H.PROVEN] * 2, "the other tree's PROVENs were not kept")
        self.assertIsNone(run.first)
        self.assertEqual(sum("REG-2599" in ln for ln in B.LINES), 1, B.LINES)

    def test_a_gate_whose_law_the_push_changed_still_runs_clean_and_fails_red(self):
        run, per = self.push(OTHER, [False], direct={B.GATE})
        self.assertEqual(self.runs.clean, 1, "a gate whose own law this push changed was kept on another tree's word")
        self.assertEqual(per, [H.UNPROVABLE] * 2)
        self.assertIsNotNone(run.first)

    def test_an_unknown_change_still_runs_clean(self):
        run, per = self.push(OTHER, [True], direct=None)
        self.assertEqual((self.runs.clean, per), (1, [H.PROVEN] * 2))


class TheWave(B.AnImportedGateRunsCleanHere):

    def wave(self, direct):
        B.AnImportedGateRunsCleanHere.push(self, OTHER, [True])     # bank both proofs...
        for e in self.cache.entries.values():
            e["tree"] = OTHER                                       # ...as another tree's (REG-2589 re-banked them here)
        self.runs = B._Runs(self.tv, [True])
        H._run_gate = self.runs
        run = H._PushRun(order={}, browser=(), cache=self.cache)
        run.direct = direct
        H._PUSH = run
        try:
            return H._wave_gate(self.tv, B.GATE, "fake_gate.py", self.proofs, B._say, run)
        finally:
            H._PUSH = None

    def test_the_wave_skips_a_foreign_gate_whose_law_did_not_change(self):
        v, per = self.wave(set())
        self.assertEqual((v, self.runs.clean), (H.NOT_RUN, 0), "the wave ran a gate the push did not change")

    def test_the_wave_runs_a_foreign_gate_whose_law_changed(self):
        self.wave({B.GATE})
        self.assertEqual(self.runs.clean, 1, "the wave skipped a gate whose own law this push changed")
        self.wave(None)
        self.assertEqual(self.runs.clean, 1, "the wave skipped a gate when what the push changes is unknown")


class TheChangedSetIsRead(unittest.TestCase):

    def test_a_law_path_git_would_quote_is_read_raw(self):
        """second eye - `git diff --name-only` quotes a path with a space or é; the push must still see it changed"""
        import subprocess
        import tempfile
        import shutil
        root = tempfile.mkdtemp(prefix="h2direct.")
        self.addCleanup(shutil.rmtree, root, True)
        env = H._git_free_env(GIT_AUTHOR_NAME="f", GIT_AUTHOR_EMAIL="f@x", GIT_COMMITTER_NAME="f",
                              GIT_COMMITTER_EMAIL="f@x")
        rel = u"tv/t_caf\u00e9 law.py"
        os.makedirs(os.path.join(root, "tv"))

        def git(*a):
            subprocess.run(["git", "-C", root] + list(a), check=True, capture_output=True, env=env)
        git("init", "-q")
        git("config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        with open(os.path.join(root, *rel.split("/")), "w", encoding="utf-8") as fh:
            fh.write("A = 1\n")
        git("add", "-A")
        git("commit", "-q", "-m", "fixture")
        git("update-ref", "refs/remotes/origin/main", "HEAD")
        with open(os.path.join(root, *rel.split("/")), "w", encoding="utf-8") as fh:
            fh.write("A = 2\n")
        real = H.REPO
        H.REPO = root
        try:
            base, changed = H._push_changed()
        finally:
            H.REPO = real
        self.assertEqual(base, "origin/main")
        self.assertEqual(changed, {rel}, "the changed law path was not read as git wrote it")


def _prove_push(changed):
    said, stopped = [], []
    with P._Env(H42_LOG=os.devnull, HEART2_PROVE_WORKERS="1", TV_LAW_WIDTHS=None), \
            P._Patch(make_sandbox=P._Sandboxes().make, _push_facts=P._no_facts, _push_changed=changed):
        H._prove_push([(P._GATE, P._FILE, [P._proof()])], said.append, stopped)
    return said


class ThePush(unittest.TestCase):

    def test_the_push_reads_what_it_changes(self):
        said = _prove_push(lambda: ("origin/main", {_rel(P._FILE)}))
        self.assertTrue(any("REG-2599: 1 of 1" in ln for ln in said), said)
        said = _prove_push(lambda: ("origin/main", set()))
        self.assertTrue(any("REG-2599: 0 of 1" in ln for ln in said), said)

    def test_a_failed_read_owes_every_clean_run(self):
        def boom():
            raise OSError("no git")
        said = _prove_push(boom)
        self.assertTrue(any("REG-2599" in ln and "could not be read" in ln for ln in said), said)
        self.assertFalse(any("REG-2599: " in ln and " of " in ln for ln in said), said)


# the inherited REG-2587 cases run here too: with no changed set they must behave exactly as before
RED_PROOF = [
    {"why": "REG-2599 - a gate whose law the push did not change still owes a clean run in the main pass",
     "file": "heart2.py",
     "find": "    if not _owes_here(run, name):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-2599 - the wave still runs a foreign gate whose law the push did not change",
     "file": "heart2.py",
     "find": "(_hit.get(\"tree\") != TREE_ID and _owes_here(run, name)):   # REG-2599\n",
     "replace": "(_hit.get(\"tree\") != TREE_ID):   # REG-2599\n",
     "matches": 1},
    {"why": "REG-2599 - an unknown change is read as 'nothing changed', so every foreign gate skips its clean run",
     "file": "heart2.py",
     "find": "    return direct is None or name in direct\n",
     "replace": "    return name in (direct or ())\n",
     "matches": 1},
    {"why": "REG-2599 - every gate counts as changed, so nothing is narrowed",
     "file": "heart2.py",
     "find": "               if os.path.relpath(os.path.join(HERE, filename), REPO).replace(os.sep, \"/\") in changed)\n",
     "replace": "               if True)\n",
     "matches": 1},
    {"why": "REG-2599 (second eye) - a quoted path (space, é) is read as git prints it, so its changed law looks unchanged",
     "file": "heart2.py",
     "find": "    ok, out = _git(\"-c\", \"core.quotePath=false\", \"diff\", \"--name-only\", \"-z\", base)\n    return base, (set(p for p in out.split(\"\\0\") if p) if ok else None)\n",
     "replace": "    ok, out = _git(\"diff\", \"--name-only\", base)\n    return base, (set(l.strip() for l in out.splitlines() if l.strip()) if ok else None)\n",
     "matches": 1},
    {"why": "REG-2599 - _prove_push never reads what the push changes",
     "file": "heart2.py",
     "find": "        run.direct = _direct_laws(have, _push_changed()[1])     # REG-2599 - who still owes a clean run here\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "REG-2599 - the main-pass skip is never said",
     "file": "heart2.py",
     "find": "        say(\"     %-52s   ↳ REG-2599: %d proof(s) were proved in another tree",
     "replace": "        (lambda *a: 0)(\"     %-52s   ↳ REG-2599: %d proof(s) were proved in another tree",
     "matches": 1},
    {"why": "REG-2599 - a failed read of what changed is swallowed silently",
     "file": "heart2.py",
     "find": "        say(\"  ⚠ REG-2599 which laws this push changes could not be read",
     "replace": "        (lambda *a: 0)(\"  ⚠ REG-2599 which laws this push changes could not be read",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
