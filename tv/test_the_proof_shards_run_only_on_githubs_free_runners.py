# -*- coding: utf-8 -*-
"""v3890 (REG-3505) - THE PROOF SHARDS RUN ON GITHUB'S OWN RUNNERS, AND NO PAID-RUNNER LANE IS WIRED.

His words, 11-09: "maybe delete the ubuntu thing so we dont get mixed up?" - "the ubicloud i meant".

v3865 (his 11-05 ruling, a hard $25 a month) built a lane to run the Linux proof shards on Ubicloud's 8-core machines: a
`budget` job in proof-keys-shards.yml asked tv/ci_budget.py which machine a round could use, reading the repo variables
PROOF_RUNNER / PROOF_BUDGET_USD / PROOF_PROVERS_FAST. PROOF_RUNNER was deleted on 11-06, so every round since ran on
GitHub's free runner - and the lane still sat in the workflow, two variables and a law, reading like a paid subscription he
does not have (I told him on 11-09 "you budget $25 a month for paid Linux runners"; he has none). Gone, and INVERTED, NOT
DELETED - this law fails if it comes back:
  * every job of every workflow runs on a GitHub-hosted label (ubuntu-*, windows-*, macos-*) written out - no third-party
    runner, and no ${{ }} expression that could route a job anywhere;
  * the proof shards' job runs on ubuntu-latest with PROOF_PROVERS lanes (2 when unset), and no job asks which machine;
  * no workflow reads PROOF_RUNNER, PROOF_BUDGET_USD or PROOF_PROVERS_FAST, and tv/ci_budget.py is not in the tree.
TOMBSTONES: tv/ci_budget.py and tv/test_the_proof_budget_never_passes_its_cap.py left with the lane (REG-3505).
Reads the workflow files only; no network. RED_PROOF below.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass

WF = os.path.join(ROOT, ".github", "workflows")
#: a GitHub-hosted runner label, written out (ubuntu-latest, ubuntu-24.04, windows-latest, macos-14, ...)
HOSTED = re.compile(r"^(ubuntu|windows|macos)-[A-Za-z0-9.]+$")
#: the paid lane's variables - a workflow that reads one has wired the lane back in
GONE_VARS = ("PROOF_RUNNER", "PROOF_BUDGET_USD", "PROOF_PROVERS_FAST")


def _code(text):
    """a workflow's YAML with its comments taken off (a `#` outside quotes starts one; no line here quotes a `#`)"""
    return "\n".join(l.split("#", 1)[0].rstrip() for l in text.split("\n"))


def _read(name):
    with io.open(os.path.join(WF, name), encoding="utf-8") as fh:
        return fh.read()


def _workflows():
    return sorted(f for f in os.listdir(WF) if f.endswith((".yml", ".yaml")))


def _offending(code):
    """-> every runs-on value in this (comment-free) YAML that is not a written-out GitHub-hosted label"""
    bad = []
    for m in re.finditer(r"(?m)^\s*runs-on:\s*(.+?)\s*$", code):
        v = m.group(1).strip().strip("'\"")
        if not HOSTED.match(v):
            bad.append(v)
    return bad


def _job(code, name):
    """the text of one top-level job (`  <name>:` up to the next job at the same indent)"""
    head = "\n  %s:\n" % name
    assert code.count(head) == 1, "PREMISE: job %s appears %d times" % (name, code.count(head))
    i = code.index(head) + 1
    m = re.compile(r"(?m)^  [A-Za-z0-9_-]+:\s*$").search(code, i + len(head))
    return code[i:m.start() if m else len(code)]


