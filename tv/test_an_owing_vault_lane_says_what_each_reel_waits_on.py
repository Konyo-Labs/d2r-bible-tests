# -*- coding: utf-8 -*-
"""REG-3200 - AN OWING VAULT LANE SAYS WHAT EACH OWED REEL WAITS ON, AND A LANE WAITING ON NAMED THINGS IS NOT "STOPPED".

MEASURED on his Mac 2026-11-05 (/api/status + /api/river + /api/fleet, GET only):
  vaultAutoread.lastTick.why   "8 owed, none startable this tick: 1 quarantined after a hang"
  vaultAutoread.skipped        6 owed reels "already sealed by the CURRENT vault reader (vp3554) with 0 rows"
  retention.say                "1 reel(s) (176 MB) are waiting on a sweep - 7 reel(s) (1441 MB) have already been read
                                and yielded nothing extractable"
  eagle "extraction lanes"     "vault: 99 session(s), last did work 194.5 h ago - past the 48 h mark, so this lane
                                has STOPPED"
So the tick passed 7 of its 8 owed reels in SILENCE (the sealed branch `continue`d without a reason), and
lane_health counted what the vault lane could act on for the chronicle only - so the vault lane could never read
BLOCKED, only STOPPED, while it was in fact waiting on a new vault reader (7) and a hang's hold (1). Not a lock
consequence: vault_sweep_start does not ask the self-arming lock (_vault_start_block says so), and the tick's sentence
was "none startable", not "LOCKED".

THE LAW:
  - the tick counts a reel sealed by the current reader with its one solo pass spent, and says what it waits on;
  - _vault_lane_reasons answers owed / startable-now / why-not from the tick's ONE picker rule (_vault_pass_reason),
    starting nothing - and agrees with the tick;
  - lane_health asks it for the vault lane: a lane past 48 h that can start NONE of what it owes is BLOCKED, with the
    lane's own reasons, never the chronicle's measured story;
  - the status board lists each owed reel held after a hang (its try count, its next try or "needs a look").
Fixtures only: TV_HIST, the lane store and the seal store are temp files; no sweep can start.
[[unknown-stays-unknown]] [[copy-drift]] [[heart-first]]
"""
import copy
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
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()
import control_app as CA  # noqa: E402
import lane_health as LH  # noqa: E402

SEALED = "reel_s_1790943996868_84048"
HUNG = "reel_s_1792343240980_21967"
FREE = "reel_s_1793000000000_11111"
HOUR = 3600000.0


def _reader():
    import tv_diablo as _tvd
    return str(getattr(_tvd, "VAULT_PROMPT_VER", "") or "vpLAW")


class _World(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="owing-vault-")
        self._hist = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = self.tmp
        self._path = CA._VAULT_AUTOREAD_PATH
        self._seals = CA._VAULT_SWEPT_PATH
        self._snap = copy.deepcopy(CA._VAULT_AUTOREAD)
        self._store = dict(CA._VAULT_AUTOREAD_STORE)
        self._q = dict(CA._VAULT_SWEEP_QUARANTINE)
        CA._VAULT_AUTOREAD_PATH = os.path.join(self.tmp, ".vault_autoread.json")
        CA._VAULT_SWEPT_PATH = os.path.join(self.tmp, "vault_swept.json")
        self.ver = _reader()
        CA._VAULT_AUTOREAD.clear()
        CA._VAULT_AUTOREAD.update({"tries": {}, "skipped": {}, "reads": 0, "lastTs": 0, "retired": {},
                                   "lastWhy": {}, "joinQueued": {}, "joinTried": {}, "cooldown": {},
                                   # the sealed reel's one solo pass is already spent under this reader
                                   "reextract": {SEALED: self.ver}, "hung": {}})
        CA._VAULT_AUTOREAD_STORE.clear()
        CA._VAULT_AUTOREAD_STORE.update({"tried": False, "readable": None})
        CA._VAULT_SWEEP_QUARANTINE.clear()
        with io.open(CA._VAULT_SWEPT_PATH, "w", encoding="utf-8") as fh:
            json.dump({SEALED.replace("reel_", "", 1): {"ts": 1, "rows": 0, "promptVer": self.ver}}, fh)
        self.dirs = {}
        for rid in (SEALED, HUNG, FREE):
            d = os.path.join(self.tmp, rid)
            os.makedirs(d)
            self.dirs[rid] = d
        self.started = []
        self.patches = [mock.patch.object(CA, "_vault_reader_ver", lambda: self.ver),
                        mock.patch.object(CA, "_vault_sweep_run", lambda *a, **k: self.started.append(a)),
                        mock.patch.object(CA, "_chron_lanes", lambda: []),
                        mock.patch.object(CA, "_sweep_skipped_because_reader_is_grok", lambda: None),
                        mock.patch.object(CA, "_reel_is_growing", lambda d, quiet_s=90: False),
                        mock.patch.object(CA, "vault_sweep_state", lambda *a, **k: {"running": False}),
                        mock.patch.object(CA, "_vault_unretire_lane_refusals", lambda: []),
                        mock.patch.object(CA, "_examined_seals_backfill", lambda: 0)]
        for p in self.patches:
            p.start()
        CA._vault_hang_record(HUNG, "frame 412 never settled", run=1, reel_dir=self.dirs[HUNG])

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
        if self._hist is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = self._hist
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _owed(self, *rids):
        return [self.dirs[r] for r in rids]


