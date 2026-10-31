# -*- coding: utf-8 -*-
"""v3848 (Dean /api/river 23-38 s under load) - OVERLAPPING RIVER ASKS SHARE ONE WALK.

Every overlapping /api/river started its own reel_router walk on a busy GIL. Now asks that overlap a walk with the
same hide set wait for it and take its answer; an ask after it ends walks again (nothing outlives the walk), an error
reaches every waiter, and the route calls the shared door. No timeout was raised.
"""
import os, sys, threading, time, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import river_lanes as RL


class OverlappingRiverAsksShareOneWalk(unittest.TestCase):
    def setUp(self):
        self._orig = RL.lanes
        self.calls = 0

        def slow(rep=None, hide=None):
            self.calls += 1
            n = self.calls
            time.sleep(0.4)
            if getattr(self, "boom", False):
                raise RuntimeError("router down")
            return {"ok": True, "walk": n}
        RL.lanes = slow

    def tearDown(self):
        RL.lanes = self._orig

    def _ask(self, n, hide=None):
        out = [None] * n

        def one(i):
            try:
                out[i] = RL.lanes_shared(hide=hide)
            except Exception as e:
                out[i] = e
        ts = [threading.Thread(target=one, args=(i,)) for i in range(n)]
        for t in ts:
            t.start()
            time.sleep(0.02)
        for t in ts:
            t.join()
        return out

    def test_five_overlapping_asks_walk_once(self):
        out = self._ask(5)
        self.assertEqual(self.calls, 1)
        self.assertTrue(all(o == {"ok": True, "walk": 1} for o in out), out)

    def test_an_ask_after_the_walk_walks_again(self):
        RL.lanes_shared()
        RL.lanes_shared()
        self.assertEqual(self.calls, 2, "an answer outlived its walk")

    def test_a_different_hide_set_is_its_own_walk(self):
        out = [None, None]
        a = threading.Thread(target=lambda: out.__setitem__(0, RL.lanes_shared(hide={"r1"})))
        b = threading.Thread(target=lambda: out.__setitem__(1, RL.lanes_shared(hide={"r2"})))
        a.start(); time.sleep(0.02); b.start(); a.join(); b.join()
        self.assertEqual(self.calls, 2)

    def test_an_error_reaches_every_waiter(self):
        self.boom = True
        out = self._ask(3)
        self.assertTrue(all(isinstance(o, RuntimeError) for o in out), out)
        self.assertEqual(self.calls, 1)

    def test_the_route_asks_the_shared_door(self):
        src = open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        lanes = open(os.path.join(HERE, "river_lanes.py"), encoding="utf-8").read()
        self.assertIn("_RL.lanes_last(hide=_hide)", src)
        self.assertNotIn("_RL.lanes(hide=_hide)", src)
        self.assertIn("def lanes_shared(", lanes)


RED_PROOF = [
    {"why": "v3848 - every overlapping ask starts its own walk again",
     "file": "river_lanes.py",
     "find": "        mine = cur is None\n",
     "replace": "        mine = True\n        cur = None\n",
     "matches": 1},
    {"why": "v3848 - an answer is kept past its walk",
     "file": "river_lanes.py",
     "find": "            _SHARED.pop(key, None)\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "v3848 - the route goes back to its own walk",
     "file": "control_app.py",
     "find": "_lr = _RL.lanes_last(hide=_hide)",
     "replace": "_lr = _RL.lanes(hide=_hide)",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
