# chronicle_template.py — v1690, THE MEASURED CHRONICLE TEMPLATE.
#
# Konyo: "every picture and screenshot taken within the chronicle feed... it needs to understand
# when the chronicle page gets opened and the template of the chronicle page is open... like a MINI
# version where we already have that has set parameters for this." This module IS that mini version
# for the Chronicle panel — a locked geometric template plus a detector that reads it, the way
# stash_eye's _TALLY_CROPS is the locked template for the stash grid.
#
# THIS IS THE TEMPLATE AND ITS PROOF ONLY (v1690). The three consumers — chronicle_retro.py (retro
# sweep), control_app.py (live closer), tv_diablo.py (live vision routing) — are DELIBERATELY NOT
# WIRED HERE. That is v1691, once this geometry has shipped and been read by a human. Nothing in
# this file imports or is imported by those three; grep for "chronicle_template" in them and expect
# zero hits until then.
#
# ── WHY A PIXEL PATH, NOT AN OCR-LINES PATH (round-1 correction #1) ──────────────────────────────
# Round 1 of this ship built `detect_from_ocr_lines`-shaped detection and was discarded: on real
# Chronicle frames with a found-item tooltip open (the exact footage motivating this ship), full-
# frame/worker OCR returns the TOOLTIP's text — "Required Strength", "Defense:", leet item affix
# lines — not "CHRONICLE" or "Unique"/"Sets". Even on a CLEAN panel, full-frame OCR barely surfaces
# the chrome at all; stash_eye's own tab-chrome path only gets readable text via a deliberate crop +
# 3x upscale, and even that stays fuzzy ("VNIQVE") rather than a clean token match. An OCR-line API
# would therefore return `tooltip`/unknown on precisely the case that matters most. `detect()` below
# reads PIXELS from the frame (same class of move as `control_app.py`'s closer, which already holds
# `fp` and calls `stash_eye.analyze_frame` for the identical reason — "full-frame OCR is dark").
# `detect_from_ocr_lines()` exists too, but only as a WEAK SECONDARY that can corroborate a pixel
# verdict in `why` — it must never be the production classify source and never overrides pixels.
#
# ── WHY THESE BANDS AND NOT STASH_EYE'S (round-1 correction #2) ──────────────────────────────────
# The Chronicle is a CENTERED MODAL, not stash_eye's LEFT-ANCHORED panel: title "CHRONICLE" · three
# tabs Unique | Sets | Runewords · a secondary Normal/Exceptional/Elite strip · a search box · a LEFT
# CATEGORY RAIL · a progress bar + "View Rewards" button · then the list. stash_eye's crops and its
# `x * cal_aspect/aspect` aspect law are written for a panel anchored at the left edge and cannot be
# copied onto a centered one without measuring first — which is how round 1 shipped invented
# fractions. Every band below was MEASURED by opening real frames from
# tv/frames/hist/reel_s_1786385768689_67392/ (native 2940x1912, the same calibration film stash_eye
# locked on) with vision and then reading their pixels directly (see MEASURED_ON below) — never
# derived by copying stash_eye's left-anchor math. Off-calibration aspects go through
# `_scale_band_for_aspect`, a DIFFERENT and CENTER-PRESERVING derivation which `geometry_signals()`
# ACTUALLY APPLIES to every x-band (`signals["band_branch"]` records which branch ran); it is
# explicitly labelled derived-not-measured, exactly as stash_eye labels its own untested 16:9 branch.
#
# ── WHY GEOMETRY IS GRADED SEPARATELY FROM VISION LABELS (round-1 correction #3) ──────────────────
# The 8 vision labels available for this reel are sparse and one of the eight is a conf-0.60 read
# whose `names` are literally `['Amulet'] * 7` — not clean ground truth. `test_chronicle_template.py`
# grades pixel geometry (measured, deterministic, reproducible from the source JPEGs) and the vision
# labels SEPARATELY and never averages them — grading a pixel template against sparse/low-confidence
# vision labels alone is how round 1 believed itself correct while its own detector flagged 30 of 31
# non-Chronicle controls AS Chronicle.
#
# ── ROUND 2 WAS REFUTED TOO. WHAT CHANGED, AND WHY (read this before touching a threshold) ────────
# Round 2 shipped a tab channel read off the SELECTED TAB'S GOLD BOX OUTLINE and an is_chronicle gate
# that was one signal wearing a template's clothes. A cross-family review ran it over the whole reel
# and broke it in three measured places. All three are fixed here, and the fix is a CHANNEL CHANGE,
# not a threshold nudge:
#
#   (a) THE GOLD-OUTLINE CHANNEL INVERTS UNDER THE OCCLUSION THIS SHIP EXISTS FOR. On
#       f_1786385904883.jpg the Unique tab is genuinely selected, with a "Radament's Sphere" tooltip
#       drawn across Sets/Runewords; the tooltip's gold item name scored 0.0415 in the runewords band
#       against the true tab's 0.0011 — 38x — so winner-take-all named "runewords", the one tab with
#       NO LEDGER PATH. Eight frames in the reel did this.
#   (b) SO DID TAB INTERIOR BRIGHTNESS, which was the obvious replacement and is MEASURED HERE TO
#       FAIL: on that same frame the tooltip scrim drags the true Unique tab to mean-luma 32.4 while
#       unselected Runewords sits at 34.9. Recorded so nobody re-derives it: brightness is not a tab
#       channel.
#   (c) THE ONE MARK THAT SURVIVES IS THE SELECTED-TAB MARKER — the small saturated BLUE DIAMOND the
#       game draws at the bottom-center of the active tab, below the tab box. It is the only
#       Chronicle chrome that is (i) positionally locked to one tab, (ii) a hue no D2R tooltip
#       chrome or gold text can imitate, and (iii) still legible through the tooltip scrim. Measured
#       blue-fraction in the marker window: clean Unique 0.0347, the SAME tab under the tooltip
#       scrim 0.0102, and EXACTLY 0.0000 on both unselected siblings in both frames. That is the
#       channel `detect()` now decides on. The gold-outline reading is kept in the signals dict as
#       corroboration for `why` and DOES NOT VOTE.
#   (d) A BLUE MARKER WINDOW CAN STILL BE POISONED — by the tooltip's own blue stat text. On
#       f_1786385826754.jpg the "Defense: (335-350)" line lands inside the runewords marker window
#       and reads 0.269, ~8x above any real diamond. So the marker channel carries an UPPER bound as
#       well as a lower one: a window above `_TAB_MARKER_MAX` is declared CONTAMINATED and cannot
#       win. That is the tab-band occlusion gate, and it watches the TAB BAND — not the far-right
#       search box, which is what round 2 watched while claiming to protect the tabs.
#   (e) is_chronicle NO LONGER RESTS ON ONE SIGNAL. Round 2's gate was `score >= 0.55` while the
#       close-X contributed exactly 0.55, so is_chronicle was literally "is there red in one
#       0.03x0.025 box" — a uniformly SOLID RED test image (tv/frames/hist/1_1785703546039.jpg)
#       returned True. `detect()` now counts FOUR independent votes and requires at least TWO, so no
#       single band can carry the verdict and list_midgray genuinely votes. The solid-red image
#       scores 1 vote and is refused.
#
# ── ONE MEASURED LIMIT, STATED RATHER THAN DISCOVERED IN v1691 ───────────────────────────────────
# THE MARKER CHANNEL NEEDS NATIVE-RESOLUTION FRAMES. tv/frames/hist/ also holds DOWNSCALED 1440x936
# copies of Chronicle frames (2_1786385782689.jpg and five siblings — same aspect, 1.5385, so they
# take the measured-mac branch). On those, `detect()` correctly returns is_chronicle=True but
# tab=None: at 1440px the diamond is ~14px across and antialiasing pulls every marker window to
# exactly 0.0000, and the thin secondary-strip lettering falls to 0.0000 too. That is the module
# REFUSING, which is the right failure — but v1691's readers must feed the NATIVE frame, not a
# thumbnail, or they will get a page they cannot attribute to a tab. Not fixed here by loosening the
# blue test: loosening it is exactly how the tooltip's blue stat text gets back in.
#
# ── PURE LAW (asserted structurally by test_chronicle_template.py, the way chronicle_retro's
#    write-free law is asserted) ── this module opens frame files to READ pixels. It performs NO
#    writes, NO deletes/renames, NO network calls, and NO model calls of any kind. It cannot tick,
#    untick, or otherwise touch d2r_foundLog/d2r_setPieces or any ledger — it only ever returns a
#    dict describing what a frame's pixels look like.
#
# ── THE RUNEWORDS DEAD END (documented, not silently folded) ──────────────────────────────────────
# The Chronicle panel has THREE tabs, but the board/intake kind vocabulary only recognises
# "chronicle-uniques" and "chronicle-sets" — there is no "chronicle-runewords" ledger kind anywhere
# in this project today. `detect()` still identifies tab="runewords" honestly when the pixels say so;
# `ledger_kind_for_tab("runewords")` returns None on purpose, and callers MUST treat that None as "no
# ledger path exists yet", never as "fold it into unique or sets". Wiring a runewords ledger is out
# of scope for this file.

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

