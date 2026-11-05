# -*- coding: utf-8 -*-
"""v3862 - THE PRE-PUSH TRUSTS GITHUB ONLY FOR THE EXACT COMMIT, ONLY ON A CLEAN TREE, AND NEVER ON AN UNKNOWN.

His ruling 2026-11-05 (the normal model): GitHub grades and proves each version once; the Mac stops re-grading 1,482 gates
serially for 1-2 h per push. The night before, v3860 and v3861 took 8 pushes between them and every refusal was a Mac-only
artifact while GitHub had graded the same bytes green. The skip is the dangerous half of that, so it is pinned four ways:
  · GREEN only when every REQUIRED workflow's NEWEST run on THIS sha succeeded (another sha, a later red re-run, a run
    still going, a missing workflow - all NOT);
  · UNKNOWN (gh unreachable) is never green;
  · the hook asks only when HEAD is the pushed commit AND `git status --porcelain` is empty (a dirty tree is graded in
    full - the pre-push grades the WORKING TREE, REG-1131, and GitHub never saw those bytes);
  · under trust, local proving is replaced by importing GitHub's proof shards, and a failed import proves locally.
"""
import ast
import io
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import ci_verdict as CV  # noqa: E402

SHA = "a" * 40
OTHER = "b" * 40


def _run(wf, sha=SHA, status="completed", conclusion="success", at="2026-11-05T10:00:00Z", rid=1):
    return {"workflowName": wf, "headSha": sha, "status": status, "conclusion": conclusion, "createdAt": at,
            "databaseId": rid}


def _all_green(sha=SHA):
    return [_run(wf, sha=sha, rid=i + 1) for i, wf in enumerate(CV.REQUIRED)]


class TheVerdict(unittest.TestCase):

    def test_every_required_workflow_green_on_this_commit_is_green(self):
        v, why = CV.decide(_all_green(), SHA)
        self.assertEqual(v, "green", why)

    def test_a_missing_workflow_is_not_green_and_is_named(self):
        runs = _all_green()[1:]
        v, why = CV.decide(runs, SHA)
        self.assertEqual(v, "not")
        self.assertIn(CV.REQUIRED[0], why)

    def test_green_on_another_commit_never_vouches_for_this_one(self):
        self.assertEqual(CV.decide(_all_green(OTHER), SHA)[0], "not")

    def test_a_running_or_failed_workflow_is_not_green(self):
        for status, concl in (("in_progress", None), ("completed", "failure"), ("completed", "cancelled")):
            runs = _all_green()
            runs[1] = _run(CV.REQUIRED[1], status=status, conclusion=concl)
            with self.subTest(status=status, conclusion=concl):
                self.assertEqual(CV.decide(runs, SHA)[0], "not")

    def test_a_red_rerun_after_a_green_run_is_red(self):
        runs = _all_green() + [_run(CV.REQUIRED[0], conclusion="failure", at="2026-11-05T11:00:00Z", rid=99)]
        self.assertEqual(CV.decide(runs, SHA)[0], "not", "an older green run outvoted the newest red one")

    def test_github_unreachable_is_unknown_never_green(self):
        self.assertEqual(CV.decide(None, SHA)[0], "unknown")
        self.assertEqual(CV.decide(_all_green(), "")[0], "unknown")

    def test_the_cli_exits_by_the_verdict(self):
        def fake(argv, *a, **k):
            return subprocess.CompletedProcess(argv, 1, "", "no network")
        self.assertIsNone(CV.fetch(SHA, run=fake), "a failed gh read became a list")


