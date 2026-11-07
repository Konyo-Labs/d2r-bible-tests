# -*- coding: utf-8 -*-
"""REG-1800 — AN UNREAD LOG IS NOT A CONSOLE WITH NO LOG YET.

/api/log and the doctor log tail caught every exception and answered
"(no log yet)" with ok true. A missing file is that empty. A blank file is
empty. A real tail is the tail. A file that will not read, a directory, and
an IO error are not that empty. The doctor adds a row that is not ok. It
warns (REG-1824): a log the doctor cannot read stops no session, and the
rows beside it that cannot read the journal warn too, so a block here was
an over-grade the boot-failure toast would print as a blocker. The screen
says the log was not read.

Nothing here reads his live log, and nothing starts a sweep.
RED_PROOF below. [[unknown-stays-unknown]]
"""
import inspect
import io
import os

#: #107 - chmod(0) makes a file or directory unreadable only where POSIX modes hold; on Windows it only sets
#: read-only, so a case built on it measures nothing there (its door is pinned by the io-error cases)
_POSIX_MODES = os.name != "nt"
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

import control_app as ca  # noqa: E402


class AnUnreadLogIsNotAConsoleWithNoLog(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="log1800_")
        self.path = os.path.join(self.tmp, "control_agent.log")

    def tearDown(self):
        try:
            os.chmod(self.path, 0o644)
        except OSError:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_missing_file_is_still_no_log_yet(self):
        got = ca._console_log_read(100, path=os.path.join(self.tmp, "missing.log"))
        self.assertEqual(got, {"ok": True, "log": "(no log yet)", "why": None})

    def test_a_blank_file_is_still_an_empty_log(self):
        with open(self.path, "wb") as fh:
            fh.write(b"")
        got = ca._console_log_read(100, path=self.path)
        self.assertTrue(got["ok"], got)
        self.assertEqual(got["log"], "")
        self.assertIsNone(got["why"])

    def test_a_real_tail_is_still_the_tail(self):
        with open(self.path, "wb") as fh:
            fh.write(b"A" * 50 + b"TAIL")
        got = ca._console_log_read(4, path=self.path)
        self.assertTrue(got["ok"], got)
        self.assertEqual(got["log"], "TAIL")
        self.assertIsNone(got["why"])

    @unittest.skipUnless(_POSIX_MODES, "chmod(0) cannot make a path unreadable on Windows")
    def test_a_file_that_will_not_read_is_not_no_log_yet(self):
        with open(self.path, "wb") as fh:
            fh.write(b"secret\n")
        os.chmod(self.path, 0)
        try:
            got = ca._console_log_read(100, path=self.path)
        finally:
            os.chmod(self.path, 0o644)
        self.assertIs(got["ok"], False, got)
        self.assertIsNone(got["log"])
        self.assertIn("PermissionError", got["why"])
        self.assertNotIn("secret", got["why"])
        self.assertNotIn("(no log yet)", got["log"] or "")

    def test_a_directory_is_not_no_log_yet(self):
        got = ca._console_log_read(100, path=self.tmp)
        self.assertIs(got["ok"], False, got)
        self.assertIsNone(got["log"])
        # #107 - opening a directory is IsADirectoryError on POSIX and PermissionError on Windows; either is unread, not no log
        self.assertTrue("IsADirectoryError" in got["why"] or (os.name == "nt" and "PermissionError" in got["why"]), got["why"])

    def test_an_io_error_is_not_no_log_yet(self):
        with mock.patch("builtins.open", side_effect=OSError("disk went away")):
            got = ca._console_log_read(100, path=self.path)
        self.assertIs(got["ok"], False, got)
        self.assertIsNone(got["log"])
        self.assertIn("OSError", got["why"])
        self.assertIn("disk went away", got["why"])

    def test_the_doctor_does_not_call_an_unread_log_absent(self):
        tail, why, extra = ca._doctor_log_fields(
            {"ok": False, "log": None, "why": "PermissionError: denied"})
        self.assertIsNone(tail)
        self.assertIn("PermissionError", why)
        self.assertEqual(len(extra), 1)
        row = extra[0]
        self.assertEqual(row["id"], "console_log")
        self.assertIs(row["ok"], False)
        self.assertEqual(row["severity"], "warn")
        self.assertIn("UNMEASURED", row["detail"])
        self.assertIn("not a console with no log yet", row["detail"])
        self.assertNotIn("(no log yet)", row["detail"])

    def test_a_missing_file_on_the_doctor_is_still_no_log_yet(self):
        tail, why, extra = ca._doctor_log_fields(
            {"ok": True, "log": "(no log yet)", "why": None})
        self.assertEqual(tail, "(no log yet)")
        self.assertIsNone(why)
        self.assertEqual(extra, [])

    def test_a_real_tail_on_the_doctor_is_still_the_tail(self):
        tail, why, extra = ca._doctor_log_fields(
            {"ok": True, "log": "booted\n", "why": None})
        self.assertEqual(tail, "booted\n")
        self.assertIsNone(why)
        self.assertEqual(extra, [])

    def test_a_read_that_did_not_answer_is_not_measured(self):
        tail, why, extra = ca._doctor_log_fields(None)
        self.assertIsNone(tail)
        self.assertIn("did not answer", why)
        self.assertIs(extra[0]["ok"], False)
        self.assertEqual(extra[0]["severity"], "warn")

    def test_the_doctor_applies_the_log_before_ok(self):
        src = inspect.getsource(ca.doctor_payload)
        call = src.find("_doctor_log_fields(_console_log_read(2048))")
        ok_at = src.find("ok = not any")
        self.assertGreater(call, 0)
        self.assertGreater(ok_at, call)
        self.assertIn('"logWhy": log_why', src)
        self.assertNotIn('log_tail = "(no log yet)"', src)

    def test_the_log_route_returns_the_read(self):
        src = inspect.getsource(ca.Handler.do_GET)
        start = src.find('if path == "/api/log":')
        end = src.find('if path == "/api/update":', start)
        self.assertGreater(start, 0)
        self.assertGreater(end, start)
        window = src[start:end]
        self.assertIn("_console_log_read(12000)", window)
        self.assertNotIn("(no log yet)", window)
        self.assertNotIn('"ok": True', window)

    def test_the_screen_does_not_call_an_unread_log_empty(self):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        start = ui.find("async function loadLog()")
        self.assertGreater(start, 0)
        end = ui.find("\n  }\n", start)           # REG-1842: loadLog's own close, not a guessed width
        self.assertGreater(end, start, "loadLog's end moved")
        window = ui[start:end]
        self.assertIn("j.ok === false", window)
        why_at = window.find("not a console with no log yet")
        empty_at = window.find("— empty log —")
        self.assertGreater(why_at, 0)
        self.assertGreater(empty_at, why_at)


