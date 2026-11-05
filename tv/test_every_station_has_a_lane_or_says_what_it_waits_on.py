# -*- coding: utf-8 -*-
"""REG-3201 - EVERY REEL AT PRINTER OR STATION HAS A LANE THAT DELIVERS IT, OR SAYS WHAT IT WAITS ON.

MEASURED on his Mac 2026-11-05 (/api/status + /api/river + /api/fleet, GET only):
  eagle "the river"        "3 of 42 reel(s) sit at a station that owes work no automatic lane delivers (PRINTER 2,
                            STATION 1). They are not stuck on evidence - nothing is scheduled to move them."
  fleet river stuck        PRINTER 2: "vault lane: owes 8, 6901 read(s) on record ... 1 quarantined after a hang"
  retention drain          "waiting at STATION 1 behind STATION: A LANE EXISTS AND THIS QUEUE IS NOT ITS INPUT"
  /api/river population    owedBy vault 8 = 8 panels-never-banked: CAPTURE 5, ROUTED 2, STATION 1 - so the two PRINTER
                           reels (reel_s_1793614663296_52736, reel_s_1793705809306_17617) are in NO lane's queue, and
                           the STATION reel (reel_s_1792343240980_21967) is the vault lane's own: the one unsealed owed
                           reel, the one the watchdog quarantined after the 854 s hang.
So the doctor called a reel its lane was holding "no automatic lane", the fleet quoted the vault lane's whole queue
about two reels that are not in it, and the drain blamed a chronicle predicate for a vault reel. Who delivers a reel
at PRINTER/STATION is a fact about the REEL.

THE LAW (control_app._station_delivery, the lanes' own rules, asked per reel; spends nothing):
  - a reel the vault lane owes and can start is delivered by the vault lane;
  - a reel the vault lane holds after a hang waits on that hold, named with its next try, and it clears by itself;
  - a PRINTER reel the triage proved panel-free waits on "a seal no lane writes" (REG-1749) - named, not self-clearing;
  - a STATION reel the reel sweep owes is delivered by the reel sweep; a reel in no queue says so; UNKNOWN stays None;
  - the doctor's river row counts only reels no lane will move by itself, and names every wait;
  - the fleet's LIVE stuck row words PRINTER/STATION from those reels; a fixture shelf keeps the lane's word;
  - the drain's upstream reason is asked per reel too (_river_drain_why), from the reels whose LAST stamp is that
    station and that are still on the shelf (_reels_at_station - its one source of per-reel data, never mocked here);
  - a lane check that could not be asked is UNKNOWN and says which check, never "no lane's queue holds it"; the
    doctor keeps the station reading for it and says it is UNKNOWN;
  - the doctor reaches the SERVING console's answer (_river_delivery), and the live wire (no fixture shelf) words
    PRINTER/STATION per reel.
[[the-unjoined-end]] [[unknown-stays-unknown]] [[label-outlived-referent]]
"""
import copy
import io
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()
import control_app as CA  # noqa: E402
import console_doctor as D  # noqa: E402
import shelf_driver as SD  # noqa: E402

HUNG = "reel_s_1792343240980_21967"
P1 = "reel_s_1793614663296_52736"
P2 = "reel_s_1793705809306_17617"
FREE = "reel_s_1793000000000_11111"
CHRON = "reel_s_1793100000000_22222"


def _code_without_comments(name):
    """The module's source with every comment token dropped, so a guard can never be satisfied by prose."""
    import tokenize
    with io.open(os.path.join(HERE, name), encoding="utf-8") as fh:
        toks = [t for t in tokenize.generate_tokens(fh.readline) if t.type != tokenize.COMMENT]
    return tokenize.untokenize(toks)


