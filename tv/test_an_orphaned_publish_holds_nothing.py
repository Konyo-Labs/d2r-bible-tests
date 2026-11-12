# -*- coding: utf-8 -*-
"""v3902 (REG-3766, #200) - A PUBLISH GITHUB PASSED OVER HOLDS NOTHING, AND IS SAID ONCE.

MEASURED 11-12 07:00 IST: Publish 43096436723 (a v3898 fix commit on main) sat QUEUED with no jobs from 11-11 22:30;
Publish 43137497174 (v3899, created later) ran past it and SUCCEEDED, and v3899 went live. The group runs one Publish at
a time, so a later Publish that started or finished means GitHub passed the waiting one over. Counted as live, it armed
the yield rule for 8.5 hours: may_push refused every grok/ and dry/ push "a real ship is live", and the v3900 ship log
printed it as REG-3654 QUEUED every 80 s. Now a waiting Publish with a later Publish in progress or completed is
ORPHANED: not live, not queued priority, named once with the run that went past it. A waiting Publish with only EARLIER
or still-waiting siblings stays live (the baseline below proves the case distinguishes).

DRIVEN: the real ship_yield functions over fixture run rows. RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import ship_yield as SY  # noqa: E402

PUBLISH = "Publish — gates, review, then deploy"
NOW = 1794459960.0  # 2026-11-12 05:06 UTC


def _run(status, rid, sha, created, conclusion="", branch="main", name=PUBLISH):
    row = {"headBranch": branch, "status": status, "databaseId": rid, "name": name, "headSha": sha,
           "createdAt": created}
    if conclusion:
        row["conclusion"] = conclusion
    return row


GHOST = _run("queued", 43096436723, "ad5945968" + "0" * 31, "2026-11-11T20:30:15Z")
LATER_DONE = _run("completed", 43137497174, "590429cab" + "0" * 31, "2026-11-12T01:52:42Z", "success")
LATER_RUNNING = _run("in_progress", 43137497175, "590429cab" + "0" * 31, "2026-11-12T01:52:42Z")
EARLIER_DONE = _run("completed", 43049700446, "1a88686b9" + "0" * 31, "2026-11-11T15:34:26Z", "success")
GROK = _run("in_progress", 43150000001, "b" * 40, "2026-11-12T04:00:00Z", branch="grok/v3901-151",
            name="TV DIABLO — agent tests")


class AnOrphanedPublishHoldsNothing(unittest.TestCase):

    def test_baseline_a_queued_publish_with_only_earlier_siblings_is_live(self):
        runs = [GHOST, EARLIER_DONE]
        self.assertEqual([SY._rid(r) for r in SY.live_publish_runs(runs)], [43096436723],
                         "PREMISE: a genuinely waiting Publish no longer reads as live - the case would not distinguish")
        ok, why = SY.may_push("grok/v3901-151", runs, now=NOW)
        self.assertFalse(ok, why)

    def test_the_ghost_of_11_12_is_orphaned_by_the_v3899_publish(self):
        """* THE POINT"""
        runs = [GHOST, LATER_DONE, EARLIER_DONE]
        later = SY.orphaned_by(GHOST, runs)
        self.assertIsNotNone(later, "a Publish GitHub ran past was not seen as orphaned")
        self.assertEqual(SY._rid(later), 43137497174)
        self.assertEqual(SY.live_publish_runs(runs), [])
        self.assertEqual(SY.queued_priority_runs(runs, NOW), [])

    def test_a_later_publish_that_only_started_also_orphans_it(self):
        self.assertIsNotNone(SY.orphaned_by(GHOST, [GHOST, LATER_RUNNING]))

    def test_a_later_publish_that_never_ran_does_not(self):
        """a later Publish that finished cancelled or skipped never ran, so it passed nothing over"""
        for c in ("cancelled", "skipped"):
            never = _run("completed", 43137497177, "590429cab" + "0" * 31, "2026-11-12T01:52:42Z", c)
            self.assertIsNone(SY.orphaned_by(GHOST, [GHOST, never]), "a %s Publish orphaned a waiting one" % c)

    def test_a_later_publish_that_is_still_waiting_does_not(self):
        waiting = _run("queued", 43137497176, "590429cab" + "0" * 31, "2026-11-12T01:52:42Z")
        self.assertIsNone(SY.orphaned_by(GHOST, [GHOST, waiting]))
        self.assertIsNone(SY.orphaned_by(LATER_RUNNING, [GHOST, LATER_RUNNING]),
                          "a RUNNING Publish was called orphaned - only a waiting one can be")

    def test_the_ghost_no_longer_refuses_a_grok_push(self):
        ok, why = SY.may_push("grok/v3901-151", [GHOST, LATER_DONE], now=NOW)
        self.assertTrue(ok, why)

    def test_it_is_said_once_with_the_run_that_went_past_it(self):
        SY._SAID_ORPHANS.discard(43096436723)
        said = []
        runs = [GHOST, LATER_DONE, GROK]
        SY.yield_to_ship(run=None, say=said.append, runs=runs, now=NOW, sweep=False)
        SY.yield_to_ship(run=None, say=said.append, runs=runs, now=NOW, sweep=False)
        orphan = [l for l in said if "REG-3766 ORPHANED" in l]
        self.assertEqual(len(orphan), 1, said)
        self.assertIn("43137497174", orphan[0])
        self.assertFalse([l for l in said if "REG-3654 QUEUED" in l], "the orphan was still logged as a queued Publish")


RED_PROOF = [
    {"why": "REG-3766 - a later Publish that finished cancelled or skipped (it never ran) orphans a real waiting one",
     "file": "tv/ship_yield.py",
     "find": "                or (_status(r) == \"completed\" and str(r.get(\"conclusion\") or \"\").lower() not in (\"cancelled\", \"skipped\", \"\"))):\n",
     "replace": "                or _status(r) == \"completed\"):\n",
     "matches": 1},
    {"why": "REG-3766 - a Publish GitHub passed over reads as live again and refuses every grok/ push for hours",
     "file": "tv/ship_yield.py",
     "find": "        if orphaned_by(r, runs) is not None:\n            continue\n        out.append(r)\n",
     "replace": "        out.append(r)\n",
     "matches": 1},
    {"why": "REG-3766 - a later Publish that already ran no longer orphans the waiting one",
     "file": "tv/ship_yield.py",
     "find": "        if theirs is not None and theirs > mine:\n",
     "replace": "        if theirs is not None and theirs > mine and False:\n",
     "matches": 1},
    {"why": "REG-3766 - the orphan is said every pass instead of once",
     "file": "tv/ship_yield.py",
     "find": "        if later is None or _rid(r) in _SAID_ORPHANS:\n",
     "replace": "        if later is None:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
