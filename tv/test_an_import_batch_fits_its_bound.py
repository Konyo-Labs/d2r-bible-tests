# -*- coding: utf-8 -*-
"""REG-3415 (v3882, his 11-08: "the proofs being proven properly on all machines ... rivers flowing finally?") - AN IMPORT
BATCH IS SIZED BY TIME, SO A RUN KILLED AT ITS BOUND KEEPS ALL BUT ITS LAST FEW MINUTES; AND THE LOCKS' GUARDS ARE TRUSTED
THE MOMENT THEY ARE BANKED.

MEASURED on the work ALT 11-08 (8 GB, i3; read-only SSH): the v3880 import of GitHub's proofs ran 5,425 s, was killed at
proof_release's 5,400 s bound and banked NOTHING (.proof_release.json: TimeoutExpired, "keying 236 law(s) here, one at a
time (790 MB free: a worker needs 400 MB over a 1024 MB floor)"). The next run's to-do GREW (4,227 -> 4,350 keyer calls,
progress.json) and keyed at ~0.7 a second (162 in ~4 min). REG-3352's batches were a fixed 1,500 calls, the shut locks'
guards first - so the first batch never reached its write inside the bound, and every run re-keyed the same batch: a
livelock. frame.release's guards (test_control, test_ledger_authority, ...) were never banked, the trust pass never ran,
and the ALT's river sat 'ROUTED 37 - the drain owes them a tombstone' behind a shut lock.

  * the first batch holds IMPORT_FIRST_BATCH calls; each later one what the last batch's measured rate keys in
    IMPORT_BATCH_TARGET_S (never under IMPORT_BATCH_MIN, never over IMPORT_BATCH_PROOFS) - a law is still never split;
  * with --trust, the trust pass runs - over the guard laws alone - right after the batch that banks the last of the shut
    locks' guards, so a lock opens at its guards, not at the end of a run its bound may kill.

Every store is a temp file; HEAD is a stand-in; the clock is the law's own (heart2._import_clock).
[[feedback-fixtures-never-touch-live-data]] [[the-unjoined-end]] RED_PROOF below.
"""
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

from console_safe import enable as _console_safe_enable  # noqa: E402  (it prints non-ASCII)
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import heart2        # noqa: E402
import proof_shard   # noqa: E402

HEAD = "0123456789abcdef0123456789abcdef01234567"
CI_TREE = "/home/runner/work/repo/repo"
ALT_S_PER_KEY = 1.0 / 0.7          # the work ALT's measured keying rate, ~0.7 a second
BOUND_S = 5400.0                   # proof_release's bound


def _e(gate, proof):
    return {"verdict": "PROVEN", "gate": gate, "proof": proof, "why": "w", "tree": CI_TREE, "provedAt": 1761200000000}


class _Fixture(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="importbound-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.target = os.path.join(self.tmp, "home", os.path.basename(heart2.CACHE))
        os.makedirs(os.path.dirname(self.target))
        self.said, self.keys, self.now = [], {}, [0.0]
        for p in (mock.patch.object(heart2, "_git", side_effect=lambda *a: (True, HEAD + "\n") if a[0] == "rev-parse"
                                    else (True, "")),
                  mock.patch.object(heart2, "_import_clock", lambda: self.now[0])):
            p.start()
            self.addCleanup(p.stop)

        def keyer(g, i):                       # each key costs what it costs on the work ALT
            self.now[0] += ALT_S_PER_KEY
            return self.keys.get((g, i))
        p = mock.patch.object(heart2, "_shard_keyer", return_value=keyer)
        p.start()
        self.addCleanup(p.stop)

    def bundle(self, laws, proofs):
        """one shard of `laws` laws, `proofs` proofs each (the work ALT's v3880 set: 291 laws, ~15 each)"""
        d = os.path.join(self.tmp, "shard-1")
        os.makedirs(d, exist_ok=True)
        ent, own = {}, {}
        for li in range(laws):
            g = "law_%03d" % li
            for pi in range(proofs):
                k = "k%03d_%02d" % (li, pi)
                ent[k] = _e(g, pi)
                self.keys[(g, pi)] = k
                own.setdefault(g, set()).add(pi)
        man = proof_shard.manifest(1, 1, HEAD, False, "plan-r", own, None, [], 1761200000000)
        path = os.path.join(d, os.path.basename(heart2.CACHE))
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"format": 2, "entries": ent, "shard": man}))
        return [path]

    def home(self):
        if not os.path.exists(self.target):
            return {}
        with io.open(self.target, encoding="utf-8") as fh:
            return json.load(fh).get("entries") or {}

    def killed_at_the_bound(self):
        """proof_release's kill: a write that would land after the bound never happens"""
        real = heart2._import_write

        def write(target, take, say, out):
            if self.now[0] > BOUND_S:
                return False, "fixture: killed at the %d s bound" % BOUND_S
            return real(target, take, say, out)
        return mock.patch.object(heart2, "_import_write", write)


