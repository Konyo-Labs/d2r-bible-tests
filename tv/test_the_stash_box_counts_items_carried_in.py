# -*- coding: utf-8 -*-
"""v3892 (#184, REG-3543) - THE STASH BOX COUNTS ITEMS CARRIED INTO THE STASH, NEVER FRAME SUMS.

His rule: STASH = items carried into the stash. MEASURED: the owner's shelf card and
`_fourBoxHtml` both summed every kaiClasses `stash*` bucket (frames the reader classed as a
stash panel, including town frames that leak into those buckets — open defect #87). They now
count the grouped names on `sm.stashed` or `sm.route.stashed`. Missing stays '?'; a counted
zero is an em dash.
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

UI = os.path.join(HERE, "control_ui.html")
NODE = shutil.which("node")


def _page():
    with io.open(UI, encoding="utf-8") as fh:
        return fh.read()


def _cut(src, sig):
    if src.count(sig) != 1:
        raise AssertionError("%r occurs %d times" % (sig, src.count(sig)))
    i = src.index(sig)
    depth = 0
    for j in range(src.index("{", i), len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
    raise AssertionError("%r never closed" % sig)


class TheStashBoxCountsItemsCarriedIn(unittest.TestCase):

    def test_neither_painter_sums_kaiClasses_stash_frames(self):
        src = _page()
        box = _cut(src, "  function _fourBoxHtml(sm){")
        self.assertNotIn("sm.kaiClasses", box)
        self.assertIn("sm.stashed", box)
        self.assertIn("sm.route.stashed", box)
        self.assertIn("groupedTotal(stashSrc)", box)
        self.assertIn("var _stashSrc = (sm.stashed && typeof sm.stashed === 'object') ? sm.stashed", src)
        self.assertIn("((sm.route && typeof sm.route === 'object') ? sm.route.stashed : null)", src)
        self.assertNotIn("if (String(_kk).indexOf('stash') === 0) { _stashN += (_kc[_kk] || 0); }", src)

    def test_a_stashed_name_fills_the_box_and_missing_stays_unknown(self):
        if NODE is None:
            self.fail("node is not on this machine - this law does not skip")
        src = _page()
        code = _cut(src, "  function esc(s){") + "\n" + _cut(src, "  function _fourBoxHtml(sm){")
        harness = r"""
const code = process.env.BOX_CODE;
const fn = new Function(code + '; return _fourBoxHtml;');
const html = fn()(JSON.parse(process.env.BOX_ROW));
const miss = fn()({ chroniclesFound: 0, farmed: { uniques: [], sets: [] } });
process.stdout.write(JSON.stringify({ html: html, miss: miss }));
"""
        row = {"chroniclesFound": 0,
               "farmed": {"uniques": [], "sets": []},
               "stashed": {"runes": [["Ber Rune", 2], ["Jah Rune", 1]]},
               "kaiClasses": {"stash": 19, "stash-gems": 4}}
        r = subprocess.run(
            [NODE, "-"], input=harness, capture_output=True, text=True, encoding="utf-8",
            timeout=30, env=dict(os.environ, BOX_CODE=code, BOX_ROW=json.dumps(row)))
        self.assertEqual(r.returncode, 0, r.stderr[-400:] if r.stderr else r.stdout[-400:])
        out = json.loads(r.stdout)
        self.assertIn("3", out["html"], "two Ber and one Jah should read 3, not the 23 frame sum: %s" % out["html"])
        self.assertNotIn("19", out["html"])
        self.assertIn(">?<", out["miss"], "a row with no stashed list must stay UNKNOWN: %s" % out["miss"])


RED_PROOF = [
    {"why": "v3892 (#184, REG-3543) - the owner card ignores route.stashed again",
     "file": "tv/control_ui.html",
     "find": "      var _stashSrc = (sm.stashed && typeof sm.stashed === 'object') ? sm.stashed\n"
             "        : ((sm.route && typeof sm.route === 'object') ? sm.route.stashed : null);\n",
     "replace": "      var _stashSrc = null;\n",
     "matches": 1},
    {"why": "v3892 (#184, REG-3543) - the four-box sums kaiClasses frames again",
     "file": "tv/control_ui.html",
     "find": "    var stashSrc = (sm.stashed && typeof sm.stashed === 'object') ? sm.stashed\n"
             "                 : ((sm.route && typeof sm.route === 'object' && sm.route.stashed && typeof sm.route.stashed === 'object') ? sm.route.stashed : null);\n"
             "    var stashN = groupedTotal(stashSrc);\n",
     "replace": "    var stashSrc = (sm.kaiClasses && typeof sm.kaiClasses === 'object') ? sm.kaiClasses : null;\n"
               "    var stashN = 0;\n"
               "    if (stashSrc) { for (var _kk in stashSrc) { if (String(_kk).indexOf('stash') === 0) stashN += (stashSrc[_kk] || 0); } }\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
