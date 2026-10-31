# -*- coding: utf-8 -*-
"""#193 — A CONSOLE READS ITS OWN RIVER, AND A PC THAT JUST STARTED SAYS SO.

His words, 2026-10-27: *"river says unknown now. make sure its all working and UX and UI freindly"*.

Measured that evening on the Fleet (/api/fleet): the ALT row had lanes but a null heart census, so it said a bare
"river UNKNOWN". Asked the ALT console directly a few minutes later, it said census stale, key aside-cooldown. The
null came from the beacon a self-update sent BEFORE the self-prove lane's first tick, which lands about 5 minutes
after a start. And a console nobody had opened the River on sent "this console has not computed its river since it
started", because only /api/river fills _RIVER_LAST and the beacon never computes it.

Three joints, each driven:
  · the console: the tvd-river-warm lane asks its OWN read-only /api/river a minute after a start and whenever the
    last read is over RIVER_WARM_STALE_S old, never while he plays or the machine is busy; it is on the roster, stood
    down under a harness, and leaves a trace. The beacon names the boot window: key 'starting', census still null.
  · the worker (functions/api/console.js, the REAL shaper in node): key 'starting' crosses; census stays null.
  · the card (control_ui.html, the REAL _fleetStuckChip / _fleetSysParts in node): 'river · starting' in muted
    words and 'first check pending', still UNKNOWN; a null census WITHOUT that key is still 'river UNKNOWN'.
RED_PROOF below.
"""
import ast
import io
import json
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import test_the_fleet_card_says_how_each_pc_films_and_drains as F  # noqa: E402  (its node harness)
import test_each_console_says_its_own_system as S  # noqa: E402  (its worker slicer)

NOW = F.NOW
MIN = 60 * 1000


