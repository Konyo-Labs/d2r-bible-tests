# -*- coding: utf-8 -*-
"""v3855 (REG-3129) - EVERY WAIT INSIDE ONE RENDER TARGET STRETCHES BY THE SAME TV_RENDER_SCALE AS THE RUN.

v3853 push 9 went red on advanced-fleet: its rows did not paint within _selector_ready's fixed 20s at load 6.8. The hook
had stretched the run's limits (_CLEAN_RUN_COST, _RUN_REPORT_BY) by TV_RENDER_SCALE, but not the per-target paint,
settle, activate and warmup waits. They now all go through _scaled_wait(), which never shrinks a wait (the scale is
clamped to [1, 2.5]), and a target's wait-expired refusal says how far it was stretched.

Static and in-process only: no browser, no page.
"""
import importlib
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

SRC_PATH = os.path.join(HERE, "render_check.py")


def _src():
    with io.open(SRC_PATH, encoding="utf-8") as fh:
        return fh.read()


def _body(src, name):
    m = re.search(r"^def %s\(.*?(?=^def |\Z)" % re.escape(name), src, re.S | re.M)
    return m.group(0) if m else ""


class ATargetWaitStretches(unittest.TestCase):
    def test_paint_and_settle_waits_read_the_scale(self):
        src = _src()
        for fn in ("_settled", "_selector_ready"):
            self.assertIn("budget = _scaled_wait(budget)", _body(src, fn), fn + " does not stretch its budget")

    def test_activate_and_warmup_read_the_scale(self):
        src = _src()
        self.assertNotRegex(src, r"float\(spec\.get\(\"activate_budget\"\)", "an activate wait is unscaled")
        self.assertNotRegex(src, r"_cap = float\(spec\.get\(\"warmup\"\)", "the warmup wait is unscaled")
        self.assertEqual(src.count("_scaled_wait(spec.get(\"activate_budget\")"), 2)
        self.assertIn("_cap = _scaled_wait(spec.get(\"warmup\")", src)

    def test_expired_waits_name_the_stretch(self):
        src = _src()
        self.assertIn('"everything" % budget) + _stretch_note()', _body(src, "_settled"))
        self.assertEqual(_body(src, "_selector_ready").count("% (sel, budget)) + _stretch_note()"), 2)
        self.assertIn("% (time.time() - _t0) + _why + _stretch_note())", src)

    def test_the_scale_never_shrinks_and_is_reported(self):
        old = os.environ.get("TV_RENDER_SCALE")
        try:
            for raw, want in (("2.0", 2.0), ("0.3", 1.0), ("9", 2.5), (None, 1.0)):
                if raw is None:
                    os.environ.pop("TV_RENDER_SCALE", None)
                else:
                    os.environ["TV_RENDER_SCALE"] = raw
                import render_check
                rc = importlib.reload(render_check)
                self.assertAlmostEqual(rc._scaled_wait(20.0), 20.0 * want)
                self.assertGreaterEqual(rc._scaled_wait(20.0), 20.0)
                self.assertEqual(bool(rc._stretch_note()), want > 1.0)
                if want > 1.0:
                    self.assertIn("x%.2f" % want, rc._stretch_note())
        finally:
            if old is None:
                os.environ.pop("TV_RENDER_SCALE", None)
            else:
                os.environ["TV_RENDER_SCALE"] = old
            import render_check
            importlib.reload(render_check)


_F = "render_check.py"
RED_PROOF = [{'why': '_selector_ready keeps its fixed 20s',
  'file': 'render_check.py',
  'find': '    budget = _scaled_wait(budget)  # TARGET-WAIT-SCALED (REG-3129)\n    t0 = time.time()\n',
  'replace': '    t0 = time.time()\n',
  'matches': 1},
 {'why': 'the activate wait is unscaled',
  'file': 'render_check.py',
  'find': '_t0 + _scaled_wait(spec.get("activate_budget")',
  'replace': '_t0 + float(spec.get("activate_budget")',
  'matches': 1},
 {'why': 'the warmup wait is unscaled',
  'file': 'render_check.py',
  'find': '_cap = _scaled_wait(spec.get("warmup") or 1.6)',
  'replace': '_cap = float(spec.get("warmup") or 1.6)',
  'matches': 1},
 {'why': 'a wait can shrink below its declared seconds',
  'file': 'render_check.py',
  'find': '    return float(secs) * max(1.0, _RENDER_SCALE)\n',
  'replace': '    return float(secs) * 0.5\n',
  'matches': 1},
 {'why': 'the activation refusal does not name the stretch',
  'file': 'render_check.py',
  'find': '% (time.time() - _t0) + _why + _stretch_note())',
  'replace': '% (time.time() - _t0) + _why)',
  'matches': 1}]

if __name__ == "__main__":
    unittest.main(verbosity=1)
