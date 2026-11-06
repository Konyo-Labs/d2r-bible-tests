# -*- coding: utf-8 -*-
"""#227 / REG-1260 — A SELF-UPDATED CONSOLE CAN READ ITS OWN FRAMES.

MEASURED 2026-09-24 over SSH on the Windows ALT: its tree held the launcher's Pillow step (6ed85ece),
its consoles were started at 20:26 and 21:06, and Pillow was still missing - start_tvd_win.log's last
line was 19:04. Every later start was the console's own os.execv after a self-update, which never runs
start_tvd_win.ps1. So the console now makes sure of Pillow itself, at boot.

  · DRIVEN: on Windows with PIL absent, the boot step runs `python.exe -m pip install --user Pillow`
    (never pythonw), hidden, and records the attempt on console_doctor.PILLOW_BOOT.
  · DRIVEN: PIL present -> no pip at all. Not Windows, or a scratch console -> nothing.
  · DRIVEN: a pip failure is recorded as a failure, with pip's words - never as "installed".
  · DRIVEN: the doctor row, with PIL unimportable, quotes the boot attempt - and no longer promises
    that the launcher will install it.
  · COMPILER: main() starts the step in its own thread.
RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import console_doctor as cd  # noqa: E402
import control_app as ca  # noqa: E402
import win_relaunch as wr  # noqa: E402


class _P(object):
    def __init__(self, rc, err=""):
        self.returncode, self.stderr, self.stdout = rc, err, ""


class ASelfUpdatedConsoleCanReadItsFrames(unittest.TestCase):

    def setUp(self):
        self._win, self._exe = ca.IS_WIN, sys.executable
        self._scratch = wr.scratch_console
        self._boot = cd.PILLOW_BOOT
        self._nboot = cd.NUMPY_BOOT
        ca.IS_WIN = True
        wr.scratch_console = lambda *a, **k: False
        sys.executable = r"C:\Py\pythonw.exe"
        self.calls = []
        self.present = [False]

    def tearDown(self):
        ca.IS_WIN, sys.executable = self._win, self._exe
        wr.scratch_console = self._scratch
        cd.PILLOW_BOOT = self._boot
        cd.NUMPY_BOOT = self._nboot

    def _find(self, name):
        return object() if self.present[0] else None

    def _run(self, rc=0, err="", becomes=True):
        def run(argv, **kw):
            self.calls.append((argv, kw))
            if rc == 0 and becomes:
                self.present[0] = True
            return _P(rc, err)
        return run

    def test_a_missing_pillow_is_installed_by_the_console_itself(self):
        rec = ca._ensure_pillow_at_boot(_find=self._find, _run=self._run())
        self.assertEqual(len(self.calls), 1, "the console never tried to install Pillow")
        argv, kw = self.calls[0]
        self.assertEqual(argv[0], r"C:\Py\python.exe", "pip must run under python.exe, never pythonw")
        self.assertEqual(argv[1:], ["-m", "pip", "install", "--user", "--quiet", "Pillow"])
        self.assertEqual(kw.get("creationflags"), ca._WIN_CREATE, "the install would flash a window on his screen")
        self.assertIs(rec.get("ok"), True)
        self.assertIs(cd.PILLOW_BOOT, rec, "the doctor cannot see the attempt")

    def test_the_install_this_process_made_is_still_said_when_the_book_asks(self):
        """REG-3268 (the Grok CLI on REG-3158) - the book's later call replaced the boot install's record: 'fine', never 'fixed'."""
        first = ca._ensure_pillow_at_boot(_find=self._find, _run=self._run())
        self.assertIs(first.get("tried"), True)
        later = ca._ensure_pillow_at_boot(_find=self._find, _run=self._run())
        self.assertIs(later.get("tried"), True, "the install that fired was forgotten when the book asked: %r" % later)
        self.assertEqual(ca._book_rec(later, "tried", "x")[0], "fixed")
        self.assertEqual(len(self.calls), 1, "a present package was installed again")

    def test_present_pillow_is_left_alone(self):
        self.present[0] = True
        rec = ca._ensure_pillow_at_boot(_find=self._find, _run=self._run())
        self.assertEqual(self.calls, [])
        self.assertIs(rec.get("tried"), False)

    def test_not_windows_or_scratch_does_nothing(self):
        ca.IS_WIN = False
        self.assertIsNone(ca._ensure_pillow_at_boot(_find=self._find, _run=self._run()))
        ca.IS_WIN = True
        wr.scratch_console = lambda *a, **k: True
        self.assertIsNone(ca._ensure_pillow_at_boot(_find=self._find, _run=self._run()))
        self.assertEqual(self.calls, [], "a scratch console installed packages on the runner")

    def test_a_failed_pip_is_a_failure_with_its_words(self):
        rec = ca._ensure_pillow_at_boot(_find=self._find, _run=self._run(rc=1, err="no network"))
        self.assertIs(rec.get("ok"), False)
        self.assertIn("no network", rec.get("why") or "")

    def test_the_row_quotes_the_boot_attempt_and_promises_no_launcher(self):
        cd.PILLOW_BOOT = {"tried": True, "ok": False, "why": "pip exited 1: no network"}
        real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

        def no_pil(name, *a, **k):
            if name == "PIL" or name.startswith("PIL."):
                raise ImportError("No module named 'PIL'")
            return real_import(name, *a, **k)
        import builtins
        builtins.__import__ = no_pil
        try:
            state, why = cd._check_this_machine_can_decode_a_frame()
        finally:
            builtins.__import__ = real_import
        self.assertEqual(state, cd.MISSING)
        self.assertIn("tried to install it at boot", why)
        self.assertIn("no network", why)
        self.assertNotIn("launcher installs it", why, "the row still promises a launcher run that a self-updated console never makes")

    def test_REG1719_a_missing_numpy_is_installed_by_the_console_itself(self):
        """the ALT on v3556 had no numpy: every inventory lattice there answered 'unreadable'"""
        rec = ca._ensure_numpy_at_boot(_find=self._find, _run=self._run())
        self.assertEqual(len(self.calls), 1, "the console never tried to install numpy")
        argv, kw = self.calls[0]
        self.assertEqual(argv[1:], ["-m", "pip", "install", "--user", "--quiet", "numpy"])
        self.assertEqual(argv[0], r"C:\Py\python.exe")
        self.assertIs(rec.get("ok"), True)
        self.assertIs(cd.NUMPY_BOOT, rec, "the doctor cannot see the numpy attempt")
        self.assertIsNot(cd.PILLOW_BOOT, rec, "numpy's attempt was filed as Pillow's")

    def test_REG1719_the_inventory_row_quotes_its_boot_attempt(self):
        cd.NUMPY_BOOT = {"tried": True, "ok": False, "why": "pip exited 1: no network"}
        real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

        def no_np(name, *a, **k):
            if name == "numpy" or name.startswith("numpy."):
                raise ImportError("No module named 'numpy'")
            return real_import(name, *a, **k)
        import builtins
        builtins.__import__ = no_np
        try:
            state, why = cd._check_this_machine_can_cross_check_an_inventory()
        finally:
            builtins.__import__ = real_import
        self.assertEqual(state, cd.MISSING)
        self.assertIn("tried to install it at boot", why)
        self.assertIn("no network", why)
        self.assertIn("this machine can cross-check an inventory", [n for n, _ in cd.CHECKS],
                      "the row is written but the doctor never runs it")

    def test_REG1719_main_starts_the_numpy_step(self):
        self.assertIn("_ensure_numpy_at_boot", ca.main.__code__.co_names,
                      "main() never starts the boot numpy step - a self-updated Windows PC never gets it")

    def test_main_starts_the_step(self):
        self.assertIn("_ensure_pillow_at_boot", ca.main.__code__.co_names,
                      "main() never starts the boot Pillow step - only a double-click would ever install it")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "REG-3268 - the repair book's later call replaces the boot install's record, so a repair that fired reads fine",
     "file": "tv/control_app.py",
     "find": "        if isinstance(_prev, dict) and _prev.get(\"tried\") is True and _prev.get(\"ok\") is True:\n            return _prev\n",
     "replace": "        pass\n",
     "matches": 1},
    {
        "why": "REG-1719 - main() stops starting the boot numpy step: a self-updated Windows PC never measures a grid",
        "file": "control_app.py",
        "find": "    threading.Thread(target=_ensure_numpy_at_boot, daemon=True, name=\"tvd-numpy\").start()   # REG-1719\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1719 - the boot install always asks pip for Pillow, whatever package is missing",
        "file": "control_app.py",
        "find": "    argv = [exe, \"-m\", \"pip\", \"install\", \"--user\", \"--quiet\", pkg]\n",
        "replace": "    argv = [exe, \"-m\", \"pip\", \"install\", \"--user\", \"--quiet\", \"Pillow\"]\n",
        "matches": 1,
    },
    {
        "why": "REG-1719 - the doctor never runs the inventory row: a PC with no numpy reads healthy",
        "file": "console_doctor.py",
        "find": "    (\"this machine can cross-check an inventory\", _check_this_machine_can_cross_check_an_inventory),\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1260 - main() stops starting the boot Pillow step: a self-updated console never gets Pillow again",
        "file": "control_app.py",
        "find": "    threading.Thread(target=_ensure_pillow_at_boot, daemon=True, name=\"tvd-pillow\").start()\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1260 - pip runs under pythonw again (no stdout; the install silently does nothing useful)",
        "file": "control_app.py",
        "find": "        exe = exe[:-len(\"pythonw.exe\")] + \"python.exe\"     # pythonw has no stdout for pip to write to\n",
        "replace": "        pass\n",
        "matches": 1,
    },
]
