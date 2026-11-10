# -*- coding: utf-8 -*-
"""#148 - ONE SESSION, WHATEVER HE DOES IN IT: the stash, the inventory, a menu, an alt-tab.

His rule, 2026-10-01: "regardless it needs to know if im in a session even if i alt tabbed like thats still a session
for until 3 minutes goes by we said for it to disconnect right?", and "make sure ... they really are properly
configured ... we will soon pinpoint tests accurately and scenario by scenario so we know and see exactly what we are
feeding the console from every angle".

MEASURED on his Mac, 2026-10-01 20:00-20:10: four Boosteroid reels were sealed as "the launcher" 23 s to 2 min after
they opened. Their first reads, as the reader journalled them, were filed as stash / inventory / loot and named
Horadric Cube, Nokozan Relic, Storm Scarab, Thul Rune - the game, every one. The first-reads rule knew only zone
names, and his stash and inventory print none. Those reads are the fixtures below, verbatim except the session ids.

REG-1873, MEASURED on his ALT 2026-10-07: 0 of the 68 launcher seals that recorded what they were fed had a stash,
inventory, loot, town or chronicle read, and his real reads of 22:00-01:24 replayed through the judge never said
"launcher" in a session that held one. The hole was D2R's own LOBBY: forty minutes of it read as "transition" and were
sealed as the launcher. The film says lobby where the reads cannot, so a lobby on the film is the game.

What this law drives (the real functions, never a re-implementation):
  * tv_diablo.read_shows_the_game / first_reads_show_d2r_hud / reads_show_the_game - the verdict on what was FED
  * control_app.shadow_watch_tick - the 3-minute launcher grace, its reset, its pin to ONE reel, the seal
  * shadow_seals.jsonl - every seal row names its reel and quotes what the judge was fed; an open carries the pid
  * printer.seal_for - the river's IN station quotes those rows for the reel they name
  * the vocabulary - the reader's scenes are reel_segments' activities, one list
RED_PROOF below.
"""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

_WORLD = tempfile.mkdtemp(prefix="one_session_")
os.environ["TV_HIST"] = _WORLD
os.environ["TV_SESSIONS"] = os.path.join(_WORLD, "sessions.jsonl")

import control_app as ca  # noqa: E402
import printer as PR  # noqa: E402
import reel_segments as RS  # noqa: E402
import tv_diablo as tv  # noqa: E402

BARE = (2002, "Boosteroid · Boosteroid")


def _words():
    return set(ca._AREA_ACT)


#: the four reels' first content reads, as journalled on his Mac (2026-10-01 20:00:17 / 20:04:19 / 20:06:43 / 20:09:48)
HIS_STASH_READS = [
    [{"lane": "deep", "scene": "loot", "area": "", "names": ["ATrLZ"]},
     {"lane": "deep", "scene": "inventory", "area": "",
      "names": ["Horadric Cube", "Tome of Town Portal", "Tome of Identify"],
      "names_loc": {"Horadric Cube": "inventory", "Tome of Town Portal": "inventory"}},
     {"lane": "deep", "scene": "inventory", "area": "", "names": []}],
    [{"lane": "deep", "scene": "stash", "area": "", "names": ["Nokozan Relic"], "names_loc": {"Nokozan Relic": "stash"}},
     {"lane": "deep", "scene": "loot", "area": "", "names": ["mAGlC DAthA6t REDuCED IY"]},
     {"lane": "deep", "scene": "stash", "area": "", "names": ["Storm Scarab"], "names_loc": {"Storm Scarab": "stash"}}],
    [{"lane": "deep", "scene": "loot", "area": "", "names": ["tQUlREfflEWT"]},
     {"lane": "deep", "scene": "stash", "area": "",
      "names": ["Horazon's Legacy", "Horadric Cube", "Tome of Town Portal", "Tome of Identify"]},
     {"lane": "deep", "scene": "loot", "area": "", "names": ["INtREA5e mAXJmUm mANA 5f"]}],
    [{"lane": "deep", "scene": "loot", "area": "", "names": ["THUL"]},
     {"lane": "deep", "scene": "stash", "area": "", "names": ["Thul Rune"], "names_loc": {"Thul Rune": "stash"}},
     {"lane": "deep", "scene": "loot", "area": "", "names": ["OAmAfjt rteDVCEP FY 7"]}],
]
#: the launcher's own screens (the bare-window law's rows: the reader's fallback scene, the client's own words)
LAUNCH = [{"lane": "deep", "area": "", "scene": "gameplay", "names": ["Play"]},
          {"lane": "deep", "area": "", "scene": "gameplay", "names": ["Library"]},
          {"lane": "deep", "area": "", "scene": "gameplay", "names": ["Boosteroid"]}]
