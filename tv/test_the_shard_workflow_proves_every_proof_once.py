# -*- coding: utf-8 -*-
"""REG-2588 - THE SHARD WORKFLOW RUNS EVERY SHARD 1..N ONCE, AND ITS FAN-IN PASSES ONLY A SET THE IMPORT WOULD TAKE.

.github/workflows/proof-keys-shards.yml cuts one `heart2 --prove --push` across N runners (REG-2585) and a fan-in job
collects their caches for `heart2 --import-shards` (REG-2586). A YAML file is a claim; this law reads it:
  1. N is said once (PROOF_SHARDS) and the matrix is exactly 1..N - a shard number nobody runs is a slice never
     proved, and the import refuses the whole set over it; N fits the Free plan's 20 concurrent jobs;
  2. each shard runs --proof-shard <its number>/N into its OWN fresh cache under RUNNER_TEMP, named as heart2's store
     writer requires, and uploads it (hidden file included) even when the prove failed;
  3. the fan-in needs every shard, runs whatever they concluded, and checks the set with tv/proof_shard.py --fan-in
     against this commit - the same check_shards/select the import applies;
  4. it runs only from ci/proof-keys-* (or by hand), never on main, and no `claude` can answer on its runners.
And the fan-in itself is DRIVEN over temp shard dirs: a whole set passes, a missing / extra-N / other-commit set is
refused, a stopped shard is named with its banked count.
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import proof_shard as PS  # noqa: E402

WF = os.path.join(ROOT, ".github", "workflows", "proof-keys-shards.yml")
HEAD = "c" * 40
# v3864 - GitHub Pro (his upgrade, 2026-11-05) runs 40 jobs at once; while the shards run, the version's other required
# checks hold ~18 (agent tests 5, Playwright 10 + 2 slow, Windows boot 1), so the shards that can ALL run at once are 22
PLAN_JOBS, OTHER_CHECK_JOBS = 40, 18


def _wf():
    with io.open(WF, encoding="utf-8") as fh:
        return fh.read()


def _job(text, name):
    """The text of one top-level job (two-space indented key under `jobs:`). -> str"""
    m = re.search(r"\n  %s:\n(.*?)(?=\n  [A-Za-z][\w-]*:\n|\Z)" % re.escape(name), "\n" + text.split("\njobs:\n", 1)[-1] + "\n",
                  re.S)
    return m.group(1) if m else ""


class TheWorkflowRunsEveryShardOnce(unittest.TestCase):

    def test_n_is_said_once_and_the_matrix_is_exactly_one_to_n(self):
        text = _wf()
        n = re.findall(r'^  PROOF_SHARDS: "(\d+)"$', text, re.M)
        self.assertEqual(len(n), 1, "PROOF_SHARDS is not set exactly once at workflow scope: %r" % n)
        n = int(n[0])
        m = re.search(r"^        shard: \[([\d, ]+)\]$", text, re.M)
        self.assertIsNotNone(m, "the shard matrix list is gone - re-anchor this law")
        got = [int(x) for x in m.group(1).split(",")]
        self.assertEqual(got, list(range(1, n + 1)), "the matrix runs %s, not every shard 1..%d once" % (got, n))
        self.assertLessEqual(n, PLAN_JOBS - OTHER_CHECK_JOBS,
                             "N=%d shards cannot all run at once beside the other checks on GitHub Pro's %d jobs" % (n, PLAN_JOBS))
        # v3864 - 22 on GitHub Pro; UNMEASURED until its first run (16 was measured: max ~41 min each on 21a78ff6)
        self.assertEqual(n, 22, "the plan this build is set for is 22 shards (GitHub Pro, beside the other checks)")
        mp = re.search(r"^      max-parallel: (\d+)$", text, re.M)
        self.assertTrue(mp and int(mp.group(1)) >= n, "max-parallel holds shards back: the wall time is the sum, not the max")

    def test_each_shard_proves_its_own_slice_into_its_own_fresh_cache(self):
        job = _job(_wf(), "shard")
        self.assertIn('python3 -u tv/heart2.py --prove --push --proof-shard "${{ matrix.shard }}/${PROOF_SHARDS}"', job,
                      "a shard no longer proves ITS slice of N")
        self.assertIn('D="$RUNNER_TEMP/shard-${{ matrix.shard }}"', job, "the shard's cache dir is not its own")
        self.assertIn('export HEART2_CACHE_PATH="$D/.heart2_cache.json"', job,
                      "the shard's cache is not named as heart2's store writer requires (.heart2_cache.json)")
        self.assertEqual(os.path.basename("x/" + PS.STORE_NAME), ".heart2_cache.json")
        self.assertIn("exit $rc", job, "a shard that failed reads as green")
        up = job[job.find("actions/upload-artifact"):]
        self.assertIn("if: always()", job[job.find("Upload this shard"):], "a failed shard's cache is never uploaded")
        self.assertIn("name: proof-shard-${{ matrix.shard }}", up)
        self.assertIn("path: ${{ runner.temp }}/shard-${{ matrix.shard }}/", up)
        self.assertIn("include-hidden-files: true", up,
                      "upload-artifact drops dot-files by default: .heart2_cache.json would never leave the runner")

    def test_the_fan_in_needs_every_shard_and_checks_the_set_as_the_import_does(self):
        job = _job(_wf(), "fan-in")
        self.assertTrue(job, "the fan-in job is gone")
        self.assertIn("needs: [shard]", job)
        head = job[:job.find("\n    steps:")]   # REG-2603 - the JOB's own if: the census steps carry always() too
        self.assertIn("\n    if: ${{ always() }}\n", head, "a failed shard skips the fan-in, and nothing says the set is broken")
        self.assertIn("pattern: proof-shard-*", job)
        self.assertNotIn("merge-multiple: true", job, "merged, the shards' one-named caches overwrite each other")
        self.assertIn('python3 tv/proof_shard.py --fan-in shards --shards "$PROOF_SHARDS" --head "$GITHUB_SHA"', job)
        hand = job[job.find("Hand the whole set on"):]
        self.assertIn("include-hidden-files: true", hand)
        self.assertNotIn("if: always()", hand, "a refused set is still handed on as if it were whole")

    def test_it_runs_only_off_main_and_no_claude_answers(self):
        text = _wf()
        on = text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertEqual(re.findall(r"- '([^']+)'", on), ["ci/proof-keys-*"], "the shard run triggers off its branches")
        self.assertNotIn("main", on)
        self.assertIn('D2R_NO_CLAUDE: "1"', text)
        self.assertIn("exit 97", text, "the runner's `claude` no longer refuses")
        self.assertIn('echo "$RUNNER_TEMP/noclaude" >> "$GITHUB_PATH"', text)
        self.assertIn("contents: read", text)

    def test_each_shard_fetches_the_commits_the_stamp_law_grades(self):
        # A 200-commit checkout does not hold RoutineIOnRealHistory.PINNED, so that class read UNMEASURED on a shard.
        import test_a_version_stamp_is_not_a_page_change as STAMP
        job = _job(_wf(), "shard")
        step = job[job.find("Fetch the commits test_a_version_stamp_is_not_a_page_change grades"):]
        step = step[:step.find("\n      - ", 1)]
        self.assertIn("git fetch --no-tags --depth=2 origin", step, "the shard no longer fetches the pinned commits")
        got = re.findall(r"\b[0-9a-f]{40}\b", step)
        for c in STAMP.RoutineIOnRealHistory.PINNED:
            if c.endswith("^"):
                continue  # depth=2 brings each pinned commit's parent
            self.assertTrue([g for g in got if g.startswith(c)], "pinned commit %s is not fetched on the shard" % c)


def _shard(root, k, n, entries, assigned, head=HEAD, stopped=None, plan="p1"):
    d = os.path.join(root, "proof-shard-%d" % k)
    os.makedirs(d)
    own = {}
    for g, i in assigned:
        own.setdefault(g, set()).add(i)
    m = PS.manifest(k, n, head, False, plan, own, None, stopped, 1761200000000)
    with io.open(os.path.join(d, PS.STORE_NAME), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"format": 2, "entries": entries, "shard": m}))


def _e(g, i, v="PROVEN"):
    return {"verdict": v, "gate": g, "proof": i, "provedAt": 1, "tree": "/home/runner/work/x/x"}


class TheFanInPassesOnlyAWholeSet(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pkfanin.")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.said = []

    def fan(self, n=2, head=HEAD):
        return PS.fan_in(self.root, n, head, say=self.said.append)

    def test_a_whole_set_passes_and_names_each_stopped_shard(self):
        _shard(self.root, 1, 2, {"a": _e("g1", 0)}, [("g1", 0)])
        _shard(self.root, 2, 2, {"b": _e("g2", 0), "c": _e("g2", 1, "BLIND")}, [("g2", 0), ("g2", 1), ("g2", 2)],
               stopped=["g2", 1, "BLIND", "green"])
        self.assertEqual(self.fan(), 0, self.said)
        out = "\n".join(self.said)
        self.assertIn("2 PROVEN entr(ies) to import, 1 not servable", out)
        self.assertRegex(out, r"shard  2/2:    3 assigned,    1 banked, STOPPED at g2\[1\] BLIND")
        self.assertNotRegex(out, r"shard  1/2:.*STOPPED")

    def test_a_missing_shard_is_refused(self):
        _shard(self.root, 1, 2, {"a": _e("g1", 0)}, [("g1", 0)])
        os.makedirs(os.path.join(self.root, "proof-shard-2"))            # an artifact with no cache in it
        self.assertEqual(self.fan(), 2)
        self.assertIn("missing", "\n".join(self.said))
        self.assertIn("proof-shard-2 carries no", "\n".join(self.said))

    def test_files_of_another_n_than_the_workflow_runs_are_refused(self):
        _shard(self.root, 1, 1, {"a": _e("g1", 0)}, [("g1", 0)])
        self.assertEqual(self.fan(n=2), 2, "a 1-shard set passed a 2-shard workflow")
        self.assertIn("N=1", "\n".join(self.said))

    def test_another_commit_is_refused(self):
        _shard(self.root, 1, 1, {"a": _e("g1", 0)}, [("g1", 0)], head="d" * 40)
        self.assertEqual(self.fan(n=1), 2)

    def test_an_entry_outside_its_shard_is_refused(self):
        _shard(self.root, 1, 1, {"a": _e("g1", 0), "z": _e("g9", 0)}, [("g1", 0)])
        self.assertEqual(self.fan(n=1), 2, "a stray entry passed the fan-in that the import would refuse")

    def test_an_extra_dir_with_no_store_is_refused_even_when_every_shard_is_there(self):
        """second eye - a whole set plus a dir with no store is not one importable set: refuse, don't hand it on"""
        _shard(self.root, 1, 1, {"a": _e("g1", 0)}, [("g1", 0)])
        os.makedirs(os.path.join(self.root, "proof-shard-stray"))
        self.assertEqual(self.fan(n=1), 2, "the fan-in handed on a set with a dir that carries no store")
        self.assertIn("carry no", "\n".join(self.said))

    def test_the_cli_reads_its_arguments(self):
        _shard(self.root, 1, 1, {"a": _e("g1", 0)}, [("g1", 0)])
        self.assertEqual(PS.main(["--fan-in", self.root, "--shards", "1", "--head", HEAD]), 0)
        self.assertEqual(PS.main(["--fan-in", self.root, "--shards", "1", "--head", "e" * 40]), 2)


