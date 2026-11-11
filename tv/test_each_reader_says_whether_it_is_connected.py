# -*- coding: utf-8 -*-
"""#105 (REG-1604) — EACH READER SAYS WHETHER IT IS CONNECTED, LIGHTS ON OR LIGHTS OFF.

MEASURED 2026-09-30 on his ALT: its Claude CLI was signed out ("Failed to authenticate: OAuth session expired and could
not be refreshed"). Since v3527 made Claude the reader, every frame it filmed for hours was read as nothing - and no
surface said so: the log line was "claude exit 1" with no reason, every doctor row read fine, and the corner chip was
green because the switch was on.

His words: "a button showing this like if synced or not under the toggle button for each - defaulted claude for primary
and the shadow for grok - lights on lights off style - so we know that they are connected".

  · ONE MEASURE, control_app._reader_health: Claude's NEWEST read in the last 2 h decides (on when it returned, off when
    it failed - with the reader's own words, and the sign-in step when the words are a sign-in failure); no read in the
    window is UNKNOWN. Grok: switched off / not installed / not signed in is OFF with that reason, else ON with its
    counts (a timeout is not a disconnection).
  · /api/status carries it; the page paints two lamps under the corner chip from it (a lamp never guesses: no answer is
    UNKNOWN); the doctor row "this machine's reader can read" asks the same measure.
Fixture rows and a stub lane status only - his journal is never read here. [[heart-first]] [[unknown-stays-unknown]]
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

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

_WORLD = tempfile.mkdtemp(prefix="reader_lamps_")
os.environ["TV_HIST"] = _WORLD
os.environ["TV_SESSIONS"] = os.path.join(_WORLD, "sessions.jsonl")

import control_app as ca  # noqa: E402
import console_doctor as cd  # noqa: E402

NOW = 1790780000000
NODE = shutil.which("node")

ALT_FAILED = {"lane": "deep", "scene": "gameplay", "mode": "empty", "names": [], "area": "", "conf": None,
              "model": "sonnet", "raw": "Failed to authenticate: OAuth session expired and could not be refreshed"}
GOOD = {"lane": "deep", "scene": "gameplay", "mode": "vision", "names": ["Shako"], "area": "Cold Plains", "conf": 0.9,
        "model": "sonnet"}
G5_ON = {"mode": "shadow", "on": True, "cliInstalled": True, "needsLogin": False,
         "stats": {"ok": 3004, "errors": 3155, "last_error": "grok -p timeout 140s"}}


def _at(row, mins_ago):
    r = dict(row)
    r["ts"] = r["completedTs"] = NOW - int(mins_ago * 60000)
    return r


def _health(rows, g5=G5_ON):
    return ca._reader_health(now_ms=NOW, rows=rows, g5=g5, use_cache=False)


class ClaudeSaysWhatItJustDid(unittest.TestCase):

    def test_the_alts_signed_out_reads_are_lights_off_with_the_sign_in_step(self):
        h = _health([_at(GOOD, 90), _at(ALT_FAILED, 3), _at(ALT_FAILED, 1)])["claude"]
        self.assertEqual(h["state"], "off", "a signed-out Claude read as connected: %r" % h)
        self.assertTrue(h["needsLogin"], "a sign-in failure was not recognised as one")
        self.assertIn("OAuth session expired", h["why"])
        self.assertIn("/login", h["why"], "the lamp does not say how to fix it")
        self.assertEqual((h["ok"], h["failed"]), (1, 2))

    def test_a_read_that_returned_is_lights_on(self):
        h = _health([_at(ALT_FAILED, 30), _at(GOOD, 2)])["claude"]
        self.assertEqual(h["state"], "on", "the NEWEST read returned, yet the lamp is %r" % h)

    def test_a_failure_that_is_not_a_sign_in_says_its_own_words(self):
        broken = dict(ALT_FAILED, raw="claude exit 3: the image could not be decoded")
        h = _health([_at(GOOD, 20), _at(broken, 1)])["claude"]
        self.assertEqual(h["state"], "off")
        self.assertEqual(h["kind"], "read-failed")
        self.assertFalse(h["needsLogin"], "a failed read was sent to /login")
        self.assertIn("could not be decoded", h["why"])

    def test_a_read_that_ran_out_of_time_is_unknown_never_a_disconnection(self):
        """REG-3227 - his ALT 11-06 03:08/03:13: 'backup: claude timed out - grok -p timeout 140s' lit CLAUDE off, the
        page said 'CLAUDE disconnected', and he signed in again to fix a sign-in that was never broken."""
        for words in ("backup: claude timed out \u2014 grok -p timeout 140s", "claude timed out after 120 s"):
            h = _health([_at(GOOD, 20), _at(dict(ALT_FAILED, raw=words), 1)])["claude"]
            self.assertEqual(h["state"], "unknown", "a timeout lit the lamp %r: %r" % (h["state"], h))
            self.assertEqual(h["kind"], "timed-out")
            self.assertFalse(h["needsLogin"], "a timeout was sent to /login")
            self.assertIn("not a sign-in problem", h["why"])
            self.assertIn("timed out", h["why"])
        # and a sign-in failure is still a sign-in failure, even when its words also say time
        both = dict(ALT_FAILED, raw="Failed to authenticate: OAuth refresh timed out")
        h = _health([_at(both, 1)])["claude"]
        self.assertEqual((h["state"], h["kind"]), ("off", "signed-out"), h)

    def test_signing_in_again_lights_the_lamp_before_the_next_read(self):
        """REG-3227 - the CLI's 'signed in', asked AFTER the read that could not sign in, is the newer word on the very
        thing that failed. Asked BEFORE it, it changes nothing."""
        rows = [_at(GOOD, 90), _at(ALT_FAILED, 5)]
        # v3881 (REG-3392) - "signed in" now means a real one-line read answered too: the status file alone cannot see a
        # revoked login (his work ALT 11-07). With that proof, after the failure, the lamp lights:
        after = {"loggedIn": True, "why": "claude auth status: signed in", "askedAtMs": NOW - 60000,
                 "verified": True, "verifiedAtMs": NOW - 50000}
        h = ca._reader_health(now_ms=NOW, rows=rows, g5=G5_ON, use_cache=False, auth=after)["claude"]
        self.assertEqual((h["state"], h["kind"], h["needsLogin"]), ("on", "signed-in-again", False), h)
        self.assertIn("signed in again", h["why"])
        # REG-3392 - the status file alone (no real line yet) does not: OFF, and it says a read is confirming it
        bare = {"loggedIn": True, "why": "claude auth status: signed in", "askedAtMs": NOW - 60000}
        h = ca._reader_health(now_ms=NOW, rows=rows, g5=G5_ON, use_cache=False, auth=bare)["claude"]
        self.assertEqual((h["state"], h["kind"]), ("off", "signed-out"), "the status file alone turned the lamp green: %r" % h)
        self.assertIn("cannot see a revoked login", h["why"])
        # REG-3392 - and a real line that could NOT sign in is OFF in its own words, whatever the status file says
        rev = dict(bare, verified=False, why="Failed to authenticate. API Error: 401 OAuth access token has been revoked.",
                   verifiedAtMs=NOW - 40000)
        h = ca._reader_health(now_ms=NOW, rows=[], g5=G5_ON, use_cache=False, auth=rev)["claude"]
        self.assertEqual((h["state"], h["needsLogin"]), ("off", True), h)
        self.assertIn("revoked", h["why"])
        before = dict(after, askedAtMs=NOW - 10 * 60000)
        h = ca._reader_health(now_ms=NOW, rows=rows, g5=G5_ON, use_cache=False, auth=before)["claude"]
        self.assertEqual((h["state"], h["kind"]), ("off", "signed-out"), "an older 'signed in' outranked a newer failure")
        undated = {"loggedIn": True, "why": "claude auth status: signed in"}
        h = ca._reader_health(now_ms=NOW, rows=rows, g5=G5_ON, use_cache=False, auth=undated)["claude"]
        self.assertEqual(h["state"], "off", "a 'signed in' with no time outranked a failed read")
        slow = ca._reader_health(now_ms=NOW, rows=[_at(GOOD, 20), _at(dict(ALT_FAILED, raw="claude timed out"), 1)],
                                 g5=G5_ON, use_cache=False, auth=after)["claude"]
        self.assertEqual((slow["state"], slow["kind"]), ("unknown", "timed-out"),
                         "signed in turned a read that ran out of time into 'no read to judge it by': %r" % slow)
        self.assertIn("Claude is signed in", slow["why"])

    def test_every_sign_in_sentence_says_when_it_was_checked(self):
        """REG-3323 (#51) - GrokBot on his window: the tip named the program it asks (claude auth status) and never WHEN.
        Signed in with no read, signed out, and a signed-in note on a timed-out read each say when the CLI answered;
        an answer with no time says so, never a guessed one."""
        on = {"loggedIn": True, "why": "claude auth status: signed in", "askedAtMs": NOW - 7 * 60000,
              "verified": True, "verifiedAtMs": NOW - 7 * 60000}     # v3881 (REG-3392) - and a real line answered
        h = ca._reader_health(now_ms=NOW, rows=[], g5=G5_ON, use_cache=False, auth=on)["claude"]
        self.assertEqual(h["state"], "on", h)
        self.assertIn("claude auth status: signed in, checked 7 min ago", h["why"])
        off = {"loggedIn": False, "why": "claude auth status: signed out (none)", "askedAtMs": NOW - 3 * 60000}
        h = ca._reader_health(now_ms=NOW, rows=[], g5=G5_ON, use_cache=False, auth=off)["claude"]
        self.assertEqual(h["state"], "off", h)
        self.assertIn("checked 3 min ago", h["why"])
        h = ca._reader_health(now_ms=NOW, rows=[], g5=G5_ON, use_cache=False, auth={"loggedIn": True, "why": "x"})["claude"]
        self.assertIn("check time not on record", h["why"], "an answer with no time read as a time")
        slow = ca._reader_health(now_ms=NOW, rows=[_at(GOOD, 20), _at(dict(ALT_FAILED, raw="claude timed out"), 1)],
                                 g5=G5_ON, use_cache=False, auth=on)["claude"]
        self.assertIn("checked 7 min ago", slow["why"])

    def test_the_probe_stamps_when_it_was_asked(self):
        src = open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.assertEqual(src.count('_v["askedAtMs"] = int(time.time() * 1000)'), 1,
                         "the CLI's answer carries no time, so it can never be newer than a failed read")

    def test_no_read_is_unknown_never_on_and_never_off(self):
        self.assertEqual(_health([])["claude"]["state"], "unknown")
        old = _health([_at(ALT_FAILED, 180), _at(GOOD, 200)])["claude"]
        self.assertEqual(old["state"], "unknown", "reads older than the window decided today's lamp: %r" % old)

    def test_an_unreadable_journal_is_unknown_and_says_so(self):
        orig = ca._journal_tail_rows
        ca._journal_tail_rows = lambda max_bytes=600000: None
        try:
            h = ca._reader_health(now_ms=NOW, g5=G5_ON, use_cache=False)["claude"]
        finally:
            ca._journal_tail_rows = orig
        self.assertEqual(h["state"], "unknown")
        self.assertIn("could not be read", h["why"], "an unreadable journal read as 'no reads'")

    def _from_file(self, text):
        """REG-1824 — drive the lamp over a real journal through the one reader's tail."""
        d = tempfile.mkdtemp(prefix="reader1824_")
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "sessions.jsonl")
        if text is not None:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        orig = ca._journal_path
        ca._journal_path = lambda: path
        try:
            return ca._reader_health(now_ms=NOW, g5=G5_ON, use_cache=False, auth={})["claude"]
        finally:
            ca._journal_path = orig

    def test_a_fresh_install_with_no_journal_is_not_an_unreadable_one(self):
        """REG-1824 — the tail reader said UNKNOWN for a missing file, so every fresh install's lamp
        said its journal could not be read. A missing file is a PC that has not read yet."""
        h = self._from_file(None)
        self.assertEqual(h["state"], "unknown")
        self.assertNotIn("could not be read", h["why"])
        self.assertIn("no Claude read", h["why"])

    def test_a_tail_of_only_bad_lines_is_not_a_pc_with_no_reads(self):
        """REG-1824 — the tail reader skipped every bad line and handed back [] - a quiet PC."""
        h = self._from_file("not json\n{also not\n")
        self.assertEqual(h["state"], "unknown")
        self.assertIn("could not be read", h["why"])

    def test_a_grok_row_is_not_claudes(self):
        g = dict(GOOD, model="grok-subscription-cli")
        self.assertEqual(_health([_at(g, 1)])["claude"]["state"], "unknown")


