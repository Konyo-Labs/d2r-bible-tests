# -*- coding: utf-8 -*-
"""v3881 (REG-3392) - THE CLAUDE LAMP IS GREEN ONLY WHEN CLAUDE ITSELF ANSWERS, AND A DOUBLE CLICK ALWAYS OPENS ITS SIGN-IN.

His words 2026-11-07: "make sure the green lamp for claude is synced to red if it is off.. currently its ... reading it as
green as if it was connected", then "when i click the lamp ... it says its already connected and doesnt let me reconnect",
then "a double click on the claude lamp forces it to open regardless".

MEASURED on his work ALT that evening: `claude -p` -> "Failed to authenticate. API Error: 401 OAuth access token has been
revoked." (rc 1, on stdout) while `claude auth status` -> "loggedIn": true. Every read failed; the Grok backup answered three
of them and each was journaled {model: sonnet, eye: grok, backup: "backup: claude signed out"}. The lamp read only `model`,
so Grok's answers counted as Claude's -> GREEN, and its click answered "linked" with no way through.

Now: a read the Grok backup answered is a CLAUDE miss with Claude's own words; "signed out" / "revoked" are sign-in words;
the status file's "signed in" turns the lamp green only after a real one-line Claude read answered (it cannot see a revoked
login); and two clicks on the same Claude lamp in the same state within 5 s open its sign-in whatever the lamp says.
A timeout stays UNKNOWN (REG-3227) and a Grok read under his GROK ONLY switch is never Claude's. RED_PROOF below.
[[unknown-stays-unknown]] [[the-unjoined-end]]
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

os.environ.setdefault("TV_STUB", "1")
import control_app as ca  # noqa: E402

NODE = shutil.which("node") or shutil.which("nodejs")
NOW = 1794073300000
G5_ON = {}

# his work ALT's own rows, 11-07 (sessions.jsonl), trimmed to the fields the lamp reads
GROK_ANSWERED = {"lane": "deep", "model": "sonnet", "mode": "oneshot", "eye": "grok", "backup": "backup: claude signed out",
                 "raw": '{"area":"","tz":[],"scene":"town"}'}
CLAUDE_TIMED_OUT = {"lane": "deep", "model": "sonnet", "mode": "empty", "readFailed": True, "eye": "unread",
                    "backup": "backup: claude timed out", "readErr": "backup: claude timed out — grok -p timeout 140s"}
CLAUDE_READ = {"lane": "deep", "model": "sonnet", "mode": "oneshot", "eye": "claude", "raw": '{"scene":"town"}'}
GROK_ONLY = {"lane": "deep", "model": "sonnet", "mode": "oneshot", "eye": "grok", "raw": '{"scene":"town"}'}


def _at(row, mins_ago):
    return dict(row, completedTs=NOW - mins_ago * 60000)


def _lamp(rows, auth=None):
    return ca._reader_health(now_ms=NOW, rows=rows, g5=G5_ON, use_cache=False, auth=auth)["claude"]


class AGrokAnswerIsAClaudeMiss(unittest.TestCase):

    def test_his_alt_reads_turn_the_claude_lamp_red_and_ask_for_a_sign_in(self):
        """* THE POINT: the rows his ALT wrote while Claude's login was revoked read OFF + sign in, never green"""
        h = _lamp([_at(CLAUDE_TIMED_OUT, 30), _at(GROK_ANSWERED, 12), _at(GROK_ANSWERED, 2)])
        self.assertEqual((h["state"], h["kind"], h["needsLogin"]), ("off", "signed-out", True), h)
        self.assertIn("claude signed out", h["why"])
        self.assertEqual((h["ok"], h["failed"]), (0, 3), "a Grok answer was counted as Claude's: %r" % h)

    def test_baseline_a_read_claude_answered_is_green(self):
        h = _lamp([_at(GROK_ANSWERED, 20), _at(CLAUDE_READ, 1)])
        self.assertEqual(h["state"], "on", h)

    def test_a_grok_read_under_grok_only_is_never_claudes(self):
        """his switch at GROK ONLY: Claude was not asked, so its lamp is not judged by Grok's reads"""
        h = _lamp([_at(CLAUDE_READ, 30), _at(GROK_ONLY, 1)])
        self.assertEqual(h["state"], "on", "a Grok read Claude was never asked for turned the Claude lamp off: %r" % h)

    def test_a_backed_up_timeout_is_still_unknown(self):
        """REG-3227 stands: a timeout says nothing about the sign-in"""
        h = _lamp([_at(dict(GROK_ANSWERED, backup="backup: claude timed out"), 1)])
        self.assertEqual((h["state"], h["kind"], h["needsLogin"]), ("unknown", "timed-out", False), h)


