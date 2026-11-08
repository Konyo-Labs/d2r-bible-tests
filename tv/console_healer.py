#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""THE SCAR LEDGER AND THE HEALER — what the watchdog does with what it sees.

Konyo, 2026-08-24: "teach watchdog and eagle eye and give it the capabilities to see this so when
it happens in the future it can auto scar / auto heal / auto fix."

The eagle SEES and the watchdog LOOKS ON A TIMER. Neither of them REMEMBERS, and neither of them
ACTS. That gap is the whole reason he keeps finding the same thing twice: a fault that appears,
gets fixed, and comes back reads exactly like a fault appearing for the first time, so nothing in
the system can say the words "this is a REGRESSION" — the one sentence that would have changed
what I did.

So this module is two halves, and they are deliberately different sizes.

  THE LEDGER (auto-scar) — every red the watchdog sees is written down: what it was, when it FIRST
  appeared, when it last appeared, when it cleared, and HOW MANY TIMES IT HAS COME BACK. Cheap,
  safe, and it applies to every fault without exception. A fault that has cleared and returned is
  reported as a RETURN, with the count, forever.

  THE HEALER (auto-fix) — a NAMED remedy for a NAMED fault, and only where the repair is
  RE-DERIVABLE FROM EVIDENCE rather than an act of judgement. That line is his, from
  [[sweep-dont-ask]], and it is the whole safety argument: folding orphan frames into the reel
  whose stamp they already carry is arithmetic. Deciding which of his items to throw out is not.
  Most faults get NO remedy, and that is the correct answer, not a gap to fill later.

FOUR LAWS, each of which exists because its absence is a way this module could hurt him:

  1. RE-DERIVABLE ONLY. If the repair needs a preference, a threshold, or a guess about intent, it
     is not a remedy. It is a report.
  2. HEAL, RE-MEASURE, AND DISARM ON FAILURE. Every heal is followed by running the SAME check
     again. If the check is still red, that remedy is disarmed for the life of the process and the
     scar records that it was tried and did not work. A remedy that can be retried forever is a
     loop, and a loop that touches his files is the worst thing in this file.
  3. NOTHING IS DESTRUCTIVE. No remedy deletes, truncates or overwrites his data. The strongest
     thing any of them may do is MOVE a file into the place its own stamp says it belongs, or
     restore a backup this module itself wrote while the store was healthy.
  4. OPT-IN, AND SILENT MEANS OFF. Healing requires TV_AUTO_HEAL=1. With it unset the module still
     scars everything — remembering costs nothing and risks nothing — and reports what it WOULD
     have done, so the remedy can be read before it is ever armed.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def _root():
    """v2080 — GUARD THE PATH, NOT THE CALL SITE.

    A unit test called the real `_eagle_once()`, which calls `tend()` unconditionally — and so a
    test wrote HIS ledger and HIS three `.healer_bak` files. Worse than a stray write: that reading
    contained no failures, so under the old clearing rule every live scar was stamped CLEARED and
    the next real watchdog tick would have announced "THIS HAS COME BACK 5 time(s)" about faults
    that never went away.

    Isolating that one test would fix that one test. The tree's existing rule is stronger and is
    why the vault ledgers survived the same night: resolve the PATH through the fixture root, so a
    test can never reach the real file no matter which call site it goes through.
    [[feedback-fixtures-never-touch-live-data]]
    """
    env = os.environ.get("TV_SCAR_ROOT")
    if env:
        return env
    try:
        sys.path.insert(0, HERE)
        import tv_diablo as _tvd
        return _tvd._fixture_root(HERE)
        # ⚠⚠ v2788 — NARROWED FROM `except Exception`. A blanket catch here also swallowed a
        # runtime failure OF THE RULE ITSELF and answered HERE — his live tree — to a caller that
        # had explicitly asked for a fixture world. `shadow_ledger._ledger_path` and
        # `retro_gate._ledger_path` already carry the correct template and say why: *"If the root
        # rule is broken that must surface, not resolve to his tree."* ImportError means tv_diablo
        # genuinely is not importable and HERE is then the honest answer; anything else must
        # propagate. Found by a census, not by hand. [[copy-drift]] [[unknown-stays-unknown]]
    except ImportError:
        return HERE