class ARunKilledAtItsBoundKeepsItsBatches(_Fixture):

    def test_the_work_alts_import_keeps_what_it_keyed_before_the_kill(self):
        """* THE POINT - 291 laws x 15 proofs at the ALT's 0.7 a second: ~104 min of keying against a 90-min bound"""
        paths = self.bundle(291, 15)
        with self.killed_at_the_bound():
            rc = heart2.import_shards(paths, say=self.said.append, target=self.target)
        self.assertEqual(rc, 2, "PREMISE: the whole set cannot be keyed inside the bound: %s" % self.said[-3:])
        kept = len(self.home())
        self.assertGreaterEqual(kept, int(BOUND_S / ALT_S_PER_KEY) - int(heart2.IMPORT_BATCH_TARGET_S / ALT_S_PER_KEY) - 15,
                                "a run killed at its bound kept %d keys of the %d it keyed in %d s - a batch outlived "
                                "the bound" % (kept, int(BOUND_S / ALT_S_PER_KEY), BOUND_S))

    def test_the_next_run_finishes_the_set(self):
        paths = self.bundle(291, 15)
        with self.killed_at_the_bound():
            heart2.import_shards(paths, say=self.said.append, target=self.target)
        self.now[0] = 0.0
        with self.killed_at_the_bound():
            self.assertEqual(heart2.import_shards(paths, say=self.said.append, target=self.target), 0, self.said[-3:])
        self.assertEqual(len(self.home()), 291 * 15)

    def test_no_batch_keys_much_past_its_target(self):
        paths = self.bundle(120, 15)
        seen = []
        real = heart2._import_write

        def write(target, take, say, out):
            seen.append(self.now[0])
            return real(target, take, say, out)
        with mock.patch.object(heart2, "_import_write", write):
            self.assertEqual(heart2.import_shards(paths, say=self.said.append, target=self.target), 0)
        spans = [b - a for a, b in zip([0.0] + seen, seen)]
        self.assertGreater(len(spans), 3, spans)
        self.assertLessEqual(max(spans), heart2.IMPORT_BATCH_TARGET_S + 15 * ALT_S_PER_KEY,
                             "a batch keyed %.0f s before its write: %s" % (max(spans), [int(s) for s in spans]))


class TheSizeComesFromTheMeasuredRate(unittest.TestCase):

    def test_the_first_batch_is_small(self):
        self.assertLessEqual(heart2._next_batch_size(None, None), heart2.IMPORT_FIRST_BATCH)
        self.assertLess(heart2.IMPORT_FIRST_BATCH * ALT_S_PER_KEY, BOUND_S / 10.0)

    def test_each_later_batch_keys_its_target_at_the_rate_measured(self):
        self.assertEqual(heart2._next_batch_size(150, 150 * ALT_S_PER_KEY), int(0.7 * heart2.IMPORT_BATCH_TARGET_S))
        self.assertEqual(heart2._next_batch_size(1500, 100.0), heart2.IMPORT_BATCH_PROOFS, "a fast PC keeps the cap")
        self.assertEqual(heart2._next_batch_size(1, 1000.0), heart2.IMPORT_BATCH_MIN, "a crawl still banks something")

    def test_a_rate_that_cannot_be_measured_keeps_the_first_size(self):
        for calls, sec in ((10, 0), (0, 5.0), (None, 3.0), (5, float("nan"))):
            self.assertEqual(heart2._next_batch_size(calls, sec), heart2._next_batch_size(None, None), (calls, sec))


