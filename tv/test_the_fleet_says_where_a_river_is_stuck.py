# -*- coding: utf-8 -*-
"""#74 — THE FLEET SAYS WHERE A PC'S RIVER IS STUCK, AND WHY (REG-1461).

His ask 2026-09-29, after the ALT was found with 76 reels at EMPTY and 25 at PRINTER for two days and nothing
on any screen said so: *"we need to be able to see that deans console is also architectured correctly ...
see whats getting updated/fetched and logged and registered live while hes on playing"* - step 1, the alarm.

Three joints, each driven, never grepped:
  · the console: `_river_stuck_for_wire` over stamp rows - ONE rule for every reel on the shelf (REG-1812):
    inside the newest KEEP_RECENT a reel at a station a lane owns that waited > 6 h is named with that
    station's own reason (CAPTURE waits by design, ROUTED is kept); PAST the window every station owes the
    drain, counted from the later of its arrival and its exit from the window, marked window False; an
    unreadable log is None, never "flowing"; a console that has not computed its river does not walk the log.
  · the worker (functions/api/console.js, the REAL shaper in node): stuck/heart cross shaped - bad keys
    dropped, text scrubbed of paths; null stays null; absent stays absent.
  · the card (control_ui.html, the REAL _fleetSysParts / _fleetStuckChip in node): a red "river stuck" on the
    row, the stations with their age in the detail, "none" when it drains, UNKNOWN when it cannot say.
    A proof that is missing, stale or unreadable is "locks shut" on that same row, and a null stuck list or a
    null census is "river UNKNOWN" — not the empty chip a draining river uses. The verdict hover keeps both sentences.
    A presence key older than two refreshes plus one beacon is not "here": the dot is silent and the words
    say presence UNKNOWN, never ON AIR.
    A restart the console could not ask about is not "clear to restart": may null says UNKNOWN and keeps
    the why, and that sentence is the pending span's text because the hover strips titles.
    A pull git could not answer is not a pull that is fine: can null says pull UNKNOWN and keeps the why
    in the span's text. can false stays not pulling. can true stays quiet. No pull object stays quiet.
    A reel the router could not place is not the whole river: unknown and shelf ride with the stations,
    the line names unplaced and a gap against that shelf, a zero map over a shelf that holds reels is
    not called empty, and a change in either count is news. A missing count stays off the wire.
RED_PROOF below.
"""
import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import test_the_fleet_card_says_how_each_pc_films_and_drains as F  # noqa: E402  (its node harness)
import test_each_console_says_its_own_system as S  # noqa: E402  (its worker slicer)

H = 3600
NOW = F.NOW


def _stamp(reel, station, ago_s, seq):
    return {"at": NOW - int(ago_s * 1000), "seq": seq, "reel": reel, "station": station,
            "by": "law", "byKind": "observer"}


