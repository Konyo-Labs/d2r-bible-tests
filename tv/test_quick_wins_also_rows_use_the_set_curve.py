# -*- coding: utf-8 -*-
"""v3893 (#43, REG-3557) - THE QUICK-WINS 'ALSO' ROWS HAND THE ITEM TO THE SET MF CURVE.

The ranked place rows already go through effChance (which asks setMfChance when the item is a
set piece at a measured farm). The leftover `_qwAlso` once-path called `effChance(base, boss, diff)`
without the item, so a set used the unique curve; regular rows used `adjustChance` alone.
The once-path now passes the item (`x.n`); regular rows ask setMfChance first and only fall back
to adjustChance — they do not pick up /players via a full effChance.
RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
NODE = shutil.which("node")


def _cut(src, start, end):
    i = src.index(start)
    return src[i:src.index(end, i) + len(end) if end.startswith("\n") else src.index(end, i)]


class QuickWinsAlsoRowsUseTheSetCurve(unittest.TestCase):

    def test_the_once_path_passes_the_item_and_regular_rows_ask_setMfChance(self):
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            src = fh.read()
        i = src.index("  function _qwAlso(x, worst, cap){")
        fn = src[i:src.index("\n  }\n", i)]
        self.assertIn("effChance(r[2], r[0], r[1], x && x.n)", fn)
        self.assertIn("setMfChance(r[4], x && x.n, r[0], r[1], mf)", fn)
        self.assertIn("adjustChance(r[4], mf)", fn)
        self.assertNotIn("effChance(r[4]", fn)

    def test_a_set_item_on_the_once_path_uses_setMfChance(self):
        if not NODE:
            self.fail("node is not on this machine - this law does not skip")
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            src = fh.read()
        i = src.index("  function _qwAlso(x, worst, cap){")
        fn = src[i:src.index("\n  }\n", i) + 5]
        js = (
            "var mf = 300;\n"
            "var _QW_DIFF = { hell: 'Hell' };\n"
            "var asked = [];\n"
            "function setMfChance(base, item, bossId, diffKey, m){ asked.push([base, item, bossId, diffKey, m]); return item === \"Civerb's Icon\" ? 99 : undefined; }\n"
            "function adjustChance(c){ return c; }\n"
            "function effChance(base, bossId, diffKey, item){ var s = setMfChance(base, item, bossId, diffKey, mf); return s !== undefined ? s : base; }\n"
            "var QW_TARGETS = { andariel: { n: 'Andariel', a: 'Catacombs Level 4', once: 1 } };\n"
            "var QW_PLACES = { \"Civerb's Icon\": { f: [['andariel', 'hell', 1234]], r: [] } };\n"
            + fn + "\n"
            "process.stdout.write(JSON.stringify({ rows: _qwAlso({ n: \"Civerb's Icon\" }, null, 5), asked: asked }));\n"
        )
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        got = json.loads(r.stdout)
        self.assertEqual(got["rows"][0]["chance"], 99, got)
        self.assertEqual(got["asked"][0][1], "Civerb's Icon", got["asked"])


RED_PROOF = [
    {"why": "v3893 (#43, REG-3557) - the once-path still calls effChance without the item",
     "file": "bible.html",
     "find": "chance: effChance(r[2], r[0], r[1], x && x.n) });   // his own /players factor (PLACE_PF); #43 REG-3557 the item, so a set uses setMfChance\n",
     "replace": "chance: effChance(r[2], r[0], r[1]) });   // his own /players factor (PLACE_PF)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
