# -*- coding: utf-8 -*-
"""#158 (REG-2914) - AN IMAGE ERROR REACHES ITS RECEIPT WITH ITS CAUSE, AND THE READER'S OWN REPORT SAYS IT TOO.

REG-2730 taught _tallyRead to name a failed pass's cause, kept the first one as each tally reader's errWhy, and had the
board post it with every read. It reached one of the two routes that receive that post. The board posts each tally read to
the AGENT's /intake_result first (the bridge port) and to the console's own route only when the agent is not listening; the
console's copy keeps the reason (v1945: err, guardHeld; REG-2730: errWhy), the agent's built its record from seven fields
and dropped the rest. So a receipt from the agent read "read failed (1 image error)" and never said which - and the reader's
own report on the board printed "1 image error" with the cause sitting unused in errWhy.

Now the agent's record keeps the reason fields as sent (tv_diablo._intake_result_fields), the receipt says the sentence the
one rule makes from them (control_app._intake_why: "read failed - 1 image error - the intake answered HTTP 503"), and the gems,
runes and materials reports print the same cause (_imgErrSay, escaped). A record or a read with no cause reads as before.

Driven: the agent's record builder, its row through the console's real receipt stream (a fixture journal under
TV_SESSIONS), and _imgErrSay cut from bible.html and run in node. RED_PROOF below.
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
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
CAUSE = "the intake answered HTTP 503"
POST = {"ts": 1787000000000, "tab": "runes", "kind": "tally", "ok": False, "counts": {}, "total": 0, "errors": 1,
        "errWhy": CAUSE, "frameId": "f_1787000000000"}


def _read(p):
    with io.open(p, encoding="utf-8") as fh:
        return fh.read()


class TheAgentKeepsTheReason(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import tv_diablo as tv
        cls.tv = tv

    def test_the_reason_fields_ride_as_sent(self):
        got = self.tv._intake_result_fields(dict(POST, err="the reader threw", guardHeld=True))
        self.assertEqual((got["errWhy"], got["err"], got.get("guardHeld")), (CAUSE, "the reader threw", True),
                         "the agent's intake record dropped what the board sent about why: %r" % got)

    def test_a_read_with_no_reason_carries_none(self):
        got = self.tv._intake_result_fields({"tab": "gems", "ok": True, "total": 4, "counts": {"Ruby": 4}})
        for k in ("errWhy", "err", "guardHeld"):
            self.assertNotIn(k, got, "a read with no reason was given an empty one (%s)" % k)
        self.assertEqual((got["total"], got["errors"], got["ok"]), (4, 0, True))

    def test_the_route_builds_its_record_from_it(self):
        src = _read(os.path.join(HERE, "tv_diablo.py"))
        body = src[src.index('if self.path.startswith("/intake_result"):'):]
        body = body[:body.index("_journal(rec)")]
        self.assertEqual(body.count('"intake": _intake_result_fields(body),'), 1,
                         "the agent's /intake_result builds its record by hand again")


class TheReceiptSaysWhich(unittest.TestCase):

    def _label(self, intake):
        import control_app as ca
        d = tempfile.mkdtemp(prefix="rcpt_cause_")
        self.addCleanup(shutil.rmtree, d, True)
        jp = os.path.join(d, "sessions.jsonl")
        with io.open(jp, "w", encoding="utf-8") as f:
            f.write(json.dumps({"lane": "intake", "ts": 1787000000000, "sessionId": "s1", "frameId": "f1",
                                "intake": intake}) + "\n")
        old = os.environ.get("TV_SESSIONS")
        os.environ["TV_SESSIONS"] = jp
        cache = ca.__dict__.pop("_RECEIPTS_CACHE", None)
        try:
            rows = [r for r in ca._receipts_stream() if r.get("kind") == "route"]
        finally:
            ca.__dict__["_RECEIPTS_CACHE"] = cache
            if old is None:
                os.environ.pop("TV_SESSIONS", None)
            else:
                os.environ["TV_SESSIONS"] = old
        self.assertTrue(rows, "PREMISE: the intake row produced no route receipt")
        return (rows[0].get("diablo") or {}).get("label") or ""

    def test_the_agents_record_reads_with_its_cause(self):
        import tv_diablo as tv
        label = self._label(tv._intake_result_fields(POST))
        self.assertIn("read failed — 1 image error — " + CAUSE, label,
                      "the receipt of an agent-written read does not say which image error: %r" % label)

    def test_an_old_record_with_no_cause_reads_as_before(self):
        label = self._label({"tab": "runes", "kind": "tally", "ok": False, "errors": 2, "total": 0})
        self.assertIn("read failed (2 image errors)", label)


class TheReadersOwnReportSaysWhich(unittest.TestCase):

    def _say(self, cases):
        if NODE is None:
            raise AssertionError("node is not on this machine - this law does not skip")
        s = _read(BIBLE)
        start, end = "function _imgErrSay(n, why){\n", "\nwindow._imgErrSay = _imgErrSay;\n"
        self.assertEqual((s.count(start), s.count(end)), (1, 1), "PREMISE: _imgErrSay is not where this law cuts it")
        fn = s[s.index(start):s.index(end) + len(end)]
        prog = "var window = {};\n" + fn + "\nprocess.stdout.write(JSON.stringify(%s.map(function(c){ return _imgErrSay(c[0], c[1]); })));" \
            % json.dumps(cases)
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("_imgErrSay did not run in node: %s" % r.stderr[-600:])
        return json.loads(r.stdout)

    def test_the_cause_is_said_and_escaped(self):
        got = self._say([[1, CAUSE], [2, None], [1, "the intake said: <b>overloaded</b>"]])
        self.assertEqual(got[0], "1 image error — " + CAUSE)
        self.assertEqual(got[1], "2 image errors", "a read with no cause grew one: %r" % got[1])
        self.assertEqual(got[2], "1 image error — the intake said: &lt;b&gt;overloaded&lt;/b&gt;")

    def test_the_three_tally_readers_say_it(self):
        s = _read(BIBLE)
        self.assertEqual(s.count("'+_imgErrSay(errors, errWhy)+'"), 6,
                         "a gems, runes or materials report prints its image errors without their cause")


RED_PROOF = [
    {"why": "REG-2914 - the agent's intake record drops WHICH image error again",
     "file": "tv/tv_diablo.py",
     "find": "    if body.get(\"errWhy\"):\n        out[\"errWhy\"] = str(body.get(\"errWhy\"))[:160]\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2914 - the receipt ignores the reason fields an agent-written record carries",
     "file": "tv/control_app.py",
     "find": "                if not _why and (ik.get(\"err\") or ik.get(\"errWhy\") or ik.get(\"guardHeld\")):\n",
     "replace": "                if False:\n",
     "matches": 1},
    {"why": "REG-2914 - the agent's route builds its record by hand again, without the reason",
     "file": "tv/tv_diablo.py",
     "find": "                        \"intake\": _intake_result_fields(body),\n",
     "replace": "                        \"intake\": {\"tab\": str(body.get(\"tab\") or \"\")[:24], \"errors\": int(body.get(\"errors\") or 0)},\n",
     "matches": 1},
    {"why": "REG-2914 - the reader's own report prints the count without the cause",
     "file": "bible.html",
     "find": "  var w = (typeof why === 'string' && why) ? ' \\u2014 ' + why.replace(",
     "replace": "  var w = (false) ? ' \\u2014 ' + why.replace(",
     "matches": 1, "needs": "node"},
    {"why": "REG-2914 - the cause reaches the page unescaped",
     "file": "bible.html",
     "find": "' \\u2014 ' + why.replace(/[&<>\"']/g, function(c){",
     "replace": "' \\u2014 ' + why + ''.replace(/[&<>\"']/g, function(c){",
     "matches": 1, "needs": "node"},
    {"why": "REG-2914 - the gems report goes back to the count alone",
     "file": "bible.html",
     "find": "      report.innerHTML='No gems read'+(errors?' ('+_imgErrSay(errors, errWhy)+')':'')",
     "replace": "      report.innerHTML='No gems read'+(errors?' ('+errors+' image error'+(errors===1?'':'s')+')':'')",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
