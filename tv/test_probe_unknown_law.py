# -*- coding: utf-8 -*-
"""EVERY PROBE MUST BE ABLE TO SAY UNKNOWN, AND MUST SAY IT WHEN HANDED NOTHING.

⚠⚠ WHY THIS EXISTS, AND IT IS A PATTERN NOT AN INCIDENT. Four times on 2026-09-04 a fix shipped
the very class of defect it was fixing, one edit away:

    REG-534  two store filenames retyped instead of quoted
    REG-537  a snapshot frozen at import — written ONE LINE BELOW the fix for REG-534
    REG-540  a store path resolved two ways, in the module built to catch dead fields
    REG-541  a wholly unreadable store reporting OK — shipped INSIDE the fix for REG-540's crash,
             by the one module whose entire job is refusing to call the unmeasured clean

The rule was quoted correctly in every one of those commits. What failed was never the rule; it was
that **the NEW code was not re-asked the question the rule exists to ask.** A note cannot fix that.
A law can: every probe on this list is handed nothing, and must answer UNKNOWN rather than a
verdict. It runs against ALL of them, so the next probe added inherits the question automatically.

⚠ IT IS A LAW, NOT A ROSTER. It asserts the BEHAVIOUR (nothing in -> UNKNOWN out) rather than
pinning today's module list to a number, so adding a probe cannot make it stale — but an
ENTRY that stops existing is a refusal, because a probe silently dropped from this list is exactly
how the law stops covering the thing it was written for. [[unknown-stays-unknown]]
"""
import contextlib
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

def _nothing_for_funnel():
    """⚠ `one_funnel.funnel()` TAKES NO ARGUMENT, so unlike its three siblings its nothing-to-read
    path cannot be driven from outside at all — it always reads the live tree. That is a real
    difference in shape, stated rather than special-cased away: to exercise it, the SOURCE has to
    be emptied. Its own suite already does this, and doing it here keeps the law uniform across
    four probes that are not uniform.
    """
    import one_funnel as OF
    import reel_story as RS
    real = RS.story
    try:
        RS.story = lambda *a, **k: {"reels": []}
        return OF.funnel()
    finally:
        RS.story = real


#: Each entry is a probe that publishes a `state`, and a callable that asks it with NOTHING TO
#: READ. Each is here because a wrong CLEAN from it would be believed.
def _nothing_for_dead_field_state():
    """Point EVERY store resolver at nothing, so `state()` really has nothing to read.

    ⚠⚠ v2658 — THIS EMPTIED ONE OF TWO STORES AND THE LAW SILENTLY STOPPED COVERING THIS PROBE.
    It patched only `reel_retention._tombstone_path` and left `disk_history` readable. `state()`
    answers UNKNOWN only when EVERY store is UNKNOWN (`dead_field.py:400`), so with one store
    still readable and clean it answered **OK** — and all three laws here then compared OK against
    OK, or asserted UNKNOWN and got OK.

    ⚠ AND IT WAS INVISIBLE ON THE VENUE THAT RUNS IT. Both stores are gitignored
    (`.gitignore` tv/reel_tombstones.json, tv/disk_history.jsonl; `git ls-files` -> 0), so on a
    GitHub runner BOTH are absent, every store is UNKNOWN, and the stub's incompleteness cannot
    show. On his Mac `disk_history.jsonl` exists — 8,599 rows — so the probe is handed something
    and the law goes red. **Green on CI, red on the machine whose pre-push hook grades the tree.**
    That is `regression-guard` §3 inverted: not a test that needs his machine, but a stub whose
    hole only his machine can reveal.

    ⚠ THE PRODUCT IS NOT THE DEFECT HERE, and it was checked before this was changed. `state()`'s
    `why` said the honest thing all along — *"nothing was established for 1 of 2 store(s)
    (reel_tombstones) — that is UNKNOWN, not a clean bill"* — while the stub's premise, that the
    probe had been handed NOTHING, was simply false. Fixing the reading to match a broken stub
    would have been the wrong half. [[feedback-suspect-the-instrument]]
    """
    gone = os.path.join(HERE, ".no_such_store_ever.json")
    return _dead_field_state_over(gone)


def _dead_field_state_over(path):
    """`dead_field.state()` with EVERY store it reads pointed at `path`. -> reading

    ⚠ ONE ROUTINE, TWO CALLERS, ON PURPOSE. This same patching is needed by
    `_nothing_for_dead_field_state` above and by the `dead_field.state` case in
    `test_no_probe_CRASHES_ON_ITS_OWN_UNREADABLE_SOURCE` below, and BOTH copies had the identical
    hole — only `_tombstone_path` was patched, `disk_history` stayed readable, and `state()`
    answered OK. A stub that exists twice drifts, and here it did not even need to drift: the
    defect was written into both copies at once. [[copy-drift]] §7 — put the routine on the path
    every entry passes through, and make the other site CALL it.

    ⚠⚠ EXHAUSTIVE BY CONSTRUCTION, NOT BY A HAND-TYPED LIST. It reads `dead_field.WATCHED` and
    patches the resolver each entry NAMES, so a third store added tomorrow is emptied the day it
    appears. A hardcoded pair would patch two of three and the law would go vacuous silently —
    and only on a venue where that third store happens to exist, which is how this hole survived
    in the first place. `test_BASELINE_the_store_stub_really_empties_every_store` asserts it.
    """
    import importlib
    import dead_field as DF
    saved = []
    try:
        for entry in DF.WATCHED:
            mod_name, attr = entry[1]
            mod = importlib.import_module(mod_name)
            saved.append((mod, attr, getattr(mod, attr)))
            setattr(mod, attr, lambda *a, **k: path)
        return DF.state()
    finally:
        for mod, attr, real in saved:
            setattr(mod, attr, real)


def _nothing_for_reel_river():
    """Empty the shelf and the river has nothing to walk."""
    import reel_river as RR
    import reel_story as RS
    real = RS.story
    try:
        RS.story = lambda *a, **k: {"reels": []}
        return RR.river()
    finally:
        RS.story = real


def _nothing_for_printer():
    """Empty both of the printer's spine owners and it has nothing to walk."""
    import one_start_point as OSP
    import printer as P
    import reel_river as RR
    a, b = OSP.start_points, RR.river
    try:
        OSP.start_points = lambda *x, **k: {"ok": False, "rows": [], "state": "UNKNOWN",
                                            "counts": {}, "why": "x"}
        RR.river = lambda *x, **k: {"ok": False, "rows": [], "gaps": [], "why": "x"}
        return P.stream()
    finally:
        OSP.start_points, RR.river = a, b