class TheConsoleNamesItsStuckStations(unittest.TestCase):

    def _stuck(self, rows, shelf=None, fixtures=()):
        """every reel in `rows` is on the shelf unless `shelf` names which are (REG-1614)"""
        import control_app as ca
        on = set(r["reel"] for r in rows) if shelf is None else shelf
        return ca._river_stuck_for_wire(now_ms=NOW, _rows=rows, _shelf=on, _fixtures=fixtures)

    def test_a_reel_gone_from_the_shelf_or_pinned_by_the_suite_is_never_stuck(self):
        """REG-1614 - his Mac on 2026-09-30: 27 'stuck', of which 16 were closed out by retention, 1 reaped by the disk
        floor and 4 were suite fixtures. A reel that has left the shelf cannot be stuck on it, and a fixture never
        moves by design - neither is an alarm. PREMISE: the same rows with every reel on the shelf DO alarm."""
        rows = [_stamp("reel_s_1_on", "EMPTY", 40 * H, 1), _stamp("reel_s_2_gone", "JOIN", 30 * H, 2),
                _stamp("reel_s_3_pin", "TRIAGE", 20 * H, 3), _stamp("reel_s_4_on", "PRINTER", 10 * H, 4)]
        every = {e["station"] for e in self._stuck(rows)}
        self.assertEqual(every, {"EMPTY", "JOIN", "TRIAGE", "PRINTER"}, "PREMISE: the rows do not alarm at all")
        got = {e["station"]: e["n"] for e in self._stuck(rows, shelf={"reel_s_1_on", "reel_s_3_pin", "reel_s_4_on"},
                                                          fixtures=("reel_s_3_pin",))}
        self.assertEqual(got, {"EMPTY": 1, "PRINTER": 1}, "a reel off the shelf or a suite fixture was called stuck")

    def test_the_real_shelf_is_asked_and_an_unreadable_one_is_unknown(self):
        """the default path asks the console's own shelf folder, one reel at a time; no shelf folder at all is None
        (UNKNOWN), never an empty list that reads as a river draining"""
        import shutil
        import tempfile
        from unittest import mock
        import control_app as ca
        d = tempfile.mkdtemp(prefix="stuck_shelf_")
        self.addCleanup(shutil.rmtree, d, True)
        os.makedirs(os.path.join(d, "reel_s_1_on"))
        rows = [_stamp("reel_s_1_on", "EMPTY", 40 * H, 1), _stamp("reel_s_2_gone", "EMPTY", 30 * H, 2)]
        with mock.patch.object(ca, "HIST_DIR", d):
            got = ca._river_stuck_for_wire(now_ms=NOW, _rows=rows, _fixtures=())
        self.assertEqual([(e["station"], e["n"]) for e in got], [("EMPTY", 1)], got)
        with mock.patch.object(ca, "HIST_DIR", os.path.join(d, "no_such_shelf")):
            self.assertIsNone(ca._river_stuck_for_wire(now_ms=NOW, _rows=rows, _fixtures=()),
                              "a shelf that is not there read as a river draining")

    def test_a_route_this_pc_never_proved_names_what_its_prover_waits_for(self):
        """REG-1614 - the ALT on 2026-09-30: its row said 'Run python3 tv/heart2.py --prove', the one thing a prove beside
        his game must never be (REG-1502). With the route locked and this PC's census not current, the reason is its own
        prover's word; with the census current, a locked route still says the lane's own reason."""
        from unittest import mock
        import control_app as ca
        locked = {"why": "reel.route is LOCKED — the heart has never run here, so nothing has shown that the gates "
                         "watching this surface can still go red. Run `python3 tv/heart2.py --prove`. UNKNOWN fails CLOSED."}
        playing = "he is playing on this PC (the game or its cloud client) - a proof never starts beside it"
        with mock.patch.object(ca, "_ROUTE_LANE", locked), \
                mock.patch.object(ca, "_SELF_PROVE", {"census": "absent", "key": "playing", "say": playing}):
            w = ca._river_stuck_why("EMPTY")
        self.assertIn("proves its own gates", w)
        self.assertIn(playing, w)
        self.assertNotIn("heart2.py --prove", w, "the ALT is told to run a prove beside his game")
        merit = {"why": "reel.route is LOCKED — 3 of 7 refusals seen; the bar is 0.510"}
        with mock.patch.object(ca, "_ROUTE_LANE", merit), \
                mock.patch.object(ca, "_SELF_PROVE", {"census": "current", "key": "current", "say": "current"}):
            self.assertEqual(ca._river_stuck_why("EMPTY"), "route lane: " + merit["why"])

    def test_the_alts_shape_is_named_with_ages(self):
        rows = [_stamp("reel_s_1_a", "TRIAGE", 50 * H, 1), _stamp("reel_s_1_a", "EMPTY", 40 * H, 2),
                _stamp("reel_s_2_b", "EMPTY", 20 * H, 3), _stamp("reel_s_3_c", "PRINTER", 38 * H, 4),
                _stamp("reel_s_4_d", "PRINTER", 1 * H, 5),          # fresh - not stuck
                _stamp("reel_s_5_e", "CAPTURE", 90 * H, 6),         # by design - never an alarm
                _stamp("reel_s_6_f", "ROUTED", 90 * H, 7)]          # the far end
        got = {e["station"]: e for e in self._stuck(rows)}
        self.assertEqual(sorted(got), ["EMPTY", "PRINTER"], got)
        self.assertEqual(got["EMPTY"]["n"], 2)
        self.assertEqual(got["EMPTY"]["oldestS"], 40 * H)
        self.assertEqual(got["PRINTER"]["n"], 1, "a reel at PRINTER for an hour was called stuck")
        for e in got.values():
            self.assertTrue(e["why"], "a stuck station was named without its lane's reason")

    def test_a_long_reason_ends_at_a_word_and_says_it_was_cut(self):
        """REG-1987 - GrokBot tick 388: tips ended "...the heart census is S" and "...the lane could not be". A bare
        [:200] cut the lane's own sentence mid-word; the wire sentence ends at a word with an ellipsis."""
        import control_app as ca
        from unittest import mock
        long_why = ("the route lane is shut until this PC proves its own gates and the heart census is STALE " * 4).strip()
        self.assertGreater(len(long_why), 200)
        rows = [_stamp("reel_s_1_a", "EMPTY", 40 * H, 1)]
        with mock.patch.object(ca, "_river_stuck_why", lambda st: long_why):
            got = self._stuck(rows)
        why = got[0]["why"]
        self.assertLessEqual(len(why), 200)
        self.assertTrue(why.endswith("…"), "a cut reason did not say it was cut: %r" % why[-30:])
        self.assertIn(why[:-1].rsplit(" ", 1)[-1], long_why.split(" "),
                      "the reason was cut mid-word: %r" % why[-30:])
        short = "the vault lane is waiting on its canary"
        with mock.patch.object(ca, "_river_stuck_why", lambda st: short):
            self.assertEqual(self._stuck(rows)[0]["why"], short, "a reason that fits was changed")

    def test_a_flowing_river_is_an_empty_list_and_an_unreadable_log_is_none(self):
        self.assertEqual(self._stuck([_stamp("reel_s_1_a", "EMPTY", 60, 1)]), [])
        import control_app as ca
        from unittest import mock
        import river_stamp as rvs
        with mock.patch.object(rvs, "rows", lambda path=None: {"ok": False, "rows": [], "why": "law"}):
            self.assertIsNone(ca._river_stuck_for_wire(now_ms=NOW), "an unreadable log read as FLOWING")

    def test_a_river_nobody_ever_stamped_is_unknown_while_reels_wait(self):
        """REG-1738 (#86 gap item 8) - no stamp log at all answered [] ("draining") whatever sat on the shelf."""
        import control_app as ca
        from unittest import mock
        import river_stamp as rvs
        never = {"ok": True, "rows": [], "everStamped": False, "why": "no stamp has ever been recorded"}
        with mock.patch.object(rvs, "rows", lambda path=None: never):
            self.assertIsNone(ca._river_stuck_for_wire(now_ms=NOW, _shelf={"reel_s_1_a"}, _fixtures=()),
                              "a shelf of reels with no stamp ever written read as FLOWING")
            self.assertEqual(ca._river_stuck_for_wire(now_ms=NOW, _shelf=set(), _fixtures=()), [],
                             "an empty shelf with no stamps is measured-and-empty")
            self.assertEqual(ca._river_stuck_for_wire(now_ms=NOW, _shelf={"reel_s_9_pin"},
                                                      _fixtures=("reel_s_9_pin",)), [],
                             "a suite fixture alone made the river UNKNOWN")
            # REG-1812 - a reel past the window is in this reading too: the newest sixteen are fixtures here
            import reel_retention as rr
            # 2017-epoch names (test_a_gate_may_not_pin_his_footage): no recording carries them
            pins = ["reel_s_%d_%d" % (1500000000100 + i, i) for i in range(int(rr.KEEP_RECENT))]
            self.assertIsNone(ca._river_stuck_for_wire(now_ms=NOW, _shelf=set(pins) | {"reel_s_1500000000000_99"},
                                                       _fixtures=tuple(pins)),
                              "an unstamped reel older than the window read as FLOWING")

    def _rows_of(self, got):
        return [(e["station"], e["n"], e["oldestS"], e.get("window")) for e in got]

    def test_every_reel_on_the_shelf_is_in_the_one_rule(self):
        """REG-1812. Inside reel_retention.recent_shield a reel at a lane's station that waited is stuck; a
        fresh one, a fixture and CAPTURE are not. PAST the window the four older PRINTER reels are not dropped
        (8c710efe dropped them): they are their own row, window False, with the vault lane's word. JOIN does
        not borrow the route lane's CAPTURE sentence."""
        import reel_retention as rr
        keep = int(rr.KEEP_RECENT)
        self.assertGreaterEqual(keep, 5, "KEEP_RECENT is too small for this fixture to discriminate")
        extra = 4

        def nm(i):
            return "reel_s_%d_%d" % (1700000000000 + i, i)

        n = keep + extra
        rows, shelf = [], set()
        for i in range(n):
            name = nm(i)
            shelf.add(name)
            if i < extra:
                rows.append(_stamp(name, "PRINTER", 80 * H, i))
            elif i == extra:
                rows.append(_stamp(name, "CAPTURE", 90 * H, i))
            elif i == extra + 1:
                rows.append(_stamp(name, "PRINTER", 50 * H, i))
            elif i == n - 1:
                rows.append(_stamp(name, "PRINTER", 60, i))
            elif i == n - 2:
                rows.append(_stamp(name, "JOIN", 40 * H, i))
            else:
                rows.append(_stamp(name, "PRINTER", 30 * H, i))
        got = self._stuck(rows, shelf=shelf, fixtures=(nm(extra + 1),))
        self.assertEqual(self._rows_of(got), [("PRINTER", extra, 80 * H, False), ("JOIN", 1, 40 * H, None),
                                              ("PRINTER", keep - 4, 30 * H, None)], got)
        why = {(e["station"], e.get("window")): e["why"] for e in got}
        self.assertIn("older than the newest %d" % keep, why[("PRINTER", False)])
        self.assertIn("vault lane", why[("PRINTER", False)], "a reel past the window lost its lane's word")
        self.assertNotIn("older than", why[("PRINTER", None)], "a reel inside the window was called older")
        self.assertNotIn("capture", why[("JOIN", None)].lower())
        # REG-2004 - JOIN has a lane (slice 4's one re-read, then the route lane); its word is that lane's state, never
        # reel_router.OWES's "No lane can fix that" slogan, which was false while 16 re-reads had already run.
        self.assertIn("the join lane:", why[("JOIN", None)])
        self.assertNotIn("No lane can fix that", why[("JOIN", None)])

    def test_the_alts_dam_past_the_window_is_named(self):
        """#168 - his ALT 2026-10-06: the newest 16 draining, and 84 older reels at PRINTER for up to 9 days. The
        windowed alarm read "none - the newest 16 are draining" over all of them."""
        import reel_retention as rr
        keep = int(rr.KEEP_RECENT)
        dam = 62

        def nm(i):
            return "reel_s_%d_%d" % (1789000000000 + i * 60000, i)

        rows, shelf = [], set()
        for i in range(dam + keep):
            shelf.add(nm(i))
            if i < dam:
                rows.append(_stamp(nm(i), "PRINTER", (9 * 24 - i) * H, i))
            else:
                rows.append(_stamp(nm(i), "ROUTED" if i % 2 else "PRINTER", 30 * 60, i))
        got = self._stuck(rows, shelf=shelf)
        self.assertEqual(self._rows_of(got), [("PRINTER", dam, 9 * 24 * H, False)], got)
        self.assertIn("vault lane", got[0]["why"])

    def test_a_reel_just_pushed_out_is_not_owed_yet(self):
        """REG-1812. A reel that sat at ROUTED for days inside the window is kept. The newest arrival pushes it
        out, and the drain gets the same six hours from THAT moment (reel_retention.shield_exits), not from
        when it reached ROUTED - else every new reel would paint the river stuck until the next pass."""
        import reel_retention as rr
        keep = int(rr.KEEP_RECENT)

        def world(pushed_ago_s):
            t_new = NOW - int(pushed_ago_s * 1000)
            names = ["reel_s_%d_%d" % (t_new - (keep - i) * 6 * H * 1000, i) for i in range(keep)]
            names.append("reel_s_%d_%d" % (t_new, keep))
            rows = [_stamp(names[0], "ROUTED", 90 * H, 0)]
            rows += [_stamp(r, "ROUTED", 60, k + 1) for k, r in enumerate(names[1:])]
            return rows, set(names)

        rows, shelf = world(1 * H)
        self.assertEqual(self._stuck(rows, shelf=shelf), [], "a reel pushed out an hour ago is already owed")
        rows, shelf = world(7 * H)
        self.assertEqual(self._rows_of(self._stuck(rows, shelf=shelf)), [("ROUTED", 1, 7 * H, False)],
                         "the patience did not start at the exit")

    def test_capture_past_the_window_is_owed_and_inside_it_is_not(self):
        """His ruling names CAPTURE: no station may hold a reel for ever. Inside the window it waits on a
        capture change by design; past it, only the drain moves it."""
        import reel_retention as rr
        keep = int(rr.KEEP_RECENT)

        def nm(i):
            return "reel_s_%d_%d" % (1700000000000 + i, i)

        rows, shelf = [], set()
        for i in range(keep + 2):
            shelf.add(nm(i))
            rows.append(_stamp(nm(i), "CAPTURE", 90 * H, i))
        got = self._stuck(rows, shelf=shelf)
        self.assertEqual(self._rows_of(got), [("CAPTURE", 2, 90 * H, False)], got)
        self.assertIn("older than the newest %d - the drain owes them a tombstone" % keep, got[0]["why"])
        self.assertNotIn("still at", got[0]["why"], "the sentence repeats the station its row already names (REG-2098)")

    def test_the_owed_sentence_carries_the_drains_last_word(self):
        """A row past the window at the deleter's own stage names why the last pass did not pay it - the lock on
        his Mac, the ON AIR hold on his ALT. A process whose pass never ran says only the debt."""
        from unittest import mock
        import control_app as ca
        said = {"checked": NOW, "say": "11.1GB free and 37 reel(s) could go, but the deleter refused: "
                                         "frame.release is LOCKED"}
        with mock.patch.object(ca, "_RETENTION", said):
            w = ca._river_owed_why("ROUTED", 16)
        self.assertIn("- the drain owes them a tombstone - the drain: 11.1GB free", w)
        self.assertIn("frame.release is LOCKED", w)
        with mock.patch.object(ca, "_RETENTION", {"checked": None, "say": "not measured yet"}):
            self.assertNotIn("the drain:", ca._river_owed_why("ROUTED", 16))

    def test_two_stations_owing_the_same_debt_read_word_for_word_alike(self):
        """REG-2098 (GrokBot tick 427 K03) - the tip said ROUTED 8's and CAPTURE 5's tombstone debt twice ('still at ROUTED'
        / 'still at CAPTURE'), and STATION 5's reason twice beside STATION 4 older: the prefixed copy was cut at 200 AFTER
        the prefix, so its tail ended at another word. Same debt, same words - the tip can then say it once."""
        from unittest import mock
        import control_app as ca
        said = {"checked": NOW, "say": "12.5GB free and 5 reel(s) could go, but the deleter refused: frame.release is LOCKED"}
        with mock.patch.object(ca, "_RETENTION", said):
            self.assertEqual(ca._river_owed_why("ROUTED", 16), ca._river_owed_why("CAPTURE", 16),
                             "two stations owing the same tombstone are worded apart")
        long_why = ("the reel sweep owes 10 read(s) - its last word: the sweep door is LOCKED until the census " * 4).strip()
        owner = sorted(ca._RIVER_OWNER)[0]
        with mock.patch.object(ca, "_river_stuck_why", lambda st: long_why):
            older = ca._river_owed_why(owner, 16)
            inside = ca._word_cut(long_why, 200)
        self.assertTrue(older.startswith("older than the newest 16 - "), older[:40])
        self.assertEqual(older[len("older than the newest 16 - "):], inside,
                         "the older copy of a lane's reason ends at a different word than the copy inside the window")

    def test_the_alarm_has_one_counting_loop(self):
        """REG-1812 - one rule, not a copy per station: 23e37f91 added a second loop for ROUTED alone. AST of the
        shipped function: exactly one `for` walks the river's last stamps."""
        import ast
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_river_stuck_for_wire"]
        self.assertEqual(len(fns), 1)
        walks = [n for n in ast.walk(fns[0]) if isinstance(n, ast.For)
                 and isinstance(n.iter, ast.Call) and isinstance(n.iter.func, ast.Attribute)
                 and n.iter.func.attr == "items" and isinstance(n.iter.func.value, ast.Name)
                 and n.iter.func.value.id == "last"]
        self.assertEqual(len(walks), 1, "%d loops walk the last stamps - a station has its own rule again"
                         % len(walks))

    def test_a_routed_reel_older_than_the_window_is_owed_to_the_drain(self):
        """#86 gap 10. The newest KEEP_RECENT stay, including one already at ROUTED. An older reel
        still at ROUTED past six hours has left that shield, so the drain owes it a tombstone. A
        fixture, a reel off the shelf, and a young one outside the window do not."""
        import reel_retention as rr
        keep = int(rr.KEEP_RECENT)
        extra = 4

        def nm(i):
            return "reel_s_%d_%d" % (1700000000000 + i, i)

        rows, shelf = [], set()
        for i in range(keep + extra):
            name = nm(i)
            if i == 2:
                rows.append(_stamp(name, "ROUTED", 90 * H, i))
                continue
            shelf.add(name)
            if i == 0:
                rows.append(_stamp(name, "ROUTED", 90 * H, i))
            elif i == 1:
                rows.append(_stamp(name, "ROUTED", 90 * H, i))
            elif i == 3:
                rows.append(_stamp(name, "ROUTED", 60, i))
            elif i == 4:
                rows.append(_stamp(name, "ROUTED", 90 * H, i))
            else:
                rows.append(_stamp(name, "EMPTY", H, i))
        got = self._stuck(rows, shelf=shelf, fixtures=(nm(1),))
        self.assertEqual(len(got), 1, got)
        self.assertEqual(got[0]["station"], "ROUTED")
        self.assertEqual(got[0]["n"], 1, got)
        self.assertEqual(got[0]["oldestS"], 90 * H)
        self.assertIs(got[0]["window"], False)
        self.assertIn("drain owes", got[0]["why"])
        self.assertIn(str(keep), got[0]["why"])

    def test_the_shelf_on_disk_uses_the_same_window(self):
        import shutil
        import tempfile
        from unittest import mock
        import control_app as ca
        import reel_retention as rr
        keep = int(rr.KEEP_RECENT)
        d = tempfile.mkdtemp(prefix="stuck_win_")
        self.addCleanup(shutil.rmtree, d, True)

        def nm(i):
            return "reel_s_%d_%d" % (1700000000000 + i, i)

        extra = 3
        rows = []
        for i in range(keep + extra):
            name = nm(i)
            os.makedirs(os.path.join(d, name))
            rows.append(_stamp(name, "EMPTY", (80 * H if i < extra else 40 * H), i))
        with mock.patch.object(ca, "HIST_DIR", d):
            got = ca._river_stuck_for_wire(now_ms=NOW, _rows=rows, _fixtures=())
        self.assertEqual(self._rows_of(got), [("EMPTY", extra, 80 * H, False), ("EMPTY", keep, 40 * H, None)],
                         got)

    def test_join_does_not_borrow_the_route_lane_and_empty_still_does(self):
        from unittest import mock
        import control_app as ca
        capture = "a capture change - the item name is printed on the character panel"
        with mock.patch.object(ca, "_ROUTE_LANE", {"why": capture}):
            join = ca._river_stuck_why("JOIN")
            station = ca._river_stuck_why("STATION")
            empty = ca._river_stuck_why("EMPTY")
        self.assertNotIn("capture", join.lower())
        self.assertIn("the join lane:", join)       # REG-2004 - the join lane's own word, not the route lane's
        self.assertIn("NOT ITS INPUT", station)
        self.assertNotIn("capture", station.lower())
        self.assertIn("capture", empty.lower(), "EMPTY stopped quoting the route lane")

    def test_station_says_the_sweeps_own_word_while_the_sweep_owes_reads(self):
        """REG-1844 - his Mac 2026-10-06: 7 reels past the window at STATION, all never chronicle-swept and owed by the
        sweep's own rule, and the drain printed "A LANE EXISTS AND THIS QUEUE IS NOT ITS INPUT" over a sweep whose door
        was locked. While the sweep owes reads, STATION quotes the sweep; when it owes none, the note is the truth."""
        from unittest import mock
        import control_app as ca
        locked = ("the sweep door is LOCKED on this machine, so the try was NOT counted: vault.sweep_start is LOCKED - "
                  "the heart census is STALE")
        with mock.patch.object(ca, "_chron_owed_count", lambda *a, **k: 7), \
                mock.patch.object(ca, "_CHRON_AUTOREAD_SAY", {"last": locked}):
            w = ca._river_stuck_why("STATION")
        self.assertIn("owes 7 read(s)", w)
        self.assertIn("vault.sweep_start is LOCKED", w)
        self.assertNotIn("NOT ITS INPUT", w, "the note blamed a predicate split over a locked sweep door")
        for owed in (0, None):
            with mock.patch.object(ca, "_chron_owed_count", lambda *a, **k: owed), \
                    mock.patch.object(ca, "_CHRON_AUTOREAD_SAY", {"last": locked}):
                self.assertIn("NOT ITS INPUT", ca._river_stuck_why("STATION"),
                              "a sweep owing %r reads lost the river walk's note" % (owed,))
        # REG-1863 - a fresh console: the sweep owes reads and has said nothing yet. That is not the note's case either.
        for quiet in ({"last": ""}, {"last": None}):
            with mock.patch.object(ca, "_chron_owed_count", lambda *a, **k: 7), \
                    mock.patch.object(ca, "_CHRON_AUTOREAD_SAY", quiet):
                w = ca._river_stuck_why("STATION")
            self.assertEqual(w, "the reel sweep owes 7 read(s) - it has not spoken since this console started", w)

    def test_an_uncomputed_river_does_not_invent_a_stuck_list(self):
        from unittest import mock
        import control_app as ca
        called = []

        def _walk(*a, **k):
            called.append(1)
            return [{"station": "EMPTY", "n": 9, "oldestS": 1, "why": "route lane: capture"}]

        with mock.patch.object(ca, "_RIVER_LAST", {"good": None, "fail": None}), \
                mock.patch.object(ca, "_river_stuck_for_wire", _walk):
            out = ca._river_for_wire(now_ms=NOW)
        self.assertIsNone(out["lanes"])
        self.assertIsNone(out["stuck"])
        self.assertNotIn("stuckKeep", out)
        self.assertEqual(called, [], "the stamp walker ran for a river that was never computed")

    def test_a_computed_river_still_carries_the_window(self):
        from unittest import mock
        import control_app as ca
        import reel_retention as rr
        called = []

        def _walk(*a, **k):
            called.append(1)
            return []

        good = {"stations": {"PRINTER": 2}, "ts": NOW - 1000, "n": 1}
        fail = {"ts": NOW, "n": 2, "why": "the last river read failed"}
        with mock.patch.object(ca, "_RIVER_LAST", {"good": good, "fail": fail}), \
                mock.patch.object(ca, "_river_stuck_for_wire", _walk):
            out = ca._river_for_wire(now_ms=NOW)
        self.assertEqual(out["lanes"]["PRINTER"], 2)
        self.assertIn("newer river read failed", out["why"])
        self.assertEqual(out["stuck"], [])
        self.assertEqual(out["stuckKeep"], int(rr.KEEP_RECENT))
        self.assertEqual(called, [1], "a computed river dropped its stuck reading")

        def _unread(*a, **k):
            return None

        with mock.patch.object(ca, "_RIVER_LAST", {"good": good, "fail": None}), \
                mock.patch.object(ca, "_river_stuck_for_wire", _unread):
            bad = ca._river_for_wire(now_ms=NOW)
        self.assertIsNone(bad["stuck"], "an unreadable log on a computed river read as flowing")
        self.assertNotIn("stuckKeep", bad)


