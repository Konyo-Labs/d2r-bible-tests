"""REG-1905 - a proof that waits for an idle machine never starts on a machine that is never idle.

GrokBot's PC read "the machine is 77% busy - a proof starts only when it is idle" for 20 DAYS (#230, the v3600 brief,
C2): its own driver keeps it above MAX_BUSY_TO_START around the clock, so its census never went current and its river
stayed shut ("stuck EMPTY 9 for 20d"), while the doctor counted the key "busy" as healthy. The law:

  * an UNBROKEN run of busy refusals is remembered from its first tick (busySince), and any other outcome ends it;
  * the refusal says how long it has been busy and when it will prove anyway;
  * past BUSY_STARVE_S it starts (it already runs at nice 15 / BELOW_NORMAL with 4x deadlines) and says why;
  * he PLAYING still beats it, at any age - the ceiling is about a busy machine, never about his game.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import self_prove as SP  # noqa: E402

INSTALLED = ("installed", "level with origin")
STALE = {"state": "stale", "why": "gates changed", "fingerprint": "abc"}
H = 3600.0


class TheDecision(unittest.TestCase):

    def d(self, mem, busy=77.0, playing=False, now=100 * 86400.0):
        return SP.decide(STALE, INSTALLED, None, busy, mem, now, playing=playing, free=8000)

    def test_a_fresh_busy_run_refuses_and_says_only_idle(self):
        r = self.d({})
        self.assertEqual((r["start"], r["key"]), (False, "busy"))
        self.assertNotIn("busy for", r["why"])

    def test_a_short_busy_run_refuses_and_names_its_age_and_its_ceiling(self):
        now = 100 * 86400.0
        r = self.d({"busySince": int((now - 2 * H) * 1000)}, now=now)
        self.assertEqual((r["start"], r["key"]), (False, "busy"))
        self.assertIn("busy for 2 h", r["why"])
        self.assertIn("past %d h it proves anyway" % (SP.BUSY_STARVE_S // 3600), r["why"])

    def test_a_starved_run_proves_at_the_lowest_priority_and_says_why(self):
        now = 100 * 86400.0
        r = self.d({"busySince": int((now - 20 * 86400) * 1000)}, now=now)
        self.assertTrue(r["start"], "a PC busy for 20 days still refused to prove - its river stays shut for ever: %s"
                        % r["why"])
        self.assertIn("20 d", r["why"])
        self.assertIn("REG-1905", r["why"])

    def test_his_game_beats_the_ceiling_at_any_age(self):
        now = 100 * 86400.0
        r = self.d({"busySince": int((now - 20 * 86400) * 1000)}, now=now, playing=True)
        self.assertEqual((r["start"], r["key"]), (False, "playing"))

    def test_an_unreadable_busy_since_never_claims_starvation(self):
        r = self.d({"busySince": "junk"})
        self.assertEqual((r["start"], r["key"]), (False, "busy"))

    def test_an_idle_machine_is_unchanged(self):
        r = self.d({}, busy=5.0)
        self.assertTrue(r["start"])


class TheTickRemembersTheRun(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="self_prove_busy_")
        self.path = os.path.join(self.dir, ".self_prove.json")
        self.spawned = []
        SP._STARTED.update(pid=None, birth=None)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        SP._STARTED.update(pid=None, birth=None)

    def _spawn(self, log_path, names=None):
        self.spawned.append(log_path)
        return 999_999_7                     # a pid that is not alive

    def tick(self, now, busy):
        return SP.tick(now_s=now, busy=busy, tree=INSTALLED, census=STALE, path=self.path, spawn_fn=self._spawn,
                       env={}, playing=False, free=8000)

    def mem(self):
        with io.open(self.path, encoding="utf-8") as fh:
            return json.load(fh)

    def test_the_first_busy_tick_starts_the_run_and_a_later_one_keeps_it(self):
        self.tick(1000.0, 80.0)
        self.assertEqual(self.mem().get("busySince"), 1000 * 1000)
        self.tick(1600.0, 80.0)
        self.assertEqual(self.mem().get("busySince"), 1000 * 1000, "a later busy tick restarted the run")
        self.assertEqual(self.spawned, [])

    def test_the_run_proves_once_it_passes_the_ceiling(self):
        self.tick(1000.0, 80.0)
        self.tick(1000.0 + SP.BUSY_STARVE_S + 60, 80.0)
        self.assertEqual(len(self.spawned), 1, "a starved busy run never started a proof")
        self.assertIsNone(self.mem().get("busySince"), "a start did not end the busy run")

    def test_any_other_outcome_ends_the_run(self):
        self.tick(1000.0, 80.0)
        SP.tick(now_s=1600.0, busy=80.0, tree=INSTALLED, census=STALE, path=self.path, spawn_fn=self._spawn,
                env={}, playing=True, free=8000)
        self.assertIsNone(self.mem().get("busySince"), "a 'playing' tick did not break the busy run")


RED_PROOF = [
    {
        "why": "REG-1905 - the ceiling is gone: a PC busy for 20 days refuses to prove for ever and its river stays shut",
        "file": "tv/self_prove.py",
        "find": "        if _for is not None and _for >= _starve:\n",   # v3884 - the ceiling reads _starve (REG-3433)
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-1905 - the busy run is never remembered, so no refusal can ever grow old enough to prove",
        "file": "tv/self_prove.py",
        "find": "        if mem.get(\"busySince\") is None:\n            mem[\"busySince\"] = now_ms\n",
        "replace": "        if False:\n            mem[\"busySince\"] = now_ms\n",
        "matches": 1,
    },
    {
        "why": "REG-1905 - the run is never ended by another outcome, so a busy hour weeks ago counts as starvation today",
        "file": "tv/self_prove.py",
        "find": "    else:\n        mem.pop(\"busySince\", None)\n",
        "replace": "    else:\n        pass\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
