# -*- coding: utf-8 -*-
"""REG-3191 (his ruling 2026-11-05 ~09:05, item 3: "Each PC imports the proofs for byte-identical files at update ... and
runs only an environment self-check: the laws whose `needs` are platform-specific. Locks open on (imported proofs + local
self-check).") - AN IMPORTED PROOF OVER IDENTICAL BYTES OPENS THE LOCKS WITHOUT A LOCAL RUN.

MEASURED on his Mac (v3864, 2026-11-05 ~21:03): GitHub's proofs were imported (2,928 entries, ~20:55), yet the self-prove
lane said "1406 of 1568 declaring gate(s) proved for the files on disk; 162 owed" and self_arming.may('frame.release')
refused on 17 of its own guard laws. The slice path already SERVED imported proofs (#186; its last slice served 183 of 251
- MEASURED from /api/status), so the hold was the wait: an owed gate reached the census only when a 40-gate slice got to
it, behind laws that really run. Read-only on his files at 21:29 (34 owed then): 7 trusted by import - test_control and
test_vault_l1_rules_drive_every_move among frame.release's 11 owed guards - 9 environment self-check, 18 the bank cannot
serve. heart2.trust_pass now writes, before a slice proves anything, every owed gate whose every proof the bank serves
over this checkout's bytes. Held here:
  * an imported entry over identical bytes is TRUSTED and written into the census (its gateSha, `trusted`, and the age it
    was measured at - never this run's clock); a gate the census holds BLIND is never written on another tree's word;
  * a gate any proof of which declares "needs", or one named in the DECLARED ENV_SELF_CHECK, is the environment
    self-check: never trusted, and the census serve never hands it another tree's PROVEN (own_only);
  * a key mismatch (no PROVEN under the key these bytes give), an unkeyable proof, a key that raises: not trusted;
  * this tree's own proofs are served-here, not "trusted";
  * the PUSH path is unchanged: _owes_here still owes a clean run outside a known change set, and only the census branch
    of prove() asks the trust pass.
Fixtures only: fixture gate files, a fixture census path, a stand-in bank. RED_PROOF below.
"""
import ast
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import heart2 as H  # noqa: E402

HERE_TREE = H.TREE_ID
CI_TREE = "/home/runner/work/d2r-bible-tests/d2r-bible-tests"


def _entry(tree, at=1000):
    return {"verdict": H.PROVEN, "provedAt": at, "tree": tree, "gate": "g", "proof": 0}


def _split(gates, bank, keys=None):
    """gates: {name: [proof]}; bank: {key: entry}; keys: {(name, i): key | None | Exception}"""
    keys = keys or {}

    def proofs_of(n):
        return "%s.py" % n, gates[n]

    def key_of(n, f, pr):
        i = gates[n].index(pr)
        k = keys.get((n, i), "k:%s:%d" % (n, i))
        if isinstance(k, Exception):
            raise k
        return k
    return H.split_owed(sorted(gates), proofs_of, key_of, bank.get, HERE_TREE)


P0 = {"why": "a", "file": "tv/x.py", "find": "a", "replace": "b", "matches": 1}
P1 = {"why": "b", "file": "tv/x.py", "find": "c", "replace": "d", "matches": 1}
PN = {"why": "n", "file": "tv/x.py", "find": "e", "replace": "f", "matches": 1, "needs": "node"}


