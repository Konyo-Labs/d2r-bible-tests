#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DID THE WINDOW ACTUALLY PAINT? — a second witness for the rescue, taken from PIXELS.

His words, 2026-09-04, after the console went black on him: *"maybe we can have like a safegaurd
for this connected to the watchdog/heart of the console that sees it rendering or something
regressing it automatically just restarts the console before i even notice it :)"*, and then:
*"and a picture harness pixel harness of some sort like a visual screenshot or something im sure
we can safegaurd it by that too if you cant archicture a bypass :)"*.

⚠⚠ THE EXISTING WITNESS ASKS THE PAGE, AND A BLANK PAGE CAN STILL ANSWER. `_UI_BEAT` is published
BY the document — `blankStrikes`, `elsHigh`, `rafNow` all come from JavaScript running inside the
window whose health is in question. That is not worthless (a wedged renderer stops beating), but
it cannot see the case he actually hit: a document that keeps beating while nothing reaches the
screen. This module never asks the page. It reads the compositor's own bitmap of his window.

⚠⚠ IT IS A WITNESS, NOT A TRIGGER, AND THAT IS DELIBERATE. Nothing here reloads, restarts, clicks
or writes. It answers one question — BLANK / PAINTED / UNKNOWN — and the rescue decides. Its most
valuable answer is the one that REFUSES: a window that is provably painted is a window that must
not be reloaded under him, whatever the beat says. [[heart-first]]

── WHY "MOSTLY DARK" WOULD HAVE BEEN WRONG, MEASURED ON HIS RUNNING CONSOLE ───────────────────
The obvious test is "is it black?". Measured on his live window (pid 11243, 1120x660) while it was
perfectly healthy: **72.7% of sampled pixels sit below luminance 24.** His console is a dark theme.
A darkness test would have called a healthy console blank every single time it ran.

What separates them is UNIFORMITY, not darkness — how much of the window is one single colour:

    surface                              modal share      distinct luminances
    his console, BLANK (caught live)        0.9963                 8-9
    his console, healthy                0.069 / 0.122           156 / 34
    Terminal                                0.6628                 117
    Safari                                  0.4892                 125
    a synthetic all-black buffer            1.0000                   1

⚠⚠ AND THE FIRST ROW IS WHY `distinct` IS NOT PART OF THE VERDICT. This module shipped with a
second bar, `distinct <= 4`, and then found his console **blank white with only the titlebar
drawn** — and called it PAINTED, because the CHROME contributes 8-9 luminances on its own. Every
fixture behind that bar was chrome-free and no real window ever is. **The one case it existed to
catch is the case it would have missed.** Modal share alone has a margin of 0.9963 against 0.6628
for the busiest ordinary window measured. [[visual-regression-detector]]

⚠ AND THE READING IS NOISY. His healthy console measured 156 distinct luminances one moment and 34
seconds later — the content moves. The margin to the bar is enormous (0.122 vs 0.98), but a single
frame is still a sample, so `blank_strikes()` requires CONSECUTIVE agreeing frames before anyone
should act. [[regression-guard]]

    python3 tv/paint_witness.py           # look at his console once, say what was seen
    python3 tv/paint_witness.py --json
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

#: a window smaller than this is a helper, not his console. Same rule and same number as
#: window_visibility.MIN_ON_SCREEN_PX — quoted below rather than re-typed, so the two cannot drift.
try:
    from window_visibility import MIN_ON_SCREEN_PX
except Exception:                                  # pragma: no cover - measured at import
    MIN_ON_SCREEN_PX = 40 * 40

