# -*- coding: utf-8 -*-
"""REG-1617 — CLAUDE SIGNS IN FROM THE CONSOLE: A SIGN IN BUTTON UNDER THE LAMPS, ON THE PC THAT NEEDS IT.

His ask, 2026-09-30: "make a button there so i can click within the console.. where we said it should render if we are
still connected because this happens monthly i think it just disconnects sometimes". MEASURED the same evening on his
ALT: `claude auth status --json` answered "authMethod": "none" while every read failed with "OAuth session expired" -
and the only way back in was a terminal he had to find and type into.

Driven, joint by joint, never by grepping prose:
  1. claude_signin.status - the CLI's own loggedIn; no CLI / no answer / garbage is UNKNOWN (None), never "signed out".
  2. claude_signin.start - the ONE fixed command (`claude auth login`) in a window HE CAN SEE: on Windows a new console
     with SW_SHOWNORMAL that the console's own no-window door (win_quiet, REG-1307) leaves visible - driven through that
     door, because a hidden sign-in would hang for ever; on the Mac, Terminal. One sign-in in flight at a time.
  3. control_app - the route answers only this console's own page (Origin), starts the sign-in and re-arms the CLI
     probe; the lamp learns "signed out" from the CLI itself (so the button shows before a read has to fail), a read
     that just succeeded outranks it, and an UNKNOWN probe changes nothing.
  4. the header - the SIGN IN pill exists under the lamps, the page's own painter shows it only for needsLogin and says
     when a sign-in is already open, and the click POSTs the route.
Nothing here opens a window or spawns the CLI: every spawn is a recorded fake. RED_PROOF below.
"""
import html.parser
import io
import json
import os
import shutil
import subprocess
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import claude_signin as CS  # noqa: E402
import win_quiet as WQ  # noqa: E402

NODE = shutil.which("node")
UI = os.path.join(HERE, "control_ui.html")

RED_PROOF = [
    {"why": "REG-1985 - a PC with no Claude CLI is told 'nothing to sign in with' again, and never how to get one",
     "file": "claude_signin.py",
     "find": "        return None, (\"the Claude CLI is not installed on this PC - install it once in %s:  %s  - then click SIGN IN \"\n",
     "replace": "        return None, \"the Claude CLI was not found on this PC, so there is nothing to sign in with\"; (\"\"\n",
     "matches": 1},
    {"why": "REG-1639 - the Mac's second click opens a second Terminal sign-in again (osascript leaves nothing to ask)",
     "file": "claude_signin.py",
     "find": "        if how == \"terminal\" and _PROC.get(\"proc\") is None and _at is not None and 0 <= now - float(_at) < TERMINAL_AGAIN_S:\n",
     "replace": "        if False:\n", "matches": 1},
    {"why": "REG-1617 - the sign-in opens hidden: win_quiet's door would hide a console that hands in no STARTUPINFO",
     "file": "claude_signin.py",
     "find": "            kw.update(creationflags=CREATE_NEW_CONSOLE, startupinfo=si)\n",
     "replace": "            kw.update(creationflags=CREATE_NEW_CONSOLE)\n", "matches": 1},
    {"why": "REG-1617 - a second click opens a second sign-in window while the first is still open",
     "file": "claude_signin.py",
     "find": "        if inflight():\n",
     "replace": "        if False:\n", "matches": 1},
    {"why": "REG-1617 - any web page may pop a sign-in window on his machine: the origin guard is gone",
     "file": "control_app.py",
     "find": "    if not origin or origin not in ok_origins:\n        return 403, {\"ok\": False, \"started\": False, \"reason\": \"origin\",\n",
     "replace": "    if False:\n        return 403, {\"ok\": False, \"started\": False, \"reason\": \"origin\",\n", "matches": 1},
    {"why": "REG-1617 - the lamp never learns 'signed out' from the CLI: no button until a read has failed",
     "file": "control_app.py",
     "find": "    if isinstance(_au, dict) and _au.get(\"loggedIn\") is False and lamp.get(\"state\") != \"on\":\n",
     "replace": "    if False:\n", "matches": 1},
    {"why": "REG-1617 - a signed-in PC that has not read lately sits at '?' again, the light he could not find",
     "file": "control_app.py",
     "find": "    elif isinstance(_au, dict) and _au.get(\"loggedIn\") is True and lamp.get(\"state\") == \"unknown\":\n",
     "replace": "    elif False:\n", "matches": 1},
    {"why": "REG-1617 - the Advanced twin never says Linked: a signed-in Claude reads as needing a sign-in",
     "file": "control_ui.html",
     "find": "        ab.textContent = '\u26a1 Linked'; ab.classList.add('is-ok');\n",
     "replace": "        ab.textContent = '\u26a1 Sign in'; ab.classList.add('is-need');\n", "matches": 1},
    {"why": "REG-1617 - clicking a green Linked opens a sign-in anyway",
     "file": "control_ui.html",
     "find": "    if (btn && btn.classList && btn.classList.contains && btn.classList.contains('is-ok')) return Promise.resolve(null);\n",
     "replace": "", "matches": 1},
    {"why": "REG-1617 - the painter never shows SIGN IN",
     "file": "control_ui.html",
     "find": "      sb.hidden = !need;\n",
     "replace": "      sb.hidden = true;\n", "matches": 1},
]


