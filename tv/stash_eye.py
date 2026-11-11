# stash_eye.py — eye/brain frame analysis that MIMICS the perfected tally intakes
# without calling or changing gemIntake / runeIntake / materialIntake.
#
# Source of crop truth: bible.html `_tallyPrepImage` v341.59 LOCKED fractions
# (aspect 1.45–1.62, W≥1200 fullscreen D2R):
#   runes: x0=0.083 y0=0.20 x1=0.402 y1=0.468  (9-wide, cube-wrapped)
#   gems:  x0=0.105 y0=0.205 x1=0.388 y1=0.445  (clean 7×5)
# Tab chrome sits JUST ABOVE that grid band — we OCR an upscaled strip there so
# Personal/Shared/Gems/Materials/Runes are readable (full-frame OCR is dark).
#
# Used by: control_app KAI closer + router votes; tv_diablo live stashTab resolve.
# NEVER imports bible, NEVER fires intake, NEVER mutates stash tallies.

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ── LOCKED crop fractions (mirror bible.html _tallyPrepImage) ──────────────
_TALLY_CROPS = {
    "runes": (0.083, 0.20, 0.402, 0.468),
    "gems": (0.105, 0.205, 0.388, 0.445),
    # materials uses the same left-panel band as runes (generic left stash)
    "materials": (0.083, 0.20, 0.402, 0.468),
    "shared": (0.083, 0.18, 0.402, 0.55),
    "personal": (0.083, 0.18, 0.402, 0.55),
}
# Tab labels ride above the grid; measured on 2940×1912 film of this product
_TAB_CHROME = (0.08, 0.12, 0.40, 0.205)

# ── v1536 — THE ASPECT THE CROPS WERE LOCKED AT, and how to reach any other one ──────────────
# Konyo: "there might be something to do with resolution for MACBOOK/WINDOWS? we had that situation
# for the AI INTAKE and we recalibrated it accordingly."  He was right, and it is worse than a
# tweak: every band above was measured on HIS MAC (2940×1912, aspect 1.538) and the caller only
# used them for 1.45 <= aspect <= 1.62. A normal Windows monitor is 16:9 = 1.778, OUTSIDE that gate,
# so his cousin's frames fell to the "foreign/windowed" fallback — the whole left 46% of the screen.
# Measured: on 1920×1080 that hands the reader a 954k-pixel slab where the Mac gets a 177k-pixel
# band. The grid arrives 5.4x more diluted, and both the tab-strip OCR and the grid fingerprint are
# reading a much emptier picture. That is "it didn't read his runestash".
#
# THE DERIVATION (not a guess): D2R scales its UI with HEIGHT and anchors the stash panel to the
# left of the viewport. So a panel spanning fraction x of the width at aspect a0 spans x * (a0/a1)
# at aspect a1; the vertical fractions do not move. One rule, every aspect.
#
# ⚠ DERIVED, NOT YET MEASURED ON A REAL 16:9 FRAME. The Mac path is byte-identical (asserted), so
# this cannot regress Konyo; it replaces a KNOWN-bad fallback with a principled band for everyone
# else. Confirm against one real Windows stash frame and, if it needs nudging, record the measured
# numbers here the way the Mac ones are recorded above.
_CROP_CAL_FILM = (2940, 1912)     # the film every band above was measured on
# the EXACT ratio, not 1.538: a rounded constant put a 0.0001 skew into every derived band,
# which the derivation's own test caught. The bands are measurements; the conversion between
# them should not add error of its own.
_CROP_CAL_ASPECT = _CROP_CAL_FILM[0] / float(_CROP_CAL_FILM[1])
_CROP_CAL_LO, _CROP_CAL_HI = 1.45, 1.62


# v1538 — WHAT THE LAST FRAME ACTUALLY DID. The v1536 band is DERIVED and has never met a real 16:9
# stash frame; Konyo asked "if i run it on my windows is it good to test?" — it is, but only if the
# answer is visible. This records which branch each frame took and at what aspect, so ONE ON AIR on
# a Windows box turns the question into a fact instead of an impression.
_LAST_CROP = {"aspect": None, "branch": "", "layout": "", "band": None, "size": None}


def last_crop_decision():
    """Read-only: how the most recent frame was cropped, and why."""
    return dict(_LAST_CROP)


def crops_for_aspect(layout: str, aspect: float, route=None):
    """The crop band for THIS frame's aspect. Returns None when no honest band can be derived.

    `route` is the capture route of the frame (capture_stamp); a route whose geometry was measured uses it (REG-1875)."""
    frac = _TALLY_CROPS.get(layout) or _TALLY_CROPS["runes"]
    if not aspect or aspect <= 0:
        return None
    if _CROP_CAL_LO <= aspect <= _CROP_CAL_HI:
        _LAST_CROP.update({"aspect": round(aspect, 4), "branch": "locked-mac",
                           "layout": layout, "band": frac})
        return frac                                   # ★ Konyo's Mac — untouched, exactly as locked
    if aspect < 1.3:
        _LAST_CROP.update({"aspect": round(aspect, 4), "branch": "no-band-windowed",
                           "layout": layout, "band": None})
        return None                                   # windowed / letterboxed oddity: no honest band
    # REG-1712 — OUTSIDE HIS FILM'S BAND THE ONE UI LAW DECIDES (slot_identity.frame_band): the panel scales with
    # HEIGHT and stays CENTRED - measured 2026-10-02 on both panels of his 1440x904 frames. The left-anchor derivation
    # this used put a 16:9 runes band's right edge at 0.348 of the width while the stash grid runs to 0.405: a third
    # of Dean's stash outside the crop. INSIDE the band (his Mac) the measured crops above stay locked, untouched -
    # they work, and their margins hold the panel at every aspect in it.
    import slot_identity as _si
    x0, y0, x1, y1 = _si.frame_band(frac, aspect, route=route)
    band = (max(0.0, x0), y0, min(1.0, x1), y1)
    _LAST_CROP.update({"aspect": round(aspect, 4),
                       "branch": "derived-edge" if _si.edge_anchored(route, aspect) else "derived", "layout": layout,
                       "band": tuple(round(v, 4) for v in band)})
    return band

_TALLY_TABS = frozenset(("runes", "gems", "materials"))
_VAULT_TABS = frozenset(("personal", "shared"))
_ALL_TABS = _TALLY_TABS | _VAULT_TABS

# v948.8 — D2R TITLE/RECONNECT SPLASH GUARD. classify_stash_grid's materials
# branch (dark_empty>=0.42 + a little chroma, low gear/tan) is tuned loose on
# purpose (materials is the tab most prone to under-detection — Konyo's repeated
# complaint). That looseness has a false-positive twin: the D2R title/reconnect
# screen ("Press Any Key to Begin" / "Connecting to Battle.net") is ~92% pure
# black with a burning-logo sliver of orange/red chroma — same signature as a
# near-empty materials grid. Caught 2026-07-21 auditing reel
# s_1784636825977_40909: 11 consecutive boot-screen frames grid-fingerprinted
# as stash-materials and the KAI retro funnel spent its one materials shot on
# one of them (materialIntake correctly came back ok:false/total:0 — nothing
# was there — but the slot was wasted and the routing ledger lied about tab
# state). Full-frame OCR still reads the splash text even when the tab-chrome
# crop is pure black, so it's a clean, additive guard that never tightens (and
# so never regresses) the fragile grid heuristic itself.
def is_boot_screen(ocr_lines: Optional[Sequence[Any]]) -> bool:
    """True when full-frame OCR lines match the D2R title/reconnect splash.

    Word-level (not exact-phrase) match — OCR on the fire-lit splash text is
    noisy ("PRESS ANY KfY T& BEGIN" for "...KEY TO BEGIN"), so a strict phrase
    regex missed the exact frame this guard was built for. Any one of these
    combos is distinctive enough that a real stash/gameplay frame won't hit it."""
    blob = " " + re.sub(r"[^a-z0-9]+", " ", " ".join(str(t) for t in (ocr_lines or [])).lower()) + " "
    if blob.strip() == "":
        return False
    def has(w):
        return (" " + w + " ") in blob
    if has("press") and has("any") and has("begin"):
        return True
    if has("connecting") and has("battle"):
        return True
    if has("diablo") and has("resurrected"):
        return True
    if has("blizzard") and has("entertainment"):
        return True
    return False


