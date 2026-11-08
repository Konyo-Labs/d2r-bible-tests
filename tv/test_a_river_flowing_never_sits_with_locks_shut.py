# -*- coding: utf-8 -*-
"""v3882 (#120) - ONE FLEET ROW NEVER SAYS "RIVER FLOWING" AND "LOCKS SHUT" ABOUT THE SAME MOMENT: THE RIVER'S DOORS ARE SAID
FROM WHAT THE RIVER OBEYS.

MEASURED 11-07 21:19 on the Mac's own beacon, as both ALTs saw it: heart.locksShut = [] (may() named no river lock shut,
3.8 s before the report) while census = stale, so the row drew "river flowing - 13 held by the drain" AND "locks shut - until
this PC proves". The Grok CLI's cold look at the open row: "river flowing sits with locks shut; CANNOT TELL if that is one
claim or two". Two checks disagreed - the finding: the "flowing" chip read may()'s answer on the river's own four doors
(REG-3197), the "locks shut" chip read the census's age alone. may() is what the river obeys; the census age is the PROOF's.

Now while may()'s answer is fresh (30 min; the lane does not ask while he plays) and names no door shut and no gate is
blind, the row says "river locks open" in amber (the proof's age rides its hover - the row's word line already says it,
the Grok CLI's look at v3882's render: the two "repeat the same complaint") and never "locks shut"; an answer that names a shut door, a
blind gate, no answer, or an old one keeps the census rule - fail closed, "locks shut". Drives the page's own _fleetStuckChip
(with the boot helpers it reads) in node through test_one_river_chip_per_row's harness; the parts reader's line is pinned on
its own code. RED_PROOF below. [[the-unjoined-end]] [[stale-reading]] [[unknown-stays-unknown]]
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import test_one_river_chip_per_row as H  # noqa: E402  (the cut-and-run harness for _fleetStuckChip)

HELD = [{"station": "CAPTURE", "n": 13, "oldestS": 9 * 86400, "window": False,
         "why": "older than the newest 16 - held by the drain, not owed: 13 panels-never-banked (no bank yet)"}]
STALE = {"census": "stale", "key": "stale", "blind": 0}


def _h(**o):
    d = dict(STALE)
    d.update(o)
    return d


class ARiverFlowingNeverSitsWithLocksShut(unittest.TestCase):

    def test_the_measured_row_says_one_story(self):
        """* THE POINT - 11-07 21:19: may() named no door shut 3.8 s before, the census stale - flowing, and the proof's age"""
        html = H._html(_h(locksShut=[], locksAgeS=3.8), HELD, 60)
        self.assertIn("river flowing · 13 held by the drain", html)
        self.assertNotIn("locks shut", html, "the row says flowing AND locks shut again: %r" % html[:400])
        self.assertIn(">river locks open</span>", html)
        self.assertIn("its proof is stale", html, "the proof's age left the chip's hover")

    def test_a_shut_door_or_a_blind_gate_keeps_locks_shut(self):
        html = H._html(_h(locksShut=["reel.route"], locksAgeS=3.8), HELD, 60)
        self.assertIn("locks shut", html)
        self.assertNotIn("river flowing", html)
        html = H._html(_h(locksShut=[], locksAgeS=3.8, blind=1), HELD, 60)
        self.assertIn("locks shut", html)
        self.assertNotIn("river locks open", html)

    def test_no_answer_or_an_old_one_fails_closed(self):
        """the census rule decides when may() has not answered, or answered past 30 min (he played since)"""
        for heart in (_h(), _h(locksShut=None, locksAgeS=None), _h(locksShut=[], locksAgeS=None),
                      _h(locksShut=[], locksAgeS=7200.0)):
            html = H._html(heart, HELD, 60)
            self.assertIn("locks shut", html, heart)
            self.assertNotIn("river locks open", html, heart)

    def test_the_parts_reader_never_says_locks_are_shut_over_open_doors(self):
        """the row's 'stuck' part (what the State panel and the PC's word read) asks the same doors"""
        with io.open(H.UI, encoding="utf-8") as fh:
            ui = fh.read()
        code = "\n".join(l.split("/*", 1)[0] for l in ui.split("\n"))
        self.assertIn("      if ((_hs === 'missing' || _hs === 'stale' || _hs === 'unreadable') && _doorsOpen !== true) {", code)
        self.assertIn("      var _doorsOpen = (typeof _fleetRiverDoorsOpen === 'function') ? _fleetRiverDoorsOpen(rv.heart) : null;", code)


RED_PROOF = [
    {"why": "#120 - the lock chip reads the census alone again: 'river flowing' beside 'locks shut'",
     "file": "tv/control_ui.html",
     "find": "    if ((census === 'missing' || census === 'stale' || census === 'unreadable') && _doorsOpen === true) {\n",
     "replace": "    if (false) {\n", "matches": 1},
    {"why": "#120 - an old may() answer (he played since) is trusted as open",
     "file": "tv/control_ui.html",
     "find": "    if (!(typeof hs.locksAgeS === 'number' && isFinite(hs.locksAgeS) && hs.locksAgeS >= 0 && hs.locksAgeS <= FLEET_LOCKS_FRESH_S)) return null;\n",
     "replace": "", "matches": 1},
    {"why": "#120 - a blind gate reads as open doors",
     "file": "tv/control_ui.html",
     "find": "    if (typeof hs.blind === 'number' && hs.blind > 0) return false;\n",
     "replace": "", "matches": 1},
    {"why": "#120 - the parts reader says 'the locks are shut' over open doors again",
     "file": "tv/control_ui.html",
     "find": "      if ((_hs === 'missing' || _hs === 'stale' || _hs === 'unreadable') && _doorsOpen !== true) {\n",
     "replace": "      if (_hs === 'missing' || _hs === 'stale' || _hs === 'unreadable') {\n", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
