# -*- coding: utf-8 -*-
"""#87 (his call 2026-11-06 10:15, "its own d2jsp window") - THE MAC SIGNS IN TO d2jsp THROUGH A PROFILE THE CONSOLE OWNS.

MEASURED on his Mac (REG-3250): his Chrome IS signed in to d2jsp, the console reads and sends all three of its d2jsp
cookies, and d2jsp answers that copy by overwriting member_id. Chrome is not set to continue where it left off, so a
session-only cookie of his sign-in lives in Chrome's memory and never reaches the cookie file - the likeliest gap. His
call: the Windows way (v3861) on the Mac too.

  1. The Mac's own login profile is ~/Library/Application Support/TVD/d2jsp-login, and it is seeded to continue where it
     left off, so a session cookie of the sign-in made there is written to its cookie file.
  2. The lamp's opener starts a SEPARATE Chrome on that profile (open -na ... --user-data-dir), never port 9222.
  3. Reads ask that profile first; his own Chrome's cookies are the fallback.
  4. The lamp is on only for the console's own sign-in; before it, the lamp says to click and sign in there once.
Temp HOME and stubbed readers only - his profiles are never opened. RED_PROOF below.
"""
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


class TheMacOwnsItsD2jspSignIn(unittest.TestCase):

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="own-d2jsp-")
        self.addCleanup(shutil.rmtree, self.home, True)
        self.root = D.login_profile_dir(platform="darwin", env={"HOME": self.home})

    def test_the_own_profile_lives_under_the_console(self):
        self.assertEqual(self.root, os.path.join(self.home, "Library", "Application Support", "TVD", "d2jsp-login"))
        self.assertIsNone(D.login_profile_dir(platform="linux", env={"HOME": self.home}))

    def test_the_own_profile_keeps_its_session(self):
        self.assertTrue(D.seed_login_profile(self.root))
        with open(os.path.join(self.root, "Default", "Preferences"), encoding="utf-8") as fh:
            prefs = json.load(fh)
        self.assertEqual(prefs["session"]["restore_on_startup"], 1,
                         "the sign-in's session cookie would die with the window")
        prefs["other"] = 7
        with open(os.path.join(self.root, "Default", "Preferences"), "w", encoding="utf-8") as fh:
            json.dump(prefs, fh)
        self.assertTrue(D.seed_login_profile(self.root))
        with open(os.path.join(self.root, "Default", "Preferences"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh).get("other"), 7, "seeding wiped what Chrome keeps there")

    def test_a_setting_chrome_reset_is_not_written_again_and_the_doctor_says_why(self):
        """#24 (the Mac's eagle; MEASURED 11-07: Secure Preferences "prefs.tracked_preferences_reset":
        ["session.restore_on_startup"], Preferences with no session) - Chrome undoes the seed as tampering"""
        d = os.path.join(self.root, "Default")
        os.makedirs(d)
        with open(os.path.join(d, "Preferences"), "w", encoding="utf-8") as fh:
            json.dump({"profile": {"exit_type": "Normal"}}, fh)
        with open(os.path.join(d, "Secure Preferences"), "w", encoding="utf-8") as fh:
            json.dump({"prefs.tracked_preferences_reset": ["session.restore_on_startup"]}, fh)
        self.assertIs(D.chrome_reset_restore(self.root), True)
        self.assertFalse(D.seed_login_profile(self.root), "the seed wrote again what Chrome resets")
        with open(os.path.join(d, "Preferences"), encoding="utf-8") as fh:
            self.assertNotIn("session", json.load(fh), "a value Chrome undoes was written again")
        import console_doctor as CD
        with mock.patch.object(D, "login_profile_dir", lambda **kw: self.root), mock.patch.object(sys, "platform", "darwin"):
            state, why = CD._check_the_macs_own_d2jsp_window_keeps_its_session()
        self.assertEqual(state, CD.MISSING)
        self.assertIn("Chrome reset", why)
        self.assertIn("On startup > Continue where you left off", why, "the doctor does not say what sticks")
        with open(os.path.join(d, "Secure Preferences"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertIsNone(D.chrome_reset_restore(self.root), "an unreadable Secure Preferences read as a known answer")

    def test_a_session_that_is_not_a_dict_is_replaced_not_a_crash(self):
        """REG-3282 (the Grok CLI on v3872) - "session": "1" raised AttributeError out of the seed and the doctor."""
        d = os.path.join(self.root, "Default")
        os.makedirs(d)
        for bad in ("1", [1], 7):
            with open(os.path.join(d, "Preferences"), "w", encoding="utf-8") as fh:
                json.dump({"session": bad, "other": 3}, fh)
            self.assertFalse(D.session_restores({"session": bad}))
            self.assertTrue(D.seed_login_profile(self.root), "a %r session made the seed fail" % (bad,))
            with open(os.path.join(d, "Preferences"), encoding="utf-8") as fh:
                prefs = json.load(fh)
            self.assertTrue(D.session_restores(prefs), "a %r session was not replaced by the seed" % (bad,))
            self.assertEqual(prefs.get("other"), 3)

    def test_a_preferences_file_that_will_not_read_is_never_overwritten(self):
        """REG-3294 (the Grok CLI's second look at v3872) - Chrome mid-write left a truncated file; the seed rewrote it
        from {} and every other setting was lost."""
        d = os.path.join(self.root, "Default")
        os.makedirs(d)
        p = os.path.join(d, "Preferences")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write('{"profile": {"name": "his"}, "sess')
        self.assertFalse(D.seed_login_profile(self.root), "a truncated Preferences read as a seeded profile")
        with open(p, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), '{"profile": {"name": "his"}, "sess', "the unreadable file was overwritten")
        os.remove(p)
        self.assertTrue(D.seed_login_profile(self.root), "premise: an absent file is created")

    def test_the_opener_starts_a_separate_chrome_on_the_own_profile(self):
        seen = []

        def run(argv, **kw):
            seen.append(list(argv))
            return type("P", (), {"returncode": 0})()
        self.assertTrue(D._open_chrome_login(platform="darwin", run=run, env={"HOME": self.home}))
        self.assertEqual(seen[-1][:4], ["open", "-na", "Google Chrome", "--args"])
        self.assertIn("--user-data-dir=" + self.root, seen[-1])
        self.assertIn(D.LOGIN_URL, seen[-1])
        self.assertFalse(any("9222" in a or "remote-debugging" in a for a in seen[-1]))

    def test_the_own_sign_in_is_read_first(self):
        os.makedirs(os.path.join(self.root, "Default"))
        open(os.path.join(self.root, "Default", "Cookies"), "wb").close()
        calls = []

        def fake(now_utc=None, why=None, root=None):
            calls.append(root)
            return ("member_id=own", "ok") if root else ("member_id=his", "ok")
        with mock.patch.object(D, "_mac_cookie_header", fake), \
                mock.patch.object(D, "login_profile_dir", lambda platform=None, env=None: self.root), \
                mock.patch.object(D.sys, "platform", "darwin"):
            self.assertEqual(D.live_cookie_header(), ("member_id=own", "ok"), "his Chrome's copy was read first")
            self.assertEqual(calls[0], os.path.join(self.root, "Default"))

    def lamp(self, own):
        def his_chrome(*a, **k):
            raise AssertionError("the lamp read his own Chrome")
        with mock.patch.object(D.sys, "platform", "darwin"), \
                mock.patch.object(D, "_sweep_stale_scratch", lambda *a, **k: 0), \
                mock.patch.object(D, "_mac_cookie_header", his_chrome), \
                mock.patch.object(D, "mac_own_login_header", own):
            return D.d2jsp_login_status()

    def test_the_lamp_is_on_only_for_the_own_sign_in(self):
        for reason in ("no-profile", "need-login"):
            st = self.lamp(lambda now_utc=None, root=None, why=None, r=reason: (None, r))
            self.assertEqual((st["state"], st["kind"], st.get("needsLogin")), ("off", "own-window", True),
                             "the lamp says signed in before the console's own sign-in exists: %r" % st)
            self.assertIn("sign in there once", st["why"])
        self.assertEqual(self.lamp(lambda now_utc=None, root=None, why=None: ("member_id=own", "ok"))["state"], "on")

    def test_a_keychain_refusal_is_unknown_never_signed_out(self):
        def refused(now_utc=None, root=None, why=None):
            why.append("the keychain refused the Chrome Safe Storage password (exit 51)")
            return None, "chrome-unread"
        st = self.lamp(refused)
        self.assertEqual(st["state"], "unknown", st)
        self.assertIn("exit 51", st["why"])

    def test_an_opened_profile_with_no_cookie_file_is_not_signed_in_yet(self):
        os.makedirs(os.path.join(self.root, "Default"))
        self.assertEqual(D.mac_own_login_header(root=self.root), (None, "need-login"))
        self.assertEqual(D.mac_own_login_header(root=os.path.join(self.home, "never")), (None, "no-profile"))


RED_PROOF = [
    {"why": "#24 - the seed rewrites a restore setting Chrome resets, every launch",
     "file": "tv/d2jsp_chrome.py",
     "find": "        if chrome_reset_restore(root):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "#24 - the doctor never says Chrome reset the setting, nor what sticks",
     "file": "tv/console_doctor.py",
     "find": "        if dj.chrome_reset_restore(root):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3294 - a Preferences file that will not read is overwritten from nothing",
     "file": "tv/d2jsp_chrome.py",
     "find": "            # mid-write, a truncated file) is never overwritten: rewriting it from {} would drop every other setting\n            return False\n",
     "replace": "            # mid-write, a truncated file) is never overwritten: rewriting it from {} would drop every other setting\n            prefs = {}\n",
     "matches": 1},
    {"why": "REG-3282 - a session value that is not a dict crashes the seed (and the doctor)",
     "file": "tv/d2jsp_chrome.py",
     "find": "        if not isinstance(prefs.get(\"session\"), dict):\n            prefs[\"session\"] = {}",
     "replace": "        if False:\n            prefs[\"session\"] = {}",
     "matches": 1},
    {"why": "REG-3282 - the predicate reads a non-dict session as restoring",
     "file": "tv/d2jsp_chrome.py",
     "find": "    return isinstance(sess, dict) and sess.get(\"restore_on_startup\") == 1\n",
     "replace": "    return bool(sess)\n",
     "matches": 1},
    {"why": "#87 - the own profile forgets its session: the sign-in's session cookie dies with the window",
     "file": "tv/d2jsp_chrome.py",
     "find": "        prefs[\"session\"][\"restore_on_startup\"] = 1\n",
     "replace": "        prefs[\"session\"]\n",
     "matches": 1},
    {"why": "#87 - reads ask his Chrome first and the copy d2jsp turns away wins",
     "file": "tv/d2jsp_chrome.py",
     "find": "        own = mac_own_login_header(now_utc)\n        if own[0]:\n",
     "replace": "        own = mac_own_login_header(now_utc)\n        if False:\n",
     "matches": 1},
    {"why": "#87 - a keychain refusal on the own profile reads as signed out, and he signs in again for nothing",
     "file": "tv/d2jsp_chrome.py",
     "find": "        if _own_reason in (\"no-profile\", \"need-login\"):\n",
     "replace": "        if True:\n",
     "matches": 1},
    {"why": "#87 - the lamp's opener opens his own Chrome again, where the console cannot use the sign-in",
     "file": "tv/d2jsp_chrome.py",
     "find": "        argv = ([\"open\", \"-na\", \"Google Chrome\", \"--args\", \"--user-data-dir=%s\" % own, \"--no-first-run\",\n",
     "replace": "        argv = ([\"open\", \"-a\", \"Google Chrome\", \"--no-first-run\",\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
