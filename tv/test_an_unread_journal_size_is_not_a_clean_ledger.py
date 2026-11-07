# -*- coding: utf-8 -*-
"""REG-1803 — AN UNREAD JOURNAL SIZE IS NOT A CLEAN LEDGER.

The ledger organ asked os.path.isfile. isfile returns False when the directory
will not stat. False is also a journal that was never written, so the poll
said 0.0 MB and the organ said the journal was clean, with its pulse ok.

A missing file is 0.0. A blank file is 0.0. A real file is its size. A
directory that will not stat, a path that is not a file, and an IO error are
not that empty. The poll says null. The organ says the size was not read, and
its pulse is not ok.

Nothing here reads his journal. RED_PROOF below. [[unknown-stays-unknown]]
"""
import inspect
import json
import os

#: #107 - chmod(0) makes a file or directory unreadable only where POSIX modes hold; on Windows it only sets
#: read-only, so a case built on it measures nothing there (its door is pinned by the io-error cases)
_POSIX_MODES = os.name != "nt"
import shutil
import subprocess
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


def _ledger(journal_mb, violations=0):
    with open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
        ui = fh.read()
    start = ui.find("var _EH_STATE = { ok: 'HEALTHY'")
    end = ui.find("function _ehOrganHtml", start)
    if start < 0 or end < 0:
        raise AssertionError("the ledger organ is not in control_ui.html")
    fn = ui[start:end]
    if "\x00" in fn:
        raise AssertionError("the organ slice crossed the null byte")
    lit = "null" if journal_mb is None else json.dumps(journal_mb)
    js = (
        "function esc(s){return String(s==null?'':s);}\n"
        + fn
        + "var o=_engineOrganData({journalMB:" + lit
        + ",watchdog:{violations:" + str(int(violations))
        + "},sessionHealth:{},driver:{},eyes:{}});\n"
        + "var led=o.filter(function(x){return x.key==='ledger';})[0];\n"
        + "process.stdout.write(JSON.stringify({pulse:led.pulse,stat:led.stat,"
        + "sub:led.sub,state:led.state}));\n"
    )
    got = subprocess.run(
        ["node", "-"], input=js.encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if got.returncode != 0:
        raise AssertionError(got.stderr.decode("utf-8", "replace")[:600])
    return json.loads(got.stdout.decode("utf-8"))


class AnUnreadJournalSizeIsNotACleanLedger(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="journal1803_")

    def tearDown(self):
        try:
            os.chmod(self.tmp, 0o755)
        except OSError:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _at(self, name):
        return os.path.join(self.tmp, name)

    def _ask(self, path):
        with mock.patch.object(ca, "_journal_path", lambda: path):
            return ca._journal_megabytes()

    def test_a_missing_file_is_still_zero(self):
        got = self._ask(self._at("never_written.jsonl"))
        self.assertEqual(got, 0.0)
        self.assertIsNotNone(got)

    def test_a_blank_file_is_still_zero(self):
        path = self._at("sessions.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n\n   \n")
        self.assertEqual(self._ask(path), 0.0)

    def test_a_real_file_is_still_its_size(self):
        path = self._at("sessions.jsonl")
        with open(path, "wb") as fh:
            fh.write(b"x" * 1500000)
        self.assertEqual(self._ask(path), 1.5)

    @unittest.skipUnless(_POSIX_MODES, "chmod(0) cannot make a path unreadable on Windows")
    def test_a_directory_that_will_not_stat_is_not_zero(self):
        os.chmod(self.tmp, 0)
        try:
            got = self._ask(self._at("sessions.jsonl"))
        finally:
            os.chmod(self.tmp, 0o755)
        self.assertIsNone(got)

    def test_a_path_that_is_not_a_file_is_not_a_measured_size(self):
        path = self._at("sessions.jsonl")
        os.mkdir(path)
        self.assertIsNone(self._ask(path))

    def test_an_io_error_is_not_zero(self):
        path = self._at("sessions.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("")
        with mock.patch("os.stat", side_effect=OSError("disk went away")):
            got = self._ask(path)
        self.assertIsNone(got)

    def test_the_poll_asks_this_look(self):
        src = inspect.getsource(ca.status_payload)
        self.assertIn('"journalMB": _t("journalMB", _journal_megabytes),', src)
        self.assertNotIn("os.path.isfile(_journal_path())", src)
        # REG-1824 — the size's look is _file_look's, the one stat-or-why the journal readers
        # share. This pinned the TEXT of a hand-rolled copy; the claim is what the look answers.
        with mock.patch.object(ca, "_file_look", lambda *_a, **_k: (None, "OSError: from the look")):
            self.assertIsNone(self._ask(self._at("sessions.jsonl")))
        with mock.patch.object(ca, "_file_look", lambda *_a, **_k: (None, None)):
            self.assertEqual(self._ask(self._at("sessions.jsonl")), 0.0)

    def test_an_empty_journal_still_reads_clean(self):
        led = _ledger(0.0)
        self.assertEqual(led["pulse"], "ok")
        self.assertEqual(led["state"], "HEALTHY")
        self.assertEqual(led["sub"], "journal clean")
        self.assertEqual(led["stat"], "0 MB")
        self.assertNotIn("was not read", led["sub"])

    def test_a_real_size_is_still_that_size(self):
        led = _ledger(1.5)
        self.assertEqual(led["pulse"], "ok")
        self.assertEqual(led["sub"], "journal clean")
        self.assertEqual(led["stat"], "1.5 MB")

    def test_an_unread_size_is_not_a_clean_ledger(self):
        led = _ledger(None)
        # REG-1824 — not read is UNKNOWN, not a strained organ that was measured.
        self.assertEqual(led["pulse"], "unknown")
        self.assertEqual(led["state"], "UNKNOWN")
        self.assertEqual(led["sub"], "the journal size was not read")
        self.assertNotIn("journal clean", led["sub"])
        self.assertNotIn("0", led["stat"])
        self.assertNotIn("MB", led["stat"])

    def test_a_measured_breach_is_still_a_breach(self):
        led = _ledger(1.5, violations=2)
        self.assertEqual(led["pulse"], "warn")
        self.assertEqual(led["sub"], "2 watchdog breach")
        self.assertIn("1.5 MB", led["stat"])
        self.assertNotIn("was not read", led["sub"])


RED_PROOF = [
    {
        "why": "REG-1803 - a failed stat is filed as an empty journal",
        "file": "control_app.py",
        "find": "    if why:\n"
                "        return None\n"
                "    return 0.0 if st is None else round(st.st_size / 1e6, 1)\n",
        "replace": "    if why:\n"
                   "        return 0.0\n"
                   "    return 0.0 if st is None else round(st.st_size / 1e6, 1)\n",
        "matches": 1,
    },
    {
        "why": "REG-1803 - a missing journal is filed as a failed read",
        "file": "control_app.py",
        "find": "    return 0.0 if st is None else round(st.st_size / 1e6, 1)\n",
        "replace": "    return None if st is None else round(st.st_size / 1e6, 1)\n",
        "matches": 1,
    },
    {
        "why": "REG-1803 - a path that is not a file counts as a measured size",
        "file": "control_app.py",
        "find": "    if not stat.S_ISREG(st.st_mode):\n"
                "        return None, \"not a %s\" % what\n"
                "    return st, None\n",
        "replace": "    return st, None\n",
        "matches": 1,
    },
    {
        "why": "REG-1803 - the poll asks isfile and paints a missing journal as 0.0",
        "file": "control_app.py",
        "find": '        "journalMB": _t("journalMB", _journal_megabytes),\n',
        "replace": '        "journalMB": (0.0 if not os.path.isfile(_journal_path()) else _journal_megabytes()),\n',
        "matches": 1,
    },
    {
        "why": "REG-1803 - an unread size is painted as a clean ledger",
        "file": "control_ui.html",
        "find": "    var journalUnread = (st.journalMB == null);\n",
        "replace": "    var journalUnread = false;\n",
        "matches": 1,
    },
    {
        "why": "REG-1803 - the screen calls an unread size a clean journal",
        "file": "control_ui.html",
        "find": "      ? 'the journal size was not read'\n",
        "replace": "      ? 'journal clean'\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