FracBox = Tuple[float, float, float, float]

# ── CALIBRATION FILM — same film stash_eye locked _TALLY_CROPS on ─────────────────────────────────
# v3895 (#22, REG-3587) - ONE film, shared with stash_eye via reader_calibration.
import reader_calibration as _RC
_CAL_FILM = _RC.FILM
_CAL_ASPECT = _RC.aspect()
_CAL_LO, _CAL_HI = 1.45, 1.62  # Konyo's Mac range; stash_eye uses the same window

# ── MEASURED ON (evidence trail — the exact frames read with vision to lock the bands below) ──────
MEASURED_ON = {
    "reel": "reel_s_1786385768689_67392",
    "frames": [
        "f_1786385782444.jpg",  # nearest to requested ts 782689 — Unique tab, mid-scroll (Amulet rows)
        "f_1786385790530.jpg",  # nearest to requested ts 790213 — Unique tab, CLEAN: the band reference
        "f_1786385797582.jpg",  # nearest to requested ts 797924 — Unique tab, mid-scroll
        "f_1786385807514.jpg",  # nearest to requested ts 807604 — Unique tab, mid-scroll (Battle* rows)
        "f_1786385814507.jpg",  # nearest to requested ts 814341
        "f_1786385822654.jpg",  # nearest to requested ts 822222
        "f_1786385826754.jpg",  # nearest to requested ts 826830 — TOOLTIP OVER PANEL (Cerebus' Bite):
                                # true tab UNIQUE; the tooltip's blue "Defense: (335-350)" poisons the
                                # RUNEWORDS marker window at 0.269. Source of _TAB_MARKER_MAX.
        "f_1786385852357.jpg",  # nearest to requested ts 852302
        "f_1786385904883.jpg",  # THE FRAME THAT REFUTED ROUND 2 — "Radament's Sphere" tooltip drawn
                                # across Sets/Runewords, true tab UNIQUE. Source of the dimmed-marker
                                # floor (0.0102) and of the recorded gold/brightness inversions.
    ],
    "negative_control": "f_1786385773403.jpg",  # earliest frame in the same reel: pure gameplay, no panel
    # A second, ADVERSARIAL negative: a uniformly solid-red image that round 2's one-signal gate
    # classified as Chronicle. Kept named here so the regression can never be quietly dropped.
    "negative_control_solid_red": "1_1785703546039.jpg",
}

