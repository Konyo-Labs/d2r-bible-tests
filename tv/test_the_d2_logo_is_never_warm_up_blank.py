# -*- coding: utf-8 -*-
"""v3900 (REG-3745, #188) - THE D2 LOGO IS THE SESSION'S FIRST DOOR, NEVER "WARM-UP BLANK".

His ruling 11-11: on every route the session is the D2 double logo -> Connecting to Battle.net -> character select, and it
STARTS at the first logo. MEASURED 11-12 on his Mac's own reels (10-13): the corner-logo frames score flatness 0.994 - black
but for the small fire logo - so chronicle_retro.is_dead_frame calls them blank and the footage warm-up gate (v1548, built to
skip the blank grabs while D2R launches) dropped them; the title frames (0.82-0.89) passed. On Dean's PC 11-07 (his capture
log, his Battle.net log, both frozen off the repo): the game launched 17:38:18, the reel opened 17:38:33, a read at 17:38:38
saw "transition", and the saved footage began at character select, 36 s in. A frame the screen reader names logo, title or
Connecting now passes the warm-up gate; a blank frame is still skipped.

DRIVEN: the real _archive_footage_copy over the door law's own synthetic logo (one logo, not a second drawing), into a
fixture hist dir. RED_PROOF below.
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
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import test_a_session_starts_at_the_games_own_door as DOOR  # noqa: E402  the ONE synthetic logo / title


class TheD2LogoIsNeverWarmUpBlank(unittest.TestCase):

    def setUp(self):
        import tv_diablo
        self.t = tv_diablo
        self.tmp = tempfile.mkdtemp(prefix="doorwarm_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.hist = os.path.join(self.tmp, "hist")
        os.makedirs(self.hist)
        keys = ("HIST_DIR", "_FOOTAGE_WARM", "_FOOTAGE_WARMSKIP", "_GAME_OK", "MIN_FREE_GB", "_FOOTAGE_WHY")
        self._old = {k: self.t.__dict__.get(k, KeyError) for k in keys}
        self.addCleanup(self._restore)
        self.t.HIST_DIR = self.hist
        self.t.__dict__.pop("_FOOTAGE_WARM", None)       # the warm-up gate is the subject here
        self.t._GAME_OK = True                             # the game-window gate is not
        self.t.MIN_FREE_GB = 0                             # nor is the disk
        for k in ("TV_STUB", "TV_NO_GAME_GUARD"):
            if os.environ.get(k):
                self.skipTest("%s is set - the guards are deliberately off for harnesses" % k)

    def _restore(self):
        for k, v in self._old.items():
            if v is KeyError:
                self.t.__dict__.pop(k, None)
            else:
                self.t.__dict__[k] = v

    def _jpg(self, im, name):
        p = os.path.join(self.tmp, name)
        im.save(p, quality=92)
        return p

    def _frames(self):
        return [f for f in os.listdir(self.hist) if f.startswith("f_")]

    def test_premise_the_logo_reads_blank_to_the_flatness_test(self):
        import chronicle_retro as CR
        import d2r_screens as DS
        p = self._jpg(DOOR.logo(), "logo.jpg")
        self.assertTrue(CR.is_dead_frame(p), "PREMISE: the logo is not flat here - the case would not distinguish")
        self.assertEqual(DS.screen_of(p)[0], "logo", "PREMISE: the screen reader does not call the fixture the logo")

    def test_the_logo_is_kept_through_the_warm_up_gate(self):
        """* THE POINT - the first door of every session was dropped as 'warming-up' (his Mac's 10-13 reel, Dean 11-07)"""
        p = self._jpg(DOOR.logo(), "logo.jpg")
        self.t._archive_footage_copy(p, 1000.0, why="test", _consume_due=False)
        self.assertEqual(len(self._frames()), 1, "the D2 logo was dropped as warm-up blank: %s"
                         % self.t.__dict__.get("_FOOTAGE_WHY"))

    def test_baseline_a_blank_startup_frame_is_still_skipped(self):
        from PIL import Image
        p = self._jpg(Image.new("RGB", (800, 450), (4, 3, 3)), "black.jpg")
        self.t._archive_footage_copy(p, 1000.0, why="test", _consume_due=False)
        self.assertEqual(self._frames(), [], "a blank startup grab was archived")
        self.assertIn("warming-up", str(self.t.__dict__.get("_FOOTAGE_WHY")))


RED_PROOF = [
    {"why": "REG-3745 - the D2 logo is dropped as warm-up blank again (his Mac's 10-13 reel, Dean 11-07)",
     "file": "tv/tv_diablo.py",
     "find": "                if _cr.is_dead_frame(src_path) and not _door_screen(src_path):\n",
     "replace": "                if _cr.is_dead_frame(src_path):\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
