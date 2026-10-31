# -*- coding: utf-8 -*-
"""REG-1624 — A PROOF RUNS ONLY WHILE THE GAME IS OFF, AND YIELDS THE MOMENT IT STARTS.

His words, 2026-09-30, after closing Boosteroid on the ALT so it could prove: "future wise it needs to be working in
parallel somehow so when logging off and the game is off ... it can do whats needed but shadow reader when game start
should be triggered regardless. the shadow reader is always on when the game is on regardless of the console" - and
"everything should work smoothly regardless of each other with an intelligent architecture that makes it all work
consecutively".

MEASURED before the change, on the ALT with the game off and the console freshly relaunched: the prover's own probes
said playing False, 1,781 MB available - and its start bar was 2,048, so it could never start at all. And a proof that
did run was asked to stand aside only on the lane's 10-minute tick, so it could run beside his game for up to ten.

Driven, joint by joint:
  1. the loop - the rescue loop's one call (_self_prove_dispatch) runs the whole tick every 10 min and, between
     ticks, the cheap guard on every 10 s tick WHILE a proof runs (never while none does).
  2. the guard - asks only "is he playing" and "how much memory is left"; when stand_aside() says go it runs the
     whole tick at once, which kills, books the stand-aside and cools down through the one door it always had.
  3. the bar - with the game off, a proof starts at MIN_FREE_MB_TO_START (1,536), still never while he plays and never
     under the running floor.
  4. REG-1628, the whole chain JOINED: the console's own guard call -> the real guard -> the real tick, with only the
     machine faked. MEASURED on the ALT on v3534: the guard booked each ended slice and the tick it chained met
     busy=None ("load-unknown"), so the next slice still waited for the 10-minute tick. Case 2's fake tick could not
     see that - it recorded the call and never asked whether a slice could start.
Nothing here kills a process or starts a prover: every kill and every tick is a recorded fake. RED_PROOF below.
"""
import ast
import io
import json
import os
import shutil
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

_WORLD = tempfile.mkdtemp(prefix="proof_yields_")
os.environ["TV_HIST"] = _WORLD
os.environ["TV_SESSIONS"] = os.path.join(_WORLD, "sessions.jsonl")

import self_prove as SP  # noqa: E402
import control_app as ca  # noqa: E402

