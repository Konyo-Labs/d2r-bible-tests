#!/usr/bin/env python3
"""Guards for the health engine. It REPORTS and never repairs, and UNKNOWN is never ok."""
import io
import os
import sys as _fx_sys
_fx_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture_ledgers as _fx_ledgers  # noqa: E402  v3470 — never HIS eagle ledgers
_fx_ledgers.redirect()
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import health_engine as HE


RED_PROOF = [
    {
        "why": "REG-1950 - a route that did not refuse is counted as a lock again",
        "file": "tv/health_engine.py",
        "find": "    inert = [l for l in valves if l.get(\"state\") == SA.LOCKED]\n",
        "replace": "    inert = [l for l in locks if l.get(\"state\") == SA.LOCKED]\n",
        "matches": 1,
    },
    {
        "why": 'the law requires this text in health_engine.py, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'health_engine.py',
        "find": 'from confidence import wilson_lower',
        "replace": '_HEART2_TAMPERED_',
        "matches": 1,
    },
    {
        "why": "a HARDENED lock is counted unproven again, so a shelf that earned the stronger tier reads as none "
               "proven (REG-3215 moved the count into self_arming.lock_counts, the one tally every surface quotes)",
        "file": "self_arming.py",
        "find": "    proven = sum(1 for v in valves if str(v.get(\"state\") or \"\").upper() in (OPEN, HARDENED))\n",
        "replace": "    proven = sum(1 for v in valves if str(v.get(\"state\") or \"\").upper() == OPEN)\n",
        "matches": 1,
    },
    {
        "why": "a heart that has never run here leaves the row OK, so the locks read open while may() is refusing",
        "file": "health_engine.py",
        "find": "    heart_shut = (not rep.get(\"heartOk\") and SA.heart_block_kind(heart_why) != \"stale\")\n",
        "replace": "    heart_shut = False\n",
        "matches": 1,
    },
]

class TestItReportsAndNeverRepairs(unittest.TestCase):
    """His rule, and the reason for it: an auto-healer can turn one fault into two, unattended."""

    def test_the_module_writes_nothing(self):
        import inspect
        src = inspect.getsource(HE)
        for forbidden in ("os.remove", "unlink", "rmtree", "subprocess", "kill", '"w"', "'w'"):
            self.assertNotIn(forbidden, src,
                             "health_engine must stay a reader; found %r" % forbidden)

    def test_every_check_returns_a_state_the_surface_can_render(self):
        rep = HE.report()
        self.assertTrue(rep["rows"], "no checks ran at all")
        for r in rep["rows"]:
            self.assertIn(r["state"], (HE.OK, HE.WARN, HE.BLOCKED, HE.UNKNOWN))
            self.assertTrue(r["line"], "%s produced no line for him to read" % r["id"])
            self.assertTrue(r["measuredAt"], "%s carries no measurement time" % r["id"])


class TestUnknownIsNeverOk(unittest.TestCase):
    """⚠ THE WHOLE POINT. "the board is not open so its store cannot be asked" is not "fine"."""

    def test_an_unoffered_board_is_UNKNOWN_not_ok(self):
        r = HE.check_board_join(None)
        self.assertEqual(r["state"], HE.UNKNOWN)
        self.assertIn("not the same as", r["line"])

    def test_a_board_that_does_not_answer_is_UNKNOWN(self):
        def boom(_js):
            raise RuntimeError("window is gone")
        self.assertEqual(HE.check_board_join(boom)["state"], HE.UNKNOWN)

    def test_an_unreadable_answer_is_UNKNOWN(self):
        self.assertEqual(HE.check_board_join(lambda _js: "not json")["state"], HE.UNKNOWN)

    def test_a_check_that_RAISES_is_UNKNOWN_not_dropped(self):
        # a check that throws must not vanish from the report — silence would read as ok
        def explode():
            raise ValueError("boom")
        old = HE.CHECKS[:]
        HE.CHECKS.append(explode)
        try:
            rep = HE.report()
            hit = [r for r in rep["rows"] if r["state"] == HE.UNKNOWN and "raised" in r["line"]]
            self.assertTrue(hit, "a raising check disappeared from the report instead of reporting UNKNOWN")
        finally:
            HE.CHECKS[:] = old

    def test_UNKNOWN_alone_stops_the_whole_report_being_ok(self):
        rep = HE.report()          # board_join is unknown with no evaluate injected
        self.assertNotEqual(rep["state"], HE.OK)


