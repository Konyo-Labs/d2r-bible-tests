# -*- coding: utf-8 -*-
"""v3894 (#153, REG-3568) - A RESISTANCE ROW NAMES THE PARTS THE ENGINE ALREADY SUMMED.

Hell's penalty and Anya's scrolls come from row.parts (difficultylevels.txt
ResistPenalty and "Anya's resistance scrolls", +10 per completed difficulty).
Nothing here invents -100 or +30; the visible line is the parts the engine attached.
RED_PROOF below.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()


def _read(rel):
    path = os.path.join(HERE, os.path.basename(rel)) if rel.startswith("tv/") else os.path.join(ROOT, rel)
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


class AResistanceRowNamesItsHellAnyaAndGearParts(unittest.TestCase):

    def test_the_parts_line_reads_the_engines_own_parts(self):
        src = _read("bible.html")
        self.assertIn("function _cbResParts(r)", src)
        self.assertIn("cb-res-parts", src)
        self.assertIn("/^res-(fire|cold|ltng|pois|all)$/", src)
        self.assertIn("_cbResParts(r)", src)
        self.assertIn("p.src || p.via || 'gear'", src)


RED_PROOF = [
    {"why": "v3894 (#153, REG-3568) - the resistance parts line is gone",
     "file": "bible.html",
     "find": "    return bits.length ? '<span class=\"cb-res-parts\">' + esc(bits.join(' \\u00b7 ')) + '</span>' : '';\n",
     "replace": "    return '';\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
