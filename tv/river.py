"""THE RIVER — stream one fish through every joint and report which ones actually carry.

Konyo, 2026-09-01: *"i want you streaming little tiny fish down streams and see that they are
connected and running properly — my analogy is for reels going through. monitor and reverse
engineer it, see how its connected and synced, and make sure these are unified where they need
to be and individually coded as PARTS like we mentioned already for a reason. just design it
correctly."*

WHAT IT IS. The pipeline is a river: material enters at CAPTURE and flows through SURVEY, READ,
GATE, SEAL and PRUNE. Between each pair of stages is a JOINT — a place one stage hands something
to the next. This module walks every joint and asks one question: **is anything actually
crossing it?**

WHY IT EXISTS, and it is the same failure four times in one day. A joint can be wired at both
ends, tested, and carry nothing — and a joint carrying nothing looks EXACTLY like a joint with
nothing to carry. Every instance found so far:

    surface     the reader knows which tab a frame showed; the sighting does not record it
                -> 8,300 sightings, 0 surfaces, and v2380's cross-surface witness can never fire
    slot        `slot_identity.slot_tags()` earns `same-slot` corroboration and had NO caller
                outside its own tests; joined at v2393 and STILL dry, because real sightings
                carry no point/panelBox/container either
    per-frame   `gate()` returns a tab name per frame; the store was handed `{"panel": N}`
                -> the prune is stuck at REEL granularity, 3.2 GB held for 104 frames
    vault lane  ran every 45s since it was built and swept nothing; `owed: 0` read as healthy

Each was found BY HAND, after he asked. He asked the right question — *"how do we find these
before i tell you about them?"* — and this file is the answer.

THE FOUR VERDICTS, and the third is the entire point:

    CARRIES   material crossed. n > 0.
    STARVED   nothing crossed AND nothing was upstream. Correct silence — not a defect.
    DRY       nothing crossed WHILE MATERIAL WAS WAITING UPSTREAM. **This is a defect.**
    UNKNOWN   the joint could not be measured. Never reported as either of the above.

⚠ DRY vs STARVED IS THE WHOLE INSTRUMENT. Collapsing them is what let every defect above hide:
a lane with nothing to do and a lane that cannot do anything publish identical numbers.
[[unknown-stays-unknown]] [[the-unjoined-end]] [[heart-first]]

⚠ IT READS AND DECIDES NOTHING. No deletion, no seal, no write of any kind. It is an instrument,
and an instrument that can change what it measures is not one. The apply stays his.
"""

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# ⚠ THIS FILE PRINTS ⚠ AND ARROWS. Without this, a non-UTF-8 console makes it crash while
# REPORTING — so a perfectly healthy tree exits non-zero for a reason that has nothing to do with
# the river. Caught by TestToolsCanReportTheirVerdict before it shipped.
try:
    from console_safe import enable as _console_safe_enable
    _console_safe_enable()
except Exception:
    pass

CARRIES, STARVED, DRY, UNKNOWN = "CARRIES", "STARVED", "DRY", "UNKNOWN"
#: ⚠⚠ v3267 — THE FIFTH STATE. DRY means "work was waiting and none crossed", which reads as a
#: BROKEN JOIN — and it was the wrong word for the `slot` joint, where the thing that would
#: produce the input has never been switched on. Measured 2026-09-17: of 14,322 sightings, ZERO
#: carry point/panelBox/container, and the only producer of cell coordinates anywhere in the tree
#: is MINI/AUTOMATIC hover mode, whose own file says the live run "is a separate thing he has
#: asked for explicitly and has not authorised yet". The panel told him a reader was dropping
#: data it held; the truth was that nothing has ever produced that data. Different fault,
#: different remedy — and the remedy for this one is his to authorise, not mine to code.
#: ⚠ UNBUILT is never INFERRED. A joint must pass `unbuilt_why` explicitly, so it can never
#: become the quiet place a genuinely broken join goes to hide. [[label-outlived-referent]]
UNBUILT = "UNBUILT"

