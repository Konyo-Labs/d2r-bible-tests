# -*- coding: utf-8 -*-
"""v3891 (#192, REG-3525 / REG-3526) - A PRICE SEARCH SPLITS COMMA-SEPARATED ITEMS, AND ITS CLEAR EMPTIES THE RESULTS.

His rule: typing "shako, jmod" is two searches, one card each; clearing the field (the native search x, or emptying it)
empties the results too, so an in-flight answer cannot repaint what he just cleared.

MEASURED: `d2jspParseSearch` is one item (it never splits on a comma); the field is already `type=search`, so the
browser draws a clear control; `priceSearch` handed the whole typed string to that one-item parser, and nothing
listened for the field going empty. Now `d2jspSearchChunks` splits on commas first, `priceSearch` asks once per
chunk and paints one section each (in the order he typed), and emptying the field bumps `searchGen` (so a late
answer is dropped) and restores the idle line. RED_PROOF below.
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


def _price_search(src):
    a = src.index("  function priceSearch(){")
    depth = 0
    start = src.index("{", a)
    for k in range(start, len(src)):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                return src[a:k + 1]
    raise AssertionError("priceSearch was not closed")


class APriceSearchSplitsItems(unittest.TestCase):

    def test_a_comma_list_is_one_chunk_per_item(self):
        src = _page()
        body = _fn(src, "d2jspSearchChunks(text) {")
        self.assertIn(".split(',')", body, "d2jspSearchChunks no longer splits on a comma")
        parse = _fn(src, "d2jspParseSearch(text) {")
        self.assertNotIn(".split(',')", parse, "d2jspParseSearch started splitting - it is one item")
        if not NODE:
            self.skipTest("no node - the chunker is not driven here (UNMEASURED)")
        prog = body + """
process.stdout.write(JSON.stringify({
  two: d2jspSearchChunks('shako, jmod'),
  spaces: d2jspSearchChunks(' shako ,  jmod '),
  empty: d2jspSearchChunks(''),
  holes: d2jspSearchChunks('shako,, jmod'),
  one: d2jspSearchChunks('shako')
}));
"""
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout)
        self.assertEqual(got["two"], ["shako", "jmod"])
        self.assertEqual(got["spaces"], ["shako", "jmod"])
        self.assertEqual(got["empty"], [])
        self.assertEqual(got["holes"], ["shako", "jmod"])
        self.assertEqual(got["one"], ["shako"])

    def test_price_search_asks_each_chunk_and_paints_one_section_each(self):
        """ "shako, jmod" is two quote reads and two painted sections, in the order he typed """
        if not NODE:
            self.skipTest("no node - the price search is not driven here (UNMEASURED)")
        src = _page()
        body = _fn(src, "d2jspSearchChunks(text) {") + "\n" + _price_search(src)
        prog = (
            "var asked = [], els = {'d2jsp-price-q': {value: 'shako, jmod'}, "
            "'d2jsp-price-out': {textContent: '', innerHTML: ''}};\n"
            "var document = {getElementById: function(id){ return els[id] || null; }};\n"
            "var searchGen = 0;\n"
            "function esc(x){ return String(x); }\n"
            "function d2jspParseSearch(v){ return {item: String(v || '').trim(), roll: null}; }\n"
            "function d2jspSimilarPrice(){ return null; }\n"
            "function d2jspBackendHtml(){ return ''; }\n"
            "function d2jspTierCardsHtml(){ return ''; }\n"
            "function d2jspEvidenceHtml(){ return ''; }\n"
            "function d2jspDatabaseButton(){ return ''; }\n"
            "function d2jspSearchLine(q, sim, parsed){ return 'LINE:' + (parsed && parsed.item) + ':' + q.reason; }\n"
            "function fetch(u){ asked.push(u); return Promise.resolve({json: function(){ "
            "return {reason: 'unread', fg: null, db: {normal: {fg: 15, n: 1}}}; }}); }\n"
            + body + "\n"
            "priceSearch();\n"
            "setTimeout(function(){ process.stdout.write(JSON.stringify({"
            "asked: asked, html: els['d2jsp-price-out'].innerHTML})); }, 50);\n")
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout)
        items = [u.split("item=", 1)[-1] for u in got["asked"]]
        self.assertEqual(items, ["shako", "jmod"], "the search did not ask one quote per typed item: %s" % got["asked"])
        self.assertIn('data-d2jsp-search-item="shako"', got["html"], "shako has no card of its own")
        self.assertIn('data-d2jsp-search-item="jmod"', got["html"], "jmod has no card of its own")
        self.assertLess(got["html"].index('data-d2jsp-search-item="shako"'),
                        got["html"].index('data-d2jsp-search-item="jmod"'),
                        "the cards are not in the order he typed")
        self.assertIn("LINE:shako:unread", got["html"])
        self.assertIn("LINE:jmod:unread", got["html"])


class APriceSearchClearEmptiesTheResults(unittest.TestCase):

    def test_emptying_the_field_clears_the_results_and_drops_a_late_answer(self):
        src = _page()
        q = src[src.index('id="d2jsp-price-q"'):src.index('id="d2jsp-price-q"') + 120]
        self.assertIn('type="search"', q, "the field is not type=search, so the browser draws no native clear")
        idle = _fn(src, "priceSearchIdle(){")
        self.assertIn("searchGen++;", idle, "clearing the field does not drop an in-flight answer")
        self.assertIn("out.textContent = (typeof d2jspReadSay === 'function') ? d2jspReadSay()", idle,
                      "clearing the field does not restore the idle line")
        maybe = _fn(src, "priceSearchMaybeIdle(ev){")
        self.assertIn("t.id === 'd2jsp-price-q'", maybe)
        self.assertIn("!String(t.value || '').trim()", maybe)
        self.assertIn("priceSearchIdle()", maybe)
        self.assertIn("document.addEventListener('input', priceSearchMaybeIdle);", src)
        self.assertIn("document.addEventListener('search', priceSearchMaybeIdle);", src)


RED_PROOF = [
    {"why": "v3891 (#192, REG-3525) - 'shako, jmod' is one search again",
     "file": "bible.html",
     "find": "  return String(text || '').split(',').map(function (s) { return s.replace(/\\s+/g, ' ').trim(); }).filter(Boolean);\n",
     "replace": "  return String(text || '').replace(/\\s+/g, ' ').trim() ? [String(text || '').replace(/\\s+/g, ' ').trim()] : [];\n",
     "matches": 1},
    {"why": "v3891 (#192, REG-3525) - two items paint as one card (the last to answer overwrites the first)",
     "file": "bible.html",
     "find": "      if (items.length > 1) out.innerHTML = htmls.join('');   /* v3891 (#192) - one card (one section) each */\n",
     "replace": "      /* v3891 sabotaged: two items no longer join into one card each */\n",
     "matches": 1},
    {"why": "v3891 (#192, REG-3526) - emptying the field leaves the last results on screen",
     "file": "bible.html",
     "find": "    searchGen++;\n    var out = document.getElementById('d2jsp-price-out');\n    if (out) out.textContent = (typeof d2jspReadSay === 'function') ? d2jspReadSay() : 'Reads d2jsp posts dated 2026 or later, board 268 only. Nothing is posted.';\n",
     "replace": "    var out = document.getElementById('d2jsp-price-out');\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
