# -*- coding: utf-8 -*-
"""v3848 (Elad 10:20) - EVERY VERSION'S HISTORY LISTS ALL ITS ITEMS.

His VERSION HISTORY showed 3 lines for v3847, which shipped ~15 things. From v3846 on, a version's CHANGELOG
entry has at least one line per feature/fix commit of that version: a commit whose subject starts "vNNNN: "
(CI/gate-fix commits are "vNNNN CI ..." and do not count; the ship-title commit "vNNNN: Two Words" does not count).
A version with no such commit in reach of the clone (shallow CI) is reported, never silently passed as checked.
"""
import json, os, re, subprocess, unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
import sys
sys.path.insert(0, HERE)
from console_safe import enable; enable()  # a subject can carry ✕; a cp1255 console must still be able to report
FROM = 3846
TITLE = re.compile(r"^v\d+: [A-Z][a-z]+ [A-Z][a-z]+$")


def feature_commits(ver):
    out = subprocess.run(["git", "log", "--format=%s"], cwd=ROOT, capture_output=True,
                         text=True, encoding="utf-8").stdout or ""
    # v3849: a subject seen twice is one item - a branch carried both rebased and merged lists each commit twice
    # (68 subjects, 53 distinct). The bar is still one line per distinct feature/fix.
    return list(dict.fromkeys(s for s in out.splitlines() if s.startswith(ver + ": ") and not TITLE.match(s)))


def short(entry):
    n = len(feature_commits(entry["ver"]))
    return n if len(entry["items"]) < n else 0


class EveryShipListsAllItsItems(unittest.TestCase):
    def test_each_history_entry_covers_its_commits(self):
        log = json.load(open(os.path.join(HERE, "CHANGELOG.json"), encoding="utf-8"))
        bad, seen = [], 0
        for e in log:
            if int(e["ver"][1:]) < FROM:
                continue
            n = len(feature_commits(e["ver"]))
            seen += bool(n)
            if len(e["items"]) < n:
                bad.append("%s: %d lines for %d feature/fix commits" % (e["ver"], len(e["items"]), n))
        self.assertEqual(bad, [], "a version's history is missing items: %s" % bad)
        print("checked %d version(s) with commits in reach" % seen)

    def test_the_rule_catches_a_thin_entry(self):
        fake = {"ver": "v3847", "items": ["one line"]}
        self.assertGreater(short(fake), 1)

    def test_git_log_is_decoded_as_utf8(self):
        seen = {}
        real = subprocess.run

        def spy(argv, **kw):
            if argv[:2] == ["git", "log"]:
                seen["encoding"] = kw.get("encoding")
            return real(argv, **kw)

        with mock.patch("subprocess.run", spy):
            feature_commits("v3848")
        self.assertEqual(seen.get("encoding"), "utf-8", "git log follows the console encoding; cp1255 cannot decode a subject")

    def test_stdout_is_made_encoding_safe_before_subjects_are_read(self):
        with open(os.path.join(HERE, "test_every_ship_lists_all_its_items.py"), encoding="utf-8") as fh:
            src = fh.read()
        code = "\n".join(re.sub(r"#.*", "", ln) for ln in src.splitlines())
        armed = code.find("enable()")
        self.assertGreater(armed, 0, "console_safe.enable() is not called")
        self.assertLess(armed, code.find("def feature_commits"))


RED_PROOF = [
    {"why": "v3848 - v3846's history drops an item it shipped",
     "file": "CHANGELOG.json",
     "find": ",\n      \"the plain-run law takes its own lock and cleans up after itself\"",
     "replace": "",
     "matches": 1},
    {"why": "v3849 - git log is decoded in the console encoding and cp1255 dies on a subject",
     "file": "test_every_ship_lists_all_its_items.py",
     "find": "                         text=True, encoding=\"utf-8\").stdout or \"\"\n",
     "replace": "                         text=True).stdout or \"\"\n",
     "matches": 1},
    {"why": "v3849 - a cp1255 console crashes while reporting a subject",
     "file": "test_every_ship_lists_all_its_items.py",
     "find": "from console_safe import enable; enable()  # a subject can carry \u2715; a cp1255 console must still be able to report\n",
     "replace": "\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