# order matters — it is the river
STAGES = ("capture", "survey", "frame-verdict", "read", "sighting",
          "surface", "slot", "gate", "seal", "prune", "disk")


def _ring(pattern):
    """Every file in a rotating journal's ring, oldest first.

    ⚠ THE LIVE FILE IS NOT THE RECORD. `sessions.jsonl` is 2.3 MB while the rotated
    `sessions.1.jsonl` beside it is 4.0 MB — reading only the live file loses more than half the
    history and has already caused one CORRECT measurement to be retracted.
    [[journal-ring-not-the-live-file]]
    """
    import glob
    return sorted(glob.glob(os.path.join(HERE, pattern)))


def _hist_dir():
    """Where the footage actually is. -> path or None

    ⚠ RESOLVED THE SAME WAY THE CONSOLE DOES, and the first cut of this did not. It guessed
    `~/Library/Application Support/TV DIABLO/history`, found nothing, and reported capture,
    prune and disk as UNKNOWN — which reads as "the pipeline could not be measured" when the real
    answer was "the instrument looked in the wrong place". A probe that fails on its own REACH
    and reports it as a fact about the system is worse than no probe.
    `control_app.py:113` is the authority: TV_HIST, else <tv>/frames/hist.
    [[source-reading-guard]] [[feedback-suspect-the-instrument]]
    """
    c = os.environ.get("TV_HIST")
    if c and os.path.isdir(c):
        return c
    d = os.path.join(HERE, "frames", "hist")
    return d if os.path.isdir(d) else None


def _joint(name, what, n, upstream, why="", unit="item", unbuilt_why=None):
    """Grade one joint. -> dict

    `n` is what CROSSED. `upstream` is what was WAITING. Either may be None for UNKNOWN, and None
    is never silently turned into 0 — that substitution is the defect this module exists to find.
    """
    if n is None or upstream is None:
        state = UNKNOWN
    elif n > 0:
        state = CARRIES
    elif upstream > 0:
        # ⚠ a joint that KNOWS its producer does not exist yet says so, rather than reading as a
        # broken join. Explicit only — see the UNBUILT note at the top of this file.
        state = UNBUILT if unbuilt_why else DRY
        if unbuilt_why:
            why = unbuilt_why
    else:
        state = STARVED
    return {"joint": name, "what": what, "crossed": n, "upstream": upstream,
            "state": state, "why": why, "unit": unit}


# ══ THE JOINTS ══════════════════════════════════════════════════════════════════════════════
# Each returns a dict from _joint(). Each is INDEPENDENTLY coded — his standing instruction is
# that the parts stay parts ("anything with exceptions are already coded properly by design
# individually in parts... i want it connecting and synced"). What is unified is the QUESTION
# they answer and the vocabulary they answer it in, never their internals.

