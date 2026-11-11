# -*- coding: utf-8 -*-
"""REG-2961 (#161 stage 2, his go 2026-10-21: "do whatever is recommended") - CI REUSES A BANKED PROOF, AND ONLY FOR THE
BYTES IT WAS PROVED ON.

Before: every proof-keys shard proved into an EMPTY $RUNNER_TEMP cache (REG-2585), so CI re-proved every law on every
run - ~41 min a shard - while the Mac reused byte-identical proofs at every push. Now each shard starts from the proofs
the last main run banked: restored by actions/cache (key prefix heart2-proofs-) into a READ-ONLY seed
(HEART2_SHARD_SEED), and the main run's fan-in merges the shards' PROVENs into the next seed and saves it (main only:
main's cache scope is the one every branch may restore).

THE SAFETY IS heart2's KEY, CHECKED IN CODE BEFORE IT WAS RELIED ON: _VerdictCache._key is a sha256 over the law file,
the proof, the gate's spec and EVERY input's repo path and bytes; peek() looks an entry up only under the key key_for()
takes from the checkout's bytes NOW. So a broad restore (any commit's seed) can serve a proof only for byte-identical
inputs - pinned below on a fixture sandbox whose subject changes - and test_a_proven_verdict_is_reused_only_on_identical_
bytes pins the key itself. The shard's own file still starts empty (REG-2585) and holds only what this run served or
proved for its own plan: a seed entry it never served is never written, so the fan-in and the Mac's import (all or
nothing, REG-2586) never see a proof outside a shard's plan. A seed is read only in a proof shard, never this machine's
store. Fixtures only, in temp dirs. RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import heart2  # noqa: E402
import proof_shard as PS  # noqa: E402

WF = os.path.join(ROOT, ".github", "workflows", "proof-keys-shards.yml")
T0 = 1790000000000
PR = {"why": "fixture", "file": "subj.txt", "find": "one", "replace": "two", "matches": 1}


def _proven(gate, idx, at=T0, tree="/runner/repo"):
    return {"verdict": "PROVEN", "provedAt": at, "gate": gate, "proof": idx, "tree": tree, "kind": "static"}


def _quiet(*a, **k):
    return None


class ASeedServesOnlyItsOwnBytes(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="seedlaw-")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.sb = os.path.join(self.d, "tv")
        os.makedirs(self.sb)
        with io.open(os.path.join(self.sb, "test_fx_seed.py"), "w", encoding="utf-8") as fh:
            fh.write(u"import unittest\nclass T(unittest.TestCase):\n    def test(self):\n"
                     u"        self.assertTrue(open('subj.txt').read())\n")
        self._subject(u"one\n")

    def _subject(self, text):
        with io.open(os.path.join(self.sb, "subj.txt"), "w", encoding="utf-8") as fh:
            fh.write(text)

    def _cache(self, name="shard"):
        """a store at <name>/.heart2_cache.json - the one basename heart2's store writer accepts"""
        os.makedirs(os.path.join(self.d, name), exist_ok=True)
        return heart2._VerdictCache(path=os.path.join(self.d, name, PS.STORE_NAME), say=_quiet)

    def _key(self):
        return self._cache("keyer").key_for(self.sb, "fx_seed", "test_fx_seed.py", PR)[0]

    def _seed(self, entries):
        p = os.path.join(self.d, "seed.json")
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump({"format": 2, "entries": entries}, fh)
        return p

    def test_a_seeded_proof_is_served_under_this_checkouts_key_and_written_as_this_runs_own(self):
        k1 = self._key()
        self.assertTrue(k1, "PREMISE: the fixture proof is keyable")
        seed = self._seed({k1: _proven("fx_seed", 0), "f" * 64: _proven("other_gate", 3)})
        c = self._cache()
        n, why = c.seed_from(seed)
        self.assertEqual((n, why), (2, None))
        self.assertEqual(c.entries, {}, "the seed was read into the shard's own entries")
        self.assertIsNotNone(c.peek(k1), "a seeded proof over identical bytes is not served")
        self.assertIsNotNone(c.lookup(k1))
        c._flush()
        with io.open(os.path.join(self.d, "shard", PS.STORE_NAME), encoding="utf-8") as fh:
            got = json.load(fh)["entries"]
        self.assertEqual(sorted(got), [k1], "the shard's file holds what it did not serve, or lost what it did: %r" % sorted(got))

    def test_the_same_seed_serves_nothing_once_a_byte_changes(self):
        k1 = self._key()
        seed = self._seed({k1: _proven("fx_seed", 0)})
        self._subject(u"one, and a byte more\n")
        k2 = self._key()
        self.assertNotEqual(k1, k2, "BASELINE: the key did not move with the subject's bytes")
        c = self._cache()
        c.seed_from(seed)
        self.assertIsNone(c.peek(k2), "a seed proved over other bytes was served")
        self.assertIsNone(c.lookup(k2))

    def test_an_unreadable_seed_seeds_nothing_and_says_why(self):
        p = os.path.join(self.d, "seed.json")
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(u"{not json")
        c = self._cache()
        n, why = c.seed_from(p)
        self.assertEqual(n, 0)
        self.assertTrue(why)
        self.assertEqual(c.seed, {})

    def test_only_a_proof_shard_reads_a_seed(self):
        k1 = self._key()
        seed = self._seed({k1: _proven("fx_seed", 0)})
        said = []
        with mock.patch.object(heart2, "CACHE", os.path.join(self.d, PS.STORE_NAME)), \
                mock.patch.object(heart2, "_red_fold_checkouts", _quiet), \
                mock.patch.dict(os.environ, {"HEART2_SHARD_SEED": seed}):
            with mock.patch.dict(heart2._SHARD, {"spec": None}):
                plain = heart2.open_cache(say=said.append)
            with mock.patch.dict(heart2._SHARD, {"spec": (1, 16)}):
                shard = heart2.open_cache(say=said.append)
        self.assertEqual(plain.seed, {}, "a push on this machine read a CI seed")
        self.assertEqual(sorted(shard.seed), [k1], "a proof shard did not read its seed")
        self.assertTrue(any("REG-2961 SEED: 1 proof(s)" in s for s in said), said)


