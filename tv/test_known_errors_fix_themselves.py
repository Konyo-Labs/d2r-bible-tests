# -*- coding: utf-8 -*-
"""v3862 - A FAULT THE REPAIR BOOK KNOWS IS FIXED AUTOMATICALLY ON THE PC THAT HAS IT; A FAULT IT DOES NOT KNOW IS LISTED.

His ruling 2026-11-05: "i think just automatically it should be fixed based on the errors it knos" (after asking whether
Dean's missing node could have been fixed on Dean's end by itself). tv/repair_book.py asks the console's EXISTING
repairs (Pillow, numpy, node, the prover's websocket-client, the shallow-clone history) on a cadence, not only at boot.
Pinned:
  · an entry tied to an eagle row runs ONLY when that row reads MISSING, and reads UNKNOWN before the eagle has passed;
  · a failed repair is retried after the cooldown, never in a loop; a door that raises is UNKNOWN, never a crash;
  · a MISSING row the book does not know is LISTED (paths scrubbed) and nothing is run for it;
  · each boot door's record maps to the book's words (fixed only when the door ACTED);
  · every entry has a door on the console and every row-tied entry names a real eagle row - no unjoined end.
Driven over stand-in doors and rows: nothing is installed, fetched or unshallowed.
"""
import inspect
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import repair_book as RB  # noqa: E402

NOW = 1_800_000_000_000


def _doors(log, answers=None):
    answers = answers or {}

    def mk(name):
        def door():
            log.append(name)
            return answers.get(name, ("fine", "nothing wrong"))
        return door
    return {e["door"]: mk(e["door"]) for e in RB.ENTRIES}


def _by(rep):
    return {e["id"]: e for e in rep["entries"]}


class TheBook(unittest.TestCase):

    def test_a_row_tied_entry_runs_only_on_missing(self):
        log = []
        rows = [{"check": "this machine can decode a frame", "state": "missing", "why": "no Pillow"},
                {"check": "this machine can cross-check an inventory", "state": "ok", "why": "numpy 1.26"}]
        rep = RB.apply(rows, _doors(log, {"pillow": ("fixed", "installed")}), now_ms=NOW)
        self.assertIn("pillow", log)
        self.assertNotIn("numpy", log, "a door ran for an eagle row that reads OK")
        self.assertEqual(_by(rep)["pillow"]["state"], "fixed")
        self.assertEqual(_by(rep)["numpy"]["state"], "fine")

    def test_before_the_eagle_has_passed_a_row_tied_entry_is_unknown(self):
        log = []
        rep = RB.apply(None, _doors(log), now_ms=NOW)
        self.assertNotIn("pillow", log)
        self.assertEqual(_by(rep)["pillow"]["state"], "unknown")
        self.assertIn("node", log, "an entry with no eagle row was not asked")

    def test_a_failed_repair_waits_out_the_cooldown(self):
        log = []
        rep = RB.apply([], _doors(log, {"node": ("failed", "the zip hash did not match")}), now_ms=NOW)
        self.assertEqual(_by(rep)["node"]["state"], "failed")
        log.clear()
        rep2 = RB.apply([], _doors(log), state=rep, now_ms=NOW + 60_000)
        self.assertNotIn("node", log, "a failed repair was retried a minute later - a loop")
        self.assertEqual(_by(rep2)["node"]["state"], "failed")
        rep3 = RB.apply([], _doors(log), state=rep2, now_ms=NOW + RB.COOLDOWN_MS + 1)
        self.assertIn("node", log, "a failed repair was never retried")
        self.assertEqual(_by(rep3)["node"]["state"], "fine")

    def test_a_door_that_raises_or_answers_nonsense_is_unknown(self):
        def boom():
            raise RuntimeError("x")
        doors = _doors([])
        doors["node"] = boom
        doors["history"] = lambda: "yes"
        rep = RB.apply([], doors, now_ms=NOW)
        self.assertEqual(_by(rep)["node"]["state"], "unknown")
        self.assertEqual(_by(rep)["shallow-history"]["state"], "unknown")

    def test_an_unknown_fault_is_listed_scrubbed_and_nothing_runs_for_it(self):
        log = []
        rows = [{"check": "the ledger backup covers every store", "state": "missing",
                 "why": "C:\\Users\\<name>\\d2r\\tv\\x.json and /Users/<name>/d2r/tv/y.json unreadable"}]
        rep = RB.apply(rows, _doors(log), now_ms=NOW)
        self.assertEqual([m["check"] for m in rep["misses"]], ["the ledger backup covers every store"])
        why = rep["misses"][0]["why"]
        self.assertNotIn("<name>", why, "a user folder survived the scrub")
        self.assertIn("<path>", why)
        self.assertEqual(sorted(log), sorted(e["door"] for e in RB.ENTRIES if not e["check"]),
                         "something ran for a fault the book does not know")


