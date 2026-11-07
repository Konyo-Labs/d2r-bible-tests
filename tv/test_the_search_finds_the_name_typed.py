# -*- coding: utf-8 -*-
"""v3881 (REG-3397, #118, GrokBot's v3879 pass) - THE BIBLE'S SEARCH OPENS THE NAME TYPED, AND EVERY SET CAN BE FOUND BY ITS NAME.

GrokBot, his board (#230, 21:24): "searching 'Spirit' and pressing Enter opens Spirit Ward, not the runeword. You have to pick
'Spirit (sword) ... RUNEWORD' from the list", and "'Bul-Kathos' Children' is UNKNOWN: the search answers 'No boss, zone, act, or
item matches'". MEASURED in a browser on v3880: the runeword's entries are labelled "Spirit (sword)" and "Spirit (shield)", so
nothing matched "spirit" exactly; five labels tied at 80 for starting with it (Spirit Ward, Spirit Mask, Spirit Forge, Spirit
Keeper, Spirit (sword)) and the SHORTEST label won Enter. And a set was in the index only when a boss's drop list happened to
name it ("Immortal King set (any)"): Tal Rasha's Wrappings and Bul-Kathos' Children - sets the bible has full cards for
(ITEM_CODEX cat 'set', opened by openDrop) - could not be found at all.

Now a name with a trailing qualifier ("Spirit (sword)") IS the name typed and ranks 95, under an exact label (100) and over a
longer name that merely starts the same (80); and every ITEM_CODEX set is indexed by its own name, opening its set card, never
doubled when a drop list already indexes it. Drives the page's own score() and the index's set block in node, the second over
the REAL ITEM_CODEX. RED_PROOF below. [[the-unjoined-end]]
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
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
NODE = shutil.which("node") or shutil.which("nodejs")
BIBLE = os.path.join(ROOT, "bible.html")


def _src():
    with io.open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("anchor %r occurs %d times - re-point this law" % (start[:60], src.count(start)))
    i = src.index(start)
    return src[i:src.index(end, i + len(start)) + len(end)]


def _node(js):
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=120, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError("node could not drive the page's own code: " + r.stderr[-800:])
    return json.loads(r.stdout)


def _rank(q, labels):
    s = _src()
    js = (_cut(s, "      var GS_STOP={", "};\n") + _cut(s, "      function score(c, q){", "\n      }\n")
          + "var L = %s, q = %s;\n" % (json.dumps(labels), json.dumps(q.strip().lower()))
          + "var sc = L.map(function(l){ return {l: l, s: score({label: l, keywords: ''}, q)}; }).filter(function(x){ return x.s >= 0; });\n"
            "sc.sort(function(a, b){ return b.s - a.s || a.l.length - b.l.length; });\n"
            "process.stdout.write(JSON.stringify(sc));")
    return _node(js)


def _sets(prior):
    """the index's set block over the REAL ITEM_CODEX; prior = labels already indexed (a drop list's)"""
    s = _src()
    codex = _cut(s, "const ITEM_CODEX = {", "};\n")
    # the set cards the page ADDS to the codex at load (Bul-Kathos' Children is one): the real registry is both blocks
    codex += "\n" + _cut(s, "try { Object.assign(ITEM_CODEX, {", "\n}); } catch(e){}")
    block = _cut(s, "    (function(){\n      if (typeof ITEM_CODEX === 'undefined') return;", "    })();\n")
    js = ("var window = {opened: []}; window.openDrop = function(n){ window.opened.push(n); };\n" + codex
          + "var cmds = %s.map(function(l){ return {label: l}; });\n" % json.dumps(prior) + block
          + "var setNames = Object.keys(ITEM_CODEX).filter(function(k){ return ITEM_CODEX[k] && ITEM_CODEX[k].cat === 'set'; })"
            ".map(function(k){ return ITEM_CODEX[k].setName || k; });\n"
            "var added = cmds.slice(%d);\n" % len(prior)
          + "added.forEach(function(c){ c.action(); });\n"
            "process.stdout.write(JSON.stringify({setNames: setNames, added: added.map(function(c){ return {label: c.label, cat: c.cat, "
            "kw: c.keywords}; }), opened: window.opened}));")
    return _node(js)


SPIRIT = ["Spirit Ward", "Spirit Mask", "Spirit Forge", "Spirit Keeper", "Spirit (sword)", "Spirit (shield)"]


@unittest.skipUnless(NODE, "node drives the page's own search code - UNMEASURED here, not a pass")
class TheSearchOpensTheNameTyped(unittest.TestCase):

    def test_spirit_enter_opens_the_runeword(self):
        """* THE POINT - GrokBot's "Spirit" + Enter: the first ranked (what Enter opens) is the runeword"""
        r = _rank("Spirit", SPIRIT)
        self.assertIn(r[0]["l"], ("Spirit (sword)", "Spirit (shield)"), r)
        self.assertEqual([x["s"] for x in r[:2]], [95, 95], r)

    def test_an_exact_label_still_wins_and_a_longer_name_still_answers(self):
        r = _rank("Spirit Ward", SPIRIT)
        self.assertEqual((r[0]["l"], r[0]["s"]), ("Spirit Ward", 100))
        r = _rank("Spirit", ["Spirit", "Spirit (sword)", "Spirit Ward"])
        self.assertEqual([x["l"] for x in r], ["Spirit", "Spirit (sword)", "Spirit Ward"])

    def test_a_qualifier_mid_name_is_not_the_name(self):
        """only a TRAILING "(...)" is a qualifier: "Eth Archon Plate (Enigma/CoH base)" is not "Eth Archon Plate" plus Enigma"""
        r = _rank("Enigma", ["Enigma", "Eth Archon Plate (Enigma/CoH base)"])
        self.assertEqual(r[0]["l"], "Enigma")
        self.assertLess(r[1]["s"], 80)


