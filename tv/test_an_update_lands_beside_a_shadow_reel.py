# -*- coding: utf-8 -*-
"""2026-09-28 — AN UPDATE LANDS BESIDE A SHADOW READER, ON EVERY CONSOLE, BY ITS OWN LOGIC.

HIS WORDS: "the windows needs proper care and attention.. it needs to work perfectly and smoothly
there thats the way we know it will work for dean too. so it needs to work on its own logic" and
"the logic needs to be individually placed and working for each console".

MEASURED 2026-09-28 on his ALT (Windows + Boosteroid, shadow reader always on): the fleet row read
ver v3520 / diskVer v3521 for over two hours, relaunch {armed: true, may: false, why: 'the console is
ON AIR (live) — you are filming'}. Nobody was filming — the SHADOW reader was. It rolls a reel every
hour of play with a ~2 s gap, and nothing_in_flight() read `_agent_mode` + `_agent_alive()` as "you
are filming" without asking whose reel it was. So on any PC where the game stays open, a new build
NEVER landed: the ALT today, Dean whenever he plays long.

WHAT THIS LAW DRIVES — the SHIPPED drift lane (_drift_loop, one iteration), shadow_watch_tick,
_shadow_rollover, the green light and the doctor row, with only the EDGES stubbed (the agent, the
clock, the window finder, the exec), on a TV_HIST fixture, once on a WINDOWS-shaped console (IS_WIN,
the Win32 finder, a bare "Boosteroid" window whose first reads show a D2R HUD word — the ALT) and
once on a MAC-shaped one (the Quartz finder, a named D2R window):

  · shadow reel + a newer build on disk -> the relaunch is HELD, not refused, and says "waiting for
    the shadow reel to close: an update is waiting — the shadow reel closes at its next clean point";
  · the next shadow look closes that reel EARLY (reason "an update is waiting") through
    stop_agent(farewell=False) + the measured-gone check, and fires the green light IN THE SAME
    BREATH — before the watcher could look again;
  · while the update is held (or the relaunch is under way) the watcher opens NO new reel, and says so;
  · ON AIR + drift -> refused, "blocked by his session", nothing closed — at any age;
  · MINI -> the same;
  · a reel whose door cannot be read (an orphan, or a busy lock) -> refused, never guessed shadow's;
  · a hold whose tree goes mid-edit neither closes the reel nor fires (one question, three askers);
  · the doctor row 'the running build is behind the disk': OK inside two hours, MISSING past them
    naming his session / the shadow close failed / the relaunch refused / did not take, UNKNOWN when
    either version cannot be read — and it reads the `since` the drift lane really wrote.

⚠ NOTHING REAL IS TOUCHED. start_agent / stop_agent / _force_kill_all_agents would spawn or kill his
agent, _exec_relaunch_now would REPLACE THIS PROCESS, and the drift lane would git-pull his tree —
every one is stubbed in setUp before anything runs, and the watcher's store is asserted to sit inside
the fixture before anything is written. RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

# the fixture world is declared BEFORE control_app is imported, so nothing resolved at import time
# can describe his tree
_WORLD = tempfile.mkdtemp(prefix="update_beside_shadow_")
os.environ["TV_HIST"] = _WORLD

import control_app as ca  # noqa: E402
import console_doctor as CD  # noqa: E402
import lane_trace as LT  # noqa: E402
import relaunch_hold as rh  # noqa: E402
import tv_diablo as tv  # noqa: E402

MIN = 60 * 1000
HOUR = 60 * MIN
SID = "s_1789100000000_5151"
RUNNING, DISK = "v3520", "v3521"
SHADOW_PHRASE = "waiting for the shadow reel to close"
HIS_PHRASE = "blocked by his session"
CLEAN_POINT = "an update is waiting — the shadow reel closes at its next clean point"


class _Proc(object):
    """An agent child as start_agent leaves it: poll() is None while it runs."""
    pid = 5151

    def __init__(self):
        self.dead = False

    def poll(self):
        return 0 if self.dead else None


class _Stop(BaseException):
    """Ends the drift lane after exactly one iteration (raised from its sleep)."""


class _Base(object):
    """Mixed into two TestCases: one WINDOWS-shaped console, one MAC-shaped. Per console, its own
    logic — his ruling — so every case runs on both."""

    WIN = None          # set by the concrete class

    STUBS = ("_shadow_state", "_agent_alive", "mini_state", "start_agent", "stop_agent",
             "_force_kill_all_agents", "_mini_sid", "_shadow_now_ms", "_screen_recording_ok_quick",
             "ON_AIR_FLOOR_GB", "_agent_proc", "_agent_origin", "_agent_since_ms", "_agent_mode",
             "_stop_inflight", "_exec_relaunch_now", "ui_fault_record", "_CHRON_JOB", "_VAULT_JOB",
             "board_identity_drift", "_tree_is_mid_edit", "_sweep_lock_path", "status_payload",
             "_disk_ver", "_pull_once", "_lane_tick", "IS_WIN", "bare_content_reads",
             "_RELAUNCH_HOLD", "_DRIFT", "time", "_shadow_hour_end_ms")

    def setUp(self):
        self.world = tempfile.mkdtemp(prefix="update_beside_shadow_case_")
        self.addCleanup(shutil.rmtree, self.world, True)
        self._env = {k: os.environ.get(k) for k in ("TV_HIST", "TV_CAPTURE", "TV_SHADOW_ROTATE_S",
                                                     "TV_AUTO_RELAUNCH")}
        os.environ["TV_HIST"] = self.world
        os.environ["TV_CAPTURE"] = "auto"
        os.environ.pop("TV_SHADOW_ROTATE_S", None)
        os.environ.pop("TV_AUTO_RELAUNCH", None)      # the default: updates are not optional
        self._saved = {k: getattr(ca, k) for k in self.STUBS}
        # ⛔ 2026-09-28 — THE PROCESS IS NEVER REPLACED. _drift_loop holds a DIRECT os.execv; a case that reached it
        # (or anything that opened the real console) exec'd the test process and wrote his .tvd_window.pid and
        # .relaunch_receipt.json. For every case here os.execv FAILS LOUDLY instead - a red law, never a new image.
        self._execv = ca.os.execv

        def _no_exec(*a, **k):
            raise AssertionError("a law reached os.execv - it would have REPLACED the test process: %r" % (a[:1],))
        ca.os.execv = _no_exec
        self._finders = (tv.find_d2r_window_mac, tv.find_d2r_window_win)
        self._note = LT.note
        self.addCleanup(self._restore)

        self.now = int(time.time() * 1000)
        # REG-1675 made a shadow reel close at the CLOCK hour; this law's reels begin 10 min back, so run in the first
        # minutes of an hour (v3544's CI, 13:0x UTC) they crossed :00 and the hour closed them - six reds about the
        # clock, not the update. The clock hour is test_a_shadow_session_rolls_over_every_hour's subject; here a
        # reel's hour is its own 60 minutes, whatever the wall clock says.
        ca._shadow_hour_end_ms = lambda since_ms: int(since_ms) + 60 * MIN
        self.alive = False
        self.stop_takes = True
        self.starts, self.stops, self.kills, self.execs, self.faults = [], [], [], [], []
        ca.IS_WIN = bool(self.WIN)
        if self.WIN:
            # his ALT: Boosteroid's own app titles its window only "Boosteroid", and the first reads
            # carry a D2R area word — so the bare-launcher judge says GAME, as it does there
            self.window = (0x2002, "Boosteroid")
            ca.bare_content_reads = lambda: [{"scene": "town", "area": "Rogue Encampment"}] * 3
        else:
            self.window = (2002, "Diablo II: Resurrected")
            ca.bare_content_reads = lambda: None
        tv.find_d2r_window_mac = lambda *a, **k: self.window
        tv.find_d2r_window_win = lambda *a, **k: self.window
        ca._shadow_state = lambda: {"on": True, "available": True, "recording": self.alive}
        ca._agent_alive = lambda: self.alive
        self.mini_running = False
        ca.mini_state = lambda: {"running": self.mini_running}
        ca._shadow_now_ms = lambda: self.now
        ca._screen_recording_ok_quick = lambda: True
        ca.ON_AIR_FLOOR_GB = 0
        ca._mini_sid = lambda: SID
        ca._stop_inflight = False
        ca._agent_proc, ca._agent_origin, ca._agent_since_ms, ca._agent_mode = None, "hand", None, "off"
        ca.start_agent = self._start
        ca.stop_agent = self._stop
        ca._force_kill_all_agents = lambda *a, **k: (self.kills.append(a) or {"ok": True, "msg": "stub"})
        # ⛔ THE EXEC. The real one replaces this process image. Recorded, never run.
        ca._exec_relaunch_now = lambda: self.execs.append(self.now)
        ca.ui_fault_record = lambda *a, **k: self.faults.append((a, k))
        ca._CHRON_JOB = {"running": False}
        ca._VAULT_JOB = {"running": False}
        ca.board_identity_drift = lambda: {"state": "ok", "why": "the world is pinned by the law"}
        self.mid_edit = (False, "")
        ca._tree_is_mid_edit = lambda *a, **k: self.mid_edit
        ca._sweep_lock_path = lambda: os.path.join(self.world, "no.sweep.lock")
        self.running, self.disk = RUNNING, DISK
        ca.status_payload = lambda *a, **k: {"ver": self.running}
        ca._disk_ver = lambda: self.disk
        ca._pull_once = lambda: None                  # ⛔ never git-pull his tree
        ca._lane_tick = lambda *a, **k: None
        LT.note = lambda *a, **k: True
        ca._RELAUNCH_HOLD = rh.new_state()
        ca._DRIFT = {"checked": None, "running": None, "disk": None, "drift": None,
                     "say": "not measured yet", "since": None, "relaunch": None}
        self.path = ca._shadow_watch_path()
        self.assertTrue(os.path.realpath(self.path).startswith(os.path.realpath(self.world)),
                        "TV_HIST was not honoured (%s) - REFUSING to run against a real store" % self.path)

    def _restore(self):
        for k, v in self._saved.items():
            setattr(ca, k, v)
        ca.os.execv = self._execv
        tv.find_d2r_window_mac, tv.find_d2r_window_win = self._finders
        LT.note = self._note
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    # ── the edges, doing to the state what the real ones do ──────────────────────────────────
    def _start(self, *a, **k):
        self.starts.append(dict(k))
        self.begin(k.get("origin", "hand"), self.now)
        return {"ok": True, "msg": "started", "origin": k.get("origin", "hand")}

    def _stop(self, *a, **k):
        self.stops.append(dict(k))
        if self.stop_takes:
            self.alive = False
            ca._agent_mode = "off"
            if ca._agent_proc is not None:
                ca._agent_proc.dead = True
            return {"ok": True, "msg": "session saved · off", "sessionSaved": True}
        return {"ok": True, "msg": "stop requested · forcing", "bridgeDown": False}

    def begin(self, origin, since, owned=True):
        """A reel rolling. owned=False is an ORPHAN: alive, live, but not opened by this console."""
        ca._agent_proc = _Proc() if owned else None
        ca._agent_origin = origin
        ca._agent_since_ms = since
        ca._agent_mode = "live"
        self.alive = True

    def drift_look(self):
        """ONE iteration of the shipped _drift_loop: pull (stubbed), measure, decide, hold/refuse."""
        slept = []

        class _Clock(object):
            def __getattr__(s, n):
                return getattr(time, n)

            def sleep(s, x):
                slept.append(x)
                raise _Stop()

        ca.time = _Clock()
        try:
            ca._drift_loop()
        except _Stop:
            pass
        finally:
            ca.time = self._saved["time"]
        return ca.drift_state()

    def record(self):
        with io.open(self.path, encoding="utf-8") as fh:
            return json.load(fh)

    def doctor(self, drift=None):
        """The SHIPPED doctor row, handed the /api/status the console would serve."""
        st = {"ver": self.running, "drift": drift if drift is not None else ca.drift_state(),
              "moduleFreshness": {}}
        saved = CD._get
        CD._get = lambda path, timeout=4: st if path == "/api/status" else None
        try:
            return CD._check_the_running_build_is_not_behind_the_disk()
        finally:
            CD._get = saved


class _Cases(_Base):

    def test_premise_the_console_is_the_shape_it_claims(self):
        """A 'Windows' run that silently asked the Quartz finder would be a Mac run twice."""
        def _wrong(*a, **k):
            raise AssertionError("the %s console asked the other OS's window finder"
                                 % ("Windows" if self.WIN else "Mac"))
        if self.WIN:
            tv.find_d2r_window_mac = _wrong
        else:
            tv.find_d2r_window_win = _wrong
        pre = ca.capture_preflight("shadow", look_for_window=True)
        self.assertIs(pre.get("windowSeen"), True, pre)
        self.assertEqual(pre.get("windowLabel"), self.window[1])
        if self.WIN:
            self.assertTrue(tv.label_is_bare_boosteroid(pre.get("windowLabel")),
                            "premise: the ALT's window is titled only 'Boosteroid'")
            self.assertIs(ca._bare_hud_verdict(pre), True,
                          "premise: the ALT's first reads show a D2R HUD word, so shadow films it")
        else:
            self.assertIsNone(ca._bare_hud_verdict(pre), "a named D2R window is not the bare launcher")

    # ── 1. shadow + drift -> HELD, closed early, green light in the same breath, no reopen ────
    def test_a_shadow_reel_holds_the_update_then_closes_early_and_the_green_light_fires(self):
        self.begin("shadow", self.now - 10 * MIN)
        d = self.drift_look()
        self.assertIs(d.get("drift"), True, "premise: the lane saw the newer build: %r" % d)
        hold = ca._RELAUNCH_HOLD
        self.assertTrue(hold.get("held"),
                        "a waiting build beside a SHADOW reel was REFUSED, not held - the ALT's "
                        "2-hour v3520/v3521 wait: %r" % (d.get("relaunch"),))
        self.assertEqual(hold.get("asked"), "drift")
        self.assertIn(CLEAN_POINT, hold.get("why") or "",
                      "the hold does not say the shadow reel closes at its next clean point: %r"
                      % hold.get("why"))
        rl = d.get("relaunch") or {}
        self.assertEqual(rl.get("waiting"), SHADOW_PHRASE, "the relaunch state does not say "
                         "'waiting for the shadow reel to close': %r" % rl)
        self.assertEqual(self.stops, [], "the drift lane closed the reel itself - the rollover owns that")
        self.assertEqual(self.execs, [], "it relaunched with a shadow reel still rolling")

        beacon = ca._relaunch_report() or {}
        self.assertTrue(str(beacon.get("why") or "").startswith(SHADOW_PHRASE),
                        "the fleet beacon's why does not LEAD with the class, and the worker keeps "
                        "only 160 chars of it: %r" % beacon)
        self.assertLessEqual(len(beacon.get("why") or ""), 160)

        r = ca.shadow_watch_tick()                    # the very next shadow look
        self.assertTrue(r.get("rotated"), "a 10-minute shadow reel was not closed for the waiting "
                                          "update: %r" % (r,))
        self.assertEqual(r.get("reason"), "an update is waiting")
        self.assertEqual(self.stops, [{"farewell": False}],
                         "the early close did not go through stop_agent(farewell=False): %r" % self.stops)
        self.assertEqual(self.kills, [])
        self.assertEqual(len(self.execs), 1,
                         "the green light did not fire IN THE SAME BREATH as the close - the watcher "
                         "could reopen a reel on the old build first: execs=%r say=%r"
                         % (self.execs, r.get("fireSay")))
        self.assertTrue(r.get("fired"))
        rec = self.record()
        self.assertEqual(rec.get("updateClosedAt"), self.now)
        self.assertEqual(rec.get("updateCloses"), 1)
        self.assertEqual(rec.get("rotations"), 1, "the early close is lane work and was not counted")

        self.now += ca._SHADOW_ROTATE_RELOOK_S * 1000   # the watcher's relook, seconds later
        r2 = ca.shadow_watch_tick()
        self.assertEqual(self.starts, [], "a new reel opened on the OLD build while the relaunch "
                                          "was under way: %r" % (r2,))
        self.assertTrue(r2.get("held"), r2)
        self.assertIn("new build", r2.get("why") or "", "the refusal does not say so: %r" % (r2,))
        self.assertEqual(len(self.execs), 1, "the relaunch fired twice")

    def test_no_reel_opens_while_the_update_is_held_and_it_says_so(self):
        """The green light LOSES the race (another thread is asking): the hold stays, and the watcher
        still opens nothing on the old build — then the next look fires it."""
        self.begin("shadow", self.now - 10 * MIN)
        self.drift_look()
        self.assertTrue(ca._RELAUNCH_HOLD.get("held"))
        ca._GREEN_LIGHT_LOCK.acquire()
        try:
            r = ca.shadow_watch_tick()
            self.assertTrue(r.get("rotated"), r)
            self.assertEqual(self.execs, [], "premise: the green light was busy on another thread")
            self.assertTrue(ca._RELAUNCH_HOLD.get("held"), "premise: the update is still held")
            self.now += ca._SHADOW_ROTATE_RELOOK_S * 1000
            r2 = ca.shadow_watch_tick()
        finally:
            ca._GREEN_LIGHT_LOCK.release()
        self.assertEqual(self.starts, [], "the watcher opened a reel on the old build while an "
                                          "update was held: %r" % (r2,))
        self.assertIn("an update is waiting", r2.get("why") or "")
        self.assertIn("next reel opens on the new build", r2.get("why") or "")
        self.assertEqual(self.record().get("updateHeldAt"), self.now, "the refusal was not noted")
        self.now += 20 * 1000
        ca.shadow_watch_tick()                        # the lock is free: this look fires it
        self.assertEqual(len(self.execs), 1, "a held update with nothing in its way never fired")
        self.assertEqual(self.starts, [])

    def test_premise_without_an_update_the_shadow_reel_keeps_its_hour(self):
        """Baseline, so the cases above are firing on the UPDATE and not on any shadow reel."""
        self.running = self.disk = DISK
        self.begin("shadow", self.now - 10 * MIN)
        self.drift_look()
        self.assertFalse(ca._RELAUNCH_HOLD.get("held"))
        r = ca.shadow_watch_tick()
        self.assertEqual(self.stops, [], "a 10-minute shadow reel was cut with no update waiting: %r" % r)
        self.assertEqual(self.execs, [])

    # ── 2. his sessions keep "never mid-film" ───────────────────────────────────────────────
    def test_ON_AIR_plus_drift_is_REFUSED_and_nothing_is_closed(self):
        self.begin("hand", self.now - 180 * MIN)
        d = self.drift_look()
        self.assertFalse(ca._RELAUNCH_HOLD.get("held"), "an update was HELD against his ON AIR "
                                                        "session: %r" % (d.get("relaunch"),))
        rl = d.get("relaunch") or {}
        self.assertEqual(rl.get("blocker"), "his-session", rl)
        self.assertTrue(str(rl.get("why") or "").startswith(HIS_PHRASE), rl)
        self.assertIn("you are filming", rl.get("why") or "")
        # and a hold made by someone else (the button) still never cuts his reel
        rh.hold(ca._RELAUNCH_HOLD, "pressed", "button", now=time.time())
        ca.shadow_watch_tick()
        self.assertEqual(self.stops, [], "his 3-hour ON AIR session was cut for an update")
        self.assertEqual(self.execs, [], "it relaunched mid-film")
        self.assertTrue(str((ca._relaunch_report() or {}).get("why") or "").startswith(HIS_PHRASE))

    def test_MINI_plus_drift_is_REFUSED_and_nothing_is_closed(self):
        self.begin("mini", self.now - 5 * MIN)
        self.mini_running = True
        d = self.drift_look()
        self.assertFalse(ca._RELAUNCH_HOLD.get("held"), "an update was held against his MINI")
        self.assertEqual((d.get("relaunch") or {}).get("blocker"), "his-session")
        rh.hold(ca._RELAUNCH_HOLD, "pressed", "button", now=time.time())
        ca.shadow_watch_tick()
        self.assertEqual(self.stops, [], "his MINI was cut for an update")
        self.assertEqual(self.execs, [])

    # ── 3. UNKNOWN door = refuse, never a guess ─────────────────────────────────────────────
    def test_an_unreadable_door_is_REFUSED_never_taken_for_shadow(self):
        # an ORPHAN: alive and live, its origin says shadow, but this console never opened it
        self.begin("shadow", self.now - 10 * MIN, owned=False)
        d = self.drift_look()
        self.assertFalse(ca._RELAUNCH_HOLD.get("held"), "a reel whose door cannot be read was "
                                                        "taken for shadow's: %r" % (d.get("relaunch"),))
        rl = d.get("relaunch") or {}
        self.assertEqual(rl.get("blocker"), "his-session", rl)
        self.assertIn("cannot be read", rl.get("why") or "")
        rh.hold(ca._RELAUNCH_HOLD, "pressed", "button", now=time.time())
        ca.shadow_watch_tick()
        self.assertEqual(self.stops, [], "an orphan reel was cut on a guess")
        self.assertEqual(self.execs, [])

    def test_a_busy_lock_reads_as_an_unknown_door_and_refuses(self):
        self.begin("shadow", self.now - 10 * MIN)
        got = threading.Event()
        done = threading.Event()

        def _hold_lock():
            with ca._lock:
                got.set()
                done.wait(10)
        t = threading.Thread(target=_hold_lock)
        t.start()
        try:
            got.wait(5)
            parts = []
            ok, why = ca.nothing_in_flight(parts=parts)
        finally:
            done.set()
            t.join(10)
        self.assertFalse(ok)
        self.assertEqual(ca._relaunch_blocker(ok, parts), "his-session",
                         "a door that could not be read this look was not refused as his: %r" % parts)

    # ── 4. one question, three askers ───────────────────────────────────────────────────────
    def test_a_hold_whose_tree_goes_mid_edit_neither_closes_the_reel_nor_fires(self):
        self.begin("shadow", self.now - 10 * MIN)
        self.drift_look()
        self.assertTrue(ca._RELAUNCH_HOLD.get("held"), "premise: the update is held")
        self.mid_edit = (True, "the working tree is mid-edit (tv/control_app.py)")
        r = ca.shadow_watch_tick()
        self.assertEqual(self.stops, [], "a reel was closed for a relaunch that cannot fire (the tree "
                                         "is mid-edit) - the rollover asked a different question "
                                         "than the green light: %r" % (r,))
        fired, say = ca.relaunch_green_light_tick()
        self.assertFalse(fired, "the green light fired a drift hold past the mid-edit interlock "
                                "the drift lane itself refuses on: %r" % say)
        self.assertEqual(self.execs, [])

    # ── 5. the heart: the doctor row ────────────────────────────────────────────────────────
    def test_the_doctor_reads_the_wait_the_drift_lane_really_wrote(self):
        self.begin("hand", self.now - 10 * MIN)
        self.drift_look()
        state, why = self.doctor()
        self.assertEqual(state, "ok", "a build 0 minutes behind read as a fault: %s" % why)
        # three hours pass with him on air: move the lane's FIRST sighting back, and look again —
        # the second look must keep the first sighting, or no wait could ever reach two hours
        with ca._PRUNE_LOCK:
            ca._DRIFT["since"] -= 3 * HOUR
        self.drift_look()
        state, why = self.doctor()
        self.assertEqual(state, "missing", "a build 3 h behind the disk read %s: %s" % (state, why))
        self.assertIn("HIS SESSION", why, "the row does not name WHY: %s" % why)
        self.assertIn(RUNNING, why)
        self.assertIn(DISK, why)

    def test_a_stop_that_did_not_take_is_named_SHADOW_CLOSE_FAILED(self):
        self.begin("shadow", self.now - 10 * MIN)
        self.drift_look()
        self.stop_takes = False
        r = ca.shadow_watch_tick()
        self.assertFalse(r.get("rotated"), "a close that did not take was reported as a close: %r" % r)
        self.assertEqual(self.execs, [], "it relaunched while the shadow reel was still rolling")
        rec = self.record()
        self.assertEqual(rec.get("updateCloseFailedAt"), self.now)
        with ca._PRUNE_LOCK:
            ca._DRIFT["since"] -= 3 * HOUR
        state, why = self.doctor()
        self.assertEqual(state, "missing", why)
        self.assertIn("SHADOW CLOSE FAILED", why, why)


class AnUpdateLandsQuietlyBesideHisGame(_Base):
    """2026-09-28 — the review of this change (medium): a relaunch from the shadow side lands while he PLAYS, and
    the new console opened FULLSCREEN and activated itself, pulling focus off D2R / Boosteroid mid-fight. Now the
    shadow side marks the exec (TV_QUIET_RELAUNCH crosses os.execv in the environment) and the new image opens
    minimized, unfocused, windowed - read once. And an EXPIRED hold closes no reel (reproduced: two early cuts
    for one update)."""

    def tearDown(self):
        os.environ.pop("TV_QUIET_RELAUNCH", None)

    def test_a_green_light_fired_from_the_shadow_side_marks_the_relaunch_quiet(self):
        real = ca.relaunch_green_light_tick
        try:
            ca.relaunch_green_light_tick = lambda: (True, "fired")
            self.assertEqual(ca._fire_green_light_now(), (True, "fired"))
            self.assertTrue(os.environ.get("TV_QUIET_RELAUNCH"),
                            "a relaunch fired beside his game carries no quiet mark - it opens fullscreen over D2R")
            os.environ.pop("TV_QUIET_RELAUNCH", None)
            ca.relaunch_green_light_tick = lambda: (False, "still held")
            ca._fire_green_light_now()
            self.assertIsNone(os.environ.get("TV_QUIET_RELAUNCH"),
                              "a green light that did NOT fire left the quiet mark for some later relaunch")
        finally:
            ca.relaunch_green_light_tick = real

    def test_a_quiet_boot_opens_minimized_unfocused_and_never_fullscreen(self):
        """Checked on _control_window_kwargs - the pure options function. ⛔ NEVER drive open_control_window in a
        law: it arms the console's real watchers, and a first cut of this case ran the real drift loop, which
        os.execv'd the test process and wrote his .tvd_window.pid and .relaunch_receipt.json (restored)."""
        os.environ.pop("TV_WINDOWED", None)
        os.environ["TV_QUIET_RELAUNCH"] = "an update landed beside a shadow reel while the game was on screen"
        kw = ca._control_window_kwargs("http://127.0.0.1:1/")
        self.assertEqual((kw.get("minimized"), kw.get("focus"), bool(kw.get("fullscreen"))), (True, False, False),
                         "a relaunch beside his game opens as %r - it takes the screen from D2R" % kw)
        self.assertIsNone(os.environ.get("TV_QUIET_RELAUNCH"), "the quiet mark was not read ONCE - it lingers")
        kw = ca._control_window_kwargs("http://127.0.0.1:1/")
        self.assertTrue(kw.get("fullscreen") and not kw.get("minimized"),
                        "an ordinary open no longer opens as it always did: %r" % kw)

    def test_a_law_that_reaches_exec_fails_instead_of_replacing_the_process(self):
        """The harness itself: a path that reaches os.execv inside these laws must go RED, never exec. A path that
        cannot exist, so even a missing stub raises (OSError) rather than replacing this process."""
        with self.assertRaises(AssertionError):
            ca.os.execv("/nonexistent/never-a-binary", ["never"])

    def test_the_window_is_opened_with_those_options(self):
        """The join: open_control_window takes its options from _control_window_kwargs, once."""
        import inspect
        src = inspect.getsource(ca.open_control_window)
        self.assertEqual(src.count("_control_window_kwargs(url)"), 1,
                         "open_control_window no longer asks _control_window_kwargs - the quiet boot is unjoined")

    def test_an_expired_hold_does_not_keep_the_door_shut(self):
        """The door's own guard: a hold past its expiry must not stop the watcher opening his next reel."""
        real = ca._green_light_question
        ca._green_light_question = lambda: (False, "only a shadow reel is in the way", "shadow")
        try:
            ca._RELAUNCH_HOLD.clear()
            ca._RELAUNCH_HOLD.update({"held": True, "expiresTs": time.time() + 600})
            self.assertIsNotNone(ca._shadow_door_held_for_update()[0], "PREMISE: a live hold does not shut the door")
            ca._RELAUNCH_HOLD["expiresTs"] = time.time() - 1
            self.assertEqual(ca._shadow_door_held_for_update(), (None, None),
                             "an EXPIRED hold still keeps the shadow door shut - no reel would ever open again")
        finally:
            ca._green_light_question = real

    def test_an_expired_hold_closes_no_reel(self):
        self.begin("shadow", self.now - 10 * MIN)
        self.drift_look()
        self.assertTrue(ca._RELAUNCH_HOLD.get("held"), "PREMISE: the update is not held")
        ca._RELAUNCH_HOLD["expiresTs"] = time.time() - 1
        r = ca.shadow_watch_tick()
        self.assertFalse(r.get("rotated"), "an EXPIRED hold still cut the shadow reel early: %r" % (r,))
        self.assertEqual(self.stops, [], "the expired hold closed the reel")