class TestTheTickNamesEveryReelItPasses(_World):

    def test_a_sealed_reel_is_counted_and_named_not_passed_in_silence(self):
        owed = self._owed(SEALED, HUNG)
        with mock.patch.object(CA, "_vault_owed_reels", lambda hist=None: owed):
            out = CA.vault_autoreel_tick()
        self.assertEqual(self.started, [], "a tick started a sweep over a sealed or held reel")
        passed = out.get("passed") or {}
        self.assertEqual((passed.get("sealed"), passed.get("quarantined")), (1, 1), out)
        self.assertEqual(sum(passed.values()), out.get("owed"), "an owed reel left the tick without a reason: %r" % out)
        self.assertIn("1 already read by the current vault reader with nothing taken - they wait on a new vault "
                      "reader", out.get("why") or "", out)

    def test_the_lane_reasons_are_the_ticks_own_rule(self):
        owed = self._owed(SEALED, HUNG, FREE)
        r = CA._vault_lane_reasons(owed=owed)
        self.assertEqual((r.get("owed"), r.get("actionable")), (3, 1), r)
        self.assertEqual(r.get("by"), {"sealed": 1, "quarantined": 1}, r)
        self.assertIn("1 of 3 owed can be started now", r.get("why") or "", r)
        self.assertIn(HUNG, r.get("why") or "", "the held reel is not named in the lane's reasons")
        self.assertEqual(self.started, [], "asking the reasons started a sweep")
        two = self._owed(SEALED, HUNG)
        with mock.patch.object(CA, "_vault_owed_reels", lambda hist=None: two):
            out = CA.vault_autoreel_tick()
        self.assertEqual({k: v for k, v in (out.get("passed") or {}).items() if v},
                         CA._vault_lane_reasons(owed=two).get("by"),
                         "the tick and the lane's health read two different picker rules")

    def test_unknown_owed_is_unknown_never_zero(self):
        with mock.patch.object(CA, "_vault_owed_reels", lambda hist=None: None):
            r = CA._vault_lane_reasons()
        self.assertIsNone(r.get("actionable"), r)
        self.assertIsNone(r.get("owed"), r)

    def test_the_status_board_lists_the_held_reel(self):
        owed = self._owed(SEALED, HUNG)
        with mock.patch.object(CA, "_vault_owed_reels", lambda hist=None: owed):
            st = CA._vault_autoread_state()
        hung = st.get("hung") or []
        self.assertEqual([h.get("reel") for h in hung], [HUNG], st)
        self.assertEqual(hung[0].get("kind"), "backoff", hung)
        self.assertIn("next try is in", hung[0].get("say") or "", hung)


