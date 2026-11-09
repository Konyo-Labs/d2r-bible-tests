#!/usr/bin/env python3
"""v1710 — Routine I must not shard by file count alone.

--shard=N/6 splits the file list evenly. The every-item simulations live in a
handful of files, so one shard ran 64 tests in 45 minutes while its siblings
finished ~320 in 15. The cure is a dedicated `slow` Playwright project plus a
CI job that runs it, so the 6-way shard only sees the fast files.
"""
from __future__ import annotations

import glob
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _console_safe
    _console_safe()
except Exception:
    pass

REPO = os.path.dirname(HERE)
CFG = os.path.join(REPO, "playwright.config.ts")
WF = os.path.join(REPO, ".github", "workflows", "routine-i-playwright.yml")
TESTS = os.path.join(REPO, "tests")

# Keep this list in lockstep with playwright.config.ts. A file that grows a
# 600s timeout and is not named here will land back in a fast shard.
KNOWN_SLOW = {
    "golden_intake.spec.ts",
    "platform_routing_audit.spec.ts",
    "v333_recipe_simulation.spec.ts",
    "v425_vault_simulation.spec.ts",
    "v42_full_ux_audit.spec.ts",
    "v43_editorial_audit.spec.ts",
    "v532_forge_base_sim.spec.ts",
    "v532_forge_lifecycle_sim.spec.ts",
    "v535_ux_simulation.spec.ts",
    "v565_forge_all_words_sim.spec.ts",
    "v566_grail_forges_all_items_sim.spec.ts",
    "v603_ux_audit_sim.spec.ts",
    "v628_exact_fit_gate.spec.ts",
    "v645_every_item_sim.spec.ts",
}


def _specs():
    return sorted(
        os.path.relpath(p, TESTS)
        for p in glob.glob(os.path.join(TESTS, "**", "*.spec.ts"), recursive=True)
        if "/golden/" not in p.replace("\\", "/")
    )


RED_PROOF = [
    {
        "why": "v1710's defect: with no 'slow' project the six-way shard splits by FILE COUNT "
               "alone, the every-item simulations pile into one shard, and Routine I times out on "
               "that shard while five others sit idle — a red CI run caused by arithmetic, not "
               "by the code under test",
        "file": "playwright.config.ts",
        "find": "          name: 'slow',",
        "replace": "          name: 'sloooow',",
        "matches": 1,
    },
    {
        "why": "the workflow stops running the slow project at all. Every simulation silently "
               "stops being executed and CI goes green FASTER, which is the most dangerous shape "
               "a shard bug can take",
        "file": ".github/workflows/routine-i-playwright.yml",
        "find": "--project=slow",
        "replace": "--project=chromium",
        "matches": 1,
    },
]


class TestSlowProjectExists(unittest.TestCase):
    def test_config_declares_a_slow_project(self):
        cfg = open(CFG, encoding="utf-8").read()
        self.assertIn("name: 'slow'", cfg)
        self.assertIn("name: 'chromium'", cfg)
        self.assertIn("testIgnore:", cfg)
        self.assertIn("testMatch:", cfg)

    def test_known_slow_files_still_exist(self):
        present = {os.path.basename(p) for p in _specs()}
        missing = sorted(KNOWN_SLOW - present)
        self.assertEqual(missing, [], "slow list names files that are gone: %s" % missing)

    def test_workflow_runs_slow_off_the_fast_shard(self):
        """The slow project keeps its own 2-way shard. The fast job's count is the dealer's."""
        import re
        wf = open(WF, encoding="utf-8").read()
        self.assertIn("--project=chromium", wf)
        self.assertIn("--project=slow", wf)
        # v3891 (#194) - the fast count is the stamp check's, chosen from measured costs each round
        self.assertIn('routine_i_shards.py --shard "$SHARD" --of "$N"', wf, "the fast job no longer asks the dealer")
        self.assertIn("shard ${{ matrix.shard }}/${{ needs.stamp-check.outputs.n }}", wf)
        self.assertIn("slow ${{ matrix.shard }}/2", wf)
        self.assertIn("--shard=${{ matrix.shard }}/2", wf)
        self.assertNotIn("slow ${{ matrix.shard }}/${{ needs.stamp-check.outputs.n }}", wf,
                         "the slow project was moved onto the fast shard count")
        # merge must wait for the slow job too, or a green merge hides it
        self.assertRegex(wf, r"needs:\s*\[[^\]]*(test|slow)")


if __name__ == "__main__":
    unittest.main()