#: THE BAR. Measured 2026-09-04 against his live console and three ordinary applications.
BLANK_MODAL_SHARE = 0.98    #: one colour covering ~all of the window
#: ⚠⚠ REPORTED, NOT REQUIRED — AND THE REASON IS A LIVE CATCH ON HIS OWN MACHINE.
#: This started as a second bar, `distinct <= 4`, calibrated against healthy windows and synthetic
#: all-black buffers. Then the harness was pointed at his running console and found it **blank
#: white, only the titlebar drawn** — the exact fault he reported — and called it **PAINTED**,
#: because the window CHROME (traffic lights, "TV DIABLO" title, the 1px rule under it) contributes
#: **9** distinct luminances all by itself. A real blank window is never chrome-free, and every
#: fixture I had built was. The conjunct would have failed on the only case that matters.
#:
#: Modal share alone separates them with room to spare, measured the same minute:
#:     his console, BLANK NOW      0.9963      <- caught
#:     his console, healthy    0.069 / 0.122
#:     Terminal                    0.6628
#:     Safari                      0.4892
#: 98% of a window being ONE colour is blank whether or not a titlebar is drawn on top of it.
BLANK_MAX_DISTINCT = 4      #: kept for the report; NOT part of the verdict — see above

#: how many CONSECUTIVE blank frames before this witness is willing to say so out loud. A single
#: frame can catch a legitimate mid-repaint moment; three cannot.
#: ⚠ THE INK BARS, calibrated on his console in BOTH states through this instrument (see verdict).
#: They sit in the empty middle of a 5x gap — blank p99 33 / healthy 177, blank 0.41% / healthy
#: 3.94% — so neither is a hair-trigger, and BOTH must agree before BLANK is declared.
INK_LUM = 90          #: a pixel at or above this counts as ink
INK_P99_MAX = 80      #: brightest 1% starting below this = no meaningful ink anywhere
INK_SHARE_MAX = 0.015 #: under 1.5% bright = nothing is drawn
#: ⚠⚠ v2944 — THE INK TEST MAY NOT FIRE ON A WINDOW THAT IS OBVIOUSLY PAINTED, and this bar is
#: guarded to the INK test ALONE. Conjoining `distinct` with the MODAL test is what failed on
#: 2026-09-04 — his blank-white console draws NINE distinct luminances from chrome alone and read
#: PAINTED — so the modal path above is deliberately left exactly as it is.
#:
#: A cross-family attack designed COLD by a different model family (GB-L-PIXEL-3, A3_dim_ink_theme)
#: landed here: a window with **distinct 140, modalShare 0.071** — arithmetically IDENTICAL to his
#: HEALTHY console (140, 0.069) — was declared BLANK because its p99 sat at 78, one point under the
#: 80 bar. 140 different shades is not a dead renderer under any theme.
#:
#: MEASURED on every real frame available, border excluded:
#:     his console, dark blank   (34 identical captures)   distinct 1
#:     his console, white blank  (18 identical captures)   distinct 1
#:     his console, painted                                distinct 152
#:     his console, healthy (live)                         distinct 140
#: Every blank measures ONE. The bar sits far above that and far below any painted frame.
#:
#: ⚠ IT IS A FLOOR, NOT A MEASUREMENT OF THE CASE THAT MATTERS MOST. The ink test exists for his
#: 2026-09-05 blank, a dark GRADIENT whose modalShare was 0.124 — and that frame is not among the
#: captures above, so ITS distinct is UNKNOWN. 64 is chosen to leave a dark gradient plus chrome
#: ample room while still refusing a window with a hundred-odd shades. If a genuine blank is ever
#: measured above it, this bar is wrong and the measurement wins.
INK_MAX_DISTINCT = 64

BLANK_STRIKES = 3

BLANK = "BLANK"
PAINTED = "PAINTED"
UNKNOWN = "UNKNOWN"


def _quartz():
    try:
        import Quartz
        return Quartz
    except Exception:
        return None


def window_for(pid, quartz=None):
    """The window id of the biggest on-screen window owned by `pid`. -> (id|None, why)

    ⚠ None is UNKNOWN, never "he has no console". A pid with no listed window may be starting,
    minimised, or on another Space, and none of those is a black screen.
    """
    Q = quartz if quartz is not None else _quartz()
    if Q is None:
        return None, "Quartz is not importable here - the window server cannot be asked"
    try:
        opts = Q.kCGWindowListOptionOnScreenOnly | Q.kCGWindowListExcludeDesktopElements
        rows = Q.CGWindowListCopyWindowInfo(opts, Q.kCGNullWindowID)
    except Exception as e:
        return None, "the window server refused the list (%s)" % type(e).__name__
    if rows is None:
        return None, "the window server returned nothing at all"
    best, best_area = None, 0.0
    for row in rows:
        try:
            if int(row.get("kCGWindowOwnerPID", -1)) != int(pid):
                continue
            b = row.get("kCGWindowBounds") or {}
            area = float(b.get("Width", 0)) * float(b.get("Height", 0))
        except Exception:
            continue
        if area >= MIN_ON_SCREEN_PX and area > best_area:
            best, best_area = row.get("kCGWindowNumber"), area
    if best is None:
        return None, ("pid %s owns no on-screen window big enough to be his console, which is not "
                      "the same as a blank one" % pid)
    return best, ""


