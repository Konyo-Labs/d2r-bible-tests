#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A DEMONSTRATION ON HIS REAL REELS — did they go through, and does downstream still agree?

Konyo, 2026-09-04: *"do tests on the reels see that they get run and proccesed through the printer
and everything down stream correctly as it was registered before.. chronicles and all the
readers.. everytinh was working before.. so it needs to be tested too"*, then *"simulations",
"demonstrations", "based on real reels", "ingame", "those same reels", "see that they got
proccsed logically coded"*.

⚠⚠ THIS IS A DEMONSTRATION, NOT A UNIT TEST, AND THE DIFFERENCE IS THE POINT. The suites already
assert behaviour against fixtures. What nothing did was take HIS OWN FOOTAGE, walk it through the
pipeline that has been rebuilt underneath it over nine versions, and show — reel by reel — that
every station still answers and that the numbers downstream are the ones that were registered
before any of it changed.

★ IT ASSERTS AGAINST REGISTERED VALUES, NOT AGAINST ITSELF. `route_totals` is the one source for
runewords/sets/uniques, each carrying his own ruling; a demonstration that re-derived them from
the same code it is testing would agree with itself and prove nothing. [[feedback-verify-not-proxy]]

★ AND IT NEVER WRITES. No seal, no ledger, no tombstone, no prune. It reads and it reports.

    python3 tv/reel_demo.py            # every reel, every station, and the downstream checks
    python3 tv/reel_demo.py --json
    python3 tv/reel_demo.py <reel>     # one reel, in full
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _check(name, got, want, why):
    ok = (got == want)
    return {"check": name, "ok": ok, "got": got, "want": want, "why": why}


def _shelf():
    """Is there a reel shelf on THIS host at all? -> (state, why). present | absent | broken.

    ⚠⚠ v2658 — A FALSE RED IS AS DISHONEST AS A FALSE GREEN, AND THIS GATE SHIPPED FOUR OF THEM.
    `tv/frames/` is gitignored (.gitignore:21) and `git ls-files tv/frames` measures 0, so a fresh
    actions/checkout has no footage at all. The two rows that need it — "the printer walked his
    shelf" and "the readers RECORD a stash tab at all" — therefore went RED on every CI push for a
    reason that has nothing whatever to do with the pipeline they exist to watch. Measured in the
    run at af8beac9: "0 reel(s) walked through 6 station(s); 10 of 12 downstream check(s) pass."
    Nor could it skip out of it: run_gates registers this gate with no `skip_ok=`, and an
    undeclared skip is counted a failure. UNKNOWN is the third state both rows were missing.
    [[unknown-stays-unknown]]

    ⚠⚠ AND IT ASKS ABOUT THE SHELF *PATH*, NOT THE PRINTER'S VERDICT. Keying this off
    `printer.stream()` coming back UNKNOWN would ALSO swallow the real defect — a shelf that EXISTS
    and walked nothing — which is the only thing "the printer walked his shelf" is for. The two
    states are indistinguishable downstream (printer.py returns rows=[] for both) and must be told
    apart HERE, at the one place that can still see the difference.

    ⚠ A recorder that will not IMPORT, or that names no shelf, is not an absent shelf; it is a
    broken one, and it stays a hard FAIL on every host.
    """
    try:
        import tv_diablo as TD
    except Exception as e:
        return "broken", "the recorder would not import (%s)" % str(e)[:70]
    # TD.HIST_DIR is the ONE hist root (tv_diablo.py:2299, TV_HIST-overridable). Read from the
    # owner rather than re-derived here, so the demo and the printer cannot disagree about where
    # the shelf is. [[copy-drift]]
    p = getattr(TD, "HIST_DIR", "")
    if not p:
        return "broken", "the recorder does not name a shelf at all"
    if not os.path.isdir(p):
        return "absent", ("no reel shelf exists on this host — the recorder names %r and it is "
                          "not a directory" % p)
    # ⚠⚠ #123 — A DIRECTORY IS NOT A SHELF, AND CI BUILDS THE DIRECTORY. machine_tree.establish()
    # creates every root and proves a write with a probe it then REMOVES, so any host that ran the
    # recorder has an empty tv/frames/hist. On CI an earlier gate does exactly that, this answered
    # "present", and a runner that never held a frame FAILED "the printer walked his shelf" — every
    # push, `0 reel(s) walked … ⚠ 1 check(s) DISAGREE`. EMPTY is the third venue: the directory
    # holds nothing and this host has no record of ever closing a reel. It is NOT empty — and the
    # walked-nothing defect above stays a FAIL — when the ledger names a closed reel (footage
    # WAS here) or cannot be read (nobody can say it never was). [[unknown-stays-unknown]]
    try:
        held = [n for n in os.listdir(p) if not n.startswith(".")]
    except OSError as e:
        return "broken", "the shelf %r exists and cannot be listed (%s)" % (p, type(e).__name__)
    if not held:
        closed, cwhy = _closed_reels_on_record()
        if closed == 0:
            return "empty", ("the shelf %r exists and holds nothing, and this host has no record "
                             "of ever closing a reel (%s) — an established tree nothing was filmed "
                             "into" % (p, cwhy))
        return "present", ("the shelf is empty and %s — an emptied shelf is not a venue without "
                           "footage" % cwhy)
    return "present", ""


