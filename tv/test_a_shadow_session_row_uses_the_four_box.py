# -*- coding: utf-8 -*-
"""v3892 (REG-3536) - A SHADOW SESSION ROW USES THE SAME FOUR-BOX AS THE OWNER'S SHELF CARD.

His rule: shadow-mode session view uses the same four-box template as the regular profile console
for STASH / CHRONICLES / UNIQUES / SETS. MEASURED: `_paintShelf` already paints `.shc-stats` via
`_scell`; `_shadowSessionRow` (what SHELF opens under a shadow, and what the owner dossier draws)
printed those facts only as sentences (`N chronicles found`, a stashed-names dump) and never the
four boxes. `_fourBoxHtml` now paints the same `.shc-stats` cells. A shadow digest row fills them
from `stashed` / `farmed` / `chroniclesFound`; an owner card fills STASH from `route.stashed` or `sm.stashed` (REG-3543),
not kaiClasses frame sums, and the other boxes from `chron` / `route.chroniclesFound`. A missing number is '?' and a counted zero is an em dash.
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


def _row(src):
    return _cut(src, "  function _shadowSessionRow(s, ix){")


def _box(src):
    return _cut(src, "  function _fourBoxHtml(sm){")


class AShadowSessionRowUsesTheFourBox(unittest.TestCase):

    def test_the_shadow_row_paints_the_four_box(self):
        body = _row(_page())
        self.assertIn("+ _fourBoxHtml(s)", body)
        self.assertIn("ssv-who", body)

    def test_the_four_box_is_the_same_template(self):
        body = _box(_page())
        for label in ("stash", "chronicles", "uniques", "sets"):
            self.assertIn("'%s'" % label, body, "the four-box dropped the %s cell" % label)
        self.assertIn('class="shc-stats"', body)
        self.assertIn('class="shc-stat"', body)
        self.assertNotIn("sm.kaiClasses", body)
        self.assertIn("sm.stashed", body)
        self.assertIn("sm.route.stashed", body)
        self.assertIn("sm.farmed", body)
        self.assertIn("sm.chroniclesFound", body)
        self.assertIn("sm.chron", body)

    def test_a_digest_row_fills_the_boxes_from_its_own_numbers(self):
        if NODE is None:
            self.fail("node is not on this machine - this law does not skip")
        src = _page()
        code = _cut(src, "  function esc(s){") + "\n" + _box(src)
        case = {
            "chroniclesFound": 2,
            "farmed": {"uniques": [["Harlequin Crest", 1], ["The Stone of Jordan", 1]], "sets": []},
            "stashed": {"runes": [["Ber Rune", 2]]},
        }
        harness = r"""
const code = process.env.BOX_CODE;
const row = JSON.parse(process.env.BOX_ROW);
const fn = new Function(code + '; return _fourBoxHtml;');
const html = fn()(row);
if (typeof html !== 'string') { console.error('not a string'); process.exit(2); }
process.stdout.write(html);
"""
        r = subprocess.run(
            [NODE, "-"], input=harness, capture_output=True, text=True, encoding="utf-8",
            timeout=30, env=dict(os.environ, BOX_CODE=code, BOX_ROW=json.dumps(case)))
        self.assertEqual(r.returncode, 0, r.stderr[-400:] if r.stderr else r.stdout[-400:])
        html = r.stdout
        self.assertIn('class="shc-stats"', html)
        self.assertIn(">stash<", html)
        self.assertIn(">chronicles<", html)
        self.assertIn(">uniques<", html)
        self.assertIn(">sets<", html)
        self.assertIn("2", html)           # chroniclesFound and/or stash count
        self.assertIn("\U0001f3c6 2", html)  # two uniques
        self.assertIn("\u2014", html)        # no sets -> em dash
        self.assertNotIn(">?<", html)

    def test_the_node_cutters_include_the_helper(self):
        files = [
            "test_a_shadow_shelf_says_playtime_and_plays_served_frames.py",
            "test_each_shadow_age_names_its_record.py",
            "test_a_shadow_shelf_shows_the_owners_sessions.py",
        ]
        needle = '"  function _fourBoxHtml(sm){"'
        for name in files:
            with io.open(os.path.join(HERE, name), encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn(needle, text, "%s no longer extracts _fourBoxHtml" % name)


RED_PROOF = [
    {"why": "v3892 (REG-3536) - a shadow session row no longer paints the four-box",
     "file": "tv/control_ui.html",
     "find": "      + _fourBoxHtml(s)\n",
     "replace": "",
     "matches": 1},
    {"why": "v3892 (REG-3536) - a shadow digest's farmed uniques and sets no longer fill the boxes",
     "file": "tv/control_ui.html",
     "find": "    } else if (sm.farmed && typeof sm.farmed === 'object') {\n",
     "replace": "    } else if (false && sm.farmed && typeof sm.farmed === 'object') {\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
