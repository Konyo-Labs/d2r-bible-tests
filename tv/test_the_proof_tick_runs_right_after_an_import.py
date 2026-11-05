# -*- coding: utf-8 -*-
"""v3865 REG-3195 - THE SELF-PROVE TICK RUNS ON THE RESCUE TICK RIGHT AFTER AN IMPORT ENDS, ONCE PER ENDING.

MEASURED 2026-11-05 on his Mac: control_app._self_prove_dispatch holds the self-prove tick while GitHub's proofs are being
imported (_PROOF_RELEASE['running'] - v3862, nothing proves what is being imported), and the real tick comes only when
n % SELF_PROVE_EVERY_TICKS (60) == SELF_PROVE_FIRST_TICK (30) on the 10 s rescue loop. So the import ended 20:55:40, two
minutes after the 20:53 tick it had held back, and the proof lane sat dead until 21:02:59. Held here, through the real
_proof_release_tick and _self_prove_dispatch:
  * an import's ending - imported, absent, or raised - is answered by the tick on the very next rescue tick, at ANY n;
  * exactly once per ending: the ticks after it are the ordinary schedule again (never hammering); a second ending is
    answered again;
  * never while an import still runs (an ending counted before `running` clears waits for it);
  * an ending that lands on the ordinary tick's own n runs ONE tick, not two;
  * which ending was answered, and when, is published beside it (tickedFor / tickedAt, ends / endedAt).
Fixtures only: the import, the tick, the guard and the beacon are stubs; git is a stub; no network. RED_PROOF below.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

SHA_A = "a" * 40
SHA_B = "b" * 40


class TheTickAfterAnImport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import control_app as CA
        cls.CA = CA

    def setUp(self):
        CA = self.CA
        self.d = tempfile.mkdtemp(prefix="tick-after-import-")
        self._saved = dict((k, getattr(CA, k)) for k in (
            "_a_push_is_grading", "_sp_proof_playing_here", "HERE", "_self_prove_tick", "_self_prove_guard",
            "_console_beacon_async"))
        self._pr = dict(CA._PROOF_RELEASE)
        self._sp = dict(CA._SELF_PROVE)
        self.ticks, self.guards = [], []
        CA._a_push_is_grading = lambda: False
        CA._sp_proof_playing_here = lambda: False
        CA.HERE = self.d                       # the import's state file lives in the scratch dir
        CA._self_prove_tick = lambda: self.ticks.append(1)
        CA._self_prove_guard = lambda: self.guards.append(1)
        CA._console_beacon_async = lambda e: None
        CA._PROOF_RELEASE.update(running=False, state=None, sha=None)
        CA._SELF_PROVE.clear()
        CA._SELF_PROVE.update(running=False, key=None)      # no proof running: no guard steps in between
        self.head = SHA_A

    def tearDown(self):
        CA = self.CA
        for k, v in self._saved.items():
            setattr(CA, k, v)
        CA._PROOF_RELEASE.clear()
        CA._PROOF_RELEASE.update(self._pr)
        CA._SELF_PROVE.clear()
        CA._SELF_PROVE.update(self._sp)
        shutil.rmtree(self.d, ignore_errors=True)

    def _git(self, argv, **kw):
        if argv[1:3] == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(argv, 0, self.head + "\n", "")
        if argv[1] == "status":
            return subprocess.CompletedProcess(argv, 0, "", "")
        raise AssertionError(argv)

    def _import(self, outcome, thread=None):
        """one real _proof_release_tick whose import ends with `outcome` (a state, or an exception to raise)"""
        def imp(sha, tv_dir=None):
            if isinstance(outcome, Exception):
                raise outcome
            return {"state": outcome, "sha": sha, "why": outcome, "seconds": 1.0, "at": 1,
                    "imported": [""] if outcome == "imported" else []}
        return self.CA._proof_release_tick(_thread=thread or (lambda f: f()), _import=imp, _git_run=self._git)

    def _base(self):
        """a rescue tick n that is not the ordinary proof tick"""
        CA = self.CA
        n = CA.SELF_PROVE_FIRST_TICK + 7
        self.assertNotEqual(n % CA.SELF_PROVE_EVERY_TICKS, CA.SELF_PROVE_FIRST_TICK)
        return n

    def test_an_ending_is_answered_on_the_next_rescue_tick_at_any_n(self):
        CA, n = self.CA, self._base()
        CA._self_prove_dispatch(n)
        self.assertEqual(self.ticks, [], "the fixture's own tick n ran the proof tick before any import")
        ends0 = int(CA._PROOF_RELEASE.get("ends") or 0)
        self._import("imported")
        self.assertFalse(CA._PROOF_RELEASE["running"])
        self.assertEqual(CA._PROOF_RELEASE["ends"], ends0 + 1, "the finished import was not counted as an ending")
        self.assertIsInstance(CA._PROOF_RELEASE["endedAt"], int)
        self.assertEqual(CA._self_prove_dispatch(n + 1), "tick")
        self.assertEqual(self.ticks, [1], "the import ended and the proof tick waited for its 10-minute slot")
        self.assertEqual(CA._PROOF_RELEASE["tickedFor"], ends0 + 1)
        self.assertIsInstance(CA._PROOF_RELEASE["tickedAt"], int)
        for k in range(2, 8):
            CA._self_prove_dispatch(n + k)
        self.assertEqual(self.ticks, [1], "the tick after the import ran again and again (hammering)")

    def test_every_kind_of_ending_is_answered_once_each(self):
        CA, n = self.CA, self._base()
        self._import("absent")
        CA._self_prove_dispatch(n)
        CA._self_prove_dispatch(n + 1)
        self.assertEqual(self.ticks, [1], "an import GitHub had no bundle for was not answered exactly once")
        self.head = SHA_B                        # another commit: owed again
        self._import(RuntimeError("the import raised"))
        self.assertEqual(CA._PROOF_RELEASE["state"], "unknown")
        CA._self_prove_dispatch(n + 2)
        CA._self_prove_dispatch(n + 3)
        self.assertEqual(self.ticks, [1, 1], "an import that raised was not answered exactly once")

    def test_never_while_an_import_still_runs(self):
        CA, n = self.CA, self._base()
        held = []
        self._import("imported", thread=held.append)          # started, not finished
        self.assertTrue(CA._PROOF_RELEASE["running"])
        CA._self_prove_dispatch(n)
        CA._self_prove_dispatch(CA.SELF_PROVE_FIRST_TICK + CA.SELF_PROVE_EVERY_TICKS)   # the ordinary tick: held
        self.assertEqual(self.ticks, [], "a proof tick ran beside the import of the same proofs")
        CA._PROOF_RELEASE["ends"] = int(CA._PROOF_RELEASE.get("ends") or 0) + 1         # counted, not yet cleared
        CA._self_prove_dispatch(n + 1)
        self.assertEqual(self.ticks, [], "the tick ran while the import still said running")
        CA._PROOF_RELEASE["ends"] -= 1
        held[0]()                                               # the import ends
        CA._self_prove_dispatch(n + 2)
        CA._self_prove_dispatch(n + 3)
        self.assertEqual(self.ticks, [1], "the ending that waited for `running` to clear was never answered once")

    def test_an_ending_on_the_ordinary_tick_runs_one_tick_not_two(self):
        CA = self.CA
        self._import("imported")
        on = CA.SELF_PROVE_FIRST_TICK + CA.SELF_PROVE_EVERY_TICKS
        CA._self_prove_dispatch(on)
        CA._self_prove_dispatch(on + 1)
        self.assertEqual(self.ticks, [1])

    def test_the_rescue_loop_asks_the_dispatch_every_tick(self):
        import inspect
        src = "\n".join(re.sub(r"\s+#.*$", "", ln) for ln in inspect.getsource(self.CA._console_rescue_loop).split("\n"))
        self.assertEqual(src.count("_self_prove_dispatch(_SELF_PROBE[\"tick\"])"), 1)


RED_PROOF = [
    {"why": "v3865 REG-3195 - the import's ending is not answered: the lane waits for its 10-minute slot (21:02:59)",
     "file": "tv/control_app.py",
     "find": "    if _self_prove_after_import(_PROOF_RELEASE):    # v3865 REG-3195",
     "replace": "    if False:    # v3865 REG-3195",
     "matches": 1},
    {"why": "v3865 REG-3195 - the answered ending is never recorded, so the tick runs on every rescue tick (hammering)",
     "file": "tv/control_app.py",
     "find": "        _PROOF_RELEASE.update(tickedFor=int(_PROOF_RELEASE.get(\"ends\") or 0), tickedAt=int(time.time() * 1000))",
     "replace": "        _PROOF_RELEASE.update(tickedAt=int(time.time() * 1000))",
     "matches": 1},
    {"why": "v3865 REG-3195 - an ending is answered while an import still runs, so the tick is spent and never runs",
     "file": "tv/control_app.py",
     "find": "    return (not pr.get(\"running\")) and int(pr.get(\"ends\") or 0) != int(pr.get(\"tickedFor\") or 0)",
     "replace": "    return int(pr.get(\"ends\") or 0) != int(pr.get(\"tickedFor\") or 0)",
     "matches": 1},
    {"why": "v3865 REG-3195 - a finished import is never counted as an ending",
     "file": "tv/control_app.py",
     "find": "            _PROOF_RELEASE.update(etaS=None, ends=int(_PROOF_RELEASE.get(\"ends\") or 0) + 1,\n",
     "replace": "            _PROOF_RELEASE.update(etaS=None,\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
