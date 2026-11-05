# -*- coding: utf-8 -*-
"""REG-1618 — EACH LAMP IS ITS OWN READER'S LINK, WITH ITS OWN LOGIC FOR A SUDDEN DISCONNECT.

His words, 2026-09-30, looking at the corner of his console: "so like maybe the top right corner under ONLINE if clicking
CLAUDE it should link me and open the browser that way its dual working also backend and visual" - "and same for grok" -
"with its own individual logic if it gets disconnected suddenly".

Driven, joint by joint, never by grepping prose:
  1. the corner - CLAUDE and GROK are BUTTONS, each wired to its own reader (window._lampClick('claude'|'grok', this)).
  2. the click - a linked lamp opens nothing; CLAUDE otherwise POSTs /api/claude_login; GROK switched off by him or not
     installed says where and changes nothing; otherwise POSTs /api/g5_login with keepSwitch - the lamp signs in, it
     never flips his switch (_g5_login_moves_switch).
  3. each lamp's memory - ON -> OFF by itself rings (data-alert) and says so ONCE, the other lamp untouched; UNKNOWN in
     between does not reset it; back ON says so and stops ringing; a sign-in being finished breathes (data-busy).
  4. GROK's own disconnect logic - his SWITCH is the only "switched off": a Grok whose sign-in just went (the effective
     mode drops to off with it) used to read "switched off", a state he chose, with nothing to click. An auth file the
     far end now refuses (401) is signed OUT - status says needsLogin, and start_login reopens the browser instead of
     answering "already authorized" from the file on disk.
  5. CLAUDE's own disconnect logic - while a sign-in he clicked is being finished the CLI is re-asked every 10 s, not
     every 5 min, and a changed answer repaints at once; the lamp says "waiting" meanwhile and never once it is on.
  6. REG-1631 - a refusal is a STATED code, never digits inside a number: the Grok CLI look at v3534 pointed at the
     substring needles, and measured, "timed out after 1401 ms" lit SIGN IN and "read 34020 bytes" said the balance was
     exhausted (and held the lane for half an hour); Windows' "insufficient system resources" read as no credit left.
Nothing here opens a window, spawns a CLI or touches his files: every spawn is a recorded fake. RED_PROOF below.
"""
import html.parser
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

_WORLD = tempfile.mkdtemp(prefix="lamp_links_")
os.environ["TV_HIST"] = _WORLD
os.environ["TV_SESSIONS"] = os.path.join(_WORLD, "sessions.jsonl")

import claude_signin as CS  # noqa: E402
import control_app as ca  # noqa: E402
import g5_grok_eyes as g5  # noqa: E402

UI = os.path.join(HERE, "control_ui.html")
NODE = shutil.which("node")
NOW = 1790780000000

