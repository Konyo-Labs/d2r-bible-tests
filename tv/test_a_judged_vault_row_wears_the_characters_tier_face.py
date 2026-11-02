# -*- coding: utf-8 -*-
"""#26 (REG-3110) - A JUDGED VAULT ROW WEARS THE CHARACTERS ROOM'S ONE TIER FACE.

GrokBot on v3838 read a vault cell as "evidence: the live reader (KAI register) · 1 look" and no
WATCHED / PROVEN / HARDENED. That chip is a receipt (kind owned, source kai-register). A receipt
is not a judged tier, and it must not grow one. The judged path (tier plus numeric successes and
trials) said the bare word. It now says the Characters room's _TIER_FACE, the one map. A tier the
map does not name stays the word it is. A witnessed row that the table has not judged still ends
tier UNKNOWN.

The evidence-line cut runs twice: once with the page's map in scope, once without it. Without the
map the standing sentence stays "PROVEN 12/12", which is what the cut-only harness already pins.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable; enable()

NODE = shutil.which("node")
BIBLE = os.path.join(ROOT, "bible.html")
BEGIN = "⟦VAULT EVIDENCE LINE BEGIN⟧"
END = "⟦VAULT EVIDENCE LINE END⟧"

HARNESS = r"""
var window = globalThis, STORE = {};
window.LSR = {
  getItem: function(k){ return Object.prototype.hasOwnProperty.call(STORE, k) ? STORE[k] : null; },
  setItem: function(k, v){ STORE[k] = String(v); } };
function _provAll(){
  try { var v = JSON.parse(window.LSR.getItem('d2r_vaultProv') || '{}'); return v || {}; }
  catch (e) { return {}; } }
