#!/usr/bin/env python3
"""WHAT MAY LEAVE THE JOURNAL, AND WHY EVERY OTHER ROW STAYS. Writes nothing.

Konyo, 2026-09-13: *"it should all go through the river and end up in tombstone and then in
deleted after being extracted"*, and *"should be left with last 8 sessions/reels"* — the 8 is
history: 2026-09-29 (REG-1433) *"instead of 8 last reels it reads 16"*, and the number lives in
reel_retention.KEEP_RECENT, imported below, never re-typed here.

⚠⚠ THE REEL RIVER IS ALREADY FINISHED, AND THIS IS THE HALF THAT IS NOT. Measured 2026-09-13:
20 reels on disk, `ROUTED 20` — every one routed, which reel_router's own note calls "the REAL
tombstone" — and `TOMBSTONE 0`, which means none have LEFT THE DISK. That zero is CORRECT: the 20
are 8 he asked to keep + 9 the test suite pins + 3 still held, and retention refuses all three
groups for good reasons. There is nothing left for the REEL planner to release.

His shelf still shows **419 rows**, because the shelf lists JOURNAL sessions and a row outlives its
film. 2,893 journaled · 2,474 hidden as empty · 419 shown · **20 reels**. Roughly 195 of the shown
rows name film that no longer exists.

⚠⚠⚠ AND THIS MODULE DELETES NOTHING. `plan()` classifies and explains, exactly as
`reel_retention.plan()` does — "what may go, oldest first, and WHY every other reel stays. Writes
nothing." A journal row is his record of a night he played. The apply half is a separate decision
and it is HIS.

THE EXTRACTION RULE, and it is deliberately strict:

    RELEASABLE   footageState == "retired" — the film gave up its information and was THEN
                 released. That is the system's own proof that extraction happened, produced by
                 the retention lane, not by this module guessing.
    HELD         everything else, including rows with no film at all. "No film" is not "extracted";
                 it is an absence of evidence either way. [[unknown-stays-unknown]]

⚠ FOUR THINGS ARE NEVER RELEASABLE, whatever the state says:
    · the newest KEEP_RECENT sessions — his own number; reel_retention OWNS it (16 since
      2026-09-29, REG-1433) and this module imports it rather than carrying a copy
    · any row whose reel still has film on disk — the river has not finished with it
    · any row whose reel the TEST SUITE opens by name — deleting one turns a real check into a
      permanent skip, which has already happened three times
    · any row that cannot be dated, because "newest KEEP_RECENT" is meaningless without an order
"""
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def _journal_path():
    """The journal this tree is actually using. -> path

    ⚠ ASK tv_diablo, do not hardcode. Its JOURNAL/STATE/HIST are chosen AT IMPORT from the TV_*
    env, which is how the CI harness and an isolated-hist run point the whole engine at a fixture
    tree. A module that hardcodes tv/sessions.jsonl would back up one file and rewrite another the
    moment anyone runs it under a redirect — and this module REWRITES, so the wrong path is the
    difference between a release and losing his history.
    """
    try:
        import tv_diablo as _tvd
        p = getattr(_tvd, "JOURNAL", None)
        if p:
            return p
    except Exception:
        pass
    return os.path.join(HERE, "sessions.jsonl")
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from console_safe import enable as _console_safe_enable
    _console_safe_enable()
except Exception:
    pass

#: his number, and the SAME one reel_retention keeps. Imported rather than re-typed — two copies
#: of a retention floor is how the two halves of one river start disagreeing. [[copy-drift]]
try:
    from reel_retention import KEEP_RECENT
except Exception:
    KEEP_RECENT = 16

#: the only state that proves the information was taken before the film went
EXTRACTED = "retired"


def _film_on_disk(sid, hist_dir):
    """Does this session's reel still hold frames? -> (bool, n)"""
    import glob
    d = os.path.join(hist_dir, "reel_" + str(sid))
    if not os.path.isdir(d):
        return False, 0
    n = len(glob.glob(os.path.join(d, "f_*.jpg")))
    return n > 0, n


def _journal_paths():
    """Every file the journal is READ from, oldest first. -> [path]

    ⚠⚠ DELEGATE. `_journal_path()` below returns the LIVE file, which is what a single-file
    rewrite needs — and for six versions this module used it as though it were the whole journal.
    It is not: `replay.load_journal` has read a generation ring since v779. The planner was fed
    the ring (via /api/sessions) and the applier rewrote one file of it, so every release against
    a session in the rotated half was a SILENT NO-OP. Measured: 2,483 of 2,840 sessions live in
    `sessions.1.jsonl`. That is why the river could not drain. [[copy-drift]] [[the-unjoined-end]]
    """
    try:
        import replay as _rp
        paths = list(_rp.journal_paths() or [])
        if paths:
            return paths
    except Exception:
        pass
    p = _journal_path()
    return [p] if os.path.exists(p) else []


