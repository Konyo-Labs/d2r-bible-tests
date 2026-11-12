# -*- coding: utf-8 -*-
"""CI SPENDS NO MINUTES ON A SLOW MIRROR, AND A CENSUS PUSH DOES NOT QUEUE BEHIND THE SUITES (gbl/ci-speed).

MEASURED 2026-10-23 on 146 "OS deps for Chromium" steps (tv-tests, Routine I, Publish): 126 finished under 60 s
(median 12 s), 19 sat on azure.archive.ubuntu.com until the 5-minute step timeout, one took 97 s. The step is
best effort (continue-on-error), so a hang never changed a verdict - it only set the slowest shard's wall: on
a2084313 tv-tests shard 4 was 19.5 min with 5.2 of it here, Routine I shard 5 16.9 min with 5.2 here.

Every such step now runs .github/scripts/chromium-os-deps.sh: no apt when Playwright's --dry-run names nothing
missing, else apt bounded at 90 s, never a red step. And tv-tests / Routine I ignore ci/proof-keys-** pushes:
the census there runs its own 16 shards, and these suites only held runners it queued behind (13-24 min).

Each case drives the real script with a fake `npx` on PATH, or reads the workflow text. RED_PROOF below.
"""
import io
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

SCRIPT = os.path.join(ROOT, ".github", "scripts", "chromium-os-deps.sh")
WF = os.path.join(ROOT, ".github", "workflows")
STEP_WORKFLOWS = ("tv-tests.yml", "routine-i-playwright.yml", "publish.yml")
SUITES = ("tv-tests.yml", "routine-i-playwright.yml")


def _read(name):
    with io.open(os.path.join(WF, name), encoding="utf-8") as fh:
        return fh.read()


def _code(text):
    """the workflow with YAML comment lines dropped - prose is never the subject"""
    return "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("#"))