class TheProofImport(unittest.TestCase):

    def test_no_download_when_the_verdict_is_not_green(self):
        calls = []

        def fake(argv, *a, **k):
            calls.append(list(argv))
            if argv[:3] == ["gh", "run", "list"]:
                import json
                return subprocess.CompletedProcess(argv, 0, json.dumps(_all_green()[1:]), "")
            raise AssertionError("downloaded or imported under a NOT verdict: %r" % (argv,))
        ok, why = CV.import_proofs(SHA, run=fake)
        self.assertFalse(ok)
        self.assertEqual([c[:3] for c in calls], [["gh", "run", "list"]])

    def test_green_downloads_this_commits_shards_and_hands_them_to_heart2(self):
        import json
        seen = {}

        def fake(argv, *a, **k):
            if argv[:3] == ["gh", "run", "list"]:
                return subprocess.CompletedProcess(argv, 0, json.dumps(_all_green()), "")
            if argv[:3] == ["gh", "run", "download"]:
                seen["download"] = list(argv)
                d = argv[argv.index("-D") + 1]
                os.makedirs(os.path.join(d, "proof-shard-1"), exist_ok=True)
                io.open(os.path.join(d, "proof-shard-1", ".heart2_cache.json"), "w").write("{}")
                return subprocess.CompletedProcess(argv, 0, "", "")
            if "--import-shards" in argv:
                seen["import"] = list(argv)
                return subprocess.CompletedProcess(argv, 0, "imported", "")
            raise AssertionError("unexpected %r" % (argv,))
        ok, why = CV.import_proofs(SHA, run=fake)
        self.assertTrue(ok, why)
        self.assertIn("proof-shards-" + SHA, seen["download"], "the artifact of another commit could be imported")
        self.assertTrue(any(a.endswith(".heart2_cache.json") for a in seen["import"]))

    def test_a_refused_import_is_a_failure_so_the_hook_proves_locally(self):
        import json

        def fake(argv, *a, **k):
            if argv[:3] == ["gh", "run", "list"]:
                return subprocess.CompletedProcess(argv, 0, json.dumps(_all_green()), "")
            if argv[:3] == ["gh", "run", "download"]:
                d = argv[argv.index("-D") + 1]
                io.open(os.path.join(d, "x.json"), "w").write("{}")
                return subprocess.CompletedProcess(argv, 0, "", "")
            return subprocess.CompletedProcess(argv, 1, "", "a partial set")
        ok, why = CV.import_proofs(SHA, run=fake)
        self.assertFalse(ok)
        self.assertIn("refused", why)


class TheHookAsksOnlyWhenItMayTrust(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(os.path.join(ROOT, "hooks", "pre-push"), encoding="utf-8") as fh:
            cls.code = "\n".join(l for l in fh.read().split("\n") if not l.lstrip().startswith("#"))

    def test_the_trust_check_needs_the_exact_commit_and_a_clean_tree(self):
        line = ('if [ -n "${_se_local:-}" ] && [ "$(git rev-parse HEAD 2>/dev/null)" = "$_se_local" ] '
                '&& [ -z "$(git status --porcelain 2>/dev/null)" ]; then')
        self.assertEqual(self.code.count(line), 1, "the trust check no longer demands the exact commit and a clean tree")
        self.assertIn('if _ci_line="$(python3 "$REPO/tv/ci_verdict.py" "$_se_local" 2>&1)"; then', self.code)

    def test_only_the_trusted_path_skips_the_suites_and_the_gate_set(self):
        self.assertIn('if [ "$_ci_trust" = 1 ] && [ -n "$_tv_lane" ]; then', self.code)
        i = self.code.index('if [ "$_ci_trust" = 1 ]; then\n  echo "pre-push: [$(_pp_el)] ⏭  the gate set ran on GitHub')
        j = self.code.index('python3 "$REPO/tv/run_gates.py" --fast', i)
        self.assertLess(i, j, "the fast gate set is no longer behind the trust check")

    def test_a_failed_import_falls_back_to_local_proving(self):
        a = self.code.index('if [ "$_ci_trust" = 1 ] && python3 "$REPO/tv/ci_verdict.py" --import "$_se_local"')
        b = self.code.index('elif python3 "$REPO/tv/heart2.py" --prove $_gates --push', a)
        self.assertLess(a, b)


RED_PROOF = [
    {"why": "v3862 - a green run on ANOTHER commit vouches for this one",
     "file": "tv/ci_verdict.py",
     "find": "    mine = [r for r in runs if isinstance(r, dict) and str(r.get(\"headSha\") or \"\").startswith(sha)]\n",
     "replace": "    mine = [r for r in runs if isinstance(r, dict)]\n",
     "matches": 1},
    {"why": "v3862 - an older green run outvotes the newest red re-run",
     "file": "tv/ci_verdict.py",
     "find": "        last = rs[-1]\n",
     "replace": "        last = next((r for r in rs if r.get(\"conclusion\") == \"success\"), rs[-1])\n",
     "matches": 1},
    {"why": "v3862 - GitHub unreachable reads as green",
     "file": "tv/ci_verdict.py",
     "find": "    if runs is None:\n        return \"unknown\",",
     "replace": "    if runs is None:\n        return \"green\",",
     "matches": 1},
    {"why": "v3862 - a DIRTY tree is trusted on GitHub's verdict for the commit (the pre-push grades the working tree)",
     "file": "hooks/pre-push",
     "find": " && [ -z \"$(git status --porcelain 2>/dev/null)\" ]; then\n  if _ci_line=",
     "replace": "; then\n  if _ci_line=",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
