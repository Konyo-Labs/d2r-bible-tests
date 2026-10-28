#!/usr/bin/env python3
"""THE SWEEP SAYS HOW LONG IT HAS BEEN READING — and in the unit it actually buys.

HIS ASK, 2026-09-15: *"time meter for the sweep i want included integrated and installed so i can
see it in th esticky tab console section on the right nder the fleet"*.

WHAT WAS MEASURED WHEN IT WAS BUILT. A vault sweep was live on his console: 43.9 minutes in, 74
paid classify runs and 220 pages spent. Nothing on screen could say any of it, and the one figure
the panel did print read "reels 0 of 14" — because `reelsDone` is written exactly once, at the
very end, from the proposal's `sessionsSeen`.

THE PIECE THAT WAS MISSING WAS THE JOIN, NOT THE MATH. `sweep_eta()` has existed since v2156,
carries its own tests, and already refuses to invent a figure — it returns ok:False plus a `why`
rather than a confident zero. It was wired to the CHRONICLE lane only. The lane that spends the
money had no clock at all. [[the-unjoined-end]]

THIS LAW PINS FOUR THINGS, each of which was FALSE before v3180:

  1. vault_sweep_state() carries an `eta`. Without it the rail meter has nothing to render and
     silently shows an empty card.
  2. That eta is measured in REELS. vault_retro.sweep's own docstring is "PAY FOR RUNS, NOT
     FRAMES — ONE call per candidate still-run"; handing the vault job to sweep_eta's frame-shaped
     defaults divides a run count by a frame count. That is the wrong-population scar already
     recorded at control_app v2168, committed a second time in a second lane.
  3. A sweep that has never run does NOT report a zero. [[zero-needs-a-denominator]]
  4. The meter is STARTED, not merely defined. Four separate defects in this repo have been
     "both ends built, never joined". [[plumbing-with-no-tap]]

⚠ ON HOW THIS READS THE SOURCE. The claims about Python are checked by PARSING, never by
substring — three laws in this repo have matched their own explanatory comments and passed while
the code they described was absent. The one claim about JS strips comments before matching,
because the comment beside the tap discusses the tap. [[source-reading-guard]]
"""
import ast
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _src(name):
    with io.open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return fh.read()


def _strip_js_comments(s):
    """Remove /* */ and // comments so a claim about CODE cannot be satisfied by PROSE."""
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    s = re.sub(r"(?m)^\s*//.*$", " ", s)
    return s


