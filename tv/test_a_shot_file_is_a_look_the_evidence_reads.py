# -*- coding: utf-8 -*-
"""v3849 - an intake screenshot (shotFile) is a look the evidence panel reads.

vault intake stores shotFile on the Magic & Rare row and the bytes in IndexedDB.
The evidence looks and the panel used to ignore the field, so a shot-only keeper
read as no picture. The field is named on the look and on the panel. A shadow does
not ask IndexedDB (that store is sealed there).
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
SHOT_BRANCH = (
    "      if (mf.shotFile){\n"
    "        return [{ frame: null, shotFile: String(mf.shotFile), conf: null, cell: null, session: mf.sessionId || null,\n"
)
SHADOW_GUARD = "    else if (shot && !window._tvdShadow && typeof window._vGetShot === 'function') {"


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("%r occurs %d times" % (start[:40], src.count(start)))
    i = src.index(start)
    return src[i:src.index(end, i)]


CUT = _cut(SRC, "  window._vaultEvidenceLine = function(name){", "  window._vaultEvidencePicture = function(frameId, done, src){")

HARNESS = r"""
var window = globalThis, PROV = {}, magicFinds = {};
function _provAll(){ return PROV; }
window._ownedProvSourceSay = function(s){ return s === 'aic-judge' ? 'the AI item checker' : (s || 'UNKNOWN'); };
function jsArg(t){ return String(t); }
""" + CUT + r"""
magicFinds['Small Charm of Vita'] = { q: 'magic', base: 'Small Charm', mods: ['+17 to Life'], shotFile: 'shot_0042.png', at: 1700000000000 };
var look = window._vaultEvidenceLooks('Small Charm of Vita');
var of = window._vaultEvidenceOf('Small Charm of Vita');
var html = window._vaultEvidenceHtml(of, { state: 'shot', say: of.shotFile });
PROV.Named = { kind: 'owned', source: 'aic-judge', looks: [] };
magicFinds.Named = { shotFile: 'shot_0099.png', at: 1700000000000 };
var line = window._vaultEvidenceLine('Named');
var named = window._vaultEvidenceOf('Named');
process.stdout.write(JSON.stringify({
  look: look, shot: of.shotFile, tally: of.tallySay, html: html, line: line, namedShot: named.shotFile
}));
"""


class AShotFileIsALookTheEvidenceReads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        r = subprocess.run([NODE, "-"], input=HARNESS, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        if r.returncode != 0:
            raise AssertionError(r.stderr[-900:])
        cls.o = json.loads(r.stdout)

    def test_a_shot_only_keeper_names_its_file(self):
        self.assertEqual(len(self.o["look"]), 1)
        self.assertIsNone(self.o["look"][0]["frame"])
        self.assertEqual(self.o["look"][0]["shotFile"], "shot_0042.png")
        self.assertEqual(self.o["shot"], "shot_0042.png")
        self.assertEqual(self.o["tally"], "1 look")
        self.assertIn("Screenshot", self.o["html"])
        self.assertIn("shot_0042.png", self.o["html"])
        self.assertNotIn("no picture was saved for this item", self.o["tally"])

    def test_a_receipt_with_no_looks_still_names_the_shot(self):
        self.assertEqual(self.o["line"], "the AI item checker · 1 look")
        self.assertEqual(self.o["namedShot"], "shot_0099.png")
        self.assertEqual(SRC.count(SHOT_BRANCH), 1)
        self.assertEqual(SRC.count(SHADOW_GUARD), 1)


RED_PROOF = [
    {"why": "v3849 - a shot-only keeper is invisible to the evidence looks again",
     "file": "bible.html",
     "find": "      if (mf.shotFile){\n        return [{ frame: null, shotFile: String(mf.shotFile), conf: null, cell: null, session: mf.sessionId || null,\n",
     "replace": "      if (false){\n        return [{ frame: null, shotFile: String(mf.shotFile), conf: null, cell: null, session: mf.sessionId || null,\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
