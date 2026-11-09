# -*- coding: utf-8 -*-
"""REG-1760 — the create-game lobby names the character, citing the frame.

Measured 2026-10-03, draft decode at 1/4, on reel_s_1790978096994 (Session 3, 3 Oct 00:55-01:00):
  lobby  f_1790978100063  full sat 0.158 val 0.192, bot val 0.183, right sat 0.083
  loading f_1790978357205 full sat 0.094 val 0.085, bot val 0.000, right sat 0.014
  skill   f_1790978399206 full sat 0.177 val 0.255, bot val 0.229, right sat 0.116
  play    f_1790978250101 full sat 0.596 val 0.156, bot val 0.170, right sat 0.556
The other dark runs in that reel are loading cards. No character-panel frame was filmed, so this law
pins no pixel band for it. A reader that says c-panel still banks. The jpegs are not on CI; the tuples
are. Accuracy is the joiner against a reader answer, not a name written into the detector.

ALT, 800x450, 2026-10-04, same draft and crops. A quiet lobby matches the Mac tuple. A lobby whose
chat is on screen is full sat 0.196 and was refused by 0.17. A skill tree at that size passes val,
bot and right sat, so full sat 0.22 is what keeps it out. Reels the char cursor had already finished
had no lobby cursor, so a match on disk still read as no lobby. The lane says checked and matched
per file size, and UNKNOWN until a size has been opened.

One lobby read per visit, on the same hourly cap as the character-select list, and the cap rewinds
onto the frame it did not read. The row is served on /api/chars_learned and painted in the in-game
section. One lobby frame does not teach the character.
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
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable
enable()

import char_select as C  # noqa: E402

NODE = shutil.which("node")
LOBBY = (0.158, 0.192, 0.183, 0.083)
LOADING = (0.094, 0.085, 0.0, 0.014)
SKILL = (0.177, 0.255, 0.229, 0.116)
PLAY = (0.596, 0.156, 0.170, 0.556)
ALT_QUIET = (0.158, 0.189, 0.182, 0.089)
ALT_CHAT = (0.196, 0.182, 0.153, 0.098)
ALT_SKILL = (0.323, 0.208, 0.155, 0.085)
# v3890 (#183) - MEASURED 11-09 over SSH on the two ALTs' own frames with lobby_stats (the four bands, then the lobby's panels:
# create-game pane value / spread, chat pane value / spread, top strip value), each frame opened and named by eye
WORK_ALT_LOBBY_810 = (0.216, 0.168, 0.120, 0.111, 0.180, 0.095, 0.169, 0.079, 0.224)    # LT-Issta 1440x810, Konyorian's lobby
WORK_ALT_LOBBY_450 = (0.230, 0.166, 0.121, 0.111, 0.179, 0.093, 0.178, 0.079, 0.224)    # LT-Issta 800x450, the same lobby
OLD_ALT_LOBBY_PANELS = (0.167, 0.185, 0.171, 0.101, 0.187, 0.089, 0.179, 0.062, 0.226)  # OLD ALT 800x450, right sat 0.101
OLD_ALT_DARK_STREET = (0.170, 0.175, 0.164, 0.113, 0.171, 0.100, 0.169, 0.061, 0.167)   # OLD ALT gameplay: panels pass, top dark
OLD_ALT_NIGHT_TOWN = (0.219, 0.209, 0.179, 0.101, 0.133, 0.059, 0.218, 0.106, 0.193)    # OLD ALT night town, a widened band's catch
BOOST_IDLE = (0.814, 0.187, 0.124, 0.843, 0.186, 0.049, 0.210, 0.070, 0.196)           # LT-Issta 1440x809 Boosteroid no-activity
BOOST_LIBRARY = (0.401, 0.234, 0.368, 0.320, 0.328, 0.204, 0.179, 0.207, 0.137)        # LT-Issta 800x449 Boosteroid library
WORK_ALT_PLAY = (0.284, 0.131, 0.159, 0.265, 0.097, 0.036, 0.099, 0.058, 0.091)        # LT-Issta 1440x810 play
PROOF = "f_1790978100063.jpg"
# A reader of that plaque. The detector never sees this. _clean_name titles an all-caps name.
PLAQUE = {"screen": "lobby", "name": "KONYOSSIN", "cls": "Assassin", "level": 90}


def _js_fn(src, sig):
    """The function whose header is the one occurrence of sig, bounded by its own braces."""
    n = src.count(sig)
    if n != 1:
        raise AssertionError("%r occurs %d times" % (sig, n))
    i = src.index(sig)
    b = src.index("{", i)
    depth = 0
    j = b
    while j < len(src):
        c = src[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
        j += 1
    raise AssertionError("could not bound %r" % sig)


class TheLobbyBands(unittest.TestCase):
    def test_the_measured_lobby_passes_and_the_screens_beside_it_do_not(self):
        ok, why = C.looks_like_lobby(LOBBY)
        self.assertTrue(ok, why)
        for tag, st in (("loading", LOADING), ("skill tree", SKILL), ("play", PLAY)):
            ok, why = C.looks_like_lobby(st)
            self.assertFalse(ok, "%s passed: %s" % (tag, why))
        self.assertEqual(C.looks_like_lobby(None), (False, "frame unreadable"))

    def test_the_alt_chatty_lobby_passes_and_the_alt_skill_tree_does_not(self):
        ok, why = C.looks_like_lobby(ALT_QUIET)
        self.assertTrue(ok, why)
        ok, why = C.looks_like_lobby(ALT_CHAT)
        self.assertTrue(ok, why)
        ok, why = C.looks_like_lobby(ALT_SKILL)
        self.assertFalse(ok, "the ALT skill tree passed: %s" % why)
        self.assertLess(ALT_CHAT[0], C.LOBBY_FULL_SAT_MAX)
        self.assertGreater(ALT_SKILL[0], C.LOBBY_FULL_SAT_MAX)

    def test_the_work_alts_own_lobby_passes_by_its_panels_and_nothing_else_does(self):
        """v3890 (#183) - his 11-09 "make sure its working and calliberated plaese". BASELINE first: the four bands alone
        refuse every lobby below (the work ALT learned no character from 9,427 frames at 1440x810); then the panels admit
        the three lobbies and refuse the gameplay a widened band let in, Boosteroid's screens and play"""
        for tag, st in (("work ALT 1440x810", WORK_ALT_LOBBY_810), ("work ALT 800x450", WORK_ALT_LOBBY_450),
                        ("OLD ALT", OLD_ALT_LOBBY_PANELS)):
            self.assertFalse(C.looks_like_lobby(st[:4])[0], "PREMISE: the bands alone already pass the %s lobby" % tag)
            ok, why = C.looks_like_lobby(st)
            self.assertTrue(ok, "the %s lobby is refused: %s" % (tag, why))
            self.assertIn("by its panels", why)
        for tag, st in (("a dark street (top strip)", OLD_ALT_DARK_STREET), ("night town", OLD_ALT_NIGHT_TOWN),
                        ("Boosteroid no-activity", BOOST_IDLE), ("Boosteroid library", BOOST_LIBRARY),
                        ("play at 1440x810", WORK_ALT_PLAY), ("the ALT skill tree", ALT_SKILL + (0.18, 0.09, 0.17, 0.07, 0.22)),
                        # each panel test alone: the lobby with ONE panel swapped for night town's measured one
                        ("a create-game pane that is not the lobby's grey", WORK_ALT_LOBBY_810[:4] + OLD_ALT_NIGHT_TOWN[4:6] + WORK_ALT_LOBBY_810[6:]),
                        ("a chat pane that is not the lobby's", WORK_ALT_LOBBY_810[:6] + OLD_ALT_NIGHT_TOWN[6:8] + WORK_ALT_LOBBY_810[8:])):
            ok, why = C.looks_like_lobby(st)
            self.assertFalse(ok, "%s passed as the lobby: %s" % (tag, why))
        self.assertIn("no game is drawn", C.LOBBY_SIZES_SEEN["1440x809"])
        self.assertIn("no game is drawn", C.LOBBY_SIZES_SEEN["800x449"])

    def test_a_count_that_has_not_started_is_not_a_zero(self):
        self.assertIsNone(C.lobby_by_size(None))
        self.assertIsNone(C.lobby_by_size(C._empty()))
        d = C._empty()
        d["stats"]["lobbyBySize"] = {"800x450": {"checked": 4, "matched": 1},
                                     "800x400": {"checked": 2, "matched": 0}}
        self.assertEqual(C.lobby_by_size(d), [
            {"size": "800x400", "checked": 2, "matched": 0, "seen": C.LOBBY_SIZES_SEEN["800x400"]},
            {"size": "800x450", "checked": 4, "matched": 1}])
        d["stats"]["lobbyBySize"] = {"bad": {"checked": 1, "matched": 2}}
        self.assertEqual(C.lobby_by_size(d), [])

    def test_a_size_that_never_matched_says_what_it_is_or_that_nobody_looked(self):
        # REG-1874 - "matched 0" at a size reads the same whether no game is drawn there or the bands are blind there
        d = C._empty()
        d["stats"]["lobbyBySize"] = {"800x420": {"checked": 965, "matched": 0},
                                     "1440x1327": {"checked": 17711, "matched": 0},
                                     "1024x600": {"checked": 7, "matched": 0},
                                     "800x450": {"checked": 118097, "matched": 10101},
                                     "640x480": {"checked": 0, "matched": 0}}
        rows = {r["size"]: r for r in C.lobby_by_size(d)}
        self.assertIn("Boosteroid's own window", rows["800x420"]["seen"])
        self.assertIn("GeForce NOW's own app", rows["1440x1327"]["seen"])
        self.assertEqual(rows["1024x600"]["seen"], C.LOBBY_SIZE_UNSEEN)
        self.assertIn("UNKNOWN", rows["1024x600"]["seen"])
        self.assertNotIn("seen", rows["800x450"], "a size where the lobby matched was given a verdict it did not need")
        self.assertNotIn("seen", rows["640x480"], "a size nobody checked was given a verdict")
        for size, said in C.LOBBY_SIZES_SEEN.items():
            w, h = size.split("x")
            self.assertTrue(int(w) > 0 and int(h) > 0, size)
            self.assertIn("no game is drawn at this size", said, "a looked-at size says something nobody measured")

    def test_there_is_no_character_panel_pixel_band(self):
        self.assertFalse(hasattr(C, "looks_like_c_panel"),
                         "a character-panel detector was added without a measured frame")

    def test_a_flat_plaque_passes_and_a_saturated_frame_does_not_and_garbage_is_unreadable(self):
        from PIL import Image
        d = tempfile.mkdtemp(prefix="lobby_px_")
        try:
            def flat(name, s, v):
                im = Image.new("HSV", (320, 200), (0, int(s * 255), int(v * 255)))
                p = os.path.join(d, name)
                im.convert("RGB").save(p, quality=95)
                return p
            yes = C.lobby_stats(flat("f_yes.jpg", 0.05, 0.19))
            no = C.lobby_stats(flat("f_no.jpg", 0.80, 0.50))
            self.assertTrue(C.looks_like_lobby(yes)[0], yes)
            self.assertFalse(C.looks_like_lobby(no)[0], no)
            junk = os.path.join(d, "f_junk.jpg")
            with open(junk, "wb") as fh:
                fh.write(b"no")
            self.assertIsNone(C.lobby_stats(junk))
        finally:
            shutil.rmtree(d, ignore_errors=True)


class TheSurfaceAnswer(unittest.TestCase):
    def test_the_plaque_answer_is_the_character_and_another_screen_banks_nothing(self):
        row, why = C.surface_of(PLAQUE)
        self.assertEqual(why, "one witness")
        self.assertEqual((row["name"], row["key"], row["cls"], row["level"], row["kind"]),
                         ("Konyossin", "konyossin", "Assassin", 90, "lobby"))
        other, owhy = C.surface_of({"screen": "other", "name": "KONYOSSIN", "cls": "Assassin", "level": 90})
        self.assertIsNone(other, "a gameplay misread was banked")
        self.assertEqual(owhy, "other screen")
        panel, _pwhy = C.surface_of({"screen": "c-panel", "name": "KONYOSSIN", "cls": "Assassin", "level": 90})
        self.assertEqual(panel["kind"], "c-panel")
        self.assertIsNone(C.surface_of({"note": "not read - subscription cap"})[0])
        self.assertIsNone(C.surface_of(None)[0])

    def test_one_image_is_one_row_and_the_two_kinds_add(self):
        d = C._empty()
        lobby, _w = C.surface_of(PLAQUE)
        C.bank_surface(d, lobby, PROOF, 1790978100063)
        C.bank_surface(d, lobby, PROOF, 1790978100063)
        ws = C.surface_witnesses(d)
        self.assertEqual(len(ws), 1, ws)
        self.assertEqual((ws[0]["image"], ws[0]["confluence"], ws[0]["name"]), (PROOF, 1.0, "Konyossin"))
        panel, _p = C.surface_of({"screen": "c-panel", "name": "KONYOSSIN", "cls": "Assassin", "level": 90})
        C.bank_surface(d, panel, "f_panel.jpg", 1790978200000)
        both = C.surface_witnesses(d)
        self.assertEqual(sorted(w["kind"] for w in both), ["c-panel", "lobby"])
        self.assertEqual({w["confluence"] for w in both}, {2.0})
        self.assertEqual(C.surface_confluence([{"kind": "lobby"}, {"kind": "snow"}]), 1.0)
        self.assertEqual(C.learned(d), [], "a surface witness taught a character")

    def test_a_witness_does_not_move_a_level_the_list_already_taught(self):
        d = C._empty()
        row = {"name": "Konyossin", "key": "konyossin", "cls": "Assassin", "level": 90, "title": None}
        C.record(d, "v1", [row], {"ts": 1})
        C.record(d, "v2", [row], {"ts": 2})
        lobby, _w = C.surface_of(PLAQUE)
        C.bank_surface(d, lobby, PROOF, 5)
        got = C.learned(d)[0]
        self.assertEqual((got["level"], got["visits"]), (90, 2))
        self.assertEqual(d["chars"]["konyossin"]["visitLevel"], {"v1": 90, "v2": 90})


class _Reel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="lobby_tick_")
        self.hist = os.path.join(self.tmp, "hist")
        self.store = os.path.join(self.tmp, "roster.json")
        os.environ["TV_CHARS_LEARNED"] = self.store
        self.called = []

    def tearDown(self):
        os.environ.pop("TV_CHARS_LEARNED", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _reel(self, frames):
        rd = os.path.join(self.hist, "reel_s_1500000000001_12001")
        os.makedirs(rd, exist_ok=True)
        for ts in frames:
            with open(os.path.join(rd, "f_%d.jpg" % ts), "wb") as fh:
                fh.write(b"no")
        return rd

    def _tick(self, stats_of, reader, **kw):
        return C.tick(root=self.hist, stats=lambda p: (0.9, 0.1, 0.9, 0.1),
                      reader=lambda crop: {"screen": "other"},
                      surface_stats=stats_of, surface_reader=reader,
                      now=kw.pop("now", 1000000.0), **kw)

    def test_one_lobby_visit_is_one_read_and_it_cites_the_frame(self):
        base = 1790978100063
        self._reel([base, base + 1000, base + 2000])

        def reader(p):
            self.called.append(os.path.basename(p))
            return dict(PLAQUE)

        r = self._tick(lambda p: LOBBY, reader)
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.called, [PROOF])
        self.assertEqual(r["surfaces"], 1)
        ws = C.surface_witnesses(C.load())
        self.assertEqual([(w["name"], w["cls"], w["level"], w["image"], w["kind"]) for w in ws],
                         [("Konyossin", "Assassin", 90, PROOF, "lobby")])
        self.assertEqual(C.learned(C.load()), [])
        again = self._tick(lambda p: LOBBY, reader)
        self.assertEqual(again["reads"], 0, "the same lobby visit was read again")

    def test_a_frame_that_is_not_the_lobby_is_not_read(self):
        self._reel([1790978250101])

        def reader(p):
            self.called.append(p)
            return dict(PLAQUE)

        r = self._tick(lambda p: PLAY, reader)
        self.assertEqual(self.called, [])
        self.assertEqual(r["reads"], 0)
        self.assertEqual(C.surface_witnesses(C.load()), [])

    def test_another_screen_spends_the_read_and_banks_nothing(self):
        self._reel([1790978100063])
        r = self._tick(lambda p: LOBBY, lambda p: {"screen": "other", "name": "KONYOSSIN"})
        self.assertEqual(r["reads"], 1)
        self.assertEqual(r["surfaces"], 0)
        self.assertEqual(C.surface_witnesses(C.load()), [])
        self.assertEqual(C.load()["stats"]["refused"], 0)

    def test_a_read_that_did_not_happen_is_tried_on_the_next_pass(self):
        self._reel([1790978100063])
        answers = [{"note": "the reader returned nothing"}, dict(PLAQUE)]

        def reader(p):
            self.called.append(os.path.basename(p))
            return answers.pop(0)

        r = self._tick(lambda p: LOBBY, reader)
        self.assertEqual(r["reads"], 0)
        self.assertEqual(r["surfaces"], 0)
        self.assertIn("surface not read", r["why"])
        d = C.load()
        self.assertEqual(d["stats"]["refused"], 0)
        self.assertEqual(d["stats"]["reads"], 0)
        self.assertEqual(d["reels"]["reel_s_1500000000001_12001"]["lobby"]["reads"], 0)
        self.assertGreater(C.owed(d, self.hist), 0)
        self.assertEqual(C.surface_witnesses(d), [])
        again = self._tick(lambda p: LOBBY, reader)
        self.assertEqual(again["surfaces"], 1)
        self.assertEqual(self.called, [PROOF, PROOF])
        self.assertEqual(C.surface_witnesses(C.load())[0]["name"], "Konyossin")

    def test_a_timeout_spends_the_hourly_cap_and_a_throttle_does_not(self):
        # REG-1941 - one lobby visit of four frames: a frame that keeps coming back empty is passed after
        # LOBBY_TRIES_PER_FRAME tries, so the cap is reached across the visit's frames, not on one frame for ever
        self._reel([1790978100063 + n * 1000 for n in range(4)])
        name = "reel_s_1500000000001_12001"

        def nothing(p):
            self.called.append(os.path.basename(p))
            return {"note": "the reader returned nothing"}

        for _ in range(C.READS_PER_HOUR):
            self._tick(lambda p: LOBBY, nothing)
        self.assertEqual(len(self.called), C.READS_PER_HOUR)
        d = C.load()
        self.assertEqual(len(d["stats"]["readTs"]), C.READS_PER_HOUR)
        self.assertEqual(d["stats"]["reads"], 0)
        self.assertEqual(d["reels"][name]["lobby"]["reads"], 0)
        stopped = self._tick(lambda p: LOBBY, nothing)
        self.assertIn("hourly read cap", stopped["why"])
        self.assertEqual(len(self.called), C.READS_PER_HOUR, "the cap asked the reader again")
        self.assertGreater(C.owed(C.load(), self.hist), 0)

        self.called = []
        os.environ["TV_CHARS_LEARNED"] = os.path.join(self.tmp, "throttle.json")

        def throttled(p):
            self.called.append(os.path.basename(p))
            return {"note": "reader throttled - not read"}

        for _ in range(3):
            self._tick(lambda p: LOBBY, throttled)
        t = C.load()
        self.assertEqual(t["stats"]["readTs"], [])
        self.assertEqual(t["reels"][name]["lobby"]["reads"], 0)
        self.assertEqual(len(self.called), 3)

    def test_an_answer_that_cannot_be_used_is_refused_and_not_retried(self):
        self._reel([1790978100063])

        def reader(p):
            self.called.append(os.path.basename(p))
            return [1, 2]

        r = self._tick(lambda p: LOBBY, reader)
        self.assertEqual(r["reads"], 0)
        self.assertEqual(C.load()["stats"]["refused"], 1)
        self.assertEqual(C.load()["reels"]["reel_s_1500000000001_12001"]["lobby"]["reads"], 1)
        self._tick(lambda p: LOBBY, reader)
        self.assertEqual(self.called, [PROOF])

    def test_the_hourly_cap_leaves_the_unread_lobby_frame_owed(self):
        base = 1790978100000
        # nine lobby visits, a hundred seconds apart: the ninth meets the cap
        self._reel([base + n * 100000 for n in range(C.READS_PER_HOUR + 1)])

        def reader(p):
            self.called.append(os.path.basename(p))
            return dict(PLAQUE)

        r = self._tick(lambda p: LOBBY, reader)
        self.assertEqual(r["reads"], C.READS_PER_HOUR)
        self.assertIn("hourly read cap", r["why"])
        d = C.load()
        name = "reel_s_1500000000001_12001"
        self.assertLess(d["reels"][name]["pos"], C.READS_PER_HOUR + 1,
                        "the cap walked past the lobby frame it did not read")
        self.assertGreater(C.owed(d, self.hist), 0)
        self.assertEqual(len(C.surface_witnesses(d)), C.READS_PER_HOUR)
        later = self._tick(lambda p: LOBBY, reader, now=1000000.0 + 3601)
        self.assertGreater(later["reads"], 0, "the next hour did not read the lobby frame the cap held")
        self.assertEqual(len(C.surface_witnesses(C.load())), C.READS_PER_HOUR + 1)

    def test_a_finished_reel_is_lobby_checked_and_counted_by_its_file_size(self):
        base = 1790634727494
        self._reel([base, base + 1000])
        name = "reel_s_1500000000001_12001"
        d = C._empty()
        d["reels"][name] = {"pos": 2, "frames": 2, "open": None}
        C.save(d)

        def reader(p):
            self.called.append(os.path.basename(p))
            return dict(PLAQUE)

        r = self._tick(lambda p: LOBBY, reader, size_of=lambda p: (800, 450))
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.called, ["f_%d.jpg" % base])
        got = C.lobby_by_size(C.load())
        self.assertEqual(got, [{"size": "800x450", "checked": 2, "matched": 2}])
        self.assertEqual(C.load()["reels"][name]["pos"], 2, "the char cursor was reopened")
        again = self._tick(lambda p: LOBBY, reader, size_of=lambda p: (800, 450))
        self.assertEqual(again["reads"], 0)
        self.assertEqual(self.called, ["f_%d.jpg" % base])
        self.assertEqual(C.lobby_by_size(C.load()), [{"size": "800x450", "checked": 2, "matched": 2}])

    def test_the_half_budget_stops_the_backfill_before_it_spends_the_tick(self):
        base_ts = 1790634727494
        rd = self._reel([base_ts])
        name = os.path.basename(rd)
        d = C._empty()
        d["reels"][name] = {"pos": 1, "frames": 1, "open": None}
        st = d["stats"]
        acc = {"reads": 0, "surfaces": 0, "why": "", "stop": False}
        t0 = 5000.0

        def reader(p):
            self.called.append(os.path.basename(p))
            return dict(PLAQUE)

        C._lobby_backfill(
            d, [rd], lambda p: (0.9, 0.1, 0.9, 0.1), lambda p: LOBBY, reader,
            lambda p: (800, 450), st, 1000000.0, t0, 2.0, lambda: t0 + 1.2, acc)
        self.assertEqual(self.called, [])
        self.assertFalse(acc["stop"])
        self.assertEqual(acc["why"], "")
        self.assertEqual(int(d["reels"][name].get("lobbyPos") or 0), 0)

    def test_a_frame_that_is_not_the_lobby_is_checked_and_not_matched(self):
        self._reel([1790978250101])

        def reader(p):
            self.called.append(p)
            return dict(PLAQUE)

        self._tick(lambda p: PLAY, reader, size_of=lambda p: (800, 450))
        self.assertEqual(self.called, [])
        self.assertEqual(C.lobby_by_size(C.load()), [{"size": "800x450", "checked": 1, "matched": 0,
                                                       "seen": C.LOBBY_SIZE_UNSEEN}])

    def test_an_unreadable_size_is_not_a_zero_row(self):
        self._reel([1790978100063])
        self._tick(lambda p: LOBBY, lambda p: dict(PLAQUE), size_of=lambda p: None)
        self.assertIsNone(C.lobby_by_size(C.load()))

    def test_a_list_frame_is_not_counted_as_a_lobby_check(self):
        self._reel([1790675069096])
        r = C.tick(root=self.hist, stats=lambda p: (0.03, 0.36, 0.10, 0.20),
                   reader=lambda crop: {"screen": "other"},
                   surface_stats=lambda p: LOBBY, surface_reader=lambda p: dict(PLAQUE),
                   size_of=lambda p: (800, 450), now=1000000.0)
        self.assertTrue(r["ok"], r)
        self.assertIsNone(C.lobby_by_size(C.load()))