def _nothing_for_printer_reach():
    """⚠⚠ THIS ONE FOUND A DEFECT THE DAY IT WAS ADDED (REG-543). `printer_reach.UNREACHABLE` was
    doing two jobs: *"I measured, and the contradiction is structurally impossible on this corpus"*
    — a real finding — and *"I could not read the seal store."* Only the `why` told them apart, so
    a store that failed to open read as the measured verdict. Splitting UNKNOWN out is what lets
    this probe join the law at all."""
    import frame_authority as FA
    import printer_reach as PR
    real = FA.sealed_sessions
    try:
        FA.sealed_sessions = lambda *a, **k: ({}, False)
        return PR.report()
    finally:
        FA.sealed_sessions = real


def _nothing_for_declared_vs_content():
    """Its source is the shelf; empty it and the sample cannot answer."""
    import declared_vs_content as DVC
    import reel_story as RS
    real = getattr(RS, "story", None)
    try:
        if real is not None:
            RS.story = lambda *a, **k: {"reels": []}
        return DVC.report()
    finally:
        if real is not None:
            RS.story = real


PROBES = (
    ("one_start_point.start_points",
     lambda: __import__("one_start_point").start_points(os.path.join(HERE, ".no_such_shelf_ever"))),
    ("one_funnel.funnel", _nothing_for_funnel),
    ("per_reel_routes.routes", lambda: __import__("per_reel_routes").routes([])),
    ("dead_field.dead_fields", lambda: __import__("dead_field").dead_fields(None)),
    ("dead_field.state", _nothing_for_dead_field_state),
    # ⚠⚠ REG-560 — `reel_river` FEEDS THE PRINTER AND WAS NEVER IN THIS LAW. It publishes a
    # reading, it is one of the printer's owners, and the shape law that exists to catch exactly
    # its defect could not see it — because nobody had put it in front of the law. It dropped
    # `clean` and `namelessRows` on its nothing-to-report path for as long as it has existed.
    ("reel_river.river", _nothing_for_reel_river),
    ("printer_reach.report", _nothing_for_printer_reach),
    ("printer.stream", _nothing_for_printer),
)

#: ⚠⚠ THE "REAL SHELF" USED TO BE *HIS* SHELF, AND ON A RUNNER THERE IS NO SHELF AT ALL.
#: `tv/frames/hist` and `tv/retro_triage.json` are gitignored — `git ls-files tv/frames | wc -l`
#: is **0** — so on a fresh checkout every ask below correctly answered UNKNOWN and THREE laws in
#: this file inverted: the shape law compared each probe against itself and its own anti-vacuous
#: guard fired ("answered 'UNKNOWN' to BOTH the empty ask and the real one"), and both BASELINEs
#: read the absence of footage as a probe that cannot reach a verdict. Measured 2026-09-05 in a
#: tracked-files-only checkout: 7 of the 8 asks below returned UNKNOWN, 3 tests failed, and the
#: SAME 3 failed on CI byte for byte.
#:
#: A law that only holds where his footage lives is a law that stops running the moment it leaves
#: his Mac — and skipping it there would have turned the whole file into a permanent skip nobody
#: notices. So the corpus is BUILT rather than borrowed: a shelf of six recorder-shaped reels plus
#: the three small stores these probes quote, identical on every machine. His corpus is still
#: measured — by each probe's own gate — and the constructed-refusal case below already says why
#: a synthetic tree reaches paths his 639 reels never do.
#: [[feedback-fixtures-never-touch-live-data]] [[regression-guard]] — a skip is not a pass.
_CORPUS = {}


