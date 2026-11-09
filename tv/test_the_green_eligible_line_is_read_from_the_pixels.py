# -*- coding: utf-8 -*-
"""v3890 (#184, REG-3512 + REG-3513) - THE GREEN "ELIGIBLE FOR CHRONICLE" LINE IS READ FROM THE PIXELS, ON EVERY REEL FRAME.

His rule, 11-09: "FOUND should be chronicle found meaning the keyword in green for unidentified items before being
identified those reels and frames are chronicles found"; and, on his screenshots of the game: "it can be not ethereal it
can be any set or unique item". Every example shows the red "Unidentified" line with the green "Eligible for Chronicle"
line directly under it; the unidentified Ring that is not eligible shows the red line and nothing green under it.

MEASURED 11-09: session_route.chronicle_eligible needs a line colour and no reader ever wrote one - 0 "Unidentified"
rows in ~33,000 journal rows - so every session's CHRONICLES box could only say '?'. Held here:
  * tv/chronicle_line.py reads the shape from pixels: a red text line, a green text line directly under it, centred
    together, the green ~1.8x as wide, both on the tooltip's dark ground. Drawn fixtures at a 1440 and an 800 frame;
    the Ring, a green line under a white one, a green line far below, a short green line and a non-tooltip ground are
    not finds. His screenshot's colours (225,111,107) / (113,238,76) are inside the bands, and the white, gold and
    blue item colours are not.
  * the lane walks every reel frame once, banks a find with its witness and a PROOF copy, counts one item hovered
    across frames once, does not count a tooltip on the stash side, and a session window is UNKNOWN (None) until its
    footage is walked - then a number, 0 included.
  * the joints: the console's 45 s tick rides the lane, both session call sites hand session_facts this console's
    count, the row cache moves when the lane's answer can, and his own card reads the count where his console puts it
    (sm.route).
RED_PROOF below. [[unknown-stays-unknown]] [[the-unjoined-end]] [[heart-first]]
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import chronicle_line as CL  # noqa: E402
import js_strip  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

RED, GREEN, WHITE = (225, 111, 107), (113, 238, 76), (166, 166, 166)
GOLD, BLUE = (199, 179, 119), (105, 105, 255)
GROUND, BOX = (46, 40, 34), (8, 8, 8)


def _text(word, colour, scale, box=BOX):
    """One line of text in the bitmap default font, scaled up by whole pixels (NEAREST keeps the colour exact). In
    CAPITALS: the game's tooltip font is small capitals with no descenders, and a 'g' would make the line a
    third taller than anything the game draws."""
    word = word.upper()
    f = ImageFont.load_default()
    probe = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    l, t, r, b = probe.textbbox((0, 0), word, font=f)
    im = Image.new("RGB", (r - l + 2, b - t + 2), box)
    ImageDraw.Draw(im).text((1 - l, 1 - t), word, fill=colour, font=f)
    return im.resize((im.size[0] * scale, im.size[1] * scale), Image.NEAREST)


def frame(lines, size=(1440, 810), scale=2, at=(900, 260), box=BOX, ground=GROUND, gap=None, jpeg=True):
    """A game-sized frame holding one tooltip: `lines` = [(word, colour), ...] centred under each other on `box`."""
    im = Image.new("RGB", size, ground)
    parts = [_text(w, c, scale, box) for w, c in lines]
    lh = max(p.size[1] for p in parts)
    step = lh + (gap if gap is not None else max(2, lh // 3))
    bw = max(p.size[0] for p in parts) + 24 * scale
    bh = step * len(parts) + 12 * scale
    x0, y0 = at[0] - bw // 2, at[1]
    ImageDraw.Draw(im).rectangle([x0, y0, x0 + bw, y0 + bh], fill=box)
    y = y0 + 6 * scale
    for p in parts:
        bg = Image.new("RGB", p.size, box)
        bg.paste(p, (0, 0))
        im.paste(bg, (at[0] - p.size[0] // 2, y))
        y += step
    if jpeg:
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
        buf.seek(0)
        im = Image.open(buf)
        im.load()
    return im


ELIGIBLE = [("Greaves", WHITE), ("Defense: 16", WHITE), ("Unidentified", RED), ("Eligible for Chronicle", GREEN),
            ("Hold Shift to Compare", WHITE)]
RING = [("Ring", WHITE), ("Unidentified", RED), ("Ctrl + Left Click to Drop", WHITE)]


def _find(im):
    r = CL.read(im)
    assert r.get("checked"), r
    return r.get("chronicle")


class TheLineIsReadFromThePixels(unittest.TestCase):

    def test_an_eligible_tooltip_is_a_find_at_1440_and_at_800(self):
        """* THE POINT - the red line with the green line under it, on a full frame and on a stream-sized one"""
        w = _find(frame(ELIGIBLE))
        self.assertIsNotNone(w, "the Greaves tooltip (red Unidentified, green Eligible under it) was not a find")
        self.assertTrue(1.35 <= w["ratio"] <= 2.4, w)
        self.assertLess(w["red"]["box"][3], w["green"]["box"][1], "the green line is not UNDER the red one")
        self.assertIsNotNone(_find(frame(ELIGIBLE, size=(800, 450), scale=1, at=(560, 120))),
                             "at an 800x450 stream the same tooltip is missed")

    def test_the_ring_without_the_line_is_not_a_find(self):
        """BASELINE - his Ring: the red line, and no green line under it"""
        self.assertIsNone(_find(frame(RING)))

    def test_a_green_line_under_a_white_one_is_not_a_find(self):
        """an identified set item's green lines sit under white and blue lines, never under the red Unidentified"""
        self.assertIsNone(_find(frame([("Required Level: 45", WHITE), ("Eligible for Chronicle", GREEN)])))

    def test_a_green_line_above_the_red_one_is_not_a_find(self):
        self.assertIsNone(_find(frame([("Eligible for Chronicle", GREEN), ("Unidentified", RED)])))

    def test_a_green_line_far_below_is_not_a_find(self):
        self.assertIsNone(_find(frame([("Unidentified", RED), ("Eligible for Chronicle", GREEN)], gap=60)))

    def test_a_short_green_line_is_not_the_eligible_line(self):
        self.assertIsNone(_find(frame([("Unidentified", RED), ("Set", GREEN)])))

    def test_a_green_line_much_wider_than_the_red_one_is_not_the_eligible_line(self):
        """the width ratio is the line's name: a long green line (a set bonus's length) under a red one is not it"""
        self.assertIsNone(_find(frame([("Unidentified", RED), ("+10 to All Attributes (Two Items Worn)", GREEN)])))

    def test_the_lines_off_a_tooltip_ground_are_not_a_find(self):
        """the dark ground is what makes it a tooltip: the same two lines on a lit wall are not"""
        self.assertIsNone(_find(frame([("Unidentified", RED), ("Eligible for Chronicle", GREEN)],
                                      box=(120, 110, 100), ground=(120, 110, 100))))

    def test_his_screenshot_colours_are_in_the_bands_and_the_item_colours_are_not(self):
        import numpy as np
        a = np.array([[RED, GREEN, WHITE, GOLD, BLUE, BOX]], dtype=np.int16)
        red, green, dark = CL.masks(a)
        self.assertEqual(red[0].tolist(), [True, False, False, False, False, False])
        self.assertEqual(green[0].tolist(), [False, True, False, False, False, False])
        self.assertEqual(dark[0].tolist(), [False, False, False, False, False, True])

    def test_a_frame_that_will_not_open_is_unknown_never_a_no(self):
        r = CL.read(os.path.join(tempfile.gettempdir(), "no_such_frame_%d.jpg" % os.getpid()))
        self.assertFalse(r.get("checked"))
        self.assertNotIn("chronicle", r)