def j_capture():
    """disk -> reels. Is footage arriving at all?"""
    h = _hist_dir()
    # ⚠ #123 — the two early returns used to skip the door split entirely, so on a machine with no
    # history (every CI runner) the capture joint carried NO `doorsSay` key and a reader could not
    # tell "nobody split the doors" from "the split field was dropped". The split is UNKNOWN there,
    # and says why; the joint's own grade is untouched. [[unknown-stays-unknown]]
    if not h:
        j = _joint("capture", "reels on disk", None, None,
                   "no history directory found — TV_HIST unset and the default is absent", "reel")
        j["doors"], j["doorsSay"] = None, ("which door opened each reel is UNKNOWN — there is no "
                                           "history directory to split")
        return j
    try:
        reels = [d for d in os.listdir(h) if os.path.isdir(os.path.join(h, d))]
    except OSError as e:
        j = _joint("capture", "reels on disk", None, None, str(e)[:70], "reel")
        j["doors"], j["doorsSay"] = None, ("which door opened each reel is UNKNOWN — the history "
                                           "directory could not be listed (%s)" % type(e).__name__)
        return j
    # upstream for capture is the game itself, which we cannot measure — so a zero here is
    # UNKNOWN-shaped, not STARVED. Report the count and say the upstream is unmeasurable.
    j = _joint("capture", "reels on disk", len(reels), len(reels) or None,
               "the upstream of capture is him playing, which this cannot measure", "reel")
    # ⚠⚠ v3312 (#65) — WHICH DOOR EACH REEL CAME BY. Konyo: "the shadow reels that get shadow
    # recorder they too need to be within the river and seen visually just like the others".
    # MEASURED: they were ALREADY in the river — shadow reaches its reel through start_agent, so
    # a shadow reel is an ordinary reel and nothing here ever filtered them out. What the river
    # could not do is SAY which ones they are: this module mentioned `door` zero times, so shadow
    # flowed every joint INVISIBLY and "shadow contributed N" had no answer. A count nobody can
    # attribute is the shape that hid an entire evening of play producing ZERO shadow reels.
    # ⚠ NEVER FATAL. The split is decoration on a joint that already graded itself; if the
    # journal cannot be read the joint keeps its verdict and the doors line says UNKNOWN.
    try:
        import reel_door as _rd
        _dmap, _dwhy = _rd.door_map()
        j["doors"] = _rd.split(reels, _dmap)
        j["doorsSay"] = _rd.say(j["doors"]) if _dmap else (
            "which door opened each reel is UNKNOWN — %s" % _dwhy)
    except Exception as _e:
        j["doors"] = None
        j["doorsSay"] = "the door split could not be read (%s)" % type(_e).__name__
    return j


def j_survey():
    """reels -> surveyed. Has the free structural filter looked at them?"""
    try:
        import retro_triage as RT
        blob, ok = RT.load(None)
        if not ok:
            return _joint("survey", "reels surveyed", None, None, "survey store unreadable", "reel")
        full = sum(1 for v in (blob or {}).values() if v.get("full"))
    except Exception as e:
        return _joint("survey", "reels surveyed", None, None, str(e)[:70], "reel")
    cap = j_capture()
    return _joint("survey", "reels surveyed", full, cap.get("crossed"),
                  "a reel nobody surveyed is UNKNOWN, never empty", "reel")


def j_frame_verdict():
    """surveyed -> per-frame verdict. Can the prune act on ONE frame, or only a whole reel?"""
    try:
        import retro_triage as RT
        blob, ok = RT.load(None)
        if not ok:
            return _joint("frame-verdict", "reels with a per-frame verdict", None, None,
                          "survey store unreadable", "reel")
        withpf = sum(1 for v in (blob or {}).values() if v.get("panelFrames") is not None)
        full = sum(1 for v in (blob or {}).values() if v.get("full"))
    except Exception as e:
        return _joint("frame-verdict", "reels with a per-frame verdict", None, None, str(e)[:70], "reel")
    return _joint("frame-verdict", "reels with a per-frame verdict", withpf, full,
                  "without this the prune is stuck at REEL granularity — v2393 writes it, but "
                  "only for reels surveyed SINCE v2393; older rows are UNKNOWN, not empty", "reel")


def j_read():
    """surveyed -> read. Has a paid reader actually looked at what carries something?"""
    try:
        import retro_triage as RT
        blob, ok = RT.load(None)
        if not ok:
            return _joint("read", "reels sealed", None, None, "survey store unreadable", "reel")
        worth = sum(1 for v in (blob or {}).values() if v.get("full") and v.get("panels"))
    except Exception as e:
        return _joint("read", "reels sealed", None, None, str(e)[:70], "reel")
    sealed = with_pages = None
    try:
        p = os.path.join(HERE, "chronicle_swept.json")
        if os.path.isfile(p):
            d = json.load(io.open(p, encoding="utf-8"))
            sealed = len(d) if isinstance(d, (dict, list)) else None
            if sealed is not None:
                rows = list(d.values()) if isinstance(d, dict) else d
                # REG-3756 - a seal that says its read found NO Chronicle page (pages == 0) owes no sighting; a seal that
                # does not say (an older row, a non-number) still counts as owing one - never assumed empty
                with_pages = sum(1 for v in rows if not (isinstance(v, dict) and isinstance(v.get("pages"), int)
                                                         and not isinstance(v.get("pages"), bool) and v.get("pages") == 0))
    except Exception:
        sealed = with_pages = None
    j = _joint("read", "reels sealed", sealed, worth,
               "a reel the survey says CARRIES something and nobody read is the backlog", "reel")
    j["sealedWithPages"] = with_pages
    return j


