# -*- coding: utf-8 -*-
"""#158.8 (REG-2815) - A READER THAT REFUSED (ITS CAP, AN ERROR BODY) IS NEVER COUNTED AS A READ.

The task: "a subscription cap hit returns HTTP 200 + an error body, so callers can't tell it from a read." MEASURED at
v3832: control_app's /api/intake already answers a cap with 429 (REG-2383/2388) - that half is closed. The callers were
not: the Chronicle screenshot reader and the grail screenshot reader parsed the cap's body and read its empty lists as a
page or a shot read with nothing on it; the Ask box showed the error as the bible's answer; the set tracker, the craft
reader and the item checker's upload read a 200 + {error} (the website path, v407) the same way; and the item checker's
judge answered a cap "server 429" beside "no magic/rare item readable", which the engine's judge loop posted to
/kai_verdict as a "kai-judge" receipt - "judge a tooltip - UNREADABLE" - that _judge_already_near then read as "this hover
was judged", so the cap stood in for a read and the hover was never judged.

One rule now, window._intakeRefused(status, body), beside the one intake door: every door asks it. aicJudge answers a
refusal as {ok:false, refused:true, why}, and /kai_verdict journals it under its own mode (_kai_refused_row), which no
judge reader takes for a judge.

Driven: the rule and aicJudge cut out of bible.html and run in node; _kai_refused_row and _judge_already_near called on
control_app itself; each door's use of the rule read at its one-line site. RED_PROOF below.

REG-2976..2979 (the v3834 second eye): every door now asks the rule through window._intakeAnswer(resp), which reads the body
before judging it, so the sites below are the doors' new lines; tv/test_a_refusal_is_never_a_read_at_any_door.py drives every
door in every refusal shape.
"""
import io
import json
import os
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
import fixture_tmp as _fx  # noqa: E402
_fx.contain()

NODE = shutil.which("node")
BIBLE = io.open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8").read()
APP = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()

CAP = {"error": "subscription-cap", "message": "20/20 this hour - intake paused", "window": "hour", "retry_s": 120}


def _cut(src, sig, tail=""):
    if src.count(sig) != 1:
        raise AssertionError("%r occurs %d times - this law cannot see its subject" % (sig[:60], src.count(sig)))
    i = src.index(sig)
    b = src.index("{", i + len(sig) - 1)
    depth = 0
    for j in range(b, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1] + tail
    raise AssertionError("%r never closed - harness fault, not a pass" % sig[:60])


HARNESS = r"""
import { readFileSync } from 'node:fs';
const CFG = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const window = {};
let NEXT = null;
const env = {
  window: window,
  downscale: async () => 'AAAA',
  _aicIntakeEndpoint: () => '/api/intake',
  _aicItem: {}, _aicSave: () => {},
  _aicApplyIntake: () => ({ ok: false, counts: { items: 0 } }),
  fetch: async () => ({ ok: NEXT.status >= 200 && NEXT.status <= 299, status: NEXT.status,
                        json: async () => NEXT.body }),
};
const F = new Function('env', 'with (env) {\n' + CFG.code + '\nreturn window; }')(env);
const out = { rule: CFG.rule.map((c) => F._intakeRefused(c[0], c[1])), judge: [] };
for (const a of CFG.answers) { NEXT = a; out.judge.push(await F.aicJudge({})); }
process.stdout.write(JSON.stringify(out));
"""

RULE = [[429, CAP], [200, {"error": "upstream", "message": "the model is overloaded"}], [200, {"items": [], "finds": []}],
        [502, {}], [0, None]]
ANSWERS = [{"status": 429, "body": CAP}, {"status": 200, "body": {"error": "upstream", "message": "overloaded"}},
           {"status": 200, "body": {"items": [], "finds": []}}]