#: REG-1603 - a read that did not happen (the ALT's signed-out reader) and a black loading frame
ALT_FAILED = {"lane": "deep", "scene": "gameplay", "mode": "empty", "names": [], "area": ""}
ALT_BLACK = {"lane": "known", "scene": "transition", "mode": "near-black", "names": [], "area": ""}
STASH_LATER = {"lane": "deep", "scene": "stash", "area": "", "names": ["Arachnid Mesh"]}
#: REG-1873 - D2R's own lobby, as his ALT journalled it on 2026-10-06 22:00-22:40 (values kept, ids and times dropped):
#: two deep reads filed "transition" at conf 0.4 and one learned frame. No zone, panel or item - and not the launcher.
ALT_LOBBY_READS = [{"lane": "deep", "scene": "transition", "mode": "warm", "names": [], "area": "", "conf": 0.4},
                   {"lane": "known", "scene": "transition", "mode": "known", "names": [], "area": ""},
                   {"lane": "deep", "scene": "transition", "mode": "warm", "names": [], "area": "", "conf": 0.4}]
#: a 2017-epoch reel id: synthetic, so no case can ever be taken for one of his reels
SYNTH_SID = "s_1500000000001_4242"


class WhatTheJudgeIsFed(unittest.TestCase):
    """the verdict on the reads alone - no window, no clock"""

    def test_his_stash_and_inventory_reads_are_the_game(self):
        for i, reads in enumerate(HIS_STASH_READS):
            self.assertIs(tv.first_reads_show_d2r_hud(reads, words=_words()), True,
                          "reel %d: first reads filed as stash/inventory/loot were called the launcher" % (i + 1))

    def test_each_read_says_what_showed_the_game(self):
        why = [tv.read_shows_the_game(r, _words()) for r in HIS_STASH_READS[1]]
        self.assertEqual(why, ["a read filed as the stash", "a read filed as the loot", "a read filed as the stash"])
        self.assertEqual(tv.read_shows_the_game({"scene": "town", "area": "Kurast Docks"}, _words()),
                         "the zone Kurast Docks")

    def test_the_launchers_own_screens_are_still_the_launcher(self):
        self.assertIs(tv.first_reads_show_d2r_hud(LAUNCH, words=_words(), items=ca._game_items()), False)
        self.assertEqual([tv.read_shows_the_game(r, _words(), ca._game_items()) for r in LAUNCH], ["", "", ""])

    def test_a_read_that_did_not_happen_is_never_a_look(self):
        self.assertIsNone(tv.first_reads_show_d2r_hud([ALT_FAILED, ALT_BLACK, ALT_FAILED], words=_words()))
        self.assertIsNone(tv.reads_show_the_game([ALT_FAILED, ALT_BLACK], words=_words()))

    def test_an_item_names_the_game_even_on_the_readers_fallback_scene(self):
        relic = {"lane": "deep", "scene": "gameplay", "area": "", "names": ["Nokozan Relic"]}
        cube = {"lane": "deep", "scene": "gameplay", "area": "", "names": ["Horadric Cube"]}
        rune = {"lane": "deep", "scene": "gameplay", "area": "", "names": ["Ist Rune"]}
        self.assertEqual(tv.read_shows_the_game(relic, _words(), ca._game_items()), "the item Nokozan Relic")
        self.assertEqual(tv.read_shows_the_game(relic, _words(), None), "",
                         "a roster name proved the game with no roster handed in")
        self.assertEqual(tv.read_shows_the_game(cube, _words(), None), "the item Horadric Cube")
        self.assertEqual(tv.read_shows_the_game(rune, _words(), None), "the item Ist Rune")

    def test_any_later_read_keeps_the_reel_the_game(self):
        self.assertIs(tv.reads_show_the_game(LAUNCH + [STASH_LATER], words=_words()), True)
        self.assertIs(tv.reads_show_the_game(LAUNCH, words=_words()), False)
        self.assertIsNone(tv.reads_show_the_game(LAUNCH[:2], words=_words()), "two reads are not yet the launcher")

    def test_the_evidence_line_is_what_was_fed(self):
        self.assertEqual(tv.read_evidence(HIS_STASH_READS[0]),
                         ["loot · ATrLZ", "inventory · Horadric Cube, Tome of Town Portal, Tome of Identify", "inventory"])
        self.assertEqual(tv.read_evidence([ALT_FAILED] + LAUNCH), ["gameplay · Play", "gameplay · Library",
                                                                   "gameplay · Boosteroid"])

    def test_a_roster_that_failed_once_is_asked_again(self):
        """REG-1704 - a failed load answers empty and says why, and the NEXT ask after the retry window loads"""
        saved, saved_mod = dict(ca._GAME_ITEMS), sys.modules.get("item_identity")
        try:
            ca._GAME_ITEMS.clear()
            ca._GAME_ITEMS.update(set=None, why=None, failedAt=None)
            sys.modules["item_identity"] = None
            self.assertEqual(ca._game_items(), frozenset())
            self.assertIn("asked again", ca._GAME_ITEMS["why"] or "")
            if saved_mod is None:
                sys.modules.pop("item_identity", None)
            else:
                sys.modules["item_identity"] = saved_mod
            self.assertEqual(ca._game_items(), frozenset(), "inside the retry window it must not hammer the import")
            ca._GAME_ITEMS["failedAt"] = time.time() - ca._GAME_ITEMS_RETRY_S - 1
            got = ca._game_items()
            self.assertIn("arachnid mesh", got, "a roster that failed once stayed empty for the life of the console")
            self.assertIsNone(ca._GAME_ITEMS["why"])
        finally:
            ca._GAME_ITEMS.clear()
            ca._GAME_ITEMS.update(saved)
            if saved_mod is None:
                sys.modules.pop("item_identity", None)
            else:
                sys.modules["item_identity"] = saved_mod

    def test_a_roster_that_will_not_load_is_said_and_the_bases_still_judge(self):
        saved, saved_mod = dict(ca._GAME_ITEMS), sys.modules.get("item_identity")
        try:
            ca._GAME_ITEMS.update(set=None, why=None)
            sys.modules["item_identity"] = None
            got = ca._game_items()
            self.assertEqual(got, frozenset())
            self.assertIn("would not load", ca._GAME_ITEMS["why"] or "")
            self.assertTrue(tv.read_shows_the_game({"scene": "gameplay", "names": ["Horadric Cube"]}, _words(), got))
        finally:
            ca._GAME_ITEMS.clear()
            ca._GAME_ITEMS.update(saved)
            if saved_mod is None:
                sys.modules.pop("item_identity", None)
            else:
                sys.modules["item_identity"] = saved_mod


