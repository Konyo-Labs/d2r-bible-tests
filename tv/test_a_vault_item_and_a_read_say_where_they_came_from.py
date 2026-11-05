#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""THE HEART ROWS FOR THE OWNED DOOR: 'a vault item with no provenance' and 'a read left no picture'.

His words, 2026-09-28: "make sure its all connected correctly and wired to the heart of the console", and "where is
the ledger proof of these two items? i cant find it.. how can i see the evidence and picture pixels".

heart-first: a door that writes provenance is not finished until something shouts when a vault item has none, and
the recorder's floor rules are not finished until something shouts when a read that named an item left no picture —
naming who took it, or that it was never written. Both are UNKNOWN (never 0, never OK) when what they judge could
not be read. [[unknown-stays-unknown]]

WHAT THIS LAW HOLDS (pure verdicts driven with fixtures — game item names only, never his store; the board is read
through the doctor's ONE shared board read, stubbed here; the shelf is a temp directory):
  · owned_provenance_verdict — MISSING names every owned name with no row that says who filed it; a receipt and a
    filing witness both count; UNKNOWN when either store is unreadable; an empty vault is OK with its 0 said.
  · vault_provenance_verdict — a filing whose only row is an owned RECEIPT is still an unwitnessed filing.
  · read_pictures.verdict / _check_a_read_left_no_picture — a read with names whose frame is on disk is fine; one
    whose frame is gone names the recorder's reap record, or says "never written" from the refusal record, or says
    UNKNOWN; reads older than 24 h and reads with no names are not judged; an unreadable journal or shelf is UNKNOWN.
  · read_pictures.status_for — the console's /api/picture_status answer, per frame: present, or gone with the reason.
  · M5 (review of 77d8d8b5) — a reel-relative ref whose file is still loose at the top level is ON DISK: the locator
    probes the bare stem after the exact miss, top level then every reel, as frame_ref.Index.resolve does.
  · both rows are in CHECKS, WATCHES and corroborate's registry; the route is served.
RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import console_doctor as D  # noqa: E402
import corroborate as C  # noqa: E402
import read_pictures as RP  # noqa: E402

NOW = int(time.time() * 1000)
RECEIPT = {"kind": "owned", "source": "aic-judge", "by": "backfill", "frameId": "9_1790543904663"}
FILING = {"mule": "uni-armor", "source": "stash", "looks": [{"id": "s_a", "frame": "f_a.jpg", "conf": 0.9}]}


class AVaultItemWithNoProvenance(unittest.TestCase):

    def test_names_every_item_nobody_can_account_for(self):
        st, why, c = D.owned_provenance_verdict(["Grief", "Plague"], {})
        self.assertEqual(D.MISSING, st, why)
        self.assertIn("Grief", why)
        self.assertIn("Plague", why)
        self.assertEqual(2, c["missing"])

    def test_a_receipt_and_a_filing_both_account_for_an_item(self):
        st, why, c = D.owned_provenance_verdict(["Grief", "Nagelring"], {"Grief": RECEIPT, "Nagelring": FILING})
        self.assertEqual(D.OK, st, why)
        self.assertEqual((0, 1, 1), (c["missing"], c["receipts"], c["filings"]))

    def test_a_row_that_does_not_say_who_is_not_provenance(self):
        st, why, _c = D.owned_provenance_verdict(["Grief"], {"Grief": {"kind": "owned", "frameId": "x"}})
        self.assertEqual(D.MISSING, st, why)

    def test_unknown_is_never_clean(self):
        for owned, prov in ((None, {}), (["Grief"], None), ("Grief", {})):
            st, why, _c = D.owned_provenance_verdict(owned, prov)
            self.assertEqual(D.UNKNOWN, st, "%r/%r read %s: %s" % (owned, prov, st, why))

    def test_an_empty_vault_says_its_zero(self):
        st, why, c = D.owned_provenance_verdict([], {})
        self.assertEqual(D.OK, st)
        self.assertIn("0 items", why)

    def test_the_row_reads_the_board_through_the_shared_read(self):
        real = D._board_read
        try:
            D._board_read = lambda: None
            self.assertEqual(D.UNKNOWN, D._check_vault_items_carry_provenance()[0])
            D._board_read = lambda: {"ok": True, "fullStores": {"d2r_owned": json.dumps(["Grief", "Plague"]),
                                                               "d2r_vaultProv": json.dumps({"Grief": RECEIPT})}}
            st, why = D._check_vault_items_carry_provenance()
            self.assertEqual(D.MISSING, st, why)
            self.assertIn("Plague", why)
            self.assertNotIn("Grief,", why)
            D._board_read = lambda: {"ok": True, "fullStores": {"d2r_owned": "[not json", "d2r_vaultProv": "{}"}}
            self.assertEqual(D.UNKNOWN, D._check_vault_items_carry_provenance()[0])
        finally:
            D._board_read = real

    def test_a_receipt_is_not_a_filing_witness(self):
        st, why, c = D.vault_provenance_verdict({"Grief": "runewords"}, {"Grief": RECEIPT}, {}, [], {"runs": 1, "banked": 0},
                                                locked_fn=lambda n: (False, ""))
        self.assertEqual(1, c["unwitnessed"], "a filing standing on an owned receipt read as witnessed: %s" % why)


class AReadLeftNoPicture(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="read_pic_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.hist = os.path.join(self.root, "frames", "hist")
        os.makedirs(os.path.join(self.hist, "reel_s_1"))
        for rel in ("1_%d.jpg" % (NOW - 5000), "reel_s_1/f_%d.jpg" % (NOW - 7000)):
            with open(os.path.join(self.hist, rel), "wb") as fh:
                fh.write(b"\xff\xd8\xff")

    def _rows(self):
        return [
            {"lane": "deep", "frameId": "1_%d" % (NOW - 5000), "names": ["Grief"], "ts": NOW - 5000},
            {"lane": "deep", "frameId": "reel_s_1/f_%d" % (NOW - 7000), "names": ["Plague"], "ts": NOW - 7000},
            {"lane": "deep", "frameId": "17_%d" % (NOW - 9000), "names": ["String of Ears"], "ts": NOW - 9000,
             "sessionId": "s_2"},
            {"lane": "deep", "frameId": "", "names": ["Hellfire Torch"], "ts": NOW - 11000, "sessionId": "s_2"},
            {"lane": "deep", "frameId": "20_%d" % (NOW - 12000), "names": ["Cranium Basher"], "ts": NOW - 12000},
            {"lane": "deep", "frameId": "30_%d" % (NOW - 13000), "names": [], "ts": NOW - 13000},
            {"lane": "deep", "frameId": "31_1", "names": ["Eye of Etlich"], "ts": NOW - 3 * 86400 * 1000},
        ]

    def _records(self):
        with io.open(os.path.join(self.root, RP.REAPS), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": NOW - 1000, "reel": "loose", "by": "recorder-loose-floor", "removed": True,
                                 "names": ["17_%d.jpg" % (NOW - 9000)]}) + "\n")
        with io.open(os.path.join(self.root, RP.REFUSALS), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": NOW - 11500, "frameId": "4_%d" % (NOW - 11500), "why": "hard-floor",
                                 "freeGb": 0.6, "session": "s_2"}) + "\n")

    def test_each_missing_picture_names_who_took_it(self):
        self._records()
        st, why = D._check_a_read_left_no_picture(rows=self._rows(), hist=self.hist, now_ms=NOW)
        self.assertEqual(D.MISSING, st, why)
        self.assertIn("3 of 5", why, "the denominator is not the reads that named something inside 24 h: %s" % why)
        self.assertIn("disk-floor reaper", why)
        self.assertIn("never written", why)
        self.assertIn("UNKNOWN", why, "a picture nobody recorded taking was not said to be UNKNOWN: %s" % why)

    def test_all_present_is_ok_with_its_count(self):
        st, why = D._check_a_read_left_no_picture(rows=self._rows()[:2], hist=self.hist, now_ms=NOW)
        self.assertEqual(D.OK, st, why)
        self.assertIn("2 of 2", why)

    def test_no_named_read_is_ok_and_says_zero(self):
        st, why = D._check_a_read_left_no_picture(rows=[self._rows()[5]], hist=self.hist, now_ms=NOW)
        self.assertEqual(D.OK, st)
        self.assertIn("0 reads", why)

    def test_what_could_not_be_read_is_unknown(self):
        st, _w, _c = RP.verdict(None, RP.locator(self.hist), [], [], [])
        self.assertEqual(D.UNKNOWN, st)
        st, _w = D._check_a_read_left_no_picture(rows=self._rows(), hist=os.path.join(self.root, "no-such"), now_ms=NOW)
        self.assertEqual(D.UNKNOWN, st)
        code, words = RP.who_took("x_1", None, [], [])
        self.assertEqual("unknown", code)
        self.assertIn("could not be read", words)

    def test_the_console_answers_per_picture(self):
        self._records()
        got = RP.status_for(["1_%d" % (NOW - 5000), "17_%d" % (NOW - 9000), "99_1"], self.hist)
        p = got["pictures"]
        self.assertTrue(p["1_%d" % (NOW - 5000)]["present"])
        self.assertFalse(p["17_%d" % (NOW - 9000)]["present"])
        self.assertEqual("reaped", p["17_%d" % (NOW - 9000)]["code"])
        self.assertEqual("unknown", p["99_1"]["code"])

    def test_a_reel_relative_ref_still_loose_at_the_top_level_is_on_disk(self):
        """⚠ M5 (review of 77d8d8b5, reproduced) — the journal names a frame `reel_<sid>/f_<ms>` the moment it is read,
        and the file may still sit LOOSE at the top level until its reel is sealed. The locator returned False right
        after the exact miss for any ref with a '/', so the doctor reported 'a read left no picture' about a picture on
        disk. It now probes the bare stem, top level then every reel — frame_ref.Index.resolve's order."""
        loose = "f_%d" % (NOW - 20000)
        with open(os.path.join(self.hist, loose + ".jpg"), "wb") as fh:
            fh.write(b"\xff\xd8\xff")
        present = RP.locator(self.hist)
        self.assertTrue(present("reel_s_1/" + loose), "a reel-relative ref whose file is still loose read as MISSING")
        self.assertTrue(present("reel_s_9/f_%d" % (NOW - 7000)), "a stem on disk in another reel read as missing")
        self.assertFalse(present("reel_s_1/f_1"), "BASELINE: a stem on disk nowhere must still read missing")
        st, why = D._check_a_read_left_no_picture(
            rows=[{"lane": "deep", "frameId": "reel_s_1/" + loose, "names": ["Grief"], "ts": NOW - 20000}],
            hist=self.hist, now_ms=NOW)
        self.assertEqual(D.OK, st, why)

    def test_a_released_reel_is_named_with_its_date(self):
        tomb = {"reels": [{"reel": "reel_s_7", "session": "s_7", "deletedTs": NOW - 3600 * 1000, "why": "released",
                           "kept": [{"frame": "f_keep.jpg"}]}]}
        with io.open(os.path.join(self.root, "frames", "reel_tombstones.json"), "w", encoding="utf-8") as fh:
            json.dump(tomb, fh)
        code, words = RP.who_took("reel_s_7/f_gone", [], RP.load_tombstones(self.hist), [], session="s_7")
        self.assertEqual("released", code, words)
        self.assertIn("released with its reel on", words)


