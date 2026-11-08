# -*- coding: utf-8 -*-
"""v3885 (#136, his 11-08) - A BUILD NEVER WEARS ANOTHER CLASS'S ITEM; AN INVENTORY OR A STASH HOLDS ANYTHING.

His words: "the sacred targe and any paladin based sheilds should not be allowed or even recommended to be equipped as an
item based on the character itself if it cant be placed on him ingame logically and technically", then "druid helm for
druids.. necromancer also has their style.. amazons.. whatever items related", then "and obviously only to items being
equipped.. mules with items can hold anything in inventory/stash", "MULES within the vault hold everything in inventory
and stash..", "and shared stash".

MEASURED 11-08 before the fix: the builder's parent lists already left another class's items out (#174 v-B2), but a class's
own rail or tree node ("Auric Shields", "Pelts (Druid)", "Primal Helms (Barbarian)") listed that class's items to ANY build,
and choosing one put it on the doll (shown red, counted for nothing). And the other way round: a mule inventory's parent
list hid another class's items, though any character carries anything.

Now: for every class the database names, no worn slot's list - parent, rail or tree node - offers an item whose every base
is locked to another class (judged HERE from the database's own type table, never by the page's answer); the class's own
locked items are all still offered to it; another class's rail and node are drawn greyed and cannot be opened; the one
equip door (_cbEquip) refuses another class's item on the doll and says why; and the mule inventory list, the Vault's add
list and the build's personal and shared stash offer a Paladin shield to a Sorceress. Runs the shipped builder in node
(tv/cb_node_harness). RED_PROOF below. [[unknown-stays-unknown]]
"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from cb_node_harness import NODE, _run, _db  # noqa: E402

WORN = ["head", "neck", "tors", "rarm", "larm", "rrin", "lrin", "belt", "feet", "glov"]

BODY = r"""
  window.openCharBuilder();
  var d = window._cbDb(), S = window._cbState();
  var id = {}; d.it.forEach(function(x){ id[x[1]] = x[0]; });
  var WORN = %s;
  OUT.cls = d.cls.map(function(c){ return c.n; });
  OUT.offered = {}; OUT.offOff = {};
  d.cls.forEach(function(c){
    window._cbCommit(function(b){ b.cls = c.n; });
    var seen = {}, offOff = [];
    WORN.forEach(function(slot){
      var add = function(rows){ rows.forEach(function(x){ seen[x[0]] = 1; }); };
      add(window._cbForSlot(slot));
      window._cbRailOf(slot).forEach(function(r){ if (r[1] >= 0) add(window._cbForSlot(slot, r[1])); });
      if (slot === 'rarm' || slot === 'larm') window._cbTree(slot).forEach(function(n){ add(window._cbNodeRows(slot, n[0])); });
      window._cbOpenPick('slot', slot);
      var html = (document.getElementById('cb-modal') || {}).innerHTML || '';
      var re = /<button type="button" class="cb-rail-b cb-rail-off"[^>]*>/g, m;
      while ((m = re.exec(html))) offOff.push([slot, /disabled/.test(m[0]), /onclick/.test(m[0])]);
      window._cbClosePick && window._cbClosePick();
    });
    OUT.offered[c.n] = Object.keys(seen);
    OUT.offOff[c.n] = offOff;
  });
  /* the equip door */
  var pickTo = function(cls, slot, name){
    window._cbCommit(function(b){ b.cls = cls; b.sets[0].slots = {}; });
    window._cbOpenPick('slot', slot);
    var ok = window._cbChoose(id[name]);
    if (S.pick && S.pick.pending) ok = window._cbQuality(window._cbCanQ ? 'b' : 'b');
    var e = (slots().sets[0].slots || {})[slot];
    return { ok: ok, worn: e ? e.id : null, say: S.wearErr || '' };
  };
  OUT.sorcHerald = pickTo('Sorceress', 'larm', 'Herald of Zakarum');
  OUT.palHerald = pickTo('Paladin', 'larm', 'Herald of Zakarum');
  OUT.sorcJalal = pickTo('Sorceress', 'head', "Jalal's Mane");
  OUT.druidJalal = pickTo('Druid', 'head', "Jalal's Mane");
  OUT.sorcTargeBase = pickTo('Sorceress', 'larm', 'Sacred Targe');
  window._cbCommit(function(b){ b.cls = 'Sorceress'; });
  var targe = null; Object.keys(d.b).forEach(function(c){ if (d.b[c][0] === 'Sacred Targe') targe = c; });
  OUT.spiritOnTarge = window._cbWearWhy(id['Spirit'], targe);
  OUT.spiritAny = window._cbWearWhy(id['Spirit']);
  window._cbCommit(function(b){ b.cls = 'Paladin'; });
  OUT.spiritOnTargePal = window._cbWearWhy(id['Spirit'], targe);
  /* the Vault is untouched: with a host open, a class rail and a class node list as they always did */
  window._cbCommit(function(b){ b.cls = 'Sorceress'; });
  var auric = -1; window._cbRailOf('larm').forEach(function(r){ if (r[1] >= 0 && /Auric/.test(r[0])) auric = r[1]; });
  OUT.auricIx = auric;
  OUT.buildAuric = window._cbForSlot('larm', auric).map(function(x){ return x[1]; });
  S.host = { stub: true };
  OUT.hostAuric = window._cbForSlot('larm', auric).map(function(x){ return x[1]; });
  OUT.hostAuricNode = window._cbNodeRows('larm', 'ashd').map(function(x){ return x[1]; });
  OUT.hostWhy = window._cbWearWhy(id['Herald of Zakarum']);
  S.host = null;
  var hc = window._cbHandCatalog('Herald of Zakarum');
  OUT.hand = hc && hc.ok ? hc.rows.map(function(r){ return r.name; }) : null;
  OUT.stash = {};
  ['personal', 'shared'].forEach(function(area){
    window._cbOpenStash(); window._cbStashArea(area); window._cbStashTab('create');
    var names = [];
    window._cbStashTree().forEach(function(n, i){
      window._cbStashCat(i);
      var h = (document.getElementById('cb-modal') || {}).innerHTML || '', re = /data-id="([^"]+)"/g, m;
      while ((m = re.exec(h))) names.push(m[1]);
    });
    OUT.stash[area] = names;
    window._cbStashAdd(id['Herald of Zakarum']);
  });
  OUT.stashHeld = (slots().stash || []).map(function(e){ return e.id; });
  OUT.sharedHeld = (slots().shared || []).map(function(e){ return e.id; });
  OUT.heraldId = id['Herald of Zakarum']; OUT.jalalId = id["Jalal's Mane"];
