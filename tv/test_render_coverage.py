"""v2475 — the render gate can now notice its own coverage shrinking.

⚠ THE GAP THIS CLOSES, in TASKS.md's own words under STILL OWED BY ME:

    "The render gate does not cover what I changed. The `console` target went 3/3 -> 2/2 when a
     control was hidden and RE-BASELINED SILENTLY... Unmeasured reads identical to clean in a
     green run."

That is tv/render_check.py's own thesis turned on itself. It refuses a zero-size element, a black
capture, an unsettled page, a dropped socket — every way ONE reading can lie — and had no way to
notice it was taking FEWER readings than before. A control that disappears takes its own check with
it, and two clean measurements are two clean measurements.

The ratchet is tv/swallow_census.py's, INVERTED: that one counts a defect and may only fall; this
counts COVERAGE and may only rise.

⚠ WHAT I COULD NOT ESTABLISH, said plainly rather than guessed. The console target's selector has
been `#btn-mini, #btn-miniauto` since it was introduced in v2378 — measured with
`git log -L '/"sel": "#btn-mini/,+1:tv/render_check.py'`, one commit, no edits. So the 3 -> 2 drop
was a change in the DOM, not in the spec: two ID selectors matching three nodes means a duplicate
id existed, and losing it was most likely a FIX rather than a loss. I did not confirm that, so the
floor blessed today records 2 and this file does not claim to know what the third node was.
The ratchet stops the NEXT silent drop; it cannot recover one that already happened.
"""
import io
import json
import os
import sys
import tempfile
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable  # noqa: E402

enable()

import render_check as R  # noqa: E402


def _run(**widths):
    """A fake per-target result in the shape main() accumulates."""
    return {"ok": True, "why": "", "refusals": [],
            "widths": {k: {"found": v, "painted": v} for k, v in widths.items()}}


RED_PROOF = [
    {
        "why": "#157 - a LIVE population above its floor is counted as stale slack again: shelf-cards' reel count reads as 32 nodes of blindness the ratchet never had",
        "file": "render_check.py",
        "find": "            if n in scope and n not in COVERAGE_VOLATILE and now.get(n, {}).get(k, 0) > floor[n][k]]\n",
        "replace": "            if n in scope and now.get(n, {}).get(k, 0) > floor[n][k]]\n",
        "matches": 1,
    },
    {
        "why": "#157 - shelf-cards leaves the volatile set: a pruned reel refuses the push as a vanished surface",
        "file": "render_check.py",
        "find": "COVERAGE_VOLATILE = frozenset((\"advanced-fleet\", \"shelf-cards\"))\n",
        "replace": "COVERAGE_VOLATILE = frozenset((\"advanced-fleet\",))\n",
        "matches": 1,
    },
    {
        "why": "the ratchet stops refusing a SHRINK — a target measuring fewer nodes than its "
               "floor sails through, which is the whole defect this file exists to catch: a "
               "surface quietly losing pieces inside a green run",
        "file": "render_check.py",
        "find": "            elif is_ < was:",
        "replace": "            elif False and is_ < was:",
        "matches": 1,
    },
    {
        "why": "a target that stops reporting ENTIRELY is accepted. A surface nobody photographs "
               "any more reads exactly like a surface that is fine — unmeasured wearing clean, "
               "and the render gate's most expensive failure mode",
        "file": "render_check.py",
        "find": "        if name not in now:",
        "replace": "        if False and name not in now:",
        "matches": 1,
    },
    {
        "why": "one WIDTH silently disappearing is accepted. 375 is where layout dies and it is "
               "the width most likely to be dropped by a harness change; losing it alone leaves "
               "four green readings and no sign the narrow one stopped happening",
        "file": "render_check.py",
        "find": "            if is_ is None:",
        "replace": "            if False and is_ is None:",
        "matches": 1,
    },
]


