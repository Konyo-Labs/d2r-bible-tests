# -*- coding: utf-8 -*-
"""REG-2870 (#83, his ask 1, GrokBot 6476487696) - EVERY D2JSP POST ANSWER SAYS WHAT THE CONSOLE SAW.

GrokBot's real post from the Linux seat, with his OK, came back "MAYBE SENT: The console answered with no reason, which
this page does not know, so the post may be up", and no topic existed on board 268. His ask: "surface what the backend
got back (HTTP status or d2jsp error) instead of MAYBE SENT with no reason."

MEASURED before (this tree, fakes only, never the live site):
  * a post whose Chrome raised while closing, after the run had clicked submit, answered "unread": "The d2jsp page did
    not answer before the post was submitted, so nothing was posted" - about a click that went out;
  * every refusal was a bare word: chrome-unread never said which step of the cookie read failed (no cookie file, the
    keychain, the decryption), not-posted and maybe-sent never said what the run saw or on which page it stopped;
  * an error inside the send escaped the route as an exception, so the connection dropped;
  * the page's words for an answer with no contract reason named no HTTP status and none of the answer's own words:
    "with no reason, which this page does not know" - the exact sentence GrokBot read.

Now the Chrome run's result outlives its cleanup (the error rides on it as `teardown`); each cookie reader says which
step failed into `why`; every answer that is not a receipt carries `why` (and the last forum page); an error inside the
send is a maybe-sent with why; the console route answers not-posted with why when the module itself fails; and the page
shows "What the console saw: ..." on the receipt and the status line, and for an unknown answer its HTTP status and its
own words. Driven through the real flow over a fake board (the send law's Board) and the room's own code in node. Never
a browser, never d2jsp, never his Chrome profile. RED_PROOF below.
"""
from __future__ import annotations

import contextlib
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
from console_safe import enable
enable()

import d2jsp_chrome as desk  # noqa: E402
import test_a_d2jsp_post_is_sent_once_and_never_called_unsent as SL  # noqa: E402  the fake board and its seat

ROOT = os.path.dirname(HERE)
BIBLE = os.path.join(ROOT, "bible.html")
NODE = shutil.which("node")


class _ClosesBadly(object):
    """A scratch Chrome whose cleanup raises after the run - the case a `with` turned into 'unread'."""

    def __init__(self, page):
        self.page = page

    def __enter__(self):
        return self.page

    def __exit__(self, *exc):
        raise OSError("the scratch Chrome would not close")