"""


@unittest.skipIf(NODE is None, "node is not on this machine")
class ABuildNeverWearsAnotherClasssItem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = _run(BODY % repr(WORN).replace("'", '"'))
        db = _db()
        cls.db = db
        cnames = [c["n"] for c in db["cls"]]
        # the database's own judge: an item (unique / set / base) whose base type carries a class index is that class's
        cls.lock = {}
        for x in db["it"]:
            if x[2] in ("u", "s") and x[3] in db["b"]:
                ci = db["ty"][db["b"][x[3]][1]][2]
                if ci is not None and ci >= 0:
                    cls.lock[x[0]] = cnames[ci]
        for c, b in db["b"].items():
            if b[20]:
                ci = db["ty"][b[1]][2]
                if ci is not None and ci >= 0:
                    cls.lock["b:" + c] = cnames[ci]

    def test_no_worn_list_offers_another_classs_item(self):
        """* THE POINT - for every class, no parent list, rail or tree node of a worn slot offers another class's item"""
        self.assertGreaterEqual(len(self.lock), 150, "PRINT THE DENOMINATOR: too few class-locked items read: %d" % len(self.lock))
        self.assertGreaterEqual(len(self.o["cls"]), 7, "premise: the database names the classes (%r)" % self.o["cls"])
        bad = []
        for c, ids in self.o["offered"].items():
            self.assertGreater(len(ids), 500, "premise: %s was offered almost nothing (%d) - the lists were not read" % (c, len(ids)))
            bad += ["%s offered %s (%s only)" % (c, i, self.lock[i]) for i in ids if i in self.lock and self.lock[i] != c]
        self.assertEqual(bad, [], "%d other-class item(s) offered on a worn slot:\n  %s" % (len(bad), "\n  ".join(bad[:20])))

    def test_each_class_keeps_its_own(self):
        """a Druid still gets every pelt, a Paladin every Auric Shield, a Necromancer every head, an Amazon her bows"""
        miss = []
        for c, ids in self.o["offered"].items():
            have = set(ids)
            own = [i for i, k in self.lock.items() if k == c]
            miss += ["%s lost %s" % (c, i) for i in own if i not in have]
        mine = [k for k in set(self.lock.values())]
        self.assertGreaterEqual(len(mine), 6, "premise: class-locked items of only %r" % mine)
        self.assertEqual(miss, [], "%d own-class item(s) left a class's lists:\n  %s" % (len(miss), "\n  ".join(miss[:20])))

    def test_another_classs_rail_is_greyed_and_cannot_open(self):
        sorc = self.o["offOff"]["Sorceress"]
        slots = set(s for s, _d, _o in sorc)
        self.assertTrue({"head", "larm", "rarm"} <= slots, "a Sorceress's helm and hands show no greyed class rail: %r" % sorc)
        self.assertEqual([r for r in sorc if not r[1] or r[2]], [], "a greyed rail is clickable: %r" % sorc)
        druid = self.o["offOff"]["Druid"]
        self.assertNotIn("Pelts", " ".join(s for s, _d, _o in druid))

    def test_the_equip_door_refuses_and_says_why(self):
        o = self.o
        self.assertEqual((o["sorcHerald"]["ok"], o["sorcHerald"]["worn"]), (False, None), "a Sorceress wore Herald of Zakarum: %r" % o["sorcHerald"])
        self.assertIn("Herald of Zakarum is Paladin only", o["sorcHerald"]["say"])
        self.assertIn("A Sorceress cannot wear it in the game, so it is not placed.", o["sorcHerald"]["say"])
        self.assertEqual((o["palHerald"]["ok"], o["palHerald"]["worn"], o["palHerald"]["say"]), (True, o["heraldId"], ""))
        self.assertEqual((o["sorcJalal"]["ok"], o["sorcJalal"]["worn"]), (False, None), "a Sorceress wore Jalal's Mane: %r" % o["sorcJalal"])
        self.assertIn("Druid only", o["sorcJalal"]["say"])
        self.assertEqual((o["druidJalal"]["ok"], o["druidJalal"]["worn"]), (True, o["jalalId"]))
        self.assertEqual(o["sorcTargeBase"]["worn"], None, "a Sorceress wore a Sacred Targe base: %r" % o["sorcTargeBase"])
        self.assertIn("Paladin only", o["spiritOnTarge"], "Spirit in a Sacred Targe was let onto a Sorceress")
        self.assertEqual((o["spiritAny"], o["spiritOnTargePal"]), ("", ""), "Spirit itself, or a Paladin's Spirit Targe, was refused")

    def test_an_inventory_and_a_stash_hold_anything(self):
        """* his 11-08 - only what is WORN on the build screen: the Vault as it always was, its add list and a personal and a shared stash take a Paladin shield"""
        o = self.o
        # his 11-08 "the vault should not be related to this.. vault items and vault logic is the way it always was"
        self.assertGreaterEqual(o["auricIx"], 0, "premise: the off-hand has no Auric Shields rail")
        self.assertNotIn("Herald of Zakarum", o["buildAuric"], "the build screen's Auric rail offers a Sorceress a Paladin shield")
        self.assertIn("Herald of Zakarum", o["hostAuric"], "the Vault's mule window lost its Auric Shields list (vault logic changed)")
        self.assertIn("Herald of Zakarum", o["hostAuricNode"], "the Vault's Auric Shields node lost its items (vault logic changed)")
        self.assertIsNotNone(o["hand"], "the Vault's add list could not be read - UNKNOWN, not passing")
        self.assertIn("Herald of Zakarum", o["hand"], "the Vault's add list hides a Paladin shield")
        for area in ("personal", "shared"):
            self.assertIn(o["heraldId"], o["stash"][area], "a Sorceress's %s stash list hides a Paladin shield" % area)
        self.assertIn(o["heraldId"], o["stashHeld"])
        self.assertIn(o["heraldId"], o["sharedHeld"])