def _sightings():
    """Every sighting in the evidence store, flattened. -> list (possibly empty) or None."""
    p = os.path.join(HERE, "chron_evidence.json")
    if not os.path.isfile(p):
        return None
    try:
        ev = json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None
    out = []
    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                if isinstance(v, dict) and ("reel" in v or "frame" in v):
                    out.append(v)
                else:
                    walk(v)
    walk(ev)
    return out


def j_sighting():
    """read -> sighting. Did the reads leave evidence behind?"""
    ss = _sightings()
    if ss is None:
        return _joint("sighting", "sightings recorded", None, None,
                      "chron_evidence.json absent or unreadable", "sighting")
    r = j_read()
    # REG-3756 (Dean's river, 11-11: "blocked at 'sighting'", 0 sightings against 7 sealed reels) - the joint waited on EVERY
    # sealed reel, and a seal whose read found no Chronicle page (pages: 0) legitimately leaves no sighting behind, so a PC
    # whose reels held no Chronicle page read DRY - a broken join - when nothing was owed. It waits only on seals that found
    # a page (or do not say); none read as UNKNOWN.
    up = r.get("sealedWithPages")
    return _joint("sighting", "sightings recorded", len(ss), up,
                  ("" if up is None else "%d of %d sealed reel(s) found a Chronicle page - a sealed read that found none "
                   "owes no sighting" % (up, r.get("crossed") or 0)), "sighting")


def j_surface():
    """sighting -> surface. Does a sighting say WHERE on screen it was seen?

    v2380 built a `cross-surface` witness: the same item on the floor, in the inventory and in
    the Chronicle list is three independent looks. It can only fire if sightings carry a surface.
    """
    ss = _sightings()
    if ss is None:
        return _joint("surface", "sightings carrying a surface", None, None,
                      "chron_evidence.json absent or unreadable", "sighting")
    # ⚠⚠ v2772 — IT ASKED FOR A KEY THE WRITER NEVER WRITES, AND THE SENTENCE UNDER IT WAS FALSE.
    # Found by an independent recon pass. `chronicle_retro.py:1349` DOES persist the surface on
    # every new sighting — as `"scene"`, named that way on purpose (:1337 "NAMED `scene`, NOT
    # `surface`, DELIBERATELY", because `surface` was already two other, narrower vocabularies).
    # This joint counted `surface`, so it read 0 for ever and the console kept printing "the reader
    # knows which tab the frame showed and DOES NOT PERSIST IT" long after that stopped being true.
    # Two vocabularies meeting silently, which `reel_segments.py:105` is quoted about beside the
    # writer itself: "two vocabularies meeting SILENTLY is how a branch stops being reachable
    # without anyone noticing." [[the-unjoined-end]] [[label-outlived-referent]]
    #
    # ⚠ AND WIDENING THE GREP TO `surface or scene` WOULD BE THE FIX THAT TURNS A REAL GAP GREEN.
    # It reports BOTH, separately, with the denominator — because the count is still 0 and the
    # REASON changed completely: the backlog PREDATES the writer, and `chronicle_autoreel_tick`
    # reports 0 reels owing a read (a reel re-owes only when it GROWS or when PROMPT_VER changes,
    # and it has not). So this joint cannot heal by waiting, and saying "not persisted" would send
    # someone to fix a writer that is already correct. [[zero-needs-a-denominator]]
    n_scene = sum(1 for s in ss if str(s.get("scene") or "").strip())
    n_surf = sum(1 for s in ss if str(s.get("surface") or "").strip())
    n = n_scene + n_surf
    if n:
        return _joint("surface", "sightings carrying a surface", n, len(ss),
                      "%d carry `scene` (the key chronicle_retro writes) and %d carry the older "
                      "`surface`" % (n_scene, n_surf), "sighting")
    return _joint("surface", "sightings carrying a surface", 0, len(ss),
                  "0 of %d carry EITHER key. ⚠ NOT because the reader drops it — chronicle_retro "
                  "persists it as `scene` — but because every stored sighting PREDATES that "
                  "writer, and no chronicle read is scheduled to make more (0 reels owe a read; a "
                  "reel re-owes only when it grows or when PROMPT_VER changes). The backlog cannot "
                  "be retrofitted without paying to re-read, so this cannot heal by waiting"
                  % len(ss), "sighting")


