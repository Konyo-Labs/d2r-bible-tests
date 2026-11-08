#!/usr/bin/env python3
"""A LOCK THAT UNLOCKS ITSELF — and cannot be opened by hand.

Konyo, 2026-09-02:

    "wilson scores all over.. once that's integrated anywhere and anyplace it can be, the system
     proves itself. START AT THE PRINTER AND REELS WITH THE WILSON SCORE FIRST so that can be done
     beforehand in order, and then once wilson score proves itself within the processing of reels —
     meaning THEATRE MODE AND THE SHELF... so if wilson score eventually proves itself within the
     optimizing and templated and routing down the river stream we mentioned, for each reel a
     unified logic, then it should work and THEN ARM ITSELF. arithmetic as you see.. A LOCK UNTIL
     IT AUTOMATICALLY UNLOCKS WITH A QUEUE FOR WILSON SCORE. this can be used in a bunch of places
     not yet built if we have them too."

This replaces "Konyo flips `_PRUNE_SAFE_TO_RUN` by hand". He does not want to be the arming
mechanism; he wants the system to EARN its permission and then take it.

═══ THE ONE THING THAT WOULD MAKE THIS A LIE ═══════════════════════════════════════════════════

**k and n count SABOTAGES, never agreements.** [[heart-first]] §5, and it is the whole risk:

    an invariant that always agrees may be perfect, or INERT, and those are indistinguishable.

A lock fed by an agreement-rate opens *because nobody ever tested it* — the exact failure the lock
exists to prevent, wearing the lock's own uniform. So:

    n = deliberate sabotages ATTEMPTED against this surface's guards
    k = times a guard REFUSED (went red) for its own reason

A guard that has never been sabotaged contributes NOTHING. `n == 0` is UNPROVEN, and unproven is
not failing — a low score names work to do, and a gate that turns amber at its own newest checks
is ignored within a week. [[heart-first]] again, and it is why `state()` has four values.

═══ WHY WILSON AND CONFLUENCE, BOTH ═══════════════════════════════════════════════════════════

`tv/confidence.py` is THE home for this maths and says why in its own words: "Wilson measures how
many looks agreed, never whether the looks were INDEPENDENT... The two run TOGETHER or neither
means anything." Four re-runs of one sabotage by one harness is one proof wearing four hats.

So a lock opens only when BOTH clear:

    wilson_lower(k, n) >= bar        how much evidence, honest about small n
    confluence(kinds)  >= kinds_bar  how many INDEPENDENT KINDS of evidence

⚠ This module CALLS confidence.py. It does not restate the maths. A second copy of a safety
routine is [[copy-drift]]'s worst case, because the two diverge and only one gets tuned.

═══ THE ORDER IS PART OF THE LOCK ═════════════════════════════════════════════════════════════

He gave a dependency chain, and a lock late in it cannot open early no matter how good its own
score is — proving the deleter in isolation proves nothing about the river feeding it:

    printer + reels  ->  theatre + shelf  ->  routing / the river  ->  the deleter

`after` encodes that. A lock whose prerequisite is not OPEN reports LOCKED with the prerequisite
named, never with its own score, so nobody reads a high number as "nearly there".

═══ WHAT THIS MODULE WILL NOT DO ═══════════════════════════════════════════════════════════════

It DECIDES and REPORTS. It never performs the action, never writes an unlock flag, and has no
override parameter — an override is the hand-arming this replaces. An unreadable ledger is
UNKNOWN, and UNKNOWN is LOCKED: fail closed, and say which of the two it is.

═══ WHOSE EVIDENCE IT IS — #181, HIS RULING 2026-10-22 ═══════════════════════════════════════

"deans is logically related and derived from his own console and not mimicking mine". The shared
ledger (tv/.self_arming.jsonl) is TRACKED, so it holds only what is a property of the CODE. A LIVE
trial is a property of the PC that ran it and goes to that PC's own ledger, which no checkout
tracks: self_arming.here.jsonl in git's COMMON dir, one per PC and shared by the main checkout and
every linked worktree (REG-2473; tv/.self_arming.here.jsonl, gitignored, only where no git dir can
be found). A live row the shared file already carries is LEGACY: counted on no PC, reported as a
count. `--adopt-legacy-live --reason "..." --confirm` moves it to the PC that measured it - a
person's statement about where real evidence came from, never new evidence, and nothing runs it on
its own.
"""

import hashlib
import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from confidence import wilson_lower, confluence   # noqa: E402  — one home for the maths

# ⚠⚠ SNAPSHOT THIS MODULE'S IDENTITY AT IMPORT, and it must happen HERE rather than lazily.
# `registry_may_be_incomplete()` answers True for UNKNOWN as well as STALE — deliberately, since
# "I never checked whether my registry is current" is not grounds for confidence. But that makes
# an un-snapshotted process permanently forgiving: every unrecognised src would read as "UNKNOWN,
# relaunch to judge", and a genuinely forged row would be excused forever. The snapshot is what
# makes the softening narrow instead of universal. [[feedback-blind-fixture-green-gate]]
try:
    import code_staleness as _code_staleness   # noqa: E402
    _code_staleness.snapshot("self_arming")
except Exception:
    pass

#: THE SHARED PROOF QUEUE — and it is TRACKED. ⚠⚠ #181 (REG-2470): this line used to call it "untracked", like
#: .console_scars.json and .second_eye.jsonl, and `git ls-files` said otherwise: it ships to EVERY PC with every
#: update. So it may hold only what is a property of the CODE - a sabotage, a cross-family refusal, a CI red - which
#: is equally true on any install. A LIVE trial is measured against ONE PC's running console, shelf, disk history or
#: window, and it lives in that PC's own ledger (_here_path). MEASURED at 7285e7efc: 657 rows = sabotage
#: 583, cross-family 25, live 49, the 49 all measured on Konyo's Mac - and Dean's heart read frame.release "earned
#: 85/85" = 35 code rows + 50 of the Mac's live checks. [[feedback-per-pc-personal-data]] [[unknown-stays-unknown]]
#: THE DEFAULT ONLY. Deliberately NOT `os.environ.get(...) or ...` at module level.
LEDGER = os.path.join(HERE, ".self_arming.jsonl")
#: THIS PC's own proof ledger's name in git's COMMON dir - one file per PC, shared by the main checkout and every
#: linked worktree, inside no work tree (REG-2473). _here_path() resolves it at call time, as _ledger_path() does LEDGER.
MACHINE_LEDGER = "self_arming.here.jsonl"
#: where it lives only when no git dir can be found (a heart2 sandbox, an unpacked copy) - gitignored, and it dies with
#: the checkout, which the door and the report SAY. A fixture may patch this attribute; a patch is honoured.
HERE_LEDGER = os.path.join(HERE, ".self_arming.here.jsonl")
_HERE_LEDGER_DEFAULT = HERE_LEDGER
#: the evidence KINDS that are a property of a PC rather than of the code. Every other kind is shared.
PER_PC_KINDS = frozenset(("live",))
#: what the last fold_deferred() put where - run_gates' fold line names both files from it, never one for both
LAST_FOLD = {"shared": 0, "here": 0}


def _ledger_path():
    """Where the proof queue lives, resolved at CALL time. -> str

    ⚠ v2438 — `test_import_bound_paths` CAUGHT THIS AS AN IMPORT-BOUND PATH AND IT WAS RIGHT.
    The first cut read the env var at module level, which freezes whatever the environment was at
    IMPORT: a fixture setting TV_SELF_ARMING_LEDGER afterwards is a silent no-op, and its proof
    rows land in HIS queue. That registry exists because exactly that truncated 525,187 bytes of
    paid page reads to 748. [[feedback-fixtures-never-touch-live-data]]

    Registering it as import-bound would have satisfied the gate. It is resolved at call time
    INSTEAD, because of what this file gates: a fixture that accidentally banks into the real
    queue does not merely corrupt a record — it RAISES A SCORE, and a raised score opens a lock
    that deletes footage. When a mistake's blast radius is his data, the fix goes in the
    fail-safe direction rather than the documented one.

    Both redirects work now: set TV_SELF_ARMING_LEDGER, or patch the module attribute.
    """
    return os.environ.get("TV_SELF_ARMING_LEDGER") or LEDGER


def _here_path():
    """THIS PC's own proof ledger, resolved at call time. -> str  (see _here_where for which kind of place it is)"""
    return _here_where()[0]


def _machine_dir(repo=None):
    """THIS PC's own directory: git's COMMON dir for the checkout at `repo`. -> (dir, None) | (None, why)

    heart2._git_common_dir is the one implementation (R10, REG-2340): read from the files git itself reads, never by
    running git - inside a hook GIT_DIR is inherited, and git would answer for whichever tree set it. Asked, not
    copied: a third copy of that walk is how two of them drift. [[copy-drift]]"""
    try:
        import heart2 as _h2
        return _h2._git_common_dir(os.path.dirname(HERE) if repo is None else repo)
    except Exception as e:  # the helper could not answer: this checkout's own file, and the door says why
        return None, "git's common dir could not be asked (%s)" % type(e).__name__


def _here_where(repo=None):
    """#181 - THIS PC's own proof ledger, and what kind of place it is. -> (path, scope, why)

      seam      TV_SELF_ARMING_HERE names it outright
      follows   a fixture redirected the SHARED queue (TV_SELF_ARMING_LEDGER, or LEDGER patched) and named no per-PC
                file: a sibling of its own queue, never this PC's real one, in either direction - its live rows must
                not land in his ledger, and his live rows must not count in its world
      patched   a fixture patched HERE_LEDGER: honoured, so a redirect never silently fails to take
      machine   git's COMMON dir: ONE file per PC, shared by the main checkout and every linked worktree
      checkout  no git dir could be found (a heart2 sandbox, an unpacked copy): this checkout's tv/ file, and why

    ⚠⚠ REG-2473 - IT WAS ONE PER CHECKOUT. The first cut answered tv/.self_arming.here.jsonl of whichever checkout ran,
    and fleet agents may write only in linked worktrees (his main tree is the running console). A deliberate live bank
    from a worktree - `python3 tv/vault_wilson.py --bank` against his console on :17772 - landed in THAT worktree's
    gitignored file: his console never counted it, git status showed nothing to carry it, and `git worktree remove`
    deleted it. Before the split the same bank went into the tracked ledger and travelled with the ship, so that was a
    NEVER-DROP regression. The common dir is the R10 precedent (heart2._shared_store): never listed by git, never
    copied into a heart2 sandbox, never in a work tree. [[feedback-fixtures-never-touch-live-data]]
    """
    env = os.environ.get("TV_SELF_ARMING_HERE")
    if env:
        return env, "seam", ""
    shared = _ledger_path()
    if os.path.abspath(shared) != os.path.abspath(os.path.join(HERE, ".self_arming.jsonl")):  # PER-PC-FOLLOWS
        return os.path.splitext(shared)[0] + ".here.jsonl", "follows", ""
    if os.path.abspath(HERE_LEDGER) != os.path.abspath(_HERE_LEDGER_DEFAULT):  # PER-PC-PATCHED
        return HERE_LEDGER, "patched", ""
    common, why = _machine_dir(repo)
    if common:  # PER-MACHINE
        return os.path.join(common, MACHINE_LEDGER), "machine", ""
    return (os.path.join(os.path.dirname(HERE) if repo is None else repo, "tv", os.path.basename(_HERE_LEDGER_DEFAULT)),
            "checkout", why)


def here_label():
    """Where THIS PC's own ledger is, in words and with no path - a gate log or a status poll is not his machine's to
    publish. -> str"""
    p, scope, why = _here_where()
    if scope == "machine":
        return "%s in git's common dir - one per PC, shared by every checkout of this repo" % os.path.basename(p)
    if scope == "checkout":
        return "this checkout's own tv/%s - no git dir was found, so it dies with this checkout" % os.path.basename(p)
    return "a fixture's %s (%s)" % (os.path.basename(p), scope)


def _is_per_pc(row):
    """Is this row a property of ONE PC (a live trial) rather than of the code? -> bool"""
    return isinstance(row, dict) and str(row.get("kind")) in PER_PC_KINDS


def _line_is_per_pc(ln):
    """_is_per_pc for one ledger LINE; a line that is not JSON is not a per-PC row. -> bool"""
    try:
        return _is_per_pc(json.loads(ln))
    except ValueError:
        return False


def _append_here(row):
    """Append one row to THIS PC's ledger. -> dict (the row written)

    ⚠ NEVER DEFERRED. TV_SELF_ARMING_DEFER exists because the SHARED queue is TRACKED: banking into it mid-run
    dirtied an input of 147 gates (REG-2296). This file is in no work tree (git's common dir, REG-2473 - or a
    gitignored tv/ file where no git dir exists), so it is no gate's input and nothing waits."""
    with io.open(_here_path(), "a", encoding="utf-8") as fh:  # PER-PC-WRITE
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def _bank_path():
    """Where a NEW row is appended, resolved at call time. -> str

    v3775 (REG-2296) — A GATE RUN DOES NOT DIRTY THE TRACKED QUEUE WHILE OTHER GATES ARE PROVED.
    Wilson gates bank here mid-run, so every later gate that reads this file was refused by the gate
    ledger ("proved on uncommitted tv/.self_arming.jsonl") - 147 of 497 reruns on a v3775 bump. While
    run_gates records proofs it sets TV_SELF_ARMING_DEFER to a scratch file outside the checkout; a row
    bound for the DEFAULT queue goes there and run_gates folds it in after the last gate. A fixture
    that redirected the queue (env or LEDGER patched) still writes where it pointed."""
    p = _ledger_path()
    d = os.environ.get("TV_SELF_ARMING_DEFER")
    if d and os.path.abspath(p) == os.path.abspath(os.path.join(HERE, ".self_arming.jsonl")):  # ARMING-DEFER
        return d
    return p


def fold_deferred(path):
    """Append every row a deferred run banked into the real queue.
    A line that is not one JSON object is not testimony this run made, so it is not folded and is
    counted as refused. -> (folded, refused)

    #181 (REG-2470) - THE FOLD ROUTES EXACTLY AS bank() DOES: a LIVE row goes to THIS PC's own ledger
    (_here_path), every other row to the shared one. LAST_FOLD says how many went where."""
    LAST_FOLD.update(shared=0, here=0)
    try:
        with io.open(path, encoding="utf-8") as fh:
            lines = [ln for ln in fh.read().splitlines() if ln.strip()]
    except OSError:
        return 0, 0
    good = []
    for ln in lines:
        try:
            if isinstance(json.loads(ln), dict):
                good.append(ln)
        except ValueError:
            pass
    here, shared = [], []
    for ln in good:
        (here if _line_is_per_pc(ln) else shared).append(ln)  # PER-PC-FOLD
    if here:
        with io.open(_here_path(), "a", encoding="utf-8") as fh:  # PER-PC-FOLD-WRITE
            fh.write("\n".join(here) + "\n")
    if shared:
        with io.open(_ledger_path(), "a", encoding="utf-8") as fh:  # ARMING-FOLD
            fh.write("\n".join(shared) + "\n")
    LAST_FOLD.update(shared=len(shared), here=len(here))  # FOLD-SAID
    return len(good), len(lines) - len(good)  # the caller removes its own scratch file

#: What counts as an INDEPENDENT KIND of proof, and what each is worth. Passed to confluence()
#: rather than hardcoded there, because what counts as independent differs per lane.
#: ⚠ An unknown kind scores 0 by design — a kind nobody has weighted is a kind nobody has thought
#: about, and a default would silently pay it as if someone had.
KINDS = {
    "sabotage": 1.0,    # a guard broken on purpose and watched to go red for its OWN reason
    "cross-family": 0.8,  # a different model family refused it on the real artifact
    "live": 0.7,        # measured against his running console, not a fixture
    "ci": 0.6,          # went red on a runner, on the same bytes
    "fixture": 0.3,     # a harness case — real, and the weakest kind on its own
}

