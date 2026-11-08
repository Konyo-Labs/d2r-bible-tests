#!/usr/bin/env python3
"""THE ONE DELETION AUTHORITY over his footage.

Three things could delete frames or reels, and each carried its own private idea of "safe":

  · control_app._prune_once  — kept a frame only when it LOOKED different from the one before
                               (sig_diff <= 0.02, whole frame, tol=28). A hover tooltip — the ONLY
                               place D2R ever writes an item name — moves that number by LITERALLY
                               ZERO. Measured on his own reel: three frames naming three different
                               grand charms are pairwise 0.00000 apart. v2058 turned it off after a
                               replay showed it dropping 67 frames including FOUR witness frames,
                               each the second session for one of his seven owned rows.
  · reel_retention           — asked the vault lane and the durable stores. The right questions, in
                               the one place the other two never called.
  · space_warden             — build artifacts only, behind a NEVER list. Correct, and out of scope.

None of them asked the same question, and only one of them asked the vault lane at all.
This module is that one question, asked once, in one place.

THE RULE, and it is his, in his own words:

    "after the sweep ... data needs to be extracted and ledgered and counted for items as
     witnesses so when they get pruned they continue to exist on record"
    "the ledger should tell us when it was seen by AI so we can see visually in retro and
     visually debug in retro if needed surgically anything"

Those two pull against each other, and the resolution IS the design: a frame that WITNESSED a row is
the visual proof of that row and is never deleted; a frame from a sealed reel that witnessed nothing
has already given up everything it had. So the question is never "does this frame look like the last
one" — it is **IS THIS FRAME EVIDENCE**. sig_diff cannot answer that at any tolerance, which is why
replacing it was the fix rather than retuning it.

Every predicate errs toward KEEPING. An unreadable store, an unparsable name, a missing index all
resolve to "do not delete". "I could not tell" must never mean "delete it", because there is no
un-delete for footage — the same asymmetry that makes the throw-out bar higher than the keep bar.
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:                                   # the report below prints a box-file glyph, and a CLI that
    from console_safe import enable    # crashes while REPORTING makes a clean tree exit non-zero
    enable()
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))


def _hist_dir(hist_dir):
    """Default hist comes from the one door. This module still creates nothing.

    A caller that passed a path keeps it (fixtures, TV_HIST harnesses). Looking
    at the live tree must not provision it — that is machine_tree.establish(),
    which only the film/archive writers call.
    """
    if hist_dir:
        return hist_dir
    try:
        import machine_tree as _mt
        p = _mt.footage_hist()
        if p:
            return p
    except Exception:
        pass
    return os.path.join(HERE, "frames", "hist")

KEEP_RECENT = 16           # never touch the newest SIXTEEN reels, whatever any ledger says
#: ⚠ 2026-09-29 — 8 -> 16 with reel_retention.KEEP_RECENT (his "instead of 8 last reels it reads 16"). Only the
#: reel deleter narrows under disk pressure (whole EXTRACTED reels go); this frame stripper never does, which is
#: the safe direction test_the_two_deleters_share_one_window describes - no reel is ever left gutted.
#: ⚠ v2875 — 5 -> 8 with reel_retention.KEEP_RECENT, on his instruction. These two MUST
#: agree: one guards reels, the other the frames inside them, and a frame floor lower than
#: the reel floor would empty a reel the retention rule swore never to touch.
#: test_the_two_keep_floors_agree holds them together. [[copy-drift]]
DURABLE_STORES = ("vault_accum.json", "vault_seen.json")
SEAL_STORE = "vault_swept.json"


def _load(root, fn):
    """None means COULD NOT READ, which is not the same as empty. Callers must treat it as a hold."""
    return _load_state(root, fn)[0]


def _load_state(root, fn):
    """(blob, state) where state is 'absent' | 'ok' | 'unreadable'.

    v2079 — AND THE THREE ARE NOT TWO. `_load` folded ABSENT and UNREADABLE into one None, and
    `witness_index` then reported ok=False for both. On a tree that has simply never run a vault
    sweep — every test fixture, and any fresh install — the durable stores are absent, so the
    authority declared itself unreliable and a caller that honours `ok` holds every reel forever.

    That is not a hypothetical: it went red across ~17 reel_retention cases within one gate run of
    the change that started honouring `ok`. The over-correction is the same defect as the one it
    was correcting, pointed the other way — "I could not read it" and "there is nothing to read"
    are opposite facts and neither may borrow the other's answer.
    [[unknown-stays-unknown]] [[gate-blind-to-unexercised-input]]
    """
    fp = os.path.join(root, fn)
    if not os.path.exists(fp):
        return {}, "absent"
    try:
        with open(fp, encoding="utf-8") as fh:
            return json.load(fh), "ok"
    except Exception:
        return None, "unreadable"


def _rows_of(blob):
    if not isinstance(blob, dict):
        return []
    rows = blob.get("owned") if "owned" in blob else blob.get("rows")
    return [r for r in (rows or []) if isinstance(r, dict)]


def witness_index(root=None):
    """Which FRAMES and which SESSIONS are named as witnesses in the durable stores.

    A witness frame is the pixels behind a row he can see in the vault. Deleting one does not make
    the row wrong — the row survives, that is the point of extracting — but it destroys the only
    way to ever answer "show me why you think I own this", which is the retro-debugging he asked
    for by name.

    `ok` is False when ANY store was unreadable. A caller that deletes on a partial index would be
    deleting on the strength of a file it could not open.
    """
    root = root or HERE
    frames, sessions, ok, seen = set(), set(), True, {}
    absent = 0
    for fn in DURABLE_STORES:
        blob, state = _load_state(root, fn)
        if state == "unreadable":
            # Only THIS makes the index partial. An absent store contributes nothing and that is a
            # measurement, not a gap — see _load_state.
            ok = False
            seen[fn] = None
            continue
        if state == "absent":
            seen[fn] = 0
            absent += 1
            continue
        n = 0
        for r in _rows_of(blob):
            for w in (r.get("witnesses") or []):
                if not isinstance(w, dict):
                    continue
                if w.get("frame"):
                    frames.add(os.path.basename(str(w["frame"])))
                    n += 1
                if w.get("session"):
                    sessions.add(str(w["session"]))
        seen[fn] = n
    # Frames a WATCHED / PROVEN / HARDENED item stands on. A ledger that will not parse is
    # UNKNOWN — ok goes false and the deleter holds every frame. An absent ledger cites nothing.
    try:
        import vault_evidence as _ve
        _cited = _ve.cited_frames(os.path.join(root, "vault_accum.json"))
    except Exception:
        _cited = None
    if not isinstance(_cited, dict) or _cited.get("frames") is None:
        ok = False
        cited = None
    else:
        cited = set(_cited.get("frames") or [])
    # v2080 — `ok` alone is not enough for a FRAME deleter, and splitting absent from unreadable
    # exposed that. `ok` answers "is my picture complete"; a tree where NO durable store exists has
    # a complete picture of nothing, and every frame then reads as "witnessed nothing" — which for
    # this module means DELETABLE. That released frames the pre-split code held, and put the
    # frame-level authority in direct contradiction with reel_retention, which holds the very same
    # reel because its sweep read rows that reached no store.
    # `haveIndex` is the missing fact: is there anything here that COULD name a witness. Without
    # one, "not a witness" is unprovable rather than false, and this module's own rule is that
    # everything errs toward keeping. [[unknown-stays-unknown]]
    return {"frames": frames, "sessions": sessions, "ok": ok, "perStore": seen,
            "cited": cited, "haveIndex": absent < len(DURABLE_STORES)}


def sealed_sessions(root=None):
    """Sessions the vault sweep has SEALED — it read what there was to read and said so.

    Returns (mapping, ok). A seal is not permanent: v2002 stamps the reader on it, so a newer
    VAULT_PROMPT_VER reopens the reel by itself. Deleting a sealed reel's frames FORECLOSES that
    reopen, which is why sealing alone never authorises deletion here — it is one of three
    conditions, not the verdict.
    """
    blob = _load(root or HERE, SEAL_STORE)
    if not isinstance(blob, dict):
        return {}, False
    return blob, True


def _session_of(path):
    b = os.path.basename(str(path or "").rstrip("/"))
    return b[len("reel_"):] if b.startswith("reel_") else b


def _reel_ts(reel_dir):
    """Sort key: the epoch ms in reel_s_<ms>_<n>. A name that will not parse sorts NEWEST, so it is
    the last thing anyone deletes rather than the first."""
    try:
        return int(os.path.basename(reel_dir).split("_")[2])
    except Exception:
        return float("inf")


def recent_reels(hist_dir, keep=KEEP_RECENT):
    """The newest `keep` reel directories — held whatever the ledgers say, because the sweep that
    would extract them may simply not have run yet."""
    hist_dir = _hist_dir(hist_dir)
    reels = [d for d in glob.glob(os.path.join(hist_dir, "reel_*")) if os.path.isdir(d)]
    return set(sorted(reels, key=_reel_ts)[-keep:]) if reels else set()


# ══ v2272 — WHAT A SEAL MUST CERTIFY BEFORE ITS PIXELS ARE DISPOSABLE ═══════════════════════════
#
# Konyo, 2026-08-29: "make sure that it isnt deleting evidence.. and only pruning literally where it
# can read tooltips.. but not only tooltips are analyzed in a reel.. there is location of the item
# its been read also like where it is exactly and where it was seen.. and everything thats detail
# related should be extracted and tallied.. and then pruned"
#
# THAT IS STRICTLY MORE THAN SEALING MEANS TODAY. A seal row is
# {ts, rows, promptVer, agentVer, why} — it certifies WHICH READER ran, which is a statement about
# the NAME lane and nothing else. frame_verdict then treats "sealed + not a witness" as disposable.
# So a frame whose LOCATION was never extracted is deletable today, and location is exactly what he
# just said must be taken first.
#
# The fix is not a new flag to trust. It is to make the seal declare WHAT IT EXTRACTED, and to hold
# every frame whose seal does not cover the contract. No seal on disk declares it yet, so this holds
# everything — which is the correct direction and is what he asked for. Arming stops being someone
# flipping _PRUNE_SAFE_TO_RUN and becomes the sweep truthfully saying it took the location too.
#
# ⚠ THE FACTS ARE NAMED, NOT COUNTED. "3 things were extracted" is satisfiable by extracting the
# same thing three times. [[unknown-stays-unknown]]
EXTRACTION_CONTRACT = ("name", "location", "provenance")

_CONTRACT_WHY = {
    "name":       "the item's name, which only ever appears in a hover tooltip",
    "location":   "WHERE it was — the container and the cell box inside it (his slot identity)",
    "provenance": "where it was SEEN — which reel and which frame, so a row can be shown its proof",
}


def seal_covers_extraction(row, contract=EXTRACTION_CONTRACT):
    """Does this seal certify that everything detail-bearing was taken? -> (bool, why)

    A seal must carry an `extracted` list naming the facts it took. Anything missing — including a
    seal that names nothing, which is every seal written before this contract existed — HOLDS.
    An unstated fact is an unextracted one; "the sweep probably got it" is not a record.
    """
    if not isinstance(row, dict):
        return False, "the seal is not a record at all"
    got = row.get("extracted")
    if got is None:
        return False, ("this seal predates the extraction contract — it certifies a reader "
                       "(promptVer %s) but never says WHAT it took, and an unstated fact is an "
                       "unextracted one" % (row.get("promptVer") or "?"))
    if not isinstance(got, (list, tuple, set)):
        return False, "the seal's `extracted` is %s, not a list of facts" % type(got).__name__
    have = {str(x) for x in got}
    missing = [f for f in contract if f not in have]
    if missing:
        return False, ("the sweep never extracted %s" % ", ".join(
            "%s (%s)" % (f, _CONTRACT_WHY.get(f, "")) for f in missing))
    return True, "the sweep took %s before anything here became disposable" % ", ".join(contract)


#: the three answers a seal can honestly give. `seal_covers_extraction` can only say yes or no,
#: and that is the whole defect this vocabulary exists to end.
COVERED, EMPTY, UNEVIDENCED = "COVERED", "EMPTY", "UNEVIDENCED"


def seal_verdict(row, contract=EXTRACTION_CONTRACT):
    """-> (COVERED | EMPTY | UNEVIDENCED, why). What this seal actually establishes.

    ⚠⚠ v2702 — WHY A THIRD ANSWER WAS NEEDED, MEASURED ON HIS 30 SEALS.
    `seal_covers_extraction` reads ONLY `extracted`. It never looks at `examinedEmpty` or
    `extractedWhy`, so a seal that examined a session and recorded "there was nothing to take"
    is scored IDENTICALLY to one that never looked. That is measured-zero collapsed into
    nobody-looked, inside the function whose entire job is policing evidence.

    It made a real number read as a disaster. `seals_certify_nothing` was filed as "ALL 30 seals
    certify nothing", and the split is:

        22 seals: `extracted: []`, extractedWhy "examined and there was nothing to take",
                  and `rows` == 0 for EVERY ONE. Seals over EMPTY sessions. There was no row
                  to take a name from, so there is no failure here to report.
         8 seals: no `extracted` key at all (they predate the contract). Six of those cover
                  7 rows each -- 42 rows of real content sealed with no record of what was
                  taken. THAT is the defect, and it is six seals, not thirty.

    ⚠ `rows == 0` IS LOAD-BEARING AND IS NOT A FORMALITY. A seal that claims "nothing to take"
    while covering seven rows is not empty, it is UNEVIDENCED wearing an excuse — the same shape
    as a probe returning 0 for a container it never opened. Only a seal over zero rows can
    honestly be EMPTY, so the declaration alone is never enough. [[zero-needs-a-denominator]]

    ⚠ THIS DOES NOT LOOSEN ANY GATE. `seal_covers_extraction` is unchanged and still answers the
    strict question, because two gates depend on its strictness: test_control asserts the frame
    authority is "the stricter of the two", and reel_retention is asserted NEVER to consult it
    (every existing seal predates the contract, so the prune would never fire again). This adds a
    word the vocabulary lacked; it takes nothing away.
    """
    covered, why = seal_covers_extraction(row, contract)
    if covered:
        return COVERED, why
    if not isinstance(row, dict):
        return UNEVIDENCED, why

    got = row.get("extracted")
    if not isinstance(got, (list, tuple, set)) or len(got) > 0:
        # absent, wrong type, or a partial list — all of these are genuinely unevidenced
        return UNEVIDENCED, why

    rows = row.get("rows")
    # False == 0 and 0.0 == 0. A bool or a float is not a row count, and treating it as zero
    # lets examinedEmpty release frames from a seal that never recorded an integer zero.
    rows_zero = isinstance(rows, int) and not isinstance(rows, bool) and rows == 0
    declared = bool(row.get("examinedEmpty")) or ("nothing" in str(row.get("extractedWhy") or "").lower())
    if rows_zero and declared:
        return EMPTY, ("this seal examined a session with 0 rows and recorded that there was "
                       "nothing to take. An empty examination is a MEASUREMENT, not a missing "
                       "one — it is not the same fact as a seal that never looked")
    if rows_zero:
        return UNEVIDENCED, ("this seal covers 0 rows but never SAYS it examined an empty "
                             "session, so nothing distinguishes it from one that did not look")
    return UNEVIDENCED, ("this seal covers %s row(s) and took nothing from them, which is not an "
                         "empty examination — it is an unevidenced one" % rows)


def probed_every_panel(row):
    """REG-2042 - did this examined-empty seal probe every stash panel triage saw in its reel? -> (bool, why)

    Pure: it reads the two counts the seal carries - `triagePanels` (a FULL triage pass's panel count for the reel) and
    `probedPanels` (how many of those the seal looked at) - and never a store. Either one missing is UNKNOWN, and
    UNKNOWN keeps the footage.
    """
    tp = (row or {}).get("triagePanels")
    pp = (row or {}).get("probedPanels")
    if not isinstance(tp, int) or isinstance(tp, bool):
        return False, ("this examined-empty seal does not say how many stash panels triage saw in the reel (it predates "
                       "the every-panel rule, or the reel was never fully triaged) - his ruling: probe every panel, so "
                       "the reel is kept")
    if not isinstance(pp, int) or isinstance(pp, bool):
        return False, ("triage saw %d stash panel(s) in this reel and the seal does not say it probed them - kept until "
                       "every panel is probed" % tp)
    if pp < tp:
        return False, ("the seal probed %d of the %d stash panel(s) triage saw - his ruling is every panel, so the reel "
                       "is kept" % (pp, tp))
    if pp > tp:
        # #231 second eye on v3622: a seal that says it probed MORE panels than a full triage saw is two instruments
        # disagreeing about one reel - a count cannot show the probe covered the panels triage saw, so the reel is kept.
        return False, ("the seal says it probed %d stash panel(s) but a full triage saw %d - the two counts disagree about "
                       "this reel, so it is kept" % (pp, tp))
    return True, ("examined and empty: it probed all %d stash panel(s) triage saw%s"
                  % (tp, "" if tp else " (a full triage pass saw none)"))


def stamp_examined_from_triage(row, triage_row):
    """REG-2042 - add the triage denominator to an examined-empty seal that lacks it. -> (row, changed)

    Re-derivable from evidence, so it may be written onto an older seal: a FULL triage pass that saw ZERO panels makes
    `probedPanels` 0 (nothing to probe); one that saw panels records how many and leaves `probedPanels` UNKNOWN, which
    keeps the reel. A partial or missing triage pass changes nothing. Pure.
    """
    if not isinstance(row, dict) or row.get("examinedEmpty") is not True or isinstance(row.get("triagePanels"), int):
        return row, False
    if not isinstance(triage_row, dict) or not triage_row.get("full"):
        return row, False
    try:
        n = int(triage_row.get("panels") or 0)
    except (TypeError, ValueError):
        return row, False
    out = dict(row)
    out["triagePanels"] = n
    if n == 0:
        out["probedPanels"] = 0
    return out, True


def seal_releases_frames(row):
    """May this seal let its frames go? -> (bool, why). The DECIDING question, stricter than the
    reporting one — and the difference is measured, not stylistic.

    ⚠⚠ v2720 — WHY THIS IS NOT JUST `seal_verdict(row) != UNEVIDENCED`. MEASURED across his 31
    seals the moment the deciders were joined to the three-answer vocabulary:

        23 scored EMPTY
           17 carry `examinedEmpty: True`
            6 qualify ONLY because `extractedWhy` contains the word "nothing", and their why is
              literally "nothing was taken"

    `seal_verdict`'s `or ("nothing" in extractedWhy)` clause is right for a REPORT — it keeps a
    measured-zero visible instead of collapsing it into nobody-looked. It is WRONG for a deletion,
    because "nothing was taken" is the DEFAULT branch of `_seal_extracted` for any sweep that
    grounded no rows. It says the sweep found nothing. It does NOT say anyone established there
    was nothing to find.

    Konyo's ruling was CONDITIONAL — *"as long as its ledgered and extracted properly and tallied
    where needed"* — and only `examinedEmpty` carries that condition. It is written at exactly one
    place (control_app's `_examined_and_empty` branch of the vault sweep) and only when the stash
    gate refused everything it was offered AND a deliberate uncached canary proved the lane live in
    the same pass. A permission read as a blanket is how a conditional yes becomes a deletion
    nobody authorised. [[unknown-stays-unknown]] [[manual-tally-is-witness]]

    ⚠⚠ v2772 — THE ONE THING THIS PREDICATE STILL CANNOT SEE, said out loud rather than fixed
    silently, because the bar for deleting his footage is HIS ruling. This paragraph used to read
    "OFFERED every frame to the stash gate, was refused by all of them", and that is not the
    condition at the writer: `_examined_and_empty` needs `not_stash > 0` — a single refusal — and
    vault_retro probes ONE frame per still-run, so the counter tallies refused RUNS. MEASURED on
    his store, 2026-09-08:

        17 `examinedEmpty` seals, claiming 38 examined frames between them
         4 of those reels still hold frames on disk: 483 · 217 · 98 · 7  = 805 frames
        12 probes stand behind all 805, and all four seals RELEASE

    A seal saying "every one of 1 frame(s) was offered to the stash gate and refused" releases 217.
    `examinedEmpty` carries no denominator, so this function has nothing to compare against and is
    not silently guessing one. [[zero-needs-a-denominator]]
    """
    v, why = seal_verdict(row)
    if v == COVERED:
        return True, why
    if v == EMPTY and isinstance(row, dict) and row.get("examinedEmpty") is True:
        # ⚖ REG-2042 (#203) - HIS RULING 2026-10-07: "probe every panel". An examined-empty seal releases a reel's frames
        # only when it probed EVERY stash panel triage saw in that reel. MEASURED on his store 2026-10-08: of 33
        # examined-empty seals, 8 had a full triage pass that saw panels they never probed - reel ...39108 was deleted on
        # 1 probe against 268 panels - 9 sat on reels triage proved panel-free, 16 were never triaged. A seal that
        # cannot show the count (an older seal, or one whose reel triage never finished) KEEPS the reel and says why.
        return probed_every_panel(row)
    if v == EMPTY:
        return False, ("this seal reads as empty only because it says %r — that is the default for "
                       "a sweep that grounded nothing, not a record that anyone established there "
                       "was nothing here. It never declared `examinedEmpty`."
                       % (str((row or {}).get("extractedWhy") or "")[:60]))
    return False, why


def frame_verdict(frame_path, sealed=None, wit=None, recent=None):
    """MAY this one frame be deleted? Returns (bool, why) and the why is written for him, not for a log.

    Four ways to be held, and each is a different thing not being true yet:
      · its reel is one of the newest              the sweep may not have run
      · its reel is not sealed                     evidence not extracted; deleting loses it
      · it is named as a witness                   it is the visual proof of a row he can see
      · anything above could not be read           an unreadable store can only ever HOLD
    """
    if sealed is None or wit is None:
        raise ValueError("frame_verdict needs the indexes passed in — reading them per frame would "
                         "ask the disk thousands of times and let them drift mid-pass")
    reel_dir = os.path.dirname(os.path.abspath(frame_path))
    sess = _session_of(reel_dir)
    if recent and reel_dir in recent:
        return False, "one of the newest %d recordings — nothing is pruned from those" % KEEP_RECENT
    if not wit.get("ok"):
        return False, ("a durable store could not be read (%s), so the witness list is incomplete "
                       "and every frame is treated as evidence" % ", ".join(
                           k for k, v in (wit.get("perStore") or {}).items() if v is None))
    if not wit.get("haveIndex", True):
        return False, ("no durable store exists yet (%s), so nothing here can prove a frame IS a "
                       "witness — and 'unprovable' is not 'no'. Every predicate in this module errs "
                       "toward keeping." % ", ".join(DURABLE_STORES))
    if sess not in (sealed or {}):
        return False, ("recording %s is not sealed — the sweep has not said it read everything "
                       "here, so these pixels may be the only copy of a name" % sess)
    if os.path.basename(frame_path) in (wit.get("frames") or set()):
        return False, ("this frame is a WITNESS behind a row in his vault — it is the only way to "
                       "ever show him why that row is there")
    # A tiered item cites the looks that saw it. Those pictures stay when the rest of the reel goes.
    # `cited is None` means the ledger could not be read — hold, do not treat that as nothing cited.
    _cited = wit.get("cited", False)
    if _cited is None:
        return False, ("the vault evidence ledger could not be read, so whether this frame is "
                       "cited is UNKNOWN")
    if os.path.basename(frame_path) in set(_cited or ()):
        return False, ("cited as vault evidence — a watched, proven or hardened item still stands "
                       "on this picture, so the reel may go and this frame stays")
    # v2272 — A FIFTH HOLD, and it is his rule: extracted FIRST, then pruned. Sealing says which
    # reader ran; it has never said what was taken. Until a seal declares the contract, these pixels
    # may still be the only record of WHERE the item was.
    # ⚠⚠ v2720 — HIS RULING, AND THE JOIN THAT MAKES IT MEAN ANYTHING.
    # Konyo, 2026-09-06, answering the question `_seal_extracted` itself flagged as not-mine:
    #   "as long as its ledgered and extracted properly and tallied where needed.. it can continue
    #    down the river to tombstone i dont see why not..? and delete.."
    #
    # `seal_verdict` has answered this correctly since v2702 — COVERED / EMPTY / UNEVIDENCED,
    # written precisely so "examined and there was genuinely nothing here" would stop being scored
    # identically to "nobody looked". It was built, it was correct, and it was called by ONE place,
    # for a REPORT. Every function that actually DECIDED still asked the old binary question, so
    # the collapse it existed to end was still happening at the only sites that mattered.
    # [[the-unjoined-end]] [[join-gate-heart]]
    #
    # ⚠ EMPTY IS NOT A FREE PASS — IT IS A DIFFERENT FACT, AND ONLY THAT BRANCH WRITES IT.
    # `examinedEmpty` is set at exactly one place — control_app's `_examined_and_empty` branch of
    # the vault sweep — and only when the stash gate refused everything it was offered AND a
    # deliberate uncached canary proved the lane live in the same pass. A seal that merely lacks
    # names does NOT reach here: it lands UNEVIDENCED and still holds. [[unknown-stays-unknown]]
    # ⚠⚠ v2772 — AND "EVERYTHING IT WAS OFFERED" IS NOT "EVERY FRAME". This comment said "OFFERED
    # every frame to the stash gate" for fifty-odd versions and that premise is not what the writer
    # enforces: `_examined_and_empty` requires `not_stash > 0` — ONE refusal — and vault_retro
    # probes ONE frame per still-run, so the counter tallies refused RUNS, not frames.
    # MEASURED on his store, 2026-09-08: 17 `examinedEmpty` seals claim 38 frames examined between
    # them, and four of those reels still hold 805 frames on disk. All four release. The worst
    # reads "every one of 1 frame(s) was offered to the stash gate and refused" and releases 217.
    # NOTHING IS CHANGED HERE — the bar for footage is his ruling, not mine to move — but the
    # sentence no longer asserts a denominator nobody measured. [[zero-needs-a-denominator]]
    # [[label-outlived-referent]] [[design-is-fine-until-he-says]]
    _ok, _why = seal_releases_frames((sealed or {}).get(sess))
    if not _ok:
        return False, ("recording %s is sealed, but %s — his rule is that everything detail-bearing "
                       "is extracted and tallied BEFORE anything is pruned" % (sess, _why))
    return True, "recording %s is sealed and this frame witnessed nothing" % sess


def keep_cited(reel_dir, sealed, wit):
    """NAME the frames of one reel that nothing cites; a cited frame is kept. Deletes nothing itself.

    -> {ok, kept, gone, why}: `gone` is a list of NAMES that may go. Removing them is
    reel_retention.release_uncited's job (second eye on v3520, 87c35d69: this docstring still said it
    released them after os.remove left). It writes no ledger and never touches the reel directory.
    An unreadable citation list names nothing.
    """
    unread = {"ok": False, "kept": None, "gone": None,
              "why": "whether a frame is cited could not be read, so nothing is released"}
    if wit is None or wit.get("ok") is False or wit.get("cited", False) is None:
        return unread
    if not reel_dir or not os.path.isdir(reel_dir):
        return {"ok": False, "kept": None, "gone": None,
                "why": "the reel could not be read, so nothing is released and nothing is called empty"}
    kept, gone = [], []
    for name in sorted(os.listdir(reel_dir)):
        if not name.endswith(".jpg"):
            continue
        path = os.path.join(reel_dir, name)
        if not os.path.isfile(path):
            continue
        may, why = frame_verdict(path, sealed=sealed, wit=wit, recent=set())
        if may:
            gone.append(name)
        else:
            kept.append({"frame": name, "why": why})
    return {"ok": True, "kept": kept, "gone": gone, "why": ""}


def evidence_held_reels(hist_dir=None):
    """Reel dir NAMES that reel_retention holds for an EVIDENCE reason. -> (set | None, why)

    None means the list could not be read, which is UNKNOWN and must never be read as "nothing is
    held". [[unknown-stays-unknown]]

    ⚠ THE IMPORT IS LAZY ON PURPOSE — `reel_retention` imports THIS module, so a module-level
    import here would be a cycle. reel_retention already uses the same lazy shape for the same
    reason, so this follows the file's own established idiom rather than inventing one.
    """
    try:
        import reel_story as _rs
    except Exception as e:
        return None, "reel_story could not be imported (%s)" % str(e)[:60]
    try:
        st = _rs.story(_hist_dir(hist_dir))
    except Exception as e:
        return None, "reel_story.story() raised (%s)" % str(e)[:60]
    if not isinstance(st, dict) or not st.get("ok"):
        # ⚠ `(st or {})` KEEPS A NON-EMPTY STRING and then .get() raises — caught by this module's
        # own gate feeding it a non-dict. The isinstance check has to be repeated here, not
        # assumed from the line above, because `or` is not a type guard.
        return None, ((st.get("why") if isinstance(st, dict) else None)
                      or "reel_story did not answer (%s)" % type(st).__name__)
    rows = st.get("reels")
    if not isinstance(rows, list):
        return None, "reel_story returned no reel list"
    # ⛔ EVIDENCE ONLY. A POLICY hold (recent / test-fixture / target-met) is a different argument
    # with a different owner; widening this to cover them would answer a question nobody asked.
    return ({r.get("reel") for r in rows
             if r.get("held") and r.get("holdKind") == "evidence" and r.get("reel")}, "")


def plan_frames(hist_dir, root=None, keep=KEEP_RECENT, held_reels=None):
    """What a witness-aware prune WOULD free. Reports; deletes nothing.

    Reporting rather than acting is deliberate: this replaces a deleter that ran automatically and
    was wrong, and the first thing its replacement should do is be readable.
    """
    hist_dir = _hist_dir(hist_dir)
    sealed, seal_ok = sealed_sessions(root)
    wit = witness_index(root)
    recent = recent_reels(hist_dir, keep)
    out = {"prunable": [], "heldBy": {}, "bytes": 0, "kept": 0, "scanned": 0,
           "sealOk": seal_ok, "witnessOk": wit["ok"],
           # v2080 — `witnessOk` answers "is my picture complete", which is TRUE of a picture of
           # nothing. A reader shown ok:true and 0 witnesses would conclude "measured, none" when
           # the fact is "there is no index yet". Both travel. [[unknown-stays-unknown]]
           "haveIndex": wit.get("haveIndex", True),
           "witnessFrames": len(wit["frames"]), "sealedSessions": len(sealed)}
    if not seal_ok:
        out["say"] = ("%s could not be read, so NOTHING is prunable — a prune that cannot tell a "
                      "sealed recording from an unswept one is the prune that ate the names" % SEAL_STORE)
        return out
    # ⚠⚠ v2740 — THE JOIN THAT WAS MISSING, AND THE 7 FRAMES IT WAS MISSING.
    # MEASURED at origin: all 805 offered frames sat inside reels reel_retention HOLDS, and 7 of
    # them were in `reel_s_1787243026006_12211`, held as `zero-pages` — an EVIDENCE hold, which
    # exists because "the engine reopens these when the prompt improves". Freeing those frames
    # destroys the one thing the hold protects: a re-read with no frames is not a re-read.
    # This module knew about witness FRAMES and nothing about held REELS. [[the-unjoined-end]]
    # ⚠⚠ v2741 — THE HOLD LIST IS AN INJECTABLE INPUT, and it had to become one.
    # v2740 computed it unconditionally from `reel_story`, which reads its stores relative to the
    # HIST dir and derives durability from `_durable_sessions()` — and that reads the LIVE tree,
    # not the caller's `root`. So a fixture that hands this function its own `root` (which is the
    # entire contract of these unit tests) had NO WAY to say what is held: every fixture reel came
    # back evidence-held, and two correct laws about THIS module's own rules went red.
    # ⚠ NOT A WEAKENED RULE. The production path is unchanged — None still means "go and ask", and
    # an unreadable answer still refuses everything below. What changed is that a caller which
    # already supplies its own stores can supply this one too, instead of being silently overruled
    # by a store it cannot reach. The cross-module rule keeps its own gate in
    # tv/test_frames_respect_evidence_holds.py, so nothing here is covering for it.
    # [[feedback-fixtures-never-touch-live-data]] — guard the FIXTURE's reach, not the call site.
    if held_reels is None:
        held_reels, held_why = evidence_held_reels(hist_dir)
    else:
        held_reels, held_why = set(held_reels), "supplied by the caller"
    out["evidenceHeldReels"] = (None if held_reels is None else sorted(held_reels))
    if held_reels is None:
        # the same answer the seal refusal above gives to the same shape of ignorance, and for the
        # same reason — never "assume nothing is held", which is how v2229 lost two fixture reels
        out["say"] = ("the reel-hold list could not be read (%s), so NOTHING is prunable — a prune "
                      "that cannot tell a held reel from a released one is the prune that ate the "
                      "footage" % held_why)
        return out
    for d in sorted(glob.glob(os.path.join(hist_dir, "reel_*")), key=_reel_ts):
        if not os.path.isdir(d):
            continue
        for f in sorted(glob.glob(os.path.join(d, "*.jpg"))):
            out["scanned"] += 1
            ok, why = frame_verdict(f, sealed, wit, recent)
            # ⚠ APPLIED HERE, NOT INSIDE frame_verdict. That function is a per-frame PREDICATE used
            # by river.py's joint and by tests; giving it a new input would either break them or
            # hand them a default, and the only available default — "assume nothing is held" — is
            # the unsafe direction. The refusal belongs where the OFFER is made.
            if ok and os.path.basename(os.path.dirname(f)) in held_reels:
                ok, why = False, ("its reel is held as EVIDENCE by the shelf — that hold exists so "
                                  "the reel can be re-read, and a re-read with no frames is not a "
                                  "re-read")
            if ok:
                try:
                    out["bytes"] += os.path.getsize(f)
                except OSError:
                    continue
                out["prunable"].append(f)
            else:
                out["kept"] += 1
                key = why.split("—")[0].strip()
                out["heldBy"][key] = out["heldBy"].get(key, 0) + 1
    out["say"] = ("%d of %d frame(s) could be freed (%.2f GB). %d held, and every witness frame "
                  "behind his vault rows is among them."
                  % (len(out["prunable"]), out["scanned"], out["bytes"] / 1e9, out["kept"]))
    return out


# ⚠⚠ v2229 — A TEST'S FIXTURES DO NOT ALL LIVE IN FILES CALLED test_*.py, AND THAT COST FOOTAGE.
# On 2026-08-28, within an hour of the prune being armed to act above the disk floor, it deleted
# reel_s_1786998671206_32230 (80.5 MB, 71 pages) and reel_s_1786998775577_33262 (42.4 MB, 35 pages)
# as "read and sealed by BOTH lanes". Both are named as SCENARIO fixtures in tv/vault_simulate.py —
# the module that DEFINES what test_vault_lane.py runs — and vault_simulate.py matched none of the
# four globs, so test_referenced_reels never saw them. Five cases went red immediately.
#
# reel_s_1786998496819_31092 survived the same pass ONLY because test_vault_lane.py happens to name
# it directly in its skipUnless. That is luck, not protection.
#
# This is the THIRD time this class has been paid for. The docstring below records the first two,
# and both fixes widened the LEDGERS the deleter consults; the reach of the SCAN was never the
# suspect. A guard fails on its own reach before it fails on the code.
#
# So: every .py under tv/ and everything under tests/. The scan is keyed on (size, mtime) and cost
# 28 ms over the old set; widening it is cheap and the failure it prevents is irreversible. Holding
# a reel too long costs disk. The other direction costs footage that does not come back.
# [[source-reading-guard]] [[feedback-blind-fixture-green-gate]]
_FIXTURE_GLOBS = ("tv/*.py", "tests/*.spec.ts", "tests/*.ts", "tests/*.py")


def _executable_only(src, path=""):
    """`src` with COMMENTS and DOCSTRINGS removed. Ordinary string literals are KEPT.

    ══ v2393 — A REEL NAMED IN PROSE IS NOT A FIXTURE, AND IT WAS HOLDING 4.8 GB ═════════════
    Konyo's disk, measured 2026-09-01: **1.2 GB free on 228 GB, 100% capacity**, against an 8 GB
    capture floor. `reel_retention.plan()` held 6.3 GB of 7.2 GB under `test-fixture`. Every hit
    for the two largest — 3.0 GB and 1.7 GB, 4.8 GB together — was inside a comment or a
    docstring. Not one was executable code that opens a reel:

        slot_identity.py:109     "# reel_s_1787520892804_95400 (seam luminance 17.0 ...)"
        control_app.py:13826     "# MEASURED ON HIS OWN REEL (reel_s_1787520892804_95400) ..."
        test_control.py:19285    docstring: "MEASURED on reel_s_1787520892804_95400: ..."
        orphan_fold.py:22        docstring table mapping the id to a sessionId
        frame_authority.py:353   the docstring OF THIS FUNCTION, explaining this exact defect

    ⚠ THE DEFECT WAS KNOWN AND WRITTEN DOWN AT v2071 AND LEFT RUNNING. That docstring says it
    plainly — *"retention began holding 3.15 GB of his footage with the reason 'the TEST SUITE
    opens this reel', which was false"* — and prescribed a fix for FUTURE tests (synthesise ids
    from a 2017 stamp). That does nothing about prose already written, and the prose kept
    accumulating: five of the nine hits above were added AFTER v2071. A wrong reason is how a
    real hold later gets dismissed as noise, and here it also cost him his disk.
    [[feedback-comments-vs-code]] — my own carved scar: an explanatory comment blinding a guard
    that greps.

    ⚠ ORDINARY STRING LITERALS ARE DELIBERATELY KEPT. A real fixture opens footage BY NAME —
    `os.path.join(hist, "reel_s_1787520892804_95400")` — and that is a STRING. Stripping all
    strings would delete the very footage this function exists to protect. Only comments and
    DOCSTRINGS (a string that is the whole of an expression statement) are removed.

    ⚠ AND EVERY FAILURE FALLS BACK TO THE OLD BEHAVIOUR, returning `src` unchanged. Holding too
    much wastes disk; holding too little deletes his footage permanently. Those are not
    symmetric, so an unparseable file is scanned exactly as before.
    """
    # ⚠ `re` IS IMPORTED INSIDE test_referenced_reels, NOT AT MODULE SCOPE — so the first cut of
    # this function read a name bound nowhere and would have raised NameError on the first .ts
    # file, inside a try/except, silently, while looking perfectly wired.
    # Caught by TestV2010NoCallIntoANameThatIsNotThere. [[the-unjoined-end]]
    import re
    if path.endswith((".ts", ".tsx", ".js")):
        try:
            out = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
            return re.sub(r"(?m)^\s*//.*$", " ", out)
        except Exception:
            return src
    import ast
    import io as _io
    import tokenize as _tk
    try:
        tree = ast.parse(src)
    except Exception:
        return src                       # unparseable -> behave exactly as before
    # every docstring / bare string-expression statement, by line span
    dead = set()
    try:
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if not isinstance(body, list):
                continue
            for stmt in body:
                if (isinstance(stmt, ast.Expr)
                        and isinstance(getattr(stmt, "value", None), ast.Constant)
                        and isinstance(stmt.value.value, str)):
                    a = getattr(stmt, "lineno", None)
                    b = getattr(stmt, "end_lineno", None) or a
                    if a:
                        dead.update(range(a, b + 1))
    except Exception:
        return src
    lines = src.split("\n")
    kept = [("" if (i + 1) in dead else ln) for i, ln in enumerate(lines)]
    # then the # comments, via the tokenizer so a # inside a string is not mistaken for one
    try:
        joined = "\n".join(kept)
        drop = []
        for tok in _tk.generate_tokens(_io.StringIO(joined).readline):
            if tok.type == _tk.COMMENT:
                drop.append((tok.start[0], tok.start[1], tok.end[1]))
        arr = joined.split("\n")
        for ln_no, c0, c1 in drop:
            if 1 <= ln_no <= len(arr):
                row = arr[ln_no - 1]
                arr[ln_no - 1] = row[:c0] + " " * (c1 - c0) + row[c1:]
        return "\n".join(arr)
    except Exception:
        return "\n".join(kept)          # docstrings gone, comments not — still safer than before


_FIXTURE_BG = {"thread": None, "last": None}


def test_referenced_reels_nowait():
    """The fixture set WITHOUT blocking a request: the last one computed, or None while the first
    computation runs in the background (and this call starts or refreshes it). -> set | None

    ⚠⚠ REG-1284 — A 9-SECOND SCAN ON THE THEATRE'S REQUEST PATH. test_referenced_reels() reads every test
    file whenever their size/mtime key changes: on a fresh world, and on his console after EVERY ship.
    The theatre called it inside /api/sessions, and the page aborts that fetch at 8 s and closes the
    stage ("could not reach the console"). MEASURED on a scratch console: first /api/sessions 9.03 s,
    then 0.01 s; a stack dump two seconds in sat inside this scan. It only MARKS rows as fixtures, and
    its caller already reads "cannot tell" as "mark nothing, show everything" - so not yet knowing
    must not cost him the open. [[unknown-stays-unknown]]"""
    import threading
    th = _FIXTURE_BG["thread"]
    if th is None or not th.is_alive():
        def _run():
            try:
                _FIXTURE_BG["last"] = frozenset(test_referenced_reels() or ())
            except Exception:
                pass
        th = threading.Thread(target=_run, name="fixture-reels", daemon=True)
        _FIXTURE_BG["thread"] = th
        th.start()
    last = _FIXTURE_BG["last"]
    return set(last) if last is not None else None


#: REG-1410 (#66) — the committed ratchet: every REAL reel id the suite is allowed to name.
#: test_a_gate_may_not_pin_his_footage keeps it a SUPERSET of what the exact scan finds, on every push.
RATCHET_PATH = os.path.join(HERE, "test_reel_refs.json")


def ratchet_reels():
    """The ratchet's `accepted` ids. -> set | None (None = it could not be read - never an empty answer)."""
    try:
        with open(RATCHET_PATH, encoding="utf-8") as fh:
            blob = json.load(fh)
    except Exception:
        return None
    acc = blob.get("accepted") if isinstance(blob, dict) else None
    if not isinstance(acc, list) or not all(isinstance(x, str) for x in acc):
        return None
    return set(acc)


