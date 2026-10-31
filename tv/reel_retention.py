"""v2001 — WHICH FOOTAGE HAS GIVEN UP ITS INFORMATION, AND MAY THEREFORE GO.

Konyo: "for storage optimization ... it should delete the oldest and older reel session after it
analyzes them and ledgers them and registers and they all get funneled properly as they should and
are." And, on keying it to swept + evidence banked: "its fine".

MEASURED FIRST, ON HIS 31 REELS (2026-08-23), because the obvious rule is the wrong one:

    read — evidence banked (pages>0)      6 reels    254 MB
    SEALED WITH 0 PAGES                  12 reels   1166 MB
    never swept                          13 reels   1058 MB

"Delete what has been swept" would take 18 reels and 1420 MB — and 1166 MB of that was **never
actually read**. A 0-page seal does not mean "done"; it means THIS READER FOUND NOTHING, and the
engine already knows it, because it reopens exactly those on its own:

    "🔓 8 reel(s) reopened - sealed with 0 pages by an older reader (now p1839)"

So the safe rule is the inverse of the obvious one: a reel is a candidate only once it has GIVEN
something up. Footage that has yielded nothing yet is the footage most worth keeping.

THE FIVE BARS, and every one of them exists because deleting his film cannot be undone:

  1. EVIDENCE BANKED     chronicle_swept says pages > 0. A 0-page seal is a re-read candidate.
  2. BOTH LANES SEALED   chronicle AND vault. A reel the vault has never swept still owes the vault
                         manager its stash rows, and vault_swept.json does not exist at all today —
                         which is why this reports ZERO candidates on his machine right now, and
                         that is the correct answer rather than a broken one.
  3. KEEP THE RECENT     the newest KEEP_RECENT reels stay whatever their state, so a bad sweep can
                         always be re-run against real footage.
  4. OLDEST FIRST        his words. It frees space in the order he asked for.
  5. FLOOR               it stops as soon as the target is met; it never empties the shelf.

IT DOES NOT DELETE UNLESS ASKED. `plan()` is pure and `main()` prints. Deletion needs --apply, and
--apply refuses without --yes, because the one thing worse than a full disk is a confident script
that removed the only copy of a Ber drop. [[unknown-stays-unknown]]
"""
import argparse
import json
import errno as _errno
import glob
import os
import shutil
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))

KEEP_RECENT = 16         # never touch the newest SIXTEEN, whatever the ledgers say
#: ⚠⚠ 2026-09-29 — 8 -> 16 ON HIS INSTRUCTION: *"8 sessions 8 hours long? if its less than 8 double the amount
#: to 16 reels.. FIFO same style just that instead of 8 last reels it reads 16"*. MEASURED that night: a full
#: hour of shadow reel is 344-506 MB on his Mac (1440x904 JPEG, ~145 KB, one a second) and 50-62 MB on the ALT,
#: so eight hours is ~3-4 GB - under his 8 GB line - and the floor doubles.
#: ⚠ AND IT MUST NEVER COST HIM RECORDING. Sixteen full hours is ~8 GB on the Mac, which had 14 GB free, and
#: below ON_AIR_FLOOR_GB the console refuses to film. So the deleting pass asks keep_recent_for(): under the
#: floor the window narrows to the old eight and the oldest EXTRACTED reels beyond it go first. Eligibility is
#: unchanged - nothing unread ever goes - only the count floor bends. [[heart-first]]
KEEP_RECENT_UNDER_PRESSURE = 8
#: ⚠⚠ v2875 — 5 -> 8 ON HIS INSTRUCTION, 2026-09-10: *"okay make it last 8"*, after he
#: asked whether the prune was working and the measurement said it never had. He also ruled
#: that the extraction precondition STAYS (*"reswept and then delete and retired"*), so this
#: is a widened floor, not a loosened rule.
#: ⚠ THE SAME NUMBER LIVES IN frame_authority.py. Two copies of one constant is how a floor
#: silently stops being a floor, so test_the_two_keep_floors_agree pins them together.
#: [[copy-drift]]
MIN_PAGES = 1            # "evidence banked" means at least one page was actually read


def _load(path):
    """{} for callers that do not need to tell the two empties apart. Use _load_state when it
    matters, and for a DELETER it always matters."""
    return _load_state(path)[0]


def _load_state(path):
    """(blob, state) where state is 'absent' | 'ok' | 'unreadable'.

    v2079 — THE HOLE THIS CLOSES, and it has been on origin since v2065. `_load` answered `{}` for
    both "this store has never been written" and "this store exists and will not parse", and those
    are opposite facts. ABSENT is a measurement: `vault_swept.json` genuinely does not exist on a
    tree that has never run a vault sweep, and this module's own prose says so. UNREADABLE is an
    UNKNOWN — the ledger might name every witness in the reel about to be deleted, and nobody can
    say, because nobody could open it.

    Collapsed, the consequence is concrete and it is not the safe direction: with an unreadable
    `vault_swept.json`, `_entry(vault, reel)` is None for EVERY reel, so every reel that a chronicle
    sweep has read falls past `ve is None and _vault_lane_owes(...)` — false for any reel that
    declared a chronicle focus — straight into `else:` and out as ELIGIBLE. Footage deleted on the
    strength of a file that could not be opened, with the report cheerfully saying "sealed by BOTH
    lanes". There is no un-delete.
    [[unknown-stays-unknown]] [[feedback-silence-is-not-evidence]]
    """
    if not os.path.exists(path):
        return {}, "absent"
    try:
        with open(path, encoding="utf-8") as fh:
            return (json.load(fh) or {}), "ok"
    except Exception:
        return {}, "unreadable"


def _entry(ledger, reel):
    """Reels are keyed BOTH ways in these files — `reel_<sid>` and bare `<sid>`. Checking one form
    only means a naming mismatch reads as 'never swept', which for a DELETER is the safe direction
    but for the report is a lie.

    ⚠⚠ REG-561 — AND `a or b` DEFEATED THAT FIX FOR A FALSY ENTRY. `ledger.get(x) or ledger.get(y)`
    treats a present-but-empty record as absent, and it does so ASYMMETRICALLY: measured, `{}`
    stored under `reel_s_1` returned None ("never swept") while the SAME `{}` stored under `s_1`
    returned it. **The same data under two spellings gave two different answers**, which is exactly
    the naming mismatch this function exists to remove. Membership, not truthiness.

    ⚠⚠ REG-563 — AND TWO PLACES IMPLEMENTED THIS ONE LOOKUP WITH OPPOSITE PRECEDENCE. This tried
    `reel` then the bare form; `reel_river`'s seal lookup tried the bare form then `reel`. Measured
    with BOTH keys present, the two returned DIFFERENT RECORDS for the same reel — the same
    copy-drift-of-a-meaning defect as REG-556's `ok`, where nothing was duplicated in text and two
    modules simply decided one question had two answers. One helper, one precedence, quoted by
    both. [[copy-drift]] §1

    ⚠ `str.replace("reel_", "", 1)` was also the wrong tool: it strips the substring ANYWHERE, so
    `"xreel_foo"` became `"xfoo"`. A prefix strip, not a replace.
    """
    return lookup_either_way(ledger, reel)


def bare_reel(reel):
    """`reel_<sid>` -> `<sid>`. A PREFIX strip, never a substring replace."""
    r = str(reel or "")
    return r[len("reel_"):] if r.startswith("reel_") else r


def lookup_either_way(store, reel):
    """The one rule for finding a reel's record in a store keyed BOTH ways. -> record or None

    PRECEDENCE: **the form you ASKED WITH wins**, then its alias. Ask with `reel_s_1` and the
    prefixed record wins; ask with `s_1` and the bare one does. `reel_river` quotes this rather
    than keeping its own order.

    ⚠⚠ REG-566 — THIS DOCSTRING SAID "the PREFIXED form first, then the bare one" AND THE CODE HAS
    NEVER DONE THAT. Measured against a store holding BOTH keys: asking with `reel_s_1` returned
    the prefixed record and asking with `s_1` returned the bare one — the asked form, both times.
    The stated rule and the real rule agreed only for the caller the deleter happens to use
    (`plan()` always asks with the directory name, which is prefixed), so nothing ever contradicted
    it.

    ⚠ AND THIS IS REG-564's CLASS ONE VERSION LATER — a comment contradicting the code it sits on —
    **in the docstring of the very function that fix produced.** The rule is now written as the
    code behaves, and a guard asks it BOTH ways so the two cannot drift apart again.

    ⚠ Membership, not truthiness (REG-561): a present-but-empty record is FOUND, not absent.
    """
    # ⚠⚠ REG-567 — AN EMPTY NAME RESOLVED TO AN EMPTY-STRING KEY. `bare_reel("reel_")` is `""`,
    # and this then looked `""` up in the store: `lookup_either_way({"": 5}, "reel_")` returned 5.
    # The phantom-key class one more time (REG-550, REG-559) — a name that names nothing must not
    # find a record. An empty name and an empty bare form are both simply not keys.
    r = str(reel or "").strip()
    if not r:
        return None
    if r in store:
        return store[r]
    b = bare_reel(r)
    if b and b != r and b in store:
        return store[b]
    # ⚠⚠ REG-565 — THE THIRD STEP RE-PREFIXED AN ALREADY-PREFIXED NAME. `"reel_" + r` was built
    # from the ORIGINAL name, so asking for `reel_s_1` against a store holding only
    # `reel_reel_s_1` RETURNED THAT DOUBLE-PREFIXED RECORD — a key this lookup should never be
    # able to reach. Found by a cold review of the shipped bytes. The prefixed form of a name that
    # already has the prefix is itself; only a BARE name gets one added.
    if r.startswith("reel_"):
        return None
    pref = "reel_" + r
    return store[pref] if pref in store else None


def _dir_mb(path):
    """A reel's size in MB. One listing per folder, never one stat per file: on Windows the listing already
    carries each size, and a per-file getsize here and in frame_ref.Index was most of the 33 s his ALT took
    to answer /api/river (2026-09-28). A symlinked folder is not entered, as os.walk does not.

    REG-1412 — the listing is frame_ref.listing(), the SAME one the frame index walks, so on a console a still
    reel's folder is read once and not again until it changes (its docstring says exactly what that covers)."""
    import frame_ref as _fr
    total = 0
    todo = [path]
    while todo:
        here = todo.pop()
        entries = _fr.listing(here)
        if entries is None:
            continue
        for name, kind, size in entries:
            if kind == "d":
                todo.append(os.path.join(here, name))
                continue
            if kind == "f" and size is not None:
                total += size
    return total / (1024.0 * 1024.0)


# ⚠⚠ v3539 REG-1647 — None MEANS "NEVER LOADED", AND IT IS NOT THE EMPTY SET. This started as set(),
# filled only by plan(). `_panels_never_banked` asks `not in _DURABLE`, so any caller that asked
# BEFORE a plan() ran in its process was told every surveyed reel with panels had never been banked.
# MEASURED on his Mac 2026-10-01, same reel, same process, a minute apart:
#     reel_s_1789330829280_66296   before plan(): never_banked True   after plan(): False (in durable)
# The console's boot re-entry (vault_reentry_sweep) asks first, so on EVERY relaunch it re-admitted
# the two reels the vault lane had retired; the lane then paid 2 passes of ~30 panel reads each on
# both, and its retire path - asking after plan() - retired them again. 9 relaunches since
# 2026-09-30 10:18, about 1,000 reads that could never seal (REG-1648). end_routes fell into this
# same unloaded global once and fixed it for itself only. [[unknown-stays-unknown]] [[copy-drift]]
_DURABLE = None


class DurableUnknown(Exception):
    """The durable witness index could not be read, so whether a reel's panels were banked is UNKNOWN.

    Raised to the caller rather than collapsed to a bool: the callers disagree on what UNKNOWN costs.
    The vault re-entry leaves a retirement alone ("never guess" - re-admitting spends), the retire
    path refuses to retire ("retiring wrongly costs the extraction for ever"). Each already says so in
    its own except arm; a bool would have picked one of them for both."""


def _durable_loaded():
    """The durable session set, loaded on first use when no plan() has run in this process. -> set

    ⚠ A failed load is NOT cached: an unreadable index read once must not stand as "nothing is
    durable" for the life of the console (the v2386 lesson, one module over)."""
    global _DURABLE
    if _DURABLE is None:
        _sess, _ok, _why = _durable_sessions(HERE)
        if not _ok:
            raise DurableUnknown(_why or "the durable witness index could not be read")
        _DURABLE = set(_sess)
    return _DURABLE


def _reel_ts_key(reel):
    """The SESSION id a reel directory name carries. vault_swept is keyed by session, the plan
    iterates directories, and the two differ by the `reel_` prefix — matching them by eye is how a
    reel gets held or released for the wrong reason."""
    b = os.path.basename(str(reel or ""))
    return b[len("reel_"):] if b.startswith("reel_") else b


def _reel_ts(reel):
    """Sort key: the epoch ms embedded in reel_s_<ms>_<n>. Falls back to mtime, and a reel whose
    name cannot be parsed sorts NEWEST so it is the last thing anyone deletes."""
    try:
        return int(reel.split("_")[2])
    except Exception:
        return float("inf")


def release_uncited(reel_dir, sealed, wit):
    """Apply keep_cited. The authority names the frames. This module is the one that removes them.

    ⚠ No production code calls this today (second eye on v3520, 87c35d69): apply_plan trims a reel through its
    own tombstone-noted path (see the NOT keep_cited() note there), and only its law calls this. It is kept as the
    one place that would remove what keep_cited names - not as a lane that runs."""
    import frame_authority as _fa
    note = _fa.keep_cited(reel_dir, sealed, wit)
    if not note.get("ok"):
        return note
    gone = []
    for name in list(note.get("gone") or []):
        path = os.path.join(reel_dir, name)
        try:
            os.remove(path)
        except OSError:
            note = dict(note)
            note["ok"] = False
            note["gone"] = gone
            note["why"] = "a frame could not be released, so the rest were left where they are"
            return note
        gone.append(name)
    return note


def _durable_sessions(here=None):
    """Sessions whose witnesses survive INDEPENDENTLY of the frames.

    v2056 — Konyo: "after the sweep ... data needs to be extracted and ledgered and counted for
    items as witnesses so when they get pruned they continue to exist on record."

    MIN_PAGES called it "evidence banked" and meant "at least one page was READ". Reading produces
    a PROPOSAL; only an apply puts rows in the ledger. Measured 2026-08-24: reel
    s_1787242455315_9654 had rows=7 in vault_swept and NOTHING in any durable store, so deleting it
    would have taken those seven witnesses with it.

    v2065 — AND THE RULE NOW HAS ONE HOME. v2062 built frame_authority to be "the one deletion
    authority" and then wired only the frame prune to it, leaving this — the deleter that removes
    WHOLE REELS — reading its own private copy of the same two stores. Two copies of one rule is how
    they drift, and these two already differed: this one swallowed an unreadable store silently
    (`except: continue`), so "no witnesses" and "could not read the ledger" were the same answer.
    They agreed on his tree the day this was written (5 sessions, identical set) — which is exactly
    when a duplicate is cheapest to remove and hardest to notice. [[copy-drift]]

    Still errs toward KEEPING: a store that will not parse contributes nothing here AND makes
    witness_index report ok=False, and the caller treats a non-durable reel as HELD. So "I could not
    read the ledger" can only ever hold a reel, never release one.
    """
    try:
        import frame_authority as _fa
    except Exception:
        # cannot ask the authority -> nothing is durable AND nothing is known
        return set(), False, "frame_authority could not be imported, so nothing can say which "\
                             "recordings are banked"
    idx = _fa.witness_index(here or HERE)
    # v2079 — and carry the authority's own `ok` instead of dropping it on the floor. It is False
    # when ANY durable store would not parse, and the sessions set is then a PARTIAL index. The
    # comment above argues a partial index can only hold reels; that is true of the rows-not-banked
    # branch and NOT true of a reel with no rows, which reaches `else:` untouched.
    bad = [k for k, v in (idx.get("perStore") or {}).items() if v is None]
    return (set(idx.get("sessions") or ()), bool(idx.get("ok")),
            ("%s will not parse" % ", ".join(sorted(bad))) if bad else None)