#: name -> what it would do · the bar it must clear · what must be OPEN before it may open at all.
#: THE ORDER IS HIS. Nothing here may be reordered to make something arm sooner.
LOCKS = {
    # ⚠⚠ v2570 — THE PRINTER HAD NO LOCK AT ALL, and it is step 1 of his own chain. Measured
    # 2026-09-04: fourteen locks and routes were declared and NOT ONE named the printer, the river
    # or reel selection, so the layer that walks every reel he owns was believed purely because
    # nobody had ever attempted to break it. That is the state this module calls INERT.
    # His words: "build the printer lock and wire the whole river".
    #
    # It earns trust in what it PRINTS rather than permission to act — printer.stream() writes
    # nothing and deletes nothing — but it is declared here rather than in ROUTES because the
    # deleter now waits on it, and `after` may only name something the chain can resolve.
    "printer.stream": {
        "surface": "THE RIVER", "acts": "walks every reel from the door to the far end",
        "bar": 0.510, "kinds_bar": 1.0, "after": [],
    },
    # step 1 — the printer and the reels
    "vault.sweep_start": {
        "surface": "VAULT", "acts": "starts a paid sweep",
        "destructive": True,   # money spent cannot be unspent
        "bar": 0.510, "kinds_bar": 1.0, "after": [],
    },
    # step 1 — the actions that change his ledger
    "vault.apply": {
        "surface": "VAULT", "acts": "mules items between characters",
        "destructive": True,   # it rewrites his ledger
        "bar": 0.722, "kinds_bar": 1.3, "after": ["vault.sweep_start"],
    },
    # ⚠⚠ THIS ONE CAN NEVER BE PROVEN, AND THAT IS A PROPERTY OF THE DOOR, NOT A MISSING HARNESS.
    # `vault_forget()` is seven lines, one return, always ok — it has NO refusal path, so there is
    # no state in which it must say no and therefore nothing a sabotage could attempt. That is
    # deliberate: its own docstring says the swept memory is an optimisation and "an optimisation
    # he cannot clear is a cage", and the ledger it drops is rebuildable from the reels. Gating it
    # would be exactly the button-blocking his standing ruling forbids — locks are BADGED, never
    # enforced.
    #
    # So it sits at n=0 forever, and the panel used to explain that with the same sentence it uses
    # for a door nobody has got round to testing: "no sabotage has been attempted ... That is not a
    # failure." True, and it implies a harness is merely MISSING. Those are different facts —
    # nobody-looked versus there-is-nothing-to-look-at — and collapsing them is the seventh shape
    # of an unmeasured number. `unprovable` says which one this is, in the panel, out loud.
    # [[unknown-stays-unknown]]
    #: 154 — THE NUMBER HE MAKES STORAGE DECISIONS ON. `prunedMb` was HARDCODED to 0 at the only
    #: call site, so "the prune has never freed a byte" was a fact about the CALLER; that framing
    #: was retracted. The call site passes None now — measured on his store, 8,270 rows carrying 0
    #: against 280 carrying None — and the remainder is that nothing has ever passed a REAL figure.
    #: His ruling: *"fix it to the hardening and wilsons and to the heart so it proves itself
    #: before its unlocked."* So the reporter earns its unlock like every other surface.
    #: ⚠ IT GUARDS THE REPORT, NOT THE DELETER. `prune.arm` already guards whether the prune may
    #: act; this guards whether the row may CLAIM. They fail differently and must not share a lock.
    #: A7·ROUTE — WHERE A REEL IS IN THE RIVER, decided by the reel's own evidence and never by
    #: why we are keeping its bytes. Measured on his shelf 2026-09-05: 40 reels, 29 never read,
    #: `vault-owes` matching 0 of 40 because it is the LAST first-match-wins rule, and all 40
    #: sitting at two of `reel_story`'s six stages because `_stage_of(tag)` reads the RETENTION
    #: TAG. ⚠ IT GUARDS THE ROUTING, NOT THE READING: nothing here arms a paid sweep, and the
    #: queue this publishes is consumed by nobody. `prune.arm` guards whether the prune may act;
    #: this guards whether the keep-reason may decide a reel's read-fate. Different failures.
    "reel.route": {
        "surface": "THE RIVER",
        "acts": "decides where each reel is, and therefore what it is owed",
        "bar": 0.510, "kinds_bar": 1.0, "after": [],
    },
    "prune.reports": {
        "surface": "THE RIVER",
        "acts": "tells him how much space was freed",
        "bar": 0.510, "kinds_bar": 1.0, "after": [],
    },
    "vault.forget": {
        "surface": "VAULT", "acts": "drops the ledger",
        "destructive": True,   # there is nothing to drop it back from
        "bar": 0.722, "kinds_bar": 1.3, "after": ["vault.sweep_start"],
        "unprovable": ("the door has no refusal path by design — clearing a rebuildable "
                       "optimisation is a button, and gating it would be a cage. There is no "
                       "state in which it must refuse, so sabotage cannot produce evidence in "
                       "either direction"),
        "unprovable_fn": "vault_forget",
    },
    # step 1 — MINI AUTO. His ruling, 2026-09-02: "i want it not enforced... i want it BADGED...
    # my point was i want it KNOWN on the console is all", with "a logical coding to it with wilson
    # via connected to the heart for real".
    # ⚠ SO THIS LOCK IS A STAMP, NOT A GATE — nothing calls may("miniauto.run") to block the
    # button, and that is deliberate rather than unfinished. It still earns its state the same way
    # every other lock does, so the console can say what has been proven instead of staying silent.
    # It sits at step 1 because MINI AUTO drives the pointer over his stash and films what the game
    # draws: it is the printer and the reels, which is where he said Wilson starts.
    "miniauto.run": {
        "surface": "MINI AUTO", "acts": "moves the pointer over his stash and films the tooltips",
        "bar": 0.510, "kinds_bar": 1.0, "after": [],
    },
    # step 4 — the deleter. Last, and it cannot be reached early.
    # ⚠⚠ v2721 — THE GATE BETWEEN A SEAL AND A DELETION, AND IT HAD NO LOCK.
    # `frame_authority.seal_releases_frames` decides, per FRAME, whether pixels may go. It is not
    # `prune.arm` ("may the prune RUN") and it is not `vault.apply` (the write door) — it is the
    # per-frame release authority, and frame-vs-reel granularity is exactly the distinction v2314
    # refused to collapse. Konyo's 2026-09-06 ruling made it decide real reels for the first time
    # (examined-empty releases; a bare "nothing was taken" does not), which is when an authority
    # earns a lock.
    #
    # It went unbanked because it had nowhere HONEST to go: seven genuine sabotages against it
    # would have had to be filed under a lock whose subject they do not attack — the counter-moving
    # `_hardening_gap` warns about in its own docstring. Declaring the lock is the honest
    # alternative to mis-filing real evidence. [[join-gate-heart]]
    #
    # BAR 0.722 / KINDS 1.3 — the write-door class (vault.apply), not the deleter class. It
    # AUTHORISES an irreversible act without performing one, and prune.arm still stands between it
    # and any byte being removed.
    "frame.release": {
        "surface": "THE RIVER",
        "acts": "decides whether a frame's pixels may be released — the last check before deletion",
        "destructive": True,   # it is the last check before deletion
        "bar": 0.722, "kinds_bar": 1.3, "after": [],
    },
    # ⚠⚠ v2784 — HIS RULING, 2026-09-08: *"if they are hardened and tested and prove themselves
    # to work is this a good place for a hardening and wilson to connect to the heart of the
    # console specifically #34"*. Yes — and this is the whole of #34's remaining half.
    #
    # THE STATE BEFORE THIS. The pixel witness REPORTS (`_pixel_blank_report` runs inside the
    # rescue loop every 6 ticks and writes a fault row) and it POST-GRADES (`rescue_worked` says
    # whether a rescue restored painting). What it may not do is TRIGGER: the rescue fires on
    # `due`, a beat/time condition read from the PAGE. And a blank page can still beat — which is
    # the exact failure mode `paint_witness`'s own docstring names, and the exact state he was
    # looking at on 2026-09-08 when his window was black and the hover art was still painting.
    #
    # ⛔ THE BAR IS THE STRICTEST ONE ON THE BOARD, equal to the deleter, and deliberately so. A
    # wrong BLANK does not lose footage — it REPLACES THE WINDOW HE IS LOOKING AT, mid-use. His
    # standing rule is that nothing auto-heals until it has proven itself, so it was DECLARED SHUT
    # and left to earn its way open. ⚠ ASK `may("console.pixel_rescue")` FOR THE STATE — do not
    # read it out of this paragraph. Shut at v2784; open on 2026-09-18 after 32 of 32 distinct
    # attacks were refused (wilson 0.893 >= 0.839, kinds 2.50 >= 1.80), with nobody editing a file
    # to move it. While it is shut the rescue loop keeps firing on `due` exactly as it did, and
    # NOTHING CHANGES until the witness has survived the attacks. That is the point of declaring
    # it rather than wiring it. [[unknown-stays-unknown]] [[REG-1133]]
    #
    # ⚠ THREE PROVERS, because one kind can never open it (kinds_bar 1.8). The families are chosen
    # to fail DIFFERENTLY: synthetic distributions built to fool the arithmetic, his real window
    # through the real window server, and a different model family judging the same bitmaps. A
    # single family agreeing with itself is the "wall of agreements" this module exists to refuse.
    "console.pixel_rescue": {
        "surface": "THE CONSOLE", "acts": "lets a PIXEL verdict trigger a rescue of his window",
        "bar": 0.839, "kinds_bar": 1.8, "after": [],
    },
}

#: ⚠⚠ RETIRED LOCKS — A REMOVED CEREMONY'S BANKED ROWS MUST STILL READ.
#:
#: HIS RULING, 2026-09-19: *"leave it off and surgically remove it we need pruning"*. `prune.arm`
#: is gone from LOCKS, its harness (`prune_wilson.py`) is deleted and its gate is de-registered —
#: that is the removal, and it is complete. This map is the other half.
#:
#: ⚠⚠ MEASURED, AND IT IS WHY THIS EXISTS. His live ledger holds **19 rows** banked by
#: `prune_wilson` against `prune.arm` (a real sabotage record, n=18/k=18 on the newest). Deleting
#: the PROVES declaration does not delete them — it makes `_row_fault` reject one row, `_rows()`
#: return None, and **every one of the NINE surviving locks fail CLOSED** with "an unreadable
#: proof queue fails CLOSED". Measured on all four sampled: vault.apply, miniauto.run,
#: prune.reports, reel.route. His ruling ends "keep self_arming for other surfaces"; un-declaring
#: the source does the exact opposite of that, for every surface at once.
#:
#: RETIRED means READABLE, NEVER BANKABLE, and the second half needs no new code: `bank()` already
#: refuses any lock absent from LOCKS — verified, `bank("prune.arm", …)` → *"no such lock or
#: route is declared"*. So the door is shut by the removal itself, and this map only keeps the
#: testimony legible. [[manual-tally-is-witness]] — once witnessed, never un-witnessed.
RETIRED_LOCKS = {
    "prune.arm": "removed 2026-09-19 by his ruling; pruning is gated by _PRUNE_SAFE_TO_RUN, which "
                 "is untouched at 53 sites and is the actual safety",
}

#: ⚠⚠ THE ROUTES, ON THE SAME ARITHMETIC. His ruling: "each of the locked routes needs that same
#: unified logic for wilson score and that same lock/unlock prove themselves style ... and all
#: connected to the heart of the console obviously".
#:
#: A VALVE earns permission to ACT — it deletes footage, it mules items. A ROUTE only REPORTS, so
#: what it can earn is trust in the NUMBER IT PRINTS, not a licence. Same Wilson lower bound, same
#: kinds/confluence bars, same self-proving flip with nothing hand-set; the earned word is PROVEN
#: rather than OPEN. Keeping them in ONE table and ONE score() is the whole point — a second
#: implementation of this arithmetic would drift from the first within a week. [[copy-drift]]
#:
#: The bars are LOWER than a valve's on purpose: being wrong about a printed number is recoverable
#: and being wrong about the deleter is not. One kind of look is enough to trust a count.
ROUTES = {}
for _set, _keys in (("chronicle", ("runeword", "set", "unique")),
                    ("fleet", ("runewords", "sets", "uniques")),
                    ("roster", ("runeword", "set", "unique"))):
    for _k in _keys:
        ROUTES["%s.%s" % (_set, _k)] = {
            "surface": _set.upper(),
            "acts": "reports the %s count on the %s route" % (_k, _set),
            "bar": 0.510, "kinds_bar": 1.0, "after": [],
        }

# the four states, and they are four on purpose
#: ⚠⚠ A TIER ABOVE MERELY-PROVEN. His ruling: "is there a way for the confluence there to like
#: surpass the defaulted or standard proven state ... is there a HARD MODE for this".
#:
#: Clearing a bar is a floor, not a ceiling, and a surface that stops at the floor looks identical
#: to one that could not do better. HARDENED is what a surface earns by continuing: a much higher
#: Wilson lower bound AND evidence from genuinely INDEPENDENT kinds. The confluence axis is the
#: one that matters here — Wilson counts how many looks agreed, never whether they were the same
#: look repeated, so more attempts of one kind can reach 0.95 while proving only that one
#: instrument keeps agreeing with itself. The maximum confluence is 3.40 (all five kinds).
#:
#: It is EARNED the same way everything else here is: derived from the ledger, never assigned.
# ⚠⚠ v2745 — WHAT THIS NUMBER ACTUALLY IS, BECAUSE IT READS AS SOMETHING ELSE AND MISLED ME.
# A cross-family audit (t30) attacked it and was RIGHT. MEASURED in tv/.self_arming.jsonl:
#     149 banked rows · rows where an attack FAILED (k < n): **6**
#     and all six are prune.reports k=0/n=8, the REG-600 case
# So for 143 of 149 rows k == n, and `wilson_lower(n, n)` reduces exactly to n / (n + z^2). The
# score is therefore a MONOTONE FUNCTION OF n — a COUNT OF DISTINCT ATTACKS, not a success rate
# and not a confidence. HARD_BAR = 0.900 means, in practice, "at least 35 distinct attacks, all
# currently answered".
#
# ⚖ THAT IS NOT NOTHING, AND THE COUNTER-EVIDENCE MATTERS: of the 17 attacks added for reel.route,
# NINE LANDED — they failed against the code as it stood and found real defects in one_funnel.py.
# So the harness demonstrably CAN produce contrary examples; attacks are not written to pass. The
# sequence is: attack fails -> THE CODE is fixed -> k = n. That is a working ratchet.
#
# ⇒ SAY IT THIS WAY AND IT IS TRUE: "N distinct attacks exist against this surface, every one is
# currently answered, across K independent kinds of witness." Saying "90.4% confident" is not.
# [[zero-needs-a-denominator]] [[feedback-suspect-the-instrument]]
HARD_BAR = 0.900        #: the Wilson lower bound a HARDENED surface must clear
HARD_KINDS_BAR = 2.50   #: needs three genuinely different kinds — e.g. sabotage+cross-family+live

HARDENED = "HARDENED"
OPEN = "OPEN"
LOCKED = "LOCKED"          # proven, and it did not clear the bar
UNPROVEN = "UNPROVEN"      # n == 0 — nobody has tested it. NOT a failure, NOT a score.
#: ⚠⚠ A CLAIM THAT COULD NOT RUN IS NOT AN ABSENT CLAIM. A harness that banks a claim with n=0 and
#: a stated reason has declared an axis and then failed to exercise it — and because zero attempts
#: cannot move a Wilson bound, that failure was INVISIBLE: the lock scored on its other claims and
#: reported OPEN.
#:
#: HIS CATCH, 2026-09-04, and it is the sharpest one yet: *"miniauto.run … absolutely has not been
#: proven or done yet … its not working at all what do you mean? it should be locked as hell!"*
#: He is right, and the harness's own words say why. `hover_wilson.probe_anchor` banks n=0 because
#: `anchor_from_tooltip_rect` refuses: *"no tooltip->cell OFFSET has been calibrated, so the anchor
#: would be the tip's own corner and EVERY ITEM WOULD LAND IN WHICHEVER CELL THE TEXT COVERS."*
#: That is a precise description of MINI AUTO not working — and the lock over it read **OPEN, 55 of
#: 55 refused**, because the one probe that tests the broken thing contributed nothing.
#:
#: So an unexercised axis holds the lock instead of disappearing from it. This is a REPORT, not a
#: gate: `may()` is still never called and nothing is blocked. [[unknown-stays-unknown]]
INCOMPLETE = "INCOMPLETE"  # a declared claim banked n == 0 — an axis nobody could exercise
UNKNOWN = "UNKNOWN"        # the ledger could not be read. Fails closed, and says so.


