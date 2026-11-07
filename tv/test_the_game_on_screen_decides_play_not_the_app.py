# -*- coding: utf-8 -*-
"""REG-1666 - a cloud client is play only while the GAME is on his screen; the game itself is play while it runs.

His words, 2026-10-01: "it needs to like register when im ingame and playing not just when its open", and "make sure
this logic is known to all routes... like nvidea play and also the local way of playing the game the way dean usually
plays on his PC". MEASURED on his ALT that morning: the self-prove lane read Boosteroid as "playing" from 02:29 to 10:49
(178 proofs owed) while the shadow watch said the launcher was on screen, and the app in the tray held 2,190 MB private
bytes - more than a live stream - so no memory bar could ever tell idle from playing.

THE ROUTES, each driven below:
  - the game itself, D2R.exe (Battle.net on his PC and on Dean's, CrossOver on the Mac): play while it runs, at its
    menu too - exclusive fullscreen can hide its window from the walk. Battle.net alone is a launcher, never play.
  - Boosteroid: the tray (no window) and the launcher (no D2R HUD word in the first reads) are not play; the game is.
  - GeForce NOW: its library (a window that does not name the game) is not play; a stream titled with the game is.
  - nobody could look, the look is stale, the shadow reader is off: a cloud client counts as playing (never a guess).

The one judge of "is the game on his screen" is the shadow watch (control_app); the prover asks it through
_sp_playing_here. The Windows process walk is the real tv_diablo._toolhelp_any over a stubbed kernel32; the Mac
listing is a stubbed `ps`. Nothing here touches his machine.

RED_PROOF below.
"""
import ctypes
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

_WORLD = tempfile.mkdtemp(prefix="game_on_screen_")
os.environ["TV_HIST"] = _WORLD
os.environ["TV_SESSIONS"] = os.path.join(_WORLD, "sessions.jsonl")

import control_app as ca  # noqa: E402
import self_prove as SP  # noqa: E402
import tv_diablo as tv  # noqa: E402

BARE = (2002, "Boosteroid · Boosteroid")
GAME = (4004, "Diablo II: Resurrected")
GFN_STREAM = (5005, "GeForce NOW · GeForceNOW · Diablo II: Resurrected on GeForce NOW")
ZONE = [{"area": "Cold Plains", "scene": "gameplay", "names": []}]
LAUNCH = [
    {"area": "", "scene": "gameplay", "names": ["Play"]},
    {"area": "", "scene": "gameplay", "names": ["Library"]},
    {"area": "", "scene": "gameplay", "names": ["Boosteroid"]},
]


def _pre(seen, label=""):
    return {"windowSeen": seen, "windowLabel": label}


class TheVerdictForEveryRoute(unittest.TestCase):
    """_game_verdict - one look's answer to "is the GAME on his screen", for every way he plays."""

    def test_no_game_window_is_not_play(self):
        game, why = ca._game_verdict(_pre(False), None)
        self.assertIs(game, False, "a desktop with no game window (Boosteroid in the tray, GeForce NOW on its "
                                   "library, the game shut) was not called 'not on screen': %r" % why)

    def test_a_look_that_did_not_happen_is_unknown(self):
        self.assertIsNone(ca._game_verdict(_pre(None), None)[0], "a finder that could not look was read as an answer")
        off = dict(_pre(False), windowLooked=False)
        self.assertIsNone(ca._game_verdict(off, None)[0],
                          "a console that never looks (capture off) was read as 'no game on screen'")

    def test_a_window_that_names_the_game_is_play(self):
        self.assertIs(ca._game_verdict(_pre(True, GAME[1]), None)[0], True, "the game's own window was not play")
        self.assertIs(ca._game_verdict(_pre(True, GFN_STREAM[1]), None)[0], True,
                      "a GeForce NOW stream titled with the game was not play")

    def test_boosteroid_on_its_launcher_is_not_play(self):
        game, why = ca._game_verdict(_pre(True, BARE[1]), False)
        self.assertIs(game, False, "Boosteroid's launcher (first reads with no D2R HUD word) read as the game")
        self.assertIn("launcher", why)

    def test_boosteroid_with_the_hud_is_play(self):
        self.assertIs(ca._game_verdict(_pre(True, BARE[1]), True)[0], True)

    def test_boosteroid_before_its_first_reads_is_unknown(self):
        self.assertIsNone(ca._game_verdict(_pre(True, BARE[1]), None, relook_open=True)[0],
                          "a bare Boosteroid window nobody has read yet was guessed")

    def test_the_wait_after_a_launcher_verdict_is_not_play(self):
        self.assertIs(ca._game_verdict(_pre(True, BARE[1]), None, relook_open=False)[0], False,
                      "the launcher verdict of the last reads (under %d s ago) was forgotten" % ca._BARE_HUD_RELOOK_S)


