# -*- coding: utf-8 -*-
"""v3864 (his ruling 2026-11-05 (c), card 33) - A VAULT MULE CARD'S ✕ REMOVES ONE COPY, AFTER AN IN-PAGE CONFIRMATION.

His words: "remove the copy with a popup message confirmation confirming it". The chain's per-copy ✕ (REG-2849) removed the
copy at once (Undo put it back). Now every ✕ that takes out one copy - the tile, the MAGIC & RARE cell, the MOVE row's
expand - calls vaultRemoveCopyAsk, which asks in the board's own uiConfirm (Cancel focused, never the OS confirm box) and
only then calls the door. No uiConfirm on the page refuses: a copy is never removed without the question. The page's own
function is run in node with a stand-in popup. RED_PROOF below.
"""
import io
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
START = "  window.vaultRemoveCopyAsk = async function(name, copyIx){\n"


def _src():
    s = io.open(BIBLE, encoding="utf-8").read()
    i = s.index(START)
    j = s.index("\n  };\n", i) + len("\n  };\n")
    return s, s[i:j]


class ACopyXAsksBeforeItRemoves(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.page, fn = _src()
        prog = """
var window = {}; var removed = [], asked = [];
function copyCount(n){ return 3; }
window.vaultRemoveCopy = function(n, k){ removed.push([n, k]); return { ok: true }; };
""" + fn + """
(async function(){
  var out = {};
  window.uiConfirm = function(msg, o){ asked.push([msg, o]); return Promise.resolve(false); };
  out.no = await window.vaultRemoveCopyAsk('Nagelring', 1); out.noRemoved = removed.length;
  window.uiConfirm = function(msg, o){ asked.push([msg, o]); return Promise.resolve(true); };
  out.yes = await window.vaultRemoveCopyAsk('Nagelring', 1); out.yesRemoved = removed.slice();
  delete window.uiConfirm;
  out.none = await window.vaultRemoveCopyAsk('Nagelring', 0); out.noneRemoved = removed.length;
  out.asked = asked;
  process.stdout.write(JSON.stringify(out));
})();
"""
        r = subprocess.run(["node", "-"], input=prog, capture_output=True, text=True, encoding="utf-8", timeout=60)
        if r.returncode != 0:
            raise AssertionError("the page's ask would not run in node: " + r.stderr[-800:])
        cls.o = json.loads(r.stdout)

    def test_no_removes_nothing(self):
        self.assertEqual((self.o["no"]["refused"], self.o["noRemoved"]), ("kept", 0), self.o["no"])

    def test_yes_removes_exactly_that_copy(self):
        self.assertEqual(self.o["yesRemoved"], [["Nagelring", 1]], "the copy he confirmed is not the one removed")

    def test_no_box_means_no_removal_never_the_os_confirm(self):
        self.assertEqual((self.o["none"]["refused"], self.o["noneRemoved"]), ("no-confirm", 1), self.o["none"])
        _p, fn = _src()
        self.assertIsNone(re.search(r"(?<![\w.])confirm\(|window\.confirm\(", fn), "the ask falls back to the OS confirm box")

    def test_the_question_names_the_copy_and_keeps_cancel_first(self):
        msg, opts = self.o["asked"][0]
        self.assertIn("copy 2 of 3 of Nagelring", msg)
        self.assertIn("2 copies stay", msg)
        self.assertIs(opts.get("cancelFirst"), True, "Enter on the popup would remove the copy: %r" % opts)

    def test_every_copy_x_asks_first(self):
        s = self.page
        self.assertEqual(s.count("window.vaultRemoveCopyAsk("), 3, "a one-copy ✕ (tile, MAGIC & RARE cell, MOVE row) does not ask")
        bare = re.findall(r"onclick=\\?\"[^\"]*window\.vaultRemoveCopy\(", s)
        self.assertEqual(bare, [], "a ✕ still removes a copy without asking: %r" % bare[:3])


RED_PROOF = [
    {"why": "v3864 - the ask removes the copy whatever he answers",
     "file": "bible.html",
     "find": "    if (!yes) return { ok: false, refused: 'kept', why: 'he kept it' };\n",
     "replace": "",
     "matches": 1},
    {"why": "v3864 - with no popup on the page the copy is removed unasked",
     "file": "bible.html",
     "find": "    if (typeof window.uiConfirm !== 'function') return { ok: false, refused: 'no-confirm', why: 'the board has no confirmation box here - nothing was removed' };\n",
     "replace": "    if (typeof window.uiConfirm !== 'function') return window.vaultRemoveCopy(name, copyIx);\n",
     "matches": 1},
    {"why": "v3864 - the tile's ✕ removes a copy without asking",
     "file": "bible.html",
     "find": "' onclick=\"event.stopPropagation();window.vaultRemoveCopyAsk(\\'' + jsArg(p.n) + '\\', ' + _rcK + ')\">✕</button>';",
     "replace": "' onclick=\"event.stopPropagation();window.vaultRemoveCopy(\\'' + jsArg(p.n) + '\\', ' + _rcK + ')\">✕</button>';",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
