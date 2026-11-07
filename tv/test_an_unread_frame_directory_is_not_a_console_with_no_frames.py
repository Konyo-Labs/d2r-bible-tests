# -*- coding: utf-8 -*-
"""REG-1801 — AN UNREAD FRAME DIRECTORY IS NOT A CONSOLE WITH NO FRAMES YET.

The live-frame check asked os.path.isfile. isfile returns False when the
directory will not stat. False is also a frame that was never written, so the
row said "no frames yet (agent off)" with ok true. While live with capture
off, it said no frame was expected.

A missing directory is that empty. An empty directory is that empty. A frame
that stats is its age. A directory that will not stat, a path that is not a
directory, and an IO error are not that empty. The row is never ok. While
LIVE it is a block, so the doctor's ok cannot stay true, and the toast prints
its detail, which is where the screen says the frames were not read. Off air
it warns (REG-1824): the check's own contract is that frames block only when
LIVE, and an unread directory off air owes no frame. It does not say the
capture is frozen.

Nothing here reads his live frames, and nothing starts a capture.
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
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import control_app as ca  # noqa: E402


class AnUnreadFrameDirectoryIsNotAConsoleWithNoFrames(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="frames1801_")
        self._was = os.environ.get("TV_CAPTURE")

    def tearDown(self):
        try:
            os.chmod(self.tmp, 0o755)
        except OSError:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)
        if self._was is None:
            os.environ.pop("TV_CAPTURE", None)
        else:
            os.environ["TV_CAPTURE"] = self._was

    def test_a_missing_directory_is_still_no_frames(self):
        missing = os.path.join(self.tmp, "never_filmed")
        got = ca._live_frame_look(missing)
        self.assertEqual(got, {"ok": True, "ages": [], "newest": None, "why": None})
        os.environ["TV_CAPTURE"] = "auto"
        row = ca._live_frames_check(False, missing)
        self.assertIs(row["ok"], True, row)
        self.assertEqual(row["detail"], "no frames yet (agent off)")

    def test_an_empty_directory_is_still_no_frames(self):
        got = ca._live_frame_look(self.tmp)
        self.assertIs(got["ok"], True, got)
        self.assertEqual(got["ages"], [])
        self.assertIsNone(got["why"])

    def test_a_frame_that_stats_is_still_its_age(self):
        path = os.path.join(self.tmp, "eye.jpg")
        with open(path, "wb") as fh:
            fh.write(b"")
        got = ca._live_frame_look(self.tmp, now=time.time() + 1)
        self.assertIs(got["ok"], True, got)
        self.assertIsNone(got["why"])
        self.assertEqual(len(got["ages"]), 1)
        self.assertTrue(got["ages"][0].startswith("eye.jpg="), got)
        os.environ["TV_CAPTURE"] = "auto"
        row = ca._live_frames_check(False, self.tmp)
        self.assertIs(row["ok"], True, row)
        self.assertIn("eye.jpg=", row["detail"])
        self.assertNotIn("no frames yet", row["detail"])
        self.assertNotIn("UNMEASURED", row["detail"])

    def test_a_stale_frame_while_live_is_still_stale(self):
        path = os.path.join(self.tmp, "live.jpg")
        with open(path, "wb") as fh:
            fh.write(b"x")
        old = time.time() - 30
        os.utime(path, (old, old))
        os.environ["TV_CAPTURE"] = "auto"
        row = ca._live_frames_check(True, self.tmp)
        self.assertIs(row["ok"], False, row)
        self.assertEqual(row["severity"], "block")
        self.assertIn("frames stale", row["detail"])
        self.assertNotIn("UNMEASURED", row["detail"])
        self.assertNotIn("no frames yet", row["detail"])

    def test_a_live_console_with_no_frame_still_blocks(self):
        os.environ["TV_CAPTURE"] = "auto"
        row = ca._live_frames_check(True, self.tmp)
        self.assertIs(row["ok"], False, row)
        self.assertEqual(row["severity"], "block")
        self.assertIn("no eye.jpg / live frame while LIVE", row["detail"])

    def test_capture_off_with_no_frame_is_still_not_frozen(self):
        os.environ["TV_CAPTURE"] = "off"
        row = ca._live_frames_check(True, self.tmp)
        self.assertIs(row["ok"], True, row)
        self.assertIn("OFF by this console's setting", row["detail"])
        self.assertNotIn("UNMEASURED", row["detail"])

    @unittest.skipUnless(_POSIX_MODES, "chmod(0) cannot make a path unreadable on Windows")
    def test_a_directory_that_will_not_stat_is_not_no_frames(self):
        os.chmod(self.tmp, 0)
        try:
            got = ca._live_frame_look(self.tmp)
        finally:
            os.chmod(self.tmp, 0o755)
        self.assertIs(got["ok"], False, got)
        self.assertEqual(got["ages"], [])
        self.assertIsNone(got["newest"])
        self.assertIn("PermissionError", got["why"])
        self.assertNotIn("eye.jpg=", got["why"])

    @unittest.skipUnless(_POSIX_MODES, "chmod(0) cannot make a path unreadable on Windows")
    def test_the_check_does_not_call_an_unread_directory_empty(self):
        os.chmod(self.tmp, 0)
        try:
            os.environ["TV_CAPTURE"] = "off"
            row = ca._live_frames_check(True, self.tmp)
            quiet = ca._live_frames_check(False, self.tmp)
        finally:
            os.chmod(self.tmp, 0o755)
        for got, severity in ((row, "block"), (quiet, "warn")):
            self.assertIs(got["ok"], False, got)
            self.assertEqual(got["severity"], severity, got)
            self.assertEqual(got["id"], "live_frames")
            self.assertIn("UNMEASURED", got["detail"])
            self.assertIn("PermissionError", got["detail"])
            self.assertIn("not a console with no frames yet", got["detail"])
            self.assertNotIn("no frames yet (agent off)", got["detail"])
            self.assertNotIn("OFF by this console's setting", got["detail"])
            self.assertNotIn("Capture is frozen", got["detail"])
            self.assertNotIn("no eye.jpg", got["detail"])
        doctor_ok = not any((not c["ok"]) and c["severity"] == "block" for c in [row])
        self.assertIs(doctor_ok, False)
        # REG-1824 — off air the unread row is not a pass, and it is not a NO-GO either.
        off_air_ok = not any((not c["ok"]) and c["severity"] == "block" for c in [quiet])
        self.assertIs(off_air_ok, True)

    def test_a_file_path_is_not_no_frames_the_way_windows_answers_too(self):
        """#107 (v3880) - Windows stats a name under a FILE as FileNotFoundError, not NotADirectoryError, so the frames path
        being a file read as "no frames yet" there. Windows' answer is stood in here, on every platform."""
        from unittest import mock
        path = os.path.join(self.tmp, "a_file_not_a_dir")
        with open(path, "wb") as fh:
            fh.write(b"x")
        def windows_stat(fp):
            raise FileNotFoundError(3, "The system cannot find the path specified", fp)
        with mock.patch.object(ca.os.path, "getmtime", windows_stat):
            got = ca._live_frame_look(path)
        self.assertIs(got["ok"], False, got)
        self.assertIn("NotADirectoryError", got["why"])

    def test_a_path_that_is_not_a_directory_is_not_no_frames(self):
        path = os.path.join(self.tmp, "not_a_dir")
        with open(path, "wb") as fh:
            fh.write(b"x")
        got = ca._live_frame_look(path)
        self.assertIs(got["ok"], False, got)
        self.assertIn("NotADirectoryError", got["why"])
        row = ca._live_frames_check(False, path)
        self.assertIs(row["ok"], False, row)
        self.assertNotIn("no frames yet (agent off)", row["detail"])

    def test_an_io_error_is_not_no_frames(self):
        with mock.patch("os.path.getmtime", side_effect=OSError("disk went away")):
            got = ca._live_frame_look(self.tmp)
        self.assertIs(got["ok"], False, got)
        self.assertIn("OSError", got["why"])
        self.assertIn("disk went away", got["why"])
        self.assertNotIn("no frames yet", got["why"] or "")

    def test_the_doctor_asks_this_look_before_ok(self):
        src = inspect.getsource(ca.doctor_payload)
        call = src.find("_live_frames_check(")
        ok_at = src.find("ok = not any")
        self.assertGreater(call, 0)
        self.assertGreater(ok_at, call)
        look = inspect.getsource(ca._live_frame_look)
        self.assertIn('for label in ("eye.jpg", "live.jpg", "live.png", "live.bmp")', look)
        self.assertNotIn("os.path.isfile", look)
        check = inspect.getsource(ca._live_frames_check)
        self.assertIn('if look["ok"] is False:', check)

    def test_the_screen_prints_a_block_detail(self):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        start = ui.find("function renderDoctor")
        self.assertGreater(start, 0)
        end = ui.find("\n  }\n", start)           # REG-1842: the function's own close, not a guessed width
        self.assertGreater(end, start, "renderDoctor's end moved")
        window = ui[start:end]
        self.assertIn("c.severity === 'block' && c.ok === false", window)
        self.assertIn("c.detail", window)