LEDGER = os.path.join(_root(), ".console_scars.json")

# The number in a why-string is the SIZE of a fault, never its identity: "2385 frame(s) belong to
# no reel" and "12 frame(s) belong to no reel" are one scar returning, not two scars. Fingerprint
# on the shape with the digits knocked out, or every recurrence reads as a first sighting and the
# ledger can never say the word REGRESSION — which is the only thing it is for.
_NUM = re.compile(r"\d+(?:\.\d+)?")


def fingerprint(check, why):
    return "%s|%s" % (check, _NUM.sub("#", (why or "").strip())[:140])


_LEDGER_UNREADABLE = False


def _load():
    """v2080 — ABSENT AND UNPARSABLE ARE NOT THE SAME EMPTY, HERE EITHER.

    This module was shipped in the same commit that split those two states apart in
    reel_retention and frame_authority, and then made the identical collapse in its own store: any
    exception returned `{"scars": {}}`, and the next `_save` overwrote the corrupt bytes. One stray
    byte in the ledger therefore erased every scar's `firstSeen`, its `returns` count — and its
    `heal.disarmed` flag, which made ledger corruption the only thing in the system that can
    RE-ARM a remedy LAW 2 disarmed for lying. [[unknown-stays-unknown]]
    """
    global _LEDGER_UNREADABLE
    if not os.path.exists(LEDGER):
        _LEDGER_UNREADABLE = False
        return {"scars": {}}
    try:
        with io.open(LEDGER, encoding="utf-8") as fh:
            blob = json.load(fh)
        # v2082 — VALID JSON IS NOT THE SAME AS A LEDGER. The flag was cleared BEFORE the shape was
        # tested, so a file holding a valid JSON list read as healthy-and-empty: no .corrupt kept,
        # every firstSeen, every returns count and every heal.disarmed silently gone — including the
        # one flag this module names as the only thing that can re-arm a remedy LAW 2 disarmed for
        # lying. One line from the defect the same commit closed.
        _LEDGER_UNREADABLE = not isinstance(blob, dict)
        return blob if isinstance(blob, dict) else {"scars": {}}
    except Exception:
        _LEDGER_UNREADABLE = True
        return {"scars": {}}


def _save(blob):
    # Never write over history nobody could read. The corrupt bytes are set aside under a name that
    # does not collide, and the fresh ledger starts beside them rather than on top of them.
    if _LEDGER_UNREADABLE:
        keep = LEDGER + ".corrupt"
        n = 0
        while os.path.exists(keep):
            n += 1
            keep = "%s.corrupt.%d" % (LEDGER, n)
        try:
            os.replace(LEDGER, keep)
        except OSError:
            return                      # cannot even move it — write nothing rather than destroy
        print("  \U0001f985 the scar ledger would not parse; kept as %s and started a new one"
              % os.path.basename(keep), flush=True)
    tmp = LEDGER + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(blob, indent=1, ensure_ascii=False))
    os.replace(tmp, LEDGER)


