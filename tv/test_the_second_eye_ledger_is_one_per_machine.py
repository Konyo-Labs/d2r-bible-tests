# -*- coding: utf-8 -*-
"""#178 (REG-2450) - THE SECOND-EYE LEDGER IS ONE PER MACHINE, AND A WORKTREE'S LOOK IS NEVER LOST.

MEASURED 2026-10-22 (Push A1): the ship gate (`second_eye_ledger.py --check <prev> --gate`) read the PUSHING tree's own
tv/.second_eye.jsonl. A fresh push worktree has none, so v3784 was refused ("v3783 OWES A LOOK - nothing was ever
recorded"), and push #13's worktree held the v3778 look, which died with that worktree. The ledger now lives in git's
COMMON dir, found by reading .git (never by running git), and the first resolution in a process folds every checkout's
own ledger in. This law drives all of it on FIXTURES - a main checkout and two linked worktrees in its own scratch, one
pointer absolute and one relative - and runs the module itself in a subprocess inside that fixture:

  1. a worktree, the main checkout and a relative-pointer worktree all resolve to ONE file in the common dir;
  2. a tree with no git dir keeps its own tv/.second_eye.jsonl, and says why;
  3. every checkout's rows are folded: a worktree's extra row arrives, a row one checkout holds twice is held twice, a
     row with no newline is closed, no source is written, and a second fold adds nothing; a row old code appends to a
     checkout's file later is folded the next time;
  4. the first READ in a process folds (the module run in the fixture, its env seam unset) - and importing
     alone writes nothing under git's dir;
  5. `--gate` reads the machine's ledger and ignores TV_SECOND_EYE_LEDGER, which still names a fixture without it.
Nothing of his is read or written: every path is under this law's scratch, and every git variable a hook could leak is
scrubbed from the subprocesses. RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402  (the docstrings carry non-ASCII)
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import second_eye_ledger as L  # noqa: E402

HOUR_AGO = time.time() - 3600


def _row(version, ts, model="grok-4-1-fast-reasoning", verdict="clean"):
    return json.dumps({"version": version, "model": model, "verdict": verdict, "reached": True,
                       "answerHead": "a look at %s" % version, "ts": ts}, ensure_ascii=False)


def _write(path, lines, newline_at_end=True):
    d = os.path.dirname(path)
    if not os.path.isdir(d):
        os.makedirs(d)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + ("\n" if newline_at_end else ""))
    os.utime(path, (HOUR_AGO, HOUR_AGO))      # settled: its signature may stand for its bytes


def _lines(path):
    with io.open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip()]


def _bytes(path):
    with io.open(path, "rb") as fh:
        return fh.read()


def _clean_env(**extra):
    """A child's environment with every GIT_* a hook could leak removed (REG-2392), the module's seam unset, and git
    unable to climb out of the scratch."""
    env = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))
    env.pop("TV_SECOND_EYE_LEDGER", None)
    env["GIT_CEILING_DIRECTORIES"] = tempfile.gettempdir()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(extra)
    return env


class _Machine(object):
    """main/ (a .git directory) + wt1/ (absolute gitdir pointer) + wt2/ (relative pointer), all in one scratch."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="se-machine-")
        self.main = os.path.join(self.root, "main")
        self.common = os.path.join(self.main, ".git")
        os.makedirs(os.path.join(self.main, "tv"))
        os.makedirs(os.path.join(self.common, "worktrees"))
        self.wt1 = self._worktree("wt1", relative=False)
        self.wt2 = self._worktree("wt2", relative=True)
        self.ledger = os.path.join(self.common, "second_eye.jsonl")

    def _worktree(self, name, relative):
        root = os.path.join(self.root, name)
        meta = os.path.join(self.common, "worktrees", name)
        os.makedirs(os.path.join(root, "tv"))
        os.makedirs(meta)
        with io.open(os.path.join(meta, "gitdir"), "w", encoding="utf-8") as fh:
            fh.write(os.path.join(root, ".git") + "\n")
        with io.open(os.path.join(meta, "commondir"), "w", encoding="utf-8") as fh:
            fh.write("../..\n")
        ptr = os.path.relpath(meta, root) if relative else meta
        with io.open(os.path.join(root, ".git"), "w", encoding="utf-8") as fh:
            fh.write("gitdir: %s\n" % ptr)
        return root

    def own(self, checkout):
        return os.path.join(checkout, "tv", ".second_eye.jsonl")

    def install(self, checkout):
        """The module under test (and the walk it reads .git with), copied into one checkout's tv/."""
        for f in ("second_eye_ledger.py", "prove_record.py"):
            shutil.copy2(os.path.join(HERE, f), os.path.join(checkout, "tv", f))

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


