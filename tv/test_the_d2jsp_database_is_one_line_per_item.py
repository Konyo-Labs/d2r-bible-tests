# -*- coding: utf-8 -*-
"""v3881 (REG-3390) - HIS D2JSP ADVANCED ASK: ITS OWN SCROLL PANEL, A STICKY FIND + SORT, GROUPS, ONE LINE PER ITEM, THE RULE
SAID ONCE, AND "Fresh. fresh" SAID ONCE.

Before: "Show the database" printed every item in full - its tier lines, "Fresh. fresh" (the server's reason for a fresh price
IS the word fresh), the weighing rule AGAIN for every item, and the whole post table - one under another, unbounded. His words
(v3878 pass, 17:35): "D2JSP Advanced = own scroll panel, sticky search+sort, groups, one collapsed line per item, rule said
once, 'Fresh. fresh' -> 'fresh', SOURCE = nickname" (the nickname is REG-3379).

The law drives the page's OWN functions (cut from bible.html) through node, with a small fake DOM for Find and Sort.
RED_PROOF below. [[visual-regression-detector]] - the pixels are looked at separately (headless render + the Grok CLI).
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

NODE = shutil.which("node") or shutil.which("nodejs")
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
FUNCS = ["d2jspEscText", "d2jspFgText", "d2jspSeenText", "d2jspPriceSyncLine", "d2jspTierSay", "d2jspDatabaseButton",
         "d2jspBackendHtml", "d2jspBatchHtml", "d2jspDbArrange",
         "d2jspItemKind", "d2jspItemArtHtml"]   # v3884 (#130) - the row's colour and art


def _fn(src, name):
    start = "function %s(" % name
    if src.count(start) != 1:
        raise AssertionError("%s moved (%d) - re-point this law" % (name, src.count(start)))
    i = src.index(start)
    return src[i:src.index("\n}\n", i) + 3]


def _proof(n):
    return {"halfLifeDays": 30, "agree": 0.2, "posts": [{"day": "2026-11-0%d" % (k + 1), "fg": 40 + k, "tier": "normal",
                                                       "ageDays": k, "w": 1, "band": "in", "src": "Konyo",
                                                       "link": "https://forums.d2jsp.org/topic.php?t=%d" % k}
                                                      for k in range(n)]}


VIEW = {"items": [
    {"item": "shako", "normal": {"fg": 40, "n": 15}, "perfect": {"fg": 80, "n": 2}, "stale": False, "why": "fresh",
     "proof": _proof(3)},
    {"item": "Arachnid Mesh", "normal": {"fg": 120, "n": 4}, "perfect": {"fg": None}, "stale": True,
     "why": "read more than 3 days ago", "proof": _proof(1)},
    {"item": "jah", "normal": {"fg": 300, "n": 9}, "perfect": {"fg": None}, "stale": False, "why": "fresh", "proof": _proof(5)},
    {"item": "anni", "normal": {"fg": None}, "perfect": {"fg": None}, "proof": {"halfLifeDays": 30, "agree": 0.2, "posts": []}},
]}

FAKE_DOM = r"""
function El(attrs){ this.a = attrs || {}; this.hidden = false; this.kids = []; this.value = ''; }
El.prototype.getAttribute = function(k){ return this.a[k] == null ? null : String(this.a[k]); };
El.prototype.appendChild = function(c){ var i = this.kids.indexOf(c); if (i >= 0) this.kids.splice(i, 1); this.kids.push(c); return c; };
El.prototype.querySelectorAll = function(sel){
  var out = [];
  (function walk(n){ n.kids.forEach(function(k){ if (k.a[sel.replace(/[\[\]]/g, '')] != null) out.push(k); walk(k); }); })(this);
  return out;
};
El.prototype.querySelector = function(sel){ return this.querySelectorAll(sel)[0] || null; };
function item(name, fg, posts){ return new El({'data-d2jsp-batch-item': name, 'data-name': name.toLowerCase(), 'data-fg': fg, 'data-posts': posts}); }
"""


def _node(js):
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError("node could not drive the page's functions: " + r.stderr[-600:])
    return json.loads(r.stdout)


def _render(view, board=False):
    """board=True gives the functions a stand-in for the board's item database (kind + art), as the page would"""
    src = io.open(BIBLE, encoding="utf-8").read()
    pre = ""
    if board:
        pre = ("var window = {artUrl: function(n){ return {'shako': 'art/shako.png', 'jah': 'art/jah.png'}[n] || null; },"
               " d2rResolveItem: function(n){ return n === 'shako' ? {kind: 'unique', canonical: 'Harlequin Crest'}"
               " : (n === 'Arachnid Mesh' ? {kind: 'unique', canonical: n} : {kind: 'unknown', canonical: null}); },"
               " _mtEntryFor: function(n){ return n === 'jah' ? {q: 'c'} : {q: null}; }};\n")
    js = pre + "\n".join(_fn(src, f) for f in FUNCS) + "\nprocess.stdout.write(JSON.stringify(d2jspBatchHtml(%s)));" % json.dumps(view)
    return _node(js)


