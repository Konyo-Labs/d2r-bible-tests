# -*- coding: utf-8 -*-
"""#151 - A GROK SESSION DIRECTORY NEVER OUTLIVES THE CALL THAT MINTED IT, IN EITHER LANE.

MEASURED on his Mac 2026-10-28: ~/.grok/sessions held 55 directories named for the intake lane's throwaway cwd
(tvd-intake-g5-...), every one since 10-21. REG-1687 made the G5 read lane remove its own and sweep leftovers, but
both matched "tvd-g5-" only - and "tvd-intake-g5-" does not contain it - while intake_grok_sub.mjs removed its work
dir and never the session directory the Grok CLI minted for it. On 09-01 this same folder reached 11 GB and ENOSPC.

Now the intake lane drops its own session directory (dropSession, matched by its unique basename only) and the read
lane's sweep knows both names (G5_SESSION_MARKS). His own sessions (any other cwd) and the persistent tvd-g5-home are
never matched. Everything here is a fixture sessions folder in a temp dir. RED_PROOF below.

REG-2731 (the #231 eye on v3819, and a measurement it led to): both lanes matched a SUBSTRING of the whole name, so a
longer folder, or one of his own whose path merely carried the mark, matched too. A session folder is now matched by the
last folder of the cwd it was minted for (g5_grok_eyes.session_tail). And the second-eye runner left its own: 250
second_eye_<pid> session folders (52 MB) on his Mac since 10-21. A look drops its own; leftovers are swept by the
lane's own rule (owner dead, or a day old), never the G5 sweep's 600 s, because a look outlives 600 s.
[[the-unjoined-end]] [[copy-drift]]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 - this run's scratch dirs leave with it; list_own reads only them
_fx_tmp.contain()
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
from cb_node_harness import NODE  # noqa: E402
import g5_grok_eyes as G  # noqa: E402
import second_eye_run as SER  # noqa: E402

MJS = os.path.join(HERE, "intake_grok_sub.mjs")
DROP_HEAD = "export function dropSession(work, home) {\n"


def _mjs():
    with open(MJS, encoding="utf-8") as fh:
        return fh.read()


def _cut_drop(s):
    assert s.count(DROP_HEAD) == 1, "dropSession is not where this law cuts it (%d)" % s.count(DROP_HEAD)
    i = s.index(DROP_HEAD)
    return s[i:s.index("\n}\n", i) + 3].replace("export function", "function", 1)


def _enc(p):
    # REG-3257 - the way Grok names a session folder on either OS: every separator encoded (%2F on a Mac, %5C on Windows,
    # g5_grok_eyes.session_tail) and a drive's colon, so the name is ONE folder. A Windows cwd kept its backslashes and
    # its C: before, so os.path.join(sd, name) dropped sd and planted the session INSIDE the look's own cwd - which the cwd
    # cleanup deletes anyway - and the work ALT filed proof [5] BLIND, which shut all four of its locks.
    return p.replace("/", "%2F").replace("\\", "%5C").replace(":", "%3A")


class _Folder(unittest.TestCase):

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="grokhome_")
        self.addCleanup(shutil.rmtree, self.home, True)
        self.sd = os.path.join(self.home, "sessions")
        os.makedirs(self.sd)

    def plant(self, name, age_s=0):
        p = os.path.join(self.sd, name)
        os.makedirs(os.path.join(p, "s1"))
        with open(os.path.join(p, "s1", "chat_history.jsonl"), "w") as fh:
            fh.write("{}\n")
        if age_s:
            t = time.time() - age_s
            os.utime(p, (t, t))
        return name

    def left(self):
        return sorted(_fx_tmp.list_own(self.sd))


class TheFixtureNamesOneFolderOnEitherOS(unittest.TestCase):

    def test_a_windows_cwd_is_one_folder_name_with_its_tail(self):
        """REG-3257 - the ALT filed proof [5] BLIND because a Windows cwd was not one folder name here."""
        win = "C:\\Users\\U\\AppData\\Local\\Temp\\eyecwd_x\\second_eye_77777"
        name = _enc(win)
        for ch in ("\\", "/", ":"):
            self.assertNotIn(ch, name, "a session name still holds %r, so it is not one folder: %r" % (ch, name))
        import g5_grok_eyes as G5
        self.assertEqual(G5.session_tail(name), "second_eye_77777")
        self.assertEqual(G5.session_tail(_enc("/var/folders/T/second_eye_42")), "second_eye_42")


class TheReadLanesSweepKnowsBothNames(_Folder):

    def test_old_leftovers_of_both_lanes_go_and_his_own_stay(self):
        old = G.G5_SESSION_STALE_S + 60
        g5 = self.plant(_enc("/private/var/folders/T/tvd-g5-AbC123"), old)
        intake = self.plant(_enc("/private/var/folders/T/tvd-intake-g5-XyZ789"), old)
        his = self.plant(_enc("/home/player"), old)
        repo = self.plant(_enc("/home/player/d2r_bible_tests"), old)
        homeish = self.plant(_enc("/private/var/folders/T/tvd-g5-home"), old)
        fresh = self.plant(_enc("/private/var/folders/T/tvd-intake-g5-Fresh1"), 0)
        gone = G._sweep_stale_sessions(self.sd)
        self.assertEqual(gone, 2, "the sweep removed %r, left %r" % (gone, self.left()))
        self.assertNotIn(intake, self.left(), "the intake lane's leftover was never swept (#151)")
        self.assertNotIn(g5, self.left())
        for keep in (his, repo, homeish, fresh):
            self.assertIn(keep, self.left(), "the sweep removed %s - never his, never home, never a call in flight" % keep)


class AFolderIsMatchedByItsLastFolderNotASubstring(_Folder):

    def test_his_folder_that_merely_carries_a_mark_stays(self):
        old = G.G5_SESSION_STALE_S + 60
        his = self.plant(_enc("/home/player/tvd-g5-notes/work"), old)
        tmp = self.plant(_enc("/private/var/folders/T/tvd-g5-Zz9Yy8"), old)
        self.assertEqual(G._sweep_stale_sessions(self.sd), 1, "left: %r" % self.left())
        self.assertIn(his, self.left(), "a folder of his whose path only CONTAINS the mark was swept")
        self.assertNotIn(tmp, self.left())

    def test_the_tail_reads_both_separators(self):
        self.assertEqual(G.session_tail(_enc("/private/var/folders/T/tvd-g5-AbC123")), "tvd-g5-AbC123")
        self.assertEqual(G.session_tail("C%3A%5CUsers%5Cme%5CAppData%5CLocal%5CTemp%5Ctvd-g5-AbC123"), "tvd-g5-AbC123")


class TheSecondEyeLeavesNoSessionBehind(_Folder):

    def test_a_look_drops_its_own_session_and_nothing_else(self):
        mine = self.plant(_enc("/private/var/folders/T/second_eye_4242"))
        longer = self.plant(_enc("/private/var/folders/T/second_eye_42420"))
        his = self.plant(_enc("/home/player"))
        self.assertEqual(SER.drop_eye_session("/var/folders/T/second_eye_4242", sd=self.sd), 1, "left: %r" % self.left())
        self.assertNotIn(mine, self.left())
        self.assertEqual(self.left(), sorted([longer, his]), "a look removed a session that was not its own")

    def test_leftovers_go_by_the_lanes_own_rule(self):
        now = time.time()
        dead = self.plant(_enc("/T/second_eye_999999"), 30)                       # past any pid this OS hands out
        old = self.plant(_enc("/T/second_eye_%d" % os.getppid()), SER.EYE_CWD_STALE_S + 60)
        own = self.plant(_enc("/T/second_eye_%d" % os.getpid()), SER.EYE_CWD_STALE_S + 60)
        his = self.plant(_enc("/home/player/second_eye_notes"), SER.EYE_CWD_STALE_S + 60)   # his, a day old
        gone = SER.sweep_stale_eye_sessions(sd=self.sd, now=now)
        self.assertEqual(sorted(os.path.basename(p) for p, _w in gone), sorted([dead, old]), "swept: %r" % gone)
        for keep in (own, his):
            self.assertIn(keep, self.left(), "the sweep removed %s" % keep)

    def test_the_looks_own_cleanup_drops_it(self):
        """eye_cwd_cleanup - the finally and atexit rope every look already runs - is where the drop happens"""
        from unittest import mock
        root = tempfile.mkdtemp(prefix="eyecwd_")
        self.addCleanup(shutil.rmtree, root, True)
        cwd = os.path.join(root, "second_eye_77777")
        os.makedirs(cwd)
        mine = self.plant(_enc(cwd))
        with mock.patch.object(SER, "EYE_CWD", cwd), mock.patch.object(SER, "_EYE_CWD_IS_OURS", True), \
                mock.patch.object(SER, "_EYE_CWD_MADE", True), mock.patch.object(SER, "_grok_sessions_dir", lambda: self.sd):
            SER.eye_cwd_cleanup()
        self.assertFalse(os.path.exists(cwd), "PREMISE: the look's own cwd was not removed")
        self.assertNotIn(mine, self.left(), "the look's cleanup left its Grok session folder behind")

    def test_a_live_owners_young_session_stays(self):
        young = self.plant(_enc("/T/second_eye_%d" % os.getppid()), 30)          # a live pid, 30 s old: a look mid-run
        self.assertEqual(SER.sweep_stale_eye_sessions(sd=self.sd), [], "a look still running lost its session")
        self.assertIn(young, self.left())


@unittest.skipIf(NODE is None, "node is not on this machine - UNMEASURED here, not passing")
class TheIntakeLaneDropsItsOwnSession(_Folder):

    def drop(self, work):
        js = _cut_drop(_mjs()) + (
            "\nconst { readdirSync, existsSync, rmSync } = require('fs');\nconst { join, basename } = require('path');"
            "\nconst { homedir } = require('os');\nprocess.stdout.write(JSON.stringify(dropSession(%s, %s)));\n"
            % (json.dumps(work), json.dumps(self.home)))
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise AssertionError("dropSession would not run in node - UNKNOWN, not passing: %s" % r.stderr[-600:])
        return json.loads(r.stdout)

    def test_only_this_calls_session_goes(self):
        mine = self.plant(_enc("/private/var/folders/T/tvd-intake-g5-Q1w2E3"))
        other = self.plant(_enc("/private/var/folders/T/tvd-intake-g5-R4t5Y6"))
        his = self.plant(_enc("/home/player"))
        n = self.drop("/var/folders/T/tvd-intake-g5-Q1w2E3")
        self.assertEqual(n, 1, "left: %r" % self.left())
        self.assertEqual(self.left(), sorted([other, his]), "it removed another call's session, or his")
        self.assertNotIn(mine, self.left())

    def test_a_longer_folder_that_contains_this_calls_name_stays(self):
        mine = self.plant(_enc("/private/var/folders/T/tvd-intake-g5-Q1w2E3"))
        longer = self.plant(_enc("/private/var/folders/T/tvd-intake-g5-Q1w2E3x"))
        self.assertEqual(self.drop("/var/folders/T/tvd-intake-g5-Q1w2E3"), 1)
        self.assertEqual(self.left(), [longer], "a folder whose name only CONTAINS this call's was removed")
        self.assertNotIn(mine, self.left())

    def test_a_work_dir_that_is_not_this_lanes_removes_nothing(self):
        """a cwd LONGER than the lane's prefix, so only the prefix check can refuse it (the length check alone would not)"""
        his = self.plant(_enc("/home/player/d2r_bible_tests"))
        self.assertEqual(self.drop("/home/player/d2r_bible_tests"), 0,
                         "a cwd that is not an intake call's matched his own session")
        self.assertEqual(self.left(), [his])

    def test_the_call_drops_it_after_its_work_dir(self):
        s = _mjs()
        self.assertEqual(s.count("  dropSession(work);\n"), 1, "the intake call never drops its session")
        self.assertGreater(s.index("  dropSession(work);\n"), s.index("if (work) rmdirSync(work, { recursive: true });"),
                           "the session is dropped before the call's own cleanup")