def stash_chrome_canons(lines: Optional[Sequence[Any]]) -> List[str]:
    """WHICH stash tab labels are legible in this strip — the raw hits, in canon form.

    v1860. This was the private middle of tab_from_ocr_lines(), and burying it conflated two
    questions that have different answers and different consequences:

      "IS THE STASH PANEL OPEN?"  — answered by how many canon labels are legible. This chrome
                                    renders only when the panel is open, so ONE is already proof
                                    and FIVE is overwhelming proof.
      "WHICH TAB IS SELECTED?"    — answered by which one, and honestly unanswerable from labels
                                    alone, because the strip prints all five whichever is active.

    Fusing them meant the CLEAREST evidence of an open stash produced the same answer as an empty
    frame: '' — and every caller reading that as "not a stash" refused his best footage. Measured
    on his own reels, four frames printed PERSONAL · SHARED · GEMS · MATERIALS in one strip and the
    vault gate turned all four away. [[the-unjoined-end]]

    Returns canon names in a stable order; the list length is the admission signal.
    """
    blob = " ".join(str(t).lower() for t in (lines or []))
    if not blob.strip():
        return []          # a LIST, always — "" is falsy and len()==0 too, which is exactly how a
                           # wrong type survives review; a caller doing canons[0] would have found it
    # normalize common OCR garble of RotW tab labels (never break the word "materials")
    blob = re.sub(r"matera?l\$?", "materials", blob)   # mATERIAL$ style
    blob = re.sub(r"materlal", "materials", blob)
    blob = re.sub(r"sha[ak]e?d", "shared", blob)
    blob = re.sub(r"pers[o•\*]*n?a?l?", "personal", blob)
    # gems garbles: G→6/9, m→rn/nn, trailing $/s noise (Gems is the shortest label
    # so OCR mangles it hardest — the ROUND-2 miss). Keep bounded to gem-ish tokens.
    blob = re.sub(r"\b[6g9]e[rmn]{1,3}[sz$]?\b", "gems", blob)
    blob = re.sub(r"\bgens\b", "gems", blob)
    blob = re.sub(r"\bgemz\b", "gems", blob)
    order = (
        ("materials", "materials"), ("material", "materials"),
        ("runes", "runes"), ("gems", "gems"),
        ("personal", "personal"), ("shared", "shared"),
        ("rune", "runes"), ("gem", "gems"),
    )
    hits: List[str] = []
    for key, canon in order:
        if re.search(r"(?<![a-z])" + re.escape(key) + r"(?![a-z])", blob):
            if canon not in hits:
                hits.append(canon)
    return hits


def tab_from_ocr_lines(lines: Optional[Sequence[Any]]) -> str:
    """Active-tab GUESS from OCR lines — and a guess is all it is.

    Stash chrome always prints ALL five tab names — first-hit order wrongly
    returned 'materials' whenever the strip was fully readable. Rule:
      · 0 hits → ''
      · 1 unique canon → that tab
      · 2+ canons → '' (ambiguous chrome; pixel/grid fingerprint decides)

    ⚠ '' MEANS "I CANNOT TELL WHICH TAB", NEVER "THIS IS NOT A STASH". Ask
    stash_chrome_canons() when the question is whether the panel is open — v1857
    shipped a lane assignment built on this return value and it mis-filed a full
    Runes stash as gems. [[unknown-stays-unknown]]
    """
    hits = stash_chrome_canons(lines)
    if len(hits) == 1:
        return hits[0]
    return ""


def _open_rgb(path: str):
    from PIL import Image  # type: ignore
    im = Image.open(path).convert("RGB")
    return im


def _crop_frac(im, frac: Tuple[float, float, float, float]):
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


def prep_tab_chrome(src_path: str, dest_path: str, scale: int = 3) -> Optional[str]:
    """Intake-style: crop tab chrome ABOVE the tally grid, upscale, high-contrast JPEG.

    Returns dest_path on success, else None. Mimics how intakes enlarge digits —
    tab labels need the same treatment or Vision/OCR returns [].
    """
    try:
        from PIL import ImageEnhance, ImageOps  # type: ignore
        im = _open_rgb(src_path)
        crop = _crop_frac(im, _TAB_CHROME)
        if crop is None:
            return None
        sw, sh = crop.size
        # the number the whole REG-086 diagnosis turned on: how much picture the reader was handed
        _LAST_CROP["size"] = [sw, sh]
        # 2026-08-20 — THIS FUNCTION HAS RETURNED None FOR 310 VERSIONS.
        #
        # These four lines were pasted here from prep_stash_grid, where `derived`, `aspect` and
        # `layout` are all local. In prep_tab_chrome none of them exist, so the line raised
        # NameError on EVERY call — and the function's own `except Exception: return None` swallowed
        # it. Introduced in v1538 (cc9c6f71); found at v1848 while building the vault's structural
        # gate, because that gate could not pass a single genuine stash frame.
        #
        # What it cost: the stash TAB CHROME is the one non-model signal for which tab is open, and
        # stash_eye's own note says the chrome "only becomes readable via a deliberate crop + 3x
        # upscale". With this dead there was no readable chrome, so nothing could confirm a stash
        # panel structurally and every ownership frame fell back to a model's guess — the exact
        # failure vault_retro warns about in its own words: "a rune tab misread as 'inventory' files
        # his runes in the wrong lane, which merge-max then makes permanent."
        #
        # A bare `except Exception` that returns a plausible value is how a function dies silently
        # and stays dead. The telemetry it was trying to write is kept, corrected to describe what
        # THIS function actually does: one fixed band, no derived layout.
        _w, _h = im.size
        _aspect = (_w / float(_h)) if _h else 0.0
        _LAST_CROP.update({"aspect": round(_aspect, 4), "branch": "tab-chrome",
                           "layout": "", "band": list(_TAB_CHROME)})
        if sw < 8 or sh < 4:
            return None
        up = crop.resize((max(8, sw * scale), max(8, sh * scale)), getattr(__import__("PIL.Image", fromlist=["Image"]).Image, "LANCZOS", 1))
        g = ImageOps.autocontrast(up.convert("L"))
        g = ImageEnhance.Contrast(g).enhance(2.4)
        # also keep a color path for Vision OCR workers that want RGB
        rgb = up.convert("RGB")
        rgb = ImageEnhance.Contrast(rgb).enhance(1.8)
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)) or ".", exist_ok=True)
        rgb.save(dest_path, format="JPEG", quality=95)
        return dest_path
    except Exception:
        return None