class ARefusalAlwaysSaysWhy(unittest.TestCase):

    def setUp(self):
        desk._SENT.clear()
        self.addCleanup(desk._SENT.clear)

    def patch(self, obj, name, value):
        old = getattr(obj, name)
        setattr(obj, name, value)
        self.addCleanup(setattr, obj, name, old)

    def seat(self, then, closes_badly=False, **kw):
        clock = SL.Clock()
        board = SL.Board(clock, then=then, **kw)
        seat = SL.Seat(board, clock)
        if closes_badly:
            seat.chrome = lambda cookie, prefix: _ClosesBadly(desk._Page(SL.DevTools(board)))
        return seat, board

    def send(self, seat):
        desk._SENT.clear()      # each world is its own first send, never a re-send of the last one
        code, out = seat.send()
        self.assertIn(out.get("reason"), desk.SEND_REASONS, out)
        self.assertNotIn("SECRETCOOKIE", json.dumps(out))
        return out

    def test_a_click_survives_a_chrome_that_will_not_close(self):
        seat, board = self.seat("stay", closes_badly=True)
        out = self.send(seat)
        self.assertEqual(board.clicks, 1, "PREMISE: the fake board was not clicked")
        self.assertEqual(out["reason"], "maybe-sent", "a click was read as nothing sent because Chrome would not close: %r" % out)
        self.assertIn("then Chrome's cleanup raised OSError: the scratch Chrome would not close", out.get("why", ""), out)
        seat2, board2 = self.seat("topic", closes_badly=True, new_id=999)
        out2 = self.send(seat2)
        self.assertEqual(out2["reason"], "submitted", "a receipt was lost to Chrome's cleanup: %r" % out2)

    def test_every_answer_that_is_not_a_receipt_says_what_the_run_saw(self):
        seat, _ = self.seat("stay")
        out = self.send(seat)
        self.assertEqual(out["reason"], "maybe-sent", out)
        self.assertIn("no topic page came back within 35 s", out.get("why", ""), out)
        self.assertIn("last page https://forums.d2jsp.org/", out.get("why", ""), out)
        seat, _ = self.seat("stay", trade_link=False)
        out = self.send(seat)
        self.assertEqual(out["reason"], "not-posted", out)
        self.assertIn("the New Trade form did not open within 25 s", out.get("why", ""), out)
        seat, _ = self.seat("form")
        out = self.send(seat)
        self.assertEqual(out["reason"], "not-posted", out)
        self.assertIn("d2jsp sent the form back after the click", out.get("why", ""), out)

    def test_a_failed_cookie_read_names_its_step(self):
        box = []
        self.assertEqual(desk._linux_cookie_header(paths=[], passwords=["x"], why=box), (None, "chrome-unread"))
        self.assertEqual(box, ["no Chrome or Chromium cookie file under ~/.config/google-chrome or ~/.config/chromium"])
        tmp = tempfile.mkdtemp(prefix="d2jsp-why-")
        self.addCleanup(shutil.rmtree, tmp, True)
        box = []
        desk._linux_cookie_header(paths=[os.path.join(tmp, "missing", "Cookies")], passwords=["x"], why=box)
        self.assertEqual(len(box), 1, box)
        self.assertTrue(box[0].startswith("1 cookie file(s) found and none would open ("), box)

        def reader(now_utc=None, why=None):
            why.append("the keychain refused the Chrome Safe Storage password (exit 51)")
            return None, "chrome-unread"
        self.patch(desk, "live_cookie_header", reader)
        self.patch(desk, "_LIVE_READER", reader)
        code, out = desk.d2jsp_send({"subject": SL.SUBJECT, "body": SL.BODY, "forum": 268}, SL.ORIGIN, SL.HOST,
                                    SL.PORT, chrome_post=lambda *a: self.fail("posted with no cookie"),
                                    open_login=lambda: False)
        self.assertEqual((out["reason"], out.get("why")),
                         ("chrome-unread", "the keychain refused the Chrome Safe Storage password (exit 51)"), out)
        lamp = desk.d2jsp_login_status()
        self.assertEqual(lamp["state"], "unknown", lamp)
        self.assertIn("the keychain refused the Chrome Safe Storage password (exit 51)", lamp["why"], lamp)

    def test_an_error_in_the_send_is_an_answer_never_a_dropped_connection(self):
        seat, _ = self.seat("stay")
        kept = desk._remember_send
        desk._remember_send = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("record broke"))
        try:
            out = self.send(seat)
        finally:
            desk._remember_send = kept
        self.assertEqual(out["reason"], "maybe-sent", out)
        self.assertIn("the console raised RuntimeError: record broke during the send", out.get("why", ""), out)
        desk._SENT.clear()

        def boom(subject, text, cookie):
            raise RuntimeError("devtools gone")
        code, out = desk.d2jsp_send({"subject": SL.SUBJECT, "body": SL.BODY, "forum": 268}, SL.ORIGIN, SL.HOST, SL.PORT,
                                    cookie_get=lambda: (SL.COOKIE, "ok"), chrome_post=boom, open_login=lambda: False)
        self.assertEqual(out["reason"], "unread", out)
        self.assertIn("RuntimeError: devtools gone", out.get("why", ""), out)

    def test_the_console_route_answers_with_why_when_the_module_fails(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        i = src.index('        if path == "/api/d2jsp_send":\n')
        block = src[i:src.index('        if path == "/api/roster-book":', i)]
        code = "\n".join(l.split("#", 1)[0] for l in block.split("\n"))
        self.assertIn('_code, _out = 200, {"ok": False, "reason": "not-posted",', code,
                      "a failing d2jsp module still drops the connection instead of answering with why")
        self.assertIn("except Exception as _e:", code)


PAGE = r"""
var LISTEN = { click: [], input: [], keydown: [] };
function Node(id){ this.id = id; this.attrs = {}; this.hidden = true; this._html = ''; this.textContent = ''; this.title = ''; }
Node.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
Node.prototype.getAttribute = function(k){ return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; };
Node.prototype.removeAttribute = function(k){ delete this.attrs[k]; };
Node.prototype.querySelector = function(){ return { focus: function(){} }; };
Node.prototype.querySelectorAll = function(){ return []; };
Node.prototype.appendChild = function(){};
Node.prototype.insertBefore = function(){};
Object.defineProperty(Node.prototype, 'innerHTML', { get: function(){ return this._html; }, set: function(v){ this._html = String(v); } });
var list = new Node('d2jsp-list'), statusEl = new Node('d2jsp-status'), lamp = new Node('d2jsp-lamp');
var host = new Node('d2jsp-draft-host'), board = new Node('d2jsp-board');
var VIEW = { textContent: '' }, SUBJECT = { textContent: '' };
var document = {
  documentElement: { classList: { contains: function(){ return false; } } },
  getElementById: function(id){ return ({ 'd2jsp-list': list, 'd2jsp-status': statusEl, 'd2jsp-lamp': lamp, 'd2jsp-draft-host': host, 'd2jsp-board': board })[id] || null; },
  querySelector: function(sel){
    if (sel === '#d2jsp-draft-host [data-d2jsp-draft-view]') return VIEW;
    if (sel === '#d2jsp-draft-host [data-d2jsp-draft-subject]') return SUBJECT;
    return null;
  },
  querySelectorAll: function(){ return []; },
  addEventListener: function(type, fn){ if (LISTEN[type]) LISTEN[type].push(fn); },
  createElement: function(){ return new Node(''); },
  body: { appendChild: function(){} }
};
var RAW = {};
var localStorage = { getItem: function(k){ return Object.prototype.hasOwnProperty.call(RAW, k) ? RAW[k] : null; },
                     setItem: function(k, v){ RAW[k] = String(v); }, removeItem: function(k){ delete RAW[k]; } };
var location = { hostname: '127.0.0.1' };
var MULE = JSON.stringify({ 'Grief': 'm1' });
var window = { addEventListener: function(){}, LSR: { getItem: function(k){ return k === 'd2r_muleAssign' ? MULE : null; } } };
var ANSWER = null, CODE = 200;
function fetch(url, opts){
  if (String(url) === '/api/d2jsp_send') return Promise.resolve({ status: CODE, json: function(){ return Promise.resolve(ANSWER); } });
  return Promise.resolve({ status: 200, json: function(){ return Promise.resolve({ state: 'unknown', fg: null, reason: 'no prices', n: 0 }); } });
}
function flush(){ return new Promise(function(r){ setTimeout(r, 0); }); }
function button(attrs, selfSel){
  var b = { getAttribute: function(k){ return Object.prototype.hasOwnProperty.call(attrs, k) ? attrs[k] : null; } };
  b.closest = function(sel){ return (sel === '#tab-d2jsp' || selfSel.indexOf(sel) >= 0) ? b : null; };
  return b;
}
"""

SCENARIO = r"""
RAW['d2r_d2jsp_fg'] = JSON.stringify({ 'Grief': '55' });
var shown = d2jspDraft('Grief', '', '', 1, 55);
async function one(answer, code){
  ANSWER = answer; CODE = code || 200; host._html = ''; statusEl.textContent = '';
  VIEW.textContent = shown.body; SUBJECT.textContent = shown.subject;
  LISTEN.click.forEach(function(f){ f({ target: button({ 'data-d2jsp-post': 'Grief', 'data-d2jsp-send': '1' }, []), preventDefault: function(){} }); });
  for (var i = 0; i < 6; i++) await flush();
  return { receipt: host._html, status: statusEl.textContent };
}
(async function(){
  var out = {};
  var SAW = 'the click went out; no topic page came back within 35 s';
  out.maybe = sendWords({ ok: false, reason: 'maybe-sent', board: 268, at: 'x', why: SAW }, 268, false);
  out.unread = sendWords({ ok: false, reason: 'chrome-unread', why: 'no Chrome cookie file' }, 268, false);
  out.start = sendWords({ ok: false, reason: 'chrome-start', why: 'no Chrome binary' }, 268, false);
  out.ok = sendWords({ ok: true, reason: 'submitted', topic: 'https://forums.d2jsp.org/topic.php?t=9&f=268', why: 'x' }, 268, false);
  out.msg = answerWords(200, { ok: false, msg: 'boom' }, 268, false);
  out.bare = answerWords(500, { ok: false }, 268, false);
  out.blank = sendWords({}, 268, false);
  out.paint = await one({ ok: false, reason: 'maybe-sent', board: 268, at: 'x', why: SAW });
  out.paintBare = await one({ ok: false }, 500);
  process.stdout.write(JSON.stringify(out));
})().catch(function(e){ process.stderr.write(String(e && e.stack || e)); process.exit(1); });
"""


def _between(src, start, end):
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i + len(start):j]