_PAYLOAD_FIELDS = ("finds", "tallies", "intakes", "named", "chron", "registered",
                   "judged", "topFind")


def _carries_payload(s):
    """Which fields of this row still hold something. -> sorted list of names."""
    return sorted(k for k in _PAYLOAD_FIELDS if s.get(k))


def _banked_reels():
    """The reels whose finds are BANKED IN THE EVIDENCE LEDGER. -> (set | None, why_unknown | None)

    ⚠⚠ v3109 — THE THIRD ARTEFACT, AND THE FIRST ONE THAT ACTUALLY HOLDS THESE FIELDS. This asked
    `chronicle_swept.json` twice and both readings were wrong about the same thing:

        v3105  key present          -> "the reel was READ"        (a look, not a bank)
        v3107  pages >= 1           -> "the reel yielded pages"   (CHRONICLE pages, not these fields)

    A cross-family read of v3107 named the remaining hole exactly: `pages` counts chronicle pages
    landing in the EVIDENCE ledger, and `_PAYLOAD_FIELDS` — finds, tallies, intakes, named, chron,
    registered, judged, topFind — are not in `chronicle_swept.json` at all. A session can drop a
    Shako into the journal row AND have a Chronicle panel that banked a page: `pages >= 1` releases
    the row, and the sweep file still does not contain the Shako.

    So this reads the place those finds are ACTUALLY written: `chron_evidence.json`, whose
    `uniques`/`sets` entries carry per-sighting rows `{reel, frame, witness, conf, lane}`.
    MEASURED on his tree: it cites 29 distinct reels, and all 12 of the payload-carrying rows the
    planner would release are among them — so today the answer is unchanged and the MECHANISM is
    finally the right one, which is what matters when the two stop coinciding.

    ⚠⚠ BOTH SPELLINGS. control_app's v2800 scar measured this exact file: 4,106 witness rows carry
    `reel_`-prefixed ids and 4,411 carry BARE ones — a near 50/50 split of two conventions in one
    field — and "every lookup whose spelling did not match its directory reported the photo as
    ABSENT". A walker that accepts one spelling under-counts the bank and holds rows that are
    safe; on the other side of a different rule it would RELEASE rows that are not.

    ⚠ DELEGATE. `control_app._chron_evidence_load()` is the reader; this joins no path of its own.
    [[copy-drift]] [[unknown-stays-unknown]]
    """
    try:
        import control_app as _ca
        ev = _ca._chron_evidence_load()
        if not isinstance(ev, dict):
            return None, "the evidence ledger came back as %s, not a mapping" % type(ev).__name__
    except Exception as e:
        return None, "the evidence ledger could not be read (%s)" % type(e).__name__
    cited = set()

    def _walk(o):
        if isinstance(o, dict):
            r = o.get("reel")
            if isinstance(r, str) and r.strip():
                r = r.strip()
                cited.add(r[len("reel_"):] if r.startswith("reel_") else r)
            for v in o.values():
                _walk(v)
        elif isinstance(o, list):
            for x in o:
                _walk(x)

    _walk(ev)
    return cited, None


def _ledger_began():
    """When the retention ledger's FIRST deletion was recorded. -> (ms | None, why_unknown | None)

    ⚠⚠ v3113 — THE BOUNDARY OF KONYO'S AMNESTY, AND IT IS THE LEDGER'S OWN FIRST ENTRY ON PURPOSE.
    His ruling, 2026-09-14, after being shown that "drain to 8" and his own condition contradict
    each other for 2,385 rows: *"it can go.. whatever was in the past for here specifically its
    fine.. just make sure forward it is all working"*.

    MEASURED before asking him: the tombstone ledger's earliest deletion is 2026-08-24 23:49, and
    **2,385 of the 2,424 `unknown` rows (98.4%) are runs that STARTED BEFORE THAT**. Their film was
    gone before any instrument existed to record it going, so no record was ever written and none
    can be manufactured — which is exactly why his condition could never be satisfied for them and
    exactly what he is waiving.

    ⚠ THE CUTOFF IS DERIVED, NEVER A CONSTANT. A hardcoded date would be a number nobody could
    re-derive, and it would keep being true as the tree moves. Reading the ledger's own first entry
    means the amnesty covers precisely "older than the instrument" and cannot creep: the day a
    reel is tombstoned earlier, the boundary moves with it, and a run that started after the
    ledger existed is NEVER covered no matter how old it gets. That is the "just make sure forward
    it is all working" half, enforced by arithmetic rather than by intention.

    ⚠ DELEGATE. reel_retention owns the path. [[copy-drift]] [[unknown-stays-unknown]]
    """
    try:
        import reel_retention as _rr
        with io.open(_rr._tombstone_path(), encoding="utf-8") as fh:
            doc = json.load(fh) or {}
    except Exception as e:
        return None, "the retention ledger could not be read (%s)" % type(e).__name__
    stamps = []
    for e in (doc.get("reels") or []):
        if isinstance(e, dict) and e.get("deletedTs"):
            try:
                stamps.append(int(e["deletedTs"]))
            except Exception:
                continue
    if not stamps:
        return None, "the retention ledger records no deletion at all, so it has no beginning yet"
    return min(stamps), None