def _frame_has_a_band(w, h, stamp):
    """Whether the one UI law may crop this frame. -> bool

    A frame at least 1200 wide is the case the law was already applied to.
    A narrower frame is that law only when a capture stamp names a measured window
    of the same aspect (the film is that window, or a downscale of it). A narrow
    frame with no such stamp is unknown: the old left-46% slab was a guess.
    """
    try:
        w = int(w)
        h = int(h)
    except (TypeError, ValueError):
        return False
    if w >= 1200 and h > 0:
        return True
    if w <= 0 or h <= 0 or not isinstance(stamp, dict):
        return False
    cw, ch = stamp.get("w"), stamp.get("h")
    if isinstance(cw, bool) or isinstance(ch, bool):
        return False
    if not (isinstance(cw, int) and isinstance(ch, int) and cw > 0 and ch > 0):
        return False
    client = cw / float(ch)
    return abs((w / float(h)) - client) / client <= 0.02


def _stamp_route(w, h, stamp):
    """REG-1875 — the capture route this frame was filmed through, or None. -> str | None

    Only when the stamp's own window has this frame's aspect (the film is that window, or a downscale of it): a stamp
    naming some other window says nothing about this frame, so its route does not move the band."""
    if not isinstance(stamp, dict):
        return None
    cw, ch = stamp.get("w"), stamp.get("h")
    if isinstance(cw, bool) or isinstance(ch, bool) or not (isinstance(cw, int) and isinstance(ch, int)):
        return None
    try:
        w, h = int(w), int(h)
    except (TypeError, ValueError):
        return None
    if w <= 0 or h <= 0 or cw <= 0 or ch <= 0:
        return None
    client = cw / float(ch)
    if abs((w / float(h)) - client) / client > 0.02:
        return None
    r = stamp.get("route")
    return r if isinstance(r, str) and r else None


def prep_stash_grid(src_path: str, dest_path: str, layout: str = "runes",
                    max_edge: int = 1200, cap: float = 3.2, stamp=None) -> Optional[str]:
    """Mimic _tallyPrepImage crop+enlarge for a layout (runes|gems|materials|shared).

    Pure image prep — does NOT call intake or the model.
    `stamp` is the reel's capture record (route, client w, h). It does not invent a band.
    """
    try:
        from PIL import Image  # type: ignore
        im = _open_rgb(src_path)
        w, h = im.size
        aspect = (w / float(h)) if h else 0
        frac = _TALLY_CROPS.get(layout) or _TALLY_CROPS["runes"]
        # v1536 — one rule for every aspect. The old shape gave the calibrated band ONLY to
        # 1.45-1.62 (Konyo's Mac) and dropped everything else — every 16:9 Windows frame — to a
        # 46%-of-screen slab. A derived band is strictly better than a slab, and the Mac branch is
        # unchanged.
        # A film under 1200 wide (the ALT caps the jpeg at 800) is the same law when the reel
        # recorded a window of that aspect. Without that record the slab is a guess, so no crop.
        if not _frame_has_a_band(w, h, stamp):
            return None
        derived = crops_for_aspect(layout, aspect, route=_stamp_route(w, h, stamp))   # REG-1875
        if derived:
            crop = _crop_frac(im, derived)
        elif aspect >= 1.3:
            # genuinely foreign (windowed, letterboxed, phone photo) — whole left 46%, as before
            crop = im.crop((0, 0, max(8, int(w * 0.46)), h))
        else:
            crop = _crop_frac(im, frac)
        if crop is None:
            return None
        sw, sh = crop.size
        scale = min(cap, max_edge / float(max(sw, sh, 1)))
        nw = max(1, int(round(sw * scale)))
        nh = max(1, int(round(sh * scale)))
        up = crop.resize((nw, nh), Image.LANCZOS)
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)) or ".", exist_ok=True)
        up.save(dest_path, format="JPEG", quality=92)
        return dest_path
    except Exception:
        return None


# v1258 — STASH-PANEL-OPEN GUARD thresholds. Derived from measuring the intake crop of
# confirmed frames across every historical reel:
#   · real open stash tabs (gems/runes/materials/personal/shared) — frac_dark ~0.31-0.42
#     (dark cells behind icons) and MANY dark-gridline columns (the lattice), typ. 12-25.
#   · Mac desktop WALLPAPER (Screen-Recording-TCC miss) — frac_dark ≈ 0.01 (smoothly-lit
#     photograph), ZERO dark-gridline columns, yet huge chroma from city lights.
# A frame must show BOTH the dark-cell band AND the lattice to be treated as an open
# stash panel; a frame with almost no dark cells is affirmatively NOT-D2R (a photograph).
_PANEL_DARK_MIN = 0.12     # real stash crop is substantially dark cells
_PANEL_DARK_MAX = 0.62     # above this = boot/loading/dark-combat, not an open panel
_PANEL_MIN_DARKCOLS = 4    # ≥4 dark-gridline columns = grid lattice present (wallpaper=0)
# v1909 — AND AN UPPER BOUND, WHICH IS WHAT REG-203 WAS MISSING. A stash grid is a LATTICE: a
# bounded number of dark gridline columns out of 84. A dark PICTURE is not a lattice — most of its
# columns are dark. The v1258 rule had a floor and no ceiling, so a fire-lit Nihlathak temple
# (dark_cols 31-40) satisfied "grid lattice present" as easily as a real panel (7-14).
#
# MEASURED ON HIS WHOLE 883-FRAME HIST, before → after:
#     tally claims   9  →  1        (the 1 is 8_1785078207015, the ONLY true positive)
#     stash bucket  69  → 77        (the 8 false tallies are demoted, not discarded)
#     real panels    5/5 kept, both ways
# The 8 that go are one fire-lit fight sequence; REG-203 named it and measured 8 of 9 wrong.
#
# ⚠ I FIRST CONCLUDED THIS CAP WAS UNSAFE, FROM THE FEATURE TABLE, AND THE MEASUREMENT SAID
# OTHERWISE. A real stash panel on the SHARED tab reads dark_cols=40, which looks fatal — but the
# plain-stash path does not require panel_open, so those frames still come back `stash`. The cap
# only gates the TALLY branches, where the real panels read 7 and 14 and the false ones 31-39.
# Reasoning from the features was wrong; running it decided. [[feedback-suspect-the-instrument]]
#
# WHY 24: real tally panels max at 14, false ones start at 31 — a 17-column gap, and 24 sits in the
# middle of it rather than on either knife-edge. dark_cols spans 0-71 across his corpus, so this is
# a threshold the signal can actually cross in both directions. [[feedback-threshold-above-ceiling]]
#
# THE ASYMMETRY THAT SETTLES THE DIRECTION: a MISSED tally costs one more look at the shelf (the
# post-seal funnel rechecks); a FALSE tally writes a tally count for a panel that was never open.
_PANEL_MAX_DARKCOLS = 24
# v2326 — the gear floor that a VISIBLE LATTICE buys. Above every negative in the corpus
# (0.000, 0.001, 0.029) and below the 0.08 gate it relieves, so it can only ever ADD a claim
# to a frame that already shows a grid.
_LATTICE_GEAR_FLOOR = 0.05


def lattice_says(dark_cols, frac_gear):
    """What the GRID ITSELF says, before any colour argument. -> (verdict|None, why)

    Pulled out of classify_stash_grid so it can be put to a case with numbers instead of
    screenshots — the same reason drift_may_relaunch and retention_may_act are separate. A
    decision that needs a 1.8 MB frame to exercise is a decision nobody tests on CI.

    "gameplay" means THERE IS NO GRID HERE and no colour statistic may overrule that.
    "stash"    means a grid is visibly present and carries enough gear to claim the panel.
    None       means the lattice has no opinion; the colour branches decide as before.
    """
    try:
        dc = int(dark_cols)
        fg = float(frac_gear)
    except (TypeError, ValueError):
        return None, "lattice unreadable"          # unknown is not a verdict [[unknown-stays-unknown]]
    if dc < _PANEL_MIN_DARKCOLS:
        return "gameplay", ("no lattice - %d dark column(s), under the %d a real grid always has"
                            % (dc, _PANEL_MIN_DARKCOLS))
    if fg >= _LATTICE_GEAR_FLOOR:
        return "stash", ("a lattice of %d columns carrying gear %.3f" % (dc, fg))
    return None, ""