def record(rows, now_ms=None):
    """Fold one watchdog reading into the ledger. Returns the scars that are RED right now, each
    carrying its own history, so the caller can tell a first sighting from a return.

    v2080 — A SCAR CLEARS WHEN ITS CHECK GOES GREEN, NOT WHEN ONE PHRASING OF IT DISAPPEARS.

    The first cut stamped `clearedAt` on any scar whose FINGERPRINT was absent from this reading.
    But one check can emit several shapes: `disk headroom` says "N GB free — BELOW the 8GB floor"
    under the floor and "N GB free — your last N reels averaged ... about N hour(s) of recording"
    above it. A disk oscillating across 8 GB therefore makes shape A vanish (recorded as CLEARED)
    while shape B appears — and back again — with the check RED the entire time.

    MEASURED ON HIS LIVE LEDGER, which is how this was found: two `disk headroom` fingerprints,
    each reporting `returns=6`. Twelve returns, none of which happened. The return count is the one
    number this module exists to produce, and it was counting a rephrasing.

    So the CHECK's state decides clearing, and the fingerprint still decides identity — two
    genuinely different failures of one check stay two scars, and neither can clear the other.
    """
    now = int(now_ms if now_ms is not None else time.time() * 1000)
    blob = _load()
    scars = blob.setdefault("scars", {})
    red_now = []
    seen_keys = set()
    # Which CHECKS are red in this reading, regardless of how they phrased it. A check absent from
    # the reading entirely (the cheap subset skipped it) is NOT evidence that it went green.
    red_checks = set(r.get("check") for r in (rows or []) if r.get("state") == "missing")
    # v2082 — AND ONLY AN **OK** READING CLEARS. The first cut took `measured` to be every check in
    # the reading, so a check that came back UNKNOWN was "measured and not red" and its scar was
    # stamped CLEARED — manufacturing the exact "THIS HAS COME BACK 1 time(s)" this function was
    # written to stop, through a different door and needing no exception to fire.
    #
    # It is an everyday path, not an edge: `board is claimed` reports UNKNOWN whenever the board
    # window simply is not open, `version drift` when the console does not answer inside 4s, and
    # `art corpus` on any machine without an art dir — all three in the CHEAP subset the eagle runs
    # every ten minutes. Close the board on an unclaimed world, reopen it, and the ledger reports a
    # regression that never happened.
    #
    # "I looked and it is fine" is the only reading that may clear a scar. UNKNOWN is not that.
    # [[unknown-stays-unknown]]
    measured = set(r.get("check") for r in (rows or []) if r.get("state") == "ok")
    for r in rows or []:
        if r.get("state") != "missing":
            continue
        k = fingerprint(r.get("check"), r.get("why"))
        seen_keys.add(k)
        s = scars.get(k)
        if s is None:
            s = {"check": r.get("check"), "why": r.get("why"), "firstSeen": now, "lastSeen": now,
                 "times": 1, "clearedAt": None, "returns": 0,
                 "heal": {"tried": 0, "worked": 0, "disarmed": False, "lastSaid": None}}
            scars[k] = s
        else:
            # A scar that had CLEARED and is red again is a regression, and the count of returns is
            # the number he should be shown. It is never reset.
            if s.get("clearedAt"):
                s["returns"] = int(s.get("returns") or 0) + 1
                s["clearedAt"] = None
            s["lastSeen"] = now
            s["times"] = int(s.get("times") or 0) + 1
            s["why"] = r.get("why")
        red_now.append(dict(s, key=k))
    # A scar clears only when its CHECK was measured this round and came back not-red. A check that
    # this reading never ran (the watchdog uses the cheap subset) leaves its scars exactly as they
    # were — "nobody looked" is not "it is fixed". [[unknown-stays-unknown]]
    for k, s in scars.items():
        if k in seen_keys or s.get("clearedAt"):
            continue
        chk = s.get("check")
        if chk in measured and chk not in red_checks:
            s["clearedAt"] = now
    _save(blob)
    return red_now


def history(key=None):
    scars = _load().get("scars") or {}
    return scars.get(key) if key else scars


def says(scar):
    """One line a person can act on, and the RETURN count is the part that matters."""
    n = int(scar.get("returns") or 0)
    if n:
        return "%s — THIS HAS COME BACK %d time(s) after clearing. %s" % (
            scar.get("check"), n, scar.get("why") or "")
    return "%s — %s" % (scar.get("check"), scar.get("why") or "")


# ─────────────────────────────────────────────────────────────────────────────────────────────
# THE REMEDIES. Each is (why it is safe, callable) and each returns (did_something, said).
#
# Read the "why it is safe" line as the contract. If a remedy is ever changed so that its line
# stops being true, the remedy is wrong, not the line.
# ─────────────────────────────────────────────────────────────────────────────────────────────

