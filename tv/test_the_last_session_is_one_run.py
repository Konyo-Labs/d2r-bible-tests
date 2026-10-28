# -*- coding: utf-8 -*-
"""#86 (REG-2790, GrokBot's v3642 pass, carried to v3686) - "LAST SESSION" IS ONE RUN ON EVERY SURFACE THAT SAYS IT.

GrokBot: the home's 📼 LAST SESSION card read "session 28 · 526 reads · 239 missed" while the Shelf's ▶ Last session
opened "THEATRE · SESSION 48". Two rules: the digest named the newest reel KAI had sealed (kaiMissed set, else HD_ALL[1]),
the button the newest reel with more than 10 film stills and a named find (thPickEntrySession's tiers). MEASURED on his
journal 2026-10-28 ~16:07 with the two old rules re-run over it read-only: the digest named session 6 (02:00, sealed),
the button session 2 (15:00-16:00, 2,274 stills, not sealed yet).

One rule now, _lastSessionRow: the newest run that is over - not a stub, not a suite fixture, and ON AIR not the run being
recorded (n 1). Sealed or not; the digest's badge says which (REG-2102). The Shelf's ▶ Last session plays that run, or says
it has nothing to replay - it never plays another reel under its name (REG-1757).

REG-2811 (his ruling 2026-10-28 on the Theatre button: "yea join same logic why not") - the THIRD surface. The Theatre
button's "replay last session" played the newest reel with substance (v786/v885 tiers); it plays the same run now, and when
that run has nothing to play its stage says which run it is (_lastSessionNoFilmSay, the Shelf button's sentence) and no
other reel loads - the old fallback to session 1 is gone.

Driven: the real hdShelf -> hdLastSession, window._shelfLastSession -> thPickEntrySession(true), and thOpen ->
thPickEntrySession() (the Theatre button's open, its /api/sessions wait stubbed), cut out of control_ui.html and run in
node over the SAME /api/sessions rows; each case reads the session the digest names, the one the Shelf button loads and
the one the Theatre loads.

REG-2868 (GrokBot #230 6477559571) - "the run being recorded" was read off the body alone, and a shadow-reader recording keeps
the body off on purpose: the Mac's digest read "session 1 · 19m00s → 22m57s · ◌ OPEN" across two loads while the console
was live. Every /api/sessions row now carries ended (control_app._session_ended: a session end, a sealed reel or a newer run
= true; session 1 with an id and none of those = false; no id = null). A false is skipped whatever the body says; a null is
shown and the digest says "ended UNKNOWN". RED_PROOF below.
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

NODE = shutil.which("node")
UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()

FNS = ["  function esc(s){", "  function _lsWhenSay(t0){", "  function _runSpanSay(t0, t1){", "  function _runSeal(sm){",
       "  function _runSealGapsSay(rs){", "  function _lastSessionRow(list){", "  function _lastSessionNoFilmSay(list){",
       "  function hdLastSession(){", "  async function hdShelf(){", "  function thPickEntrySession(strict){",
       "  window._shelfLastSession = async function(){", "  async function thOpen(){"]


def _cut(sig):
    """The one declaration that starts at sig, through its matching brace. -> str"""
    if UI.count(sig) != 1:
        raise AssertionError("%r occurs %d times - this law cannot see its subject" % (sig, UI.count(sig)))
    i = UI.index(sig)
    b = UI.index("{", i)
    depth = 0
    for j in range(b, len(UI)):
        if UI[j] == "{":
            depth += 1
        elif UI[j] == "}":
            depth -= 1
            if depth == 0:
                return UI[i:j + 1] + (";" if sig.strip().startswith("window.") else "")
    raise AssertionError("%r never closed - harness fault, not a pass" % sig)


HARNESS = r"""
import { readFileSync } from 'node:fs';
const CFG = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const out = [];
for (const C of CFG.cases) {
  const LOG = [], ELS = {};
  const _el = (id) => ({ id: id, hidden: true, innerHTML: '', textContent: '' });
  const env = {
    LOG: LOG,
    $: (id) => ELS[id] || (ELS[id] = _el(id)),
    document: { getElementById: (id) => env.$(id),
                body: { getAttribute: (k) => (k === 'data-state' && C.onAir) ? 'on' : null,
                        classList: { add: () => {}, remove: () => {}, contains: () => false } } },
    window: { _sessionsJson: async () => ({ sessions: C.rows }) },
    TH: { sessions: C.rows },
    toast: (m) => LOG.push('toast:' + m),
    thLoadSession: (n) => LOG.push('load:' + n),
    _sceneFingerprint: () => '', _findsStrip: () => '', _hdHistoryRender: () => {}, _hdKpiRender: () => {},
    // the Theatre button's open: its /api/sessions wait answers these rows; the stage helpers do nothing
    thSessionsWait: async () => ({ sessions: C.rows }),
    thArtInit: () => {}, thRibbon: () => {}, thCoachOnce: () => {}, thLit: () => {}, thApplyCardPref: () => {},
  };
  const run = new Function('env', 'with (env) { var HD_ALL = [], HD_TOTAL = null;\n' + CFG.fns + '\n'
    + 'return (async function(){ await hdShelf(); var box = $("hd-lastsession"), row = $("hd-ls-row").innerHTML;'
    + ' var m = /<b>session (\\d+)<\\/b>/.exec(row); await window._shelfLastSession();'
    + ' var shelfLog = LOG.splice(0, LOG.length); TH.open = false; TH.sessions = [];'
    + ' env.thLoadSession = function(n){ LOG.push("load:" + n); }; await thOpen();'
    + ' return { digest: box.hidden ? null : (m ? +m[1] : "unparsed"), row: row, log: shelfLog,'
    + ' theatre: LOG.slice(), stage: $("th-caption").textContent, line: $("th-sess").textContent }; })(); }');
  out.push(await run(env));
}
process.stdout.write(JSON.stringify(out));
"""

T = 1793189802000   # 2026-10-28, his afternoon


def _run(**k):
    r = {"t0": T, "t1": T + 600000, "reads": 6, "frames": 0, "footageN": 0, "named": 0, "kaiMissed": None}
    r.update(k)
    r.setdefault("sessionId", "s_%d" % r["n"])
    return r


CASES = {
    # his journal today: a stub head, three runs since the last seal, then the sealed one
    "three_runs_since_the_seal": {"rows": [
        {"n": 1, "stub": True, "sessionId": "s_1"},
        _run(n=2, reads=40, frames=12, footageN=2274, named=3),
        _run(n=3, reads=4, frames=2, footageN=38, named=1),
        _run(n=4, reads=120, frames=40, footageN=2539, named=65),
        {"n": 5, "stub": True, "sessionId": "s_5"},
        _run(n=6, reads=14, frames=6, footageN=3280, kaiMissed=0)]},
    # GrokBot's 28 vs 48: the newest run had stills but no film; an older one had film and a find
    "grokbots_28_vs_48": {"rows": [
        {"n": 27, "stub": True, "sessionId": "s_27"},
        _run(n=28, reads=526, frames=9, footageN=0, named=30, kaiMissed=239, tallies=106),
        _run(n=48, reads=7, frames=19, footageN=19, named=1, kaiMissed=8)]},
    # ON AIR: the newest row is the run being recorded, and the theatre is PAST only
    "on_air": {"onAir": True, "rows": [
        _run(n=1, reads=9, frames=5, footageN=50, named=2),
        _run(n=2, reads=60, frames=20, footageN=900, named=4),
        _run(n=3, reads=50, frames=18, footageN=800, named=2, kaiMissed=5)]},
    # the suite's fixture reel is never his last session (v3083)
    "a_fixture_on_top": {"rows": [
        _run(n=1, fixture=True, reads=80, frames=30, footageN=600, named=9, kaiMissed=0),
        _run(n=2, reads=12, frames=4, footageN=30, named=1)]},
    # the last session has nothing to replay, an older reel does
    "the_last_one_has_no_film": {"rows": [
        _run(n=1, reads=5, frames=0, footageN=0),
        _run(n=2, reads=20, frames=4, footageN=40, named=1, kaiMissed=3)]},
    # nothing he played at all
    "only_a_stub": {"rows": [{"n": 1, "stub": True, "sessionId": "s_1"}]},
    # REG-2868 (GrokBot #230 6477559571) - a shadow-reader recording keeps the body OFF; the server says session 1 has not ended
    "recording_body_off": {"rows": [
        _run(n=1, ended=False, reads=9, frames=5, footageN=50, named=2),
        _run(n=2, ended=True, reads=60, frames=20, footageN=900, named=4)]},
    # the same run once it sealed: it IS the last session
    "sealed_body_off": {"rows": [
        _run(n=1, ended=True, reads=9, frames=5, footageN=50, named=2),
        _run(n=2, ended=True, reads=60, frames=20, footageN=900, named=4)]},
    # no session id: the server cannot tell - shown, never skipped silently, and said
    "ended_unknown": {"rows": [
        _run(n=1, ended=None, reads=9, frames=5, footageN=50, named=2),
        _run(n=2, ended=True, reads=60, frames=20, footageN=900, named=4)]},
}


def _drive():
    if NODE is None:
        raise AssertionError("node is not on this machine - this law does not skip")
    names = sorted(CASES)
    d = tempfile.mkdtemp(prefix="last_session_")
    try:
        h, c = os.path.join(d, "h.mjs"), os.path.join(d, "cfg.json")
        io.open(h, "w", encoding="utf-8").write(HARNESS)
        io.open(c, "w", encoding="utf-8").write(json.dumps({
            "fns": "\n".join(_cut(s) for s in FNS),
            "cases": [CASES[n] for n in names]}))
        r = subprocess.run([NODE, h, c], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=60, env=dict(os.environ, TZ="UTC"))
    finally:
        shutil.rmtree(d, True)
    if r.returncode != 0:
        raise AssertionError("node failed: %s" % r.stderr[-900:])
    return dict(zip(names, json.loads(r.stdout)))


class TheLastSessionIsOneRun(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.got = _drive()

    def loaded(self, name):
        return [int(x[5:]) for x in self.got[name]["log"] if x.startswith("load:")]

    def played(self, name):
        return [int(x[5:]) for x in self.got[name]["theatre"] if x.startswith("load:")]

    def same(self, name, n):
        g = self.got[name]
        self.assertEqual(g["digest"], n, "%s: the LAST SESSION digest named %r, not session %d: %r" % (name, g["digest"], n, g))
        self.assertEqual(self.loaded(name), [n], "%s: the Shelf's ▶ Last session loaded %r, not session %d: %r"
                         % (name, self.loaded(name), n, g["log"]))
        self.assertEqual(self.played(name), [n], "%s: the Theatre button's 'replay last session' played %r, not session %d"
                         % (name, self.played(name), n))

    def test_runs_played_after_the_last_seal_are_the_last_session(self):
        self.same("three_runs_since_the_seal", 2)
        self.assertIn("◌ OPEN", self.got["three_runs_since_the_seal"]["row"],
                      "an unsealed last session must say it is open, never clean (REG-2102)")

    def test_grokbots_28_and_48_are_one_session(self):
        self.same("grokbots_28_vs_48", 28)

    def test_on_air_the_run_being_recorded_is_not_the_last_session(self):
        self.same("on_air", 2)

    def test_a_fixture_is_never_his_last_session(self):
        self.same("a_fixture_on_top", 2)

    def test_a_last_session_with_nothing_to_replay_says_so(self):
        g = self.got["the_last_one_has_no_film"]
        self.assertEqual(g["digest"], 1, g)
        self.assertEqual(self.loaded("the_last_one_has_no_film"), [], "another reel played under 'Last session': %r" % g["log"])
        say = "the last session (session 1) has no film to replay - older reels are on the shelf"
        self.assertIn("toast:" + say, g["log"])
        self.assertEqual(self.played("the_last_one_has_no_film"), [],
                         "the Theatre button played another reel under 'replay last session': %r" % g["theatre"])
        self.assertEqual(g["stage"], "🎞 " + say, "the Theatre's stage does not say which run has no film")
        self.assertEqual(g["line"], "session 1 · no film to replay", "the session line names another reel")

    def test_no_run_is_no_last_session(self):
        g = self.got["only_a_stub"]
        self.assertIsNone(g["digest"], "a stub was shown as the last session: %r" % g)
        self.assertEqual(self.loaded("only_a_stub"), [])
        self.assertIn("toast:no session has film yet", g["log"])
        self.assertEqual(self.played("only_a_stub"), [], "the Theatre played a stub (the old fallback to session 1)")
        self.assertEqual(g["stage"], "🎞 no session has film yet")

    def test_a_run_still_being_recorded_is_not_the_last_session_whatever_the_body_says(self):
        """REG-2868 - body OFF (a shadow-reader recording), the server says session 1 has not ended: all three doors skip it."""
        self.same("recording_body_off", 2)

    def test_a_sealed_session_1_is_the_last_session(self):
        self.same("sealed_body_off", 1)
        self.assertNotIn("ended UNKNOWN", self.got["sealed_body_off"]["row"])

    def test_an_unknown_end_is_shown_and_said_never_skipped_silently(self):
        self.same("ended_unknown", 1)
        self.assertIn("ended UNKNOWN", self.got["ended_unknown"]["row"], "a run nobody can say has ended reads as over")

    def test_the_theatre_plays_the_last_session_not_the_newest_with_a_find(self):
        """REG-2811 - the substance tiers would play session 48 (film and a find) over session 28 (stills, no film)."""
        self.assertEqual(self.played("grokbots_28_vs_48"), [28])
        self.assertEqual(self.played("three_runs_since_the_seal"), [2])


class TheServerSaysWhetherARunEnded(unittest.TestCase):
    """REG-2868 - control_app._session_ended, the field every /api/sessions row carries (ended, endedWhy)."""

    @classmethod
    def setUpClass(cls):
        import fixture_tmp as _fx
        _fx.contain()
        import control_app as ca
        cls.ca = ca

    def setUp(self):
        self.hist = tempfile.mkdtemp(prefix="last_session_hist_")
        self.addCleanup(shutil.rmtree, self.hist, True)

    def test_each_way_a_run_is_over_and_the_one_way_it_is_not(self):
        e = self.ca._session_ended
        rec = [{"sessionId": "s_100_1", "ts": 1}, {"sessionId": "s_100_1", "ts": 2}]
        self.assertEqual(e(rec, 1, self.hist)[0], False, "session 1 with an id, no end and no reel was called over")
        self.assertIn("still being recorded", e(rec, 1, self.hist)[1])
        self.assertIs(e(rec + [{"sessionId": "s_100_1", "sessionEnd": True}], 1, self.hist)[0], True)
        self.assertIs(e(rec, 2, self.hist)[0], True, "a run a newer one followed was called still being recorded")
        os.makedirs(os.path.join(self.hist, "reel_s_100_1"))
        self.assertEqual(e(rec, 1, self.hist), (True, "its reel is sealed"))
        self.assertEqual(e([{"ts": 1}], 1, self.hist)[0], None, "a run with no id was guessed")

    def test_both_row_paths_carry_it(self):
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.assertEqual(src.count('_hit["ended"], _hit["endedWhy"] = _session_ended(sess, i, HIST_DIR)'), 1,
                         "a memoised row keeps the ended it was stored with, though its n moved")
        self.assertEqual(src.count('_row["ended"], _row["endedWhy"] = _session_ended(sess, i, HIST_DIR)'), 1,
                         "a freshly built row carries no ended")


# ── REG-2812 (#86, the REG-2790/2811 sweep) - the session comparison's default "last two real runs" ─────────────────────
CMP_FNS = ["  function esc(s){", "  function _cmpList(){", "  function _cmpFind(n){", "  function _cmpOptions(sel){",
           "  window._cmpOpen = function(){"]
CMP_HARNESS = r"""
import { readFileSync } from 'node:fs';
const CFG = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const ELS = {};
const env = {
  TH: { sessions: CFG.rows }, HD_ALL: [],
  document: { getElementById: (id) => ELS[id] || (ELS[id] = { id: id, hidden: true, innerHTML: '', scrollTop: 0 }) },
  window: {}, _cmpRender: () => {},
};
const f = new Function('env', 'with (env) {\n' + CFG.line + '\n' + CFG.fns + '\nwindow._cmpOpen();\n'
  + 'return { b: CMP.b, a: CMP.a, list: _cmpList().map(function(s){ return s.n; }),'
  + ' options: (document.getElementById("th-compare-ov").innerHTML.match(/<option value="\\d+"/g) || []).length }; }');
