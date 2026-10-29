# -*- coding: utf-8 -*-
"""#86 (REG-2791, GrokBot's v3642 pass) - KAI'S UNREAD TEXT IS SHOWN AS THE OCR READ IT, AND SAYS SO.

GrokBot, Shelf > Theatre Sess 48 frame 27/28: "the caught-text chip shows raw markup - `missed -> KAI caught (retro):
CHAKm •<li•`". It is not markup. kaiMissTexts (a footage beat) and kai.texts (a kai beat) are the KAI closer's
`missed[].texts`: OCR off a film still no eye read. MEASURED read-only 2026-10-28: 1,029 such texts on his 38 sealed reels,
10 with a '<' or '>'; 8,637 on the journal's kai rows, 45 with one, 4 distinct - 'FAsT ArrA<K SpfE' (ATTACK SPEED),
'kf>uiRfD STRENGT' (REQUIRED STRENGTH), '*NVS T• A TTA<X RATIN', '>-Diablos' - each a letter the OCR misread, none a tag.
The chips printed them bare beside "KAI caught", so garble read as leaked HTML and as a catch.

A read is testimony and is never cleaned: each text is escaped and quoted verbatim by one helper (_ocrRawSay), and the
three surfaces that print it (the footage chip, the kai chip, the kai caption) say it is raw OCR.

REG-3106 (#86 item 5) asked again whether markup-shaped garble should read as "unreadable text (N chars)" with the raw
text in a title. Decided from the code and the reads: no. The same measured garbles are a reader's evidence - 'FAsT ArrA<K
SpfE' is ATTACK SPEED, 'kf>uiRfD STRENGT' is REQUIRED STRENGTH - and a count in the chip would hide them behind a hover
that a touch screen and a glance never make, the very hiding REG-2791 ruled out ("a read is testimony and is never
cleaned"). Its quoting, its escaping and its "raw OCR" label already answer GrokBot's "looks like leaked HTML". What was
not locked: every check above read the whole span, title included, so moving the read into the title would have passed.
Now the read must be on the chip's face, outside every attribute, and no surface may stand a count in for it.

Driven: esc, _ocrRawSay, thHandoffNote and _thKaiCaption cut out of control_ui.html and run in node; each quoted text is
unescaped and compared to what the OCR read, character for character. RED_PROOF below.
"""
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

NODE = shutil.which("node")
UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
FNS = ["  function esc(s){", "  function _ocrRawSay(texts, max){", "  function thHandoffNote(b){",
       "  function _thKaiCaption(b){"]

# what the OCR read on his reels, verbatim (GrokBot's chip first)
READ = ["CHAKm •<li•", "FAsT ArrA<K SpfE", "kf>uiRfD STRENGT", ">-Diablos", "QufST L•"]


def _cut(sig):
    if UI.count(sig) != 1:
        raise AssertionError("%r occurs %d times - this law cannot see its subject" % (sig, UI.count(sig)))
    i = UI.index(sig)
    b = UI.index("{", i)
    depth = 0
    for j in range(b, len(UI)):
        if UI[j] == "{":
            depth += 1
        elif UI[j] == "}":
            depth -= 1
            if depth == 0:
                return UI[i:j + 1]
    raise AssertionError("%r never closed - harness fault, not a pass" % sig)


HARNESS = r"""
import { readFileSync } from 'node:fs';
const CFG = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const f = new Function(CFG.fns + '\nreturn { hand: thHandoffNote, cap: _thKaiCaption };')();
process.stdout.write(JSON.stringify(CFG.cases.map(c => f[c.fn](c.b))));
"""


def _drive(cases):
    if NODE is None:
        raise AssertionError("node is not on this machine - this law does not skip")
    d = tempfile.mkdtemp(prefix="ocr_raw_")
    try:
        h, c = os.path.join(d, "h.mjs"), os.path.join(d, "cfg.json")
        io.open(h, "w", encoding="utf-8").write(HARNESS)
        io.open(c, "w", encoding="utf-8").write(json.dumps({"fns": "\n".join(_cut(s) for s in FNS), "cases": cases}))
        r = subprocess.run([NODE, h, c], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=60, env=dict(os.environ, TZ="UTC"))
    finally:
        shutil.rmtree(d, True)
    if r.returncode != 0:
        raise AssertionError("node failed: %s" % r.stderr[-900:])
    return json.loads(r.stdout)


def _quoted(out):
    """The texts the chip quotes, unescaped back to what a reader sees. -> [str]"""
    return [html.unescape(q) for q in re.findall("“([^”]*)”", out)]