def _vault_lane_owes(reel_path):
    """Would the VAULT lane ever read this reel at all?

    v2042 — a reel that DECLARED a chronicle focus is not the vault lane's to read:
    `vault_retro.OWNERSHIP_SURFACES` deliberately excludes 'chronicle'. Holding such a reel until
    the vault sweeps it holds it FOREVER.

    Measured 2026-08-24: five reels declaring chronicle-uniques / chronicle-sets (250 MB) were kept
    on exactly that reason, waiting for a lane that was never going to come, while the disk sat at
    96%. A hold that can never be satisfied is not a hold, it is a leak.

    Errs toward KEEPING: an unreadable index, or no declared focus at all, still owes the lane.
    Deleting footage is irreversible and 'I could not tell' must never resolve to 'delete it'.
    """
    try:
        with open(os.path.join(reel_path, "index.json"), encoding="utf-8") as fh:
            ix = json.load(fh)
    except Exception:
        return True
    focus = str((ix or {}).get("focus") or "").lower()
    if not focus:
        return True
    try:
        import vault_retro as _vr
        surfaces = tuple(_vr.OWNERSHIP_SURFACES)
    except Exception:
        surfaces = ("stash", "inventory", "equipment", "runes", "gems", "materials")
    return focus in surfaces


_TRIAGE_CACHE = {"at": None, "store": None}


_UNSUPPLIED = object()


def _panels_never_banked(reel, seal=_UNSUPPLIED):
    """A full survey saw panels here, and the vault ledger holds nothing from this reel. -> bool

    `seal` is the caller's own vault_swept entry for this reel (plan() passes the one it already
    read from ITS store, None when there is none); left out, the live seal store is asked.

    ⚠ UNKNOWN KEEPS THE REEL, as everywhere in this file: no survey, a sampled pass, an unreadable
    store or any exception returns False only when we can positively say the panels were banked;
    every other not-knowing returns True and HOLDS. The cost of being wrong is footage with no
    un-delete. [[unknown-stays-unknown]]
    """
    try:
        import os as _os
        import retro_triage as _rt
        p = _rt._store_path()
        key = (p, _os.path.getmtime(p))
        if _TRIAGE_CACHE["at"] != key:
            store, ok = _rt.load()
            if not ok:
                return False              # cannot read the survey -> other rules decide
            _TRIAGE_CACHE["store"] = store
            _TRIAGE_CACHE["at"] = key
        rec = (_TRIAGE_CACHE["store"] or {}).get(reel)
        if not isinstance(rec, dict) or not rec.get("full"):
            return False                  # not surveyed -> _proven_empty/never-swept rules apply
        if int(rec.get("panels") or 0) <= 0:
            return False                  # genuinely no panels -> nothing to bank -> may retire
        # ⚠⚠ v3074 — PANELS THAT HOLD NO NAMES ARE NOT PANELS NOBODY READ, AND CONFLATING THEM
        # MADE THIS RULE A PERMANENT HOLD. This asked only "are there panels, and is the reel in
        # the durable stores", and a reel whose panels carry no readable NAME can never enter
        # those stores — so the answer was True forever and no future run could change it. The
        # rule's own comment says it exists for "the state a seal-with-no-rows leaves behind",
        # and it never once consulted that seal. [[the-unjoined-end]]
        #
        # MEASURED 2026-09-13: this held all 8 reels the river could not drain. One of them is a
        # Shared stash page 5/5 with ~25 items on screen — genuinely full, and genuinely
        # unnameable, because a stash GRID prints no names at all; only the hover tooltip does.
        # The vault reader returning items:[] there is CORRECT, which vault_seal_is_definitive
        # already rules a complete answer rather than a failure.
        #
        # The authority is frame_authority's, not a second opinion invented here:
        # seal_releases_frames says yes ONLY for a COVERED seal, or an EMPTY one that carries
        # examinedEmpty — the flag v3074 writes when every panel was read AND cross-checked with
        # no pixel error and no over-read. A default "nothing was taken" seal still returns False.
        _row = seal if seal is not _UNSUPPLIED else None
        try:
            import frame_authority as _fa
            if seal is _UNSUPPLIED:
                _seals, _sok = _fa.sealed_sessions()
                if _sok:
                    _row = _seals.get(reel) or _seals.get(str(reel).replace("reel_", "", 1))
            if isinstance(_row, dict):
                _releases, _ = _fa.seal_releases_frames(_row)
                if _releases:
                    return False      # examined, cross-checked, no name to be had
        except Exception:
            pass                          # UNKNOWN KEEPS THE REEL — fall through and hold
        # ⚠⚠⚠ REG-1277 (#221) — A LIVE WITNESS IS NOT AN EXTRACTION, AND READING IT AS ONE DELETED
        # THIRTEEN REELS. The line below asks "is this session in the durable stores", and one item
        # the LIVE lane read while filming puts it there. MEASURED from his console's own stdout:
        # at 01:36:21 on 2026-09-10 it relaunched onto v2875 and one second later printed "freed
        # 3565 MB by removing 7 reel(s)" — the exact "7 candidates (3,565 MB)" v2875's commit had
        # measured as a dry run. Five more passes that day took 11 more. 13 of the 18 had a FULL
        # survey with panels and a vault seal with rows 0: reel_s_1787523300658_1 held 2,385 frames
        # (3,002.9 MB, 18 panels) and went on ONE durable row, a Deep Worldstone Shard seen live.
        # reel_s_1788105158696_89699 is named in v2875's own comment below as a reel this rule
        # exists to hold; it left three minutes after that comment was committed. end_routes asked
        # the same reels and refused every one — the two answers disagreed and nothing compared them.
        # A seal that took 0 rows extracted nothing, whatever else names the session.
        # [[feedback-contradiction-is-the-finding]] [[the-unjoined-end]]
        if isinstance(_row, dict):
            _n = _row.get("rows")
            if isinstance(_n, bool) or not isinstance(_n, int) or _n <= 0:
                return True
        return _reel_ts_key(reel) not in _durable_loaded()     # REG-1647 — never the unloaded global
    except DurableUnknown:
        raise                             # REG-1647 — UNKNOWN travels; each caller prices it itself
    except Exception:
        return False


def _no_chronicle_to_find(reel):
    """Did a FULL survey of this reel find no chronicle panel at all? -> bool

    ⚠⚠ v2875 — THE `zero-pages` RULE HOLDS REELS FOR AN EVENT THAT CANNOT HAPPEN.

    Konyo, 2026-09-10: *"whatever doesn have information on the reels get filtered anyways and go
    to tombstone eventually within the filtering system and process"*.

    `zero-pages` says "sealed with 0 pages — the engine reopens these when the prompt improves".
    That is exactly right for footage that CONTAINS a Chronicle screen the reader failed to read.
    It is meaningless for footage that has none: no future prompt can find a page in a reel where
    the Chronicle was never on screen, so the reel is held for ever by a verdict from a lane that
    was never the right one for it.

    MEASURED on his tree, 2026-09-10:
        41 reels on disk, retention holding them as   zero-pages 25 · test-fixture 8 · recent 8
        2,437 panel frames across those reels (36% of all footage)
        kinds: stash 1855 · shared 407 · personal 121 · materials 40 · runes 10 · gems 4
        chronicle: ZERO — and across ALL 454 surveyed reels in his store, never once
    `retro_triage.PANEL_KINDS` carries 'chronicle', so the survey CAN say it and never has. Those
    25 reels are stash footage, and their stash rows are the VAULT lane's work — which the chain
    never reaches, because `zero-pages` matches first. The file predicted this: "the vault-owes tag
    genuinely never fires on his tree because earlier rules match first... a LATENT defect the day
    a reel legitimately reaches it."

    ⚠ THIS DOES NOT DELETE ANYTHING. It only stops a chronicle verdict from being the reason, so
    the reel falls through to the rules that actually apply to it — rows-not-banked, vault-owes,
    the receipt hold. Every one of those can still keep it.

    ⚠ NOT SURVEYED IS NOT "NO CHRONICLE". A missing store, an unreadable one, a reel absent from
    it, a SAMPLED pass, or any exception all return False — which KEEPS the chronicle hold. Same
    doctrine as _proven_empty, for the same reason: the cost of being wrong is footage with no
    un-delete. [[unknown-stays-unknown]] [[label-outlived-referent]]
    """
    try:
        import os as _os
        import retro_triage as _rt
        p = _rt._store_path()
        key = (p, _os.path.getmtime(p))
        if _TRIAGE_CACHE["at"] != key:
            store, ok = _rt.load()
            if not ok:
                return False
            _TRIAGE_CACHE["store"] = store
            _TRIAGE_CACHE["at"] = key
        rec = (_TRIAGE_CACHE["store"] or {}).get(reel)
        if not isinstance(rec, dict) or not rec.get("full"):
            return False                      # never surveyed, or sampled -> UNKNOWN -> keep
        kinds = rec.get("kinds")
        if not isinstance(kinds, dict):
            return False                      # no kind breakdown -> cannot say -> keep
        return int(kinds.get("chronicle") or 0) == 0
    except Exception:
        return False


def _proven_empty(reel):
    """Has the FREE pass fully surveyed this reel and found no panel at all? -> bool

    ⚠ THIS IS THE ONE RULE ALLOWED TO OVERRULE "it has never been read", so it is deliberately
    the narrowest thing that can: a FULL pass (`full`), and ZERO frames on which any panel or
    stash screen was open. `retro_triage.survey` refuses to produce a disposal list from a
    sampled pass for the same reason, and this refuses to consult one.

    ⚠ NOT SURVEYED IS NOT EMPTY. A missing store, an unparseable one, a reel absent from it, or
    any exception all return False — which KEEPS the reel. The cost of being wrong here is
    footage with no un-delete, so the unknown case must fall on the keep side every time.
    [[unknown-stays-unknown]] [[feedback-suspect-the-instrument]]

    Why it is safe against BOTH lanes: the gate is stash_screen_open_cached, which answers with a
    tab name whenever a stash grid OR a chronicle panel is on screen. Zero of those across every
    frame means there is no page for the chronicle reader to read and no grid for the vault lane
    to bank — so `vault-owes` is satisfied too, which is why that rule is guarded as well.
    """
    try:
        import os as _os
        import retro_triage as _rt
        p = _rt._store_path()
        # ⚠ KEY THE CACHE ON (PATH, MTIME), NOT MTIME ALONE. The store path follows TV_HIST, so
        # it is NOT one fixed file: a harness and the live console resolve different ones. Keyed
        # on mtime alone, two stores whose timestamps happen to match would serve each other's
        # verdicts — and the consequence here is deleting footage that has no un-delete.
        key = (p, _os.path.getmtime(p))
        if _TRIAGE_CACHE["at"] != key:                # re-read only when the store actually moved
            # ⚠ load() RETURNS (store, ok), NOT a store. Calling .get() on that tuple raises, the
            # except below swallows it, and every reel comes back "not proven empty" — which is
            # INDISTINGUISHABLE from the deadlock this change exists to break. It got as far as a
            # sandbox run before anything noticed. `ok` False means the store could not be READ,
            # which is not "nothing surveyed": treat it as UNKNOWN and keep the footage.
            # [[unknown-stays-unknown]] [[feedback-silence-is-not-evidence]]
            store, ok = _rt.load()
            if not ok:
                return False
            _TRIAGE_CACHE["store"] = store
            _TRIAGE_CACHE["at"] = key
        rec = (_TRIAGE_CACHE["store"] or {}).get(reel)
        if not isinstance(rec, dict):
            return False
        return bool(rec.get("full")) and int(rec.get("panels") or 0) == 0
    except Exception:
        return False


# Every conclusion plan() can reach about a reel. Module-level since v2383 so reel_story can
# assert it has a stage for each one — see tv/test_reel_story.py.
RULES = ("no-witness-index", "ledger-unreadable", "holds-proof", "test-fixture", "recent",
         "never-chronicle-swept", "zero-pages",
         # v2875 — panels on film with NOTHING in the ledger. Ordered BEFORE rows-not-banked
         # because that rule fires only when rows exist and are not durable; this one is the case
         # where the count is ZERO and the panels are real, which is the state a seal-with-no-rows
         # leaves behind. It is the safety half of _no_chronicle_to_find.
         "panels-never-banked",
         "rows-not-banked", "vault-owes", "target-met", "eligible")


def _evidence_rows():
    """chron_evidence flattened into the row shape frame_ref expects. -> (rows, why)

    ⚠⚠ THE ADAPTER IS THE WHOLE POINT, AND WITHOUT IT THE GUARD PROTECTS NOTHING.
    `frame_ref.cited_frames()` decides a row is PROOF via `r.get("items") or r.get("names")`.
    chron_evidence.json does not store it that way — the item name is the KEY:

        {"uniques": {"Djinn Slayer": [{"reel": ..., "frame": ..., "conf": ...}, ...]}}

    So every row would fall through to `other` (fair game), `named` would come back EMPTY, and a
    guard wired straight onto it would delete every frame it was written to protect while looking
    correct. Measured on the real store before writing this. [[plumbing-with-no-tap]]
    """
    try:
        import tv_diablo as _tvd
        root = _tvd._fixture_root(HERE)
        # ⚠⚠ NARROWED FROM `except Exception`, AND THE CORRECTED TEMPLATE WAS ALREADY IN THIS FILE.
        # `_tombstone_path()` five hundred lines below carries the v2788 fix verbatim; this arm
        # arrived at v2814 as a fresh copy of the shape that fix removed, and the census in
        # test_no_resolver_falls_back_to_his_live_world.py caught it — which is the whole reason
        # that law is a census and not a list of three. A blanket catch also swallows a runtime
        # failure OF THE RULE ITSELF and answers HERE — his live tree — to a caller that had
        # explicitly asked for a fixture world. That is the worst possible answer here: `root`
        # picks the chron_evidence.json that decides which of his reels hold PROOF, and the prune
        # deletes what it does not. ImportError means tv_diablo genuinely is not importable and
        # HERE is then the honest answer; anything else must surface, not resolve to his tree.
        # [[copy-drift]] [[unknown-stays-unknown]] [[the-unjoined-end]]
    except ImportError:
        root = HERE
    return evidence_rows_at(root)


def evidence_rows_at(root):
    """_evidence_rows for an EXPLICIT tree. -> (rows | None, why)

    2026-09-28 — the recorder's disk-floor reaper (tv_diablo._reel_evidence) asks this with the root of the shelf
    it deletes from. It cannot go through _evidence_rows, which resolves its root by importing tv_diablo — a
    second copy of the running recorder. ONE flattening, two ways to name the tree. [[copy-drift]]
    """
    p = os.path.join(root, "chron_evidence.json")
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except FileNotFoundError:
        # ⚠⚠ AN ABSENT STORE IS NOT AN UNKNOWN ONE, AND FOUR GATES TAUGHT ME THE DIFFERENCE.
        # The first cut returned None (CANNOT TELL) here, which HOLDS every reel — and in an
        # isolated fixture world, which has no chronicle at all, that held everything and made the
        # prune untestable: test_the_fixture_is_deletable_WITHOUT_the_hold and
        # test_the_branch_is_reachable_or_this_whole_case_proves_nothing both went red, correctly.
        # A world with no chronicle has no CLAIMS, so it has no receipts to protect — that is an
        # empty answer, not an absent one. CANNOT TELL is reserved for a store that EXISTS and
        # could not be read, which is the case where something may be cited and we cannot see it.
        # [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
        return [], "no chron_evidence.json at %s — this world holds no claims" % p
    except Exception as e:
        return None, "chron_evidence.json could not be read (%s)" % type(e).__name__
    rows = []
    for section in ("uniques", "sets"):
        sec = d.get(section)
        if not isinstance(sec, dict):
            continue
        for item, cites in sec.items():
            for c in (cites or []):
                if not isinstance(c, dict):
                    continue
                fid = c.get("frame") or c.get("frameId")
                if not fid:
                    continue
                # the KEY is the claim; carrying it onto the row is what makes it count as NAMED
                rows.append({"frameId": fid, "reel": c.get("reel"), "items": [item]})
    return rows, "%d citation(s) across uniques+sets" % len(rows)


