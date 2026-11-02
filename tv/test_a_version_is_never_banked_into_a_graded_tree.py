# -*- coding: utf-8 -*-
"""v3330 — A VERSION IS NEVER BANKED INTO A TREE SOMEONE IS GRADING.

His ruling, from the #46 false alarm: *"do not write while a gate runs"* must be a REFUSAL, not a
habit. It existed as PROSE in CLAUDE.md, in regression-guard, and in every staged apply-script —
four copies, none enforcing — while an entire session was spent hand-typing
`pgrep -f hooks/pre-push` before each write. That worked every time, which is exactly what a habit
looks like until the once it does not.

WHY THE BANK STEP: `hooks/pre-push` grades the WORKING TREE, not the commit (REG-1131). A version
banked mid-run earns a green verdict about bytes that are not the ones shipping — indistinguishable
from a correct one, which is what makes it the most expensive answer this repo produces.

⚠⚠ TWO SIGNALS, AND THE SECOND IS NOT BELT-AND-BRACES. MEASURED 2026-09-18 against a REAL running
gate:

    gate flock held   : False
    pre-push running  : True  (pid 59755)

The hook holds the tree far longer than `run_gates` does — through renders, console demos and the
Playwright smoke — and the flock is released for all of it. A lock-only check would have answered
"tree is free" while a hook was actively grading. That case was predicted when the module was
designed and then measured, rather than reasoned about and assumed.

⚠ UNKNOWN IS NOT FREE. If neither signal can be asked, `why()` returns a sentence saying so. A
writer that cannot find out whether a gate is running must not assume the happy answer — the
confident-zero shape this repo keeps paying for. [[unknown-stays-unknown]]

⚠ REACH, STATED: this cannot cover an ad-hoc edit. A heredoc writing bible.html will never consult
a module it does not import. It covers the BANK step, which is the one every ship passes.
[[the-unjoined-end]]
"""
import io
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import tree_busy as TB  # noqa: E402