class TheSweepSaysHowLongItHasBeenReading(unittest.TestCase):

    def test_the_vault_state_carries_an_eta(self):
        """vault_sweep_state() must actually call sweep_eta and put it on the dict."""
        tree = ast.parse(_src("control_app.py"))
        fn = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "vault_sweep_state":
                fn = node
        self.assertIsNotNone(fn, "vault_sweep_state is gone from control_app.py")

        calls = [n for n in ast.walk(fn)
                 if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "sweep_eta"]
        print("   sweep_eta calls inside vault_sweep_state: %d" % len(calls))
        self.assertTrue(calls, "the vault lane does not call sweep_eta — the clock is unjoined, "
                               "which is exactly the state the meter was built to end")

        # ...and the result must be STORED under 'eta', not computed and dropped.
        stored = []
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Subscript):
                        k = t.slice
                        # ⚠ py3.9+ hands back the Constant itself, NOT an ast.Index wrapper. A
                        # getattr(.., "value", ..) here returns the STRING and the check silently
                        # stops testing anything — this repo has been bitten by that twice.
                        if isinstance(k, ast.Index):
                            k = k.value
                        if isinstance(k, ast.Constant) and k.value == "eta":
                            stored.append(n)
        print("   assignments to st['eta']: %d" % len(stored))
        self.assertTrue(stored, "sweep_eta is called but its answer is never stored as 'eta'")

    def test_the_vault_eta_is_measured_in_reels_not_frames(self):
        """The vault buys still-RUNS. A frames denominator is the wrong population."""
        tree = ast.parse(_src("control_app.py"))
        fn = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "vault_sweep_state":
                fn = node
        self.assertIsNotNone(fn)
        kw = {}
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "sweep_eta":
                for k in n.keywords:
                    if isinstance(k.value, ast.Constant):
                        kw[k.arg] = k.value.value
        print("   sweep_eta kwargs from the vault lane: %r" % (kw,))
        self.assertEqual(kw.get("unit"), "reel",
                         "the vault eta must be denominated in reels — vault_retro.sweep pays "
                         "'ONE call per candidate still-run', not per frame")
        self.assertEqual(kw.get("done_key"), "runReelsDone",
                         "the numerator must be the per-reel progress hook's counter, not "
                         "`classified` (paid runs) and not `reelsDone` (written once, at the end)")
        self.assertEqual(kw.get("total_key"), "runReelsTotal",
                         "the denominator must be the reel count this run will actually enter")

    def test_a_sweep_that_never_ran_reports_no_figure(self):
        """An idle lane says so. It does not report 0% of 0 reels in 0 seconds."""
        import control_app as ca
        e = ca.sweep_eta({"running": False}, done_key="runReelsDone", base_key=None,
                         total_key="runReelsTotal", unit="reel")
        print("   idle eta: ok=%r pct=%r say=%r" % (e.get("ok"), e.get("pct"), e.get("say")))
        self.assertFalse(e.get("ok"), "an idle sweep must not report a usable estimate")
        self.assertIsNone(e.get("pct"), "an idle sweep must not report a percentage")
        self.assertTrue(e.get("why") or e.get("say"),
                        "refusing to answer without saying why is the unknown-as-zero failure")

    def test_an_early_sweep_does_not_invent_a_finish_time(self):
        """Two reels in is not a rate. The chronicle side shipped an 8-hour ETA off one probe."""
        import time
        import control_app as ca
        e = ca.sweep_eta({"running": True, "phase": "reading", "runReelsDone": 1,
                          "runReelsTotal": 14, "runExact": True,
                          "runStartedTs": int(time.time() * 1000) - 8000},
                         done_key="runReelsDone", base_key=None,
                         total_key="runReelsTotal", unit="reel")
        print("   early eta: ok=%r etaMs=%r why=%r" % (e.get("ok"), e.get("etaMs"), e.get("why")))
        self.assertFalse(e.get("ok"), "one reel is not enough to project a finish time")
        self.assertIsNone(e.get("etaMs"), "no ETA may be published off a single sample")

    def test_a_running_sweep_reports_its_elapsed_time(self):
        """The headline figure of a TIME meter. Always known, never estimated."""
        import time
        import control_app as ca
        e = ca.sweep_eta({"running": True, "phase": "reading", "runReelsDone": 6,
                          "runReelsTotal": 14, "runExact": True,
                          "runStartedTs": int(time.time() * 1000) - 2640000},
                         done_key="runReelsDone", base_key=None,
                         total_key="runReelsTotal", unit="reel")
        print("   live eta: elapsedMs=%r say=%r" % (e.get("elapsedMs"), e.get("say")))
        self.assertIsNotNone(e.get("elapsedMs"), "a time meter with no elapsed time is not one")
        self.assertGreater(e.get("elapsedMs"), 2000000)
        self.assertIn("reel", str(e.get("say")),
                      "the sentence must name the unit it counted, or the number wears a label "
                      "that stopped being true")

    def test_the_reader_offers_a_per_reel_progress_hook(self):
        """Without it nothing outside sweep() can see a reel begin."""
        import inspect
        import vault_retro
        params = inspect.signature(vault_retro.sweep).parameters
        print("   vault_retro.sweep params: %s" % ", ".join(params))
        self.assertIn("on_reel", params,
                      "vault_retro.sweep must offer the per-reel hook the meter counts with")

        # and the vault lane must actually pass one
        tree = ast.parse(_src("control_app.py"))
        passed = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                for k in n.keywords:
                    if k.arg == "on_reel":
                        passed.append(n)
        print("   call sites passing on_reel=: %d" % len(passed))
        self.assertTrue(passed, "the hook exists but the sweep is never asked to report progress")

    def test_the_meter_is_started_not_merely_defined(self):
        """Four defects in this repo have been 'both ends built, never joined'."""
        js = _strip_js_comments(_src("control_ui.html"))
        calls = len(re.findall(r"window\._swmStart\s*\(\s*\)", js))
        defs = len(re.findall(r"window\._swmStart\s*=", js))
        print("   _swmStart definitions: %d | calls (comments stripped): %d" % (defs, calls))
        self.assertTrue(defs, "the sweep meter's starter is gone")
        self.assertTrue(calls, "the sweep meter is defined but never started — plumbing with "
                               "no tap, in the surface he asked to be able to SEE")

    def test_the_meter_lives_in_the_rail_under_the_fleet(self):
        """His placement was explicit: the sticky console section on the right, under THE FLEET."""
        html = _src("control_ui.html")
        i_fleet = html.find('<div class="fleet-box">')
        i_sweep = html.find('id="sweep-box"')
        print("   fleet-box at %d | sweep-box at %d" % (i_fleet, i_sweep))
        self.assertGreater(i_fleet, 0, "the fleet box is gone from the rail")
        self.assertGreater(i_sweep, 0, "the sweep meter is not in the console at all")
        self.assertGreater(i_sweep, i_fleet,
                           "the sweep meter must sit UNDER the fleet, which is where he asked "
                           "for it")

RED_PROOF = [
    {"why": "v3180 - the vault sweep's meter is denominated in frames again: a run count divided by a frame count",
     "file": "tv/control_app.py",
     "find": "                              total_key=\"runReelsTotal\", unit=\"reel\")\n",
     "replace": "                              total_key=\"runReelsTotal\", unit=\"frame\")\n",
     "matches": 1},
    {"why": "v3180 - a running sweep's time meter carries no elapsed time",
     "file": "tv/control_app.py",
     "find": "    out[\"elapsedMs\"] = max(0, now - started) if started else None\n",
     "replace": "    out[\"elapsedMs\"] = None\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
