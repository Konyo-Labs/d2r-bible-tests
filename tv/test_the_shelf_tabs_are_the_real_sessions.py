# -*- coding: utf-8 -*-
"""THE TABS ON TOP OF THE SHELF ARE BUILT FROM HIS REELS, NOT FROM A LIST.

He said it three times, escalating, because it kept not being done:
    "the tabs ontop need updating related to the reels sessions.. not random or outdated like it is"
    "and accorindgly relevant to the sessions"
    "the tabs within shelf on top need a fixing and updating so they represent the real reel
     sessions that its managing"

⚠⚠ AND THE FIRST TIME IT WAS "DONE" IT WAS HALF-DONE, BY ME. v3195 shipped `SHELF_F.station`, the
`st:` toggle branch, the filter clause in the predicate and the `active` flag — every half except
THE BUTTONS. So a complete, working filter sat in the file with nothing on screen able to reach
it. [[plumbing-with-no-tap]] in its purest form: both ends built, never joined, and it looked
finished from the code side.

THE RULES THIS PINS, each of which is what "not random or outdated" actually means:
  1. EVERY CHIP IS EARNED BY A CARD. The row is tallied from `data-station` on the visible cards,
     so a station with no reel gets no chip and the row can never show a stage his footage is not
     in.
  2. THE ORDER COMES FROM THE RIVER. `SHELF_RIVER_ORDER` is /api/river's own station sequence.
     This file already carries that ruling beside the sort selector — *"The station order is NEVER
     hardcoded here ... Two lists of stations is how they drift."* A hardcoded order would also
     silently drop any station reel_router gains. [[copy-drift]]
  3. AN UNMAPPED STATION IS MARKED, NEVER DROPPED. A stage the river order does not name is a
     finding about the router; hiding it makes the row lie by omission.
  4. AN EMPTY ROW HIDES ITSELF. Nothing stamped means the river has not answered — not that no
     stations exist. [[zero-needs-a-denominator]]
"""
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

UI = os.path.join(HERE, "control_ui.html")


def _py_only(src):
    """`#`-style and `//` comment lines out, block comments out — but NOT triple-quoted spans.

    ⚠ A "strip docstrings" filter would delete real code here, the way it deleted render_check's
    browser probe when this helper was first written elsewhere. Only comment syntax goes.
    """
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", " ", src)


def _fn_body(code, start):
    """-> the source of the JS function beginning at `start`, brace-balanced, or "".

    ⚠⚠ v3350 — A BYTE COUNT IS A GUESS ABOUT WHERE A FUNCTION ENDS, AND BOTH DIRECTIONS BITE.
    MEASURED in control_ui.html: `_shelfRefused` is 4,057 chars and its law read `src[i:i+1600]`,
    so 61% of the function it polices was never examined — under assertNotIn that is an absence
    reported without looking. `window._dossierClose` is 112 chars and its law read `src[i:i+260]`,
    so it reached 148 chars PAST the function into the next one, where an innocent `thShelf(` in
    a neighbour would have failed it. One under-reached, one over-reached, same root.

    ⚠ IT RETURNS "" ONLY WHEN IT CANNOT BOUND THE BLOCK — anchor absent, or braces never balance.
    Callers MUST fail on that rather than assert over it: `assertNotIn(anything, "")` passes, and
    a helper that quietly yields an empty region under a negative assertion rebuilds the exact
    silence this replaces. [[unknown-stays-unknown]] [[source-reading-guard]] §3

    ⚠⚠ STATED LIMIT, FOUND BY A CROSS-FAMILY REVIEW AND THEN MEASURED: this counts RAW braces and
    does NOT skip braces inside string literals, template literals, regex literals or comments. On
    a body containing an unmatched brace in such a token the span is truncated or over-long while
    still containing the anchor — so a later assertIn can pass or fail for the wrong reason.
    MEASURED across the functions this repo actually bounds: _shelfRefused (1,621), _dossierClose
    (113) and _shDismiss (131) agree with a string-aware walk; _reopenClear (665 vs 21,689) and
    vaultAccumApply (41,387 vs 83,951) do NOT. USE IT ONLY WHERE THE TWO AGREE, and leave the
    others on a byte window that does not pretend to be a boundary.
    """
    i = code.find(start)
    if i < 0:
        return ""
    # ⚠ v3352 — BALANCE FROM THE FIRST OPENING BRACE, NOT FROM CHARACTER ZERO. An anchor can
    # legitimately OPEN with a closing brace — `} else if (rHere > 0) {` is a real branch head in
    # this file — and balancing from there drives depth to -1 before any `{` is seen, so the walk
    # never returns to zero and the helper reports "cannot bound" for a block it can see perfectly
    # well. Start the count at the first `{` at or after the anchor; the RETURNED span still
    # begins at the anchor, so the caller reads the branch head it asked for.
    _open = code.find("{", i)
    if _open < 0:
        return ""
    depth, seen = 0, False
    for k in range(_open, len(code)):
        c = code[k]
        if c == "{":
            depth += 1
            seen = True
        elif c == "}":
            depth -= 1
            if seen and depth == 0:
                return code[i:k + 1]
    return ""


def _between(src, start, end):
    i = src.find(start)
    if i < 0:
        return ""
    j = src.find(end, i + len(start))
    return src[i:j] if j > i else ""


