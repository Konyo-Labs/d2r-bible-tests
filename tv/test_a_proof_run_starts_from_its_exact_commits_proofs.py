# -*- coding: utf-8 -*-
"""REG-3210 - A PROOF RUN STARTS FROM THE PROOFS ITS EXACT COMMIT ALREADY HAS (Publish takes the exact-sha bank).

MEASURED on v3864 (2026-11-05): ci/proof-keys-v3864 proved commit 9d9485ea6 and published
proofs-9d9485ea61f7482320cdc47a5d0e05f670776e77.tgz to the proof bank at 18:17; Publish began on THE SAME commit nine
minutes later (run 42084305066), and every one of its 22 shards restored only v3863's seed, served 1-2 proofs and re-proved
the rest - 56 min on a commit already proved (shard 6 proved 380 of its 388 again, for 49.5 min). Every PC imports that
bundle; GitHub did not. And a "Re-run failed jobs" shard serves what its run's earlier attempt proved (ci/proof-keys-v3864's
shard 10: 656 proofs, 87 min and cancelled; its re-run served 47 gates whole and took 36 min). Held here:
  * tv/proof_seed.py asks the bank for the bundle of EXACTLY the head sha it is given, unpacks it through the PCs' own
    safe unpack, and merges it with the seed actions/cache restored into ONE read-only store (merge_shards: only
    servable PROVENs); a missing bundle or nothing restored is said and is a cold run, never a failure;
  * served.json names only the proofs PROVEN in shard files whose manifest is this very commit's, from a clean tree;
  * the store's sha256 is what the shards check: every shard reads the same seed and so cuts the same plan;
  * the workflow builds that seed once (job `seed`, from $GITHUB_SHA, after the REG-2961 restore, never failing the run),
    every shard needs it, downloads it into the dir heart2 seeds from and refuses a seed whose digest is not the seed
    job's - and Publish runs this very workflow (job `proof`, gate deploy), so Publish takes the exact-sha bank;
  * (the second eye on v3865) a "Re-run failed jobs" shard restores the cache THIS run's earlier attempt saved and widens
    the seed with it (proof_seed.widen: AFTER the digest check, the plan still the seed job's served.json), so what
    attempt 1 proved is served, never proved again - the recovery that rescued v3864's shard 10;
  * a bundle of this commit that still OWES proofs cut at their bound is bank=partial, never ok (the next round proves
    the rest from it).
heart2 serves a seed entry only under the key THIS checkout's bytes give it (test_ci_reuses_a_proof_only_for_identical_bytes),
so only byte-identical proofs are ever served. Fixtures only - the bank download is replaced; no network. RED_PROOF below.
"""
import hashlib
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
import proof_seed as SEED  # noqa: E402
import proof_shard as PS  # noqa: E402

SHA = "9d9485ea61f7482320cdc47a5d0e05f670776e77"
OTHER = "16cc3872c30b" + "0" * 28


def _e(g, i, v="PROVEN", at=1762000000000):
    return {"verdict": v, "gate": g, "proof": i, "provedAt": at, "tree": "/home/runner/work/x/x"}


def _store(d, entries, head=None, dirty=False):
    os.makedirs(d, exist_ok=True)
    body = {"format": 2, "entries": entries}
    if head:
        own = {}
        for e in entries.values():
            own.setdefault(e["gate"], set()).add(e["proof"])
        body["shard"] = PS.manifest(1, 1, head, dirty, "p", own, None, None, 1762000000000)
    with io.open(os.path.join(d, PS.STORE_NAME), "w", encoding="utf-8") as fh:
        json.dump(body, fh)


class _Tmp(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="seed-law-")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.asked = []

    def bundle(self, sha, shards):
        """A proof-bank bundle for `sha`, packed by the fan-in's own packer. shards: [(entries, head, dirty)]"""
        root = os.path.join(self.d, "pack-" + sha[:6])
        for k, (ent, head, dirty) in enumerate(shards, 1):
            _store(os.path.join(root, "proof-shard-%d" % k), ent, head=head, dirty=dirty)
        out = os.path.join(self.d, "proofs-%s.tgz" % sha)
        self.assertEqual(PS.bank(root, out, say=lambda *a: None), 0)
        return out

    def download(self, have):
        def dl(sha, dest, flavor=""):
            self.asked.append((sha, flavor))
            src = have.get((sha, flavor))
            if not src:
                return "absent", "GitHub has no proof bundle for %s yet" % sha[:9]
            shutil.copyfile(src, dest)
            return "ok", "downloaded"
        return dl

    def build(self, have, restored=None, **kw):
        rdir = os.path.join(self.d, "restored")
        if restored is not None:
            _store(rdir, restored)
        said = []
        rec = SEED.build(SHA, rdir, os.path.join(self.d, "work"), os.path.join(self.d, "out"),
                         download=self.download(have), say=said.append, **kw)
        return rec, "\n".join(said)

    def seed_body(self):
        with io.open(os.path.join(self.d, "out", PS.STORE_NAME), encoding="utf-8") as fh:
            return json.load(fh)

    def served(self):
        with io.open(os.path.join(self.d, "out", SEED.SERVED_NAME), encoding="utf-8") as fh:
            return json.load(fh)