def j_slot():
    """sighting -> slot. Does a sighting carry the material to name its CELL?

    `slot_identity.slot_tags()` earns `same-slot`: two reads agreeing on the cell agree about a
    second, independent fact, which a shared misread of the TEXT cannot fake. Joined into
    `witnesses()` at v2393.

    ⚠ A SLOT IS A WITNESS, NEVER A NAME. A stash grid carries no item names — v1861 design,
    re-confirmed on his 31 reels. The cell corroborates a name something else proposed.
    """
    ss = _sightings()
    if ss is None:
        return _joint("slot", "sightings with a derivable slot", None, None,
                      "chron_evidence.json absent or unreadable", "sighting")
    try:
        import slot_identity as SI
        n = sum(1 for s in ss if SI.slot_of_sighting(s))
    except Exception as e:
        return _joint("slot", "sightings with a derivable slot", None, None, str(e)[:70], "sighting")
    # ⚠⚠ v3267 — THE OLD SENTENCE BLAMED A READER THAT HAS NOTHING TO WRITE. It said "the reader
    # has all three at the moment it reads and records none of them", which describes a dropped
    # field, so it sends whoever reads it into `chronicle_retro` to add three keys. MEASURED:
    # every `point` in that file is the English word, the sighting it mints carries
    # reel/frame/witness/conf/lane/foundAt/droppedBy/sort, and the ONLY code in the tree that ever
    # produces `panelBox` is `hover_wilson.py` — a Wilson probe over synthetic rectangles, whose
    # own docstring says the live hover "is a separate thing he has asked for explicitly and has
    # not authorised yet". So this joint is waiting on a MODE, not on a missing assignment.
    #
    # ⚠ AND IT IS MEASURED, NOT ASSUMED. If even one sighting carries geometry, the producer HAS
    # run and a zero here is a real derivation failure — which must keep reading DRY. Hard-coding
    # UNBUILT would turn this joint off the day the autopilot is switched on and starts writing
    # coordinates that do not derive. [[unknown-stays-unknown]] [[strictness-that-closes-the-lane]]
    _geo = sum(1 for x in ss
               if isinstance(x, dict) and (x.get("point") or x.get("panelBox")
                                           or x.get("container") or x.get("slot")))
    _unbuilt = None
    if not _geo:
        _unbuilt = ("no sighting has ever carried a cell coordinate (0 of %d), because the only "
                    "thing that produces one is MINI/AUTOMATIC hover mode and it has never been "
                    "authorised to run on his screen. This joint is waiting on that decision, "
                    "not on a broken join — nothing in the read path is dropping data it holds."
                    % len(ss))
    return _joint("slot", "sightings with a derivable slot", n, len(ss),
                  "%d of %d sighting(s) carry geometry and none derived a cell — the derivation "
                  "is failing, not the producer" % (_geo, len(ss)), "sighting",
                  unbuilt_why=_unbuilt)