@unittest.skipUnless(NODE, "node is required to run the room's own code")
class ThePageSaysWhatTheConsoleSaw(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        pane = _between(src, 'id="tab-d2jsp"', 'id="tab-vault"')
        words = _between(src, "/* ⟦D2JSP SEND WORDS BEGIN⟧ */", "/* ⟦D2JSP SEND WORDS END⟧ */")   # the room's words, read directly
        r = subprocess.run([NODE, "-"], input=PAGE + pane.split("<script>", 1)[1].split("</script>", 1)[0] + "\n" + words + "\n" + SCENARIO,
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("node failed: " + (r.stderr or r.stdout)[-2500:])
        cls.o = json.loads(r.stdout.strip().splitlines()[-1])

    def test_a_reason_carries_its_why(self):
        o = self.o
        self.assertEqual(o["maybe"]["why"], "the click went out; no topic page came back within 35 s", o["maybe"])
        self.assertEqual(o["unread"]["why"], "no Chrome cookie file", o["unread"])
        self.assertNotIn("why", o["start"], "chrome-start's why is said twice")
        self.assertIn("no Chrome binary", o["start"]["text"])
        self.assertNotIn("why", o["ok"], "a receipt carries a why")

    def test_an_answer_with_no_contract_reason_shows_its_status_and_words(self):
        o = self.o
        for k in ("msg", "bare", "blank"):
            self.assertEqual(o[k]["kind"], "maybe", o[k])
            self.assertNotIn("with no reason", o[k]["text"], "the old words with nothing in them: %r" % o[k])
        self.assertIn('HTTP 200 with no post result: "boom"', o["msg"]["text"], o["msg"])
        self.assertIn("HTTP 500 with no post result and no words", o["bare"]["text"], o["bare"])
        self.assertEqual(o["bare"]["why"], 'HTTP 500 {"ok":false}', o["bare"])

    def test_the_receipt_and_the_status_say_it(self):
        p = self.o["paint"]
        self.assertIn('<p class="d2jsp-say" data-d2jsp-why>What the console saw: the click went out; no topic page came back within 35 s</p>',
                      p["receipt"], p)
        self.assertIn("What the console saw: the click went out", p["status"], p)
        b = self.o["paintBare"]
        self.assertIn('What the console saw: HTTP 500 {&quot;ok&quot;:false}', b["receipt"], b)


RED_PROOF = [
    {"why": "REG-2870 - Chrome's cleanup error replaces a run that clicked (a click read as nothing sent)",
     "file": "tv/d2jsp_chrome.py",
     "find": "        got = dict(got, teardown=_err(e)) if isinstance(got, dict) else got\n",
     "replace": "        raise\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2870 - a verdict drops what the run saw",
     "file": "tv/d2jsp_chrome.py",
     "find": "        if said:\n            out[\"why\"] = \"; \".join(said)\n        return 200, out\n    if res[\"clicked\"] is not False:",
     "replace": "        return 200, out\n    if res[\"clicked\"] is not False:",
     "matches": 1, "needs": "node"},
    {"why": "REG-2870 - a clicked post with no receipt says nothing of what came back",
     "file": "tv/d2jsp_chrome.py",
     "find": "(\"the click went out; no topic page came back within %d s and the board list read \"",
     "replace": "(\"(nothing) %d \"",
     "matches": 1, "needs": "node"},
    {"why": "REG-2870 - a form that never opened says nothing",
     "file": "tv/d2jsp_chrome.py",
     "find": "why=\"the %s form did not open within %d s\"",
     "replace": "why=\"%s%d\"",
     "matches": 1, "needs": "node"},
    {"why": "REG-2870 - a missing cookie file is a bare chrome-unread again",
     "file": "tv/d2jsp_chrome.py",
     "find": "        _note(why, \"no Chrome or Chromium cookie file under ~/.config/google-chrome or ~/.config/chromium\")\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2870 - the send's cookie refusal drops the reader's why",
     "file": "tv/d2jsp_chrome.py",
     "find": "        if said:\n            out[\"why\"] = \"; \".join(said)    # REG-2870 which step of the read failed\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2870 - the live reader is asked without a why box",
     "file": "tv/d2jsp_chrome.py",
     "find": "    if reader is _LIVE_READER:\n        return reader(now_utc, why=why)\n",
     "replace": "    if False:\n        return reader(now_utc, why=why)\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2870 - the lamp's unread says nothing of which step failed",
     "file": "tv/d2jsp_chrome.py",
     "find": "        \"why\": \"This machine could not read the Chrome login\" + (\": \" + \"; \".join(said) if said else \"\") + \".\",\n",
     "replace": "        \"why\": \"This machine could not read the Chrome login.\",\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2870 - an error inside the send escapes as an exception (the dropped connection)",
     "file": "tv/d2jsp_chrome.py",
     "find": "    except Exception as e:\n        # REG-2870 - an error inside the send",
     "replace": "    except ZeroDivisionError as e:\n        # REG-2870 - an error inside the send",
     "matches": 1, "needs": "node"},
    {"why": "REG-2870 - a Chrome run that raised says nothing of the error",
     "file": "tv/d2jsp_chrome.py",
     "find": "        return None, {\"ok\": False, \"reason\": \"unread\", \"why\": \"the Chrome run stopped before it opened the board (%s)\" % _err(e)}\n",
     "replace": "        return None, {\"ok\": False, \"reason\": \"unread\"}\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2870 - the console route drops the connection when the module fails",
     "file": "tv/control_app.py",
     "find": "                _code, _out = 200, {\"ok\": False, \"reason\": \"not-posted\",\n",
     "replace": "                raise\n                _code, _out = 200, {\"ok\": False,\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2870 - the page drops the console's why",
     "file": "bible.html",
     "find": "    if (why && w.kind !== 'confirmed' && String((j && j.reason) || '') !== 'chrome-start') w.why = why;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2870 - an answer with no contract reason has no status and no words again",
     "file": "bible.html",
     "find": "      return { kind: 'maybe', text: 'The console answered' + (code ? (' HTTP ' + code) : '') + ' with no post result'\n",
     "replace": "      if (false) return { kind: 'maybe', text: 'The console answered' + (code ? (' HTTP ' + code) : '') + ' with no post result'\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2870 - the receipt does not show what the console saw",
     "file": "bible.html",
     "find": "      + (why ? '<p class=\"d2jsp-say\" data-d2jsp-why>What the console saw: ' + esc(why) + '</p>' : '')   /* REG-2870 */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2870 - the status line drops the why",
     "file": "bible.html",
     "find": "  function whySay(w){ return w.text + (w.why ? (' What the console saw: ' + w.why) : ''); }",
     "replace": "  function whySay(w){ return w.text; }",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
