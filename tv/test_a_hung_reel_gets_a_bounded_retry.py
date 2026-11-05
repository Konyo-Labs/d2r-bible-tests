# -*- coding: utf-8 -*-
"""REG-3200 - A REEL THAT HUNG THE MEASURER GETS A BOUNDED RETRY WITH BACKOFF, NEVER ONE RETRY PER RELAUNCH.

MEASURED on his Mac 2026-11-05 (/api/status + /api/river, GET only; his console log, read only): the console came up at
20:27:26 (triage upSince), the vault lane started its one unsealed owed reel, reel 21967, 77 s later (vaultAutoread.lastTs
20:28:43), the sweep hung 854 s (the triage stood aside 9 ticks: skips {"paid-sweep": 9}) and the river watchdog
quarantined the reel. That quarantine lived only in memory - "cleared on relaunch, a transient hang retries" - and his
console relaunches on every ship, so the next boot hands a hung reel its read straight back. His log shows the loop:
reel 20599 was quarantined 4 times on 2026-10-17, three of them right after a relaunch (the v3759, v3760 and v3761
boots). Reel 21967 has hung once. The lane said only "8 owed, none startable this tick: 1 quarantined after a hang"
(never which reel, never when it is tried again).
WHY 21967 WAS READ AT ALL (r4 review, from his lane store and git history): it was cooling after 6 barren reads under
reader vp3554, until 11-12. The 16:06 bump to vp-reg2915 - which tv_diablo declares answers the same as vp3554
(VAULT_PROMPT_ANSWERS_SAME_AS, so its seals stand) - ended that cooldown, because the cooldown compared reader versions
exactly. One rule now (control_app._vault_same_reader) for the seals, the cooldown and the hang book.

THE LAW:
  - a hang is an ATTEMPT on record, persisted: a relaunch (memory gone, store reloaded) still holds the reel;
  - inside its backoff the picker AND the start door refuse it; past the backoff it is tried again (once);
  - one sweep is one attempt however many writers report it (retry cap, then the no-progress watchdog);
  - after _VAULT_HANG_TRIES hangs it waits for a person: "needs a look: <shape>, <why>", never retried for ever;
  - ways out: a new vault reader ends the hold; vault_hang_release gives exactly one more bounded try;
  - a RETRY is time-bounded: past _VAULT_RETRY_HELD_CAP_S it is asked to stop at its next banked read (#130), a
    first attempt is not capped - nor a new reader's first attempt, nor an untargeted sweep (it names no reel) - and
    the bound is asked on the path that runs: the 10 s rescue tick -> _vault_sweep_hang_check;
  - the in-sweep per-reel deadline (REG-2271, the sweep returns and the watchdog never fires) records the hang too;
  - a full read takes the reel off the hang book (_vault_hang_clear_read, called when a run returns);
  - a reader that answers the same as the one that hung (or that set a cooldown) keeps the hold, the count and the
    cooldown; a reader that does not, ends them;
  - an unreadable hang count is judged the last try (asks for a person), never a fresh shortest wait;
  - the tick's sentence names the held reel and when it is tried again.
Fixtures only: TV_HIST and the lane store point at a temp dir; the sweep door is never reached with a real reel.
[[unknown-stays-unknown]] [[heart-first]] [[the-unjoined-end]]
"""
import copy
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()
import control_app as CA  # noqa: E402

RID = "reel_s_1500000000002_21967"
VER = "vpLAW"


