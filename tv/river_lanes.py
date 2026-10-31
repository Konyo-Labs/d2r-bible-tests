# -*- coding: utf-8 -*-
"""THE RIVER AS FOUR LANES — the shape he asked to SEE, over the nine stations that actually exist.

Konyo: *"the visual rendering of it i want it replicating a simple · INTAKE where the reels come
and get stationed · PRINTER where they get filtered · CAPTURE where they get extracted.. and
finally TOMBSTONE. now obivously the logic behind the backed is not sycned and is not 1000% doing
this.. but the stamps and everything and the movement of them going down that architure and
structure i want built. first in first out FIFO.. that way its optimzed."*

And, decisively: *"now dont get me wrong. the backend should be pinpoint perfect and nothing
fabricated what so ever.. just the visual rendering of the backend and the entire process of the
reel coming in extracted and then out i want that visually built."*

=== ⚠⚠ SO THIS IS A VIEW, NOT A SECOND PIPELINE ===
Nothing here decides where a reel is. `reel_router.route()` decides, and this GROUPS its answer.
The moment this file starts computing a station of its own, the console shows a river the backend
does not have — which is the one thing he ruled out.

=== ⚠⚠ THE LANE MAP IS A PARTITION, AND THAT IS ENFORCED ===
Every station in `reel_router.STATIONS` belongs to EXACTLY ONE lane. Not zero, not two.
`assert_partitions()` proves it against the router's own tuple rather than against a copy, so a
tenth station added upstream turns this RED instead of quietly vanishing from his screen — the
`reel_story` failure this family already lived through, where four of six stages were permanently
empty and nothing said so.

MEASURED on his shelf the day this was written (40 reels):

    INTAKE       7   INTAKE:0 + TRIAGE:0 + STATION:7 + EMPTY:0
    PRINTER     11   PRINTER:11
    CAPTURE     16   CAPTURE:12 + JOIN:4
    TOMBSTONE    6   ROUTED:6 + TOMBSTONE:0
    TOTAL       40   = shelf, reconciles True

⚠ TOMBSTONE READS 6 AND NOT 0 ONLY BECAUSE v2764 UNWELDED ROUTED FROM THE DELETER. Before that,
the last lane could never hold anything: the only writer of a tombstone row lived inside the
deleter, behind the arming lock. The lane would have been a permanently empty box with a label.

=== FIFO IS INHERITED, NEVER RE-SORTED ===
`reel_router.route()` already orders oldest-capture-first and puts reels with NO readable clock
LAST (None must not become 0, which is 1970 and would put every unmeasured reel at the head). A
second sort here would be a second copy of that rule, free to drift. [[copy-drift]]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

#: The four lanes he named, in river order, each over the REAL stations it covers.
#: ⚠ THE STATION NAMES ARE THE ROUTER'S. `assert_partitions()` holds this to `reel_router.STATIONS`.
LANES = (
    ("INTAKE", ("INTAKE", "TRIAGE", "STATION", "EMPTY"),
     "the reels arrive and get stationed — surveyed, or waiting to be"),
    ("PRINTER", ("PRINTER",),
     "names have been read off the frames and the session carries no seal yet"),
    ("CAPTURE", ("CAPTURE", "JOIN"),
     "the names are extracted and joined to a seal"),
    ("TOMBSTONE", ("ROUTED", "TOMBSTONE"),
     "closed out — the extraction contract is satisfied; release is a separate, locked act"),
)


#: How many CLOSED reels a lane hands to the page. The count is always the whole ledger; this caps
#: only the rows drawn. His ledger holds 428 and #15 is the standing precedent for what happens
#: when a surface hands the DOM everything it has.
SHOW_CLOSED = 24


def assert_partitions():
    """Every router station belongs to exactly one lane. -> (ok, findings)

    ⚠⚠ THE FAILURE THIS CATCHES IS SILENT BY NATURE. A station added upstream and not mapped here
    simply stops appearing on his shelf: the lanes still add up among themselves, the page still
    renders, and reels quietly leave the picture. That is `reel_story`'s exact defect — four of six
    stages permanently empty with nothing saying so — and it is why this compares against the
    ROUTER'S tuple instead of a list kept here. [[the-unjoined-end]]
    """
    findings = []
    try:
        import reel_router as _rr
    except Exception as exc:
        return False, ["reel_router could not be imported (%s) — a REFUSAL, never a pass"
                       % type(exc).__name__]
    declared = tuple(getattr(_rr, "STATIONS", ()) or ())
    if not declared:
        return False, ["reel_router.STATIONS is empty, so this guard inspected nothing — an "
                       "instrument failure, not a clean result"]
    # ⚠⚠ THESE FOUR CHECKS WERE MISSING AND THE GUARD STILL CALLED ITSELF A PARTITION PROOF.
    # Raised by the second eye: a station repeated INSIDE ONE lane's tuple leaves len(seen[st])
    # at 1, so the old loop saw nothing wrong — while the lane's own `byStation` would then count
    # that station twice and its total would exceed the shelf. An empty tuple makes a lane that
    # can never hold anything, and a duplicate lane NAME makes two boxes the reader cannot tell
    # apart. A guard that names itself after a property must actually test the property.
    _names = [n for n, _s, _w in LANES]
    for n in sorted(set(_names)):
        if _names.count(n) > 1:
            findings.append("lane %r is declared %d times — two boxes with one name, and a reader "
                            "cannot tell which reels are in which" % (n, _names.count(n)))
    for lane, stations, _why in LANES:
        if not stations:
            findings.append("lane %r covers NO stations, so it can never hold a reel and will sit "
                            "on the shelf as a permanently empty box with a label" % lane)
        for st in sorted(set(stations)):
            if list(stations).count(st) > 1:
                findings.append("lane %r lists station %r %d times — its byStation count would be "
                                "inflated and the lanes would out-total the shelf"
                                % (lane, st, list(stations).count(st)))
    seen = {}
    for lane, stations, _why in LANES:
        for st in stations:
            seen.setdefault(st, []).append(lane)
    for st in declared:
        if st not in seen:
            findings.append("station %r is in no lane, so every reel sitting there is INVISIBLE on "
                            "the shelf while the counts still add up among themselves" % st)
        elif len(seen[st]) > 1:
            findings.append("station %r is in %d lanes (%s) — a reel would be counted twice and "
                            "the total would exceed the shelf" % (st, len(seen[st]), seen[st]))
    for st in seen:
        if st not in declared:
            findings.append("lane map names %r, which reel_router does not have — the shelf would "
                            "show a lane the backend cannot fill" % st)
    return (not findings), findings


def lanes(rep=None, hide=None):
    """The four lanes over the router's answer. Decides nothing. -> dict

    -> {"ok", "lanes": [{name, why, stations, count, reels: [...]}], "shelf", "unknown",
        "reconciles", "why"}

    `hide` is a set of reel ids the CALLER has decided this console must not show. This module
    still decides nothing — it applies the caller's set to the router's report BEFORE grouping, so
    `shelf`, every lane `count`, every `byStation` figure and `reconciles` all move together off
    one filter rather than four hand-patched numbers.

    ⚠ `reconciles` IS PUBLISHED, NOT ASSUMED. It is the sum over lanes plus UNKNOWN against the
    shelf. A view that quietly drops a reel is the whole reason the router returns a report rather
    than a list, and inheriting that discipline is the point.
    """
    out = {"ok": False, "lanes": [], "shelf": 0, "unknown": 0, "reconciles": False, "why": ""}
    if rep is None:
        try:
            import reel_router as _rr
            rep = _rr.route()
        except Exception as exc:
            out["why"] = ("the router could not be walked (%s), so the shelf is UNKNOWN — this is "
                          "NOT an empty river" % type(exc).__name__)
            return out
    # ⚠⚠ v2881 — THE MAP IS CHECKED FIRST, BECAUSE IT IS A PROPERTY OF THE CODE, NOT OF THE DATA.
    # `assert_partitions()` reads LANES and reel_router.STATIONS and nothing else — it needs no
    # reels, no shelf and no router answer. It used to run BELOW the router check, so on any
    # machine whose walk comes back UNKNOWN the structural check never ran at all — and that is
    # EVERY CI runner, which has no reels by construction. The one place a broken map would be
    # caught before it reached him was the one place it was unreachable.
    # MEASURED: with printer._sources emptied to imitate a runner, test_a_BROKEN_map_refuses_to_draw
    # fails with "'partition' not found in 'the router did not answer…'" — the transient refusal
    # masking the permanent defect. A broken map is broken whether or not the river is flowing, so
    # it is now reported whether or not the router answered.
    # [[feedback-blind-fixture-green-gate]] [[gate-blind-to-unexercised-input]]
    ok, findings = assert_partitions()
    if not ok:
        # ⚠ REFUSE TO DRAW A RIVER THAT WOULD LOSE REELS. Rendering four tidy lanes over a broken
        # map is worse than rendering nothing, because it looks complete. [[unknown-stays-unknown]]
        out["why"] = "the lane map does not partition the router's stations: %s" % "; ".join(findings)
        return out
    if not isinstance(rep, dict) or not rep.get("ok"):
        out["why"] = ("the router did not answer (%s), so there are no lanes to draw and this is "
                      "not a report that the river is empty"
                      % ((rep or {}).get("why") or "no reason given"))
        return out
    # ⚠⚠ v2893 — ONE FILTER, AND EVERY FIGURE MOVES WITH IT (#58).
    # Konyo, 2026-09-10, on the 8 reels the suite opens by name: *"no need to even mention those 8
    # anywhere visually on the console."* `_shelf_visible()` had subtracted them from
    # /api/reel_story since v2877 and the RIVER STRIP — the other surface drawn from the same
    # shelf, two panels away — still counted every one of them. MEASURED on his console:
    #
    #     strip header   24 reel(s) on the shelf      the shelf below it        16 rows
    #     INTAKE 6 · PRINTER 2 · CAPTURE 12 · TOMBSTONE 4   of which 2 · 1 · 4 · 1 are fixtures
    #
    # Two surfaces, one shelf, two answers — the exact defect the ruling was given to end.
    #
    # ⚠ THE CUT IS ON THE REPORT, NOT ON THE OUTPUT, and that is the whole reason it is here and
    # not four subtractions at the endpoint. Everything below — `by`, each lane's `reels`,
    # `count`, `byStation`, `shelf`, `unknown` and `reconciles` — is derived from `rep`. Filter the
    # report once and all of them are already right; patch the output and each figure is a
    # separate chance to miss one. [[zero-needs-a-denominator]] [[label-outlived-referent]]
    rep_all = rep                      # ⚠ the ROSTER still needs every reel — see below
    out["hidden"] = 0
    if hide:
        _h = set(str(x) for x in hide if x)
        _keep, _drop = [], []
        for _r in (rep.get("reels") or []):
            (_drop if str(_r.get("reel") or "") in _h else _keep).append(_r)
        if _drop:
            # ⚠ UNKNOWN IS ITS OWN DENOMINATOR. A hidden reel the router could not place is
            # counted in `unknown`, not in any lane, so hiding it must decrement BOTH or
            # `reconciles` goes false on a river that is perfectly intact.
            _unk = sum(1 for _r in _drop if _r.get("station") == "UNKNOWN")
            rep = dict(rep)
            rep["reels"] = _keep
            rep["shelf"] = max(0, int(rep.get("shelf") or 0) - len(_drop))
            rep["unknown"] = max(0, int(rep.get("unknown") or 0) - _unk)
            out["hidden"] = len(_drop)
    by = {}
    for r in (rep.get("reels") or []):
        by.setdefault(r.get("station"), []).append(r)

    # ⚠⚠ THE CLOSURE HALF, AND IT IS STILL NOT A SECOND PIPELINE. `reel_router.roster()` assigns
    # the TOMBSTONE station; this only asks for its answer and hands the rows to whichever lane
    # the map says covers that station. Nothing here decides where a reel is.
    #
    # ⚠⚠ WHY IT HAD TO BE ADDED, MEASURED 2026-09-09 (#36). The TOMBSTONE lane is labelled
    # "closed out — the extraction contract is satisfied", and until now it could only ever hold
    # ROUTED-but-still-on-disk reels: a reel that had ACTUALLY closed out leaves the disk, so it
    # was absent from every walk feeding this file. 41 reels were drawable and 428 closed ones
    # were not — the lane could never show the one thing its own label promises.
    # [[label-outlived-referent]] [[plumbing-with-no-tap]]
    #
    # ⚠ `count` AND `reconciles` ARE NOT TOUCHED BY THIS. They are about the SHELF — reels on
    # disk — and folding 428 closed reels into them would move a number he reads without a word
    # on screen saying why. The closure rows ride beside, with their own count, their own
    # denominator and their own named source. [[zero-needs-a-denominator]]
    closed_by_station, closed_why, closed_n = {}, "", None
    try:
        import reel_router as _rr2
        # ⚠⚠ THE ROSTER GETS `rep_all`, NOT THE FILTERED REPORT, AND THIS IS NOT A DETAIL.
        # roster() decides a reel has CLOSED OUT by its ABSENCE from the walk. Hand it a report
        # with 8 reels removed and it reads all 8 as closed — the console would hide them from the
        # shelf and then announce them in the TOMBSTONE lane and in `closed`, which is the one
        # place the ruling most obviously forbids. Hidden means unseen, never "finished".
        _ro = _rr2.roster(rep=rep_all)
        closed_why = str(_ro.get("closedWhy") or "")
        if _ro.get("closedReadable"):
            closed_n = _ro.get("closed")
            for _r in (_ro.get("rows") or []):
                if not _r.get("onDisk"):
                    closed_by_station.setdefault(_r.get("station"), []).append(_r)
        else:
            closed_by_station = None
    except Exception as _exc:
        closed_by_station = None
        closed_why = ("the closure roster raised %s, so how many reels have closed out is "
                      "UNKNOWN — it is NOT none" % type(_exc).__name__)

    total = 0
    for name, stations, why in LANES:
        # ⚠ FIFO INHERITED: `rep["reels"]` is already oldest-first, so walking it once per lane
        # preserves that order without re-sorting. Concatenating per station would NOT — it would
        # order by station first and clock second.
        reels = [r for r in (rep.get("reels") or []) if r.get("station") in stations]
        total += len(reels)
        # ⚠ FIFO INHERITED HERE TOO — `_ro["rows"]` is already ordered by the router's one clock
        # rule (oldest capture first, no-clock LAST), so slicing preserves it. `SHOW_CLOSED` caps
        # what is HANDED TO THE PAGE, never what is counted: `closedCount` is the whole ledger and
        # `closedShown` says how much of it is drawn, so a reader can never mistake the sample for
        # the total. #15 is the precedent — one open built ~72,700 DOM nodes and stopped the
        # window painting. [[zero-needs-a-denominator]]
        _cl = None if closed_by_station is None else [
            r for st in stations for r in (closed_by_station.get(st) or [])]
        _lane = {
            "name": name,
            "why": why,
            "stations": list(stations),
            "count": len(reels),
            "byStation": {s: len(by.get(s) or []) for s in stations},
            "reels": reels,
            # None is UNKNOWN — the ledger could not be read — and is never rendered as 0.
            "closedCount": (None if _cl is None else len(_cl)),
            "closedShown": (None if _cl is None else min(len(_cl), SHOW_CLOSED)),
            "closedReels": (None if _cl is None else _cl[:SHOW_CLOSED]),
            "closedWhy": closed_why,
        }
        out["lanes"].append(_lane)
    out["shelf"] = rep.get("shelf") or 0
    # ⚠ TWO DIFFERENT DENOMINATORS, BOTH NAMED. `shelf` is reels ON DISK and is what `reconciles`
    # is about; `closed` is reels that have LEFT it. Publishing only one of them is how the
    # per-reel surfaces came to cover 41 of 469 lifetimes with nothing saying so.
    out["closed"] = closed_n
    out["closedWhy"] = closed_why
    out["lifetime"] = (None if closed_n is None else (rep.get("shelf") or 0) + int(closed_n))
    out["unknown"] = rep.get("unknown") or 0
    out["reconciles"] = (total + out["unknown"]) == out["shelf"]
    out["ok"] = True
    out["why"] = rep.get("why") or ""
    # ⚠⚠ NAME THE STATIONS THAT FELL OUT, DO NOT JUST COUNT THEM. Raised by the second eye: a
    # reel at a station no lane covers is dropped from every lane and from `total`, so
    # `reconciles` goes false and the reader is handed a bare mismatch with nothing to act on.
    # The station name IS the finding — it says which upstream change orphaned them.
    _mapped = set()
    for _n, _sts, _w in LANES:
        _mapped |= set(_sts)
    orphan = sorted({r.get("station") for r in (rep.get("reels") or [])
                     if r.get("station") and r.get("station") not in _mapped
                     and r.get("station") != "UNKNOWN"})
    out["orphanStations"] = orphan
    if not out["reconciles"]:
        out["why"] = ("the lanes hold %d reel(s) and the shelf has %d — %d have gone missing from "
                      "the picture%s"
                      % (total, out["shelf"], out["shelf"] - total - out["unknown"],
                         (" · they sit at %s, which no lane covers" % ", ".join(orphan))
                         if orphan else "")) \
                     + ((" · " + out["why"]) if out["why"] else "")
    return out


def main(argv):
    import json
    if "--check" in argv:
        ok, f = assert_partitions()
        print("lane map partitions the router's stations: %s" % ("ok" if ok else "FAILED"))
        for x in f:
            print("  - %s" % x)
        return 0 if ok else 1
    rep = lanes()
    if not rep["ok"]:
        print("UNKNOWN — %s" % rep["why"])
        return 1
    print("THE RIVER, FOUR LANES (shelf %d, reconciles %s)" % (rep["shelf"], rep["reconciles"]))
    for ln in rep["lanes"]:
        bits = " + ".join("%s:%d" % (s, ln["byStation"][s]) for s in ln["stations"])
        print("  %-10s %3d   %s" % (ln["name"], ln["count"], bits))
        if "--reels" in argv:
            for r in ln["reels"][:5]:
                print("        %-34s %s" % (r["reel"][:34], r["station"]))
    if not rep["reconciles"]:
        print("\n⚠ %s" % rep["why"])
    return 0



# v3848 (Dean /api/river 23-38 s under load) - CONCURRENT ASKS SHARE ONE WALK. MEASURED on the Mac: lanes() is
# ~2.4 s, almost all reel_router.route(); Dean's PC is ~10x slower, and every overlapping /api/river (the strip, a
# shadow, a probe) started its OWN route() on a busy GIL, so each one waited for all of them. A caller that arrives
# while a walk with the same `hide` is running now waits for THAT walk and takes its answer; nothing is cached past
# it - the next ask after it ends walks again, so no answer is older than the walk the caller waited on. No timeout
# was raised. -> the same dict lanes() returns
import threading as _th
_SHARED_LOCK = _th.Lock()
_SHARED = {}          # key -> {"ev": Event, "out": dict|None, "err": BaseException|None}


def _release_shared(key):
    """Drop a shared walk's slot. lanes_shared keeps its own pop, so this line stays unique there."""
    with _SHARED_LOCK:
        _SHARED.pop(key, None)


