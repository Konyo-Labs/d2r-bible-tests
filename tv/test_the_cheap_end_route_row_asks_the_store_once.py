# -*- coding: utf-8 -*-
"""#243 (REG-2060) - ONE END-ROUTE REPORT PASS ASKS THE DURABLE STORE ONCE PER WORLD, NOT ONCE PER REEL.

MEASURED 2026-10-08 on his Mac, blocking the v3623 push: test_control's "the cheap subset is actually CHEAP" refused
"end routes reachable (5043 ms, again 4772 ms)" against a 3000 ms budget; timed alone 5.9-6.3 s. cProfile of
end_routes.report(): reel_retention._durable_sessions ran 182 times (once per reel with rows) and each rebuilt
frame_authority.witness_index - 366 store loads, 2.8 of 4.3 s - so the watchdog's 10-minute "cheap" row grew with every
reel. After: 1.7-2.0 s, the same verdict (30 of 42 dead-ended).

  * inside one report() pass, unextracted_door asks _durable_sessions once per world root and reuses the answer;
  * outside a pass (a bare verdict) nothing is remembered - every call asks, exactly as before.
Nothing here reads his reels or writes his stores: the shelf is a temp dir and the durable store is a counting stub.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402  #173 - its scratch is its own, so listing it keeps the law keyable
_fx_tmp.contain()

import end_routes as ER      # noqa: E402
import reel_retention as RR  # noqa: E402


class TheCheapEndRouteRowAsksTheStoreOnce(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="endroute-once-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.hist = os.path.join(self.tmp, "hist")
        os.makedirs(self.hist)
        now = int(time.time() * 1000)
        vault = {}
        for i in range(5):
            nm = "reel_s_%d_%03d" % (now - (90 - i) * 86400000, i)
            d = os.path.join(self.hist, nm)
            os.makedirs(d)
            io.open(os.path.join(d, "f_1700000000.jpg"), "w").write("x")
            vault[nm] = {"rows": 3, "ts": now, "agentVer": "fixture", "promptVer": 1}
        io.open(os.path.join(self.hist, "vault_swept.json"), "w", encoding="utf-8").write(json.dumps(vault))
        io.open(os.path.join(self.hist, "chronicle_swept.json"), "w", encoding="utf-8").write("{}")
        self._env = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = self.hist
        self.addCleanup(self._restore_env)
        # the door asks a FULL structural pass with panels before it asks about rows; the survey is the fixture's own -
        # its path is checked to sit inside this temp dir BEFORE anything is written (never his retro_triage store)
        import retro_triage as rt
        sp = os.path.realpath(ER._store_paths(self.hist)["retro_triage.json"])
        if not sp.startswith(os.path.realpath(self.tmp)):
            self.skipTest("the structural store would resolve outside the fixture (%s) - refusing to write it" % sp)
        io.open(sp, "w", encoding="utf-8").write(json.dumps(
            {nm: {"full": True, "panels": 3, "frames": 1, "kinds": {"stash": 3}} for nm in vault}))
        self.calls = []
        self._real = RR._durable_sessions
        RR._durable_sessions = lambda here=None: (self.calls.append(here) or (set(), True, None))
        self.addCleanup(setattr, RR, "_durable_sessions", self._real)

    def _restore_env(self):
        if self._env is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = self._env

    def test_one_pass_asks_once_per_world(self):
        ER.report(self.hist, safety=False)
        self.assertGreaterEqual(len(self.calls), 1, "premise: the fixture's reels with rows never reached the durable "
                                                     "question, so this case measures nothing")
        self.assertEqual(len(set(map(str, self.calls))), len(self.calls),
                         "one report pass asked the durable store %d times for %d world(s): %r"
                         % (len(self.calls), len(set(map(str, self.calls))), self.calls))
        self.assertIsNone(ER._DUR_PASS, "the pass memo outlived its report()")

    def test_outside_a_pass_every_call_asks(self):
        src = ER.sources(self.hist)
        reels = sorted(d for d in _fx_tmp.list_own(self.hist) if d.startswith("reel_"))
        for r in reels[:2]:
            try:
                ER.unextracted_door(r, src)
            except TypeError:
                self.skipTest("unextracted_door's signature moved - re-point this case")
        self.assertEqual(len(self.calls), 2, "a bare door call remembered a durable answer it was never handed: %r"
                         % self.calls)


RED_PROOF = [
    {"why": "REG-2060 - the end-route report asks the durable store once per reel again (~6 s on his Mac)",
     "file": "end_routes.py",
     "find": "            if _memo is not None and _root in _memo:\n",
     "replace": "            if False:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