class GrokSaysItsLanesState(unittest.TestCase):

    def test_switched_off_not_installed_and_signed_out_are_lights_off(self):
        self.assertEqual(_health([], g5={"mode": "off", "on": False})["grok"]["state"], "off")
        self.assertIn("switched off", _health([], g5={"mode": "off"})["grok"]["why"])
        self.assertIn("not installed", _health([], g5=dict(G5_ON, cliInstalled=False))["grok"]["why"])
        self.assertIn("not signed in", _health([], g5=dict(G5_ON, needsLogin=True))["grok"]["why"])

    def test_a_working_lane_is_lights_on_with_its_counts(self):
        g = _health([])["grok"]
        self.assertEqual(g["state"], "on")
        self.assertIn("3004 ok", g["why"])
        self.assertIn("timeout", g["why"], "the lane's last error is hidden behind a green lamp")

    def test_the_last_error_says_how_old_it_is(self):
        """* v3897 (REG-3697) - MEASURED 11-11 on his Mac: "last error: grok -p timeout 140s" beside a lane last asked 8 days
        earlier, the error itself a month old - it read as a lane failing now. The error carries its age, or says the age
        was never recorded."""
        old = dict(G5_ON, stats=dict(G5_ON["stats"], last_error_ts=NOW - 31 * 86400 * 1000))
        self.assertIn("last error: grok -p timeout 140s, 31.0 days ago", _health([], g5=old)["grok"]["why"])
        self.assertIn("when it happened was not recorded", _health([])["grok"]["why"],
                      "an error with no time reads as if it were current")


