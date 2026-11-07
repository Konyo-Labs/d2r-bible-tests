# -*- coding: utf-8 -*-
"""REG-2586 — A SHARD'S PROVENS COME HOME ALL OR NOTHING, AND EACH KEEPS THE TREE IT WAS PROVED IN.

⚠ WHAT IT IS FOR. `heart2 --prove --push --proof-shard K/N` (REG-2585, test_a_proof_shard_covers_every_proof_once)
banks each CI runner's PROVENs into a file of its own. `heart2 --import-shards FILE...` merges those files into this
machine's verdict cache, so the next push serves them instead of proving them again.

⚠ THE DEFECTS THIS GUARDS, each one a verdict served that nobody earned here:
  · a PARTIAL set is imported (a shard died, its runner timed out) - the push then reads "all banked" for proofs that
    were never run, and nothing says which;
  · a shard of ANOTHER commit is imported - its keys still hash bytes, but a set cut from another plan is not this
    push's set; a shard from a tree that differed from its HEAD (dirty) banked bytes no commit holds;
  · an unfinished shard, two shards with one number, shards that disagree on N or on the plan;
  · an ELSEWHERE, a BLIND, an UNPROVABLE, an undated or a fact-bound entry is banked - peek() would refuse to serve it,
    so the import must refuse to bank it;
  · an entry a shard was never assigned is taken - a shard that proved outside its plan is not trusted with the rest;
  · the import rewrites `tree` to this checkout's - then #242's "every gate's clean run in THIS tree" is skipped and a
    gate whose clean run only ever happened on a Linux runner reads as checked here;
  · the import overwrites what this machine already serves, or writes past the store's lock (a running push's flush
    and the import racing on one file).
Every store here is a temp file; HEAD is a stand-in. [[feedback-fixtures-never-touch-live-data]] RED_PROOF below.
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
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402  (it prints non-ASCII)
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import heart2        # noqa: E402
import proof_shard   # noqa: E402

RED_PROOF = [
    {
        "why": "REG-2586 - a stopped shard's proofs that were never banked are not counted: it reads as fully imported",
        "file": "heart2.py",
        "find": "    for _k in sorted(_stops):\n",
        "replace": "    for _k in []:\n",
        "matches": 1,
    },
    {
        "why": "REG-2586 - the count calls a stopped shard's proofs banked though the import took none of them",
        "file": "proof_shard.py",
        "find": "                  if take.get(key) is e)\n",
        "replace": "                  )\n",
        "matches": 1,
    },
    {
        "why": "REG-2586 - a partial set is imported: a dead shard's proofs read as banked though nothing ran them",
        "file": "proof_shard.py",
        "find": "    if missing:\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2586 - a shard of another commit is imported into this checkout's cache",
        "file": "proof_shard.py",
        "find": "        if not head or m.get(\"head\") != head:\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2586 - a shard proved from a tree that differed from its HEAD is imported",
        "file": "proof_shard.py",
        "find": "        if m.get(\"dirty\") is not False:\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2586 - a shard that never finished is imported as if it had",
        "file": "proof_shard.py",
        "find": "        if m.get(\"finished\") is not True:\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2586 - shards cut from two different plans are imported as one set",
        "file": "proof_shard.py",
        "find": "    if len(plans) != 1:\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2586 - an ELSEWHERE, BLIND or undated entry is banked though peek() would never serve it",
        "file": "proof_shard.py",
        "find": "            if not servable(e):\n",
        "replace": "            if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2586 - a shard that holds a proof its plan never gave it is still trusted with the rest",
        "file": "proof_shard.py",
        "find": "            if (str(e.get(\"gate\")), e.get(\"proof\")) not in assigned:\n",
        "replace": "            if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2586 - the import rewrites each entry's tree, so #242 skips the clean run this tree never had",
        "file": "proof_shard.py",
        "find": "            take[key] = e                   # KEPT",
        "replace": "            take[key] = dict(e, tree=\"REWRITTEN\")  # KEPT",
        "matches": 1,
    },
    {
        "why": "REG-2586 - an in-plan proof is banked under a key this checkout's bytes never give it (any law's key)",
        "file": "proof_shard.py",
        "find": "            if keyer is not None and keyer(str(e.get(\"gate\")), e.get(\"proof\")) != key:\n",
        "replace": "            if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2596 - a key these bytes do not give is banked anyway when the import drops instead of refusing",
        "file": "proof_shard.py",
        "find": "                    dropped.append((k, str(e.get(\"gate\")), e.get(\"proof\")))\n                    continue\n",
        "replace": "                    dropped.append((k, str(e.get(\"gate\")), e.get(\"proof\")))\n",
        "matches": 1,
    },
    {
        "why": "REG-2596 - the import drops entries silently: nobody learns which laws' keys differ",
        "file": "heart2.py",
        "find": "    if _dropped:\n        _dg = {}\n",
        "replace": "    if False:\n        _dg = {}\n",
        "matches": 1,
    },
    {
        "why": "REG-2596 - the import refuses the whole set over one law's differing key",
        "file": "heart2.py",
        "find": "keyer=_shard_keyer(target), dropped=_dropped,",
        "replace": "keyer=_shard_keyer(target), dropped=None,",
        "matches": 1,
    },
    {
        "why": "REG-2586 - two shards that both claim one proof are imported, the later entry silently wins",
        "file": "proof_shard.py",
        "find": "            if row in owner:\n",
        "replace": "            if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2586 - an import into a checkout whose tracked files differ from HEAD keys proofs by bytes no commit has",
        "file": "heart2.py",
        "find": "        if not ok_d or dirty.strip():\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2586 - an import overwrites an entry this machine already serves",
        "file": "proof_shard.py",
        "find": "        if servable(out.get(key)):\n            continue\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-2586 - the import writes past the store's lock and drops what the store held",
        "file": "heart2.py",
        "find": "    w_ok, w_why = _StoreFile(target, say).commit(merge)",
        "replace": "    w_ok, w_why = (io.open(target, \"w\", encoding=\"utf-8\").write(json.dumps(merge({}))) > 0), None",
        "matches": 1,
    },
]

HEAD = "1234567890abcdef1234567890abcdef12345678"
CI_TREE = "/home/runner/work/repo/repo"


def _e(gate, proof, verdict="PROVEN", at=1761200000000, **extra):
    e = {"verdict": verdict, "gate": gate, "proof": proof, "why": "w", "tree": CI_TREE}
    if at is not None:
        e["provedAt"] = at
    e.update(extra)
    return e


class _Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="shardimport-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.target = os.path.join(self.tmp, "home", os.path.basename(heart2.CACHE))
        os.makedirs(os.path.dirname(self.target))
        self.said = []
        self.dirty = ""
        p = mock.patch.object(heart2, "_git", side_effect=lambda *a: (True, HEAD + "\n") if a[0] == "rev-parse"
                              else (True, self.dirty))
        p.start()
        self.addCleanup(p.stop)
        self.keys = {}                  # (gate, proof) -> the key this checkout's bytes give it (a stand-in keyer)
        p = mock.patch.object(heart2, "_shard_keyer", return_value=lambda g, i: self.keys.get((g, i)))
        p.start()
        self.addCleanup(p.stop)

    def shard(self, k, n, entries, assigned=None, **m):
        d = os.path.join(self.tmp, "shard-%d" % k)
        if not os.path.isdir(d):
            os.makedirs(d)
        path = os.path.join(d, os.path.basename(heart2.CACHE))
        for key, e in entries.items():
            self.keys.setdefault((e["gate"], e["proof"]), key)
        own = {}
        for g, i in (assigned if assigned is not None else [(e["gate"], e["proof"]) for e in entries.values()]):
            own.setdefault(g, set()).add(i)
        man = proof_shard.manifest(k, n, HEAD, False, "plan-1", own, None, [], 1761200000000)
        man.update(m)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"format": 2, "entries": entries, "shard": man}))
        return path

    def run_import(self, paths):
        return heart2.import_shards(paths, say=self.said.append, target=self.target)

    def home(self):
        if not os.path.exists(self.target):
            return None
        with io.open(self.target, encoding="utf-8") as fh:
            return json.load(fh)

    def two(self, **m2):
        a = self.shard(1, 2, {"k1": _e("g1", 0), "k2": _e("g1", 1)})
        b = self.shard(2, 2, {"k3": _e("g2", 0)}, **m2)
        return [a, b]


class TheMergeNeverDisplacesALocalProof(unittest.TestCase):
    """REG-3352 - import_shards no longer keys an entry this PC already serves (test_an_import_keeps_what_it_has_keyed),
    so a served key rarely reaches the merge from it; the merge's own rule still guards a key that became served while an
    import ran, and every other import path. Asked of the merge itself."""

    def test_a_served_key_is_kept_as_it_is(self):
        mine = dict(_e("g1", 0), tree="here", provedAt=1761100000000)
        out, added = proof_shard.merge_into({"k1": mine}, {"k1": _e("g1", 0), "k2": _e("g2", 0)})
        self.assertIs(out["k1"], mine, "the import displaced a proof this machine already serves")
        self.assertEqual(added, 1)
        self.assertIn("k2", out)


class AWholeSetComesHome(_Fixture):
    def test_every_proven_is_banked_with_the_tree_it_was_proved_in(self):
        self.assertEqual(self.run_import(self.two()), 0, self.said)
        ent = self.home()["entries"]
        self.assertEqual(sorted(ent), ["k1", "k2", "k3"])
        for k, e in ent.items():
            self.assertEqual(e["tree"], CI_TREE, "%s: the import rewrote the tree it was proved in" % k)
            self.assertNotEqual(e["tree"], heart2.TREE_ID)

    def test_a_stopped_shard_banks_what_it_proved_and_says_it_stopped(self):
        a = self.shard(1, 2, {"k1": _e("g1", 0)})
        b = self.shard(2, 2, {"k3": _e("g2", 0)}, stopped=["g2", 1, "BLIND", "stayed green"])
        self.assertEqual(self.run_import([a, b]), 0, self.said)
        self.assertEqual(sorted(self.home()["entries"]), ["k1", "k3"])
        self.assertIn("1 shard(s) STOPPED", " ".join(self.said))

    def test_each_stopped_shard_says_how_many_of_its_proofs_were_not_banked(self):
        """REG-2586 - a stopped shard is still imported, and each one names what it never banked: assigned 4, banked 1
        (one more is BLIND, two never ran) -> 3 not banked; a shard that ran to the end says nothing"""
        a = self.shard(1, 2, {"k1": _e("g1", 0)}, assigned=[("g1", 0), ("g1", 1)])
        blind = dict(_e("g2", 1), verdict=heart2.BLIND)
        b = self.shard(2, 2, {"k3": _e("g2", 0), "k4": blind},
                       assigned=[("g2", 0), ("g2", 1), ("g2", 2), ("g2", 3)], stopped=["g2", 1, "BLIND", "stayed green"])
        self.assertEqual(self.run_import([a, b]), 0, self.said)
        lines = [ln for ln in self.said if "shard 2/2 STOPPED at g2[1] BLIND" in ln]
        self.assertEqual(len(lines), 1, "the stopped shard's own line is missing: %s" % self.said)
        self.assertIn("3 of its 4 assigned proof(s) NOT banked", lines[0])
        self.assertFalse(any("shard 1/2 STOPPED" in ln for ln in self.said), "a shard that finished was called stopped")

    def test_what_peek_would_refuse_is_never_banked(self):
        a = self.shard(1, 1, {"ok": _e("g", 0), "else": _e("g", 1, verdict="ELSEWHERE"),
                              "blind": _e("g", 2, verdict="BLIND"), "unp": _e("g", 3, verdict="UNPROVABLE"),
                              "undated": _e("g", 4, at=None), "traced": _e("g", 5, kind="traced"),
                              "facts": _e("g", 6, factsRef="x")})
        self.assertEqual(self.run_import([a]), 0, self.said)
        self.assertEqual(sorted(self.home()["entries"]), ["ok"])

    def test_what_this_machine_already_serves_is_kept_and_its_other_keys_stay(self):
        mine = {"k1": dict(_e("g1", 0, at=1700000000000), tree="/here"),
                "own": dict(_e("x", 0), tree="/here"), "stale": _e("g2", 0, verdict="UNPROVABLE")}
        with io.open(self.target, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"format": 2, "entries": mine, "extra": 7}))
        paths = [self.shard(1, 2, {"k1": _e("g1", 0), "k2": _e("g1", 1)}),
                 self.shard(2, 2, {"stale": _e("g2", 0)})]
        self.assertEqual(self.run_import(paths), 0, self.said)
        body = self.home()
        ent = body["entries"]
        self.assertEqual(ent["k1"]["tree"], "/here", "an entry this machine serves was overwritten")
        self.assertIn("own", ent)
        self.assertEqual(ent["stale"]["verdict"], "PROVEN", "a stale local non-PROVEN was not replaced")
        self.assertEqual(body.get("extra"), 7)

    def test_the_write_goes_through_the_stores_lock(self):
        calls = []
        real = heart2._StoreFile.commit

        def spy(self_, merge):
            calls.append(self_.path)
            return real(self_, merge)
        with mock.patch.object(heart2._StoreFile, "commit", spy):
            self.assertEqual(self.run_import(self.two()), 0, self.said)
        self.assertEqual(calls, [self.target])


class APartOrForeignSetIsRefused(_Fixture):
    def assertRefused(self, paths, word):
        before = self.home()
        self.assertEqual(self.run_import(paths), 2, self.said)
        self.assertEqual(self.home(), before, "a refused import wrote")
        self.assertIn(word, " ".join(str(x) for x in self.said))

    def test_a_missing_shard(self):
        self.assertRefused(self.two()[:1], "missing")

    def test_a_shard_of_another_head(self):
        self.assertRefused(self.two(head="f" * 40), "HEAD")

    def test_a_dirty_shard(self):
        self.assertRefused(self.two(dirty=True), "differed")

    def test_a_shard_that_never_finished(self):
        self.assertRefused(self.two(finished=False), "never finished")

    def test_shards_of_two_plans(self):
        self.assertRefused(self.two(plan="plan-2"), "plans")

    def test_shards_that_disagree_on_n(self):
        a = self.shard(1, 2, {"k1": _e("g1", 0)})
        b = self.shard(2, 3, {"k3": _e("g2", 0)})
        self.assertRefused([a, b], "disagree")

    def test_one_shard_given_twice(self):
        a = self.shard(1, 1, {"k1": _e("g1", 0)})
        self.assertRefused([a, a], "twice")

    def test_a_file_with_no_manifest(self):
        p = os.path.join(self.tmp, os.path.basename(heart2.CACHE))
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"format": 2, "entries": {"k": _e("g", 0)}}))
        self.assertRefused([p], "manifest")

    def test_an_entry_outside_its_plan(self):
        a = self.shard(1, 1, {"k1": _e("g1", 0), "k9": _e("g9", 4)}, assigned=[("g1", 0)])
        self.assertRefused([a], "never gave")

    def test_an_entry_filed_under_a_key_these_bytes_do_not_give_it_is_dropped_and_named(self):
        """REG-2596 - the entry is never banked, the rest of the set is, and the line names the law and the proof"""
        paths = self.two()
        self.keys[("g1", 1)] = "the-key-this-tree-gives"
        self.assertEqual(self.run_import(paths), 0, self.said)
        self.assertEqual(sorted(self.home()["entries"]), ["k1", "k3"])
        text = " ".join(self.said)
        self.assertIn("REG-2596 1 PROVEN entr(ies) in 1 law(s) DROPPED", text)
        self.assertIn("g1 [1]", text)

    def test_an_unkeyable_entry_is_dropped_too(self):
        paths = self.two()
        self.keys[("g2", 0)] = None
        self.assertEqual(self.run_import(paths), 0, self.said)
        self.assertEqual(sorted(self.home()["entries"]), ["k1", "k2"])

    def test_without_a_dropped_list_select_still_refuses(self):
        a = self.shard(1, 1, {"k1": _e("g1", 0)})
        with io.open(a, encoding="utf-8") as fh:
            body = json.load(fh)
        ok, why, shards = proof_shard.check_shards([("s1", body, None)], HEAD)
        self.assertTrue(ok, why)
        ok, why, take, _sk = proof_shard.select(shards, keyer=lambda g, i: "other")
        self.assertFalse(ok)
        self.assertIn("do not give it", why)
        got = []
        ok, why, take, _sk = proof_shard.select(shards, keyer=lambda g, i: "other", dropped=got)
        self.assertTrue(ok, why)
        self.assertEqual((take, got), ({}, [(1, "g1", 0)]))

    def test_one_proof_assigned_to_two_shards(self):
        a = self.shard(1, 2, {"k1": _e("g1", 0)})
        b = self.shard(2, 2, {"k3": _e("g2", 0)}, assigned=[("g2", 0), ("g1", 0)])
        self.assertRefused([a, b], "assigned to shards")

    def test_a_shard_number_that_is_not_a_whole_number(self):
        a = self.shard(1, 2, {"k1": _e("g1", 0)})
        b = self.shard(2, 2, {"k3": _e("g2", 0)})
        with io.open(b, encoding="utf-8") as fh:
            body = json.load(fh)
        body["shard"]["k"] = 2.0
        with io.open(b, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(body))
        self.assertRefused([a, b], "readable shard number")

    def test_into_a_checkout_whose_files_differ_from_head(self):
        paths = self.two()
        self.dirty = " M tv/heart2.py\n"
        self.assertRefused(paths, "differ from its HEAD")

    def test_a_head_nobody_can_read(self):
        with mock.patch.object(heart2, "_git", return_value=(False, "")):
            self.assertRefused(self.two(), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