class TheVerdictIsOnlyAsGoodAsItsAge(unittest.TestCase):

    def setUp(self):
        self.saved = ca._SHADOW_GAME.get("v")
        self.addCleanup(lambda: ca._SHADOW_GAME.__setitem__("v", self.saved))

    def test_a_fresh_look_answers(self):
        now = 1_790_000_000_000
        ca._shadow_game_note(now, False, "no game window")
        self.assertIs(ca.shadow_game_on_screen(now + 1000), False)
        ca._shadow_game_note(now, True, "the game")
        self.assertIs(ca.shadow_game_on_screen(now + 1000), True)

    def test_a_stale_look_is_unknown(self):
        now = 1_790_000_000_000
        ca._shadow_game_note(now, False, "no game window")
        late = now + ca._SHADOW_GAME_FRESH_S * 1000 + 1
        self.assertIsNone(ca.shadow_game_on_screen(late),
                          "a look older than three watch periods still said 'not on screen' - the reader may be off "
                          "or its loop dead, and he may be playing now")
        self.assertEqual(ca.shadow_game_detail(late)["ageS"], ca._SHADOW_GAME_FRESH_S)

    def test_no_look_since_boot_is_unknown(self):
        ca._SHADOW_GAME["v"] = (None, None, "the shadow watch has not looked since this console started")
        self.assertIsNone(ca.shadow_game_on_screen(1_790_000_000_000))
        self.assertIsNone(ca.shadow_game_detail(1_790_000_000_000)["ageS"])


class _Proc(object):
    pid = 4242

    def poll(self):
        return None