RED_PROOF = [
    {"why": "v3885 (#136) - a class node lists its class's items to any build again (the Sorceress's Auric Shields)",
     "file": "bible.html",
     "find": "  function _cbNodeSrc(slot, t){ return t === CB_OFF_NODE ? _cbForSlot(slot, _cbOffIx(slot)) : _cbForSlot(slot, -1, st.host ? _cbNodeOwn(t) : false); }\n",
     "replace": "  function _cbNodeSrc(slot, t){ return t === CB_OFF_NODE ? _cbForSlot(slot, _cbOffIx(slot)) : _cbForSlot(slot, -1, _cbNodeOwn(t)); }\n",
     "matches": 1, "needs": "node"},
    {"why": "v3885 (#136) - a class rail lists its class's items to any build again (the Sorceress's Pelts)",
     "file": "bible.html",
     "find": "    var bci = (_worn && !st.host) ? _cbClsIx((_cbBuild() || {}).cls)\n",
     "replace": "    var bci = false ? _cbClsIx((_cbBuild() || {}).cls)\n", "matches": 1, "needs": "node"},
    {"why": "v3885 (#136) - the class rule reaches the Vault's mule window (its Auric Shields list empties for a Sorceress mule)",
     "file": "bible.html",
     "find": "    var bci = (_worn && !st.host) ? _cbClsIx((_cbBuild() || {}).cls)\n",
     "replace": "    var bci = (_worn) ? _cbClsIx((_cbBuild() || {}).cls)\n", "matches": 1, "needs": "node"},
    {"why": "v3885 (#136) - the equip door no longer refuses",
     "file": "bible.html",
     "find": "      if (_ww){ st.wearErr = _ww; _cbRender(); return false; }\n",
     "replace": "      if (false){ st.wearErr = _ww; _cbRender(); return false; }\n", "matches": 1, "needs": "node"},
    {"why": "v3885 (#136) - the stash is filtered by class (a Sorceress's shared stash hides a Paladin shield)",
     "file": "bible.html",
     "find": "_cbForSlot(src.slot, i, true).forEach(",
     "replace": "_cbForSlot(src.slot, i).forEach(", "matches": 1, "needs": "node"},
    {"why": "v3885 (#136) - another class's rail is clickable again",
     "file": "bible.html",
     "find": "          if (off) return '<button type=\"button\" class=\"cb-rail-b cb-rail-off\" data-rail=\"' + c[1] + '\" disabled aria-disabled=\"true\"",
     "replace": "          if (off) return '<button type=\"button\" class=\"cb-rail-b cb-rail-off\" data-rail=\"' + c[1] + '\" onclick=\"window._cbRail(' + c[1] + ')\"",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