class TheRatchetIsActuallyJOINEDToTheVerdict(unittest.TestCase):
    """⚠⚠ EVERY OTHER TEST IN THIS FILE CALLS `_coverage_check` DIRECTLY, SO NOTHING GUARDED THE
    JOIN. The ratchet could be correct in every case and never consulted by the run that decides
    the exit code — [[the-unjoined-end]], the defect class this repo repeats most. Gate the call
    behind `if False:` and all of this file stays green while a vanished surface ships.

    It also pins the SEPARATION that v2481 introduced: coverage refusals must not be added to the
    render-failure counter. Mixing them made `clean = len(targets) - bad` go NEGATIVE and skipped
    both branches that exist to say 'nothing was established'.
    """

    def setUp(self):
        self._realcov, self._realup, self._realdown, self._realcheck = (
            R.COVERAGE, R._chrome_up, R._chrome_down, R.check)
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        R.COVERAGE = self.path
        R._chrome_up = lambda *a, **k: True
        R._chrome_down = lambda *a, **k: None

    def tearDown(self):
        R.COVERAGE, R._chrome_up, R._chrome_down, R.check = (
            self._realcov, self._realup, self._realdown, self._realcheck)
        try:
            os.unlink(self.path)
        except Exception:
            pass

    def _main(self):
        """Run main([]) with every target rendering CLEAN, capturing what it printed."""
        out = []
        import builtins
        real = builtins.print
        builtins.print = lambda *a, **k: out.append(" ".join(str(x) for x in a))
        try:
            rc = R.main([])
        finally:
            builtins.print = real
        return rc, "\n".join(out)

    def test_main_consults_the_ratchet_and_a_shrink_fails_the_RUN(self):
        # a floor demanding a width nobody will report, for a target that DOES render clean
        name = sorted(R.TARGETS)[0]
        io.open(self.path, "w", encoding="utf-8").write(
            json.dumps({"floor": {name: {"1120x628": 99}}}))
        R.check = lambda *a, **k: _run(**{"1120x628": 1})
        rc, out = self._main()
        self.assertNotEqual(rc, 0,
                            "main() exited 0 while the coverage floor was not met — the ratchet "
                            "is not JOINED to the verdict, so it can be right and ignored.\n%s"
                            % out[-600:])

    def test_a_coverage_refusal_is_not_counted_as_a_render_failure(self):
        name = sorted(R.TARGETS)[0]
        io.open(self.path, "w", encoding="utf-8").write(
            json.dumps({"floor": {name: {"1120x628": 99}}}))
        R.check = lambda *a, **k: _run(**{"1120x628": 1})
        _rc, out = self._main()
        self.assertNotIn(
            "-", [w for w in out.split() if w.lstrip("-").isdigit() and w.startswith("-")] and "-" or "",
            "a negative count was printed")
        self.assertTrue(
            "COVERAGE refusal" in out or "ratchet expected" in out,
            "a coverage shortfall was not reported AS a coverage shortfall — it was folded into "
            "the render-failure count, which is how a dead browser printed 'did not render "
            "cleanly, LOOK AT THE PNGs' for PNGs that were never written.\n%s" % out[-600:])


