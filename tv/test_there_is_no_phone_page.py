# -*- coding: utf-8 -*-
"""v3889 (#132, REG-3489) - THERE IS NO PHONE PAGE: NO PHONE BAR, AND NO GATE RENDERS AT A PHONE WIDTH.

His ruling, 11-08 ~12:30 IST: "forget the MOBILE PAGE COMPELTELY drop it", "i dont need any mobile anything". He plays and
reads the board on his PCs (1512, 1120, Dean's windowed 800-wide console); a phone width cost every render target a fourth
pass, ~40 laws a phone case, and GitHub rounds on phone-only geometry nobody uses.

INVERTED, NOT DELETED (GATE_MOVES_WITH_PRODUCT): this law fails if the phone page comes back -
  * the REG-3090 phone tray bar is gone: no #tray-bar element, no --tray-bar-h, no reg3090 stylesheet, no
    _trayBarH / _dockReserve fold, and the 600px band's dock reserve is the dock alone;
  * render_check renders at no phone width: its default WIDTHS and every target's own widths stay >= 700px, no target
    is a phone-bar, and none is parked waiting to come back.

TOMBSTONES - what left with the phone page, and where it went:
  * tv/test_on_a_phone_the_tray_is_one_bottom_bar.py (REG-3090: the tray orbs ride one bar under the dock at <=600px) -
    REMOVED with the bar. Nothing replaces it: the bar is gone by his decision, and THIS law holds that it stays gone.
  * render_check target `phone-bar` (the bar's pixels on CI) - REMOVED with the bar.
  * tv/test_a_quick_wins_place_reads_on_a_phone.py (#125 at 390px) - REMOVED: it measured only at 390. The Quick wins
    grid at the widths he uses is held by test_quick_wins_shows_each_place_with_its_picture and the quick-wins render
    target (1440 / 1120 / 901).
  * the 375 / 390 widths inside the browser laws that measured a range (builder, mule window, Fleet card, rails fold,
    roster eyes, card names) - dropped from their lists; their wider widths still run.
The sub-700px layout CSS that is not the bar (the narrow dock bands, the phone header rules) is the second half of #132:
dead on every screen he uses, read and removed block by block - this law does not claim it yet.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
import render_check as R  # noqa: E402

PHONE_MAX = 700     # the narrowest width he uses is Dean's ~800-wide window; anything under this is a phone


def _bible():
    with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


class ThereIsNoPhoneBar(unittest.TestCase):

    def test_the_tray_bar_is_gone_from_the_page(self):
        src = _bible()
        for gone in ('id="tray-bar"', "--tray-bar-h", 'id="reg3090-phone-tray-bar"', "_trayBarH", "_dockReserve"):
            self.assertNotIn(gone, src, "the phone tray bar is back in bible.html: %r" % gone)

    def test_the_600px_band_reserves_the_dock_alone(self):
        src = _bible()
        head = "@media (max-width: 600px){\n  :root{ --dock-h: "
        self.assertEqual(src.count(head), 1, "PREMISE: the 600px dock band moved - re-point this law")
        line = src[src.index(head):src.index("\n", src.index(head) + len(head))]
        self.assertIn("--dock-h: 225px;", line, "the 600px band folds something besides the dock again: %s" % line)


class NoGateRendersAtAPhoneWidth(unittest.TestCase):

    def test_the_default_widths_have_no_phone(self):
        narrow = [w for w, _h in R.WIDTHS if w < PHONE_MAX]
        self.assertEqual(narrow, [], "render_check's default widths render a phone again: %s" % narrow)
        self.assertGreater(len(R.WIDTHS), 2, "PREMISE: render_check renders at almost nothing")

    def test_no_target_renders_or_activates_at_a_phone_width(self):
        bad = []
        for name, spec in sorted(R.TARGETS.items()):
            for w, h in tuple(spec.get("widths") or ()):
                if w < PHONE_MAX:
                    bad.append("%s %dx%d" % (name, w, h))
            at = spec.get("activate_at")
            if at and at[0] < PHONE_MAX:
                bad.append("%s activates at %dx%d" % (name, at[0], at[1]))
        self.assertEqual(bad, [], "a render target measures a phone again: %s" % bad)
        self.assertGreater(len(R.TARGETS), 20, "PREMISE: render_check has almost no targets")

    def test_the_coverage_floors_name_no_phone(self):
        """v3889 - stage 1 removed the 375 floors and left phone-bar's own 600-wide floor: the render gate refused
        'the floor names this target and TARGETS no longer defines it'. A floor is a promise to measure."""
        import json
        with io.open(os.path.join(HERE, "render_coverage.json"), encoding="utf-8") as fh:
            cov = json.load(fh)
        bad = []
        for sect in ("floor", "nodes"):
            for name, ws in (cov.get(sect) or {}).items():
                if "phone" in name:
                    bad.append("%s %s" % (sect, name))
                for w in (ws or {}):
                    if int(str(w).split("x")[0]) < PHONE_MAX:
                        bad.append("%s %s %s" % (sect, name, w))
        self.assertEqual(bad, [], "the coverage ratchet still expects a phone surface: %s" % bad[:6])

    def test_no_phone_target_waits_to_come_back(self):
        names = list(R.TARGETS) + list(getattr(R, "PARKED_TARGETS", {}) or {})
        self.assertEqual([n for n in names if "phone" in n], [], "a phone target is listed or parked")


RED_PROOF = [
    {"why": "v3889 (#132) - the coverage ratchet expects the phone-bar surface again",
     "file": "tv/render_coverage.json",
     "find": "  \"floor\": {\n",
     "replace": "  \"floor\": {\n    \"phone-bar\": {\"600x900\": 1},\n",
     "matches": 1},
    {"why": "v3889 (#132) - render_check renders at 375 again",
     "file": "tv/render_check.py",
     "find": "WIDTHS = ((1440, 1000), (1280, 720), (1120, 900), (901, 900), (1120, 628))   # v3889 (#132) - no phone width",
     "replace": "WIDTHS = ((1440, 1000), (1280, 720), (1120, 900), (901, 900), (375, 800), (1120, 628))",
     "matches": 1},
    {"why": "v3889 (#132) - the phone tray bar's element is back in the page",
     "file": "bible.html",
     "find": "<button id=\"tvd-return-pill\" type=\"button\" onclick=\"window.switchTab&&window.switchTab('session')\">",
     "replace": "<div id=\"tray-bar\" aria-hidden=\"true\"></div>\n<button id=\"tvd-return-pill\" type=\"button\" onclick=\"window.switchTab&&window.switchTab('session')\">",
     "matches": 1},
    {"why": "v3889 (#132) - the 600px band folds the phone tray bar into the dock again",
     "file": "bible.html",
     "find": "  :root{ --dock-h: 225px; }   /* v3889 (#132, his 11-08 'no mobile anything') - the phone tray bar is gone; the dock alone */\n",
     "replace": "  :root{ --dock-h: calc(225px + var(--tray-bar-h, 0px)); }\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