class _Proc(object):
    def __init__(self, alive=True):
        self.alive = alive

    def poll(self):
        return None if self.alive else 0


class _SI(object):
    """A stand-in for subprocess.STARTUPINFO (it exists only on Windows)."""
    def __init__(self):
        self.dwFlags = 0
        self.wShowWindow = 0


class TheCliIsAskedAndDriven(unittest.TestCase):

    def setUp(self):
        CS._PROC.update(proc=None, at=None)

    def _run(self, out):
        return lambda *a, **k: mock.Mock(stdout=out, returncode=0)

    def test_status_is_the_clis_own_word_and_unknown_is_never_signed_out(self):
        self.assertIs(CS.status("/x/claude", _run=self._run('{"loggedIn": false, "authMethod": "none"}'))["loggedIn"], False)
        self.assertIs(CS.status("/x/claude", _run=self._run('{"loggedIn": true, "authMethod": "claude.ai"}'))["loggedIn"], True)
        for bad in ("", "not json", '{"authMethod": "none"}', '["x"]'):
            self.assertIsNone(CS.status("/x/claude", _run=self._run(bad))["loggedIn"], "%r read as a verdict" % bad)
        self.assertIsNone(CS.status(None)["loggedIn"], "no CLI read as signed out")

        def boom(*a, **k):
            raise OSError("gone")
        self.assertIsNone(CS.status("/x/claude", _run=boom)["loggedIn"])

    def test_the_command_is_fixed_per_os(self):
        argv, how = CS.command("C:\\u\\claude.exe", "win32")
        self.assertEqual((argv, how), (["C:\\u\\claude.exe", "auth", "login"], "window"))
        argv, how = CS.command("C:\\u\\claude.cmd", "win32")
        self.assertEqual((argv, how), (["cmd.exe", "/d", "/c", "C:\\u\\claude.cmd", "auth", "login"], "window"))
        argv, how = CS.command("/opt/claude/bin/claude", "darwin")
        self.assertEqual(argv[0], "osascript")
        self.assertIn("'/opt/claude/bin/claude' auth login", " ".join(argv))
        argv, why = CS.command("/usr/bin/claude", "linux")
        self.assertIsNone(argv)
        self.assertIn("claude auth login", why, "a PC with no window is not told what to type")
        self.assertIsNone(CS.command(None, "win32")[0])

    def test_the_windows_sign_in_is_visible_through_the_consoles_own_no_window_door(self):
        calls = []
        with mock.patch.object(CS.subprocess, "STARTUPINFO", _SI, create=True):
            r = CS.start("C:\\u\\claude.exe", "win32", _popen=lambda argv, **kw: calls.append((argv, kw)) or _Proc())
        self.assertTrue(r["started"], r)
        self.assertIn("paste the code", r.get("why") or "")
        argv, kw = calls[0]
        self.assertEqual(argv, ["C:\\u\\claude.exe", "auth", "login"])
        seen = WQ._quiet_kwargs(kw, mock.Mock(STARTUPINFO=_SI))
        self.assertFalse(seen["creationflags"] & WQ.CREATE_NO_WINDOW, "the door made the sign-in windowless")
        self.assertTrue(seen["creationflags"] & WQ.CREATE_NEW_CONSOLE)
        self.assertEqual(seen["startupinfo"].wShowWindow, CS.SW_SHOWNORMAL, "the door hid the sign-in window")

    def test_one_sign_in_at_a_time_and_none_without_a_cli(self):
        calls = []
        pop = lambda argv, **kw: calls.append(argv) or _Proc(alive=True)   # noqa: E731
        with mock.patch.object(CS.subprocess, "STARTUPINFO", _SI, create=True):
            first = CS.start("C:\\u\\claude.exe", "win32", _popen=pop)
            second = CS.start("C:\\u\\claude.exe", "win32", _popen=pop)
        self.assertTrue(first["started"])
        self.assertEqual((second["started"], second["reason"]), (False, "in-flight"))
        self.assertEqual(len(calls), 1, "a second click opened a second sign-in window")
        CS._PROC.update(proc=None)
        none = CS.start(None, "win32", _popen=pop)
        # REG-1639 - the Mac: osascript exits at once, so there is no process to ask; a second click two seconds later
        # opened a second Terminal sign-in (the #231 eye on 5979d7f3, reproduced). Now it says where the first one is.
        mac = []
        mpop = lambda argv, **kw: mac.append(argv) or _Proc(alive=False)   # noqa: E731
        CS._PROC.update(proc=None, at=None)
        m1 = CS.start("/opt/claude/bin/claude", "darwin", _popen=mpop, now=5000.0)
        m2 = CS.start("/opt/claude/bin/claude", "darwin", _popen=mpop, now=5002.0)
        self.assertTrue(m1["started"])
        self.assertEqual((m2["started"], m2["reason"]), (False, "in-flight"), "a second click opened a second Terminal sign-in")
        self.assertIn("Terminal", m2["why"])
        m3 = CS.start("/opt/claude/bin/claude", "darwin", _popen=mpop, now=5000.0 + CS.TERMINAL_AGAIN_S + 1)
        self.assertTrue(m3["started"], "a click long after the first could never open a fresh sign-in")
        self.assertEqual(len(mac), 2)
        CS._PROC.update(proc=None, at=None)
        self.assertEqual((none["started"], none["reason"]), (False, "no-cli"))
        # REG-1985 - a PC with no CLI is told the one line that installs it, on its own shell - never a dead end
        self.assertIn("PowerShell:  " + CS.INSTALL["win32"], none["why"], "a click on a PC with no Claude CLI went nowhere")
        mac_none = CS.start(None, "darwin", _popen=pop)
        self.assertIn("Terminal:  " + CS.INSTALL["other"], mac_none["why"])
        self.assertEqual(len(calls), 1)