class TheStatusFileIsNotProof(unittest.TestCase):

    STATUS = {"loggedIn": True, "why": "claude auth status: signed in", "askedAtMs": NOW - 60000}

    def test_signed_in_on_the_status_file_alone_never_turns_a_failed_lamp_green(self):
        h = _lamp([_at(GROK_ANSWERED, 5)], auth=self.STATUS)
        self.assertEqual(h["state"], "off", "the status file's 'signed in' outranked a revoked login: %r" % h)
        self.assertIn("cannot see a revoked login", h["why"])

    def test_a_real_line_that_answered_after_the_failure_turns_it_green(self):
        h = _lamp([_at(GROK_ANSWERED, 5)], auth=dict(self.STATUS, verified=True, verifiedAtMs=NOW - 30000))
        self.assertEqual((h["state"], h["kind"]), ("on", "signed-in-again"), h)

    def test_a_real_line_that_could_not_sign_in_is_red_in_its_words_even_with_no_reads(self):
        rev = dict(self.STATUS, verified=False, verifiedAtMs=NOW - 30000,
                   why="Failed to authenticate. API Error: 401 OAuth access token has been revoked.")
        h = _lamp([], auth=rev)
        self.assertEqual((h["state"], h["needsLogin"]), ("off", True), h)
        self.assertIn("401 OAuth access token has been revoked", h["why"])

    def test_no_reads_and_only_the_status_file_is_unknown_until_a_real_line_answers(self):
        h = _lamp([], auth=self.STATUS)
        self.assertEqual(h["state"], "unknown", "the status file alone lit an idle lamp: %r" % h)
        self.assertEqual(_lamp([], auth=dict(self.STATUS, verified=True, verifiedAtMs=NOW - 60000))["state"], "on")

    def test_the_real_line_reads_its_own_answer(self):
        class R(object):
            def __init__(self, rc, out, err=""):
                self.returncode, self.stdout, self.stderr = rc, out, err

        def run_with(r):
            return lambda *a, **k: r
        v = ca._claude_verify_call("claude", _run=run_with(R(1, "Failed to authenticate. API Error: 401 OAuth access token "
                                                              "has been revoked.\n")))
        self.assertIs(v["verified"], False, v)
        self.assertIn("revoked", v["why"])
        self.assertIs(ca._claude_verify_call("claude", _run=run_with(R(0, "OK\n")))["verified"], True)

        def slow(*a, **k):
            raise subprocess.TimeoutExpired("claude", 60)
        self.assertIsNone(ca._claude_verify_call("claude", _run=slow)["verified"], "a timeout was taken as an answer")
        self.assertIsNone(ca._claude_verify_call("claude", _run=run_with(R(2, "some crash")))["verified"])


