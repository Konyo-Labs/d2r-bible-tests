# -*- coding: utf-8 -*-
"""#104 (REG-3587) - A BUILDS BOOK NEVER HIDES THIS PC'S SAVE NAMES (Crest, Morph, ...).

MEASURED 11-07 on Dean: /api/saves named Crest, Morph, Morphad, ... but the roster upload's
characters section was his builds book ("Barbarian build", "Sorceress build") because
_roster_reads set used_book and skipped with_save_names. A build never hides a character:
the builds section keeps its rows, and the save names ride beside it as inGame.

Fixtures only - no real save folder is read. RED_PROOF below.
"""
import io
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
         "chars": [{"name": "Crest"}, {"name": "Morph"}, {"name": "Morphad"}]}


class ABuildsBookDoesNotHideSaveNames(unittest.TestCase):

    def test_crest_and_morph_ride_beside_the_builds(self):
        book = {"read": True, "asOf": NOW, "counts": 1,
                "rows": [{"name": "Barbarian build"}], "allow": ("build",)}
        chars = RP.with_save_names(None, SAVES, NOW)
        got = RP.with_ingame_beside_builds(book, chars)
        self.assertEqual([r["name"] for r in got["rows"]], ["Barbarian build"],
                         "the builds themselves moved: %s" % got)
        self.assertEqual(got["allow"], ("build",))
        names = [r["name"] for r in got["inGame"]["rows"]]
        self.assertEqual(names, ["Crest", "Morph", "Morphad"], names)

    def test_with_save_names_still_leaves_the_builds_rows_alone(self):
        book = {"read": True, "asOf": NOW, "counts": 1,
                "rows": [{"name": "Barbarian build"}], "allow": ("build",)}
        self.assertIs(RP.with_save_names(book, SAVES, NOW), book)

    def test_the_console_joins_them_even_when_a_book_is_used(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        reads = src.split("def _roster_reads(", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("with_ingame_beside_builds(", reads,
                      "_roster_reads no longer joins save names beside a builds book")
        a = reads.find("got = _rp.characters_read(present, ledger, learned, now_ms)")
        b = reads.find("got = _rp.with_save_names(got, saves_answer(), now_ms)")
        c = reads.find("with_ingame_beside_builds(")
        self.assertTrue(0 <= a < b < c, "save names are still skipped when a builds book is used")


RED_PROOF = [
    {"why": "REG-3587 - a builds book hides Crest and Morph again",
     "file": "tv/roster_publish.py",
     "find": "        out[\"inGame\"] = {\"rows\": list(chars[\"rows\"]),\n",
     "replace": "        out[\"inGame\"] = {\"rows\": [],\n",
     "matches": 1},
    {"why": "REG-3587 - the console skips save names when a builds book is used",
     "file": "tv/control_app.py",
     "find": "                reads[\"characters\"] = _rp.with_ingame_beside_builds(reads[\"characters\"], got)\n",
     "replace": "                reads[\"characters\"] = reads[\"characters\"]\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
