# -*- coding: utf-8 -*-
"""REG-3191 (his ruling 2026-11-05 ~09:05, item 3: "Each PC imports the proofs for byte-identical files at update ... and
runs only an environment self-check: the laws whose `needs` are platform-specific. Locks open on (imported proofs + local
self-check).") - AN IMPORTED PROOF OVER IDENTICAL BYTES OPENS THE LOCKS WITHOUT A LOCAL RUN, AND WITHOUT WAITING FOR IDLE.

MEASURED on his Mac (v3864, 2026-11-05): GitHub's proofs were imported (~20:55), yet at 21:03 the lane said "1406 of 1568
declaring gate(s) proved ...; 162 owed" and self_arming.may('frame.release') refused on 17 of its own guard laws. The slice
path already served imported proofs (#186), so the hold was the WAIT: an owed gate reached the census only when a 40-gate
slice got to it, and a slice waits for an idle PC - at 22:14 the lane sat 'busy' for 34 min with 6 of its 27 owed gates
fully servable and unwritten. heart2.trust_pass writes every owed gate whose every proof the bank serves over this
checkout's bytes, with no law run: before a slice proves anything, right after the update-time import
(`heart2.py --trust --import-shards`, proof_release), and as the lane's own light start when a slice is held only by its
cost (`heart2.py --trust`, self_prove.trust_start). Held here, on fixtures:
  * an imported entry over identical bytes is TRUSTED and written (its gateSha, `trusted`, its measured age); a gate the
    census holds BLIND - or one a slice files BLIND while the keys are taken - is never written on another tree's word;
  * a gate any proof of which declares "needs", or one named in the DECLARED ENV_SELF_CHECK, is the environment
    self-check: never trusted, and prove() judges it here (the census serve hands it no other tree's PROVEN);
  * a key mismatch, an unkeyable proof, a key that raises: not trusted; an open environment re-prove asks the bank nothing;
  * prove(reuse=True) never re-proves a gate the trust pass wrote; a hand prove (no --reuse) and a PUSH never ask it;
  * `--trust` runs it alone, and after an import only when the import landed; proof_release asks for it at update;
  * the lane starts it when a slice is held by busy / cooldown / backoff / memory / takes-only - never beside his game,
    never twice for one bank, never during an environment re-prove - and books its end as neither a proof nor a failure.
Fixtures only: fixture gate files, a fixture census path, a stand-in bank. RED_PROOF below.
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
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import heart2 as H  # noqa: E402
import self_prove as SP  # noqa: E402
import proof_release as PR  # noqa: E402

HERE_TREE = H.TREE_ID
CI_TREE = "/home/runner/work/d2r-bible-tests/d2r-bible-tests"
QUIET = lambda *a, **k: None  # noqa: E731


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

    def test_this_trees_own_proofs_are_served_here_not_trusted(self):
        sp = _split({"own": [P0, P1]}, {"k:own:0": _entry(HERE_TREE), "k:own:1": _entry(HERE_TREE)})
        self.assertEqual((sp["trusted"], sp["servedHere"]), ({}, ["own"]))
        sp = _split({"mixed": [P0, P1]}, {"k:mixed:0": _entry(HERE_TREE), "k:mixed:1": _entry(CI_TREE)})
        self.assertEqual(sp["trusted"], {"mixed": 1})

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

    def test_a_key_mismatch_or_an_unkeyable_proof_is_not_trusted(self):
        sp = _split({"moved": [P0, P1]}, {"k:moved:0": _entry(CI_TREE), "k:other-bytes:1": _entry(CI_TREE)})
        self.assertEqual(sp["trusted"], {}, "a gate with a proof the bank cannot serve was trusted")
        self.assertEqual(sp["unservable"], {"moved": "proof 1 has no PROVEN banked over these bytes"})
        sp = _split({"nokey": [P0], "boom": [P0]}, {"k:nokey:0": _entry(CI_TREE), "k:boom:0": _entry(CI_TREE)},
                    keys={("nokey", 0): None, ("boom", 0): RuntimeError("x")})
        self.assertEqual((sp["trusted"], sorted(sp["unservable"])), ({}, ["boom", "nokey"]))


_GATE_SRC = '''RED_PROOF = [%s]
'''


class _Bank(object):
    """A stand-in census cache: the slice's own key_for / peek, over the fixture gates' proofs."""

    def __init__(self, entries, on_key=None):
        self.entries, self.on_key, self.reused, self.peeked = entries, on_key, {}, []

    def key_for(self, sandbox, name, filename, pr, unread=None, listed=None):
        if self.on_key is not None:
            self.on_key(name)
        return "k:%s:%d" % (name, H.red_proofs_in(filename).index(pr)), [], None

    def peek(self, key):
        self.peeked.append(key)
        return self.entries.get(key)

    def summary(self, n):
        return "#42 P3 CACHE: fixture"


class _Census(unittest.TestCase):
    """Three fixture gates: `plain` (imported, servable whole), `js` (a needs node proof - the self-check), `moved` (no
    PROVEN under the key its bytes give). The census path, the gate files and the bank are all fixtures."""

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
        self.bank = _Bank({"k:plain:0": _entry(CI_TREE, 600), "k:plain:1": _entry(CI_TREE, 400),
                           "k:js:0": _entry(CI_TREE), "k:js:1": _entry(CI_TREE), "k:other:0": _entry(CI_TREE)})
        gates = self.gates
        for patch in (mock.patch.object(H, "STATE", self.state),
                      mock.patch.object(H, "gate_files", lambda say=print: list(gates)),
                      mock.patch.object(H, "surface_verdict", lambda *a, **k: None),
                      mock.patch.object(H, "env_reprove_state", lambda *a, **k: None),
                      mock.patch.dict(H._CENSUS, {"cache": None, "here": (), "red": set(), "net": False})):
            patch.start()
            self.addCleanup(patch.stop)

    def census(self):
        with io.open(self.state, encoding="utf-8") as fh:
            return json.load(fh)

    def write(self, body):
        with io.open(self.state, "w", encoding="utf-8") as fh:
            json.dump(body, fh)

    def owed(self):
        return [n for n, _k in H.slice_owed(self.gates, self.census())["owed"]]


class TheTrustPassWritesTheCensus(_Census):

    def test_trusted_gates_are_recorded_in_the_census(self):
        sp = H.trust_pass(self.bank, say=QUIET)
        self.assertEqual(sp["written"], ["plain"])
        st = self.census()
        sha = H.gate_shas(self.gates)["plain"]
        self.assertEqual(st["gateShas"].get("plain"), sha, "the trusted gate's sha was not recorded - it stays owed")
        self.assertEqual(st["trusted"], {"plain": sha}, "the census does not say which gate stands on another tree")
        self.assertEqual(st["verdictAt"]["plain"], 400, "a trusted gate was stamped NOW, not when it was measured")
        self.assertEqual(self.owed(), ["js", "moved"], "only the self-check and the unservable stay owed")

    def test_a_gate_the_census_holds_blind_is_never_written_on_another_trees_word(self):
        self.write({"blind": ["plain"], "gateShas": {}})
        sp = H.trust_pass(self.bank, say=QUIET)
        self.assertNotIn("plain", sp["written"])
        self.assertNotIn("plain", self.census().get("gateShas") or {})
        self.assertEqual(sp["owed"], 2, "a gate the census holds BLIND was asked of the bank at all")
        self.assertFalse([k for k in self.bank.peeked if k.startswith("k:plain:")],
                         "the bank was asked to stand in for a BLIND measured here")

    def test_a_blind_a_slice_files_while_the_keys_are_taken_is_not_overwritten(self):
        self.write({"gateShas": {}})
        said = []

        def slice_files_blind(name):
            if not said:
                said.append(name)
                with io.open(self.state, "w", encoding="utf-8") as fh:
                    json.dump({"gateShas": {}, "blind": ["plain"]}, fh)
        self.bank.on_key = slice_files_blind
        sp = H.trust_pass(self.bank, say=QUIET)
        self.assertNotIn("plain", sp["written"], "a BLIND filed during the pass was overwritten on another tree's word")
        self.assertEqual(self.census().get("blind"), ["plain"])

    def test_an_open_environment_reprove_asks_the_bank_nothing(self):
        with mock.patch.object(H, "env_reprove_state", lambda *a, **k: {"owed": ["plain"], "from": {}, "to": {}}):
            sp = H.trust_pass(self.bank, say=QUIET)
        self.assertEqual((sp["written"], self.bank.peeked), ([], []),
                         "a proof banked under the old environment was served during its re-prove")
        self.assertFalse(os.path.exists(self.state))

    def test_a_later_verdict_judged_here_ends_the_trust(self):
        H.trust_pass(self.bank, say=QUIET)
        H._write_state({"plain": H.PROVEN}, stamp=False)
        self.assertEqual(self.census()["trusted"], {}, "a gate judged here still read as another tree's word")


class ProveTrustsBeforeItProves(_Census):
    """prove(reuse=True) - the self-prove lane's census - end to end, with only the law runs stood in."""

    def _prove(self, **kw):
        seen = {}

        def gates_run(have, say=print, workers=None, blank=None):
            seen["names"] = sorted(n for n, _f, _p in have)
            seen["here"] = set(H._CENSUS.get("here") or ())
            seen["cache"] = H._CENSUS.get("cache")
            return dict((n, H.PROVEN) for n in seen["names"]), dict((n, [H.PROVEN]) for n in seen["names"])
        with mock.patch.object(H, "_census_cache", lambda reuse, say=print: self.bank if reuse else None), \
                mock.patch.object(H, "_prove_gates", gates_run):
            got = H.prove(say=QUIET, stamp=False, **kw)
        return got, seen

    def test_the_census_writes_the_imported_gate_and_proves_only_the_rest(self):
        got, seen = self._prove(reuse=True)
        self.assertEqual(seen["names"], ["js", "moved"], "a gate the bank serves whole was proved again by the slice")
        self.assertEqual(seen["here"], {"js"}, "the environment self-check is not judged on this PC")
        self.assertEqual(self.census()["trusted"], {"plain": H.gate_shas(self.gates)["plain"]})
        self.assertEqual(self.owed(), [], "the census still owes gates after the slice proved the rest")

    def test_a_hand_prove_never_asks_the_bank(self):
        with mock.patch.object(H, "trust_pass", mock.Mock(side_effect=AssertionError("asked"))):
            got, seen = self._prove(reuse=False)
        self.assertEqual(seen["names"], ["js", "moved", "plain"])
        self.assertIsNone(seen["cache"])
        self.assertNotIn("plain", self.census().get("trusted") or {})