# ── LOCKED GEOMETRY — fractions of full-frame (W, H) on the calibration film ───────────────────────
# All bands MEASURED by cropping the real frames above at native 2940x1912 and reading the result.
# Nothing here was copied from stash_eye's _TALLY_CROPS.

# Whole modal: outer stone-frame border, anchored to the CENTER of the viewport (not the left edge).
MODAL_BAND: FracBox = (0.215, 0.060, 0.785, 0.941)

# "CHRONICLE" gold title, centered top of the modal.
# NOTE: title gold was MEASURED AND REJECTED as an is_chronicle vote — 0.0065 on a clean Chronicle
# frame vs 0.0054 on pure gameplay in the same reel (torchlit stone reads gold too). The band stays
# because it is real geometry a v1691 reader may crop; it does not vote.
TITLE_BAND: FracBox = (0.30, 0.062, 0.70, 0.115)

# Red X close button, top-right corner of the modal frame.
CLOSE_X_BAND: FracBox = (0.770, 0.065, 0.800, 0.090)

# The full tab-strip row: three tabs + the search box, all on one row directly under the title.
TAB_STRIP_BAND: FracBox = (0.375, 0.135, 0.765, 0.173)
TAB_BANDS: Dict[str, FracBox] = {
    "unique": (0.378, 0.137, 0.462, 0.171),
    "sets": (0.462, 0.137, 0.542, 0.171),
    "runewords": (0.542, 0.137, 0.623, 0.171),
}
SEARCH_BAND: FracBox = (0.623, 0.137, 0.765, 0.171)

# THE SELECTED-TAB MARKER WINDOW — the blue diamond under the ACTIVE tab. Measured from the clean
# frame: the diamond's centroid sits at frame-x 0.4197 against the Unique tab's own center 0.4200,
# i.e. it is locked to the tab's horizontal center, and vertically just BELOW the tab box.
# Half-width 0.010 of frame width (~29px on the calibration film) and y 0.1715..0.1820 (~20px) is the
# tightest window that holds the whole diamond; the y floor of 0.1715 is what keeps the tooltip's
# blue stat lines (which start ~0.19) out on most frames — 826754 is the case where one does get in,
# and _TAB_MARKER_MAX is what catches it.
_MARKER_HALF_W = 0.010
MARKER_Y: Tuple[float, float] = (0.1715, 0.1820)