class TheConsoleAsksItsOwnRiver(unittest.TestCase):

    def test_it_reads_when_nothing_has_and_when_the_read_went_stale(self):
        import control_app as ca
        stale = ca.RIVER_WARM_STALE_S * 1000
        due, why = ca._river_warm_due(NOW, {"good": None, "fail": None}, False, 10.0)
        self.assertTrue(due, why)
        self.assertIn("since this console started", why)
        due, why = ca._river_warm_due(NOW, {"good": {"ts": NOW - stale - MIN, "n": 1}, "fail": None}, False, 10.0)
        self.assertTrue(due, "a river read older than the stale window was never refreshed: %s" % why)
        due, why = ca._river_warm_due(NOW, {"good": {"ts": NOW - MIN, "n": 1}, "fail": None}, False, 10.0)
        self.assertFalse(due, "a fresh river was walked again: %s" % why)
        # a failed read is retried on the cadence, never in a tight loop
        due, why = ca._river_warm_due(NOW, {"good": None, "fail": {"ts": NOW - MIN, "n": 1}}, False, 10.0)
        self.assertFalse(due, "a read that just failed was asked again at once: %s" % why)

    def test_it_never_reads_while_he_plays_or_the_machine_is_busy(self):
        import control_app as ca
        empty = {"good": None, "fail": None}
        due, why = ca._river_warm_due(NOW, empty, True, 5.0)
        self.assertFalse(due, "the river walk ran while he played")
        self.assertIn("playing", why)
        due, why = ca._river_warm_due(NOW, empty, False, ca.RIVER_WARM_BUSY_PCT + 1)
        self.assertFalse(due, "the river walk ran on a busy machine")
        self.assertIn("busy", why)
        # an unmeasured CPU is not a busy one (the walk is read-only), and not a reason to wait for ever
        due, _ = ca._river_warm_due(NOW, empty, False, None)
        self.assertTrue(due)

    def test_one_pass_asks_the_read_only_route_and_a_failure_stays_a_failure(self):
        import control_app as ca
        asked = []

        class _R(object):
            def read(self):
                return b"{}"

        def _ok(url, timeout=None):
            asked.append((url, timeout))
            return _R()

        rec = dict(ca._RIVER_WARM)
        with mock.patch.object(ca, "_RIVER_WARM", rec), \
                mock.patch.object(ca, "_RIVER_LAST", {"good": None, "fail": None}):
            r = ca._river_warm_once(now_ms=NOW, _urlopen=_ok, playing=False, busy_pct=5.0)
        self.assertEqual(len(asked), 1, "the warm pass did not ask the river")
        self.assertTrue(asked[0][0].endswith("/api/river"), "it asked %r, not the read-only river" % asked[0][0])
        self.assertIn("127.0.0.1:%d" % ca.CONTROL_PORT, asked[0][0])
        self.assertEqual(r["worked"], int(ca._RIVER_WARM.get("worked") or 0) + 1, "a read that reached the route was not counted")
        self.assertEqual(r["owed"], 0)

        def _boom(url, timeout=None):
            raise OSError("refused")

        rec = dict(ca._RIVER_WARM, worked=0)
        with mock.patch.object(ca, "_RIVER_WARM", rec), \
                mock.patch.object(ca, "_RIVER_LAST", {"good": None, "fail": None}):
            r = ca._river_warm_once(now_ms=NOW, _urlopen=_boom, playing=False, busy_pct=5.0)
        self.assertEqual(r["worked"], 0, "a read that never reached the route was counted as work")
        self.assertEqual(r["owed"], 1)
        self.assertIn("OSError", r["say"])

        asked[:] = []
        with mock.patch.object(ca, "_RIVER_WARM", dict(ca._RIVER_WARM)), \
                mock.patch.object(ca, "_RIVER_LAST", {"good": None, "fail": None}):
            r = ca._river_warm_once(now_ms=NOW, _urlopen=_ok, playing=True, busy_pct=5.0)
        self.assertEqual(asked, [], "the warm pass walked the river while he played")
        self.assertIn("playing", r["say"])

    def test_a_waiting_pass_keeps_a_failure_and_a_read_closes_its_response(self):
        """The Grok eye on v3813: a pass that waits wrote owed=0 over a failure; the response was never closed."""
        import control_app as ca

        def _boom(url, timeout=None):
            raise OSError("refused")

        rec = dict(ca._RIVER_WARM, worked=0, owed=None)
        with mock.patch.object(ca, "_RIVER_WARM", rec), \
                mock.patch.object(ca, "_RIVER_LAST", {"good": None, "fail": None}):
            ca._river_warm_once(now_ms=NOW, _urlopen=_boom, playing=False, busy_pct=5.0)
            r = ca._river_warm_once(now_ms=NOW + 60000, _urlopen=_boom, playing=True, busy_pct=5.0)
        self.assertEqual(r["owed"], 1, "a pass that waited for his game cleared the failed read: %r" % r)
        closed = []

        class _R(object):
            def read(self):
                return b"{}"

            def close(self):
                closed.append(1)

        with mock.patch.object(ca, "_RIVER_WARM", dict(ca._RIVER_WARM)), \
                mock.patch.object(ca, "_RIVER_LAST", {"good": None, "fail": None}):
            r = ca._river_warm_once(now_ms=NOW, _urlopen=lambda url, timeout=None: _R(), playing=False, busy_pct=5.0)
        self.assertEqual(closed, [1], "the river read left its response open")
        self.assertEqual(r["owed"], 0)

    def test_the_lane_is_on_the_roster_stood_down_in_a_harness_and_leaves_a_trace(self):
        import control_app as ca
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        tree = ast.parse(src)
        pairs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Tuple) and len(node.elts) == 2 and isinstance(node.elts[0], ast.Constant) \
                    and node.elts[0].value == "tvd-river-warm" and isinstance(node.elts[1], ast.Name):
                pairs.append(node.elts[1].id)
        self.assertEqual(pairs, ["_river_warm_loop"], "the river warm lane is not on the roster exactly once")
        self.assertIn("tvd-river-warm", ca._HARNESS_ONLY_SKIP,
                      "a render or demo console would pay a river walk over its fixture reels")
        self.assertIn("lane_trace", ca._river_warm_loop.__code__.co_names, "the warm lane leaves no trace")
        import loop_corroborate as lc
        self.assertIn("_river_warm_loop", lc.SURFACES)
        self.assertEqual(lc.LOOPS["_river_warm_loop"][0], "tvd-river-warm")
        self.assertEqual(lc.LOOPS["_river_warm_loop"][2], float(ca.RIVER_WARM_EVERY_S))
        import auto_scope as asc
        self.assertEqual(asc.LANE_FN.get("tvd-river-warm"), "_river_warm_loop")


