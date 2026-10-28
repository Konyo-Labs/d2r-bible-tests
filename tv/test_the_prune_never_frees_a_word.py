"""REG-1904 - the rolling prune freed the frames carrying FLOOR LABELS and called them "blank".

Measured 2026-10-07 by re-running the shipped `_prune_once` on a scratch copy of his reel
reel_s_1791129432613_17451: it freed the four frames showing "Storm Slippers / Wyrmhide Boots" and
"Colossus Blade" on the ground, because

  * the group test is a 16x16 thumbnail at tol 28, and those frames sat 0.0039-0.0117 from a label-less anchor
    (on 305 vault witness frames - each carrying a name the vault read - 273 sit at 0.0 from the frame before them);
  * "silent" meant only that the TAB-STRIP crop the panel gate OCRs held no text, and a floor label lives outside it.

The law: a silent frame may be freed only when it is the SAME PICTURE as the frame kept beside it at a scale where a
word changes it (96x60, 12 grey levels). The cases build synthetic frames - a textured scene, its exact duplicate, and
the same scene with a small dark label box and bright strokes - and first assert the DEFECT'S PREMISE (the label frame
is inside the old grouping bar, so the old rule would have freed it), so a green here cannot be a case that never
reached the deleter. Fixtures only: nothing here reads his frames.
"""
import os
import sys
import tempfile
import time
import unittest
import unittest.mock as mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402

_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402  #173 - its scratch is its own, so listing it keeps the law keyable
_fx_tmp.contain()

import chronicle_retro as cr  # noqa: E402
import control_app as ca  # noqa: E402

try:
    from PIL import Image, ImageDraw  # noqa: F401
    _PIL = True
except Exception:  # pragma: no cover - CI installs pillow
    _PIL = False


def _scene(path, label=False):
    """A 1440x936 textured scene (smooth enough that a duplicate is a duplicate), optionally with a floor label."""
    from PIL import Image, ImageDraw
    im = Image.new("L", (1440, 936))
    px = im.load()
    for y in range(0, 936):
        for x in range(0, 1440, 1):
            px[x, y] = (40 + ((x // 37) * 13 + (y // 29) * 7) % 90)
    im = im.convert("RGB")
    if label:
        d = ImageDraw.Draw(im)
        x0, y0 = 700, 420                         # a ground label: a dark translucent box with bright letters
        d.rectangle([x0, y0, x0 + 170, y0 + 20], fill=(12, 12, 14))
        for k in range(9):                        # nine glyph-sized bright strokes
            d.rectangle([x0 + 8 + k * 18, y0 + 5, x0 + 18 + k * 18, y0 + 15], fill=(230, 220, 160))
    im.save(path, "JPEG", quality=92)


@unittest.skipUnless(_PIL, "UNMEASURED here, not passing: the scene fixtures need PIL")
class AFloorLabelIsNotABlankFrame(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="prune_word_")
        now = time.time()
        self.paths = {}
        for k, (name, label) in enumerate((("f_1000.jpg", False), ("f_1001.jpg", False), ("f_1002.jpg", True))):
            p = os.path.join(self.d, name)
            _scene(p, label=label)
            os.utime(p, (now - 600 + k, now - 600 + k))
            self.paths[name] = p

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self):
        def _probe(_self, kg=None, t=None):
            _self.marks.append((time.time(), True))
            return True
        # the panel gate is pinned SILENT (the tab-strip crop held no text) and the lane is proven live, so the only
        # thing deciding is the prune's own picture test - which is what this law is about
        with mock.patch.object(ca, "stash_panel_verdict", lambda _q: "unknown"), \
             mock.patch.object(ca.LaneCanary, "probe", _probe):
            return ca._prune_once(hist_dir=self.d, floor=0, grace_s=0.0, batch=500)

    def left(self):
        return sorted(n for n in _fx_tmp.list_own(self.d) if n.startswith("f_"))

    def test_the_premise_the_label_frame_is_inside_the_old_grouping_bar(self):
        a = cr.jpeg_sig(self.paths["f_1000.jpg"])
        b = cr.jpeg_sig(self.paths["f_1002.jpg"])
        self.assertLessEqual(cr.sig_diff(a, b), ca._PRUNE_MAX_DIFF,
                             "the fixture no longer reproduces the defect: its label frame is outside the 16x16 "
                             "grouping bar, so a green below would not prove the finer look does anything")
        fa, fb = ca._prune_fine_sig(self.paths["f_1000.jpg"]), ca._prune_fine_sig(self.paths["f_1002.jpg"])
        self.assertGreater(cr.sig_diff(fa, fb, tol=ca._PRUNE_FINE_TOL), 0.0)

    def test_a_label_frame_is_kept_and_a_true_duplicate_is_freed(self):
        dropped, freed, why = self._run()
        left = self.left()
        self.assertIn("f_1002.jpg", left, "the frame carrying a floor label was freed as 'blank' (REG-1904): %s" % why)
        self.assertIn("f_1000.jpg", left, "the anchor itself must never go")
        self.assertNotIn("f_1001.jpg", left, "an exact duplicate of the kept frame adds nothing and should go: %s" % why)
        self.assertEqual(dropped, 1, why)
        self.assertIn("1 kept because the finer look found a change", why)

    def test_a_frame_the_finer_look_cannot_decode_is_kept(self):
        real = ca._prune_fine_sig

        def _fine(p):
            return None if p.endswith("f_1001.jpg") else real(p)
        with mock.patch.object(ca, "_prune_fine_sig", _fine):
            dropped, freed, why = self._run()
        self.assertIn("f_1001.jpg", self.left(), "an undecodable frame was freed - an unmeasured frame is not a spare one")
        self.assertEqual(dropped, 0, why)

    def test_the_armed_promise_on_his_panel_names_the_finer_look(self):
        say = ca._PRUNE_STATS["lastSay"]
        self.assertNotIn("frees only blank frames", say, "the panel still promises the rule REG-1904 refuted")
        self.assertIn("same picture as the frame kept beside it", say)


RED_PROOF = [
    {
        "why": "REG-1904 - the finer look is skipped and a silent frame inside the 16x16 bar is freed: the floor-label "
               "frame goes as 'blank'",
        "file": "tv/control_app.py",
        "find": "            if _same is not True:\n                _wordy += 1\n",
        "replace": "            if False:\n                _wordy += 1\n",
        "matches": 1,
    },
    {
        "why": "REG-1904 - the finer look answers 'same picture' for anything, so the label frame and an undecodable "
               "frame are both freed",
        "file": "tv/control_app.py",
        "find": "    return _cr.sig_diff(a, b, tol=_PRUNE_FINE_TOL) == 0.0\n",
        "replace": "    return True\n",
        "matches": 1,
    },
    {
        "why": "REG-1904 - the finer look's tolerance is opened to every grey level, so it cannot see a word",
        "file": "tv/control_app.py",
        "find": "_PRUNE_FINE_TOL = 12\n",
        "replace": "_PRUNE_FINE_TOL = 255\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