_NOT_D2R_DARK_MAX = 0.05   # a lit photograph has essentially no dark stash cells


def _panel_open_from_features(frac_dark: float, dark_cols: int) -> Tuple[bool, bool]:
    """Positive 'the D2R stash panel is actually open' evidence from cheap grid geometry.

    Returns (panel_open, not_d2r):
      panel_open — dark-cell band AND a visible grid lattice (dark gridline columns).
                   REQUIRED precondition for any stash-gems/runes/materials grid label.
      not_d2r    — almost no dark cells at all → a smoothly-lit photograph (desktop
                   wallpaper), affirmatively not a game frame; reject before ANY label.

    Pure — no I/O. Kept deliberately light (two already-computed pixel features)."""
    fd = float(frac_dark or 0.0)
    dc = int(dark_cols or 0)
    not_d2r = fd < _NOT_D2R_DARK_MAX
    panel_open = (
        (not not_d2r)
        and (_PANEL_DARK_MIN <= fd <= _PANEL_DARK_MAX)
        and (_PANEL_MIN_DARKCOLS <= dc <= _PANEL_MAX_DARKCOLS)
    )
    return panel_open, not_d2r


# ── v1912 — THE SELECTED TAB IS IN THE PIXELS, AND IT IS THE GEM ────────────────────────────────
# REG-205 filed this OPEN: "the selected stash tab IS visible in the pixels; reading it is not
# solved." It tried the obvious thing — crop the chrome, split it into five equal cells, take the
# argmax mean luminance — and got 1 of 3 on margins of 1-5 grey levels, because the labels are not
# equal width and a cell straddles two of them.
#
# The obvious thing was the wrong FEATURE. D2R does not merely brighten the active tab; it draws a
# gold box around it AND sets a small BLUE GEM on the underline directly beneath it. That gem is
# tiny, saturated, and sits at a position no other chrome occupies — a structural marker, not a
# brightness contest.
#
# MEASURED, on the twelve hand-labelled frames of stash_grid_truth.json:
#     five real panels     -> 5/5 correct   (personal, shared x2, materials, and the one below)
#     seven non-panels     -> 0 false tabs  (zero qualifying blue pixels in the band)
#
# THE GEOMETRY IS REGULAR, and that is a MEASUREMENT rather than an assumption. The gem centres came
# out at personal 0.141, shared 0.324, materials 0.691 of the strip — differences of 0.183 and
# 0.367, exactly one and two pitches. So the five centres are 0.141 + 0.1835*i, which PREDICTS
# gems at 0.508 and runes at 0.875. When this was written no frame in his corpus had those two tabs
# open, so both were recorded as UNVERIFIED rather than quietly counted as covered.
#
# ✅ v1919 — BOTH PREDICTIONS ARE NOW VERIFIED, on his own footage, and they came in on the nose.
# vault_corpus.py found the missing frames in the REELS — a half of the archive no stash measurement
# had ever touched (the 883 loose frames in frames/hist and the 1,970 inside the reels share ZERO
# filenames). Opened and looked at, gold box and gem both on the named tab:
#     f_1784984269782  RUNES  detector x=0.874   predicted 0.875   (off by 0.001)
#     f_1784984271825  GEMS   detector x=0.506   predicted 0.508   (off by 0.002)
# A pitch derived from three tabs placed the other two to within two thousandths of the strip. The
# reader is 5 of 5 tabs, and the corpus behind that claim is 151 tab-readable frames, not 12.
#
# ⚠ THE FALSE POSITIVE THAT ALMOST SHIPPED: run without the guards below, this named a tab on 131
# of his 883 frames, 125 of them "personal" — and five of the six I opened were SOLID BLUE capture
# failures. Every pixel qualifies as blue, so the "centre of the strongest blue" lands wherever the
# arithmetic puts it. It is the same shape as this file's own oldest scar, "69 wallpaper frames
# sealed as stash-gems". Both guards are measured, and both gaps are enormous:
#     qualifying blue px:  real 2-18        solid blue 1025
#     strip luminance sd:  real 32.7-35.2   solid blue 0.00   (a flat fill has no variance)
_GEM_MIN_PX = 2            # the tooltip-occluded frame shows only 2 and is still right
_GEM_MAX_PX = 200          # a gem is small; a blue SCREEN is not
_GEM_MIN_STRIP_SD = 8.0    # chrome has structure; a flat fill has none
_GEM_BAND = (0.74, 0.90)   # the underline the gem sits on, as a fraction of the chrome crop
_GEM_FIRST = 0.141         # measured centre of tab 1
_GEM_PITCH = 0.1835        # measured spacing, from three tabs spanning four pitches
_GEM_TABS = ("personal", "shared", "gems", "materials", "runes")


def tab_from_gem(src_path: str) -> Tuple[str, Dict[str, Any]]:
    """Which stash tab is SELECTED, read off the active-tab gem. ("" , detail) when it cannot say.

    Never guesses: no gem, too much "gem", or a strip with no structure all return "". An honest
    empty is the whole point — a plausible-but-wrong tab detector is the precise defect v1857 and
    v1859 already cost.
    """
    detail: Dict[str, Any] = {"method": "tab-gem"}
    try:
        from PIL import Image, ImageStat  # type: ignore
        im = _open_rgb(src_path)
        w, h = im.size
        if w < 200 or h < 200:
            return "", detail
        c = _crop_frac(im, _TAB_CHROME)
        if c is None:
            return "", detail
        W, H = c.size
        sd = ImageStat.Stat(c.convert("L")).stddev[0]
        detail["stripSd"] = round(float(sd), 2)
        if sd < _GEM_MIN_STRIP_SD:
            detail["why"] = "the tab strip has no structure — a flat fill, not chrome"
            return "", detail
        px = c.load()
        hits = []
        for y in range(int(H * _GEM_BAND[0]), int(H * _GEM_BAND[1])):
            for x in range(W):
                r, g, b = px[x, y]
                if b > 110 and b - r > 45 and b - g > 25:
                    hits.append((x, b - max(r, g)))
        detail["gemPx"] = len(hits)
        if len(hits) < _GEM_MIN_PX:
            detail["why"] = "no active-tab gem found"
            return "", detail
        if len(hits) > _GEM_MAX_PX:
            detail["why"] = "too much blue to be a gem (%d px) — a blue screen, not a panel" % len(hits)
            return "", detail
        hits.sort(key=lambda t: -t[1])
        top = hits[:40]
        cx = sum(x for x, _ in top) / float(len(top)) / float(W)
        detail["gemX"] = round(cx, 4)
        idx = int(round((cx - _GEM_FIRST) / _GEM_PITCH))
        if idx < 0 or idx >= len(_GEM_TABS):
            detail["why"] = "the gem is outside the tab strip (x=%.3f)" % cx
            return "", detail
        return _GEM_TABS[idx], detail
    except Exception as e:
        detail["why"] = "could not read the tab strip: %s" % str(e)[:80]
        return "", detail