def test_referenced_reels(repo=None, exact=False):
    """Reel ids the TEST SUITE opens by name. A reel a test reads is a FIXTURE, whatever the ledgers
    say about it.

    ⚠⚠ REG-1410 (#66) — A CONSOLE DOES NOT TOKENIZE THE TEST SUITE. MEASURED on his ALT (Windows +
    Boosteroid) for ~15 minutes after v3522 landed: /api/status took 11 s and then timed out, and a
    py-spy dump showed ONE hot thread, tvd-eagle-watch, holding the GIL in _executable_only -> tokenize
    over every tv/*.py, reached through reel_retention.plan(). The key below changes on EVERY ship, so
    every ship paid it again (9 s on the Mac in REG-1284, 20.6 s measured here on 2026-09-29, minutes
    on the ALT). On the CONSOLE PATH (frame_ref.mark_console_path(), set by control_app.main()) the set
    is the committed ratchet, tv/test_reel_refs.json `accepted` - which the gate keeps a superset of
    every real id this scan finds, so it holds at least what the scan would. Synthetic 2017-epoch ids
    are not in it and pin no footage by construction.
    The exact scan stays for the gate, CI, a CLI, `repo=` and `exact=True` (test_a_gate_may_not_pin_his_footage
    asks exact=True: graded against the ratchet itself it would be blind). A ratchet that will not read
    is UNKNOWN, not empty: the console then pays the exact scan rather than hold nothing.
    [[unknown-stays-unknown]]
    ⚠ REG-1440 — THE WORKING-TREE GAP, STATED: the ratchet is a COMMITTED file, so it is only as new as its last
    edit. A law written in a working tree that names a real reel, and is not yet ratcheted, is held by the exact
    scan (the gate, CI, a CLI) but NOT by a console reading the ratchet - until tv/test_reel_refs.json is edited
    to accept it. test_a_gate_may_not_pin_his_footage closes it at push: it asks exact=True and refuses any real
    id the ratchet lacks. Between the write and that push, a console on that tree can offer the reel for release.
    (A console whose ratchet will not read keys no plan at all - reel_retention.plan_fingerprint, REG-1439.)

    v2069 — MEASURED, after the fact, on a prune I had already run. Six reels were deleted as
    "sealed by both lanes, has given up its information" and THREE of them were named by
    tv/test_control.py. The suite did not go red: those tests are written to skipTest when the
    footage is absent, so a real check silently became a permanent skip — a gate that always skips
    is the same defect as one that is always green.

    It had happened twice before and been absorbed: the suite already carries two cases marked
    "fixture reel ... was pruned — PERMANENTLY skipped in both venues". Nobody was wrong at any
    step, which is exactly why it kept happening — the deleter asked the ledgers and the ledgers
    have no idea a test exists.

    Only REAL reel ids count (a 10-16 digit epoch): tests build their own throwaway dirs called
    reel_s_1_1, and holding those would be holding nothing.

    ⚠ AND A TEST LITERAL CAN CLAIM REAL FOOTAGE BY ACCIDENT. This scan cannot tell a reel a test
    READS from one a test merely NAMES. v2071 wrote `reel_s_1787523300658_1` into a guard as an
    illustration, and the orphan fold minted that exact directory from the same t0 an hour later —
    so retention began holding 3.15 GB of his footage with the reason "the TEST SUITE opens this
    reel", which was false. It errs toward KEEPING, so nothing was endangered; what was wrong was
    the REASON, and a wrong reason is how a real hold later gets dismissed as noise.

    Use a stamp no recording can carry (the v2071 guards now use 1500000000000 — 2017) whenever a
    test SYNTHESISES a reel name rather than pointing at footage on disk.
    """
    import re
    if not exact and repo is None:
        try:
            import frame_ref as _fr_cp
            _console = _fr_cp.on_console_path()
        except Exception:
            _console = False
        if _console:
            _rat = ratchet_reels()
            if _rat is not None:
                return _rat
            # the ratchet will not read -> fall through to the exact scan, never to an empty set
    root = repo or os.path.dirname(HERE)
    # plan() asks this for every run and the suite file alone is ~0.9 MB — 28 ms a call, which is
    # nothing once and 2.8 s across a hundred plans. Keyed on the files' (size, mtime) so an edited
    # test is picked up immediately rather than cached into invisibility.
    try:
        stamp = tuple(sorted(
            (f, os.stat(f).st_size, int(os.stat(f).st_mtime))
            for pat in _FIXTURE_GLOBS
            for f in glob.glob(os.path.join(root, pat))))
    except OSError:
        stamp = None
    cached = globals().get("_FIXTURE_CACHE")
    if stamp is not None and cached and cached[0] == stamp:
        return set(cached[1])
    # ⚠⚠ v2692 — AND THE SAME ANSWER ON DISK, BECAUSE THE IN-MEMORY CACHE CANNOT HELP A COLD START.
    # PROFILED: heart.vessels() -> _health_rows -> check_lanes -> owed_counts -> _vault_owed_reels
    # -> reel_retention.plan() -> HERE, and this call alone was 22.4s of a 24.3s vessels() — 1,196
    # _executable_only() calls driving 1,140,383 tokenize() calls. The memo above makes the SECOND
    # call free and does nothing for the first, and /api/heart on a freshly served console is
    # always a first call: measured 19.5s cold vs 0.05s warm, against a render gate that allows
    # 10s warmup + a 12s activate poll. That is what refused a push with "the panel could not be
    # ACTIVATED".
    # Keyed on the IDENTICAL (path, size, mtime) stamp the memo uses, so an edited test invalidates
    # it exactly as before — a cache that outlives its evidence is the defect this repo calls
    # [[stale-reading]], and the point of reusing the key is that there is only one rule.
    # ⚠ FAILS OPEN, ALWAYS: any read or write problem falls through to the full parse. A cache that
    # can break the answer is worse than no cache.
    # ⚠ v2778 — v1869's RULE, WHICH THIS FILE WAS ADDED AFTER AND NEVER GOT.
    # `_fixture_root` says it in its own docstring: "one rule, four files" — his console
    # log, his engine state, his G5 stats and his subscription meter follow TV_HIST when a
    # caller has said "this is not his world". This path arrived at v2147 and was written
    # against a bare HERE, so a harness console wrote its record into his real tree.
    # MEASURED 2026-09-08: a render run left .board_identity.json, .fixture_reels_cache.json
    # and .chronicle_routes_cache.json changed in his tv/ — three files added after v1869,
    # all three missing the same rule. [[feedback-fixtures-never-touch-live-data]]
    # ⚠⚠ v2788 — the except-arm handed back his LIVE directory when isolation had been asked for.
    # Same shape as control_app's, fixed there in v2783/v2785 and never swept here. This one WRITES
    # (.fixture_reels_cache.json), and the v2778 comment above already measured these files being
    # left in his live tv/. [[copy-drift]]
    try:
        import tv_diablo as _tvd
        _croot = _tvd._fixture_root(HERE)
    except Exception:
        _croot = HERE
        _h = os.environ.get("TV_HIST")
        if _h:
            try:
                _r = os.path.realpath(_h)
                if not (_r == HERE or _r.startswith(HERE + os.sep)):
                    _croot = _r
            except Exception:
                pass
    _cpath = os.path.join(_croot, ".fixture_reels_cache.json")
    _ckey = None
    if stamp is not None:
        try:
            import hashlib as _hl
            _ckey = _hl.sha1(repr(stamp).encode("utf-8", "replace")).hexdigest()
            with open(_cpath, "r", encoding="utf-8") as _fh:
                _blob = json.load(_fh) or {}
            if _blob.get("key") == _ckey and isinstance(_blob.get("reels"), list):
                _hit = set(_blob["reels"])
                globals()["_FIXTURE_CACHE"] = (stamp, frozenset(_hit))
                return _hit
        except Exception:
            pass
    out = set()
    for pat in _FIXTURE_GLOBS:
        for f in glob.glob(os.path.join(root, pat)):
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    src = fh.read()
            except OSError:
                continue
            out.update(re.findall(r"reel_s_\d{10,16}_\d+", _executable_only(src, f)))
    if stamp is not None:
        globals()["_FIXTURE_CACHE"] = (stamp, frozenset(out))
        if _ckey:
            try:
                _tmp = _cpath + ".tmp"
                with open(_tmp, "w", encoding="utf-8") as _fh:
                    json.dump({"key": _ckey, "reels": sorted(out)}, _fh)
                os.replace(_tmp, _cpath)   # atomic: a half-written cache must never be readable
            except Exception:
                pass
    return out


