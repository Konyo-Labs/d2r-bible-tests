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

The adversarial review of this item reproduced two more holes, closed here too:
  * A FAILING WALK RAN BACK TO BACK. river_lanes._lanes_refresh swallowed the walk's exception and wrote nothing, so the
    route kept answering "computing" and every 5 s poll started a NEW walk - measured 11 walks in one pass with a raising
    lanes(), for the whole 120 s bound, every pass, for good (and _RIVER_LAST never heard of it, so the next pass was
    due at once). Now the failed walk keeps its reason (river_lanes._FAIL), no walk for that key starts again until
    _FAIL_BACKOFF_S has passed, the route answers it as a REFUSAL with the walk's own reason (so _river_remember keeps
    it and failWhy carries it, REG-3196), and the lane counts that answer as a failed read - one walk per pass.
  * THE ADVANCED BOX WAS NOT TOLD. The row's chip said "offline since 02:49 · no river in its last run", while
    _fleetSysParts (the Advanced box, and the row's own hover through _fleetHoverPlain) still said river UNKNOWN, stuck
    UNKNOWN and a warning "proof out of date" for Dean, 17 h offline. Both now read one helper (_fleetOffline).
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
import river_lanes as RL  # noqa: E402
import test_one_river_chip_per_row as H  # noqa: E402  (the cut-and-run pieces for _fleetStuckChip)

NOW = 1793900000000


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()
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


#: the fleet helpers, both ends anchored once (the same block the card's own law cuts; that law drives Chrome, so its
#: harness is not imported here)
FLEET = ("  var _fleetSince = function (iso) {", "  /* \u2500\u2500 v2851 \u2014 A TRANSIENT FAILURE MUST NOT BECOME A PERMANENT CARD")


def _box(row, now=NOW):
    """The SHIPPED _fleetSysParts over one fleet row, run in node (TZ=UTC). -> {key: {t, unk, warn}}"""
    with io.open(H.UI, encoding="utf-8") as fh:
        src = fh.read()
    for a in FLEET:
        if src.count(a) != 1:
            raise AssertionError("anchor %r matched %d times" % (a[:40], src.count(a)))
    i = src.index(FLEET[0])
    block = src[i:src.index(FLEET[1], i)]
    js = ("var window = {}; var document = { getElementById: function () { return null; } };\n"
          "var localStorage = { getItem: function () { return null; }, setItem: function () {} };\n"
          "function escC(x){ return String(x).replace(/&/g,'&amp;').replace(/\"/g,'&quot;')"
          ".replace(/</g,'&lt;').replace(/>/g,'&gt;'); }\nvar esc = escC;\n%s\n%s\n"
          "var out = {}; _fleetSysParts(%s, %d).forEach(function (x) { out[x.k] = { t: String(x.t).replace(/\\u00a0/g, ' '),"
          " unk: !!x.unk, warn: !!x.warn, why: String(x.why || '') }; }); console.log(JSON.stringify(out));") % (
        H._cut(src, H.WHY[0], H.WHY[1]), block, json.dumps(row), now)
    r = subprocess.run([H._need_node(), "-"], input=js, capture_output=True, text=True, timeout=30,
                       env=dict(os.environ, TZ="UTC"))
    if r.returncode != 0:
        raise AssertionError("the cut box did not run in node: %s" % r.stderr[-600:])
    return json.loads(r.stdout.strip().splitlines()[-1])


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


class AFailingWalkIsOneWalk(unittest.TestCase):
    """The reviewer's own shape: lanes() raising, the lane polling while the route says computing."""

    def setUp(self):
        self._saved = (RL.lanes, dict(RL._LAST), dict(RL._FAIL), set(RL._REFRESH_ON))
        RL._LAST.clear()
        RL._FAIL.clear()
        RL._REFRESH_ON.clear()

    def tearDown(self):
        RL.lanes = self._saved[0]
        for d, v in ((RL._LAST, self._saved[1]), (RL._FAIL, self._saved[2])):
            d.clear()
            d.update(v)
        RL._REFRESH_ON.clear()
        RL._REFRESH_ON.update(self._saved[3])

    def _settle(self):
        import time
        for _ in range(200):
            if not RL._REFRESH_ON:
                return
            time.sleep(0.01)
        raise AssertionError("a background walk never ended")

    def test_a_failed_walk_keeps_its_reason_and_is_not_walked_again_at_once(self):
        walks = []

        def boom(hide=None):
            walks.append(1)
            raise KeyError("ROUTED")
        RL.lanes = boom
        self.assertIsNone(RL.lanes_last())
        self._settle()
        for _ in range(5):
            self.assertIsNone(RL.lanes_last(), "a failed walk was served as lanes")
            self._settle()
        self.assertEqual(len(walks), 1, "every ask after a failed walk started another walk (%d)" % len(walks))
        f = RL.last_failure()
        self.assertIsNotNone(f, "the failed walk's reason was not kept")
        self.assertIn("KeyError", f["why"])
        self.assertGreater(f["retryInS"], 0)
        self.assertEqual(RL._LAST, {})
        # past the backoff it is tried again, and a walk that finishes clears the failure
        RL._FAIL[()]["at"] -= RL._FAIL_BACKOFF_S + 1
        RL.lanes = lambda hide=None: {"ok": True, "lanes": []}
        self.assertIsNone(RL.lanes_last())
        self._settle()
        self.assertIsNotNone(RL.lanes_last())
        self.assertIsNone(RL.last_failure(), "a finished walk left the old failure standing")

    def test_one_pass_is_one_walk_and_a_refusal_is_a_failed_read(self):
        import time
        walks, asked, clock = [], [], _Clock()

        def boom(hide=None):
            walks.append(1)
            time.sleep(0.05)        # still walking when the route first answers: "computing", as on a real PC
            raise KeyError("ROUTED")
        RL.lanes = boom

        def route(url, timeout=None):
            # the /api/river decision, from the route's own two calls (its source is pinned below)
            asked.append(url)
            lr = RL.lanes_last()
            lf = RL.last_failure() if lr is None else None
            self._settle()
            if lr is None and lf is not None:
                CA._river_remember({"ok": False, "why": "the river walk failed %.0f s ago (%s)" % (lf["ageS"], lf["why"])})
                return _Resp(json.dumps({"ok": True, "lanes": {"ok": False, "why": "the river walk failed (%s)"
                                                                % lf["why"]}}).encode())
            return _Resp(b'{"ok": false, "computing": true}')
        last = {"good": None, "fail": None}
        with mock.patch.object(CA, "_RIVER_WARM", dict(CA._RIVER_WARM, worked=0, owed=None, beaconed=True)), \
                mock.patch.object(CA, "_RIVER_LAST", last):
            r = CA._river_warm_once(now_ms=NOW, _urlopen=route, playing=False, busy_pct=5.0,
                                    _sleep=clock.sleep, _clock=clock)
            self.assertEqual(len(walks), 1, "one pass ran %d walks back to back" % len(walks))
            self.assertLessEqual(len(asked), 2, "the lane kept polling after the walk failed (%d asks)" % len(asked))
            self.assertEqual(r["worked"], 0, "a failed walk was counted as a read")
            self.assertEqual(r["owed"], 1)
            self.assertIn("the river walk failed", r["say"])
            self.assertIn("KeyError", r["say"], "the walk's own reason did not reach the lane: %r" % r["say"])
            self.assertIn("KeyError", (last.get("fail") or {}).get("why", ""), "the beacon was never told")
            due, why = CA._river_warm_due(int(time.time() * 1000) + 60 * 1000, last, False, 5.0)
            self.assertFalse(due, "the next pass was due at once after a failed walk: %s" % why)

    def test_the_route_answers_a_failed_walk_as_a_refusal(self):
        src = _read(os.path.join(HERE, "control_app.py"))
        i = src.index("                    _lr = _RL.lanes_last(hide=_hide)\n")
        block = src[i:src.index("                    if _lr.get(\"ok\"):\n", i)]
        self.assertEqual(block.count("                    _lf = _RL.last_failure(hide=_hide) if _lr is None else None\n"), 1,
                         "the route never asks whether its walk failed")
        self.assertIn("                    if _lr is None and _lf is not None:\n", block, "a failed walk still answers 'computing'")
        self.assertLess(block.index("                    if _lr is None and _lf is not None:\n"),
                        block.index("                    if _lr is None:\n"),
                        "a failed walk still answers 'computing'")


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
        src = _read(os.path.join(HERE, "control_app.py"))
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

    def test_the_advanced_box_says_offline_too(self):
        # the reviewer on r3, his live rows: Dean 17 h offline read 'river: UNKNOWN', 'stuck: UNKNOWN' and a warning
        # 'proved: proof out of date' in the box while the chip said offline
        dean = self._dean({"lanes": None, "ageS": None, "stuck": None,
                           "why": "this console has not computed its river since it started",
                           "heart": {"census": "stale", "key": "stale-at-boot", "blind": None}})
        grok = self._dean({"lanes": None, "stuck": None, "heart": {"census": None, "key": "starting", "blind": None}},
                          gone_s=8 * 86400)
        old = dict(self._dean(None, gone_s=65 * 86400), system={"tree": "ok"})   # his Wife PC: v2101, no river field
        for row, since in ((dean, "23:33"), (grok, "Oct 28 17:33"), (old, "Sep 1 17:33")):
            parts = _box(row)
            for k in ("river", "stuck", "proved"):
                self.assertIn(k, parts, "the box lost its %s line" % k)
                self.assertNotIn("UNKNOWN", parts[k]["t"], "%s: an offline PC's %s read UNKNOWN" % (since, k))
                self.assertFalse(parts[k]["unk"] or parts[k]["warn"], "%s: an offline %s line was a warning" % (since, k))
                self.assertIn("offline since " + since, parts[k]["t"], parts[k]["t"])
        self.assertIn("no river in its last run", _box(dean)["river"]["t"])
        self.assertIn("proof out of date at its last report", _box(dean)["proved"]["t"])
        self.assertIn("no proof check in its last run", _box(grok)["proved"]["t"])
        self.assertIn("river not reported", _box(old)["river"]["t"])
        self.assertIn("proof not reported", _box(old)["proved"]["t"])
        online = dict(dean, presence={"state": "online", "online": True, "via": "console", "ageS": 60})
        self.assertTrue(_box(online)["river"]["unk"], "an online row with no river stopped saying UNKNOWN")

    def test_an_offline_pc_whose_last_report_carried_a_stuck_list_is_still_offline(self):
        """v3867 - the Grok CLI on REG-3198 (#231 6674616420): the box's offline branch ran only when the stuck field was
        missing, null or not a list. An offline PC whose last beacon carried one painted the live "every station is
        draining", or a warn line in the stuck chip's red, while its row said offline."""
        for stuck, said in (([], "named no station stuck then"),
                            ([{"station": "PRINTER", "n": 3, "oldestS": 30000, "why": "waits on the vault lane"}],
                             "named 1 station(s) stuck then")):
            row = self._dean({"lanes": {"ROUTED": 4}, "ageS": 30.0, "stuck": stuck,
                              "heart": {"census": "fresh", "key": "ok", "blind": None}})
            part = _box(row)["stuck"]
            self.assertIn("offline since 23:33", part["t"], "an offline PC's stuck line read %r" % part["t"])
            self.assertNotIn("draining", part["t"], "an offline PC said its stations are draining now")
            self.assertFalse(part["warn"] or part["unk"], "an offline stuck line was a warning: %r" % part)
            self.assertIn(said, part["why"])

    def test_the_red_proof_finds_match_once(self):
        for p in RED_PROOF:
            with io.open(os.path.join(ROOT, p["file"]), encoding="utf-8") as fh:
                self.assertEqual(fh.read().count(p["find"]), p["matches"], p["why"])


RED_PROOF = [
    {"why": "v3867 - the box's offline branch runs again only when the last report carried no stuck list",
     "file": "tv/control_ui.html",
     "find": "    if (_offS) {\n      out.push(_fleetPart('stuck', ['not read \\u2014 offline since ' + _offS.since], {\n",
     "replace": "    if (_offS && (!rv || typeof rv !== 'object' || sk === undefined || sk === null || !Array.isArray(sk))) {\n      out.push(_fleetPart('stuck', ['not read \\u2014 offline since ' + _offS.since], {\n",
     "matches": 1},
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
     "find": "    var _off = (_pres && _pres.state === 'offline') ? _fleetOffline(m, nowMs) : null;\n    if (_off) {\n",
     "replace": "    var _off = (_pres && _pres.state === 'offline') ? _fleetOffline(m, nowMs) : null;\n    if (false) {\n",
     "matches": 1},
    {"why": "REG-3198 - an offline row's last river stops ageing at its beacon",
     "file": "tv/control_ui.html",
     "find": "      river = 'last river ' + _fleetAgo(rv.ageS + gone);",
     "replace": "      river = 'last river ' + _fleetAgo(rv.ageS);",
     "matches": 1},
    {"why": "REG-3198 (the reviewer on r3) - the Advanced box says river/stuck UNKNOWN and warns for an offline PC",
     "file": "tv/control_ui.html",
     "find": "    var _offS = _fleetOffline(m, nowMs);\n",
     "replace": "    var _offS = null;\n",
     "matches": 1},
    {"why": "REG-3198 (the reviewer on r3) - a failed walk is forgotten, so every ask walks again (11 walks in one pass)",
     "file": "tv/river_lanes.py",
     "find": "                _FAIL[key] = {\"at\": time.time(), \"why\": failed}\n",
     "replace": "                pass\n",
     "matches": 1},
    {"why": "REG-3198 (the reviewer on r3) - a walk that just failed is walked again on the next ask",
     "file": "tv/river_lanes.py",
     "find": "            due = False         # REG-3198",
     "replace": "            due = True          # REG-3198",
     "matches": 1},
    {"why": "REG-3198 (the reviewer on r3) - the route answers a failed walk as 'computing' for ever",
     "file": "tv/control_app.py",
     "find": "                    if _lr is None and _lf is not None:\n",
     "replace": "                    if False:\n",
     "matches": 1},
    {"why": "REG-3198 (the reviewer on r3) - the lane counts a refused (failed) walk as a read",
     "file": "tv/control_app.py",
     "find": "        _refused = _river_warm_refusal(_final)\n",
     "replace": "        _refused = None\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
