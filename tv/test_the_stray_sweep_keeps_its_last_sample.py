# -*- coding: utf-8 -*-
"""v3902 (REG-3774) - THE STRAY-PROCESS SWEEP KEEPS ITS LAST SAMPLE ACROSS PASSES THAT RUN IN DIFFERENT PROCESSES.

MEASURED 11-12 on his Mac's console doctor: "stray processes" UNKNOWN for 6 days across 885 asks - "only ONE cpu sample is
available ... Ask again in a moment". The sweep's second sample comes from the PREVIOUS call (never a sleep), kept in a
module-level dict - and since REG-2987 a console runs each doctor pass in a SHORT-LIVED CHILD, so that dict died with every
pass and the second sample never existed. The last sample now also lives on disk (TV_ORPHAN_SAMPLE in a law), and a pass
with no memory copy compares against it while it is younger than PREV_MAX_AGE_S. An old, corrupt or absent file is no
previous sample: UNKNOWN, never a guess.

DRIVEN: the real my_orphans.suspects() - its POSIX path over a fake ps and clock, its Windows path through the Windows law's
own harness - with the in-memory sample cleared between the two passes, as a new child would have it. RED_PROOF below.
"""
import io
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import my_orphans as MO  # noqa: E402
import test_stray_processes_are_measured_on_windows as W  # noqa: E402

ONE = "only ONE cpu sample"
LISTING = ("  PID  PPID  %CPU     ELAPSED COMMAND\n"
           " 4242     1  99.0    01:10:00 python3 -c while-1\n")


class _R(object):
    def __init__(self, out):
        self.returncode, self.stdout, self.stderr = 0, out, ""


class ThePosixSweep(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="tvd-orphan-sample-law-")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.clock = [100000.0]
        for name, val in (("_platform", lambda: "darwin"), ("_cpu_sample", lambda: {"4242": 99.0}),
                          ("time", types.SimpleNamespace(time=lambda: self.clock[0], sleep=lambda s: None))):
            p = mock.patch.object(MO, name, val)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(MO.subprocess, "run", lambda *a, **k: _R(LISTING))
        p.start()
        self.addCleanup(p.stop)
        p = mock.patch.dict(os.environ, {MO.SAMPLE_ENV: os.path.join(self.d, "sample.json")})
        p.start()
        self.addCleanup(p.stop)
        saved = dict(MO._LAST_SAMPLE)
        self.addCleanup(lambda: (MO._LAST_SAMPLE.clear(), MO._LAST_SAMPLE.update(saved)))
        MO._LAST_SAMPLE.update(at=0.0, cpu={})

    def _pass(self, at):
        """one doctor pass in a NEW child: the in-memory sample is gone"""
        MO._LAST_SAMPLE.update(at=0.0, cpu={})
        self.clock[0] = at
        return MO.suspects()

    def _said(self, rows):
        return " | ".join(str(r.get("why") or "") for r in rows if not r.get("pid"))

    def test_baseline_with_no_kept_sample_every_pass_is_one_sample(self):
        self._pass(100000.0)
        os.remove(os.path.join(self.d, "sample.json"))
        self.assertIn(ONE, self._said(self._pass(100600.0)), "PREMISE: a pass with nothing kept judged anyway")

    def test_a_new_childs_pass_compares_against_the_last_ones(self):
        """* THE POINT - 885 asks in 6 days, every one UNKNOWN"""
        self.assertIn(ONE, self._said(self._pass(100000.0)), "the very first pass did not say it had one sample")
        rows = self._pass(100600.0)
        self.assertNotIn(ONE, self._said(rows), "a pass in a new process still has only one sample")
        self.assertEqual([r.get("pid") for r in rows if r.get("pid")], ["4242"], rows)

    def test_a_sample_older_than_the_bound_or_corrupt_is_no_sample(self):
        self._pass(100000.0)
        self.assertIn(ONE, self._said(self._pass(100000.0 + MO.PREV_MAX_AGE_S + 60)), "a stale sample was judged against")
        with io.open(os.path.join(self.d, "sample.json"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertIn(ONE, self._said(self._pass(100700.0)), "a corrupt file read as a sample")


class TheWindowsSweep(W._Sweep):

    def test_a_new_childs_pass_compares_against_the_last_ones(self):
        self.births.update({"4242": W.T0 - 3600})
        self.cmds.update({"4242": "python.exe -c \"while 1: pass\""})
        self.samples[:] = [{"4242": W._p(100.0)}, {"4242": W._p(400.0)}]
        self.clock[0] = W.T0
        MO.suspects()
        MO._LAST_WIN.update(at=0.0, cpu={})          # a new child: the memory copy is gone
        self.clock[0] = W.T1
        rows = MO.suspects()
        self.assertEqual([r.get("pid") for r in rows if r.get("pid")], ["4242"], rows)


RED_PROOF = [
    {"why": "REG-3774 - the POSIX sweep stops keeping its sample: every doctor pass in a child is one sample again",
     "file": "tv/my_orphans.py",
     "find": "    _keep_sample(\"ps\", _cur, _now)\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3774 - the Windows sweep stops keeping its sample",
     "file": "tv/my_orphans.py",
     "find": "    _keep_sample(\"win\", cur, now)\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3774 - a kept sample of any age is judged against",
     "file": "tv/my_orphans.py",
     "find": "        if isinstance(cpu, dict) and cpu and 0 < now - at <= PREV_MAX_AGE_S:\n",
     "replace": "        if isinstance(cpu, dict) and cpu:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
