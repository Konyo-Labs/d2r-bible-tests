# -*- coding: utf-8 -*-
"""v3849 — an empty self-prove record does not hide a census this PC has already read as shut.

Before the first tick the record has no key, no census and no lastTs, and the beacon used to say
key "starting" with census null. If the disk census is already stale, missing, or unreadable, that
word hid a known shut lock. The beacon then sends that census and key stale-at-boot. The fleet chip
says "locks shut · rechecking". current, unknown, and a raise stay starting with census null.
The disk is asked at most once per process. A record that has already ticked is left as it is.
"""
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

_WORLD = tempfile.mkdtemp(prefix="stale_at_boot_")
os.environ["TV_HIST"] = _WORLD
os.environ["TV_SESSIONS"] = os.path.join(_WORLD, "sessions.jsonl")
os.environ["TVD_NO_BEACON"] = "1"

import self_prove  # noqa: E402
import control_app as ca  # noqa: E402
import worker_source as _ws  # noqa: E402
from cb_node_harness import NODE  # noqa: E402

UI = os.path.join(HERE, "control_ui.html")
WORKER = os.path.join(ROOT, "functions", "api", "console.js")
CHIP = ("  var _fleetStuckChip = function (m, nowMs) {\n", "    return bits.join('');\n  };\n")
EMPTY = {"on": None, "worked": None, "lastTs": None, "owed": None, "key": None,
         "say": "the self-prove lane has not ticked yet since this console started"}


def _need_node():
    if not NODE:
        raise AssertionError("node is not on this machine - this gate does not skip")
    return NODE


def _cut(src, pair):
    start, end = pair
    if src.count(start) != 1:
        raise AssertionError("anchor %r matched %d times" % (start.strip()[:48], src.count(start)))
    i = src.index(start)
    fn = src[i:src.index(end, i) + len(end)]
    if fn.count("{") != fn.count("}"):
        raise AssertionError("the chip cut is not a whole function")
    return fn


