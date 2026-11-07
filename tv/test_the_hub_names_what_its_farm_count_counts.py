# -*- coding: utf-8 -*-
"""REG-3328 (#63, GrokBot 6698868304 on 11-07: "Fleet API rosters.uniques = 403, and Quick wins shows 403 (6 + 397). The
home card says '380 grails still out there', which doesn't match.") - THE HOME CARD NAMES WHAT ITS NUMBER COUNTS.

The console hub's next-chronicle card, when the ranker cannot answer, printed farm.length - the length of d2r_grailFarm,
which holds a missing UNIQUE only when it has a farm on record - as "N grails still out there": a third uniques number
worded as the count still missing, and in a word ("grail") his v2269 ruling took off the console. It now says "N missing
uniques with a farm on record". Held here on the source, comments stripped: the line names its population, and no
user-visible string of the console says "grails still out there". RED_PROOF below.
"""
import io
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def _code(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return "\n".join(l.split("//", 1)[0] if "://" not in l else l for l in src.split("\n"))


class TheHubNamesWhatItsFarmCountCounts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            cls.src = _code(fh.read())

    def test_the_idle_line_names_its_population(self):
        i = self.src.index("async function hubNextGrail(){")
        body = self.src[i:self.src.index("\n  }\n", i)]
        self.assertIn("' missing unique' + (farm.length === 1 ? '' : 's') + ' with a farm on record", body)

    def test_no_console_string_says_grails_still_out_there(self):
        self.assertNotIn("grails still out there", self.src)


RED_PROOF = [
    {"why": "REG-3328 - the hub prints its farm list's length as the uniques still missing, in a word he ruled out",
     "file": "control_ui.html",
     "find": "' missing unique' + (farm.length === 1 ? '' : 's') + ' with a farm on record · ranking unavailable right now",
     "replace": "' grails still out there · ranking unavailable right now",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