class _World(unittest.TestCase):
    """A temp shelf, a temp lane store, a fixed vault reader."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hung-retry-")
        self._hist = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = self.tmp
        self._path = CA._VAULT_AUTOREAD_PATH
        self._seals = CA._VAULT_SWEPT_PATH
        self._snap = copy.deepcopy(CA._VAULT_AUTOREAD)
        self._store = dict(CA._VAULT_AUTOREAD_STORE)
        self._q = dict(CA._VAULT_SWEEP_QUARANTINE)
        self._job = dict(CA._VAULT_JOB)
        self._prog = dict(CA._VAULT_SWEEP_PROGRESS)
        CA._VAULT_AUTOREAD_PATH = os.path.join(self.tmp, ".vault_autoread.json")
        CA._VAULT_SWEPT_PATH = os.path.join(self.tmp, "vault_swept.json")
        CA._VAULT_AUTOREAD.clear()
        CA._VAULT_AUTOREAD.update({"tries": {}, "skipped": {}, "reads": 0, "lastTs": 0, "retired": {},
                                   "lastWhy": {}, "reextract": {}, "joinQueued": {}, "joinTried": {},
                                   "cooldown": {}, "hung": {}})
        CA._VAULT_AUTOREAD_STORE.clear()
        CA._VAULT_AUTOREAD_STORE.update({"tried": False, "readable": None})
        CA._VAULT_SWEEP_QUARANTINE.clear()
        self.reel = os.path.join(self.tmp, RID)
        os.makedirs(self.reel)
        for i in range(3):
            with open(os.path.join(self.reel, "f_%d.jpg" % i), "wb") as fh:
                fh.write(b"\xff\xd8" + b"\0" * 1000 + b"\xff\xd9")
        # nothing here may ever start a real read: the sweep thread's body, the reader list and the reader switch
        # are all stand-ins, so even a sabotaged door that lets a held reel through spends nothing
        self.started = []
        self.patches = [mock.patch.object(CA, "_vault_reader_ver", lambda: VER),
                        mock.patch.object(CA, "_vault_sweep_run", lambda *a, **k: self.started.append(a)),
                        mock.patch.object(CA, "_chron_lanes", lambda: []),
                        mock.patch.object(CA, "_sweep_skipped_because_reader_is_grok", lambda: None)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        CA._VAULT_AUTOREAD_PATH = self._path
        CA._VAULT_SWEPT_PATH = self._seals
        CA._VAULT_AUTOREAD.clear()
        CA._VAULT_AUTOREAD.update(self._snap)
        CA._VAULT_AUTOREAD_STORE.clear()
        CA._VAULT_AUTOREAD_STORE.update(self._store)
        CA._VAULT_SWEEP_QUARANTINE.clear()
        CA._VAULT_SWEEP_QUARANTINE.update(self._q)
        CA._VAULT_JOB.clear()
        CA._VAULT_JOB.update(self._job)
        CA._VAULT_SWEEP_PROGRESS.clear()
        CA._VAULT_SWEEP_PROGRESS.update(self._prog)
        if self._hist is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = self._hist
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- helpers -------------------------------------------------------------------------------------------------
    def _hang_by_watchdog(self, started_ms):
        """The river watchdog's real path: a sweep on this reel with no progress past the deadline."""
        now = time.time()
        stalled = CA._VAULT_SWEEP_HANG_DEADLINE_S + 30
        CA._VAULT_JOB.clear()
        CA._VAULT_JOB.update({"running": True, "startedTs": started_ms, "phase": "reading",
                              "runReelsDone": 0, "classified": 0, "pagesRead": 0, "runReel": "law",
                              "runReelDir": self.reel, "groupTiles": 0})
        sig = (started_ms, "reading", 0, 0, 0, "law", 0)
        CA._VAULT_SWEEP_PROGRESS.clear()
        CA._VAULT_SWEEP_PROGRESS.update({"sig": sig, "ts": now - stalled})
        with mock.patch.object(CA, "_sweep_lock_release", lambda: None):
            return CA._vault_sweep_hang_check()

    def _relaunch(self):
        """A new process: memory gone, the store read back from disk."""
        CA._VAULT_SWEEP_QUARANTINE.clear()
        CA._VAULT_AUTOREAD["hung"] = {}
        CA._VAULT_AUTOREAD_STORE.clear()
        CA._VAULT_AUTOREAD_STORE.update({"tried": False, "readable": None})
        self.assertIs(CA._vault_autoread_load(), True, "the lane store did not read back")

    def _door(self):
        return CA.vault_sweep_start(limit=1, reel_dir=self.reel) or {}


