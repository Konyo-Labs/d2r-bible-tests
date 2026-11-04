# -*- coding: utf-8 -*-
"""#36 — A REEL'S WHOLE LIFE IS ONE WORK-LIST, AND THE FAR STATION IS REACHABLE.

MEASURED 2026-09-09 against his real stores. Every source feeding `reel_router.route()` walks what
is CURRENTLY ON DISK. The moment `reel_retention.apply_plan()` removes a reel's directory that reel
is written into `tv/reel_tombstones.json` and vanishes from every list the printer/router chain
touches:

    live per-reel work-list           41
    closure ledger                   428   (all distinct — ZERO overlap with the 41)
    one roster spanning a life       469
    covered by the per-reel surfaces  41/469 = 8.7%   |  invisible: 428/469 = 91.3%

Consequence, in the module's own words: `reel_router.STATIONS` declares TOMBSTONE, **no code path
in `_station_of()` or `route()` ever assigned it**, `counts["TOMBSTONE"]` was structurally always 0,
and `route()["unreached"]` named it EVERY RUN — the system reporting its own gap to nobody. So
`river_lanes`' TOMBSTONE lane, labelled *"closed out — the extraction contract is satisfied"*, could
only ever display ROUTED-but-still-on-disk reels. It could never show a reel that had actually
closed out, which is its entire purpose. [[label-outlived-referent]] [[plumbing-with-no-tap]]

★ WHAT THIS FILE HOLDS, AND WHAT IT DELIBERATELY DOES NOT.
It holds `roster()` to assigning TOMBSTONE, to refusing to invent a total over a half-read union,
and to counting a reel in BOTH records exactly ONCE. It also holds the join to `route()` NOT moving
— `shelf` still means "on disk" and still reconciles — because the fix he must not get is one where
41 quietly becomes 469 on a figure he reads. [[zero-needs-a-denominator]]

⚠ EVERY CASE HERE IS A FIXTURE. `roster(rep=...)` takes an already-walked report and the ledger path
is redirected through `reel_retention._tombstone_path`, so this runs on any machine and never reads
his footage — Heart 2.0 calls a law it cannot re-run in a sandbox UNPROVABLE, and a gate that only
runs on his Mac is one nobody can defeat on purpose. [[feedback-fixtures-never-touch-live-data]]
"""
import io
import json
import os
import tempfile
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import reel_router as RR  # noqa: E402


def _rep(*reels):
    """A minimal successful route() report. Only the keys roster() reads."""
    return {"ok": True, "reels": list(reels), "shelf": len(reels), "counts": {}, "unknown": 0,
            "why": ""}


def _live(name, station="STATION", ms=None):
    return {"reel": name, "station": station, "why": "fixture", "owes": None,
            "capturedMs": ms, "clockFrom": "fixture", "sealed": True, "names": 3,
            "worthReading": True, "surveyedAt": None}


class _Ledger(object):
    """Point reel_retention's own path authority at a fixture, and put it back."""

    def __init__(self, blob):
        self.blob = blob

    def __enter__(self):
        import tempfile
        import reel_retention as _rr
        self._rr = _rr
        self._old = _rr._tombstone_path
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        if self.blob is None:
            os.unlink(self.path)          # ABSENT is a third state, not an empty one
        else:
            io.open(self.path, "w", encoding="utf-8").write(
                json.dumps(self.blob, ensure_ascii=False))
        _rr._tombstone_path = lambda *a, **k: self.path
        return self

    def __exit__(self, *exc):
        self._rr._tombstone_path = self._old
        try:
            os.unlink(self.path)
        except OSError:
            pass
        return False


def _closed(name, session=None, started=None, deleted=1000):
    return {"reel": name, "session": session or name.replace("reel_", ""), "mb": 1.0,
            "pages": 0, "frames": 4, "focus": None, "why": "fixture closure",
            "deletedTs": deleted, "startedTs": started}