class _World(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="station-lane-")
        self._hist = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = self.tmp
        self._path = CA._VAULT_AUTOREAD_PATH
        self._seals = CA._VAULT_SWEPT_PATH
        self._snap = copy.deepcopy(CA._VAULT_AUTOREAD)
        self._store = dict(CA._VAULT_AUTOREAD_STORE)
        self._q = dict(CA._VAULT_SWEEP_QUARANTINE)
        CA._VAULT_AUTOREAD_PATH = os.path.join(self.tmp, ".vault_autoread.json")
        CA._VAULT_SWEPT_PATH = os.path.join(self.tmp, "vault_swept.json")
        CA._VAULT_AUTOREAD.clear()
        CA._VAULT_AUTOREAD.update({"tries": {}, "skipped": {}, "reads": 0, "lastTs": 0, "retired": {},
                                   "lastWhy": {}, "reextract": {}, "joinQueued": {}, "joinTried": {},
                                   "cooldown": {}, "hung": {}})
        CA._VAULT_AUTOREAD_STORE.clear()
        CA._VAULT_AUTOREAD_STORE.update({"tried": False, "readable": None})
        CA._VAULT_SWEEP_QUARANTINE.clear()
        with io.open(CA._VAULT_SWEPT_PATH, "w", encoding="utf-8") as fh:
            fh.write("{}")
        self.dirs = {}
        for rid in (HUNG, P1, P2, FREE, CHRON):
            d = os.path.join(self.tmp, rid)
            os.makedirs(d)
            self.dirs[rid] = d
        self.owed = [self.dirs[HUNG], self.dirs[FREE]]
        self.empty = {P1, P2}
        self.chron = {CHRON}
        self.patches = [mock.patch.object(CA, "_vault_reader_ver", lambda: "vpLAW"),
                        mock.patch.object(CA, "_vault_owed_reels", lambda hist=None: list(self.owed)),
                        mock.patch.object(CA, "_reel_is_growing", lambda d, quiet_s=90: False),
                        mock.patch.object(CA, "_chron_reel_owes_a_read",
                                          lambda rid, mem=None, prompt_ver=None: rid in self.chron),
                        mock.patch.object(SD, "_proven_empty", lambda reel: os.path.basename(str(reel)) in self.empty)]
        for p in self.patches:
            p.start()
        CA._vault_hang_record(HUNG, "frame 412 never settled", run=1, reel_dir=self.dirs[HUNG])

    def tearDown(self):
        for p in self.patches:
            p.stop()
        CA._VAULT_AUTOREAD_PATH = self._path
        CA._VAULT_SWEPT_PATH = self._seals
        CA._VAULT_AUTOREAD.clear()
        CA._VAULT_AUTOREAD.update(self._snap)
        CA._VAULT_AUTOREAD_STORE.clear()
        CA._VAULT_AUTOREAD_STORE.update(self._store)
        CA._VAULT_SWEEP_QUARANTINE.clear()
        CA._VAULT_SWEEP_QUARANTINE.update(self._q)
        CA._RIVER_WHY_CTX.reels = None
        if self._hist is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = self._hist
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestEachReelSaysWhoDeliversIt(_World):

    def test_the_vault_lanes_held_reel_waits_on_its_hold_not_on_no_lane(self):
        dl = CA._station_delivery("STATION", [HUNG])
        self.assertEqual([w["key"] for w in dl["waits"]], ["quarantined"], dl)
        self.assertTrue(dl["waits"][0]["selfClearing"], dl)
        self.assertEqual(dl["noLane"], 0, "a reel its lane is holding was called undelivered")
        self.assertIn("the vault lane, which holds it after a hang", dl["why"])
        self.assertIn(HUNG, dl["why"])
        self.assertIn("next try is in", dl["why"])

    def test_a_triage_empty_printer_reel_waits_on_a_seal_no_lane_writes(self):
        dl = CA._station_delivery("PRINTER", [P1, P2])
        self.assertEqual([(w["key"], len(w["reels"])) for w in dl["waits"]], [("triage-empty", 2)], dl)
        self.assertFalse(dl["waits"][0]["selfClearing"], dl)
        self.assertEqual(dl["noLane"], 2)
        self.assertTrue(dl["why"].startswith("PRINTER 2: 2 wait on a seal no lane writes"), dl["why"])
        self.assertIn("REG-1749", dl["why"])

    def test_startable_and_swept_reels_are_delivered_and_the_rest_say_so(self):
        self.empty = set()
        dl = CA._station_delivery("STATION", [FREE, CHRON, P1])
        self.assertEqual(dl["lanes"], {"the vault lane": [FREE], "the reel sweep": [CHRON]}, dl)
        self.assertEqual([w["key"] for w in dl["waits"]], ["no-queue"], dl)
        self.assertIn("no lane's queue holds it", dl["why"])

    def test_unknown_owed_is_unknown(self):
        self.owed = None
        self.assertIsNone(CA._station_delivery("PRINTER", [P1]))


