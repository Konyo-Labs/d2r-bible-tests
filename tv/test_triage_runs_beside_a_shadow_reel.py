# -*- coding: utf-8 -*-
"""2026-09-28 — TRIAGE RUNS BESIDE A SHADOW REEL, AND A LANE THAT REFUSES SAYS SO.

MEASURED over SSH on his Windows ALT (plays D2R through Boosteroid, shadow reader ON, the hourly
rollover live — 10 rotations overnight): 7 of its 10 reels sat in TRIAGE — "the template is known and
retro_triage has not walked its frames, so whether it holds a panel is UNSURVEYED" — and 3 at PRINTER.
Nothing reached TOMBSTONE, so the FIFO drain correctly released nothing.

THE CAUSE, read in control_app.retro_triage_tick. It backed off on
  (a) _d2r_process_alive()  — False on Boosteroid, there is no local D2R.exe;
  (b) os.getloadavg()       — DOES NOT EXIST ON WINDOWS; the except swallowed it, so the ALT had no
                              load guard at all;
  (c) _capture_is_live()    — with shadow rolling continuously (a ~2 s gap between hourly reels) this
                              refused ~every 90 s tick, for ever.
And the loop printed only on success; _TRIAGE_LANE {surveyed, panels, lastTs, lastReel, skips} was
never published and `skips` was never filled — a lane refusing for ever read like one with nothing to do.

HIS WORDS: "this needs to be automated flow", "not stacking up", "regardless of room.. to flow through
the river". The docstring's POLITENESS rule stays: triage must not compete with HIS sessions.

WHAT THIS LAW DRIVES — the SHIPPED retro_triage_tick, the SHIPPED doctor row and the SHIPPED CPU helper,
with only the edges stubbed (_capture_is_live, the agent's door, _cpu_busy_pct, _d2r_process_alive,
the survey call, the sealed-session read, the paid-sweep state) on a TV_HIST fixture world:
  · a SHADOW capture + CPU 20%     -> it reaches the survey;
  · an ON AIR / MINI capture       -> refuses "never compete with the camera", before the CPU is asked;
  · a capture whose door is unread -> refuses (an unknown reel is his, never the console's);
  · SHADOW + CPU unmeasurable      -> refuses and names it; SHADOW + CPU 90% -> refuses;
  · no capture: the SAME helper guards a saturated machine and an unmeasurable one (no silent no-guard);
  · every refusal is RECORDED (lastWhy, lastSkipTs, skips[key] counted) and a raise too;
  · a reel still being folded, and a reel with no frame, never park the lane; a walk that walked
    nothing does not stamp lastTs;
  · the lane is PUBLISHED on /api/river, and its last walk survives a relaunch via the store;
  · the doctor row 'triage starved' reads MISSING / UNKNOWN / OK (and UNMEASURED when stood down),
    including off the exact state the console publishes — the join, not two halves;
  · _cpu_busy_pct: the Windows GetSystemTimes arithmetic (kernel INCLUDES idle), and the load-average
    path capped at 100 with None when unmeasurable.

⚠ NOTHING REAL IS TOUCHED. The survey is stubbed before any tick runs, the store path is asserted to sit
in the fixture before anything is read, and no console, bridge or agent is contacted. RED_PROOF below.
[[heart-first]] [[unknown-stays-unknown]] [[the-unjoined-end]] [[regression-guard]]
"""
import ast
import ctypes
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

# the fixture world is declared BEFORE control_app is imported, so nothing resolved at import time can
# describe his tree
_WORLD = tempfile.mkdtemp(prefix="triage_shadow_")
os.environ["TV_HIST"] = _WORLD

import control_app as ca  # noqa: E402
import console_doctor as CD  # noqa: E402
import corroborate as CO  # noqa: E402
import frame_authority as FA  # noqa: E402
import retro_triage as RT  # noqa: E402
import tv_diablo as TVD  # noqa: E402

# #189 REG-2559 - NO LAW IN THIS FILE MAY REACH THE REAL CLAUDE CLI. farmgate_payload's d2r_window row asks the agent
# probe, which ran `claude auth status` and then `claude -p "reply with only: ok"` on his plan (Opus), once per run of
# test_a_cloud_route_pc_is_never_told_to_launch_d2r. Every case here sees "no Claude CLI on this machine"; a case
# that needs one patches its own. Measured by TheClaudeCliIsNeverLaunched below.
_NO_CLAUDE = mock.patch.object(ca, "_find_claude_bin", lambda *a, **k: None)
_NO_CLAUDE.start()

HOUR = 3600.0


class _Proc(object):
    """An agent child as start_agent leaves it: poll() is None while it runs."""
    pid = 4242

    def poll(self):
        return None


def _fresh_lane():
    return {"surveyed": 0, "panels": 0, "lastTs": None, "lastReel": None, "skips": {},
            "ticks": 0, "idle": 0, "lastKey": None, "lastWhy": None, "lastAt": None,
            "lastSkipKey": None, "lastSkipWhy": None, "lastSkipTs": None,
            "backlog": None, "backlogAt": None, "upSince": int(time.time() * 1000),
            "playingSince": None}


class _Base(unittest.TestCase):

    STUBS = ("_capture_is_live", "_agent_origin", "_agent_proc", "_agent_alive", "_cpu_busy_pct",
             "vault_sweep_state", "_CHRON_JOB", "HIST_DIR", "_TRIAGE_ON", "_TRIAGE_LANE",
             "_TRIAGE_STORE_SEED", "_TRIAGE_BACKLOG_SEED", "IS_WIN", "stash_screen_open_cached",
             "_os_input_idle_s")
    ENV = ("TV_HIST", "TV_TRIAGE_SHADOW_MAX_CPU", "TV_TRIAGE_WIN_MAX_CPU")

    def setUp(self):
        self.world = tempfile.mkdtemp(prefix="triage_shadow_case_")
        self.addCleanup(shutil.rmtree, self.world, True)
        self._env = {k: os.environ.get(k) for k in self.ENV}
        os.environ["TV_HIST"] = self.world
        os.environ.pop("TV_TRIAGE_SHADOW_MAX_CPU", None)
        os.environ.pop("TV_TRIAGE_WIN_MAX_CPU", None)
        self._saved = {k: getattr(ca, k) for k in self.STUBS}
        self._edges = (TVD._pgrep_d2r_state, TVD._toolhelp_d2r_state, RT.survey, FA.sealed_sessions)
        self.addCleanup(self._restore)
        self.assertTrue(os.path.realpath(RT._store_path()).startswith(os.path.realpath(self.world)),
                        "TV_HIST was not honoured by the survey store (%s) - REFUSING to run against "
                        "a real store" % RT._store_path())

        self.cpu = 20.0
        self.cpu_asks = 0
        self.surveyed = []
        self.walks = 1
        self.playing = False
        self.agent_live = False
        self.pgrep_asks = 0
        ca.HIST_DIR = self.world
        ca._TRIAGE_ON = True
        ca._TRIAGE_LANE = _fresh_lane()
        ca._TRIAGE_STORE_SEED = {"read": False, "ts": None, "why": ""}
        ca._TRIAGE_BACKLOG_SEED = {"read": False, "why": ""}
        # Mac-shaped by default (CI is Linux, his Mac is darwin): the Windows cases say so themselves
        ca.IS_WIN = False
        ca._capture_is_live = lambda: False
        ca._agent_proc, ca._agent_origin = None, "hand"
        # ⚠ _agent_alive falls back to the REAL control_agent.pid — his console's agent. Stubbed.
        ca._agent_alive = lambda: self.agent_live
        ca._cpu_busy_pct = self._cpu
        ca.vault_sweep_state = lambda: {"running": False}
        ca._CHRON_JOB = {}
        ca.stash_screen_open_cached = lambda f: None
        # ⚠ v3861 - THE REAL IDLE CLOCK IS HIS. v3855's stale-play rule reads this PC's keyboard/mouse idle time, and a
        # fixture that left it live went RED on the v3861 push at 06:xx (8 failures, 2 errors: 'surveyed' != 'playing')
        # because the Mac had been idle 4.2 h, past the 3 h bar - and green at 04:30 and on CI, where nobody is idle.
        # Every case here is an ACTIVE player; test_a_game_left_open_is_not_play owns the idle rule.
        ca._os_input_idle_s = lambda: 0.0
        # ⚠ the real probes would ask HIS machine whether D2R.exe runs (pgrep on this Mac)
        TVD._pgrep_d2r_state = self._pgrep
        TVD._toolhelp_d2r_state = lambda: self.playing
        RT.survey = self._survey
        FA.sealed_sessions = lambda *a, **k: ({}, True)

    def _restore(self):
        for k, v in self._saved.items():
            setattr(ca, k, v)
        TVD._pgrep_d2r_state, TVD._toolhelp_d2r_state, RT.survey, FA.sealed_sessions = self._edges
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    # ── the edges ─────────────────────────────────────────────────────────────────────────────
    def _cpu(self, *a, **k):
        self.cpu_asks += 1
        return self.cpu

    def _pgrep(self):
        self.pgrep_asks += 1
        return self.playing

    def _survey(self, reels, gate, **k):
        """A walk the store KEEPS: the reel leaves the owed set, as the real survey()+remember() do."""
        self.surveyed.append([os.path.basename(r) for r in reels])
        if self.walks:
            for r in reels:
                RT.remember(r, 0, 3)
        return {"reels": self.walks, "frames": 3 if self.walks else 0, "panels": 0,
                "stoppedEarly": False, "say": "stub survey"}

    def reel(self, name="reel_s_1510000000000_1", frames=3, age_s=HOUR):
        """A folded reel on the fixture shelf, last modified `age_s` ago."""
        d = os.path.join(self.world, name)
        os.makedirs(d, exist_ok=True)
        # the capture clock is the frame name, not the directory mtime and not a fixed id
        base = int((time.time() - age_s) * 1000)
        for i in range(frames):
            with io.open(os.path.join(d, "f_%d.jpg" % (base + i)), "wb") as fh:
                fh.write(b"\xff\xd8\xff")
        t = time.time() - age_s
        os.utime(d, (t, t))
        return d

    def rolling(self, origin):
        """A capture is live, opened by THIS console through `origin`'s door (Windows-shaped: the
        capture half's pid is alive AND the agent is)."""
        ca._capture_is_live = lambda: True
        self.agent_live = True
        ca._agent_proc = _Proc()
        ca._agent_origin = origin

    def tick(self):
        return ca.retro_triage_tick()

    def doctor_over(self, n_triage):
        """The doctor row over the state the console PUBLISHES right now, with n reels at TRIAGE."""
        p = _river(n_triage)
        p["triage"] = ca.triage_lane_state()
        real = CD._get
        CD._get = lambda path, *a, **k: (p if path == "/api/river" else None)
        try:
            st, why = CD._check_triage_is_not_starved()
        finally:
            CD._get = real
        return st, (why[0] if isinstance(why, tuple) else why)


class _FakeK32(object):
    """kernel32, as far as the two Windows probes use it: a Toolhelp32 process list and
    GetSystemTimes. Each call fills the ctypes structure the SHIPPED code allocated (byref()._obj)."""

    def __init__(self, procs=None, times=None, snap_raises=None):
        self.procs, self.times, self.snap_raises = list(procs or []), list(times or []), snap_raises
        self.closed, self._i = [], 0

    def CreateToolhelp32Snapshot(self, flags, pid):
        if self.snap_raises is not None:
            raise self.snap_raises
        self._i = 0
        return 77

    def _fill(self, ref):
        if self._i >= len(self.procs):
            return 0
        ref._obj.szExeFile = self.procs[self._i]
        self._i += 1
        return 1

    def Process32FirstW(self, snap, ref):
        self._i = 0
        return self._fill(ref)

    def Process32NextW(self, snap, ref):
        return self._fill(ref)

    def CloseHandle(self, h):
        self.closed.append(h)
        return 1

    def GetSystemTimes(self, idle, kern, user):
        if not self.times:
            return 0
        for ref, (hi, lo) in zip((idle, kern, user), self.times.pop(0)):
            ref._obj.dwHighDateTime, ref._obj.dwLowDateTime = hi, lo
        return 1


