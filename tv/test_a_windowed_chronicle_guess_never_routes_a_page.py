# -*- coding: utf-8 -*-
"""#255 (v3881, REG-3383) - AT AN ASPECT NOBODY CALIBRATED, A CHRONICLE GUESS NEVER ROUTES A PAGE.

MEASURED 2026-11-07 on the reader-parity bench (tv/reader_parity.py): a GAMEPLAY frame from a Windows PC that plays D2R
windowed, in the bench's caption-cut variant (800x383, aspect 2.089 - the old capture's frame minus its caption, which also
lost the client's bottom strip; the v3881 capture delivers the WHOLE client, ~2.0 on that PC, still outside the window), made
chronicle_template.detect() answer is_chronicle=True - votes 2/4 ['secondary-gold', 'list-stone'], close_x_red 0.0000,
sec_gold 0.0065, list_midgray 0.5478, no tab marker. The Grok CLI, shown the frame cold, called it gameplay. The Mac's
calibration window is 1.45-1.62; at 2.09 every band goes through _scale_band_for_aspect, DERIVED NOT MEASURED.

What keeps that harmless today is a JOIN, not the threshold: (1) detect() reports a tab only off a clean tab-marker vote and
only for a frame it calls Chronicle; (2) a derived-aspect reading is capped at 0.6 and says UNCONFIRMED; (3) the console's one
template consumer (_chron_sweep_run's _classify_one) routes a frame as a Chronicle page ONLY when that tab names a ledger, and
otherwise falls through to the paid read. No production code reads is_chronicle alone (grep, 2026-11-07).

The vote rule itself is NOT changed here, on purpose: one negative and ZERO real windowed Chronicle frames is a guess, not a
calibration - every Chronicle session in the windowed PC's reels was filmed as a DESKTOP frame (REG-3377, the bug v3881
fixes). The calibration is owed on the first client-only Chronicle frames that capture produces. RED_PROOF below.
[[unknown-stays-unknown]] [[the-unjoined-end]]
"""
import io
import os
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

import chronicle_template as ct  # noqa: E402

# the signals the bench read off the caption-cut windowed gameplay frame, verbatim
WINDOWED_GAMEPLAY = {"size": [800, 383], "aspect": 2.0888, "band_branch": "derived-not-measured", "close_x_red": 0.0,
                     "search_bright": 0.0, "list_midgray": 0.5478, "sec_gold": 0.0065,
                     "tab_border": {"unique": 0.0, "sets": 0.0, "runewords": 0.0},
                     "tab_marker": {"unique": 0.0, "sets": 0.0, "runewords": 0.0}}


def _detect(sig, tab=None):
    """drive detect() on a signal set, with resolve_tab answering `tab` when one is given"""
    old_sig, old_tab = ct.geometry_signals, ct.resolve_tab
    try:
        ct.geometry_signals = lambda _p: dict(sig)
        if tab is not None:
            ct.resolve_tab = lambda _s: (tab, "stub: a clean %s marker" % tab)
        return ct.detect("unused.jpg")
    finally:
        ct.geometry_signals, ct.resolve_tab = old_sig, old_tab


def _console_branch():
    src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
    start, end = "                _det = _ct.detect(p) or {}", '                    return {"scene": "chronicle",'
    if src.count(start) != 1:
        raise AssertionError("the console's template call moved - re-point this law (%d)" % src.count(start))
    i = src.index(start)
    blk = src[i:src.index(end, i)]
    return "\n".join(l.split("#", 1)[0].rstrip() for l in blk.split("\n"))


class AWindowedGuessNeverRoutes(unittest.TestCase):

    def test_the_measured_windowed_gameplay_frame_carries_no_tab(self):
        """* THE POINT: the 2-vote windowed guess is unconfirmed, capped, and names no tab - so no ledger"""
        d = _detect(WINDOWED_GAMEPLAY)
        self.assertTrue(d["is_chronicle"], "the fixture no longer reproduces the measured 2-vote guess - it proves nothing")
        self.assertIsNone(d["tab"], "a tab-less windowed guess named a tab")
        self.assertIsNone(ct.ledger_kind_for_tab(d["tab"]), "a tab-less guess resolves to a ledger")
        self.assertLessEqual(d["confidence"], 0.6, "a derived-aspect reading claims more than its cap")
        self.assertIn("UNCONFIRMED", d["why"])

    def test_baseline_a_clean_marker_at_the_same_aspect_is_routed(self):
        """BASELINE - the case can tell the two apart: with a clean tab marker the same frame DOES name a ledger"""
        d = _detect(WINDOWED_GAMEPLAY, tab="unique")
        self.assertEqual(d["tab"], "unique")
        self.assertIsNotNone(ct.ledger_kind_for_tab(d["tab"]))
        self.assertLessEqual(d["confidence"], 0.6, "the cap must hold even when a marker votes")

    def test_a_marker_on_a_frame_that_is_not_chronicle_is_withheld(self):
        gold_and_marker = dict(WINDOWED_GAMEPLAY, list_midgray=0.0)
        d = _detect(gold_and_marker, tab="sets")
        self.assertTrue(d["is_chronicle"], "marker + gold is two votes - the fixture moved")
        no_vote = dict(WINDOWED_GAMEPLAY, list_midgray=0.0, sec_gold=0.0)
        d = _detect(no_vote, tab="sets")
        self.assertFalse(d["is_chronicle"])
        self.assertIsNone(d["tab"], "a marker alone made a non-Chronicle frame carry a tab")

    def test_the_console_routes_a_page_only_on_a_tab_that_names_a_ledger(self):
        c = _console_branch()
        a = c.index('_tab = _det.get("tab")')
        b = c.index("_kind = _ct.ledger_kind_for_tab(_tab)")
        k = c.index("if _kind:")
        self.assertLess(a, b)
        self.assertLess(b, k)
        self.assertNotIn("is_chronicle", c, "the console routes on is_chronicle - a windowed guess would become a page")


RED_PROOF = [
    {"why": "REG-3383 - the console routes a tab-less Chronicle guess as a uniques page",
     "file": "tv/control_app.py", "find": '                _tab = _det.get("tab")\n',
     "replace": '                _tab = _det.get("tab") or ("unique" if _det.get("is_chronicle") else None)\n', "matches": 1},
    {"why": "REG-3383 - a derived-aspect reading claims its full confidence again",
     "file": "tv/chronicle_template.py", "find": "        score = min(score, 0.6)\n", "replace": "        score = score\n",
     "matches": 1},
    {"why": "REG-3383 - detect() names a tab off is_chronicle alone, with no clean marker",
     "file": "tv/chronicle_template.py", "find": "    tab = tab_candidate if is_chronicle else None\n",
     "replace": '    tab = (tab_candidate or "unique") if is_chronicle else None\n', "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
