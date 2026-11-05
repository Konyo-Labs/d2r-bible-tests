# -*- coding: utf-8 -*-
"""REG-3198 - EVERY RUNNING CONSOLE COMPUTES ITS OWN RIVER, AND AN OFFLINE ONE IS SAID OFFLINE, NOT UNKNOWN.

His words 2026-11-05: "i want the river flowing and the fleet rendering it properly that it is for each and for whoever
is not fix it! this is too long waiting and been said dozens of times". MEASURED on his /api/fleet at 21:01: Dean
(v3860, last beacon 02:49) and GrokBot (v3815, offline since 10-27) both sent river.lanes null with "this console has
not computed its river since it started - nothing has asked for the river yet, and the beacon never computes it
itself", and Dean's row drew red "locks shut · rechecking" + "river UNKNOWN" 18 hours after he was last heard.

The joints this closes (the console's own river lane, tvd-river-warm, #193, on the roster's thread door):
  * /api/river serves the last FINISHED walk; before one has finished in a process it answers {computing: true} and
    keeps nothing. The lane counted that answer as a read and slept RIVER_WARM_EVERY_S, so a fresh console carried no
    lanes for ~6 minutes. A pass now asks again every RIVER_WARM_POLL_S until the walk it started finishes (inside
    RIVER_WARM_TIMEOUT_S - past it the pass is a failed read, TimeoutError, never a counted one).
  * the first good river since a start sends ONE beacon (event "river"), as the first proof tick does (v3849) - the
    boot beacon left before it, and a PC that went offline in between kept "has not computed" for good.
  * a console with no river waits for a busy machine at most RIVER_WARM_BUSY_MAX_WAIT_S (REG-1905's rule), then reads
    once; his game is never waited out (playing refuses, always).
  * no lanes is said in the lane's own words (he plays, the machine is busy, it has not run yet) - never "nothing has
    asked for the river yet", which has not been true since #193.
  * the row (control_ui.html, the REAL _fleetStuckChip in node): a PC past its presence bound reads "offline since
    <time> · last river <age>" (or "· no river in its last run"), muted - never red, never a bare UNKNOWN.
  * /api/status carries the lane's record (riverWarm) and the last lock reading (riverLocks).
⚠ NOT a lowered OS thread priority: a Python thread holding the GIL at a lowered priority makes the shadow recorder in
the same process wait on it (priority inversion). The walk stays on river_lanes' own daemon thread, never the beacon's.
RED_PROOF below.
"""
import datetime
import io
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import control_app as CA  # noqa: E402
import test_one_river_chip_per_row as H  # noqa: E402  (the cut-and-run pieces for _fleetStuckChip)

NOW = 1793900000000
MIN = 60 * 1000