def _remedy_fold_orphan_footage():
    """Frames of a session that died before sealing sit loose in hist/, where no lane and no
    deleter can see them. Every one of those files CARRIES ITS OWN SESSION STAMP in its name, so
    the reel it belongs to is read off the evidence, never chosen. Nothing is deleted: the frames
    move into the reel directory their own stamp names."""
    sys.path.insert(0, HERE)
    # v2080 — AND NOT WHILE ANYTHING IS IN FLIGHT. orphan_fold now refuses a still-growing window on
    # its own (the structural fix, which protects the CLI too), but this remedy runs UNATTENDED on a
    # timer and must not lean on one guard for something with no undo. If the console can be asked
    # what is running, ask it; if it cannot be asked, that is not permission.
    try:
        import control_app as _ca
        # v2128 (#33) — ASK WHAT IS IN FLIGHT, not whether the DELETER is armed. Folding loose
        # frames into the reel their own stamp names deletes nothing, so borrowing
        # retention_may_act meant TV_AUTO_PRUNE=0 — the documented way to stop the prune — also
        # silenced the fold, with a refusal naming a feature the fold is not. [[copy-drift]]
        ok, why = _ca.nothing_in_flight("folding now would move frames out from under it")
        if not ok:
            return None, "not folding while %s" % why
    except Exception:
        pass          # no console in this process — orphan_fold's own time guard still applies
    import orphan_fold as of
    # TV_HIST or nothing. `of.plan()` with no argument reads the module's OWN default hist dir,
    # which on a test tree is HIS footage and on a scratch tree is the wrong directory entirely —
    # the remedy then reports "nothing loose to fold" about a place nobody asked about. Exactly the
    # defect that put seven cases on his live reels last night.
    # [[feedback-fixtures-never-touch-live-data]]
    p = of.plan(hist_dir=(os.environ.get("TV_HIST")
                          or os.path.join(HERE, "frames", "hist")))
    # The key is `clusters`, and `frames` on each is a COUNT, not a list. The first cut of this
    # remedy read `p["groups"]` — a field orphan_fold has never had — so it returned False every
    # time and reported "nothing loose to fold" about 12 frames that were sitting right there. A
    # remedy that can never fire, wearing a clean answer. Found by running it, not by reading it.
    # [[plumbing-with-no-tap]] [[the-unjoined-end]]
    if not p.get("ok"):
        return False, "orphan_fold could not read the footage: %s" % str(p.get("why"))[:90]
    ok = [c for c in (p.get("clusters") or []) if c.get("eligible") and c.get("frames")]
    refused = [c for c in (p.get("clusters") or []) if not c.get("eligible") and not c.get("join")]   # v3883 - a join is no refusal
    if not ok:
        return None, ("nothing eligible to fold"
                       + (" — %d cluster(s) REFUSED for overlapping an existing reel, which would "
                          "forge a second session id for one recording" % len(refused)
                          if refused else ""))
    n = sum(int(c.get("frames") or 0) for c in ok)
    res = of.apply_plan(p, yes=True)
    if isinstance(res, dict) and res.get("ok") is False:
        return False, "orphan_fold refused: %s" % str(res.get("why"))[:110]
    return True, ("folded %d loose frame(s) into %d reel(s) named by their own stamps%s"
                  % (n, len(ok),
                     "; %d refused for overlapping an existing reel" % len(refused)
                     if refused else ""))