def record(lock, kind, refused, note="", src=None):
    """Append one SABOTAGE ATTEMPT and whether the guard refused. -> dict (the row written)

    `refused` True means the guard went RED for its own reason — that is the SUCCESS here, which
    reads backwards until you remember what is being measured: the ability to say no.

    ⚠⚠ REG-591 — THIS DOOR HAD NO ALLOW-LIST, AND IT IS THE ONE RULE THAT MATTERS MOST HERE.
    `bank()` refuses any (src, lock) pair PROVES does not declare — that is what stops one
    surface's sabotage opening a DIFFERENT surface's lock, and it matters most for `prune.arm`,
    because footage has no undo. `record()` took no `src` at all, so a single call could credit
    ANY lock from anywhere, and nothing downstream could tell where the evidence came from.

    MEASURED when this was found (fixing REG-575): `record()` has **ZERO production callers** and
    his live ledger holds **51 bank-shaped rows and 0 record-shaped**. So this was never a leak —
    it was a loaded gun, and the first caller added would have fired it. Closing the writer is
    cheap precisely because nobody uses it yet.

    ⚠ THE READER IS DELIBERATELY UNCHANGED. `_row_fault` still accepts a src-less row, because
    historical rows and `test_self_arming`'s own `put()` helper write that shape directly, and
    rejecting them would fail the whole read — the exact defect REG-575 was. The hole is closed at
    the door where new evidence is created, not by refusing evidence that already exists.
    [[unknown-stays-unknown]]
    """
    src = str(src or "").strip()
    if not src:
        raise ValueError(
            "record() needs a `src`: which harness produced this attempt. Without one the row "
            "could credit any lock from anywhere, which is what the PROVES allow-list exists to "
            "prevent. Use bank() if you have counts; pass src= if you have a single attempt.")
    allowed = PROVES.get(src)
    if allowed is None:
        raise ValueError("src %r is not a declared evidence source (PROVES)" % src)
    if str(lock) not in allowed:
        raise ValueError("%r does not prove %r — PROVES declares it for %s"
                         % (src, lock, ", ".join(allowed) or "nothing"))
    row = {
        "lock": str(lock), "kind": str(kind), "refused": bool(refused), "src": src,
        "note": str(note or "")[:400], "ts": int(time.time() * 1000),
    }
    # #181 (REG-2470) - a LIVE attempt is a fact about THIS PC, so it never enters the shared (tracked) queue
    if _is_per_pc(row):  # PER-PC-ROUTE
        return _append_here(row)
    with io.open(_bank_path(), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


# ── WHERE EACH HARNESS'S EVIDENCE IS ALLOWED TO LAND ─────────────────────────────────────────
# v2444 — AN ALLOW-LIST, BECAUSE THE FAILURE IT PREVENTS IS THE WORST ONE AVAILABLE HERE. A
# sabotage against the render gate proves THE RENDER GATE. It is real evidence and it says nothing
# whatever about whether the vault may mule an item or whether footage may be deleted. Banking it
# under prune.arm would let the deleter open itself on somebody else's proof, and footage has no
# undo. So a source declares what it bears on, and bank() refuses everything else.
#
# A source that proves NOTHING declared here is listed with an empty tuple ON PURPOSE — that is a
# statement that its evidence has no lock, not an oversight, and it keeps the next person from
# quietly wiring it to whichever lock happens to be nearby.
PROVES = {
    # hover_wilson scores the autopilot's four claims on real sabotage attempts, and the autopilot
    # IS mini-auto: "moves the pointer over his stash and films the tooltips". Same surface, same
    # guards, same three-state vocabulary (UNPROVEN / PROVEN / LEAKS).
    "hover_wilson": ("miniauto.run",),
    # render_check proves that the RENDER GATE can be seen red. There is no render lock, and there
    # should not be one — nothing it sabotages can delete footage or touch his ledger.
    "render_check": (),
    # A2 step 1 — "the printer and the reels", which is this table's own label for
    # vault.sweep_start. sweep_wilson attempts states in which chronicle_sweep_start MUST refuse
    # (a sweep already running; no lane to read with) and counts whether it did. It never starts a
    # sweep: there is no attempt in it whose success path runs, because the door it guards spends
    # money.
    "sweep_wilson": ("vault.sweep_start",),
    "sweep_live": ("vault.sweep_start",),
    #: 154 — the disk row's own refusals. It NEVER prunes: every attempt is a state in which the
    #: row must decline to name a freed figure, and nothing here deletes a byte.
    "disk_report_wilson": ("prune.reports",),
    # The same reporter, read off his real disk_history series. One check over every
    # numeric row, so it is one attack however many rows the series holds.
    "disk_report_live": ("prune.reports",),
    # ⚠ THE SECOND KIND for prune.reports — attacks a different model family designed COLD, three
    # of which LANDED and were all mine (negative zero past a `< 0` check; a flat +1 MB tolerance
    # licensing 0.9 MB against a 0-byte corpus and 2.0 MB against a 1 MiB one). Confluence only
    # moves on independent kinds; five more sabotages of mine would be one instrument in a new hat.
    "disk_report_crossfamily": ("prune.reports",),
    #: A7·ROUTE — seven refusals the router must make, each a way the keep-reason could creep back
    #: into the read-fate or an unmeasured reel could be dressed as a measured one. It reads no
    #: footage, arms no sweep and deletes nothing.
    "reel_router_wilson": ("reel.route",),
    # v2725 — the OTHER half of "where is this reel". reel_router_wilson attacks the routing
    # decision; this attacks whether the accounting can admit it cannot establish a rung at all.
    # Both bear on reel.route and neither bears on anything else.
    "rung_accounting_wilson": ("reel.route",),
    # v2727 — the LIVE half of the same subject. Three coherence checks over his real shelf; it
    # returns UNKNOWN where there are no reels, so it cannot bank a clean zero on CI.
    "rung_accounting_live": ("reel.route",),
    # v2728 — the CROSS-FAMILY half. A different model family (xai/grok) handed the real decision
    # code and told to REFUTE six named claims. Banked as attacks=1: it reported seven probes, but
    # an LLM's self-reported breadth is not verifiable breadth, and the value here is the KIND.
    "rung_accounting_xfam": ("reel.route",),
    #: A2·HARD — attacks on the vault WRITE door designed by a DIFFERENT model family, which is
    #: the third evidence KIND `vault.apply` needed and the only one available without spending
    #: his money. Two of the three found a real hole (an uncorroborated row under `unsure` reached
    #: the write path without the gate being asked); the third was refuted and is banked anyway so
    #: the tried-and-failed axis is on the record. Safe by construction: every attempt carries
    #: evidence that cannot clear the gate, so the only outcome the door can produce is a refusal.
    "vault_apply_crossfamily": ("vault.apply",),
    # vault_wilson attempts proposals the WRITE door must reject — v1595's re-gate, which
    # returns before the board is ever asked. It never applies anything: every row it hands
    # in carries an empty evidence list, so it fails the witness gate by construction.
    # ⚠ It is declared for vault.apply ONLY. vault.forget has no refusal path at all (7
    # lines, one return, always ok), so nothing can prove it by sabotage and nothing here
    # pretends to.
    "vault_wilson": ("vault.apply",),
    # printer_wilson removes each owner's ability to answer and requires the printer to say
    # UNKNOWN **with a reason** rather than guess, skip the station, or drop the reel. It calls
    # exactly one function, printer.stream(), whose own docstring is "IT PRINTS NOTHING AND
    # DELETES NOTHING ... This is a REPORT." No os.remove, no apply_plan, no TV_AUTO_PRUNE.
    "printer_wilson": ("printer.stream",),
    "printer_live": ("printer.stream",),
    # the same refusal asked of the RUNNING console over its own HTTP route — a different
    # KIND, not a second helping of the same one. vault.apply carries kinds_bar 1.3 exactly
    # so that one kind cannot open it.
    "vault_live": ("vault.apply",),
    # A2 step 4 — the deleter. prune_wilson attempts states in which retention_may_act() MUST
    # refuse: every spelling of OFF (v2082's scar, where only the byte "0" held and every other
    # spelling armed an unattended deleter), an unconfirmed board world, a world check that
    # raises, and a drift answer of the wrong shape. It calls exactly one function, whose own
    # docstring is "Decides; never acts" — there is no path in it that deletes a byte, and
    # tv/test_prune_wilson.py asserts that from the source.
    # ⚠ It is declared for prune.arm ONLY, and even a perfect record cannot open that lock:
    # kinds_bar is 1.8 and sabotage weighs 1.0. The door with no undo does not open on one kind
    # of look, which is the point of the bar rather than a gap in this harness.
    # ⚠ v2784 — three families for console.pixel_rescue. An allow-list entry is not evidence; it
    # only says whose evidence would COUNT. Until a harness banks under one of these the lock is
    # UNPROVEN, which is not the same as failing and is not the same as permitted.
    "pixel_witness_wilson": ("console.pixel_rescue",),
    "pixel_witness_live": ("console.pixel_rescue",),
    "pixel_witness_crossfamily": ("console.pixel_rescue",),
    # ⚠ RETIRED, AND DELIBERATELY STILL HERE. prune.arm is no longer a lock and prune_wilson.py
    # is deleted, so nothing can bank through this pair ever again — bank() refuses a lock absent
    # from LOCKS. It stays declared so the 19 rows already in his ledger READ; dropping it fails
    # all nine surviving locks CLOSED. See RETIRED_LOCKS.
    "prune_wilson": ("prune.arm",),
    # v2721 — frame_release_wilson attacks `frame_authority.seal_releases_frames` in states where
    # it MUST refuse: a seal that never looked, one saying only "nothing was taken", one whose
    # examinedEmpty is falsy rather than declared. It deletes nothing and arms nothing — it calls
    # one pure predicate and counts refusals.
    "frame_release_wilson": ("frame.release",),
    "frame_release_live": ("frame.release",),
    "frame_release_xfam": ("frame.release",),
    # ⚠ THE ROUTES. route_wilson removes what each lane CLAIMS TO HAVE FOUND — deletes the
    # artifact, deletes bible.html, blanks every mention of the roster stem, removes the file a
    # lane names — and counts whether the lane noticed. A lane that still says ok with its
    # evidence gone was decorative. It proves ONLY the routes, never a valve: evidence about a
    # thing that reports may not open a door that acts.
    "route_wilson": tuple(sorted(ROUTES)),
    # Lane predicates attacked directly — the same functions routes() calls — so a
    # mutation is one idea about one guard, not another copy of "delete the file".
    "route_lane_wilson": tuple(sorted(ROUTES)),
    "route_lane_live": tuple(sorted(ROUTES)),
    # A recorded Claude verdict. The module refuses to bank unless the verdict file is a
    # real answer from that family — an auth error or an empty file writes nothing.
    "crossfamily_claude": (
        "frame.release", "printer.stream", "vault.sweep_start",
    ) + tuple(sorted(ROUTES)),
}


def withdraw(lock, kind, src, ref, why, prove_absent=False):
    """Retire one banked AXIS whose evidence was never about the lock. -> dict (the row written)

    ⚠⚠ WHY THIS HAD TO EXIST, MEASURED 2026-09-05. `_fold` keys on (lock, kind, src, ref) and keeps
    the NEWEST row per key. So rewriting a harness's attacks retires an axis only when the new axis
    reuses the old REF NAME. `disk_report_wilson`'s four corrected attacks are named
    notanumber/notfinite/negative/overcorpus; the three REG-600 axes they replaced were named
    noprune/unreadable/shrank. Nothing superseded those, so **`prune.reports` read n=56 — 32 real
    refusals PLUS the 24 identity assertions the rewrite existed to remove.**

    That is worse than not having fixed it: the lock LOOKS repaired while three-eighths of its
    evidence is still an event that could not fail, and the mixture is invisible in the total.

    ⚠ NOTHING IS DELETED. The ledger stays append-only — this appends a row that supersedes the
    axis with `n=0, k=0`, so it contributes nothing to any score while the original row and this
    retraction both remain on the record. A withdrawal you cannot read is a deletion with a nicer
    name. [[unknown-stays-unknown]]

    ⚠ A REASON IS REQUIRED. An axis retired with no stated reason is indistinguishable from one
    quietly dropped because it was inconvenient.
    """
    if not str(why or "").strip():
        raise ValueError("a withdrawal needs a REASON. An axis retired without one cannot be told "
                         "apart from evidence quietly dropped because it was inconvenient.")
    if not str(ref or "").strip():
        raise ValueError("a withdrawal needs the REF of the axis it retires — that is the fold key,"
                         " and without it this appends a new empty axis instead of superseding one")
    # ⚠⚠ IT MUST ACTUALLY RETIRE SOMETHING, AND v2647's CUT DID NOT CHECK. `_fold` keys on
    # (lock, kind, src, ref), so a withdrawal filed under the wrong KIND or a mistyped REF matches
    # no row, supersedes nothing, and still lands in `withdrawnClaims` — the report then NAMES a
    # retraction that did nothing. Measured 2026-09-05 by a review of the shipped bytes: filing
    # `noprune` under kind='cross-family' left the axis at 24/24 and still printed it as withdrawn.
    # This function's own ValueError above describes that outcome and did not prevent it.
    # ⚠ `_rows()` returns (list|None, why) — None means UNREADABLE, which is never "no proofs".
    # An unreadable ledger must REFUSE the withdrawal rather than read as "nothing to retire",
    # because that would let a corrupt file license a retraction of something still standing.
    _all, _rwhy = _rows()
    if _all is None:
        raise ValueError("the proof ledger could not be read (%s), so whether this axis exists is "
                         "UNKNOWN — and unknown is not permission to retire it" % (_rwhy or "?"))
    _prior = [r for r in _fold(_all)
              if r.get("lock") == str(lock) and r.get("kind") == str(kind)
              and r.get("src") == str(src) and (r.get("ref") or "") == str(ref)
              and not r.get("withdrawn")]
    if not prove_absent and not _prior:
        raise ValueError(
            "no banked axis matches (lock=%r kind=%r src=%r ref=%r), so this withdrawal would "
            "supersede NOTHING while still being reported as a retraction. Check the KIND — a "
            "sabotage axis filed under cross-family is the shape that bit here. Pass "
            "prove_absent=True only when retiring an axis you have separately established is gone."
            % (lock, kind, src, ref))
    # ⚠⚠ AND IT MUST SAY WHAT IT REMOVED, because a withdrawal CAN RAISE THE SCORE and nothing
    # said so. Measured on the shipped bytes: retiring a failing axis (2 of 8 refused) took
    # `prune.reports` from wilson 0.7093 to 0.8928 — **+0.18 by deleting six failures from the
    # arithmetic**. That is legitimate when the axis was invalid, and indistinguishable from
    # laundering when nothing records what left. `withdrewN`/`withdrewK` are the record.
    _n = sum(int(r.get("n") or 0) for r in _prior)
    _k = sum(int(r.get("k") or 0) for r in _prior)
    row = bank(lock, kind, src, n=0, k=0, ref=ref, attacks=0, withdrawn=True,
               note="WITHDRAWN (removed %d/%d) — %s" % (_k, _n, str(why)[:320]))
    row["withdrewN"], row["withdrewK"] = _n, _k
    return row


def bank(lock, kind, src, n, k, note="", ref="", attacks=None, withdrawn=False):
    """Bank a harness's OWN aggregate for one lock. -> dict (the row written)

    Idempotent by construction: the row carries `src`, and _fold keeps only the newest row per
    (lock, kind, src). Running the harness twice does not make the evidence twice as strong.

    ⚠ IT REFUSES RATHER THAN GUESSES, in three directions, because every one of them ends with a
    lock opening on evidence that was never about it:
      · an undeclared source, or a lock that source does not prove -> refuse
      · k > n -> refuse; more refusals than attempts is an instrument fault, not a great result
      · a lock that is not declared -> refuse
    [[unknown-stays-unknown]] [[feedback-suspect-the-instrument]]
    """
    if lock not in LOCKS and lock not in ROUTES:
        raise ValueError("no such lock or route is declared: %r" % (lock,))
    allowed = PROVES.get(str(src))
    if allowed is None:
        raise ValueError("%r is not a declared evidence source. Add it to PROVES and say what its "
                         "sabotages actually bear on — an undeclared source is how a lock opens on "
                         "somebody else's proof." % (src,))
    if lock not in allowed:
        raise ValueError("%r does not prove %r. It is declared as proving %s. Evidence about one "
                         "surface is not evidence about another, and this refusal is the whole "
                         "point of the allow-list." % (src, lock, allowed or "NOTHING"))
    # ⚠ AN UNDECLARED KIND IS A SILENT STOP, WHICH IS WORSE THAN A LOUD ONE. `kind` is the TIER
    # confluence() weighs, not a free label — KINDS maps sabotage 1.0 / cross-family 0.8 / live 0.7
    # / ci 0.6 / fixture 0.3. An unrecognised tier scores 0.00, so the lock stays shut FOREVER while
    # its Wilson figure reads 0.935 and every number on the page looks healthy. Measured here on the
    # first real run: banking the four hover claims under their own names gave kinds ['coordinate',
    # 'read', 'slot'] scoring 0.00 against a bar of 1.00. Refusing beats a lock nobody can explain.
    if str(kind) not in KINDS:
        raise ValueError("%r is not a declared evidence tier. confluence() weighs KINDS (%s), and "
                         "an unrecognised kind scores 0.00 — the lock would stay shut for ever with "
                         "a healthy-looking Wilson score and no reason on screen."
                         % (kind, ", ".join(sorted(KINDS))))
    n = int(n or 0)
    k = int(k or 0)
    if n < 0 or k < 0 or k > n:
        raise ValueError("k=%d of n=%d is not a possible sabotage record — more refusals than "
                         "attempts is an instrument fault" % (k, n))
    # ⚠ v3487's second eye: more DISTINCT attacks than attempts is the same instrument fault one field
    # over. n == 0 stays legal (an axis declared and unable to run banks attacks=1, n=0 — no evidence).
    if attacks is not None and n > 0 and int(attacks) > n:
        raise ValueError("attacks=%d over n=%d attempts is not a possible record — a distinct attack "
                         "needs at least one attempt" % (int(attacks), n))
    row = {
        "lock": str(lock), "kind": str(kind), "src": str(src), "ref": str(ref or ""),
        "n": n, "k": k, "refused": bool(k > 0),
        # ⚠⚠ HOW MANY DISTINCT SABOTAGES ARE BEHIND THOSE n TRIALS — the number that stops a score
        # being bought by repetition. Wilson tightens with n and has no way to know whether n is
        # 83 independent looks or ONE attack applied 83 times, so it must be told.
        # MEASURED 2026-09-04, and it is why this field exists: `printer.stream` banked 83/83 for
        # wilson 0.9558, and 80 of those 83 were TWO attack functions applied to 40 reels each.
        # Counted as the five distinct attacks it actually runs, the same evidence scores 0.5655
        # — barely over its 0.510 bar. Nothing was faked and every refusal was real; the SCORE was
        # inflated by looping. `None` means the harness did not say, which is not the same as one.
        "attacks": (None if attacks is None else int(attacks)),
        # ⚠⚠ A RETIRED AXIS IS NOT AN UNRUNNABLE ONE, and the report read them identically until
        # v2647. Both bank n == 0; only this field separates "I own this axis and could not run
        # it" from "this axis was exercised, found to prove nothing, and withdrawn". Reporting a
        # withdrawal as INCOMPLETE puts a true sentence under the wrong word.
        # [[label-outlived-referent]] [[unknown-stays-unknown]]
        "withdrawn": bool(withdrawn),
        "note": str(note or "")[:400], "ts": int(time.time() * 1000),
    }
    # ⚠⚠ #181 (REG-2470) - A LIVE TRIAL IS A FACT ABOUT THE PC THAT RAN IT. Banked into the shared (tracked) queue
    # it shipped to every PC and scored there as that PC's own: Dean's heart read the Mac's 50 seals as his. It goes
    # to THIS PC's gitignored ledger; every other kind is a property of the code and stays shared.
    if _is_per_pc(row):  # PER-PC-ROUTE
        return _append_here(row)
    with io.open(_bank_path(), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def _fold(rows):
    """Reduce banked AGGREGATES to one row per (lock, kind, src, ref), newest wins. -> list

    Single-attempt rows are never folded — each one is its own event and they accumulate, which
    is what record() means.

    ⚠⚠ v2612 — THIS KEYED ON `src` AND THAT STOPPED BEING THE RIGHT QUESTION. `record()` took no
    src until REG-591 closed the allow-list bypass at its door; the moment single events grew one,
    three separate attempts folded into ONE and the count read (0, 1) instead of (2, 3). The test
    that caught it says the rule in its own name: *record() rows are events and must keep adding
    up; only banked aggregates fold.*

    What makes a row foldable is that it is an AGGREGATE — a harness re-reporting its own running
    total, where the newest reading replaces the older. An EVENT is not a re-report of anything.
    Key on that and a src can be added to either writer without silently eating evidence.
    """
    out, latest = [], {}
    for r in rows:
        src = r.get("src")
        if not src or not (("n" in r) or ("k" in r)):
            out.append(r)
            continue
        # ⚠ ref IS PART OF THE KEY, and leaving it out cost three of four claims on the first
        # real run. The four hover claims are all `sabotage` tier, so (lock, kind, src) is the SAME
        # key for all of them — folding on that kept only the last one written and threw away
        # coordinate's 48/48, keeping slot's 2/2. n fell from 55 to 2 and nothing said so.
        key = (r.get("lock"), r.get("kind"), src, r.get("ref") or "")
        cur = latest.get(key)
        if cur is None or int(r.get("ts", 0) or 0) >= int(cur.get("ts", 0) or 0):
            latest[key] = r
    out.extend(latest.values())
    return out


def _row_fault(r):
    """Why this row could not have come from ANY writer in this module. -> str ("" when sound)

    ⚠ EVERY CHECK HERE IS ONE bank() ALREADY MAKES (self_arming.py, bank). It is not a second
    opinion — a second copy of a safety rule is [[copy-drift]]'s worst case. It is the SAME rules
    asked on the read side, because bank() guards its own door and nothing guarded the file.

    ⚠⚠ REG-575 — IT ONLY KNEW ONE OF THIS MODULE'S TWO WRITERS, AND FAILED THE WHOLE FILE ON THE
    OTHER. v2581 wrote this against bank()'s shape alone. `record()` — the single-attempt writer,
    documented in score() as *"everything record() has ever written"* — emits
    `{lock, kind, refused, ts}` with **no `src` and no `n`/`k`**, so every row it has ever produced
    was judged "src '' is not a declared evidence source". One bad row fails the entire read by
    design, so a single `record()` call would have turned all fifteen locks UNKNOWN at once.

    MEASURED 2026-09-04: `record()` has ZERO production callers and his live ledger holds 51
    bank() rows and 0 record() rows, so it never fired on his console — but `test_self_arming`
    (a REGISTERED gate) went red the version this shipped and stayed red. **A validator that
    rejects rows its own module writes is not strict, it is wrong**, and the gate said so.

    ⚠ SO IT JUDGES A ROW AGAINST THE SHAPE IT DECLARES. A row carrying `src` is a bank() row and
    gets every bank() rule. A row without one is a record() row and gets the rules that APPLY to
    it — never the three that cannot. Silently passing a record() row through the bank() checks
    would be the same defect wearing the opposite coat.

    ⚠ AND THE ASYMMETRY IS REAL, NOT RESOLVED HERE: a record() row carries no `src`, so the PROVES
    allow-list — the rule stopping one surface's proof from opening another's lock — cannot be
    applied to it at all. That was true before this function existed and is not made worse by it.
    It is safe TODAY only because record() has no callers; the moment one is added, a proof could
    land on any lock. Named in TASKS.md rather than left for someone to find. [[the-unjoined-end]]
    """
    lock, kind = str(r.get("lock") or ""), str(r.get("kind") or "")
    # ⚠⚠ THE DISCRIMINATOR IS AGGREGATE-vs-EVENT, NOT src, AND THAT DISTINCTION COST A SECOND
    # ROUND OF REG-575. It keyed on `"src" in r` — correct only while `record()` wrote no src.
    # v2612 gave record() a src to close the allow-list bypass, every single-event row grew one,
    # this branch judged them as bank() rows, demanded the `n`/`k` they never have, and the whole
    # read failed CLOSED again — all fifteen locks UNKNOWN, exactly the defect REG-575 was.
    # Caught by `test_single_attempts_still_ACCUMULATE_and_mix_with_aggregates`, which read
    # (None, None) instead of (2, 3).
    #
    # What actually separates the two writers is what they CARRY: `bank()` writes counts, and
    # `record()` writes one outcome. Key on that and a src can be added to either without
    # re-breaking the reader.
    _is_aggregate = ("n" in r) or ("k" in r)
    if "src" in r:
        src = str(r.get("src") or "")
        allowed = PROVES.get(src)
        if allowed is None:
            # ⚠⚠ AN UNRECOGNISED SOURCE IS NOT A FORGED ROW WHEN THIS PROCESS'S REGISTRY IS OLD.
            # MEASURED 2026-09-05: his console booted at 08:43 and ran that image for sixteen
            # hours. `reel_router_wilson` was declared in PROVES on disk and its rows appended to
            # the ledger; the running console did not recognise the source and published
            # ".self_arming.jsonl has a row that could not have been banked" — a definite
            # accusation of forgery against a row that was banked correctly. Read under the code
            # on disk the same ledger is clean (reel.route OPEN, 56/56).
            #
            # His ask, three times: *"stale in-memory so for this a safeguard on it? just like we
            # have regression watchdog?"* This is it. "I do not know this source" and "this source
            # may not exist" are different facts, and which one applies depends entirely on
            # whether THIS process's PROVES can be trusted to be complete.
            # [[unknown-stays-unknown]] [[stale-reading]]
            try:
                import code_staleness as _CS
                if _CS.registry_may_be_incomplete("self_arming"):
                    return ("src %r is not in THIS PROCESS's PROVES, and this process is running "
                            "an older self_arming than the one on disk — so whether the row is "
                            "legitimate is UNKNOWN, not refused. Relaunch to judge it." % src)
            except Exception:
                pass
            return "src %r is not a declared evidence source" % src
        if lock not in allowed:
            return "%r does not prove %r" % (src, lock)
    if not _is_aggregate:
        # a single attempt: its outcome is in `refused`. score() reads it as n=1.
        if not isinstance(r.get("refused"), bool):
            return ("refused=%r is not a boolean, and score() would have read it as an outcome "
                    "anyway" % r.get("refused"))
    elif "src" not in r:
        return ("a row carries n/k with no src, so nothing declares what it may prove and score() "
                "would still count it")
    if _is_aggregate and kind not in KINDS:
        # ⚠ ON BANK() ROWS ONLY, and that is not a softening. bank() validates the kind at its own
        # door, so an undeclared kind in a row claiming a src could not have come from it. A
        # record() row is different BY CONTRACT: `confluence()` weights an unlisted kind at ZERO,
        # and `test_an_UNWEIGHTED_kind_is_worth_zero_not_a_default` pins that a surface carrying
        # one stays LOCKED — a real, useful state. Failing the read instead turned "this evidence
        # counts for nothing" into "the file cannot be trusted", which are opposite facts about
        # the same row. Worth zero is a MEASUREMENT; unreadable is the absence of one.
        return "kind %r is not a declared evidence tier" % kind
    if _is_aggregate:
        n, k = r.get("n"), r.get("k")
        # ⚠ bool is a subclass of int, and `True` would otherwise pass as the count 1 — the same
        # shape REG-573 found writing "read (1 pages)" into a tombstone.
        for nm, v in (("n", n), ("k", k)):
            if isinstance(v, bool) or not isinstance(v, int):
                return "%s=%r is not a whole number, and score() would have defaulted it" % (nm, v)
        if not (0 <= k <= n):
            return "k=%d of n=%d is not a possible record" % (k, n)
    ts = r.get("ts")
    # ⚠ _fold keeps the GREATEST ts per (lock, kind, src, ref), so a row stamped in the future is
    # an unreplaceable pin: no honest later run could ever supersede it.
    if isinstance(ts, (int, float)) and ts > (time.time() + 300) * 1000:
        return "ts is in the future, which _fold could never supersede"
    return ""


def _rows():
    """-> (list|None, why). None means UNREADABLE, which is never 'no proofs'.

    #181 (REG-2470) - the SHARED ledger's code rows plus THIS PC's own ledger. A live row in the shared file is
    LEGACY: measured on one install before the split, counted on no PC (score() says how many it left out)."""
    sp = _ledger_split()
    return sp["rows"], sp["why"]


def _ledger_split():
    """#181 (REG-2470) - both ledgers, read once. -> dict

      rows    what THIS PC scores on: the shared ledger's code rows + this PC's own rows; None = UNREADABLE
      why     why rows is None ("" otherwise)
      legacy  the shared ledger's LIVE rows - measured on an install this PC cannot identify, before the split
      here    THIS PC's own rows (its live trials: banked here, or adopted through --adopt-legacy-live)
      code    how many shared rows are code rows

    Either file failing its read fails the whole read CLOSED, exactly as one bad row always has: UNKNOWN is LOCKED.
    """
    shared, why = _read_ledger(_ledger_path())
    if shared is None:
        return {"rows": None, "why": why, "legacy": [], "here": [], "code": 0}
    code, legacy = [], []
    for r in shared:
        if _is_per_pc(r):  # PER-PC-LEGACY
            legacy.append(r)
            continue
        code.append(r)
    hp = _here_path()
    mine, hwhy = _read_ledger(hp)
    if mine is None:
        return {"rows": None, "why": hwhy, "legacy": legacy, "here": [], "code": len(code)}
    for r in mine:
        # ⚠ only this PC's live trials are ever written there (bank, record, the fold, the adoption door), so any
        # other kind could not have been banked - and counting it would make a code proof one PC's alone
        if not _is_per_pc(r):  # PER-PC-ONLY
            return {"rows": None, "legacy": legacy, "here": [], "code": len(code),
                    "why": ("%s holds a %r row, and only this PC's LIVE trials are ever written there - a row that "
                            "could not have been banked fails the read CLOSED" % (os.path.basename(hp),
                                                                                str(r.get("kind"))))}
    return {"rows": code + mine, "why": "", "legacy": legacy, "here": mine, "code": len(code)}


def _read_ledger(p):
    """One proof ledger, every row judged by _row_fault. -> (list|None, why). None means UNREADABLE."""
    if not os.path.exists(p):
        return [], ""          # absent is legitimately empty: nothing has been proven yet
    out = []
    try:
        with io.open(p, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    # a line that will not parse is a hole in the evidence, not a blank one
                    return None, "%s has an unparseable row" % os.path.basename(p)
                if not isinstance(r, dict):
                    continue
                # ⚠⚠ v2581 — THE VALIDATIONS LIVED ONLY IN bank(), SO THEY GUARDED THE DOOR AND
                # NOT THE ROOM. Anything that appended a line to this file — a stray script, a
                # hand edit, a crashed writer — bypassed every check bank() makes, and score()
                # then read it as evidence. Worse, score() defaults a missing count:
                # `int(r.get("n", 1) or 0)`, so a three-key row {lock, kind, refused:true} was
                # silently worth n=1 k=1 of whatever tier it named.
                #
                # These are bank()'s OWN rules re-applied on the way IN. Measured against his 51
                # real rows before it shipped: ZERO would fail, so this costs nothing that is
                # honest and closes the gap for everything that is not.
                #
                # ⚠ A BAD ROW FAILS THE WHOLE READ, exactly as an unparseable line does. Skipping
                # it would let a forged row be quietly dropped while the rest scored on — and the
                # lock would open on a ledger nobody could see had been edited. UNKNOWN is
                # LOCKED here (may() returns False), so this fails closed. [[unknown-stays-unknown]]
                _bad = _row_fault(r)
                if _bad:
                    return None, ("%s has a row that could not have been banked: %s"
                                  % (os.path.basename(p), _bad))
                out.append(r)
    except Exception as e:
        return None, "%s could not be read: %s" % (os.path.basename(p), e)
    return out, ""


def _attacks_passed(k, n, attacks):
    """How many DISTINCT attacks may be credited as refused, given k of n attempts refused. -> int

    ⚠⚠ #123 — IT WAS `min(k, attacks)`, THE OPTIMISTIC ASSUMPTION, AND IT INFLATED THE SCORE IT EXISTS
    TO DEFLATE. With failures present, min(k, attacks) credits every distinct attack as refused
    whenever k >= attacks — as if all n-k failures fell on attacks that also passed elsewhere.
    MEASURED on his live evidence: prune.reports, 117 of 125 attempts over 35 attacks -> byAttack
    0.9011 ABOVE its raw 0.8788, and `deciding` is wilsonByAttack, so the lock's state was judged on
    confidence the evidence never gave (test_every_lock_declares_its_attacks, red on CI and here).
    A correction that can only help is not a correction. The conservative reading: every failure may
    be a different attack, so attacks - (n - k), floored at 0. Fewer trials and a larger failure
    share can only LOWER a Wilson bound, so this can never exceed the raw figure — PROVIDED
    attacks <= n. ⚠⚠ The second eye on v3487 (grok-4.7), reproduced: with attacks > n the old line
    credited 10 of 10 over 20 attacks as 20 of 20 (0.8389 against a raw 0.7225) and 9 of 10 over 20
    as 19 of 20. Distinct attacks cannot outnumber the attempts that ran them, so attacks is clamped
    to n and the credit to k. [[regression-guard]] [[unknown-stays-unknown]]
    """
    a = min(int(attacks), int(n))
    return max(0, min(int(k), a - (int(n) - int(k))))


def _count(rows):
    """(k, n) over rows _fold has already reduced - the ONE arithmetic score() and byOrigin both use. -> (k, n)

    v2444 — A ROW IS EITHER ONE ATTEMPT OR AN AGGREGATE, and the two must add up the same way.
    A row with no "n" is a single attempt worth 1 (everything record() has ever written), so the
    old arithmetic is unchanged for it. A row WITH "n" was banked by a harness that owns its own
    counting, and _fold has already reduced its family to the newest one — so re-running that
    harness replaces its evidence rather than doubling it.
    """
    n = sum(int(r.get("n", 1) or 0) for r in rows)
    k = sum(int(r.get("k", 1 if r.get("refused") else 0) or 0) for r in rows)
    return k, n


#: what a lock's evidence says about THIS PC when nothing here measured it - #181, his ruling 2026-10-22
_HERE_NOTHING = ("nothing measured on this PC yet - every figure here is shared: proven in code, true on any "
                 "install")
_HERE_UNREAD = "UNKNOWN - the proof ledgers could not be read"


def _by_origin(mine):
    """#181 (REG-2470) - where this lock's evidence came from. -> {"code": {k, n}, "here": {k, n, adopted} | None}

    `mine` is already folded. A row of a per-PC kind is THIS PC's measurement - _ledger_split drops the shared
    ledger's live rows as legacy before any score sees them - and every other row is a property of the code."""
    here = [r for r in mine if _is_per_pc(r)]
    ck, cn = _count([r for r in mine if not _is_per_pc(r)])
    h = None
    if here:  # PER-PC-ORIGIN
        hk, hn = _count(here)
        h = {"k": hk, "n": hn, "adopted": sum(1 for r in here if r.get("adopted"))}
    return {"code": {"k": ck, "n": cn}, "here": h}


def _here_say(by):
    """The sentence a surface prints beside byOrigin. -> str"""
    if not by:
        return _HERE_UNREAD
    h = by.get("here")
    if not h:
        return _HERE_NOTHING
    return ("measured on this PC: %d of %d live trial(s) refused%s"
            % (h["k"], h["n"], (" - %d adopted from the shared ledger by --adopt-legacy-live" % h["adopted"])
               if h.get("adopted") else ""))


def score(lock, rows=None, legacy=None):
    """The arithmetic for ONE lock. -> dict

    Never returns a wilson figure when n == 0. `wilson: None` means nobody looked; `0.0` would be
    a measurement nobody took. [[unknown-stays-unknown]]

    #181 (REG-2470) - `byOrigin` splits the figure into what is proven in CODE (shared by every PC) and what was
    measured on THIS PC, and `hereSay` says "nothing measured on this PC yet" when that half is empty. `legacyLive` is
    how many live rows the shared ledger holds for this lock and no PC counts: read here when score() reads the
    ledger itself, handed in by report(), and None when a caller passed its own rows and no legacy (not asked).
    """
    # a route scores on the SAME arithmetic as a valve — one table lookup, one score()
    spec = LOCKS.get(lock) or ROUTES.get(lock)
    if not spec:
        return {"lock": lock, "state": UNKNOWN, "why": "no such lock is declared"}
    if rows is None:
        sp = _ledger_split()
        rows, why = sp["rows"], sp["why"]
        if rows is None:
            return {"lock": lock, "state": UNKNOWN, "why": why,
                    "k": None, "n": None, "wilson": None, "kinds": None,
                    "byOrigin": None, "hereSay": _HERE_UNREAD, "legacyLive": None}
        legacy = sp["legacy"]  # LEGACY-COUNT
    mine = _fold([r for r in rows if r.get("lock") == lock])
    k, n = _count(mine)
    _origin = _by_origin(mine)
    # a kind counts as evidence only where something was actually REFUSED under it
    kinds = sorted({str(r.get("kind")) for r in mine
                    if int(r.get("k", 1 if r.get("refused") else 0) or 0) > 0})
    conf = confluence(kinds, KINDS)
    # ⚠⚠ HOW MANY DISTINCT SABOTAGES ARE UNDER THAT n — the repetition check.
    # Wilson tightens with n and cannot tell 83 independent looks from ONE attack applied 83
    # times. MEASURED 2026-09-04: `printer.stream` banked 83/83 -> 0.9558, and 80 of the 83 were
    # TWO attack functions applied to 40 reels each. On its five distinct attacks the identical
    # evidence scores 0.5655. Nothing was faked and every refusal was real — the SCORE was bought
    # by looping, which is the same objection already standing against prune.arm ("one proof
    # wearing four hats") at forty hats. `None` = the harness did not say how many, which is NOT
    # the same as one, and must never be read as a clean bill. [[unknown-stays-unknown]]
    # ⚠⚠ CLAIMS THAT WERE DECLARED AND NEVER EXERCISED. A banked row with n == 0 is a harness
    # saying "I own this axis and I could not run it". Zero attempts cannot move a Wilson bound, so
    # without this the axis vanishes and the lock scores on its remaining claims. See INCOMPLETE.
    # ⚠ WITHDRAWN AXES ARE EXCLUDED FROM `blind` AND REPORTED SEPARATELY. Both bank n == 0, and
    # folding them together told a reader "3 claims were never exercised at all" about three axes
    # that WERE exercised, found to be identity assertions, and deliberately retired (REG-600).
    blind = sorted({str(r.get("ref") or r.get("note") or "?")[:60]
                    for r in mine
                    if int(r.get("n", 1) or 0) == 0 and not r.get("withdrawn")})
    withdrawn = sorted({str(r.get("ref") or "?")[:60]
                        for r in mine if r.get("withdrawn")})
    # ⚠ #123 / v3487's second eye — each row's attacks are clamped to ITS OWN n before summing. Live
    # hover_wilson rows bank n=0 with attacks=1 (an axis declared and unable to run): an attack with
    # zero trials is no evidence, and adding it to the attack count while adding nothing to n is one
    # way attacks could exceed n and lift wilsonByAttack above the raw bound.
    _atk = [min(r.get("attacks"), int(r.get("n") or 0))
            for r in mine if isinstance(r.get("attacks"), int)]
    attacks = sum(_atk) if _atk else None
    out = {"lock": lock, "surface": spec["surface"], "acts": spec["acts"],
           "attacks": attacks,
           # REG-547 shape law — present on every path, so "no blind claim" and "never looked for
           # one" cannot render identically.
           "blindClaims": blind,
           # REG-547 shape law again: present on every path, so "nothing was retired" and "nobody
           # asked" cannot render identically.
           "withdrawnClaims": withdrawn,
           "wilsonByAttack": (None if not attacks
                              else round(wilson_lower(_attacks_passed(k, n, attacks), attacks), 4)),
           # REG-2141 - the pair that figure is computed from, published so a surface can print the
           # numbers that DECIDED without re-deriving _attacks_passed (a second copy would drift).
           "attacksPassed": (None if not attacks else _attacks_passed(k, n, attacks)),
           "repetition": (None if not attacks else round(float(n) / attacks, 1)),
           "k": k, "n": n, "kinds": kinds, "confluence": conf,
           "bar": spec["bar"], "kindsBar": spec["kinds_bar"], "after": list(spec["after"]),
           # #181 (REG-2470) - shape law again: on every path, so "nothing measured here" is said, not inferred
           "byOrigin": _origin, "hereSay": _here_say(_origin),
           "legacyLive": (None if legacy is None else sum(1 for r in legacy if r.get("lock") == lock))}
    if n == 0:
        out["wilson"] = None
        out["state"] = UNPROVEN
        # NOBODY LOOKED and THERE IS NOTHING TO LOOK AT are different facts. Both leave n=0 and
        # neither is a failure, but only one of them is waiting on work.
        if spec.get("unprovable"):
            out["provable"] = False
            out["why"] = ("this cannot be proven by sabotage and never will be: %s. n=0 here is "
                          "the correct and final state, not a harness anyone still owes."
                          % spec["unprovable"])
        else:
            out["provable"] = True
            out["why"] = ("no sabotage has been attempted against this surface's guards, so there "
                          "is no evidence in either direction. That is not a failure.")
        # ⚠ REG-547 SHAPE LAW — the key exists on EVERY path, including this one. A row that
        # carries `hardeningGap` only when there is a gap makes "no gap" and "never computed"
        # render identically, and a consumer would have to know which it was looking at.
        out["hardeningGap"] = _hardening_gap(None, conf, kinds, n, k)
        return out
    w = wilson_lower(k, n)
    out["wilson"] = round(w, 4)
    # ⚠⚠⚠ THE BAR IS READ AGAINST THE PER-ATTACK SCORE, NOT THE RAW n — HIS RULING, 2026-09-04,
    # and until now the code reported it and did not enforce it.
    #
    # His words: *"Beware n inflated by repetition. printer.stream banked 83/83 — but 80 of those
    # were TWO attacks applied to 40 reels each. Five distinct attacks scores 0.5655, not 0.9558.
    # Looping one attack over more inputs buys a bigger number and proves nothing new; MORE KINDS
    # is what earns HARDENED."*
    #
    # `wilsonByAttack` has been computed and published since REG-600 while `state` went on being
    # decided by `w`, so the repetition was REPORTED AND NOT ENFORCED. Measured on his tree the day
    # this changed, exactly two locks were OPEN on the inflated figure and would not open on the
    # honest one — and they are the two that matter most:
    #     prune.arm          wilson 0.9259 >= bar 0.839 > byAttack 0.5655   (THE DELETER, no undo)
    #     vault.sweep_start  wilson 0.8064 >= bar 0.510 > byAttack 0.3424   (HIS MONEY)
    # A third, vault.apply, held HARDENED on 0.9259 against a byAttack of 0.4385.
    #
    # ⚠ WHEN THE ATTACK COUNT IS UNKNOWN the honest score cannot be computed, so `w` is used and
    # `deciding` says so out loud. That is not a silent fallback: a reader can see the badge rests
    # on a figure whose repetition nobody measured. [[unknown-stays-unknown]]
    # ⚠ BOTH NUMBERS STAY IN THE PAYLOAD. Nothing is lost, and `deciding` is a FIELD because a
    # consumer cannot branch on a sentence.
    # ⚠ IT IS STILL A BADGE. `may()` has ZERO production callers and `_PRUNE_SAFE_TO_RUN` is a
    # separate switch that remains his — what changes is what the board CLAIMS, not what any door
    # does. Which is the whole point: the claim was outrunning its evidence.
    _by = out.get("wilsonByAttack")
    if _by is None:
        out["deciding"] = "wilson"
        out["decidingWhy"] = ("no attack count was banked, so repetition is UNKNOWN and the honest "
                              "per-attack score cannot be computed — this badge rests on raw n")
    else:
        w = _by
        out["deciding"] = "wilsonByAttack"
        out["decidingWhy"] = ("scored per DISTINCT ATTACK (%d) rather than per attempt (%d): "
                              "looping one attack over more inputs buys a bigger number and proves "
                              "nothing new" % (attacks, n))
    # ⚠⚠ THE COUNTS MUST NAME THE SAME QUANTITY AS THE FIGURE BESIDE THEM. ddd55279 switched the
    # DECISION to the per-attack score and left every sentence printing the raw attempt counts, so
    # a row read "56 of 56 sabotages refused · wilson 0.646" — and 56/56 is 0.936, not 0.646. The
    # number was right and the words beside it named another quantity, which is the one defect this
    # console keeps re-growing. [[label-outlived-referent]] [[the-unjoined-end]]
    # BOTH are printed: the attack pair decides, the attempt pair is kept in parentheses so nothing
    # is hidden and the repetition stays visible.
    if out["deciding"] == "wilsonByAttack":
        _wk, _wn = _attacks_passed(k, n, attacks), attacks
        _wunit, _walso = "DISTINCT ATTACKS", " (%d of %d attempts)" % (k, n)
    else:
        _wk, _wn, _wunit, _walso = k, n, "sabotages", ""
    # the tier above the bar — reported on every row so a surface can show how far past it is
    out["hardBar"] = HARD_BAR
    out["hardKindsBar"] = HARD_KINDS_BAR
    out["hardened"] = bool(w >= HARD_BAR and conf >= HARD_KINDS_BAR)
    # what this surface still owes the tier above it, named on every scored row — see
    # _hardening_gap. Computed here so LOCKED rows carry it too: a lock below its own bar is
    # also below HARDENED, and hiding that until it opens would make the ladder look shorter
    # than it is.
    # ⚠⚠ REG-616 — THE ADVICE MUST COUNT WHAT THE BAR COUNTS. This passed the RAW attempt pair
    # while `w` is the per-attack score, so it answered a question nobody is graded on: it told
    # reel.route "1 more refused sabotage would clear it" (n=56 -> 57) when a 57th ATTEMPT leaves
    # the 7 distinct attacks untouched and the figure unmoved at 0.646. wilson_lower(x, x) first
    # clears HARD_BAR at x=35, so the honest answer was +28 DISTINCT ATTACKS — wrong by 28x, and
    # wrong in the direction that recommends the exact repetition his 2026-09-04 ruling refuses to
    # reward. Sibling of REG-614, found by sweeping for it rather than by being told.
    out["hardeningGap"] = _hardening_gap(w, conf, kinds, _wn, _wk, unit=_wunit.lower())
    if w < spec["bar"]:
        out["state"] = LOCKED
        out["why"] = ("%d of %d %s were refused%s; the Wilson lower bound is %.3f against a "
                      "bar of %.3f" % (_wk, _wn, _wunit, _walso, w, spec["bar"]))
    elif conf < spec["kinds_bar"]:
        out["state"] = LOCKED
        out["why"] = ("the score clears (%.3f) but the evidence is too alike: kinds %s score %.2f "
                      "against %.2f. Wilson counts how many looks agreed, never whether they were "
                      "independent." % (w, kinds or "[]", conf, spec["kinds_bar"]))
    else:
        # ⚠ THE LADDER, NOT A BOOLEAN. "Wilson score" here is his nickname for the WHOLE standard
        # — the lower bound AND the confluence — so the tier above the bar is a real STATE that
        # every surface can reach, not a flag riding alongside OPEN. Clearing the bar is the floor;
        # HARDENED says a surface kept going and did it with independent kinds.
        out["state"] = HARDENED if out.get("hardened") else OPEN
        out["why"] = ("%d of %d %s refused%s · wilson %.3f >= %.3f · kinds %s = %.2f >= %.2f"
                      % (_wk, _wn, _wunit, _walso, w, spec["bar"], kinds, conf,
                         spec["kinds_bar"]))
    # ⚠⚠ LAST, AND IT OUTRANKS OPEN. A lock cannot be called proven while one of the axes its own
    # harness declared has never been exercised — the score simply never saw that axis. Applied
    # after the ladder so it also refuses to let HARDENED stand on an untested claim.
    # ⚠ IT IS A REPORT, NOT A GATE. `may()` is still never called and no button is blocked; what
    # changes is that the badge stops saying proven. [[unknown-stays-unknown]]
    if blind:
        out["state"] = INCOMPLETE
        # ⚠ SAME PAIR AS THE FIGURE. This sentence used to print the raw attempt counts beside a
        # per-attack score — `55 of 55` next to wilson 0.510, which is wilson_lower(4, 4), not
        # wilson_lower(55, 55) = 0.935. "ATTEMPTED" still earns its place: it separates what was
        # RUN from what this harness only DECLARED.
        out["why"] = ("%d of %d %s ATTEMPTED were refused%s — but %d claim(s) this harness "
                      "declared were never exercised at all (%s). Zero attempts cannot move a "
                      "Wilson bound, so that axis is MISSING from the score rather than failing "
                      "it — the number beside it is about the other claims only. Nothing is "
                      "blocked; the badge just stops saying proven."
                      % (_wk, _wn, _wunit, _walso, len(blind), ", ".join(blind)))
    return out


def _hardening_gap(w, conf, kinds, n, k, unit="sabotage(s)"):
    """What does this surface still OWE the HARDENED tier? -> dict, always the same shape.

    ⚠⚠ HARDENED WAS A TIER NOTHING COULD REACH AND NOTHING EXPLAINED. Measured 2026-09-04 across
    the whole table: **14 of 15 locks OPEN, 0 HARDENED**, and every `why` on those rows recited
    only the bar it had already cleared. A surface could sit one evidence-kind short of his own
    HARDENING stamp forever and the report would never say the word. An unreachable tier that
    gives no account of itself is indistinguishable from a broken one. [[unknown-stays-unknown]]

    ⚠ IT NAMES WHAT IS MISSING; IT NEVER LOWERS ANYTHING. The bars are his. This computes the
    shortfall and the CHEAPEST HONEST combination of kinds that would close it — and a kind is
    earned by doing that work, never by relabelling evidence already banked. Calling a fixture
    `live`, or an agreement a `sabotage`, would clear this gap on paper and prove nothing, which
    is the exact failure the confluence bar exists to stop.

    ⚠ THE SABOTAGE COUNT IS REAL ARITHMETIC, NOT AN ESTIMATE. `wilson_lower` rises with n at a
    fixed k/n, so "how many more consecutive refusals clear HARD_BAR" has one answer and it is
    computed here by asking, never by a rule of thumb.
    """
    out = {"hardened": bool(w is not None and w >= HARD_BAR and conf >= HARD_KINDS_BAR),
           "wilsonShort": None, "kindsShort": None, "moreRefusalsNeeded": None,
           "kindsWouldClose": [], "why": ""}
    if w is None:
        out["why"] = ("nothing has been attempted, so there is no gap to measure — an unmeasured "
                      "distance is not a short one")
        return out
    if out["hardened"]:
        out["why"] = "already HARDENED"
        return out

    if w < HARD_BAR:
        out["wilsonShort"] = round(HARD_BAR - w, 4)
        # how many MORE refused sabotages would clear it, asked rather than guessed
        if k == n:
            nn = n
            while nn < n + 500:
                nn += 1
                if wilson_lower(nn, nn) >= HARD_BAR:
                    out["moreRefusalsNeeded"] = nn - n
                    break
    if conf < HARD_KINDS_BAR:
        out["kindsShort"] = round(HARD_KINDS_BAR - conf, 4)
        have = set(kinds or ())
        missing = sorted((kd for kd in KINDS if kd not in have),
                         key=lambda kd: -KINDS[kd])
        # the smallest set of ABSENT kinds that closes the confluence gap, largest weight first
        run, chosen = conf, []
        for kd in missing:
            if run >= HARD_KINDS_BAR:
                break
            chosen.append(kd)
            run += KINDS[kd]
        out["kindsWouldClose"] = chosen if run >= HARD_KINDS_BAR else []

    bits = []
    if out["wilsonShort"] is not None:
        bits.append("wilson %.3f is %.3f short of %.3f%s"
                    % (w, out["wilsonShort"], HARD_BAR,
                       ("" if out["moreRefusalsNeeded"] is None else
                        " (%d more refused %s would clear it)"
                        % (out["moreRefusalsNeeded"], unit))))
    if out["kindsShort"] is not None:
        bits.append("kinds %.2f is %.2f short of %.2f%s"
                    % (conf, out["kindsShort"], HARD_KINDS_BAR,
                       (" — adding %s would close it"
                        % " + ".join("%s (%.1f)" % (kd, KINDS[kd])
                                     for kd in out["kindsWouldClose"])
                        if out["kindsWouldClose"] else
                        " — NO combination of the remaining kinds can close it")))
    out["why"] = ("owes HARDENED: " + "; ".join(bits)) if bits else ""
    return out


def _heart_says_watched():
    """Can the instruments that watch this system still go red? -> (bool, why)

    ⚠⚠ v2861 — THE LOCK AND THE HEART WERE TWO SYSTEMS THAT NEVER SPOKE. Konyo, 2026-09-09:
    *"the lock and everything still derives from the heart and visually seen"*. MEASURED when he
    asked: `self_arming.py` and `hover_wilson.py` held ZERO references to heart2. So a surface could
    reach its Wilson bar and ARM ITSELF while the gates that would catch its failure were blind —
    the lock proving the surface works, with nothing left able to prove the PROOF works.

    A Wilson score says "this refused every attack we made". It cannot say "and we would have
    noticed if it had not". That second question is the heart's, and it belongs in the same
    precondition chain as the upstream check: `may()` already refuses when a prerequisite is not
    OPEN, because proving a surface in isolation proves nothing about what feeds it. An instrument
    that cannot go red is exactly that kind of missing prerequisite.

    ⚠ IT FAILS CLOSED, matching `_rows()`: an unreadable census is UNKNOWN, and UNKNOWN never arms
    anything. [[unknown-stays-unknown]] [[the-unjoined-end]]

    ⚠ AND IT DOES NOT GATE ON `partial`. That flag has been True on every run this file has ever
    seen, so refusing on it would lock every surface for ever — a gate that can only say no is not
    a gate, it is furniture. Blind instruments are the honest bar: today there are 0, so this joins
    the two systems without bricking the lock. [[feedback-blind-fixture-green-gate]]
    """
    try:
        import heart2 as _h2
        # ⚠⚠ RESOLVED AT CALL TIME, and here is what it is for. This path was hardcoded, so a
        # TEST that exercises a destructive production path read HIS LIVE CENSUS — and a census
        # goes stale on any gate-file edit. Measured 2026-09-13: editing 16 gate files closed
        # `vault.sweep_start`, which failed 20 tests in TestChronicleSweepJob and friends. Those
        # tests are about SWEEP LOGIC (does it propose rather than write, does a silent lane read
        # as agreement); none of them is about whether supervision is currently proven. They were
        # asserting X while depending on Y. [[feedback-fixtures-never-touch-live-data]]
        #
        # ⚠ THIS DOES NOT SOFTEN THE LOCK. Production reads the real census and still fails
        # closed; `test_a_STALE_census_closes_the_lock` proves that and must never use this seam.
        # The shape is inherited from TV_SELF_ARMING_LEDGER above — an env honoured only at import
        # is a redirect that silently does not take, so it is read HERE, every call.
        _p = os.environ.get("TV_HEART_CENSUS") or os.path.join(_h2.HERE, ".heart2.json")
    except Exception as _e:
        return False, ("the heart could not be imported (%s), so nothing can say whether the gates "
                       "watching this surface still work. UNKNOWN fails CLOSED." % type(_e).__name__)
    if not os.path.exists(_p):
        # REG-2017 (#260, GrokBot tick 405) - NAME THE INSTRUMENT. "the heart has never run here" sat in GrokBot's fleet
        # tip seconds after its Heart panel read "census taken 15 s ago": two different censuses, one word. This one is
        # heart2 --prove's proof census (.heart2.json), not the Heart panel's live walk.
        return False, ("this PC's gates have never been PROVEN here (no heart2 proof census - not the Heart panel's live "
                       "census, which is a different walk), so nothing has shown that the gates watching this surface "
                       "can still go red. Run `python3 tv/heart2.py --prove`. UNKNOWN fails CLOSED.")
    try:
        with io.open(_p, encoding="utf-8") as _fh:
            _st = json.load(_fh)
    except Exception as _e:
        return False, ("the heart2 PROOF census would not parse (%s) — UNKNOWN fails CLOSED."
                       % type(_e).__name__)
    # ⚠⚠ v2862 — AND IT MUST NOT BE STALE. A cross-family review: "the file still exists with
    # blind=[], so may() returns true and a surface can arm itself even though no live supervision
    # has run since." Correct, and it is my own scar — surface_verdict() was given an `ageS` field
    # for exactly this an hour earlier and the lock did not get the same rule. [[stale-reading]]
    #
    # THE BAR IS MEASURED, NOT INVENTED. No arbitrary "24 hours": the census is stale when a GATE
    # FILE HAS CHANGED SINCE IT RAN. That is the precise condition under which the last proof no
    # longer speaks for the instruments now on disk, and it needs no number chosen by hand.
    # ⚠⚠ v2862 — CONTENT, NOT MTIME. The first cut compared each gate file's mtime against the
    # census `ranAt`. Right on the machine that proved them, wrong everywhere else: safe_copy, a git
    # checkout, CI and the Windows machine all stamp fresh mtimes, so every gate reads as newer, the
    # lock closes on every surface, and the sandbox reported this gate UNPROVABLE because it was
    # already red in its own copy. A rule that only holds in the tree that wrote it is not a rule.
    # A digest of the gate CONTENTS survives copying and says the thing actually meant: have the
    # instruments changed since they were proved? [[stale-reading]]
    _want = _st.get("gatesFingerprint")
    if not _want:
        # ⚠⚠ v3542 REG-1665 — A CENSUS STILL BEING PROVEN IS A PROVER THAT HAS NOT CAUGHT UP. #99 stamps the
        # fingerprint only once no declaring gate is owed, and a PC he plays on proves only while he does not - so
        # MEASURED 2026-10-01 his Windows PC had proved 524 of 714 with 161 still owed and NO fingerprint, and every
        # lock read "UNKNOWN fails CLOSED": 250 reels with nothing to read sat at ROUTE for days while reel.route's
        # own merit was 0.904. His v3042 ruling covers exactly this: an ordinary act refuses on MERIT while the prover
        # catches up; only an act with no undo waits. So a census that EXISTS and is unfinished reads as STALE -
        # and the BLIND instruments it has already recorded still fail closed for everything, because blind is a
        # fact about supervision, not about lateness. [[stale-reading]] [[the-unjoined-end]]
        _blind0 = list(_st.get("blind") or [])
        if _blind0:
            return False, ("%d instrument(s) are BLIND (%s) — a surface may not arm itself while the gates that would "
                           "catch its failure cannot go red (recorded by a census still being proven)."
                           % (len(_blind0), ", ".join(sorted(_blind0)[:3])))
        if _st.get("partial") or _st.get("sliceOwed"):
            return False, ("the heart2 PROOF census is STALE (not the Heart panel's live census): it is still being proven "
                           "(%s gate(s) owed) and carries no gate "
                           "fingerprint yet, so it cannot speak for the instruments now on disk."
                           % (_st.get("sliceOwed") if isinstance(_st.get("sliceOwed"), int) else "some"))
        return False, ("the heart2 PROOF census carries no gate fingerprint, so nothing can say whether it "
                       "still describes the instruments on disk. UNKNOWN fails CLOSED.")
    try:
        _have = _h2.gates_fingerprint()
    except Exception as _e:
        return False, ("the gate fingerprint could not be computed (%s) — UNKNOWN fails CLOSED."
                       % type(_e).__name__)
    if _have != _want:
        return False, ("the heart2 PROOF census is STALE (not the Heart panel's live census): the gate files have changed "
                       "since it ran "
                       "(%s != %s). The last proof does not speak for the instruments now on disk "
                       "— re-run `python3 tv/heart2.py --prove`." % (_have[:8], str(_want)[:8]))
    _blind = list(_st.get("blind") or [])
    if _blind:
        return False, ("%d instrument(s) are BLIND (%s) — a surface may not arm itself while the "
                       "gates that would catch its failure cannot go red."
                       % (len(_blind), ", ".join(sorted(_blind)[:3])))
    # v3862 (item 4) - AN OPEN ENVIRONMENT RE-PROVE IS A PROVER THAT HAS NOT CAUGHT UP: this PC's python, OS build, node
    # or autocrlf moved, and its proofs were earned under the old one. STALE, so his v3042 rule applies (an act with no
    # undo waits, an ordinary one refuses on merit); an older heart2 without the re-prove says nothing here.
    # v3866 (the #231 eye on v3862) - "could not tell" fails CLOSED like every other unreadable branch above; only an older
    # heart2 that has no re-prove at all says nothing here
    _er = None
    if hasattr(_h2, "env_reprove_state"):
        try:
            _er = _h2.env_reprove_state(_st, path=os.path.join(os.path.dirname(os.path.abspath(_p)), _h2.ENV_NAME))
        except Exception as _e:
            _er = {"owed": None, "unknown": "the environment re-prove check raised %s" % type(_e).__name__}
    if _er and _er.get("unknown"):
        return False, ("the heart2 PROOF census may be STALE: whether this PC's environment changed cannot be told (%s) "
                       "- UNKNOWN fails CLOSED." % str(_er.get("unknown"))[:160])
    if _er and _er.get("owed"):
        return False, ("the heart2 PROOF census is STALE (not the Heart panel's live census): this PC's environment "
                       "changed (%s) and %d gate(s) are proved again under it."
                       % (_h2.env_change_words(_er), len(_er["owed"])))
    # ⚠ COVERAGE IS REPORTED, NOT GATED. Same review: blind=[] with proved 12 of 47 means almost
    # nothing was exercised. True — and the honest response is to SAY the number, not to invent a
    # ratio bar. `partial` has been True on every run this file has seen, so gating on it locks
    # everything for ever; gating on a proved/total threshold would mean picking a figure out of
    # the air and calling it a law. The reason string now carries the coverage so it can never be
    # invisible to whoever reads the permit. [[zero-needs-a-denominator]]
    # ⚠⚠ v3318 — THE DENOMINATOR WAS THE WRONG POPULATION, AND THE 40 VANISHED INTO IT.
    # `proved` counts gates that DECLARE a red-proof and were proven. Dividing it by `total` —
    # every registered gate, including those that declare no proof at all — puts a numerator from
    # one population over a denominator from another. MEASURED 2026-09-18 from run_gates.GATES and
    # the test files themselves: 457 registered, 417 declaring a RED_PROOF, 394 proven. So this
    # printed "394 of 457" (86.2%) where the true figure for that population is 394 of 417 (94.5%).
    #
    # ⚠ IT UNDER-STATED, which is the safe direction and exactly why it would have survived: a
    # number that looks worse than reality never gets challenged.
    #
    # ⚠⚠ AND THE REAL LOSS WAS THE 40. Forty registered gates declare NO red-proof — gates that
    # have never been SEEN to refuse. Folding them into a denominator turns "we have not proven
    # these" into "we proved a smaller fraction", which is far less actionable. They now get their
    # own clause. control_app.py:19460 has printed it correctly all along ("N of <declared>
    # gate(s) can still go red; M carry no executable proof and are UNKNOWN") — one fact, two
    # readers, and only this one was wrong. [[zero-needs-a-denominator]] [[copy-drift]]
    _proved, _decl, _tot = _st.get("proved"), _st.get("declared"), _st.get("total")
    _noproof = ((_tot - _decl) if isinstance(_tot, int) and isinstance(_decl, int) else None)
    return True, ("instruments watched: %s of %s gate(s) that declare a proof are PROVEN, "
                  "0 blind, census current%s"
                  % (_proved, _decl,
                     ("" if _noproof is None else
                      ("; %d of %d registered gate(s) declare NO executable proof and have never "
                       "been seen to refuse" % (_noproof, _tot)))))


_HEART_SAYS_WATCHED_REAL = _heart_says_watched   # #156 - per-lock stands aside when a law seats the global answer

#: the two phrases _heart_says_watched() uses for the two failures that mean different things.
#: ⚠ THEY ARE MATCHED AS TEXT, AND test_the_stale_prover_is_not_a_safety_verdict PARSES THIS FILE
#: TO PROVE BOTH STILL EXIST IN THE BRANCHES THEY CAME FROM. A silent reword would otherwise turn
#: every stale census back into a refusal for every lock — the exact outage this split exists to
#: prevent — and nothing would say so. [[source-reading-guard]]
_HEART_STALE_PHRASE = "census is STALE"
_HEART_BLIND_PHRASE = "are BLIND"


def heart_block_kind(why):
    """Which KIND of heart failure is this? -> 'stale' | 'blind' | 'other'

    STALE means the prover has not caught up with the code. BLIND means a gate cannot fail at all.
    Only one of those is a fact about the SURFACE; the other is a fact about the INSTRUMENT, and
    conflating them is why writing a single gate could shut nineteen locks at once.
    """
    w = str(why or "")
    if _HEART_STALE_PHRASE in w:
        return "stale"
    if _HEART_BLIND_PHRASE in w:
        return "blind"
    return "other"


#: #156 (his ruling 2026-10-28: "do whatever is needed.. if needs to be rep-proving and build-per lock then do it") - the
#: module(s) each lock's DOOR lives in. A lock goes STALE only through ITS OWN guard laws: the gates whose source names
#: the lock, or directly imports (or opens) one of these modules or the lock machinery (self_arming). Measured on his
#: census 2026-10-28: printer.stream 81, reel.route 70, frame.release 119 of 1,200 gates - so a law edited among the other
#: ~1,100 no longer takes the river off every PC until a full re-prove (#193). A recorded BLIND still closes every lock
#: (his 2026-09-12 ruling: BLIND is not STALE). A lock NOT listed here, and every route, keeps the global rule. A door in
#: a module as broad as control_app counts through that lock's own marks (LOCK_MARKS below), not the module's import.
LOCK_DOORS = {
    "printer.stream": ("printer",),
    "reel.route": ("reel_route_lane",),
    "frame.release": ("reel_retention",),
    "vault.sweep_start": ("control_app", "sweep_wilson"),
    "vault.apply": ("read_names_feeder",),
    "prune.reports": ("disk_report_wilson", "control_app"),
    "vault.forget": (),
    "miniauto.run": ("hover_wilson",),
    "console.pixel_rescue": ("control_app",),
}
#: the lock machinery every lock stands on: a law that exercises it guards them all
LOCK_MACHINERY = ("self_arming",)
#: REG-2865 (#212) - A DOOR MODULE TOO BROAD TO SAY WHICH LOCK A LAW EXERCISES. Measured on the batch-3841 tree (1,234
#: gates): importing or opening control_app made 489 laws guard vault.sweep_start, 490 prune.reports and 488
#: console.pixel_rescue - so after every ship hundreds of laws nowhere near the sweep were owed, they never re-prove while he
#: plays, and the paid sweep stayed shut (the Mac's vault ledger went unwritten for hours, the ALT's for days). In a module
#: listed here, a law guards a lock only through that lock's LOCK_MARKS; a lock with no marks keeps the import rule (broad in
#: the safe direction), and so does every small door module.
BROAD_DOORS = ("control_app",)
#: per lock whose door lives in a broad module: the names its own code answers to - its door functions and their state, its
#: routes and its stores, the modules it reads with, and the lock's name in any spelling. Matched as text, so a law that
#: names one in prose guards it too: broad in the safe direction.
LOCK_MARKS = {
    # the paid sweep: chronicle_sweep_start asks the lock; the vault sweep, its autoreel picker, its jobs, its ledger
    # (vault_accum.json) and its readers (vault_retro, chronicle_retro), and the wilson that earns it
    "vault.sweep_start": ("vault.sweep_start", "vault_sweep", "VAULT_SWEEP", "chronicle_sweep", "_chron_sweep",
                          "CHRON_SWEEP", "vault_autoreel", "_VAULT_AUTOREAD", "_VAULT_JOB", "_CHRON_JOB", "vault_accum",
                          "VAULT_LEDGER_PATH", "vault_retro", "chronicle_retro", "sweep_wilson", "sweep_live"),
    # the freed-space claim: disk_history_append asks the lock before a row says prunedMb
    "prune.reports": ("prune.reports", "disk_history", "DISK_HISTORY", "prunedMb", "pruned_mb", "disk_report"),
    # the pixels' reload: the console's rescue loop asks the lock on a BLANK pixel verdict
    "console.pixel_rescue": ("console.pixel_rescue", "_console_rescue_loop", "pixelBlank", "pixelMayAct", "_PIXEL_ACT",
                             "_PIXEL_VERDICT_MAX_AGE_S", "ui_rescue_due", "console-blank-by-pixels", "pixel_witness"),
}
_LOCK_MEMO = {"key": None, "owed": None, "blind": None, "why": None, "src": {}, "guard": {}}


#: REG-3324 - a law that guards at least this many locks is narrowed to its failing cases' classes when the net finds it
NET_NARROW_MIN_LOCKS = 5


def _case_class_source(text, case):
    """REG-3324 - the source of the TestCase class a failing case ("Class.test_x") belongs to. -> str | None"""
    cls = str(case).split(".", 1)[0]
    m = re.search(r"(?m)^class\s+%s\b[^\n]*:\n" % re.escape(cls), text or "")
    if not m:
        return None
    nxt = re.search(r"(?m)^(?:class\s|def\s|[A-Za-z_]\w*\s*=)", text[m.end():])
    return text[m.start(): m.end() + (nxt.start() if nxt else len(text) - m.end())]


def _net_case_guards(name, text, find, lock, stems):
    """REG-3324 (#103) - does this safety-net FIND close `lock`? -> bool

    MEASURED 11-06 23:38Z on his Mac: test_control (one 2,274-case file that names every lock) was found RED once and,
    guarding all nine, closed the whole river. A law that guards NET_NARROW_MIN_LOCKS or more locks is narrowed to the
    CLASSES of the cases that failed (the find's `cases`, REG-3324 heart2): the lock closes when one of those classes
    guards it (_guards_lock on that class's source). Anything less certain stays broad, in the safe direction: a find
    that names no case, a case whose class cannot be found, and every focused law (fewer locks) close by the whole file
    exactly as before."""
    if not _guards_lock(text, lock, stems):
        return False
    cases = find.get("cases") if isinstance(find, dict) else None
    if not cases:
        return True
    try:
        n_locks = sum(1 for lk in LOCK_DOORS if _guards_lock(text, lk, LOCK_DOORS[lk]))
    except Exception:
        return True
    if n_locks < NET_NARROW_MIN_LOCKS:
        return True
    for c in cases:
        src = _case_class_source(text, c)
        if src is None or _guards_lock(src, lock, stems):
            return True
    return False


def _guards_lock(text, lock, stems):
    """Does this gate's source guard `lock`? -> bool. Names the lock or one of its marks, or directly imports / opens
    one of its door modules or the lock machinery - a BROAD_DOORS module only when the lock declares no marks (REG-2865).
    Static and cheap; broad in the safe direction."""
    if not text:
        return False
    if ('"%s"' % lock) in text or ("'%s'" % lock) in text:
        return True
    marks = LOCK_MARKS.get(lock) or ()
    for mark in marks:
        if mark in text:
            return True
    for stem in tuple(stems) + LOCK_MACHINERY:
        if marks and stem in BROAD_DOORS:
            continue
        if (stem + ".py") in text:
            return True
        if re.search(r"(?m)^\s*(?:from\s+%s\s+import\b|import\s+%s\b)" % (re.escape(stem), re.escape(stem)), text):
            return True
    return False


# ══ #103 item 3 (REG-3484) - A BROAD LAW HOLDS A LOCK ONLY THROUGH THE PART OF IT THAT GUARDS THAT LOCK ═════════════════
# His question, 11-07 ~01:45 IST: "if the river proves itself already why does every proof going forward not related to it
# need to continue proofing it over and over again for it to unlock?" - and 11-08: "for fleet the river should be flowing
# for all pcs". MEASURED 11-09 on main, v3878-v3886: in every version that owed a lock anything, the same few BROAD laws
# held all nine shut - test_control (one 2.7 MB file, 486 classes), test_ledger_authority and the lock-machinery laws -
# because the WHOLE FILE imports the lock machinery, so any edit anywhere in it owed every lock on every PC until that law
# was proven again there (the ALT and Dean's PC wait out GitHub's proof import, 45-70 min a version). Yet of test_control's
# 486 classes 1-15 touch a river lock, and over the five versions that changed test_control.py the three river locks' own
# part of it - its module code, the classes that touch the lock, the red-proofs aimed at its code - was byte-identical in
# four (scratchpad river103/proto.py).
#
# So a law that guards NET_NARROW_MIN_LOCKS or more locks keeps a lock shut only when THAT LOCK'S PART changed since the
# proof this PC banked. The census records the part's digest beside the law's own (heart2 `lockShas`, written by the same
# write that banks `gateShas`); the lock compares it with the part of the file on disk now. The part of a lock is:
#   * the module's own code (everything outside its classes, its RED_PROOF list and its docstring) - an edit there owes
#     every lock the law guards;
#   * every class whose source guards the lock (_guards_lock, plus a door or machinery module the file imported under
#     another name - `import reel_retention as rr` makes a class that says `rr.` a guard);
#   * every class this PC's red memory saw CATCH a sabotage aimed at the lock, recorded by name with the proof - so a
#     class that guards the lock without naming it is still in its part, and a renamed or removed one owes it;
#   * the red-proofs aimed at the lock's code, and the bytes of the lock's own door modules and of this file (the lock
#     machinery) - a version that changes the lock's own code AND its broad guard owes the guard again.
# Anything less certain stays broad, in the safe direction: a census with no part recorded, a file that will not parse, a
# RED_PROOF that is not a literal list (then it is module code), a focused law (fewer locks), and a console whose index
# child has not answered yet. A class that catches a lock's sabotage on a PC whose red memory never saw it is the one gap
# the text rule leaves; GitHub proved those exact bytes before main could move (ruling 11-05, CI proves once).
# The law: test_a_version_that_touches_nothing_a_lock_reads_keeps_it_open. [[heart-first]] [[the-unjoined-end]]
LOCK_PART_VERSION = 1


def _sha16(text):
    """The digest heart2.gate_shas gives a gate's text. -> str"""
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]


def _sha24(text):
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:24]


def _part_aliases(nodes):
    """The names a module's top-level imports bind, by the module they come from. -> {stem: {name}} ("*" = a star import)"""
    import ast
    out = {}

    def walk(n):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return
        if isinstance(n, ast.Import):
            for a in n.names:
                out.setdefault(a.name.split(".")[0], set()).add((a.asname or a.name).split(".")[0])
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            for a in n.names:
                out.setdefault(n.module.split(".")[0], set()).add(a.asname or a.name)
        for c in ast.iter_child_nodes(n):
            walk(c)

    for n in nodes:
        walk(n)
    return out


def _class_guards(src, lock, aliases):
    """#103 item 3 - does this class's source guard `lock`? _guards_lock, or a door / machinery module the FILE imported
    under another name used inside it. -> bool. Broad in the safe direction, like _guards_lock."""
    stems = LOCK_DOORS.get(lock) or ()
    if _guards_lock(src, lock, stems):
        return True
    marks = LOCK_MARKS.get(lock) or ()
    for stem in tuple(stems) + LOCK_MACHINERY:
        if marks and stem in BROAD_DOORS:
            continue
        for al in (aliases or {}).get(stem, ()):
            if al == "*" or re.search(r"(?<![\w.])%s\b" % re.escape(al), src):
                return True
    return False


def lock_index(text):
    """#103 item 3 - one gate file, indexed by the part each lock stands on. -> dict | None (it would not parse)

    {"v", "sha": the file's digest (heart2.gate_shas), "m": its module code's digest, "cls": {class: [digest, [locks]]},
    "red": [[entry digest, [locks]]] | None (RED_PROOF is not a literal list - it is module code then), "all": [the locks
    the whole file guards]}. Compact on purpose: the console asks a short-lived child for it (audit_child.lock_index_for),
    because parsing test_control in its own heap costs ~140 MB (#172)."""
    import ast
    try:
        tree = ast.parse(text)
    except Exception:                                   # SyntaxError, ValueError (a null byte), RecursionError
        return None
    lines = text.splitlines(True)

    def seg(n):
        start = min([n.lineno] + [d.lineno for d in getattr(n, "decorator_list", None) or ()])
        return "".join(lines[start - 1:getattr(n, "end_lineno", None) or n.lineno])

    body = list(tree.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]                                 # the module docstring is prose
    aliases = _part_aliases([n for n in body if not isinstance(n, ast.ClassDef)])
    module, classes, red = [], {}, None
    for n in body:
        if isinstance(n, ast.ClassDef):
            # a second class of one name: both stay in its part (the later one wins at import, both are its bytes)
            classes[n.name] = classes.get(n.name, "") + seg(n)
            continue
        if red is None and isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "RED_PROOF":
            try:
                val = ast.literal_eval(n.value)
            except Exception:
                val = None
            if isinstance(val, (list, tuple)) and all(isinstance(e, dict) for e in val):
                red = [dict(e) for e in val]
                continue
        module.append(seg(n))
    locks = sorted(LOCK_DOORS)
    out = {"v": LOCK_PART_VERSION, "sha": _sha16(text), "m": _sha24("".join(module)),
           "cls": {}, "red": None, "all": [lk for lk in locks if _guards_lock(text, lk, LOCK_DOORS[lk])]}
    for c, src in classes.items():
        out["cls"][c] = [_sha24(src), [lk for lk in locks if _class_guards(src, lk, aliases)]]
    if red is not None:
        out["red"] = []
        for e in red:
            blob = json.dumps(e, sort_keys=True, ensure_ascii=False, default=str)
            out["red"].append([_sha24(blob), [lk for lk in locks if _guards_lock(blob, lk, LOCK_DOORS[lk])]])
    return out


def red_entry_digest(entry):
    """#103 item 3 - one RED_PROOF entry's digest, as lock_index files it. -> str | None"""
    try:
        return _sha24(json.dumps(dict(entry), sort_keys=True, ensure_ascii=False, default=str))
    except Exception:
        return None


def _part_door_stems(lock):
    """The modules whose bytes are part of a lock's part: its own doors (a BROAD_DOORS module only when the lock declares
    no marks - _guards_lock's rule) and the lock machinery."""
    marks = LOCK_MARKS.get(lock) or ()
    return [s for s in tuple(LOCK_DOORS.get(lock) or ()) + LOCK_MACHINERY if not (marks and s in BROAD_DOORS)]


def _door_sha(stem):
    """A door module's digest on disk, or UNREADABLE (never an empty file's digest). -> str"""
    try:
        with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), stem + ".py"), "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()[:16]
    except OSError:
        return "UNREADABLE"