RED_PROOF = [
    {
        "why": "REG-1824 - an unread log is graded a block again, so the boot-failure toast names it a blocker",
        "file": "control_app.py",
        "find": "        \"console_log\", False, \"warn\",\n",
        "replace": "        \"console_log\", False, \"block\",\n",
        "matches": 1,
    },
    {
        "why": "REG-1800 - a missing file is filed as a failed read",
        "file": "control_app.py",
        "find": "    except FileNotFoundError:\n"
                "        return {\"ok\": True, \"log\": \"(no log yet)\", \"why\": None}\n",
        "replace": "    except FileNotFoundError:\n"
                   "        return {\"ok\": False, \"log\": None, \"why\": \"missing\"}\n",
        "matches": 1,
    },
    {
        "why": "REG-1800 - a failed read is painted as no log yet",
        "file": "control_app.py",
        "find": "        # REG-1800 — a failed read is not a console with no log yet.\n"
                "        return {\"ok\": False, \"log\": None, \"why\": _why_of(exc)}\n",
        "replace": "        # REG-1800 — a failed read is not a console with no log yet.\n"
                   "        return {\"ok\": True, \"log\": \"(no log yet)\", \"why\": None}\n",
        "matches": 1,
    },
    {
        "why": "REG-1800 - the doctor paints an unread log as no log yet and adds no row",
        "file": "control_app.py",
        "find": "    return None, why, [_chk(\n"
                "        \"console_log\", False, \"warn\",\n"
                "        _us.unmeasured(\"the log was not read\", why, \"a console with no log yet\"),\n"
                "        \"Read the console log at the path this doctor names.\")]\n",
        "replace": "    return \"(no log yet)\", None, []\n",
        "matches": 1,
    },
    {
        "why": "REG-1800 - the log route forces ok true and the absent string",
        "file": "control_app.py",
        "find": "            self._json(200, _console_log_read(12000))\n",
        "replace": "            self._json(200, {\"ok\": True, \"log\": \"(no log yet)\"})\n",
        "matches": 1,
    },
    {
        "why": "REG-1800 - the screen calls an unread log an empty log again",
        "file": "control_ui.html",
        "find": "      if (!j || j.ok === false) {\n"
                "        brain.innerHTML = '<div class=\"empty\">UNMEASURED: the log was not read ('\n"
                "          + esc((j && j.why) || 'no reason') + ') — not a console with no log yet</div>';\n"
                "        return;\n"
                "      }\n",
        "replace": "      if (false) {\n"
                   "        brain.innerHTML = '<div class=\"empty\">measured</div>';\n"
                   "        return;\n"
                   "      }\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