_LAST = {}                # key -> {"at": float, "out": dict}
_REFRESH_S = 5.0
_REFRESH_ON = set()


def _lanes_refresh(key, hide):
    """One background walk. An exception writes nothing. The caller never waits on this."""
    import time
    out = None
    failed = False
    try:
        out = lanes(hide=hide)
    except Exception:
        failed = True
    finally:
        _release_shared(key)
        with _SHARED_LOCK:
            _REFRESH_ON.discard(key)
    if failed or not isinstance(out, dict):
        return
    with _SHARED_LOCK:
        _LAST[key] = {"at": time.time(), "out": out}


def lanes_last(hide=None):
    """The last finished river walk for this hide set. Never waits. -> dict | None

    None: this process has not finished a walk yet (UNKNOWN, not an empty river). A dict is a
    copy of that walk plus ageMs. When the kept walk is missing or older than _REFRESH_S, one
    daemon starts; a second ask does not start another while that one is running.
    """
    import time
    key = tuple(sorted(str(x) for x in (hide or ())))
    hide_snap = None if hide is None else set(hide)
    now = time.time()
    start = False
    with _SHARED_LOCK:
        cur = _LAST.get(key)
        due = cur is None or (now - cur["at"]) >= _REFRESH_S
        if due and key not in _REFRESH_ON:
            _REFRESH_ON.add(key)
            start = True
        if cur is None:
            payload = None
        else:
            payload = dict(cur["out"])
            payload["ageMs"] = int((now - cur["at"]) * 1000)
    if start:
        _th.Thread(target=_lanes_refresh, args=(key, hide_snap), daemon=True).start()
    return payload


def lanes_shared(hide=None):
    key = tuple(sorted(str(x) for x in (hide or ())))
    with _SHARED_LOCK:
        cur = _SHARED.get(key)
        mine = cur is None
        if mine:
            cur = _SHARED[key] = {"ev": _th.Event(), "out": None, "err": None}
    if not mine:
        cur["ev"].wait()
        if cur["err"] is not None:
            raise cur["err"]
        return cur["out"]
    try:
        cur["out"] = lanes(hide=hide)
        return cur["out"]
    except BaseException as e:
        cur["err"] = e
        raise
    finally:
        with _SHARED_LOCK:
            _SHARED.pop(key, None)
        cur["ev"].set()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

