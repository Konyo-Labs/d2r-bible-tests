# -*- coding: utf-8 -*-
"""REG-3192 (his ruling 2026-11-05 ~09:15, item 4: "the background full proof keeps running at idle as a SAFETY NET but no
longer holds the river shut - a red/blind it finds goes to the fleet + BUGS and closes only the lock its law guards").

REG-3191 writes a gate into the census on another tree's proofs over byte-identical inputs (`trusted`). The safety net is
the self-prove lane's idle run of exactly those gates ON THIS PC, once the census is current, lowest priority, behind every
stand-aside rule. What it finds must not undo REG-3191 (MEASURED 2026-11-05: after every ship each PC's river stayed shut
~1 h on his Mac, 28 days on the old ALT, until every changed law re-proved locally) - so it is held here, end to end:
  * prove(net=True) judges every gate it is handed ON THIS PC (no other tree's PROVEN), never asks the trust pass, and
    writes only through _write_net: a clean run RED here (its first or its CLOSING run), a BLIND, an INVALID is a find in
    `netFinds` with its sha, verdict, first/last seen, a BUGS-ready line - and NEVER the census's `blind`, `gateShas` or
    fingerprint, so the census does not go stale (his 2026-09-12 "a BLIND closes every lock" stands for every other BLIND);
  * may() - and report(), the padlock - close ONLY the lock(s) whose #156 guard set holds the found law, on the real gate
    files; a find is never softened like a STALE census; a find on a file that changed since is moot;
  * a gate the net PROVES here leaves `trusted`; a found gate and one it could not judge here (UNKNOWN, slow) STAY trusted
    and are asked again after NET_RETRY_S - one flaky red never shuts a lock until someone edits the law; a slice that banks
    its snapshot every minute counts each run once;
  * the lane starts the net only over a CURRENT census with trusted gates owed, never beside his game, never starving its
    way in, and the spawn it calls is told `net`; its status carries the net (on / worked / lastTs / owed / unjudged).
Fixtures only: fixture gate files and a fixture census (TV_HEART_CENSUS / heart2.STATE); the may() case reads the real
gate files with a fixture census, as the per-lock law does. RED_PROOF below.
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
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import heart2 as H  # noqa: E402
import self_arming as SA  # noqa: E402
import self_prove as SP  # noqa: E402

QUIET = lambda *a, **k: None  # noqa: E731
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
                      mock.patch.dict(SA._NET_MEMO, {"key": None, "finds": None, "files": None}),
                      mock.patch.dict(H._CENSUS, {"cache": None, "here": (), "red": set(), "net": False,
                                                  "netSaid": set()})):
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

    def test_a_find_carries_its_cases_and_a_flake_is_kept_apart(self):
        """REG-3324 - the census keeps WHICH cases failed on a find, and a flake in netFlakes (named, dated), never in
        netFinds - so the lock rule can narrow, and nothing a flake did is lost"""
        self.write(self.current())
        with mock.patch.dict(H._CENSUS, {"redCases": {"g_frame": ["TestB.test_y"]}, "flakes": {"g_print": ["TestA.test_x"]}}):
            H._write_net({"g_frame": H.UNPROVABLE, "g_print": H.PROVEN}, red={"g_frame"})
        st = self.census()
        self.assertEqual(st["netFinds"]["g_frame"].get("cases"), ["TestB.test_y"])
        self.assertNotIn("g_print", st["netFinds"])
        self.assertEqual(st["netFlakes"]["g_print"]["cases"], ["TestA.test_x"], "the flake was not kept")

    def test_a_found_or_unjudged_gate_stays_trusted_so_it_is_asked_again(self):
        self.write(self.current())
        H._write_net({"g_frame": H.UNPROVABLE, "g_idle": H.UNPROVABLE}, red={"g_frame"})
        st = self.census()
        self.assertIn("g_frame", st["trusted"], "a found gate left the net for good - its lock shut until an edit")
        self.assertIn("g_idle", st["trusted"], "a gate the net could not judge left the net for good")

    def test_each_run_is_counted_once_though_its_slice_banks_every_minute(self):
        self.write(self.current())
        for _ in range(3):
            H._write_net({"g_frame": H.UNPROVABLE, "g_idle": H.UNPROVABLE}, red={"g_frame"})
        st = self.census()
        self.assertEqual((st["netFinds"]["g_frame"]["seen"], st["netUnjudged"]["g_idle"]["tries"]), (1, 1))
        H._CENSUS["netSaid"] = set()                               # the next net run
        H._write_net({"g_frame": H.UNPROVABLE}, red={"g_frame"})
        self.assertEqual(self.census()["netFinds"]["g_frame"]["seen"], 2)

    def test_a_find_on_a_file_that_changed_since_or_an_unmeasured_gate_is_not_written(self):
        self.write(self.current(gateShas=dict(self.shas, g_frame="older")))
        H._write_net({"g_frame": H.BLIND})
        self.assertNotIn("g_frame", self.census()["netFinds"])
        self.write(self.current())
        H._write_net({"g_blind": H.BLIND}, unmeasured={"g_blind"})
        self.assertEqual(self.census()["netFinds"], {})


class TheNetAsksAgain(_Fixture):

    def owed(self, now_ms):
        return [n for n, _k in H.net_owed(self.census(), self.gates, now_ms=now_ms)]

    def test_a_find_and_an_unjudged_gate_are_asked_again_after_the_retry_and_not_before(self):
        at = 10 ** 12
        self.write(self.current(netFinds={"g_frame": {"verdict": "RED", "sha": self.shas["g_frame"], "at": at}},
                                netUnjudged={"g_idle": {"verdict": "UNPROVABLE", "sha": self.shas["g_idle"], "at": at}}))
        soon = self.owed(at + 3600 * 1000)
        self.assertNotIn("g_frame", soon, "a find was re-judged an hour later - the net would loop on one flaky law")
        self.assertNotIn("g_idle", soon)
        self.assertIn("g_ok", soon, "a trusted gate never asked is not owed")
        later = self.owed(at + (H.NET_RETRY_S + 60) * 1000)
        self.assertIn("g_frame", later, "a find is never judged again - one flaky red shuts its lock until an edit")
        self.assertIn("g_idle", later, "a gate the net could not judge is never asked again")

    def test_a_gate_whose_file_moved_is_the_censuss_not_the_nets(self):
        self.write(self.current(gateShas=dict(self.shas, g_ok="older")))
        self.assertNotIn("g_ok", self.owed(10 ** 12))


class TheNetLearnsARedCleanRun(unittest.TestCase):
    """A clean run RED here - the first one its proofs shared, or the CLOSING one (REG-1669) - is read from the gate's own
    shared clean-run record, so the census path calls the prover exactly as before and only a net run makes it a find."""

    def _gate(self, net, run):
        def proofs(sandbox, name, filename, prs, say):
            H._CLEAN.runs[("g.py",)] = dict(run)
            return [H.UNPROVABLE if run.get("ok") is False else H.PROVEN]
        with mock.patch.object(H, "_prove_gate_proofs", proofs), \
                mock.patch.object(H, "_reset_lane_records", lambda *a, **k: None), \
                mock.patch.dict(H._CENSUS, {"cache": None, "here": (), "red": set(), "net": net}):
            H._prove_gate(HERE, "g_frame", "g.py", [{"find": "a"}], QUIET)
            return set(H._CENSUS["red"])

    def test_a_red_first_clean_run_on_a_net_run_is_recorded(self):
        self.assertEqual(self._gate(True, {"ok": False, "tail": "red"}), {"g_frame"},
                         "the net's RED clean run was not recorded, so it can never be a find")

    def test_a_red_closing_clean_run_is_recorded_and_an_unknown_one_is_not(self):
        red = {"ok": True, "reused": 1, "by": [0], "again": lambda: (False, "red: case_x")}
        self.assertEqual(self._gate(True, red), {"g_frame"}, "a CLOSING clean run that went RED was not a find")
        unk = {"ok": True, "reused": 1, "by": [0], "again": lambda: (None, "deadline")}
        self.assertEqual(self._gate(True, unk), set(), "an UNKNOWN closing run was filed as a red")

    def _gate_records(self, run):
        """REG-3324 - the net's red set, its flakes and its failing cases, read inside the patch."""
        def proofs(sandbox, name, filename, prs, say):
            H._CLEAN.runs[("g.py",)] = dict(run)
            return [H.UNPROVABLE if run.get("ok") is False else H.PROVEN]
        with mock.patch.object(H, "_prove_gate_proofs", proofs), \
                mock.patch.object(H, "_reset_lane_records", lambda *a, **k: None), \
                mock.patch.dict(H._CENSUS, {"cache": None, "here": (), "red": set(), "net": True,
                                            "flakes": {}, "redCases": {}}):
            H._prove_gate(HERE, "g_frame", "g.py", [{"find": "a"}], QUIET)
            return set(H._CENSUS["red"]), dict(H._CENSUS["flakes"]), dict(H._CENSUS["redCases"])

    def test_a_red_that_comes_back_green_on_its_recheck_is_a_flake_never_a_find(self):
        """REG-3324 (#103) - MEASURED 11-06 23:38Z: test_control went RED once under load and closed all nine locks; it ran
        2,274 OK 25 minutes later. The net re-runs a red clean run ONCE: green again is a FLAKE (named, closes nothing)."""
        red, flakes, cases = self._gate_records({"ok": False, "tail": "FAIL: test_x (test_control.TestA)\n",
                                                 "again": lambda: (True, "OK")})
        self.assertEqual(red, set(), "a red that did not repeat became a find - one flake closes every lock it guards")
        self.assertEqual(flakes, {"g_frame": ["TestA.test_x"]}, "the flake is not recorded with the case that failed")

    def test_a_red_that_repeats_is_a_find_naming_its_cases(self):
        red, flakes, cases = self._gate_records({"ok": False, "tail": "FAIL: test_y (m.TestB)\n",
                                                 "again": lambda: (False, "ERROR: test_z (m.TestC.test_z)\n")})
        self.assertEqual(red, {"g_frame"}, "a red that repeated on its re-check is not a find")
        self.assertEqual(flakes, {})
        self.assertEqual(cases, {"g_frame": ["TestB.test_y", "TestC.test_z"]}, "the find does not carry its failing cases")

    def test_a_green_clean_run_or_a_census_run_records_nothing(self):
        self.assertEqual(self._gate(True, {"ok": True}), set())
        self.assertEqual(self._gate(False, {"ok": False}), set(), "a census run (not the net) recorded a red for the net")