# ── v2028 — THE INVENTORY TITLE, THE ONE ANCHOR A STASH-SIDE TOOLTIP CANNOT COVER ────────────
_INV_BAND = (0.60, 0.08, 1.00, 0.20)


#: v3881 (REG-3388) - why the last inventory_title_visible() answered None (UNKNOWN), for the bench and a doctor to quote
_INV_TITLE_LAST: Dict[str, Any] = {"why": None}


def inventory_title_visible(src_path: str) -> Optional[bool]:
    """Is D2R's gold INVENTORY title printed on the right of this frame?

    WHY THIS EXISTS. stash_screen_open admits a frame only if stash_chrome_canons finds a legible
    tab label. A D2R hover tooltip is drawn ON TOP of that tab strip, so the gate refuses, with
    perfect consistency, exactly the frames that contain a readable item NAME — and keeps the bare
    grids, which print no names at all. That is why every vault sweep came back "no name to be had".

    LOOKED AT, not inferred. Two refused frames:
      f_1784984195842.jpg  "Sullied Grand Charm of Blight" — its "Ctrl + Left Click to Move to
                           Inventory" line sits straight across the tab row.
      f_1787508818939.jpg  "Marshal's Amulet" — "Shift + Left Click to Equip" over GEMS/MATERIALS.
    On the second, the chrome still OCRs as ['StrNAL','SHAktD','GE',...] — PERSONAL and SHARED are
    THERE, corrupted just past the fuzzy matcher's tolerance ('SHAkED' canonicalises, 'SHAktD' does
    not). Loosening that matcher would be the dangerous fix; this is the additive one, in the same
    spirit as the is_boot_screen guard above: it never tightens the fragile heuristics and so can
    never regress them.

    The title sits on the FAR RIGHT, opposite the stash tab strip, so a stash-side tooltip cannot
    reach it — and D2R draws the inventory beside the stash whenever the stash is open, which is
    exactly the "both at the same time" template the vault gate was built around.

    Band calibrated on his own 2940x1912 frames; the OCR is forgiving about the O, because the
    engine reliably returns INVENT&RY / INVf NT&RY / I NVENT&R Y.
    """
    try:
        import os as _os
        import tempfile as _tf
        from PIL import Image  # type: ignore
        import tv_diablo as _tvd
        im = _open_rgb(src_path)
        w, h = im.size
        if w < 200 or h < 200:
            return False
        x0, y0, x1, y1 = _INV_BAND
        box = im.crop((int(w * x0), int(h * y0), int(w * x1), int(h * y1)))
        box = box.resize((box.width * 3, box.height * 3), Image.LANCZOS)
        out = _os.path.join(_tf.gettempdir(), "inv_title_%d.jpg" % _os.getpid())
        box.save(out, quality=92)
        rd = _tvd.ocr_fast(out)
        if rd is None:
            # v3881 (REG-3388) - THE OCR DID NOT READ, SO NOTHING WAS SEEN EITHER WAY. ocr_fast answers None when the OCR
            # is off, has no worker on this OS, or erred - and this said False ("no inventory title") for all three. The
            # reader-parity bench (#255) counted those as AGREEMENTS between a Mac and a Windows PC whose OCR never ran.
            # Callers test truthiness, so None refuses exactly as False did; the difference is that UNKNOWN is now SAID.
            _INV_TITLE_LAST["why"] = "the OCR did not read the title band (off, no worker on this OS, or an error)"
            return None
        j = " ".join(str(x) for x in (rd.get("raw_lines") or rd.get("lines") or [])).upper()
        j = j.replace("0", "O").replace("&", "O").replace("@", "O").replace(" ", "")
        _INV_TITLE_LAST["why"] = None
        return ("INVENT" in j) or ("NVENTO" in j) or ("NVENTR" in j)
    except Exception as e:
        _INV_TITLE_LAST["why"] = "the title band could not be read (%s)" % type(e).__name__
        return None


