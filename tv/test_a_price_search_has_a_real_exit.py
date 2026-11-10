# -*- coding: utf-8 -*-
"""v3891 (#191, REG-3531) - A PRICE SEARCH'S RESULTS HAVE A REAL EXIT.

His rule: D2JSP results need a way out. REG-3526 already empties them when the field's native clear
runs; the results themselves had no close. `priceSearchExit` now paints `#d2jsp-price-x` (the same
`gic-close-btn` the other cards use) on the results; clicking it clears the field and runs
`priceSearchIdle` so the idle line comes back and an in-flight answer is dropped. The painted
search line (`out.innerHTML = _first + '<div>'`) is unchanged. RED_PROOF below.
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

PAGE = os.path.join(ROOT, "bible.html")
NODE = shutil.which("node")


def _page():
    with io.open(PAGE, encoding="utf-8") as fh:
        return fh.read()


def _fn(src, name):
    head = "function %s" % name
    i = src.index(head)
    start = src.index("{", i)
    depth = 0
    for k in range(start, len(src)):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
    raise AssertionError("%s was not closed" % name)


class APriceSearchHasARealExit(unittest.TestCase):

    def test_results_paint_an_exit_and_the_search_line_stays(self):
        src = _page()
        self.assertIn("      out.innerHTML = _first + '<div>' + esc(d2jspSearchLine(j, sim, parsed)) + '</div>'", src,
                      "the pinned search-line paint moved - this law must not rewrite it")
        done_bit = src[src.index("if (items.length > 1) out.innerHTML = htmls.join('');"):
                       src.index("if (items.length > 1) out.innerHTML = htmls.join('');") + 220]
        self.assertIn("if (typeof priceSearchExit === 'function') priceSearchExit(out);", done_bit,
                      "the results are painted without an exit")
        exit_fn = _fn(src, "priceSearchExit(out){")
        self.assertIn("d2jsp-price-x", exit_fn)
        self.assertIn("gic-close-btn", exit_fn)

    def test_the_exit_clears_the_field_and_restores_the_idle_line(self):
        src = _page()
        i = src.index("window._d2jspPriceClick = function(ev){")
        click = src[i:src.index("function d2jspRevealAboveDock(el){", i)]
        self.assertIn("t.id === 'd2jsp-price-x'", click)
        i = click.index("t.id === 'd2jsp-price-x'")
        bit = click[i:click.index("if (t.id !== 'd2jsp-price-advanced')", i)]
        self.assertIn("q.value = ''", bit)
        self.assertIn("priceSearchIdle()", bit)
        if not NODE:
            self.skipTest("no node - the exit painter is not driven here (UNMEASURED)")
        prog = _fn(src, "priceSearchExit(out){") + """
var out = { innerHTML: '<section data-d2jsp-search-item="shako">LINE</section>' };
if (typeof priceSearchExit === 'function') priceSearchExit(out);
process.stdout.write(JSON.stringify({ html: out.innerHTML }));
"""
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout)
        self.assertIn('id="d2jsp-price-x"', got["html"])
        self.assertIn('gic-close-btn', got["html"])
        self.assertIn('data-d2jsp-search-item="shako"', got["html"], "the exit wiped the results instead of sitting on them")
        self.assertLess(got["html"].index('id="d2jsp-price-x"'),
                        got["html"].index('data-d2jsp-search-item="shako"'))


RED_PROOF = [
    {"why": "v3891 (#191, REG-3531) - the results paint without an exit again",
     "file": "bible.html",
     "find": "      if (items.length > 1) out.innerHTML = htmls.join('');   /* v3891 (#192) - one card (one section) each */\n      if (typeof priceSearchExit === 'function') priceSearchExit(out);\n",
     "replace": "      if (items.length > 1) out.innerHTML = htmls.join('');   /* v3891 (#192) - one card (one section) each */\n",
     "matches": 1},
    {"why": "v3891 (#191, REG-3531) - clicking the results exit does not leave them",
     "file": "bible.html",
     "find": "    if (t.id === 'd2jsp-price-x') {\n      if (ev.preventDefault) ev.preventDefault();\n      var q = document.getElementById('d2jsp-price-q');\n      if (q) q.value = '';\n      priceSearchIdle();\n      return true;\n    }\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
