# -*- coding: utf-8 -*-
"""#2 (REG-3082) - A BLESS RECORDS WHAT IT MEASURED, AND A REFUSED ONE SAYS WHICH TARGETS STOPPED IT.

`render_check.py --bless` writes tv/render_coverage.json, a MERGE: a count lower than its floor is held, a higher one
raised, a new width added, and the file cannot tell them apart afterwards. A refused bless wrote nothing, and said only
"this run did not report every target" - also when it had reported every target and one was red. That is enough on the
machine that ran it; it is not enough for a bless made on another venue (CI's render-bless job, REG-3081), whose run
nobody watched. So the bless now writes .render_bless.json beside the floor: every count it measured, and what it raised,
held and added - or, refused, why, naming the targets. The floor rules are untouched: it still only rises, and a run that
is not full and clean still writes no floor.
Driven through the real _coverage_bless and main(), with the browser and the renders stubbed and the floor in a temp
file. RED_PROOF below.
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

import render_check as R  # noqa: E402


def _run(ok=True, **widths):
    return {"ok": ok, "why": "", "refusals": [] if ok else ["a fixture refusal"],
            "widths": {k: {"found": v, "painted": v} for k, v in widths.items()}}


class _Floor(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "render_coverage.json")
        self._real = (R.COVERAGE, R._chrome_up, R._chrome_down, R.check)
        R.COVERAGE = self.path
        R._chrome_up = lambda *a, **k: True
        R._chrome_down = lambda *a, **k: None
        self.said = []

    def tearDown(self):
        R.COVERAGE, R._chrome_up, R._chrome_down, R.check = self._real
        shutil.rmtree(self.dir, True)

    def floor(self, d):
        with io.open(self.path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"floor": d}))

    def read(self, name):
        with io.open(os.path.join(self.dir, name), encoding="utf-8") as fh:
            return json.load(fh)


class ABlessRecordsWhatItMeasured(_Floor):

    def test_a_clean_bless_records_each_count_and_what_it_did(self):
        self.floor({"console": {"a": 2, "b": 5}})
        rc = R._coverage_bless({"console": _run(a=4, b=3, c=7)}, True, self.said.append)
        self.assertEqual(rc, 0)
        rec = self.read(".render_bless.json")
        self.assertTrue(rec["complete"])
        self.assertEqual(rec["measured"], {"console": {"a": 4, "b": 3, "c": 7}})
        self.assertEqual(rec["raised"], [["console", "a", 2, 4]])
        self.assertEqual(rec["held"], [["console", "b", 5, 3]], "a count under its floor was not recorded as held")
        self.assertEqual(rec["added"], [["console", "c", 7]])
        self.assertNotIn("refused", rec)
        self.assertEqual(self.read("render_coverage.json")["floor"], {"console": {"a": 4, "b": 5, "c": 7}},
                         "PREMISE: the floor rules moved (only rise; a new width joins)")

    def test_a_refused_bless_records_why_and_writes_no_floor(self):
        self.floor({"console": {"a": 2}})
        why = "1 target(s) did not render cleanly (heart)"
        rc = R._coverage_bless({"console": _run(a=9)}, False, self.said.append, why=why)
        self.assertEqual(rc, 2)
        rec = self.read(".render_bless.json")
        self.assertEqual((rec["complete"], rec["refused"]), (False, why))
        self.assertEqual(rec["measured"], {"console": {"a": 9}}, "a refused bless dropped what it measured")
        self.assertEqual(self.read("render_coverage.json")["floor"], {"console": {"a": 2}}, "a refused bless wrote a floor")
        self.assertTrue(any(why in s for s in self.said), "the refusal did not say why: %r" % self.said)

    def test_main_names_the_red_target_that_stopped_the_bless(self):
        self.floor({})
        red = sorted(R.TARGETS)[0]
        R.check = lambda name, spec, *a, **k: _run(ok=(name != red), **{"1120x628": 1})
        out = []
        import builtins
        real = builtins.print
        builtins.print = lambda *a, **k: out.append(" ".join(str(x) for x in a))
        try:
            rc = R.main(["--bless"])
        finally:
            builtins.print = real
        self.assertEqual(rc, 2, "\n".join(out)[-600:])
        rec = self.read(".render_bless.json")
        self.assertIn("did not render cleanly (%s)" % red, rec.get("refused") or "",
                      "the refusal does not name the red target: %r" % rec.get("refused"))
        self.assertEqual(self.read("render_coverage.json")["floor"], {})


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "#2 (REG-3082) - a refused bless writes no record, so CI hands back nothing about its run",
     "file": "tv/render_check.py",
     "find": "            say(\"   why this run is not clean: %s\" % why)\n        _bless_record(rec, say)\n        return 2\n",
     "replace": "            say(\"   why this run is not clean: %s\" % why)\n        return 2\n",
     "matches": 1},
    {"why": "#2 (REG-3082) - a held count is not recorded, so a floor that refused to fall reads like one that rose",
     "file": "tv/render_check.py",
     "find": "    rec.update({\"raised\": sorted(list(x) for x in raised), \"held\": sorted(list(x) for x in held),\n",
     "replace": "    rec.update({\"raised\": sorted(list(x) for x in raised), \"held\": [],\n",
     "matches": 1},
    {"why": "#2 (REG-3082) - main() hands the bless no reason, so a red target reads as a partial run",
     "file": "tv/render_check.py",
     "find": "        return _coverage_bless(results, _full and not bad and not unknown, _say, why=\"; \".join(_bw) or None)\n",
     "replace": "        return _coverage_bless(results, _full and not bad and not unknown, _say)\n",
     "matches": 1},
    {"why": "#2 (REG-3082) - the floor is lowered by a bless again (the record must never loosen the ratchet)",
     "file": "tv/render_check.py",
     "find": "            if isinstance(was, int) and isinstance(v, int) and v < was:\n                held.append((name, k, was, v))\n                continue                      # the floor may only RISE\n",
     "replace": "            if isinstance(was, int) and isinstance(v, int) and v < was:\n                held.append((name, k, was, v))\n",
     "matches": 1},
]
