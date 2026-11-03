# -*- coding: utf-8 -*-
"""v3849 item 10 - A SHADOW SHELF SAYS THE RUN IN PLAIN WORDS, AND PLAY ONLY STEPS FRAMES THE OWNER ALREADY SERVED.

Playtime is the short gaps between captured moments. AFK time is the long ones. One moment is not a span, so both
stay unknown rather than 0. Chronicles found are the distinct names on a chronicle-panel row (scene chronicle).
Items farmed are the distinct names whose intent is farmed. An empty name list says no item was named on this run.
PLAY walks the last N reels in the record, oldest first, and only a key frame whose body is base64: the jpeg the
owner's digest already served. It does not fetch, and it does not open this PC's theatre.

The numbers come from shadow_sessions.digest on a fixture journal. The words and the player are the page functions
cut out of control_ui.html and run in node, program on stdin. RED_PROOF below.
"""
import base64
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
import shadow_sessions as SS  # noqa: E402

NODE = shutil.which("node")
UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
PY = io.open(os.path.join(HERE, "shadow_sessions.py"), encoding="utf-8").read()

FNS = ["  function esc(s){", "  function _lsWhenSay(t0){", "  function _runSpanSay(t0, t1){",
       "  function _shadowSessionRow(s, ix){", "  function _shadowSessionsHead(owner){",
       "  function _shadowSessionsHtml(d){", "  function _shadowSessionsClose(){",
       "  function _shadowSessionsSpeed(){", "  function _shadowSessionsPlayStop(){",
       "  function _shadowSessionsPlayTick(){", "  function _shadowSessionsPlay(ix){"]
LINES = ["  var _SSV_B64 = ", "  var _SSV_SPEEDS = ", "  var _ssvGen = 0;"]

T0 = 1792000000000
MANY = "s_1792000000000_1"
ONE = "s_1793000000000_2"
A = base64.b64encode(b"\xff\xd8\xffA-frame").decode("ascii")
B = base64.b64encode(b"\xff\xd8\xffB-frame").decode("ascii")