class _FakeWindll(object):
    def __init__(self, k32):
        self.kernel32 = k32


class TriageRunsBesideAShadowReel(_Base):

    def test_a_shadow_capture_and_a_quiet_cpu_reach_the_survey(self):
        self.reel()
        self.rolling("shadow")
        self.cpu = 20.0
        r = self.tick()
        self.assertEqual(self.surveyed, [["reel_s_1510000000000_1"]],
                         "a shadow reel rolling beside a 20%%-busy machine still blocked triage: %r" % r)
        self.assertTrue(r.get("ok"), r)
        self.assertEqual(r.get("key"), "surveyed")
        self.assertTrue(r.get("shadow"), "the tick did not know it ran beside a shadow reel: %r" % r)
        lane = ca._TRIAGE_LANE
        self.assertEqual(lane["surveyed"], 1)
        self.assertIsNotNone(lane["lastTs"], "a walk that happened was not stamped")
        self.assertEqual(lane["lastReel"], "reel_s_1510000000000_1")
        self.assertEqual(lane["backlog"], 0, "the backlog after the only reel was walked must be 0")
        self.assertEqual(lane["skips"], {}, "a successful walk was counted as a refusal")

    def test_an_on_air_capture_refuses_before_the_cpu_is_even_asked(self):
        self.reel()
        self.rolling("hand")
        r = self.tick()
        self.assertFalse(r.get("ok"), r)
        self.assertEqual(r.get("key"), "capture-onair", r)
        self.assertIn("never compete with the camera", r.get("why") or "")
        self.assertIn("ONAIR", r.get("why") or "", "the refusal does not say whose session it is")
        self.assertEqual(self.surveyed, [], "triage walked a reel beside HIS ON AIR session")
        self.assertEqual(self.cpu_asks, 0, "his session is refused on the door alone; sampling the "
                                           "CPU first spends his machine on a question already answered")

    def test_a_mini_capture_refuses_too(self):
        self.reel()
        self.rolling("mini")
        r = self.tick()
        self.assertEqual(r.get("key"), "capture-mini", r)
        self.assertIn("never compete with the camera", r.get("why") or "")
        self.assertEqual(self.surveyed, [])

    def test_a_capture_whose_door_cannot_be_read_is_his_never_the_consoles(self):
        """An orphan agent (not opened by THIS console) carries a stale origin that means nothing."""
        self.reel()
        ca._capture_is_live = lambda: True
        ca._agent_proc, ca._agent_origin = None, "shadow"
        r = self.tick()
        self.assertEqual(r.get("key"), "capture-unowned", r)
        self.assertIn("never compete with the camera", r.get("why") or "")
        self.assertEqual(self.surveyed, [], "an orphan's stale shadow origin was believed")

    def test_shadow_with_an_unmeasurable_cpu_refuses_and_names_it(self):
        self.reel()
        self.rolling("shadow")
        self.cpu = None
        r = self.tick()
        self.assertFalse(r.get("ok"), r)
        self.assertEqual(r.get("key"), "cpu-unmeasured", r)
        self.assertIn("could not be measured", r.get("why") or "")
        self.assertIn("SHADOW", r.get("why") or "")
        self.assertEqual(self.surveyed, [], "an UNKNOWN CPU was read as an idle one")

    def test_shadow_with_a_busy_cpu_refuses(self):
        self.reel()
        self.rolling("shadow")
        self.cpu = 90.0
        r = self.tick()
        self.assertEqual(r.get("key"), "cpu-shadow", r)
        self.assertIn("90%", r.get("why") or "")
        self.assertIn("%.0f%%" % ca._TRIAGE_SHADOW_MAX_CPU, r.get("why") or "")
        self.assertEqual(self.surveyed, [])

    def test_the_shadow_bar_is_the_named_constant_and_a_law_can_move_it(self):
        self.reel()
        self.rolling("shadow")
        bar = ca._TRIAGE_SHADOW_MAX_CPU
        self.cpu = bar + 1
        self.assertEqual(self.tick().get("key"), "cpu-shadow", "one point above the bar was let through")
        self.cpu = bar
        self.assertEqual(self.tick().get("key"), "surveyed", "the bar itself must be allowed")
        self.reel("reel_s_1510000000001_2")
        os.environ["TV_TRIAGE_SHADOW_MAX_CPU"] = "95"
        self.cpu = 90.0
        self.assertEqual(self.tick().get("key"), "surveyed",
                         "TV_TRIAGE_SHADOW_MAX_CPU was not read at call time")

    def test_without_a_capture_the_same_helper_guards_the_machine(self):
        """The ALT's defect was NO guard at all. Every OS now asks _cpu_busy_pct."""
        self.reel()
        self.cpu = ca._TRIAGE_MAX_CPU
        self.assertEqual(self.tick().get("key"), "cpu-loaded")
        self.cpu = None
        r = self.tick()
        self.assertEqual(r.get("key"), "cpu-unmeasured", "an unmeasurable machine ran triage blind")
        self.assertNotIn("SHADOW", r.get("why") or "", "no shadow reel was rolling; the why says one was")
        self.assertEqual(self.surveyed, [])
        self.cpu = 50.0
        self.assertEqual(self.tick().get("key"), "surveyed")

    def test_he_is_playing_still_refuses_first(self):
        self.reel()
        self.playing = True
        r = self.tick()
        self.assertEqual(r.get("key"), "playing", r)
        self.assertEqual(self.cpu_asks, 0)
        self.assertEqual(self.pgrep_asks, 1, "on the Mac the game is asked of pgrep (D2R.exe under "
                                             "CrossOver)")


class EveryOutcomeIsRecorded(_Base):

    def test_each_refusal_is_recorded_and_counted_by_reason(self):
        self.reel()
        self.rolling("hand")
        self.tick()
        self.tick()
        self.rolling("shadow")
        self.cpu = 90.0
        r = self.tick()
        lane = ca._TRIAGE_LANE
        self.assertEqual(lane["skips"], {"capture-onair": 2, "cpu-shadow": 1},
                         "refusals were not counted by reason: %r" % lane["skips"])
        self.assertEqual(lane["ticks"], 3)
        self.assertEqual(lane["lastKey"], "cpu-shadow")
        self.assertEqual(lane["lastWhy"], r["why"])
        self.assertEqual(lane["lastSkipWhy"], r["why"])
        self.assertEqual(lane["lastSkipKey"], "cpu-shadow")
        self.assertIsInstance(lane["lastSkipTs"], int)
        self.assertIsNone(lane["lastTs"], "no reel was walked, yet the lane says one was")

    def test_a_raise_is_recorded_before_it_propagates(self):
        self.reel()

        def _boom(*a, **k):
            raise RuntimeError("survey exploded")
        RT.survey = _boom
        with self.assertRaises(RuntimeError):
            self.tick()
        lane = ca._TRIAGE_LANE
        self.assertEqual(lane["skips"].get("raised"), 1, lane)
        self.assertIn("survey exploded", lane["lastSkipWhy"] or "")

    def test_nothing_owed_is_recorded_as_idle_not_as_a_refusal(self):
        r = self.tick()
        self.assertTrue(r.get("done"), r)
        lane = ca._TRIAGE_LANE
        self.assertEqual(lane["idle"], 1)
        self.assertEqual(lane["skips"], {})
        self.assertEqual(lane["backlog"], 0)
        self.assertEqual(lane["lastKey"], "done")

    def test_a_reel_still_being_folded_is_not_walked(self):
        self.reel(age_s=5)
        r = self.tick()
        self.assertEqual(self.surveyed, [], "a reel folded 5 s ago was walked - its frames may still "
                                            "be arriving, and it would be remembered as walked IN FULL")
        self.assertEqual(r.get("key"), "unworkable", r)
        self.assertEqual(r.get("settling"), 1)
        self.assertEqual(ca._TRIAGE_LANE["backlog"], 1, "a settling reel is still OWED")

    def test_a_frameless_reel_does_not_park_the_lane(self):
        self.reel("reel_s_1510000000000_0", frames=0)
        self.reel("reel_s_1510000000001_1", frames=4)
        r = self.tick()
        self.assertEqual(self.surveyed, [["reel_s_1510000000001_1"]],
                         "smallest-first picked the reel with NO frame, which survey() skips without "
                         "remembering - the lane would pick it again every tick for ever")
        self.assertEqual(r.get("frameless"), 1)
        self.assertEqual(r.get("backlog"), 1, "the frameless reel is still owed and must be counted")

    def test_a_walk_that_walked_nothing_does_not_stamp_lastTs(self):
        self.reel()
        self.walks = 0
        r = self.tick()
        self.assertFalse(r.get("ok"), r)
        self.assertEqual(r.get("key"), "walked-nothing")
        self.assertIsNone(ca._TRIAGE_LANE["lastTs"],
                          "a tick that walked no reel stamped lastTs, so a parked lane reads as busy")


class TheLaneIsPublished(_Base):

    def _river_payload_dicts(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        out = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Dict):
                keys = {k.value for k in n.keys if isinstance(k, ast.Constant)}
                if {"mouth", "population", "detail"} <= keys:
                    out.append(("ok", n))
                elif {"stations", "counts", "reels", "why"} <= keys and len(keys) <= 7:
                    out.append(("failed", n))
        return out

    def test_the_river_payload_carries_the_lane_on_both_answers(self):
        found = self._river_payload_dicts()
        kinds = sorted(k for k, _ in found)
        self.assertEqual(kinds, ["failed", "ok"],
                         "premise: the /api/river payload dicts were not found as expected (%r)" % kinds)
        for kind, d in found:
            vals = {k.value: v for k, v in zip(d.keys, d.values) if isinstance(k, ast.Constant)}
            v = vals.get("triage")
            self.assertTrue(isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                            and v.func.id == "triage_lane_state",
                            "the %s /api/river payload does not publish triage_lane_state() - the "
                            "doctor runs in another process and cannot see the lane" % kind)
            lane = vals.get("routeLane")
            self.assertTrue(isinstance(lane, ast.Call) and isinstance(lane.func, ast.Name)
                            and lane.func.id == "route_lane_pulse",
                            "the %s /api/river payload does not publish route_lane_pulse() - the "
                            "outlet row runs in another process and cannot see the driver" % kind)

    def test_the_published_state_says_never_and_up_not_zero(self):
        s = ca.triage_lane_state()
        self.assertTrue(s["ok"], s)
        self.assertIsNone(s["lastSurveyTs"])
        self.assertIsNone(s["sinceSurveyS"], "a lane that never walked a reel read as recent")
        self.assertIsInstance(s["upS"], float)
        self.assertIsNone(s["owed"], "no tick has counted the backlog; owed must be UNKNOWN, not 0")
        self.assertEqual(s["shadowMaxCpu"], ca._TRIAGE_SHADOW_MAX_CPU)

    def test_the_last_walk_survives_a_relaunch_via_the_store(self):
        ts = int((time.time() - 5 * HOUR) * 1000)
        with io.open(RT._store_path(), "w", encoding="utf-8") as fh:
            json.dump({"reel_s_1": {"panels": 0, "frames": 3, "ts": ts, "full": True},
                       "reel_s_2": {"panels": 1, "frames": 3, "ts": ts + 999, "full": False}}, fh)
        s = ca.triage_lane_state()
        self.assertEqual(s["lastSurveyTs"], ts, "the newest FULL store row was not the seed: %r" % s)
        self.assertEqual(s["lastSurveySource"], "the survey store")
        self.assertGreater(s["sinceSurveyS"], 4.9 * HOUR)
        self.reel()
        self.tick()
        s2 = ca.triage_lane_state()
        self.assertEqual(s2["lastSurveySource"], "this process",
                         "a walk in this process did not supersede the older store row")
        self.assertLess(s2["sinceSurveyS"], 60)


