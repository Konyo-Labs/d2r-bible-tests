"""v1571 — VAULT ACCUMULATOR, the engine. Retro sweep of the sealed reels for what he OWNS.

Konyo: *"the vault manager is synced to also slowly analyze and remember especially between and among
sessions ... it should eventually in retro KAI READERS get a read on it and slowly also feed the vault
manager for throwing out or muling the items read at the time."*

RETRO IS THE PRIORITY LANE. A live read has one look at a panel; the sealed reels have every look he
has ever given one, and a mini stash session (MC-03) is the densest evidence in the whole archive —
he is parked, not fighting, and the panel is held still. So the sweep prefers those reels first.

This module is the CHRONICLE SWEEP pointed at a different target. It does not re-implement it: the
signature function, STILL_MAX_DIFF, MIN_RUN_FRAMES, the still-run grouping, the blank-capture probe
and the within-run dedupe are all imported from `chronicle_retro`. Two copies of a threshold
calibrated on his footage is two things that drift apart, and only one of them would get re-tuned.

THE FIVE LAWS, in his terms:

  1. MERGE-MAX ACROSS SESSIONS. A read NEVER lowers a count and never removes a row. An obstructed
     or half-scrolled stash frame is a NORMAL event, not evidence he threw something away. A later
     session that sees fewer says so in `held` and changes nothing. No ordering of the inputs can
     change the answer — every fold here is a max() or a sorted union.

  2. MULTI-WITNESS CORROBORATION. A name grounds on TWO INDEPENDENT witnesses, and independence is
     counted in SESSIONS: two still-runs inside one reel are the same eye looking twice at the same
     stash, so they are ONE witness. One witness goes to `unsure`, never to `owned`.

  3. THERE IS NO UN-THROW IN DIABLO. Advising him to bin an item is the only irreversible act in the
     whole app, so a throw-out clears a STRICTLY higher bar than a keep on BOTH axes — confidence and
     witnesses — and can never be reached on single-session evidence however confident the reader is.
     Everything in `throwOut` is a SUGGESTION for the Vault manager to show him. Nothing here is
     automatic and nothing here is a write.

  4. HONEST-ABSENT. An unknown count stays None; it never defaults to 1. A run that cannot be
     classified is `held` with a why, not guessed into a lane. A name the reader did not return is
     never invented. A missing sig/reader/classify returns ok:False with a why — never a fabricated
     empty success, which is the one failure shape that looks exactly like "you own nothing".

  5. NEVER WRITE. No filesystem writes, no ledger, no board access, no second apply path.
     `apply_payload()` only SHAPES the proposal so the caller can hand it to the ONE existing apply
     (window.chronicleApply), which owns the date stamp, the merge-max and the undo bar.

Pure by construction: the caller injects the signature fn, the classifier and the reader, so the
tests drive every law from fixtures with zero JPEGs and zero vision calls.
"""

import copy
import glob
import os
import re
import json
import time

try:
    import chronicle_retro as _cr
except ImportError:  # pragma: no cover — running from the repo root rather than from tv/
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import chronicle_retro as _cr


# The production signature function, BORROWED not re-typed (see the module note on drift). The caller
# passes it in — this module never picks a default for itself, because law 4 says a missing sig is an
# answer ("I was not given eyes"), not something to paper over.
DEFAULT_SIG = _cr.jpeg_sig

# Grouping thresholds live in ONE place: chronicle_retro, calibrated on Konyo's own footage.
STILL_MAX_DIFF = _cr.STILL_MAX_DIFF
MIN_RUN_FRAMES = _cr.MIN_RUN_FRAMES

#: v2398 — tooltip rects memoised across CALLS, keyed on (path, size, mtime).
#: ⚠ THE FIRST CUT LANDED INSIDE THE MODULE DOCSTRING. The anchor was the bare string
#: "MIN_RUN_FRAMES", which the docstring mentions at :12 — BEFORE the assignment at :74. So the
#: memo became prose, `_TOOLTIP_MEMO` did not exist on the module, and the proof failed with
#: AttributeError. Anchor on the ASSIGNMENT, never on a name that also appears in prose.
#: [[feedback-comments-vs-code]] [[append-below-the-runner]]
#: WHY IT EXISTS: _vault_scan_cost_inner — the FREE PASS he checks before agreeing to spend —
#: calls this same sweep(), deliberately, because "both halves of a price must name the same
#: thing" (v1834). So v2397's tooltip split ran inside the quote too and took it from a few
#: seconds to over THREE MINUTES. A per-call dict made the quote and the run each pay in full,
#: and the quote is almost always followed by the run.
#: ⚠ Keyed on (size, mtime), NEVER path alone: a reel directory is written to while it is filmed.
_TOOLTIP_MEMO = {}
_TOOLTIP_MEMO_MAX = 20000

# The surfaces that show what he OWNS. Anything else in the footage — town, a fight, the Chronicle,
# character select — is not evidence of ownership and is skipped without paying a read.
OWNERSHIP_SURFACES = ("stash", "inventory", "equipment", "runes", "gems", "materials")

# Which lane a surface's items land in. Runes/gems/materials are STASH TABS in his game, so their
# items are stash items; the reader may override per item when it can actually see the split.
SURFACE_LANE = {
    "stash": "stash", "runes": "stash", "gems": "stash", "materials": "stash",
    "inventory": "inventory", "equipment": "equipment",
}
LANES = ("stash", "inventory", "equipment")

# ── REG-2271 — THE PER-REEL NO-PROGRESS GROUPING DEADLINE (vault lane) ─────────────────────────
# A FROZEN measure phase (a tooltip-OCR tile that never settles) used to sit classified=0/pages=0
# until control_app's 240s river watchdog cleared it — one 240s stall per frozen reel, so his owed
# backlog drained one slow cycle at a time. sweep() now bounds the GROUPING with a NO-PROGRESS window
# via _cr.reel_deadline (the shared helper, one logic across both lanes): the clock resets on every
# COMPLETED tile (a cache-MISS frame, via _tile_progress) AND on every completed cache-HIT tooltip
# look (the beat in _tip_of's cache-hit branch, so a PRIMED tooltip memo whose _tip_of are all cache
# hits still beats per frame), and fires only when NOTHING completes for the budget. sig_of does NOT
# beat; it surfaces the per-frame grouping count UP (on_tile) so the out-of-thread watchdog's sig moves
# on a cache-hit frame too. A reel whose frames/tiles keep completing — however slowly, past 240s — is NEVER skipped
# (his footage is never discarded). Defaults resolved at CALL time; the default MUST stay under the
# watchdog or the guard could never beat it. The one case it cannot catch in-thread is a unit that
# blocks UNINTERRUPTIBLY (a wedged OCR subprocess, or — before REG-2271's complement bounded it — the
# OCR worker's lock); control_app's river watchdog is the out-of-thread backstop for that, and is now
# PHASE-SCOPED so a frozen grouping drains in ~budget rather than 240s.
_REEL_DEADLINE_DEFAULT_S = 20
_HANG_DEADLINE_DEFAULT_S = 240   # mirrors control_app._VAULT_SWEEP_HANG_DEADLINE_S (TV_VAULT_HANG_DEADLINE_S)
assert _REEL_DEADLINE_DEFAULT_S < _HANG_DEADLINE_DEFAULT_S, \
    "REG-2271: the vault per-reel grouping deadline default must stay under the 240s watchdog backstop"


def _reel_deadline_budget(explicit=None):
    """REG-2271 — the vault per-reel NO-PROGRESS grouping deadline, seconds, resolved at CALL time (a
    default read at import would freeze the bar). Default 20: comfortably above the 4.0s single-tile
    OCR cap (tooltip_find reader timeout) so one legit tile that burns its full 4s never trips it,
    while a reel that makes NO tile progress for 20s fires ~12x faster than the 240s river watchdog.
    Because the window RESETS on every completed tile, a healthy or merely-slow reel (36 tiles at up
    to 4s each, grouping a whole reel) NEVER fires — only a genuinely frozen one does. MUST stay below
    the watchdog (TV_VAULT_HANG_DEADLINE_S, default 240) or it would never beat it; clamped so a
    misconfig cannot silently exceed the backstop. The paid read stage is NOT bounded here — that is
    the watchdog's job, so a legitimately long read is never false-killed."""
    if explicit is not None:
        try:
            return float(explicit)
        except Exception:
            return float(_REEL_DEADLINE_DEFAULT_S)
    try:
        v = int(os.environ.get("TV_VAULT_REEL_DEADLINE_S") or _REEL_DEADLINE_DEFAULT_S)
    except Exception:
        v = _REEL_DEADLINE_DEFAULT_S
    try:
        hang = int(os.environ.get("TV_VAULT_HANG_DEADLINE_S") or _HANG_DEADLINE_DEFAULT_S)
    except Exception:
        hang = _HANG_DEADLINE_DEFAULT_S
    if v >= hang:          # the per-reel guard MUST beat the watchdog or it is pointless
        v = max(1, hang - 1)
    return v


# ── v2075 — THE LANES HE HAS ALREADY RULED ON. HIS WORDS: ────────────────────────────────────
# "the whole point of this is for the ai readers to log and register exactly whats currently in my
#  inventory and main character equipment (SHOULD NEVER BE TOLD TO BE MOVED its locked there)"
# and PROJECT_VAULT_MANAGER.md territory 1: "never suggest moving it — it is LOCKED there".
#
# bible.html has carried `_LOCKED_LANES = { equipment: 1, inventory: 1 }` since v1712. The BOARD
# knew; this engine — the thing that actually PRODUCES the suggestions — did not. Measured before
# fixing: a NON-grail item on the equipment lane, flagged junk in 4 recordings at conf 0.99, cleared
# the throw bar with "corroborated across 4 recordings". The only guard on that path was the grail
# roster, so anything he WEARS that is not a named grail item — a crafted amulet, a rare ring, a
# socketed base mid-build — could be offered up for binning. [[the-unjoined-end]]
#
# There is no un-throw in Diablo, so this refuses rather than ranks: no amount of evidence promotes
# a locked lane, exactly as no confidence promotes a grail name (v1903). Evidence is not the
# question here; the LANE is.
LOCKED_LANES = ("equipment", "inventory")

# A surface that already tells us what KIND of thing is on it. Used only as a fallback when the
# reader does not say — never to invent an item, only to type one it did return.
SURFACE_KIND = {"runes": "rune", "gems": "gem", "materials": "material"}
KINDS = ("rune", "gem", "material", "item")

# ── THE TWO BARS (law 3) ────────────────────────────────────────────────────────
# These floors are REASONED, not measured — exactly as honest as the chronicle gate is about its own
# CONF_FLOOR. The keep bar matches the chronicle's (an unsure reader is unsure twice over). The throw
# bar is deliberately stricter on BOTH axes because the two mistakes are not symmetrical: a missed
# keep costs one more look at the stash, a wrong throw costs an item that does not come back.
# v1792 — A RE-LOOK INSIDE ONE RECORDING COUNTS FOR THE KEEP BAR, AND NEVER FOR THE THROW BAR.
#
# Konyo: "maybe though like it can be smarter then this if in the same session but theres a 3-4 min
# gap between timestamped reels then it can be considered another witness?"
#
# The reasoning holds, and better than it first looks. Two candidate runs inside one reel are already
# separated by a SIGNATURE CHANGE — still_runs only starts a new run when the screen moves past
# STILL_MAX_DIFF — so a second run is not the same frozen screen, it is the panel left and returned
# to. Add a multi-minute gap and it is him walking away and coming back, which is a genuinely
# different look at the shelf: different scroll, different overlay, different mouse.
#
# WHAT IT DOES NOT BUY, which is why it stops at the keep bar. The failure this rule guards against
# is a SYSTEMATIC misread — same model, same prompt, same font, same row. Coming back four minutes
# later and reading "Ral" as "Ort" a second time is exactly as likely as the first time. Elapsed time
# buys independence of STATE, never independence of JUDGEMENT. A separate recording does not buy the
# latter either, strictly speaking, but it is the strongest signal available and law 3 spends it on
# the only irreversible act in the app.
#
# So: a re-look can ground `owned`, and can never on its own justify suggesting he bin something.
# UNMEASURED, and it must stay labelled that way — there is no ownership footage in the archive to
# calibrate it against (REG-185), so this is a reasoned bar exactly like the two below it.
REOPEN_GAP_MS = 180_000                   # 3 minutes — his number, taken as given rather than tuned

KEEP_CONF_FLOOR = _cr.CONF_FLOOR          # 0.55 — one number, shared with the chronicle gate
# ── v2070 — THREE READS. HIS RULING, 2026-08-24: "make it 3 reads". ──────────────────────
# PROJECT_VAULT_MANAGER.md has recorded his rule as "verified by 3 reads" since 2026-08-21
# while this constant said 2, so items were entering his vault on less corroboration than he
# had asked for. The doc and the code disagreed and the doc was right.
#
# WHAT THIS COSTS, measured through the real gate before changing it: of his 7 grounded rows,
# 6 have exactly TWO looks and only "Sullied Grand Charm of the Glacier" has three. Nothing
# already in the ledger is lost — merge_vault absorbs existing rows without re-gating them
# (see _rows_of/_absorb), and the console never writes the board. The bar governs what grounds
# NEXT, not what he already owns.
#
# ⚠ AND THIS COUNTS LOOKS, NOT RECORDINGS. The default witness_field here is "witness" — a
# re-look key opened by REOPEN_GAP_MS (3 minutes) — so three reads can come from ONE recording
# in which the shelf was examined three times, minutes apart. Only the THROW bar passes
# witness_field="session" and demands independent recordings. I told him "film it twice"
# before reading this and it was wrong.
KEEP_MIN_WITNESSES = 2                    # two DIFFERENT looks agreeing — HIS RULING, 2026-09-07
# ══ 2026-09-07 — ONE NUMBER FOR "CORROBORATED", WHICH IS HIS RULING AND NOT A LOOSENING ═══════
#
# Konyo: *"hmm maybe a unified logic for this... lets keep it maybe 2 witnsses"*, and then, on the
# throw bar specifically: *"make it two also.. its fine.. i will review what i throw regardless..
# as long as it in that bin"*, *"i will decide if to throw it out or not to"*.
#
# WHAT MOVED: KEEP 3 -> 2 and THROWOUT 4 -> 2. `chronicle_retro.MIN_WITNESSES` was already 2, so
# the three lanes now agree on what "corroborated" means. Two bars for one question was an
# accident of authorship, not a decision.
#
# ⚠ WHAT DID NOT MOVE, AND IT IS WHY THE THROW LANE IS STILL THE STRICTER OF THE TWO:
#     KEEP_CONF_FLOOR      0.55
#     THROWOUT_CONF_FLOOR  0.85   <- unchanged, still strictly above
# Equal witnesses do not make throwing easier than keeping: the throw lane still demands that the
# reader was far more certain of what it saw. The old law's spirit ("throw must never quietly
# become the easier of the two") now rests on confidence rather than on witness count.
#
# ⚠⚠ AND THE SAFETY ARGUMENT IS NOT A PROMISE, IT IS A MEASUREMENT. Two things were verified in
# CODE before this change, not taken from a docstring or from the UI copy:
#   1. THE THROW LANE HAS NO APPLY PATH. `control_app.vault_apply` re-gates and walks
#      `for _which in ("owned", "unsure")` — `throwOut` is carried in the display payload and is
#      never consumed by the write. The screen's own words ("suggestions only ... there is no
#      un-throw in Diablo, so this lane has no button") are true of the code.
#   2. THE PRUNE IS DISARMED. `control_app._PRUNE_SAFE_TO_RUN` is False and gates the write half
#      at :17255; its note says it "remains his". So a lower keep bar frees no footage today.
# ⚠ THE FUTURE COST, STATED PLAINLY: `reel_retention` holds a reel with the reason
#   `rows-not-banked`. When he DOES arm the prune, a 2-witness keep bar means more rows count as
#   banked and therefore more footage becomes eligible. That is a real consequence, deferred
#   behind a flag only he sets, and it is his call. [[unknown-stays-unknown]]
#
# MEASURED CONSEQUENCE ON HIS OWN STORE, the reason he asked: 6 of the 7 rows in his stored
# vault_accum OWNED lane were banked under a 2-witness bar and could not clear 3, so the panel
# was calling them "corroborated" on a bar they would fail and "register 7" would have been
# refused outright by the re-gate. At 2 they are coherent again.

THROWOUT_CONF_FLOOR = 0.85                # strictly above KEEP_CONF_FLOOR
THROWOUT_MIN_WITNESSES = 2                # HIS RULING, 2026-09-07. See the note below: this is
                                          # no longer strictly above the keep bar on WITNESSES,
                                          # and it remains strictly above it on CONFIDENCE.


# ── reel selection ──────────────────────────────────────────────────────────────

def _declared_surface(idx):
    """The ownership surface HE declared for this reel, or None.

    v1603 — only an OWNERSHIP surface counts. `chronicle-uniques` / `chronicle-sets` are real mini
    focuses but they are the chronicle sweep's business, not this one, so they return None here and
    the run falls through to the classifier exactly as before.
    """
    idx = idx if isinstance(idx, dict) else {}
    f = str(idx.get("focus") or "").strip().lower()
    # v1783 — A DEFAULT IS NOT A DECLARATION. Trusting this stamp replaces a paid classify for
    # EVERY run in the reel, so an untouched default ("stash", which the console pre-selects) would
    # label town, a fight and a Chronicle page as a stash panel without one of them being looked at
    # — and any name read off them lands in the stash lane, where merge-max makes it permanent.
    # Reels stamped before v1783 carry no focusChosen key; those keep the old behaviour rather than
    # having their history reinterpreted, and only NEW reels are held to the stricter rule.
    if "focusChosen" in idx and not idx.get("focusChosen"):
        return None
    return f if f in OWNERSHIP_SURFACES else None