class TheFarStationIsReachable(unittest.TestCase):

    def test_a_closed_reel_is_assigned_the_tombstone_station(self):
        """The whole point. Before this, `TOMBSTONE` was a declared word nothing could produce."""
        with _Ledger({"reels": [_closed("reel_gone_a"), _closed("reel_gone_b")]}):
            r = RR.roster(rep=_rep(_live("reel_here")))
        self.assertTrue(r["ok"], r.get("why"))
        st = [x["station"] for x in r["rows"] if x["reel"].startswith("reel_gone")]
        self.assertEqual(["TOMBSTONE", "TOMBSTONE"], sorted(st),
                         "a closed reel did not land at TOMBSTONE, so the station is STILL "
                         "unreachable and the lane still cannot show what its label promises")
        self.assertEqual(2, r["counts"].get("TOMBSTONE"),
                         "the roster's own counts do not carry the far station")

    def test_the_far_station_is_no_longer_named_unreached(self):
        """`unreached_stations` is the module's own self-report and it must agree with reality."""
        self.assertNotIn("TOMBSTONE", RR.unreached_stations({}, 428),
                         "the router still calls TOMBSTONE unreached while the ledger holds 428")
        self.assertIn("TOMBSTONE", RR.unreached_stations({}, 0),
                       "a genuinely empty ledger must still say the station is unreached — "
                       "silencing a real emptiness trades one lie for another")

    def test_the_roster_spans_both_halves_and_names_each_denominator(self):
        with _Ledger({"reels": [_closed("reel_g1"), _closed("reel_g2"), _closed("reel_g3")]}):
            r = RR.roster(rep=_rep(_live("reel_a"), _live("reel_b")))
        self.assertEqual(2, r["onDisk"])
        self.assertEqual(3, r["closed"])
        self.assertEqual(5, r["lifetime"])
        self.assertEqual(5, len(r["rows"]))
        self.assertTrue(r["reconciles"], "the union does not reconcile against its own total")