class TheRatchetRefusesAShrink(unittest.TestCase):

    def setUp(self):
        self._real = R.COVERAGE
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        R.COVERAGE = self.path
        self.said = []

    def tearDown(self):
        R.COVERAGE = self._real
        try:
            os.unlink(self.path)
        except Exception:
            pass

    def _say(self, m):
        self.said.append(m)

    def _floor(self, d):
        io.open(self.path, "w", encoding="utf-8").write(json.dumps({"floor": d}))

    def test_a_dropped_node_count_is_refused(self):
        """The whole point: 3 -> 2 must not be a green run."""
        self._floor({"console": {"1120x628": 3}})
        bad = R._coverage_check({"console": _run(**{"1120x628": 2})}, self._say)
        self.assertEqual(bad, 1, "a target measuring 2 nodes where its floor says 3 was accepted")
        self.assertTrue(any("was 3" in m and "console" in m for m in self.said),
                        "the refusal does not name both numbers: %s" % self.said)

    def test_an_unchanged_count_passes(self):
        self._floor({"console": {"1120x628": 2}})
        self.assertEqual(R._coverage_check({"console": _run(**{"1120x628": 2})}, self._say), 0)

    def test_growth_passes_and_is_reported(self):
        """Coverage may rise freely — and it says so, or nobody re-blesses."""
        self._floor({"console": {"1120x628": 2}})
        bad = R._coverage_check({"console": _run(**{"1120x628": 5})}, self._say)
        self.assertEqual(bad, 0, "coverage growing was treated as a failure")
        self.assertTrue(any("grew" in m for m in self.said),
                        "growth was silent, so the floor would never be raised: %s" % self.said)

    def test_a_target_that_stops_reporting_entirely_is_refused(self):
        """A surface that vanishes from the run is UNMEASURED, not clean."""
        self._floor({"console": {"1120x628": 2}, "vault": {"1120x628": 11}})
        bad = R._coverage_check({"console": _run(**{"1120x628": 2})}, self._say)
        self.assertEqual(bad, 1, "a target absent from the whole run was accepted")
        self.assertTrue(any("vault" in m for m in self.said))

    def test_a_width_that_stops_being_measured_is_refused(self):
        """Dropping a viewport is dropping coverage, even if the rest is clean."""
        self._floor({"console": {"1120x628": 2, "375x800": 2}})
        bad = R._coverage_check({"console": _run(**{"1120x628": 2})}, self._say)
        self.assertEqual(bad, 1, "a width silently disappearing was accepted")
        self.assertTrue(any("375x800" in m for m in self.said))

    def test_an_absent_floor_is_UNKNOWN_not_zero(self):
        """No file must not mean 'everything is fine'. [[unknown-stays-unknown]]"""
        os.unlink(self.path)
        self.assertIsNone(R._coverage_floor())
        bad = R._coverage_check({"console": _run(**{"1120x628": 2})}, self._say)
        self.assertEqual(bad, 0, "an absent floor should not fail a run")
        self.assertTrue(any("UNKNOWN" in m for m in self.said),
                        "an absent floor was silently treated as satisfied: %s" % self.said)


class BlessingIsNotAWayToLowerTheBar(unittest.TestCase):

    def setUp(self):
        self._real = R.COVERAGE
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        R.COVERAGE = self.path
        self.said = []

    def tearDown(self):
        R.COVERAGE = self._real
        try:
            os.unlink(self.path)
        except Exception:
            pass

    def _say(self, m):
        self.said.append(m)

    def test_a_partial_run_may_not_write_a_floor(self):
        """One busy afternoon must not become the new normal."""
        rc = R._coverage_bless({"console": _run(**{"1120x628": 1})}, False, self._say)
        self.assertEqual(rc, 2, "a run that did not report every target was allowed to bless")
        self.assertFalse(os.path.getsize(self.path),
                         "a refused bless still wrote the floor file")

    def test_a_clean_run_writes_and_MERGES_rather_than_replacing(self):
        """A target absent from this run keeps its old floor instead of vanishing from the file."""
        io.open(self.path, "w", encoding="utf-8").write(
            json.dumps({"floor": {"vault": {"1120x628": 11}}}))
        rc = R._coverage_bless({"console": _run(**{"1120x628": 2})}, True, self._say)
        self.assertEqual(rc, 0)
        got = json.load(io.open(self.path, encoding="utf-8"))["floor"]
        self.assertIn("vault", got,
                      "blessing dropped a target that was not in this run — the floor may only be "
                      "lowered deliberately, never by omission")
        self.assertEqual(got["console"]["1120x628"], 2)


class TheFloorInTheRepoIsReal(unittest.TestCase):

    def test_it_exists_and_covers_every_target(self):
        """A floor missing a target is a target nobody would notice losing."""
        floor = R._coverage_floor()
        self.assertIsNotNone(
            floor, "tv/render_coverage.json is missing — run: python3 tv/render_check.py --bless")
        missing = sorted(set(R.TARGETS) - set(floor))
        self.assertEqual(missing, [],
                         "these render targets have no coverage floor, so losing them would be "
                         "invisible: %s" % missing)

    def test_every_floor_entry_is_a_positive_count(self):
        """A floor of 0 ratchets nothing — it is the absent case wearing a number."""
        floor = R._coverage_floor() or {}
        zero = ["%s/%s" % (t, w) for t in floor for w, n in floor[t].items() if not n]
        self.assertEqual(zero, [],
                         "these floors are 0, which permits the surface to vanish entirely: %s"
                         % zero)


