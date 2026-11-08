# -*- coding: utf-8 -*-
"""#86 gap audit 25 (REG-1783) — A LANE COUNT THAT WAS NOT TAKEN IS NOT A PASS.

The shelf row returned OK while its sentence said the per-lane count was UNKNOWN.
The eagle colours the state word, so that beat was tallied green.

  · DRIVEN: a fresh beat that says the plan was readable and carries no laneCounts.
    The state is unknown. The sentence still says so.
  · DRIVEN: a fresh beat with no ok key, and one whose ok is None. Unknown, not a pass,
    and not the stalled-lane row.
  · DRIVEN: a fresh beat that counted a reading lane is still ok. A DARK count is still
    missing. A beat forty hours old is still missing, before the count is consulted.

Nothing here reads his shelf. The stored beat is replaced for the call. RED_PROOF below.
[[unknown-stays-unknown]]
"""
import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()


def _fresh(**extra):
    beat = {"at": time.time() * 1000.0}
    beat.update(extra)
    return beat


class ALaneCountThatWasNotTakenIsNotAPass(unittest.TestCase):
    def setUp(self):
        import console_doctor as CD
        import shelf_driver as SD
        self.CD = CD
        self.SD = SD
        self._was = SD.last_beat

    def tearDown(self):
        self.SD.last_beat = self._was

    def _ask(self, beat):
        self.SD.last_beat = lambda: beat
        return self.CD._check_the_shelf_lanes_are_still_reading()

    def test_a_readable_plan_with_no_lane_count_is_not_a_pass(self):
        for counts in (None, {}, "not-a-dict"):
            beat = _fresh(ok=True, owed=0)
            if counts is not None:
                beat["laneCounts"] = counts
            st, why = self._ask(beat)
            self.assertEqual(self.CD.UNKNOWN, st,
                             "no lane count (%r) graded %r: %s" % (counts, st, why))
            self.assertIn("UNKNOWN", why)
            self.assertNotEqual(self.CD.OK, st)

    def test_a_beat_that_did_not_say_whether_the_plan_was_readable_is_not_a_pass(self):
        st, why = self._ask(_fresh(owed=0))
        self.assertEqual(self.CD.UNKNOWN, st, "a missing ok graded %r: %s" % (st, why))
        self.assertIn("did not say", why)
        self.assertNotEqual(self.CD.MISSING, st)
        st2, why2 = self._ask(_fresh(ok=None, owed=0))
        self.assertEqual(self.CD.UNKNOWN, st2, "ok None graded %r: %s" % (st2, why2))

    def test_a_counted_reading_lane_is_still_a_pass(self):
        st, why = self._ask(_fresh(ok=True, laneCounts={"reading": 2}))
        self.assertEqual(self.CD.OK, st, "a counted reading lane graded %r: %s" % (st, why))

    def test_a_dark_count_is_still_missing(self):
        st, why = self._ask(_fresh(ok=True, laneCounts={"DARK": 1, "reading": 3}))
        self.assertEqual(self.CD.MISSING, st, "a DARK lane graded %r: %s" % (st, why))

    def test_a_dark_lane_is_named_with_what_it_owes(self):
        """v3882 (every Windows PC's doctor, 11-08: "but 2 dark" - and nothing said WHICH). Dean's beat, as measured: the
        chronicle and the deleter dark behind his shut locks, triage untimed, vault idle - the row names the two"""
        lanes = [{"lane": "chronicle", "state": "DARK", "owed": 38}, {"lane": "deleter", "state": "DARK", "owed": 130},
                 {"lane": "triage", "state": "UNTIMED", "owed": 45}, {"lane": "vault", "state": "IDLE", "owed": 0}]
        st, why = self._ask(_fresh(ok=True, laneCounts={"dark": 2, "untimed": 1, "idle": 1}, lanes=lanes))
        self.assertEqual(self.CD.MISSING, st, why)
        self.assertIn("chronicle dark (38 owed), deleter dark (130 owed)", why)
        self.assertNotIn("triage", why, "a lane that is not dark was named as stopped")
        st2, why2 = self._ask(_fresh(ok=True, laneCounts={"dark": 1}, lanes=None))
        self.assertEqual(self.CD.MISSING, st2, "a dark count with no rows to name is still MISSING: %s" % why2)

    def test_a_stale_beat_is_still_missing_before_the_count(self):
        beat = {"at": (time.time() - 40 * 3600) * 1000.0, "ok": True, "owed": 1}
        st, why = self._ask(beat)
        self.assertEqual(self.CD.MISSING, st, "a 40h beat graded %r: %s" % (st, why))


RED_PROOF = [
    {"why": "v3882 - the dark-lanes row says '2 dark' and names none of them again",
     "file": "tv/console_doctor.py",
     "find": "                                (\": \" + \", \".join(_named)) if _named else \"\", tail))",
     "replace": "                                \"\", tail))",
     "matches": 1},
    {"why": "REG-1783 - a beat with no lane count is a pass again",
     "file": "console_doctor.py",
     "find": "    return UNKNOWN, (\"the shelf driver beat %.1fh ago and reported ok; "
             "it recorded no per-lane counts, \"\n"
             "                     \"so whether each lane is reading is UNKNOWN rather "
             "than confirmed%s\" % (age_h, tail))",
     "replace": "    return OK, (\"the shelf driver beat %.1fh ago and reported ok; "
                "it recorded no per-lane counts, \"\n"
                "                     \"so whether each lane is reading is UNKNOWN rather "
                "than confirmed%s\" % (age_h, tail))",
     "matches": 1},
    {"why": "REG-1783 - a beat that did not say whether the plan was readable is a pass again",
     "file": "console_doctor.py",
     "find": "        return UNKNOWN, (\n"
             "            \"the shelf driver beat %.1fh ago and did not say whether its plan "
             "was readable, \"\n"
             "            \"so whether each lane is reading is UNKNOWN%s\" % (age_h, tail))",
     "replace": "        return OK, (\n"
                "            \"the shelf driver beat %.1fh ago and did not say whether its plan "
                "was readable, \"\n"
                "            \"so whether each lane is reading is UNKNOWN%s\" % (age_h, tail))",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