class TheWatchSaysWhatItSaw(unittest.TestCase):
    """shadow_watch_tick, real, with the machine stubbed - every look leaves its verdict."""

    STUBS = ("_shadow_state", "_agent_alive", "mini_state", "start_agent", "stop_agent",
             "_force_kill_all_agents", "_mini_sid", "_shadow_now_ms", "_screen_recording_ok_quick",
             "ON_AIR_FLOOR_GB", "_agent_proc", "_agent_origin", "_agent_since_ms", "_stop_inflight",
             "bare_content_reads", "reel_content_reads")

    def setUp(self):
        self.world = tempfile.mkdtemp(prefix="game_on_screen_case_")
        self.addCleanup(shutil.rmtree, self.world, True)
        self._env = {k: os.environ.get(k) for k in ("TV_HIST", "TV_SESSIONS", "TV_CAPTURE")}
        os.environ["TV_HIST"] = self.world
        os.environ["TV_SESSIONS"] = os.path.join(self.world, "sessions.jsonl")
        os.environ["TV_CAPTURE"] = "auto"
        self._saved = {k: getattr(ca, k) for k in self.STUBS}
        self._finders = (tv.find_d2r_window_mac, tv.find_d2r_window_win, getattr(tv, "_PICK_UNKNOWN", False))
        self._verdict = ca._SHADOW_GAME.get("v")
        self.addCleanup(self._restore)
        self.now = int(time.time() * 1000)
        self.alive, self.on = False, True
        self.window, self.reads = BARE, None
        ca._shadow_state = lambda: {"on": self.on, "available": True, "recording": self.alive}
        ca._agent_alive = lambda: self.alive
        ca.mini_state = lambda: {"running": False}
        ca._shadow_now_ms = lambda: self.now
        ca._screen_recording_ok_quick = lambda: True
        ca.ON_AIR_FLOOR_GB = 0
        ca._mini_sid = lambda: "s_game"
        ca._stop_inflight = False
        ca._agent_proc, ca._agent_origin, ca._agent_since_ms = None, "hand", None
        ca.start_agent = self._start
        ca.stop_agent = self._stop
        ca._force_kill_all_agents = lambda *a, **k: {"ok": True}
        ca.bare_content_reads = lambda: self.reads
        # REG-1704 - the whole reel's reads hold its first reads (one journal); the real reader answered [] for this
        # fixture's reel, a pair the console never sees, and the launcher cases leaned on it.
        ca.reel_content_reads = lambda: self.reads
        tv._PICK_UNKNOWN = False
        tv.find_d2r_window_mac = lambda *a, **k: self.window
        tv.find_d2r_window_win = lambda *a, **k: self.window
        ca._SHADOW_GAME["v"] = (None, None, "fixture: never looked")
        self.assertTrue(os.path.realpath(ca._shadow_watch_path()).startswith(os.path.realpath(self.world) + os.sep),
                        "TV_HIST was not honoured")

    def _restore(self):
        for k, v in self._saved.items():
            setattr(ca, k, v)
        tv.find_d2r_window_mac, tv.find_d2r_window_win, tv._PICK_UNKNOWN = self._finders
        ca._SHADOW_GAME["v"] = self._verdict
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _start(self, *a, **k):
        ca._agent_proc = _Proc()
        ca._agent_origin = k.get("origin", "hand")
        ca._agent_since_ms = self.now
        self.alive = True
        return {"ok": True, "msg": "started", "origin": k.get("origin", "hand")}

    def _stop(self, *a, **k):
        self.alive = False
        return {"ok": True, "msg": "session saved · off"}

    def _verdict_now(self):
        return ca.shadow_game_on_screen(self.now)

    def test_the_tray_is_not_play(self):
        self.window = None                     # Boosteroid / GeForce NOW in the tray: no game window at all
        ca.shadow_watch_tick()
        self.assertIs(self._verdict_now(), False, "a desktop with no game window left no 'not on screen' verdict")

    def test_the_boosteroid_launcher_is_not_play(self):
        self.reads = LAUNCH
        ca.shadow_watch_tick()
        self.assertIs(self._verdict_now(), False, "the launcher look left no 'not on screen' verdict")
        self.now += 1000
        self.reads = None                      # the wait after the launcher verdict: still the launcher
        ca.shadow_watch_tick()
        self.assertIs(self._verdict_now(), False, "the wait after a launcher verdict forgot it")

    def test_the_game_is_play(self):
        self.reads = ZONE
        ca.shadow_watch_tick()
        self.assertIs(self._verdict_now(), True, "Boosteroid showing the HUD did not read as the game")
        ca._SHADOW_GAME["v"] = (None, None, "fixture")
        self.alive, self.window, self.reads = False, GFN_STREAM, None
        ca.shadow_watch_tick()
        self.assertIs(self._verdict_now(), True, "a GeForce NOW stream titled with the game did not read as the game")

    def test_a_bare_window_nobody_has_read_is_unknown(self):
        self.reads = None
        ca.shadow_watch_tick()
        self.assertIsNone(self._verdict_now())

    def test_a_rolling_shadow_reel_reports_what_it_films(self):
        ca._agent_proc, ca._agent_origin, ca._agent_since_ms = _Proc(), "shadow", self.now
        self.alive, self.reads = True, None
        ca.shadow_watch_tick()
        self.assertIsNone(self._verdict_now(), "a shadow reel whose first reads are not in yet was guessed")
        self.reads = ZONE
        ca.shadow_watch_tick()
        self.assertIs(self._verdict_now(), True, "a rolling shadow reel on the game left no 'on screen' verdict")
        self.reads = LAUNCH
        ca.shadow_watch_tick()
        self.assertIs(self._verdict_now(), False, "a rolling shadow reel on the launcher left no verdict")

    def test_a_switched_off_reader_says_nothing(self):
        self.on = False
        self.window = None
        ca.shadow_watch_tick()
        self.assertIsNone(self._verdict_now(), "a reader that is off and never looked gave a verdict")


class _Toolhelp(object):
    """kernel32's process snapshot over `procs` (exe names) - the real tv_diablo._toolhelp_any walks it."""

    def __init__(self, procs):
        self.procs = list(procs)
        self._i = 0
        self.kernel32 = self

    def CreateToolhelp32Snapshot(self, flags, pid):
        self._i = 0
        return 77

    def _fill(self, ref):
        if self._i >= len(self.procs):
            return 0
        ref._obj.szExeFile, ref._obj.th32ProcessID = self.procs[self._i], 100 + self._i
        self._i += 1
        return 1

    def Process32FirstW(self, snap, ref):
        return self._fill(ref)

    def Process32NextW(self, snap, ref):
        return self._fill(ref)

    def CloseHandle(self, h):
        return 1