def _river(triage=7, ok=True):
    return {"ok": True, "lanes": {"ok": ok, "lanes": [
        {"name": "INTAKE", "byStation": {"INTAKE": 0, "TRIAGE": triage, "STATION": 0, "EMPTY": 0}},
        {"name": "PRINTER", "byStation": {"PRINTER": 3, "JOIN": 0}}]}}


class TheDoctorRow(unittest.TestCase):

    def verdict(self, payload):
        real = CD._get
        CD._get = lambda path, *a, **k: (payload if path == "/api/river" else None)
        try:
            st, why = CD._check_triage_is_not_starved()
        finally:
            CD._get = real
        return st, (why[0] if isinstance(why, tuple) else why)

    def lane(self, **kw):
        s = {"ok": True, "stoodDown": False, "skips": {"cpu-shadow": 140, "capture-onair": 3},
             "lastSkipKey": "cpu-shadow", "lastSkipWhy": "a SHADOW reel is rolling and the CPU is 88% busy",
             "lastWhy": "a SHADOW reel is rolling and the CPU is 88% busy",
             "backlog": 7, "lastSurveyTs": 1, "lastReel": "reel_x", "lastSurveySource": "the survey store",
             "sinceSurveyS": 4 * HOUR, "upS": 9 * HOUR}
        s.update(kw)
        return s

    def test_missing_when_triage_holds_reels_and_nothing_was_walked_for_three_hours(self):
        p = _river(7)
        p["triage"] = self.lane()
        st, why = self.verdict(p)
        self.assertEqual(st, CD.MISSING, why)
        self.assertIn("7 reel(s) wait in TRIAGE", why)
        self.assertIn("88% busy", why, "the row does not name the lane's last refusal")
        self.assertIn("cpu-shadow", why)
        self.assertIn("Backlog: 7", why)

    def test_missing_when_the_lane_never_walked_in_a_long_lived_process(self):
        p = _river(2)
        p["triage"] = self.lane(lastSurveyTs=None, sinceSurveyS=None, upS=5 * HOUR,
                                lastSkipWhy=None, lastWhy=None, skips={})
        st, why = self.verdict(p)
        self.assertEqual(st, CD.MISSING, why)
        self.assertIn("NEVER walked", why)
        self.assertIn("NONE RECORDED", why, "a lane with no tick at all must say the loop may be dead")

    def test_ok_inside_the_bar_and_ok_when_nothing_waits(self):
        p = _river(7)
        p["triage"] = self.lane(sinceSurveyS=HOUR)
        self.assertEqual(self.verdict(p)[0], CD.OK)
        p = _river(0)
        p["triage"] = self.lane()
        st, why = self.verdict(p)
        self.assertEqual(st, CD.OK, why)
        self.assertIn("no reel waits in TRIAGE", why)

    def test_unknown_when_the_lane_state_cannot_be_read(self):
        self.assertEqual(self.verdict(None)[0], CD.UNKNOWN, "no answer must be UNKNOWN")
        self.assertEqual(self.verdict(_river(7))[0], CD.UNKNOWN,
                         "a console that publishes no triage field must be UNKNOWN, not clean")
        p = _river(7)
        p["triage"] = {"ok": False, "why": "boom"}
        self.assertEqual(self.verdict(p)[0], CD.UNKNOWN)

    def test_unknown_when_the_river_cannot_count_triage(self):
        p = _river(7, ok=False)
        p["triage"] = self.lane()
        self.assertEqual(self.verdict(p)[0], CD.UNKNOWN)
        p = {"ok": True, "lanes": {"ok": True, "lanes": [{"name": "PRINTER", "byStation": {"PRINTER": 1}}]}}
        p["triage"] = self.lane()
        st, why = self.verdict(p)
        self.assertEqual(st, CD.UNKNOWN, "no lane carried a TRIAGE count and it was read as zero: %s" % why)

    def test_a_stood_down_lane_is_unmeasured_not_starved(self):
        p = _river(7)
        p["triage"] = self.lane(stoodDown=True)
        self.assertEqual(self.verdict(p)[0], CD.UNMEASURED)

    def test_the_row_never_imports_the_twin(self):
        import inspect
        src = inspect.getsource(CD._check_triage_is_not_starved)
        code = "\n".join(l.split("#", 1)[0] for l in src.split("\n"))
        body = code.split('"""')[-1]
        self.assertNotIn("import control_app", body,
                         "the row imported control_app, whose _TRIAGE_LANE is the empty literal")
        self.assertIn('_get("/api/river"', body)

    def test_it_is_registered_explained_declared_and_periodic(self):
        self.assertIn("triage starved", [n for n, _ in CD.CHECKS])
        self.assertIn("triage starved", CD.PERIODIC)
        self.assertIn("triage starved", CD.WATCHES)
        self.assertIn("triage starved", CO.NO_JOINT_YET)


class TheJoin(_Base):
    """The state the console PUBLISHES is the shape the doctor READS — driven end to end."""

    def _doctor_over(self, n_triage):
        p = _river(n_triage)
        p["triage"] = ca.triage_lane_state()
        real = CD._get
        CD._get = lambda path, *a, **k: (p if path == "/api/river" else None)
        try:
            st, why = CD._check_triage_is_not_starved()
        finally:
            CD._get = real
        return st, (why[0] if isinstance(why, tuple) else why)

    def test_a_lane_refusing_beside_his_session_for_four_hours_reads_missing(self):
        self.reel()
        self.rolling("hand")
        self.tick()
        ca._TRIAGE_LANE["upSince"] -= int(4 * HOUR * 1000)
        st, why = self._doctor_over(1)
        self.assertEqual(st, CD.MISSING, why)
        self.assertIn("never compete with the camera", why)
        self.assertIn("capture-onair", why)

    def test_the_same_lane_after_a_walk_reads_ok(self):
        self.reel()
        self.rolling("shadow")
        self.tick()
        ca._TRIAGE_LANE["upSince"] -= int(4 * HOUR * 1000)
        st, why = self._doctor_over(1)
        self.assertEqual(st, CD.OK, why)


class TheCpuHelper(unittest.TestCase):

    def setUp(self):
        self._saved = (ca.IS_WIN, ca._system_times)
        self.addCleanup(self._restore)

    def _restore(self):
        ca.IS_WIN, ca._system_times = self._saved

    def test_windows_busy_is_kernel_plus_user_minus_idle_over_kernel_plus_user(self):
        # kernel INCLUDES idle: 100 kernel (80 of it idle) + 100 user -> 120 busy of 200 = 60%
        self.assertEqual(ca._cpu_busy_from_times((0, 0, 0), (80, 100, 100)), 60.0)
        self.assertEqual(ca._cpu_busy_from_times((10, 10, 10), (10, 10, 10)), None,
                         "a clock that did not move is UNMEASURED, not 0% busy")
        self.assertIsNone(ca._cpu_busy_from_times(None, (1, 2, 3)))

    def test_the_windows_path_samples_system_times_twice(self):
        seq = iter([(1000, 2000, 3000), (1080, 2100, 3100)])
        ca.IS_WIN = True
        ca._system_times = lambda: next(seq)
        # as on Windows: there IS no load average, so a path that still asks for one reads None
        with mock.patch.object(ca.os, "getloadavg", create=True, side_effect=AttributeError("windows")):
            self.assertEqual(ca._cpu_busy_pct(sample_s=0), 60.0,
                             "the Windows path did not answer from GetSystemTimes")
            ca._system_times = lambda: None
            self.assertIsNone(ca._cpu_busy_pct(sample_s=0), "an unreadable GetSystemTimes must be None")

    def test_elsewhere_it_is_the_load_average_over_the_cores_capped_and_unknown_when_absent(self):
        ca.IS_WIN = False
        with mock.patch.object(ca.os, "getloadavg", create=True, return_value=(5.0, 1, 1)), \
                mock.patch.object(ca.os, "cpu_count", return_value=10):
            self.assertEqual(ca._cpu_busy_pct(), 50.0)
        with mock.patch.object(ca.os, "getloadavg", create=True, return_value=(30.0, 1, 1)), \
                mock.patch.object(ca.os, "cpu_count", return_value=10):
            self.assertEqual(ca._cpu_busy_pct(), 100.0)
        with mock.patch.object(ca.os, "getloadavg", create=True, side_effect=AttributeError("windows")):
            self.assertIsNone(ca._cpu_busy_pct(), "no load average must be UNKNOWN, never 0")
        with mock.patch.object(ca.os, "getloadavg", create=True, return_value=(5.0, 1, 1)), \
                mock.patch.object(ca.os, "cpu_count", return_value=None):
            self.assertIsNone(ca._cpu_busy_pct(), "an unknown core count must not be guessed as 4")


class TheGameOnThisMachine(_Base):
    """H1 — HIS LAPTOP PLAYS NATIVELY. Dean plays D2R.exe on a Windows laptop, "usually", and triage
    must stand aside while the game runs and catch up after. The tick asked pgrep, which Windows does
    not have: FileNotFoundError, swallowed, False on every Windows PC — so with the shadow allowance
    triage walked reels beside his LOCAL game. Driven through the SHIPPED process probe with a fake
    kernel32 (the Toolhelp32 walk runs for real over the structures the code allocates)."""

    def _windows(self, procs, **kw):
        ca.IS_WIN = True
        TVD._toolhelp_d2r_state = self._edges[1]          # the REAL process half
        self.playing = None                               # pgrep on Windows: absent, cannot answer
        k32 = _FakeK32(procs=procs, **kw)
        p = mock.patch.object(ctypes, "windll", _FakeWindll(k32), create=True)
        p.start()
        self.addCleanup(p.stop)
        return k32

    def test_windows_native_d2r_refuses_playing_beside_a_quiet_shadow_reel(self):
        self.reel()
        k32 = self._windows(["System", "explorer.exe", "Battle.net.exe", "D2R.exe"])
        self.rolling("shadow")
        self.cpu = 20.0
        r = self.tick()
        self.assertEqual(r.get("key"), "playing",
                         "Windows + D2R.exe up + a shadow reel + a 20%%-busy CPU walked a reel beside "
                         "his NATIVE game: %r" % r)
        self.assertIn("Toolhelp32", r.get("why") or "", "the refusal does not say how it looked")
        self.assertEqual(self.surveyed, [])
        self.assertEqual(self.pgrep_asks, 0, "pgrep was asked on Windows, where it does not exist")
        self.assertEqual(self.cpu_asks, 0, "the CPU was sampled after the game was already found")
        self.assertEqual(k32.closed, [77], "the process snapshot handle was not closed")

    def test_windows_boosteroid_with_a_diablo_titled_window_walks_beside_the_shadow_reel(self):
        """His ALT: the capture half pinned a Boosteroid window titled for the game, and no D2R.exe
        runs there. A probe that read cap_target.json's label would call that local play."""
        self.reel()
        frames = tempfile.mkdtemp(prefix="triage_capframes_")
        self.addCleanup(shutil.rmtree, frames, True)
        with io.open(os.path.join(frames, "cap_target.json"), "w", encoding="utf-8") as fh:
            json.dump({"mode": "window", "d2rProcess": False, "ts": int(time.time() * 1000),
                       "label": "Boosteroid [boosteroid] - Diablo II: Resurrected via PrintWindow"}, fh)
        for p in (mock.patch.object(TVD, "FRAMES", frames), mock.patch.object(sys, "platform", "win32")):
            p.start()
            self.addCleanup(p.stop)
        self._windows(["System", "explorer.exe", "Boosteroid.exe", "chrome.exe"])
        self.assertTrue(TVD._win_d2r_process_alive(),
                        "premise: the label step of _win_d2r_process_alive DOES call this window the "
                        "game - which is why the triage probe must never use it")
        self.rolling("shadow")
        r = self.tick()
        self.assertEqual(r.get("key"), "surveyed",
                         "a Boosteroid session with no local D2R.exe starved triage again: %r" % r)
        self.assertEqual(self.surveyed, [["reel_s_1510000000000_1"]])

    def test_a_windows_probe_that_cannot_run_refuses_and_says_unknown(self):
        self.reel()
        self._windows([], snap_raises=OSError("the snapshot was refused"))
        self.rolling("shadow")
        r = self.tick()
        self.assertEqual(r.get("key"), "playing-unknown", "a probe that could not run was read as "
                                                          "'not playing': %r" % r)
        self.assertIn("UNKNOWN", r.get("why") or "")
        self.assertEqual(self.surveyed, [])
        self.assertEqual(self.cpu_asks, 0)

    def test_a_probe_that_raises_refuses_and_says_unknown(self):
        self.reel()
        ca.IS_WIN = True

        def _boom():
            raise RuntimeError("the snapshot exploded")
        TVD._toolhelp_d2r_state = _boom
        self.rolling("shadow")
        r = self.tick()
        self.assertEqual(r.get("key"), "playing-unknown", r)
        self.assertIn("raised RuntimeError", r.get("why") or "")
        self.assertIn("UNKNOWN", r.get("why") or "")
        self.assertEqual(self.surveyed, [])

    def test_the_mac_probe_reads_pgreps_exit_codes_and_a_missing_pgrep_is_unknown(self):
        """The Mac keeps pgrep (D2R.exe under CrossOver). Exit 0 = playing, 1 = not; a missing binary
        or any other code is UNKNOWN — exactly the answer Windows' missing pgrep used to swallow."""
        self.reel()
        TVD._pgrep_d2r_state = self._edges[0]             # the REAL pgrep half
        real_run = TVD.subprocess.run
        outcome = {}

        def _run(args, *a, **k):
            if list(args)[:1] != ["pgrep"]:
                return real_run(args, *a, **k)
            if "raise" in outcome:
                raise outcome["raise"]
            return TVD.subprocess.CompletedProcess(args, outcome["rc"], b"", b"")
        with mock.patch.object(TVD.subprocess, "run", _run):
            outcome.clear(); outcome["raise"] = FileNotFoundError("pgrep")
            self.assertEqual(self.tick().get("key"), "playing-unknown")
            self.assertFalse(TVD._d2r_process_alive(),
                             "the two-valued _d2r_process_alive must still read False for its callers")
            outcome.clear(); outcome["rc"] = 2
            self.assertEqual(self.tick().get("key"), "playing-unknown", "pgrep exit 2 is not 'no match'")
            outcome.clear(); outcome["rc"] = 0
            self.assertEqual(self.tick().get("key"), "playing")
            self.assertTrue(TVD._d2r_process_alive())
            outcome.clear(); outcome["rc"] = 1
            self.assertEqual(self.tick().get("key"), "surveyed")
        self.assertEqual(self.surveyed, [["reel_s_1510000000000_1"]])