RED_PROOF = [
    {"why": "#151 - the read lane's sweep knows only its own name, so every intake session is left behind",
     "file": "tv/g5_grok_eyes.py",
     "find": "G5_SESSION_MARKS = (\"tvd-g5-\", \"tvd-intake-g5-\")\n",
     "replace": "G5_SESSION_MARKS = (\"tvd-g5-\",)\n",
     "matches": 1},
    {"why": "#151 - the intake lane never drops the session directory its call minted",
     "file": "tv/intake_grok_sub.mjs",
     "find": "  dropSession(work);\n",
     "replace": "",
     "matches": 1},
    {"why": "#151 - the intake lane drops every session in the folder, not its own",
     "file": "tv/intake_grok_sub.mjs",
     "find": "      if (name.split(/%2F|%5C/i).pop() !== mine) continue;   // REG-2731 - the cwd's last folder, never a substring\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2731 - the intake lane matches a substring again, so a longer folder that contains its name goes too",
     "file": "tv/intake_grok_sub.mjs",
     "find": "      if (name.split(/%2F|%5C/i).pop() !== mine) continue;   // REG-2731 - the cwd's last folder, never a substring\n",
     "replace": "      if (!name.includes(mine)) continue;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2731 - the G5 sweep matches a substring again, so his folder that merely carries the mark is swept",
     "file": "tv/g5_grok_eyes.py",
     "find": "        if not any(_tail.startswith(m) for m in G5_SESSION_MARKS) or _tail == \"tvd-g5-home\":\n",
     "replace": "        if not any(m in name for m in G5_SESSION_MARKS) or \"tvd-g5-home\" in name:\n",
     "matches": 1},
    {"why": "REG-2731 - a look leaves its Grok session folder behind (250 on his Mac since 10-21)",
     "file": "tv/second_eye_run.py",
     "find": "    drop_eye_session(EYE_CWD)              # REG-2731 - and the Grok session folder this look's cwd minted\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2731 - the second eye's sweep takes his folder that merely starts with its words",
     "file": "tv/second_eye_run.py",
     "find": "        if not pid.isdigit() or pid == str(os.getpid()):\n",
     "replace": "        if pid == str(os.getpid()):\n",
     "matches": 1},
    {"why": "REG-2731 - the second eye's leftover sessions are never swept",
     "file": "tv/second_eye_run.py",
     "find": "        if _g5._drop_session_dir(p, attempts=2, pause_s=0.1):\n            gone.append((p, why))\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "REG-2731 - the second eye's sweep takes a live look's young session",
     "file": "tv/second_eye_run.py",
     "find": "        if age < EYE_CWD_STALE_S and _pid_alive(pid):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "#151 - a work dir that is not an intake call's (his home) matches his own session and removes it",
     "file": "tv/intake_grok_sub.mjs",
     "find": "    if (!mine.startsWith('tvd-intake-g5-') || ",
     "replace": "    if (",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
