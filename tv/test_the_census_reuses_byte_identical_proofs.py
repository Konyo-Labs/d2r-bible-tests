# -*- coding: utf-8 -*-
"""#186 - THE SELF-PROVE CENSUS SERVES A PROOF BANKED OVER BYTE-IDENTICAL INPUTS, AND BANKS WHAT IT PROVES.

His ruling, 2026-10-28: "NO IT DOESNT NEED TO PROVE ITSELF. it can accept a proof earned on byte identical ... it should
work with that same recipe". Measured the night before: a push banks its PROVENs in the machine's verdict cache, and
then the census on the same PC re-proved those very laws from scratch (test_control: 27 proofs, ~92 minutes), while the
river stayed locked behind it. The census path (_prove_gates) never opened the cache; only prove(push=True) did.

Now `heart2.py --prove ... --reuse` - the self-prove lane's census, and only it - opens the cache: each proof is served
over byte-identical inputs through _cache_serve (the push's own rule, the same function) or run as the census always
ran it and banked through _cache_bank once its gate's closing clean run has kept it PROVEN. A proof needing what this
PC lacks is never served. A served gate keeps the age it was MEASURED at. A plain --prove (run_gates, CI, a hand run)
never opens it. The lane reads the prover's own served/banked line back (None until a run has said it).

EVERYTHING HERE IS A FIXTURE: the P3 law's throwaway repo, its ten-line law and a cache file beside it.
[[copy-drift]] [[stale-reading]] [[unknown-stays-unknown]] [[the-unjoined-end]]
RED_PROOF below.
"""
import io
import os
import sys
import tempfile
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 - this run's scratch dirs leave with it
_fx_tmp.contain()

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import heart2 as H  # noqa: E402
import self_prove as SP  # noqa: E402
# ONE copy of the fixture: the P3 law's tree, proof and cache case, and the #42 law's env/patch helpers. [[copy-drift]]
from test_a_push_proof_runs_only_where_its_defect_shows import _Env, _Patch  # noqa: E402
from test_a_proven_verdict_is_reused_only_on_identical_bytes import (  # noqa: E402
    _CLEAN_TAMPERED, _Case, _FILE, _GATE, _proof, _push_run)


def _census_run(tree, proofs, cache_path, lacks=None):
    """The REAL census path (_prove_gates) over the fixture tree with a census cache opened on `cache_path`, the way
    prove(reuse=True) opens one. `lacks`: what host_lacks answers. -> (results, per, runs logged, lines said)"""
    fd, log = tempfile.mkstemp(prefix="p3log.")
    os.close(fd)
    said = []
    patches = {"make_sandbox": tree.make}
    if lacks is not None:
        patches["host_lacks"] = lambda need: (lacks, "a fixture capability")
    try:
        H._CENSUS["cache"] = H._VerdictCache(path=cache_path, say=said.append) if cache_path else None
        try:
            with _Env(P3_LOG=log, HEART2_PROVE_WORKERS="1", TV_LAW_WIDTHS=None, P3_MUTATE=None), _Patch(**patches):
                results, per = H._prove_gates([(_GATE, _FILE, proofs)], said.append)
        finally:
            H._CENSUS["cache"] = None
        with io.open(log, encoding="utf-8") as fh:
            runs = [l.strip().split("|") for l in fh if l.strip()]
    finally:
        os.remove(log)
    return results, per, runs, said