class ThePushPathIsUnchanged(_Census):

    def test_a_push_with_an_unknown_change_set_still_owes_a_clean_run(self):
        run = H._PushRun()
        self.assertIsNone(run.direct)
        self.assertTrue(H._owes_here(run, "anything"), "a push with an UNKNOWN change set kept another tree's word")
        run.direct = {"changed"}
        self.assertTrue(H._owes_here(run, "changed"))
        self.assertFalse(H._owes_here(run, "untouched"))

    def test_a_push_never_asks_the_trust_pass_and_judges_nothing_here(self):
        seen = {}

        def push(have, say, stopped, cache=None, blank=None):
            seen["names"] = sorted(n for n, _f, _p in have)
            seen["here"] = set(H._CENSUS.get("here") or ())
            return dict((n, H.PROVEN) for n in seen["names"]), {}
        with mock.patch.object(H, "trust_pass", mock.Mock(side_effect=AssertionError("a push asked the trust pass"))), \
                mock.patch.object(H, "open_cache", lambda say=print: None), \
                mock.patch.object(H, "_prove_push", push), \
                mock.patch.dict(H._SHARD, {"spec": None}):
            H.prove(say=QUIET, push=True)
        self.assertEqual(seen, {"names": ["js", "moved", "plain"], "here": set()})

    def test_the_push_serve_still_takes_another_trees_proof(self):
        e = dict(_entry(CI_TREE), inputs=[])

        class C(object):
            n = {}

            def key_for(s, *a, **k):
                return "key", [], None

            def peek(s, key):
                return e

            def lookup(s, key):
                return e

            def count(s, what):
                pass

            def count_carried(s, by):
                pass

            def reused_at(s, *a):
                pass

            def say_once(s, *a):
                pass
        self.assertEqual(H._cache_serve(C(), HERE, "g", "g.py", P0, 0, QUIET)[0], H.PROVEN)
        self.assertIsNone(H._cache_serve(C(), HERE, "g", "g.py", P0, 0, QUIET, own_only=True)[0],
                          "the self-check was served another tree's PROVEN")