class OneVocabulary(unittest.TestCase):

    def test_the_readers_scenes_are_the_segmenters_activities(self):
        self.assertEqual(set(tv._HUD_SCENES), set(RS._ACTIVITY_LANE),
                         "the reader's scene words and reel_segments' activities drifted apart")

    def test_the_fallback_scenes_prove_nothing_alone(self):
        self.assertNotIn("gameplay", tv._GAME_PANEL_SCENES)
        self.assertNotIn("transition", tv._GAME_PANEL_SCENES)
        self.assertEqual(set(tv._GAME_PANEL_SCENES), {"stash", "inventory", "chronicle", "loot", "town"})


class _Proc(object):
    pid = 4242

    def poll(self):
        return None


class TheSessionLastsWhileTheGameIsShown(unittest.TestCase):
    """driven through the real shadow_watch_tick, with the finder, the agent and the reads stubbed"""

    STUBS = ("_shadow_state", "_agent_alive", "mini_state", "start_agent", "stop_agent", "_force_kill_all_agents",
             "_mini_sid", "_shadow_now_ms", "_screen_recording_ok_quick", "ON_AIR_FLOOR_GB", "_agent_proc",
             "_agent_origin", "_agent_since_ms", "_stop_inflight", "bare_content_reads", "reel_content_reads",
             "_shadow_hour_end_ms")

    def setUp(self):
        self.world = tempfile.mkdtemp(prefix="one_session_case_")
        self.addCleanup(shutil.rmtree, self.world, True)
        self._env = {k: os.environ.get(k) for k in ("TV_HIST", "TV_SESSIONS", "TV_CAPTURE")}
        os.environ["TV_HIST"] = self.world
        os.environ["TV_SESSIONS"] = os.path.join(self.world, "sessions.jsonl")
        os.environ["TV_CAPTURE"] = "auto"
        self._saved = {k: getattr(ca, k) for k in self.STUBS}
        self._finders = (tv.find_d2r_window_mac, tv.find_d2r_window_win)
        self.addCleanup(self._restore)
        self.now = int(time.time() * 1000)
        self.alive, self.reads, self.allreads = False, None, None
        self.sid = "s_%d_4242" % self.now
        self.starts, self.stops = [], []
        ca._shadow_state = lambda: {"on": True, "available": True, "recording": self.alive}
        ca._agent_alive = lambda: self.alive
        ca.mini_state = lambda: {"running": False}
        ca._shadow_now_ms = lambda: self.now
        ca._screen_recording_ok_quick = lambda: True
        ca.ON_AIR_FLOOR_GB = 0
        ca._mini_sid = lambda: self.sid
        ca._stop_inflight = False
        ca._agent_proc, ca._agent_origin, ca._agent_since_ms = None, "hand", None
        ca.start_agent = self._start
        ca.stop_agent = self._stop
        ca._force_kill_all_agents = lambda *a, **k: {"ok": True}
        ca.bare_content_reads = lambda: self.reads
        # REG-1704 - the wide scan reads the SAME journal as the first reads, so a reel's whole read list always holds
        # them. A default of None here modelled "the reel cannot be read" while its first reads could - and every case
        # leaned on that None becoming "the launcher", the very collapse the v3550 eye found.
        ca.reel_content_reads = lambda: self.allreads if self.allreads is not None else self.reads
        ca._shadow_hour_end_ms = lambda since: int(since) + 10 ** 9   # no clock hour ends inside a case
        tv.find_d2r_window_mac = lambda *a, **k: BARE
        tv.find_d2r_window_win = lambda *a, **k: BARE
        self.seals = os.path.join(ca._fixture_root_for_state(), "shadow_seals.jsonl")
        self.assertTrue(os.path.realpath(self.seals).startswith(os.path.realpath(self.world) + os.sep),
                        "the seal log is not in this case's world (%s)" % self.seals)

    def _restore(self):
        for k, v in self._saved.items():
            setattr(ca, k, v)
        tv.find_d2r_window_mac, tv.find_d2r_window_win = self._finders
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _start(self, *a, **k):
        self.starts.append(dict(k))
        self.begin(k.get("origin", "hand"))
        return {"ok": True, "msg": "started", "origin": k.get("origin", "hand"), "pid": 4242}

    def _stop(self, *a, **k):
        self.stops.append(dict(k))
        self.alive = False
        return {"ok": True, "msg": "session saved · off"}

    def begin(self, origin):
        ca._agent_proc = _Proc()
        ca._agent_origin = origin
        ca._agent_since_ms = self.now
        self.alive = True

    def tick(self, advance_s=0):
        self.now += int(advance_s * 1000)
        return ca.shadow_watch_tick()

    def rows(self):
        if not os.path.isfile(self.seals):
            return []
        with open(self.seals, encoding="utf-8") as fh:
            return [json.loads(ln) for ln in fh if ln.strip()]

    def test_his_stash_reels_are_never_sealed_as_the_launcher(self):
        for reads in HIS_STASH_READS:
            self.begin("shadow")
            self.reads = reads
            for _ in range(5):
                r = self.tick(60)
                self.assertFalse(r.get("cut"), r)
                self.assertFalse(r.get("launcher"), r)
        self.assertEqual(self.stops, [])

    def test_the_launcher_seals_only_after_three_minutes(self):
        self.begin("shadow")
        self.reads = LAUNCH
        r = self.tick()
        self.assertTrue(r.get("launcher"), r)
        self.assertFalse(r.get("cut"), r)
        r = self.tick(ca._SHADOW_AWAY_GRACE_S - 1)
        self.assertFalse(r.get("cut"), r)
        self.assertIn("%d s of %d" % (ca._SHADOW_AWAY_GRACE_S - 1, ca._SHADOW_AWAY_GRACE_S), r.get("why") or "")
        r = self.tick(2)
        self.assertTrue(r.get("cut"), r)
        self.assertEqual(self.stops, [{"farewell": False}])

    def film(self, kind, ages_s=(0, 1, 2)):
        """Write this reel's newest film frames: flat pictures char_select's lobby bands pass (the lobby) or refuse."""
        from PIL import Image
        d = os.path.join(self.world, "reel_" + self.sid)
        os.makedirs(d, exist_ok=True)
        s, v = {"lobby": (0.05, 0.19), "launcher": (0.80, 0.50)}[kind]
        for a in ages_s:
            im = Image.new("HSV", (320, 180), (170, int(s * 255), int(v * 255)))
            im.convert("RGB").save(os.path.join(d, "f_%d.jpg" % (self.now - int(a * 1000))), quality=95)

    def test_the_games_own_lobby_is_never_sealed_as_the_launcher(self):
        # REG-1873 - his ALT, 22:00-22:40: the lobby on screen for forty minutes, sealed as "the launcher"
        self.sid = SYNTH_SID
        self.begin("shadow")
        self.reads = ALT_LOBBY_READS
        for _ in range(6):
            self.film("lobby")
            r = self.tick(60)
            self.assertFalse(r.get("cut"), r)
            self.assertFalse(r.get("launcher"), "the D2R lobby was put on the launcher clock: %r" % r)
        self.assertEqual(self.stops, [])
        g = ca.shadow_game_detail(self.now)
        self.assertIs(g["game"], True, "the lobby read as no game on his screen: %r" % g)
        self.assertIn("D2R's own lobby", g["why"])

    def test_premise_the_same_reads_over_a_launchers_film_still_seal(self):
        self.sid = SYNTH_SID
        self.begin("shadow")
        self.reads = ALT_LOBBY_READS
        self.film("launcher")
        r = self.tick()
        self.assertTrue(r.get("launcher"), r)
        self.film("launcher")
        r = self.tick(ca._SHADOW_AWAY_GRACE_S + 1)
        self.assertTrue(r.get("cut"), "these reads over a launcher's film did not seal, so the lobby case shows nothing")
        self.assertEqual(self.stops, [{"farewell": False}])

    def test_a_film_with_no_fresh_frame_says_nothing(self):
        self.sid = SYNTH_SID
        self.begin("shadow")
        self.assertIsNone(ca.reel_film_shows_the_lobby(self.now), "a reel with no film was called a lobby or not")
        self.film("lobby", ages_s=(ca._LOBBY_FILM_FRESH_S + 5,))
        self.assertIsNone(ca.reel_film_shows_the_lobby(self.now), "a frame older than the window was taken as now")
        d = os.path.join(self.world, "reel_" + self.sid)
        with open(os.path.join(d, "f_%d.jpg" % self.now), "wb") as fh:
            fh.write(b"not a picture")
        self.assertIsNone(ca.reel_film_shows_the_lobby(self.now), "an unreadable frame was a verdict")
        self.film("lobby")
        self.assertIs(ca.reel_film_shows_the_lobby(self.now), True)
        self.film("launcher")
        self.assertIs(ca.reel_film_shows_the_lobby(self.now), False)
        # the stale lobby frame alone does not hold a launcher reel open
        self.reads = ALT_LOBBY_READS
        shutil.rmtree(d)
        self.film("lobby", ages_s=(ca._LOBBY_FILM_FRESH_S + 5,))
        self.tick()
        r = self.tick(ca._SHADOW_AWAY_GRACE_S + 1)
        self.assertTrue(r.get("cut"), "a lobby frame from minutes ago kept a launcher reel open: %r" % r)

    def test_a_read_that_shows_the_game_restarts_the_three_minutes(self):
        self.begin("shadow")
        self.reads = LAUNCH
        self.tick()
        self.tick(150)
        self.reads = HIS_STASH_READS[1]          # back from the menu: the stash is open
        r = self.tick(10)
        self.assertFalse(r.get("launcher"), r)
        self.reads = LAUNCH                       # the launcher again - a NEW three minutes, not the old one's tail
        r = self.tick(10)
        self.assertTrue(r.get("launcher"), r)
        self.assertFalse(r.get("cut"), "sealed on a grace that a game read had already ended")
        r = self.tick(ca._SHADOW_AWAY_GRACE_S - 5)
        self.assertFalse(r.get("cut"), r)
        r = self.tick(6)
        self.assertTrue(r.get("cut"), r)

    def test_a_later_read_in_the_reel_keeps_it_the_game(self):
        self.begin("shadow")
        self.reads = LAUNCH
        self.allreads = LAUNCH + [STASH_LATER]
        for _ in range(5):
            r = self.tick(60)
            self.assertFalse(r.get("launcher"), r)
            self.assertFalse(r.get("cut"), r)

    def test_a_clock_left_by_an_earlier_reel_never_seals_this_one(self):
        old = self.now - 3600 * 1000
        ca._shadow_watch_note(launcherSince=old, launcherFor=old)
        self.begin("shadow")
        self.reads = LAUNCH
        r = self.tick()
        self.assertFalse(r.get("cut"), "an hour-old launcher clock from another reel sealed a fresh one")
        self.assertTrue(r.get("launcher"), r)

    def test_his_own_session_is_never_sealed_for_this(self):
        self.begin("hand")
        self.reads = LAUNCH
        r = self.tick(ca._SHADOW_AWAY_GRACE_S + 60)
        self.assertFalse(r.get("cut"), r)
        self.assertEqual(self.stops, [])

    def test_the_seal_row_names_its_reel_and_what_was_fed(self):
        self.begin("shadow")
        self.reads = LAUNCH
        self.tick()
        self.tick(ca._SHADOW_AWAY_GRACE_S + 1)
        closes = [r for r in self.rows() if r.get("event") == "close"]
        self.assertEqual(len(closes), 1, self.rows())
        c = closes[0]
        self.assertEqual(c.get("reason"), "launcher")
        self.assertEqual(c.get("reel"), "reel_" + self.sid)
        self.assertEqual(c.get("fed"), ["gameplay · Play", "gameplay · Library", "gameplay · Boosteroid"])
        self.assertGreaterEqual(c.get("heldS"), ca._SHADOW_AWAY_GRACE_S)

    def test_a_wider_scan_nobody_could_read_never_seals(self):
        """REG-1704 - the first reads show nothing, and the whole reel cannot be read: UNKNOWN, never the launcher"""
        self.begin("shadow")
        self.reads = LAUNCH
        ca.reel_content_reads = lambda: (_ for _ in ()).throw(RuntimeError("journal unreadable"))
        for _ in range(6):
            r = self.tick(60)
            self.assertFalse(r.get("cut"), "a reel whose reads could not be read was sealed as the launcher: %r" % r)
        self.assertEqual(self.stops, [])

    def test_the_seal_row_says_what_the_whole_reel_showed(self):
        """REG-1704 - the close row carries how many reads were judged and which scenes they were"""
        self.begin("shadow")
        self.reads = LAUNCH
        self.allreads = LAUNCH + LAUNCH
        self.tick()
        self.tick(ca._SHADOW_AWAY_GRACE_S + 1)
        c = [r for r in self.rows() if r.get("event") == "close"][0]
        self.assertEqual(c.get("judged"), 6, c)
        self.assertEqual(c.get("scenes"), {"gameplay": 6}, c)
        self.assertIs(c.get("capped"), False)
        self.assertIn("judged 6 reads of this reel: gameplay 6", c.get("why") or "")

    def test_the_open_row_carries_the_agent_pid(self):
        self.reads = None
        r = self.tick()
        self.assertTrue(r.get("started"), r)
        opens = [x for x in self.rows() if x.get("event") == "open"]
        self.assertEqual(len(opens), 1, self.rows())
        self.assertEqual(opens[0].get("agentPid"), 4242)


