# -*- coding: utf-8 -*-
"""v3862 (item 9) - AN UNKNOWN FAULT IS DIAGNOSED BY THE PC'S OWN CLAUDE, READ-ONLY, A FEW TIMES A DAY AT MOST - NEVER FIXED.

His ask 2026-11-05: could Dean's missing node "have been like done automatically by an AI claude on his own end?" Known
faults fix themselves (the repair book); an unknown one gets a proposal from that PC's signed-in Claude (CAUSE / FIX /
VERIFY), which rides the fleet row to whoever overwatches - and a new fix is never run by itself. The spend is the
dangerous half (a re-read loop maxed his weekly plan three times in October), so it is pinned hard:
  · never under D2R_NO_CLAUDE (every law and runner) and never with no claude on PATH - and neither counts as a spend;
  · only misses this PC never diagnosed, at most MAX_PER_DAY a day; a seat that did not answer is retried tomorrow;
  · Claude may READ only (--allowedTools Read) with a turn cap and a timeout;
  · a fault that clears is forgotten, so it is diagnosed again if it returns;
  · the proposal reaches the beacon, the worker (scrubbed again) and the overwatch line.
Stand-in runners only: no claude is started.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import repair_diagnose as RD  # noqa: E402

NOW = 1_800_000_000.0
MISS = {"check": "the ledger backup covers every store", "why": "C:\\Users\\<name>\\x.json unreadable"}


def _ran(log, out="CAUSE: the backup root moved\nFIX: point it back\nVERIFY: the row reads ok\nCONFIDENCE: medium", rc=0):
    def run(argv, **kw):
        log.append(list(argv))
        return subprocess.CompletedProcess(argv, rc, out, "")
    return run


class TheAsk(unittest.TestCase):

    def test_never_under_no_claude_and_never_without_one(self):
        log = []
        r = RD.diagnose(MISS, "_check_x", "win32", run=_ran(log), env={"D2R_NO_CLAUDE": "1"}, which=lambda n: "/x/claude")
        self.assertTrue(r["summary"].startswith("not asked"))
        r = RD.diagnose(MISS, "_check_x", "win32", run=_ran(log), env={}, which=lambda n: None)
        self.assertTrue(r["summary"].startswith("not asked"))
        self.assertEqual(log, [], "claude was started under D2R_NO_CLAUDE or with none on PATH")

    def test_it_may_read_only_and_answers_the_cause(self):
        log = []
        r = RD.diagnose(MISS, "_check_x", "win32", run=_ran(log), env={}, which=lambda n: "/x/claude")
        argv = log[0]
        self.assertEqual(argv[argv.index("--allowedTools") + 1], "Read", "the diagnosis may do more than read")
        self.assertIn("--max-turns", argv)
        self.assertNotIn("<name>", argv[-1], "the prompt carries a user folder")
        self.assertTrue(r["ok"])
        self.assertEqual(r["summary"], "the backup root moved")

    def test_a_dead_seat_is_not_an_answer(self):
        r = RD.diagnose(MISS, "_check_x", "win32", run=_ran([], out="Not logged in - please run /login", rc=1),
                        env={}, which=lambda n: "/x/claude")
        self.assertFalse(r["ok"])
        self.assertTrue(r["summary"].startswith("not answered"))


class TheAllowance(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="diag-")
        self.path = os.path.join(self.d, RD.STATE_NAME)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _misses(self, n):
        return [{"check": "fault %d" % i, "why": "x"} for i in range(n)]

    def test_new_misses_only_and_at_most_the_daily_allowance(self):
        asked = []

        def ask(m, fn, plat):
            asked.append(m["check"])
            return {"check": m["check"], "at": 1, "ok": True, "summary": "cause of " + m["check"], "text": "x"}
        RD.run_due(self._misses(5), lambda c: None, "darwin", path=self.path, now_s=NOW, ask=ask)
        self.assertEqual(asked, ["fault 0", "fault 1"], "more than MAX_PER_DAY diagnoses ran in a day")
        RD.run_due(self._misses(5), lambda c: None, "darwin", path=self.path, now_s=NOW + 60, ask=ask)
        self.assertEqual(len(asked), 2, "the allowance was spent twice in one day")
        out = RD.run_due(self._misses(5), lambda c: None, "darwin", path=self.path, now_s=NOW + 86400, ask=ask)
        self.assertEqual(asked[2:], ["fault 2", "fault 3"], "a diagnosed fault was asked again, or a new day asked none")
        self.assertEqual(out["fault 0"], "cause of fault 0")

    def test_not_asked_costs_nothing_and_not_answered_is_retried(self):
        calls = []

        def none(m, fn, plat):
            calls.append(m["check"])
            return {"check": m["check"], "ok": False, "summary": "not asked: no claude on this PC"}
        RD.run_due(self._misses(1), lambda c: None, "darwin", path=self.path, now_s=NOW, ask=none)
        self.assertEqual(RD.load(self.path).get("n") or 0, 0, "a diagnosis that was never asked spent the allowance")

        def dead(m, fn, plat):
            calls.append(m["check"])
            return {"check": m["check"], "ok": False, "summary": "not answered: usage limit"}
        RD.run_due(self._misses(1), lambda c: None, "darwin", path=self.path, now_s=NOW, ask=dead)
        st = RD.load(self.path)
        self.assertEqual(st.get("n"), 1)
        self.assertNotIn("fault 0", st.get("seen") or {}, "a seat that did not answer marked the fault diagnosed")

    def test_a_cleared_fault_is_forgotten(self):
        st = RD.forget_cleared({"seen": {"fault 0": {}, "fault 1": {}}}, [{"check": "fault 1"}])
        self.assertEqual(sorted(st["seen"]), ["fault 1"])


class ItRidesToTheOverwatch(unittest.TestCase):

    def test_the_console_attaches_and_sends_it(self):
        import control_app as CA
        saved = (dict(CA._REPAIR_BOOK), dict(CA._EAGLE))
        try:
            CA._EAGLE.update(checked=1, rows=[dict(MISS, state="missing")])
            CA._REPAIR_BOOK.update(running=False)
            doors = {e["door"]: (lambda: ("fine", "x")) for e in __import__("repair_book").ENTRIES}
            CA._repair_book_start(_thread=lambda f: f(), _doors=doors,
                                  _diagnose=lambda misses: {MISS["check"]: "the backup root moved"})
            w = CA._repair_for_wire()
            self.assertEqual(w["misses"][0]["diag"], "the backup root moved")
        finally:
            CA._REPAIR_BOOK.clear()
            CA._REPAIR_BOOK.update(saved[0])
            CA._EAGLE.clear()
            CA._EAGLE.update(saved[1])

    def test_the_overwatch_line_says_it_and_a_late_proposal_is_news(self):
        import fleet_errors as FE
        bare = {"online": [{"nickname": "dean", "system": {"repair": {"misses": [{"id": "f", "why": "x"}]}}}]}
        told = {"online": [{"nickname": "dean", "system": {"repair": {"misses": [
            {"id": "f", "why": "x", "diag": "the backup root moved"}]}}}]}
        new, keep = FE.new_since(FE.open_faults(bare), {})
        new2, _k = FE.new_since(FE.open_faults(told), keep)
        self.assertEqual(len(new2), 1, "a proposal for a fault already shown never reached the line")
        self.assertIn("its Claude: the backup root moved", FE.summary(new2))


RED_PROOF = [
    {"why": "v3862 - a diagnosis runs under D2R_NO_CLAUDE (a law spends his plan)",
     "file": "tv/repair_diagnose.py",
     "find": "    if env.get(\"D2R_NO_CLAUDE\") == \"1\":\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3862 - the diagnosis may edit and run, not only read",
     "file": "tv/repair_diagnose.py",
     "find": "[exe, \"-p\", \"--allowedTools\", \"Read\", \"--max-turns\"",
     "replace": "[exe, \"-p\", \"--allowedTools\", \"Read,Edit,Write,Bash\", \"--max-turns\"",
     "matches": 1},
    {"why": "v3862 - the daily allowance is ignored",
     "file": "tv/repair_diagnose.py",
     "find": "    left = max(0, max_per_day - used)\n",
     "replace": "    left = 99\n",
     "matches": 1},
    {"why": "v3862 - a fault already diagnosed is asked again every pass",
     "file": "tv/repair_diagnose.py",
     "find": "        if isinstance(m, dict) and m.get(\"check\") and m[\"check\"] not in seen:\n",
     "replace": "        if isinstance(m, dict) and m.get(\"check\"):\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
