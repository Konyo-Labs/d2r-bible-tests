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


def stamps_in_reach():
    """v3898 (MEASURED 11-11 on GitHub, agent-suite (4) of v3898's round) - the versions whose own STAMP commit ("vNNNN: Two
    Words") is in this clone. -> set. A version whose stamp is in reach WAS checked even with no "vNNNN: " feature commit:
    since ~v3880 fixes are written "fix: vNNNN - ...", so the newest old-style subject (v3889) fell to depth 203 - past CI's
    200-commit clone - and the law read "checked nothing" on a clone that held v3897's and v3898's stamps."""
    git = subprocess.run(["git", "log", "--format=%s"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    out = git.stdout or ""
    return set(s.split(":", 1)[0] for s in out.splitlines() if TITLE.match(s))


def short(entry):
    n = len(feature_commits(entry["ver"]))
    return n if len(entry["items"]) < n else 0


class EveryShipListsAllItsItems(unittest.TestCase):
    def test_each_history_entry_covers_its_commits(self):
        log = json.load(open(os.path.join(HERE, "CHANGELOG.json"), encoding="utf-8"))
        bad, seen = [], 0
        stamps = stamps_in_reach()
        for e in log:
            if int(e["ver"][1:]) < FROM:
                continue
            n = len(feature_commits(e["ver"]))
            seen += bool(n) or e["ver"] in stamps     # v3898 - a stamp in reach is a version checked (0 feature commits)
            if len(e["items"]) < n:
                bad.append("%s: %d lines for %d feature/fix commits" % (e["ver"], len(e["items"]), n))
        self.assertEqual(bad, [], "a version's history is missing items: %s" % bad)
        # v3850 (Grok CLI second eye on v3848, finding 2) - a clone with no listed version in reach checked nothing
        self.assertGreater(seen, 0, "no version since v%d has a commit in reach (a shallow clone?) - this checked "
                                    "nothing, and nothing checked is never a pass" % FROM)
        print("checked %d version(s) with commits in reach" % seen)

    def test_a_clone_with_no_version_in_reach_is_not_a_pass(self):
        with mock.patch(__name__ + ".feature_commits", lambda ver: []), \
                mock.patch(__name__ + ".stamps_in_reach", lambda: set()):
            with self.assertRaises(AssertionError):
                self.test_each_history_entry_covers_its_commits()

    def test_a_shallow_clone_holding_only_new_style_versions_is_checked(self):
        """v3898 - only a stamp and fix commits in reach: the version is checked (0 feature commits), never 'nothing'"""
        subjects = ["fix: v3898 - a thing", "v3898: One Game", "fix: v3897 - other", "v3897: Honest Rounds"]
        with mock.patch("subprocess.run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "\n".join(subjects), "")):
            self.assertEqual(stamps_in_reach(), {"v3898", "v3897"})
            self.assertEqual(feature_commits("v3898"), [], "PREMISE: a fix commit is not an old-style feature subject")

    def test_the_rule_catches_a_thin_entry(self):
        # v3859: the rule is asked over a fixed log, not the clone's. CI clones 200 commits deep, and a 174-commit bundle
        # pushed every v3847 subject out of reach, so the self-test read 0 subjects and said the rule was blind.
        subjects = ["v3847: one", "v3847: two", "v3847: three", "v3847 CI not counted", "v3847: Ship Title"]
        with mock.patch("subprocess.run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "\n".join(subjects), "")):
            self.assertEqual(short({"ver": "v3847", "items": ["one line"]}), 3)
            self.assertEqual(short({"ver": "v3847", "items": ["a", "b", "c"]}), 0)

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
    {"why": "v3898 - a version whose stamp is in reach counts as unchecked again (the 200-commit CI clone reads nothing)",
     "file": "test_every_ship_lists_all_its_items.py",
     "find": "    return set(s.split(\":\", 1)[0] for s in out.splitlines() if TITLE.match(s))\n",
     "replace": "    return set()\n",
     "matches": 1},
    {"why": "v3850 - a clone with no version in reach passes having checked nothing",
     "file": "test_every_ship_lists_all_its_items.py",
     "find": "seen, 0, \"no version since",
     "replace": "seen + 1, 0, \"no version since",
     "matches": 1},
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
    {"why": "v3859 - a thin entry is never short: the rule counts nothing and every history passes",
     "file": "test_every_ship_lists_all_its_items.py",
     "find": "    return n if len(entry[\"items\"]) < n else 0\n",
     "replace": "    return 0\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
