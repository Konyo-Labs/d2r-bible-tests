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
The evidence panel Tier row uses the same clause. A Wilson number already on the row stays beside
it. A tier word with no trial counts stays the bare word.
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


def _node_json(expr):
    """A program on argv is refused past 128 KB on CI. The expression goes in on stdin."""
    prog = "process.stdout.write(JSON.stringify(%s))" % expr
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=15, check=True)
    return json.loads(r.stdout)


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
        # v3855 item E (his ruling): plain words on the face; the gold seal is the mark
        self.assertIn("WATCHED: 'Not confirmed yet'", literal)
        self.assertIn("PROVEN: 'Not confirmed yet'", literal)
        self.assertIn("HARDENED: 'Confirmed'", literal)
        line = src[src.index("window._vaultEvidenceLine = function"):src.index("window._vaultLookSrc = function")]
        self.assertIn("_TIER_FACE[r.tier]", line)
        self.assertNotIn("WATCHED:", line, "the evidence line grew a second tier map")
        self.assertIn("if (r.kind === 'owned') return who + ' · ' + tally;", line)

    def test_a_judged_row_wears_the_face_and_a_receipt_does_not(self):
        src = _page()
        face = _node_json(_face_literal(src))
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

    def test_the_evidence_panel_tier_row_wears_the_same_clause(self):
        """The panel Tier row is the same judged record as the chip. It wears the clause. Wilson stays on the row."""
        src = _page()
        sig = "window._vaultTierFaceClause = function"
        self.assertEqual(src.count(sig), 1)
        fn = _brace(src, sig)
        self.assertNotIn("WATCHED:", fn, "the panel clause grew a second tier map")
        join = ("      var _tierClause = window._vaultTierFaceClause(r);\n"
                "      if (_tierClause) m.tierSay = _tierClause\n"
                "                            + (typeof r.wilson === 'number' ? ' (Wilson ' + r.wilson.toFixed(2) + ')' : '');\n"
                "      else if (r.tier) m.tierSay = r.tier\n")
        self.assertEqual(src.count(join), 1, "the panel stopped using the clause, or Wilson left the row")
        self.assertEqual(src.count("row('Tier', m.tierSay)"), 1)
        face = _node_json(_face_literal(src))
        got = _drive_clause("var _TIER_FACE = %s;\n" % _face_literal(src), fn)
        bare = _drive_clause("", fn)
        self.assertEqual(got["proven"], face["PROVEN"] + " 12/12")
        self.assertEqual(got["watched"], face["WATCHED"] + " 1/1")
        self.assertEqual(got["hardened"], face["HARDENED"] + " 21/21")
        self.assertEqual(got["stranger"], "GOLD 3/3")
        self.assertEqual(got["bare"], "")
        self.assertEqual(got["receipt"], "")
        self.assertEqual(got["none"], "")
        self.assertNotIn("session", got["proven"])
        self.assertEqual(bare["proven"], "PROVEN 12/12")
        self.assertEqual(bare["watched"], "WATCHED 1/1")
        self.assertEqual(bare["bare"], "")


def _brace(src, sig):
    i = src.index(sig)
    b = src.index("{", i)
    depth = 0
    for k in range(b, len(src)):
        c = src[k]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = k + 1
                if src[end:end + 1] == ";":
                    end += 1
                return src[i:end]
    raise AssertionError("the tier clause function does not close")


def _drive_clause(prefix, fn):
    if NODE is None:
        raise AssertionError("node is absent — the panel clause was not driven")
    body = r"""
process.stdout.write(JSON.stringify({
  proven: window._vaultTierFaceClause({tier:'PROVEN', successes:12, trials:12, wilson:0.9}),
  watched: window._vaultTierFaceClause({tier:'WATCHED', successes:1, trials:1}),
  hardened: window._vaultTierFaceClause({tier:'HARDENED', successes:21, trials:21, locked:true}),
  stranger: window._vaultTierFaceClause({tier:'GOLD', successes:3, trials:3}),
  bare: window._vaultTierFaceClause({tier:'WATCHED', source:'stash'}),
  receipt: window._vaultTierFaceClause({kind:'owned', source:'kai-register'}),
  none: window._vaultTierFaceClause(null)
}));
"""
    prog = "var window = globalThis;\n" + prefix + fn + "\n" + body
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError("the panel clause would not run — UNKNOWN, not passing: %s"
                             % (r.stderr or r.stdout)[-800:])
    return json.loads(r.stdout)


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
    {"why": "REG-3110 - the evidence panel Tier row says the bare tier word again",
     "file": "bible.html",
     "find": "    var face = (typeof _TIER_FACE === 'object' && _TIER_FACE && typeof _TIER_FACE[tier] === 'string') ? _TIER_FACE[tier] : tier;\n    return face + ' ' + r.successes + '/' + r.trials;\n",
     "replace": "    var face = tier;\n    return face + ' ' + r.successes + '/' + r.trials;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3110 - the evidence panel ignores the tier clause",
     "file": "bible.html",
     "find": "      if (_tierClause) m.tierSay = _tierClause\n",
     "replace": "      if (r.tier) m.tierSay = r.tier\n",
     "matches": 1, "needs": "node"},
]
