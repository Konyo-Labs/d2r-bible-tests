# -*- coding: utf-8 -*-
"""REG-1642 — A SHELL LAW ON A PC WITH NO REAL BASH IS UNMEASURED, NEVER RED AND NEVER A CRASH.

The v3535 cross-family eye (2026-10-01), both halves reproduced before this was written:
  1. test_the_gate_never_adopts_a_browser_it_did_not_start's `skipIf(bash absent)` sat on the WRONG class after
     REG-1632 inserted the resolver's class under it: the resolver cases (which need no shell) were skipped, and the
     four cases that RUN the hook's snippet were not - measured with no bash on PATH: 4 ERRORS, FileNotFoundError.
  2. Every caller did `posix_shell.bash() or "bash"`. bash() answers None when the PC has no real POSIX bash, and
     `or "bash"` then ran whatever `bash` names - on a Windows PC the WSL launcher, which runs nothing, so the law
     read RED there: the lock-shut outcome REG-1632 existed to end. The sibling sweep found two more laws that ran a
     bare "bash" and never asked the resolver at all (the render gate's hook syntax, the launcher guard in
     test_control) - on the ALT the first was in its live proving slice.

  · DRIVEN: each shell-driving case runs in a child whose environment cannot resolve a real bash (an empty PATH, and
    on Windows no Program Files / LocalAppData to find Git in). It must be SKIPPED with UNMEASURED in its reason -
    never an error, never a failure - and the resolver's own cases must still RUN, because they need no shell.
  · PREMISE: on this PC, with its real PATH, the resolver finds a bash and the stamp case really runs - so the skip
    above is the PC's answer, not a skip that fires everywhere.
RED_PROOF below. [[unknown-stays-unknown]] [[strictness-that-closes-the-lane]]
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_ledgers as _fx_ledgers  # noqa: E402  the children inherit the redirect
_fx_ledgers.redirect()
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import posix_shell as PS  # noqa: E402

#: every case that runs a shell snippet, by unittest id - and the resolver cases that must NOT be skipped
SHELL_CASES = (
    "test_the_gate_never_adopts_a_browser_it_did_not_start.TheGateNeverAdoptsABrowserItDidNotStart"
    ".test_premise_with_nothing_held_the_first_port_is_chosen",
    "test_the_gate_never_adopts_a_browser_it_did_not_start.TheGateNeverAdoptsABrowserItDidNotStart"
    ".test_a_held_port_is_skipped",
    "test_the_gate_never_adopts_a_browser_it_did_not_start.TheGateNeverAdoptsABrowserItDidNotStart"
    ".test_a_full_window_refuses_and_never_adopts",
    "test_the_gate_never_adopts_a_browser_it_did_not_start.TheGateNeverAdoptsABrowserItDidNotStart"
    ".test_never_his_ports",
    "test_every_push_line_carries_its_elapsed_time.EveryPushLineIsTimed.test_the_stamp_is_the_real_elapsed_time",
    "test_the_launcher_brings_a_running_console_forward.TheShellBlockRunsUnderSetE.test_replace_it_goes_on_to_launch",
    "test_the_launcher_brings_a_running_console_forward.TheShellBlockRunsUnderSetE.test_brought_forward_ends_the_launch",
    "test_the_render_gate_runs_before_the_proving_stage.TheRenderGateRunsBeforeTheProvingStage"
    ".test_bash_accepts_the_hook",
    "test_control.TestV2012TheLauncherDoesNotRaceItself.test_a_free_port_is_never_blocked",
)
RESOLVER_CASES = (
    "test_the_gate_never_adopts_a_browser_it_did_not_start.TheLawsBashIsAPosixBash"
    ".test_the_wsl_launcher_is_never_the_answer",
    "test_the_gate_never_adopts_a_browser_it_did_not_start.TheLawsBashIsAPosixBash"
    ".test_no_real_bash_is_none_never_the_launcher",
    "test_the_gate_never_adopts_a_browser_it_did_not_start.TheLawsBashIsAPosixBash.test_a_real_bash_on_path_is_kept",
)


def _no_bash_env(empty_dir):
    # #107 (REG-3801) - os.environ's keys are UPPER-CASE on Windows (PROGRAMFILES), so popping "ProgramFiles" from its
    # copy removed nothing: GitHub windows-latest on v3901 kept Program Files, found Git's bash, and the first shell
    # case read ok. Every key is matched without case.
    drop = ("PATH", "PROGRAMFILES", "PROGRAMW6432", "PROGRAMFILES(X86)", "LOCALAPPDATA")
    env = {k: v for k, v in os.environ.items() if k.upper() not in drop}
    env["PATH"] = empty_dir
    return env


#: the child's runner: every verdict by test id, as ONE JSON line - never scraped from -v text, which warnings
#: interleave (measured: a ResourceWarning landed between "..." and "ok" and the case read as never reported)
_RUNNER = r"""
import json, sys, unittest
class R(unittest.TestResult):
    def __init__(self):
        unittest.TestResult.__init__(self); self.v = {}
    def addSuccess(self, t): self.v[t.id()] = "ok"
    def addSkip(self, t, why): self.v[t.id()] = "skipped: " + str(why)
    def addError(self, t, e): self.v[t.id()] = "ERROR: " + self._exc_info_to_string(e, t)[-300:]
    def addFailure(self, t, e): self.v[t.id()] = "FAIL: " + self._exc_info_to_string(e, t)[-300:]
