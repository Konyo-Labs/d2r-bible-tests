# -*- coding: utf-8 -*-
"""v3893 (REG-3551) - A SESSION IS TAGGED FROM THE HIGHLIGHTED NAME ON CHARACTER SELECT.

Recording starts before character select, so who_at(the session's t0) only sees earlier characters
(signals with ts <= t0) and can tag the reel as the previous player. The highlighted name is already
read: char_select.selected_of extracts it, logins / session_characters bind it to the reel's sessionId.
The digest now consults that login, instead of inventing a new pixel reader or guessing from t0.

Law: a reel that started at the logo, whose character-select visit later named the highlighted row,
is tagged as that character — not as whoever was playing when the recorder started. A session with
no login of its own still inherits who_at(t0), so a later farm reel without a new select screen
keeps its player. An unconfirmed close (the first highlight may not be who he entered with) is not
replaced by the previous character. RED_PROOF below.
"""
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import char_select as CS  # noqa: E402
import shadow_sessions as SS  # noqa: E402

T0 = 1793614663296          # recorder starts (logo)
T_PREV = T0 - 3_600_000     # previous character-select
T_LOGIN = T0 + 90_000       # this reel's character select (after the second logo / CONNECTING...)
T_PLAY = T0 + 180_000
PREV = "s_1793611000000_1"
NEW = "s_1793614663296_52736"


def _row(ts, sid, **k):
    d = {"ts": ts, "captureTs": ts, "sessionId": sid, "lane": "deep", "frameId": "f_%d" % ts}
    d.update(k)
    return d


def _journal():
    return [
        _row(T_PREV, PREV, scene="char-select", character="Hammy", cls="Barbarian", level=90),
        _row(T0, NEW, scene="gameplay"),
        _row(T_PLAY, NEW, scene="gameplay", intent="farmed", names=["Shako"]),
    ]


def _ledger(name="Blizzy", reader="vision-close", closed="read"):
    return {
        "version": 1, "chars": {}, "reels": {},
        "stats": {"ticks": 0, "frames": 0, "reads": 0, "refused": 0, "lastTs": None, "lastWhy": "", "readTs": []},
        "visits": {
            "reel_%s#1" % NEW: {
                "reel": "reel_%s" % NEW,
                "ts": T_LOGIN,
                "closed": closed,
                "sel": [{"ts": T_LOGIN, "name": name, "reader": reader}],
            }
        },
    }


class TheSessionIsTaggedFromTheHighlightedName(unittest.TestCase):

    def setUp(self):
        self._load = CS.load
        import control_app as ca
        self._is_read = ca._is_a_live_read
        self.tmp = tempfile.mkdtemp(prefix="sel_tag_")

    def tearDown(self):
        CS.load = self._load
        shutil.rmtree(self.tmp, True)

    def _digest(self, ledger):
        CS.load = lambda: ledger
        return SS.digest(_journal(), self.tmp, self._is_read, T_PLAY + 1, make=None)

    def test_a_reel_that_started_at_the_logo_takes_the_highlighted_name(self):
        out = self._digest(_ledger("Blizzy"))
        by = {s["sessionId"]: s for s in out["sessions"]}
        self.assertIn(NEW, by)
        self.assertEqual(by[NEW]["character"]["name"], "Blizzy")
        self.assertIn("select-screen", by[NEW]["character"]["sources"])
        self.assertNotEqual(by[NEW]["character"]["name"], "Hammy")

    def test_without_a_login_the_session_still_inherits_who_was_playing_at_t0(self):
        out = self._digest(CS._empty())
        by = {s["sessionId"]: s for s in out["sessions"]}
        self.assertEqual(by[NEW]["character"]["name"], "Hammy")
        self.assertIn("earlier read", by[NEW]["character"]["sources"])

    def test_an_unconfirmed_close_is_not_replaced_by_the_previous_character(self):
        # closed, but the newest named row was not the closing read — logins marks it unconfirmed
        out = self._digest(_ledger("Blizzy", reader="vision", closed="read"))
        by = {s["sessionId"]: s for s in out["sessions"]}
        self.assertIsNone(by[NEW]["character"]["name"])
        self.assertNotEqual(by[NEW]["character"].get("name"), "Hammy")

    def test_the_helper_reuses_the_existing_login_reader(self):
        with open(os.path.join(HERE, "shadow_sessions.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("def character_from_select(", src)
        self.assertIn("for L in CS.logins(d) or []:", src)
        self.assertIn("CS.load()", src)
        with open(os.path.join(HERE, "char_select.py"), encoding="utf-8") as fh:
            sel = fh.read()
        self.assertIn("def selected_of(", sel)
        self.assertIn("def logins(d):", sel)


RED_PROOF = [
    {"why": "v3893 (REG-3551) - a reel that started at the logo is tagged as whoever was playing at t0, not the highlighted name",
     "file": "tv/shadow_sessions.py",
     "find": "        _from_select = None if _sig else character_from_select(sid, s.get(\"t0\"), s.get(\"t1\"))\n",
     "replace": "        _from_select = None\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
