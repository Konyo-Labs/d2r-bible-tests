# -*- coding: utf-8 -*-
"""THE RIVER, MADE VISIBLE AS THE FOUR LANES HE NAMED.

Konyo: *"the visual rendering of it i want it replicating a simple · INTAKE where the reels come
and get stationed · PRINTER where they get filtered · CAPTURE where they get extracted.. and
finally TOMBSTONE... first in first out FIFO.. that way its optimzed."*

And the constraint that shapes every line of this: *"now dont get me wrong. the backend should be
pinpoint perfect and nothing fabricated what so ever.. just the visual rendering of the backend."*

So `river_lanes` DECIDES NOTHING. `reel_router.route()` decides; this groups its answer.

MEASURED on his shelf the day this shipped (40 reels, reconciles true):

    INTAKE       7   INTAKE:0 + TRIAGE:0 + STATION:7 + EMPTY:0
    PRINTER     11   PRINTER:11
    CAPTURE     16   CAPTURE:12 + JOIN:4
    TOMBSTONE    6   ROUTED:6  + TOMBSTONE:0
    TOTAL       40   = shelf

⚠ TOMBSTONE HOLDS 6 ONLY BECAUSE v2764 UNWELDED ROUTED FROM THE DELETER. Before that the last lane
could never hold anything — the only writer of a tombstone row lived inside the deleter, behind the
arming lock, so "finished" and "deleted" were one event and the lane was a labelled empty box.

=== ⚠⚠ THE DEFECT THAT COST THE MOST, AND IT WAS A NAME ===
The strip was first called `_shRiverRender` / `_shRiverLoad`. **`_shRiverLoad` ALREADY EXISTED** at
the bottom of control_ui.html — the SHELF_RIVER card-grouping feature. Two function declarations
with one name in one scope: the later wins, silently. The whole strip was unreachable while every
piece of it measured correct — the container rendered, the export was on `window`, the fetch fired
and returned 200 with a good payload, and NO ERROR WAS THROWN ANYWHERE. The placeholder simply
never changed.

It survived four rounds of probing because a second bug hid it: the could-not-ask branch first
rendered the SAME words as the loading placeholder, so a permanent failure and an unfinished load
were indistinguishable. Both are fixed. It was found only by printing
`window._shRiverLoad.toString()` in the page and reading back a function I had not written.

`test_no_new_duplicate_function_name` is the general guard that would have caught it in one second.
[[the-unjoined-end]] [[zero-needs-a-denominator]]
"""
import io
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

import reel_router as RR  # noqa: E402
import river_lanes as RL  # noqa: E402

UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
APP = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()

#: function names already declared more than once when this guard was written. Both are NESTED
#: helpers living inside different parents (measured: `close` at 7962/10332, `ensure` at
#: 7936/7963/8011, all at indent 4), so they are separate scopes and not collisions.
KNOWN_DUPES = {"close", "ensure"}