def is_mini_reel(idx, reel_dir=""):
    """Was this reel a MINI stash capture (MC-03)? Preferred first — densest evidence per read.

    Several markers are accepted on purpose: the journal field is MC-03's to name, and a sweep that
    silently mis-detects would just quietly read the reels in a worse order. Being wrong here costs
    ordering, never correctness — the laws below do not depend on it.
    """
    idx = idx if isinstance(idx, dict) else {}
    if idx.get("mini") is True:
        return True
    if str(idx.get("mode") or "").lower() in ("mini", "mini_stash", "ministash"):
        return True
    if str(idx.get("kind") or "").lower() in ("mini", "mini_stash"):
        return True
    if str(idx.get("focus") or "").lower() in OWNERSHIP_SURFACES:
        return True
    return "_mini" in os.path.basename(reel_dir or "").lower()


def _load_index(reel_dir):
    try:
        with open(os.path.join(reel_dir, "index.json"), encoding="utf-8") as fh:
            idx = json.load(fh)
        return idx if isinstance(idx, dict) else None
    except Exception:
        return None


def _frame_rows(frames):
    """A reel index's frame list, normalised to the {"f","ts"} rows the grouping expects.

    Real sealed reels always carry dicts, but an older or hand-built index can carry bare filenames,
    and chronicle_retro.still_runs() calls .get() on each row — a bare string raises AttributeError
    and takes the whole sweep down with it. Normalising HERE keeps that shape out of the borrowed
    grouping without touching it: a sweep that dies on one odd reel reads as "the vault is broken".
    """
    out = []
    for fr in (frames or []):
        if isinstance(fr, dict):
            out.append(fr)
        elif isinstance(fr, str) and fr.strip():
            out.append({"f": fr.strip(), "ts": 0})
    return out


def panel_density(reel_dir, panel_gate, sample_every=8, cap=24):
    """FREE: what fraction of sampled frames in this reel actually show an ownership panel.

    `panel_gate(path)` is control_app.stash_screen_open (or its cached twin) — a crop and an OCR,
    no model call, which is why the sweep can afford to ask it about every reel before paying to
    read any of them. Returns 0.0 when the reel is unreadable rather than raising: a reel we cannot
    measure must sort LAST, never first.
    """
    try:
        frames = sorted(glob.glob(os.path.join(reel_dir, "*.jpg")))
    except Exception:
        return 0.0
    probe = frames[::max(1, int(sample_every))][:max(1, int(cap))]
    if not probe:
        return 0.0
    hits = 0
    for f in probe:
        try:
            if panel_gate(f) is not None:
                hits += 1
        except Exception:
            continue
    return hits / float(len(probe))


def order_reels(hist_dirs, panel_gate=None):
    """Reels that actually SHOW a stash first; mini-ness only breaks ties.

    ── v2023 — "MINI-FIRST" WAS SORTING BY THE WRONG THING ─────────────────────────────────────
    Konyo, on being told the first real sweep read nothing: *"but didnt we say it needs to know like
    we have a identifed and classifer for templates when im in the vault/stashing it should know
    that when to grab the reels after that specific moment and until it closes"*. He is right, and
    the ordering was the reason it did not.

    MEASURED, 2026-08-23, the first vault sweep ever run. It took the 4 mini-first reels, examined
    234 frames, and read ZERO pages. Sampling those same four with the panel gate:

        reel_s_1787307553811_9452     25 frames   0 of  7 sampled show a panel
        reel_s_1787307317840_8033    148 frames   0 of 37 sampled show a panel
        reel_s_1787251265965_42930    22 frames   0 of  6 sampled show a panel
        reel_s_1787181101377_20439    39 frames   0 of 10 sampled show a panel
        ──────────────────────────────────────────────────────────────────────
        reel_s_1784984019250_95276   153 frames  23 of 39 sampled show a panel   <- NOT SWEPT

    Zero out of sixty against fifty-nine percent. The reader was never the problem; it was pointed
    at footage of him walking around. `is_mini_reel` asks whether he PRESSED MINI, which is a
    statement of intent and not evidence about the film — and the sweep had no way to prefer, or be
    pointed at, a reel that demonstrably contains what it is looking for.

    THE GATE COSTS NOTHING, WHICH IS THE WHOLE POINT. control_app already says so in its own words
    about the quote path: "The gate costs no model call — a crop and an OCR." So the sweep can price
    every reel by measured panel density before spending a single read on any of them.

    STILL A STABLE SORT. Reels of equal density keep the caller's order, so law 1 holds: this only
    chooses what we PAY to read first, never what the fold concludes. And with no gate supplied the
    behaviour is exactly the old one, so nothing that calls this without a gate changes.
    """
    dirs = [d for d in (hist_dirs or []) if d]
    if panel_gate is None:
        return sorted(dirs, key=lambda d: 0 if is_mini_reel(_load_index(d), d) else 1)
    dens = {}
    for d in dirs:
        dens[d] = panel_density(d, panel_gate)
    # HIGHEST density first; mini-ness only breaks ties; then the caller's order.
    return sorted(dirs, key=lambda d: (-dens.get(d, 0.0),
                                       0 if is_mini_reel(_load_index(d), d) else 1))


# ── normalisation (law 4: honest-absent) ────────────────────────────────────────

def _surface_of(verdict):
    """A classifier's answer → an ownership surface, or None. Accepts a bare string or a dict."""
    if isinstance(verdict, dict):
        verdict = verdict.get("surface") or verdict.get("scene") or verdict.get("kind")
    s = str(verdict or "").strip().lower()
    return s if s in OWNERSHIP_SURFACES else None


def _count_of(v):
    """A count, or None. None is NOT 1 and never becomes 1 (law 4)."""
    if v is None or isinstance(v, bool):
        return None
    try:
        n = int(v)
    except Exception:
        return None
    return n if 0 <= n <= 99999 else None


def _conf_of(v, fallback=0.0):
    # True is an int, and float(True) is 1.0, so a flag would clear the confidence floor.
    # A numeric string is the same class of lie: the sighting did not carry a measured number.
    # NaN survives float() and then fails every comparison, which used to take the PASS branch.
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return fallback
    try:
        x = float(v)
    except Exception:
        return fallback
    if x != x or abs(x) == float("inf"):
        return fallback
    return max(0.0, min(1.0, x))


def _max_count(a, b):
    """MERGE-MAX on one count (law 1). Unknown loses to any number; unknown+unknown stays unknown.

    Commutative and idempotent by construction — that is what makes the fold order-independent.
    """
    if a is None:
        return b
    if b is None:
        return a
    return a if a >= b else b


def _xy_of(v):
    """v3554 (#146 3b) — the reader's point for one item: [x, y] of non-negative numbers, or None. A malformed point is
    None (no point), never a guessed one."""
    try:
        if isinstance(v, (list, tuple)) and len(v) == 2:
            x, y = float(v[0]), float(v[1])
            if x >= 0 and y >= 0 and x == x and y == y:
                return [x, y]
    except (TypeError, ValueError):
        pass
    return None


def _box_of(v):
    """REG-2915 (#158.7) - the reader's tooltip box for one item: [left, top, right, bottom] of non-negative numbers with
    right > left and bottom > top, or None. A malformed box is None (no box), never a guessed one."""
    try:
        if isinstance(v, (list, tuple)) and len(v) == 4:
            b = [float(x) for x in v]
            if all(x == x and x >= 0 for x in b) and b[2] > b[0] and b[3] > b[1]:
                return b
    except (TypeError, ValueError):
        pass
    return None


def place_on_grid(xy, xy_map, lane):
    """v3554 (#146 3b) — WHERE a vault look saw the item. -> {"point": [x, y] | None, "cell": str | None, "why": str | None}

    The reader points in the picture IT saw; `xy_map` (tv_diablo._vault_xy_map) says how that picture sits in the
    frame. The point is scaled to the frame and placed by slot_identity - a stash/inventory grid's cell
    ("stash:c3r4"), or the doll slot it lies in ("equipped:torso"). Every refusal is said; a cell is never guessed,
    because a wrong cell files the item where he will not look. [[unknown-stays-unknown]]"""
    if xy is None:
        return {"point": None, "cell": None, "why": "the reader gave no point for it"}
    if not isinstance(xy_map, dict):
        return {"point": None, "cell": None, "why": "the size of the picture the reader pointed in is unknown"}
    try:
        sw, sh = [float(v) for v in xy_map["space"]]
        ox, oy = [float(v) for v in xy_map["origin"]]
        ew, eh = [float(v) for v in xy_map["extent"]]
        fw, fh = [float(v) for v in xy_map["frame"]]
    except (KeyError, TypeError, ValueError):
        return {"point": None, "cell": None, "why": "the picture's measurements are unreadable"}
    if sw <= 0 or sh <= 0 or ew <= 0 or eh <= 0:
        return {"point": None, "cell": None, "why": "the picture's measurements are empty"}
    if not (xy[0] <= sw and xy[1] <= sh):
        return {"point": None, "cell": None,
                "why": "the point (%g,%g) lies outside the %gx%g picture the reader was shown" % (xy[0], xy[1], sw, sh)}
    pt = [round(ox + xy[0] * ew / sw, 1), round(oy + xy[1] * eh / sh, 1)]
    try:
        import slot_identity as _si
    except Exception as e:
        return {"point": pt, "cell": None, "why": "the grid geometry would not load (%s)" % type(e).__name__}
    if lane == "equipment":
        slot, why = _si.worn_slot_of(pt, fw, fh)
        return {"point": pt, "cell": ("equipped:%s" % slot) if slot else None, "why": None if slot else why}
    cont = {"stash": "stash", "inventory": "inventory"}.get(lane)
    if cont is None:
        return {"point": pt, "cell": None, "why": "no grid is measured for the %s lane" % lane}
    box, why = _si.panel_box_for(fw, fh, container=cont)
    if not box:
        return {"point": pt, "cell": None, "why": why}
    cell, why = _si.cell_of(pt, box, cont)
    if not cell:
        return {"point": pt, "cell": None, "why": why}
    return {"point": pt, "cell": _si.slot_key(cont, cell[0], cell[1]), "why": None}


def lane_by_point(lane, xy, xy_map):
    """REG-1911 - where the item WAS, over what the reader CALLED it, in the safe direction only. -> (lane, placement)

    A Death Mask tooltip sat over his INVENTORY with the stash tab empty, and the reader called it lane 'stash' - so a
    second look would have grounded an inventory item as vault-owned (the testing-phase pre-run, F7). When the reader
    says stash and its point is on no stash cell but IS on a measured inventory cell, the sighting is filed where it
    was seen: inventory, which is held and never registered to a locker. The reverse - a point on the stash grid under
    an 'inventory' label - is NOT flipped, because that direction would ground a vault item on a pointing error."""
    pl = place_on_grid(xy, xy_map, lane)
    if lane == "stash" and pl.get("cell") is None and pl.get("point") is not None:
        alt = place_on_grid(xy, xy_map, "inventory")
        if alt.get("cell"):
            return "inventory", dict(alt, why="the reader said stash; its point is on the inventory grid (%s), so it "
                                              "is filed as an inventory sighting" % alt["cell"])
    return lane, pl


def normalize_item(raw, surface, lane_default, page_conf):
    """One reader row → the canonical owned-row seed, or None if it is not an item at all.

    Never invents: no name, no row. Never types what it cannot type: an unknown kind falls back to
    the SURFACE's kind (a rune page holds runes) and only then to the generic 'item'.
    """
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()[:80]
    if not name:
        return None
    lane = str(raw.get("lane") or "").strip().lower()
    if lane not in LANES:
        lane = lane_default
    kind = str(raw.get("kind") or "").strip().lower()
    if kind not in KINDS:
        kind = SURFACE_KIND.get(surface, "item")
    return {
        "name": name,
        "lane": lane,
        "kind": kind,
        "count": _count_of(raw.get("count")),
        # v3368 (#60) — THE THREE FACTS THAT DECIDE A BASE ITEM'S VALUE. Until now the reader was
        # told to look at sockets, used them to judge junk, and the fact was discarded: 44 rows on
        # his disk, ZERO carrying sockets/eth/quality. Prices are downstream of this — an averaged
        # price cannot be applied to a row that does not say whether the item is socketed.
        # ⚠ NULL IS NOT ZERO AT ANY OF THE THREE. 0 sockets is a MEASUREMENT ("it has none"); null
        # is "the reader could not tell". eth False is "visibly not ethereal"; None is "unknown".
        # [[unknown-stays-unknown]] [[heart-first]] §6
        "sockets": _sockets_of(raw.get("sockets")),
        "eth": (True if raw.get("eth") is True
                else (False if raw.get("eth") is False else None)),
        "quality": _quality_of(raw.get("quality")),
        # v3554 (#146 3b) — where the reader saw it, in ITS picture; place_on_grid turns it into a frame point and a cell
        "xy": _xy_of(raw.get("xy")),
        # REG-2915 (#158.7) - the box of the tooltip this name was read from, in the reader's picture; the crop is cut from it
        "tip": _box_of(raw.get("tip")),
        # ⚠⚠ v3368 — WHICH PROMPT PRODUCED THIS ROW. Without it a null socket count from the OLD
        # prompt (which never asked) is indistinguishable from a null the NEW one genuinely could
        # not read, and the heart row that watches this cannot name its own population.
        # MEASURED before adding it: `promptVer` appears 0 times in vault_seen.json, while the
        # heart row keyed on it — a reader with no writer, which would have sat UNKNOWN forever
        # while the version note claimed "a row records which prompt produced it".
        # [[the-unjoined-end]] [[stale-reading]]
        "promptVer": _prompt_ver(),
        "conf": _conf_of(raw.get("conf"), page_conf),
        "throwOut": raw.get("throwOut") is True,
        # v2011 — SAY WHEN THIS IS A DEFAULT. The reader was never asked for throwWhy in the JSON
        # shape (fixed in tv_diablo the same version), so this fallback fired on EVERY suggestion
        # and read like the reader's own words. A substituted default must be labelled as one, or
        # it is a sentence with no author. [[unknown-stays-unknown]]
        "throwWhy": (str(raw.get("throwWhy") or "").strip()[:160]
                     or "no reason given by the reader — flagged as junk on the throwOut flag alone"),
    }


# ── THE GATE (laws 2 and 3) ─────────────────────────────────────────────────────

#: What a look says when it was taken and did NOT see the item. A look carrying one of these (or
#: hit False) is a real look that missed — never a success, however confident or framed it is.
MISS_SAWS = frozenset(("empty", "other", "miss"))


def look_saw_it(e, conf_floor=None):
    """Did this ONE look see the item? -> bool. The one definition — every counter calls it.

    ══ 2026-09-28 (Ledger fix round 2, finding D) — "A LOOK THAT SAW IT" WAS DEFINED TWICE ════════
    gate()._qualifies read `bool(frame) and _conf_of(conf) >= floor`: it refused a bool or string
    conf but ignored `saw`/`hit`. vault_evidence._is_success read `float(conf)`: it ACCEPTED True
    (1.0) and "0.9", refused saw in (empty, other, miss) or hit False, and stripped the frame. The
    keep bar and the tier table could therefore disagree about the same look. Now both call this,
    with the STRICTER half of each where they differed:
      · a dict, whose `saw` is not a miss word and whose `hit` is not False (from _is_success);
      · its OWN frame — a non-blank one (from _is_success: "  " is not a frame to open);
      · its OWN conf, a real number — never a bool, a string, NaN or inf (from gate: a flag or a
        numeric string is not a measured confidence) — at or above the floor, clamped to [0, 1].
    MEASURED before changing it, on a scratch copy of his vault_accum.json (hash unchanged): all
    150 looks carry a float conf, none carries saw/hit, and the 2 frameless looks (the Bone Break
    and Magefist priors) were refused by both copies alike. The two old definitions disagreed on 0
    of 150 looks, and no item's count, tier, retro flag or plan row moved.
    `conf_floor` None is KEEP_CONF_FLOOR, read at call time. [[copy-drift]]
    """
    if conf_floor is None:
        conf_floor = KEEP_CONF_FLOOR
    if not isinstance(e, dict):
        return False
    if str(e.get("saw") or "").strip().lower() in MISS_SAWS or e.get("hit") is False:
        return False
    if not str(e.get("frame") or "").strip():
        return False
    c = e.get("conf")
    if isinstance(c, bool) or not isinstance(c, (int, float)):
        return False
    if c != c or abs(c) == float("inf"):
        return False
    return max(0.0, min(1.0, float(c))) >= conf_floor


