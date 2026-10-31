"""THE REEL'S STORY — where each reel stands, and how much of the film was worth keeping.

Konyo, 2026-09-01: "reels need to be visually connected to the backend coding of the pruning and
optimization and extracting process.. so maybe it can also be visually structured as such within
THE SHELF so its logically showing visually whats happening and needs to happen storyline synced
to the process" — and then: "those filters we mentioned the 10-15% of real footage and the other
70%+ was useless.. maybe that statistically can be also rendering and shown? as the filtering and
routing processes happen? so visually in retrospect we can surgically fix anything out of line".

⚠ THIS MODULE DECIDES NOTHING. Every stage below is read from the code that already decides it —
`reel_retention.plan()` for the verdict, `retro_triage` for the yield. A second opinion about
which reels may go would be a second prune authority, and two authorities disagreeing over
footage that has no un-delete is the worst outcome available here. If a stage looks wrong on
screen, the fix belongs in the decider, not in this file.

THE STAGES, and the function that decides each one:

    FILMED            the reel directory exists                    reel_retention.plan() -> onDisk
    TRIAGED           a structural verdict was recorded            retro_triage.load()
    SWEPT             the chronicle lane read it                   plan(): pages > 0
    BANKED            its rows reached the durable ledger          plan(): tag != rows-not-banked
    VAULT DONE        the vault lane is finished with it           plan(): tag != vault-owes
    RELEASABLE        both lanes done; it may be pruned            plan(): tag == eligible
    PRUNED            gone, tombstoned                             reel_retention._tombstone

A reel that has not REACHED a stage is "not yet" — never "failed". A reel nobody has measured is
UNKNOWN, and UNKNOWN is not zero: `yield: None` means nobody surveyed it, `yield: 0.0` means it
was surveyed and carried nothing. Collapsing those two is a lie with no author.
[[unknown-stays-unknown]] [[stale-reading]]
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))

# The order a reel moves through. Index into this is the reel's progress.
STAGES = ("filmed", "triaged", "swept", "banked", "vault-done", "releasable")

# Which stage a plan() tag says the reel is STUCK BEFORE. A tag not in here does not mean the
# reel is fine — it means this map has not been taught about it, which is why _stage_of refuses
# rather than guessing. Keyed on the tags reel_retention.RULES actually emits.
TAG_STAGE = {
    "no-witness-index":   "triaged",     # nothing can prove the frames are not the only record
    "ledger-unreadable":  "triaged",     # our picture of what is banked is unknown, for every reel
    "never-chronicle-swept": "swept",
    "zero-pages":         "swept",       # swept, and the sweep found nothing to read
    # ⚠ v2875 — STUCK BEFORE `banked`, NOT BEFORE `swept`. A reel wearing this HAS been swept and
    # HAS been surveyed: the survey is what found the panels. What has not happened is the
    # extraction — the vault ledger holds no row from it, so its stash rows live only in the
    # frames. Drawing it as stuck at `swept` would say the reader never got there; it did, and the
    # information simply never reached a store. Sits beside rows-not-banked because it is the same
    # lane at a different count: that one fires when rows exist and are not durable, this one when
    # the count is ZERO and the panels are real. [[label-outlived-referent]]
    "panels-never-banked": "banked",
    "rows-not-banked":    "banked",
    "vault-owes":         "vault-done",
    # v2848 — TAUGHT, not guessed. `holds-proof` (reel_retention v2815) fires from the LAST
    # position in plan()'s chain, after vault-owes and immediately before eligible, so a reel
    # wearing it has already passed every lane: swept, banked, vault-done. It is finished and
    # held — like `recent` and `test-fixture` — because its frames are the receipt for a named
    # chronicle claim, or because the receipt store could not be read at all. Mapping it any
    # earlier would draw a completed reel as stuck in a lane plan() says it cleared.
    "holds-proof":        "releasable",
    "recent":             "releasable",  # finished, held only by the age floor
    "test-fixture":       "releasable",  # finished, held because the suite opens it
    "target-met":         "releasable",  # finished and eligible; the run simply stopped early
    "eligible":           "releasable",
}

# Tags that mean "held for a reason that is ABOUT THIS REEL'S EVIDENCE" versus "held by policy".
# The distinction matters on screen: the first is a gap in the pipeline, the second is the
# pipeline working as designed, and painting them the same colour is how a real blocker gets
# ignored.
POLICY_HOLDS = frozenset(("recent", "test-fixture", "target-met"))
GLOBAL_HOLDS = frozenset(("no-witness-index", "ledger-unreadable"))


def _stage_of(tag):
    """(stage, reached_index). Returns (None, -1) for a tag this map has never been taught.

    ⚠ AN UNKNOWN TAG MUST NOT DEFAULT TO 'filmed' OR TO 'releasable'. The first would draw a
    finished reel as untouched; the second would draw a held reel as ready to delete. Both are
    confident pictures of something nobody established.
    """
    st = TAG_STAGE.get(tag)
    if st is None:
        return None, -1
    return st, STAGES.index(st)


def _yield_of(triage_blob, reel):
    """(panels, frames, ratio) or (None, None, None) when nobody surveyed this reel.

    None is not 0.0. A reel nobody looked at and a reel that was looked at and carried nothing
    are opposite facts, and only one of them is a reason to prune.
    """
    e = (triage_blob or {}).get(reel)
    if not isinstance(e, dict):
        return None, None, None
    f = int(e.get("frames") or 0)
    p = int(e.get("panels") or 0)
    if f <= 0:
        return p, f, None          # surveyed, but no frames — a ratio would divide by zero
    return p, f, p / float(f)


def story(hist_dir=None):
    """The whole board. Writes nothing, decides nothing, and names what it could not establish."""
    import reel_retention as RR
    try:
        import retro_triage as RT
    except Exception:
        RT = None

    plan = RR.plan_for_reader(hist_dir=hist_dir)
    if not isinstance(plan, dict) or not plan.get("ok"):
        plan = RR.plan(hist_dir=hist_dir)
    if not plan.get("ok"):
        # A plan that could not run is not an empty shelf. Say so, and let the caller print it.
        return {"ok": False, "why": plan.get("why") or "reel_retention.plan() could not run",
                "reels": [], "stages": {}, "yield": None}

    triage, t_ok = ({}, False)
    if RT is not None:
        try:
            triage, t_ok = RT.load()
        except Exception:
            triage, t_ok = {}, False

    rows = []
    for rec in list(plan.get("candidates") or []) + list(plan.get("kept") or []):
        reel = rec.get("reel")
        tag = rec.get("tag")
        stage, idx = _stage_of(tag)
        p, f, ratio = _yield_of(triage if t_ok else None, reel)
        rows.append({
            "reel": reel,
            "mb": rec.get("mb"),
            "pages": rec.get("pages"),
            "tag": tag,
            "why": rec.get("why"),
            # `stage` None + `stageKnown` False is the honest shape for a tag we were never
            # taught. The UI must draw that as a question mark, not as stage 0.
            "stage": stage,
            "stageIdx": idx,
            "stageKnown": stage is not None,
            "held": tag != "eligible",
            "holdKind": ("policy" if tag in POLICY_HOLDS else
                         "global" if tag in GLOBAL_HOLDS else
                         None if tag == "eligible" else "evidence"),
            "panels": p, "frames": f,
            # ratio None = NOBODY SURVEYED IT. Not zero.
            "yield": None if ratio is None else round(ratio, 4),
        })

    stages = {}
    for s in STAGES:
        stages[s] = sum(1 for r in rows if r["stage"] == s)
    stages["unknown-stage"] = sum(1 for r in rows if not r["stageKnown"])

    # The aggregate he asked to see. Computed only over reels that were ACTUALLY SURVEYED, and
    # the count of un-surveyed reels travels beside it so the percentage cannot be read as
    # covering the whole shelf. [[unknown-stays-unknown]]
    tp = sum(r["panels"] or 0 for r in rows if r["yield"] is not None)
    tf = sum(r["frames"] or 0 for r in rows if r["yield"] is not None)
    unmeasured = sum(1 for r in rows if r["yield"] is None)
    yld = None if tf <= 0 else {
        "panels": tp, "frames": tf,
        "usefulPct": round(100.0 * tp / tf, 1),
        "emptyPct": round(100.0 * (tf - tp) / tf, 1),
        "reelsMeasured": len(rows) - unmeasured,
        "reelsUnmeasured": unmeasured,
        # ⚠ SAY WHOSE STORE THIS IS. A yield computed off a triage store that would not parse is
        # not a yield; t_ok False means the number below is over whatever subset happened to load.
        "storeOk": bool(t_ok),
    }

    return {
        "ok": True,
        "hist": plan.get("hist"),
        "onDisk": plan.get("onDisk"),
        "reels": sorted(rows, key=lambda r: (r["stageIdx"], -(r["mb"] or 0))),
        "stages": stages,
        "yield": yld,
        "unreadable": plan.get("unreadable") or [],
        # v3225 — the plan's figure is MB THIS PLAN WOULD FREE, never free disk.
        "eligibleMb": plan.get("eligibleMb", plan.get("freeMb")),
    }


def _fmt(v, suffix=""):
    return "—" if v is None else ("%s%s" % (v, suffix))


def main(argv=None):
    import sys
    # This CLI prints ⚠ and ⚙; on a non-UTF-8 console that is a UnicodeEncodeError instead of a
    # report. console_safe is the repo's existing answer and it never raises.
    try:
        import console_safe
        console_safe.enable()
    except Exception:
        pass
    st = story()
    if not st["ok"]:
        print("cannot tell the story: %s" % st["why"])
        return 1
    print("\nTHE SHELF — %d reels in %s" % (st["onDisk"], st["hist"]))
    y = st["yield"]
    if y is None:
        print("  yield: UNKNOWN — no reel on this shelf has been surveyed")
    else:
        print("  yield: %.1f%% of film carried a panel, %.1f%% carried nothing"
              % (y["usefulPct"], y["emptyPct"]))
        print("         (%d panels / %d frames, over %d surveyed reels; %d reel(s) never surveyed%s)"
              % (y["panels"], y["frames"], y["reelsMeasured"], y["reelsUnmeasured"],
                 "" if y["storeOk"] else "; ⚠ THE TRIAGE STORE WOULD NOT PARSE"))
    print("\n  where they stand:")
    for s in STAGES:
        n = st["stages"].get(s) or 0
        if n:
            print("     %-12s %3d" % (s, n))
    if st["stages"].get("unknown-stage"):
        print("     %-12s %3d  ⚠ a verdict this board was never taught — teach TAG_STAGE"
              % ("unknown", st["stages"]["unknown-stage"]))
    if st["unreadable"]:
        print("\n  ⚠ will not parse: %s" % ", ".join(st["unreadable"]))
    print()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