RED_PROOF = [
    {"why": "REG-1715 - the idle floor applies when the game is UNKNOWN too",
     "file": "self_prove.py",
     "find": "    _floor = MIN_FREE_MB_WHILE_RUNNING_IDLE if playing is False else MIN_FREE_MB_WHILE_RUNNING   # REG-1715\n",
     "replace": "    _floor = MIN_FREE_MB_WHILE_RUNNING_IDLE if not playing else MIN_FREE_MB_WHILE_RUNNING   # REG-1715\n",
     "matches": 1},
    {"why": "REG-1715 - a proof with no game beside it is stood aside at the stream's floor again: the ALT never proves",
     "file": "self_prove.py",
     "find": "    _floor = MIN_FREE_MB_WHILE_RUNNING_IDLE if playing is False else MIN_FREE_MB_WHILE_RUNNING   # REG-1715\n",
     "replace": "    _floor = MIN_FREE_MB_WHILE_RUNNING   # REG-1715\n",
     "matches": 1},
    {"why": "REG-1643 - the fast path reads a stranger holding the ended prover's pid as the prover again",
     "file": "self_prove.py",
     "find": "        alive = identity(pid, birth) is not False\n",
     "replace": "        alive = pid_alive(pid)\n", "matches": 1},
    {"why": "REG-1624 - the guard never stands a running proof aside: it waits for the 10-minute tick",
     "file": "self_prove.py",
     "find": "        aside, _why = stand_aside(play_now, free_now)\n        if not aside:\n            return None\n",
     "replace": "        aside, _why = False, ''\n        if not aside:\n            return None\n", "matches": 1},
    {"why": "REG-1624 - the loop never asks the guard between ticks, so a proof runs beside his game for 10 minutes",
     "file": "control_app.py",
     "find": "    if isinstance(sp, dict) and (sp.get(\"running\") or sp.get(\"key\") in (\"running\", \"start\", \"aside-survived\")):\n        return \"guard\"\n",
     "replace": "    if False:\n        return \"guard\"\n", "matches": 1},
    {"why": "REG-1624 - the dispatch forgets to call the guard it chose",
     "file": "control_app.py",
     "find": "    elif step == \"guard\":\n        _self_prove_guard()",
     "replace": "    elif step == \"guard\":\n        pass", "matches": 1},
    {"why": "REG-1624 - the start bar is the stream-era 2048 again: an idle 8 GB ALT never starts a proof",
     "file": "self_prove.py",
     "find": "MIN_FREE_MB_TO_START = 1536\n",
     "replace": "MIN_FREE_MB_TO_START = 2048\n", "matches": 1},
    {"why": "REG-1625 - an ended slice waits out the 10-minute tick: slices are not consecutive",
     "file": "self_prove.py",
     "find": "        if not alive:\n            return (_tick or tick)(now_s=now_s, path=path, kill_fn=kill_fn, busy=busy, playing=playing, free=free)\n",     # REG-1671 re-anchor
     "replace": "        if False:\n            return (_tick or tick)(now_s=now_s, path=path, kill_fn=kill_fn, busy=busy, playing=playing, free=free)\n",
     "matches": 1},
    {"why": "REG-1628 - the guard's chained tick is not handed the load probe: load-unknown, the next slice waits",
     "file": "self_prove.py",
     "find": "            return (_tick or tick)(now_s=now_s, path=path, kill_fn=kill_fn, busy=busy, playing=playing, free=free)\n",     # REG-1671 re-anchor
     "replace": "            return (_tick or tick)(now_s=now_s, path=path, kill_fn=kill_fn, playing=playing, free=free)\n",
     "matches": 1},
    {"why": "REG-1671 - the chained tick is not handed the console's play judge: a cloud client in the tray is play",
     "file": "self_prove.py",
     "find": "            return (_tick or tick)(now_s=now_s, path=path, kill_fn=kill_fn, busy=busy, playing=playing, free=free)\n",
     "replace": "            return (_tick or tick)(now_s=now_s, path=path, kill_fn=kill_fn, busy=busy, free=free)\n",
     "matches": 1},
    {"why": "REG-1628 - the console asks the guard without its load probe (the measured ALT defect)",
     "file": "control_app.py",
     "find": "        r = _sp.guard(busy=_cpu_busy_pct, playing=_sp_yield_here)   # REG-2192 - yield to a sweep, not only his game\n",     # REG-2192 re-anchor
     "replace": "        r = _sp.guard(playing=_sp_yield_here)   # REG-2192 - yield to a sweep, not only his game\n", "matches": 1},
    {"why": "REG-1624 - the guard runs a tick even when no proof is running (a 10 s full tick on an idle PC)",
     "file": "self_prove.py",
     "find": "        pid = mem.get(\"pid\") or _STARTED.get(\"pid\")\n        if not pid:\n            return None\n",
     "replace": "        pid = mem.get(\"pid\") or _STARTED.get(\"pid\")\n        if False:\n            return None\n", "matches": 1},
]


