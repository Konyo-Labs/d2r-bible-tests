# -*- coding: utf-8 -*-
"""REG-3212 - A PROOF RUN BOUNDS ITSELF INSIDE HIS 75 MINUTES: A GATE PAST ITS BOUND IS CUT, RECORDED TIMEOUT, AND NAMED.

His words (2026-11-05): "2hr and 50 min are you kidding me?" (that figure was a UTC-vs-Israel-time misreading, not a
measurement - Publish took 55.7 min) and "...not triggered at an alert somewhere at 75 minutes which was max?".
MEASURED on v3864 (ci/proof-keys-v3864, run 42061540765): shard 10 held 656 of 8,829 proofs and proved
for 87 min of job - every other shard done in 24-57 - until it was cancelled, under a 160-minute prove step and a 180-minute
job, so no bound ever fired. Held here:
  * heart2 reads its bounds from HEART2_GATE_CAP_S (one gate's wall cap) and HEART2_PROVE_DEADLINE (the run's deadline,
    epoch seconds); unset, empty, junk or <= 0 is NO bound (his Mac's push and a PC's census are never cut);
  * past either bound a proof still to RUN is not started: it is cut, recorded TIMEOUT (UNKNOWN - never PROVEN, never
    banked) and OWED by name in the run's failures (REG-2591's list: the shard manifest, the fan-in, Publish's verdict);
    a proof the cache SERVES is still served (it runs nothing); the gate is NOT RUN, never PROVEN on what ran first;
  * the clean wave starts no gate past the deadline;
  * (the second eye on v3865) a law run ALREADY GOING is cut too: every law run of a push takes the tighter of its own
    deadline and the bound - the run's hard stop (its deadline + HARD_STOP_AFTER_S) and, for a gate's proofs, the gate's
    cap from its first proof - so a proof started at minute 54 can no longer run past the 70-minute step and leave no
    manifest. A run the bound killed (or would not start) is TIMEOUT, owed by name - never the law's verdict - and so are
    the PROVENs whose closing clean run the hard stop killed (never banked unconfirmed, never silently UNPROVABLE);
  * the census lists a TIMEOUT apart from "laws owed a fix" (it is no defect of its law), and Publish's verdict still
    holds the deploy on a TIMEOUT of one of the push's laws;
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
        # the second eye on v3865 - a law that only ran out of time is not a law to repair
        self.assertIn("owed a fix 1 · unbanked 0", text)
        self.assertIn("· cut at the bound 2 (TIMEOUT", text)
        self.assertEqual([f[:3] for f in tot["fix"]], [["gb", 1, "BLIND"]], "a TIMEOUT was listed as a law owed a fix")
        self.assertEqual([f[:3] for f in tot["cut"]], [["ga", 1, "TIMEOUT"], ["gb", 0, "TIMEOUT"]])
        nxt = text.split("### Next batch - laws owed a fix (1)", 1)
        self.assertEqual(len(nxt), 2, text)
        self.assertNotIn("TIMEOUT", nxt[1].split("###")[0], "the next batch lists a proof its bound cut")

    def test_a_timeout_on_the_pushs_own_law_holds_the_deploy(self):
        root = tempfile.mkdtemp(prefix="timeout-law-")
        self.addCleanup(shutil.rmtree, root, True)
        e = {"verdict": "PROVEN", "gate": "ga", "proof": 0, "provedAt": 1, "tree": "/x"}
        _shard(root, 1, 2, {"k1": e}, [("ga", 0), ("ga", 1)], [["ga", 1, "TIMEOUT", "cut at its bound"]])
        _shard(root, 2, 2, {}, [("gb", 0)], [])
        said = []
        rc = PS.deploy_verdict(root, 2, HEAD, "b" * 40, say=said.append, changed={"tv/ga.py"},
                               gates_of=lambda paths: ["ga"], mac_only=lambda names: set())
        self.assertEqual(rc, 1, "a law of this push its bound cut reads proved on CI:\n" + "\n".join(said))
        self.assertIn("ga[1] TIMEOUT", "\n".join(said))


class AGateMayDeclareItsOwnCap(unittest.TestCase):
    """REG-3317 (his 11-06: "these shards and these tests need to be smooth and work fast") - the run's one cap (1,500 s)
    cut the two width laws in v3872's round and v3875's rounds 1, 3 and 5: their proofs MEASURED ~1,600-1,700 s, and each
    cut cost a make-up re-run or a red round. A gate may declare its own larger cap beside its registration; it never
    lowers the run's, and where no run cap is set (his Mac's push, a PC's census) nothing is cut."""

    class _G(object):
        def __init__(self, name, cap=None):
            self.name, self.prove_cap_s = name, cap

    def _with(self, gates):
        import run_gates
        return mock.patch.object(run_gates, "GATES", gates)

    def test_the_declared_cap_wins_only_when_it_is_larger(self):
        gates = [self._G("g_wide", 2400), self._G("g_plain"), self._G("g_small", 1000)]
        with self._with(gates):
            self.assertEqual(heart2._gate_cap_for("g_wide", 1500.0), 2400.0)
            self.assertEqual(heart2._gate_cap_for("g_plain", 1500.0), 1500.0)
            self.assertEqual(heart2._gate_cap_for("g_small", 1500.0), 1500.0, "a declared cap lowered the run's")
            self.assertIsNone(heart2._gate_cap_for("g_wide", None), "a declared cap cut where no run cap is set")

    def test_both_bounds_use_the_gates_own_cap(self):
        run = heart2._PushRun(keep_going=True)
        run.gate_cap, run.deadline = 1500.0, None
        self.assertIsNone(heart2._past_bound(run, 0.0, now=1600.0, cap=2400.0), "the declared cap was not used")
        self.assertIn("1500 s cap", heart2._past_bound(run, 0.0, now=1600.0), "premise: the run's cap cuts at 1,600 s")
        heart2._BOUND.t0, heart2._BOUND.cap = 1000.0, 2400.0
        try:
            secs, why = heart2._inflight_limit(5000, now=2600.0, run=run)
            self.assertEqual((round(secs), why), (800, "this gate's 2400 s cap"), "a run already going ignores the declared cap")
        finally:
            heart2._BOUND.t0, heart2._BOUND.cap = None, None

    def test_the_two_width_laws_declare_their_measured_cap(self):
        import run_gates
        caps = {g.name: getattr(g, "prove_cap_s", None) for g in run_gates.GATES}
        for name in ("test_the_character_builder_fits_at_every_width", "test_the_mule_window_fits_at_every_width"):
            self.assertIsNotNone(caps.get(name), "%s is cut at the run's 1,500 s cap again" % name)
            self.assertGreaterEqual(caps[name], 2000, name)