class TestTheDoctorCountsOnlyWhatNoLaneWillMove(_World):

    def _verdict(self, rows):
        import reel_router as RR
        real = RR.route
        RR.route = lambda *a, **k: {"ok": True, "reels": rows}
        try:
            return dict(D.CHECKS)["the river"]()
        finally:
            RR.route = real

    def test_a_held_reel_is_not_no_lane_and_every_wait_is_named(self):
        rows = [{"reel": HUNG, "station": "STATION", "owes": "a paid read"},
                {"reel": P1, "station": "PRINTER", "owes": "SEAL"},
                {"reel": P2, "station": "PRINTER", "owes": "SEAL"}]
        st, say = self._verdict(rows)
        self.assertEqual(st, D.MISSING, say)
        self.assertTrue(say.startswith("2 of 3 reel(s)"), "the reel its lane holds was counted: %s" % say)
        self.assertIn("(PRINTER 2)", say)
        self.assertIn("a seal no lane writes", say, "the PRINTER wait is not named")
        self.assertIn("the vault lane, which holds it after a hang", say, "the STATION wait is not named")

    def test_only_self_clearing_waits_is_ok_and_still_named(self):
        st, say = self._verdict([{"reel": HUNG, "station": "STATION", "owes": "a paid read"}])
        self.assertEqual(st, D.OK, say)
        self.assertIn("holds that clear by themselves", say)
        self.assertIn(HUNG, say)

    def test_who_delivers_unknown_keeps_the_station_reading(self):
        self.owed = None
        st, say = self._verdict([{"reel": P1, "station": "PRINTER", "owes": "SEAL"}])
        self.assertEqual(st, D.MISSING, say)
        self.assertTrue(say.startswith("1 of 1 reel(s)"), say)


class TestTheFleetRowWordsItsOwnReels(_World):

    def test_a_live_row_words_printer_from_its_reels(self):
        with mock.patch.object(CA, "_vault_autoread_state_cached",
                               lambda: {"owed": 8, "reads": 6901, "owedWhy": "the whole queue"}):
            out = CA._river_stuck_worded([{"station": "PRINTER", "n": 2, "oldestS": 9 * 3600,
                                           "_reels": [P1, P2]}], 16, live=True)
        self.assertIn("a seal no lane writes", out[0]["why"], out)
        self.assertNotIn("the whole queue", out[0]["why"], "the row quoted the lane's whole queue about two reels "
                                                           "that are not in it")

    def test_a_fixture_shelf_keeps_the_lanes_word(self):
        now = int(time.time() * 1000)
        rows = [{"at": now - 9 * 3600 * 1000, "seq": 1, "reel": P1, "station": "PRINTER", "by": "law",
                 "byKind": "observer"}]
        asked = []
        real = CA._station_delivery
        with mock.patch.object(CA, "_vault_autoread_state_cached",
                               lambda: {"owed": 8, "reads": 6901, "owedWhy": "the whole queue"}), \
                mock.patch.object(CA, "_station_delivery", lambda *a, **k: asked.append(a) or real(*a, **k)):
            out = CA._river_stuck_for_wire(now_ms=now, _rows=rows, _shelf={P1}, _fixtures=(), _remnants=())
        self.assertEqual(asked, [], "a fixture shelf asked his live lane stores who delivers its reels")
        self.assertIn("vault lane: owes 8", out[0]["why"], out)
        self.assertIsNone(getattr(CA._RIVER_WHY_CTX, "reels", "unset"), "the row's reels outlived its wording")

    def test_a_vault_reel_its_lane_can_start_at_station_is_not_blamed_on_the_sweep(self):
        """Right after a relaunch the held reel's record may not exist yet: the vault lane can start it. STATION's
        standing note ("A LANE EXISTS AND THIS QUEUE IS NOT ITS INPUT") is about the reel sweep and was false for it."""
        with mock.patch.object(CA, "_reels_at_station", lambda st: [FREE]):
            w = CA._river_drain_why("STATION")
        self.assertIn("1 is delivered by the vault lane", w)
        self.assertNotIn("NOT ITS INPUT", w)

    def test_the_drain_asks_per_reel(self):
        with mock.patch.object(CA, "_reels_at_station", lambda st: [HUNG]):
            w = CA._river_drain_why("STATION")
        self.assertIn("the vault lane, which holds it after a hang", w)
        self.assertNotIn("NOT ITS INPUT", w, "the drain blamed the chronicle predicate for a vault reel")
        self.assertEqual(_code_without_comments("control_app.py").count(
            "upstream=tuple(_RIVER_OWNER), why_of=_river_drain_why,"), 1,
            "the drain no longer asks its upstream reason per reel")


