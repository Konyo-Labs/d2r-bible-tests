# -*- coding: utf-8 -*-
"""v3901 (REG-3757, #44 / #104) - A DARK PAID-READ LANE NAMES A SIGNED-OUT CLAUDE.

Dean's console's last report (11-11): "the shelf driver beat 1.0h ago, but 2 dark: chronicle dark (51 owed), deleter dark (131
owed)". The same beacon's readers block said "Claude is signed out on this PC" (OAuth session expired), and its fault rows
said "791 item name(s) were READ ... NONE are banked". The chronicle and vault lanes' reads are PAID Claude reads - they
cannot run while the reader is signed out - and the row said only "dark", so nothing on his fleet row named the one step that
unblocks them (a sign-in only the person at that PC can do). Now a dark chronicle or vault lane carries "Claude is signed out
on this PC, so its paid reads cannot run: sign in (CLAUDE / SIGN IN, top right)" when the readers' own lamp says so. A lane
that is not a paid read (the deleter) and a reader that is signed in or UNKNOWN add nothing.

DRIVEN: console_doctor._check_the_shelf_lanes_are_still_reading over a stubbed shelf_driver beat, and _claude_signed_out
over a stubbed reader lamp. RED_PROOF below.
"""
import os
import sys
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import console_doctor as cd  # noqa: E402
import shelf_driver as sd  # noqa: E402


def _beat():
    return {"at": cd.time.time() * 1000.0, "ok": True, "owed": 182, "held": 0, "onDisk": 198,
            "laneCounts": {"DARK": 2, "OK": 1},
            "lanes": [{"lane": "chronicle", "state": "DARK", "owed": 51},
                      {"lane": "deleter", "state": "DARK", "owed": 131},
                      {"lane": "vault", "state": "OK", "owed": 0}]}


class ADarkPaidLaneNamesASignedOutReader(unittest.TestCase):

    def _row(self, signed_out):
        with mock.patch.object(sd, "last_beat", _beat), mock.patch.object(cd, "_claude_signed_out", lambda: signed_out):
            return cd._check_the_shelf_lanes_are_still_reading()

    def test_a_signed_out_reader_is_named_on_the_paid_lane_only(self):
        """* THE POINT - Dean 11-11: chronicle dark (51 owed) while his Claude was signed out"""
        state, why = self._row("Claude is signed out on this PC (OAuth session expired)")
        self.assertEqual(state, cd.MISSING)
        i = why.index("chronicle dark (51 owed)")
        j = why.index("deleter dark (131 owed)")
        self.assertIn("Claude is signed out on this PC, so its paid reads cannot run", why[i:j],
                      "the dark chronicle lane does not name the signed-out reader")
        self.assertNotIn("signed out", why[j:], "the deleter (not a paid read) was blamed on the sign-in")

    def test_baseline_a_signed_in_or_unknown_reader_adds_nothing(self):
        state, why = self._row(None)
        self.assertEqual(state, cd.MISSING)
        self.assertIn("chronicle dark (51 owed)", why)
        self.assertNotIn("signed out", why)

    def test_the_stalled_reel_extract_says_it_too(self):
        """the reel sweep's reads are paid too: both of its stalled rows carry the same note (swept with this fix)"""
        import inspect
        src = "\n".join(l.split("#", 1)[0] for l in inspect.getsource(cd._check_the_reel_extract_is_moving).split("\n"))
        self.assertEqual(src.count("_paid_reads_blocked_note()"), 2, "a stalled reel-extract row no longer names the sign-in")
        with mock.patch.object(cd, "_claude_signed_out", lambda: "signed out"):
            self.assertIn("sign in (CLAUDE / SIGN IN", cd._paid_reads_blocked_note())
        with mock.patch.object(cd, "_claude_signed_out", lambda: None):
            self.assertEqual(cd._paid_reads_blocked_note(), "")

    def test_the_lamp_decides_and_unknown_is_not_signed_out(self):
        def fake(lamp, rows=()):
            m = types.ModuleType("control_app")
            m._reader_health = lambda *a, **k: {"claude": lamp}
            m._journal_tail_rows = lambda *a, **k: (None if rows is None else list(rows))
            return m
        for lamp, want in (({"state": "off", "needsLogin": True, "why": "Claude is signed out on this PC"}, True),
                           ({"state": "off", "needsLogin": False, "why": "the last read failed"}, False),
                           ({"state": "unknown", "needsLogin": False}, False),
                           ({"state": "on", "needsLogin": False}, False)):
            with mock.patch.dict(sys.modules, {"control_app": fake(lamp)}):
                self.assertEqual(bool(cd._claude_signed_out()), want, lamp)
        # the journal would not read: UNKNOWN, never "signed out" (v3901 run c moved this off the serving console)
        with mock.patch.dict(sys.modules, {"control_app": fake({"state": "off", "needsLogin": True}, rows=None)}):
            self.assertIsNone(cd._claude_signed_out(), "an unreadable journal read as signed out")


RED_PROOF = [
    {"why": "REG-3757 - the one note every stalled paid-read row adds goes silent",
     "file": "tv/console_doctor.py",
     "find": "            if _claude_signed_out() else \"\")\n",
     "replace": "            if False else \"\")\n",
     "matches": 1},
    {"why": "REG-3757 - a dark paid-read lane says only 'dark' again while the reader is signed out (Dean 11-11)",
     "file": "tv/console_doctor.py",
     "find": "                        if _signed_out:\n",
     "replace": "                        if False:\n",
     "matches": 1},
    {"why": "REG-3757 - a reader that merely failed a read is called signed out",
     "file": "tv/console_doctor.py",
     "find": "    if lamp.get(\"state\") == \"off\" and lamp.get(\"needsLogin\") is True:\n",
     "replace": "    if lamp.get(\"state\") == \"off\":\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
