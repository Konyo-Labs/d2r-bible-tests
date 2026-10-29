# -*- coding: utf-8 -*-
"""REG-3074 (#84, GrokBot #230 ticks on 2026-10-12) - A LOCK NEVER PUBLISHES MORE REFUSALS THAN ATTEMPTS.

GrokBot read the Heart fan twice on v3679/v3680 as "printer.stream earned 138/135" (earned above its total). Measured:
v3680's own self_arming over v3680's own ledger scores printer.stream k=135 n=135 (657 rows, 0 faults; its folded rows
are sabotage 126/126 and live 9/9, unchanged since 2026-09-22), and that build's caption printed L.k + '/' + L.n as
served. GrokBot's next three ticks the same day and its 10-16 answer read 135/135. So the 138 was a misread of the
pixels, not a figure the arithmetic made - NOT A DEFECT in the count.

What makes "k above n" impossible is two checks: bank() refuses k > n at its door, and _row_fault refuses a row with
k > n on the way out of the file, so a hand-edited or crashed-writer row fails the read CLOSED (UNKNOWN, which is
LOCKED) instead of scoring. No law named either check (no tv/test_*.py carried their refusal text). This law holds
both, on an isolated ledger, and holds the shape over the tracked ledger: every lock publishes k <= n and
attacksPassed <= attacks <= n. RED_PROOF below. [[unknown-stays-unknown]]
"""
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import self_arming as SA  # noqa: E402

TRACKED = os.path.join(HERE, ".self_arming.jsonl")


class _Isolated(unittest.TestCase):
    """Both ledgers point into a temp dir for the whole test; his ledgers are never opened for writing."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sa-kn-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.shared = os.path.join(self.tmp, "shared.jsonl")
        self.here = os.path.join(self.tmp, "here.jsonl")
        self._env = {k: os.environ.get(k) for k in ("TV_SELF_ARMING_LEDGER", "TV_SELF_ARMING_HERE")}
        os.environ["TV_SELF_ARMING_LEDGER"] = self.shared
        os.environ["TV_SELF_ARMING_HERE"] = self.here
        self.addCleanup(self._restore)
        # the redirect is resolved at call time - prove it took before anything is written
        self.assertEqual(SA._ledger_path(), self.shared)
        self.assertEqual(SA._here_path(), self.here)

    def _restore(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _write(self, rows):
        with io.open(self.shared, "w", encoding="utf-8") as fh:
            fh.write("".join(json.dumps(r) + "\n" for r in rows))


def _row(n, k, ts):
    return {"lock": "printer.stream", "kind": "sabotage", "src": "printer_wilson", "ref": "",
            "n": n, "k": k, "refused": bool(k > 0), "attacks": 36, "withdrawn": False, "note": "", "ts": ts}


class TheDoorRefusesMoreRefusalsThanAttempts(_Isolated):

    def test_bank_refuses_k_above_n_and_writes_nothing(self):
        with self.assertRaises(ValueError) as cm:
            SA.bank("printer.stream", "sabotage", "printer_wilson", n=135, k=138, attacks=36)
        self.assertIn("k=138 of n=135", str(cm.exception))
        self.assertFalse(os.path.exists(self.shared) and os.path.getsize(self.shared),
                         "bank() refused and still wrote a row")

    def test_baseline_bank_takes_k_equal_to_n(self):
        SA.bank("printer.stream", "sabotage", "printer_wilson", n=135, k=135, attacks=36)
        s = SA.score("printer.stream")
        self.assertEqual((s["k"], s["n"]), (135, 135), s)


class AFileRowWithMoreRefusalsFailsTheReadClosed(_Isolated):

    def test_baseline_a_sound_row_scores(self):
        self._write([_row(135, 135, int(time.time() * 1000) - 60000)])
        s = SA.score("printer.stream")
        self.assertEqual((s["k"], s["n"]), (135, 135), "PREMISE: a sound row must score: %r" % s)

    def test_a_row_with_k_above_n_is_unknown_never_a_figure(self):
        self._write([_row(135, 138, int(time.time() * 1000) - 60000)])
        s = SA.score("printer.stream")
        self.assertEqual(s["state"], SA.UNKNOWN, "a row with 138 refusals of 135 attempts was scored: %r" % s)
        self.assertIsNone(s.get("k"), "UNKNOWN still published a refusal count: %r" % s)
        self.assertIn("k=138 of n=135", s.get("why") or "", s)
        ok, why = SA.may("printer.stream")   # an unreadable queue answers before the heart is ever asked
        self.assertFalse(ok, "a ledger that cannot be read must leave the lock LOCKED: %r" % why)
        self.assertIn("UNKNOWN", why)


class EveryLockOnTheTrackedLedgerPublishesASoundPair(_Isolated):

    def test_every_lock_and_route_has_k_at_most_n(self):
        self.assertTrue(os.path.exists(TRACKED), "the tracked proof ledger is gone - re-point this law")
        shutil.copyfile(TRACKED, self.shared)
        names = sorted(SA.LOCKS) + sorted(SA.ROUTES)
        scored, bad = 0, []
        for lk in names:
            s = SA.score(lk)
            self.assertNotEqual(s.get("state"), SA.UNKNOWN, "the tracked ledger did not read: %r" % s)
            k, n, a, ap = s.get("k"), s.get("n"), s.get("attacks"), s.get("attacksPassed")
            if not n:
                continue
            scored += 1
            if not (0 <= k <= n):
                bad.append("%s k=%r n=%r" % (lk, k, n))
            if a is not None and not (0 <= ap <= a <= n):
                bad.append("%s attacksPassed=%r attacks=%r n=%r" % (lk, ap, a, n))
        self.assertGreater(scored, 5, "PREMISE: too few locks carry evidence to say anything (%d)" % scored)
        self.assertEqual(bad, [], "a lock publishes a pair no ledger could have earned")


RED_PROOF = [
    {"why": "REG-3074 - bank() writes a row with more refusals than attempts",
     "file": "tv/self_arming.py",
     "find": "    if n < 0 or k < 0 or k > n:\n",
     "replace": "    if n < 0 or k < 0:\n",
     "matches": 1},
    {"why": "REG-3074 - a file row with more refusals than attempts is scored instead of failing the read closed",
     "file": "tv/self_arming.py",
     "find": "        if not (0 <= k <= n):\n",
     "replace": "        if not (0 <= k):\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