class TheRowsAreJoined(unittest.TestCase):

    def test_registered_declared_and_explained(self):
        for name in ("a vault item with no provenance", "a read left no picture"):
            self.assertIn(name, dict(D.CHECKS))
            self.assertIn(name, D.WATCHES)
            self.assertIn(name, C.NO_JOINT_YET)
            self.assertNotIn(name, C.COVERED_BY)

    def test_the_console_serves_the_picture_status(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        i = src.index('if path == "/api/picture_status":')
        blk = src[i:src.index("return\n", i)]
        self.assertIn("_rpic.status_for(_ids, _fap._hist_dir(None))", blk)
        with io.open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8") as fh:
            bible = fh.read()
        # #41 rank 18 sibling (REG-1552) — the board asks the console that SERVED it (_consoleOrigin), never :17772 by name
        ask = "      var url = origin + '/api/picture_status?ids=' + encodeURIComponent(id);\n"
        self.assertEqual(bible.count(ask), 1, "nothing on the board asks the route of the console that served it (%d matches)" % bible.count(ask))
        self.assertNotIn("/api/picture_status') + '?ids='", bible, "the board asks a console by name again (REG-1552)")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "#41 rank 18 sibling (REG-1552) - the board's picture-status ask names a console again instead of the one that served it",
        "file": "bible.html",
        "find": "      var url = origin + '/api/picture_status?ids=' + encodeURIComponent(id);\n",
        "replace": "      var url = 'http://127.0.0.1:17772/api/picture_status?ids=' + encodeURIComponent(id);\n",
        "matches": 1,
    },
    {
        "why": "the row stops naming vault items with no provenance",
        "file": "console_doctor.py",
        "find": "    missing = [n for n in names if not _row_says_who(prov.get(n))]\n",
        "replace": "    missing = []\n",
        "matches": 1,
    },
    {
        "why": "an unreadable board reads as clean instead of UNKNOWN",
        "file": "console_doctor.py",
        "find": "        return UNKNOWN, \"the board's owned list or its provenance store would not read — UNKNOWN, not clean\", {}\n",
        "replace": "        return OK, \"0 missing\", {}\n",
        "matches": 1,
    },
    {
        "why": "an owned receipt counts as a filing witness",
        "file": "console_doctor.py",
        "find": "    prov = {k: v for k, v in prov.items() if not (isinstance(v, dict) and v.get(\"kind\") == \"owned\")}\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "a read whose picture is gone is not reported",
        "file": "read_pictures.py",
        "find": "        if not p:\n            code, words = who_took(",
        "replace": "        if False:\n            code, words = who_took(",
        "matches": 1,
    },
    {
        "why": "the reap record's names are not read — the deleter goes unnamed",
        "file": "read_pictures.py",
        "find": "    if stem:\n        for r in idx[\"names\"].get(stem, ()):\n",
        "replace": "    if False:\n        for r in idx[\"names\"].get(stem, ()):\n",
        "matches": 1,
    },
    {
        "why": "a refused picture is not recognised as 'never written'",
        "file": "read_pictures.py",
        "find": "        if same:\n            return {\"code\": \"never-written\",",
        "replace": "        if False:\n            return {\"code\": \"never-written\",",
        "matches": 1,
    },
    {
        "why": "M5: a reel-relative ref whose file is still loose at the top level reads as missing again",
        "file": "read_pictures.py",
        "find": "            if \"/\" in rel and os.path.isfile(os.path.join(hist_dir, base)):\n                return True\n",
        "replace": "            if \"/\" in rel:\n                return False\n",
        "matches": 1,
    },
    {
        "why": "the row is dropped from the doctor's roster, so nothing ever runs it",
        "file": "console_doctor.py",
        "find": "    (\"a read left no picture\", _check_a_read_left_no_picture),\n",
        "replace": "",
        "matches": 1,
    },
]
