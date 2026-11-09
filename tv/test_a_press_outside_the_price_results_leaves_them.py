# -*- coding: utf-8 -*-
"""v3892 (#191, REG-3537) - A PRESS OUTSIDE THE PRICE-SEARCH RESULTS LEAVES THEM.

His rule: every popup uses the same close; a click outside the top layer peels it.
MEASURED: REG-3531 painted `#d2jsp-price-x` on the results, and only that button (or emptying
the field) ran `priceSearchIdle`. A press elsewhere on the page left the cards up.
`_tvOutsidePrice` now sees the exit button as "results are showing" and, on a pointerdown
outside the results, the search field and the search form, clears the field and runs the same
idle the ✕ already runs. A press on the results, the field or the form is left alone.
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
        self.assertIn("priceSearchIdle()", body)

    def test_a_press_on_the_field_or_form_is_not_outside(self):
        body = _fn(_page())
        self.assertIn("if (q && (t === q || (q.contains && q.contains(t)))) return '';", body)
        self.assertIn("if (form && form.contains(t)) return '';", body)

    def test_the_listener_is_a_capturing_pointerdown(self):
        src = _page()
        self.assertIn("document.addEventListener('pointerdown', function(e){ _tvOutsidePrice(e); }, true);", src)


RED_PROOF = [
    {"why": "v3892 (#191, REG-3537) - a press outside the price results no longer leaves them",
     "file": "bible.html",
     "find": "  if (q) q.value = '';\n  if (typeof priceSearchIdle === 'function') priceSearchIdle();\n  return 'd2jsp';\n",
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