def gate(evidence, conf_floor=KEEP_CONF_FLOOR, min_witnesses=KEEP_MIN_WITNESSES,
         witness_field="witness", witness_noun="look"):
    """Does this pile of sightings ground? Returns a verdict that EXPLAINS itself either way.

    evidence: [{"session","frame","lane","conf",...}, ...]
    -> {"pass", "why", "sessions": [sid...], "witnesses": n, "sightings": n, "bestConf": float}

    WITNESS IDENTITY (law 2): witnesses are DISTINCT SESSION IDS. Two still-runs inside one reel are
    one eye looking at the same stash twice — repetition, not corroboration.

    Law 3 is enforced here and not by the caller: whatever floors are passed in, a single-session
    pile can never satisfy a throw-out bar, because THROWOUT_MIN_WITNESSES is >1 and the witness
    count is a count of sessions. The `why` is what the Vault manager shows him when it declines.
    """
    ev = [e for e in (evidence or []) if isinstance(e, dict)]
    # v1792 — the KEEP bar counts distinct LOOKS (separate recordings, or one recording re-opened
    # after REOPEN_GAP_MS); the THROW bar is called with witness_field="session" so it can only ever
    # count distinct recordings. Falls back to the session id for evidence written before v1792.
    #
    # ══ #246 W3 — A LOOK IS A WITNESS ONLY IF IT CARRIES ITS OWN FRAME AND ITS OWN CONF ≥ THE FLOOR ══
    # This counted a session from EVERY row of the pile and tested the floor on the pile's BEST row. So
    # Magefist's pile — [{conf 0.0, frame null}, {conf 0.85, frame f_…}] — passed as "corroborated
    # across 2 looks at conf 0.85": one real look, plus a frameless look the reader was not sure of at
    # all, counted as its second witness. Its confidence lower bound was 0.095. His rule is two looks
    # AGREEING; a look nobody can open and the reader itself doubted is not a look that agreed.
    # Now each look qualifies ON ITS OWN (a frame to open, conf ≥ the floor) and only qualifying looks
    # are counted. `looksSeen` keeps the raw count BESIDE it, never instead of it. Nothing is destroyed:
    # a refused pile is banked as `unsure` and one more real look grounds it.
    # The raw look count rides beside the qualifying one so the SHIPPED verdict can carry a confidence
    # bound (apply_payload stamps it); this function reads no score and decides on his 2-look ruling
    # (2026-09-07) alone. Moving the bar to a 0.43 confidence floor (about three looks) is his call.
    # 2026-09-28 (Ledger fix round 2, finding D): the per-look test is look_saw_it — the ONE
    # definition vault_evidence._is_success and the shadow scorer below call too. Never re-typed.
    qual = [e for e in ev if look_saw_it(e, conf_floor)]
    # 2026-09-28 (Ledger fix, finding 7) — the id goes through look_id(), the ONE spelling of a look
    # this module and vault_evidence both count with, so "reel_sA#0" and "sA#0" are one look.
    sessions = _fold_bare_sessions({look_id(e, witness_field) for e in qual})
    seen_all = _fold_bare_sessions({look_id(e, witness_field) for e in ev})
    best = max([_conf_of(e.get("conf")) for e in ev] or [0.0])
    base = {"sessions": sessions, "witnesses": len(sessions), "sightings": len(ev), "bestConf": best,
            "looksSeen": len(seen_all), "allLooks": seen_all,
            "floor": conf_floor, "minWitnesses": min_witnesses}
    if not ev:
        return dict(base, **{"pass": False, "why": "no evidence at all"})
    if best < conf_floor:
        return dict(base, **{"pass": False,
                             "why": "the reader itself was unsure (%.2f < %.2f) — unsure twice is "
                                    "still unsure" % (best, conf_floor)})
    if len(sessions) < min_witnesses:
        _nq = len(seen_all) - len(sessions)
        return dict(base, **{"pass": False,
                             "why": "only %d independent %s%s (%s) — needs %d; two runs of the same "
                                    "unbroken screen are ONE witness%s"
                                    % (len(sessions), witness_noun,
                                       "" if len(sessions) == 1 else "s",
                                       ", ".join(sessions) or "none", min_witnesses,
                                       ("; %d more %s%s did not count — a %s counts only with its own "
                                        "frame and its own conf ≥ %.2f"
                                        % (_nq, witness_noun, "" if _nq == 1 else "s", witness_noun,
                                           conf_floor)) if _nq > 0 else "")})
    return dict(base, **{"pass": True,
                         "why": "corroborated across %d %ss (%s) at conf %.2f"
                                % (len(sessions), witness_noun, ", ".join(sessions), best)})



# ── WILSON, ON THE ONE GATE THAT OWNS AN IRREVERSIBLE ACT ────────────────────────────────────────
# Konyo, 2026-08-28: spread the Wilson + confluence logic "anywhere needed... especially with data
# coming through consecutively".
#
# THIS IS THE SHARPEST PLACE IT APPLIES IN THE WHOLE TREE, and it was the one gate without it. The
# two bars above already reason that "a wrong throw costs an item that does not come back" — and
# then decide on a FLAT COUNT, where 4 looks and 40 looks score exactly the same. Wilson is the
# statistic that can tell those apart, and the throw bar is where being unable to is expensive.
#
# ⚠ THE DESIGN DECISION THAT MATTERS, and getting it wrong would silently repeal law 2: Wilson runs
# on the FOLDED WITNESS LIST, never on raw sightings. Four re-reads of one frozen frame are one eye
# looking twice; scored as n=4 they would produce a confident bound from a single look — precisely
# the systematic-misread failure the throw bar exists to prevent. So n = distinct witnesses AFTER
# _fold_bare_sessions, which is the same denominator the live gate uses.
VAULT_WITNESS_TIER = {
    "multi-session": 1.00,   # different recordings — the strongest independence available (law 3)
    "multi-lane":    0.75,   # a different reader lane looked and agreed
    "multi-surface": 0.50,   # seen on a second ownership surface
    "re-look":       0.25,   # same recording, reopened after REOPEN_GAP_MS — state, not judgement
}
# ⚠ THE FLOORS ARE REASONED FROM THE TIER ARITHMETIC, NOT MEASURED — and saying so is the point.
# My first pass wrote "tuned to reproduce today's verdict" and that was FALSE: no live evidence pile
# exists on this disk to tune against, and the synthetic fixture I checked against earns exactly one
# tag, so the throw shadow could only ever say no. A floor above what the data can reach is an ABSENT
# gate wearing a tuned face. [[feedback-threshold-above-the-ceiling]]
#
# So they are derived instead, and the derivation is checkable: the tier table tops out at 2.50.
#   keep  1.00 = ONE kind of independence          (wilson 0.43 = the 3-witness bar it mirrors)
#   throw 1.75 = TWO kinds, and multi-session must be one of them by law 3
#                (wilson 0.51 = the 4-witness bar). Stricter on BOTH axes, because the mistakes are
#                not symmetrical: a missed keep costs another look, a wrong throw costs the item.
# floors_are_reachable() asserts they sit under the ceiling, so this can never silently go inert.
KEEP_WILSON_FLOOR = 0.43
KEEP_CONFLUENCE_FLOOR = 1.00
THROWOUT_WILSON_FLOOR = 0.51
THROWOUT_CONFLUENCE_FLOOR = 1.75


def _vault_tags(ev, sessions):
    """Which KINDS of independence this pile actually has. -> [tag]"""
    tags = []
    if len({str(s).split("#")[0] for s in sessions}) > 1:
        tags.append("multi-session")
    if len({str(e.get("lane") or "") for e in ev if e.get("lane")}) > 1:
        tags.append("multi-lane")
    if len({str(e.get("surface") or e.get("scene") or "") for e in ev
            if (e.get("surface") or e.get("scene"))}) > 1:
        tags.append("multi-surface")
    if len(sessions) > len({str(s).split("#")[0] for s in sessions}):
        tags.append("re-look")
    return tags


def gate_shadow(evidence, bar="keep"):
    """What Wilson WOULD say about this pile, beside what the live gate DID say. -> dict

    ⚠ DECIDES NOTHING. No caller may branch on it, and the live `gate()` above does not call it.
    Task #34 measured the chronicle's shadow agreeing with its live gate 23/23 and that is exactly
    why it stayed shadow: a rule that has never disagreed has never been tested against the live
    one. The disagreements are the product. [[feedback-blind-fixture-green-gate]]
    """
    import confidence as _cf
    if bar == "throwout":
        cfl, mw, wf, cff = (THROWOUT_CONF_FLOOR, THROWOUT_MIN_WITNESSES,
                            THROWOUT_WILSON_FLOOR, THROWOUT_CONFLUENCE_FLOOR)
        field, noun = "session", "session"
    else:
        cfl, mw, wf, cff = (KEEP_CONF_FLOOR, KEEP_MIN_WITNESSES,
                            KEEP_WILSON_FLOOR, KEEP_CONFLUENCE_FLOOR)
        field, noun = "witness", "look"
    live = gate(evidence, cfl, mw, witness_field=field, witness_noun=noun)
    ev = [e for e in (evidence or []) if isinstance(e, dict)]
    # #246 W3 — n is EVERY distinct look the pile holds (the live gate now counts only qualifying ones
    # as `sessions`, and handing the shadow that list would make its denominator the numerator).
    sessions = live.get("allLooks") or live.get("sessions") or []
    # k = witnesses with a look that SAW it; n = every distinct witness. A look with no frame to open
    # clears nothing — the same per-look rule the live gate applies, because it is the same
    # function: look_saw_it (Ledger fix round 2, finding D — this was a third copy of that rule).
    saw_by = set()
    for e in ev:
        w = look_id(e, field)       # the spelling live gate() keyed `sessions` with, or k misses it
        if w and look_saw_it(e, cfl):
            saw_by.add(w)
    n = len(sessions)
    k = sum(1 for w in sessions if str(w) in saw_by)
    return _cf.shadow(k, n, _vault_tags(ev, sessions), VAULT_WITNESS_TIER, wf, cff,
                      bool(live.get("pass")), lane="vault:%s" % bar,
                      subject=str(ev[0].get("name") or "") if ev else "")



def floors_are_reachable():
    """PROVE both shadow bars can actually be cleared. -> (ok, why)

    The failure this exists to catch is SILENT: a confluence floor above what the tier table can sum
    to makes the shadow answer no forever, and "never passed" is indistinguishable from "never
    should have". Asserted rather than trusted, because I got it wrong on the first pass.
    """
    ceiling = round(sum(VAULT_WITNESS_TIER.values()), 3)
    for name, floor in (("keep", KEEP_CONFLUENCE_FLOOR), ("throwout", THROWOUT_CONFLUENCE_FLOOR)):
        if floor > ceiling:
            return False, ("the %s confluence floor %.2f is above the %.2f the tier table can sum "
                           "to — that bar can never be cleared" % (name, floor, ceiling))
    # And reachable by a REALISTIC pile, not just arithmetically: the throw bar demands two kinds,
    # and multi-session + multi-lane is the cheapest real pair a sweep can produce.
    real = round(VAULT_WITNESS_TIER["multi-session"] + VAULT_WITNESS_TIER["multi-lane"], 3)
    if THROWOUT_CONFLUENCE_FLOOR > real:
        return False, ("the throw floor %.2f needs more than multi-session + multi-lane (%.2f), so "
                       "it demands evidence a sweep does not routinely produce"
                       % (THROWOUT_CONFLUENCE_FLOOR, real))
    return True, None



def shadow_scores(piles, bar="keep"):
    """Score a whole sweep under BOTH rules. WRITES NOTHING. -> {scored, disagreements, names}

    ⚠ WHY THIS EXISTS AND WHY IT IS SEPARATE FROM THE PERSISTING. gate_shadow() answers about one
    pile, and one pile answers nothing: a rule that agrees with the live gate on today's handful of
    items is a statement about how little evidence the tree holds, not about the two rules. Konyo's
    reason for asking for Wilson at all was "especially with data coming through consecutively" —
    which only pays off if the comparison ACCUMULATES.

    Same shape as chronicle_retro.shadow_scores so shadow_ledger.observe can fold either. This
    module scores; the caller persists. (vault_retro is not under the chronicle's read-only law, but
    keeping the split identical means one ledger and one set of arithmetic rather than two.)
    """
    scored, dis, seen = 0, [], []
    for name, ev in sorted((piles or {}).items()):
        if not isinstance(ev, list) or not ev:
            continue
        try:
            sh = gate_shadow(ev, bar)
        except Exception:
            continue
        scored += 1
        seen.append(name)
        if sh.get("agrees") is False:
            dis.append({"name": name, "lane": sh["lane"], "shadowPass": sh["wouldPass"],
                        "livePass": sh["livePassed"], "wilson": sh["wilson"],
                        "confluence": sh["confluence"], "tags": sh["tags"], "why": sh["why"]})
    # `scored` counts SCORINGS in this one sweep, never names — the v2225 lesson, which inflated a
    # count to 1141 against a 403-name universe by summing re-scorings into a field called `names`.
    return {"scored": scored, "disagreements": dis, "names": sorted(set(seen))}



# ── THE CROP THAT NAMED IT (#45) ────────────────────────────────────────────────────────────────
# Konyo wants the item ledger to SHOW its evidence, not merely assert it. A receipt already carries
# a frameId; what it could not carry was the picture.
#
# ⚠ WHY THE CROP OUTLIVING THE REEL IS THE WHOLE POINT. Retention deletes footage once it has given
# up its information — correctly, and it is what keeps his disk breathing. But it means the frame
# behind every ledger entry eventually stops existing, and "71 pages were read from it" is a
# sentence, not a picture. A 15 KB crop survives the 80 MB reel, so the evidence outlives the film.
#
# ⚠ AND IT IS NOT A WITNESS. The crop is the SAME look that produced the name. Counting it would
# double the evidence for one glance — the exact defect v2209 fixed when a persisted prior started
# counting as a second witness. It is stored for HIM to look at, and the gate never sees it.
# [[d2r-multiwitness-corroboration]] [[the-unjoined-end]]
CROP_DIR = "tooltip_crops"
CROP_MAX_BYTES = 60 * 1024        # a tooltip crop that big is a mis-derived rectangle, not a tooltip
CROP_BUDGET = 600                 # a hard ceiling on how many he accumulates; oldest are not touched


def _crop_room(out_root):
    """The crop store's budget, asked before a crop is written. -> why it is full | None"""
    try:
        os.makedirs(out_root, exist_ok=True)
        n = len([f for f in os.listdir(out_root) if f.endswith(".jpg")])
        if n >= CROP_BUDGET:
            return ("the crop store already holds %d — at the %d ceiling, so this one was "
                    "not written (say it, never silently skip)" % (n, CROP_BUDGET))
    except Exception as e:
        return "could not prepare the crop store: %s" % str(e)[:70]
    return None


def _crop_kept(dest):
    """The byte cap, the backstop after a crop is written. -> why it was discarded | None"""
    try:
        if os.path.getsize(dest) > CROP_MAX_BYTES:
            os.remove(dest)
            return ("the crop came out larger than %d bytes, so the rectangle is wrong — "
                    "discarded rather than filed beside an item" % CROP_MAX_BYTES)
    except Exception:
        pass
    return None


def _crop_from_box(reel_dir, frame, box, xy_map, out_root):
    """REG-2915 (#158.7) - THE CROP CUT FROM THE BOX THE READ RETURNED. -> (relpath | None, why)

    Frame differencing cannot find a tooltip on his reels - the D2R world animates behind the panel, so the change box
    covers 53-91% of the frame and the byte cap rightly refuses it. The read that NAMED the item saw the tooltip; its box,
    in the picture it saw, is placed on the frame through the read's own picture map (xy_map, the one its points use),
    padded and kept within the frame by tooltip_crop.rect_from_read_box. A box that cannot be placed, or that covers
    too much of the frame to be a tooltip, is refused with why - never a full-frame crop. The byte cap stays the
    backstop. Like every crop, it is evidence for him to look at, never a witness."""
    try:
        import tooltip_crop as _tc
    except Exception as e:
        return None, "tooltip_crop did not import: %s" % str(e)[:70]
    rect, why = _tc.rect_from_read_box(box, xy_map)
    if not rect:
        return None, why
    full = _crop_room(out_root)
    if full:
        return None, full
    dest = os.path.join(out_root, "%s__%s__tip_%d_%d.jpg" % (os.path.basename(reel_dir), os.path.splitext(frame)[0],
                                                            rect[0], rect[1]))
    ok, w = _tc.crop_to(os.path.join(reel_dir, frame), rect, dest, max_side=_tc.TIP_MAX_SIDE)
    if not ok:
        return None, w
    big = _crop_kept(dest)
    if big:
        return None, big
    return os.path.join(CROP_DIR, os.path.basename(dest)), None


def _crop_for(reel_dir, frame, prev_frame, out_root):
    """Derive and store the tooltip rectangle for one frame. -> (relpath|None, why)

    Never raises into a sweep, and never invents a rectangle: every refusal from tooltip_crop is
    passed through verbatim rather than collapsed to None, so "no tooltip here" and "the frames were
    different sizes" stay different answers.
    """
    if not prev_frame:
        return None, "no previous frame in this run to difference against"
    try:
        import tooltip_crop as _tc
    except Exception as e:
        return None, "tooltip_crop did not import: %s" % str(e)[:70]
    a = os.path.join(reel_dir, prev_frame)
    b = os.path.join(reel_dir, frame)
    rect, why = _tc.changed_rect(a, b)
    if not rect:
        return None, why
    full = _crop_room(out_root)
    if full:
        return None, full
    dest = os.path.join(out_root, "%s__%s" % (os.path.basename(reel_dir), frame))
    ok, w = _tc.crop_to(b, rect, dest)
    if not ok:
        return None, w
    big = _crop_kept(dest)
    if big:
        return None, big
    return os.path.join(CROP_DIR, os.path.basename(dest)), None


# ── THE FOLD (law 1) ────────────────────────────────────────────────────────────

_BUCKET_RE = re.compile(r"^(.*)#\d+$")


def look_id(e, witness_field="witness"):
    """The look one sighting belongs to, in ONE spelling. '' when the sighting names none.

    `witness` is "<sid>#<bucket>", minted at the re-look loop; a persisted prior carries only its
    `session`. gate() keys the keep bar on it and vault_evidence._measure keys a visit on it, so
    this is the one definition both call — a second copy would drift. [[copy-drift]]

    ══ 2026-09-28 (Ledger fix, finding 7) — ONE REEL, TWO SPELLINGS, WAS TWO LOOKS ══════════════
    The sweep mints `sid = idx.get("sessionId") or os.path.basename(reel_dir)` (the reel loop), so
    one reel can arrive as "s_…" and as "reel_s_…". Their buckets "reel_s_X#0" and "s_X#0" are
    different strings, and this counted them as two looks at one stash screen. evidence_for already
    normalises the reel through chronicle_retro._reel_key; the look id now goes through the same
    function. It can only ever REMOVE a look, never add one. MEASURED 2026-09-28 on a read-only
    copy of his vault_accum.json: 0 of 28 look ids carry the prefix today — latent, not live.
    """
    if not isinstance(e, dict):
        return ""
    raw = e.get(witness_field) or e.get("session")
    return _cr._reel_key(str(raw)) if raw else ""


