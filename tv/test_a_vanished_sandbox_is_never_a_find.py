# -*- coding: utf-8 -*-
"""REG-3416 (v3882, his 11-08: "the proofs being proven properly on all machines ... rivers flowing finally?") - A PROVER'S
SANDBOX KEEPS ITS FILES, AND A RED RUN WHOSE SANDBOX LOST FILES IS NEVER THE SAFETY NET'S FIND.

MEASURED on his Mac 11-08 (read-only: tv/.heart2.json, tv/.self_prove.json.log): at 03:44 the safety net filed
"test_control: its clean run is RED here, untampered" and every lock test_control guards shut (the Fleet: "safety net:
test_control RED · its locks shut", the river "waits on 4 shut locks"). Its own log said why, and nothing read it:
"#144 a tracked file vanished from a lane sandbox: .claude/skills/d2r-bible/SKILL.md, ... (running test_control.py, lane
1) [owner file present; sandbox root present; created 6979s ago ...; no sweep journal line names it]", then "the CLOSING
clean run is RED (Ran 2274 tests ... FAILED (failures=14, errors=29))". 1,328 files had vanished - EVERY one with an access
time of 3.2+ days in the repo, none under 3 days, while 571 of 1,924 tv/*.py read in the last 3 days all stayed. macOS
sweeps $TMPDIR files unread for 3 days; safe_copy's copytree used copy2, which carries each file's OLD times into the
sandbox. test_control ran 2,274 OK quietly on the same Mac at 04:06. The third such vanish in that log.

  * safe_copy copies bytes and mode with FRESH times (as a git checkout and CI do) - a sandbox never looks days unread;
  * a red clean run of a gate whose sandbox lost files while that gate ran (#144, heart2._VANISHED) is not a find: the net
    could not judge it here, so it stays trusted, closes nothing and is asked again. Another gate's vanish does not count.

Temp trees and stubs only - no prover runs, no census of his is read or written. RED_PROOF below.
[[stale-reading]] [[the-unjoined-end]] [[feedback-fixtures-never-touch-live-data]]
"""
import io
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import heart2       # noqa: E402

# v3883 - the net's re-check now waits for a quiet PC (heart2._wait_for_quiet). These cases judge the re-check's
# VERDICT, never this machine's load: the wait answers "quiet" for the whole module, and
# test_a_net_red_under_load_is_judged_again drives the wait itself.
_QUIET = mock.patch.object(heart2, "_wait_for_quiet", lambda *a, **k: 0.0)


def setUpModule():
    _QUIET.start()


def tearDownModule():
    _QUIET.stop()

import safe_copy    # noqa: E402

TEN_DAYS = 10 * 86400