class TheCensusReusesByteIdenticalProofs(_Case):

    def census(self, proofs=None, lacks=None):
        return _census_run(self.tree, proofs or [_proof()], self.cache_path, lacks=lacks)

    def test_a_census_banks_what_it_proves_and_serves_it_over_identical_bytes(self):
        results, per, runs, said = self.census()
        self.assertRan(runs, said, "cold census")
        self.assertEqual(results, {_GATE: H.PROVEN}, "\n".join(said))
        ent = self.entries()
        self.assertEqual(len(ent), 1, "a census PROVEN was not banked: %s\n%s" % (ent, "\n".join(said)))
        e = list(ent.values())[0]
        self.assertEqual((e.get("verdict"), e.get("by"), e.get("at")), (H.PROVEN, "census", ""),
                         "a census entry does not say it ran the whole law: %s" % e)
        results, per, runs, said = self.census()
        self.assertReused(runs, results, said, "warm census")

    def test_a_pushs_proof_makes_the_census_current_without_a_run(self):
        """the Mac's case: the push banked it in a worktree, the census in his tree serves it"""
        _r, _p, _s, runs, said = self.push()
        self.assertRan(runs, said, "PREMISE: the push proved it")
        results, per, runs, said = self.census()
        self.assertReused(runs, results, said, "a census after the push")

    def test_an_edit_to_the_subject_runs_the_census_again(self):
        self.census()
        self.tree.files["tv/subject.txt"] = "all fine here\n# an edit to the subject\n"
        results, per, runs, said = self.census()
        self.assertRan(runs, said, "the subject moved")
        self.assertEqual(len(self.entries()), 2, "the new bytes were not banked under a new key")

    def test_a_blind_proof_is_never_banked(self):
        blind = _proof(replace="FINE")                    # the law goes red only on BROKEN: this tamper stays green
        results, per, runs, said = self.census([blind])
        self.assertEqual(results, {_GATE: H.BLIND}, "PREMISE: the fixture proof is BLIND\n" + "\n".join(said))
        self.assertEqual(self.entries(), {}, "a census banked a BLIND")
        results, per, runs, said = self.census([blind])
        self.assertNotEqual(runs, [], "a BLIND was served from the cache")

    def test_a_proof_needing_what_this_pc_lacks_is_never_served(self):
        needy = _proof(needs="posix")
        results, per, runs, said = self.census([needy], lacks=False)
        self.assertEqual(results, {_GATE: H.PROVEN}, "PREMISE: proved where the need is met\n" + "\n".join(said))
        results, per, runs, said = self.census([needy], lacks=False)
        self.assertReused(runs, results, said, "BASELINE: the banked entry IS servable where the need is met")
        results, per, runs, said = self.census([needy], lacks=True)
        self.assertEqual(per[_GATE], [H.ELSEWHERE], "a proof this PC cannot judge was served: %s\n%s"
                         % (per, "\n".join(said)))
        self.assertFalse(any("PROVEN (cached" in l for l in said), "it was served from the cache")

    def test_the_closing_run_decides_what_a_census_banks(self):
        c = H._VerdictCache(path=self.cache_path, say=self.said.append)
        e = {"verdict": H.PROVEN, "provedAt": 1, "gate": _GATE}
        H._CLEAN.pending = [(0, "k-taken-away", dict(e, proof=0)), (1, lambda: "k-deferred", dict(e, proof=1))]
        try:
            n = H._census_bank(c, _GATE, [H.UNPROVABLE, H.PROVEN], self.said.append)
        finally:
            H._CLEAN.pending = None
        self.assertEqual((n, sorted(self.entries())), (1, ["k-deferred"]),
                         "the census banked a PROVEN its closing clean run took away, or not the deferred key")
        self.assertTrue(any("closing clean run took its PROVEN away" in l for l in self.said), self.said)


    def test_a_cache_that_raises_costs_a_re_prove_never_a_blind(self):
        class _Boom(H._VerdictCache):
            def lookup(self, key):
                raise RuntimeError("a cache fault")
        fd, log = tempfile.mkstemp(prefix="p3log.")
        os.close(fd)
        said = []
        try:
            H._CENSUS["cache"] = _Boom(path=self.cache_path, say=said.append)
            try:
                with _Env(P3_LOG=log, HEART2_PROVE_WORKERS="1", TV_LAW_WIDTHS=None, P3_MUTATE=None), \
                        _Patch(make_sandbox=self.tree.make):
                    results, per = H._prove_gates([(_GATE, _FILE, [_proof()])], said.append)
            finally:
                H._CENSUS["cache"] = None
        finally:
            os.remove(log)
        self.assertEqual(results, {_GATE: H.PROVEN}, "a cache fault became the proof's verdict:\n" + "\n".join(said))
        self.assertTrue(any("the census cache raised RuntimeError" in l for l in said), said[-4:])


