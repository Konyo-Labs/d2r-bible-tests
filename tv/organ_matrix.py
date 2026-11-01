#!/usr/bin/env python3
"""A3 — WHICH SURFACES HAVE WHICH ORGANS, MEASURED, WITH THE HOLES LEFT AS HOLES.

His ask, over a table that was mostly empty: *"fix those gaps and anywhere else.. make it unified
and logical and coded properly with watchdogged and eagle eyed and doctor and corraborotror"* —
`surfaces registry` empty across every column, `stash_eye grid` empty, `enlarge` empty, `OCR worker`
present in exactly one. **Every surface gets the same four organs, or it is honestly marked as not
having them.**

⚠⚠ THIS FILE DOES NOT FILL THE TABLE IN. It measures it. A matrix that reports coverage it cannot
demonstrate is worse than the empty one he was shown, because the empty one at least told the
truth. Every cell here is one of:

    COVERED    the organ's own output NAMES this surface — checked, not assumed
    ABSENT     the organ runs and does not name it
    UNKNOWN    the organ could not be asked at all (no report, would not import, raised)

⚠ UNKNOWN IS NOT ABSENT. Two of the four organs have no callable report on this tree —
console_doctor exposes none and there is no `eagle` module — so their columns are UNKNOWN
everywhere rather than empty, and the difference is the whole point. An organ nobody can ask has
not been shown to miss anything; it has not been shown to do anything either.
[[unknown-stays-unknown]] [[the-unjoined-end]]
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

COVERED, ABSENT, UNKNOWN, MISNAMED = "COVERED", "ABSENT", "UNKNOWN", "MISNAMED"

#: The four organs, and how to ask each one what it covers. `None` where nothing can be asked —
#: recorded as an absence of an INSTRUMENT, never as an absence of coverage.
ORGANS = ("eagle", "watchdog", "doctor", "corroborator")


#: ⚠ "key" BELONGS HERE AND ITS ABSENCE MADE A LIVE ORGAN LOOK DEAD. The route rows identify
#: themselves with `key`, not `id`/`name`/`route`, so the corroborator extracted nothing and this
#: file reported "no route set answered" about three modules that had answered all day. A reader
#: would have concluded the corroborator was broken; the extractor was. Suspect the instrument.
#: ⚠ `check` WAS THE MISSING SYNONYM AND ITS ABSENCE WOULD HAVE BEEN SILENT. Every organ names
#: the things it watches under some key, and this list is how the matrix reads all of them without
#: forcing each organ to carry a second copy of its own vocabulary. console_doctor names its 34
#: subjects under `check`, which was not here — so the moment console_doctor.report() existed, the
#: doctor column would have flipped from an honest "cannot be asked" to a confident
#: "watches nothing at all", with 44 ABSENT cells and no error anywhere. A reader missing one
#: synonym does not fail; it reports emptiness. [[the-unjoined-end]] [[unknown-stays-unknown]]
def _names_from(rows, keys=("id", "key", "lane", "route", "name", "surface", "lock", "target",
                            "check")):
    out = set()
    for r in (rows or []):
        if isinstance(r, dict):
            # ⚠⚠ v3040 — A LIST UNDER `surfaces` IS THE ORGAN ANSWERING IN THIS TABLE'S OWN
            # VOCABULARY, and it was silently ignored: every key below is read only when its
            # value is a STRING, so a row saying surfaces: ["heart", "locks"] contributed
            # nothing. One check can legitimately watch several surfaces, so the plural has to
            # be a list — and the reader has to accept one. [[the-unjoined-end]]
            _sf = r.get("surfaces")
            if isinstance(_sf, (list, tuple)):
                for _v in _sf:
                    if isinstance(_v, str) and _v:
                        out.add(_v)
            for k in keys:
                v = r.get(k)
                if isinstance(v, str) and v:
                    out.add(v)
        elif isinstance(r, str):
            out.add(r)
    return out


def _ask(mod_name, attr, extract):
    """-> (set_of_names, why_unknown). An organ that cannot be asked yields (None, reason)."""
    try:
        mod = __import__(mod_name)
    except Exception as e:
        return None, "%s will not import (%s)" % (mod_name, str(e)[:50])
    fn = getattr(mod, attr, None)
    if fn is None:
        return None, "%s has no %s()" % (mod_name, attr)
    try:
        return extract(fn()), ""
    except Exception as e:
        return None, "%s.%s() raised (%s)" % (mod_name, attr, str(e)[:50])


def _ask_live_eagle():
    """The eagle as the RUNNING console holds it. -> (set_of_names|None, why_unknown)

    ⚠ A cold import cannot answer this and must not pretend to. If the console is not up, this
    returns None with the reason — UNKNOWN, never an empty set, because "the console was not
    running" and "the eagle watches nothing" are opposite facts and only one of them is a defect.
    [[unknown-stays-unknown]]
    """
    import json as _json
    import urllib.request as _rq
    try:
        with _rq.urlopen("http://127.0.0.1:17772/api/status", timeout=6) as _r:
            _d = _json.loads(_r.read().decode("utf-8", "replace"))
    except Exception as e:
        return None, ("the running console did not answer on :17772 (%s), and a cold import of "
                      "control_app holds only the unfilled _EAGLE literal" % str(e)[:44])
    _e = _d.get("eagle")
    if not isinstance(_e, dict):
        return None, "the console answered but published no eagle block"
    _rows = (_e.get("rows") or []) + (_e.get("slowRows") or [])
    if not _rows:
        return None, ("the console answered and the eagle block carried NO rows — %s"
                      % str(_e.get("say") or "no reason given")[:60])
    return _names_from(_rows), ""


def organ_coverage():
    """What each organ actually names. -> {organ: (names|None, why_unknown)}"""
    out = {}
    # ⚠⚠ v3036 — THE EAGLE WAS ASKED COLD, SO ITS COLUMN COULD NEVER BE ANYTHING BUT EMPTY.
    # `_ask` does `__import__("control_app")` and calls `eagle_state()` on a FRESHLY IMPORTED
    # module, where `_EAGLE` is still its literal initial value — `{"rows": [], "say": "not
    # measured yet"}`. That dict is only ever filled by the RUNNING console's background loop, in
    # another process. Measured 2026-09-12: the live console publishes 58 eagle rows on
    # /api/status while this table reported "eagle answered, and named nothing at all" — which the
    # table itself flagged as indistinguishable from "watches nothing". It was neither: nobody had
    # asked the process that knows. An organ judged by an instrument that cannot reach it has not
    # been shown to miss anything. [[feedback-suspect-the-instrument]] [[the-unjoined-end]]
    out["eagle"] = _ask_live_eagle()
    # WATCHDOG — the health engine's own check rows.
    out["watchdog"] = _ask("health_engine", "report",
                           lambda r: _names_from((r or {}).get("rows") if isinstance(r, dict) else r))
    # DOCTOR — the console doctor's findings.
    out["doctor"] = _ask("console_doctor", "report",
                         lambda r: _names_from((r or {}).get("rows") if isinstance(r, dict) else r))
    # CORROBORATOR — the route sets compare siblings against each other and flag the odd one out.
    def _corr(_f):
        """⚠⚠ IT WAS THROWING AWAY THE ONE FACT THAT MADE THE JOIN POSSIBLE. Three modules were
        flattened into one set, so `chronicle_routes` saying `runeword` and `fleet_routes` saying
        `runeword` became a single bare name — and every route surface (`chronicle.runeword`,
        `fleet.sets`, `roster.unique`) could only ever come back MISNAMED. All nine of them, every
        run, for exactly this reason: WHICH LANE a name came from is known right here, at the call
        site, and was discarded one line later.

        Those nine were 100% of the MISNAMED cells in the table. They are not a naming problem in
        the route sets — the route sets are fine — they were a reader dropping a qualifier.

        So each name is published twice: bare (nothing that resolved before stops resolving) and
        qualified with its lane, spelled through the shared resolver so `runewords` and `runeword`
        land on the one form the surface registry uses. [[the-unjoined-end]] [[copy-drift]] §1
        """
        names = set()
        try:
            import one_name as _on
        except Exception:
            _on = None
        for m in ("chronicle_routes", "fleet_routes", "roster_routes"):
            lane = m[:-len("_routes")]
            try:
                mod = __import__(m)
                rep = mod.routes() if m == "chronicle_routes" else mod.routes(None)
                bare = _names_from(rep.get("routes"))
            except Exception:
                continue
            names |= bare
            for n in bare:
                # ⚠ EVERY FORM, NOT THE ROUTE FORM — because his three route sets do not agree
                # with each other. Measured: `chronicle.runeword` and `roster.runeword` are
                # SINGULAR while `fleet.runewords`, `fleet.sets`, `fleet.uniques` are PLURAL. One
                # form joined six of the nine and left fleet's three still reading MISNAMED, which
                # would have looked like a partial fix and was really this table meeting a
                # vocabulary split it did not cause.
                #
                # ⚠⚠ AND THAT SPLIT IS NOT FIXED HERE — it is only stopped from corrupting this
                # measurement. Three route sets, two spellings, is a real inconsistency in the
                # console and it is logged as REG-470; absorbing it silently in the reader is how
                # a drift becomes permanent. The corroborator genuinely watches the CONCEPT in
                # that lane however the lane spells it, so all forms are published and the
                # coverage answer is honest either way.
                forms = set()
                if _on:
                    for surface in ("route", "lane", "template"):
                        f = _on.form(n, surface)
                        if f:
                            forms.add(f)
                for f in (forms or {n}):
                    names.add("%s.%s" % (lane, f))
        # ⚠⚠ v3059 — THE CORROBORATOR COVERED 9 OF 58 SURFACES AND THAT WAS THE HOLE.
        # Measured 2026-09-13: this organ named ONLY the nine route subjects, so 49 surfaces
        # had no cross-witness at all — including the shelf, where a card said "19 frames"
        # and the dossier said "0 FRAMES" for the same reel and nothing noticed. An eagle
        # watches cheaply, a watchdog asks if a thing is alive, a doctor asks if a check
        # passes; only a corroborator compares two witnesses. On its first run the shelf
        # corroborator reported 52 of 53 reels disagreeing.
        #
        # ⚠ IT DECLARES ITS SURFACES. shelf_corroborate.SURFACES names them in the registry's
        # own vocabulary rather than being matched by resemblance — v3055 deleted a resolver
        # that matched on the tail and manufactured 8 cells of coverage that did not exist.
        # [[copy-drift]] [[the-unjoined-end]]
        try:
            import shelf_corroborate as _sc
            for _s in (_sc.SURFACES or ()):
                names.add(str(_s))
        except Exception:
            pass                      # an organ that cannot be asked adds nothing and says nothing
        # ⚠⚠ v3069 — AND THE TWO LOOPS THAT LEAVE A TRACE. Ten surfaces sat at 3 of 4 organs, all
        # missing this one, because a corroborator needs TWO INDEPENDENT witnesses and six of the
        # eight loops leave nothing an outside reader can date. These two do:
        #     _ledger_backup_loop   106 backup files, newest datable
        #     _vault_autoread_loop  .vault_autoread.json
        # The other six stay honestly ABSENT rather than filled — inventing a trace for them is
        # the coverage v3055 deleted. [[unknown-stays-unknown]] [[the-unjoined-end]]
        try:
            import loop_corroborate as _lc
            for _s in (_lc.SURFACES or ()):
                names.add(str(_s))
        except Exception:
            pass
        # ⚠⚠ v3071 — AND THE LOCKS, cross-witnessed on the arithmetic that decides whether his
        # vault may write: a source's BANKED attack count against the claims it DECLARES.
        # Compared PER SOURCE, never per lock — reel.route's 34 is 7 from reel_router_wilson plus
        # 27 from rung_accounting_wilson, and a per-lock total would have flagged a HARDENED lock
        # as 5x inflated. [[feedback-suspect-the-instrument]]
        try:
            import lock_evidence_corroborate as _le
            # ⚠ covered(), NOT SURFACES. v3071 unioned the DECLARED scope and painted three locks
            # COVERED that the organ had read nothing about. Scope is an intention; coverage is a
            # reading. [[unknown-stays-unknown]]
            for _s in (_le.covered() or ()):
                names.add(str(_s))
        except Exception:
            pass
        return names
    out["corroborator"] = (_corr(None), "") if _corr(None) else (None, "no route set answered")
    return out


#: The corroborator modules `organ_coverage()` reads. Kept in ONE place so a fifth corroborator
#: cannot be added to the reader and forgotten by the law that checks it — which is exactly how
#: the over-reach check came to test a proxy instead of the question. [[copy-drift]]
CORROBORATORS = ("shelf_corroborate", "loop_corroborate", "lock_evidence_corroborate")


def declared_surfaces():
    """Every surface a corroborator DECLARES it watches. -> {name}

    ⚠⚠ v3134 — THE OVER-REACH CHECK WAS ASKING A PROXY. `test_organ_matrix` flagged every COVERED
    surface whose origin was not "route" — a rule written when the corroborator covered routes and
    nothing else. Since then `loop_corroborate` and `lock_evidence_corroborate` arrived, each
    declaring its own SURFACES, and `shelf_corroborate` declares four more. MEASURED on HEAD:

        COVERED total 24  =  9 route  +  15 declared  +  0 with no basis

    Every one of the 11 the law called over-reach is in a registry:
        loop_corroborate.SURFACES           the 6 loops (_drift_loop, _orphan_watch, …)
        lock_evidence_corroborate.SURFACES  the 8 locks it LOOKS AT (its SCOPE)

    ⚠ `SURFACES` IS THE DECLARATION, NOT THE COVERAGE. `lock_evidence_corroborate` covers 5 of its
    8 — `covered()` returns only the locks with readable AGREE/OVERCLAIM evidence, and v3073 made
    `_corr()` use that for exactly this reason (console.pixel_rescue, frame.release and
    printer.stream are declared and unread). An allow-list wants the DECLARATION, which is right;
    calling it the coverage set is what would invite someone to "make it consistent" and let three
    unread locks read as covered. Named here so that edit is never made by accident.

    So the honest question is not "is this a route" but "did any corroborator SAY it watches
    this". A claim with a declaration behind it is coverage; a claim without one is invention.
    """
    out = set()
    for m in CORROBORATORS:
        try:
            out.update(str(x) for x in (getattr(__import__(m), "SURFACES", ()) or ()))
        except Exception:
            continue
    return out


def surfaces():
    """Everything that COULD be covered, derived from what already exists. -> {name: origin}"""
    found = {}
    try:
        import render_check as R
        for t in (R.TARGETS or {}):
            found[str(t)] = "render target"
    except Exception:
        pass
    try:
        import self_arming as SA
        for k in SA.LOCKS:
            found[k] = "valve"
        for k in getattr(SA, "ROUTES", {}):
            found[k] = "route"
    except Exception:
        pass
    # ⚠⚠ v3134 — A FOURTH REGISTRY THIS MAP WAS NEVER ASKING, AND KONYO RULED ON IT.
    # `shelf_corroborate.SURFACES` declares FOUR surfaces — ('shelf-cards', 'river-strip',
    # 'shelf.rows', 'shelf.scene') — and only the two render targets reached this map, because
    # they happen to also be `render_check.TARGETS`. The two DOTTED ones had no other source, so
    # the `shelf` lane did not exist here at all, while `vault.apply`, `reel.route`,
    # `prune.reports`, `printer.stream` and `frame.release` all arrive from `self_arming`.
    #
    # MEASURED: test_organ_matrix reported STRAY 2 — shelf.rows, shelf.scene — "the corroborator
    # invented lane(s) that do not exist". It had not invented them; this map had never been told.
    # Konyo, 2026-09-14, asked which side was wrong: "YES it is shelf.rows/shelf.scene" — shelf IS
    # a lane, so the map carries it.
    #
    # ⚠ THE ORIGIN IS HONEST ABOUT WHERE IT CAME FROM. These are not render targets, valves or
    # vessels; they are surfaces a corroborator DECLARES it watches. Calling them "route" to make
    # the over-reach law quieter would be picking a label for its effect on a test rather than for
    # what the thing is. [[the-unjoined-end]] [[label-outlived-referent]]
    # ⚠ v3136 — THE SAME ROSTER, NOT A SECOND COPY OF IT. v3134 added `declared_surfaces()` over
    # CORROBORATORS and then hardcoded `shelf_corroborate` alone twenty lines below, so a dotted
    # name added to `loop_corroborate.SURFACES` would be allow-listed by the law and still have no
    # row here — STRAY, "invented lane(s) that do not exist", the exact false accusation v3134
    # exists to stop, fixed for shelf and left standing for everyone else. Caught by the second
    # eye in one read. I fixed a copy-drift by writing a new one. [[copy-drift]]
    for _m in CORROBORATORS:
        try:
            for k in (getattr(__import__(_m), "SURFACES", ()) or ()):
                found.setdefault(str(k), "declared surface")
        except Exception:
            continue
    try:
        import heart as H
        for v in (H.vessels().get("vessels") or []):
            n = v.get("name")
            if n:
                found.setdefault(str(n), "vessel")
    except Exception:
        pass
    return found


def _lane_of(name):
    """The lane a dotted surface name belongs to, or None if it carries no lane. -> str|None

    `fleet.sets` -> "fleet". `route chronicle · sets` -> None, because an organ that spells a
    subject in prose has not claimed a lane and must not be judged as though it had.
    """
    s = str(name or "").strip().lower()
    return s.split(".")[0] if "." in s else None


def _same_lane(surface, name):
    """May a name from this organ stand for this surface at all? -> bool

    ⚠⚠ THIS IS THE GUARD THAT STOPPED A TABLE FROM BORROWING ONE LANE'S ORGANS FOR ANOTHER'S.
    Measured 2026-09-13: the eagle and the doctor each name exactly two route subjects,
    `chronicle.set` and `chronicle.unique`, and NOTHING in the fleet or roster lane —
    `lanes.get("fleet")` and `lanes.get("roster")` were both `[]` for both organs. The matrix
    nevertheless reported `fleet.sets`, `fleet.uniques`, `roster.set` and `roster.unique` as
    MISNAMED on both columns — 8 cells, 100% of the MISNAMED in the table — because
    `one_name.same_thing` compares the TAIL and is deliberately lane-blind:

        same_thing("fleet.sets",  "chronicle.set") -> True
        same_thing("fleet.sets",  "roster.set")    -> True

    MISNAMED means *the organ IS watching this thing and calls it something else* (see the
    banner this file prints at the bottom). For those 8 cells that sentence was FALSE: nothing
    was watching them, and the table said something was. That is worse than the empty table this
    module was written to replace, which is the module's own stated standard.

    All six are separately registered surfaces (`surfaces()` carries `chronicle.set`,
    `fleet.sets`, `roster.set` and their unique twins, every one with `origin="route"`), so a
    cross-lane match is not a spelling difference — it is a different subject.

    The rule: when BOTH sides carry a lane, the lanes must agree. When either side carries none —
    an organ naming a subject in prose, like `route chronicle · sets` — the older tail rule still
    decides, because a name that never claimed a lane cannot be caught contradicting one.
    [[unknown-stays-unknown]] [[the-unjoined-end]]
    """
    a, b = _lane_of(surface), _lane_of(name)
    if a is None or b is None:
        return True
    return a == b


def _same_thing(surface, names):
    """Does the organ name this surface under a DIFFERENT string? -> bool

    ⚠ THIS WAS THE FIFTH LOCAL ALIAS MAP AND IT IS NOW THE FIRST TO GO. It carried its own narrow
    rule — tail-after-a-dot plus singular/plural — which is how the console came to hold five
    resolvers that disagree on 6 of 9 inputs. tv/one_name.py answers this question for everyone
    now; adopting it was measured behaviour-neutral first: 132 cells agree, 0 differ.
    Falls back to the old rule only if one_name cannot be imported, because a matrix that stops
    working is worse than one using a narrower rule. [[copy-drift]]
    """
    try:
        import one_name as _on
    except Exception:
        _on = None
    if _on is not None:
        return any(_on.same_thing(surface, n) and _same_lane(surface, n)
                   for n in (names or ()))
    tail = surface.split(".")[-1].strip().lower()
    if not tail:
        return False
    cands = {tail, tail + "s", tail.rstrip("s")}
    for n in names:
        low = str(n).strip().lower()
        if low in cands or low.split(".")[-1] in cands:
            return True
    return False


def comparability(cov, surf):
    """Can this organ's vocabulary be COMPARED to the surface list at all? -> {organ: (bool, why)}

    ⚠⚠ THE TABLE PRINTED `ABSENT` FOR THREE DIFFERENT SITUATIONS AND ONLY ONE WAS A MEASUREMENT.
    Measured the moment console_doctor became askable (v2496):

        corroborator   6 names, 9 of the 44 surfaces resolve  -> comparable
        doctor        34 names, ZERO resolve                  -> different KIND of name
        watchdog       7 names, ZERO resolve                  -> different KIND of name
        eagle          0 names                                -> answered with nothing at all

    The doctor names CONCERNS — 'armed migration', 'art corpus', 'board join'. The surfaces are
    CODE OBJECTS — '_bridge_prober', '_chron_autoread_loop', 'vault.apply'. Neither list is
    wrong; they simply do not name the same kind of thing, so "the doctor does not watch
    _bridge_prober" is not something this table has established. Printing ABSENT there asserts a
    measurement nobody took, and it would have arrived as 44 confident cells replacing an honest
    'could not be asked'. [[unknown-stays-unknown]] — the gap between "we did not look" and "we
    looked and it was not there" is exactly where fabrication lives.

    An organ that names NOTHING is the third case and it is not the same as the second: an empty
    answer cannot distinguish "watches nothing" from "had nothing to say just now" (eagle_state()
    returns no rows when the console is not running), so it is UNKNOWN rather than a verdict.

    The rule is deliberately not a threshold: ONE surface resolving is enough to make the
    vocabulary comparable, because at that point ABSENT for the rest is a real finding about
    coverage rather than an artefact of two lists talking past each other.
    """
    out = {}
    for organ in ORGANS:
        names, _w = cov.get(organ, (None, "not asked"))
        if names is None:
            out[organ] = (False, "could not be asked")
        elif not names:
            out[organ] = (False, "answered, and named nothing at all — which cannot tell "
                                 "'watches nothing' apart from 'had nothing to say just now'")
        else:
            hits = sum(1 for s in surf if s in names or _same_thing(s, names))
            out[organ] = ((hits > 0),
                          "" if hits else
                          "names %d thing(s), and NONE of them resolves to any of the %d surfaces "
                          "— it is naming a different KIND of thing (concerns, not code objects), "
                          "so this table has not established what it does or does not watch"
                          % (len(names), len(surf)))
    return out


#: Filled by matrix() so main() can say how wide its verdict is. A module-level handoff rather
#: than a third return value, because matrix()'s (rows, why) shape is unpacked in four callers and
#: widening a tuple breaks all of them at once — the v2228 lesson, which cost nine call sites.
LAST_COMPARABILITY = {}


def matrix(cov=None):
    """-> (rows, organ_why). One row per surface, one cell per organ.

    v3849 - `cov` lets a caller judge the matrix against the SAME organ answer it was built from.
    The eagle is asked live over :17772; asking it twice (once here, once by the checker) under
    gate load could get an answer the first time and a timeout the second, and the checker then
    reported a COVERED cell as "could not be asked" - two measurements compared as one."""
    if cov is None:
        cov = organ_coverage()
    why = {o: cov[o][1] for o in ORGANS if cov.get(o) and cov[o][1]}
    _surf_all = surfaces()
    comp = comparability(cov, _surf_all)
    LAST_COMPARABILITY.clear()
    LAST_COMPARABILITY.update(comp)
    for o, (ok, w) in comp.items():
        if not ok and w and not why.get(o):
            why[o] = w
    rows = []
    for name, origin in sorted(_surf_all.items()):
        cells = {}
        for o in ORGANS:
            names, _w = cov.get(o, (None, "not asked"))
            if names is None:
                cells[o] = UNKNOWN          # the ORGAN could not be asked — not the surface's fault
            elif not comp[o][0]:
                # ⚠ ITS VOCABULARY DOES NOT MEET THIS LIST, so nothing about this cell was
                # measured. ABSENT here would be a verdict on evidence that does not exist.
                cells[o] = UNKNOWN
            elif name in names:
                cells[o] = COVERED
            else:
                # ⚠⚠ NOT COVERED AND NOT ABSENT — A THIRD THING, AND IT IS THE WHOLE ANSWER TO A3.
                # The corroborator names `runeword`, `sets`, `uniques`; the surface is
                # `chronicle.runeword`, `fleet.sets`. The organ IS watching this thing and calls
                # it something else, so a plain membership test reports ABSENT and the matrix
                # fills with holes that are not holes. That is the table he was shown.
                #
                # It is the same disjoint-vocabulary defect as A1's FLOWING (organ ids vs lane
                # names) and v2480's tab vocabulary (`unique` vs `uniques`) — three instances in
                # one day, which is a territory, not a coincidence.
                cells[o] = MISNAMED if _same_thing(name, names) else ABSENT
        rows.append({"surface": name, "origin": origin, "cells": cells,
                     "covered": sum(1 for v in cells.values() if v == COVERED),
                     "misnamed": sum(1 for v in cells.values() if v == MISNAMED),
                     "unknown": sum(1 for v in cells.values() if v == UNKNOWN)})
    return rows, why


def main(argv=None):
    rows, why = matrix()
    print("A3 — SURFACE × ORGAN, measured. COVERED = the organ names it · ABSENT = the organ's "
          "vocabulary reaches this list and does not name it · UNKNOWN = nothing was established "
          "(the organ could not be asked, answered with nothing, or names a different KIND of "
          "thing)\n")
    print("%-24s %-14s %s" % ("surface", "origin", "  ".join("%-12s" % o for o in ORGANS)))
    print("-" * 96)
    for r in rows:
        print("%-24s %-14s %s" % (r["surface"][:24], r["origin"],
                                  "  ".join("%-12s" % r["cells"][o] for o in ORGANS)))
    tot = len(rows)
    full = sum(1 for r in rows if r["covered"] == len(ORGANS))
    mis = sum(r.get("misnamed", 0) for r in rows)
    # ⚠⚠ "HAVE NONE" MUST NOT COUNT A SURFACE THAT IS WATCHED UNDER ANOTHER NAME. This read
    # `covered == 0` and so reported 44-have-none on the same screen as 9-are-MISNAMED — a cold
    # cross-family read caught it: "the first line treats the data at face value; the second
    # directly contradicts that framing". It is the same collapse the MISNAMED state exists to
    # prevent, reappearing in the SUMMARY of it. A count that ignores a state is that state
    # deleted. [[unknown-stays-unknown]]
    # ⚠⚠ AND IT MUST NOT COUNT AN UNKNOWN CELL AS A HOLE EITHER — the same collapse, one layer
    # out. "have none at all" once meant `covered == 0 and not misnamed`, which was true while
    # every organ's vocabulary was comparable. The moment console_doctor became askable (v2496),
    # three of the four columns turned UNKNOWN — the organs name CONCERNS and the surfaces are
    # CODE OBJECTS — and this line went on reporting 35-have-none from cells that had stopped
    # being measurements. A RIGHT NUMBER UNDER A WORD THAT STOPPED BEING TRUE.
    # [[label-outlived-referent]]
    #
    # A surface has been SHOWN to have nothing only when at least one organ could actually be
    # compared against it and did not name it. Everything else is unmeasured, and says so.
    none = sum(1 for r in rows
               if r["covered"] == 0 and not r.get("misnamed")
               and r.get("unknown", 0) < len(ORGANS))
    dark = sum(1 for r in rows if r.get("unknown", 0) == len(ORGANS))
    joined = sum(1 for r in rows if r["covered"] == 0 and r.get("misnamed"))
    # ⚠ AND SAY HOW MANY ORGANS THAT VERDICT RESTS ON. "35 have none" reads as "35 things
    # nobody is watching", which would be a serious claim — and it rests on the ONE organ whose
    # vocabulary reaches this list. The other three were not compared, so they have neither
    # confirmed nor denied anything. A number is only as wide as the evidence under it.
    comp = LAST_COMPARABILITY
    ncomp = sum(1 for o in ORGANS if comp.get(o, (False, ""))[0])
    print("\n%d surface(s): %d have all four organs, %d are named by NO organ that could be "
          "compared — and only %d of the %d organs could be — and %d are watched under another "
          "name and would count as covered the moment the join is made."
          % (tot, full, none, ncomp, len(ORGANS), joined))
    if dark:
        print("⚠ %d surface(s) have every cell UNKNOWN — no organ's vocabulary could be compared "
              "against them at all. They are not holes and they are not covered; nothing about "
              "them has been established, and counting them as either is the fabrication this "
              "table exists to avoid." % dark)
    if mis:
        print("⚠ %d cell(s) are MISNAMED — the organ IS watching that thing and calls it "
              "something else. Those are not holes; they are a join nobody made, and reporting "
              "them as ABSENT is how this table came to look empty." % mis)
    if why:
        # ⚠ "COULD NOT BE ASKED" IS NOW ONLY ONE OF THE REASONS, and saying it for all of them
        # is a second stale label. console_doctor answers perfectly well; what fails is that its
        # 34 names and these 44 surfaces are different KINDS of name. An organ reported as
        # unaskable when it is merely incomparable sends the reader to fix the wrong thing.
        print("\n⚠ %d of %d organs have a column that is UNKNOWN everywhere — not empty, and for "
              "these reasons:" % (len(why), len(ORGANS)))
        for o, w in sorted(why.items()):
            print("   %-14s %s" % (o, w))
        print("   An organ that could not be asked — or that answers in a vocabulary this list "
              "cannot meet — has not been shown to miss anything, and has not been shown to do "
              "anything either.")
    return 0


if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
