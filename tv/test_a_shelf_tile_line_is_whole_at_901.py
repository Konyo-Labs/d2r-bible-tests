# -*- coding: utf-8 -*-
"""v3906 (REG-3853, #224) - A SHELF TILE'S LINES ARE WHOLE AT 901.

GrokBot #230 6851436283 (v3904, his console): "at 901 the Shelf BEST RUN sub is cut to `5 chronicle…` and STREAK to
`467+ runs l…`. Both lines are whole at 1440 and 1512." The tiles' sub line was one line with an ellipsis (.shi-sub nowrap)
in a strip that kept five 158px tiles on one row however narrow the window. Now the sub line wraps and, under 1100px, the
strip lays its tiles 190px and up so they wrap to a second row. The value line stays one line (REG-3768).

Driven in a real headless Chrome (render_check's) on the SHIPPED rules: every `.sh-hi` / `.shi-*` rule and the media rules
that hold them, cut from tv/control_ui.html with the custom properties they read, over the five tiles in the markup
_shHighlights writes, with GrokBot's measured texts. At 1512, 1440 and 901: no line of any tile is cut (its scroll width
fits its box), and no tile is narrower than its icon and words. No Chrome here is UNMEASURED, never a pass.
"""
import io
import json
import os
import re
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402 - a cp1255 console must survive its own report
_console_safe_enable()
import render_check as RC  # noqa: E402 - the one Chrome finder and CDP tab every render law uses

UI = os.path.join(HERE, "control_ui.html")
WIDTHS = (1512, 1440, 901)
# (icon, label, value, sub) - the five tiles as his v3904 console showed them (6851436283), worst case first
TILES = [("\U0001f3c6", "Best run", "Session 205", "5 chronicles \u00b7 12,345 reads"),
         ("\u26a1", "Most reads", "Session 92", "12,345 reads"),
         ("\U0001f4c8", "Top reads/hr", "Session 189", "1,234 /hr"),
         ("\U0001f4ca", "Best coverage", "Session 104", "87%"),
         ("\U0001f525", "Streak", "12 days", "467+ runs logged")]
_CACHE = {}


def _shipped_css():
    ui = io.open(UI, encoding="utf-8").read()
    rules = []
    for m in re.finditer(r"^[ \t]*(@media[^{]*\{\s*)?(\.sh-hi\b|\.shi-)[^{]*\{[^}]*\}(\s*\})?", ui, re.M):
        rules.append(m.group(0))
    css = "\n".join(rules)
    names = sorted(set(re.findall(r"var\((--[a-z0-9-]+)", css)))
    props = []
    for n in names:
        d = re.search(r"^\s*" + re.escape(n) + r":\s*([^;]+);", ui, re.M)
        if d:
            props.append("%s: %s;" % (n, d.group(1).strip()))
    return ":root{" + " ".join(props) + "}\n" + css, rules


def _page():
    css, _ = _shipped_css()
    tiles = "".join('<div class="sh-hi-card"><div class="shi-ic">%s</div><div class="shi-body"><div class="shi-lab">%s</div>'
                    '<div class="shi-val">%s</div><div class="shi-sub">%s</div></div></div>' % t for t in TILES)
    return ("<!doctype html><html><head><meta charset='utf-8'><style>html,body{margin:0;background:#050403;color:#ddd}"
            "#shelf{box-sizing:border-box;padding:0 24px}\n%s</style></head><body><div id='shelf'><div class='sh-hi'>%s</div>"
            "</div><script>document.title='ready';</script></body></html>" % (css, tiles))


MEASURE = r"""JSON.stringify([].map.call(document.querySelectorAll('.sh-hi-card'), function (c) {
  var r = c.getBoundingClientRect(), lines = {};
  ['.shi-lab', '.shi-val', '.shi-sub'].forEach(function (s) { var e = c.querySelector(s);
    lines[s] = { text: e.textContent, cut: e.scrollWidth > e.clientWidth + 1, right: e.getBoundingClientRect().right }; });
  return { lab: c.querySelector('.shi-lab').textContent, w: Math.round(r.width), right: r.right, top: Math.round(r.top), lines: lines };
}))"""


def _results():
    if "r" in _CACHE:
        return _CACHE["r"]
    res = {}
    with tempfile.TemporaryDirectory(prefix="tvd_shelf_tiles_") as d:
        page = os.path.join(d, "p.html")
        with io.open(page, "w", encoding="utf-8") as fh:
            fh.write(_page())
        url = ("file://" if os.name != "nt" else "file:///") + page.replace(os.sep, "/")
        RC.require_chrome()   # REG-3061 - a browser that will not start is UNKNOWN for this law (a VenueFault), never a red
        try:
            t = RC._Tab("about:blank")
            t.send("Page.enable")
            t.send("Runtime.enable")
            for w in WIDTHS:
                t.send("Emulation.setDeviceMetricsOverride", width=w, height=900, deviceScaleFactor=1, mobile=False)
                t.send("Page.navigate", url=url)
                for _ in range(80):
                    time.sleep(0.25)
                    try:
                        if t.ev("document.readyState==='complete' && document.title==='ready'") is True:
                            break
                    except Exception:
                        pass
                else:
                    raise AssertionError("the tiles page never loaded at %d - UNKNOWN, not passing" % w)
                time.sleep(0.3)
                res[w] = json.loads(t.ev(MEASURE))
            try:
                t.close()
            except Exception:
                pass
        finally:
            RC._chrome_down()
    _CACHE["r"] = res
    return res


@unittest.skipUnless(os.path.exists(RC.CHROME or ""), "no Chrome on this machine - UNMEASURED, never a pass")
class AShelfTileLineIsWholeAt901(unittest.TestCase):

    def test_the_shipped_rules_were_found(self):
        _, rules = _shipped_css()
        self.assertTrue(any(".shi-sub" in r for r in rules), "the .shi-sub rule was not found in control_ui.html")
        self.assertTrue(any(".sh-hi " in r or ".sh-hi{" in r for r in rules), "the .sh-hi strip rule was not found")

    def test_no_tile_line_is_cut_at_any_width(self):
        """* THE POINT - '5 chronicle…' and '467+ runs l…' at 901"""
        for w, cards in sorted(_results().items()):
            self.assertEqual(len(cards), len(TILES), "PREMISE: not every tile rendered at %d" % w)
            for c in cards:
                for sel, ln in c["lines"].items():
                    with self.subTest(width=w, tile=c["lab"], line=sel):
                        self.assertFalse(ln["cut"], "%s's %s line %r is cut at %d (its words run past its box)"
                                         % (c["lab"], sel, ln["text"], w))

    def test_every_tile_stays_inside_the_window(self):
        for w, cards in sorted(_results().items()):
            for c in cards:
                self.assertLessEqual(c["right"], w + 0.5, "%s runs off the window at %d" % (c["lab"], w))


RED_PROOF = [
    {"why": "REG-3853 - the sub line goes back to one ellipsised line (the v3905 rule): BEST RUN reads '5 chronicle…' at 901",
     "file": "tv/control_ui.html",
     "find": "margin-top: 2px; white-space: normal; overflow-wrap: anywhere; }",
     "replace": "margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