class TheConsoleDoors(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import control_app as CA
        cls.CA = CA

    def test_a_boot_record_maps_to_the_books_words(self):
        m = self.CA._book_rec
        self.assertEqual(m(None, "tried", "off")[0], "not-here")
        self.assertEqual(m({"ok": True, "tried": True, "why": "installed"}, "tried", "")[0], "fixed")
        self.assertEqual(m({"ok": True, "tried": False, "why": "present"}, "tried", "")[0], "fine")
        self.assertEqual(m({"ok": False, "why": "pip exited 1"}, "tried", "")[0], "failed")
        self.assertEqual(m({"ok": None, "why": "fetching node 22 in the background - ask again"}, "fetched", "")[0],
                         "waiting")
        self.assertEqual(m({"ok": None, "why": "UNKNOWN - node_runtime could not be imported"}, "fetched", "")[0],
                         "unknown")

    def test_the_history_door_says_fixed_only_when_it_unshallowed(self):
        CA = self.CA
        saved = CA.history_repair
        try:
            for rec, want in (({"shallow": False, "repaired": False, "why": "full"}, "fine"),
                              ({"shallow": False, "repaired": True, "why": "fetched"}, "fixed"),
                              ({"shallow": True, "repaired": False, "why": "fetch failed"}, "failed"),
                              ({"shallow": None, "repaired": False, "why": "git?"}, "unknown")):
                CA.history_repair = lambda rec=rec: rec
                self.assertEqual(CA._book_history()[0], want, rec)
        finally:
            CA.history_repair = saved

    def test_every_entry_has_a_door_and_every_row_is_real(self):
        import console_doctor as CD
        doors = self.CA._book_doors()
        names = {n for n, _fn in CD.CHECKS}
        for e in RB.ENTRIES:
            with self.subTest(entry=e["id"]):
                self.assertIn(e["door"], doors, "the book knows a fault no console door fixes")
                if e["check"]:
                    self.assertIn(e["check"], names, "the book waits on an eagle row that does not exist")

    def test_the_pass_runs_on_the_eagles_rows_and_lands_in_status(self):
        CA = self.CA
        saved = (dict(CA._REPAIR_BOOK), dict(CA._EAGLE))
        try:
            CA._EAGLE.update(checked=None, rows=[])
            CA._REPAIR_BOOK.update(running=False)
            CA._repair_book_start(_thread=lambda f: f(), _doors=_doors([]))
            self.assertEqual(_by(CA._REPAIR_BOOK)["pillow"]["state"], "unknown",
                             "the book judged an eagle row before the eagle had passed")
            self.assertFalse(CA._REPAIR_BOOK["running"])
            CA._EAGLE.update(checked=1, rows=[{"check": "this machine can decode a frame", "state": "ok"}])
            CA._repair_book_start(_thread=lambda f: f(), _doors=_doors([]))
            self.assertEqual(_by(CA._REPAIR_BOOK)["pillow"]["state"], "fine")
        finally:
            CA._REPAIR_BOOK.clear()
            CA._REPAIR_BOOK.update(saved[0])
            CA._EAGLE.clear()
            CA._EAGLE.update(saved[1])
        self.assertIn("_repair_book_start()", inspect.getsource(CA._console_rescue_loop))
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            self.assertIn('"repairBook": dict(_REPAIR_BOOK)', fh.read())


class TheFleetSeesIt(unittest.TestCase):
    """His ask: unknown errors "fetched and can be seen by you" - the book rides the presence row, scrubbed twice."""

    @classmethod
    def setUpClass(cls):
        import control_app as CA
        cls.CA = CA

    def test_nothing_rides_before_the_book_has_run(self):
        self.assertIsNone(self.CA._repair_for_wire({"ranAt": None}))

    def test_failed_repairs_and_misses_ride_the_beacon(self):
        rep = RB.apply([{"check": "the ledger backup covers every store", "state": "missing", "why": "x"}],
                       _doors([], {"node": ("failed", "hash mismatch"), "history": ("fixed", "unshallowed")}),
                       now_ms=NOW)
        w = self.CA._repair_for_wire(rep)
        self.assertEqual(w["fixed"], 1)
        self.assertEqual([f["id"] for f in w["failed"]], ["node"])
        self.assertEqual([m["id"] for m in w["misses"]], ["the ledger backup covers every store"])
        self.assertIn("_repair_for_wire", self.CA._system_for_wire.__code__.co_names,
                      "the beacon never carries the repair book - nobody can overwatch")

    @unittest.skipIf(__import__("shutil").which("node") is None, "node is absent - the worker half is UNMEASURED")
    def test_the_worker_keeps_it_and_scrubs_it_again(self):
        import json
        import subprocess
        import worker_source as _ws
        root = os.path.dirname(HERE)
        with io.open(os.path.join(root, "functions", "api", "console.js"), encoding="utf-8") as fh:
            src = fh.read()
        i = src.index("    system: (function (s) {")
        j = src.index("    })(body.system),", i) + len("    })(body.system),")
        fn = "(" + src[i + len("    system: "):j - len("(body.system),")] + ")"
        body = {"tree": "ok", "reels": 1, "repair": {
            "ranAt": NOW, "fixed": 2,
            "failed": [{"id": "node", "why": "C:\\Users\\<name>\\AppData\\node.zip hash mismatch"}],
            "misses": [{"id": "the ledger backup covers every store", "why": "/Users/<name>/d2r/tv/x.json unreadable"}]}}
        js = _ws.prelude(src) + "var shape = %s; console.log(JSON.stringify(shape(%s)));" % (fn, json.dumps(body))
        r = subprocess.run(["node", "-"], input=js, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[:400])
        got = json.loads(r.stdout.strip().splitlines()[-1])["repair"]
        self.assertEqual(got["fixed"], 2)
        self.assertEqual(got["failed"][0]["id"], "node")
        self.assertEqual(got["misses"][0]["id"], "the ledger backup covers every store")
        flat = json.dumps(got)
        self.assertNotIn("<name>", flat, "a user folder crossed into the fleet record")


@unittest.skipIf(__import__("shutil").which("node") is None, "node is absent - the card is UNMEASURED here")
class TheCardSaysIt(unittest.TestCase):

    def _facts(self, rp):
        import json
        import subprocess
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        i = ui.index("  var _repairFacts = function (rp) {")
        j = ui.index("\n  };", i)
        js = ui[i:j + 4] + "\nconsole.log(JSON.stringify(_repairFacts(%s)));" % json.dumps(rp)
        r = subprocess.run(["node", "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[:400])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_a_quiet_pc_or_an_older_build_draws_nothing(self):
        self.assertIsNone(self._facts(None))
        self.assertIsNone(self._facts({"ranAt": 1, "fixed": 2, "failed": [], "misses": []}))

    def test_faults_and_their_proposals(self):
        got = self._facts({"failed": [{"id": "node", "why": "hash mismatch"}],
                           "misses": [{"id": "the ledger backup covers every store", "why": "x", "diag": "root moved"},
                                      {"id": "two eyes compared", "why": "y"}]})
        self.assertEqual(got["f"], ["2 unknown faults", "1 repair failed"])
        self.assertIn("its Claude: root moved", got["why"])
        self.assertIn("not diagnosed yet", got["why"])
        self.assertIn("REPAIR FAILED: node", got["why"])

    def test_the_row_draws_it(self):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        self.assertIn("    var _rpF = _repairFacts(sy && sy.repair);\n"
                      "    if (_rpF) out.push(_fleetPart('repairs', _rpF.f, { warn: true, why: _rpF.why }));", ui)


class TheOverwatchLine(unittest.TestCase):
    """tv/fleet_errors.py - what a UserPromptSubmit hook prints: each PC's new faults once, nothing when none."""

    FLEET = {"online": [
        {"nickname": "dean", "system": {"repair": {"misses": [{"id": "the ledger backup covers every store",
                                                               "why": "unreadable"}],
                                                   "failed": [{"id": "node", "why": "hash mismatch"}]}}},
        {"nickname": "konyo-3", "system": {"river": {}}},
    ]}

    def test_new_faults_print_once_and_a_cleared_one_is_new_again(self):
        import tempfile
        import fleet_errors as FE
        d = tempfile.mkdtemp(prefix="fleet-errors-")
        seen = os.path.join(d, "seen.json")
        out = []
        saved = sys.stdout
        try:
            sys.stdout = io.StringIO()
            FE.main(["--summary"], fetch=lambda: self.FLEET, seen_path=seen)
            first = sys.stdout.getvalue()
            sys.stdout = io.StringIO()
            FE.main(["--summary"], fetch=lambda: self.FLEET, seen_path=seen)
            second = sys.stdout.getvalue()
            sys.stdout = io.StringIO()
            FE.main(["--summary"], fetch=lambda: {"online": []}, seen_path=seen)
            sys.stdout = io.StringIO()
            FE.main(["--summary"], fetch=lambda: self.FLEET, seen_path=seen)
            third = sys.stdout.getvalue()
            sys.stdout = io.StringIO()
            FE.main(["--summary"], fetch=lambda: None, seen_path=seen)
            down = sys.stdout.getvalue()
        finally:
            sys.stdout = saved
            __import__("shutil").rmtree(d, ignore_errors=True)
        self.assertIn("2 new", first)
        self.assertIn("dean: unknown the ledger backup covers every store", first)
        self.assertIn("dean: repair failed node", first)
        self.assertEqual(second, "", "the same fault was shown twice")
        self.assertIn("2 new", third, "a fault that cleared and came back was not new again")
        self.assertEqual(down, "", "a console that could not be asked printed something")


RED_PROOF = [
    {"why": "v3862 - a door runs for an eagle row that reads OK (every pass re-installs what is there)",
     "file": "tv/repair_book.py",
     "find": "            if row.get(\"state\") != \"missing\":\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "v3862 - a failed repair is retried every pass - a loop of pip / zip fetches on his PC",
     "file": "tv/repair_book.py",
     "find": "        if p.get(\"state\") == \"failed\" and isinstance(p.get(\"lastTry\"), int) and now - p[\"lastTry\"] < COOLDOWN_MS:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "v3862 - a miss carries his paths",
     "file": "tv/repair_book.py",
     "find": "    misses = [{\"check\": r[\"check\"], \"why\": scrub(r.get(\"why\"))}",
     "replace": "    misses = [{\"check\": r[\"check\"], \"why\": r.get(\"why\")}",
     "matches": 1},
    {"why": "v3862 - a repair that ACTED reads fine: nobody sees the fault was ever there",
     "file": "tv/control_app.py",
     "find": "        return (\"fixed\" if rec.get(done_key) else \"fine\"), why\n",
     "replace": "        return \"fine\", why\n",
     "matches": 1},
    {"why": "v3862 - the beacon stops carrying the repair book: no PC's unknown error can be seen from here",
     "file": "tv/control_app.py",
     "find": "    out[\"repair\"] = _repair_for_wire()\n",
     "replace": "",
     "matches": 1},
    {"why": "v3862 - the worker keeps a miss's why unscrubbed (a user folder reaches the fleet record)",
     "file": "functions/api/console.js",
     "find": "            return id ? (d ? { id: id, why: txt(e.why, 200), diag: d } : { id: id, why: txt(e.why, 200) }) : null;\n",
     "replace": "            return id ? (d ? { id: id, why: e.why, diag: d } : { id: id, why: e.why }) : null;\n",
     "matches": 1},
    {"why": "v3862 - the card stops counting a PC's unknown faults (nobody sees them without the line)",
     "file": "tv/control_ui.html",
     "find": "    if (miss.length) f.push(miss.length + (miss.length === 1 ? ' unknown fault' : ' unknown faults'));\n",
     "replace": "",
     "matches": 1},
    {"why": "v3862 - the overwatch line repeats every fault on every prompt (it becomes furniture)",
     "file": "tv/fleet_errors.py",
     "find": "        if k not in seen:\n",
     "replace": "        if True:\n",
     "matches": 1},
    {"why": "v3862 - a background node fetch reads unknown, not waiting",
     "file": "tv/control_app.py",
     "find": "    return (\"waiting\" if \"background\" in why else \"unknown\"), why\n",
     "replace": "    return \"unknown\", why\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