class TestAHungReelGetsABoundedRetry(_World):

    def test_a_hang_is_a_persisted_attempt_that_survives_a_relaunch(self):
        self.assertTrue(self._hang_by_watchdog(int(time.time() * 1000) - 900000))
        rec = CA._VAULT_AUTOREAD["hung"].get(RID)
        self.assertIsInstance(rec, dict, "the watchdog's hang was not recorded as an attempt")
        self.assertEqual((rec["n"], rec["of"], rec["look"]), (1, CA._VAULT_HANG_TRIES, False), rec)
        self.assertGreater(rec["until"], time.time() * 1000 + 25 * 60 * 1000, "the first wait is not ~30 min")
        self._relaunch()
        hold = CA._vault_hang_hold(RID)
        self.assertEqual((hold or {}).get("kind"), "backoff",
                         "a relaunch handed the hung reel its read straight back (the measured loop)")
        door = self._door()
        self.assertTrue(door.get("quarantined"), door)
        self.assertEqual(door.get("hangHold"), "backoff", door)
        self.assertIn("next try is in", door.get("why") or "", door)

    def test_past_its_backoff_it_is_tried_again(self):
        self._hang_by_watchdog(int(time.time() * 1000) - 900000)
        CA._VAULT_AUTOREAD["hung"][RID]["until"] = int(time.time() * 1000) - 1
        self.assertIsNone(CA._vault_hang_hold(RID), "a reel past its backoff is still held")
        self.assertNotIn(RID, CA._VAULT_SWEEP_QUARANTINE, "the in-process entry outlived its wait")

    def test_one_sweep_is_one_attempt(self):
        started = int(time.time() * 1000) - 900000
        CA._vault_hang_record(RID, "retry cap", run=started)
        CA._vault_hang_record(RID, "the watchdog, same sweep", run=started)
        self.assertEqual(CA._VAULT_AUTOREAD["hung"][RID]["n"], 1, "one sweep was counted twice")

    def test_after_the_bound_it_needs_a_look_and_is_never_retried(self):
        for i in range(CA._VAULT_HANG_TRIES):
            CA._vault_hang_record(RID, "frame 412 never settled", run=1000 + i, reel_dir=self.reel)
        hold = CA._vault_hang_hold(RID, now_ms=time.time() * 1000 + 30 * 24 * 3600 * 1000)
        self.assertEqual((hold or {}).get("kind"), "look", "a reel past its bound is retried (silently, for ever)")
        say = CA._vault_hang_words(hold)
        self.assertTrue(say.startswith("needs a look: "), say)
        self.assertIn("MB, 3 frame(s)", say, "the look does not carry the reel's shape")
        self.assertIn("frame 412 never settled", say, "the look does not carry why")
        self.assertIn("retryReel", say, "the look offers no way out")
        door = self._door()
        self.assertEqual(door.get("hangHold"), "look", door)

    def test_an_unreadable_count_asks_for_a_person(self):
        CA._VAULT_AUTOREAD["hung"][RID] = {"n": "?", "promptVer": VER, "until": 0}
        e = CA._vault_hang_record(RID, "again", run=7)
        self.assertTrue(e and e.get("look"), "an unreadable count restarted the backoff at its shortest wait: %r" % e)

    def test_a_new_vault_reader_ends_the_hold(self):
        for i in range(CA._VAULT_HANG_TRIES):
            CA._vault_hang_record(RID, "hung", run=i)
        with mock.patch.object(CA, "_vault_reader_ver", lambda: "vpNEWER"):
            self.assertIsNone(CA._vault_hang_hold(RID), "a new reader did not give the reel its read back")

    def test_release_is_one_more_bounded_try(self):
        for i in range(CA._VAULT_HANG_TRIES):
            CA._vault_hang_record(RID, "hung", run=i)
        r = CA.vault_hang_release(RID)
        self.assertTrue(r.get("ok"), r)
        self.assertIsNone(CA._vault_hang_hold(RID), "a released reel is still held")
        e = CA._vault_hang_record(RID, "hung once more", run=99)
        self.assertTrue(e.get("look"), "a release became an unbounded retry: %r" % e)
        self.assertFalse(CA.vault_hang_release("reel_s_never_hung_1").get("ok"))

    def test_the_way_out_is_reachable_from_the_console(self):
        """The look names POST /api/vault_sweep {"retryReel": ...}; that route must reach vault_hang_release and spend
        nothing (it returns before any sweep starts)."""
        import io
        import tokenize
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            bare = tokenize.untokenize(t for t in tokenize.generate_tokens(fh.readline) if t.type != tokenize.COMMENT)
        code = "\n".join(ln.rstrip() for ln in bare.splitlines() if ln.strip()) + "\n"   # comments and blank lines gone
        want = ('            if body.get("retryReel"):\n'
                '                self._json(200, vault_hang_release(body.get("retryReel")))\n'
                '                return\n')
        self.assertEqual(code.count(want), 1, "the console route no longer reaches the way out")
        i = code.index(want)
        self.assertGreater(code.index("vault_sweep_start(limit=_vlim", i), i, "the way out is not ahead of the sweep")

    def test_a_retry_is_time_bounded_and_a_first_attempt_is_not(self):
        now = time.time()
        started = int((now - CA._VAULT_RETRY_HELD_CAP_S - 5) * 1000)
        CA._VAULT_JOB.clear()
        CA._VAULT_JOB.update({"running": True, "startedTs": started, "runReelDir": self.reel, "stopAsk": None})
        self.assertFalse(CA._vault_retry_cap_check(now), "a FIRST attempt was capped (a long reel may read long)")
        self.assertIsNone(CA._VAULT_JOB.get("stopAsk"))
        CA._vault_hang_record(RID, "hung before", run=1)
        self.assertTrue(CA._vault_retry_cap_check(now), "a retry ran past its bound and nothing asked it to stop")
        self.assertTrue(CA._VAULT_JOB.get("stopAsk"), "the retry was not asked to stop at its next banked read")
        self.assertTrue(CA._VAULT_JOB.get("running"), "the cap cleared the guard instead of asking for a banked stop")
        self.assertEqual(CA._VAULT_AUTOREAD["hung"][RID]["n"], 2, "the capped retry was not counted")
        self.assertIsNotNone(CA._vault_hang_hold(RID), "the capped reel is not held for its backoff")

    def test_the_tick_names_the_held_reel_and_when(self):
        CA._vault_hang_record(RID, "hung", run=1)
        with mock.patch.object(CA, "_vault_owed_reels", lambda hist=None: [self.reel]), \
                mock.patch.object(CA, "_reel_is_growing", lambda d, quiet_s=90: False), \
                mock.patch.object(CA, "vault_sweep_state", lambda *a, **k: {"running": False}), \
                mock.patch.object(CA, "_vault_unretire_lane_refusals", lambda: []), \
                mock.patch.object(CA, "_examined_seals_backfill", lambda: 0), \
                mock.patch.object(CA, "vault_sweep_start",
                                  lambda **k: (_ for _ in ()).throw(AssertionError("started %r" % k))):
            out = CA.vault_autoreel_tick()
        self.assertEqual((out.get("passed") or {}).get("quarantined"), 1, out)
        self.assertIn(RID, out.get("why") or "", "the sentence does not name the held reel")
        self.assertIn("next try is in", out.get("why") or "", "the sentence does not say when it is tried")
        for i in range(2, CA._VAULT_HANG_TRIES + 1):
            CA._vault_hang_record(RID, "hung", run=i)
        with mock.patch.object(CA, "_vault_owed_reels", lambda hist=None: [self.reel]), \
                mock.patch.object(CA, "_reel_is_growing", lambda d, quiet_s=90: False), \
                mock.patch.object(CA, "vault_sweep_state", lambda *a, **k: {"running": False}), \
                mock.patch.object(CA, "_vault_unretire_lane_refusals", lambda: []), \
                mock.patch.object(CA, "_examined_seals_backfill", lambda: 0), \
                mock.patch.object(CA, "vault_sweep_start",
                                  lambda **k: (_ for _ in ()).throw(AssertionError("started %r" % k))):
            out = CA.vault_autoreel_tick()
        self.assertEqual((out.get("passed") or {}).get("look"), 1, out)
        self.assertIn("needs a look", out.get("why") or "", out)


    # -- r4 review: the joins on the path that runs ---------------------------------------------------------------
    def test_the_rescue_tick_bounds_a_retry(self):
        """(A) the 10 s rescue tick calls _vault_sweep_hang_check, and that is what asks a retry past its bound to stop
        - while the sweep is still making progress, so the no-progress watchdog alone would never fire."""
        CA._vault_hang_record(RID, "hung before", run=1)
        started = int((time.time() - CA._VAULT_RETRY_HELD_CAP_S - 5) * 1000)
        CA._VAULT_JOB.clear()
        CA._VAULT_JOB.update({"running": True, "startedTs": started, "phase": "reading", "runReelsDone": 0,
                              "classified": 7, "pagesRead": 7, "runReel": "law", "runReelDir": self.reel,
                              "groupTiles": 3, "stopAsk": None})
        CA._VAULT_SWEEP_PROGRESS.clear()                  # first sighting: the watchdog only starts its clock
        with mock.patch.object(CA, "_sweep_lock_release", lambda: None):
            cleared = CA._vault_sweep_hang_check()
        self.assertFalse(cleared, "a progressing retry was cleared as hung")
        self.assertTrue(CA._VAULT_JOB.get("stopAsk"), "the rescue tick's watchdog does not bound a retry")
        self.assertTrue(CA._VAULT_JOB.get("running"), "the bound cleared the guard instead of asking a banked stop")
        self.assertEqual(CA._VAULT_AUTOREAD["hung"][RID]["n"], 2, "the bounded retry was not counted")
        code = _code_without_comments("control_app.py")
        self.assertEqual(code.count("\n            _vault_sweep_hang_check()\n"), 1,
                         "the rescue tick no longer runs the vault watchdog (and with it the retry bound)")

    def test_the_in_sweep_deadline_records_the_hang(self):
        """(B) REG-2271's per-reel deadline: the sweep RETURNS, the watchdog never fires, and this is the only
        recorder on that path."""
        started = int(time.time() * 1000) - 60000
        CA._VAULT_JOB.clear()
        CA._VAULT_JOB.update({"running": True, "startedTs": started, "runReelDir": self.reel})
        CA._vault_quarantine_reel(RID, "frame 9 froze in grouping")
        rec = CA._VAULT_AUTOREAD["hung"].get(RID)
        self.assertIsInstance(rec, dict, "the per-reel deadline's hang is not an attempt on record")
        self.assertEqual((rec.get("n"), rec.get("run")), (1, started), rec)
        self._relaunch()
        self.assertEqual((CA._vault_hang_hold(RID) or {}).get("kind"), "backoff",
                         "a relaunch handed a reel that blew its deadline its read straight back")

    def test_a_new_readers_first_attempt_is_not_capped(self):
        CA._vault_hang_record(RID, "hung under the old reader", run=1)
        started = int((time.time() - CA._VAULT_RETRY_HELD_CAP_S - 100) * 1000)
        CA._VAULT_JOB.clear()
        CA._VAULT_JOB.update({"running": True, "startedTs": started, "runReelDir": self.reel, "stopAsk": None})
        with mock.patch.object(CA, "_vault_reader_ver", lambda: "vpNEWER"):
            self.assertIsNone(CA._vault_hang_hold(RID), "a new reader did not get the reel fresh")
            self.assertFalse(CA._vault_retry_cap_check(), "a new reader's FIRST attempt was capped as a retry")
        self.assertIsNone(CA._VAULT_JOB.get("stopAsk"))
        self.assertEqual(CA._VAULT_AUTOREAD["hung"][RID]["n"], 1, "a new reader's first attempt was counted")

    def test_an_untargeted_sweep_is_never_capped(self):
        """runReelDir is set only for a sweep aimed at ONE reel, so startedTs is that reel's start; a sweep that names
        no reel is never cut by the bound (r4 review's third point, reproduced the other way)."""
        CA._vault_hang_record(RID, "hung", run=1)
        CA._VAULT_JOB.clear()
        CA._VAULT_JOB.update({"running": True, "startedTs": int((time.time() - 4000) * 1000), "runReelDir": None,
                              "runReel": RID, "stopAsk": None})
        self.assertFalse(CA._vault_retry_cap_check())
        self.assertIsNone(CA._VAULT_JOB.get("stopAsk"))

    def test_a_reader_that_answers_the_same_keeps_the_hold_the_count_and_the_cooldown(self):
        import tv_diablo as TD
        CA._vault_autoread_load()              # the boot's one load (no store yet), so a later ask re-reads nothing
        CA._vault_hang_record(RID, "hung", run=1)
        CA._vault_cool(RID, "barren")
        CA._VAULT_AUTOREAD["cooldown"][RID]["until"] = time.time() * 1000 + 3600000
        with mock.patch.object(CA, "_vault_reader_ver", lambda: "vpBUMP"), \
                mock.patch.object(TD, "VAULT_PROMPT_VER", "vpBUMP"), \
                mock.patch.object(TD, "VAULT_PROMPT_ANSWERS_SAME_AS", (VER,)):
            self.assertEqual((CA._vault_hang_hold(RID) or {}).get("kind"), "backoff",
                             "a bump that answers the same handed the hung reel a fresh set of tries")
            self.assertIsNotNone(CA._vault_cooling(RID),
                                 "a bump that answers the same ended a cooldown (his Mac: 21967 read at 20:28, hung)")
            self.assertEqual(CA._vault_cool(RID, "barren again")["barren"], 2, "the bump reset the barren count")
            e = CA._vault_hang_record(RID, "hung again", run=2)
            self.assertEqual(e.get("n"), 2, "the bump restarted the hang count: %r" % e)
        # both records are now stamped vpBUMP; a reader that does NOT answer the same as vpBUMP ends them
        with mock.patch.object(CA, "_vault_reader_ver", lambda: "vpOTHER"), \
                mock.patch.object(TD, "VAULT_PROMPT_VER", "vpOTHER"), \
                mock.patch.object(TD, "VAULT_PROMPT_ANSWERS_SAME_AS", (VER,)):
            self.assertIsNone(CA._vault_hang_hold(RID), "a reader that asks a NEW question did not end the hold")
            self.assertIsNone(CA._vault_cooling(RID), "a reader that asks a NEW question did not end the cooldown")

    def test_a_full_read_takes_the_reel_off_the_hang_book(self):
        CA._vault_hang_record(RID, "hung", run=1)
        self.assertEqual(CA._vault_hang_clear_read(["s_1793000000000_11111"]), [])
        self.assertIn(RID, CA._VAULT_AUTOREAD["hung"], "a run that never examined the reel took it off the book")
        self.assertEqual(CA._vault_hang_clear_read([RID.replace("reel_", "", 1)]), [RID])
        self.assertNotIn(RID, CA._VAULT_AUTOREAD["hung"])
        self._relaunch()
        self.assertNotIn(RID, CA._VAULT_AUTOREAD.get("hung") or {}, "taking it off the book was not saved")
        CA._VAULT_JOB.clear()
        CA._VAULT_JOB.update({"running": True, "startedTs": int((time.time() - 4000) * 1000),
                              "runReelDir": self.reel, "stopAsk": None})
        self.assertFalse(CA._vault_retry_cap_check(), "a reel read in full is still capped as a retry")
        # the join: a run that RETURNED (after the #130 stop's own return, before it reports done) clears the book
        code = _code_without_comments("control_app.py")
        call = "        _vault_hang_clear_read(prop.get(\"sessionsExamined\"))\n"
        self.assertEqual(code.count(call), 1, "no returned sweep takes a read reel off the hang book")
        run = code.index("def _vault_sweep_run(")
        stop = code.index("        except _vr.VaultSweepStopped as _stop:\n", run)
        done = code.index('_VAULT_JOB.update({"running": False, "phase": "done"', run)
        self.assertTrue(stop < code.index(call, run) < done, "the hang book is cleared outside the returned path")


