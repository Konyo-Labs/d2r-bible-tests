#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3899 (card #200, REG-3727) - THE PRE-FLIGHT RUNS THE LIKELY REDS FIRST: what failed lately, what is new, what changed.

MEASURED on v3898's pre-flight runs (11-11): the laws ran in cost order and a version's NEW laws - no CI cost yet - after all
1,686 cheap ones. Run d's only red came at minute 22; run b's five at minutes 6-21. And the same laws-about-laws had failed on
v3896, v3897 and v3898 (the no-scratch-dirs law, the shard balance file, the ci push). Any red voids the run, so each one
found late cost every minute before it. Now preflight() puts first: the laws a recent pre-flight log said failed, the
version's new (uncosted) laws, and the laws whose own file the version changed - the same set, only the order moves.

DRIVEN: recent_reds over fixture logs, first_order over a fixture list, and the real preflight() over a fixture tree whose
law runner records the order it was handed; the history and the changed set are injected, so this law never reads this
PC's own ship logs (REG-3709's class). RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import preflight as PF  # noqa: E402


class TheLogsNameWhatFailed(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pfreds_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _log(self, name, lines, age_s):
        p = os.path.join(self.tmp, name)
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        t = time.time() - age_s
        os.utime(p, (t, t))

    def test_a_failed_law_is_named_and_the_summary_is_not(self):
        self._log("preflight_v1_b.log", ["preflight: [5m] 400 of 1711 laws", "preflight: RED test_x",
                                         "preflight: TIMEOUT test_y", "preflight: RED live-panel",
                                         "preflight: RED - 3 finding(s); GitHub would have spent a round on them:",
                                         "   RED test_z: AssertionError: 4 != 3"], 10)
        self.assertEqual(PF.recent_reds(self.tmp), {"test_x", "test_y", "live-panel"})

    def test_only_the_newest_runs_are_read(self):
        self._log("preflight_v1.log", ["preflight: RED test_old"], 500)
        self._log("preflight_v2.log", ["preflight: RED test_new"], 10)
        self.assertEqual(PF.recent_reds(self.tmp, last=1), {"test_new"})
        self.assertEqual(PF.recent_reds(self.tmp, last=2), {"test_new", "test_old"})

    def test_no_log_is_an_empty_hint_never_a_crash(self):
        self.assertEqual(PF.recent_reds(os.path.join(self.tmp, "no_such_dir")), set())


class TheOrderMovesTheSetDoesNot(unittest.TestCase):

    def test_failed_then_new_then_changed_then_the_rest(self):
        names = ["test_a", "test_b", "test_c", "test_d", "test_e"]
        out, n = PF.first_order(names, recent={"test_d", "test_not_here"}, new=["test_e"], changed=["test_b", "test_d"])
        self.assertEqual(out, ["test_d", "test_e", "test_b", "test_a", "test_c"])
        self.assertEqual(n, 3)
        self.assertEqual(sorted(out), sorted(names), "the reorder added or dropped a law")

    def test_baseline_no_hint_keeps_the_order(self):
        names = ["test_a", "test_b", "test_c"]
        self.assertEqual(PF.first_order(names), (names, 0))


class ThePreflightHandsTheRunnerTheLikelyRedsFirst(unittest.TestCase):

    def test_the_runner_sees_the_failed_and_changed_laws_first(self):
        tmp = tempfile.mkdtemp(prefix="pforder_")
        self.addCleanup(shutil.rmtree, tmp, True)
        laws = ["test_a", "test_b", "test_c", "test_d"]
        with io.open(os.path.join(tmp, "gate_costs.json"), "w", encoding="utf-8") as fh:
            json.dump({"costs": dict((n, 1.0) for n in laws)}, fh)
        for n in laws:
            with io.open(os.path.join(tmp, n + ".py"), "w", encoding="utf-8") as fh:
                fh.write("print('ok')\n")
        seen, said = [], []

        def runner(names):
            seen.extend(names)
            return [(n, "ok", "") for n in names]

        code, reds = PF.preflight(prove=False, here=tmp, say=said.append, _laws=runner, _registry={},
                                  _anchors=lambda: (True, ""), _demos_due=lambda: (False, ""),
                                  _second_eye=lambda: (True, ""), _render_due=lambda: (False, ""),
                                  _recent=lambda: {"test_d"}, _changed=lambda: ["test_c"])
        self.assertEqual(code, 0, "\n".join(said))
        self.assertEqual(seen[:2], ["test_d", "test_c"], "the law runner was not handed the likely reds first: %r" % seen)
        self.assertEqual(sorted(seen), laws)
        self.assertTrue(any("go first" in l for l in said), "the pre-flight does not say what it moved")


RED_PROOF = [
    {"why": "REG-3727 (#200) - the pre-flight goes back to cost order: a recent failure, a new law and a changed law wait "
            "behind every cheap one again (v3898 run d: its only red at minute 22)",
     "file": "tv/preflight.py",
     "find": "    s[\"run\"], _lead = first_order(s[\"run\"], recent=_rec, new=un_run, changed=_chg)\n",
     "replace": "    _lead = 0\n",
     "matches": 1},
    {"why": "REG-3727 (#200) - the log reader stops naming the failed laws",
     "file": "tv/preflight.py",
     "find": "                    if m:\n                        out.add(m.group(1))\n",
     "replace": "                    if m and False:\n                        out.add(m.group(1))\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