class TheSplitTrustsOnlyWhatTheBankServesWhole(unittest.TestCase):

    def test_an_imported_proof_over_identical_bytes_is_trusted(self):
        sp = _split({"plain": [P0, P1]}, {"k:plain:0": _entry(CI_TREE, 700), "k:plain:1": _entry(CI_TREE, 500)})
        self.assertEqual(sp["trusted"], {"plain": 2})
        self.assertEqual(sp["ages"]["plain"], 500, "a trusted gate keeps the OLDEST age it stands on")
        self.assertEqual((sp["env"], sp["unservable"], sp["servedHere"]), ({}, {}, []))

    def test_one_foreign_proof_among_this_trees_own_is_trusted(self):
        sp = _split({"mixed": [P0, P1]}, {"k:mixed:0": _entry(HERE_TREE), "k:mixed:1": _entry(CI_TREE)})
        self.assertEqual(sp["trusted"], {"mixed": 1})

    def test_this_trees_own_proofs_are_served_here_not_trusted(self):
        sp = _split({"own": [P0, P1]}, {"k:own:0": _entry(HERE_TREE), "k:own:1": _entry(HERE_TREE)})
        self.assertEqual((sp["trusted"], sp["servedHere"]), ({}, ["own"]))

    def test_a_needs_gate_is_the_environment_self_check(self):
        sp = _split({"js": [P0, PN]}, {"k:js:0": _entry(CI_TREE), "k:js:1": _entry(CI_TREE)})
        self.assertEqual(sp["trusted"], {}, "a gate whose proof declares needs was trusted on another tree's word")
        self.assertIn("needs node", sp["env"]["js"])

    def test_a_declared_env_gate_is_the_environment_self_check(self):
        for name in ("test_d2jsp_desk", "test_a_windows_console_runs_in_utf8_mode",
                     "test_triage_runs_beside_a_shadow_reel", "test_a_proof_stands_aside_for_a_push"):
            self.assertIn(name, H.ENV_SELF_CHECK, "the declared self-check lost a measured environment catcher")
            sp = _split({name: [P0]}, {"k:%s:0" % name: _entry(CI_TREE)})
            self.assertEqual(sp["trusted"], {}, "%s was trusted on another tree's word" % name)
            self.assertEqual(sp["env"], {name: "named in ENV_SELF_CHECK"})

    def test_a_key_mismatch_is_not_trusted(self):
        # proof 1 was banked over OTHER bytes: nothing sits under the key these bytes give it
        sp = _split({"moved": [P0, P1]}, {"k:moved:0": _entry(CI_TREE), "k:other-bytes:1": _entry(CI_TREE)})
        self.assertEqual(sp["trusted"], {}, "a gate with a proof the bank cannot serve was trusted")
        self.assertEqual(sp["unservable"], {"moved": "proof 1 has no PROVEN banked over these bytes"})

    def test_an_unkeyable_or_raising_key_is_not_trusted(self):
        sp = _split({"nokey": [P0], "boom": [P0]}, {"k:nokey:0": _entry(CI_TREE), "k:boom:0": _entry(CI_TREE)},
                    keys={("nokey", 0): None, ("boom", 0): RuntimeError("x")})
        self.assertEqual(sp["trusted"], {})
        self.assertEqual(sorted(sp["unservable"]), ["boom", "nokey"])


_GATE_SRC = '''RED_PROOF = [%s]
'''


class TheTrustPassWritesTheCensus(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="reg3191-")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.state = os.path.join(self.d, ".heart2.json")
        self.gates = []
        for n, prs in (("plain", [P0, P1]), ("js", [P0, PN]), ("moved", [P0])):
            p = os.path.join(self.d, "%s.py" % n)
            with io.open(p, "w", encoding="utf-8") as fh:
                fh.write(_GATE_SRC % ", ".join(repr(x) for x in prs))
            self.gates.append((n, p))
        self.bank = {"k:plain:0": _entry(CI_TREE, 600), "k:plain:1": _entry(CI_TREE, 400),
                     "k:js:0": _entry(CI_TREE), "k:js:1": _entry(CI_TREE), "k:other:0": _entry(CI_TREE)}
        gates = self.gates

        class Bank(object):
            def __init__(s, entries):
                s.entries = entries

            def key_for(s, sandbox, name, filename, pr, unread=None, listed=None):
                proofs = H.red_proofs_in(filename)
                return "k:%s:%d" % (name, proofs.index(pr)), [], None

            def peek(s, key):
                return s.entries.get(key)
        self.cache = Bank(self.bank)
        for patch in (mock.patch.object(H, "STATE", self.state),
                      mock.patch.object(H, "gate_files", lambda say=print: list(gates)),
                      mock.patch.object(H, "surface_verdict", lambda *a, **k: None)):
            patch.start()
            self.addCleanup(patch.stop)

    def _census(self):
        with io.open(self.state, encoding="utf-8") as fh:
            return json.load(fh)

    def test_trusted_gates_are_recorded_in_the_census(self):
        sp = H.trust_pass(self.cache, say=lambda *a: None)
        self.assertEqual(sp["written"], ["plain"])
        st = self._census()
        sha = H.gate_shas(self.gates)["plain"]
        self.assertEqual(st["gateShas"].get("plain"), sha, "the trusted gate's sha was not recorded - it stays owed")
        self.assertEqual(st["trusted"], {"plain": sha}, "the census does not say which gate stands on another tree")
        self.assertIn("plain", st["provedGates"])
        self.assertEqual(st["verdictAt"]["plain"], 400, "a trusted gate was stamped NOW, not when it was measured")
        for n in ("js", "moved"):
            self.assertNotIn(n, st["gateShas"], "%s was written on the bank's word" % n)
        owed = [n for n, _k in H.slice_owed(self.gates, st)["owed"]]
        self.assertEqual(owed, ["js", "moved"], "only the self-check and the unservable stay owed")

    def test_a_gate_the_census_holds_blind_is_never_written_on_another_trees_word(self):
        with io.open(self.state, "w", encoding="utf-8") as fh:
            json.dump({"blind": ["plain"], "gateShas": {}}, fh)
        sp = H.trust_pass(self.cache, say=lambda *a: None)
        self.assertNotIn("plain", sp["written"])
        self.assertNotIn("plain", self._census().get("gateShas") or {})

    def test_a_later_verdict_judged_here_ends_the_trust(self):
        H.trust_pass(self.cache, say=lambda *a: None)
        H._write_state({"plain": H.PROVEN}, stamp=False)
        self.assertEqual(self._census()["trusted"], {}, "a gate judged here still read as another tree's word")


