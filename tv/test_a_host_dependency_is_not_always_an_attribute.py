# -*- coding: utf-8 -*-
"""A HOST DEPENDENCY IS NOT ALWAYS A PYTHON ATTRIBUTE, AND ci_sim COULD ONLY EXPRESS THAT ONE.

`tv/ci_sim.py` answers one question — *would this pass on a runner?* — and `HOST_STUBS` is the
durable record of what his Mac silently provides. MEASURED before this file was written: all three
entries patch a python MODULE ATTRIBUTE (`control_app.board_identity_drift`,
`control_app._tree_is_mid_edit`, `console_doctor.slow_surface`), and **neither CI-vs-Mac
disagreement found in the week of 2026-09-23 is one**:

  · `tv/bin/ocr_mac` is a MACOS BINARY ON DISK. "this executable cannot run here" is a filesystem
    fact — no attribute carries it.
  · "this interpreter starts children with fork_exec where Linux uses posix_spawn" is a PLATFORM
    fact about CPython and this kernel. **You cannot patch a Mac into being Linux.**

So the simulator printed "🟢 no KNOWN host dependency" about both of them — the same shape as the
third HOST_STUBS entry's own comment, which records that THE LIVE SITE DID NOT DEPLOY ALL DAY
while the code was correct throughout.

WHAT WAS MEASURED HERE, because the fix turns on it and a guess would have built the wrong stub:

  · `git ls-files` TRACKS `tv/bin/ocr_mac`, and `file` calls it "Mach-O 64-bit executable arm64".
    So on ubuntu-latest the path is PRESENT with its exec bit — `tv_diablo._ocr_worker_cmd()`'s
    `os.path.isfile(OCR_BIN) and os.access(OCR_BIN, os.X_OK)` guard PASSES there, the fast lane is
    taken, and the failure lands one step later at exec as OSError errno 8 "Exec format error".
    ⚠ Stubbing that path ABSENT would therefore simulate a world CI does not have and would hide
    the guard being taken. The mode is `not-executable`, and the two modes are different laws.
  · `test_a_broken_pipe_must_not_skip_the_reap` spawns NO ocr binary at all — audited with
    `sys.addaudithook`, its whole run is two `subprocess.Popen` of `sys.executable`, and the one
    occurrence of the string "ocr_mac" in it is in its module DOCSTRING. A text scan for that name
    would have been grepping prose. [[source-reading-guard]] §4. What it really leans on is the
    PLATFORM fact, and `test_closing_the_worker_stdin_CANNOT_BLOCK_THE_CALLER` — green here in
    5.3s, red on the runner at 25.4s against its own >20s bound — is the test that pays for it.
  · The platform detector was sized before it was written, because a row that cries wolf gets
    silenced and that costs more than the defect: **8,111 test methods across every tv/test_*.py,
    64 flagged (0.79%)**; 16 inside test_control.py.

⚠ THE PROPERTY THIS FILE PROTECTS ABOVE ALL: ci_sim states its own reach in the same breath as its
verdict. Every new capability must EXTEND that sentence, never weaken it — so the UNKNOWN verdict
still carries "only the stubs above were neutralised", and the new stub kind carries the same
refusal the attribute kind has: an inert stub exits 2 rather than silently simulating less than it
claims. [[unknown-stays-unknown]] [[regression-guard]]
"""
import io
import os
import subprocess
import sys
import tempfile
import unittest
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import ci_sim  # noqa: E402

SIM = os.path.join(HERE, "ci_sim.py")
OCR = os.path.join(HERE, "bin", "ocr_mac")

# Mach-O 64-bit, little endian (MH_MAGIC_64 = 0xFEEDFACF). A Linux kernel cannot exec this.
MACHO64_LE = b"\xcf\xfa\xed\xfe"

_SIM_RUNS = {}


def _sim(*args):
    """Run ci_sim as a real subprocess, once per argument list. -> (exit code, output)"""
    key = tuple(args)
    if key not in _SIM_RUNS:
        p = subprocess.Popen([sys.executable, SIM] + list(args),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=HERE)
        out, _ = p.communicate()
        _SIM_RUNS[key] = (p.returncode, (out or b"").decode("utf-8", "replace"))
    return _SIM_RUNS[key]


