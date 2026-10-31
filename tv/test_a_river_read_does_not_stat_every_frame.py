# -*- coding: utf-8 -*-
"""v3849 H1 — A RIVER READ DOES NOT STAT EVERY FRAME.

MEASURED on a synthetic shelf (no live footage): plan() off the console stat'd each frame twice
(the index, then each reel's size), and a console whose shelf was moving did it again on every
plan(). /api/river calls reel_census, which called plan(). That cost follows FRAME count. Dean's
river was ~36 s at 170 reels; the ALT's was 3.8 s at 655. A stamp log of 4,000 rows was 0.02 s.

A fingerprint asks which folders exist, so it does not stat a file. One plan shares the listing it
just took, so a moving reel is stat'd once. While the shelf is moving, the census keeps the last
plan instead of walking the frames on the request.

The budget is the request itself, under 10 s, on a fat shelf and a wide one. RED_PROOF below.
"""
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

_HIST = tempfile.mkdtemp(prefix="river_frames_")
os.environ["TV_HIST"] = _HIST

import frame_ref as FR  # noqa: E402
import reel_retention as RR  # noqa: E402

RED_PROOF = [
    {
        "why": "the census recomputes a plan on the request while the shelf is moving, so every river read stats the frames again",
        "file": "control_app.py",
        "find": "        if isinstance(_held, dict) and _held.get(\"moving\") is True:\n            _p = _held\n",
        "replace": "        if False:\n            _p = _held\n",
        "matches": 1,
    },
    {
        "why": "the fingerprint stats every frame again to learn which folders exist",
        "file": "reel_retention.py",
        "find": "        sub = _fr.folders(d)\n",
        "replace": "        sub = _fr.listing(d)\n",
        "matches": 1,
    },
    {
        "why": "one plan stats every frame twice: the index walk and then each reel's size",
        "file": "frame_ref.py",
        "find": "    if isinstance(memo, dict) and folder in memo:\n        return memo[folder]\n",
        "replace": "    if False:\n        return memo[folder]\n",
        "matches": 1,
    },
]

_ORIG_STAT = os.DirEntry.stat
_STATS = {"n": 0}


def _counted_stat(self, *a, **k):
    _STATS["n"] += 1
    return _ORIG_STAT(self, *a, **k)


def _reel(i):
    return "reel_s_%d_%d" % (1500000000000 + i * 1000, 1000 + i)


def _build(n_reels, n_files):
    for name in os.listdir(_HIST):
        p = os.path.join(_HIST, name)
        if os.path.isdir(p):
            shutil.rmtree(p)
        else:
            os.remove(p)
    for i in range(n_reels):
        reel = _reel(i)
        d = os.path.join(_HIST, reel)
        os.makedirs(os.path.join(d, "nest"))
        for j in range(n_files):
            with open(os.path.join(d, "f_%d.jpg" % (1500000000000 + j)), "wb") as fh:
                fh.write(b"x")
        with open(os.path.join(d, "index.json"), "w", encoding="utf-8") as fh:
            fh.write("{}")
    with open(os.path.join(_HIST, "river_stamp.jsonl"), "w", encoding="utf-8") as fh:
        for i in range(n_reels):
            fh.write(json.dumps({
                "reel": _reel(i), "station": "CAPTURE", "at": 1500000000000 + i,
                "by": "fixture", "byKind": "observer", "why": "fixture",
            }) + "\n")
    return n_reels * (n_files + 1)


def _touch_future(path):
    ahead = time.time() + 3600
    os.utime(path, (ahead, ahead))


def _files(root):
    n = 0
    for _dir, _dirs, names in os.walk(root):
        n += len(names)
    return n


