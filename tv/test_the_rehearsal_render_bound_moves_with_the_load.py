# -*- coding: utf-8 -*-
"""v3898 (card #200, REG-3712) - THE SHIP'S REHEARSAL GIVES THE RENDER THE SAME LOAD-SCALED BOUND THE PUSH HOOK GIVES IT.

MEASURED 11-11 on v3897's ship (attempt 2): the Mac rehearsal killed tv/render_check.py at a FIXED 360 s and the ship
stopped with "Mac rehearsal ended UNKNOWN while CI was still running - main is NOT pushed" - a whole relaunch - while
hooks/pre-push grades the same render with its bound scaled by tv/render_bound.py (REG-1993: x1-x2.5 by the 1-min
load). Now preship.check_render asks render_bound for the factor, scales its kill by it and hands TV_RENDER_SCALE /
GATE_SCALE down so render_check's own cost and report-by deadline move with it. At or under BASE_LOAD nothing changes.

DRIVEN: the shipped check_render with preship._run stubbed (no browser starts) at a quiet load and at a busy one, and
the scale read from render_bound itself, never typed here. RED_PROOF below.
"""
import os
import sys
import unittest
from unittest import mock
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import preship  # noqa: E402
import render_bound  # noqa: E402


def _drive(load):
    seen = []

    def fake_run(cmd, cwd, timeout, env=None):
        seen.append({"timeout": timeout, "scale": (env or {}).get("TV_RENDER_SCALE"),
                     "gate": (env or {}).get("GATE_SCALE")})
        return subprocess.CompletedProcess(cmd, 0, "ok", "")

    with mock.patch.object(preship, "_run", fake_run), mock.patch.object(preship.os, "getloadavg", lambda: (load, 0, 0)):
        code, say = preship.check_render("/nonexistent-root")
    return code, say, seen


class TheRehearsalRenderBoundMovesWithTheLoad(unittest.TestCase):

    def test_a_busy_mac_gives_the_render_the_hooks_scaled_bound(self):
        """* THE POINT - at twice the base load the kill is twice the base, and render_check is told the same factor"""
        load = render_bound.BASE_LOAD * 2
        k = render_bound.scale(load)
        self.assertGreater(k, 1.0, "PREMISE: render_bound no longer scales at twice its base load")
        code, say, seen = _drive(load)
        self.assertEqual(code, 0)
        self.assertEqual(len(seen), 1, seen)
        self.assertEqual(seen[0]["timeout"], int(round(preship.RENDER_TIMEOUT_S * k)),
                         "the rehearsal still kills the render at its fixed bound on a busy Mac: %s" % seen)
        self.assertEqual(seen[0]["scale"], "%.2f" % k, "render_check is not told the factor its kill uses")
        self.assertEqual(seen[0]["gate"], "%.2f" % k)
        self.assertIn("bound x%.2f" % k, say, "the verdict does not say the bound moved")

    def test_a_quiet_mac_keeps_the_hang_detector_it_had(self):
        """BASELINE - at or under BASE_LOAD the bound is exactly RENDER_TIMEOUT_S (a fixed higher ceiling is no detector)"""
        code, say, seen = _drive(render_bound.BASE_LOAD - 1)
        self.assertEqual(seen[0]["timeout"], preship.RENDER_TIMEOUT_S, seen)
        self.assertEqual(seen[0]["scale"], "1.00")
        self.assertNotIn("bound x", say)

    def test_the_cap_is_render_bounds_cap(self):
        code, say, seen = _drive(render_bound.BASE_LOAD * 50)
        self.assertEqual(seen[0]["timeout"], int(round(preship.RENDER_TIMEOUT_S * render_bound.CAP)), seen)


RED_PROOF = [
    {"why": "v3898 (#200, REG-3712) - the rehearsal kills the render at its fixed 360 s again on a busy Mac",
     "file": "tv/preship.py",
     "find": "    return int(round(timeout * k)), env, k\n",
     "replace": "    return int(timeout), env, k\n",
     "matches": 1},
    {"why": "v3898 (#200, REG-3712) - render_check is no longer told the factor, so its own deadline stays fixed",
     "file": "tv/preship.py",
     "find": "    env[\"TV_RENDER_SCALE\"] = env[\"GATE_SCALE\"] = \"%.2f\" % k\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