class TheRoutePaintsTheRow(unittest.TestCase):
    def test_the_chars_route_returns_the_rows_and_the_in_game_section_paints_them(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            app = fh.read()
        self.assertEqual(app.count('"surfaceWitnesses": _cs.surface_witnesses(_d)'), 1)
        self.assertEqual(app.count('"lobbyBySize": _cs.lobby_by_size(_d)'), 1)
        self.assertEqual(app.count('"cPanel": _cs.CPANEL_SAY'), 1)
        self.assertEqual(app.count('"gear": _gear, "gearWhy": _gwhy})'), 1,
                         "the gear line the card test reads was moved")
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            page = fh.read()
        self.assertEqual(page.count("function _surfaceWitnessHtml()"), 1)
        self.assertEqual(page.count("function _lobbySizeHtml()"), 1)
        ing = page.index('data-sec="ingame"')
        sim = page.index("</div></section>';", ing)   # v3855 item D: the in-game section now ends the room
        call = page.index("_surfaceWitnessHtml()", ing)
        self.assertLess(call, sim, "the in-game section does not paint the witness rows")
        size_call = page.index("_lobbySizeHtml()", ing)
        self.assertLess(size_call, sim, "the in-game section does not paint the lobby counts")
        fn = _js_fn(page, "function _surfaceWitnessHtml()")
        fn = _js_fn(page, "function _dumpOpen(key)") + "\n" + _js_fn(page, "function _dumpWrap(key, sub, summary, body)") + "\n" + fn   # v3855 the dumps fold
        self.assertIn("surfaceWitnesses", fn)
        if not NODE:
            self.skipTest("node is required to run the page function")
        learned = {"ok": True, "surfaceWitnesses": [{
            "name": "Konyossin", "cls": "Assassin", "level": 90, "kind": "lobby",
            "image": PROOF, "confluence": 1.0}]}
        out = _paint(fn, learned)
        self.assertIn('data-kind="lobby"', out)
        self.assertIn('data-image="%s"' % PROOF, out)
        self.assertIn("Konyossin", out)
        self.assertIn("confluence 1", out)
        self.assertEqual(_paint(fn, {"ok": True, "surfaceWitnesses": []}), "")
        self.assertEqual(_paint(fn, {"ok": True, "chars": []}), "")
        self.assertEqual(_paint(fn, {"ok": False, "surfaceWitnesses": None}), "")
        self.assertEqual(_paint(fn, {"ok": True, "surfaceWitnesses": [
            {"name": "Konyossin", "kind": "lobby"}]}), "")

    def test_the_lane_says_checked_against_matched_per_size_and_the_panel_is_reader_only(self):
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            page = fh.read()
        if not NODE:
            self.skipTest("node is required to run the page function")
        fn = _js_fn(page, "function _lobbySizeHtml()")
        fn = _js_fn(page, "function _dumpOpen(key)") + "\n" + _js_fn(page, "function _dumpWrap(key, sub, summary, body)") + "\n" + fn   # v3855 the dumps fold
        self.assertIn("data-cpanel", fn)
        unknown = _paint_size(fn, {"ok": True, "lobbyBySize": None, "cPanel": C.CPANEL_SAY})
        self.assertIn('data-lobby-sizes="unknown"', unknown)
        self.assertIn("UNKNOWN", unknown)
        self.assertNotIn("matched 0", unknown)
        self.assertIn('data-cpanel="reader-only"', unknown)
        self.assertIn("no pixel band", unknown)
        none = _paint_size(fn, {"ok": True, "lobbyBySize": [], "cPanel": C.CPANEL_SAY})
        self.assertIn('data-lobby-sizes="none"', none)
        self.assertNotIn("matched 0", none)
        counted = _paint_size(fn, {"ok": True, "lobbyBySize": [
            {"size": "800x450", "checked": 4, "matched": 1}], "cPanel": C.CPANEL_SAY})
        self.assertIn('data-size="800x450"', counted)
        self.assertIn("checked 4", counted)
        self.assertIn("matched 1", counted)
        self.assertNotIn("800x400", counted)
        self.assertNotIn("data-seen", counted, "a size where the lobby matched printed a verdict")
        zero = _paint_size(fn, {"ok": True, "lobbyBySize": [
            {"size": "800x400", "checked": 9733, "matched": 0, "seen": C.LOBBY_SIZES_SEEN["800x400"]},
            {"size": "1024x600", "checked": 7, "matched": 0, "seen": C.LOBBY_SIZE_UNSEEN}], "cPanel": C.CPANEL_SAY})
        self.assertEqual(zero.count("data-seen"), 2, zero)
        self.assertIn("no game is drawn at this size", zero)
        self.assertIn("whether the bands see the lobby here is UNKNOWN", zero)
        self.assertEqual(_paint_size(fn, {"ok": False, "lobbyBySize": None}), "")

    def test_the_list_prompt_still_refuses_a_frame_that_is_not_the_list(self):
        with io.open(os.path.join(HERE, "tv_diablo.py"), encoding="utf-8") as fh:
            src = fh.read()
        a = src.index("CHARSEL_READ_PROMPT = (")
        b = src.index("SURFACE_READ_PROMPT = (", a)
        c = src.index("def surface_read(", b)
        charsel = src[a:b]
        surface = src[b:c]
        self.assertIn('{"screen":"other","chars":[]}', charsel)
        self.assertNotIn("c-panel", charsel)
        self.assertIn('{"screen":"lobby"', surface)
        self.assertIn('{"screen":"c-panel"', surface)
        self.assertIn('{"screen":"other"}', surface)


def _paint_size(fn, learned):
    drv = (
        "function esc(s){ return String(s == null ? '' : s); }\n"
        "var window = { _cbLearnedNow: function(){ return LEARNED; } };\n"
        "var LEARNED = %s;\n"
        "%s\n"
        "process.stdout.write(_lobbySizeHtml());\n"
    ) % (json.dumps(learned), fn)
    r = subprocess.run([NODE, "-"], input=drv, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-500:] or r.stdout[-500:])
    return r.stdout