class TheShelfTabsAreTheRealSessions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(UI, encoding="utf-8") as fh:
            cls.src = fh.read()
        cls.code = _py_only(cls.src)
        cls.fn = _between(cls.code, "function _shStationChips(cards){",
                          "window._shStationChips")
        assert cls.fn, "_shStationChips is gone — this law is reading nothing"

    # ── the half that was missing for a whole version ────────────────────────────────────
    def test_the_buttons_actually_EXIST(self):
        """v3195's defect, pinned: a filter with no control is not a feature."""
        self.assertIn('id="sh-stationbar"', self.code,
                      "the station chip row has no container in the markup")
        self.assertIn("class=\"sh-chip sh-chip-st", self.fn,
                      "the builder emits no chip buttons")

    def test_the_builder_is_actually_CALLED(self):
        """[[the-unjoined-end]] — a builder nobody calls renders nothing, which is exactly the
        state this law exists to end."""
        self.assertIn("_shStationChips(vis)", self.code,
                      "nothing calls _shStationChips, so the row stays empty forever")

    def test_the_filter_half_is_still_wired(self):
        """both halves, or it is the same defect facing the other way."""
        self.assertIn("SHELF_F.station", self.code, "the station filter state is gone")
        self.assertIn("'st:'", self.code + repr(self.code),
                      "the st: toggle prefix is gone, so a chip click does nothing")
        self.assertIn("data-station", self.code, "the cards no longer carry their station")

    # ── what "not random or outdated" means, as assertions ───────────────────────────────
    def test_every_chip_is_earned_by_a_CARD(self):
        self.assertIn("getAttribute('data-station')", self.fn,
                      "the chips are no longer tallied from the cards, so the row can show a "
                      "station none of his reels is in — which is what he called random")
        self.assertIn("if (!st) return;", self.fn,
                      "an unstamped card is being counted into some station")

    def test_the_order_comes_from_the_RIVER_not_a_list_here(self):
        self.assertIn("SHELF_RIVER_ORDER", self.fn,
                      "the station order is no longer taken from /api/river — two lists of "
                      "stations is how they drift, and this file already carved that rule")
        # a literal station roster written into the builder is the exact thing being banned
        for banned in ("'INTAKE'", "'PRINTER'", "'CAPTURE'", "'TOMBSTONE'"):
            self.assertNotIn(banned, self.fn,
                             "a station name is hardcoded in the chip builder (%s) — that is a "
                             "second roster and it will drift from the router" % banned)

    def test_an_unmapped_station_is_MARKED_not_dropped(self):
        self.assertIn("sh-chip-stunk", self.fn,
                      "a station the river order does not name is silently dropped, so the row "
                      "lies by omission about a stage that has real reels in it")
        self.assertIn("indexOf(st) < 0", self.fn,
                      "nothing detects a station missing from the river order")

    def test_an_empty_row_HIDES_itself(self):
        """⚠ v3214 — TWO BRANCHES NOW, BECAUSE AN EMPTY BAR WAS HIDING TWO OPPOSITE FACTS.

        The original assertion was the literal text `if (!seen.length) { bar.hidden = true;`,
        which pinned the FORMATTING of one line rather than the behaviour. It was right that a
        bar with nothing stamped must not read as "no stations exist" — but `bar.hidden = true`
        fired in two situations that are not the same:

          · the river has not answered yet            -> hiding is correct, the header says so
          · the river HAS answered and no card is stamped -> that is a DEFECT, and hiding buried it

        The second is the unjoined end #227 named: the strip above prints station counts from
        /api/river while the grid beside it carries none. So this now pins BOTH branches, and
        does it on structure rather than on a byte sequence any reformat would break.
        [[zero-needs-a-denominator]] [[the-unjoined-end]] [[source-reading-guard]]
        """
        self.assertIn("if (!seen.length)", self.fn,
                      "nothing branches on an unstamped shelf at all, so a bar with no chips "
                      "renders empty and reads as 'no stations exist'")
        # ⚠⚠ THE BRANCH ITSELF, BY BRACE COUNTING — NOT A FIXED WINDOW OF CHARACTERS.
        # A `[:1400]` slice ran past the end of this branch into the chip builder below, where
        # `SHELF_RIVER_ORDER` and `SHELF_RIVER_LABELS` both CONTAIN the substring "SHELF_RIVER".
        # A sabotage that deleted the river consultation outright stayed GREEN, because the
        # assertion was being satisfied by two unrelated identifiers further down — which is the
        # exact failure the test three below this one already records ("a guard a rename satisfies
        # is measuring the alphabet"). Anchor BOTH ends or the reach is the finding.
        # [[source-reading-guard]] [[sabotage-is-usually-the-wrong-one]]
        _i = self.fn.index("if (!seen.length)")
        _o = self.fn.index("{", _i)
        _d, _j = 0, _o
        while _j < len(self.fn):
            if self.fn[_j] == "{":
                _d += 1
            elif self.fn[_j] == "}":
                _d -= 1
                if _d == 0:
                    break
            _j += 1
        tail = self.fn[_o:_j + 1]
        # ⚠ v3259 — CEILING RAISED FROM 1400 TO 2400, DELIBERATELY, BECAUSE THE BRANCH GREW.
        # This number is a REACH guard ("am I still inside the branch?"), never a budget, so it
        # moves when the branch legitimately moves and not otherwise. What grew it: the empty
        # branch now has to keep the station rail alive when a FILTER emptied the shelf — see the
        # law directly below. Raising it without saying why is how a reach guard stops guarding.
        self.assertLess(len(tail), 2400,
                        "the unstamped branch is %d chars — too large to be the branch, so this "
                        "is reading past it again" % len(tail))
        self.assertIn("bar.hidden = true", tail,
                      "an unstamped shelf no longer hides the bar, so an empty chip row is shown "
                      "as though the river had answered with nothing")
        self.assertIn("Object.keys(SHELF_RIVER", tail,
                      "the empty branch does not consult the river, so it cannot tell 'not "
                      "answered yet' from 'answered, and not one card is stamped' — and those "
                      "are opposite facts")
        self.assertIn("bar.hidden = false", tail,
                      "there is no branch that SHOWS the bar when the river answered and no card "
                      "carries a stamp, so the river-vs-grid mismatch stays invisible")

    def test_a_FILTER_that_empties_the_shelf_leaves_the_way_out(self):
        """★ GROK BOT FOUND THIS BY DRIVING THE SHELF AS A USER, and ranked it the worst trap of
        all — ahead of everything I had hypothesised:

            "CAPTURE (count 0) -> TRAP: chip rail VANISHED; body 'No runs match these filters...';
             0 RUNS. Could not reach ROUTE/ANALYZE after that. Re-click / clear did not restore
             the chip rail in this pass (stuck empty-filter state)."

        Click a station holding nothing -> the filter matches no card -> `seen.length` is 0 -> the
        bar hides itself, TAKING EVERY OTHER STATION CHIP WITH IT. There is then no way back to
        ROUTE or ANALYZE except leaving the shelf entirely. A dead end built out of two
        individually reasonable rules.

        ⚠ THE HIDE RULE ABOVE IS STILL RIGHT AND IS NOT BEING DELETED. "A bar with nothing in it
        reads as 'no stations exist'" is true WHEN NOTHING IS FILTERED. Once he has chosen a
        station, an empty result is a statement about his FILTER, not about the river - same
        condition, opposite meaning, and only the filter can tell them apart. That is why this law
        sits beside the hide law rather than replacing it. [[the-unjoined-end]]
        """
        _i = self.fn.index("if (!seen.length)")
        _o = self.fn.index("{", _i)
        _d, _j = 0, _o
        while _j < len(self.fn):
            if self.fn[_j] == "{":
                _d += 1
            elif self.fn[_j] == "}":
                _d -= 1
                if _d == 0:
                    break
            _j += 1
        tail = self.fn[_o:_j + 1]
        # ⚠⚠ ANCHORED TO THE GUARD, NOT TO THE IDENTIFIERS. The first cut of this law asserted
        # that "SHELF_F.station" and "SHELF_LAST_STATIONS" appear somewhere in the branch - and
        # BOTH sabotages came back GREEN, because `if (false)` leaves the body's mentions intact
        # and the writer lives outside the branch entirely. The names were present and the feature
        # was dead. That is the SECOND presence-law-where-a-reachability-law-was-needed in one
        # session; the remainder chip above carries the first.
        # [[the-unjoined-end]] [[sabotage-is-usually-the-wrong-one]]
        # ⚠ v3260 — THE GUARD IS THE FILTER ALONE. It used to also require the remembered rail,
        # which a cross-family review named as a hole: filter active + nothing remembered took the
        # hide path and stranded him anyway. The rail is now a bonus, never the precondition.
        g = tail.find("if (SHELF_F.station) {")
        self.assertGreater(
            g, -1,
            "the empty branch has no LIVE guard on the active filter, so a station holding "
            "nothing hides the rail and strands him with no way back to another station")
        body = tail[g:]
        self.assertIn("bar.hidden = false", body,
                      "the filter branch never SHOWS the bar, so the rail stays hidden anyway")
        self.assertIn("sh-chip-stclear", body,
                      "there is no explicit way OUT of an empty filter - the stations alone "
                      "narrow, and he needs one control that widens")
        # and the rail must actually be REMEMBERED somewhere, or there is nothing to restore
        self.assertIn("SHELF_LAST_STATIONS = bar.innerHTML", self.fn,
                      "nothing ever records the station rail, so the way out is the only thing "
                      "left in the bar and he loses the other stations")
        self.assertIn("(SHELF_LAST_STATIONS || '')", self.fn,
                      "the remembered rail is a PRECONDITION again - if it is null the branch "
                      "renders 'null' or throws, instead of still giving him the way out")

    def test_the_count_says_what_it_is_OVER(self):
        """[[zero-needs-a-denominator]] — a bare number on a chip is a figure with no scale."""
        self.assertIn("' of the ' + total + ' stamped reel(s)", self.fn,
                      "the chip tooltip gives a count with no denominator")

    def test_a_TRAJECTORY_is_never_claimed_from_an_OCCUPANCY_count(self):
        """★ HIS SHELF, READ BACK TO ME OFF ITS OWN TOOLTIP: *"no reel has reached triage yet"*,
        *"no join has reached yet also"* - and then the real report, *"it just looks stuck this
        way and as if the river IS not flowing"*.

        MEASURED the same minute on his live river:
            counts (WHERE THEY SIT)   TRIAGE 2 - JOIN 14 - CAPTURE 21 - ROUTED 21
            visits (WHO PASSED THROUGH) TRIAGE 21 - JOIN 14 - ROUTED 33
        21 reels have been through TRIAGE and the chip said NO REEL HAS REACHED IT. The count is
        an OCCUPANCY and the sentence was a TRAJECTORY, and `one_funnel.py` already carries this
        exact scar in its own gotcha - *"'no reel sits at banked' and 'no reel ever passed banked'
        are opposite"* - carved on a neighbouring module while this surface committed it verbatim.

        The law pins the JOINT, not the wording: an empty chip may not make an ever-claim unless
        it consulted something that actually knows. [[the-unjoined-end]] [[label-outlived-referent]]
        """
        self.assertNotIn("NO reel has reached", self.fn,
                         "the chip is claiming a reel has never REACHED a station from a count of "
                         "what sits there NOW - opposite facts, and his river has passed 21 reels "
                         "through the station it called untouched")
        self.assertIn("SHELF_RIVER_VISITS", self.fn,
                      "the builder never consults the river's visits, so it has nothing to answer "
                      "'has anything ever been here' with and can only guess from occupancy")
        self.assertIn("SHELF_RIVER_UNREACHED", self.fn,
                      "the builder never consults the river's own unreached list")

    def test_an_UNREPORTED_trajectory_stays_UNKNOWN(self):
        """⚠ THE DANGEROUS DIRECTION. A river that answers WITHOUT `visits` must not let the chip
        fall back to "never" - that is the same fabrication in the other direction, and it would
        be invisible because it reads exactly like a measured zero. [[unknown-stays-unknown]]"""
        self.assertIn("UNKNOWN", self.fn,
                      "no branch says UNKNOWN, so a river that reported no visits is presented as "
                      "a river that reported zero")
        self.assertIn("=== 'number'", self.fn,
                      "the visits read is not type-checked, so a missing key becomes undefined and "
                      "compares as a number would not")

    def test_the_REMAINDER_is_counted_even_when_stations_are_stamped(self):
        """★ HIS SCREENSHOT: the chips summed to 12 and the header said "13 of 13". One card sat
        in no chip at all - not even UNKNOWN - and nothing accounted for it.

        The accounting existed, and ONLY inside the `!seen.length` branch: it ran only when NOTHING
        was stamped. The moment one station held a reel - the case where a missing card is hardest
        to spot - it stopped counting. A denominator that appears only when the numerator is zero
        is not a denominator. [[zero-needs-a-denominator]]
        """
        i = self.fn.find("var total = 0;")
        j = self.fn.find("bar.hidden = false;", i)
        self.assertGreater(i, -1, "the total is gone; re-anchor this law")
        self.assertGreater(j, i, "the show-the-bar line is gone; re-anchor this law")
        main = self.fn[i:j]
        self.assertIn("data-station-why", main,
                      "the stamped path does not account for cards carrying no station, so a card "
                      "in no chip vanishes from a row whose numbers are supposed to close")
        # ⚠ THE PRINT MUST BE REACHABLE, not merely present. A first cut of this law asserted
        # only that the class appears somewhere in the branch, which an `if (false)` around the
        # print would have satisfied perfectly - the remainder computed, then thrown away, which
        # is the historical behaviour this law exists to refuse. So it is anchored to the GUARD.
        g = main.find("if (_rmWithheld || _rmNoStamp)")
        self.assertGreater(g, -1,
                           "the remainder has no live guard, so it is computed and never shown - "
                           "which is the state his screenshot was in")
        _blk = _fn_body(main, "if (_rmWithheld || _rmNoStamp)")
        self.assertTrue(_blk, "could not bound the remainder guard")
        self.assertIn("sh-chip-strem", _blk,
                      "nothing PRINTS the remainder inside its own guard, so it is counted and "
                      "then thrown away")

    def test_the_denominator_cannot_be_NaN(self):
        """★ IT WAS. Found by RENDERING the shipped chip and reading its tooltip off his live
        console: *"7 of the NaN stamped reel(s)"*.

        `ordered` carries every station the river names; `tally` only the ones some card is at. So
        the first ordered station with no cards made the sum `0 + undefined`, and every chip after
        it printed NaN as its denominator. The sibling law above asserts the PHRASE
        "of the N stamped reel(s)" is present - and NaN satisfies that phrase perfectly, which is
        why it went unseen. A number printed as NaN is a missing denominator wearing a figure.
        [[zero-needs-a-denominator]] [[regression-guard]]
        """
        self.assertIn("total += (tally[st] || 0)", self.fn,
                      "the chip total sums tally entries without guarding the stations that have "
                      "no cards, so the denominator is NaN again")

    def test_an_empty_SHELF_chip_does_not_claim_an_empty_RIVER(self):
        """⚠ THE CONTRADICTION THE FIRST CUT SHIPPED, caught on real pixels before it went out:
        JOIN carried the DAM mark and its own sentence said *"the river flows here, it is simply
        not holding anything"* - while the river held 14 reels at JOIN with none ever leaving.

        The shelf window is 13 cards; the river is 63 reels. A chip that is empty in the WINDOW
        must consult the RIVER's occupancy before saying anything about the river.
        """
        self.assertIn("SHELF_RIVER_COUNTS", self.fn,
                      "the builder never reads the river's own occupancy, so it can only describe "
                      "the 13-card window while appearing to describe the river")
        # ⚠⚠ AND SOMETHING MUST WRITE IT. A sabotage that renamed the ASSIGNMENT left this law
        # green, because the law only ever asked whether the BUILDER reads the variable - and it
        # still did, from a name nothing sets. The read would then be null for ever and every
        # river sentence would quietly degrade to the window-only branch, which is the exact
        # defect this file exists to catch, one level up. Both ends, or neither.
        # [[the-unjoined-end]] [[sabotage-is-usually-the-wrong-one]]
        self.assertIn("SHELF_RIVER_COUNTS = (d.counts", self.code,
                      "nothing ASSIGNS SHELF_RIVER_COUNTS from the river payload, so the builder "
                      "reads a name that is null for ever and silently falls back to the "
                      "shelf-window sentence")
        i = self.fn.find("} else if (rHere > 0) {")
        self.assertGreater(i, -1,
                           "there is no branch for 'empty on this shelf, occupied in the river' - "
                           "so that state falls through to a sentence about flow")
        _blk = _fn_body(self.fn, "} else if (rHere > 0) {")
        self.assertTrue(_blk, "could not bound the empty-on-this-shelf branch")
        self.assertIn("THIS SHELF", _blk,
                      "that branch does not name WHICH population is empty")

    def test_a_LEDGER_figure_is_never_spoken_as_an_ON_DISK_one(self):
        """★ v3257 SHIPPED THIS WRONG AND v3258 CORRECTED IT. One /api/river payload carries THREE
        populations, and the chip picked the widest one and described it as the narrowest:

            lanes.byStation  12   what THIS SHELF shows
            census.counts    63   the STAMP LEDGER (lifetime 465, closed out 453)
            reel_router      20   what is actually ON DISK (8 fixtures + 12 shown)

        The chip read census.counts and said "the river has 14 sitting there" about JOIN, where the
        real on-disk figure is 2. Twelve of those fourteen were stamped JOIN and then DELETED - the
        last stamp never moved because the reel stopped existing.

        river_stamp.census is exact about this in its own docstring: counts is "how many reels are
        THERE NOW (their most recent stamp)", a fact about the LEDGER, and the same file says "how
        many reels exist is the shelf's question". The number is fine; calling it an occupancy was
        not. [[label-outlived-referent]] [[zero-needs-a-denominator]]
        """
        self.assertNotIn("sitting there", self.fn,
                         "a ledger figure is being spoken as reels sitting on disk again - 14 at "
                         "JOIN in the ledger, 2 actually there")
        self.assertNotIn("sit here", self.fn,
                         "a ledger figure is being spoken as an on-disk occupancy again")
        i = self.fn.find("rHere")
        self.assertGreater(i, -1, "the ledger figure is gone; re-anchor this law")
        self.assertIn("MOST RECENT STAMP", self.fn,
                      "the sentence built from the ledger figure never says what that figure IS, "
                      "so it reads as an on-disk count of reels standing at the station")

    def test_a_filter_that_would_greet_him_EMPTY_is_cleared_on_OPEN(self):
        """★ GROK BOT RANKED THIS #2 OF FOUR TRAPS, and it reproduced exactly on his console:

            opened               visible 8
            filtered to FRESH 0  visible 0   (deliberate)
            closed               hidden
            RE-OPENED            visible 0   <- the filter SURVIVED the close

        `SHELF_F` is a module var, so a station filtered before closing is still applied on the
        next open. Thirteen cards in the DOM, every one filtered out. It reads as a broken shelf;
        it is a remembered click.

        ⚠ A FILTER HE JUST CLICKED IS NOT TOUCHED, and that boundary is the law. Clicking a station
        holding nothing and seeing nothing is CORRECT — that is him asking. The clear happens only
        on OPEN, and only when the remembered filter would show an empty shelf, so a filter that
        still matches survives untouched. A fix that cleared unconditionally would take his own
        deliberate filter away from him. [[the-unjoined-end]]
        """
        src = _py_only(self.src)
        i = src.find("var _reopenClear = function()")
        self.assertGreater(
            i, -1,
            "nothing clears a station filter that survived a close, so re-opening the shelf can "
            "greet him with an empty panel and thirteen cards he cannot see")
        # ⚠⚠ v3352 — LEFT AS A BYTE WINDOW, AND THE REASON IS A DISAGREEMENT I CANNOT SETTLE.
        # A cross-family review pointed out that _fn_body counts RAW braces and never skips those
        # inside strings, regexes or template literals. MEASURED on this function: the plain walk
        # ends at 665 chars, a string-aware walk ends at 21,689. Two methods disagreeing by 33x
        # means the true extent is UNKNOWN, and a bound I cannot defend is worse than an honest
        # guess — the guess at least does not claim to be the function. The 1,200 window stands
        # until the walker is string-aware. [[unknown-stays-unknown]]
        body = src[i:i + 1200]
        self.assertIn("if (_any) return;", body,
                      "the clear does not check whether the remembered filter still MATCHES, so "
                      "it would throw away a filter he deliberately left on and that still shows "
                      "him something")
        # ⚠⚠ AND "MATCHED" MEANS THE FILTER, NOT THE SCREEN. v3263's first cut also treated a card
        # hidden by the FIFO cap (`data-river-out`) as "did not match" — and a cross-family review
        # reproduced it on his live shelf: PRINTER (he reads it as SEAL) holds exactly ONE reel and
        # the cap hides it, so filtering to SEAL matched a real reel, showed nothing because of the
        # CAP, and the filter he had just set would have been cleared out from under him.
        #     style.display = 'none'  -> the FILTER rejected it  -> not a match
        #     data-river-out          -> the FIFO cap hid it     -> IT MATCHED
        # Taking his filter away is the one thing this must never do.
        _loop = body[body.find("for (var _q"):body.find("if (_any) return;")]
        self.assertNotIn("data-river-out", _loop,
                         "the match test counts a FIFO-capped card as 'did not match', so a filter "
                         "whose reels are all past the river gets cleared even though it matched")
        self.assertIn("SHELF_F.station = null", body,
                      "the clear never actually clears the station")
        # and it must be REACHED from the open path, not merely defined
        # ⚠⚠ BOTH CALL SITES, NOT ONE. A sabotage that removed the `_had` path alone came back
        # GREEN, because the fetch path still carried the string — and the `_had` path IS the
        # re-open path, the one that runs when sessions are already loaded, which is exactly the
        # case Grok Bot hit. A law satisfied by the site that was not broken is no law.
        n_called = src.count("_reopenClear()")
        self.assertGreaterEqual(
            n_called, 3,
            "_reopenClear is reached from %d place(s); it must be called on the cached-open path "
            "AND on both fetch outcomes, or re-opening with sessions already loaded still greets "
            "him with an empty shelf" % (n_called - 1))
        self.assertIn("if (_had) { _paintShelf(); _reopenClear(); }", src,
                      "the CACHED open path does not clear — that is the re-open path, the one "
                      "the trap was reported on")

    def test_EVERY_dismiss_leaves_the_way_he_came_in(self):
        """★ THE REAL CODE DEBT, filed as #229: *"outside-click on SHELF does not honor
        shelfIsDoor, so it can leave a bare stage."*

        v2451 taught the ✕ to leave the way he came in — if THE SHELF was the door, closing it
        closes everything; if he opened the shelf from inside the theatre, it returns him to the
        reel. That fix was applied at ONE site and its sibling THIRTEEN LINES BELOW — the
        click-outside-a-card dismiss — kept doing a bare `ov.hidden = true`. Dismissing by clicking
        beside a card left him on the same black rectangle v2451 exists to prevent.

        ⚠ THE LAW IS THAT THERE IS ONE DISMISS, not that two sites each remember. Two call sites
        with the same rule is exactly how the first one got fixed alone. [[sweep-dont-ask]]

        Verified on pixels: shelf opened as the door -> theatre flex 1044x978; outside-click
        dismiss -> theatre display:none, box [0,0]. No bare stage.
        """
        src = _py_only(self.src)
        i = src.find("var _shDismiss = function()")
        self.assertGreater(
            i, -1,
            "there is no single dismiss for the shelf, so the ✕ and the click-outside paths each "
            "carry their own rule and one of them will be fixed alone again")
        body = _fn_body(src, "var _shDismiss = function()")
        self.assertTrue(body, "could not bound _shDismiss")
        self.assertIn("_thShelfWasTheDoor()", body,
                      "the shared dismiss does not ask whether THE SHELF was the door, so it can "
                      "leave him on a bare stage with no reel under it")
        self.assertIn("thClose()", body,
                      "the shared dismiss never closes the stage it opened")
        # ⚠ BOTH paths must GO THROUGH it — a helper nothing calls is the defect wearing a fix
        self.assertNotIn("if (!c){ ov.hidden = true; return; }", src,
                         "the click-outside dismiss still hides the overlay directly instead of "
                         "going through the shared dismiss — the bare-stage path is back")
        self.assertGreaterEqual(
            src.count("_shDismiss()"), 2,
            "the shared dismiss is reached from fewer than both paths, so one of ✕ / "
            "click-outside still carries its own rule")

    def test_the_dossier_BACK_button_never_names_a_place_it_is_not_going(self):
        """★ v3273 — THE SENTENCE HE REPORTED, FOUND IN THE LABEL RATHER THAN THE BEHAVIOUR.

        Konyo: *"when i click on things within the tabs inside shelf i exit out it brings me to
        the console instead of moving me back one to where i was within the shelf"*.

        `_dossierClose` is a bare `ov.hidden = true` — and that is CORRECT: it reveals whatever is
        underneath, which IS one step back. The defect is that the button hard-coded
        **"‹ back to the shelf"** while the dossier has FOUR openers and only two are the shelf:

            a shelf card / highlight card  -> the shelf IS underneath   the label is true
            the off-air HOME strip         -> NO shelf underneath       lands on the console
            a `session` deeplink           -> NO shelf underneath       lands on the console

        So from the home strip he taps a run, reads it, presses a button that says THE SHELF, and
        arrives at the console. Nothing moved him wrongly; the word did.
        [[label-outlived-referent]]

        ⚠ Fixed as a LABEL, never as a jump. Forcing the shelf open would invent a destination he
        never came from — the opposite of v3264's rule that a dismiss leaves the way he came in.
        """
        src = _py_only(self.src)
        i = src.find("class=\"dsr-back\"")
        self.assertGreater(i, -1, "the dossier back button is gone or renamed")
        # the label must be DECIDED, not typed: the shelf's own state has to be consulted
        blk = src[max(0, i - 700):i + 400]
        self.assertIn("th-shelfov", blk,
                      "the back button never asks whether the shelf is actually underneath, so it "
                      "names the shelf from the home strip and the deeplink too")
        self.assertIn("'back to the shelf'", blk,
                      "the true branch is gone — it no longer says the shelf even when the shelf "
                      "IS underneath")
        self.assertIn("'back'", blk,
                      "there is no honest fallback, so a dossier opened off the shelf still "
                      "promises the shelf")

    def _theatre_keys(self):
        """The THEATRE's keydown handler, both ends anchored on code that predates this fix.

        ⚠ `find("document.addEventListener('keydown'")` matches an UNRELATED handler ~9000 lines
        earlier and the first cut of these laws read that one — it went red immediately, which is
        the test doing its job. The lightbox arrow branch is unique to this handler, so the slice
        runs from the handler that OWNS it back to its own registration.
        [[source-reading-guard]]
        """
        src = _py_only(self.src)
        end = src.find("if (e.key === 'ArrowRight'){ thHdStep(1)")
        self.assertGreater(end, -1, "the theatre keydown handler is gone or renamed")
        start = src.rfind("document.addEventListener('keydown'", 0, end)
        self.assertGreater(start, -1, "the theatre keydown registration is gone")
        return src[start:end]

    def test_ESCAPE_still_works_when_the_STAGE_never_opened(self):
        """★ v3274 — THE STATE HE COULD NOT CLICK HIS WAY OUT OF, filed as "no ✕, Escape no-op".

        ⚠⚠ v3275 CORRECTION — v3274 blamed a failing `thOpen()` for the dead Escape and that was
        WRONG. Every statement before `TH.open = true;` sits inside one try/catch, so a rejecting
        `thOpen()` leaves TH.open TRUE; and `thClose()` already hides `#th-shelfov` itself. Both
        candidate paths are closed.

        THE REACHABLE TRIGGER IS THE OFF-AIR HOME STRIP, `control_ui.html:21440`:

            el.onclick = function(e){ var c = e.target.closest('.hh-card');
                                      if (c) _sessionDossier(Number(c.dataset.hn) || 1); };

        No `thOpen()`. So TH.open is FALSE, `#th-dossier-ov` IS up, and `if (!TH.open) return;`
        swallowed Escape — a dead end reached from the same opener REG-1083 fixed the label for.
        One entry point, two traps: a button naming a place it was not going, and no Escape at all.

        The other half of v3274 stands on its own: `_shelfRefused` replaces the overlay's
        innerHTML, and the ✕ it overwrites belongs to `_paintShelf`, so the refusal state had no
        close control — and its advice was "press ON AIR", the RECORDING control.
        [[the-unjoined-end]] [[a-wrong-answer-skips-the-fallback]]
        """
        blk = self._theatre_keys()
        self.assertIn("if (!TH.open) {", blk,
                      "the handler no longer has a closed-stage branch at all")
        self.assertIn("thEscUnwind()", blk,
                      "Escape never reaches the unwind when the stage did not open, so the "
                      "refusal panel is a dead end")
        self.assertIn("th-shelfov", blk,
                      "the closed-stage branch does not check that an overlay is actually up")

    def _pop_clause(self):
        src = _py_only(self.src)
        # REG-2084 - the clause moved out of an inline IIFE into _shelfPopClause(P, shown, pushed) so a law can drive it;
        # the same body, bounded by the function and its export line
        i = src.find("  function _shelfPopClause(P, shown, pushed){")
        self.assertGreater(i, -1, "the header's population clause is gone or renamed")
        j = src.find("  window._shelfPopClause = _shelfPopClause;", i)
        self.assertGreater(j, i, "the population clause never closes")
        return src[i:j]

    def test_the_header_ANSWERS_why_the_disk_holds_more_than_he_sees(self):
        """★ v3279 — "Shelf shows 13, disk holds 20", answered where he asks it.

        v3278 measured the population and joined it to the DOCTOR. Measured on his tree:
        20 on disk = 8 he sees + 8 hidden fixtures the suite opens by name + 3 the vault still
        owes a bank + 1 the prune may release. Run in node against five payload shapes, the
        header now reads:

            " · 20 on disk in all (8 hidden fixtures · 3 still owed · 1 releasable)"
        """
        blk = self._pop_clause()
        self.assertIn("on disk in all", blk, "the header no longer states the disk total")
        self.assertIn("hidden fixture", blk, "the hidden fixtures are not accounted for on screen")
        # ⚠⚠ v3344 — THIS PINNED "waiting on a lane" AND THE DOCSTRING ABOVE CONTRADICTED IT.
        # Three lines up this law says the 3 are ones "the vault still owes a BANK", and it then
        # asserted the screen calls them "waiting on a lane" — the OWED_BY question (which lane owns
        # this) standing in for the READ_CLEARS question (can a read clear it). `rows-not-banked` is
        # the proof they are different: v2878 kept it OUT of READ_CLEARS because it is owed a BANK,
        # so no lane pass will ever clear it, and the sentence filed it with the other four anyway.
        # The screen now names the TAG, so the docstring above is true rather than contradicted.
        self.assertIn("still owed", blk, "reels that are still owed are not named")
        self.assertNotIn(
            "waiting on a lane", blk,
            "the shelf is back to calling every owed reel 'waiting on a lane'. That is true only "
            "where a READ clears it; a rows-not-banked reel waits for a BANK and no sweep will "
            "ever come. Name the tag, not the owner.")

    def test_a_reconciliation_that_does_NOT_SUM_prints_NOTHING(self):
        """⚠⚠ THE LAW THIS TURNS ON. A total whose parts do not add up is worse on a screen than
        no total at all — it looks authoritative and is wrong. The clause is dropped entirely
        unless the census says it sums, and `sums !== true` is deliberate: a MISSING field must
        also print nothing, not be read as truthy."""
        blk = self._pop_clause()
        self.assertIn("P.sums !== true", blk,
                      "the header will print a reconciliation the census says does not add up")
        self.assertIn("typeof P.onDisk !== 'number'", blk,
                      "a missing onDisk would render as undefined on his screen")

    def test_every_COUNT_is_proven_a_number_before_it_is_printed(self):
        """★ v3280 — raised by the cross-family eye on v3279, and real.

        The guard checked `sums` and `onDisk`, then trusted `fixtures`, `owed`, `releasable` and
        the values inside `other` blindly. A payload carrying `owed:null` and `releasable:"x"`
        would render *"0 waiting on a lane · NaN releasable"* — garbage that still reads as a
        measurement, on the one line whose whole job is to make numbers trustworthy.

        `_n` returns a positive integer or 0, and 0 prints nothing, so a malformed count becomes
        SILENCE rather than a number he might act on. Verified in node: a payload with
        `fixtures:"8", owed:null, releasable:NaN, other:{bad:"x"}` renders "".
        [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
        """
        blk = self._pop_clause()
        self.assertIn("var _n = function(v)", blk,
                      "the counts are printed without being proven numeric")
        self.assertIn("typeof v === 'number'", blk, "_n does not check the type at all")
        self.assertIn("isFinite(v)", blk, "_n admits NaN and Infinity")
        self.assertIn("_n(P.other[oth[i]])", blk,
                      "the counts inside `other` are still printed unvalidated, so a malformed "
                      "one reaches his screen through the newest branch")

    def test_the_tag_NAME_is_escaped_into_the_header(self):
        """⚠ `mkHead` inserts its label as HTML, and the sibling clause already does
        `esc(String(SHELF_MOUTH.why))`. These tag names come from reel_retention's own rules, so
        nothing hostile reaches here today — but an unescaped backend string in an HTML label is a
        habit, not a risk assessment, and the inconsistency is what rots."""
        blk = self._pop_clause()
        self.assertIn("esc(String(oth[i]))", blk,
                      "a retention tag name is interpolated into an HTML label unescaped")

    def test_an_unrecognised_tag_reaches_the_SCREEN_too(self):
        """⚠ the census names a tag it has never met rather than dropping it; that naming is
        worthless if the surface then drops it. Both ends, or neither. [[the-unjoined-end]]"""
        blk = self._pop_clause()
        self.assertIn("P.other", blk,
                      "the header ignores tags the census could not place, so a new retention "
                      "rule would silently go missing from the only sentence that adds up")

    def _shelf_door_rule(self):
        src = _py_only(self.src)
        i = src.find("#btn-shelf { margin-top: auto")
        self.assertGreater(i, -1, "the shelf door's rule is gone or renamed")
        j = src.find("}", i)
        self.assertGreater(j, i, "the shelf door's rule never closes")
        return src[i:j + 1]

    def test_the_SHELF_DOOR_is_anchored_to_the_VISIBLE_floor(self):
        """★ v3277 — THE DOOR WAS ANCHORED TO A FLOOR THAT IS OFF-SCREEN AT HIS RESOLUTION.

        Filed by the Mac third eye four briefs running as *"1280x800 rail-clip unpaid: door still
        after Console-rail scroll to floor"*, and every native LOOKED reaches THE SHELF "via
        Console-rail scroll" rather than by seeing it.

        MEASURED at 1280x800 against the live console:

            .rail        height 629   content 741   overflow-y auto   canScroll 112   scrollTop 0
            #btn-shelf   top 779   bottom 849   viewport 800   ->  FULLY OFF-SCREEN
            any "more below" affordance: NONE

        `margin-top: auto` puts it last in the flex column — the CONTENT floor. When the rail
        overflows, that floor is past the fold and the primary door silently leaves the screen.

        ⚠ HIS INTENT IS KEPT, NOT OVERRULED. He anchored it to the floor on purpose; sticky still
        puts it last and at the bottom — it just makes "the bottom" mean the VISIBLE bottom.
        Nothing is reordered and v1354's engines-first layout is untouched.
        After: in view at 1280x800 (top 667), 1440x900 and 1280x1100.
        """
        rule = self._shelf_door_rule()
        self.assertIn("position: sticky", rule,
                      "the door is pinned to the content floor again, which is off-screen at "
                      "1280x800 — his own resolution")
        self.assertIn("bottom: 0", rule, "the sticky door has no edge to stick to")
        self.assertIn("margin-top: auto", rule,
                      "the door is no longer last in the rail — his floor anchoring was dropped")

    def test_the_sticky_door_is_OPAQUE(self):
        """⚠⚠ THE GUARD THE GEOMETRY COULD NOT GIVE. The first cut kept `.act`'s
        `rgba(0,0,0,.28)` and measured perfectly — in view at all three viewports. LOOKING at it
        showed the defect: with the rail scrolled 60px, "last read — duration not recorded" reads
        STRAIGHT THROUGH the button, across the words THE SHELF. A door you cannot read is not a
        door.

        A sticky element has content scrolling behind it, so a translucent background is not a
        style choice — it is a legibility bug waiting for the first scroll.
        [[visual-regression-detector]]
        """
        rule = self._shelf_door_rule()
        self.assertIn("background:", rule,
                      "the sticky door has no background of its own, so the rail's content shows "
                      "through it the moment anything scrolls behind")
        import re
        bg = re.search(r"background:\s*([^;}]+)", rule)
        self.assertIsNotNone(bg, "the door's background could not be read")
        val = bg.group(1).strip()
        self.assertNotIn("rgba", val,
                         "the sticky door's background is translucent (%r) — scrolling content "
                         "reads through it" % val)
        self.assertNotIn("transparent", val, "the sticky door is transparent")

    def test_the_HOME_STRIP_really_does_open_the_dossier_with_NO_theatre(self):
        """★ v3275 — THE MEASURED TRIGGER, pinned so the bug cannot be hidden by accident.

        The closed-stage Escape branch only matters because something opens an overlay without a
        theatre. `control_ui.html:21440` is that something: the off-air HOME strip calls
        `_sessionDossier` directly, with no `thOpen()`.

        ⚠ If a later change makes this path open the theatre first, TH.open becomes true, the
        branch stops being exercised, and it rots as dead code that still looks maintained. Then
        this law goes red and says why — which is the only way that stays visible.
        [[matches-once-can-still-prove-nothing]]
        """
        src = _py_only(self.src)
        i = src.find("var c = e.target.closest('.hh-card')")
        self.assertGreater(i, -1, "the off-air home strip's card handler is gone or renamed")
        handler = src[max(0, i - 120):i + 200]
        self.assertIn("_sessionDossier(", handler,
                      "the home strip no longer opens the dossier")
        self.assertNotIn("thOpen(", handler,
                         "the home strip now opens the theatre first — TH.open is true, so the "
                         "closed-stage Escape branch is no longer exercised by this path and is "
                         "at risk of rotting untested")

    def test_the_closed_stage_branch_lets_ONLY_escape_through(self):
        """⚠ THE GUARD ON THAT FIX. Every other key in this handler belongs to an OPEN theatre —
        arrows walk frames, space plays. Opening the whole handler to a closed stage would hand a
        shut theatre the transport keys, which is a bigger bug than the one being fixed."""
        blk = self._theatre_keys()
        j = blk.find("if (!TH.open) {")
        self.assertGreater(j, -1, "the closed-stage branch is gone")
        branch = _fn_body(blk, "if (!TH.open) {")
        self.assertTrue(branch, "could not bound the closed-stage branch")
        self.assertIn("e.key !== 'Escape'", branch,
                      "the closed-stage branch does not restrict itself to Escape, so a shut "
                      "theatre now answers the transport keys")

    def test_escape_proves_the_RECT_not_the_hidden_FLAG(self):
        """★ v3275 — `!hidden` IS NOT "HE CAN SEE IT", and this file says so twice already.

        MEASURED by counting div nesting from `id="theatre"` in control_ui.html:

            #th-shelfov      12 <div vs 11 </div>   -> net +1, it IS A CHILD of #theatre
            #th-dossier-ov  167 <div vs 168 </div>  -> net -1, it is a SIBLING

        `#theatre` is `display:none` while shut, so an un-hidden SHELF inside it is a zero-height
        box he cannot see — the exact trap `_shelfRefused`'s own comment records ("the overlay
        reported height 0 with the full refusal text inside it"), and the reason the door path
        proves itself from `getBoundingClientRect()`. Firing Escape on an invisible overlay would
        tear down state he never opened.

        The DOSSIER being a sibling is what makes the off-air home strip's dossier genuinely
        visible with no theatre — which is why that trap was real. One rule covers both: a rect,
        never a flag. Raised by the cross-family eye on v3274 and reproduced.
        """
        blk = self._theatre_keys()
        self.assertIn("getBoundingClientRect", blk,
                      "the closed-stage Escape branch still trusts .hidden, so it can fire on a "
                      "shelf sitting invisible inside a display:none theatre")
        self.assertNotIn("!_sv.hidden) || (_dv && !_dv.hidden)", blk,
                         "the flag-only test is still the one deciding")

    def test_the_refusal_panel_BINDS_its_own_close_when_none_exists(self):
        """⚠ THE ✕ MUST NOT DEPEND ON A PAINTER THAT MAY NEVER HAVE RUN. The shared dismiss is
        `ov.onclick`, assigned inside `_paintShelf` — delegation, so it survives an innerHTML
        replacement once it exists. But `_shelfRefused` stands in for `_paintShelf` exactly when
        the shelf failed to open, so on a FIRST-EVER open that fails before the painter runs,
        nothing is bound and v3274's ✕ would be inert: a close button that is furniture.

        ⚠ Bound only when ABSENT, so the shared dismiss stays the one rule wherever it exists —
        a second unconditional binding would be the duplicate v3264 collapsed into one.
        """
        src = _py_only(self.src)
        i = src.find("function _shelfRefused(")
        self.assertGreater(i, -1, "the refusal handler is gone or renamed")
        body = _fn_body(src, "function _shelfRefused(")
        self.assertTrue(body, "could not bound _shelfRefused")
        self.assertIn("!ov.onclick", body,
                      "the refusal panel does not bind its own close, so a shelf that fails "
                      "before it was ever painted shows an inert ✕")
        self.assertIn("th-shelf-x", body, "the bound handler does not look for the ✕")
        self.assertIn("_thShelfWasTheDoor()", body,
                      "the refusal close does not leave the way he came in")

    def test_the_REFUSAL_panel_keeps_a_way_out(self):
        """⚠ The refusal panel replaces innerHTML, which is where the ✕ lived. It must re-emit one
        with the SAME id, so the existing shared dismiss picks it up and still leaves the way he
        came in — a second close path would be exactly what v3264 collapsed into one."""
        src = _py_only(self.src)
        i = src.find("function _shelfRefused(")
        self.assertGreater(i, -1, "the refusal handler is gone or renamed")
        body = _fn_body(src, "function _shelfRefused(")
        self.assertTrue(body, "could not bound _shelfRefused")
        self.assertIn("it did not open", body, "this is not the refusal panel")
        self.assertIn("th-shelf-x", body,
                      "the refusal panel has no ✕, so a failed shelf cannot be closed by clicking")

    def test_the_refusal_panel_does_NOT_send_him_to_a_RECORDING_control(self):
        """⚠ It used to say "Press ON AIR to close the stage and try again". ON AIR starts filming.
        Telling him to record his way out of an error panel is not an exit, and GrokBot's own
        standing rules for driving this console are "no ON AIR"."""
        src = _py_only(self.src)
        # ⚠⚠ v3350 — TWO DEFECTS HERE, AND THE UNGUARDED FIND WAS THE WORSE ONE. `i = src.find(...)`
        # had NO check, so a rename makes i == -1, `src[-1:1599]` is a ONE-CHARACTER window, and
        # this assertNotIn passes having read a single byte. On top of that the window was 1,600
        # against a function MEASURED at 4,057 chars, so even when the anchor hit, 61% of the
        # subject went unread. Both are now bounded by the function itself.
        body = _fn_body(src, "function _shelfRefused(")
        self.assertTrue(body, "could not bound _shelfRefused — it is renamed, gone, or its braces "
                              "do not balance. Refusing to report that a phrase is absent from a "
                              "region this law could not locate.")
        self.assertNotIn("Press <b>ON AIR</b>", body,
                         "the refusal panel still names the recording control as the way out")

    def test_the_dossier_close_still_only_STEPS_BACK_and_never_jumps(self):
        """⚠ the guard on the fix: `_dossierClose` must stay a plain reveal. The moment it starts
        opening the shelf to honour its own label, a dossier opened from the home strip would
        land him somewhere he never was — which is the trap wearing the other face."""
        src = _py_only(self.src)
        i = src.find("window._dossierClose = function()")
        self.assertGreater(i, -1, "the dossier close is gone or renamed")
        # ⚠ v3350 — the function is MEASURED at 112 chars and this read 260, reaching 148 chars
        # into the NEXT function; a neighbour that legitimately calls thShelf( would have failed
        # the three assertNotIn below on code this law says nothing about.
        body = _fn_body(src, "window._dossierClose = function()")
        self.assertTrue(body, "could not bound _dossierClose, so the forbidden-jump check below "
                              "would be measuring a region this law could not locate")
        self.assertIn("hidden = true", body, "the close no longer hides the dossier")
        for forbidden in ("thShelf(", "thOpen(", "shellOpen("):
            self.assertNotIn(forbidden, body,
                             "the close now JUMPS (%s) instead of stepping back one" % forbidden)

    # ── a class nobody styles is a flag nobody can see ───────────────────────────────────
    def test_every_class_the_BUILDER_EMITS_is_actually_styled(self):
        """The join, asked in the only direction that cannot be faked.

        ⚠⚠ TWO EARLIER CUTS OF THIS TEST WERE SATISFIED BY THINGS THAT WERE NOT THE POINT, and
        the red-proof caught both:
          1. `assertIn(".sh-chip.sh-chip-stunk", src)` — a sabotage renaming the rule to
             `...-stunkX` STAYED GREEN, because the renamed selector still CONTAINS the old one.
             A guard a rename satisfies is measuring the alphabet.
          2. Adding a `(?![\\w-])` boundary fixed that and it STILL stayed green, because the
             class has TWO rules (`.sh-chip-stunk` and `.sh-chip-stunk::after`) and renaming one
             leaves the other.
        Both failures share a cause: the test asserted a STRING EXISTS rather than that the two
        halves AGREE. So it now reads the class names out of the builder itself and requires each
        to be styled. Rename it in either half and they stop matching, which is the actual defect.
        [[the-unjoined-end]] [[sabotage-is-usually-the-wrong-one]] [[source-reading-guard]]
        """
        emitted = set()
        for m in re.finditer(r"class=\\?\"([^\"]*sh-chip[^\"]*)", self.fn):
            for tok in re.split(r"[\s'+]+", m.group(1)):
                tok = tok.strip()
                if tok.startswith("sh-chip-"):
                    emitted.add(tok)
        print("   classes the builder emits: %s" % sorted(emitted))
        self.assertTrue(emitted,
                        "no sh-chip-* class could be read out of the builder, so this test is "
                        "checking nothing [[zero-needs-a-denominator]]")
        unstyled = [c for c in sorted(emitted)
                    if not re.search(r"\." + re.escape(c) + r"(?![\w-])", self.src)]
        self.assertEqual([], unstyled,
                         "the builder emits %r and the stylesheet never styles it — a class "
                         "nobody styles is a flag nobody can see, the same "
                         "[[plumbing-with-no-tap]] shape as the buttons that were missing"
                         % unstyled)


RED_PROOF = [
    ("control_ui.html", "_shStationChips(vis)", "_shStationChipsX(vis)",
     "test_the_builder_is_actually_CALLED"),
    ("control_ui.html", 'id="sh-stationbar"', 'id="sh-stationbarX"',
     "test_the_buttons_actually_EXIST"),
    # tamper the BUILDER, which is the half that decides what must be styled
    ("control_ui.html", "class=\"sh-chip sh-chip-st'", "class=\"sh-chip sh-chip-stZ'",
     "test_every_class_the_BUILDER_EMITS_is_actually_styled"),
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
