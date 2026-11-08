# -*- coding: utf-8 -*-
"""v3865 REG-3194 - WHILE GITHUB'S PROOFS ARE IMPORTED, THE CONSOLE SAYS HOW FAR THE IMPORT IS: done / of / etaS.

MEASURED 2026-11-05 on his Mac: the import after an update (control_app _PROOF_RELEASE, 'proofRelease' in /api/status)
ran 1,278 s for v3863 and 1,635 s for v3864 with every lock shut, and all the console could say was "importing" - no
count, no end. Now heart2 --import-shards keeps {done, of, etaS, at, phase} in the file --import-progress names
(_ImportProgress), proof_release reads it every PROGRESS_POLL_S while heart2 runs (_ProgressWatch, and once more when it
ends), and the console copies done / of / etaS (+ progressAt, heart2's own stamp) into _PROOF_RELEASE - the three names
the fleet chip reads. Held here:
  * done/of count select()'s keyer calls exactly once each, one core or a pool (no double count, none missed);
  * etaS is None until 1% is done and once all is (the store's write has no rate): None is UNKNOWN, never 0;
  * the file is written at most every EVERY_S (and always at a phase change), atomically;
  * a reading of 0, negative, a bool or garbage is None (UNKNOWN), never a number;
  * proof_release hands heart2 a progress file in the import's own scratch dir and reads it WHILE heart2 runs, and once
    more after, so the last count is never lost;
  * the console resets done/of/etaS to None when a run starts and publishes each reading under exactly those names;
  * heart2's CLI hands --import-progress to the import.
Fixtures only: a scratch store, stub runs, a stub import; no network. RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
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

_SCRATCH = tempfile.mkdtemp(prefix="import-progress-law-")
os.environ["HEART2_CACHE_PATH"] = os.path.join(_SCRATCH, ".heart2_cache.json")
os.environ["HEART2_RED_PATH"] = os.path.join(_SCRATCH, ".heart2_red.json")
os.environ["TV_HEART_CENSUS"] = os.path.join(_SCRATCH, ".heart2.json")
import heart2 as H  # noqa: E402
import proof_release as PR  # noqa: E402
import proof_shard as PS  # noqa: E402

SHA = "c" * 40
LAWS = ("test_the_proof_budget_never_passes_its_cap", "test_a_law_file_has_no_invalid_escape")


class _Clock(object):
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


class TheProgressFile(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="p-", dir=_SCRATCH)
        self.p = os.path.join(self.d, "progress.json")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_counts_and_an_eta_only_once_it_is_measured(self):
        clk = _Clock()
        pg = H._ImportProgress(self.p, 400, clock=clk)
        b = _read(self.p)
        self.assertEqual((b["done"], b["of"], b["etaS"], b["phase"]), (0, 400, None, "keying"))
        clk.t += 10
        pg.add(3)                                         # under 1%: no rate yet
        self.assertIsNone(_read(self.p)["etaS"], "an ETA from three of 400")
        clk.t += 0.5
        pg.add(1)                                         # inside EVERY_S: not written
        self.assertEqual(_read(self.p)["done"], 3, "the file was written on every call")
        clk.t += H._ImportProgress.EVERY_S
        pg.add(0)
        b = _read(self.p)
        self.assertEqual(b["done"], 4)
        self.assertEqual(b["etaS"], int(round(12.5 * 396 / 4.0)))
        self.assertIsInstance(b["at"], int)
        clk.t += 10
        pg.add(396)
        b = _read(self.p)
        self.assertEqual((b["done"], b["of"]), (400, 400))
        self.assertIsNone(b["etaS"], "an ETA once every key is done (what remains has no rate)")
        pg.write("writing", force=True)
        self.assertEqual((_read(self.p)["phase"], _read(self.p)["etaS"]), ("writing", None))
        self.assertFalse(os.path.exists(self.p + ".tmp"), "a half-written file was left")

    def test_it_writes_only_its_own_name_and_never_into_the_tree(self):
        self.assertEqual(H.IMPORT_PROGRESS_NAME, PR.PROGRESS_NAME, "heart2 and proof_release name the file differently")
        other = os.path.join(self.d, "census.json")
        H._ImportProgress(other, 10)
        self.assertFalse(os.path.exists(other), "the import wrote a file that is not its progress file")
        inside = os.path.join(HERE, H.IMPORT_PROGRESS_NAME)
        self.assertFalse(os.path.exists(inside), "PREMISE: a progress file already sits in tv/")
        try:
            pg = H._ImportProgress(inside, 10)
            self.assertFalse(pg.write("keying", force=True))
            self.assertFalse(os.path.exists(inside), "the import wrote into the checkout")
        finally:
            for q in (inside, inside + ".tmp"):
                if os.path.exists(q):
                    os.remove(q)

    def test_a_tiny_remainder_is_never_an_eta_of_zero(self):
        clk = _Clock()
        pg = H._ImportProgress(self.p, 100000, clock=clk)
        clk.t += 1
        pg.add(99999)
        self.assertEqual(pg.eta_s(), 1)

    def test_a_reading_that_is_not_a_count_is_unknown(self):
        self.assertIsNone(PR.read_progress(os.path.join(self.d, "absent.json")))
        for bad in ({"done": -1, "of": True, "etaS": 0, "at": "x"}, {"done": 1.5, "of": None, "etaS": -3, "at": 0}):
            with io.open(self.p, "w", encoding="utf-8") as fh:
                json.dump(bad, fh)
            self.assertEqual(PR.read_progress(self.p), {"done": None, "of": None, "etaS": None, "at": None}, bad)
        with io.open(self.p, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertIsNone(PR.read_progress(self.p))
        with io.open(self.p, "w", encoding="utf-8") as fh:
            json.dump({"done": 5, "of": 10, "etaS": 30, "at": 1700000000000, "phase": "keying"}, fh)
        self.assertEqual(PR.read_progress(self.p), {"done": 5, "of": 10, "etaS": 30, "at": 1700000000000})


class TheEtaIsTheRecentRate(unittest.TestCase):
    """v3882 (his 11-08: "the 5 min thing isnt correlated correctly and synced properly to the numbers ... also on the alt
    pcs"). MEASURED on Dean's PC 03:03: the file said etaS 380-425 while the count moved 2,997 -> 3,029 in 60 s (0.53 a
    second, ~43 min for the 1,367 left): the ETA was the rate SINCE THE START, six times too short."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="p-", dir=_SCRATCH)
        self.p = os.path.join(self.d, "progress.json")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _dean(self):
        clk = _Clock()
        pg = H._ImportProgress(self.p, 10000, clock=clk)
        for _ in range(60):                    # the fast start: 3,000 keys in a minute
            clk.t += 1
            pg.add(50)
        for k in range(180):                   # then 0.5 a second, beside his game
            clk.t += 1
            pg.add(1 if k % 2 == 0 else 0)
        return clk, pg

    def test_the_eta_follows_the_recent_rate(self):
        """* THE POINT - Dean's shape: the ETA is the time the CURRENT rate needs, never the start's average"""
        clk, pg = self._dean()
        true = (10000 - pg.done) / 0.5
        eta = pg.eta_s()
        self.assertTrue(abs(eta - true) <= 0.05 * true, "the ETA %r is not the recent rate's %r" % (eta, true))
        lifetime = (240 * (10000 - pg.done)) / float(pg.done)
        self.assertGreater(eta, 10 * lifetime, "PREMISE: the start's average would have said ~%d s" % lifetime)
        self.assertEqual(_read(self.p)["etaS"], eta, "the file carries another ETA than the one computed")

    def test_no_progress_in_the_window_is_unknown(self):
        clk, pg = self._dean()
        clk.t += H._ImportProgress.WINDOW_S + 20
        self.assertIsNone(pg.eta_s(), "a stalled import still promised a time")

    def test_a_quiet_reading_drops_its_eta_on_the_console(self):
        import control_app as ca
        now = 1794100000000
        rel = {"running": True, "done": 3029, "of": 4396, "etaS": 425, "ver": "v3880", "progressAt": now - 200 * 1000}
        q = ca.heart_importing(rel, {}, now_ms=now)
        self.assertIsNone(q["etaS"], "a reading 200 s old repeated its ETA")
        self.assertEqual(q["quietS"], 200)
        fresh = ca.heart_importing(dict(rel, progressAt=now - 5 * 1000), {}, now_ms=now)
        self.assertEqual((fresh["etaS"], fresh.get("quietS")), (425, None))
        undated = ca.heart_importing(dict(rel, progressAt=None), {}, now_ms=now)
        self.assertEqual(undated["etaS"], 425, "an undated reading was aged")


