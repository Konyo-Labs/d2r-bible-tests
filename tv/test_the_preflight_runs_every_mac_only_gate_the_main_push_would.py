# -*- coding: utf-8 -*-
"""v3883 (#129) - THE PRE-FLIGHT RUNS THE RENDER GATE AND ASKS THE SECOND EYE WHENEVER THE MAIN PUSH WOULD.

MEASURED on v3881 (2026-11-08): GitHub vouched for a1de4b253 after ~51 min, and the main push was then refused TWICE by
gates the hook runs only on this Mac, after the whole round: (1) "v3881 may not ship while v3880 has never been looked at
by a different model family" (tv/second_eye_ledger.py --check v3880 --gate); (2) after the look, render: fleet-xref read 2
of 25 nodes ZERO-SIZE at all six widths - v3881's own REG-3395 had moved a row's chips onto the OPEN row and the target
still selected them on closed ones. The render fix changed the sha and bought a whole new GitHub round. tv/preflight.py
mirrored the console demos (REG-3384, after v3879 lost a round to them) and neither of these.

Now the pre-flight asks the hook's two questions the hook's way: the render gate runs when the push's diff touches the
hook's _px_watch (held equal here) or bible.html changed beyond its stamp (tv/page_delta.py, fail-closed); the second eye
is asked of the version live on main whenever this push carries a new one. A red is RED; a gate that could not run, or a
diff git could not list, is UNKNOWN (exit 2) - never a pass. Every step but the one under test is stubbed; no Chrome, no
git, no ledger is touched. RED_PROOF below. [[copy-drift]] [[regression-guard]] [[unknown-stays-unknown]]
"""
import io
import json
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


def _git_with(main_diff, tree_diff="", vers=("v3880", "v3881")):
    def g(*args):
        if args[:2] == ("diff", "--name-only"):
            return True, (main_diff if args[-1] == "origin/main..HEAD" else tree_diff)
        if args and args[0] == "show":
            v = vers[0] if args[1].startswith("origin/main:") else vers[1]
            return (v is not None), (json.dumps({"ver": v}) if v else "")
        return False, ""
    return g


class _Ran(object):
    def __init__(self, rc, out=""):
        self.returncode, self.stdout, self.stderr = rc, out, ""


def _run_pf(render=lambda: (True, ""), render_due=(True, "this version changes tv/control_ui.html"),
            eye=(True, "v3880 has its recorded second-eye look"), says=None):
    out = says if says is not None else []
    keep = (P.read_costs, P.select, P.uncosted)
    try:
        P.read_costs = lambda _p: {"test_x": 1.0}
        P.select = lambda _c, _h, _cap: {"run": [], "argv": {}, "browser": [], "slow": [], "other": []}
        P.uncosted = lambda _c, _h, _registry=None: ([], {}, [])
        code, reds = P.preflight(prove=False, say=out.append, _laws=lambda names: [], _anchors=lambda: (True, ""),
                                 _demos_due=lambda: (False, "not this law's step"),
                                 _render=render, _render_due=lambda: render_due, _second_eye=lambda: eye)
    finally:
        P.read_costs, P.select, P.uncosted = keep
    return code, reds, out


class ThePreflightRunsTheRenderGate(unittest.TestCase):

    def test_a_red_render_makes_the_preflight_red(self):
        """* THE POINT: v3881's fleet-xref, caught before the round instead of after it"""
        code, reds, _ = _run_pf(render=lambda: (False, "\U0001F534 fleet-xref 2 of 25 node(s) are ZERO-SIZE"))
        self.assertEqual(code, 1)
        self.assertTrue(any(r.startswith("render") and "fleet-xref" in r for r in reds), reds)

    def test_baseline_a_green_render_leaves_it_green(self):
        self.assertEqual(_run_pf()[:2], (0, []))

    def test_a_render_not_due_is_not_run(self):
        ran = []
        code, _r, _s = _run_pf(render=lambda: ran.append(1) or (False, "x"), render_due=(False, "nothing watched changed"))
        self.assertEqual((code, ran), (0, []))

    def test_a_render_that_could_not_run_is_unknown_never_green(self):
        code, _r, says = _run_pf(render=lambda: (None, "no Chrome here"))
        self.assertEqual(code, 2)
        self.assertTrue(any("UNKNOWN" in s and "render" in s for s in says), says)
        self.assertEqual(_run_pf(render_due=(None, "git could not list - UNKNOWN"))[0], 2)

    def test_the_trigger_is_the_hooks(self):
        for f in ("tv/control_ui.html", "tv/render_check.py", "tv/render_coverage.json"):
            self.assertTrue(P.render_due(_git_with("tv/heart2.py\n" + f + "\n"))[0], f)
            self.assertTrue(P.render_due(_git_with("", f + "\n"))[0], "the working tree the hook grades: " + f)
        self.assertFalse(P.render_due(_git_with("tv/heart2.py\ntv/control_ui.htmlx\n"), _page_delta=lambda: True)[0])
        self.assertIsNone(P.render_due(lambda *a: (False, ""))[0])

    def test_bible_counts_only_beyond_its_stamp(self):
        self.assertTrue(P.render_due(_git_with("bible.html\n"), _page_delta=lambda: True)[0])
        self.assertFalse(P.render_due(_git_with("bible.html\n"), _page_delta=lambda: False)[0],
                         "a version stamp alone re-rendered the whole page (REG-1753)")

    def test_the_watch_is_the_hooks_watch(self):
        src = io.open(HOOK, encoding="utf-8").read()
        m = re.findall(r"^_px_watch='([^']+)'\s*$", src, re.M)
        self.assertEqual(len(m), 1, "the hook's render watch moved - re-point this law")
        self.assertEqual(m[0], P.RENDER_WATCH, "the pre-flight renders on other files than the main push's hook")

    def test_render_check_exit_codes_mean_what_they_say(self):
        self.assertEqual(P.run_render(_run=lambda *a, **k: _Ran(0, "\U0001F7E2 every target rendered"))[0], True)
        ok, tail = P.run_render(_run=lambda *a, **k: _Ran(1, "\U0001F534 fleet-xref THE FLEET CROSS-REFERENCE\nx"))
        self.assertIs(ok, False)
        self.assertIn("fleet-xref", tail)
        self.assertIsNone(P.run_render(_run=lambda *a, **k: _Ran(2, "no Chrome"))[0], "exit 2 (no Chrome) read as a verdict")