class TheQuietUpdateOnAWindowsConsole(AnUpdateLandsQuietlyBesideHisGame, unittest.TestCase):
    WIN = True


class TheQuietUpdateOnAMacConsole(AnUpdateLandsQuietlyBesideHisGame, unittest.TestCase):
    WIN = False


class TheRowOnAWindowsConsole(_Cases, unittest.TestCase):
    WIN = True


class TheRowOnAMacConsole(_Cases, unittest.TestCase):
    WIN = False


class TheDoctorVerdictIsPure(unittest.TestCase):
    """The pure half, every state, no console. [[unknown-stays-unknown]]"""

    NOW = 1789200000000

    def v(self, **k):
        base = dict(running=RUNNING, disk=DISK, since_ms=None, now_ms=self.NOW)
        base.update(k)
        return CD.behind_the_disk_verdict(**base)

    def test_in_sync_is_OK(self):
        self.assertEqual(self.v(disk=RUNNING)[0], "ok")

    def test_an_unreadable_version_is_UNKNOWN(self):
        """⚠ WITH a three-hour `since` and a named cause, so the ONLY thing standing between this
        input and a confident MISSING is the unreadable version. Without the since, a missing stamp
        fell through to the older-console UNKNOWN and the case could not tell the guard was gone —
        heart2 proved it BLIND on the first run. [[regression-guard]] §5a"""
        since = self.NOW - 3 * HOUR
        rl = {"blocker": "work", "why": "a chronicle sweep is reading"}
        for k in ({"running": None}, {"disk": None}, {"running": "", "disk": ""}):
            st, why = self.v(since_ms=since, relaunch=rl, **k)
            self.assertEqual(st, "unknown", "%r was graded (%s): %s" % (k, st, why))
            self.assertIn("cannot be read", why)

    def test_inside_two_hours_is_OK_and_past_them_is_MISSING(self):
        bar = CD.BEHIND_THE_DISK_MAX_S * 1000
        self.assertEqual(self.v(since_ms=self.NOW - bar + 60000)[0], "ok")
        st, why = self.v(since_ms=self.NOW - bar - 60000,
                         relaunch={"blocker": "work", "why": "a chronicle sweep is reading"})
        self.assertEqual(st, "missing", why)
        self.assertIn("RELAUNCH REFUSED", why)
        self.assertIn("a chronicle sweep is reading", why)

    def test_each_cause_is_named(self):
        since = self.NOW - 3 * HOUR
        cases = (
            ({"blocker": "his-session", "why": HIS_PHRASE + ": the console is ON AIR (live)"},
             None, "HIS SESSION"),
            ({"blocker": "shadow", "why": SHADOW_PHRASE}, None, "SHADOW CLOSE FAILED"),
            ({"blocker": "shadow", "why": SHADOW_PHRASE},
             {"updateCloseFailedAt": since + 60000, "updateCloseWhy": "STILL ROLLING"},
             "STILL ROLLING"),
            ({"blocker": "exec-failed", "why": "the exec did not take"}, None,
             "THE RELAUNCH DID NOT TAKE"),
            ({"blocker": "mid-edit", "why": "the working tree is mid-edit"}, None, "RELAUNCH REFUSED"),
            (None, None, "does not publish why"),
        )
        for rl, watch, needle in cases:
            st, why = self.v(since_ms=since, relaunch=rl, watch=watch)
            self.assertEqual(st, "missing", "%r -> %s" % (rl, why))
            self.assertIn(needle, why, "%r did not name %r: %s" % (rl, needle, why))

    def test_an_OLDER_console_is_bounded_not_guessed(self):
        """No `since` (a console that predates it): the disk write is a LOWER bound, the load an
        UPPER bound; between them is UNKNOWN, said so."""
        self.assertEqual(self.v(written_ms=self.NOW - 3 * HOUR)[0], "missing")
        self.assertIn("at least", self.v(written_ms=self.NOW - 3 * HOUR)[1])
        self.assertEqual(self.v(loaded_ms=self.NOW - 1 * HOUR, written_ms=self.NOW - 30 * MIN)[0], "ok")
        self.assertEqual(self.v(loaded_ms=self.NOW - 5 * HOUR, written_ms=self.NOW - 30 * MIN)[0],
                         "unknown")
        self.assertEqual(self.v()[0], "unknown", "no reading at all was graded")

    def test_the_row_is_registered_where_the_heart_looks(self):
        names = [n for n, _ in CD.CHECKS]
        self.assertEqual(names.count("the running build is behind the disk"), 1)
        self.assertIn("the running build is behind the disk", CD.WATCHES)
        import corroborate as C
        self.assertIn("the running build is behind the disk",
                      set(C.COVERED_BY) | set(C.NO_JOINT_YET))