class TheNextSeedIsMergedFromTheShards(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="seedmerge-")
        self.addCleanup(shutil.rmtree, self.root, True)

    def _shard(self, k, entries, manifest=True):
        d = os.path.join(self.root, "proof-shard-%d" % k)
        os.makedirs(d)
        body = {"format": 2, "entries": entries}
        if manifest:
            body["shard"] = {"v": 1, "k": k, "n": 2, "finished": True}
        with io.open(os.path.join(d, PS.STORE_NAME), "w", encoding="utf-8") as fh:
            json.dump(body, fh)

    def test_only_servable_proofs_the_newer_of_two_and_no_manifest(self):
        old, new = _proven("g", 0, at=T0), _proven("g", 0, at=T0 + 5000)
        elsewhere = dict(_proven("h", 0), verdict="ELSEWHERE")
        traced = dict(_proven("i", 0), kind="traced")
        self._shard(1, {"ka": old, "kb": elsewhere, "kt": traced})
        self._shard(2, {"ka": new, "kc": _proven("j", 1)})
        out = os.path.join(self.root, "seed", PS.STORE_NAME)
        self.assertEqual(PS.merge_shards(self.root, out, say=_quiet), 0)
        with io.open(out, encoding="utf-8") as fh:
            body = json.load(fh)
        self.assertEqual(sorted(body["entries"]), ["ka", "kc"], "a proof the import would never bank went into the seed")
        self.assertEqual(body["entries"]["ka"]["provedAt"], T0 + 5000, "the older of two proofs under one key was kept")
        self.assertNotIn("shard", body, "the seed carries a shard manifest - it is no shard's file")
        self.assertEqual(body["format"], 2)
        self.assertEqual(heart2._entries_shape(body), None, "heart2 cannot read the seed it is handed")

    def test_no_shard_file_is_no_seed(self):
        self.assertEqual(PS.merge_shards(self.root, os.path.join(self.root, "seed", PS.STORE_NAME), say=_quiet), 2)