class TheDoctorAsksTheSameMeasure(unittest.TestCase):

    def _row(self, h):
        orig = ca._reader_health
        ca._reader_health = lambda **kw: h
        try:
            return cd._check_this_machines_reader_can_read()
        finally:
            ca._reader_health = orig

    def test_off_is_missing_on_is_ok_nothing_is_unknown(self):
        self.assertEqual(self._row(_health([_at(ALT_FAILED, 1)]))[0], cd.MISSING)
        self.assertIn("/login", self._row(_health([_at(ALT_FAILED, 1)]))[1])
        self.assertEqual(self._row(_health([_at(GOOD, 1)]))[0], cd.OK)
        self.assertEqual(self._row(_health([]))[0], cd.UNKNOWN)

    def test_the_row_is_registered(self):
        names = [n for n, _f in cd.CHECKS] if hasattr(cd, "CHECKS") else None
        src = io.open(os.path.join(HERE, "console_doctor.py"), encoding="utf-8").read()
        self.assertIn('("this machine\'s reader can read", _check_this_machines_reader_can_read)', src)
        if names is not None:
            self.assertIn("this machine's reader can read", names)


class ThePageLightsTheLamps(unittest.TestCase):

    def test_status_carries_the_measure_and_the_page_asks_it(self):
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.assertIn('"readers": _t("readers", _reader_health),', src)
        ui = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
        self.assertIn("window._paintReaderLamps(st.readers)", ui, "the status poll never paints the lamps")
        self.assertIn('id="rl-claude"', ui)
        self.assertIn('id="rl-grok"', ui)

    @unittest.skipUnless(NODE, "node drives the page's own painter")
    def test_the_painter_lights_what_it_is_told_and_guesses_nothing(self):
        ui = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
        a = ui.index("  function _paintReaderLamps(rd) {")
        b = ui.index("  window._paintReaderLamps = _paintReaderLamps;", a)
        fn = ui[a:b]
        prog = r"""
var ELS = {};
function El(){ this.attrs = {}; this.title = ''; }
El.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
var document = { getElementById: function(id){ return ELS[id] || (ELS[id] = new El()); } };
var window = {};
""" + fn + r"""
var out = {};
function snap(){ return { c: [ELS['rl-claude'].attrs['data-lamp'], ELS['rl-claude'].attrs['data-fault'], ELS['rl-claude'].title],
                          g: [ELS['rl-grok'].attrs['data-lamp'], ELS['rl-grok'].attrs['data-fault'], ELS['rl-grok'].title] }; }
_paintReaderLamps(RD1); out.one = snap();
_paintReaderLamps(null); out.none = snap();
process.stdout.write(JSON.stringify(out));
"""
        rd1 = _health([_at(ALT_FAILED, 1)])
        prog = prog.replace("RD1", json.dumps(rd1))
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        o = json.loads(r.stdout)
        self.assertEqual(o["one"]["c"][:2], ["off", "1"], "a signed-out Claude did not light OFF with its fault ring")
        self.assertIn("NOT CONNECTED", o["one"]["c"][2])
        self.assertIn("/login", o["one"]["c"][2])
        self.assertEqual(o["one"]["g"][0], "on")
        self.assertEqual([o["none"]["c"][0], o["none"]["g"][0]], ["unknown", "unknown"],
                         "no answer from the console lit a lamp")