def classify_stash_grid(src_path: str) -> Tuple[str, Dict[str, Any]]:
    """Pixel fingerprint of the left stash GRID (intake crop region) → tab guess.

    Mimics the spirit of _runeSheetPrep (luminance / owned-stone detection) and
    gem colour columns — WITHOUT running the intake model.

    Returns (label, detail) where label is one of:
      stash-runes | stash-gems | stash-materials | stash | gameplay
    """
    detail: Dict[str, Any] = {"method": "grid-fingerprint"}
    try:
        from PIL import Image  # type: ignore
        im = _open_rgb(src_path)
        w, h = im.size
        if w < 200 or h < 200:
            return "gameplay", detail
        # use gems crop as the common left-grid window (overlaps runes/materials)
        crop = _crop_frac(im, _TALLY_CROPS["gems"])
        if crop is None:
            return "gameplay", detail
        # sample down for speed
        _gw, _gh = 84, 56
        g = crop.resize((_gw, _gh), Image.BILINEAR)
        px = list(g.getdata())
        n = len(px) or 1
        # features
        gold_tan = 0      # rune stones (pale limestone / tan)
        chroma = 0        # saturated gems (ruby/sapphire/emerald…)
        dark_empty = 0
        mid_gear = 0      # mixed shared/personal equipment
        bright = 0
        hue_bkt = [0] * 6  # v948.20 — sextant histogram of the saturated pixels
        # v1258 — PANEL-OPEN geometry: per-column luminance means → count of "dark
        # gridline" columns. The D2R stash grid is a LATTICE (regular dark cells /
        # gridlines), so a real stash tab shows several columns whose mean luminance
        # dips well below the crop's global mean. A Mac-desktop wallpaper photograph
        # (the TCC-failure frames) is a smoothly-lit continuous image with ZERO such
        # dark gridline columns — that geometry, plus the dark-cell fraction below, is
        # the positive "is this actually an open stash panel" evidence the tally
        # branches now require. See _panel_open_from_features / classify_stash_grid.
        col_lum = [0.0] * _gw
        for i, (r, gch, b) in enumerate(px):
            lum = 0.299 * r + 0.587 * gch + 0.114 * b
            col_lum[i % _gw] += lum
            if lum > 115:
                bright += 1
            if lum < 40:
                dark_empty += 1
            # limestone / parchment rune: high lum, low chroma, R≈G≈B or slightly warm
            cr = abs(r - gch) + abs(gch - b) + abs(r - b)
            if lum > 100 and cr < 55 and r > 90:
                gold_tan += 1
            # gem: high chroma, one channel dominates
            mx, mn = max(r, gch, b), min(r, gch, b)
            if (mx - mn) > 70 and mx > 120 and lum > 50:
                chroma += 1
                # sextant hue bucket (standard HSV hue → 6 bins), df>0 guaranteed
                df = mx - mn
                if mx == r:
                    hh = ((gch - b) / df) % 6
                elif mx == gch:
                    hh = ((b - r) / df) + 2
                else:
                    hh = ((r - gch) / df) + 4
                hue_bkt[int(hh) % 6] += 1
            # gear/metal: mid lum, moderate chroma (rings, charms)
            if 55 < lum < 140 and 25 < cr < 90:
                mid_gear += 1
        ft = gold_tan / n
        fc = chroma / n
        fd = dark_empty / n
        fg = mid_gear / n
        fb = bright / n
        # v948.20 — hue diversity: how many hue sextants each hold a meaningful share
        # of the saturated pixels. The Gems tab is a grid of DISTINCT gem colours
        # (ruby-red · emerald-green · sapphire-blue · amethyst-purple · topaz-yellow),
        # so ≥3 sextants light up — a fire-spark / single-colour gameplay frame does not.
        _hmin = max(2, int(0.006 * n))
        hue_div = sum(1 for x in hue_bkt if x >= _hmin)
        # v1258 — lattice geometry: count columns whose mean luminance dips well below
        # the crop's global mean (the dark gridlines / dark cells of an open stash grid).
        col_mean = [c / _gh for c in col_lum]
        _gmean = (sum(col_mean) / _gw) if _gw else 0.0
        # v2239 (#31) — KEEP WHERE THE GRIDLINES ARE, not only how many there were.
        #
        # This list has been computed on every frame since v1258 and immediately collapsed to a
        # count. The indices ARE the lattice x-boundaries, and slot identity — "the same slot across
        # consecutive sessions means PARKED, not merely seen" — needs exactly them. Without this the
        # only other route was a coordinate from the AI read, which means touching the intake, and
        # the intake is LOCKED (Sonnet + crop, do not change). [[d2r-intake-locked]]
        #
        # ⚠ THESE ARE CROP-RELATIVE, and saying so is the whole point of the name. `col_lum` is
        # measured over the stash CROP, not the full frame, so an index here is a column of the crop.
        # Turning it into a frame coordinate needs the crop's own offset, which crops_for_aspect
        # owns. A caller that forgets that puts every item in the wrong slot with total confidence —
        # worse than no slot at all. [[unknown-stays-unknown]]
        dark_col_idx = [i for i, c in enumerate(col_mean) if c < _gmean * 0.70]
        dark_cols = len(dark_col_idx)
        panel_open, not_d2r = _panel_open_from_features(fd, dark_cols)
        detail.update({
            "frac_tan": round(ft, 4), "frac_chroma": round(fc, 4),
            "frac_dark": round(fd, 4), "frac_gear": round(fg, 4),
            "frac_bright": round(fb, 4), "hue_div": hue_div,
            "dark_cols": dark_cols, "panel_open": panel_open,
            # bounded: a full-width list on every frame would bloat every journal row that carries
            # `detail`. 96 is well past any real lattice (his corpus spans 0-71).
            "dark_col_idx": dark_col_idx[:96],
            "dark_col_space": "crop",     # NEVER let a reader assume these are frame coordinates
        })
        # v1258 🛑 NOT-D2R / DESKTOP GUARD — a smoothly-lit photograph (Mac desktop
        # wallpaper captured when the Screen-Recording-TCC grab misses D2R) has
        # essentially NO dark stash cells in this crop (frac_dark≈0.01) yet can carry
        # huge chroma (city lights). Reject it up front so a colourful non-game frame
        # can never fall through to ANY stash-* / vault label. Root cause of the 69
        # wallpaper frames sealed as stash-gems (reels s_1784734976651 / s_1784734921329).
        if not_d2r:
            detail["pick"] = "not-d2r"
            return "gameplay", detail
        # ══ v2326 — NO LATTICE, NO GRID. A STASH IS A GRID BEFORE IT IS A COLOUR ══════════════
        # Every branch below this point decides from colour FRACTIONS, and the fall-through at the
        # end of this function returns "stash". So a frame with no grid in it at all still had to
        # argue its way OUT of being called a stash, and a bright one could not.
        #
        # MEASURED on the corpus, 2026-08-31. reel_s_1788103235974_74668/f_1788103257004.jpg is
        # the Rogue Encampment in daylight — no stash, no inventory, nothing open. It scored
        # frac_gear 0.301-0.350, over the 0.14 gate, and was returned as "stash", because grass,
        # rubble and tents are mid-luminance with moderate chroma and that is what the gear test
        # actually measures. It is NOT a darkness false positive; the scorer's own header warns
        # about dark frames, and this one is bright.
        #
        # dark_cols is the count of columns whose mean luminance dips below the crop mean - the
        # lattice. Across the whole corpus: every REAL panel scores 6 to 40. That frame scores 0.
        # Not "low" - ZERO, which is the one value that can only mean "there is no grid here".
        # So it is refused structurally rather than out-argued numerically, and the bound is the
        # existing _PANEL_MIN_DARKCOLS rather than a fresh number invented to fit one frame.
        # [[feedback-threshold-above-the-ceiling]]
        _lat, _lat_why = lattice_says(dark_cols, fg)
        detail["latticeSays"] = _lat
        detail["latticeWhy"] = _lat_why
        if _lat == "gameplay":
            detail["pick"] = "no-lattice"
            return "gameplay", detail
        # decision tree — shared/personal vaults have COLOURED ring gems (chroma)
        # that must NOT be misread as the Gems tab. Gear density gates first.
        # shared/personal: gear / mixed mid-tones dominate the left panel
        if fg >= 0.14:
            detail["pick"] = "stash"
            return "stash", detail
        # gems tab: high chroma AND low gear (pure jewel grid, not jewelry on gear).
        # v1258 — REQUIRES panel_open (dark-cell lattice): the OLD high-chroma path had
        # no dark/lattice gate, so a vivid wallpaper (fc≈0.74, frac_dark≈0.01, zero
        # gridline columns) tripped it. A genuine packed Gems tab still passes (dark
        # cells behind vivid icons → many dark gridline columns).
        if fc >= 0.11 and fg < 0.10 and fc >= ft and panel_open:
            detail["pick"] = "gems"
            return "stash-gems", detail
        # v948.20 — gems tab, MODERATE chroma (the ROUND-2 miss). A packed gem grid is
        # small vivid icons on mostly-dark cells, so total chroma is only ~0.05-0.10 —
        # it fell in the DEAD ZONE between the high-chroma gems floor (fc>=0.11) above
        # and the materials chroma cap (fc<0.045) below, and dropped to stash-default.
        # ROOT of the s_1784736270319 f_1784736381363 GEMS MISS: fc=0.058 measured.
        # Discriminated from dark-gameplay fire-sparks (fc~0.025) by the fc floor, and
        # from a single-colour glow by hue_div>=3 (multiple distinct gem colours). fd is
        # a closed stash-panel band (splash/combat run much darker). Verified on a
        # 2722-frame sweep of every reel: fires on 67 frames, ALL genuine Gems-tab stills
        # across 16 sessions, zero flips out of materials/runes/gameplay.
        if (0.045 <= fc < 0.11 and hue_div >= 3 and fg < 0.12
                and ft < 0.08 and 0.30 <= fd <= 0.55 and fc >= ft and panel_open):
            detail["pick"] = "gems-multihue"
            return "stash-gems", detail
        # runes: pale limestone stones dominate (tan high, chroma low)
        if ft >= 0.08 and fc < 0.06 and fb >= 0.12 and panel_open:
            detail["pick"] = "runes"
            return "stash-runes", detail
        # materials: dark empties + a little chroma (essences/keys/organs) but NOT
        # gear-dense vault, NOT the vivid gem chroma band, and BOUNDED away from
        # near-pure-black scenes (boot/loading splash, dark gameplay with fire chroma —
        # the false-positive twin the is_boot_screen guard was built for).
        # v948.19 — RECALIBRATED (Grok forensic #5, 2026-07-21 21:05 fast run: 'materials 0
        # classes'). The old band (fd>=0.42, fc 0.04-0.10) was miscalibrated on BOTH sides,
        # found by cross-referencing real materialIntake RECEIPTS (ground truth — the LOCKED
        # intake actually read materials and confirmed totals) against their source frames:
        #   · UNDER-detection: 2 receipted-real materials frames (reel_s_1784561282553_86929/
        #     f_1784561356596.jpg total=184, reel_s_1784561832500_95271/f_1784561874907.jpg
        #     total=210) measured fd=0.3839 fc=0.0308 — BELOW the old fd>=0.42 and fc>=0.04
        #     floors, so the grid vote never fired and only OCR chrome-read could catch it.
        #   · OVER-detection: dark gameplay-with-fire combat frames (e.g.
        #     reel_s_1784647619282_26240/f_1784647734875.jpg, a Catacombs fight, fd=0.7795)
        #     and D2R boot/reconnect splash frames (fd 0.85-0.95, the is_boot_screen class)
        #     landed INSIDE the old band and grid-fingerprinted as materials with zero UI
        #     open — exactly the wrong-cell class this heuristic must never produce.
        # New band verified against a 3200-frame sweep of every historical reel: adds the 2
        # receipted-real frames + 4 more visually-confirmed Materials-tab frames across 4
        # OTHER sessions (true positives), while removing 88 false positives (every one
        # inspected was a boot-splash/lobby cluster at a reel's start) and zero confirmed
        # regressions on gems/personal/shared/runes ground truth. fd is now a closed band
        # (not just a floor) because every confirmed real STASH-panel frame across all tabs
        # sampled fd in [0.31, 0.42] — gameplay/splash scenes run much darker.
        if 0.30 <= fd <= 0.55 and 0.02 <= fc < 0.045 and fg < 0.12 and ft < 0.08 and panel_open:
            detail["pick"] = "materials"
            return "stash-materials", detail
        # softer vault
        # ⚠ v2326 — AND A LATTICE IS EVIDENCE, not merely a precondition. A stash panel with a
        # TOOLTIP OVER IT is diluted exactly where it is being measured: the tip covers the grid
        # with dark, low-chroma text, so the gear fraction falls even though the panel is wide
        # open. reel_s_1788105158696_89699/f_1788105171326.jpg is a SHARED stash, labelled by
        # eye off its own tab strip, that scored fg 0.0795 against this 0.08 gate and was
        # returned as "gameplay" — missed by five ten-thousandths. Its twin two frames later
        # scored 0.093 and was claimed. A gate that two frames of one panel land on either side
        # of is not separating anything.
        #
        # And a hover pass is precisely when the tip is up, so the better he aims MINI the more
        # of the run goes unrecognised. The lattice does not dilute: when the grid is visibly
        # there, a lower gear bar is enough. 0.05 sits above every NEGATIVE in the corpus
        # (0.000, 0.001, 0.029) and below every real panel this rule needs to catch.
        _lattice_says_panel = (_lat == "stash")
        if fg >= 0.08 or (fb >= 0.08 and ft < 0.10) or _lattice_says_panel:
            detail["pick"] = "stash-lattice" if (_lattice_says_panel and fg < 0.08) else "stash"
            return "stash", detail
        if fd >= 0.60 and fb < 0.06:
            detail["pick"] = "gameplay"
            return "gameplay", detail
        detail["pick"] = "stash-default"
        return "stash", detail
    except Exception as e:
        detail["err"] = str(e)[:80]
        return "gameplay", detail