def proof_reels(hist_dir):
    """Reels holding a frame that is the receipt for a NAMED claim. -> (set|None, why)

    ⚠⚠ None means CANNOT TELL, and a caller that cannot tell MUST NOT DELETE. Measured 2026-09-09:
    53-77% of cited proof frames were already gone (the spread is the denominator — 53% within
    uniques+sets, 77% across every section carrying a reel+frame), because `plan()` marks a reel
    eligible on a coarse reel-level vault signal and `apply_plan()` then rmtree's the WHOLE
    directory without ever asking which frames a claim depends on.

    frame_ref has shipped exactly this rule since v2364 — "a frame cited by a row that NAMED an
    item is PROOF and may not be deleted while the claim stands" — and NOTHING in production ever
    called it. AST-confirmed: the only callers of cited_frames/prunable/Index are frame_ref itself
    and one test. reel_retention did not even import it. [[the-unjoined-end]]
    """
    rows, why = _evidence_rows()
    if rows is None:
        return None, why
    try:
        import frame_ref as _fr
    except Exception as e:
        return None, "frame_ref could not be imported (%s)" % type(e).__name__
    try:
        named, _other = _fr.cited_frames(rows)
        idx = _fr.Index(hist_dir)
    except Exception as e:
        return None, "the frame index could not be built (%s)" % type(e).__name__
    if not named:
        # a real possibility, and NOT the same as "nothing is cited" — say which.
        return set(), "no citation names an item (%s)" % why
    held, unresolved = set(), 0
    for fid in named:
        try:
            hit = idx.resolve(fid)
        except Exception:
            hit = None
        if not hit:
            unresolved += 1
            continue
        # ⚠ frame_ref.Index.resolve() RETURNS A PATH ALREADY RELATIVE TO ITS ROOT
        # ("reel_s_.../f_....jpg"). The first cut ran os.path.relpath(hit, hist_dir) over it —
        # relpath of a relative path against a relative dir — and EVERY result collapsed to "..",
        # so 667 protected frames reported as ONE fake reel and the guard would have protected
        # essentially nothing while printing a confident number. Caught by the count being
        # implausible, not by the code looking wrong. [[feedback-suspect-the-instrument]]
        rel = os.path.relpath(hit, hist_dir) if os.path.isabs(hit) else hit
        seg = str(rel).replace("\\", "/").split("/")[0]
        if seg and seg not in (".", ".."):
            held.add(seg)
    return held, ("%d reel(s) hold the proof of a named claim; %d cited frame(s) resolve to "
                  "nothing on disk (already lost); %s" % (len(held), unresolved, why))


def recent_order(reels):
    """The PARSEABLE reels in FIFO order, oldest first. -> list. Pure.

    REG-1813 — THE ONE ORDER THE SHELF IS KEPT BY. recent_shield is its tail, the stuck alarm dates a
    reel's exit from it, and /api/river hands it to THE SHELF (`riverKept`) so the page never sorts
    the window itself. The page did: by a run's END time, so on the ALT 2026-10-06 its sixteen held
    3 long runs the deleter had already let go and hid 3 the deleter keeps. The key is the epoch in
    the name, the same key plan() orders by; the name breaks a tie, so two callers handed the same
    reels in a different order get the same list. REG-571: an unparseable name is not in it.
    """
    return sorted((r for r in reels if _reel_ts(r) != float("inf")), key=lambda r: (_reel_ts(r), r))


def recent_shield(reels, keep_recent=KEEP_RECENT):
    """The newest `keep_recent` PARSEABLE reels — the ones kept whatever the ledgers say. -> set

    #84 (REG-1517) — pulled out of plan() so the drain's blocked-upstream reading shields exactly the
    reels the plan shields. REG-571's rule travels with it: an unparseable name keeps its inf sort
    key (last to be deleted) and cannot stand in the shield for a real reel. `reels` may arrive in
    any order; the order is recent_order's.
    """
    if not keep_recent:
        return set()
    return set(recent_order(reels)[-int(keep_recent):])


def shield_exits(reels, keep_recent=KEEP_RECENT):
    """When each reel OLDER than the newest `keep_recent` left that shield. -> {reel: epoch ms}. Pure.

    REG-1812 — a reel leaves when the `keep_recent`-th reel newer than it arrives, so its exit is
    that reel's name epoch. The stuck alarm starts the drain's patience there: a reel pushed out a
    minute ago is not yet owed, however long it sat at its station inside the window. Read off the
    shelf as it stands, so a newer reel already gone cannot be seen and the time is a LATEST bound -
    an age built on it is a floor, never an overstatement. A reel inside the shield, or one whose
    name does not parse, has no entry. No shield (0, like recent_shield) puts every reel outside it
    from the moment it arrived.
    """
    order = recent_order(reels)
    k = int(keep_recent or 0)
    return dict((order[i], int(_reel_ts(order[i + k]))) for i in range(max(0, len(order) - k)))


def keep_recent_for(free_gb, floor_gb):
    """How many of the newest reels the deleting pass must keep, given the disk. -> int. Pure.

    His sixteen while the disk can afford them; the old eight when free space is under the recording floor,
    so holding the extra hours never stops the console from filming the next one. An UNKNOWN reading keeps
    the full sixteen - a deleter that cannot see the disk must not act as if it were full."""
    try:
        if free_gb is not None and floor_gb is not None and float(free_gb) < float(floor_gb):
            return KEEP_RECENT_UNDER_PRESSURE
    except (TypeError, ValueError):
        pass
    return KEEP_RECENT


def _resolve_hist(hist_dir):
    """The footage tree plan() reads: the caller's, else this machine's (machine_tree), else HERE/frames/hist.
    ONE rule, asked by plan() and by its fingerprint, so the two cannot name different trees."""
    if hist_dir:
        return hist_dir
    try:
        import machine_tree as _mt
        hist = _mt.footage_hist()
    except Exception:
        hist = None
    if not hist:
        hist = os.path.join(HERE, "frames", "hist")
    return hist


# ── REG-1411 (#66) — ONE PLAN, SHARED, UNTIL ONE OF ITS INPUTS MOVES ──────────────────────────────────────
# MEASURED on his ALT (Windows + Boosteroid, ~30 reels, ~21,000 frames) right after v3522 landed: /api/river
# timed out at 90 s while THREE threads were inside frame_ref.Index.__init__ at the same moment - tvd-retro-triage
# (river_stamp.run -> reel_router.route -> printer.stream -> reel_story.story -> plan), tvd-eagle-watch
# (health_engine -> lane_health.owed_counts -> control_app._vault_owed_reels -> plan) and an HTTP request
# (heart_state -> printer.stream -> ... -> plan). plan() is called from ~62 places and remembered nothing, so every
# lane rebuilt the whole frame index and the proof set from scratch, concurrently, over footage that had not moved.
# Measured on an ALT-shaped fixture here (31 reels, 21,205 files, 3 plan() callers + reel_story.story at once):
# 153.6 s cold after a ship, 4.6 s warm, 4 index builds and 268 folder listings per round.
_NO_MEMO = object()
_PLAN_MEMO = {}                 # key -> (fingerprint, snapshot)
_PLAN_LAST = {}                 # wave key -> {"snap": dict, "asOf": float}: the last plan a reader may take
_PLAN_FLIGHTS = {}              # key -> {"fp", "done", "result"}: the computation other callers may join
_PLAN_MEMO_MAX = 16
_JOIN_WAIT_S = 300.0            # a joiner never waits longer than this on another thread's computation
_PLAN_LOCK = threading.Lock()
_IN_PLAN = threading.local()
_PLAN_WAVES = {}                # call key -> {"running": wave | None, "next": wave | None} (see _plan_wave)
#: runs = executions of plan()'s body; served/joined = answers that ran nothing; unkeyed/off/alone = calls that
#: computed their own answer and shared it with nobody (see _plan_shared); moving = calls that found an input
#: moving, each answered by a WAVE (_plan_wave): waves = wave computations, coalesced = wave answers handed to a
#: caller that ran nothing
PLAN_STATS = {"runs": 0, "served": 0, "joined": 0, "led": 0, "moving": 0, "unkeyed": 0, "off": 0,
              "alone": 0, "waves": 0, "coalesced": 0}


class _Unkeyable(Exception):
    """An input plan() reads that the fingerprint cannot key. -> no memo for that call."""


class _Moving(Exception):
    """An input changed less than frame_ref.RACY_S ago. -> computed fresh, never kept, never shared."""


def plan_input_files(hist_dir=None):
    """Every FILE plan() reads besides the footage tree, enumerated from the code. -> [absolute path]

        chronicle_swept.json, vault_swept.json   _pick(): the HERE copy and the hist copy of each
        reel_tombstones.json                      _tombstone_path(hist): the remnant filter
        vault_accum.json, vault_seen.json         frame_authority.DURABLE_STORES under HERE: _durable_sessions,
                                                  witness_index(HERE).haveIndex, vault_evidence.cited_frames
        retro_triage.json                         retro_triage._store_path(): _proven_empty,
                                                  _no_chronicle_to_find, _panels_never_banked
        chron_evidence.json                       tv_diablo._fixture_root(HERE): proof_reels -> _evidence_rows
        test_reel_refs.json                       frame_authority.RATCHET_PATH: the fixture set on a console
    Constants (MIN_PAGES, RULES, vault_retro's surfaces and conf floor) are code, fixed for a process's life."""
    hist = _resolve_hist(hist_dir)
    import frame_authority as _fa
    import retro_triage as _rt
    out = [os.path.join(HERE, "chronicle_swept.json"), os.path.join(hist, "chronicle_swept.json"),
           os.path.join(HERE, "vault_swept.json"), os.path.join(hist, "vault_swept.json"),
           _tombstone_path(hist)]
    out += [os.path.join(HERE, fn) for fn in _fa.DURABLE_STORES]
    out.append(_rt._store_path())
    try:
        import tv_diablo as _tvd
        _root = _tvd._fixture_root(HERE)
    except ImportError:
        _root = HERE
    out.append(os.path.join(_root, "chron_evidence.json"))
    out.append(_fa.RATCHET_PATH)
    return out


def _still_file(path, now_ns):
    """A file's key, None when absent (absence is a measurement). Raises _Moving / _Unkeyable."""
    import frame_ref as _fr
    try:
        st = os.stat(path)
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError as e:
        raise _Unkeyable("%s: %s" % (type(e).__name__, path))
    if not _fr.still(st, now_ns):
        raise _Moving(path)
    return (st.st_mtime_ns, getattr(st, "st_ctime_ns", 0), st.st_size, st.st_ino, st.st_dev)


def plan_fingerprint(hist_dir=None, free_mb=None, keep_recent=KEEP_RECENT):
    """-> (key, fingerprint) for a plan() call, or raises _Moving / _Unkeyable.

    KEY: the footage tree (as resolved, and absolute), HERE, TV_HIST, free_mb, keep_recent - and _pick's ORDER
    (HERE's copy of a ledger first, or hist's), but only while BOTH copies of chronicle_swept or vault_swept are
    present: with one copy the order cannot change the answer, so plan() and plan(<that same tree>) - the eagle's
    call shape and reel_story's - share one computation. FINGERPRINT - what the answer depends on, and nothing is
    left to a guess:
      · every file in plan_input_files(): (mtime, ctime, size, inode, device), or absent;
      · the footage tree: hist's own folder key (which names are in it - reels and loose frames alike, the index
        resolves both), then EVERY folder the frame index and _dir_mb walk beneath it, each by its folder key,
        found from its kept listing (frame_ref.listing), and each reel's index.json (_vault_lane_owes).
    Any input changed less than frame_ref.RACY_S ago raises _Moving: a second change inside one clock tick can
    leave a stamp unchanged, so a moving input is never trusted. A reel folder that is a symlink, a store that
    cannot be stat'd, or a tree that cannot be listed raises _Unkeyable: no memo for that path.
    REG-1439 — and on a console whose ratchet will not read, _Unkeyable too: frame_authority then falls back to
    the EXACT scan, whose answer comes from tv/*.py and tests/* - files this key does not cover, so an edited
    test would leave a kept plan standing on a fixture set that has moved."""
    import frame_ref as _fr
    hist = _resolve_hist(hist_dir)
    now = time.time_ns()
    parts = [(p, _still_file(p, now)) for p in plan_input_files(hist_dir)]
    import frame_authority as _fa_key
    if _fr.on_console_path() and _fa_key.ratchet_reels() is None:
        raise _Unkeyable("the ratchet will not read: the fixture set is the exact scan, which this key does not cover")
    _present = dict(parts)
    _both = any(_present.get(os.path.join(HERE, fn)) is not None and _present.get(os.path.join(hist, fn)) is not None
                for fn in ("chronicle_swept.json", "vault_swept.json"))
    _order = (bool(hist_dir) or bool(os.environ.get("TV_HIST"))) if _both else None
    try:
        key = (hist, os.path.abspath(hist), HERE, os.environ.get("TV_HIST") or "", _order, free_mb, keep_recent)
        hash(key)
    except Exception:
        raise _Unkeyable("the arguments cannot be keyed")
    try:
        st = os.stat(hist)
    except OSError:
        raise _Unkeyable("no footage tree to key")        # plan answers that one cheaply anyway
    if not _fr.still(st, now):
        raise _Moving(hist)
    # REG-1438 — hist's OWN folder key is load-bearing: a loose hist/f_<ms>.jpg whose stem a citation names
    # decides whether that citation resolves to its reel (the reel HOLDS PROOF) or to the loose copy (it does not),
    # and adding or removing one moves nothing else this fingerprint reads.
    parts.append((hist, _fr.folder_key(st)))
    top = _fr.listing(hist)
    if top is None:
        raise _Unkeyable("the footage tree cannot be listed")
    todo = []
    for name, kind, _size in top:
        if kind == "d":
            todo.append(os.path.join(hist, name))
            if name.startswith("reel_"):
                ix = os.path.join(hist, name, "index.json")
                parts.append((ix, _still_file(ix, now)))
        elif kind != "f" and name.startswith("reel_"):
            # _dir_mb follows a symlinked reel and the index does not: one input, two readings - no memo
            raise _Unkeyable("reel folder %s is a symlink or cannot be typed" % name)
    while todo:
        d = todo.pop()
        try:
            st = os.stat(d)
        except OSError:
            raise _Unkeyable("a folder vanished while it was keyed")
        if not _fr.still(st, now):
            raise _Moving(d)
        parts.append((d, _fr.folder_key(st)))
        sub = _fr.listing(d)
        if sub is None:
            raise _Unkeyable("a folder cannot be listed")
        todo.extend(os.path.join(d, n) for n, k, _s in sub if k == "d")
    return key, tuple(parts)


def _plan_count(field):
    with _PLAN_LOCK:
        PLAN_STATS[field] += 1


def _remember_plan(key, snap):
    """Keep the last finished plan for a reader. A plan that is not ok is not kept.

    The lock is taken here. The caller must not already hold _PLAN_LOCK: it is not reentrant.
    The deleter's memo is a different store and is not written here."""
    if key is None or not isinstance(snap, dict) or snap.get("ok") is not True:
        return
    import copy
    kept = copy.deepcopy(snap)
    kept.pop("moving", None)
    kept.pop("asOf", None)
    with _PLAN_LOCK:
        _PLAN_LAST[key] = {"snap": kept, "asOf": time.time()}


