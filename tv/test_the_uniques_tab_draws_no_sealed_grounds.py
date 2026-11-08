# -*- coding: utf-8 -*-
"""v3884 - THE UNIQUES TAB DRAWS NO "SEALED GROUNDS" BAND (his ruling 2026-11-08 ~10:31).

His words, with a screenshot of the band ("NORMAL TZ MEPHISTO - GROUNDS SEALED all 103 verified uniques found · runs here are
trade loot now", six rows): "sealed ground is not technically right here.. i didnt farm them all like it seems. but regardless
its pointless to have here and see hide it plesae from the section". v619 drew the band for every run whose whole verified
pool is found. The band is not drawn now; the scan still knows s.sealed, so a run whose pool is found still leaves Best runs
(v619's cancel-out sync, guarded by tests/v619_grail_forges_sync.spec.ts on GitHub), and an empty runs list says so.

Reads the page's own source, comments stripped (a law must not be satisfied by the sentence that explains the change). The
rendered half is the spec's. RED_PROOF below. [[source-reading-guard]]
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")


def _code():
    with io.open(BIBLE, encoding="utf-8") as fh:
        src = fh.read()
    src = re.sub(r"/\*.{0,4000}?\*/", "", src, flags=re.S)
    return "\n".join(re.sub(r"(^|\s)//.*$", r"\1", ln) for ln in src.split("\n"))


class TheUniquesTabDrawsNoSealedGrounds(unittest.TestCase):

    def test_the_band_is_not_drawn(self):
        """* THE POINT - no code draws the Sealed grounds header or its rows"""
        code = _code()
        self.assertNotIn("Sealed grounds <span class=\"forge-sec-ct\">", code, "the Sealed grounds header is drawn again")
        self.assertNotIn("' — grounds sealed</span>", code, "a 'grounds sealed' row is drawn again")

    def test_premise_the_scan_still_seals_and_the_runs_still_render(self):
        """the run still leaves Best runs: the scan keeps s.sealed, and the runs section is still drawn"""
        code = _code()
        self.assertIn("forge-sec forge-sec-pipe", code, "PREMISE: the Best runs section is gone - this law reads the wrong page")
        self.assertRegex(code, r"sealed\s*[:=]", "PREMISE: the scan no longer computes sealed runs")

    def test_an_empty_runs_list_says_so(self):
        code = _code()
        self.assertIn("if(F==='runs'&&!s.runs.length){", code,
                      "the empty runs list waits for a band that is no longer drawn - nothing would say it is empty")


RED_PROOF = [
    {"why": "v3884 - the Sealed grounds header is drawn again",
     "file": "bible.html",
     "find": "    if(F==='runs'&&!s.runs.length){   // v3884 - no band to stand in for the empty runs list\n",
     "replace": "    if(show('runs')&&(s.sealed||[]).length){ H.push('<div class=\"forge-sec forge-sec-done\"><div class=\"forge-sec-h\">"
                "Sealed grounds <span class=\"forge-sec-ct\">'+s.sealed.length+'</span></div></div>'); }\n"
                "    if(F==='runs'&&!s.runs.length){   // v3884 - no band to stand in for the empty runs list\n",
     "matches": 1},
    {"why": "v3884 - an empty runs list waits for the band again (says nothing when every run is sealed)",
     "file": "bible.html",
     "find": "    if(F==='runs'&&!s.runs.length){   // v3884 - no band to stand in for the empty runs list\n",
     "replace": "    if(F==='runs'&&!s.runs.length&&!(s.sealed||[]).length){\n", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
