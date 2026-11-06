# -*- coding: utf-8 -*-
"""v3862 (item 4) - A PC WHOSE ENVIRONMENT CHANGED PROVES EVERY LAW ONCE AGAIN, WITHOUT THE CACHE; NOTHING ELSE DOES.

His ruling 2026-11-05 (the normal model): GitHub proves each version once, each PC imports - and "a full proof once per
PC or when its environment changes". Before this, nothing re-proved on an environment change: the census owes a gate only
when its own test file changes (gateShas), and the proof cache keys on file bytes alone, so a PC moved from python 3.9 to
3.12 (or a Windows feature update, or node arriving) kept serving every proof it had earned under the old one. Pinned:
  · the fingerprint is UNKNOWN (None) when any part cannot be read - a timed-out `node --version` is never a change;
  · the first reading is ADOPTED (rollout owes nothing); a change opens a pending re-prove; back to the proved one drops it;
  · while it is open every declaring gate not proved SINCE the change is owed (slice_owed), and the census reads STALE;
  · the slices of a re-prove run WITHOUT --reuse (a proof earned under the old environment proves nothing new);
  · the lock reads the re-prove beside the census IT read (a law's fixture never meets his real record);
  · with nothing left owed the new fingerprint becomes the PC's.
Driven on fixture records in a scratch dir and stand-in runtimes - never his census, never his environment file.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import heart2 as H  # noqa: E402

T0 = 1_800_000_000_000
RT = {"platform": "darwin", "python": "3.9", "node": "22"}


def _git(ok=True, out="false\n"):
    return lambda *a: (ok, out)


class TheFingerprint(unittest.TestCase):

    def test_known_parts_make_one_and_a_change_moves_it(self):
        a, pa = H.env_fingerprint(runtime=RT, os_build=lambda: "25", git=_git())
        b, _pb = H.env_fingerprint(runtime=dict(RT, python="3.12"), os_build=lambda: "25", git=_git())
        self.assertTrue(a and b and a != b, "a python upgrade left the fingerprint where it was")
        self.assertEqual(pa["autocrlf"], "false")

    def test_a_reading_stands_its_ttl_then_is_taken_again(self):
        """REG-3264 - node placed on this process's PATH at first boot never reached env_observe until a relaunch."""
        saved = dict(H._ENV_FP)
        calls = []
        real = H.export_runtime
        try:
            H._ENV_FP.clear()
            H.export_runtime = lambda which=None, run=None: calls.append(1) or dict(RT, node="none" if len(calls) == 1 else "22")
            real_os, real_git = H._os_build, H._git
            H._os_build, H._git = (lambda: "25"), _git()
            try:
                a = H.env_fingerprint(now=1000.0)
                b = H.env_fingerprint(now=1000.0 + 60)
                self.assertEqual(a, b, "a reading did not stand inside its TTL")
                self.assertEqual(len(calls), 1)
                c = H.env_fingerprint(now=1000.0 + H.ENV_FP_TTL_S + 1)
                self.assertEqual(len(calls), 2, "the environment was never read again in this process")
                self.assertNotEqual(c[0], a[0], "node placed mid-process did not move the fingerprint")
            finally:
                H._os_build, H._git = real_os, real_git
        finally:
            H.export_runtime = real
            H._ENV_FP.clear()
            H._ENV_FP.update(saved)

    def test_any_unknown_part_is_no_fingerprint(self):
        for rt, osb, git in ((dict(RT, node=None), lambda: "25", _git()),
                             (RT, lambda: None, _git()),
                             (RT, lambda: "25", _git(ok=False, out=""))):
            with self.subTest(rt=rt):
                self.assertIsNone(H.env_fingerprint(runtime=rt, os_build=osb, git=git)[0],
                                  "an unreadable part became a fingerprint - a timeout would read as a change")

    def test_node_absent_is_a_known_part(self):
        self.assertIsNotNone(H.env_fingerprint(runtime=dict(RT, node="none"), os_build=lambda: "25", git=_git())[0])


