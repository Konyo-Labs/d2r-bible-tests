# -*- coding: utf-8 -*-
"""v3859 (Dean, Nov 2 18:43) - A REFUSED JOB BREAKAWAY STILL STARTS THE SCANNER, AND SAYS SO IN PLAIN WORDS.

Dean's console toasted "failed to start scanner: [WinError 5] Access is denied". Root cause: v3850 spawns the
reel-cutter with CREATE_BREAKAWAY_FROM_JOB so it outlives the console. When the launcher's job forbids
breakaway, CreateProcess fails with ERROR_ACCESS_DENIED (WinError 5) and nothing started.
Now _popen_scanner retries once inside the job and the start reply names what happened; any other refusal is a
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
    {"why": "the console shows a bare WinError again", "file": "control_app.py",
     "find": "\"failed to start scanner: \" + _scanner_start_error(e, py_exe),",
     "replace": "\"failed to start scanner: %s\" % e,", "matches": 1},
    {"why": "start_agent stops using the fallback", "file": "control_app.py",
     "find": "            _agent_proc, _spawn_note = _popen_scanner(\n",
     "replace": "            _agent_proc, _spawn_note = subprocess.Popen(**popen_kw), None; _x = (\n", "matches": 1},
]


def _denied():
    e = PermissionError(13, "Access is denied")
    e.winerror = 5
    return e


class FakePopen(object):
    calls = []

    def __init__(self, **kw):
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
        proc, note = ca._popen_scanner({"args": ["py"], "creationflags": 0x200 | BREAK}, say=said.append)
        self.assertEqual(proc.pid, 4242)
        self.assertEqual(len(FakePopen.calls), 2)
        self.assertEqual(FakePopen.calls[1]["creationflags"], 0x200)
        self.assertIn("access denied", note)
        self.assertIn("inside it instead", note)
        self.assertEqual(said, [note])

    def test_a_normal_start_says_nothing_extra(self):
        proc, note = ca._popen_scanner({"args": ["py"], "creationflags": 0x200})
        self.assertEqual((proc.pid, note, len(FakePopen.calls)), (4242, None, 1))

    def test_a_denial_without_breakaway_is_not_retried(self):
        def deny(**kw):
            FakePopen.calls.append(kw)
            raise _denied()
        ca.subprocess.Popen = deny
        with self.assertRaises(PermissionError):
            ca._popen_scanner({"args": ["py"], "creationflags": 0x200})
        self.assertEqual(len(FakePopen.calls), 1)

    def test_the_refusal_is_a_plain_sentence_not_a_bare_winerror(self):
        msg = ca._scanner_start_error(_denied(), r"C:\\py\\python.exe")
        self.assertIn("access denied launching the scanner", msg)
        self.assertNotIn("WinError", msg)
        self.assertNotIn("C:", msg)

    def test_start_agent_uses_the_fallback_and_the_plain_sentence(self):
        import inspect
        src = inspect.getsource(ca)
        self.assertIn("_agent_proc, _spawn_note = _popen_scanner(", src)
        self.assertIn("\"failed to start scanner: \" + _scanner_start_error(e, py_exe),", src)
        self.assertIn("\"msg\": \"started\" + (\" - \" + _spawn_note if _spawn_note else \"\"),", src)


if __name__ == "__main__":
    unittest.main()
