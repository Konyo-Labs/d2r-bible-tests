# -*- coding: utf-8 -*-
"""v2729 — A CENTRED LABEL WITH NO WIDTH BOUND IS A COLLISION WAITING FOR MORE DATA.

The heart's lock fan draws each lock's lines with `text-anchor="middle"` at a point chosen by its
INDEX in a sorted list (control_ui.html: `reach = [0.78, 1.06, 1.34][j % 3]`). Position comes from
the index; WIDTH comes from the content; nothing ever compares them. So the fan is correct only for
the content it happened to hold when someone last looked at it.

PROVEN BY CAUSING IT, 2026-09-06: banking evidence into `reel.route` and `frame.release` changed
nothing but the NUMBERS inside two labels, and `overlap_ratchet` went 2 -> 4 at 1120, 1440 and 901,
and 0 -> 2 at 375. No code was touched. That is why this file pins WIDTH BOUNDS rather than a
layout: the layout cannot be made safe while any label can grow without limit.

WHAT THIS PINS, AND WHY EACH IS A LAW AND NOT A STRING
------------------------------------------------------
1. THE BLIND-CLAIMS LABEL MUST NOT INTERPOLATE AN UNBOUNDED LIST. It read
       arith = k + '/' + n + ' on the claims that RAN · ' + blind.length + ' never ran (' +
               _blind.join(', ') + ')'
   — every blind claim's NAME, joined, into a centred label. Measured at 1440: 313px, against lock
   names of 89-104px. THREE TIMES WIDER than the thing it belongs to, and growing with every claim
   added. Bounding it is what took 375 back to zero.
   ⚠ THE COUNT IS THE FACT AND MUST SURVIVE. "3 never ran" is the claim a reader acts on; the names
   are detail. A bound that dropped the number instead of the names would be the wrong half.

2. NO LABEL PRINTS ITS OWN SCORE TWICE. The second arithmetic line appended ' → ' + wilsonByAttack,
   and the first line already prints the deciding score — which IS wilsonByAttack for every lock in
   this fan (`deciding` is `wilsonByAttack`). ~40px of width for a number already on screen, one
   line up, where it is compared against its bar and therefore means something.

⚠⚠ WHAT THIS FILE DELIBERATELY DOES NOT DO: it does not pin an overlap COUNT. `overlap_ratchet`
owns that, it is baselined, and it can only run where the live console is. This file runs anywhere
and grades the one thing that is checkable from source — that no label can grow without limit.
A gate that cannot run on CI is not a substitute for one that can. [[regression-guard]]
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

UI = os.path.join(HERE, "control_ui.html")


def _src():
    return io.open(UI, encoding="utf-8").read()


def _nocomments(src):
    """JS/CSS comments stripped, because a law that greps SOURCE cannot tell code from prose.

    ⚠⚠ THIS FILE'S OWN FIRST RUN PROVED THE NEED. The v2729 comment explaining the fix QUOTES the
    defective line it replaced — "It interpolated `_blind.join(', ')`" — so the law forbidding
    `_blind.join(` matched the explanation of why `_blind.join(` was removed, and failed on a tree
    where the fix was correctly applied. A guard that reads its own documentation as a violation
    is the [[source-reading-guard]] shape exactly, and it cost this repo four false readings in a
    day before it was carved.
    """
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)      # block comments, including the /* ⚠ */ ones
    src = re.sub(r"(?m)^\s*//.*$", " ", src)               # whole-line // comments
    return src


def _between(src, start, end, whence=0):
    """A window anchored at BOTH ends — never `src[i:i+N]`. [[source-reading-guard]]"""
    i = src.find(start, whence)
    if i < 0:
        return None
    j = src.find(end, i + len(start))
    return None if j < 0 else src[i:j + len(end)]


class HeartFanLabelsAreWidthBounded(unittest.TestCase):

    def setUp(self):
        self.raw = _src()
        self.s = _nocomments(self.raw)

    def test_the_guard_can_find_the_fan_at_all(self):
        """⚠ A law that finds nothing to grade passes by examining ZERO candidates."""
        # ⚠⚠ COUNT THEM. The first cut asked only whether "hrt-fan" appeared AT ALL, so renaming
        # ONE of the three stacked lines left two behind and the law stayed green while a third of
        # the fan had left the vocabulary. A presence check over a set is a check on the set's
        # loudest member. [[zero-needs-a-denominator]]
        # REG-3091 - the three lines are now DECLARED as a stack's lines (`cls: 'hrt-fan ...'`) and drawn after the
        # placement pass, so a line is counted in either form; renaming one still drops the count below three.
        n_fan = self.raw.count('class="hrt-fan') + self.raw.count("cls: 'hrt-fan ")
        self.assertGreaterEqual(
            n_fan, 3,
            "only %d fan label line(s) carry the `hrt-fan` class; each lock draws THREE (name, "
            "arithmetic, second arithmetic). A renamed line silently leaves the vocabulary this "
            "file and any future fit pass select on." % n_fan
        )
        self.assertRegex(
            self.s, r"reach\s*=\s*\[",
            "the fan's radial tiering is gone, so the geometry this file reasons about no longer "
            "exists and its laws may be grading a shape that left."
        )

    # ── law 1: no unbounded interpolation into a centred label ────────────────────────────────
    def test_the_blind_claims_list_is_BOUNDED(self):
        blk = _between(self.s, "if (_blind) {", "}")
        self.assertIsNotNone(blk, "the blind-claims branch is gone")
        self.assertNotRegex(
            blk, r"_blind\.join\(",
            "the blind-claims label joins the FULL list of claim names into a centred label again. "
            "Measured 2026-09-06 that made it 313px against lock names of 89-104px, and it grows "
            "with every claim added — a width with no bound, drawn at a position chosen by index. "
            "Bound it (a slice plus '+N more') and keep the COUNT."
        )
        self.assertRegex(
            blk, r"_blind\.slice\(",
            "the blind list is no longer bounded by a slice, so nothing caps how wide this label "
            "can become."
        )

    def test_the_blind_COUNT_survives_the_bound(self):
        """⚠ The names are detail; the COUNT is the fact a reader acts on."""
        blk = _between(self.s, "if (_blind) {", "}")
        self.assertIsNotNone(blk)
        # ⚠⚠ PIN IT IN THE OUTPUT STRING, NOT ANYWHERE IN THE BLOCK. The first cut asserted only
        # that "_blind.length" appeared SOMEWHERE in the branch — and the bound itself contains
        # `_blind.length > 2`, so deleting the count from the rendered sentence left the law GREEN.
        # A law satisfied by a mention of the right name in the wrong place is measuring the file,
        # not the output. Caught by sabotage, not by reading. [[source-reading-guard]]
        self.assertRegex(
            blk, r"\+\s*_blind\.length\s*\+\s*'\s*never ran",
            "the COUNT is no longer interpolated into the label's own sentence. '3 never ran' is "
            "the claim a reader acts on; the names are detail. Bounding the label must not cost "
            "the number — and having `_blind.length` elsewhere in the branch is not the same as "
            "PRINTING it."
        )

    # ── law 2: a label never prints the same number twice ─────────────────────────────────────
    def test_the_second_line_does_not_REPRINT_the_deciding_score(self):
        blk = _between(self.s, "var arith2 = _blind", "var waiting")
        self.assertIsNotNone(blk, "arith2 is gone, or `var waiting` no longer follows it")
        self.assertNotRegex(
            blk, r"_wba\s*!==\s*null\s*\?\s*'\s*\\u2192",
            "the second arithmetic line appends the wilsonByAttack score again. The FIRST line "
            "already prints the deciding score, and `deciding` is `wilsonByAttack` for every lock "
            "in this fan — so the label prints its own score twice and pays ~40px of width for it, "
            "reaching further into BOTH neighbours because it is centred."
        )

    def test_the_score_is_still_printed_ONCE(self):
        """⚠ Removing a duplicate must not remove the original. [[unknown-stays-unknown]]"""
        blk = _between(self.s, "var arith = (n_ && n_ > 0)", "var _blind")
        self.assertIsNotNone(blk, "the first arithmetic line is gone")
        self.assertRegex(
            blk, r"_sc\s*==\s*null\s*\?\s*'\?'\s*:\s*_sc\.toFixed",
            "the first arithmetic line no longer prints the deciding score. v2729 removed the "
            "DUPLICATE on the second line on the strength of this one existing; if this goes, the "
            "score is nowhere and the removal became a deletion."
        )

    # ── the reverted experiment must stay reverted ────────────────────────────────────────────
    def test_no_vertical_dodge_pass_came_back(self):
        """⚠ IT MADE THE NUMBER WORSE. A post-layout pass that nudged each lock's grouped lines
        downward took 1120 and 901 from 4 overlaps to FIVE, because the fan opens DOWNWARD and
        pushing a group down drives it into the next one. Measured, then removed. If a future
        change reintroduces it, this fails and points at the measurement rather than the idea.
        """
        self.assertNotIn(
            "_hrtFitFan", self.s,
            "a post-layout fit pass is back in control_ui.html. The last one was measured and made "
            "the overlap count WORSE (4 -> 5 at two widths). If this is a new attempt, it must be "
            "measured with `python3 tv/overlap_ratchet.py --check` BEFORE it lands, and this law "
            "updated with the number it achieved."
        )


RED_PROOF = [
    {
        'why': "v2729 — the blind-claims label interpolated EVERY blind claim's name into a centred label positioned by INDEX and sized by CONTENT: measured 313px at 1440 against lock names of 89-104px, growing without limit as claims are added. `_blind.slice(0, 2)` is the only width bound; deleting it restores the unbounded join the fan was measured to collide on (overlap_ratchet 2->4 at three widths, 0->2 at 375, with no code touched).  MEASURED: untampered OK — Ran 6 tests, 0 failures (python3 tv/test_heart_fan_labels_are_width_bounded.py); tampered (all 1) FAILED (failures=1) — only test_the_blind_claims_list_is_BOUNDED went red; reddened law test_heart_fan_labels_are_width_bounded.HeartFanLabelsAreWidthBounded.; ALONE FAILS ALONE — `python3 -m unittest test_heart_fan_labels_are_width_bounded.HeartFanLabelsAreWidthBounded.test_.",
        'file': 'control_ui.html',
        'find': "_blind.slice(0, 2).join(', ')",
        'replace': "_blind.join(', ')",
        'matches': 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