# Secondary strip: Normal / Exceptional / Elite checkboxes + the "All" category dropdown, right below
# the tab row. This is the second INDEPENDENT is_chronicle vote — bright gold panel text on a band
# no gameplay HUD occupies.
SECONDARY_STRIP_BAND: FracBox = (0.239, 0.190, 0.762, 0.215)

# Left category rail: Armor / Weapons / Accessories tree, the % progress bar, and "View Rewards".
LEFT_RAIL_BAND: FracBox = (0.239, 0.230, 0.383, 0.780)

# The scrolling list of items — this is what a v1691 reader would page through.
LIST_BAND: FracBox = (0.400, 0.222, 0.762, 0.941)

# Vertical fraction of frame height per list row, measured from consecutive row centers in the clean
# frame (f_1786385790530.jpg): displayed-pixel row centers ~290,388,485,582,680,777,874 (2000px-wide
# render) give a pitch of ~97.3px there -> 97.3/1301 of frame height.
ROW_PITCH_FRAC = 0.0746

# Tabs with no ledger path in the board/intake kind vocabulary today. See "THE RUNEWORDS DEAD END"
# above. Kept as a set (not a single constant) so a future ledger kind removes itself from here in
# one edit instead of a scattered `!= "runewords"` check.
NO_LEDGER_TABS = frozenset({"runewords"})

_LEDGER_KIND_BY_TAB = {
    "unique": "chronicle-uniques",
    "sets": "chronicle-sets",
    # "runewords" intentionally absent — see NO_LEDGER_TABS.
}

#: ⚠ TWO PRODUCERS, TWO SPELLINGS, ONE CONCEPT — and for a while, two resolvers that each only
#: understood their own. MEASURED before this existed:
#:
#:     tab        ledger_kind_for_tab   chronicle_kind
#:     'unique'   chronicle-uniques     None              <-- disagree
#:     'uniques'  None                  chronicle-uniques <-- disagree
#:     'sets'     chronicle-sets        chronicle-sets
#:
#: `ct.detect()` reports "unique" (this file, :501, and the marker box at :165 is keyed on it);
#: READ_PROMPT asks the model for "uniques" (tv_diablo.py:402-403). Neither is wrong for its own
#: producer, so neither could simply be renamed. This is the one place that says they are the same
#: word, and both resolvers quote it. A third spelling appearing anywhere fails
#: tv/test_tab_vocabulary.py rather than silently resolving in one half of the console.
TAB_ALIASES = {
    "unique": "unique",
    "uniques": "unique",
    "set": "sets",
    "sets": "sets",
    "runeword": "runewords",
    "runewords": "runewords",
}


def canonical_tab(tab):
    """Any spelling either producer emits -> the one this module keys on. -> str | None

    None means "not a tab word I know", which is a different fact from "a tab with no ledger"
    (that is `runewords`, and it canonicalises fine before resolving to None as a ledger).
    [[unknown-stays-unknown]]
    """
    if not tab:
        return None
    return TAB_ALIASES.get(str(tab).strip().lower())


def ledger_kind_for_tab(tab: Optional[str]) -> Optional[str]:
    """The board/intake ledger kind for a detected tab, or None when there isn't one yet.

    None is not a bug to route around — for "runewords" it means the ledger genuinely does not
    exist; for anything else it means the tab itself was not established (occluded/ambiguous).
    """
    if not tab:
        return None
    # through the alias map, so the model's "uniques" and the template's "unique" land together
    return _LEDGER_KIND_BY_TAB.get(canonical_tab(tab) or "")


# ── ASPECT SCALING — CENTER-PRESERVING, DIFFERENT FROM STASH_EYE'S LEFT-ANCHOR LAW ────────────────
def _scale_band_for_aspect(frac: FracBox, aspect: float) -> Tuple[FracBox, str]:
    """Scale a width band to an off-calibration aspect, preserving the panel's CENTER.

    stash_eye's law (`x * cal_aspect/aspect`) is correct for a panel anchored at x=0 — the left
    edge stays put and only the right edge moves. The Chronicle modal is anchored at its CENTER, so
    the same formula would silently drag the whole panel sideways. This scales the half-width around
    the band's own midpoint instead. It is exactly as DERIVED-NOT-MEASURED as stash_eye's own 16:9
    branch — no off-Mac Chronicle frame has confirmed it — and every reading produced through it is
    labelled so, downstream, the way stash_eye's `_LAST_CROP["branch"]` does.

    THIS IS LIVE CODE, not documentation: `geometry_signals()` routes EVERY x-band through it and
    reports the branch it took as `signals["band_branch"]`. Round 2 claimed this and did not do it.
    """
    x0, y0, x1, y1 = frac
    if not aspect or aspect <= 0:
        return frac, "no-aspect"
    if _CAL_LO <= aspect <= _CAL_HI:
        return frac, "measured-mac"
    k = _CAL_ASPECT / float(aspect)
    cx = (x0 + x1) / 2.0
    half = (x1 - x0) / 2.0 * k
    return (max(0.0, cx - half), y0, min(1.0, cx + half), y1), "derived-not-measured"