RED_PROOF = [
    {"why": "REG-1618 - a Grok whose sign-in just went reads 'switched off' again: the lamp keys on the effective mode",
     "file": "control_app.py",
     "find": "    _his_off = (_sw == \"off\") if _sw is not None else (\n",
     "replace": "    _his_off = True if isinstance(g, dict) and g.get(\"mode\") == \"off\" else (_sw == \"off\") if _sw is not None else (\n",
     "matches": 1},
    {"why": "REG-1618 - a refused sign-in (401) reads as linked: the lamp never learns the credentials were rejected",
     "file": "control_app.py",
     "find": "    elif g.get(\"credentialsRejected\"):\n",
     "replace": "    elif False:\n", "matches": 1},
    {"why": "REG-1618 - the Grok lane still calls a 401 'authorized' because the auth file is on disk",
     "file": "g5_grok_eyes.py",
     "find": "        \"needsLogin\": bool(cli and (not authorized or rejected)),\n",
     "replace": "        \"needsLogin\": bool(cli and not authorized),\n", "matches": 1},
    {"why": "REG-1618 - start_login answers 'already authorized' from a file the far end refuses: no browser opens",
     "file": "g5_grok_eyes.py",
     "find": "    if _subscription_logged_in() and not credentials_rejected():\n",
     "replace": "    if _subscription_logged_in():\n", "matches": 1},
    {"why": "REG-1618 - a click on the GROK lamp switches the + GROK layer on: keepSwitch is ignored",
     "file": "control_app.py",
     "find": "    if body.get(\"keepSwitch\"):\n        return False\n",
     "replace": "    if False:\n        return False\n", "matches": 1},
    {"why": "REG-1618 - Claude's sign-in is re-asked every 5 min even while he is finishing it in the browser",
     "file": "control_app.py",
     # v3863 (REG-3168) - the cadence now leads with the fast re-check after a sign-in; the watch arm is its second line
     "find": "              else CLAUDE_AUTH_WATCH_EVERY_S if _watch and not _green\n",
     "replace": "              else CLAUDE_AUTH_EVERY_S if _watch and not _green\n", "matches": 1},
    {"why": "REG-1618 - a changed sign-in waits out the 30 s lamp cache instead of repainting",
     "file": "control_app.py",
     "find": "                    _READER_CACHE[\"at\"] = 0.0      # REG-1618",
     "replace": "                    pass                          # REG-1618", "matches": 1},
    {"why": "REG-1618 - a lamp that goes ON -> OFF by itself does not ring",
     "file": "control_ui.html",
     "find": "        el.setAttribute('data-alert', '1');\n        say(NAME[p[0]] + ' disconnected on this PC - '",
     "replace": "        el.setAttribute('data-alert', '0');\n        say(NAME[p[0]] + ' disconnected on this PC - '",
     "matches": 1},
    {"why": "REG-1618 - switching + GROK off himself rings and is announced as a disconnection",
     "file": "control_ui.html",
     "find": "      } else if (state === 'off' && (L && L.kind) === 'switched-off') {\n",
     "replace": "      } else if (false) {\n", "matches": 1},
    {"why": "REG-1618 - an UNKNOWN poll between ON and OFF wipes the lamp's memory, so the drop is never said",
     "file": "control_ui.html",
     "find": "      if (state !== 'unknown') M.seen[p[0]] = state;\n",
     "replace": "      M.seen[p[0]] = state;\n", "matches": 1},
    {"why": "REG-1618 - a click on a switched-off GROK lamp opens a sign-in (and the route would switch it on)",
     "file": "control_ui.html",
     "find": "    if (k === 'grok' && (kind === 'switched-off' || kind === 'not-installed')) {\n",
     "replace": "    if (false) {\n", "matches": 1},
    {"why": "REG-1618 - the CLAUDE lamp is a label again: nothing to click in the corner",
     "file": "control_ui.html",
     "find": "          <button type=\"button\" class=\"rl\" id=\"rl-claude\" data-lamp=\"unknown\" onclick=\"window._lampClick('claude', this)\"\n",
     "replace": "          <button type=\"button\" class=\"rl\" id=\"rl-claude\" data-lamp=\"unknown\"\n", "matches": 1},
    {"why": "REG-1618 - the lamp says 'waiting' after Claude is back on (signInOpen ignores the state)",
     "file": "control_app.py",
     "find": "        lamp[\"signInOpen\"] = bool(_csi.watching()) and lamp.get(\"state\") != \"on\"\n",
     "replace": "        lamp[\"signInOpen\"] = bool(_csi.watching())\n", "matches": 1},
    {"why": "REG-1636 - a sign-in check whose thread never started keeps `busy` for good: the CLAUDE lamp never asks again",
     "file": "control_app.py",
     "find": "        except Exception as e:\n            _CLAUDE_AUTH[\"busy\"] = False\n",
     "replace": "        except Exception as e:\n            pass\n", "matches": 1},
    {"why": "REG-1631 - a status code is a substring again: a timeout of 1401 ms reads as a revoked sign-in",
     "file": "g5_grok_eyes.py",
     "find": "    return _re.compile(r\"(?<![\\w.])%s(?![\\w.])(?!\\s*(?:ms|s|secs?|seconds?|bytes?|[kmg]i?b)\\b)\" % n)\n",
     "replace": "    return _re.compile(r\"%s\" % n)\n", "matches": 1},
    {"why": "REG-1631 - 'insufficient' alone again: Windows running short of resources reads as no Grok credit",
     "file": "g5_grok_eyes.py",
     "find": "(_re.compile(r\"insufficient[\\s_-]*(?:credits?|balance|funds?|quota)\"),",
     "replace": "(_re.compile(r\"insufficient\"),", "matches": 1},
]


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _grok(**kw):
    base = {"switch": "shadow", "mode": "shadow", "on": True, "cliInstalled": True, "needsInstall": False,
            "needsLogin": False, "credentialsRejected": False, "loginInflight": False, "intentBlocked": False,
            "blockedWhy": "", "stats": {"ok": 12, "errors": 3, "last_error": None}}
    base.update(kw)
    return base


