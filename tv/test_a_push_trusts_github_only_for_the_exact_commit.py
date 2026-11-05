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
  · under trust the Mac proves only the changed laws a runner cannot (Publish's own rule), never imports (each PC
    imports from the proof bank), and a rule that cannot be read proves every changed law here.
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

    def test_under_trust_only_the_macs_own_laws_are_proved_here(self):
        """v3862 - the push no longer imports (each PC imports from the proof bank, tv/proof_release.py); it proves
        only the changed laws a runner cannot, and an unreadable rule proves EVERY changed law here."""
        a = self.code.index('if [ "$_ci_trust" = 1 ] && [ -n "$_gates" ]; then')
        b = self.code.index('if _gates_mac="$(python3 "$REPO/tv/ci_verdict.py" --mac-only $_gates 2>/dev/null)"; then', a)
        c = self.code.index('_gates="$_gates_mac"', b)
        d = self.code.index("every changed law is proved here", c)
        e = self.code.index('if python3 "$REPO/tv/heart2.py" --prove $_gates --push', d)
        self.assertLess(a, e)
        self.assertNotIn("ci_verdict.py\" --import", self.code, "the push imports GitHub's proofs again (~17 min)")


class TheMacOnlySplit(unittest.TestCase):

    def test_the_rule_answers_and_an_unreadable_rule_is_none(self):
        self.assertEqual(CV.mac_only(["b", "a", "c"], rule=lambda names: {"c", "a"}), ["a", "c"])

        def broken(names):
            raise ImportError("no proof_shard")
        self.assertIsNone(CV.mac_only(["a"], rule=broken), "an unreadable rule read as 'nothing only the Mac proves'")
        self.assertIsNone(CV.mac_only(["a"], rule=lambda names: None))

    def test_the_cli_exits_2_when_the_rule_cannot_be_read(self):
        saved = CV.mac_only
        CV.mac_only = lambda names, rule=None: None
        try:
            self.assertEqual(CV.main(["--mac-only", "a"]), 2)
        finally:
            CV.mac_only = saved