def _cells(h):
    """each item row's three value cells, their text with the tags stripped -> [[normal, perfect, posts], ...]"""
    import re
    rows = re.findall(r'<summary>(.*?)</summary>', h, re.S)
    out = []
    for r in rows:
        cells = re.findall(r'<span class="d2jsp-db-c [^"]*">(.*?)</span></span>|<span class="d2jsp-db-c [^"]*">(.*?)(?=<span class="d2jsp-db-c|</span></summary>|$)', r, re.S)
        vals = [re.sub(r"<[^>]+>", "", a or b) for a, b in cells]
        out.append(vals)
    return out


def _arrange(q, key):
    src = io.open(BIBLE, encoding="utf-8").read()
    js = (_fn(src, "d2jspDbArrange") + FAKE_DOM + r"""
var root = new El({}), find = new El({'data-d2jsp-db-find': 1}), sort = new El({'data-d2jsp-db-sort': 1});
find.value = %s; sort.value = %s; root.kids.push(find, sort);
var g1 = new El({'data-d2jsp-db-group': 'fresh'}), g2 = new El({'data-d2jsp-db-group': 'stale'});
[item('shako', 40, 3), item('jah', 300, 5), item('Ber', 250, 9)].forEach(function(i){ g1.kids.push(i); });
[item('Arachnid Mesh', 120, 1)].forEach(function(i){ g2.kids.push(i); });
root.kids.push(g1, g2);
var shown = d2jspDbArrange(root);
process.stdout.write(JSON.stringify({shown: shown,
  g1: g1.kids.filter(function(k){ return !k.hidden; }).map(function(k){ return k.a['data-d2jsp-batch-item']; }),
  g2hidden: g2.hidden}));
""" % (json.dumps(q), json.dumps(key)))
    return _node(js)


