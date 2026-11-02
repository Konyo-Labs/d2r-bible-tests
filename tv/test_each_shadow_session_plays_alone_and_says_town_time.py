# -*- coding: utf-8 -*-
"""v3855 - EACH SHADOW SESSION PLAYS ALONE, AND SAYS ITS TOWN TIME, CHRONICLES AND STASH FROM ITS OWN READS.

Elad 2026-11-02: every ~1 h session in the shadow Sessions card gets its own PLAY (the same served-frame player as
'PLAY the last N'), and its row says in game / in town / out of town with percentages, the chronicles read, and what
was read in the stash (grouped, consumables out). Town is a read whose scene is town or whose area is an act town;
any other area or a gameplay/loot scene is out of town; a gap over AFK_GAP_MS is AFK and counts for neither, and
unchanged town reads for over TOWN_IDLE_MS (3 min) are AFK (idle in town); a brief stash/shop visit stays town. A session
with no placed read says UNKNOWN, never 0. RED_PROOF below.
"""
import base64
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
import test_a_shadow_shelf_says_playtime_and_plays_served_frames as BASE  # noqa: E402
import shadow_sessions as SS  # noqa: E402

T0 = 1792000000000
S1, S2 = "s_1792000000000_1", "s_1793000000000_2"
A = base64.b64encode(b"\xff\xd8\xffA").decode("ascii")
B = base64.b64encode(b"\xff\xd8\xffB").decode("ascii")


def _rows():
    def r(dt, **k):
        d = {"ts": T0 + dt, "captureTs": T0 + dt, "sessionId": S1, "lane": "deep", "frameId": "f%d" % dt}
        d.update(k)
        return d
    return [r(0, scene="town", area="Harrogath"), r(30000, scene="gameplay", area="Worldstone Keep Level 2"),
            r(90000, scene="loot", area="Worldstone Keep Level 2", names=["Shako"]),
            r(400000, scene="chronicle", names=["Stone of Jordan"]),
            r(410000, scene="stash", stashTab="personal", names=["Ber Rune", "Super Healing Potion"]),
            {"ts": T0 + 10000000, "captureTs": T0 + 10000000, "sessionId": S2, "lane": "deep", "frameId": "g"}]


HARNESS = r"""
const CFG = JSON.parse(process.env.SSV_CFG);
const TIMERS = []; let tid = 1; const REG = {};
function El(id){ this.id = id; this.innerHTML = ''; this.textContent = ''; }
['ssv-stage','ssv-play','ssv-speed'].forEach((k) => REG[k] = new El(k));
const env = { window: {}, document: { getElementById: (id) => REG[id] || null },
  setTimeout: (fn, ms) => { const id = tid++; TIMERS.push({ id, fn }); return id; },
  clearTimeout: (id) => { const i = TIMERS.findIndex((t) => t.id === id); if (i >= 0) TIMERS.splice(i, 1); } };
const F = new Function('env', 'with (env) {\n' + CFG.code + '\nreturn { html: _shadowSessionsHtml, play: _shadowSessionsPlay, stop: _shadowSessionsPlayStop }; }')(env);
const html = F.html(CFG.rec);
const shown = [];
F.play(1); shown.push(env.window._ssvShown); while (TIMERS.length) { TIMERS.pop().fn(); if (env.window._ssvPlay.on) shown.push(env.window._ssvShown); }
const one = shown.slice(); shown.length = 0;
F.stop(); F.play(); shown.push(env.window._ssvShown); while (TIMERS.length) { TIMERS.pop().fn(); if (env.window._ssvPlay.on) shown.push(env.window._ssvShown); }
process.stdout.write(JSON.stringify({ html, one, all: shown }));
"""


class TheDigestPlacesEachRead(unittest.TestCase):

    def test_town_field_chronicles_and_stash(self):
        import control_app as ca
        d = tempfile.mkdtemp(prefix="ssv_town_")
        self.addCleanup(shutil.rmtree, d, True)
        o = SS.digest(_rows(), d, ca._is_a_live_read, T0 + 20000000, make=None)
        by = {s["sessionId"]: s for s in o["sessions"]}
        s1 = by[S1]
        # 0->30s in town, 30->90s out of town; 90->400s is AFK; 400->410s opens on an unplaced chronicle read (over AFK_GAP_MS)
        self.assertEqual((s1["townMs"], s1["fieldMs"], s1["awayMs"]), (30000, 60000, 310000), s1)
        self.assertEqual(s1["chronicleNames"], ["Stone of Jordan"])
        flat = [n for g in s1["stashed"].values() for n, _ in g]
        self.assertIn("Ber Rune", flat)
        self.assertNotIn("Super Healing Potion", flat, "a potion was counted as stashed")
        self.assertEqual((by[S2]["townMs"], by[S2]["fieldMs"], by[S2]["awayMs"]), (None, None, None), "an unplaced session was given a time")