class TheNetRunEndToEnd(_Fixture):
    """prove(net=True) with only the law runs stood in: what it judges where, and what it writes."""

    def test_it_judges_here_and_writes_only_its_record(self):
        self.write(self.current())
        seen = {}

        def gates_run(have, say=print, workers=None, blank=None):
            seen["names"] = sorted(n for n, _f, _p in have)
            seen["here"] = set(H._CENSUS.get("here") or ())
            seen["net"] = H._CENSUS.get("net")
            H._CENSUS["red"].add("g_frame")
            return {"g_frame": H.UNPROVABLE, "g_ok": H.PROVEN}, {}
        with mock.patch.object(H, "_census_cache", lambda reuse, say=print: None), \
                mock.patch.object(H, "trust_pass", mock.Mock(side_effect=AssertionError("the net asked the trust pass"))), \
                mock.patch.object(H, "_prove_gates", gates_run):
            H.prove(only={"g_frame", "g_ok"}, say=QUIET, stamp=False, reuse=True, net=True)
        self.assertEqual(seen, {"names": ["g_frame", "g_ok"], "here": {"g_frame", "g_ok"}, "net": True},
                         "the net did not judge every gate it was handed on this PC")
        st = self.census()
        self.assertEqual(sorted(st["netFinds"]), ["g_frame"])
        self.assertEqual((st["blind"], st["gateShas"], st["gatesFingerprint"]), ([], self.shas, "FP"),
                         "the net wrote the census's own verdicts - a find would make it stale or shut every lock")
        self.assertNotIn("g_ok", st["trusted"])

    def test_the_cli_hands_the_net_flag_to_prove(self):
        got = {}
        with mock.patch.object(H, "prove", lambda **kw: got.update(kw) or {}):
            H.main(["--prove", "g_frame", "--slice", "--reuse", "--net"])
        self.assertTrue(got.get("net") and got.get("reuse") and got.get("stamp") is False, got)
        self.assertEqual(H.main(["--prove", "--slice", "--reuse", "--net"]), 2, "the net proved a whole census")