def lock_part_digest(index, lock, extra=(), door=None):
    """#103 item 3 - the digest of `lock`'s part of an indexed gate file. -> str. `extra` = classes recorded as catching
    the lock's sabotages (a name the file no longer has digests as MISSING, so a removed catcher owes the lock); `door`
    is the door-module reader (a law's seam)."""
    h = hashlib.sha256(("lockpart/%d\0%s\0%s" % (LOCK_PART_VERSION, lock, (index or {}).get("m"))).encode("utf-8"))
    cls = (index or {}).get("cls") or {}
    mine = set(c for c, v in cls.items() if isinstance(v, list) and len(v) == 2 and lock in (v[1] or ()))
    for c in sorted(mine | set(extra or ())):
        v = cls.get(c)
        h.update(("\0C%s=%s" % (c, v[0] if isinstance(v, list) and v else "MISSING")).encode("utf-8"))
    red = (index or {}).get("red")
    if red is None:
        h.update(b"\0R?")
    else:
        for s in sorted(s for s, lks in red if lock in (lks or ())):
            h.update(("\0R" + str(s)).encode("utf-8"))
    for stem in _part_door_stems(lock):
        h.update(("\0D%s=%s" % (stem, (door or _door_sha)(stem))).encode("utf-8"))
    return h.hexdigest()[:24]


