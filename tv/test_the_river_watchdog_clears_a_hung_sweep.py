# -*- coding: utf-8 -*-
"""RIVER WATCHDOG — a sweep whose guard a HANG left set is cleared, on BOTH lanes, and the vault reel quarantined.

THE BUG (live 2026-10-17 on his console: vaultAutoread owed=14, lastTick {kind:busy, why:"a vault sweep is
already running"}): _vault_sweep_run / _chron_sweep_run release job["running"] only when the synchronous read
RETURNS or RAISES — their `finally` does NOT clear it (REG-1745, it only releases the sweep lock, a no-op while
running=True). A sweep that HANGS in its measure phase (a frame that never settles, a hung tooltip locate, a
read that never returns) leaves running=True forever, so every 45s/20s tick refuses "a sweep is already running"
and the river stalls on EVERY PC (Mac, GrokBot, ALT). Relaunch clears it but it RECURS.

v3758 shipped the VAULT watchdog. v3759 (this law) generalises it to ONE `_sweep_hang_check` logic shared by the
vault AND chronicle lanes, and hardens it against the v3758 cross-family (Grok) review:
  · a sweep that makes NO forward progress past _VAULT_SWEEP_HANG_DEADLINE_S is cleared (running False,
    phase 'hung'); the vault lane also quarantines its reel in _VAULT_SWEEP_QUARANTINE so the lane reads the rest.
  · a sweep that is making progress is LEFT RUNNING (any change to the progress snapshot resets the clock).
  · a sweep that is not running is a no-op.
  · FINDING 1 (TOCTOU): the snapshot is read outside the lock, so the clear re-check must prove it is the SAME
    sweep (startedTs == the snapshot's), not merely that *a* sweep is running — else a fresh, healthy sweep that
    took the slot in the gap is wrongly declared hung and its reel quarantined.
  · FINDING 3: a quarantined reel is refused at the vault_sweep_start DOOR (every caller), not only at the
    autoreel picker — a relaunch / manual / busy-retry / api caller would otherwise re-run it and re-hang.
Two RED_PROOFs below: a missing `running=False` (the stall this exists to end) and a missing startedTs identity
check (finding 1). [[heart-first]] [[the-unjoined-end]] [[unknown-stays-unknown]] [[copy-drift]]
"""
import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()
# REG-3200 - a hang is now a persisted attempt (the lane store), so this suite lives in a fixture world: TV_HIST points
# every store this process could reach at a temp dir, never his live lane memory.
import tempfile  # noqa: E402
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
os.environ.setdefault("TV_HIST", tempfile.mkdtemp(prefix="watchdog-iso-"))
import control_app as ca  # noqa: E402

REEL = "/reels/reel_s_17913672099321"
RID = "reel_s_17913672099321"


def _set_sweep(running, stalled_s):
    now = time.time()
    ca._VAULT_SWEEP_QUARANTINE.clear()
    ca._VAULT_JOB.clear()
    ca._VAULT_JOB.update({"running": running, "startedTs": int((now - stalled_s) * 1000),
                          "phase": "reading", "runReelsDone": 0, "classified": 0, "pagesRead": 0,
                          "runReel": "Bad Reel", "runReelDir": REEL, "groupTiles": 0})
    # REG-2271 — the production sig carries groupTiles (per-tile/per-frame grouping progress); the
    # seeded snapshot MUST match it exactly or the watchdog reads a "first sighting" and resets instead
    # of timing the stall. phase "reading" so the 240s (not the short grouping) bound applies here.
    sig = (ca._VAULT_JOB["startedTs"], "reading", 0, 0, 0, "Bad Reel", 0)
    ca._VAULT_SWEEP_PROGRESS.clear()
    ca._VAULT_SWEEP_PROGRESS.update({"sig": sig, "ts": now - stalled_s})


def _set_chron(running, stalled_s):
    now = time.time()
    ca._CHRON_JOB.clear()
    ca._CHRON_JOB.update({"running": running, "startedTs": int((now - stalled_s) * 1000),
                          "phase": "reading", "reelsDone": 0, "classified": 0, "pagesRead": 0,
                          "groupFrames": 0})
    # REG-2271 — the production sig carries groupFrames; the seeded snapshot must match it exactly.
    sig = (ca._CHRON_JOB["startedTs"], "reading", 0, 0, 0, 0)
    ca._CHRON_SWEEP_PROGRESS.clear()
    ca._CHRON_SWEEP_PROGRESS.update({"sig": sig, "ts": now - stalled_s})