@unittest.skipUnless(NODE, "node drives the page's own functions - UNMEASURED here, not a pass")
class TheDatabaseIsOneLinePerItem(unittest.TestCase):

    def test_the_rule_is_said_once_for_every_item(self):
        """* THE POINT (his 'rule said once'): one weighing rule above four items, none repeated inside them"""
        h = _render(VIEW)
        self.assertEqual(h.count("data-d2jsp-law"), 1, "the weighing rule is printed per item again")
        self.assertIn("Every item below: age half-life 30 days", h)

    def test_each_item_is_one_collapsed_line_in_its_group(self):
        h = _render(VIEW)
        self.assertEqual(h.count("<details class=\"d2jsp-db-item\""), 4)
        self.assertNotIn("<details class=\"d2jsp-db-item\" open", h, "an item opens expanded - not one line")
        self.assertIn('data-d2jsp-db-group="fresh"><h3>Fresh · 2</h3>', h)
        self.assertIn('data-d2jsp-db-group="stale"><h3>Stale · 1</h3>', h)
        self.assertIn('data-d2jsp-db-group="unknown"><h3>Freshness not known · 1</h3>', h)
        # v3884 (#130) - the row is a grid: the item, then three cells; their words stay (hidden labels) for a reader and here
        import re
        rows = dict((re.search(r'<span class="d2jsp-db-nm">([^<]*)</span>', r).group(1), re.sub(r"<[^>]+>", "", r))
                    for r in re.findall(r'<summary>(.*?)</summary>', h, re.S))
        self.assertIn(u"normal\u00a040\u00a0fg· perfect\u00a080\u00a0fg·\u00a03\u00a0posts", rows["shako"])
        self.assertIn(u"normal\u00a0not\u00a0priced· perfect\u00a0not\u00a0priced·\u00a00\u00a0posts", rows["anni"])

    def test_a_wrap_never_strands_a_middot(self):
        """the v3881 look at 390: 'Griffon's Eye normal 95 fg · perfect 160 fg' / '· 4 posts' - a line began with the middot.
        Every middot in an item's line is bound to the fact before it (a no-break space), so a wrap ends a line on it"""
        # v3884 (#130) - each fact is its OWN grid cell now, so no line can start with a middot; and a cell's value is one
        # unbreakable unit (no-break spaces only), so no wrap tears '160' from 'fg'
        h = _render(VIEW)
        import re
        cells = re.findall(r'<span class="d2jsp-db-c ([^"]*)">(.*?)(?=<span class="d2jsp-db-c |</summary>)', h, re.S)
        self.assertEqual(len(cells), 12, "four items, three cells each: %r" % [c[0] for c in cells])
        for cls, body in cells:
            val = re.sub(r'<span class="d2jsp-db-l">[^<]*</span>', "", body)
            val = re.sub(r"<[^>]+>", "", val)
            self.assertNotIn(" ", val, "a value a wrap can tear apart ('160' / 'fg'): %r" % val)

    def test_the_prices_stand_in_one_column_under_their_titles(self):
        """* v3884 (#130, his 11-08: "the prices should be more grid ... on the right ... in the same column so they are
        vertically aligned") - the header and every row share ONE grid; a group says its columns once"""
        h = _render(VIEW)
        self.assertEqual(h.count('<div class="d2jsp-db-head" aria-hidden="true"><span>item</span><span>normal</span>'
                                 '<span>perfect</span><span>posts</span></div>'), 3, "each group says its columns")
        css = io.open(BIBLE, encoding="utf-8").read()
        self.assertIn("#tab-d2jsp .d2jsp-db-item > summary,#tab-d2jsp .d2jsp-db-head{display:grid;grid-template-columns:"
                      "minmax(0,1fr) minmax(0,11ch) minmax(0,12ch) minmax(0,9ch);", css,
                      "the rows and the header no longer share one grid - the prices would not align")
        self.assertIn("#tab-d2jsp .d2jsp-db-item > summary > .d2jsp-db-k{display:contents}", css)

    def test_a_name_wears_its_kind_and_its_art(self):
        """v3884 (#130) - the item in its rarity's colour with its HD art (the board's hover card rides the art);
        an item the board cannot place claims no colour and draws no art"""
        h = _render(VIEW, board=True)
        self.assertIn('<span class="d2jsp-db-name d2jsp-q-unique"><span class="d2art-wrap d2jsp-iart xs" aria-label="shako">', h)
        self.assertIn('<span class="d2jsp-db-name d2jsp-q-unique"><span class="d2jsp-db-nm">Arachnid Mesh</span>', h,
                      "an item with no art drew a picture anyway")
        self.assertIn('<span class="d2jsp-db-name"><span class="d2jsp-db-nm">anni</span>', h, "an unplaced item claimed a colour")

    def test_its_own_scroll_panel_with_a_find_and_sort_bar(self):
        h = _render(VIEW)
        i, j = h.index('<div class="d2jsp-db-scroll" data-d2jsp-db-scroll>'), h.index('<div class="d2jsp-db-bar" data-d2jsp-db-bar>')
        self.assertLess(i, j, "the bar is not inside the scroll panel (it cannot stick to its top)")
        self.assertIn("data-d2jsp-db-find", h)
        self.assertIn("data-d2jsp-db-sort", h)
        css = io.open(BIBLE, encoding="utf-8").read()
        self.assertIn("#tab-d2jsp .d2jsp-db-scroll{max-height:min(62vh,560px);overflow:auto;", css)
        self.assertIn("#tab-d2jsp .d2jsp-db-bar{position:sticky;top:0;", css)

    def test_fresh_is_said_once(self):
        h = _render(VIEW)
        self.assertNotIn("Fresh. fresh", h)
        self.assertIn("<p data-d2jsp-fresh>Fresh.</p>", h)
        self.assertIn("<p data-d2jsp-fresh>Stale. read more than 3 days ago</p>", h, "a real reason is no longer said")

    def test_find_narrows_and_sort_orders(self):
        a = _arrange("", "fg")
        self.assertEqual(a["g1"], ["jah", "Ber", "shako"], "sort by price is not highest first")
        a = _arrange("", "name")
        self.assertEqual(a["g1"], ["Ber", "jah", "shako"])
        a = _arrange("SHA", "name")
        self.assertEqual((a["shown"], a["g1"], a["g2hidden"]), (1, ["shako"], True), "find did not narrow, or an empty group stayed")

    def test_baseline_one_item_view_still_carries_its_rule(self):
        """the single-item Advanced view (a price check) still says its own rule - only the database view says it once"""
        src = io.open(BIBLE, encoding="utf-8").read()
        js = "\n".join(_fn(src, f) for f in FUNCS[:7]) + "\nprocess.stdout.write(JSON.stringify(d2jspBackendHtml(%s, null, {})));" \
            % json.dumps(VIEW["items"][0])
        self.assertEqual(_node(js).count("data-d2jsp-law"), 1)