class ASandboxCopyHasFreshTimes(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="freshcopy-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.src = os.path.join(self.tmp, "src")
        os.makedirs(os.path.join(self.src, ".claude", "skills", "x"))
        old = time.time() - TEN_DAYS
        for rel in ("AGENTS.md", os.path.join(".claude", "skills", "x", "SKILL.md"), "tool.py"):
            p = os.path.join(self.src, rel)
            with io.open(p, "w", encoding="utf-8") as fh:
                fh.write("x\n")
            os.utime(p, (old, old))
        os.chmod(os.path.join(self.src, "tool.py"), 0o755)

    def test_no_copied_file_looks_days_unread(self):
        """* THE POINT - a file unread for 10 days in the repo is not 10 days unread in the sandbox"""
        dst = os.path.join(self.tmp, "dst")
        self.assertEqual(safe_copy.copy(self.src, dst, say=lambda *a, **k: None), 0)
        now = time.time()
        for rel in ("AGENTS.md", os.path.join(".claude", "skills", "x", "SKILL.md"), "tool.py"):
            st = os.stat(os.path.join(dst, rel))
            self.assertGreater(st.st_atime, now - 3600, "%s carried its old access time into the copy" % rel)
            self.assertGreater(st.st_mtime, now - 3600, "%s carried its old modification time into the copy" % rel)

    def test_the_bytes_and_the_mode_still_travel(self):
        dst = os.path.join(self.tmp, "dst")
        safe_copy.copy(self.src, dst, say=lambda *a, **k: None)
        with io.open(os.path.join(dst, "AGENTS.md"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "x\n")
        # v3886 (#107, windows-latest) - an execute bit is a POSIX mode; Windows has none for chmod to set or a copy to keep
        if os.name == "posix":
            self.assertTrue(os.stat(os.path.join(dst, "tool.py")).st_mode & 0o100, "the copy lost the file's mode")


class _NetFixture(unittest.TestCase):

    def setUp(self):
        self._runs = getattr(heart2._CLEAN, "runs", None)
        self._census = dict(heart2._CENSUS)
        self.addCleanup(self._restore)
        self.said = []
        self.asked = []

    def _restore(self):
        heart2._CLEAN.runs = self._runs
        heart2._CENSUS.clear()
        heart2._CENSUS.update(self._census)

    def red_runs(self, again_ok=False):
        def again():
            self.asked.append(1)
            return again_ok, "FAIL: test_b (m.C)\n"
        heart2._CLEAN.runs = {"clean": {"ok": False, "tail": "FAIL: test_a (m.C)\n", "again": again}}


class AVanishedRedIsNeverAFind(_NetFixture):

    def test_a_red_after_its_sandbox_lost_files_is_not_a_find(self):
        """* THE POINT - the Mac's 03:44 test_control: files vanished, the clean run RED - judged again, never a find"""
        self.red_runs()
        held = heart2._net_red_holds("test_control", self.said.append,
                                     vanished=[("test_control.py", "AGENTS.md", 1), ("test_control.py", "tv/x.json", 1)])
        self.assertFalse(held, "a red over a sandbox that lost files was filed as the safety net's find")
        self.assertEqual(heart2._CENSUS.get("vanishedRed", {}).get("test_control"), ["AGENTS.md", "tv/x.json"])
        self.assertEqual(self.asked, [], "the re-check ran in the same broken sandbox")
        self.assertIn("REG-3416", " ".join(self.said))

    def test_premise_a_red_with_nothing_vanished_still_stands(self):
        self.red_runs(again_ok=False)
        self.assertTrue(heart2._net_red_holds("test_control", self.said.append, vanished=[]))
        self.assertEqual(self.asked, [1])
        self.red_runs(again_ok=False)
        self.assertTrue(heart2._net_red_holds("test_control", self.said.append), "the old call shape changed meaning")


class OnlyThisGatesVanishCounts(_NetFixture):

    def _prove(self, appended):
        seen = {}

        def proofs(sandbox, name, filename, proofs_, say):
            heart2._VANISHED.extend(appended)
            heart2._CLEAN.runs = {"clean": {"ok": False, "tail": ""}}
            return [heart2.PROVEN]

        def holds(name, say, vanished=None):
            seen["vanished"] = vanished
            return False
        n0 = len(heart2._VANISHED)
        self.addCleanup(lambda: heart2._VANISHED.__delitem__(slice(n0, None)))
        heart2._CENSUS["net"] = True
        heart2._CENSUS.pop("cache", None)
        with mock.patch.object(heart2, "_reset_lane_records", lambda *a, **k: None), \
                mock.patch.object(heart2, "_PUSH", None), \
                mock.patch.object(heart2, "_prove_gate_proofs", proofs), \
                mock.patch.object(heart2, "_closing_clean", lambda name, v, say: v), \
                mock.patch.object(heart2, "_net_red_holds", holds):
            heart2._prove_gate("/nowhere", "test_control", "test_control.py", [], lambda *a, **k: None)
        return seen.get("vanished")

    def test_the_gate_hands_the_net_its_own_vanished_files(self):
        got = self._prove([("test_control.py", "AGENTS.md", 1), ("test_other.py", "README.md", 2)])
        self.assertEqual(got, [("test_control.py", "AGENTS.md", 1)], "another gate's vanish was counted, or none: %r" % got)

    def test_a_vanish_before_this_gate_ran_is_not_its_own(self):
        heart2._VANISHED.append(("test_control.py", "OLD.md", 1))
        self.addCleanup(lambda: heart2._VANISHED.remove(("test_control.py", "OLD.md", 1)))
        self.assertEqual(self._prove([]), [])


RED_PROOF = [
    {"why": "REG-3416 - safe_copy copies with copy2 again: a sandbox carries the repo's old access times and macOS's "
            "$TMPDIR sweep deletes a live prover's files",
     "file": "safe_copy.py",
     "find": "    shutil.copytree(src, dst, ignore=_ignore, symlinks=True, copy_function=shutil.copy)\n",
     "replace": "    shutil.copytree(src, dst, ignore=_ignore, symlinks=True)\n", "matches": 1},
    {"why": "REG-3416 - a red over a sandbox that lost files is the net's find again: every lock it guards shuts for 6 h",
     "file": "heart2.py",
     "find": "    if vanished:\n        # REG-3416 - FILES VANISHED FROM THIS GATE'S SANDBOX WHILE IT RAN (#144)",
     "replace": "    if False:\n        # REG-3416 - FILES VANISHED FROM THIS GATE'S SANDBOX WHILE IT RAN (#144)", "matches": 1},
    {"why": "REG-3416 - the gate counts every lane's vanish, not its own",
     "file": "heart2.py",
     "find": "        _gone = [v for v in _VANISHED[_v0:] if v[0] == filename]\n",
     "replace": "        _gone = list(_VANISHED[_v0:])\n", "matches": 1},
    {"why": "REG-3416 - the gate counts a vanish from before it ran",
     "file": "heart2.py",
     "find": "        _v0 = len(_VANISHED)                             # REG-3416 - what vanished from THIS gate's sandbox while it ran\n",
     "replace": "        _v0 = 0\n", "matches": 1},
    {"why": "REG-3416 - the gate never hands the net what vanished",
     "file": "heart2.py",
     "find": "                                                                                                    vanished=_gone):",
     "replace": "                                                                                                    vanished=None):",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
