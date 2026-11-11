# -*- coding: utf-8 -*-
"""v3898 (#188, REG-3713) - THE HOURLY PARTS STAY, AND THE PARTS OF ONE GAME ARE LINKED; A PART THAT NEVER SHOWED THE GAME ENDS IT.

His 11-11 ruling (memory ruling_2026-11-11_hourly_parts_one_game): "its one session connected and one game in this case i
stayed AFK all night ... i just wanted it broken up like this so the retro readers can work ... the FIFO design" - keep
each sealed hour as its own part, and link the parts with no new trigger between them into one game. "if i exit and was
afk that the trigger for a new session obviously".

The chain already existed in the equipped ledger (a character select starts a game; a part with no login continues the
last one across the hourly hand-off, ROLLOVER_GAP_MS). MEASURED 11-11 on the work ALT's own store: 01:03 -> 13:50 chained
as ONE game of 15 parts straight through the 12:00 part that filmed only Boosteroid's page, so his 12:40 new game was
glued onto the night's AFK game. Now a part whose film walked to its end with no D2R screen (is_game False) is no part
of a game and ends the one before it; an unknown answer cuts nothing. The Shelf row carries `game` {part, parts} for a
reel of a 2+ part game, stamped after the row cache, and the card says "part k of m · one game".

DRIVEN: the shipped game_sessions over fixture reels; the shipped _shelf_games over a stub ledger store; the shipped
shGamePart cut from tv/control_ui.html and run in node. RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import equipped_ledger as EL  # noqa: E402
import js_strip  # noqa: E402
from cb_node_harness import NODE  # noqa: E402

T0 = 1794348000000
HOUR = 3600 * 1000


def _reels(n=3, gap_s=15):
    """n hourly parts of one AFK game: no login in any, each starting gap_s after the last one's seal"""
    out = []
    for k in range(n):
        a = T0 + k * (HOUR + gap_s * 1000)
        b = a + HOUR - 1000
        rows = [{"sessionId": "s_%d" % k, "ts": a, "scene": "town"}, {"sessionId": "s_%d" % k, "ts": b, "scene": "town"}]
        out.append({"sid": "s_%d" % k, "t0": a, "t1": b, "door": "rollover", "sealed": True, "sealedTs": b, "rows": rows})
    return out


def _games(is_game=None, **kw):
    sessions, _by = EL.game_sessions(_reels(**kw), is_game=is_game)
    return [s["reels"] for s in sessions]