class TheTrustRunsWithoutASlice(_Census):

    def _main(self, argv, rc=0):
        calls = []
        with mock.patch.object(H, "_census_cache", lambda reuse, say=print: self.bank), \
                mock.patch.object(H, "import_shards", lambda paths, say=print, target=None: calls.append(paths) or rc):
            got = H.main(argv)
        return got, calls

    def test_trust_alone_writes_what_the_bank_serves(self):
        got, _c = self._main(["--trust"])
        self.assertEqual(got, 0)
        self.assertIn("plain", self.census()["trusted"], "`heart2.py --trust` wrote nothing")

    def test_an_import_that_landed_runs_it_and_a_refused_one_does_not(self):
        got, calls = self._main(["--trust", "--import-shards", "a.json"], rc=2)
        self.assertEqual((got, calls), (2, [["a.json"]]))
        self.assertFalse(os.path.exists(self.state), "a REFUSED import wrote the census on the bank's word")
        got, calls = self._main(["--trust", "--import-shards", "a.json"], rc=0)
        self.assertEqual(got, 0)
        self.assertIn("plain", self.census()["trusted"], "the import landed and the locks still wait for a slice")

    def test_the_update_import_asks_for_the_trust_pass(self):
        b = os.path.join(self.d, "bundle.tgz")
        src = os.path.join(self.d, "s.json")
        with io.open(src, "w", encoding="utf-8") as fh:
            fh.write("{}")
        with tarfile.open(b, "w:gz") as t:
            t.add(src, arcname="proof-shard-1/.heart2_cache.json")
        with io.open(b, "rb") as fh:
            data = fh.read()

        class R(object):
            def __init__(s):
                s.buf = io.BytesIO(data)

            def read(s, n=-1):
                return s.buf.read(n)

            def __enter__(s):
                return s

            def __exit__(s, *a):
                return False
        seen = {}

        def run(argv, **kw):
            seen["argv"] = list(argv)
            return subprocess.CompletedProcess(argv, 0, "  REG-2586 IMPORTED 1 shard(s)", "")
        PR.import_bundle("c" * 40, tv_dir=HERE, run=run, urlopen=lambda req, timeout=None: R())
        argv = seen.get("argv") or []
        self.assertIn("--import-shards", argv)
        self.assertIn("--trust", argv, "the update-time import does not open the locks - they wait for an idle slice")


