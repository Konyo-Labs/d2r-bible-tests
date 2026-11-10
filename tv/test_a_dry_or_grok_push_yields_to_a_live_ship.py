# -*- coding: utf-8 -*-
"""REG-3653 - A DRY OR GROK CI PUSH YIELDS TO A LIVE SHIP.

Attempt 10 (sha 518744bfd): the proof-keys fan-in sat queued on ubuntu-latest
for about 21 minutes (15:47-16:08 IST) behind our own dry-v3894,
grok/v3894-merge and grok/ship-system CI jobs. While a real ship
(ci/claude-* or ci/proof-keys-*) is live, preship/dry-run tooling must not
launch a new dry/ or grok/ CI push, and live dry/ and grok/ runs are
cancelled so the ship's required jobs never wait on our own test runners.
"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import ship_yield as SY  # noqa: E402
import ship_when_green as SW  # noqa: E402


def _run(branch, status, rid, name="CI"):
    return {"headBranch": branch, "status": status, "databaseId": rid, "name": name}


LIVE_SHIP = [
    _run("ci/proof-keys-v3893", "in_progress", 42816227617, "proof-keys shards (ci/proof-keys-* only)"),
    _run("ci/claude-v3893", "queued", 42816227618, "TV DIABLO — agent tests"),
]
COMPETING = [
    _run("dry/v3894", "in_progress", 11, "agent tests"),
    _run("grok/v3894-merge", "queued", 12, "agent tests"),
    _run("grok/ship-system", "in_progress", 13, "agent tests"),
]
OTHER = [
    _run("main", "in_progress", 99, "Publish — gates, review, then deploy"),
    _run("ci/proof-keys-v3893", "in_progress", 42816227617, "proof-keys shards (ci/proof-keys-* only)"),
]


class _GH:
    def __init__(self, ok=True):
        self.ok = ok
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        if cmd[:3] == ["gh", "run", "cancel"]:
            return subprocess.CompletedProcess(cmd, 0 if self.ok else 1, "",
                                               "" if self.ok else "cannot cancel")
        return subprocess.CompletedProcess(cmd, 1, "", "unexpected")


class TheLawHolds(unittest.TestCase):
    def test_a_dry_or_grok_push_is_refused_while_a_ship_is_live(self):
        for branch in ("dry/v3894", "grok/v3894-merge", "grok/ship-system",
                       "refs/heads/dry/v3894"):
            ok, why = SY.may_push(branch, LIVE_SHIP)
            self.assertFalse(ok, "%s was allowed: %s" % (branch, why))
            self.assertIn("ci/proof-keys-v3893", why)

    def test_a_ship_branch_and_any_other_ref_are_never_held(self):
        for branch in ("ci/claude-v3893", "ci/proof-keys-v3893", "main",
                       "feature/foo"):
            ok, why = SY.may_push(branch, LIVE_SHIP + COMPETING)
            self.assertTrue(ok, "%s was held: %s" % (branch, why))

    def test_a_dry_push_is_allowed_when_no_ship_is_live(self):
        ok, why = SY.may_push("dry/v3894", COMPETING + [_run("main", "in_progress", 99)])
        self.assertTrue(ok, why)

    def test_unknown_github_refuses_a_dry_push_never_a_ship_push(self):
        ok, why = SY.may_push("grok/ship-system", None)
        self.assertFalse(ok, why)
        self.assertIn("UNKNOWN", why)
        self.assertTrue(SY.may_push("ci/claude-v3893", None)[0])

    def test_competing_runs_are_cancelled_and_ci_or_main_are_not(self):
        gh = _GH()
        ids = SY.cancel_competing(LIVE_SHIP + COMPETING + OTHER, gh)
        self.assertEqual(sorted(ids), [11, 12, 13])
        cancelled = [c[3] for c in gh.calls if c[:3] == ["gh", "run", "cancel"]]
        self.assertEqual(sorted(cancelled), ["11", "12", "13"])
        self.assertNotIn("99", cancelled)
        self.assertNotIn("42816227617", cancelled)

    def test_windows_proofs_and_a_dry_proof_keys_branch_are_not_a_live_ship(self):
        only_windows = [_run("ci/proof-keys-v3893", "in_progress", 42816227690,
                             "🪟 proof-keys windows (beside the ci shards, not required)")]
        self.assertEqual(SY.live_ship_runs(only_windows), [])
        self.assertTrue(SY.may_push("grok/ship-system", only_windows)[0])
        dry = [_run("ci/proof-keys-dry-v3894", "in_progress", 42825683620,
                    "proof-keys shards (ci/proof-keys-* only)")]
        self.assertEqual(SY.live_ship_runs(dry), [])
        self.assertTrue(SY.is_yield_ref("ci/proof-keys-dry-v3894"))
        # When a real ship IS live, the misnamed dry branch is cancelled.
        gh = _GH()
        ids = SY.cancel_competing(LIVE_SHIP + dry, gh)
        self.assertEqual(ids, [42825683620])

    def test_nothing_is_cancelled_when_no_ship_is_live(self):
        gh = _GH()
        self.assertEqual(SY.cancel_competing(COMPETING, gh), [])
        self.assertEqual(gh.calls, [])
        self.assertEqual(SY.cancel_competing(None, gh), [])

    def test_the_ship_calls_yield_before_the_ci_push(self):
        src = open(os.path.join(SW.REPO, "tv", "ship_when_green.py"), encoding="utf-8").read()
        needle = "SY.yield_to_ship(run=run, say=say)"
        self.assertIn(needle, src)
        # The call must happen before the ci/ refs go up, so ship jobs don't sit
        # behind dry/grok runners that were already going.
        call_at = src.index(needle)
        push_at = src.index("+HEAD:refs/heads/ci/claude-%s")
        self.assertLess(call_at, push_at, "yield ran after the ci/ push")


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            blob = open(os.path.join(SW.REPO, p["file"]), encoding="utf-8").read()
            self.assertEqual(blob.count(p["find"]), p["matches"], p["why"])


RED_PROOF = [
    {"why": "REG-3653 - the ship no longer yields runners to a live ship before the ci/ push",
     "file": "tv/ship_when_green.py",
     "find": "        SY.yield_to_ship(run=run, say=say)\n",
     "replace": "        None\n",
     "matches": 1},
    {"why": "REG-3653 - a dry/ or grok/ push is allowed while a ship is live",
     "file": "tv/ship_yield.py",
     "find": "    if not is_yield_ref(name):\n        return True, \"not a dry/ or grok/ CI push\"\n",
     "replace": "    if True:\n        return True, \"not a dry/ or grok/ CI push\"\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
