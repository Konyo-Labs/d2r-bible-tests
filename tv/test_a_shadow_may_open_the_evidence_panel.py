# -*- coding: utf-8 -*-
"""v3849 - a shadow may open the evidence panel, read only.

The click veil's VIEW list did not name _vaultEvidenceOpen, so the magnifier's
button was stopped and the panel could not close either. Opening, stepping,
the lightbox and the close are view moves. A write is still stopped.
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
NAMES = "'_vaultEvidenceOpen', '_vaultEvidenceClose', '_vaultOpenEvidence', '_vaultEvidenceLightbox', '_vaultEvidenceStep'"


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
    raise AssertionError("viewOnly never closed")


VO = _fn(SRC, "    function viewOnly(el) {")
VIEW = SRC[SRC.index("    var VIEW = ['switchTab'"):SRC.index("    window._tvdShadowView = VIEW;")]

HARNESS = "var window = {};\nvar document = { addEventListener: function(){} };\n" + VIEW + "\n" + VO + r"""
function el(code){ return { getAttribute: function(n){ return n === 'onclick' ? code : null; }, matches: function(){ return false; } }; }
var out = {
  open: viewOnly(el("window._vaultEvidenceOpen('Shako')")),
  close: viewOnly(el("window._vaultEvidenceClose()")),
  step: viewOnly(el("window._vaultEvidenceStep(1)")),
  light: viewOnly(el("window._vaultEvidenceLightbox()")),
  wit: viewOnly(el("window._vaultOpenEvidence('Shako',0)")),
  write: viewOnly(el("window.magicFindsSave()")),
  post: viewOnly(el("fetch('/api/vault',{method:'POST'})"))
};
process.stdout.write(JSON.stringify(out));
"""


class AShadowMayOpenTheEvidencePanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        r = subprocess.run([NODE, "-"], input=HARNESS, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        if r.returncode != 0:
            raise AssertionError(r.stderr[-900:])
        cls.o = json.loads(r.stdout)

    def test_the_magnifier_is_on_the_view_list_and_a_write_is_not(self):
        self.assertEqual(SRC.count(NAMES), 1)
        self.assertTrue(self.o["open"] and self.o["close"] and self.o["step"] and self.o["light"] and self.o["wit"])
        self.assertFalse(self.o["write"])
        self.assertFalse(self.o["post"])


RED_PROOF = [
    {"why": "v3849 - the evidence magnifier is stopped in a shadow again",
     "file": "bible.html",
     "find": "'_vaultEvidenceOpen', '_vaultEvidenceClose', '_vaultOpenEvidence', '_vaultEvidenceLightbox', '_vaultEvidenceStep'",
     "replace": "'_vaultEvidenceClose', '_vaultOpenEvidence', '_vaultEvidenceLightbox', '_vaultEvidenceStep'",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