def _plan_shared(hist_dir, free_mb, keep_recent):
    """plan()'s answer without running it, when that is PROVABLY the answer it would compute. -> dict | _NO_MEMO

    ON THE CONSOLE PATH ONLY (frame_ref.on_console_path(), set by control_app.main()); anywhere else a law may
    monkeypatch what plan() calls, and a memo cannot key on a monkeypatch. _NO_MEMO means "run plan() yourself".
      · SERVED  the last answer for this key, while plan_fingerprint() is identical - nothing it reads has moved.
      · JOINED  a computation already running for this key, started on the SAME fingerprint this caller sees; it
                is handed over only if the fingerprint taken again AFTER it finished is still identical.
      · otherwise the caller LEADS: it computes, and its answer is kept and shared only on that same condition.
    Every answer handed out is a deep copy - no caller can edit what another is served. An exception is never
    shared (a joiner then computes its own). An input that cannot be keyed computes fresh; an input MOVING
    computes fresh too, in a wave shared only by callers that arrived before it started (_plan_wave, REG-1437)."""
    try:
        import frame_ref as _fr
        if not _fr.on_console_path():
            _plan_count("off")
            return _NO_MEMO
    except Exception:
        return _NO_MEMO
    if getattr(_IN_PLAN, "on", False):
        # a plan() asked from INSIDE a computation this thread leads would wait on itself for ever
        _plan_count("alone")
        return _NO_MEMO
    import copy
    for _attempt in range(3):
        try:
            key, fp = plan_fingerprint(hist_dir, free_mb, keep_recent)
        except _Moving:
            _plan_count("moving")
            return _plan_wave(hist_dir, free_mb, keep_recent)
        except Exception:
            _plan_count("unkeyed")
            return _NO_MEMO
        with _PLAN_LOCK:
            m = _PLAN_MEMO.get(key)
            if m is not None and m[0] == fp:
                PLAN_STATS["served"] += 1
                role, snap = "served", m[1]
            else:
                fl = _PLAN_FLIGHTS.get(key)
                if fl is None:
                    fl = {"fp": fp, "done": threading.Event(), "result": _NO_MEMO}
                    _PLAN_FLIGHTS[key] = fl
                    role = "lead"
                elif fl["fp"] == fp:
                    role = "join"
                else:
                    PLAN_STATS["alone"] += 1
                    role = "alone"
        if role == "served":
            return copy.deepcopy(snap)
        if role == "alone":
            return _NO_MEMO
        if role == "lead":
            res = _NO_MEMO
            _IN_PLAN.on = True
            try:
                res = plan(hist_dir, free_mb, keep_recent, _fresh=True)
            finally:
                _IN_PLAN.on = False
                same = False
                if res is not _NO_MEMO:
                    try:
                        same = plan_fingerprint(hist_dir, free_mb, keep_recent) == (key, fp)
                    except Exception:
                        same = False
                with _PLAN_LOCK:
                    PLAN_STATS["led"] += 1
                    if _PLAN_FLIGHTS.get(key) is fl:
                        del _PLAN_FLIGHTS[key]
                    if same:
                        snap = copy.deepcopy(res)
                        fl["result"] = snap
                        if len(_PLAN_MEMO) >= _PLAN_MEMO_MAX:
                            _PLAN_MEMO.clear()
                        _PLAN_MEMO[key] = (fp, snap)
                    else:
                        _PLAN_MEMO.pop(key, None)
                    fl["done"].set()
                try:
                    _remember_plan(_plan_call_key(hist_dir, free_mb, keep_recent), res)
                except _Unkeyable:
                    pass
            return res
        if not fl["done"].wait(_JOIN_WAIT_S):
            # the computation this caller joined has not finished in _JOIN_WAIT_S (a hung disk, a stuck store):
            # waiting on someone else's hang is worse than computing, so this caller computes its own
            _plan_count("alone")
            return _NO_MEMO
        if fl["result"] is not _NO_MEMO:
            _plan_count("joined")
            return copy.deepcopy(fl["result"])
        # the leader raised, or its inputs moved while it ran: ask again from the top
    _plan_count("alone")
    return _NO_MEMO


def _plan_call_key(hist_dir, free_mb, keep_recent):
    """The QUESTION a plan() call asks, apart from what its inputs hold. -> hashable key, or raises _Unkeyable

    Two calls share a wave only when they read the same tree with the same HERE and TV_HIST, pick the ledger copies
    in the same ORDER (_pick: a call that names its tree, or runs under TV_HIST, reads hist's copy first), and pass
    the same free_mb and keep_recent - the same computation, whatever the files hold at the moment it runs. Unlike
    plan_fingerprint's key this does not fold the order away when one ledger copy exists: that needs the ledgers
    STILL, and a wave exists precisely because something is not."""
    hist = _resolve_hist(hist_dir)
    key = ("wave", hist, os.path.abspath(hist), HERE, os.environ.get("TV_HIST") or "",
           bool(hist_dir) or bool(os.environ.get("TV_HIST")), free_mb, keep_recent)
    try:
        hash(key)
    except Exception:
        raise _Unkeyable("the arguments cannot be keyed")
    return key


def _plan_wave(hist_dir, free_mb, keep_recent):
    """plan() while an input is MOVING: computed fresh, never remembered - and computed ONCE for every caller
    waiting at the same moment. -> dict (this caller's answer) | _NO_MEMO (compute your own)

    ⚠⚠ REG-1437 (#66) — WHILE HE FILMS, THE MEMO NEVER ENGAGED. The footage writer drops a loose hist/f_<ms>.jpg
    about once a second, so hist's own stamp is never RACY_S still, plan_fingerprint raises _Moving on every call,
    and every caller computed alone - the three concurrent index walks REG-1411 was written for, for as long as
    D2R runs. A remembered answer can never be served while an input moves; but concurrent callers can share ONE
    computation, if none of them is handed an answer older than its own call:
      · nothing running for this question -> this caller computes now, alone;
      · a computation IS running -> it began before this call, so it may have read the world as it was before
        this call. This caller joins the NEXT wave instead, which starts only after the running one finishes -
        after every caller waiting on it had arrived - and all of them share that one run.
    The first caller to join a wave runs it (after _JOIN_WAIT_S it runs it beside a hung one). A leader that raises
    shares nothing: its members compute their own. Each member gets a deep copy; nothing is kept afterwards."""
    import copy
    try:
        key = _plan_call_key(hist_dir, free_mb, keep_recent)
    except _Unkeyable:
        _plan_count("alone")
        return _NO_MEMO
    with _PLAN_LOCK:
        st = _PLAN_WAVES.get(key)
        if st is None:
            st = _PLAN_WAVES[key] = {"running": None, "next": None}
        if st["running"] is None:
            w = st["running"] = {"go": threading.Event(), "done": threading.Event(), "result": _NO_MEMO}
            w["go"].set()
            lead = True
        else:
            # a computation is running, and it began before this call: wait for the NEXT one to start
            w = st["next"]
            lead = w is None
            if lead:
                w = st["next"] = {"go": threading.Event(), "done": threading.Event(), "result": _NO_MEMO}
    if not lead:
        if not w["done"].wait(2 * _JOIN_WAIT_S):
            _plan_count("alone")
            return _NO_MEMO
        if w["result"] is _NO_MEMO:
            _plan_count("alone")            # the wave's leader raised: this caller computes its own
            return _NO_MEMO
        _plan_count("coalesced")
        return copy.deepcopy(w["result"])
    if not w["go"].wait(_JOIN_WAIT_S):
        # the running computation has not finished in _JOIN_WAIT_S (a hung disk, a stuck store): run this wave
        # now, beside it. Its members all arrived before this moment, so the answer is still not older than any.
        with _PLAN_LOCK:
            if st["next"] is w:
                st["next"] = None
            w["go"].set()
    res = _NO_MEMO
    _IN_PLAN.on = True
    try:
        res = plan(hist_dir, free_mb, keep_recent, _fresh=True)
    finally:
        _IN_PLAN.on = False
        snap = copy.deepcopy(res) if res is not _NO_MEMO else _NO_MEMO
        with _PLAN_LOCK:
            PLAN_STATS["waves"] += 1
            w["result"] = snap
            if st["running"] is w:
                nxt = st["running"] = st["next"]
                st["next"] = None
                if nxt is not None:
                    nxt["go"].set()
            if st["running"] is None and st["next"] is None and _PLAN_WAVES.get(key) is st:
                del _PLAN_WAVES[key]
            w["done"].set()
        _remember_plan(key, res)
    return res


def _forget_plans():
    """Drop every kept plan and zero the counters (a law's clean slate). -> None"""
    with _PLAN_LOCK:
        _PLAN_MEMO.clear()
        _PLAN_LAST.clear()
        for k in PLAN_STATS:
            PLAN_STATS[k] = 0


def plan_for_reader(hist_dir=None, free_mb=None, keep_recent=KEEP_RECENT):
    """The last plan this process finished for this question. Never starts a wave. -> dict | None

    None: no finished plan yet, so which reels are hidden is UNKNOWN, not an empty shelf.
    Otherwise a copy of that plan plus moving (True when an input is moving now, False when the
    inputs are still, None when that could not be told) and asOf (when the plan finished).
    A reader that called plan() while he films would wait out the next wave. This returns at once.
    """
    import copy
    try:
        key = _plan_call_key(hist_dir, free_mb, keep_recent)
    except _Unkeyable:
        return None
    with _PLAN_LOCK:
        held = _PLAN_LAST.get(key)
    if not isinstance(held, dict):
        return None
    snap = held.get("snap")
    if not isinstance(snap, dict) or snap.get("ok") is not True:
        return None
    moving = None
    try:
        plan_fingerprint(hist_dir, free_mb, keep_recent)
        moving = False
    except _Moving:
        moving = True
    except Exception:
        moving = None
    out = copy.deepcopy(snap)
    out["moving"] = moving
    out["asOf"] = held.get("asOf")
    return out


#: REG-2728 - what the console itself writes INTO a reel folder from the frames already there: the index rebuilt from
#: the frame names, the KAI closer's report, a corrupt index kept aside, and the dot-named thumbnails (.stash_eye_tab.jpg,
#: .tooltip_tile.jpg). None of it is footage, so none of it turns a finished evidence remnant back into a reel.
REMNANT_DERIVED = frozenset(("index.json", "kai_report.json", "index.json.corrupt"))
_REMNANT_MEMO = {}


def remnant_reels(hist):
    """The EVIDENCE REMNANTS on the shelf: reels apply_plan already released whose cited pictures stayed (his §26),
    tombstoned WITH a `kept` list. -> set of reel names. An unreadable tombstone -> an empty set: every reel is then
    planned, and closed, exactly as before.

    The second eye on v3521: the tombstone is written BEFORE the delete, so a trim that failed halfway (a file in use, a
    crash) left a `kept` row over a reel still holding its other frames. A remnant is DONE only when nothing but its kept
    pictures is left; anything more and it is planned again like any reel.

    REG-2728 (#158, measured on his Mac 2026-10-28): "anything more" counted what the console writes back. The KAI
    closer met a remnant with no index and no report, rebuilt the index from the kept pictures and closed the reel again
    (the paid gap funnel and SUPER-ANALYZE deep re-reads on it); the next pass saw index.json and kai_report.json beside
    the kept pictures, planned it, and trimmed them away. 12 reels went round 82 times in the log, 1,258 tombstone rows,
    up to 141 for one reel. REMNANT_DERIVED is not footage, and the closer asks this same function before it closes."""
    path = _tombstone_path(hist)
    try:
        st = os.stat(path)
        key = (path, st.st_mtime_ns, st.st_size)
    except OSError:
        key = None
    kept_of = _REMNANT_MEMO.get(key) if key is not None else None
    if kept_of is None:
        try:
            rows = (_load(path) or {}).get("reels") or []
            kept_of = {}
            for t in rows:
                if isinstance(t, dict) and t.get("kept"):
                    kept_of.setdefault(t.get("reel"), set()).update(str(x) for x in t.get("kept") or ())
        except Exception:
            return set()
        if key is not None:
            _REMNANT_MEMO.clear()
            _REMNANT_MEMO[key] = kept_of
    out = set()
    for r, k in kept_of.items():
        if not _is_reel_dir_name(r):
            continue
        try:
            _left = set(f for f in os.listdir(os.path.join(hist, r)) if not f.startswith(".") and f not in REMNANT_DERIVED)
        except OSError:
            continue
        if _left <= k:
            out.add(r)
    return out


