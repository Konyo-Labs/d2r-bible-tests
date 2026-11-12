# -*- coding: utf-8 -*-
"""v3900 (REG-3746) - ONE NICKNAME LIST IN EVERY SEARCH BAR, AND NO NICKNAME EVER BECOMES A D2JSP SEARCH.

His ask (via GrokBot, #230 6810554491, 11-12 02:20 IST): the trade nicknames (D2JSP_SLANG, functions/api/d2jsp_quote.js) work
only in Price it - the top "jump straight to it" bar and the D2JSP database's "Find an item" filter are substring matches, so
"cta" never finds Call to Arms and "sunders" never finds a sunder charm. "Sunders" is the family name of all six sunder
charms (never one of them); "lightning sunder" is Crack of the Heavens. And "it doesnt need to search sunders" - no extra
d2jsp search for a nickname: the Worker searches with an item's FIRST nickname (d2jspSearchWords' query), so a search-only
alias must never enter D2JSP_SLANG.

Now: the page carries D2JSP_SLANG word for word (held equal here - the Worker cannot be read from the page), plus
D2R_SEARCH_ALIASES (search-only: the sunder family and each sunder's element name), and d2rNicknameItems(q) -> the item names a
typed word means; the database filter and the jump bar both ask it.

DRIVEN: the page's own d2rNicknameItems and d2jspDbArrange, cut from bible.html and run in node over a small fake DOM. RED_PROOF
below.
"""
import io
import json
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NODE = shutil.which("node") or shutil.which("nodejs")
SUNDERS = ["bone break", "black cleft", "crack of the heavens", "flame rift", "cold rupture", "rotting fissure"]


