# -*- coding: utf-8 -*-
"""#158 (GrokBot #230; REG-2730) - AN IMAGE ERROR SAYS WHICH.

GrokBot counted 335 kai-funnel intake rows on his Mac and found no reason on them. Most did carry one - "read failed -
1 image error" - and that sentence was the whole of it. An image error is the board's _tallyRead returning null, and three
different failures did that without a word: the intake answered an HTTP error, it answered with an error field, or the
request itself threw. _tallyRead now names the failed pass's cause into an object its caller passes (`why`); the gems,
runes and materials readers keep the first one as `errWhy`; the live tally post and the console's kai-funnel post carry
it; and the journal's reason reads "read failed - 1 image error - the intake answered HTTP 503". Nothing about the read
itself changes - not the prompt, the model, the crop or the vote (all locked).

_tallyRead is driven in node, cut from bible.html, over a stubbed fetch. RED_PROOF below.

REG-2978 (#158, the v3834 second eye): _tallyRead reads its answer through window._intakeAnswer (beside the refusal rule), so
an HTTP error and an error field say the rule's sentence - "the reader answered HTTP 503", "the reader refused (overloaded)",
and a cap its own "the reader is at its cap (...) - HTTP 429" - where they said "HTTP 429" alone. The rule and the reader are
cut in beside _tallyRead.
"""
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
from cb_node_harness import NODE  # noqa: E402
import control_app as CA  # noqa: E402

BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
START = "async function _tallyRead(b64, vocab, layout, kind, why){\n"
END = "\nwindow._tallyRead = _tallyRead;\n"

PROGRAM = r"""
var window = { _d2rIntakeEndpoint: function(){ return '/intake'; } };
var MODE = %s, CALLS = 0;
function fetch(){
  CALLS++;
  if (MODE === 'http') return Promise.resolve({ ok: false, status: 503 });
  if (MODE === 'field') return Promise.resolve({ ok: true, json: function(){ return Promise.resolve({ error: 'overloaded' }); } });
  if (MODE === 'throw') return Promise.reject(new Error('socket hang up'));
  return Promise.resolve({ ok: true, json: function(){ return Promise.resolve({ tally: { Ber: 3 } }); } });
}
%s
(async function(){
  var why = {}, t = await _tallyRead('b64', ['Ber'], 'runes', 'tally', why);
  var bare = await _tallyRead('b64', ['Ber'], 'runes', 'tally');
  process.stdout.write(JSON.stringify({ t: t, why: why.text === undefined ? null : why.text, bare: bare, calls: CALLS }));
})().catch(function(e){ process.stderr.write(String(e && e.stack || e)); process.exit(3); });
"""


def _bible():
    with open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _cut_fn(s, sig):
    if s.count(sig) != 1:
        raise AssertionError("PREMISE: %r occurs %d times - this law cannot see it" % (sig[:50], s.count(sig)))
    i = s.index(sig)
    depth = 0
    for j in range(s.index("{", i + len(sig) - 1), len(s)):
        depth += {"{": 1, "}": -1}.get(s[j], 0)
        if depth == 0:
            return s[i:j + 1] + ";\n"
    raise AssertionError("%r never closed - harness fault, not a pass" % sig[:50])