def _corpus_shelf():
    """The synthetic shelf, built ONCE per process. -> path

    ⚠ Built eagerly by `setUpModule` rather than on first use, because two cases below break
    `open`/`os.listdir` process-wide before asking a probe — a corpus built lazily inside one of
    those would be built through the very calls they have disabled.
    """
    if _CORPUS.get("shelf"):
        return _CORPUS["shelf"]
    import atexit
    import json
    import shutil
    import tempfile
    d = tempfile.mkdtemp(prefix="probe_corpus_")
    atexit.register(shutil.rmtree, d, True)
    triage = {}
    for i in range(6):
        sid = "s_17569000000%d_%d" % (i, i)
        rd = os.path.join(d, "reel_" + sid)
        os.makedirs(rd)
        # the CORE shape one_start_point attributes to the recorder: sessionId, int n, list frames
        frames = [{"f": "%s_%03d.jpg" % (sid, k), "ts": 1756900000000 + k} for k in range(3)]
        with io.open(os.path.join(rd, "index.json"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"sessionId": sid, "n": len(frames), "frames": frames}))
        for fr in frames:
            with open(os.path.join(rd, fr["f"]), "wb") as fh:
                fh.write(b"\xff\xd8\xff\xd9")
        triage["reel_" + sid] = {"ts": 1756900000000 + i, "hits": 2, "frames": 3, "panels": 1}
    with io.open(os.path.join(d, "retro_triage.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(triage))
    # ⚠⚠ AND THE SEAL STORE, WITHOUT WHICH `printer_reach` READS A CORPUS OF ZERO SEALS. Its
    # `_load` joins the shelf with `frame_authority.SEAL_STORE`. Seals that name no `extracted`,
    # so the contract genuinely REFUSES them and the real ask reaches a MEASURED verdict.
    #
    # ⚠⚠ THIS FILE WAS EDITED AND REPORTED VERIFIED EARLIER THE SAME SESSION, AND THE VERIFICATION
    # COULD NOT HAVE SEEN THIS. Measured twice, independently, 2026-09-05 — probing from INSIDE
    # `_against_the_corpus()`:
    #
    #     vault_swept.json planted in the corpus?  False
    #     sealed_sessions() inside the corpus   ->  30 seals, ok=True
    #     his real tv/vault_swept.json          ->  30 seals
    #
    # The corpus this file's own comment above calls BUILT rather than borrowed was reading his
    # real seal store, because `sealed_sessions`' root falls back to `frame_authority.HERE` and the
    # hook list had no entry for it. On his Mac that leak made the shelf look complete; on a runner
    # the store is absent and the "REAL" ask was a corpus of ZERO seals — so both laws below were
    # comparing UNKNOWN against a verdict that only looked measured, and passing for a reason that
    # cannot hold on the venue they exist to protect. Two greens, neither earned.
    #
    # A verification run on the machine that owns the data cannot see a borrowed store: the borrow
    # is what makes it look right. That is the third escape of this shape found in one day — the
    # others were `board_sync.REPO`, a hardcoded absolute path that reached out of a `git archive`
    # export, and this file's own printer_reach hook. [[copy-drift]] [[the-unjoined-end]]
    with io.open(os.path.join(d, "vault_swept.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({sid: {"ts": 1756900000000, "rows": 2, "promptVer": "vpFixture"}
                             for sid in (k[len("reel_"):] for k in triage)}))
    # ⚠⚠ THE DURABLE-STORE ROOT, AND THE ORDER MATTERS: PLANT FIRST, REDIRECT SECOND.
    # `witness_index` is what decides `haveIndex`, and `haveIndex` is the input deciding whether
    # `reel_retention` HOLDS EVERY REEL. Redirecting the root at an empty corpus would flip it to
    # False and silently change a verdict — which is exactly why the earlier attempt was reverted
    # rather than kept with a comment claiming a containment it did not deliver.
    # MEASURED against his real tv/ before this existed: perStore = {vault_accum.json: 16,
    # vault_seen.json: 5} -> 9 sessions, 21 frames, haveIndex True. Only those TWO of the four
    # durable stores feed the index, so only those two need planting.
    # The contract is `frame_authority.witness_index`'s own loop: for each row, for each entry in
    # `witnesses`, take `w["session"]` and `basename(w["frame"])`. The rows below carry exactly
    # that and nothing invented — the session ids are the CORPUS's own, so the index it builds
    # describes this corpus rather than resembling his.
    # ⚠ THE SHAPE IS THE CONTRACT, AND MY FIRST CUT GOT IT WRONG. `_rows_of` reads
    # `blob["owned"]` or `blob["rows"]` and returns [] for anything else, so a bare dict keyed by
    # item name planted SIX rows that the index counted as ZERO — files present, perStore 0, and a
    # corpus that looks contained while measuring nothing. Read off his real stores rather than
    # guessed: vault_accum is {"owned": [...]}, vault_seen is {"rows": [...]}, and a witness is
    # {session, frame, lane, conf}.
    _sids = [k[len("reel_"):] for k in triage]
    _rows = [{"name": "fixture item %d" % _i, "lane": "stash", "kind": "unique",
              "count": 1, "conf": 0.9, "lastSeenTs": 1756900000000 + _i,
              "witnesses": [{"session": _sid, "frame": "%s_%03d.jpg" % (_sid, 0),
                             "lane": "stash", "conf": 0.85}]}
             for _i, _sid in enumerate(_sids)]
    with io.open(os.path.join(d, "vault_accum.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"owned": _rows, "added": [], "raised": [], "held": [], "byKey": {}}))
    with io.open(os.path.join(d, "vault_seen.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"rows": [{k: v for k, v in r.items() if k != "count"} for r in _rows],
                             "ts": 1756900000000}))
    # ⚠ `dead_field.MIN_ROWS` is 30 — under the floor a store is UNKNOWN, not clean — so both
    # watched stores get 32 rows with every column filled on at least one of them.
    with io.open(os.path.join(d, "reel_tombstones.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"reels": [{"reel": "reel_gone_%d" % k, "ts": 1756900000000 + k,
                                        "mb": 1.5, "why": "fixture"} for k in range(32)]}))
    with io.open(os.path.join(d, "disk_history.jsonl"), "w", encoding="utf-8") as fh:
        for k in range(32):
            fh.write(json.dumps({"ts": 1756900000000 + k, "freeGb": 100.0, "reels": 6,
                                 "histBytes": 4096, "eligibleMb": 1.5}) + u"\n")
    _CORPUS["shelf"] = d
    return d


@contextlib.contextmanager
def _against_the_corpus():
    """Point every shelf-and-store resolver these probes use at `_corpus_shelf()`, then put them
    back. The hooks are the tree's own: `TV_HIST` (which `tv_diablo._fixture_root` turns into the
    root for `reel_tombstones.json` and `disk_history.jsonl`), `tv_diablo.HIST_DIR` (frozen at
    import, so the env alone does not take), `reel_retention.plan`'s default shelf — which is
    HERE-relative and honours no env at all — and `printer_reach.TRIAGE`, a module constant.

    ⚠⚠ AND `frame_authority.sealed_sessions`, THE ONE RESOLVER THIS LIST USED TO OMIT. Its root
    defaults to `frame_authority.HERE`, so `printer_reach` read the REAL `tv/vault_swept.json`
    from inside a corpus this file's own comment calls "identical on every machine". On his Mac
    his 30 seals leaked in and the shelf looked complete; on a runner that store is absent, so the
    REAL ask was a corpus of ZERO SEALS and both laws below were comparing UNKNOWN against a
    verdict that only looked measured. MEASURED 2026-09-05 in a tracked-files-only checkout.
    [[copy-drift]] [[feedback-fixtures-never-touch-live-data]]

    ⚠ AND `one_funnel.HERE`, found by MEASURING rather than reading: with `open` instrumented,
    every FULL ask below was asked which DATA files it actually touched. `one_funnel.funnel` was
    opening the real `tv/retro_triage.json` and `tv/vault_swept.json` from inside the corpus —
    `one_funnel.py:128` joins its store name onto `HERE` at call time. It reads those for rung
    COVERAGE and not for its verdict, so nothing was ever red, which is exactly why it would have
    kept leaking.

    ⚠⚠ AND THE HOOK LIST IS STILL NOT COMPLETE — SAID HERE BECAUSE AN UNSTATED GAP BECOMES A
    FALSE CLAIM OF CONTAINMENT. Measured on HIS MAC 2026-09-05, after the two hooks above:

        one_funnel.funnel · per_reel_routes.routes · printer.stream · reel_river.river
        still open  vault_accum.json · vault_seen.json · vault_swept.json · chronicle_swept.json
        from the real tv/  —  4 of the 8 asks

    The path, from a captured stack rather than a guess: `reel_story.story` -> the `RR.plan` hook
    above -> `reel_retention.plan:371`, which calls `_durable_sessions(HERE)` and so passes
    `reel_retention.HERE` EXPLICITLY into `frame_authority.witness_index`. An explicit root means
    `witness_index`'s own `root or HERE` fallback never fires, so patching `frame_authority.HERE`
    does NOTHING here — tried, measured, still 4 of 8, and the hook was reverted rather than kept
    with a comment claiming a containment it did not deliver. The `RR.plan` hook redirects the
    SHELF and not the DURABLE-STORE ROOT: a half-redirect of the same shape
    `test_import_bound_paths.py` records for `board_sync.REPO`/`TASKS`.

    NOT fixed here, deliberately: the corpus carries no `vault_accum`/`vault_seen`, so redirecting
    that root would make `witness_index` report `haveIndex: False`, which is the input that decides
    whether `reel_retention` holds every reel. That is a verdict change and needs its own
    measurement, not a line added to a hook list at the end of an unrelated fix.

    ⚠ THE SWEEP'S FIRST RUN NAMED TWO MORE, AND BOTH WERE THE INSTRUMENT: macOS `/var` is a symlink
    to `/private/var`, so `abspath` on a tempdir compared unequal against itself. `realpath` on both
    sides and they had been inside the corpus all along. The same sweep on a RUNNER reported
    "0 of 8 contained" — also the instrument: a tree with no stores has nothing to leak, so
    containment cannot be measured there at all. [[feedback-suspect-the-instrument]]
    [[gate-blind-to-unexercised-input]]
    """
    import frame_authority as FA
    import one_funnel as OF
    import printer_reach as PR
    import reel_retention as RR
    import tv_diablo as TD
    shelf = _corpus_shelf()
    env, hist, plan, triage = os.environ.get("TV_HIST"), TD.HIST_DIR, RR.plan, PR.TRIAGE
    seals, funnel_here = FA.sealed_sessions, OF.HERE
    # ⚠⚠ THE HALF-REDIRECT THAT LEAKED FOUR ASKS. `RR.plan` below redirects the SHELF; it does not
    # touch the DURABLE-STORE ROOT. `reel_retention.plan:371` calls `_durable_sessions(HERE)` and
    # passes `reel_retention.HERE` EXPLICITLY into `witness_index`, so `witness_index`'s own
    # `root or HERE` fallback never fires and patching `frame_authority.HERE` does nothing — tried,
    # measured, still 4 of 8. The root that has to move is THIS one.
    rr_here = RR.HERE
    RR.HERE = shelf
    os.environ["TV_HIST"] = shelf
    TD.HIST_DIR = shelf
    RR.plan = lambda hist_dir=None, *a, **k: plan(hist_dir or shelf, *a, **k)
    PR.TRIAGE = os.path.join(shelf, "retro_triage.json")
    FA.sealed_sessions = lambda root=None: seals(root or shelf)
    OF.HERE = shelf
    try:
        yield shelf
    finally:
        RR.plan, TD.HIST_DIR, PR.TRIAGE = plan, hist, triage
        FA.sealed_sessions, OF.HERE = seals, funnel_here
        RR.HERE = rr_here
        if env is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = env


