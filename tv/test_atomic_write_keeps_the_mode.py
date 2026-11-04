# -*- coding: utf-8 -*-
"""v2795 — atomic_write SILENTLY DISABLED THE ENTIRE PRE-PUSH GATE.

`os.replace` moves the TEMP FILE's inode into place, and a temp file is created with the default
0644. So every executable `atomic_write` touched came out NON-EXECUTABLE. Measured 2026-09-08:

    hooks/pre-push at v2793   100755
    hooks/pre-push at v2794   100644     <- this function, editing the hook to add a gate

and git said so, once, in a hint that scrolls past:

    hint: The 'hooks/pre-push' hook was ignored because it's not set as executable.

**v2794 then pushed straight to origin with no gates at all** — no test_control, no render, no
Playwright smoke, no second eye, and not even the blueprint check that commit existed to add. The
irony is exact: the commit that installed a new gate is the one that turned every gate off.

=== ⚠⚠ WHY THIS IS THE WORST SHAPE OF FAILURE ===
It is SILENT, it is PERSISTENT, and it disables the thing that would have caught it. A hook that is
merely broken fails loudly; a hook that is not executable is simply not run, and every future push
would have sailed through green-looking until somebody read a `hint:` line. The repo's own rule
covers it — *"a skip is not a pass"* — and here the skip was of the whole gate set.
[[regression-guard]] [[feedback-silence-is-not-evidence]]

=== ⚠ THE FIX IS THE ONE LINE THE ORIGINAL WAS MISSING ===
Preserving the CONTENT while dropping the PERMISSION is not preserving the file. `os.stat` before
the write, `os.chmod` after the replace. A path that did not exist has no mode to copy and
correctly keeps the default.
"""
import io
import os
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

try:
    from console_safe import enable
    enable()
except Exception:
    pass

import bump_version as BV  # noqa: E402


