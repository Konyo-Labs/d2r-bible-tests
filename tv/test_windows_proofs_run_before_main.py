# -*- coding: utf-8 -*-
"""REG-3214 - THE WINDOWS PROOFS RUN BESIDE THE LINUX SHARDS, ON THE ci/proof-keys-<v> PUSH, BEFORE MAIN.

MEASURED (2026-11-05): .github/workflows/proof-keys-windows.yml ran ONLY on workflow_run after Publish succeeded - v3863:
Publish 67 min, then the Windows set ~2 h (an 839 KB proofs-<sha>-win32.tgz); v3864: none at all - while a Windows PC
imports only the win32 set first: OLD PC ALT's proofRelease read "GitHub has no proof bundle for 9d9485ea6 yet (the Linux
set is already in)", so it re-proved alone for hours after every ship. Held here:
  * the Windows workflow runs on a push to ci/proof-keys-* (beside the Linux shards, before main), keeps workflow_dispatch,
    and after Publish runs only while this commit's Windows set is not banked yet (a main push that skipped the ci branch);
  * it is still NOT one of ci_verdict.REQUIRED (nothing required changes meaning) and its shards never fail the run;
  * it starts from one seed job: the newest Windows set in the bank for ANOTHER commit plus this commit's own
    (tv/proof_seed.py --flavor win32 --prior) - a seed serves only byte-identical proofs - and is bounded like the
    Linux shards (job 75, step 70, heart2's deadline at job minute 55);
  * newest_prior picks the newest asset of THIS flavor for another commit, never this one, never the other flavor.
Fixtures only - the bank listing and download are replaced; no network. RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import ci_verdict as CV  # noqa: E402
import proof_seed as SEED  # noqa: E402
import proof_shard as PS  # noqa: E402

SHA = "9d9485ea61f7482320cdc47a5d0e05f670776e77"
PREV = "b" * 40
OLDER = "a" * 40
WF = os.path.join(ROOT, ".github", "workflows", "proof-keys-windows.yml")


def _code(text):
    return "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("#"))


def _job(text, name):
    m = re.search(r"\n  %s:\n(.*?)(?=\n  [A-Za-z][\w-]*:\n|\Z)" % re.escape(name), "\n" + text.split("\njobs:\n", 1)[-1],
                  re.S)
    return m.group(1) if m else ""


class TheWorkflowRunsBesideTheCiShards(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(WF, encoding="utf-8") as fh:
            cls.wf = _code(fh.read())
        cls.on = "\n" + cls.wf.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]

    def test_it_runs_on_the_ci_proof_keys_push_and_by_hand(self):
        self.assertIn("\n  push:\n    branches:\n      - 'ci/proof-keys-*'\n", self.on,
                      "the Windows set runs only after Publish again - no win32 set when the ship lands")
        self.assertIn("\n  workflow_dispatch:", self.on)
        self.assertIn('workflows: ["Publish — gates, review, then deploy"]', self.on)

    def test_it_is_never_a_ship_gate_and_its_shards_never_fail_the_run(self):
        name = self.wf.split("\n", 1)[0].split("name:", 1)[1].strip()
        self.assertNotIn(name, CV.REQUIRED, "the Windows set became a gate on every ship")
        shard = _job(self.wf, "shard")
        prove = shard[shard.index("- name: Prove this shard on Windows"):]
        self.assertIn("exit 0", prove)
        self.assertNotIn("exit 3", prove, "a Windows shard can fail the run on its seed")

    def test_after_publish_it_runs_only_while_the_set_is_not_banked(self):
        shard = _job(self.wf, "shard")
        self.assertIn("    needs: [seed]\n", shard)
        self.assertIn("(github.event_name != 'workflow_run' || needs.seed.outputs.bank != 'ok')", shard,
                      "the Windows set is proved twice for one commit")

    def test_it_starts_from_the_banks_windows_sets_and_is_bounded(self):
        seed = _job(self.wf, "seed")
        self.assertIn('python3 tv/proof_seed.py --sha "$HEAD_SHA" --flavor win32 --prior', seed)
        self.assertIn("continue-on-error: true", seed)
        shard = _job(self.wf, "shard")
        self.assertEqual(re.findall(r"^    timeout-minutes: (\d+)$", shard, re.M), ["75"])
        prove = shard[shard.index("- name: Prove this shard on Windows"):]
        self.assertEqual(re.findall(r"^        timeout-minutes: (\d+)$", prove, re.M)[:1], ["70"])
        self.assertIn("export HEART2_PROVE_DEADLINE=$(( T0 + 55 * 60 ))", prove)
        self.assertIn('export HEART2_SHARD_SEED="$RUNNER_TEMP/heart2-seed/.heart2_cache.json"', prove)
        self.assertIn("path: ${{ runner.temp }}/heart2-seed", shard)


class TheSeedTakesTheNewestOtherSetOfItsFlavor(unittest.TestCase):

    LISTING = {"assets": [
        {"name": "proofs-%s-win32.tgz" % OLDER, "created_at": "2026-11-04T10:00:00Z"},
        {"name": "proofs-%s-win32.tgz" % PREV, "created_at": "2026-11-05T10:00:00Z"},
        {"name": "proofs-%s-win32.tgz" % SHA, "created_at": "2026-11-05T19:00:00Z"},
        {"name": "proofs-%s.tgz" % ("c" * 40), "created_at": "2026-11-05T20:00:00Z"},
        {"name": "proofs-%s.tgz.partial" % ("d" * 40), "created_at": "2026-11-05T21:00:00Z"},
    ]}

    def test_newest_other_commit_of_this_flavor(self):
        got, why = SEED.newest_prior(SHA, "win32", get=lambda p: self.LISTING)
        self.assertEqual(got, PREV, why)
        self.assertEqual(SEED.newest_prior(SHA, "", get=lambda p: self.LISTING)[0], "c" * 40,
                         "the Linux seed took a Windows set, or the other way round")
        self.assertIsNone(SEED.newest_prior(SHA, "win32", get=lambda p: None)[0])
        self.assertIsNone(SEED.newest_prior(SHA, "win32", get=lambda p: {"assets": []})[0])

    def test_the_prior_set_seeds_but_is_never_named_as_this_commits(self):
        d = tempfile.mkdtemp(prefix="win-seed-law-")
        self.addCleanup(shutil.rmtree, d, True)
        root = os.path.join(d, "pack", "proof-shard-1")
        os.makedirs(root)
        own = {"gw": {0}}
        with io.open(os.path.join(root, PS.STORE_NAME), "w", encoding="utf-8") as fh:
            json.dump({"format": 2, "entries": {"kw": {"verdict": "PROVEN", "gate": "gw", "proof": 0, "provedAt": 5}},
                       "shard": PS.manifest(1, 1, PREV, False, "p", own, None, None, 5)}, fh)
        prev_tgz = os.path.join(d, "prev.tgz")
        self.assertEqual(PS.bank(os.path.join(d, "pack"), prev_tgz, say=lambda *a: None), 0)
        asked = []

        def dl(sha, dest, flavor=""):
            asked.append((sha, flavor))
            if (sha, flavor) == (PREV, "win32"):
                shutil.copyfile(prev_tgz, dest)
                return "ok", "downloaded"
            return "absent", "none"
        rec = SEED.build(SHA, "", os.path.join(d, "work"), os.path.join(d, "out"), flavor="win32", prior=True,
                         download=dl, get=lambda p: self.LISTING, say=lambda *a: None)
        self.assertEqual(asked, [(SHA, "win32"), (PREV, "win32")])
        self.assertTrue(rec["seeded"])
        self.assertEqual((rec["bank"], rec["prior"]), ("absent", "ok"))
        with io.open(os.path.join(d, "out", SEED.SERVED_NAME), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["served"], [], "the last version's proofs were named as this commit's")
        with io.open(os.path.join(d, "out", PS.STORE_NAME), encoding="utf-8") as fh:
            self.assertEqual(sorted(json.load(fh)["entries"]), ["kw"])


RED_PROOF = [
    {"why": "REG-3214 - the Windows set runs only after Publish again (v3864: no win32 set ever)",
     "file": ".github/workflows/proof-keys-windows.yml",
     "find": "on:\n  push:\n    branches:\n      - 'ci/proof-keys-*'\n  workflow_run:\n",
     "replace": "on:\n  workflow_run:\n",
     "matches": 1},
    {"why": "REG-3214 - the Windows set starts cold every version (no prior set from the bank)",
     "file": ".github/workflows/proof-keys-windows.yml",
     "find": "--flavor win32 --prior\n",
     "replace": "--flavor win32\n",
     "matches": 1},
    {"why": "REG-3214 - after Publish the Windows set is proved again though the ci push banked it",
     "file": ".github/workflows/proof-keys-windows.yml",
     "find": " && (github.event_name != 'workflow_run' || needs.seed.outputs.bank != 'ok') }}\n",
     "replace": " }}\n",
     "matches": 1},
    {"why": "REG-3214 - the Windows shards keep v3863's 340-minute bound",
     "file": ".github/workflows/proof-keys-windows.yml",
     "find": "    timeout-minutes: 75\n    strategy:",
     "replace": "    timeout-minutes: 340\n    strategy:",
     "matches": 1},
    {"why": "REG-3214 - the prior picked is this very commit's (no other version's proofs seed it)",
     "file": "tv/proof_seed.py",
     "find": "            if m and m.group(1) != sha and (best is None",
     "replace": "            if m and (best is None",
     "matches": 1},
    {"why": "REG-3214 - the prior ignores the flavor: a Linux set seeds the Windows run and back",
     "file": "tv/proof_seed.py",
     "find": "    pat = re.compile(r\"^proofs-([0-9a-f]{40})%s\\.tgz$\" % (re.escape(\"-\" + flavor) if flavor else \"\"))\n",
     "replace": "    pat = re.compile(r\"^proofs-([0-9a-f]{40})(?:-win32)?\\.tgz$\")\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
