# -*- coding: utf-8 -*-
"""v3859 (Dean, Nov 2 18:43) - A REFUSED JOB BREAKAWAY STILL STARTS THE SCANNER, AND SAYS SO IN PLAIN WORDS.

Dean's console toasted "failed to start scanner: [WinError 5] Access is denied". Root cause: v3850 spawns the
reel-cutter with CREATE_BREAKAWAY_FROM_JOB so it outlives the console. When the launcher's job forbids
breakaway, CreateProcess fails with ERROR_ACCESS_DENIED (WinError 5) and nothing started.
Now _popen_breakaway (the scanner AND the recorder, capture_win.ps1) retries once inside the job and the start reply names what happened; any other refusal is a
plain sentence, never a bare WinError. RED_PROOF reverts each joint.
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
try:
    import fixture_tmp as _fx_tmp  # noqa: E402
    _fx_tmp.contain()
except Exception:
    pass
import control_app as ca  # noqa: E402

BREAK = 0x01000000

RED_PROOF = [
    {"why": "no retry: a refused breakaway leaves the scanner unstarted", "file": "control_app.py",
     "find": "        if getattr(e, \"winerror\", None) != 5 or not (flags & 0x01000000):\n            raise\n",
     "replace": "        raise\n", "matches": 1},
    {"why": "the retry keeps the breakaway flag and is refused again", "file": "control_app.py",
     "find": "        kw[\"creationflags\"] = flags & ~0x01000000\n",
     "replace": "        kw[\"creationflags\"] = flags\n", "matches": 1},
    {"why": "the recorder spawns without the fallback again", "file": "control_app.py",
     "find": "            popen=lambda argv, **kw: _popen_breakaway(\n",
     "replace": "            _unused=lambda argv, **kw: _popen_breakaway(\n", "matches": 1},
    {"why": "the recorder's failure is a bare exception again", "file": "control_app.py",
     "find": "% _scanner_start_error(e, \"powershell.exe\", \"the recorder\"))",
     "replace": "% e)", "matches": 1},
    {"why": "the console shows a bare WinError again", "file": "control_app.py",
     "find": "\"failed to start scanner: \" + _scanner_start_error(e, py_exe),",
     "replace": "\"failed to start scanner: %s\" % e,", "matches": 1},
    {"why": "start_agent stops using the fallback", "file": "control_app.py",
     "find": "            _agent_proc, _spawn_note = _popen_breakaway(\n",
     # v3859: the call grew a say= keyword, so the swallowed tail is a call now, never a bare tuple (INVALID on CI)
     "replace": "            _agent_proc, _spawn_note = subprocess.Popen(**popen_kw), None; _x = (lambda *a, **k: None)(\n",
     "matches": 1},
]


def _denied():
    e = PermissionError(13, "Access is denied")
    e.winerror = 5
    return e


class FakePopen(object):
    calls = []

    def __init__(self, args, **kw):
        FakePopen.calls.append(kw)
        if kw.get("creationflags", 0) & BREAK:
            raise _denied()
        self.pid = 4242


class Fallback(unittest.TestCase):
    def setUp(self):
        FakePopen.calls = []
        self._orig = ca.subprocess.Popen
        ca.subprocess.Popen = FakePopen

    def tearDown(self):
        ca.subprocess.Popen = self._orig

    def test_a_refused_breakaway_starts_the_scanner_inside_the_job(self):
        said = []
        proc, note = ca._popen_breakaway({"args": ["py"], "creationflags": 0x200 | BREAK}, say=said.append)
        self.assertEqual(proc.pid, 4242)
        self.assertEqual(len(FakePopen.calls), 2)
        self.assertEqual(FakePopen.calls[1]["creationflags"], 0x200)
        self.assertIn("access denied", note)
        self.assertIn("inside it instead", note)
        self.assertEqual(said, [note])

    def test_a_normal_start_says_nothing_extra(self):
        proc, note = ca._popen_breakaway({"args": ["py"], "creationflags": 0x200})
        self.assertEqual((proc.pid, note, len(FakePopen.calls)), (4242, None, 1))

    def test_a_denial_without_breakaway_is_not_retried(self):
        def deny(args, **kw):
            FakePopen.calls.append(kw)
            raise _denied()
        ca.subprocess.Popen = deny
        with self.assertRaises(PermissionError):
            ca._popen_breakaway({"args": ["py"], "creationflags": 0x200})
        self.assertEqual(len(FakePopen.calls), 1)

    def test_the_refusal_is_a_plain_sentence_not_a_bare_winerror(self):
        msg = ca._scanner_start_error(_denied(), r"C:\\py\\python.exe")
        self.assertIn("access denied launching the scanner", msg)
        self.assertNotIn("WinError", msg)
        self.assertNotIn("C:", msg)

    def test_start_agent_uses_the_fallback_and_the_plain_sentence(self):
        import inspect
        src = inspect.getsource(ca)
        self.assertIn("_agent_proc, _spawn_note = _popen_breakaway(", src)
        self.assertIn("\"failed to start scanner: \" + _scanner_start_error(e, py_exe),", src)
        self.assertIn("\"msg\": \"started\" + (\" - \" + _spawn_note if _spawn_note else \"\"),", src)


class Recorder(unittest.TestCase):
    def setUp(self):
        FakePopen.calls = []
        self._orig = ca.subprocess.Popen
        ca.subprocess.Popen = FakePopen

    def tearDown(self):
        ca.subprocess.Popen = self._orig

    def test_the_recorder_spawn_goes_through_the_fallback(self):
        import io
        seen = {}
        log = io.StringIO()

        def spawn(role, argv, popen=None, **kw):
            kw.pop("kill", None); kw.pop("alive", None); kw.pop("contain", None)
            seen["proc"] = popen(argv, **kw)
            raise RuntimeError("stop after the spawn")
        orig = ca._child_guard.spawn
        ca._child_guard.spawn = spawn
        try:
            src = __import__("inspect").getsource(ca._start_capture_locked)
            self.assertIn("popen=lambda argv, **kw: _popen_breakaway(", src)
            self.assertIn('"the recorder"', src)
            # drive the lambda the recorder hands child_guard, flags as the recorder sets them
            popen = eval(src[src.index("lambda argv"):src.index("[0],") + 3].replace("log_fp", "log"),
                         dict(vars(ca), log=log))
            proc = popen(["powershell.exe"], creationflags=0x200 | BREAK)
        finally:
            ca._child_guard.spawn = orig
        self.assertEqual(proc.pid, 4242)
        self.assertEqual(FakePopen.calls[-1]["creationflags"], 0x200)
        self.assertIn("started the recorder inside it instead", log.getvalue())

    def test_a_recorder_that_cannot_start_says_why_in_plain_words(self):
        src = __import__("inspect").getsource(ca._start_capture_locked)
        self.assertIn('_scanner_start_error(e, "powershell.exe", "the recorder")', src)
        msg = ca._scanner_start_error(_denied(), "powershell.exe", "the recorder")
        self.assertIn("access denied launching the recorder (powershell.exe)", msg)
        self.assertNotIn("WinError", msg)


if __name__ == "__main__":
    unittest.main()