class OnlyTheSelfProveCensusOpensIt(_Case):

    def prove(self, reuse, env=None):
        fd, log = tempfile.mkstemp(prefix="p3log.")
        os.close(fd)
        wrote = []
        try:
            with _Env(P3_LOG=log, HEART2_PROVE_WORKERS="1", TV_LAW_WIDTHS=None, P3_MUTATE=None, **(env or {})), \
                    _Patch(gate_files=lambda say=None: [(_GATE, _FILE)], red_proofs_in=lambda f: [_proof()],
                           red_proof_unreadable=lambda f: False, make_sandbox=self.tree.make, CACHE=self.cache_path,
                           _write_state=lambda r, measured=None, stamp=True, unmeasured=None: wrote.append(measured)):
                results = H.prove(only={_GATE}, say=self.said.append, reuse=reuse)
            with io.open(log, encoding="utf-8") as fh:
                runs = [l.strip().split("|") for l in fh if l.strip()]
        finally:
            os.remove(log)
        return results, runs, wrote

    def test_a_plain_prove_runs_and_a_reuse_census_serves_with_its_measured_age(self):
        self.push()
        proved_at = list(self.entries().values())[0]["provedAt"]
        results, runs, wrote = self.prove(False)
        self.assertEqual((runs, results), (_CLEAN_TAMPERED, {_GATE: H.PROVEN}),
                         "a plain --prove served a verdict: the verdict of record must be a run: %s" % runs)
        self.assertIsNone(H._CENSUS["cache"], "the census cache outlived its run")
        results, runs, wrote = self.prove(True)
        self.assertEqual((runs, results), ([], {_GATE: H.PROVEN}),
                         "the self-prove census re-ran a proof banked over identical bytes: %s\n%s"
                         % (runs, "\n".join(self.said[-8:])))
        self.assertEqual(wrote[-1], {_GATE: proved_at}, "a served gate was stamped with this run's clock")
        self.assertTrue(any("#186 CENSUS CACHE: 1 of 1 proof(s) reused" in l for l in self.said),
                        [l for l in self.said if "CACHE" in l])
        self.assertIsNone(H._CENSUS["cache"], "the census cache outlived its run")

    def test_the_off_switch_closes_the_census_cache_and_says_so(self):
        self.push()
        results, runs, wrote = self.prove(True, env={"HEART2_PROVE_CACHE": "0"})
        self.assertEqual(runs, _CLEAN_TAMPERED, "HEART2_PROVE_CACHE=0 was ignored by the census")
        self.assertTrue(any("#186 CENSUS CACHE: OFF" in l for l in self.said), self.said[-4:])

    def test_a_slice_bank_stamps_a_served_gate_with_its_measured_age(self):
        class _Stub(object):
            reused = {(_GATE, 0): 4242}
        wrote = []
        H._CENSUS["cache"] = _Stub()
        try:
            with _Patch(_write_state=lambda r, measured=None, stamp=True, unmeasured=None: wrote.append(measured)):
                H._slice_banker(set(), self.said.append, every_s=0)({_GATE: (H.PROVEN, [H.PROVEN])}, threading.Lock())
        finally:
            H._CENSUS["cache"] = None
        self.assertEqual(wrote, [{_GATE: 4242}], "the slice bank stamped a served gate with its own clock")


class TheLaneReadsItsCensusCountBack(_Case):

    def test_the_lane_spawns_with_reuse_and_parses_the_provers_own_line(self):
        seen = {}

        class _P(object):
            pid = 4242

        def popen(cmd, **kw):
            seen["cmd"] = cmd
            return _P()
        SP.spawn(os.path.join(self.dir, "log"), popen=popen, names=["g1"])
        self.assertIn("--reuse", seen["cmd"], "the self-prove census is not told to reuse")
        self.push()
        _r, _runs, _w = OnlyTheSelfProveCensusOpensIt.prove(self, True)
        line = [l for l in self.said if "#186 CENSUS CACHE:" in l and "reused" in l]
        self.assertTrue(line, "PREMISE: the census said its count")
        log = os.path.join(self.dir, "prover.log")
        with io.open(log, "w", encoding="utf-8") as fh:
            fh.write("  #186 CENSUS CACHE: 7 of 9 proof(s) reused from the cache · 2 proved and banked · ...\n")
            start = fh.tell()
            fh.write("\n".join(self.said) + "\n")
        # REG-3046 - the prover's line now says how many of the served proofs were carried from another PC (0 here)
        self.assertEqual(SP._log_reuse(log, start), {"served": 1, "of": 1, "carried": 0, "banked": 0},
                         "the lane misread THIS run's line (or read an older run's): %s" % line)
        with io.open(log, "a", encoding="utf-8") as fh:
            start = fh.tell()
            fh.write("a prover that died before it said anything\n")
        self.assertIsNone(SP._log_reuse(log, start), "a run that said nothing was given a count")
        # REG-2732 (the #231 eye on v3819) - a run whose start is UNKNOWN cannot tell this run's line from an older one
        self.assertIsNone(SP._log_reuse(log, None), "a run with no known start adopted an EARLIER run's reuse line")