class AtomicWriteKeepsTheModeAndTheHookStaysArmed(unittest.TestCase):

    # ── ⚠⚠ THE LAW ──────────────────────────────────────────────────────────────────────────
    # v3860 - POSIX ONLY: Windows has no execute bit (NTFS reports 0o666/0o444; a file is never S_IXUSR), so on win32
    # this case could only fail and never measure. Git for Windows decides by the shebang instead - see the hook case.
    @unittest.skipUnless(os.name == "posix", "POSIX only: Windows has no execute bit to keep")
    def test_atomic_write_PRESERVES_an_executable_bit(self):
        """★★★ The defect, reproduced end to end. Without this, any tool that edits a script
        through atomic_write disarms it, and the failure is a hint nobody reads."""
        d = tempfile.mkdtemp()
        p = os.path.join(d, "hookish.sh")
        io.open(p, "w").write("#!/bin/sh\necho one\n")
        os.chmod(p, 0o755)
        before = os.stat(p).st_mode & 0o777
        BV.atomic_write(p, "#!/bin/sh\necho two\n")
        after = os.stat(p).st_mode & 0o777
        self.assertEqual(after, before,
                         "atomic_write dropped the mode %o -> %o. Any executable it edits is "
                         "silently disarmed — this is how the whole pre-push gate was turned off "
                         "by the commit that added a gate to it." % (before, after))
        self.assertTrue(after & stat.S_IXUSR, "the owner-execute bit is gone")

    # ── ⚠⚠ v2797 — THE FIX ITSELF LEFT A WINDOW, FOUND BY A COLD CROSS-FAMILY REVIEW ────────
    # v3860 - POSIX ONLY: Windows has no execute bit (NTFS reports 0o666/0o444; a file is never S_IXUSR), so on win32
    # this case could only fail and never measure. Git for Windows decides by the shebang instead - see the hook case.
    @unittest.skipUnless(os.name == "posix", "POSIX only: Windows has no execute bit to keep")
    def test_the_mode_is_ON_THE_TEMP_FILE_at_the_moment_of_replace(self):
        """★★★ THE RACE, AND IT IS THE ORIGINAL DEFECT IN MINIATURE.

        v2795 restored the mode by chmod'ing AFTER os.replace. Between those two calls the new
        content is already live under the TEMP file's mode, which is born under umask. Measured by
        stopping the sequence mid-way:

            target before         0o755
            the temp file's mode  0o644   <- born under umask
            AFTER os.replace      0o644   <- the window
            after os.chmod        0o755

        A push starting inside that window sees a NON-EXECUTABLE hooks/pre-push and skips every
        gate — exactly what v2794 did, reduced to a race. Not hypothetical: pushes run in the
        background here while other work continues.

        ⚠ THIS WATCHES THE TEMP FILE, NOT THE RESULT. Asserting the final mode passes either way
        and would have missed the whole defect; the only moment that distinguishes the two designs
        is the instant `os.replace` is called. [[feedback-verify-not-proxy]]
        """
        d = tempfile.mkdtemp()
        p = os.path.join(d, "hookish.sh")
        io.open(p, "w").write("#!/bin/sh\necho one\n")
        os.chmod(p, 0o755)
        seen = {}
        real = os.replace

        def spy(src, dst):
            seen["mode"] = os.stat(src).st_mode & 0o777
            return real(src, dst)

        os.replace = spy
        try:
            BV.atomic_write(p, "#!/bin/sh\necho two\n")
        finally:
            os.replace = real
        self.assertIn("mode", seen, "os.replace was never called — atomic_write no longer renames "
                                    "into place, so this law is measuring nothing")
        self.assertEqual(
            seen["mode"], 0o755,
            "at the moment of os.replace the temp file was %s, so the destination is briefly %s. "
            "For hooks/pre-push that window is a push that runs with NO gates. chmod the temp file "
            "BEFORE the replace so content and permissions arrive in one step."
            % (oct(seen["mode"]), oct(seen["mode"])))

    def test_no_stray_temp_survives_a_FAILED_write(self):
        """⚠ mkstemp makes the temp name unique, which fixes one hazard and creates another: a
        failure between create and replace would leave an unpredictable file beside his data
        forever, and `bible.html` lives in that directory."""
        d = tempfile.mkdtemp()
        p = os.path.join(d, "x.txt")
        io.open(p, "w").write("before")

        class Boom(Exception):
            pass

        real = os.replace

        def bang(src, dst):
            raise Boom("simulated failure between write and replace")

        os.replace = bang
        try:
            with self.assertRaises(Boom):
                BV.atomic_write(p, "after")
        finally:
            os.replace = real
        strays = [f for f in os.listdir(d) if f != "x.txt"]
        self.assertEqual(strays, [], "a failed write left %s behind" % strays)
        self.assertEqual(io.open(p).read(), "before",
                         "the original was damaged by a write that never completed")

    def test_a_NEW_file_still_gets_the_default(self):
        """⛔ The other half: a path that did not exist has no mode to inherit, and inventing one
        would be its own surprise."""
        d = tempfile.mkdtemp()
        p = os.path.join(d, "fresh.txt")
        BV.atomic_write(p, "hello")
        self.assertFalse(os.stat(p).st_mode & stat.S_IXUSR,
                         "a brand-new text file came out executable")

    def test_it_leaves_no_tmp_behind(self):
        """⚠ The rename is the whole mechanism; a leftover .tmp means the replace did not happen."""
        d = tempfile.mkdtemp()
        p = os.path.join(d, "x.txt")
        BV.atomic_write(p, "a")
        self.assertFalse(os.path.exists(p + ".tmp"), "the temp file survived the write")

    # ── ⛔ AND THE HOOK ITSELF MUST BE ARMED ─────────────────────────────────────────────────
    def test_the_pre_push_hook_is_EXECUTABLE_in_the_index(self):
        """★★★ The working tree's mode is not what git ships — the INDEX mode is. v2794 committed
        100644 and every clone would have inherited a dead hook. Checked with `git ls-files -s`,
        which reports the mode git actually recorded."""
        try:
            out = subprocess.check_output(["git", "ls-files", "-s", "hooks/pre-push"],
                                          cwd=REPO, stderr=subprocess.STDOUT, timeout=30)
        except Exception as e:
            self.skipTest("git could not be asked (%s) — UNMEASURED, not passing" % type(e).__name__)
        line = out.decode("utf-8", "replace").strip()
        self.assertTrue(line, "hooks/pre-push is not tracked at all")
        mode = line.split()[0]
        self.assertEqual(mode, "100755",
                         "hooks/pre-push is recorded as %s, so git will IGNORE it and every push "
                         "runs with no gates — exactly what happened on v2794" % mode)

    def test_the_hook_is_executable_on_disk_too(self):
        """⚠ The index mode arms a fresh clone; the disk mode arms THIS one. Both, or the gate is
        off for whoever is actually pushing."""
        p = os.path.join(REPO, "hooks", "pre-push")
        self.assertTrue(os.path.isfile(p), "the pre-push hook is gone")
        if os.name == "nt":
            # ⚠ v3860 - WINDOWS ASKS THE FIRST LINE, NOT THE MODE. MEASURED 2026-11-04 on the new Konyo · ALT (Git
            # 2.56.0.windows.4): a hook file with mode 0o100666 and no S_IXUSR RAN when it began with `#!/bin/sh`; the
            # same hook without that line did not run and the commit failed (rc 1). So here the armed hook is the one
            # whose first two bytes are `#!` - the mode bit is a question Windows never asks.
            with io.open(p, "rb") as fh:
                head = fh.read(2)
            self.assertEqual(head, b"#!", "hooks/pre-push does not start with #!, so Git for Windows will not run "
                                          "it and this clone pushes with no gates")
            return
        self.assertTrue(os.stat(p).st_mode & stat.S_IXUSR,
                        "hooks/pre-push is not executable on disk, so git silently skips it and "
                        "this clone pushes with no gates")


RED_PROOF = [
    {
        'why': "Deletes the ONLY capture of the destination's existing permission bits in atomic_write (tv/bump_version.py). With _mode None the function takes the brand-new-file branch — chmod(tmp, 0o666 & ~umask) = 0644 — and the post-replace fallback, guarded by `if _mode is not None`, never fires, so os.replace lands a 0644 inode over a 0755 script. That is the v2794 defect exactly: an executable edited through atomic_write comes out non-executable, hooks/pre-push goes 100755 -> 100644, and git silently skips every gate. The anchor is the executable statement, not a comment or a message string; the docstring's many prose mentions of the mode are untouched by this literal (count 1 in the file).  MEASURED: untampered OK — `python3 tv/test_atomic_write_keeps_the_mode.py` ran 7 tests, verdict OK, 0.015s.; tampered (all 1) FAILED (failures=2) — 7 tests run. test_atomic_write_PRESERVES_an_executable_bit: Assertio; reddened law AtomicWriteKeepsTheModeAndTheHookStaysArmed.test_atomic_write_PRESERVE; ALONE RED ALONE — `python3 -m unittest test_atomic_write_keeps_the_mode.AtomicWriteKeepsTheModeAndTheHookStaysArmed..",
        'file': 'bump_version.py',
        'find': '_mode = os.stat(path).st_mode',
        'replace': '_mode = None',
        'matches': 1,
        'needs': 'posix',   # v3860 - only the POSIX execute-bit cases catch it; Windows has no execute bit
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