class TheWorkerCarriesIt(unittest.TestCase):

    def _shape(self, river):
        return S.TheRelayShapesIt._shape(self, {"tree": "ok", "reels": 3, "river": river})

    def test_stuck_and_heart_cross_shaped(self):
        got = self._shape({"lanes": {"PRINTER": 25}, "stuck": [
            {"station": "PRINTER", "n": 25, "oldestS": 38 * H, "why": r"vault lane: owes 0 C:\Users\Dean Smith\tv\x.json"},
            {"station": "bad station", "n": 1, "oldestS": 1, "why": "x"}],
            "heart": {"census": "missing", "key": "busy", "blind": 0}})
        rv = got["river"]
        self.assertEqual([e["station"] for e in rv["stuck"]], ["PRINTER"], "a bad station key crossed")
        self.assertNotIn("Dean", rv["stuck"][0]["why"], "a user path crossed the PUBLIC wire")
        # v3862 (REG-3160) - the meter and the why ride beside the census; a beacon that sends none reads them null
        self.assertEqual(rv["heart"], {"census": "missing", "key": "busy", "blind": 0, "owed": None, "ratePerH": None,
                                       "etaS": None, "why": None})

    def test_null_stays_null_and_absent_stays_absent(self):
        self.assertIsNone(self._shape({"lanes": {}, "stuck": None})["river"]["stuck"])
        self.assertNotIn("stuck", self._shape({"lanes": {}})["river"], "an older console gained a field")

    def test_the_window_crosses_only_with_a_measured_list(self):
        got = self._shape({"lanes": {"PRINTER": 1}, "stuck": [], "stuckKeep": 16})["river"]
        self.assertEqual(got["stuck"], [])
        self.assertEqual(got["stuckKeep"], 16)
        dropped = self._shape({"lanes": {}, "stuck": [], "stuckKeep": "16"})["river"]
        self.assertNotIn("stuckKeep", dropped, "a window that is not a count crossed")
        unknown = self._shape({"lanes": {}, "stuck": None, "stuckKeep": 16})["river"]
        self.assertIsNone(unknown["stuck"])
        self.assertNotIn("stuckKeep", unknown, "an unknown river grew a window")

    def test_unplaced_and_the_shelf_cross_and_a_bad_count_does_not(self):
        """#86 gap 14. The station map is not the shelf. A whole count crosses. Absent stays
        absent. A string, a negative and a count past the cap do not become zero."""
        got = self._shape({"lanes": {"EMPTY": 76, "PRINTER": 25}, "unknown": 25, "shelf": 126})["river"]
        self.assertEqual(got["unknown"], 25)
        self.assertEqual(got["shelf"], 126)
        zero = self._shape({"lanes": {"EMPTY": 4}, "unknown": 0, "shelf": 4})["river"]
        self.assertEqual(zero["unknown"], 0)
        self.assertEqual(zero["shelf"], 4)
        old = self._shape({"lanes": {"EMPTY": 76}})["river"]
        self.assertNotIn("unknown", old, "an older console gained a count")
        self.assertNotIn("shelf", old)
        bad = self._shape({"lanes": {"EMPTY": 1}, "unknown": "25", "shelf": -3})["river"]
        self.assertNotIn("unknown", bad, "a count that is not a count crossed as zero")
        self.assertNotIn("shelf", bad)
        over = self._shape({"lanes": {"EMPTY": 1}, "unknown": 100001, "shelf": 100001})["river"]
        self.assertNotIn("unknown", over, "a count past the cap crossed")
        self.assertNotIn("shelf", over)

    def test_a_reel_outside_the_window_keeps_that_mark(self):
        got = self._shape({"lanes": {"ROUTED": 1}, "stuck": [
            {"station": "ROUTED", "n": 4, "oldestS": 90 * H,
             "why": "older than the newest 16, still at ROUTED, so the drain owes them a tombstone",
             "window": False},
            {"station": "PRINTER", "n": 1, "oldestS": 40 * H, "why": "vault lane: owes 1",
             "window": "false"}]})["river"]
        self.assertIs(got["stuck"][0]["window"], False)
        self.assertNotIn("window", got["stuck"][1], "a mark that is not false crossed")