def _drive():
    if NODE is None:
        raise AssertionError("node is not on this machine - this law does not skip")
    code = (_cut(BIBLE, "window._intakeRefused = function(status, data){", ";") + "\n"
            + _cut(BIBLE, "window._intakeAnswer = async function(resp){", ";") + "\n"
            + _cut(BIBLE, "window._intakeIsCap = function(status, data){", ";") + "\n"
            + _cut(BIBLE, "window._intakeThrew = function(e){", ";") + "\n"
            + _cut(BIBLE, "  window.aicJudge = async function(file){", ";"))
    d = tempfile.mkdtemp(prefix="refused_read_")
    try:
        h, c = os.path.join(d, "h.mjs"), os.path.join(d, "cfg.json")
        io.open(h, "w", encoding="utf-8").write(HARNESS)
        io.open(c, "w", encoding="utf-8").write(json.dumps({"code": code, "rule": RULE, "answers": ANSWERS}))
        r = subprocess.run([NODE, h, c], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    finally:
        shutil.rmtree(d, True)
    if r.returncode != 0:
        raise AssertionError("node failed: %s" % r.stderr[-900:])
    return json.loads(r.stdout)


class TheRuleSaysARefusal(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = _drive()

    def test_a_cap_an_error_body_and_a_bad_status_are_refusals(self):
        cap, err, read, bad, none = self.o["rule"]
        self.assertIn("at its cap", cap or "", cap)
        self.assertIn("HTTP 429", cap or "")
        self.assertIn("overloaded", err or "", "a 200 with an error body read as a read")
        self.assertIsNone(read, "a clean read was called a refusal")
        self.assertEqual(bad, "the reader answered HTTP 502")
        self.assertIsNone(none)

    def test_the_judge_says_refused_and_a_read_that_found_nothing_does_not(self):
        cap, err, read = self.o["judge"]
        self.assertEqual((cap["ok"], cap.get("refused")), (False, True), cap)
        self.assertIn("at its cap", cap["why"])
        self.assertEqual((err["ok"], err.get("refused")), (False, True), "a 200 + {error} judged as unreadable: %r" % err)
        self.assertFalse(read.get("refused"), read)
        self.assertEqual(read["why"], "no magic/rare item readable in this frame")


class AJournaledRefusalIsNoJudge(unittest.TestCase):

    def test_a_refused_judge_never_counts_as_a_judged_hover(self):
        import control_app as ca
        row = ca._kai_refused_row({"refused": True, "why": "the reader is at its cap", "fts": 1793189802000,
                                   "sid": "s_1", "frameId": "1_1"}, 1793189900000)
        self.assertEqual(row["mode"], "kai-judge-refused")
        self.assertNotIn("judge", row["kai"], "a refusal carries a judge slot the theatre and the register read")
        self.assertIn("refused", row["note"])
        self.assertFalse(ca._judge_already_near([row], 1793189802000), "a refusal stood in for a judge of that hover")
        judged = dict(row, mode="kai-judge")
        self.assertTrue(ca._judge_already_near([judged], 1793189802000), "PREMISE: a real judge receipt counts")

    def test_the_handler_journals_a_refusal_before_any_judge_row(self):
        i = APP.index('        if path == "/kai_verdict":\n')
        refused = APP.find("                if body.get(\"refused\") is True:   # REG-2815", i)
        judge = APP.find("                _fts = int(body.get(\"fts\") or 0) or int(time.time() * 1000)", i)
        self.assertTrue(0 < refused < judge, "/kai_verdict writes a judge receipt for a refusal")


class EveryDoorAsksTheRule(unittest.TestCase):

    SITES = [
        "      if (ans.refused) { notRead++; notReadWhy = notReadWhy || ans.refused; continue; }   /* REG-2815 - a refusal is not a page read clean */\n",
        "    .then(function(x){ var d=x.data||{}, el=document.getElementById('ask-pending'); var rf=x.refused;   /* REG-2815 */\n",
        "    if (ans.refused) { if (why) why.text = ans.refused; return null; }   /* REG-2815 - a refusal is no tally, never an empty one */\n",
        "      var _rfU=_ansU.refused;   /* REG-2815 - a refusal is said, never \"no item read\" */\n",
        "        if (_rfC) { refused.push({ n:i+1, why:_rfC }); continue; }   /* REG-2977 - nor a page at all */\n",
        "        if (_rfG) { errs++; refusedWhy = refusedWhy || _rfG; continue; }\n",
    ]

    def test_each_door_asks(self):
        for site in self.SITES:
            self.assertEqual(BIBLE.count(site), 1, "a door no longer asks the refusal rule: %r" % site[:90])


RED_PROOF = [
    {"why": "REG-2815 - an error body (the website's 200 + {error}) reads as a read again",
     "file": "bible.html",
     "find": "  if (data && typeof data === 'object' && data.error)\n    return (data.error === 'subscription-cap'",
     "replace": "  if (false)\n    return (data.error === 'subscription-cap'",
     "matches": 1, "needs": "node"},
    {"why": "REG-2815 - a bad status with no body reads as a read",
     "file": "bible.html",
     "find": "  if (st && (st < 200 || st > 299)) return 'the reader answered HTTP ' + st;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2815 - the judge reads a 200 + {error} as 'no item readable' again",
     "file": "bible.html",
     "find": "      if (ans.refused) return { ok:false, refused:true, why: ans.refused };   /* REG-2815 - a cap is a refusal, never UNREADABLE */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2815 - the judge answers a cap without saying it refused",
     "file": "bible.html",
     "find": "      if (ans.refused) return { ok:false, refused:true, why: ans.refused };   /* REG-2815 - a cap is a refusal, never UNREADABLE */\n",
     "replace": "      if (ans.refused) return { ok:false, why: ans.refused };\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2815 - a refusal is journaled as a judge receipt, which blocks the real judge of that hover",
     "file": "tv/control_app.py",
     "find": "            \"mode\": \"kai-judge-refused\", \"names\": [], \"area\": \"\",\n",
     "replace": "            \"mode\": \"kai-judge\", \"names\": [], \"area\": \"\",\n",
     "matches": 1},
    {"why": "REG-2815 - /kai_verdict writes a refusal as a judge row again",
     "file": "tv/control_app.py",
     "find": "                if body.get(\"refused\") is True:   # REG-2815 - the reader refused: journal a refusal, never a judge receipt\n",
     "replace": "                if False:   # REG-2815\n",
     "matches": 1},
    {"why": "REG-2815 - the Chronicle screenshot reader counts a refused page as read",
     "file": "bible.html",
     "find": "        if (_rfC) { refused.push({ n:i+1, why:_rfC }); continue; }   /* REG-2977 - nor a page at all */\n",
     "replace": "        if (_rfC) { pages.push({ n:i+1, note:_rfC, witness:'none', printed:{}, read:{} }); continue; }\n",
     "matches": 1},
    {"why": "REG-2815 - the grail screenshot reader counts a refused shot as read",
     "file": "bible.html",
     "find": "        if (_rfG) { errs++; refusedWhy = refusedWhy || _rfG; continue; }\n",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