# ── PIXEL SIGNAL THRESHOLDS — calibrated against MEASURED_ON's frames, not statistically fit ───────
# Every number below is a reading taken off a named frame; the reading is quoted beside it. A
# threshold with no measured reading beside it does not belong in this file.
#
# close-X red button: measured 0.0682 on both a clean Chronicle frame and a tooltip-occluded one
# (the close button sits outside where a tooltip draws); 0.0000 on the gameplay negative control.
# It is ONE VOTE OF FOUR now — a solid-red image also scores it, which is exactly why it cannot gate.
_CLOSE_X_RED_THRESH = 0.03
# Normal/Exceptional/Elite gold strip: measured 0.0345 clean, 0.0143 and 0.0152 on the two
# tooltip-occluded frames, and 0.0000 on BOTH negative controls (gameplay AND solid red). The
# cleanest Chronicle-vs-not separator this module has; 0.005 sits ~3x under the weakest positive.
_SEC_GOLD_THRESH = 0.005
# ── UPPER BOUNDS: EVERY BAND SIGNAL HAS ONE, NOT JUST THE MARKER ──────────────────────────────────
# _TAB_MARKER_MAX taught the general law and it applies to the whole class: a real Chronicle chrome
# element occupies a BOUNDED fraction of its own band — a small red X on stone, thin gold lettering
# on stone. A band that is MOSTLY red or MOSTLY gold is not a stone panel, it is fire. Measured on
# tv/frames/hist/f_1785708388296.jpg ("Entering the River of Flame", pure gameplay, no panel):
# close_x_red 0.7963 and sec_gold 0.1005, against a real Chronicle's 0.0682 and 0.0345 — the two
# sibling River-of-Flame frames read 0.5602/0.0698 and 0.2009/0.1343. Those three were this module's
# only remaining false positives across 383 swept frames; both bounds sit ~2x above anything a real
# Chronicle has ever measured and ~2x below the fire.
_CLOSE_X_RED_MAX = 0.35
_SEC_GOLD_MAX = 0.06
# list interior mid-gray stone (sampled at stride 4): measured 0.6934 clean / 0.4810 / 0.4922 on
# Chronicle frames vs 0.4077 and 0.4055 on gameplay and 0.0000 on solid red. This is a WEAK vote by
# design — the tooltip case reads 0.3969 and legitimately does not score it. It only ever supplies
# one of the two votes is_chronicle needs, never both.
_LIST_MIDGRAY_THRESH = 0.45
# SELECTED-TAB BLUE MARKER — the tab channel. Measured 0.0347 (clean Unique), 0.0102 (same tab under
# a tooltip scrim), 0.0000 on every unselected sibling on every measured frame. Floor 0.004 sits
# ~2.5x under the dimmed reading and infinitely above the siblings' exact zero.
_TAB_MARKER_MIN = 0.004
# ...and the upper bound that makes this survive a tooltip: measured 0.269 where the tooltip's blue
# "Defense: (335-350)" text fell inside the runewords marker window — ~8x the brightest real diamond
# ever measured (0.0347). 0.10 sits ~3x above any real marker and ~2.7x below the poisoned reading.
_TAB_MARKER_MAX = 0.10
# search box brightness: measured 0.0233 clean, 0.0048 under a tooltip that partially covers the
# search box, 0.0000 with no panel open. REPORTED ONLY. Round 2 used this as the tab occlusion gate,
# which was wrong twice over: it watched a box 0.16 of the frame away from the tabs it claimed to
# protect, and it passed the failing frame by 0.0013. The tab occlusion gate is now _TAB_MARKER_MAX,
# inside the tab band itself.
_SEARCH_BRIGHT_THRESH = 0.012
# selected-tab gold/tan box outline: measured 0.0022 on the Unique tab's own outline on clean frames.
# CORROBORATION ONLY, NEVER A VOTE — on f_1786385904883.jpg the tooltip's gold item name scored
# 0.0415 in the runewords band against the true tab's 0.0011, a 38x inversion. It stays in the
# signals dict so `why` can say whether the outline agreed, and so this refutation stays measurable.
_TAB_BORDER_THRESH = 0.001


def _open_rgb(path: str):
    from PIL import Image  # type: ignore

    return Image.open(path).convert("RGB")


