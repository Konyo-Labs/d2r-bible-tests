#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TEXT SITTING ON TEXT — the class the render gate cannot see.

⚠⚠ WHY THIS EXISTS. `render_check` measures whether an element is CLIPPED, OFF-SCREEN or COVERED.
None of those catches two labels drawn on top of each other: both are fully on screen, neither is
clipped, and the pixels are a mess. Measured 2026-09-04 at 375x800 — a width the render gate
already renders and reports as *"no clipping"*:

    375x800    36 painted text leaves    3 overlapping pairs
    901/1120/1440                          0 overlapping pairs

⚠⚠ THOSE NUMBERS ARE THE CORRECTED ONES, AND THE CORRECTION IS THE MOST IMPORTANT THING IN THIS
FILE. The first version counted BOUNDING RECTS and reported 24 at 375 and 2-3 at every desktop
width. It was wrong: `getBoundingClientRect()` returns geometry for content an ancestor has CLIPPED
AWAY, and this page has one — at 375px `#home-dash` is height 0 with scrollHeight 591 and
overflow:auto, so its entire subtree has rects while none of it is painted. **21 of the 24, and
every single desktop "overlap", were invisible.** I had already written the desktop ones up as a
finding — "a 246x29px collision on his widest view" — and that finding did not exist.

Elements are hit-tested now: `elementFromPoint` at the centre must return the element or something
inside it. What is not drawn cannot collide. [[feedback-verify-not-proxy]]

A cold cross-family look at the same PNG found it unprompted — *"'AI READS · LIVE' overlaps the
partial text 'appea here'… ':17772' and ':17771' colliding with 'MILLENIUM', 'heart', and
'AGENT'"* — and the gate had just called that width green. **He must not be the detector, and
today neither was the gate.** [[visual-regression-detector]]

⚠⚠ IT IS A RATCHET, NOT A PASS/FAIL, AND THAT IS DELIBERATE. There are 24 overlaps at 375px today.
A check that failed on all of them would be red from birth, and a gate that is red on arrival gets
switched off or re-baselined without being read — which is precisely how the swallow ratchet one
file over came to be cleared by `--write-baseline` instead of by fixing anything. So: the debt is
RECORDED per target per width, a RISE fails, and a FALL fails too until it is blessed deliberately.
An exact-match baseline has no slack for a new overlap to hide in.

⚠ 2 OVERLAPS AT 1120 ARE IN THE BASELINE AND ARE NOT ASSUMED HARMLESS. Nobody has read them yet.
They are debt, recorded as debt, and the ratchet stops them growing — calling them "fine" would be
a verdict nobody earned. [[unknown-stays-unknown]]

    python3 tv/overlap_ratchet.py              # measure and print
    python3 tv/overlap_ratchet.py --check      # grade against the baseline (the gate)
    python3 tv/overlap_ratchet.py --write-baseline
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

REPO = os.path.dirname(HERE)
BASELINE = os.path.join(REPO, "baseline", "overlap_baseline.json")

#: the widths this asks about. The narrow one is the point — layout dies at breakpoints. [[workflow-topology]]'s render
#: rule said include 375; v3889 (#132, his 11-08 "i dont need any mobile anything") overrules it here - 901 is the
#: narrowest width he uses a breakpoint near (tv/test_there_is_no_phone_page.py)
WIDTHS = ((901, 900), (1120, 900), (1440, 1000))

#: ⚠⚠ THE PANELS THIS WAS BLIND TO. Measured: the console has FIVE overlay panels and this gate
#: opened NONE of them — it graded the page as loaded, so a 0/0/0/0 baseline was a clean bill over
#: surfaces it had never seen. Two REAL overlaps sat on the heart panel because of it
#: (`_chron_autoread_loop` over `_drift_loop`, 66x9px, visible in a screenshot he sent).
#: Each entry is (panel id, the expression that opens it). `th-dossier-ov` is deliberately absent
#: and NAMED: it exports no opener, so it stays UNMEASURED rather than being counted as clean.
#: [[gate-blind-to-unexercised-input]] [[unknown-stays-unknown]]
PANELS = (
    ("heart-ov", "(function(){var c=document.getElementById('heart-chip'); if(c) c.click(); "
                 "return !!c;})()"),
    ("forensics-ov", "(function(){return !!(window._forensicsOpen && (window._forensicsOpen()||1));})()"),
    ("th-compare-ov", "(function(){return !!(window._cmpOpen && (window._cmpOpen()||1));})()"),
    ("th-heatmap-ov", "(function(){return !!(window._hmOpen && (window._hmOpen()||1));})()"),
)