class TheKeyerCountsEachCallOnce(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        files = dict(H.gate_files(say=lambda *a, **k: None))
        cls.calls = []
        ent, asg, n = {}, set(), 0
        for g in LAWS:
            for i in range(len(H.red_proofs_in(files[g]) or [])):
                n += 1
                ent["k%d" % n] = {"gate": g, "proof": i, "verdict": "PROVEN", "provedAt": 1700000000000 + n}
                asg.add((g, i))
        ent["not-servable"] = {"gate": LAWS[0], "proof": 0, "verdict": "BLIND", "provedAt": 1}
        cls.shards = [(1, ent, asg)]
        cls.of = n

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="k-", dir=_SCRATCH)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self, workers):
        os.makedirs(os.path.join(self.d, str(workers)))
        p = os.path.join(self.d, str(workers), H.IMPORT_PROGRESS_NAME)
        self.assertEqual(sum(H._keyer_calls(self.shards).values()), self.of, "the BLIND entry was counted")
        pg = H._ImportProgress(p, sum(H._keyer_calls(self.shards).values()))
        keyer = H._shard_keyer(os.path.join(self.d, "store-%d.json" % workers))
        rep = keyer.prewarm(self.shards, workers=workers, progress=pg)
        after_pool = pg.done
        ok, why, take, skipped = PS.select(self.shards, keyer=keyer, dropped=[])
        self.assertTrue(ok, why)
        return rep, after_pool, pg.done

    def test_one_core_counts_each_keyer_call(self):
        rep, after_pool, done = self._run(1)
        self.assertEqual(after_pool, 0)
        self.assertEqual(done, self.of)

    def test_a_pool_counts_what_it_answered_and_the_keyer_never_counts_it_again(self):
        rep, after_pool, done = self._run(2)
        self.assertEqual((rep["laws"], rep["answered"]), (len(LAWS), rep["jobs"]))
        self.assertEqual(after_pool, self.of, "the pool's answers were not counted as they came")
        self.assertEqual(done, self.of, "a key was counted twice (or missed)")