class TheLaneWalksEveryFrameOnce(unittest.TestCase):

    T0 = 1794000000000

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="chron_lane_")
        self.hist = os.path.join(self.tmp, "frames", "hist")
        self.old_env = os.environ.get("TV_CHRONICLE_LINES")
        os.environ["TV_CHRONICLE_LINES"] = os.path.join(self.tmp, ".chronicle_lines.json")
        # three reels, oldest first; the oldest holds the finds (two inventory sightings of one item, one more item,
        # one stash-side sighting), the newer two are plain. LIVE_REELS (2) newest reels are never marked done.
        self.reel = os.path.join(self.hist, "reel_s_%d_1" % self.T0)
        plain = frame(RING, jpeg=False)
        shots = [plain, frame(ELIGIBLE, at=(1000, 300), jpeg=False), frame(ELIGIBLE, at=(1000, 300), jpeg=False),
                 plain, frame(ELIGIBLE, at=(1180, 420), jpeg=False), frame(ELIGIBLE, at=(380, 300), jpeg=False), plain]
        self._write(self.reel, self.T0, shots)
        self._write(os.path.join(self.hist, "reel_s_%d_2" % (self.T0 + 600000)), self.T0 + 600000, [plain, plain])
        self._write(os.path.join(self.hist, "reel_s_%d_3" % (self.T0 + 900000)), self.T0 + 900000, [plain])

    def _write(self, d, t, shots):
        os.makedirs(d)
        for i, im in enumerate(shots):
            im.save(os.path.join(d, "f_%d.jpg" % (t + i * 1000)), "JPEG", quality=90)

    def tearDown(self):
        if self.old_env is None:
            os.environ.pop("TV_CHRONICLE_LINES", None)
        else:
            os.environ["TV_CHRONICLE_LINES"] = self.old_env
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_unknown_until_walked_then_the_distinct_inventory_finds(self):
        """* THE POINT - None before the lane walked the window; then 2 items (one hovered twice), the stash-side
        sighting left out, and every banked sighting has its proof frame beside the ledger"""
        t0, t1 = self.T0, self.T0 + 6000
        self.assertIsNone(CL.session_count(t0, t1, CL.load())[0], "a window nobody walked read as a measured count")
        st = CL.tick(root=self.hist, budget_s=120)
        self.assertTrue(st["ok"], st)
        self.assertEqual(st["scanned"], 10, "every frame of the three reels, once")
        self.assertEqual(st["hits"], 4, st)
        d = CL.load()
        n, why = CL.session_count(t0, t1, d)
        self.assertEqual(n, 2, "%s %s %s" % (n, why, [(h["ts"], h["side"], h["red"]) for h in d["hits"]]))
        self.assertEqual(sorted(h["side"] for h in d["hits"]), ["inventory"] * 3 + ["left-panel"])
        for h in d["hits"]:
            self.assertTrue(h.get("proof") and os.path.isfile(os.path.join(CL.proof_dir(), h["proof"])), h)
        self.assertTrue(d["reels"][os.path.basename(self.reel)].get("done"))

    def test_a_second_tick_reads_nothing_twice(self):
        CL.tick(root=self.hist, budget_s=120)
        again = CL.tick(root=self.hist, budget_s=120)
        self.assertEqual((again["scanned"], again["hits"]), (0, 0), again)
        self.assertEqual(len(CL.load()["hits"]), 4)

    def test_a_window_walked_only_part_way_stays_unknown(self):
        """the tick's budget ran out inside the oldest reel: its window is not walked, so it is not a number yet"""
        ticks = iter(range(1000))
        st = CL.tick(root=self.hist, budget_s=4.5, clock=lambda: float(next(ticks)), now_ms=1)
        self.assertEqual((st["scanned"], st["why"]), (4, "tick budget spent"), st)
        n, why = CL.session_count(self.T0, self.T0 + 6000, CL.load())
        self.assertIsNone(n, "a window the lane stopped inside read as a measured count")
        self.assertIn("not walked", why)

    def test_a_window_no_reel_filmed_stays_unknown(self):
        CL.tick(root=self.hist, budget_s=120)
        n, why = CL.session_count(self.T0 - 10 ** 8, self.T0 - 10 ** 7, CL.load())
        self.assertIsNone(n)
        self.assertIn("no reel", why)

    def test_a_walked_window_with_nothing_is_a_measured_zero(self):
        CL.tick(root=self.hist, budget_s=120)
        self.assertEqual(CL.session_count(self.T0 + 600000, self.T0 + 601000, CL.load())[0], 0)