process.stdout.write(JSON.stringify(f(env)));
"""


def _cut_cmp(sig):
    if UI.count(sig) != 1:
        raise AssertionError("%r occurs %d times - this law cannot see its subject" % (sig, UI.count(sig)))
    i = UI.index(sig)
    b = UI.index("{", i)
    depth = 0
    for j in range(b, len(UI)):
        if UI[j] == "{":
            depth += 1
        elif UI[j] == "}":
            depth -= 1
            if depth == 0:
                return UI[i:j + 1] + (";" if sig.strip().startswith("window.") else "")
    raise AssertionError("%r never closed - harness fault, not a pass" % sig)


def _compare(rows):
    if NODE is None:
        raise AssertionError("node is not on this machine - this law does not skip")
    line = "  var CMP = { a: null, b: null };"
    if UI.count(line) != 1:
        raise AssertionError("the comparison's CMP state moved - re-point this law")
    d = tempfile.mkdtemp(prefix="last_session_cmp_")
    try:
        h, c = os.path.join(d, "h.mjs"), os.path.join(d, "cfg.json")
        io.open(h, "w", encoding="utf-8").write(CMP_HARNESS)
        io.open(c, "w", encoding="utf-8").write(json.dumps({"line": line, "fns": "\n".join(_cut_cmp(x) for x in CMP_FNS),
                                                            "rows": rows}))
        r = subprocess.run([NODE, h, c], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
                           env=dict(os.environ, TZ="UTC"))
    finally:
        shutil.rmtree(d, True)
    if r.returncode != 0:
        raise AssertionError("node failed: %s" % r.stderr[-900:])
    return json.loads(r.stdout)


class TheComparisonComparesHisRuns(unittest.TestCase):
    """REG-2812 - a suite fixture newer than his runs is not the comparison's default, nor one of its options."""

    def test_a_newer_fixture_is_not_a_default(self):
        got = _compare([_run(n=1, fixture=True, t0=T + 7200000, t1=T + 7800000, reads=80, frames=30, footageN=600),
                        _run(n=2, t0=T, t1=T + 600000, reads=12, frames=4, footageN=30, named=1),
                        _run(n=3, t0=T - 86400000, t1=T - 86000000, reads=9, frames=3, footageN=20),
                        {"n": 4, "stub": True, "sessionId": "s_4", "t0": T + 9000000}])
        self.assertEqual((got["b"], got["a"]), (2, 3), "the comparison defaulted to a suite fixture or a stub: %r" % got)
        self.assertEqual(got["list"], [2, 3], "his runs, newest first, are not what the comparison lists: %r" % got)
        self.assertEqual(got["options"], 4, "each picker should offer exactly his two runs: %r" % got)