class TestTheRealJoins(_World):
    """r4 review (C) and the unknown case: the joins exercised without mocking the function under test."""

    def _stamps(self, rows):
        import json
        with io.open(os.path.join(self.tmp, "river_stamp.jsonl"), "w", encoding="utf-8") as fh:
            for i, (reel, st) in enumerate(rows):
                fh.write(json.dumps({"at": 1793000000000 + i, "seq": i + 1, "reel": reel, "station": st,
                                     "by": "law", "byKind": "observer"}) + "\n")

    def test_the_drain_reads_which_reels_stand_at_each_station(self):
        gone = "reel_s_1793200000000_33333"          # stamped at STATION, no longer on the shelf
        self._stamps([(FREE, "STATION"), (HUNG, "PRINTER"), (P1, "PRINTER"), (HUNG, "STATION"), (P2, "PRINTER"),
                      (gone, "STATION"), (FREE, "ROUTED")])
        with mock.patch.object(CA, "HIST_DIR", self.tmp):
            self.assertEqual(CA._reels_at_station("STATION"), [HUNG],
                             "the drain's per-reel data is not the reels whose LAST stamp is STATION on the shelf")
            self.assertEqual(CA._reels_at_station("PRINTER"), [P1, P2])
            w = CA._river_drain_why("STATION")
        self.assertIn("the vault lane, which holds it after a hang", w, w)
        self.assertIn(HUNG, w)
        self.assertNotIn("NOT ITS INPUT", w, "the measured drain sentence came back")

    def test_a_check_that_cannot_be_asked_is_unknown_not_no_lane(self):
        def _boom(rid, mem=None, prompt_ver=None):
            raise KeyError("the chronicle store would not read")
        with mock.patch.object(CA, "_chron_reel_owes_a_read", _boom):
            dl = CA._station_delivery("STATION", [CHRON])
            st, say = TestTheDoctorCountsOnlyWhatNoLaneWillMove._verdict(
                self, [{"reel": CHRON, "station": "STATION", "owes": "a paid read"}])
        self.assertEqual([w["key"] for w in dl["waits"]], ["unknown"], dl)
        self.assertEqual((dl["noLane"], dl["unknown"]), (0, 1), dl)
        self.assertIn("UNKNOWN - who moves it could not be established: the reel sweep's check could not be asked "
                      "(KeyError)", dl["why"])
        self.assertNotIn("no lane's queue holds it", dl["why"], "an unasked check read as a confident no lane")
        self.assertEqual(st, D.MISSING, say)              # the station's old reading is kept for an UNKNOWN reel...
        self.assertIn("1 of them is UNKNOWN", say, say)   # ...and the doctor says it is UNKNOWN, not "no lane"

    def test_the_live_wire_words_its_reels(self):
        now = int(time.time() * 1000)
        rows = [{"at": now - 9 * 3600 * 1000, "seq": 1, "reel": P1, "station": "PRINTER", "by": "law",
                 "byKind": "observer"},
                {"at": now - 8 * 3600 * 1000, "seq": 2, "reel": P2, "station": "PRINTER", "by": "law",
                 "byKind": "observer"}]
        with mock.patch.object(CA, "HIST_DIR", self.tmp), \
                mock.patch.object(CA, "_vault_autoread_state_cached",
                                  lambda: {"owed": 8, "reads": 6901, "owedWhy": "the whole queue"}):
            out = CA._river_stuck_for_wire(now_ms=now, _rows=rows, _fixtures=())
        self.assertEqual([(e["station"], e["n"]) for e in out], [("PRINTER", 2)], out)
        self.assertIn("a seal no lane writes", out[0]["why"], out)
        self.assertNotIn("the whole queue", out[0]["why"], "the live wire quoted the lane's whole queue")

    def test_the_doctor_asks_the_serving_console(self):
        dl = D._river_delivery("PRINTER", [P1])
        self.assertIsInstance(dl, dict, "the doctor's seam reaches no console")
        self.assertEqual(dl.get("noLane"), 1, dl)