class TheConsoleAnswersOnlyItsOwnPage(unittest.TestCase):

    def setUp(self):
        import control_app as ca
        self.ca = ca
        self.origin = "http://127.0.0.1:%d" % ca.CONTROL_PORT

    def test_the_route_is_origin_guarded_and_rearms_the_probe(self):
        ca, seen = self.ca, []
        code, out = ca.claude_login("https://evil.example", _start=lambda b: seen.append(b) or {"started": True})
        self.assertEqual((code, out["reason"]), (403, "origin"))
        code, out = ca.claude_login(None, _start=lambda b: seen.append(b) or {"started": True})
        self.assertEqual(code, 403)
        self.assertEqual(seen, [], "a foreign page reached the sign-in")
        with mock.patch.dict(ca._CLAUDE_AUTH, {"at": 12345.0}):
            code, out = ca.claude_login(self.origin, _start=lambda b: seen.append(b) or {"ok": True, "started": True},
                                        _bin="/x/claude")
            self.assertEqual((code, out["started"]), (200, True))
            self.assertEqual(seen, ["/x/claude"])
            self.assertEqual(ca._CLAUDE_AUTH["at"], 0.0, "a started sign-in did not re-arm the CLI probe")

    def test_the_real_post_route_reaches_it(self):
        ca, got = self.ca, {}
        h = ca.Handler.__new__(ca.Handler)
        h.path = "/api/claude_login"
        h.headers = {"Origin": self.origin, "Content-Length": "2"}
        h.rfile = io.BytesIO(b"{}")
        h._json = lambda code, obj: got.update(code=code, obj=obj)
        with mock.patch.object(CS, "start", lambda b, **k: {"ok": True, "started": True, "reason": "spawned", "why": "x"}), \
                mock.patch.object(ca, "_find_claude_bin", lambda *a, **k: "/x/claude"):
            h.do_POST()
        self.assertEqual((got.get("code"), (got.get("obj") or {}).get("started")), (200, True), got)

    def test_the_lamp_says_on_or_off_from_the_cli_and_the_reads_still_decide(self):
        """His words, looking at his Mac: "nothing is showing me the CLAUDE specifically on and off light". The lamp sat at
        "?" whenever no read had happened in 2 h, while the CLI said signed in. Now: signed out -> OFF + SIGN IN; signed in
        and nothing read -> ON; a read that just succeeded or just FAILED still decides; an UNKNOWN probe changes nothing."""
        ca = self.ca
        now = 1790000000000
        ok_read = [{"lane": "deep", "model": "claude-sonnet", "completedTs": now - 60000}]
        bad_read = [{"lane": "deep", "model": "claude-sonnet", "completedTs": now - 60000, "readFailed": True,
                     "readErr": "claude exit 3: the image could not be decoded"}]
        slow_read = [dict(bad_read[0], readErr="the read timed out")]
        out = ca._reader_health(now_ms=now, rows=[], g5={}, auth={"loggedIn": False, "why": "claude auth status: signed out (none)"})
        self.assertEqual((out["claude"]["state"], out["claude"]["needsLogin"]), ("off", True), out["claude"])
        self.assertIn("SIGN IN", out["claude"]["why"])
        self.assertIn("/login", out["claude"]["why"])
        on = ca._reader_health(now_ms=now, rows=[], g5={}, auth={"loggedIn": True, "why": "claude auth status: signed in",
                                                                  "verified": True, "verifiedAtMs": now - 1000})  # REG-3392
        self.assertEqual((on["claude"]["state"], on["claude"]["needsLogin"]), ("on", False),
                         "a signed-in PC with no recent read still shows '?' instead of ON")
        self.assertIn("signed in", on["claude"]["why"])
        good = ca._reader_health(now_ms=now, rows=ok_read, g5={}, auth={"loggedIn": False})
        self.assertEqual((good["claude"]["state"], good["claude"]["needsLogin"]), ("on", False),
                         "a read that just succeeded was overruled by the probe")
        failed = ca._reader_health(now_ms=now, rows=bad_read, g5={}, auth={"loggedIn": True})
        self.assertEqual(failed["claude"]["state"], "off", "a read that just FAILED was painted ON because the CLI is signed in")
        slow = ca._reader_health(now_ms=now, rows=slow_read, g5={}, auth={"loggedIn": True})
        self.assertEqual(slow["claude"]["state"], "unknown",
                         "REG-3227 - a read that ran out of time was painted %r beside a signed-in CLI" % slow["claude"]["state"])
        unk = ca._reader_health(now_ms=now, rows=[], g5={}, auth={"loggedIn": None, "why": "UNKNOWN"})
        self.assertEqual(unk["claude"]["state"], "unknown", "an UNKNOWN probe was read as a verdict")

    def test_the_probe_runs_off_the_request_path_and_is_not_repeated(self):
        """the thread seam CAPTURES the job instead of running it, so this can see the caller did not wait"""
        ca, runs, pending = self.ca, [], []
        with mock.patch.dict(ca._CLAUDE_AUTH, {"at": 0.0, "val": None, "busy": False}):
            probe = lambda b: runs.append(b) or {"loggedIn": False, "why": "x"}   # noqa: E731
            first = ca._claude_auth_state(now=1000.0, _probe=probe, _thread=pending.append)
            self.assertIsNone(first, "the caller waited on the CLI instead of reading the last answer")
            self.assertEqual(runs, [], "the CLI ran on the caller's own path")
            self.assertEqual(len(pending), 1, "no background ask was started")
            pending.pop()()                                   # the daemon thread runs
            again = ca._claude_auth_state(now=1001.0, _probe=probe, _thread=pending.append)
            self.assertEqual(again["loggedIn"], False)
            self.assertEqual((pending, len(runs)), ([], 1), "the CLI was asked again inside its window")