#: THE VENUE HAS NO BROWSER — the one reason a run could not START, as opposed to a run that
#: started and then could not answer. Compared by IDENTITY (`is`) at the exit-code decision, never
#: by substring: a reason string matched with `in` is the [[source-reading-guard]] defect, and this
#: one decides whether a build fails.
#:
#: ⚠⚠ v2658 — THIS MODULE PRINTED "⚪ UNKNOWN" AND EXITED 1, AND THOSE TWO DISAGREED FOR ITS WHOLE
#: LIFE. `run_gates` maps exit 77 to SKIP and EVERY other non-zero to FAIL, so on a GitHub runner —
#: where `tv-tests.yml` installs no browser at all — this gate reported `❌ overlap_ratchet` with
#: the words *"Nothing was established, which is not the same as no overlaps"* sitting in its own
#: status column. It was counted among the 16 red gates while NINE sibling gates that print
#: `⚪ SKIPPED` were not counted, purely because they exit 77 and this one did not.
#: The contradiction was the finding: the module's message was right and its exit code was wrong.
#:
#: ⚠ THIS DOES NOT MAKE THE GATE PASS. A venue with no browser now reports a DECLARED SKIP, which
#: `run_gates` prints loudly and counts in its "did not run" line — never a tick. And a declared
#: skip that never becomes a real run is [[d2r-bible]] §8's "a gate that always skips is the same
#: defect as one that never runs", so the coverage gap is NAMED rather than closed: `tv-tests.yml`
#: needs the chromium install + `~/.cache/ms-playwright` cache that `publish.yml:97-117` already
#: has. Until then this gate measures on his Mac only, and says so on CI.
NO_BROWSER = "headless chrome would not start, so no width was measured"

#: v1601's contract, shared with tv/js_syntax_gate.py and run_gates.SKIP_EXIT: "I could not run",
#: which is not "I passed" and not "I failed".
SKIP_EXIT = 77
#: REG-3064 - a browser INSTALLED that would not start: the venue could not measure (must match render_check.VENUE_EXIT
#: and run_gates.VENUE_EXIT; run_gates reads it with the mark as VENUE)
VENUE_EXIT, VENUE_MARK = 3, "VENUE FAULT"


def _unmeasured_exit(why):
    """REG-3064 - the exit for a run that measured nothing, by WHY. -> SKIP_EXIT (no browser here, declared), VENUE_EXIT
    (installed and would not start: UNKNOWN, never a red), or 1 (the browser answered and the run still failed)"""
    if why is NO_BROWSER:
        return SKIP_EXIT
    return VENUE_EXIT if VENUE_MARK in str(why or "") else 1

#: panels that exist and cannot be opened from here, so their overlap count is UNKNOWN and must
#: never be folded into a total as a zero.
UNREACHABLE_PANELS = ("th-dossier-ov",)

#: (width-key, panel) pairs that are structurally UNMEASURABLE — the panel exists but does not
#: populate at that width, so its overlap count is a reading of an empty box.
#:
#: ⚠⚠ v2730 — THIS FILE ALREADY SAID SO IN PROSE AND NOTHING ENFORCED IT. The baseline's own
#: `_panels` note reads: "heart-ov at 375 carries only 3 leaves — it does not populate at that
#: width, so its 0 is NOT evidence of anything and must not be read as clean." That warning was
#: written into the very file whose numbers I then quoted, and I reported "375 fully recovered,
#: 2 -> 0" three times on the strength of a 0 measured over THREE text leaves against the 32-43
#: a populated panel carries. A note nobody can act on is a note nobody acts on.
#: [[zero-needs-a-denominator]] [[measured-true-read-wrong]]
UNMEASURABLE_AT = {
    ("375x800", "heart-ov"): "the heart panel does not populate at 375 — 3 text leaves against "
                             "the 32-43 a rendered panel carries, so any count here is a reading "
                             "of an empty box, not a clean one",
}


def _unmeasurable(key):
    """-> reason, or None. `key` is like '375x800 heart-ov'."""
    parts = str(key).split(" ", 1)
    if len(parts) != 2:
        return None
    return UNMEASURABLE_AT.get((parts[0], parts[1]))

#: minimum overlap in BOTH axes before two boxes count as colliding. A 1-2px kiss is antialiasing
#: and letter-spacing, not two labels on top of each other; measured, 3px removes those without
#: hiding any of the 24 real ones at 375.
MIN_OVERLAP_PX = 3