class ThePreflightAsksTheSecondEye(unittest.TestCase):

    def test_an_owed_look_makes_the_preflight_red(self):
        """* THE POINT: v3880 had no recorded look, and the main push found that out after the round"""
        code, reds, _ = _run_pf(eye=(False, "v3880 has no recorded second-eye look - run python3 tv/second_eye_run.py v3880"))
        self.assertEqual(code, 1)
        self.assertTrue(any(r.startswith("second-eye") and "second_eye_run.py v3880" in r for r in reds), reds)

    def test_unreadable_versions_are_unknown_and_a_same_version_push_asks_nothing(self):
        self.assertEqual(_run_pf(eye=(None, "could not be read - UNKNOWN"))[0], 2)
        self.assertEqual(_run_pf(eye=("same", "no new version"))[0], 0)

    def test_it_asks_the_ledger_about_the_version_on_main(self):
        asked = []

        def run(argv, **kw):
            asked.append(list(argv[1:]))
            return _Ran(0 if argv[-2] == "v3880" else 1)
        got, why = P.second_eye_due(_git_with("", vers=("v3880", "v3881")), _run=run)
        self.assertIs(got, True, why)
        self.assertEqual(asked, [[os.path.join("tv", "second_eye_ledger.py"), "--check", "v3880", "--gate"]])
        got, why = P.second_eye_due(_git_with("", vers=("v3880", "v3881")), _run=lambda *a, **k: _Ran(1))
        self.assertIs(got, False)
        self.assertIn("second_eye_run.py v3880", why)
        self.assertEqual(P.second_eye_due(_git_with("", vers=("v3881", "v3881")), _run=run)[0], "same")
        self.assertIsNone(P.second_eye_due(_git_with("", vers=(None, "v3881")), _run=run)[0])


RED_PROOF = [
    {"why": "v3883 - the pre-flight no longer runs the render gate (v3881's fleet-xref refuses main after a green round "
            "again)",
     "file": "tv/preflight.py", "find": "        r_ok, r_tail = (_render or run_render)()\n",
     "replace": "        r_ok, r_tail = True, ''\n", "matches": 1},
    {"why": "v3883 - the pre-flight renders on fewer files than the hook (a render_check.py edit skips it here)",
     "file": "tv/preflight.py",
     "find": 'RENDER_WATCH = r"^(tv/control_ui\\.html|tv/render_check\\.py|tv/render_coverage\\.json)$"\n',
     "replace": 'RENDER_WATCH = r"^(tv/control_ui\\.html)$"\n', "matches": 1},
    {"why": "v3883 - the pre-flight never asks the second eye (v3880's missing look refuses main after the round again)",
     "file": "tv/preflight.py", "find": "    if se is False:\n        reds.append(",
     "replace": "    if False:\n        reds.append(", "matches": 1},
    {"why": "v3883 - a render that could not run reads as a pass",
     "file": "tv/preflight.py", "find": "    if r.returncode == 2:\n        return None,",
     "replace": "    if r.returncode == 2:\n        return True,", "matches": 1},
    {"why": "v3883 - a version stamp alone re-renders the whole page (bible.html counted by its name)",
     "file": "tv/preflight.py", "find": "        if changed is not False:\n",
     "replace": "        if True:\n", "matches": 1},
    {"why": "v3883 - the ledger is asked about this push's version, not the one live on main",
     "file": "tv/preflight.py",
     "find": "[sys.executable, os.path.join(\"tv\", \"second_eye_ledger.py\"), \"--check\", prev, \"--gate\"]",
     "replace": "[sys.executable, os.path.join(\"tv\", \"second_eye_ledger.py\"), \"--check\", this, \"--gate\"]",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
