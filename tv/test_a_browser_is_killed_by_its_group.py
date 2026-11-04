#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3380 — A BROWSER IS KILLED BY ITS GROUP, OR IT IS NOT KILLED AT ALL.

THE INCIDENT THIS PINS. Five consecutive pushes were refused between 2026-09-19 23:00 and
2026-09-20 02:00. Every one of them passed all six static checks, including "every changed law
demonstrated it can still go red", and then died with:

    pre-push: test_control DID NOT FINISH in 1500s - load average 9.43. Push blocked.

The load averages were 9.44, 16.50 and 9.43. Two of the three were a QUIET machine, so the
"he is gaming" explanation was wrong and so was every bound theory built on it.

WHAT IT ACTUALLY WAS, measured rather than inferred. Two faulthandler dumps taken 120s apart named
the identical frame:

    File "tv/js_syntax_gate.py", line 357 in check
      -> subprocess.run -> communicate -> selectors.select
    File "tv/test_control.py", line 4544 in test_surfaces_parse_in_a_real_js_engine

subprocess.run(..., timeout=T) does NOT bound a browser. Its timeout path kills the LAUNCHER and
then calls communicate() a second time to drain the pipes. Chrome forks renderer/GPU/zygote
helpers that INHERIT the stdout pipe, and at least one of them reparents to launchd - measured on
this Mac as a live pid with PPID 1 while its launcher was already gone. The write end therefore
never closes, so that second communicate() blocks forever. The call is bounded on paper and
unbounded in fact.

The signature was identical four times: the gate halted at 244,189-244,190 bytes of output, and a
standalone run halted at 244,935 - the same place within 750 bytes, at 0.0% CPU.

THE BOUND WAS INNOCENT AND MUST NOT BE RAISED. Six completed runs on this exact tree measure
507.5 / 514.2 / 518.5 / 527.3 / 533.4 / 563.7 seconds against a 1500s ceiling - 2.66x margin.
Raising it would have hidden a real hang behind a bigger number.
(A separate true finding, recorded where it will be seen: hooks/pre-push's own comment claims
"the suite has never exceeded 720s", and its own kept logs contain a 773.229s run. That comment is
false and is not load-bearing for this fix.)

THE CURE ALREADY EXISTED AND WAS NEVER JOINED. tv/test_control.py:129 `_reap()` was written at
v1925 for precisely this failure, and says so in its own docstring:

    "The launcher is started in its own session, so ONE killpg reaches the renderer grandchildren
     that hold the stdout pipe open"

js_syntax_gate.py referenced `_reap` ZERO times and used bare subprocess.run instead. The knowledge
lived in one file and was absent in the neighbour that needed it - [[the-unjoined-end]].

WHAT THIS FILE PINS - behaviour first, text only where behaviour cannot reach:
  * a launcher that outlives its timeout is killed BY GROUP, so a pipe-holding grandchild dies too
  * TimeoutExpired still propagates, so v1808's "a timeout is not a syntax verdict" node fallback
    is untouched and "nobody could check" never reads as "it is broken"
  * the browser is started in its own session, which is what makes one killpg sufficient
  * check() does not reach for subprocess.run on a browser argv again