def _restore_paths():
    """Undo everything apply_path_stubs installed, whatever the test did."""
    real = ci_sim._REAL_IO
    if "Popen" in real:
        subprocess.Popen = real.pop("Popen")
    if "exists" in real:
        os.path.exists = real.pop("exists")
    if "isfile" in real:
        os.path.isfile = real.pop("isfile")
    if "access" in real:
        os.access = real.pop("access")
    ci_sim._STUBBED_PATHS.clear()


class ThePremisesThisFixIsBuiltOn(unittest.TestCase):
    """⚠ PROVE THE PREMISE OR EVERY CASE BELOW PASSES VACUOUSLY."""

    def test_the_ocr_binary_is_a_MACH_O_that_a_runner_keeps_but_cannot_exec(self):
        self.assertTrue(os.path.isfile(OCR),
                        "tv/bin/ocr_mac is not on this machine, so nothing below is measuring "
                        "the case it was written for")
        with io.open(OCR, "rb") as fh:
            magic = fh.read(4)
        self.assertEqual(
            magic, MACHO64_LE,
            "tv/bin/ocr_mac is no longer a 64-bit Mach-O (magic %r). The whole reason its stub "
            "mode is 'not-executable' rather than 'absent' is that a Linux runner CHECKS IT OUT "
            "and then fails at exec; a different binary format makes that record wrong."
            % (magic,))
        self.assertTrue(os.access(OCR, os.X_OK),
                        "the exec bit is gone, so a runner would not even reach the exec — the "
                        "recorded mode would then be describing something that cannot happen")
        # Tracked-ness decides ABSENT vs NOT-EXECUTABLE. What must never pass silently is a
        # positive "untracked".
        # ⚠⚠ "GIT SAYS NO" AND "THERE IS NO GIT HERE" ARE DIFFERENT FACTS, and the first cut of
        # this case collapsed them. MEASURED: safe_copy.py excludes `.git` from the sabotage
        # sandbox, so `git ls-files` exits 128 there — read as "untracked", this case failed in
        # the sandbox and made every red-proof below UNPROVABLE, over a repo that tracks the file
        # perfectly well. An answer nobody could obtain is UNKNOWN. [[unknown-stays-unknown]]
        tracked = None
        try:
            repo = os.path.dirname(HERE)
            if subprocess.call(["git", "rev-parse", "--git-dir"], cwd=repo,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                tracked = subprocess.call(
                    ["git", "ls-files", "--error-unmatch", "tv/bin/ocr_mac"], cwd=repo,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
        except Exception:
            tracked = None
        self.assertNotEqual(
            tracked, False,
            "git does not track tv/bin/ocr_mac, so a runner's checkout would NOT contain it and "
            "the recorded mode must be 'absent', not 'not-executable' — the stub is simulating a "
            "world CI does not have")

    def test_the_binary_is_RECORDED_as_a_host_path(self):
        """The join: measuring the binary is worth nothing if the list never names it."""
        rels = {rel: mode for rel, mode, _why in ci_sim.HOST_PATHS}
        self.assertIn("bin/ocr_mac", rels,
                      "the macOS OCR binary is not in HOST_PATHS, so ci_sim still has no way to "
                      "say 'this executable cannot run here'")
        self.assertEqual(rels["bin/ocr_mac"], "not-executable",
                         "the mode contradicts the measurement above: git tracks the file, so a "
                         "runner HAS it and only the exec fails")


class APathStubIsABSENTOrNONEXECUTABLE_NeverAWorkingStandIn(unittest.TestCase):

    def tearDown(self):
        _restore_paths()

    def test_the_NOT_EXECUTABLE_mode_leaves_the_path_alone_and_only_the_EXEC_fails(self):
        rows = ci_sim.apply_path_stubs(verbose=False)
        self.assertTrue(all(ok for _n, ok, _w in rows),
                        "the recorded host paths did not bind: %r" % (rows,))
        # ⚠⚠ PREMISE FIRST, AND THIS ONE IS NOT COSMETIC. If the interception is not installed,
        # the Popen below really would launch `ocr_mac --worker` — a persistent worker that waits
        # on stdin for ever. Assert the wrapper is in place BEFORE handing it a real binary.
        self.assertTrue(getattr(subprocess.Popen, "_ci_sim_path_stub", False),
                        "ci_sim did not install its exec interception, so this case must NOT "
                        "spawn the real worker")
        self.assertTrue(os.path.isfile(OCR),
                        "the not-executable stub HID the file. A runner checks it out; hiding it "
                        "simulates a world CI does not have and skips the isfile/X_OK guard that "
                        "tv_diablo really takes there")
        self.assertTrue(os.access(OCR, os.X_OK),
                        "the not-executable stub cleared the exec bit, so _ocr_worker_cmd() would "
                        "return None here and the failing branch is never reached")
        with self.assertRaises(OSError) as caught:
            subprocess.Popen([OCR, "--worker"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.assertEqual(
            caught.exception.errno, 8,
            "exec of the Mach-O binary did not fail the way a Linux runner fails it (errno 8, "
            "'Exec format error'). Got errno %r: %s"
            % (caught.exception.errno, caught.exception))

    def test_the_ABSENT_mode_hides_the_path_AND_refuses_the_exec(self):
        """The other mode, driven on a throwaway file so nothing real is hidden."""
        d = tempfile.mkdtemp(prefix="ci_sim_pathstub_")
        # v3886 (#107, windows-latest: "[WinError 193] %1 is not a valid Win32 application") - a throwaway tool this OS can
        # run: a #!/bin/sh script on the Mac, a .cmd batch file on Windows (CreateProcess runs it); the stub is the subject
        if os.name == "nt":
            script = os.path.join(d, "a_host_tool.cmd")
            with io.open(script, "w", encoding="utf-8") as fh:
                fh.write("@exit /b 0\r\n")
        else:
            script = os.path.join(d, "a_host_tool")
            with io.open(script, "w", encoding="utf-8") as fh:
                fh.write("#!/bin/sh\nexit 0\n")
            os.chmod(script, 0o755)
        try:
            # PREMISE: it really is there and really runs, or "absent" proves nothing.
            self.assertTrue(os.path.exists(script))
            p = subprocess.Popen([script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.assertEqual(p.wait(timeout=20), 0,
                             "the throwaway tool did not run before it was stubbed, so hiding it "
                             "afterwards would measure nothing")

            rows = ci_sim.apply_path_stubs(
                entries=[(script, "absent", "a runner has no such file")], verbose=False)
            self.assertTrue(all(ok for _n, ok, _w in rows), "the absent stub did not bind: %r"
                            % (rows,))
            self.assertFalse(os.path.exists(script),
                             "os.path.exists still finds a path stubbed ABSENT")
            self.assertFalse(os.path.isfile(script),
                             "os.path.isfile still finds a path stubbed ABSENT")
            self.assertFalse(os.access(script, os.X_OK),
                             "os.access still calls a path stubbed ABSENT executable")
            with self.assertRaises(FileNotFoundError):
                subprocess.Popen([script])
            # and it is a stub, not a stand-in: an UNRELATED binary is untouched
            q = subprocess.Popen([sys.executable, "-c", "pass"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.assertEqual(q.wait(timeout=30), 0,
                             "the interception broke every spawn, not just the stubbed path — a "
                             "gate that perturbs everything measures nothing")
        finally:
            _restore_paths()
            try:
                os.remove(script)
                os.rmdir(d)
            except Exception:
                pass


class AnInertPathStubMakesTheRunREFUSE(unittest.TestCase):
    """⚠ A STUB WITH NO TARGET IS A SIMULATION MEASURING NOTHING — the attribute kind has said so
    since v2200, and a path kind without the same refusal silently simulates less than it claims."""

    def tearDown(self):
        _restore_paths()

    def test_a_path_that_has_MOVED_binds_as_INERT(self):
        gone = os.path.join(HERE, "bin", "no_such_host_binary_xyz")
        self.assertFalse(os.path.lexists(gone), "the fixture path exists, so this proves nothing")
        rows = ci_sim.apply_path_stubs(
            entries=[(gone, "not-executable", "unused")], verbose=False)
        self.assertEqual(len(rows), 1)
        _name, ok, why = rows[0]
        self.assertFalse(ok, "a recorded path that is no longer on disk bound as if it had been "
                             "neutralised — the stub is inert and nothing says so")
        self.assertIn("stale", why.lower(),
                      "the refusal does not say WHY it refused, so a reader cannot tell an inert "
                      "record from a real finding. Got: %s" % why)

    def test_the_REFUSAL_REACHES_THE_VERDICT_and_nothing_is_simulated(self):
        """[[the-unjoined-end]] — detecting it and acting on it are two halves."""
        import contextlib
        gone = os.path.join(HERE, "bin", "no_such_host_binary_xyz")
        real = ci_sim.HOST_PATHS
        buf = io.StringIO()
        try:
            ci_sim.HOST_PATHS = ((gone, "not-executable", "unused"),)
            with contextlib.redirect_stdout(buf):
                rc = ci_sim.main(["TestNoSuchClassAnywhereXYZ"])
        finally:
            ci_sim.HOST_PATHS = real
        out = buf.getvalue()
        self.assertEqual(rc, 2,
                         "an inert PATH stub did not stop the run. 2 means UNKNOWN — nothing was "
                         "simulated — and anything else lets a weaker simulation print a "
                         "verdict.\n%s" % out[-700:])
        self.assertIn("could not bind", out,
                      "the run does not say a stub failed to bind, so the reader cannot tell a "
                      "weakened simulation from a full one:\n%s" % out[-700:])
        self.assertNotIn("Ran ", out,
                         "tests were executed despite an inert stub — the refusal has to come "
                         "BEFORE anything counts as evidence:\n%s" % out[-700:])


class APlatformFactIsReportedUNKNOWNRatherThanGreen(unittest.TestCase):
    """⚠ THE ONE CASE THE BRIEF NAMED. `test_a_broken_pipe_must_not_skip_the_reap` is green here
    in 5.3s and red on ubuntu-latest at 25.4s. ci_sim used to call that "🟢 no KNOWN host
    dependency", which is the over-claim its own header forbids."""

    def test_the_reap_suite_is_UNKNOWN_and_the_blocking_test_is_NAMED(self):
        rc, out = _sim("TestABrokenPipeMustNotSkipTheReap")
        self.assertIn("Ran ", out,
                      "the simulator did not run the suite at all, so its verdict is about "
                      "something else entirely:\n%s" % out[-900:])
        self.assertEqual(rc, 3,
                         "a suite whose result turns on this kernel's pipe and spawn semantics "
                         "did not come back UNKNOWN (3). 0 would claim a green it has not "
                         "earned; 2 would claim nothing ran.\n%s" % out[-900:])
        self.assertIn("UNKNOWN", out, "the verdict does not use the word:\n%s" % out[-900:])
        self.assertIn("PLATFORM FACT", out,
                      "the run does not say WHAT it could not neutralise, so UNKNOWN reads as a "
                      "malfunction rather than an answer:\n%s" % out[-900:])
        self.assertIn(
            "test_closing_the_worker_stdin_CANNOT_BLOCK_THE_CALLER", out,
            "the exact test that is green here and red on the runner is not named, so the report "
            "cannot be acted on:\n%s" % out[-900:])
        self.assertNotIn(
            "no KNOWN host dependency in 10 test(s).", out,
            "the run still prints the plain green verdict over a suite it could not simulate")

    def test_the_UNKNOWN_verdict_STILL_STATES_ITS_OWN_REACH(self):
        """The property that makes this tool trustworthy. A new capability extends that sentence;
        it never replaces it. [[regression-guard]] §1 — a sample is not a verdict."""
        rc, out = _sim("TestABrokenPipeMustNotSkipTheReap")
        # ⚠ PREMISE FIRST, AND IT WAS MISSING. This law is about the UNKNOWN verdict's wording,
        # and the GREEN verdict prints the same closing sentence — so without this line the case
        # passed unchanged when the UNKNOWN tier was sabotaged away, asserting about a verdict
        # that was no longer being printed. [[source-reading-guard]] §4b
        self.assertEqual(rc, 3,
                         "this is not the UNKNOWN verdict, so the sentences below are being read "
                         "off a different answer:\n%s" % out[-900:])
        self.assertIn("only the stubs above were neutralised", out,
                      "the UNKNOWN verdict dropped the sentence that bounds every verdict this "
                      "tool prints:\n%s" % out[-900:])
        self.assertIn("reach:", out,
                      "the run no longer states which module it covered:\n%s" % out[-900:])
        self.assertIn("bin/ocr_mac", out,
                      "the stub list printed above the verdict does not name the host PATH, so "
                      "'only the stubs above' points at an incomplete list:\n%s" % out[-900:])


class TheDetectorReadsCODEAndDoesNotCryWolf(unittest.TestCase):

    def test_a_NAME_IN_PROSE_is_not_a_dependency(self):
        """⚠ The reap suite mentions `ocr_mac` exactly once, in its module DOCSTRING, and spawns
        no such thing. A text scan would have called that a finding. [[source-reading-guard]] §4"""
        with io.open(os.path.join(HERE, "test_a_broken_pipe_must_not_skip_the_reap.py"),
                     encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        self.assertEqual(src.count("ocr_mac"), 1,
                         "the fixture moved: this case exists because that name appears there as "
                         "PROSE and nowhere as code")
        _rc, out = _sim("TestABrokenPipeMustNotSkipTheReap")
        self.assertNotIn("ocr_mac [not-executable]  <-", out)      # never a per-test finding
        for line in out.splitlines():
            if line.strip().startswith("⚪ test_"):
                self.assertNotIn("ocr_mac", line,
                                 "a test was reported as depending on the OCR binary on the "
                                 "strength of a word in a docstring: %s" % line)

    def test_the_platform_markers_flag_a_SMALL_MINORITY_of_the_tree(self):
        """⚠ A guard that cries wolf gets silenced, which costs more than the defect it catches.
        MEASURED when the markers were chosen: 64 of 8,111 test methods, 0.79%."""
        import ast
        marks = set()
        for names, _why in ci_sim.PLATFORM_FACTS:
            marks.update(names)
        total = flagged = 0
        for fn in sorted(os.listdir(HERE)):
            if not (fn.startswith("test_") and fn.endswith(".py")):
                continue
            aliases, idx = ci_sim._source_index(os.path.join(HERE, fn))
            for (_cls, meth), node in idx.items():
                if not meth.startswith("test"):
                    continue
                total += 1
                al = dict(aliases)
                al.update(ci_sim._alias_map(node))
                for c in ast.walk(node):
                    if isinstance(c, ast.Call) and ci_sim._dotted(c, al) in marks:
                        flagged += 1
                        break
        self.assertGreater(total, 5000,
                           "the scan only reached %d test methods, so the ratio below is not "
                           "about this tree" % total)
        self.assertLess(
            float(flagged) / total, 0.05,
            "the platform markers flag %d of %d test methods (%.1f%%). At that density the "
            "UNKNOWN verdict stops carrying information and gets skipped, which is the "
            "always-red gate ci_sim was written to replace."
            % (flagged, total, 100.0 * flagged / total))
        self.assertGreater(flagged, 0,
                           "the markers flag nothing at all, so the UNKNOWN tier can never fire "
                           "and is a capability on paper only")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "THE NON-EXECUTABLE STUB TURNED BACK INTO AN ABSENT ONE. Stubbing tv/bin/ocr_mac "
               "absent simulates a world CI does not have: git tracks the file, so a runner "
               "checks it out with its exec bit and tv_diablo's isfile/X_OK guard PASSES there. "
               "The failure belongs at exec (errno 8), not at the filesystem.",
        "file": "ci_sim.py",
        "find": '                raise OSError(8, "Exec format error", str(argv0))',
        "replace": '                raise OSError(2, "No such file or directory", str(argv0))',
        "matches": 1,
    },
    {
        "why": "THE ABSENT MODE STOPPED HIDING THE PATH. A path a runner does not have must read "
               "missing to the filesystem, or every isfile/access guard in the product takes the "
               "branch it takes on his Mac and the simulation is of this machine.",
        "file": "ci_sim.py",
        "find": '            return False if _path_mode(p) == "absent" else _REAL_IO["exists"](p)',
        "replace": '            return _REAL_IO["exists"](p)',
        "matches": 1,
    },
    {
        "why": "THE INERT-PATH REFUSAL REMOVED. A recorded path that has been renamed or deleted "
               "neutralises nothing; without the refusal the run prints a verdict while "
               "simulating less than it claims - the exact failure the attribute stubs already "
               "refuse on.",
        "file": "ci_sim.py",
        "find": "        if not os.path.lexists(full):",
        "replace": "        if False:",
        "matches": 1,
    },
    {
        "why": "THE PLATFORM DETECTOR DISARMED. With no marker ever matching, a suite whose "
               "result turns on this kernel's pipe and spawn semantics goes back to printing a "
               "green it has not earned.",
        "file": "ci_sim.py",
        "find": "                    if d in marks:",
        "replace": "                    if False:",
        "matches": 1,
    },
    {
        "why": "UNKNOWN COLLAPSED BACK INTO GREEN. The tests still ran and still passed; the "
               "point is that passing HERE is not evidence about a runner. Folding that into the "
               "green verdict is the over-claim the file's own header forbids.",
        "file": "ci_sim.py",
        "find": "    if plat:\n        print(\"\\u26aa UNKNOWN",
        "replace": "    if []:\n        print(\"\\u26aa UNKNOWN",
        "matches": 1,
    },
]
