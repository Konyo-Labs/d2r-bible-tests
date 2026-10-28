#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""#54 (REG-1522..1524) — EQUIPPED ITEMS ARE PIXEL-EXACT, PER CHARACTER, AND CARRIED ACROSS THE HOURLY REELS.

Every joint below is DRIVEN over a throwaway journal and frames copied from the committed fixture packs
(fixtures/short-run is 1280x832 — inside the doll's calibrated aspect band; fixtures/pack-stash-001 is
1280x756 — outside it). His journal, his frames and his store are never opened: TV_HIST points at a
scratch world before anything imports, and the store path is patched to that world.

  1. a doll slot's box is slot_identity's MEASURED fractions scaled to THAT frame's pixels; the four
     unmeasured slots and an out-of-band frame are REFUSED with the reason, never interpolated
  2. the frame size comes from the JPEG on disk (stdlib SOF read), so no Pillow is needed on the ALT
  3. a character is read from a LOGIN row only — a `character` on any other scene is refused
  4. worn items are filed under the character who logged in, with slot, box, frame and sightings
  5. a reel that opens WITHOUT a login inherits the character across a rollover-sized gap (`carried`),
     the two reels share one game session, and the join is written down with its gap
  6. a longer gap never chains: the worn items land in `unattributed` with a denominator
  7. a login in the later reel is a boundary even inside the gap — a new character, a new session
  8. the reader's slot WORD and the frame's GEOMETRY corroborate; a disagreement is a CONFLICT that
     leaves the item unplaced with both answers; a word alone and a point alone each answer alone
  9. a worn item with no slot evidence is UNPLACED with the reason, never guessed
 10. ingest is idempotent, and sightings count FRAMES
 11. the lane's contract: owed = sealed reels not ingested; UNKNOWN when no journal is readable
 12. the rollover gap bound covers the watcher's own mechanism and cannot chain two evenings
 13. the reader's parse keeps `char-select`, keeps `character` on that scene only, validates
     `names_slot` against the doll's own vocabulary and `names_xy` as a point, and the row carries them
 14. after_session_ended reaches the nudge (compiler-level: co_names), and the nudge files the reel
     through the console's own journal ring and HIST_DIR
 15. the doctor row: OK, MISSING when an old seal is owed, UNKNOWN when nothing can be read; registered
 16. REG-1558 — UNKNOWN stays UNKNOWN: the parse's failure arms say None (never "" / {}), the journal row
     carries names_slot / names_xy AS PARSED (never `or {}`), a login row whose name could not be read
     says None, a row whose slot words were never parsed says so, and a row with no readable stamp is
     None — never epoch 0: it still seals its reel, it never chains on a guessed clock, and it never
     stamps a slot as seen in 1970
 17. REG-1559 — the doctor judges the OLDEST owed seal: two owed reels, 61 min and 1 min old, are
     MISSING (the first cut read the newest seal of all reels and said OK); owed reels with no readable
     seal time are UNKNOWN, not OK

RED_PROOF below: 21 tampers, each seen red by applying it, running this file and restoring byte-exact.
[[feedback-fixtures-never-touch-live-data]] [[heart-first]] [[unknown-stays-unknown]]
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

# ⚠ THE WORLD IS A SCRATCH DIR BEFORE ANY MODULE BINDS A PATH. tv_diablo and control_app bind their
# state files at import from TV_HIST; a redirect after import is the v1866/REG-937 no-op.
_WORLD = tempfile.mkdtemp(prefix="equipped-world-")
os.environ["TV_HIST"] = os.path.join(_WORLD, "hist")
os.makedirs(os.environ["TV_HIST"], exist_ok=True)
os.environ["TV_SESSIONS"] = os.path.join(_WORLD, "sessions.jsonl")

import equipped_ledger as E  # noqa: E402
import slot_identity as S  # noqa: E402

IN_BAND = os.path.join(REPO, "fixtures", "short-run", "reels", "reel_s_1786999742937_fxshortrun")     # 1280x832
OUT_OF_BAND = os.path.join(REPO, "fixtures", "pack-stash-001", "reels", "reel_s_1784984019250_fxstash001")  # 1280x756
# #173 - each reel's first frame by NAME, so heart2 keys its bytes: listing the folder for it made this law unkeyable
IN_BAND_JPG = os.path.join(REPO, "fixtures/short-run/reels/reel_s_1786999742937_fxshortrun/f_1786999746023.jpg")
OUT_OF_BAND_JPG = os.path.join(REPO, "fixtures/pack-stash-001/reels/reel_s_1784984019250_fxstash001/f_1784984130673.jpg")