function esc(t){ return String(t == null ? '' : t); }
"""

BODY = r"""
STORE['d2r_vaultProv'] = JSON.stringify({
  Shako: { tier: 'PROVEN', successes: 12, trials: 12, sessions: ['s0', 's1', 's2'], source: 'stash',
           looks: [{ id: 's0', frame: 'cited.jpg', conf: 0.91 }] },
  Watched: { tier: 'WATCHED', successes: 1, trials: 1, sessions: ['s1'], source: 'stash',
             looks: [{ id: 's1', frame: 'a.jpg', conf: 0.9 }] },
  Hard: { tier: 'HARDENED', successes: 21, trials: 21, sessions: ['h'], locked: true, source: 'stash',
          looks: [{ id: 'h', frame: 'b.jpg', conf: 0.9 }] },
  Gold: { tier: 'GOLD', successes: 3, trials: 3, sessions: ['g'], source: 'stash',
          looks: [{ id: 'g', frame: 'c.jpg', conf: 0.9 }] },
  Receipt: { kind: 'owned', source: 'kai-register', looks: [{ id: 's_r', frame: 'f_1.jpg', conf: 0.9 }] },
  Normal: { source: 'stash', looks: [{ id: 'a', frame: 'f_2.jpg', conf: 0.9 }, { id: 'b', frame: 'f_3.jpg', conf: 0.88 }],
            gate: { pass: true, looks: 2 } },
  Bare: { tier: 'WATCHED', source: 'stash', looks: [{ id: 'z', frame: 'f_4.jpg', conf: 0.9 }] }
});
process.stdout.write(JSON.stringify({
  proven: window._vaultEvidenceLine('Shako'),
  watched: window._vaultEvidenceLine('Watched'),
  hardened: window._vaultEvidenceLine('Hard'),
  stranger: window._vaultEvidenceLine('Gold'),
  receipt: window._vaultEvidenceLine('Receipt'),
  witnessed: window._vaultEvidenceLine('Normal'),
  bare: window._vaultEvidenceLine('Bare')
}));
"""


def _page():
    with io.open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _cut(src):
    if src.count(BEGIN) != 1 or src.count(END) != 1:
        raise AssertionError("the evidence line markers are not one each")
    i = src.index(BEGIN)
    j = src.index(END, i) + len(END)
    return src[src.rfind("\n", 0, i) + 1:src.index("\n", j) + 1]


def _face_literal(src):
    sig = "var _TIER_FACE = "
    if src.count(sig) != 1:
        raise AssertionError("_TIER_FACE is defined %d times" % src.count(sig))
    i = src.index(sig) + len(sig)
    j = src.index(";", i)
    return src[i:j]


def _drive(prefix):
    if NODE is None:
        raise AssertionError("node is absent — the evidence line was not driven")
    prog = HARNESS + prefix + "\n" + _cut(_page()) + "\n" + BODY
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError("the evidence line would not run — UNKNOWN, not passing: %s"
                             % (r.stderr or r.stdout)[-800:])
    return json.loads(r.stdout)


class AJudgedVaultRowWearsTheCharactersTierFace(unittest.TestCase):
    def test_the_page_has_one_face_map_and_the_judged_line_calls_it(self):
        src = _page()
        literal = _face_literal(src)
        self.assertIn("WATCHED: '👁 WATCHED'", literal)
        self.assertIn("PROVEN: '✓ PROVEN'", literal)
        self.assertIn("HARDENED: '🔒 HARDENED'", literal)
        line = src[src.index("window._vaultEvidenceLine = function"):src.index("window._vaultLookSrc = function")]
        self.assertIn("_TIER_FACE[r.tier]", line)
        self.assertNotIn("WATCHED:", line, "the evidence line grew a second tier map")
        self.assertIn("if (r.kind === 'owned') return who + ' · ' + tally;", line)

    def test_a_judged_row_wears_the_face_and_a_receipt_does_not(self):
        src = _page()
        face = json.loads(subprocess.run(
            [NODE, "-e", "process.stdout.write(JSON.stringify(%s))" % _face_literal(src)],
            capture_output=True, text=True, timeout=15, check=True).stdout)
        got = _drive("var _TIER_FACE = %s;" % _face_literal(src))
        self.assertEqual(got["proven"], face["PROVEN"] + " 12/12 · 3 sessions")
        self.assertEqual(got["watched"], face["WATCHED"] + " 1/1 · 1 session")
        self.assertEqual(got["hardened"], face["HARDENED"] + " 21/21 · 1 session · 🔒 locked")
        self.assertEqual(got["stranger"], "GOLD 3/3 · 1 session", "a tier the map does not name was replaced")
        self.assertEqual(got["receipt"], "kai-register · 1 look", "a receipt's line must not claim a tier")
        self.assertNotIn("👁", got["receipt"])
        self.assertEqual(got["witnessed"], "filed · stash · 2 looks · gate passed on 2 · tier UNKNOWN")
        self.assertNotIn("👁", got["witnessed"])
        self.assertIn("tier UNKNOWN", got["bare"], "a tier word with no trial counts was treated as judged")
        self.assertNotIn("👁", got["bare"])

    def test_without_the_map_the_standing_sentence_stays(self):
        """The cut-only harness does not see _TIER_FACE. The sentence it already pins must stay."""
        got = _drive("")
        self.assertEqual(got["proven"], "PROVEN 12/12 · 3 sessions")
        self.assertEqual(got["watched"], "WATCHED 1/1 · 1 session")
        self.assertEqual(got["receipt"], "kai-register · 1 look")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "REG-3110 - a judged row says the bare tier word again",
     "file": "bible.html",
     "find": "      var face = (typeof _TIER_FACE === 'object' && _TIER_FACE && typeof _TIER_FACE[r.tier] === 'string') ? _TIER_FACE[r.tier] : r.tier;\n      return face + ' ' + r.successes + '/' + r.trials\n",
     "replace": "      return r.tier + ' ' + r.successes + '/' + r.trials\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3110 - a receipt claims WATCHED",
     "file": "bible.html",
     "find": "    if (r.kind === 'owned') return who + ' · ' + tally;\n",
     "replace": "    if (r.kind === 'owned') return '👁 WATCHED · ' + tally;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3110 - a witnessed row that was not judged says WATCHED",
     "file": "bible.html",
     "find": "      + ' · tier UNKNOWN';\n",
     "replace": "      + ' · tier WATCHED';\n",
     "matches": 1, "needs": "node"},
]