RED_PROOF = [
    {"why": "REG-3201 - the vault picker's reason is not asked, so a held reel reads as delivered",
     "file": "tv/control_app.py",
     "find": "                why = _vault_pass_reason(rid, vault_owed[rid], seals)\n",
     "replace": "                why = None\n",
     "matches": 1},
    {"why": "REG-3201 - a triage-empty PRINTER reel loses what it waits on",
     "file": "tv/control_app.py",
     "find": "            waits.setdefault(\"triage-empty\" if empty else \"no-queue\", []).append(rid)\n",
     "replace": "            waits.setdefault(\"no-queue\", []).append(rid)\n",
     "matches": 1},
    {"why": "REG-3201 - a hang's hold is treated as a wait no lane clears, so the doctor counts the lane's own reel",
     "file": "tv/control_app.py",
     "find": "            rows.append({\"key\": k, \"on\": on, \"reels\": rs, \"selfClearing\": k in _DELIVERY_SELF_CLEARING})\n",
     "replace": "            rows.append({\"key\": k, \"on\": on, \"reels\": rs, \"selfClearing\": False})\n",
     "matches": 1},
    {"why": "REG-3201 - a STATION reel the reel sweep owes is not asked of the sweep",
     "file": "tv/control_app.py",
     "find": "                    _sweep_owes = _chron_reel_owes_a_read(rid)\n",
     "replace": "                    _sweep_owes = False\n",
     "matches": 1},
    {"why": "REG-3201 - the doctor counts every PRINTER/STATION reel again, held or not",
     "file": "tv/console_doctor.py",
     "find": "            if st in _PER_REEL_STATIONS and r.get(\"reel\"):\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-3201 - the doctor counts the waits but names none",
     "file": "tv/console_doctor.py",
     "find": "    said = (\" Per reel: %s.\" % \"; \".join(waits)) if waits else \"\"\n",
     "replace": "    said = \"\"\n",
     "matches": 1},
    {"why": "REG-3201 - PRINTER/STATION quote the lane's whole queue whatever reels stand there",
     "file": "tv/control_app.py",
     "find": "    if station in (\"PRINTER\", \"STATION\") and reels:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3201 - a vault reel at STATION its lane can start is blamed on the reel sweep's predicate",
     "file": "tv/control_app.py",
     "find": "        if _dl is not None and (_dl.get(\"waits\") or set(_dl.get(\"lanes\") or {}) - {_STATION_OWN_LANE.get(station)}):\n",
     "replace": "        if _dl is not None and _dl.get(\"waits\"):\n",
     "matches": 1},
    {"why": "REG-3201 - the live stuck row's reels never reach its wording",
     "file": "tv/control_app.py",
     "find": "        _RIVER_WHY_CTX.reels = (list(_rs) if live else None)\n",
     "replace": "        _RIVER_WHY_CTX.reels = None\n",
     "matches": 1},
    {"why": "REG-3201 - a fixture shelf asks his live lane stores (a law's verdict decided by the venue)",
     "file": "tv/control_app.py",
     "find": "        return _river_stuck_worded(out, _keep, live=(_shelf is None))\n",
     "replace": "        return _river_stuck_worded(out, _keep, live=True)\n",
     "matches": 1},
    {"why": "REG-3201 - the drain blames the chronicle predicate for whatever stands at STATION",
     "file": "tv/control_app.py",
     "find": "            _last, plan, upstream=tuple(_RIVER_OWNER), why_of=_river_drain_why,",
     "replace": "            _last, plan, upstream=tuple(_RIVER_OWNER), why_of=_river_stuck_why,",
     "matches": 1},
    {"why": "REG-3201 (r4 review C) - the drain's per-reel data is lost: STATION blames the reel sweep's predicate again",
     "file": "tv/control_app.py",
     "find": "        return sorted(k for k, v in last.items() if v == station and k in on)\n",
     "replace": "        return None\n",
     "matches": 1},
    {"why": "REG-3201 - the drain counts reels that left the shelf",
     "file": "tv/control_app.py",
     "find": "        return sorted(k for k, v in last.items() if v == station and k in on)\n",
     "replace": "        return sorted(k for k, v in last.items() if v == station)\n",
     "matches": 1},
    {"why": "REG-3201 - the drain reads a reel's FIRST stamp, not where it stands now",
     "file": "tv/control_app.py",
     "find": "            last[str(r.get(\"reel\"))] = str(r.get(\"station\"))\n",
     "replace": "            last.setdefault(str(r.get(\"reel\")), str(r.get(\"station\")))\n",
     "matches": 1},
    {"why": "REG-3201 (r4 review) - a reel-sweep check that could not be asked reads as a confident 'no lane'",
     "file": "tv/control_app.py",
     "find": "                    waits.setdefault(\"unknown\", []).append(rid)\n",
     "replace": "                    waits.setdefault(\"no-queue\", []).append(rid)\n",
     "matches": 1},
    {"why": "REG-3201 (r4 review) - the doctor counts an UNKNOWN reel as undelivered without saying it is unknown",
     "file": "tv/console_doctor.py",
     "find": "                if w.get(\"key\") == \"unknown\":\n",
     "replace": "                if False:\n",
     "matches": 1},
    {"why": "REG-3201 - the doctor's seam reaches no console, so every PRINTER/STATION reel is counted again",
     "file": "tv/console_doctor.py",
     "find": "        return _serving_console(_ca)._station_delivery(station, reels)\n",
     "replace": "        return None\n",
     "matches": 1},
    {"why": "REG-3201 - the LIVE wire words PRINTER/STATION with the lane's whole-queue sentence",
     "file": "tv/control_app.py",
     "find": "        return _river_stuck_worded(out, _keep, live=(_shelf is None))\n",
     "replace": "        return _river_stuck_worded(out, _keep, live=False)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