def _crop_frac(im, frac: FracBox):
    w, h = im.size
    x0, y0, x1, y1 = frac
    box = (
        max(0, int(w * x0)),
        max(0, int(h * y0)),
        min(w, max(1, int(w * x1))),
        min(h, max(1, int(h * y1))),
    )
    if box[2] <= box[0] or box[3] <= box[1]:
        return None
    return im.crop(box)


def _sample(crop, stride: int = 2):
    """Yield (r,g,b) at a stride — sampling, not scanning every pixel, keeps this cheap and pure."""
    w, h = crop.size
    px = crop.load()
    for x in range(0, w, stride):
        for y in range(0, h, stride):
            yield px[x, y]


def _red_fraction(crop) -> float:
    n = tot = 0
    for r, g, b in _sample(crop):
        tot += 1
        if r > 130 and (r - g) > 50 and (r - b) > 50:
            n += 1
    return n / tot if tot else 0.0


def _bright_fraction(crop, thresh: float = 150.0) -> float:
    n = tot = 0
    for r, g, b in _sample(crop):
        tot += 1
        if (0.299 * r + 0.587 * g + 0.114 * b) > thresh:
            n += 1
    return n / tot if tot else 0.0


def _midgray_fraction(crop) -> float:
    # stride 4: the list band is ~1058x1376px on the calibration film and this runs over whole reels.
    n = tot = 0
    for r, g, b in _sample(crop, stride=4):
        tot += 1
        l = 0.299 * r + 0.587 * g + 0.114 * b
        if 35 <= l <= 110 and abs(r - g) < 18 and abs(g - b) < 18:
            n += 1
    return n / tot if tot else 0.0


def _gold_fraction(crop) -> float:
    """Bright panel gold — the Normal/Exceptional/Elite lettering. Tighter than _gold_border_fraction:
    it demands a real gold SEPARATION (r-b >= 55), which is what keeps torchlit gameplay stone out."""
    n = tot = 0
    for r, g, b in _sample(crop):
        tot += 1
        if 120 <= r <= 245 and 95 <= g <= 215 and b < 155 and (r - b) >= 55 and (r - g) >= 10:
            n += 1
    return n / tot if tot else 0.0


def _gold_border_fraction(crop) -> float:
    n = tot = 0
    for r, g, b in _sample(crop, stride=3):
        tot += 1
        if 100 <= r <= 210 and 80 <= g <= 180 and 50 <= b <= 150 and (r - b) >= 15 and r >= g - 5:
            n += 1
    return n / tot if tot else 0.0


def _blue_marker_fraction(crop) -> float:
    """Saturated blue — the active-tab diamond. Deliberately narrow: b must dominate BOTH r and g by
    a wide margin, which no gold/tan/stone Chronicle chrome and no torchlit gameplay pixel does."""
    n = tot = 0
    for r, g, b in _sample(crop, stride=1):
        tot += 1
        if b > 90 and (b - r) > 35 and (b - g) > 18:
            n += 1
    return n / tot if tot else 0.0


def _marker_band_for(tab: str) -> FracBox:
    """The blue-diamond window for a tab: its own horizontal CENTER +/- _MARKER_HALF_W, at MARKER_Y."""
    x0, _, x1, _ = TAB_BANDS[tab]
    cx = (x0 + x1) / 2.0
    return (cx - _MARKER_HALF_W, MARKER_Y[0], cx + _MARKER_HALF_W, MARKER_Y[1])


def geometry_signals(frame_path: str) -> Optional[Dict[str, Any]]:
    """The raw MEASURED pixel signals for a frame — no thresholds, no verdict.

    Exists so tests (and any future caller) can grade geometry on its own terms, separate from the
    sparse/low-confidence vision labels (round-1 correction #3). Returns None if the frame cannot be
    opened at all — never a zeroed-out dict pretending to be a real reading.
    """
    if not frame_path or not os.path.isfile(frame_path):
        return None
    try:
        im = _open_rgb(frame_path)
    except Exception:
        return None
    w, h = im.size
    aspect = (w / float(h)) if h else 0.0

    branches = set()

    def band(frac: FracBox) -> FracBox:
        scaled, br = _scale_band_for_aspect(frac, aspect)
        branches.add(br)
        return scaled

    close_x = _crop_frac(im, band(CLOSE_X_BAND))
    search = _crop_frac(im, band(SEARCH_BAND))
    listband = _crop_frac(im, band(LIST_BAND))
    secondary = _crop_frac(im, band(SECONDARY_STRIP_BAND))
    if close_x is None or search is None or listband is None or secondary is None:
        return None

    tab_border: Dict[str, float] = {}
    tab_marker: Dict[str, float] = {}
    for tab in TAB_BANDS:
        c = _crop_frac(im, band(TAB_BANDS[tab]))
        tab_border[tab] = round(_gold_border_fraction(c), 4) if c is not None else 0.0
        m = _crop_frac(im, band(_marker_band_for(tab)))
        tab_marker[tab] = round(_blue_marker_fraction(m), 4) if m is not None else 0.0

    # One branch label for the whole read: if ANY band was derived, the whole reading is derived.
    if "derived-not-measured" in branches:
        band_branch = "derived-not-measured"
    elif "no-aspect" in branches:
        band_branch = "no-aspect"
    else:
        band_branch = "measured-mac"

    return {
        "size": (w, h),
        "aspect": round(aspect, 4),
        "band_branch": band_branch,
        "close_x_red": round(_red_fraction(close_x), 4),
        "search_bright": round(_bright_fraction(search), 4),
        "list_midgray": round(_midgray_fraction(listband), 4),
        "sec_gold": round(_gold_fraction(secondary), 4),
        "tab_marker": tab_marker,
        "tab_border": tab_border,
    }