class TheCardSaysIt(unittest.TestCase):

    def _run(self, river):
        row = F._row(t_ago_s=60, river=dict({"lanes": {"PRINTER": 25}, "ageS": 30.0, "why": "", "triage": F.TRI_OK},
                                             **river))
        return F._run("var p = _fleetSysParts(%s, NOW); OUT.p = {}; p.forEach(function(x){ OUT.p[x.k] = "
                      "{ t: plain(x.t), unk: !!x.unk, warn: !!x.warn, why: x.why }; });"
                      "OUT.chip = strip(_fleetStuckChip(%s)); OUT.chipHtml = _fleetStuckChip(%s);"
                      % (json.dumps(row), json.dumps(row), json.dumps(row)))

    def test_a_stuck_pc_says_so_on_the_row_and_in_the_detail(self):
        out = self._run({"stuck": [{"station": "PRINTER", "n": 25, "oldestS": 38 * H,
                                    "why": "vault lane: owes 0"}], "heart": {"census": "missing", "blind": None}})
        st = out["p"]["stuck"]
        self.assertTrue(st["warn"], "a stuck river was not drawn as a warning")
        self.assertIn("PRINTER 25 for", st["t"])
        self.assertIn("vault lane: owes 0", st["why"])
        self.assertIn("river stuck", out["chip"], "the row does not say the river is stuck")
        self.assertIn("locks shut", out["chip"], "a missing proof beside a stuck river left the locks off the row")
        self.assertIn("vault lane: owes 0", out["chipHtml"], "the row's hover does not carry the reason")
        self.assertIn("never proved on this PC", out["p"]["proved"]["t"])
        self.assertTrue(out["p"]["proved"]["warn"])

    def test_a_draining_pc_is_calm_and_an_unknown_one_says_unknown(self):
        out = self._run({"stuck": [], "heart": {"census": "current", "blind": 0}})
        self.assertIn("none", out["p"]["stuck"]["t"])
        self.assertFalse(out["p"]["stuck"]["warn"])
        self.assertEqual(out["chip"], "", "a draining PC grew an alarm")
        self.assertFalse(out["p"]["proved"]["warn"])
        out = self._run({"stuck": None})
        self.assertTrue(out["p"]["stuck"]["unk"], "an unreadable log read as draining")
        self.assertIn("stamp log", out["p"]["stuck"]["why"])
        self.assertIn("river UNKNOWN", out["chip"], "a null stuck list drew the same empty chip as a draining river")
        self.assertNotIn("river stuck", out["chip"])
        self.assertNotIn("locks shut", out["chip"])

    def test_an_uncomputed_river_says_unknown_for_that_reason(self):
        why = "this console has not computed its river since it started"
        out = self._run({"stuck": None, "lanes": None, "why": why})
        self.assertTrue(out["p"]["stuck"]["unk"])
        self.assertIn(why, out["p"]["stuck"]["why"])
        self.assertNotIn("stamp log", out["p"]["stuck"]["why"])
        self.assertIn("river UNKNOWN", out["chip"], "an uncomputed river drew the same empty chip as a draining one")
        self.assertNotIn("river stuck", out["chip"], "an unknown river grew an alarm")

    def test_a_clear_window_names_how_many_reels_it_tallied(self):
        out = self._run({"stuck": [], "stuckKeep": 16, "heart": {"census": "current", "blind": 0}})
        self.assertIn("newest 16", out["p"]["stuck"]["t"])
        self.assertIn("none", out["p"]["stuck"]["t"])
        self.assertFalse(out["p"]["stuck"]["warn"])
        self.assertEqual(out["chip"], "", "a clear window grew an alarm")
        old = self._run({"stuck": [], "heart": {"census": "current", "blind": 0}})
        self.assertIn("every station is draining", old["p"]["stuck"]["t"])
        self.assertNotIn("newest", old["p"]["stuck"]["t"])

    def test_an_empty_stuck_list_under_shut_locks_is_not_draining(self):
        """REG-1960 - GrokBot tick 387: Dean's row wore 'locks shut' while its tip said 'every station is draining'."""
        for census in ("missing", "stale", "unreadable"):
            with self.subTest(census=census):
                out = self._run({"stuck": [], "stuckKeep": 16, "heart": {"census": census, "blind": None}})
                self.assertIn("locks shut", out["chip"], "baseline: the row did not wear the shut locks")
                self.assertNotIn("draining", out["p"]["stuck"]["t"],
                                 "a PC whose locks are shut was told its stations are draining (REG-1960)")
                self.assertIn("nothing drains", out["p"]["stuck"]["t"])
                self.assertIn(census, out["p"]["stuck"]["why"])

    def test_a_stuck_window_stays_on_the_row(self):
        out = self._run({"stuck": [{"station": "PRINTER", "n": 7, "oldestS": 40 * H,
                                    "why": "vault lane: owes 1"}], "stuckKeep": 16})
        self.assertIn("river stuck", out["chip"], "a reel stuck inside the window lost its chip")
        self.assertIn("PRINTER 7 for", out["p"]["stuck"]["t"])
        self.assertIn("among the newest 16", out["p"]["stuck"]["why"])
        self.assertTrue(out["p"]["stuck"]["warn"])

    def test_an_older_routed_reel_is_not_called_one_of_the_newest(self):
        why = "older than the newest 16, still at ROUTED, so the drain owes them a tombstone"
        out = self._run({"stuck": [{"station": "ROUTED", "n": 4, "oldestS": 90 * H,
                                    "why": why, "window": False}], "stuckKeep": 16})
        self.assertIn("ROUTED 4 older for", out["p"]["stuck"]["t"])     # REG-2007 - the chip says it is past the window
        self.assertIn(why, out["p"]["stuck"]["why"])
        self.assertNotIn("among the newest", out["p"]["stuck"]["why"])
        self.assertTrue(out["p"]["stuck"]["warn"])
        self.assertIn("river stuck", out["chip"])
        self.assertIn("drain owes", out["chipHtml"])

    def _chip(self, river):
        row = F._row(t_ago_s=60, river=dict({"lanes": {"EMPTY": 76}, "ageS": 30.0, "why": "", "triage": F.TRI_OK},
                                             **river))
        return F._run("OUT.chip = strip(_fleetStuckChip(%s)); OUT.html = _fleetStuckChip(%s);"
                      "OUT.hover = plain(_fleetHoverPlain(%s, 'idle · v1', NOW));"
                      % (json.dumps(row), json.dumps(row), json.dumps(row)))

    def test_a_shut_proof_is_on_the_row_and_a_null_reading_is_not_draining(self):
        """#86 gap 9. The row's only dam word was river stuck, and only when the list had stations.
        A missing, stale or unreadable proof is locks shut. A null census, or a null stuck list, is
        river UNKNOWN. The verdict hover keeps the stuck sentence and the proved sentence."""
        for word in ("missing", "stale", "unreadable"):
            out = self._chip({"stuck": [], "heart": {"census": word, "blind": None}})
            self.assertIn("locks shut", out["chip"], word)
            self.assertIn("fleet-riverstuck", out["html"], word)
            self.assertNotIn("river stuck", out["chip"], word)
            self.assertNotIn("river UNKNOWN", out["chip"], word)
            self.assertIn("proved:", out["hover"], word)
            self.assertIn("stuck:", out["hover"], word)
        shut = self._chip({"stuck": [], "heart": {"census": "missing", "blind": None}})
        self.assertIn("never proved on this PC", shut["hover"])
        calm = self._chip({"stuck": [], "heart": {"census": "current", "blind": 0}})
        self.assertEqual(calm["chip"], "", "a current proof with nothing stuck grew a word")
        self.assertIn("proved:", calm["hover"], "a calm river dropped its proved sentence from the hover")
        self.assertIn("stuck:", calm["hover"])
        null_census = self._chip({"stuck": [], "heart": {"census": None}})
        self.assertEqual(null_census["chip"], "river UNKNOWN")
        self.assertIn("fleet-riverunk", null_census["html"])
        self.assertNotIn("locks shut", null_census["chip"])
        both = self._chip({"stuck": None, "heart": {"census": "missing"}})
        self.assertIn("locks shut", both["chip"])
        self.assertIn("river UNKNOWN", both["chip"])
        self.assertEqual(F.UI.count("var plain = _fleetHoverPlain(m, meta);"), 1,
                         "the verdict hover no longer asks for the stuck and proved sentences")


