# -*- coding: utf-8 -*-
"""#173 (REG-2940) - NO LAW OPENS THE REAL CONSOLE WINDOW. Moved out of test_an_update_lands_beside_a_shadow_reel,
verbatim, with the red-proof that plants the call.

The rule reads every law file in tv/ (glob test_*.py): the folder is the denominator, so a new law that drives the real
window cannot hide. That listing is why it lives alone: a law that lists a directory itself cannot have its proofs
saved, and inside the update-beside-the-shadow law it made all 20 of that law's proofs re-run on every push. Here it is
two cheap cases, listed in tv/unkeyable_laws.json on purpose. [[regression-guard]]
"""
import glob
import io
import os
import sys
import tokenize
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass


class NoLawOpensTheRealConsole(unittest.TestCase):
    """2026-09-28 — A LAW THAT OPENS THE REAL WINDOW ARMS HIS CONSOLE'S WATCHERS INSIDE THE TEST.

    MEASURED, twice in one hour: the first cut of AnUpdateLandsQuietlyBesideHisGame drove
    open_control_window(). That call runs start_background_watchers(), which starts the REAL drift loop,
    and the drift loop's direct os.execv replaced the test process and rewrote his .tvd_window.pid and
    .relaunch_receipt.json. Both files were restored by hand. The window's options now come from the pure
    _control_window_kwargs(), and no file of laws may CALL either door. Read with tokenize, so a name in
    a comment, a docstring or a red-proof string is not a call."""

    DOORS = ("open_control_window", "start_background_watchers")

    def _calls(self, src):
        skip = (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT)
        toks = [t for t in tokenize.generate_tokens(io.StringIO(src).readline) if t.type not in skip]
        return [(t.start[0], t.string) for i, t in enumerate(toks[:-1])
                if t.type == tokenize.NAME and t.string in self.DOORS and toks[i + 1].string == "("
                and not (i and toks[i - 1].string == "def")]

    def test_the_scan_sees_a_call_and_only_a_call(self):
        self.assertEqual(self._calls("ca.open_control_window()\n"), [(1, "open_control_window")],
                         "PREMISE: the scan cannot see a call, so its green below means nothing")
        self.assertEqual(self._calls("x = 1\nstart_background_watchers ('t')\n"), [(2, "start_background_watchers")])
        self.assertEqual(self._calls("# open_control_window()\ns = 'start_background_watchers(y)'\n"
                                     "n = src.count(\"open_control_window(\")\ng = inspect.getsource(ca.open_control_window)\n"
                                     "def open_control_window():\n    pass\n"), [],
                         "a comment, a string, a reference or a definition was read as a call")

    def test_no_law_calls_the_real_window_or_its_watchers(self):
        laws = sorted(glob.glob(os.path.join(HERE, "test_*.py")))
        self.assertGreater(len(laws), 100, "PREMISE: the scan found %d law files - wrong folder" % len(laws))
        found = []
        for p in laws:
            with open(p, encoding="utf-8") as f:
                src = f.read()
            try:
                hits = self._calls(src)
            except (tokenize.TokenError, IndentationError, SyntaxError) as e:
                found.append("%s: unreadable (%s) - a law nobody can scan is not proven safe" % (os.path.basename(p), e))
                continue
            found += ["%s:%d calls %s()" % (os.path.basename(p), n, name) for n, name in hits]
        self.assertEqual(found, [], "a law drives the REAL console window - it arms his watchers and can exec "
                                    "the test process over his pid file: %s" % found)


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "2026-09-28 - a law opens the real console window again (it armed his watchers and exec'd the test over his pid file)",
        "file": "test_an_update_lands_beside_a_shadow_reel.py",
        "find": "        ca.os.execv = self._execv\n",
        "replace": "        ca.os.execv = self._execv\n        if False:\n            ca.open_control_window()\n",
        "matches": 1,
    },
]