def fuse_tab_signals(
    ocr_tab: str = "",
    grid_label: str = "",
    journal_tab: str = "",
    model_tab: str = "",
    allow_grid_solo: bool = False,
    gem_tab: str = "",
) -> Tuple[str, List[str]]:
    """Fuse eye signals into one tab + list of agreeing sources.

    Priority (eyes, before router):
      1) OCR single-tab (chrome strip) when unambiguous
      2) grid fingerprint tally tab (runes/gems/materials)
      3) model deep-read stashTab
      4) journal sticky
      5) grid said plain stash → personal/shared from journal/model if any

    allow_grid_solo (v948.7 KAI retro): when the film still is already a stash panel
    (grid/chrome fingerprint), grid may promote runes/gems/materials WITHOUT a live
    deep journal sticky — Theatre has the pixels; post-seal funnel must recheck them.
    Live path keeps allow_grid_solo=False so loading screens don't invent tallies.
    """
    sources: List[str] = []
    ocr_tab = (ocr_tab or "").lower().strip()
    journal_tab = (journal_tab or "").lower().strip()
    model_tab = (model_tab or "").lower().strip()
    gem_tab = (gem_tab or "").lower().strip()
    if gem_tab not in _ALL_TABS:
        gem_tab = ""
    gl = (grid_label or "").lower().strip()
    grid_tab = ""
    if gl.startswith("stash-"):
        grid_tab = gl[len("stash-"):]
    elif gl == "stash":
        grid_tab = "stash"

    # stash-open corroboration — grid alone on a dark loading screen invents materials
    stash_open = (
        journal_tab in _ALL_TABS or journal_tab == "stash"
        or model_tab in _ALL_TABS or model_tab == "stash"
        or ocr_tab in _ALL_TABS
        or grid_tab == "stash"
        or str(grid_label or "").startswith("stash")
    )

    # 1 OCR tally wins over vague vault labels (same law as live _resolve_stash_tab)
    if ocr_tab in _TALLY_TABS:
        # ── v1907 — REG-204 CLOSED: A GUESS MAY BEAT A VAGUE LABEL, NEVER A DIFFERENT ANSWER ──
        #
        # This rule's intent is sound: a specific tally word should beat a vague `shared`/`vault`/
        # `stash` label. Its implementation also beat a SPECIFIC AND DIFFERENT tally. Measured when
        # the defect was filed:
        #
        #     fuse_tab_signals(ocr_tab="gems", grid_label="stash-runes")              -> ('gems', ['ocr'])
        #     fuse_tab_signals(ocr_tab="gems", grid_label="stash", model_tab="runes") -> ('gems', ['ocr'])
        #
        # One witness — one that names itself a GUESS in its own docstring — overruled two that
        # disagreed, and reported `sources: ['ocr']` while doing it. That contradicts the
        # multi-witness doctrine head-on.
        #
        # ⚠ WHY IT RETURNS "stash" AND NOT "". Both witnesses agree the panel IS a stash; they
        # disagree only about WHICH tally. Returning "" sends class_from_tab down the else branch
        # and the frame is dropped as `gameplay` — losing a real stash panel is a worse answer than
        # declining to name its tab. "stash" keeps the frame and claims no tally.
        #
        # ⚠ AND THIS CHANGES NOTHING ON HIS CORPUS. The disagreement occurs in ZERO of the 68
        # stash-panel frames — which is exactly why it was filed OPEN rather than fixed blind, and
        # exactly why the guards below drive it synthetically. A branch his data cannot exercise is
        # still a branch. [[gate-blind-to-unexercised-input]] [[d2r-multiwitness-corroboration]]
        # ⚠ v1907.1 — THE JOURNAL STICKY IS NOT A DISAGREEING WITNESS, IT IS A LAGGING ONE.
        # v1907 shipped this set with `journal_tab` in it and that was wrong, caught in the review
        # pass 20 minutes later. `_kai_sticky_tab` says so in its own docstring: "last deep tab with
        # st<=ts+1.5s, HELD until the next deep tab (or 25s)". So for up to 25 seconds after he
        # clicks from Runes to Gems, the sticky still says runes while the OCR correctly reads gems
        # — and treating that as a contradiction would demote an ordinary tab switch to a generic
        # `stash` with no tally. That is a regression on something he does constantly, traded
        # against a contradiction measured at ZERO of 68 frames. REG-204's measurement named grid
        # and model, and it named them for a reason. [[feedback-suspect-the-instrument]]
        _conflicting = {t for t in (grid_tab, model_tab, gem_tab)
                        if t in _TALLY_TABS and t != ocr_tab}
        if _conflicting:
            return "stash", ["tab-conflict"]
        sources.append("ocr")
        # v1912 — CREDIT THE GEM WHEN IT AGREES. It is a witness like the others; leaving it out of
        # the list would under-report the corroboration that actually existed, which is the same
        # class of quiet dishonesty as over-reporting it.
        if gem_tab == ocr_tab:
            sources.append("gem")
        if grid_tab == ocr_tab:
            sources.append("grid")
        if journal_tab == ocr_tab:
            sources.append("journal")
        if model_tab == ocr_tab:
            sources.append("model")
        return ocr_tab, sources

    # 1b THE ACTIVE-TAB GEM (v1912). Placed AFTER the OCR, which reads the actual word, and BEFORE
    # the grid, which is a colour fingerprint that measured 1-of-9 on his own frames. The gem is the
    # game's own selected-state marker: 12 of 12 on the hand-labelled corpus, zero false tabs on the
    # seven non-panels, and 8 named frames across his whole 883-frame hist.
    #
    # ⚠ IT IS NOT PROMOTED ABOVE THE OCR, on purpose. Twelve frames is a small corpus and two of the
    # five tabs (gems, runes) have no example in it at all — their positions are PREDICTED by the
    # measured pitch and unverified. A reader of actual words outranks a geometric prediction until
    # the corpus says otherwise. [[unknown-stays-unknown]]
    if gem_tab:
        sources.append("gem")
        if grid_tab == gem_tab:
            sources.append("grid")
        if journal_tab == gem_tab:
            sources.append("journal")
        if model_tab == gem_tab:
            sources.append("model")
        return gem_tab, sources

    # 2 grid fingerprint tally — when stash panel is open
    if grid_tab in _TALLY_TABS and stash_open:
        # live: need journal/model/ocr corroboration (or journal vault sticky counts as open)
        # KAI retro: allow_grid_solo when grid itself already classified a tally layout
        has_other = bool(journal_tab or model_tab or ocr_tab)
        if has_other or allow_grid_solo:
            sources.append("grid")
            if allow_grid_solo and not has_other:
                sources.append("solo")
            if journal_tab == grid_tab:
                sources.append("journal")
            if model_tab == grid_tab:
                sources.append("model")
            if ocr_tab == grid_tab:
                sources.append("ocr")
            return grid_tab, sources

    # 3 model tally
    if model_tab in _TALLY_TABS:
        sources.append("model")
        if journal_tab == model_tab:
            sources.append("journal")
        return model_tab, sources

    # 4 journal tally sticky
    if journal_tab in _TALLY_TABS:
        sources.append("journal")
        return journal_tab, sources

    # 5 vault tabs
    for cand, src in ((ocr_tab, "ocr"), (model_tab, "model"), (journal_tab, "journal")):
        if cand in _VAULT_TABS:
            sources.append(src)
            if grid_tab in ("stash", "personal", "shared"):
                sources.append("grid")
            return cand, sources

    if grid_tab == "stash" or gl == "stash":
        sources.append("grid")
        return "shared" if not journal_tab else journal_tab, sources  # plain stash panel open

    return "", sources