RED_PROOF = [
    {"why": "REG-2732 - a run whose start is unknown adopts an earlier run's reuse line as its own",
     "file": "tv/self_prove.py",
     "find": "            if begin is None:\n                return None          # REG-2732 (the #231 eye on v3819) - the tail could be an EARLIER run's line\n",
     "replace": "            begin = 0 if begin is None else begin\n",
     "matches": 1},
    {"why": "#186 - the census never serves a banked proof: every push's work is re-proved",
     "file": "tv/heart2.py",
     "find": "    if served is not None:\n        return served\n    v = _prove_one(sandbox, name, filename, pr, idx, say)\n",
     "replace": "    v = _prove_one(sandbox, name, filename, pr, idx, say)\n",
     "matches": 1},
    {"why": "#186 - a cache that raises files the proof BLIND, and one BLIND shuts every lock",
     "file": "tv/heart2.py",
     "find": "    try:\n        served, key, rels = _cache_serve(cache, sandbox, name, filename, pr, idx, say)\n    except Exception as _se:\n",
     "replace": "    if True:\n        served, key, rels = _cache_serve(cache, sandbox, name, filename, pr, idx, say)\n    if False:\n",
     "matches": 1},
    {"why": "#186 - the census banks nothing: a slice that stands aside keeps no proof",
     "file": "tv/heart2.py",
     "find": "    _cache_bank(cache, sandbox, name, filename, pr, idx, say, key, rels, v, by=\"census\")\n",
     "replace": "    pass\n",
     "matches": 1},
    {"why": "#186 - the census banks a PROVEN its closing clean run took away",
     "file": "tv/heart2.py",
     "find": "        if _bankable(per[_i]):\n            if callable(_key):\n",
     "replace": "        if True:\n            if callable(_key):\n",
     "matches": 1},
    {"why": "#186 - a proof needing what this PC lacks is served from another PC's bank",
     "file": "tv/heart2.py",
     "find": "        if _lacks is not False:\n            return None, None, []\n",
     "replace": "        if False:\n            return None, None, []\n",
     "matches": 1},
    {"why": "#186 - a plain --prove (the verdict of record) opens the census cache",
     "file": "tv/heart2.py",
     "find": "        _CENSUS[\"cache\"] = _census_cache(reuse, say)",
     "replace": "        _CENSUS[\"cache\"] = _census_cache(True, say)",
     "matches": 1},
    {"why": "#186 - HEART2_PROVE_CACHE=0 does not close the census cache",
     "file": "tv/heart2.py",
     "find": "    if _prove_cache_off():\n        say(\"  #186 CENSUS CACHE: OFF",
     "replace": "    if False:\n        say(\"  #186 CENSUS CACHE: OFF",
     "matches": 1},
    {"why": "#186 - a served census gate is stamped with this run's clock, not the age it was measured at",
     "file": "tv/heart2.py",
     "find": "            _ages = _reused_ages(_ccache, results or {})\n",
     "replace": "            _ages = {}\n",
     "matches": 1},
    {"why": "#186 - a slice's bank stamps a served gate with its own clock",
     "file": "tv/heart2.py",
     "find": "unmeasured=unm, measured=_reused_ages(_CENSUS.get(\"cache\"), snap))\n",
     "replace": "unmeasured=unm, measured=None)\n",
     "matches": 1},
    {"why": "#186 - the lane gives a run that said nothing a count of zero (UNKNOWN read as measured)",
     "file": "tv/self_prove.py",
     "find": "    if not got:\n        return None\n    a, b, k, c = got[-1]\n",
     "replace": "    if not got:\n        return {\"served\": 0, \"of\": 0, \"banked\": 0}\n    a, b, k, c = got[-1]\n",
     "matches": 1},
    {"why": "#186 - the lane spawns the census without --reuse",
     "file": "tv/self_prove.py",
     "find": "           + ([\"--reuse\"] if reuse else []))\n",
     "replace": "           )\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
