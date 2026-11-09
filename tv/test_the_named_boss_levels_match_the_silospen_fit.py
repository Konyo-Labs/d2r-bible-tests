# -*- coding: utf-8 -*-
"""v3892 (#181, REG-3541) - THREE NAMED BOSS LEVELS ON THE PAGE MATCH SILOSPEN'S FITTED ILVL.

The unique-first quality roll (SET_MF_FARM, written from silospen D2R_ROW_3_0) is computed at
Duriel (22, 55, 88), Mephisto (26, 59, 87) and Diablo (40, 62, 94). The page's BOSSES diffs
still showed Hell Duriel mlvl 80, Nightmare Mephisto 58 and Nightmare Diablo 66. Those three
named cells now read the same ilvl SET_MF_FARM already fitted. A later sweep of every other
farm waits on the same confirmation, and is not this slice.
RED_PROOF below.
"""
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
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

BIBLE = os.path.join(ROOT, "bible.html")
NAMED = (("duriel", "HELL", "hell"), ("mephisto", "NM", "nm"), ("diablo", "NM", "nm"))


def _src():
    with io.open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _bosses(src):
    i = src.find("const BOSSES = ")
    start = src.index("[", i)
    depth = 0
    for j in range(start, len(src)):
        if src[j] == "[":
            depth += 1
        elif src[j] == "]":
            depth -= 1
            if depth == 0:
                return json.loads(src[start:j + 1])
    raise AssertionError("BOSSES never closed")


def _farm(src):
    m = re.search(r"const SET_MF_FARM = (\{.*?\});", src)
    if not m:
        raise AssertionError("SET_MF_FARM is gone")
    return json.loads(m.group(1))


class TheNamedBossLevelsMatchTheSilospenFit(unittest.TestCase):

    def test_the_three_named_cells_match_the_fitted_ilvl(self):
        src = _src()
        bosses = {b["id"]: b for b in _bosses(src)}
        farm = _farm(src)
        for fid, lab, key in NAMED:
            self.assertIn(fid, bosses, "BOSSES lost %s" % fid)
            cell = next((d for d in bosses[fid].get("diffs") or [] if d.get("label") == lab and not d.get("terror")), None)
            self.assertIsNotNone(cell, "%s %s is not on the page" % (fid, lab))
            fitted = (farm.get(fid) or {}).get(key)
            self.assertTrue(fitted, "SET_MF_FARM lost %s.%s" % (fid, key))
            self.assertEqual(cell.get("mlvl"), fitted[0],
                             "%s %s is mlvl %s, not the fitted ilvl %s" % (fid, lab, cell.get("mlvl"), fitted[0]))


RED_PROOF = [
    {"why": "v3892 (#181, REG-3541) - Hell Duriel is mlvl 80 again, not the fitted 88",
     "file": "bible.html",
     "find": "\"mlvl\":75,\"tcMax\":85,\"tc\":\"TC 78\"},{\"label\":\"HELL\",\"terror\":false,\"mlvl\":88",
     "replace": "\"mlvl\":75,\"tcMax\":85,\"tc\":\"TC 78\"},{\"label\":\"HELL\",\"terror\":false,\"mlvl\":80",
     "matches": 1},
    {"why": "v3892 (#181, REG-3541) - Nightmare Mephisto is mlvl 58 again, not the fitted 59",
     "file": "bible.html",
     "find": "\"mlvl\":45,\"tcMax\":78,\"tc\":\"TC 57\"},{\"label\":\"NM\",\"terror\":false,\"mlvl\":59",
     "replace": "\"mlvl\":45,\"tcMax\":78,\"tc\":\"TC 57\"},{\"label\":\"NM\",\"terror\":false,\"mlvl\":58",
     "matches": 1},
    {"why": "v3892 (#181, REG-3541) - Nightmare Diablo is mlvl 66 again, not the fitted 62",
     "file": "bible.html",
     "find": "\"mlvl\":45,\"tcMax\":78,\"tc\":\"TC 60\"},{\"label\":\"NM\",\"terror\":false,\"mlvl\":62",
     "replace": "\"mlvl\":45,\"tcMax\":78,\"tc\":\"TC 60\"},{\"label\":\"NM\",\"terror\":false,\"mlvl\":66",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