class TheBoundedStep(unittest.TestCase):

    def setUp(self):
        if os.name == "nt" or shutil.which("bash") is None:
            self.skipTest("UNMEASURED - the Linux apt step is never run on Windows")
        self.d = tempfile.mkdtemp(prefix="osdeps_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.log = os.path.join(self.d, "calls")
        if shutil.which("timeout") is None:
            self.timeout_shim()

    def timeout_shim(self):
        """macOS ships no coreutils `timeout`, and a skip there left RED_PROOF [0]-[3] BLIND on his Mac's push.
        This stands in for `timeout -k K N cmd...` with the same contract the script reads: 124 when cut, and like
        coreutils it signals the whole process group, so a grandchild cannot hold the step open."""
        p = os.path.join(self.d, "timeout")
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write("#!%s\n"
                     "import os, signal, subprocess, sys\n"
                     "a = sys.argv[1:]\n"
                     "k = 10.0\n"
                     "if a[0] == '-k':\n"
                     "    k = float(a[1]); a = a[2:]\n"
                     "n = float(a[0]); cmd = a[1:]\n"
                     "p = subprocess.Popen(cmd, start_new_session=True)\n"
                     "try:\n"
                     "    sys.exit(p.wait(timeout=n))\n"
                     "except subprocess.TimeoutExpired:\n"
                     "    os.killpg(p.pid, signal.SIGTERM)\n"
                     "    try:\n"
                     "        p.wait(timeout=k)\n"
                     "    except subprocess.TimeoutExpired:\n"
                     "        os.killpg(p.pid, signal.SIGKILL); p.wait()\n"
                     "    sys.exit(124)\n" % sys.executable)
        os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)

    def npx(self, dry_out, install_sleep=0, install_rc=0, dry_rc=None):
        if dry_rc is None:   # Playwright >= 1.60 exits 1 when it names a missing package
            dry_rc = 0 if dry_out.startswith("All system") else 1
        p = os.path.join(self.d, "npx")
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\necho \"$*\" >> %s\n"
                     "case \"$*\" in *--dry-run*) printf '%%s\\n' %s; exit %d;; esac\n"
                     "sleep %s\nexit %d\n" % (self.log, "'" + dry_out + "'", dry_rc, install_sleep, install_rc))
        os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)

    def run_script(self, bound=None):
        env = dict(os.environ, PATH=self.d + os.pathsep + os.environ.get("PATH", ""))
        src = io.open(SCRIPT, encoding="utf-8").read()
        if bound is not None:   # the case may not wait 90 s: the bound under test is rewritten to 2 s, and asserted below
            src = src.replace("timeout -k 10 90 ", "timeout -k 1 %d " % bound)
        p = os.path.join(self.d, "s.sh")
        io.open(p, "w", encoding="utf-8").write(src)
        t = time.time()
        r = subprocess.run(["bash", p], env=env, capture_output=True, text=True, timeout=200)
        calls = io.open(self.log, encoding="utf-8").read().split("\n") if os.path.exists(self.log) else []
        return r, [c for c in calls if c], time.time() - t

    def test_nothing_missing_runs_no_apt(self):
        self.npx("All system dependencies are installed.")
        r, calls, _ = self.run_script()
        self.assertEqual(r.returncode, 0)
        self.assertEqual(len(calls), 1, "apt ran though the dry run named nothing missing: %r" % calls)
        self.assertIn("--dry-run", calls[0])

    def test_an_answer_that_is_not_all_installed_installs(self):
        # Playwright < 1.60 prints the apt-get command and exits 0; an empty answer is not "nothing missing" either.
        for out in ("sudo -- sh -c \"apt-get update&& apt-get install -y --no-install-recommends fonts-unifont\"", ""):
            if os.path.exists(self.log):
                os.remove(self.log)
            self.npx(out, dry_rc=0)
            _r, calls, _t = self.run_script()
            self.assertEqual([c for c in calls if "--dry-run" not in c], ["playwright install-deps chromium"], out)

    def test_something_missing_installs(self):
        self.npx("Missing system dependencies (1):\n  fonts-unifont")
        r, calls, _ = self.run_script()
        self.assertEqual(r.returncode, 0)
        self.assertEqual([c for c in calls if "--dry-run" not in c], ["playwright install-deps chromium"])

    def test_the_install_is_bounded_at_90_seconds_and_a_cut_is_not_red(self):
        src = io.open(SCRIPT, encoding="utf-8").read()
        m = re.search(r"^timeout -k \d+ (\d+) npx playwright install-deps chromium", src, re.M)
        self.assertIsNotNone(m, "the install is not under a `timeout N` bound")
        self.assertEqual(int(m.group(1)), 90, "the bound is %s s - the measured hangs start past 97 s" % m.group(1))
        self.npx("Missing system dependencies (1):\n  fonts-unifont", install_sleep=30)
        r, _calls, took = self.run_script(bound=2)
        self.assertLess(took, 20, "a hung apt was not cut by the bound (%.0f s)" % took)
        self.assertEqual(r.returncode, 0, "a cut apt made the step red")
        self.assertIn("OS deps cut", r.stdout)

    def test_a_failed_install_is_a_warning_not_a_red(self):
        self.npx("Missing system dependencies (1):\n  fonts-unifont", install_rc=100)
        r, _c, _t = self.run_script()
        self.assertEqual(r.returncode, 0)
        self.assertIn("OS deps failed", r.stdout)


class TheWorkflows(unittest.TestCase):

    def test_every_os_deps_step_runs_the_bounded_script(self):
        seen = 0
        for name in STEP_WORKFLOWS:
            code = _code(_read(name))
            self.assertNotIn("run: npx playwright install-deps", code,
                             "%s still runs apt unbounded by the script" % name)
            n = code.count("run: bash .github/scripts/chromium-os-deps.sh")
            self.assertGreaterEqual(n, 1, "%s has no bounded OS-deps step" % name)
            seen += n
        self.assertGreaterEqual(seen, 4, "a zero needs a denominator: only %d bounded steps found" % seen)

    def test_the_bounded_step_is_never_a_red(self):
        for name in STEP_WORKFLOWS:
            code = _code(_read(name))
            for m in re.finditer(r"\n((?:        [^\n]*\n)*?)        run: bash \.github/scripts/chromium-os-deps\.sh", code):
                self.assertIn("continue-on-error: true", m.group(1), "%s: an OS-deps step can fail the job" % name)

    def test_a_census_push_does_not_run_the_suites(self):
        for name in SUITES:
            code = _code(_read(name))
            push = code[code.index("\n  push:\n"):]
            push = push[:re.search(r"\n  \S", push[1:]).start() + 1] + "\n"
            self.assertRegex(push, r"\n    branches-ignore:\n      - 'ci/proof-keys-\*\*'\n",
                             "%s runs on every proof-keys census push" % name)
            self.assertIn("\n    paths:\n", push, "%s lost its paths filter" % name)

    def test_a_windows_laws_push_runs_no_other_workflow(self):
        """REG-3807 (#107, 11-12) - a NEW ci/winlaws branch is compared against main, so a paths filter alone fired Routine I,
        M, the agent suite and the Windows boot beside the one run it was for; each push workflow ignores those branches"""
        n = 0
        for f in sorted(os.listdir(WF)):
            if not f.endswith(".yml") or f == "windows-laws.yml":
                continue
            code = _code(_read(f))
            i = code.find("\n  push:\n")
            if i < 0:
                continue
            push = code[i:]
            push = push[:re.search(r"\n  \S", push[1:]).start() + 1] + "\n"
            if re.search(r"\n    branches:[ \n]", push):
                continue                     # an allow-list names its own branches (block or inline [main])
            n += 1
            self.assertIn("\n      - 'ci/winlaws-**'", push, "%s runs on a Windows-laws push" % f)
        self.assertGreaterEqual(n, 8, "a zero needs a denominator: only %d push workflows read" % n)