class TheBootWindowHasAName(unittest.TestCase):

    def _heart(self, sp):
        import control_app as ca
        # The disk census is stubbed to "not already shut". A known stale/missing/unreadable census is
        # stale-at-boot in its own law; this floor stays starting + null when that census is not shut.
        with mock.patch.object(ca, "_SELF_PROVE", sp), \
                mock.patch.object(ca, "_boot_census_once", lambda: None), \
                mock.patch.object(ca, "_RIVER_LAST", {"good": None, "fail": None}):
            return ca._river_for_wire(now_ms=NOW)["heart"]

    def test_before_the_first_tick_it_is_starting_and_still_unknown(self):
        import control_app as ca
        h = self._heart({"on": None, "worked": None, "lastTs": None, "owed": None, "key": None,
                         "say": "the self-prove lane has not ticked yet since this console started"})
        self.assertIsNone(h["census"], "the boot window invented a census")
        self.assertEqual(h["key"], "starting", "a console that just started sent a bare null census")
        # a ticked lane keeps its own key
        h = self._heart({"on": True, "worked": 0, "lastTs": NOW, "owed": 3, "key": "aside-cooldown", "census": "stale"})
        self.assertEqual((h["census"], h["key"]), ("stale", "aside-cooldown"))
        # a tick that raised is not 'starting' - it is a fault with its own word
        h = self._heart({"on": None, "worked": None, "lastTs": None, "owed": None, "key": "raised",
                         "say": "the self-prove tick raised KeyError"})
        self.assertEqual(h["key"], "raised")
        self.assertIsNone(h["census"])
        self.assertTrue(isinstance(ca.SELF_PROVE_FIRST_TICK, int))

    def test_the_worker_carries_starting_and_keeps_the_census_null(self):
        got = S.TheRelayShapesIt._shape(self, {"tree": "ok", "reels": 3, "river": {
            "lanes": None, "stuck": None, "heart": {"census": None, "key": "starting", "blind": None}}})
        self.assertEqual(got["river"]["heart"], {"census": None, "key": "starting", "blind": None})


class TheRowSaysStartingNotUnknown(unittest.TestCase):

    def _card(self, river, t_ago_s=60):
        row = F._row(t_ago_s=t_ago_s, river=dict({"lanes": None, "ageS": None, "triage": F.TRI_OK,
                                             "why": "this console has not computed its river since it started"},
                                            **river))
        return F._run("OUT.chip = strip(_fleetStuckChip(%s, NOW)); OUT.html = _fleetStuckChip(%s, NOW);"
                      "var p = _fleetSysParts(%s, NOW); OUT.p = {}; p.forEach(function(x){ OUT.p[x.k] = "
                      "{ t: plain(x.t), unk: !!x.unk, warn: !!x.warn, why: x.why }; });"
                      % (json.dumps(row), json.dumps(row), json.dumps(row)))

    def test_a_just_started_pc_says_starting(self):
        out = self._card({"stuck": None, "heart": {"census": None, "key": "starting", "blind": None}})
        self.assertEqual(out["chip"], "river · starting", "a just-started PC wore %r" % out["chip"])
        self.assertIn("fleet-riverunk", out["html"], "the boot window grew an alarm colour")
        self.assertNotIn("river UNKNOWN", out["chip"])
        self.assertNotIn("locks shut", out["chip"])
        self.assertIn("about 5 minutes", out["html"], "the hover does not say what it waits for")
        self.assertEqual(out["p"]["proved"]["t"], "first check pending")
        self.assertTrue(out["p"]["proved"]["unk"], "the boot window read as a measured answer")

    def test_a_pc_heard_only_at_its_start_hours_ago_is_not_starting(self):
        """GrokBot's v3817 pass: an offline row whose last beacon was its first after a start read 'river · starting ...
        started moments ago' 5.5 h later. Past the boot window it is UNKNOWN and says when it last reported."""
        out = self._card({"stuck": None, "heart": {"census": None, "key": "starting", "blind": None}}, t_ago_s=int(5.5 * 3600))
        self.assertNotIn("starting", out["chip"], "a PC last heard 5.5 h ago still reads as booting: %r" % out["chip"])
        self.assertIn("river UNKNOWN", out["chip"])
        self.assertIn("the first after a start", out["html"], "the hover does not say why it is UNKNOWN")
        self.assertEqual(out["p"]["proved"]["t"], "UNKNOWN", "a long-gone boot window still says 'first check pending'")

    def test_a_stuck_river_still_shows_through_the_boot_window(self):
        """The Grok eye on v3813 said the starting chip hides a stuck station. Measured: the stuck chip is drawn first."""
        out = self._card({"lanes": {"PRINTER": 3}, "stuck": [{"station": "PRINTER", "n": 3, "oldestS": 40 * 3600,
                                                              "why": "vault lane: owes 1"}],
                          "heart": {"census": None, "key": "starting", "blind": None}})
        self.assertIn("river stuck", out["chip"], "a stuck station was hidden by the boot window: %r" % out["chip"])
        self.assertIn("river \u00b7 starting", out["chip"])

    def test_a_null_census_without_the_key_is_still_unknown(self):
        out = self._card({"stuck": None, "heart": {"census": None, "key": None, "blind": None}})
        self.assertIn("river UNKNOWN", out["chip"])
        self.assertNotIn("starting", out["chip"])
        self.assertEqual(out["p"]["proved"]["t"], "UNKNOWN")
        raised = self._card({"stuck": None, "heart": {"census": None, "key": "raised", "blind": None}})
        self.assertIn("river UNKNOWN", raised["chip"], "a raised tick was dressed as a calm start")