class TheFloorMayOnlyRISE(unittest.TestCase):
    """⚠⚠ REG-568 — THE RATCHET DID NOT RATCHET. `render_coverage.json`'s own `_why` says *"It may
    only RISE"*, and `--bless` merged with a plain `dict.update()` — which OVERWRITES with whatever
    the run measured, including a LOWER number. Reproduced: a floor of 65 and a run measuring 12
    wrote **12**. So a bless after a real coverage loss silently adopted the loss as the new
    normal, which is exactly what the sentence above it promised could not happen.

    TASKS.md has carried this as still-owed since the `console` target went 3/3 -> 2/2 and was
    re-baselined with nobody noticing. **A floor that can be lowered by the thing it is measuring
    is not a floor.**
    """

    def _bless(self, old, now):
        import render_check as RC
        said, real_floor, real_of = [], RC._coverage_floor, RC._coverage_of
        bak = io.open(RC.COVERAGE, encoding="utf-8").read()
        # REG-3082 - a bless now also writes its record beside the floor: this fixture's must not stand as the real one
        rec_path = RC._bless_record_path()
        rec_bak = io.open(rec_path, encoding="utf-8").read() if os.path.exists(rec_path) else None
        try:
            RC._coverage_floor = lambda: old
            RC._coverage_of = lambda results: now
            RC._coverage_bless({}, True, said.append)
            written = json.loads(io.open(RC.COVERAGE, encoding="utf-8").read())["floor"]
        finally:
            RC._coverage_floor, RC._coverage_of = real_floor, real_of
            io.open(RC.COVERAGE, "w", encoding="utf-8").write(bak)
            if rec_bak is None:
                if os.path.exists(rec_path):
                    os.remove(rec_path)
            else:
                io.open(rec_path, "w", encoding="utf-8").write(rec_bak)
        return written, said

    def test_a_LOWER_measurement_does_not_lower_the_floor(self):
        written, said = self._bless({"heart": {"1440x1000": 65}}, {"heart": {"1440x1000": 12}})
        self.assertEqual(written["heart"]["1440x1000"], 65,
                         "a run measuring 12 wrote the floor DOWN from 65 — the loss became the "
                         "new normal, silently")
        self.assertTrue(any("HELD" in x for x in said),
                        "the floor held and said nothing, so a real coverage loss passes as a "
                        "clean bless: %s" % said)

    def test_a_HIGHER_measurement_still_raises_it(self):
        """⚠ BASELINE: or the fix froze the ratchet and new coverage could never be recorded."""
        written, _ = self._bless({"heart": {"1440x1000": 65}}, {"heart": {"1440x1000": 70}})
        self.assertEqual(written["heart"]["1440x1000"], 70,
                         "growth was refused too, so the floor can never rise again")

    def test_a_NEW_target_is_recorded_rather_than_ignored(self):
        written, _ = self._bless({"heart": {"1440x1000": 65}}, {"brand_new": {"1440x1000": 4}})
        self.assertEqual(written["brand_new"]["1440x1000"], 4,
                         "a target with no prior floor was not recorded at all")
        self.assertEqual(written["heart"]["1440x1000"], 65, "an untouched target lost its floor")