def _code_without_comments(name):
    """The module's source with comment tokens and blank lines dropped, each line right-stripped."""
    import io
    import tokenize
    with io.open(os.path.join(HERE, name), encoding="utf-8") as fh:
        bare = tokenize.untokenize(t for t in tokenize.generate_tokens(fh.readline) if t.type != tokenize.COMMENT)
    return "\n".join(ln.rstrip() for ln in bare.splitlines() if ln.strip()) + "\n"


RED_PROOF = [
    {"why": "REG-3200 - the watchdog's hang is not recorded, so a relaunch re-runs the hung reel (the measured loop)",
     "file": "tv/control_app.py",
     "find": "                    on_quarantine(rid, \"no progress for %ds (held %ds) in phase %r\"\n",
     "replace": "                    (lambda *a: None)(rid, \"no progress for %ds (held %ds) in phase %r\"\n",
     "matches": 1},
    {"why": "REG-3200 - the hang record is not persisted, so a relaunch forgets it",
     "file": "tv/control_app.py",
     "find": "        if isinstance(d.get(\"hung\"), dict):\n            _VAULT_AUTOREAD[\"hung\"] = dict(d[\"hung\"])\n",
     "replace": "        if False:\n            _VAULT_AUTOREAD[\"hung\"] = dict(d[\"hung\"])\n",
     "matches": 1},
    {"why": "REG-3200 - the door ignores the persisted hold, so any caller re-runs a reel inside its backoff",
     "file": "tv/control_app.py",
     "find": "        if _qhold is not None and _qhold.get(\"kind\") in (\"backoff\", \"look\"):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3200 - past its backoff the in-process entry keeps holding, so a reel is never tried again",
     "file": "tv/control_app.py",
     "find": "            if now < until:\n                return dict(e, kind=\"backoff\")\n            _VAULT_SWEEP_QUARANTINE.pop(rid, None)\n            return None\n",
     "replace": "            if now < until:\n                return dict(e, kind=\"backoff\")\n            return dict(e, kind=\"backoff\")\n",
     "matches": 1},
    {"why": "REG-3200 - one sweep reported twice is counted as two attempts",
     "file": "tv/control_app.py",
     "find": "        if run is not None and same_reader and old.get(\"run\") == run:\n            return old\n",
     "replace": "        if False:\n            return old\n",
     "matches": 1},
    {"why": "REG-3200 - the bound never arrives: a hung reel is retried for ever",
     "file": "tv/control_app.py",
     "find": "        look = n >= _VAULT_HANG_TRIES\n",
     "replace": "        look = False\n",
     "matches": 1},
    {"why": "REG-3200 - an unreadable count restarts the backoff at its shortest wait",
     "file": "tv/control_app.py",
     "find": "        except (TypeError, ValueError):\n            n = _VAULT_HANG_TRIES - 1\n",
     "replace": "        except (TypeError, ValueError):\n            n = 0\n",
     "matches": 1},
    {"why": "REG-3200 - a new vault reader does not end the hold",
     "file": "tv/control_app.py",
     "find": "            if ver and not _vault_same_reader(e.get(\"promptVer\"), ver):\n                _VAULT_SWEEP_QUARANTINE.pop(rid, None)\n",
     "replace": "            if False:\n                _VAULT_SWEEP_QUARANTINE.pop(rid, None)\n",
     "matches": 1},
    {"why": "REG-3200 - a release wipes the count, so the way out becomes an unbounded retry",
     "file": "tv/control_app.py",
     "find": "    h[rid] = dict(e or {}, n=_VAULT_HANG_TRIES - 1, of=_VAULT_HANG_TRIES,",
     "replace": "    h[rid] = dict(e or {}, n=0, of=_VAULT_HANG_TRIES,",
     "matches": 1},
    {"why": "REG-3200 - a retry is not time-bounded",
     "file": "tv/control_app.py",
     "find": "        if not started or held < _VAULT_RETRY_HELD_CAP_S:\n            return False\n",
     "replace": "        if True:\n            return False\n",
     "matches": 1},
    {"why": "REG-3200 - the cap is applied to a first attempt too (a long reel's first read would be cut)",
     "file": "tv/control_app.py",
     "find": "        rec = h.get(rid) if (rid and isinstance(h, dict)) else None\n",
     "replace": "        rec = (h.get(rid) if (rid and isinstance(h, dict)) else None) or {\"promptVer\": _vault_reader_ver()}\n",
     "matches": 1},
    {"why": "REG-3200 - the look loses the reel's shape",
     "file": "tv/control_app.py",
     "find": "             \"shape\": _vault_reel_shape(rid, reel_dir)}\n",
     "replace": "             \"shape\": None}\n",
     "matches": 1},
    {"why": "REG-3200 - the look's way out is unreachable: the console route no longer releases the reel",
     "file": "tv/control_app.py",
     "find": "                self._json(200, vault_hang_release(body.get(\"retryReel\")))\n",
     "replace": "                self._json(200, {\"ok\": False})\n",
     "matches": 1},
    {"why": "REG-3200 - the tick's sentence stops naming the held reel and when it is tried again",
     "file": "tv/control_app.py",
     "find": "            _hang_seen.append((rid, _hang))\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "REG-3200 (r4 review A) - the rescue tick's watchdog no longer asks the retry bound: a progressing retry runs on",
     "file": "tv/control_app.py",
     "find": "    _vault_retry_cap_check()        # REG-3200 \u2014 a RETRY of a reel that hung before is also bounded in wall clock\n",
     "replace": "    pass\n",
     "matches": 1},
    {"why": "REG-3200 (r4 review A) - the 10 s rescue tick stops running the vault watchdog, and with it the retry bound",
     "file": "tv/control_app.py",
     "find": "            _vault_sweep_hang_check()       # RIVER WATCHDOG \u2014 a vault sweep whose guard a HANG left set is cleared here\n",
     "replace": "            pass                            # RIVER WATCHDOG \u2014 a vault sweep whose guard a HANG left set is cleared here\n",
     "matches": 1},
    {"why": "REG-3200 (r4 review B) - the in-sweep per-reel deadline (REG-2271) quarantines without a record: a relaunch re-runs it",
     "file": "tv/control_app.py",
     "find": "        _vault_hang_record(rid, _VAULT_SWEEP_QUARANTINE[rid][\"why\"], run=_VAULT_JOB.get(\"startedTs\"))\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "REG-3200 (r4 review) - a new vault reader's FIRST attempt is capped and counted as a retry",
     "file": "tv/control_app.py",
     "find": "        if _ver and not _vault_same_reader(rec.get(\"promptVer\"), _ver):\n            return False            # a new reader's first attempt: the no-progress watchdog only\n",
     "replace": "        if False:\n            return False\n",
     "matches": 1},
    {"why": "REG-3200 (r4 review) - a reader that answers the same is called new: a bump ends the cooldown and resets the hang count",
     "file": "tv/control_app.py",
     "find": "    return bool(c) and (s == c or s in _vault_prompt_vers_same_as(c))\n",
     "replace": "    return bool(c) and s == c\n",
     "matches": 1},
    {"why": "REG-3200 (r4 review) - a reel read in full stays on the hang book (capped as a retry for ever)",
     "file": "tv/control_app.py",
     "find": "            for rid in (x, \"reel_\" + x):\n",
     "replace": "            for rid in ():\n",
     "matches": 1},
    {"why": "REG-3200 (r4 review) - no returned sweep takes a read reel off the hang book",
     "file": "tv/control_app.py",
     "find": "        _vault_hang_clear_read(prop.get(\"sessionsExamined\"))\n",
     "replace": "        pass\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
