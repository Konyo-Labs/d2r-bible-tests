# -*- coding: utf-8 -*-
"""v3900 (REG-3742, #188) - A GAME THAT STARTS INSIDE AN HOURLY PART SAYS ITS PART 1 ON THAT PART'S CARD.

MEASURED by GrokBot 11-12 01:25-01:50 (#230 6809993907, look only) on the Mac's shadow rows of the work ALT: 19 of 21 games
read right (the long 02:00-09:00 game is part 2..8 of 8), and 2 read "part 2 of 2" with no part 1 anywhere: the 22:00 card,
whose game id names the 21:52 reel as its start (character select 21:54:50) while the 21:52 row carries no game; and the
14:00 card, whose game began at a character select at 13:50:18 inside the 13:00 card - itself "part 2 of 2" of the older
no-login game. The equipped ledger files each reel under its OPENING span's game (ingest's reelGame), so a reel holding the
tail of one game and then a character select never said it starts the next one. Now _shelf_games also gives such a reel
`then` - the multi-part game it starts - the shadow digest carries it, and shGamePart draws "then a new game: part 1 of m".

DRIVEN: the shipped game_sessions over fixture reels (the reelGame rule read off ingest's own line), the shipped _shelf_games
over that store, the shipped shadow digest, and shGamePart cut from tv/control_ui.html in node. RED_PROOF below.
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
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import equipped_ledger as EL  # noqa: E402
from cb_node_harness import NODE  # noqa: E402

T0 = 1500000000000
HOUR = 3600 * 1000
GAP = 15 * 1000


def _reel(sid, a, rows, door="rollover"):
    b = a + HOUR - 1000
    return {"sid": sid, "t0": a, "t1": b, "door": door, "sealed": True, "sealedTs": b, "rows": rows}


def _row(sid, ts):
    return {"sessionId": sid, "ts": ts, "scene": "town"}


def _work_alt_night(tail_chains=True):
    """the 21:00 part (AFK, no login) -> the 22:00 part: its tail, then a character select, then play -> the 23:00 part
    (rollover). tail_chains=False puts the 22:00 part past the hand-off, so its tail is a one-part game of its own."""
    a0 = T0
    a1 = a0 + HOUR - 1000 + (GAP if tail_chains else 10 * HOUR)
    a2 = a1 + HOUR - 1000 + GAP
    login = EL.login_rows([{"sessionId": "s_1", "ts": a1 + 20 * 60 * 1000, "character": "Konyomancer"}])
    r0 = _reel("s_0", a0, [_row("s_0", a0), _row("s_0", a0 + HOUR - 1000)])
    r1 = _reel("s_1", a1, [_row("s_1", a1), _row("s_1", a1 + 10 * 60 * 1000)] + login
               + [_row("s_1", a1 + 30 * 60 * 1000), _row("s_1", a1 + HOUR - 1000)])
    r2 = _reel("s_2", a2, [_row("s_2", a2), _row("s_2", a2 + HOUR - 1000)])
    reels = [r0, r1, r2]
    sessions, _by = EL.game_sessions(reels)
    # ingest's reelGame rule, word for word (pinned below against equipped_ledger.py)
    rg = {}
    for reel in reels:
        sp0 = (reel.get("spans") or [None])[0]
        if isinstance(sp0, dict) and sp0.get("session"):
            rg[reel["sid"]] = sp0["session"]
    return {"gameSessions": dict((s["id"], s) for s in sessions), "reelGame": rg}


def _shelf(store):
    import control_app as CA
    with mock.patch.object(EL, "load", lambda *a, **k: (store, "")):
        return CA._shelf_games()


class AGameThatStartsMidReelSaysItsPartOne(unittest.TestCase):

    def test_the_reel_that_starts_the_game_says_part_one(self):
        """* THE POINT - the work ALT's 22:00 game: "part 2 of 2" and no part 1 card"""
        store = _work_alt_night()
        multi = [g for g in store["gameSessions"].values() if len(g["reels"]) > 1]
        self.assertEqual(sorted(g["reels"] for g in multi), [["s_0", "s_1"], ["s_1", "s_2"]],
                         "PREMISE: the fixture is not the work ALT's shape - two games that share the 22:00 part")
        got = _shelf(store)
        self.assertEqual((got["s_1"]["part"], got["s_1"]["parts"]), (2, 2), got)   # the tail of the AFK game, as before
        self.assertEqual(got["s_1"].get("then"), {"id": store["reelGame"]["s_2"], "part": 1, "parts": 2,
                                                 "character": "Konyomancer"},
                         "the part where the character select happened does not say it starts the next game: %r" % got)
        self.assertEqual((got["s_2"]["part"], got["s_2"]["parts"]), (2, 2))
        self.assertNotIn("then", got["s_2"])
        self.assertNotIn("then", got["s_0"], "a part that starts no game claims one")

    def test_a_one_part_tail_still_says_the_game_it_starts(self):
        """the 14:00 shape, when the tail before the character select is a game of its own: the card says only 'then'"""
        got = _shelf(_work_alt_night(tail_chains=False))
        self.assertNotIn("part", got["s_1"], "a one-part tail claims a link")
        self.assertEqual((got["s_1"]["then"]["part"], got["s_1"]["then"]["parts"]), (1, 2), got)

    def test_the_shadow_digest_carries_the_game_it_starts(self):
        import shadow_sessions as SS
        rows = [{"sessionId": "s_1", "ts": T0, "captureTs": T0, "frameId": "f_1", "scene": "town"},
                {"sessionId": "s_1", "ts": T0 + 1000, "captureTs": T0 + 1000, "scene": "session_end"}]
        both = {"s_1": {"part": 2, "parts": 2, "character": None,
                        "then": {"id": "g", "part": 1, "parts": 2, "character": "Konyomancer"}}}
        d = SS.digest(rows, tempfile.gettempdir(), lambda r: False, T0, make=lambda *a, **k: None, game_of=both.get)
        self.assertEqual(d["sessions"][0].get("game"), {"part": 2, "parts": 2, "character": None,
                                                        "then": {"part": 1, "parts": 2, "character": "Konyomancer"}})
        only = {"s_1": {"then": {"id": "g", "part": 1, "parts": 3, "character": None}}}
        d2 = SS.digest(rows, tempfile.gettempdir(), lambda r: False, T0, make=lambda *a, **k: None, game_of=only.get)
        self.assertEqual(d2["sessions"][0].get("game"), {"then": {"part": 1, "parts": 3, "character": None}})

    def test_the_card_draws_then_a_new_game(self):
        if NODE is None:
            raise AssertionError("node is not installed on this PC - this law runs the shipped card helper and does not skip")
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        head = "  function shGamePart(g, after){"
        self.assertEqual(ui.count(head), 1)
        i = ui.index(head)
        fn = ui[i:ui.index("\n  }\n", i) + 4]
        prog = ("function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/\"/g,'&quot;'); }\n"
                + fn + "\nconsole.log(JSON.stringify([shGamePart({part: 2, parts: 2, then: {part: 1, parts: 2, character: 'Konyomancer'}}, true),"
                " shGamePart({then: {part: 1, parts: 3}}, true), shGamePart({then: {part: 1, parts: 1}}, true),"
                " shGamePart({part: 2, parts: 7}, true)]));\n")
        d = tempfile.mkdtemp(prefix="game_then_")
        try:
            h = os.path.join(d, "h.js")
            with io.open(h, "w", encoding="utf-8") as fh:
                fh.write(prog)
            r = subprocess.run([NODE, h], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        finally:
            shutil.rmtree(d, True)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace")[-600:])
        both, only, one, plain = json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])
        self.assertIn("part 2 of 2 · one game", both)
        self.assertIn("then a new game as Konyomancer: part 1 of 2", both)
        self.assertIn("then a new game: part 1 of 3", only)
        self.assertNotIn("one game", only, "a one-part tail claims a link")
        self.assertEqual(one, "", "a one-part new game claims a link")
        self.assertNotIn("then", plain)

    def test_the_rule_this_law_reads_is_ingests_own(self):
        with io.open(os.path.join(HERE, "equipped_ledger.py"), encoding="utf-8") as fh:
            el = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
        self.assertEqual(el.count('rg[reel["sid"]] = sp0["session"]'), 1, "ingest's reelGame rule moved - re-read it here")


RED_PROOF = [
    {"why": "REG-3742 - the part where a character select started the next game no longer says so (GrokBot, the work "
            "ALT 11-11: 'part 2 of 2' with no part 1)",
     "file": "tv/control_app.py",
     "find": "            if str(rg.get(sid)) != str(gid):\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-3742 - the shadow digest drops the game a part starts",
     "file": "tv/shadow_sessions.py",
     "find": "        if isinstance(_then, dict) and (_then.get(\"parts\") or 0) > 1:   # REG-3742 - the game this part STARTS, mid-reel\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3742 - the card does not draw the game a part starts",
     "file": "tv/control_ui.html",
     "find": "    if (t && t.parts > 1 && t.part >= 1) {\n",
     "replace": "    if (false) {\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
