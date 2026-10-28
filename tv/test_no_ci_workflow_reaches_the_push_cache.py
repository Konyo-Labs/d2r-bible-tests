# -*- coding: utf-8 -*-
"""#173 (REG-2939) - NO CI WORKFLOW REACHES THE PUSH-TIME PROOF CACHE. Moved out of
test_a_proven_verdict_is_reused_only_on_identical_bytes, verbatim.

heart2's verdict cache is opened only by prove(push=True) on his machines; CI must run every proof (its verdict is the
one of record), so no workflow may run `--push` or name .heart2_cache - except a proof shard (REG-2588), which proves
into its own fresh cache. The rule reads every workflow in .github/workflows: the folder is the denominator, so a new
workflow cannot slip past. That listing is why it lives alone: a law that lists a directory itself cannot have its
proofs saved, and inside the cache law it made all 27 of that law's proofs re-run on every push. Here it is one cheap
case, listed in tv/unkeyable_laws.json on purpose. [[regression-guard]]
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass


class NoCiWorkflowReachesThePushCache(unittest.TestCase):

    def test_no_workflow_runs_a_push_time_prove_or_names_the_cache(self):
        wf = os.path.join(ROOT, ".github", "workflows")
        names = sorted(os.listdir(wf)) if os.path.isdir(wf) else []
        self.assertTrue(names, "PREMISE: no CI workflow was found to read")
        for n in names:
            with io.open(os.path.join(wf, n), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            if n == "proof-keys-shards.yml":
                # REG-2588 - the ONE exception: a proof shard proves at push time into its OWN fresh cache (REG-2585
                # refuses one that already exists). Every --push line must be a shard's, and the cache may be named only
                # where its fresh per-shard path is set - or, REG-2961, as the shard's READ-ONLY seed (HEART2_SHARD_SEED:
                # heart2 serves a seed entry only under the key this checkout's bytes give it) and the seed the fan-in
                # writes from the shards (--merge-shards). Never this machine's store, never a path the hook reads.
                # (ship-chain replay: REG-2961's lines, from the ship line's copy of this half, carried into the moved law)
                lines = text.splitlines()
                self.assertTrue(all("--proof-shard" in l for l in lines if "--push" in l),
                                "workflow %s runs a push-time prove that is not a proof shard" % n)
                self.assertTrue(all(("HEART2_CACHE_PATH=" in l or "HEART2_SHARD_SEED=" in l or "--merge-shards" in l)
                                    for l in lines if ".heart2_cache" in l),
                                "workflow %s names the cache other than as a shard's own fresh path or its seed" % n)
                self.assertTrue(all("heart2-seed/" in l for l in lines if "HEART2_SHARD_SEED=" in l or "--merge-shards" in l),
                                "workflow %s seeds a shard from somewhere other than the restored seed dir" % n)
                continue
            self.assertNotIn(".heart2_cache", text, "workflow %s names the cache" % n)
            self.assertNotIn("--push", text, "workflow %s runs a push-time prove - CI must run every proof" % n)


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "REG-2588 - the proof-shard workflow runs `--prove --push` without --proof-shard: a push-time prove on CI "
               "consults a banked cache instead of running every proof",
        "file": "../.github/workflows/proof-keys-shards.yml",
        "find": "--prove --push --proof-shard \"${{ matrix.shard }}/${PROOF_SHARDS}\" 2>&1",
        "replace": "--prove --push 2>&1",
        "matches": 1,
    },
    {
        "why": "REG-2588 - the shard names the cache other than as its own fresh HEART2_CACHE_PATH: it could start from "
               "a cache it did not prove",
        "file": "../.github/workflows/proof-keys-shards.yml",
        "find": "          export HEART2_CACHE_PATH=\"$D/.heart2_cache.json\"\n",
        "replace": "          cp tv/.heart2_cache.json \"$D/.heart2_cache.json\" || true\n",
        "matches": 1,
    },
]
