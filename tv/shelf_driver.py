#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🎞🚚 THE SHELF DRIVER — it RUNS what retention decides, and decides nothing itself.

Konyo, 2026-09-10, choosing this over a manager AI for THE SHELF: *"1. A driver — something that
executes what reel_retention.plan() already decides. No opinions, no second predicate... 2. Heart
2.0 supervision over the driver — so a lane that stops reading goes RED on its own"*.

⚠⚠ WHY THERE IS NO SECOND PREDICATE HERE, AND WHY THAT IS THE WHOLE DESIGN.
Every serious defect found on 2026-09-10 was TWO AUTHORITIES ANSWERING ONE QUESTION:

    _chron_owed_count()   41   vs   vaultAutoread.owed        0
    _vault_lane_owes      40   vs   _vault_owed_reels         0
    plan()                 2   vs   the watchdog's predicate 19   (2026-08-28: 17 needless paid sweeps)
    `--prove` "fix the skip"   vs   propose() "the law is weak"

`control_app._vault_owed_reels` already carries the ruling in its own docstring: *"ONE DEFINITION.
The reason string is retention's, so a reel leaves this list the moment retention stops calling it
vault-blocked, and the panel and the sweeper cannot drift apart."* A manager with judgement would be
a THIRD opinion about "is this reel done" — the exact failure mode, added on purpose.

So this module asks `reel_retention.plan()` for why a reel is still on disk, and `vault_owes_read`
for whether the vault lane owes that reel a read. It invents neither answer. It carries retention's
own `tag` and `why` through untouched. If it ever starts deciding, it has become the defect it was
built to avoid.
[[the-unjoined-end]] [[copy-drift]] [[feedback-contradiction-is-the-finding]]