if __name__ == "__main__":
    unittest.main()


# REG-2687 (Dean's PC, 2026-10-27): the `timeout` stand-in kills a process GROUP (os.killpg), which Windows has no such
# signal for, so these proofs filed BLIND there and held every lock shut. Judged where POSIX signals are; ELSEWHERE on Windows.
RED_PROOF = [
    {
        "why": "gbl/ci-speed review - the skip reads 'no word missing' again, so an older Playwright's apt-get line skips apt",
        "file": "../.github/scripts/chromium-os-deps.sh",
        "find": "grep -qx 'All system dependencies are installed\\.'",
        "replace": "! grep -qi 'missing'",
        "matches": 1, "needs": "posix-signals",
    },
    {
        "why": "gbl/ci-speed - apt runs even when nothing is missing",
        "file": "../.github/scripts/chromium-os-deps.sh",
        "find": "  exit 0\nfi\n",
        "replace": "fi\n",
        "matches": 1, "needs": "posix-signals",
    },
    {
        "why": "gbl/ci-speed - the install is unbounded again",
        "file": "../.github/scripts/chromium-os-deps.sh",
        "find": "timeout -k 10 90 npx playwright install-deps chromium; rc=$?",
        "replace": "npx playwright install-deps chromium; rc=$?",
        "matches": 1, "needs": "posix-signals",
    },
    {
        "why": "gbl/ci-speed - a cut or failed install turns the step red",
        "file": "../.github/scripts/chromium-os-deps.sh",
        "find": "  echo \"::warning title=OS deps failed::npx playwright install-deps exited $rc - continuing\"\nfi\nexit 0\n",
        "replace": "  echo \"::warning title=OS deps failed::npx playwright install-deps exited $rc - continuing\"\nfi\nexit $rc\n",
        "matches": 1, "needs": "posix-signals",
    },
    {
        "why": "gbl/ci-speed - tv-tests runs apt unbounded again",
        "file": "../.github/workflows/tv-tests.yml",
        "find": "        run: bash .github/scripts/chromium-os-deps.sh\n",
        "replace": "        run: npx playwright install-deps chromium\n",
        "matches": 1, "needs": "posix-signals",
    },
    {
        "why": "gbl/ci-speed - Routine I runs on every census push again",
        "file": "../.github/workflows/routine-i-playwright.yml",
        "find": "    branches-ignore:\n      - 'ci/proof-keys-**'\n",
        "replace": "",
        "matches": 1, "needs": "posix-signals",
    },
    {
        "why": "gbl/ci-speed - tv-tests runs on every census push again",
        "file": "../.github/workflows/tv-tests.yml",
        "find": "    branches-ignore:\n      - 'ci/proof-keys-**'\n",
        "replace": "",
        "matches": 1, "needs": "posix-signals",
    },
    {"why": "REG-3807 - a Windows-laws push starts the Windows boot again",
     "file": "../.github/workflows/tv-windows-boot.yml",
     "find": "    branches-ignore:\n      - 'ci/winlaws-**'      # #107 - a Windows-laws push grades only its laws\n",
     "replace": "",
     "matches": 1, "needs": "posix-signals"},
]