FILES = dict(H.gate_files())
PRINTER, FRAME = "printer.stream", "frame.release"


def _text(name):
    f = FILES[name]
    with open(f if os.path.isabs(f) else os.path.join(H.HERE, f), encoding="utf-8") as fh:
        return fh.read()


def _guards(lock):
    return set(n for n in FILES if SA._guards_lock(_text(n), lock, SA.LOCK_DOORS[lock]))


DECLARING = set(n for n in FILES if H.red_proofs_in(FILES[n]))
G_PRINTER, G_FRAME = _guards(PRINTER), _guards(FRAME)
ONLY_FRAME = sorted((G_FRAME - G_PRINTER) & DECLARING)
ONLY_PRINTER = sorted((G_PRINTER - G_FRAME) & DECLARING)


class AFindClosesOnlyTheLockItsLawGuards(unittest.TestCase):
    """may() and report() themselves, over the real gate files and a fixture census (TV_HEART_CENSUS)."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="reg3192-may-")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.path = os.path.join(self.d, ".heart2.json")
        for patch in (mock.patch.dict(os.environ, {"TV_HEART_CENSUS": self.path}),
                      mock.patch.dict(SA._NET_MEMO, {"key": None, "finds": None, "files": None})):
            patch.start()
            self.addCleanup(patch.stop)
        SA._LOCK_MEMO.update(key=None)
        self.addCleanup(SA._LOCK_MEMO.update, key=None)

    def census(self, find, current=True, sha=None, owed=()):
        shas = H.gate_shas()
        shas.update((n, "0" * 16) for n in owed)
        st = {"gatesFingerprint": (H.gates_fingerprint() if current else "f" * 32), "gateShas": shas,
              "provedGates": sorted(FILES), "blind": [], "proved": len(FILES), "declared": len(DECLARING),
              "total": len(FILES), "sliceOwed": 0, "trusted": {find: shas[find]},
              "netFinds": {find: {"verdict": "RED", "sha": sha or H.gate_shas()[find], "at": 1,
                                  "why": "its clean run is RED here"}}}
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        SA._LOCK_MEMO.update(key=None)
        SA._NET_MEMO.update(key=None, finds=None, files=None)

    def test_the_premise_a_law_guards_one_lock_and_not_the_other(self):
        self.assertTrue(ONLY_FRAME and ONLY_PRINTER, "PREMISE: no law guards frame.release without printer.stream")

    def test_a_find_closes_the_guarded_lock_and_not_an_unrelated_one(self):
        self.census(ONLY_FRAME[0])
        ok, why = SA.may(FRAME)
        self.assertFalse(ok, "the river's lock stayed open beside a find on its own guard law")
        self.assertIn(SA._NET_PHRASE, why)
        self.assertIn(ONLY_FRAME[0], why)
        self.assertNotIn(SA._NET_PHRASE, SA.may(PRINTER)[1], "a find closed a lock its law does not guard")
        rows = dict((r["lock"], r) for r in SA.report().get("locks", []))
        self.assertIn(SA._NET_PHRASE, rows[FRAME].get("permittedWhy") or "", "the padlock disagrees with the act")
        self.assertNotIn(SA._NET_PHRASE, rows[PRINTER].get("permittedWhy") or "")

    def test_a_find_is_never_softened_as_a_stale_census(self):
        """printer.stream's OWN guards owe a proof (#156 answers STALE for it), and another of its guards has a find:
        a STALE refusal of an ordinary act is softened to merit (v3042), a find must not be."""
        self.assertGreater(len(ONLY_PRINTER), 1, "PREMISE: printer.stream has fewer than two guards of its own")
        self.census(ONLY_PRINTER[0], current=False, owed=[ONLY_PRINTER[1]])
        self.assertEqual(SA.heart_block_kind(SA._lock_heart(PRINTER)[1]), "stale",
                         "PREMISE: printer.stream's own guard owed did not make it STALE")
        ok, why = SA.may(PRINTER)
        self.assertFalse(ok, "an ordinary act was let through a find because the census also read STALE")
        self.assertIn(SA._NET_PHRASE, why)

    def _census_cases(self, find, cases):
        self.census(find)
        with open(self.path, encoding="utf-8") as fh:
            st = json.load(fh)
        if cases is not None:
            st["netFinds"][find]["cases"] = cases
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        SA._LOCK_MEMO.update(key=None)
        SA._NET_MEMO.update(key=None, finds=None, files=None)

    def test_a_giant_law_closes_only_the_locks_its_failing_classes_guard(self):
        """REG-3324 (#103) - test_control names every lock, so one red of it closed the whole river. A law guarding
        NET_NARROW_MIN_LOCKS or more locks closes only what its FAILING CLASSES guard; with no case named it stays broad."""
        import re as _re
        if "test_control" not in FILES:
            self.skipTest("PREMISE: test_control is not a registered gate here")
        text = _text("test_control")
        n = sum(1 for lk in SA.LOCK_DOORS if SA._guards_lock(text, lk, SA.LOCK_DOORS[lk]))
        self.assertGreaterEqual(n, SA.NET_NARROW_MIN_LOCKS, "PREMISE: test_control no longer guards enough locks to narrow")
        classes = _re.findall(r"(?m)^class\s+(\w+)", text)
        quiet = [c for c in classes if not any(SA._guards_lock(SA._case_class_source(text, c + ".t") or "", lk, SA.LOCK_DOORS[lk])
                                               for lk in SA.LOCK_DOORS)]
        river = [c for c in classes if SA._guards_lock(SA._case_class_source(text, c + ".t") or "", FRAME, SA.LOCK_DOORS[FRAME])]
        self.assertTrue(quiet and river, "PREMISE: no class guards no lock, or none guards the river")
        self._census_cases("test_control", [quiet[0] + ".test_x"])
        self.assertNotIn(SA._NET_PHRASE, SA.may(FRAME)[1], "a red in a class that guards no lock closed the river")
        self._census_cases("test_control", [river[0] + ".test_x"])
        self.assertIn(SA._NET_PHRASE, SA.may(FRAME)[1], "a red in a class that guards the river left it open")
        self._census_cases("test_control", None)
        self.assertIn(SA._NET_PHRASE, SA.may(FRAME)[1], "a find naming no case was narrowed - it must stay broad")

    def test_a_find_whose_file_changed_since_is_moot(self):
        self.census(ONLY_FRAME[0], sha="an-older-sha")
        self.assertNotIn(SA._NET_PHRASE, SA.may(FRAME)[1])


class TheLaneRunsTheNetOnlyOverACurrentCensus(unittest.TestCase):

    CUR = {"state": "current", "why": "ok", "netOwed": [("g_frame", 1)], "fingerprint": "FP",
           "netUnjudged": [{"gate": "g_idle", "verdict": "UNPROVABLE", "at": 1, "tries": 1}]}

    def decide(self, census, **kw):
        a = dict(running_pid=None, busy_pct=0.0, mem={}, now_s=1.0e9, playing=False, free=99999.0)
        a.update(kw)
        return SP.decide(census, ("installed", ""), a.pop("running_pid"), a.pop("busy_pct"), a.pop("mem"),
                         a.pop("now_s"), **a)

    def test_current_with_trusted_gates_owed_starts_the_net(self):
        d = self.decide(dict(self.CUR))
        self.assertTrue(d["start"] and d.get("net"), d)
        self.assertFalse(self.decide({"state": "current", "netOwed": []})["start"])
        self.assertFalse(self.decide({"state": "stale", "why": "x", "netOwed": [("g", 1)]}).get("net"),
                         "the net ran while the census still owes gates")

    def test_the_net_never_runs_beside_his_game_or_starves_its_way_in(self):
        self.assertFalse(self.decide(dict(self.CUR), playing=True)["start"])
        long_busy = {"busySince": int((1.0e9 - 10 * 86400) * 1000)}
        d = self.decide(dict(self.CUR), busy_pct=99.0, mem=long_busy)
        self.assertFalse(d["start"], "the safety net starved its way in past a busy machine: %s" % d)
        self.assertFalse(self.decide(dict(self.CUR), free=float(SP.MIN_FREE_MB_TO_START - 1))["start"])

    def test_the_tick_spawns_the_net_as_net_and_books_it_apart(self):
        """The REAL spawn door (self_prove.spawn, looked up as the tick calls it) - the one a live tick uses - is told
        `net`; a law's recording spawn would bypass the very line that says so."""
        d = tempfile.mkdtemp(prefix="reg3192-sp-")
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "sp.json")
        calls = []

        def spawn(log_path, names=None, workers=None, net=False, trust=False, reuse=True):
            calls.append({"names": names, "net": net, "trust": trust})
            return 4242
        base = (mock.patch.object(SP, "spawn", spawn), mock.patch.object(SP, "proc_birth", lambda pid: 1.0),
                mock.patch.object(SP, "ensure_prover_deps", lambda *a, **k: {"ok": True}),
                mock.patch.object(SP, "_hold_awake", lambda *a, **k: None),
                mock.patch.dict(SP._STARTED, {"pid": None, "birth": None}))
        for p in base:
            p.start()
            self.addCleanup(p.stop)
        with mock.patch.object(SP, "identity", lambda pid, birth: True):
            st = SP.tick(now_s=1.0e9, busy=0.0, tree=("installed", ""), census=dict(self.CUR), path=path,
                         env={"TV_SELF_PROVE": "1"}, playing=False, free=99999.0, sandbox=(True, ""))
        self.assertEqual(calls, [{"names": ["g_frame"], "net": True, "trust": False}],
                         "the net's slice was spawned without --net - its verdicts would be the census's")
        self.assertEqual(st["net"]["owed"], 1)
        self.assertEqual(st["net"]["unjudged"][0]["gate"], "g_idle", "a gate the net could not judge is not said")
        with mock.patch.object(SP, "identity", lambda pid, birth: False):
            st = SP.tick(now_s=1.0e9 + 60, busy=0.0, tree=("installed", ""), census=dict(self.CUR, netOwed=[]),
                         path=path, env={"TV_SELF_PROVE": "1"}, playing=False, free=99999.0, sandbox=(True, ""))
        mem = SP.load(path)
        self.assertEqual(mem.get("netWorked"), 1, "the net's end was not booked on its own counters")
        self.assertIsNone(mem.get("lastFailAt"))
        self.assertEqual(st["net"]["worked"], 1)

    def test_the_real_spawn_passes_net_over_named_gates_only(self):
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
        self.assertIn("--net", got[0], "the net's slice reaches heart2 without --net - it would write the census")
        self.assertNotIn("--net", got[1], "the net was asked to prove a whole census")
        self.assertNotIn("--net", got[2])

    def test_the_census_reading_owes_the_net_only_when_current(self):
        class H2(object):
            @staticmethod
            def net_finds(st):
                return {"g_frame": {"verdict": "RED", "at": 1, "why": "w", "line": "### REG-NNNN"}}

            @staticmethod
            def net_owed(st):
                return [("g_ok", 2)]
        st = {"trusted": {"g_ok": "s", "g_idle": "t"}, "netUnjudged": {"g_idle": {"verdict": "UNPROVABLE", "tries": 2}}}
        self.assertEqual(SP._net_of(H2, st, True)["netOwed"], [("g_ok", 2)])
        self.assertEqual(SP._net_of(H2, st, False)["netOwed"], [], "the net was owed over a census still owed gates")
        self.assertEqual(SP._net_of(H2, st, False)["netFinds"][0]["gate"], "g_frame")
        self.assertEqual([u["gate"] for u in SP._net_of(H2, st, True)["netUnjudged"]], ["g_idle"])