class TheNumbersHeReadsDoNotMove(unittest.TestCase):

    def test_route_shelf_is_not_widened_by_the_join(self):
        """★ 41 must not silently become 469. `roster()` is asked for by name or not at all."""
        import ast
        src = io.open(os.path.join(HERE, "reel_router.py"), encoding="utf-8").read()
        tree = ast.parse(src)
        fn = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "route"]
        self.assertEqual(1, len(fn), "route() is not a single top-level function any more")
        called = {n.func.id for n in ast.walk(fn[0])
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertNotIn("_closed_rows", called,
                         "route() now reads the closure ledger's ROWS — if those rows reach "
                         "`reels`, `shelf` moves from 'on disk' to 'ever existed' and a number "
                         "he acts on has changed meaning with nothing on screen saying so")
        self.assertNotIn("roster", called, "route() calls roster() — that is a cycle, and it is "
                                           "also how the walk would acquire 428 extra rows")

    def test_the_ledger_has_exactly_one_reader(self):
        """Two readers of one ledger is how three walks came to agree at 41 by luck."""
        import ast
        src = io.open(os.path.join(HERE, "reel_router.py"), encoding="utf-8").read()
        opens = 0
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id == "open":
                opens += 1
        self.assertEqual(1, opens,
                         "reel_router opens a file in %d places; the closure ledger must have "
                         "exactly ONE reader (`_closed_rows`) that everything else asks."
                         % opens)


class AnUnreadableLedgerIsUnknown(unittest.TestCase):

    def test_an_unreadable_ledger_is_never_a_confident_zero(self):
        with _Ledger("this is not json at all"):
            r = RR.roster(rep=_rep(_live("reel_a")))
        self.assertFalse(r["ok"])
        self.assertIsNone(r["closed"], "an unreadable ledger reported a NUMBER of closures")
        self.assertIsNone(r["lifetime"], "a lifetime total was computed over a half-read union")
        self.assertFalse(r["closedReadable"])
        self.assertIn("UNKNOWN", r["why"],
                      "the report does not say the total is unknown: %r" % r["why"][:120])
        self.assertEqual(1, len(r["rows"]),
                         "the half that WAS readable was thrown away — a partial answer is still "
                         "worth returning, it just may not claim to be whole")

    def test_an_absent_ledger_is_zero_and_says_so(self):
        """ABSENT and UNREADABLE are different facts. Only one of them is good news."""
        with _Ledger(None):
            r = RR.roster(rep=_rep(_live("reel_a")))
        self.assertTrue(r["ok"])
        self.assertEqual(0, r["closed"])
        self.assertEqual(1, r["lifetime"])

    def test_an_unknown_walk_does_not_become_an_empty_shelf(self):
        with _Ledger({"reels": [_closed("reel_g1")]}):
            r = RR.roster(rep={"ok": False, "why": "the printer would not answer", "reels": []})
        self.assertFalse(r["ok"])
        self.assertIsNone(r["onDisk"], "an unwalkable shelf reported a COUNT of reels on disk")
        self.assertIsNone(r["lifetime"])


class AReelInBothRecordsIsCountedOnce(unittest.TestCase):

    def test_a_contradiction_appears_once_and_is_named(self):
        """Zero overlap today is LUCK — nothing enforces it, which is what opened #36."""
        with _Ledger({"reels": [_closed("reel_dup"), _closed("reel_gone")]}):
            r = RR.roster(rep=_rep(_live("reel_dup"), _live("reel_b")))
        names = [x["reel"] for x in r["rows"]]
        self.assertEqual(1, names.count("reel_dup"),
                         "a reel in BOTH records appears %d times — the lifetime total is "
                         "inflated by a contradiction" % names.count("reel_dup"))
        self.assertEqual(["reel_dup"], r["both"], "the contradiction is not named")
        dup = [x for x in r["rows"] if x["reel"] == "reel_dup"][0]
        self.assertTrue(dup.get("onDisk"), "the live row lost to the ledger row")
        self.assertTrue(dup.get("alsoClosed"), "the contradiction is invisible on the row itself")

    def test_the_ledgers_two_key_conventions_both_match(self):
        """The ledger has keyed by reel dir name AND by bare session id across versions."""
        with _Ledger({"reels": [{"session": "s_9", "mb": 1.0, "why": "x", "deletedTs": 1}]}):
            r = RR.roster(rep=_rep(_live("reel_s_9")))
        self.assertEqual(["reel_s_9"], r["both"],
                         "a session-keyed ledger row did not match its live reel, so the same "
                         "reel would be counted twice under two spellings")


class FifoIsOneRuleAppliedOnce(unittest.TestCase):

    def test_a_reel_with_no_clock_sorts_last_not_first(self):
        """None must not become 0 — 0 is 1970 and puts every unmeasured reel at the head."""
        with _Ledger({"reels": [_closed("reel_noclock", started=None),
                                _closed("reel_old", started=10)]}):
            r = RR.roster(rep=_rep(_live("reel_new", ms=99)))
        self.assertEqual(["reel_old", "reel_new", "reel_noclock"],
                         [x["reel"] for x in r["rows"]],
                         "the union is not in the router's one FIFO order")


class TheLaneAndTheWireCarryIt(unittest.TestCase):
    """[[the-unjoined-end]] — the join is worth nothing if it stops before a screen."""

    def test_the_tombstone_lane_carries_the_closure_rows(self):
        import river_lanes as RL
        rep = _rep(_live("reel_a", station="ROUTED"))
        with _Ledger({"reels": [_closed("reel_g1"), _closed("reel_g2")]}):
            lr = RL.lanes(rep)
        self.assertTrue(lr["ok"], lr.get("why"))
        tomb = [l for l in lr["lanes"] if "TOMBSTONE" in l["stations"]]
        self.assertEqual(1, len(tomb), "no lane covers the TOMBSTONE station")
        self.assertEqual(2, tomb[0]["closedCount"],
                         "the lane labelled 'closed out' still cannot show a closed reel")
        self.assertEqual(2, len(tomb[0]["closedReels"] or []))
        self.assertEqual(2, lr["closed"])
        self.assertEqual(2, lr["lifetime"] - lr["shelf"])

    def test_the_shelf_count_and_reconciles_are_untouched(self):
        import river_lanes as RL
        rep = _rep(_live("reel_a", station="ROUTED"))
        with _Ledger({"reels": [_closed("reel_g%d" % i) for i in range(400)]}):
            lr = RL.lanes(rep)
        self.assertEqual(1, lr["shelf"], "400 closed reels moved the SHELF count")
        self.assertTrue(lr["reconciles"], "the closure rows broke the lanes' reconciliation")
        tomb = [l for l in lr["lanes"] if "TOMBSTONE" in l["stations"]][0]
        self.assertEqual(1, tomb["count"], "closed reels were folded into the lane's own count")

    def test_the_drawn_sample_never_passes_for_the_total(self):
        """#15's precedent: one open built ~72,700 nodes. The cap is fine; a silent cap is not."""
        import river_lanes as RL
        with _Ledger({"reels": [_closed("reel_g%d" % i) for i in range(400)]}):
            lr = RL.lanes(_rep(_live("reel_a", station="ROUTED")))
        tomb = [l for l in lr["lanes"] if "TOMBSTONE" in l["stations"]][0]
        self.assertEqual(400, tomb["closedCount"], "the count shrank to the sample size")
        self.assertEqual(RL.SHOW_CLOSED, len(tomb["closedReels"]))
        self.assertEqual(RL.SHOW_CLOSED, tomb["closedShown"],
                         "nothing says how much of the 400 is actually drawn")

    def test_an_unreadable_ledger_reaches_the_lane_as_unknown(self):
        import river_lanes as RL
        with _Ledger("not json"):
            lr = RL.lanes(_rep(_live("reel_a", station="ROUTED")))
        tomb = [l for l in lr["lanes"] if "TOMBSTONE" in l["stations"]][0]
        self.assertIsNone(tomb["closedCount"], "an unreadable ledger drew as 0 closed reels")
        self.assertIsNone(lr["closed"])
        self.assertIsNone(lr["lifetime"])

    def test_the_endpoint_ships_the_closed_half(self):
        """The whitelist at /api/river is the last place this fact can be silently dropped."""
        import ast
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        i = src.find('_lane_rows.append({"name": l["name"]')
        self.assertGreater(i, 0, "the /api/river lane whitelist moved — this gate lost its target")
        j = src.find('"lanes": _lane_rows}', i)
        self.assertGreater(j, i, "could not find the end of the /api/river payload block")
        blk = src[i:j]
        for key in ('"closedCount"', '"closedIds"', '"closedShown"'):
            self.assertIn(key, blk,
                          "/api/river drops %s, so the lane's closure figure never reaches the "
                          "page and the join ends one file short of a screen" % key)
        self.assertIn('"lifetime": _lr.get("lifetime")', blk,
                      "/api/river ships the shelf without the lifetime denominator")

    def test_the_page_draws_it_and_does_not_read_unknown_as_zero(self):
        src = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
        i = src.find("function _shLanesRender")
        self.assertGreater(i, 0)
        j = src.find("window._shLanesRender = _shLanesRender", i)
        self.assertGreater(j, i)
        blk = src[i:j]
        self.assertIn("closedCount", blk, "the renderer never reads the lane's closure count")
        self.assertIn("shr-cl", blk, "the closure figure is computed and never drawn")
        # ⚠ `l.closedCount || 0` would turn UNKNOWN into a confident zero. The guard is that the
        # renderer distinguishes them, and the `=== 0 ||` idiom is how this file does that.
        self.assertIn("(l.closedCount === 0 || l.closedCount)", blk,
                      "the renderer coerces an UNKNOWN closure count into a number")
        self.assertNotIn("l.closedCount || 0", blk,
                         "UNKNOWN would render as 0 closed reels — the exact conflation this "
                         "whole change exists to end")


class NodeMissing(Exception):
    """node is not installed — the ONLY legitimate reason not to run these."""


def _render(payload):
    """Run the SHIPPED `_shLanesRender` in node. -> str

    ⚠ The probe file is named after THIS gate. The sibling gate uses the same technique and the
    same TMPDIR, and run_gates may run them together — two guards writing one scratch path is a
    race that would make either of them fail for the other's reasons.

    ⚠⚠ A BROKEN RENDERER RAISES; ONLY A MISSING NODE SKIPS. The first cut returned None on EVERY
    failure and the caller turned that into `skipTest`, so a `_shLanesRender` that would not even
    PARSE exited this gate green — and Heart 2.0 proved it: tamper [4] introduced a JS syntax
    error and the law stayed GREEN through its own defeat, reported BLIND. "node is absent" and
    "the shipped renderer is broken" are opposite facts and only one of them is a legitimate
    skip. [[regression-guard]] — SKIP IS NOT PASS.
    """
    import json as _json
    import subprocess
    ui = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
    # ⚠ 2026-09-28 — THE CUT STARTS AT THE TRIAGE LANE'S HELPERS, which sit directly above the renderer: it now draws
    # the lane's one line (_shTriageLine, _triageSay, _shAgo, _TRIAGE_WORDS) on every path, and a cut that starts at
    # `function _shLanesRender` hands node a renderer whose helpers are not defined (ReferenceError on every case).
    i = ui.find("  var _TRIAGE_WORDS = {")
    if i < 0 or i > ui.find("  function _shLanesRender(d){"):
        i = ui.find("  function _shLanesRender(d){")
    j = ui.find("  window._shLanesRender = _shLanesRender;", i)
    if i < 0 or j < 0:
        raise AssertionError("_shLanesRender is no longer findable in control_ui.html — this "
                             "gate has lost its target and is measuring nothing")
    # ⚠⚠ THE FAKE ELEMENT MUST ANSWER EVERYTHING THE SHIPPED CODE ASKS IT. This stub carried
    # `innerHTML` alone, and `_shLanesRender` also does:
    #     var _fd = el.querySelector('.shr-fold');
    #     if (_fd) _fd.addEventListener('toggle', ... localStorage.setItem(...) ...)
    # so the probe died with "el.querySelector is not a function" and all three laws failed on a
    # HARNESS gap while reporting as if the shipped renderer were broken. Same class as
    # test_fleet_mask's node harness modelling a page with no LSR (REG-1041): a fixture that
    # cannot satisfy the code it drives measures nothing, and fails naming the wrong subject.
    #
    # ⚠ It returns a REAL-SHAPED fold element rather than null. Null would also pass — the `if
    # (_fd)` guard would simply skip — but it would silently stop exercising the listener branch,
    # and a stub that answers "not there" to everything is how a fixture drifts into testing less
    # than it claims. `localStorage` is stubbed for the same reason: the callback writes to it.
    # [[feedback-blind-fixture-green-gate]]
    js = ("var out = '';\n"
          "var window = {};\n"
          "var _fold = { open: false, addEventListener: function(){} };\n"
          "var localStorage = { setItem: function(){}, getItem: function(){ return null; } };\n"
          "var document = { getElementById: function(){ return { set innerHTML(v){ out = v; },"
          " get innerHTML(){ return out; },"
          " querySelector: function(sel){ return sel === '.shr-fold' ? _fold : null; } }; } };\n"
          "var esc = function(s){ return String(s === undefined ? '' : s)"
          ".replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/\"/g,'&quot;'); };\n"
          + ui[i:j] + "\n_shLanesRender(" + _json.dumps(payload) + ");\n"
          "console.log(JSON.stringify(out));")
    path = os.path.join(tempfile.gettempdir(), "whole_life_lanes_probe.js")
    io.open(path, "w", encoding="utf-8").write(js)
    try:
        r = subprocess.run(["node", path], capture_output=True, text=True, timeout=90)
    except (OSError, FileNotFoundError):
        raise NodeMissing("node is not installed")
    if r.returncode != 0:
        raise AssertionError("the SHIPPED _shLanesRender would not run in node (exit %d): %s"
                             % (r.returncode, (r.stderr or "").strip()[:400]))
    try:
        return _json.loads((r.stdout or "").strip().split("\n")[-1])
    except Exception as exc:
        raise AssertionError("_shLanesRender ran but produced no readable HTML (%s): %r"
                             % (type(exc).__name__, (r.stdout or "")[:200]))


def _payload(closed):
    """A /api/river lanes payload whose TOMBSTONE lane carries `closed` as its closure count."""
    lanes = []
    for name, sts in (("INTAKE", ["INTAKE", "TRIAGE", "STATION", "EMPTY"]),
                      ("PRINTER", ["PRINTER"]), ("CAPTURE", ["CAPTURE", "JOIN"]),
                      ("TOMBSTONE", ["ROUTED", "TOMBSTONE"])):
        tomb = name == "TOMBSTONE"
        lanes.append({"name": name, "why": name.lower(), "stations": sts, "count": 1 if tomb else 1,
                      "byStation": {s: (0 if s == "TOMBSTONE" else 1) for s in sts},
                      "reelIds": [],
                      "closedCount": closed if tomb else 0,
                      "closedShown": (None if closed is None else (min(closed, 24) if tomb else 0)),
                      "closedIds": [], "closedWhy": "fixture"})
    return {"lanes": {"ok": True, "reconciles": True, "shelf": 4, "unknown": 0,
                      "closed": closed, "closedWhy": "fixture",
                      "lifetime": (None if closed is None else 4 + closed),
                      "idsCapped": False, "lanes": lanes}}


class TheRenderedStripSaysWhichSource(unittest.TestCase):
    """⚠ THE THREE CLOSURE STATES ARE THREE DIFFERENT SENTENCES, and one of them had NO BRANCH.

    A readable ledger naming nothing (`closedCount: 0`) fell through every condition and the strip
    emitted no note at all — the last lane back to reading dead with nothing saying why, which is
    the exact defect the note exists to prevent, reintroduced by the change that fixed it. Caught
    by a sibling gate, so this one now exercises all three on the SHIPPED renderer.
    """

    def _got(self, closed):
        try:
            return _render(_payload(closed))
        except NodeMissing:
            self.skipTest("node is not installed — a skip is NOT a pass, and it is the ONLY "
                          "condition that skips here: a renderer that fails to run FAILS")

    def test_a_ledger_with_reels_names_its_source_and_never_reads_as_arithmetic(self):
        got = self._got(7)
        self.assertIn("the ledger", got,
                      "the closure figure does not name its source, so a reader has nothing "
                      "telling them it is not more of the station count above it")
        self.assertIn("7 closed out", got)
        # ⚠⚠ THE LAW IS "NO PLUS ANYWHERE IN THE CHIP", NOT "NOT THE STRING `>+7`". The narrow
        # version was written first and Heart 2.0 reported it BLIND: a tamper putting the plus
        # back as `</i>+<b>7</b>` left `>+7` absent, so the guard sailed through its own defeat.
        # A guard that pins ONE SPELLING of a defect is pinned to the spelling, not the law.
        # [[regression-guard]] — PIN THE LAW, NOT THE NUMBER.
        import re as _re
        chip = _re.search(r'class="shr-cl"[^>]*>(.*?)</div>', got)
        self.assertIsNotNone(chip, "the closure chip is not in the rendered strip at all")
        self.assertNotIn("+", chip.group(1),
                         "the closure chip carries a plus sign directly under the lane's own 0 — "
                         "a cross-family eye read exactly that as 0 + 7 = 7 reels in the lane. "
                         "Rendered chip: %r" % chip.group(1)[:140])
        self.assertIn("leaves the shelf", got, "the zero station lost the reason it is zero")

    def test_a_readable_empty_ledger_is_a_measured_zero_and_says_so(self):
        got = self._got(0)
        self.assertIn("leaves the shelf", got,
                      "a readable-but-empty ledger produced NO note, so the last lane reads dead")
        self.assertIn("measured zero", got,
                      "nothing distinguishes 'nothing has closed out' from 'nobody looked'")

    def test_an_unreadable_ledger_says_unknown_and_still_explains_the_zero(self):
        got = self._got(None)
        self.assertIn("leaves the shelf", got, "the zero station lost the reason it is zero")
        self.assertIn("UNKNOWN", got)
        self.assertNotIn("measured zero", got,
                         "an unreadable ledger is described as a measured zero")


# ══ THE EXECUTABLE RED-PROOF ═════════════════════════════════════════════════════════════════
# Heart 2.0 re-runs this in a sandbox and DISTRUSTS the law if it stays green. Three tampers,
# because this gate holds three separable claims and any one of them could rot alone.
RED_PROOF = [
    {
        "why": "not assigning TOMBSTONE is the original defect verbatim — the declared station "
               "no code path could produce",
        "file": "reel_router.py",
        "find": '''                "station": "TOMBSTONE",''',
        "replace": '''                "station": "ROUTED",''',
        "matches": 1,
    },
    {
        "why": "letting the closure rows into the lane's own count is the fix that moves a number "
               "he reads — 41 becoming 469 with nothing on screen saying why",
        "file": "river_lanes.py",
        "find": '''            "count": len(reels),''',
        "replace": '''            "count": len(reels) + len(_cl or []),''',
        "matches": 1,
    },
    {
        "why": "coercing an unreadable ledger to 0 restores the conflation between 'nothing has "
               "closed out' and 'I could not tell'",
        "file": "river_lanes.py",
        "find": '''            "closedCount": (None if _cl is None else len(_cl)),''',
        "replace": '''            "closedCount": len(_cl or []),''',
        "matches": 1,
    },
    {
        "why": "collapsing the three closure states back into two is how a readable-but-empty "
               "ledger came to emit no note at all — the last lane reading dead with nothing "
               "saying why, which is the defect the note exists to prevent",
        "file": "control_ui.html",
        "find": """      } else if (_tc === 0) {""",
        "replace": """      } else if (false) {""",
        "matches": 1,
    },
    {
        "why": "restoring the plus sign restores the reading a cross-family eye actually made: "
               "0 + 7 = 7 reels in the lane",
        "file": "control_ui.html",
        "find": """<i>deleted \\u00b7 the ledger</i><b>' + _lc""",
        "replace": """<i>the ledger</i>+<b>' + _lc""",
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
