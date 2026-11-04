# -*- coding: utf-8 -*-
"""v3421 — A FAILURE CLOSING stdin MUST NOT SKIP THE REAP.

The shutdown of the ocr worker was three statements sharing one `try`:

    try:
        wp.stdin.close(); wp.terminate()
        threading.Thread(target=wp.wait, daemon=True, name="tvd-ocr-reap").start()
    except Exception:
        pass

`wp.stdin.close()` raises BrokenPipeError when the worker has **already exited on its own** — and
that is precisely the case that leaves a zombie. One raise and `terminate()` never ran, the reaper
thread never started, and the bare `except` said nothing. **The guard was skipped in exactly the
scenario it was written for, and looked healthy in every other.**

⚠ THE FIX IT REPLACED WAS ITSELF A FIX. The comment at that site already read *"Measured
2026-09-01: 12 defunct children, oldest 16.5h"* — the reap had been added three weeks earlier and
leaked anyway, because of the shared `try` one line above it.

MEASURED 2026-09-23: 14 defunct children of his console. A 95-minute catcher sampling every second
logged 81 children; exactly one later became defunct, and it had been caught ALIVE first —
`tv/bin/ocr_mac --worker`, pid 88160, alive 23:36:21, `<defunct>` 70 minutes later. **A zombie
carries no argv**, so nothing but catching it alive could have named the site; four rounds of
reading the file could not choose between three Popen sites.

⚠ THIS GATE DRIVES THE SHIPPED ROUTINE. `close_ocr_worker` was extracted so the failure can be
handed to it directly — a source check would only prove the text is arranged a certain way, not
that a broken pipe still gets reaped. [[copy-drift]] §7 — one routine, one home, and the other
sites call it.
"""
import io
import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import control_app as CA  # noqa: E402
# ⚠ v3424 — importing this is now FREE. Until v3422 it minted a temp directory at import, and
# this gate would have been the 32nd module doing so. [[the-unjoined-end]]
import second_eye_run as R  # noqa: E402


class _Stdin(object):
    def __init__(self, raises=None):
        self.raises, self.closed = raises, False

    def close(self):
        if self.raises:
            raise self.raises
        self.closed = True


class _Worker(object):
    """A stand-in for the Popen. Records what was actually called on it."""

    def __init__(self, stdin_raises=None, terminate_raises=None, no_stdin=False):
        self.stdin = None if no_stdin else _Stdin(stdin_raises)
        self._terminate_raises = terminate_raises
        self.terminated = False
        self.waited = False

    def terminate(self):
        self.terminated = True
        if self._terminate_raises:
            raise self._terminate_raises

    def wait(self):
        self.waited = True