_JS = """(() => {
  // ⚠⚠ HIT-TESTED, NOT JUST MEASURED. getBoundingClientRect() reports geometry for content an
  // ancestor has CLIPPED away — and this page has one: at 375px #home-dash is height 0 with
  // scrollHeight 591 and overflow:auto, so its whole subtree has rects while none of it is
  // painted. Counting those produced overlaps that are invisible on the pixels, which is a gate
  // reporting damage nobody can see. elementFromPoint at the centre answers what is ACTUALLY on
  // top there; if neither the element nor a descendant of it is, it is not drawn and cannot
  // collide with anything. [[feedback-verify-not-proxy]]
  // ⚠⚠ REG-1872 — CLIPPED AWAY IS NOT DRAWN, AND THE HIT-TEST BELOW COULD NOT TELL. It accepts an
  // ANCESTOR at the centre (`hit.contains(e)`), and text an overflow box has clipped away has an
  // ancestor under its centre: MEASURED at 1440x1000, `.tzz-terr` "-> 96 terrorized" at y 971-999
  // sits wholly below #home-dash's bottom edge (929, overflow:auto), the point lands on .shell, and
  // the gate reported it 4px over the footer's "not taken" (957-976) — a collision with nothing on
  // the pixels. GrokBot read the same phantom as "PRIME · Bloodraven country" over the footer.
  // So every box is first cut to what its clipping ancestors leave visible: a box cut to nothing is
  // not painted, and a box cut short collides only with what is left of it.
  const clipOf = e => {
    let l = -Infinity, t = -Infinity, r = Infinity, b = Infinity;
    for (let p = e.parentElement; p; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (cs.overflowX === 'visible' && cs.overflowY === 'visible') continue;
      const q = p.getBoundingClientRect();
      l = Math.max(l, q.left); t = Math.max(t, q.top); r = Math.min(r, q.right); b = Math.min(b, q.bottom);
    }
    return [l, t, r, b];
  };
  const cutTo = (r, c) => ({left: Math.max(r.left, c[0]), top: Math.max(r.top, c[1]),
                           right: Math.min(r.right, c[2]), bottom: Math.min(r.bottom, c[3])});
  const some = r => r.right - r.left > 0 && r.bottom - r.top > 0;
  const painted = (e, r0) => {
    const r = cutTo(r0, clipOf(e));
    if (!some(r)) return false;
    const x = (r.left + r.right) / 2, y = (r.top + r.bottom) / 2;
    if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) return false;
    const hit = document.elementFromPoint(x, y);
    return !!hit && (hit === e || e.contains(hit) || hit.contains(e));
  };
  const leaves = [...document.querySelectorAll('*')].filter(e => {
    const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    return e.children.length === 0 && (e.textContent || '').trim()
           && r.width > 4 && r.height > 4
           && cs.visibility !== 'hidden' && cs.display !== 'none' && cs.opacity !== '0'
           && r.top < innerHeight && r.bottom > 0
           && painted(e, r);
  });
  // ⚠⚠ PER-LINE BOXES, NOT THE UNION RECT — AND THIS FILE HAS NOW BEEN WRONG ABOUT RECTS TWICE.
  // getBoundingClientRect() on an INLINE element returns the union of every line box it occupies,
  // so a wrapped inline beside a sibling reports an overlap where not one pixel touches. Measured
  // on his forensics panel: `<b>0 chronicle misses</b>` sits at [94..261] and the wrapped
  // `.fxr-sub` sits at [612..1207] on its first line and [94..173] on its SECOND, a line below.
  // The union starts at x=94 and swallows the <b>. I reported that as a real overlap and then
  // refuted it by asking for the line boxes.
  // ⚠ THE HIT-TEST CANNOT CATCH THIS. It asks what is painted at the rect's CENTRE, and the union
  // rect's centre lands on the element's own text — so the phantom passes the very check added to
  // stop phantoms. getClientRects() is the only honest answer for inline content.
  // ⚠ VERIFIED BASELINE-NEUTRAL BEFORE SHIPPING: per-line and bounding-rect both give 0 overlaps
  // at 375/901/1120/1440 on the page this already grades. It removes phantoms and nothing else.
  const boxes = leaves.map(e => { const c = clipOf(e); return [...e.getClientRects()].map(b => cutTo(b, c)).filter(some); });
  const pairs = [];
  for (let i = 0; i < leaves.length; i++) {
    for (let j = i + 1; j < leaves.length; j++) {
      let hit = null;
      for (const a of boxes[i]) {
        for (const b of boxes[j]) {
          const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
          const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
          if (ox > __MIN__ && oy > __MIN__) { hit = {ox: Math.round(ox), oy: Math.round(oy)}; break; }
        }
        if (hit) break;
      }
      if (hit) {
        pairs.push({a: (leaves[i].textContent || '').trim().slice(0, 26),
                    b: (leaves[j].textContent || '').trim().slice(0, 26),
                    ox: hit.ox, oy: hit.oy});
      }
    }
  }
  return {leaves: leaves.length, count: pairs.length, sample: pairs.slice(0, 8)};
})()"""


#: the same arithmetic, scoped to ONE overlay panel. Kept as its own expression rather than
#: parameterising `_JS`, because the page-level version deliberately walks `document` and a panel
#: must walk only its own subtree — conflating them would let a panel's rows collide with the page
#: behind it and report an overlap that is really a stacking order.
_PANEL_JS = _JS.replace("document.querySelectorAll('*')",
                        "(document.getElementById('__ID__') || document)"
                        ".querySelectorAll('*')")