def _cut(src, sig):
    if src.count(sig) != 1:
        raise AssertionError("%r occurs %d times" % (sig, src.count(sig)))
    i = src.index(sig)
    b = src.index("{", i)
    depth = 0
    for j in range(b, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
    raise AssertionError("%r never closed" % sig)


def _line(src, start):
    if src.count(start) != 1:
        raise AssertionError("%r occurs %d times" % (start, src.count(start)))
    i = src.index(start)
    return src[i:src.index("\n", i)]


def _rows():
    return [
        {"ts": T0, "captureTs": T0, "sessionId": MANY, "lane": "deep", "scene": "stash", "frameId": "1_%d" % T0},
        {"ts": T0 + 30000, "captureTs": T0 + 30000, "sessionId": MANY, "lane": "deep", "scene": "inventory",
         "frameId": "2_%d" % (T0 + 30000), "names": ["Harlequin Crest", "Eligible for Chronicle"]},
        {"ts": T0 + 230000, "captureTs": T0 + 230000, "sessionId": MANY, "lane": "deep", "scene": "inventory",
         "intent": "farmed", "frameId": "3_%d" % (T0 + 230000), "names": ["Ber Rune"]},
        {"ts": T0 + 10000000, "captureTs": T0 + 10000000, "sessionId": ONE, "lane": "deep", "scene": "stash",
         "frameId": "4_%d" % (T0 + 10000000)},
    ]


HARNESS = r"""
const CFG = JSON.parse(process.env.SSV_CFG);
const CALLS = [];
const TIMERS = [];
let tid = 1;
const REG = {};
function El(id){ this.id = id; this.innerHTML = ''; this.textContent = ''; this.hidden = false; }
const stage = new El('ssv-stage'), playBtn = new El('ssv-play'), speedBtn = new El('ssv-speed');
REG['ssv-stage'] = stage; REG['ssv-play'] = playBtn; REG['ssv-speed'] = speedBtn;
const env = {
  window: {},
  document: { getElementById: (id) => REG[id] || null, body: { classList: { contains: () => false } } },
  setTimeout: (fn, ms) => { const id = tid++; TIMERS.push({ id, fn, ms }); return id; },
  clearTimeout: (id) => { const i = TIMERS.findIndex((t) => t.id === id); if (i >= 0) TIMERS.splice(i, 1); },
  fetch: (url) => { CALLS.push(String(url)); return Promise.resolve({ json: () => Promise.resolve({}) }); },
};
const F = new Function('env', 'with (env) {\n' + CFG.code + '\nreturn { html: _shadowSessionsHtml, play: _shadowSessionsPlay,'
  + ' speed: _shadowSessionsSpeed, close: _shadowSessionsClose, tick: _shadowSessionsPlayTick }; }')(env);
const html = CFG.cases.map((c) => F.html(c));
const playHtml = F.html(CFG.play);
const reels = (env.window._ssvReels || []).slice();
const started = F.play();
const first = { shown: env.window._ssvShown, wait: env.window._ssvWait, on: !!(env.window._ssvPlay && env.window._ssvPlay.on) };
const speed2 = F.speed();
if (TIMERS.length) TIMERS.pop().fn();
const second = { shown: env.window._ssvShown, wait: env.window._ssvWait };
const speeds = [speed2, F.speed(), F.speed(), F.speed()];
F.close();
const afterClose = { on: !!(env.window._ssvPlay && env.window._ssvPlay.on), timers: TIMERS.length };
F.html(CFG.bad);
const bad = { played: F.play(), shown: env.window._ssvShown, stage: stage.textContent, reels: (env.window._ssvReels || []).slice() };
F.html(CFG.one);
const one = { html: F.html(CFG.one), n: env.window._ssvReelN, label: F.html(CFG.one) };
process.stdout.write(JSON.stringify({ html, playHtml, reels, started, first, second, speeds, afterClose, bad, one, calls: CALLS }));
"""


def _code():
    return "\n".join([_line(UI, x) for x in LINES] + [_cut(UI, x) for x in FNS])


def _drive(cases, play, bad, one):
    if NODE is None:
        raise AssertionError("node is not on this machine - this law does not skip")
    cfg = json.dumps({"code": _code(), "cases": cases, "play": play, "bad": bad, "one": one})
    r = subprocess.run([NODE, "-"], input=HARNESS, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=60, env=dict(os.environ, SSV_CFG=cfg, TZ="UTC", LANG="en_US.UTF-8"))
    if r.returncode != 0:
        raise AssertionError("node failed: %s" % (r.stderr or r.stdout)[-900:])
    return json.loads(r.stdout)


class TheDigestMeasuresTheFourFacts(unittest.TestCase):

    def setUp(self):
        import control_app as ca
        self.is_read = ca._is_a_live_read
        self.d = tempfile.mkdtemp(prefix="shadow_plain_")
        self.addCleanup(shutil.rmtree, self.d, True)

    def test_play_afk_chronicles_and_farmed_come_from_the_rows(self):
        o = SS.digest(_rows(), self.d, self.is_read, T0 + 20000000, make=None)
        by = {s["sessionId"]: s for s in o["sessions"]}
        many = by[MANY]
        self.assertEqual((many["playMs"], many["afkMs"]), (30000, 200000), many)
        # v3859 - two items picked up, one tooltip with the green 'Eligible for Chronicle' line (session_route)
        self.assertEqual(many["chroniclesFound"], 1, many)
        self.assertEqual(many["itemsFarmed"], 2, many)
        one = by[ONE]
        self.assertIsNone(one["playMs"], "one captured moment was called a playtime of %r" % one["playMs"])
        self.assertIsNone(one["afkMs"], "one captured moment was called AFK of %r" % one["afkMs"])
        self.assertEqual((one["chroniclesFound"], one["itemsFarmed"]), (0, 0))


class ThePageSaysThemAndPlaysOnlyServedFrames(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import control_app as ca
        d = tempfile.mkdtemp(prefix="shadow_plain_node_")
        try:
            o = SS.digest(_rows(), d, ca._is_a_live_read, T0 + 20000000, make=None)
        finally:
            shutil.rmtree(d, True)
        by = {s["sessionId"]: s for s in o["sessions"]}
        words = {"ok": True, "owner": "Wife PC", "ago": "1 min ago", "source": "worker",
                 "sessions": [by[MANY], by[ONE], dict(by[ONE], names=None, sessionId="s_old")]}
        bare = {"ok": True, "owner": "Wife PC", "ago": "1 min ago", "source": "worker",
                "sessions": [{"sessionId": "s_bare", "t0": T0, "t1": T0 + 1000, "reads": 1, "names": ["Shako"],
                              "namesMore": 0, "frames": [], "why": None}]}
        play = {"ok": True, "owner": "Wife PC", "ago": "1 min ago", "source": "worker", "sessions": [
            {"sessionId": "s_new", "t0": T0 + 5000, "t1": T0 + 9000, "reads": 2, "names": [], "namesMore": 0,
             "frames": [{"id": "b", "jpg": B}, {"id": "bad", "jpg": "javascript:alert(1)"}], "why": None},
            {"sessionId": "s_old", "t0": T0, "t1": T0 + 1000, "reads": 1, "names": ["Shako"], "namesMore": 0,
             "frames": [{"id": "a", "jpg": A}], "why": None}]}
        bad = {"ok": True, "owner": "Wife PC", "ago": "1 min ago", "source": "worker", "sessions": [
            {"sessionId": "s_x", "t0": T0, "t1": T0 + 1, "reads": 0, "names": [], "namesMore": 0,
             "frames": [{"id": "z", "jpg": "not base64 !!!"}], "why": None}]}
        one = {"ok": True, "owner": "Wife PC", "ago": "1 min ago", "source": "worker", "sessions": [
            {"sessionId": "s_only", "t0": T0, "t1": T0 + 1, "reads": 1, "names": [], "namesMore": 0,
             "frames": [{"id": "a", "jpg": A}], "why": None}]}
        cls.got = _drive([words, bare], play, bad, one)
        cls.words, cls.bare = cls.got["html"]

    def test_the_digest_numbers_are_the_words_on_the_row(self):
        self.assertIn("playtime 0m30s · AFK time 3m20s · 1 chronicle found · 2 items farmed", self.words)
        self.assertIn("playtime UNKNOWN · AFK time UNKNOWN · 0 chronicles found · 0 items farmed", self.words)
        self.assertIn("no item was named on this run", self.words)
        self.assertNotIn("no name read", self.words)
        self.assertIn("names UNKNOWN", self.words)
        self.assertIn("playtime UNKNOWN · AFK time UNKNOWN · chronicles found UNKNOWN · items farmed UNKNOWN", self.bare)

    def test_play_steps_only_the_frames_the_record_served(self):
        g = self.got
        self.assertIn("▶ PLAY the last 2 reels", g["playHtml"])
        self.assertIn('onclick="window._shadowSessionsPlay&&window._shadowSessionsPlay()"', g["playHtml"])
        self.assertEqual(g["reels"], ["data:image/jpeg;base64," + A, "data:image/jpeg;base64," + B], g["reels"])
        self.assertNotIn("javascript:", "".join(g["reels"]))
        self.assertTrue(g["started"])
        self.assertEqual(g["first"]["shown"], "data:image/jpeg;base64," + A)
        self.assertEqual(g["first"]["wait"], 800, "1× did not wait the theatre's base step: %r" % g["first"])
        self.assertEqual(g["second"]["shown"], "data:image/jpeg;base64," + B)
        self.assertEqual(g["second"]["wait"], 400, "2× did not halve the step: %r" % g["second"])
        self.assertEqual(g["speeds"], [2, 4, 8, 1], g["speeds"])
        self.assertEqual(g["calls"], [], "play fetched %r" % g["calls"])
        self.assertFalse(g["afterClose"]["on"], "close left play running")
        self.assertEqual(g["afterClose"]["timers"], 0)
        self.assertFalse(g["bad"]["played"])
        self.assertIsNone(g["bad"]["shown"])
        self.assertEqual(g["bad"]["stage"], "no served frame to play")
        self.assertEqual(g["bad"]["reels"], [])
        self.assertEqual(g["one"]["n"], 1)
        self.assertIn("▶ PLAY the last 1 reel", g["one"]["html"])
        play_src = _cut(UI, "  function _shadowSessionsPlay(ix){")
        for banned in ("fetch(", "/hist", "thOpen"):
            self.assertNotIn(banned, play_src, "play reaches %s" % banned)


class TheProofsNameOnePlace(unittest.TestCase):

    def test_each_find_matches_once(self):
        for proof in RED_PROOF:
            path = proof["file"]
            src = UI if path.endswith("control_ui.html") else PY
            self.assertEqual(src.count(proof["find"]), proof["matches"], proof["why"])


RED_PROOF = [
    {"why": "a frame the owner did not serve is played",
     "file": "tv/control_ui.html",
     "find": "          if (b && _SSV_B64.test(b)) own.push('data:image/jpeg;base64,' + b);\n",
     "replace": "          if (b) own.push(b);\n",
     "matches": 1, "needs": "node"},
    {"why": "an unnamed run says 'no name read' again",
     "file": "tv/control_ui.html",
     "find": "'no item was named on this run'",
     "replace": "'no name read'",
     "matches": 1, "needs": "node"},
    {"why": "fast-forward no longer leaves 1×",
     "file": "tv/control_ui.html",
     "find": "  var _SSV_SPEEDS = [1, 2, 4, 8];\n",
     "replace": "  var _SSV_SPEEDS = [1];\n",
     "matches": 1, "needs": "node"},
    {"why": "a chronicle find is counted as nothing",
     "file": "tv/shadow_sessions.py",
     "find": "         \"chroniclesFound\": len(rt[\"chronicle\"]) if rt[\"chronicle\"] is not None else None,\n",
     "replace": "         \"chroniclesFound\": 0,\n",
     "matches": 1},
    {"why": "one captured moment is reported as zero play and zero AFK",
     "file": "tv/shadow_sessions.py",
     "find": "    if len(ms) < 2:\n        return None, None\n",
     "replace": "    if False:\n        return None, None\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