def j_gate():
    """sighting -> grounded. Did evidence become a name he can act on?"""
    ss = _sightings()
    up = len(ss) if ss is not None else None
    p = os.path.join(HERE, "chron_last_result.json")
    if not os.path.isfile(p):
        return _joint("gate", "names grounded", None, up, "no last-result store", "name")
    try:
        d = json.load(io.open(p, encoding="utf-8"))
    except Exception as e:
        return _joint("gate", "names grounded", None, up, str(e)[:70], "name")
    # ⚠⚠ v2761 — THIS JOINT ASKED FOR THREE KEYS THE STORE HAS NEVER WRITTEN, and reported the
    # miss as a hard 0. MEASURED on his live chron_last_result.json — the result carries
    # ['calibration','contested','contestedExpired','denial','fold','held','hunt','lanes',
    #  'newlyDated','notFoundDatable','reels','refused','refusedEver','resolverOk','setGroups',
    #  'totals','verdict','wouldAdd'] — and NOT grounded, applied or accepted. So the river's own
    # diagnosis said "gate DRY, 0 names grounded of 14,034" for a joint that was never measured.
    # A zero with no denominator, living inside the instrument that diagnoses the river.
    # [[zero-needs-a-denominator]] [[feedback-suspect-the-instrument]]
    #
    # ⚠ AND THE TRUE STATE IS NOT "BLOCKED". `newlyDated` is what a sweep writes when a name
    # actually grounds. His last sweep: wouldAdd 271 uniques + 83 sets = 354 proposed, and
    # /api/chronicle_crossref answers "354 of the 354 read are already in your chronicle; 0 are
    # new". So NOTHING NEW TO GROUND is the honest reading — a legitimate state that this joint
    # could not tell apart from a blockage, because both rendered as 0.
    #
    # THREE STATES, NOT TWO:
    #   nothing was proposed          -> UNKNOWN, there is no question to answer yet
    #   proposed, and some grounded   -> CARRIES
    #   proposed, and NONE grounded   -> DRY, and that is a real blockage worth his attention
    # ⚠⚠ AND THE ORIGINAL MISS WAS TWO DEFECTS, NOT ONE. Reading the right keys exposed the
    # second immediately: the sweep store is {"proposal", "result", "savedTs"} and EVERY figure
    # lives under `result`. So the old code asked the TOP level for grounded/applied/accepted and
    # would have missed them even if they had been the right names. Two wrong things pointing the
    # same way is why this read as a confident 0 for so long.
    d = (d.get("result") if isinstance(d.get("result"), dict) else d)
    wa = d.get("wouldAdd")
    proposed = 0
    if isinstance(wa, dict):
        for v in wa.values():
            proposed += (len(v) if isinstance(v, (list, dict)) else int(v or 0))
    elif isinstance(wa, (list, dict)):
        proposed = len(wa)
    nd = d.get("newlyDated")
    grounded = len(nd) if isinstance(nd, (list, dict)) else None
    held = d.get("held")
    n_held = len(held) if isinstance(held, (list, dict)) else 0
    if grounded is None:
        return _joint("gate", "names grounded", None, up,
                      "this sweep result carries no `newlyDated`, so nothing here can say whether "
                      "a name grounded — absent is not zero", "name")
    if not proposed:
        return _joint("gate", "names grounded", None, up,
                      "no name was proposed by the last sweep (%d held), so there was nothing to "
                      "ground — that is an empty question, not a dry joint" % n_held, "name")
    # ⚠⚠ A VERDICT THAT CONTRADICTS ITS OWN REASON IS THE DEFECT, NOT THE PROSE. Found by a
    # SECOND EYE (grok-4-1-fast-reasoning, reviewing this diff cold): the first cut returned
    # crossed=0 — which grades DRY — while its own `why` said "this may be 'nothing NEW to
    # ground' and not a blockage". The instrument asserted a blockage and then argued against
    # itself in the sentence underneath. That is exactly the shape this repo keeps removing from
    # other people's code.
    #
    # ⚠ AND IT GENUINELY CANNOT TELL THE TWO APART. "0 grounded of 354 proposed" is a blockage
    # ONLY if some of those 354 were new. `chronicle_crossref` is what knows — and it has no cache
    # file, it is computed live against the board window, so this joint cannot ask it without
    # dragging the console in. An instrument that cannot distinguish two states MUST NOT PICK ONE.
    # UNKNOWN, with both possibilities named and the thing that would settle it.
    # [[unknown-stays-unknown]] [[feedback-contradiction-is-the-finding]]
    if not grounded:
        return _joint("gate", "names grounded", None, proposed,
                      "%d name(s) were proposed and none grounded (%d held). This joint cannot "
                      "tell a real blockage from 'he already has all of them' — chronicle_crossref "
                      "knows, and is computed live rather than cached. Ask it: newCount > 0 with "
                      "nothing grounded is a blockage; newCount == 0 means there was nothing new "
                      "to ground." % (proposed, n_held), "name")
    return _joint("gate", "names grounded", grounded, proposed, "", "name")