class TheSecondEyeLedgerIsOnePerMachine(unittest.TestCase):

    def setUp(self):
        self.m = _Machine()
        self.addCleanup(self.m.close)

    # 1 ---------------------------------------------------------------------------------------------------------------
    def test_every_checkout_resolves_to_one_file_in_the_common_dir(self):
        want = os.path.realpath(self.m.ledger)
        for checkout in (self.m.wt1, self.m.wt2, self.m.main):
            path, why = L.machine_ledger(checkout)
            self.assertIsNone(why, "%s could not find its git dir: %s" % (checkout, why))
            self.assertEqual(os.path.realpath(path), want,
                             "%s resolves its ledger to %s - not the machine's one file in git's common dir, so a "
                             "look recorded there dies with the checkout" % (os.path.basename(checkout), path))
        self.assertNotIn(os.path.realpath(self.m.wt1), want, "PREMISE: the machine's ledger is outside every work tree")

    # 2 ---------------------------------------------------------------------------------------------------------------
    def test_a_tree_with_no_git_dir_keeps_its_own_file_and_says_so(self):
        bare = os.path.join(self.m.root, "sandbox")
        os.makedirs(os.path.join(bare, "tv"))
        path, why = L.machine_ledger(bare)
        self.assertEqual(os.path.realpath(path), os.path.realpath(os.path.join(bare, "tv", ".second_eye.jsonl")))
        self.assertTrue(why and "no .git" in why, "a tree with no git dir did not say why it keeps its own file: %r"
                        % (why,))

    # 3 ---------------------------------------------------------------------------------------------------------------
    def test_every_checkout_row_is_folded_and_none_is_dropped(self):
        a, b, c = _row("v0001", 1000), _row("v0002", 2000), _row("v0003", 3000)
        twice = _row("v0004", 4000, verdict="findings")
        extra = _row("v0005", 5000)                      # only the worktree holds it: the look a removal would lose
        tail = _row("v0006", 6000)                       # written by a writer killed before its newline
        _write(self.m.own(self.m.main), [a, b, twice, twice, c])
        _write(self.m.own(self.m.wt1), [a, b, c, extra])
        _write(self.m.own(self.m.wt2), [a, "{not json", tail], newline_at_end=False)
        _write(self.m.ledger, [a])
        before = dict((p, _bytes(p)) for p in
                      (self.m.own(self.m.main), self.m.own(self.m.wt1), self.m.own(self.m.wt2)))

        sources = L.checkout_ledgers(self.m.wt1)
        self.assertEqual(sorted(os.path.realpath(s) for s in sources), sorted(os.path.realpath(p) for p in before),
                         "the fold does not find every checkout's own ledger (main + both worktrees)")
        added = L.fold(self.m.ledger, sources)
        got = _lines(self.m.ledger)

        union = set()
        for p in before:
            union |= set(_lines(p))
        self.assertEqual(set(got), union, "distinct rows after the fold are not the union of every checkout's rows")
        self.assertIn(extra, got, "the worktree's own look was not folded - it would die with the worktree")
        self.assertEqual(got.count(twice), 2, "a row main holds TWICE is held %d time(s) - a fold never drops one"
                         % got.count(twice))
        self.assertEqual(got.count(a), 1, "a row every checkout holds once was folded %d times" % got.count(a))
        self.assertIn(tail, got, "a row with no newline at the end of its file was not folded whole")
        self.assertEqual(added, len(got) - 1)
        stamps = [json.loads(x)["ts"] for x in got if x.startswith("{\"")]
        self.assertEqual(stamps, sorted(stamps), "the fold broke the ledger's time order: %r" % stamps)
        for p, raw in before.items():
            self.assertEqual(_bytes(p), raw, "the fold WROTE a checkout's own ledger: %s" % p)

        self.assertEqual(L.fold(self.m.ledger, sources), 0, "a second fold over unchanged sources added rows")
        later = _row("v0007", 7000)                      # old code still appending to its checkout's own file
        with io.open(self.m.own(self.m.wt2), "a", encoding="utf-8") as fh:
            fh.write("\n" + later + "\n")
        self.assertEqual(L.fold(self.m.ledger, sources), 1, "a row appended to a checkout's file later was not folded")
        self.assertIn(later, _lines(self.m.ledger))

    # 4 ---------------------------------------------------------------------------------------------------------------
    def test_the_first_read_in_a_process_folds_every_checkout(self):
        a, extra = _row("v0011", 1000), _row("v0012", 2000)
        _write(self.m.own(self.m.main), [a])
        _write(self.m.own(self.m.wt2), [a, extra])
        self.m.install(self.m.wt1)
        prog = ("import os, second_eye_ledger as L\n"
                "print(L.LEDGER_PATH)\n"
                "print('AFTER-IMPORT', os.path.exists(L.LEDGER_PATH))\n"
                "print('ROWS', len(L._rows()))\n")
        out = subprocess.run([sys.executable, "-c", prog], cwd=os.path.join(self.m.wt1, "tv"), env=_clean_env(),
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr[-800:])
        said = out.stdout.splitlines()
        self.assertEqual(os.path.realpath(said[0]), os.path.realpath(self.m.ledger),
                         "the module run in a worktree did not resolve the machine's ledger: %r" % out.stdout)
        self.assertEqual(said[1], "AFTER-IMPORT False",
                         "importing the module already wrote under git's dir - the gate ledger never carries a law "
                         "that reads git's own files, and ~36 laws import this module only for fixtures")
        self.assertEqual(said[2], "ROWS 2", "the first read did not see every checkout's rows: %r" % said)
        self.assertEqual(sorted(_lines(self.m.ledger)), sorted([a, extra]),
                         "the first read in a process did not fold every checkout's rows in")

    # 5 ---------------------------------------------------------------------------------------------------------------
    def test_the_gate_reads_the_machine_ledger_and_ignores_the_variable(self):
        self.m.install(self.m.wt1)
        decoy = os.path.join(self.m.root, "decoy.jsonl")
        _write(decoy, [_row("v0042", 1000)])           # a look for v0042 that exists ONLY in the decoy
        script = os.path.join(self.m.wt1, "tv", "second_eye_ledger.py")

        def check(*flags):
            return subprocess.run([sys.executable, script, "--check", "v0042"] + list(flags),
                                  cwd=self.m.wt1, env=_clean_env(TV_SECOND_EYE_LEDGER=decoy), capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=60)

        gated = check("--gate")
        self.assertEqual(gated.returncode, 1,
                         "--gate passed on a look that lives only in TV_SECOND_EYE_LEDGER's file - a one-word prefix "
                         "on the push command would disarm the gate: %s" % (gated.stdout + gated.stderr)[-600:])
        seam = check()
        self.assertEqual(seam.returncode, 0, "without --gate the seam must still name a fixture: %s"
                         % (seam.stdout + seam.stderr)[-600:])
        _write(self.m.own(self.m.main), [_row("v0042", 1000)])  # the look, recorded in the main checkout
        gated = check("--gate")
        self.assertEqual(gated.returncode, 0,
                         "--gate did not see a look the main checkout holds, from a worktree: %s"
                         % (gated.stdout + gated.stderr)[-600:])
        self.assertTrue(os.path.isfile(self.m.ledger), "--gate did not fold the checkouts into the machine's ledger")