class TheRecord(unittest.TestCase):

    def test_the_first_reading_is_adopted_and_the_same_one_writes_nothing(self):
        rec = H.env_step({}, "aaa", {"python": "3.9"}, T0)
        self.assertEqual(rec["fingerprint"], "aaa")
        self.assertNotIn("pending", rec, "rollout opened a re-prove of every law on every PC")
        self.assertIsNone(H.env_step(rec, "aaa", {}, T0 + 1))

    def test_a_change_opens_one_re_prove_and_a_return_drops_it(self):
        rec = {"fingerprint": "aaa", "parts": {"python": "3.9"}}
        rec2 = H.env_step(rec, "bbb", {"python": "3.12"}, T0)
        self.assertEqual((rec2["pending"], rec2["since"]), ("bbb", T0))
        self.assertIsNone(H.env_step(rec2, "bbb", {}, T0 + 5), "the open re-prove restarted its clock")
        back = H.env_step(rec2, "aaa", {}, T0 + 9)
        self.assertNotIn("pending", back, "a PC back on the environment it proved under still re-proves")

    def test_unknown_or_unreadable_changes_nothing(self):
        self.assertIsNone(H.env_step({"fingerprint": "aaa"}, None, {}, T0))
        self.assertIsNone(H.env_step(None, "bbb", {}, T0), "an unreadable record was written over")

    def test_what_is_owed_and_when_it_is_done(self):
        rec = {"fingerprint": "aaa", "parts": {"python": "3.9"}, "pending": "bbb", "pendingParts": {"python": "3.12"},
               "since": T0}
        st = {"verdictAt": {"g1": T0 - 1, "g2": T0 + 1}}
        self.assertEqual(H.env_owed(st, rec, ["g1", "g2", "g3"]), ["g1", "g3"])
        self.assertEqual(H.env_owed(st, {"fingerprint": "aaa"}, ["g1"]), [], "a steady PC owed a re-prove")
        self.assertIsNone(H.env_finish(rec, ["g1"]))
        done = H.env_finish(rec, [])
        self.assertEqual(done["fingerprint"], "bbb")
        self.assertNotIn("pending", done)
        self.assertEqual(H.env_change_words({"from": {"python": "3.9"}, "to": {"python": "3.12"}}),
                         "python 3.9 -> 3.12")


class TheCensusOwesIt(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="env-reprove-")
        self._state = H.STATE
        H.STATE = os.path.join(self.d, ".heart2.json")
        H._ENV_HAVE.update(at=0.0, have=None)
        self.gates = [(n, f) for n, f in H.gate_files(say=lambda *a, **k: None)
                      if n in ("test_a_pc_reproves_when_its_environment_changes", "test_known_errors_fix_themselves")]
        self.assertEqual(len(self.gates), 2, "PREMISE: the two fixture gates are registered")
        self.shas = H.gate_shas(self.gates)

    def tearDown(self):
        H.STATE = self._state
        H._ENV_HAVE.update(at=0.0, have=None)
        shutil.rmtree(self.d, ignore_errors=True)

    def _env(self, rec):
        with io.open(os.path.join(self.d, H.ENV_NAME), "w", encoding="utf-8") as fh:
            json.dump(rec, fh)

    def test_an_open_re_prove_owes_the_gates_not_proved_since(self):
        st = {"gateShas": dict(self.shas), "verdictAt": {n: T0 - 10 for n, _f in self.gates}}
        self.assertEqual(H.slice_owed(self.gates, st)["owed"], [], "PREMISE: the fixture census owes nothing")
        self._env({"fingerprint": "aaa", "parts": {"python": "3.9"}, "pending": "bbb",
                   "pendingParts": {"python": "3.12"}, "since": T0})
        got = H.slice_owed(self.gates, st)
        self.assertEqual(sorted(n for n, _k in got["owed"]), sorted(n for n, _f in self.gates))
        self.assertIn("environment changed", got["why"])
        st["verdictAt"] = {n: T0 + 10 for n, _f in self.gates}
        self.assertEqual(H.slice_owed(self.gates, st)["owed"], [], "a gate proved since the change is still owed")

    def test_another_census_dir_never_reads_this_record(self):
        other = tempfile.mkdtemp(prefix="env-other-")
        try:
            self._env({"fingerprint": "aaa", "pending": "bbb", "since": T0})
            st = {"gateShas": dict(self.shas), "verdictAt": {}}
            self.assertEqual(H.slice_owed(self.gates, st, env_path=os.path.join(other, H.ENV_NAME))["owed"], [],
                             "a fixture census read another directory's environment record")
        finally:
            shutil.rmtree(other, ignore_errors=True)