def _glamp(g):
    return ca._reader_health(now_ms=NOW, rows=[], g5=g, use_cache=False, auth={"loggedIn": None})["grok"]


class GrokHasItsOwnDisconnectLogic(unittest.TestCase):
    def test_a_grok_whose_sign_in_just_went_is_signed_out_not_switched_off(self):
        # the lane's effective mode drops to off the moment its sign-in is gone; his switch still says shadow
        h = _glamp(_grok(mode="off", on=False, needsLogin=True))
        self.assertEqual((h["state"], h["kind"]), ("off", "signed-out"), h)
        self.assertTrue(h["needsLogin"])
        self.assertNotIn("switched off", h["why"], "a sign-out read as a switch he flipped: %r" % h["why"])
        self.assertIn("click GROK", h["why"])

    def test_only_his_switch_reads_as_switched_off(self):
        h = _glamp(_grok(switch="off", mode="off", on=False, needsLogin=True))
        self.assertEqual((h["state"], h["kind"]), ("off", "switched-off"), h)
        # an older status without `switch` keeps the old reading
        old = _grok(mode="off", on=False)
        del old["switch"]
        self.assertEqual(_glamp(old)["kind"], "switched-off")

    def test_a_refused_sign_in_is_a_disconnection_with_the_far_ends_words(self):
        h = _glamp(_grok(needsLogin=True, credentialsRejected=True,
                         stats={"ok": 5, "errors": 9, "last_error": "HTTP 401 Unauthorized"}))
        self.assertEqual((h["state"], h["kind"], h["needsLogin"]), ("off", "signed-out", True), h)
        self.assertIn("401", h["why"])

    def test_a_blocked_lane_and_a_healthy_one(self):
        h = _glamp(_grok(intentBlocked=True, blockedWhy="the Grok balance is exhausted"))
        self.assertEqual((h["state"], h["kind"]), ("off", "blocked"), h)
        self.assertIn("balance", h["why"])
        ok = _glamp(_grok(loginInflight=True))
        self.assertEqual((ok["state"], ok["kind"]), ("on", "on"), ok)
        self.assertTrue(ok["signInOpen"], "a login in flight is not said")
        # a lane that answers something other than a status is UNKNOWN (g5=None would ask the live lane instead)
        self.assertEqual(_glamp([])["kind"], "unknown")