class ARunAlreadyGoingIsCut(unittest.TestCase):
    """The second eye on v3865: the bound was asked only BEFORE a proof, and nothing killed a law run in flight."""

    def setUp(self):
        self.sb = tempfile.mkdtemp(prefix="inflight-law-")
        self.addCleanup(shutil.rmtree, self.sb, True)
        self.mark = os.path.join(self.sb, "ran.txt")
        with io.open(os.path.join(self.sb, "test_zz_sleeps_fixture.py"), "w", encoding="utf-8") as fh:
            fh.write("import io, time\nio.open(%r, 'w').write('ran')\ntime.sleep(6)\n" % self.mark)
        heart2._BOUND.cut = None
        heart2._BOUND.t0 = None
        self.addCleanup(setattr, heart2._BOUND, "cut", None)
        self.addCleanup(setattr, heart2._BOUND, "t0", None)

    def _run(self, deadline=None, cap=None, t0=None):
        run = heart2._PushRun(keep_going=True)
        run.deadline, run.gate_cap = deadline, cap
        heart2._BOUND.t0 = t0
        a = time.time()
        with mock.patch.object(heart2, "_PUSH", run):
            ok, tail = heart2._run_gate_once(self.sb, "test_zz_sleeps_fixture.py", timeout=30)
        return ok, tail, time.time() - a

    def test_the_hard_stop_kills_a_run_already_going(self):
        ok, tail, took = self._run(deadline=time.time() - heart2.HARD_STOP_AFTER_S + 1.5)
        self.assertIsNone(ok, tail)
        self.assertIn("cut at its bound", tail)
        self.assertLess(took, 4.5, "the run went on past the hard stop (%.1f s)" % took)
        self.assertIn("hard stop", heart2._BOUND.cut or "", "a run the bound killed is not marked TIMEOUT")

    def test_past_the_hard_stop_no_run_starts(self):
        ok, tail, took = self._run(deadline=time.time() - heart2.HARD_STOP_AFTER_S - 10)
        self.assertIsNone(ok)
        self.assertIn("before it started", tail)
        self.assertFalse(os.path.exists(self.mark), "a law run started past the hard stop")

    def test_a_gates_cap_kills_its_run_already_going(self):
        ok, tail, took = self._run(cap=1.5, t0=time.time())
        self.assertIsNone(ok, tail)
        self.assertLess(took, 4.5, "one gate ran past its cap (%.1f s)" % took)
        self.assertIn("cap", heart2._BOUND.cut or "")

    def test_the_limit_is_the_tighter_of_the_law_and_the_bound(self):
        run = heart2._PushRun(keep_going=True)
        run.deadline, run.gate_cap = 20000.0, 1500.0
        hs = 20000.0 + heart2.HARD_STOP_AFTER_S
        self.assertEqual(heart2._hard_stop(run), hs)
        self.assertEqual(heart2._inflight_limit(60, now=9000.0, run=run, gate_t0=9000.0), (60, None),
                         "a bound cut a run its own deadline already bounds tighter")
        t, why = heart2._inflight_limit(1800, now=9000.0, run=run, gate_t0=9000.0)
        self.assertEqual(t, float(heart2.PROOF_CAP_S), "a doubled 900 s law outlasted the per-proof cap")
        self.assertIn("proof", why)
        t, why = heart2._inflight_limit(1800, now=hs - 100, run=run, gate_t0=hs - 100)
        self.assertEqual((t, "hard stop" in why), (100.0, True))
        self.assertEqual(heart2._inflight_limit(None, now=hs + 5, run=run, gate_t0=None)[0], 0.0)
        run.deadline = run.gate_cap = None
        self.assertEqual(heart2._inflight_limit(1800, now=1.0, run=run, gate_t0=0.0), (1800, None), "no bound cut a run")
        with mock.patch.object(heart2, "_PUSH", None):
            self.assertEqual(heart2._inflight_limit(1800), (1800, None), "a run with no push (his census) was bounded")

    def test_a_gates_proofs_run_under_its_cap_and_a_killed_one_is_owed_timeout(self):
        run = heart2._PushRun(keep_going=True)
        run.gate_cap, run.deadline = 1500.0, None
        seen = []

        def one(sandbox, name, filename, pr, idx, say, why):
            seen.append(heart2._inflight_limit(3000))
            if idx == 1:
                heart2._BOUND.cut = "this gate's 1500 s cap"       # the bound killed its run in flight
                return heart2.UNPROVABLE
            return heart2.PROVEN
        said = []
        with mock.patch.object(heart2, "_prove_push_one", one), mock.patch.object(heart2, "_PUSH", run):
            v, per = heart2._prove_gate_push("/nowhere", "g_law", "g_law.py", [{"i": i} for i in range(3)],
                                             said.append, run)
        self.assertTrue(all(w and "cap" in w for _t, w in seen), "a gate's proof ran with no cap on it: %r" % (seen,))
        self.assertEqual(per, [heart2.PROVEN, None, heart2.PROVEN], "a run the bound killed kept the law's verdict")
        self.assertEqual([(f[0], f[1], f[2]) for f in run.failures], [("g_law", 1, "TIMEOUT")])
        self.assertEqual(run.proofs[("g_law", 1)]["v"], heart2.TIMEOUT)
        self.assertEqual(v, heart2.NOT_RUN)
        self.assertIsNone(heart2._BOUND.t0, "the gate's clock outlived its gate")

    def test_proofs_whose_closing_run_the_hard_stop_killed_are_owed_timeout(self):
        run = heart2._PushRun(keep_going=True)
        run.gate_cap = run.deadline = None

        def closing(name, per, say):
            heart2._BOUND.cut = "the run's hard stop, 480 s past its deadline"
            return [heart2.UNPROVABLE if x == heart2.PROVEN else x for x in per]
        with mock.patch.object(heart2, "_prove_push_one", lambda *a: heart2.PROVEN), \
                mock.patch.object(heart2, "_closing_clean", closing):
            v, per = heart2._prove_gate_push("/nowhere", "g_law", "g_law.py", [{}, {}], lambda *a: None, run)
        self.assertEqual(per, [None, None], "a PROVEN its closing run never confirmed reads UNPROVABLE, owed by no one")
        self.assertEqual(sorted((f[1], f[2]) for f in run.failures), [(0, "TIMEOUT"), (1, "TIMEOUT")])
        self.assertEqual(v, heart2.NOT_RUN)


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
        # the second eye on v3865 - every law run still going is killed at the hard stop, inside the 70-minute step with
        # minutes to spare for the manifest, the flush and the upload
        self.assertLessEqual(55 * 60 + heart2.HARD_STOP_AFTER_S, 65 * 60, "the hard stop lands on the step's own cap")


