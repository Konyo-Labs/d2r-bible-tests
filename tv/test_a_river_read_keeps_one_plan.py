# -*- coding: utf-8 -*-
"""v3849 - A RIVER READ KEEPS ONE PLAN, AND A ROUTED REEL REPORTS ITS ROUTE.

plan() never memoized while an input was moving, and /api/river asked it twice: the hidden set,
then the story inside the walk. A reader now takes the last finished plan and does not start a
wave. The river ask takes the last finished walk and does not wait for one. A ROUTED reel carries
the route that closed it out (from, by, why); an empty from stays unknown.
Pure Python. No server. RED_PROOF below.
"""
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

import reel_retention as RR  # noqa: E402
import river_lanes as RL  # noqa: E402


class ARiverReadKeepsOnePlan(unittest.TestCase):

    def setUp(self):
        self._dir = tempfile.mkdtemp(prefix="river-plan-")
        old = time.time() - 10
        os.utime(self._dir, (old, old))
        RR._forget_plans()
        self._lanes = RL.lanes
        RL._LAST.clear()
        RL._REFRESH_ON.clear()
        RL._SHARED.clear()

    def tearDown(self):
        for _ in range(40):
            if not RL._REFRESH_ON:
                break
            time.sleep(0.05)
        RL.lanes = self._lanes
        RL._LAST.clear()
        RL._REFRESH_ON.clear()
        RL._SHARED.clear()
        RR._forget_plans()
        shutil.rmtree(self._dir, ignore_errors=True)

    def test_no_finished_plan_is_unknown_and_starts_no_wave(self):
        runs, waves = RR.PLAN_STATS["runs"], RR.PLAN_STATS["waves"]
        self.assertIsNone(RR.plan_for_reader(hist_dir=self._dir))
        self.assertEqual((RR.PLAN_STATS["runs"], RR.PLAN_STATS["waves"]), (runs, waves))
        import control_app as ca
        ids, why = ca.shelf_hidden_reels(hist_dir=self._dir)
        self.assertIsNone(ids)
        self.assertIn("UNKNOWN", why or "")
        self.assertEqual((RR.PLAN_STATS["runs"], RR.PLAN_STATS["waves"]), (runs, waves))

    def test_a_reader_takes_the_last_plan_and_does_not_compute(self):
        """The still/moving bit is the fingerprint's answer. This worktree's own ledgers are
        written while the law runs, so the fingerprint is stubbed: a still input, then a moving
        one. The remembered plan and the wave counters stay the real ones."""
        built = RR.plan(hist_dir=self._dir)
        self.assertTrue(built.get("ok"), built)
        runs, waves = RR.PLAN_STATS["runs"], RR.PLAN_STATS["waves"]
        state = {"moving": False}
        real_fp = RR.plan_fingerprint

        def _fp(*a, **k):
            if state["moving"]:
                raise RR._Moving(self._dir)
            return ("still", "still")

        RR.plan_fingerprint = _fp
        real_plan = RR.plan

        def _no_second_plan(*a, **k):
            raise AssertionError("story computed a second plan")

        try:
            got = RR.plan_for_reader(hist_dir=self._dir)
            self.assertTrue(got.get("ok"), got)
            self.assertIs(got.get("moving"), False, got.get("moving"))
            self.assertIsInstance(got.get("asOf"), float)
            state["moving"] = True
            moved = RR.plan_for_reader(hist_dir=self._dir)
            self.assertIs(moved.get("moving"), True, moved.get("moving"))
            self.assertEqual(moved.get("asOf"), got.get("asOf"))
            self.assertEqual((RR.PLAN_STATS["runs"], RR.PLAN_STATS["waves"]), (runs, waves),
                             "a reader started a plan while the last one was already finished")
            import reel_story as RS
            RR.plan = _no_second_plan
            told = RS.story(hist_dir=self._dir)
            self.assertTrue(told.get("ok"), told)
        finally:
            RR.plan_fingerprint = real_fp
            RR.plan = real_plan

    def test_the_river_ask_does_not_wait_for_its_walk(self):
        calls = {"n": 0}

        def slow(hide=None):
            time.sleep(0.35)
            calls["n"] += 1
            return {"ok": True, "walk": calls["n"], "lanes": []}

        RL.lanes = slow
        t0 = time.time()
        self.assertIsNone(RL.lanes_last(hide={"a"}))
        self.assertLess(time.time() - t0, 0.2, "the ask waited for the walk")
        got = None
        for _ in range(30):
            time.sleep(0.05)
            got = RL.lanes_last(hide={"a"})
            if got is not None:
                break
        self.assertIsNotNone(got)
        self.assertEqual(got.get("ok"), True)
        self.assertIsInstance(got.get("ageMs"), int)
        self.assertEqual(calls["n"], 1)
        RL.lanes_last(hide={"a"})
        time.sleep(0.2)
        self.assertEqual(calls["n"], 1, "a fresh ask started a second walk")

    def test_a_failed_walk_is_not_kept(self):
        def boom(hide=None):
            raise RuntimeError("router down")

        RL.lanes = boom
        self.assertIsNone(RL.lanes_last())
        for _ in range(30):
            if not RL._REFRESH_ON:
                break
            time.sleep(0.05)
        self.assertIsNone(RL.lanes_last())
        self.assertEqual(RL._LAST, {})

    def test_a_routed_reel_reports_its_route(self):
        import reel_router as router
        import control_app as ca
        ev = {
            "reel_routed": {"sealed": True, "names": 1, "surveyed": True, "worthReading": True},
            "reel_open": {"sealed": False, "names": 0, "surveyed": False, "worthReading": None},
        }
        stamp = {"from": "CAPTURE", "by": "kai", "byKind": "actor", "station": "ROUTED",
                 "why": "the contract was satisfied"}
        blank = {"from": "", "by": "kai", "byKind": "actor", "station": "ROUTED", "why": "closed"}
        orig = (router._evidence, router._routed_by_a_lane, router._captured_ms)
        try:
            router._evidence = lambda hist=None: (ev, "")
            router._captured_ms = lambda reel, hist=None: (1, "fixture")
            router._routed_by_a_lane = lambda path=None: ({"reel_routed": dict(stamp)}, "")
            rep = router.route(hist=self._dir)
            rows = {r["reel"]: r for r in rep["reels"]}
            self.assertEqual(rows["reel_routed"]["station"], "ROUTED")
            self.assertEqual(rows["reel_routed"]["route"],
                             {"from": "CAPTURE", "by": "kai", "why": rows["reel_routed"]["why"]})
            self.assertNotIn("route", rows["reel_open"])
            router._routed_by_a_lane = lambda path=None: ({"reel_routed": dict(blank)}, "")
            again = {r["reel"]: r for r in router.route(hist=self._dir)["reels"]}
            self.assertIsNone(again["reel_routed"]["route"]["from"])
        finally:
            router._evidence, router._routed_by_a_lane, router._captured_ms = orig
        joined = ca.river_routed_reports([
            {"reel": "reel_routed", "station": "ROUTED", "route": {"from": "CAPTURE", "by": "kai", "why": "x"}},
            {"reel": "reel_open", "station": "INTAKE"},
            {"reel": "reel_bad", "station": "ROUTED", "route": "nope"},
        ])
        self.assertEqual([j["reel"] for j in joined], ["reel_routed", "reel_bad"])
        self.assertEqual(joined[0]["route"]["by"], "kai")
        self.assertIsNone(joined[1]["route"])
        src = open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.assertIn('"routed": river_routed_reports(l.get("reels"))', src)
        self.assertIn("_p = _RR.plan_for_reader(hist_dir=hist_dir)", src)