RED_PROOF = [
    {"why": "v3884 (#130) - the rows and the header stop sharing one grid: the prices drift out of their column",
     "file": "bible.html",
     "find": "#tab-d2jsp .d2jsp-db-item > summary,#tab-d2jsp .d2jsp-db-head{display:grid;",
     "replace": "#tab-d2jsp .d2jsp-db-head{display:grid;", "matches": 1},
    {"why": "v3884 (#130) - a group no longer says its columns",
     "file": "bible.html",
     "find": "      + '<div class=\"d2jsp-db-head\" aria-hidden=\"true\"><span>item</span><span>normal</span><span>perfect</span><span>posts</span></div>'\n",
     "replace": "", "matches": 1},
    {"why": "v3884 (#130) - the item's name loses its rarity colour",
     "file": "bible.html",
     "find": "      var line = '<span class=\"d2jsp-db-name' + (_kind ? ' d2jsp-q-' + _kind : '') + '\">'",
     "replace": "      var line = '<span class=\"d2jsp-db-name' + '\">'", "matches": 1},
    {"why": "v3881 look - a wrap tears a fact apart again ('perfect' / '160 fg')",
     "file": "bible.html",
     "find": "'<span class=\"d2jsp-db-l\">· perfect' + NB + '</span>' + (pf != null ? d2jspEscText(d2jspFgText(pf)) + NB + 'fg'",
     "replace": "'<span class=\"d2jsp-db-l\">· perfect' + NB + '</span>' + (pf != null ? d2jspEscText(d2jspFgText(pf)) + ' fg'",
     "matches": 1},   # v3884 re-anchor (#130 - the value cell)
    {"why": "v3881 look / v3884 cells - a wrap tears the posts count from its word again ('3' / 'posts')",
     "file": "bible.html",
     "find": "posts + NB + (posts === 1 ? 'post' : 'posts')))", "replace": "posts + ' ' + (posts === 1 ? 'post' : 'posts')))",
     "matches": 1},
    {"why": "REG-3390 - every item prints the weighing rule again",
     "file": "bible.html", "find": "d2jspBackendHtml(it, null, {noLaw: true})", "replace": "d2jspBackendHtml(it, null, {})",
     "matches": 1},
    {"why": "REG-3390 - the fresh line reads 'Fresh. fresh' again",
     "file": "bible.html",
     "find": "_why.toLowerCase() === fresh.toLowerCase() ? fresh + '.' : fresh + '. ' + _why",
     "replace": "fresh + '. ' + _why", "matches": 1},
    {"why": "REG-3390 - Find narrows nothing",
     "file": "bible.html", "find": "      var hit = !q || String(it.getAttribute('data-name')).indexOf(q) !== -1;\n",
     "replace": "      var hit = true;\n", "matches": 1},
    {"why": "REG-3390 - the database loses its own scroll panel",
     "file": "bible.html", "find": "#tab-d2jsp .d2jsp-db-scroll{max-height:min(62vh,560px);overflow:auto;",
     "replace": "#tab-d2jsp .d2jsp-db-scroll{", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
