# -*- coding: utf-8 -*-
"""v3890 (#188, REG-3514 + REG-3515) - A SESSION STARTS AT THE GAME'S OWN DOOR, ON EVERY ROUTE; A SCREEN THAT NEVER SHOWED
D2R IS NOT A SESSION.

His words 11-09: "for a logical thing to have here is for it to be able to identify this and not register them as a
session at all so the last real game sessions from the diablo ii logo game and then character selection screen it
should start from there" - "if it were inteligent it would be able to register the sessions from the diablo ii logo
screen login regardless of the window being recorder wether it be boosteroid or nvideaplay or or locally" - "there
diablo ii twice... the fire logo and the screen logo ... and then im at the character selection" - "it can register it
the first and the second is the witness to it" - "and the third is the character selection screen" - "its the process".

MEASURED: the OLD ALT opened six sessions on GeForce NOW's "session ended due to inactivity" page (07:41-12:30, the tab
still titled Diablo II) and the Mac four; the READS cannot tell (two of the OLD ALT's six read as the game: the OCR lane
filed the page's words as loot). The FILM can - tv/d2r_screens.py, measured on real frames: the corner logo (corner fire
0.034-0.037 on a 0.996-dark screen), the title (centre fire 0.22-0.26), the in-game orbs (red 0.038-0.040 left, blue
0.038-0.041 right of the bottom band); every other screen centre fire <= 0.007, corner 0, no orb pair. Over his Mac's
own reels: the two idle-page reels 0 D2R frames, a real start logo x7 -> title x3 -> character select x4. Held here:
  * the screens on drawn fixtures, a browser's bright chrome cut off, and the idle page (its red book included) none;
  * chain(): the logo registers, the title witnesses, character select enters; a logo with no title is not a start;
  * the lane tags every walked frame: a walked reel with no D2R frame is False, one with the orbs True, an unwalked
    reel None;
  * _session_is_the_game: False only when the film was walked and showed nothing AND no deep read named the game; the
    Shelf list and the timeline number sessions through the one helper, and the shadow digest drops the same runs.
RED_PROOF below. [[unknown-stays-unknown]] [[the-unjoined-end]]
"""
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import d2r_screens as DS  # noqa: E402
import chronicle_line as CL  # noqa: E402

from PIL import Image, ImageDraw  # noqa: E402

FIRE = (240, 150, 40)
W, H = 800, 450


def _blank(c=(4, 3, 3)):
    return Image.new("RGB", (W, H), c)


def logo():
    im = _blank()
    ImageDraw.Draw(im).ellipse([W - 70, H - 50, W - 30, H - 22], fill=FIRE)       # the small fire logo, bottom right
    return im


def title():
    im = _blank((8, 4, 4))
    d = ImageDraw.Draw(im)
    d.rectangle([250, 90, 550, 230], fill=FIRE)                                      # the fire DIABLO II
    d.text((340, 300), "PRESS ANY KEY TO BEGIN", fill=(200, 200, 200))
    return im


def in_game():
    im = Image.new("RGB", (W, H), (60, 70, 45))                                     # the ground
    d = ImageDraw.Draw(im)
    d.ellipse([150, 370, 220, 440], fill=(190, 20, 20))                             # life, bottom left
    d.ellipse([590, 370, 660, 440], fill=(20, 40, 200))                             # mana, bottom right
    return im


def idle_page():
    """GeForce NOW's 'session ended due to inactivity': dark key art, a light dialog, and the red book bottom left."""
    im = Image.new("RGB", (W, H), (40, 44, 60))
    d = ImageDraw.Draw(im)
    d.rectangle([260, 160, 540, 260], fill=(30, 30, 34))
    d.text((280, 180), "Your game session ended due to inactivity.", fill=(230, 230, 230))
    d.rectangle([130, 360, 260, 449], fill=(190, 30, 40))                          # the red book, no blue orb anywhere
    return im


def with_chrome(im):
    """The same frame inside a browser: a bright flat bar on top."""
    out = Image.new("RGB", (W, H + 70), (241, 243, 244))
    out.paste(im, (0, 70))
    return out


def kind(im):
    return DS.screen_of(None, array=__import__("numpy").asarray(im, dtype="int16"))[0]