class TheGrokLaneKnowsARefusedSignInIsNotASignIn(unittest.TestCase):
    def setUp(self):
        g5._LOGIN_PROC = None
        self.spawned = []

        class _P(object):
            pid = 4242

            def poll(self):
                return None

        def _popen(argv, **kw):
            self.spawned.append(list(argv))
            return _P()
        self._popen = _popen

    def tearDown(self):
        g5._LOGIN_PROC = None

    def _stats(self, err):
        return mock.patch.object(g5, "stats_view", lambda: {"last_error": err, "ok": 1, "errors": 1})

    def test_credentials_rejected_reads_only_the_last_call(self):
        self.assertTrue(g5.credentials_rejected("grok: HTTP 401 Unauthorized"))
        self.assertTrue(g5.credentials_rejected("Invalid API key"))
        self.assertFalse(g5.credentials_rejected("grok -p timeout 140s"))
        self.assertFalse(g5.credentials_rejected(None))
        # the hard-stop headline and the rejection share ONE list
        self.assertEqual(g5._hard_stop_why("HTTP 401"), g5._CRED_REJECT_SAY)

    def test_a_401_behind_an_auth_file_reopens_the_browser(self):
        with mock.patch.object(g5, "_grok_bin", lambda: "/fake/grok"), \
                mock.patch.object(g5, "_subscription_logged_in", lambda: True), \
                self._stats("HTTP 401 Unauthorized"), \
                mock.patch.object(g5.subprocess, "Popen", self._popen):
            out = g5.start_login(prefer_oauth=True)
        self.assertTrue(out.get("started"), "a refused sign-in answered %r" % out)
        self.assertEqual(self.spawned, [["/fake/grok", "login", "--oauth"]])

    def test_a_good_sign_in_opens_nothing(self):
        with mock.patch.object(g5, "_grok_bin", lambda: "/fake/grok"), \
                mock.patch.object(g5, "_subscription_logged_in", lambda: True), \
                self._stats("grok -p timeout 140s"), \
                mock.patch.object(g5.subprocess, "Popen", self._popen):
            out = g5.start_login(prefer_oauth=True)
        self.assertEqual(out.get("reason"), "already-authorized")
        self.assertEqual(self.spawned, [])

    def test_status_says_signed_out_for_a_refused_file(self):
        with mock.patch.object(g5, "_grok_bin", lambda: "/fake/grok"), \
                mock.patch.object(g5, "_subscription_logged_in", lambda: True), \
                mock.patch.object(g5, "_budget_counts", lambda: (0, 0)), \
                self._stats("HTTP 401 Unauthorized"):
            st = g5.status()
        self.assertTrue(st["needsLogin"], "a refused sign-in is not a needed login: %r" % st.get("needsLogin"))
        self.assertTrue(st["credentialsRejected"])
        with mock.patch.object(g5, "_grok_bin", lambda: "/fake/grok"), \
                mock.patch.object(g5, "_subscription_logged_in", lambda: True), \
                mock.patch.object(g5, "_budget_counts", lambda: (0, 0)), \
                self._stats(None):
            st = g5.status()
        self.assertFalse(st["needsLogin"])
        self.assertFalse(st["credentialsRejected"])


class ARefusalIsAStatedCodeNotDigitsInANumber(unittest.TestCase):
    """REG-1631 - both lamps' refusal readers, driven with the shapes the far end states and the shapes it never does."""

    STATED = (("HTTP 401: Unauthorized", "cred"), ("status code: 401", "cred"), ("(401)", "cred"),
              ("Invalid API key provided", "cred"),
              ('API error (status 402 Payment Required): Grok Build usage balance exhausted", "http_status": 402}',
               "balance"),
              ("insufficient credits on this team", "credit"), ("insufficient_quota", "credit"))
    NEVER = ("grok CLI timed out after 1401 ms", "session 1790401234567 read failed (exit 1)",
             "read 34020 bytes then EOF", "waited 401 s for an answer",
             "The system has insufficient system resources to complete the requested service", "status 429 rate limited")

    def test_a_stated_refusal_is_read(self):
        for err, kind in self.STATED:
            said = g5._hard_stop_why(err)
            self.assertIn(kind if kind != "cred" else "sign in", said, "a stated refusal was not read: %r -> %r" % (err, said))
            self.assertEqual(g5.credentials_rejected(err), kind == "cred", err)

    def test_digits_inside_a_number_are_never_a_refusal(self):
        for err in self.NEVER:
            self.assertFalse(g5.credentials_rejected(err), "SIGN IN lit by a number that merely holds 401: %r" % err)
            self.assertEqual(g5._hard_stop_why(err), "", "a stated refusal invented from %r" % err)