class AVolatileExemptionStaysBounded(unittest.TestCase):
    """⚠⚠ AN EXEMPTION IS A HOLE UNTIL SOMETHING BOUNDS IT.

    `COVERAGE_VOLATILE` stands the POPULATION COUNT down for a target whose node population is
    live. That is correct for exactly one measured reason and it is one step from becoming the
    place every awkward refusal gets filed.

    MEASURED 2026-09-17 on ONE unchanged tree within the hour: `advanced-fleet` at 1120x628 read
    **13 nodes twice** (both during a pre-push, both blocking a ship), **14 twice**, and **15 three
    times**. The differing node was his own fleet row, whose TEXT carries a live status clause, and
    the ratchet keys on text. The target serves the REAL console on purpose, so its population is
    however many machines have beaconed lately.

    [[regression-guard]] [[unknown-stays-unknown]]
    """

    def _rc(self):
        import importlib
        return importlib.import_module("render_check")

    def test_it_names_only_targets_that_actually_exist(self):
        rc = self._rc()
        unknown = sorted(n for n in rc.COVERAGE_VOLATILE if n not in rc.TARGETS)
        self.assertFalse(unknown,
                         "COVERAGE_VOLATILE names %s, which TARGETS does not define - an exemption "
                         "for a surface that is not rendered excuses nothing and hides that it is "
                         "gone" % ", ".join(unknown))

    def test_only_a_target_with_UNSTUBBED_data_may_be_volatile(self):
        """★ THE FIRST CUT OF THIS LAW CHECKED `serve`, AND A SABOTAGE PROVED IT WRONG.

        Slipping `advanced-fleet-down` into the exemption came back GREEN, because `serve` means
        "serve the console", not "serve live data" — BOTH fleet targets set it. The predicate was
        measuring the wrong property and would have waved through the one target that exists
        precisely so the degraded render CAN be pinned.

        The real discriminator, measured: `advanced-fleet-down`'s seed STUBS `fetch` and names
        `/api/fleet` (1039 chars); `advanced-fleet`'s seed does neither (87 chars). A target that
        stubs the data it renders is deterministic by construction and has no claim here.
        [[sabotage-is-usually-the-wrong-one]] [[measured-true-read-wrong]]
        """
        rc = self._rc()
        bad = []
        for n in rc.COVERAGE_VOLATILE:
            t = rc.TARGETS.get(n) or {}
            seed = str(t.get("seed") or "")
            if not t.get("serve"):
                bad.append("%s (does not serve the console at all)" % n)
            elif "fetch" in seed or "XMLHttpRequest" in seed:
                bad.append("%s (its seed STUBS the data it renders, so it is deterministic)" % n)
        self.assertFalse(
            bad, "exempt from the coverage count without earning it: %s" % "; ".join(bad))

    def test_an_UNMEASURED_volatile_target_still_REFUSES(self):
        """★ A CROSS-FAMILY REVIEW CALLED THIS A DEFECT AND IT IS THE BOUNDARY, NOT A HOLE.

        The v3260 look (xai) reported: *"the exemption is incomplete - the `is_ is None` branch is
        not guarded by the volatile check, so a volatile target whose measurement disappeared is
        still refused."* Correct as an observation, wrong as a defect.

        A POPULATION that churned is what COVERAGE_VOLATILE forgives. A target that produced NO
        READING AT ALL means the surface was not rendered - and a volatile population is no excuse
        for an unmeasured one. Exempting it would let this target stop being photographed entirely
        and still read clean: a skip passing for a pass. [[regression-guard]]
        """
        import inspect
        rc = self._rc()
        src = inspect.getsource(rc)
        src = re.sub(r"(?m)^\s*#.*$", " ", src)      # strip comments - prose must not satisfy this
        i = src.find("if is_ is None:")
        self.assertGreater(i, -1, "the unmeasured branch is gone - re-anchor this law")
        branch = src[i:src.find("elif is_ <", i)]
        self.assertIn("bad += 1", branch,
                      "an UNMEASURED target no longer refuses, so a surface that stopped being "
                      "rendered reads as clean")
        self.assertNotIn("COVERAGE_VOLATILE", branch,
                         "the volatile exemption was widened to cover 'no reading at all'. A "
                         "churning population is forgivable; not being photographed is not")

    def test_the_exemption_does_not_SPREAD(self):
        """A ceiling, with the reason: one target has earned this. A second should have to argue
        for itself in a diff, not arrive quietly inside a set nobody re-reads."""
        rc = self._rc()
        self.assertLessEqual(
            len(rc.COVERAGE_VOLATILE), 2,
            "%d targets are exempt from the coverage count. This set was written for ONE measured "
            "case; at this size it is a dumping ground and the ratchet guards nothing."
            % len(rc.COVERAGE_VOLATILE))

    def test_the_stand_down_is_PRINTED_and_not_counted(self):
        """A skip nobody can see is the silent truncation [[regression-guard]] names. The volatile
        branch must SAY the numbers and must not increment the refusal count."""
        import inspect
        rc = self._rc()
        src = inspect.getsource(rc)
        i = src.find("elif is_ < was and name in COVERAGE_VOLATILE:")
        self.assertGreater(i, -1,
                           "nothing stands the volatile count down any more, or it was renamed - "
                           "re-anchor this law rather than deleting it")
        branch = src[i:src.find("elif is_ < was:", i)]
        self.assertIn("\u26aa coverage", branch,
                      "the stand-down does not PRINT the numbers, so an exempt target reads as "
                      "clean and the exemption is invisible")
        self.assertNotIn("bad += 1", branch,
                         "the volatile branch still counts as a refusal, so the exemption does "
                         "nothing except add a confusing line")