class TheGuardsAreTrustedTheMomentTheyAreBanked(_Fixture):

    def setUp(self):
        super(TheGuardsAreTrustedTheMomentTheyAreBanked, self).setUp()
        self.trusted, self.writes = [], []
        self.rank = dict(("law_%03d" % i, n) for n, i in enumerate(range(0, 60, 5)))   # 12 guard laws: 180 calls
        real = heart2._import_write

        def write(target, take, say, out):
            self.writes.append(len(take))
            return real(target, take, say, out)
        for p in (mock.patch.object(heart2, "trust_now", lambda say=None, only=None: self.trusted.append(
                      (len(self.writes), sorted(only) if only is not None else None)) or 0),
                  mock.patch.object(heart2, "_import_write", write),
                  mock.patch.object(heart2, "_import_order", lambda target=None: dict(self.rank))):
            p.start()
            self.addCleanup(p.stop)

    def test_the_trust_pass_runs_once_right_after_the_last_guard_lands(self):
        """* THE POINT - the guards span two batches (12 laws x 15 > the first batch of 150): one early pass, after the second"""
        paths = self.bundle(60, 15)
        self.assertEqual(heart2.import_shards(paths, say=self.said.append, target=self.target, trust=True), 0)
        self.assertGreater(len(self.writes), 3, "PREMISE: several batches")
        self.assertEqual(self.trusted, [(2, sorted(self.rank))],
                         "the trust pass ran %r (batches written, laws asked) - not once, right after the guards' batch"
                         % self.trusted)

    def test_no_trust_was_asked_none_runs(self):
        self.assertEqual(heart2.import_shards(self.bundle(60, 15), say=self.said.append, target=self.target), 0)
        self.assertEqual(self.trusted, [])

    def test_main_hands_the_import_its_trust(self):
        seen = {}
        with mock.patch.object(heart2, "import_shards", lambda paths, progress=None, trust=False: seen.update(
                trust=trust) or 2):
            heart2.main(["--import-shards", "x.json", "--trust"])
        self.assertIs(seen.get("trust"), True, seen)


class TheEarlyPassAsksTheGuardsAlone(unittest.TestCase):

    def test_only_names_the_gates_the_bank_is_asked_for(self):
        asked = {}
        with mock.patch.object(heart2, "_census_cache", lambda *a, **k: object()), \
                mock.patch.object(heart2, "gate_files", lambda say=None: [("law_a", "a.py"), ("law_b", "b.py")]), \
                mock.patch.object(heart2, "trust_pass", lambda cache, say=None, gates=None: asked.update(gates=gates)):
            heart2.trust_now(say=lambda *a, **k: None, only=["law_b"])
        self.assertEqual(asked.get("gates"), [("law_b", "b.py")], asked)
        with mock.patch.object(heart2, "_census_cache", lambda *a, **k: object()), \
                mock.patch.object(heart2, "trust_pass", lambda cache, say=None, gates=None: asked.update(gates=gates)):
            heart2.trust_now(say=lambda *a, **k: None)
        self.assertIsNone(asked.get("gates"), "the lane's own trust pass no longer asks every owed gate")


RED_PROOF = [
    {"why": "REG-3415 - the first batch is the fixed 1,500 again: the work ALT's first batch never reaches its write",
     "file": "heart2.py",
     "find": "        _size = _next_batch_size(None, None)           # REG-3415 - the first batch is small; the rest, sized by time\n",
     "replace": "        _size = IMPORT_BATCH_PROOFS\n", "matches": 1},
    {"why": "REG-3415 - later batches ignore the measured rate: one long batch outlives the bound",
     "file": "heart2.py",
     "find": "            _size = _next_batch_size(_n_b, _import_clock() - _t_b)\n",
     "replace": "            _size = IMPORT_BATCH_PROOFS\n", "matches": 1},
    {"why": "REG-3415 - the rate is not turned into a batch that keys its target",
     "file": "heart2.py",
     "find": "    return max(1, min(cap, max(IMPORT_BATCH_MIN, int(rate * IMPORT_BATCH_TARGET_S))))\n",
     "replace": "    return max(1, min(cap, max(IMPORT_BATCH_MIN, int(rate * IMPORT_BATCH_TARGET_S * 20))))\n", "matches": 1},
    {"why": "REG-3415 - no early trust: the locks wait for the end of a run its bound may kill",
     "file": "heart2.py",
     "find": "                trust_now(say=say, only=sorted(_rank))\n",
     "replace": "                pass\n", "matches": 1},
    {"why": "REG-3415 - the early trust runs after every batch that holds a guard, not once when the last guard lands",
     "file": "heart2.py",
     "find": "    return bool(held & set(rank)) and not (left & set(rank))\n",
     "replace": "    return bool(held & set(rank))\n", "matches": 1},
    {"why": "REG-3415 - the early trust re-keys every owed law (the guards are not the only gates asked)",
     "file": "heart2.py",
     "find": "            trust_pass(cache, say=say, gates=[(n, f) for n, f in gate_files() if n in _only])\n",
     "replace": "            trust_pass(cache, say=say)\n", "matches": 1},
    {"why": "REG-3415 - main never hands the import its --trust: no early pass on a real import",
     "file": "heart2.py",
     "find": "        _irc = import_shards(a.import_shards, progress=a.import_progress, trust=a.trust)\n",
     "replace": "        _irc = import_shards(a.import_shards, progress=a.import_progress)\n", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