def _render(payload):
    """Run the SHIPPED _shLanesRender in node. -> str|None"""
    # ⚠ 2026-09-28 — THE CUT STARTS AT THE TRIAGE LANE'S HELPERS (they sit directly above the renderer, which now draws
    # the lane's one line on every path), and the fake element answers `querySelector` + `localStorage` as the renderer
    # asks since v2987's fold. Without both, node died on the first line and _render returned None — so 7 of this law's
    # 15 cases SKIPPED on every venue, reading as a pass (the same harness gap test_a_reels_whole_life_is_one_work_list
    # already named and fixed for itself). A skip is not a pass. [[regression-guard]]
    i = UI.find("  var _TRIAGE_WORDS = {")
    if i < 0 or i > UI.find("  function _shLanesRender(d){"):
        i = UI.find("  function _shLanesRender(d){")
    j = UI.find("  window._shLanesRender = _shLanesRender;", i)
    if i < 0 or j < 0:
        raise AssertionError("REG-1900 - the subject this harness drives is gone (_shLanesRender): a renamed subject is a FAILURE, never a skip")
    js = ("var out = '';\n"
          "var _fold = { open: false, addEventListener: function(){} };\n"
          "var localStorage = { setItem: function(){}, getItem: function(){ return null; } };\n"
          "var window = {};\n"
          "var document = { getElementById: function(){ return { set innerHTML(v){ out = v; },"
          " get innerHTML(){ return out; },"
          " querySelector: function(sel){ return sel === '.shr-fold' ? _fold : null; } }; } };\n"
          "var esc = function(s){ return String(s === undefined ? '' : s)"
          ".replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/\"/g,'&quot;'); };\n"
          + UI[i:j] + "\n"
          "_shLanesRender(" + json.dumps(payload) + ");\n"
          "console.log(JSON.stringify(out));")
    p = os.path.join(os.environ.get("TMPDIR", "/tmp"), "lanes_probe.js")
    io.open(p, "w", encoding="utf-8").write(js)
    try:
        r = subprocess.run(["node", p], capture_output=True, text=True, timeout=90)
    except FileNotFoundError:
        return None          # REG-1900 - the ONE skip: there is no node on this venue
    if r.returncode != 0:    # the subject would not run: that is the subject's failure, not the venue's
        raise AssertionError("REG-1900 - the shipped code would not run in node: %s" % (r.stderr or "")[-400:])
    return json.loads((r.stdout or "").strip().split("\n")[-1])