def lock_parts(index, catchers=None, door=None):
    """#103 item 3 - what the census records for a BROAD gate it banks. -> {lock: {"d": digest, "c": [classes]}} | None

    None for a gate that guards fewer than NET_NARROW_MIN_LOCKS locks (it keeps the whole-file rule) or no index. `catchers`
    = {lock: [class, ...]} - the classes the red memory saw catch that lock's sabotages; those not already in its part by
    their own text are recorded by name, so the lock asks the same classes later."""
    if not isinstance(index, dict) or len(index.get("all") or ()) < NET_NARROW_MIN_LOCKS:
        return None
    cls = index.get("cls") or {}
    out = {}
    for lock in index["all"]:
        mine = set(c for c, v in cls.items() if lock in (v[1] or ()))
        extra = sorted(set((catchers or {}).get(lock) or ()) - mine)
        out[lock] = {"d": lock_part_digest(index, lock, extra, door=door), "c": extra}
    return out


def _lock_index_now(name, files, text):
    """This gate file's lock index now, memoised per census. -> (index | None, pending bool). On a console it is asked of a
    short-lived child (#172); `pending` = the child has not answered yet - the caller narrows nothing and asks again later."""
    memo = _LOCK_MEMO.setdefault("index", {})
    if name in memo:
        return memo[name], False
    try:
        import audit_child as _ac
        if _ac.wanted():
            import heart2 as _h2
            f = files.get(name) if isinstance(files, dict) else None
            if not f:
                return None, False
            st = os.stat(f if os.path.isabs(f) else os.path.join(_h2.HERE, f))
            got = _ac.lock_index_for(f, (st.st_mtime_ns, int(st.st_size)))
            if got is None:
                return None, True
        else:
            got = lock_index(text)
    except Exception:
        got = None
    memo[name] = got
    return got, False