class TestAVersionIsNeverBankedIntoAGradedTree(unittest.TestCase):

    def setUp(self):
        self._lock, self._pp = TB._gate_lock_held, TB._prepush_running

    def tearDown(self):
        TB._gate_lock_held, TB._prepush_running = self._lock, self._pp

    def _stub(self, lock, pp):
        TB._gate_lock_held = lambda *a, **k: lock
        TB._prepush_running = lambda *a, **k: pp

    def test_a_free_tree_is_free(self):
        """⚠ THE BASELINE. A refusal that never passes is an off switch, not a guard."""
        self._stub((False, ""), (False, ""))
        self.assertIsNone(
            TB.why(),
            "the tree reads BUSY with both signals clear. A guard that refuses on a free tree "
            "blocks every ship and gets removed within a day.")

    def test_a_held_gate_lock_refuses(self):
        self._stub((True, "run_gates pid 1"), (False, ""))
        w = TB.why()
        self.assertTrue(w and "gate run holds this tree" in w,
                        "a held gate lock did not refuse: %r" % w)

    def test_a_RUNNING_PREPUSH_refuses_even_with_the_lock_FREE(self):
        """⚠⚠ THE MEASURED CASE — gate flock False, pre-push True, pid 59755, 2026-09-18."""
        self._stub((False, ""), (True, "pid 59755"))
        w = TB.why()
        self.assertTrue(
            w and "pre-push hook is running" in w,
            "the lock was free and a pre-push was grading, and this said the tree was free: %r. "
            "That is the exact state measured on a live gate — the hook holds the tree through "
            "renders, demos and smoke while the flock is released." % w)

    def test_ONE_dark_signal_is_already_UNKNOWN(self):
        """⚠⚠ THE CASE THE FIRST CUT MISSED, AND A SECOND EYE FOUND IT.

        `why()` originally said UNKNOWN only when BOTH signals were unaskable (`held is None and
        running is None`). So the flock going dark while pgrep cleanly found nothing fell through
        to `return None` = FREE — with the PRIMARY signal blind. The old UNKNOWN case stubbed
        BOTH as None and therefore could never see it: it tested the one arrangement that
        happened to work. A guard is only as good as the combinations its law actually walks.
        [[unknown-stays-unknown]] [[regression-guard]]
        """
        # flock dark, process list clean — the exact mixed pair that read as FREE.
        self._stub((None, "fcntl unavailable"), (False, ""))
        w = TB.why()
        self.assertTrue(
            w and "UNKNOWN" in w,
            "the gate lock could not be read and this answered FREE because the OTHER signal "
            "happened to work. One silent signal is enough to refuse - a bump banked here lands "
            "in a tree that may be mid-grade. Got: %r" % w)

        # and the mirror, so neither ordering is privileged
        self._stub((False, ""), (None, "pgrep unavailable"))
        w = TB.why()
        self.assertTrue(
            w and "UNKNOWN" in w,
            "the process list could not be read and this answered FREE. Got: %r" % w)

    def test_a_MENTION_of_the_hook_is_not_a_RUNNING_hook(self):
        """A guard that fails closed on an ordinary editor session is an off switch.

        The first cut matched `pgrep -f hooks/pre-push`, which any command line NAMING the hook
        satisfies. Opening it in an editor would have refused every bump, permanently. Negative
        fixtures are pinned here because that is the half test-venue learned the hard way when a
        watchdog was accused for the string it prints.
        """
        # ⚠⚠ v3334 — EVERY ONE OF THESE WAS MEASURED WRONG IN v3332, AND A SECOND EYE FOUND THEM.
        # That cut inverted v3331's allow-list into a reader deny-list and CLOSED THE LANE: 7 of
        # 11 probes came back FALSE POSITIVES, so ordinary inspection commands blocked every bump.
        # A guard that refuses on `find` or on `git branch push` is an off switch, not a check.
        # [[strictness-that-closes-the-lane]]
        for cmd in ("vi /repo/hooks/pre-push",
                    "less hooks/pre-push",
                    "cat /repo/hooks/pre-push",
                    "grep -n smoke /repo/hooks/pre-push",
                    "find /work -path */hooks/pre-push",      # the hook is a FLAG ARGUMENT
                    "rsync -a hooks/pre-push /tmp/",
                    "tar tf hooks/pre-push.tar",              # a DIFFERENT file (.tar)
                    "node tool.js hooks/pre-push.json",       # a DIFFERENT file (.json)
                    "cat hooks/pre-push.log",
                    "git branch push",                        # `push` as a BRANCH, not a command
                    "git log --grep push",
                    "git checkout -b push",
                    # ⚠ THE ONE THAT REACHES THE POSITION RULE. Every case above is rejected
                    # earlier — by _READERS or by the git branch — so the position rule had NO
                    # coverage at all and its sabotage came back BLIND with a correct match count.
                    # A leader that is neither a reader nor a known runner, with the hook sitting
                    # behind a flag, is the only input that exercises it.
                    "mytool --config /repo/hooks/pre-push",
                    "git config push.default simple",        # `push` inside a CONFIG KEY
                    "git remote add push http://x"):         # a REMOTE named push
            self.assertFalse(
                TB._is_hook_invocation(cmd),
                "%r was read as a RUNNING pre-push. It only mentions the path - matching that "
                "blocks every bump for as long as the editor is open." % cmd)

        # ⚠⚠ v3332 — THE WRAPPERS, AND EVERY ONE OF THESE WAS MEASURED WRONG IN v3331.
        # That cut ALLOW-LISTED the interpreters, so anything it had not thought of fell through
        # to "not running" — 5 of 10 cases missed, all FALSE NEGATIVES, which is the direction
        # that banks a version into a tree a gate is grading. A second eye found it. The list is
        # now a DENY-list of readers, so an unknown wrapper refuses rather than waves through.
        for cmd in ("/bin/sh /repo/hooks/pre-push origin git@host:r.git",
                    "bash hooks/pre-push",
                    "/usr/bin/git push origin main",
                    "git --no-pager push origin main",
                    "git -c http.version=HTTP/1.1 push origin main",   # push outside toks[1:3]
                    "nohup /repo/hooks/pre-push origin git@host:r.git",
                    "env FOO=1 /repo/hooks/pre-push origin",
                    "stdbuf -o0 /repo/hooks/pre-push origin",
                    "/bin/sh /my repo/hooks/pre-push origin",           # a path with a SPACE
                    "FOO=1 /repo/hooks/pre-push origin",                # leading env assignment
                    "/repo/hooks/pre-push origin",                      # executed directly
                    "weirdwrapper /repo/hooks/pre-push origin",         # UNKNOWN leader -> CLOSED
                    # ⚠⚠ v3336 — BOTH MEASURED WRONG IN v3334, found by a second eye. That cut
                    # stepped over global flags using a list of the ones that consume a value.
                    # That list can never be complete: a git-dir containing a SPACE and an
                    # unlisted flag each hid a real push, which is the direction that banks a
                    # version mid-grade.
                    "/usr/bin/git --git-dir /path/with spaces push origin main",
                    "git --super-prefix foo/ push origin main",
                    # ⚠ v3338 — a second eye found this: the -C VALUE was being read as the
                    # SUBCOMMAND. A directory literally named `log` matched the list and returned
                    # False on a real push — a FALSE NEGATIVE, which banks a version mid-grade.
                    "git -C log push origin main"):
            self.assertTrue(
                TB._is_hook_invocation(cmd),
                "%r is a real invocation and was not recognised - the signal this whole module "
                "exists for would be silent exactly when it matters." % cmd)

    def test_UNKNOWN_is_not_free(self):
        self._stub((None, "fcntl unavailable"), (None, "pgrep unavailable"))
        w = TB.why()
        self.assertTrue(
            w and "UNKNOWN" in w,
            "neither signal could be asked and this answered FREE. Not knowing whether a gate is "
            "running is not the same as knowing one is not. Got: %r" % w)

    def test_the_lock_is_RELEASED_after_the_check(self):
        """Holding it would make the check the collision it exists to prevent."""
        with io.open(os.path.join(HERE, "tree_busy.py"), encoding="utf-8") as fh:
            code = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
        self.assertIn(
            "LOCK_UN", code,
            "tree_busy takes the gate lock and never releases it. A checker that holds the lock "
            "IS the second gate run REG-162 is about.")

    def test_the_bank_step_actually_consults_it(self):
        """A module nobody calls is the unjoined end this whole task is about."""
        with io.open(os.path.join(HERE, "bump_version.py"), encoding="utf-8") as fh:
            code = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
        self.assertIn("import tree_busy", code,
                      "bump_version does not import tree_busy — the refusal exists and nothing "
                      "asks it, which is prose with extra steps.")
        self.assertIn("_tb.why(", code, "tree_busy is imported and never asked")

        # ⚠⚠ REACHABILITY, NOT PRESENCE — AND heart2 CAUGHT THE FIRST CUT OF THIS.
        # That cut asserted only that the string "REFUSED to bump" appears somewhere in the file.
        # The sabotage `if _busy:` -> `if False:` leaves the import, the call and the message all
        # perfectly intact while the refusal becomes unreachable, so the proof came back BLIND:
        # 1 match tampered, law still GREEN. A law that asserts a NAME appears is not a law that
        # the code RUNS. Anchor the LIVE CONDITION and require the raise inside ITS body.
        # [[presence-law-vs-reachability-law]] [[source-reading-guard]]
        i = code.find("if _busy:")
        self.assertGreater(
            i, -1,
            "the refusal is no longer guarded by `if _busy:`. Either it was renamed, or the "
            "condition was replaced by a constant - and a constant-false guard leaves every "
            "string this law used to check exactly where it was.")
        # Bound BOTH ends: the block is the refusal, not its neighbourhood. The next sibling
        # statement at the same indent ends it; refusing to judge a slice whose far end is a
        # guess is the rule that made the byte-window scars.
        j = code.find("\n    if ", i + 1)
        self.assertGreater(
            j, i, "could not bound the refusal block - refusing to judge an unbounded slice.")
        blk = code[i:j]
        self.assertIn(
            "REFUSED to bump", blk,
            "`if _busy:` exists but does not raise the refusal inside its own body. The message "
            "lives somewhere else in the file, so the branch that fires on a busy tree does "
            "something other than refuse.")
        self.assertIn(
            "raise SystemExit", blk,
            "the busy branch does not raise - it may warn, and a warning is not a refusal.")