RED_PROOF = [
    {
        "why": "REG-1824 - an unread frame directory blocks off air, against the check's blocks-only-when-LIVE contract",
        "file": "control_app.py",
        "find": "            \"live_frames\", False, (\"block\" if live else \"warn\"),\n",
        "replace": "            \"live_frames\", False, \"block\",\n",
        "matches": 1, "needs": "posix",
    },
    {
        "why": "REG-1801 - a failed stat is skipped, so an unreadable directory looks like no frames",
        "file": "control_app.py",
        "find": "        except Exception as exc:\n"
                "            # REG-1801 — a failed stat is not a console with no frames yet.\n"
                "            return {\"ok\": False, \"ages\": [], \"newest\": None, \"why\": _why_of(exc)}\n",
        "replace": "        except Exception:\n"
                   "            continue\n",
        "matches": 1,
    },
    {
        "why": "REG-1801 - the check drops the unread door and falls through to no frames yet",
        "file": "control_app.py",
        "find": "    look = _live_frame_look(frames_dir)\n"
                "    if look[\"ok\"] is False:\n",
        "replace": "    look = _live_frame_look(frames_dir)\n"
                   "    if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-1801 - a missing frame is filed as a failed read",
        "file": "control_app.py",
        "find": "            age = now - os.path.getmtime(fp)\n"
                "        except FileNotFoundError:\n"
                "            continue\n",
        "replace": "            age = now - os.path.getmtime(fp)\n"
                   "        except FileNotFoundError:\n"
                   "            return {\"ok\": False, \"ages\": [], \"newest\": None, \"why\": \"missing\"}\n",
        "matches": 1,
    },
    {"why": "#107 - on Windows a frames path that is a file reads as no frames yet again",
     "file": "control_app.py",
     "find": "    if not ages and os.path.exists(frames_dir) and not os.path.isdir(frames_dir):\n",
     "replace": "    if False:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