def j_seal():
    """grounded -> sealed. Is the reel's verdict durable?"""
    p = os.path.join(HERE, "chronicle_swept.json")
    if not os.path.isfile(p):
        return _joint("seal", "seals written", None, None, "no seal store", "seal")
    try:
        d = json.load(io.open(p, encoding="utf-8"))
        n = len(d) if isinstance(d, (dict, list)) else None
    except Exception as e:
        return _joint("seal", "seals written", None, None, str(e)[:70], "seal")
    return _joint("seal", "seals written", n, j_read().get("upstream"), "", "seal")


def j_prune():
    """sealed -> releasable. Would the planner let anything go?"""
    h = _hist_dir()
    if not h:
        return _joint("prune", "reels the planner would release", None, None,
                      "no history directory", "reel")
    try:
        import reel_retention as RR
        plan = RR.plan(h)
        # ⚠⚠ v3267 — THIS ASKED FOR TWO KEYS THE PLANNER HAS NEVER PUBLISHED. `reel_retention.plan()`
        # returns candidates/kept/coverage/eligibleMb/onDisk/say — there is no `delete` and no
        # `remove`, so `gone` was `len([])` on every run this joint has ever made, and the river
        # reported "a planner that releases nothing while the disk is full is the blockage" while
        # the planner's own `say` read "1 reel(s) may go, freeing 17 MB". A permanent false
        # blockage, produced by a caller and a callee disagreeing about a key name.
        # ⚠ the old names stay in the chain: if a future planner does publish them this still
        # reads them, and an empty `candidates` beside a populated `delete` must not read as 0.
        gone = len(plan.get("candidates") or plan.get("delete") or plan.get("remove") or [])
        kept = len(plan.get("kept") or [])
        # v3295 - THIS NAMED A CAUSE IT NEVER MEASURED. The why hard-coded "while the disk is
        # full"; j_disk measured 22.0 GB FREE in the same run. An instrument that asserts an
        # unmeasured cause is worse than one saying UNKNOWN, because the reader acts on it - the
        # task tracking this joint carried "while the disk is full" in its TITLE for days.
        # The planner already publishes its own reason in `say`; quote that, never invent one.
        say = str(plan.get("say") or "").strip()
    except Exception as e:
        return _joint("prune", "reels the planner would release", None, None, str(e)[:70], "reel")
    return _joint("prune", "reels the planner would release", gone, gone + kept,
                  (("the planner's own reading: %s" % say) if say
                   else "the planner released nothing and gave no reason; the cause is NOT "
                        "measured at this joint"), "reel")


def j_disk():
    """releasable -> freed. Did the disk actually change?"""
    h = _hist_dir()
    if not h:
        return _joint("disk", "GB free", None, None, "no history directory", "GB")
    try:
        # #229 — shutil.disk_usage, not os.statvfs: statvfs does not exist on Windows, so this read UNKNOWN on every Windows console. disk_usage.free is f_bavail * f_frsize on POSIX.
        import shutil as _sh
        import disk_room as _dr   # #151 (REG-2742) - purgeable space counts, as on every other floor
        free_gb = _dr.free_bytes(h)[0] / (1024.0 ** 3)
    except Exception as e:
        return _joint("disk", "GB free", None, None, str(e)[:70], "GB")
    pr = j_prune()
    return _joint("disk", "GB free", round(free_gb, 1), pr.get("crossed"),
                  "capture refuses below its floor, so this joint gates the whole river", "GB")