class TheCensusServeJudgesTheSelfCheckHere(unittest.TestCase):

    def _cache(self, tree):
        e = dict(_entry(tree), inputs=[])

        class C(object):
            def __init__(s):
                s.n = {}
                s.said = []

            def key_for(s, *a, **k):
                return "key", [], None

            def peek(s, key):
                return e

            def lookup(s, key):
                return e

            def count(s, what):
                s.n[what] = s.n.get(what, 0) + 1

            def count_carried(s, by):
                pass

            def reused_at(s, *a):
                pass

            def say_once(s, name, why, line):
                s.said.append(line)
        return C()

    def test_own_only_refuses_another_trees_proof_and_serves_this_trees(self):
        q = lambda *a: None  # noqa: E731
        got = H._cache_serve(self._cache(CI_TREE), HERE, "g", "g.py", P0, 0, q, own_only=True)[0]
        self.assertIsNone(got, "the self-check was served another tree's PROVEN")
        got = H._cache_serve(self._cache(HERE_TREE), HERE, "g", "g.py", P0, 0, q, own_only=True)[0]
        self.assertEqual(got, H.PROVEN, "this tree's own PROVEN was refused")
        got = H._cache_serve(self._cache(CI_TREE), HERE, "g", "g.py", P0, 0, q)[0]
        self.assertEqual(got, H.PROVEN, "the push's serve (no own_only) changed")

    def test_the_census_hands_own_only_to_the_self_check_gates(self):
        ran = []
        with mock.patch.object(H, "_prove_one", lambda *a, **k: ran.append(a[1]) or "RAN"), \
                mock.patch.object(H, "_cache_bank", lambda *a, **k: None), \
                mock.patch.dict(H._CENSUS, {"cache": self._cache(CI_TREE), "here": {"g"}, "red": set()}):
            self.assertEqual(H._census_one(HERE, "g", "g.py", P0, 0, lambda *a: None), "RAN")
            self.assertEqual(H._census_one(HERE, "other", "g.py", P0, 0, lambda *a: None), H.PROVEN)
        self.assertEqual(ran, ["g"])

    def test_prove_names_the_self_check_gates_for_the_census(self):
        body = _code_of("prove")
        self.assertEqual(body.count('_CENSUS["here"] = set(n for n, _f, _p in have if env_gate(n, _p)[0])'), 1,
                         "the census no longer judges the environment self-check gates here")


def _heart2_src():
    with io.open(os.path.join(HERE, "heart2.py"), encoding="utf-8") as fh:
        return fh.read()


def _code_of(fn_name):
    """One module-level function of heart2.py, comments stripped by the tokenizer (never by a '#' split), blank lines
    dropped. The function is found by the AST, so the anchor is its name, which occurs once at module level."""
    import tokenize
    src = _heart2_src()
    toks = [t for t in tokenize.generate_tokens(io.StringIO(src).readline) if t.type != tokenize.COMMENT]
    bare = tokenize.untokenize(toks)
    tree = ast.parse(src)
    hits = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn_name]
    assert len(hits) == 1, fn_name
    lines = bare.splitlines()[hits[0].lineno - 1:hits[0].end_lineno]
    return "\n".join(ln.rstrip() for ln in lines if ln.strip())