class ALivePopulationIsNotAFloor(unittest.TestCase):
    """#157 — a coverage floor pinned to a COUNT OF LIVE ROWS tracks the data, not the surface.

    shelf-cards photographs his reels on the real console: 533 cards at v3051, a floor of 16, 48 on
    2026-09-23 — one selector. Its drop refused pushes whenever a reel was pruned, and its growth was
    reported as 32 nodes of slack the ratchet could never have used. DRIVEN through _coverage_check
    on a temp floor file, never render_coverage.json. [[unknown-stays-unknown]]"""

    def setUp(self):
        self._real = R.COVERAGE
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        R.COVERAGE = self.path
        self.said = []

    def tearDown(self):
        R.COVERAGE = self._real
        try:
            os.unlink(self.path)
        except Exception:
            pass

    def _floor(self, d):
        io.open(self.path, "w", encoding="utf-8").write(json.dumps({"floor": d}))

    def test_shelf_cards_is_a_live_population(self):
        self.assertIn("shelf-cards", R.COVERAGE_VOLATILE)
        seed = str((R.TARGETS.get("shelf-cards") or {}).get("seed") or "")
        self.assertNotIn("fetch", seed, "premise: shelf-cards now stubs its data, so it is "
                                        "deterministic and has no claim to the exemption")

    def test_a_pruned_reel_is_printed_not_refused(self):
        self._floor({"shelf-cards": {"1440x1000": 16}})
        bad = R._coverage_check({"shelf-cards": _run(**{"1440x1000": 12})}, self.said.append)
        self.assertEqual(bad, 0, "a live population shrinking refused the run")
        self.assertTrue(any("\u26aa coverage" in m and "shelf-cards" in m for m in self.said),
                        "the stand-down was silent: %s" % self.said)

    def test_a_live_population_above_its_floor_is_not_slack(self):
        rep = {}
        self._floor({"shelf-cards": {"1440x1000": 16}, "console": {"1440x1000": 2}})
        bad = R._coverage_check({"shelf-cards": _run(**{"1440x1000": 48}),
                                 "console": _run(**{"1440x1000": 5})}, self.said.append, out=rep)
        self.assertEqual(bad, 0)
        self.assertEqual([r[0] for r in rep["stale"]], ["console"],
                         "the stale list must hold the REAL floor that fell behind and not the live one")
        self.assertEqual(rep["staleNodes"], 3, "the live population's 32 was counted as slack")
        self.assertTrue(any("LIVE population" in m and "shelf-cards" in m and "48>16" in m
                            for m in self.said), "the live gap was dropped silently: %s" % self.said)

    def test_a_live_target_with_no_reading_still_refuses(self):
        """The layout half stays pinned: no reading at a width is UNMEASURED, volatile or not."""
        self._floor({"shelf-cards": {"1440x1000": 16, "375x800": 16}})
        bad = R._coverage_check({"shelf-cards": _run(**{"1440x1000": 20})}, self.said.append)
        self.assertEqual(bad, 1, "a live target that stopped being measured at a width read clean")


if __name__ == "__main__":
    unittest.main(verbosity=2)
