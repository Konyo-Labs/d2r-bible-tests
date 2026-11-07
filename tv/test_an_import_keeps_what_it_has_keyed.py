# -*- coding: utf-8 -*-
"""REG-3352 - AN IMPORT KEYS ONLY WHAT THIS PC DOES NOT SERVE YET, AND WRITES EACH BATCH BEFORE THE NEXT.

His question, 11-07 ~10:00 IST: "not logical that the alt is on 68 proof only when like 8 hours ago we were at 95 or
something... how is it this slow??? its like not finishing or stale?". MEASURED on the ALT (tv/.proof_release.json,
v3876 9c759b54a): the first win32 import landed a PARTIAL set (2,179 proofs cut on GitHub); the re-ask for the completed
set keyed all ~9,000 proofs again - most already served here - ran 17,673 s against proof_release's 5,400 s bound, was
killed ("heart2 --import-shards could not run (TimeoutExpired)") and kept NOTHING, because the import wrote only at the
very end. Meanwhile the PC proved the owed laws itself, two or three at a time.

  * the WHOLE set's shape is still checked first: a stray entry or a proof index that names no proof refuses it all,
    and nothing is written (REG-2586's rule stands);
  * a key this PC already serves is not keyed again - merge_into keeps a served key as it is, so keying it could only
    cost - and it still counts as banked for its shard;
  * the rest is keyed and WRITTEN a batch at a time (a law never split), so a killed run keeps every batch it finished
    and the next run resumes past them; the shut locks' guards go first (#103-C) when it is this PC's own store.

Every store here is a temp file; HEAD is a stand-in. [[feedback-fixtures-never-touch-live-data]] RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
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
import proof_release  # noqa: E402
import proof_shard   # noqa: E402

HEAD = "fedcba0987654321fedcba0987654321fedcba09"
CI_TREE = "/home/runner/work/repo/repo"


def _e(gate, proof, at=1761200000000):
    return {"verdict": "PROVEN", "gate": gate, "proof": proof, "why": "w", "tree": CI_TREE, "provedAt": at}


class _Fixture(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="importresume-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.target = os.path.join(self.tmp, "home", os.path.basename(heart2.CACHE))
        os.makedirs(os.path.dirname(self.target))
        self.said = []
        p = mock.patch.object(heart2, "_git", side_effect=lambda *a: (True, HEAD + "\n") if a[0] == "rev-parse"
                              else (True, ""))
        p.start()
        self.addCleanup(p.stop)
        self.keys, self.asked = {}, []

        def keyer(g, i):
            self.asked.append((g, i))
            return self.keys.get((g, i))
        p = mock.patch.object(heart2, "_shard_keyer", return_value=keyer)
        p.start()
        self.addCleanup(p.stop)

    def shard(self, k, n, entries, assigned=None):
        d = os.path.join(self.tmp, "shard-%d" % k)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, os.path.basename(heart2.CACHE))
        for key, e in entries.items():
            self.keys.setdefault((e["gate"], e["proof"]), key)
        own = {}
        for g, i in (assigned if assigned is not None else [(e["gate"], e["proof"]) for e in entries.values()]):
            own.setdefault(g, set()).add(i)
        man = proof_shard.manifest(k, n, HEAD, False, "plan-r", own, None, [], 1761200000000)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"format": 2, "entries": entries, "shard": man}))
        return path

    def seed_home(self, entries):
        with io.open(self.target, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"format": 2, "entries": entries}))

    def home(self):
        if not os.path.exists(self.target):
            return {}
        with io.open(self.target, encoding="utf-8") as fh:
            return json.load(fh).get("entries") or {}

    def run_import(self, paths):
        return heart2.import_shards(paths, say=self.said.append, target=self.target)

    def three_laws(self):
        a = self.shard(1, 2, {"a0": _e("law_a", 0), "a1": _e("law_a", 1), "b0": _e("law_b", 0)})
        b = self.shard(2, 2, {"c0": _e("law_c", 0), "c1": _e("law_c", 1)})
        return [a, b]


class WhatIsServedIsNotKeyedAgain(_Fixture):

    def test_a_re_ask_keys_only_the_entries_this_pc_does_not_serve(self):
        """* THE POINT: the first, partial import already banked law_a and law_b; the re-ask keys law_c alone"""
        paths = self.three_laws()
        self.seed_home({"a0": dict(_e("law_a", 0), tree="here"), "a1": _e("law_a", 1), "b0": _e("law_b", 0)})
        self.assertEqual(self.run_import(paths), 0, self.said)
        self.assertEqual(sorted(set(g for g, _i in self.asked)), ["law_c"],
                         "the import keyed proofs this PC already serves: %s" % self.asked)
        self.assertEqual(sorted(self.home()), ["a0", "a1", "b0", "c0", "c1"])
        self.assertEqual(self.home()["a0"]["tree"], "here", "a served entry was replaced by the import")
        self.assertIn("3 entr(ies) this PC already served were not keyed again", " ".join(self.said))

    def test_a_served_entry_still_counts_as_banked_for_its_shard(self):
        a = self.shard(1, 1, {"a0": _e("law_a", 0)}, assigned=[("law_a", 0), ("law_a", 1)])
        with io.open(a, encoding="utf-8") as fh:
            body = json.load(fh)
        body["shard"]["stopped"] = ["law_a", 1, "BLIND", "stayed green"]
        with io.open(a, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(body))
        self.seed_home({"a0": _e("law_a", 0)})
        self.assertEqual(self.run_import([a]), 0, self.said)
        line = [ln for ln in self.said if "STOPPED at law_a[1]" in ln]
        self.assertTrue(line and "1 of its 2 assigned proof(s) NOT banked" in line[0], self.said)

    def test_an_empty_home_keys_everything_as_before(self):
        self.assertEqual(self.run_import(self.three_laws()), 0, self.said)
        self.assertEqual(len(self.asked), 5, self.asked)
        self.assertEqual(sorted(self.home()), ["a0", "a1", "b0", "c0", "c1"])


class EachBatchIsWrittenBeforeTheNext(_Fixture):

    def setUp(self):
        super(EachBatchIsWrittenBeforeTheNext, self).setUp()
        p = mock.patch.object(heart2, "IMPORT_BATCH_PROOFS", 2)
        p.start()
        self.addCleanup(p.stop)

    def test_a_run_killed_in_its_second_batch_keeps_the_first(self):
        """* THE POINT: the second batch's write fails (a kill, a full disk) - the first batch is already in the store"""
        real, calls = heart2._import_write, []

        def write(target, take, say, out):
            calls.append(sorted(take))
            if len(calls) == 2:
                return False, "fixture: the run was killed"
            return real(target, take, say, out)
        with mock.patch.object(heart2, "_import_write", write):
            self.assertEqual(self.run_import(self.three_laws()), 2, self.said)
        self.assertEqual(len(calls), 2, calls)
        self.assertEqual(sorted(self.home()), calls[0], "the batch written before the kill was not kept")
        self.assertIn("1 batch(es) were written before it", " ".join(self.said))

    def test_the_next_run_resumes_past_what_was_written(self):
        real, n = heart2._import_write, []

        def write(target, take, say, out):
            n.append(1)
            if len(n) == 2:
                return False, "fixture: the run was killed"
            return real(target, take, say, out)
        paths = self.three_laws()
        with mock.patch.object(heart2, "_import_write", write):
            self.run_import(paths)
        first = sorted(self.home())
        del self.asked[:]
        self.assertEqual(self.run_import(paths), 0, self.said)
        keyed = set("%s%d" % (g[-1], i) for g, i in self.asked)
        self.assertFalse(keyed & set(first), "the resumed run keyed the batch it had already written: %s" % keyed)
        self.assertEqual(sorted(self.home()), ["a0", "a1", "b0", "c0", "c1"])

    def test_a_law_is_never_split_across_batches(self):
        batches = heart2._import_batches([(1, {"a0": _e("law_a", 0), "a1": _e("law_a", 1), "a2": _e("law_a", 2),
                                                "b0": _e("law_b", 0)}, set())], size=2)
        laws = [sorted(set(e["gate"] for _k, ent, _a in b for e in ent.values())) for b in batches]
        self.assertEqual(laws, [["law_a"], ["law_b"]], "a law was split, or two laws over the size shared a batch")

    def test_the_shut_locks_guards_come_first(self):
        batches = heart2._import_batches([(1, {"a0": _e("law_a", 0), "z0": _e("law_z", 0), "m0": _e("law_m", 0)},
                                           set())], rank={"law_z": 0, "law_m": 1}, size=1)
        order = [next(iter(ent.values()))["gate"] for b in batches for _k, ent, _a in b if ent]
        self.assertEqual(order, ["law_z", "law_m", "law_a"], order)

    def test_a_fixture_store_is_never_ranked_against_this_pcs_census(self):
        asked = []
        with mock.patch("self_arming.owed_guard_rank", lambda: asked.append(1) or {"rank": {"law_a": 0}}):
            self.assertEqual(heart2._import_order(self.target), {})
        self.assertEqual(asked, [], "a fixture store was ranked against this PC's census")