def measure(page=None, widths=WIDTHS):
    """-> ({("%dx%d" % w): {...}}, why). `why` non-empty means NOTHING was established."""
    import time
    try:
        import render_check as RC
    except Exception as e:
        return None, "render_check would not import (%s)" % str(e)[:70]
    if not RC._chrome_up():
        # ⚠⚠ TWO DIFFERENT FACTS, AND v2658 COLLAPSED THEM INTO ONE — caught by a cross-family
        # review of the pushed bytes, reproduced here before being believed.
        # `_chrome_up()` answers False for BOTH "this machine has no Chrome" (a venue fact, and
        # the only thing a declared skip may forgive) and "Chrome is installed and would not
        # start" (a real fault on a venue that is supposed to measure). Returning NO_BROWSER for
        # both meant a launch FLAKE ON HIS MAC — where Chrome demonstrably exists — became a
        # declared skip instead of a red, on the one venue this gate actually measures.
        # That is the same "two facts under one word" defect the module's own UNKNOWN handling
        # exists to prevent, reintroduced one level up. [[unknown-stays-unknown]]
        # It also narrows what `skip_ok` can forgive: run_gates matches the reason as a SUBSTRING,
        # so the message that reaches it must be true of the absent case ONLY.
        if not os.path.exists(RC.CHROME):
            return None, NO_BROWSER
        return None, ("%s — a venue that is supposed to measure could not, which is not a venue without a browser "
                      "(REG-3064)" % RC.no_browser_say()[1])
    # ⚠⚠ SERVED, NOT file:// — AND THE FIRST CUT OF THE PANEL WORK PROVED WHY. Under file:// the
    # console's panels cannot reach /api/…, so they render almost nothing: measured, forensics came
    # back with FIVE text leaves where a served page gives THIRTY-NINE, and every panel reported a
    # confident 0 overlaps. That is worse than not opening them at all, because the gate then shows
    # apparent coverage over surfaces it never really saw — the exact shape of the blindness this
    # change exists to remove. render_check learned the same thing and grew `_serve_console` for it.
    # [[feedback-blind-fixture-green-gate]] [[gate-blind-to-unexercised-input]]
    srv = None
    if page:
        url = "file://" + page
    else:
        try:
            origin, srv = RC._serve_console()
            url = origin
        except Exception as e:
            return None, ("the console would not serve (%s), so the overlay panels could not be "
                          "populated — and measuring them unserved would report a clean 0 over "
                          "empty panels" % str(e)[:70])
    out = {}
    try:
        tab = RC._Tab(url)
    except Exception as e:
        return None, "could not open the page (%s)" % str(e)[:70]
    for w, h in widths:
        try:
            tab.send("Emulation.setDeviceMetricsOverride", width=w, height=h,
                     deviceScaleFactor=1, mobile=False)
            # ⚠ RELOAD AT EACH WIDTH. Measuring four widths in sequence on one tab grades 1440 on
            # a layout that has just been squeezed to 375 and back: scroll position persists,
            # anything that collapsed stays collapsed, and a resize reflow is not a first paint.
            # Each width is now graded as a user opening AT that width sees it.
            #
            # ⚠⚠ AND THE HONEST FOOTNOTE, because the tempting version of this comment is wrong:
            # THIS CHANGED NOTHING. Measured both ways — 2 / 3 / 24 / 3, identical, and identical
            # across three consecutive sequenced runs before that. I added the reload suspecting
            # the sequenced numbers were an artifact and they were not. It stays because grading a
            # first paint is the right thing to measure, NOT because it fixed a defect, and
            # writing it up as a fix would have put a discovery in the log that never happened.
            # [[feedback-suspect-the-instrument]]
            tab.send("Page.navigate", url=url)
            time.sleep(2.5)
            r = tab.send("Runtime.evaluate",
                         expression=_JS.replace("__MIN__", str(MIN_OVERLAP_PX)),
                         returnByValue=True)
            v = (r.get("result") or {}).get("value")
            if not isinstance(v, dict):
                return None, "the page returned no measurement at %dx%d" % (w, h)
            out["%dx%d" % (w, h)] = v
            # ⚠⚠ AND THE PANELS, WHICH THIS GATE HAS NEVER ONCE OPENED. Everything above measures
            # the page AS LOADED, so five overlay surfaces were outside its reach and a 0/0/0/0
            # baseline read as a clean bill over them. Two REAL overlaps sat on the heart panel
            # because of it. A panel is measured as its OWN key so a regression names the surface
            # rather than moving a page total nobody can locate.
            # ⚠ A panel that REFUSES TO OPEN is recorded as such and is NOT counted as zero — an
            # unopened panel is unmeasured, and folding it in as clean is the exact thing this
            # whole change is fixing. [[unknown-stays-unknown]]
            for pid, opener in PANELS:
                try:
                    tab.send("Runtime.evaluate", expression=opener, returnByValue=True)
                    pv = None
                    # A packed machine paints the panel after the first look. Ask again
                    # before recording "not measured". A panel that never answers stays unmeasured.
                    for _attempt in range(5):
                        time.sleep(1.6 if _attempt == 0 else 0.8)
                        pr = tab.send("Runtime.evaluate", returnByValue=True,
                                      expression=_PANEL_JS.replace("__MIN__", str(MIN_OVERLAP_PX))
                                                          .replace("__ID__", pid))
                        pv = (pr.get("result") or {}).get("value")
                        _count = pv.get("count") if isinstance(pv, dict) else None
                        if isinstance(_count, int) and not isinstance(_count, bool):
                            break
                    if isinstance(pv, dict):
                        out["%dx%d %s" % (w, h, pid)] = pv
                    else:
                        out["%dx%d %s" % (w, h, pid)] = {
                            "count": None, "leaves": None, "sample": [],
                            "why": "the panel returned no measurement"}
                    tab.send("Runtime.evaluate", returnByValue=True,
                             expression="(function(){var o=document.getElementById(%r);"
                                        "if(o) o.hidden=true; return 1;})()" % pid)
                    time.sleep(0.3)
                except Exception as pe:
                    out["%dx%d %s" % (w, h, pid)] = {
                        "count": None, "leaves": None, "sample": [],
                        "why": "could not be asked (%s)" % str(pe)[:60]}
        except Exception as e:
            # ⚠ ONE WIDTH THAT COULD NOT BE ASKED MAKES THE WHOLE RUN UNKNOWN. A partial run
            # graded against a full baseline would read every unmeasured width as zero.
            return None, "%dx%d could not be measured (%s)" % (w, h, str(e)[:60])
    finally_note = None
    if srv is not None:
        try:
            srv.terminate()
        except Exception:
            finally_note = "the private console server did not stop cleanly"
    return out, (finally_note or "")