def _fold_bare_sessions(ids):
    """Drop a BARE session id when that same session also appears with a re-look bucket.

    ⚠ THIS IS A LIVE DOUBLE-COUNT, AND IT IS REPRODUCIBLE ON HIS OWN FILE. A fresh sighting carries
    `witness` = "<sid>#<bucket>" (minted at the re-look loop, ~:750). A sighting PERSISTED by an
    earlier sweep carries no `witness` key at all, because _witness_rows ships only
    {session, frame, lane, conf} — so the fallback above reads its bare `session`. "sA" and "sA#0"
    are different strings, so ONE look counts as TWO witnesses. Measured, with his real rows:

        fresh alone                 witnesses=1  ['s_1787512325134_62795#0']
        fresh + its own prior       witnesses=2  ['s_…62795', 's_…62795#0']
        2 recordings + their priors witnesses=4  ['sA','sA#0','sB','sB#0']  pass=True

    That last line is the damage: two recordings clearing a THREE-witness bar. And the prior-fold
    that is supposed to stop a sighting arriving twice cannot — it keys on (session, frame), and
    every persisted frame is None (17 of 17 in tv/vault_seen.json today).

    THE RULE: a row that does not say WHICH look it came from cannot be SHOWN to be a different
    look from the buckets of its own session, so it must not be counted beside them. A session with
    only bare rows still counts once — pre-v1792 evidence is unchanged, which is why this does not
    quietly re-grade old sightings.

    ⚠ AND IT IS FAIL-CLOSED, NOT [[unknown-stays-unknown]] — I labelled it wrongly and the review
    was right to say so. An unbucketed row IS unknown, and this resolves that unknown to "not an
    extra witness" rather than leaving it unresolved. The direction is chosen, not neutral, and here
    is why it is the right one: the KEEP bar's wrong answer is CLAIMING HE OWNS SOMETHING HE DOES
    NOT, and a refused sighting is not destroyed — v2051 banks it as `unsure`, so one more look
    grounds it. Over-counting is unrecoverable in the way that matters; under-counting costs a
    second look. The honest cost is real: given a bare prior that truly was bucket 0 and a fresh
    sighting that is bucket 1, this counts one where two happened. That case needs a partial re-read
    of one reel, it has never been observed, and it resolves itself the next time the reel is swept
    whole. Named here so the next person can challenge it rather than discover it.

    ⚠ MEASURED BEFORE SHIPPING, because this can only ever LOWER a count: across
    tv/vault_accum.json and tv/vault_last_result.json, ZERO rows change today. The collision needs a
    name to hold both a persisted prior and a fresh sighting from the same session, which is what a
    re-sweep produces — so this lands before it has grounded anything, not after.
    """
    # ⚠ `"#" in i` IS NOT A BUCKET TEST — same review. The minter writes "%s#%d", so a look id ends
    # in "#" plus digits; any other "#" belongs to the session name and must not be split on.
    ids = {str(i) for i in (ids or []) if str(i)}
    bucketed = set()
    for i in ids:
        m = _BUCKET_RE.match(i)
        if m:
            bucketed.add(m.group(1))
    return sorted(i for i in ids if not (not _BUCKET_RE.match(i) and i in bucketed))


def _witness_rows(evidence):
    """The provenance the board shows when he asks WHY it thinks he owns this. Sorted = stable."""
    # v1786 — CARRY conf. These rows are not only what the board shows: control_app re-gates a
    # caller-supplied proposal by feeding them straight back into gate(), and gate() reads conf.
    # Without it bestConf was 0.0, so a GENUINE proposal — two sessions at 0.97 and 0.95 — was
    # refused with "the reader itself was unsure (0.00 < 0.55)", blaming the reader for a field the
    # provenance never carried. It was fail-CLOSED only because the console posts an empty body
    # today; the moment anything posted the engine's own proposal back, apply would refuse
    # everything. Found by an adversarial review of this lane.
    # v2209 — CARRY THE WITNESS ID, AND ONLY WHEN THERE IS ONE. Dropping it is what made a
    # persisted prior fall back to its bare session and double-count against its own fresh sighting
    # (see _fold_bare_sessions). The fold repairs rows already on disk; this stops new ones losing
    # the identity at all.
    #
    # ⚠ THE FIRST CUT WROTE `e.get("witness") or e.get("session")`, AND A CROSS-FAMILY REVIEW KILLED
    # IT IN ONE SENTENCE: after a single persist round-trip every row would SAY it has a look id,
    # so "never had a bucket" and "bucket unknown" become the same string and the fold's own premise
    # stops being true of its own output. A fallback that manufactures the missing fact is
    # [[unknown-stays-unknown]] broken by the fix for it. Absent stays absent.
    # ⚠⚠ v2233 — A FRAME THAT WAS NEVER RECORDED MUST SAY SO, NOT ARRIVE AS null.
    # MEASURED on his tree 2026-08-28: all 17 vault_seen.json rows carry `"frame": null`, and
    # `conf: 0.0`, and `lastSeenTs: null`. Not missing keys — PRESENT keys with empty values, which
    # is how they survived every merge unnoticed. #45's whole purpose is tracing an item back to
    # "which reel + FRAME" and then to the picture that established the name, and the field the
    # trace depends on is blank on every row he owns.
    #
    # The live sighting builder DOES carry it (`"frame": name`, ~:988) and vault_seen_save preserves
    # what it is given, so new evidence is fine. These rows are folded-back PRIOR: written before
    # the frame was carried, and a null propagates through every union for ever.
    #
    # So the null becomes a STATED absence. "no frame was recorded for this sighting" and "we have
    # a frame and it is empty" are different facts, and only the first is true here — a trace that
    # finds null cannot tell whether the evidence is old or the pipeline is broken.
    # [[unknown-stays-unknown]] [[plumbing-with-no-tap]]
    rows = []
    for e in evidence:
        _f = e.get("frame")
        r = {"session": e.get("session"),
             "frame": _f if _f else None,
             "frameNote": None if _f else "no frame was recorded for this sighting",
             "lane": e.get("lane"), "conf": e.get("conf")}
        # v3369 — AND THE VALUE FACTS. This builder has silently dropped a needed field THREE times
        # already — conf (v1786), the witness id (v2209), the crop (v2239) — each repaired by hand,
        # each invisible until something downstream read a confident blank. WITNESS_NOT_CARRIED
        # below makes the fourth kind of drop loud instead.
        #
        # `is not None`, never truthiness: eth=False and sockets=0 are ANSWERS, and `if e.get("eth")`
        # would throw both away as if the reader had said nothing. [[unknown-stays-unknown]]
        for _vf in ("sockets", "eth", "quality", "promptVer", "point", "cell", "cellWhy", "holder"):   # v3767 - who holds it, and where
            if e.get(_vf) is not None:
                r[_vf] = e.get(_vf)
        if e.get("cropFrom") is not None:   # REG-2915 - how the crop was cut (the read's tooltip box, or the frame difference)
            r["cropFrom"] = e.get("cropFrom")
        if e.get("laneSaid") is not None:   # REG-1911 - what the reader called it, when it was filed by its point
            r["laneSaid"] = e.get("laneSaid")
        w = e.get("witness")
        if w:                      # falsy ("" / None) is NOT a look id; it stays absent
            r["witness"] = w
        # v2239 (#45) — CARRY THE PICTURE, OR WHY THERE IS NONE. This is the join, and without it
        # the whole crop lane was inert: the sweep derived a rectangle, wrote a crop, hung it on the
        # sighting — and this builder rebuilt every row from four fields and dropped it. Both ends
        # were correct and nothing connected them, which is the same shape that made v2223's vault
        # watchdog skip every reel forever. The tell was the COUNT: 0 crops and 0 stated reasons on
        # a fixture run that had produced both. [[the-unjoined-end]] [[plumbing-with-no-tap]]
        #
        # `cropWhy` rides along on purpose. "no tooltip on this frame" and "the crop store is full"
        # are different answers, and a bare absence would make them one. [[unknown-stays-unknown]]
        _c = e.get("crop")
        if _c:
            r["crop"] = _c
        elif e.get("cropWhy"):
            r["cropWhy"] = e.get("cropWhy")
        rows.append(r)
    return sorted(rows, key=lambda r: (str(r["session"]), str(r["frame"]), str(r["lane"])))


# ── v2074 — THE CLOSED FIELD LIST THAT HAS SILENTLY DROPPED A FIELD FOUR TIMES ───────────────
# apply_payload() rebuilds each owned row by NAMING the fields it ships. That is the right shape —
# a payload should be deliberate — but it means a field added to _owned_row simply does not arrive,
# and NOTHING fails. It has happened four times (v1986, v1996, v2004, v2006), and v1986's was the
# expensive one: `witnesses` shipped as an int instead of rows, so a board loop `for (i < w.length)`
# over a number never ran, and REG-339's 3-session equipment lock was disabled ON THE ONLY PATH THAT
# RUNS while still passing against hand-made arrays in tests.
#
# So the omission is now DECLARED rather than accidental. Anything an owned row carries must either
# ship, or be named here with a reason. The guard in test_vault_retro.py fails on any field that is
# in neither list — a fifth silent drop becomes a loud one.
#
# Empty today, and that is the honest state: every field an owned row carries is shipped.
# ── v3369 — THE SAME DISCIPLINE, ONE BOUNDARY UP ────────────────────────────────────────────
# v2074 (above) closed this class at apply_payload after FOUR silent drops. It did not close it at
# _witness_rows, which by its own comments has dropped a field THREE times — conf (v1786), the
# witness id (v2209), the crop (v2239) — and dropped four more on the day v3368 added them.
#
# So the sighting's field list is now DECLARED. Anything `sight` carries must either reach the
# banked witness or be named here with a reason. The guard in test_vault_retro.py fails on any
# field in neither list, so a fifth drop is loud.
WITNESS_NOT_CARRIED = {
    "ts": "the row carries lastSeenTs, folded across every sighting by _owned_row",
    "count": "merge-max lives on the row; a per-sighting count would re-open the max",
    "kind": "the row votes on kind across sightings; one witness's guess is not the answer",
}

APPLY_NOT_SHIPPED = {
    # "fieldname": "why the board does not need it",
    #
    # v3369 — `variants` is DERIVED, and its source ships. _variants_of() is a pure fold over the
    # witnesses, and witnesses ARE in the payload, so the board can recompute it exactly and a
    # round-trip back through gate() loses nothing. Shipping it as well would put a second copy of
    # one fact on the wire, which is how two paths start disagreeing. [[copy-drift]]
    #
    # ⚠ THE MOMENT THE BOARD RENDERS VARIANTS, DELETE THIS LINE AND SHIP IT. A derived field is
    # only safe to omit while nobody on the far side needs it in hand.
    "variants": "derived by _variants_of from `witnesses`, which the payload already carries",
}


def _variants_of(evidence, name=None):
    """The DISTINCT (sockets, eth, quality) triples under one (name, lane) key, each with its count.

    ⚠ ONE KEY LEGITIMATELY HOLDS SEVERAL PHYSICAL ITEMS. A 4-socket Gorgon Crossbow and a plain one
    are different items worth different money, and they fold to the same (name, lane). Measured on
    his live store the day this was written: 4 of 44 rows already carry more than one witness
    (Horadric Cube 20, War Traveler 4, Magefist 2, Gheed's Fortune 2).

    So the row must NOT carry a single `sockets`. That is a one-to-many fact in a one-to-one store:
    setdefault keeps the first, d[k] = v keeps the last, and neither says a word about the other.
    A row carries the SET it has seen; the sighting carries what one look saw.

    Triples that are entirely unknown are dropped — a variant nobody could describe is not a
    variant, it is an absence, and counting it would inflate the answer with blanks.
    """
    # REG-2037 (#207, the 10-07 sim F6) - ONE LOOK THAT DISAGREES IS NOT A SECOND ITEM. MEASURED on his seen bank: Grief,
    # one session, three reads 1.4-3 s apart, 5 sockets each - eth True once, False twice - so the row carried an
    # ethereal Grief nobody owns. Sightings in ONE session with the same sockets and no cell telling them apart
    # cannot be shown to be two items; where their eth reads disagree, that item's eth is UNKNOWN (None) and the reads
    # ride beside it as ethReads - a minority read never invents an ethereal item, and nothing claims it is not one.
    # Different sessions or different cells stay different items (the law above). And a runeword's "quality" is the
    # colour of its name, not a quality the reader can give (Heart of the Oak read unique, blue and gold): None.
    rw = _is_runeword(name)
    looks = []
    for e in evidence:
        if not isinstance(e, dict):
            continue
        looks.append([e.get("sockets"), e.get("eth"), None if rw else e.get("quality"),
                      (e.get("session"), str(e.get("cell")) if e.get("cell") is not None else None)])
    groups = {}
    for lk in looks:
        groups.setdefault((lk[3], lk[0], lk[2]), []).append(lk)
    disagree = {}
    for gk, g in groups.items():
        eths = [x[1] for x in g if x[1] is not None]
        if True in eths and False in eths:
            for x in g:
                x[1] = None
            disagree[(gk[1], None, gk[2])] = {"eth": eths.count(True), "notEth": eths.count(False)}
    seen = {}
    for lk in looks:
        trip = (lk[0], lk[1], lk[2])
        if trip == (None, None, None):
            continue
        seen[trip] = seen.get(trip, 0) + 1
    out = []
    for t, n in seen.items():
        v = {"sockets": t[0], "eth": t[1], "quality": t[2], "witnesses": n}
        if t in disagree:
            v["ethReads"] = disagree[t]
        out.append(v)
    # sorted so the answer does not depend on the order the sightings arrived in
    return sorted(out, key=lambda v: (str(v["sockets"]), str(v["eth"]), str(v["quality"])))


_RUNEWORDS = {}


def _is_runeword(name):
    """True when `name` is a runeword in the game's own tables (tv/item_tables.json); False when it is not or the
    tables cannot be read - an unreadable table never strips a fact."""
    if not name:
        return False
    if "n" not in _RUNEWORDS:
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "item_tables.json"),
                      encoding="utf-8") as fh:
                t = json.load(fh)
            _RUNEWORDS["n"] = {re.sub(r"[^a-z]", "", str(r.get("name") or "").replace("\u2019", "'").lower())
                               for r in (t.get("runewords") or {}).values()} - {""}
        except Exception:
            _RUNEWORDS["n"] = set()
    return re.sub(r"[^a-z]", "", str(name).replace("\u2019", "'").lower()) in _RUNEWORDS["n"]


def _owned_row(key, evidence):
    """Fold one (name, lane) pile into an owned row. MERGE-MAX on count and conf; max on lastSeen.

    Law 1 lives here: `count` is a max() across every sighting, so no session can ever produce a row
    whose count is lower than one already seen, and the result does not depend on the order the
    sightings arrived in.
    """
    name, lane = key
    count = None
    conf = 0.0
    last = None
    kinds = {}
    for e in evidence:
        count = _max_count(count, e.get("count"))
        conf = max(conf, _conf_of(e.get("conf")))
        ts = e.get("ts")
        if isinstance(ts, (int, float)):
            last = ts if last is None else max(last, ts)
        k = e.get("kind") or "item"
        kinds[k] = kinds.get(k, 0) + 1
    # the kind the most sightings agreed on; ties broken by name so the answer is order-independent
    kind = sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if kinds else "item"
    return {"name": name, "lane": lane, "kind": kind, "count": count, "conf": round(conf, 3),
            "witnesses": _witness_rows(evidence), "lastSeenTs": last,
            "variants": _variants_of(evidence, key[0])}


def merge_vault(existing, incoming):
    """MERGE-MAX ACROSS SESSIONS (law 1) — fold a new proposal into the accumulated picture.

    Both sides may be a proposal dict, a list of owned rows, or a {key: row} map; the result is the
    same either way and merge_vault(a, b) agrees with merge_vault(b, a) on every count.

    A row the incoming read saw FEWER of does not subtract and does not disappear — the shortfall is
    reported in `held` with a why, because an obstructed or half-scrolled stash frame is a normal
    event and not evidence he threw something away. A row missing from the incoming read entirely is
    simply absent evidence, and absence is never a claim.

    -> {"owned": [...], "added": [...], "raised": [...], "held": [...], "byKey": {"lane|name": row}}
    """
    have = {}
    for row in _rows_of(existing):
        _absorb(have, row)
    added, raised, held = [], [], []
    for row in _rows_of(incoming):
        key = (row["name"], row["lane"])
        prev = have.get(key)
        if prev is None:
            _absorb(have, row)
            added.append(row["name"])
            continue
        pc, nc = prev.get("count"), row.get("count")
        if pc is not None and nc is not None and nc < pc:
            # LAW 1. Never lower a count. Say so instead.
            held.append({"name": row["name"],
                         "why": "this read saw %d in %s but %d was already recorded — kept the "
                                "higher count; a half-scrolled or obstructed panel is normal and is "
                                "not evidence anything was thrown away" % (nc, row["lane"], pc)})
        elif nc is not None and (pc is None or nc > pc):
            raised.append(row["name"])
        _absorb(have, row)
    owned = sorted(have.values(), key=lambda r: (r["lane"], r["name"].lower(), r["name"]))
    return {
        "owned": owned,
        "added": sorted(set(added)),
        "raised": sorted(set(raised)),
        "held": held,
        "byKey": {"%s|%s" % (r["lane"], r["name"]): r for r in owned},
    }


#: REG-1718 - the fields that NAME a look (which frame, which reel, which reader, when) - a re-read never fills these
_WITNESS_IDENTITY = frozenset(("session", "frame", "frameNote", "lane", "witness", "promptVer", "ts", "seenAt", "filledBy"))