class TheLaneIsJoined(unittest.TestCase):
    """The joints, read from the code that runs: the rider, the two call sites, the cache key, his own card."""

    @classmethod
    def setUpClass(cls):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            cls.app = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            cls.ui = js_strip.strip_js_comments(fh.read())

    def test_the_console_tick_rides_the_lane(self):
        i = self.app.index("_lane_tick('tvd-chronicle-lines', _VAULT_AUTOREAD_EVERY_S)")
        self.assertIn("_clr = _chl.tick()", self.app[i:i + 400])
        self.assertEqual(self.app.count("_lane_tick('tvd-chronicle-lines'"), 1)

    def test_both_session_call_sites_hand_this_consoles_count(self):
        self.assertEqual(self.app.count(
            "_route = _SSF.session_facts(sess, [r2 for r2 in sess if _is_a_live_read(r2)], _game_tl,\n"
            "                                            chron_count=_chronicle_count)"), 1)
        self.assertEqual(self.app.count(
            "witness_ids=_profile_picture_ids(stores),\n                   chron_count=_chronicle_count,"), 1)
        self.assertIn("return _chl.session_count(t0, t1)", self.app)

    def test_the_row_cache_moves_with_the_lanes_answer(self):
        i = self.app.index("def _theatre_row_fingerprint(")
        body = self.app[i:self.app.index("\ndef ", i + 10)]
        self.assertIn("chron_k = _chl.cache_key()", body)
        self.assertIn("os.path.abspath(str(hist_dir)), chron_k)", body)

    def test_his_own_card_reads_the_count_where_his_console_puts_it(self):
        self.assertIn("? sm.chroniclesFound : ((sm.route && typeof sm.route === 'object') ? sm.route.chroniclesFound : null);",
                      self.ui)

    def test_session_facts_takes_the_lanes_answer_when_the_route_has_none(self):
        import shadow_sessions as SS
        f = SS.session_facts([], [], [], chron_count=lambda a, b: (3, ""))
        self.assertEqual(f["chroniclesFound"], 3)
        f = SS.session_facts([], [], [], chron_count=lambda a, b: (None, "the chronicle lane has not walked it yet"))
        self.assertIsNone(f["chroniclesFound"])
        self.assertIn("not walked", f.get("chroniclesWhy", ""))
        self.assertIsNone(SS.session_facts([], [], [])["chroniclesFound"], "no lane handed: the route's UNKNOWN stands")