def _venue():
    """WHERE a set of counts was measured. -> str

    Font rasterisation is the whole reason this exists. The same page measures differently on
    macOS and on a Linux runner — this repo has the number: a tab strip that is 1223px on his
    machine measures 750px under Playwright's metrics. Overlap counts are a DIRECT function of
    text advance widths, so a baseline from one venue cannot grade the other.
    """
    import platform
    return platform.system() or "unknown"


def _baseline():
    try:
        with io.open(BASELINE, encoding="utf-8") as fh:
            return json.load(fh) or {}, ""
    except FileNotFoundError:
        return None, "no baseline at %s — this gate is UNCONFIGURED, not clean" % BASELINE
    except Exception as e:
        return None, "the baseline would not parse (%s) — refusing to grade against it" % e


def _venue_matches(was):
    """(ok, why) — may this baseline grade a run taken HERE?

    ⚠⚠ v2659 — WRITTEN BEFORE THE FALSE RED, NOT AFTER IT. The same ship that gave CI a browser
    made this gate able to RUN there for the first time, against a baseline measured entirely on
    his Mac. `check()` fails on ANY difference — `if now != then`, a fall as loudly as a rise — so
    the first green CI run with Chromium would have compared Linux font metrics against macOS ones
    and called the difference a defect.
    That is the false red this module's own docstring fears most: it says an exact-match ratchet
    that fires every run "teaches him to skip it", which is the same defect as a gate that is red
    on arrival. A red pointing at nothing trains everyone to ignore the next real one.

    ⚠ SO IT REFUSES RATHER THAN GRADES. A cross-venue comparison is not a lenient verdict or a
    strict one; it is NOT A VERDICT, and UNKNOWN is the honest answer. [[unknown-stays-unknown]]
    ⚠ A baseline with NO venue stamp is every baseline written before today. That is UNKNOWN too —
    it must not be assumed to have come from here, because assuming is exactly how a cross-venue
    comparison would sneak back in wearing a clean face.
    """
    if not isinstance(was, dict):
        return False, "the baseline is not a record"
    stamped = was.get("_venue")
    here = _venue()
    if not stamped:
        return False, ("this baseline carries no venue stamp, so nobody can say which platform's "
                       "font metrics produced it — and overlap counts are a direct function of "
                       "text advance widths. Re-bless it here with --write-baseline")
    if stamped != here:
        return False, ("the baseline was measured on %s and this run is on %s. Overlap counts "
                       "follow font rasterisation, so comparing them is not a strict verdict or a "
                       "lenient one — it is not a verdict at all" % (stamped, here))
    return True, ""


#: keys whose count differs between two consecutive measurements are recorded as `None` — UNSTABLE
#: — and are reported rather than graded. ⚠⚠ MEASURED, NOT ASSUMED: serving the console revealed
#: 17 real overlaps, and re-running immediately gave 1120: 7 -> 5 and 901: 6 -> 7. The bottom
#: AI-READS strip carries LIVE data, so its text length changes between runs and the overlap count
#: moves on its own. An exact-match ratchet over that fires every run and teaches him to skip it —
#: which is this module's own stated fear about gates that are red on arrival. A surface that
#: cannot be measured twice the same way is not a surface that can be ratcheted, and saying so is
#: the honest answer rather than inventing slack. [[unknown-stays-unknown]]
#: ⚠⚠ ITS OWN SENTINEL, NOT `None` — AND HIS EXISTING SUITE CAUGHT ME COLLAPSING THEM. The first
#: cut wrote `None` for an unstable key, and `None` already meant MALFORMED BASELINE ("this key has
#: no recorded count, which is not a count of zero"). `test_a_MALFORMED_count_is_not_read_as_zero`
#: went red immediately: a corrupt baseline started reporting as a deliberate design decision.
#: Two meanings on one value is the collapse this repo keeps finding, and the guard was already
#: standing here waiting for it. [[unknown-stays-unknown]]
UNSTABLE = "UNSTABLE"


def _is_panel_key(k):
    """A measurement of ONE overlay panel, rather than the whole page. -> bool

    Panel keys carry the panel id after the width ("901x900 heart-ov"). They are the surfaces this
    gate grades, because they hold no live ticker and measured 0 on every run.
    """
    return any(k.endswith(" " + pid) for pid, _ in PANELS)