class TheWholeSetIsStillCheckedFirst(_Fixture):

    def test_a_stray_entry_refuses_everything_before_any_key_or_write(self):
        a = self.shard(1, 1, {"a0": _e("law_a", 0), "x9": _e("law_x", 9)}, assigned=[("law_a", 0)])
        self.assertEqual(self.run_import([a]), 2, self.said)
        self.assertEqual(self.asked, [], "the import keyed proofs of a set it then refused")
        self.assertEqual(self.home(), {}, "a refused set wrote something")
        self.assertIn("Nothing was written", " ".join(self.said))


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class TheImportRunCannotOutliveItsBound(unittest.TestCase):
    """REG-3352 - MEASURED on the ALT: one re-ask ran 17,673 s against proof_release's 5,400 s bound. On a timeout run()
    kills heart2 and then waits for its pipes to close, which the key workers heart2 started still held. The output now
    goes to a file in the import's scratch dir: nothing is left to wait on, and a killed run still says how far it got."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="importrun-")
        self.addCleanup(shutil.rmtree, self.d, True)
        b = os.path.join(self.d, "src.tgz")
        with tarfile.open(b, "w:gz") as tf:
            body = b"{}"
            ti = tarfile.TarInfo("proof-shard-1/.heart2_cache.json")
            ti.size = len(body)
            tf.addfile(ti, io.BytesIO(body))
        data = io.open(b, "rb").read()
        self.urlopen = lambda req, timeout=None: _Resp(data)

    def test_heart2_writes_to_a_file_never_a_pipe(self):
        seen = {}

        def run(argv, **kw):
            seen.update(kw)
            kw["stdout"].write("  \u2713 REG-2586 IMPORTED 1 shard(s) of HEAD cccc: 3 PROVEN entr(ies) banked\n")
            kw["stdout"].flush()
            return subprocess.CompletedProcess(argv, 0, None, None)
        r = proof_release.import_bundle("c" * 40, tv_dir=HERE, run=run, urlopen=self.urlopen)
        self.assertNotIn("capture_output", seen, "the import's output is a pipe again: a kill waits on its workers")
        self.assertNotEqual(seen.get("stdout"), subprocess.PIPE)
        self.assertTrue(hasattr(seen.get("stdout"), "write"), "heart2's output is not a file: %r" % seen.get("stdout"))
        self.assertEqual(r["state"], "imported", r)
        self.assertIn("3 PROVEN entr(ies) banked", r["why"], "the line heart2 wrote to its log was not read back")

    def test_a_killed_run_says_the_last_line_it_wrote(self):
        def run(argv, **kw):
            kw["stdout"].write("    REG-3352 batch 3 of 6 written\n")
            kw["stdout"].flush()
            raise subprocess.TimeoutExpired(argv, 5400)
        r = proof_release.import_bundle("c" * 40, tv_dir=HERE, run=run, urlopen=self.urlopen)
        self.assertEqual(r["state"], "unknown", r)
        self.assertIn("TimeoutExpired", r["why"])
        self.assertIn("batch 3 of 6 written", r["why"], "a killed import said nothing of how far it got: %s" % r["why"])


RED_PROOF = [
    {
        "why": "REG-3352 - every entry is keyed again, the ones this PC already serves too: a re-ask runs past its bound",
        "file": "heart2.py",
        "find": "            if key in served and isinstance(e, dict) and _PS.servable(e):\n                kept[key] = e\n",
        "replace": "            if False:\n                kept[key] = e\n",
        "matches": 1,
    },
    {
        "why": "REG-3352 - a served entry no longer counts as banked: its shard reads as owing it",
        "file": "heart2.py",
        "find": "        _left, _resumed, took = _unserved(shards, _served_keys(target))\n",
        "replace": "        _left, _resumed, took = _unserved(shards, _served_keys(target))\n        took = {}\n",
        "matches": 1,
    },
    {
        "why": "REG-3352 - the import writes only at the end again: a killed run keeps nothing",
        "file": "heart2.py",
        "find": "            w_ok, w_why = _import_write(target, take, say, out)          # the stores' one locked writer, per batch\n",
        "replace": "            w_ok, w_why = True, None\n",
        "matches": 1,
    },
    {
        "why": "REG-3352 - a law is split across batches (the size alone decides)",
        "file": "heart2.py",
        "find": "    for g in order:\n        if cur and n + by[g] > size:\n",
        "replace": "    for g in order:\n        if cur and n + by[g] > size + 10 ** 6:\n",
        "matches": 1,
    },
    {
        "why": "REG-3352 - the import ignores the shut locks' rank and goes by name alone",
        "file": "heart2.py",
        "find": "    order = sorted(by, key=lambda g: (0, rank[g], g) if g in rank else (1, 0, g))\n",
        "replace": "    order = sorted(by)\n",
        "matches": 1,
    },
    {
        "why": "REG-3352 - a fixture store is ranked against this PC's real census",
        "file": "heart2.py",
        "find": "    if target is None or os.path.abspath(target) != os.path.abspath(CACHE):\n        return {}\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-3352 - heart2's output is a pipe again: a timed-out run waits on the key workers that hold it",
        "file": "proof_release.py",
        "find": "                        stdout=_log, stderr=subprocess.STDOUT, timeout=5400, creationflags=flags)\n",
        "replace": "                        capture_output=True, text=True, timeout=5400, creationflags=flags)\n",
        "matches": 1,
    },
    {
        "why": "REG-3352 - a killed import says nothing of how far it got",
        "file": "proof_release.py",
        "find": "    return (\" - last line: %s\" % lines[-1][:200]) if lines else \"\"\n",
        "replace": "    return \"\"\n",
        "matches": 1,
    },
    {
        "why": "REG-3352 - the shape pass is skipped: a stray entry is found only after earlier batches were keyed and written",
        "file": "heart2.py",
        "find": "        ok, why, _shape, skipped = _PS.select(shards, keyer=None)\n",
        "replace": "        _shape, skipped = {}, 0\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