⚠ IT NEVER DELETES. `_PRUNE_SAFE_TO_RUN` is Konyo's to arm, not this module's. `work()` reports;
`stages()` draws; neither removes a frame.
"""
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

def _beat_path():
    """Where the driver's own heartbeat lives, resolved at CALL time. -> str|None

    ⚠⚠ IT WAS A MODULE CONSTANT, WHICH MEANT A GATE WROTE INTO HIS LIVE tv/. `BEAT` was
    `os.path.join(HERE, ...)` computed at import, so `TV_HIST` — the one thing a caller sets to say
    "this is not his world" — could never reach it, and `beat()` writes on every call. control_app
    has already paid for this exact shape (`_shadow_watch_path`, v2423: *"an env honoured only at
    import is a redirect that silently does not take"*). [[feedback-fixtures-never-touch-live-data]]

    ⛔ AND A REQUEST FOR ISOLATION THAT CANNOT BE HONOURED REFUSES RATHER THAN DEGRADING. It asks
    `tv_diablo._fixture_root` — the ONE definition of the rule — and never restates it. If that
    resolver is unreachable while TV_HIST is set this returns None and `beat()` records that it
    could not persist, because the alternative is a FOURTH copy of a rule whose existing copies are
    already a live disagreement (REG-875). [[copy-drift]] [[unknown-stays-unknown]]
    """
    try:
        import tv_diablo as _tvd
        return os.path.join(_tvd._fixture_root(HERE), ".shelf_driver.json")
    except Exception:
        if os.environ.get("TV_HIST"):
            return None
        return os.path.join(HERE, ".shelf_driver.json")


#: Back-compat for readers of the module attribute. The CALLABLE above is the source of truth;
#: this is the same answer on his console, where TV_HIST is unset.
BEAT = os.path.join(HERE, ".shelf_driver.json")

#: Which retention tag means "a lane still owes this reel work", and which lane owes it.
#: ⚠ KEYED ON THE TAG, NOT THE SENTENCE — v2392's lesson: a `why` string is prose and improving
#: the wording must not silently change what runs. Tags come from reel_retention.RULES.
OWED_BY = {
    "never-chronicle-swept": "chronicle",
    "zero-pages":            "chronicle",
    "panels-never-banked":   "vault",
    "rows-not-banked":       "vault",
    "vault-owes":            "vault",
}

#: ⚠⚠ v2878 — OF THOSE, THE ONES A PAID RE-READ CAN ACTUALLY CLEAR.
#: A cross-family review of v2876: `OWED_BY` maps three tags to the vault lane, and v2876 queued
#: all three for a re-read. `rows-not-banked` is not a read — the sweep ALREADY ran and produced
#: rows; what is missing is a durable BANK. Queuing it spends up to _VAULT_AUTOREAD_MAX_TRIES paid
#: reads, the hold does not clear, and the reel is retired as "still owed" without ever banking.
#: Latent on his tree today (0 such reels) and the same over-queue shape as the 2026-08-28 incident,
#: aimed at the wrong verb.
#:
#: So the two questions are kept apart, because they are different questions:
#:     OWED_BY      -> WHICH LANE owns this reel   (what the panel reports as waiting)
#:     READ_CLEARS  -> can a READ clear it         (what the sweeper is allowed to pay for)
#: [[label-outlived-referent]] [[feedback-contradiction-is-the-finding]]
READ_CLEARS = ("never-chronicle-swept", "zero-pages", "panels-never-banked", "vault-owes")

#: ⚠⚠ v3344 — WHAT EACH OWED TAG MEANS, IN HIS WORDS. The shelf said "N waiting on a lane (vault: N)"
#: for every owed reel, and "waiting on a lane" is the READ_CLEARS question asked of the OWED_BY map,
#: which cannot answer it. OWED_BY says WHICH LANE OWNS a reel; it does not say a lane pass will ever
#: clear it. `rows-not-banked` is the proof: v2878 ruled it owed a BANK, not a READ, so it is
#: deliberately absent from READ_CLEARS above and no sweep will ever clear it — yet the screen filed
#: it under "waiting on a lane" with the other four.
#:
#: ⚠ KEYED ON THE TAG, NOT THE SENTENCE — v2392's lesson, the same reason OWED_BY is. Improving the
#: wording must never change what runs.
#: ⚠ THREE PROSE SITES ALREADY SAID THIS AND ONLY THE SCREEN DID NOT: control_app.reel_census's own
#: docstring ("panels-never-banked 3 — the VAULT still owes a bank"), the law that pins the sentence
#: (test_the_shelf_tabs_are_the_real_sessions: "3 the vault still owes a BANK"), and the v2878 note
#: above. Every author who described this population got it right in prose.
OWED_SAYS = {
    "never-chronicle-swept": "never chronicle-swept",
    "zero-pages":            "no pages to read",
    "panels-never-banked":   "panels on film, nothing banked",
    "rows-not-banked":       "owed a bank, not a read",
    "vault-owes":            "the vault has never swept it",
}

#: Tags that mean the reel is finished and held for a reason no lane can clear.
HELD = ("recent", "test-fixture", "holds-proof", "target-met",
        "no-witness-index", "ledger-unreadable")


#: ⚠⚠ 2026-09-29 (#50, REG-1446) — THE TAGS THAT VETO A VAULT READ EVEN AT PRINTER. A fixture belongs
#: to his suite; an unreadable ledger or witness index is UNKNOWN, and UNKNOWN never spends; and
#: `rows-not-banked` owes a BANK, not a read (v2878). Everything else - `recent`, `zero-pages`,
#: `holds-proof` - says why the reel is still ON DISK, which is not a reason to leave it unread.
VAULT_READ_VETO = ("test-fixture", "no-witness-index", "ledger-unreadable", "rows-not-banked")


def _no_witness_store_was_ever_written(root=None):
    """Were the durable witness stores MEASURED absent (not unreadable, not unknown)? -> bool. Never raises.

    True only when frame_authority answered with a complete picture (`ok`) of no store at all (`haveIndex` False).
    A store that will not parse, or a check that could not run, is UNKNOWN - and UNKNOWN never spends."""
    try:
        import frame_authority as _fa
        wi = _fa.witness_index(root) or {}
    except Exception:
        return False
    return wi.get("ok") is True and wi.get("haveIndex") is False


def _proven_empty(reel):
    """REG-1749 — did a FULL triage pass find no panel of any kind on this reel? -> bool. Never raises.

    Retention's own reading (reel_retention._proven_empty), called rather than re-derived; anything it cannot prove is
    False, which leaves the read owed."""
    try:
        import os as _os
        import reel_retention as _rr
        return bool(_rr._proven_empty(_os.path.basename(str(reel))))
    except Exception:
        return False


def vault_owes_read(tag, station, reel=None):
    """Does the vault lane owe this reel a paid READ? -> bool. THE ONE DEFINITION.

    ⚠⚠ 2026-09-29 (#50, REG-1446) — TWO INDEPENDENT FACTS, AND ONLY ONE WAS EVER ASKED. Retention's
    tag answers "why is this reel still on disk", first-match-wins, so a reel the river puts at
    PRINTER (names read, the session carries no seal) and that retention files as `recent` or
    `zero-pages` never carried a vault tag: the lane published owed:0, and the reel waited for a
    seal nothing would write. river_walk's PRINTER probe had been printing that very sentence.
    MEASURED: the ALT held 25 reels at PRINTER since 09-27, every one `zero-pages`; his Mac held 4,
    every one `recent` (265, 23, 26 and 14 names read).

    `station` is the ROUTER's position (reel_router._station_of, from evidence: names, sealed) - a
    source independent of retention, which is why it can see what retention's ordering hides.
    None means the position is unknown, and then only the tag decides - never a guess of PRINTER.
    [[the-unjoined-end]] [[copy-drift]] [[feedback-contradiction-is-the-finding]]
    """
    # ⚠⚠ REG-1743 (2026-10-02, the ALT) - A STORE NOBODY EVER WROTE IS NOT AN UNREADABLE ONE. Retention tags EVERY reel
    # `no-witness-index` while no durable witness store exists; the vault lane vetoed that tag; and only a vault read
    # ever writes those stores. MEASURED on the ALT: 62 reels at PRINTER, every one `no-witness-index`, owes False,
    # vault_accum.json and vault_seen.json both ABSENT - the lane read 0 reels, ever, and never could. The veto's own
    # reason ("UNKNOWN never spends") is about a store that will not READ; a store measured ABSENT is "nothing read
    # yet", which is the one state a read is owed. So at PRINTER it owes - only when the stores are measured absent.
    #
    # ⚠⚠ REG-1749 (2026-10-03, the ALT) - AND THE FILTER HAD ALREADY RULED ON SOME OF THEM. REG-1743 opened the vault to
    # every PRINTER reel and asked nothing of the triage: MEASURED, it paid to read reel_s_1790528959887_11808, which
    # retro_triage had walked in full (1,212 frames) and found NO panel in; the pass found no stash, could not prove its
    # gate live on footage with nothing to see, called the answer UNKNOWN and requeued it. A reel the triage proved
    # empty has no stash for this lane to read. `reel` asks retention's own reading (reel_retention._proven_empty, the
    # same call the chronicle rule makes since REG-1747), so the lanes cannot disagree about one reel; no reel given, or
    # nothing proven (no store, a sampled pass, an absent reel), and the rest of this rule decides as before.
    if reel and _proven_empty(reel):
        return False
    if tag == "no-witness-index" and station == "PRINTER":
        return _no_witness_store_was_ever_written()
    if tag in VAULT_READ_VETO:
        return False
    if tag in lane_read_tags("vault"):
        return True
    if station != "PRINTER":
        return False
    # ⚠ second eye on this change (Grok, 2026-09-29): a tag retention never emits - None, "", a renamed
    # rule - would have been bought at PRINTER, because the veto is a deny-list. The PRINTER path takes
    # only tags retention actually emits; anything else is UNKNOWN, and UNKNOWN never spends.
    try:
        import reel_retention as _rr
        return tag in _rr.RULES
    except Exception:
        return False


def lane_read_tags(lane):
    """The tags `lane` owns THAT A PAID READ CAN CLEAR — the one definition of a lane's work list.

    v3295 — THIS EXISTS BECAUSE THE SAME EXPRESSION WAS WRITTEN TWICE AND THE COPIES DRIFTED.
    `control_app._vault_autoread_candidates` computed `OWED_BY ∩ READ_CLEARS` (v2878) while
    `river_walk`'s PRINTER probe still counted the single tag `vault-owes`. The lane held 3
    `panels-never-banked` reels and the river printed "the lane's queue is EMPTY ... this reel
    waits for a seal nothing will write" — an instrument and the thing it measures disagreeing
    about what the lane is for, which is the whole failure this module's docstring is against.

    Returning a frozenset rather than a tuple is deliberate: callers test membership, and a
    caller that wants an ordered label should sort it at the point of display.

    ⚠ An unreadable map is UNKNOWN, never an empty set. This cannot raise on a well-formed
    module, so a caller that gets back an empty set is being told THIS LANE OWNS NOTHING A READ
    CAN FIX — a real answer — and must not render it as "idle". [[copy-drift]] [[the-unjoined-end]]
    """
    return frozenset(t for t, owner in OWED_BY.items()
                     if owner == lane and t in READ_CLEARS)


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# THE LANE CENSUS — Heart 2.0's discipline, aimed at LANES instead of GATES
# ═══════════════════════════════════════════════════════════════════════════════════════════════
#
# ⚠⚠ WHAT WAS MISSING, IN ONE SENTENCE FROM THIS FILE'S OWN DOCSTRING: *"a lane with work owed and
# a heartbeat that has stopped is the state `vaultAutoread` sat in for weeks with `reads: 0,
# lastTs: null` and nothing said so."* Heart 2.0 asks whether the GATES can still go red.
# `lane_liveness` asks whether a THREAD is still ticking. Nothing joined "there is work owed" to
# "this lane has done a unit of work", and those are the two halves of the only question that
# matters here. [[the-unjoined-end]] [[heart-first]]
#
# ⛔ AND THERE IS STILL NO SECOND PREDICATE. The census asks THREE different questions of THREE
# owners and joins them; it re-derives none of them:
#
#     is there work owed          `work()` -> reel_retention.plan()      (this module's one answer)
#     has this lane worked        the LANE'S OWN durable store           (asked of its owner)
#     is this lane allowed to act the flag its owner already keeps       (asked of its owner)
#
# If a "does this lane owe anything" function ever appears below, it is the defect this whole file
# is named after. [[feedback-contradiction-is-the-finding]]
#
# ⚠ AND IT READS THE **STORE**, NOT PROCESS MEMORY. That is #60's whole lesson one level up: a
# process-local counter reports a RESTART as "this lane has never swept", which is a completely
# different accusation from the truth. Every reading below comes off disk, so a restart cannot
# manufacture a dark lane — and where a lane keeps nothing on disk, that is reported as a
# durability failure rather than papered over. [[unknown-stays-unknown]]

#: Work owed, and this lane completed a unit inside its own declared bound.
FLOWING = "FLOWING"
#: Work owed, this lane HAS completed units, and staleness is not decidable — no WORK period is
#: declared for it, or nothing durable records WHEN the last unit happened. Not a clean bill.
UNTIMED = "UNTIMED"
#: Work owed, this lane has worked, and its last unit is older than its own declared bound.
STALLED = "STALLED"
#: ⚠ THE ONE THIS FILE EXISTS FOR. Work owed, and this lane has NEVER completed a unit of work.
#: NO THRESHOLD IS INVOLVED — which is why it is the red that can actually be trusted. A bound is a
#: number somebody guessed; "owed > 0 and works == 0" is two measurements and a conjunction. The
#: vault lane sat in exactly this state for weeks. [[feedback-threshold-above-the-ceiling]]
DARK = "DARK"
#: Nothing owed, measured, WITH the denominator printed beside it. A 0 with no denominator is not
#: IDLE, it is UNKNOWN. [[zero-needs-a-denominator]]
IDLE = "IDLE"
#: Not acting, and the reason is KNOWN and by design — copied from `lane_liveness.DORMANT`, for its
#: reason: collapsing a known reason into UNKNOWN sends a reader hunting a fault that is not there,
#: and hides the case that IS one.
DORMANT = "DORMANT"
#: Could not ask. NEVER renders as IDLE and never as "nothing owed".
UNKNOWN = "UNKNOWN"

#: How many of its own declared bounds a lane may miss before it is STALLED. Same number and same
#: reasoning as `lane_liveness.STALE_SLACK`: 1.0 would fire on ordinary jitter, and a gate that
#: cries wolf is one he learns to skip.
BOUND_SLACK = 3.0

#: ⚠⚠ EVERY LANE DECLARED, INCLUDING THE ONES WITH NOTHING TO DO TODAY — that is the whole
#: discipline borrowed from the gate census. `beat()` used to write `owedByLane`, which is built by
#: counting owed reels, so a lane owing zero was simply ABSENT from the record. MEASURED on his
#: tree 2026-09-10: `owedByLane` read `{"vault": 18}` and the chronicle lane — which exists, has a
#: store, and has a watchdog — appeared nowhere at all. Absent and healthy looked identical, which
#: is the exact failure `lane_census.py` was written about one level down. [[unknown-stays-unknown]]
#:
#: Each entry says where the lane's OWN record lives and which key in it means what. It never says
#: whether that record is durable — that is MEASURED from the store's own keys, because a hand-kept
#: durability flag is the rot `lane_census.supervisor_set_is_current` already had to make
#: falsifiable. [[label-outlived-referent]]
LANES = {
    "chronicle": {
        "what": "reads a reel's chronicle pages so its names can be banked",
        "owedFrom": "tags",
        "owner": "control_app",
        # ⚠ resolved at control_app's IMPORT time, not at call time. A census run after TV_HIST
        # changes reads whichever world that module was imported into. Named here rather than
        # worked around, because the fix belongs in control_app and this file does not own it.
        "store": "_CHRON_AUTOREAD_PATH",
        # ⚠⚠ `done` IS THE DURABLE UNIT COUNT, AND `reads` IS NOT. `_CHRON_AUTOREAD["reads"]` is a
        # process counter that no writer persists — `_chron_autoread_save`'s payload is exactly
        # {done, reels, retired, skipped}, measured on his store. Reading `reads` here would make
        # every restart report a lane that has never worked, which is #60 verbatim.
        "worksKey": "done",
        "worksAs": "len",
        # ⚠⚠ AND ITS `lastTs` IS NOT A CLOCK READING. `_CHRON_AUTOREAD["lastTs"] = ts` stores the
        # VISIT's timestamp; the vault's sibling field stores `int(time.time()*1000)`. Same field
        # name, two different quantities, in two sibling lanes — so "when did this lane last work"
        # is genuinely UNKNOWN for the chronicle lane and is reported as UNKNOWN, never guessed
        # from the newest visit it has read. [[label-outlived-referent]]
        "lastKey": None,
        "lastWhy": ("nothing durable records WHEN this lane last worked: its store carries "
                    "{done, reels, retired, skipped} and no clock reading, and the in-memory "
                    "`lastTs` holds a VISIT id rather than a time"),
        "boundS": None,
        "armedFrom": None,
    },
    "vault": {
        "what": "sweeps a reel so its panels reach the vault ledger",
        "owedFrom": "tags",
        "owner": "control_app",
        "store": "_vault_autoread_path",
        "worksKey": "reads",
        "worksAs": "int",
        "lastKey": "lastTs",
        "lastWhy": "",
        "boundS": None,
        "armedFrom": None,
    },
    "deleter": {
        # The outlet. Its work-list is the plan's OWN `candidates` — the same call, the same
        # answer, read off a different field. Not a second predicate.
        "what": "tombstones a reel every lane has finished with, then reclaims its frames",
        "owedFrom": "releasable",
        "owner": "reel_retention",
        "store": "_tombstone_path",
        "worksKey": "reels",
        "worksAs": "len",
        "lastKey": "updatedTs",
        "lastWhy": "",
        "boundS": None,
        # ⚠ ASKED, NOT DECIDED. `_PRUNE_SAFE_TO_RUN` is Konyo's to arm and this module must never
        # form an opinion about it. Without this read, a disarmed prune with releasable reels
        # waiting would be reported DARK — an alarm about a deliberate decision, which is how a
        # supervision layer teaches him to ignore it.
        # REG-1879 — and his TV_AUTO_PRUNE switch is the other half of arming. The constant alone is True on every
        # machine, so this lane could never be DORMANT. deleter_armed() is the one answer the drain gives too.
        "armedFrom": ("control_app", "deleter_armed"),
        "dormantWhy": ("the prune is armed by Konyo and is not armed. Reels may sit releasable "
                       "indefinitely and that is a decision, not a stall"),
    },
    # ⚠⚠ v3018 — THE FOURTH LANE, AND THE ONE THAT COULD NOT BE CAUGHT IDLE. tvd-retro-triage had
    # a heartbeat and no work-level supervision: the thread being alive was the only thing anyone
    # could see, so "running and doing nothing" was invisible — the exact shape vaultAutoread died
    # in, beating happily for 5.7 days without sweeping a reel. It could not be declared before now
    # because every other lane takes its work-list from RETENTION TAGS, and retro_triage walks
    # frames structurally BEFORE any tag exists, so there was no tag to map. It answers for itself
    # instead (`owedFrom: "own"` -> retro_triage.owed()), and its store is one row per reel with no
    # tally and no top-level clock, which is what `worksAs: "storeLen"` and `lastAs: "maxRowTs"`
    # are for. Live at declaration: owed 0 of 24 on disk, 455 rows remembered.
    "triage": {
        "what": "walks a reel's frames structurally so the other lanes know what is worth reading",
        "owedFrom": "own",
        "owner": "retro_triage",
        "store": "_store_path",
        "worksKey": None,
        "worksAs": "storeLen",
        "lastKey": None,
        "lastAs": "maxRowTs",
        "lastWhy": "",
        "boundS": None,
        "armedFrom": None,
    },

}


#: ⚠⚠ THE SCOPE, SAID OUT LOUD, BECAUSE A PARTIAL CENSUS THAT DOES NOT SAY SO IS A FULL ONE THAT
#: LIES. His console starts 12 background loops. THREE of them own a work-list on the shelf and are
#: declared above. The other NINE are named here with the reason they are not, so "absent from this
#: table" can never be mistaken for "forgotten" — which is the whole complaint this census answers
#: one level up. Whether those nine are ALIVE is a different question with a different owner:
#: `lane_liveness` asks it, and its answer is thread-local by design.
#:
#:     tvd-retro-triage    acts on reels, and its work-list is NOT in the retention plan. Declaring
#:                         it would mean writing a second "which reels need triage" predicate — the
#:                         exact defect this module is named after. It needs an owed-count from its
#:                         OWN authority before it can be supervised here.
#:     tvd-shadow-watch    watches for the game, not for reels
#:     tvd-stash-watch     seals a reel a lane already declared; no work-list of its own
#:     tvd-rolling-prune   prunes duplicate LIVE frames mid-recording, not shelved reels
#:     tvd-ledger-backup   copies a ledger out; nothing on the shelf waits on it
#:     tvd-space-warden    reclaims regenerable test output, never footage
#:     tvd-version-drift   announces a stale process
#:     tvd-eagle-watch     a supervisor, not a worker
#:     tvd-runaway-watch   a supervisor, not a worker
#:     tvd-tooltip-oracle  #41 rank 16 - runs the shipped tooltip code over a FIXED oracle (203 rows) and writes
#:                         only its own receipt; no reel, no frame, no ledger is on its work-list
#:     tvd-orphan-fold     REG-2463 - folds LOOSE frames (no reel yet) into new reels; its work-list is
#:                         orphan_fold.plan's clusters, and no shelved reel waits on it
#:     tvd-price-refresh   #96 - re-asks d2jsp for one due price-database item; it touches no reel and no frame
#:     tvd-river-warm      #193 - READS the river (the read-only route) so the Fleet has one; it moves no reel
#:     tvd-disk-sign       #151 - MEASURES what holds the disk for the sign under the ONLINE light; it moves nothing
#: [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
# ⚠⚠ v3018 — "tvd-retro-triage" REMOVED FROM THIS LIST, because it is now a declared shelf lane.
# It sat here because every lane the driver supervised took its work-list from retention TAGS, and
# retro_triage walks frames structurally BEFORE any tag exists — so there was nothing to map it to,
# and being unmappable got written down as being out of scope. It has run with liveness-only
# supervision ever since. `owedFrom: "own"` gives it a real work-list, so the exclusion is no longer
# true. Declared AND excused is the one state this census must never be in.
NOT_SHELF_LANES = ("tvd-shadow-watch", "tvd-stash-watch", "tvd-rolling-prune",
                   "tvd-ledger-backup", "tvd-space-warden", "tvd-version-drift",
                   "tvd-eagle-watch", "tvd-runaway-watch", "tvd-tooltip-oracle", "tvd-orphan-fold",
                   "tvd-price-refresh", "tvd-river-warm", "tvd-disk-sign")


def declared_covers_the_map(owed_by=None, lanes=None):
    """Does every lane the TAG MAP names also have a declaration here? -> (ok, why)

    ⚠⚠ A HAND-KEPT SET ROTS, AND THIS FILE ALREADY KNOWS IT. `lane_census.supervisor_set_is_current`
    exists for the same reason and says it best: a declaration that silently stops matching makes
    the warning disappear and the table render as if nothing were wrong. `LANES` is hand-kept; add a
    tag to `OWED_BY` pointing at a lane nobody declared and that lane's reels would be counted into
    a total and shown on no row.

    This does not make `LANES` self-deriving — a lane's store, its unit key and its arming flag
    cannot be inferred from a tag. It makes it FALSIFIABLE, which is the achievable half.
    """
    owed_by = OWED_BY if owed_by is None else owed_by
    lanes = LANES if lanes is None else lanes
    gone = sorted(set(owed_by.values()) - set(lanes))
    if gone:
        return False, ("%d lane(s) are named by the tag map and DECLARED NOWHERE: %s. Their reels "
                       "are counted as owed and appear on no row, so the shelf reports work that "
                       "belongs to nobody." % (len(gone), ", ".join(gone)))
    return True, "every lane the tag map names is declared"


def _owner_module(name, allow_import=False):
    """The module that OWNS a lane's record. -> (module|None, why)

    ⚠ IT DOES NOT IMPORT BY DEFAULT, AND THAT IS DELIBERATE. `control_app` is a 27,000-line module;
    importing it to answer an HTTP request would be the wrong shape, and importing it inside a gate
    drags a fixture's whole world in behind it. When it is already loaded — which is every case that
    matters, because the console IS control_app — its record is right there. When it is not, the
    answer is UNKNOWN with a reason, never a confident zero.
    """
    m = sys.modules.get(name)
    if m is not None:
        return m, ""
    if not allow_import:
        return None, ("%s is not loaded in this process, so this lane's own record cannot be "
                      "asked. That is UNKNOWN — not an idle lane" % name)
    try:
        return __import__(name), ""
    except Exception as e:
        return None, "%s could not be imported (%s)" % (name, type(e).__name__)


def _store_path(decl, allow_import=False):
    """Where a lane's durable record lives, asked of its OWNER. -> (path|None, why)

    ⚠ ONE DEFINITION OF THE PATH. Every one of these files already has an owner that computes its
    location, honours TV_HIST and has been fixed there more than once. Recomputing any of them here
    would be a second definition of a filename, which is this repo's most expensive habit — the
    `.heart2.json` literal that `_heart2_census` had to be taught to stop inventing is the same
    shape. [[copy-drift]]
    """
    mod, why = _owner_module(decl.get("owner"), allow_import=allow_import)
    if mod is None:
        return None, why
    attr = getattr(mod, decl.get("store") or "", None)
    if attr is None:
        return None, ("%s.%s is gone — the lane's store has been renamed or removed, so where its "
                      "record lives is UNKNOWN" % (decl.get("owner"), decl.get("store")))
    try:
        return (attr() if callable(attr) else str(attr)), ""
    except Exception as e:
        return None, ("%s.%s raised (%s), so where its record lives is UNKNOWN"
                      % (decl.get("owner"), decl.get("store"), type(e).__name__))


def _read_store(path):
    """-> (doc, readable). readable is True | False (no store yet) | None (UNKNOWN).

    The three outcomes are the vault store's own, and they are kept apart for its reason: an
    UNREADABLE store read as a fresh start turns "nobody could measure this" into "this lane has
    done nothing", and those are opposite facts. [[unknown-stays-unknown]]
    """
    if not path:
        return None, None
    if not os.path.isfile(path):
        return None, False
    try:
        with io.open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        return (d if isinstance(d, dict) else None), (True if isinstance(d, dict) else None)
    except Exception:
        return None, None


def lane_beat(lane, decl=None, allow_import=False):
    """What a lane's OWN durable record says it has done. -> dict

    Never a judgement, never a second opinion about work owed — only: how many units this lane has
    completed, when the last one was, and whether either of those survives a restart.
    """
    decl = LANES[lane] if decl is None else decl
    # ⚠⚠ DURABILITY HAS TWO HALVES AND THEY COME APART. A first cut reported one `durable` bool
    # measured from the unit-count key alone, and the chronicle lane — which persists `done` and NO
    # clock reading anywhere — came back `durable: True`. That is a right measurement under a word
    # that had stopped being true of the whole heartbeat: the count survives a restart and "when did
    # this lane last work" does not. So both halves are measured and `durable` means BOTH.
    # [[label-outlived-referent]] [[zero-needs-a-denominator]]
    out = {"lane": lane, "resolved": False, "store": None, "storeReadable": None,
           "works": None, "lastWorkAt": None,
           "durable": None, "durableWorks": None, "durableLast": None, "durableWhy": "", "why": ""}
    path, why = _store_path(decl, allow_import=allow_import)
    out["store"] = path
    if path is None:
        out["why"] = why
        return out
    doc, readable = _read_store(path)
    out["resolved"] = True
    out["storeReadable"] = readable
    if readable is None:
        out["why"] = ("this lane's store exists and could NOT be read, so how much it has done is "
                      "UNKNOWN. An empty count here would be a claim nobody measured")
        return out
    if readable is False:
        # A genuine fresh start IS a fact, and it is the fact that makes DARK reachable.
        out.update({"works": 0, "lastWorkAt": None, "durable": False,
                    "durableWorks": False, "durableLast": False,
                    "durableWhy": "there is no store on disk at all, so nothing this lane learns "
                                  "would survive a restart",
                    "why": "no store yet — this lane has genuinely never recorded a unit of work"})
        return out
    wkey = decl.get("worksKey")
    lkey = decl.get("lastKey")
    raw = (doc or {}).get(wkey)
    # ⚠ DURABILITY IS MEASURED FROM THE STORE'S OWN KEYS, not declared. Measured on his tree:
    # `.vault_autoread.json` carries reads AND lastTs; `chron_autoread.json` carries {done, reels,
    # retired, skipped} and no clock reading of any kind.
    out["durableWorks"] = wkey in (doc or {})
    out["durableLast"] = bool(lkey) and lkey in (doc or {})
    out["durable"] = bool(out["durableWorks"] and out["durableLast"])
    out["durableWhy"] = ("both halves survive a restart" if out["durable"] else
                         ("the unit COUNT survives a restart and no clock reading does, so after a "
                          "restart 'when did this lane last work' is UNKNOWN"
                          if out["durableWorks"] else
                          ("only the clock reading survives a restart; the unit count does not"
                           if out["durableLast"] else
                           "neither the unit count nor a clock reading survives a restart")))
    # ⚠⚠ v3018 — A STORE CAN BE ITS OWN RECORD. Every lane declared before this one keeps a COUNT
    # under a key; retro_triage keeps one ROW PER REEL and no tally anywhere, so `worksKey` had
    # nothing to point at and the reader would have called a fully-working lane UNKNOWN forever.
    # `worksAs: "storeLen"` says the document itself is the count — and durability is TRUE by
    # construction there, because the rows ARE the persistence rather than a number beside them.
    if decl.get("worksAs") == "storeLen":
        out["durableWorks"] = True
        out["works"] = len(doc or {})
        # ⚠ AND THE CLOCK COMES FROM THE ROWS. Same reason: there is no top-level stamp, but every
        # row carries its own `ts`, so "when did this lane last work" is the newest of them. A lane
        # whose rows carry no ts at all leaves this None — UNKNOWN, never 0. [[stale-reading]]
        if decl.get("lastAs") == "maxRowTs":
            _ts = []
            for _r in (doc or {}).values():
                if isinstance(_r, dict):
                    try:
                        _v = int(_r.get("ts") or 0)
                    except Exception:
                        _v = 0
                    if _v > 0:
                        _ts.append(_v)
            out["lastWorkAt"] = max(_ts) if _ts else None
            out["durableLast"] = bool(_ts)
            out["durable"] = bool(out["durableWorks"] and out["durableLast"])
            out["durableWhy"] = ("both halves survive a restart: the rows ARE the record and each "
                                 "carries its own stamp" if out["durable"] else
                                 "the rows survive a restart but none carries a stamp, so WHEN "
                                 "this lane last worked is UNKNOWN after one")
            if out["lastWorkAt"] is None:
                out["why"] = ("this lane's rows carry no readable stamp, so WHEN it last worked "
                              "is UNKNOWN")
            return out
        out["why"] = decl.get("lastWhy") or ""
        return out
    if raw is None:
        out["why"] = ("this lane's store carries no %r key, so how much it has done is UNKNOWN and "
                      "does not survive a restart" % wkey)
        return out
    try:
        out["works"] = len(raw) if decl.get("worksAs") == "len" else int(raw)
    except Exception:
        out["why"] = "this lane's %r is not a number this reader understands" % wkey
        return out
    if not lkey:
        out["why"] = decl.get("lastWhy") or ""
        return out
    try:
        v = (doc or {}).get(lkey)
        out["lastWorkAt"] = None if v in (None, 0) else int(v)
    except Exception:
        out["lastWorkAt"] = None
    if out["lastWorkAt"] is None:
        out["why"] = ("this lane's store carries no readable %r, so WHEN it last worked is UNKNOWN"
                      % lkey)
    return out


def lane_beats(allow_import=False):
    """Every declared lane's own record, in one dict. -> {lane: beat}"""
    return dict((k, lane_beat(k, v, allow_import=allow_import)) for k, v in LANES.items())


def _armed(decl, allow_import=False):
    """Is this lane allowed to act? -> (True|False|None, why). None is UNKNOWN, never False."""
    src = decl.get("armedFrom")
    if not src:
        return True, ""
    mod, why = _owner_module(src[0], allow_import=allow_import)
    if mod is None:
        return None, why
    if not hasattr(mod, src[1]):
        return None, ("%s.%s is gone, so whether this lane is allowed to act is UNKNOWN"
                      % (src[0], src[1]))
    _v = getattr(mod, src[1])
    if callable(_v):
        # REG-1879 — an arming that is a DECISION (a constant and his switch) is asked, and it answers (armed, why)
        try:
            _r = _v()
        except Exception as e:
            return None, ("%s.%s() raised %s, so whether this lane is allowed to act is UNKNOWN"
                          % (src[0], src[1], type(e).__name__))
        if isinstance(_r, tuple):
            return (None if _r[0] is None else bool(_r[0])), str(_r[1] if len(_r) > 1 and _r[1] else "")
        return (None if _r is None else bool(_r)), ""
    return bool(_v), ""


def _lane_state(row):
    """The one verdict, from readings already taken. -> (state, why)

    ⚠ THE ORDER IS THE LAW. Every early return here is a case that must not be allowed to fall
    through into a calmer word: an unmeasurable work-list must not become IDLE, a zero without a
    denominator must not become IDLE, and a lane nobody could ask about must not become DARK.
    """
    owed, on_disk = row.get("owed"), row.get("onDisk")
    # 1. WORK OWED COULD NOT BE MEASURED. "cannot ask" and "nothing owed" are opposite facts.
    if owed is None:
        return UNKNOWN, ("how much this lane owes could not be measured — %s. That is UNKNOWN, and "
                         "it is not an idle lane" % (row.get("owedWhy") or "no reason given"))
    # 2. A ZERO WITH NO DENOMINATOR IS UNKNOWN. Nothing owed out of nothing counted is not a
    #    measurement of an empty work-list, it is an absent measurement. [[zero-needs-a-denominator]]
    if owed == 0 and on_disk is None:
        return UNKNOWN, ("this lane owes 0 of an UNKNOWN number of reels. A count with no "
                         "denominator cannot say whether the shelf is clear or unread")
    # 3. DELIBERATELY NOT ACTING, WITH A REASON. Before IDLE, so a disarmed lane with a clear
    #    work-list still says WHY it is not acting rather than looking finished.
    if row.get("armed") is False:
        return DORMANT, ("%d owed of %s on the shelf, and this lane is not acting BY DESIGN: %s"
                         % (owed, on_disk, row.get("armedWhy") or row.get("dormantWhy") or "no reason declared"))
    # 4. NOTHING OWED, AND THE DENOMINATOR IS RIGHT THERE.
    if owed == 0:
        return IDLE, "nothing owed of %s reel(s) on the shelf" % on_disk
    # 5. WORK IS OWED AND NOBODY COULD ASK THIS LANE WHAT IT HAS DONE.
    if not row.get("resolved") or row.get("works") is None:
        return UNKNOWN, ("%d reel(s) owed, and what this lane has done could not be measured — %s. "
                         "An unmeasured lane is not a stopped one, and it is not a working one"
                         % (owed, row.get("beatWhy") or "no reason given"))
    # 6. ⚠⚠ DARK. Work owed, and this lane has NEVER completed a unit. No threshold is involved.
    if not row.get("works"):
        return DARK, ("%d reel(s) owed of %s on the shelf, and this lane has completed 0 units of "
                      "work. That is the state the vault lane sat in for weeks with reads 0 and "
                      "lastTs null while nothing said so" % (owed, on_disk))
    # 7. It has worked, and nothing durable says when.
    if row.get("lastWorkAt") is None:
        return UNTIMED, ("%d reel(s) owed; this lane has completed %d unit(s) and nothing durable "
                         "records WHEN, so whether it has stopped cannot be decided from here — %s"
                         % (owed, row["works"], row.get("beatWhy") or "no clock reading is kept"))
    # 8. It has worked, recently enough to place in time, and no WORK period is declared for it.
    #    ⚠ A TICK PERIOD IS NOT A WORK PERIOD. The vault loop wakes every few seconds and a paid
    #    sweep takes minutes, so grading the work against the loop's sleep would report every
    #    healthy lane STALLED. No lane declares a measured work period today, and that gap is
    #    printed in the census `why` rather than papered over with a guess.
    bound = row.get("boundS")
    if bound is None:
        return UNTIMED, ("%d reel(s) owed; this lane last worked %s ago and declares no WORK "
                         "period, so whether that is late cannot be decided from here"
                         % (owed, _ago(row.get("lastWorkAgeMs"))))
    if (row.get("lastWorkAgeMs") or 0) > bound * 1000.0 * BOUND_SLACK:
        return STALLED, ("%d reel(s) owed and this lane last worked %s ago against its own %gs "
                         "period" % (owed, _ago(row.get("lastWorkAgeMs")), bound))
    return FLOWING, ("%d reel(s) owed and this lane worked %s ago, within its own %gs period"
                     % (owed, _ago(row.get("lastWorkAgeMs")), bound))


def _ago(ms):
    """A duration a person can read. -> str ('UNKNOWN' when nobody measured it)."""
    if ms is None:
        return "an UNKNOWN time"
    s = max(0.0, float(ms) / 1000.0)
    if s < 90:
        return "%.0fs" % s
    if s < 5400:
        return "%.0fm" % (s / 60.0)
    return "%.1fh" % (s / 3600.0)


def lane_census(hist=None, work_=None, beats=None, now_ms=None, allow_import=False):
    """Every declared lane: what it owes, when it last worked, and whether that survives. -> dict

    `work_` and `beats` exist so a law can drive this over a known shelf and a known set of lane
    records without touching his footage or his stores — the same door `reel_retention.plan(hist)`
    and `lane_census.census(src)` already open. Production callers pass neither.

    ⚠ UNKNOWN IS A FIRST-CLASS ANSWER IN EVERY COLUMN, and the counts never collapse it into a
    verdict: a census where nothing could be read reports 0 dark and 0 flowing, which is not a clean
    bill and does not read as one. [[unknown-stays-unknown]]
    """
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    w = work_ if work_ is not None else work(hist)
    if not w.get("ok"):
        # ⚠⚠ EVERY LANE STILL GETS A ROW, AND EVERY ROW SAYS UNKNOWN. A plan that could not be read
        # must never shorten the table — an absent lane and a clear lane look identical, which is
        # the defect this census exists to end.
        owed_all, owed_why = None, str(w.get("why") or "the shelf could not be read")
        on_disk = None
    else:
        owed_all, owed_why, on_disk = w.get("owed"), "", w.get("onDisk")
    beats = lane_beats(allow_import=allow_import) if beats is None else beats
    rows = []
    for lane in sorted(LANES):
        decl = LANES[lane]
        b = dict(beats.get(lane) or {})
        if decl.get("owedFrom") == "own":
            # ⚠⚠ v3018 — SOME LANES ARE NOT IN RETENTION'S PLAN AT ALL. The three lanes declared
            # before this one all take their work-list from retention tags, so a lane that
            # retention has no tag for could not be supervised at work level however alive it was.
            # tvd-retro-triage is exactly that: it walks frames STRUCTURALLY, before any tag
            # exists, which is why "running and doing nothing" was invisible for it — the shape
            # vaultAutoread died in. This asks the lane itself, and an owner that cannot answer
            # leaves owed None so _lane_state renders UNKNOWN rather than IDLE.
            _mod, _mwhy = _owner_module(decl.get("owner"), allow_import=allow_import)
            if _mod is None or not hasattr(_mod, "owed"):
                owed = None
                owed_why = _mwhy or ("%s declares owedFrom 'own' and exposes no owed() — how much "
                                     "it owes is UNKNOWN" % decl.get("owner"))
            else:
                try:
                    _o = _mod.owed()
                except Exception as _e:
                    owed, owed_why = None, ("%s.owed() raised %s — UNKNOWN, never zero"
                                            % (decl.get("owner"), type(_e).__name__))
                else:
                    if not isinstance(_o, dict) or not _o.get("ok"):
                        owed = None
                        owed_why = str((_o or {}).get("why") or "the lane could not measure its own work")
                    else:
                        owed = _o.get("owed")
                        owed_why = "" if owed is not None else str(_o.get("why") or "")
                        if on_disk is None:
                            on_disk = _o.get("onDisk")
        elif decl.get("owedFrom") == "releasable":
            owed = None if owed_all is None else len(w.get("releasable") or [])
        elif owed_all is None:
            owed = None
        elif lane == "vault" and w.get("vaultKnown") is False:
            # The tag map is only the reels retention already named for this lane. A reel at
            # PRINTER can owe a read under another tag, and that half is invisible when the
            # stamp log will not read. The tag count alone would be a shorter list wearing a
            # measured number. UNKNOWN, not idle. [[unknown-stays-unknown]]
            owed = None
            owed_why = str(w.get("vaultWhy") or
                           "the river could not be asked, so a reel at PRINTER is not in this count")
        else:
            owed = len([r for r in owed_all if lane in _lanes_of(r)])
        armed, armed_why = _armed(decl, allow_import=allow_import)
        last_at = b.get("lastWorkAt")
        row = {
            "lane": lane,
            "what": decl.get("what"),
            "owedFrom": decl.get("owedFrom"),
            "tags": sorted(t for t, l in OWED_BY.items() if l == lane),
            "readClears": sorted(t for t, l in OWED_BY.items()
                                 if l == lane and t in READ_CLEARS),
            "owed": owed,
            "owedWhy": owed_why,
            "onDisk": on_disk,
            "resolved": bool(b.get("resolved")),
            "store": b.get("store"),
            "storeReadable": b.get("storeReadable"),
            "works": b.get("works"),
            "lastWorkAt": last_at,
            "lastWorkAgeMs": (None if last_at is None else max(0, now_ms - int(last_at))),
            "durable": b.get("durable"),
            "durableWorks": b.get("durableWorks"),
            "durableLast": b.get("durableLast"),
            "durableWhy": b.get("durableWhy") or "",
            "beatWhy": b.get("why") or "",
            "boundS": decl.get("boundS"),
            "armed": armed,
            "armedWhy": armed_why,
            "dormantWhy": decl.get("dormantWhy"),
        }
        row["state"], row["why"] = _lane_state(row)
        rows.append(row)
    counts = {"declared": len(rows)}
    for st in (FLOWING, UNTIMED, STALLED, DARK, IDLE, DORMANT, UNKNOWN):
        counts[st.lower()] = len([r for r in rows if r["state"] == st])
    counts["durable"] = len([r for r in rows if r["durable"] is True])
    counts["bounded"] = len([r for r in rows if r["boundS"] is not None])
    dec_ok, dec_why = declared_covers_the_map()
    if counts[DARK.lower()]:
        say = ("%d of %d lane(s) have work owed and have never done any of it"
               % (counts[DARK.lower()], counts["declared"]))
    elif counts[STALLED.lower()]:
        say = "%d of %d lane(s) have stopped working while work waits" % (
            counts[STALLED.lower()], counts["declared"])
    elif counts[UNKNOWN.lower()]:
        say = "%d of %d lane(s) could not be measured at all" % (
            counts[UNKNOWN.lower()], counts["declared"])
    elif counts[UNTIMED.lower()]:
        # ⚠⚠ UNTIMED IS NOT A CLEAN BILL AND MUST NOT BE SUMMARISED AS ONE. A first cut's closing
        # sentence read "3 of 3 lane(s) are working or idle with nothing owed" over a census whose
        # vault row carried owed 8 — a right count under a phrase that had stopped describing it.
        # This is the headline on his tree today, so it says exactly what is true: work is waiting
        # and nothing can decide whether the lane carrying it has stopped.
        # [[label-outlived-referent]] [[zero-needs-a-denominator]]
        say = ("%d of %d lane(s) have work owed and no way to tell whether they have stopped"
               % (counts[UNTIMED.lower()], counts["declared"]))
    else:
        say = ("no lane is dark or stalled — %d flowing · %d idle · %d dormant of %d declared"
               % (counts[FLOWING.lower()], counts[IDLE.lower()],
                  counts[DORMANT.lower()], counts["declared"]))
    # ⚠ THE TWO GAPS TRAVEL WITH THE VERDICT. `bounded` is how many lanes could ever reach STALLED;
    # with none declared, STALLED is a state nothing can produce and a reader deserves to know that
    # rather than trusting an absence. `durable` is how many survive a restart. Both are printed as
    # N of M, because a gap with no denominator is the thing this file argues against.
    say += (" · %d of %d keep a durable record · %d of %d declare a WORK period, so STALLED is "
            "reachable for %d" % (counts["durable"], counts["declared"],
                                  counts["bounded"], counts["declared"], counts["bounded"]))
    return {"ok": True, "rows": rows, "counts": counts, "say": say,
            "onDisk": on_disk, "declaredOk": dec_ok, "declaredWhy": dec_why,
            "slack": BOUND_SLACK}


def plan(hist=None):
    """Retention's own answer, unmodified. -> dict"""
    import reel_retention as _rr
    h = hist or os.environ.get("TV_HIST") or os.path.join(HERE, "frames", "hist")
    return _rr.plan(h)


def _lanes_of(row):
    """Every lane one owed row counts toward. The tag's own lane, then a read that tag did not name."""
    lanes = []
    if not isinstance(row, dict):
        return lanes
    primary = row.get("lane")
    if primary:
        lanes.append(primary)
    for extra in row.get("also") or ():
        if extra and extra not in lanes:
            lanes.append(extra)
    return lanes


def _vault_read_lane(tag, reel, station, seals):
    """'vault' when this reel owes the vault a read, else None. Asks vault_owes_read. Never a second table.

    A tag the vault already owns does not depend on the seal store. Anything else is the PRINTER
    half: an unreadable seal store adds nothing, and a reel the store already holds is not re-bought.
    """
    if not reel or not vault_owes_read(tag, station, reel):
        return None
    if tag in lane_read_tags("vault"):
        return "vault"
    if not isinstance(seals, dict):
        return None
    import reel_retention as _rr
    if _rr.lookup_either_way(seals, reel) is not None:
        return None
    return "vault"


def _river_and_seals():
    """The pair the sweeper already asks. -> (positions|None, seals|None, why). Never raises.

    The console process already holds that reader. A gate, where the console is not loaded, reads
    the same two stores. positions() answers {} for a store that was never written — measured and
    empty, not unknown. None is a store that would not read.
    """
    ca = sys.modules.get("control_app")
    if ca is not None and hasattr(ca, "_vault_positions_and_seals"):
        try:
            pos, seals = ca._vault_positions_and_seals()
        except Exception as e:
            return None, None, "the river could not be asked (%s)" % type(e).__name__
        if pos is None:
            return None, seals, ("the river could not be read, so a reel at PRINTER is not in "
                                 "the vault count")
        return pos, seals, ""
    try:
        import river_stamp as _rvs
        pos, why = _rvs.positions()
    except Exception as e:
        return None, None, "the river could not be asked (%s)" % type(e).__name__
    seals = None
    try:
        import frame_authority as _fa
        import tv_diablo as _tvd
        blob, ok = _fa.sealed_sessions(_tvd._fixture_root(HERE))
        seals = blob if ok else None
    except Exception:
        seals = None
    if pos is None:
        return None, seals, (why or "the river could not be read, so a reel at PRINTER is not in "
                                   "the vault count")
    return pos, seals, ""


_RIVER_ASK = object()


def _take_river(positions, seals):
    """Injected readings, or the live pair. A caller that passes None has already measured unknown."""
    if positions is not _RIVER_ASK and seals is not _RIVER_ASK:
        why = "" if positions is not None else (
            "the river could not be read, so a reel at PRINTER is not in the vault count")
        return positions, seals, why
    live_pos, live_seals, why = _river_and_seals()
    if positions is _RIVER_ASK:
        positions = live_pos
    if seals is _RIVER_ASK:
        seals = live_seals
    if positions is None and not why:
        why = "the river could not be read, so a reel at PRINTER is not in the vault count"
    return positions, seals, why


def work(hist=None, positions=_RIVER_ASK, seals=_RIVER_ASK):
    """What the lanes still owe, straight off retention's plan. -> dict

    ⚠ UNKNOWN IS NOT "NOTHING OWED". A plan that could not be built returns ok False and an
    explicit why, never an empty work list — an empty list is a MEASUREMENT ("every lane is
    caught up") and must never be produced by a failed read. [[unknown-stays-unknown]]
    [[zero-needs-a-denominator]]

    ⚠⚠ THE TAG IS WHY THE REEL IS STILL ON DISK. It is not which lane owes a read. A reel at
    PRINTER (names read, no seal) that retention files as `recent` was held, and one it files as
    `zero-pages` was billed only to the chronicle, while vault_owes_read already said the vault
    owes both a read. The census then said the vault lane was idle over work the sweeper had.
    The tag's lane stays. The vault's read is asked of that one rule and counted beside it.
    `vaultKnown` False means the stamp log would not read: the vault's number is UNKNOWN, not
    the tags alone. [[the-unjoined-end]]
    """
    try:
        p = plan(hist)
    except Exception as e:
        return {"ok": False, "why": "retention could not plan (%s)" % type(e).__name__,
                "neverRecorded": False,
                "owed": None, "held": None, "releasable": None}
    if not p.get("ok"):
        # ⚠⚠ v3400 — THIS READ THE WRONG KEY AND THREW AWAY THE ONLY USEFUL SENTENCE.
        # plan() publishes its failure reason as `why`; `say` exists only on the SUCCESS payload,
        # so `p.get("say")` was None on EVERY failure and this always fell through to the generic
        # fallback. v3393 fixed plan() to answer "no footage tree on this machine yet" and its
        # own comment names the shelf as a consumer that "drew a 0x0 box" — and the shelf never
        # received a word of it. MEASURED on his ALT console 2026-09-20: the eagle read
        # "the shelf driver's last beat 2.5h ago reported NOT ok: retention could not read this
        # shelf" on a machine whose only fault is that nothing has ever been recorded on it.
        # Reproduced on the Mac with plan(<absent tree>). [[the-unjoined-end]]
        return {"ok": False,
                "why": str(p.get("say") or p.get("why")
                           or "retention could not read this shelf"),
                "neverRecorded": bool(p.get("neverRecorded")),
                "owed": None, "held": None, "releasable": None}
    positions, seals, river_why = _take_river(positions, seals)
    vault_known = positions is not None
    owed, held = [], []
    for k in (p.get("kept") or []):
        tag = k.get("tag")
        reel = k.get("reel")
        rid = os.path.basename(str(reel or ""))
        row = {"reel": reel, "tag": tag, "why": k.get("why"), "mb": k.get("mb")}
        station = positions.get(rid) if vault_known else None
        extra = _vault_read_lane(tag, rid, station, seals) if vault_known else None
        if tag in OWED_BY:
            row["lane"] = OWED_BY[tag]
            if extra and extra != row["lane"]:
                row["also"] = [extra]
            owed.append(row)
        elif extra:
            row["lane"] = extra
            owed.append(row)
        else:
            held.append(row)
    return {"ok": True, "why": "", "owed": owed, "held": held,
            "releasable": [c.get("reel") if isinstance(c, dict) else str(c)
                           for c in (p.get("candidates") or [])],
            "onDisk": p.get("onDisk"), "say": p.get("say"),
            "vaultKnown": vault_known,
            "vaultWhy": "" if vault_known else river_why}


def stages(hist=None):
    """Every reel placed on the river, newest first. -> dict

    ⚠ NEWEST FIRST, because that is how he reads it: *"timestamps organzied from what came in
    last"*. The reel id carries the stamp (`reel_s_<ms>_<n>`), so the order is the film's own,
    never the filesystem's.
    """
    import reel_story as _rs
    w = work(hist)
    if not w.get("ok"):
        return {"ok": False, "why": w.get("why"), "rows": None}
    rows = []
    for row in (w["owed"] or []) + (w["held"] or []):
        stage = _rs.TAG_STAGE.get(row["tag"])
        rows.append(dict(row, stage=stage, ts=_reel_ts(row["reel"])))
    for r in (w["releasable"] or []):
        rows.append({"reel": r, "tag": "eligible", "why": "every lane is finished with it",
                     "lane": None, "stage": _rs.TAG_STAGE.get("eligible"), "ts": _reel_ts(r)})
    rows.sort(key=lambda r: (r["ts"] is None, -(r["ts"] or 0)))
    unplaced = [r["reel"] for r in rows if not r["stage"]]
    return {"ok": True, "why": "", "rows": rows, "stageOrder": list(_rs.STAGES),
            "unplaced": unplaced, "onDisk": w.get("onDisk")}


def _reel_ts(reel):
    """The millisecond stamp inside `reel_s_<ms>_<n>`. -> int|None (None is UNKNOWN, not 0)."""
    try:
        return int(str(reel).split("_")[2])
    except Exception:
        return None


def beat(hist=None, write=True):
    """Record that the driver looked, and what it saw. -> dict

    This is what Heart 2.0 supervises: a lane with work owed and a heartbeat that has stopped is
    the state `vaultAutoread` sat in for weeks with `reads: 0, lastTs: null` and nothing said so.
    """
    w = work(hist)
    lanes = {}
    for row in (w.get("owed") or []):
        # A vault number taken from the tags alone, while the stamp log would not read, is the
        # shorter list. Leave it out of this count. The census row says UNKNOWN.
        for lane in _lanes_of(row):
            if lane == "vault" and w.get("vaultKnown") is False:
                continue
            lanes[lane] = lanes.get(lane, 0) + 1
    # ⚠ THE SAME `work()` ANSWER, PASSED IN. Calling lane_census() bare here would build a SECOND
    # retention plan for one beat — two reads of a moving shelf, which can disagree, and paid for
    # twice. One question, asked once.
    try:
        cen = lane_census(hist, work_=w)
    except Exception as e:
        cen = {"ok": False, "rows": None, "counts": None,
               "say": "the lane census could not be built (%s), so nothing is known about any "
                      "lane — which is not the same as every lane being fine" % type(e).__name__}
    out = {"at": int(time.time() * 1000), "ok": bool(w.get("ok")), "why": w.get("why") or "",
           # v3400 — carried so the heart can tell a NEW machine from a BROKEN lane. Without it
           # the doctor can only read the sentence, and a row that greps English is a row that
           # breaks when the English improves.
           "neverRecorded": bool(w.get("neverRecorded")),
           # ⚠ KEPT, AND NO LONGER THE WHOLE STORY. `owedByLane` is built by COUNTING owed reels,
           # so a lane owing zero is absent from it — measured on his tree, it read {"vault": 18}
           # and the chronicle lane appeared nowhere. Existing readers keep their field; `lanes`
           # below is the one that declares every lane whether it owes anything or not.
           "owedByLane": lanes,
           "lanes": cen.get("rows"),
           "laneCounts": cen.get("counts"),
           "laneSay": cen.get("say"),
           "owed": None if w.get("owed") is None else len(w["owed"]),
           "held": None if w.get("held") is None else len(w["held"]),
           "releasable": None if w.get("releasable") is None else len(w["releasable"]),
           "onDisk": w.get("onDisk")}
    if write:
        # ⚠⚠ tmp + os.replace, NEVER a bare open(p, "w"). That call TRUNCATES BEFORE it writes, so a
        # crash or a full disk mid-beat leaves an empty file that reads back as a lane census
        # nobody could build — and this repo has already emptied a 6 MB bible.html exactly that way.
        # [[open-for-write-truncates-first]] [[bible-writes-must-be-atomic]]
        dest = _beat_path()
        if dest is None:
            out["persisted"] = False
            out["persistWhy"] = ("TV_HIST asked for a fixture world and the isolation rule could "
                                 "not be resolved, so this beat was NOT written anywhere rather "
                                 "than written into his live tv/")
            return out
        try:
            tmp = dest + ".tmp"
            with io.open(tmp, "w", encoding="utf-8") as fh:
                json.dump(out, fh, indent=1)
            os.replace(tmp, dest)
            out["persisted"] = True
        except Exception as e:
            out["persisted"] = False
            out["persistWhy"] = "%s — the beat was not recorded" % str(e)[:120]
    return out


def last_beat():
    """The last recorded look. -> dict|None (None means it has NEVER run — not 'nothing owed')."""
    try:
        with io.open(_beat_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def main(argv):
    b = beat()
    print("🎞🚚 SHELF DRIVER — retention decides, this runs it")
    if not b["ok"]:
        print("   ⚠ UNMEASURED: %s" % b["why"])
        return 1
    print("   %s reel(s) on disk · %s owed · %s held · %s releasable"
          % (b["onDisk"], b["owed"], b["held"], b["releasable"]))
    # ── THE LANE CENSUS. Every declared lane gets a row, including the ones owing nothing. ──────
    cen = lane_census(allow_import=True)
    if not cen.get("declaredOk"):
        print("   🔴 %s" % cen.get("declaredWhy"))
    print("\n   LANES — %s" % cen["say"])
    _mark = {FLOWING: "🟢", IDLE: "⚪", DORMANT: "🟡", UNTIMED: "🟠",
             STALLED: "🔴", DARK: "🔴", UNKNOWN: "❔"}
    for r in cen["rows"]:
        print("      %s %-10s %-8s owed %-6s works %-7s durable %-5s  %s"
              % (_mark.get(r["state"], "❔"), r["lane"], r["state"],
                 "UNK" if r["owed"] is None else r["owed"],
                 "UNK" if r["works"] is None else r["works"],
                 {True: "yes", False: "no", None: "UNK"}[r["durable"]],
                 r["why"][:96]))
    st = stages()
    if st["ok"]:
        if st["unplaced"]:
            print("   ⚠ %d reel(s) have no stage on the river: %s"
                  % (len(st["unplaced"]), st["unplaced"][:3]))
        for s in st["stageOrder"]:
            n = sum(1 for r in st["rows"] if r["stage"] == s)
            print("      %-12s %d" % (s, n))
    return 0


if __name__ == "__main__":
    try:
        from console_safe import enable as _cs
        _cs()
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
