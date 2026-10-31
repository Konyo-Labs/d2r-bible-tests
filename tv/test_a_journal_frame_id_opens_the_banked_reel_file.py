# -*- coding: utf-8 -*-
"""v3849 - a journal frame id <n>_<ms> opens the banked reel file f_<ms>.jpg.

The reel banks f_<ms>.jpg. A look that stores the journal id 3_<ms> was opened
as reel_.../3_<ms>.jpg, which is not the file. A bare millisecond, an f_ name,
cited.jpg and a reel-relative path stay as they were.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from console_safe import enable
enable()

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
NODE = shutil.which("node")
SRC = open(BIBLE, encoding="utf-8").read()
NMS = "    var nms = /^(\\d+)_(\\d{12,14})$/.exec(stem);\n"


def _fn_assign(src, start):
    if src.count(start) != 1:
        raise AssertionError("%r occurs %d times" % (start[:40], src.count(start)))
    i = src.index(start)
    b = src.index("{", i)
    depth = 0
    j = b
    n = len(src)
    while j < n:
        c = src[j]
        if c in ("'", '"', "`"):
            q = c
            j += 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == q:
                    j += 1
                    break
                j += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = src.index(";", j)
                return src[i:end + 1]
        j += 1
    raise AssertionError("look src never closed")


FN = _fn_assign(SRC, "  window._vaultLookSrc = function(look){")
HARNESS = "var window = {};\n" + FN + r"""
var s = function(frame, session){ return window._vaultLookSrc({ frame: frame, session: session }); };
process.stdout.write(JSON.stringify({
  journal: s('3_1784984175075', 's_9'),
  journalJpg: s('3_1784984175075.jpg', 'reel_s_9'),
  bucket: s('3_1784984175075#2', 's_9'),
  bareMs: s('1788820373017', 's_1786385768689_67392'),
  bareMsReel: s('1788820373017', 'reel_s_1786385768689_67392'),
  fPrefixed: s('f_1788820373017.jpg', 's_9_9'),
  filename: s('cited.jpg', 's0'),
  reelRel: window._vaultLookSrc({ frame: 'reel_s_9_9/f_777' }),
  reelRelJpg: window._vaultLookSrc({ frame: 'reel_s_9_9/f_777.jpg', session: null }),
  noReel: s('1788820373017', null),
  noFrame: s('', 's_9_9'),
  short: s('3_178', 's_9')
}));
"""


class AJournalFrameIdOpensTheBankedReelFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        r = subprocess.run([NODE, "-"], input=HARNESS, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        if r.returncode != 0:
            raise AssertionError(r.stderr[-900:])
        cls.o = json.loads(r.stdout)

    def test_a_journal_id_is_the_banked_f_file(self):
        o = self.o
        self.assertEqual(o["journal"], "tv/frames/hist/reel_s_9/f_1784984175075.jpg")
        self.assertEqual(o["journalJpg"], "tv/frames/hist/reel_s_9/f_1784984175075.jpg")
        self.assertEqual(o["bucket"], "tv/frames/hist/reel_s_9/f_1784984175075.jpg")
        self.assertEqual(o["short"], "tv/frames/hist/reel_s_9/3_178.jpg")

    def test_the_older_frame_shapes_stay(self):
        o = self.o
        self.assertEqual(o["bareMs"], "tv/frames/hist/reel_s_1786385768689_67392/f_1788820373017.jpg")
        self.assertEqual(o["bareMsReel"], "tv/frames/hist/reel_s_1786385768689_67392/f_1788820373017.jpg")
        self.assertEqual(o["fPrefixed"], "tv/frames/hist/reel_s_9_9/f_1788820373017.jpg")
        self.assertEqual(o["filename"], "tv/frames/hist/reel_s0/cited.jpg")
        self.assertEqual(o["reelRel"], "tv/frames/hist/reel_s_9_9/f_777.jpg")
        self.assertEqual(o["reelRelJpg"], "tv/frames/hist/reel_s_9_9/f_777.jpg")
        self.assertIsNone(o["noReel"])
        self.assertIsNone(o["noFrame"])
        self.assertEqual(SRC.count(NMS), 1)


RED_PROOF = [
    {"why": "v3849 - a journal frame id is opened as reel/<n>_<ms>.jpg again",
     "file": "bible.html",
     "find": "    var nms = /^(\\d+)_(\\d{12,14})$/.exec(stem);\n",
     "replace": "    var nms = null;\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
