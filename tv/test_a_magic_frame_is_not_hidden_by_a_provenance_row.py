# -*- coding: utf-8 -*-
"""v3849 - a Magic & Rare frame is a look even when a provenance row exists.

The evidence looks used to return only the provenance row, so a keeper's frameId was
dropped whenever any receipt existed, and the line still said "no picture recorded".
The frame is included whenever it exists. With no frame and no screenshot, the line
says "no picture was saved for this item".
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
APPEND = (
    "      if (!e.frame && e.shotFile && out.some(function(k){ return k && k.shotFile === e.shotFile; })) return;\n"
    "      out.push(e);\n"
)


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("%r occurs %d times" % (start[:40], src.count(start)))
    i = src.index(start)
    return src[i:src.index(end, i)]


CUT = _cut(SRC, "  window._vaultEvidenceLine = function(name){", "  window._vaultEvidenceOf = function(name){")

HARNESS = r"""
var window = globalThis, PROV = {}, magicFinds = {};
function _provAll(){ return PROV; }
window._ownedProvSourceSay = function(s){ return s === 'aic-judge' ? 'the AI item checker' : (s || 'UNKNOWN'); };
""" + CUT + r"""
PROV.Shako = { kind: 'owned', source: 'aic-judge', looks: [{ id: 's0', frame: 'cited.jpg', conf: 0.9 }] };
magicFinds.Shako = { frameId: '3_1784984175075', sessionId: 's_9', shotFile: 'shot_a.png' };
PROV.Empty = { kind: 'owned', source: 'aic-judge', looks: [] };
magicFinds.Empty = { frameId: '9_1784984175075', sessionId: 's_1' };
PROV.Bare = { kind: 'owned', source: 'aic-judge', looks: [] };
PROV.Same = { kind: 'owned', source: 'aic-judge', looks: [{ id: 's_9', frame: '3_1784984175075' }] };
magicFinds.Same = { frameId: '3_1784984175075', sessionId: 's_9', shotFile: 'shot_b.png' };
var both = window._vaultEvidenceLooks('Shako').map(function(k){ return k.frame; });
var line = window._vaultEvidenceLine('Empty');
var bare = window._vaultEvidenceLine('Bare');
var same = window._vaultEvidenceLooks('Same');
process.stdout.write(JSON.stringify({
  both: both,
  line: line,
  bare: bare,
  sameFrames: same.map(function(k){ return k.frame; }),
  sameShot: same.map(function(k){ return k.shotFile || null; })
}));
"""


class AMagicFrameIsNotHiddenByAProvenanceRow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        r = subprocess.run([NODE, "-"], input=HARNESS, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        if r.returncode != 0:
            raise AssertionError(r.stderr[-900:])
        cls.o = json.loads(r.stdout)

    def test_a_provenance_row_keeps_the_magic_frame(self):
        self.assertEqual(self.o["both"], ["cited.jpg", "3_1784984175075"])
        self.assertEqual(self.o["sameFrames"], ["3_1784984175075"])
        self.assertEqual(self.o["sameShot"], ["shot_b.png"])

    def test_the_line_counts_that_frame_and_says_when_none_was_saved(self):
        self.assertEqual(self.o["line"], "the AI item checker · 1 look")
        self.assertNotIn("no picture recorded", self.o["line"])
        self.assertEqual(self.o["bare"], "the AI item checker · no picture was saved for this item")
        self.assertEqual(SRC.count(APPEND), 1)


RED_PROOF = [
    {"why": "v3849 - a provenance row hides the keeper's frame again",
     "file": "bible.html",
     "find": "      if (!e.frame && e.shotFile && out.some(function(k){ return k && k.shotFile === e.shotFile; })) return;\n      out.push(e);\n",
     "replace": "      if (!e.frame && e.shotFile && out.some(function(k){ return k && k.shotFile === e.shotFile; })) return;\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
