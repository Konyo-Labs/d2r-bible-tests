# -*- coding: utf-8 -*-
"""v3894 (#95, REG-3573) - ADD MOD SEARCH MATCHES AN AFFIX'S OWN STAT KEY.

Typing a key the affix already carries (fcr on a Faster Cast Rate roll) finds it,
alongside the printed text and the affix name. No abbreviation table was invented.
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


class AddModSearchMatchesAnAffixStatKey(unittest.TestCase):

    def test_the_filter_reads_the_affix_keys(self):
        src = _read("bible.html")
        self.assertIn("function _cbAfKeys(a)", src)
        self.assertIn("keys.indexOf(qq) < 0", src)
        self.assertIn("((a && a[11]) || [])", src)


RED_PROOF = [
    {"why": "v3894 (#95, REG-3573) - search no longer matches an affix stat key",
     "file": "bible.html",
     "find": "        var keys = _cbAfKeys(a);\n        if (qq && t.toLowerCase().indexOf(qq) < 0 && String(a[2]).toLowerCase().indexOf(qq) < 0\n            && keys.indexOf(qq) < 0 && !keys.some(function(k){ return k.indexOf(qq) >= 0; })) return;\n",
     "replace": "        if (qq && t.toLowerCase().indexOf(qq) < 0 && String(a[2]).toLowerCase().indexOf(qq) < 0) return;\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