class TheSeedTakesThisCommitsOwnProofs(_Tmp):

    def test_the_exact_commits_bundle_and_the_restored_seed_become_one_store(self):
        b = self.bundle(SHA, [({"k1": _e("ga", 0), "k2": _e("ga", 1)}, SHA, False),
                              ({"k3": _e("gb", 0), "k4": _e("gb", 1, "BLIND")}, SHA, False)])
        rec, said = self.build({(SHA, ""): b}, restored={"k9": _e("gz", 0), "k1": _e("ga", 0, at=1)})
        self.assertEqual(self.asked, [(SHA, "")], "the bank was asked for another commit than the head sha")
        self.assertTrue(rec["seeded"], said)
        self.assertEqual(rec["bank"], "ok")
        body = self.seed_body()
        self.assertEqual(sorted(body["entries"]), ["k1", "k2", "k3", "k9"], "the seed holds what heart2 would never serve, "
                                                                       "or lost the restored seed")
        self.assertEqual(body["entries"]["k1"]["provedAt"], 1762000000000, "the older proof of one key won the seed")
        self.assertNotIn("shard", body, "the seed carries a shard manifest - it is no shard's file")
        self.assertEqual(self.served(), {"sha": SHA, "flavor": "", "served": [["ga", 0], ["ga", 1], ["gb", 0]]})
        with io.open(os.path.join(self.d, "out", PS.STORE_NAME), "rb") as fh:
            self.assertEqual(rec["digest"], hashlib.sha256(fh.read()).hexdigest(), "the digest is not the seed's bytes")

    def test_only_this_commits_clean_shard_files_name_served_proofs(self):
        b = self.bundle(SHA, [({"k1": _e("ga", 0)}, SHA, False), ({"k2": _e("gb", 0)}, OTHER, False),
                              ({"k3": _e("gc", 0)}, SHA, True), ({"k4": _e("gd", 0)}, None, False)])
        rec, said = self.build({(SHA, ""): b})
        self.assertEqual(self.served()["served"], [["ga", 0]], "another commit's or a dirty tree's proofs priced the plan")
        self.assertEqual(rec["served"], 1)

    def test_no_bundle_yet_is_said_and_the_restored_seed_still_seeds(self):
        rec, said = self.build({}, restored={"k9": _e("gz", 0)})
        self.assertTrue(rec["seeded"])
        self.assertEqual(rec["bank"], "absent")
        self.assertIn("ABSENT", said)
        self.assertEqual(self.served()["served"], [])

    def test_nothing_at_all_is_a_cold_run_and_says_so(self):
        rec, said = self.build({})
        self.assertFalse(rec["seeded"])
        self.assertIn("cold run", said)
        self.assertFalse(os.path.exists(os.path.join(self.d, "out", PS.STORE_NAME)))

    def test_a_bundle_the_safe_unpack_refuses_seeds_nothing_from_it(self):
        bad = os.path.join(self.d, "bad.tgz")
        import tarfile
        p = os.path.join(self.d, "evil.txt")
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write("x")
        with tarfile.open(bad, "w:gz") as tf:
            tf.add(p, arcname="proof-shard-1/../../evil.txt")
        rec, said = self.build({(SHA, ""): bad}, restored={"k9": _e("gz", 0)})
        self.assertEqual(rec["bank"], "refused")
        self.assertEqual(sorted(self.seed_body()["entries"]), ["k9"])

    def test_a_set_its_bound_cut_is_partial_never_banked(self):
        root = os.path.join(self.d, "pack-cut")
        _store(os.path.join(root, "proof-shard-1"), {"k1": _e("ga", 0)}, head=SHA)
        p2 = os.path.join(root, "proof-shard-2")
        _store(p2, {"k2": _e("gb", 0)}, head=SHA)
        with io.open(os.path.join(p2, PS.STORE_NAME), encoding="utf-8") as fh:
            body = json.load(fh)
        body["shard"]["owed"] = [["gb", 1, "TIMEOUT", "cut at its bound"], ["gb", 2, "BLIND", "green"]]
        with io.open(os.path.join(p2, PS.STORE_NAME), "w", encoding="utf-8") as fh:
            json.dump(body, fh)
        out = os.path.join(self.d, "cut.tgz")
        self.assertEqual(PS.bank(root, out, say=lambda *a: None), 0)
        rec, said = self.build({(SHA, ""): out})
        self.assertEqual((rec["bank"], rec["cut"]), ("partial", 1), said)
        self.assertIn("PARTIAL", said)
        self.assertEqual(self.served()["served"], [["ga", 0], ["gb", 0]], "a partial set's PROVENs are not served")
        rec2, _s = self.build({(SHA, ""): self.bundle(SHA, [({"k1": _e("ga", 0)}, SHA, False)])})
        self.assertEqual((rec2["bank"], rec2["cut"]), ("ok", 0))
        self.assertIsNone(SEED.cut_in([], SHA), "no shard file read is 0 cut - it is UNKNOWN")

    def test_a_rerun_shard_serves_what_its_earlier_attempt_proved(self):
        seed = os.path.join(self.d, "seed")
        _store(seed, {"k1": _e("ga", 0, at=5)})
        earlier = os.path.join(self.d, "rerun")
        _store(earlier, {"k1": _e("ga", 0, at=9), "k2": _e("gb", 0), "k3": _e("gc", 0, "BLIND")})
        said = []
        got = SEED.widen(os.path.join(seed, PS.STORE_NAME), earlier, os.path.join(self.d, "wide"), say=said.append)
        self.assertEqual(got, os.path.join(self.d, "wide", PS.STORE_NAME), "\n".join(said))
        with io.open(got, encoding="utf-8") as fh:
            ent = json.load(fh)["entries"]
        self.assertEqual(sorted(ent), ["k1", "k2"], "the earlier attempt's proofs are not served, or a BLIND is")
        self.assertEqual(ent["k1"]["provedAt"], 9)
        self.assertFalse(os.path.exists(os.path.join(self.d, "wide", "parts")), "the scratch copies were left behind")
        self.assertIsNone(SEED.widen(os.path.join(seed, PS.STORE_NAME), "", os.path.join(self.d, "w2"), say=said.append))
        cold = SEED.widen("", os.path.join(earlier, PS.STORE_NAME), os.path.join(self.d, "w3"), say=said.append)
        self.assertTrue(cold and os.path.isfile(cold), "a cold run's re-run serves nothing its first attempt proved")

    def test_the_outputs_the_shards_read(self):
        out = os.path.join(self.d, "gh_output")
        SEED.write_outputs({"seeded": True, "digest": "ab" * 32, "bank": "ok", "entries": 3, "served": 2}, out)
        with io.open(out, encoding="utf-8") as fh:
            got = fh.read()
        for line in ("seeded=true\n", "digest=" + "ab" * 32 + "\n", "bank=ok\n", "served=2\n"):
            self.assertIn(line, got)