def _live(fn):
    """`fn`, asked against the corpus. -> callable"""
    def _run():
        with _against_the_corpus():
            return fn()
    return _run


def setUpModule():
    """⚠ The corpus is built here and nowhere else — see `_corpus_shelf`."""
    for name in ("dead_field", "one_funnel", "one_start_point", "per_reel_routes", "printer",
                 "printer_reach", "reel_retention", "reel_river", "reel_story", "tv_diablo"):
        __import__(name)          # so entering the corpus never imports under a broken `open`
    _corpus_shelf()


#: Each probe, and how to ask it with a REAL shelf. Used only by the shape law below — a reading's
#: key set must not depend on its verdict.
FULL = (
    ("one_start_point.start_points", _live(lambda: __import__("one_start_point").start_points())),
    ("one_funnel.funnel", _live(lambda: __import__("one_funnel").funnel())),
    ("per_reel_routes.routes", _live(lambda: __import__("per_reel_routes").routes())),
    ("dead_field.dead_fields",
     lambda: __import__("dead_field").dead_fields([{"a": 1, "z": None} for _ in range(40)])),
    ("printer_reach.report", _live(lambda: __import__("printer_reach").report())),
    ("printer.stream", _live(lambda: __import__("printer").stream())),
    # ⚠ REG-553 — `dead_fields` takes rows in memory, so the unreadable-source law never touched a
    # filesystem for it. `state()` is the entry point that actually READS, and it is the one a
    # consumer calls. Both are covered now.
    ("dead_field.state", _live(lambda: __import__("dead_field").state())),
    ("reel_river.river", _live(lambda: __import__("reel_river").river())),
)

#: ⚠ Probes whose FULL entry is handed data IN MEMORY and never touches a filesystem. The
#: unreadable-source law cannot ask them anything — breaking `open` changes nothing about a list
#: that is already in hand — so requiring UNKNOWN of them would be requiring a wrong answer. Named
#: with the reason rather than silently skipped, because an exemption nobody can see is how a law
#: quietly stops covering things. `dead_field.state` IS covered: it is the entry point that reads.
IN_MEMORY = ("dead_field.dead_fields",)

#: ⚠ NOT ON THE LIST, WITH THE REASON — because a probe missing silently is the failure this file
#: exists to prevent, and a probe missing with a REASON is a decision anyone can re-open:
#:
#:   declared_vs_content.report — its no-data path could not be driven from outside in the time
#:       this was written: emptying reel_story leaves its own reel-dir walk untouched, so the stub
#:       does not reach it. It is UNTESTABLE-aware (that IS its live verdict), so the question it
#:       would be asked here is one it already answers — but "already answers" is a claim I did not
#:       prove, and an unproven claim does not earn a line above. Open.
#:   store_owners.audit — publishes `ok`/`rows`/`why` and NO `state` at all. It is a different
#:       shape, not a probe that forgot to say UNKNOWN, and widening the law to cover it would
#:       change what the law means. Left out deliberately.
NOT_COVERED = ("declared_vs_content.report", "store_owners.audit")

#: The number of probes this law covered when it was last deliberately changed. It may only RISE:
#: adding a probe is free, removing one needs a reason written down, because the run stays green
#: either way. Kept as a constant so no test NAME has to restate it. [[label-outlived-referent]]
#:
#: ⚠⚠ AND IT WAS SET BELOW THE ACTUAL COUNT, WHICH IS A RATCHET THAT PERMITS A SILENT DROP. I wrote
#: 6 while PROBES held 7, so removing one left the floor satisfied and the run green — exactly the
#: silent loss this constant exists to catch. Found by a sabotage that removed a probe and PASSED.
#: A floor below the real number is not a floor, it is a formality.
FLOOR = 8

#: ⚠⚠ WHICH PROBES THE PER-PROBE UNREADABLE-SOURCE LAW REACHES, AND WHICH IT DOES NOT — because
#: its first cut covered THREE of six and nothing said so, which is how a law quietly means less
#: than its name. `per_reel_routes` and `printer.stream` read nothing themselves: their source is
#: other probes' modules, and breaking those is what the OWNERS' own cases already do. That is a
#: reason, not an excuse, and it is written down so the next reader can disagree with it.
OWN_SOURCE_UNTESTED = ("per_reel_routes.routes", "printer.stream", "reel_river.river")