@unittest.skipUnless(NODE, "node drives the page's own search code - UNMEASURED here, not a pass")
class EverySetIsFoundByItsName(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = _sets(["Immortal King set (any)", "Griswold's Legacy (any)"])

    def test_every_set_is_indexed_and_opens_its_own_card(self):
        """* THE POINT - Bul-Kathos' Children and Tal Rasha's Wrappings, and every other set in the codex"""
        names = set(self.o["setNames"])
        # premise: the codex's set cards (13 when written - measured, not pinned), with the two GrokBot could not find among them
        self.assertTrue(names and {"Bul-Kathos' Children", "Tal Rasha's Wrappings"} <= names, "premise: %r" % sorted(names))
        found = set(a["label"] for a in self.o["added"]) | {"Immortal King", "Griswold's Legacy"}
        self.assertEqual(sorted(names - found), [], "sets the search cannot find")
        self.assertIn("Bul-Kathos' Children", found)
        self.assertIn("Tal Rasha's Wrappings", found)
        self.assertEqual(self.o["opened"], [a["label"] for a in self.o["added"]], "a set entry opens something else")
        self.assertTrue(all(a["cat"] == "set" for a in self.o["added"]))

    def test_a_set_a_drop_list_already_indexes_is_not_doubled(self):
        labels = [a["label"] for a in self.o["added"]]
        self.assertNotIn("Immortal King", labels)
        self.assertNotIn("Griswold's Legacy", labels)
        self.assertEqual(len(labels), len(set(labels)), "a set is indexed twice")

    def test_a_set_is_found_by_its_pieces_too(self):
        tal = [a for a in self.o["added"] if a["label"] == "Tal Rasha's Wrappings"][0]
        self.assertIn("tal rasha's guardianship", tal["kw"])


RED_PROOF = [
    {"why": "REG-3397 - 'Spirit' + Enter opens Spirit Ward again (a qualified name ties every longer name at 80)",
     "file": "bible.html",
     "find": "        if (l.replace(/\\s*\\([^)]*\\)\\s*$/, '') === q) return 95;\n", "replace": "\n", "matches": 1},
    {"why": "REG-3397 - sets a drop list never names cannot be found again",
     "file": "bible.html",
     "find": "        var c = ITEM_CODEX[k]; if (!c || c.cat !== 'set') return;\n",
     "replace": "        var c = ITEM_CODEX[k]; if (!c || c.cat !== 'set' || true) return;\n", "matches": 1},
    {"why": "REG-3397 - a set a drop list already indexes is listed twice",
     "file": "bible.html",
     "find": "        if (have[_k(nm)]) return; have[_k(nm)] = 1;\n", "replace": "        have[_k(nm)] = 1;\n", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
