#!/usr/bin/env python3
"""v3842 (GATE-TRIM B) - every worktree of one repo banks into ONE gate ledger, in the git common dir.

The ledger used to live in each checkout's tv/, so a ship worktree's --full PASSes never reached the push made from
the main checkout, and the hook re-ran gates that exact SHA had just passed. Driven on a fixture repo with a linked
worktree: both resolve the same ledger file under <common dir>/tvd-gate-ledger, TV_GATE_LEDGER still wins, and a
directory that is not a git checkout keeps the old per-checkout file. The carry rule itself is untouched and is held
by test_a_gate_proven_on_these_bytes_is_carried / test_a_red_gate_is_never_carried_as_a_pass.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "gate_ledger.py")


def _env():
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k != "TV_GATE_LEDGER"}


def _ledger_of(tv_dir, extra=None):
    env = _env()
    env.update(extra or {})
    code = ("import sys; sys.path.insert(0, %r); sys.path.insert(1, %r); import gate_ledger as g; "
            "print(g.ledger_path())" % (tv_dir, HERE))
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=60)
    if p.returncode != 0:
        raise AssertionError(p.stderr[-1500:])
    return os.path.realpath(p.stdout.strip())


class EveryWorktreeBanksIntoOneLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="tvd-ledger-share-")
        cls.main = os.path.join(cls.tmp, "main")
        cls.wt = os.path.join(cls.tmp, "wt")
        os.makedirs(os.path.join(cls.main, "tv"))
        shutil.copy(SRC, os.path.join(cls.main, "tv", "gate_ledger.py"))
        g = lambda *a, cwd=None: subprocess.run(["git"] + list(a), cwd=cwd or cls.main, env=_env(),
                                                capture_output=True, text=True, check=True)
        g("init", "-q")
        g("config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        g("-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
        g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "fixture")
        g("worktree", "add", "-q", "--detach", cls.wt)
        cls.plain = os.path.join(cls.tmp, "plain", "tv")
        os.makedirs(cls.plain)
        shutil.copy(SRC, os.path.join(cls.plain, "gate_ledger.py"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_main_and_worktree_share_one_file_in_the_common_dir(self):
        a = _ledger_of(os.path.join(self.main, "tv"))
        b = _ledger_of(os.path.join(self.wt, "tv"))
        self.assertEqual(a, b, "two worktrees of one repo bank into two ledgers")
        want = os.path.realpath(os.path.join(self.main, ".git", "tvd-gate-ledger", ".gate_ledger.json"))
        self.assertEqual(a, want)

    def test_the_override_still_wins(self):
        p = os.path.join(self.tmp, "elsewhere.json")
        self.assertEqual(_ledger_of(os.path.join(self.wt, "tv"), {"TV_GATE_LEDGER": p}), os.path.realpath(p))

    def test_no_git_keeps_the_checkouts_own_file(self):
        self.assertEqual(_ledger_of(self.plain, {"GIT_CEILING_DIRECTORIES": os.path.dirname(os.path.dirname(self.plain))}),
                         os.path.realpath(os.path.join(self.plain, ".gate_ledger.json")))


if __name__ == "__main__":
    unittest.main()