class AStalePresenceIsNotOnline(unittest.TestCase):
    """#86 gap 12. The presence key lives 40 minutes so a quiet console is not evicted.
    The card was painting that key as here: green dot, and ON AIR in the hover for the whole
    wait, including a console that died while it was recording."""

    def _pres(self, ago_s, online=True, t=True):
        row = {"nickname": "ALT", "machine": "box-b", "ver": "v3595", "mode": "live"}
        if t is True and ago_s is not None:
            row["t"] = F._iso(NOW - int(ago_s * 1000))
        elif isinstance(t, str):
            row["t"] = t
        import fleet_presence as _fp   # v3850 - the server stamps presence; the card only reads it
        row["presence"] = _fp.presence_of(row, bool(online), NOW)
        return F._run("OUT.p = _fleetPresence(%s, %s, NOW);"
                      % (json.dumps(row), "true" if online else "false"))["p"]

    def test_a_fresh_beacon_is_still_here(self):
        p = self._pres(40)
        self.assertEqual(p["state"], "here", p)
        self.assertEqual(p["dot"], "")
        self.assertEqual(p["word"], "")
        self.assertNotIn("UNKNOWN", p["why"])

    def test_a_beacon_older_than_two_refreshes_is_not_on_air(self):
        """v3850 (Elad 17:51) - one bar, fleet_presence.STALE_AFTER_S (one refresh + one beacon + 60 s; 8 min on Workers Paid).
        At the bar a row is still here; one second past it the card says offline with its last-seen age."""
        import fleet_presence as _fp
        still = self._pres(_fp.STALE_AFTER_S)
        self.assertEqual(still["state"], "here", still)
        gone = self._pres(_fp.STALE_AFTER_S + 1)
        self.assertEqual(gone["state"], "silent", gone)
        self.assertEqual(gone["dot"], "silent")
        self.assertIn("offline \u00b7 last seen %d min ago" % ((_fp.STALE_AFTER_S + 1) // 60), gone["word"])
        self.assertNotIn("ON AIR", gone["word"])
        died = self._pres(38 * 60)
        self.assertIn("last seen 38 min ago", died["word"])
        self.assertNotIn("ON AIR", died["word"])

    def test_a_beacon_time_the_card_cannot_read_is_unknown_not_here(self):
        missing = self._pres(None, t=False)
        self.assertEqual(missing["state"], "unknown", missing)
        self.assertEqual(missing["dot"], "silent")
        self.assertIn("presence UNKNOWN", missing["word"])
        self.assertNotIn("ON AIR", missing["word"])
        self.assertNotIn("offline", missing["word"].lower())
        future = self._pres(0, t=F._iso(NOW + 60000))
        self.assertEqual(future["state"], "unknown", future)
        self.assertNotIn("ON AIR", future["word"])

    def test_an_offline_row_keeps_its_own_sentence(self):
        self.assertIsNone(self._pres(10, online=False))

    def test_the_row_asks_that_verdict_before_it_draws_the_dot(self):
        ui = F.UI
        self.assertEqual(ui.count("var pres = _fleetPresence(m, online);"), 1)
        self.assertEqual(ui.count("var heard = !!(pres && pres.state === 'here');"), 1)
        self.assertIn("fleet-dot' + (heard ? '' : (online ? ' silent' : ' off'))", ui)
        self.assertIn("fleet-row' + (heard ? ' on' : '')", ui)
        self.assertIn("_fleetShadowEye(m, heard, undefined, pres)", ui)   # REG-1833 - the eye gets the presence answer too
        self.assertIn("_fleetRowChips(m, heard)", ui)
        self.assertIn("escC(pres.word)", ui)


class AnUnaskedRestartIsNotClearToGo(unittest.TestCase):
    """#86 gap 15. The pending badge's else said clear to restart whenever may was not false.
    null is the console saying it could not ask. That is not a yes, and the why stays."""

    def _say(self, relaunch):
        return F._run("OUT.s = _fleetRelaunchSay(%s);" % json.dumps(relaunch))["s"]

    def test_a_measured_yes_is_clear_and_a_measured_no_names_the_hold(self):
        yes = self._say({"armed": True, "may": True, "why": ""})
        self.assertIn("clear to restart", yes)
        self.assertNotIn("UNKNOWN", yes)
        no = self._say({"armed": True, "may": False, "why": "waiting for the shadow reel to close"})
        self.assertIn("holding off because: waiting for the shadow reel to close", no)
        self.assertNotIn("clear to restart", no)
        self.assertNotIn("UNKNOWN", no)
        off = self._say({"armed": False, "may": None, "why": "could not ask whether a restart is safe right now"})
        self.assertIn("Auto-relaunch is OFF", off)
        self.assertNotIn("UNKNOWN", off)
        self.assertNotIn("clear to restart", off)

    def test_an_unasked_restart_is_unknown_and_keeps_the_why(self):
        why = "could not ask whether a restart is safe right now"
        got = self._say({"armed": True, "may": None, "why": why})
        self.assertIn("whether it may restart is UNKNOWN", got)
        self.assertIn(why, got)
        self.assertNotIn("clear to restart", got)
        self.assertNotIn("holding off", got)
        bare = self._say({"armed": True, "may": None, "why": ""})
        self.assertIn("UNKNOWN", bare)
        self.assertNotIn("clear to restart", bare)
        self.assertNotIn("\u2014", bare)

    def test_an_older_console_that_sent_no_relaunch_says_nothing(self):
        self.assertEqual(self._say(None), "")

    def test_the_hover_keeps_the_sentence_the_title_would_have_lost(self):
        """The hover strips tags. A sentence only in the title is the same as silence, and silence
        here used to read as clear. The pending span's text is what the hover keeps."""
        why = "could not ask whether a restart is safe right now"
        out = F._run(
            "var say = _fleetRelaunchSay(%s);\n"
            "var meta = '<span class=\"fleet-pending\" title=\"outstanding.' + say + '\"> · v3596 on disk' + say + '</span>';\n"
            "OUT.hover = plain(_fleetHoverPlain({nickname:'ALT'}, meta, NOW));\n"
            "OUT.say = say;" % json.dumps({"armed": True, "may": None, "why": why}))
        self.assertIn("whether it may restart is UNKNOWN", out["hover"])
        self.assertIn(why, out["hover"])
        self.assertNotIn("clear to restart", out["hover"])
        ui = F.UI
        i = ui.index('class="fleet-pending"')
        span = ui[i:ui.index("</span>", i)]
        self.assertIn("only the ", span)
        self.assertIn("_fleetRelaunchSay(m.relaunch)", span.split(">", 1)[1],
                      "the restart sentence is only in the title, and the hover strips titles")
        self.assertEqual(ui.count("var _fleetRelaunchSay = function"), 1)


class AnUnreadablePullIsNotAPullThatIsFine(unittest.TestCase):
    """#86 gap 16. can null used to draw nothing, so the server's "N behind" read as a
    machine that would catch up. can false stays not pulling. can true stays quiet.
    No pull object is an older console. The why is the span's text: the hover strips titles."""

    def _say(self, pull):
        return F._run("OUT.s = _fleetPullSay(%s);" % json.dumps(pull))["s"]

    def test_a_clear_pull_is_quiet_and_a_refused_one_is_not_called_unknown(self):
        clear = self._say({"can": True, "behind": 6, "why": "6 commits behind and clear to pull"})
        self.assertEqual(clear, "")
        refused = self._say({"can": False, "behind": 4,
                             "why": "local tracked edits — a fast-forward would not be safe here"})
        self.assertEqual(refused, "")
        level = self._say({"can": False, "behind": 0, "why": "pinned: TV_NO_AUTO_PULL is set on this machine"})
        self.assertEqual(level, "")

    def test_an_unreadable_pull_is_unknown_and_keeps_the_why(self):
        why = "git could not answer"
        got = self._say({"can": None, "behind": None, "why": why})
        self.assertIn("pull UNKNOWN", got)
        self.assertIn(why, got)
        self.assertNotIn("not pulling", got)
        zero = self._say({"can": None, "behind": 0, "why": why})
        self.assertIn("pull UNKNOWN", zero)
        self.assertIn(why, zero)
        bare = self._say({"can": None, "why": ""})
        self.assertIn("pull UNKNOWN", bare)
        self.assertNotIn("\u2014", bare)
        self.assertNotIn("not pulling", bare)

    def test_an_older_console_that_sent_no_pull_says_nothing(self):
        self.assertEqual(self._say(None), "")

    def test_the_hover_keeps_unknown_beside_the_behind_count(self):
        """The hover strips tags. A why only in the title is silence, and silence beside
        "N behind" is a pull that looks as if it will catch up."""
        why = "git could not answer"
        out = F._run(
            "var say = _fleetPullSay(%s);\n"
            "var meta = '<span class=\"fleet-lag\">· 6 behind</span>' +\n"
            "  '<span class=\"fleet-pullunk\" title=\"title only ' + say + '\">' + say + '</span>';\n"
            "OUT.hover = plain(_fleetHoverPlain({nickname:'ALT'}, meta, NOW));\n"
            "OUT.say = say;\n"
            "var clear = _fleetPullSay(%s);\n"
            "var calm = '<span class=\"fleet-lag\">· 6 behind</span>';\n"
            "OUT.clear = clear;\n"
            "OUT.calm = plain(_fleetHoverPlain({nickname:'ALT'}, calm, NOW));"
            % (json.dumps({"can": None, "behind": None, "why": why}),
               json.dumps({"can": True, "behind": 6, "why": "6 commits behind and clear to pull"})))
        self.assertIn("pull UNKNOWN", out["say"])
        self.assertIn(why, out["hover"])
        self.assertIn("6 behind", out["hover"])
        self.assertIn("pull UNKNOWN", out["hover"])
        self.assertNotIn("not pulling", out["hover"])
        self.assertEqual(out["clear"], "")
        self.assertIn("6 behind", out["calm"])
        self.assertNotIn("pull UNKNOWN", out["calm"])
        self.assertNotIn("not pulling", out["calm"])

    def test_the_row_keeps_refused_and_unknown_apart(self):
        ui = F.UI
        self.assertEqual(ui.count("var _fleetPullSay = function"), 1)
        self.assertEqual(ui.count("var pullSay = _fleetPullSay(m.pull);"), 1)
        i = ui.index('class="fleet-pullunk"')
        text = ui[i:ui.index("</span>", i)].split(">", 1)[1]
        self.assertIn("pullSay", text)
        self.assertNotIn("not pulling", text)
        j = ui.index('class="fleet-stuck"')
        stuck = ui[j:ui.index("</span>", j)]
        self.assertIn("not pulling", stuck.split(">", 1)[1])
        self.assertNotIn("pullSay", stuck)
        import re
        def col(cls):
            k = ui.index("." + cls + "{")
            return re.search(r"color:(#[0-9a-fA-F]+)", ui[k:ui.index("}", k)]).group(1).lower()
        self.assertNotEqual(col("fleet-pullunk"), col("fleet-stuck"))
        self.assertNotEqual(col("fleet-pullunk"), col("fleet-lag"))


class AnUnplacedReelIsNotTheWholeRiver(unittest.TestCase):
    """#86 gap 14. The beacon used to keep only byStation, so the card drew the placed stations
    as every reel. unknown and shelf come from the same river block. A missing count is an
    older console and is not zero."""

    def _drive(self, lanes):
        from unittest import mock
        import control_app as ca
        fresh = {"good": None, "fail": None}
        with mock.patch.object(ca, "_RIVER_LAST", fresh), \
                mock.patch.object(ca, "_river_stuck_for_wire", lambda *a, **k: []):
            ca._river_remember(lanes)
            return ca._river_for_wire(now_ms=NOW)

    def test_unknown_and_the_shelf_ride_with_the_stations(self):
        out = self._drive({"ok": True, "unknown": 25, "shelf": 126,
                           "lanes": [{"byStation": {"EMPTY": 76, "PRINTER": 25}}]})
        self.assertEqual(out["lanes"], {"EMPTY": 76, "PRINTER": 25})
        self.assertEqual(out["unknown"], 25)
        self.assertEqual(out["shelf"], 126)

    def test_a_measured_zero_is_kept_and_a_missing_count_is_not_sent_as_zero(self):
        zero = self._drive({"ok": True, "unknown": 0, "shelf": 4,
                            "lanes": [{"byStation": {"EMPTY": 4}}]})
        self.assertEqual((zero["unknown"], zero["shelf"]), (0, 4))
        bare = self._drive({"ok": True, "lanes": [{"byStation": {"EMPTY": 1}}]})
        self.assertEqual(bare["lanes"], {"EMPTY": 1})
        self.assertNotIn("unknown", bare)
        self.assertNotIn("shelf", bare)
        bad = self._drive({"ok": True, "unknown": "25", "shelf": True,
                           "lanes": [{"byStation": {"EMPTY": 1}}]})
        self.assertEqual(bad["lanes"], {"EMPTY": 1})
        self.assertNotIn("unknown", bad, "a string crossed as zero unplaced")
        self.assertNotIn("shelf", bad, "a bool crossed as a shelf of 1")

    def _line(self, **river):
        base = {"lanes": {"EMPTY": 0, "PRINTER": 0}, "ageS": 30.0, "why": "", "triage": F.TRI_OK}
        base.update(river)
        return F._parts(F._row(60, river=base))["river"]["t"]

    def test_a_full_shelf_the_router_could_not_place_is_not_called_empty(self):
        t = self._line(lanes={"EMPTY": 0, "PRINTER": 0}, unknown=126, shelf=126)
        self.assertIn("126 unplaced", t)
        self.assertNotIn("empty", t)
        self.assertNotIn("unaccounted", t)
        self.assertNotIn("counted twice", t)

    def test_a_gap_beside_the_placed_stations_is_named(self):
        t = self._line(lanes={"EMPTY": 76, "PRINTER": 25}, unknown=0, shelf=126)
        self.assertIn("EMPTY 76", t)
        self.assertIn("PRINTER 25", t)
        self.assertIn("25 unaccounted", t)
        self.assertNotIn("unplaced", t)
        self.assertNotIn("empty", t)

    def test_a_zero_map_over_a_shelf_is_not_called_empty(self):
        t = self._line(lanes={"EMPTY": 0, "PRINTER": 0}, unknown=0, shelf=126)
        self.assertIn("126 unaccounted", t)
        self.assertNotIn("empty", t)
        self.assertNotIn("unplaced", t)

    def test_a_river_that_adds_up_names_only_its_stations(self):
        t = self._line(lanes={"EMPTY": 76, "PRINTER": 25}, unknown=0, shelf=101)
        self.assertIn("EMPTY 76", t)
        self.assertIn("PRINTER 25", t)
        self.assertNotIn("unplaced", t)
        self.assertNotIn("unaccounted", t)
        self.assertNotIn("counted twice", t)
        self.assertNotIn("empty", t)

    def test_a_count_past_the_shelf_is_not_hidden(self):
        t = self._line(lanes={"EMPTY": 76}, unknown=0, shelf=50)
        self.assertIn("EMPTY 76", t)
        self.assertIn("26 counted twice", t)
        self.assertNotIn("unaccounted", t)

    def test_an_older_console_that_sent_no_place_count_is_unchanged(self):
        t = self._line(lanes={"TRIAGE": 0, "PRINTER": 0})
        self.assertTrue(t.startswith("empty — 0 reels at every station"), t)
        self.assertNotIn("unplaced", t)
        self.assertNotIn("unaccounted", t)
        named = self._line(lanes={"INTAKE": 0, "TRIAGE": 7, "PRINTER": 1, "JOIN": 0, "TOMBSTONE": 2},
                           ageS=300.0)
        self.assertEqual(named, "TRIAGE 7 · PRINTER 1 · TOMBSTONE 2 · 6m ago")

    def test_a_change_in_the_place_count_is_news_and_an_age_is_not(self):
        """The line sits for fifteen minutes unless the worker compares these two counts.
        An age moves every beacon and is not news."""
        path = os.path.join(os.path.dirname(HERE), "functions", "api", "console.js")
        with io.open(path, encoding="utf-8") as f:
            src = f.read()
        start = "  const riverNews = (r) => {"
        end = "  const shelfNews = (r) => {"
        self.assertEqual(src.count(start), 1)
        i = src.index(start)
        fn = src[i:src.index(end, i)]
        placed = {"system": {"river": {"lanes": {"EMPTY": 76, "PRINTER": 25}, "unknown": 0,
                                        "shelf": 101, "ageS": 12}}}
        moved = {"system": {"river": {"lanes": {"EMPTY": 76, "PRINTER": 25}, "unknown": 25,
                                       "shelf": 126, "ageS": 90}}}
        aged = {"system": {"river": {"lanes": {"EMPTY": 76, "PRINTER": 25}, "unknown": 0,
                                      "shelf": 101, "ageS": 90}}}
        prog = fn + "\nvar rows = %s;\nprocess.stdout.write(JSON.stringify(rows.map(riverNews)));\n" % json.dumps(
            [placed, moved, aged])
        r = __import__("subprocess").run([F.NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        a, b, c = json.loads(r.stdout)
        self.assertNotEqual(a, b, "unplaced changed and the stored river line would sit for 15 min")
        self.assertEqual(a, c, "an age that moved was treated as news")
        self.assertIn("[0,101]", a)
        self.assertIn("[25,126]", b)
        self.assertNotIn("[25,126]", a)



#: v3861 - the sentence control_app builds when the window path gave up and the board has handed nothing over (a fresh
#: PC whose board holds no items): it filled the row of the work ALT in his fleet screenshot
_BOARD_WHY = ("the native window gave up; and the board has not handed its stores over either "
              "(no store present on this board)")
_OTHER_WHY = "the window path refused because the console was relaunching its view while a capture was being written out"


class TheRowSaysItsWhyInAFewWords(unittest.TestCase):
    """v3861 (his fleet screenshot, 2026-11-05): the fleet row carried the whole maskWhy - a paragraph - beside the PC's
    name. The row now says it in a few words; the hover keeps every word."""

    @classmethod
    def setUpClass(cls):
        def tweak(fx):
            fx["online"][0]["maskWhy"] = {"sets": _BOARD_WHY, "uniques": _BOARD_WHY}
            fx["online"][1]["maskWhy"] = {"sets": _OTHER_WHY}
        cls.rows = _rail(tweak)

    def _why(self, machine):
        row = [r for t, r in self.rows if 'data-fleet-machine="%s"' % machine in t]
        self.assertEqual(len(row), 1, "the rail drew no row for " + machine)
        i = row[0].find('<span class="fleet-meta fleet-why" title="')
        self.assertGreater(i, -1, "the row lost its why clause: " + machine)
        span = row[0][i:row[0].index("</span>", i)]
        title = span.split('title="', 1)[1].split('"', 1)[0]
        return span.split(">", 1)[1], title

    def test_a_board_with_no_items_says_so_in_a_few_words(self):
        shown, title = self._why("box-a")
        self.assertEqual(shown, "\u00b7 can\u2019t name pieces \u2014 this PC\u2019s board has no items yet")
        self.assertIn("no store present on this board", title, "the hover lost the whole reason")

    def test_any_other_long_reason_is_cut_at_a_word(self):
        shown, title = self._why("box-b")
        self.assertLessEqual(len(shown), 2 + 62, "a long reason runs the row again: %r" % shown)
        self.assertTrue(shown.endswith("\u2026"), shown)
        self.assertTrue(_OTHER_WHY.startswith(shown[2:-1]), "the cut is not a prefix at a word: %r" % shown)
        self.assertIn(_OTHER_WHY, title)

#: REG-1828 — the comment that opens the block after _fleetRefresh; F._cut counts it once
_REFRESH_END = "  /* ⚠⚠ v3086 — NOBODY EVER ASKED."
_CLICK = "click: open the row · click it again: how this PC films and drains, and their set pieces against yours"   # #225 (his ruling 2026-10-28): the row first, the compare on a second click
_SHOW = ".fleet-row.has-ftt:hover .ftt, .fleet-row.has-ftt:focus-visible .ftt {"
_STEP_ASIDE = (".fleet-row.has-ftt:has(:is([title], [data-tip-held]):hover) .ftt "
               "{ opacity: 0; visibility: hidden; }")


def _rail(tweak=None):
    """The SHIPPED _fleetRefresh in node over the fixture roster. -> [(row tag, row html)]

    One row carries counts so both of the card's paths draw (counted, and no report). `tweak(fx)` edits the roster
    first (v3861: a case's own maskWhy)."""
    fx = F._fixture()
    fx["online"][0]["tally"] = {"ok": True, "at": F._iso(F.NOW)}
    if tweak:
        tweak(fx)
    # REG-2072 - the rail's river chip now groups its tip through _fleetStuckWhy, defined further down the page; the cut
    # region does not hold it, so it is declared from the page's own bytes (a free name the harness was never told).
    prog = (F.HARNESS + F._cut("  function _fleetStuckWhy(list, label){\n", "join('  |  ');\n  }\n", inclusive_end=True) + "\n"
            + F._cut(F.FLEET_START, _REFRESH_END) + "\n"
            + "ELS['fleet-list'] = { innerHTML: '' };\n"
            + "var fetch = function(){ return Promise.resolve({ json: function(){ return Promise.resolve(%s); } }); };\n"
            % json.dumps(fx)
            + "window._fleetRefresh().then(function(){ process.stdout.write(ELS['fleet-list'].innerHTML); },"
            + " function(e){ process.stdout.write('ERR ' + e); });\n")
    r = F.subprocess.run([F.NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
    if r.returncode != 0 or r.stdout.startswith("ERR"):
        raise AssertionError("the shipped rail would not paint: %s" % (r.stderr or r.stdout)[-1200:])
    html = r.stdout
    chunks = html.split('<div class="fleet-row')[1:]
    out = []
    for c in chunks:
        c = '<div class="fleet-row' + c
        out.append((c[:c.index(">") + 1], c))
    return out


@unittest.skipIf(F.NODE is None, "node is not on this machine - this law RUNS the shipped rail")
class OneBoxAtATimeOnTheRow(unittest.TestCase):
    """REG-1828 — THE ROW CARRIED ITS WORDS TWICE. GrokBot, on his live screen at v3595: on the
    river-stuck word three boxes stacked, and the native strip "click: how this PC films and
    drains..." covered the last two lines. The row had a title AND its own card. The console's hint
    lane takes the hovered word's title away so no native box opens for it, and that left the row's
    title as the nearest one, so the native strip opened anyway. The click sentence now lives in the
    card, the row has no title, and the card steps aside while a word with its own words is under
    the pointer."""

    @classmethod
    def setUpClass(cls):
        cls.rows = _rail()

    def test_the_rail_painted_every_row(self):
        self.assertEqual(len(self.rows), 3, "the fixture roster has 3 PCs and the rail drew %d" % len(self.rows))

    def test_no_row_carries_a_title_of_its_own(self):
        # REG-1893 - a rail the parse could not find gives no rows, and "no row has a title" holds of none.
        self.assertTrue(self.rows, "the rail drew no fleet row, so this law would judge none")
        for tag, _ in self.rows:
            with self.subTest(tag[:60]):
                self.assertNotIn(" title=", tag,
                                 "the row carries a native title beside its card, so two boxes open: " + tag)
                self.assertIn("window._fleetRowClick(this)", tag, "the row stopped opening its box")

    def test_the_card_carries_the_click_sentence(self):
        # REG-1893 - a rail the parse could not find gives no rows, and "every card says it" holds of none.
        self.assertTrue(self.rows, "the rail drew no fleet row, so this law would judge none")
        for tag, row in self.rows:
            with self.subTest(tag[:60]):
                card = row[row.find('<div class="ftt">'):]
                self.assertTrue(card.startswith('<div class="ftt">'), "this row has no card: " + tag)
                self.assertEqual(card.count('<div class="ftt-click">' + _CLICK + '</div>'), 1,
                                 "the card does not say what a click opens, so the sentence left the row "
                                 "for nowhere")
        paths = [("ftt-age" in r) for _, r in self.rows]
        self.assertIn(True, paths, "no row drew the counted card, so its path was never graded")
        self.assertIn(False, paths, "no row drew the no-report card, so its path was never graded")

    def test_a_stuck_word_still_carries_its_own_reason(self):
        alt = [r for t, r in self.rows if 'data-fleet-machine="box-b"' in t]
        self.assertEqual(len(alt), 1)
        # v3861 (his fleet screenshot) - box-b's census is not current, so EMPTY 76 ("reel.route is LOCKED") is the shut
        # lock's consequence: it rides the muted "wait on the locks" chip with its reason, never red "river stuck".
        self.assertIn('class="fleet-riverwait" title="reels this PC cannot move until its locks open: EMPTY 76:', alt[0],
                      "the lock-held reel lost the reason it shows on hover")
        self.assertNotIn('river stuck on this PC - EMPTY 76:', alt[0], "a lock-held reel is called river stuck again")

    def test_the_card_steps_aside_for_a_word_with_its_own_words(self):
        """CSS cannot be driven without a browser. This pins the rule; the merger's render is the look."""
        import re as _re
        css = _re.sub(r"/\*.{0,4000}?\*/", "", F.UI, flags=_re.S)
        self.assertGreater(len(css), 0.5 * len(F.UI), "the comment strip ate the file")
        self.assertEqual(css.count(_STEP_ASIDE), 1,
                         "the card no longer steps aside while a titled word is hovered, so it and the hint "
                         "bubble open together")
        self.assertEqual(css.count(_SHOW), 1)
        self.assertGreater(css.find(_STEP_ASIDE), css.find(_SHOW),
                           "the step-aside comes before the rule that shows the card")


RED_PROOF = [
    {"why": "v3861 - the fleet row carries the whole board-stores paragraph again beside the PC's name",
     "file": "tv/control_ui.html",
     "find": "                        if (/no store present on this board|has not handed its stores/.test(w))\n",
     "replace": "                        if (false)\n",
     "matches": 1},
    {"why": "v3861 - any other long reason runs the fleet row uncut again",
     "file": "tv/control_ui.html",
     "find": "                        return w.length > 64 ? w.slice(0, 61).replace(/\\s+\\S*$/, '') + '\\u2026' : w;\n",
     "replace": "                        return w;\n",
     "matches": 1},
    {"why": "v3861 - a reel held by a shut lock is called red 'river stuck' again, a second alarm for one cause",
     "file": "tv/control_ui.html",
     "find": "    var _byLock = function (e) { return _locksShut && !!e && typeof e === 'object'\n",
     "replace": "    var _byLock = function (e) { return false && !!e && typeof e === 'object'\n",
     "matches": 1},
    {
        "why": "REG-2098 - the deleter's sentence repeats its station again, so ROUTED and CAPTURE owing one tombstone read apart",
        "file": "tv/control_app.py",
        "find": "    why = \"older than the newest %s - the drain owes them a tombstone\" % keep\n",
        "replace": "    why = \"older than the newest %s, still at %s, so the drain owes them a tombstone\" % (keep, station)\n",
        "matches": 1,
    },
    {
        "why": "REG-2098 - the older copy of a lane's reason is cut after its prefix again and ends at another word",
        "file": "tv/control_app.py",
        "find": "        return \"older than the newest %s - %s\" % (keep, _word_cut(_river_stuck_why(station), 200)) + (\n",
        "replace": "        return \"older than the newest %s - %s\" % (keep, _river_stuck_why(station)) + (\n",
        "matches": 1,
    },
    {
        "why": "REG-1987 - the stuck reason is a bare [:200] again and ends mid-word on every fleet tip",
        "file": "tv/control_app.py",
        "find": "        e[\"why\"] = (_word_cut(_river_stuck_why(e[\"station\"]), 200) if e.get(\"window\") is not False\n                    else _word_cut(_river_owed_why(e[\"station\"], _keep, _rs), 320))\n",
        "replace": "        e[\"why\"] = (_river_stuck_why(e[\"station\"])[:200] if e.get(\"window\") is not False\n                    else _river_owed_why(e[\"station\"], _keep, _rs)[:320])\n",
        "matches": 1,
    },
    {
        "why": "REG-1960 - an empty stuck list under shut locks says 'every station is draining' again",
        "file": "tv/control_ui.html",
        "find": "      if (_hs === 'missing' || _hs === 'stale' || _hs === 'unreadable') {\n",
        "replace": "      if (false) {\n",
        "matches": 1,
    },
    {
        "why": "REG-1863 - a fresh console's sweep owes reads and says nothing, so STATION falls back to the note again",
        "file": "tv/control_app.py",
        "find": "            return \"the reel sweep owes %d read(s) - it has not spoken since this console started\" % _owed_r\n",
        "replace": "            pass\n",
        "matches": 1,
    },
    {
        "why": "REG-1844 - STATION blames a predicate split again while the sweep owes reads behind a locked door",
        "file": "tv/control_app.py",
        "find": "        if isinstance(_owed_r, int) and not isinstance(_owed_r, bool) and _owed_r > 0 and _last_r:\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {"why": "REG-1738 - a river nobody ever stamped reads as draining again",
     "file": "control_app.py",
     "find": "            _never = rep.get(\"everStamped\") is False\n",
     "replace": "            _never = False\n",
     "matches": 1},
    {
        "why": "2026-09-29 - the fleet row stops saying a PC's river is stuck (REG-1461)",
        "file": "tv/control_ui.html",
        "find": "    if (Array.isArray(sk) && sk.length && _heldList.length < sk.length) {\n",
        "replace": "    if (false) {\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - CAPTURE (stuck by design) and fresh reels read as an alarm",
        "file": "tv/control_app.py",
        "find": "        if age < RIVER_STUCK_AFTER_S:\n            continue\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - the worker drops the stuck list, so no other PC ever sees it",
        "file": "functions/api/console.js",
        "find": "        if (Array.isArray(rv.stuck)) {\n",
        "replace": "        if (false) {\n",
        "matches": 1,
    },
    {
        "why": "REG-1614 - reels that left the shelf are counted again: his Mac's 17 deleted reels read as stuck",
        "file": "tv/control_app.py",
        "find": "        if reel in _pinned or reel in _done or not _on(reel):\n            continue\n",
        "replace": "        if reel in _pinned or reel in _done:\n            continue\n",
        "matches": 1,
    },
    {
        "why": "REG-1614 - the suite's fixture reels are counted again: reels that never move by design read as stuck",
        "file": "tv/control_app.py",
        "find": "        if reel in _pinned or reel in _done or not _on(reel):\n            continue\n",
        "replace": "        if reel in _done or not _on(reel):\n            continue\n",
        "matches": 1,
    },
    {
        "why": "REG-1614 - a shelf that is not there reads as a river draining (an empty list, not UNKNOWN)",
        "file": "tv/control_app.py",
        "find": "        if not os.path.isdir(HIST_DIR):\n            return None\n",
        "replace": "        if not os.path.isdir(HIST_DIR):\n            return []\n",
        "matches": 1,
    },
    {
        "why": "REG-1812 - a reel older than the newest window is dropped again, so the ALT's 84 at PRINTER read as none",
        "file": "tv/control_app.py",
        "find": "        inside = reel not in _left\n",
        "replace": "        if reel in _left:\n            continue\n        inside = True\n",
        "matches": 1,
    },
    {
        "why": "REG-1812 - past the window only a lane's station is counted, so ROUTED and CAPTURE debts read as a clear river",
        "file": "tv/control_app.py",
        "find": "        if inside and st not in _RIVER_OWNER:\n",
        "replace": "        if st not in _RIVER_OWNER:\n",
        "matches": 1,
    },
    {
        "why": "REG-1812 - the drain's patience starts at the station, so every new reel paints the river stuck",
        "file": "tv/control_app.py",
        "find": "        if not inside:\n            since = max(since, int(_left[reel]))\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1812 - a reel past the window loses the drain's word on why it was not paid",
        "file": "tv/control_app.py",
        "find": "    return why + (\" - the drain: \" + say if say else \"\")\n",
        "replace": "    return why\n",
        "matches": 1,
    },
    {
        "why": "a console that has not computed its river walks the stamp log and paints stuck",
        "file": "tv/control_app.py",
        "find": "    if out[\"lanes\"] is None:\n        out[\"stuck\"] = None\n",
        "replace": "    if False:\n        out[\"stuck\"] = None\n",
        "matches": 1,
    },
    {
        "why": "JOIN borrows the route lane sentence again, including a CAPTURE decline",
        "file": "tv/control_app.py",
        "find": "    if station in (\"JOIN\", \"STATION\"):\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-1614 - the ALT's locked route tells him to run a prove beside his game again",
        "file": "tv/control_app.py",
        "find": "            if w.startswith(\"reel.route is LOCKED\") and _sp.get(\"census\") not in (None, \"current\"):\n",
        "replace": "            if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-1770 - a missing proof draws the same empty chip as a river that is draining",
        "file": "tv/control_ui.html",
        "find": "    if (census === 'missing' || census === 'stale' || census === 'unreadable') {\n",
        "replace": "    if (false) {\n",
        "matches": 1,
    },
    {
        "why": "REG-1770 - a null stuck list draws the same empty chip as a river that is draining",
        "file": "tv/control_ui.html",
        "find": "    if (sk === null || census === null) {\n",
        "replace": "    if (false) {\n",
        "matches": 1,
    },
    {
        "why": "REG-1770 - the hover drops the stuck and proved sentences, so they live only behind a click",
        "file": "tv/control_ui.html",
        "find": "        if (p && (p.k === 'stuck' || p.k === 'proved') && p.t) sig.push(p.k + ': ' + p.t);\n",
        "replace": "        if (false) sig.push('');\n",
        "matches": 1,
    },
    {
        "why": "REG-1770 - the verdict hover stops asking for those sentences",
        "file": "tv/control_ui.html",
        "find": "              var plain = _fleetHoverPlain(m, meta);\n",
        "replace": "              var plain = String(meta || '').replace(/<[^>]*>/g, '').replace(/\\s+/g, ' ').trim();\n",
        "matches": 1,
    },
    {
        "why": "REG-1772/v3850 - a stale stamp draws as here again, green dot and ON AIR",
        "file": "tv/control_ui.html",
        "find": "    if (p.state === 'online') return { state: 'here',",
        "replace": "    if (true) return { state: 'here',",
        "matches": 1,
    },
    {
        "why": "REG-1772 - the row stops asking the pulse and paints every stored key as here",
        "file": "tv/control_ui.html",
        "find": "        var heard = !!(pres && pres.state === 'here');\n",
        "replace": "        var heard = !!online;\n",
        "matches": 1,
    },
    {
        "why": "REG-1773 - a restart nobody could ask about reads as clear to go again",
        "file": "tv/control_ui.html",
        "find": "    if (relaunch.may === true) {\n",
        "replace": "    if (true) {\n",
        "matches": 1,
    },
    {
        "why": "REG-1774 - an unreadable pull draws nothing again, so a behind count reads as a pull that will catch up",
        "file": "tv/control_ui.html",
        "find": "    if (pull.can === true || pull.can === false) return '';\n",
        "replace": "    if (true) return '';\n",
        "matches": 1,
    },
    {
        "why": "REG-1775 - unknown and the shelf are dropped before the beacon, so the placed stations read as the whole river",
        "file": "tv/control_app.py",
        "find": "            if _unk is not None:\n                good[\"unknown\"] = _unk\n            if _shelf_n is not None:\n                good[\"shelf\"] = _shelf_n\n",
        "replace": "            if False:\n                good[\"unknown\"] = _unk\n            if False:\n                good[\"shelf\"] = _shelf_n\n",
        "matches": 1,
    },
    {
        "why": "REG-1775 - the beacon stores the counts and then leaves them off the wire",
        "file": "tv/control_app.py",
        "find": "        if isinstance(g.get(\"unknown\"), int) and not isinstance(g.get(\"unknown\"), bool):\n            out[\"unknown\"] = int(g[\"unknown\"])\n        if isinstance(g.get(\"shelf\"), int) and not isinstance(g.get(\"shelf\"), bool):\n            out[\"shelf\"] = int(g[\"shelf\"])\n",
        "replace": "        if False:\n            out[\"unknown\"] = int(g[\"unknown\"])\n        if False:\n            out[\"shelf\"] = int(g[\"shelf\"])\n",
        "matches": 1,
    },
    {
        "why": "REG-1775 - the worker drops unknown and the shelf, so no other PC ever sees them",
        "file": "functions/api/console.js",
        "find": "        if (unk !== null) out.river.unknown = unk;\n        if (shelfN !== null) out.river.shelf = shelfN;\n",
        "replace": "        if (false) out.river.unknown = unk;\n        if (false) out.river.shelf = shelfN;\n",
        "matches": 1,
    },
    {
        "why": "REG-1775 - a change in unplaced is not news, so the river line sits for 15 min",
        "file": "functions/api/console.js",
        "find": "    return JSON.stringify([stuckWord === undefined ? 'absent' : stuckWord, heartWord, laneWord,\n                           triageWord, placeWord]);\n",
        "replace": "    return JSON.stringify([stuckWord === undefined ? 'absent' : stuckWord, heartWord, laneWord, triageWord]);\n",
        "matches": 1,
    },
    {
        "why": "REG-1775 - the card draws the placed stations as the whole river again",
        "file": "tv/control_ui.html",
        "find": "      if (hasUnk && rv.unknown > 0) bits.push(rv.unknown + nbsp + 'unplaced');\n      if (gap > 0) bits.push(gap + nbsp + 'unaccounted');\n      else if (gap < 0) bits.push((-gap) + nbsp + 'counted twice');\n",
        "replace": "      if (false) bits.push('');\n",
        "matches": 1,
    },
    {
        "why": "REG-1828 - the row carries a native title beside its own card, so two boxes open on it",
        "file": "tv/control_ui.html",
        "find": "          + ' data-fleet-machine=\"' + escC(m.machine || '') + '\"'\n"
                "          + ' onclick=",
        "replace": "          + ' data-fleet-machine=\"' + escC(m.machine || '') + '\"'\n"
                   "          + ' title=\"click: how this PC films and drains, and their set pieces against yours\"'\n"
                   "          + ' onclick=",
        "matches": 1,
    },
    {
        "why": "REG-1828 - the counted card drops the click sentence, so what a click opens is said nowhere",
        "file": "tv/control_ui.html",
        "find": "toISOString() : m.t)\n          + '</div>' + _fttClick + '</div>';",
        "replace": "toISOString() : m.t)\n          + '</div></div>';",
        "matches": 1,
    },
    {
        "why": "REG-1828 - the no-report card drops the click sentence",
        "file": "tv/control_ui.html",
        "find": "            + '</div>' + _fttClick + '</div>';",
        "replace": "            + '</div></div>';",
        "matches": 1,
    },
    {
        "why": "REG-1828 - the card stays up over the hint of a word with its own words",
        "file": "tv/control_ui.html",
        "find": "  .fleet-row.has-ftt:has(:is([title], [data-tip-held]):hover) .ftt { opacity: 0; visibility: hidden; }\n",
        "replace": "",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
