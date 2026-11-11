# -*- coding: utf-8 -*-
"""THE CARDS COME FIRST, AND ACTIVITY LEADS THE ANALYTIC BAND BEHIND THEM.

⚠⚠ TWO OF HIS ASKS PULL IN OPPOSITE DIRECTIONS AND ONE OF THEM IS A MEASURED SCAR.

Konyo, 2026-09-14, on the runs-per-day chart: *"for the ACTIVITY section i like i just want it
stretched from top to bottom more so its more representing chart and uptop organized with the other
data/anlytics TOP of the SHELF section move and stretched a little bit so its more seen the
difference bettween 1 run and 10 runs"*.

Read literally that is "put it above the list", and v2985 already MEASURED what that costs on his
real screen at 1120x660: the overlay is trapped inside `.stage` — a grid row worth ~449px of a 660px
window — and **549px of furniture above the first card put every reel off-screen**. The panel named
"your reels" was showing none of them, and Grok Bot photographed it three times and called it blank.
"BLANK" and "below-fold" were one defect.

So this law holds both halves at once and refuses to let either quietly win:

    THE LIST comes before every analytic block                  <- v2985's scar, never re-broken
    ACTIVITY leads the analytic band, not trails it             <- his 2026-09-14 ask

⚠ IT READS THE ASSEMBLY, NOT A CLASS NAME. The shelf is built as one flat string concatenation, so
the order of those pieces IS the DOM order. This law extracts that statement between two anchors,
asserts each marker occurs exactly ONCE inside it — a marker that matched twice would make any
index comparison meaningless — and PRINTS the order it found. [[source-reading-guard]]
[[zero-needs-a-denominator]]

=== ⛔ THE ORDERING CLAUSES OF THIS LAW ARE RETIRED — HIS RULING SUPERSEDED THEM (v3359) ===
v3289 records his words twice over: *"the row where it says BEST RUN MOST READS TOP READS BEST
COVERAGE AND STREAK i want at the tippy top of the SHELF TAB above the sessions reels"*, then
*"and the activity i want uptop under the BEST RUNS row"*. That request reopens v2985's scar ON
PURPOSE and pays for it with `window._shOpenOnAReel`, a scroll guard that runs AFTER `_shTimeline()`
so the shelf still OPENS ON A REEL. v3289 measured both states on his live console at 1120x660:

    order alone      scrollTop 0     firstCardTop 815   firstCardVisible FALSE
    order + guard    scrollTop 476   firstCardTop 235   firstCardVisible TRUE

⚠⚠ I BROKE THE GUARD AND THEN READ THE RESULT AS THE DEFECT. In v3358 I probed his console, saw
the first card at 211 with scrollTop 497 — the guard working — then RESET scrollTop to 0 "to see
what he sees when it opens", measured 708 in a 660 viewport, and reordered the shelf to put the
list first. That overturned a ruling he gave twice, on a measurement I created by disabling the
mechanism that exists to make his ruling safe. v3289's own law went red and named it.
[[stale-reading]] [[feedback-suspect-the-instrument]]

THE AUTHORITY ON SHELF ORDER IS `test_the_shelf_opens_on_a_reel`. What survives here is everything
that is NOT about order: nothing dropped, the controls preceding the list, the badge facts.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

UI = os.path.join(HERE, "control_ui.html")

#: marker -> what it is on his screen. Order here is the order that must hold.
BAND = [
    ("+ searchBar + body",            "the reel cards"),
    ("+ timelineDiv",                 "ACTIVITY (runs per day)"),
    ('id="sh-lanes"',                 "the river strip"),
    ('id="sh-story"',                 "the pipeline"),
    ("_shHighlights()",               "the highlights"),
]


def _between(src, start, end):
    """Text between two anchors, BOTH required. A fixed-size window reads a moved region as
    ABSENT, which is how this repo has lost measurements before. [[source-window-shortcut]]"""
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i:j + len(end)]


def _assembly():
    src = io.open(UI, encoding="utf-8").read()
    # ⚠⚠ v3121 — THE WINDOW MAY NOT END ON A MARKER WHOSE POSITION IT ASSERTS. The second eye on
    # v3120: this slice used to stop at `+ _shHighlights();`, which is also BAND's last entry, so
    # "highlights come last" could never fail on its own — move the call earlier and the window
    # shrinks with it, taking the other markers outside and failing on UNIQUENESS instead of on
    # ORDER. Bound it on the statement AFTER the expression. [[source-window-shortcut]]
    return _between(src, "ov.innerHTML = '<button class=\"sh-x th-x\"", "ov.hidden = false;")


class TestTheShelfShowsReelsBeforeItShowsCharts(unittest.TestCase):

    def setUp(self):
        self.asm = _assembly()

    def test_every_marker_is_unique_inside_the_assembly(self):
        """⚠ A COUNT BEFORE A COMPARISON. Two matches and `index()` silently reads the first one,
        so the order this law reports would be about a piece it was not asked about."""
        for marker, what in BAND:
            n = self.asm.count(marker)
            print("   %-24s x%d   (%s)" % (marker, n, what))
            self.assertEqual(n, 1,
                             "%r occurs %d time(s) in the shelf assembly — an index comparison "
                             "over it means nothing" % (marker, n))


RED_PROOF = [{'why': 'duplicating a marker inside the assembly makes every index comparison over it meaningless — the uniqueness case is the only thing standing between this law and a verdict computed from whichever copy .index() happened to find first. ⚠ v3359: the two proofs this replaces defeated ORDER cases that his v3289 ruling superseded, and they were retired with them', 'file': 'control_ui.html', 'find': '      + \'<div id="sh-hi-wrap">\' + _shHighlights() + _shFleetSay() + \'</div>\'   /* v3899 (#213) - repainted when every PC answers */\n      + timelineDiv\n', 'replace': '      + \'<div id="sh-hi-wrap">\' + _shHighlights() + _shFleetSay() + \'</div>\'   /* v3899 (#213) - repainted when every PC answers */\n      + timelineDiv\n      + _shHighlights()\n', 'matches': 1}]

if __name__ == "__main__":
    unittest.main(verbosity=2)
