# -*- coding: utf-8 -*-
"""v3848 SPEED - `run_gates.py --rerun-failed` RUNS ONLY WHAT THE LAST RUN LEFT RED.

v3847 spent 5+ h re-running full sets after a red. The rule (FAST_GATE.md) is: after a red run, rerun ONLY the
failed gates plus the gates the fix touches. This law pins the mechanism: a run records its red names in this
worktree's git dir; --rerun-failed reads them back (a suffix like '(undeclared SKIP)' is the same gate), adds any
--only names, refuses when nothing is recorded, and refuses to combine with a set-picking flag.

v3849 - a green --only or --fast run must not replace that set. A selection merges: drop only names that
ran green, keep names that did not run, add names that ran red. A full run (no selection, or --fast that
fell through to every gate) is what replaces the set. A shard still writes nothing.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_gates as R  # noqa: E402


def _row(name, status):
    g = type("G", (), {"name": name, "skip_ok": ()})()
    return (g, status, 0.01, "", "")


def _drive(argv, rows):
    """Run main() up to the failed-set write, without a lock, a tree walk, or port 17772."""
    buf = io.StringIO()

    def fake_run(only=None, live_watch=True, live_writer=None, ledger=None):
        return list(rows)

    with mock.patch.object(R, "_claim_the_tree", lambda: None), \
            mock.patch.object(R, "_parallel_light", lambda *a, **k: (None, None)), \
            mock.patch.object(R, "_console_writes_here", lambda *a, **k: (False, "mocked")), \
            mock.patch.object(R, "_console_is_running", lambda *a, **k: False), \
            mock.patch.object(R, "_external_writer", lambda *a, **k: []), \
            mock.patch.object(R, "_sweep_in_progress", lambda *a, **k: False), \
            mock.patch.object(R, "_live_fingerprint", lambda: {}), \
            mock.patch.object(R, "_tree_fingerprint", lambda: {}), \
            mock.patch.object(R, "run", fake_run), \
            redirect_stdout(buf):
        rc = R.main(["run_gates.py"] + list(argv))
    return rc, buf.getvalue()


class ARerunRunsOnlyTheLastReds(unittest.TestCase):
    def setUp(self):
        fd, self.p = tempfile.mkstemp(prefix="tvd-lastfailed-", suffix=".json")
        os.close(fd)
        os.unlink(self.p)
        self.addCleanup(lambda: os.path.exists(self.p) and os.unlink(self.p))
        m = mock.patch.object(R, "_last_failed_path", lambda: self.p)
        m.start()
        self.addCleanup(m.stop)

    def test_the_recorded_reds_come_back_as_gate_names(self):
        R._write_last_failed(["visual-lock", "visual-lock (undeclared SKIP)", "test_control"], "abc")
        names, why = R._read_last_failed()
        self.assertEqual(names, ["visual-lock", "test_control"], why)

    def test_nothing_recorded_refuses(self):
        names, why = R._read_last_failed()
        self.assertIsNone(names, "a rerun with no recorded run must refuse, never run every gate")

    def test_rerun_runs_exactly_the_reds_plus_the_named(self):
        R._write_last_failed(["visual-lock"], "abc")
        seen = {}

        def fake_run(only, **kw):
            seen["only"] = list(only or [])
            raise SystemExit(0)
        with mock.patch.object(R, "run", fake_run), mock.patch.object(R, "_claim_the_tree", lambda: None), \
                mock.patch.object(R, "_parallel_light", lambda a, o: (None, None)), \
                mock.patch.object(R, "_console_writes_here", lambda *a, **k: (False, "mocked")), \
                mock.patch.object(R, "_console_is_running", lambda *a, **k: False), \
                mock.patch.object(R, "_external_writer", lambda *a, **k: []), \
                mock.patch.object(R, "_sweep_in_progress", lambda *a, **k: False), \
                mock.patch.object(R, "_live_fingerprint", lambda: {}), \
                mock.patch.object(R, "_tree_fingerprint", lambda: {}):
            with self.assertRaises(SystemExit):
                R.main(["run_gates.py", "--rerun-failed", "--only", "test_control"])
        self.assertEqual(seen.get("only"), ["visual-lock", "test_control"])

    def test_it_does_not_combine_with_a_set_picking_flag(self):
        R._write_last_failed(["visual-lock"], "abc")
        for flag in ("--full", "--fast"):
            self.assertEqual(R.main(["run_gates.py", "--rerun-failed", flag]), 2, flag)

    def test_the_cli_refuses_with_nothing_recorded(self):
        env = dict(os.environ, GIT_DIR=tempfile.mkdtemp(prefix="tvd-nogit-"))
        p = subprocess.run([sys.executable, os.path.join(HERE, "run_gates.py"), "--rerun-failed"],
                           cwd=os.path.dirname(HERE), env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 2, (p.stdout + p.stderr)[-800:])
        self.assertIn("NO gate ran", p.stdout)

    def test_merge_drops_only_a_name_that_ran_green(self):
        got = R._merge_failed_names(
            ["visual-lock", "test_control (undeclared SKIP)"],
            ["test_control"],
            ["visual-lock"])
        self.assertEqual(got, ["test_control"])

    def test_merge_keeps_a_name_this_run_did_not_touch(self):
        self.assertEqual(R._merge_failed_names(["visual-lock", "test_control"], [], ["test_control"]),
                         ["visual-lock"])

    def test_a_green_only_run_keeps_reds_it_did_not_run(self):
        R._write_last_failed(["visual-lock", "test_control"], "abc")
        rc, out = _drive(["--only", "test_control"], [_row("test_control", "PASS")])
        self.assertEqual(rc, 0, out[-800:])
        names, _why = R._read_last_failed()
        self.assertEqual(names, ["visual-lock"], "a green --only run replaced the recorded red set")

    def test_a_green_only_run_drops_the_name_that_passed(self):
        R._write_last_failed(["test_control"], "abc")
        rc, out = _drive(["--only", "test_control"], [_row("test_control", "PASS")])
        self.assertEqual(rc, 0, out[-800:])
        names, _why = R._read_last_failed()
        self.assertEqual(names, [])

    def test_a_green_only_run_does_not_invent_an_empty_red_set(self):
        self.assertFalse(os.path.exists(self.p))
        rc, out = _drive(["--only", "test_control"], [_row("test_control", "PASS")])
        self.assertEqual(rc, 0, out[-800:])
        self.assertFalse(os.path.exists(self.p), "a green --only run created an empty red set; --rerun-failed would exit 0")

    def test_a_red_only_run_records_its_red_when_nothing_was_recorded(self):
        rc, out = _drive(["--only", "test_control"], [_row("test_control", "FAIL")])
        self.assertEqual(rc, 1, out[-800:])
        names, _why = R._read_last_failed()
        self.assertEqual(names, ["test_control"])

    def test_an_unreadable_red_set_survives_a_partial_run(self):
        with open(self.p, "w", encoding="utf-8") as f:
            f.write("{not json")
        with open(self.p, encoding="utf-8") as f:
            before = f.read()
        rc, out = _drive(["--only", "test_control"], [_row("test_control", "FAIL")])
        self.assertEqual(rc, 1, out[-800:])
        with open(self.p, encoding="utf-8") as f:
            self.assertEqual(f.read(), before)

    def test_a_full_run_replaces_the_recorded_set(self):
        R._write_last_failed(["visual-lock", "test_control"], "abc")
        rc, out = _drive([], [_row("test_control", "FAIL")])
        self.assertEqual(rc, 1, out[-800:])
        names, _why = R._read_last_failed()
        self.assertEqual(names, ["test_control"])

    def test_a_carried_gate_is_not_dropped(self):
        R._write_last_failed(["test_control"], "abc")
        rc, out = _drive(["--only", "test_control"], [_row("test_control", "CARRY")])
        self.assertEqual(rc, 0, out[-800:])
        names, _why = R._read_last_failed()
        self.assertEqual(names, ["test_control"], "a carry did not run; it must not clear a recorded red")

    def test_a_green_fast_run_keeps_reds_it_did_not_run(self):
        import fast_gates
        R._write_last_failed(["visual-lock", "test_control"], "abc")
        with mock.patch.object(fast_gates, "changed", lambda base="origin/main": []), \
                mock.patch.object(fast_gates, "select", lambda gates, files, base="origin/main": (["test_control"], "pinned")):
            rc, out = _drive(["--fast"], [_row("test_control", "PASS")])
        self.assertEqual(rc, 0, out[-800:])
        names, _why = R._read_last_failed()
        self.assertEqual(names, ["visual-lock"])

    def test_a_fast_run_of_every_gate_replaces_the_set(self):
        import fast_gates
        R._write_last_failed(["visual-lock"], "abc")
        with mock.patch.object(fast_gates, "changed", lambda base="origin/main": []), \
                mock.patch.object(fast_gates, "select", lambda gates, files, base="origin/main": (None, "every gate")):
            rc, out = _drive(["--fast"], [_row("test_control", "FAIL")])
        self.assertEqual(rc, 1, out[-800:])
        names, _why = R._read_last_failed()
        self.assertEqual(names, ["test_control"], "a --fast run of every gate kept a red from before it")

    def test_a_shard_does_not_write_the_red_set(self):
        R._write_last_failed(["visual-lock"], "abc")
        rc, out = _drive(["--shard", "1/2"], [_row("test_control", "FAIL")])
        self.assertEqual(rc, 1, out[-800:])
        names, _why = R._read_last_failed()
        self.assertEqual(names, ["visual-lock"])


RED_PROOF = [
    {"why": "v3848 - a '(undeclared SKIP)' red is read as an unknown gate name",
     "file": "run_gates.py",
     "find": "        n = n.split(\" (\")[0]\n",
     "replace": "",
     "matches": 1},
    {"why": "v3848 - --rerun-failed ignores the recorded reds",
     "file": "run_gates.py",
     "find": "        only = a.only = _rf\n",
     "replace": "        only = a.only = [n for n in (a.only or [])]\n",
     "matches": 1},
    {"why": "v3848 - --rerun-failed combines with --full",
     "file": "run_gates.py",
     "find": "        if a.shard or a.full or a.fast:\n",
     "replace": "        if a.shard:\n",
     "matches": 1},
    {"why": "v3849 - a green --only run replaces the recorded red set",
     "file": "run_gates.py",
     "find": "        if a.only:  # PARTIAL-RED-SET a selection merges; it does not replace the recorded reds\n",
     "replace": "        if False:  # PARTIAL-RED-SET a selection merges; it does not replace the recorded reds\n",
     "matches": 1},
    {"why": "v3849 - a partial run keeps a gate that ran green",
     "file": "run_gates.py",
     "find": "        if b in passed:  # PARTIAL-RED-SET drop only a name that ran green\n            continue\n",
     "replace": "\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
