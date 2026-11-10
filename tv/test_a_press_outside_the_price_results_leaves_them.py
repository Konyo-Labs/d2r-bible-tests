# -*- coding: utf-8 -*-
"""v3892 / v3894 (#191, REG-3537) - A PRESS OUTSIDE THE PRICE-SEARCH RESULTS LEAVES THEM.

His rule: every popup uses the same close; a click outside the top layer peels it.
MEASURED: REG-3531 painted `#d2jsp-price-x` on the results, and only that button (or emptying
the field) ran `priceSearchIdle`. A press elsewhere on the page left the cards up.
`_tvOutsidePrice` now sees the exit button as "results are showing" and, on a pointerdown
outside the results, the search field and the search form, clears the field and runs the same
idle the ✕ already runs. A press on the results, the field or the form is left alone.

Live v3893 still missed the idle: `_tvOutsidePrice` sits at page scope and called
`priceSearchIdle` only when it was a global, but the function is local to the search
IIFE and published as `window._d2jspPriceSearchIdle`. The closer must call that hook,
not a bare undefined global. RED_PROOF below.
"""
import io
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

PAGE = os.path.join(ROOT, "bible.html")


def _page():
    with io.open(PAGE, encoding="utf-8") as fh:
        return fh.read()


def _fn(src):
    i = src.index("function _tvOutsidePrice(e){")
    return src[i:src.index("window._tvOutsidePrice = _tvOutsidePrice;", i)]


class APressOutsideThePriceResultsLeavesThem(unittest.TestCase):

    def test_results_with_an_exit_close_on_an_outside_press(self):
        body = _fn(_page())
        self.assertIn("getElementById('d2jsp-price-out')", body)
        self.assertIn("querySelector('#d2jsp-price-x')", body)
        self.assertIn("out.contains(t)", body)
        self.assertIn("getElementById('d2jsp-price-q')", body)
        self.assertIn("getElementById('d2jsp-price-form')", body)
        self.assertIn("q.value = ''", body)
        self.assertIn("window._d2jspPriceSearchIdle", body)

    def test_the_closer_is_the_window_hook_not_an_undefined_global(self):
        """priceSearchIdle is local; typeof priceSearchIdle at page scope is undefined."""
        src = _page()
        body = _fn(src)
        self.assertIn("window._d2jspPriceSearchIdle = priceSearchIdle;", src)
        self.assertIn("window._d2jspPriceSearchIdle", body)
        self.assertNotIn("typeof priceSearchIdle === 'function'", body)
        stripped = body.replace("window._d2jspPriceSearchIdle", "")
        self.assertNotIn("priceSearchIdle()", stripped)
        self.assertNotIn("typeof priceSearchIdle", stripped)

    def test_an_undefined_global_idle_still_closes(self):
        """REG-3537 - when the bare global is missing, the window hook still runs."""
        body = _fn(_page())
        script = (
            "var called = 0;\n"
            "var window = { _d2jspPriceSearchIdle: function(){ called += 1; } };\n"
            "var document = {\n"
            "  getElementById: function(id){\n"
            "    if (id === 'd2jsp-price-out') {\n"
            "      return { querySelector: function(s){ return s === '#d2jsp-price-x' ? {} : null; },\n"
            "               contains: function(){ return false; } };\n"
            "    }\n"
            "    if (id === 'd2jsp-price-q') {\n"
            "      return { value: 'foo', contains: function(){ return false; } };\n"
            "    }\n"
            "    if (id === 'd2jsp-price-form') {\n"
            "      return { contains: function(){ return false; } };\n"
            "    }\n"
            "    return null;\n"
            "  }\n"
            "};\n"
            + body + "\n"
            "var ev = { button: 0, target: { closest: function(){ return true; } } };\n"
            "var got = _tvOutsidePrice(ev);\n"
            "if (got !== 'd2jsp') { console.error('leave=' + got); process.exit(2); }\n"
            "if (called !== 1) { console.error('called=' + called); process.exit(3); }\n"
        )
        path = None
        try:
            fd, path = tempfile.mkstemp(suffix=".js", prefix="reg-3537-")
            os.write(fd, script.encode("utf-8"))
            os.close(fd)
            proc = subprocess.run(["node", path], capture_output=True, text=True)
        finally:
            if path and os.path.isfile(path):
                os.remove(path)
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout or "node failed")

    def test_a_press_on_the_field_or_form_is_not_outside(self):
        body = _fn(_page())
        self.assertIn("if (q && (t === q || (q.contains && q.contains(t)))) return '';", body)
        self.assertIn("if (form && form.contains(t)) return '';", body)

    def test_the_listener_is_a_capturing_pointerdown(self):
        src = _page()
        self.assertIn("document.addEventListener('pointerdown', function(e){ _tvOutsidePrice(e); }, true);", src)


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            with io.open(os.path.join(ROOT, p["file"]), encoding="utf-8") as fh:
                blob = fh.read()
            self.assertEqual(blob.count(p["find"]), p["matches"], p["why"])


RED_PROOF = [
    {"why": "v3892 (#191, REG-3537) - a press outside the price results no longer leaves them",
     "file": "bible.html",
     "find": "  if (q) q.value = '';\n  /* REG-3537 - priceSearchIdle is local to the search IIFE; the published hook is on window. */\n  if (typeof window._d2jspPriceSearchIdle === 'function') window._d2jspPriceSearchIdle();\n  return 'd2jsp';\n",
     "replace": "  return '';\n",
     "matches": 1},
    {"why": "v3892 (#191, REG-3537) - a press on the search field is treated as outside and wipes the query",
     "file": "bible.html",
     "find": "  if (q && (t === q || (q.contains && q.contains(t)))) return '';\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