class TestRiverWatchdogClearsAHungSweep(unittest.TestCase):
    # ── VAULT lane ──────────────────────────────────────────────────────────────────────────────
    def test_a_hung_sweep_past_the_deadline_is_cleared_and_its_reel_quarantined(self):
        _set_sweep(running=True, stalled_s=ca._VAULT_SWEEP_HANG_DEADLINE_S + 30)
        acted = ca._vault_sweep_hang_check()
        self.assertTrue(acted, "the watchdog did not act on a sweep stalled past the deadline")
        self.assertFalse(ca._VAULT_JOB.get("running"), "a hung sweep's guard was NOT cleared — the river stays stalled")
        self.assertEqual(ca._VAULT_JOB.get("phase"), "hung")
        self.assertIn(RID, ca._VAULT_SWEEP_QUARANTINE, "the hung reel was not quarantined, so the next sweep re-hangs on it")

    def test_a_sweep_making_progress_is_left_running(self):
        _set_sweep(running=True, stalled_s=1)                    # fresh — not past the deadline
        self.assertFalse(ca._vault_sweep_hang_check(), "the watchdog cleared a sweep that is making progress")
        self.assertTrue(ca._VAULT_JOB.get("running"), "a live, progressing sweep was wrongly cleared")

    def test_a_new_progress_snapshot_resets_the_clock(self):
        _set_sweep(running=True, stalled_s=ca._VAULT_SWEEP_HANG_DEADLINE_S + 30)
        ca._VAULT_JOB["classified"] = 5                          # forward progress since the snapshot
        self.assertFalse(ca._vault_sweep_hang_check(), "a sweep that just advanced must not be cleared")
        self.assertTrue(ca._VAULT_JOB.get("running"))

    def test_not_running_is_a_no_op(self):
        _set_sweep(running=False, stalled_s=ca._VAULT_SWEEP_HANG_DEADLINE_S + 30)
        self.assertFalse(ca._vault_sweep_hang_check())

    # ── FINDING 1 (TOCTOU) — a NEW sweep that took the slot in the gap must NOT be cleared ───────
    def test_a_sweep_that_started_since_the_snapshot_is_not_declared_hung(self):
        """The snapshot sees startedTs=T_A; before the clear re-check, a new sweep takes the slot
        (startedTs=T_B). A flip-lock reproduces that window in one thread. The watchdog must clear
        ONLY the sweep it timed — so it leaves T_B running. Without the startedTs identity check it
        would clear a fresh, healthy sweep and quarantine its reel."""
        now = time.time()
        T_A = int((now - (ca._VAULT_SWEEP_HANG_DEADLINE_S + 30) * 1000))
        T_B = T_A + 999999
        job = {"running": True, "startedTs": T_A, "phase": "reading"}
        prog = {"sig": (T_A, "reading"), "ts": now - (ca._VAULT_SWEEP_HANG_DEADLINE_S + 30)}

        class _FlipLock(object):                                 # a new sweep takes the slot between snapshot and clear
            def __init__(self): self.n = 0
            def __enter__(self):
                self.n += 1
                if self.n == 2:                                  # the clear's critical section
                    job["startedTs"] = T_B
                return self
            def __exit__(self, *a): return False

        acted = ca._sweep_hang_check(job, _FlipLock(), prog,
                                     lambda st: (st.get("startedTs"), st.get("phase")), "toctou")
        self.assertFalse(acted, "the watchdog cleared a sweep that replaced the one it timed (TOCTOU)")
        self.assertTrue(job.get("running"), "a fresh sweep that took the slot was wrongly declared hung")
        self.assertEqual(job.get("startedTs"), T_B, "the new sweep's identity was overwritten")

    # ── FINDING 3 — a quarantined reel is refused at the DOOR, not just the picker ───────────────
    def test_a_quarantined_reel_is_refused_at_the_vault_sweep_start_door(self):
        ca._VAULT_SWEEP_QUARANTINE.clear()
        ca._VAULT_SWEEP_QUARANTINE[RID] = {"at": int(time.time() * 1000), "why": "hung"}
        try:
            r = ca.vault_sweep_start(reel_dir=REEL, force=False) or {}
        finally:
            ca._VAULT_SWEEP_QUARANTINE.clear()
        self.assertTrue(r.get("quarantined"),
                        "a quarantined reel was NOT refused at the door — a direct caller would re-hang on it")
        self.assertFalse(r.get("ok"))
        self.assertEqual(r.get("reel"), RID)

    # ── CHRONICLE lane — the SAME hang, the SAME shared logic ────────────────────────────────────
    def test_a_hung_chronicle_sweep_past_the_deadline_is_cleared(self):
        _set_chron(running=True, stalled_s=ca._VAULT_SWEEP_HANG_DEADLINE_S + 30)
        acted = ca._chron_sweep_hang_check()
        self.assertTrue(acted, "the chronicle watchdog did not act on a sweep stalled past the deadline")
        self.assertFalse(ca._CHRON_JOB.get("running"), "a hung chronicle sweep's guard was NOT cleared — its river stays stalled")
        self.assertEqual(ca._CHRON_JOB.get("phase"), "hung")

    def test_a_progressing_chronicle_sweep_is_left_running(self):
        _set_chron(running=True, stalled_s=ca._VAULT_SWEEP_HANG_DEADLINE_S + 30)
        ca._CHRON_JOB["pagesRead"] = 3                           # forward progress since the snapshot
        self.assertFalse(ca._chron_sweep_hang_check(), "a chronicle sweep that just advanced must not be cleared")
        self.assertTrue(ca._CHRON_JOB.get("running"))

    def test_a_not_running_chronicle_sweep_is_a_no_op(self):
        _set_chron(running=False, stalled_s=ca._VAULT_SWEEP_HANG_DEADLINE_S + 30)
        self.assertFalse(ca._chron_sweep_hang_check())


RED_PROOF = [
    {
        "why": "river watchdog - if the guard clear does not set running False, a hung sweep stays 'running' "
               "forever and every tick refuses busy (the river stall this watchdog exists to end), on BOTH lanes",
        "file": "control_app.py",
        "find": '                job.update({"running": False, "phase": "hung",',
        "replace": '                job.update({"running": True, "phase": "hung",',
        "matches": 1,
    },
    {
        "why": "finding 1 (TOCTOU) - without the startedTs identity check the clear fires on ANY running sweep, "
               "so a fresh sweep that took the slot after the snapshot is wrongly declared hung and quarantined",
        "file": "control_app.py",
        "find": "            if job.get(\"running\") and job.get(\"startedTs\") == started:",
        "replace": "            if job.get(\"running\"):",
        "matches": 1,
    },
    {
        "why": "finding 3 - if vault_sweep_start does not consult the quarantine, a direct caller (relaunch, "
               "manual, busy-retry, api) re-runs the hanging reel and re-hangs until the watchdog fires again",
        "file": "control_app.py",
        "find": "        if _qrid in _VAULT_SWEEP_QUARANTINE:",
        "replace": "        if _qrid in ():",
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main()