def _at(dt, **k):
    d = {"ts": T0 + dt, "captureTs": T0 + dt, "lane": "deep"}
    d.update(k)
    return d


def _split(rows, t0=None, t1=None):
    segs = SS.game_timeline(rows)
    t0 = T0 if t0 is None else t0
    t1 = max(r["ts"] for r in rows) if t1 is None else t1
    d = SS.session_split(segs, t0, t1)
    return d["townMs"], d["fieldMs"], d["awayMs"]


class IdleInTownIsAfk(unittest.TestCase):
    """Elad 2026-11-02: AFK is often hours standing in town with the game open while reads keep arriving, and it is
    AFK until it is not - one stretch can cross two ~1 h sessions of the same game."""

    def test_hours_of_unchanged_town_reads_are_afk(self):
        rows = [_at(i * 60000, scene="town", area="Harrogath") for i in range(121)]       # 2 h, one read a minute
        self.assertEqual(_split(rows), (0, 0, 120 * 60000))

    def test_a_40s_stash_visit_is_town(self):
        rows = [_at(0, scene="gameplay", area="Worldstone Keep Level 2"),
                _at(20000, scene="town", area="Harrogath"),
                _at(40000, scene="stash", area="Harrogath", names=["Ber Rune"]),
                _at(60000, scene="gameplay", area="Worldstone Keep Level 2"),
                _at(80000, scene="gameplay", area="Worldstone Keep Level 2")]
        self.assertEqual(_split(rows), (40000, 40000, 0))

    def test_changing_town_reads_stay_town(self):
        rows = [_at(i * 60000, scene="town", area="Harrogath", names=["Item %d" % i]) for i in range(6)]
        self.assertEqual(_split(rows), (300000, 0, 0))

    def test_a_2h_stretch_across_two_sessions_is_split_not_reset(self):
        H = 3600000
        rows = ([_at(i * 60000, sessionId=S1, scene="gameplay", area="Worldstone Keep Level 2") for i in range(0, 11)]
                + [_at(10 * 60000 + i * 60000, sessionId=S1 if i <= 50 else S2, scene="town", area="Harrogath")
                   for i in range(1, 121)]
                + [_at(130 * 60000 + 30000, sessionId=S2, scene="gameplay", area="Worldstone Keep Level 1")])
        segs = SS.game_timeline(rows)
        a = SS.session_split(segs, T0, T0 + 60 * 60000)                      # S1: 0..60 min
        b = SS.session_split(segs, T0 + 61 * 60000, T0 + 130 * 60000 + 30000)  # S2: 61..130.5 min
        self.assertEqual(SS.afk_stretches(segs), [(T0 + 11 * 60000, T0 + 130 * 60000)], "the stretch was cut")
        self.assertEqual(a["awayMs"], 49 * 60000, a)
        self.assertEqual(b["awayMs"], 69 * 60000, b)
        self.assertEqual((a["afkInto"], a["afkFrom"], b["afkFrom"], b["afkInto"]), (True, False, True, False))
        self.assertEqual((a["fieldMs"], b["fieldMs"], b["townMs"]), (11 * 60000, 0, 30000))
        # 119 min stretch = S1 49 + S2 69 + the 1 min between the two sessions' spans; never reset at the boundary
        self.assertEqual(a["awayMs"] + b["awayMs"] + 60000, 2 * H - 60000, "the 2 h stretch was reset at the boundary")