class TheShipWaitsForGitHubOnTheExactCommit(unittest.TestCase):
    """v3862 - tv/ship_when_green.py: ci/ branches first, GitHub's verdict on THAT sha, main only on green."""

    def _ship(self, verdicts, dirty="", ff=0, wait_s=600):
        import ship_when_green as SW
        calls, said, t = [], [], [0.0]
        feed = list(verdicts)

        def run(argv, **kw):
            calls.append(list(argv))
            if argv[:3] == ["git", "status", "--porcelain"]:
                return subprocess.CompletedProcess(argv, 0, dirty, "")
            if argv[:3] == ["git", "rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(argv, 0, SHA + "\n", "")
            if argv[:3] == ["git", "merge-base", "--is-ancestor"]:
                return subprocess.CompletedProcess(argv, ff, "", "")
            return subprocess.CompletedProcess(argv, 0, "", "")

        def fetch(sha):
            self.assertEqual(sha, SHA, "the verdict was asked about another commit")
            return feed.pop(0) if len(feed) > 1 else feed[0]

        def sleep(s):
            t[0] += s
        rc = SW.ship("v3862", run=run, fetch=fetch, sleep=sleep, clock=lambda: t[0], say=said.append, wait_s=wait_s)
        mains = [c for c in calls if c[:1] == ["git"] and "HEAD:main" in c]
        return rc, calls, mains, said

    def test_a_dirty_tree_or_a_non_fast_forward_pushes_nothing(self):
        for kw in ({"dirty": " M tv/control_app.py\n"}, {"ff": 1}):
            with self.subTest(**kw):
                rc, calls, mains, said = self._ship([_all_green()], **kw)
                self.assertEqual(rc, 3)
                self.assertFalse([c for c in calls if "push" in c], "pushed from a tree GitHub never graded")

    def test_green_pushes_the_ci_branches_then_main_through_the_hook(self):
        rc, calls, mains, said = self._ship([_all_green()])
        self.assertEqual(rc, 0, said)
        ci = next(c for c in calls if "push" in c)
        self.assertIn("+HEAD:refs/heads/ci/claude-v3862", ci)
        self.assertIn("+HEAD:refs/heads/ci/proof-keys-v3862", ci)
        self.assertEqual(len(mains), 1)
        self.assertIn("core.hooksPath=hooks", mains[0])
        self.assertFalse(any("--no-verify" in c or "-f" in c or "--force" in c for c in mains), "main was forced")

    def test_red_stops_the_ship_and_names_the_workflow(self):
        runs = _all_green()
        runs[2] = _run(CV.REQUIRED[2], conclusion="failure")
        rc, calls, mains, said = self._ship([runs])
        self.assertEqual(rc, 1)
        self.assertEqual(mains, [], "main was pushed over a red GitHub run")
        self.assertIn(CV.REQUIRED[2], said[-1])

    def test_pending_or_unknown_never_pushes_main(self):
        for feed in ([_all_green()[:2]], [None]):
            with self.subTest(feed=feed):
                rc, calls, mains, said = self._ship(feed, wait_s=300)
                self.assertEqual(rc, 2)
                self.assertEqual(mains, [], "main was pushed without a GitHub verdict")

    def test_a_workflow_its_paths_did_not_fire_is_dispatched_once_on_the_ci_branch(self):
        rc, calls, mains, said = self._ship([_all_green()[:3]] * 6 + [_all_green()])
        self.assertEqual(rc, 0, said)
        disp = [c for c in calls if c[:3] == ["gh", "workflow", "run"]]
        self.assertEqual(disp, [["gh", "workflow", "run", "proof-keys-shards.yml", "--repo", CV.REPO_SLUG,
                                 "--ref", "ci/claude-v3862"]])


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
    {"why": "v3862 - an unreadable Mac-only rule reads as 'none': the Mac's own changed laws go unproved under trust",
     "file": "tv/ci_verdict.py",
     "find": "        return sorted(set(got)) if got is not None else None\n    except Exception:\n        return None\n",
     "replace": "        return sorted(set(got)) if got is not None else None\n    except Exception:\n        return []\n",
     "matches": 1},
    {"why": "v3862 - the hook narrows to the Mac-only laws even when the rule failed",
     "file": "hooks/pre-push",
     "find": "    if _gates_mac=\"$(python3 \"$REPO/tv/ci_verdict.py\" --mac-only $_gates 2>/dev/null)\"; then\n",
     "replace": "    if _gates_mac=\"$(python3 \"$REPO/tv/ci_verdict.py\" --mac-only $_gates 2>/dev/null || true)\"; then\n",
     "matches": 1},
    {"why": "v3862 - the ship pushes main over a red GitHub run (it waits it out instead of stopping)",
     "file": "tv/ship_when_green.py",
     "find": "        if red:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "v3862 - the ship pushes from a dirty tree, so GitHub grades bytes the Mac never sends",
     "file": "tv/ship_when_green.py",
     "find": "    if st.returncode != 0 or (st.stdout or \"\").strip():\n",
     "replace": "    if st.returncode != 0:\n",
     "matches": 1},
    {"why": "v3862 - the ship pushes main on a pending verdict",
     "file": "tv/ship_when_green.py",
     "find": "        if verdict == \"green\":\n            break\n",
     "replace": "        if verdict in (\"green\", \"not\"):\n            break\n",
     "matches": 1},
    {"why": "v3862 - a DIRTY tree is trusted on GitHub's verdict for the commit (the pre-push grades the working tree)",
     "file": "hooks/pre-push",
     "find": " && [ -z \"$(git status --porcelain 2>/dev/null)\" ]; then\n  if _ci_line=",
     "replace": "; then\n  if _ci_line=",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