def _code(text):
    return "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("#"))


def _job(text, name):
    m = re.search(r"\n  %s:\n(.*?)(?=\n  [A-Za-z][\w-]*:\n|\Z)" % re.escape(name), "\n" + text.split("\njobs:\n", 1)[-1],
                  re.S)
    return m.group(1) if m else ""


class TheWorkflowSeedsEveryShardFromIt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(os.path.join(ROOT, ".github", "workflows", "proof-keys-shards.yml"), encoding="utf-8") as fh:
            cls.wf = _code(fh.read())
        with io.open(os.path.join(ROOT, ".github", "workflows", "publish.yml"), encoding="utf-8") as fh:
            cls.pub = _code(fh.read())

    def test_the_seed_job_builds_one_seed_from_the_head_sha(self):
        seed = _job(self.wf, "seed")
        self.assertTrue(seed, "the seed job is gone")
        r = seed.index("uses: actions/cache/restore@v4")
        b = seed.index("python3 tv/proof_seed.py")
        self.assertLess(r, b, "the seed is built before the REG-2961 restore")
        step = seed[seed.rfind("\n      - ", 0, b):seed.find("\n      - ", b)]
        self.assertIn('--sha "$GITHUB_SHA"', step, "the seed is built for another commit than the one this run proves")
        self.assertIn('--restored "$RUNNER_TEMP/heart2-seed"', step)
        self.assertIn("continue-on-error: true", step, "a seed that cannot be built fails the run")
        self.assertIn("name: proof-seed\n", seed)
        self.assertIn("digest: ${{ steps.seed.outputs.digest }}", seed)

    def test_every_shard_needs_it_downloads_it_and_checks_its_digest(self):
        shard = _job(self.wf, "shard")
        # v3890 (REG-3505) - the budget job is gone: the shards wait on their seed alone
        self.assertIn("    needs: [seed]\n", shard, "a shard starts before the seed is built")
        d = shard.index("actions/download-artifact")
        step = shard[shard.rfind("\n      - ", 0, d):shard.find("\n      - ", d)]
        self.assertIn("name: proof-seed\n", step)
        self.assertIn("path: ${{ runner.temp }}/heart2-seed", step, "the seed lands where heart2 does not read it")
        self.assertIn("if: ${{ needs.seed.outputs.seeded == 'true' }}", step)
        prove = shard[shard.index("- name: Prove this shard"):]
        self.assertLess(d, shard.index("- name: Prove this shard"))
        self.assertIn('[ "$(sha256sum "$HEART2_SHARD_SEED" | cut -d\' \' -f1)" != "${{ needs.seed.outputs.digest }}" ]',
                      prove)
        chk = prove[prove.index("sha256sum"):]
        self.assertIn("exit 3; fi", chk[:chk.index("\n", chk.index("REG-3210")) + 1],
                      "a shard reading another seed than its siblings still proves")

    def test_a_rerun_shard_restores_its_runs_earlier_attempt_and_widens_after_the_digest(self):
        shard = _job(self.wf, "shard")
        r = shard.index("key: heart2-proofs-k3-${{ github.sha }}-${{ github.run_id }}-rerun\n")
        step = shard[shard.rfind("\n      - ", 0, r):shard.find("\n      - ", r)]
        self.assertIn("uses: actions/cache/restore@v4", step)
        self.assertRegex(step, r"\n          restore-keys: heart2-proofs-k3-\$\{\{ github\.sha \}\}-\$\{\{ github\.run_id \}\}-(\n|$)",
                         "a re-run restores another run's or another commit's cache, or none")
        self.assertIn("path: ${{ runner.temp }}/heart2-seed/rerun", step, "the re-run seed lands outside the seed dir")
        self.assertIn("continue-on-error: true", step)
        fan = _job(self.wf, "fan-in")
        self.assertIn("key: heart2-proofs-k3-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}", fan,
                      "the fan-in no longer saves the attempt the re-run restores")
        # REG-3280 - THE JOINT, NOT THE HALVES. actions/cache serves an entry only to a restore with the SAME path, so the
        # fan-in must save one under the exact path the shard restores, and with a key the restore's prefix matches.
        # v3872: the key was there, the paths differed (heart2-seed vs heart2-seed/rerun), and no re-run was ever served.
        rpath = re.search(r"\n          path: (.+)\n", step).group(1)
        saves = [b for b in fan.split("\n      - ")[1:] if "uses: actions/cache/save@v4" in b]
        joined = [b for b in saves if ("\n          path: %s\n" % rpath) in b + "\n"]
        self.assertEqual(len(joined), 1, "no fan-in save is under the re-run's restore path %r - the re-run serves nothing"
                         % rpath)
        key = re.search(r"\n          key: (.+)", joined[0]).group(1)
        self.assertTrue(key.startswith("heart2-proofs-k3-${{ github.sha }}-${{ github.run_id }}-"),
                        "the re-run's restore-keys prefix never matches the saved key %r" % key)
        cp = fan.index('--merge-shards shards --out "$RUNNER_TEMP/heart2-seed/rerun/.heart2_cache.json"')
        self.assertLess(fan.index('--merge-shards shards --out "$RUNNER_TEMP/heart2-seed/.heart2_cache.json"'), cp)
        self.assertLess(cp, fan.index(joined[0]), "the re-run copy is saved before it is written")
        prove = shard[shard.index("- name: Prove this shard"):]
        w = prove.index("python3 tv/proof_seed.py --widen")
        self.assertLess(prove.index("sha256sum"), w, "the seed is widened before its digest is checked")
        # bounded by the command's own end (the `; then` closing its `if`), never a 200-character guess
        self.assertIn('--with "$RUNNER_TEMP/heart2-seed/rerun"', prove[w:prove.index("; then", w)])
        self.assertIn('export HEART2_SHARD_SEED="$RUNNER_TEMP/heart2-seed/wide/.heart2_cache.json"; fi', prove[w:])
        self.assertLess(w, prove.index("python3 -u tv/heart2.py --prove --push"))
        self.assertNotIn("HEART2_SHARD_SERVED=", prove[w:], "a re-run shard plans from another served list")

    def test_publish_runs_this_workflow(self):
        proof = _job(self.pub, "proof")
        self.assertIn("uses: ./.github/workflows/proof-keys-shards.yml", proof)
        self.assertIn("gate: deploy", proof)