class TheLoopAsksTheGuardOnlyWhileAProofRuns(unittest.TestCase):
    def test_the_step(self):
        first, every = ca.SELF_PROVE_FIRST_TICK, ca.SELF_PROVE_EVERY_TICKS
        self.assertEqual(ca._self_prove_step(first, {}), "tick")
        self.assertEqual(ca._self_prove_step(first + every, {"running": True}), "tick", "the whole tick keeps its slot")
        self.assertEqual(ca._self_prove_step(first + 1, {"running": True, "key": "running"}), "guard")
        self.assertEqual(ca._self_prove_step(first + 1, {"running": False, "key": "aside-survived"}), "guard",
                         "a prover that outlived its kill must keep being asked to end")
        self.assertIsNone(ca._self_prove_step(first + 1, {"running": False, "key": "current"}),
                          "the guard ran with no proof running")
        self.assertIsNone(ca._self_prove_step(first + 1, None))

    def test_the_dispatch_calls_what_it_chose(self):
        calls = []
        with mock.patch.object(ca, "_self_prove_tick", lambda: calls.append("tick")), \
                mock.patch.object(ca, "_self_prove_guard", lambda: calls.append("guard")), \
                mock.patch.object(ca, "_console_beacon_async", lambda event: None), \
                mock.patch.dict(ca._SELF_PROVE, {"running": True, "key": "running"}, clear=True):
            ca._self_prove_dispatch(ca.SELF_PROVE_FIRST_TICK)
            ca._self_prove_dispatch(ca.SELF_PROVE_FIRST_TICK + 1)
            ca._self_prove_dispatch(ca.SELF_PROVE_FIRST_TICK + 2)
        self.assertEqual(calls, ["tick", "guard", "guard"])

    def test_the_rescue_loop_goes_through_the_dispatch(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        loop = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_console_rescue_loop")
        called = {c.func.id for c in ast.walk(loop) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
        self.assertIn("_self_prove_dispatch", called, "the rescue loop no longer reaches the self-prove lane")
        self.assertNotIn("_self_prove_tick", called, "a second, unguarded door into the lane from the loop")


class TheGuardStandsARunningProofAside(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="guard_store_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.store = os.path.join(self.d, ".self_prove.json")
        self.ticks = []
        self._started = dict(SP._STARTED)
        SP._STARTED.update(pid=None, birth=None)
        self.addCleanup(lambda: (SP._STARTED.clear(), SP._STARTED.update(self._started)))

    def _running(self):
        with io.open(self.store, "w", encoding="utf-8") as fh:
            json.dump({"pid": 4242, "pidBirth": 1234.5, "startedFor": "fp"}, fh)
        # the fake prover is alive unless a case says it ended - and it IS ours: its birth is the one recorded at spawn
        # (REG-1643: the guard asks who holds the pid, so a fixture that only says "something is alive" is a stranger)
        for name, fake in (("pid_alive", lambda pid: True), ("proc_birth", lambda pid: 1234.5 if pid == 4242 else None)):
            p = mock.patch.object(SP, name, fake)
            p.start()
            self.addCleanup(p.stop)

    def _tick(self, **kw):
        self.ticks.append(kw)
        return {"key": "stood-aside", "running": False}

    def test_no_proof_running_asks_nothing(self):
        self.assertIsNone(SP.guard(path=self.store, playing=True, free=100, _tick=self._tick))
        self.assertEqual(self.ticks, [], "the guard ran the tick with no proof running")

    def test_a_proof_beside_nothing_keeps_running(self):
        self._running()
        self.assertIsNone(SP.guard(path=self.store, playing=False, free=3000, _tick=self._tick))
        self.assertEqual(self.ticks, [])

    def test_the_game_starting_stands_it_aside_at_once(self):
        self._running()
        r = SP.guard(path=self.store, playing=True, free=3000, _tick=self._tick)
        self.assertEqual(r["key"], "stood-aside")
        self.assertEqual(len(self.ticks), 1)
        self.assertIs(self.ticks[0]["playing"], True, "the tick was not told what the guard saw")

    def test_memory_under_the_running_floor_stands_it_aside(self):
        self._running()
        SP.guard(path=self.store, playing=False, free=SP.MIN_FREE_MB_WHILE_RUNNING_IDLE - 100, _tick=self._tick)
        self.assertEqual(len(self.ticks), 1)

    def test_with_no_game_a_proof_runs_on_down_to_the_idle_floor(self):
        """REG-1715 - his ALT, 10-02: one proof took 2,070 MB free to 990 and stood aside ten times, 94 gates owed"""
        self._running()
        self.assertIsNone(SP.guard(path=self.store, playing=False, free=990, _tick=self._tick))
        self.assertEqual(self.ticks, [], "a proof with no game beside it was stood aside at 990 MB")

    def test_an_unknown_game_keeps_the_strict_floor(self):
        self._running()
        # playing=None hands guard() no answer, so it asks the console's own probe; an UNKNOWN is a judge that ANSWERS None
        SP.guard(path=self.store, playing=(lambda: None), free=990, _tick=self._tick)
        self.assertEqual(len(self.ticks), 1, "an UNKNOWN 'is he playing' loosened the running floor")

    def test_a_slice_that_ended_is_booked_now_and_the_next_can_start(self):
        # REG-1625 - measured on the ALT: a 40-gate slice took about a minute, then the lane waited out its 10-minute
        # tick. An ended slice is booked at once (the tick decides whether the next one starts)
        # REG-1671 - it is handed the console's own probes, to ask at its own moment: never an answer the guard read
        # earlier, and never none at all (then a cloud client in the tray read as play - the v3542 eye's finding)
        self._running()
        judge, room = (lambda: False), (lambda: 3000)
        with mock.patch.object(SP, "pid_alive", lambda pid: False):
            r = SP.guard(path=self.store, playing=judge, free=room, _tick=self._tick)
        self.assertEqual(r["key"], "stood-aside")          # whatever the tick said, it was asked
        self.assertEqual(len(self.ticks), 1, "an ended slice waited for the 10-minute tick")
        self.assertIs(self.ticks[0].get("playing"), judge, "the chained tick was not handed the console's play judge")
        self.assertIs(self.ticks[0].get("free"), room, "the chained tick was not handed the console's memory probe")

    def test_a_live_slice_beside_nothing_is_left_alone(self):
        self._running()
        with mock.patch.object(SP, "pid_alive", lambda pid: True):
            self.assertIsNone(SP.guard(path=self.store, playing=False, free=3000, _tick=self._tick))
        self.assertEqual(self.ticks, [], "a healthy running slice was ticked every 10 s")

    def test_the_real_tick_kills_through_its_one_door_and_books_it(self):
        self._running()
        killed = []
        with mock.patch.object(SP, "is_ours", lambda pid, birth: True), \
                mock.patch.object(SP, "census_state", lambda: {"state": "missing", "why": "fixture"}), \
                mock.patch.object(SP, "tree_state", lambda: ("installed", "fixture")):
            r = SP.guard(now_s=5000.0, path=self.store, playing=True, free=3000,
                         kill_fn=lambda pid, birth: killed.append(pid) or True)
        self.assertEqual(killed, [4242], "the running proof was not ended when he started playing")
        self.assertEqual(r.get("key"), "stood-aside", r)
        mem = SP.load(self.store)
        self.assertEqual(mem.get("stoodAside"), 1, "the stand-aside was not booked (it would read as a failure)")
        self.assertIsNone(mem.get("pid"))


class TheNextSliceStartsTheMomentOneEnds(unittest.TestCase):
    """REG-1628 - ca._self_prove_guard() -> SP.guard -> SP.tick, real all the way; only the machine is faked: the ended
    prover (4242), the census, the tree, the spawn (a recorder, never a process), and how busy the CPU is."""

    OLD, NEW = 4242, 5151

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="chain_store_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.store = os.path.join(self.d, ".self_prove.json")
        with io.open(self.store, "w", encoding="utf-8") as fh:
            json.dump({"pid": self.OLD, "pidBirth": 1234.5, "startedFor": "fp", "sliceGates": ["gate_a", "gate_b"]}, fh)
        self._started = dict(SP._STARTED)
        SP._STARTED.update(pid=None, birth=None)
        self.addCleanup(lambda: (SP._STARTED.clear(), SP._STARTED.update(self._started)))
        self._lane = dict(ca._SELF_PROVE)
        self.addCleanup(lambda: (ca._SELF_PROVE.clear(), ca._SELF_PROVE.update(self._lane)))
        ca._SELF_PROVE.clear()
        ca._SELF_PROVE.update({"key": "start", "running": True})
        self.spawned = []
        census = {"state": "stale", "why": "fixture", "fingerprint": "fp", "owed": 2,
                  "owedGates": [("gate_c", 1), ("gate_d", 1)], "owedWhy": "fixture; 2 owed"}
        for name, fake in (("_store_path", lambda path=None: path or self.store),
                           ("pid_alive", lambda pid: pid == self.NEW),
                           ("proc_birth", lambda pid: 77.0 if pid == self.NEW else None),
                           ("census_state", lambda: dict(census)),
                           ("tree_state", lambda git=None: ("installed", "fixture")),
                           ("spawn", lambda log_path, names=None, **k: self.spawned.append(names) or self.NEW),
                           ("ensure_prover_deps", lambda *a, **k: {"ok": True, "installed": [], "why": "fixture"}),
                           ("_gate_costs", lambda path=None: None),
                           ("playing_state", lambda **k: False),     # REG-1666 - asked with the screen judge
                           ("free_mb", lambda: 3000.0)):
            p = mock.patch.object(SP, name, fake)
            p.start()
            self.addCleanup(p.stop)

    def _guard(self, busy):
        with mock.patch.object(ca, "_cpu_busy_pct", lambda *a, **k: busy):
            return ca._self_prove_guard()

    def test_an_idle_pc_starts_the_next_slice_at_once(self):
        r = self._guard(5.0)
        self.assertEqual(len(self.spawned), 1, "the slice ended on an idle PC and the next one did not start: %r" % (r,))
        self.assertTrue(set(self.spawned[0]) <= {"gate_c", "gate_d"}, "the next slice is not the owed gates")
        self.assertEqual(ca._SELF_PROVE.get("key"), "start", "the console's lane state does not say it started")
        mem = SP.load(self.store)
        self.assertEqual((mem.get("pid"), mem.get("slices")), (self.NEW, 1),
                         "the ended slice was not booked, or the new prover is not tracked")

    def test_a_busy_pc_books_the_slice_and_waits(self):
        r = self._guard(90.0)
        self.assertEqual(self.spawned, [], "a slice started on a busy PC")
        self.assertEqual(r.get("key"), "busy")
        self.assertEqual(SP.load(self.store).get("slices"), 1, "the ended slice was not booked")

    def test_an_unmeasured_load_is_never_read_as_idle(self):
        self.assertEqual(self._guard(None).get("key"), "load-unknown")
        self.assertEqual(self.spawned, [])

    def test_a_reused_pid_is_not_our_prover(self):
        """REG-1643 (the v3535 cross-family eye) - the ended prover's pid now names a STRANGER (alive, another birth).
        The fast path must see the slice ended, as the tick and the kill do, and start the next one at once."""
        with mock.patch.object(SP, "pid_alive", lambda pid: pid in (self.OLD, self.NEW)), \
                mock.patch.object(SP, "proc_birth", lambda pid: 77.0 if pid == self.NEW else 999.0):
            r = self._guard(5.0)
        self.assertEqual(len(self.spawned), 1, "a stranger holding the ended prover's pid was read as the prover, so "
                                               "the next slice waits for the 10-minute tick: %r" % (r,))
        mem = SP.load(self.store)
        self.assertEqual((mem.get("pid"), mem.get("slices")), (self.NEW, 1))

    def test_a_cloud_client_in_the_tray_does_not_hold_the_next_slice(self):
        """REG-1671 (the v3542 cross-family eye) - the ALT's steady state: Boosteroid open in the tray, the console's shadow
        watch saying the GAME is not on his screen. The tick the guard chains must ask that judge; a bare process list
        reads the tray client as play and the next slice waits for the 10-minute tick."""
        def boosteroid_running(game_on_screen=None):          # REG-1666's real rule for a running cloud client
            return SP.is_play_proc("Boosteroid.exe", SP._ask(game_on_screen, lambda: None))
        with mock.patch.object(SP, "playing_state", boosteroid_running), \
                mock.patch.object(ca, "shadow_game_on_screen", lambda *a, **k: False):
            r = self._guard(5.0)
        self.assertEqual(len(self.spawned), 1, "Boosteroid in the tray with no game on his screen held the next slice "
                                               "(the chained tick never asked the console's judge): %r" % (r,))

    def test_the_game_on_his_screen_still_holds_the_next_slice(self):
        """REG-1671 - the other side: the same tray client WITH the game on his screen is play, and nothing starts"""
        def boosteroid_running(game_on_screen=None):
            return SP.is_play_proc("Boosteroid.exe", SP._ask(game_on_screen, lambda: None))
        with mock.patch.object(SP, "playing_state", boosteroid_running), \
                mock.patch.object(ca, "shadow_game_on_screen", lambda *a, **k: True):
            r = self._guard(5.0)
        self.assertEqual(self.spawned, [], "a slice started beside his game: %r" % (r,))
        self.assertEqual(r.get("key"), "playing", r)

    def test_a_live_pid_with_no_recorded_birth_is_left_alone(self):
        """a store from before REG-1511: no birth to check - the fast path keeps the old answer and starts nothing"""
        with io.open(self.store, "w", encoding="utf-8") as fh:
            json.dump({"pid": self.OLD, "startedFor": "fp", "sliceGates": ["gate_a"]}, fh)
        with mock.patch.object(SP, "pid_alive", lambda pid: pid in (self.OLD, self.NEW)):
            r = self._guard(5.0)
        self.assertIsNone(r)
        self.assertEqual(self.spawned, [], "a second prover started beside a live one whose identity is unknown")


class AProofStartsWhenTheGameIsOffAndMemoryAllows(unittest.TestCase):
    def d(self, free, playing=False):
        return SP.decide({"state": "missing", "why": "fixture", "fingerprint": "fp"}, ("installed", "fixture"), None, 0,
                         {}, 100000.0, on=True, playing=playing, free=free)

    def test_the_idle_alt_can_start(self):
        self.assertTrue(self.d(1781)["start"], "the measured idle ALT (1,781 MB available) still cannot start a proof")

    def test_never_beside_his_game_and_never_near_the_floor(self):
        self.assertEqual(self.d(6000, playing=True)["key"], "playing")
        self.assertEqual(self.d(SP.MIN_FREE_MB_TO_START - 1)["key"], "low-memory")
        self.assertGreater(SP.MIN_FREE_MB_TO_START, SP.MIN_FREE_MB_WHILE_RUNNING + 256,
                           "a proof must start with room above the floor it stands aside at")


if __name__ == "__main__":
    unittest.main(verbosity=2)
