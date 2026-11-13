# -*- coding: utf-8 -*-
"""Job E item 5 - card #222 (his words: "when clicking advanced for d2jsp it collapses and decollapses but it doesnt
properly show this like when opened or closed").

Before: a plain "Advanced" pill whose only state was the panel appearing 8px below it - nothing on the control said open
or shut. Now the control is a drawer header in the Shelf backdoor's style (control_ui.html #th-shelfov .sh-backdoor: the
same gold hairline frame, 12px corners and dark glass; a serif gold-bright title; a quiet hint), and it SHOWS ITS STATE:
  * a chevron that turns (rotate 90deg when open);
  * words that change - "Show advanced" shut, "Hide advanced" open - both in the markup, aria-expanded picks one, so the
    click, Escape and "Show the database" (every path that opens or shuts it) all say it without a second writer;
  * aria-expanded on the control, aria-controls naming the panel;
  * open, the header squares its foot and the panel joins beneath it (no gap, no top border, the bottom corners round).
A press on the chevron, the words or the hint is a press on the header. The console's pointer is the page's own (no
cursor here) and only defined tokens are used (the --warn trap). Pixels: GrokBot's scratch console at 1440 / 1120 / 901
(REPORT.md). Pure python over the shipped page + the real click handler in node. RED_PROOF below (hand-proven).
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

NODE = shutil.which("node")
DOOR = "#tab-d2jsp #d2jsp-price-advanced"


def _read(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _css(page):
    return re.sub(r"/\*[\s\S]*?\*/", " ", page)


def _rule(css, sel):
    m = re.search(re.escape(sel) + r"\s*\{([^}]*)\}", css)
    return m.group(1) if m else None


class TheControlShowsItsState(unittest.TestCase):

    def setUp(self):
        self.page = _read("bible.html")
        self.css = _css(self.page)

    def test_the_markup_carries_chevron_both_words_and_aria(self):
        a = self.page.index('id="d2jsp-price-advanced"')
        btn = self.page[self.page.rindex("<button", 0, a):self.page.index("</button>", a) + 9]
        self.assertIn('aria-controls="d2jsp-price-backend"', btn)
        self.assertIn('aria-expanded="false"', btn, "the control does not start saying it is shut")
        self.assertIn('<span class="d2jsp-adv-chev" aria-hidden="true">', btn, "no chevron")
        self.assertIn('<span class="d2jsp-adv-show">Show advanced</span>', btn)
        self.assertIn('<span class="d2jsp-adv-hide">Hide advanced</span>', btn)
        after = self.page[self.page.index("</button>", a) + 9:][:80]
        self.assertTrue(after.lstrip().startswith('<div id="d2jsp-price-backend" class="d2jsp-backend" hidden>'),
                        "the panel is not the header's next sibling, so it cannot join it: %r" % after[:60])

    def test_the_chevron_turns_and_the_words_swap_on_aria_expanded(self):
        turn = _rule(self.css, DOOR + '[aria-expanded="true"] .d2jsp-adv-chev')
        self.assertTrue(turn and "rotate(90deg)" in turn, "the chevron never turns")
        self.assertIn("transition:transform", _rule(self.css, "#tab-d2jsp .d2jsp-adv-chev") or "")
        hide = _rule(self.css, DOOR + " .d2jsp-adv-hide," + DOOR + '[aria-expanded="true"] .d2jsp-adv-show')
        self.assertTrue(hide and "display:none" in hide, "both words show at once, or neither swaps")
        show = _rule(self.css, DOOR + '[aria-expanded="true"] .d2jsp-adv-hide')
        self.assertTrue(show and "display:inline" in show, "'Hide advanced' never shows when it is open")

    def test_open_the_panel_joins_its_header(self):
        head = _rule(self.css, DOOR + '[aria-expanded="true"]') or ""
        self.assertIn("border-radius:12px 12px 0 0", head, "open, the header keeps its round foot - nothing joins")
        join = _rule(self.css, DOOR + '[aria-expanded="true"] + .d2jsp-backend') or ""
        for want in ("margin-top:-8px", "border-top:0", "border-radius:0 0 12px 12px"):
            self.assertIn(want, join, "the open panel is not joined to its header (%s)" % want)

    def test_it_is_drawn_in_the_shelf_backdoors_style(self):
        ui = _css(_read("tv/control_ui.html"))
        shelf = re.search(r"#th-shelfov \.sh-backdoor \{([^}]*)\}", ui).group(1)
        door = _rule(self.css, DOOR) or ""
        for part in ("rgba(212,168,71,.28)", "rgba(13,10,6,.35)"):
            self.assertIn(part, shelf.replace(" ", ""), "PREMISE: the Shelf backdoor drawer changed its look")
            self.assertIn(part, door, "Advanced is not in the Shelf backdoor's frame (%s)" % part)
        self.assertIn("border-radius:12px", door)
        self.assertIn("color:var(--gold-bright)", door)

    def test_no_cursor_and_only_defined_tokens(self):
        a = self.page.index("/* Job E item 5 (card #222)")
        block = self.page[a:self.page.index("@media (prefers-reduced-motion: reduce){#tab-d2jsp .d2jsp-adv-chev", a)]
        self.assertNotIn("cursor", _css(block), "the Advanced header sets its own cursor - the console pointer is the page's")
        used = sorted(set(re.findall(r"var\(\s*(--[a-zA-Z0-9-]+)", block)))
        self.assertTrue(used)
        undefined = [t for t in used if not re.search(re.escape(t) + r"\s*:", self.css)]
        self.assertEqual(undefined, [], "an undefined token (the --warn trap): %r" % undefined)

    def test_every_path_that_opens_or_shuts_it_sets_aria_expanded(self):
        desk = self.page[self.page.index("  window._d2jspPriceClick = function(ev){"):self.page.index("  function d2jspShotRead(name) {")]
        flips = len(re.findall(r"panel\.hidden = ", desk))
        says = len(re.findall(r"setAttribute\('aria-expanded'", desk))
        self.assertEqual(flips, 3, "PREMISE: the toggle, Escape and Show the database are the three paths")
        self.assertEqual(says, flips, "a path opens or shuts Advanced without saying so")


@unittest.skipUnless(NODE, "no node - the click handler is not driven here (UNMEASURED)")
class APressOnItsWordsIsAPressOnTheHeader(unittest.TestCase):

    def test_pressing_the_words_opens_and_says_open(self):
        page = _read("bible.html")
        a = page.index("  window._d2jspPriceClick = function(ev){\n")
        tail = "  window._d2jspRevealAboveDock = d2jspRevealAboveDock;\n"
        b = page.index(tail) + len(tail)
        js = r"""
