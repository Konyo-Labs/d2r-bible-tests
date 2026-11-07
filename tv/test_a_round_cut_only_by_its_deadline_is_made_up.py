# -*- coding: utf-8 -*-
"""REG-3270..3274 - A PROOF ROUND CUT ONLY BY ITS DEADLINE IS MADE UP, AND THE PLAN PRICES ITSELF FROM WHAT IT MEASURED.

MEASURED on v3872 (0d4e24537, ci/proof-keys-v3872 run 42200089396, every one of 9,378 proofs run fresh, 0 served): the
plan modelled each of 22 shards at 1,720 s; they proved for 1,521-3,357 s (job walls 26-57 min). Shards 14 and 22 reached
heart2's minute-55 deadline with 27 proofs still to run (TIMEOUT - no law red), the run went red, and the ship stopped
until the failed shards were re-run by hand an hour later. Held here:
  * REG-3270 the census writes its totals as JSON beside census.md; proof_shard.makeup_due says a round is made up only
    when its ONLY debt is cut proofs (no law owes a fix, every shard left a store); ship_when_green then re-runs the
    failed shards ONCE and waits on - a law that went red, a store that is missing, or a second red is never made up;
  * REG-3271 measure_costs never reads a gap past the job's bound as one proof (shard 14's store held a proof served
    from 04:21 beside 258 run at 10:0x-11:01 - a 6-hour "per-proof" price for that gate);
  * REG-3272 the plan's modelled wall is the work over the lanes times the measured SHARD_WALL_FACTOR (1.30 on v3872;
    real = 1.30 x modelled, residual mean 154 s over 22 shards);
  * REG-3273 the shard's first lines say whether the slowest shard fits PLAN_HEADROOM of the proving window;
  * REG-3274 the prices update themselves: the fan-in measures this round's per-proof costs beside the seed it saves,
    the seed job carries them in the one proof-seed artifact, and every shard's plan reads them (HEART2_SHARD_COSTS)
    over the committed tv/proof_costs.json - all shards one table, so one plan.
Fixtures only: no GitHub, no heart2 run. RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()   # v3880 - its census case prints a non-ASCII clock; a cp1255 console must not crash reporting it
import proof_shard as PS  # noqa: E402
import proof_seed as SEED  # noqa: E402
import ship_when_green as SW  # noqa: E402
import ci_verdict as CV  # noqa: E402

SHA = "0d4e24537fe744df866433a808ed69daa2d65ecd"


def _store(d, k, n, owed=(), entries=None):
    os.makedirs(d, exist_ok=True)
    body = {"format": 2, "entries": entries or {},
            "shard": PS.manifest(k, n, SHA, False, "plan1", {"g": {0, 1}}, None, None, 1000, owed=list(owed))}
    with io.open(os.path.join(d, PS.STORE_NAME), "w", encoding="utf-8") as fh:
        json.dump(body, fh)


class TheMakeupDecision(unittest.TestCase):
    def test_only_cut_proofs_are_made_up(self):
        due, why = PS.makeup_due({"cut": [["g", 3, PS.TIMEOUT, "deadline", 14]], "fix": [], "lost": [], "missing": []})
        self.assertTrue(due, why)
        self.assertIn("shard(s) 14", why)

    def test_a_red_law_is_never_made_up(self):
        due, why = PS.makeup_due({"cut": [["g", 3, PS.TIMEOUT, "x", 14]], "fix": [["h", 0, "RED", "x", 2]],
                                  "lost": [], "missing": []})
        self.assertFalse(due)
        self.assertIn("owe a fix", why)

    def test_an_unreadable_job_list_is_unknown_and_makes_no_shard_up(self):
        """The swallow ratchet on v3876's pre-flight: an unparseable job list became [] - "no runner killed one", a reading
        no caller could tell from a real one. It is None (UNKNOWN) now, which makes no lost shard up."""
        class _R(object):
            def __init__(self, rc, out):
                self.returncode, self.stdout = rc, out
        for res in (_R(0, "{not json"), _R(1, "")):
            got = SW.killed_shards(42, [7], lambda *a, **k: res)
            self.assertIsNone(got, "an unreadable job list was answered as a reading: %r" % (got,))
            self.assertFalse(PS.makeup_due({"cut": [], "fix": [], "lost": [7], "missing": []}, killed=got)[0])

    def test_a_runner_killed_shard_is_due_and_no_other_lost_one(self):
        """REG-3292 - only the shards the runner killed; one more lost shard makes the round UNKNOWN again."""
        self.assertTrue(PS.makeup_due({"cut": [], "fix": [], "lost": [7], "missing": []}, killed={"7"})[0])
        self.assertFalse(PS.makeup_due({"cut": [], "fix": [], "lost": [7, 9], "missing": []}, killed={"7"})[0])
        self.assertFalse(PS.makeup_due({"cut": [], "fix": [["x", 0, "RED", "", 2]], "lost": [7], "missing": []},
                                       killed={"7"})[0], "a red law rode in on a runner kill")

    def test_a_shard_with_no_store_is_never_made_up(self):
        self.assertFalse(PS.makeup_due({"cut": [["g", 3, PS.TIMEOUT, "x", 14]], "fix": [], "lost": [7],
                                        "missing": []})[0])
        self.assertFalse(PS.makeup_due({"cut": [["g", 3, PS.TIMEOUT, "x", 14]], "fix": [], "lost": [],
                                        "missing": ["proof-shard-7"]})[0])

    def test_nothing_cut_and_no_census_are_not_made_up(self):
        self.assertFalse(PS.makeup_due({"cut": [], "fix": [], "lost": [], "missing": []})[0])
        self.assertFalse(PS.makeup_due(None)[0])

    def test_the_census_json_carries_what_the_decision_reads(self):
        t = tempfile.mkdtemp()
        try:
            _store(os.path.join(t, "proof-shard-1"), 1, 2)
            _store(os.path.join(t, "proof-shard-2"), 2, 2, owed=[["g", 1, PS.TIMEOUT, "the run's deadline passed"]])
            out = os.path.join(t, "census.json")
            with open(os.devnull, "w", encoding="utf-8") as nul:   # #107 - Windows' default is cp1252, and the census prints ⏱
                saved, sys.stdout = sys.stdout, nul
                try:
                    code = PS.main(["--census", t, "--shards", "2", "--head", SHA, "--json", out])
                finally:
                    sys.stdout = saved
            self.assertEqual(code, 0)
            with io.open(out, encoding="utf-8") as fh:
                tot = json.load(fh)
            self.assertEqual(tot["stores"], 2)
            self.assertEqual(tot["lost"], [])
            self.assertEqual(len(tot["cut"]), 1)
            self.assertTrue(tot["makeupDue"], tot["makeupWhy"])
            _store(os.path.join(t, "proof-shard-2"), 2, 2, owed=[["g", 1, "RED", "the law failed"]])
            _t = PS.census(t, SHA, 2)[1]
            self.assertFalse(PS.makeup_due(_t)[0], "a red law read as only cut")
            shutil.rmtree(os.path.join(t, "proof-shard-2"))
            _t = PS.census(t, SHA, 2)[1]
            self.assertEqual(_t["lost"], [2])
            self.assertFalse(PS.makeup_due(_t)[0], "a lost shard read as only cut")
        finally:
            shutil.rmtree(t, ignore_errors=True)


class _Gh(object):
    """A fake `gh`/`git` for ship(): runs on one sha; the proof run red until re-run, then green (or red again)."""

    def __init__(self, census, second="success", job_log=""):
        self.census, self.second, self.reruns, self.calls, self.job_log = census, second, 0, [], job_log

    def runs(self):
        rs = [{"workflowName": wf, "headSha": SHA, "status": "completed", "conclusion": "success",
               "createdAt": "2026-11-06T10:00:00Z", "databaseId": 100 + i} for i, wf in enumerate(CV.REQUIRED)]
        p = rs[3]
        p["databaseId"] = 42200089396
        if self.reruns == 0:
            p["conclusion"] = "failure"
        else:
            p["conclusion"] = self.second
        return rs

    def __call__(self, cmd, **kw):
        self.calls.append(list(cmd))
        out = ""
        if cmd[:3] == ["gh", "run", "download"]:
            d = cmd[cmd.index("-D") + 1]
            if self.census is None:
                return subprocess.CompletedProcess(cmd, 1, "", "no artifact")
            with io.open(os.path.join(d, "census.json"), "w", encoding="utf-8") as fh:
                json.dump(self.census, fh)
        elif cmd[:3] == ["gh", "run", "rerun"]:
            self.reruns += 1
        elif cmd[:3] == ["gh", "run", "view"] and "--json" in cmd:      # REG-3292 - the run's jobs
            out = json.dumps({"jobs": [{"name": "shard 7", "databaseId": 555}, {"name": "shard 8", "databaseId": 556}]})
        elif cmd[:2] == ["gh", "api"] and cmd[2].endswith("/jobs/555/logs"):
            out = self.job_log
        elif cmd[:2] == ["git", "rev-parse"]:
            out = SHA + "\n"
        elif cmd[:2] == ["git", "ls-remote"]:
            out = "%s\trefs/heads/ci/claude-v3875\n%s\trefs/heads/ci/proof-keys-v3875\n" % (SHA, SHA)
        return subprocess.CompletedProcess(cmd, 0, out, "")


def _ship(gh):
    said, t = [], [0.0]

    def sleep(s):
        t[0] += s

    code = SW.ship("v3875", run=gh, fetch=lambda sha: gh.runs(), sleep=sleep, clock=lambda: t[0],
                   say=said.append, wait_s=600 * 60, preflight=False, watch=None, watch_publish_s=None)
    return code, said


CUT = {"cut": [["test_what_keeps_growing_is_salvaged_then_pruned", 23, PS.TIMEOUT, "deadline", 22]], "fix": [],
       "lost": [], "missing": [], "stores": 22}


class TheShipMakesUpARound(unittest.TestCase):
    def test_a_cut_only_red_is_re_run_once_and_then_ships(self):
        gh = _Gh(CUT)
        code, said = _ship(gh)
        self.assertEqual(gh.reruns, 1, said)
        self.assertEqual(code, 0, "\n".join(said))
        self.assertTrue(any("REG-3270 MAKE-UP" in s for s in said), said)
        self.assertIn(["git", "-c", "core.hooksPath=hooks", "push", "origin", "HEAD:main"], gh.calls)

    def test_a_second_red_on_the_same_run_stops_the_ship(self):
        gh = _Gh(CUT, second="failure")
        code, said = _ship(gh)
        self.assertEqual(gh.reruns, 1, "a red re-run was re-run again")
        self.assertEqual(code, 1, said)
        self.assertNotIn(["git", "-c", "core.hooksPath=hooks", "push", "origin", "HEAD:main"], gh.calls)

    def test_a_red_law_is_not_re_run(self):
        gh = _Gh(dict(CUT, fix=[["test_x", 0, "RED", "failed", 3]]))
        code, said = _ship(gh)
        self.assertEqual(gh.reruns, 0)
        self.assertEqual(code, 1)
        self.assertTrue(any("not made up" in s for s in said), said)

    def test_a_shard_the_runner_killed_is_re_run_once(self):
        """REG-3292 (REG-3085's case) - Publish 40812615686: shard 7 'The runner has received a shutdown signal', no store."""
        lost = dict(CUT, cut=[], lost=[7])
        gh = _Gh(lost, job_log="2026-10-29T08:00Z ##[error]" + SW.RUNNER_KILLED + ".\nexit 143")
        code, said = _ship(gh)
        self.assertEqual((gh.reruns, code), (1, 0), said)
        self.assertTrue(any("killed by the runner" in s for s in said), said)

    def test_a_lost_shard_with_no_runner_shutdown_is_not_re_run(self):
        gh = _Gh(dict(CUT, cut=[], lost=[7]), job_log="Traceback: the prover crashed")
        code, said = _ship(gh)
        self.assertEqual((gh.reruns, code), (0, 1), said)
        self.assertTrue(any("not made up" in s for s in said), said)

    def test_an_unreadable_census_is_not_re_run(self):
        gh = _Gh(None)
        code, said = _ship(gh)
        self.assertEqual((gh.reruns, code), (0, 1), said)


class ThePricesMeasureThemselves(unittest.TestCase):
    def test_a_gap_past_the_jobs_bound_is_not_one_proof(self):
        t0 = 1793960000000
        body = {"entries": {
            "a": {"gate": "g", "provedAt": t0},                                   # served from an older round
            "b": {"gate": "g", "provedAt": t0 + 6 * 3600 * 1000},
            "c": {"gate": "g", "provedAt": t0 + 6 * 3600 * 1000 + 40000}}}
        self.assertEqual(PS.measure_costs([body]), {"g": 40.0})

    def test_the_last_rounds_prices_win_over_the_committed_table(self):
        t = tempfile.mkdtemp()
        try:
            base = PS.proof_costs(env={})
            self.assertTrue(base and len(base) > 300, "the committed table is not read")
            g = sorted(base)[0]
            f = os.path.join(t, "proof_costs.json")
            with io.open(f, "w", encoding="utf-8") as fh:
                json.dump({"perProof": {g: base[g] + 77.0, "a_gate_only_the_round_measured": 3.0}}, fh)
            got = PS.proof_costs(env={"HEART2_SHARD_COSTS": f})
            self.assertEqual(got[g], base[g] + 77.0)
            self.assertEqual(got["a_gate_only_the_round_measured"], 3.0)
            self.assertEqual(len(got), len(base) + 1)
            self.assertEqual(PS.proof_costs(env={"HEART2_SHARD_COSTS": os.path.join(t, "absent.json")}), base)
            with io.open(f, "w", encoding="utf-8") as fh:
                fh.write("{not json")
            self.assertEqual(PS.proof_costs(env={"HEART2_SHARD_COSTS": f}), base, "a broken round file replaced the table")
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_a_round_never_prices_a_gate_below_the_committed_table(self):
        """v3880 (REG-3365) - MEASURED on v3878: the last round priced test_control at 19.1 s a proof, the committed table
        says 272.8 s, and each proof took 226-263 s on shard 10 - so 20 of its 28 owed proofs went to one shard and the
        round needed four attempts. A round may raise a price; it never sinks one below the committed table."""
        t = tempfile.mkdtemp()
        try:
            base = PS.proof_costs(env={})
            self.assertGreater(base.get("test_control", 0), 200, "premise: the committed table prices test_control's full proof")
            f = os.path.join(t, "proof_costs.json")
            with io.open(f, "w", encoding="utf-8") as fh:
                json.dump({"perProof": {"test_control": 19.059}}, fh)
            got = PS.proof_costs(env={"HEART2_SHARD_COSTS": f})
            self.assertEqual(got["test_control"], base["test_control"], "a cheap round sank test_control to %r" % got["test_control"])
            # a round's size: 300 other gates of 30 cheap proofs beside test_control's 28 (v3878 owed ~9,500 proofs)
            fill = [("f%03d" % i, "f%03d.py" % i, [{}] * 30) for i in range(300)]
            pp = dict(((n, 3.5) for n, _f, _p in fill), test_control=got["test_control"])
            plan = PS.plan([("test_control", "test_control.py", [{}] * 28)] + fill, 22,
                           costs={"test_control": 129.2}, per_proof=pp)
            shards = {}
            for (g, i), k in plan.items():
                if g == "test_control":
                    shards[k] = shards.get(k, 0) + 1
            # at 19 s a proof the same plan put 14 on each of two shards: 14 x ~245 s on one lane is past the 55-min job
            self.assertLessEqual(max(shards.values()), 4,
                                 "one shard still owes %d of test_control's proofs at its real price" % max(shards.values()))
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_the_seed_carries_the_prices_and_refuses_a_broken_file(self):
        t = tempfile.mkdtemp()
        try:
            rest, out = os.path.join(t, "restored"), os.path.join(t, "out")
            os.makedirs(rest)
            os.makedirs(out)
            self.assertEqual(SEED.carry_prices(rest, out, say=lambda *_: None), 0)
            with io.open(os.path.join(rest, SEED.PRICES_NAME), "w", encoding="utf-8") as fh:
                json.dump({"perProof": {"g": 12.5}}, fh)
            self.assertEqual(SEED.carry_prices(rest, out, say=lambda *_: None), 1)
            self.assertEqual(PS.proof_costs(os.path.join(out, SEED.PRICES_NAME)), {"g": 12.5})
            os.remove(os.path.join(out, SEED.PRICES_NAME))
            with io.open(os.path.join(rest, SEED.PRICES_NAME), "w", encoding="utf-8") as fh:
                fh.write("[]")
            self.assertEqual(SEED.carry_prices(rest, out, say=lambda *_: None), 0)
            self.assertFalse(os.path.exists(os.path.join(out, SEED.PRICES_NAME)))
        finally:
            shutil.rmtree(t, ignore_errors=True)


class ThePlanSaysItsRealWall(unittest.TestCase):
    def test_the_modelled_wall_carries_the_measured_factor(self):
        have = [("g%d" % i, "f", [{"i": j} for j in range(4)]) for i in range(6)]
        rep = {}
        PS.plan(have, 2, {"g%d" % i: 10.0 for i in range(6)}, browser=set(), per_proof={}, report=rep)
        self.assertEqual(rep["factor"], PS.SHARD_WALL_FACTOR)
        raw = [w / PS.SHARD_WALL_FACTOR for w in rep["wall"]]
        for w, t in zip(raw, rep["work"]):
            self.assertAlmostEqual(w, t / PS.RUNNER_LANES, delta=0.2)
        self.assertGreater(PS.SHARD_WALL_FACTOR, 1.0, "the plan models less than the shards really take")

    def test_headroom_is_said_both_ways(self):
        ok, why = PS.headroom([0.5 * PS.PROVE_WINDOW_S])
        self.assertTrue(ok, why)
        bad, why = PS.headroom([0.78 * PS.PROVE_WINDOW_S, 100.0])
        self.assertFalse(bad)
        self.assertIn("over the 70% headroom", why)
        self.assertFalse(PS.headroom(None)[0] and PS.headroom(["x"])[0])

    def test_the_shard_says_its_headroom(self):
        with io.open(os.path.join(HERE, "heart2.py"), encoding="utf-8") as fh:
            src = fh.read()
        line = '    say("  REG-3273 HEADROOM: %s" % _PS.headroom(_w)[1] if _w else "  REG-3273 HEADROOM: UNKNOWN - the plan said no wall")\n'
        self.assertEqual(src.count(line), 1)


class TheWorkflowCarriesIt(unittest.TestCase):
    def setUp(self):
        with io.open(os.path.join(ROOT, ".github", "workflows", "proof-keys-shards.yml"), encoding="utf-8") as fh:
            self.y = "\n".join(l for l in fh.read().split("\n") if not l.lstrip().startswith("#"))

    def test_the_census_writes_and_keeps_its_json(self):
        self.assertEqual(self.y.count('--out census.md \\\n            --json census.json\n'), 1)
        self.assertEqual(self.y.count("          path: |\n            census.md\n            census.json\n"), 1)

    def test_the_fan_in_saves_the_rounds_prices_beside_the_seed(self):
        line = '          python3 tv/proof_shard.py --measure-costs shards --out "$RUNNER_TEMP/heart2-seed/proof_costs.json" || true\n'
        self.assertEqual(self.y.count(line), 1)
        self.assertLess(self.y.index('--merge-shards shards --out "$RUNNER_TEMP/heart2-seed/.heart2_cache.json"'),
                        self.y.index(line))

    def test_every_shard_reads_the_carried_prices(self):
        prove = self.y[self.y.index("- name: Prove this shard"):]
        line = '          export HEART2_SHARD_COSTS="$RUNNER_TEMP/heart2-seed/proof_costs.json"\n'
        self.assertEqual(prove.count(line), 1)
        self.assertLess(prove.index(line), prove.index("python3 -u tv/heart2.py --prove --push"))


class TheAptStepRunsOnlyWhenNeeded(unittest.TestCase):
    """REG-3279 - v3872's shard 22 spent its OS-deps step's whole 5 minutes in apt while its browsers needed nothing."""

    def _script(self):
        with io.open(os.path.join(ROOT, ".github", "workflows", "proof-keys-shards.yml"), encoding="utf-8") as fh:
            y = fh.read()
        i = y.index("      - name: OS deps for Chromium (best effort)")
        j = y.index("\n      - name:", i + 10)
        step = y[i:j]
        body = step[step.index("        run: |\n") + len("        run: |\n"):]
        return "\n".join(l[10:] for l in body.split("\n"))

    def _run(self, ldd_says_missing, browsers=2):
        if not shutil.which("bash"):
            self.skipTest("no bash - this case runs the step's own script")
        t = tempfile.mkdtemp()
        try:
            home, binp = os.path.join(t, "home"), os.path.join(t, "bin")
            os.makedirs(binp)
            for k in range(browsers):
                d = os.path.join(home, ".cache", "ms-playwright", "chromium-%d" % k, "chrome-linux64")
                os.makedirs(d)
                with io.open(os.path.join(d, "chrome" if k == 0 else "chrome-headless-shell"), "w") as fh:
                    fh.write("x")
            calls = os.path.join(t, "calls")
            with io.open(os.path.join(binp, "ldd"), "w") as fh:
                fh.write("#!/bin/sh\necho 'libc.so.6 => /lib/libc.so.6'\n%s\n"
                         % ("echo 'libnss3.so => not found'" if ldd_says_missing else ""))
            with io.open(os.path.join(binp, "npx"), "w") as fh:
                fh.write("#!/bin/sh\necho \"$@\" >> %s\n" % calls)
            for f in ("ldd", "npx"):
                os.chmod(os.path.join(binp, f), 0o755)
            env = dict(os.environ, HOME=home, PATH=binp + os.pathsep + os.environ.get("PATH", ""))
            r = subprocess.run(["bash", "-c", self._script()], env=env, capture_output=True, text=True, timeout=60)
            ran = io.open(calls).read() if os.path.exists(calls) else ""
            return r, ran
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def test_a_browser_that_links_every_library_skips_apt(self):
        r, ran = self._run(False)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(ran, "", "apt ran for browsers that need nothing")
        self.assertIn("link every library - no apt step", r.stdout)

    def test_a_missing_library_still_installs_the_deps(self):
        r, ran = self._run(True)
        self.assertIn("install-deps chromium", ran, "a browser missing a library got no OS deps")

    def test_no_browser_found_is_unknown_and_installs(self):
        r, ran = self._run(False, browsers=0)
        self.assertIn("install-deps chromium", ran, "no browser seen read as every library present")


RED_PROOF = [
    {"why": "the swallow ratchet on v3876 - an unreadable job list is answered as 'no runner killed one' again",
     "file": "tv/ship_when_green.py",
     "find": "        return None          # the swallow ratchet (v3876 pre-flight) - an unreadable list is UNKNOWN, never \"none killed\"\n",
     "replace": "        jobs = []\n",
     "matches": 1},
    {"why": "REG-3292 - a shard the runner killed is never made up (REG-3085's case stays a hand re-run)",
     "file": "tv/ship_when_green.py",
     "find": "        if getattr(g, \"returncode\", 1) == 0 and RUNNER_KILLED in (g.stdout or \"\"):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3292 - every lost shard counts as runner-killed, whatever its log says",
     "file": "tv/proof_shard.py",
     "find": "    unexplained = [str(k) for k in lost if str(k) not in killed] + list(missing)\n",
     "replace": "    unexplained = list(missing)\n",
     "matches": 1},
    {"why": "REG-3279 - apt runs whatever the browsers need (v3872's shard 22: 5 of 55 proving minutes)",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "          if [ \"$seen\" -gt 0 ] && [ \"$miss\" -eq 0 ]; then\n",
     "replace": "          if false; then\n",
     "matches": 1, "needs": "posix"},
    {"why": "REG-3279 - no browser seen reads as every library present",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "          if [ \"$seen\" -gt 0 ] && [ \"$miss\" -eq 0 ]; then\n",
     "replace": "          if [ \"$miss\" -eq 0 ]; then\n",
     "matches": 1, "needs": "posix"},
    {"why": "REG-3270 - a round with a red law is made up as if only cut",
     "file": "tv/proof_shard.py",
     "find": "    if fix:\n        return False, \"%d proof(s) owe a fix (a law went red) - a re-run cannot make that up\" % len(fix)\n",
     "replace": "    if False:\n        return False, \"\"\n",
     "matches": 1},
    {"why": "REG-3270 - a missing shard store is made up",
     "file": "tv/proof_shard.py",
     "find": "    if unexplained:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3270 - the census JSON never says what the decision reads",
     "file": "tv/proof_shard.py",
     "find": "               lost=lost, missing=missing, stores=len(rows))      # REG-3270 - what makeup_due reads\n",
     "replace": "               stores=len(rows))\n",
     "matches": 1},
    {"why": "REG-3270 - the ship never makes a round up",
     "file": "tv/ship_when_green.py",
     "find": "            elif only_proofs and makeup(sha, runs, run, say, made, clock):\n",
     "replace": "            elif False:\n",
     "matches": 1},
    {"why": "REG-3270 - a made-up run is made up again and again",
     "file": "tv/ship_when_green.py",
     "find": "    if not rid or rid in made:\n",
     "replace": "    if not rid:\n",
     "matches": 1},
    {"why": "REG-3271 - a gap that spans two rounds prices one proof",
     "file": "tv/proof_shard.py",
     "find": "if x <= MAX_PROOF_GAP_S)",
     "replace": "if x >= 0)",
     "matches": 1},
    {"why": "REG-3272 - the modelled wall drops the measured factor",
     "file": "tv/proof_shard.py",
     "find": "        report.update(wall=[round(SHARD_WALL_FACTOR * max(t / lanes, w), 1) for t, w in zip(tot, brw)],\n",
     "replace": "        report.update(wall=[round(max(t / lanes, w), 1) for t, w in zip(tot, brw)],\n",
     "matches": 1},
    {"why": "REG-3273 - an over-full plan reads as fitting",
     "file": "tv/proof_shard.py",
     "find": "    if w <= share * window:\n",
     "replace": "    if True:\n",
     "matches": 1},
    {"why": "REG-3274 - the round's prices never reach the plan",
     "file": "tv/proof_shard.py",
     "find": "            out[g] = max(v, base.get(g, 0.0))\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "REG-3274 - a broken round file is carried into every shard",
     "file": "tv/proof_seed.py",
     "find": "    if not got:\n        say(\"  REG-3274 PRICES: no measured prices",
     "replace": "    if got is None and False:\n        say(\"  REG-3274 PRICES: no measured prices",
     "matches": 1},
    {"why": "REG-3274 - the fan-in never saves the round's prices",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "          python3 tv/proof_shard.py --measure-costs shards --out \"$RUNNER_TEMP/heart2-seed/proof_costs.json\" || true\n",
     "replace": "          true\n",
     "matches": 1},
    {"why": "v3880 (REG-3365) - a cheap round sinks a gate below its committed full-proof price (v3878: test_control 19 s)",
     "file": "tv/proof_shard.py",
     "find": "            out[g] = max(v, base.get(g, 0.0))\n",
     "replace": "            out[g] = v\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
