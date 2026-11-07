# -*- coding: utf-8 -*-
"""#227 — THE WINDOWS EYE IS FOUND BY ITS .EXE.

MEASURED on his Windows ALT box: C:\\Users\\<user>\\.grok\\bin\\grok.exe existed and was on PATH, the
resolver's candidate list carried no .exe, and second_eye_run hardcoded ~/.grok/bin/grok — so the
doctor said "no binary there" and the second opinion read MISSING on a machine that had one. Fixed in
#225 (candidate + one resolver) and pinned only by a re-anchored source guard until now.

  · DRIVEN: a Windows-shaped home (only ~/.grok/bin/grok.exe; the process PATH does not have it)
    resolves through g5_grok_eyes._grok_bin AND second_eye_run._default_eye_cli.
  · DRIVEN: the doctor's second-opinion row reads OK on that home, never "no binary there".
  · PREMISE: without the .exe candidate the resolver finds nothing, so the cases can fail.
RED_PROOF below.
"""
import os
import shutil
import stat
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import console_doctor as cd  # noqa: E402
import g5_grok_eyes as g5  # noqa: E402
import second_eye_run as ser  # noqa: E402

_ENV = ("HOME", "USERPROFILE", "PATH", "G5_GROK_BIN", "TV_GROK_BIN", "THIRD_EYE_CLI")


class AWindowsHome(unittest.TestCase):

    def setUp(self):
        self._env = {k: os.environ.get(k) for k in _ENV}
        self._cli, self._cwd = ser.EYE_CLI, getattr(ser, "EYE_CWD", None)
        self.home = tempfile.mkdtemp(prefix="winhome-")
        bindir = os.path.join(self.home, ".grok", "bin")
        os.makedirs(bindir)
        self.exe = os.path.join(bindir, "grok.exe")
        with open(self.exe, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(self.exe, os.stat(self.exe).st_mode | stat.S_IXUSR)
        self.empty_path = tempfile.mkdtemp(prefix="nopath-")
        os.environ["HOME"] = self.home
        os.environ["USERPROFILE"] = self.home   # #107 - on Windows expanduser("~") reads USERPROFILE, never HOME
        os.environ["PATH"] = self.empty_path          # the GUI process PATH: no grok on it
        for k in ("G5_GROK_BIN", "TV_GROK_BIN", "THIRD_EYE_CLI"):
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        ser.EYE_CLI = self._cli
        if self._cwd is not None:
            ser.EYE_CWD = self._cwd
        shutil.rmtree(self.home, ignore_errors=True)
        shutil.rmtree(self.empty_path, ignore_errors=True)

    def test_the_resolver_finds_the_exe(self):
        self.assertEqual(g5._grok_bin(), self.exe)

    def test_the_second_eye_asks_the_one_resolver(self):
        self.assertEqual(ser._default_eye_cli(), self.exe,
                         "the second eye hardcoded a path again instead of asking the resolver")

    def test_the_doctor_row_is_ok_not_no_binary_there(self):
        ser.EYE_CLI = ser._default_eye_cli()
        ser.EYE_CWD = self.home                       # outside the repo, like the real seat
        state, why = cd._check_this_machine_can_get_a_second_opinion()
        self.assertEqual(state, cd.OK, "a machine with grok.exe read: %s" % why)
        self.assertNotIn("no binary there", why)

    def test_premise_without_the_exe_candidate_nothing_is_found(self):
        real = g5._GROK_CANDIDATES
        try:
            g5._GROK_CANDIDATES = tuple(c for c in real if not c.endswith(".exe"))
            self.assertEqual(g5._grok_bin(), "", "premise: the .exe candidate is what finds it")
        finally:
            g5._GROK_CANDIDATES = real


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "#227 - the resolver's candidates lose grok.exe: the Windows eye reads MISSING on a machine that has one",
        "file": "g5_grok_eyes.py",
        "find": "    \"~/.grok/bin/grok.exe\",\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#227 - the second eye hardcodes ~/.grok/bin/grok again instead of asking the one resolver",
        "file": "second_eye_run.py",
        "find": "        hit = _g5._grok_bin()\n",
        "replace": "        hit = \"\"\n",
        "matches": 1,
    },
]