class TheProofShardsRunOnlyOnGitHubsRunners(unittest.TestCase):

    def test_the_reader_sees_a_runner_that_is_not_githubs(self):
        """BASELINE: the reader is not blind - a paid label and an expression are found, GitHub's labels are not"""
        self.assertEqual(_offending("    runs-on: ubicloud-standard-8\n"), ["ubicloud-standard-8"])
        self.assertEqual(_offending("    runs-on: ${{ vars.PROOF_RUNNER || 'ubuntu-latest' }}\n"),
                         ["${{ vars.PROOF_RUNNER || 'ubuntu-latest' }}"])
        self.assertEqual(_offending("    runs-on: ubuntu-latest\n    runs-on: windows-latest\n    runs-on: macos-14\n"), [])

    def test_every_job_of_every_workflow_runs_on_a_github_hosted_label(self):
        files = _workflows()
        self.assertIn("proof-keys-shards.yml", files, "PREMISE: the proof shards' workflow is not where this law reads")
        bad, n = [], 0
        for f in files:
            code = _code(_read(f))
            n += len(re.findall(r"(?m)^\s*runs-on:", code))
            bad += ["%s: runs-on %s" % (f, v) for v in _offending(code)]
        self.assertGreater(n, 20, "PRINT THE DENOMINATOR: only %d runs-on lines across %d workflows" % (n, len(files)))
        self.assertEqual(bad, [], "a job runs somewhere that is not GitHub's own runner:\n  " + "\n  ".join(bad))

    def test_the_shards_run_on_ubuntu_latest_with_proof_provers_lanes_and_nothing_picks_the_machine(self):
        code = _code(_read("proof-keys-shards.yml"))
        shard = _job(code, "shard")
        self.assertIn("    needs: [seed]\n", shard, "the shards wait on something besides their seed - a machine picker?")
        self.assertIn("    runs-on: ubuntu-latest\n", shard)
        self.assertIn("      HEART2_PROVE_WORKERS: ${{ vars.PROOF_PROVERS || '2' }}\n", shard,
                      "the shards' lanes are not PROOF_PROVERS (2 when unset)")
        self.assertNotIn("\n  budget:\n", code, "a budget job is back in the proof shards' workflow")

    def test_no_workflow_reads_the_paid_lanes_variables_and_its_meter_is_gone(self):
        hits = []
        for f in _workflows():
            code = _code(_read(f))
            hits += ["%s reads %s" % (f, v) for v in GONE_VARS if v in code]
            if "ci_budget" in code:
                hits.append("%s runs tv/ci_budget.py" % f)
        self.assertEqual(hits, [], "\n  ".join(hits))
        self.assertFalse(os.path.exists(os.path.join(HERE, "ci_budget.py")), "tv/ci_budget.py is back in the tree")


RED_PROOF = [
    {"why": "v3890 (REG-3505) - the proof shards run wherever a repo variable says again",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "    # switched on after 11-06 (PROOF_RUNNER deleted) and is gone; test_the_proof_shards_run_only_on_githubs_free_runners holds it.\n    runs-on: ubuntu-latest\n",
     "replace": "    # switched on after 11-06 (PROOF_RUNNER deleted) and is gone; test_the_proof_shards_run_only_on_githubs_free_runners holds it.\n    runs-on: ${{ vars.PROOF_RUNNER || 'ubuntu-latest' }}\n",
     "matches": 1},
    {"why": "v3890 (REG-3505) - the Windows proof shards run on a third-party runner",
     "file": ".github/workflows/proof-keys-windows.yml",
     "find": "    runs-on: windows-latest\n",
     "replace": "    runs-on: ubicloud-standard-8\n",
     "matches": 1},
    {"why": "v3890 (REG-3505) - the shards' lanes come from the paid lane's variable again",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "      HEART2_PROVE_WORKERS: ${{ vars.PROOF_PROVERS || '2' }}\n",
     "replace": "      HEART2_PROVE_WORKERS: ${{ vars.PROOF_PROVERS_FAST || '2' }}\n",
     "matches": 1},
    {"why": "v3890 (REG-3505) - the shards wait on a machine-picking job again",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "  shard:\n    name: shard ${{ matrix.shard }}\n    needs: [seed]\n",
     "replace": "  shard:\n    name: shard ${{ matrix.shard }}\n    needs: [seed, budget]\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
