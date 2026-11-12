# -*- coding: utf-8 -*-
"""v3901 (REG-3755, #188) - A SHELF CARD SAYS WHEN THE GAME BEGAN AT ITS OWN DOOR.

His ruling 11-11: on every route the session starts at the game's own door - the first D2 logo, witnessed by the title or
Connecting to Battle.net, then character select. The chronicle lane works that door out for every reel it walks
(d2r_screens.chain over the reel's door marks, kept in its ledger as `chain`) and NOTHING read it: game_door() had no caller
outside the laws, so a reel that opened on a cloud launcher, Boosteroid's queue or the Battle.net launcher said only when the
REEL opened. Now /api/sessions carries each walked reel's `door` (attached AFTER the row cache, like v3898's game link -
the lane walks a reel after its row is built and a sealed reel's directory never changes again) and the card draws "game
began 9:04 PM at the D2 logo · 12 min in" on its own line. No door -> nothing is said; an unreadable ledger draws no door.

DRIVEN: control_app._session_doors over a fixture ledger (TV_CHRONICLE_LINES), the sessions builder's after-cache attach by
its own source (one anchor), and shDoorPart cut from tv/control_ui.html and run in node. RED_PROOF below.
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
from cb_node_harness import NODE  # noqa: E402

T0 = 1796000000000
DOOR = {"startTs": T0 + 12 * 60000, "logoTs": T0 + 12 * 60000, "titleTs": None, "connectingTs": T0 + 12 * 60000 + 9000,
        "charTs": T0 + 12 * 60000 + 31000, "witnessed": True, "entered": True}


class ACardSaysWhenTheGameBegan(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="door_card_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.path = os.path.join(self.tmp, ".chronicle_lines.json")
        self.old = os.environ.get("TV_CHRONICLE_LINES")
        os.environ["TV_CHRONICLE_LINES"] = self.path
        self.addCleanup(self._env)

    def _env(self):
        if self.old is None:
            os.environ.pop("TV_CHRONICLE_LINES", None)
        else:
            os.environ["TV_CHRONICLE_LINES"] = self.old

    def _ledger(self, reels):
        with io.open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"v": 1, "reels": reels, "hits": [], "stats": {}}, fh)

    def test_the_console_hands_each_walked_reel_its_door(self):
        import control_app as ca
        self._ledger({"reel_s_%d_1" % T0: {"chain": DOOR, "marks": [[DOOR["logoTs"], "logo"]]},
                      "reel_s_%d_2" % T0: {"marks": [], "d2r": {"hud": 3}}})
        doors = ca._session_doors()
        self.assertEqual(sorted(doors), ["s_%d_1" % T0], "a reel with no door was handed one, or the walked one lost it")
        self.assertEqual(doors["s_%d_1" % T0]["startTs"], DOOR["startTs"])
        self.assertNotIn("witnessed", doors["s_%d_1" % T0], "the row carries more than the door's moments")

    def test_an_unreadable_ledger_draws_no_door(self):
        import control_app as ca
        with io.open(self.path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertIsNone(ca._session_doors(), "an unreadable ledger read as 'no reel has a door'")

    def test_the_door_rides_the_rows_after_the_cache(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            code = "\n".join(l.split("#", 1)[0].rstrip() for l in fh.read().split("\n"))
        anchor = ("            _doors = _session_doors() or {}\n"
                  "            for _r in out:\n"
                  "                _d = _doors.get(str((_r or {}).get(\"sessionId\") or \"\"))\n"
                  "                if _d:\n"
                  "                    _r[\"door\"] = _d\n")
        self.assertEqual(code.count(anchor), 1, "the sessions rows no longer carry the reel's door")

    def test_a_shadow_carries_the_door_too(self):
        """REG-3759 (#212) - the shadow digest each PC publishes carries the door, and the shadow row draws the same line"""
        import shadow_sessions as SS
        rows = [{"sessionId": "s_1", "ts": T0, "captureTs": T0, "frameId": "f_1", "scene": "town"},
                {"sessionId": "s_1", "ts": T0 + 1000, "captureTs": T0 + 1000, "scene": "session_end"}]
        d = SS.digest(rows, tempfile.gettempdir(), lambda r: False, T0, make=lambda *a, **k: None,
                      door_of={"s_1": DOOR}.get)
        self.assertEqual(d["sessions"][0].get("door"), {k: DOOR[k] for k in ("startTs", "logoTs", "titleTs",
                                                                               "connectingTs", "charTs")})
        d2 = SS.digest(rows, tempfile.gettempdir(), lambda r: False, T0, make=lambda *a, **k: None, door_of={}.get)
        self.assertNotIn("door", d2["sessions"][0], "a session with no door was handed one")
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        self.assertEqual(ui.count("(typeof shDoorPart === 'function' ? shDoorPart(s.door, s.t0) : '')"), 1,
                         "the shadow row no longer draws when its game began")
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            app = "\n".join(l.split("#", 1)[0].rstrip() for l in fh.read().split("\n"))
        self.assertEqual(app.count("door_of=(_session_doors() or {}).get)"), 1, "the published digest lost the door")

    def test_the_card_says_when_the_game_began(self):
        """* THE POINT - a reel that opened 12 min before the D2 logo says the game began at the logo, 12 min in"""
        if NODE is None:
            raise AssertionError("node is not installed on this PC - this law runs the shipped card helper and does not skip")
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        head = "  function shDoorPart(dr, t0){"
        self.assertEqual(ui.count(head), 1)
        i = ui.index(head)
        fn = ui[i:ui.index("\n  }\n", i) + 4]
        prog = ("function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/\"/g,'&quot;'); }\n"
                + fn + "\nvar D = %s;\nconsole.log(JSON.stringify([shDoorPart(D, %d), shDoorPart(null, %d),"
                       " shDoorPart({startTs: %d, logoTs: null, titleTs: %d}, %d), shDoorPart(D, 0), shDoorPart(D, 1000)]));\n"
                % (json.dumps(DOOR), T0, T0, T0 + 5000, T0 + 5000, T0))
        d = tempfile.mkdtemp(prefix="door_card_js_")
        try:
            h = os.path.join(d, "h.js")
            with io.open(h, "w", encoding="utf-8") as fh:
                fh.write(prog)
            r = subprocess.run([NODE, h], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        finally:
            shutil.rmtree(d, True)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace")[-600:])
        logo, none, title, no_t0, foreign = json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])
        self.assertIn("game began", logo)
        self.assertIn("at the D2 logo · 12 min in", logo)
        self.assertEqual(logo.count('class="shc-door-u"'), 2, "the line no longer wraps between its two units")
        self.assertNotIn("min in", foreign, "a start clock that does not belong to this reel gave an absurd lag")
        self.assertIn("Connecting to Battle.net", logo, "the door's witness is not named in its detail")
        self.assertEqual(none, "", "a card with no door says something anyway")
        self.assertIn("at the D2 title", title)
        self.assertNotIn("min in", title, "a game that began in the reel's first minute claims a lag")
        self.assertNotIn("min in", no_t0, "a lag was computed against an unknown reel start")


RED_PROOF = [
    {"why": "REG-3759 - a shadow session loses its door (the owner's card says when the game began, the shadow does not)",
     "file": "tv/shadow_sessions.py",
     "find": "        if isinstance(_dr, dict) and isinstance(_dr.get(\"startTs\"), int):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3755 - the sessions rows lose the reel's door again (the lane's chain is computed and never shown)",
     "file": "tv/control_app.py",
     "find": "                    _r[\"door\"] = _d\n",
     "replace": "                    pass\n",
     "matches": 1},
    {"why": "REG-3755 - the card never says when the game began",
     "file": "tv/control_ui.html",
     "find": "    if (!dr || !(+dr.startTs > 0)) return '';\n",
     "replace": "    return '';\n",
     "matches": 1},
    {"why": "REG-3755 - an unreadable ledger reads as 'no reel has a door'",
     "file": "tv/control_app.py",
     "find": "    if d is None:\n        return None\n    out = {}\n    for name, rs in ((d or {}).get(\"reels\") or {}).items():\n",
     "replace": "    out = {}\n    for name, rs in ((d or {}).get(\"reels\") or {}).items():\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