def _closed_reels_on_record():
    """How many reels this host's tombstone ledger says were ever closed. -> (int | None, why)

    A ledger that does not exist is a host that never closed one: 0. A ledger that exists and will
    not read is None — UNKNOWN, never 0."""
    try:
        import reel_retention as RR
        path = RR._tombstone_path()
    except Exception as e:
        return None, "the tombstone ledger could not be located (%s)" % type(e).__name__
    try:
        with io.open(path, encoding="utf-8") as fh:
            blob = json.load(fh)
    except FileNotFoundError:
        return 0, "no tombstone ledger exists here"
    except Exception as e:
        return None, "the tombstone ledger exists and will not read (%s)" % type(e).__name__
    rows = blob.get("reels") if isinstance(blob, dict) else None
    if not isinstance(rows, list):
        return None, "the tombstone ledger carries no reel list"
    n = len([r for r in rows if isinstance(r, dict)])
    return n, ("the tombstone ledger names %d closed reel(s)" % n) if n else \
        "the tombstone ledger names no closed reel"



#: HIS TEMPLATE LIST, verbatim from 2026-09-04: *"stash/runes/gems each have their template..
#: also test those individually.. runes/gems/materials... then we have stash then we have
#: INVENTORY/STASH . then we have CHRONICLES which is mainmenu for UNIQUES and SETS"*.
#: Each maps to something the readers ALREADY record — a scene, or a stash tab.
TEMPLATES = (
    ("stash",      "scene", "the STASH panel is open — the one activity that can grant possession"),
    ("inventory",  "scene", "the INVENTORY is open. Held is not owned (v2346)"),
    ("chronicle",  "scene", "the CHRONICLE main menu — where UNIQUES and SETS are listed"),
    ("runes",      "tab",   "the RUNES tab of the stash"),
    ("gems",       "tab",   "the GEMS tab"),
    ("materials",  "tab",   "the MATERIALS tab"),
    ("personal",   "tab",   "the PERSONAL stash tab"),
    ("shared",     "tab",   "the SHARED stash tab"),
)