def _lock_part_unchanged(name, lock, text, files):
    """#103 item 3 - is `lock`'s part of this owed BROAD gate the part this PC proved? -> True | False | None (pending)

    False (the whole-file rule stands) whenever anything is uncertain: no part recorded, a record for other bytes than the
    proved ones, a focused gate, an index for other bytes than these, a lock the proved bytes did not guard."""
    rec = (_LOCK_MEMO.get("lockShas") or {}).get(name)
    if not isinstance(rec, dict) or rec.get("v") != LOCK_PART_VERSION or not rec.get("sha") \
            or rec.get("sha") != (_LOCK_MEMO.get("gateShas") or {}).get(name):
        return False
    r = (rec.get("locks") or {}).get(lock)
    if not isinstance(r, dict) or not r.get("d"):
        return False
    idx, pending = _lock_index_now(name, files, text)
    if pending:
        return None
    if not isinstance(idx, dict) or idx.get("v") != LOCK_PART_VERSION or idx.get("sha") != _sha16(text) \
            or len(idx.get("all") or ()) < NET_NARROW_MIN_LOCKS:
        return False
    return lock_part_digest(idx, lock, r.get("c") or ()) == r.get("d")


def _owed_and_blind():
    """This PC's proof census against the gate files on disk now. -> (owed names, blind names, files) | (None, None, why)

    owed = gates that DECLARE a proof and are not proven against their file as it is now (heart2.slice_owed - the same
    rule a slice proves by), blind = what the census filed BLIND. Memoised on the census bytes and the gate fingerprint,
    so a may() on a hot path pays what the global rule already pays."""
    try:
        import heart2 as _h2
        # the call-time seam _heart_says_watched reads too, so a law's fixture census reaches both answers
        _census = os.environ.get("TV_HEART_CENSUS") or os.path.join(_h2.HERE, ".heart2.json")
        if not os.path.exists(_census):
            return None, None, "no proof census on this PC"
        with io.open(_census, "rb") as _fh:
            raw = _fh.read()
        # v3862 (item 4) - the environment re-prove's record beside THIS census, and in the memo's key: an open re-prove
        # owes guards while the census bytes have not moved yet
        _envp = os.path.join(os.path.dirname(os.path.abspath(_census)), getattr(_h2, "ENV_NAME", ".heart2_env.json"))
        try:
            with io.open(_envp, "rb") as _fe:
                _envb = hashlib.sha256(_fe.read()).hexdigest()
        except OSError:
            _envb = None
        # #103 item 3 - and the door modules' bytes: a lock's part carries them, so a changed door file is never judged
        # from an answer memoised before it changed
        _doors = tuple(sorted(set(s for lk in LOCK_DOORS for s in _part_door_stems(lk))))
        key = (hashlib.sha256(raw).hexdigest(), _h2.gates_fingerprint(), _envb, tuple(_door_sha(s) for s in _doors))
        if _LOCK_MEMO["key"] == key:
            return _LOCK_MEMO["owed"], _LOCK_MEMO["blind"], _LOCK_MEMO["files"]
        st = json.loads(raw.decode("utf-8"))
        files = dict(_h2.gate_files())
        try:
            _so = _h2.slice_owed(list(files.items()), st, env_path=_envp)
        except TypeError:                                    # an older heart2 without the re-prove
            _so = _h2.slice_owed(list(files.items()), st)
        owed = set(n for n, _k in (_so.get("owed") or []))
        blind = set(st.get("blind") or [])
        _gsr = st.get("gateShas") if isinstance(st.get("gateShas"), dict) else {}
        _lsr = st.get("lockShas") if isinstance(st.get("lockShas"), dict) else {}
        _LOCK_MEMO.update(key=key, owed=owed, blind=blind, files=files, src={}, guard={}, index={},
                          gateShas=_gsr, lockShas=_lsr)
        return owed, blind, files
    except Exception as _e:
        return None, None, "the census could not be read for one lock (%s)" % type(_e).__name__


