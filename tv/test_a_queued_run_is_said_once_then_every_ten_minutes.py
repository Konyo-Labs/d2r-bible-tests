# -*- coding: utf-8 -*-
"""v3902 (REG-3773, #200) - A QUEUED RUN IS SAID ONCE, THEN EVERY TEN MINUTES - NEVER EVERY PASS.

MEASURED 11-12 07:06: v3900's ship log carried (from the vouch wait's shard watch, every 60 s+) "ship: REG-3654 QUEUED - Publish ... run 43096436723 queued 29847s ..." on
every 80 s pass - 30+ times in 40 minutes - and a watch on the log drowned in it. The ship now hands the yield rule its own
{run id: when said}: a run is said when first seen queued, then once every QUEUED_SAY_EVERY_S while it stays queued, and a
pass that cancelled something is always said. Any other caller (no `quiet`) says every pass, as before.

DRIVEN: the real ship_yield.yield_to_ship over fixture runs on a moving clock; the ship's two call sites by their source.
RED_PROOF below.
"""
import inspect
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import ship_yield as SY  # noqa: E402
import ship_when_green as SW  # noqa: E402

PUBLISH = "Publish — gates, review, then deploy"
NOW = 1794459960.0
Q = [{"headBranch": "main", "status": "queued", "databaseId": 43200000001, "name": PUBLISH, "headSha": "a" * 40,
      "createdAt": "2026-11-12T05:00:00Z"}]


def _passes(quiet, n, step=80):
    said = []
    for i in range(n):
        SY.yield_to_ship(run=None, say=said.append, runs=Q, now=NOW + i * step, sweep=False, quiet=quiet)
    return [l for l in said if "REG-3654 QUEUED" in l]


class AQueuedRunIsSaidOnceThenEveryTenMinutes(unittest.TestCase):

    def test_baseline_no_quiet_says_every_pass(self):
        self.assertEqual(len(_passes(None, 5)), 5, "PREMISE: a caller with no quiet no longer says every pass")

    def test_the_ship_says_it_once_in_ten_minutes(self):
        """* THE POINT - 40 minutes of 80 s passes: said at 0, 10, 20 and 30 minutes, never 30 times"""
        lines = _passes({}, 30)
        self.assertEqual(len(lines), 4, "a queued run was said %d times in 40 min of passes" % len(lines))

    def test_the_ship_hands_its_quiet_to_both_per_pass_calls(self):
        """the vouch wait (shard_watch, every 60 s - the one that wrote the 30 lines) and the Publish watch"""
        import shard_watch as SHW
        src = "\n".join(l.split("#", 1)[0] for l in inspect.getsource(SW).split("\n"))
        self.assertEqual(src.count("quiet=QUEUED_SAID"), 1, "the Publish watch says a queued run every pass again")
        shw = "\n".join(l.split("#", 1)[0] for l in inspect.getsource(SHW.watch_jobs_live).split("\n"))
        self.assertEqual(shw.count('quiet=getattr(SW, "QUEUED_SAID", None)'), 1, "the vouch wait says a queued run every pass again")


RED_PROOF = [
    {"why": "REG-3773 - the ship's queued line is said every 80 s pass again",
     "file": "tv/ship_yield.py",
     "find": "    if quiet is not None and not cancelled:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3773 - the vouch wait stops handing the yield rule the ship's quiet (the 80 s line again)",
     "file": "tv/shard_watch.py",
     "find": "            SY.protect_priority(run=run, say=say, now=clock(), quiet=getattr(SW, \"QUEUED_SAID\", None))",
     "replace": "            SY.protect_priority(run=run, say=say, now=clock())",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
