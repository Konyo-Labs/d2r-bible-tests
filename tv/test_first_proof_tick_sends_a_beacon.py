# -*- coding: utf-8 -*-
"""v3849 — the first self-prove tick sends one beacon, so the fleet row's "river · starting" can clear.

The rescue loop's first proof lands at SELF_PROVE_FIRST_TICK (~5 min). Until a beacon leaves after that tick,
every other PC keeps the boot chip. A later tick (FIRST + EVERY) and a guard tick send nothing: one beacon,
after the tick, and only for that first number.
"""
import inspect
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

_WORLD = tempfile.mkdtemp(prefix="first_proof_beacon_")
os.environ["TV_HIST"] = _WORLD
os.environ["TV_SESSIONS"] = os.path.join(_WORLD, "sessions.jsonl")
os.environ["TVD_NO_BEACON"] = "1"

import control_app as ca  # noqa: E402

ROOT = os.path.dirname(HERE)


def _order_for(ns):
    order = []

    def tick():
        order.append("tick")

    def guard():
        order.append("guard")

    def beacon(event):
        order.append(("beacon", event))

    with mock.patch.object(ca, "_self_prove_tick", tick), \
            mock.patch.object(ca, "_self_prove_guard", guard), \
            mock.patch.object(ca, "_console_beacon_async", beacon), \
            mock.patch.dict(ca._SELF_PROVE, {"running": True, "key": "running"}, clear=True):
        steps = [ca._self_prove_dispatch(n) for n in ns]
    return steps, order


class TestFirstProofTickSendsABeacon(unittest.TestCase):
    def test_only_the_first_tick_sends_one_beacon_after_the_tick(self):
        first, every = ca.SELF_PROVE_FIRST_TICK, ca.SELF_PROVE_EVERY_TICKS
        steps, order = _order_for([first, first + 1, first + every])
        self.assertEqual(steps, ["tick", "guard", "tick"])
        self.assertEqual(order, ["tick", ("beacon", "proof"), "guard", "tick"])

    def test_an_idle_tick_that_is_not_the_first_sends_nothing(self):
        with mock.patch.object(ca, "_self_prove_tick", lambda: None), \
                mock.patch.object(ca, "_console_beacon_async", lambda event: self.fail(event)), \
                mock.patch.dict(ca._SELF_PROVE, {"running": False, "key": "current"}, clear=True):
            self.assertIsNone(ca._self_prove_dispatch(ca.SELF_PROVE_FIRST_TICK + 1))

    def test_a_second_pass_of_the_first_number_sends_one_beacon_each_time(self):
        first = ca.SELF_PROVE_FIRST_TICK
        steps, order = _order_for([first, first])
        self.assertEqual(steps, ["tick", "tick"])
        self.assertEqual(order, ["tick", ("beacon", "proof"), "tick", ("beacon", "proof")])

    def test_the_beacon_sits_after_the_tick_and_the_red_proof_matches_once(self):
        src = inspect.getsource(ca._self_prove_dispatch)
        tick_at = src.index("_self_prove_tick()")
        beacon_at = src.index('_console_beacon_async("proof")')
        guard_at = src.index("_self_prove_guard()")
        self.assertLess(tick_at, beacon_at)
        self.assertLess(beacon_at, guard_at)
        self.assertEqual(src.count('_console_beacon_async("proof")'), 1)
        with open(os.path.join(ROOT, "tv", "control_app.py"), encoding="utf-8") as fh:
            app = fh.read()
        for proof in RED_PROOF:
            with open(os.path.join(ROOT, proof["file"]), encoding="utf-8") as fh:
                body = fh.read()
            self.assertEqual(body.count(proof["find"]), proof["matches"], proof["why"])
            self.assertNotEqual(proof["find"], proof["replace"])
        self.assertIn(RED_PROOF[0]["find"], app)


RED_PROOF = [
    {"why": "the first proof tick stays silent, so the fleet row keeps saying river · starting",
     "file": "tv/control_app.py",
     "find": "        if n == SELF_PROVE_FIRST_TICK:\n            _console_beacon_async(\"proof\")  # v3849 — one beacon, so the fleet row drops \"river · starting\"\n",
     "replace": "",
     "matches": 1},
    {"why": "every later tick beacons too, so a proof that is not the first one still phones the fleet",
     "file": "tv/control_app.py",
     "find": "        if n == SELF_PROVE_FIRST_TICK:\n            _console_beacon_async(\"proof\")  # v3849 — one beacon, so the fleet row drops \"river · starting\"\n",
     "replace": "        _console_beacon_async(\"proof\")  # v3849 — one beacon, so the fleet row drops \"river · starting\"\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