class UnreadTextIsShownAsTheOcrReadIt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.foot, cls.kai, cls.cap = _drive([
            {"fn": "hand", "b": {"footage": True, "kaiMissTexts": READ[:4]}},
            {"fn": "hand", "b": {"lane": "kai", "kai": {"texts": READ[1:4]}}},
            {"fn": "cap", "b": {"lane": "kai", "kai": {"texts": READ}, "ts": 1793189802000}},
        ])

    def chip(self, out, read, more):
        self.assertIn("raw OCR", out, "the chip does not say its text is raw OCR: %r" % out)
        self.assertEqual(_quoted(out), read, "the chip did not print the OCR's read verbatim, one quote each: %r" % out)
        for t in read:
            if "<" in t or ">" in t:
                self.assertNotIn(t, out, "an OCR read went into the page unescaped: %r" % out)
        if more:
            self.assertIn(" +%d" % more, out, "the texts past the cap are not counted: %r" % out)

    def test_the_footage_chip(self):
        self.chip(self.foot, READ[:3], 1)
        self.assertNotIn("(retro): CHAKm", self.foot, "GrokBot's chip, bare: %r" % self.foot)

    def test_the_kai_chip(self):
        self.chip(self.kai, READ[1:4], 0)

    def test_the_kai_caption(self):
        self.chip(self.cap, READ[:4], 1)
        self.assertIn("unread text on this frame", self.cap)

    def test_the_read_is_on_the_chips_face_never_only_in_a_title(self):
        """REG-3106 - the quoted reads sit in the visible text (every attribute stripped), and no count stands in."""
        for out, read in ((self.foot, READ[:3]), (self.kai, READ[1:4]), (self.cap, READ[:4])):
            face = re.sub(r'\s[a-z-]+="[^"]*"', "", out)
            self.assertEqual(_quoted(face), read, "the OCR's read is not on the chip's face: %r" % out)
            self.assertIn("raw OCR", face, "the chip's face does not say its text is raw OCR: %r" % out)
            self.assertNotRegex(face, r"(?i)unreadable|\(\d+ chars?\)", "a count stands in for the read: %r" % out)


RED_PROOF = [
    {"why": "REG-3106 - the footage chip shows a count and hides the read in its title",
     "file": "tv/control_ui.html",
     "find": "stray marks and all; it is not a name yet\">🔴 missed → 🧠 KAI caught unread text · raw OCR: '\n        + _ocrRawSay(b.kaiMissTexts, 3) + '</span>';\n",
     "replace": "stray marks and all; it is not a name yet. raw OCR: ' + _ocrRawSay(b.kaiMissTexts, 3) + '\">🔴 missed → 🧠 KAI caught unreadable text (' + b.kaiMissTexts.join('').length + ' chars)</span>';\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3106 - the kai chip shows a count and hides the read in its title",
     "file": "tv/control_ui.html",
     "find": "stray marks and all\">🔴 missed → 🧠 KAI caught unread text · raw OCR: ' + _ocrRawSay(kk.texts, 3) + '</span>';   /* REG-2791 */\n",
     "replace": "stray marks and all · raw OCR: ' + _ocrRawSay(kk.texts, 3) + '\">🔴 missed → 🧠 KAI caught unreadable text (' + kk.texts.join('').length + ' chars)</span>';   /* REG-2791 */\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2791 - the footage chip prints the OCR bare beside 'KAI caught' again (GrokBot's CHAKm •<li•)",
     "file": "tv/control_ui.html",
     "find": "        + _ocrRawSay(b.kaiMissTexts, 3) + '</span>';\n",
     "replace": "        + esc(b.kaiMissTexts.slice(0, 3).join(', ')) + (b.kaiMissTexts.length > 3 ? ' +' + (b.kaiMissTexts.length - 3) : '') + '</span>';\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2791 - an OCR read goes into the page unescaped",
     "file": "tv/control_ui.html",
     "find": "    return t.slice(0, max).map(function(x){ return '“' + esc(String(x)) + '”'; }).join(', ')\n",
     "replace": "    return t.slice(0, max).map(function(x){ return '“' + String(x) + '”'; }).join(', ')\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2791 - the display 'cleans' the OCR read, so the chip no longer shows what was read",
     "file": "tv/control_ui.html",
     "find": "    return t.slice(0, max).map(function(x){ return '“' + esc(String(x)) + '”'; }).join(', ')\n",
     "replace": "    return t.slice(0, max).map(function(x){ return '“' + esc(String(x).replace(/[<>•*]/g, '')) + '”'; }).join(', ')\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2791 - the kai chip prints the OCR bare again",
     "file": "tv/control_ui.html",
     "find": "' + _ocrRawSay(kk.texts, 3) + '</span>';   /* REG-2791 */\n",
     "replace": "' + esc(kk.texts.slice(0, 3).join(', ')) + '</span>';\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2791 - the kai caption prints the OCR bare again",
     "file": "tv/control_ui.html",
     "find": "_ocrRawSay(kk.texts, 4) + when + '</span>';   /* REG-2791 */\n",
     "replace": "esc((kk.texts || []).slice(0, 4).join(', ')) + when + '</span>';\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2791 - the footage chip calls the garble a catch and stops saying it is raw OCR",
     "file": "tv/control_ui.html",
     "find": "🔴 missed → 🧠 KAI caught unread text · raw OCR: '\n        + _ocrRawSay(b.kaiMissTexts, 3)",
     "replace": "🔴 missed → 🧠 KAI caught (retro): '\n        + _ocrRawSay(b.kaiMissTexts, 3)",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