def loose_frames(hist_dir):
    """Frames sitting DIRECTLY in hist/, belonging to no reel — and therefore to no authority.

    v2069 — MEASURED on his tree the night this was written: 3,420 loose .jpg files, 3.41 GB, which
    is more than a third of all his footage. Every deleter was blind to them by construction:
    reel_retention iterates `reel_*` directories, this module globbed `hist/reel_*`, and
    space_warden has tv/frames on its NEVER list. So a third of the disk was invisible to the three
    things whose whole job is deciding what may go — not protected, just unseen, which is worse
    because it reads as protected.

    They are two different populations and the difference decides everything:
      · `f_<ms>.jpg`      an ungrouped RECORDING. The indexer never turned it into a reel, so no
                          lane has swept it and it may hold names nothing has read.
      · `<n>_<ms>.jpg`    the AI's READ PICTURES: tv_diablo.archive_read_frame (v735) keeps the settled screen each read
                          saw, so its history row can reopen it. v3883 - this line called them "probe / extract
                          artifacts from the free pixel lane"; MEASURED 11-08 on the work ALT, two written 11 s apart at
                          09:55 beside the live footage, 4,582 of them (508 MB), Dean 11,902. His v861.1 rule keeps them
                          ("so much smarter without a cap - it's locally stored"): evicted only under the free-disk floor,
                          a journal-named one never.

    This REPORTS them and refuses all of them. Classifying an ungrouped recording is a different
    job — it needs the indexer, not a deleter — and until that exists "I do not know what this is"
    must resolve to KEEP. [[unknown-stays-unknown]]
    """
    import re
    out = {"recording": [], "artifact": [], "bytes": 0, "recordingBytes": 0, "artifactBytes": 0}
    try:
        names = [f for f in os.listdir(hist_dir)
                 if f.endswith(".jpg") and os.path.isfile(os.path.join(hist_dir, f))]
    except OSError as e:
        return dict(out, ok=False, say="cannot read %s: %s" % (hist_dir, e))
    for f in names:
        try:
            n = os.path.getsize(os.path.join(hist_dir, f))
        except OSError:
            continue
        out["bytes"] += n
        if re.match(r"f_\d{10,16}\.jpg$", f):
            out["recording"].append(f)
            out["recordingBytes"] += n
        else:
            out["artifact"].append(f)
            out["artifactBytes"] += n
    out["ok"] = True
    out["say"] = ("%d loose frame(s) belong to no reel (%.2f GB): %d look like an UNGROUPED "
                  "RECORDING (%.2f GB) that no lane has swept, %d are the AI's read pictures "
                  "(%.2f GB - kept under the free-disk rule, each reopens its history row). NONE is offered for deletion — a frame nothing has classified is not "
                  "a frame anything may delete."
                  % (len(names), out["bytes"] / 1e9,
                     len(out["recording"]), out["recordingBytes"] / 1e9,
                     len(out["artifact"]), out["artifactBytes"] / 1e9)) if names else \
                 "no loose frames — every frame on disk belongs to a reel"
    return out


def main(argv=None):
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    hist = os.environ.get("TV_HIST") or os.path.join(HERE, "frames", "hist")
    p = plan_frames(hist)
    print("\U0001f5c3  THE ONE DELETION AUTHORITY — plan only, nothing is deleted here")
    print("   sealed recordings : %d" % p["sealedSessions"])
    print("   witness frames    : %d %s" % (p["witnessFrames"],
                                            "" if p["witnessOk"] else "(INCOMPLETE — a store would not read)"))
    print("   %s" % p["say"])
    for k, n in sorted(p["heldBy"].items(), key=lambda kv: -kv[1]):
        print("     held  %5d  %s" % (n, k))
    lf = loose_frames(hist)
    print("\n\u26a0  BELONGING TO NO REEL, AND THEREFORE TO NO AUTHORITY:")
    print("   %s" % lf.get("say"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
