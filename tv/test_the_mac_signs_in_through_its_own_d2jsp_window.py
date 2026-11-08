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

    def _write(self, name, obj):
        d = os.path.join(self.root, "Default")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh) if not isinstance(obj, str) else fh.write(obj)

    def test_the_setting_is_read_where_chrome_keeps_it(self):
        """REG-3349 - MEASURED 11-07 on a scratch profile: Chrome (Mac) keeps session.restore_on_startup in SECURE
        Preferences; a reader of Preferences alone said 'off' while it was on"""
        self.assertIsNone(D.restore_value(self.root), "a profile with no settings files read as a known answer")
        self._write("Preferences", {"profile": {}})
        self.assertEqual(D.restore_value(self.root), 0)
        self._write("Secure Preferences", {"session": {"restore_on_startup": 1}})
        self.assertEqual(D.restore_value(self.root), 1, "the setting where Chrome keeps it was not read")
        self._write("Secure Preferences", "{not json")
        self.assertIsNone(D.restore_value(self.root))

    @unittest.skipIf(os.name == "nt", "a SingletonLock symlink is the Mac/Linux lock; Windows' held lockfile is "
                                      "test_on_windows_the_held_lockfile_says_in_use_and_no_signal_is_sent (v3886, #107)")
    def test_a_profile_chrome_holds_is_never_touched(self):
        os.makedirs(self.root)
        lk = os.path.join(self.root, "SingletonLock")
        os.symlink("host-%d" % os.getpid(), lk)
        self.assertTrue(D.profile_in_use(self.root))
        called = []
        self.assertEqual(D.ensure_restore_on(self.root, launch=lambda r: called.append(r), platform="darwin")[0], "waiting")
        self.assertEqual(called, [], "Chrome was started on a profile another Chrome holds")
        os.remove(lk)
        os.symlink("host-999999999", lk)
        self.assertFalse(D.profile_in_use(self.root), "a lock whose Chrome is gone read as in use")

    def test_on_windows_the_held_lockfile_says_in_use_and_no_signal_is_sent(self):
        """REG-3355 - Windows Chrome keeps no SingletonLock: it holds `lockfile` with no sharing. os.kill(pid, 0) there is
        a Ctrl-C, so it is never asked; a lockfile that will not open is in use, one that opens is a leftover"""
        os.makedirs(self.root)
        killed = []
        with mock.patch.object(D.os, "name", "nt"), mock.patch.object(D.os, "kill", lambda *a: killed.append(a)):
            self.assertFalse(D.profile_in_use(self.root), "no lockfile read as a Chrome holding the profile")
            with io.open(os.path.join(self.root, "lockfile"), "w") as fh:
                fh.write("")
            self.assertFalse(D.profile_in_use(self.root), "a leftover lockfile that opens read as in use")

            def held(*a, **k):
                raise PermissionError(13, "The process cannot access the file because it is being used")
            with mock.patch.object(D.os, "open", held):
                self.assertTrue(D.profile_in_use(self.root), "a lockfile Chrome holds read as free")

            # the second eye on v3879 (Grok CLI): every OSError read "Chrome holds the profile". Anything but the sharing
            # violation (EACCES) cannot be told - None (UNKNOWN), never a claim either way
            def other(*a, **k):
                raise OSError(22, "Invalid argument")
            with mock.patch.object(D.os, "open", other):
                self.assertIsNone(D.profile_in_use(self.root), "a lockfile that will not open for another reason read as a Chrome")
            os.remove(os.path.join(self.root, "lockfile"))
            os.makedirs(os.path.join(self.root, "lockfile"))
            self.assertIsNone(D.profile_in_use(self.root), "a directory where the lock should be read as a Chrome holding it")
        self.assertEqual(killed, [], "a signal was sent on Windows - os.kill(pid, 0) is CTRL_C_EVENT there")

    def test_a_lock_that_cannot_be_told_launches_nothing_and_says_unknown(self):
        """the second eye on v3879 - the repair book says UNKNOWN for a lock it cannot read, never 'waiting' (a claim that the
        window is open), and nothing is launched over it"""
        os.makedirs(self.root)
        launched = []
        with mock.patch.object(D, "restore_value", lambda r: 0), mock.patch.object(D, "profile_in_use", lambda r: None):
            st, why = D.ensure_restore_on(self.root, launch=lambda r: launched.append(r), platform="darwin")
        self.assertEqual((st, launched), ("unknown", []), why)
        self.assertIn("could not be told", why)

    def test_it_is_set_through_chromes_own_settings_by_default(self):
        """REG-3349 (his 11-07: "by default this should be done and not optional on the console end. it should be
        defaulted on") - off and closed -> set (the launch stands in for the headless settings pass); on -> fine"""
        os.makedirs(os.path.join(self.root, "Default"))
        self._write("Preferences", {"profile": {}})
        set_it = lambda r: (self._write("Secure Preferences", {"session": {"restore_on_startup": 1}}) or True)
        self.assertEqual(D.ensure_restore_on(self.root, launch=set_it, platform="darwin")[0], "fixed")
        self.assertEqual(D.ensure_restore_on(self.root, launch=lambda r: 1 / 0, platform="darwin")[0], "fine",
                         "a setting already on started Chrome again")
        self._write("Secure Preferences", {"session": {"restore_on_startup": 5}})
        st, why = D.ensure_restore_on(self.root, launch=lambda r: False, platform="darwin")
        self.assertEqual(st, "failed", "a pass that did not take read as fixed")
        self.assertEqual(D.ensure_restore_on(self.root, launch=lambda r: 1 / 0, platform="darwin")[0], "failed")
        self.assertEqual(D.ensure_restore_on(self.root, platform="linux")[0], "not-here")

    def test_the_old_seed_never_rewrites_what_chrome_reset(self):
        """REG-3347 - a value written from outside is reset by Chrome; the seed does not write it again"""
        self._write("Preferences", {"profile": {}})
        self._write("Secure Preferences", {"prefs.tracked_preferences_reset": ["session.restore_on_startup"]})
        self.assertIs(D.chrome_reset_restore(self.root), True)
        self.assertFalse(D.seed_login_profile(self.root), "the seed wrote again what Chrome resets")
        with open(os.path.join(self.root, "Default", "Preferences"), encoding="utf-8") as fh:
            self.assertNotIn("session", json.load(fh))

    def test_the_doctor_and_the_repair_book_carry_it(self):
        self._write("Preferences", {"profile": {}})
        self._write("Secure Preferences", {"prefs.tracked_preferences_reset": ["session.restore_on_startup"]})
        import console_doctor as CD
        with mock.patch.object(D, "login_profile_dir", lambda **kw: self.root), mock.patch.object(sys, "platform", "darwin"):
            state, why = CD._check_the_macs_own_d2jsp_window_keeps_its_session()
            self.assertEqual(state, CD.MISSING)
            self.assertIn("the repair book sets it through Chrome's own settings", why)
            self._write("Secure Preferences", {"session": {"restore_on_startup": 1}})
            self.assertEqual(CD._check_the_macs_own_d2jsp_window_keeps_its_session()[0], CD.OK,
                             "the setting where Chrome keeps it reads as off")
        import repair_book as RB
        ent = [e for e in RB.ENTRIES if e["id"] == "d2jsp-restore"]
        self.assertEqual(len(ent), 1, "the repair book does not know this fault")
        self.assertEqual(ent[0]["check"], "the Mac signs in to d2jsp through its own window")
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            app = fh.read()
        self.assertIn('"d2jsp-restore": _book_d2jsp_restore,', app, "the book is handed no door for it")
        with io.open(os.path.join(HERE, "d2jsp_chrome.py"), encoding="utf-8") as fh:
            dj = fh.read()
        self.assertIn("            ensure_restore_on(own, platform=plat)", dj, "the lamp's opener does not set it first")

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
    {"why": "the second eye on v3879 - any OSError reads as Chrome holding the profile again",
     "file": "tv/d2jsp_chrome.py",
     "find": "        except OSError:\n            return None                 # any other refusal cannot be told: UNKNOWN\n",
     "replace": "        except OSError:\n            return True\n", "matches": 1},
    {"why": "the second eye on v3879 - a lock that cannot be told reads as 'waiting' (the window open) again",
     "file": "tv/d2jsp_chrome.py",
     "find": "    if held is None:\n", "replace": "    if False:\n", "matches": 1},
    {
        "why": "REG-3355 - Windows falls through to the Mac's SingletonLock and os.kill: a Ctrl-C, and his Chrome read as free",
        "file": "d2jsp_chrome.py",
        "find": "    if os.name == \"nt\":\n        lf = os.path.join(root, \"lockfile\")\n",
        "replace": "    if False:\n        lf = os.path.join(root, \"lockfile\")\n",
        "matches": 1,
    },
    {
        "why": "REG-3355 - a lockfile Chrome holds (it will not open) reads as free on Windows",
        "file": "d2jsp_chrome.py",
        "find": "        except PermissionError:\n            return True                 # held with no sharing",
        "replace": "        except PermissionError:\n            return False                # held with no sharing",
        "matches": 1,
    },
    {"why": "#24 - the seed rewrites a restore setting Chrome resets, every launch",
     "file": "tv/d2jsp_chrome.py",
     "find": "        if chrome_reset_restore(root):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3349 - the setting is read from Preferences only, so it reads off while Chrome keeps it on",
     "file": "tv/d2jsp_chrome.py",
     "find": "    for name in (\"Secure Preferences\", \"Preferences\"):\n",
     "replace": "    for name in (\"Preferences\",):\n",
     "matches": 1},
    {"why": "REG-3349 - Chrome is started on a profile another Chrome holds",
     "file": "tv/d2jsp_chrome.py",
     "find": "    if held:\n        return \"waiting\"",
     "replace": "    if False:\n        return \"waiting\"",
     "matches": 1, "needs": "posix"},   # v3886 (#107) - caught by the SingletonLock case, which is the Mac/Linux lock
    {"why": "REG-3349 - the repair book never sets it, so it stays off until someone clicks",
     "file": "tv/control_app.py",
     "find": "        \"d2jsp-restore\": _book_d2jsp_restore,\n",
     "replace": "",
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