def _twice():
    """Measure twice and mark anything that moved as UNSTABLE. -> (counts, samples, why)"""
    a, why_a = measure()
    if a is None:
        return None, None, why_a
    b, why_b = measure()
    if b is None:
        return None, None, why_b
    counts, samples = {}, {}
    for k in sorted(set(list(a) + list(b))):
        va, vb = (a.get(k) or {}).get("count"), (b.get(k) or {}).get("count")
        # ⚠⚠ PAGE-LEVEL IS OBSERVATION, NEVER A GRADE — AND TWO AGREEING RUNS DID NOT PROVE IT
        # STABLE. Measured across four consecutive runs at 1120x900: 7, 5, 8, 5. The first cut
        # here graded any key that matched twice, and 1120 matched twice and then moved anyway.
        # The bottom AI-READS strip carries LIVE text, so its length — and therefore the overlap
        # count — changes on its own. A ratchet over that is red for reasons nobody caused, and
        # this module's own doctrine says a gate red on arrival gets switched off rather than read.
        # The PANELS are the gradeable surface: every panel key measured 0 on every run.
        # ⚠⚠ v2730 — TWO AGREEING COUNTS OVER TWO DIFFERENT PANELS IS NOT AGREEMENT.
        # This compared only the overlap COUNT. Measured 2026-09-06 at 375x800, two consecutive
        # runs seconds apart:
        #       run 1:  0 overlap(s)  across  3 text leaves
        #       run 2:  1 overlap(s)  across 32 text leaves
        # Three leaves against thirty-two: the first run measured a panel that had not finished
        # laying out. A count taken over almost nothing is not a low count, it is an UNMEASURED
        # one — and if BOTH runs catch the panel half-rendered they both read 0, they AGREE, and
        # this function blesses the pair as stable. I reported "375 fully recovered, 2 -> 0" three
        # times on exactly that reading.
        #
        # So the DENOMINATOR has to agree too. `leaves` was already measured and already printed
        # (`%d overlap(s) across %d text leaf/leaves`) and then discarded — the number that would
        # have caught this was on screen the whole time.
        # [[zero-needs-a-denominator]] [[feedback-suspect-the-instrument]]
        if _unmeasurable(k):
            # structurally unmeasurable at this width — never graded, and SAID so rather than
            # silently dropped, because an absent row reads as a clean one
            counts[k] = UNSTABLE
            samples[k] = (a.get(k) or {}).get("sample") or []
            continue
        la = (a.get(k) or {}).get("leaves")
        lb = (b.get(k) or {}).get("leaves")
        _same_panel = (la is not None and lb is not None and la == lb)
        if _is_panel_key(k):
            counts[k] = va if (va is not None and va == vb and _same_panel) else UNSTABLE
        else:
            counts[k] = UNSTABLE
        # keep the denominator beside the verdict so a reader can see what it was measured over
        samples.setdefault("_leaves", {})[k] = (la, lb)
        samples[k] = (a.get(k) or {}).get("sample") or []
    return counts, samples, ""


def write_baseline():
    counts, samples, why = _twice()
    if counts is None:
        print("🔴 %s" % why)
        return 1
    got = {k: {"count": counts[k], "leaves": None, "sample": samples.get(k) or []} for k in counts}
    os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
    with io.open(BASELINE, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            # ⚠ THE VENUE, FIRST. Overlap counts follow font rasterisation, so a baseline that
            # does not say which platform produced it cannot honestly grade any run — see
            # _venue_matches. Written on every bless so the refusal above has something to read.
            "_venue": _venue(),
            "_why": "TEXT-ON-TEXT overlaps per width, and per overlay PANEL. A rise FAILS; a "
                    "fall also fails until it is blessed here deliberately, so there is no slack "
                    "for a new overlap to hide in. These are DEBT, not a clean bill: nobody has "
                    "read them.",
            "_v2625": "⚠⚠ THE NUMBERS IN THIS FILE JUMPED FROM 0/0/0/0 AND NOTHING GOT WORSE. "
                      "Until v2625 this gate loaded control_ui.html over file://, where the "
                      "console cannot reach /api/… and renders almost nothing — measured, the "
                      "forensics panel showed FIVE text leaves against THIRTY-NINE on a served "
                      "page. So the old baseline was a clean bill over a console that never "
                      "loaded its data. Serving it revealed 17 overlaps that were always there: "
                      "0 at 375, 6 at 901, 5 at 1120, 6 at 1440, all in the bottom AI-READS strip "
                      "('act 5' over 'live guess' by 92x19px at 1440). NOT A REGRESSION — a gate "
                      "that finally looked. They are recorded as debt so they cannot grow while "
                      "someone reads them.",
            "_panels": "The four overlay panels measure 0 at every width and that is a REAL "
                       "reading now, on a served page with 32-43 text leaves each. ⚠ heart-ov at "
                       "375 carries only 3 leaves — it does not populate at that width, so its 0 "
                       "is NOT evidence of anything and must not be read as clean. th-dossier-ov "
                       "exports no opener and stays unmeasured on purpose.",
            "counts": {k: v["count"] for k, v in sorted(got.items())}}, indent=2, sort_keys=True))
        fh.write("\n")
    print("wrote %s" % BASELINE)
    for k, v in sorted(got.items()):
        # ⚠⚠ THE SENTINEL IS A STRING, NOT None, AND THIS LINE ASSUMED OTHERWISE. An unstable key
        # is stored as the literal "UNSTABLE" (its own sentinel — the module docstring says so
        # explicitly, because `None` already means MALFORMED BASELINE). This branch tested only
        # `is None`, so any unstable key fell through to `"%d" % "UNSTABLE"` and raised
        # TypeError — AFTER the file was already written. `--write-baseline` therefore exited 1
        # on a run that had SUCCEEDED, and a caller reading that status would conclude the bless
        # failed and re-run it. Found by reading a non-zero exit that a green `--check` right
        # after it would otherwise have explained away. [[exit-status-of-the-block]]
        # ⚠ `isinstance(True, int)` is True in Python, and THIS REPO HAS BEEN BITTEN BY THAT
        # EXACT THING: REG-600's disk rows carried `prunedMb: true` and it was read as a number,
        # producing "2 MB of that was freed" out of two booleans. A bool is not a count here
        # either, so it falls to the sentinel branch rather than printing as 1 overlap.
        _c = v["count"]
        _n = isinstance(_c, int) and not isinstance(_c, bool)
        print("   %-24s %s" % (k, "UNSTABLE — moved between two runs, reported not graded"
                               if not _n else "%d overlap(s)" % _c))
    return 0


