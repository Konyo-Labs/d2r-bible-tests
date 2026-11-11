# -*- coding: utf-8 -*-
"""REG-3676 (card #200 guard 9c) - A REHEARSAL NEVER RACES ITS OWN TREE LOCK.

MEASURED 2026-11-11 01:47-02:30, the box rehearsal's first real use on v3895: failed_shards and changed_tests both run
tv/run_gates.py, which takes the tree's flock; started together they collided and the second was refused by the first's
lock - the rehearsal stopped the ship on a red about ITSELF. A check marked locks_tree now runs in ONE lane, one after the
other, while every other check still runs beside them.

DRIVEN through preship.run_checks with stub checks that record when they ran (no run_gates, no tree touched); the BASELINE
case shows two free checks DO overlap, so the case can tell the two shapes apart. RED_PROOF below.
"""
import os
import sys
import threading
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import preship as P  # noqa: E402


class ARehearsalNeverRacesItsOwnTreeLock(unittest.TestCase):
    def _run(self, names, cat):
        spans, lock = {}, threading.Lock()

        def fake_run_one(name, root, **kw):
            t0 = time.time()
            time.sleep(0.3)
            with lock:
                spans[name] = (t0, time.time())
            return {"name": name, "code": 0, "ms": 300, "say": "fixture"}

        with mock.patch.object(P, "catalog", lambda: cat), mock.patch.object(P, "run_one", fake_run_one):
            code, rows = P.run_checks(names, "/nonexistent-root", parallel=True, fail_fast=True, include_lessons=False)
        self.assertEqual(code, 0, rows)
        self.assertEqual(sorted(r["name"] for r in rows), sorted(names), "a check did not run, or ran twice")
        return spans

    @staticmethod
    def _overlap(a, b):
        return a[0] < b[1] and b[0] < a[1]

    def test_two_checks_that_run_run_gates_never_overlap(self):
        cat = {"free_a": {"cheap": False}, "free_b": {"cheap": False},
               "tree_a": {"cheap": False, "locks_tree": True}, "tree_b": {"cheap": False, "locks_tree": True}}
        spans = self._run(["free_a", "free_b", "tree_a", "tree_b"], cat)
        self.assertTrue(self._overlap(spans["free_a"], spans["free_b"]),
                        "PREMISE: two free checks did not run side by side - the case cannot tell a lane from a pool")
        self.assertFalse(self._overlap(spans["tree_a"], spans["tree_b"]),
                         "two checks that each take the tree lock ran together - the second is refused by the first")

    def test_the_real_catalog_marks_both_run_gates_checks(self):
        cat = P.catalog()
        for name in ("changed_tests", "failed_shards", "render_check"):   # render_check writes tv/.render_shots (guard 9d)
            with self.subTest(check=name):
                self.assertTrue((cat.get(name) or {}).get("locks_tree"),
                                "%s runs tv/run_gates.py or writes the tree, and is not marked locks_tree" % name)



class ARedTheHookCannotProduceNeverStopsAShip(unittest.TestCase):
    """REG-3682 - the rehearsal runs side by side, the hook one at a time: a red check is asked again ALONE before it stops a
    ship (v3895 attempt 3's rehearsal stopped it on two reds the same checks did not have run one at a time)"""

    def _rehearse(self, first, alone):
        asked = []

        def fake_run_one(name, root, **kw):
            asked.append(name)
            return {"name": name, "code": alone, "ms": 1, "say": "alone"}

        with mock.patch.object(P, "run_checks", lambda *a, **k: first), mock.patch.object(P, "run_one", fake_run_one):
            code, rows = P.mac_rehearse("/nonexistent-root")
        return code, rows, asked

    def test_a_red_only_beside_the_others_is_green_and_says_so(self):
        code, rows, asked = self._rehearse((1, [{"name": "x", "code": 1, "ms": 1, "say": "a tree lock held"},
                                                {"name": "y", "code": 0, "ms": 1, "say": "ok"}]), alone=0)
        self.assertEqual((code, asked), (0, ["x"]), rows)
        self.assertIn("green alone (red beside the others: a tree lock held)", rows[0]["say"])

    def test_a_red_that_holds_alone_stays_red(self):
        code, rows, asked = self._rehearse((1, [{"name": "x", "code": 1, "ms": 1, "say": "really red"}]), alone=1)
        self.assertEqual((code, asked), (1, ["x"]), "a real red was re-asked into a pass")

    def test_an_unknown_is_never_re_asked(self):
        code, rows, asked = self._rehearse((2, [{"name": "x", "code": 2, "ms": 1, "say": "no Chrome"}]), alone=0)
        self.assertEqual((code, asked), (2, []), "an UNKNOWN was re-asked into a pass")


RED_PROOF = [
    {"why": "REG-3676 - the run_gates checks share the pool again and race each other's tree lock",
     "file": "tv/preship.py",
     "find": "    tree = [n for n in rest if (cat.get(n) or {}).get(\"locks_tree\")]\n",
     "replace": "    tree = []\n",
     "matches": 1},
    {"why": "REG-3676 - changed_tests is no longer marked as taking the tree lock",
     "file": "tv/preship.py",
     "find": "        (\"changed_tests\",  {\"run\": check_changed, \"cheap\": False, \"timeout\": CHANGED_TIMEOUT_S, \"locks_tree\": True,\n",
     "replace": "        (\"changed_tests\",  {\"run\": check_changed, \"cheap\": False, \"timeout\": CHANGED_TIMEOUT_S,\n",
     "matches": 1},
    {"why": "REG-3676 (guard 9d) - render_check rewrites tv/.render_shots beside the laws that watch the tree again",
     "file": "tv/preship.py",
     "find": "        (\"render_check\",   {\"run\": check_render, \"cheap\": False, \"timeout\": RENDER_TIMEOUT_S, \"locks_tree\": True,\n",
     "replace": "        (\"render_check\",   {\"run\": check_render, \"cheap\": False, \"timeout\": RENDER_TIMEOUT_S,\n",
     "matches": 1},
    {"why": "REG-3682 - a red the parallel rehearsal produced stops the ship again, though the hook runs it alone and green",
     "file": "tv/preship.py",
     "find": "    if code != 1:\n        return code, rows\n    out, worst = [], 0\n",
     "replace": "    if True:\n        return code, rows\n    out, worst = [], 0\n",
     "matches": 1}
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