class TheStoreMustKeepTheWalk(_Base):
    """M1 — survey() counts a reel it looked at whether or not remember() kept the verdict, and
    remember() returns False without raising on an unwritable or corrupt store. So the lane walked
    the SAME reel every 90 s for ever, answered key=surveyed, stamped lastTs — and the doctor read OK.
    Driven through the REAL survey() and remember() on the fixture store; only the frame gate is stubbed."""

    def _real_survey(self):
        RT.survey = self._edges[2]
        self.gate_calls = 0

        def _gate(f):
            self.gate_calls += 1
            return None
        ca.stash_screen_open_cached = _gate

    def _unwritable(self):
        os.chmod(self.world, 0o555)
        self.addCleanup(os.chmod, self.world, 0o755)
        probe = os.path.join(self.world, ".probe")
        try:
            open(probe, "w").close()
        except (IOError, OSError):
            return                                       # chmod holds: the store cannot be written
        # running as root, where chmod does not bind: block the store's own atomic write instead
        os.remove(probe)
        os.makedirs(RT._store_path() + ".tmp")

    def _four_hours_on(self):
        L = ca._TRIAGE_LANE
        L["upSince"] -= int(4 * HOUR * 1000)
        if L.get("owedSince"):
            L["owedSince"] -= int(4 * HOUR * 1000)

    def _assert_not_remembered(self, how):
        r = self.tick()
        self.assertEqual(self.gate_calls, 3, "premise: the survey really looked at the reel's 3 frames")
        self.assertFalse(r.get("ok"), r)
        self.assertEqual(r.get("key"), "not-remembered",
                         "a walk the store did not keep was counted as a walk: %r" % r)
        self.assertIn(how, r.get("why") or "")
        L = ca._TRIAGE_LANE
        self.assertIsNone(L["lastTs"], "a walk the store did not keep stamped lastTs")
        self.assertEqual(L["surveyed"], 0)
        self.assertEqual(L["backlog"], 1, "the reel is still owed")
        self.assertEqual(self.tick().get("key"), "not-remembered")
        self.assertEqual(ca._TRIAGE_LANE["skips"].get("not-remembered"), 2,
                         "the second tick paid for the same reel and was not recorded as a refusal")
        self._four_hours_on()
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.MISSING, "a lane re-walking one reel for ever read healthy: %s" % why)
        self.assertIn("not-remembered", why)

    def test_an_unwritable_store_records_not_remembered_and_reads_missing_after_the_bar(self):
        self.reel()
        self._real_survey()
        self._unwritable()
        self._assert_not_remembered("would not take the write")

    def test_a_corrupt_store_records_not_remembered_and_reads_missing_after_the_bar(self):
        self.reel()
        self._real_survey()
        with io.open(RT._store_path(), "w", encoding="utf-8") as fh:
            fh.write("{not json at all")
        self._assert_not_remembered("does not read back cleanly")

    def test_a_writable_store_counts_the_walk(self):
        """The baseline: the same real survey on a healthy store IS a walk."""
        d = self.reel()
        self._real_survey()
        r = self.tick()
        self.assertEqual(r.get("key"), "surveyed", r)
        self.assertIs(RT.worth_reading(d), False, "the verdict (looked, no panel) was not stored")
        self.assertIsNotNone(ca._TRIAGE_LANE["lastTs"])


class TheWaitIsHowLongAReelWaited(_Base):
    """M2 — the row measured time since the LAST WALK, not how long a reel had WAITED. After an idle
    day the last walk is a day old, so a reel folded 30 s ago (still settling) or held ten minutes
    behind 'playing' read MISSING '24.0 h' — on his Mac, every evening he plays."""

    def _an_idle_day(self):
        ts = int((time.time() - 24 * HOUR) * 1000)
        with io.open(RT._store_path(), "w", encoding="utf-8") as fh:
            json.dump({"reel_s_1500000000000_9": {"panels": 0, "frames": 3, "ts": ts, "full": True}}, fh)
        ca._TRIAGE_LANE["upSince"] -= int(48 * HOUR * 1000)

    def test_a_day_old_store_row_and_a_reel_folded_moments_ago_reads_ok(self):
        self._an_idle_day()
        self.reel(age_s=5)
        self.assertEqual(self.tick().get("key"), "unworkable", "premise: the reel is still settling")
        s = ca.triage_lane_state()
        self.assertGreater(s["sinceSurveyS"], 23.9 * HOUR, "premise: the last walk is a day old")
        self.assertEqual(s["waitFrom"], "the first tick that found this backlog")
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.OK, "a reel folded seconds ago read as starved for a day: %s" % why)

    def test_the_same_reel_still_unwalked_four_hours_later_reads_missing(self):
        self._an_idle_day()
        self.reel(age_s=5)
        self.tick()
        ca._TRIAGE_LANE["owedSince"] -= int(4 * HOUR * 1000)
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.MISSING, why)
        self.assertIn("4.0 h", why)
        self.assertIn("the first tick that found this backlog", why)

    def test_after_an_idle_day_a_reel_held_behind_playing_reads_ok_until_the_play_bar(self):
        """Every tick since the reel folded refused before it could count the backlog - the lane was
        caught up just before, and that is the moment the wait can have begun.
        ⚠ 2026-09-28 — this case used to pin MISSING at four hours of 'playing': the defect itself
        (standing aside for his game is by design). A 'playing' lane is judged by its UNBROKEN run of
        play against TRIAGE_PLAYING_BAR_S, so four hours is OK and past the play bar is MISSING."""
        self._an_idle_day()
        self.assertEqual(self.tick().get("key"), "done", "premise: nothing owed - the lane is caught up")
        self.reel(age_s=HOUR)
        self.playing = True
        self.assertEqual(self.tick().get("key"), "playing")
        s = ca.triage_lane_state()
        self.assertEqual(s["waitFrom"], "the last tick that found nothing owed")
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.OK, "ten minutes behind 'playing' after an idle day read starved: %s" % why)
        ca._TRIAGE_LANE["caughtUpTs"] -= int(4 * HOUR * 1000)
        ca._TRIAGE_LANE["playingSince"] -= int(4 * HOUR * 1000)
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.OK, "four hours of his game read as a starved lane: %s" % why)
        self.assertIn("standing aside for his game", why)
        ca._TRIAGE_LANE["playingSince"] -= int((CD.TRIAGE_PLAYING_BAR_S / HOUR) * HOUR * 1000)
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.MISSING, why)
        self.assertIn("[playing]", why, "the row does not say the lane is standing aside for his game")


class ARelaunchDoesNotResetTheWait(_Base):
    """Gap 20 — the wait was the newest of the last walk, an empty tick, the first backlog and
    this process starting. A relaunch made the process start the newest mark, so a backlog that
    had stood for hours read as inside the bar for as long as the console kept relaunching.

    The first-backlog mark is kept across the restart. The oldest waiting reel is judged by its
    own capture clock, and that age wins when it is the longer one. Process start is not a mark.
    """

    def _mark(self, owed_since, relaunches=1, oldest=None):
        path = ca._triage_backlog_path()
        self.assertTrue(os.path.realpath(path).startswith(os.path.realpath(self.world)),
                        "the backlog mark is not inside the fixture (%s)" % path)
        with io.open(path, "w", encoding="utf-8") as fh:
            json.dump({"owedSince": owed_since, "oldestReelMs": oldest,
                       "relaunches": relaunches}, fh)
        return path

    def test_a_backlog_that_caught_up_starts_the_next_one_at_one_relaunch(self):
        """REG-1949 (the #231 eye on 1ae4574f) - caught up wrote relaunches 0 to the file and kept the count in memory,
        so the next backlog in the same process was saved, and doctored, "across N relaunches" it never lived."""
        owed = int(time.time() * 1000) - int(2 * HOUR * 1000)
        path = self._mark(owed, relaunches=2)
        ca._triage_backlog_load()
        self.assertEqual(ca._TRIAGE_LANE.get("relaunches"), 3, "baseline: the relaunch was not counted")
        ca._triage_record({"ok": True, "key": "idle", "backlog": 0})
        with io.open(path, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh).get("relaunches"), 0)
        ca._triage_record({"ok": True, "key": "surveyed", "backlog": 2})
        with io.open(path, encoding="utf-8") as fh:
            saved = json.load(fh).get("relaunches")
        self.assertEqual(saved, 1, "a fresh backlog inherited the old one's relaunch count (REG-1949): %s" % saved)
        self.assertEqual(ca._TRIAGE_LANE.get("relaunches"), 1)

    def test_a_relaunch_keeps_the_first_backlog_mark(self):
        owed = int(time.time() * 1000) - int(6 * HOUR * 1000)
        self._mark(owed)
        self.reel("reel_plain", frames=0, age_s=6 * HOUR)
        r = self.tick()
        self.assertEqual(r.get("key"), "unworkable", r)
        self.assertGreaterEqual(r.get("backlog") or 0, 1)
        self.assertEqual(ca._TRIAGE_LANE["owedSince"], owed,
                         "the first tick after a relaunch moved the backlog mark to now")
        self.assertEqual(ca._TRIAGE_LANE.get("relaunches"), 2)
        s = ca.triage_lane_state()
        self.assertEqual(s["waitFrom"], "the first tick that found this backlog")
        self.assertNotEqual(s["waitFrom"], "this process starting")
        self.assertIsNone(s.get("reelWaitS"), "a reel with no capture clock invented an age")
        self.assertGreater(s["waitS"], CD.TRIAGE_STARVED_AFTER_S)
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.MISSING, why)
        self.assertIn("6.0 h", why)
        self.assertIn("the first tick that found this backlog", why)
        self.assertIn("across 2 relaunches", why)
        self.assertNotIn("this process starting", why)

    def test_an_old_reel_is_judged_by_its_own_age(self):
        """The backlog mark was written by this tick, so waitS is a few seconds. The reel was
        filmed six hours ago. The row follows the reel."""
        self.reel("reel_old", frames=2, age_s=6 * HOUR)
        self.walks = 0
        r = self.tick()
        self.assertEqual(r.get("key"), "walked-nothing", r)
        self.assertEqual(r.get("backlog"), 1, r)
        s = ca.triage_lane_state()
        self.assertLess(s["waitS"], CD.TRIAGE_STARVED_AFTER_S,
                        "premise: the first-backlog mark is this tick, not the reel")
        self.assertGreater(s["reelWaitS"], CD.TRIAGE_STARVED_AFTER_S, s)
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.MISSING, why)
        self.assertIn("oldest waiting reel", why)
        self.assertIn("6.0 h", why)
        self.assertNotIn("this process starting", why)

    def test_a_reel_folded_moments_ago_stays_inside_the_bar_after_a_relaunch(self):
        owed = int(time.time() * 1000) - int(30 * 1000)
        filmed = int(time.time() * 1000) - int(30 * 1000)
        self._mark(owed, oldest=filmed)
        ca._TRIAGE_LANE = _fresh_lane()
        ca._TRIAGE_LANE["ticks"] = 2
        ca._TRIAGE_BACKLOG_SEED = {"read": False}
        s = ca.triage_lane_state()
        self.assertLess(s["waitS"], CD.TRIAGE_STARVED_AFTER_S)
        self.assertLess(s["reelWaitS"], CD.TRIAGE_STARVED_AFTER_S)
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.OK, "a reel filmed 30 s ago read as starved after a relaunch: %s" % why)
        self.assertNotIn("this process starting", why)