def check():
    was, why = _baseline()
    if was is None:
        print("🔴 %s" % why)
        print("   run:  python3 tv/overlap_ratchet.py --write-baseline")
        return 1
    # ⚠ BEFORE MEASURING ANYTHING — a cross-venue comparison is not a verdict, so there is no
    # point spending a browser launch to produce one. Declared as a SKIP (77) so run_gates counts
    # it in "did not run" and never as a tick; the reason names both venues so the fix is obvious.
    _vok, _vwhy = _venue_matches(was)
    if not _vok:
        # ⚠ ONE LINE, AND IT CARRIES THE DECLARED PHRASE. `run_gates` reads a gate's skip reason
        # as the LAST NON-BLANK LINE it printed, so splitting this across two prints would leave
        # the matched phrase on the first and hand the gate a reason its `skip_ok` does not cover
        # — an UNDECLARED skip, which :2025 counts as a build FAILURE. I wrote it as two prints
        # first and caught it before shipping; it is the same unjoined end this gate already
        # carries a scar for. [[the-unjoined-end]]
        print("⚪ UNKNOWN — baseline venue mismatch: %s. Nothing was established, which is not the "
              "same as no overlaps." % _vwhy)
        return SKIP_EXIT
    got, mwhy = measure()
    if got is None:
        # ⚠ UNKNOWN IS NOT A PASS. Nothing was measured, so nothing may be reported clean.
        print("⚪ UNKNOWN — %s. Nothing was established, which is not the same as no overlaps."
              % mwhy)
        # ⚠ …AND UNKNOWN IS NOT A DEFECT EITHER. Which of the two this is depends entirely on
        # WHY nothing was measured, and only one of the reasons is about the page:
        #   · the venue has no browser  -> the gate COULD NOT RUN -> 77, a declared skip
        #   · anything else             -> the browser answered and the run still failed -> 1
        # Identity, not substring — see NO_BROWSER.
        return _unmeasured_exit(mwhy)
    old = was.get("counts") or {}
    print("text-on-text overlap ratchet")
    bad = []
    for k in sorted(set(list(old) + list(got))):
        now = (got.get(k) or {}).get("count")
        then = old.get(k)
        # ⚠⚠ v2730 — STRUCTURALLY UNMEASURABLE IS NOT A NUMBER, AND check() GRADED IT ANYWAY.
        # `_twice()` learned to skip these, but check() calls measure() DIRECTLY, so the guard only
        # protected the baseline writer and never the verdict — the two halves of one rule, joined
        # at one end. heart-ov at 375 kept being graded on a count taken over 3 text leaves.
        # SAID, never silently dropped: a row that vanishes from the list reads as a clean one.
        _un = _unmeasurable(k)
        if _un:
            print("   %-26s ⚪ NOT GRADED — %s (read %s)" % (k, _un, now))
            continue
        if now is None:
            bad.append("%s was in the baseline and was NOT measured" % k)
            continue
        if then == UNSTABLE:
            # ⚠ DECLARED UNSTABLE, not missing. This key moved between two consecutive measurements
            # when the baseline was written, so it is REPORTED and never graded — grading a number
            # that changes on its own produces a gate that is red for reasons nobody caused.
            print("   %-24s UNSTABLE by measurement · now %s (not graded)" % (k, now))
            continue
        if not isinstance(then, int):
            bad.append("%s has no recorded baseline (%r) — MALFORMED, not a count of zero"
                       % (k, then))
            continue
        flag = "" if now == then else ("  🔴 ROSE +%d" % (now - then) if now > then
                                       else "  🟡 fell -%d" % (then - now))
        print("   %-10s baseline %-3d now %-3d%s" % (k, then, now, flag))
        if now != then:
            bad.append("%s: %d -> %d" % (k, then, now))
            for pr in (got.get(k) or {}).get("sample") or []:
                print("        %r over %r  (%dx%d px)" % (pr["a"], pr["b"], pr["ox"], pr["oy"]))
    if bad:
        print()
        print("🔴 the overlap count moved: %s" % "; ".join(bad))
        print("   A RISE is new text drawn on top of other text — no clipping check can see it.")
        print("   A FALL is good and still fails, so the win is recorded rather than absorbed:")
        print("       python3 tv/overlap_ratchet.py --write-baseline")
        return 1
    print("✅ held.")
    return 0