def _remedy_restore_a_vault_store():
    """A store that will not parse is restored ONLY from a backup THIS MODULE wrote while the same
    store was parsing. The corrupt file is kept beside it — under a name that does not collide with
    an earlier one — because nothing of his is ever thrown away to make a check go green.

    The row protection is in back_up_healthy_stores, not here: a backup is only ever refreshed from
    a store that PARSED and had NOT SHRUNK, so the bytes this restores were, at the moment they were
    banked, at least as many rows as anything seen since. Saying it here as if this function checked
    it would be publishing a check nobody performs."""
    names = ("vault_accum.json", "vault_seen.json", "vault_swept.json")
    fixed = []
    for n in names:
        fp = os.path.join(_root(), n)
        bak = fp + ".healer_bak"
        if not os.path.exists(fp) or not os.path.exists(bak):
            continue
        try:
            with io.open(fp, encoding="utf-8") as fh:
                json.load(fh)
            continue                       # it parses; nothing to restore
        except Exception:
            pass
        try:
            with io.open(bak, encoding="utf-8") as fh:
                good = json.load(fh)
        except Exception:
            continue                       # the backup is no better; leave both alone
        # v2080 — AND THE FIX FOR "IT ADVERTISES A CHECK IT DOES NOT PERFORM" IS THE WORDS.
        # The docstring and the REMEDIES contract both promised "only when that backup holds AT
        # LEAST AS MANY ROWS", and there was no comparison here. My first correction ADDED one —
        # and a sabotage proved it could never run: a store that parses is skipped four lines above
        # (nothing to restore), and a store that does not parse has no countable rows, so the
        # comparison is unreachable from both directions. A branch that cannot execute is not a
        # guard, it is a guard-shaped comment. [[feedback-threshold-above-the-ceiling]]
        #
        # The row protection is real and it lives in back_up_healthy_stores: a smaller ledger never
        # overwrites a larger backup, which is tested and has been seen red. So the promise moves to
        # where the code is, rather than a check moving to where the promise was.
        # v2080 — AND SAY HOW OLD THE BYTES ARE. A backup is only refreshed when the live store
        # parses AND has not shrunk, so it can legitimately be days behind — a restore reporting
        # only a ROW COUNT reads as "recovered" when it may be "recovered to last Tuesday". A
        # reading carries the age of the thing it measured, never the age of the read.
        # [[stale-reading]]
        try:
            age_s = max(0.0, time.time() - os.path.getmtime(bak))
        except OSError:
            age_s = None
        when = ("age UNKNOWN" if age_s is None else
                ("%.0f minute(s) old" % (age_s / 60.0) if age_s < 5400 else
                 "%.1f hour(s) old" % (age_s / 3600.0)))
        # ...and never on top of an earlier .corrupt. A second corruption used to overwrite the
        # first — potentially his only unbacked bytes — under a message saying it was KEPT.
        keep = fp + ".corrupt"
        _n = 0
        while os.path.exists(keep):
            _n += 1
            keep = "%s.corrupt.%d" % (fp, _n)
        os.replace(fp, keep)
        with io.open(fp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(good, ensure_ascii=False))
        fixed.append("%s (%d row(s), backup %s; corrupt copy kept as %s)" % (
            n, len(_rows_of(good)), when, os.path.basename(keep)))
    if not fixed:
        return None, "no store had a healthy backup to come back from"
    return True, "restored " + "; ".join(fixed)


def _rows_of(blob):
    for k in ("owned", "rows"):
        if isinstance(blob, dict) and k in blob:
            v = blob[k]
            return v if hasattr(v, "__len__") else []
    return blob if hasattr(blob, "__len__") else []


def back_up_healthy_stores():
    """The half of the vault remedy that has to run BEFORE the fault.

    A repair needs something to repair FROM, and nothing in this tree wrote one. So every time the
    watchdog finds the stores healthy, the healthy bytes are copied aside. This is not a heal — it
    is the reason a heal can exist later, and it runs whether or not healing is armed."""
    kept = 0
    for n in ("vault_accum.json", "vault_seen.json", "vault_swept.json"):
        fp = os.path.join(_root(), n)
        if not os.path.exists(fp):
            continue
        try:
            with io.open(fp, encoding="utf-8") as fh:
                blob = json.load(fh)
        except Exception:
            continue                       # only healthy bytes are ever banked
        bak = fp + ".healer_bak"
        try:
            # Never bank a SMALLER ledger over a larger one. A store that has just lost rows is
            # exactly the moment a backup is most valuable and most dangerous to overwrite.
            if os.path.exists(bak):
                with io.open(bak, encoding="utf-8") as fh:
                    if len(_rows_of(json.load(fh))) > len(_rows_of(blob)):
                        continue
            tmp = bak + ".tmp"
            with io.open(tmp, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(blob, ensure_ascii=False))
            os.replace(tmp, bak)
            kept += 1
        except Exception:
            pass
    return kept