class AContinuationLineIsNotAProcess(unittest.TestCase):
    """REG-1846 - pgrep prints a multi-line argv as several lines; only a line that starts with a pid is a process."""

    def _run(self, stdout):
        real = TB.subprocess.run
        class _R(object):
            returncode = 0
        _R.stdout = stdout
        TB.subprocess.run = lambda *a, **k: _R()
        try:
            return TB._prepush_running()
        finally:
            TB.subprocess.run = real

    def test_a_prompt_that_names_the_hook_is_not_a_running_hook(self):
        out = ("25680 /opt/x/.grok/bin/grok -p Code review. The following is a diff\n"
               "READ-ONLY bash hooks/pre-push origin url\n"
               "hooks/pre-push\n")
        running, why = self._run(out)
        self.assertIs(False, running, "a line inside another program's argv read as a running hook: %r" % why)

    def test_a_real_hook_is_still_seen(self):
        running, why = self._run("4242 bash hooks/pre-push origin https://example.invalid/repo.git\n")
        self.assertIs(True, running)
        self.assertIn("4242", why)

    def test_windows_reads_its_own_process_list(self):
        """Dean's machine has no pgrep. A quiet Windows process list is free, and a hook line is busy."""
        quiet = ["100 C:\\Windows\\System32\\powershell.exe",
                 "200 pythonw.exe tv\\control_app.py --open --background"]
        with mock.patch("tree_busy.sys.platform", "win32"), \
             mock.patch("tree_busy._windows_command_lines", return_value=quiet):
            running, detail = TB._prepush_running()
        self.assertIs(False, running, detail)
        busy = quiet + ["300 bash hooks/pre-push origin https://example.invalid/repo.git"]
        with mock.patch("tree_busy.sys.platform", "win32"), \
             mock.patch("tree_busy._windows_command_lines", return_value=busy):
            running, detail = TB._prepush_running()
        self.assertIs(True, running)
        self.assertIn("300", detail)

    def test_a_missing_lock_file_is_free_without_fcntl(self):
        """No lock file is a measurement. It does not wait on fcntl, which Windows does not have."""
        with mock.patch("tree_busy.os.path.exists", return_value=False):
            held, who = TB._gate_lock_held()
        self.assertIs(False, held)
        self.assertEqual(who, "")

    def test_a_present_lock_without_fcntl_stays_unknown(self):
        real = __import__
        def boom(name, *a, **k):
            if name == "fcntl":
                raise ImportError("no fcntl")
            return real(name, *a, **k)
        with mock.patch("tree_busy.os.path.exists", return_value=True), \
             mock.patch("builtins.__import__", boom):
            held, who = TB._gate_lock_held()
        self.assertIsNone(held)
        self.assertIn("fcntl", who)