r = R()
unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:]).run(r)
print("VERDICTS " + json.dumps(r.v))
"""


def _run(ids, env, resolver=None):
    """-> ({test id: 'ok' | 'skipped: <reason>' | 'ERROR: ...' | 'FAIL: ...'}, tail for a message).
    `resolver`: a bash path the child's posix_shell.bash() answers with, whatever PATH says."""
    import json
    code = _RUNNER if resolver is None else (
        "import posix_shell\nposix_shell.bash = lambda *a, **k: %r\n" % resolver) + _RUNNER
    r = subprocess.run([sys.executable, "-W", "ignore", "-c", code] + list(ids), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600, cwd=HERE, env=env)
    for line in reversed((r.stdout or "").splitlines()):
        if line.startswith("VERDICTS "):
            return json.loads(line[len("VERDICTS "):]), (r.stderr or "")[-900:]
    return {}, "the child printed no verdicts (exit %s): %s" % (r.returncode, (r.stderr or "")[-900:])


@unittest.skipIf(PS.bash(which=lambda n: None, platform=sys.platform, env={}) is not None,
                 "on this platform an empty PATH still resolves a bash - the no-bash PC cannot be staged here")
class AShellLawWithoutARealBashIsUnmeasured(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._empty = tempfile.mkdtemp(prefix="nobash-")
        cls.got, cls.tail = _run(SHELL_CASES + RESOLVER_CASES, _no_bash_env(cls._empty))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._empty, ignore_errors=True)

    def _verdict(self, case):
        if case not in self.got:
            self.fail("PREMISE: %s never reported a verdict, so this proves nothing:\n%s" % (case, self.tail))
        return self.got[case]

    def test_every_shell_case_is_skipped_as_unmeasured(self):
        for case in SHELL_CASES:
            v = self._verdict(case)
            self.assertTrue(v.startswith("skipped"), "%s on a PC with no real bash read %s - it must be SKIPPED as "
                                                     "unmeasured, never run whatever `bash` names:\n%s"
                            % (case, v, self.tail))
            self.assertIn("UNMEASURED", v, "%s was skipped without saying it is unmeasured: %s" % (case, v))

    def test_the_resolver_cases_still_run_without_a_shell(self):
        for case in RESOLVER_CASES:
            self.assertEqual(self._verdict(case), "ok", "%s needs no shell and must RUN on every PC:\n%s"
                             % (case, self.tail))


@unittest.skipIf(sys.platform.startswith("win"),
                 "a fake launcher named `bash` cannot be staged without an .exe here - UNMEASURED on this venue, "
                 "measured on the Mac and on CI")
