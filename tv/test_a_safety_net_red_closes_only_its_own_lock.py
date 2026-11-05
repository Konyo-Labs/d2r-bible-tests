# -*- coding: utf-8 -*-
"""REG-3192 (his ruling 2026-11-05 ~09:15, item 4: "the background full proof keeps running at idle as a SAFETY NET but no
longer holds the river shut - a red/blind it finds goes to the fleet + BUGS and closes only the lock its law guards").

REG-3191 writes a gate into the census on another tree's proofs over byte-identical inputs (`trusted`). The safety net is
the self-prove lane's idle run of exactly those gates ON THIS PC, once the census is current, lowest priority, behind every
stand-aside rule. What it finds must not undo the point of REG-3191 (MEASURED 2026-11-05: after every ship each PC's river
stayed shut ~1 h on his Mac, 28 days on the old ALT, until every changed law re-proved locally) - so it is held here:
  * a clean run RED here, a BLIND, an INVALID: recorded per gate in `netFinds` with its sha, verdict and a BUGS-ready line -
    and NEVER in the census's `blind`, `gateShas` or fingerprint, so the census does not go stale and every other lock
    stays as it was (his 2026-09-12 "a BLIND closes every lock" ruling stands for every other BLIND);
  * a find closes ONLY the lock(s) whose guard set holds its law (#156's _guards_lock), never an unrelated lock, and it is
    never softened like a STALE census for an ordinary act; a find on a file that has since changed is moot;
  * a gate the net proves here leaves `trusted`;
  * the lane starts the net only over a CURRENT census with trusted gates owed, never beside his game, never starving its
    way in on a busy machine, and spawns it as `--net` over named gates only; the lane's status carries the net
    (on / worked / lastTs / owed) and its finds, so they reach the fleet.
Fixtures only: fixture gate files, a fixture census (TV_HEART_CENSUS / heart2.STATE). RED_PROOF below.
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
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import heart2 as H  # noqa: E402
import self_arming as SA  # noqa: E402
import self_prove as SP  # noqa: E402

_PR = 'RED_PROOF = [{"why": "w", "file": "tv/x.py", "find": "a", "replace": "b", "matches": 1}]\n'
SOURCES = {
    "g_frame": "import reel_retention\n" + _PR,          # guards frame.release (its door module)
    "g_print": "import printer\n" + _PR,                 # guards printer.stream
    "g_ok": "import printer\n" + _PR,
    "g_blind": "import printer\n" + _PR,
    "g_idle": "import printer\n" + _PR,
}


class _Fixture(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="reg3192-")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.state = os.path.join(self.d, ".heart2.json")
        self.gates = []
        for n, src in sorted(SOURCES.items()):
            p = os.path.join(self.d, "%s.py" % n)
            with io.open(p, "w", encoding="utf-8") as fh:
                fh.write(src)
            self.gates.append((n, p))
        self.shas = H.gate_shas(self.gates)
        gates = self.gates
        for patch in (mock.patch.object(H, "STATE", self.state),
                      mock.patch.object(H, "gate_files", lambda say=print: list(gates)),
                      mock.patch.object(H, "surface_verdict", lambda *a, **k: None),
                      mock.patch.dict(os.environ, {"TV_HEART_CENSUS": self.state}),
                      mock.patch.dict(SA._NET_MEMO, {"key": None, "finds": None, "files": None})):
            patch.start()
            self.addCleanup(patch.stop)

    def write(self, body):
        with io.open(self.state, "w", encoding="utf-8") as fh:
            json.dump(body, fh)

    def census(self):
        with io.open(self.state, encoding="utf-8") as fh:
            return json.load(fh)

    def current(self, **extra):
        body = {"gateShas": dict(self.shas), "gatesFingerprint": "FP", "blind": [], "provedGates": sorted(self.shas),
                "trusted": dict(self.shas)}
        body.update(extra)
        return body


class TheNetWritesOnlyItsOwnRecord(_Fixture):

    def test_a_red_or_blind_is_a_find_and_never_the_censuss_blind(self):
        self.write(self.current())
        H._write_net({"g_frame": H.UNPROVABLE, "g_blind": H.BLIND, "g_ok": H.PROVEN, "g_idle": H.UNPROVABLE},
                     red={"g_frame"})
        st = self.census()
        self.assertEqual(sorted(st["netFinds"]), ["g_blind", "g_frame"])
        self.assertEqual(st["netFinds"]["g_frame"]["verdict"], "RED", "a clean run RED here was not recorded")
        self.assertEqual(st["netFinds"]["g_blind"]["verdict"], H.BLIND, "a BLIND here was not recorded")
        self.assertEqual(st["netFinds"]["g_frame"]["sha"], self.shas["g_frame"])
        line = st["netFinds"]["g_frame"]["line"]
        self.assertTrue(line.startswith("### REG-NNNN - THE SAFETY NET FOUND g_frame RED"), line)
        self.assertIn("python3 tv/heart2.py --prove g_frame", line)
        line.encode("ascii")                                    # it travels to Windows consoles
        self.assertEqual(st["blind"], [], "a safety-net find joined the census's BLIND list - every lock would close")
        self.assertEqual(st["gateShas"], self.shas, "a safety-net find moved a gate sha - the census would go stale")
        self.assertEqual(st["gatesFingerprint"], "FP")
        self.assertNotIn("g_ok", st["trusted"], "a gate proved here still reads as another tree's word")
        self.assertIn("g_idle", st["netUnjudged"], "an UNPROVABLE that was not RED became a find")
        self.assertNotIn("g_idle", st["netFinds"])

    def test_a_find_on_a_file_that_changed_since_is_not_written(self):
        self.write(self.current(gateShas=dict(self.shas, g_frame="older")))
        H._write_net({"g_frame": H.BLIND})
        self.assertNotIn("g_frame", self.census()["netFinds"])

    def test_a_lane_that_never_measured_the_gate_files_no_find(self):
        self.write(self.current())
        H._write_net({"g_blind": H.BLIND}, unmeasured={"g_blind"})
        self.assertEqual(self.census()["netFinds"], {})


class TheNetLearnsARedCleanRun(unittest.TestCase):
    """A clean run RED here is read from the gate's own shared clean-run record (REG-1669), so the census path calls the
    prover exactly as before and only a net run turns it into a find."""

    def _gate(self, net, ok):
        def proofs(sandbox, name, filename, prs, say):
            H._CLEAN.runs[("g.py",)] = {"ok": ok, "tail": "red: case_x", "reused": 0}
            return [H.UNPROVABLE if ok is False else H.PROVEN]
        with mock.patch.object(H, "_prove_gate_proofs", proofs), \
                mock.patch.object(H, "_reset_lane_records", lambda *a, **k: None), \
                mock.patch.dict(H._CENSUS, {"cache": None, "here": (), "red": set(), "net": net}):
            H._prove_gate(HERE, "g_frame", "g.py", [{"find": "a"}], lambda *a: None)
            return set(H._CENSUS["red"])

    def test_a_red_clean_run_on_a_net_run_is_recorded(self):
        self.assertEqual(self._gate(True, False), {"g_frame"},
                         "the net's RED clean run was not recorded, so it can never be a find")

    def test_a_green_clean_run_or_a_census_run_records_nothing(self):
        self.assertEqual(self._gate(True, True), set())
        self.assertEqual(self._gate(False, False), set(), "a census run (not the net) recorded a red for the net")


class AFindClosesOnlyTheLockItsLawGuards(_Fixture):

    def find(self, gate, sha=None):
        self.write(self.current(netFinds={gate: {"verdict": "RED", "sha": sha or self.shas[gate],
                                                 "why": "its clean run is RED here, untampered"}}))

    def test_a_red_closes_the_guarded_lock_and_not_an_unrelated_one(self):
        self.find("g_frame")
        ok, why = SA._net_heart("frame.release", True, "instruments watched")
        self.assertFalse(ok, "the lock the found law guards stayed open")
        self.assertIn("g_frame", why)
        self.assertEqual(SA._net_heart("printer.stream", True, "instruments watched"), (True, "instruments watched"),
                         "a find closed a lock its law does not guard")
        self.assertFalse(SA._net_heart("fleet.sets", True, "ok")[0],
                         "a route with no declared guard set must keep the global rule (any find closes it)")

    def test_a_find_is_never_softened_as_a_stale_census(self):
        self.find("g_print")
        stale = "the heart2 PROOF census is STALE (not the Heart panel's live census): ..."
        ok, why = SA._net_heart("printer.stream", False, stale)
        self.assertFalse(ok)
        self.assertNotEqual(SA.heart_block_kind(why), "stale", "an ordinary act would be let through a find on merit")

    def test_a_find_whose_file_changed_since_is_moot(self):
        self.find("g_frame", sha="an-older-sha")
        self.assertEqual(SA._net_heart("frame.release", True, "ok"), (True, "ok"))

    def test_may_asks_the_net_whatever_the_heart_said(self):
        import ast
        import tokenize
        with io.open(os.path.join(HERE, "self_arming.py"), encoding="utf-8") as fh:
            src = fh.read()
        bare = tokenize.untokenize([t for t in tokenize.generate_tokens(io.StringIO(src).readline)
                                    if t.type != tokenize.COMMENT])
        fn = [n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "may"][0]
        body = "\n".join(ln.rstrip() for ln in bare.splitlines()[fn.lineno - 1:fn.end_lineno])
        self.assertEqual(body.count("\n    _hok, _hwhy = _net_heart(lock, _hok, _hwhy)\n"), 1,
                         "may() no longer asks the safety net on every answer")


class TheLaneRunsTheNetOnlyOverACurrentCensus(unittest.TestCase):

    def decide(self, census, **kw):
        a = dict(running_pid=None, busy_pct=0.0, mem={}, now_s=1.0e9, playing=False, free=99999.0)
        a.update(kw)
        return SP.decide(census, ("installed", ""), a.pop("running_pid"), a.pop("busy_pct"), a.pop("mem"),
                         a.pop("now_s"), **a)

    def test_current_with_trusted_gates_owed_starts_the_net(self):
        d = self.decide({"state": "current", "netOwed": [("g_frame", 1)]})
        self.assertTrue(d["start"] and d.get("net"), d)
        self.assertFalse(self.decide({"state": "current", "netOwed": []})["start"])
        self.assertFalse(self.decide({"state": "stale", "why": "x", "netOwed": [("g", 1)]}).get("net"),
                         "the net ran while the census still owes gates")

    def test_the_net_never_runs_beside_his_game_or_starves_its_way_in(self):
        cur = {"state": "current", "netOwed": [("g_frame", 1)]}
        self.assertFalse(self.decide(cur, playing=True)["start"])
        long_busy = {"busySince": int((1.0e9 - 10 * 86400) * 1000)}
        d = self.decide(cur, busy_pct=99.0, mem=long_busy)
        self.assertFalse(d["start"], "the safety net starved its way in past a busy machine: %s" % d)
        self.assertFalse(self.decide(cur, free=float(SP.MIN_FREE_MB_TO_START - 1))["start"])

    def test_the_census_reading_owes_the_net_only_when_current(self):
        class H2(object):
            @staticmethod
            def net_finds(st):
                return {"g_frame": {"verdict": "RED", "at": 1, "why": "w", "line": "### REG-NNNN"}}

            @staticmethod
            def net_owed(st):
                return [("g_ok", 2)]
        st = {"trusted": {"g_ok": "s"}}
        self.assertEqual(SP._net_of(H2, st, True)["netOwed"], [("g_ok", 2)])
        self.assertEqual(SP._net_of(H2, st, False)["netOwed"], [], "the net was owed over a census still owed gates")
        self.assertEqual(SP._net_of(H2, st, False)["netFinds"][0]["gate"], "g_frame")

    def test_the_net_is_spawned_as_net_over_named_gates_only(self):
        d = tempfile.mkdtemp(prefix="reg3192-sp-")
        self.addCleanup(shutil.rmtree, d, True)
        got = []

        class P(object):
            pid = 4242

        def popen(cmd, **kw):
            got.append(list(cmd))
            return P()
        SP.spawn(os.path.join(d, "log"), workers=1, popen=popen, names=["g_ok"], net=True)
        SP.spawn(os.path.join(d, "log"), workers=1, popen=popen, names=None, net=True)
        SP.spawn(os.path.join(d, "log"), workers=1, popen=popen, names=["g_ok"])
        self.assertIn("--net", got[0])
        self.assertNotIn("--net", got[1], "the net was asked to prove a whole census")
        self.assertNotIn("--net", got[2])


RED_PROOF = [
    {"why": "REG-3192 - a safety-net find joins the census's BLIND list, so it closes every lock",
     "file": "tv/heart2.py",
     "find": "    out.update(trusted=tr, netFinds=finds, netUnjudged=unj)\n",
     "replace": "    out.update(trusted=tr, netFinds=finds, netUnjudged=unj, blind=sorted(set(prior.get(\"blind\") or []) | set(finds)))\n",
     "matches": 1},
    {"why": "REG-3192 - a clean run RED here is not recorded as a find",
     "file": "tv/heart2.py",
     "find": "        is_red = v == UNPROVABLE and n in red\n",
     "replace": "        is_red = False\n",
     "matches": 1},
    {"why": "REG-3192 - a BLIND here is not recorded as a find",
     "file": "tv/heart2.py",
     "find": "        if n not in unm and (v in (BLIND, INVALID) or is_red):\n",
     "replace": "        if n not in unm and is_red:\n",
     "matches": 1},
    {"why": "REG-3192 - a find closes every lock, not only the ones its law guards",
     "file": "tv/self_arming.py",
     "find": "        if text is None or _guards_lock(text, lock, stems):     # a guard that will not read is counted, never skipped\n",
     "replace": "        if True:\n",
     "matches": 1},
    {"why": "REG-3192 - a find reads as a STALE census, so an ordinary act is let through on merit",
     "file": "tv/self_arming.py",
     "find": "_NET_PHRASE = \"the SAFETY NET found\"\n",
     "replace": "_NET_PHRASE = \"the SAFETY NET found (census is STALE)\"\n",
     "matches": 1},
    {"why": "REG-3192 - may() asks the net only when the heart already said yes",
     "file": "tv/self_arming.py",
     "find": "    _hok, _hwhy = _net_heart(lock, _hok, _hwhy)\n",
     "replace": "    _hok, _hwhy = _net_heart(lock, _hok, _hwhy) if _hok else (_hok, _hwhy)\n",
     "matches": 1},
    {"why": "REG-3192 - a find on a gate whose file has since changed still closes its lock",
     "file": "tv/heart2.py",
     "find": "                if isinstance(f, dict) and n in files and f.get(\"sha\") and shas.get(n) == f.get(\"sha\"))\n",
     "replace": "                if isinstance(f, dict) and n in files)\n",
     "matches": 1},
    {"why": "REG-3192 - the safety net starves its way in past a busy machine",
     "file": "tv/self_prove.py",
     "find": "        if _small or _net:                         # a small slice, or the safety net, never starves its way in\n",
     "replace": "        if _small:\n",
     "matches": 1},
    {"why": "REG-3192 - the net is owed while the census still owes gates",
     "file": "tv/self_prove.py",
     "find": "        out[\"netOwed\"] = [(str(n), int(k)) for n, k in h2.net_owed(st)] if current else []\n",
     "replace": "        out[\"netOwed\"] = [(str(n), int(k)) for n, k in h2.net_owed(st)]\n",
     "matches": 1},
    {"why": "REG-3192 - the net is spawned without --net, so it writes the census's verdicts",
     "file": "tv/self_prove.py",
     "find": "    if net and names:\n        cmd.append(\"--net\")",
     "replace": "    if False:\n        cmd.append(\"--net\")",
     "matches": 1},
    {"why": "REG-3192 - the net never learns that a gate's clean run was RED here",
     "file": "tv/heart2.py",
     "find": "        if _CENSUS.get(\"net\") and any(r.get(\"ok\") is False for r in (getattr(_CLEAN, \"runs\", None) or {}).values()):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3192 - a census run (not the net) files a red for the net",
     "file": "tv/heart2.py",
     "find": "        if _CENSUS.get(\"net\") and any(r.get(\"ok\") is False",
     "replace": "        if True and any(r.get(\"ok\") is False",
     "matches": 1},
    {"why": "REG-3192 - a gate proved here by the net stays listed as another tree's word",
     "file": "tv/heart2.py",
     "find": "        if v == PROVEN:\n            tr.pop(n, None)\n",
     "replace": "        if v == PROVEN:\n            pass\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
