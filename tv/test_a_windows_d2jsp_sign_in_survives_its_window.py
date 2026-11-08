# -*- coding: utf-8 -*-
"""v3882 (Dean 11-08, his d2jsp report) - ON WINDOWS THE SIGN-IN MADE IN THE CONSOLE'S OWN d2jsp WINDOW SURVIVES CLOSING IT,
AND THE DOCTOR SAYS SO WHEN IT WOULD NOT.

His words, 11-08: "dean is trying to do d2jsp from his console and its not giving him prices for any searched item".
MEASURED on Dean's PC (SSH, read-only): the console's own d2jsp window went login.php -> r.php -> the forum index - he
SIGNED IN - and once it closed, its cookie file held 0 rows: the sign-in was session-only, and Chrome drops a session
cookie when a profile that does not "continue where it left off" closes (restore_on_startup was unset there). So every
search read "sign in first". The Mac has kept that session since REG-3349 (Chrome's own settings, set while the window is
closed); Windows has signed in through a window the console owns since v3861, and ensure_restore_on answered "not-here"
there - and the doctor's check answered "not a Mac - OK" on every Windows PC, so nothing ever said so.

MEASURED on the work ALT the same hour: _set_restore_headless on its own d2jsp profile - restore_on_startup 0 -> 1 in
18 s, headless, the profile released after. Now ensure_restore_on acts on Windows too (the repair book asks it every 30
min; the login opener asks it before it opens the window), and the doctor's Windows half reads the setting. Temp profiles
and stubbed launches only - no Chrome is started, no profile of his is opened. RED_PROOF below. [[the-unjoined-end]]
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import d2jsp_chrome as D  # noqa: E402
import console_doctor as CD  # noqa: E402


class AWindowsSignInSurvivesItsWindow(unittest.TestCase):

    def setUp(self):
        self.local = tempfile.mkdtemp(prefix="win-d2jsp-")
        self.addCleanup(shutil.rmtree, self.local, True)
        self.root = D.login_profile_dir(platform="win32", env={"LOCALAPPDATA": self.local})
        os.makedirs(os.path.join(self.root, "Default"))

    def _write(self, name, body):
        with io.open(os.path.join(self.root, "Default", name), "w", encoding="utf-8") as fh:
            json.dump(body, fh)

    def _set(self, r):
        self._write("Secure Preferences", {"session": {"restore_on_startup": 1}})
        return True

    def test_windows_is_set_through_chromes_own_settings(self):
        """* THE POINT - Dean's profile: off and closed -> set; on -> fine (the launch stands in for the headless pass)"""
        self._write("Preferences", {"profile": {}})
        with mock.patch.object(D, "profile_in_use", lambda r: False):
            self.assertEqual(D.ensure_restore_on(self.root, launch=self._set, platform="win32")[0], "fixed")
            self.assertEqual(D.ensure_restore_on(self.root, launch=lambda r: 1 / 0, platform="win32")[0], "fine")

    def test_an_open_window_on_windows_is_waited_for_never_launched_over(self):
        launched = []
        with mock.patch.object(D, "profile_in_use", lambda r: True):
            st, _why = D.ensure_restore_on(self.root, launch=lambda r: launched.append(r), platform="win32")
        self.assertEqual((st, launched), ("waiting", []))

    def test_the_windows_opener_keeps_the_session_before_it_opens_the_window(self):
        """the real launch (no law popen) asks ensure_restore_on for the own profile FIRST, then starts that window"""
        order = []
        with mock.patch.object(D, "ensure_restore_on", lambda root, platform=None: order.append(("restore", root, platform))), \
                mock.patch.object(D.subprocess, "Popen", lambda argv, **kw: order.append(("open", list(argv)))), \
                mock.patch.dict(os.environ, {"LOCALAPPDATA": self.local}):
            ok = D._open_chrome_login(platform="win32", which=lambda n: "C:/chrome.exe", env={"LOCALAPPDATA": self.local})
        self.assertTrue(ok)
        self.assertEqual([o[0] for o in order], ["restore", "open"], order)
        self.assertEqual(order[0][1:], (self.root, "win32"))
        self.assertIn("--user-data-dir=" + self.root, order[1][1])

    def test_a_law_launch_never_touches_a_profile(self):
        """a law hands its own popen: no settings pass runs for it (the existing opener laws stay hermetic)"""
        seen = []
        with mock.patch.object(D, "ensure_restore_on", lambda *a, **k: seen.append(a)):
            D._open_chrome_login(platform="win32", which=lambda n: "C:/chrome.exe", popen=lambda argv, **kw: None,
                                 env={"LOCALAPPDATA": self.local})
        self.assertEqual(seen, [])

    def test_the_doctor_says_when_the_sign_in_would_die_with_the_window(self):
        self._write("Secure Preferences", {"session": {"restore_on_startup": 5}})
        st, why = CD._win_own_d2jsp_window_keeps_its_session(self.root)
        self.assertEqual(st, CD.MISSING, why)
        self.assertIn("dies when that window closes", why)
        self._write("Secure Preferences", {"session": {"restore_on_startup": 1}})
        self.assertEqual(CD._win_own_d2jsp_window_keeps_its_session(self.root)[0], CD.OK)
        self.assertEqual(CD._win_own_d2jsp_window_keeps_its_session(os.path.join(self.local, "none"))[0], CD.OK,
                         "a window never opened is not a sign-in that dies")
        with io.open(os.path.join(self.root, "Default", "Secure Preferences"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertEqual(CD._win_own_d2jsp_window_keeps_its_session(self.root)[0], CD.UNKNOWN)

    def test_the_doctor_asks_the_windows_half_on_windows(self):
        with mock.patch.object(CD.sys, "platform", "win32"), \
                mock.patch.object(CD, "_win_own_d2jsp_window_keeps_its_session", lambda root=None: (CD.MISSING, "x")):
            self.assertEqual(CD._check_the_macs_own_d2jsp_window_keeps_its_session(), (CD.MISSING, "x"))

    def test_only_mac_and_windows_sign_in_through_their_own_window(self):
        self.assertEqual(D.ensure_restore_on(self.root, platform="linux")[0], "not-here")


RED_PROOF = [
    {"why": "v3882 - Windows answers 'not-here' again: Dean's sign-in dies with its window and every search reads 'sign in first'",
     "file": "tv/d2jsp_chrome.py",
     "find": '    if plat not in ("darwin", "win32"):\n',
     "replace": '    if plat != "darwin":\n', "matches": 1},
    {"why": "v3882 - the Windows login opener no longer keeps the session before it opens the window",
     "file": "tv/d2jsp_chrome.py",
     "find": "            ensure_restore_on(own, platform=plat)   # v3882 - the sign-in made in this window survives closing it\n",
     "replace": "", "matches": 1},
    {"why": "v3882 - the doctor answers 'not a Mac - OK' on Windows again (nothing says the sign-in dies)",
     "file": "tv/console_doctor.py",
     "find": "    if sys.platform == \"win32\":\n        # v3882 (Dean 11-08: he signed in",
     "replace": "    if False:\n        # v3882 (Dean 11-08: he signed in", "matches": 1},
    {"why": "v3882 - the doctor's Windows half calls a session that dies with its window OK",
     "file": "tv/console_doctor.py",
     "find": "    if v != 1:\n        return MISSING, (\"the console's own d2jsp window does not continue where it left off, so a sign-in's",
     "replace": "    if False:\n        return MISSING, (\"the console's own d2jsp window does not continue where it left off, so a sign-in's",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