function El(id){ this.id = id; this.attrs = {}; this.hidden = true; }
El.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
El.prototype.getAttribute = function(k){ return this.attrs[k]; };
El.prototype.getBoundingClientRect = function(){ return {top: 0, bottom: 10}; };
var door = new El('d2jsp-price-advanced'), panel = new El('d2jsp-price-backend');
door.closest = function(sel){ return sel === '#d2jsp-price-advanced' ? door : null; };
var word = {id: '', closest: function(sel){ return sel === '#d2jsp-price-advanced' ? door : null; }};
var window = {innerHeight: 900, scrollBy: function(){}};
var document = {getElementById: function(id){ return id === 'd2jsp-price-backend' ? panel : (id === 'd2jsp-price-advanced' ? door : null); },
                querySelector: function(){ return null; }, addEventListener: function(){}};
function priceSearch(){} function d2jspLoadDatabase(){} function priceSearchIdle(){}
""" + page[a:b] + r"""
var r1 = window._d2jspPriceClick({target: word});
var open = {handled: r1, hidden: panel.hidden, exp: door.attrs['aria-expanded']};
window._d2jspPriceClick({target: word});
process.stdout.write(JSON.stringify({open: open, shut: {hidden: panel.hidden, exp: door.attrs['aria-expanded']}}));
"""
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout)
        self.assertEqual(got["open"], {"handled": True, "hidden": False, "exp": "true"},
                         "a press on the header's words did not open Advanced and say so")
        self.assertEqual(got["shut"], {"hidden": True, "exp": "false"})


RED_PROOF = [
    {"why": "#222 - the chevron never turns",
     "file": "bible.html",
     "find": "#tab-d2jsp #d2jsp-price-advanced[aria-expanded=\"true\"] .d2jsp-adv-chev{transform:rotate(90deg)}",
     "replace": "#tab-d2jsp #d2jsp-price-advanced[aria-expanded=\"true\"] .d2jsp-adv-chev{}",
     "matches": 1},
    {"why": "#222 - the words never change (Show advanced stays when it is open)",
     "file": "bible.html",
     "find": "#tab-d2jsp #d2jsp-price-advanced[aria-expanded=\"true\"] .d2jsp-adv-hide{display:inline}",
     "replace": "",
     "matches": 1},
    {"why": "#222 - the open panel floats 8px under its header again (not joined)",
     "file": "bible.html",
     "find": "+ .d2jsp-backend{margin-top:-8px;border-color:rgba(212,168,71,.28);border-top:0;",
     "replace": "+ .d2jsp-backend{border-color:rgba(212,168,71,.28);",
     "matches": 1},
    {"why": "#222 - a press on the header's words does nothing (the span has no id)",
     "file": "bible.html",
     "find": "    if (_adv) t = _adv;\n",
     "replace": "",
     "matches": 1},
    {"why": "#222 - the toggle opens the panel without saying so (aria-expanded stays false)",
     "file": "bible.html",
     "find": "    t.setAttribute('aria-expanded', panel.hidden ? 'false' : 'true');\n",
     "replace": "",
     "matches": 1},
    {"why": "#222 - the control is a plain pill again, not the Shelf backdoor's drawer header",
     "file": "bible.html",
     "find": "padding:9px 13px;border:1px solid rgba(212,168,71,.28);border-radius:12px;background:rgba(13,10,6,.35);color:var(--gold-bright)",
     "replace": "padding:9px 13px",
     "matches": 1},
    {"why": "#222 - the pointer ban: the header sets its own cursor",
     "file": "bible.html",
     "find": "#tab-d2jsp #d2jsp-price-advanced:hover{border-color:rgba(240,192,96,.55)}",
     "replace": "#tab-d2jsp #d2jsp-price-advanced:hover{border-color:rgba(240,192,96,.55);cursor:pointer}",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