class TheProverAsksTheScreen(unittest.TestCase):
    """ca._sp_playing_here -> self_prove.playing_state(game_on_screen=ca.shadow_game_on_screen), real both sides."""

    def setUp(self):
        self.verdict = ca._SHADOW_GAME.get("v")
        self.addCleanup(lambda: ca._SHADOW_GAME.__setitem__("v", self.verdict))
        self.clock = ca._shadow_now_ms
        self.addCleanup(lambda: setattr(ca, "_shadow_now_ms", self.clock))
        self.now = 1_790_000_000_000
        ca._shadow_now_ms = lambda: self.now

    def _say(self, game):
        ca._shadow_game_note(self.now, game, "fixture")

    def _win(self, procs):
        fake = _Toolhelp(procs)
        with mock.patch.object(SP, "IS_WIN", True), mock.patch.object(ctypes, "windll", fake, create=True):
            return ca._sp_playing_here()

    def test_boosteroid_with_no_game_on_screen_is_not_play(self):
        self._say(False)
        self.assertIs(self._win(["System", "Boosteroid.exe", "chrome.exe"]), False,
                      "Boosteroid on its launcher or in the tray read as playing - the ALT's 178 owed proofs")

    def test_boosteroid_with_the_game_on_screen_is_play(self):
        self._say(True)
        self.assertIs(self._win(["Boosteroid.exe"]), True)

    def test_a_client_nobody_could_look_at_is_play(self):
        self._say(False)
        self.now += ca._SHADOW_GAME_FRESH_S * 1000 + 1      # the look went stale: the reader stopped
        self.assertIs(self._win(["Boosteroid.exe"]), True, "a stale look let a proof start beside a client")
        ca._SHADOW_GAME["v"] = (None, None, "never looked")
        self.assertIs(self._win(["GeForceNOW.exe"]), True, "a client nobody ever looked at was guessed idle")

    def test_geforce_now_follows_the_same_rule(self):
        self._say(False)
        self.assertIs(self._win(["GeForceNOW.exe"]), False, "GeForce NOW on its library read as playing")
        self.assertIs(self._win(["NVIDIA GeForce NOW.exe"]), False)
        self._say(True)
        self.assertIs(self._win(["GeForceNOW.exe"]), True, "a GeForce NOW stream of the game was not play")

    def test_the_game_itself_is_play_whatever_the_screen_says(self):
        self._say(False)                      # exclusive fullscreen can hide D2R's window from the walk
        self.assertIs(self._win(["Battle.net.exe", "D2R.exe"]), True,
                      "local D2R (Dean's way of playing) did not count - its window can be invisible to the walk")
        self.assertIs(self._win(["Boosteroid.exe", "D2R.exe"]), True)

    def test_battle_net_alone_is_not_play(self):
        self._say(None)
        self.assertIs(self._win(["Battle.net.exe", "Agent.exe"]), False, "the Battle.net launcher read as the game")

    def test_the_mac_follows_the_same_rule(self):
        class _R(object):
            def __init__(self, out):
                self.stdout, self.returncode = out, 0
        boost = "81237 /Applications/Boosteroid.app/Contents/MacOS/Boosteroid\n"
        game = r"81235 /Applications/CrossOver.app/Contents/wine64-preloader C:\Program Files\Diablo II Resurrected\D2R.exe" + "\n"

        def mac(listing):
            with mock.patch.object(SP, "IS_WIN", False), \
                    mock.patch.object(SP.subprocess, "run", lambda *a, **k: _R(listing)):
                return ca._sp_playing_here()
        self._say(False)
        self.assertIs(mac(boost), False, "Boosteroid on the Mac with no game on screen read as playing")
        self.assertIs(mac(boost + game), True, "D2R under CrossOver did not count")
        self._say(True)
        self.assertIs(mac(boost), True)
        self._say(None)
        self.assertIs(mac(boost), True, "an unknown screen let a proof start beside a client on the Mac")


class TheLaneAsksThroughTheJudge(unittest.TestCase):
    """the rescue loop's two doors into the lane hand it the judge - both, or a stand-aside reads the process alone."""

    def _captured(self, name, door):
        got = {}

        def fake(**k):
            got.update(k)
            return {"on": True, "worked": 0, "lastTs": None, "owed": 0, "key": "fixture", "say": "fixture"}
        lane = dict(ca._SELF_PROVE)
        self.addCleanup(lambda: (ca._SELF_PROVE.clear(), ca._SELF_PROVE.update(lane)))
        with mock.patch.object(SP, name, fake):
            door()
        return got

    def test_the_tick_asks_the_judge(self):
        got = self._captured("tick", ca._self_prove_tick)
        # v3882 (#123) - the prover's own judge: the console's yield judge (his game OR a sweep reading, REG-2192) plus
        # GitHub's import - never the process alone
        self.assertIs(got.get("playing"), ca._sp_prove_yield_here,
                      "the ten-minute tick must hand the yield judge (his game OR a sweep reading, REG-2192), not the process alone")
        self._judge_holds_the_widened_one()
        self.assertIn("gameOnScreen", ca._SELF_PROVE, "the lane's status does not say what the screen showed")

    def test_the_guard_asks_the_judge(self):
        got = self._captured("guard", ca._self_prove_guard)
        self.assertIs(got.get("playing"), ca._sp_prove_yield_here,
                      "the ten-second stand-aside must hand the yield judge (REG-2192), not the process alone - it and the tick disagree")
        self._judge_holds_the_widened_one()

    def _judge_holds_the_widened_one(self):
        """the prover's judge says yield whenever the console's widened judge does (his game, a sweep) - it only adds"""
        with mock.patch.object(ca, "_sp_yield_here", lambda: True):
            self.assertTrue(ca._sp_prove_yield_here(), "the prover's judge dropped the game/sweep judge")


