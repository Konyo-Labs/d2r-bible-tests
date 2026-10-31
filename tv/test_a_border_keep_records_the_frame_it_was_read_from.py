# -*- coding: utf-8 -*-
"""v3849 - a border keep records the frame and session when the read knew them.

The keep tier wrote frameId and sessionId. The border tier wrote only
{q, base, mods, border:true}, so the magnifier could not name the picture.
Known frameId, sessionId and at are stored. Unknown ones are omitted, not
blank strings. A shotFile already on the row stays.
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
FRAME_LINE = "            if (meta && meta.frameId) row.frameId = meta.frameId;\n"
SESS_LINE = "            if (meta && (meta.sid || meta.sessionId)) row.sessionId = meta.sid || meta.sessionId;\n"


def _fn(src, start):
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
                return src[i:j + 1]
        j += 1
    raise AssertionError("border block never closed")


BLOCK = _fn(SRC, "      if (tier === 'border'){")
HARNESS = r"""
var tier = 'border', magicFinds, nm, q, base, mods, meta, out;
var LS = { setItem: function(){} };
function persistOwned(){}
function renderVault(){}
function go(){
""" + BLOCK + r"""
}
function fresh(prev, m){
  magicFinds = { 'Harlequin Crest': prev };
  nm = 'Harlequin Crest'; q = 'unique'; base = 'Shako'; mods = ['+2'];
  meta = m; out = { actions: [] };
  go();
  return magicFinds['Harlequin Crest'];
}
var known = fresh({ shotFile: 'shot_0042.png', q: 'magic', base: 'Shako', mods: ['+1'] },
                  { frameId: '3_1784984175075', sid: 's_abc', fts: 1784984175075 });
var blank = fresh({}, { frameId: '', sid: '', sessionId: '' });
var none = fresh({}, {});
var kept = fresh({ frameId: 'f_old', sessionId: 's_old', at: 10, shotFile: 'shot_keep.png' }, {});
process.stdout.write(JSON.stringify({ known: known, blank: blank, none: none, kept: kept, mode: out.mode }));
"""


class ABorderKeepRecordsTheFrameItWasReadFrom(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        r = subprocess.run([NODE, "-"], input=HARNESS, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        if r.returncode != 0:
            raise AssertionError(r.stderr[-900:])
        cls.o = json.loads(r.stdout)

    def test_a_known_frame_and_session_are_recorded_and_a_shot_stays(self):
        k = self.o["known"]
        self.assertEqual(k["frameId"], "3_1784984175075")
        self.assertEqual(k["sessionId"], "s_abc")
        self.assertEqual(k["at"], 1784984175075)
        self.assertEqual(k["shotFile"], "shot_0042.png")
        self.assertIs(k["border"], True)
        self.assertEqual(self.o["mode"], "border")

    def test_an_unknown_frame_is_omitted_and_an_old_one_stays(self):
        for row in (self.o["blank"], self.o["none"]):
            self.assertNotIn("frameId", row)
            self.assertNotIn("sessionId", row)
            self.assertNotIn("at", row)
        self.assertEqual(self.o["kept"]["frameId"], "f_old")
        self.assertEqual(self.o["kept"]["sessionId"], "s_old")
        self.assertEqual(self.o["kept"]["shotFile"], "shot_keep.png")
        self.assertEqual(self.o["kept"]["at"], 10)
        self.assertEqual(SRC.count(FRAME_LINE), 1)
        self.assertEqual(SRC.count(SESS_LINE), 1)


RED_PROOF = [
    {"why": "v3849 - a border keep drops the frame it was read from",
     "file": "bible.html",
     "find": "            if (meta && meta.frameId) row.frameId = meta.frameId;\n",
     "replace": "",
     "matches": 1},
    {"why": "v3849 - a border keep drops the session it was read in",
     "file": "bible.html",
     "find": "            if (meta && (meta.sid || meta.sessionId)) row.sessionId = meta.sid || meta.sessionId;\n",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