def _read(mode):
    if NODE is None:
        raise AssertionError("node is not on this machine - this gate does not skip")
    s = _bible()
    if s.count(START) != 1 or s.count(END) != 1:
        raise AssertionError("PREMISE: _tallyRead is not where this law cuts it (%d, %d)" % (s.count(START), s.count(END)))
    i = s.index(START)
    fn = (_cut_fn(s, "window._intakeRefused = function(status, data){")
          + _cut_fn(s, "window._intakeAnswer = async function(resp){")
          + _cut_fn(s, "window._intakeIsCap = function(status, data){") + s[i:s.index(END, i) + len(END)])
    r = subprocess.run([NODE, "-"], input=PROGRAM % (json.dumps(mode), fn), capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("the cut _tallyRead did not run in node: %s" % r.stderr[-800:])
    return json.loads(r.stdout)


class ATallyReadNamesWhyItFailed(unittest.TestCase):

    def test_an_http_error_is_named(self):
        o = _read("http")
        self.assertIsNone(o["t"], "PREMISE: a failed read still returns null to the readers")
        self.assertEqual(o["why"], "the reader answered HTTP 503")

    def test_an_error_field_is_named(self):
        self.assertEqual(_read("field")["why"], "the reader refused (overloaded)")

    def test_a_request_that_threw_is_named(self):
        self.assertEqual(_read("throw")["why"], "the request failed: socket hang up")

    def test_a_good_read_says_nothing_and_a_caller_without_why_still_reads(self):
        o = _read("good")
        self.assertEqual(o["t"], {"Ber": 3})
        self.assertIsNone(o["why"], "a read that worked carried a failure cause: %r" % o)
        self.assertEqual(o["bare"], {"Ber": 3}, "a caller that passes no `why` lost its read")
        self.assertIsNone(_read("http")["bare"])


class TheCauseReachesTheJournal(unittest.TestCase):

    def test_the_reason_names_the_cause_when_it_came_and_stays_plain_when_it_did_not(self):
        self.assertEqual(CA._intake_why({"errors": 1, "errWhy": "the intake answered HTTP 503"}),
                         "read failed — 1 image error — the intake answered HTTP 503")
        self.assertEqual(CA._intake_why({"errors": 2}), "read failed — 2 image errors")

    def test_the_three_readers_and_both_posts_carry_it(self):
        s = _bible()
        code = "\n".join(re.sub(r"//.*$", "", l) for l in s.split("\n"))
        self.assertEqual(code.count("if(t===null){ errors++; errWhy = errWhy || _why.text || ''; continue; }"), 3,
                         "a tally reader counts an image error without keeping its cause")
        self.assertEqual(len(re.findall(r"_tallyRead\([^)]*, _why\)", code)), 4,
                         "a tally reader does not hand _tallyRead its `why`")
        self.assertEqual(code.count("errWhy: (_ir && _ir.errWhy) || undefined"), 2, "the live tally post drops the cause")
        with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            ca = fh.read()
        self.assertEqual(ca.count("errWhy:(res&&res.errWhy)||undefined,frameId:%s,guardHeld:!applied})"), 1,
                         "the kai-funnel post drops the cause")
        self.assertEqual(ca.count('**({"errWhy": str(body.get("errWhy"))[:160]} if body.get("errWhy") else {}),'), 1,
                         "the intake record drops the cause at the door")


RED_PROOF = [
    {"why": "#158 - an HTTP error from the intake is an image error with no cause again",
     "file": "bible.html",
     "find": "      if(ans.refused) return _fail(ans.refused);",
     "replace": "      if(ans.refused) return null;",
     "matches": 1, "needs": "node"},
    {"why": "#158 - a request that threw is an image error with no cause again",
     "file": "bible.html",
     "find": "    }catch(e){ return _fail('the request failed: ' + ((e && e.message) || e)); }\n",
     "replace": "    }catch(e){ return null; }\n",
     "matches": 1, "needs": "node"},
    {"why": "#158 - the cause never reaches the caller (why is not filled)",
     "file": "bible.html",
     "find": "  function _fail(t){ try { if (why) why.text = String(t).slice(0, 160); } catch (_e) {} return null; }\n",
     "replace": "  function _fail(t){ return null; }\n",
     "matches": 1, "needs": "node"},
    {"why": "#158 - the journal's reason drops the cause",
     "file": "tv/control_app.py",
     "find": "                                                       (\" \\u2014 \" + _cause) if _cause else \"\")\n",
     "replace": "                                                       \"\")\n",
     "matches": 1},
    {"why": "#158 - the kai-funnel post drops the cause",
     "file": "tv/control_app.py",
     "find": "errWhy:(res&&res.errWhy)||undefined,frameId:%s,guardHeld:!applied})",
     "replace": "frameId:%s,guardHeld:!applied})",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
