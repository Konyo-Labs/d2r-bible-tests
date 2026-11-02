# -*- coding: utf-8 -*-
"""v3855 - A READ NAMES ITS CHARACTER AND ITS GAME, NEVER THE GAME PASSWORD (Elad 2026-11-02).

read_identity is the one console-wide extractor: game name and its farming series (Morph1..N, or the same name
re-entered), the login screen's character (name, class, level), the character panel, and the avatar's class.
Each console builds the ledger locally (shadow_sessions.digest runs on the owner's console); another console sees
only the published fields. Disagreeing signals are both kept and the attribution is UNKNOWN. RED_PROOF below.
"""
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
import read_identity as RI  # noqa: E402
import shadow_sessions as SS  # noqa: E402

T0 = 1792000000000
S1, S2 = "s_1792000000000_1", "s_1792003700000_2"
SECRET = "hunter2zz"


def _r(dt, sid=S1, **k):
    d = {"ts": T0 + dt, "captureTs": T0 + dt, "sessionId": sid, "lane": "deep", "frameId": "f%d" % dt}
    d.update(k)
    return d


def _journal():
    rows = [_r(0, scene="char-select", character="Blizzy", cls="Sorceress", level=92)]
    for i in range(1, 8):
        rows.append(_r(i * 60000, scene="gameplay", area="Durance of Hate Level 3",
                       text="Game name: Morph%d Password: %s" % (i, SECRET), gamePassword=SECRET))
    rows.append(_r(8 * 60000, scene="gameplay", area="Durance of Hate Level 3", intent="farmed", names=["Shako"]))
    rows.append(_r(3700000, sid=S2, scene="gameplay", area="Durance of Hate Level 3", chat="You joined game Morph8"))
    return rows


class TheExtractor(unittest.TestCase):

    def test_game_name_is_cut_before_the_password(self):
        self.assertEqual(RI.game_name_of_row({"text": "Game name: Morph3 Password: abc"}), "Morph3")
        self.assertEqual(RI.game_name_of_row({"chat": "You joined game Baal Run 12."}), "Baal Run 12")
        self.assertIsNone(RI.game_name_of_row({"gamePassword": "x", "scene": "gameplay"}))

    def test_series_and_runs(self):
        self.assertEqual(RI.say_games(["Morph1", "Morph2", "Morph7"]), "Morph1-Morph7 (3 games)")
        runs = RI.game_runs(_journal())
        self.assertEqual(sorted(runs["morph"]["sessions"]), sorted([S1, S2]))

    def test_conflict_is_unknown_with_both(self):
        a = RI.attribute_character([{"name": "Blizzy", "cls": "Sorceress", "level": 92, "source": "select-screen"},
                                    {"name": "Hammy", "cls": None, "level": None, "source": "char-panel"}])
        self.assertIsNone(a["name"])
        self.assertEqual(a["conflict"], ["Blizzy", "Hammy", "Sorceress"])

    def test_avatar_is_a_fallback_class(self):
        a = RI.attribute_character(RI.character_signals([{"scene": "gameplay", "avatarClass": "barbarian"}]))
        self.assertEqual((a["name"], a["cls"], a["sources"]), (None, "Barbarian", ["avatar"]))

    def test_a_find_is_attributed_to_who_played(self):
        f = [x for x in RI.attribute_finds(_journal()) if x["name"] == "Shako"]
        self.assertEqual(f[0]["character"]["name"], "Blizzy")

    def test_a_series_game_inherits_its_character(self):
        led = RI.identity_ledger(_journal())
        m8 = [r for r in led if r["gameName"] == "Morph8"][0]
        self.assertEqual((m8["character"], m8["source"]), ("Blizzy", "game-series"))


