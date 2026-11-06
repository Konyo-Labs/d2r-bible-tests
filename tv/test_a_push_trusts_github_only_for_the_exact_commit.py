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
                os.makedirs(os.path.join(d, "proof-shard-1"), exist_ok=True)
                io.open(os.path.join(d, "proof-shard-1", ".heart2_cache.json"), "w").write("{}")
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

    def _ship(self, verdicts, dirty="", ff=0, wait_s=600, preflight=0, refuse_dispatch=0):
        import ship_when_green as SW
        calls, said, t = [], [], [0.0]
        feed = list(verdicts)
        refused = [refuse_dispatch]

        def run(argv, **kw):
            calls.append(list(argv))
            if argv[:3] == ["gh", "workflow", "run"] and refused[0] > 0:
                refused[0] -= 1
                return subprocess.CompletedProcess(argv, 1, "", "HTTP 502: Server Error")
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
        pf = []
        rc = SW.ship("v3862", run=run, fetch=fetch, sleep=sleep, clock=lambda: t[0], say=said.append, wait_s=wait_s,
                     preflight=lambda v, say: (pf.append(v), preflight)[1])
        self.pf_asked = pf
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

    def test_a_resumed_ship_does_not_push_ci_branches_already_at_head(self):
        """v3866 - both ci branches already at HEAD: an up-to-date push hands the hook no refs, and no refs is the full
        Mac gate; a resumed ship reads GitHub's verdict instead of pushing nothing through the whole gate."""
        import ship_when_green as SW
        listed = "%s\trefs/heads/ci/claude-v3862\n%s\trefs/heads/ci/proof-keys-v3862\n" % (SHA, SHA)
        t, calls, said = [0], [], []

        def run(argv, **kw):
            calls.append(list(argv))
            if argv[:2] == ["git", "ls-remote"]:
                return subprocess.CompletedProcess(argv, 0, listed, "")
            if argv[:3] == ["git", "status", "--porcelain"]:
                return subprocess.CompletedProcess(argv, 0, "", "")
            if argv[:3] == ["git", "rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(argv, 0, SHA + "\n", "")
            return subprocess.CompletedProcess(argv, 0, "", "")
        rc = SW.ship("v3862", run=run, fetch=lambda sha: _all_green(), sleep=lambda s: None, clock=lambda: t[0],
                     say=said.append, preflight=False)
        self.assertEqual(rc, 0, said)
        ci = [c for c in calls if "push" in c and any("refs/heads/ci/" in x for x in c)]
        self.assertEqual(ci, [], "ci branches already at HEAD were pushed again through the full gate")
        self.assertEqual(len([c for c in calls if c[:1] == ["git"] and "HEAD:main" in c]), 1, "main was not pushed")
        self.assertTrue(any("already point at" in l for l in said), said)

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

    def test_a_workflow_its_paths_did_not_fire_is_dispatched_once_on_its_own_branch(self):
        # v3865 - the proof shards are dispatched on ci/proof-keys-<v>: a run on ci/claude-<v> cannot restore the proofs its
        # version's red run banked (GitHub scopes the cache by branch) - v3864 round 3, 2026-11-05
        # v3865 (REG-3214) - the Windows set beside them runs here, so only the REQUIRED dispatch is asked of this case
        import ship_when_green as SW
        win = [_run(n, status="in_progress", conclusion=None, rid=9) for n in SW.BESIDE]
        rc, calls, mains, said = self._ship([_all_green()[:3] + win] * 6 + [_all_green() + win])
        self.assertEqual(rc, 0, said)
        disp = [c for c in calls if c[:3] == ["gh", "workflow", "run"]]
        self.assertEqual(disp, [["gh", "workflow", "run", "proof-keys-shards.yml", "--repo", CV.REPO_SLUG,
                                 "--ref", "ci/proof-keys-v3862"]])
        import ship_when_green as SW
        self.assertEqual(SW.dispatch_ref(CV.REQUIRED[0], "v3862"), "ci/claude-v3862", "the other workflows left their branch")

    def test_a_refused_dispatch_is_asked_again_on_the_next_poll(self):
        # v3865 - GitHub answered HTTP 500/502 to two dispatches on 2026-11-05; asked once, the ship would have waited 5 h
        import ship_when_green as SW
        win = [_run(n, status="in_progress", conclusion=None, rid=9) for n in SW.BESIDE]     # REG-3214 - it runs here
        rc, calls, mains, said = self._ship([_all_green()[:3] + win] * 8 + [_all_green() + win], refuse_dispatch=2)
        self.assertEqual(rc, 0, said)
        disp = [c for c in calls if c[:3] == ["gh", "workflow", "run"]]
        self.assertEqual(len(disp), 3, "a refused dispatch was not asked again (or a granted one was asked twice): %r" % disp)
        self.assertTrue(any("REFUSED (try 1" in l for l in said), said)

    def test_a_red_or_unknown_pre_flight_pushes_nothing(self):
        # v3865 (his ask 2026-11-05: "not to re-run another 40 minutes everytime") - what GitHub would find first is
        # looked for on this PC first; a red one never reaches GitHub
        for code, want in ((1, 1), (2, 2)):
            with self.subTest(preflight=code):
                rc, calls, mains, said = self._ship([_all_green()], preflight=code)
                self.assertEqual(rc, want, said)
                self.assertEqual(self.pf_asked, ["v3862"], "the pre-flight was not asked about this version")
                self.assertFalse([c for c in calls if "push" in c], "pushed to GitHub over a %s pre-flight" % code)
        rc, calls, mains, said = self._ship([_all_green()])
        self.assertEqual((rc, self.pf_asked), (0, ["v3862"]), said)


RED_PROOF = [
    {"why": "v3866 - a resumed ship pushes ci branches already at HEAD, and the empty ref list runs the full Mac gate",
     "file": "tv/ship_when_green.py",
     "find": "    if have.returncode == 0 and all(at.get(r) == sha for r in ci_refs):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3865 - a red pre-flight still pushes the version to GitHub",
     "file": "tv/ship_when_green.py",
     "find": "        if pcode != 0:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "v3865 - the proof shards are dispatched on ci/claude-<v>, where the banked proofs cannot be restored",
     "file": "tv/ship_when_green.py",
     "find": "    return (\"ci/proof-keys-%s\" if (WORKFLOW_FILES.get(wf) or BESIDE.get(wf)) in (\"proof-keys-shards.yml\",\n"
             "                                                                                   \"proof-keys-windows.yml\")\n"
             "            else \"ci/claude-%s\") % version\n",
     "replace": "    return \"ci/claude-%s\" % version\n",
     "matches": 1},
    {"why": "v3865 - a refused dispatch is never asked again",
     "file": "tv/ship_when_green.py",
     "find": "                tries[wf] = -1 if d.returncode == 0 else n + 1\n",
     "replace": "                tries[wf] = -1\n",
     "matches": 1},
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