def _chip(row, now=NOW):
    """The SHIPPED _fleetStuckChip over one fleet row, run in node (TZ=UTC). -> html"""
    with io.open(H.UI, encoding="utf-8") as fh:
        src = fh.read()
    boot = src[src.index(H.BOOT[0]):src.index("  var _fleetSay = function (k) {")]
    js = ("var window = {};\n"
          "function escC(x){ return String(x).replace(/&/g,'&amp;').replace(/\"/g,'&quot;')"
          ".replace(/</g,'&lt;').replace(/>/g,'&gt;'); }\n%s\n%s\n%s\n%s\n"
          "console.log(JSON.stringify(_fleetStuckChip(%s, %d)));") % (
        H._cut(src, H.AGO[0], H.AGO[1]), boot, H._cut(src, H.WHY[0], H.WHY[1]), H._cut(src, H.CHIP[0], H.CHIP[1]),
        json.dumps(row), now)
    r = subprocess.run([H._need_node(), "-"], input=js, capture_output=True, text=True, timeout=30,
                       env=dict(os.environ, TZ="UTC"))
    if r.returncode != 0:
        raise AssertionError("the cut chip did not run in node: %s" % r.stderr[-600:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _iso(ms):
    return datetime.datetime.fromtimestamp(ms / 1000.0, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


class _Resp(object):
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def close(self):
        pass


class _Clock(object):
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


class TheLaneWaitsForTheWalkItStarted(unittest.TestCase):

    def test_computing_is_asked_again_until_the_walk_finishes(self):
        answers = [b'{"ok": false, "computing": true}', b'{"ok": false, "computing": true}', b'{"ok": true}']
        asked, clock = [], _Clock()

        def route(url, timeout=None):
            asked.append(url)
            return _Resp(answers[min(len(asked), len(answers)) - 1])
        with mock.patch.object(CA, "_RIVER_WARM", dict(CA._RIVER_WARM, worked=0, owed=None, beaconed=True)), \
                mock.patch.object(CA, "_RIVER_LAST", {"good": None, "fail": None}):
            r = CA._river_warm_once(now_ms=NOW, _urlopen=route, playing=False, busy_pct=5.0,
                                    _sleep=clock.sleep, _clock=clock)
        self.assertEqual(len(asked), 3, "the lane took 'computing' for a read (asked %d time(s))" % len(asked))
        self.assertEqual(r["worked"], 1)
        self.assertEqual(r["owed"], 0)
        self.assertIn("after its walk finished", r["say"])

    def test_a_walk_that_never_finishes_is_a_failed_read(self):
        asked, clock = [], _Clock()

        def route(url, timeout=None):
            asked.append(url)
            if len(asked) > 400:
                raise RuntimeError("asked for ever")
            return _Resp(b'{"ok": false, "computing": true}')
        with mock.patch.object(CA, "_RIVER_WARM", dict(CA._RIVER_WARM, worked=0, owed=None, beaconed=True)), \
                mock.patch.object(CA, "_RIVER_LAST", {"good": None, "fail": None}):
            r = CA._river_warm_once(now_ms=NOW, _urlopen=route, playing=False, busy_pct=5.0,
                                    _sleep=clock.sleep, _clock=clock)
        self.assertEqual(r["worked"], 0, "a walk that never finished was counted as a read")
        self.assertEqual(r["owed"], 1)
        self.assertIn("did not finish inside %d s" % CA.RIVER_WARM_TIMEOUT_S, r["say"], "the lane did not stop at its own bound: %r" % r["say"])
        self.assertLessEqual(len(asked), 2 + int(CA.RIVER_WARM_TIMEOUT_S / CA.RIVER_WARM_POLL_S))


class TheFirstRiverGoesOutAtOnce(unittest.TestCase):

    def test_one_beacon_after_the_first_good_read_and_none_before(self):
        sent = []
        last = {"good": None, "fail": None}

        def route_fills(url, timeout=None):
            last["good"] = {"ts": NOW, "n": 1, "stations": {"PRINTER": 1}}   # what the route remembers when it walks
            return _Resp(b'{"ok": true}')

        def route_empty(url, timeout=None):
            return _Resp(b'{"ok": true}')
        rec = dict(CA._RIVER_WARM, worked=0, owed=None, beaconed=False)
        with mock.patch.object(CA, "_RIVER_WARM", rec), mock.patch.object(CA, "_RIVER_LAST", last):
            CA._river_warm_once(now_ms=NOW, _urlopen=route_empty, playing=False, busy_pct=5.0, _beacon=sent.append)
            self.assertEqual(sent, [], "a beacon went out with no river to carry")
            CA._river_warm_once(now_ms=NOW, _urlopen=route_fills, playing=False, busy_pct=5.0, _beacon=sent.append)
            self.assertEqual(sent, ["river"], "the first good river did not go out at once")
            last["good"] = None
            CA._river_warm_once(now_ms=NOW + 20 * MIN, _urlopen=route_fills, playing=False, busy_pct=5.0,
                                _beacon=sent.append)
        self.assertEqual(sent, ["river"], "every read sent a beacon of its own")


class ABusyMachineIsNotWaitedForEver(unittest.TestCase):

    def test_no_river_reads_once_past_the_busy_bound(self):
        empty = {"good": None, "fail": None}
        busy = CA.RIVER_WARM_BUSY_PCT + 5
        bound = CA.RIVER_WARM_BUSY_MAX_WAIT_S * 1000
        due, why = CA._river_warm_due(NOW, empty, False, busy, NOW - bound - MIN)
        self.assertTrue(due, "a console with no river waited for a busy machine for ever: %s" % why)
        self.assertIn("no river yet", why)
        due, _ = CA._river_warm_due(NOW, empty, False, busy, NOW - 2 * MIN)
        self.assertFalse(due, "a just-busy machine was walked at once")
        good = {"good": {"ts": NOW - 20 * MIN, "n": 1}, "fail": None}
        due, _ = CA._river_warm_due(NOW, good, False, busy, NOW - bound - MIN)
        self.assertFalse(due, "a console that has a river walked a busy machine again")
        due, why = CA._river_warm_due(NOW, empty, True, busy, NOW - bound - MIN)
        self.assertFalse(due, "the walk ran while he played")

    def test_the_pass_remembers_when_the_machine_went_busy(self):
        rec = dict(CA._RIVER_WARM, busySince=None)
        with mock.patch.object(CA, "_RIVER_WARM", rec), \
                mock.patch.object(CA, "_RIVER_LAST", {"good": None, "fail": None}):
            CA._river_warm_once(now_ms=NOW, _urlopen=None, playing=False, busy_pct=CA.RIVER_WARM_BUSY_PCT + 5)
            self.assertEqual(rec["busySince"], NOW)
            CA._river_warm_once(now_ms=NOW + MIN, _urlopen=None, playing=False, busy_pct=CA.RIVER_WARM_BUSY_PCT + 5)
            self.assertEqual(rec["busySince"], NOW, "each busy pass restarted the wait, so it never ends")


class NoLanesSayWhy(unittest.TestCase):

    def _why(self, warm):
        with mock.patch.object(CA, "_RIVER_WARM", warm), \
                mock.patch.object(CA, "_RIVER_LAST", {"good": None, "fail": None}):
            return CA._river_for_wire(now_ms=NOW)["why"]

    def test_the_lane_says_why_it_has_not(self):
        w = self._why(dict(CA._RIVER_WARM, lastTs=NOW - MIN,
                           say="he is playing - the river walk waits for the game to close"))
        self.assertIn("has not computed its river", w)
        self.assertIn("he is playing", w, "the row was not told why: %r" % w)
        self.assertNotIn("nothing has asked", w)
        w = self._why(dict(CA._RIVER_WARM, lastTs=None))
        self.assertIn("has not run yet", w)
        self.assertNotIn("nothing has asked", w)

    def test_the_status_carries_the_lane(self):
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.assertEqual(src.count('"riverWarm": dict(_RIVER_WARM), "riverLocks": dict(_RIVER_LOCKS_SEEN), '), 1,
                         "/api/status does not carry the river lane's record")


@unittest.skipIf(H.NODE is None, "node is not on this machine - this law RUNS the shipped chip and will not re-implement it")
class AnOfflineRowIsSaidOffline(unittest.TestCase):

    def _dean(self, river, gone_s=18 * 3600):
        return {"t": _iso(NOW - gone_s * 1000), "nickname": "Dean",
                "presence": {"state": "offline", "online": False, "via": None, "ageS": gone_s,
                             "words": "offline \u00b7 last seen 18 hr ago", "staleAfterS": 520},
                "system": {"river": river}}

    def test_the_measured_dean_row(self):
        html = _chip(self._dean({"lanes": None, "ageS": None, "stuck": None,
                                 "why": "this console has not computed its river since it started - its river lane "
                                        "reads it about 60 s after a start and has not run yet",
                                 "heart": {"census": "stale", "key": "stale-at-boot", "blind": None}}))
        self.assertIn(">offline since 23:33 \u00b7 no river in its last run<", html, html)
        self.assertIn("fleet-riveroff", html)
        for word in ("locks shut", "river UNKNOWN", "fleet-riverstuck", "river stuck"):
            self.assertNotIn(word, html, "an 18 h offline row still drew %r" % word)
        self.assertIn("has not computed its river", html, "the hover lost the PC's own last word")

    def test_a_last_river_keeps_ageing_offline(self):
        html = _chip(self._dean({"lanes": {"ROUTED": 4}, "ageS": 600.0, "stuck": [],
                                 "heart": {"census": "current", "key": "current", "blind": 0}}, gone_s=3 * 3600))
        self.assertIn(">offline since 14:33 \u00b7 last river 3h ago<", html,
                      "the river's age stopped at the beacon instead of ageing with the PC: %r" % html)

    def test_a_row_offline_for_days_names_the_day(self):
        html = _chip(self._dean({"lanes": None, "stuck": None, "heart": {"census": None, "key": "starting"}},
                                gone_s=8 * 86400))
        self.assertIn(">offline since Oct 28 17:33 \u00b7 no river in its last run<", html, html)

    def test_an_online_row_is_untouched(self):
        row = self._dean({"lanes": {"ROUTED": 4}, "ageS": 30.0, "stuck": [],
                          "heart": {"census": "stale", "key": "busy", "blind": None}}, gone_s=60)
        row["presence"] = {"state": "online", "online": True, "via": "console", "ageS": 60}
        html = _chip(row)
        self.assertNotIn("offline since", html)
        self.assertIn("locks shut", html)

    def test_the_red_proof_finds_match_once(self):
        for p in RED_PROOF:
            with io.open(os.path.join(ROOT, p["file"]), encoding="utf-8") as fh:
                self.assertEqual(fh.read().count(p["find"]), p["matches"], p["why"])


RED_PROOF = [
    {"why": "REG-3198 - 'computing' is counted as a read again, and the river waits a whole cadence",
     "file": "tv/control_app.py",
     "find": "    while _river_warm_computing(body):\n",
     "replace": "    while False:\n",
     "matches": 1},
    {"why": "REG-3198 - a walk that never finishes is waited for without a bound",
     "file": "tv/control_app.py",
     "find": "        if clock() - t0 >= RIVER_WARM_TIMEOUT_S:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3198 - the first good river waits minutes for the next beacon",
     "file": "tv/control_app.py",
     "find": "    if not _RIVER_WARM.get(\"beaconed\") and isinstance(_RIVER_LAST.get(\"good\"), dict):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3198 - every read sends a beacon of its own",
     "file": "tv/control_app.py",
     "find": "        _RIVER_WARM[\"beaconed\"] = True\n        try:\n",
     "replace": "        _RIVER_WARM[\"beaconed\"] = False\n        try:\n",
     "matches": 1},
    {"why": "REG-3198 - a console with no river waits for a busy machine for ever",
     "file": "tv/control_app.py",
     "find": "        if not (g is None and _bs is not None and now_ms - _bs >= RIVER_WARM_BUSY_MAX_WAIT_S * 1000):\n",
     "replace": "        if True:\n",
     "matches": 1},
    {"why": "REG-3198 - each busy pass restarts the busy wait, so it never ends",
     "file": "tv/control_app.py",
     "find": "        if _RIVER_WARM.get(\"busySince\") is None:\n            _RIVER_WARM[\"busySince\"] = now\n",
     "replace": "        if True:\n            _RIVER_WARM[\"busySince\"] = now\n",
     "matches": 1},
    {"why": "REG-3198 - no lanes says 'nothing has asked' again instead of the lane's own word",
     "file": "tv/control_app.py",
     "find": "                      + ((\"its river lane: \" + _wire_text(_ws.get(\"say\"), 140)) if _ws.get(\"lastTs\") is not None\n",
     "replace": "                      + ((\"nothing has asked for the river yet\") if _ws.get(\"lastTs\") is not None\n",
     "matches": 1},
    {"why": "REG-3198 - an 18 h offline row draws red locks and river UNKNOWN again (Dean, his 21:01 Fleet)",
     "file": "tv/control_ui.html",
     "find": "    if (_pres && _pres.state === 'offline') {\n",
     "replace": "    if (false) {\n",
     "matches": 1},
    {"why": "REG-3198 - an offline row's last river stops ageing at its beacon",
     "file": "tv/control_ui.html",
     "find": "        _offRiver = 'last river ' + _fleetAgo(rv.ageS + _offGone);\n",
     "replace": "        _offRiver = 'last river ' + _fleetAgo(rv.ageS);\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
