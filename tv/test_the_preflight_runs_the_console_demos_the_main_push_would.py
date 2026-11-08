# -*- coding: utf-8 -*-
"""v3881 (REG-3384) - THE PRE-FLIGHT RUNS THE CONSOLE DEMOS WHENEVER THE MAIN PUSH WOULD.

MEASURED on v3879 (2026-11-07): GitHub vouched for 9c5815c6f after a re-run; the main push's hook then ran
tv/demo_console.mjs - which runs ONLY there, never on GitHub - and J9 refused the push ("a zone has no game-extracted face"):
v3879's own #108 had moved the Terror Zone cards to monster sprites. The pre-flight had run 1,539 python laws and handed
"node, shell, the app" to GitHub, which never runs this one. The fix changed the sha and bought a whole new round.

Now tv/preflight.py asks the same question the hook asks - does the diff the main push carries touch the demos' watch? -
and when it does, runs the demos (bounded) and turns RED on a red demo. The watch is the hook's, held equal here, so the two
cannot drift apart. No node on the PC is UNKNOWN (exit 2), never a pass. RED_PROOF below. [[copy-drift]] [[regression-guard]]
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import preflight as P  # noqa: E402

HOOK = os.path.join(os.path.dirname(HERE), "hooks", "pre-push")


def _git_with(main_diff, tree_diff=""):
    def g(*args):
        if args[:2] == ("diff", "--name-only"):
            return True, (main_diff if args[-1] == "origin/main..HEAD" else tree_diff)
        return False, ""
    return g


def _run_pf(demo, due=(True, "this version changes tv/control_ui.html"), says=None):
    """drive preflight() with every other step stubbed green - only the demo step decides"""
    out = says if says is not None else []
    keep = (P.read_costs, P.select, P.uncosted)
    try:      # the registry walk is not under test here (and costs ~70 s): one law, nothing browser-driving
        P.read_costs = lambda _p: {"test_x": 1.0}
        P.select = lambda _c, _h, _cap: {"run": [], "argv": {}, "browser": [], "slow": [], "other": []}
        P.uncosted = lambda _c, _h, _registry=None: ([], {}, [])
        code, reds = P.preflight(prove=False, say=out.append, _laws=lambda names: [], _anchors=lambda: (True, ""),
                                 _demos=demo, _demos_due=lambda: due,
                                 _render_due=lambda: (False, "v3883 - not this law's step"),
                                 _second_eye=lambda: ("same", "v3883 - not this law's step"))
    finally:
        P.read_costs, P.select, P.uncosted = keep
    return code, reds, out


class ThePreflightRunsTheDemos(unittest.TestCase):

    def test_a_red_demo_makes_the_preflight_red(self):
        """* THE POINT: v3879's J9, caught before the round instead of after it"""
        code, reds, _ = _run_pf(lambda: (False, "❌ J9 TERROR ZONE FLAGSHIP - a zone has no game-extracted face"))
        self.assertEqual(code, 1)
        self.assertTrue(any("console-demos" in r and "J9" in r for r in reds), reds)

    def test_baseline_green_demos_leave_the_preflight_green(self):
        code, reds, _ = _run_pf(lambda: (True, "DEMOS: 16/16"))
        self.assertEqual((code, reds), (0, []))

    def test_demos_not_due_are_not_run(self):
        ran = []
        code, _r, _s = _run_pf(lambda: ran.append(1) or (False, "x"), due=(False, "nothing the console demos watch changed"))
        self.assertEqual((code, ran), (0, []), "the demos ran (and could refuse) on a version that does not touch them")

    def test_demos_that_could_not_run_are_unknown_never_green(self):
        code, _r, says = _run_pf(lambda: (None, "node is not on this PC"))
        self.assertEqual(code, 2)
        self.assertTrue(any("UNKNOWN" in s for s in says))
        code, _r, _s = _run_pf(lambda: (True, ""), due=(None, "git could not list the files - UNKNOWN"))
        self.assertEqual(code, 2, "an unreadable diff read as 'the demos are not due'")

    def test_the_trigger_names_each_watched_file_and_nothing_else(self):
        for f in ("tv/control_ui.html", "tv/control_app.py", "tv/demo_console.mjs"):
            self.assertTrue(P.demos_due(_git_with("tv/heart2.py\n" + f + "\n"))[0], f)
            self.assertTrue(P.demos_due(_git_with("", f + "\n"))[0], "the working tree the hook grades: " + f)
        self.assertFalse(P.demos_due(_git_with("tv/heart2.py\nbible.html\ntv/control_uix.css\n"))[0])
        self.assertIsNone(P.demos_due(lambda *a: (False, ""))[0])

    def test_the_watch_is_the_hooks_watch(self):
        src = io.open(HOOK, encoding="utf-8").read()
        m = re.findall(r"^\s*_demo_watch='([^']+)'\s*$", src, re.M)
        self.assertEqual(len(m), 1, "the hook's demo watch moved - re-point this law")
        self.assertEqual(m[0], P.DEMO_WATCH, "the pre-flight watches other files than the main push's hook")


RED_PROOF = [
    {"why": "REG-3384 - the pre-flight no longer runs the console demos (v3879's J9 refuses main after a green round again)",
     "file": "tv/preflight.py", "find": "        d_ok, d_tail = (_demos or run_demos)()\n",
     "replace": "        d_ok, d_tail = True, ''\n", "matches": 1},
    {"why": "REG-3384 - the pre-flight watches fewer files than the hook (a server change skips the demos here)",
     "file": "tv/preflight.py",
     "find": 'DEMO_WATCH = r"tv/control_ui\\.html|tv/control_app\\.py|tv/demo_console\\.mjs"\n',
     "replace": 'DEMO_WATCH = r"tv/control_ui\\.html|tv/demo_console\\.mjs"\n', "matches": 1},
    {"why": "REG-3384 - demos that could not run read as a pass",
     "file": "tv/preflight.py", "find": "        return 2, []\n    say(\"preflight: GREEN",
     "replace": "        pass\n    say(\"preflight: GREEN", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
