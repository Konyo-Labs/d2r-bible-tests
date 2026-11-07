# -*- coding: utf-8 -*-
"""REG-1993 - THE RENDER GATE'S BOUND MOVES WITH THE LOAD, AND ITS THREE NUMBERS MOVE TOGETHER.

His question, 2026-10-07, after the v3603 push starved at the render (353 s, load 8, while he played ON AIR over
GeForceNOW): "raise the limit why not?". Not a fixed higher ceiling - that is an absent hang detector on every quiet push.
The load measured when the render starts scales the hook's kill, render_check's clean-run cost and its report-by
deadline by one factor (tv/render_bound.py, 1x at or under load 5, capped at 2.5x).

Drives the real scale()/from_env(), render_check's constants under a handed-down factor (a fresh interpreter each), and
the hook's own gate_run widening lifted out of hooks/pre-push and run in bash.
"""
import io
import os

#: #107 - this law drives hooks/pre-push or a Linux job's own bash. Neither runs on Windows (only the Mac pushes; the job
#: runs on ubuntu), and Windows' bash there is the WSL launcher or Git Bash with backslash paths - nothing to measure
_RUNS_POSIX_HOOKS = os.name != "nt"
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import render_bound as RB  # noqa: E402

HOOK = os.path.join(os.path.dirname(HERE), "hooks", "pre-push")
WIDEN = '  if [ -n "${GATE_SCALE:-}" ]; then\n'
EXPORT = '    export GATE_SCALE="${_rs:-1.00}" TV_RENDER_SCALE="${_rs:-1.00}" GATE_LOAD_GRACE=1\n'
UNSET = '    unset GATE_SCALE TV_RENDER_SCALE GATE_LOAD_GRACE\n'


def _hook():
    with io.open(HOOK, encoding="utf-8") as fh:
        return fh.read()


def _code(src):
    return "\n".join(l for l in src.split("\n") if not l.lstrip().startswith("#"))


def _render_numbers(factor):
    env = dict(os.environ)
    env.pop("TV_RENDER_SCALE", None)
    if factor is not None:
        env["TV_RENDER_SCALE"] = factor
    p = subprocess.run([sys.executable, "-c", "import render_check as r; print(r._RENDER_SCALE, r._CLEAN_RUN_COST, "
                        "r._RUN_REPORT_BY)"], cwd=HERE, env=env, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr[-600:]
    return [float(x) for x in p.stdout.split()]


class TheRenderBoundMovesWithTheLoad(unittest.TestCase):

    def test_a_quiet_machine_keeps_the_measured_numbers_and_a_busy_one_widens_them(self):
        self.assertEqual(RB.scale(RB.BASE_LOAD), 1.0)
        self.assertEqual(RB.scale(2.0), 1.0, "a machine quieter than the measured load got a TIGHTER bound")
        self.assertAlmostEqual(RB.scale(8.0), 1.6)
        self.assertEqual(RB.scale(40.0), RB.CAP, "an overloaded machine widened the bound without limit")
        for bad in (None, "x", float("nan")):
            self.assertEqual(RB.scale(bad), 1.0, "an unreadable load %r was read as a busy machine" % (bad,))

    def test_the_handed_down_factor_is_clamped(self):
        self.assertEqual(RB.from_env({}), 1.0)
        self.assertEqual(RB.from_env({"TV_RENDER_SCALE": "1.6"}), 1.6)
        self.assertEqual(RB.from_env({"TV_RENDER_SCALE": "0.2"}), 1.0)
        self.assertEqual(RB.from_env({"TV_RENDER_SCALE": "9"}), RB.CAP)
        self.assertEqual(RB.from_env({"TV_RENDER_SCALE": "nan"}), 1.0)

    def test_render_check_scales_its_cost_and_deadline_by_the_same_factor(self):
        base = _render_numbers(None)
        self.assertEqual(base, [1.0, 317.0, 333.0], "a hand run (no factor) no longer reads the measured numbers")
        two = _render_numbers("2")
        self.assertEqual(two, [2.0, 634.0, 666.0], "render_check did not move its numbers with the hook's bound")
        self.assertLessEqual(two[2] + 20, 353 * 2, "at x2 the report-by deadline no longer leaves the hook's 20 s margin")

    @unittest.skipUnless(_RUNS_POSIX_HOOKS and shutil.which("bash"), "hooks/pre-push runs only where pushes happen - never on Windows (and bash is needed)")
    def test_the_hooks_gate_run_widens_its_limit_by_the_callers_factor(self):
        src = _hook()
        i = src.find(WIDEN)
        self.assertNotEqual(i, -1, "gate_run no longer widens its bound by GATE_SCALE")
        j = src.find("\n  fi\n", i)
        block = src[i:j + 6]
        got = []
        for s in ("1.6", "0.2", "9", ""):
            p = subprocess.run(["bash", "-c", "limit=353; GATE_SCALE=%s\n%s\necho $limit" % (s, block)],
                               capture_output=True, text=True, timeout=30)
            got.append(p.stdout.strip())
        self.assertEqual(got, ["565", "353", "883", "353"], "gate_run's widening: %s" % got)

    def test_only_the_render_gate_gets_the_factor(self):
        code = _code(_hook())
        self.assertEqual(code.count(EXPORT), 1, "the render call site no longer hands its measured factor down")
        self.assertEqual(code.count(UNSET), 1, "the factor outlives the render gate into the gates after it")
        self.assertLess(code.find(EXPORT), code.find('gate_run "render" "python3 tv/render_check.py" 353'))
        self.assertGreater(code.find(UNSET), code.find('gate_run "render" "python3 tv/render_check.py" 353'))


RED_PROOF = [
    {"why": "REG-1993 - the render bound never widens: the v3603 push starves at 353 s again under his game's load",
     "file": "tv/render_bound.py",
     "find": "    return min(CAP, v / BASE_LOAD)\n",
     "replace": "    return 1.0\n",
     "matches": 1},
    {"why": "REG-1993 - an overloaded machine widens the render bound without limit (an absent hang detector)",
     "file": "tv/render_bound.py",
     "find": "    return min(CAP, v / BASE_LOAD)\n",
     "replace": "    return v / BASE_LOAD\n",
     "matches": 1},
    {"why": "REG-1993 - render_check keeps its own 333 s deadline while the hook waits longer: its reads clamp to the floor",
     "file": "tv/render_check.py",
     "find": "_RENDER_SCALE = _RB.from_env()\n",
     "replace": "_RENDER_SCALE = 1.0\n",
     "matches": 1},
    {"why": "REG-1993 - gate_run ignores the caller's factor and kills at the base bound",
     "file": "hooks/pre-push",
     "find": '  if [ -n "${GATE_SCALE:-}" ]; then\n',
     "replace": '  if false; then\n',
     "matches": 1,
     # REG-2354 - only the bash law runs gate_run; with no bash on PATH it skips and the other four never reach it, so
     # Dean's PC filed this proof BLIND and shut every lock there. Judged where bash is.
     "needs": "posix"},
    {"why": "REG-1993 - the render call site never hands its measured factor down",
     "file": "hooks/pre-push",
     "find": '    export GATE_SCALE="${_rs:-1.00}" TV_RENDER_SCALE="${_rs:-1.00}" GATE_LOAD_GRACE=1\n',
     "replace": '    : no factor\n',
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