RED_PROOF = [
    {"why": "the chain rule: a reel with no login continues the previous game session ONLY across a rollover-sized gap; "
            "chaining unconditionally files a different evening's gear under the last character seen",
     "file": "equipped_ledger.py", "find": "if 0 <= g <= gap:", "replace": "if True:", "matches": 1},
    {"why": "a login row NAMES the character; a login that names nobody leaves every worn item unattributed",
     "file": "equipped_ledger.py", "find": "name, _why = character_of_row(r)",
     "replace": "name, _why = None, 'tampered'", "matches": 1},
    {"why": "the corroborator pair: the reader's word and the point's slot must AGREE; accepting the word over a "
            "disagreeing point is one number wearing two names",
     "file": "equipped_ledger.py", "find": "if word == geo:", "replace": "if True:", "matches": 1},
    {"why": "a character is read from the LOGIN scene only; a `character` on an inventory row is text from elsewhere",
     "file": "equipped_ledger.py", "find": '!= CHAR_SELECT_SCENE:', "replace": "!= CHAR_SELECT_SCENE and False:",
     "matches": 1},
    {"why": "an unmeasured slot is REFUSED by name, never given a box",
     "file": "equipped_ledger.py", "find": "if slot in _SI.UNMEASURED_SLOTS:", "replace": "if slot in ():", "matches": 1},
    {"why": "no readable journal means owed is UNKNOWN (None), never 0",
     "file": "equipped_ledger.py",
     "find": 'out["say"] = "no journal could be read, so what is owed is UNKNOWN — not zero"',
     "replace": 'out["owed"] = 0', "matches": 1},
    {"why": "ingest is idempotent: a reel already in the ledger is not filed twice, so sightings count frames",
     "file": "equipped_ledger.py", "find": 'done = set(d["lane"].get("ingested") or [])', "replace": "done = set()", "matches": 1},
    {"why": "the parse keeps the char-select scene; clamped to gameplay, the login screen has no word and the name goes nowhere",
     "file": "tv_diablo.py", "find": '"transition", "chronicle", "char-select"):', "replace": '"transition", "chronicle"):',
     "matches": 1},
    {"why": "the parse keeps a character on the LOGIN scene only",
     "file": "tv_diablo.py", "find": 'if scene == "char-select" and isinstance(_ch, str) and _ch.strip():',
     "replace": 'if isinstance(_ch, str) and _ch.strip():', "matches": 1},
    {"why": "the seal reaches the ledger: after_session_ended must call the nudge, or the store is plumbing with no tap",
     "file": "control_app.py", "find": "        _eq = _equipped_ledger_nudge()", "replace": "        _eq = None", "matches": 1},
    {"why": "the doctor row is registered in CHECKS, or nothing ever asks whether the lane still runs",
     "file": "console_doctor.py",
     "find": '    ("equipped ledger files every seal", _check_the_equipped_ledger_files_every_sealed_reel),\n',
     "replace": "", "matches": 1},
    {"why": "the doctor says MISSING when an old seal is owed; without it a stopped lane reads OK forever",
     "file": "console_doctor.py",
     "find": "        if (now - float(oldest)) > _EQUIPPED_OWED_GRACE_MS:",
     "replace": "        if False:", "matches": 1},
    {"why": "the doll vocabulary is the six measured slots PLUS the four refused — a helm is a slot the reader may name",
     "file": "slot_identity.py", "find": "DOLL_SLOTS = tuple(sorted(EQUIP_SLOTS)) + UNMEASURED_SLOTS",
     "replace": "DOLL_SLOTS = tuple(sorted(EQUIP_SLOTS))", "matches": 1},
    # ── REG-1558 / REG-1559 — the skeptic's fixes: UNKNOWN stays UNKNOWN all the way to the doctor ──
    {"why": "REG-1558: a row with no readable stamp is UNKNOWN (None), never epoch 0 — a 0 sorts it before everything "
            "and stamps a slot record as seen in 1970",
     "file": "equipped_ledger.py", "find": "        if t > 0:\n            return t\n    return None",
     "replace": "        if t > 0:\n            return t\n    return 0", "matches": 1},
    {"why": "REG-1558: SEALED is a fact about the rows; an undated seal row must not read as 'still rolling'",
     "file": "equipped_ledger.py", "find": '        if not reel["sealed"]:', "replace": '        if reel["sealedTs"] is None:',
     "matches": 1},
    {"why": "REG-1558: a gap nobody can measure never chains — chaining on a guessed clock files gear under the previous character",
     "file": "equipped_ledger.py", "find": '                    if seal is None or reel["t0"] is None:',
     "replace": "                    if False:", "matches": 1},
    {"why": "REG-1558: a read whose slot words were never parsed says so; reading None as 'no slot word' is a measured empty "
            "nobody measured",
     "file": "equipped_ledger.py",
     "find": "    words_unknown, points_unknown = not isinstance(words_raw, dict), not isinstance(points_raw, dict)",
     "replace": "    words_unknown, points_unknown = False, False", "matches": 1},
    {"why": "REG-1558: the parse says UNKNOWN (None) when the slot vocabulary is unavailable — {} reads as 'the reader named no slots'",
     "file": "tv_diablo.py", "find": "                _doll = None\n            if _doll is None:",
     "replace": "                _doll = ()\n            if _doll is None:", "matches": 1},
    {"why": "REG-1558: the journal row carries names_slot AS PARSED; `or {}` turns UNKNOWN back into a measured empty one frame up",
     "file": "tv_diablo.py", "find": '        "names_slot": rd.get("names_slot"),',
     "replace": '        "names_slot": rd.get("names_slot") or {},', "matches": 1},
    {"why": "REG-1559: the doctor judges the OLDEST owed seal; judged by the newest, a lane failing at every seal reads OK forever",
     "file": "equipped_ledger.py", "find": '    out["oldestOwedSealTs"] = (min(t for _s, t in owed if t is not None)',
     "replace": '    out["oldestOwedSealTs"] = (max(t for _s, t in owed if t is not None)', "matches": 1},
    {"why": "REG-1559: owed reels with no readable seal time are UNKNOWN, not OK",
     "file": "console_doctor.py",
     "find": '            return UNKNOWN, ("%d sealed reel(s) are owed and none of them carries a readable seal time, so "',
     "replace": '            return OK, ("%d sealed reel(s) are owed and none of them carries a readable seal time, so "',
     "matches": 1},
]

SID_A, SID_B, SID_C = "s_1790000000000_fxa", "s_1790003700000_fxb", "s_1790009000000_fxc"
T0 = 1790000000000


def _row(sid, ts, scene="inventory", frame=None, door="shadow", **kw):
    r = {"ts": ts, "captureTs": ts, "sessionId": sid, "scene": scene, "names": [], "lane": "deep",
         "door": door, "n": 1}
    if frame:
        r["frameId"] = frame
    r.update(kw)
    return r


def _seal(sid, ts):
    return {"ts": ts, "sessionId": sid, "scene": "session_end", "names": [], "lane": "system", "n": 0,
            "mode": "session_end", "door": "shadow"}


def _worn(sid, ts, frame, item, slot=None, xy=None):
    # a real deep-read row ALWAYS carries names_slot / names_xy (emit_deep_read writes them as parsed):
    # {} is "the read named none". A row without the keys is a row from before #54 — see the
    # never-parsed case in TestTheWordAndTheGeometryCorroborate (REG-1558).
    r = _row(sid, ts, "inventory", frame, names=[item], names_loc={item: "equipped"}, names_slot={}, names_xy={})
    if slot:
        r["names_slot"] = {item: slot}
    if xy:
        r["names_xy"] = {item: list(xy)}
    return r