class TheDoorIsReadFromThePixels(unittest.TestCase):

    def test_the_logo_the_title_and_the_game_are_named(self):
        """* THE POINT - the three things only D2R draws"""
        self.assertEqual((kind(logo()), kind(title()), kind(in_game())), ("logo", "title", "hud"))

    def test_a_browsers_chrome_does_not_hide_the_title(self):
        self.assertEqual(kind(with_chrome(title())), "title")

    def test_the_idle_page_black_and_a_plain_field_are_not_the_game(self):
        """BASELINE - GeForce NOW's idle page (its red book included), a black screen, a field with no orbs"""
        self.assertEqual([kind(idle_page()), kind(_blank()), kind(Image.new("RGB", (W, H), (60, 70, 45)))],
                         [None, None, None])

    def test_a_frame_that_will_not_open_is_unknown(self):
        k, why = DS.screen_of(os.path.join(tempfile.gettempdir(), "no_frame_%d.jpg" % os.getpid()))
        self.assertIsNone(k)
        self.assertIn("unreadable", why)

    def test_screen_of_decodes_each_frame_once(self):
        """v3894 - logo/title/hud and the char-select/lobby look share one file open"""
        from PIL import Image as PILImage
        d = tempfile.mkdtemp(prefix="screen_once_")
        try:
            path = os.path.join(d, "idle.jpg")
            idle_page().save(path, "JPEG", quality=92)
            opens = []
            real = PILImage.open
            def spy(*a, **k):
                opens.append(a[0] if a else k.get("fp"))
                return real(*a, **k)
            PILImage.open = spy
            try:
                DS.screen_of(path)
            finally:
                PILImage.open = real
            self.assertEqual(opens.count(path), 1,
                             "screen_of opened the frame %d times: %r" % (opens.count(path), opens))
        finally:
            shutil.rmtree(d, ignore_errors=True)


class TheChainIsHisProcess(unittest.TestCase):
    T = 1793208591025

    def test_logo_registers_title_witnesses_character_select_enters(self):
        c = DS.chain([(self.T + 45000, "char-select"), (self.T, "logo"), (self.T + 7000, "title")])
        self.assertEqual((c["startTs"], c["titleTs"], c["charTs"], c["witnessed"], c["entered"]),
                         (self.T, self.T + 7000, self.T + 45000, True, True))

    def test_a_title_alone_still_starts_it(self):
        c = DS.chain([(self.T, "title"), (self.T + 30000, "char-select")])
        self.assertEqual((c["startTs"], c["witnessed"], c["entered"]), (self.T, False, True))

    def test_a_logo_with_no_title_is_not_a_start(self):
        self.assertIsNone(DS.chain([(self.T, "logo"), (self.T + 5000, "char-select")]))
        self.assertIsNone(DS.chain([(self.T, "char-select")]))


class TheLaneTagsEveryFrame(unittest.TestCase):
    T0 = 1794000000000

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="door_lane_")
        self.hist = os.path.join(self.tmp, "frames", "hist")
        self.old = os.environ.get("TV_CHRONICLE_LINES")
        os.environ["TV_CHRONICLE_LINES"] = os.path.join(self.tmp, ".chronicle_lines.json")
        # oldest first: an idle-page reel, a game reel; then two newer reels (LIVE_REELS = 2 are never marked done)
        self.idle = self._reel(self.T0, [idle_page()] * 4)
        self.game = self._reel(self.T0 + 10 ** 6, [logo(), title(), title(), in_game()])
        self._reel(self.T0 + 2 * 10 ** 6, [idle_page()])
        self._reel(self.T0 + 3 * 10 ** 6, [idle_page()])

    def _reel(self, t, shots):
        name = "reel_s_%d_1" % t
        d = os.path.join(self.hist, name)
        os.makedirs(d)
        for i, im in enumerate(shots):
            im.save(os.path.join(d, "f_%d.jpg" % (t + i * 1000)), "JPEG", quality=92)
        return name

    def tearDown(self):
        if self.old is None:
            os.environ.pop("TV_CHRONICLE_LINES", None)
        else:
            os.environ["TV_CHRONICLE_LINES"] = self.old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_unknown_until_walked_then_the_film_decides(self):
        """* THE POINT - before the walk nothing is known; after it the idle reel is not the game, the game reel is,
        and the game reel carries its door"""
        self.assertIsNone(CL.reel_shows_d2r(self.idle, CL.load()))
        CL.tick(root=self.hist, budget_s=120)
        d = CL.load()
        self.assertIs(CL.reel_shows_d2r(self.idle, d), False)
        self.assertIs(CL.reel_shows_d2r(self.game, d), True)
        door = CL.game_door(self.game, d)
        self.assertTrue(door and door["witnessed"] and door["startTs"] == self.T0 + 10 ** 6, door)
        self.assertEqual(d["reels"][self.game]["d2r"].get("hud"), 1)


