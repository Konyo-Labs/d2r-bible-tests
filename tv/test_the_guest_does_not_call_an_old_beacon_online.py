# -*- coding: utf-8 -*-
"""REG-3199 - THE SHADOW BAR NEVER CALLS AN OLD BEACON "ONLINE NOW".

GrokBot's report 2026-11-05 (his live screen, the GUEST console's shadow bar): "Dean · online now" over a board hours
old - while his /api/fleet at 21:01 had Dean's last beacon at 02:49, ~18 h before. Two holes let that through:
  * the bar's words (console_snapshot.view) took "online" from whoever asked, with no test of the beacon's own age, and
    called a console that was only RECORDING (its recorder alive, the console down) "online now" too;
  * the bar was painted ONCE, when the shadow opened, and never asked again - a shadow left open kept "online now" for
    as long as it stayed open.

Now:
  * view() tests "online now" against the one presence bound (fleet_presence.STALE_AFTER_S) with the beacon's own time
    (seen): a known beacon older than the bound is "offline" whatever list the row came from; a recorder-only presence
    says "online · recording"; no beacon time leaves the caller's answer as it was (unread is not evidence);
  * the view sends seenMs and liveUntil (seen + the bound), _shadowFillFromRoster hands them on, and the bar
    (_shadowLiveWords, the REAL function in node) re-tests the words at paint and every 30 s while it stays open;
  * _profile_view passes the presence's `via` (console / recorder) beside online and seen.

The adversarial review of this item reproduced two more holes, closed here too:
  * THE RE-TEST FROZE ITS OWN AGE. Each 30 s tick tested the bar's CURRENT words, so once " · online now" had become
    "offline · last seen 9 min ago" no later tick found the claim, and "9 min ago" stood for hours. The bar keeps the
    words as the view painted them (live.base) and each tick re-derives from those; a bar someone else repainted since
    (a new shadow opening) is left alone (live.painted).
  * "ONLINE · RECORDING" WAS NEVER RE-TESTED - and could not be, because liveUntil was the CONSOLE's beacon + bound,
    which is old exactly when the recorder is what keeps the owner online. The console now reads the time of the
    check-in presence stands on (live_at_of: the recorder's own report when via is recorder), view() tests both claims
    against it and sends it as liveAt, and the bar re-tests "online · recording" exactly like "online now".
RED_PROOF below.
"""
import datetime
import io
import json
import os
import subprocess
import sys
import tempfile
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
import console_snapshot as CS  # noqa: E402
import fleet_presence as FP  # noqa: E402
from cb_node_harness import NODE  # noqa: E402

UI = os.path.join(HERE, "control_ui.html")
OWNER = "Dean"
NOW = 1793900000000
H18 = 18 * 3600 * 1000
BOUND = FP.STALE_AFTER_S * 1000