class TheLampNeverFlipsHisSwitch(unittest.TestCase):
    def test_keep_switch_wins_over_every_reason_to_switch_on(self):
        mv = ca._g5_login_moves_switch
        self.assertFalse(mv({"ok": True, "reason": "already-authorized"}, {"oauth": True, "keepSwitch": True}))
        self.assertFalse(mv({"ok": True, "reason": "spawned"}, {"setOn": True, "keepSwitch": True}))
        # the Advanced ⚡ keeps its own behaviour
        self.assertTrue(mv({"ok": True, "reason": "already-authorized"}, {"oauth": True}))
        self.assertTrue(mv({"ok": True, "reason": "spawned"}, {"setOn": True}))
        self.assertFalse(mv({"ok": False, "reason": "no-cli"}, {"setOn": True}))
        self.assertFalse(mv(None, {"setOn": True}))

    def test_the_route_asks_it(self):
        src = _read(os.path.join(HERE, "control_app.py"))
        a = src.index('        if path == "/api/g5_login":')
        b = src.index('        if path == "/kai_verdict":', a)
        self.assertIn("if _g5_login_moves_switch(out, body):", src[a:b],
                      "the Grok login route decides the switch somewhere the lamp's keepSwitch cannot reach")


class ClaudeHasItsOwnDisconnectLogic(unittest.TestCase):
    def setUp(self):
        self._saved = dict(ca._CLAUDE_AUTH)
        self._rc = dict(ca._READER_CACHE)

    def tearDown(self):
        ca._CLAUDE_AUTH.clear()
        ca._CLAUDE_AUTH.update(self._saved)
        ca._READER_CACHE.clear()
        ca._READER_CACHE.update(self._rc)

    def _ask(self, now, watching, val, answer):
        asked = []
        ca._CLAUDE_AUTH.update(at=now - 15, val=val, busy=False)

        def _probe(_bin):
            asked.append(1)
            return answer
        with mock.patch.object(ca, "_find_claude_bin", lambda: "/fake/claude"):
            ca._claude_auth_state(now=now, _probe=_probe, _thread=lambda f: f(), _watching=lambda _n: watching)
        return len(asked)

    def test_it_is_re_asked_every_few_seconds_only_while_he_is_signing_in(self):
        out = {"loggedIn": False, "method": None, "why": "signed out"}
        self.assertEqual(self._ask(1000.0, True, out, out), 1, "a sign-in being finished waited for the 5-min probe")
        self.assertEqual(self._ask(1000.0, False, out, out), 0, "the CLI was asked every 15 s with no sign-in open")
        on = {"loggedIn": True, "method": "oauth", "why": "signed in"}
        self.assertEqual(self._ask(1000.0, True, on, on), 0, "a signed-in CLI kept being asked every 10 s")

    def test_a_changed_answer_repaints_at_once(self):
        ca._READER_CACHE.update(at=time.time(), val={"claude": {"state": "off"}})
        self._ask(1000.0, True, {"loggedIn": False}, {"loggedIn": True, "method": "oauth", "why": "signed in"})
        self.assertEqual(ca._READER_CACHE["at"], 0.0, "the lamps waited out their cache after a sign-in landed")
        ca._READER_CACHE.update(at=123.0)
        self._ask(1000.0, True, {"loggedIn": False}, {"loggedIn": False, "why": "still out"})
        self.assertEqual(ca._READER_CACHE["at"], 123.0, "an unchanged answer dropped the cache")

    def test_a_check_that_never_started_is_not_still_running(self):
        """REG-1636 - a worker whose start raised left `busy` True for good: the lamp never asked the CLI again."""
        ca._CLAUDE_AUTH.update(at=0.0, val={"loggedIn": True, "why": "signed in"}, busy=False)

        def no_thread(_f):
            raise RuntimeError("can't start new thread")
        with mock.patch.object(ca, "_find_claude_bin", lambda: "/fake/claude"):
            ca._claude_auth_state(now=5000.0, _thread=no_thread, _watching=lambda _n: False)
        self.assertFalse(ca._CLAUDE_AUTH["busy"], "a check that never started still reads as running")
        self.assertIn("RuntimeError", ca._CLAUDE_AUTH.get("startFailed") or "")
        asked = []
        with mock.patch.object(ca, "_find_claude_bin", lambda: "/fake/claude"):
            ca._claude_auth_state(now=5000.0 + ca.CLAUDE_AUTH_EVERY_S + 1, _probe=lambda b: asked.append(b) or {"loggedIn": True},
                                  _thread=lambda f: f(), _watching=lambda _n: False)
        self.assertEqual(asked, ["/fake/claude"], "the lamp never asked again after a start that failed")

    def test_the_watch_window(self):
        saved = dict(CS._PROC)
        try:
            CS._PROC.update(proc=None, at=10000.0)
            self.assertTrue(CS.watching(now=10000.0 + 100))
            self.assertFalse(CS.watching(now=10000.0 + CS.WATCH_S + 1))

            class _Live(object):
                def poll(self):
                    return None
            CS._PROC.update(proc=_Live(), at=1.0)
            self.assertTrue(CS.watching(now=10 ** 9), "an open sign-in window was not watched")
        finally:
            CS._PROC.clear()
            CS._PROC.update(saved)

    def test_waiting_is_said_while_signing_in_and_never_once_it_is_on(self):
        def lamp(auth):
            with mock.patch.object(CS, "watching", lambda *a, **k: True):
                return ca._reader_health(now_ms=NOW, rows=[], g5=_grok(), use_cache=False, auth=auth)["claude"]
        out = lamp({"loggedIn": False, "why": "claude auth status: signed out (none)"})
        self.assertEqual((out["state"], out["kind"], out["signInOpen"]), ("off", "signed-out", True), out)
        on = lamp({"loggedIn": True, "why": "claude auth status: signed in"})
        self.assertEqual((on["state"], on["kind"], on["signInOpen"]), ("on", "on", False), on)