def _lock_src(name, files):
    """#156 - one owed gate's source, read once per census (memoised in _LOCK_MEMO). -> str | None (would not read)"""
    if name in _LOCK_MEMO["src"]:
        return _LOCK_MEMO["src"][name]
    f = files.get(name) if isinstance(files, dict) else None
    text = None
    if f:
        try:
            import heart2 as _h2
            with io.open(f if os.path.isabs(f) else os.path.join(_h2.HERE, f), encoding="utf-8") as _fh:
                text = _fh.read()
        except Exception:
            text = None
    _LOCK_MEMO["src"][name] = text
    return text


def _lock_guard(name, lock, files):
    """#156 - does this owed gate guard `lock`? -> bool. ONE rule for the per-lock answer and the order the self-prove lane
    proves in (#103-C), so the two can never disagree about which laws keep a lock shut. [[copy-drift]]"""
    # v3856 gate - one answer per (gate, lock, doors) per census: report() asks every lock, and re-running the regex
    # walk over every owed gate's source for each one took test_heart past its 60 s budget (48,204 walks per report)
    stems = LOCK_DOORS.get(lock) or ()
    gk = (name, lock, tuple(stems))
    memo = _LOCK_MEMO.setdefault("guard", {})
    if gk not in memo:
        t = _lock_src(name, files)
        if t is None:
            memo[gk] = True                       # a gate that will not read is counted, never skipped
        elif not _guards_lock(t, lock, stems):
            memo[gk] = False
        else:
            # #103 item 3 (REG-3484) - a BROAD gate holds this lock only when the lock's own part of it changed
            same = _lock_part_unchanged(name, lock, t, files)
            if same is None:
                return True                       # the index child has not answered: counted, and asked again later
            memo[gk] = not same
    return memo[gk]


def owed_guard_rank():
    """#103-C - THE LAWS THAT KEEP A LOCK SHUT, AND WHICH LOCK EACH OPENS SOONEST. -> {"rank": {gate: int},
    "locks": [[lock, n owed guards]], "why": str}. Never raises.

    His question (11-07 ~01:45 IST): "if the river proves itself already why does every proof going forward not related to
    it need to continue proofing it over and over again for it to unlock?". MEASURED on the ALT 11-07 ~09:50 IST (v3876):
    its vault autoread loop FLOWING every 45 s and vault.sweep_start OPEN-not-permitted for ~42 h - "26 of its own guard
    law(s) changed or are unproven" - while the self-prove lane worked 71 owed laws cheapest-first, so the sweep lock's
    guards waited behind laws that guard nothing. A lock that answers per lock (#156, LOCK_DOORS) opens the moment ITS
    guards are proven, so those go first: rank 0 = a guard of the door lock with the FEWEST owed guards (it opens after
    the fewest proofs), 1 the next, and a law guarding two locks takes the sooner one. A gate guarding no door lock has no
    rank. {} when the census cannot be read, and when it records a BLIND: a BLIND shuts every lock and is proved first,
    alone (REG-1673), whatever this says. [[heart-first]] [[unknown-stays-unknown]]"""
    out = {"rank": {}, "locks": [], "why": ""}
    try:
        owed, blind, files = _owed_and_blind()
        if owed is None:
            out["why"] = "the census could not be asked (%s) - the lane keeps its own order" % files
            return out
        if blind:
            out["why"] = "the census records a BLIND - it is proved first, alone (REG-1673)"
            return out
        per = []
        for lock in sorted(LOCK_DOORS):
            g = sorted(n for n in owed if _lock_guard(n, lock, files))
            if g:
                per.append((len(g), lock, g))
        per.sort(key=lambda t: (t[0], t[1]))
        for pos, (_n, _lock, g) in enumerate(per):
            for n in g:
                out["rank"].setdefault(n, pos)
        out["locks"] = [[lock, n] for n, lock, _g in per]
        out["why"] = ("%d owed law(s) keep %d lock(s) shut - proved first, the lock with the fewest owed guards first"
                      % (len(out["rank"]), len(per)) if per else "no owed law guards a door lock")
    except Exception as _e:
        out = {"rank": {}, "locks": [], "why": "the shut locks' guards could not be ranked (%s)" % type(_e).__name__}
    return out


def _lock_heart(lock, gwhy=None):
    """#156 - the heart's answer for ONE lock, from its own guard laws, when the global rule called the census STALE.
    -> (ok, why) | None (no per-lock answer: the global rule stands). Asked by may() and report() only when the global
    rule refused; `gwhy` is that refusal (read here when a caller does not pass it).

    None when the lock declares no door (LOCK_DOORS), when the census cannot be read (the global rule then fails it
    closed), when the global answer has been seated by a law (a law that seats _heart_says_watched is asking about the
    global rule), when the global refusal is not STALE, and whenever the census records a BLIND instrument: his
    2026-09-12 ruling (test_a_stale_prover_is_not_a_safety_verdict) - BLIND IS NOT STALE, a gate that cannot fail is a fact
    about supervision itself and closes every lock. #156 narrows STALE only. A guard owed a proof makes the lock STALE
    (its reason is the global one, plus which of ITS guards are owed), and the v3042 rule still decides what STALE
    permits (an ordinary act on merit, an irreversible one never)."""
    if lock not in LOCK_DOORS or _heart_says_watched is not _HEART_SAYS_WATCHED_REAL:
        return None
    if gwhy is None:
        try:
            _gok, gwhy = _heart_says_watched()
        except Exception:
            return None
        if _gok:
            return None
    if heart_block_kind(gwhy) != "stale":
        return None
    owed, blind, files = _owed_and_blind()
    if owed is None or blind:
        return None
    g_owed = sorted(n for n in owed if _lock_guard(n, lock, files))
    if g_owed:
        return False, ("%s For %s (#156, per-lock): %d of its own guard law(s) changed or are unproven since it ran (%s); "
                       "the rest of the tree does not decide this lock."
                       % (str(gwhy).rstrip(), lock, len(g_owed), ", ".join(g_owed[:3])))
    # #103 item 3 - name the broad laws that changed only outside this lock's part, so an open lock says why it is open
    _stems = LOCK_DOORS.get(lock) or ()
    _narrow = sorted(n for n in owed if (lambda t: t is not None and _guards_lock(t, lock, _stems))(_lock_src(n, files)))
    return True, ("instruments watched for %s: every law that guards it is proven against the files on disk; the %d gate(s) "
                  "owed elsewhere guard other surfaces, not this one (#156, per-lock)%s"
                  % (lock, len(owed), ("; %d broad law(s) changed only outside its part: %s (#103)"
                                       % (len(_narrow), ", ".join(_narrow[:3]))) if _narrow else ""))


_NET_MEMO = {"key": None, "finds": None, "files": None}
#: REG-3192 - the words a safety-net refusal starts with; heart_block_kind() reads it as neither STALE nor BLIND, so the
#: v3042 softening never lets an ordinary act through it
_NET_PHRASE = "the SAFETY NET found"


def _net_finds():
    """REG-3192 - this PC's safety-net finds that still speak for the files on disk. -> ({gate: find}, files) | (None, why)

    Read from the same census the heart reads (TV_HEART_CENSUS, the call-time seam), through heart2.net_finds - one rule
    for the lock and for the lane's status. may() asks this on every call, so a census with no finds (the usual case)
    is answered from its bytes alone, memoised on their digest; only a census that HAS finds reads the found gates'
    files, every call, because a find whose file changed is moot. UNKNOWN (an unreadable census) is (None, why): the
    global rule has already failed that closed."""
    try:
        import heart2 as _h2
        _census = os.environ.get("TV_HEART_CENSUS") or os.path.join(_h2.HERE, ".heart2.json")
        if not os.path.exists(_census):
            return {}, {}
        with io.open(_census, "rb") as _fh:
            raw = _fh.read()
        key = hashlib.sha256(raw).hexdigest()
        if _NET_MEMO["key"] == key and not _NET_MEMO["finds"]:
            return {}, {}
        st = json.loads(raw.decode("utf-8"))
        if not (isinstance(st, dict) and st.get("netFinds")) or not hasattr(_h2, "net_finds"):
            _NET_MEMO.update(key=key, finds={}, files={})
            return {}, {}
        files = dict(_h2.gate_files())
        finds = _h2.net_finds(st, list(files.items()))
        _NET_MEMO.update(key=key, finds=finds, files=files)
        return finds, files
    except Exception as _e:
        return None, "the safety net's finds could not be read (%s)" % type(_e).__name__


def _net_hits(lock, finds, files, texts=None):
    """REG-3192 - which of the safety net's finds close `lock`. -> [gate, ...] sorted. ONE rule for may() (_net_heart) and
    for the Fleet's word on what each find shuts (net_find_shuts, v3884), so the two can never disagree. A lock or route
    with no declared door keeps the global rule: every find closes it. A found law whose file will not read is counted,
    never skipped. `texts` memoises each found law's source across locks (net_find_shuts asks all of them)."""
    stems = LOCK_DOORS.get(lock)
    hit = []
    for n in sorted(finds):
        if stems is None:
            hit.append(n)
            continue
        if texts is not None and n in texts:
            text = texts[n]
        else:
            text = None
            f = files.get(n) if isinstance(files, dict) else None
            if f:
                try:
                    import heart2 as _h2
                    with io.open(f if os.path.isabs(f) else os.path.join(_h2.HERE, f), encoding="utf-8") as _fh:
                        text = _fh.read()
                except Exception:
                    text = None
            if texts is not None:
                texts[n] = text
        if text is None:                                          # a guard that will not read is counted, never skipped
            hit.append(n)
            continue
        if _net_case_guards(n, text, finds[n], lock, stems):
            hit.append(n)
    return hit


def net_find_shuts():
    """v3884 (GrokBot's v3882 pass on his Mac: "ready" beside "safety net: test_a_parallel_proof_is_the_same_proof RED · its
    locks shut" while every river lock was open) - WHAT EACH SAFETY-NET FIND ACTUALLY SHUTS on this PC.
    -> {gate: {"locks": [lock, ...], "routes": [route, ...]}} | {} (no find) | None (UNKNOWN: the finds could not be read)

    MEASURED on his Mac 11-08 ~11:05: its one find (that law, red under load at 09:09 and green alone) shut no lock and all
    nine routes - a route declares no door, so every find closes it (the global rule, broad in the safe direction). The
    Fleet chip said "its locks shut", which named neither. Asked through the very rule may() applies (_net_hits), lock by
    lock and route by route, so the chip can say "shuts 9 routes" or "shuts vault.apply" and never disagree with may().
    Laws that seat _heart_says_watched are answered by the global rule alone, as _net_heart is: {} here."""
    if _heart_says_watched is not _HEART_SAYS_WATCHED_REAL:
        return {}
    try:
        finds, files = _net_finds()
        if finds is None:
            return None
        if not finds:
            return {}
        texts = {}
        out = dict((n, {"locks": [], "routes": []}) for n in finds)
        for kind, names in (("locks", sorted(LOCKS)), ("routes", sorted(ROUTES))):
            for k in names:
                for n in _net_hits(k, finds, files, texts):
                    out[n][kind].append(k)
        return out
    except Exception:
        return None


def _net_heart(lock, ok, why):
    """REG-3191 / REG-3192 (his ruling 2026-11-05 (4): "a red/blind it finds goes to the fleet + BUGS and closes only the
    lock its law guards") - the heart's answer for `lock` once the safety net has spoken. -> (ok, why)

    A find closes a lock whose guard set holds its law - the #156 rule exactly (_guards_lock over LOCK_DOORS / LOCK_MARKS)
    - and no other. A lock or route with no declared door has no guard set to narrow to: it keeps the global rule, where
    any law guards it, so every find closes it (broad in the safe direction). A find never makes the census stale and
    never joins its BLIND list; his 2026-09-12 ruling (a BLIND closes every lock) stands for every other BLIND. Laws that
    seat _heart_says_watched ask the global rule and are answered by it alone, as _lock_heart does."""
    if _heart_says_watched is not _HEART_SAYS_WATCHED_REAL:
        return ok, why
    finds, files = _net_finds()
    if not finds:
        return ok, why
    hit = _net_hits(lock, finds, files)
    if not hit:
        return ok, why
    f0 = finds[hit[0]]
    return False, ("%s %d law(s) guarding %s failing on this PC (%s: %s) after they were opened on another tree's proofs "
                   "over the same bytes (REG-3191). Only the locks those laws guard close; the census is not made stale."
                   % (_NET_PHRASE, len(hit), lock, hit[0], f0.get("why") or f0.get("verdict")))


def may_on_merit(lock):
    """Permission for a READ THAT FEEDS A DISPLAY: this lock's own merit, never the heart's. -> (bool, why)

    ⚠⚠ WHY THIS EXISTS, measured on his live console at 01:55. v3049 put a `may()` seat in
    `printer.stream()`. Routine U then re-proved the census at 00:48 and found NINE BLIND
    instruments — none of which watch the river. `may()` fails closed on blindness for
    EVERYTHING (deliberately: a blind instrument is a gate that cannot fail), so the seat
    refused, `/api/river` answered `lanes.ok: false — printer.stream() could not answer`, and
    THE RIVER STRIP WENT DARK ON HIS SCREEN. Measured against :17772 directly: rows=0.

    The rule was not wrong; the place I applied it was. `printer.stream` is not destructive —
    self_arming's own note says it "earns trust in what it PRINTS rather than permission to
    act" — and the seat's own comment claims it "refuses on MERIT only". It did not, because
    BLIND is not STALE and the softening clause only covers stale. A reader that shows him what
    is there must not go blank because an unrelated gate lost its red-proof; the honest failure
    for a display is to SHOW the data and say what is unverified, never to show nothing.

    ⚠ THIS CAN NEVER ARM AN ACT. It refuses outright for any lock marked `destructive`, so it
    cannot be reached for by a caller that wants an easier yes on the vault, the prune or the
    frame release. Those still go through may(), where blind still fails closed.
    [[unknown-stays-unknown]] [[the-unjoined-end]]
    """
    spec = LOCKS.get(lock) or ROUTES.get(lock)
    if not spec:
        return False, "no such lock is declared — an undeclared surface is never permitted"
    if spec.get("destructive"):
        return False, ("%s is DESTRUCTIVE — merit alone never permits it. Ask may(), where a "
                       "blind instrument fails closed." % lock)
    rows, why = _rows()
    if rows is None:
        return False, "UNKNOWN: %s. An unreadable proof queue fails CLOSED." % why
    # the upstream chain still holds: merit includes what feeds this surface, exactly as in may().
    # Dropping the heart is the ONLY difference between the two functions.
    for pre in spec["after"]:
        st = score(pre, rows)
        if st.get("state") not in (OPEN, HARDENED):
            return False, ("blocked upstream: %s is %s — %s. Proving this surface in isolation "
                           "proves nothing about what feeds it." % (pre, st.get("state"), st.get("why")))
    st = score(lock, rows)
    return (st.get("state") in (OPEN, HARDENED)), st.get("why")


def may(lock):
    """May this surface act right now? -> (bool, why)

    THE ORDER IS CHECKED FIRST. A lock late in his chain reports its blocked prerequisite rather
    than its own score, so a high number is never mistaken for "nearly there".
    """
    # a route scores on the SAME arithmetic as a valve — one table lookup, one score()
    spec = LOCKS.get(lock) or ROUTES.get(lock)
    if not spec:
        return False, "no such lock is declared — an undeclared surface is never permitted"
    rows, why = _rows()
    if rows is None:
        return False, "UNKNOWN: %s. An unreadable proof queue fails CLOSED." % why
    # v2861 — AND THE HEART, in the same chain and for the same reason. See _heart_says_watched().
    _hok, _hwhy = _heart_says_watched()
    if not _hok:
        # #156 - the global rule refused; this lock's OWN guard laws decide when it declares a door
        _per = _lock_heart(lock, _hwhy)
        if _per is not None:
            _hok, _hwhy = _per
    # REG-3192 - a safety-net find closes only the locks it guards - asked whatever the heart said, because a STALE
    # refusal of an ordinary act is softened to merit below (v3042) and a find must not be softened with it
    _hok, _hwhy = _net_heart(lock, _hok, _hwhy)
    if not _hok:
        _hwhy = _hwhy or "UNKNOWN: the heart refused and gave no reason - which fails CLOSED"
    return _verdict(lock, spec, rows, _hok, _hwhy)


def _verdict(lock, spec, rows, _hok, _hwhy):
    """may()'s chain, given the proof rows and the heart's answer. -> (bool, why)

    ⚠ REG-1737 - ONE PATH FOR THE ACT AND FOR THE SURFACE THAT SHOWS IT. report() used to score the
    ledger alone, so with no census a lock read OPEN / HARDENED on the heart and the vault chip
    (open padlock) while may() refused it - "the heart has never run here" - and every reel stayed
    put. report() now asks THIS function for each row, so the padlock and the act cannot disagree.
    """
    if not _hok:
        # ⚠⚠ v3042 — A STALE PROVER IS NOT A SAFETY VERDICT ABOUT AN ORDINARY ACT. The census
        # goes stale whenever a GATE FILE changes, which is whenever anyone writes a gate — it
        # happened four separate times in one session of doing exactly that, and each time every
        # one of the nineteen locks answered may=False. Wiring ordinary actions to that would
        # mean editing a test takes features off his console until a ~38-minute re-prove.
        #
        # So the split is by REVERSIBILITY, and it is his ruling: an act that cannot be undone
        # keeps the full guarantee — a prover that has not caught up is reason enough to refuse
        # to delete footage, drop a ledger, mule items or spend money. An act that reports,
        # walks or decides refuses on MERIT alone, because "the instrument is out of date" says
        # nothing about whether THAT surface has earned the right to act.
        #
        # ⚠ BLIND IS NOT STALE AND NEVER SOFTENS. A blind instrument is a gate that cannot fail;
        # that IS a fact about supervision, and it fails closed for everything. [[stale-reading]]
        if not (heart_block_kind(_hwhy) == "stale" and not spec.get("destructive")):
            return False, _hwhy
    for pre in spec["after"]:
        s = score(pre, rows)
        if s.get("state") not in (OPEN, HARDENED):
            return False, ("blocked upstream: %s is %s — %s. Proving this surface in isolation "
                           "proves nothing about what feeds it." % (pre, s.get("state"), s.get("why")))
    s = score(lock, rows)
    # HARDENED is strictly stronger than OPEN — a surface that exceeded the bar may certainly act
    return (s.get("state") in (OPEN, HARDENED)), s.get("why")