RED_PROOF = [
    {"why": "REG-2868 - session 1 with an id and no end is called over, so the page cannot skip it",
     "file": "tv/control_app.py",
     "find": "    return False, \"no session end and no sealed reel yet - it is still being recorded\"\n",
     "replace": "    return True, \"no session end and no sealed reel yet - it is still being recorded\"\n",
     "matches": 1},
    {"why": "REG-2868 - a memoised row keeps the ended it was stored with after a newer run moved its n",
     "file": "tv/control_app.py",
     "find": "                    _hit[\"ended\"], _hit[\"endedWhy\"] = _session_ended(sess, i, HIST_DIR)   # REG-2868 - n moved, so ask again\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2868 - a run still being recorded is named the last session while the body is off (a shadow recording)",
     "file": "tv/control_ui.html",
     "find": "      if (s.ended === false) continue;   /* REG-2868 - still being recorded, whatever the body says */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2868 - a run whose end is unknown is skipped silently (an older run named last for no visible reason)",
     "file": "tv/control_ui.html",
     "find": "      if (s.ended === false) continue;   /* REG-2868 - still being recorded, whatever the body says */\n",
     "replace": "      if (s.ended !== true) continue;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2868 - the digest stops saying a run's end is unknown",
     "file": "tv/control_ui.html",
     "find": "      if (t.ended !== true && t.ended !== false) parts.push('ended UNKNOWN');",
     "replace": "      if (false) parts.push('ended UNKNOWN');",
     "matches": 1, "needs": "node"},
    {"why": "REG-2790 - the digest names the newest SEALED reel again (session 6 over three newer runs)",
     "file": "tv/control_ui.html",
     "find": "      var t = _lastSessionRow(HD_ALL);   /* REG-2790 - the run the Shelf's ▶ Last session opens too */\n",
     "replace": "      var t = (HD_ALL || []).find(function(s){ return s.kaiMissed != null; });\n"
                "      if (!t && (HD_ALL || []).length > 1) t = HD_ALL[1];\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2790/2811 - the entry pick prefers the newest reel with film and a find again (plays 48 under a digest saying 28)",
     "file": "tv/control_ui.html",
     "find": "    var last = _lastSessionRow(TH.sessions || []);\n    return (last && ((last.frames || 0) > 0",
     "replace": "    var last = (TH.sessions || []).filter(function(s){ return !s.stub && (s.footageN || 0) > 10 && (s.named || 0) > 0; })[0]"
                " || _lastSessionRow(TH.sessions || []);\n    return (last && ((last.frames || 0) > 0",
     "matches": 1, "needs": "node"},
    {"why": "REG-2790 - ON AIR, the run being recorded is called the last session",
     "file": "tv/control_ui.html",
     "find": "      if (onAir && s.n === 1) continue;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2790 - a suite fixture is named as his last session",
     "file": "tv/control_ui.html",
     "find": "      if (!s || s.stub || s.fixture) continue;\n",
     "replace": "      if (!s || s.stub) continue;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2790 - a stub is named as the last session on the shelf's side",
     "file": "tv/control_ui.html",
     "find": "      if (!s || s.stub || s.fixture) continue;\n",
     "replace": "      if (!s || s.fixture) continue;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2790/2811 - a last session with no film is reported as 'no session has film' over a shelf of film",
     "file": "tv/control_ui.html",
     "find": "    return (ls && film) ? ('the last session (session ' + ls.n",
     "replace": "    return (false) ? ('the last session (session ' + ls.n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2811 - the Theatre button falls back to session 1 again when the last session has nothing to play",
     "file": "tv/control_ui.html",
     "find": "    return (last && ((last.frames || 0) > 0 || (last.footageN || 0) > 0)) ? (last.n || 0) : 0;\n  }\n",
     "replace": "    return (last && ((last.frames || 0) > 0 || (last.footageN || 0) > 0)) ? (last.n || 0) : (strict ? 0 : 1);\n  }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2811 - the Theatre button alone goes back to the newest reel with film and a find",
     "file": "tv/control_ui.html",
     "find": "    var pick = thPickEntrySession();\n    if (!pick) {\n",
     "replace": "    var pick = ((TH.sessions || []).filter(function(s){ return !s.stub && (s.footageN || 0) > 10 && (s.named || 0) > 0; })[0]"
                " || {}).n || thPickEntrySession();\n    if (!pick) {\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2812 - the comparison's runs take the suite's fixture reels again (a newer fixture is its default B)",
     "file": "tv/control_ui.html",
     "find": "    return (list || []).filter(function(s){ return s && !s.stub && !s.fixture; })",
     "replace": "    return (list || []).filter(function(s){ return s && !s.stub; })",
     "matches": 1, "needs": "node"},
    {"why": "REG-2811 - the session line keeps naming whatever reel this page showed before (REG-2135's class)",
     "file": "tv/control_ui.html",
     "find": "            if (_ns) _ns.textContent = _lsr ? 'session ' + _lsr.n + ' · no film to replay' : 'no session to replay'; } catch (e) {}\n",
     "replace": "            } catch (e) {}\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2811 - the Theatre's stage is silent about a last session with nothing to play",
     "file": "tv/control_ui.html",
     "find": "      try { $('th-caption').textContent = '🎞 ' + _lastSessionNoFilmSay(TH.sessions); } catch (e) {}\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