"""

import ast
import io
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    import console_safe
    console_safe.enable()
except Exception:
    pass

import js_syntax_gate as JSG

SRC = io.open(os.path.join(HERE, "js_syntax_gate.py"), encoding="utf-8").read()


def _code_only(src):
    """Strip comments so a law never grades the prose that explains it.

    [[source-reading-guard]] section 4: three of four guards in one session went red on the
    sentence describing their own fix.
    """
    return "\n".join(l.split("#", 1)[0] for l in src.split("\n"))


def _fn_src(name):
    """The named function's OWN text, bounded by the parser rather than a byte window.

    A fixed src[i:i+N] window measures my guess about someone's prose, not the file.
    """
    tree = ast.parse(SRC)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(SRC, node) or ""
    return ""


# A stand-in "browser": it forks a child that inherits stdout and holds it open, then the
# launcher itself sleeps past any timeout. That is Chrome's shape reduced to nine lines, and it
# reproduces the deadlock without needing Chrome.
FAKE_BROWSER = textwrap.dedent(
    """
    import subprocess, sys, time
    # v3861 - the grandchild is a Popen, not a fork, so the fixture is real on Windows too (no os.fork there). It is
    # handed the launcher's stdout explicitly, so it holds the very pipe the timeout must not wait on, on every OS.
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)", __file__],
                     stdout=sys.stdout, stderr=subprocess.DEVNULL)
    sys.stderr.write("launcher-up\\n")
    sys.stderr.flush()
    time.sleep(600)
    """
)


def _ours_alive(fake):
    """-> [str] the processes still running whose command line names this fixture, on either OS."""
    if os.name == "nt":
        ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*%s*' } | "
              "ForEach-Object { [string]$_.ProcessId + ' ' + $_.CommandLine }" % os.path.basename(fake))
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                             timeout=60).stdout
        return [ln.strip()[:80] for ln in out.splitlines() if ln.strip() and "Get-CimInstance" not in ln]
    return [ln.strip()[:80] for ln in os.popen("ps -eo pid,command").read().splitlines()[1:] if fake in ln]


class ABrowserIsKilledByItsGroup(unittest.TestCase):

    # ---------- the behavioural proof ----------

    # v3861 - NOW REAL ON WINDOWS TOO. v3860 pinned this to POSIX because the fake forked; the grandchild is a Popen now,
    # and on Windows the timeout path ends the tree with `taskkill /T` (there is no process group to kill).
    def test_a_pipe_holding_grandchild_does_not_outlive_the_timeout(self):
        """THE WHOLE POINT. subprocess.run would hang here forever; this must raise and clean up."""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
            fh.write(FAKE_BROWSER)
            fake = fh.name
        self.addCleanup(lambda: os.path.exists(fake) and os.unlink(fake))

        t0 = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            JSG._run_browser_bounded([sys.executable, fake], 3)
        elapsed = time.monotonic() - t0

        # It must RETURN. The defect was an infinite block, so any finite answer is the fix;
        # a generous ceiling keeps this from becoming a flake on a loaded machine.
        self.assertLess(elapsed, 45.0,
                        "did not come back within 45s - this is the hang the file exists for "
                        "(measured %.1fs)" % elapsed)

        # and nothing of ours may be left holding the pipe
        time.sleep(0.5)
        leftovers = _ours_alive(fake)
        self.assertEqual(leftovers, [],
                         "a child survived the timeout still holding the pipe: %r" % (leftovers,))

    def test_a_launcher_that_exits_on_its_own_returns_its_output(self):
        """BASELINE, so the case above can discriminate.

        Without this, a helper that always raised would pass the test above and prove nothing.
        """
        r = JSG._run_browser_bounded(
            [sys.executable, "-c", "import sys; sys.stdout.write('hello'); sys.stdout.flush()"], 30)
        self.assertEqual(r.returncode, 0)
        self.assertIn("hello", r.stdout)

    def test_the_timeout_still_propagates_so_the_node_fallback_runs(self):
        """v1808 ruled that a timeout is NOT a syntax verdict; that ruling must survive this fix.

        If the helper swallowed TimeoutExpired, check() would stop falling through to node and a
        slow browser would once again read as a broken file.
        """
        src = _fn_src("_run_browser_bounded")
        self.assertTrue(src, "_run_browser_bounded is gone")
        tree = ast.parse(textwrap.dedent(src))
        bare_raises = [n for n in ast.walk(tree)
                       if isinstance(n, ast.Raise) and n.exc is None]
        self.assertTrue(bare_raises,
                        "the timeout is not re-raised, so check()'s node fallback can never run")

    # ---------- the structural laws ----------

    def test_the_browser_is_started_in_its_own_session(self):
        """One killpg is only sufficient because the launcher leads its own group."""
        src = _code_only(_fn_src("_run_browser_bounded"))
        self.assertIn("start_new_session=True", src,
                      "without its own session, killpg either misses the helpers or reaches too far")

    def test_the_timeout_path_kills_the_GROUP(self):
        """Killing the launcher alone is what left pid 19019 (PPID 1) holding the pipe."""
        src = _code_only(_fn_src("_run_browser_bounded"))
        self.assertIn("killpg", src,
                      "the timeout path does not kill the process group, which is the entire defect")

    def test_the_pipes_are_closed_before_any_wait(self):
        """_reap()'s own lesson: no later wait may block on an fd a survivor still holds."""
        src = _code_only(_fn_src("_run_browser_bounded"))
        self.assertIn(".close()", src, "our ends of the pipes are never closed")

    def test_check_does_not_reach_for_subprocess_run_on_a_browser_again(self):
        """The regression this file exists to prevent, asked of the CODE and not of the prose."""
        check_src = _code_only(_fn_src("check"))
        self.assertTrue(check_src, "check() is gone")
        tree = ast.parse(textwrap.dedent(check_src))
        run_calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr == "run" and \
               isinstance(f.value, ast.Name) and f.value.id == "subprocess":
                run_calls.append(node.lineno)
        self.assertEqual(run_calls, [],
                         "check() calls subprocess.run again at %r - that call cannot reach the "
                         "renderer grandchildren and will hang exactly as it did at v3379"
                         % (run_calls,))

    def test_check_actually_uses_the_bounded_helper(self):
        """A helper nobody calls is documentation. [[the-unjoined-end]]"""
        check_src = _code_only(_fn_src("check"))
        tree = ast.parse(textwrap.dedent(check_src))
        names = [n.func.id for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertIn("_run_browser_bounded", names,
                      "check() no longer calls the bounded launcher - the fix is inert")


RED_PROOF = [
    {
        "why": "the group kill is the fix; without it a pipe-holding grandchild survives and the "
               "second communicate() blocks forever, which is the measured wedge",
        "file": "tv/js_syntax_gate.py",
        "find": "                    os.killpg(pgid, _signal.SIGKILL)",
        "replace": "                    proc.kill()",
        "matches": 1,
        "needs": "posix",   # v3860 - only the forking case catches it (a second killpg stays in the code)
    },
    {
        "why": "without its own session the launcher shares our group, so killpg would either miss "
               "the helpers or signal this very test runner",
        "file": "tv/js_syntax_gate.py",
        "find": "        start_new_session=True,",
        "replace": "        start_new_session=False,",
        "matches": 1,
    },
    {
        "why": "re-raising TimeoutExpired is what keeps v1808's node fallback reachable; swallowing "
               "it makes a slow browser read as a broken file again",
        "file": "tv/js_syntax_gate.py",
        "find": "        raise\n    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)",
        "replace": "        return subprocess.CompletedProcess(cmd, 1, '', '')\n"
                   "    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)",
        "matches": 1,
    },
    {
        "why": "the helper must actually be called; restoring subprocess.run in check() is the exact "
               "regression, and the AST law must catch it",
        "file": "tv/js_syntax_gate.py",
        "find": "                    r = _run_browser_bounded(cmd, timeout)",
        "replace": "                    r = subprocess.run(cmd, capture_output=True, text=True,\n"
                   "                                       encoding=\"utf-8\", errors=\"replace\", timeout=timeout)",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
