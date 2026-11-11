# -*- coding: utf-8 -*-
"""v3898 (card #209, GrokBot #230 6795677353) - A FRAME THE RECORDER MARKED BLANK IS NEVER A THEATRE PHOTO.

GrokBot's look at his Mac's 3 Nov reel (session s_1793705809306_17617): the recorder's own index.json marks 65 of its 290
film frames `blank: true` (near-black - a pixel recount found 64), and the session record says 22 of 97 read photos are
missing on disk (frameMissing). The Theatre counted every film frame as a photo, drew a filmstrip tile for each black one
and stepped through them with ← / →, because the beat builder never carried the recorder's mark onto the film beat.

Now the film beat carries `blank` from index.json (absent stays absent), the Theatre leaves blank beats out of the photo
count, the filmstrip and photo stepping, and the mode pill's hover says what was left out in plain words: "65 blank frames
the recorder marked (skipped) · 22 read photos missing on disk".

DRIVEN: the shipped thBeatIsPhoto / thSessionPhotoStats / thFramedIndices / thLeftOutSay, cut from tv/control_ui.html and run
in node on a fixture reel; the server's pass-through read from its one line. RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import js_strip  # noqa: E402  (one comment stripper for the laws)
from cb_node_harness import NODE  # noqa: E402

FUNCS = ("thBeatIsPhoto", "thSessionPhotoStats", "thLeftOutSay", "thFramedIndices")


def _ui():
    with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
        return fh.read()


def _function(src, name):
    head = "  function %s(" % name
    assert src.count(head) == 1, "PREMISE: %s is declared %d times" % (name, src.count(head))
    i = src.index(head)
    if src[i:].split("\n", 1)[0].rstrip().endswith("}"):       # a one-line function
        return src[i:src.index("\n", i) + 1]
    j = src.index("\n  }\n", i)
    return src[i:j + 4]


def _run(fixture):
    if NODE is None:
        raise AssertionError("node is not installed on this PC - this law runs the shipped Theatre in node and does not skip")
    src = _ui()
    prog = "var TH = {};\n" + "\n".join(_function(src, f) for f in FUNCS) + r"""
var fx = JSON.parse(process.argv[2]);
TH.allBeats = fx.beats; TH.beats = fx.beats; TH.sessions = [fx.session]; TH.sn = 1;
var st = thSessionPhotoStats();
console.log(JSON.stringify({ st: st, framed: thFramedIndices(fx.beats), say: thLeftOutSay(st) }));
"""
    d = tempfile.mkdtemp(prefix="blank_frame_")
    try:
        h = os.path.join(d, "h.js")
        with io.open(h, "w", encoding="utf-8") as fh:
            fh.write(prog)
        r = subprocess.run([NODE, h, json.dumps(fixture)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    finally:
        shutil.rmtree(d, True)
    if r.returncode != 0:
        raise AssertionError("node failed: %s" % r.stderr.decode("utf-8", "replace")[-800:])
    return json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])


def _reel():
    """3 film frames (one blank), 1 read with its photo, 1 read whose photo is missing (frame '')"""
    return {"beats": [{"footage": True, "frame": "reel/f_1.jpg"},
                      {"footage": True, "frame": "reel/f_2.jpg", "blank": True},
                      {"footage": True, "frame": "reel/f_3.jpg"},
                      {"frame": "1.jpg", "frameOk": True},
                      {"frame": "", "frameOk": False}],
            "session": {"frameMissing": 22}}


class ABlankFrameIsNeverATheatrePhoto(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = _run(_reel())

    def test_a_blank_frame_is_not_counted_as_a_photo(self):
        """* THE POINT - 3 photos (2 film + 1 read), never the black frame"""
        self.assertEqual(self.out["st"]["allPhoto"], 3, "a frame the recorder marked blank was counted as a photo")
        self.assertEqual(self.out["st"]["allBlank"], 1)

    def test_no_blank_tile_and_no_blank_step(self):
        self.assertEqual(self.out["framed"], [0, 2, 3], "the filmstrip / ← → still lands on the blank frame")

    def test_what_was_left_out_is_said_in_words(self):
        say = self.out["say"]
        self.assertIn("1 blank frame the recorder marked (skipped)", say, "the hover does not say a blank frame was skipped")
        self.assertIn("22 read photos missing on disk", say, "the hover does not say the read photos missing on disk")

    def test_an_unknown_missing_count_says_nothing(self):
        """BASELINE - no blank and no frameMissing: no claim, never a confident zero"""
        out = _run({"beats": [{"footage": True, "frame": "reel/f_1.jpg"}], "session": {}})
        self.assertEqual(out["say"], "", "a reel with nothing left out still claims something was")
        self.assertEqual(out["st"]["allPhoto"], 1)

    def test_the_server_carries_the_recorders_mark(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            code = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
        self.assertEqual(code.count('**({"blank": True} if it.get("blank") is True else {}),'), 1,
                         "the film beat no longer carries the recorder's blank mark - the Theatre cannot skip it")


RED_PROOF = [
    {"why": "v3898 (#209) - a frame the recorder marked blank counts as a Theatre photo again",
     "file": "tv/control_ui.html",
     "find": "  function thBeatIsPhoto(b){ return !!(b && b.frame && !b.blank); }\n",
     "replace": "  function thBeatIsPhoto(b){ return !!(b && b.frame); }\n",
     "matches": 1, "needs": "node"},
    {"why": "v3898 (#209) - the hover stops saying how many read photos are missing on disk",
     "file": "tv/control_ui.html",
     "find": "    if (typeof miss === 'number' && miss > 0) parts.push(",
     "replace": "    if (false) parts.push(",
     "matches": 1, "needs": "node"},
    {"why": "v3898 (#209) - the film beat drops the recorder's blank mark",
     "file": "tv/control_app.py",
     "find": "                            **({\"blank\": True} if it.get(\"blank\") is True else {}),\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