def resolve_tab(sig: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """Name the selected tab from the BLUE MARKER channel, or refuse. Returns (tab|None, why).

    Three ways this refuses, each one a measured failure of round 2's outline channel:
      - every marker window is either empty or CONTAMINATED (>_TAB_MARKER_MAX): the tab band is
        occluded, so there is nothing honest to say;
      - two or more windows are validly lit: ambiguous, and a Sets page tallied as Uniques writes a
        wrong count into his grail truth;
      - the winner's own window is contaminated: a blue blob is not a diamond.
    """
    marker = sig.get("tab_marker") or {}
    # ⚠⚠ A8 — THE TEMPLATE MUST BE THE MECHANISM, AND IT WAS NOT. This named ANY tab present in
    # the marker dict, including one with no template band at all: handed
    # {"tab_marker": {"hardcore": 0.05}} it answered `hardcore`, a tab TAB_BANDS has never heard
    # of. `geometry_signals` only ever produces keys from TAB_BANDS today, so nothing was wrong on
    # this tree — but the router's correctness rested on an upstream convention it did not check,
    # which is the shape that breaks the day a band is renamed, a dict is merged, or an OCR
    # artefact adds a key. His ask for A8 was that the templates be what the routing filters WITH,
    # not a pass beside it; a tab that can be routed without a template is the opposite.
    #
    # ⚠ AND AN UNDECLARED TAB IS DROPPED, NOT GUESSED AT. `ledger_kind_for_tab` returns None for
    # it, so letting it through means an unknown kind flowing onward under a real-looking name.
    # [[the-unjoined-end]] [[unknown-stays-unknown]]
    _no_template = sorted(t for t in marker if t not in TAB_BANDS)
    if _no_template:
        marker = {t: v for t, v in marker.items() if t in TAB_BANDS}
    contaminated = [t for t, v in marker.items() if v > _TAB_MARKER_MAX]
    lit = [t for t, v in marker.items() if _TAB_MARKER_MIN <= v <= _TAB_MARKER_MAX]

    note = ""
    if _no_template:
        note = ("; marker window(s) %s have NO TEMPLATE BAND — dropped, because a tab this module "
                "cannot describe is not a tab it may name" % _no_template)
    if contaminated:
        note = ("; marker window(s) %s CONTAMINATED (>%.2f, tooltip blue text) — excluded"
                % (sorted(contaminated), _TAB_MARKER_MAX))

    if not lit:
        return None, ("tab band unreadable: no clean selected-tab marker (%s)%s — refusing to name a "
                      "tab" % (marker, note))
    if len(lit) > 1:
        return None, ("tab ambiguous: %d marker windows lit (%s)%s — refusing to name a tab"
                      % (len(lit), marker, note))

    tab = lit[0]
    why = "selected-tab blue marker on %s (%.4f; siblings %s)%s" % (
        tab, marker[tab],
        {t: v for t, v in marker.items() if t != tab},
        note,
    )
    border = (sig.get("tab_border") or {}).get(tab, 0.0)
    if border >= _TAB_BORDER_THRESH:
        why += "; gold outline corroborates (%.4f)" % border
    else:
        why += "; gold outline did NOT corroborate (%.4f) — outline is occlusion-fragile, marker wins" % border
    if tab in NO_LEDGER_TABS:
        why += ("; tab=%s has NO LEDGER PATH today (NO_LEDGER_TABS) — not folded into unique or sets"
                % tab)
    return tab, why


def detect(frame_path: str) -> Dict[str, Any]:
    """detect(frame) -> {is_chronicle, tab, confidence, why}

    PURE: reads pixels from frame_path, nothing else. No writes, no network, no model call.

    is_chronicle needs at least TWO of four INDEPENDENT votes (close-X red button / secondary
    Normal-Exceptional-Elite gold strip / list interior stone-gray / a clean selected-tab marker).
    No single band can carry it — that is what let round 2 call a solid-red image a Chronicle.

    tab is one of "unique" | "sets" | "runewords" | None — None whenever the tab strip cannot be
    read with confidence (occluded by a tooltip, ambiguous, or the panel isn't Chronicle at all).
    A Sets page misread as Uniques writes a wrong count into his grail truth, so this REFUSES
    (tab=None) rather than guessing whenever the signal is not clean.
    """
    sig = geometry_signals(frame_path)
    if sig is None:
        return {"is_chronicle": False, "tab": None, "confidence": 0.0,
                "why": "frame unreadable or missing"}

    tab_candidate, tab_why = resolve_tab(sig)

    votes = []
    reasons_pre = []
    score = 0.0
    if _CLOSE_X_RED_THRESH <= sig["close_x_red"] <= _CLOSE_X_RED_MAX:
        votes.append("close-X")
        score += 0.30
    elif sig["close_x_red"] > _CLOSE_X_RED_MAX:
        reasons_pre.append("close-X band %.4f is ABOVE _CLOSE_X_RED_MAX %.2f — that is fire/red "
                           "scenery, not a red X on stone; vote refused"
                           % (sig["close_x_red"], _CLOSE_X_RED_MAX))
    if _SEC_GOLD_THRESH <= sig["sec_gold"] <= _SEC_GOLD_MAX:
        votes.append("secondary-gold")
        score += 0.30
    elif sig["sec_gold"] > _SEC_GOLD_MAX:
        reasons_pre.append("secondary strip %.4f is ABOVE _SEC_GOLD_MAX %.2f — that is a gold-lit "
                           "scene, not thin gold lettering on stone; vote refused"
                           % (sig["sec_gold"], _SEC_GOLD_MAX))
    if sig["list_midgray"] >= _LIST_MIDGRAY_THRESH:
        votes.append("list-stone")
        score += 0.25
    if tab_candidate is not None:
        votes.append("tab-marker")
        score += 0.25

    is_chronicle = len(votes) >= 2

    reasons = ["votes %d/4 %s" % (len(votes), votes),
               "close_x_red %.4f, sec_gold %.4f, list_midgray %.4f, search_bright %.4f"
               % (sig["close_x_red"], sig["sec_gold"], sig["list_midgray"], sig["search_bright"]),
               tab_why] + reasons_pre

    if not is_chronicle:
        reasons.append("fewer than 2 independent signals — NOT Chronicle")

    if sig["band_branch"] == "derived-not-measured":
        score = min(score, 0.6)
        reasons.append("aspect %.3f outside the measured %.2f-%.2f window: bands went through "
                       "_scale_band_for_aspect (center-preserving, DERIVED NOT MEASURED) — treat "
                       "this reading as UNCONFIRMED" % (sig["aspect"], _CAL_LO, _CAL_HI))

    # A tab is only ever reported for a frame this module is willing to call Chronicle at all.
    tab = tab_candidate if is_chronicle else None
    if tab_candidate is not None and not is_chronicle:
        reasons.append("a marker was found but the frame is not Chronicle — tab withheld")

    return {
        "is_chronicle": bool(is_chronicle),
        "tab": tab,
        "confidence": round(min(1.0, max(0.0, score)), 2) if is_chronicle else 0.0,
        "why": "; ".join(reasons),
    }


def detect_from_ocr_lines(lines) -> Optional[str]:
    """WEAK SECONDARY ONLY (round-1 correction #1). Never the production classify source, never
    allowed to override a pixel verdict from `detect()`. Exists purely so a caller with OCR lines
    already in hand (e.g. a lane that ran OCR for some other reason) can add one more corroborating
    word to `why` — nothing here should ever gate is_chronicle or tab on its own.

    Returns a loose guess ("unique"/"sets"/"runewords") or None; deliberately does not distinguish
    "found nothing" from "no lines given" because neither is trustworthy enough to act on alone.
    """
    if not lines:
        return None
    text = " ".join(str(l) for l in lines).upper()
    if "RUNEWORD" in text:
        return "runewords"
    if "SETS" in text or "SET ITEM" in text:
        return "sets"
    if "UNIQUE" in text or "VNIQVE" in text:
        return "unique"
    return None


if __name__ == "__main__":
    import sys

    from console_safe import enable

    enable()
    for p in sys.argv[1:]:
        print(p, detect(p))