class ARiverReadDoesNotStatEveryFrame(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.DirEntry.stat = _counted_stat
        cls._racy = FR.RACY_S
        FR.RACY_S = 0
        cls._console = FR.on_console_path()

    @classmethod
    def tearDownClass(cls):
        os.DirEntry.stat = _ORIG_STAT
        FR.RACY_S = cls._racy
        FR.mark_console_path(cls._console)
        FR._forget_listings()
        RR._forget_plans()
        shutil.rmtree(_HIST, ignore_errors=True)

    def test_the_proofs_each_match_once(self):
        for pr in RED_PROOF:
            path = os.path.join(HERE, pr["file"])
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertEqual(text.count(pr["find"]), pr["matches"], pr["why"])
            self.assertNotEqual(pr["find"], pr["replace"])

    def test_one_plan_stats_each_frame_once_and_the_river_does_not(self):
        import control_app as ca
        import river_lanes as RL
        import river_stamp as RS

        fat = _build(6, 40)
        self.assertGreater(fat, 200)
        FR.mark_console_path(False)
        RR._forget_plans()
        FR._forget_listings()
        RR.plan(hist_dir=_HIST)  # warm the fixture-set scan; not the budget
        RR._forget_plans()
        FR._forget_listings()
        on_disk = _files(_HIST)
        self.assertGreater(on_disk, fat)
        _STATS["n"] = 0
        t0 = time.perf_counter()
        planned = RR.plan(hist_dir=_HIST)
        plan_s = time.perf_counter() - t0
        self.assertTrue(planned.get("ok"), planned.get("why"))
        self.assertLess(plan_s, 10, "one plan took %.2fs" % plan_s)
        self.assertEqual(
            _STATS["n"], on_disk,
            "one plan stat'd %d files on a shelf of %d — a second walk over the same frames is back"
            % (_STATS["n"], on_disk))

        FR.mark_console_path(True)
        for n_reels, n_files, fatness in ((6, 40, fat), (30, 2, None)):
            files = _build(n_reels, n_files)
            if fatness is not None:
                self.assertEqual(files, fatness)
            else:
                self.assertLess(files, fat, "the wide shelf is not the smaller frame count")
            RR._forget_plans()
            FR._forget_listings()
            seeded = RR.plan(hist_dir=_HIST)
            self.assertTrue(seeded.get("ok"), seeded.get("why"))
            self.assertEqual(seeded.get("onDisk"), n_reels)
            FR._forget_listings()
            _touch_future(os.path.join(_HIST, _reel(0), "nest"))
            finished = {"ok": True, "lanes": [], "reconciles": True, "shelf": n_reels,
                        "hidden": 0, "closed": 0, "lifetime": n_reels}
            RL.lanes = lambda hide=None: dict(finished)
            RL._LAST[()] = {"at": time.time(), "out": dict(finished)}
            real_rows = RS.rows

            def rows(path=None, _real=real_rows):
                return _real(os.path.join(_HIST, "river_stamp.jsonl") if path is None else path)

            RS.rows = rows
            got = {}
            h = ca.Handler.__new__(ca.Handler)
            h.path = "/api/river"
            h._json = lambda code, obj: got.update(code=code, obj=obj)
            _STATS["n"] = 0
            t1 = time.perf_counter()
            try:
                h.do_GET()
            finally:
                RS.rows = real_rows
                RL._LAST.pop((), None)
                RL._REFRESH_ON.discard(())
            elapsed = time.perf_counter() - t1
            obj = got.get("obj") or {}
            self.assertLess(elapsed, 10, "the river read took %.2fs on %d frames" % (elapsed, files))
            self.assertFalse(obj.get("computing"), obj.get("why"))
            pop = obj.get("population") or {}
            self.assertTrue(pop.get("ok"), pop.get("why"))
            self.assertEqual(pop.get("onDisk"), n_reels, pop.get("why"))
            self.assertEqual(
                _STATS["n"], 0,
                "the river read stat'd %d frames on a shelf of %d frames and %d reels"
                % (_STATS["n"], files, n_reels))


if __name__ == "__main__":
    unittest.main(verbosity=2)
