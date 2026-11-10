# -*- coding: utf-8 -*-
"""REG-3642 - EVERY PRESHIP LESSON NAMES A CHECK THAT EXISTS AND RUNS.

Attempts 6 and 7 each cost a full CI round because a cheap local check was missing or
out of date. The ledger tv/preship_lessons.json records those refusals and the check
that now catches them. This law refuses a lesson whose `check` is not in preship.catalog()
or is not actually invoked when preship runs. Adding a lesson is one entry; this law
keeps the entry honest.
"""
import json
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import preship as P  # noqa: E402


class TheLawHolds(unittest.TestCase):
    def test_every_lesson_names_a_catalog_check(self):
        rows = P.load_lessons()
        cat = P.catalog()
        self.assertGreaterEqual(len(rows), 3, "the starting set is attempts 6, 7 and 8")
        for row in rows:
            self.assertIn("check", row, row)
            self.assertIn(row["check"], cat,
                          "%s names %r, which is not a check this file runs" % (row.get("id"), row["check"]))

    def test_the_starting_lessons_are_the_three_bundle_attempts(self):
        by = {r["id"]: r["check"] for r in P.load_lessons()}
        self.assertEqual(by["bundle-attempt-6"], "render_check")
        self.assertEqual(by["bundle-attempt-7"], "test_a_chronicle_title_never_shaves_its_count")
        self.assertEqual(by["bundle-attempt-8"], "mac_ready")

    def test_preship_invokes_every_lesson_check(self):
        called = []

        def wrap(name):
            def _fn(root, timeout=None, **kw):
                called.append(name)
                return 0, "ok"
            return _fn

        patches = {n: dict(spec, run=wrap(n)) for n, spec in P.catalog().items()}
        with mock.patch.object(P, "catalog", return_value=patches):
            P.run_checks(list(P.BOX_ORDER) + list(P.READY_ORDER), P.REPO, parallel=False, fail_fast=False)
        for row in P.load_lessons():
            self.assertIn(row["check"], called, "%s was not invoked" % row["check"])


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            blob = open(os.path.join(P.REPO, p["file"]), encoding="utf-8").read()
            self.assertEqual(blob.count(p["find"]), p["matches"], p["why"])

    def test_each_proof_turns_a_check_red(self):
        src = open(P.lessons_path(), encoding="utf-8").read()
        for p in RED_PROOF:
            after = src.replace(p["find"], p["replace"])
            rows = (json.loads(after) or {}).get("lessons") or []
            cat = set(P.catalog())
            red = any((not r.get("check")) or r.get("check") not in cat for r in rows if isinstance(r, dict))
            self.assertTrue(red, "this proof would not turn the law red: " + p["why"])


RED_PROOF = [
    {"why": "REG-3642 - a lesson names a check that does not exist",
     "file": "tv/preship_lessons.json",
     "find": '"check": "mac_ready"',
     "replace": '"check": "not-a-real-check"',
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