def _absorb(have, row):
    """Merge one row into the accumulator under MERGE-MAX. Idempotent: absorbing twice is a no-op."""
    key = (row["name"], row["lane"])
    cur = have.get(key)
    if cur is None:
        have[key] = dict(row)
        return
    cur["count"] = _max_count(cur.get("count"), row.get("count"))
    cur["conf"] = round(max(_conf_of(cur.get("conf")), _conf_of(row.get("conf"))), 3)
    a, b = cur.get("lastSeenTs"), row.get("lastSeenTs")
    cur["lastSeenTs"] = a if b is None else (b if a is None else max(a, b))
    seen = {(w.get("session"), w.get("frame"), w.get("lane")): w for w in (cur.get("witnesses") or [])}
    for w in (row.get("witnesses") or []):
        k = (w.get("session"), w.get("frame"), w.get("lane"))
        if k not in seen:
            cur.setdefault("witnesses", []).append(w)
            seen[k] = w
            continue
        # REG-1713 (the v3554 eye) - the SAME look read again (a reel an older reader sealed, re-bought by v3554) came
        # back WITH its point and cell, and this dedupe dropped it whole: the stored look stayed cell-less for ever.
        # Fill-only - a re-read adds where a look had none; it never moves a cell already filed.
        old = seen[k]
        if not (isinstance(old, dict) and isinstance(w, dict)):
            continue
        # REG-1718 (the v3556 eye) - and EVERY fact the first read lacked, not only the cell: a re-read that brought
        # sockets / eth / quality lost them, so the item-facts doctor said MISSING for facts the reader did read. Still
        # fill-only - a fact already filed never moves - and each filled fact names the reader that supplied it
        # (`filledBy`), so a later reader's fact is never credited to the first reader's promptVer.
        _by_ver = str(w.get("promptVer") or "")
        for _f, _v in w.items():
            if _f in _WITNESS_IDENTITY or _v is None or _v == "" or _v == [] or _v == {}:
                continue
            if old.get(_f) is None or old.get(_f) == "" or old.get(_f) == [] or old.get(_f) == {}:
                # REG-1730 (the v3557 eye) - a COPY: filing the incoming list/dict by reference let a later mutation of
                # the row (or of a nested list another absorb thinks it owns) change a fact already filed.
                old[_f] = copy.deepcopy(_v)     # REG-1735 - any type (a JSON round trip raised on a non-JSON value)
                if _by_ver and _by_ver != str(old.get("promptVer") or ""):
                    old.setdefault("filledBy", {})[_f] = _by_ver
    cur["witnesses"] = sorted(cur.get("witnesses") or [],
                              key=lambda r: (str(r.get("session")), str(r.get("frame")),
                                             str(r.get("lane"))))
    if cur.get("kind") in (None, "item"):
        cur["kind"] = row.get("kind") or cur.get("kind") or "item"


def _rows_of(blob):
    """Accept a proposal, a list of rows, or a {key: row} map. Anything else contributes nothing."""
    if not blob:
        return []
    if isinstance(blob, dict):
        rows = blob.get("owned") if "owned" in blob else list(blob.values())
    else:
        rows = list(blob)
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        name = str(r.get("name") or "").strip()
        lane = str(r.get("lane") or "").strip().lower()
        if not name or lane not in LANES:
            continue
        out.append({"name": name, "lane": lane, "kind": r.get("kind") or "item",
                    "count": _count_of(r.get("count")), "conf": _conf_of(r.get("conf")),
                    "witnesses": [w for w in (r.get("witnesses") or []) if isinstance(w, dict)],
                    "lastSeenTs": r.get("lastSeenTs")})
    return out


# ── THE SWEEP ───────────────────────────────────────────────────────────────────

def _empty(why, sessions_seen=0):
    """A refusal, fully shaped. ok:False with a why — never a fabricated empty success (law 4)."""
    return {"ok": False, "generatedTs": int(time.time() * 1000), "why": why, "sessionsRead": [],
            "sessionsExamined": [],
            "owned": [], "throwOut": [], "unsure": [], "held": [],
            "totals": {"sessionsSeen": sessions_seen, "framesSeen": 0, "classified": 0,
                       "pagesRead": 0, "skipped": 0}}


_RESOLVER_WARNED = [False]


_GRAIL_WARNED = [False]


_VOCAB_WARNED = [False]


def _vocab_of(name):
    """-> (vocab, why). What the game's own affix tables say this NAME is.

    v3364 (#60) — his ask: *"the vault needs to know every single item in its data base ... it also
    needs to know what to route to garbage and what is considered HIGH QUALITY"*. The roster names
    uniques, sets and runewords — 1,059 of them. It cannot name anything MAGIC or RARE, because
    those are COMPOSED at drop time from four affix tables and a base type rather than drawn from a
    list. `affix_lexicon` carries that vocabulary, pulled from his own install.

    ⚠ THE FIELD IS `vocab`, NOT `kind`. The unsure row already carries `"kind": "item"` — a
    hardcoded literal naming the ROW's kind, not the item's class. Reusing that name would put two
    referents under one label and the older one would win silently.
    [[label-outlived-referent]]

    ⚠ AN ABSENT LEXICON IS UNKNOWN, NOT A CRASH AND NOT A GUESS. The store is generated from a
    28 GB game install that a CI runner does not have, so `None` here is the ordinary case off his
    Mac. It says so ONCE rather than returning a quiet default.
    [[unknown-stays-unknown]] [[feedback-silence-is-not-evidence]]
    """
    try:
        import affix_lexicon as _al
    except Exception as e:
        if not _VOCAB_WARNED[0]:
            _VOCAB_WARNED[0] = True
            print("   \u26a0 the affix lexicon will not import (%s) \u2014 no name can be read as "
                  "magic or rare here" % str(e)[:80])
        return None, "the lexicon module is unavailable"
    try:
        return _al.classify(name)
    except Exception as e:
        return None, "the lexicon raised: %s" % str(e)[:90]


def _prompt_ver():
    """-> the vault prompt version that read this item, or None.

    ⚠ None, never a guess. If tv_diablo cannot be imported the version is UNKNOWN, and stamping a
    remembered constant would attribute the row to a prompt that may not have run.
    """
    try:
        import tv_diablo as _td
        return str(getattr(_td, "VAULT_PROMPT_VER", "") or "") or None
    except Exception:
        return None


#: the colours his items actually come in, in his own words: "white/blue/gold/unique/green for set"
QUALITIES = ("white", "blue", "gold", "unique", "set")


def _sockets_of(v):
    """-> int 0..6, or None. ⚠ None and 0 are DIFFERENT ANSWERS and must never collapse."""
    if v is None or v is True or v is False:
        return None
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    # ⚠ BOUNDED BY THE GAME, NOT BY TASTE. Nothing in D2R carries more than 6 sockets, so a larger
    # number is a misread rather than a rare item, and banking it would be a fact about his loot
    # that the game cannot produce.
    return n if 0 <= n <= 6 else None


def _quality_of(v):
    """-> one of QUALITIES, or None. An unrecognised colour is UNKNOWN, never a nearest match."""
    q = str(v or "").strip().lower()
    if q in ("green",):
        q = "set"          # his word for it; the store keeps one spelling
    if q in ("normal",):
        q = "white"
    if q in ("magic",):
        q = "blue"
    if q in ("rare",):
        q = "gold"
    return q if q in QUALITIES else None


def _grail_guard():
    """A predicate: is this name a GRAIL ITEM — a named unique or set piece he is hunting?

    v1903 — THE BACKSTOP THE THROW LANE NEVER HAD. Whether an item is junk is decided entirely by
    the reader's `throwOut` flag: a vision model's opinion, arriving through a prompt (see
    tv_diablo.VAULT_READ_PROMPT) with real consequences. Law 3 of this file is that there is no
    un-throw in Diablo, and the whole gate above is built on that — a strictly higher confidence
    floor, three separate recordings, never automatic. All of it guards HOW MUCH evidence a throw
    needs, and none of it guards WHAT MAY BE THROWN.

    So one thing is settled in code rather than left to the reader's judgement: a name on his grail
    roster is never a throw-out suggestion, at any confidence, from any number of recordings. That
    is not a matter of degree — a unique or set piece is the thing this entire project exists to
    collect, and a suggestion to bin one is wrong even when the reader is certain.

    ⚠ AN UNLOADABLE ROSTER TURNS THE BACKSTOP OFF, so it says so once rather than returning a quiet
    False. A guard that cannot answer must not answer "no". [[feedback-silence-is-not-evidence]]
    """
    try:
        import chronicle_resolve as _res
        roster = _res.load_roster()
        set_roster = _res.load_set_roster()
    except Exception as e:
        if not _GRAIL_WARNED[0]:
            _GRAIL_WARNED[0] = True
            print("   \u26a0 grail backstop unavailable (%s) \u2014 a throw-out suggestion can no "
                  "longer be checked against his roster" % e)
        return None

    def is_grail(name):
        try:
            k = _res._norm(name)
        except Exception:
            return False
        return bool(k) and any(r and k in r for r in (roster, set_roster))

    return is_grail


def _name_folder(resolve=None):
    """A function that CORRECTS a reader's item name onto his roster, or leaves it alone.

    v1885 — THE VAULT LANE HAD NO FOLD AT ALL, and the chronicle lane has had one for versions.
    Measured on the exact corrections his chronicle sweep made on 2026-08-20 — 53 of them in one
    reel — pushed at the vault instead:

        pushed  Atma's Scarab · Battlecage · Saracen's Chance
        owned   Atma's Scarab · Battlecage · Saracen's Chance      (verbatim)
        both spellings together -> SIX owned rows for THREE real items

    And merge-max never subtracts, so each of those is PERMANENT. A systematic misread is exactly
    the kind that repeats across sessions — this file's own law-3 note says so: "Coming back four
    minutes later and reading 'Ral' as 'Ort' a second time is exactly as likely as the first time"
    — so the two-witness keep bar does not save it. Two sessions of one misread is a ghost item in
    his vault, forever.

    ⚠ THE ONE THING THIS MUST NOT DO IS RETIRE WHAT IT CANNOT FOLD. The chronicle fold may call an
    unfoldable name debris, because a Chronicle page holds nothing but grail items. A STASH holds
    runes, gems, materials, bases, charms and jewels — `canonical("Ral Rune")` is None and that is
    a real thing he owns. So: correct what folds, leave everything else EXACTLY as read.
    [[d2r-multiwitness-corroboration]] [[feedback-generalize-fixes]]
    """
    if resolve is not None:
        return resolve
    try:
        import chronicle_resolve as _res
        roster = _res.load_roster()
        set_roster = _res.load_set_roster()
    except Exception as e:
        if not _RESOLVER_WARNED[0]:
            _RESOLVER_WARNED[0] = True
            print("   \u26a0 vault name-fold unavailable (%s) \u2014 gating on RAW reader names, so a "
                  "misread can become a permanent row" % e)
        return lambda n: n

    # ⚠ EXACT FOLDS ONLY IN THE VAULT LANE — NO NEAR MATCHES. This is not caution, it is a defect
    # my own test caught within a minute of writing the fold: canonical() near-matched
    # "Isenhart's Armory (set)" — a SET AGGREGATE — onto "Isenhart's Parry (shield)", a specific
    # piece. That is not a correction, it is a find he never made, and it is exactly what the
    # resolver's own comment warns about ("guessing here writes a find he never made").
    #
    # WHY THE CHRONICLE LANE CAN AFFORD NEAR MATCHES AND THIS ONE CANNOT: a Chronicle page is a
    # CLOSED list of grail names, so every row IS a roster item and the nearest one is very likely
    # right. A STASH IS AN OPEN UNIVERSE — runes, gems, materials, bases, charms, jewels, set
    # aggregates, quest items — so "nearest roster entry" is a guess about which of two different
    # things he owns.
    #
    # WHAT THIS FIXES, measured: the apostrophe class, which is the common one and the one his own
    # sweep hit — "Atma's Scarab" and "Saracen's Chance" both normalise onto their curly-quoted
    # roster names EXACTLY (_norm folds ’ to ' and strips non-letters).
    # WHAT IT DELIBERATELY DOES NOT FIX: "Battlecage" -> "Rattlecage". That needs a near match, and
    # an uncorrected row he can SEE is better than a confident wrong attribution he cannot.
    joined = _base_joined_keys(_res._norm)

    def fold(name):
        try:
            k = _res._norm(name)
        except Exception:
            return name
        if not k:
            return name
        for r in (roster, set_roster):
            if r and k in r:
                return r[k]
        # REG-2036 (#212 F14) - THE TOOLTIP'S BASE LINE JOINED TO ITS NAME. MEASURED on frame f_1791058494714:
        # "Dwarf Star" and "Dwarf Star Ring" were both stored from ONE tooltip - the reader joined the unique's name
        # to the base line under it. Still EXACT: a name folds only when it is a roster item's name followed by THAT
        # item's own base (the game's tables: Dwarf Star is a 'rin', a Ring), so "Dwarf Star Ring" -> "Dwarf Star"
        # and "Dwarf Star Amulet" stays as read.
        j = joined.get(k)
        if j:
            for r in (roster, set_roster):
                if r and j in r:
                    return r[j]
        return name           # a rune, a gem, a base, a charm — not debris, just not a grail name

    return fold


def _base_joined_keys(norm):
    """{norm(item name + its own base name): norm(item name)} for every unique and set item in the game's tables.

    From tv/item_tables.json (generated from the CASC): each unique / set item carries its base code, and the
    base code names its base. Unreadable tables -> {} (the fold stays exact-only, as it was), never a guess.
    """
    out = {}
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "item_tables.json"),
                  encoding="utf-8") as fh:
            t = json.load(fh)
        bases = t.get("items") or {}
        for grp in ("uniques", "setItems"):
            for row in (t.get(grp) or {}).values():
                b = (bases.get(row.get("code")) or {}).get("name")
                n = row.get("name")
                if b and n and norm(b) and not norm(n).endswith(norm(b)):
                    out.setdefault(norm(n + " " + b), norm(n))
    except Exception as _e:
        print("   \u26a0 vault name-fold: the game's item tables would not read (%s) - a name joined to its base line "
              "stays as read (the fold is exact-only)" % str(_e)[:60])
        return {}
    return out


# ══ #130 — RESUME-SEAL: carry a stopped sweep's accumulators across a relaunch ═══════════════════
# Mirrors the chronicle's REG-2039 stop/resume, but the vault CANNOT bank incrementally the way the
# chronicle does. merge_vault is MERGE-MAX on GRADED owned rows (law 1), and a single reel is one
# session that cannot ground alone (law 2 needs KEEP_MIN_WITNESSES distinct sessions, weighed once).
# Grading a half-read reel and merging it would SPLIT its witnesses — a later read of the rest could
# never raise a count already banked low. So instead of merging partial evidence, a stopped vault
# sweep PRESERVES its in-progress accumulators; the control side writes them to the resume store; the
# next pass SEEDS them and SKIPS the frames already read, then grades ONCE, at the end — exactly as
# an uninterrupted sweep does, so the proposal is identical to one that was never interrupted.
_RESUME_FS = "\x1f"     # the unit separator joining (name, lane) into one JSON-string key


class VaultSweepStopped(Exception):
    """Raised inside sweep() when on_checkpoint returns True — a waiting build asked the sweep to
    stop at its next banked read. The reads it has paid for are on record (the checkpoint persisted
    them); the reel is NOT sealed (it still owes its unread frames) and resumes after the relaunch.
    The caller catches this and stops cleanly, which is what releases the lock the relaunch waits on.
    The sibling of _ChronSweepStopped (control_app, REG-2039)."""


def _ser_ev(ev_map):
    """{(name, lane): [sighting...]}  ->  {"name\x1flane": [sighting...]}  — a JSON-safe rekey.

    The sighting dicts are referenced, not copied: a sighting is built once (sweep's page loop) and
    never mutated afterward, so this is safe and cheap even firing every few reads on a big reel."""
    out = {}
    for (name, lane), sights in (ev_map or {}).items():
        out["%s%s%s" % (name, _RESUME_FS, lane)] = list(sights or [])
    return out


def _deser_ev(d):
    """The inverse of _ser_ev. lane is the LAST field (it never carries the separator)."""
    out = {}
    for k, sights in (d or {}).items():
        if _RESUME_FS in k:
            name, lane = k.rsplit(_RESUME_FS, 1)
        else:
            name, lane = k, ""
        out[(name, lane)] = list(sights or [])
    return out


def _ser_state(evidence, throw_flags, unsure, held, folded_names,
               frames_seen, classified, pages_read, skipped, answered, rescued, trusted,
               sessions_seen, sessions_read, sessions_examined):
    """A JSON-safe snapshot of EVERY sweep accumulator, so a stopped pass loses nothing. The counts a
    RESUME re-derives by re-walking the reel (sessionsSeen/framesSeen/sessionsExamined and the
    classify-stage counters) are carried here for inspection; _deser_state names which a resume
    actually re-seeds."""
    return {
        "evidence": _ser_ev(evidence),
        "throw_flags": _ser_ev(throw_flags),
        "unsure": list(unsure or []),
        "held": list(held or []),
        "folded_names": dict(folded_names or {}),
        "frames_seen": int(frames_seen or 0),
        "classified": int(classified or 0),
        "pages_read": int(pages_read or 0),
        "skipped": int(skipped or 0),
        "answered": int(answered or 0),
        "rescued": int(rescued or 0),
        "trusted": int(trusted or 0),
        "sessions_seen": int(sessions_seen or 0),
        "sessions_read": list(sessions_read or []),
        "sessions_examined": list(sessions_examined or []),
    }


def _deser_state(st):
    """A serialized snapshot -> the accumulators a resume SEEDS. Only the evidence-bearing piles and
    the counters a re-walk would otherwise lose are restored:

      * evidence / throw_flags / folded_names / unsure / held — what the reads already PAID FOR. A
        re-walk SKIPS those frames, so none of this can be re-derived; it must be carried or it is
        lost.
      * pages_read / sessions_read — likewise bank what the skipped reads earned.

    The per-reel counters (sessionsSeen/framesSeen/sessionsExamined) and the classify-stage counters
    (classified/answered/rescued/trusted/skipped) are DELIBERATELY NOT returned: the resume re-walks
    the reel, re-running the classify stage for every run (the chronicle does the same — "the run
    still classifies, a few cheap calls"), so those counts rebuild themselves and seeding them would
    double-count against the re-walk. [[unknown-stays-unknown]]"""
    st = st or {}
    return {
        "evidence": _deser_ev(st.get("evidence")),
        "throw_flags": _deser_ev(st.get("throw_flags")),
        "unsure": list(st.get("unsure") or []),
        "held": list(st.get("held") or []),
        "folded_names": dict(st.get("folded_names") or {}),
        "pages_read": int(st.get("pages_read") or 0),
        "sessions_read": list(st.get("sessions_read") or []),
    }