class TestAWaitingVaultLaneIsBlockedNotStopped(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="lane-blocked-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self._here = LH.HERE
        LH.HERE = self.root
        self.addCleanup(setattr, LH, "HERE", self._here)
        self.now = 1000000 * HOUR
        for name, age in (("vault_swept.json", 194.5), ("chronicle_swept.json", 2)):
            with io.open(os.path.join(self.root, name), "w", encoding="utf-8") as fh:
                json.dump({"s_%d" % i: {"ts": self.now - age * HOUR, "rows": 1} for i in range(3)}, fh)

    WHY = ("0 of 8 owed can be started now: the rest 7 already read by the current vault reader with nothing taken - "
           "they wait on a new vault reader, 1 quarantined after a hang")

    def test_the_lane_says_its_own_reasons(self):
        r = LH.lane("vault", self.now, owed=8, actionable=0, blocked_why=self.WHY)
        self.assertEqual(r["state"], "blocked", r)
        self.assertIn(self.WHY, r["why"])
        self.assertNotIn("Chronicle focus", r["why"], "the vault lane borrowed the chronicle's measured story")

    def test_the_live_report_carries_the_vault_lanes_count_and_reasons(self):
        with mock.patch.object(LH, "owed_counts", lambda: {"vault": 8, "chronicle": 0}), \
                mock.patch.object(LH, "lane_reasons",
                                  lambda: {"vault": {"actionable": 0, "why": self.WHY},
                                           "chronicle": {"actionable": 0, "why": None}}), \
                mock.patch.object(LH, "owed_sessions", lambda *a, **k: None), \
                mock.patch.object(LH, "held_by_design", lambda *a, **k: None):
            rep = LH.report(self.now)
        v = rep["lanes"]["vault"]
        self.assertEqual(v["state"], "blocked", "a vault lane waiting on named things read %r" % v["state"])
        self.assertIn("wait on a new vault reader", v["why"])

    def test_lane_reasons_asks_the_vault_lane(self):
        with mock.patch.object(CA, "_vault_lane_reasons", lambda: {"owed": 8, "actionable": 0, "why": self.WHY}), \
                mock.patch.object(CA, "_unswept_chron_reels", lambda limit=50: []):
            got = LH.lane_reasons()
        self.assertEqual(got["vault"], {"actionable": 0, "why": self.WHY}, got)
        self.assertEqual(LH.actionable_counts().get("chronicle") is None, False)


RED_PROOF = [
    {"why": "REG-3200 - a sealed reel whose one pass is spent leaves the tick in silence again",
     "file": "tv/control_app.py",
     "find": "                _passed[\"sealed\"] += 1\n                continue\n",
     "replace": "                continue\n",
     "matches": 1},
    {"why": "REG-3200 - the sealed reason loses what it waits on",
     "file": "tv/control_app.py",
     "find": "                     \"sealed\": \"already read by the current vault reader with nothing taken - they wait on a new \"\n",
     "replace": "                     \"sealed\": \"passed over - \"\n",
     "matches": 1},
    {"why": "REG-3200 - the lane's reasons read a sealed-and-spent reel as startable (two picker rules)",
     "file": "tv/control_app.py",
     "find": "    return not _unextracted_seal_needs_one_pass(refusal, (_VAULT_AUTOREAD.get(\"reextract\") or {}).get(rid))\n",
     "replace": "    return False\n",
     "matches": 1},
    {"why": "REG-3200 - the lane's reasons ignore a hang's hold",
     "file": "tv/control_app.py",
     "find": "    _hold = _vault_hang_hold(rid)\n    if _hold is not None:\n        return \"look\" if _hold.get(\"kind\") == \"look\" else \"quarantined\"\n",
     "replace": "    _hold = None\n",
     "matches": 1},
    {"why": "REG-3200 - a blocked vault lane tells the chronicle's story instead of its own",
     "file": "tv/lane_health.py",
     "find": "    if blocked and blocked_why:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3200 - lane_health counts nothing for the vault lane, so it can only ever read STOPPED",
     "file": "tv/lane_health.py",
     "find": "            out[\"vault\"] = {\"actionable\": a, \"why\": r.get(\"why\")}\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "REG-3200 - the live report drops the vault lane's reasons on the way to lane()",
     "file": "tv/lane_health.py",
     "find": "                     blocked_why=(_rsn.get(n) or {}).get(\"why\")) for n in LANES}\n",
     "replace": "                     blocked_why=None) for n in LANES}\n",
     "matches": 1},
    {"why": "REG-3200 - the status board stops listing the reels held after a hang",
     "file": "tv/control_app.py",
     "find": "                \"hung\": _vault_hang_board(owed),\n",
     "replace": "                \"hung\": [],\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