class TheRiverQuotesTheDoor(unittest.TestCase):
    """printer.seal_for - the IN station's join, on rows shaped exactly as the console writes them"""

    BORN = 1790874403116
    REEL = "reel_s_%d_75286" % BORN

    def seals(self, *rows):
        return {"ok": True, "rows": list(rows), "why": ""}

    def test_a_close_joins_by_the_reel_it_names(self):
        got = PR.seal_for(self.seals({"event": "close", "reason": "launcher", "reel": self.REEL, "why": "w"}), self.REEL)
        self.assertEqual(got, {"opened": None, "closed": "launcher — w"})

    def test_an_open_joins_by_its_pid_and_its_moment(self):
        o = {"event": "open", "ts": self.BORN + 76, "agentPid": 75286, "why": "started a reel"}
        self.assertEqual(PR.seal_for(self.seals(o), self.REEL)["opened"], "started a reel")

    def test_an_open_from_another_pid_or_another_hour_does_not_join(self):
        other_pid = {"event": "open", "ts": self.BORN + 76, "agentPid": 75287, "why": "x"}
        other_hour = {"event": "open", "ts": self.BORN + 3600 * 1000, "agentPid": 75286, "why": "y"}
        self.assertEqual(PR.seal_for(self.seals(other_pid, other_hour), self.REEL), {"opened": None, "closed": None})

    def test_the_seal_path_follows_one_rule_when_tv_diablo_will_not_import(self):
        """REG-1708 (the v3553 eye) - the fallback arm resolves TV_HIST exactly as _fixture_root does"""
        saved_mod, saved_env = sys.modules.get("tv_diablo"), os.environ.get("TV_HIST")
        out = tempfile.mkdtemp(prefix="seal_root_")
        self.addCleanup(shutil.rmtree, out, True)
        try:
            sys.modules["tv_diablo"] = None
            os.environ["TV_HIST"] = os.path.join(PR.HERE, "frames", "hist")
            self.assertEqual(PR._seal_path(), os.path.join(PR.HERE, "shadow_seals.jsonl"),
                             "a TV_HIST inside his tree read a different seal log than the console writes")
            os.environ["TV_HIST"] = out
            self.assertEqual(PR._seal_path(), os.path.join(os.path.realpath(out), "shadow_seals.jsonl"))
        finally:
            if saved_mod is None:
                sys.modules.pop("tv_diablo", None)
            else:
                sys.modules["tv_diablo"] = saved_mod
            if saved_env is None:
                os.environ.pop("TV_HIST", None)
            else:
                os.environ["TV_HIST"] = saved_env

    def test_no_record_is_said_not_read_as_empty(self):
        d = tempfile.mkdtemp(prefix="seal_none_")
        self.addCleanup(shutil.rmtree, d, True)
        got = PR.shadow_seals(os.path.join(d, "shadow_seals.jsonl"))
        self.assertFalse(got["ok"])
        self.assertIn("written nothing", got["why"])