# #173 (REG-2940) - NoLawOpensTheRealConsole (no law file CALLS open_control_window / start_background_watchers)
# globs every test_*.py, so it lives in test_no_law_opens_the_real_console.py and this law's proofs can be saved.


RED_PROOF = [
    {
        "why": "2026-09-28 review - an EXPIRED hold cuts the shadow reel early again (two cuts for one update)",
        "file": "control_app.py",
        "find": "    if _hold_expired():\n        return False, \"the held update has EXPIRED",
        "replace": "    if False:\n        return False, \"the held update has EXPIRED",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a law may reach os.execv without failing: it would REPLACE the test process",
        "file": "test_an_update_lands_beside_a_shadow_reel.py",
        "find": "        ca.os.execv = _no_exec\n",
        "replace": "        ca.os.execv = lambda *a, **k: None\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 review - a relaunch beside his game opens fullscreen and takes focus again (no quiet mark)",
        "file": "control_app.py",
        "find": "    os.environ[\"TV_QUIET_RELAUNCH\"] = \"an update landed beside a shadow reel while the game was on screen\"\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "2026-09-28 review - the new image ignores the quiet mark and opens fullscreen over the game",
        "file": "control_app.py",
        "find": "        kwargs.update(minimized=True, focus=False)\n",
        "replace": "        pass\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 review - an EXPIRED hold keeps the shadow door shut: the watcher never opens another reel",
        "file": "control_app.py",
        "find": "    if not _RELAUNCH_HOLD.get(\"held\") or _hold_expired():\n        return None, None\n",
        "replace": "    if not _RELAUNCH_HOLD.get(\"held\"):\n        return None, None\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the ALT's defect: a SHADOW reel read as 'you are filming', so the update is "
               "refused on every look and never lands on a console where the game stays open",
        "file": "control_app.py",
        "find": "            if _door == \"shadow\":\n                _add(\"shadow\",",
        "replace": "            if False:\n                _add(\"shadow\",",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the drift lane refuses instead of HOLDING a waiting build beside a shadow reel",
        "file": "control_app.py",
        "find": "                if _dd.get(\"blocker\") == \"shadow\":\n",
        "replace": "                if False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the rollover never closes a shadow reel early for a waiting update",
        "file": "control_app.py",
        "find": "    _upd, _upd_why = _an_update_waits_on_the_shadow_reel()\n",
        "replace": "    _upd, _upd_why = False, \"\"\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the green light is not fired in the same breath as the early close, so the "
               "watcher can reopen a reel on the old build first",
        "file": "control_app.py",
        "find": "            fired, fsay = _fire_green_light_now()\n",
        "replace": "            fired, fsay = False, \"sabotaged\"\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the watcher reopens a reel on the old build while an update is held",
        "file": "control_app.py",
        "find": "    _uwhy, _ublk = _shadow_door_held_for_update()\n",
        "replace": "    _uwhy, _ublk = None, None\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - his ON AIR / MINI session (or an unreadable door) is held like a shadow reel",
        "file": "control_app.py",
        "find": "    if kinds == {\"shadow\"}:\n        return \"shadow\"\n",
        "replace": "    if kinds <= {\"shadow\", \"session\", \"door-unknown\"}:\n        return \"shadow\"\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a reel whose door cannot be read is guessed to be the shadow reader's",
        "file": "control_app.py",
        "find": "                _door = _rolling_reel().get(\"door\")\n",
        "replace": "                _door = _rolling_reel().get(\"door\") or \"shadow\"\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the green light releases a DRIFT hold on a different question than the drift "
               "lane asked, so a reel is closed and the exec fired past the mid-edit interlock",
        "file": "control_app.py",
        "find": "        if _RELAUNCH_HOLD.get(\"asked\") == \"drift\":\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - every drift look re-stamps its first sighting, so no wait can ever reach two hours",
        "file": "control_app.py",
        "find": "            _since = _since or _now_ms\n",
        "replace": "            _since = _now_ms\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the beacon's why stops leading with 'waiting for the shadow reel to close'",
        "file": "control_app.py",
        "find": "_WAITING_FOR_SHADOW = \"waiting for the shadow reel to close\"\n",
        "replace": "_WAITING_FOR_SHADOW = \"the console is ON AIR\"\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a failed early close leaves no record, so the doctor cannot name it",
        "file": "control_app.py",
        "find": "rotateFailedAt=now, updateCloseFailedAt=now,",
        "replace": "rotateFailedAt=now,",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the doctor calls a build that waited three hours a normal wait",
        "file": "console_doctor.py",
        "find": "    if age_s <= BEHIND_THE_DISK_MAX_S:\n",
        "replace": "    if True:\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the doctor grades a version nobody could read",
        "file": "console_doctor.py",
        "find": "    if not running or not disk:\n        return UNKNOWN, (",
        "replace": "    if False:\n        return UNKNOWN, (",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the doctor stops naming his session as the cause",
        "file": "console_doctor.py",
        "find": "    if blocker == \"his-session\":\n        return MISSING, head + (\"HIS SESSION",
        "replace": "    if False:\n        return MISSING, head + (\"HIS SESSION",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