class TheWorkflowSeedsEachShardAndSavesFromMainOnly(unittest.TestCase):

    def setUp(self):
        with io.open(WF, encoding="utf-8") as fh:
            self.text = fh.read()
        self.code = "\n".join(l for l in self.text.split("\n") if not l.lstrip().startswith("#"))

    def test_each_shard_restores_the_seed_before_it_proves(self):
        r = self.code.find("uses: actions/cache/restore@v4")
        p = self.code.find("python3 -u tv/heart2.py --prove --push --proof-shard")
        self.assertTrue(0 < r < p, "the seed is not restored before the shard proves")
        step = self.code[r:self.code.find("\n      - ", r)]
        self.assertIn("path: ${{ runner.temp }}/heart2-seed", step)
        self.assertRegex(step, r"restore-keys: \|\n\s+heart2-proofs-k\d+-\n")
        prove = self.code[self.code.rfind("\n      - ", 0, p):p]
        self.assertIn('export HEART2_SHARD_SEED="$RUNNER_TEMP/heart2-seed/.heart2_cache.json"', prove)
        self.assertIn('export HEART2_CACHE_PATH="$D/.heart2_cache.json"', prove, "the shard's own file is no longer fresh")
        self.assertIn("unset HEART2_SHARD_SEED", prove, "a missed restore hands heart2 a path that is not there")

    def test_every_proof_key_in_the_workflow_carries_the_one_declared_format(self):
        """v3896 (REG-3686, the Grok CLI's look on v3895) - the restore check accepted heart2-proofs-k<any digits>- while the
        save was pinned to k3, so a restore under k2 beside a k3 save passed it. Every proof-key prefix the workflow names -
        the seed's restore, the shards' re-run restore, every save - carries ONE format, and it is heart2's declared one."""
        import re as _re
        import heart2 as _H2
        ks = [int(k) for k in _re.findall(r"heart2-proofs-k(\d+)-", self.code)]
        self.assertGreaterEqual(len(ks), 4, "PREMISE: the workflow's proof keys were not found - %r" % ks)
        self.assertEqual(set(ks), {_H2.P3_KEY_FORMAT},
                         "the workflow's proof keys name formats %s, heart2 declares %d - a restore would read another "
                         "format's entries" % (sorted(set(ks)), _H2.P3_KEY_FORMAT))

    def test_the_fan_in_merges_and_saves_on_main_only_under_the_prefix_the_shards_restore(self):
        m = self.code.find('python3 tv/proof_shard.py --merge-shards shards --out "$RUNNER_TEMP/heart2-seed/.heart2_cache.json"')
        s = self.code.find("uses: actions/cache/save@v4")
        self.assertTrue(0 < m < s, "the fan-in does not merge the seed before saving it")
        for at in (m, s):
            head = self.code[self.code.rfind("\n      - ", 0, at):at]
            self.assertIn("github.ref == 'refs/heads/main'", head, "a seed is saved off main, where no other branch can read it")
            # v3864 - and on its own ci/proof-keys branch, which only that branch can restore: a red-then-fixed re-push of one
            # version starts from its red run's proofs. Never any branch: the condition names exactly these two.
            self.assertIn("startsWith(github.ref, 'refs/heads/ci/proof-keys-')", head,
                          "a re-pushed version no longer starts from the proofs its own red run made")
            self.assertIn("(github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/heads/ci/proof-keys-'))", head,
                          "the seed is saved on a branch other than main and the version's own ci/proof-keys branch")
        save = self.code[s:self.code.find("\n      - ", s)]
        self.assertIn("path: ${{ runner.temp }}/heart2-seed", save)
        self.assertIn("key: heart2-proofs-k3-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}", save,
                      "the save key is not under the prefix the shards restore, or is not unique per run")


RED_PROOF = [
    {"why": "REG-2961 - peek never asks the seed, so CI re-proves every law on every run",
     "file": "tv/heart2.py",
     "find": "            if e is None:\n                e = self.seed.get(key)       # REG-2961",
     "replace": "            if False:\n                e = self.seed.get(key)       # REG-2961",
     "matches": 1},
    {"why": "REG-2961 - a proof served from the seed is not written as the shard's own, so the set never brings it home",
     "file": "tv/heart2.py",
     "find": "                if key not in self.entries:                   # REG-2961 - served from the seed: this run's own now\n",
     "replace": "                if False:                   # REG-2961 - served from the seed: this run's own now\n",
     "matches": 1},
    {"why": "REG-2961 - a seed is read on this machine's own push too",
     "file": "tv/heart2.py",
     "find": "    if seed and _SHARD.get(\"spec\"):                  # REG-2961",
     "replace": "    if seed:                  # REG-2961",
     "matches": 1},
    {"why": "REG-2961 - the next seed takes proofs the import would never bank",
     "file": "tv/proof_shard.py",
     "find": "            if not servable(e):          # what the import would bank, never more\n                continue\n            cur = take.get(key)\n",
     "replace": "            cur = take.get(key)\n",
     "matches": 1},
    {"why": "REG-2961 - the older of two proofs under one key wins the seed",
     "file": "tv/proof_shard.py",
     "find": "            if cur is None or e.get(\"provedAt\") > cur.get(\"provedAt\"):\n",
     "replace": "            if cur is None:\n",
     "matches": 1},
    {"why": "REG-2961 - the seed is saved from any branch, where no other branch can restore it",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "      - name: Save the seed (REG-2961 main; v3864 its own ci/proof-keys branch too)\n        if: ${{ always() && (github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/heads/ci/proof-keys-')) }}\n",
     "replace": "      - name: Save the seed (REG-2961 main; v3864 its own ci/proof-keys branch too)\n        if: ${{ always() }}\n",
     "matches": 1},
    {"why": "REG-2961 - the shard never hands heart2 its seed",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "          export HEART2_SHARD_SEED=\"$RUNNER_TEMP/heart2-seed/.heart2_cache.json\"\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3686 - the seed restores another proof-key format than the shards save (k2 beside k3) and the law still passes",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "            heart2-proofs-k3-\n",
     "replace": "            heart2-proofs-k2-\n",
     "matches": 1}
]

if __name__ == "__main__":
    unittest.main()