def _iso(ms):
    return datetime.datetime.fromtimestamp(ms / 1000.0, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _rec(t=NOW - 30 * 3600 * 1000):
    stores = {"d2r_charBuilds": json.dumps({"s0": {"name": "Hammerdin"}})}
    return {"owner": OWNER, "t": t, "hash": CS.digest(stores), "stores": stores}


class TheWordsTestTheBeacon(unittest.TestCase):

    def test_an_18_hour_old_beacon_is_not_online_now(self):
        v = CS.view(OWNER, _rec(), NOW, online=True, seen=NOW - H18)
        self.assertNotIn("online now", v["words"], "an 18 h old beacon was called online now: %r" % v["words"])
        self.assertTrue(v["words"].startswith("Dean · offline · board uploaded"), v["words"])
        self.assertEqual(v["state"], "offline")
        self.assertIsNone(v["liveUntil"])
        self.assertEqual(v["seenMs"], NOW - H18)

    def test_a_fresh_beacon_is_online_now_until_its_bound(self):
        seen = NOW - 60 * 1000
        v = CS.view(OWNER, _rec(), NOW, online=True, seen=seen)
        self.assertTrue(v["words"].startswith("Dean · online now · board uploaded"), v["words"])
        self.assertEqual(v["liveUntil"], seen + BOUND)
        at_bound = CS.view(OWNER, _rec(), seen + BOUND, online=True, seen=seen)
        self.assertEqual(at_bound["state"], "live", "a beacon exactly at the bound went offline early")
        past = CS.view(OWNER, _rec(), seen + BOUND + 1000, online=True, seen=seen)
        self.assertEqual(past["state"], "offline", "a beacon past the bound stayed online now")

    def test_no_beacon_time_leaves_the_answer_and_a_recorder_is_recording(self):
        v = CS.view(OWNER, _rec(), NOW, online=True)
        self.assertIn("online now", v["words"], "an unread beacon time was taken as evidence of offline")
        self.assertIsNone(v["liveUntil"])
        r = CS.view(OWNER, _rec(), NOW, online=True, seen=NOW - H18, via="recorder")
        self.assertIn("Dean · online · recording · board uploaded", r["words"], r["words"])
        self.assertNotIn("online now", r["words"], "a console that is only recording was called online now")

    def test_recording_is_tested_against_the_recorders_own_report(self):
        rec_at = NOW - 60 * 1000
        r = CS.view(OWNER, _rec(), NOW, online=True, seen=NOW - H18, via="recorder", live_at=rec_at)
        self.assertIn("online · recording", r["words"])
        self.assertEqual(r["liveAt"], rec_at)
        self.assertEqual(r["liveUntil"], rec_at + BOUND,
                         "recording's bound was the console's 18 h old beacon - the bar would call it offline at once")
        dead = CS.view(OWNER, _rec(), NOW, online=True, seen=NOW - H18, via="recorder", live_at=NOW - H18)
        self.assertEqual(dead["state"], "offline", "a recorder silent for 18 h was still recording: %r" % dead["words"])
        row = {"nickname": "Dean", "platform": "windows", "t": _iso(NOW - H18),
               "recorder": {"alive": True, "t": _iso(rec_at)}}
        fleet = {"ok": True, "online": [row], "offline": []}
        self.assertEqual(CS.live_at_of(OWNER, fleet, NOW), rec_at, "the recorder's own time was not read")
        live = dict(row, t=_iso(NOW - 30 * 1000), recorder=None)
        self.assertEqual(CS.live_at_of(OWNER, {"ok": True, "online": [live], "offline": []}, NOW), NOW - 30 * 1000)
        self.assertIsNone(CS.live_at_of(OWNER, {"ok": True, "online": [], "offline": [dict(row, recorder=None)]}, NOW))
        self.assertEqual(CS.beacon_stale(None, NOW), False)
        self.assertEqual(CS.beacon_stale(NOW - BOUND - 1, NOW), True)
        self.assertEqual(CS.beacon_stale(NOW - BOUND, NOW), False)


class TheConsoleAsksTheSameRow(unittest.TestCase):

    def _view(self, row, listed_online):
        import control_app as CA
        fleet = {"ok": True, "online": [row] if listed_online else [], "offline": [] if listed_online else [row]}
        d = tempfile.mkdtemp(prefix="r3199-")
        try:
            CS.write_cache(d, _rec())
            with mock.patch.object(CA, "_beacon_suppressed_by", lambda: "TVD_NO_BEACON"), \
                    mock.patch.object(CA, "_profile_cache_dir", lambda: d), \
                    mock.patch.object(CA, "fleet_presence_last_good", lambda: (fleet, 1.0)), \
                    mock.patch.object(CA.time, "time", lambda: NOW / 1000.0), \
                    mock.patch.object(FP.time, "time", lambda: NOW / 1000.0):
                return CA._profile_view(OWNER)
        finally:
            import shutil
            shutil.rmtree(d, True)

    def test_dean_listed_online_18_hours_after_his_beacon_is_offline(self):
        row = {"nickname": "Dean", "platform": "windows", "t": _iso(NOW - H18)}
        v = self._view(row, True)
        self.assertTrue(v.get("ok"), v)
        self.assertNotIn("online now", v["words"], "the bar called Dean online now 18 h after his beacon: %r" % v["words"])
        self.assertIn("offline", v["words"])

    def test_a_recorder_only_presence_reaches_the_bar_as_recording(self):
        row = {"nickname": "Dean", "platform": "windows", "t": _iso(NOW - H18),
               "recorder": {"alive": True, "t": _iso(NOW - 60 * 1000)}}
        v = self._view(row, True)
        self.assertIn("online · recording", v["words"], "the presence's own word never reached the bar: %r" % v["words"])
        self.assertEqual(v["liveAt"], NOW - 60 * 1000, "the console never handed the recorder's time to the bar")
        self.assertEqual(v["liveUntil"], NOW - 60 * 1000 + BOUND)
        with mock.patch.object(FP.time, "time", lambda: NOW / 1000.0):
            self.assertEqual(CS.via_of(OWNER, {"ok": True, "online": [row], "offline": []}), "recorder")


def _live_words(cases):
    with io.open(UI, encoding="utf-8") as fh:
        src = fh.read()
    a = "  window._shadowLiveWords = function (words, live, nowMs) {\n"
    if src.count(a) != 1:
        raise AssertionError("_shadowLiveWords anchor matched %d times" % src.count(a))
    i = src.index(a)
    fn = src[i:src.index("\n  };\n", i) + len("\n  };\n")]
    js = "var window = {};\n%s\nconsole.log(JSON.stringify(%s.map(function (c) { return window._shadowLiveWords(c[0], c[1], c[2]); })));" % (
        fn, json.dumps(cases))
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError("_shadowLiveWords did not run in node: %s" % r.stderr[-600:])
    return json.loads(r.stdout.strip().splitlines()[-1])


@unittest.skipIf(NODE is None, "node is not on this machine - this law RUNS the shipped function and will not re-implement it")
class TheBarAsksAgain(unittest.TestCase):

    def test_the_bar_retests_online_now(self):
        w = "Dean · online now · board uploaded 30 hr ago · snapshot Nov 4 11:33 · read only"
        seen = NOW - 60 * 1000
        live = {"seenMs": seen, "liveUntil": seen + BOUND}
        got = _live_words([[w, live, NOW], [w, live, NOW + H18], [w, {}, NOW],
                           ["Dean · offline · board uploaded 30 hr ago", live, NOW + H18]])
        self.assertEqual(got[0], w, "a beacon inside its bound lost online now")
        self.assertEqual(got[1], "Dean · offline · last seen 18 hr ago · board uploaded 30 hr ago · snapshot Nov 4 11:33 · read only",
                         "a bar left open kept online now: %r" % got[1])
        self.assertIn("online UNKNOWN", got[2], "online now with no clock to test it by stayed online now")
        self.assertEqual(got[3], "Dean · offline · board uploaded 30 hr ago")

    def test_recording_is_re_tested_and_the_age_keeps_counting(self):
        rec = "Dean · online · recording · board uploaded 30 hr ago · read only"
        rec_at = NOW - 60 * 1000
        live = {"seenMs": NOW - H18, "liveAt": rec_at, "liveUntil": rec_at + BOUND}
        got = _live_words([[rec, live, NOW], [rec, live, NOW + 3 * 3600 * 1000]])
        self.assertEqual(got[0], rec, "a recorder inside its bound lost 'recording'")
        self.assertEqual(got[1], "Dean · offline · last seen 3 hr ago · board uploaded 30 hr ago · read only",
                         "a dead recorder kept 'online · recording': %r" % got[1])
        # the reviewer's frozen age: the same BASE at two later moments gives two ages, not the first one twice
        w = "Dean · online now · board uploaded 30 hr ago · read only"
        seen = NOW - 60 * 1000
        live = {"seenMs": seen, "liveUntil": seen + BOUND}
        got = _live_words([[w, live, seen + 9 * 60 * 1000], [w, live, seen + 3 * 3600 * 1000]])
        self.assertIn("last seen 9 min ago", got[0])
        self.assertIn("last seen 3 hr ago", got[1], "the bar's age froze at its first rewrite: %r" % got[1])

    def test_the_bar_is_wired_to_it(self):
        with io.open(UI, encoding="utf-8") as fh:
            src = fh.read()
        i = src.index("  window._shadowSnapEnter = function (owner, d) {\n")
        enter = src[i:src.index("\n  };\n", i)]
        line = "    if (who) who.textContent = String(d.words || owner) + at + ' · read only';\n"
        base = ("      var _live = { seenMs: d.seenMs, liveAt: d.liveAt, liveUntil: d.liveUntil, "
                "base: who ? who.textContent : '' };\n")
        call = "      _live.painted = window._shadowLiveWords(_live.base, _live, Date.now());\n"
        tick = "        sn.live.painted = window._shadowLiveWords(sn.live.base, sn.live, Date.now());\n"
        guard = "        if (!(sn && sn.live && el) || el.textContent !== sn.live.painted) return;\n"
        self.assertEqual(enter.count(base), 1, "the bar does not keep the words it was painted with")
        self.assertEqual(enter.count(call), 1, "the bar never re-tests its own online now")
        self.assertLess(enter.index(line), enter.index(base), "the base is taken before the words it keeps are painted")
        self.assertEqual(enter.count(tick), 1, "each tick tests its own last rewrite, so the age freezes")
        self.assertEqual(enter.count(guard), 1, "a tick repaints a bar someone else has repainted since")
        self.assertEqual(enter.count("}, 30000);"), 1, "the bar is tested only once, at entry")
        self.assertEqual(src.count("                     seenMs: snap && snap.seenMs, liveAt: snap && snap.liveAt,"), 1,
                         "the roster fill drops the check-in's clock before the bar can test it")
        self.assertEqual(src.count("                     liveUntil: snap && snap.liveUntil,\n"), 1)

    def test_the_red_proof_finds_match_once(self):
        for p in RED_PROOF:
            with io.open(os.path.join(ROOT, p["file"]), encoding="utf-8") as fh:
                self.assertEqual(fh.read().count(p["find"]), p["matches"], p["why"])


RED_PROOF = [
    {"why": "REG-3199 - the words take 'online' on trust again: Dean's 18 h old beacon reads online now",
     "file": "tv/console_snapshot.py",
     "find": "    if online is True and beacon_stale(_live_at, now_ms):\n        online = False\n",
     "replace": "    if False:\n        online = False\n",
     "matches": 1},
    {"why": "REG-3199 - with no recorder time, the console's beacon is not the time online now stands on",
     "file": "tv/console_snapshot.py",
     "find": "        _live_at = seen\n",
     "replace": "        _live_at = None\n",
     "matches": 1},
    {"why": "REG-3199 (the reviewer on r3) - recording is tested against the console's 18 h old beacon, not its own report",
     "file": "tv/console_snapshot.py",
     "find": "    if pres.get(\"via\") == \"recorder\":\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3199 (the reviewer on r3) - the console never hands the recorder's time to the bar",
     "file": "tv/control_app.py",
     "find": "        live_at = _cs.live_at_of(owner, fl, now_ms)",
     "replace": "        live_at = None",
     "matches": 1},
    {"why": "REG-3199 - the beacon's age is never tested against its bound",
     "file": "tv/console_snapshot.py",
     "find": "    return now_ms - seen_ms > live_bound_ms()\n",
     "replace": "    return False\n",
     "matches": 1},
    {"why": "REG-3199 - a console that is only recording is called online now",
     "file": "tv/console_snapshot.py",
     "find": "    if online is True and via == \"recorder\":\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3199 - the view sends no moment when online now stops being true",
     "file": "tv/console_snapshot.py",
     "find": "\"liveUntil\": (_live_at + live_bound_ms()) if (state == \"live\" and _live_at is not None) else None}",
     "replace": "\"liveUntil\": None}",
     "matches": 1},
    {"why": "REG-3199 - the console never tells the bar HOW the owner is online",
     "file": "tv/control_app.py",
     "find": "source=source, via=via, live_at=live_at, fetch_why=why",
     "replace": "source=source, live_at=live_at, fetch_why=why",
     "matches": 1},
    {"why": "REG-3199 - the bar keeps online now past its bound (painted once, never asked again)",
     "file": "tv/control_ui.html",
     "find": "    if (until !== null && now <= until) return w;\n",
     "replace": "    return w;\n",
     "matches": 1},
    {"why": "REG-3199 - the bar is never re-tested",
     "file": "tv/control_ui.html",
     "find": "      _live.painted = window._shadowLiveWords(_live.base, _live, Date.now());\n",
     "replace": "      _live.painted = _live.base;\n",
     "matches": 1},
    {"why": "REG-3199 (the reviewer on r3) - each tick tests its own last rewrite, so 'last seen 9 min ago' freezes",
     "file": "tv/control_ui.html",
     "find": "        sn.live.painted = window._shadowLiveWords(sn.live.base, sn.live, Date.now());\n",
     "replace": "        sn.live.painted = window._shadowLiveWords(el.textContent, sn.live, Date.now());\n",
     "matches": 1},
    {"why": "REG-3199 (the reviewer on r3) - 'online · recording' is never re-tested",
     "file": "tv/control_ui.html",
     "find": "    if (at < 0) { claim = ' \\u00b7 online \\u00b7 recording'; at = w.indexOf(claim); }\n",
     "replace": "\n",
     "matches": 1},
    {"why": "REG-3199 - the roster fill drops the check-in's clock",
     "file": "tv/control_ui.html",
     "find": "                     liveUntil: snap && snap.liveUntil,\n",
     "replace": "                     liveUntil: null,\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