def _templates():
    """Each template he named, tested individually against what the readers know. -> [check]

    ⚠⚠ IT ASSERTS THE VOCABULARY, NOT THE COUNT. A check that required "at least one stash read"
    would go RED the day he prunes a stash reel — a gate failing for a non-defect, which teaches
    him to skip the row. What must hold is that every template he named is a thing the readers
    CAN recognise; how many of each his current shelf happens to hold is EVIDENCE, reported
    beside it. [[feedback-blind-fixture-green-gate]]
    """
    import os
    out = []
    try:
        import reel_segments as RS
        known_scenes = set(RS._ACTIVITY_LANE)
    except Exception as e:
        return [{"check": "reel_segments vocabulary", "ok": False, "got": str(e)[:60],
                 "want": "importable", "why": "the scene vocabulary could not be read"}]
    # what his shelf actually holds right now, per template
    live, live_why = {}, ""
    try:
        import control_app as CA
        import json as _j
        ring = [x for x in (CA._journal_ring() or []) if os.path.isfile(x)]
        # ⚠⚠ v2658 — REG-579's SIBLING, AND REG-579's COMMENT BELOW CLOSED ONLY THE *EXCEPTION*
        # BRANCH. An ABSENT journal does not raise: the `isfile` filter simply yields an empty
        # list, the loop body never runs, and `live` stays `{}` — the very failed-read-handed-back-
        # as-DATA shape the comment below was written about, surviving one line outside it. On a CI
        # runner it is the NORMAL state (tv/sessions.jsonl at .gitignore:24, tv/sessions.*.jsonl at
        # :31, both zero-tracked), so every push printed "NO TAB HAS EVER BEEN RECORDED" as though
        # somebody had looked at his nights and found none. Nobody could look.
        # [[unknown-stays-unknown]]
        if not ring:
            live, live_why = None, "no journal generation exists on this host"
        for path in ring:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        r = _j.loads(line)
                    except Exception:
                        continue
                    if r.get("lane") != "deep":
                        continue
                    sc = str(r.get("scene") or "").strip()
                    tb = str(r.get("stashTab") or "").strip()
                    if sc:
                        live[sc] = live.get(sc, 0) + 1
                    if tb:
                        live[tb] = live.get(tb, 0) + 1
    except Exception as _e:
        # ⚠⚠ REG-579 — THIS WAS `live = {}`, AND IT WAS MINE (v2580). An empty dict here says
        # "the shelf holds no sighting of this template", and a failed read says "nobody could
        # look". Downstream they are read identically — `live.get(name, 0)` returns 0 for both,
        # and every template would report `known · 0 read(s) on the shelf` as though that were a
        # measurement. Counted by the swallow census as RANK 1, *a failed read handed back as
        # DATA*, and it is exactly the class this repo has a skill about. [[unknown-stays-unknown]]
        #
        # `None` is the honest value: `live_unreadable` carries the reason, and the callers below
        # ask before they count.
        live, live_why = None, "the reel shelf could not be read (%s)" % str(_e)[:80]
    for name, kind, why in TEMPLATES:
        if kind == "scene":
            known = name in known_scenes
            where = "reel_segments._ACTIVITY_LANE"
            got = ("known · %s on the shelf"
                   % ("UNKNOWN — %s" % live_why if live is None
                      else "%d read(s)" % live.get(name, 0))) if known \
                  else "NOT RECOGNISED"
        else:
            # ⚠⚠ v2585 — THIS ASSERTED THE OPPOSITE OF WHAT ITS COMMENT CLAIMED, found by a cold
            # cross-family look. It said "assert the VOCABULARY, not the count" and the code was
            #     bool(live.get(name)) or bool([k for k in live if k in (...the five tabs...)])
            # which is a LIVE-DATA test with a proxy fallback. Reproduced: with only `personal`
            # on the shelf, runes AND gems AND materials all reported known=True on the strength
            # of a different tab — and with no tab data at all, `runes` reported NOT RECOGNISED
            # even though the reader may know the token perfectly well. Both directions wrong,
            # and a comment contradicting its code is v2565's scar again.
            #
            # The honest vocabulary question for a tab is asked ONCE, below: does the reader
            # RECORD stashTab at all? Whether this particular tab has been seen on the current
            # shelf is EVIDENCE, reported and never asserted — which is what the intent said.
            known = True
            where = "the deep rows' stashTab field (checked once, below)"
            seen = None if live is None else live.get(name, 0)
            # ⚠ v2658 — `if seen else` read None and 0 identically, so an UNREADABLE shelf printed
            # "0 on this shelf" as a measurement. Evidence lines lie as easily as asserted ones.
            got = ("UNKNOWN — %s" % live_why) if seen is None else \
                  ("%d read(s) on the shelf" % seen) if seen else \
                  "0 on this shelf — evidence, not a failure"
        # ⚠⚠ v2588 — AN EVIDENCE LINE MUST NOT WEAR A PASS. A cold review pointed out that every
        # tab line sets ok=True unconditionally, so a reader sees "runes ✅ 0 on this shelf" and
        # can reasonably read it as the runes template being healthy when no runes tab was ever
        # observed. Asserting the count would be the gate-fails-on-a-non-defect trap this was
        # written to avoid — so the line says out loud that it asserts nothing, and the one real
        # vocabulary assertion is the appended check below. [[unknown-stays-unknown]]
        _label = "template %-10s (%s)" % (name, kind)
        if kind != "scene":
            _label += " · evidence only"
        # ⚠⚠ v2590 — A SUFFIX IN THE NAME IS DOCUMENTATION, NOT A GUARD. The cold review was
        # right: `ok` was still True and anything that FILTERS OR COUNTS on `ok` — including this
        # file's own pass/fail tally — read an evidence line as a passed check. Renaming it could
        # not fix that. The row carries an explicit `evidence` flag now, and the verdict below
        # excludes those rows from the tally, so "17 of 17 checks pass" counts only things that
        # were actually asserted.
        out.append({"check": _label, "ok": bool(known), "evidence": (kind != "scene"),
                    "got": got, "want": "recognised by " + where, "why": why})
    # THE ONE REAL VOCABULARY CHECK FOR TABS: is the field carried at all? If the readers stopped
    # recording stashTab, every per-tab line above would go quietly to zero and none of them would
    # fail — which is exactly the silent-zero shape this repo keeps paying for.
    tabs_seen = (None if live is None else
                 [k for k in live if k in ("runes", "gems", "materials", "personal", "shared")])
    if tabs_seen is None:
        # ⚠⚠ v2658 — AND HANDING THIS ROW A `None` IS NOT ENOUGH ON ITS OWN, which is where the
        # first prescription for this bug stopped: `bool(None)` is still False and `got` still fell
        # through to the literal "NO TAB HAS EVER BEEN RECORDED", so the false zero and the red
        # check both survived. The row needs the explicit third state the SCENE rows above already
        # have. Not asserted, because a journal nobody can read says nothing either way — and a
        # gate that goes red for an absent host file teaches him to skip the row.
        out.append({"check": "the readers RECORD a stash tab at all", "ok": False, "unknown": True,
                    "got": "UNKNOWN — %s" % live_why,
                    "want": "at least one stashTab value in the journal",
                    "why": "nobody could look, so this is not a measurement of the readers"})
    else:
        out.append({"check": "the readers RECORD a stash tab at all", "ok": bool(tabs_seen),
                    "got": ("carried · tabs seen: %s" % ", ".join(sorted(tabs_seen))) if tabs_seen
                           else "NO TAB HAS EVER BEEN RECORDED",
                    "want": "at least one stashTab value in the journal",
                    "why": "without this every per-tab line above reads 0 and none of them fails"})
    return out


