# -*- coding: utf-8 -*-
"""v3885 (his 11-08: "the console reads a differnt run number for the 500MF toggled or slid and silopen read" ... "i couldnt
simply toggle it within the console not that i did not try or want to") - A DRAGGED MF LANDS ON A ROUND TEN.

MEASURED on his screenshot: the Quick wins header read "odds @ 498% MF" against silospen's 500 - the MF slider is 0-1000 in
steps of 1 on a short dock track, several MF a pixel, so a drag cannot land on 500. Now a drag snaps to the nearest 10; a
move of 1 (an arrow key) stays exact - and so does every value the page sets for him (a preset, 553 / 699; the number box;
the palette's "mf 553" and "mf+50"): those fire the slider's input event UNTRUSTED, and only a trusted event (his own drag)
snaps. GitHub's first v3885 round caught the palette at 550: this law's preset case was _mfSnap(553, 553) - a preset onto
an MF already 553, a case that could not fail. Runs the page's own _mfSnap AND its slider handler in node. RED_PROOF below.
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

    def test_only_his_drag_snaps_a_value_the_page_sets_stays_exact(self):
        """* v3885 round 1 - the slider's own handler, from another MF: a TRUSTED input (his drag) snaps; an untrusted one (a
        preset, the number box, the palette) keeps its exact value"""
        line = next((ln for ln in self.src.split("\n") if ln.startswith('$("mf").oninput = ')), None)
        self.assertIsNotNone(line, "the MF slider has no input handler - re-point this law")
        snap = next(ln for ln in self.src.split("\n") if ln.startswith("const _mfSnap = "))
        stubs = ("var EL = { value: '' }; var $ = function(){ return EL; }; var mf = 300, _mfChosen = false, selectedItem = null, "
                 "activeItemDetail = null, activeBossId = null; function noop(){} var persistSoon = noop, updateEffMF = noop, "
                 "renderHero = noop, renderBossCards = noop, renderDetail = noop, renderItemDetailCard = noop, "
                 "renderBossDetailCard = noop, renderGrailProgress = noop, renderWishlistHuntPath = noop, _sliderFanout = noop;\n")
        prog = (stubs + snap + "\n" + line.replace('$("mf").oninput = ', "var H = ", 1) + "\n"
                "var out = [];\n"
                "[[553, false], [699, false], [603, false], [498, true], [553, true]].forEach(function(c){ mf = 300; EL.value = String(c[0]); "
                "H({ isTrusted: c[1] }); out.push([mf, EL.value]); });\n"
                "process.stdout.write(JSON.stringify(out));")
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, "node could not run the slider's handler - UNKNOWN: " + r.stderr[-600:])
        got = json.loads(r.stdout)
        self.assertEqual(got[:3], [[553, "553"], [699, "699"], [603, "603"]],
                         "a value the page set for him (preset / number box / palette) was snapped: %r" % got)
        self.assertEqual(got[3:], [[500, "500"], [550, "550"]], "his drag does not land on a round ten: %r" % got)


RED_PROOF = [
    {"why": "v3885 round 1 - every input snaps again: the palette's 'mf 553' and his 553 / 699 presets read 550 / 700",
     "file": "bible.html",
     "find": "_v = (ev && ev.isTrusted) ? _mfSnap(_raw, mf) : _raw;",
     "replace": "_v = _mfSnap(_raw, mf);", "matches": 1, "needs": "node"},
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