class TestTheBoardJoinCheck(unittest.TestCase):
    """The check the register failure needed. The console asking ITSELF must read BLOCKED."""

    def test_the_console_asking_itself_is_BLOCKED_and_says_so(self):
        r = HE.check_board_join(lambda _js: '{"p":"/","has":false}')
        self.assertEqual(r["state"], HE.BLOCKED)
        self.assertIn("CONSOLE, not the board", r["line"])

    def test_a_reachable_board_is_ok(self):
        r = HE.check_board_join(lambda _js: '{"p":"/board","has":true}')
        self.assertEqual(r["state"], HE.OK)

    def test_console_with_handoff_note_is_UNKNOWN_not_blocked_and_not_ok(self):
        """CF-2 — the console cannot call chronicleApply; it CAN leave a note. That is the door,
        and calling it BLOCKED is the tautology that taught him to skip the row.

        ⚠ BUT IT IS NOT OK EITHER, AND THE FIRST CUT OF THIS TEST SAID IT WAS — its own name
        asserted `is_ok_not_blocked`. The flag it rests on, control_app.py:11406, is

            var canHandoff = !!(window.LSR && window.LSR.setItem);

        which proves A WRITER OBJECT EXISTS — not that a note was written, that the board drained
        it, or that any handoff completed. An OK built on "the capability is present" is how an
        unjoined end hides, and a test named after the wrong answer is how it survives review.

        UNKNOWN is the honest state and it composes with CF-8, which now gives the row its age.
        OK becomes correct when there is a drained marker or an acknowledgement from the board
        side — evidence a handoff COMPLETED, not that one could be attempted.
        [[unknown-stays-unknown]] [[the-unjoined-end]]"""
        r = HE.check_board_join(payload={
            "ok": True, "path": "/", "hasChronicleApply": False, "canHandoff": True})
        self.assertEqual(r["state"], HE.UNKNOWN, r.get("line"))
        self.assertNotEqual(r["state"], HE.BLOCKED,
                            "a designed handoff path must not read as a fault")
        self.assertIn("note", r["line"])
        self.assertIn("confirm", r["line"].lower(),
                      "the row must say WHY it is unknown — that nobody has seen the handoff "
                      "complete — or the state is just a word")