RED_PROOF = [
    {"why": "v3890 (#184) - a green line above the red one passes as the eligible line",
     "file": "tv/chronicle_line.py",
     "find": "            if gap < 0 or gap > 1.0 * r[\"h\"] + 3:\n",
     "replace": "            if gap > 1.0 * r[\"h\"] + 3 or gap < -10 * r[\"h\"]:\n",
     "matches": 1},
    {"why": "v3890 (#184) - any green line under a red one is a find, whatever its length",
     "file": "tv/chronicle_line.py",
     "find": "            if not (WIDTH_RATIO[0] <= ratio <= WIDTH_RATIO[1]):\n                continue\n",
     "replace": "",
     "matches": 1},
    {"why": "v3890 (#184) - two coloured lines on any ground pass for a tooltip",
     "file": "tv/chronicle_line.py",
     "find": "    if ground < MIN_DARK_GROUND:\n        return None\n",
     "replace": "",
     "matches": 1},
    {"why": "v3890 (#184) - the stash side counts as a find this run",
     "file": "tv/chronicle_line.py",
     "find": "        if (h.get(\"side\") or side_of(h)) != \"inventory\":\n            continue\n",
     "replace": "",
     "matches": 1},
    {"why": "v3890 (#184) - the cursor never moves: every tick re-reads every frame",
     "file": "tv/chronicle_line.py",
     "find": "            i += 1\n            rs[\"pos\"] = i\n",
     "replace": "            i += 1\n",
     "matches": 1},
    {"why": "v3890 (#184) - a window nobody walked reads as a measured count",
     "file": "tv/chronicle_line.py",
     "find": "        if int(rs.get(\"scannedTs\") or 0) < min(t1, rs[\"lastTs\"]):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "v3890 (#184) - one item hovered across frames counts once per frame",
     "file": "tv/chronicle_line.py",
     "find": "                    and h[\"ts\"] - it[\"lastTs\"] <= SAME_ITEM_GAP_MS):\n",
     "replace": "                    and h[\"ts\"] - it[\"lastTs\"] <= SAME_ITEM_GAP_MS and False):\n",
     "matches": 1},
    {"why": "v3890 (#184) - the console's tick never rides the lane",
     "file": "tv/control_app.py",
     "find": "                _lane_tick('tvd-chronicle-lines', _VAULT_AUTOREAD_EVERY_S)\n",
     "replace": "",
     "matches": 1},
    {"why": "v3890 (#184) - his own Sessions rows never ask the lane",
     "file": "tv/control_app.py",
     "find": "                                            chron_count=_chronicle_count)   # v3890 (#184) - THIS console's reels\n",
     "replace": "                                            )\n",
     "matches": 1},
    {"why": "v3890 (#184) - a cached row keeps its '?' after the lane walked its footage",
     "file": "tv/control_app.py",
     "find": "    return (str(sid), len(sess), last_ts, reel_mt, os.path.abspath(str(hist_dir)), chron_k)\n",
     "replace": "    return (str(sid), len(sess), last_ts, reel_mt, os.path.abspath(str(hist_dir)))\n",
     "matches": 1},
    {"why": "v3890 (#184) - his own card reads only the top level, where his console never puts the count",
     "file": "tv/control_ui.html",
     "find": "? sm.chroniclesFound : ((sm.route && typeof sm.route === 'object') ? sm.route.chroniclesFound : null);",
     "replace": "? sm.chroniclesFound : null;",
     "matches": 1},
    {"why": "v3890 (#184) - session_facts drops the lane's answer",
     "file": "tv/shadow_sessions.py",
     "find": "            chron, chron_why = chron_count(min(moments) if moments else None, max(moments) if moments else None)\n",
     "replace": "            chron_why = 'dropped'\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
