# -*- coding: utf-8 -*-
"""v3865 REG-3193 - AN IMPORT OF GITHUB'S PROOFS KEYS ON THE PC'S SPARE CORES, AND EVERY KEY IS THE ONE ONE CORE GIVES.

MEASURED 2026-11-05 on his Mac: `heart2 --import-shards` (the console's import after an update, control_app
_PROOF_RELEASE / proof_release.import_bundle) ran on ONE core: 1,278 s for v3863 (2,625 proofs), 1,635 s for v3864, and
every lock stays shut while it runs. A profile of the first 300 entries of the v3864 bundle put 28 of 76 s in
law_inputs' closure walks and the rest in _key's per-proof hashing. heart2._prewarm_keys now computes those answers in
a pool of worker processes and key_for takes them (pre=). A key decided differently in a worker would bank a proof under
a key this tree never gives - or drop one it does - so the law holds, on REAL laws of this tree keyed into a TEMP store:
  * every proof keyed with the pool is keyed byte-identically to one core, and the pool really ran (not a fallback);
  * a v2 variant the target records is keyed by the pool exactly as key_for would (the variant, not the v1 key);
  * a pool that cannot start, or whose jobs fail, is SAID, and every key still comes - from here, one at a time;
  * workers = cores - 2, at most IMPORT_WORKERS_MAX, and no more than free memory above the floor holds; UNKNOWN cores
    or memory -> one at a time;
  * a worker asks git nothing (it takes its parent's tracked/kept sets) and leaves when its parent is gone;
  * on Windows the workers run under pythonw (no console window on his screen);
  * both import paths (--import-shards, --import-proved) prewarm before select().
Fixtures only: HEART2_CACHE_PATH / HEART2_RED_PATH / TV_HEART_CENSUS name a scratch dir before heart2 is imported.
RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402  #171 - this run's scratch dirs leave with it
_fx_tmp.contain()

_SCRATCH = tempfile.mkdtemp(prefix="import-pool-law-")
os.environ["HEART2_CACHE_PATH"] = os.path.join(_SCRATCH, ".heart2_cache.json")
os.environ["HEART2_RED_PATH"] = os.path.join(_SCRATCH, ".heart2_red.json")
os.environ["TV_HEART_CENSUS"] = os.path.join(_SCRATCH, ".heart2.json")
import heart2 as H  # noqa: E402
import proof_shard as PS  # noqa: E402

#: real laws of this tree with small closures and several proofs each - keyed for real, never run (the second lists a
#: directory itself, so its key is a pending-listing one: that path is held too)
LAWS = ("test_a_ci_run_past_75_minutes_alerts", "test_a_law_file_has_no_invalid_escape")   # v3890: the budget law left with the Ubicloud lane (REG-3505)


def _shards(files, proofs):
    """one shard set naming every proof of LAWS, under made-up keys (select is asked only what the keyer says)"""
    ent, asg, n = {}, set(), 0
    for g in LAWS:
        for i in range(len(proofs[g])):
            n += 1
            ent["claimed-%d" % n] = {"gate": g, "proof": i, "verdict": "PROVEN", "provedAt": 1700000000000 + n}
            asg.add((g, i))
    return [(1, ent, asg)]


class _Fixture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.files = dict(H.gate_files(say=lambda *a, **k: None))
        missing = [g for g in LAWS if g not in cls.files]
        assert not missing, "the fixture's laws are not registered here: %s" % missing
        cls.proofs = dict((g, H.red_proofs_in(cls.files[g]) or []) for g in LAWS)
        assert all(len(cls.proofs[g]) >= 2 for g in LAWS), "a fixture law lost its RED_PROOF list"

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="import-pool-", dir=_SCRATCH)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _keys(self, target, workers=None, pool=None, said=None, here=None):
        """-> ({(gate, idx): key}, prewarm's report); `here` collects each _key call THIS process made while keying"""
        keyer = H._shard_keyer(target)
        rep = None
        sh = _shards(self.files, self.proofs)
        if workers is not None or pool is not None:
            rep = keyer.prewarm(sh, say=(said.append if said is not None else None), workers=workers, pool=pool)
        real = H._VerdictCache._key

        def counted(cache, *a, **k):
            if here is not None:
                here.append(a[1:2])
            return real(cache, *a, **k)
        got = {}
        with mock.patch.object(H._VerdictCache, "_key", counted):
            for g in LAWS:
                for i in range(len(self.proofs[g])):
                    got[(g, i)] = keyer(g, i)
        return got, rep


class ThePoolKeysAsOneCore(_Fixture):

    def test_every_proof_is_keyed_byte_identically_and_the_pool_really_ran(self):
        mine = []
        one, _ = self._keys(os.path.join(self.d, "one.json"), here=mine)
        self.assertTrue(all(isinstance(k, str) and k for k in one.values()), one)
        self.assertEqual(len(mine), len(one), "the one-core fixture did not key every proof here")
        said, mine = [], []
        two, rep = self._keys(os.path.join(self.d, "two.json"), workers=2, said=said, here=mine)
        self.assertEqual(rep["workers"], 2, said)
        self.assertEqual((rep["laws"], rep["answered"]), (len(LAWS), rep["jobs"]),
                         "the pool did not answer every job - keys came from one core: %s" % said)
        self.assertFalse([s for s in said if "REG-3193" in s], said)
        self.assertEqual(mine, [], "the pool answered and the keyer computed the keys here anyway")
        self.assertEqual(two, one, "a worker keyed a proof differently from one core")

    def test_a_law_with_more_proofs_than_a_job_holds_is_shared_across_jobs(self):
        one, _ = self._keys(os.path.join(self.d, "one.json"))
        said, mine = [], []
        with mock.patch.object(H, "IMPORT_JOB_PROOFS", 2):
            two, rep = self._keys(os.path.join(self.d, "two.json"), workers=2, said=said, here=mine)
        want = sum((len(self.proofs[g]) + 1) // 2 for g in LAWS)
        self.assertEqual((rep["jobs"], rep["answered"]), (want, want), said)
        self.assertEqual(mine, [])
        self.assertEqual(two, one, "a law split across jobs was keyed differently")

    def test_a_recorded_variant_is_keyed_by_the_pool_as_key_for_would(self):
        g = LAWS[0]
        fn, pr = self.files[g], self.proofs[g][0]
        c = H._VerdictCache(path=os.path.join(self.d, "probe.json"), say=lambda *a, **k: None)
        k1, rels, why = c.key_for(H.HERE, g, fn, pr)
        self.assertIsNone(why)
        un = [r for r in rels if r.endswith(".py") and "console_safe" in r][:1] or rels[:1]
        k2 = c.key_for(H.HERE, g, fn, pr, unread=un)[0]
        self.assertTrue(k2 and k2 != k1)
        target = os.path.join(self.d, "with-variant.json")
        with io.open(target, "w", encoding="utf-8") as fh:
            json.dump({"format": 2, "entries": {k2: {"gate": g, "proof": 0, "verdict": "PROVEN", "provedAt": 1700000000000,
                                                     "ident": c.ident(g, fn, pr), "unread": un}}}, fh)
        one, _ = self._keys(target)
        self.assertEqual(one[(g, 0)], k2, "the fixture's variant is not what one core serves")
        said = []
        two, rep = self._keys(target, workers=2, said=said)
        self.assertEqual((rep["laws"], rep["answered"]), (len(LAWS), rep["jobs"]), said)
        self.assertEqual(two[(g, 0)], k2, "the pool keyed the v1 key where key_for serves the recorded variant")
        self.assertEqual(two, one)


class _NoStart(object):
    def __init__(self, *a, **k):
        raise OSError("the pool could not start")


class _FailingJobs(object):
    """an executor whose every job fails, the way a broken pool's futures do"""
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def submit(self, fn, *a, **k):
        import concurrent.futures as cf
        f = cf.Future()
        f.set_exception(RuntimeError("a worker died"))
        return f


class AFailedPoolIsSaid(_Fixture):

    def test_a_pool_that_cannot_start_is_said_and_every_key_still_comes(self):
        one, _ = self._keys(os.path.join(self.d, "one.json"))
        for pool in (_NoStart, _FailingJobs):
            said = []
            got, rep = self._keys(os.path.join(self.d, "p.json"), workers=2, pool=pool, said=said)
            self.assertEqual(rep["answered"], 0)
            self.assertTrue([s for s in said if "REG-3193" in s and "one at a time" in s], (pool, said))
            self.assertEqual(got, one, "a failed pool lost or changed keys")

    def test_one_core_is_said_too(self):
        said = []
        got, rep = self._keys(os.path.join(self.d, "one.json"), workers=1, said=said)
        self.assertEqual(rep["workers"], 1)
        self.assertTrue([s for s in said if "one at a time" in s], said)


class HowManyWorkers(unittest.TestCase):

    def test_cores_minus_two_capped_and_never_past_free_memory(self):
        fl = 1024
        big = fl + 100 * H.IMPORT_WORKER_MB
        self.assertEqual(H.import_workers(cpus=10, free_mb=big, floor_mb=fl)[0], 6)   # v3885: at most 6 (his 11-08)
        self.assertEqual(H.import_workers(cpus=12, free_mb=big, floor_mb=fl)[0], 6,
                         "Dean's 12 cores: 8 workers pinned all of them (his 11-08 'cap it to like 5-6')")
        self.assertEqual(H.IMPORT_WORKERS_MAX, 6)
        self.assertEqual(H.import_workers(cpus=64, free_mb=big, floor_mb=fl)[0], H.IMPORT_WORKERS_MAX)
        self.assertEqual(H.import_workers(cpus=4, free_mb=big, floor_mb=fl)[0], 2)
        self.assertEqual(H.import_workers(cpus=3, free_mb=big, floor_mb=fl)[0], 1, "a 3-core PC gave its last spare core away")
        three = fl + 3 * H.IMPORT_WORKER_MB + 1
        self.assertEqual(H.import_workers(cpus=10, free_mb=three, floor_mb=fl)[0], 3, "workers past what free memory holds")
        self.assertEqual(H.import_workers(cpus=10, free_mb=fl + H.IMPORT_WORKER_MB, floor_mb=fl)[0], 1)
        self.assertEqual(H.import_workers(cpus=10, free_mb=fl + 3 * H.IMPORT_WORKER_MB, floor_mb=fl + 1)[0], 2,
                         "the floor was not left to the PC")

    def test_the_floor_is_child_guards_one_figure(self):
        import child_guard as CG
        self.assertEqual(H._import_floor_mb(), int(CG.RAM_FLOOR_MB))
        free = CG.RAM_FLOOR_MB + 2 * H.IMPORT_WORKER_MB
        self.assertEqual(H.import_workers(cpus=10, free_mb=free)[0], 2)
        self.assertEqual(H.import_workers(cpus=10, free_mb=free - 1)[0], 1)

    def test_unknown_is_one_at_a_time_and_says_so(self):
        n, why = H.import_workers(cpus=10, free_mb=None)
        self.assertEqual(n, 1)
        self.assertIn("UNKNOWN", why)
        n, why = H.import_workers(cpus=None, free_mb=64000)
        self.assertEqual(n, 1)
        self.assertIn("UNKNOWN", why)

    def test_windows_workers_run_under_pythonw(self):
        self.assertEqual(H._pool_executable("nt", "C:\\Py\\python.exe", isfile=lambda p: True), "C:\\Py\\pythonw.exe")
        self.assertIsNone(H._pool_executable("nt", "C:\\Py\\python.exe", isfile=lambda p: False))
        self.assertIsNone(H._pool_executable("nt", "C:\\Py\\pythonw.exe", isfile=lambda p: True))
        self.assertIsNone(H._pool_executable("posix", "/usr/bin/python.exe", isfile=lambda p: True))


class _Parent(object):
    def __init__(self):
        self.asked = 0

    def is_alive(self):
        self.asked += 1
        return False


class AWorker(unittest.TestCase):

    def test_asks_git_nothing_and_leaves_when_its_parent_is_gone(self):
        import multiprocessing
        exits, parent = [], _Parent()

        def no_git(*a, **k):
            raise AssertionError("an import worker asked git")
        saved = dict(H._KW)
        try:
            with mock.patch.object(H, "_tracked_files", no_git), mock.patch.object(H, "_kept_files", no_git), \
                    mock.patch.object(H, "IMPORT_WORKER_WATCH_S", 0.01), \
                    mock.patch.object(multiprocessing, "parent_process", lambda: parent), \
                    mock.patch.object(H.os, "_exit", exits.append):
                tracked = frozenset(["tv/x.py"])
                H._key_worker_init(tracked, None, os.path.join(_SCRATCH, "no-such-store.json"))
                self.assertIs(H._KW["cache"].tracked, tracked)
                self.assertIsNone(H._KW["cache"].kept, "an UNKNOWN kept set was asked again in the worker")
                t0 = time.time()
                while not exits and time.time() - t0 < 5:
                    time.sleep(0.01)
            self.assertEqual(exits, [0], "a worker outlived its parent")
        finally:
            H._KW.clear()
            H._KW.update(saved)


def _code(path):
    with io.open(path, encoding="utf-8") as fh:
        return "\n".join(re.sub(r"\s+#.*$", "", ln) for ln in fh.read().split("\n"))


class BothImportPathsPrewarm(unittest.TestCase):

    def test_import_shards_and_import_proved_ask_for_it_around_select(self):
        src = _code(os.path.join(HERE, "heart2.py"))
        for fn, ask, sel in (("import_shards", "with _keys_prewarmed(target, shards, say=say, progress=_prog):",
                              "_PS.select(shards, keyer=_shard_keyer(target), dropped=_dropped, here=TREE_ID)"),
                             ("import_proved", "with _keys_prewarmed(target, sets, say=say):",
                              "_PS.select(sets, keyer=_shard_keyer(target), dropped=_gone, here=TREE_ID,")):
            body = src[src.index("\ndef %s(" % fn):]
            body = body[:body.index("\ndef ", 1)]
            self.assertEqual(body.count(ask), 1, fn)
            self.assertEqual(body.count(sel), 1, fn)
            gap = body[body.index(ask) + len(ask):body.index(sel)]
            self.assertRegex(gap, r"^\n +ok, why, take, skipped = $", "%s: select does not run inside the ask" % fn)

    def test_a_keyer_built_inside_the_ask_is_prewarmed_and_one_outside_is_not(self):
        asked = []
        target = os.path.join(_SCRATCH, "ask.json")
        with mock.patch.object(H, "_prewarm_keys", lambda st, sh, **k: asked.append((sh, k.get("progress"))) or {}):
            H._shard_keyer(target)
            self.assertEqual(asked, [], "a keyer nobody asked to prewarm was prewarmed")
            with H._keys_prewarmed(target, ["the shards"], progress="p"):
                H._shard_keyer(target)
            H._shard_keyer(target)
        self.assertEqual(asked, [(["the shards"], "p")], "the import's keyer was not prewarmed exactly once")


def tearDownModule():
    shutil.rmtree(_SCRATCH, ignore_errors=True)


RED_PROOF = [
    {"why": "v3865 REG-3193 - a worker keys every proof with the law's FIRST proof: the import banks under keys this tree "
            "never gives",
     "file": "tv/heart2.py",
     "find": "        pr, got = proofs[i], {}\n",
     "replace": "        pr, got = proofs[0], {}\n",
     "matches": 1},
    {"why": "v3865 REG-3193 - key_for serves the worker's v1 answer for a recorded v2 variant",
     "file": "tv/heart2.py",
     "find": "            got = pre.get((tuple(un), ls)) if pre else None\n",
     "replace": "            got = pre.get(((), None)) if pre else None\n",
     "matches": 1},
    {"why": "v3865 REG-3193 - a law's proofs all go to one job: test_control's hundreds run on alone while the pool waits",
     "file": "tv/heart2.py",
     "find": "        for a in range(0, len(ix), IMPORT_JOB_PROOFS):\n            jobs.append((g, st[\"files\"][g], ix[a:a + IMPORT_JOB_PROOFS], vmap.get(g)))\n",
     "replace": "        for a in range(0, len(ix), len(ix)):\n            jobs.append((g, st[\"files\"][g], ix, vmap.get(g)))\n",
     "matches": 1},
    {"why": "v3865 REG-3193 - a pool that fails is not said",
     "file": "tv/heart2.py",
     "find": "    if broke or failed or rep[\"answered\"] < len(jobs):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3865 REG-3193 - the worker count ignores free memory (the 8 GB ALT)",
     "file": "tv/heart2.py",
     "find": "    n = min(by_cpu, by_mem)\n",
     "replace": "    n = by_cpu\n",
     "matches": 1},
    {"why": "v3865 REG-3193 - an UNKNOWN free memory reads as plenty",
     "file": "tv/heart2.py",
     "find": "    if not isinstance(free_mb, (int, float)) or isinstance(free_mb, bool):\n        return 1, \"this PC's free memory is UNKNOWN\"\n",
     "replace": "    if not isinstance(free_mb, (int, float)) or isinstance(free_mb, bool):\n        free_mb = 1 << 20\n",
     "matches": 1},
    {"why": "v3865 REG-3193 - a worker asks git for the tracked set itself (a console window on Windows, and maybe another set)",
     "file": "tv/heart2.py",
     "find": "    _KW[\"cache\"] = _VerdictCache(path=store, say=lambda *a, **k: None, tracked=tracked, kept=kept)\n",
     "replace": "    _KW[\"cache\"] = _VerdictCache(path=store, say=lambda *a, **k: None)\n",
     "matches": 1},
    {"why": "v3865 REG-3193 - a worker never notices its parent is gone",
     "file": "tv/heart2.py",
     "find": "            if gone:\n                os._exit(0)\n",
     "replace": "            if False:\n                os._exit(0)\n",
     "matches": 1},
    {"why": "v3865 REG-3193 - Windows workers run under python.exe (a console window on his screen)",
     "file": "tv/heart2.py",
     "find": "    if platform == \"nt\" and exe.lower().endswith(\"python.exe\"):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3865 REG-3193 - the import's keyer is never prewarmed: the import keys on one core again",
     "file": "tv/heart2.py",
     "find": "    asked = _PREWARM_ASKED.pop(target, None)\n",
     "replace": "    asked = None\n",
     "matches": 1},
    {"why": "v3865 REG-3193 - the pool's answers are never handed to the keyer: everything is keyed on one core again",
     "file": "tv/heart2.py",
     "find": "                            st[\"pre\"][(gate, i)] = ans\n",
     "replace": "                            pass\n",
     "matches": 1},
    {"why": "v3885 (his 11-08 'cap it to like 5-6') - the import keys on 8 workers again (Dean's 12 cores pinned)",
     "file": "tv/heart2.py",
     "find": "IMPORT_WORKERS_MAX = 6\n",
     "replace": "IMPORT_WORKERS_MAX = 8\n", "matches": 1}
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