class TestTheArmedSweepReadsTheREALSHAPES(unittest.TestCase):
    """★ v2281 — NO HARDCODED FLAG NAMES. The first cut carried one tuple naming
    d2r_vaultBackfill_v2200 by hand, so it caught the v2205 loaded gun only because I already knew
    the answer, and would have missed the next one entirely."""

    #: the real shape in bible.html — a CONST, never a literal. My first reader matched only
    #: `getItem('flag')` and found nothing at all. [[source-reading-guard]]
    REAL = ("var DONE = 'd2r_thing_v1';\n"
            "if (window.LSR.getItem(DONE)) return;\n")

    def test_it_resolves_a_flag_bound_to_a_CONST(self):
        flag, how = HE._flag_of("DONE", self.REAL)
        self.assertEqual(flag, "d2r_thing_v1")
        self.assertIn("const", how)

    def test_it_still_reads_a_plain_literal(self):
        flag, how = HE._flag_of("'d2r_x'", "")
        self.assertEqual((flag, how), ("d2r_x", "literal"))

    def test_an_UNRESOLVABLE_gate_is_reported_not_skipped(self):
        """⚠ a gate whose flag cannot be resolved is not a SAFE gate — it is an unread one, and
        skipping it silently is how the next armed migration walks past this check."""
        src = "if (!window.LSR.getItem(MYSTERY)) return;\n"
        rows = HE.armed_flags(src)
        self.assertTrue(rows, "an unresolvable gate vanished instead of being reported")
        self.assertTrue(rows[0]["unresolved"])
        self.assertIn("UNRESOLVED", rows[0]["how"])

    def test_the_SAFE_polarity_is_not_flagged(self):
        # "already done, skip" — a stray stamp DISABLES the block, which is the harmless direction
        self.assertEqual(HE.armed_flags(self.REAL), [])

    def test_the_DANGEROUS_polarity_with_a_stamp_IS_flagged(self):
        src = ("var DONE = 'd2r_thing_v1';\n"
               "window.LSR.setItem(DONE, JSON.stringify({retired:'v2'}));\n"
               "if (!window.LSR.getItem(DONE)) return;\n")
        rows = HE.armed_flags(src)
        self.assertEqual([r["flag"] for r in rows], ["d2r_thing_v1"])
        self.assertGreater(rows[0]["stamps"], 0)

    def test_a_reader_that_MATCHES_NOTHING_is_UNKNOWN_not_ok(self):
        """★ THE BRANCH THAT SAVED THIS SHIP. When the reader missed every real site it said
        UNKNOWN — 'a broken reader, not a clean tree' — instead of reporting a green sweep over
        zero sites. A check that cannot find its subject has measured nothing. [[regression-guard]]"""
        import tempfile, shutil
        root = tempfile.mkdtemp(prefix="noshape-")
        self.addCleanup(shutil.rmtree, root, True)
        os.makedirs(os.path.join(root, "tv"))
        with io.open(os.path.join(root, "bible.html"), "w", encoding="utf-8") as fh:
            fh.write("<html>nothing that looks like a one-shot gate at all</html>")
        old = HE.HERE
        HE.HERE = os.path.join(root, "tv")
        try:
            r = HE.check_armed_migrations()
        finally:
            HE.HERE = old
        self.assertEqual(r["state"], HE.UNKNOWN)
        self.assertIn("broken reader", r["line"])

    def test_the_real_tree_finds_BOTH_polarities_so_the_zero_is_measured(self):
        """A zero is only a measurement if the instrument demonstrably finds things. Measured on
        bible.html 2026-08-30: 4 safe-polarity gates, 0 dangerous ones."""
        with io.open(os.path.join(os.path.dirname(HE.HERE), "bible.html"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertGreaterEqual(len(HE._SAFE_RE.findall(src)), 1,
                                "the safe polarity is no longer found, so a clean verdict on the "
                                "dangerous one proves nothing")


class TestTheBoardJoinPayloadPath(unittest.TestCase):
    """⚠ THE PATH THAT ACTUALLY RUNS. Nothing on the console holds a window handle to hand this
    module, so the `evaluate` door was a tap nobody could open and this flag was UNKNOWN for ever.
    A flag that can only ever say one thing is furniture. [[plumbing-with-no-tap]]"""

    def test_a_reachable_board_is_ok(self):
        r = HE.check_board_join(payload={"ok": True, "hasChronicleApply": True, "path": "/board"})
        self.assertEqual(r["state"], HE.OK)
        self.assertIn("/board", r["line"])

    def test_the_console_answering_for_the_board_is_BLOCKED_and_names_the_page(self):
        r = HE.check_board_join(payload={"ok": True, "hasChronicleApply": False, "path": "/"})
        self.assertEqual(r["state"], HE.BLOCKED)
        self.assertIn("CONSOLE, not the board", r["line"])

    def test_a_console_build_too_old_to_answer_is_UNKNOWN_not_ok(self):
        # his RUNNING console serves the code it booted with; a build without the field must not
        # read as a healthy join. Measured live 2026-08-29 — this is the real state today.
        r = HE.check_board_join(payload={"ok": True, "boardLoaded": True})
        self.assertEqual(r["state"], HE.UNKNOWN)
        self.assertIn("nobody asked", r["line"])

    def test_a_refusing_or_absent_board_is_UNKNOWN(self):
        for p in ({"ok": False, "why": "the board window is not open"}, None, "junk"):
            if p is None:
                continue                       # None means "no payload offered" — the other path
            self.assertEqual(HE.check_board_join(payload=p)["state"], HE.UNKNOWN)

    def test_the_payload_beats_the_evaluate_door_when_both_are_offered(self):
        # one answer, not two that can disagree
        r = HE.check_board_join(evaluate=lambda _js: '{"p":"/","has":false}',
                                payload={"ok": True, "hasChronicleApply": True, "path": "/board"})
        self.assertEqual(r["state"], HE.OK)

    def test_report_threads_the_payload_through(self):
        rep = HE.report(board={"ok": True, "hasChronicleApply": True, "path": "/board"})
        row = [r for r in rep["rows"] if r["id"] == "board_join"][0]
        self.assertEqual(row["state"], HE.OK,
                         "report() dropped the board payload on the floor, so the console rail "
                         "would go on reporting UNKNOWN whatever the board said")


class TestTheConsoleRailIsTheONLYSurface(unittest.TestCase):
    """He asked for \"one unit system engine locked in\". This machine already had FOUR things
    implementing report-never-repair; a fifth parallel surface would be [[copy-drift]] exactly."""

    def test_the_eagle_eye_carries_every_health_check(self):
        import console_doctor as CD
        names = [n for n, _ in CD.CHECKS]
        for want in ("armed migration", "extraction lanes", "board join", "stray processes"):
            self.assertIn(want, names,
                          "%r is not on the eagle-eye rail, so it is a flag nobody sees" % want)

    def test_the_rail_maps_UNKNOWN_to_UNKNOWN(self):
        # the one distinction that may never be lost in the state map
        import console_doctor as CD
        state, detail = CD._health("board_join")()
        self.assertIn(state, (CD.OK, CD.MISSING, CD.UNKNOWN))
        self.assertTrue(detail)

    def test_one_tick_reads_HIS_BOARD_once_not_three_times(self):
        """/api/board_ownership EVALUATES JAVASCRIPT IN THE WINDOW HE IS LOOKING AT. Three checks
        need it now and two of those predate this fold, so the rail was already poking his live
        board twice every ten minutes with nothing saying so. [[borrowed-surface]]"""
        import console_doctor as CD
        calls, real = [], CD._post
        CD._post = lambda p, b=None, timeout=20: (calls.append(p),
                                                  {"ok": True, "boardLoaded": False})[1]
        try:
            CD.run(include_slow=False)
        finally:
            CD._post = real
        self.assertEqual(calls.count("/api/board_ownership"), 1,
                         "one rail tick asked his board %d times"
                         % calls.count("/api/board_ownership"))

    def test_OUTSIDE_a_tick_every_check_reads_fresh(self):
        """⚠ THE PROPERTY MY FIRST CUT BROKE. A 5-second module-level memo swallowed the `_post`
        stub and served the previous test's answer — EIGHT existing guards failed at once, which is
        a shape mistake, not eight defects. [[feedback-suspect-the-instrument]]"""
        import console_doctor as CD
        calls, real = [], CD._post
        CD._post = lambda p, b=None, timeout=20: (calls.append(p), {"ok": True})[1]
        try:
            CD._board_read(); CD._board_read()
        finally:
            CD._post = real
        self.assertEqual(len(calls), 2,
                         "a check called on its own reused a cached answer, so any guard that "
                         "stubs _post is now measuring the previous test")

    def test_a_check_that_disappears_reads_UNKNOWN_not_ok(self):
        import console_doctor as CD
        # the tick must be OPEN for the injected report to be the one consulted — outside a tick
        # every check reads fresh, which is the property that keeps stubbed guards working
        CD._health_cache["active"] = True
        CD._health_cache["rep"] = {"rows": [], "state": "ok", "why": ""}
        try:
            state, detail = CD._health("armed_migration")()
        finally:
            CD._health_cache["active"] = False
            CD._health_cache["rep"] = None
        self.assertEqual(state, CD.UNKNOWN)
        self.assertIn("no longer reports", detail)


class TestTheArmedMigrationCheck(unittest.TestCase):
    """⚠ THE CHECK THAT WOULD HAVE CAUGHT THE LOADED GUN. The v2205 undo was armed on every board
    since v2203 and would have dropped 273 of his 280 owned names, and nothing watched for it."""

    def test_it_is_GREEN_on_the_current_tree(self):
        self.assertEqual(HE.check_armed_migrations()["state"], HE.OK)

    def test_it_WOULD_HAVE_GONE_RED_on_the_pre_fix_code(self):
        # ⚠ A CHECK NOBODY HAS SEEN FIRE IS NOT A CHECK. Rebuild the exact pre-v2275 shape — a
        # retirement that stamps the flag, and a gate that trusts the flag's PRESENCE — and prove
        # this check calls it ARMED. [[regression-guard]]
        import tempfile, shutil
        root = tempfile.mkdtemp(prefix="armed-")
        self.addCleanup(shutil.rmtree, root, True)
        os.makedirs(os.path.join(root, "tv"))
        with io.open(os.path.join(root, "bible.html"), "w", encoding="utf-8") as fh:
            fh.write("var DONE='d2r_vaultBackfill_v2200';\n"
                     "window.LSR.setItem(DONE, JSON.stringify({retired:'v2203'}));\n"
                     "if (!window.LSR.getItem('d2r_vaultBackfill_v2200')) return;   // it never ran here\n")
        old_here = HE.HERE
        HE.HERE = os.path.join(root, "tv")
        try:
            r = HE.check_armed_migrations()
        finally:
            HE.HERE = old_here
        self.assertEqual(r["state"], HE.BLOCKED,
                         "the pre-fix code did NOT read as armed — this check would have watched "
                         "the v2205 undo sit loaded and said nothing")
        self.assertIn("ARMED", r["line"])


class TestWilsonIsTheFifthOrganOfTheHeart(unittest.TestCase):
    """★ v2438 — Konyo: "the heart should be wilson score too, not just doctor / eagle eye /
    watchdog / corroborator — wilson score embedded in it too."

    The heart scores rows in ONE place. What these cases defend is the distinction the whole
    self-proving idea rests on, and it is easy to lose to a `or 0`:

        UNTESTED (n=0)  -> score None   work owed, and NOT a fault
        INERT   (0 of N)-> score 0.0    it WAS tested and could not refuse — the dangerous one

    An invariant that always agrees may be perfect or inert, and no amount of agreement tells
    them apart. If these two collapse, a lock opens because nobody ever tried to break it.
    """

    def test_untested_scores_NONE_not_zero(self):
        r = HE._row("x", HE.OK, "l", k=0, n=0)
        self.assertIsNone(r["score"],
                          "n=0 produced a NUMBER. 'nobody looked' would then be indistinguishable "
                          "from 'it scored zero', and untested work would read as a failure")
        self.assertEqual(r["proofN"], 0)

    def test_INERT_scores_zero_and_is_NOT_none(self):
        r = HE._row("x", HE.OK, "l", k=0, n=40)
        self.assertEqual(r["score"], 0.0,
                         "40 sabotages, 0 refusals must score 0.0 — a guard that cannot say no is "
                         "the defect, and it must never hide behind the untested state")

    def test_a_row_with_no_proof_history_carries_no_score_FIELD_at_all(self):
        r = HE._row("x", HE.OK, "l")
        self.assertNotIn("score", r,
                         "a check with no proof history published a score field. An absent field "
                         "and a null score are both honest; a fabricated one is not")

    def test_the_score_comes_from_confidence_not_a_local_copy(self):
        import inspect
        src = inspect.getsource(HE._row)
        code = "\n".join(l.split("#", 1)[0] for l in src.split("\n"))
        self.assertIn("from confidence import wilson_lower", code)
        self.assertNotIn("def wilson", code,
                         "a second copy of the Wilson maths in the heart. [[copy-drift]] — two "
                         "copies of one law diverge and only one gets tuned")

    def test_the_scale_matches_the_published_reference(self):
        """confidence.py publishes 2/2=0.342, 4/4=0.510, 10/10=0.722, 20/20=0.839 and the lock
        bars are set from those. If the scale moves, every bar silently means something else."""
        for k, n, want in ((2, 2, 0.342), (4, 4, 0.510), (10, 10, 0.722), (20, 20, 0.839)):
            got = HE._row("x", HE.OK, "l", k=k, n=n)["score"]
            self.assertAlmostEqual(got, want, places=2,
                                   msg="%d/%d scored %.3f, not the published %.3f — the lock bars "
                                       "are calibrated to this scale" % (k, n, got, want))


class TestTheDecidingSentenceIsTHEONEPRINTED(unittest.TestCase):
    """★ v2437 — THE PANEL PRINTED TWO SENTENCES DESCRIBING A HEALTHY LANE, UNDER THE WORD MISSING.

    console_doctor renders `"; ".join(_clip(x, 110) for x in evidence[:2])` — only the first TWO.
    check_lanes built its evidence lanes-first, divergences-last, so with two lanes and one
    divergence the [:2] kept both "last did work N h ago" lines and DROPPED the divergence, which
    is the only sentence that says what is wrong.

    The cost was a MISDIAGNOSIS, not a cosmetic one: CF-1 was filed as "chronicle and vault both
    stopped doing work hours ago". Measured, neither had stopped — both sat under their 48h
    threshold with owed 0. The fault was a divergence, and the console could not say so.

    The law pinned here is ORDERING, not a number: whatever `worst` is, its sentence is first.
    Pinning "evidence[0] mentions divergence" would go quietly wrong the day a stalled lane is
    the worst finding. [[regression-guard]] — pin the law, not the number.
    """

    def _row(self, lanes, divs):
        class _LH(object):
            @staticmethod
            def report(*a, **k):
                return {"lanes": lanes, "divergences": divs, "ok": False}
        return _LH

    def test_the_worst_finding_leads_the_evidence(self):
        lanes = {"chronicle": {"state": "fresh", "why": "chronicle: fine, 20h ago"},
                 "vault": {"state": "fresh", "why": "vault: fine, 23h ago"}}
        divs = [{"state": "diverged", "pair": ["chronicle", "vault"],
                 "why": "THE ACTUAL PROBLEM: 25 sessions with footage the vault never sealed"}]
        sys.modules["lane_health"] = self._row(lanes, divs)
        try:
            r = HE.check_lanes()
        finally:
            sys.modules.pop("lane_health", None)
        ev = r["evidence"]
        self.assertEqual(ev[0], divs[0]["why"],
                         "the deciding sentence is not first, so the console's [:2] will drop "
                         "it and print two healthy-looking lines under a fault")
        self.assertIn(divs[0]["why"], ev[:2],
                      "the reason must survive the two-item cut the renderer applies")

    def test_a_STALLED_lane_leads_when_IT_is_the_worst(self):
        """The ordering must follow `worst`, not the word 'divergence'."""
        lanes = {"chronicle": {"state": "stalled", "why": "chronicle: STOPPED 90h ago"},
                 "vault": {"state": "fresh", "why": "vault: fine"}}
        divs = [{"state": "aligned", "pair": ["chronicle", "vault"], "why": "they agree"}]
        sys.modules["lane_health"] = self._row(lanes, divs)
        try:
            r = HE.check_lanes()
        finally:
            sys.modules.pop("lane_health", None)
        self.assertEqual(r["evidence"][0], "chronicle: STOPPED 90h ago")

    def test_no_sentence_is_LOST_by_the_reordering(self):
        """Reordering must not drop evidence — the panel cuts it, this function must not."""
        lanes = {"chronicle": {"state": "fresh", "why": "A"},
                 "vault": {"state": "fresh", "why": "B"}}
        divs = [{"state": "diverged", "pair": ["chronicle", "vault"], "why": "C"}]
        sys.modules["lane_health"] = self._row(lanes, divs)
        try:
            r = HE.check_lanes()
        finally:
            sys.modules.pop("lane_health", None)
        self.assertEqual(sorted(r["evidence"]), ["A", "B", "C"])


class AHardenedLockIsOpenAndARouteIsNotALock(unittest.TestCase):
    """Gap audit #5. This row counted OPEN only, and it counted routes as locks. A shelf
    of HARDENED valves read as none open, under OK, including on a PC whose heart had
    never run and where may() was refusing every one of them."""

    def _ask(self, locks, heart_ok=True, heart_why=""):
        import self_arming as SA
        real = SA.report
        SA.report = lambda: {"ok": True, "locks": locks,
                             "heartOk": heart_ok, "heartWhy": heart_why}
        self.addCleanup(setattr, SA, "report", real)
        return HE.check_self_arming()

    def _one(self, name, state, kind=None, k=2, n=2):
        row = {"lock": name, "state": state, "why": "fixture", "k": k, "n": n}
        if kind:
            row["kind"] = kind
        return row

    def test_a_HARDENED_valve_counts_as_open(self):
        import self_arming as SA
        r = self._ask([self._one("frame.release", SA.HARDENED)])
        self.assertEqual(r["state"], HE.OK)
        # REG-3215 - the act question leads; the evidence tier is the "(N proven)" beside it
        self.assertIn("(1 proven)", r["line"])
        self.assertNotIn("(0 proven)", r["line"])

    def test_a_route_is_not_one_of_the_locks(self):
        import self_arming as SA
        r = self._ask([
            self._one("frame.release", SA.UNPROVEN),
            self._one("chronicle", SA.HARDENED, kind="route"),
        ])
        self.assertIn("of 1 may act now", r["line"])
        self.assertIn("(0 proven)", r["line"])
        self.assertIn("1 of 1 routes proven", r["line"])
        self.assertNotIn("of 2 may act", r["line"])
        self.assertNotIn("2 of 2", r["line"])

    def test_an_INCOMPLETE_axis_is_named(self):
        import self_arming as SA
        r = self._ask([self._one("miniauto.run", SA.INCOMPLETE, k=0, n=0)])
        self.assertEqual(r["state"], HE.OK)
        self.assertIn("1 incomplete", r["line"])
        self.assertIn("(0 proven)", r["line"])

    def test_a_missing_heart_is_not_an_open_row(self):
        import self_arming as SA
        r = self._ask([self._one("frame.release", SA.HARDENED)],
                      heart_ok=False, heart_why="the heart has never run here")
        self.assertEqual(r["state"], HE.UNKNOWN)
        self.assertIn("(1 proven)", r["line"])
        self.assertIn("none of that may act here", r["line"])
        self.assertIn("the heart has never run here", r["line"])
        self.assertEqual(r.get("proofN"), 2)

    def test_a_stale_census_is_named_and_is_not_a_fault(self):
        import self_arming as SA
        r = self._ask([self._one("frame.release", SA.HARDENED)],
                      heart_ok=False,
                      heart_why="the heart census is STALE: the gate files have changed")
        self.assertEqual(r["state"], HE.OK)
        self.assertIn("census is STALE", r["line"])
        self.assertNotIn("none of that may act here", r["line"])

    def test_a_route_that_did_not_refuse_is_named_a_route_and_kept_out_of_the_lock_score(self):
        """REG-1950 (the #231 eye on 2f5cb714)."""
        import self_arming as SA
        r = self._ask([self._one("frame.release", SA.UNPROVEN, k=0, n=0),
                       self._one("chronicle", SA.LOCKED, kind="route", k=0, n=4)])
        self.assertEqual(r["state"], HE.WARN, "a route that did not refuse stopped being a warning")
        self.assertIn("1 route(s) were sabotaged and did not refuse", r["line"])
        self.assertNotIn("lock(s) were sabotaged", r["line"], "a route was reported as a lock (REG-1950)")
        self.assertEqual(r.get("proofN"), 0, "a route's trials are in the lock score")

    def test_a_lock_that_did_not_refuse_is_still_the_warning(self):
        import self_arming as SA
        r = self._ask([self._one("frame.release", SA.LOCKED, k=0, n=3)],
                      heart_ok=False, heart_why="the heart has never run here")
        self.assertEqual(r["state"], HE.WARN)
        self.assertIn("did not refuse", r["line"])
        self.assertEqual(r.get("proofN"), 3)


if __name__ == "__main__":
    try:
        import console_safe as _cs
        _cs.enable()
    except Exception:
        pass
    unittest.main(verbosity=1)