def plan(hist_dir=None, free_mb=None, keep_recent=KEEP_RECENT, *, _fresh=False):
    """What may go, oldest first, and WHY every other reel stays. Writes nothing.

    free_mb: stop once this much has been selected. None = report every eligible reel.

    REG-1411 — on a CONSOLE, a call with the same arguments as one already running JOINS it, and a finished answer
    is SERVED again until one of its inputs moves: plan_fingerprint() names every one of them, and _plan_shared
    says exactly when an answer may be handed over. `_fresh=True` computes, always (the leader's own call).
    """
    if not _fresh:
        _shared = _plan_shared(hist_dir, free_mb, keep_recent)
        if _shared is not _NO_MEMO:
            return _shared
    _plan_count("runs")
    hist = _resolve_hist(hist_dir)
    unreadable = []

    def _pick(fn):
        """First readable copy wins, and every UNREADABLE copy is named. A store that exists and
        will not parse is recorded even when a sibling copy answers, because the reason a caller
        wants to know is 'is my picture of the ledgers complete', not 'did I get a dict'."""
        # ⚠⚠ v2575 REG-570 — A FIXTURE COULD NOT REDIRECT THE DELETER'S LEDGERS, AND ELEVEN TEST
        # CALL SITES BELIEVED IT COULD. This searched HERE before `hist` unconditionally, so
        # `plan(hist_dir=<scratch>)` read Konyo's LIVE chronicle_swept (401 entries) and
        # vault_swept (30) instead of the caller's. Proven: a scratch ledger declaring pages=99
        # for three fixture reels produced `never-chronicle-swept: 3` — his store answered, the
        # fixture's was ignored. Setting TV_HIST did not help either; the read was anchored to
        # HERE and nothing else.
        #
        # The consequence is not a wrong number in a report — it is that every sabotage ever
        # aimed at this chooser was graded against live data it could not control, which is
        # exactly why four claimed defects in it could not be reproduced. [[feedback-fixtures-
        # never-touch-live-data]] guards the FIXTURE, not the call site — so the redirect happens
        # HERE, once, rather than in eleven tests remembering to.
        #
        # ⚠ THE DEFAULT PATH IS UNCHANGED. With no redirect the order is still HERE then hist.
        # Only a caller that explicitly repointed gets its own directory consulted first.
        _redirected = bool(hist_dir) or bool(os.environ.get("TV_HIST"))
        _order = ((os.path.join(hist, fn), os.path.join(HERE, fn)) if _redirected
                  else (os.path.join(HERE, fn), os.path.join(hist, fn)))
        # ⚠⚠ AND "FIRST READABLE WINS" IS WHAT THIS DOCSTRING ALWAYS SAID, while the code said
        # "first NON-EMPTY wins" (`if b and not blob`). They differ on the one case that matters:
        # a readable `{}` is a MEASUREMENT — nothing has been swept — and under the old rule a
        # stale non-empty sibling overruled it, so more reels looked swept and MORE FOOTAGE
        # became eligible. The docstring's rule holds footage; the code's rule released it.
        # [[unknown-stays-unknown]] [[feedback-comments-vs-code]]
        blob, picked = {}, False
        for cand in _order:
            b, st = _load_state(cand)
            if st == "unreadable":
                unreadable.append(os.path.relpath(cand, HERE))
                continue
            if st == "ok" and not picked:
                blob, picked = b, True
        return blob

    chron = _pick("chronicle_swept.json")
    vault = _pick("vault_swept.json")

    try:
        reels = sorted((d for d in os.listdir(hist) if d.startswith("reel_")), key=_reel_ts)
        # 2026-09-28 — an EVIDENCE REMNANT is a reel already released whose cited pictures stayed (apply_plan, his
        # §26): tombstoned WITH a `kept` list. It is not a new candidate and not owed - replanning it would release
        # it again every pass and read as a stalled drain. It is listed in `remnants`, never silently dropped.
        _remnants = remnant_reels(hist)
        _remnant_list = sorted(r for r in reels if r in _remnants)
        reels = [r for r in reels if r not in _remnants]
    except OSError as e:
        # ⚠⚠ v3393 — THE SAME DEFECT AS end_routes.report, AT ITS SOURCE. The footage tree
        # is created inside tv_diablo._film_loop, so a console that has never filmed has no
        # frames/hist BY DESIGN. Answering "cannot read <path>" made his Windows box report
        # itself broken when nothing had ever been recorded on it — and every consumer of
        # plan() inherited that, including end_routes._safety and the shelf, which drew a
        # 0x0 box. A legitimate EMPTY must not wear the clothes of a failure.
        # ⚠ NO PATH IN THIS MESSAGE: a Windows profile can carry a non-ASCII character and
        # printing it crashes a cp1255 console WHILE reporting. [[unknown-stays-unknown]]
        if getattr(e, "errno", None) == _errno.ENOENT or not os.path.exists(hist):
            # v3400 — A FLAG, NOT A SENTENCE, because the consumer must not string-match prose.
            # v3393 wrote the sentence above and every consumer still had to GUESS what kind of
            # failure this was. A downstream reader that greps English breaks the moment the
            # wording improves. [[unknown-stays-unknown]]
            return {"ok": False, "candidates": [], "kept": [], "neverRecorded": True,
                    "why": ("no footage tree on this machine yet — nothing has been "
                            "recorded here, so there is no reel to plan for")}
        return {"ok": False, "why": "cannot read %s: %s" % (hist, e), "candidates": [], "kept": [],
                "neverRecorded": False}

    # v2056 — sessions whose witnesses survive without the frames, read ONCE per plan.
    global _DURABLE
    _dur_set, _durable_ok, _durable_why = _durable_sessions(HERE)
    # REG-1647 — PUBLISHED ONLY WHEN IT WAS READ. A failed load stays None (UNKNOWN), so a caller
    # outside plan() is never handed an empty set meaning "nothing is durable"; plan's own rules use
    # the local set, and its `ledger-unreadable` rule already holds every reel in that case.
    _DURABLE = set(_dur_set) if _durable_ok else None
    if not _durable_ok:
        # NAME THE REAL REASON. `_durable_sessions` returns ok=False both when a store will not
        # parse AND when frame_authority itself could not be imported — and saying "vault_accum.json
        # / vault_seen.json will not parse" about two perfectly readable files sends him to fix the
        # wrong thing. Right hold, wrong reason is still a wrong report.
        unreadable.append("the durable witness index could not be read"
                          if _durable_why is None else _durable_why)
    # v2122 (#32) — AND A TREE WITH NO INDEX AT ALL HOLDS TOO. frame_authority refuses to delete a
    # SINGLE FRAME when `haveIndex` is False — nothing there can prove a frame is not the only
    # record of what it saw — and this module, which deletes the WHOLE REEL those frames live in,
    # never asked: `haveIndex` appeared zero times in this file. `ok` is True for a complete
    # picture of NOTHING, so the two deleters disagreed by construction on the same footage, and
    # footage has no undo. [[unknown-stays-unknown]] [[feedback-contradiction-is-the-finding]]
    _have_index = False
    try:
        import frame_authority as _fa_idx
        _have_index = bool(_fa_idx.witness_index(HERE).get("haveIndex", True))
    except Exception:
        _have_index = False
    # ⚠⚠ v2576 REG-571 — JUNK DIRECTORIES ATE THE RECENT SHIELD. `_reel_ts` returns
    # float("inf") for a name it cannot parse, deliberately, "so it is the last thing anyone
    # deletes" — true of the junk dir itself, and it says nothing about that junk DISPLACING real
    # reels out of the shield. Measured: five `reel_backup_*` siblings alongside five real reels
    # with keep_recent=3 took all three slots, and eligible went 2 -> 5. Three reels lost their
    # protection and the coverage line still read `recent: 3`, so the instrument certified a rule
    # that had stopped protecting anything.
    #
    # The shield is the newest PARSEABLE reels now. An unparseable dir keeps its inf sort key and
    # is still last to be deleted; it simply cannot stand in for a real reel.
    #
    # ⚠ REG-572, same line — a NEGATIVE keep_recent silently removed the shield entirely.
    # `--keep-recent` is bare `type=int`, `if keep_recent` is truthy for -6, and `reels[-(-6):]`
    # is a SUFFIX FROM THE FRONT, which for 5 reels is empty. Measured: eligible 2 -> 5. A
    # negative shield is not a smaller shield, it is no shield, and it arrived through an
    # argument nobody validated. Non-negative is enforced here rather than at one call site.
    if keep_recent is not None and keep_recent < 0:
        raise ValueError("keep_recent must be >= 0, got %r — a negative window silently drops "
                         "the recent shield entirely rather than shrinking it" % (keep_recent,))
    # #84 (REG-1517) — ONE spelling of "the newest keep_recent": the drain's blocked-upstream reading
    # asks the same question of the same names, and a second sort there is how the two would drift.
    recent = recent_shield(reels, keep_recent)
    try:
        import frame_authority as _fa
        _fixtures = _fa.test_referenced_reels()
    except Exception:
        _fixtures = set()          # cannot ask -> hold nothing extra, but never hold LESS safely:
                                   # the other rules still apply and eligibility is unchanged
    # v2815 (#45) — ONE index walk per plan, not one per reel: the frame index is ~7,600 files.
    try:
        _proof_hold, _proof_why = proof_reels(hist)
    except Exception as _e:
        _proof_hold, _proof_why = None, "the proof scan itself failed (%s)" % type(_e).__name__
    candidates, kept, freed = [], [], 0.0

    # ── v2068 — A RULE THAT NEVER RUNS MUST SAY SO ─────────────────────────────────────────────
    # Every reason below is a REASON NOT TO DELETE, and they are checked in order, so an earlier
    # one hides every later one. MEASURED on his 35 reels: 12 never-swept, 11 sealed-with-0-pages,
    # 5 recent, 1 vault-owes, 6 eligible — and the v2056 rule ("this reel produced rows and none of
    # them are banked, so the frames ARE the record") fired ZERO times. On his data a working v2056
    # and a deleted one are indistinguishable, which is the mirror of a blind fixture: real data,
    # right gate, still green.
    #
    # So the plan now counts its own branches and names the ones that never ran. NEVER FIRED is
    # reported as UNMEASURED, never as "fine" and never as "broken" — this run simply contains no
    # reel that reaches it, and that is a fact about the footage, not about the rule.
    # [[gate-blind-to-unexercised-input]] [[unknown-stays-unknown]]
    # v2383 — the tuple now lives at MODULE scope (see RULES above). It stayed local for as
    # long as nothing outside plan() needed to know what this module can conclude; reel_story
    # draws a stage per verdict, so "every rule has a stage" is now a contract another file must
    # be able to check. A test that had to re-list these by hand would be a copy that drifts.
    # [[copy-drift]]
    # ⚠ v2316 — "not-extracted" WAS DECLARED HERE AND IS GONE. v2312 tried to make retention hold a
    # reel whose seal names nothing it took; that fix was WITHDRAWN (every existing seal predates
    # the contract, so the prune would never have fired again). The code went and the DECLARATION
    # stayed — an orphan tag no code path can ever reach, which coverage then reported as an
    # unmeasured rule for ever. A withdrawn change must take its declarations with it, or the
    # roster slowly fills with rules that describe work nobody does.
    # [[the-unjoined-end]] [[label-outlived-referent]]
    hits = dict((r, 0) for r in RULES)

    # v2383 — THE TAG TRAVELS WITH THE REEL, not only into the counter. `hits` says how many reels
    # were held for each reason; nothing said WHICH reason held THIS reel except the prose, so a
    # caller wanting to draw the lifecycle would have had to regex an English sentence. A reader
    # that pattern-matches prose is a guard on the sentence, not on the rule. [[source-reading-guard]]
    _last = [None]

    def _rule(tag, why):
        hits[tag] += 1
        _last[0] = tag
        return why

    for reel in reels:
        path = os.path.join(hist, reel)
        size = _dir_mb(path)
        # ⚠⚠ REG-562 — TWO DIFFERENT QUESTIONS, AND v2560 QUIETLY MERGED THEM. `_entry` was fixed
        # to return a present-but-EMPTY record faithfully (membership, not truthiness) because the
        # REPORT was lying about which reels had a ledger row. But the branches below ask
        # `ce is None` / `ve is None` to mean *this lane has not finished with the reel*, and after
        # that fix an empty `{}` stopped answering None — so a reel whose ledger row exists and
        # says NOTHING would skip the HOLD branches and fall toward releasable.
        #
        # Measured on his tree: chronicle_swept 401 entries, vault_swept 30, **0 falsy in either**,
        # so nothing moved today. That is luck, not design, and it is the DELETER. The report's
        # question is "is there a row?"; the deleter's question is "does the row SAY anything?" —
        # `_told` asks the second one, so an empty row holds exactly as an absent one does.
        def _told(e):
            return e if e else None

        ce, ve = _told(_entry(chron, reel)), _told(_entry(vault, reel))
        # ⚠⚠ v2576 REG-573 — A NON-INTEGER PAGE COUNT REACHED THE TOMBSTONE. `int()` accepts
        # True (bool is a subclass of int) and raises on "many" or [1,2,3]. Measured: `pages:
        # true` made all five reels ELIGIBLE and stamped the permanent record of an irreversible
        # act with *"read (1 pages) and sealed by BOTH lanes"* — a boolean rendered as a page
        # count. And `pages: "many"` let a ValueError escape plan() entirely, which
        # _retention_loop swallows in `except Exception: pass`, so the pass dies silently with
        # the console's last sentence frozen on screen.
        #
        # A page count that is not a whole number is not a small count, it is an UNREADABLE
        # ledger — which is a state this module already has, and which HOLDS. [[unknown-stays-unknown]]
        _pv = (ce or {}).get("pages")
        if _pv is None or _pv == "":
            pages = 0
        elif isinstance(_pv, bool) or not isinstance(_pv, int):
            unreadable.append("%s: pages=%r is not a whole number" % (reel, _pv))
            pages = 0
        else:
            pages = _pv

        if not _have_index:
            why = _rule("no-witness-index",
                        "HELD — no durable witness store exists yet, so nothing here can prove "
                        "this reel's frames are not the only record of what it saw. The FRAME "
                        "deleter holds every frame in this reel for exactly that reason; a reel "
                        "deleter that released it would destroy what the frame deleter is "
                        "protecting.")
        elif unreadable:
            # v2079 — FIRST, and it holds EVERYTHING. Not a per-reel judgement: a ledger that will
            # not parse means this module's picture of what has been banked is unknown for every
            # reel at once, so there is no reel it can honestly release. Deliberately ahead of
            # test-fixture so the REPORT names the real reason rather than a coincidental one.
            why = _rule("ledger-unreadable",
                        "HELD — %s will not parse, so nothing here knows which witnesses are "
                        "banked. 'I could not read the ledger' is not 'there are no witnesses', "
                        "and footage has no un-delete. Fix or remove the file and re-run."
                        % ", ".join(sorted(set(unreadable))))
        elif reel in _fixtures:
            # ── v2069 — A REEL A TEST OPENS IS A FIXTURE, WHATEVER THE LEDGERS SAY ─────────────
            # Learned the expensive way, on a prune that had already run: six reels went as
            # "sealed by both lanes, has given up its information" and THREE were named by
            # tv/test_control.py. The suite did not go red — those cases skipTest when the footage
            # is absent — so a real check silently became a permanent skip.
            #
            # It had happened twice before and been absorbed: two cases already read "fixture reel
            # ... was pruned — PERMANENTLY skipped in both venues". Of the 17 reels the suite names,
            # EIGHT are already gone. Nobody was wrong at any step; the deleter asks the ledgers,
            # and the ledgers have no idea a test exists.
            # [[feedback-blind-fixture-green-gate]] [[gate-blind-to-unexercised-input]]
            why = _rule("test-fixture",
                        "the TEST SUITE opens this reel by name — deleting it does not turn a test "
                        "red, it turns one into a permanent skip, which is worse")
        elif reel in recent:
            why = _rule("recent",
                        "one of the %d most recent — kept so a re-sweep always has real footage"
                        % keep_recent)
        elif ce is None and not _proven_empty(reel):
            why = _rule("never-chronicle-swept",
                        "never chronicle-swept — it has not been read even once")
        elif pages < MIN_PAGES and not _proven_empty(reel) and not _no_chronicle_to_find(reel):
            why = _rule("zero-pages",
                        "sealed with 0 pages — that is 'this reader found nothing', not 'done'; "
                        "the engine reopens these when the prompt improves")
        elif _panels_never_banked(reel, ve):
            # ⚠⚠⚠ v2875 — THE SAFETY HALF OF _no_chronicle_to_find, AND IT IS NOT OPTIONAL.
            # Lifting the chronicle hold exposed eleven reels the chain then called
            # "sealed by BOTH lanes — it has given up its information". MEASURED, they had not:
            #     reel_s_1787508759592_46621   73 panels in  80 frames   148 MB
            #     reel_s_1787512325134_62795   64 panels in  67 frames   124 MB
            #     reel_s_1788105158696_89699   49 panels in  49 frames    88 MB
            # A vault SEAL existed for each, with ZERO rows behind it — the same "a seal that
            # records nothing" defect as the chronicle side, and the vault lane has never run
            # (reads: 0). `rows-not-banked` below could not catch them: it fires only when rows
            # EXIST and are not durable, never when the count is zero and the panels are real.
            #
            # Konyo's rule is the order, not just the outcome: *"all of the reels get extracted
            # with information thats needed"* BEFORE the tombstone. Panels on film with nothing in
            # the ledger is unextracted information, whatever any seal says.
            # [[unknown-stays-unknown]] [[feedback-contradiction-is-the-finding]]
            why = _rule("panels-never-banked",
                        "a FULL survey found panel frames here and the vault ledger holds NO row "
                        "from this reel — its stash rows have never been extracted, so deleting it "
                        "destroys the only copy. A seal is not an extraction.")
        elif (ve or {}).get("rows") and _reel_ts_key(reel) not in _dur_set:
            # v2056 — READ IS NOT BANKED. This reel produced rows and none of them reached a store
            # that outlives the frames, so deleting it destroys the only record of those witnesses.
            why = _rule("rows-not-banked",
                        "the sweep read %s row(s) here and NONE of them are in the ledger yet — the "
                        "witnesses live only in these frames, so this reel is the record. Apply the "
                        "vault proposal (or let a sweep write vault_seen.json) and it becomes "
                        "eligible." % (ve or {}).get("rows"))
        elif ve is None and _vault_lane_owes(path) and not _proven_empty(reel):
            why = _rule("vault-owes",
                        "the VAULT lane has never swept it — it still owes the vault manager its "
                        "stash rows" + ("" if vault else
                                        (" (vault_swept.json will not parse)" if unreadable
                                         else " (vault_swept.json does not exist yet)")))
        elif _proof_hold is None:
            # ⚠⚠ CANNOT TELL, SO CANNOT DELETE. proof_reels() returns None when the evidence store,
            # frame_ref, or the index could not be read. Deleting on an unknown is the one
            # direction that cannot be undone. [[unknown-stays-unknown]]
            why = _rule("holds-proof",
                        "HELD — this console cannot tell which frames are cited as proof (%s), and "
                        "a reel deleted on an unknown cannot be brought back." % (_proof_why or "?"))
        elif reel in _proof_hold:
            # ⚠⚠ v2815 (#45) — THE RECEIPT RULE, FINALLY JOINED. frame_ref has stated it since
            # v2364 and AST-confirmed nothing in production ever called it. MEASURED on his tree:
            # 739 of 10,318 cited frames already resolve to nothing on disk.
            #
            # ⚠ AND ITS POSITION IN THIS CHAIN IS DELIBERATE, LEARNED THE HARD WAY. v2814 put it
            # FIRST and four gates went red — the chain's own comment says "an earlier one hides
            # every later one", and holds-proof at the top hid test-fixture, the unreadable-ledger
            # branch and the prune-cycle cases, making three of them unreachable. It belongs HERE:
            # the last hold before a reel can become eligible. Every more SPECIFIC reason is still
            # reported first (a fixture is a fixture, recent is recent), and this only catches the
            # reels that would otherwise have been deleted. [[regression-guard]]
            why = _rule("holds-proof",
                        "HELD — a frame in this reel is the receipt for a NAMED claim in the "
                        "chronicle. Deleting it would leave the claim standing with its proof "
                        "destroyed, which is the one loss this repo cannot undo.")
        else:
            if free_mb is not None and freed >= free_mb:
                why = _rule("target-met",
                            "eligible, but the target was already met — this stops as soon as it can")
                kept.append({"reel": reel, "mb": round(size, 1), "why": why, "pages": pages,
                             "tag": _last[0]})
                continue
            # ⚠⚠ v2314 — I TIGHTENED THIS IN v2312 AND IT WAS AN OVER-CORRECTION. WITHDRAWN.
            #
            # After deleting 388.6 MB of his footage unattended on 2026-08-30 I made eligibility
            # require the seal to satisfy frame_authority's extraction contract. Three deliberate
            # cases went red, and they were right: EVERY seal on his tree predates that contract,
            # so the change would have stopped the prune firing on any existing reel — the exact
            # opposite of "automatically prune its not a question.. needs to be defaulted in".
            #
            # And re-examined honestly, the RULE was not the defect. reel_s_1786922954749_12579 had
            # 286 pages read by the chronicle lane and a vault seal confirming no stash screen
            # existed to take anything from. Both lanes were genuinely finished with it.
            # frame_authority is stricter because it answers a DIFFERENT question — may this FRAME
            # go, protecting the witness frames behind his vault rows — not may this REEL go. Two
            # authorities at two granularities is correct; collapsing them was my error.
            #
            # What actually went wrong that day was mine and not the code's: I swept a reel to
            # clear a backlog, which made it eligible, while telling him nothing could delete
            # because I had checked _PRUNE_SAFE_TO_RUN and not retention_may_act().
            # [[feedback-suspect-the-instrument]]
            freed += size
            candidates.append({"reel": reel, "mb": round(size, 1), "pages": pages,
                               "why": _rule("eligible",
                                            "read (%d pages) and sealed by BOTH lanes — it has "
                                            "given up its information" % pages),
                               "tag": "eligible"})
            continue
        kept.append({"reel": reel, "mb": round(size, 1), "why": why, "pages": pages,
                             "tag": _last[0]})

    # NOT REACHED and NOT APPLICABLE are two different answers, and only one of them is a gap.
    # `target-met` can only fire when a free_mb target was asked for; with no target it is
    # unreachable BY CONSTRUCTION, not unexercised by the footage. Reporting them together would
    # make a structurally-inert branch look like a rule that quietly stopped working.
    # `ledger-unreadable` is structurally inert on a healthy tree, exactly like `target-met` with no
    # target — reporting it as NEVER REACHED would train him to ignore the list that names real gaps.
    _na = set() if free_mb is not None else {"target-met"}
    if not unreadable:
        _na.add("ledger-unreadable")
    never = [r for r in RULES if not hits[r] and r not in _na]
    na = sorted(r for r in _na if not hits[r])
    _reader_out = {"ok": True, "hist": hist, "candidates": candidates, "kept": kept,
            # ⚠⚠ v3225 — `freeMb` DOES NOT MEAN FREE DISK. It is `freed`: the megabytes
            # THIS PLAN WOULD RELEASE. With no candidates it is 0.0, which is correct
            # arithmetic under a word naming a different quantity — and control_app
            # publishes it into a dict that ALSO carries `freeGb` (actual free disk).
            # MEASURED 2026-09-16: `{"freeMb": 0.0, "freeGb": 9.0}` in one payload, one
            # letter apart, meaning opposite things. Read as the Mb twin of freeGb it
            # says the disk is FULL. `eligibleMb` is the true name and the one to use;
            # `freeMb` stays only so older readers keep working.
            # [[label-outlived-referent]] [[d2r-g5-budget-unit-collision]]
            "eligibleMb": round(freed, 1),
            "freeMb": round(freed, 1), "onDisk": len(reels), "remnants": _remnant_list,
            "vaultLedger": bool(vault),
            # Published so a caller cannot repeat the mistake this fix corrects: an empty
            # `candidates` because everything is held reads identically to an empty one because
            # nothing was eligible, unless the reason is on the payload.
            "unreadable": sorted(set(unreadable)),
            "coverage": dict(hits), "neverFired": never, "notApplicable": na,
            "coverageSay": (("every rule this run could reach was exercised by the footage"
                             if not never else
                             "%d rule(s) were NEVER REACHED on these %d reel(s) — %s. That is "
                             "UNMEASURED, not fine and not broken: nothing in this footage gets far "
                             "enough down the chain to test them."
                             % (len(never), len(reels), ", ".join(never)))
                            + ("" if not na else
                               " (%s cannot fire without a free_mb target and is not counted as a "
                               "gap.)" % ", ".join(na))),
            # v2080 — AND `say` MUST NOT CONTRADICT `unreadable`. It branched on bool(vault),
            # which is falsy for BOTH an absent store and a corrupt one, so a ledger that would not
            # parse was reported to him as "vault_swept.json does not exist, so the vault manager
            # has never sealed anything." The `unreadable` field said the opposite two keys away —
            # and the sweep consumer (control_app.py) copies ONLY `say` onto his console, so the
            # true field never reaches a screen. The most alarming state was described as the most
            # innocent one. [[unknown-stays-unknown]] [[label-outlived-referent]]
            "say": ("%d reel(s) may go, freeing %d MB" % (len(candidates), round(freed))
                    if candidates else
                    "NOTHING is safe to delete yet — and that is an answer, not a failure. " +
                    ("%s will NOT PARSE, so every reel is held: nothing here knows which "
                     "witnesses are banked, and that is not the same as knowing there are none."
                     % ", ".join(sorted(set(unreadable))) if unreadable else
                     "no reel has been swept by BOTH lanes; vault_swept.json does not exist, so the "
                     "vault manager has never sealed anything." if not vault else
                     "every reel is recent, unread, or still owed to a lane."))}
    try:
        _remember_plan(_plan_call_key(hist_dir, free_mb, keep_recent), _reader_out)
    except _Unkeyable:
        pass
    return _reader_out