RED_PROOF = [
    {"why": "REG-1666 - the ten-minute tick asks the process alone: Boosteroid open on its launcher reads as playing",
     "file": "control_app.py",
     "find": "        r = _sp.tick(busy=_cpu_busy_pct, playing=_sp_prove_yield_here,   # REG-1666 game · REG-2192 a sweep · #123 an import\n",
     "replace": "        r = _sp.tick(busy=_cpu_busy_pct,\n",
     "matches": 1},
    {"why": "REG-1666 - the ten-second stand-aside asks the process alone, so it and the tick disagree",
     "file": "control_app.py",
     "find": "        r = _sp.guard(busy=_cpu_busy_pct, playing=_sp_prove_yield_here)   # REG-2192 a sweep · #123 an import\n",
     "replace": "        r = _sp.guard(busy=_cpu_busy_pct)\n",
     "matches": 1},
    {"why": "REG-1666 - a stale look is trusted: a dead watch keeps saying 'not on screen' while he plays",
     "file": "control_app.py",
     "find": "    if now - at > _SHADOW_GAME_FRESH_S * 1000:\n        return None\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-1666 - Boosteroid's launcher (no D2R HUD word) reads as the game",
     "file": "control_app.py",
     "find": "        return False, \"Boosteroid is open on its launcher - the first reads show no D2R HUD word\"\n",
     "replace": "        return True, \"Boosteroid is open on its launcher - the first reads show no D2R HUD word\"\n",
     "matches": 1},
    {"why": "REG-1666 - a desktop with no game window (the tray, the library) reads as UNKNOWN, so the client still blocks",
     "file": "control_app.py",
     "find": "        return False, \"no game window on his screen (the game is shut, or its app is in the tray or on its library)\"\n",
     "replace": "        return None, \"no game window on his screen (the game is shut, or its app is in the tray or on its library)\"\n",
     "matches": 1},
    {"why": "REG-1666 - a console that never looks (capture off) is read as 'no game on screen'",
     "file": "control_app.py",
     "find": "    if pre.get(\"windowLooked\") is False:\n        return None, \"this console does not look for the game window (capture is off)\"\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-1666 - the watch's idle look leaves no verdict, so the tray and the launcher are never known",
     "file": "control_app.py",
     "find": "    _shadow_game_note(now, *_game_verdict(pre, hud, relook_open=_bare_relook_open(now)))\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-1666 - a rolling shadow reel leaves no verdict on what it films",
     "file": "control_app.py",
     "find": "            _shadow_game_note(now, *_game_verdict(pre, _hud, lobby=_lobby))\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-1666 - the Windows walk asks a cloud client's name alone again, never the screen",
     "file": "self_prove.py",
     "find": "                    return is_play_proc(name, _screen())\n",
     "replace": "                    return is_play_proc(name)\n",
     "matches": 1},
    {"why": "REG-1666 - local D2R is not known as the game, so Dean's way of playing never counts",
     "file": "self_prove.py",
     "find": "    return n.startswith(\"d2r\") or \"diabloii\" in n.replace(\" \", \"\")\n",
     "replace": "    return False\n",
     "matches": 1},
    {"why": "REG-1666 - the Mac reads D2R under CrossOver as a cloud client, judged by the screen",
     "file": "self_prove.py",
     "find": "        if any(_POSIX_GAME.search(ln) for ln in hits):\n            return True                        # the game itself (D2R.exe under CrossOver)\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-1666 - the Mac counts any cloud client by name again, whatever is on the screen",
     "file": "self_prove.py",
     "find": "        return bool(hits) and _screen() is not False      # a cloud client: only with the game on his screen\n",
     "replace": "        return bool(hits)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