RED_PROOF = [
    {"why": "REG-3324 - the net never re-checks a red: one flake under load closes every lock its law guards again",
     "file": "heart2.py",
     "find": "        if _CENSUS.get(\"net\") and _clean_went_red(getattr(_CLEAN, \"runs\", None)) and _net_red_holds(name, say):\n",
     "replace": "        if _CENSUS.get(\"net\") and _clean_went_red(getattr(_CLEAN, \"runs\", None)):\n",
     "matches": 1},
    {"why": "REG-3324 - a giant law's find closes every lock it names again, whatever class failed (the river shut)",
     "file": "self_arming.py",
     "find": "    if n_locks < NET_NARROW_MIN_LOCKS:\n        return True\n",
     "replace": "    if n_locks < 10 ** 6:\n        return True\n",
     "matches": 1},
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
    {"why": "REG-3192 - a found gate leaves the net for good, so its lock stays shut until someone edits the law",
     "file": "tv/heart2.py",
     "find": "            unj.pop(n, None)\n            said[\"finds\"].append(n)\n",
     "replace": "            unj.pop(n, None)\n            tr.pop(n, None)\n            said[\"finds\"].append(n)\n",
     "matches": 1},
    {"why": "REG-3192 - a gate the net could not judge leaves the net for good, trusted and never judged here",
     "file": "tv/heart2.py",
     "find": "        said[\"unjudged\"].append(n)\n        _once.add(n)\n",
     "replace": "        said[\"unjudged\"].append(n)\n        _once.add(n)\n        tr.pop(n, None)\n",
     "matches": 1},
    {"why": "REG-3192 - a find is never judged again",
     "file": "tv/heart2.py",
     "find": "        if n in finds and not _net_age_ok(finds[n], now_ms):\n            continue\n",
     "replace": "        if n in finds:\n            continue\n",
     "matches": 1},
    {"why": "REG-3192 - the net re-asks a find at once, looping on one flaky law",
     "file": "tv/heart2.py",
     "find": "    return now_ms - at >= NET_RETRY_S * 1000\n",
     "replace": "    return True\n",
     "matches": 1},
    {"why": "REG-3192 - every minute's slice bank counts the same run again",
     "file": "tv/heart2.py",
     "find": "\"seen\": int(_was.get(\"seen\") or 0) + (0 if n in _once else 1)",
     "replace": "\"seen\": int(_was.get(\"seen\") or 0) + 1",
     "matches": 1},
    {"why": "REG-3192 - a gate proved here by the net stays listed as another tree's word",
     "file": "tv/heart2.py",
     "find": "        if v == PROVEN:\n            tr.pop(n, None)\n",
     "replace": "        if v == PROVEN:\n            pass\n",
     "matches": 1},
    {"why": "REG-3192 - the net never learns that a gate's clean run was RED here",
     "file": "tv/heart2.py",
     "find": "        if _CENSUS.get(\"net\") and _clean_went_red(getattr(_CLEAN, \"runs\", None)):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3192 - a census run (not the net) files a red for the net",
     "file": "tv/heart2.py",
     "find": "        if _CENSUS.get(\"net\") and _clean_went_red(",
     "replace": "        if True and _clean_went_red(",
     "matches": 1},
    {"why": "REG-3192 - a RED closing clean run is missed (the red is filed before the closing run)",
     "file": "tv/heart2.py",
     "find": "        if ok is False:\n            r[\"closingRed\"] = True",
     "replace": "        if False:\n            r[\"closingRed\"] = True",
     "matches": 1},
    {"why": "REG-3192 - the net judges on another tree's word (nothing judged here)",
     "file": "tv/heart2.py",
     "find": "            _CENSUS[\"here\"] = set(n for n, _f, _p in have)          # REG-3192 - every proof judged on this PC\n",
     "replace": "            _CENSUS[\"here\"] = set()\n",
     "matches": 1},
    {"why": "REG-3192 - the net writes the census's verdicts (a find makes it stale and shuts every lock)",
     "file": "tv/heart2.py",
     "find": "            _said = _write_net(results, red=_CENSUS.get(\"red\"), unmeasured=_blank) or {}\n",
     "replace": "            _said = _write_state(results, stamp=False, unmeasured=_blank) or {}\n",
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
    {"why": "REG-3192 - the padlock (report) ignores the net while the act refuses",
     "file": "tv/self_arming.py",
     "find": "        return _net_heart(lock, heart[0], heart[1])\n",
     "replace": "        return heart\n",
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
    {"why": "REG-3192 - the tick spawns the net's slice without --net (the reviewer's sabotage)",
     "file": "tv/self_prove.py",
     "find": "                _spawn_real = _ft.partial(_spawn_real, net=True)    # REG-3192 - spawned as --net over named gates\n",
     "replace": "                pass\n",
     "matches": 1},
    {"why": "REG-3192 - the real spawn never passes --net to heart2",
     "file": "tv/self_prove.py",
     "find": "    if net and names:\n        cmd.append(\"--net\")",
     "replace": "    if False:\n        cmd.append(\"--net\")",
     "matches": 1},
    {"why": "REG-3192 - the CLI drops --net, so the net's slice writes the census",
     "file": "tv/heart2.py",
     "find": "            if a.net:\n                _rk[\"net\"] = True",
     "replace": "            if False:\n                _rk[\"net\"] = True",
     "matches": 1},
    {"why": "REG-3192 - the lane's status never says which trusted gates the net could not judge here",
     "file": "tv/self_prove.py",
     "find": "                    \"unjudged\": census.get(\"netUnjudged\") if isinstance(census.get(\"netUnjudged\"), list) else None},\n",
     "replace": "                    \"unjudged\": None},\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
