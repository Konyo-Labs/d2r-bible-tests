# -*- coding: utf-8 -*-
"""#251 (REG-2929) - THE ROSTER PUBLISH'S CHARACTERS SECTION CARRIES THIS PC'S SAVE NAMES, EXACTLY SPELLED, NEVER AN ID.

roster_publish.with_save_names(section, saves, now_ms) folds the console's /api/saves answer (control_app.saves_answer,
REG-2926) into the characters section the console publishes (control_app._roster_reads, the reels' path):
  * a learned row whose name folds to a save name takes the save's spelling and keeps its class and level;
  * a save name no row holds joins with its name only, and the section's count grows by it;
  * only names leave - never an account id, never the id count;
  * saves that did not answer, or name nobody, leave the section exactly as it was; a PC whose reels learned nothing
    publishes a section from its saves alone; a builds book's section is builds, and is left alone.
Python only, fixtures only: the answer is handed in, so no law here reads a real save folder. RED_PROOF below.
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

import roster_publish as RP  # noqa: E402

NOW = 1793240000000
SAVES = {"ok": True, "state": "folder",
         "chars": [{"name": "Konyolock", "ids": 1}, {"name": "Hammer-Din", "ids": 2}, {"name": "Hammer-Din", "ids": 2}]}


def _learned():
    return RP.characters_read(True, {"chars": {"a": {}, "b": {}}},
                              [{"name": "KONYOLOCK", "cls": "Warlock", "level": 88, "title": "Patriarch"},
                               {"name": "Mulebox", "cls": "Paladin", "level": 1}], NOW)


class TheRosterCarriesThisPcsSaveNames(unittest.TestCase):

    def test_a_reel_name_takes_the_saves_spelling_and_a_new_name_joins(self):
        got = RP.with_save_names(_learned(), SAVES, NOW)
        names = [r["name"] for r in got["rows"]]
        self.assertEqual(names, ["Konyolock", "Mulebox", "Hammer-Din"], "a save name was lost, doubled or misspelled")
        self.assertEqual(got["rows"][0], {"name": "Konyolock", "cls": "Warlock", "level": 88, "title": "Patriarch"})
        self.assertEqual(got["rows"][2], {"name": "Hammer-Din"}, "a save-only character carries a class or level nobody read")
        self.assertEqual(got["counts"], 3, "the count did not grow by the character only the saves name")

    def test_no_id_leaves(self):
        for sec in (RP.with_save_names(_learned(), SAVES, NOW), RP.with_save_names(None, SAVES, NOW)):
            for r in sec["rows"]:
                self.assertNotIn("ids", r, "an account id count left in the published characters")
            self.assertEqual(RP.section_of(sec, NOW)["rows"], sec["rows"], "the publish's own cleaning dropped a row")

    def test_saves_that_did_not_answer_change_nothing(self):
        base = _learned()
        for bad in (None, {"ok": False, "chars": None}, {"ok": True, "state": "no-folder", "chars": None},
                    {"ok": True, "chars": []}):
            self.assertEqual(RP.with_save_names(base, bad, NOW), base, bad)
            self.assertIsNone(RP.with_save_names(None, bad, NOW), bad)

    def test_a_pc_with_no_reels_publishes_its_saves_alone(self):
        got = RP.section_of(RP.with_save_names(None, SAVES, NOW), NOW)
        self.assertEqual(got, {"asOf": NOW, "counts": 2, "rows": [{"name": "Konyolock"}, {"name": "Hammer-Din"}]})

    def test_a_builds_book_is_left_alone(self):
        book = {"read": True, "asOf": NOW, "counts": 1, "rows": [{"name": "MF Sorc"}], "allow": ("build",)}
        self.assertIs(RP.with_save_names(book, SAVES, NOW), book)

    def test_the_console_publishes_through_it(self):
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        reads = src.split("def _roster_reads(", 1)[1].split("\ndef ", 1)[0]
        a = reads.find("got = _rp.characters_read(present, ledger, learned, now_ms)")
        b = reads.find("got = _rp.with_save_names(got, saves_answer(), now_ms)")
        c = reads.find('reads["characters"] = got', max(a, 0))
        self.assertTrue(0 <= a < b < c, "the reels' characters section is published without this PC's save names")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "#251 (REG-2929) - a learned row keeps the reels' spelling though the save folder spells it",
     "file": "tv/roster_publish.py",
     "find": "        if hit is not None:\n            hit[\"name\"] = n\n            continue\n",
     "replace": "        if hit is not None:\n            continue\n",
     "matches": 1},
    {"why": "#251 (REG-2929) - a character only the saves name is never published",
     "file": "tv/roster_publish.py",
     "find": "        row = {\"name\": n}\n        rows.append(row)\n",
     "replace": "        row = {\"name\": n}\n",
     "matches": 1},
    {"why": "#251 (REG-2929) - the saves' rows go out whole, account id count and all",
     "file": "tv/roster_publish.py",
     "find": "\"rows\": [{\"name\": n} for n in names], \"allow\": allow}",
     "replace": "\"rows\": [dict(r) for r in saves[\"chars\"]], \"allow\": allow}",
     "matches": 1},
    {"why": "#251 (REG-2929) - the count does not grow by the characters only the saves name",
     "file": "tv/roster_publish.py",
     "find": "        out[\"counts\"] = c + added\n",
     "replace": "        out[\"counts\"] = c\n",
     "matches": 1},
    {"why": "#251 (REG-2929) - the console publishes the reels' section without this PC's save names",
     "file": "tv/control_app.py",
     "find": "        got = _rp.with_save_names(got, saves_answer(), now_ms)\n",
     "replace": "",
     "matches": 1},
]