def _read(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("cut start %r occurs %d times - re-point this law" % (start[:60], src.count(start)))
    i = src.index(start)
    return src[i:src.index(end, i + len(start)) + len(end)]


def _node(js):
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError("node could not run the page's own code: " + r.stderr[-800:])
    return json.loads(r.stdout)


@unittest.skipUnless(NODE, "node is required to run the page's own search code - UNMEASURED here, not a pass")
class OneNicknameListInEverySearchBar(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.page = _read("bible.html")
        cls.worker = _read(os.path.join("functions", "api", "d2jsp_quote.js"))
        cls.page_slang = _cut(cls.page, "var D2JSP_SLANG = {", "\n};\n")
        cls.helper = _cut(cls.page, "var D2R_SEARCH_ALIASES = {", "if (typeof window !== 'undefined') { window.d2rNicknameItems = d2rNicknameItems; window.D2JSP_SLANG = D2JSP_SLANG; }\n")
        cls.arrange = _cut(cls.page, "function d2jspDbArrange(root) {", "\n}\n")

    def test_the_page_list_is_the_workers_word_for_word(self):
        """one list: a nickname added on one side and not the other would answer differently in Price it and the bars"""
        worker_slang = _cut(self.worker, "var D2JSP_SLANG = {", "\n};\n")
        both = _node("var W = (function(){ " + worker_slang + " return D2JSP_SLANG; })();\n"
                     "var P = (function(){ " + self.page_slang + " return D2JSP_SLANG; })();\n"
                     "process.stdout.write(JSON.stringify([W, P]));")
        self.assertEqual(both[0], both[1], "the page's nickname list drifted from the Worker's")
        self.assertGreater(len(both[0]), 40, "PREMISE: the Worker's list was not read")

    def test_a_nickname_names_its_item_and_a_family_its_six(self):
        """* THE POINT - 'cta' finds Call to Arms; 'sunders' all six sunder charms; 'lightning sunder' one"""
        got = _node(
            "var window = {};\n" + self.page_slang + "\n" + self.helper + "\n"
            "process.stdout.write(JSON.stringify({cta: d2rNicknameItems('cta'), shako: d2rNicknameItems('Shako'),"
            " sunders: d2rNicknameItems('sunders'), light: d2rNicknameItems('Lightning Sunder'),"
            " fire: d2rNicknameItems('fire sunder'), none: d2rNicknameItems('enigma'), empty: d2rNicknameItems('  ')}));")
        self.assertEqual(got["cta"], ["call to arms"])
        self.assertEqual(got["shako"], ["harlequin crest"])
        self.assertEqual(sorted(got["sunders"]), sorted(SUNDERS), "'sunders' is the family of six, never one charm")
        self.assertEqual(got["light"], ["crack of the heavens"])
        self.assertEqual(got["fire"], ["flame rift"])
        self.assertEqual(got["none"], [], "a full name came back as a nickname - the bars already match names")
        self.assertEqual(got["empty"], [])

    def test_the_database_filter_finds_an_item_by_its_nickname(self):
        js = ("var window = {};\n" + self.page_slang + "\n" + self.helper + "\n" + self.arrange + "\n"
              "function El(attrs){ this.a = attrs || {}; this.hidden = false; this.kids = []; }\n"
              "El.prototype.getAttribute = function(k){ return this.a[k]; };\n"
              "El.prototype.appendChild = function(c){ this.kids.push(c); };\n"
              "var items = ['call to arms', 'harlequin crest', 'flame rift', 'crack of the heavens', 'bone break', 'enigma']"
              ".map(function(n){ return new El({'data-name': n, 'data-fg': '1', 'data-posts': '1'}); });\n"
              "var group = new El({}); group.querySelectorAll = function(){ return items; };\n"
              "function run(q){ var find = {value: q}, sort = {value: 'name'};\n"
              "  var root = {querySelector: function(s){ return s.indexOf('find') >= 0 ? find : sort; },\n"
              "              querySelectorAll: function(){ return [group]; }};\n"
              "  d2jspDbArrange(root); return items.filter(function(i){ return !i.hidden; }).map(function(i){ return i.a['data-name']; }); }\n"
              "process.stdout.write(JSON.stringify({cta: run('cta'), sunders: run('sunders'), light: run('lightning sunder'),"
              " plain: run('enig'), none: run('zzz')}));")
        got = _node(js)
        self.assertEqual(got["cta"], ["call to arms"], "the database filter did not find Call to Arms by 'cta'")
        self.assertEqual(sorted(got["sunders"]), ["bone break", "crack of the heavens", "flame rift"])
        self.assertEqual(got["light"], ["crack of the heavens"])
        self.assertEqual(got["plain"], ["enigma"], "BASELINE: a plain part of a name stopped finding its item")
        self.assertEqual(got["none"], [])

    def test_the_jump_bar_asks_the_same_helper(self):
        code = "\n".join(l.split("//", 1)[0] for l in self.page.split("\n"))
        self.assertEqual(code.count("var _nick=(typeof window.d2rNicknameItems==='function') ? window.d2rNicknameItems(q) : [];"), 1,
                         "the jump bar no longer asks the nickname list")
        self.assertEqual(code.count("if (_nick.length && _nick.indexOf(String(all[i].label||'').toLowerCase()"), 1,
                         "the jump bar no longer ranks the item a nickname names")

    def test_no_nickname_search_is_added_to_d2jsp(self):
        """his rule: the backfill keeps searching the official name - a search-only alias never enters the query list"""
        worker_slang = _cut(self.worker, "var D2JSP_SLANG = {", "\n};\n")
        self.assertNotIn("sunder", worker_slang.lower(), "a sunder word entered the list the Worker searches d2jsp with")
        self.assertNotIn("D2R_SEARCH_ALIASES", self.worker)


RED_PROOF = [
    {"why": "REG-3746 - the database filter matches names only again: 'cta' finds nothing (his ask 11-12)",
     "file": "bible.html",
     "find": "      var hit = !q || _nm.indexOf(q) !== -1 || _nick.indexOf(_nm.toLowerCase()) !== -1;",
     "replace": "      var hit = !q || _nm.indexOf(q) !== -1;",
     "matches": 1, "needs": "node"},
    {"why": "REG-3746 - 'sunders' names one charm, or none, instead of the family of six",
     "file": "bible.html",
     "find": "  if (Object.prototype.hasOwnProperty.call(D2R_SEARCH_ALIASES, f)) D2R_SEARCH_ALIASES[f].forEach(add);\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3746 - the page's nickname list drifts from the Worker's",
     "file": "bible.html",
     "find": "\"Call to Arms\": [\"cta\"],",
     "replace": "\"Call to Arms\": [\"cta\", \"call\"],",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