class ThePushPathStillOwesItsCleanRun(unittest.TestCase):

    def test_a_push_with_an_unknown_change_set_still_owes_a_clean_run(self):
        run = H._PushRun()
        self.assertIsNone(run.direct)
        self.assertTrue(H._owes_here(run, "anything"), "a push with an UNKNOWN change set kept another tree's word")
        run.direct = {"changed"}
        self.assertTrue(H._owes_here(run, "changed"))
        self.assertFalse(H._owes_here(run, "untouched"))

    def test_only_the_census_branch_asks_the_trust_pass(self):
        tree = ast.parse(_heart2_src())
        fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "prove"][0]
        tops = [n for n in fn.body if isinstance(n, ast.If) and isinstance(n.test, ast.Name) and n.test.id == "push"
                and n.orelse]
        self.assertEqual(len(tops), 1, "prove() no longer has ONE push / census fork")

        def calls(nodes):
            return [c.func.id for x in nodes for c in ast.walk(x)
                    if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)]
        self.assertNotIn("trust_pass", calls(tops[0].body), "the push branch asks the trust pass")
        self.assertEqual(calls(tops[0].orelse).count("trust_pass"), 1, "the census branch lost its trust pass")
        push_one = _code_of("_prove_push_one")
        self.assertIn("served, key, rels = _cache_serve(cache, sandbox, name, filename, pr, idx, say)\n", push_one + "\n",
                      "the push's serve now passes own_only")


RED_PROOF = [
    {"why": "REG-3191 - a gate with a proof the bank cannot serve (a key mismatch) is trusted all the same",
     "file": "tv/heart2.py",
     "find": "            if not isinstance(hit, dict):\n                miss = \"proof %d has no PROVEN banked over these bytes\" % i\n                break\n",
     "replace": "            if not isinstance(hit, dict):\n                continue\n",
     "matches": 1},
    {"why": "REG-3191 - a gate whose proof declares needs is trusted on another tree's word",
     "file": "tv/heart2.py",
     "find": "    if needs:\n        return True, \"a proof declares needs %s\"",
     "replace": "    if False:\n        return True, \"a proof declares needs %s\"",
     "matches": 1},
    {"why": "REG-3191 - the declared ENV_SELF_CHECK is ignored",
     "file": "tv/heart2.py",
     "find": "    if name in ENV_SELF_CHECK:\n        return True, \"named in ENV_SELF_CHECK\"",
     "replace": "    if False:\n        return True, \"named in ENV_SELF_CHECK\"",
     "matches": 1},
    {"why": "REG-3191 - this tree's own proofs are counted as another tree's word",
     "file": "tv/heart2.py",
     "find": "            if hit.get(\"tree\") != here:\n                foreign += 1\n",
     "replace": "            foreign += 1\n",
     "matches": 1},
    {"why": "REG-3191 - a gate the census holds BLIND is written on another tree's word",
     "file": "tv/heart2.py",
     "find": "    owed = [n for n, _k in so.get(\"owed\") or [] if n not in _blind]\n",
     "replace": "    owed = [n for n, _k in so.get(\"owed\") or []]\n",
     "matches": 1},
    {"why": "REG-3191 - a trusted gate is stamped with this run's clock, not the age it was measured at",
     "file": "tv/heart2.py",
     "find": "        _write_state(dict((n, PROVEN) for n in take), measured=dict((n, sp[\"ages\"][n]) for n in take if n in sp[\"ages\"]),\n",
     "replace": "        _write_state(dict((n, PROVEN) for n in take), measured=None,\n",
     "matches": 1},
    {"why": "REG-3191 - the census does not record which gates stand on another tree's proofs",
     "file": "tv/heart2.py",
     "find": "        if _n in _trq and _n not in _unm:\n            _tr[_n] = _shas.get(_n)\n",
     "replace": "        if False:\n            _tr[_n] = _shas.get(_n)\n",
     "matches": 1},
    {"why": "REG-3191 - the census serve hands the self-check gates another tree's PROVEN",
     "file": "tv/heart2.py",
     "find": "            if own_only and _own is not None and _own.get(\"tree\") != TREE_ID:\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-3191 - the census serve never asks which gates the census judges here, so none is",
     "file": "tv/heart2.py",
     "find": "        own_only = name in (_CENSUS.get(\"here\") or ())\n",
     "replace": "        own_only = False\n",
     "matches": 1},
    {"why": "REG-3191 - prove() stops naming the environment self-check gates",
     "file": "tv/heart2.py",
     "find": "            _CENSUS[\"here\"] = set(n for n, _f, _p in have if env_gate(n, _p)[0])   # the environment self-check\n",
     "replace": "            _CENSUS[\"here\"] = set()\n",
     "matches": 1},
    {"why": "REG-2599 (push path unchanged) - a push with an UNKNOWN change set keeps another tree's word",
     "file": "tv/heart2.py",
     "find": "    return direct is None or name in direct\n",
     "replace": "    return direct is not None and name in direct\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