def _remedy_clear_a_stuck_theatre():
    """A theatre stage that opened and never filled leaves the console BLACK until he quits it.

    ⚠ v2235 (#44) — HE FOUND THIS ONE HIMSELF, TWICE, WITH SCREENSHOTS, because nothing in the tree
    could see it. `thOpen()` opens the stage BEFORE the network by design (v859: "pixels BEFORE
    network") and then awaited /api/sessions with no timeout — so an auto-relaunch replacing the
    server mid-fetch left a full-bleed black rectangle up indefinitely. Hovering still painted a
    tooltip, which is what told him it was not a crash.

    v2228 fixed the CAUSE (bounded fetch, the stage closes on failure, a 12s self-heal) and gave the
    console POST /api/ui_fault so it can say so. This is the third half: a fault that KEEPS COMING
    BACK is a regression, and the eagle counts returns — but counting without acting is what #167
    was about.

    ⚠ IT CANNOT REACH INTO HIS WINDOW, and must not pretend to. The console UI heals itself
    client-side; the only thing this can honestly do is CLEAR THE FAULT RECORD once the condition
    has stopped recurring, so a healed lane stops reading as a standing red. It deletes nothing he
    owns and touches no ledger. Returns (ok, said)."""
    sys.path.insert(0, HERE)
    try:
        import control_app as _ca
    except Exception as e:
        return False, "control_app did not import: %s" % str(e)[:70]
    rows, why = _ca.ui_faults_recent(1)          # the LAST HOUR only
    if rows is None:
        # unreadable is UNKNOWN, and UNKNOWN is never a licence to act
        return False, why or "the fault log is unreadable, so nothing can be concluded"
    stuck = [r for r in rows if str(r.get("kind") or "").startswith("theatre-")]
    if stuck:
        # still happening — say so and leave it alone. A remedy that "fixes" a live fault by
        # erasing its record is the worst possible shape.
        return False, ("the console has healed itself from %d theatre fault(s) in the last hour; "
                       "the record stays until an hour passes clean" % len(stuck))
    return True, ("no theatre fault in the last hour — the console self-healed and the condition "
                  "has stopped recurring")


REMEDIES = {
    # v2235 (#44) — the newest fault the console can report about ITSELF. Keyed on the CHECK NAME,
    # like its siblings. It clears a record that has stopped recurring; it never reaches into his
    # window and never touches a ledger.
    "console UI faults": ("clears a theatre-fault record only after a clean hour; nothing he owns "
                          "is touched and the live console heals itself client-side",
                          _remedy_clear_a_stuck_theatre),
    "footage has a reel": ("the reel is read off each frame's own stamp; nothing is deleted",
                           _remedy_fold_orphan_footage),
    "vault stores": ("restores only from a backup this module wrote while the store parsed and had "
                     "not shrunk; every corrupt copy is kept",
                     _remedy_restore_a_vault_store),
}

# Everything else is deliberately absent, and the absences are the interesting part:
#   version drift    the console decides that itself (drift_may_relaunch), because only IT knows
#                    whether he is filming — a restart mid-session orphans the frames it kills.
#   art corpus       the sprites are genuinely gone. Extracting them from CASC is a job, not a fix.
#   visual lock      a code regression. There is no safe machine repair for "someone changed the
#   locked lanes     rules" — the repair is a person reading a diff, and the scar is what gets them
#                    there. A module that silently rewrote code to make its own gate go green would
#                    be the single most dangerous thing in this tree.
#   disk headroom    deleting his footage is his call and always will be.

_DISARMED = set()