def main(argv):
    if "--write-baseline" in argv:
        return write_baseline()
    if "--check" in argv:
        return check()
    got, why = measure()
    if got is None:
        print("⚪ UNKNOWN — %s" % why)
        return _unmeasured_exit(why)
    print("\nTEXT-ON-TEXT OVERLAPS — the class a clipping check cannot see\n")
    for k, v in sorted(got.items()):
        print("  %-10s %3d overlap(s)   across %d text leaf/leaves" % (k, v["count"], v["leaves"]))
        for pr in (v.get("sample") or [])[:3]:
            print("       %r over %r  (%dx%d px)" % (pr["a"], pr["b"], pr["ox"], pr["oy"]))
    print()
    return 0


def venue_here():
    """REG-2592 - heart2's PROOF_NEEDS_HOST probe for "overlap-venue": was the baseline measured on this platform?
    -> bool. Only a baseline STAMPED with another platform says no. A missing, unparseable, non-record or unstamped
    baseline says yes: that is a broken gate (it refuses everywhere, his Mac too), judged and red where it runs - never
    ELSEWHERE on every host, where nobody would ever prove it (second eye, REG-2592)."""
    was, _why = _baseline()
    if not isinstance(was, dict) or not was.get("_venue"):
        return True
    return _venue_matches(was)[0]


RED_PROOF = [
    {
        'why': 'The gate is `python3 tv/overlap_ratchet.py --check` (run_gates.py:3086) and the SOURCE it protects is the console it serves and measures: tv/control_ui.html. Only the four overlay-panel keys are actually graded — every page-level width is recorded UNSTABLE by measurement and `375x800 heart-ov` is declared structurally unmeasurable — and of those panels only #forensics-ov populates enough to hold a collision (28 painted text leaves at 901 against 3/2/2 for heart, compare and heatmap). So the honest place to attack this gate is a real spacing law inside the forensics panel. `.fx-secsub { … margin: -2px 0 8px 16px; }` (control_ui.html:1355) IS that law: the -2px is the tuned pull that seats each section\'s subtitle immediately under its section header, and it is real CSS — not a comment, not a mention inside a message string, and not a constant an agreement law reads from both sides (nothing else in the file or in overlap_ratchet.py reads it). Moving it to -13px pulls the subtitle 11px up onto the header line, which is exactly the defect class this gate exists for and the one render_check cannot see: nothing is clipped, nothing is off-screen, nothing is covered — two labels are simply drawn on top of each other. ⚠⚠ THE 11px IS MEASURED, NOT PICKED, AND A BIGGER SHIFT WOULD HAVE READ GREEN. `_JS` hit-tests every leaf with elementFromPoint at its centre, so once the subtitle\'s box swallows the header\'s centre y the header stops being a painted leaf, the pair disappears and the count falls back to 0 — a sabotage that looks violent and proves nothing. The header span is 15px tall (y=196..211, centre 203.5) and the subtitle 15px (y=217..232), so the usable window is a shift of >9px (to clear the 3px MIN_OVERLAP_PX threshold) and <13.5px (to keep the header\'s centre outside the subtitle\'s box). -13px sits in the middle of it and the measured pairs came back at oy=5 and oy=4 against a threshold of 3, with `leaves` unchanged at 28. ⚠ The gate measures on his Mac only — on a venue with no browser it exits 77 and on a non-Darwin baseline venue it declares a skip — so this proof was measured where the gate actually runs. MEASURED: untampered GREEN (exit 0, `✅ held.`); tampered RED (exit 1) at ALL FOUR widths — forensics-ov 0->6 / 0->6 / 0->6 / 0->5; law reddened = check()\'s `if now != then` ratchet comparison; ALONE a fresh process calling only `overlap_ratchet.check()` returned 1 with the same rise; RESTORED with `git checkout -- tv/control_ui.html` and the gate printed `✅ held.` again. matches=1, counted in tv/control_ui.html (not estimated) — the string is unique, so heart2\'s replace-all and a single replacement are the same experiment. `file` is the bare basename: heart2 joins it onto the sandbox tv/, giving <sandbox>/tv/control_ui.html, which exists.  MEASURED: untampered GREEN. `python3 tv/overlap_ratchet.py --check` -> exit 0, last line `✅ held.` Al; tampered (all 1) RED. Same command, exit 1. `901x900 forensics-ov baseline 0 now 6 🔴 ROSE +6`, an; reddened law check()\'s ratchet comparison in tv/overlap_ratchet.py — `if now != the; ALONE FAILS ALONE. The gate is a SCRIPT, not a unittest suite, so "alone" was a fresh python3 process that.',
        'file': 'control_ui.html',
        'find': 'margin: -2px 0 8px 16px;',
        'replace': 'margin: -13px 0 8px 16px;',
        'matches': 1, 'needs': 'overlap-venue',
    },
]


if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