RED_PROOF = [
    {"why": "shard 16 census - the pinned-commit fetch drops one, so RoutineIOnRealHistory reads UNMEASURED again",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "          f591953451f7a0aff8db3f22938c6f1ded12ce88\n",
     "replace": "",
     "matches": 1},
    {"why": "shard 16 census - the fetch is shallow-by-one, so a8246cdf^ is missing and the class skips",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "git fetch --no-tags --depth=2 origin",
     "replace": "git fetch --no-tags --depth=1 origin",
     "matches": 1},
    {"why": "REG-2588 - the matrix drops a shard: its slice is never proved and every import refuses the set",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "        shard: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]\n",
     "replace": "        shard: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]\n",
     "matches": 1},
    {"why": "REG-2588 - the cache upload drops dot-files, so .heart2_cache.json never leaves the runner",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "          path: ${{ runner.temp }}/shard-${{ matrix.shard }}/\n          include-hidden-files: true\n",
     "replace": "          path: ${{ runner.temp }}/shard-${{ matrix.shard }}/\n",
     "matches": 1},
    {"why": "REG-2588 - the fan-in is skipped when a shard fails, so a broken set is never named",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "    needs: [shard]\n    if: ${{ always() }}\n",
     "replace": "    needs: [shard]\n",
     "matches": 1},
    {"why": "REG-2588 - the fan-in passes a set whose files name another N than the workflow runs",
     "file": "proof_shard.py",
     "find": "        if got != {n} or len(shards) != n:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-2588 - the fan-in skips select(), so a stray entry the import refuses passes CI",
     "file": "proof_shard.py",
     "find": "        ok, why, take, skipped = select(shards)\n",
     "replace": "        take, skipped = {}, 0\n",
     "matches": 1},
    {"why": "REG-2588 - the fan-in hands on a set with a dir that carries no store",
     "file": "proof_shard.py",
     "find": "    if ok and empty:",
     "replace": "    if False and empty:",
     "matches": 1},
    {"why": "REG-2588 - the shard runs on main too",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "      - 'ci/proof-keys-*'\n",
     "replace": "      - 'ci/proof-keys-*'\n      - 'main'\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
