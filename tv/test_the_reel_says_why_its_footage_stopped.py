# -*- coding: utf-8 -*-
"""v3901 (REG-3753, #188) - WHY THE FOOTAGE STOPPED IS SAID IN THE AGENT LOG AND KEPT IN THE REEL.

MEASURED 11-12 on Dean's frozen copy (off the repo): reel 11-08 17:09 opened after an update ("Diablo is on screen"), its AI
reads ran the whole time (Catacombs Level 2 at 17:22, the warm-up gate never skipped - no "held back" line at seal, the
game gate was open - the reads ran), and its first footage frame landed at 17:43, 34 minutes in - a painted in-game frame,
seconds after "[reap] ... read-eviction took 112 picture(s)". A second reel that evening started 31 minutes late. The reason
the footage writer refused lived only in _FOOTAGE_WHY, in memory, overwritten every second: nothing in his logs or his reels
could say which gate held the film (the warm-up and game-window gates are ruled out by his logs; the disk floor is
unlikely - the shedding ran on its above-the-floor cadence; a stale capture file is the open lead).

Now each refused frame is counted by reason (source missing / stale, no game, warming up, disk floor, write failed), the
start of a pause and its end are said once each, and the reel's index carries footageRefused when it seals.

DRIVEN: the real _archive_footage_copy into a fixture hist dir, the disk floor raised and lowered around it; the seal and
the Windows watch feed by their own source, one anchor each. RED_PROOF below.
"""
import contextlib
import io
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

from PIL import Image, ImageDraw  # noqa: E402


def _code():
    with io.open(os.path.join(HERE, "tv_diablo.py"), encoding="utf-8") as fh:
        return "\n".join(l.split("#", 1)[0].rstrip() for l in fh.read().split("\n"))


class TheReelSaysWhyItsFootageStopped(unittest.TestCase):

    def setUp(self):
        import tv_diablo
        self.t = tv_diablo
        self.tmp = tempfile.mkdtemp(prefix="footwhy_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.hist = os.path.join(self.tmp, "hist")
        os.makedirs(self.hist)
        keys = ("HIST_DIR", "_FOOTAGE_WARM", "_GAME_OK", "MIN_FREE_GB", "_FOOTAGE_WHY")
        self._old = {k: self.t.__dict__.get(k, KeyError) for k in keys}
        self._tally = dict(self.t._FOOTAGE_REFUSED)
        self._pause = dict(self.t._FOOTAGE_PAUSE)
        self.addCleanup(self._restore)
        self.t.HIST_DIR = self.hist
        self.t._FOOTAGE_WARM = True          # the warm-up gate is not the subject
        self.t._GAME_OK = True               # nor is the game-window gate
        self.t._FOOTAGE_REFUSED.clear()
        self.t._FOOTAGE_PAUSE.update(since=None, kind=None, n=0)
        for k in ("TV_STUB", "TV_NO_GAME_GUARD"):
            if os.environ.get(k):
                self.skipTest("%s is set - the guards are deliberately off for harnesses" % k)
        im = Image.new("RGB", (800, 450), (40, 60, 30))
        d = ImageDraw.Draw(im)
        for x in range(0, 800, 37):
            d.line([(x, 0), (800 - x, 450)], fill=(200, (x * 3) % 255, 90), width=3)   # a painted, busy in-game-ish frame
        self.src = os.path.join(self.tmp, "eye.jpg")
        im.save(self.src, quality=92)

    def _restore(self):
        for k, v in self._old.items():
            if v is KeyError:
                self.t.__dict__.pop(k, None)
            else:
                self.t.__dict__[k] = v
        self.t._FOOTAGE_REFUSED.clear()
        self.t._FOOTAGE_REFUSED.update(self._tally)
        self.t._FOOTAGE_PAUSE.update(self._pause)

    def _shoot(self, at):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ok = self.t._archive_footage_copy(self.src, at, why="test", _consume_due=False)
        return ok, buf.getvalue()

    def _frames(self):
        return [f for f in os.listdir(self.hist) if f.startswith("f_")]

    def test_baseline_a_frame_lands_with_room(self):
        self.t.MIN_FREE_GB = 0
        ok, said = self._shoot(1000.0)
        self.assertTrue(ok)
        self.assertEqual(len(self._frames()), 1, "PREMISE: the fixture frame does not land - the case cannot distinguish")
        self.assertEqual(self.t._FOOTAGE_REFUSED, {})
        self.assertNotIn("footage paused", said)

    def test_a_disk_floor_pause_is_said_counted_and_its_end_too(self):
        """* THE POINT - Dean 11-08: 34 minutes of a reel with no footage and no word anywhere"""
        self.t.MIN_FREE_GB = 10 ** 6
        ok1, said1 = self._shoot(1000.0)
        ok2, said2 = self._shoot(1001.0)
        self.assertEqual((ok1, ok2), (False, False))
        self.assertEqual(self._frames(), [])
        self.assertIn("footage paused - free disk is under the floor", said1)
        self.assertNotIn("footage paused", said2, "the pause was said on every refused frame, not once")
        self.assertEqual(self.t._FOOTAGE_REFUSED, {"disk-floor": 2})
        self.t.MIN_FREE_GB = 0
        ok3, said3 = self._shoot(1002.0)
        self.assertTrue(ok3)
        self.assertIn("footage resumed - 2 frame(s) refused", said3)
        self.assertIn("disk-floor 2", said3)

    def test_the_tally_reads_most_first(self):
        self.assertEqual(self.t.footage_refused_words({"warming-up": 3, "disk-floor": 40}), "disk-floor 40 · warming-up 3")
        self.assertEqual(self.t.footage_refused_words({}), "none")

    def test_the_seal_keeps_the_tally_in_the_reel_index(self):
        code = _code()
        self.assertEqual(code.count('                    _ixdoc["footageRefused"] = dict(_FOOTAGE_REFUSED)\n'), 1,
                         "the reel's index no longer carries why its footage was refused")

    def test_the_windows_feed_counts_a_stale_capture(self):
        code = _code()
        self.assertEqual(code.count('                    _footage_refused("source-stale")\n'), 1,
                         "a due footage frame whose capture file went stale is no longer counted")


RED_PROOF = [
    {"why": "REG-3753 - the disk floor refuses footage silently again (Dean 11-08: 34 minutes, no word)",
     "file": "tv/tv_diablo.py",
     "find": "            _footage_refused(\"disk-floor\", \"%.1f GB free, the floor is %s GB\" % (_free_now, MIN_FREE_GB))\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3753 - the end of a footage pause is not said",
     "file": "tv/tv_diablo.py",
     "find": "        _footage_landed(now_f)\n        return True\n",
     "replace": "        return True\n",
     "matches": 1},
    {"why": "REG-3753 - the reel seals without its refusal tally",
     "file": "tv/tv_diablo.py",
     "find": "                    _ixdoc[\"footageRefused\"] = dict(_FOOTAGE_REFUSED)\n",
     "replace": "                    pass\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
