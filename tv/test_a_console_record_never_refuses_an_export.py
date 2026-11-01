# -*- coding: utf-8 -*-
"""v3850 (Dean's console, 2026-10-31) - THE CONSOLE'S OWN RECORD NEVER REFUSES A PROOF EXPORT.

Seen: `heart2.py --export-proved` on Dean's PC said "REG-2630 EXPORT REFUSED: this checkout's tracked files differ from
its HEAD" and the only edit was ` M tv/.status_worst.json` - the record the console rewrites itself, which
self_prove.tracked_edits already forgives for the pull, the fleet row and the ship audit (REG-1837/1898). The file
stays tracked on purpose: deleting it would make `git pull --ff-only` refuse forever on a PC where it is modified
(control_app._status_worst_path). heart2._tracked_dirty is now the one door all four heart2 dirty checks ask. The
other runtime files gate runs write (.chronicle_routes_cache.json, .lane_trace/, *.scratch-*) are gitignored and
untracked, pinned here so none comes back tracked.

RED_PROOF below.
"""
import io
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import heart2 as H  # noqa: E402

RED_PROOF = [
    {"why": "heart2 reads the raw porcelain again, so the console's record refuses the export",
     "file": "heart2.py",
     "find": "        lines, _why = _sp.tracked_edits(out)\n",
     "replace": "        lines = out.splitlines()\n",
     "matches": 1},
    {"why": "the export asks git itself again",
     "file": "heart2.py",
     "find": "    ok_d, dirty = _tracked_dirty()\n    out = os.path.join(",
     "replace": "    ok_d, dirty = _git(\"status\", \"--porcelain\", \"--untracked-files=no\")\n    out = os.path.join(",
     "matches": 1},
]


def _with_status(text):
    real = H._git
    H._git = lambda *a: (True, text) if a[:1] == ("status",) else real(*a)
    try:
        return H._tracked_dirty()
    finally:
        H._git = real


class TheOneDoor(unittest.TestCase):
    def test_the_consoles_own_rewrite_is_forgiven(self):
        self.assertEqual(_with_status(" M tv/.status_worst.json\n"), (True, ""))

    def test_a_real_edit_is_still_dirty(self):
        ok, d = _with_status(" M tv/.status_worst.json\n M tv/heart2.py\n")
        self.assertEqual(d.strip(), "M tv/heart2.py")

    def test_a_merge_conflict_on_the_record_is_never_forgiven(self):
        self.assertIn("UU", _with_status("UU tv/.status_worst.json\n")[1])

    def test_every_heart2_dirty_check_asks_the_door(self):
        with io.open(os.path.join(HERE, "heart2.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertEqual(src.count('_git("status", "--porcelain", "--untracked-files=no")'), 1, "only the door asks git")
        self.assertGreaterEqual(src.count("= _tracked_dirty()"), 4)


class RuntimeFilesStayUntracked(unittest.TestCase):
    def test_none_is_tracked(self):
        r = subprocess.run(["git", "-C", os.path.dirname(HERE), "ls-files", "tv/.chronicle_routes_cache.json",
                            "tv/.lane_trace", "tv/*.scratch-*"], stdout=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(r.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