class _Tags(html.parser.HTMLParser):
    def __init__(self):
        html.parser.HTMLParser.__init__(self)
        self.found, self.stack = {}, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id") in ("rl-claude", "rl-grok"):
            self.found[a["id"]] = (tag, a, [x.get("id") or x.get("class") for x in self.stack])
        if tag not in ("br", "img", "input", "meta", "link", "i"):
            self.stack.append(a)

    def handle_endtag(self, tag):
        if self.stack and tag not in ("br", "img", "input", "meta", "link", "i"):
            self.stack.pop()


class TheCornerLampsAreTheLinks(unittest.TestCase):
    def test_each_lamp_is_a_button_wired_to_its_own_reader(self):
        p = _Tags()
        p.feed(_read(UI))
        for k in ("claude", "grok"):
            tag, a, parents = p.found["rl-" + k]
            self.assertEqual(tag, "button", "the %s lamp is a %s - nothing to click" % (k, tag))
            self.assertEqual(a.get("type"), "button")
            self.assertEqual(a.get("onclick"), "window._lampClick('%s', this)" % k)
            self.assertIn("reader-lamps", parents)

    @unittest.skipUnless(NODE, "node drives the page's own painter and click")
    def test_each_lamp_remembers_rings_and_clicks_on_its_own(self):
        ui = _read(UI)
        a = ui.index("  function _rlHint(k, L, state) {")
        b = ui.index("  window._lampClick = _lampClick;", a)
        prog = r"""
var ELS = {}, POSTS = [], TOASTS = [];
function El(){ this.attrs = {}; this.title = ''; this.hidden = true; this.disabled = false; this.textContent = '';
  var cls = {}; this.classList = { add: function(c){ cls[c] = 1; }, remove: function(){ for (var i = 0; i < arguments.length; i++) delete cls[arguments[i]]; },
                                   contains: function(c){ return !!cls[c]; } }; }
El.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
El.prototype.getAttribute = function(k){ return (k in this.attrs) ? this.attrs[k] : null; };
var document = { getElementById: function(id){ return ELS[id] || (ELS[id] = new El()); } };
var window = {};
function toastC(m){ TOASTS.push(m); }
function fetch(u, o){ POSTS.push([u, o && o.method, o && o.body]);
  return Promise.resolve({ json: function(){ return { ok: true, started: true, reason: 'spawned', why: 'opened' }; } }); }
""" + ui[a:b] + r"""
function st(k){ var e = ELS['rl-' + k]; return [e.attrs['data-lamp'], e.attrs['data-alert'] || '0', e.attrs['data-busy'] || '0']; }
var ON = { state: 'on', kind: 'on', why: 'reading' };
var C_OUT = { state: 'off', kind: 'signed-out', needsLogin: true, why: 'OAuth session expired' };
var out = {};
_paintReaderLamps({ claude: C_OUT, grok: ON });
out.first = { c: st('claude'), g: st('grok'), toasts: TOASTS.length };
_paintReaderLamps({ claude: ON, grok: ON });
out.back = { c: st('claude'), toasts: TOASTS.slice() }; TOASTS.length = 0;
_paintReaderLamps({ claude: C_OUT, grok: ON });
out.drop = { c: st('claude'), g: st('grok'), toasts: TOASTS.slice() };
_paintReaderLamps({ claude: C_OUT, grok: ON });
out.again = TOASTS.length;
_paintReaderLamps({ claude: C_OUT, grok: null });
_paintReaderLamps({ claude: C_OUT, grok: { state: 'off', kind: 'signed-out', needsLogin: true } });
out.grokDrop = { g: st('grok'), toasts: TOASTS.length };
_paintReaderLamps({ claude: { state: 'off', kind: 'signed-out', needsLogin: true, signInOpen: true }, grok: ON });
out.busy = st('claude')[2];
var nToasts = TOASTS.length;
_paintReaderLamps({ claude: C_OUT, grok: { state: 'off', kind: 'switched-off', why: 'the + GROK layer is switched off' } });
out.hisSwitch = { g: st('grok'), toasts: TOASTS.length - nToasts };
_paintReaderLamps({ claude: C_OUT, grok: ON });
out.title = ELS['rl-claude'].title;
Promise.resolve()
.then(function(){ return _lampClick('claude', ELS['rl-claude']); })
.then(function(j){ out.claudeClick = [j && j.reason, st('claude')[1], st('claude')[2]];
  _paintReaderLamps({ claude: ON, grok: { state: 'off', kind: 'switched-off' } }); return _lampClick('claude'); })
.then(function(j){ out.claudeOn = j && j.reason; return _lampClick('grok'); })
.then(function(j){ out.grokOff = j && j.reason;
  _paintReaderLamps({ claude: ON, grok: { state: 'off', kind: 'not-installed' } }); return _lampClick('grok'); })
.then(function(j){ out.grokMissing = j && j.reason;
  _paintReaderLamps({ claude: ON, grok: { state: 'off', kind: 'signed-out', needsLogin: true } }); return _lampClick('grok'); })
.then(function(){ _paintReaderLamps({ claude: ON, grok: null }); return _lampClick('grok'); })
.then(function(){ out.posts = POSTS; process.stdout.write(JSON.stringify(out)); });
"""
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        o = json.loads(r.stdout)
        # a lamp that was never ON does not ring - the fault ring already says it
        self.assertEqual(o["first"]["c"], ["off", "0", "0"], o["first"])
        self.assertEqual(o["first"]["toasts"], 0)
        self.assertEqual(o["back"]["c"][:2], ["on", "0"])
        self.assertEqual(len(o["back"]["toasts"]), 1, "coming back on was not said")
        self.assertIn("CLAUDE", o["back"]["toasts"][0])
        # the sudden drop rings, is said once, and leaves the other lamp alone
        self.assertEqual(o["drop"]["c"][:2], ["off", "1"], "a sudden disconnect did not ring: %r" % o["drop"])
        self.assertEqual(o["drop"]["g"][:2], ["on", "0"], "CLAUDE's drop touched GROK")
        self.assertEqual(len(o["drop"]["toasts"]), 1)
        self.assertIn("CLAUDE disconnected", o["drop"]["toasts"][0])
        self.assertIn("OAuth session expired", o["drop"]["toasts"][0])
        self.assertEqual(o["again"], 1, "the same drop was announced twice")
        self.assertEqual(o["grokDrop"]["g"][:2], ["off", "1"], "an UNKNOWN poll between ON and OFF hid GROK's drop")
        self.assertEqual(o["grokDrop"]["toasts"], 2)
        self.assertEqual(o["busy"], "1", "a sign-in being finished does not breathe")
        # his own switch is his choice, never a disconnection: no ring, no "disconnected" (the pixel probe caught it)
        self.assertEqual(o["hisSwitch"]["g"][:2], ["off", "0"], "switching + GROK off rang as a disconnect: %r" % o["hisSwitch"])
        self.assertEqual(o["hisSwitch"]["toasts"], 0, "switching + GROK off was announced as a disconnect")
        self.assertIn("click to open Claude's sign-in", o["title"])
        # clicks: each reader its own door; a click answers the ring
        self.assertEqual(o["claudeClick"][:2], ["spawned", "0"], o["claudeClick"])
        self.assertEqual(o["claudeOn"], "linked")
        self.assertEqual(o["grokOff"], "switched-off")
        self.assertEqual(o["grokMissing"], "not-installed")
        posts = o["posts"]
        self.assertEqual([p[:2] for p in posts],
                         [["/api/claude_login", "POST"], ["/api/g5_login", "POST"], ["/api/g5_login", "POST"]], posts)
        for p in posts[1:]:
            body = json.loads(p[2])
            self.assertEqual(body, {"oauth": True, "keepSwitch": True}, "the GROK lamp asked to flip the switch: %r" % body)