class _Find(html.parser.HTMLParser):
    def __init__(self):
        html.parser.HTMLParser.__init__(self)
        self.hit, self.stack, self.parent_of = None, [], {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id") == "rl-signin":
            self.hit = (tag, a, [x.get("class") for x in self.stack])
        if tag not in ("br", "img", "input", "meta", "link"):
            self.stack.append(a)

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()


class TheHeaderOffersIt(unittest.TestCase):

    def test_the_button_sits_under_the_lamps_and_calls_the_click(self):
        p = _Find()
        p.feed(io.open(UI, encoding="utf-8").read())
        self.assertIsNotNone(p.hit, "there is no SIGN IN button in the page")
        tag, a, parents = p.hit
        self.assertEqual(tag, "button")
        self.assertIn("head-right", parents, "the button is not in the header's right corner, under the lamps")
        self.assertIn("hidden", a, "the button shows before anything said Claude is signed out")
        self.assertEqual(a.get("onclick"), "window._claudeSignIn(this)")

    @unittest.skipUnless(NODE, "node drives the page's own painter and click")
    def test_the_painter_shows_it_only_when_signed_out_and_the_click_posts(self):
        ui = io.open(UI, encoding="utf-8").read()
        a = ui.index("  function _paintReaderLamps(rd) {")
        b = ui.index("  window._claudeSignIn = _claudeSignIn;", a)
        prog = r"""
var ELS = {}, POSTS = [];
function El(){ this.attrs = {}; this.title = ''; this.hidden = true; this.disabled = false; this.textContent = '';
  var cls = {}; this.classList = { add: function(c){ cls[c] = 1; }, remove: function(){ for (var i = 0; i < arguments.length; i++) delete cls[arguments[i]]; },
                                   contains: function(c){ return !!cls[c]; }, list: function(){ return Object.keys(cls).sort(); } }; }
El.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
El.prototype.getAttribute = function(k){ return (k in this.attrs) ? this.attrs[k] : null; };
var document = { getElementById: function(id){ return ELS[id] || (ELS[id] = new El()); } };
var window = {};
function fetch(u, o){ POSTS.push([u, o && o.method]); return Promise.resolve({ json: function(){ return { ok: true, started: true, why: 'opened' }; } }); }
""" + ui[a:b] + r"""
var out = {}, sb = function(){ return ELS['rl-signin']; };
function snap(){ return [sb().hidden, sb().textContent]; }
_paintReaderLamps({ claude: { state: 'off', needsLogin: true }, grok: { state: 'off' } }); out.signedOut = snap();
_paintReaderLamps({ claude: { state: 'off', needsLogin: true, signInOpen: true } }); out.open = snap();
_paintReaderLamps({ claude: { state: 'on', needsLogin: false } }); out.on = snap();
_paintReaderLamps({ claude: { state: 'off', needsLogin: false, why: 'timeout' } }); out.failedRead = snap();
_paintReaderLamps(null); out.none = snap();
var ab = function(){ return ELS['btn-claude-auth']; };
function adv(rd){ _paintReaderLamps(rd); return [ab().textContent, ab().classList.list().join(' ')]; }
out.adv = { on: adv({ claude: { state: 'on', why: 'signed in' } }), out: adv({ claude: { state: 'off', needsLogin: true } }),
            open: adv({ claude: { state: 'off', needsLogin: true, signInOpen: true } }),
            failed: adv({ claude: { state: 'off', needsLogin: false, why: 'timeout' } }), none: adv(null) };
ab().attrs['data-idle'] = '⚡ Sign in'; ab().attrs['data-busy'] = '⚡ Waiting…';
_paintReaderLamps({ claude: { state: 'on' } });
_claudeSignIn(ab()).then(function(linkedClick){
  out.linkedPosts = POSTS.length;
  _paintReaderLamps({ claude: { state: 'off', needsLogin: true } });
  return _claudeSignIn(ab());
}).then(function(){
  out.advAfter = ab().textContent;
  return _claudeSignIn(sb());
}).then(function(){ out.posts = POSTS; out.after = snap(); process.stdout.write(JSON.stringify(out)); });
"""
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        o = json.loads(r.stdout)
        self.assertEqual(o["signedOut"], [False, "SIGN IN"], o)
        self.assertEqual(o["open"], [False, "SIGNING IN…"], "an open sign-in offered a second one")
        for k in ("on", "failedRead", "none"):
            self.assertTrue(o[k][0], "%s showed SIGN IN" % k)
        # his "a button under advanced where it says linked so its like individual": Claude's own ⚡, the twin of Grok's
        self.assertEqual(o["adv"]["on"], ["⚡ Linked", "is-ok"], o["adv"])
        self.assertEqual(o["adv"]["out"], ["⚡ Sign in", "is-need"])
        self.assertEqual(o["adv"]["open"], ["⚡ Waiting…", "is-busy"])
        self.assertEqual(o["adv"]["failed"], ["⚡ Not reading", "is-need"])
        self.assertEqual(o["adv"]["none"], ["⚡ Claude ?", ""], "no answer painted the Advanced button as a state")
        self.assertEqual(o["linkedPosts"], 0, "clicking a green Linked opened a sign-in")
        self.assertEqual(o["advAfter"], "⚡ Waiting…", "the Advanced click did not say the sign-in is open")
        self.assertEqual(o["posts"], [["/api/claude_login", "POST"], ["/api/claude_login", "POST"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