class ABootIsNotAStarvedLane(_Base):
    """L1 — at boot the first periodic look lands before the loop's first tick, and the row read
    'NONE RECORDED ... the loop may not be running' after every relaunch."""

    def _five_hour_old_walk(self):
        ts = int((time.time() - 5 * HOUR) * 1000)
        with io.open(RT._store_path(), "w", encoding="utf-8") as fh:
            json.dump({"reel_s_1500000000000_9": {"panels": 0, "frames": 3, "ts": ts, "full": True}}, fh)

    def test_a_lane_that_has_not_ticked_yet_is_unknown_not_missing(self):
        self._five_hour_old_walk()
        self.assertEqual(ca._TRIAGE_LANE["ticks"], 0, "premise: no tick yet in this process")
        st, why = self.doctor_over(2)
        self.assertEqual(st, CD.UNKNOWN, "a console seconds after boot read as starved or clean: %s" % why)
        self.assertIn("has not ticked yet in this process", why)

    def test_a_lane_that_never_ticked_for_hours_is_missing(self):
        self._five_hour_old_walk()
        ca._TRIAGE_LANE["upSince"] -= int(4 * HOUR * 1000)
        st, why = self.doctor_over(2)
        self.assertEqual(st, CD.MISSING, why)
        self.assertIn("NONE RECORDED", why)


class TheLoadBarCanTrip(_Base):
    """L2 — Windows' no-capture bar was 100 on a 0.5 s utilisation sample, which never reads 100.
    Pinned with LITERAL numbers, so a constant pushed to the ceiling goes red."""

    def test_windows_95_percent_busy_refuses_and_89_walks(self):
        ca.IS_WIN = True
        self.reel()
        self.cpu = 95.0
        r = self.tick()
        self.assertEqual(r.get("key"), "cpu-loaded", "a 95%%-busy Windows machine ran triage: %r" % r)
        self.assertIn("95%", r.get("why") or "")
        self.cpu = 89.0
        self.assertEqual(self.tick().get("key"), "surveyed")

    def test_a_windows_override_at_the_ceiling_is_refused_and_one_below_it_takes(self):
        ca.IS_WIN = True
        self.reel()
        self.cpu = 95.0
        os.environ["TV_TRIAGE_WIN_MAX_CPU"] = "100"
        self.assertEqual(self.tick().get("key"), "cpu-loaded", "an override AT the ceiling was taken - "
                                                               "the bar can never trip again")
        os.environ["TV_TRIAGE_WIN_MAX_CPU"] = "97"
        self.assertEqual(self.tick().get("key"), "surveyed", "the override was not read at call time")

    def test_the_mac_load_bar_refuses_at_1_2_times_the_cores(self):
        ca.IS_WIN = False
        ca._cpu_busy_pct = self._saved["_cpu_busy_pct"]   # the REAL helper over a faked load
        self.reel()
        with mock.patch.object(ca.os, "getloadavg", create=True, return_value=(12.0, 1, 1)), \
                mock.patch.object(ca.os, "cpu_count", return_value=10):
            self.assertEqual(self.tick().get("key"), "cpu-loaded",
                             "load 12 on 10 cores (1.2 x) did not trip the Mac bar")
        with mock.patch.object(ca.os, "getloadavg", create=True, return_value=(5.0, 1, 1)), \
                mock.patch.object(ca.os, "cpu_count", return_value=10):
            self.assertEqual(self.tick().get("key"), "surveyed")


class GetSystemTimesIsRead(unittest.TestCase):
    """L3 — _system_times (ctypes GetSystemTimes + the FILETIME high/low combine) never ran in the law.
    The fake fills FILETIMEs whose low words CARRY into the high word between samples, so a combine
    that drops the high DWORD reads garbage."""

    #: idle, kernel, user as (high, low) — deltas 5 / 50 / 50, every one crossing a 2^32 boundary
    SAMPLES = [((3, 0xFFFFFFFE), (9, 0xFFFFFFE0), (1, 0xFFFFFFFF)),
               ((4, 3), (10, 0x12), (2, 49))]

    def setUp(self):
        self._win = ca.IS_WIN
        self.addCleanup(setattr, ca, "IS_WIN", self._win)

    def _windll(self, samples):
        return mock.patch.object(ctypes, "windll", _FakeWindll(_FakeK32(times=samples)), create=True)

    def test_the_high_and_low_words_are_combined(self):
        with self._windll(list(self.SAMPLES)):
            got = ca._system_times()
        self.assertEqual(got, ((3 << 32) | 0xFFFFFFFE, (9 << 32) | 0xFFFFFFE0, (1 << 32) | 0xFFFFFFFF))

    def test_the_windows_busy_reading_crosses_a_high_word_carry(self):
        ca.IS_WIN = True
        with self._windll(list(self.SAMPLES)):
            self.assertEqual(ca._cpu_busy_pct(sample_s=0), 95.0,
                             "the Windows CPU reading is wrong across a FILETIME high-word carry")

    def test_a_refused_call_is_unmeasured(self):
        ca.IS_WIN = True
        with self._windll([]):
            self.assertIsNone(ca._system_times())
            self.assertIsNone(ca._cpu_busy_pct(sample_s=0))


class TheMacCameraIsTheAgent(_Base):
    """L4 — on the Mac control_capture.pid is never written (only capture_win.ps1 writes it), so
    _capture_is_live() is never True there and the ON AIR / MINI refusal was unreachable: triage ran
    beside HIS session with only the load bar in the way. The camera on a Mac is the console's agent."""

    def _mac_agent(self, origin):
        ca._capture_is_live = lambda: False
        self.agent_live = True
        ca._agent_proc, ca._agent_origin = _Proc(), origin

    def test_a_mac_on_air_session_refuses_the_camera(self):
        self.reel()
        self._mac_agent("hand")
        self.assertFalse(ca._capture_is_live(), "premise: no Windows capture pid on a Mac")
        r = self.tick()
        self.assertEqual(r.get("key"), "capture-onair", "triage walked a reel beside his Mac ON AIR: %r" % r)
        self.assertEqual(self.surveyed, [])
        self.assertEqual(self.cpu_asks, 0)

    def test_a_mac_mini_session_refuses_too(self):
        self.reel()
        self._mac_agent("mini")
        self.assertEqual(self.tick().get("key"), "capture-mini")

    def test_a_mac_shadow_reel_is_shared_when_the_cpu_is_quiet(self):
        self.reel()
        self._mac_agent("shadow")
        r = self.tick()
        self.assertEqual(r.get("key"), "surveyed", r)
        self.assertTrue(r.get("shadow"))

    def test_an_agent_this_console_did_not_open_is_his(self):
        self.reel()
        self.agent_live = True
        ca._agent_proc, ca._agent_origin = None, "shadow"
        self.assertEqual(self.tick().get("key"), "capture-unowned")


# ══ 2026-09-28 — the adversarial review of the merged triage+beacon build (792dd6d9), each item
# reproduced before it was fixed, each fix driven through the SHIPPED code and sabotaged below ══

class ALongNativeSessionIsNotAStarvedLane(_Base):
    """Review item 1 (MEDIUM) — Dean plays D2R NATIVELY for hours ("usually" how he plays). Every tick
    refuses 'playing' BY DESIGN and triage catches up when he stops, yet a 3.5 h session turned
    'triage starved' MISSING against the 3 h bar. Driven through the SHIPPED tick, the SHIPPED
    triage_lane_state and the SHIPPED doctor row: playingSince marks the first tick of an UNBROKEN run
    of 'playing', any other outcome ends the run, and a 'playing' lane is judged against its own bar,
    TRIAGE_PLAYING_BAR_S. Pinned with LITERAL hours (3.5 and 13), so a bar moved to either side of
    them goes red."""

    def _hours_of_play(self, hours):
        """He sat down `hours` ago with a reel owed, and every tick since has refused 'playing'."""
        self.reel()
        self.playing = True
        self.assertEqual(self.tick().get("key"), "playing")
        L = ca._TRIAGE_LANE
        self.assertIsNotNone(L.get("playingSince"), "the first 'playing' tick did not start the run")
        L["playingSince"] -= int(HOUR * 1000)
        first = L["playingSince"]
        self.assertEqual(self.tick().get("key"), "playing")
        self.assertEqual(L["playingSince"], first,
                         "a second tick of the SAME unbroken run restarted it - no session could "
                         "ever be measured past one tick")
        L["playingSince"] = first - int((hours - 1.0) * HOUR * 1000)
        L["upSince"] -= int((hours + 1.0) * HOUR * 1000)    # the console was up before he sat down
        # the reels were already owed when he sat down. Process start is not the wait clock.
        L["owedSince"] = int(time.time() * 1000) - int((hours + 0.5) * HOUR * 1000)
        s = ca.triage_lane_state()
        self.assertGreater(s["waitS"], CD.TRIAGE_STARVED_AFTER_S,
                           "premise: the reels have waited past the 3 h starve bar")
        self.assertAlmostEqual(s["playingForS"] / HOUR, hours, delta=0.05)
        return s

    def test_three_and_a_half_hours_of_his_game_reads_ok_standing_aside(self):
        self._hours_of_play(3.5)
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.OK, "a 3.5 h native session read as a starved lane: %s" % why)
        self.assertIn("standing aside for his game - 1 reel(s) wait, 3.5 h", why)

    def test_thirteen_hours_of_unbroken_play_reads_missing(self):
        self._hours_of_play(13.0)
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.MISSING, "a D2R.exe open for 13 h read healthy: %s" % why)
        self.assertIn("13.0 h", why)
        self.assertIn("[playing]", why)

    def test_any_other_outcome_ends_the_run_and_the_old_bar_judges_again(self):
        self.reel()
        self.playing = True
        self.assertEqual(self.tick().get("key"), "playing")
        ca._TRIAGE_LANE["playingSince"] -= int(10 * HOUR * 1000)
        self.playing = False
        self.cpu = 100.0                                   # the Mac bar: load at or above the cores
        self.assertEqual(self.tick().get("key"), "cpu-loaded")
        self.assertIsNone(ca._TRIAGE_LANE["playingSince"], "a CPU refusal did not end the run of play")
        self.assertIsNone(ca.triage_lane_state()["playingForS"])
        self.playing = True
        self.assertEqual(self.tick().get("key"), "playing")
        self.assertLess(ca.triage_lane_state()["playingForS"], 60.0,
                        "a broken run resumed its old start - two sessions read as one unbroken one")
        self.playing = None                                # the probe cannot answer: not "he plays" -
        _run = ca._TRIAGE_LANE["playingSince"]             # and not "he stopped" either (review round 2)
        self.assertEqual(self.tick().get("key"), "playing-unknown")
        self.assertEqual(ca._TRIAGE_LANE["playingSince"], _run,
                         "one probe flake ended the run of play - the 12 h clock restarts on every flake")
        ca._TRIAGE_LANE["upSince"] -= int(4 * HOUR * 1000)
        self.cpu, self.playing = 100.0, False
        self.assertEqual(self.tick().get("key"), "cpu-loaded")
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.MISSING, why)
        self.assertIn("[cpu-loaded]", why, "the old judgement did not come back when he stopped")