class ALauncherNamedBashIsNeverRun(unittest.TestCase):
    """The ALT's measured shape: `bash` on PATH is a launcher that runs nothing, while the resolver knows the real
    bash. Every shell case must run the RESOLVER'S bash and pass - one that runs the name gets the launcher."""

    @classmethod
    def setUpClass(cls):
        cls.real = PS.bash()
        if cls.real is None:
            raise unittest.SkipTest("no real bash on this PC to hand the resolver - UNMEASURED")
        cls._fake = tempfile.mkdtemp(prefix="fakebash-")
        cls.fake = os.path.join(cls._fake, "bash")
        with io.open(cls.fake, "w", encoding="utf-8") as fh:
            fh.write('#!/bin/sh\necho "Windows Subsystem for Linux has no installed distributions." >&2\nexit 1\n')
        os.chmod(cls.fake, 0o755)
        cls.env = dict(os.environ, PATH=cls._fake + os.pathsep + os.environ.get("PATH", ""))
        cls.got, cls.tail = _run(SHELL_CASES, cls.env, resolver=cls.real)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(getattr(cls, "_fake", ""), ignore_errors=True)

    def test_premise_the_name_bash_is_the_launcher_and_it_runs_nothing(self):
        self.assertEqual(shutil.which("bash", path=self.env["PATH"]), self.fake)
        r = subprocess.run(["bash", "-c", "echo RAN"], capture_output=True, text=True, env=self.env, timeout=30)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("RAN", r.stdout)

    def test_every_shell_case_runs_the_resolvers_bash(self):
        for case in SHELL_CASES:
            v = self.got.get(case)
            self.assertEqual(v, "ok", "%s read %s with a launcher named `bash` first on PATH - it ran the NAME, not "
                                      "the bash the resolver found (on the ALT that reads RED):\n%s"
                             % (case, v, self.tail))


class OnThisPCTheShellCasesReallyRun(unittest.TestCase):

    def test_premise_a_real_bash_runs_the_stamp_case(self):
        if PS.bash() is None:
            self.skipTest("this PC has no real POSIX bash - the premise cannot be staged here (UNMEASURED)")
        case = SHELL_CASES[4]
        got, tail = _run([case], dict(os.environ))
        v = got.get(case)
        self.assertEqual(v, "ok", "with this PC's own bash the stamp case did not run (%r) - a skip that fires "
                                  "everywhere would make the law above vacuous:\n%s" % (v, tail))


RED_PROOF = [
    {"why": "REG-1642 - the hook cases run whatever `bash` names again (the WSL launcher on a Windows PC)",
     "file": "test_the_gate_never_adopts_a_browser_it_did_not_start.py",
     "find": "_BASH = PS.bash()\n", "replace": "_BASH = PS.bash() or \"bash\"\n", "matches": 1},
    {"why": "REG-1642 - the skip lands on the resolver's class again, which needs no shell",
     "file": "test_the_gate_never_adopts_a_browser_it_did_not_start.py",
     "find": "class TheLawsBashIsAPosixBash(unittest.TestCase):\n",
     "replace": "@_NEEDS_BASH\nclass TheLawsBashIsAPosixBash(unittest.TestCase):\n", "matches": 1},
    {"why": "REG-1642 - the push-stamp case runs with no bash instead of saying it is unmeasured",
     "file": "test_every_push_line_carries_its_elapsed_time.py",
     "find": "        if _bash is None:           # REG-1642", "replace": "        if False:           # REG-1642",
     "matches": 1},
    {"why": "REG-1642 - the launcher block runs with no bash instead of saying it is unmeasured",
     "file": "test_the_launcher_brings_a_running_console_forward.py",
     "find": "            if _bash is None:           # REG-1642", "replace": "            if False:           # REG-1642",
     "matches": 1},
    {"why": "REG-1642 - the hook's syntax check runs a bare `bash` again (the WSL launcher on the ALT)",
     "file": "test_the_render_gate_runs_before_the_proving_stage.py",
     "find": "        r = subprocess.run([_bash, \"-n\", HOOK]", "replace": "        r = subprocess.run([\"bash\", \"-n\", HOOK]",
     # REG-2357 - its only catching case is ALauncherNamedBashIsNeverRun's, which skips on Windows: BLIND there
     "matches": 1, "needs": "posix"},
    {"why": "REG-1642 - the launcher guard in test_control runs a bare `bash` again",
     "file": "test_control.py",
     "find": "        r = subprocess.run([_bash, sh, str(port), str(grace)]",
     "replace": "        r = subprocess.run([\"bash\", sh, str(port), str(grace)]",
     # REG-2357 - its only catching case is ALauncherNamedBashIsNeverRun's, which skips on Windows: BLIND there
     "matches": 1, "needs": "posix"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