class NothingInMustGiveUnknownOut(unittest.TestCase):

    def test_every_probe_answers_UNKNOWN_when_handed_nothing(self):
        for name, ask in PROBES:
            r = ask()
            self.assertIsInstance(r, dict, "%s did not return a reading" % name)
            state = r.get("state") or r.get("ladder")   # one_funnel publishes two readings
            self.assertEqual(
                state, "UNKNOWN",
                "%s was handed nothing and answered %r. Nothing-to-read is not a clean verdict — "
                "it is the ABSENCE of one, and a probe that rounds it up is the defect every probe "
                "on this list was written to prevent. why=%r"
                % (name, state, str(r.get("why"))[:160]))

    def test_the_reason_is_carried_not_just_the_word(self):
        """⚠ UNKNOWN with no reason is a shrug. A reader has to be able to tell 'the shelf is
        empty' from 'the shelf could not be read' — opposite facts about his footage."""
        for name, ask in PROBES:
            why = str((ask() or {}).get("why") or "").strip()
            self.assertTrue(why, "%s said UNKNOWN and gave no reason at all" % name)
            # ⚠ REG-557 — LENGTH ALONE IS AN ARBITRARY BAR AND `"x" * 25` PASSED IT. A reason
            # exists so a reader can tell *the shelf is empty* from *the shelf could not be read*,
            # which means it has to NAME something: the thing that was missing, the module that
            # would not answer, or the store that would not read. Two words of the probe's own
            # subject, or it is a shrug of the right length.
            self.assertGreater(len(why), 20,
                               "%s's reason is too short to distinguish anything: %r" % (name, why))
            subject = name.split(".")[0].replace("_", " ")
            named = (any(w in why.lower() for w in subject.split())
                     or any(w in why.lower() for w in
                            ("read", "import", "answer", "empty", "shelf", "store", "floor",
                             "reel", "found", "judged", "established")))
            self.assertTrue(
                named,
                "%s's reason is %d characters and names nothing a reader could act on: %r. It has "
                "to say WHAT was missing — the shelf, the store, the module that would not answer "
                "— or it is a shrug of the right length." % (name, len(why), why))

    def test_the_law_still_covers_every_probe_it_did(self):
        """⚠ It asserts BEHAVIOUR, not a roster — but a probe silently dropped from PROBES is
        exactly how a law stops covering the thing it was written for, and that deletion looks
        identical to a passing run. The count is the only thing that catches it."""
        # ⚠⚠ REG-557 — THE NAME SAID "four probes" WHILE THE ASSERTION SAID 5, AND THERE ARE NOW
        # SIX. A right number under a word that stopped being true, caught by a cold review of the
        # shipped bytes. The floor is a NAMED CONSTANT now and the test's name no longer carries a
        # count at all, so the two cannot drift apart again — a label that restates a number is a
        # label that will outlive it. [[label-outlived-referent]]
        self.assertGreaterEqual(
            len(PROBES), FLOOR,
            "a probe was removed from this law. Adding one is free; removing one needs a reason "
            "written down, because the run stays green either way.")

    def test_the_per_probe_law_says_which_probes_it_does_NOT_reach(self):
        """⚠⚠ Its first cut reached THREE of six and nothing said so. A law that covers half its
        subjects while carrying a name that implies all of them is the same defect as a probe that
        rounds UNKNOWN up — it claims more than it measured. Every probe in FULL must either have
        an own-source case or be named, with a reason, in OWN_SOURCE_UNTESTED."""
        import inspect
        src = inspect.getsource(type(self).test_no_probe_CRASHES_ON_ITS_OWN_UNREADABLE_SOURCE)
        for name, _ in FULL:
            if name in IN_MEMORY or name in OWN_SOURCE_UNTESTED:
                continue
            self.assertIn('"%s"' % name, src,
                          "%s has no own-source case and is not named in OWN_SOURCE_UNTESTED, so "
                          "nobody can tell whether this law reaches it" % name)

    def test_OK_means_the_same_thing_in_every_probe(self):
        """⚠⚠ REG-556, from the cold look at v2554. `dead_field.state()` returned `ok: True` while
        its state was UNKNOWN; `one_start_point` and `per_reel_routes` return `ok: False` for
        exactly that state. **A consumer branching on `ok` got opposite answers from probes meant
        to be uniform** — the copy-drift defect applied to a MEANING rather than a filename, which
        no filename check could ever have caught.

        The rule, once: `ok` is False when nothing was established. Asked of every probe that
        publishes one, in both directions — UNKNOWN must be `ok: False`, and a real verdict must
        be `ok: True`, or the field would just be a second name for the state.
        """
        for name, ask in PROBES:
            r = ask()
            if "ok" not in r:
                continue
            st = r.get("state") or r.get("ladder")
            if st != "UNKNOWN":
                continue
            self.assertIs(r["ok"], False,
                          "%s says ok=%r while nothing was established. Its siblings say False, "
                          "and a consumer branching on `ok` gets opposite answers from probes that "
                          "are meant to be uniform." % (name, r["ok"]))
        for name, ask in FULL:
            r = ask()
            if "ok" not in r:
                continue
            st = r.get("state") or r.get("ladder")
            if st == "UNKNOWN":
                continue
            self.assertIs(r["ok"], True,
                          "%s reached the verdict %r and still says ok=%r, so `ok` is not "
                          "reporting whether anything was established" % (name, st, r["ok"]))

    def test_every_IN_MEMORY_exemption_is_real(self):
        """⚠ An exemption is a hole in a law, so it has to be checkable. Each name in IN_MEMORY
        must actually be in FULL (or it is a stale entry silently exempting nothing) and must NOT
        be the filesystem-reading sibling — `dead_field.state` reads and is covered; only
        `dead_field.dead_fields`, handed rows in memory, is exempt."""
        names = [n for n, _ in FULL]
        for n in IN_MEMORY:
            self.assertIn(n, names, "%s is exempted but is not in FULL — a stale exemption "
                                    "silently covers nothing" % n)
        self.assertIn("dead_field.state", names,
                      "the filesystem-reading entry point is not in the law, so the exemption for "
                      "its in-memory sibling leaves that module unasked entirely")

    def test_every_probe_left_OUT_carries_a_reason(self):
        """⚠⚠ A probe missing from PROBES silently is the exact failure this file exists to
        prevent, and the count check above cannot see one that was never added. So the ones left
        out are NAMED, and this pins that the list of exclusions is not empty — an empty
        NOT_COVERED would mean either everything is covered (say so by adding them) or somebody
        deleted the reasons."""
        self.assertTrue(NOT_COVERED,
                        "no probe is recorded as deliberately left out. If everything is covered, "
                        "add it to PROBES; if something is not, it needs a reason here.")
        for name in NOT_COVERED:
            self.assertNotIn(name, [n for n, _ in PROBES],
                             "%s is both covered and listed as not covered" % name)

    def test_printer_reach_tells_UNKNOWN_apart_from_UNREACHABLE(self):
        """⚠⚠ REG-543, and it is why this probe could join the law at all. `UNREACHABLE` meant
        BOTH *"I measured, and the contradiction is structurally impossible"* — a real finding —
        AND *"I could not read the seal store."* Only the `why` told them apart, so a consumer
        branching on `state` could not, and an unopenable store read as the measured verdict."""
        import printer_reach as PR
        self.assertEqual(_nothing_for_printer_reach().get("state"), "UNKNOWN")
        # ⚠ ASKED OF THE CORPUS, NOT OF HIS TREE. `printer_reach.TRIAGE` is `tv/retro_triage.json`,
        # which is gitignored, so on a runner the readable side answered UNKNOWN too and this
        # assertion inverted — the split reading as collapsed when the only thing missing was the
        # store. The two sides now differ by ONE variable, which is what the split claims.
        with _against_the_corpus():
            live = PR.report().get("state")
        self.assertNotEqual(
            live, "UNKNOWN",
            "the live tree now reports UNKNOWN too, so the split collapsed the other way and the "
            "real measured finding has been lost")

    def test_a_readings_SHAPE_does_not_depend_on_its_VERDICT(self):
        """⚠⚠ REG-546, and it is the FIFTH instance of one pattern in a day — a fix shipping the
        class it was fixing. REG-544 caught `dead_fields` omitting `judged`/`skipped` on its
        UNKNOWN paths; the SAME defect shipped in the SAME batch inside `printer.stream`, whose
        UNKNOWN return dropped `walked`, `unknownStations`, `stations` and `owners`. **A consumer
        reading those raised KeyError on exactly the path that means nothing was established — the
        reading breaks in the state it exists to report.**

        The word-level law above could not see it, because both readings said UNKNOWN correctly.
        So the shape is checked mechanically too: ask each probe with NOTHING and with a REAL
        shelf, and the key sets must match. This is what would have caught the fifth instance
        without anyone remembering.
        """
        empty = dict(PROBES)
        full = dict(FULL)
        # ⚠⚠ REG-548, from the cold look at v2546 — THE LOOP ITERATES `FULL`, so a probe in PROBES
        # and NOT in FULL is never fetched and never shaped, silently. Adding a probe to one list
        # and forgetting the other leaves it unguarded while the run stays green, which is the
        # failure this whole file exists to prevent, one level up.
        self.assertEqual(
            sorted(set(empty) - set(full)), [],
            "these probes are asked with NOTHING but never shaped against a real dataset, so "
            "their key sets are unguarded and the run stays green: %s"
            % sorted(set(empty) - set(full)))
        for name, ask_full in FULL:
            ask_empty = empty.get(name)
            self.assertTrue(ask_empty, "%s is in FULL but not in PROBES" % name)
            a, b = ask_empty(), ask_full()
            # ⚠⚠ REG-548 — AND A PROBE WHOSE TWO CALLS RETURN THE SAME THING PASSES VACUOUSLY.
            # `set(b) - set(a)` is empty when a IS b, so a probe whose "empty" stub does not
            # actually empty anything would be compared against itself and prove nothing. The two
            # calls must reach DIFFERENT states, or the fixture is the defect, not the subject.
            # [[feedback-blind-fixture-green-gate]]
            sa = a.get("state") or a.get("ladder")
            sb = b.get("state") or b.get("ladder")
            self.assertNotEqual(
                sb, sa,
                "%s answered %r to BOTH the empty ask and the real one, so the two calls are not "
                "distinguishing anything and its shape was compared against itself. The stub is "
                "not emptying what this probe reads." % (name, sa))
            self.assertIsInstance(a, dict, "%s empty reading is not a dict" % name)
            self.assertIsInstance(b, dict, "%s full reading is not a dict" % name)
            missing = sorted(set(b) - set(a))
            self.assertEqual(
                missing, [],
                "%s drops %s when it has nothing to report, so a caller reading them breaks on "
                "exactly the path that means NOTHING WAS ESTABLISHED. A shape that changes with "
                "the verdict is not a shape." % (name, missing))

    def test_every_ROW_in_a_reading_agrees_with_its_siblings_on_shape(self):
        """⚠⚠ REG-549, and it closes the mesh one level down from REG-547.

        The reading-level law compares TOP-LEVEL key sets. REG-547 was a shape defect nested two
        levels below that, and I fixed it by hand in one file — which leaves every OTHER nested
        reading unguarded. This asks it generically: within one reading, every row must carry the
        same keys, because a row that drops a key on its refusal path breaks a consumer walking
        the list on exactly the rows that went wrong.

        ⚠⚠ AND THE FIRST DEFECT IT FOUND WAS LATENT. `one_start_point` dropped `frames` and
        `blankFlagged` on its two refusal rows — and **his shelf has no reel with a missing or
        unparseable index**, so every LIVE reading showed one uniform shape and nothing would ever
        have revealed it. It took a CONSTRUCTED tree. *All rows agree today* is a fact about his
        corpus, not about the function, so this law is driven by BOTH.
        """
        for name, ask in FULL:
            r = ask()
            for key in ("rows", "stores"):
                rows = [x for x in (r.get(key) or []) if isinstance(x, dict)]
                if len(rows) < 2:
                    continue
                shapes = set(frozenset(x) for x in rows)
                if len(shapes) > 1:
                    u = set().union(*[set(x) for x in shapes])
                    i = set.intersection(*[set(x) for x in shapes])
                    self.fail("%s.%s has %d different row shapes; %s are missing from some rows. "
                              "A consumer walking the list breaks on exactly the rows that went "
                              "wrong." % (name, key, len(shapes), sorted(u - i)))

    def test_a_CONSTRUCTED_refusal_row_keeps_the_full_shape(self):
        """⚠ The law above runs on HIS shelf, which exercises only the happy path — so the refusal
        rows are built here on purpose. This is the case that found REG-549."""
        import json
        import shutil
        import tempfile
        import one_start_point as OSP
        d = tempfile.mkdtemp(prefix="probe_shape_")
        self.addCleanup(shutil.rmtree, d, True)
        for nm, idx in (("reel_s_1", {"sessionId": "s_1", "n": 1,
                                      "frames": [{"f": "a.jpg", "ts": 1}]}),
                        ("reel_s_2", None),
                        ("reel_s_3", "{ not json")):
            os.makedirs(os.path.join(d, nm))
            if idx is not None:
                with open(os.path.join(d, nm, "index.json"), "w") as fh:
                    fh.write(idx if isinstance(idx, str) else json.dumps(idx))
        rows = OSP.start_points(d)["rows"]
        self.assertEqual(len(rows), 3, "the constructed tree was not walked: %s" % rows)
        doors = sorted(r["door"] for r in rows)
        self.assertEqual(doors, ["UNKNOWN", "UNREADABLE", "recorder"],
                         "BASELINE: the three refusal paths were not all reached: %s" % doors)
        shapes = set(frozenset(r) for r in rows)
        self.assertEqual(len(shapes), 1,
                         "a reel whose birth could not be read gets a THINNER row than one that "
                         "could: %s" % [sorted(x) for x in shapes])

    def test_BASELINE_the_store_stub_really_empties_every_store(self):
        """★ ANTI-VACUITY for the stub itself, and it is the guard this file most needed.

        Three laws below ask `dead_field.state` what it says when handed NOTHING. All three were
        passing OK-against-OK on his Mac because the stub emptied ONE of two stores — it never
        handed the probe nothing at all, so the laws compared a reading against itself and could
        not have failed for their own reason.

        A stub is an instrument. This asserts the instrument WORKED before any verdict built on it
        is believed: every store `dead_field.WATCHED` declares must come back UNKNOWN, and the
        count must equal the number declared — so adding a store the stub cannot reach fails HERE,
        loudly, instead of quietly making three laws vacuous somewhere else.
        [[feedback-suspect-the-instrument]] [[feedback-blind-fixture-green-gate]]
        """
        import dead_field as DF
        r = _nothing_for_dead_field_state()
        self.assertEqual(len(r["stores"]), len(DF.WATCHED),
                         "the stub reached %d store(s) but dead_field declares %d — a store it "
                         "cannot empty makes every law over this probe vacuous: %s"
                         % (len(r["stores"]), len(DF.WATCHED), r))
        not_unknown = [s["store"] for s in r["stores"] if s["state"] != "UNKNOWN"]
        self.assertEqual(not_unknown, [],
                         "%s stayed READABLE while the stub claimed to hand this probe nothing, "
                         "so the laws below compared a real reading against itself. This is the "
                         "exact hole that made them pass on CI (where every store is gitignored "
                         "and therefore absent) and fail on his Mac (where disk_history.jsonl "
                         "has 8,599 rows). Reading: %s" % (not_unknown, r))
        self.assertEqual(r["state"], "UNKNOWN",
                         "every store is UNKNOWN and the headline still is not: %s" % r)

    def test_no_probe_CRASHES_ON_ITS_OWN_UNREADABLE_SOURCE(self):
        """⚠⚠ REG-554 — THE FIRST VERSION OF THIS LAW PASSED FOR THE WRONG REASON, and a cold
        review's unrelated question is what exposed it.

        It patched `os.listdir`, `builtins.open` and `io.open` globally and required UNKNOWN.
        Measured with a sentinel in the exception message: **only 1 of 6 probes ever reported the
        blocked read.** The rest answered UNKNOWN because the patch broke the IMPORT MACHINERY —
        `one_start_point` said *"the recorder would not import"* — so they never reached their own
        read at all. The law claimed to prove *a probe survives an unreadable source* and actually
        proved *a probe survives a process where nothing can be opened, including imports*. Every
        one of them passed, and five passed vacuously.

        So each probe's OWN source is broken instead of the world's: a path that exists and cannot
        be read as what the probe expects. And the reading must NAME the failure — a probe that
        answers UNKNOWN for an unrelated reason is exactly the vacuous pass this replaces.
        """
        import shutil
        import tempfile
        d = tempfile.mkdtemp(prefix="unreadable_")
        self.addCleanup(shutil.rmtree, d, True)
        # a DIRECTORY where each probe expects a FILE — a real read error at the real read site,
        # reached through the probe's own code rather than through a broken interpreter.
        trap = os.path.join(d, "trap.json")
        os.makedirs(trap)

        import reel_retention as RR

        cases = (
            ("one_start_point.start_points",
             lambda: __import__("one_start_point").start_points(os.path.join(d, "no_shelf")),
             "state"),
            # ⚠ v2658 — this patched ONLY `_tombstone_path`, so `disk_history` stayed readable and
            # `state()` answered OK over a source it could not read. Same hole as
            # `_nothing_for_dead_field_state`, written twice; both now call the one routine.
            ("dead_field.state", lambda: _dead_field_state_over(trap), "state"),
            # ⚠ MY FIRST CUT PATCHED THE WRONG THING AND THE LAW BLAMED THE PROBE. I swapped
            # `retro_triage.STORE`, assuming printer_reach quoted it; it reads its own module
            # constant `TRIAGE`. The probe answered its real measured verdict and the law called
            # that a defect. Suspect the instrument first — it was the instrument.
            ("printer_reach.report",
             self._with(__import__("printer_reach"), "TRIAGE", trap,
                        lambda: __import__("printer_reach").report()),
             "state"),
            # ⚠ REG-555 — one_funnel was NOT in this law's first cut, and asking it found a real
            # defect: with both waypoint stores unreadable it reported the passage UNRECORDED, a
            # claim about his pipeline made over evidence nobody gathered.
            # ⚠⚠ AND THIS ONE PUBLISHES TWO READINGS. `one_funnel` answers a LADDER and a
            # PASSAGE; breaking its waypoint stores blinds the passage and leaves the ladder
            # legitimately readable, because the ladder comes from reel_story. The law's first cut
            # demanded UNKNOWN of the whole reading and FAILED a probe that was answering
            # correctly — the same coarse-mesh mistake in a new place. A case names WHICH reading
            # its broken source feeds.
            ("one_funnel.funnel", self._two_stores_unreadable(trap), "passage"),
        )
        for name, ask, key in cases:
            try:
                r = ask()
            except Exception as e:
                self.fail("%s RAISED %s on its OWN unreadable source. A probe that crashes goes "
                          "silent exactly when things are unusual: %s"
                          % (name, type(e).__name__, str(e)[:90]))
            st = r.get(key) if key in r else (r.get("state") or r.get("ladder"))
            self.assertEqual(st, "UNKNOWN",
                             "%s answered %r for %r over a source it could not read. why=%r"
                             % (name, st, key, str(r.get("why"))[:140]))

    def _two_stores_unreadable(self, trap):
        """one_funnel reads through TWO owners, so both have to break for its passage to be blind."""
        def _run():
            import frame_authority as FA
            import one_funnel as OF
            import retro_triage as RT
            rt, fa = RT.STORE, FA.SEAL_STORE
            try:
                RT.STORE = FA.SEAL_STORE = os.path.basename(trap)
                return OF.funnel()
            finally:
                RT.STORE, FA.SEAL_STORE = rt, fa
        return _run

    def _with(self, mod, attr, value, fn):
        """Run `fn` with `mod.attr` replaced, restoring it afterwards. -> callable"""
        def _run():
            real = getattr(mod, attr)
            try:
                setattr(mod, attr, value)
                return fn()
            finally:
                setattr(mod, attr, real)
        return _run

    def test_the_GLOBAL_patch_reaches_at_least_one_probes_read(self):
        """⚠ BASELINE that the OLD law lacked. Patching the world is still worth doing — it is how
        `printer_reach` was shown to handle a read failure — but it must be shown to reach a READ
        rather than an import, or it proves nothing. This asserts the sentinel actually appears in
        at least one probe's reason."""
        import builtins
        rl, ro, ri = os.listdir, builtins.open, io.open

        def _boom(*a, **k):
            raise PermissionError("BLOCKED-SENTINEL")

        seen = []
        for name, ask in FULL:
            if name in IN_MEMORY:
                continue
            try:
                os.listdir, builtins.open, io.open = _boom, _boom, _boom
                try:
                    r = ask()
                except Exception:
                    r = {}
            finally:
                os.listdir, builtins.open, io.open = rl, ro, ri
            if "BLOCKED-SENTINEL" in str(r.get("why") or ""):
                seen.append(name)
        self.assertTrue(
            seen,
            "the global patch reached NO probe's actual read — every UNKNOWN it produces would be "
            "an import failure wearing the right word, which is a law passing for the wrong reason")

    def test_no_probe_CRASHES_when_the_whole_process_cannot_open_anything(self):
        """⚠⚠ REG-552 EXPOSED A HOLE IN THIS LAW ITSELF. Every case above asks a probe with a
        source that is MISSING or EMPTY — and `one_start_point` handled those and **raised** on a
        source that EXISTS and cannot be READ, because `os.listdir` propagated a PermissionError.
        A probe that crashes goes silent exactly when the filesystem is unusual, which is when you
        need it most.

        Missing and unreadable are different failures and only one of them was being asked. This
        breaks `os.listdir` and `io.open` under every probe and requires an ANSWER — any answer,
        UNKNOWN or otherwise — rather than an exception.
        """
        import builtins
        real_listdir, real_open, real_io = os.listdir, builtins.open, io.open
        # v3849 - a reader may take the last plan this process finished (reel_retention.plan_for_reader), and an
        # earlier case in this file leaves one. This case is "nothing could be read AND nothing is held", so it
        # starts from no held plan; a held plan is memory, not a read, and is not this case's subject.
        import reel_retention as _RR
        _RR._forget_plans()

        def _boom(*a, **k):
            raise PermissionError("denied")

        for name, ask in FULL:
            try:
                os.listdir, builtins.open, io.open = _boom, _boom, _boom
                try:
                    r = ask()
                except Exception as e:
                    self.fail("%s RAISED %s when its source could not be read. A probe that "
                              "crashes goes silent exactly when things are unusual: %s"
                              % (name, type(e).__name__, str(e)[:80]))
            finally:
                os.listdir, builtins.open, io.open = real_listdir, real_open, real_io
            self.assertIsInstance(r, dict, "%s did not return a reading" % name)
            # ⚠⚠ REG-553 — REQUIRING A DICT WAS NOT ENOUGH. A probe that swallows everything and
            # answers OK on an unreadable filesystem would have PASSED this law — the
            # unmeasured-reads-as-clean defect, inside the law written to prevent it. Found by
            # measuring what the probes actually SAY under a broken filesystem rather than
            # assuming the law covered it.
            if name in IN_MEMORY:
                continue          # nothing on disk to break; see IN_MEMORY
            st = r.get("state") or r.get("ladder")
            self.assertEqual(
                st, "UNKNOWN",
                "%s answered %r when NOTHING on the filesystem could be read. Nothing established "
                "is UNKNOWN; any other word is a verdict over evidence that was never gathered. "
                "why=%r" % (name, st, str(r.get("why"))[:140]))

    def test_BASELINE_these_probes_can_reach_a_real_verdict(self):
        """⚠⚠ Or the law above passes on four functions that answer UNKNOWN to everything, which
        would be a guard proving the opposite of what it claims. Each is handed real input and must
        NOT say UNKNOWN."""
        import dead_field as DF
        import one_funnel as OF
        import per_reel_routes as PRR
        rows = [{"reel": "reel_%d" % i, "deletedTs": 1, "z": None} for i in range(40)]
        self.assertNotEqual(DF.dead_fields(rows).get("state"), "UNKNOWN",
                            "dead_fields cannot reach a verdict at all")
        self.assertNotEqual(
            PRR.routes([{"reel": "reel_a", "tag": "zero-pages", "stage": "swept"}]).get("state"),
            "UNKNOWN", "per_reel_routes cannot reach a verdict at all")
        # ⚠ `funnel()` takes no argument, so the only way to hand it reels is to point the shelf
        # it reads at one. It used to read the live tree — and a runner's tree has no reels, so
        # this BASELINE read "no footage on this machine" as "this probe can never reach a
        # verdict", which is the opposite of what it asserts.
        with _against_the_corpus():
            got = OF.funnel()
        self.assertNotEqual(got.get("ladder"), "UNKNOWN",
                            "one_funnel cannot reach a verdict at all: %s" % got.get("why"))


RED_PROOF = [
    {
        'why': 'Deletes the ONLY nothing-to-read branch in per_reel_routes.routes() (line 104), the code that makes the probe say UNKNOWN over an empty shelf; without it the probe answers POLICY_ONLY — a verdict over evidence never gathered, the exact defect this gate forbids. Anchor is executable code, occurs exactly once, and is not shared with any agreement law. Measured: untampered OK (16 tests), tampered FAILED (failures=2), the named law fails ALONE, restored with git checkout and green again (16 tests, OK). Path check: heart2 joins onto tv/ → tv/per_reel_routes.py, which exists.  MEASURED: untampered tv/test_probe_unknown_law.py: Ran 16 tests in 3.861s — OK (green before the tamp; tampered (all 1) Ran 16 tests in 3.557s — FAILED (failures=2): test_every_probe_answers_UNKNOWN_w; reddened law test_probe_unknown_law.NothingInMustGiveUnknownOut.test_every_probe_an; ALONE FAILED (failures=1) in a fresh process — `python3 -m unittest test_probe_unknown_law.NothingInMustGi.',
        'file': 'per_reel_routes.py',
        'find': 'if not rows:',
        'replace': 'if False:',
        'matches': 1,
    },
]


if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    unittest.main(verbosity=2)
