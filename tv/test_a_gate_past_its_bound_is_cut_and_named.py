# -*- coding: utf-8 -*-
"""REG-3212 - A PROOF RUN BOUNDS ITSELF INSIDE HIS 75 MINUTES: A GATE PAST ITS BOUND IS CUT, RECORDED TIMEOUT, AND NAMED.

His words (2026-11-05): "2hr and 50 min are you kidding me?" and "...not triggered at an alert somewhere at 75 minutes
which was max?". MEASURED on v3864's Publish (run 42084305066): shards 6 and 13 proved 387 and 324 proofs from 18:27 to
~21:20 with no gap over 7 minutes - a pile, not a hang - under a 160-minute prove step and a 180-minute job, so no bound
ever fired. Held here:
  * heart2 reads its bounds from HEART2_GATE_CAP_S (one gate's wall cap) and HEART2_PROVE_DEADLINE (the run's deadline,
    epoch seconds); unset, empty, junk or <= 0 is NO bound (his Mac's push and a PC's census are never cut);
  * past either bound a proof still to RUN is not started: it is cut, recorded TIMEOUT (UNKNOWN - never PROVEN, never
    banked) and OWED by name in the run's failures (REG-2591's list: the shard manifest, the fan-in, Publish's verdict);
    a proof the cache SERVES is still served (it runs nothing); the gate is NOT RUN, never PROVEN on what ran first;
  * the clean wave starts no gate past the deadline;
  * the fan-in names every TIMEOUT, shard by shard, and the census says how many were cut;
  * the shard workflow's bounds are the ones his 75 minutes can trust: job 75, prove step 70, heart2's deadline at job
    minute 55, a per-gate cap set - never v3864's 180/160.
Fixtures only: _prove_push_one is replaced, nothing is proved, no browser. RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import heart2  # noqa: E402
import proof_shard as PS  # noqa: E402

HEAD = "c" * 40


class TheBoundsAreRead(unittest.TestCase):

    def test_unset_or_junk_is_no_bound(self):
        self.assertEqual(heart2._prove_bounds({}), (None, None))
        self.assertEqual(heart2._prove_bounds({"HEART2_GATE_CAP_S": "", "HEART2_PROVE_DEADLINE": "soon"}), (None, None))
        self.assertEqual(heart2._prove_bounds({"HEART2_GATE_CAP_S": "-5", "HEART2_PROVE_DEADLINE": "0"}), (None, None))
        self.assertEqual(heart2._prove_bounds({"HEART2_GATE_CAP_S": "1500", "HEART2_PROVE_DEADLINE": "1762000000"}),
                         (1500.0, 1762000000.0))

    def test_past_the_deadline_or_the_cap_is_said(self):
        run = heart2._PushRun(keep_going=True)
        run.gate_cap, run.deadline = 100.0, 5000.0
        self.assertIsNone(heart2._past_bound(run, 4950.0, now=4990.0))
        self.assertIn("deadline", heart2._past_bound(run, 4990.0, now=5001.0))
        self.assertIn("cap", heart2._past_bound(run, 4800.0, now=4950.0))
        run.gate_cap = run.deadline = None
        self.assertIsNone(heart2._past_bound(run, 0.0, now=1e12), "no bound cut a proof")


class AGatePastItsBoundIsCut(unittest.TestCase):

    def _gate(self, run, n=4, served=(), slow=0.0):
        ran, said = [], []

        def one(sandbox, name, filename, pr, idx, say, why):
            ran.append(idx)
            if slow:
                time.sleep(slow)
            return heart2.PROVEN
        with mock.patch.object(heart2, "_prove_push_one", one), \
                mock.patch.object(heart2, "_served_here", lambda c, sb, nm, f, pr: pr.get("i") in served):
            v, per = heart2._prove_gate_push("/nowhere", "g_law", "g_law.py", [{"i": i} for i in range(n)],
                                             said.append, run)
        return v, per, ran, "\n".join(said)

    def test_past_the_deadline_nothing_starts_and_every_cut_proof_is_owed_timeout(self):
        run = heart2._PushRun(keep_going=True)
        run.deadline, run.gate_cap = time.time() - 1, None
        v, per, ran, said = self._gate(run, n=4, served=(2,))
        self.assertEqual(ran, [2], "a proof past the deadline was started (or a served one was not served)")
        self.assertEqual(per, [None, None, heart2.PROVEN, None])
        self.assertEqual(v, heart2.NOT_RUN, "a gate the bound cut reads PROVEN on what ran")
        self.assertEqual(sorted((f[0], f[1], f[2]) for f in run.failures),
                         [("g_law", 0, "TIMEOUT"), ("g_law", 1, "TIMEOUT"), ("g_law", 3, "TIMEOUT")],
                         "a cut proof was dropped instead of owed by name")
        self.assertEqual(sorted(run.cut), [("g_law", 0), ("g_law", 1), ("g_law", 3)])
        self.assertIn("REG-3212 TIMEOUT", said)

    def test_a_gate_past_its_cap_keeps_what_ran_and_cuts_the_rest(self):
        run = heart2._PushRun(keep_going=True)
        run.gate_cap, run.deadline = 0.15, None
        v, per, ran, _said = self._gate(run, n=5, slow=0.2)
        self.assertEqual(ran, [0], "the cap did not cut the gate after its first slow proof")
        self.assertEqual(per[0], heart2.PROVEN)
        self.assertEqual([f[1] for f in run.failures], [1, 2, 3, 4])
        self.assertTrue(all(f[2] == heart2.TIMEOUT for f in run.failures))

    def test_no_bound_runs_every_proof(self):
        run = heart2._PushRun(keep_going=True)
        run.gate_cap = run.deadline = None
        v, per, ran, _said = self._gate(run, n=3)
        self.assertEqual((v, ran, run.failures), (heart2.PROVEN, [0, 1, 2], []))

    def test_a_proof_the_cache_serves_is_one_it_would_serve(self):
        class _C(object):
            def __init__(self, hit):
                self.hit = hit

            def key_for(self, sandbox, name, filename, pr):
                return "k-%s" % pr.get("i"), [], None

            def peek(self, key):
                return {"verdict": "PROVEN"} if self.hit else None
        self.assertTrue(heart2._served_here(_C(True), "/nowhere", "g", "g.py", {"i": 1}))
        self.assertFalse(heart2._served_here(_C(False), "/nowhere", "g", "g.py", {"i": 1}))
        self.assertFalse(heart2._served_here(None, "/nowhere", "g", "g.py", {"i": 1}), "no cache served a proof")

    def test_the_clean_wave_starts_no_gate_past_the_deadline(self):
        run = heart2._PushRun(keep_going=True)
        run.deadline = time.time() - 1
        ran = []
        with mock.patch.object(heart2, "_prove_one", lambda *a, **k: ran.append(a[4]) or heart2.CLEAN):
            self.assertEqual(heart2._wave_gate("/nowhere", "g_law", "g_law.py", [{}, {}], lambda *a: None, run),
                             (heart2.NOT_RUN, [None, None]))
        self.assertEqual(ran, [], "the clean wave ran a gate past the run's deadline")


def _shard(root, k, n, entries, assigned, owed):
    d = os.path.join(root, "proof-shard-%d" % k)
    os.makedirs(d)
    own = {}
    for g, i in assigned:
        own.setdefault(g, set()).add(i)
    m = PS.manifest(k, n, HEAD, False, "p1", own, None, None, 1762000000000, owed=owed)
    with io.open(os.path.join(d, PS.STORE_NAME), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"format": 2, "entries": entries, "shard": m}))


class TheFanInNamesEveryTimeout(unittest.TestCase):

    def test_every_cut_proof_is_named_with_its_shard(self):
        root = tempfile.mkdtemp(prefix="timeout-law-")
        self.addCleanup(shutil.rmtree, root, True)
        e = {"verdict": "PROVEN", "gate": "ga", "proof": 0, "provedAt": 1, "tree": "/x"}
        _shard(root, 1, 2, {"k1": e}, [("ga", 0), ("ga", 1)], [["ga", 1, "TIMEOUT", "cut at its bound"]])
        _shard(root, 2, 2, {}, [("gb", 0), ("gb", 1)], [["gb", 0, "TIMEOUT", "cut"], ["gb", 1, "BLIND", "green"]])
        said = []
        self.assertEqual(PS.fan_in(root, 2, HEAD, say=said.append), 0)
        out = "\n".join(said)
        self.assertIn("REG-3212: 2 proof(s) were cut at their bound", out)
        self.assertIn("ga[1] (shard 1)", out)
        self.assertIn("gb[0] (shard 2)", out)
        self.assertNotIn("gb[1] (shard 2)", out.split("REG-3212")[1].split("\n")[0], "a BLIND was named as a TIMEOUT")
        text, tot = PS.census(root, HEAD, 2)
        self.assertIn("2 proof(s) were cut at their bound (TIMEOUT", text)


class TheWorkflowBoundsAreHisMax(unittest.TestCase):

    def test_job_75_step_70_deadline_55_and_a_gate_cap(self):
        with io.open(os.path.join(ROOT, ".github", "workflows", "proof-keys-shards.yml"), encoding="utf-8") as fh:
            wf = fh.read()
        shard = wf[wf.index("\n  shard:\n"):wf.index("\n  fan-in:\n")]
        code = "\n".join(l for l in shard.split("\n") if not l.lstrip().startswith("#"))
        self.assertEqual(re.findall(r"^    timeout-minutes: (\d+)$", code, re.M), ["75"], "the shard job is not bound at 75")
        prove = code[code.index("- name: Prove this shard"):]
        self.assertEqual(re.findall(r"^        timeout-minutes: (\d+)$", prove, re.M)[:1], ["70"])
        self.assertIn("export HEART2_PROVE_DEADLINE=$(( T0 + 55 * 60 ))", prove)
        self.assertLess(prove.index("HEART2_PROVE_DEADLINE="), prove.index("python3 -u tv/heart2.py --prove --push"))
        self.assertRegex(code, r'\n      HEART2_GATE_CAP_S: "(\d+)"\n')
        cap = int(re.search(r'\n      HEART2_GATE_CAP_S: "(\d+)"\n', code).group(1))
        self.assertLessEqual(cap, 55 * 60, "one gate may run longer than the whole run's deadline")


RED_PROOF = [
    {"why": "REG-3212 - a gate past its bound keeps proving (v3864: 387 proofs, 2 h 50 min)",
     "file": "tv/heart2.py",
     "find": "            if _bound is not None and not _served_here(run.cache, sandbox, name, filename, proofs[i]):\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-3212 - a cut proof is silently dropped, never owed by name",
     "file": "tv/heart2.py",
     "find": "    for i in cut:\n        run.fail(name, i, TIMEOUT, reason)\n",
     "replace": "    for i in cut:\n        pass\n",
     "matches": 1},
    {"why": "REG-3212 - the run's deadline is never read",
     "file": "tv/heart2.py",
     "find": "    if dl is not None and now >= dl:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3212 - a junk bound is read as zero and cuts every proof",
     "file": "tv/heart2.py",
     "find": "        out.append(v if (v is not None and v > 0) else None)\n",
     "replace": "        out.append(v if v is not None else 0.0)\n",
     "matches": 1},
    {"why": "REG-3212 - a proof the cache serves is cut too",
     "file": "tv/heart2.py",
     "find": "    return key is not None and cache.peek(key) is not None\n",
     "replace": "    return False\n",
     "matches": 1},
    {"why": "REG-3212 - the clean wave runs gates past the deadline",
     "file": "tv/heart2.py",
     "find": "        if getattr(run, \"deadline\", None) is not None and time.time() >= run.deadline:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3212 - the fan-in never names the TIMEOUTs",
     "file": "tv/proof_shard.py",
     "find": "            if isinstance(f, list) and len(f) >= 3 and f[2] == TIMEOUT:\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-3212 - the shard job is bound at v3864's 180 minutes again",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "    timeout-minutes: 75\n    strategy:",
     "replace": "    timeout-minutes: 180\n    strategy:",
     "matches": 1},
    {"why": "REG-3212 - heart2 is never handed the run's deadline",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "          export HEART2_PROVE_DEADLINE=$(( T0 + 55 * 60 ))\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