RED_PROOF = [
    {"why": "REG-3280 - the fan-in saves the re-run's proofs under another path than the re-run restores (v3872)",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "          path: ${{ runner.temp }}/heart2-seed/rerun\n          key: heart2-proofs-k3-${{ github.sha }}-${{ github.run_id }}-rerun-${{ github.run_attempt }}\n",
     "replace": "          path: ${{ runner.temp }}/heart2-seed\n          key: heart2-proofs-k3-${{ github.sha }}-${{ github.run_id }}-rerun-${{ github.run_attempt }}\n",
     "matches": 1},
    {"why": "REG-3210 - the bank is asked for another commit than the head sha (v3864: Publish never took 9d9485ea6's)",
     "file": "tv/proof_seed.py",
     "find": "        rec[\"bank\"], exact = _bundle(sha, flavor, work, \"exact\", download, say)\n",
     "replace": "        rec[\"bank\"], exact = _bundle(\"0\" * 40, flavor, work, \"exact\", download, say)\n",
     "matches": 1},
    {"why": "REG-3210 - another commit's or a dirty tree's proofs are named as this commit's",
     "file": "tv/proof_seed.py",
     "find": "        if not isinstance(m, dict) or m.get(\"head\") != sha or m.get(\"dirty\") is not False:\n",
     "replace": "        if not isinstance(m, dict):\n",
     "matches": 1},
    {"why": "REG-3210 - the restored seed is dropped from the merge",
     "file": "tv/proof_seed.py",
     "find": "        if r and os.path.isfile(r):\n            stores.append(r)\n",
     "replace": "        if False:\n            stores.append(r)\n",
     "matches": 1},
    {"why": "REG-3210 - the shards check no digest, so two shards can cut two plans from two seeds",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "its plan would differ from its siblings'\"; exit 3; fi\n",
     "replace": "its plan would differ from its siblings'\"; fi\n",
     "matches": 1},
    {"why": "REG-3210 - the seed job builds the seed for another commit",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "python3 tv/proof_seed.py --sha \"$GITHUB_SHA\"",
     "replace": "python3 tv/proof_seed.py --sha \"$(git rev-parse HEAD~1)\"",
     "matches": 1},
    {"why": "REG-3210 - the shards start before the seed exists",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "    needs: [seed]\n",
     "replace": "    needs: []\n",
     "matches": 1},
    {"why": "REG-3210 (second eye) - a re-run shard never restores what its run's earlier attempt proved (v3864 shard 10)",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "          restore-keys: heart2-proofs-k3-${{ github.sha }}-${{ github.run_id }}-\n",
     "replace": "          restore-keys: heart2-proofs-k3-${{ github.sha }}-none-\n",
     "matches": 1},
    {"why": "REG-3210 (second eye) - the widened seed is built and never handed to heart2",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "            export HEART2_SHARD_SEED=\"$RUNNER_TEMP/heart2-seed/wide/.heart2_cache.json\"; fi\n",
     "replace": "            true; fi\n",
     "matches": 1},
    {"why": "REG-3210 (second eye) - the earlier attempt's proofs are left out of the widened seed",
     "file": "tv/proof_seed.py",
     "find": "        have = [p for p in (seed, extra) if p and os.path.isfile(p)]\n",
     "replace": "        have = [p for p in (seed,) if p and os.path.isfile(p)]\n",
     "matches": 1},
    {"why": "REG-3214 (second eye) - a set its bound cut reads banked, so no round ever proves the rest",
     "file": "tv/proof_seed.py",
     "find": "            if _c:                          # REG-3214 - a set its bound cut is partial",
     "replace": "            if False:                          # REG-3214 - a set its bound cut is partial",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