class TestABrokenPipeMustNotSkipTheReap(unittest.TestCase):

    def setUp(self):
        self._said = []

    def _say(self, m):
        self._said.append(m)

    # ---- baseline: a healthy worker is closed, terminated and reaped ----------------------

    def test_BASELINE_a_healthy_worker_is_closed_terminated_and_reaped(self):
        w = _Worker()
        ok = CA.close_ocr_worker(w, say=self._say)
        self.assertTrue(ok, "the reap thread did not start on a perfectly healthy worker — every "
                            "case below would then pass for the wrong reason")
        self.assertTrue(w.stdin.closed)
        self.assertTrue(w.terminated)
        self.assertEqual(self._said, [], "a healthy shutdown should say nothing")

    # ---- the defect --------------------------------------------------------------------

    def test_a_BROKEN_PIPE_on_stdin_still_terminates_and_still_reaps(self):
        """The worker exited on its own, so the pipe is broken — the zombie case exactly."""
        w = _Worker(stdin_raises=BrokenPipeError("worker already gone"))
        ok = CA.close_ocr_worker(w, say=self._say)
        self.assertTrue(w.terminated,
                        "stdin.close() raised and terminate() was skipped — the shared-try defect")
        self.assertTrue(ok,
                        "stdin.close() raised and the REAP was skipped, which is how this leaked "
                        "one zombie per closer run for three weeks")

    def test_ANY_stdin_failure_still_reaps(self):
        for exc in (BrokenPipeError("gone"), ValueError("closed file"), OSError("errno 9")):
            w = _Worker(stdin_raises=exc)
            self.assertTrue(CA.close_ocr_worker(w, say=self._say),
                            "a %s closing stdin skipped the reap" % type(exc).__name__)

    def test_a_FAILING_terminate_still_reaps(self):
        """It may already be dead; wait() reaps it regardless."""
        w = _Worker(terminate_raises=OSError("no such process"))
        self.assertTrue(CA.close_ocr_worker(w, say=self._say),
                        "terminate() raised and the reap was skipped")

    def test_a_worker_with_NO_stdin_does_not_crash_or_skip(self):
        w = _Worker(no_stdin=True)
        self.assertTrue(CA.close_ocr_worker(w, say=self._say))
        self.assertTrue(w.terminated)

    # ---- and a failed reap is never silent -----------------------------------------------

    def test_a_reap_that_cannot_start_SAYS_SO(self):
        """⚠ The one refusal that says nothing is the one that hides — this exact silence cost
        three weeks. [[feedback-silence-is-not-evidence]]"""
        w = _Worker()
        real = CA.threading.Thread

        class _Boom(object):
            def __init__(self, *a, **k):
                pass

            def start(self):
                raise RuntimeError("can't start new thread")

        CA.threading.Thread = _Boom
        try:
            ok = CA.close_ocr_worker(w, say=self._say)
        finally:
            CA.threading.Thread = real
        self.assertFalse(ok, "a reap that never started reported success")
        self.assertTrue(self._said, "the reap failed and NOTHING was said — silent exactly where "
                                    "it matters")
        self.assertIn("defunct", " ".join(self._said).lower(),
                      "the message does not say what the consequence is")

    # ---- the same class, swept: a timeout handler that kills must also reap -------------

    def test_every_timeout_handler_in_the_eye_GOES_THROUGH_THE_ONE_REAP_DOOR(self):
        """⚠⚠ v3424 — THIS CASE USED TO ACCEPT THE DEFECT, AND THE SECOND EYE SAID SO.

        v3421 required only that a `TimeoutExpired` handler contain calls named `kill` and
        `communicate`/`wait`. `kill(); communicate(timeout=10)` satisfies that and DOES NOT REAP:
        on CPython 3.9 `communicate` runs its select loop first and only reaches `self.wait(...)`
        afterwards, so a second timeout escapes before any wait happens. MEASURED, not argued — see
        the behavioural case below. A law shaped like the fix it was written beside will accept
        every wrong implementation that happens to use the same words.

        So the law is now ONE DOOR: a handler that kills must hand the child to
        `_reap_after_kill`, where the wait is unconditional. Re-implementing it per site is the
        copy-drift shape — a rule that lands at three of four call sites is not a rule."""
        import ast
        src = io.open(os.path.join(HERE, "second_eye_run.py"),
                      encoding="utf-8", errors="replace").read()
        bad = []
        for node in ast.walk(ast.parse(src)):
            if not isinstance(node, ast.ExceptHandler) or node.type is None:
                continue
            if "TimeoutExpired" not in ast.dump(node.type):
                continue
            calls = {n.func.attr for n in ast.walk(node)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
            names = {n.func.id for n in ast.walk(node)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
            if "kill" in calls and "_reap_after_kill" not in names:
                bad.append(node.lineno)
        self.assertEqual(bad, [], "timeout handler(s) at line(s) %r kill a child without handing "
                                  "it to _reap_after_kill — so the reap depends on the drain "
                                  "succeeding, which is exactly what just failed" % (bad,))

    # ⚠ v3860 — POSIX ONLY. The premise is os.fork() and a <defunct> child; Windows has neither (no fork, no zombies),
    # so there the premise case could only fail and never measure. The proof it backs says "needs": "posix".
    @unittest.skipUnless(hasattr(os, "fork"), "POSIX only: the corpse premise needs os.fork and zombies")
    def test_kill_then_communicate_REALLY_DOES_leave_a_corpse_and_the_door_does_not(self):
        """THE MEASUREMENT THAT SETTLED IT, kept as a case so nobody re-argues it from the docs.

        A child that forks a grandchild inheriting the stdout pipe cannot be drained: the write end
        stays open after the child dies. `kill()` then `communicate(timeout=N)` therefore times out
        AGAIN, `returncode` stays None, and `ps` reports `Z <defunct>`. An explicit `wait()` reaps
        it. Python's own docs write `kill(); communicate()` with no timeout, which has no hole —
        but an unbounded drain in a console that is up for days is a hang, so the bound stays and
        the WAIT is what became unconditional."""
        import subprocess as sp
        code = ("import os, time, sys\n"
                "if os.fork() == 0:\n"
                "    time.sleep(120)\n"
                "    sys.exit(0)\n"
                "time.sleep(120)\n")
        p = sp.Popen([sys.executable, "-c", code], stdout=sp.PIPE, stderr=sp.PIPE)
        try:
            time.sleep(0.8)
            p.kill()
            # the v3421 shape, on its own
            try:
                p.communicate(timeout=2)
            except Exception:
                pass
            self.assertIsNone(p.returncode,
                              "the premise no longer holds on this interpreter: kill+communicate "
                              "reaped the child, so this case is measuring nothing")
            # the v3424 door, on the same child
            self.assertTrue(R._reap_after_kill(p, drain_s=1.0, reap_s=10.0),
                            "_reap_after_kill did not collect an already-SIGKILLed child")
            self.assertIsNotNone(p.returncode, "the child is still uncollected after the door ran")
        finally:
            try:
                p.kill()
                p.wait(timeout=5)
            except Exception:
                pass

    @staticmethod
    def _fill(p):
        """Stuff well past a 64 KiB pipe buffer. Blocks by design; runs on a daemon thread."""
        try:
            p.stdin.write("x" * (1024 * 1024))
            p.stdin.flush()
        except Exception:
            pass

    def test_closing_the_worker_stdin_CANNOT_BLOCK_THE_CALLER(self):
        """⚠ v3424 — the other half the eye found. The worker is spawned `text=True, bufsize=1`, so
        `wp.stdin` is a buffered writer and `.close()` FLUSHES. A worker that has stopped reading,
        with a full pipe and bytes still buffered, makes that flush block forever — no exception,
        so the `except` never fires, `terminate()` never runs, the reap thread never starts, and
        the closer loop never returns. It would hang one step EARLIER than the stall the function
        was written to avoid.

        Driven, not grepped: a real child that never reads, a pipe stuffed past its capacity, and
        a hard bound on how long the close may take."""
        import subprocess as sp
        import threading as th
        # ⚠ v3860 — THE CHILD IGNORES SIGTERM. close_ocr_worker now terminates FIRST (Windows' fd lock, see the
        # case below), and a child that dies on SIGTERM frees the stuck writer on its own - so against an obedient
        # child this case could no longer tell the raw close from the buffered one. A worker that ignores SIGTERM is
        # the one terminate-first does not rescue, and it is the case the raw close exists for. (Windows' terminate
        # cannot be ignored, so there the child dies and the case measures the new order instead.)
        p = sp.Popen([sys.executable, "-c",
                      "import signal, time\n"
                      "try:\n    signal.signal(signal.SIGTERM, signal.SIG_IGN)\nexcept Exception:\n    pass\n"
                      "time.sleep(30)"],
                     stdin=sp.PIPE, stdout=sp.PIPE, text=True, bufsize=1)
        try:
            # ⚠ THE FILL ITSELF BLOCKS, AND IT IS SETUP, NOT THE SUBJECT. Writing past the pipe
            # buffer to a child that never reads is exactly the state under test, so the write
            # cannot return until the child dies — done on the test's own thread it cost 60s of
            # gate time and measured nothing. [[a-gate-can-perturb-what-it-measures]]
            th.Thread(target=lambda: self._fill(p), daemon=True).start()
            time.sleep(1.5)                        # long enough for the pipe to be full
            done = []
            t = th.Thread(target=lambda: (CA.close_ocr_worker(p), done.append(True)), daemon=True)
            t.start()
            t.join(20.0)
            self.assertTrue(done, "close_ocr_worker BLOCKED for over 20s on a worker that stopped "
                                  "reading — the caller thread, and the whole reel backlog, is "
                                  "stalled with no exception and nothing in the log")
        finally:
            try:
                p.kill()
                p.wait(timeout=5)
            except Exception:
                pass

    def test_a_close_that_WAITS_FOR_THE_WRITER_cannot_hold_the_caller_hostage(self):
        """⚠⚠ v3860 — WINDOWS' SHAPE, ON EVERY OS. The C runtime locks a file descriptor for the whole of a write(),
        and close() takes the same lock, so on win32 the RAW close waits for a writer stuck on a full pipe until the
        worker dies. The routine used to close first and terminate second: the worker could never die, because the
        terminate was queued behind the close that was waiting for it. MEASURED 2026-11-04 on the new Konyo · ALT
        (Python 3.12): close first was still blocked after 12 s; terminate first returned in 0.0 s. Linux and macOS
        close(2) do not wait, which is why only the Windows prover saw it (the real-pipe case above, red there).

        This removes the venue the way #185 did for Linux: a raw stream whose close() waits on the in-flight
        write's lock, and a terminate() that kills the child so the write fails. The routine must kill first and
        return promptly with the stream CLOSED. [[a-probe-licenses-only-what-it-tested]]
        """
        import threading as th

        release, entered, fd_lock = th.Event(), th.Event(), th.Lock()

        class _CrtRaw(io.RawIOBase):
            def writable(self):
                return True

            def write(self, b):
                with fd_lock:             # the CRT holds the fd's lock for the whole write
                    entered.set()
                    release.wait(30)      # a full pipe: the write returns only when the child is gone
                    raise BrokenPipeError("the child is gone")

            def close(self):
                with fd_lock:             # ...and close() takes that same lock, so it WAITS for the write
                    io.RawIOBase.close(self)

        raw = _CrtRaw()
        stdin = io.TextIOWrapper(io.BufferedWriter(raw, buffer_size=8), write_through=True)

        class _W(object):
            def __init__(self):
                self.stdin, self.terminated = stdin, False

            def terminate(self):
                self.terminated = True
                release.set()             # the child dies -> the stuck write fails and lets go of the fd

            def wait(self):
                pass

        w = _W()
        th.Thread(target=lambda: self._swallow(lambda: stdin.write("x" * 64)), daemon=True).start()
        self.assertTrue(entered.wait(5), "premise: the writer never got inside write(), so the fd lock was "
                                         "never held and this case measures nothing")
        done = []
        t = th.Thread(target=lambda: (CA.close_ocr_worker(w), done.append(True)), daemon=True)
        t0 = time.time()
        t.start()
        t.join(5.0)
        try:
            self.assertTrue(done, "close_ocr_worker waited over 5s on a close that was waiting for the stuck write - "
                                  "the terminate that would free it was queued BEHIND that close. On Windows that is "
                                  "the closer loop, and the whole reel backlog, stalled with nothing in the log")
            self.assertLess(time.time() - t0, 5.0)
            self.assertTrue(w.terminated, "the routine returned without terminating the worker")
            self.assertTrue(raw.closed, "the raw stream was left open")
        finally:
            release.set()

    def test_a_writer_HOLDING_THE_BUFFER_LOCK_cannot_hold_the_caller_hostage(self):
        """⚠⚠ #185 — THE CASE ABOVE WAS GREEN ON HIS MAC AND RED ON CI, SAME COMMIT. On Linux a thread
        blocked in write() on a full pipe keeps holding the BufferedWriter's lock after close(2),
        and TextIOWrapper.close() takes that lock before anything else — so the old routine waited
        for the child to die (CI: 25.4s against a 20s bound). macOS wakes the writer, which is why
        the venue decided the verdict.

        This removes the venue. The raw stream's write() blocks on an Event and ignores close —
        exactly Linux's shape — so the lock is held on EVERY OS, deterministically, and the routine
        must still return promptly and leave the stream reading CLOSED.
        [[a-probe-licenses-only-what-it-tested]] [[ab-against-head-before-blaming-the-room]]
        """
        import threading as th

        release, entered = th.Event(), th.Event()

        class _StuckRaw(io.RawIOBase):
            def writable(self):
                return True

            def write(self, b):
                entered.set()
                release.wait(30)      # a writer the close cannot wake — Linux's full pipe
                raise BrokenPipeError("the child is gone")

        raw = _StuckRaw()
        stdin = io.TextIOWrapper(io.BufferedWriter(raw, buffer_size=8), write_through=True)

        class _W(object):
            def __init__(self):
                self.stdin, self.terminated = stdin, False

            def terminate(self):
                # ⚠ v3860 — a worker that IGNORES SIGTERM: the stuck write is NOT freed here. Terminate-first
                # rescues an obedient worker by itself, so only this shape still measures the raw close.
                self.terminated = True

            def wait(self):
                pass

        w = _W()
        th.Thread(target=lambda: self._swallow(lambda: stdin.write("x" * 64)), daemon=True).start()
        self.assertTrue(entered.wait(5), "premise: the writer never got inside write(), so the "
                                         "buffer lock was never held and this case measures nothing")
        done = []
        t = th.Thread(target=lambda: (CA.close_ocr_worker(w), done.append(True)), daemon=True)
        t0 = time.time()
        t.start()
        t.join(5.0)
        try:
            self.assertTrue(done, "close_ocr_worker waited on another thread's buffer lock for over "
                                  "5s — on Linux that is until the worker dies, and the closer loop "
                                  "and the whole reel backlog stall with it")
            self.assertLess(time.time() - t0, 5.0)
            self.assertTrue(w.terminated, "the routine returned without terminating the worker")
            self.assertTrue(raw.closed, "the raw stream was left open — a later flush could write "
                                        "into a descriptor number someone else has reused")
        finally:
            release.set()

    @staticmethod
    def _swallow(fn):
        try:
            fn()
        except Exception:
            pass


    # ---- the call site actually calls it --------------------------------------------------

    def test_the_closer_loop_CALLS_the_routine_rather_than_re_implementing_it(self):
        """[[copy-drift]] §7 — a safety routine that exists twice is the dangerous copy."""
        src = io.open(os.path.join(HERE, "control_app.py"),
                      encoding="utf-8", errors="replace").read()
        code = "\n".join(l.split("#", 1)[0] for l in src.split("\n"))
        self.assertIn("close_ocr_worker(wp)", code,
                      "the closer loop no longer calls the shared routine")
        self.assertEqual(code.count('name="tvd-ocr-reap"'), 1,
                         "the reap exists in more than one place — the copy-drift shape")


RED_PROOF = [
    {
        "why": "v3421 - THE SHARED try, RESTORED. Closing stdin inside the same try as terminate "
               "means a BrokenPipeError from a worker that already exited skips both the "
               "terminate and the reap - which is the exact case that leaves a zombie, and the "
               "reason this leaked for three weeks after the reap was added.",
        "file": "control_app.py",
        # ⚠ v3421 — SHORT AND EXACT. My first anchor pasted the whole three-step block and
        # matched ZERO times, because the comment carries an em dash and I typed a hyphen.
        # heart2 would have reported INVALID. [[source-reading-guard]] §2 — print the count.
        # ⚠⚠ v3424 — AND THE SECOND ANCHOR WENT **BLIND AT MATCH COUNT 1**, which is the tell that
        # the LAW is weak rather than the sabotage wrong. It aimed at an OUTER `except` that my own
        # v3424 restructure had just made unreachable: the two inner handlers swallow everything,
        # so returning from a branch nothing can enter changes nothing and the gate stayed green.
        # The dead branch is now gone, and the tamper aims at the handler the broken-pipe case
        # actually reaches. [[sabotage-is-usually-the-wrong-one]]
        "find": "            pass                  # a stdin that will not close is NOT a reason to skip the reap",
        "replace": "            return False  # the shared-try defect: a broken pipe skips everything below",
        "matches": 1,
    },
    {
        "why": "v3421 - THE FAILED REAP MADE SILENT AGAIN. Returning without a word when the "
               "reaper thread cannot start reinstates the silence that hid this defect: the rows "
               "keep arriving, the console keeps working, and the process table fills up.",
        "file": "control_app.py",
        "find": "        (say or (lambda m: print(m, flush=True)))(msg)\n        return False",
        "replace": "        return False",
        "matches": 1,
    },
    {
        "why": "v3424 - THE REAP MADE CONDITIONAL AGAIN. This is the v3421 shape the second eye "
               "refused and the measurement confirmed: kill() then communicate(timeout=N) does "
               "NOT reap, because CPython runs the select loop before self.wait() and a second "
               "TimeoutExpired escapes first. Measured: returncode None, ps says Z <defunct>.",
        "file": "second_eye_run.py",
        "find": "    try:\n        p.wait(timeout=reap_s)\n        return True\n    except Exception:\n        return False",
        "replace": "    try:\n        return p.returncode is not None\n    except Exception:\n        return False",
        "matches": 1,
        # v3860 - only the fork case catches it, and Windows has no fork: judged where POSIX is, ELSEWHERE there.
        "needs": "posix",
    },
    {
        "why": "v3424 - THE ONE DOOR, BYPASSED. A handler that kills and re-implements the reap "
               "inline is how the defect came back once already; the AST law must refuse it "
               "whatever words the inline version happens to use.",
        "file": "second_eye_run.py",
        "find": "        p.kill()\n        _reap_after_kill(p)\n        return None, \"timed out after %ss\" % timeout",
        "replace": "        p.kill()\n        try:\n            p.communicate(timeout=10)\n        except Exception:\n            pass\n        return None, \"timed out after %ss\" % timeout",
        "matches": 1,
    },
    {
        "why": "v3424 - THE BLOCKING FLUSH, RESTORED. wp.stdin is a buffered writer (text=True, "
               "bufsize=1), so .close() FLUSHES; against a worker that stopped reading with a "
               "full pipe that blocks forever, with no exception, so terminate() never runs and "
               "the closer thread - and the whole reel backlog - stalls.",
        "file": "control_app.py",
        # ⚠ v3424 — this anchor was INVALID at match count 0 once, because flattening the dead
        # outer try de-indented the line from 16 spaces to 12. A tamper carries whitespace.
        # ⚠ #185 — re-anchored: the door that stops the flush is now the RAW close.
        "find": "                _raw.close()      # the fd AND the closed flag — no buffered lock, no flush",
        "replace": "                pass",
        "matches": 1,
    },
    {
        "why": "v3860 - THE CLOSE MOVED BACK IN FRONT OF THE TERMINATE. Windows' C runtime makes a raw close WAIT "
               "for a write stuck on a full pipe, and the terminate that would free that write is queued behind "
               "the close: the closer loop stalls on every Windows PC (measured on the ALT: >12 s, never returned).",
        "file": "control_app.py",
        "find": "    try:\n        wp.terminate()\n    except Exception:\n        pass                      # it may have exited on its own; wait() still reaps it\n",
        "replace": "    _r0 = getattr(getattr(getattr(wp, \"stdin\", None), \"buffer\", None), \"raw\", None)\n"
                   "    try:\n        if _r0 is not None:\n            _r0.close()\n    except Exception:\n        pass\n"
                   "    try:\n        wp.terminate()\n    except Exception:\n        pass\n",
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