class _World(unittest.TestCase):
    """One scratch world per test: a hist dir, a journal, a store — and the frame files it needs."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="equipped-")
        self.hist = os.path.join(self.d, "hist")
        os.makedirs(self.hist)
        self.journal = os.path.join(self.d, "sessions.jsonl")
        self.store = os.path.join(self.d, "equipped_ledger.json")
        self._orig_store_path = E.store_path
        E.store_path = lambda store=None, _p=self.store: (store or _p)

    def tearDown(self):
        E.store_path = self._orig_store_path
        shutil.rmtree(self.d, ignore_errors=True)

    def frame(self, sid, frame_id, src=IN_BAND_JPG):
        reel = os.path.join(self.hist, "reel_" + sid)
        os.makedirs(reel, exist_ok=True)
        dst = os.path.join(reel, frame_id + ".jpg")
        shutil.copyfile(src, dst)
        return dst

    def write(self, rows):
        with io.open(self.journal, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        return self.journal

    def ingest(self, rows, now_ms=None, **kw):
        self.write(rows)
        r = E.ingest([self.journal], self.hist, now_ms=now_ms, **kw)
        d, why = E.load(self.store)
        self.assertIsNotNone(d, why)
        return r, d

    def doctor(self, journals, now_ms):
        """The doctor row driven over THIS world's journal ring and frames, the console's resolvers patched."""
        import console_doctor as CD
        import control_app as CA
        orig_ring, orig_hist = CA._journal_ring, CA.HIST_DIR
        CA._journal_ring = lambda _j=journals: list(_j)
        CA.HIST_DIR = self.hist
        try:
            return CD._check_the_equipped_ledger_files_every_sealed_reel(now_ms=now_ms)
        finally:
            CA._journal_ring, CA.HIST_DIR = orig_ring, orig_hist


class TestTheBoxIsTheMeasuredSlotInThatFramesPixels(unittest.TestCase):

    def test_a_measured_slot_scales_to_the_frame(self):
        box, why = E.slot_box("torso", 2940, 1912)
        self.assertIsNone(why)
        self.assertEqual(box, (2114.0, 548.0, 206.0, 294.0), "at the calibration frame the box IS the measurement")
        box2, why2 = E.slot_box("torso", 1280, 832)
        self.assertIsNone(why2)
        fx, fy, fw, fh = S.EQUIP_SLOTS["torso"]
        self.assertEqual(box2, (round(fx * 1280, 2), round(fy * 832, 2), round(fw * 1280, 2), round(fh * 832, 2)))
        self.assertNotEqual(box, box2, "two frame sizes, two boxes — a constant here would be a guess")

    def test_the_four_unmeasured_slots_are_refused_by_name(self):
        for slot in S.UNMEASURED_SLOTS:
            box, why = E.slot_box(slot, 2940, 1912)
            self.assertIsNone(box, slot)
            self.assertIn("not measured", why)
            self.assertIn(slot, why)

    def test_an_unknown_slot_and_an_out_of_band_frame_are_refused(self):
        self.assertIsNone(E.slot_box("hat", 2940, 1912)[0])
        self.assertIn("not a doll slot", E.slot_box("hat", 2940, 1912)[1])
        box, why = E.slot_box("torso", 1280, 756)              # pack-stash-001's aspect, 1.693
        self.assertIsNone(box)
        self.assertIn("aspect", why)

    def test_the_vocabulary_is_the_dolls_ten_slots_and_is_shared(self):
        self.assertEqual(len(E.DOLL_SLOTS), 10)
        for s in ("helm", "torso", "weapon", "off-hand", "gloves", "belt", "boots", "ring1", "ring2", "amulet"):
            self.assertIn(s, E.DOLL_SLOTS)
        self.assertIs(E.DOLL_SLOTS, S.DOLL_SLOTS, "one tuple, owned by the geometry")

    def test_the_frame_size_is_read_from_the_jpeg_on_disk(self):
        self.assertEqual(E.jpeg_size(IN_BAND_JPG), (1280, 832))
        self.assertEqual(E.jpeg_size(OUT_OF_BAND_JPG), (1280, 756))
        self.assertIsNone(E.jpeg_size(os.path.join(IN_BAND, "index.json")), "not a JPEG -> None, never a size")
        self.assertIsNone(E.jpeg_size(os.path.join(IN_BAND, "nope.jpg")))


class TestACharacterComesOnlyFromTheLoginRow(unittest.TestCase):

    def test_a_login_row_names_him(self):
        self.assertEqual(E.character_of_row({"scene": "char-select", "character": " Konyo "}), ("Konyo", None))

    def test_any_other_scene_is_refused_even_with_a_name(self):
        name, why = E.character_of_row({"scene": "inventory", "character": "Konyo"})
        self.assertIsNone(name)
        self.assertIn("not the login screen", why)

    def test_a_login_with_no_name_is_refused_with_a_reason(self):
        name, why = E.character_of_row({"scene": "char-select", "character": ""})
        self.assertIsNone(name)
        self.assertIn("no readable character", why)


class TestWornItemsAreFiledUnderWhoLoggedIn(_World):

    def test_the_record_carries_slot_box_frame_and_sightings(self):
        f1 = "f_%d" % (T0 + 60000)
        self.frame(SID_A, f1)
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, T0 + 60000, f1, "Chains of Honor", slot="torso"),
                _seal(SID_A, T0 + 120000)]
        r, d = self.ingest(rows, now_ms=T0 + 130000)
        self.assertTrue(r["ok"], r["why"])
        self.assertEqual(r["ingested"], [SID_A])
        rec = d["characters"]["Konyo"]
        torso = rec["slots"]["torso"]
        self.assertEqual(torso["item"], "Chains of Honor")
        self.assertEqual(torso["frame"], f1)
        self.assertEqual(torso["frameSize"], [1280, 832])
        self.assertEqual(torso["box"], list(E.slot_box("torso", 1280, 832)[0]))
        self.assertEqual(torso["sightings"], 1)
        self.assertEqual(torso["slotBy"], "reader")
        self.assertEqual(rec["reels"], [SID_A])
        self.assertEqual(d["unattributed"]["reads"], 0)
        self.assertEqual(d["lane"]["worked"], 1)
        self.assertEqual(d["lane"]["lastTs"], T0 + 130000)

    def test_an_unmeasured_slot_is_filed_with_no_box_and_the_reason(self):
        f1 = "f_%d" % (T0 + 60000)
        self.frame(SID_A, f1)
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, T0 + 60000, f1, "Harlequin Crest", slot="helm"), _seal(SID_A, T0 + 120000)]
        _r, d = self.ingest(rows)
        helm = d["characters"]["Konyo"]["slots"]["helm"]
        self.assertEqual(helm["item"], "Harlequin Crest")
        self.assertIsNone(helm["box"])
        self.assertIn("not measured", helm["boxWhy"])

    def test_a_frame_off_the_calibrated_aspect_keeps_the_slot_and_refuses_the_box(self):
        f1 = "f_%d" % (T0 + 60000)
        self.frame(SID_A, f1, src=OUT_OF_BAND_JPG)
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, T0 + 60000, f1, "Chains of Honor", slot="torso"), _seal(SID_A, T0 + 120000)]
        _r, d = self.ingest(rows)
        torso = d["characters"]["Konyo"]["slots"]["torso"]
        self.assertEqual(torso["frameSize"], [1280, 756])
        self.assertIsNone(torso["box"])
        self.assertIn("aspect", torso["boxWhy"])

    def test_a_frame_not_on_disk_is_unknown_never_the_calibration_size(self):
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, T0 + 60000, "f_missing", "Chains of Honor", slot="torso"), _seal(SID_A, T0 + 120000)]
        _r, d = self.ingest(rows)
        torso = d["characters"]["Konyo"]["slots"]["torso"]
        self.assertIsNone(torso["frameSize"])
        self.assertIsNone(torso["box"])
        self.assertIn("not on disk", torso["boxWhy"])

    def test_a_changed_item_in_the_same_slot_replaces_and_keeps_the_previous(self):
        f1, f2 = "f_%d" % (T0 + 60000), "f_%d" % (T0 + 90000)
        self.frame(SID_A, f1)
        self.frame(SID_A, f2)
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, T0 + 60000, f1, "Chains of Honor", slot="torso"),
                _worn(SID_A, T0 + 90000, f2, "Enigma", slot="torso"), _seal(SID_A, T0 + 120000)]
        _r, d = self.ingest(rows)
        torso = d["characters"]["Konyo"]["slots"]["torso"]
        self.assertEqual(torso["item"], "Enigma")
        self.assertEqual([p["item"] for p in torso["previous"]], ["Chains of Honor"])


class TestTheGameSessionIsCarriedAcrossTheHourlyReels(_World):

    def _two_reels(self, gap_ms, login_in_b=None):
        fa, fb = "f_%d" % (T0 + 60000), "f_%d" % (T0 + 3600000 + gap_ms + 5000)
        self.frame(SID_A, fa)
        self.frame(SID_B, fb)
        seal_a = T0 + 3600000
        b0 = seal_a + gap_ms
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, T0 + 60000, fa, "Chains of Honor", slot="torso"), _seal(SID_A, seal_a)]
        if login_in_b:
            rows.append(_row(SID_B, b0, "char-select", character=login_in_b))
            rows.append(_worn(SID_B, b0 + 5000, fb, "Mara's Kaleidoscope", slot="amulet"))
        else:
            rows.append(_worn(SID_B, b0, fb, "Mara's Kaleidoscope", slot="amulet"))
        rows.append(_seal(SID_B, b0 + 3600000))
        return rows

    def test_a_reel_without_a_login_inherits_the_character_across_a_rollover_gap(self):
        _r, d = self.ingest(self._two_reels(25000))         # the seal + the 2 s relook + a missed look
        rec = d["characters"]["Konyo"]
        self.assertEqual(rec["slots"]["amulet"]["item"], "Mara's Kaleidoscope")
        self.assertEqual(rec["slots"]["amulet"]["reel"], SID_B)
        self.assertEqual(rec["reels"], [SID_A, SID_B])
        self.assertIn(SID_B, rec["carried"])
        self.assertIn("carried from " + SID_A, rec["carried"][SID_B])
        sessions = [s for s in d["gameSessions"].values() if SID_A in s["reels"]]
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["reels"], [SID_A, SID_B], "one game session, two hourly reels")
        self.assertEqual(sessions[0]["joins"][0]["gapMs"], 25000)
        self.assertEqual(rec["gameSessions"], [sessions[0]["id"]])
        self.assertEqual(d["unattributed"]["reads"], 0)

    def test_a_gap_longer_than_a_rollover_never_chains(self):
        _r, d = self.ingest(self._two_reels(10 * 60000))      # ten minutes: he came back, nobody logged in
        rec = d["characters"]["Konyo"]
        self.assertNotIn("amulet", rec["slots"], "the later reel's gear is NOT his by adjacency")
        self.assertEqual(rec["reels"], [SID_A])
        self.assertEqual(d["unattributed"]["reads"], 1)
        self.assertEqual(d["unattributed"]["reels"], [SID_B])
        self.assertIn("longer than a rollover", d["unattributed"]["why"])
        ids = [s["id"] for s in d["gameSessions"].values()]
        self.assertEqual(len(ids), 2)
        self.assertIn("g_%s_nologin" % SID_B, ids)

    def test_a_login_in_the_later_reel_is_a_boundary_even_inside_the_gap(self):
        _r, d = self.ingest(self._two_reels(20000, login_in_b="Dean"))
        self.assertEqual(d["characters"]["Konyo"]["reels"], [SID_A])
        self.assertNotIn("amulet", d["characters"]["Konyo"]["slots"])
        self.assertEqual(d["characters"]["Dean"]["slots"]["amulet"]["item"], "Mara's Kaleidoscope")
        self.assertEqual(len(d["gameSessions"]), 2)
        self.assertNotEqual(d["characters"]["Konyo"]["gameSessions"], d["characters"]["Dean"]["gameSessions"])

    def test_three_hourly_reels_are_one_game_session(self):
        fa, fb, fc = "f_%d" % (T0 + 60000), "f_%d" % (T0 + 3630000), "f_%d" % (T0 + 7260000)
        for sid, f in ((SID_A, fa), (SID_B, fb), (SID_C, fc)):
            self.frame(sid, f)
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, T0 + 60000, fa, "Chains of Honor", slot="torso"), _seal(SID_A, T0 + 3600000),
                _worn(SID_B, T0 + 3630000, fb, "Mara's Kaleidoscope", slot="amulet"), _seal(SID_B, T0 + 7230000),
                _worn(SID_C, T0 + 7260000, fc, "Arachnid Mesh", slot="belt"), _seal(SID_C, T0 + 10800000)]
        _r, d = self.ingest(rows)
        rec = d["characters"]["Konyo"]
        self.assertEqual(sorted(rec["slots"]), ["amulet", "belt", "torso"])
        self.assertEqual(rec["reels"], [SID_A, SID_B, SID_C])
        s = [s for s in d["gameSessions"].values() if SID_A in s["reels"]][0]
        self.assertEqual(s["reels"], [SID_A, SID_B, SID_C])
        self.assertEqual([j["gapMs"] for j in s["joins"]], [30000, 30000])


class TestTheWordAndTheGeometryCorroborate(_World):

    def _center(self, slot):
        x, y, w, h = E.slot_box(slot, 1280, 832)[0]
        return (x + w / 2.0, y + h / 2.0)

    def test_agreement_is_corroborated(self):
        f1 = "f_%d" % (T0 + 60000)
        self.frame(SID_A, f1)
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, T0 + 60000, f1, "Chains of Honor", slot="torso", xy=self._center("torso")),
                _seal(SID_A, T0 + 120000)]
        _r, d = self.ingest(rows)
        torso = d["characters"]["Konyo"]["slots"]["torso"]
        self.assertEqual(torso["slotBy"], "reader+geometry")

    def test_a_disagreement_is_a_conflict_that_leaves_the_item_unplaced(self):
        f1 = "f_%d" % (T0 + 60000)
        self.frame(SID_A, f1)
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, T0 + 60000, f1, "Chains of Honor", slot="torso", xy=self._center("ring1")),
                _seal(SID_A, T0 + 120000)]
        _r, d = self.ingest(rows)
        rec = d["characters"]["Konyo"]
        self.assertNotIn("torso", rec.get("slots") or {}, "a conflicted slot is not filed")
        un = rec["unplaced"]["Chains of Honor"]
        self.assertIn("CONFLICT", un["why"])
        self.assertIn("torso", un["why"])
        self.assertIn("ring1", un["why"])

    def test_a_point_alone_answers_from_the_geometry(self):
        f1 = "f_%d" % (T0 + 60000)
        self.frame(SID_A, f1)
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, T0 + 60000, f1, "Stone of Jordan", xy=self._center("ring2")), _seal(SID_A, T0 + 120000)]
        _r, d = self.ingest(rows)
        ring2 = d["characters"]["Konyo"]["slots"]["ring2"]
        self.assertEqual(ring2["item"], "Stone of Jordan")
        self.assertEqual(ring2["slotBy"], "geometry")

    def test_a_point_in_no_measured_box_leaves_the_item_unplaced_with_the_geometrys_reason(self):
        f1 = "f_%d" % (T0 + 60000)
        self.frame(SID_A, f1)
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, T0 + 60000, f1, "Harlequin Crest", xy=(5.0, 5.0)), _seal(SID_A, T0 + 120000)]
        _r, d = self.ingest(rows)
        un = d["characters"]["Konyo"]["unplaced"]["Harlequin Crest"]
        self.assertIn("no MEASURED equipment slot", un["why"])

    def test_no_slot_evidence_is_unplaced_never_guessed(self):
        f1 = "f_%d" % (T0 + 60000)
        self.frame(SID_A, f1)
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, T0 + 60000, f1, "War Traveler"), _seal(SID_A, T0 + 120000)]
        _r, d = self.ingest(rows)
        rec = d["characters"]["Konyo"]
        self.assertEqual(rec.get("slots") or {}, {})
        self.assertIn("no slot word and no point", rec["unplaced"]["War Traveler"]["why"])
        self.assertEqual(rec["unplaced"]["War Traveler"]["sightings"], 1)

    def test_a_read_whose_slot_words_were_never_parsed_says_so_instead_of_no_slot_word(self):
        """REG-1558 — None (the parse raised / the vocabulary was unavailable) and an absent key (a row
        from before #54) are UNKNOWN; {} is a measured 'none'. Reading them alike is a lie nobody measured."""
        f1 = "f_%d" % (T0 + 60000)
        self.frame(SID_A, f1)
        r_none = _worn(SID_A, T0 + 60000, f1, "War Traveler")
        r_none["names_slot"], r_none["names_xy"] = None, None
        r_absent = _worn(SID_A, T0 + 70000, f1, "Gore Rider")
        del r_absent["names_slot"], r_absent["names_xy"]
        rows = [_row(SID_A, T0, "char-select", character="Konyo"), r_none, r_absent, _seal(SID_A, T0 + 120000)]
        _r, d = self.ingest(rows)
        un = d["characters"]["Konyo"]["unplaced"]
        for item in ("War Traveler", "Gore Rider"):
            self.assertIn("UNKNOWN whether there was any", un[item]["why"], item)
            self.assertIn("slot words were never parsed", un[item]["why"], item)
            self.assertIn("points were never parsed", un[item]["why"], item)
            self.assertNotIn("carried no slot word", un[item]["why"], item)


class TestIngestIsIdempotentAndCountsFrames(_World):

    def test_a_second_ingest_files_nothing_and_a_second_frame_counts_once_more(self):
        f1, f2 = "f_%d" % (T0 + 60000), "f_%d" % (T0 + 70000)
        self.frame(SID_A, f1)
        self.frame(SID_A, f2)
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, T0 + 60000, f1, "Chains of Honor", slot="torso"),
                _worn(SID_A, T0 + 70000, f2, "Chains of Honor", slot="torso"),
                _worn(SID_A, T0 + 70000, f2, "Chains of Honor", slot="torso"),   # the same frame read twice
                _seal(SID_A, T0 + 120000)]
        r1, d1 = self.ingest(rows)
        self.assertEqual(d1["characters"]["Konyo"]["slots"]["torso"]["sightings"], 2, "frames, not reads")
        r2 = E.ingest([self.journal], self.hist)
        self.assertTrue(r2["ok"])
        self.assertEqual(r2["ingested"], [])
        self.assertIn("nothing new", r2["why"])
        d2, _ = E.load(self.store)
        self.assertEqual(d2["characters"]["Konyo"]["slots"]["torso"]["sightings"], 2)
        self.assertEqual(d2["lane"]["worked"], 1)

    def test_a_rolling_reel_is_left_for_its_seal(self):
        f1 = "f_%d" % (T0 + 60000)
        self.frame(SID_A, f1)
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, T0 + 60000, f1, "Chains of Honor", slot="torso")]      # no session_end
        r, d = self.ingest(rows)
        self.assertEqual(r["rolling"], [SID_A])
        self.assertEqual(r["ingested"], [])
        self.assertEqual(d["characters"], {})