class TheRowPlaysOnlyItsOwnSession(unittest.TestCase):

    def test_row_play_and_words(self):
        rec = {"ok": True, "owner": "Dean", "ago": "1 min ago", "source": "cache", "sessions": [
            {"sessionId": "new", "t0": T0 + 5000, "t1": T0 + 9000, "reads": 2, "names": [], "namesMore": 0,
             "frames": [{"id": "b", "jpg": B}], "why": None, "townMs": 30000, "fieldMs": 90000, "awayMs": 120000, "afkFrom": True, "afkInto": False,
             "chronicleNames": ["Stone of Jordan"], "stashed": {"runes": [["Ber Rune", 2]]}},
            {"sessionId": "old", "t0": T0, "t1": T0 + 1000, "reads": 1, "names": [], "namesMore": 0,
             "frames": [{"id": "a", "jpg": A}], "why": None}]}
        cfg = json.dumps({"code": BASE._code(), "rec": rec})
        r = subprocess.run([BASE.NODE or "node", "-"], input=HARNESS, capture_output=True, text=True, timeout=60,
                           env=dict(os.environ, SSV_CFG=cfg, TZ="UTC"))
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        g = json.loads(r.stdout)
        h = g["html"]
        self.assertIn("▶ PLAY the last 2 reels", h)
        self.assertEqual(h.count("▶ PLAY this session"), 2)
        self.assertIn("window._shadowSessionsPlay(1)", h)
        self.assertIn("in game 2m00s · out of town 1m30s (38%) · in town 0m30s (13%) · AFK 2m00s (50%) (continues from previous session)", h)
        self.assertIn("in game UNKNOWN · out of town UNKNOWN · in town UNKNOWN · AFK UNKNOWN", h)
        self.assertIn("chronicles: Stone of Jordan", h)
        self.assertIn("stashed: Runes Ber Rune \u00d72", h)
        self.assertIn("stashed UNKNOWN", h)
        self.assertIn("chronicle names UNKNOWN", h)
        self.assertEqual(g["one"], ["data:image/jpeg;base64," + A], "row 1's PLAY played %r" % g["one"])
        self.assertEqual(g["all"], ["data:image/jpeg;base64," + A, "data:image/jpeg;base64," + B])


class TheProofsNameOnePlace(unittest.TestCase):

    def test_each_find_matches_once(self):
        for proof in RED_PROOF:
            src = open(os.path.join(HERE, "..", proof["file"]), encoding="utf-8").read()
            self.assertEqual(src.count(proof["find"]), proof["matches"], proof["why"])


RED_PROOF = [
    {"why": "hours of unchanged town reads count as town, not AFK",
     "file": "tv/shadow_sessions.py",
     "find": "        if pts[k][0] - pts[i][0] > TOWN_IDLE_MS:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "a 40s stash visit counts as AFK",
     "file": "tv/shadow_sessions.py",
     "find": "        if pts[k][0] - pts[i][0] > TOWN_IDLE_MS:\n",
     "replace": "        if pts[k][0] - pts[i][0] >= 0:\n",
     "matches": 1},
    {"why": "AFK is reset at a session boundary (each session's own reads only)",
     "file": "tv/shadow_sessions.py",
     "find": "        s.update(session_split(timeline, s[\"t0\"], s[\"t1\"]))\n",
     "replace": "        s.update(session_split(game_timeline(g), s[\"t0\"], s[\"t1\"]))\n",
     "matches": 1},
    {"why": "a stretch crossing a boundary is not said",
     "file": "tv/control_ui.html",
     "find": "sayDur(aMs) + pc(aMs) + (cont ? ' (' + cont + ')' : '')",
     "replace": "sayDur(aMs) + pc(aMs)",
     "matches": 1, "needs": "node"},
    {"why": "a row's PLAY plays every session",
     "file": "tv/control_ui.html",
     "find": "    if (typeof ix === 'number') window._ssvReels = ",
     "replace": "    if (false) window._ssvReels = ",
     "matches": 1, "needs": "node"},
    {"why": "an AFK gap is counted as town or field time",
     "file": "tv/shadow_sessions.py",
     "find": "    kinds = [(\"afk\" if b[0] - a[0] > AFK_GAP_MS else a[1]) for a, b in zip(pts, pts[1:])]\n",
     "replace": "    kinds = [a[1] for a, b in zip(pts, pts[1:])]\n",
     "matches": 1},
    {"why": "a session with no placed time says 0 instead of UNKNOWN",
     "file": "tv/shadow_sessions.py",
     "find": "    if not any(got.values()):\n        return none\n",
     "replace": "    if False:\n        return none\n",
     "matches": 1},
    {"why": "a town area is read as out of town",
     "file": "tv/shadow_sessions.py",
     "find": "    if sc == \"town\" or (area and area in TOWN_AREAS):\n",
     "replace": "    if sc == \"town\":\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