def report():
    """Every lock, for a surface that must show its work. -> dict"""
    sp = _ledger_split()
    rows, why = sp["rows"], sp["why"]
    if rows is None:
        return {"ok": False, "why": why, "ledger": _ledger_summary(sp),
                "locks": [with_words({"lock": k, "state": UNKNOWN, "why": why, "permitted": False,
                                      "permittedWhy": why}) for k in sorted(LOCKS)]}
    # ⚠ ROUTES RIDE THE SAME REPORT, not a second one. The heart reads ONE self_arming.report(),
    # so a route appears beside the valves in the same four words and the corroborator sees them
    # as siblings — which is what he asked for: "all connected to the heart of the console
    # obviously.. so its all communicating and intertwined and integrated together properly".
    # ⚠⚠ REG-1737 - AND WHETHER IT MAY ACT, FROM may()'s OWN CHAIN. `state` is the evidence tier
    # (what the sabotage ledger earned); `permitted` is the answer the act gets (the heart and the
    # upstream chain as well). They differ on a PC whose census is missing, and the padlock used to
    # be drawn from `state` alone. Both are published; a surface draws open only when both agree.
    heart = _heart_for_report()
    _leg = sp["legacy"]
    # REG-3192 - each row's heart once the safety net has spoken, exactly as may() asks it (REG-1737)
    out = [_with_permit(score(k, rows, legacy=_leg), k, LOCKS[k], rows, _net_of_row(k, _heart_of(k, heart)))
           for k in sorted(LOCKS)]
    out += [dict(_with_permit(score(k, rows, legacy=_leg), k, ROUTES[k], rows, _net_of_row(k, heart)), kind="route")
            for k in sorted(ROUTES)]
    return {"ok": True, "locks": out,
            "open": len([x for x in out if x.get("state") in (OPEN, HARDENED)]),
            "hardened": len([x for x in out if x.get("state") == HARDENED]),
            "permitted": len([x for x in out if x.get("permitted")]),
            # REG-3215 - the valves' count in the act's words ("4 of 9 may act now (7 proven)"); routes are not valves
            "say": lock_counts([x for x in out if x.get("kind") != "route"])["say"],
            "heartOk": bool(heart[0]), "heartWhy": heart[1] or "",
            "ledger": _ledger_summary(sp),
            "total": len(out)}


def _ledger_summary(sp):
    """#181 (REG-2470) - which ledgers this report stands on, for a surface that must say so. -> dict

    File NAMES only, never paths: a report rides the status poll and the roster, and a path is a machine's."""
    legacy, here = sp.get("legacy") or [], sp.get("here") or []
    n = len(legacy)
    _took = set(_identity(r) for r in here if r.get("adopted"))
    taken = sum(1 for r in legacy if _identity(r) in _took)
    if not n:
        lsay = ""
    elif taken >= n:
        lsay = ("%d live trial row(s) in the shared ledger were measured before the per-PC split; THIS PC adopted all "
                "of them (--adopt-legacy-live) and counts them as its own. No other PC counts them." % n)
    else:
        lsay = ("%d live trial row(s) in the shared ledger were measured on an install this PC cannot identify, before "
                "the per-PC split - counted on no PC%s. Only the PC that measured them may take them, through "
                "`python3 tv/self_arming.py --adopt-legacy-live --reason \"<why>\" --confirm`."
                % (n, (" (this PC adopted %d of them)" % taken) if taken else ""))
    _hp, _hscope, _ = _here_where()
    return {"shared": os.path.basename(_ledger_path()), "here": os.path.basename(_hp),
            # REG-2473 - WHICH KIND of place it is, in words: one per PC (git's common dir), or one per checkout
            "hereScope": _hscope, "hereWhere": here_label(),
            "codeRows": sp.get("code") or 0, "hereRows": len(here),
            "hereAdopted": sum(1 for r in here if r.get("adopted")),
            "hereSay": (_HERE_NOTHING if not here else
                        "this PC has measured %d live trial row(s) of its own" % len(here)),
            "legacyLive": n, "legacyAdoptedHere": taken, "legacyLiveSay": lsay}


def _identity(r):
    """A row as it was banked, without the adoption mark - so an adopted copy matches its original. -> str"""
    return json.dumps(dict((k, v) for k, v in r.items() if k != "adopted"), sort_keys=True, ensure_ascii=False)


def adopt_legacy_live(reason, confirm=False):
    """#181 (REG-2471) - THE DOOR FOR THE PC THAT MEASURED THE LEGACY LIVE TRIALS. -> dict

    The split leaves the shared ledger's live rows counted on NO PC - including the Mac that measured them, which
    drops from HARDENED to OPEN on every surface whose third kind was live. Nothing in the rows says which install
    ran them, so no code may decide that; a person does, on that PC, and says why:

        python3 tv/self_arming.py --adopt-legacy-live --reason "<why this PC measured them>" --confirm

    It copies every legacy live row into THIS PC's own ledger, each marked `adopted` (the reason, the moment, the
    file it came from) and keeping its own `ts` - a trial is as old as what it measured, never as old as the copy.
    No reason -> REFUSED. No --confirm -> a DRY RUN that writes nothing and says what it would take. A row already
    adopted here is never written twice. The shared file's bytes are never touched. Nothing calls this on its own.
    [[unknown-stays-unknown]] [[stale-reading]]
    """
    why = str(reason or "").strip()
    if why.startswith("--"):
        why = ""                # a flag swallowed as the reason is no reason
    if not why:  # ADOPT-REASON
        return {"ok": False, "refused": True, "dryRun": not confirm, "wrote": 0, "would": None, "byLock": {},
                "say": ("REFUSED: adopting live trials needs --reason \"<why this PC measured them>\". Nothing in the "
                        "rows says which install ran them, so the person who knows must say it - nothing written.")}
    sp = _ledger_split()
    if sp["rows"] is None:
        return {"ok": False, "refused": True, "dryRun": not confirm, "wrote": 0, "would": None, "byLock": {},
                "say": ("REFUSED: the proof ledgers could not be read (%s) - UNKNOWN is not permission to copy "
                        "anything. Nothing written." % sp["why"])}
    have = set(_identity(r) for r in sp["here"])
    todo = [r for r in sp["legacy"] if _identity(r) not in have]  # ADOPT-ONCE
    by_lock = {}
    for r in todo:
        by_lock[str(r.get("lock"))] = by_lock.get(str(r.get("lock")), 0) + 1
    _list = ", ".join("%s %d" % kv for kv in sorted(by_lock.items())) or "none"
    # ⚠ REG-2473 - THE SENTENCE NAMES THE WHOLE PATH AND THE CHECKOUT IT RAN FROM, never a basename: run in the wrong
    # checkout, a basename reads as success. This sentence goes to his terminal only - report() carries names.
    dest = _here_path()
    where = "%s (%s; run from the checkout at %s)" % (dest, here_label(), os.path.dirname(HERE))  # ADOPT-WHERE
    if not confirm:  # ADOPT-DRY
        return {"ok": True, "refused": False, "dryRun": True, "wrote": 0, "would": len(todo), "byLock": by_lock,
                "dest": dest,
                "say": ("DRY RUN - nothing written. %d legacy live row(s) would be adopted into %s - %s; %d already "
                        "adopted here. Pass --confirm to write them." % (len(todo), where, _list,
                                                                         len(sp["legacy"]) - len(todo)))}
    stamp = {"by": "--adopt-legacy-live", "reason": why[:400], "at": int(time.time() * 1000),
             "from": os.path.basename(_ledger_path())}
    rows = [dict(r, adopted=dict(stamp)) for r in todo]  # ADOPT-KEEPS-TS
    if rows:
        with io.open(dest, "a", encoding="utf-8") as fh:  # ADOPT-WRITE
            fh.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return {"ok": True, "refused": False, "dryRun": False, "wrote": len(rows), "would": len(todo), "byLock": by_lock,
            "dest": dest,
            "say": ("adopted %d legacy live row(s) into %s - %s - each marked with this reason and keeping its own "
                    "age; %d were already here. The shared ledger was not touched."
                    % (len(rows), where, _list, len(sp["legacy"]) - len(todo)))}


def _adopt_cli(argv):
    """`--adopt-legacy-live [--reason WHY] [--confirm]` -> exit code: 0 done or dry run, 2 refused"""
    reason = ""
    for i, a in enumerate(argv):
        if a == "--reason":
            reason = argv[i + 1] if i + 1 < len(argv) else ""
        elif a.startswith("--reason="):
            reason = a[len("--reason="):]
    res = adopt_legacy_live(reason, confirm="--confirm" in argv)
    print(res["say"])
    return 0 if res.get("ok") else 2


#: REG-1737 - report() rides the status poll; asking the heart costs 0.2-0.6 s (the gate digest),
#: so the SURFACE reuses one answer for this long. may() never does: an act always asks fresh.
_HEART_SHOWN_TTL_S = 30.0
_HEART_SHOWN = {"at": None, "v": None}


def _heart_for_report(_now=None):
    """The heart's answer for a surface, at most _HEART_SHOWN_TTL_S old. -> (bool, why)"""
    now = time.monotonic() if _now is None else _now
    at, v = _HEART_SHOWN["at"], _HEART_SHOWN["v"]
    if v is not None and at is not None and 0 <= now - at < _HEART_SHOWN_TTL_S:
        return v
    try:
        v = _heart_says_watched()
    except Exception as e:
        v = (False, "UNKNOWN: the heart could not be asked (%s: %s) - which fails CLOSED"
                    % (type(e).__name__, str(e)[:80]))
    if not v[0] and not v[1]:
        v = (False, "UNKNOWN: the heart refused and gave no reason - which fails CLOSED")
    _HEART_SHOWN["at"], _HEART_SHOWN["v"] = now, v
    return v


def _heart_of(lock, heart):
    """#156 - the heart answer one report row stands on: the global one, or - when it refused - this lock's own,
    exactly as may() takes it, so the padlock and the act cannot disagree (REG-1737). -> (bool, why)"""
    if heart and heart[0]:
        return heart
    try:
        per = _lock_heart(lock, heart[1] if heart else None)
    except Exception:
        per = None
    return per if per is not None else heart


def _net_of_row(lock, heart):
    """REG-3192 - a report row's heart once the safety net has spoken, as may() takes it (REG-1737). -> (bool, why)"""
    if not heart:
        return heart
    try:
        return _net_heart(lock, heart[0], heart[1])
    except Exception as e:
        return False, "UNKNOWN: the safety net could not be asked (%s) - which fails CLOSED" % type(e).__name__


def _with_permit(row, lock, spec, rows, heart):
    """A report row plus may()'s verdict on it. -> a new dict"""
    row = dict(row)
    try:
        ok, why = _verdict(lock, spec, rows, heart[0], heart[1])
    except Exception as e:
        ok, why = False, "UNKNOWN: the verdict could not be taken (%s) - which fails CLOSED" % str(e)[:80]
    row["permitted"] = bool(ok)
    row["permittedWhy"] = why or ""
    # a short word a centred label can afford: WHAT holds a lock its evidence already earned
    row["heldBy"] = "" if ok else _held_by(why, heart)
    return with_words(row)


# REG-3215 - A LOCK ANSWERS TWO QUESTIONS, AND EACH GETS ITS OWN WORD. Measured on his Mac 2026-11-05 21:23: the
# heart's lock rows read "OPEN" for frame.release (35 of 35 distinct attacks refused, wilson 0.901 >= 0.722) while
# may() refused it (the proof census is STALE and the lock is destructive), and the count read "7 of 9 open" where
# 4 may act - so the Fleet card said "locks shut" and the Heart said OPEN about the same lock (GrokBot, #230 21:08).
# "OPEN" answered "is it proven strong enough" while his question is "may it act now". Every surface now leads with
# the ACT word - "may act", or "shut - <the one reason>" - and names the strength as what it is: "proven 0.90 >=
# 0.72". `state` and `permitted` stay on every row for older readers; these words are what a surface prints.
ACT_MAY = "may act"
ACT_SHUT = "shut"
#: what holds a lock, by heldBy, in the words a label can afford (control_ui.html's fan says the same four)
HELD_SAY = {"stale": "the prover is behind", "blind": "an instrument is blind",
            "heart": "not proven on this PC yet", "upstream": "blocked upstream"}


def _pair(a, b):
    """a and b at two decimals - more only when two would print them equal and they are not. -> (str, str)"""
    for d in (2, 3, 4):
        sa, sb = "%.*f" % (d, a), "%.*f" % (d, b)
        if sa != sb or a == b:
            break
    return sa, sb


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def proven_say(row):
    """The STRENGTH question - how far this lock's own evidence got - in its own words. -> str

    Never "OPEN": that is a door's word, and the door is the other question (act_say)."""
    st = str(row.get("state") or UNKNOWN).upper()
    sc = row.get(row.get("deciding") or "wilson")
    if sc is None:
        sc = row.get("wilson")
    bar = row.get("bar")
    if st in (OPEN, HARDENED):
        word = "hardened" if st == HARDENED else "proven"
        if _num(sc) and _num(bar):
            return "%s %s >= %s" % ((word,) + _pair(sc, bar))
        return word
    if st == UNPROVEN:
        if row.get("provable") is False:
            return "by design - nothing to sabotage"
        return "untested - nobody has tried to break it yet"
    if st == INCOMPLETE:
        nb = len(row.get("blindClaims") or [])
        return "not proven - %s never ran" % ("%d declared claim(s)" % nb if nb else "a declared claim")
    if st == LOCKED:
        if _num(sc) and _num(bar):
            a, b = _pair(sc, bar)
            if sc < bar:
                return "not proven %s < %s" % (a, b)
            return "not proven - %s >= %s, but its evidence is all of one sort" % (a, b)
        return "not proven"
    return "UNKNOWN - the proof could not be read"


def act_why(row):
    """The ACT question's one reason when the lock is shut; "" when it may act. -> str"""
    if row.get("permitted") is True:
        return ""
    if not isinstance(row.get("permitted"), bool):
        return "no verdict was taken, so it fails closed"
    by = row.get("heldBy")
    if by == "upstream":
        m = re.match(r"blocked upstream: (\S+) is ", str(row.get("permittedWhy") or ""))
        return "blocked upstream (%s)" % m.group(1) if m else HELD_SAY["upstream"]
    if by in HELD_SAY:
        return HELD_SAY[by]
    # its own evidence holds it: the reason is what the evidence still lacks (the figures are proven_say's)
    st = str(row.get("state") or UNKNOWN).upper()
    if st in (OPEN, HARDENED):
        return "the act's own check refused"
    if st == UNPROVEN:
        return "by design, nothing to sabotage" if row.get("provable") is False else "nobody has tried to break it yet"
    if st == INCOMPLETE:
        return "a declared claim never ran"
    if st == LOCKED:
        sc = row.get(row.get("deciding") or "wilson")
        sc = row.get("wilson") if sc is None else sc
        bar = row.get("bar")
        if _num(sc) and _num(bar) and sc >= bar:
            return "its evidence is all of one sort"
        return "its score is under the bar"
    return "the proof could not be read"


def act_say(row):
    """'may act', or 'shut - <the one reason>'. -> str"""
    why = act_why(row)
    return ACT_MAY if row.get("permitted") is True else "%s - %s" % (ACT_SHUT, why)


def with_words(row):
    """A report row plus the words a surface prints for its two questions. -> the same dict"""
    row["act"] = ACT_MAY if row.get("permitted") is True else ACT_SHUT
    row["actWhy"] = act_why(row)
    row["actSay"] = act_say(row)
    row["provenSay"] = proven_say(row)
    return row


def lock_counts(valves):
    """The valve tally every surface quotes. -> {"permitted": int|None, "proven", "total", "say"}

    `permitted` is None when any row carries no verdict: how many may act is then UNKNOWN, never 0."""
    valves = [v for v in (valves or []) if isinstance(v, dict)]
    total = len(valves)
    proven = sum(1 for v in valves if str(v.get("state") or "").upper() in (OPEN, HARDENED))
    if all(isinstance(v.get("permitted"), bool) for v in valves):
        permitted = sum(1 for v in valves if v.get("permitted") is True)
        say = "%d of %d may act now (%d proven)" % (permitted, total, proven)
    else:
        permitted = None
        say = "how many of %d may act now is UNKNOWN (%d proven)" % (total, proven)
    return {"permitted": permitted, "proven": proven, "total": total, "say": say}


def _held_by(why, heart):
    """Which thing refused? -> 'upstream' | 'stale' | 'blind' | 'heart' | 'evidence'"""
    w = why or ""
    if w.startswith("blocked upstream"):
        return "upstream"
    if not heart[0] and w == (heart[1] or ""):
        k = heart_block_kind(w)
        return k if k in ("stale", "blind") else "heart"
    return "evidence"


def main(argv):
    if "--adopt-legacy-live" in argv:
        return _adopt_cli(argv)      # #181 (REG-2471) - the only writer this command line has, and it asks first
    rep = report()
    print("SELF-ARMING LOCKS — %s" % ((rep.get("say") or "") if rep.get("ok") else "UNREADABLE: " + rep.get("why", "")))
    _led = rep.get("ledger") or {}
    if _led:
        print("  ledgers: %s (shared: proven in code, %d rows) + %s (this PC: %d rows, %d adopted) - %s"
              % (_led.get("shared"), _led.get("codeRows") or 0, _led.get("hereWhere") or _led.get("here"),
                 _led.get("hereRows") or 0, _led.get("hereAdopted") or 0, _led.get("hereSay") or ""))
        if _led.get("legacyLive"):
            print("  %s" % _led.get("legacyLiveSay"))
    for l in rep["locks"]:
        # ⚠ THE HEADER MUST PRINT THE FIGURE THAT DECIDED. It read `l["wilson"]` — the raw,
        # repetition-inflated score — beside a state derived from `wilsonByAttack`, so the glance
        # value and the deciding value disagreed by as much as 0.936 vs 0.646 on one row.
        w = l.get(l.get("deciding") or "wilson")
        if w is None:
            w = l.get("wilson")
        print("  %-9s %-20s %s" % (l.get("act"), l.get("lock"),
                                   ("wilson %.3f/%.3f%s" % (w, l["bar"],
                                    "" if l.get("deciding") != "wilsonByAttack"
                                    else " (per attack; raw %.3f)" % l["wilson"]))
                                   if w is not None else "no sabotage attempted"))
        print("            %s · %s" % (l.get("actSay") or "", l.get("provenSay") or ""))
        print("            %s" % (l.get("why") or ""))
    # a report is not a verdict: exit 0 always, because "nothing is open yet" is the CORRECT
    # state on a fresh tree and must not read as a broken build.
    return 0


if __name__ == "__main__":
    try:
        import console_safe as _cs
        _cs.enable()
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
