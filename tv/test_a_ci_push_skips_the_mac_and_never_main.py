# -*- coding: utf-8 -*-
"""#182 (his go 2026-10-06) - A ci/* PUSH IS GRADED ON GITHUB; ANYTHING NAMING main PAYS THE FULL MAC GATE.

63 Grok commits sat unpushed for two days because every push - a branch included - paid the full Mac
gate, so no CI saw them and four HIGH defects stacked. hooks/pre-push now asks tv/push_lane.py which
lane a push takes. What is pinned here, each seen RED:
  1. the decider: only refs that are ALL refs/heads/ci/<name> take the ci-only lane; main (even a
     deletion of main), a tag, any other branch, an empty ci/ name, a bad line -> full
  2. the REAL hook, run up to the end of its lane block with a marker where the gates begin: a ci-only
     push exits 0 there with the loud line; a main push falls through to the gates
  3. a ci/* branch never deploys: publish.yml runs on main only
"""
import io
import os

#: #107 - this law drives hooks/pre-push or a Linux job's own bash. Neither runs on Windows (only the Mac pushes; the job
#: runs on ubuntu), and Windows' bash there is the WSL launcher or Git Bash with backslash paths - nothing to measure
_RUNS_POSIX_HOOKS = os.name != "nt"
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import push_lane as PL  # noqa: E402

SHA = "a" * 40
ZERO = "0" * 40
HOOK = os.path.join(REPO, "hooks", "pre-push")
END = "# <<< ci-only lane\n"


def line(remote, local_sha=SHA):
    return "refs/heads/x %s %s %s" % (local_sha, remote, ZERO)


class TheDeciderFailsTowardTheFullGate(unittest.TestCase):

    def test_every_ref_on_ci_is_ci_only(self):
        self.assertEqual("ci-only", PL.lane(line("refs/heads/ci/signin"))[0])
        self.assertEqual("ci-only", PL.lane(line("refs/heads/ci/a") + "\n" + line("refs/heads/ci/b"))[0])

    def test_one_ref_that_is_not_ci_makes_it_full(self):
        for other in ("refs/heads/main", "refs/heads/signin", "refs/tags/v3596", "refs/heads/cix/a",
                      "refs/heads/ci/", "refs/heads/ci"):
            self.assertEqual("full", PL.lane(line("refs/heads/ci/signin") + "\n" + line(other))[0], other)

    def test_a_deletion_of_main_is_still_full(self):
        txt = line("refs/heads/ci/signin") + "\n" + line("refs/heads/main", local_sha=ZERO)
        self.assertEqual("full", PL.lane(txt)[0])

    def test_nothing_that_ships_and_a_bad_line_are_full(self):
        self.assertEqual("full", PL.lane("")[0])
        self.assertEqual("full", PL.lane(line("refs/heads/ci/old", local_sha=ZERO))[0])
        self.assertEqual("full", PL.lane("refs/heads/ci/x only-three fields")[0])