def _on_path():
    """HERE on sys.path ONCE. -> None

    ⚠⚠ REG-1413 — `sys.path.insert(0, HERE)` ran inside _tombstone_path on EVERY call, and plan() asks it on
    every run (twice on his live tree, once per fixture), so a console grew sys.path by one or two entries per
    plan, for ever. MEASURED 2026-09-29: +50 entries over 50 calls; a failed import then walks every entry and
    stats each one - 1.1 ms with 6 entries, 15.9 ms with 1,000, 153 ms with 10,000 on the Mac, and a stat is
    dearer on Windows."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)


def _tombstone_path(hist=None):
    """v2080 — RESOLVE AT CALL TIME, NOT AT IMPORT.

    `TOMBSTONE_PATH = os.path.join(HERE, ...)` was bound when the module loaded, so a test that
    repoints `rr.HERE` at a fixture tree — which every retention test does — still wrote its
    tombstones into HIS tree. The full gate run proved it: 89 tombstones carrying 2017 fixture
    stamps sitting in his real reel_tombstones.json, and the byte-identical canary caught the file
    moving during a run with his console down.

    Nothing of his was deleted (all 30 reels intact, and the 6 real entries are an earlier
    deliberate prune) — but a deleter's record of what it removed is not a file tests may write to,
    and "it happened to be harmless this time" is not a property to rely on.

    A constant computed at import is a fixture guard with a race built into it: the guard is only
    as good as the moment it was evaluated. [[feedback-fixtures-never-touch-live-data]]
    """
    # v2086 — AND IT ANSWERS FROM THE TREE BEING DELETED, when the caller knows which one that is.
    # It resolved from rr.HERE and TV_HIST only, so a caller that repointed NEITHER — passing
    # hist_dir straight to plan() — deleted from one tree and recorded the tombstones into HIS.
    # `_tombstone(hist, cands)` has always RECEIVED that path and ignored it. Not exercised today
    # (the suite patches the resolver, _retention_once sets TV_HIST) but a deleter's record of what
    # it removed should not be one indirection away from the footage it removed.
    # [[feedback-fixtures-never-touch-live-data]]
    if hist:
        # ⚠ `_under` is NOT in this module — it lives in tv_diablo, and the first cut called it
        # bare. That is a NameError, and the `except Exception: pass` right here would have
        # swallowed it and fallen through to the old behaviour: a guard that can never pass, hiding
        # inside its own error handling. The muleById defect, one more time.
        #
        # And it is imported rather than re-derived because v1897 says why: this comparison "was
        # written four times tonight as h.startswith(root + os.sep), and on Windows that is a coin
        # flip". His Windows machine is the other half of this project. [[copy-drift]]
        try:
            _on_path()
            from tv_diablo import _under as _is_under
        except Exception:
            _is_under = None
        if _is_under is not None:
            try:
                h = os.path.realpath(hist)
                base = os.path.dirname(h) if os.path.basename(h) == "hist" else h
                if not _is_under(h, HERE):
                    return os.path.join(base, "reel_tombstones.json")
            except Exception:
                pass
    try:
        _on_path()
        import tv_diablo as _tvd
        return os.path.join(_tvd._fixture_root(HERE), "reel_tombstones.json")
        # ⚠⚠ v2788 — NARROWED FROM `except Exception`. A blanket catch here also swallowed a
        # runtime failure OF THE RULE ITSELF and answered HERE — his live tree — to a caller that
        # had explicitly asked for a fixture world. `shadow_ledger._ledger_path` and
        # `retro_gate._ledger_path` already carry the correct template and say why: *"If the root
        # rule is broken that must surface, not resolve to his tree."* ImportError means tv_diablo
        # genuinely is not importable and HERE is then the honest answer; anything else must
        # propagate. Found by a census, not by hand. [[copy-drift]] [[unknown-stays-unknown]]
    except ImportError:
        return os.path.join(HERE, "reel_tombstones.json")


TOMBSTONE_PATH = _tombstone_path()   # back-compat for readers; the writers call the function


def _filmed_ts(reel_dir, ix=None):
    """When was this reel FILMED? -> int ms, or None if nothing can say.

    Two sources, both measured at 40 of 40 on his shelf, asked cheapest-first:
      1. the frame NAMES — the recorder stamps every frame `f_<epoch-ms>.jpg`, which is the same
         pair `reconstruct_index` rebuilds a lost index from, so it survives a missing index;
      2. the index's own frame rows, whose `ts` is that stamp already parsed.

    ⚠ The EARLIEST stamp, not the latest: the question is when the reel began, and a reel is
    written over minutes. And None when neither answers — a guessed age on a deletion record is
    worse than an absent one. [[unknown-stays-unknown]]
    """
    best = None
    try:
        for f in os.listdir(reel_dir):
            if not (f.startswith("f_") and f.endswith(".jpg")):
                continue
            try:
                v = int(f[2:-4])
            except Exception:
                continue
            if v > 1e12 and (best is None or v < best):
                best = v
    except Exception:
        pass
    if best is not None:
        return best
    for row in ((ix or {}).get("frames") or []):
        if isinstance(row, dict) and isinstance(row.get("ts"), (int, float)) and row["ts"] > 1e12:
            v = int(row["ts"])
            if best is None or v < best:
                best = v
    return best


def _tombstone(hist, cands):
    """Write down what a reel WAS before its frames go.

    Konyo: "after the sweep ... data needs to be extracted and ledgered and counted for items as
    witnesses so when they get pruned they continue to exist on record."

    apply_plan used to rmtree and return a count, so a deleted reel left NOTHING behind — not its
    id, not how much was read from it, not why it was judged spent. The rows it produced live in the
    ledger, but the reel itself simply stopped having existed, and "I never recorded that" and "that
    was pruned in August" became the same answer.

    Written BEFORE the delete and flushed to disk, so a crash mid-delete leaves a record of MORE
    than was removed rather than less. Returns the rows it wrote; a failure here is reported and
    does NOT block the delete he asked for — but it is never silent.
    """
    rows = []
    for c in cands or []:
        d = os.path.join(hist, c["reel"])
        rec = {"reel": c["reel"], "session": _reel_ts_key(c["reel"]),
               "mb": c.get("mb"), "pages": c.get("pages"), "why": c.get("why"),
               "deletedTs": int(time.time() * 1000)}
        try:
            rec["frames"] = len([f for f in os.listdir(d) if f.endswith(".jpg")])
        except Exception:
            rec["frames"] = None          # UNKNOWN, never 0 — nobody counted
        try:
            with open(os.path.join(d, "index.json"), encoding="utf-8") as fh:
                ix = json.load(fh) or {}
            rec["focus"] = ix.get("focus") or None
            # ⚠⚠ REG-538 — THIS READ TWO KEYS NO INDEX HAS EVER CARRIED, and wrote None 410 times
            # out of 410. Measured on his shelf: 0 of 40 indexes carry `startedTs`, 0 carry `ts`.
            # So the one door with no undo recorded WHAT it deleted and WHEN it deleted it, and
            # never HOW OLD THE FOOTAGE WAS — the question you would actually ask after a bad
            # prune. Both real sources exist and both cover 40 of 40: the frame names, which the
            # recorder stamps as f_<epoch-ms>.jpg, and the index's own frame rows. Ask them, in
            # that order, and keep None only when neither can answer. [[unknown-stays-unknown]]
            rec["startedTs"] = (ix.get("startedTs") or ix.get("ts")
                                or _filmed_ts(d, ix) or None)
        except Exception:
            rec["focus"] = None
            rec["startedTs"] = _filmed_ts(d, None) or None
        if isinstance(c.get("kept"), list):
            rec["kept"] = c["kept"]
        rows.append(rec)
    try:
        old = _load(_tombstone_path(hist))
        prev = old.get("reels") if isinstance(old, dict) else None
    except Exception:
        prev = None
    blob = {"reels": (prev or []) + rows, "updatedTs": int(time.time() * 1000)}
    # ⚠⚠ v2949 — THE MOUTH OF THE RIVER SAYS WHO CLOSED IT OUT. Task #69.
    # `reel_tombstones.json` is the record of what retention actually deleted — 446 reels and
    # 5,768 MB reclaimed — and it could not say what produced it. Chosen as the next writer to
    # join because its single-writer rule is already a GATED LAW (test_reel_reaper.py:163), its
    # shape is flat `{reels, updatedTs}`, and every reader takes `blob["reels"]` rather than
    # enumerating the top level — so a `_prov` key here cannot move a count.
    # ⚠ GUARDED, and it must be: a store that cannot be stamped is still a store worth writing.
    # Provenance is a label on the data, never a precondition for keeping it. Same shape as the
    # block proven at ledger_highwater.py. [[the-unjoined-end]]
    # ⚠ NEVER do this to a ROW-KEYED store (retro_triage, chron_hunt_memory, main_character,
    # capture_doors): a top-level `_prov` there becomes a FAKE ROW that blueprint.py publishes as
    # a reel count of 456 and printer_reach admits as a reel. [[zero-needs-a-denominator]]
    try:
        import provenance as _PV
        blob = _PV.stamp(blob, by='reel_retention')
    except Exception:
        pass
    dest = _tombstone_path(hist)
    tmp = dest + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(blob, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, dest)
    return rows


def _is_reel_dir_name(name):
    """REG-1918 - one path segment named like a reel ("reel_..."): never "", ".", "..", or anything with a separator."""
    return (isinstance(name, str) and name.startswith("reel_") and name not in (".", "..")
            and "/" not in name and "\\" not in name and os.sep not in name and "\0" not in name)


def _is_child_dir(hist, name):
    """REG-1918 - `hist/name` resolves to a directory DIRECTLY under hist (a symlink out of the shelf is not)."""
    try:
        h = os.path.realpath(hist)
        d = os.path.realpath(os.path.join(hist, name))
        return os.path.dirname(d) == h and d != h
    except Exception:
        return False


def apply_plan(p, yes=False):
    """Delete what plan() selected. Refuses without an explicit yes — this is not undoable."""
    if not yes:
        return {"ok": False, "why": "refusing to delete without --yes; run without --apply to read the plan"}
    # ⚠⚠ v3050 — THE LOCK, ON THE ONE LINE THAT DELETES HIS FOOTAGE. `frame.release` is described
    # by self_arming as "the last check before deletion" and until now it checked nothing: it
    # scored, drew a padlock, and the rmtree below ran regardless. A scouted pass found this is
    # the only deleter — `shutil.rmtree(path)` a few lines down is the single line that removes
    # frame pixels, and both live doors (the auto-prune tick and the CLI) funnel through here.
    #
    # ⚠ BEFORE THE TOMBSTONE, NOT AFTER. v2069 put the record down first so a crash halfway leaves
    # a tombstone for MORE reels than were removed rather than fewer — deliberately erring toward
    # over-recording. A refusal must land BEFORE that, or a locked door still writes a tombstone
    # for footage that was never touched, and the ledger would claim deletions that never happened.
    #
    # ⚠ DESTRUCTIVE — "deletes footage — there is no undo" in its sibling's words — so under
    # v3042's split this fails closed on ANY refusal, a stale census included. A prover that has
    # not caught up is reason enough not to delete.
    try:
        import self_arming as _sa_fr
        _fr_ok, _fr_why = _sa_fr.may("frame.release")
    except Exception as _fr_e:
        _fr_ok, _fr_why = False, ("the lock could not be read (%s), which is UNKNOWN and fails "
                                  "closed" % type(_fr_e).__name__)
    if not _fr_ok:
        return {"ok": False, "why": "frame.release is LOCKED — %s" % _fr_why,
                "removed": [], "failed": [], "tombstone": None}
    # v2069 — THE RECORD GOES DOWN FIRST. Written before a single rmtree, so a crash halfway leaves
    # a tombstone for more reels than were actually removed rather than for fewer.
    # ⚠⚠ 2026-09-28 — HIS §26 AND HIS v2056, BOTH. v2056: a reel whose sightings are banked may go - the record
    # outlives the frames. §26: "the evidence linked and attached with the picture being able to be clicked" - so the
    # PICTURES a vault item stands on must outlive their reel. This loop used to rmtree every candidate whole (Grok's
    # f189f767 recorded a `kept` list and deleted it anyway). Now, BEFORE the tombstone, each released reel names its
    # evidence pictures - a frame behind a vault row (witness_index `frames`) or one a WATCHED/PROVEN/HARDENED item
    # stands on (`cited`) - and only those stay, at their own path, so /frame and the lightbox still open them.
    # ⚠ NOT keep_cited(): that applies EVERY frame_authority keep-reason (its own seal store, a missing index), which
    # kept whole reels the plan had already cleared and freed nothing. The plan decides the reel; this only spares
    # its evidence. UNKNOWN (the evidence ledger will not parse) touches nothing in any reel.
    # [[the-unjoined-end]] [[unknown-stays-unknown]]
    _evid, _ewhy = None, ""
    try:
        import frame_authority as _fak
        _wit = _fak.witness_index(HERE)
        _cit = _wit.get("cited", False)
        # the second eye on v3521: `ok` False means a witness STORE would not parse, so `frames` is a PARTIAL index -
        # a picture named only in that store would read as "not evidence" and go. A partial index holds, like cited.
        _bad = sorted(k for k, v in (_wit.get("perStore") or {}).items() if v is None)
        if _cit is None:
            _ewhy = "the vault evidence ledger could not be read"
        elif not _wit.get("ok", False) or _wit.get("frames") is None:
            _ewhy = ("a witness store would not parse (%s), so which pictures are evidence is only PARTLY known"
                     % (", ".join(_bad) or "the index said it is partial"))
        else:
            _evid = set(_wit.get("frames")) | set(_cit or ())
    except Exception as _ke:
        _ewhy = "the witness index could not be read (%s)" % type(_ke).__name__
    removed, failed, go, notes = [], [], [], {}
    for c in p.get("candidates") or []:
        # REG-1918 - THE ONLY DELETER TAKES ONLY A REEL DIRECTORY NAME. `shutil.rmtree(os.path.join(hist, reel))` below
        # would remove the WHOLE hist root - every reel he has - for a candidate whose reel is "" (join(hist, "") IS hist),
        # and a name holding a separator or ".." walks out of it. plan() only ever lists real reel_* folders, so this has
        # never happened; a Grok look at v3596 (river slice, finding 4) found the path a malformed candidate would take
        # through _drop_reels_still_filming, and the cost of being wrong once is all of his footage.
        _rn = c.get("reel") if isinstance(c, dict) else None
        if not _is_reel_dir_name(_rn) or not _is_child_dir(p.get("hist"), _rn):
            failed.append({"reel": repr(_rn)[:80], "why": "REFUSED, nothing deleted - not a reel directory directly under "
                                                         "the shelf, so the deleter will not touch it"})
            continue
        path = os.path.join(p["hist"], c["reel"])
        if _evid is None:
            failed.append({"reel": c["reel"], "why": "HELD, nothing deleted - which pictures in it are evidence is "
                                                     "UNKNOWN: %s" % _ewhy})
            continue
        try:
            kept = sorted(f for f in os.listdir(path) if f in _evid)
        except OSError as e:
            failed.append({"reel": c["reel"], "why": "the reel could not be listed (%s)" % str(e)[:80]})
            continue
        if kept:
            c = dict(c)
            c["kept"] = kept
        notes[c["reel"]] = kept
        go.append(c)
    tomb, tomb_why = None, None
    try:
        tomb = _tombstone(p["hist"], go)
    except Exception as e:
        tomb_why = str(e)[:160]
    freed_by = {}
    for c in go:
        path = os.path.join(p["hist"], c["reel"])
        keep = set(notes.get(c["reel"]) or ())
        # the second eye on v3521: a trimmed reel freed its size MINUS the pictures it kept, never its planned size
        _kept_mb = 0.0
        for f in keep:
            try:
                _kept_mb += os.path.getsize(os.path.join(path, f)) / (1024.0 * 1024.0)
            except OSError:
                pass
        freed_by[c["reel"]] = max(0.0, float(c.get("mb") or 0) - _kept_mb)
        try:
            if keep:
                for f in os.listdir(path):
                    if f in keep:
                        continue
                    fp = os.path.join(path, f)
                    if os.path.isdir(fp):
                        shutil.rmtree(fp)
                    else:
                        os.remove(fp)
            else:
                shutil.rmtree(path)
            removed.append(c["reel"])
        except Exception as e:
            failed.append({"reel": c["reel"], "why": str(e)[:120]})
    _removed_set = set(removed)
    return {"ok": not failed, "removed": removed, "failed": failed,
            "keptPictures": dict((r, k) for r, k in notes.items() if k and r in _removed_set),
            "freedMb": round(sum(freed_by.get(r, 0.0) for r in removed), 1),
            "trimmed": sum(1 for r in removed if notes.get(r)),
            "freedMbPlanned": p.get("freeMb", 0),
            "tombstoned": (len(tomb) if tomb is not None else None),
            "tombstonePath": _tombstone_path(p.get("hist")),
            "tombstoneWhy": tomb_why}


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# THE DRAIN — does the river actually empty at its mouth, pass after pass?
# ═══════════════════════════════════════════════════════════════════════════════════════════════
#
# Konyo, 2026-09-27: *"session reels in shelf registered by FIFO first in first out and getting
# extracted and tallied and ledgered accoridngly to its won indivudal console ... and allproeprly
# getting delted after the 8 sessions"* — and #255: *"getting pruned and extracted data wise and
# eventually tombstones to get deleted.. that way storage is always smooth and optimized and not
# stacking up"*.
#
# ⚠⚠ WHAT WAS MEASURED BEFORE A LINE OF THIS WAS WRITTEN, because the brief's root cause did not
# survive the measurement. It said the pass only frees under disk pressure. Read against the code
# and against his live console (GET /api/status, 2026-09-27, 11.8 GB free): above floor+headroom
# the pass has asked for NO target since v2226, and his console reported `eligible: 0` — 19 reel
# dirs = 8 test fixtures + the newest 8 + 3 held `panels-never-banked` (sealed barren, rows 0).
# His drain was at its floor, CORRECTLY. The real defect was the BAND: at or below floor+headroom
# the pass handed plan() `free_mb=need_mb`, so the moment the disk got tight it stopped after
# `need_mb` and held every other finished reel as `target-met` — disk pressure freed LESS than no
# pressure. That band is where his disk is heading (down 0.6 GB/day).
#
# ⚠ AND NOTHING WATCHED THE MOUTH. shelf_driver declares the `deleter` lane with `boundS: None`, so a
# drain that stopped with reels owed could only ever read UNTIMED — never STALLED — and a wall-clock
# bound would cry wolf the first pass after a quiet week. The honest unit is the PASS: a working
# pass releases every reel it plans in that same pass, so a reel still owed through two whole
# passes that released nothing is a drain that has stopped, not one that is slow.
# [[heart-first]] [[the-unjoined-end]] [[feedback-contradiction-is-the-finding]]

#: How many consecutive passes may carry releasable reels forward before the drain is STOPPED.
#: The brief's own bar — "owed > 0 for longer than two passes" — so the THIRD pass that still owes
#: and released nothing fires. Derive from this in tests; never hardcode 3. [[regression-guard]] §4
DRAIN_STOPPED_AFTER_PASSES = 3

#: The drain's states. UNKNOWN is a first-class answer and never renders as CLEAR.
DRAIN_CLEAR, DRAIN_OWED, DRAIN_STOPPED, DRAIN_DORMANT, DRAIN_DEFERRED, DRAIN_UNKNOWN = (
    "CLEAR", "OWED", "STOPPED", "DORMANT", "DEFERRED", "UNKNOWN")
#: #84 (REG-1517) — and BLOCKED: reels older than the newest KEEP_RECENT are waiting UPSTREAM of the
#: mouth, at a station a lane is meant to move them out of. The deleter may owe nothing at its own
#: stage and the river still not be draining; CLEAR was saying the first and being read as the second.
DRAIN_BLOCKED = "BLOCKED"


def blocked_upstream(last, plan, upstream=None, why_of=None, keep_recent=KEEP_RECENT, now_ms=None,
                     after_s=None, river_why=None, river_unparsed=None):
    """WHAT THE DRAIN CANNOT SEE FROM ITS OWN STAGE — reels older than the newest `keep_recent` that
    are still waiting UPSTREAM of the mouth, read from the river's own positions. -> dict

    #84 (REG-1517) — MEASURED ON THE ALT, 2026-09-29: 126 reels, river EMPTY 91 / PRINTER 33 (all
    unsealed, `reel.route` CLOSED — "the heart has never run here"), and retention.drain said
    {state: CLEAR, owed: 0, why: "drained — every reel that cleared every bar ... nothing is owed"}.
    drain_owed() counts the plan's CANDIDATES, and a reel held at EMPTY or PRINTER is not one — so
    the drain counted only the reels that had reached ITS stage and called the other 110 nothing.
    Every word of CLEAR was true of the mouth and false of the river. [[heart-first]] §2: on is not
    working, and "nothing owed at my stage" is not "nothing owed".

    `last`      river_stamp.last_stamps(): reel -> its last stamp row (`station`, `at`). None = the
                store would not read = UNKNOWN, never an empty river. THE POSITION IS QUOTED FROM
                HERE AND NEVER RE-DERIVED — the router is the authority on where a reel is, the
                stamp store is its record, and a second derivation here would be [[copy-drift]].
    `plan`      THIS pass's plan(): candidates + kept are the shelf, and a `test-fixture` tag names
                a reel pinned by the suite, which waits on no lane and is never counted.
    `upstream`  the stations a LANE is meant to move a reel out of. The console passes its own
                _RIVER_OWNER keys — CAPTURE is not among them because it waits on a capture change
                by design (REG-340) and is never an alarm; those reels are counted BESIDE `n` in
                `byDesign`, never inside it. None = every station before ROUTED, no exemption.
    `why_of`    station -> the owning lane's own last word (control_app._river_stuck_why), quoted
                for the "behind <lock/reason>" half of the sentence. None = no reason available.
    `after_s`   the bar the doctor holds `oldestS` against (control_app.RIVER_STUCK_AFTER_S);
                carried as `afterS` so the row never hardcodes it. None = no bar declared.

    -> n None      the river or the shelf could not be read — UNKNOWN, never 0
       n 0         MEASURED: nothing older than the shield waits at an owned station
       complete    False when an older reel has no readable position (`unplaced`: never stamped;
                   `unknown`: stamped UNKNOWN), so `n` is a FLOOR and a 0 is not a CLEAR
       oldestS     how long the longest-waiting blocked reel has sat at its station, from the
                   river's own arrival stamp — never from when this process first noticed: his
                   console relaunches every ~30 min and a process clock would restart with it.
                   [[stale-reading]]
    """
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    keep = int(keep_recent) if isinstance(keep_recent, int) and not isinstance(keep_recent, bool) \
        and keep_recent >= 0 else KEEP_RECENT
    out = {"n": None, "stations": {}, "oldestS": None, "afterS": after_s, "byDesign": {},
           "unplaced": None, "unknown": None, "atMouth": None, "older": None, "keepRecent": keep,
           "complete": None, "reasons": {}, "why": ""}
    try:
        import reel_router as _rt
        order = list(_rt.STATIONS)
    except Exception as e:
        out["why"] = ("reel_router would not import (%s), so which stations are upstream of the "
                      "mouth is UNKNOWN" % type(e).__name__)
        return out
    if "ROUTED" not in order:
        out["why"] = "reel_router.STATIONS names no ROUTED station, so where the mouth is is UNKNOWN"
        return out
    before_mouth = order[:order.index("ROUTED")]
    owned = tuple(upstream) if upstream is not None else tuple(before_mouth)
    if last is None:
        out["why"] = ("the river could not be read%s, so whether reels wait upstream is UNKNOWN — "
                      "never 'nothing is owed'"
                      % ((" — " + str(river_why)[:160]) if river_why else ""))
        return out
    if not isinstance(plan, dict) or not plan.get("ok"):
        out["why"] = ("the shelf could not be planned this pass, so which reels are older than the "
                      "newest %d is UNKNOWN" % keep)
        return out
    cands, kept = plan.get("candidates"), plan.get("kept")
    if not isinstance(cands, list) or not isinstance(kept, list):
        out["why"] = "the plan carries no reel lists, so which reels are on the shelf is UNKNOWN"
        return out
    shelf = [str(x.get("reel")) for x in cands + kept if isinstance(x, dict) and x.get("reel")]
    pinned = set(str(x.get("reel")) for x in kept
                 if isinstance(x, dict) and x.get("reel") and x.get("tag") == "test-fixture")
    shield = recent_shield(shelf, keep)
    older = [r for r in shelf if r not in shield and r not in pinned]
    stations, by_design = {}, {}
    unplaced = unknown = at_mouth = 0
    oldest = None
    for reel in older:
        row = last.get(reel)
        if not isinstance(row, dict):
            unplaced += 1                      # the walk has never placed it: not a position
            continue
        st = str(row.get("station"))
        if st == "UNKNOWN":
            unknown += 1                       # walked and could not be placed: still not a position
        elif st in owned:
            stations[st] = stations.get(st, 0) + 1
            at = row.get("at")
            if isinstance(at, (int, float)) and not isinstance(at, bool):
                age = max(0, int((now_ms - int(at)) / 1000))
                oldest = age if oldest is None else max(oldest, age)
        elif st in before_mouth:
            by_design[st] = by_design.get(st, 0) + 1
        else:
            at_mouth += 1                      # ROUTED (the deleter's own stage) or TOMBSTONE
    ordered = dict((s, stations[s]) for s in order if s in stations)
    reasons = {}
    for s in ordered:
        if why_of is None:
            continue
        try:
            w = str(why_of(s) or "")
        except Exception as e:
            w = "the owning lane could not be asked (%s)" % type(e).__name__
        if w:
            reasons[s] = w[:200]
    n = sum(ordered.values())
    # v3526 (#231 second eye on v3525) — a torn line in the river's record may be ANY reel's newest move, so a
    # record with one is a floor for every position in it: never complete, never CLEAR, and said.
    torn = river_unparsed if (isinstance(river_unparsed, int) and not isinstance(river_unparsed, bool)
                              and river_unparsed > 0) else 0
    complete = (unplaced == 0 and unknown == 0 and not torn)
    out.update({"n": n, "stations": ordered, "oldestS": oldest,
                "byDesign": dict((s, by_design[s]) for s in order if s in by_design),
                "unplaced": unplaced, "unknown": unknown, "atMouth": at_mouth, "older": len(older),
                "complete": complete, "reasons": reasons})
    _tails = []
    if torn:
        _tails.append("%d line(s) of the river's record would not parse and any of them may be a reel's "
                      "newest move, so every position here is a FLOOR" % torn)
    if unplaced + unknown:
        _tails.append("%d older reel(s) have no readable position in the river (%d never stamped, "
                      "%d stamped UNKNOWN), so this count is a FLOOR"
                      % (unplaced + unknown, unplaced, unknown))
    if by_design:
        _tails.append("%s wait by design (not an alarm)"
                      % ", ".join("%s %d" % (s, c) for s, c in out["byDesign"].items()))
    tail = ("; " + "; ".join(_tails)) if _tails else ""
    if n > 0:
        out["why"] = ("blocked upstream: %d reel(s) older than the newest %d are waiting at %s behind %s%s"
                      % (n, keep, ", ".join("%s %d" % (s, c) for s, c in ordered.items()),
                         ("; ".join("%s: %s" % (s, w) for s, w in reasons.items()) if reasons
                          else "a reason no lane has given"),
                         tail))
    elif not complete:
        out["why"] = ("whether reels older than the newest %d wait upstream is UNKNOWN — %s — never "
                      "'nothing is owed'" % (keep, _tails[0]))
    else:
        out["why"] = ("nothing older than the newest %d waits upstream of the mouth — measured over "
                      "%d older reel(s) on the river%s" % (keep, len(older), tail))
    return out


def drain_owed(p):
    """How many reels this plan says the deleter OWES. -> int | None

    Releasable = cleared EVERY bar and is older than the newest KEEP_RECENT: the plan's own
    `candidates`, plus any it held back as `target-met` when a caller asked it to stop early —
    those finished reels are owed just the same. Nothing here is a second predicate; it counts
    two lists plan() already wrote. [[copy-drift]]

    ⚠ None — never 0 — when the plan could not judge: not ok, or ANY ledger unreadable (plan()
    then holds every reel as ledger-unreadable, so an empty candidate list is not a measurement of
    an empty drain). [[unknown-stays-unknown]]
    """
    if not isinstance(p, dict) or not p.get("ok") or p.get("unreadable"):
        return None
    cands, kept = p.get("candidates"), p.get("kept")
    if not isinstance(cands, list) or not isinstance(kept, list):
        return None
    return len(cands) + len([k for k in kept if isinstance(k, dict) and k.get("tag") == "target-met"])


def _drain_count(v):
    """A whole, non-negative count, or None. `True` is not 1 (REG-573's lesson)."""
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else None


def drain_state(rows, beat=None, on=True, stop_why=None, unknown_why=None, now_ms=None,
                every_s=None, upstream=None):
    """THE RETENTION LANE IN THE SHARED VOCABULARY — on / worked / lastTs / owed. -> dict

    Two readings, one row: `_mouth_state` is what the DELETER owes at its own stage (the per-pass
    series), and `upstream` is what the RIVER holds above it (blocked_upstream). #84 (REG-1517):
    the first alone said CLEAR over 110 reels that had never reached the mouth, so
      · upstream n > 0        -> BLOCKED (STOPPED stays STOPPED — a deleter that stalled on what
                                 DID reach it is the worse fact), owed = mouth + upstream
      · upstream n 0, complete-> the mouth's verdict stands, with the measurement beside it
      · upstream None / a floor of 0 / not asked -> CLEAR degrades to UNKNOWN, never stays CLEAR:
                                 "nothing owed at the mouth" cannot certify the river unread
    The mouth's own count is kept beside the total as `owedAtMouth`. [[unknown-stays-unknown]]
    """
    out = _mouth_state(rows, beat=beat, on=on, stop_why=stop_why, unknown_why=unknown_why,
                       now_ms=now_ms, every_s=every_s)
    out["upstream"] = upstream if isinstance(upstream, dict) else None
    out["owedAtMouth"] = out["owed"]
    mouth_state, mouth_why = out["state"], out["why"]
    up = out["upstream"]
    n = up.get("n") if up else None
    if up is None or n is None:
        unread = (str(up.get("why") or "the river's upstream reading is empty") if up else
                  "the river was not read, so whether reels wait upstream is UNKNOWN")
        if mouth_state == DRAIN_CLEAR:
            out["state"], out["owed"] = DRAIN_UNKNOWN, None
            out["why"] = "the deleter owes nothing at the mouth, but %s — never CLEAR" % unread
        else:
            out["why"] = "%s · %s" % (mouth_why, unread)
        return out
    if n > 0:
        mouth = out["owed"]
        out["owed"] = n + mouth if _drain_count(mouth) is not None else n
        if mouth_state == DRAIN_STOPPED:
            out["why"] = "%s · and %s" % (mouth_why, up.get("why"))
            return out
        out["state"] = DRAIN_BLOCKED
        mouth_say = ("the deleter itself owes nothing — every reel that reached the mouth has been "
                     "released" if mouth_state == DRAIN_CLEAR else
                     "at the mouth: %s — %s" % (mouth_state, mouth_why))
        out["why"] = "%s · %s" % (up.get("why"), mouth_say)
        return out
    if not up.get("complete"):
        if mouth_state == DRAIN_CLEAR:
            out["state"], out["owed"] = DRAIN_UNKNOWN, None
            out["why"] = "the deleter owes nothing at the mouth, but %s" % up.get("why")
        else:
            out["why"] = "%s · %s" % (mouth_why, up.get("why"))
        return out
    out["why"] = "%s · %s" % (mouth_why, up.get("why"))
    return out


def _mouth_state(rows, beat=None, on=True, stop_why=None, unknown_why=None, now_ms=None,
                 every_s=None):
    """WHAT THE DELETER OWES AT ITS OWN STAGE — the pure walk of the per-pass series. -> dict

    `rows` is the console's own per-pass series (disk_history.jsonl, oldest first): each pass writes
    one row carrying `owed` BEFORE it acts, and — only when the deleter actually ran — one row
    carrying `released` after. That series is per console (it lives in that console's own tree) and
    it SURVIVES A RELAUNCH, which is the point: his console relaunches every ~30 minutes (measured
    by relaunch_hold) and a process-local streak across 15-minute passes would almost never reach 3.

    `beat` is shelf_driver.lane_beat("deleter") — the ONE reading of what the deleter has done
    (lifetime reels in the tombstone ledger, and when it last wrote). Quoted, never recomputed.

    ⚠ ROWS WITHOUT EITHER KEY END THE WALK. They were written before this contract existed, so a
    pass there cannot be judged; the streak counts only the contiguous new-format tail.
    ⚠ `carried` is what a pass left owed: `owed - released`, or all of `owed` when the deleter never
    ran (refused, locked, switched off). An unreadable count on either side is UNKNOWN and ends
    the streak — it never extends it and never resets it to a confident zero.
    """
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    beat = beat if isinstance(beat, dict) else {}
    out = {"on": (None if on is None else bool(on)),
           "worked": _drain_count(beat.get("works")),
           "lastTs": (beat.get("lastWorkAt") if isinstance(beat.get("lastWorkAt"), int)
                      and not isinstance(beat.get("lastWorkAt"), bool) else None),
           "owed": None, "passesOwed": None, "state": DRAIN_UNKNOWN, "why": "",
           "stopWhy": (str(stop_why)[:200] if stop_why else None),
           "stoppedAfter": DRAIN_STOPPED_AFTER_PASSES, "keepRecent": KEEP_RECENT,
           "at": now_ms, "everyS": every_s,
           "workedWhy": ("" if _drain_count(beat.get("works")) is not None else
                         str(beat.get("why") or "the deleter's own record could not be read"))}
    if rows is None:
        out["why"] = ("the per-pass series could not be read, so whether the drain is moving is "
                      "UNKNOWN — not clear")
        return out
    tail = []
    for r in reversed(list(rows)):
        # `held` is a deferral mark on the pass that owed and did not run (ON AIR, a sweep
        # reading). It is part of the contract, so it must not end the walk.
        if isinstance(r, dict) and ("owed" in r or "released" in r or "held" in r):
            tail.append(r)
        else:
            break
    tail.reverse()
    passes = []
    for r in tail:
        if "owed" in r:
            passes.append({"owed": _drain_count(r.get("owed")),
                           "held": r.get("held") if isinstance(r.get("held"), str) else None})
        elif "held" in r and passes and "released" not in passes[-1]:
            passes[-1]["held"] = r.get("held") if isinstance(r.get("held"), str) else None
        elif passes and "released" not in passes[-1]:
            passes[-1]["released"] = _drain_count(r.get("released"))

    def _carried(ps):
        if ps["owed"] is None:
            return None
        if "released" not in ps:
            return ps["owed"]                  # the deleter never ran: everything it owed stays
        if ps["released"] is None:
            return None
        return max(0, ps["owed"] - ps["released"])

    def _held(ps):
        h = ps.get("held")
        return h if isinstance(h, str) and h else None

    # A deferred pass is a hold, not a stall. It ends the streak instead of extending it,
    # so ON AIR or a sweep that is reading can never add up to STOPPED.
    streak = 0
    for ps in reversed(passes):
        if _held(ps):
            break
        c = _carried(ps)
        if not c:                              # None (unknown) or 0 (drained) ends the run
            break
        streak += 1
    owed_now = _carried(passes[-1]) if passes else None
    out["owed"], out["passesOwed"] = owed_now, (streak if passes else None)
    if unknown_why:
        out["owed"], out["passesOwed"] = None, None
        out["why"] = "the retention plan could not run this pass — %s" % str(unknown_why)[:200]
        return out
    if not passes:
        out["why"] = ("no retention pass on this console has recorded what it owes yet, so whether "
                      "the drain is moving is UNKNOWN")
        return out
    if owed_now is None:
        out["why"] = ("the last pass could not judge which reels are releasable (the plan or a "
                      "ledger could not be read), so what the drain owes is UNKNOWN — never 0")
        return out
    if owed_now == 0:
        out["state"] = DRAIN_CLEAR
        out["why"] = ("drained — every reel that cleared every bar and is older than the newest %d "
                      "has been released; nothing is owed" % KEEP_RECENT)
        return out
    if on is not None and not on:           # the second eye on v3520: 0 is disarmed too, not only False
        out["state"] = DRAIN_DORMANT
        out["why"] = ("%d releasable reel(s) wait and the deleter is disarmed BY DESIGN — a "
                      "decision, not a stall" % owed_now)
        return out
    _defer = _held(passes[-1]) if passes else None
    if on is None and not _defer:
        # the second eye on v3520: whether the deleter is ARMED could not be read - a remainder then is UNKNOWN, never
        # "the drain has stopped" (a disarmed drain and an unread one are not a stall) [[unknown-stays-unknown]]
        out["why"] = ("%d releasable reel(s) wait and whether the deleter is armed could not be read, so this is "
                      "UNKNOWN - never called a stall" % owed_now)
        return out
    if _defer:
        out["state"] = DRAIN_DEFERRED
        out["why"] = ("%d releasable reel(s) wait and this pass was DEFERRED — %s — "
                      "a hold while the console is filming or a sweep is reading, not a stall"
                      % (owed_now, _defer[:160]))
        return out
    if streak >= DRAIN_STOPPED_AFTER_PASSES:
        out["state"] = DRAIN_STOPPED
        out["why"] = ("the drain has STOPPED — %d releasable reel(s) have been carried through %d "
                      "consecutive retention passes and none of those passes released them%s"
                      % (owed_now, streak,
                         (" — the last refusal: %s" % str(stop_why)[:160]) if stop_why else
                         " — the passes gave no reason"))
        return out
    out["state"] = DRAIN_OWED
    out["why"] = ("%d releasable reel(s) owed, carried through %d pass(es); the drain is called "
                  "stopped at %d%s" % (owed_now, streak, DRAIN_STOPPED_AFTER_PASSES,
                                       (" — this pass: %s" % str(stop_why)[:160]) if stop_why else ""))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Which reels have given up their information.")
    ap.add_argument("--hist", default=None)
    ap.add_argument("--free-mb", type=float, default=None, help="stop once this much is selected")
    ap.add_argument("--keep-recent", type=int, default=KEEP_RECENT)
    ap.add_argument("--apply", action="store_true", help="actually delete (needs --yes)")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)

    p = plan(a.hist, a.free_mb, a.keep_recent)
    if not p["ok"]:
        print("refusing: %s" % p["why"])
        return 1
    print("%d reel(s) on disk in %s%s" % (p["onDisk"], p["hist"],
          (" (+ %d released reel(s) holding only their evidence pictures)" % len(p.get("remnants") or []))
          if p.get("remnants") else ""))
    print(p["say"])
    if p["candidates"]:
        print("\nMAY GO (oldest first):")
        for c in p["candidates"]:
            print("   %-40s %6.1f MB  %s" % (c["reel"], c["mb"], c["why"]))
    print("\nKEPT, and why:")
    for k in p["kept"]:
        print("   %-40s %6.1f MB  %s" % (k["reel"], k["mb"], k["why"]))
    # v2068 — print the coverage LAST, where a verdict is read. A rule that never ran is the one
    # thing this plan cannot otherwise tell him, and it is exactly the thing that looks fine.
    print("\nRULE COVERAGE:")
    for _r, _n in p["coverage"].items():
        _tag = ("" if _n else ("   <- NEVER REACHED on this footage"
                               if _r in p["neverFired"] else "   (n/a without --free-mb)"))
        print("   %-24s %3d%s" % (_r, _n, _tag))
    print("   %s" % p["coverageSay"])
    if a.apply:
        r = apply_plan(p, a.yes)
        print("\n%s" % ("removed %d reel(s) (%d of them kept only their evidence pictures), freed %d MB"
                        % (len(r["removed"]), r.get("trimmed") or 0, round(r["freedMb"]))
                        if r["ok"] else r.get("why") or "some deletions failed"))
        for f in r.get("failed") or []:
            print("   FAILED %s — %s" % (f["reel"], f["why"]))
        return 0 if r["ok"] else 1
    return 0


if __name__ == "__main__":
    import console_safe  # noqa: F401 — emoji must survive a non-UTF-8 console
    sys.exit(main())