RED_PROOF = [
    {"why": "a reader with no finished plan computes one and waits out a wave",
     "file": "reel_retention.py",
     "find": "    if not isinstance(held, dict):\n        return None\n",
     "replace": "    if not isinstance(held, dict):\n        return plan(hist_dir, free_mb, keep_recent)\n",
     "matches": 1},
    {"why": "the river ask waits for the walk on the caller",
     "file": "river_lanes.py",
     "find": "        _th.Thread(target=_lanes_refresh, args=(key, hide_snap), daemon=True).start()\n",
     "replace": "        _lanes_refresh(key, hide_snap)\n",
     "matches": 1},
    {"why": "a ROUTED reel no longer reports the route that closed it out",
     "file": "reel_router.py",
     "find": '                row["route"] = {"from": _r.get("from") or None, "by": _r.get("by") or None, "why": swhy}\n',
     "replace": '                row["route"] = None\n',
     "matches": 1},
    {"why": "the lane payload drops the routed reels, so the route never reaches the river",
     "file": "control_app.py",
     "find": '"routed": river_routed_reports(l.get("reels")),\n',
     "replace": '"routed": [],\n',
     "matches": 1},
    {"why": "the hidden set asks plan() again and starts a wave while he films",
     "file": "control_app.py",
     "find": "        _p = _RR.plan_for_reader(hist_dir=hist_dir)\n",
     "replace": "        _p = _RR.plan(hist_dir=hist_dir)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