def sweep(hist_dirs, sig=None, reader=None, classify=None, limit=None, resolve=None,
          on_reel=None,
          panel_gate=None, prior_seen=None,
          resume=None, on_checkpoint=None, checkpoint_every=4,
          on_tile=None, on_reel_timeout=None, reel_deadline_s=None):
    """THE VAULT RETRO SWEEP: sealed reels in, a PROPOSAL of what he owns out. Writes nothing.

    hist_dirs: sealed reel directories, newest-first (mini/stash reels are re-ordered to the front).
    sig(frame_path)      -> fingerprint or None. Production value: DEFAULT_SIG (chronicle_retro.jpeg_sig).
    classify(frame_path) -> an ownership surface name, a dict carrying one, or None. ONE call per
                            candidate still-run, on the run's most settled frame.
    reader(frame_path, surface) -> {"items": [{name, kind, count, conf, lane, throwOut, throwWhy}],
                            "conf": float, "note": str|None}. Only ownership runs are ever read.
    limit: read at most N reels (after the mini-first re-ordering) — the cost dial, not a filter on
           what counts as evidence.

    PAY FOR RUNS, NOT FRAMES — inherited wholesale from the chronicle sweep: ~150 frames become a
    handful of still-runs, one classify each, and only ownership runs cost a read.
    """
    if sig is None or reader is None or classify is None:
        # Law 4. "I was not given eyes" is a fact; dressing it as an empty stash would read exactly
        # like "you own nothing", which is the one wrong answer that looks like a right one.
        missing = ", ".join(n for n, v in (("sig", sig), ("reader", reader), ("classify", classify))
                            if v is None)
        return _empty("cannot sweep: no %s was supplied — this is not an empty vault, it is a sweep "
                      "that never ran" % missing, len(hist_dirs or []))

    # v2023 — order by MEASURED panel density when a gate is supplied, so `limit` spends the
    # budget on reels that demonstrably show a stash instead of on the four most recent ones.
    # REG-2271 — resolve the per-reel NO-PROGRESS grouping deadline ONCE, at call time (a default read
    # at import would freeze the bar). _reel_deadline_budget: default 20s, clamped under the 240s watchdog.
    _reel_deadline_s = _reel_deadline_budget(reel_deadline_s)
    dirs = order_reels(hist_dirs, panel_gate=panel_gate)
    if limit:
        dirs = dirs[:limit]
    evidence = {}          # (name, lane) -> [sighting...]
    throw_flags = {}       # (name, lane) -> [sighting...] the reader flagged as junk
    unsure, held = [], []
    sessions_read, sessions_seen = [], 0
    # ⚠ v2306 — WHICH REELS THIS SWEEP ACTUALLY OPENED, which is NOT the same as which it READ.
    # control_app's "examined, and there is no stash screen here" branch seals the reels the sweep
    # LOOKED AT and found nothing in — and it was iterating `sessionsRead`, which by definition is
    # empty in exactly that case. So it printed "Sealed at vp2017" and wrote nothing, every pass,
    # for ever. Reproduced twice on reel_s_1787239578536_99671 at zero cost.
    # [[the-unjoined-end]] [[plumbing-with-no-tap]]
    sessions_examined = []
    # v2020 — `classified` counts CALLS MADE. `answered` counts calls that came back with a
    # surface. They are the same number only when the classifier works, and the whole of
    # REG-382 is the case where they are not. See _verdict().
    # v2028 — `rescued` counts runs admitted only because a NEIGHBOUR frame resolved the tab
    # the probe's tooltip was covering. It is reported, not pocketed: if it ever reads 0 on
    # footage with tooltips, this fix has stopped working.
    frames_seen = classified = pages_read = skipped = answered = rescued = 0
    trusted = 0   # runs whose surface came from HIS declared focus rather than a paid read

    _fold = _name_folder(resolve)
    folded_names = {}
    # ══ #130 — RESUME-SEAL: seed a stopped pass's accumulators, then SKIP the frames it banked. ══
    # SEEDED: evidence, throw_flags, unsure, held, folded_names and the two read counters
    # (pages_read, sessions_read) — everything a read EARNED, which a resume's re-walk skips and so
    # cannot re-derive. The per-reel and classify-stage counts rebuild themselves on the re-walk (see
    # _deser_state). A resume that fails to seed drops banked reads; one that fails to skip re-pays
    # them — the guard (test_vault_resume_seal) asserts against both. [[the-unjoined-end]]
    # ⚠ A re-walked reel re-runs its classify stage and its blank/unclassifiable RUNS, so on a resume
    # those runs may re-count `classified`/`skipped` and re-note `held` — DIAGNOSTICS only; the
    # evidence it grounds and the seal it earns are untouched. Reads are never re-paid.
    _resume_frames = set()
    if resume and isinstance(resume, dict):
        _resume_frames = set(resume.get("frames") or [])
        _st = resume.get("state")
        if _st:
            try:
                _seed = _deser_state(_st)
                evidence = _seed["evidence"]
                throw_flags = _seed["throw_flags"]
                unsure = _seed["unsure"]
                held = _seed["held"]
                folded_names = _seed["folded_names"]
                pages_read = _seed["pages_read"]
                sessions_read = _seed["sessions_read"]
            except Exception as _rde:
                # a resume record that will not deserialize is UNKNOWN, never a licence to seal a
                # half-read reel: fall back to reading it in full — the frames are re-paid, nothing is
                # lost or corrupted. [[unknown-stays-unknown]]
                print("   ⚠ vault resume state would not seed (%s) — the reel is read from "
                      "the start" % str(_rde)[:80], flush=True)
                _resume_frames = set()
    # frames read (reader-called) so far: the prior pass's banked set plus this pass's reads. A
    # checkpoint records this; the next resume skips it.
    _read_frames = set(_resume_frames)
    _reads_this_pass = [0]

    def _maybe_checkpoint(_sid):
        """Every checkpoint_every NEW reads, hand the control side a snapshot to persist and ask
        whether a waiting build wants the sweep to stop. A FAILED checkpoint never ends a working
        sweep; a True answer raises VaultSweepStopped, which the caller turns into a clean,
        lock-releasing halt. The accumulators are read as closure free-variables, so it always sees
        their live values."""
        if on_checkpoint is None:
            return
        _reads_this_pass[0] += 1
        if checkpoint_every and (_reads_this_pass[0] % checkpoint_every) != 0:
            return
        try:
            _stop = on_checkpoint(_sid, sorted(_read_frames),
                                  _ser_state(evidence, throw_flags, unsure, held, folded_names,
                                             frames_seen, classified, pages_read, skipped,
                                             answered, rescued, trusted, sessions_seen,
                                             sessions_read, sessions_examined))
        except Exception as _ce:
            print("   ⚠ vault checkpoint failed (%s) — the sweep continues uninterrupted"
                  % str(_ce)[:80], flush=True)
            return
        if _stop:
            raise VaultSweepStopped(
                "stopped at a banked read for a waiting build: %d read(s) banked this pass; the reel "
                "resumes from the frames already read after the relaunch" % _reads_this_pass[0])

    for _reel_i, reel_dir in enumerate(dirs):
        # ── v3180 — THE ONLY PLACE THAT KNOWS A REEL HAS STARTED ────────────────────────────
        # Added for the sweep meter. This loop is the sweep's unit of work ("PAY FOR RUNS, NOT
        # FRAMES", above), so it is the only honest denominator a progress bar can use — and
        # before this hook existed NOTHING outside this function could see it advance. The
        # console showed "0 of 14" for 44 minutes because the caller's only counter was written
        # once, at the end. [[the-unjoined-end]]
        #
        # ⚠ A BROKEN CALLBACK MAY NEVER COST A SWEEP. This fires inside a loop that spends real
        # money per iteration; a meter is worth nothing next to the read it is watching, so every
        # failure here is swallowed on purpose.
        if on_reel is not None:
            try:
                on_reel(_reel_i, len(dirs), os.path.basename(str(reel_dir)))
            except Exception:
                pass
        # ── REG-2271 — PER-REEL NO-PROGRESS GROUPING DEADLINE ───────────────────────────────
        # _dl is a fresh no-progress window for THIS reel. The per-tile callback below beats it on
        # every COMPLETED tooltip tile (resetting the window — a reel that keeps completing tiles,
        # however slowly, is NEVER skipped) and polls it (a frozen tile that stalls past the budget
        # raises _cr.ReelDeadline, a BaseException that escapes still_runs' `except Exception`). The
        # grouping below catches it, HOLDS + QUARANTINEs the reel via on_reel_timeout and CONTINUEs,
        # so the sweep RETURNS and the rest of the owed reels drain this pass — instead of sitting
        # classified=0/pages=0 until the 240s river watchdog fires. Disarmed before the paid read
        # stage, which stays the watchdog's job so a legitimately long read is never false-killed.
        _reel_rid = os.path.basename(str(reel_dir))
        _dl = _cr.reel_deadline(_reel_rid, _reel_deadline_s)

        def _tile_progress():
            # one tooltip tile COMPLETED. poll FIRST (did THIS tile take longer than the budget to
            # complete — i.e. no progress for too long?), then beat (reset the window), then surface
            # the per-tile grouping count up to the console (the river watchdog sig reads it). A raise
            # here is _cr.ReelDeadline (BaseException), which escapes density and still_runs uncaught.
            _dl.check()   # REG-2271 vault per-tile no-progress poll (raises if this tile stalled past budget)
            _dl.beat()    # this tile completed = forward progress; reset the no-progress window
            if on_tile is not None:
                try:
                    on_tile()
                except Exception:
                    pass
        sessions_seen += 1
        sessions_examined.append(os.path.basename(os.path.normpath(str(reel_dir))).replace("reel_", "", 1))
        idx = _load_index(reel_dir)
        if idx is None:
            held.append({"name": None, "why": "reel %s has no readable index.json — held, not guessed"
                                              % os.path.basename(reel_dir)})
            continue
        sid = str(idx.get("sessionId") or os.path.basename(reel_dir))
        # the focus HE declared when he pressed MINI — trusted below in place of a classify call,
        # but only when it names an ownership surface this sweep actually owns.
        declared = _declared_surface(idx)
        frames = _frame_rows(idx.get("frames"))
        frames_seen += len(frames)
        # BORROWED grouping — chronicle_retro owns STILL_MAX_DIFF / MIN_RUN_FRAMES and the run logic.
        # v3076 — MEMOISED, because the grouping is now computed twice per reel (split and
        # unsplit) and DEFAULT_SIG reads the image. Keyed per reel, so it cannot outlive the loop.
        _sig_memo = {}

        def sig_of(n, _d=reel_dir):
            _dl.check()   # REG-2271 vault per-frame no-progress poll (did the PREVIOUS unit stall past
                          # budget?) — runs once per frame regardless of tooltip cache state.
            if n not in _sig_memo:
                _sig_memo[n] = sig(os.path.join(_d, n))
            # REG-2271 — SURFACE PER-FRAME GROUPING PROGRESS UP, unconditionally, so _VAULT_JOB's
            # groupTiles advances on a cache-HIT frame too. On a PRIMED _TOOLTIP_MEMO (vault_scan_cost
            # primes his whole corpus) every _tip_of returns at the cache-hit branch and _tile_progress
            # — the ONLY other on_tile source — NEVER fires; without this call the control_app river
            # watchdog's sig would FREEZE through a healthy primed grouping and, under the phase-scoped
            # grouping bound, FALSE-KILL it (discarding his footage — THE hard constraint). The
            # in-thread no-progress window is beaten per frame by the tooltip look itself (the cache-hit
            # beat in _tip_of, or the per-tile beat in _tile_progress on a miss), so the deadline is not
            # beaten here; this is the heartbeat the OUT-OF-THREAD watchdog reads. [[heart-first]]
            if on_tile is not None:
                try:
                    on_tile()
                except Exception:
                    pass
            return _sig_memo[n]
        # ══ v2396 — SPLIT THE RUN ON THE TOOLTIP, NOT ONLY ON THE GRID ═══════════════════════
        # MEASURED on reel_s_1788099914191_40921: 20 frames, all carrying an open stash panel,
        # median consecutive sig_diff 0.0000, collapsed to ONE run, ONE page read, ZERO rows — while
        # 16 of those 20 frames carried a tooltip in SIX DISTINCT POSITIONS. He hovered slot to
        # slot; the grid behind never changed, and sig_diff runs over the whole frame where the
        # static grid dominates. Six items became one page became nothing.
        #
        # With the split: 1 run -> 7 runs, 1 candidate page -> 4. The control reel (7 frames, ZERO
        # tooltips) is unchanged at 1 -> 1, so it splits on evidence and leaves the rest alone.
        #
        # ⚠ MEMOISED PER REEL. locate() measured at 0.239 s/frame cold on 40 real frames; the cache
        # brought a 20-frame reel to +4s total. It is a crop and a text-density pass — no model
        # call — but it must never run corpus-wide (15,956 frames would be ~64 minutes).
        # ⚠ AND A FAILED LOOK IS UNKNOWN, NOT "no tooltip". still_runs breaks the run on an
        # exception rather than welding two screens together. [[unknown-stays-unknown]]
        # ⚠ v2398 — THE MEMO IS MODULE-SCOPED, AND THAT IS THE FIX FOR THE SLOW QUOTE.
        # _vault_scan_cost_inner — the FREE PASS he consults BEFORE agreeing to spend — calls this
        # same sweep(), deliberately, because "both halves of a price must name the same thing"
        # (v1834) and v1596's scar was a quote that under-quoted by skipping the read stage.
        # So v2397's tooltip split ran inside the quote too, and MEASURED it took the quote from a
        # few seconds to over THREE MINUTES with no output. A number he waits three minutes for is
        # a number he stops consulting.
        #
        # A per-call dict made the quote and the run each pay in full, and the quote is almost
        # always followed by the run. Keyed on (size, mtime) — the same shape
        # stash_screen_open_cached already proves out — so the second pass is nearly free.
        # ⚠ NEVER on path alone: a reel directory is written to WHILE it is being filmed, and a
        # memo that ignores mtime serves a stale verdict for a frame that changed.
        def _tip_of(n, _d=reel_dir):
            p = os.path.join(_d, n)
            try:
                st = os.stat(p)
                key = (p, int(st.st_size), int(st.st_mtime))
            except OSError:
                key = None
            if key is not None and key in _TOOLTIP_MEMO:
                # REG-2271 — a cache HIT is a COMPLETED tooltip look (a dict lookup; it cannot freeze),
                # so it is forward progress and beats the no-progress window. On a PRIMED memo every
                # _tip_of lands here and locate() (which beats via _tile_progress) never runs; without
                # this beat the window would see no tile heartbeat at all for the frame. sig_of also
                # beats per frame, so this is the belt to that suspenders — and it keeps a frame that is
                # tooltip-looked more than once honest. [[heart-first]] [[the-unjoined-end]]
                _dl.beat()
                return _TOOLTIP_MEMO[key]
            import tooltip_find as _tf
            # REG-2271 — hand the per-tile heartbeat down so density beats/polls the no-progress
            # deadline once per completed tile (see _tile_progress). A cache HIT returns above without
            # locate(), which is correct: a memoised look did no OCR work, so it owes no heartbeat.
            r = _tf.locate(p, on_tile=_tile_progress)
            v = r[0] if isinstance(r, tuple) else r
            if key is not None:
                if len(_TOOLTIP_MEMO) >= _TOOLTIP_MEMO_MAX:
                    _TOOLTIP_MEMO.clear()     # coarse, bounded, never stale
                _TOOLTIP_MEMO[key] = v
            return v
        try:
            runs = _cr.still_runs(frames, sig_of, tooltip_of=_tip_of)
            cands = _cr.candidate_runs(runs, min_frames=MIN_RUN_FRAMES)
        except _cr.ReelDeadline as _rd:
            # REG-2271 — this reel's grouping made NO progress for the budget (a frozen tooltip pass).
            # HOLD it with a machine-readable reason and QUARANTINE it via on_reel_timeout so the lane
            # does not re-own it every tick; CONTINUE so the rest of the owed reels still drain this
            # pass and the sweep RETURNS (running clears without the 240s watchdog). No read was paid
            # here (classified=0/pages=0), so nothing partial is banked. [[the-unjoined-end]] [[heart-first]]
            held.append({"name": None, "why": "REG-2271: %s" % _rd})
            # REG-2271 (GrokBot #250 review, BLOCKING #1+#2) — this reel was appended to
            # sessions_examined at the top of the loop BEFORE grouping, but blowing the deadline means
            # it was NOT examined to completion. Left in sessionsExamined, a multi-reel pass would seal
            # it examinedEmpty (control_app seals EVERY sessionsExamined reel once another reel is
            # examined-empty) and RELEASE its footage, and would clear its banked resume record. A
            # frozen reel is HELD / UNKNOWN, never "looked, nothing here" — so take it back out.
            # [[unknown-stays-unknown]] [[the-unjoined-end]]
            try:
                sessions_examined.remove(
                    os.path.basename(os.path.normpath(str(reel_dir))).replace("reel_", "", 1))
            except ValueError:
                pass
            if on_reel_timeout is not None:
                try:
                    on_reel_timeout(_reel_rid, str(_rd))
                except Exception:
                    pass
            continue
        finally:
            _dl.disarm()   # bound ONLY grouping; the paid read stage below (and the memoised _unsplit
                           # regroup) is the 240s river watchdog's job, never false-killed here
        # ⚠⚠ v3075 — THE SPLIT MAY ONLY EVER ADD. v2396 splits a still run on the TOOLTIP so a
        # hover-by-hover pass stops collapsing into one page, and it says of itself that it
        # "splits on evidence and leaves the rest alone". It does not: MIN_RUN_FRAMES is a
        # STILLNESS floor calibrated on UNSPLIT runs, and applying it to the fragments can discard
        # every candidate a reel had.
        #
        # MEASURED 2026-09-13 on reel_s_1788099999528_42457 — 4 frames, 1 run, 1 candidate before
        # the split; 2 runs and ZERO candidates after it, because both fragments fall under the
        # 3-frame floor. Nothing was ever offered to the reader: a forced re-sweep of that reel
        # reported reelsDone=1/1 with pagesRead=0, classify called 0 times, reader 0 times. The
        # frames are fine — the free structural gate opens all 4 as `shared`, and the survey counts
        # 4 panels. A short reel with a hover in it was simply unreadable, permanently.
        #
        # So: if the split leaves nothing, fall back to the grouping that existed before it. The
        # split can then only ever ADD pages, which is what it was introduced to do. The control
        # case v2396 cites (7 frames, zero tooltips, 1 -> 1) never reaches this branch at all.
        # [[feedback-threshold-above-the-ceiling]]
        # ⚠⚠ v3076 — "ONLY EVER ADD" MEANS NEVER FEWER, NOT MERELY NEVER ZERO. v3075 fell back
        # only `if not cands`, which the cross-family second eye called out on the shipped diff:
        # the law is named "may only ever add pages" and the code restored solely at zero.
        # REPRODUCED before believing it — 8 frames as two held screens of 4, a hover moving
        # inside the FIRST screen only:
        #     no split      runs [4, 4]     -> 2 candidates
        #     tooltip split runs [2, 2, 4]  -> 1 candidate
        # Candidates fell 2 -> 1 without ever reaching zero, so the old guard never fired and a
        # whole held screen was never read. Comparing the COUNTS makes the grouping monotone,
        # which is what the name claimed all along. [[review-after-ship]]
        _unsplit = _cr.candidate_runs(_cr.still_runs(frames, sig_of), min_frames=MIN_RUN_FRAMES)
        if len(_unsplit) > len(cands):
            cands = _unsplit
        read_this_reel = False
        # v1792 — RE-LOOK BUCKETS. Candidate runs are already separated by a signature change, so a
        # multi-minute gap between two of them is the panel left and returned to rather than one
        # frozen screen. Each gap opens a new bucket, and the bucket is what the KEEP bar counts.
        # Compared against the PREVIOUS RUN'S END, not the reel's start, so three looks spread over
        # an hour are three buckets and three quick glances in one minute are still one.
        _wbucket = 0
        _prev_end = None
        for run in cands:
            _st = run.get("start_ts") or 0
            if _prev_end is not None and _st and (_st - _prev_end) >= REOPEN_GAP_MS:
                _wbucket += 1
            _prev_end = run.get("end_ts") or _st or _prev_end
            _wkey = "%s#%d" % (sid, _wbucket)
            names = run.get("frames") or []
            probe, _dead = _cr.live_probe(names, lambda n, _d=reel_dir: os.path.join(_d, n))
            if probe is None:
                skipped += 1
                held.append({"name": None,
                             "why": "a %d-frame run in %s was BLANK all the way through — the window "
                                    "was grabbed with nothing on it; that is a capture fault, not an "
                                    "empty stash" % (len(names), sid)})
                continue
            # ── v1603 — A DECLARED FOCUS IS NOT A GUESS. ─────────────────────────────────
            # When he presses MINI he TELLS the app what he is parked on, and that stamp lands in
            # the reel's index.json. Until now the sweep used it only to read mini reels first;
            # every run still paid a classify call to rediscover a fact already on disk, and could
            # still get it wrong — a rune tab misread as "inventory" files his runes in the wrong
            # lane, which merge-max then makes permanent.
            #
            # This is the same trade chronicle_retro.sweep_frames() already makes for the live
            # lane: "a recorded visit already knows two things a blind sweep has to pay a model to
            # discover". Cheaper AND more accurate, which is rare enough to be worth saying out
            # loud — the model call it removes was the one that could be wrong.
            #
            # TRUSTED NARROWLY, on purpose: only when the reel declares a focus that IS an
            # ownership surface. A chronicle-focused mini is NOT an ownership surface, so it falls
            # through to the classifier here and is read by the chronicle sweep instead.
            if declared:
                surface = declared
                trusted += 1
            else:
                classified += 1
                surface = _surface_of(classify(os.path.join(reel_dir, probe)))
                if surface is not None:
                    answered += 1
                else:
                    # ── v2028 — ONE OCCLUDED FRAME MUST NOT CONDEMN THE RUN ──────────────────
                    # THE ROOT CAUSE OF THE WHOLE "no name to be had" STORY, and it is the exact
                    # inverse of what anyone would guess.
                    #
                    # stash_screen_open identifies a stash panel by OCR-ing the TAB CHROME
                    # (PERSONAL / SHARED / GEMS / MATERIALS / RUNES). A D2R hover tooltip is drawn
                    # ON TOP of that row. So the gate rejects, with perfect consistency, exactly
                    # the frames that contain a readable item NAME — and keeps the ones showing a
                    # bare grid, which prints no names at all.
                    #
                    # LOOKED AT, not inferred. Two frames the gate refused:
                    #   f_1784984195842.jpg  "Sullied Grand Charm of Blight / Required Level: 42 /
                    #                         +1 to Eldritch Skills (Warlock Only)" — its
                    #                        "Ctrl + Left Click to Move to Inventory" line sits
                    #                        straight across the tab row.
                    #   f_1787508818939.jpg  "Marshal's Amulet / +3 to Offensive Auras" — same,
                    #                        "Shift + Left Click to Equip" over GEMS/MATERIALS.
                    #
                    # MEASURED across his four stash reels: 16 of 170 in-panel frames (9%, and 10%
                    # on each of the two best reels) are refused while BRACKETED by frames the gate
                    # resolves — i.e. the panel is provably still open. Every one of those is a
                    # frame he was hovering on.
                    #
                    # A still-run is ONE HELD SCREEN by construction. So a single frame's occluded
                    # tab row cannot be evidence about the run; any frame that resolves settles it.
                    # This is FREE — classify here is a crop and an OCR, no model call — and it is
                    # bounded at 3 extra looks so a genuinely non-stash run stays cheap.
                    #
                    # It rescues the RIGHT frames too: the reader below walks _distinct(names), so
                    # once the run is admitted the tooltip frames are read like any other.
                    # [[the-unjoined-end]] [[feedback-suspect-the-instrument]]
                    # ⚠ THE RESCUE MUST BE FREE. The first cut of this retried `classify`, and
                    # `classify` on the console is the FREE gate followed by a PAID model call
                    # (control_app._classify: `if stash_screen_open(p) is None: return None` then
                    # `_tv.claude_read(p)`). Three retries per rejected run would have tripled the
                    # classify spend on exactly the runs that are NOT stash panels — a cost
                    # regression wearing a fix's clothes.
                    #
                    # panel_gate is the free half on its own (a crop and an OCR), and v2023 already
                    # threads it in for the ordering. So: ask the FREE gate whether any neighbour
                    # sees the panel, and only then pay ONE classify, on that frame.
                    _alts = [n for n in names if n != probe]
                    if _alts and panel_gate is not None:
                        _step = max(1, len(_alts) // 4)
                        for _alt in _alts[::_step][:4]:
                            try:
                                _seen = panel_gate(os.path.join(reel_dir, _alt)) is not None
                            except Exception:
                                _seen = False
                            if not _seen:
                                continue
                            classified += 1
                            surface = _surface_of(classify(os.path.join(reel_dir, _alt)))
                            if surface is not None:
                                answered += 1
                                rescued += 1
                            break        # one paid look is the whole budget for a rescue
            if surface is None:
                # Law 4: unclassifiable is HELD, never guessed into a lane.
                skipped += 1
                held.append({"name": None,
                             "why": "a still run in %s (frame %s) could not be classified — held "
                                    "rather than guessed onto a shelf" % (sid, probe)})
                continue
            if surface not in OWNERSHIP_SURFACES:   # unreachable via _surface_of; kept as the law
                skipped += 1
                continue
            lane_default = SURFACE_LANE.get(surface, "stash")
            # A held-still panel is ONE page; a SCROLLED panel is several. _distinct is the chronicle's
            # calibrated "same pixels?" test — borrowed so the two sweeps pay alike.
            # ── v2032 — THE DEDUPE THAT MAKES A HELD GRID CHEAP MAKES A HOVER PASS INVISIBLE ──
            # _distinct keeps only frames that LOOK different from the last kept one, so a panel he
            # held still costs ONE read instead of forty. Exactly right for a grid — and exactly
            # inverted for a tooltip pass, where the panel is identical frame to frame and only a
            # small tooltip rectangle changes. jpeg_sig fingerprints the WHOLE frame, so that
            # rectangle moves it far less than the default max_diff=0.06 tolerates.
            #
            # MEASURED on his tooltip reel, the 73-frame run that holds all 18 of its tooltips:
            #     vault today (defaults)                  2 pages,  1 tooltip
            #     chronicle's max_diff=0.002             36 pages,  8 tooltips
            #     chronicle's full tuning                72 pages, 18 tooltips
            # So one name reached him out of eighteen chances.
            #
            # COPYING THE CHRONICLE'S NUMBERS IS THE WRONG FIX: 72 of 73 frames is not a dedupe at
            # all, and the tally lanes would pay it too. The vault lane only cares about frames that
            # carry a NAME, and those are identifiable FOR FREE — a tooltip covering the tab strip
            # is exactly what makes the gate answer the GENERIC "stash" rather than a tab (v2028).
            #
            # So: the cheap dedupe still decides the GRID pages, and every tooltip frame is added on
            # top. ~20 reads instead of 72, and 18 of 18 names instead of 1. Chronological order is
            # preserved so witnesses read in the order he actually hovered them. [[copy-drift]]
            _pages = list(_cr._distinct(names, sig_of))
            if panel_gate is not None:
                _have = set(_pages)
                for _n in names:
                    if _n in _have:
                        continue
                    try:
                        if panel_gate(os.path.join(reel_dir, _n)) == "stash":
                            _pages.append(_n)
                            _have.add(_n)
                    except Exception:
                        continue
                _order = {n: i for i, n in enumerate(names)}
                _pages.sort(key=lambda n: _order.get(n, 1 << 30))
            # v2239 (#45) — the crop that NAMED it. `_prev_page` is the frame before this one in
            # the run, which is what a tooltip is differenced against. Held outside the loop so a
            # skipped/refused page still advances it — otherwise a refusal would silently make the
            # next crop a diff across two hovers instead of one.
            _prev_page = None
            _crop_root = os.path.join(os.path.dirname(reel_dir), CROP_DIR)
            for name in _pages:
                if name in _resume_frames:
                    # #130 — banked by an earlier stopped pass; its sighting is already seeded. Skip
                    # the paid read, but keep the crop-diff anchor moving across the resume boundary.
                    _prev_page = name
                    continue
                path = os.path.join(reel_dir, name)
                # REG-2915 (#158.7) - the frame-difference crop is today's crop for an item the read gave no tooltip box; it
                # is asked once per frame, and only when such an item arrives
                _diff_prev, _diff_crop = _prev_page, []
                _prev_page = name
                resp = reader(path, surface)
                _read_frames.add(name)   # #130 — the reader was called (paid); never re-read on a resume
                if not isinstance(resp, dict) or resp.get("note"):
                    skipped += 1
                    held.append({"name": None,
                                 "why": "the reader refused %s in %s (%s)"
                                        % (name, sid, (resp or {}).get("note") if isinstance(resp, dict)
                                           else "no answer")})
                    continue
                pages_read += 1
                read_this_reel = True
                page_conf = _conf_of(resp.get("conf"))
                ts = resp.get("ts") if isinstance(resp.get("ts"), (int, float)) else run.get("end_ts")
                for raw in (resp.get("items") or []):
                    item = normalize_item(raw, surface, lane_default, page_conf)
                    if item is not None:
                        # v1885 — fold BEFORE the key is formed, or two spellings of one item are
                        # two piles of evidence and neither may reach two witnesses
                        _canon = _fold(item["name"])
                        if _canon and _canon != item["name"]:
                            folded_names[item["name"]] = _canon
                            item["name"] = _canon
                    if item is None:
                        unsure.append({"name": None,
                                       "why": "the reader returned a row with no name on %s in %s — "
                                              "nothing was invented for it" % (name, sid)})
                        continue
                    _lane_said = item["lane"]
                    item["lane"], _pl = lane_by_point(item["lane"], item.get("xy"), resp.get("xy"))   # v3554 · REG-1911
                    # REG-2915 (#158.7) - THE CROP IS CUT FROM THE TOOLTIP BOX THE READ RETURNED. A read with no box behaves as
                    # before (the frame-difference crop, or why there is none) and says the box is UNKNOWN; never a
                    # full-frame crop.
                    if item.get("tip"):
                        _crop_rel, _crop_why = _crop_from_box(reel_dir, name, item["tip"], resp.get("xy"), _crop_root)
                        _crop_from = "tooltip box" if _crop_rel else None
                    else:
                        if not _diff_crop:
                            _diff_crop.append(_crop_for(reel_dir, name, _diff_prev, _crop_root))
                        _crop_rel, _crop_why = _diff_crop[0]
                        _crop_from = "frame difference" if _crop_rel else None
                        if not _crop_rel:
                            _crop_why = "the read gave no tooltip box (UNKNOWN); " + str(_crop_why or "no reason")
                    sight = {"session": sid, "witness": _wkey, "frame": name, "lane": item["lane"],
                             "conf": item["conf"], "count": item["count"], "kind": item["kind"],
                             "ts": ts,
                             # v3369 — THE VALUE FACTS TRAVEL WITH THE SIGHTING. v3368 taught the
                             # prompt to ask for sockets/eth/quality and normalize_item to parse
                             # them, and then this dict dropped all four: the reader SAW them, used
                             # sockets to judge junk, and banked a bare name. Six links, two built.
                             # They belong on the SIGHTING, not the row — see _variants_of.
                             "sockets": item.get("sockets"), "eth": item.get("eth"),
                             "quality": item.get("quality"), "promptVer": item.get("promptVer"),
                             # v2239 — the picture, or WHY there is none. Never silently absent:
                             # "no tooltip on this frame" and "the crop store is full" are
                             # different answers and only one of them is about his footage.
                             "crop": _crop_rel, "cropWhy": None if _crop_rel else _crop_why,
                             "cropFrom": _crop_from,   # REG-2915 - which way the picture was cut
                             # v3554 (#146 3b) — WHERE THIS LOOK SAW IT: the frame point and its cell, or why
                             # there is none. In the literal, so the field census reads them like every other key.
                             "point": _pl["point"], "cell": _pl["cell"], "cellWhy": _pl["why"],
                             # REG-1911 - what the reader SAID, kept beside where it was filed, when the two differ
                             "laneSaid": _lane_said if _lane_said != item["lane"] else None}
                    key = (item["name"], item["lane"])
                    evidence.setdefault(key, []).append(sight)
                    if item["throwOut"]:
                        throw_flags.setdefault(key, []).append(dict(sight, why=item["throwWhy"]))
                # #130 — a read is banked; offer a checkpoint (stop here if a build waits). AFTER the
                # sighting is in `evidence`, so a stop never records a frame whose read it did not keep.
                _maybe_checkpoint(sid)
        if read_this_reel:
            sessions_read.append(sid)

    if folded_names:
        _eg = ", ".join("%s -> %s" % kv for kv in sorted(folded_names.items())[:3])
        print("   \U0001f9f9 %d reader name(s) folded onto the roster (%s)"
              % (len(folded_names), _eg))
    # ── v2051 — FOLD IN WHAT EARLIER SWEEPS SAW, BEFORE THE GATE RUNS ────────────────────────
    # `prior_seen` is the caller's record of sightings that did NOT ground last time: rows shaped
    # like the `unsure` rows this function emits. Folding them into `evidence` is what makes the
    # two-witness bar mean "twice EVER" instead of "twice inside one sweep run".
    #
    # THE GATE IS NOT TOUCHED. Whether any of this grounds is still decided by gate() on DISTINCT
    # SESSIONS and the confidence floor, so a prior sighting can only ever supply a session id that
    # gate() then has to accept on its own terms. A repeat of the SAME session adds nothing, because
    # witnesses are counted as distinct sessions (law 2).
    #
    # LAW 5 IS INTACT: this reads what it was handed and writes nothing. The console owns the file.
    _folded_prior = 0
    for _row in (prior_seen or []):
        if not isinstance(_row, dict):
            continue
        # REG-2036 (#212 F14) - an earlier sighting passes the SAME exact fold as a fresh read, so a row stored as
        # "Dwarf Star Ring" before the base-line fold existed corroborates "Dwarf Star" instead of living beside it
        _nm = _fold(str(_row.get("name") or "").strip())
        _ln = str(_row.get("lane") or "").strip().lower()
        if not _nm or _ln not in LANES:
            continue
        _key = (_nm, _ln)
        _have = {(w.get("session"), w.get("frame")) for w in evidence.get(_key, [])
                 if isinstance(w, dict)}
        for _w in (_row.get("witnesses") or []):
            if not isinstance(_w, dict):
                continue
            if (_w.get("session"), _w.get("frame")) in _have:
                continue        # the same sighting twice is repetition, not corroboration
            evidence.setdefault(_key, []).append(dict(_w))
            _folded_prior += 1
    if _folded_prior:
        print("   \U0001f9e9 folded %d earlier sighting(s) that had not grounded yet"
              % _folded_prior, flush=True)

    owned, throw_out = [], []
    for key in sorted(evidence, key=lambda k: (k[1], k[0].lower(), k[0])):
        ev = evidence[key]
        v = gate(ev, KEEP_CONF_FLOOR, KEEP_MIN_WITNESSES)
        if not v["pass"]:
            # Law 2: one witness is never `owned`. It is remembered as unsure so a later session can
            # corroborate it — the accumulator's whole point.
            #
            # v2051 — AND NOW THE ROW CAN ACTUALLY CARRY THAT. Until now an unsure row was
            # {name, why}: no lane, no witnesses, no session, no confidence. `_rows_of` absorbs only
            # `owned`, so nothing downstream could ever pair a sighting from THIS run with one from
            # the next. The sentence above described an accumulator that was not being fed.
            #
            # Measured 2026-08-24 across two real sweeps of his reels: TEN items were unsure in
            # BOTH — Enigma, Dwarf Star, Bone Visor, Obsession among them — each seen at least once
            # in each run, and every one of those sightings discarded. The two-witness bar was in
            # practice "twice inside one sweep", never "twice ever".
            #
            # The evidence rides along; the GATE is untouched. Whether this grounds is still decided
            # by `gate()` on distinct sessions and the confidence floor.
            # v3364 (#60) — WHAT THE GAME'S OWN TABLES SAY THIS NAME IS. Measured over his 43
            # real unsure rows: GRAIL 14 · BASE 12 · MAGIC 8 · RARE 4 · UNKNOWN 5. The five
            # refusals are honest — `scarab` is one of exactly SIX rare keys with no display
            # string in either of the game's string tables, so `Storm Scarab` cannot be named from
            # this data and says so instead of being guessed into a lane.
            _vk, _vw = _vocab_of(key[0])
            unsure.append({"name": key[0], "why": "%s in %s — %s" % (key[0], key[1], v["why"]),
                           "lane": key[1], "kind": "item",
                           "vocab": _vk, "vocabWhy": _vw,
                           "conf": v.get("bestConf"),
                           "sessions": v.get("sessions") or [],
                           "witnesses": [dict(e) for e in ev if isinstance(e, dict)],
                           "variants": _variants_of(ev, key[0]),
                           "lastSeenTs": max([e.get("ts") or 0 for e in ev] or [0]) or None})
            continue
        owned.append(_owned_row(key, ev))
    _is_grail = _grail_guard()
    for key in sorted(throw_flags, key=lambda k: (k[1], k[0].lower(), k[0])):
        ev = throw_flags[key]
        # v1903 — A GRAIL NAME IS NEVER A THROW-OUT, at any confidence, from any number of
        # recordings. Every other guard on this lane is about HOW MUCH evidence a throw needs;
        # none of them was about WHAT MAY BE THROWN, and "is this junk" was the reader's opinion
        # alone. A unique or set piece is the thing this whole project exists to collect.
        if key[1] in LOCKED_LANES:
            # v2075 — the LANE decides, before any evidence is weighed. He is wearing it or
            # carrying it; that is not a shelf to tidy.
            held.append({"name": key[0],
                         "why": "throw-out SUGGESTION refused for %s \u2014 it is on his %s, a "
                                "LOCKED lane. He said it plainly: equipment and inventory are never "
                                "to be told to move. No number of recordings promotes a lane he has "
                                "already ruled on" % (key[0], key[1].upper())})
            continue
        if _is_grail is not None and _is_grail(key[0]):
            held.append({"name": key[0],
                         "why": "throw-out SUGGESTION refused for %s in %s \u2014 it is on his GRAIL "
                                "ROSTER. Evidence is not the question here: a named unique or set "
                                "piece is never junk, however sure the reader was"
                                % (key[0], key[1])})
            continue
        # Law 3: the STRICTER bar, on both axes. Single-session evidence can never clear it.
        # law 3 — the throw bar counts RECORDINGS, never re-looks. A single reel, however many times
        # he re-opened the panel in it, can never suggest binning an item.
        v = gate(ev, THROWOUT_CONF_FLOOR, THROWOUT_MIN_WITNESSES,
                 witness_field="session", witness_noun="recording")
        if not v["pass"]:
            held.append({"name": key[0],
                         "why": "throw-out SUGGESTION withheld for %s in %s — %s. There is no "
                                "un-throw in Diablo, so this bar is higher than the keep bar on "
                                "purpose" % (key[0], key[1], v["why"])})
            continue
        whys = sorted({str(e.get("why") or "").strip() for e in ev if e.get("why")})
        throw_out.append({"name": key[0], "lane": key[1],
                          "why": "; ".join(whys) or "the reader flagged it as junk",
                          "conf": round(v["bestConf"], 3), "witnesses": _witness_rows(ev),
                          "suggestion": True})   # never automatic — the Vault manager ASKS him

    totals = {"sessionsSeen": sessions_seen, "framesSeen": frames_seen, "classified": classified,
              "pagesRead": pages_read, "skipped": skipped,
              # v2020 — how many of those classify calls came back with an actual surface.
              "classifierAnswered": answered,
              # v2028 — runs saved from a tooltip-occluded probe frame.
              "occludedRescued": rescued,
              # v1603 — classify calls SKIPPED because he had already said what he was looking at.
              # Reported rather than silently pocketed: "9 classifies" and "9 classifies + 4 you
              # told us" are different facts about the same sweep.
              "trustedFocus": trusted}
    # v2236 — THE SHADOW RIDES ALONG, exactly as the chronicle sweep attaches its own. Without this
    # the Wilson lane is two halves each built right and never joined: gate_shadow() computes a
    # verdict nobody reads, and the ledger accumulates nothing, and BOTH ends look wired.
    # [[the-unjoined-end]] [[plumbing-with-no-tap]]
    #
    # ⚠ The failure is RECORDED, never swallowed. A `why` on the except branch is what lets
    # _shadow_bank tell "this sweep saw nothing scoreable" from "this lane has crashed on every
    # sweep since it shipped" — collapsing those is how a dead lane reports "agrees so far" forever.
    try:
        _piles = {}
        for (_nm, _ln), _ev in (evidence or {}).items():
            _piles.setdefault(str(_nm), []).extend(_ev or [])
        _shadow = shadow_scores(_piles, "keep")
    except Exception as _e:
        _shadow = {"scored": 0, "disagreements": [], "names": [],
                   "why": "the vault shadow lane could not score this sweep: %s" % str(_e)[:120]}
    return {"ok": True, "generatedTs": int(time.time() * 1000), "why": _verdict(totals, owned, unsure),
            "sessionsRead": sorted(set(sessions_read)),
            "sessionsExamined": sorted(set(sessions_examined)),   # v2306 — opened, not necessarily read
            "shadow": _shadow,
            "owned": owned, "throwOut": throw_out, "unsure": unsure, "held": held, "totals": totals}


def _verdict(totals, owned, unsure):
    """WHY an empty sweep is empty. Four different nothings, exactly as the chronicle sweep does it —
    collapsing them would send him debugging a reader when what he needs is to open his stash."""
    if owned:
        return ("%d item(s) grounded across %d session(s) from %d page(s) — %d more need a second "
                "session to corroborate." % (len(owned), totals["sessionsSeen"], totals["pagesRead"],
                                             len(unsure)))
    if not totals["sessionsSeen"]:
        return "There is no sealed footage to sweep yet — record a mini stash session first."
    # v1783 — THIS BRANCH ACCUSED HIS CAMERA FOR THE READER'S FAILURE. classified counts PAID
    # classifier calls, and the v1603 trusted-focus path never increments it: when he presses MINI
    # the focus is taken as a declaration and the classifier is skipped entirely. So for any mini
    # reel with a declared focus this is STRUCTURALLY 0, and the sweep answered "footage of moving,
    # not of looking at a stash" for a reel it had read pages from — sending him to steady the
    # camera when the reader is the thing to look at. Found by an adversarial review of this lane.
    if not totals["classified"] and not totals.get("trustedFocus"):
        return ("%d reel(s) held no screen still long enough to be worth reading — that is footage of "
                "moving, not of looking at a stash." % totals["sessionsSeen"])
    if not totals["classified"] and totals.get("trustedFocus") and not totals["pagesRead"]:
        return ("%d reel(s) carried a declared focus so no screen was classified, and no page was "
                "read from them — the reader, not the footage, is what to check."
                % totals["sessionsSeen"])
    if not totals["pagesRead"]:
        # ── v2020 (REG-382) — "NOBODY LOOKED" WAS BEING PRINTED AS "WE LOOKED AND FOUND NOTHING" ──
        # This branch used to fire on `pagesRead == 0` alone and announce that NONE of his stills was
        # a stash panel, and that this "is not a reader failure". Both halves were false whenever the
        # classifier never answered — and the FREE --cost pass installs `classify=lambda p: None`,
        # a classifier that refuses everything BY DESIGN, so the free pass was structurally
        # guaranteed to print it.
        #
        # MEASURED, 2026-08-23: `vault_retro.py --cost` reported "84 still screen(s) ... NONE was a
        # stash, inventory or equipment panel" over the same corpus in which vault_doctor finds 16
        # stash panels in 238 sampled frames, and in which frame f_1784984209709 carries a COMPLETE
        # Annihilus tooltip that a paid chronicle sweep had already read. Three witnesses against it.
        #
        # This is the most expensive possible wrong answer: the cost pass is what you run BEFORE
        # deciding to pay, and it told him his footage held nothing and the reader was blameless.
        # A sweep that has never run is why vault_swept.json has never existed.
        # [[unknown-stays-unknown]] [[feedback-contradiction-is-the-finding]]
        if not totals.get("classifierAnswered"):
            # v2024 — DO NOT NAME A CAUSE THIS FUNCTION CANNOT SEE. The first cut asserted the
            # --cost stub, which is only ONE way to reach this state; the first REAL sweep hit it
            # too, from a live classifier that refused every still. Naming the wrong cause sends
            # him to check the wrong thing, which is the same failure as the verdict this replaced.
            return ("%d still screen(s) were examined and the classifier answered about NONE of "
                    "them, so whether any is a stash panel is UNKNOWN — this says nothing about "
                    "the footage. Two things reach this state: the free --cost pass, which installs "
                    "a classifier that refuses everything by design, or a real sweep whose "
                    "classifier refused every still. Check which before concluding anything."
                    % totals["classified"])
        return ("%d still screen(s) were examined across %d reel(s), the classifier answered about "
                "%d of them, and NONE was a stash, inventory or equipment panel — there was nothing "
                "to read. This is not a reader failure."
                % (totals["classified"], totals["sessionsSeen"], totals["classifierAnswered"]))
    if unsure:
        return ("%d page(s) were read and every name so far has only ONE session behind it — open the "
                "same stash on camera once more and they ground." % totals["pagesRead"])
    return ("%d page(s) were read and produced no items. This one is the reading itself, not the "
            "footage." % totals["pagesRead"])


# ── APPLY (law 5: shapes, never writes) ─────────────────────────────────────────

def apply_payload(proposal):
    """Shape a proposal for the ONE existing apply path. It does not write and cannot write.

    The caller hands this to window.chronicleApply — the same function his hand-tick uses — so the
    write inherits the date stamp, the merge-max and the undo bar. A second write path is a second
    thing that drifts, and this module deliberately does not have one.

    THROW-OUTS ARE NOT IN `items`. They ride along as `suggestions`, flagged as suggestions, because
    nothing this module produces may bin anything on its own.
    

    ⚠ v1986 — WITNESSES SHIP AS ROWS, NOT AS A COUNT. This used to emit
    `"witnesses": len(...)`, turning the list _witness_rows builds into an int. Every reader on
    the board treats it as an ARRAY — `witnesses[0].session`, `witnesses.length` — so the
    production payload never looked like what the board expects, and a JS `for (i < w.length)`
    over a number simply never ran. That silently disabled REG-339's 3-session equipment lock
    on the only path that actually runs: it locked fine against hand-made arrays in tests and
    could not fire on a real apply. Measured: owned row `witnesses` is list len 3, the shaped
    item was int 3.

    The count survives as `witnessCount` for any surface that wants a number. Losing the rows
    also cost provenance — reel and frame live on those dicts and nowhere else in `items`."""
    p = proposal if isinstance(proposal, dict) else {}
    if not p.get("ok"):
        return {"ok": False, "source": "vault-retro", "mode": "merge-max", "items": [],
                "suggestions": [], "why": p.get("why") or "no proposal to apply",
                "generatedTs": p.get("generatedTs")}
    # ⚠ #246 W1/W3 — THE VERDICT TRAVELS WITH THE WITNESSES. The board's one door (vaultFile) re-checks
    # every look itself, and its provenance row keeps the gate's own words and the Wilson bound, so
    # "why is this in my vault" is answered by the row, not re-derived. Computed here by the SAME
    # gate() the sweep used — never a second rule. [[copy-drift]]
    def _gate_of(r):
        try:
            g = gate([w for w in (r.get("witnesses") or []) if isinstance(w, dict)],
                     KEEP_CONF_FLOOR, KEEP_MIN_WITNESSES)
            # the Wilson lower bound of qualifying-of-seen looks: STAMPED for the provenance row,
            # decides nothing (the live gate reads no score — test_the_shadow_DECIDES_nothing)
            try:
                import confidence as _cf1
                _w = round(float(_cf1.wilson_lower(g.get("witnesses") or 0,
                                                   max(g.get("looksSeen") or 0, g.get("witnesses") or 0))), 3)
            except Exception:
                _w = None           # could not be computed — UNKNOWN, never a made-up 0
            return {"pass": bool(g.get("pass")), "why": g.get("why"), "looks": g.get("witnesses"),
                    "looksSeen": g.get("looksSeen"), "wilson": _w,
                    "floor": KEEP_CONF_FLOOR, "minLooks": KEEP_MIN_WITNESSES}
        except Exception as _ge:
            return {"pass": None, "why": "the gate could not be asked (%s)" % type(_ge).__name__}
    items = [{"name": r["name"], "lane": r["lane"], "kind": r.get("kind") or "item",
              "count": r.get("count"), "conf": r.get("conf"),
              "witnesses": [w for w in (r.get("witnesses") or []) if isinstance(w, dict)],
              "witnessCount": len(r.get("witnesses") or []),
              "lastSeenTs": r.get("lastSeenTs"),
              "gate": _gate_of(r)}
             for r in (p.get("owned") or [])]
    return {
        "ok": True,
        "source": "vault-retro",
        "mode": "merge-max",            # the receiving apply must raise counts, never lower them
        "readOnlyUntilApply": True,     # nothing has been written; this is a proposal he presses
        "generatedTs": p.get("generatedTs"),
        "sessionsRead": p.get("sessionsRead") or [],
        "items": items,
        "suggestions": [dict(t, automatic=False) for t in (p.get("throwOut") or [])],
        "unsure": p.get("unsure") or [],
        "held": p.get("held") or [],
        "totals": p.get("totals") or {},
        # v1996 — CARRY THE FREE EVIDENCE THROUGH. The sweep computes two things from the PIXELS,
        # at no cost, on frames the paid reader had to give up on:
        #   glimpsed    cells that are visibly occupied on a panel whose read named nothing (v1989)
        #   reconciled  the per-frame comparison of names against occupied cells, and `overRead`,
        #               the subset where the model named MORE than the panel can physically hold —
        #               the only fabrication signal this lane has (v1994)
        # Both were written onto the proposal and DROPPED HERE, so the board could not have rendered
        # them however much it wanted to. Konyo asked for exactly this: "i want it to visually render
        # the backend through the ledger visually so we can visually surgically fix anything needed."
        # A signal computed and never carried is the same defect as one computed and never read.
        # [[the-unjoined-end]]
        "glimpsed": p.get("glimpsed") or [],
        "reconciled": p.get("reconciled") or [],
        "overRead": p.get("overRead") or [],
        # v2004 — the ROOM (which squares never move, which are open floor) and the reason the pixel
        # lane went quiet if it did. Both were computed and then dropped here, which is the same
        # defect v1996 fixed for glimpsed/reconciled — committed again eight versions later, by me.
        "room": p.get("room") or None,
        "pixelLaneError": p.get("pixelLaneError") or "",
        # v2006 — how much footage has given up its information, and how close the disk is to the
        # floor below which ON AIR refuses to record. A report, never an instruction to delete.
        "retention": p.get("retention") or None,
        "why": p.get("why") or "",
    }


# ── CLI ─────────────────────────────────────────────────────────────────────────
# Print-only, like the chronicle sweep's. This module may never write, and a CLI that dropped a
# proposal file would break the law the whole arc rests on.
def rank_by_panel(reel_dirs, panel_gate, sample_every=8, cap=24):
    """Order reels by how likely a vault sweep is to find anything in them. -> [(dir, density)]

    ★ THE JOIN THIS EXISTS FOR, 2026-09-15. panel_density's own docstring already said why it is
    free: "which is why the sweep can afford to ask it about every reel before paying to read any
    of them." It was never asked. MEASURED on his machine: the sweeper took reels in directory
    order filtered only by "not already swept", so it spent 45 sessions on arbitrary footage, 36
    of them (80%) came back with nothing, and the THREE best stash-panel reels - one of them at
    100% density - had NEVER BEEN SWEPT. Meanwhile the stash bank held 12 keys against the
    chronicle bank's 8517 sightings.

    The chooser existed, the sweeper existed, and nothing joined them: the ranking was computed
    only inside a doctor row that PRINTS it. [[the-unjoined-end]] [[plumbing-with-no-tap]]

    ⚠ ONE IMPLEMENTATION, TWO CALLERS. console_doctor sorted this inline; a second copy in the
    sweep path would drift the first time the tie-break changed, and the console would then hold
    two answers to "which reel should be read next". [[copy-drift]]

    ⚠ UNREADABLE SORTS LAST, NEVER FIRST - panel_density returns 0.0 rather than raising, so a
    reel we cannot measure can never be promoted ahead of one we can. Ties keep their original
    order (sorted() is stable), so this only ever REORDERS by evidence and never invents one.
    """
    out = []
    for d in (reel_dirs or []):
        try:
            v = panel_density(d, panel_gate, sample_every=sample_every, cap=cap)
        except Exception:
            v = 0.0          # a gate that raises is not a reel that is empty
        out.append((d, float(v or 0.0)))
    return sorted(out, key=lambda kv: -kv[1])


if __name__ == "__main__":
    import console_safe  # noqa: F401  — emoji must survive a non-UTF-8 console
    import argparse

    ap = argparse.ArgumentParser(description="Vault accumulator: what the sealed reels say he owns.")
    ap.add_argument("--hist", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                   "frames", "hist"))
    ap.add_argument("--limit", type=int, default=None, help="only the N best reels")
    ap.add_argument("--cost", action="store_true",
                    help="FREE: group frames into runs and report what a real sweep WOULD cost")
    args = ap.parse_args()

    dirs = _cr.reel_dirs(args.hist)
    if args.cost:
        # the free pass: real grouping, a classifier that refuses everything, a reader that is never
        # reached. Nothing is read, nothing is charged, and the run/classify arithmetic is his own.
        res = sweep(dirs, sig=DEFAULT_SIG, classify=lambda p: None,
                    reader=lambda p, s: {"note": "cost-pass"}, limit=args.limit)
        t = res["totals"]
        print("🗄  %d reel(s) · %d frames → %d classifies · %d pages read"
              % (t["sessionsSeen"], t["framesSeen"], t["classified"], t["pagesRead"]))
        print("   mini-first order: %s" % ", ".join(os.path.basename(d) for d in order_reels(dirs)[:8]))
        print("   %s" % res["why"])
        raise SystemExit(0)

    print("This sweep needs a reader and a classifier. Use --cost for the free grouping pass, or")
    print("drive sweep() from the console, which owns the reader lanes and the apply step.")