class OneGameInHourlyParts(unittest.TestCase):

    def test_hourly_parts_with_no_trigger_between_are_one_game(self):
        """BASELINE - the ledger's chain: three parts across the hourly hand-off are one game"""
        self.assertEqual(_games(), [["s_0", "s_1", "s_2"]])

    def test_a_part_that_never_showed_the_game_ends_the_game(self):
        """* THE POINT - the work ALT's 12:00 Boosteroid-page part: it joins nothing and nothing joins it"""
        self.assertEqual(_games(is_game=lambda sid: sid != "s_1"), [["s_0"], ["s_1"], ["s_2"]],
                         "a part that filmed no D2R still chained the game before it to the game after it")

    def test_an_unknown_answer_cuts_nothing(self):
        """a reel the film lane has not walked (None) is not called a non-game: nothing is cut on a guess"""
        self.assertEqual(_games(is_game=lambda sid: None), [["s_0", "s_1", "s_2"]])

    def test_a_longer_gap_than_the_hand_off_is_still_a_new_game(self):
        self.assertEqual(_games(gap_s=EL.ROLLOVER_GAP_MS // 1000 + 30), [["s_0"], ["s_1"], ["s_2"]])

    def test_the_shelf_reads_part_k_of_m_from_the_ledger(self):
        import control_app as CA
        store = {"gameSessions": {"g_a": {"id": "g_a", "reels": ["s_0", "s_1", "s_2"], "character": "Konyomancer"},
                                  "g_b": {"id": "g_b", "reels": ["s_9"], "character": None}},
                 "reelGame": {"s_0": "g_a", "s_1": "g_a", "s_2": "g_a", "s_9": "g_b"}}
        with mock.patch.object(EL, "load", lambda *a, **k: (store, "")):
            got = CA._shelf_games()
        self.assertEqual(got.get("s_1"), {"id": "g_a", "part": 2, "parts": 3, "character": "Konyomancer"}, got)
        self.assertNotIn("s_9", got, "a one-part game is not a linked game - the card says nothing")
        with mock.patch.object(EL, "load", lambda *a, **k: (None, "unreadable")):
            self.assertEqual(CA._shelf_games(), {}, "an unreadable ledger must link nothing, never guess")

    def test_the_ledger_records_each_reels_game_and_the_console_passes_the_film(self):
        with io.open(os.path.join(HERE, "equipped_ledger.py"), encoding="utf-8") as fh:
            el = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
        self.assertEqual(el.count("gsessions, _by = game_sessions(reels, gap_ms=gap_ms, named_at=_named, is_game=is_game)"), 1)
        self.assertEqual(el.count("rg[reel[\"sid\"]] = sp0[\"session\"]"), 1, "ingest no longer records each reel's game")
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            ca = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
        self.assertEqual(ca.count("_el.ingest(_journal_ring(), HIST_DIR, is_game=_reel_is_the_game)"), 1,
                         "the seal's ledger call no longer passes the film's answer - a non-game part chains again")
        i = ca.index("def _theatre_sessions(self):")
        j = ca.index("\n    def ", i + 10)
        body = ca[i:j]
        self.assertLess(body.index("_theatre_row_cache_put(_ck, _row)"), body.index("_games = _shelf_games()"),
                        "the game link is stamped before the row cache - a cached row would freeze 'part 1 of 1'")

    def test_the_card_says_part_k_of_m(self):
        if NODE is None:
            raise AssertionError("node is not installed on this PC - this law runs the shipped card helper and does not skip")
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        head = "  function shGamePart(g, after){"
        self.assertEqual(ui.count(head), 1)
        i = ui.index(head)
        fn = ui[i:ui.index("\n  }\n", i) + 4]
        prog = ("function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/\"/g,'&quot;'); }\n"
                + fn + "\nconsole.log(JSON.stringify([shGamePart({part: 2, parts: 7}, true), shGamePart({part: 1, parts: 1}, true),"
                " shGamePart(null, false), shGamePart({part: 3, parts: 4, character: 'Konyomancer'}, false)]));\n")
        d = tempfile.mkdtemp(prefix="game_part_")
        try:
            h = os.path.join(d, "h.js")
            with io.open(h, "w", encoding="utf-8") as fh:
                fh.write(prog)
            r = subprocess.run([NODE, h], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        finally:
            shutil.rmtree(d, True)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace")[-600:])
        a, one, none, who = json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])
        self.assertIn("part 2 of 7 · one game", a)
        self.assertTrue(a.startswith(" "), "after a duration the label is set apart")
        self.assertEqual(one, "", "a one-part game claims a link")
        self.assertEqual(none, "")
        self.assertIn("as Konyomancer", who)
        self.assertIn('class="shc-game"', who)
        self.assertEqual(ui.count("_shcWhen += shGamePart(sm.game, !!_shcWhen);"), 1, "the card no longer draws the link")


    def test_a_shadow_draws_the_same_part_of_one_game(self):
        """his shadow view of the ALT is where he sees its AFK night: the published digest carries `game`, the shadow row draws it"""
        import shadow_sessions as SS
        rows = [{"sessionId": "s_0", "ts": T0, "captureTs": T0, "frameId": "f_1", "scene": "town"},
                {"sessionId": "s_0", "ts": T0 + 1000, "captureTs": T0 + 1000, "scene": "session_end"}]
        d = SS.digest(rows, tempfile.gettempdir(), lambda r: False, T0, make=lambda *a, **k: None,
                      game_of={"s_0": {"part": 2, "parts": 3, "character": None}}.get)
        self.assertEqual([x.get("game") for x in d["sessions"]], [{"part": 2, "parts": 3, "character": None}], d["sessions"])
        d1 = SS.digest(rows, tempfile.gettempdir(), lambda r: False, T0, make=lambda *a, **k: None,
                       game_of={"s_0": {"part": 1, "parts": 1}}.get)
        self.assertNotIn("game", d1["sessions"][0], "a one-part game is published as a link")
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        self.assertEqual(ui.count("+ (typeof shGamePart === 'function' ? shGamePart(s.game, true) : '') + '</div>'"), 1,
                         "the shadow row no longer draws the link")
        self.assertEqual(ui.count("  function shGamePart(g, after){"), 1, "the helper the shadow row asks for is gone")
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            ca = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
        self.assertEqual(ca.count("game_of=_shelf_games().get)"), 1, "the published digest no longer carries the game link")

RED_PROOF = [
    {"why": "v3898 (#188, REG-3713) - a part that filmed no D2R chains the game before it to the game after it again",
     "file": "tv/equipped_ledger.py",
     "find": "            not_game = is_game is not None and is_game(reel[\"sid\"]) is False\n",
     "replace": "            not_game = False\n",
     "matches": 1},
    {"why": "v3898 (#188, REG-3713) - the part after a non-game part chains onto it (only one side of the break)",
     "file": "tv/equipped_ledger.py",
     "find": "        prev_not_game = not_game\n",
     "replace": "        prev_not_game = False\n",
     "matches": 1},
    {"why": "v3898 (#188, REG-3713) - an unknown film answer cuts the game on a guess",
     "file": "tv/equipped_ledger.py",
     "find": "            not_game = is_game is not None and is_game(reel[\"sid\"]) is False\n",
     "replace": "            not_game = is_game is not None and not is_game(reel[\"sid\"])\n",
     "matches": 1},
    {"why": "v3898 (#188, REG-3713) - a one-part game is drawn as a linked game",
     "file": "tv/control_app.py",
     "find": "        if len(reels) > 1 and str(sid) in reels:\n",
     "replace": "        if len(reels) > 0 and str(sid) in reels:\n",
     "matches": 1},
    {"why": "v3898 (#188, REG-3713) - the card stops saying which part of one game it is",
     "file": "tv/control_ui.html",
     "find": "    if (!g || !(g.parts > 1) || !(g.part >= 1)) return '';\n",
     "replace": "    return '';\n",
     "matches": 1, "needs": "node"},
    {"why": "v3898 (#188, REG-3713) - the published digest stops carrying the part of one game, so a shadow never sees it",
     "file": "tv/shadow_sessions.py",
     "find": "        if isinstance(_gp, dict) and _gp.get(\"parts\", 0) > 1:\n",
     "replace": "        if False:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