def _paint(fn, learned):
    drv = (
        "function esc(s){ return String(s == null ? '' : s); }\n"
        "var window = { _cbLearnedNow: function(){ return LEARNED; } };\n"
        "var LEARNED = %s;\n"
        "%s\n"
        "process.stdout.write(_surfaceWitnessHtml());\n"
    ) % (json.dumps(learned), fn)
    r = subprocess.run([NODE, "-"], input=drv, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-500:] or r.stdout[-500:])
    return r.stdout


RED_PROOF = [
    {"why": "v3890 (#183) - the panel path is gone: the work ALT's lobby is refused again and it learns no character",
     "file": "tv/char_select.py",
     "find": "    if len(stats) == 9:\n        rv, rsd, lv, lsd, tv = stats[4:]\n",
     "replace": "    if False:\n        rv, rsd, lv, lsd, tv = stats[4:]\n",
     "matches": 1},
    {"why": "v3890 (#183) - the top strip is not asked: a dark street with lobby-grey panels passes as the lobby",
     "file": "tv/char_select.py",
     "find": "                and tv > LOBBY_PANEL_TOP_VAL_MIN):\n",
     "replace": "                and True):\n",
     "matches": 1},
    {"why": "v3890 (#183) - the panels are not asked: the widened colour limits let night-town gameplay in",
     "file": "tv/char_select.py",
     "find": "                and LOBBY_PANEL_RIGHT_VAL[0] < rv < LOBBY_PANEL_RIGHT_VAL[1] and LOBBY_PANEL_RIGHT_SD[0] < rsd < LOBBY_PANEL_RIGHT_SD[1]\n",
     "replace": "\n",
     "matches": 1},
    {"why": "v3890 (#183) - the Boosteroid sizes read as UNKNOWN again though they were opened",
     "file": "tv/char_select.py",
     "find": "    \"1440x809\": \"Boosteroid's own window (its no-activity screen) - no game is drawn at this size\",\n",
     "replace": "",
     "matches": 1},
    {
        "why": "REG-1874 - a size that never matched says nothing again, so matched 0 reads as no lobby",
        "file": "char_select.py",
        "find": "            row[\"seen\"] = LOBBY_SIZES_SEEN.get(str(key)) or LOBBY_SIZE_UNSEEN\n",
        "replace": "            pass\n",
        "matches": 1,
    },
    {
        "why": "REG-1874 - a size nobody looked at loses its UNKNOWN",
        "file": "char_select.py",
        "find": "LOBBY_SIZES_SEEN.get(str(key)) or LOBBY_SIZE_UNSEEN",
        "replace": "LOBBY_SIZES_SEEN.get(str(key))",
        "matches": 1,
    },
    {
        "why": "REG-1874 - the page drops what a zero-match size is",
        "file": "bible.html",
        "find": "((typeof r.seen === 'string' && r.seen) ? '<span data-seen>' + esc(r.seen) + '.</span>' : '')",
        "replace": "''",
        "matches": 1,
    },
    {
        "why": "the half budget compares elapsed seconds to an absolute deadline, so the backfill never stops",
        "file": "tv/char_select.py",
        "find": "if clock() > deadline:\n",
        "replace": "if clock() - t0 > deadline:\n",
        "matches": 2,
    },
    {
        "why": "REG-1764 - a count that has not started is reported as matched nothing",
        "file": "tv/char_select.py",
        "find": "    if not isinstance(stt, dict) or \"lobbyBySize\" not in stt:\n        return None\n",
        "replace": "    if not isinstance(stt, dict) or \"lobbyBySize\" not in stt:\n        return []\n",
        "matches": 1,
    },
    {
        "why": "REG-1764 - the chatty ALT lobby is refused again by the Mac saturation cap",
        "file": "tv/char_select.py",
        "find": "LOBBY_FULL_SAT_MAX = 0.22\n",
        "replace": "LOBBY_FULL_SAT_MAX = 0.17\n",
        "matches": 1,
    },
    {
        "why": "REG-1764 - an uncounted size is painted as matched 0",
        "file": "bible.html",
        "find": "      bits = '<p data-lobby-sizes=\"unknown\">Lobby checked against matched, per frame size, is UNKNOWN. This console has not counted yet.</p>';\n",
        "replace": "      bits = '<p data-lobby-sizes=\"unknown\">Lobby at 800x450: checked 0, matched 0.</p>';\n",
        "matches": 1,
    },
    {
        "why": "REG-1760 - the loading card passes the lobby bands once val and the bottom strip are not required",
        "file": "tv/char_select.py",
        "find": "    ok = (fs < LOBBY_FULL_SAT_MAX and LOBBY_FULL_VAL[0] < fv < LOBBY_FULL_VAL[1]\n"
                "          and bv > LOBBY_BOT_VAL_MIN and rs < LOBBY_RIGHT_SAT_MAX)\n",
        "replace": "    ok = (fs < LOBBY_FULL_SAT_MAX and rs < LOBBY_RIGHT_SAT_MAX)\n",
        "matches": 1,
    },
    {
        "why": "REG-1760 - a frame the reader called another screen is banked as the lobby",
        "file": "tv/char_select.py",
        "find": "    if not kind:\n        return None, \"other screen\"\n",
        "replace": "    if not kind:\n        kind = \"lobby\"\n",
        "matches": 1,
    },
    {
        "why": "REG-1760 - banking the same frame twice stores two rows",
        "file": "tv/char_select.py",
        "find": "        if isinstance(w, dict) and w.get(\"kind\") == kind and w.get(\"image\") == image:\n"
                "            return w\n",
        "replace": "        if False and isinstance(w, dict) and w.get(\"kind\") == kind and w.get(\"image\") == image:\n"
                   "            return w\n",
        "matches": 1,
    },
    {
        "why": "REG-1760 - the hourly cap walks the cursor past the lobby frame it did not read",
        "file": "tv/char_select.py",
        "find": "def _rewind_unread(rs, i):\n"
                "    \"\"\"The frame was not read. The cursor waits on it.\"\"\"\n"
                "    rs[\"pos\"] = i - SAMPLE_EVERY\n",
        "replace": "def _rewind_unread(rs, i):\n"
                   "    \"\"\"The frame was not read. The cursor waits on it.\"\"\"\n"
                   "    return\n",
        "matches": 1,
    },
    {
        "why": "REG-1761 - a lobby read that did not happen is kept and never retried",
        "file": "tv/char_select.py",
        # REG-1941 re-anchored: the per-frame bound now sits between the spend and the rewind
        "find": "            if _surface_unread(raw):\n"
                "                if _surface_call_was_spent(raw):\n"
                "                    st[\"readTs\"].append(now_s)\n"
                "                if not _surface_later(raw) and _lobby_tries(rs, p) >= LOBBY_TRIES_PER_FRAME:\n",
        "replace": "            if False and _surface_unread(raw):\n"
                   "                if _surface_call_was_spent(raw):\n"
                   "                    st[\"readTs\"].append(now_s)\n"
                   "                if not _surface_later(raw) and _lobby_tries(rs, p) >= LOBBY_TRIES_PER_FRAME:\n",
        "matches": 1,
    },
    {
        "why": "REG-1762 - a lobby timeout retries forever and never spends the hourly cap",
        "file": "tv/char_select.py",
        "find": "            if _surface_unread(raw):\n"
                "                if _surface_call_was_spent(raw):\n"
                "                    st[\"readTs\"].append(now_s)\n",
        "replace": "            if _surface_unread(raw):\n"
                   "                if False and _surface_call_was_spent(raw):\n"
                   "                    st[\"readTs\"].append(now_s)\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