def _downstream():
    """The numbers that were REGISTERED before the pipeline was rebuilt. -> [check]"""
    out = []
    try:
        import route_totals as RT
        _pin = RT.file_pin() if hasattr(RT, "file_pin") else None
        _unique = _pin if isinstance(_pin, int) else None
        for kind, want in (("runeword", 99), ("set", 135), ("unique", _unique)):
            got = RT.total(kind) if hasattr(RT, "total") else None
            out.append(_check("route_totals.%s" % kind, got, want,
                              "his own ruling, and the one source every surface quotes"))
    except Exception as e:
        out.append({"check": "route_totals", "ok": False, "got": None, "want": "importable",
                    "why": "would not answer (%s)" % str(e)[:80]})
    # the three route sets must AGREE with that one source — the v2484 rule
    for mod, label in (("chronicle_routes", "chronicle"), ("fleet_routes", "fleet"),
                       ("roster_routes", "roster")):
        try:
            m = __import__(mod)
            r = m.report() if hasattr(m, "report") else (m.routes() if hasattr(m, "routes") else {})
            out.append({"check": "%s reports" % label, "ok": bool(r and r.get("ok", True)),
                        "got": (r or {}).get("state") or "ok", "want": "ok",
                        "why": "the route set still derives without raising"})
        except Exception as e:
            out.append({"check": "%s reports" % label, "ok": False, "got": str(e)[:60],
                        "want": "ok", "why": "the route set would not answer"})
    return out