class ReviewRoundTwo(_Base):
    """2026-09-28 — the second review of the play bar: a flake never resets the run, a stale 'playing' tick
    never reads 'standing aside', a cloud-route PC is never told to launch D2R, and the walk asks on TIME too."""

    def test_a_flaky_probe_neither_starts_nor_ends_a_run_of_play(self):
        self.reel()
        self.playing = True
        self.tick()
        ca._TRIAGE_LANE["playingSince"] -= int(5 * HOUR * 1000)
        _run = ca._TRIAGE_LANE["playingSince"]
        self.playing = None
        self.assertEqual(self.tick().get("key"), "playing-unknown")
        self.playing = True
        self.tick()
        self.assertEqual(ca._TRIAGE_LANE["playingSince"], _run,
                         "a flake between two 'playing' ticks restarted the run - 5 h of play read as 0")
        self.assertGreater(ca.triage_lane_state()["playingForS"], 4.9 * HOUR)
        ca._TRIAGE_LANE["playingSince"] = None
        self.playing = None
        self.tick()
        self.assertIsNone(ca._TRIAGE_LANE["playingSince"], "a flake STARTED a run of play")

    def test_a_stale_playing_tick_never_reads_standing_aside(self):
        self.reel()
        self.playing = True
        self.tick()
        L = ca._TRIAGE_LANE
        for k in ("playingSince", "lastAt", "lastSkipTs"):
            if isinstance(L.get(k), (int, float)):
                L[k] -= int(5 * HOUR * 1000)
        L["upSince"] -= int(6 * HOUR * 1000)
        s = ca.triage_lane_state()
        self.assertGreater(s["lastAgoS"], 2 * s["everyS"], "PREMISE: the last tick is not stale")
        st, why = self.doctor_over(1)
        self.assertNotIn("standing aside for his game", why,
                         "a loop that stopped ticking 5 h ago still reads 'standing aside for his game'")
        self.assertEqual(st, CD.MISSING, why)

    def test_a_fresh_playing_tick_still_reads_standing_aside(self):
        self.reel()
        self.playing = True
        self.tick()
        ca._TRIAGE_LANE["playingSince"] -= int(2 * HOUR * 1000)
        ca._TRIAGE_LANE["upSince"] -= int(4 * HOUR * 1000)
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.OK, why)
        self.assertIn("standing aside for his game", why)

    def test_a_cloud_route_pc_is_never_told_to_launch_d2r(self):
        with mock.patch.object(ca, "_d2r_running_here", lambda: (False, "a Toolhelp32 process snapshot")), \
                mock.patch.object(ca, "_capture_route_for_wire",
                                  lambda now_ms=None: {"route": "boosteroid", "ageS": 5.0, "why": "", "source": "capture-half"}):
            checks = (ca.farmgate_payload() or {}).get("checks") or []
        row = [c for c in checks if c.get("id") == "d2r_window" or c.get("name") == "d2r_window"]
        self.assertTrue(row, "PREMISE: the gate has no d2r_window row: %r" % checks)
        text = json.dumps(row[0])
        self.assertNotIn("launch D2R", text, "a Boosteroid PC was told to launch a local D2R.exe: %s" % text)
        self.assertIn("boosteroid", text)

    def test_the_walk_asks_on_time_as_well_as_frames(self):
        import retro_triage as RT
        asks = []
        clock = [1000.0]
        def _mono():
            clock[0] += 2.0          # every frame costs 2 s: 100 frames would be 200 s between asks
            return clock[0]
        d = os.path.join(self.world, "reel_s_1510000000000_9")
        os.makedirs(d, exist_ok=True)
        for i in range(12):
            with open(os.path.join(d, "f_17890000%05d.jpg" % i), "wb") as fh:
                fh.write(b"x")
        real_survey = self._edges[2]          # the base stubs RT.survey; this case drives the REAL walk
        with mock.patch.object(RT.time, "monotonic", _mono):
            real_survey([d], lambda f: None, abort=lambda: asks.append(1) or None, abort_every=100,
                        remember_to=False, every_frame=True)
        self.assertGreaterEqual(len(asks), 3, "at 2 s a frame the walk asked only %d time(s) in 12 frames "
                                              "- the 3 s time bar is not honoured" % len(asks))


class ThePlayProbeThatCannotRunSaysSo(_Base):
    """Review item 5 — a lane whose refusals are mostly 'playing-unknown' is BLIND on this machine
    (it will not guess whether he plays), not busy: the row says so in its own sentence, and it still
    refuses. Driven on a Windows-shaped world whose REAL Toolhelp32 probe has its snapshot refused."""

    SENTENCE = "the play probe cannot run on this machine"

    def _blind_windows(self):
        ca.IS_WIN = True
        TVD._toolhelp_d2r_state = self._edges[1]          # the REAL process half
        p = mock.patch.object(ctypes, "windll",
                              _FakeWindll(_FakeK32(snap_raises=OSError("the snapshot was refused"))),
                              create=True)
        p.start()
        self.addCleanup(p.stop)

    def test_a_windows_pc_whose_probe_is_refused_says_the_probe_cannot_run(self):
        self.reel()
        self._blind_windows()
        for _ in range(3):
            self.assertEqual(self.tick().get("key"), "playing-unknown")
        self.assertEqual(self.surveyed, [], "a blind probe walked a reel")
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.OK, "inside the bar: %s" % why)
        self.assertIn(self.SENTENCE, why)
        ca._TRIAGE_LANE["upSince"] -= int(4 * HOUR * 1000)
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.MISSING, "a lane blind to his game for four hours read healthy: %s" % why)
        self.assertIn(self.SENTENCE, why)
        self.assertIn("3 of 3 refusals", why)

    def test_a_lane_refusing_mostly_for_load_does_not_say_it(self):
        """The BASELINE: the sentence is about a blind probe, not about any refusal."""
        self.reel()
        self.cpu = 100.0
        for _ in range(2):
            self.assertEqual(self.tick().get("key"), "cpu-loaded")
        self.playing = None
        self.assertEqual(self.tick().get("key"), "playing-unknown")
        ca._TRIAGE_LANE["upSince"] -= int(4 * HOUR * 1000)
        st, why = self.doctor_over(1)
        self.assertEqual(st, CD.MISSING, why)
        self.assertNotIn(self.SENTENCE, why, "one blind tick in three was called a blind machine")


class TheWalkStopsWhenHeStartsPlaying(_Base):
    """Review item 6 — the play probe ran only at a tick's START, and one walk may run its whole 120 s
    budget beside a game he started a second later. Driven through the SHIPPED tick and the REAL
    survey(): he starts D2R after the walk has looked at 3 frames, and the walk must stop, leave the
    reel owed and record 'playing'."""

    FRAMES = 12

    def setUp(self):
        super(TheWalkStopsWhenHeStartsPlaying, self).setUp()
        RT.survey = self._edges[2]                          # the REAL survey
        every = ca._TRIAGE_ABORT_EVERY_FRAMES
        self.addCleanup(setattr, ca, "_TRIAGE_ABORT_EVERY_FRAMES", every)
        ca._TRIAGE_ABORT_EVERY_FRAMES = 2
        self.gate_calls, self.start_after, self.then = 0, None, True
        ca.stash_screen_open_cached = self._gate

    def _gate(self, f):
        self.gate_calls += 1
        if self.start_after is not None and self.gate_calls >= self.start_after:
            self.playing = self.then                        # he launches the game mid-walk
        return None

    def test_a_walk_beside_no_game_runs_to_the_end(self):
        """The BASELINE: the same walk with no game is a full walk."""
        d = self.reel(frames=self.FRAMES)
        r = self.tick()
        self.assertEqual(r.get("key"), "surveyed", r)
        self.assertEqual(self.gate_calls, self.FRAMES)
        self.assertIs(RT.worth_reading(d), False)

    def test_he_starts_playing_mid_walk_and_the_walk_stops(self):
        d = self.reel(frames=self.FRAMES)
        self.start_after = 3
        r = self.tick()
        self.assertEqual(r.get("key"), "playing", "the walk ran on beside his game: %r" % r)
        self.assertTrue(r.get("midWalk"))
        self.assertGreaterEqual(self.gate_calls, 3, "premise: the walk had started")
        self.assertLess(self.gate_calls, self.FRAMES, "every frame was walked beside his game")
        self.assertIsNone(RT.worth_reading(d), "a half-walked reel was remembered as walked")
        L = ca._TRIAGE_LANE
        self.assertIsNone(L["lastTs"], "a stopped walk stamped a walk")
        self.assertEqual((L["surveyed"], L["backlog"]), (0, 1), "the reel is still owed")
        self.assertEqual(L["skips"], {"playing": 1})
        self.assertIsNotNone(L["playingSince"], "the mid-walk stop did not start the run of play")
        self.assertGreaterEqual(self.pgrep_asks, 2, "the probe was asked only at the tick's start")
        self.start_after, self.playing = None, False       # he stops: the lane catches up
        calls = self.gate_calls
        self.assertEqual(self.tick().get("key"), "surveyed")
        self.assertEqual(self.gate_calls - calls, self.FRAMES, "the catch-up walk was not a full walk")
        self.assertIs(RT.worth_reading(d), False)

    def test_a_probe_that_goes_blind_mid_walk_stops_it_as_unknown(self):
        d = self.reel(frames=self.FRAMES)
        self.start_after, self.then = 3, None
        r = self.tick()
        self.assertEqual(r.get("key"), "playing-unknown", r)
        self.assertIn("UNKNOWN", r.get("why") or "")
        self.assertLess(self.gate_calls, self.FRAMES)
        self.assertIsNone(RT.worth_reading(d))


