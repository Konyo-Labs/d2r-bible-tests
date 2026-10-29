# -*- coding: utf-8 -*-
"""#2 (REG-3083) - A FLOOR CI BLESSED RISES HERE ONLY AS FAR AS THIS MACHINE'S PUSH GATE ALSO MEASURED.

CI's render-bless job (REG-3081) renders a cold sandbox; the push gate renders on his Mac and enforces the floor. Taken
whole, a CI count above what the Mac measures turns the next push red ("measured X, was Y") over a node that was never
gone, and his push costs ~25 minutes. `python3 tv/render_bless.py apply <record>` raises each floor to
min(CI's count, the push gate's count from this machine's tv/.render_verdict.json), only where the push gate measured
above the floor too. Both are measurements; none is invented, none is lowered. A CI record that is not complete, and a
verdict that is not a full, clean, unaborted run, are refused whole; a LIVE population (COVERAGE_VOLATILE) is never
raised; --write touches only the floors it raises and keeps everything else in the file.
Python only, fixtures only (a temp floor file; the record and the verdict are handed in). RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
from console_safe import enable as _enable  # noqa: E402
_enable()

import render_bless as B  # noqa: E402

VERDICT = {"full": True, "abortedAt": "", "renderFailures": 0, "coverageMissing": 0, "coverageFloorKnown": True,
           "coverageStale": []}


def _rec(*raised):
    return {"complete": True, "measured": {}, "raised": [list(r) for r in raised], "held": [], "added": []}


def _verdict(*stale, **over):
    v = dict(VERDICT, coverageStale=[list(s) for s in stale])
    v.update(over)
    return v


class ACiBlessNeverOutrunsThePushGate(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "render_coverage.json")
        self.cov = {"floor": {"heart": {"a": 10}, "console": {"a": 2}, "vault": {"b": 3}, "shelf-cards": {"a": 16},
                              "locks": {"a": 5}},
                    "nodes": {"console": {"a": ["x", "y"]}}, "_why": "fixture"}
        with io.open(self.path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(self.cov))
        self.said = []

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def _apply(self, rec, verdict, write=False):
        return B.apply(rec, verdict, write=write, coverage=self.path, say=self.said.append)

    def _floor(self):
        with io.open(self.path, encoding="utf-8") as fh:
            return json.load(fh)

    def _plan(self, rec, verdict):
        got, why = B.plan(rec, verdict, self.cov["floor"])
        self.assertIsNone(why, why)
        return {(d["target"], d["width"]): (d["act"], d["new"]) for d in got}

    def test_a_floor_rises_to_the_lower_of_the_two_measurements(self):
        p = self._plan(_rec(("heart", "a", 10, 15), ("console", "a", 2, 4)),
                       _verdict(("heart", "a", 10, 12), ("console", "a", 2, 4)))
        self.assertEqual(p[("heart", "a")], ("raise", 12), "CI's 15 outran the push gate's 12")
        self.assertEqual(p[("console", "a")], ("raise", 4))

    def test_a_width_the_push_gate_did_not_measure_above_its_floor_holds(self):
        p = self._plan(_rec(("vault", "b", 3, 5)), _verdict())
        self.assertEqual(p[("vault", "b")], ("hold", 3), "a CI count the push gate never saw raised the floor")

    def test_a_live_population_is_never_raised(self):
        p = self._plan(_rec(("shelf-cards", "a", 16, 30)), _verdict(("shelf-cards", "a", 16, 30)))
        self.assertEqual(p[("shelf-cards", "a")][0], "hold")

    def test_nothing_is_ever_lowered(self):
        p = self._plan(_rec(("locks", "a", 4, 6)), _verdict(("locks", "a", 2, 3)))
        self.assertEqual(p[("locks", "a")], ("hold", 5), "a raise below this tree's floor lowered it")

    def test_an_incomplete_ci_record_is_refused_whole(self):
        rec = dict(_rec(("console", "a", 2, 4)), complete=False, refused="1 target(s) did not render cleanly (heart)")
        self.assertEqual(self._apply(rec, _verdict(("console", "a", 2, 4)), write=True), 2)
        self.assertEqual(self._floor(), self.cov, "a refused apply changed the floor file")
        self.assertTrue(any("not complete" in s for s in self.said), self.said)

    def test_a_verdict_that_cannot_speak_for_the_push_gate_is_refused_whole(self):
        rec = _rec(("console", "a", 2, 4))
        for bad in (dict(full=False), dict(abortedAt="heart"), dict(renderFailures=1), dict(coverageMissing=2),
                    dict(coverageFloorKnown=False)):
            self.said = []
            self.assertEqual(self._apply(rec, _verdict(("console", "a", 2, 4), **bad), write=True), 2, bad)
            self.assertEqual(self._floor(), self.cov, bad)
        self.assertEqual(self._apply(rec, None, write=True), 2, "no verdict at all was taken as a measurement")

    def test_write_raises_only_what_it_may_and_keeps_the_rest_of_the_file(self):
        rc = self._apply(_rec(("heart", "a", 10, 15), ("vault", "b", 3, 5)), _verdict(("heart", "a", 10, 12)), write=True)
        self.assertEqual(rc, 0)
        got = self._floor()
        want = json.loads(json.dumps(self.cov))
        want["floor"]["heart"]["a"] = 12
        self.assertEqual(got, want, "--write changed more than the floors it raised")

    def test_the_report_says_a_refusal_and_lists_a_bless(self):
        self.assertIn("**REFUSED** - 1 target(s) did not render cleanly (heart).",
                      B.report({"complete": False, "refused": "1 target(s) did not render cleanly (heart)", "measured": {}}))
        lines = B.report(dict(_rec(("console", "a", 2, 4)), measured={"console": {"a": 4}}))
        self.assertIn("| console | a | 2 | 4 |", lines)
        self.assertTrue(any(l.startswith("**UNKNOWN**") for l in B.report(None)))


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "#2 (REG-3083) - a CI count above the push gate's goes in whole, and the next push refuses",
     "file": "tv/render_bless.py",
     "find": "            new = min(ci, d[\"gate\"])\n",
     "replace": "            new = ci\n",
     "matches": 1},
    {"why": "#2 (REG-3083) - a width the push gate never measured above its floor is raised on CI's word alone",
     "file": "tv/render_bless.py",
     "find": "        elif d[\"gate\"] is None:\n            d.update(act=\"hold\", why=\"the push gate's last run did not measure it above its floor\")\n",
     "replace": "        elif d[\"gate\"] is None:\n            d.update(act=\"raise\", new=ci, why=\"CI alone\")\n",
     "matches": 1},
    {"why": "#2 (REG-3083) - a LIVE population's floor is raised as if it were a law",
     "file": "tv/render_bless.py",
     "find": "        if n in vol:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "#2 (REG-3083) - a verdict from a partial, aborted or failing run speaks for the push gate",
     "file": "tv/render_bless.py",
     "find": "    if bad:\n        return None, \"this machine's last render run cannot speak for its push gate: \" + \"; \".join(bad)\n",
     "replace": "",
     "matches": 1},
    {"why": "#2 (REG-3083) - a raise below this tree's floor lowers it",
     "file": "tv/render_bless.py",
     "find": "            if new <= cur:\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "#2 (REG-3083) - an incomplete CI record is applied",
     "file": "tv/render_bless.py",
     "find": "    if not isinstance(rec, dict) or rec.get(\"complete\") is not True:\n        return None, (",
     "replace": "    if not isinstance(rec, dict):\n        return None, (",
     "matches": 1},
]
