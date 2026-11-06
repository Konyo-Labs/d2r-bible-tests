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
        tools = set(argv[argv.index("--allowedTools") + 1].split(","))
        self.assertTrue(tools and tools <= {"Read", "Grep", "Glob"}, "the diagnosis may do more than read: %r" % tools)
        self.assertIn("--max-turns", argv)
        self.assertNotIn("<name>", argv[-1], "the prompt carries a user folder")
        self.assertTrue(r["ok"])
        self.assertEqual(r["summary"], "the backup root moved")

    def test_it_asks_from_outside_the_project_with_room_to_find_the_function(self):
        """v3867 (#17) - MEASURED: both of a day's asks spent and none landed (8 Read-only turns through a ~12k-line file,
        inside a repo whose CLAUDE.md orders skill loads first). A hand run of the same ask answered and named that."""
        log, cwds = [], []

        def run(argv, **kw):
            log.append(argv)
            cwds.append(kw.get("cwd"))
            return _ran([])(argv, **kw)
        RD.diagnose(MISS, "_check_x", "darwin", run=run, env={}, which=lambda n: "/x/claude")
        argv = log[0]
        self.assertNotEqual(os.path.realpath(cwds[0]), os.path.realpath(RD.REPO), "the ask runs inside the project again")
        self.assertEqual(argv[argv.index("--add-dir") + 1], RD.REPO, "the ask cannot read the repo it diagnoses")
        for flag in ("--strict-mcp-config", "--no-session-persistence"):
            self.assertIn(flag, argv)
        self.assertEqual(argv[argv.index("--setting-sources") + 1], "user")
        self.assertIn("Grep", argv[argv.index("--allowedTools") + 1].split(","), "finding the function costs a page a turn")
        self.assertGreaterEqual(int(argv[argv.index("--max-turns") + 1]), 16)
        self.assertNotIn(RD.REPO, argv[-1], "the prompt carries the repo's absolute path (a user folder)")

    def test_an_answer_is_a_cause_line_whatever_words_it_uses(self):
        """v3868 (the Grok CLI on REG-3235, #231 6676508919): a fault about signing in answers in a dead seat's words, and
        a run that exits 0 without ever writing CAUSE was stored as diagnosed."""
        out = "CAUSE: the console is not logged in to Claude\nFIX: run claude and /login\nVERIFY: the lamp\nCONFIDENCE: high"
        r = RD.diagnose(MISS, "_check_x", "darwin", run=_ran([], out=out), env={}, which=lambda n: "/x/claude")
        self.assertTrue(r["ok"], "a real proposal was dropped for naming its own fault: %r" % r)
        self.assertIn("not logged in", r["summary"])
        r = RD.diagnose(MISS, "_check_x", "darwin", run=_ran([], out="I could not finish reading the checker"),
                        env={}, which=lambda n: "/x/claude")
        self.assertFalse(r["ok"], "an exit 0 with no CAUSE line was stored as diagnosed")
        r = RD.diagnose(MISS, "_check_x", "darwin", run=_ran([], out="Error: usage limit reached"), env={},
                        which=lambda n: "/x/claude")
        self.assertFalse(r["ok"])
        self.assertIn("usage limit", r["summary"], "a dead seat no longer says it is one")

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

    def test_a_spent_ask_that_did_not_land_says_why_until_one_lands(self):
        """v3867 (#17) - the hover said 'not diagnosed yet' all day with the allowance gone and no reason."""
        def dead(m, fn, plat):
            return {"check": m["check"], "ok": False, "summary": "not answered: Error: Reached max turns (8)"}
        got = RD.run_due(self._misses(1), lambda c: None, "darwin", path=self.path, now_s=NOW, ask=dead)
        self.assertIn("Reached max turns", got.get("fault 0") or "", "a spent ask's reason was not kept: %r" % got)
        RD.run_due(self._misses(1), lambda c: None, "darwin", path=self.path, now_s=NOW + 60, ask=dead)   # the 2nd of 2
        again = RD.run_due(self._misses(1), lambda c: None, "darwin", path=self.path, now_s=NOW + 120,
                           ask=lambda m, fn, plat: self.fail("asked past the day's allowance"))
        self.assertIn("did not land", again.get("fault 0") or "", "with the allowance spent the reason was gone: %r" % again)
        self.assertIn("Reached max turns", again.get("fault 0") or "")

        def ok(m, fn, plat):
            return {"check": m["check"], "ok": True, "summary": "the backup root moved", "at": 1}
        later = RD.run_due(self._misses(1), lambda c: None, "darwin", path=self.path, now_s=NOW + 2 * 86400, ask=ok)
        self.assertEqual(later.get("fault 0"), "the backup root moved")
        self.assertNotIn("fault 0", RD.load(self.path).get("failed") or {}, "a landed diagnosis kept its old failure")
        RD.run_due([], lambda c: None, "darwin", path=self.path, now_s=NOW + 3 * 86400, ask=ok)
        self.assertEqual(RD.load(self.path).get("failed") or {}, {}, "a cleared fault kept its failure record")

    def test_a_fault_that_failed_today_waits_and_another_is_asked(self):
        """v3868 (the Grok CLI on REG-3235): one stuck fault took both of the day's asks while another waited."""
        asked = []

        def ask(m, fn, plat):
            asked.append(m["check"])
            return {"check": m["check"], "at": NOW * 1000, "ok": m["check"] != "fault 0",
                    "summary": "not answered: timed out" if m["check"] == "fault 0" else "cause of " + m["check"]}
        RD.run_due(self._misses(1), lambda c: None, "darwin", path=self.path, now_s=NOW, ask=ask)
        RD.run_due(self._misses(2), lambda c: None, "darwin", path=self.path, now_s=NOW + 60, ask=ask)
        self.assertEqual(asked, ["fault 0", "fault 1"], "the fault that failed today took the second ask: %r" % asked)

    def test_an_unreadable_record_is_said_and_spends_nothing(self):
        with open(self.path, "w") as fh:
            fh.write("{not json")
        got = RD.run_due(self._misses(1), lambda c: None, "darwin", path=self.path, now_s=NOW,
                         ask=lambda m, fn, plat: self.fail("asked over a record that will not read"))
        self.assertIn("will not read", got.get("fault 0") or "", "an unreadable record read as 'not diagnosed yet'")

    def test_a_save_that_fails_does_not_reopen_the_days_allowance(self):
        asked = []

        def ask(m, fn, plat):
            asked.append(m["check"])
            return {"check": m["check"], "at": 1, "ok": False, "summary": "not answered: timed out"}
        real = RD.save
        RD.save = lambda path, st: False
        try:
            RD.run_due(self._misses(3), lambda c: None, "darwin", path=self.path, now_s=NOW, ask=ask)
            RD.run_due(self._misses(5), lambda c: None, "darwin", path=self.path, now_s=NOW + 60, ask=ask)
        finally:
            RD.save = real
        self.assertEqual(len(asked), RD.MAX_PER_DAY, "a failed save re-opened the allowance: %r" % asked)

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
    {"why": "v3868 - a dead-seat phrase drops a real CAUSE again, and an exit 0 without one is stored as diagnosed",
     "file": "tv/repair_diagnose.py",
     "find": "    if rc != 0 or not has_cause:\n",
     "replace": "    if rc != 0 or any(s in low for s in DEAD_SEAT):\n",
     "matches": 1},
    {"why": "v3868 - a fault that failed today is asked again and takes the other faults' ask",
     "file": "tv/repair_diagnose.py",
     "find": "and m[\"check\"] not in seen and not _failed_today(m[\"check\"]):\n",
     "replace": "and m[\"check\"] not in seen:\n",
     "matches": 1},
    {"why": "v3868 - an unreadable record answers nothing, so the hover says 'not diagnosed yet' for good",
     "file": "tv/repair_diagnose.py",
     "find": "        return dict((m[\"check\"], \"UNKNOWN - this PC's diagnosis record will not read, so nothing was asked\")\n",
     "replace": "        return {}\n        return dict((m[\"check\"], \"UNKNOWN - this PC's diagnosis record will not read, so nothing was asked\")\n",
     "matches": 1},
    {"why": "v3868 - a failed save re-opens the day's allowance",
     "file": "tv/repair_diagnose.py",
     "find": "        _SPENT[(path, today)] = max(_SPENT.get((path, today), 0), st[\"n\"])\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "v3867 (#17) - the ask runs inside the project again, where its CLAUDE.md and paging Reads spend every turn",
     "file": "tv/repair_diagnose.py",
     "find": "            cwd=_neutral_cwd(), capture_output=True,",
     "replace": "            cwd=REPO, capture_output=True,",
     "matches": 1},
    {"why": "v3867 (#17) - a spent ask that did not land keeps no reason again",
     "file": "tv/repair_diagnose.py",
     "find": "            st.setdefault(\"failed\", {})[m[\"check\"]] = {\"at\": rec.get(\"at\"), \"summary\": rec.get(\"summary\")}\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "v3862 - a diagnosis runs under D2R_NO_CLAUDE (a law spends his plan)",
     "file": "tv/repair_diagnose.py",
     "find": "    if env.get(\"D2R_NO_CLAUDE\") == \"1\":\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3862 - the diagnosis may edit and run, not only read",
     "file": "tv/repair_diagnose.py",
     "find": "[exe, \"-p\", \"--allowedTools\", ALLOWED_TOOLS, \"--max-turns\"",
     "replace": "[exe, \"-p\", \"--allowedTools\", \"Read,Edit,Write,Bash\", \"--max-turns\"",
     "matches": 1},
    {"why": "v3862 - the daily allowance is ignored",
     "file": "tv/repair_diagnose.py",
     "find": "    left = max(0, max_per_day - used)\n",
     "replace": "    left = 99\n",
     "matches": 1},
    {"why": "v3862 - a fault already diagnosed is asked again every pass",
     "file": "tv/repair_diagnose.py",
     "find": "        if isinstance(m, dict) and m.get(\"check\") and m[\"check\"] not in seen and not _failed_today(m[\"check\"]):\n",
     "replace": "        if isinstance(m, dict) and m.get(\"check\") and not _failed_today(m[\"check\"]):\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
