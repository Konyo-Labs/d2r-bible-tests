# -*- coding: utf-8 -*-
"""#108 - EACH TERROR ZONE CARD WEARS ITS OWN MONSTER, THE SAME SPRITE QUICK WINS DRAWS.

His words, 11-07 ~11:30 IST, on the console's Terror Zone panel (Blood Moor, Den of Evil, Nihlathak's Temple and Halls of
Anguish wearing grey zone tiles): "for terror zones section i want them also updated with the proper .gifs related ... so its
unified". Every pick and its source is recorded in tv/data/monster_art_arreat.json "zones": the act boss whose fight the zone
is, else its super-unique, else its most common random pack in the board's own data, else the first monster of the wiki's
roster with a verified family sprite. A zone no source names keeps its zone art - never a guessed sprite. Like a Quick wins
tile, the monster is drawn alone (REG-3321).
RED_PROOF below.
"""
import hashlib
import io
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING on a non-UTF-8 console
    _enable()
except Exception:
    pass


def _read(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


class EachTerrorZoneWearsItsOwnMonster(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ui = _read("tv/control_ui.html")
        cls.tz = json.loads(re.search(r"var TZ_INFO = (\{.*?\});", cls.ui).group(1))
        cls.mon = json.loads(re.search(r"var TZ_MONSTER = (\{.*?\});", cls.ui).group(1))
        cls.rec = json.loads(_read("tv/data/monster_art_arreat.json"))
        cls.fandom = json.loads(_read("tv/data/monster_art_fandom.json"))

    def test_every_zone_is_its_recorded_pick(self):
        """* THE POINT: the console's table is exactly the recorded picks - a zone with a source wears it, one without has none"""
        want = dict((z, v["file"]) for z, v in self.rec["zones"].items() if v.get("file"))
        self.assertEqual(self.mon, want, "the console's zone monsters drifted from their recorded picks")
        self.assertEqual(sorted(self.rec["zones"]), sorted(self.tz), "a zone the console knows has no recorded pick (or the reverse)")
        bare = [z for z, v in self.rec["zones"].items() if not v.get("file")]
        self.assertTrue(all("never a guessed sprite" in self.rec["zones"][z]["by"] for z in bare), "a zone without a monster says nothing")
        self.assertGreaterEqual(len(self.mon), 70, "premise: %d of %d zones wear a monster" % (len(self.mon), len(self.tz)))
        self.assertEqual(self.mon.get("Den of Evil"), "d2mon_Corpsefire.gif")
        self.assertEqual(self.mon.get("Nihlathak's Temple"), "d2mon_Pindleskin.gif")

    def test_the_board_draws_the_same_table_the_same_way(self):
        """#108 'so its unified' - the board's Terror Zone rows read the SAME picks (two copies, one record: the law keeps them
        equal) by the zone's own key, and draw the monster alone"""
        board = _read("bible.html")
        bm = json.loads(re.search(r"\n  var TZ_MONSTER = (\{.*?\});", board).group(1))
        self.assertEqual(bm, self.mon, "the board's zone monsters drifted from the console's")
        i = board.index("function tzZoneRowHtml(zoneName){")
        row = board[i:board.index("const meta = t.nodata", i)]
        self.assertIn("const _mk = (typeof tzKey === 'function') ? tzKey(zoneName) : zoneName;", row)
        self.assertIn('<span class="tzt-z-art tzt-z-art-mon"><img class="tzt-z-mon" src="art/\'+mon+\'"', row)
        self.assertIn("const face = mon\n    ? '<span class=\"tzt-z-art tzt-z-art-mon\">", row,
                      "the row's face is not chosen by the zone's monster first")

    def test_every_monster_file_is_shipped_and_sourced(self):
        fand = set(os.path.basename(x.get("file", "")) for x in self.fandom.get("sprites") or [])
        bad = []
        for z, f in sorted(self.mon.items()):
            p = os.path.join(ROOT, "art", f)
            if not os.path.isfile(p):
                bad.append((z, f, "not in art/"))
            elif f in self.rec.get("rejected", {}):
                bad.append((z, f, "a file the cold look rejected"))
            elif f.startswith(("d2fam_", "d2arreat_")):
                got = hashlib.sha1(open(p, "rb").read()).hexdigest()
                if (self.rec["files"].get(f) or {}).get("sha1") != got:
                    bad.append((z, f, "not the file its record names"))
            elif f not in fand:
                bad.append((z, f, "no recorded source"))
        self.assertEqual(bad, [], "a Terror Zone monster is missing, unsourced or rejected: %s" % bad)

    def test_the_card_draws_the_monster_alone_by_the_zones_own_key(self):
        i = self.ui.index("var mon = Object.prototype.hasOwnProperty.call(TZ_MONSTER, _mk)")
        blk = self.ui[i - 200:self.ui.index("var meta = t.nodata", i)]
        self.assertIn("var _mk = _tzKey(x);", blk, "the monster is looked up by the raw feed name, not the key its art uses")
        self.assertIn('<span class="tzz-art tzz-art-mon"><img class="tzz-mon" src="/art/\' + mon + \'"', blk)
        mon_face = blk[blk.index("? '<span class=\"tzz-art tzz-art-mon\">"):blk.index(": file")]
        self.assertNotIn("background-image", mon_face, "the zone is painted behind the monster again")


RED_PROOF = [
    {"why": "#108 - the board's Terror Zone rows go back to zone art while the console wears the monsters (not unified)",
     "file": "bible.html",
     "find": "  const face = mon\n    ? '<span class=\"tzt-z-art tzt-z-art-mon\"><img class=\"tzt-z-mon\" src=\"art/'+mon+'\"",
     "replace": "  const face = false\n    ? '<span class=\"tzt-z-art tzt-z-art-mon\"><img class=\"tzt-z-mon\" src=\"art/'+mon+'\"",
     "matches": 1},
    {"why": "#108 - a zone loses its monster with no recorded reason (the console and the record disagree)",
     "file": "control_ui.html",
     "find": "\"Den of Evil\": \"d2mon_Corpsefire.gif\", ",
     "replace": "",
     "matches": 1},
    {"why": "#108 - the zone's monster is looked up by the raw feed name, so a renamed zone loses it",
     "file": "control_ui.html",
     "find": "        var _mk = _tzKey(x);",
     "replace": "        var _mk = x;",
     "matches": 1},
    {"why": "#108 - the zone art is painted behind the monster again",
     "file": "control_ui.html",
     "find": "? '<span class=\"tzz-art tzz-art-mon\"><img class=\"tzz-mon\"",
     "replace": "? '<span class=\"tzz-art tzz-art-mon\" style=\"background-image:url(/art/tz_' + file + '.jpg)\"><img class=\"tzz-mon\"",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