def _node(js):
    r = subprocess.run([_need_node(), "-"], input=js, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("node could not run the shipped code: %s" % r.stderr[-600:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _chip(heart, stuck):
    with io.open(UI, encoding="utf-8") as fh:
        src = fh.read()
    js = (
        "function escC(x){ return String(x).replace(/&/g,'&amp;').replace(/\"/g,'&quot;')"
        ".replace(/</g,'&lt;').replace(/>/g,'&gt;'); }\n%s\n"
        "console.log(JSON.stringify(_fleetStuckChip(%s, 0)));"
    ) % (_cut(src, CHIP), json.dumps({"system": {"river": {"stuck": stuck, "heart": heart}}}))
    return _node(js)


def _relay(system):
    with io.open(WORKER, encoding="utf-8") as fh:
        src = fh.read()
    start, end = "    system: (function (s) {", "    })(body.system),"
    if src.count(start) != 1 or src.count(end) != 1:
        raise AssertionError("the system shaper anchors are not unique")
    fn = src[src.index(start):src.index(end, src.index(start)) + len(end)]
    fn = "(" + fn[len("    system: "):-len("(body.system),")] + ")"
    return _node(_ws.prelude(src) + "var shape = %s; console.log(JSON.stringify(shape(%s)));" % (fn, json.dumps(system)))


class TestStartingNeverHidesAKnownStaleCensus(unittest.TestCase):
    def setUp(self):
        self._boot = dict(ca._BOOT_CENSUS)
        ca._BOOT_CENSUS.update(asked=False, state=None)

    def tearDown(self):
        ca._BOOT_CENSUS.clear()
        ca._BOOT_CENSUS.update(self._boot)

    def _hearts(self, answer, record):
        calls = []

        def census():
            calls.append(1)
            if answer == "raise":
                raise RuntimeError("the census file could not be read")
            return answer

        with mock.patch.object(ca, "_SELF_PROVE", record), \
                mock.patch.object(ca, "_RIVER_LAST", {"good": None, "fail": None}), \
                mock.patch.object(self_prove, "census_state", census):
            one = ca._river_for_wire(now_ms=1700000000000)["heart"]
            two = ca._river_for_wire(now_ms=1700000000000)["heart"]
        return one, two, calls

    def test_a_known_shut_census_is_sent_once_as_stale_at_boot(self):
        for word in ("stale", "missing", "unreadable"):
            ca._BOOT_CENSUS.update(asked=False, state=None)
            one, two, calls = self._hearts({"state": word, "why": "read"}, EMPTY)
            self.assertEqual(one, two)
            self.assertEqual(one["census"], word)
            self.assertEqual(one["key"], "stale-at-boot")
            self.assertNotEqual(one["key"], "starting")
            self.assertEqual(calls, [1], "the disk census was asked %d times" % len(calls))

    def test_current_unknown_and_a_raise_stay_starting_with_a_null_census(self):
        for answer in ({"state": "current"}, {"state": "unknown"}, {"state": None},
                       "stale", None, "raise"):
            ca._BOOT_CENSUS.update(asked=False, state=None)
            one, two, calls = self._hearts(answer, EMPTY)
            self.assertIsNone(one["census"], answer)
            self.assertEqual(one["key"], "starting", answer)
            self.assertEqual(one, two)
            self.assertEqual(calls, [1])

    def test_a_record_that_has_already_ticked_is_not_asked_and_keeps_its_key(self):
        record = {"on": True, "worked": 0, "lastTs": 5, "key": "aside-cooldown", "census": "stale"}
        one, _, calls = self._hearts({"state": "missing"}, record)
        self.assertEqual(calls, [])
        self.assertEqual((one["census"], one["key"]), ("stale", "aside-cooldown"))
        partial = {"key": None, "census": None, "lastTs": 5}
        ca._BOOT_CENSUS.update(asked=False, state=None)
        one, _, calls = self._hearts({"state": "missing"}, partial)
        self.assertEqual(calls, [])
        self.assertIsNone(one["key"])

    def test_the_chip_says_rechecking_only_for_that_key(self):
        shut = _chip({"census": "stale", "key": "stale-at-boot", "blind": None}, [])
        self.assertIn("locks shut \u00b7 rechecking", shut)
        self.assertNotIn("starting", shut)
        self.assertNotIn("census waiting for memory", shut)
        plain = _chip({"census": "missing", "key": "aside-cooldown", "blind": None}, [])
        self.assertIn(">locks shut<", plain)
        self.assertNotIn("rechecking", plain)
        memory = _chip({"census": "stale", "key": "low-memory", "blind": None}, [])
        self.assertIn("locks shut \u00b7 census waiting for memory", memory)
        self.assertNotIn("rechecking", memory)
        # v3861 (his fleet screenshot) - the lock chip says what the proof waits on, in a few words, for the keys that have one
        idle = _chip({"census": "stale", "key": "start", "blind": None}, [])
        self.assertIn("locks shut \u00b7 proof waits for an idle PC", idle)
        borrow = _chip({"census": "missing", "key": "takes-fleet", "blind": None}, [])
        self.assertIn("locks shut \u00b7 borrows proofs, proves none", borrow)
        both = _chip({"census": "unreadable", "key": "stale-at-boot", "blind": None}, None)
        self.assertIn("locks shut \u00b7 rechecking", both)
        self.assertIn("river UNKNOWN", both)

    def test_the_worker_forwards_the_key_and_the_census(self):
        got = _relay({"tree": "ok", "reels": 1, "river": {
            "lanes": None, "stuck": None,
            "heart": {"census": "missing", "key": "stale-at-boot", "blind": None}}})
        self.assertEqual(got["river"]["heart"], {"census": "missing", "key": "stale-at-boot", "blind": None})

    def test_the_red_proof_finds_match_once(self):
        for proof in RED_PROOF:
            with io.open(os.path.join(ROOT, proof["file"]), encoding="utf-8") as fh:
                body = fh.read()
            self.assertEqual(body.count(proof["find"]), proof["matches"], proof["why"])
            self.assertNotEqual(proof["find"], proof["replace"])


RED_PROOF = [
    {"why": "v3861 - the lock chip loses its few words of why: 'locks shut' and nothing about what the proof waits on",
     "file": "tv/control_ui.html",
     "find": "'locks shut')) + _lw\n",
     "replace": "'locks shut'))\n",
     "matches": 1},
    {"why": "a known shut census is hidden behind starting again",
     "file": "tv/control_app.py",
     "find": "        if _shut in (\"stale\", \"missing\", \"unreadable\"):\n            _census = _shut\n            _key = \"stale-at-boot\"\n",
     "replace": "        if False:\n            _census = _shut\n            _key = \"stale-at-boot\"\n",
     "matches": 1},
    {"why": "the disk census is asked on every beacon instead of once per process",
     "file": "tv/control_app.py",
     "find": "    if _BOOT_CENSUS[\"asked\"]:\n        return _BOOT_CENSUS[\"state\"]\n",
     "replace": "    if False:\n        return _BOOT_CENSUS[\"state\"]\n",
     "matches": 1},
    {"why": "the fleet row says a bare locks shut for a census already read at boot",
     "file": "tv/control_ui.html",
     "find": "(_recheck ? 'locks shut \\u00b7 rechecking' : 'locks shut')",
     "replace": "'locks shut'",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