def class_from_tab(tab: str) -> str:
    tab = (tab or "").lower()
    if tab in _TALLY_TABS:
        return "stash-" + tab
    if tab in _VAULT_TABS or tab == "stash":
        return "stash"
    return ""


#: v3896 (#197 finding 5, REG-3680) - "the caller never asked what screen this is" - never the same as screen_of's own None
#: ("asked: no known screen", the answer for most gameplay frames). MEASURED on v3893's look: a reel frame was decoded up to
#: three times - v3894 handed the closer's screen_of answer in, but a None answer read as "not asked" and decoded the frame
#: again, which is every frame of play. A caller that asked passes its answer, None included; only an unasked frame decodes.
SCREEN_UNASKED = object()


def classify_when_in_play(src_path: str, kind=SCREEN_UNASKED, chain=None, recording=True):
    """v3893 (#187/#185, REG-3550) - the stash-grid reader, joined to the shared screen
    templates and the recorder's window. Pre-game frames (logo, title, character select)
    and frames outside a recording never reach classify_stash_grid. An unlabelled frame
    (a launcher, idle page, or CONNECTING...) reaches it only after the chain has entered,
    or when the caller did not pass a chain (a standalone look at a known panel)."""
    try:
        import d2r_screens as _DS
        if kind is SCREEN_UNASKED:
            kind = _DS.screen_of(src_path)[0] if src_path else None
        if not _DS.readers_may_run(kind, chain=chain, recording=recording):
            return "gameplay", {"method": "screen-type", "screen": kind, "skipped": True}
    except Exception:
        pass
    return classify_stash_grid(src_path)


def analyze_frame(
    path: str,
    ocr_lines: Optional[Sequence[Any]] = None,
    journal_tab: str = "",
    model_tab: str = "",
    ocr_worker_read=None,
    work_dir: Optional[str] = None,
    allow_grid_solo: bool = False,
    chain=None,
    recording: bool = True,
    screen=SCREEN_UNASKED,
) -> Dict[str, Any]:
    """Full eye analysis of one photo (for KAI / live resolve).

    ocr_worker_read: optional callable(path)->dict with 'lines' (warm OCR worker).
    When provided, tab chrome is prepped intake-style and re-OCR'd.
    allow_grid_solo: KAI retro reel pass — grid may name tally tabs without live sticky.
    """
    out: Dict[str, Any] = {
        "path": path,
        "ocrTab": "",
        "gridLabel": "",
        "gridDetail": {},
        "tab": "",
        "cls": "gameplay",
        "sources": [],
        "kaiVer": 3,
    }
    if not path or not os.path.isfile(path):
        return out

    # v948.8 — title/reconnect splash guard, before grid/OCR tab fusion can
    # mistake the burning-logo screen for a near-empty materials grid.
    if is_boot_screen(ocr_lines):
        out["cls"] = "gameplay"
        out["sources"] = ["boot-screen-guard"]
        return out

    # full-frame OCR lines if already available
    ocr_tab = tab_from_ocr_lines(ocr_lines or [])
    # intake-style tab chrome re-OCR
    if ocr_worker_read is not None:
        try:
            wd = work_dir or os.path.dirname(path) or "/tmp"
            chrome = os.path.join(wd, ".stash_eye_tab.jpg")
            if prep_tab_chrome(path, chrome):
                j = ocr_worker_read(chrome) or {}
                t2 = tab_from_ocr_lines(j.get("lines") or [])
                if t2:
                    ocr_tab = t2
                    out["chromeOcr"] = list((j.get("lines") or [])[:8])
        except Exception:
            pass
    out["ocrTab"] = ocr_tab

    gl, gd = classify_when_in_play(path, kind=screen, chain=chain, recording=recording)
    out["gridLabel"] = gl
    out["gridDetail"] = gd

    gem_tab, gem_detail = tab_from_gem(path)
    out["gemTab"] = gem_tab
    out["gemDetail"] = gem_detail
    tab, sources = fuse_tab_signals(
        ocr_tab, gl, journal_tab, model_tab, allow_grid_solo=allow_grid_solo, gem_tab=gem_tab)
    out["tab"] = tab
    out["sources"] = sources
    # class from fused tab; retro solo grid still only yields cls when fuse accepted it
    if tab:
        out["cls"] = class_from_tab(tab) or "gameplay"
    elif gl == "stash" and (journal_tab or model_tab or ocr_tab or allow_grid_solo):
        out["cls"] = "stash"
    else:
        out["cls"] = "gameplay"
    return out