RED_PROOF = [
    {"why": "REG-3317 - a gate's declared cap is ignored, and the width laws are cut at 1,500 s again",
     "file": "tv/heart2.py",
     "find": "                if isinstance(own, (int, float)) and own > run_cap:\n",
     "replace": "                if False:\n",
     "matches": 1},
    {"why": "REG-3317 - a law run already going is killed at the run's cap, not the gate's own",
     "file": "tv/heart2.py",
     "find": "    cap = (getattr(_BOUND, \"cap\", None) if t0 is not None else None) or getattr(run, \"gate_cap\", None)   # REG-3317\n",
     "replace": "    cap = getattr(run, \"gate_cap\", None)\n",
     "matches": 1},
    {"why": "REG-3317 - the character builder's width law loses its measured cap",
     "file": "tv/run_gates.py",
     "find": '    Gate("test_the_character_builder_fits_at_every_width",\n         [sys.executable, os.path.join(HERE, "test_the_character_builder_fits_at_every_width.py")], 300,\n         needs_app=False,\n         # REG-3317 - measured on GitHub\'s shards: its width proofs need ~1,600-1,700 s and were cut at the 1,500 s cap in\n         # v3872\'s round and v3875\'s rounds 1, 3 and 5 (each a make-up re-run or a red round); 2,400 s leaves headroom\n         prove_cap_s=2400,',
     "replace": '    Gate("test_the_character_builder_fits_at_every_width",\n         [sys.executable, os.path.join(HERE, "test_the_character_builder_fits_at_every_width.py")], 300,\n         needs_app=False,\n         # REG-3317 - measured on GitHub\'s shards: its width proofs need ~1,600-1,700 s and were cut at the 1,500 s cap in\n         # v3872\'s round and v3875\'s rounds 1, 3 and 5 (each a make-up re-run or a red round); 2,400 s leaves headroom\n         prove_cap_s=None,',
     "matches": 1},
    {"why": "REG-3212 - a gate past its bound keeps proving (v3864: shard 10, 656 proofs, 87 min)",
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
    {"why": "REG-3212 (second eye) - a law run already going is never cut: a proof started at minute 54 runs past the step",
     "file": "tv/heart2.py",
     "find": "    timeout, _bwhy = _inflight_limit(timeout)          # REG-3212 - a run already going is cut at its bound too\n",
     "replace": "    _bwhy = None\n",
     "matches": 1},
    {"why": "REG-3212 (second eye) - a run the bound killed reads as the law's own deadline, never TIMEOUT",
     "file": "tv/heart2.py",
     "find": "        if _bwhy is not None:                 # REG-3212 - the bound killed it, not the law's own deadline: TIMEOUT\n",
     "replace": "        if False:                 # REG-3212 - the bound killed it, not the law's own deadline: TIMEOUT\n",
     "matches": 1},
    {"why": "REG-3212 (second eye) - the run has no hard stop: in-flight runs go on to the step's cap",
     "file": "tv/heart2.py",
     "find": "    return None if dl is None else dl + HARD_STOP_AFTER_S\n",
     "replace": "    return None\n",
     "matches": 1},
    {"why": "REG-3212 (second eye) - a gate's proofs run with no cap on a run already going",
     "file": "tv/heart2.py",
     "find": "        _BOUND.t0 = _g0                                  # REG-3212 - a run of this gate's proofs is killed at its cap\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3212 (second eye) - a proof the bound killed keeps the law's verdict (UNPROVABLE), owed by no one",
     "file": "tv/heart2.py",
     "find": "            if getattr(_BOUND, \"cut\", None) is not None and got.get(i) != PROVEN:\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-3212 (second eye) - PROVENs whose closing run the hard stop killed go silently UNPROVABLE",
     "file": "tv/heart2.py",
     "find": "        if getattr(_BOUND, \"cut\", None) is not None:\n            # REG-3212 - the clean run that had to CONFIRM",
     "replace": "        if False:\n            # REG-3212 - the clean run that had to CONFIRM",
     "matches": 1},
    {"why": "REG-3212 (second eye) - the census lists a law that only ran out of time as a law owed a fix",
     "file": "tv/proof_shard.py",
     "find": "            (cut if f[2] == TIMEOUT else fix).append(f + [sh.get(\"k\")])\n",
     "replace": "            fix.append(f + [sh.get(\"k\")])\n",
     "matches": 1},
    {"why": "REG-3212 (second eye) - a TIMEOUT on one of the push's laws no longer holds the deploy",
     "file": "tv/proof_shard.py",
     "find": "    for f in tot[\"fix\"] + tot[\"cut\"]:",
     "replace": "    for f in tot[\"fix\"]:",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