class TheConsoleReadsItWhileHeart2Runs(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="c-", dir=_SCRATCH)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_proof_release_hands_a_scratch_file_and_reads_it_during_and_after(self):
        import tarfile
        b = os.path.join(self.d, "src.tgz")
        with tarfile.open(b, "w:gz") as tf:
            data = b"{}"
            ti = tarfile.TarInfo("proof-shard-1/.heart2_cache.json")
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
        with io.open(b, "rb") as fh:
            body = fh.read()

        class _Resp(object):
            def __init__(self):
                self.b = io.BytesIO(body)

            def read(self, n=-1):
                return self.b.read(n)

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        seen, during, where = [], [], {}

        def run(argv, **kw):
            p = argv[argv.index("--import-progress") + 1]
            where["p"] = p
            self.assertLess(argv.index("--import-progress"), argv.index("--import-shards"))
            with io.open(p, "w", encoding="utf-8") as fh:
                json.dump({"done": 5, "of": 10, "etaS": 30, "at": 1700000000000, "phase": "keying"}, fh)
            t0 = time.time()
            while not seen and time.time() - t0 < 5:
                time.sleep(0.01)
            during.extend(seen)
            with io.open(p, "w", encoding="utf-8") as fh:
                json.dump({"done": 10, "of": 10, "etaS": None, "at": 1700000000500, "phase": "imported"}, fh)
            return subprocess.CompletedProcess(argv, 0, "  ✓ REG-2586 IMPORTED 1 shard(s)", "")
        with mock.patch.object(PR, "PROGRESS_POLL_S", 0.02):
            r = PR.import_bundle(SHA, tv_dir=HERE, run=run, urlopen=lambda req, timeout=None: _Resp(),
                                 progress=seen.append)
        self.assertEqual(r["state"], "imported", r)
        self.assertEqual(during[:1], [{"done": 5, "of": 10, "etaS": 30, "at": 1700000000000}],
                         "nothing was read while heart2 ran")
        self.assertEqual(seen[-1], {"done": 10, "of": 10, "etaS": None, "at": 1700000000500}, "the last count was lost")
        self.assertFalse(os.path.abspath(where["p"]).startswith(os.path.abspath(HERE) + os.sep),
                         "the progress file was written into tv/")
        self.assertFalse(os.path.exists(where["p"]), "the progress file outlived the import's scratch dir")

    def test_no_progress_asked_leaves_heart2_argv_as_it_was(self):
        seen = {}

        def run(argv, **kw):
            seen["argv"] = list(argv)
            return subprocess.CompletedProcess(argv, 0, "ok", "")
        with mock.patch.object(PR, "download", lambda *a, **k: ("ok", "fixture")), \
                mock.patch.object(PR, "safe_extract", lambda b, d: ([os.path.join(d, "x")], None)):
            PR.import_bundle(SHA, tv_dir=HERE, run=run)
        self.assertNotIn("--import-progress", seen["argv"])

    def test_the_console_resets_and_publishes_exactly_done_of_etaS(self):
        import control_app as CA
        saved = dict((k, getattr(CA, k)) for k in ("_a_push_is_grading", "_sp_proof_playing_here", "HERE"))
        state = dict(CA._PROOF_RELEASE)
        CA._a_push_is_grading = lambda: False
        CA._sp_proof_playing_here = lambda: False
        CA.HERE = self.d
        snaps = {}

        def best(sha, tv_dir=None, state=None, progress=None, **kw):
            snaps["start"] = dict(CA._PROOF_RELEASE)
            progress({"done": 7, "of": 70, "etaS": 90, "at": 1700000000000})
            snaps["mid"] = dict(CA._PROOF_RELEASE)
            progress({"done": 70, "of": 70, "etaS": None, "at": 1700000009000})
            return {"state": "imported", "sha": sha, "why": "imported", "seconds": 9.0, "at": 1, "imported": [""]}

        def git(argv, **kw):
            if argv[1:3] == ["rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(argv, 0, SHA + "\n", "")
            return subprocess.CompletedProcess(argv, 0, "", "")
        try:
            CA._PROOF_RELEASE.update(running=False, sha=None, state=None, done=3, of=4, etaS=5, progressAt=6)
            with mock.patch.object(PR, "import_best", best):
                CA._proof_release_tick(_thread=lambda f: f(), _git_run=git)
            st, mid, end = snaps["start"], snaps["mid"], dict(CA._PROOF_RELEASE)
        finally:
            for k, v in saved.items():
                setattr(CA, k, v)
            CA._PROOF_RELEASE.clear()
            CA._PROOF_RELEASE.update(state)
        self.assertTrue(st["running"])
        self.assertEqual((st["done"], st["of"], st["etaS"], st["progressAt"]), (None, None, None, None),
                         "a new run started with the last run's count")
        self.assertEqual((mid["done"], mid["of"], mid["etaS"], mid["progressAt"]), (7, 70, 90, 1700000000000))
        self.assertEqual((end["done"], end["of"], end["etaS"]), (70, 70, None))
        self.assertFalse(end["running"])


class TheCliHandsItOn(unittest.TestCase):

    def test_import_progress_reaches_the_import(self):
        got = {}

        def imp(paths, say=print, target=None, progress=None, trust=False):
            got.update(paths=paths, progress=progress)
            return 0
        with mock.patch.object(H, "import_shards", imp):
            self.assertEqual(H.main(["--import-progress", "/x/p.json", "--import-shards", "a.json", "b.json"]), 0)
        self.assertEqual(got, {"paths": ["a.json", "b.json"], "progress": "/x/p.json"})


def tearDownModule():
    shutil.rmtree(_SCRATCH, ignore_errors=True)


RED_PROOF = [
    {"why": "v3882 - the import ETA is the start's average again (Dean: '~7 min' for ~43 min of keys)",
     "file": "tv/heart2.py", "find": "        if el < self.MIN_SPAN_S:\n", "replace": "        if True:\n", "matches": 1},
    {"why": "v3882 - a stalled import keeps promising a time",
     "file": "tv/heart2.py", "find": "        if span <= 0 or moved <= 0:\n            return None                        # no progress",
     "replace": "        if span <= 0:\n            return None                        # no progress", "matches": 1},
    {"why": "v3882 - the console repeats a quiet import's last ETA",
     "file": "tv/control_app.py", "find": "        if age / 1000.0 > IMPORT_QUIET_S:\n", "replace": "        if False:\n", "matches": 1},
    {"why": "v3865 REG-3194 - an ETA is said from the first few keys (no measured rate yet)",
     "file": "tv/heart2.py",
     "find": "        if self.of <= 0 or self.done < max(1, self.of // 100) or self.done >= self.of or el <= 0:\n",
     "replace": "        if self.of <= 0 or self.done < 1 or self.done >= self.of or el <= 0:\n",
     "matches": 1},
    {"why": "v3865 REG-3194 - an ETA is said once every key is done (the write that remains has no rate)",
     "file": "tv/heart2.py",
     "find": "        if self.of <= 0 or self.done < max(1, self.of // 100) or self.done >= self.of or el <= 0:\n",
     "replace": "        if self.of <= 0 or self.done < max(1, self.of // 100) or el <= 0:\n",
     "matches": 1},
    {"why": "v3865 REG-3194 - the progress writer writes any path it is handed, into the checkout too",
     "file": "tv/heart2.py",
     "find": "        if os.path.basename(self.path) != IMPORT_PROGRESS_NAME or _inside(REPO, self.path):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "v3865 REG-3194 - the progress file is written on every key (thousands of writes)",
     "file": "tv/heart2.py",
     "find": "        if not force and self.wrote is not None and now - self.wrote < self.EVERY_S:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "v3865 REG-3194 - the keyer counts the keys the pool already counted",
     "file": "tv/heart2.py",
     "find": "            if st[\"progress\"] is not None and ((), None) not in (st[\"pre\"].get((gate, idx)) or {}):\n",
     "replace": "            if st[\"progress\"] is not None:\n",
     "matches": 1},
    {"why": "v3865 REG-3194 - the pool's answers are never counted as they come",
     "file": "tv/heart2.py",
     "find": "                    if progress is not None:\n                        progress.add(got)\n",
     "replace": "                    if False:\n                        progress.add(got)\n",
     "matches": 1},
    {"why": "v3865 REG-3194 - an ETA of 0 reads as a number (done)",
     "file": "tv/proof_release.py",
     "find": "\"etaS\": _n(body.get(\"etaS\"), 1),",
     "replace": "\"etaS\": _n(body.get(\"etaS\"), 0),",
     "matches": 1},
    {"why": "v3865 REG-3194 - the last count is lost (no read after heart2 ends)",
     "file": "tv/proof_release.py",
     "find": "        self._t.join(10)\n        self._read()\n",
     "replace": "        self._t.join(10)\n",
     "matches": 1},
    {"why": "v3865 REG-3194 - nothing is read while heart2 runs",
     "file": "tv/proof_release.py",
     "find": "        while not self._halt.wait(PROGRESS_POLL_S):\n            self._read()\n",
     "replace": "        while not self._halt.wait(PROGRESS_POLL_S):\n            pass\n",
     "matches": 1},
    {"why": "v3865 REG-3194 - a new run starts with the last run's count",
     "file": "tv/control_app.py",
     "find": "                          done=None, of=None, etaS=None, progressAt=None,\n",
     "replace": "",
     "matches": 1},
    {"why": "v3865 REG-3194 - the console never hands the import a progress callback",
     "file": "tv/control_app.py",
     "find": "                r = _pr.import_best(head, tv_dir=HERE, state=rec, progress=_progress)\n",
     "replace": "                r = _pr.import_best(head, tv_dir=HERE, state=rec)\n",
     "matches": 1},
    {"why": "v3865 REG-3194 - heart2's CLI drops --import-progress",
     "file": "tv/heart2.py",
     "find": "        _irc = import_shards(a.import_shards, progress=a.import_progress, trust=a.trust)\n",
     "replace": "        _irc = import_shards(a.import_shards, trust=a.trust)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