@unittest.skipUnless(NODE, "node drives the page's own click - UNMEASURED here, not a pass")
class ADoubleClickAlwaysOpensClaudesSignIn(unittest.TestCase):

    def _drive(self, script):
        ui = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
        a = ui.index("  function _rlHint(k, L, state) {")
        b = ui.index("  window._lampClick = _lampClick;", a)
        prog = r"""
var ELS = {}, POSTS = [], TOASTS = [];
function El(){ this.attrs = {}; this.title = ''; this.hidden = true; this.disabled = false; this.textContent = '';
  var cls = {}; this.classList = { add: function(c){ cls[c] = 1; }, remove: function(){}, contains: function(c){ return !!cls[c]; } }; }
El.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
El.prototype.getAttribute = function(k){ return (k in this.attrs) ? this.attrs[k] : null; };
var document = { getElementById: function(id){ return ELS[id] || (ELS[id] = new El()); } };
var window = {};
function toastC(m){ TOASTS.push(m); }
function fetch(u, o){ POSTS.push(u);
  return Promise.resolve({ json: function(){ return { ok: true, started: true, reason: 'spawned', why: 'opened' }; } }); }
""" + ui[a:b] + script
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        return json.loads(r.stdout)

    def test_a_green_claude_lamp_double_clicked_opens_its_sign_in(self):
        """* THE POINT of his ask: one click on a green lamp says linked and how to force it; the second opens the sign-in"""
        o = self._drive(r"""
var ON = { state: 'on', kind: 'on', why: 'reading' }, out = {};
_paintReaderLamps({ claude: ON, grok: ON });
Promise.resolve().then(function(){ return _lampClick('claude'); })
.then(function(j){ out.first = [j.reason, POSTS.length, TOASTS[TOASTS.length - 1]]; return _lampClick('claude'); })
.then(function(j){ out.second = [j.reason, POSTS.slice()]; process.stdout.write(JSON.stringify(out)); });
""")
        self.assertEqual(o["first"][:2], ["linked", 0])
        self.assertIn("click again within 5 s", o["first"][2])
        self.assertEqual(o["second"], ["spawned", ["/api/claude_login"]], o)

    def test_a_timed_out_lamp_double_clicked_opens_too_but_one_click_still_does_not(self):
        o = self._drive(r"""
var SLOW = { state: 'unknown', kind: 'timed-out', needsLogin: false, why: 'ran out of time' }, out = {};
_paintReaderLamps({ claude: SLOW, grok: { state: 'on', kind: 'on' } });
Promise.resolve().then(function(){ return _lampClick('claude'); })
.then(function(j){ out.first = [j.reason, POSTS.length]; return _lampClick('claude'); })
.then(function(j){ out.second = [j.reason, POSTS.slice()]; process.stdout.write(JSON.stringify(out)); });
""")
        self.assertEqual(o["first"], ["timed-out", 0], "one click on a timed-out lamp opened a sign-in (REG-3227)")
        self.assertEqual(o["second"], ["spawned", ["/api/claude_login"]], o)

    def test_the_grok_lamp_is_not_forced(self):
        o = self._drive(r"""
var ON = { state: 'on', kind: 'on', why: 'reading' }, out = {};
_paintReaderLamps({ claude: ON, grok: ON });
Promise.resolve().then(function(){ return _lampClick('grok'); }).then(function(){ return _lampClick('grok'); })
.then(function(j){ out.second = [j.reason, POSTS.slice()]; process.stdout.write(JSON.stringify(out)); });
""")
        self.assertEqual(o["second"], ["linked", []], o)


RED_PROOF = [
    {"why": "REG-3392 - a Grok backup answer counts as Claude's again (his ALT's lamp green on a revoked login)",
     "file": "tv/control_app.py",
     "find": '    return str(r.get("eye") or "").lower() == "grok" and bool(str(r.get("backup") or "").strip())\n',
     "replace": '    return False\n', "matches": 1},
    {"why": "REG-3392 - 'signed out' is no longer a sign-in word (the lamp says read-failed, the click opens nothing)",
     "file": "tv/control_app.py", "find": '                      "signed out", "revoked")',
     "replace": '                      "revoked")', "matches": 1},
    {"why": "REG-3392 - the status file's 'signed in' turns a failed lamp green again",
     "file": "tv/control_app.py",
     "find": '          and _au["askedAtMs"] > lamp["lastFailTs"] and not _verified_after(_au, lamp.get("lastFailTs"), now)):\n',
     "replace": '          and _au["askedAtMs"] > lamp["lastFailTs"] and False):\n', "matches": 1},
    {"why": "REG-3392 - a real line that could not sign in is read as UNKNOWN",
     "file": "tv/control_app.py",
     "find": '        return {"verified": False, "why": first[:200] or "Claude could not sign in", "verifiedAtMs": at}\n',
     "replace": '        return {"verified": None, "why": first[:200] or "Claude could not sign in", "verifiedAtMs": at}\n',
     "matches": 1},
    {"why": "REG-3392 - a double click no longer forces Claude's sign-in open (his ask)",
     "file": "tv/control_ui.html",
     "find": "    var forced = (k === 'claude') && !!_arm && _arm.k === k && _arm.kind === kind && (_now - _arm.at) < 5000;\n",
     "replace": "    var forced = false;\n", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