class TheLaneProvesItWithoutTheCache(unittest.TestCase):

    def test_a_re_prove_slice_drops_reuse(self):
        import self_prove as SP
        seen = []

        class _P:
            pid = 4242

        def popen(cmd, **kw):
            seen.append(list(cmd))
            return _P()
        d = tempfile.mkdtemp(prefix="env-spawn-")
        try:
            log = os.path.join(d, "p.log")
            SP.spawn(log, workers=1, popen=popen, names=["g1"])
            SP.spawn(log, workers=1, popen=popen, names=["g1"], reuse=False)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertIn("--reuse", seen[0], "PREMISE: a slice serves banked proofs")
        self.assertNotIn("--reuse", seen[1], "a re-prove served proofs earned under the old environment")

    def test_the_tick_spawns_with_the_census_answer(self):
        with io.open(os.path.join(HERE, "self_prove.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('_spawn_real = _ft.partial(spawn, reuse=not census.get("envReprove"))', src)
        self.assertEqual(src.count("(spawn_fn or spawn)("), 0, "a real spawn bypasses the re-prove's no-reuse")
        self.assertIn("_env_observe()                      # v3862 (item 4)", src)


class TheLockReadsIt(unittest.TestCase):
    """v3866 (the #231 eye on v3862: "self_arming._heart_says_watched fails open") - the lock's environment branch, driven
    through the real _heart_says_watched() on a census file whose every earlier check passes (its TV_HEART_CENSUS seam).
    An open re-prove is STALE; a record whose state cannot be told fails CLOSED - it was None, the answer for "none
    open", so the lock armed over it."""

    def setUp(self):
        import self_arming as SA
        self.SA = SA
        self.d = tempfile.mkdtemp(prefix="env-lock-")
        self.p = os.path.join(self.d, ".heart2.json")
        with io.open(self.p, "w", encoding="utf-8") as fh:
            json.dump({"gatesFingerprint": "fp-law", "blind": [], "verdictAt": {}}, fh)
        self.saved = os.environ.get("TV_HEART_CENSUS")
        os.environ["TV_HEART_CENSUS"] = self.p
        self.fp = mock.patch.object(H, "gates_fingerprint", lambda: "fp-law")
        self.fp.start()
        H._ENV_HAVE.update(at=0.0, have=None)

    def tearDown(self):
        self.fp.stop()
        if self.saved is None:
            os.environ.pop("TV_HEART_CENSUS", None)
        else:
            os.environ["TV_HEART_CENSUS"] = self.saved
        H._ENV_HAVE.update(at=0.0, have=None)
        shutil.rmtree(self.d, ignore_errors=True)

    def _env(self, raw):
        with io.open(os.path.join(self.d, H.ENV_NAME), "w", encoding="utf-8") as fh:
            fh.write(raw)

    def test_no_record_says_nothing_about_the_environment(self):
        _ok, why = self.SA._heart_says_watched()
        self.assertNotIn("environment", str(why), "a PC with no environment record was refused over it: %r" % why)

    def test_an_open_re_prove_reads_stale(self):
        self._env(json.dumps({"fingerprint": "aaa", "parts": {"python": "3.9"}, "pending": "bbb",
                              "pendingParts": {"python": "3.12"}, "since": T0}))
        ok, why = self.SA._heart_says_watched()
        self.assertFalse(ok)
        self.assertIn("environment changed", why)
        self.assertEqual(self.SA.heart_block_kind(why), "stale")

    def test_a_record_that_will_not_parse_fails_closed(self):
        self._env("{ not json")
        self.assertEqual(H.env_reprove_state({}, path=os.path.join(self.d, H.ENV_NAME)).get("owed"), None)
        ok, why = self.SA._heart_says_watched()
        self.assertFalse(ok, "the lock armed while whether this PC's environment changed could not be told")
        self.assertIn("cannot be told", why)
        self.assertEqual(self.SA.heart_block_kind(why), "other", "UNKNOWN was softened to a prover catching up: %r" % why)

    def test_a_failure_after_a_pending_record_is_found_fails_closed(self):
        self._env(json.dumps({"fingerprint": "aaa", "pending": "bbb", "since": T0}))
        with mock.patch.object(H, "env_owed", side_effect=RuntimeError("boom")):
            er = H.env_reprove_state({}, path=os.path.join(self.d, H.ENV_NAME))
            self.assertEqual((er.get("owed"), "could not be read" in er.get("unknown", "")), (None, True), er)
            ok, why = self.SA._heart_says_watched()
        self.assertFalse(ok)
        self.assertIn("cannot be told", why)


RED_PROOF = [
    {"why": "REG-3264 - one reading of the environment stands for the life of the process again",
     "file": "tv/heart2.py",
     "find": "            and _now - float(_ENV_FP.get(\"at\") or 0) < ENV_FP_TTL_S):\n",
     "replace": "            ):\n",
     "matches": 1},
    {"why": "v3866 (#231 on v3862) - an environment record that will not parse reads as 'no re-prove open', so locks arm",
     "file": "tv/heart2.py",
     "find": "        if rec is None:\n            return {\"owed\": None, \"unknown\": \"this PC's environment record exists and will not parse\"}\n",
     "replace": "",
     "matches": 1},
    {"why": "v3866 (#231 on v3862) - a failure after a pending record is found reads as 'none open'",
     "file": "tv/heart2.py",
     "find": "        return {\"owed\": None, \"unknown\": \"the open environment re-prove could not be read (%s)\" % type(e).__name__}\n",
     "replace": "        return None\n",
     "matches": 1},
    {"why": "v3866 (#231 on v3862) - the lock reads 'cannot be told' as permission (fails open)",
     "file": "tv/self_arming.py",
     "find": "    if _er and _er.get(\"unknown\"):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3862 - a part that could not be read becomes a fingerprint (a timeout re-proves every law)",
     "file": "tv/heart2.py",
     "find": "    if all(parts.get(k) not in (None, \"\") for k in ENV_KEYS):\n",
     "replace": "    if True:\n",
     "matches": 1},
    {"why": "v3862 - the rollout opens a re-prove of every law on every PC",
     "file": "tv/heart2.py",
     "find": "    if not rec.get(\"fingerprint\"):\n        return {\"fingerprint\": cur, \"parts\": dict(parts or {}), \"adoptedAt\": int(now_ms)}\n",
     "replace": "    if not rec.get(\"fingerprint\"):\n        return {\"fingerprint\": \"\", \"pending\": cur, \"since\": int(now_ms)}\n",
     "matches": 1},
    {"why": "v3862 - an environment change owes nothing: proofs earned under the old one keep serving",
     "file": "tv/heart2.py",
     "find": "    if _er and _er.get(\"owed\"):\n        _have_n = {n for n, _k in owed}\n",
     "replace": "    if False:\n        _have_n = {n for n, _k in owed}\n",
     "matches": 1},
    {"why": "v3862 - a re-prove slice serves the cache",
     "file": "tv/self_prove.py",
     "find": "           + ([\"--reuse\"] if reuse else []))\n",
     "replace": "           + [\"--reuse\"])\n",
     "matches": 1},
    {"why": "v3862 - a gate proved since the change is still owed (the re-prove never ends)",
     "file": "tv/heart2.py",
     "find": "    return sorted(n for n in have if not (isinstance(seen.get(n), (int, float)) and seen.get(n) >= since))\n",
     "replace": "    return sorted(have)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