class TheLiveFilmSaysWhetherItIsTheGame(unittest.TestCase):
    """v3890 (#189, REG-3516) - the Fleet eye's LIVE glow: the rolling reel's own film, its last five walked minutes."""
    T0 = 1795000000000

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="live_film_")
        self.hist = os.path.join(self.tmp, "frames", "hist")
        self.old = os.environ.get("TV_CHRONICLE_LINES")
        os.environ["TV_CHRONICLE_LINES"] = os.path.join(self.tmp, ".chronicle_lines.json")
        m = 60 * 1000
        self.left = self._reel(self.T0, [(0, in_game())] + [(k * m, idle_page()) for k in range(1, 8)])
        self.playing = self._reel(self.T0 + 10 ** 7, [(k * m, idle_page()) for k in range(0, 6)] + [(6 * m, in_game())])
        self.fresh = self._reel(self.T0 + 2 * 10 ** 7, [(0, idle_page()), (60 * 1000, idle_page())])

    def _reel(self, t, shots):
        name = "reel_s_%d_1" % t
        d = os.path.join(self.hist, name)
        os.makedirs(d)
        for dt, im in shots:
            im.save(os.path.join(d, "f_%d.jpg" % (t + dt)), "JPEG", quality=92)
        return name

    def tearDown(self):
        if self.old is None:
            os.environ.pop("TV_CHRONICLE_LINES", None)
        else:
            os.environ["TV_CHRONICLE_LINES"] = self.old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_game_now_the_game_gone_and_too_soon_to_say(self):
        """* THE POINT - in the game within the last five minutes is the game; seven minutes of a streaming page after
        it is not; two minutes of film with nothing yet is not known"""
        CL.tick(root=self.hist, budget_s=120)
        d = CL.load()
        self.assertEqual([CL.live_game(self.playing, d), CL.live_game(self.left, d), CL.live_game(self.fresh, d)],
                         [True, False, None])

    def test_the_console_posts_it_beside_recording(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            app = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
        i = app.index("def _shadow_for_wire(")
        body = app[i:app.index("\ndef ", i + 10)]
        self.assertIn('game = _chl.live_game("reel_" + str(_sid))', body)
        self.assertIn('"game": game, "working": working,', body)


class ASessionThatNeverShowedTheGameIsNone(unittest.TestCase):
    """control_app's one judge, driven with the film's answer stubbed."""

    @classmethod
    def setUpClass(cls):
        import control_app
        cls.C = control_app

    def _judge(self, film, rows):
        real = CL.reel_shows_d2r
        CL.reel_shows_d2r = lambda name, d=None: film
        try:
            return self.C._session_is_the_game(rows)
        finally:
            CL.reel_shows_d2r = real

    def test_the_film_decides_and_unknown_keeps_it(self):
        rows = [{"sessionId": "s_1", "lane": "ocr", "scene": "loot", "names": ["Ring"], "conf": 0.8}]
        self.assertEqual([self._judge(False, rows), self._judge(True, rows), self._judge(None, rows)],
                         [False, True, None], "an OCR 'loot' row on a streaming page must not make it the game")

    def test_a_deep_read_that_names_the_game_keeps_it(self):
        area = sorted(self.C._AREA_ACT)[0]
        rows = [{"sessionId": "s_2", "lane": "deep", "scene": "gameplay", "area": area, "names": [], "conf": 0.9,
                 "mode": "sonnet", "model": "sonnet", "ms": 900}]
        self.assertIs(self._judge(False, rows), True)

    def test_the_list_drops_only_the_runs_that_were_never_the_game(self):
        real = CL.reel_shows_d2r
        verdict = {"reel_s_a": False, "reel_s_b": True, "reel_s_c": None}
        CL.reel_shows_d2r = lambda name, d=None: verdict.get(name)
        try:
            kept, dropped = self.C._game_sessions([[{"sessionId": "s_a"}], [{"sessionId": "s_b"}], [{"sessionId": "s_c"}]])
        finally:
            CL.reel_shows_d2r = real
        self.assertEqual(([s[0]["sessionId"] for s in kept], dropped), (["s_b", "s_c"], 1))

    def test_every_site_that_numbers_sessions_uses_the_one_helper(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            app = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
        import re
        # the comment line between them strips to blanks: allow blank lines, nothing else
        self.assertEqual(len(re.findall(r"sessions = _rp\.split_sessions\(_jrows\)\n(?:[ ]*\n)*[ ]*"
                                        r"sessions, _not_game = _game_sessions\(sessions\)", app)), 1)
        self.assertEqual(len(re.findall(r"sessions = _rp\.split_sessions\(self\._load_journal_cached\(\)\)\n(?:[ ]*\n)*[ ]*"
                                        r"sessions, _ng = _game_sessions\(sessions\)", app)), 1)
        self.assertIn("                   is_game=_session_is_the_game,", app)   # v3898 - game_of= follows it now
        with io.open(os.path.join(HERE, "shadow_sessions.py"), encoding="utf-8") as fh:
            ss = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
        self.assertIn("_game = [g for g in _kept if is_game(g) is not False]", ss)


RED_PROOF = [
    {"why": "v3890 (#189) - a streaming page after the game still reads as the game on the live eye",
     "file": "tv/chronicle_line.py",
     "find": "    if isinstance(since, int) and walked - since >= fresh_ms:\n        return False\n",
     "replace": "",
     "matches": 1},
    {"why": "v3890 (#189) - the console never posts whether the rolling reel shows the game",
     "file": "tv/control_app.py",
     "find": "                game = _chl.live_game(\"reel_\" + str(_sid))\n",
     "replace": "                game = None\n",
     "matches": 1},
    {"why": "v3890 (#188) - any dark screen passes for the title",
     "file": "tv/d2r_screens.py",
     "find": "    if (st[\"centre\"] >= TITLE_CENTRE_MIN and st[\"rest\"] <= TITLE_REST_MAX and st[\"dark\"] >= TITLE_DARK_MIN):\n",
     "replace": "    if (st[\"rest\"] <= TITLE_REST_MAX and st[\"dark\"] >= TITLE_DARK_MIN):\n",
     "matches": 1},
    {"why": "v3890 (#188) - a black screen passes for the corner logo",
     "file": "tv/d2r_screens.py",
     "find": "    if (st[\"corner\"] >= LOGO_CORNER_MIN and st[\"dark\"] >= LOGO_DARK_MIN\n",
     "replace": "    if (st[\"dark\"] >= LOGO_DARK_MIN\n",
     "matches": 1},
    {"why": "v3890 (#188) - a red book with no mana orb passes for a game",
     "file": "tv/d2r_screens.py",
     "find": "    if (st.get(\"red\", 0) >= ORB_MIN and st.get(\"blue\", 0) >= ORB_MIN\n            and 0.08 <= (st.get(\"redX\") or 0) <= 0.42 and 0.58 <= (st.get(\"blueX\") or 0) <= 0.92):\n",
     "replace": "    if (st.get(\"red\", 0) >= ORB_MIN\n            and 0.08 <= (st.get(\"redX\") or 0) <= 0.42):\n",
     "matches": 1},
    {"why": "v3890 (#188) - a logo with no title witness starts a session",
     "file": "tv/d2r_screens.py",
     "find": "        if title is None and conn is None:\n            continue\n",   # v3898 (REG-3715) - CONNECTING witnesses too
     "replace": "",
     "matches": 1},
    {"why": "v3890 (#188) - a reel walked to its end with no D2R frame stays UNKNOWN, so it is never left out",
     "file": "tv/chronicle_line.py",
     "find": "    if rs.get(\"done\") and n > 0 and int(rs.get(\"pos\") or 0) >= n:\n        return False\n",
     "replace": "",
     "matches": 1},
    {"why": "v3890 (#188) - the lane stops tagging the frames it walks",
     "file": "tv/chronicle_line.py",
     "find": "                if r.get(\"screen\"):\n                    _mark(rs, _frame_ts(p), r[\"screen\"])\n",
     "replace": "",
     "matches": 1},
    {"why": "v3890 (#188) - a deep read naming the game no longer keeps a session the orbs missed",
     "file": "tv/control_app.py",
     "find": "               if isinstance(r, dict) and r.get(\"lane\") == \"deep\" and _tv._is_content_read(r)):\n            return True\n",
     "replace": "               if False):\n            return True\n",
     "matches": 1},
    {"why": "v3890 (#188) - the Shelf lists every run again, the idle pages included",
     "file": "tv/control_app.py",
     "find": "            sessions, _not_game = _game_sessions(sessions)\n",
     "replace": "            _not_game = 0\n",
     "matches": 1},
    {"why": "v3890 (#188) - the timeline numbers sessions another way than the Shelf",
     "file": "tv/control_app.py",
     "find": "            sessions, _ng = _game_sessions(sessions)   # v3890 (#188) - numbered the same way the Shelf numbers them\n",
     "replace": "",
     "matches": 1},
    {"why": "v3890 (#188) - the shadow digest keeps the idle-page runs",
     "file": "tv/shadow_sessions.py",
     "find": "        _game = [g for g in _kept if is_game(g) is not False]\n",
     "replace": "        _game = list(_kept)\n",
     "matches": 1},
    {"why": "v3894 - screen_of decodes the frame again for char-select",
     "file": "tv/d2r_screens.py",
     "find": "            ok, cwhy = _cs.looks_like_char_select(_cs.panel_stats(src if isinstance(src, str) else None, image=raw))\n",
     "replace": "            ok, cwhy = _cs.looks_like_char_select(_cs.panel_stats(src))\n",
     "matches": 1},
    {"why": "v3894 - screen_of decodes the frame again for the lobby look",
     "file": "tv/d2r_screens.py",
     "find": "            ok, lwhy = _cs.looks_like_lobby(_cs.lobby_stats(src if isinstance(src, str) else None, image=raw))\n",
     "replace": "            ok, lwhy = _cs.looks_like_lobby(_cs.lobby_stats(src))\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