class TheShipGateIsArmed(unittest.TestCase):
    """v3866 - his ruling 2026-11-05 ("Lift after v3865"): hooks/pre-push waived the second-family look from 2026-11-02,
    printing a waiver and exiting 0, and v3856-v3864 shipped with no recorded look. The ship gate asks this ledger again
    and refuses on its answer; the waiver line is gone from the code (comments stripped, so the history may say it)."""

    def test_the_hook_asks_the_ledger_and_refuses_on_its_answer(self):
        with io.open(os.path.join(os.path.dirname(HERE), "hooks", "pre-push"), encoding="utf-8") as fh:
            code = "\n".join(l for l in fh.read().splitlines() if not l.lstrip().startswith("#"))
        call = 'python3 "$REPO/tv/second_eye_ledger.py" --check "$_prev_ver" --gate; then'
        self.assertEqual(code.count(call), 1, "the ship gate no longer asks the second-eye ledger")
        self.assertNotIn("is waived for now", code, "the second-eye waiver is back in the hook")


RED_PROOF = [
    {"why": "v3866 - the second-eye ship gate is waived again: it prints and exits 0",
     "file": "hooks/pre-push",
     "find": "         python3 \"$REPO/tv/second_eye_ledger.py\" --check \"$_prev_ver\" --gate; then\n",
     "replace": "         bash -c \"echo second eye on $_prev_ver is waived for now\"; then\n",
     "matches": 1},
    {"why": "#178 - the ledger resolves to the checkout's own tv/.second_eye.jsonl again (the HERE path), so a fresh "
            "push worktree has none and a look recorded in a worktree dies with it",
     "file": "second_eye_ledger.py",
     "find": "        return os.path.join(common, MACHINE_NAME), None\n",
     "replace": "        return os.path.join(repo, \"tv\", CHECKOUT_NAME), None\n",
     "matches": 1},
    {"why": "#178 - the fold skips the worktrees: main's rows arrive and a worktree's own look (v3778's shape) is lost",
     "file": "second_eye_ledger.py",
     "find": "        for root in _worktree_roots(common):\n",
     "replace": "        for root in []:\n",
     "matches": 1},
    {"why": "#178 - the fold dedupes to a set: a row one checkout holds twice is folded once, so a fold drops rows",
     "file": "second_eye_ledger.py",
     "find": "            if seen[r] > have[r]:\n",
     "replace": "            if have[r] == 0:\n",
     "matches": 1},
    {"why": "v2143.1 / #178 - --gate honours TV_SECOND_EYE_LEDGER again: a one-word prefix on the push disarms the gate",
     "file": "second_eye_ledger.py",
     "find": "        LEDGER_PATH = _MACHINE_LEDGER\n",
     "replace": "        LEDGER_PATH = os.environ.get(\"TV_SECOND_EYE_LEDGER\") or _MACHINE_LEDGER\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
