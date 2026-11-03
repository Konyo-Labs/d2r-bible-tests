# -*- coding: utf-8 -*-
"""#150 (REG-2942 / REG-2943) - A PUSH KILLED MID-GATE KEEPS WHAT A GREEN CLEAN RUN ALREADY BRACKETED.

A push gate held every PROVEN in _CLEAN.pending until its CLOSING clean run (REG-1988), and _on_fatal_signal removed
the sandboxes and os._exit()ed without banking. So a kill mid-gate - the hook's deadline, a Ctrl-C, a closed terminal -
lost every proof that gate had already proved, and the next push paid for all of them again (test_control: 27 proofs at
~4 min each). His order: prove once, never drop.

Banking each PROVEN the moment it returns is NOT the fix: the proofs share ONE clean run, and a proof can go red because
earlier runs drifted the sandbox rather than because of its tamper - the reason the closing run exists. So the bracket
moves earlier instead: once CHECKPOINT_EVERY PROVENs wait and another proof is about to run, the shared clean run is
asked again; green banks and FLUSHES every waiting PROVEN (each sits between two green clean runs), red banks nothing.
And the fatal-signal handler writes what was already banked before it exits - never a PROVEN still waiting.
The review added two rules, both pinned here: a LATER red clean run of the same gate (a checkpoint or the closing run)
takes back every proof an earlier checkpoint of it banked, so no resume ever reuses one; and the push RECORD carries the
checkpoints' cost (clean runs and seconds) beside what they saved (hits a killed run's checkpoint had banked), so a
CHECKPOINT_EVERY that costs more than it saves shows up as a number.

Driven through the REAL _prove_gate / _prove_gate_push / _VerdictCache against a real directory, exactly as the REG-1988
law drives them; only the law RUN is a stand-in, answering from the subject file's actual bytes. A kill is a
KeyboardInterrupt from inside a run - it escapes every `except Exception` on the way out, as a signal's exit does.
[[regression-guard]] [[stale-reading]]
RED_PROOF below.
"""
import io
import os
import shutil
import signal
import subprocess
import sys
import tempfile
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
import heart2 as H  # noqa: E402

GATE = "no-such-registered-gate"
KEYS = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J")   # two checkpoints and a tail


def _quiet(*a, **k):
    pass


class _Runs(object):
    """A stand-in for heart2._run_gate that reads the subject's real bytes. `red_clean_at` turns the Nth clean run red;
    `kill_at` raises KeyboardInterrupt on the Nth tampered run (a kill landing mid-gate)."""

    def __init__(self, tv, red_clean_at=None, kill_at=None):
        self.tv, self.red_clean_at, self.kill_at = tv, red_clean_at, kill_at
        self.clean = self.tampered = 0

    def __call__(self, sandbox_tv, filename, timeout=180, extra=(), script=None, widths=None):
        with io.open(os.path.join(self.tv, "subject.py"), encoding="utf-8") as fh:
            src = fh.read()
        if "BAD" in src:
            self.tampered += 1
            if self.kill_at is not None and self.tampered == self.kill_at:
                raise KeyboardInterrupt("the push was killed mid-gate")
            return False, "Ran 1 test | FAILED"
        self.clean += 1
        if self.red_clean_at is not None and self.clean == self.red_clean_at:
            return False, "Ran 1 test | FAILED (drifted state)"
        return True, "Ran 1 test | OK"


