# -*- coding: utf-8 -*-
"""v3849 — every beacon states whether its tally reported onOwnerSeed.

The ALT sent onOwnerSeed null, and every ledger read UNKNOWN, because the beacon never said
whether that null was measured or simply omitted. _tally_cached stamps a copy:

  measured   — the tally carried true or false
  absent     — the key was present and null, or not a boolean
  unreported — the key was omitted; onOwnerSeed is then stated as None

A null is never rewritten into true, and classify_row still says UNKNOWN. The worker forwards
only those three words. The beacon still sends "tally": _tally_cached().
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

_WORLD = tempfile.mkdtemp(prefix="seed_provenance_")
os.environ["TV_HIST"] = _WORLD
os.environ["TV_SESSIONS"] = os.path.join(_WORLD, "sessions.jsonl")
os.environ["TVD_NO_BEACON"] = "1"

import control_app as ca  # noqa: E402
import ledger_authority as la  # noqa: E402
import worker_source as _ws  # noqa: E402
from cb_node_harness import NODE  # noqa: E402

WORKER = os.path.join(ROOT, "functions", "api", "console.js")


def _need_node():
    if not NODE:
        raise AssertionError("node is not on this machine - this gate does not skip")
    return NODE


def _table():
    seeds = {}
    for name in ("_GRAIL_SEED", "_RULING_SEED", "_SET_SEED", "_RWC_SEED"):
        seeds[name] = {"names": ["One"], "n": 1, "line": 1, "newestFindDate": None}
    return {"ok": True, "seeds": seeds}


def _tally(seed="omit", have=0):
    t = {"ok": True, "at": 1700000000000,
         "sets": {"have": have, "total": 2},
         "uniques": {"have": have, "total": 2},
         "runewords": {"have": have, "total": 2}}
    if seed != "omit":
        t["onOwnerSeed"] = seed
    return t


def _words(tally):
    v = la.classify_row(tally, table=_table())
    return dict((row["ledger"], row["provenance"]) for row in v["ledgers"])


def _shape(tally):
    with io.open(WORKER, encoding="utf-8") as fh:
        src = fh.read()
    start = "    tally: (function (t) {"
    end = "    })(body.tally),"
    if src.count(start) != 1 or src.count(end) != 1:
        raise AssertionError("the tally shaper anchors are not unique")
    i = src.index(start)
    fn = "(" + src[i + len("    tally: "):src.index(end, i) + len("    })")] + ")"
    js = _ws.prelude(src) + "var shape = %s;\nconsole.log(JSON.stringify(shape(%s)));" % (fn, json.dumps(tally))
    r = subprocess.run([_need_node(), "-"], input=js, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("node could not run the tally shaper: %s" % r.stderr[-500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


class TestEveryBeaconStatesSeedProvenance(unittest.TestCase):
    def setUp(self):
        self._cache = dict(ca._TALLY_CACHE)
        ca._TALLY_CACHE.update(t=0.0, val=None)

    def tearDown(self):
        ca._TALLY_CACHE.clear()
        ca._TALLY_CACHE.update(self._cache)

    def _cached(self, tally, calls):
        def grail():
            calls.append(1)
            return dict(tally)
        with mock.patch.object(ca, "grail_tally", grail):
            one = ca._tally_cached()
            two = ca._tally_cached()
        return one, two

    def test_a_null_is_absent_and_every_ledger_stays_unknown(self):
        calls = []
        one, two = self._cached(_tally(None, have=4), calls)
        self.assertEqual(calls, [1])
        for got in (one, two):
            self.assertIsNone(got["onOwnerSeed"])
            self.assertEqual(got["onOwnerSeedProvenance"], "absent")
        self.assertNotIn("onOwnerSeedProvenance", ca._TALLY_CACHE["val"])
        self.assertIsNone(ca._TALLY_CACHE["val"].get("onOwnerSeed"))
        words = _words(one)
        self.assertTrue(words)
        for ledger, word in words.items():
            self.assertEqual(word, "UNKNOWN", ledger)

    def test_a_boolean_is_measured_and_keeps_its_own_verdict(self):
        one, _ = self._cached(_tally(False, have=0), [])
        self.assertIs(one["onOwnerSeed"], False)
        self.assertEqual(one["onOwnerSeedProvenance"], "measured")
        for ledger, word in _words(one).items():
            self.assertEqual(word, "UNSYNCED", ledger)
        ca._TALLY_CACHE.update(t=0.0, val=None)
        seeded, _ = self._cached(_tally(True, have=4), [])
        self.assertIs(seeded["onOwnerSeed"], True)
        self.assertEqual(seeded["onOwnerSeedProvenance"], "measured")
        for ledger, word in _words(seeded).items():
            self.assertEqual(word, "SEEDED", ledger)

    def test_an_omitted_flag_is_unreported_and_a_junk_flag_is_absent(self):
        one, two = self._cached(_tally("omit"), [])
        self.assertEqual(one["onOwnerSeedProvenance"], "unreported")
        self.assertIsNone(one["onOwnerSeed"])
        self.assertEqual(two["onOwnerSeedProvenance"], "unreported")
        self.assertNotIn("onOwnerSeed", ca._TALLY_CACHE["val"])
        for word in _words(one).values():
            self.assertEqual(word, "UNKNOWN")
        ca._TALLY_CACHE.update(t=0.0, val=None)
        junk, _ = self._cached(_tally("false"), [])
        self.assertIsNone(junk["onOwnerSeed"])
        self.assertEqual(junk["onOwnerSeedProvenance"], "absent")
        for word in _words(junk).values():
            self.assertNotIn(word, ("SYNCED", "SEEDED", "MANUAL"))

    def test_a_tally_that_raises_still_states_a_word(self):
        def boom():
            raise RuntimeError("board down")
        with mock.patch.object(ca, "grail_tally", boom):
            got = ca._tally_cached()
        self.assertIs(got["ok"], False)
        self.assertEqual(got["onOwnerSeedProvenance"], "unreported")
        self.assertIsNone(got["onOwnerSeed"])

    def test_the_beacon_still_sends_the_cached_tally_and_the_worker_forwards_the_word(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count('"tally": _tally_cached(),'), 1)
        base = _tally(None, have=1)
        for word in ("measured", "absent", "unreported"):
            body = dict(base, onOwnerSeed=False if word == "measured" else None, onOwnerSeedProvenance=word)
            out = _shape(body)
            self.assertEqual(out.get("onOwnerSeedProvenance"), word)
            self.assertIs(out.get("onOwnerSeed"), False if word == "measured" else None)
        self.assertIsNone(_shape(dict(base, onOwnerSeed=None, onOwnerSeedProvenance="SYNCED")).get("onOwnerSeedProvenance"))
        self.assertIsNone(_shape(dict(base, onOwnerSeed=None, onOwnerSeedProvenance="SEEDED")).get("onOwnerSeed"))
        refused = _shape({"ok": False, "why": "the board refused the read", "at": 1,
                          "onOwnerSeedProvenance": "unreported"})
        self.assertEqual(refused.get("onOwnerSeedProvenance"), "unreported")
        self.assertIs(refused.get("ok"), False)

    def test_the_red_proof_finds_match_once(self):
        for proof in RED_PROOF:
            with io.open(os.path.join(ROOT, proof["file"]), encoding="utf-8") as fh:
                body = fh.read()
            self.assertEqual(body.count(proof["find"]), proof["matches"], proof["why"])
            self.assertNotEqual(proof["find"], proof["replace"])


RED_PROOF = [
    {"why": "a null seed is reported as measured true, so every ledger can read SEEDED",
     "file": "tv/control_app.py",
     "find": "    else:\n        out[\"onOwnerSeed\"] = None\n        out[\"onOwnerSeedProvenance\"] = \"absent\"\n",
     "replace": "    else:\n        out[\"onOwnerSeed\"] = True\n        out[\"onOwnerSeedProvenance\"] = \"measured\"\n",
     "matches": 1},
    {"why": "the beacon stops stating provenance, so a null and an omission look the same again",
     "file": "tv/control_app.py",
     "find": "    out = dict(tally)\n    flag = out.get(\"onOwnerSeed\")\n",
     "replace": "    out = dict(tally)\n    return out\n    flag = out.get(\"onOwnerSeed\")\n",
     "matches": 1},
    {"why": "the worker drops the word, so the fleet never hears what the beacon stated",
     "file": "functions/api/console.js",
     "find": "      const seedProvenance = (t.onOwnerSeedProvenance === 'measured' || t.onOwnerSeedProvenance === 'absent' || t.onOwnerSeedProvenance === 'unreported') ? t.onOwnerSeedProvenance : null;\n",
     "replace": "      const seedProvenance = null;\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
