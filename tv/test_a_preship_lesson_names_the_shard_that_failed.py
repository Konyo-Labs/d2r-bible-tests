# -*- coding: utf-8 -*-
"""REG-3650 - A PRESHIP LESSON THAT CAME FROM A SHARD FAILURE NAMES THAT SHARD.

Attempt 9's red was agent-suite (2). The lessons ledger now records the
shard's identity so a repeat is caught before the next ci/ push (the
failed_shards check runs those tests in the box rehearsal). A lesson
without a shard field for that class, or whose shard is missing from the
history, is a hole this law refuses.
"""
import json
import os
import sys
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import preship as P  # noqa: E402
import shard_watch as SHW  # noqa: E402


class TheLawHolds(unittest.TestCase):
    def test_attempt_9_names_agent_suite_2(self):
        rows = {r["id"]: r for r in P.load_lessons()}
        self.assertIn("bundle-attempt-9", rows)
        row = rows["bundle-attempt-9"]
        self.assertEqual(row["check"], "failed_shards")
        self.assertEqual(row["shard"], "agent-suite (2)")
        self.assertIn("test_the_planner_spinner_stays_under_the_cursor", row.get("reason", ""))

    def test_the_named_shard_is_in_the_history(self):
        row = next(r for r in P.load_lessons() if r["id"] == "bundle-attempt-9")
        names = [j.get("name") for j in SHW.owed_shards()]
        self.assertIn(row["shard"], names)

    def test_remember_refusal_stores_the_shard(self):
        root = tempfile.mkdtemp(prefix="lesson-shard-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, "tv"), exist_ok=True)
        with open(os.path.join(root, "tv", P.LESSONS_NAME), "w", encoding="utf-8") as fh:
            json.dump({"lessons": []}, fh)
        row = P.remember_refusal("shard agent-suite (2) went red: sockets",
                                 "failed_shards", root=root, cls="shard-failure",
                                 shard="agent-suite (2)")
        self.assertIsNotNone(row)
        self.assertEqual(row["shard"], "agent-suite (2)")
        loaded = P.load_lessons(root)
        self.assertEqual(loaded[0]["shard"], "agent-suite (2)")


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            blob = open(os.path.join(P.REPO, p["file"]), encoding="utf-8").read()
            self.assertEqual(blob.count(p["find"]), p["matches"], p["why"])

    def test_each_proof_turns_the_law_red(self):
        src = open(P.lessons_path(), encoding="utf-8").read()
        for p in RED_PROOF:
            after = src.replace(p["find"], p["replace"])
            rows = (json.loads(after) or {}).get("lessons") or []
            row = next((r for r in rows if r.get("id") == "bundle-attempt-9"), {})
            self.assertNotEqual(row.get("shard"), "agent-suite (2)", p["why"])


RED_PROOF = [
    {"why": "REG-3650 - attempt 9 no longer names the shard that failed",
     "file": "tv/preship_lessons.json",
     "find": '"check": "failed_shards",\n      "class": "shard-failure",\n      "shard": "agent-suite (2)"',
     "replace": '"check": "failed_shards",\n      "class": "shard-failure",\n      "shard": ""',
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