class AKilledPushKeepsWhatItProved(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="h2kill.")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.tv = os.path.join(self.root, "repo", "tv")
        os.makedirs(self.tv)
        self.good = "".join('%s = "GOOD"\n' % k for k in KEYS)
        self._write(self.good)
        with io.open(os.path.join(self.tv, "fake_gate.py"), "w", encoding="utf-8") as fh:
            fh.write("import sys\nsys.exit(0)\n")
        self.proofs = [{"file": "subject.py", "find": '%s = "GOOD"' % k, "replace": '%s = "BAD"' % k,
                        "matches": 1, "why": k} for k in KEYS]
        self.path = os.path.join(self.root, ".heart2_cache.json")
        p = mock.patch.dict(os.environ, {"HEART2_RED_MEMORY": "0"})   # the sabotage memory is neither read nor written
        p.start()
        self.addCleanup(p.stop)
        self._real = H._run_gate
        self.addCleanup(lambda: setattr(H, "_run_gate", self._real))
        self.addCleanup(lambda: setattr(H, "_PUSH", None))
        self.assertIsNone(H._PUSH, "PREMISE: no push-time run is in progress")
        self.assertGreater(len(KEYS), 2 * H.CHECKPOINT_EVERY, "PREMISE: the gate holds two checkpoints and a tail")

    def _write(self, text):
        with io.open(os.path.join(self.tv, "subject.py"), "w", encoding="utf-8") as fh:
            fh.write(text)

    def _gate(self, runs):
        """One push-time gate over a cache opened FROM DISK, as each push opens it. -> (verdict, per, cache)"""
        cache = H._VerdictCache(path=self.path, say=_quiet)
        H._run_gate = runs
        H._PUSH = self.run = H._PushRun(order={}, browser=(), cache=cache)
        try:
            verdict, per = H._prove_gate(self.tv, GATE, "fake_gate.py", self.proofs, _quiet)
        finally:
            H._PUSH = None
        return verdict, per, cache

    def _record(self, cache):
        return H._push_record(self.run, [(GATE, "fake_gate.py", self.proofs)], cache, len(self.proofs), {})

    def _killed(self, runs):
        with self.assertRaises(KeyboardInterrupt, msg="PREMISE: the stand-in kill did not land"):
            self._gate(runs)
        self._write(self.good)                  # a real kill leaves this sandbox behind; the next push makes a fresh one

    def _on_disk(self):
        ent, why = H._load_cache(self.path)
        self.assertIsNone(why, "the cache on disk could not be read: %s" % why)
        return ent or {}

    def test_a_kill_after_a_green_checkpoint_leaves_those_proofs_on_disk(self):
        n = H.CHECKPOINT_EVERY
        self._killed(_Runs(self.tv, kill_at=n + 1))
        self.assertEqual(len(self._on_disk()), n,
                         "the push was killed after %d proofs had come back PROVEN and a green clean run bracketed "
                         "them, and the disk holds %d - the next push proves them all again" % (n, len(self._on_disk())))

    def test_the_resumed_push_reuses_what_was_banked_and_proves_only_the_rest(self):
        n = H.CHECKPOINT_EVERY
        self._killed(_Runs(self.tv, kill_at=n + 1))
        runs = _Runs(self.tv)
        verdict, per, cache = self._gate(runs)
        self.assertEqual((verdict, per), (H.PROVEN, [H.PROVEN] * len(KEYS)))
        self.assertEqual(cache.hits, n, "the resumed push re-proved %d proof(s) the killed one had already banked"
                         % (n - cache.hits))
        self.assertEqual(runs.tampered, len(KEYS) - n, "the resumed push ran %d tampered runs; only %d were owed"
                         % (runs.tampered, len(KEYS) - n))
        self.assertEqual(len(self._on_disk()), len(KEYS))

    def test_a_red_checkpoint_banks_nothing(self):
        # clean run 1 is the gate's shared one; run 2 is the checkpoint - red, as a drifted sandbox reads
        self._killed(_Runs(self.tv, red_clean_at=2, kill_at=H.CHECKPOINT_EVERY + 1))
        self.assertEqual(self._on_disk(), {}, "a PROVEN whose checkpoint clean run went RED was banked anyway")

    def test_a_resume_never_reuses_a_proof_a_later_red_checkpoint_took_back(self):
        """The #150 review's addition: checkpoint 1 is green and banks four; checkpoint 2 goes RED - the gate drifted - so those four
        are taken back too, and the push is killed before it closes. Nothing it proved may be served on resume."""
        k = H.CHECKPOINT_EVERY
        self._killed(_Runs(self.tv, red_clean_at=3, kill_at=2 * k + 2))
        self.assertEqual(self._on_disk(), {}, "proofs a LATER red checkpoint of the same gate took back are on disk")
        verdict, per, cache = self._gate(_Runs(self.tv))
        self.assertEqual(cache.hits, 0, "the resumed push reused %d proof(s) banked before a red checkpoint of their "
                                        "gate" % cache.hits)
        self.assertEqual(verdict, H.PROVEN)

    def test_a_red_closing_run_takes_back_what_the_checkpoints_banked(self):
        k = H.CHECKPOINT_EVERY
        runs = _Runs(self.tv, red_clean_at=4)             # 1 shared, 2 and 3 the green checkpoints, 4 the closing run
        verdict, per, _cache = self._gate(runs)
        self.assertEqual(runs.clean, 4, "PREMISE: two checkpoints and the closing run were not the runs asked")
        self.assertEqual(verdict, H.UNPROVABLE)
        self.assertEqual(self._on_disk(), {}, "%d proof(s) two green checkpoints banked survived a RED closing run of "
                                              "their gate" % len(self._on_disk()))
        self.assertEqual(self._record(_cache)["checkpoint"]["revoked"], 2 * k)

    def test_an_unkilled_gate_pays_two_checkpoints_and_banks_every_proof(self):
        runs = _Runs(self.tv)
        verdict, per, cache = self._gate(runs)
        self.assertEqual((verdict, per), (H.PROVEN, [H.PROVEN] * len(KEYS)))
        self.assertEqual(len(self._on_disk()), len(KEYS))
        self.assertEqual(runs.clean, 4, "ten proofs should pay the shared clean run, two checkpoints and the closing "
                                        "run - %d clean runs were paid" % runs.clean)
        self.assertFalse([k for k, e in self._on_disk().items() if e.get("ckpt")],
                         "a gate that closed green left its checkpoint marks - a later push would count them as saved")

    def test_the_push_record_says_what_the_checkpoints_cost_and_saved(self):
        """The #150 review's addition: the RECORD carries the cost and the saving, so a K that costs more than it saves is a number."""
        k = H.CHECKPOINT_EVERY
        _v, _p, cache = self._gate(_Runs(self.tv))
        rec = self._record(cache)
        self.assertIn("checkpoint", rec, "the push record says nothing of what the checkpoints cost or saved")
        c = rec["checkpoint"]
        self.assertEqual((c["every"], c["forecast"], c["runs"], c["banked"], c["red"], c["savedHits"]),
                         (k, (len(KEYS) - 1) // k, 2, 2 * k, 0, 0), "the record's checkpoint account: %r" % c)
        self.assertIn("costS", c)
        self.assertIn("bankedS", c)
        os.remove(self.path)
        self._killed(_Runs(self.tv, kill_at=k + 1))
        _v, _p, cache = self._gate(_Runs(self.tv))
        c = self._record(cache)["checkpoint"]
        self.assertEqual(c["savedHits"], k, "the resumed push did not record the %d proof(s) a killed run's checkpoint "
                                            "banked as SAVED: %r" % (k, c))


@unittest.skipUnless(H._host_has_posix_signals(), "a signal sent to itself is a POSIX act - declared, never a pass")
class TheFatalSignalWritesWhatWasBanked(unittest.TestCase):
    """REG-2943 - a SIGTERM mid-push writes what store() already banked before the handler exits."""

    def test_a_sigterm_writes_the_banked_entry_and_never_a_waiting_one(self):
        d = tempfile.mkdtemp(prefix="h2sig.")
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, ".heart2_cache.json")
        child = (
            "import os, signal, sys, time\n"
            "sys.path.insert(0, %r)\n"
            "import heart2 as H\n"
            "c = H._VerdictCache(path=%r, say=lambda *a, **k: None)\n"
            "H._PUSH = H._PushRun(order={}, browser=(), cache=c)\n"
            "c.store('banked', {'verdict': H.PROVEN, 'provedAt': 1})\n"
            "H._CLEAN.pending = [(0, 'waiting', {'verdict': H.PROVEN, 'provedAt': 1})]\n"
            "H.install_sandbox_cleanup()\n"
            "os.kill(os.getpid(), signal.SIGTERM)\n"
            "time.sleep(30)\n" % (HERE, path))
        env = dict(os.environ, HEART2_RED_MEMORY="0")
        r = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True, timeout=120, env=env)
        self.assertEqual(r.returncode, 128 + int(signal.SIGTERM),
                         "PREMISE: the child did not exit the way the signal meant (%r): %s" % (r.returncode,
                                                                                              r.stderr[-400:]))
        ent, why = H._load_cache(path)
        self.assertIsNone(why, "the cache the handler wrote cannot be read: %s" % why)
        self.assertIn("banked", ent or {}, "a SIGTERM exited without writing what the push had already banked")
        self.assertNotIn("waiting", ent or {}, "the handler banked a PROVEN that no green clean run bracketed")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "#150 - no checkpoint: every PROVEN waits for the closing run, and a kill mid-gate loses them all",
     "file": "heart2.py",
     "find": "                _ckpt[\"on\"] = _checkpoint_bank(name, got, say, run)",
     "replace": "                _ckpt[\"on\"] = False",
     "matches": 1},
    {"why": "#150 - a checkpoint banks without asking the clean run again, so a drift-red PROVEN is stored",
     "file": "heart2.py",
     "find": "    for r in [r for r in (getattr(_CLEAN, \"runs\", None) or {}).values() if r.get(\"reused\")]:\n        _t0 = time.time()\n",
     "replace": "    for r in []:\n        _t0 = time.time()\n",
     "matches": 1},
    {"why": "#150 - the checkpoint banks in memory only, so the kill still loses it (nothing written until the gate ends)",
     "file": "heart2.py",
     "find": "    _CLEAN.pending = keep\n    run.cache.flush()\n",
     "replace": "    _CLEAN.pending = keep\n",
     "matches": 1},
    {"why": "#150 - a checkpoint leaves what it banked waiting, so every later proof asks another checkpoint clean "
            "run - REG-1988's run per proof, back",
     "file": "heart2.py",
     "find": "    _CLEAN.pending = keep\n",
     "replace": "    pass\n",
     "matches": 1},
    {"why": "#150 (review) - a red checkpoint takes nothing back: proofs banked before it in the same gate are "
            "reused by the resumed push",
     "file": "heart2.py",
     "find": "            _checkpoint_revoke(name, say, run)\n            return False\n",
     "replace": "            return False\n",
     "matches": 1},
    {"why": "#150 - a red CLOSING run after green checkpoints takes nothing back",
     "file": "heart2.py",
     "find": "                _checkpoint_revoke(name, say, run)       # #150 - the closing run went RED after a green checkpoint\n",
     "replace": "                pass\n",
     "matches": 1},
    {"why": "#150 - a gate that closed green keeps its checkpoint marks, so every later push counts them as SAVED",
     "file": "heart2.py",
     "find": "                _checkpoint_close(name, run)\n",
     "replace": "                pass\n",
     "matches": 1},
    {"why": "#150 (review) - the push record says nothing of what the checkpoints cost or saved",
     "file": "heart2.py",
     "find": "        \"checkpoint\": _checkpoint_record(run, per),\n",
     "replace": "",
     "matches": 1},
    {"why": "#150 - a hit on a killed run's checkpoint bank is not counted as saved: the saving never shows as a number",
     "file": "heart2.py",
     "find": "                        _PUSH.ckpt[\"resumed\"] += 1\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2943 - the fatal-signal handler exits without writing what the push had already banked",
     "file": "heart2.py",
     "find": "    _flush_on_kill()\n    _remove_all_sandboxes()\n",
     "replace": "    _remove_all_sandboxes()\n",
     "matches": 1,
     "needs": "posix-signals"},
]