class TheRelaunchRefusalNeverAlerts(unittest.TestCase):
    def test_block_ones_toast_is_on_window_where_its_callers_look(self):
        # the relaunch refusal says `if (window.toast) window.toast(..) else alert(..)`: with toast local to its IIFE the
        # else ran - a modal over his console. The assignment must sit beside the declaration, in the same scope.
        ui = _read(UI)
        a = ui.index("  function toast(msg, ms){")
        b = ui.index("\n  }\n", a) + len("\n  }\n")
        # both ends are real boundaries (the function's close, the assignment itself), never a guessed length: between
        # them only comment lines may sit - any code there (an IIFE's close above all) moves it out of toast's scope
        c = ui.index("window.toast = toast;", b)
        between = [ln.strip() for ln in ui[b:c].split("\n") if ln.strip()]
        self.assertTrue(between and between[0].startswith("// REG-1618"), "the assignment's reason is not beside it")
        self.assertTrue(all(ln.startswith("//") for ln in between),
                        "code sits between toast and its window assignment: %r" % [ln for ln in between if not ln.startswith("//")][:3])
        self.assertEqual(ui[ui.rfind("\n", 0, c) + 1:c], "  ", "the assignment is not at toast's own indentation")


if __name__ == "__main__":
    unittest.main(verbosity=2)