class TheRealHookStopsOnlyForCi(unittest.TestCase):
    """Runs hooks/pre-push itself, cut at the end of its lane block, with a marker where the gates begin."""

    def _run(self, refs):
        if not _RUNS_POSIX_HOOKS:
            self.skipTest("hooks/pre-push runs only where pushes happen (the Mac) - never on Windows")
        with io.open(HOOK, encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(1, src.count(END), "the lane block's end marker is not in the hook once")
        prefix = src[:src.index(END) + len(END)] + 'echo "FELL-THROUGH-TO-THE-GATES"\nexit 3\n'
        fd, p = tempfile.mkstemp(prefix=".lane_hook_", suffix=".sh", dir=HERE)
        try:
            with io.open(fd, "w", encoding="utf-8") as fh:
                fh.write(prefix)
            env = os.environ.copy()
            # The lane law does not start the agent suite, and it does not scan the Chrome
            # ports the rest of the gate is using. Inheriting those made this check sit
            # until its own budget killed it.
            env["SUITE_VERDICT_REUSE"] = "0"
            env["TV_RENDER_PORT_FROM"] = "39124"
            r = subprocess.run(["bash", p, "origin", "https://example.invalid/repo.git"], input=refs, cwd=REPO,
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40,
                               env=env)
        finally:
            os.unlink(p)
        return r.returncode, r.stdout + r.stderr

    def test_a_ci_only_push_stops_before_any_gate_and_says_so(self):
        rc, out = self._run(line("refs/heads/ci/signin") + "\n")
        self.assertIn("CI-ONLY PUSH", out)
        self.assertNotIn("FELL-THROUGH-TO-THE-GATES", out, "a ci-only push walked into the Mac gates")
        self.assertEqual(0, rc, out[-600:])

    def test_a_push_naming_main_goes_to_the_gates(self):
        rc, out = self._run(line("refs/heads/ci/signin") + "\n" + line("refs/heads/main") + "\n")
        self.assertNotIn("CI-ONLY PUSH", out)
        self.assertIn("FELL-THROUGH-TO-THE-GATES", out)
        self.assertEqual(3, rc, out[-600:])


class ACiBranchNeverDeploys(unittest.TestCase):

    def test_publish_runs_on_main_only(self):
        with io.open(os.path.join(REPO, ".github", "workflows", "publish.yml"), encoding="utf-8") as fh:
            y = fh.read()
        code = "\n".join(l.split("#", 1)[0] for l in y.split("\n"))
        m = re.search(r"\n\s*push:\s*\n\s*branches:\s*\[([^\]]*)\]", code)
        self.assertIsNotNone(m, "publish.yml no longer pins its push trigger to named branches")
        self.assertEqual(["main"], [b.strip().strip("'\"") for b in m.group(1).split(",") if b.strip()])



class ACiPushStartsNoSuiteOnThisMac(unittest.TestCase):
    """v3861 - the hook read its ref lines only AFTER the fast-gate overlap, so every ci/* push of tv/ python started a
    background test_agent on his Mac and then left by the ci-only lane with it running (the case above sets
    SUITE_VERDICT_REUSE=0 for exactly that reason). The refs are read first now, and the overlap skips a ci-only push.
    Graded on the hook's code with its comments stripped: whether a real push would start the suite depends on the
    push range, which differs per checkout, so a run of the hook here could not see a regression on every tree."""

    def test_the_refs_are_read_first_and_the_overlap_skips_a_ci_push(self):
        with io.open(HOOK, encoding="utf-8") as fh:
            code = "\n".join(l for l in fh.read().split("\n") if not l.lstrip().startswith("#"))
        read = '_PUSH_REFS="$(cat)"'
        lane = ('_pp_lane_early="$(printf \'%s\\n\' "$_PUSH_REFS" | python3 "$REPO/tv/push_lane.py" 2>/dev/null)" '
                '|| _pp_lane_early="full"')
        start = 'python3 "$REPO/tv/suite_verdict.py" --run test_agent'
        self.assertEqual(code.count(read), 1, "the ref lines are not read exactly once")
        self.assertEqual(code.count(lane), 1, "the early lane is not decided from those refs")
        self.assertEqual(code.count(start), 1)
        self.assertLess(code.index(read), code.index(lane))
        self.assertLess(code.index(lane), code.index(start), "the overlap starts before the push's refs are known")
        self.assertIn('&& [ "${SUITE_VERDICT_REUSE:-1}" != "0" ] && [ "$_pp_lane_early" != "ci-only" ]; then', code,
                      "a ci-only push starts test_agent on this Mac again")

RED_PROOF = [
    {"why": "v3861 - a ci-only push starts a background test_agent on his Mac again",
     "file": "hooks/pre-push",
     "find": ' && [ "$_pp_lane_early" != "ci-only" ]; then\n',
     "replace": "; then\n",
     "matches": 1},
    {"why": "v3861 - the ref lines are read after the overlap again, so it cannot know a push is ci-only",
     "file": "hooks/pre-push",
     "find": '_PUSH_REFS="$(cat)"\n_pp_lane_early=',
     "replace": "_pp_lane_early=",
     "matches": 1},
    {
        "why": "#182 - a push that names main (a deletion of main beside a ci push) takes the ci-only lane",
        "file": "tv/push_lane.py",
        "find": "        if rr == MAIN:\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "#182 - a push mixing ci/* with another branch skips the Mac gate",
        "file": "tv/push_lane.py",
        "find": "    other = [r for r in ships if not (r.startswith(CI_PREFIX) and len(r) > len(CI_PREFIX))]\n",
        "replace": "    other = []\n",
        "matches": 1,
    },
    {
        "why": "#182 - the hook prints the ci-only line and then walks into the Mac gates anyway",
        "file": "hooks/pre-push",
        "find": "          (gh run list --branch <the ci branch>). Nothing deploys. Shipping to main still pays the full gate.\"\n  exit 0\n",
        "replace": "          (gh run list --branch <the ci branch>). Nothing deploys. Shipping to main still pays the full gate.\"\n",
        "matches": 1, "needs": "posix",
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