RED_PROOF = [
    {
        "why": "REG-1873 - the rolling path no longer asks the film, so the D2R lobby is sealed as the launcher again",
        "file": "control_app.py",
        "find": "                if hud is False and _lobby is True:\n",
        "replace": "                if False and _lobby is True:\n",
        "matches": 1,
    },
    {
        "why": "REG-1873 - the lobby witness never says lobby",
        "file": "control_app.py",
        "find": "    return sum(seen) * 2 > len(seen)\n",
        "replace": "    return False\n",
        "matches": 1,
    },
    {
        "why": "REG-1873 - a lobby frame from minutes ago counts as the screen now",
        "file": "control_app.py",
        "find": "             if 0 <= now - _film_ts(n) <= _LOBBY_FILM_FRESH_S * 1000]\n",
        "replace": "             ]\n",
        "matches": 1,
    },
    {
        "why": "REG-1708 - the seal path's fallback takes any absolute TV_HIST again, so his frames/hist reads a different log",
        "file": "printer.py",
        "find": "        if _h and os.path.isabs(_h) and not _inside_tree(_h, HERE):\n",
        "replace": "        if _h and os.path.isabs(_h):\n",
        "matches": 1,
    },
    {
        "why": "REG-1704 - a wider scan nobody could read seals the reel as the launcher again",
        "file": "control_app.py",
        "find": "    if _wide is None:\n        return None\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1704 - a roster that failed to load once is cached empty for the life of the console again",
        "file": "control_app.py",
        "find": "            _GAME_ITEMS[\"failedAt\"] = time.time()\n            return frozenset()\n",
        "replace": "            _GAME_ITEMS[\"set\"] = frozenset()\n            return frozenset()\n",
        "matches": 1,
    },
    {
        "why": "REG-1704 - the seal row stops saying how many reads of the reel were judged",
        "file": "control_app.py",
        "find": "                     judged=_judged, scenes=_scenes, capped=_capped, why=why)\n",
        "replace": "                     why=why)\n",
        "matches": 1,
    },
    {
        "why": "#148 - a read the reader filed as the stash/inventory/loot is no longer the game: his four reels seal again",
        "file": "tv_diablo.py",
        "find": "    if sc in _GAME_PANEL_SCENES:\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "#148 - a roster item on the reader's fallback scene no longer names the game",
        "file": "tv_diablo.py",
        "find": "if k in _D2R_ALWAYS_ITEMS or (items and k in items) or",
        "replace": "if k in _D2R_ALWAYS_ITEMS or False or",
        "matches": 1,
    },
    {
        "why": "#148 - the launcher seals on the second look again instead of after three minutes",
        "file": "control_app.py",
        "find": "                    _held = (now - float(_ls)) / 1000.0\n                    if _held < _SHADOW_AWAY_GRACE_S:\n",
        "replace": "                    _held = (now - float(_ls)) / 1000.0\n                    if False:\n",
        "matches": 1,
    },
    {
        "why": "#148 - a launcher clock left by an earlier reel seals the next reel on its first look",
        "file": "control_app.py",
        "find": "                    if not isinstance(_ls, (int, float)) or _lc.get(\"launcherFor\") != _since:\n",
        "replace": "                    if not isinstance(_ls, (int, float)):\n",
        "matches": 1,
    },
    {
        "why": "#148 - a read that shows the game no longer restarts the three minutes",
        "file": "control_app.py",
        "find": "                    _shadow_watch_note(launcherUntil=None, launcherSince=None, launcherFor=None)\n",
        "replace": "                    _shadow_watch_note(launcherUntil=None)\n",
        "matches": 1,
    },
    {
        "why": "#148 - a later read of the same reel no longer keeps it the game",
        "file": "control_app.py",
        "find": "    if _wide is True:\n        return True\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#148 - the launcher seal row no longer names its reel",
        "file": "control_app.py",
        "find": "    _shadow_seal_log(\"close\", reason=\"launcher\", reel=(\"reel_\" + _sid) if _sid else None,\n",
        "replace": "    _shadow_seal_log(\"close\", reason=\"launcher\", reel=None,\n",
        "matches": 1,
    },
    {
        "why": "#148 - the open row no longer carries the agent pid, so the river cannot say why a reel opened",
        "file": "control_app.py",
        "find": "                         agentPid=(r.get(\"pid\") if isinstance(r, dict) else None),\n",
        "replace": "                         agentPid=None,\n",
        "matches": 1,
    },
    {
        "why": "#148 - the river joins an open to any reel with the same pid, whatever hour it opened in",
        "file": "printer.py",
        "find": "and abs(int(r[\"ts\"]) - born) <= _SEAL_OPEN_JOIN_MS",
        "replace": "and True",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