OCCLUDED = "OCCLUDED"


def occluded_by(pid, quartz=None):
    """Is another window sitting ON TOP of his console? -> (list|None, why)

    ⚠ QUOTED, NOT REIMPLEMENTED. `window_visibility` owns every "what is the window server saying"
    question and now owns this one too (REG-594). My first cut walked the z-order here as well —
    a second copy of a safety rule is [[copy-drift]]'s worst case, and this one decides whether a
    healthy console gets reloaded under him.
    """
    try:
        import window_visibility as _wv
        return _wv.covered_by(pid=pid, quartz=quartz)
    except Exception as e:
        return None, "the window witness could not be asked (%s)" % str(e)[:70]


def _grab(window_id, quartz=None):
    """The compositor's bitmap of ONE window. -> (dict|None, why)

    ⚠ READ-ONLY ON HIS SURFACE. CGWindowListCreateImage neither focuses, raises, resizes nor
    activates the window — it copies what is already composited. Nothing here sends an event.
    [[borrowed-surface]]
    """
    Q = quartz if quartz is not None else _quartz()
    if Q is None:
        return None, "Quartz is not importable here"
    try:
        img = Q.CGWindowListCreateImage(
            Q.CGRectNull, Q.kCGWindowListOptionIncludingWindow, window_id,
            Q.kCGWindowImageBoundsIgnoreFraming | Q.kCGWindowImageNominalResolution)
    except Exception as e:
        return None, "the capture raised (%s: %s)" % (type(e).__name__, str(e)[:60])
    if img is None:
        # the usual cause is Screen Recording permission, and saying so beats a bare None
        return None, ("the window server returned no image - the window may have closed, or this "
                      "process may lack Screen Recording permission. Either way NOTHING WAS SEEN")
    try:
        w, h = Q.CGImageGetWidth(img), Q.CGImageGetHeight(img)
        buf = bytes(Q.CGDataProviderCopyData(Q.CGImageGetDataProvider(img)))
        return {"w": w, "h": h, "buf": buf,
                "bpr": Q.CGImageGetBytesPerRow(img),
                "bpp": Q.CGImageGetBitsPerPixel(img) // 8}, ""
    except Exception as e:
        return None, "the image would not yield its pixels (%s)" % type(e).__name__


#: how much of the top of a window is the OS title bar rather than anything the page drew.
#: Measured on his 1120x660 console: cropping 24px already clears the 0.98 bar (0.9872), 30px gives
#: 0.9966 and 36px 0.9998. 30 is taken because it clears with margin without eating page content —
#: and it is a floor, not a guess: the bar itself is ~28px at his scale.
#: ⚠ Skipped only on windows tall enough for it to be chrome rather than the whole thing, so a
#: small helper window is never measured down to nothing.
CHROME_TOP_PX = 36

#: ⚠⚠ v2953 — THE SIDES ARE CHROME TOO, AND ONLY THE TOP WAS EVER EXCLUDED.
#: The note beside the top crop already gives the whole reason — "The chrome is not evidence about
#: whether the page drew; it is drawn by the window server either way" — and then applied it to ONE
#: axis. The sampling loop ran `range(0, w)`, straight through the left and right window border.
#: MEASURED, by a cold cross-family attack (GB-L-PIXEL-3, designed by a different model family with
#: no hint from me): A1 "chrome bleed" — a DEAD body whose only bright pixels are a border hairline
#: — reads p99Luminance 255 and brightShare 0.0162, clearing both ink bars, so the witness calls a
#: dead window PAINTED. One bright row of window border vetoes emptiness.
#: ⚠ THE VALUE IS NOT MINE AND NOT NEW. `frozen_frames.SIDE_FRACTION` has excluded exactly this
#: since it was written, for exactly this reason: "rounded window corners and the 1px window border
#: are not evidence about what the page drew". Two pipelines measured the same window and disagreed
#: about what counted as evidence.
#: ⚠ COPIED, NOT IMPORTED, BECAUSE frozen_frames IMPORTS THIS MODULE — importing it back is a
#: cycle. A copy is only allowed if something holds the two together, so
#: test_chrome_alone_is_not_paint asserts they are equal. [[copy-drift]]
CHROME_SIDE_FRACTION = 0.02
#: ⚠⚠ v2752 — 30 WAS CHOSEN AGAINST THE MODAL TEST AND THE INK TEST OUTGREW IT. HIS BLACK CONSOLE
#: READ AS **PAINTED** BECAUSE OF TWO ROWS OF WINDOW CHROME.
#: Konyo, 2026-09-07, with a screenshot of a black console: *"black screen again.. something should
#: be catching this"*. Measured on that exact window (pid 4333, 1120x660) while it was blank:
#:
#:     crop  modalShare  brightShare  p99   verdict
#:      30     0.1252      0.0159     255   PAINTED   <- the shipped value
#:      31     0.1192      0.0159     230   PAINTED
#:      32     0.1240      0.0000      27   BLANK
#:      36     0.1252      0.0000      27   BLANK
#:
#: EVERY ONE of the 63 bright samples sat at **y=30 exactly** — the title bar's bottom border, at
#: luminance 255. 63 of 3,969 samples is 1.59%, just over the 1.5% INK_SHARE_MAX bar, and it also
#: dragged p99 to 255. So a completely blank window cleared BOTH ink conditions on chrome alone.
#:
#: ⚠ THE NOTE ABOVE IS STILL TRUE AND WAS STILL NOT ENOUGH: 30 was derived when the only test was
#: `modalShare >= 0.98`, where chrome merely dilutes. The INK test that came later asks whether ANY
#: pixel is bright, and two rows of 255 answer yes. The threshold outlived the instrument it was
#: measured against. [[label-outlived-referent]] [[feedback-threshold-above-the-ceiling]]
#: ⚠ THE COST, STATED: 6 more rows of page content are excluded from the sample. That is 0.9% of a
#: 660px window, and it buys the difference between seeing his black screen and not.


def measure(shot, samples=60):
    """How uniform is this bitmap? -> dict

    Returns the two numbers the bars are written against, plus the mean luminance — which is NOT
    used to decide anything and is reported because it is the number a reader will reach for
    first, and seeing it high on a blank white window is what stops them re-deriving the bar.
    """
    from collections import Counter
    w, h, buf, bpr, bpp = shot["w"], shot["h"], shot["buf"], shot["bpr"], shot["bpp"]
    # ⚠⚠ SKIP THE TITLE BAR, AND THIS IS WHY HIS BLANK WINDOW WAS NEVER ONCE CAUGHT.
    # Measured 2026-09-04 by capturing his actual window while he was reporting it black:
    #
    #     whole window            modalShare 0.9513  -> PAINTED   (wrong)
    #     excluding the top 30px  modalShare 0.9966  -> BLANK     (correct)
    #
    # A blank body plus a title bar reading "TV DIABLO" with three traffic lights is ~5% of the
    # pixels and NEVER uniform, so the chrome alone held the window three points under a 0.98 bar.
    # The module already knew chrome was the problem — its own note says "window CHROME draws 8-9
    # distinct luminances" — and answered it by dropping the DISTINCT conjunct, which left the
    # modal-share bar just as diluted. The chrome is not evidence about whether the page drew; it
    # is drawn by the window server either way. [[feedback-threshold-above-the-ceiling]]
    top = CHROME_TOP_PX if h > CHROME_TOP_PX * 4 else 0
    # ⚠ v2953 — the SIDE border, excluded for the same reason as the top.
    side = int(w * CHROME_SIDE_FRACTION) if w > CHROME_TOP_PX * 4 else 0
    lums, total = Counter(), 0
    for yy in range(top, h, max(1, (h - top) // samples)):
        for xx in range(side, max(side + 1, w - side),
                        max(1, (w - 2 * side) // samples)):
            o = yy * bpr + xx * bpp
            if o + 3 > len(buf):
                continue
            b, g, r = buf[o], buf[o + 1], buf[o + 2]
            lums[(r * 299 + g * 587 + b * 114) // 1000] += 1
            total += 1
    if not total:
        return {"samples": 0, "distinct": None, "modalShare": None, "meanLuminance": None,
                "why": "no pixel could be sampled, so nothing was measured"}
    modal, modal_n = lums.most_common(1)[0]
    # ⚠⚠ INK — THE ONLY STATISTIC THAT SEPARATES HIS ACTUAL BLANK WINDOW FROM A HEALTHY ONE.
    # `p99` is the luminance the brightest 1% of pixels start at, and `brightShare` is the
    # fraction at or above INK_LUM. Text on this console is bright gold/white on near-black, so a
    # window with anything drawn on it has a bright tail and a blank one does not.
    _ordered = sorted(lums.items())
    _cut, _seen, _p99 = int(total * 0.99), 0, _ordered[-1][0] if _ordered else 0
    for _l, _n in _ordered:
        _seen += _n
        if _seen >= _cut:
            _p99 = _l
            break
    _bright = sum(v for k, v in lums.items() if k >= INK_LUM)
    return {"samples": total, "distinct": len(lums),
            "modalShare": round(modal_n / float(total), 4),
            "modalLuminance": modal,
            "meanLuminance": round(sum(k * v for k, v in lums.items()) / float(total), 1),
            "p99Luminance": _p99,
            "brightShare": round(_bright / float(total), 4),
            "why": ""}


def verdict(m):
    """BLANK / PAINTED / UNKNOWN for ONE frame. -> (state, why)"""
    if not m or m.get("distinct") is None:
        return UNKNOWN, (m or {}).get("why") or "nothing was measured"
    d, share = m["distinct"], m["modalShare"]

    def _measured(x):
        # A bool is an int in Python, and True >= 0.98, so a flag would clear the blank bar.
        return (isinstance(x, (int, float)) and not isinstance(x, bool)
                and x == x and abs(float(x)) != float("inf"))

    # A share that is not a fraction, or a count that is not a count, is a failed measurement.
    # Calling it BLANK replaces the window he is looking at. UNKNOWN is the refusal.
    if not _measured(share) or not (0.0 <= float(share) <= 1.0):
        return UNKNOWN, ("modalShare is not a fraction of this window (%r), so BLANK is not "
                         "sayable" % (share,))
    if not _measured(d) or float(d) < 1:
        return UNKNOWN, ("the distinct-luminance count is not a measurement (%r), so BLANK is "
                         "not sayable" % (d,))
    # True < 80, so a boolean brightness sits inside the ink bar and would call a window blank.
    p99 = m.get("p99Luminance")
    bright = m.get("brightShare")
    if not _measured(p99):
        p99 = None
    if not _measured(bright):
        bright = None
    # ⚠ ORDER MATTERS AND MY OWN GUARD CAUGHT IT. The single-colour test runs FIRST because it is
    # the more specific case and it owns its own sentence. With the ink test first, a genuinely
    # flat window (modal 99.5%, no ink) was caught by ink and told "the single-colour test cannot
    # see this fault" — false for that window, since 99.5% is exactly what that test is for. A
    # right verdict under a wrong reason is how the last three attempts at this bug went.
    if share >= BLANK_MODAL_SHARE:
        return BLANK, ("%.1f%% of this window is a SINGLE colour (luminance %s) - nothing is drawn "
                       "on it. %d distinct luminance(s) found, which on a blank window is the "
                       "CHROME: the titlebar and its buttons draw whatever the page does not"
                       % (share * 100.0, m.get("modalLuminance"), d))
    # ⚠⚠ THE INK TEST, AND IT EXISTS BECAUSE THE MODAL TEST BELOW COULD NEVER FIRE ON HIS CONSOLE.
    # MEASURED 2026-09-05 through this same instrument, on his window in BOTH states plus a
    # known-painted window for a same-instrument reference:
    #
    #     window                     modalShare   p99   brightShare
    #     his console, BLANK to him      0.124     33      0.0041
    #     his console, HEALTHY           0.069    177      0.0394
    #     Terminal, full of text         0.628    254      0.0581
    #
    # ⚠ READ THE MODAL COLUMN. The PAINTED window scores 0.628 and the blank one 0.124 — the
    # blank window is FURTHER from the `>= 0.98` bar than a healthy one, because a text window has
    # a dominant background colour and this console's background is a dark GRADIENT that never
    # collapses to one colour. So `share >= 0.98` is not merely a high bar here; it is structurally
    # unreachable, and the check below has never once been able to report his actual fault.
    #
    # p99 and brightShare separate the two states with no overlap (33 vs 177, 0.41% vs 3.94%), and
    # the healthy console sits beside Terminal rather than beside its own blank state — so this is
    # not the dark theme being mistaken for emptiness.
    #
    # ⚠ BOTH must agree before this fires, and the bars sit in the empty middle of a 5x gap. A
    # window is BLANK-BY-INK only when its brightest 1% is dark AND almost nothing is bright.
    # ⚠ It reports a DISTINCT reason, never "one colour covers the window", because that sentence
    # would be false here and a wrong reason is how the last three attempts at this bug went.
    if (p99 is not None and bright is not None
            and d is not None and d <= INK_MAX_DISTINCT
            and p99 < INK_P99_MAX and bright < INK_SHARE_MAX):
        return BLANK, ("nothing is DRAWN on this window: its brightest 1%% of pixels start at "
                       "luminance %s (a painted console reads ~177) and only %.2f%% of it is "
                       "bright (~3.9%% when healthy). The commonest colour covers just %.1f%%, so "
                       "the single-colour test cannot see this fault at all — this console's "
                       "background is a gradient, not one flat colour"
                       % (p99, bright * 100.0, share * 100.0))
    if (d is not None and d > INK_MAX_DISTINCT
            and p99 is not None and bright is not None
            and p99 < INK_P99_MAX and bright < INK_SHARE_MAX):
        # ⚠ SAY WHICH TEST DECLINED AND WHY — a right verdict under a wrong reason is how the last
        # three attempts at this bug went, and this window is dim enough that the ink bars alone
        # would have called it empty.
        return PAINTED, ("this window is DIM (brightest 1%% at luminance %s, %.2f%% bright) but it "
                         "is not empty: %d distinct luminance(s) are drawn on it, and a dead "
                         "renderer leaves ONE. The ink test is declined above %d distinct"
                         % (p99, bright * 100.0, d, INK_MAX_DISTINCT))
    return PAINTED, ("the commonest colour covers %.1f%% of this window across %d distinct "
                     "luminance(s) - it has content on it (blank needs >= %.0f%%)"
                     % (share * 100.0, d, BLANK_MODAL_SHARE * 100.0))


def look(pid, quartz=None, samples=60):
    """One look at one window. -> dict, always the same shape."""
    out = {"pid": pid, "windowId": None, "state": UNKNOWN, "why": "", "measure": None,
           "bars": {"modalShare": BLANK_MODAL_SHARE, "strikes": BLANK_STRIKES,
                    "distinctReportedOnly": BLANK_MAX_DISTINCT}}
    wid, why = window_for(pid, quartz=quartz)
    if wid is None:
        out["why"] = why
        return out
    out["windowId"] = wid
    shot, why = _grab(wid, quartz=quartz)
    if shot is None:
        out["why"] = why
        return out
    m = measure(shot, samples=samples)
    out["measure"] = {k: v for k, v in m.items() if k != "why"}
    out["state"], out["why"] = verdict(m)
    # ⚠⚠ AND A UNIFORM FRAME IS ONLY BLANK IF NOTHING IS COVERING IT. See occluded_by: a window
    # under another app captures as a flat frame, and calling that BLANK accuses a healthy console.
    if out["state"] == BLANK:
        cov, cwhy = occluded_by(pid, quartz=quartz)
        if cov is None:
            out["state"] = UNKNOWN
            out["why"] = ("the frame is uniform, and whether anything is covering the window "
                          "could not be asked (%s) — so BLANK is not sayable" % cwhy)
        elif cov:
            out["state"] = OCCLUDED
            out["why"] = ("NOT blank — %s. The uniform frame is what capturing a covered window "
                          "returns, and the page reporting hidden/not-painting is CORRECT for "
                          "one." % cwhy)
    out["occludedBy"] = None if out["state"] != OCCLUDED else out["why"]
    return out


def blank_strikes(pid, strikes=None, quartz=None, sleep=None):
    """Is this window blank across CONSECUTIVE looks? -> dict

    ⚠⚠ ONE FRAME IS A SAMPLE, NOT A VERDICT. A repaint, a resize or a Space switch can catch a
    window mid-nothing. A window that is genuinely dead stays dead, so this asks again.

    ⚠ AND A SINGLE UNKNOWN ENDS IT. If any look could not be taken, the run is UNKNOWN — not
    "fewer strikes than needed", which would quietly read as healthier than the truth.
    """
    n = int(strikes or BLANK_STRIKES)
    looks, hit = [], 0
    for i in range(n):
        if sleep and i:
            sleep(0.35)
        r = look(pid, quartz=quartz)
        looks.append(r)
        if r["state"] == UNKNOWN:
            return {"state": UNKNOWN, "strikes": i, "needed": n, "looks": looks,
                    "why": "look %d of %d could not be taken (%s), so nothing is established "
                           "about this window" % (i + 1, n, r["why"])}
        if r["state"] == BLANK:
            hit += 1
        else:
            return {"state": PAINTED, "strikes": hit, "needed": n, "looks": looks,
                    "why": "look %d of %d found content on the window, so it is not blank: %s"
                           % (i + 1, n, r["why"])}
    return {"state": BLANK, "strikes": hit, "needed": n, "looks": looks,
            "why": "%d consecutive look(s) found a window with nothing drawn on it" % hit}


def contradicts_a_blank_beat(pid, quartz=None):
    """Do the PIXELS refute the page's own claim to be blank? -> (bool, why)

    THE VALUABLE DIRECTION, and the one his rescue needs most. `_UI_BEAT`'s blank counters come
    from JavaScript inside the window; this is the only check that can say *"the page thinks it is
    empty and I can see that it is not"*. True here should HOLD a rescue.

    ⚠ UNKNOWN IS NOT A CONTRADICTION. A capture that could not be taken returns False with its
    reason, so a missing witness never stops a rescue the beat genuinely called for — silence is
    not evidence. [[feedback-silence-is-not-evidence]]
    """
    r = look(pid, quartz=quartz)
    if r["state"] == PAINTED:
        return True, ("the window server's own bitmap shows content on this window: %s" % r["why"])
    if r["state"] == UNKNOWN:
        return False, ("the pixels could not be read (%s), so they refute nothing - this is an "
                       "absent witness, not a disagreeing one" % r["why"])
    return False, "the pixels agree that nothing is drawn on this window: %s" % r["why"]


def rescue_worked(pid, quartz=None, sleep=None, settle=2.5):
    """After a reload, did PAINTING actually come back? -> dict

    ⚠⚠ MEASURED ON HIS MACHINE, 2026-09-04, AND THIS IS WHY THE FUNCTION EXISTS. The watchdog
    detected the fault correctly and fired correctly — `uiBeat.rescues = 1`, reason *"the page is
    BEATING and DRAWING NOTHING: 20 beats with no frame while the DOM stayed intact (11841
    elements)"* — and **the window was still blank white afterwards**, with `frozenBeats` climbing
    29 → 38 and `painting` still false. The detection works. **The CURE does not cure**, and
    nothing anywhere checked: `rescues: 1` reads exactly like "handled".

    A self-heal that is never verified is a fault that stops being reported — by the machine.
    It goes on being reported by HIM. [[feedback-verify-not-proxy]] [[the-unjoined-end]]

    ⚠ UNKNOWN STAYS UNKNOWN. If the pixels cannot be read the answer is None, never "it worked".
    """
    if sleep:
        sleep(settle)
    r = look(pid, quartz=quartz)
    if r["state"] == UNKNOWN:
        return {"worked": None, "state": UNKNOWN, "why": (
            "whether the reload restored painting is UNKNOWN - the pixels could not be read (%s). "
            "That is not success." % r["why"])}
    if r["state"] == PAINTED:
        return {"worked": True, "state": PAINTED, "why": (
            "the reload restored painting: %s" % r["why"])}
    return {"worked": False, "state": BLANK, "why": (
        "THE RELOAD DID NOT RESTORE PAINTING - the window is still blank after it. Reloading the "
        "document cannot fix a compositor that has stopped presenting frames for this window, and "
        "counting this as a completed rescue is how the fault goes on being reported by him "
        "instead of by the machine. %s" % r["why"])}


def console_pid(port=None):
    """The pid actually LISTENING on his console port. -> int or None

    ⚠ None is UNKNOWN — "nobody is serving that port", never "his console is fine".
    """
    try:
        import console_port as _cport   # REG-2998 - its own console's port; an unreadable one is no console, never his
        port = int(port) if port else _cport.port()
    except Exception:
        port = None
    if not port:
        return None
    try:
        out = subprocess.check_output(["lsof", "-ti", "tcp:%d" % port],
                                      stderr=subprocess.DEVNULL, timeout=10)
    except Exception:
        return None
    for line in out.decode("utf-8", "replace").split():
        try:
            pid = int(line)
        except Exception:
            continue
        # ⚠ THE PORT HAS MORE THAN ONE OWNER. Measured 2026-09-08: :17772 was held by the console
        # (14222) AND by a WebKit XPC renderer service (60423) that serves no window of its own.
        # Take the one that owns a window; a renderer helper answers `window_for` with None.
        wid, _why = window_for(pid)
        if wid is not None:
            return pid
    return None


def main(argv):
    # ⚠⚠ IT USED TO DEFAULT TO `os.getpid()` — ITS OWN PROCESS. This module's own usage line says
    # `python3 tv/paint_witness.py   # look at his console once`, and with no argument it looked at
    # the interpreter running the witness, which owns no window. So it answered
    #
    #     UNKNOWN - pid <self> owns no on-screen window big enough to be his console
    #
    # every single time, forever. Caught 2026-09-08 while he was looking at a BLACK console window
    # and asking why nothing had noticed: the one hand-run instrument for "is his console blank"
    # had never once been pointed at his console. A default that measures the asker is not a
    # measurement. [[unknown-stays-unknown]] [[feedback-suspect-the-instrument]]
    # [[label-outlived-referent]]
    explicit = next((a for a in argv if a.isdigit()), None)
    pid = int(explicit) if explicit else console_pid()
    if pid is None:
        msg = ("UNKNOWN - nothing is listening on his console port, so there is no window to look "
               "at. That is not a blank console and not a healthy one.")
        if "--json" in argv:
            print(json.dumps({"state": UNKNOWN, "why": msg, "pid": None, "windowId": None},
                             indent=2, sort_keys=True))
        else:
            print("\n  %s\n" % msg)
        return 0
    r = look(pid)
    if "--json" in argv:
        print(json.dumps(r, indent=2, sort_keys=True, default=str))
        return 0
    print("\nPAINT WITNESS - what the compositor actually shows for pid %d\n" % pid)
    print("  window   %s" % (r["windowId"] if r["windowId"] is not None else "UNKNOWN"))
    print("  state    %s" % r["state"])
    m = r.get("measure") or {}
    if m:
        print("  measured %d sample(s) - %s distinct luminance(s), modal share %s, mean %s"
              % (m.get("samples"), m.get("distinct"), m.get("modalShare"), m.get("meanLuminance")))
    print("  bar      blank needs modalShare >= %.2f, over %d consecutive looks (distinct is "
          "reported, not required - chrome alone draws several)"
          % (BLANK_MODAL_SHARE, BLANK_STRIKES))
    print("\n  %s\n" % r["why"])
    return 0


if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