def demo(reel=None):
    """Walk his real reels through the printer and check downstream. -> dict"""
    try:
        import printer as P
        rep = P.stream(reel)
    except Exception as e:
        return {"ok": False, "state": "UNKNOWN", "reels": [], "checks": [],
                "why": "the printer would not run (%s) — UNKNOWN, never 'the reels are fine'"
                       % str(e)[:90]}
    rows = rep.get("rows") or []
    stations = list(rep.get("stations") or ())
    reels, blanks = [], 0
    for r in rows:
        st = r.get("stations") or {}
        # every station must have ANSWERED — a station missing from a row reads as a reel that
        # did not need it, which is exactly what the printer's own shape law forbids
        missing = [s for s in stations if s not in st]
        unknown = [s for s in stations if str((st.get(s) or {}).get("say")) == "UNKNOWN"]
        if missing:
            blanks += 1
        reels.append({
            "reel": r.get("reel"),
            "in": (st.get("in") or {}).get("say"),
            "stage": (st.get("funnel") or {}).get("say"),
            "template": (st.get("template") or {}).get("template"),
            "zone": (st.get("template") or {}).get("say"),
            "worth": (st.get("template") or {}).get("worthReading"),
            "route": (st.get("route") or {}).get("say"),
            "extract": (st.get("extract") or {}).get("say"),
            "out": (st.get("out") or {}).get("say"),
            "missingStations": missing,
            "unknownStations": unknown,
        })
    shelf, shelf_why = _shelf()
    checks = _downstream() + _templates()
    if rows:
        checks.append(_check("every reel carries every station", blanks, 0,
                             "a station missing from a row reads as a reel that did not need it"))
    else:
        # ⚠ v2658 — WITH ZERO REELS THIS PASSED 0 == 0, examining nothing. A vacuous pass inflates
        # the tally line he reads and is the sample-mistaken-for-a-verdict shape. [[regression-guard]]
        checks.append({"check": "every reel carries every station", "ok": False, "unknown": True,
                       "got": "UNKNOWN — no reel walked, so no row could be inspected",
                       "want": 0, "why": "0 blanks out of 0 rows asserts nothing"})
    if not rows and shelf in ("absent", "empty"):
        # ⚠ NOT a FAIL and NOT a PASS — see _shelf(). On a host that HAS a shelf, or one whose
        # recorder is broken, this stays the hard assertion it has always been.
        #
        # ⚠⚠ AND IT NEEDS *BOTH* CONDITIONS. Measured 2026-09-05 while proving this fix: with
        # TV_HIST pointed at an empty scratch tree the printer STILL walked his 40 real reels,
        # because reel_retention.plan() defaults to a hardcoded `HERE/frames/hist` (:319) and does
        # not follow TV_HIST the way one_start_point does. So `_shelf()` can say "absent" on a run
        # that walked a shelf anyway. Rows on the table outrank the path probe: if reels walked,
        # the row is asserted, whatever the probe thinks.
        checks.append({"check": "the printer walked his shelf", "ok": False, "unknown": True,
                       "got": "UNKNOWN — %s" % shelf_why, "want": ">0",
                       "why": "there is no footage on this host, so nothing about the walk is "
                              "established either way"})
    else:
        checks.append({"check": "the printer walked his shelf", "ok": bool(rows),
                       "got": len(rows), "want": ">0",
                       "why": "zero reels would mean the demonstration proved nothing at all"})
    # ⚠ an EVIDENCE row is never counted as a passed check — it asserted nothing. Nor is an
    # UNKNOWN one: v2658 — a row nobody could look at must not be counted PASSED (it would be the
    # green that lies) and must not be counted FAILED (it would be the false red that made this
    # gate ship four consecutive CI reds). It is counted SEPARATELY, and said out loud below.
    asserted = [c for c in checks if not c.get("evidence") and not c.get("unknown")]
    unk = [c for c in checks if c.get("unknown")]
    bad = [c for c in asserted if not c["ok"]]
    # ⚠⚠ A RUN THAT WALKED NOTHING IS NOT A PASS — and the first cut of this fix made it one.
    # Separating UNKNOWN from FAILED was right and stopped four false REDS. But `ok = not bad`
    # then made a shelf-less venue return 0, so `run_gates` recorded a ✅ for a run whose own
    # output says `0 reel(s) walked through 6 station(s) … 3 UNKNOWN`. A false red got traded for
    # a false GREEN, which is the worse of the two: a red gets investigated, a green ships.
    # Caught by a same-family review of the pushed bytes, which named the inconsistency exactly —
    # `overlap_ratchet` in this SAME ship exits 77 for its unmeasurable venue, and this did not.
    # THE THIRD STATE, matching that one: the shelf is absent and nothing walked, so the gate
    # COULD NOT RUN. That is 77 — a declared skip, printed loudly, counted in "did not run",
    # never a tick. [[unknown-stays-unknown]] [[regression-guard]]
    _no_venue = (shelf in ("absent", "empty")) and not rows
    if _no_venue:
        return {
            "ok": False, "state": "SKIPPED",
            "venue": ("no-shelf" if shelf == "absent" else "empty-shelf"),
            "reels": reels, "checks": checks, "walked": 0,
            "stations": stations, "unknown": len(unk), "shelf": shelf,
            # ⚠ #123 — TWO LITERAL SENTENCES, NOT ONE `%s`: run_gates declares this skip by the text
            # it prints, and TestADeclaredSkipCanActuallyFire asks the SOURCE for that text. A
            # composed sentence cannot be found there, and the push was refused for it.
            "why": ("%s (%s), so nothing was walked and no downstream number was established — "
                    "%d check(s) UNKNOWN. This is a declared SKIP, not a pass and not a defect."
                    % ("his reel shelf is absent on this venue" if shelf == "absent" else
                       "his reel shelf is empty on this venue", shelf_why, len(unk))),
        }
    return {
        "ok": not bad, "state": ("PASS" if not bad else "FAIL"),
        "reels": reels, "checks": checks, "walked": len(rows),
        "stations": stations, "unknown": len(unk), "shelf": shelf,
        "why": ("%d reel(s) walked through %d station(s); %d of %d downstream check(s) pass%s. %s"
                % (len(rows), len(stations), len(asserted) - len(bad), len(asserted),
                   ("; %d UNKNOWN — nobody could look" % len(unk)) if unk else "",
                   ("Everything that could be checked still agrees."
                    if unk else "Everything registered before still agrees.") if not bad else
                   "⚠ %d check(s) DISAGREE with what was registered before." % len(bad))),
    }