def plan(sessions, hist_dir=None, keep_recent=KEEP_RECENT):
    """Classify every journal row. -> dict. WRITES NOTHING.

    sessions: the /api/sessions payload rows (already carry footageState/footageWhy).
    """
    hist_dir = hist_dir or os.path.join(HERE, "frames", "hist")
    try:
        import frame_authority as _fa
        pinned = set(_fa.test_referenced_reels() or ())
    except Exception:
        pinned = None            # UNKNOWN -> hold everything that might be a fixture

    rows = [s for s in (sessions or []) if isinstance(s, dict)]
    dated = [s for s in rows if isinstance(s.get("t0"), (int, float))]
    dated.sort(key=lambda s: s.get("t0") or 0, reverse=True)
    newest = {str(s.get("sessionId") or "") for s in dated[:max(0, int(keep_recent))]}

    # ⚠⚠ v3105 — KONYO'S CONDITION, MADE A RULE INSTEAD OF A ONE-OFF CHECK. He approved the
    # deletion with one string attached: *"just make sure before it was tallied and extracted
    # properly"*. Measured on his live journal before writing this: of 447 releasable rows, 245
    # still carried payload (finds, tallies, intakes, named, chron, registered, topFind), 207 of
    # those had their reel recorded in the sweep memory — so the read survives the row — and
    # **38 appeared in no bank at all**, several of them carrying `finds` and `topFind`. Deleting
    # those 38 throws away the only trace of what they found.
    #
    # The film gate already enforces his rule on the OTHER side: reel_retention refuses to
    # tombstone on `zero-pages` ("that is 'this reader found nothing', not 'done'") and on
    # `panels-never-banked`, which quotes him directly — *"all of the reels get extracted with
    # information thats needed"* BEFORE the tombstone. This is the same sentence applied to the
    # journal ROW, which is what survives the film. [[join-gate-heart]]
    banked, bank_why = _banked_reels()
    began, began_why = _ledger_began()

    release, keep = [], []
    n_amnesty = 0
    for s in rows:
        sid = str(s.get("sessionId") or "")
        why = None
        if not sid:
            why = "this row carries no session id, so it can be neither dated nor matched to film"
        elif not isinstance(s.get("t0"), (int, float)):
            why = "this row cannot be dated, and 'the newest %d' is meaningless without an order" % keep_recent
        elif sid in newest:
            why = "one of the %d most recent runs — kept whatever its state says" % keep_recent
        elif pinned is None:
            why = "the fixture list could not be read, so every row is held rather than risk deleting one the suite opens by name"
        elif ("reel_" + sid) in pinned or sid in pinned:
            why = "the TEST SUITE opens this reel by name — releasing it turns a real check into a permanent skip"
        else:
            has, n = _film_on_disk(sid, hist_dir)
            if has:
                why = "its reel still holds %d frame(s) on disk — the river has not finished with it" % n
            elif (str(s.get("footageState") or "") != EXTRACTED
                  and not (began and isinstance(s.get("t0"), (int, float)) and s["t0"] < began)):
                # ⚠ KONYO'S AMNESTY IS THE `not (...)` ABOVE, AND IT IS DELIBERATELY NARROW. A run
                # that started BEFORE the retention ledger's first entry could never have been
                # recorded by it, so holding it for a missing record holds it forever. Everything
                # AFTER that instant is judged exactly as before — his "just make sure forward it
                # is all working". The only-trace hold below is NOT waived by this: a row that is
                # the only copy of a find is a different concern from a row with no retention
                # record, and he ruled on the second.
                why = ("footageState is %r, not %r — no film is not the same fact as extracted, "
                       "and an absence of evidence is not a proof"
                       % (str(s.get("footageState") or "none"), EXTRACTED))
            elif _carries_payload(s) and banked is None:
                why = ("this row still carries %s and %s, so whether any of it was banked is "
                       "UNKNOWN — and unknown holds on a path that deletes"
                       % (", ".join(_carries_payload(s)), bank_why))
            elif _carries_payload(s) and sid not in banked:
                # ⚠ THE EVIDENCE LEDGER IS THE ONLY ARTEFACT THAT HOLDS THESE FIELDS. A sweep key
                # is a look; a sweep page-count is a CHRONICLE yield; neither contains a find.
                why = ("this row still carries %s and the evidence ledger does not cite its reel — "
                       "nothing else holds what it found, so deleting the row throws away the only "
                       "trace of it" % ", ".join(_carries_payload(s)))
        if why is None:
            # ⚠⚠ v3113 — AN AMNESTY RELEASE MAY NOT WEAR THE PROOF'S LABEL. A cross-family read of
            # v3112 caught this on the one line he reads before approving a deletion: every
            # release said "film was retired after giving up its information" — with an EMPTY
            # tail, because a waived row has no footageWhy — and the summary said they "have a
            # proof of extraction". Measured on a fixture: `5 of 13 … have a proof of extraction`
            # when four had one and the fifth was the waiver. The waiver is exactly the case where
            # no proof exists; saying otherwise on a delete path is the worst place in this repo
            # for a right-sounding sentence. [[label-outlived-referent]]
            _amnesty = (str(s.get("footageState") or "") != EXTRACTED)
            if _amnesty:
                n_amnesty += 1
                release.append({"sessionId": sid, "t0": s.get("t0"), "amnesty": True,
                                "why": "released under his 2026-09-14 ruling: this run started "
                                       "before the retention ledger existed, so NO proof of "
                                       "extraction could ever have been written for it"})
            else:
                release.append({"sessionId": sid, "t0": s.get("t0"), "amnesty": False,
                                "why": "film was retired after giving up its information: %s"
                                       % str(s.get("footageWhy") or "")[:90]})
        else:
            keep.append({"sessionId": sid, "t0": s.get("t0"), "why": why})

    release.sort(key=lambda r: r.get("t0") or 0)          # oldest first, like reel_retention
    # ⚠ v3106 — THE PLAN NAMES THE CORPUS IT JUDGED, so `apply_plan` can refuse when the files
    # moved underneath it. A plan is a judgement ABOUT a set of files; applying it to a different
    # set is how a correct decision lands on the wrong rows.
    sources = []
    for _p in _journal_paths():
        try:
            sources.append({"path": _p, "rows": sum(1 for _l in
                                                    io.open(_p, encoding="utf-8", errors="replace")
                                                    if _l.strip())})
        except Exception:
            sources.append({"path": _p, "rows": None})
    return {"ok": True, "keepRecent": keep_recent, "rows": len(rows),
            "release": release, "keep": keep, "sources": sources,
            "counts": {"release": len(release), "keep": len(keep)},
            "amnesty": n_amnesty,
            # ⚠ THE SENTENCE SPLITS THE TWO REASONS, because they are different facts and he acts
            # on this line. A single count folding a proof and a waiver together is the label
            # defect one layer up from the rows themselves.
            "say": ("%d of %d journal row(s) could be released — %d with a proof of extraction and "
                    "%d under the pre-ledger ruling, which is a WAIVER and not a proof; %d stay. "
                    "NOTHING was written."
                    % (len(release), len(rows), len(release) - n_amnesty, n_amnesty, len(keep)))}








def main(argv=None):
    import json
    import urllib.request
    import console_port as _cport       # REG-2998 - the console's port (TV_PORT is the AGENT's), never :17772 by name
    with urllib.request.urlopen(_cport.url("/api/sessions") or "", timeout=120) as r:
        rows = json.loads(r.read().decode("utf-8", "replace")).get("sessions") or []
    p = plan(rows)
    print(p["say"])
    from collections import Counter
    print("\nWHY ROWS STAY (top reasons):")
    for w, n in Counter(k["why"][:72] for k in p["keep"]).most_common(8):
        print("   %5d  %s" % (n, w))
    print("\nRELEASABLE, oldest first (first 8 of %d):" % len(p["release"]))
    for r in p["release"][:8]:
        print("   %s" % r["sessionId"])
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ⚠⚠ v3113 — THE WRITER LIVES IN `journal_drain.py`, NOT HERE. `test_a_journal_row_leaves_only_on_
# proof.test_the_planner_cannot_write_anything` parses THIS FILE and refuses any write-capable
# call: "It exists to classify and explain; the apply half is a separate decision and it is his.
# There is no un-delete". `backup()` and `apply_plan()` were added here and made that registered
# gate RED for several versions. They moved rather than the law bending to fit them.