RED_PROOF = [
    {"why": "the Grok eye on v3813 - a pass that waits clears the lane's recorded failure again",
     "file": "tv/control_app.py",
     "find": "        _RIVER_WARM.update(lastTs=now, say=why)\n        return dict(_RIVER_WARM)\n",
     "replace": "        _RIVER_WARM.update(lastTs=now, owed=0, say=why)\n        return dict(_RIVER_WARM)\n",
     "matches": 1},
    {"why": "the Grok eye on v3813 - the river read leaves its response open again",
     "file": "tv/control_app.py",
     "find": "            if callable(_close):\n                _close()",
     "replace": "            if False:\n                _close()",
     "matches": 1},
    {"why": "#193 - the beacon sends a bare null census through the boot window again",
     "file": "tv/control_app.py",
     "find": "        _key = \"starting\"\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "#193 - the warm lane walks the river while he plays",
     "file": "tv/control_app.py",
     "find": "    if playing:\n        return False, \"he is playing - the river walk waits for the game to close\"\n",
     "replace": "",
     "matches": 1},
    {"why": "#193 - the warm lane re-walks a fresh river every pass",
     "file": "tv/control_app.py",
     "find": "    if newest and now_ms - newest < RIVER_WARM_STALE_S * 1000:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "#193 - the warm lane is off the roster, so nothing reads the river until someone opens it",
     "file": "tv/control_app.py",
     "find": "        (\"tvd-river-warm\", _river_warm_loop),\n",
     "replace": "",
     "matches": 1},
    {"why": "#193 - a harness console walks its fixture river",
     "file": "tv/control_app.py",
     "find": "\"tvd-retro-triage\", \"tvd-orphan-fold\", \"tvd-river-warm\", \"tvd-disk-sign\")",
     "replace": "\"tvd-retro-triage\", \"tvd-orphan-fold\", \"tvd-disk-sign\")",
     "matches": 1},
    {"why": "#193 - a read that never reached the route is counted as work",
     "file": "tv/control_app.py",
     "find": "        _RIVER_WARM.update(lastTs=now, owed=1, ms=int((time.time() - t0) * 1000),\n",
     "replace": "        _RIVER_WARM.update(worked=int(_RIVER_WARM.get(\"worked\") or 0) + 1, lastTs=now, owed=1, ms=int((time.time() - t0) * 1000),\n",
     "matches": 1},
    {"why": "#193 - the card draws the boot window as a bare river UNKNOWN again",
     "file": "tv/control_ui.html",
     "find": "    else if (census === null && hs && hs.key === 'starting') {\n",
     "replace": "    else if (false) {\n",
     "matches": 1},
    {"why": "#193 - the proved part says UNKNOWN through the boot window",
     "file": "tv/control_ui.html",
     "find": "               || ((hs.key === 'starting' && _fleetBooting(m, nowMs)) ? 'first check pending' : 'UNKNOWN');",
     "replace": "               || 'UNKNOWN';",
     "matches": 1},
    {"why": "GrokBot v3817 - an offline row heard only at its start reads 'river · starting' for ever",
     "file": "tv/control_ui.html",
     "find": "    return age !== null && age <= FLEET_BOOT_WINDOW_S;\n",
     "replace": "    return true;\n",
     "matches": 1},
    {"why": "GrokBot v3817 - the system parts say 'first check pending' past the boot window",
     "file": "tv/control_ui.html",
     "find": "((hs.key === 'starting' && _fleetBooting(m, nowMs)) ? 'first check pending' : 'UNKNOWN')",
     "replace": "((hs.key === 'starting') ? 'first check pending' : 'UNKNOWN')",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