class TheShelfShowsTheFourLanes(unittest.TestCase):

    # ── ⚠⚠ THE BACKEND IS THE AUTHORITY ─────────────────────────────────────────────────────
    def test_the_lane_map_PARTITIONS_the_routers_stations(self):
        """★ Every station in exactly one lane. A station added upstream and not mapped here just
        STOPS APPEARING on his shelf: the lanes still add up among themselves, the page still
        renders, and reels quietly leave the picture. That is `reel_story`'s exact defect."""
        ok, findings = RL.assert_partitions()
        self.assertTrue(ok, "the lane map no longer partitions reel_router.STATIONS: %r" % findings)
        mapped = set()
        for _n, sts, _w in RL.LANES:
            mapped |= set(sts)
        self.assertEqual(set(RR.STATIONS), mapped,
                         "the lane map and the router's station list have diverged")

    def test_the_partition_proof_actually_proves_a_partition(self):
        """★ RAISED BY THE SECOND EYE on v2769: the guard called itself a partition proof and did
        not test the property. A station repeated INSIDE ONE lane's tuple leaves len(seen[st]) at
        1, so nothing objected — while that lane's byStation would count it twice and the lanes
        would out-total the shelf. An empty tuple makes a lane that can never hold anything; a
        duplicate lane NAME makes two boxes a reader cannot tell apart."""
        real = RL.LANES
        for bad, what in (
                ((("A", ("STATION", "STATION"), "x"),), "a station repeated inside one lane"),
                ((("A", (), "x"),), "a lane covering no stations"),
                ((("A", ("STATION",), "x"), ("A", ("PRINTER",), "y")), "two lanes with one name")):
            RL.LANES = bad
            try:
                ok, findings = RL.assert_partitions()
            finally:
                RL.LANES = real
            self.assertFalse(ok, "%s was accepted as a partition" % what)
            self.assertTrue(findings, "%s produced no finding to act on" % what)

    def test_an_ORPHANED_station_is_NAMED_not_just_counted(self):
        """★ RAISED BY THE SECOND EYE: a reel at a station no lane covers is dropped from every
        lane and from the total, so `reconciles` goes false and the reader gets a bare mismatch
        with nothing to act on. The station name IS the finding — it says which upstream change
        orphaned them. [[zero-needs-a-denominator]]"""
        rep = RR.route()
        if not rep.get("ok") or not rep.get("reels"):
            self.skipTest("no shelf here to orphan a reel from — a skip is NOT a pass")
        import copy
        fake = copy.deepcopy(rep)
        fake["reels"][0]["station"] = "NEWSTATION"
        out = RL.lanes(fake)
        self.assertTrue(out["ok"])
        self.assertFalse(out["reconciles"], "a reel left every lane and the totals still agreed")
        self.assertIn("NEWSTATION", out["why"],
                      "the orphaned station is not named, so the reader is handed a count with no "
                      "way to find what fell out")
        self.assertIn("NEWSTATION", out.get("orphanStations") or [])

    def test_it_DECIDES_nothing_and_calls_the_router(self):
        """★ Proven by SUBSTITUTION. If this computed a station of its own, the stub could not
        change what it reports — and the console would show a river the backend does not have,
        which is the one thing he ruled out."""
        seen = {"n": 0}
        real = RR.route

        def counting(*a, **k):
            seen["n"] += 1
            return real(*a, **k)
        RR.route = counting
        try:
            RL.lanes()
        finally:
            RR.route = real
        self.assertEqual(1, seen["n"], "river_lanes never asked the router")

    def test_a_BROKEN_map_refuses_to_draw(self):
        """⚠ Four tidy lanes over a broken map is worse than none — it looks complete while reels
        leave the frame. [[unknown-stays-unknown]]"""
        real = RL.LANES
        RL.LANES = (("ONLY", ("STATION",), "a map that covers almost nothing"),)
        try:
            rep = RL.lanes()
        finally:
            RL.LANES = real
        self.assertFalse(rep["ok"], "a map covering 1 of 9 stations still drew a river")
        self.assertIn("partition", rep["why"])

    def test_an_UNREADABLE_router_is_a_refusal_not_an_empty_river(self):
        real = RR.route
        RR.route = lambda hist=None: {"ok": False, "why": "simulated"}
        try:
            rep = RL.lanes()
        finally:
            RR.route = real
        self.assertFalse(rep["ok"])
        self.assertIn("not a report that the river is empty", rep["why"])

    def test_FIFO_is_inherited_never_re_sorted(self):
        """His word: *"first in first out FIFO"*. `route()` already orders oldest-first and puts
        reels with NO clock LAST — None must not become 0, which is 1970. A second sort here would
        be a second copy of that rule, free to drift. [[copy-drift]]"""
        src = io.open(os.path.join(HERE, "river_lanes.py"), encoding="utf-8").read()
        self.assertNotIn(".sort(", src, "river_lanes re-sorts instead of inheriting the router's order")
        rep = RL.lanes()
        if rep["ok"]:
            for ln in rep["lanes"]:
                ms = [r["capturedMs"] for r in ln["reels"] if r.get("capturedMs") is not None]
                self.assertEqual(sorted(ms), ms, "lane %s is not oldest-first" % ln["name"])

    def test_the_lanes_RECONCILE_with_the_shelf(self):
        rep = RL.lanes()
        if not rep["ok"]:
            self.skipTest("the router did not answer here — a skip is NOT a pass")
        total = sum(l["count"] for l in rep["lanes"])
        self.assertEqual(rep["shelf"], total + rep["unknown"],
                         "the lanes hold %d of %d reels — the view is losing some"
                         % (total, rep["shelf"]))
        self.assertTrue(rep["reconciles"])

    # ── ⚠ THE WIRE ──────────────────────────────────────────────────────────────────────────
    def test_the_endpoint_carries_the_lanes(self):
        i = APP.find('if path == "/api/river":')
        self.assertGreater(i, 0, "the river route is gone")
        blk = APP[i:APP.find('\n        if path ', i + 10)]
        self.assertIn("river_lanes", blk, "/api/river does not carry the lanes")
        self.assertIn('"lanes": _lanes', blk)
        self.assertIn('"ok": False', blk,
                      "a lane refusal does not travel as a refusal, so a renderer would draw it "
                      "as four zeroes")

    # ── ⚠⚠ THE RENDERER, AGAINST THE REAL FUNCTION ──────────────────────────────────────────
    def test_it_draws_four_lanes_in_river_order(self):
        got = _render({"lanes": {"ok": True, "reconciles": True, "shelf": 40, "unknown": 0,
                                 "lanes": [{"name": n, "why": w, "stations": list(s),
                                            "count": 3, "byStation": {x: 1 for x in s}}
                                           for n, s, w in RL.LANES]}})
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        for name, _s, _w in RL.LANES:
            self.assertIn(name, got, "the %s lane is not drawn" % name)
        self.assertEqual(3, got.count("shr-arrow"),
                         "the lanes do not read as a waterfall — %d connectors for 4 lanes"
                         % got.count("shr-arrow"))
        self.assertIn("FIFO", got, "nothing says the order is oldest-first")
        # ⚠ 2026-09-28 — BY THE LANE HEADERS, NOT THE FIRST OCCURRENCE OF A WORD. This case SKIPPED on every venue since
        # v2987's fold (the harness could not satisfy `el.querySelector`); un-skipped, `got.index("TOMBSTONE")` found the
        # word in the fold's own title ("why TOMBSTONE reads zero") at 123, before any lane was drawn. The order that
        # matters is the lanes' own numbered headers. [[source-reading-guard]] §2
        heads = [got.find('class="shr-n"><u>%d</u> %s</div>' % (k + 1, n)) for k, (n, _s, _w) in enumerate(RL.LANES)]
        self.assertTrue(all(x >= 0 for x in heads), "a lane header is not drawn in its place: %s" % heads)
        self.assertEqual(heads, sorted(heads), "the lanes are not in river order: %s" % heads)

    def test_a_REFUSAL_does_not_render_as_four_zeroes(self):
        got = _render({"lanes": {"ok": False, "why": "the lane map is broken"}})
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        self.assertNotIn("shr-lane", got, "a refusal still drew lanes")
        self.assertIn("could not be drawn", got)
        self.assertIn("the lane map is broken", got, "the refusal does not carry its reason")

    def test_a_walk_still_in_progress_stays_reading(self):
        """The route answers {computing:true} before the walk finishes. That is not a refusal.
        Painting it as could-not-be-read stops the shelf on the first packet."""
        got = _render({"ok": False, "computing": True,
                       "why": "the river walk has not finished in this process yet"})
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        self.assertNotIn("could not be read", got)
        self.assertNotIn("shr-bad", got)
        self.assertIn("reading the river", got)
        self.assertIn("shr-wait", got)
        self.assertNotIn("shr-lane", got)

    def test_both_readers_ask_again_while_the_walk_runs(self):
        """The product shelf asks once. render_check's poll is not that shelf. A computing
        answer has to schedule the next ask in both readers, or the strip stays on the first packet."""
        code = re.sub(r"/\*(?:.|\n)*?\*/", " ", UI)
        code = re.sub(r"(?m)//.*$", " ", code)
        for fn in ("async function _shLanesLoad()", "function _shRiverLoad(then){"):
            i = code.find(fn)
            self.assertGreater(i, -1, fn)
            d, j = 0, code.index("{", i)
            end = j
            while end < len(code):
                if code[end] == "{":
                    d += 1
                elif code[end] == "}":
                    d -= 1
                    if d == 0:
                        break
                end += 1
            body = code[i:end + 1]
            k = body.find("computing === true")
            self.assertGreater(k, -1, fn)
            tail = body[k:k + 700]
            self.assertIn("_RIVER_WALK_WAIT_MS", tail, fn)
            self.assertIn("setTimeout", tail, "%s does not ask again while the walk runs" % fn)

    def test_a_COULD_NOT_ASK_does_not_wear_the_placeholders_words(self):
        """★★ THE BUG THAT HID THE COLLISION FOR FOUR ROUNDS. This branch first rendered "reading
        the river…" — the exact text the container ships with — so a permanent failure and a page
        that had simply not finished loading were the same pixels. [[zero-needs-a-denominator]]"""
        got = _render(None)
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        self.assertNotIn("reading the river", got,
                         "a failed ask renders the loading placeholder's words, so UNKNOWN and "
                         "not-yet-loaded are indistinguishable on his screen")
        self.assertIn("UNKNOWN", got)

    def test_a_zero_TOMBSTONE_carries_its_denominator(self):
        """⚠ TOMBSTONE:0 does NOT mean nothing ever finishes — a released reel LEAVES the shelf,
        and the ledger holds 410 of them. A bare 0 there would read as a dead river."""
        got = _render({"lanes": {"ok": True, "reconciles": True, "shelf": 40, "unknown": 0,
                                 "lanes": [{"name": n, "why": w, "stations": list(s), "count": 1,
                                            "byStation": {x: (0 if x == "TOMBSTONE" else 1) for x in s}}
                                           for n, s, w in RL.LANES]}})
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        self.assertIn("leaves the shelf", got,
                      "TOMBSTONE reads 0 with nothing explaining it, so the last lane looks dead")

    def test_a_disagreement_is_SHOUTED_not_swallowed(self):
        got = _render({"lanes": {"ok": True, "reconciles": False, "shelf": 40, "unknown": 0,
                                 "lanes": [{"name": n, "why": w, "stations": list(s), "count": 1,
                                            "byStation": {x: 1 for x in s}} for n, s, w in RL.LANES]}})
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        self.assertIn("shr-warn", got,
                      "the lanes and the shelf disagree and nothing on screen says so")

    # ── ⚠⚠ THE GENERAL GUARD THE COLLISION EARNED ───────────────────────────────────────────
    def test_no_new_duplicate_function_name(self):
        """★★ THE ONE THAT WOULD HAVE SAVED FOUR ROUNDS OF PROBING. `_shRiverLoad` was declared
        twice in one scope; the later declaration won, silently, and an entire feature was
        unreachable while every piece of it measured correct and nothing threw.

        ⚠ IT IS A RATCHET, NOT A BAN, because two duplicates predate it and are legitimate:
        `close` and `ensure` are NESTED helpers inside different parents (measured at indent 4,
        clustered at 7936/7962/7963/8011/10332), so they occupy separate scopes. Anything NEW
        must be justified or renamed.
        """
        blocks = [(m.start(), UI.index("</script>", m.start()))
                  for m in re.finditer(r"<script[^>]*>", UI)]
        self.assertTrue(blocks, "no script blocks found — this guard inspected nothing")
        import collections
        dupes = {}
        for a, b in blocks:
            names = re.findall(r"(?:^|\n)\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(",
                               UI[a:b])
            for k, v in collections.Counter(names).items():
                if v > 1:
                    dupes[k] = v
        new = {k: v for k, v in dupes.items() if k not in KNOWN_DUPES}
        self.assertEqual({}, new,
                         "these function names are declared more than once in one script block: "
                         "%r. In one scope the LATER declaration wins SILENTLY — the earlier "
                         "function becomes unreachable while every piece of it still looks "
                         "correct, nothing throws, and no error is logged. Rename, or add to "
                         "KNOWN_DUPES with the measurement showing the scopes are separate." % new)



RED_PROOF = [
    {
        'why': 'waving the partition check through lets a lane map that loses reels draw four tidy lanes; test_a_BROKEN_map_refuses_to_draw must go red',
        'file': 'river_lanes.py',
        'find': '    ok, findings = assert_partitions()',
        'replace': '    ok, findings = True, []',
        'matches': 1,
    },
    {
        'why': 'a walk still running is painted as a dead river, so the shelf stops on the first packet',
        'file': 'control_ui.html',
        'find': '    if (d && d.computing === true && !d.lanes) {\n      el.innerHTML = \'<div class="shr-wait">reading the river… the walk has not finished</div>\';\n',
        'replace': '    if (false) {\n      el.innerHTML = \'<div class="shr-wait">reading the river… the walk has not finished</div>\';\n',
        'matches': 1,
    },
    {
        'why': 'the lane strip never asks again, so a computing answer stays on screen after the walk finishes',
        'file': 'control_ui.html',
        'find': '          setTimeout(function(){ try { window._shLanesLoad(); } catch (eR) {} }, 1000);\n',
        'replace': '          void 0;\n',
        'matches': 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
