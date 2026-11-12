# -*- coding: utf-8 -*-
"""v3901 (REG-3762, #188) - THE FROZEN-PAGE JUDGE READS THE ROLLING REEL'S FRAMES WHERE THEY ARE: LOOSE IN hist/.

GrokBot (#230, 11-12, the work ALT on v3899, read-only): GeForce NOW's "Your game session ended due to inactivity" dialog was
filmed for 54 minutes, then 24+ more - 949 of 989 frames byte-identical - and no frozen-idle seal ever came: no seal row,
no frozenIdleSince in the watcher's record. control_app.reel_film_is_frozen_non_d2r looked ONLY in reel_<sid>/ under the
session id the agent's bridge reports, but every recorder writes f_<ms>.jpg straight into hist/ and folds them into the
reel at the SEAL, and the bridge does not answer there - so the judge answered UNKNOWN on every look and both frozen clocks
(REG-3722's away path and v3894's window-seen path) never started. Its law stubbed the function. Now it reads the fresh
frames wherever they are.

DRIVEN: the real reel_film_is_frozen_non_d2r over real JPEGs in a fixture hist (TV_HIST), the bridge stubbed silent; the
real d2r_screens.frozen_non_d2r decides. RED_PROOF below.
"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

from PIL import Image, ImageDraw  # noqa: E402
import control_app as ca  # noqa: E402

NOW = 1796000000000


def _dialog(shade=0):
    """A cloud client's frozen idle page: a grey dialog with text-like bars (not D2R)."""
    im = Image.new("RGB", (800, 450), (32, 34, 38))
    d = ImageDraw.Draw(im)
    d.rectangle([200, 140, 600, 300], fill=(60 + shade, 62, 66))
    for i in range(4):
        d.rectangle([230, 170 + i * 25, 560 - i * 40, 182 + i * 25], fill=(200, 200, 200))
    return im


class AFrozenCloudPageIsReadFromItsLooseFrames(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="frozen_loose_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.hist = os.path.join(self.tmp, "frames", "hist")
        os.makedirs(self.hist)
        p = mock.patch.dict(os.environ, {"TV_HIST": self.hist})
        p.start()
        self.addCleanup(p.stop)
        q = mock.patch.object(ca, "_mini_sid", lambda: None)       # the bridge does not answer (the work ALT)
        q.start()
        self.addCleanup(q.stop)

    def _shoot(self, ims, where=None, ago_s=(20, 10, 2)):
        d = os.path.join(self.hist, where) if where else self.hist
        os.makedirs(d, exist_ok=True)
        for im, ago in zip(ims, ago_s):
            im.save(os.path.join(d, "f_%d.jpg" % (NOW - ago * 1000)), "JPEG", quality=92)

    def test_loose_frozen_frames_are_judged_frozen(self):
        """* THE POINT - the work ALT 11-12: a frozen GeForce NOW dialog, loose frames, the bridge silent"""
        self._shoot([_dialog()] * 3)
        self.assertIs(ca.reel_film_is_frozen_non_d2r(NOW), True,
                      "the rolling reel's loose frames were never read, so the frozen page could not end the session")

    def test_baseline_a_changing_picture_is_not_frozen(self):
        self._shoot([_dialog(0), _dialog(40), _dialog(80)])
        self.assertIs(ca.reel_film_is_frozen_non_d2r(NOW), False)

    def test_stale_frames_say_nothing(self):
        self._shoot([_dialog()] * 3, ago_s=(400, 300, 200))
        self.assertIsNone(ca.reel_film_is_frozen_non_d2r(NOW), "frames older than the fresh window were judged")

    def test_the_reels_own_folder_still_counts(self):
        with mock.patch.object(ca, "_mini_sid", lambda: "s_1"):
            self._shoot([_dialog()] * 3, where="reel_s_1")
            self.assertIs(ca.reel_film_is_frozen_non_d2r(NOW), True)


RED_PROOF = [
    {"why": "REG-3762 - the judge reads only reel_<sid>/ again: the rolling reel's loose frames are never seen (the work ALT)",
     "file": "tv/control_app.py",
     "find": "        paths += [os.path.join(hist, n) for n in os.listdir(hist)\n",
     "replace": "        paths += [os.path.join(hist, n) for n in ()\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