class TestTheLanesContract(_World):

    def test_owed_is_the_sealed_reels_not_ingested_and_unknown_is_never_zero(self):
        f1 = "f_%d" % (T0 + 60000)
        self.frame(SID_A, f1)
        self.write([_row(SID_A, T0, "char-select", character="Konyo"),
                    _worn(SID_A, T0 + 60000, f1, "Chains of Honor", slot="torso"), _seal(SID_A, T0 + 120000)])
        before = E.contract([self.journal])
        self.assertEqual((before["on"], before["worked"], before["lastTs"], before["owed"]), (True, 0, None, 1))
        self.assertEqual(before["sealedNotIngested"], [SID_A])
        self.assertEqual(before["newestSealTs"], T0 + 120000)
        E.ingest([self.journal], self.hist, now_ms=T0 + 130000)
        after = E.contract([self.journal])
        self.assertEqual((after["worked"], after["lastTs"], after["owed"]), (1, T0 + 130000, 0))
        unknown = E.contract([os.path.join(self.d, "nope.jsonl")])
        self.assertIsNone(unknown["owed"], "no journal readable -> owed UNKNOWN, never 0")
        self.assertIn("UNKNOWN", unknown["say"])
        nothing = E.contract()
        self.assertIsNone(nothing["owed"])

    def test_an_unreadable_store_is_unknown_and_ingest_writes_nothing_over_it(self):
        with io.open(self.store, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        c = E.contract([self.journal])
        self.assertIsNone(c["owed"])
        self.assertIsNone(c["worked"])
        self.write([_seal(SID_A, T0)])
        r = E.ingest([self.journal], self.hist)
        self.assertIsNone(r["ok"])
        with io.open(self.store, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "{not json", "an unreadable store is never overwritten")

    def test_no_readable_journal_is_unknown_and_files_nothing(self):
        r = E.ingest([os.path.join(self.d, "absent.jsonl")], self.hist)
        self.assertIsNone(r["ok"])
        self.assertIn("UNKNOWN", r["why"])
        self.assertFalse(os.path.exists(self.store))


class TestTheRolloverGapBoundCoversTheWatcher(unittest.TestCase):

    def test_the_bound_sits_above_the_mechanism_and_below_two_evenings(self):
        import control_app as CA
        mechanism_s = float(CA._SHADOW_ROTATE_RELOOK_S) + float(CA._SHADOW_WATCH_EVERY_S) + 8.0   # + a ~8 s stop
        self.assertGreaterEqual(E.ROLLOVER_GAP_MS / 1000.0, mechanism_s,
                                "a bound below the watcher's own relook + period + stop misses real rollovers")
        self.assertLessEqual(E.ROLLOVER_GAP_MS, 5 * 60 * 1000,
                             "a bound above five minutes chains two separate evenings")
        self.assertGreater(float(CA._SHADOW_AWAY_GRACE_S), 0)


class TestTheReaderKeepsTheLoginAndTheSlot(unittest.TestCase):

    def test_char_select_survives_the_parse_with_its_name(self):
        import tv_diablo as TV
        r = TV._parse_read('{"scene":"char-select","character":"Konyo","names":[],"conf":0.9}')
        self.assertEqual(r["scene"], "char-select")
        self.assertEqual(r["character"], "Konyo")
        self.assertEqual([d for d in r["_parse_audit"]["normalized"] if d.get("field") == "scene"], [],
                         "the login scene must not be clamped to gameplay")

    def test_a_character_on_any_other_scene_is_dropped_with_its_reason(self):
        import tv_diablo as TV
        r = TV._parse_read('{"scene":"inventory","character":"Konyo","names":[]}')
        self.assertEqual(r["character"], "")
        drops = [d for d in r["_parse_audit"]["dropped"] if d.get("field") == "character"]
        self.assertEqual(len(drops), 1)
        self.assertEqual(drops[0]["why"], "not-a-login-scene")

    def test_the_slot_word_is_validated_against_the_dolls_vocabulary_and_the_point_as_a_point(self):
        import tv_diablo as TV
        raw = ('{"scene":"inventory","names":["Shako","Enigma"],"names_loc":{"Shako":"equipped","Enigma":"equipped"},'
               '"names_slot":{"Shako":"HELM","Enigma":"chestplate"},"names_xy":{"Shako":[12,34.5],"Enigma":"here"}}')
        r = TV._parse_read(raw)
        self.assertEqual(r["names_slot"], {"Shako": "helm"})
        self.assertEqual(r["names_xy"], {"Shako": [12.0, 34.5]})
        whys = sorted(d["why"] for d in r["_parse_audit"]["dropped"])
        self.assertEqual(whys, ["invalid-slot", "not-a-point"])
        kept = list(TV._parse_read('{"scene":"inventory","names":[],"names_slot":{%s}}'
                                   % ",".join('"i%d":"%s"' % (i, s) for i, s in enumerate(E.DOLL_SLOTS)))["names_slot"].values())
        # REG-1893 - a validator that dropped EVERY word would leave nothing for the loop below to check
        self.assertEqual(len(kept), len(E.DOLL_SLOTS), "valid doll words were dropped: kept %r" % kept)
        for s in kept:
            self.assertIn(s, E.DOLL_SLOTS)

    def test_the_journal_row_carries_the_fields(self):
        """The rec built in tv_diablo's read path names the three keys — asked of the SOURCE because the
        builder is a 300-line function inside the live read loop; the parse above is driven for real."""
        import tv_diablo as TV
        with io.open(TV.__file__.replace(".pyc", ".py"), encoding="utf-8") as fh:
            src = fh.read()
        code = "\n".join(l.split("#", 1)[0] for l in src.split("\n"))
        # REG-1558 — AS PARSED, never `or {}`: the driven twin is TestUnknownStaysUnknownInTheReader
        self.assertEqual(code.count('"names_slot": rd.get("names_slot"),'), 1)
        self.assertEqual(code.count('"names_xy": rd.get("names_xy"),'), 1)
        self.assertEqual(code.count('rec["character"] = rd.get("character")'), 1)


class TestTheSealReachesTheLedger(_World):

    def test_after_session_ended_references_the_nudge(self):
        import control_app as CA
        self.assertIn("_equipped_ledger_nudge", set(CA.after_session_ended.__code__.co_names),
                      "after_session_ended no longer calls the nudge — the store is plumbing with no tap")

    def test_the_nudge_files_the_sealed_reel_through_the_consoles_own_resolvers(self):
        import control_app as CA
        f1 = "f_%d" % (T0 + 60000)
        self.frame(SID_A, f1)
        self.write([_row(SID_A, T0, "char-select", character="Konyo"),
                    _worn(SID_A, T0 + 60000, f1, "Chains of Honor", slot="torso"), _seal(SID_A, T0 + 120000)])
        orig_ring, orig_hist = CA._journal_ring, CA.HIST_DIR
        CA._journal_ring = lambda _j=self.journal: [_j + ".5", _j]
        CA.HIST_DIR = self.hist
        try:
            r = CA._equipped_ledger_nudge()
        finally:
            CA._journal_ring, CA.HIST_DIR = orig_ring, orig_hist
        self.assertTrue(r.get("ok"), r)
        self.assertEqual(r["ingested"], [SID_A])
        d, _ = E.load(self.store)
        self.assertEqual(d["characters"]["Konyo"]["slots"]["torso"]["item"], "Chains of Honor")


class TestTheDoctorRow(_World):

    def test_missing_when_an_old_seal_is_owed_ok_once_filed_unknown_when_nothing_reads(self):
        import console_doctor as CD
        f1 = "f_%d" % (T0 + 60000)
        self.frame(SID_A, f1)
        self.write([_row(SID_A, T0, "char-select", character="Konyo"),
                    _worn(SID_A, T0 + 60000, f1, "Chains of Honor", slot="torso"), _seal(SID_A, T0 + 120000)])
        state, why = self.doctor([self.journal], now_ms=T0 + 120000 + 20 * 60000)
        self.assertEqual(state, CD.MISSING, why)
        self.assertIn("1 sealed reel(s)", why)
        self.assertIn("owed=1", why)
        state, why = self.doctor([self.journal], now_ms=T0 + 125000)   # sealed 5 s ago: inside the grace
        self.assertEqual(state, CD.OK, why)
        E.ingest([self.journal], self.hist)
        state, why = self.doctor([self.journal], now_ms=T0 + 120000 + 20 * 60000)
        self.assertEqual(state, CD.OK, why)
        self.assertIn("1 character(s)", why)
        self.assertIn("owed=0", why)
        state, why = self.doctor([os.path.join(self.d, "nope.jsonl")], now_ms=T0)
        self.assertEqual(state, CD.UNKNOWN, why)
        self.assertIn("owed=None", why)

    def test_the_row_is_registered(self):
        import console_doctor as CD
        names = [n for n, _fn in CD.CHECKS]
        self.assertIn("equipped ledger files every seal", names)


class TestTheDoctorJudgesTheOldestOwedSeal(_World):
    """REG-1559 — MEASURED on the first cut with two owed reels, 61 min and 1 min old: OK. It read the
    NEWEST seal of ALL reels, so a lane failing at every seal read OK for as long as reels kept sealing —
    each fresh seal hid the hour-old one beside it. The OLDEST owed seal is the age that says 'late'."""

    def _two_owed(self):
        self.write([_seal(SID_A, T0), _seal(SID_B, T0 + 3600000)])
        return [self.journal]

    def test_the_contract_names_the_oldest_owed_seal(self):
        j = self._two_owed()
        c = E.contract(j)
        self.assertEqual((c["owed"], c["newestSealTs"], c["oldestOwedSealTs"], c["owedUndated"]),
                         (2, T0 + 3600000, T0, 0))
        self.assertEqual(c["sealedNotIngested"], [SID_A, SID_B])
        E.ingest(j, self.hist)
        c2 = E.contract(j)
        self.assertEqual((c2["owed"], c2["oldestOwedSealTs"], c2["newestSealTs"]), (0, None, T0 + 3600000))

    def test_missing_when_the_oldest_owed_seal_is_old_even_though_the_newest_is_fresh(self):
        import console_doctor as CD
        state, why = self.doctor(self._two_owed(), now_ms=T0 + 3600000 + 60000)
        self.assertEqual(state, CD.MISSING, why)
        self.assertIn("2 sealed reel(s)", why)
        self.assertIn("oldest of them sealed 61 min ago", why)

    def test_unknown_when_no_owed_seal_carries_a_readable_time(self):
        import console_doctor as CD
        self.write([_seal(SID_A, None)])
        state, why = self.doctor([self.journal], now_ms=T0)
        self.assertEqual(state, CD.UNKNOWN, why)
        self.assertIn("none of them carries a readable seal time", why)
        self.assertIn("owed=1 (1 owed reel(s) carry no seal time)", why)


class TestAnUndatedRowIsUnknownNeverEpochZero(_World):
    """REG-1558 — _ts() returned 0 on a missing or unreadable stamp: the row sorted before everything,
    a seal row without a stamp read as 'still rolling' (never filed, never owed), and a slot record was
    stamped as seen in 1970. [[stale-reading]] §3"""

    def test_ts_is_none_for_a_missing_bad_or_zero_stamp_and_falls_back_to_capture_ts(self):
        self.assertIsNone(E._ts({}))
        self.assertIsNone(E._ts({"ts": "abc"}))
        self.assertIsNone(E._ts({"ts": 0}))
        self.assertIsNone(E._ts({"ts": None, "captureTs": ""}))
        self.assertIsNone(E._ts({"ts": True}))
        self.assertIsNone(E._ts("not a row"))
        self.assertEqual(E._ts({"ts": "abc", "captureTs": 5}), 5)
        self.assertEqual(E._ts({"ts": T0, "captureTs": 1}), T0)
        self.assertIsNone(E._newest(None, None))
        self.assertEqual(E._newest(None, 7, 3), 7)

    def test_an_undated_seal_row_still_seals_the_reel_and_an_undated_sighting_has_no_stamp(self):
        f1 = "f_%d" % (T0 + 60000)
        self.frame(SID_A, f1)
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, "abc", f1, "Chains of Honor", slot="torso"),      # its clock is unreadable
                _seal(SID_A, None)]                                              # its seal row carries no stamp
        reels = E.reels_from_rows([r for r in rows])
        self.assertEqual((reels[0]["sealed"], reels[0]["sealedTs"], reels[0]["t0"], reels[0]["t1"]),
                         (True, None, T0, T0), "sealed is a fact about the rows; t0/t1 are the KNOWN stamps")
        r, d = self.ingest(rows, now_ms=T0 + 130000)
        self.assertTrue(r["ok"], r["why"])
        self.assertEqual((r["ingested"], r["rolling"]), ([SID_A], []))
        torso = d["characters"]["Konyo"]["slots"]["torso"]
        self.assertEqual(torso["item"], "Chains of Honor")
        self.assertIsNone(torso["ts"], "an undated sighting is UNKNOWN, never 0 (1970)")
        self.assertIsNone(torso["firstTs"])
        self.assertIsNone(d["characters"]["Konyo"]["lastTs"])
        c = E.contract([self.journal])
        self.assertEqual((c["owed"], c["owedUndated"]), (0, 0))

    def test_a_gap_nobody_can_measure_never_chains(self):
        fa, fb = "f_%d" % (T0 + 60000), "f_%d" % (T0 + 3700000)
        self.frame(SID_A, fa)
        self.frame(SID_B, fb)
        rows = [_row(SID_A, T0, "char-select", character="Konyo"),
                _worn(SID_A, T0 + 60000, fa, "Chains of Honor", slot="torso"), _seal(SID_A, T0 + 120000),
                _worn(SID_B, "abc", fb, "Mara's Kaleidoscope", slot="amulet"),   # reel B: no readable clock at all
                _seal(SID_B, None)]
        r, d = self.ingest(rows)
        self.assertEqual(sorted(r["ingested"]), sorted([SID_A, SID_B]))
        rec = d["characters"]["Konyo"]
        self.assertNotIn("amulet", rec["slots"], "B's gap is UNKNOWN — its gear is not his by adjacency")
        self.assertEqual(rec["reels"], [SID_A])
        self.assertEqual(d["unattributed"]["reads"], 1)
        self.assertIn("cannot be measured", d["unattributed"]["why"])
        self.assertIn("undated", d["unattributed"]["why"])
        self.assertIn("g_%s_nologin" % SID_B, d["gameSessions"])