class TheSurveyStopsWhenAsked(unittest.TestCase):
    """retro_triage.survey's `abort` hook on its own, over a scratch store (remember_to=<root>)."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="triage_abort_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.a, self.b = self._reel("reel_s_1510000000000_1"), self._reel("reel_s_1510000000000_2")
        self.calls = 0

    def _reel(self, name, frames=5):
        d = os.path.join(self.root, name)
        os.makedirs(d)
        for i in range(frames):
            with io.open(os.path.join(d, "f_%d.jpg" % (1510000000000 + i)), "wb") as fh:
                fh.write(b"\xff\xd8\xff")
        return d

    def gate(self, f):
        self.calls += 1
        return "stash" if self.calls == 1 else None         # the first frame carries a panel

    def run_survey(self, abort, every=2):
        return RT.survey([self.a, self.b], self.gate, every_frame=True, remember_to=self.root,
                         abort=abort, abort_every=every)

    def test_no_stop_walks_both_reels(self):
        out = self.run_survey(lambda: None)
        self.assertEqual((out["reels"], out["frames"], out["stoppedEarly"]), (2, 10, False))
        self.assertNotIn("aborted", out)
        self.assertIs(RT.worth_reading(self.b, root=self.root), False)

    def test_a_stop_before_the_first_frame_walks_nothing(self):
        out = self.run_survey(lambda: "he is playing")
        self.assertEqual((out["reels"], out["frames"], self.calls), (0, 0, 0))
        self.assertEqual(out["aborted"], "he is playing")
        self.assertTrue(out["stoppedEarly"])
        self.assertEqual(out["abortedAt"], {"reel": os.path.basename(self.a), "frames": 0})

    def test_a_stop_inside_a_reel_gives_back_its_claims_and_remembers_nothing(self):
        out = self.run_survey(lambda: ("he is playing" if self.calls >= 3 else None))
        self.assertLess(out["frames"], 5, "the reel was walked to its end")
        self.assertEqual(out["aborted"], "he is playing")
        self.assertEqual((out["keep"], out["dispose"], out["panels"], out["byKind"], out["reels"]),
                         ([], [], 0, {}, 0),
                         "a half-walked reel left keep/dispose claims a caller could act on")
        self.assertIsNone(RT.worth_reading(self.a, root=self.root), "a half-walked reel was remembered")
        self.assertEqual(out["abortedAt"]["reel"], os.path.basename(self.a))

    def test_a_stop_between_reels_keeps_the_finished_one(self):
        out = self.run_survey(lambda: ("he is playing" if self.calls >= 5 else None), every=100)
        self.assertEqual(out["reels"], 1)
        self.assertEqual(len(out["dispose"]), 4, "the finished reel's claims were lost")
        self.assertIs(RT.worth_reading(self.a, root=self.root), True, "the finished reel was not kept")
        self.assertIsNone(RT.worth_reading(self.b, root=self.root))
        self.assertEqual(out["abortedAt"], {"reel": os.path.basename(self.b), "frames": 0})

    def test_a_hook_that_raises_stops_the_walk(self):
        def _boom():
            raise RuntimeError("probe exploded")
        out = self.run_survey(_boom)
        self.assertIn("raised RuntimeError", str(out.get("aborted")))
        self.assertEqual(out["frames"], 0)


class TheFarmGateAsksTheSameProbe(_Base):
    """Review item 7 (sibling) — farmgate_payload's d2r_window check ran its own `pgrep`, absent on
    Windows: every Windows PC read 'process check unavailable' whether D2R ran or not. It asks
    _d2r_running_here() now. Driven on a Windows-shaped world where pgrep RAISES, as it does there;
    everything that would reach his machine (the Claude CLI ping, the agent socket, the fleet fetch)
    is stubbed."""

    def _gate(self):
        def _no_pgrep(args, *a, **k):
            if list(args)[:1] == ["pgrep"]:
                raise FileNotFoundError("pgrep")            # Windows has none
            raise AssertionError("the farm gate ran %r in a law" % (args,))
        with mock.patch.object(ca, "status_payload", lambda *a, **k: {"ver": None}), \
                mock.patch.object(ca, "fleet_origin_status", lambda *a, **k: {"behind": 0}), \
                mock.patch.object(ca, "_find_claude_bin", lambda *a, **k: None), \
                mock.patch.object(ca, "_G5", None), \
                mock.patch.object(ca, "_sock_open", lambda *a, **k: False), \
                mock.patch.object(ca.subprocess, "run", _no_pgrep), \
                mock.patch.dict(os.environ, {"TV_CLAUDE_BIN": ""}):
            j = ca.farmgate_payload()
        return next(c for c in j["checks"] if c["id"] == "d2r_window")

    def test_windows_native_d2r_reads_running_not_unavailable(self):
        ca.IS_WIN = True
        TVD._toolhelp_d2r_state = lambda: True
        c = self._gate()
        self.assertTrue(c["ok"], "Dean's native D2R.exe read as %r" % c)
        self.assertIn("D2R.exe is running", c["detail"])
        TVD._toolhelp_d2r_state = lambda: False
        c = self._gate()
        self.assertFalse(c["ok"])
        self.assertIn("not running yet", json.dumps(c))
        TVD._toolhelp_d2r_state = lambda: None
        c = self._gate()
        self.assertFalse(c["ok"])
        self.assertIn("process check unavailable", json.dumps(c))
        self.assertEqual(c["severity"], "warn")


class TheClaudeCliIsNeverLaunched(unittest.TestCase):
    """#189 REG-2559 - the farm-gate law runs with a tripwire `claude` first on PATH (and as ~/.local/bin/claude) and
    the tripwire must never be called. Before the fix it logged `auth status --json` and `-p reply with only: ok`."""

    def test_the_cloud_route_law_never_runs_claude(self):
        if os.environ.get("TV_CLAUDE_TRIPWIRE"):
            self.skipTest("inside the tripwire run")
        import subprocess
        root = tempfile.mkdtemp(prefix="claude_tripwire_")
        self.addCleanup(shutil.rmtree, root, True)
        log = os.path.join(root, "calls")
        for d in (os.path.join(root, "bin"), os.path.join(root, "home", ".local", "bin")):
            os.makedirs(d)
            exe = os.path.join(d, "claude")
            with open(exe, "w") as fh:
                fh.write('#!/bin/sh\necho "$@" >> "%s"\necho "{}"\n' % log)
            os.chmod(exe, 0o755)
        env = dict(os.environ, PATH=os.path.join(root, "bin") + os.pathsep + os.environ.get("PATH", ""),
                   HOME=os.path.join(root, "home"), TV_CLAUDE_TRIPWIRE="1")
        name = "test_triage_runs_beside_a_shadow_reel.ReviewRoundTwo.test_a_cloud_route_pc_is_never_told_to_launch_d2r"
        r = subprocess.run([sys.executable, "-m", "unittest", "-q", name], cwd=HERE, env=env,
                           capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 0, "PREMISE: the cloud-route law itself failed:\n%s" % r.stderr[-1500:])
        calls = open(log).read() if os.path.exists(log) else ""
        self.assertEqual(calls, "", "a law in this file launched the real Claude CLI (his plan): %r" % calls[:300])


RED_PROOF = [
    {
        "why": "#189 REG-2559 - the file stops hiding the Claude CLI: the cloud-route law runs the real `claude -p` again",
        "file": "tv/test_triage_runs_beside_a_shadow_reel.py",
        "find": "_NO_CLAUDE.start()\n",
        "replace": "pass\n",
        "matches": 1,
    },
    {
        "why": "REG-1949 - caught up stops resetting the relaunch count in memory: the next backlog inherits the old one's",
        "file": "tv/control_app.py",
        "find": "    elif owed is None and old is None:\n",
        "replace": "    elif False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 round 2 - a single 'playing-unknown' flake ends the run of play again (the 12 h clock restarts)",
        "file": "control_app.py",
        "find": "    elif key != \"playing-unknown\":\n        L[\"playingSince\"] = None\n",
        "replace": "    else:\n        L[\"playingSince\"] = None\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 round 2 - a stale 'playing' tick reads 'standing aside for his game' again (the freshness guard is gone)",
        "file": "console_doctor.py",
        "find": "            and not isinstance(_pf, bool) and _fresh):\n",
        "replace": "            and not isinstance(_pf, bool)):\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 round 2 - a Boosteroid PC is told to launch a local D2R.exe again",
        "file": "control_app.py",
        "find": "            _cloud = _cr if _cr in (\"boosteroid\", \"geforce-now\") else None\n",
        "replace": "            _cloud = None\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 round 2 - the walk asks only every N frames again (49-130 s between asks at the slow rates)",
        "file": "retro_triage.py",
        "find": "                                or (time.monotonic() - _last_ask[0]) >= ABORT_EVERY_S):\n",
        "replace": "                                or False):\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the old behaviour: any live capture refuses, so a continuously rolling shadow "
               "reel starves triage and reels stack up in TRIAGE",
        "file": "control_app.py",
        "find": "        if door == \"shadow\":\n            shadow = True\n",
        "replace": "        if False:\n            shadow = True\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - triage competes with HIS ON AIR / MINI session",
        "file": "control_app.py",
        "find": "        if door == \"shadow\":\n            shadow = True\n",
        "replace": "        if door in (\"shadow\", \"onair\", \"mini\"):\n            shadow = True\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - an orphan agent's stale shadow origin is believed, so an unknown reel is "
               "treated as the console's",
        "file": "control_app.py",
        "find": "        door = (_rolling_reel() or {}).get(\"door\")\n",
        "replace": "        door = _door_of_origin(_agent_origin)\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - an UNMEASURABLE CPU is read as an idle machine and triage runs blind",
        "file": "control_app.py",
        "find": "    cpu = _cpu_busy_pct()\n",
        "replace": "    cpu = _cpu_busy_pct()\n    cpu = 0.0 if cpu is None else cpu\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - beside a shadow reel triage runs whatever the CPU is doing",
        "file": "control_app.py",
        "find": "    if shadow and cpu > _triage_shadow_max_cpu():\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the shadow bar is read once at import, so his override silently does not take",
        "file": "control_app.py",
        "find": "    raw = (os.environ.get(\"TV_TRIAGE_SHADOW_MAX_CPU\") or \"\").strip()\n",
        "replace": "    raw = \"\"\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - no outcome is recorded: a lane refusing for ever reads like one with nothing to do",
        "file": "control_app.py",
        "find": "    _triage_record(r)\n    return r\n",
        "replace": "    return r\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - refusals are recorded but not COUNTED by reason",
        "file": "control_app.py",
        "find": "        sk[key] = int(sk.get(key) or 0) + 1\n",
        "replace": "        sk[key] = 1\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a tick that raises leaves no trace in the lane",
        "file": "control_app.py",
        "find": "        _triage_record({\"ok\": False, \"key\": \"raised\",\n",
        "replace": "        (lambda _x: None)({\"ok\": False, \"key\": \"raised\",\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the lane is never published, so the doctor (another process) cannot see it",
        "file": "control_app.py",
        "find": "                    \"triage\": triage_lane_state(),\n                    \"walked\": _walked,",
        "replace": "                    \"walked\": _walked,",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a relaunch resets the lane's last walk to never (every ship re-execs the console)",
        "file": "control_app.py",
        "find": "        if stored is not None and (last is None or stored > last):\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a tick that walked nothing stamps lastTs, so a parked lane reads as busy",
        "file": "control_app.py",
        "find": "    if walked:\n        _TRIAGE_LANE[\"lastTs\"] = int(time.time() * 1000)\n",
        "replace": "    if True:\n        _TRIAGE_LANE[\"lastTs\"] = int(time.time() * 1000)\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a reel still being folded is walked and remembered as walked IN FULL",
        "file": "control_app.py",
        "find": "            return (_now_s - os.path.getmtime(p)) < _TRIAGE_SETTLE_S\n",
        "replace": "            return False\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a reel with no frame sorts first and parks the lane for ever",
        "file": "control_app.py",
        "find": "    frameless = [d for d in owed if d not in settling and _n_frames(d) == 0]\n",
        "replace": "    frameless = []\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the Windows path is skipped and getloadavg (absent on Windows) is asked instead",
        "file": "control_app.py",
        "find": "    if IS_WIN:\n        a = _system_times()\n",
        "replace": "    if False:\n        a = _system_times()\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - GetSystemTimes idle counted twice: a pegged machine reads ~half busy",
        "file": "control_app.py",
        "find": "        total = (int(after[1]) - int(before[1])) + (int(after[2]) - int(before[2]))\n",
        "replace": "        total = (int(after[1]) - int(before[1])) + (int(after[2]) - int(before[2])) + di\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - an unknown core count is guessed, so an unmeasurable load reads as a number",
        "file": "control_app.py",
        "find": "    cpus = os.cpu_count()\n    if not cpus:\n        return None\n",
        "replace": "    cpus = os.cpu_count() or 4\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the doctor is blind to a lane starved past the bar",
        "file": "console_doctor.py",
        "find": "    if age_s > TRIAGE_STARVED_AFTER_S:\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a console that publishes no lane state reads as a healthy lane",
        "file": "console_doctor.py",
        "find": "    tri = riv.get(\"triage\")\n    if not isinstance(tri, dict):\n        return UNKNOWN,",
        "replace": "    tri = riv.get(\"triage\")\n    if not isinstance(tri, dict):\n        return OK,",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a river that cannot count TRIAGE is read as holding none",
        "file": "console_doctor.py",
        "find": "    return n if seen else None\n",
        "replace": "    return n if seen else 0\n",
        "matches": 1,
    },
    # ── the adversarial review of 3a495c26, every item reproduced, each fix driven and sabotaged ──
    {
        "why": "H1 - Windows asks pgrep (absent there) instead of the process table, so Dean's native "
               "D2R.exe is never seen",
        "file": "control_app.py",
        "find": "        if IS_WIN:\n            return _tvd._toolhelp_d2r_state(), \"a Toolhelp32 process snapshot\"\n",
        "replace": "        if False:\n            return _tvd._toolhelp_d2r_state(), \"a Toolhelp32 process snapshot\"\n",
        "matches": 1,
    },
    {
        "why": "H1 - the probe reads cap_target.json's label: a Boosteroid window titled 'Diablo' starves "
               "the ALT again",
        "file": "control_app.py",
        "find": "            return _tvd._toolhelp_d2r_state(), \"a Toolhelp32 process snapshot\"\n",
        "replace": "            return _tvd._win_d2r_process_alive(), \"a Toolhelp32 process snapshot\"\n",
        "matches": 1,
    },
    {
        "why": "H1 - the shipped defect itself: the tick asks the two-valued pgrep probe, which swallows "
               "Windows' missing pgrep as 'not playing'",
        "file": "control_app.py",
        "find": "    _playing, _how = _d2r_running_here()\n",
        "replace": "    import tv_diablo as _tvd0\n    _playing, _how = _tvd0._d2r_process_alive(), \"pgrep\"\n",
        "matches": 1,
    },
    {
        "why": "H1 - a probe that cannot run is read as 'he is not playing'",
        "file": "control_app.py",
        "find": "    if _playing is None:\n        return {\"ok\": False, \"key\": \"playing-unknown\",\n",
        "replace": "    if False:\n        return {\"ok\": False, \"key\": \"playing-unknown\",\n",
        "matches": 1,
    },
    {
        "why": "H1 - a refused process snapshot answers False (not running) instead of UNKNOWN",
        "file": "tv_diablo.py",
        "find": "    except Exception:\n        return None\n    return False\n",
        "replace": "    except Exception:\n        return False\n    return False\n",
        "matches": 1,
    },
    {
        "why": "H1 - a missing pgrep answers False (not running) instead of UNKNOWN",
        "file": "tv_diablo.py",
        "find": "    except Exception:\n        return None\n    if out.returncode == 0:\n",
        "replace": "    except Exception:\n        return False\n    if out.returncode == 0:\n",
        "matches": 1,
    },
    {
        "why": "M1 - a walk the store did not keep counts as a walk: the same reel every 90 s for ever, "
               "lastTs stamped, doctor OK",
        "file": "control_app.py",
        "find": "    walked = 1 if (looked and _rt.worth_reading(d) is not None) else 0\n",
        "replace": "    walked = looked\n",
        "matches": 1,
    },
    {
        "why": "M2 - the wait ignores the first tick that found the backlog: a reel folded moments ago "
               "after an idle day reads starved for a day",
        "file": "control_app.py",
        "find": "                  (\"the first tick that found this backlog\", d.get(\"owedSince\")),\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "M2 - the wait ignores the last caught-up tick: ten minutes behind 'playing' after an idle "
               "day reads starved for a day",
        "file": "control_app.py",
        "find": "                  (\"the last tick that found nothing owed\", d.get(\"caughtUpTs\")),\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "M2 - a tick that finds nothing owed never stamps caughtUpTs",
        "file": "control_app.py",
        "find": "            L[\"owedSince\"], L[\"caughtUpTs\"] = None, now\n",
        "replace": "            L[\"owedSince\"], L[\"caughtUpTs\"] = None, None\n",
        "matches": 1,
    },
    {
        "why": "M2 - the doctor judges by the last walk, not by how long the reels waited",
        "file": "console_doctor.py",
        "find": "    wait = tri.get(\"waitS\")\n",
        "replace": "    wait = None\n",
        "matches": 1,
    },
    {
        "why": "L1 - a console seconds after boot reads as a starved (or clean) lane before its first tick",
        "file": "console_doctor.py",
        "find": "    if (tri.get(\"ticks\") == 0 and isinstance(up, (int, float))\n",
        "replace": "    if (False and isinstance(up, (int, float))\n",
        "matches": 1,
    },
    {
        "why": "L2 - the Windows utilisation bar sits AT the ceiling, where a 0.5 s sample never reaches it",
        "file": "control_app.py",
        "find": "_TRIAGE_WIN_MAX_CPU = 90.0\n",
        "replace": "_TRIAGE_WIN_MAX_CPU = 100.0\n",
        "matches": 1,
    },
    {
        "why": "L2 - the Mac load bar is pushed past its own cap and can never trip",
        "file": "control_app.py",
        "find": "\n_TRIAGE_MAX_CPU = 100.0\n",
        "replace": "\n_TRIAGE_MAX_CPU = 101.0\n",
        "matches": 1,
    },
    {
        "why": "L2 - an override AT the ceiling is taken, restoring a bar that cannot trip",
        "file": "control_app.py",
        "find": "                if 0 < v < 100:\n                    return v\n",
        "replace": "                if 0 < v <= 100:\n                    return v\n",
        "matches": 1,
    },
    {
        "why": "L3 - the FILETIME high DWORD is dropped: every reading across a 2^32 carry is garbage",
        "file": "control_app.py",
        "find": "        return tuple((ft.dwHighDateTime << 32) | ft.dwLowDateTime for ft in (idle, kern, user))\n",
        "replace": "        return tuple(ft.dwLowDateTime for ft in (idle, kern, user))\n",
        "matches": 1,
    },
    {
        "why": "L4 - on the Mac the camera refusal keys on the Windows-only capture pid and never fires",
        "file": "control_app.py",
        "find": "    if _capture_is_live() or _agent_alive():\n",
        "replace": "    if _capture_is_live():\n",
        "matches": 1,
    },
    # ── the adversarial review of the merged build 792dd6d9, each item reproduced, fixed and sabotaged ──
    {
        "why": "review 1 - the doctor's playing branch is dropped: Dean's 3.5 h native session reads "
               "'triage starved' MISSING against the 3 h bar",
        "file": "console_doctor.py",
        "find": "    if (tri.get(\"lastKey\") == \"playing\" and isinstance(_pf, (int, float))\n",
        "replace": "    if (False and isinstance(_pf, (int, float))\n",
        "matches": 1,
    },
    {
        "why": "review 1 - any other outcome no longer ends the run of play: two sessions read as one",
        "file": "control_app.py",
        "find": "    elif key != \"playing-unknown\":\n        L[\"playingSince\"] = None\n",
        "replace": "    elif key != \"playing-unknown\":\n        pass\n",
        "matches": 1,
    },
    {
        "why": "review 1 - every 'playing' tick restarts the run, so no session is ever measured past one tick",
        "file": "control_app.py",
        "find": "        if not L.get(\"playingSince\"):\n            L[\"playingSince\"] = now\n",
        "replace": "        if True:\n            L[\"playingSince\"] = now\n",
        "matches": 1,
    },
    {
        "why": "review 1 - the console never publishes how long it has stood aside, so the doctor cannot judge it",
        "file": "control_app.py",
        "find": "        d[\"playingForS\"] = (round(",
        "replace": "        d[\"playingForS\"] = None and (round(",
        "matches": 1,
    },
    {
        "why": "review 5 - a lane blind to his game (the play probe cannot run) reads like any starved lane",
        "file": "console_doctor.py",
        "find": "        if probe_blind:\n            return MISSING,",
        "replace": "        if False:\n            return MISSING,",
        "matches": 1,
    },
    {
        "why": "review 5 - one blind tick in three is called a blind machine (dominance is not a majority)",
        "file": "console_doctor.py",
        "find": "    return (n_key > 0 and 2 * n_key > n_all), n_key, n_all\n",
        "replace": "    return (n_key > 0), n_key, n_all\n",
        "matches": 1,
    },
    {
        "why": "review 6 - the tick passes survey no abort hook: a walk runs 120 s beside a game he just started",
        "file": "control_app.py",
        "find": "                     abort=_triage_walk_should_stop, abort_every=_TRIAGE_ABORT_EVERY_FRAMES)\n",
        "replace": "                     )\n",
        "matches": 1,
    },
    {
        "why": "review 6 - survey asks the hook only between reels, so one long reel walks on beside his game",
        "file": "retro_triage.py",
        "find": "            if walked_here and (walked_here % every == 0\n",
        "replace": "            if False and (walked_here % every == 0\n",
        "matches": 1,
    },
    {
        "why": "review 6 - a walk stopped inside a reel keeps its dispose claims: a caller could drop frames "
               "nobody finished",
        "file": "retro_triage.py",
        "find": "            del out[\"dispose\"][_dp:]\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "review 6 - a walk stopped inside a reel walks on and remembers the reel as walked in full",
        "file": "retro_triage.py",
        "find": "                       abortedAt={\"reel\": os.path.basename(d), \"frames\": walked_here})\n"
                "            break\n",
        "replace": "                       abortedAt={\"reel\": os.path.basename(d), \"frames\": walked_here})\n",
        "matches": 1,
    },
    {
        "why": "review 6 - the tick ignores a stopped walk and records it as a walk that walked nothing",
        "file": "control_app.py",
        "find": "    if _stop:\n        _sk = ",
        "replace": "    if False:\n        _sk = ",
        "matches": 1,
    },
    {
        "why": "review 6 - a probe that goes blind mid-walk is read as 'not playing' and the walk goes on",
        "file": "control_app.py",
        "find": "    if playing is None:\n        return {\"key\": \"playing-unknown\",",
        "replace": "    if False:\n        return {\"key\": \"playing-unknown\",",
        "matches": 1,
    },
    {
        "why": "review 7 - the farm gate runs its own pgrep again: every Windows PC reads 'process check "
               "unavailable' whether D2R runs or not",
        "file": "control_app.py",
        "find": "    _running, _how = _d2r_running_here()\n",
        "replace": "    import tv_diablo as _tvd9\n    _running, _how = _tvd9._pgrep_d2r_state(), \"pgrep\"\n",
        "matches": 1,
    },
    {
        "why": "gap 20 - process start is the wait clock again, so a relaunch hides a standing backlog",
        "file": "control_app.py",
        "find": "                  (\"the first tick that found this backlog\", d.get(\"owedSince\")),\n"
                "                  ]\n",
        "replace": "                  (\"the first tick that found this backlog\", d.get(\"owedSince\")),\n"
                   "                  (\"this process starting\", d.get(\"upSince\"))]\n",
        "matches": 1,
    },
    {
        "why": "gap 20 - the row ignores the reel's own age, so a fresh backlog mark hides an old reel",
        "file": "console_doctor.py",
        "find": "        reel_wait = tri.get(\"reelWaitS\")\n",
        "replace": "        reel_wait = None\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