JOINTS = (j_capture, j_survey, j_frame_verdict, j_read, j_sighting,
          j_surface, j_slot, j_gate, j_seal, j_prune, j_disk)


def trace():
    """Walk every joint. -> list of joint dicts, in river order."""
    out = []
    for f in JOINTS:
        try:
            out.append(f())
        except Exception as e:
            out.append(_joint(f.__name__[2:], "(the probe itself failed)", None, None,
                              "%s: %s" % (type(e).__name__, str(e)[:60])))
    return out


def summary(rows=None):
    """One line per state, plus the first DRY joint — which is where the river is blocked."""
    rows = rows if rows is not None else trace()
    by = {}
    for r in rows:
        by.setdefault(r["state"], []).append(r["joint"])
    first_dry = next((r for r in rows if r["state"] == DRY), None)
    # ⚠ v3267 — an UNBUILT joint is NOT a blockage he can fix by repairing something, so it must
    # not claim the headline. It must also not vanish: "no joint is dry" over a joint that has
    # never been able to carry is the same over-claim this module exists to stop.
    unbuilt = by.get(UNBUILT, [])
    first_ub = next((r for r in rows if r["state"] == UNBUILT), None)
    if first_dry:
        say = "the river is blocked at %r — %s" % (first_dry["joint"], first_dry["why"])
    elif first_ub:
        say = ("no joint is dry; %d joint(s) have never been built or switched on (%s) — %s"
               % (len(unbuilt), ", ".join(unbuilt), first_ub["why"]))
    else:
        say = "no joint is dry"
    return {
        "counts": {k: len(v) for k, v in sorted(by.items())},
        "dry": by.get(DRY, []),
        "unbuilt": unbuilt,
        "unknown": by.get(UNKNOWN, []),
        "firstBlockage": (first_dry or {}).get("joint"),
        "awaiting": (first_ub or {}).get("joint"),
        "say": say,
    }


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    rows = trace()
    if "--json" in argv:
        print(json.dumps({"joints": rows, "summary": summary(rows)}, indent=2))
        return 0
    print("THE RIVER — one fish, every joint\n")
    print("  %-14s %-34s %10s %10s  %s" % ("joint", "what crosses", "crossed", "upstream", "state"))
    print("  " + "-" * 92)
    for r in rows:
        c = "?" if r["crossed"] is None else str(r["crossed"])
        u = "?" if r["upstream"] is None else str(r["upstream"])
        print("  %-14s %-34s %10s %10s  %s" % (r["joint"], r["what"][:34], c, u, r["state"]))
    s = summary(rows)
    print("\n  " + json.dumps(s["counts"]))
    print("  " + s["say"])
    # v3312 — the capture joint CARRIES, and a CARRIES joint never prints its `why` (see the loop
    # below). So the door split gets its own line, always, rather than hiding behind a state it
    # will never reach. ⚠ UNKNOWN is printed too: "nobody could attribute these" is a reading.
    for r in rows:
        if r.get("joint") == "capture" and r.get("doorsSay"):
            print("  doors: " + r["doorsSay"])
    for r in rows:
        if r["state"] in (DRY, UNBUILT, UNKNOWN) and r["why"]:
            print("\n  %-8s %-14s %s" % (r["state"], r["joint"], r["why"]))
    # ⚠ EXIT 0 ALWAYS. This is an instrument, not a gate. A DRY joint is a finding to act on,
    # and turning it into a build failure is how a real signal becomes furniture.
    return 0


if __name__ == "__main__":
    sys.exit(main())
