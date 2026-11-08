# -*- coding: utf-8 -*-
"""v3885 (his 11-08: "the console reads a differnt run number for the 500MF toggled or slid and silopen read" ... "i couldnt
simply toggle it within the console not that i did not try or want to") - A DRAGGED MF LANDS ON A ROUND TEN.

MEASURED on his screenshot: the Quick wins header read "odds @ 498% MF" against silospen's 500 - the MF slider is 0-1000 in
steps of 1 on a short dock track, several MF a pixel, so a drag cannot land on 500. Now a drag snaps to the nearest 10; a
move of 1 (an arrow key) and a preset (553, 699 - set by setMFPreset, not by a drag) stay exact. Runs the page's own _mfSnap
in node. RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
NODE = shutil.which("node")
LINE = "const _mfSnap = (v, prev) => (Math.abs(v - prev) > 1 && v % 10) ? Math.min(1000, Math.round(v / 10) * 10) : v;"


@unittest.skipUnless(NODE, "node is required to run the page's own snap")
class ADraggedMfLandsOnARoundTen(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(BIBLE, encoding="utf-8") as fh:
            cls.src = fh.read()
        line = next((ln for ln in cls.src.split("\n") if ln.startswith("const _mfSnap = ")), None)
        if line is None:
            raise AssertionError("the page has no _mfSnap - re-point this law")
        prog = line + "\nprocess.stdout.write(JSON.stringify([_mfSnap(498, 400), _mfSnap(503, 300), _mfSnap(996, 900), "\
               "_mfSnap(501, 500), _mfSnap(499, 500), _mfSnap(553, 553), _mfSnap(500, 400), _mfSnap(0, 40)]));"
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("node could not run the page's snap - UNKNOWN, not passing: " + r.stderr[-600:])
        cls.o = json.loads(r.stdout)

    def test_a_drag_lands_on_500(self):
        """* THE POINT - his drag read 498; it reads 500"""
        self.assertEqual(self.o[:3], [500, 500, 1000], "a drag does not land on a round ten: %r" % self.o)

    def test_one_step_and_a_preset_stay_exact(self):
        self.assertEqual(self.o[3:], [501, 499, 553, 500, 0], "an arrow-key step or an exact value was moved: %r" % self.o)

    def test_the_slider_reads_the_snap(self):
        self.assertIn("$(\"mf\").oninput = () => { const _v = _mfSnap(parseInt($(\"mf\").value), mf);", self.src,
                      "the MF slider does not snap a drag")


RED_PROOF = [
    {"why": "v3885 (his 11-08) - a drag lands on 498 again",
     "file": "bible.html",
     "find": "const _mfSnap = (v, prev) => (Math.abs(v - prev) > 1 && v % 10) ? Math.min(1000, Math.round(v / 10) * 10) : v;\n",
     "replace": "const _mfSnap = (v, prev) => v;\n", "matches": 1, "needs": "node"},
    {"why": "v3885 (his 11-08) - an arrow-key step is snapped back to its ten (the slider cannot move by one)",
     "file": "bible.html",
     "find": "const _mfSnap = (v, prev) => (Math.abs(v - prev) > 1 && v % 10) ? Math.min(1000, Math.round(v / 10) * 10) : v;\n",
     "replace": "const _mfSnap = (v, prev) => (v % 10) ? Math.min(1000, Math.round(v / 10) * 10) : v;\n", "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