RED_PROOF = [
    {
        "why": "REG-1846 - a continuation line of another program's argv is read as a process again",
        "file": "tv/tree_busy.py",
        "find": "        if not pid.isdigit():\n            continue\n",
        "replace": "",
        "matches": 1,
    },
    {
        # Stops value-flags consuming their value, so `-C log push` reads the DIRECTORY as the
        # subcommand, matches the list and returns False on a real push.
        "why": "a value-flag value read as a subcommand hides a real push behind git -C",
        "file": "tv/tree_busy.py",
        "find": "        if t in _GIT_VALUE_FLAGS:\n            i += 2",
        "replace": "        if False:\n            i += 2",
        "matches": 1,
    },
    {
        # ⚠ Restores v3334's behaviour exactly: decide on the FIRST bare token. A git-dir with a
        # space, or any unlisted value-flag, then puts its VALUE there and the real push is missed.
        "why": "deciding on the first bare token lets a spaced git-dir hide a real push",
        "file": "tv/tree_busy.py",
        "find": '        if b == "push":\n            return True',
        "replace": '        return b == "push"',
        "matches": 1,
    },
    {
        "why": "without the position rule a hook named as a flag argument reads as a running gate",
        "file": "tv/tree_busy.py",
        "find": '    if any(t.startswith("-") for t in before[1:]):',
        "replace": "    if False:",
        "matches": 1,
    },
    {
        # ⚠ Restores the `and` the second eye refuted: UNKNOWN then requires BOTH signals dark,
        # so one blind signal plus one clean one reads as FREE again.
        "why": "requiring BOTH signals to be dark lets one blind signal read as a free tree",
        "file": "tv/tree_busy.py",
        "find": "    if _dark:",
        "replace": "    if held is None and running is None:",
        "matches": 1,
    },
    {
        "why": "dropping the pre-push signal calls the tree free while a hook is grading it",
        "file": "tv/tree_busy.py",
        "find": "    running, detail = _prepush_running(repo)\n    if running:",
        "replace": "    running, detail = _prepush_running(repo)\n    if False:",
        "matches": 1,
    },
    {
        "why": "removing the bank-step refusal puts the rule back to being prose nobody enforces",
        "file": "tv/bump_version.py",
        "find": "    if _busy:\n        raise SystemExit(",
        "replace": "    if False:\n        raise SystemExit(",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
