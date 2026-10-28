"""#118 — a measured First Found date stays on the live sighting.

The parser has kept foundAt, droppedBy and chronicleSort since v1818.
emit_deep_read built the journal row without them, and live_pages copied
the sort word and never the date. A chronicle the agent read while he
played therefore filed the moment the sweep ran.

This drives the real parse, the real journal row and the real live page.
A monster name in the date field stays off the row. A date printed on a
different name is not worn by this one. A row that never parsed the field
says None, and its sighting carries no date.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import chronicle_retro as cr
import tv_diablo as TV


DATE = "08/20/2026, 00:49"
NAME = "Harlequin Crest"
OTHER = "Razorswitch"


def _led(name):
    return "uniques" if name == NAME else None


class MeasuredFindDateStaysOnTheLiveSighting(unittest.TestCase):
    def setUp(self):
        self._old_state, self._old_j = TV.STATE, TV.JOURNAL
        self._dir = tempfile.mkdtemp(prefix="found-date-")
        TV.STATE = os.path.join(self._dir, "state.json")
        TV.JOURNAL = os.path.join(self._dir, "j.jsonl")

    def tearDown(self):
        TV.STATE, TV.JOURNAL = self._old_state, self._old_j
        shutil.rmtree(self._dir, ignore_errors=True)

    def _emit(self, payload):
        rd = TV._parse_read(json.dumps(payload))
        return rd, TV.emit_deep_read(rd, n=1, frame_id="f_118")

    def _sight(self, rec, name=NAME):
        pages = cr.live_pages([rec], _led)
        self.assertEqual(len(pages), 1, "the chronicle row never became a live page")
        prop = cr.proposal_from_pages(pages)
        sights = (prop.get("uniques") or {}).get(name) or []
        self.assertEqual(len(sights), 1, "the name never became one sighting: %r" % prop)
        return pages[0]["resp"], sights[0]

    def test_a_parsed_date_is_journaled_and_hung_on_that_name(self):
        rd, rec = self._emit({
            "scene": "chronicle",
            "chronicleTab": "uniques",
            "chronicleSort": "Newest to Oldest",
            "names": [NAME],
            "discovered": [NAME],
            "foundAt": {NAME: DATE},
            "droppedBy": {NAME: "Andariel"},
            "conf": 0.9,
        })
        self.assertEqual(rd["foundAt"].get(NAME), DATE)
        self.assertEqual(rec["foundAt"].get(NAME), DATE,
                         "the journal row dropped the date the parse kept")
        self.assertEqual(rec["droppedBy"].get(NAME), "Andariel")
        self.assertEqual(rec["chronicleSort"], "newest")
        resp, sight = self._sight(rec)
        self.assertEqual(resp["foundAt"].get(NAME), DATE)
        self.assertEqual(sight.get("foundAt"), DATE)
        self.assertEqual(sight.get("droppedBy"), "Andariel")
        self.assertEqual(sight.get("sort"), "newest")
        stamp = cr.in_game_stamp([sight])
        self.assertEqual(stamp.get("at"), DATE)
        self.assertEqual(stamp.get("by"), "Andariel")

    def test_a_monster_name_is_not_stored_as_the_find_date(self):
        _rd, rec = self._emit({
            "scene": "chronicle",
            "chronicleTab": "uniques",
            "names": ["M'avina's True Sight"],
            "discovered": ["M'avina's True Sight"],
            "foundAt": {"M'avina's True Sight": "Doom Knight"},
            "conf": 0.9,
        })
        self.assertEqual(rec["foundAt"], {}, "a monster name was journaled as a find date")
        pages = cr.live_pages([rec], lambda n: "uniques")
        sights = cr.proposal_from_pages(pages)["uniques"]["M'avina's True Sight"]
        self.assertNotIn("foundAt", sights[0])
        self.assertEqual(cr.in_game_stamp(sights), {})

    def test_another_names_date_is_not_worn_by_this_one(self):
        _rd, rec = self._emit({
            "scene": "chronicle",
            "chronicleTab": "uniques",
            "names": [NAME],
            "discovered": [NAME],
            "foundAt": {OTHER: DATE},
            "conf": 0.9,
        })
        self.assertEqual(rec["foundAt"].get(OTHER), DATE)
        self.assertNotIn(NAME, rec["foundAt"])
        resp, sight = self._sight(rec)
        self.assertEqual(resp["foundAt"].get(OTHER), DATE)
        self.assertNotIn(NAME, resp["foundAt"])
        self.assertNotIn("foundAt", sight)
        self.assertEqual(cr.in_game_stamp([sight]), {})
        self.assertNotIn(OTHER, cr.proposal_from_pages(cr.live_pages([rec], _led))["uniques"])

    def test_a_row_that_never_parsed_the_field_stays_unknown(self):
        rec = TV.emit_deep_read({
            "area": "Harrogath", "scene": "chronicle", "names": [NAME],
            "discovered": [NAME], "conf": 0.9, "tz": [],
        }, n=2, frame_id="f_118b")
        self.assertIsNone(rec["foundAt"], "a read that never parsed a date measured an empty map")
        self.assertIsNone(rec["droppedBy"])
        self.assertIsNone(rec["chronicleSort"])
        resp, sight = self._sight(rec)
        self.assertEqual(resp["foundAt"], {})
        self.assertEqual(resp["droppedBy"], {})
        self.assertEqual(resp["sort"], "")
        self.assertNotIn("foundAt", sight)
        self.assertNotIn("droppedBy", sight)
        self.assertNotIn("sort", sight)
        self.assertEqual(cr.in_game_stamp([sight]), {})

RED_PROOF = [
    {"why": "#118 - emit_deep_read builds the journal row without the date the parse kept, so a live read files the sweep's moment",
     "file": "tv/tv_diablo.py",
     "find": "        \"foundAt\": rd.get(\"foundAt\"),\n",
     "replace": "        \"foundAt\": None,\n",
     "matches": 1},
    {"why": "#118 - live_pages copies the sort word and never the date, so the date dies between the journal and the page",
     "file": "tv/chronicle_retro.py",
     "find": "               \"foundAt\": (row.get(\"foundAt\") if isinstance(row.get(\"foundAt\"), dict)\n                           else row.get(\"found_at\") if isinstance(row.get(\"found_at\"), dict)\n                           else None),\n",
     "replace": "               \"foundAt\": None,\n",
     "matches": 1},
    {"why": "a monster name the reader put in the date field is journaled as the First Found date",
     "file": "tv/tv_diablo.py",
     "find": "                if _chron_stamp_ok(v3):\n                    found_at[k3] = v3\n",
     "replace": "                if True:\n                    found_at[k3] = v3\n",
     "matches": 1},
    {"why": "a date printed on a different name is worn by this one",
     "file": "tv/chronicle_retro.py",
     "find": "                _fa = (resp.get(\"foundAt\") or {}).get(nm)\n",
     "replace": "                _fa = (resp.get(\"foundAt\") or {}).get(nm) or next(iter((resp.get(\"foundAt\") or {}).values()), None)\n",
     "matches": 1},
    {"why": "a read that never parsed the field journals an empty map - a measured 'no dates' instead of UNKNOWN",
     "file": "tv/tv_diablo.py",
     "find": "        \"foundAt\": rd.get(\"foundAt\"),\n",
     "replace": "        \"foundAt\": rd.get(\"foundAt\") or {},\n",
     "matches": 1},
    {"why": "the journal row drops the dropper the parse kept",
     "file": "tv/tv_diablo.py",
     "find": "        \"droppedBy\": rd.get(\"droppedBy\"),\n",
     "replace": "        \"droppedBy\": {},\n",
     "matches": 1},
    {"why": "v1907 - the live page is built without the sort word, so no sighting carries it",
     "file": "tv/chronicle_retro.py",
     "find": "               \"sort\": row.get(\"chronicleSort\") or row.get(\"chronicle_sort\") or \"\",\n",
     "replace": "               \"sort\": \"\",\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
