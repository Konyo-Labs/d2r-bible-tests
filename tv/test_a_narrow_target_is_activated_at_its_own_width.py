# -*- coding: utf-8 -*-
"""REG-3301 (#74) - A RENDER TARGET WHOSE SURFACE EXISTS ONLY AT A NARROW WIDTH IS ACTIVATED AT ONE OF ITS OWN WIDTHS.

v3864 parked the `phone-bar` target: it never ACTIVATED on CI, so the bottom bar's pixels were UNMEASURED. Measured on this
PC 2026-11-06 (the target run from PARKED_TARGETS): its own reason said "the bar is not drawn at 1440x1213 (0x0)".
check() polled `activate` at the harness's default viewport, and the bar exists only at <=600px - the target's widths
(375 and 600) were set only AFTER activation, in the width loop. With the viewport fixed, the next reason was
"the bar is not the bottom edge: 0,744 364x56": the check compared the bar to innerWidth (375), which counts the headless
desktop scrollbar (11px) that a fixed full-width bar never spans. With both fixed it rendered clean at 375 and 600.

So, held here without a browser (the pixels are the render gate's, on GitHub):
  * every target whose widths never reach the harness's own window width declares `activate_at`, and it is one of its widths;
  * check() sets `activate_at` BEFORE it polls `activate`;
  * phone-bar's activate measures the bar against the layout width (clientWidth), never innerWidth;
  * phone-bar is a TARGET again, not parked.
RED_PROOF below.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import render_check as R  # noqa: E402


def _src():
    with io.open(os.path.join(HERE, "render_check.py"), encoding="utf-8") as fh:
        return fh.read()


def _harness_width(src):
    m = re.search(r'"--window-size=(\d+),(\d+)"', src)
    assert m, "PREMISE: render_check launches its Chrome with no --window-size - the default width is unknown"
    return int(m.group(1))


class ANarrowTargetIsActivatedAtItsOwnWidth(unittest.TestCase):

    def test_every_narrow_only_target_declares_where_it_activates(self):
        default_w = _harness_width(_src())
        narrow = []
        for name, spec in sorted(R.TARGETS.items()):
            ws = tuple(spec.get("widths") or R.WIDTHS)
            if max(w for w, _h in ws) >= default_w:
                continue
            narrow.append(name)
            at = spec.get("activate_at")
            self.assertIsNotNone(at, "%s draws only at %s and declares no activate_at - it is activated at the harness's "
                                     "%d wide, where its surface does not exist" % (name, ws, default_w))
            self.assertIn(tuple(at), ws, "%s activates at %s, which is not one of its own widths %s" % (name, at, ws))
        self.assertIn("phone-bar", narrow, "PREMISE: phone-bar is the narrow-only target this law was written for")

    def test_check_sets_the_activation_viewport_before_it_polls(self):
        src = _src()
        body = src[src.index("\ndef check(name, spec, shots=True):"):]
        body = body[:body.index("\ndef ", 10)]
        at = body.find('if spec.get("activate_at"):')
        poll = body.find('act = tab.ev(spec["activate"])')
        self.assertGreater(poll, 0, "PREMISE: check() no longer polls a target's activate")
        self.assertGreater(at, 0, "check() never reads a target's activate_at")
        self.assertLess(at, poll, "check() sets activate_at only after it has polled activate")
        self.assertIn("Emulation.setDeviceMetricsOverride", body[at:poll])

    def test_the_bar_is_measured_against_the_layout_width(self):
        act = R.TARGETS["phone-bar"]["activate"]
        self.assertIn("var vw = document.documentElement.clientWidth;", act)
        self.assertNotIn("innerWidth - 1", act, "the bar is compared to innerWidth, which counts the headless scrollbar")
        self.assertNotIn("r.right > innerWidth", act)

    def test_phone_bar_is_a_target_again(self):
        self.assertIn("phone-bar", R.TARGETS)
        self.assertNotIn("phone-bar", getattr(R, "PARKED_TARGETS", {}) or {})


RED_PROOF = [
    {"why": "REG-3301 - phone-bar is activated at the harness's 1440 again, where the bar does not exist",
     "file": "tv/render_check.py",
     "find": "        \"activate_at\": (375, 800),",
     "replace": "        \"activate_at_note\": (375, 800),",
     "matches": 1},
    {"why": "REG-3301 - check() ignores a target's activate_at",
     "file": "tv/render_check.py",
     "find": "        if spec.get(\"activate_at\"):\n",
     "replace": "        if spec.get(\"activate_at_ignored\"):\n",
     "matches": 1},
    {"why": "REG-3301 - the bar is measured against innerWidth again (the headless scrollbar makes it 11px short)",
     "file": "tv/render_check.py",
     "find": "            var vw = document.documentElement.clientWidth;\n",
     "replace": "            var vw = innerWidth;\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