def main(argv):
    reel = next((a for a in argv if not a.startswith("-")), None)
    r = demo(reel)
    if "--json" in argv:
        print(json.dumps(r, indent=2, sort_keys=True, default=str))
        return 0
    print("\nREEL DEMONSTRATION — his own footage, through the whole pipeline\n")
    if not r.get("reels") and not r["ok"]:
        print("  %s\n" % r["why"])
        # ⚠⚠ THE VENUE CHECK HAS TO BE HERE TOO, AND MY FIRST CUT PUT IT ONLY AT THE BOTTOM.
        # The no-shelf state has `reels: []` and `ok: False`, so it hits THIS early return and the
        # `return 77` at the end of this function was unreachable — the fix printed its new
        # "declared SKIP" sentence and still exited 1. Two return paths, one of them patched.
        # Caught by running it in a tracked-files-only export of the CI venue rather than by
        # reading the diff. [[the-unjoined-end]]
        # #123 — keyed on the ONE decision (demo() said SKIPPED), never on a venue spelling: the
        # empty-shelf venue arrived and exited 1 here while printing "a declared SKIP".
        return 77 if r.get("state") == "SKIPPED" else 1
    print("  %-30s %-9s %-11s %-9s %-11s %s" % ("reel", "door", "stage", "template", "extract", "worth"))
    for x in r["reels"][:60]:
        print("  %-30s %-9s %-11s %-9s %-11s %s" % (
            str(x["reel"])[-30:], str(x["in"])[:9], str(x["stage"])[:11],
            str(x["template"])[:9], str(x["extract"])[:11], x["worth"]))
    print("\n  DOWNSTREAM, against what was registered before:")
    for c in r["checks"]:
        # ⚠ v2658 — ⚪ is a THIRD GLYPH, not a dressed-up ❌. A row nobody could look at printed a
        # red cross for four CI runs, which is how an absent host file reads as a broken pipeline.
        glyph = "⚪" if c.get("unknown") else ("✅" if c["ok"] else "❌")
        print("    %s %-32s %s" % (glyph, c["check"], str(c["got"])[:46]))
        if c.get("unknown"):
            print("       could not establish: %s — %s" % (str(c["want"])[:40], str(c["why"])[:70]))
        elif not c["ok"]:
            print("       wanted: %s — %s" % (str(c["want"])[:44], str(c["why"])[:70]))
    print("\n  %s · %s\n" % (r["state"], r["why"]))
    # 77 = SKIP_EXIT, the same contract js_syntax_gate and overlap_ratchet use: "I could not
    # run", which run_gates counts in its did-not-run line and never as a tick.
    if r.get("state") == "SKIPPED":
        return 77
    return 0 if r["ok"] else 1


def shelf_here():
    """REG-2592 - heart2's PROOF_NEEDS_HOST probe for "reel-shelf". -> bool. Absent or empty is a venue with no footage;
    present and BROKEN both say yes, so a broken recorder is still judged (and fails) rather than excused."""
    return _shelf()[0] not in ("absent", "empty")


RED_PROOF = [
    {
        "why": "v2889 — the tamper changes one of the counts Konyo REGISTERED as his own rulings "
               "(runewords 99, sets 135 pieces, uniques the chronicle pin). "
               "_check compares got == want and main ends in `return 0 if r[\"ok\"] else 1`, so a "
               "single wrong number turns the gate red. That is the whole point of this gate: it "
               "walks his REAL reels through all six printer stations and holds the pipeline to "
               "numbers fixed before any of it changed. ⚠ It declares SKIP 77 with a named reason "
               "where the shelf is absent (CI has no footage), so this proof only runs where his "
               "reels are. [[regression-guard]]",
        "file": 'reel_demo.py',
        "find": 'for kind, want in (("runeword", 99), ("set", 135), ("unique", _unique)):',
        "replace": 'for kind, want in (("runeword", 98), ("set", 135), ("unique", _unique)):',
        "matches": 2, "needs": "reel-shelf",
    },
]

if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