def heal(scar, recheck=None):
    """Try the named remedy for one scar. Returns (state, said) where state is one of
    'healed' / 'no-remedy' / 'not-armed' / 'disarmed' / 'failed' / 'still-red'."""
    check = scar.get("check")
    entry = REMEDIES.get(check)
    if not entry:
        return "no-remedy", "there is no safe machine repair for %r — it needs a person" % check
    why_safe, fn = entry
    if check in _DISARMED or (scar.get("heal") or {}).get("disarmed"):
        return "disarmed", "the remedy for %r was tried and did not clear the check" % check
    if os.environ.get("TV_AUTO_HEAL") != "1":
        return "not-armed", "would run: %s (%s). Arm with TV_AUTO_HEAL=1" % (check, why_safe)
    try:
        did, said = fn()
    except Exception as e:
        _note_heal(scar, worked=False, said="the remedy threw: %s" % str(e)[:110], disarm=True)
        _DISARMED.add(check)
        return "failed", "the remedy for %r threw: %s" % (check, str(e)[:110])
    if did is None:
        # v2080 — NOTHING TO DO IS NOT A FAILURE. `_remedy_fold_orphan_footage` returns a refusal
        # when every cluster overlaps an existing reel — that is orphan_fold's DESIGNED answer, the
        # correct one, and treating it as a failed heal disarmed the remedy permanently. And the
        # disarm outlives the process: it is written to the ledger, and nothing anywhere sets it
        # back to False. So a remedy could be retired forever by working correctly.
        return "nothing-to-do", said
    if not did:
        _note_heal(scar, worked=False, said=said, disarm=True)
        _DISARMED.add(check)
        return "failed", said
    # LAW 2. A heal is not believed because it returned — it is believed because the check that
    # was red is now green. Anything else is a remedy grading its own homework.
    if recheck is not None:
        try:
            state, why = recheck()
        except Exception as e:
            state, why = "unknown", str(e)[:110]
        if state == "missing":
            _note_heal(scar, worked=False, said="ran (%s) and the check is STILL red: %s" % (
                said, why), disarm=True)
            _DISARMED.add(check)
            return "still-red", "%s — but %r is still red: %s" % (said, check, why)
    _note_heal(scar, worked=True, said=said, disarm=False)
    return "healed", said


def _note_heal(scar, worked, said, disarm):
    blob = _load()
    s = (blob.get("scars") or {}).get(scar.get("key") or fingerprint(scar.get("check"),
                                                                    scar.get("why")))
    if s is None:
        return
    h = s.setdefault("heal", {"tried": 0, "worked": 0, "disarmed": False, "lastSaid": None})
    h["tried"] = int(h.get("tried") or 0) + 1
    if worked:
        h["worked"] = int(h.get("worked") or 0) + 1
    if disarm:
        h["disarmed"] = True
    h["lastSaid"] = said
    h["lastAt"] = int(time.time() * 1000)
    _save(blob)


def tend(rows, recheck_for=None):
    """The whole cycle, for the watchdog to call: scar everything red, bank the healthy stores,
    then attempt the remedies that exist. Returns a list of {scar, state, said}."""
    red = record(rows)
    if not any(r.get("check") == "vault stores" for r in red):
        back_up_healthy_stores()
    out = []
    for s in red:
        rc = (recheck_for or {}).get(s.get("check"))
        state, said = heal(s, recheck=rc)
        out.append({"scar": s, "state": state, "said": said})
    return out


def main(argv=None):
    try:
        from console_safe import enable as _console_safe
        _console_safe()
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    scars = history()
    if not scars:
        print("the ledger is empty — nothing red has been seen yet")
        return 0
    live = [s for s in scars.values() if not s.get("clearedAt")]
    old = [s for s in scars.values() if s.get("clearedAt")]
    if live:
        print("RED NOW (%d):" % len(live))
        for s in sorted(live, key=lambda x: -int(x.get("returns") or 0)):
            print("  • " + says(s))
            h = s.get("heal") or {}
            if h.get("tried"):
                print("      heal: tried %d, worked %d%s — %s" % (
                    h["tried"], h.get("worked") or 0,
                    ", DISARMED" if h.get("disarmed") else "", h.get("lastSaid") or ""))
    if old:
        print("CLEARED (%d), kept so a return can be named a return:" % len(old))
        for s in old:
            print("  · %s — seen %d time(s), %d return(s)" % (
                s.get("check"), s.get("times") or 0, s.get("returns") or 0))
    return 1 if live else 0


if __name__ == "__main__":
    sys.exit(main())