class TheLaneStartsTheTrustPassWhenASliceIsHeld(unittest.TestCase):

    STALE = {"state": "stale", "why": "x", "trustSig": "FP|1|2", "owedGates": [("g", 1)], "fingerprint": "FP"}

    def decide(self, census=None, mem=None, **kw):
        a = dict(running_pid=None, busy_pct=99.0, now_s=1.0e9, playing=False, free=99999.0, tree=("installed", ""))
        a.update(kw)
        return SP.decide(dict(self.STALE) if census is None else census, a.pop("tree"), a.pop("running_pid"),
                         a.pop("busy_pct"), mem or {}, a.pop("now_s"), **a)

    def test_a_busy_pc_starts_the_trust_pass(self):
        d = self.decide()
        self.assertEqual((d["start"], d["key"], d.get("trust")), (True, "trust", True), d)
        for kw in ({"takes_only": True}, {"free": float(SP.MIN_FREE_MB_TO_START - 1)}):
            self.assertEqual(self.decide(**kw)["key"], "trust", "a slice held by %s held the trust pass too" % kw)

    def test_never_twice_for_one_bank(self):
        self.assertEqual(self.decide(mem={"trustFor": "FP|1|2"})["key"], "busy")
        self.assertEqual(self.decide(mem={"trustFor": "FP|1|1"})["key"], "trust", "a bank that grew was not read")

    def test_never_beside_his_game_on_a_guess_in_a_dev_tree_or_an_environment_reprove(self):
        self.assertEqual(self.decide(playing=True)["key"], "playing")
        self.assertFalse(self.decide(playing=None)["start"])
        # a slice held by a backoff or by takes-only is refused BEFORE his game is asked: the trust pass asks it itself
        backoff = {"lastFailAt": 1.0e9 - 60, "lastFailFingerprint": "FP", "lastFailKind": "proof"}
        for kw in ({"mem": backoff}, {"takes_only": True}):
            for playing in (True, None):
                d = self.decide(playing=playing, **kw)
                self.assertFalse(d["start"], "the trust pass started beside his game (%s, playing %r): %s"
                                 % (kw, playing, d))
        self.assertFalse(self.decide(tree=("dev", "x"))["start"])
        self.assertEqual(self.decide(census=dict(self.STALE, envReprove=True))["key"], "busy",
                         "the trust pass served old-environment proofs during an environment re-prove")
        self.assertEqual(self.decide(free=float(SP.TRUST_MIN_FREE_MB - 1))["key"], "low-memory")
        self.assertEqual(self.decide(census={"state": "current", "why": "ok"})["key"], "current")

    def test_an_idle_pc_proves_its_slice_as_before(self):
        self.assertEqual(self.decide(busy_pct=0.0)["key"], "start", "an idle PC ran a trust pass instead of its slice")

    def test_the_tick_spawns_it_alone_and_books_its_end_as_neither_proof_nor_failure(self):
        d = tempfile.mkdtemp(prefix="reg3191-sp-")
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "sp.json")
        calls = []

        def spawn(log_path, names=None, workers=None, trust=False, net=False):
            calls.append({"names": names, "trust": trust, "net": net})
            return 4242
        with mock.patch.object(SP, "proc_birth", lambda pid: 1.0), \
                mock.patch.object(SP, "identity", lambda pid, birth: True):
            st = SP.tick(now_s=1.0e9, busy=99.0, tree=("installed", ""), census=dict(self.STALE), path=path,
                         spawn_fn=spawn, env={"TV_SELF_PROVE": "1"}, playing=False, free=99999.0)
        self.assertEqual(calls, [{"names": None, "trust": True, "net": False}], "the lane did not start the trust pass")
        self.assertEqual(st["key"], "trust")
        mem = SP.load(path)
        self.assertEqual((mem.get("trust"), mem.get("trustFor")), (True, "FP|1|2"))
        with mock.patch.object(SP, "identity", lambda pid, birth: False):
            st = SP.tick(now_s=1.0e9 + 60, busy=99.0, tree=("installed", ""), census=dict(self.STALE), path=path,
                         spawn_fn=spawn, env={"TV_SELF_PROVE": "1"}, playing=False, free=99999.0)
        mem = SP.load(path)
        self.assertEqual(mem.get("trustWorked"), 1, "the trust run's end was not booked as a trust run")
        self.assertIsNone(mem.get("lastFailAt"), "a trust run's end was booked as a failed proof (a 3 h backoff)")
        self.assertEqual(st["trust"]["owed"], 0)
        self.assertEqual(len(calls), 1, "the same bank was read twice")

    def test_its_spawn_runs_no_law(self):
        got = []

        class P(object):
            pid = 4242
        d = tempfile.mkdtemp(prefix="reg3191-sp-")
        self.addCleanup(shutil.rmtree, d, True)
        SP.spawn(os.path.join(d, "log"), workers=1, popen=lambda cmd, **kw: got.append(list(cmd)) or P(), trust=True)
        cmd = got[0]
        self.assertEqual(cmd[-2:], [os.path.join(SP.HERE, "heart2.py"), "--trust"], cmd)
        self.assertNotIn("--prove", cmd, "the trust run proves laws")

    def test_the_census_signature_moves_with_the_bank(self):
        tmp = tempfile.mkdtemp(prefix="reg3191-sig-")
        self.addCleanup(shutil.rmtree, tmp, True)
        bank = os.path.join(tmp, "bank.json")
        with io.open(bank, "w", encoding="utf-8") as fh:
            fh.write("{}")

        class H2(object):
            CACHE = bank
        a = SP._trust_sig(H2, "FP")
        with io.open(bank, "w", encoding="utf-8") as fh:
            fh.write('{"entries": {"k": 1}}')
        b = SP._trust_sig(H2, "FP")
        self.assertTrue(a and b and a != b, "an import that grew the bank left the trust signature where it was: %r %r"
                        % (a, b))
        H2.CACHE = os.path.join(tmp, "absent.json")
        self.assertIsNone(SP._trust_sig(H2, "FP"), "an unreadable bank gave a signature - a trust run on a guess")


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
    {"why": "REG-3191 - a BLIND a slice filed while the keys were taken is overwritten (no re-read under the lock)",
     "file": "tv/heart2.py",
     "find": "            take = [n for n in take if n in _still and n not in _fb]\n",
     "replace": "            take = list(take)\n",
     "matches": 1},
    {"why": "REG-3191 - a trusted gate is stamped with this run's clock, not the age it was measured at",
     "file": "tv/heart2.py",
     "find": "                                      measured=dict((n, sp[\"ages\"][n]) for n in take if n in sp[\"ages\"]),\n",
     "replace": "                                      measured=None,\n",
     "matches": 1},
    {"why": "REG-3191 - the census does not record which gates stand on another tree's proofs",
     "file": "tv/heart2.py",
     "find": "        if _n in _trq and _n not in _unm:\n            _tr[_n] = _shas.get(_n)\n",
     "replace": "        if False:\n            _tr[_n] = _shas.get(_n)\n",
     "matches": 1},
    {"why": "REG-3191 - an open environment re-prove still asks the bank (old-environment proofs served)",
     "file": "tv/heart2.py",
     "find": "    if _er and _er.get(\"owed\"):\n        say(\"  REG-3191 TRUST PASS: not asked",
     "replace": "    if False:\n        say(\"  REG-3191 TRUST PASS: not asked",
     "matches": 1},
    {"why": "REG-3191 - the census serve hands the self-check gates another tree's PROVEN",
     "file": "tv/heart2.py",
     "find": "            if own_only and _own is not None and _own.get(\"tree\") != TREE_ID:\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-3191 - prove() stops naming the environment self-check gates (judged on another tree's word)",
     "file": "tv/heart2.py",
     "find": "            _CENSUS[\"here\"] = set(n for n, _f, _p in have if env_gate(n, _p)[0])   # the environment self-check\n",
     "replace": "            _CENSUS[\"here\"] = set()\n",
     "matches": 1},
    {"why": "REG-3191 - prove() asks the trust pass but writes nothing (the reviewer's sabotage: the feature dead)",
     "file": "tv/heart2.py",
     "find": "                _tp = trust_pass(_CENSUS[\"cache\"], say=say, gates=gates) or {}\n",
     "replace": "                _tp = trust_pass(_CENSUS[\"cache\"], say=say, gates=gates, write=False) or {}\n",
     "matches": 1},
    {"why": "REG-3191 - the slice re-proves the gates the trust pass wrote",
     "file": "tv/heart2.py",
     "find": "            have = [(n, f, p) for n, f, p in have if n not in _trusted]\n",
     "replace": "            have = list(have)\n",
     "matches": 1},
    {"why": "REG-2599 (push path unchanged) - a push asks the trust pass",
     "file": "tv/heart2.py",
     "find": "        _cache = open_cache(say)\n        results, per_proof = _prove_push(have, say, stopped, cache=_cache, blank=_blank)\n",
     "replace": "        _cache = open_cache(say)\n        trust_pass(_cache, say=say, gates=gates)\n        results, per_proof = _prove_push(have, say, stopped, cache=_cache, blank=_blank)\n",
     "matches": 1},
    {"why": "REG-2599 (push path unchanged) - a push with an UNKNOWN change set keeps another tree's word",
     "file": "tv/heart2.py",
     "find": "    return direct is None or name in direct\n",
     "replace": "    return direct is not None and name in direct\n",
     "matches": 1},
    {"why": "REG-3191 - `heart2.py --trust` alone does nothing",
     "file": "tv/heart2.py",
     "find": "    if a.trust and a.prove is None:\n        return trust_now()",
     "replace": "    if False:\n        return trust_now()",
     "matches": 1},
    {"why": "REG-3191 - an import that landed leaves the locks waiting for a slice",
     "file": "tv/heart2.py",
     "find": "        if _irc == 0 and a.trust:\n            trust_now()                          # REG-3191 - the import's proofs",
     "replace": "        if False:\n            trust_now()                          # REG-3191 - the import's proofs",
     "matches": 1},
    {"why": "REG-3191 - a REFUSED import still writes the census on the bank's word",
     "file": "tv/heart2.py",
     "find": "        if _irc == 0 and a.trust:\n            trust_now()                          # REG-3191 - the import's proofs",
     "replace": "        if a.trust:\n            trust_now()                          # REG-3191 - the import's proofs",
     "matches": 1},
    {"why": "REG-3191 - the update-time import does not ask for the trust pass",
     "file": "tv/proof_release.py",
     "find": "\"heart2.py\"), \"--trust\", \"--import-shards\"] + paths,",
     "replace": "\"heart2.py\"), \"--import-shards\"] + paths,",
     "matches": 1},
    {"why": "REG-3191 - a busy PC holds the trust pass like a slice (the measured 34 min)",
     "file": "tv/self_prove.py",
     "find": "TRUST_DESPITE = (\"busy\", ",
     "replace": "TRUST_DESPITE = (\"busy-never\", ",
     "matches": 1},
    {"why": "REG-3191 - the trust pass starts beside his game",
     "file": "tv/self_prove.py",
     "find": "    if playing is not False:\n        return None\n    try:\n        free = float(free)\n",
     "replace": "    if False:\n        return None\n    try:\n        free = float(free)\n",
     "matches": 1},
    {"why": "REG-3191 - the same bank is read again and again (no signature)",
     "file": "tv/self_prove.py",
     "find": "    if not sig or sig == (mem or {}).get(\"trustFor\"):\n",
     "replace": "    if not sig:\n",
     "matches": 1},
    {"why": "REG-3191 - the trust pass runs during an environment re-prove",
     "file": "tv/self_prove.py",
     "find": "    if c.get(\"state\") not in (\"stale\", \"missing\") or c.get(\"envReprove\"):\n",
     "replace": "    if c.get(\"state\") not in (\"stale\", \"missing\"):\n",
     "matches": 1},
    {"why": "REG-3191 - the tick never records which bank it read, so it starts a trust run every tick",
     "file": "tv/self_prove.py",
     "find": "                mem[\"trustFor\"] = census.get(\"trustSig\")",
     "replace": "                mem[\"trustFor\"] = None",
     "matches": 1},
    {"why": "REG-3191 - a trust run's end is booked as a failed proof (a 3 h backoff on every slice)",
     "file": "tv/self_prove.py",
     "find": "        elif mem.get(\"trust\"):\n            # REG-3191 - the trust run ended",
     "replace": "        elif False:\n            # REG-3191 - the trust run ended",
     "matches": 1},
    {"why": "REG-3191 - the trust run proves the whole census instead of running no law",
     "file": "tv/self_prove.py",
     "find": "[os.path.join(HERE, \"heart2.py\"), \"--trust\"]   # REG-3191 - no law runs",
     "replace": "[os.path.join(HERE, \"heart2.py\"), \"--prove\", \"--trust\"]   # REG-3191 - no law runs",
     "matches": 1},
    {"why": "REG-3191 - the trust signature ignores the bank, so an import never starts a trust run",
     "file": "tv/self_prove.py",
     "find": "        return \"%s|%d|%d\" % (fp, int(bst.st_mtime_ns), int(bst.st_size))\n",
     "replace": "        return \"%s\" % (fp,)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
