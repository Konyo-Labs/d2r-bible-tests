# -*- coding: utf-8 -*-
"""REG-1802 — AN UNREAD JOURNAL IS NOT A NIGHT WITH NO ROWS YET.

The replay row and the generation row asked os.path.isfile. isfile returns
False when the directory will not stat. False is also a journal that was
never written, so the rows said "no journal rows yet" and "live=no gens=none"
with ok true.

A missing file is that empty. A blank file is that empty. A real beat is its
coverage. A rotated file that is there is counted. A directory that will not
stat, a path that is not a file, and an IO error are not that empty. The row
is the same warn it already uses when the path raises, so an off-air night is
not a new block. The toast only prints blocks, so this row is not a toast.

Nothing here reads his journal. RED_PROOF below. [[unknown-stays-unknown]]
"""
import inspect
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
import fixture_tmp as _fx_tmp  # noqa: E402  #173 - its scratch is its own, so listing it keeps the law keyable
_fx_tmp.contain()

import control_app as ca  # noqa: E402


def _rows(calls):
    return {c["id"]: c for c in calls}


class AnUnreadJournalIsNotANightWithNoRows(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="journal1802_")

    def tearDown(self):
        try:
            os.chmod(self.tmp, 0o755)
        except OSError:
            pass
        for name in _fx_tmp.list_own(self.tmp):
            path = os.path.join(self.tmp, name)
            try:
                os.chmod(path, 0o755)
            except OSError:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _at(self, name):
        return os.path.join(self.tmp, name)

    def _ask(self, path):
        with mock.patch.object(ca, "_journal_path", lambda: path):
            return _rows(ca._journal_doctor_rows())

    def _assert_unread(self, rows, needle):
        for cid, empty in (
            ("session_integrity", "no journal rows yet"),
            ("journal_gens", "live=no"),
        ):
            got = rows[cid]
            self.assertIs(got["ok"], False, got)
            self.assertEqual(got["severity"], "warn")
            self.assertIn("could not be measured", got["detail"])
            self.assertIn("UNKNOWN", got["detail"])
            self.assertIn(needle, got["detail"])
            self.assertNotIn(empty, got["detail"])
            self.assertNotIn("live=yes", got["detail"])
            self.assertNotIn("gens=none", got["detail"])
        doctor_ok = not any(
            (not c["ok"]) and c["severity"] == "block" for c in rows.values())
        self.assertIs(doctor_ok, True, rows)

    def test_a_missing_file_is_still_no_rows(self):
        rows = self._ask(self._at("never_written.jsonl"))
        self.assertIs(rows["session_integrity"]["ok"], True, rows["session_integrity"])
        self.assertEqual(rows["session_integrity"]["detail"], "no journal rows yet")
        self.assertIs(rows["journal_gens"]["ok"], True, rows["journal_gens"])
        self.assertEqual(rows["journal_gens"]["detail"], "live=no gens=none")
        self.assertNotIn("could not be measured", rows["session_integrity"]["detail"])
        self.assertNotIn("could not be measured", rows["journal_gens"]["detail"])

    def test_a_blank_file_is_still_empty(self):
        path = self._at("sessions.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n\n   \n")
        rows = self._ask(path)
        self.assertIs(rows["session_integrity"]["ok"], True, rows["session_integrity"])
        self.assertEqual(rows["session_integrity"]["detail"], "no journal rows yet")
        self.assertEqual(rows["journal_gens"]["detail"], "live=yes gens=none")

    def test_a_real_beat_is_still_its_coverage(self):
        path = self._at("sessions.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"frameId": "no_such_frame", "sessionId": "s1"}) + "\n")
        rows = self._ask(path)
        got = rows["session_integrity"]
        self.assertIs(got["ok"], False, got)
        self.assertIn("frames 0%", got["detail"])
        self.assertIn("sessionId 1/1", got["detail"])
        self.assertNotIn("could not be measured", got["detail"])
        self.assertNotIn("no journal rows yet", got["detail"])
        self.assertEqual(rows["journal_gens"]["detail"], "live=yes gens=none")

    def test_a_rotated_file_is_still_counted(self):
        path = self._at("sessions.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("")
        with open(self._at("sessions.1.jsonl"), "w", encoding="utf-8") as fh:
            fh.write("")
        with open(self._at("sessions.3.jsonl"), "w", encoding="utf-8") as fh:
            fh.write("")
        rows = self._ask(path)
        self.assertEqual(rows["journal_gens"]["detail"], "live=yes gens=1,3")
        self.assertIs(rows["journal_gens"]["ok"], True, rows["journal_gens"])

    def test_a_directory_that_will_not_stat_is_not_no_rows(self):
        os.chmod(self.tmp, 0)
        try:
            rows = self._ask(self._at("sessions.jsonl"))
        finally:
            os.chmod(self.tmp, 0o755)
        self._assert_unread(rows, "Permission denied")

    def test_a_path_that_is_not_a_file_is_not_a_live_journal(self):
        path = self._at("sessions.jsonl")
        os.mkdir(path)
        rows = self._ask(path)
        self._assert_unread(rows, "not a journal file")

    def test_a_rotated_path_that_is_not_a_file_does_not_wipe_the_replay(self):
        path = self._at("sessions.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"frameId": "no_such_frame", "sessionId": "s1"}) + "\n")
        os.mkdir(self._at("sessions.1.jsonl"))
        rows = self._ask(path)
        got = rows["session_integrity"]
        self.assertIn("frames 0%", got["detail"])
        self.assertNotIn("could not be measured", got["detail"])
        self.assertNotIn("no journal rows yet", got["detail"])
        gens = rows["journal_gens"]
        self.assertIs(gens["ok"], False, gens)
        self.assertEqual(gens["severity"], "warn")
        self.assertIn("not a journal file", gens["detail"])
        self.assertNotIn("gens=none", gens["detail"])
        self.assertNotIn("gens=1", gens["detail"])
        self.assertNotIn("live=yes", gens["detail"])

    def test_an_io_error_is_not_no_rows(self):
        path = self._at("sessions.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("")
        with mock.patch("os.stat", side_effect=OSError("disk went away")):
            rows = self._ask(path)
        self._assert_unread(rows, "disk went away")

    def test_a_file_that_will_not_open_is_not_no_rows(self):
        path = self._at("sessions.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{}\n")
        os.chmod(path, 0)
        try:
            rows = self._ask(path)
        finally:
            os.chmod(path, 0o644)
        got = rows["session_integrity"]
        self.assertIs(got["ok"], False, got)
        self.assertIn("could not be measured", got["detail"])
        self.assertIn("Permission denied", got["detail"])
        self.assertNotIn("no journal rows yet", got["detail"])
        self.assertEqual(rows["journal_gens"]["detail"], "live=yes gens=none")

    def test_the_doctor_asks_the_one_reader(self):
        """REG-1824 — this pinned TEXT: `assertIn("return False", look)` passed on any such line, and
        `assertNotIn("os.path.isfile(_jl)")` would trip on a comment quoting the old code. The claim
        is behaviour: the doctor's replay row is whatever the one journal reader says, and the
        doctor applies both rows before it decides ok."""
        said = {"rows": [], "why": "PermissionError: from the one reader", "lines": 0, "torn": 0}
        with mock.patch.object(ca, "_journal_read", lambda **_k: said), \
                mock.patch.object(ca, "_journal_path", lambda: self._at("never_written.jsonl")):
            rows = _rows(ca._journal_doctor_rows())
        got = rows["session_integrity"]
        self.assertIs(got["ok"], False, got)
        self.assertIn("from the one reader", got["detail"])
        self.assertNotIn("no journal rows yet", got["detail"])
        torn = {"rows": [], "why": "the journal opened and none of its 2 line(s) parsed",
                "lines": 2, "torn": 2}
        with mock.patch.object(ca, "_journal_read", lambda **_k: torn), \
                mock.patch.object(ca, "_journal_path", lambda: self._at("never_written.jsonl")):
            rows = _rows(ca._journal_doctor_rows())
        self.assertIn("2 journal line(s) in the tail would not parse", rows["session_integrity"]["detail"])
        pay = inspect.getsource(ca.doctor_payload)
        call = pay.find("checks.extend(_journal_doctor_rows())")
        ok_at = pay.find("ok = not any")
        self.assertGreater(call, 0)
        self.assertGreater(ok_at, call)

    def test_absent_is_false_and_anything_else_is_not(self):
        missing = self._at("nope.jsonl")
        self.assertIs(ca._journal_file_there(missing), False)
        path = self._at("sessions.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("")
        self.assertIs(ca._journal_file_there(path), True)
        os.mkdir(self._at("not_a_file.jsonl"))
        with self.assertRaises(OSError):
            ca._journal_file_there(self._at("not_a_file.jsonl"))
        with mock.patch("os.stat", side_effect=OSError("disk went away")):
            with self.assertRaises(OSError):
                ca._journal_file_there(path)


RED_PROOF = [
    {
        "why": "REG-1802 - a failed stat is filed as a journal that is not there",
        "file": "control_app.py",
        "find": "    except OSError as exc:\n"
                "        return None, _why_of(exc)\n"
                "    if not stat.S_ISREG(st.st_mode):\n",
        "replace": "    except OSError as exc:\n"
                   "        return None, None\n"
                   "    if not stat.S_ISREG(st.st_mode):\n",
        "matches": 1,
    },
    {
        "why": "REG-1802 - a missing journal is filed as a failed read",
        "file": "control_app.py",
        "find": "    except FileNotFoundError:\n"
                "        return None, None\n"
                "    except OSError as exc:\n",
        "replace": "    except FileNotFoundError:\n"
                   "        return None, \"missing\"\n"
                   "    except OSError as exc:\n",
        "matches": 1,
    },
    {
        "why": "REG-1802 - a path that is not a file counts as a live journal",
        "file": "control_app.py",
        "find": "    if not stat.S_ISREG(st.st_mode):\n"
                "        return None, \"not a %s\" % what\n"
                "    return st, None\n",
        "replace": "    return st, None\n",
        "matches": 1,
    },
    {
        "why": "REG-1824 - the doctor reads its own tail again instead of the one reader's answer",
        "file": "control_app.py",
        "find": "        _tail = _journal_read(tail_lines=200)\n",
        "replace": "        _tail = {\"rows\": [], \"why\": None, \"lines\": 0, \"torn\": 0}\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