class TheDigestPublishesItAndNeverThePassword(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import control_app as ca
        d = tempfile.mkdtemp(prefix="ident_")
        try:
            cls.o = SS.digest(_journal(), d, ca._is_a_live_read, T0 + 9000000, make=None)
        finally:
            shutil.rmtree(d, True)
        cls.by = {s["sessionId"]: s for s in cls.o["sessions"]}

    def test_the_password_is_nowhere_in_the_record(self):
        blob = json.dumps(self.o)
        self.assertNotIn(SECRET, blob, "a game password reached the published record")
        self.assertNotIn("assword", blob)

    def test_rows_carry_character_and_games(self):
        s1 = self.by[S1]
        self.assertEqual(s1["gamesSay"], "Morph1-Morph7 (7 games)")
        self.assertEqual(s1["gameRunSessions"], 2)
        self.assertEqual((s1["character"]["name"], s1["character"]["cls"], s1["character"]["level"]), ("Blizzy", "Sorceress", 92))
        self.assertEqual(self.by[S2]["character"]["name"], "Blizzy", "a session with no login lost who played")
        self.assertEqual(self.o["identity"]["characters"], [{"name": "Blizzy", "cls": "Sorceress", "level": 92}])

    def test_the_row_says_it(self):
        rec = {"ok": True, "owner": "Dean", "ago": "1 min ago", "source": "cache",
               "sessions": [self.by[S1], dict(self.by[S2], character={"name": None, "cls": None, "level": None,
                            "sources": ["select-screen", "char-panel"], "conflict": ["Blizzy", "Hammy"]}, gamesSay=None)]}
        cfg = json.dumps({"code": BASE._code(), "rec": rec})
        js = ("const CFG = JSON.parse(process.env.SSV_CFG); const env = { window: {}, document: { getElementById: () => null },"
              " setTimeout: () => 0, clearTimeout: () => 0 };"
              " const F = new Function('env', 'with (env) {\\n' + CFG.code + '\\nreturn _shadowSessionsHtml; }')(env);"
              " process.stdout.write(F(CFG.rec));")
        r = subprocess.run([BASE.NODE or "node", "-"], input=js, capture_output=True, text=True, timeout=60,
                           env=dict(os.environ, SSV_CFG=cfg, TZ="UTC"))
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        h = r.stdout
        self.assertIn("character: Blizzy (Sorceress 92) · from select-screen · games: Morph1-Morph7 (7 games) · one farming run across 2 sessions", h)
        self.assertIn("character UNKNOWN - the reads disagree: Blizzy / Hammy · games UNKNOWN", h)


class TheProofsNameOnePlace(unittest.TestCase):

    def test_each_find_matches_once(self):
        for proof in RED_PROOF:
            src = open(os.path.join(HERE, "..", proof["file"]), encoding="utf-8").read()
            self.assertEqual(src.count(proof["find"]), proof["matches"], proof["why"])


RED_PROOF = [
    {"why": "the game password is published",
     "file": "tv/read_identity.py",
     "find": "(?=\\s*(?:$|[.,;|]|\\bpass|\\bpw\\b))",
     "replace": "(?=\\s*(?:$|[.,;|]))",
     "matches": 1},
    {"why": "disagreeing characters are guessed instead of UNKNOWN",
     "file": "tv/read_identity.py",
     "find": "    conflict = len(names) > 1 or len(classes) > 1\n",
     "replace": "    conflict = False\n",
     "matches": 1},
    {"why": "Morph1..Morph7 are seven separate games",
     "file": "tv/read_identity.py",
     "find": "_SERIES = re.compile(r\"^(.*?)(\\d+)$\")\n",
     "replace": "_SERIES = re.compile(r\"^(x)(y)$\")\n",
     "matches": 1},
    {"why": "a session with no login loses who played",
     "file": "tv/shadow_sessions.py",
     "find": "            s[\"character\"] = who_at(ident, s[\"t0\"])\n",
     "replace": "            s[\"character\"] = None\n",
     "matches": 1},
    {"why": "a conflict is drawn as a name",
     "file": "tv/control_ui.html",
     "find": "    else if (Array.isArray(ch.conflict) && ch.conflict.length) who = ",
     "replace": "    else if (false) who = ",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