class TestUnknownStaysUnknownInTheReader(unittest.TestCase):
    """REG-1558 — the parse's failure arms and the journal row say None, never a measured empty."""

    def test_an_unavailable_slot_vocabulary_makes_names_slot_unknown_not_empty(self):
        import tv_diablo as TV
        raw = '{"scene":"inventory","names":["Shako"],"names_loc":{"Shako":"equipped"},"names_slot":{"Shako":"helm"}}'
        saved = sys.modules.get("slot_identity")
        sys.modules["slot_identity"] = None          # `import slot_identity` now raises ImportError
        try:
            r = TV._parse_read(raw)
        finally:
            if saved is not None:
                sys.modules["slot_identity"] = saved
            else:
                sys.modules.pop("slot_identity", None)
        self.assertIsNone(r["names_slot"], "no vocabulary -> UNKNOWN, not {} ('the reader named no slots')")
        drops = [d for d in r["_parse_audit"]["dropped"] if d.get("field") == "names_slot"]
        self.assertEqual([d["why"] for d in drops], ["slot-vocabulary-unavailable"])
        self.assertEqual(drops[0]["count"], 1)
        self.assertEqual(TV._parse_read(raw)["names_slot"], {"Shako": "helm"}, "with the vocabulary back it is measured")

    def test_the_journal_row_carries_unknown_slot_words_as_null_never_as_empty(self):
        """emit_deep_read driven the way test_agent drives it — STATE/JOURNAL swapped to a scratch dir."""
        import tv_diablo as TV
        old_state, old_j = TV.STATE, TV.JOURNAL
        d = tempfile.mkdtemp(prefix="equipped-emit-")
        TV.STATE, TV.JOURNAL = os.path.join(d, "state.json"), os.path.join(d, "j.jsonl")
        try:
            base = {"area": "Harrogath", "scene": "inventory", "names": [], "tz": [], "conf": 0.9, "ms": 1}
            rec_unknown = TV.emit_deep_read(dict(base, names_slot=None, names_xy=None), n=1, frame_id="")
            rec_absent = TV.emit_deep_read(dict(base), n=2, frame_id="")
            rec_empty = TV.emit_deep_read(dict(base, names_slot={}, names_xy={}), n=3, frame_id="")
            rec_login = TV.emit_deep_read(dict(base, scene="char-select", character=None), n=4, frame_id="")
            rec_named = TV.emit_deep_read(dict(base, scene="char-select", character="Konyo"), n=5, frame_id="")
        finally:
            TV.STATE, TV.JOURNAL = old_state, old_j
            shutil.rmtree(d, ignore_errors=True)
        self.assertIsNone(rec_unknown["names_slot"])
        self.assertIsNone(rec_unknown["names_xy"])
        self.assertIsNone(rec_absent["names_slot"], "a read that never went through the parse measured nothing")
        self.assertEqual((rec_empty["names_slot"], rec_empty["names_xy"]), ({}, {}))
        self.assertIn("character", rec_login)
        self.assertIsNone(rec_login["character"], "a login row whose name could not be read says UNKNOWN on the row")
        self.assertEqual(rec_named["character"], "Konyo")
        self.assertNotIn("character", rec_empty, "a play row carries no character key at all")


if __name__ == "__main__":
    unittest.main()