RED_PROOF = [
    {"why": "v3897 (REG-3697) - the lane's last error is shown with no age again (a month-old timeout reads as current)",
     "file": "tv/control_app.py",
     "find": "            (\" - last error: %s%s\" % (st.get(\"last_error\"), _le_age)) if st.get(\"last_error\") else \"\"))",
     "replace": "            (\" - last error: %s\" % st.get(\"last_error\")) if st.get(\"last_error\") else \"\"))",
     "matches": 1},
    {"why": "v3897 (REG-3697) - an error with no recorded time is given an age anyway",
     "file": "tv/control_app.py",
     "find": "            _le_age = \", %s ago\" % _fmt_age_ms(now - float(_le_ts)) if _le_ts else \", when it happened was not recorded\"\n",
     "replace": "            _le_age = \", %s ago\" % _fmt_age_ms(now - float(_le_ts or 0))\n",
     "matches": 1},
    {"why": "REG-3323 - the Claude lamp's sign-in sentence never says when the CLI last answered (GrokBot on his window)",
     "file": "control_app.py",
     "find": "    return \"checked just now\" if m < 1 else (\"checked %d min ago\" % m if m < 120 else \"checked %d h ago\" % (m // 60))\n",
     "replace": "    return \"\"\n",
     "matches": 1},
    {"why": "REG-3227 - a read that ran out of time lights Claude OFF again (his ALT 11-06: 'CLAUDE disconnected')",
     "file": "tv/control_app.py",
     "find": "            _slow = (not lamp[\"needsLogin\"]) and any(w in _why.lower() for w in _READER_TIMEOUT_WORDS)\n",
     "replace": "            _slow = False\n", "matches": 1},
    {"why": "REG-3227 - signing in again leaves the lamp off until a read comes back",
     "file": "tv/control_app.py",
     "find": "          and _au[\"askedAtMs\"] > lamp[\"lastFailTs\"]):\n",
     "replace": "          and False):\n", "matches": 1},
    {"why": "REG-3227 - an older 'signed in' outranks a newer failed read",
     "file": "tv/control_app.py",
     "find": "          and _au[\"askedAtMs\"] > lamp[\"lastFailTs\"]):\n",
     "replace": "          and True):\n", "matches": 1},
    {"why": "REG-3227 - signed in turns a timed-out read into 'no read to judge it by' (green over a read that did not finish)",
     "file": "tv/control_app.py",
     "find": "    elif (isinstance(_au, dict) and _au.get(\"loggedIn\") is True and lamp.get(\"state\") == \"unknown\"\n          and lamp.get(\"kind\") == \"timed-out\"):\n",
     "replace": "    elif False:\n", "matches": 1},
    {"why": "REG-1824 - the tail reader calls a missing journal unreadable again, so a fresh install's lamp says broken",
     "file": "control_app.py",
     "find": "        if st is None:\n            return out\n",
     "replace": "        if st is None:\n            out[\"why\"] = \"missing\"\n            return out\n",
     "matches": 1},
    {"why": "#105 - a failed newest read lights Claude ON (the ALT's signed-out day, green)",
     "file": "tv/control_app.py",
     "find": "        if _claude_row_missed(last):\n            _why = str(last.get(\"readErr\") or \"\").strip()\n",
     "replace": "        if False:\n            _why = str(last.get(\"readErr\") or \"\").strip()\n", "matches": 1},
    {"why": "#105 - a sign-in failure is not recognised, so the lamp never says /login",
     "file": "tv/control_app.py",
     "find": "            lamp[\"needsLogin\"] = any(w in _why.lower() for w in _READER_AUTH_WORDS)\n",
     "replace": "            lamp[\"needsLogin\"] = False\n", "matches": 1},
    {"why": "#105 - reads older than the window decide today's lamp",
     "file": "tv/control_app.py",
     "find": "        if ts and now - ts <= _READER_WINDOW_MS:\n",
     "replace": "        if ts:\n", "matches": 1},
    {"why": "#105 - no read at all lights a lamp instead of UNKNOWN",
     "file": "tv/control_app.py",
     "find": "        lamp.update(state=\"unknown\", kind=\"unknown\", why=(\"the journal could not be read, so whether Claude can read is UNKNOWN\"\n",
     "replace": "        lamp.update(state=\"on\", kind=\"unknown\", why=(\"the journal could not be read, so whether Claude can read is UNKNOWN\"\n",
     "matches": 1},
    {"why": "#105 - a switched-off Grok layer reads as connected",
     "file": "tv/control_app.py",
     "find": "    elif _his_off:\n",
     "replace": "    elif False:\n", "matches": 1},
    {"why": "#105 - the doctor calls a reader that cannot read fine",
     "file": "tv/console_doctor.py",
     "find": "        return MISSING, \"%s (%s failed, %s returned in 2 h)%s\" % (c.get(\"why\"), c.get(\"failed\"), c.get(\"ok\"), tail)\n",
     "replace": "        return OK, \"%s (%s failed, %s returned in 2 h)%s\" % (c.get(\"why\"), c.get(\"failed\"), c.get(\"ok\"), tail)\n",
     "matches": 1},
    {"why": "#105 - the painter guesses: every lamp lights ON whatever it is told",
     "file": "tv/control_ui.html",
     "find": "      var state = (L && (L.state === 'on' || L.state === 'off')) ? L.state : 'unknown';\n",
     "replace": "      var state = 'on';\n", "matches": 1},
    {"why": "#105 - /api/status stops carrying the measure (the lamps go dark for good)",
     "file": "tv/control_app.py",
     "find": "        \"readers\": _t(\"readers\", _reader_health),\n",
     "replace": "", "matches": 1},
    {"why": "#105 - the status poll stops painting the lamps (the unjoined end)",
     "file": "tv/control_ui.html",
     "find": "window._paintReaderLamps(st.readers)",
     "replace": "window._paintReaderLampsX(st.readers)", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
