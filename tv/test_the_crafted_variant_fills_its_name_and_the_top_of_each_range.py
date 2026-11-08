# -*- coding: utf-8 -*-
"""#95 (REG-1823) — A CRAFTED ITEM IS ITS RECIPE PLUS REGULAR MODS, NAMED ONCE, AND A TOTAL SPLITS BETWEEN THEM.

His demo (2026-09-30, #230): a Ghoul Scarab Amulet, crafted — +20% FCR, +2 Assassin skills, +12 mana, 6% mana regen, a
chance-to-cast and +3 max damage. Our 'Caster Amulet Amulet' editor showed only the recipe's 3 lines, had no way to add
the regular mods, and refused 20 FCR ("5–10 on this item"). The first cut (fb33b9b2) did not touch that editor: it put a
'Crafted' QUALITY on a plain Amulet base — a crafted amulet carrying none of its recipe's fixed lines, named "Grim Noose
Amulet", whose picked mods stored the top of their range — and said a ring offers no crafted, beside the four crafted Ring
recipes the database carries. That variant is REVERTED here and the real editor is fixed, from the tables in the block:

  · ONE NAME: the recipe's name already ends in its base, so the Edit tab says "Caster Amulet" (and "Caster Ring"), never
    "Caster Amulet Amulet"; a base the name does not end in is still said (Hit Power Helm · Full Helm, Harlequin Crest ·
    Shako).
  · NO CRAFTED QUALITY ON A BASE: an Amulet and a Ring offer the qualities itemtypes.txt gives them (Rare, Magic) — a
    crafted item is one of the cube's recipes, picked as itself.
  · REGULAR MODS: a crafted item's Edit tab carries the Regular Mods block (the base tab's own renderer) — the affixes its
    base may roll at its item level under the RARE flag (a crafted item's random affixes are drawn like a rare's), class
    lines included; at most 3 prefixes and 3 suffixes, 4 in all ("3 fixed + 1–4 random", this page's own crafting card).
    Every crafted Ring recipe offers them too. A picked mod stores a BLANK roll (the range), as every other item does.
  · A TOTAL SPLITS: 20 typed into the Caster recipe's FCR box (5–10) is refused NAMING the mod that supplies the rest
    (of the Apprentice) and nothing is saved; with of the Apprentice on the item, 20 is stored as the recipe's 10 and the
    say line prints "20 = 10 (this recipe, 5–10) + 10 (of the Apprentice)"; 25 is refused with the reachable total; and
    the tooltip prints ONE "+20% Faster Cast Rate" line, as the game does.
  · Nothing is written to the vault stores.

REG-1901 — HIS DEMO, POINT BY POINT (the planner beside the console, 2026-09-30, #230 5910409367/…19973/…33089):
  · THE VARIANT FILLS ITS NAME: a crafted item is named like a rare - two words from rareprefix/raresuffix over its
    base ("Skull Emblem" / "Amulet"; the planner's Grim Noose Amulet, his own Ghoul Scarab Amulet) - and the recipe is
    its CRAFTED line ("CRAFTED · Caster Amulet"), said once. The words are his to choose or re-roll, as a rare's are.
    One stored before REG-1901 (no words) is still its recipe's name, said once.
  · THE TOP OF EACH RANGE: a crafted pick's recipe lines land at the top (10% FCR, 20 to Mana, Regenerate Mana 10%),
    and a mod picked from Add Mod lands at the top of its range (Sapphire's Cold Resist 40%). A typed box still wins
    and a cleared one is the range again.
  · Add Mod is the searchable list of what the item can roll (the REG-1823 block). Reset and Escape were GrokBot's
    test steps ("Do not Reset. No Escape on an empty stack."), not features: there is no Reset here.

Drives the shipped builder through tv/test_the_character_builder_is_their_builder.py's harness. A missing node raises.
This law does not skip. RED_PROOF below.
"""
import os
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

import test_the_character_builder_is_their_builder as CB  # noqa: E402

HELP = r"""
function mk(cls, lvl){ window.openCharBuilder(); window._cbOpenNew(); window._cbNewCls(cls); window._cbNewLvl(lvl); window._cbNewGo(); }
function cur(){ return window._cbAll()[window._cbState().bid]; }
function title(){ return (MODAL._html.match(/<div class="cb-ed-n [^"]*">([\s\S]*?)<\/div>/) || [])[1] || null; }
function opts(){ return (MODAL._html.match(/data-q="[a-z]+"/g) || []).map(function(x){ return x.slice(8, -1); }); }
function vaultSnap(){ var o = {}; ['d2r_muleAssign','d2r_owned','d2r_muleEquip','d2r_muleRoster','d2r_foundLog'].forEach(function(k){ o[k] = RAW[k]; }); return o; }
function vaultSame(b){ return ['d2r_muleAssign','d2r_owned','d2r_muleEquip','d2r_muleRoster','d2r_foundLog'].every(function(k){ return RAW[k] === b[k]; }); }
function box(key, lo, hi, val){ var c = {}, a = { 'data-key': key, 'data-lo': String(lo), 'data-hi': String(hi) };
  return { value: String(val), getAttribute: function(n){ return a[n] === undefined ? null : a[n]; }, _c: c,
           classList: { contains: function(x){ return x === 'cb-roll'; }, add: function(x){ c[x] = 1; }, remove: function(x){ delete c[x]; },
                        toggle: function(x, on){ if (on) c[x] = 1; else delete c[x]; } } }; }
function type(key, lo, hi, val){ ELS['cb-roll-say'] = new El('cb-roll-say'); var t = box(key, lo, hi, val); window._cbRollInput({ target: t });
  return { say: ELS['cb-roll-say'].textContent, bad: !!t._c['cb-bad'], box: t.value }; }
function pick(slot, id){ window._cbClosePick(); window._cbOpenPick('slot', slot); window._cbChoose(id); return cur().sets[0].slots[slot]; }
"""


def _run(body):
    if CB.NODE is None:
        raise AssertionError("node is not on this machine — this gate does not skip")
    return CB._run(HELP + body)


class ACraftedItemIsItsRecipePlusRegularMods(unittest.TestCase):

    def test_a_crafted_item_is_named_once(self):
        out = _run(r"""
          mk('Warlock', 90);
          var e88 = pick('neck', 'c88'); OUT.amulet = title();
          OUT.words = [window._cbRareWords('amu', 0), window._cbRareWords('amu', 1)];
          OUT.rn = e88.rn;
          OUT.craftedLine = (MODAL._html.match(/<div class="cb-ed-q">([^<]*)<\/div>/) || [])[1] || null;
          OUT.nameCtl = /id="cb-rn0"/.test(MODAL._html) && /id="cb-rn1"/.test(MODAL._html) && /id="cb-dice"/.test(MODAL._html);
          var t88 = window._cbTipEntry(e88, window._cbItem(e88.id), 90, 'neck', 'Warlock');
          OUT.card = { shown: window._cbShown(e88, window._cbItem(e88.id)).name, tip: t88.name, tipBase: t88.base, q: t88.q };
          window._cbRareName(0, OUT.words[0][0]); window._cbRareName(1, OUT.words[1][0]); OUT.chosen = title();
          var rin = pick('rrin', 'c89'); OUT.ring = [title(), rin.rn];
          var hlm = pick('head', 'c64'); OUT.helm = [title(), hlm.rn];
          pick('head', 'u248'); OUT.unique = title();
          /* one stored before REG-1901 carries no words: its recipe, said once */
          var old = JSON.parse(JSON.stringify(e88)); delete old.rn;
          OUT.old = window._cbShown(old, window._cbItem(old.id)).name;
          /* and the Edit tab of a crafted item with no words: its recipe, its base said once */
          pick('neck', 'c88'); window._cbRareName(0, ''); window._cbRareName(1, ''); OUT.oldTitle = title();
        """)
        w0, w1 = out["words"]
        self.assertEqual(len(out["rn"]), 2, "the crafted variant did not fill its name")
        self.assertIn(out["rn"][0], w0, "a first word this base cannot carry: %r" % out["rn"])
        self.assertIn(out["rn"][1], w1, "a second word this base cannot carry: %r" % out["rn"])
        self.assertEqual(out["amulet"], '%s %s <span class="cb-c-c">Amulet</span>' % tuple(out["rn"]),
                         "the crafted amulet is not its two words over its base")
        self.assertNotIn("Amulet Amulet", out["amulet"])
        self.assertEqual(out["craftedLine"], "CRAFTED · Caster Amulet", "the recipe is not said as the crafted line")
        self.assertTrue(out["nameCtl"], "the crafted name cannot be chosen or re-rolled")
        # the card (the tooltip, _cbShown) says the same name; its base is the tooltip's own second line, as in the game
        self.assertEqual(out["card"], {"shown": " ".join(out["rn"]), "tip": " ".join(out["rn"]), "tipBase": "Amulet", "q": "c"},
                         "the card and the editor name a crafted item differently")
        self.assertEqual(out["chosen"], '%s %s <span class="cb-c-c">Amulet</span>' % (w0[0], w1[0]))
        self.assertEqual(out["ring"][0], '%s %s <span class="cb-c-c">Ring</span>' % tuple(out["ring"][1]))
        self.assertEqual(out["helm"][0], '%s %s <span class="cb-c-c">Full Helm</span>' % tuple(out["helm"][1]),
                         "a crafted helm lost its base")
        self.assertEqual(out["unique"], 'Harlequin Crest <span class="cb-c-u">Shako</span>', "a unique lost its base")
        self.assertEqual(out["old"], "Caster Amulet", "a crafted item stored before its words lost its recipe's name")
        self.assertEqual(out["oldTitle"], "Caster Amulet", "a crafted item with no words doubles its base again")

    def test_a_pick_lands_at_the_top_of_its_range(self):
        out = _run(r"""
          mk('Warlock', 90);
          var e = pick('neck', 'c88');
          OUT.rolls = e.rolls;
          OUT.boxes = (MODAL._html.match(/<input[^>]*data-key="p[123]"[^>]*>/g) || []).map(function(x){ return (x.match(/ value="([^"]*)"/) || [])[1]; });
          var t = window._cbTipEntry(e, window._cbItem(e.id), 90, 'neck', 'Warlock');
          OUT.tip = t.lines.map(function(l){ return (l.html || l.t || '').replace(/<[^>]+>/g, ''); });
          var P = window._cbAffixPool(cur().sets[0].slots.neck), sap = P.rows.p.concat(P.rows.s).filter(function(a){ return a[2] === 'Sapphire'; })[0];
          OUT.sap = !!sap;
          if (sap){ window._cbAddMod(sap[0]); OUT.say = window._cbState().modSay; OUT.added = cur().sets[0].slots.neck.affixes; }
          OUT.cleared = type('p3', 5, 10, '');
          OUT.after = cur().sets[0].slots.neck.rolls;
          OUT.reset = /Reset/.test(MODAL._html);
        """)
        self.assertEqual(out["rolls"], {"p3": 10, "p2": 20, "p1": 10}, "the recipe lines did not land at the top")
        self.assertEqual(out["boxes"], ["10", "20", "10"], "the boxes do not show the top of each range")
        self.assertEqual(out["tip"], ["+10% Faster Cast Rate", "+20 to Mana", "Regenerate Mana 10%"])
        self.assertTrue(out["sap"], "PREMISE: no Sapphire cold resist in the amulet's pool")
        self.assertEqual(out["added"], [{"id": out["added"][0]["id"], "rolls": {"m1": 40}}],
                         "a picked mod did not land at the top of its range")
        self.assertIn("lands at the top of its range (40 of 31-40)", out["say"])
        self.assertEqual(out["cleared"]["say"], "cleared — this roll is its range again")
        self.assertNotIn("p3", out["after"], "a cleared box did not return to the range")
        self.assertFalse(out["reset"], "a Reset sits on the crafted dialog")

    def test_no_crafted_quality_sits_on_a_base(self):
        out = _run(r"""
          mk('Warlock', 90);
          OUT.amu = window._cbCanQ('amu'); OUT.rin = window._cbCanQ('rin'); OUT.ci3 = window._cbCanQ('ci3');
          window._cbOpenPick('slot', 'neck'); window._cbChoose('b:amu');
          OUT.opts = opts();
          window._cbQuality('rare');
          OUT.stuck = window._cbQuality('c');
          OUT.q = cur().sets[0].slots.neck.q;
        """)
        self.assertEqual(out["amu"], ["rare", "m"])
        self.assertEqual(out["rin"], ["rare", "m"])
        self.assertEqual(out["ci3"], ["rare", "m", "sup", "b", "low"])
        self.assertEqual(out["opts"], ["rare", "m"], "an Amulet base offers a quality itemtypes.txt does not give it")
        self.assertFalse(out["stuck"], "'Crafted' stuck on a plain Amulet base")
        self.assertEqual(out["q"], "rare")

    def test_a_crafted_item_takes_regular_mods_from_the_tables(self):
        out = _run(r"""
          mk('Warlock', 90);
          var before = vaultSnap();
          var e = pick('neck', 'c88'), P = window._cbAffixPool(e);
          OUT.block = /<div class="cb-mods-h">Regular Mods<\/div>/.test(MODAL._html) && /id="cb-add-h"/.test(MODAL._html);
          OUT.recipe = /data-key="p3" data-lo="5" data-hi="10"/.test(MODAL._html);
          OUT.lim = P.lim;
          OUT.n = [P.rows.p.length, P.rows.s.length];
          OUT.allRare = P.rows.p.concat(P.rows.s).every(function(a){ return !!a[6]; });
          OUT.apprentice = P.rows.s.some(function(a){ return a[0] === 's174'; });
          OUT.classLine = P.rows.p.some(function(a){ return a[8] >= 0; });
          OUT.add = window._cbAddMod('s174');
          OUT.stored = cur().sets[0].slots.neck.affixes;
          OUT.listed = /data-ax="0"[\s\S]*of the Apprentice/.test(MODAL._html);
          for (var i = 0; i < 3; i++){ var Pi = window._cbAffixPool(cur().sets[0].slots.neck); if (Pi.rows.p[0]) window._cbAddMod(Pi.rows.p[0][0]); }
          var P4 = window._cbAffixPool(cur().sets[0].slots.neck);
          OUT.n4 = cur().sets[0].slots.neck.affixes.length;
          OUT.full = [P4.full.p, P4.full.s];
          var more = P.rows.s.filter(function(a){ return a[0] !== 's174' && a[7] !== 9; })[0];
          OUT.fifth = more ? window._cbAddMod(more[0]) : 'no suffix in the pool';
          OUT.n5 = cur().sets[0].slots.neck.affixes.length;
          OUT.rings = ['c71', 'c80', 'c89', 'c98'].map(function(id){ var r = pick('rrin', id); var Q = window._cbAffixPool(r);
            return [id, r.q, Q.rows.p.length + Q.rows.s.length > 0, /Regular Mods/.test(MODAL._html)]; });
          OUT.vaultSame = vaultSame(before);
        """)
        self.assertTrue(out["block"], "the crafted Edit tab has no Regular Mods / Add Mod")
        self.assertTrue(out["recipe"], "the recipe's own FCR line left the Edit tab")
        self.assertEqual(out["lim"], {"p": 3, "s": 3, "a": 1, "q": 0, "total": 4})
        self.assertGreater(out["n"][0], 0)
        self.assertGreater(out["n"][1], 0)
        self.assertTrue(out["allRare"], "a crafted item offers an affix the rare flag keeps off it")
        self.assertTrue(out["apprentice"], "an amulet's +10% FCR suffix is not offered")
        self.assertTrue(out["classLine"], "no class line (his +2 Assassin skills) is offered")
        self.assertTrue(out["add"])
        self.assertEqual(out["stored"], [{"id": "s174", "rolls": {}}], "a picked mod did not store a blank roll (the range)")
        self.assertTrue(out["listed"])
        self.assertEqual(out["n4"], 4)
        self.assertEqual(out["full"], [True, True], "four random affixes did not fill a crafted item")
        self.assertFalse(out["fifth"], "a fifth random affix went onto a crafted item")
        self.assertEqual(out["n5"], 4)
        for rid, q, offers, block in out["rings"]:
            self.assertEqual(q, "c", rid)
            self.assertTrue(offers and block, "the crafted ring %s offers no regular mods" % rid)
        self.assertTrue(out["vaultSame"], "the crafted edit wrote a vault store")

    def test_a_total_above_the_recipe_splits_with_the_mod_beside_it(self):
        out = _run(r"""
          mk('Warlock', 90);
          pick('neck', 'c88');
          OUT.alone = type('p3', 5, 10, '20');
          OUT.rollsAlone = cur().sets[0].slots.neck.rolls;
          window._cbAddMod('s174');
          OUT.split = type('p3', 5, 10, '20');
          OUT.rolls = cur().sets[0].slots.neck.rolls;
          var e = cur().sets[0].slots.neck, tip = window._cbTipEntry(e, window._cbItem(e.id), 90, 'neck', 'Warlock');
          OUT.fcr = tip.lines.filter(function(l){ return /Faster Cast Rate/.test(l.html || l.t || ''); }).map(function(l){ return l.html || l.t; });
          OUT.over = type('p3', 5, 10, '25');
          OUT.under = type('p3', 5, 10, '3');
          OUT.inside = type('p3', 5, 10, '7');
          OUT.rolls7 = cur().sets[0].slots.neck.rolls;
          /* REG-1852 — a stored roll that is not a whole number is not a known share */
          var e = cur().sets[0].slots.neck, junk = function(v){ var x = JSON.parse(JSON.stringify(e)); x.affixes = [{ id: 'p304', rolls: { m1: v } }]; return x; };
          OUT.blank = window._cbCraftSplit(junk(''), 'p2', '30');
          OUT.nan = window._cbCraftSplit(junk('abc'), 'p2', '30');
          OUT.typed = window._cbCraftSplit(junk('5'), 'p2', '25');
        """)
        self.assertTrue(out["alone"]["bad"])
        self.assertIn("this recipe line is 5–10; 20 is above it", out["alone"]["say"])
        self.assertIn("Add Mod → of the Apprentice", out["alone"]["say"], "the refusal does not name the mod that supplies the rest")
        self.assertIn("not saved", out["alone"]["say"])
        self.assertEqual(out["rollsAlone"], {"p3": 10, "p2": 20, "p1": 10}, "a refused total moved a stored roll")
        self.assertFalse(out["split"]["bad"])
        self.assertEqual(out["split"]["say"], "saved: 20 = 10 (this recipe, 5–10) + 10 (of the Apprentice)")
        self.assertEqual(out["split"]["box"], "10", "the recipe's box does not show its own share")
        self.assertEqual(out["rolls"], {"p3": 10, "p2": 20, "p1": 10})
        self.assertEqual(out["fcr"], ["+20% Faster Cast Rate"], "the tooltip does not print one FCR line of 20")
        self.assertTrue(out["over"]["bad"])
        self.assertIn("so the total is 15–20; 25 is outside it", out["over"]["say"])
        self.assertTrue(out["under"]["bad"])
        self.assertIn("3 is below it", out["under"]["say"])
        self.assertEqual(out["inside"]["say"], "saved: 7 (EXACT)")
        self.assertEqual(out["rolls7"], {"p3": 7, "p2": 20, "p1": 10})
        for k in ("blank", "nan"):
            self.assertFalse(out[k]["ok"])
            self.assertIn("with its roll not typed", out[k]["why"], "a stored %s roll was read as a known share" % k)
            self.assertNotRegex(out[k]["why"], r"\b0 \(|NaN", "an untyped roll was printed as a number")
        self.assertEqual(out["typed"]["say"], "saved: 25 = 20 (this recipe, 10–20) + 5 (Lizard's)")


RED_PROOF = [
    {
        "why": "REG-1901 - the crafted variant no longer fills its name: it is its recipe again, not the planner's two words",
        "file": "bible.html",
        "find": "    if (_cbIsCraft(it)){ e.rn = _cbDice(base) || []; e.rolls = _cbTopRolls(it[6]); }\n",
        "replace": "    if (_cbIsCraft(it)){ e.rolls = _cbTopRolls(it[6]); }\n",
        "matches": 1,
    },
    {
        "why": "REG-1901 - the crafted recipe lines are ranges again, not the top of each range",
        "file": "bible.html",
        "find": "    if (_cbIsCraft(it)){ e.rn = _cbDice(base) || []; e.rolls = _cbTopRolls(it[6]); }\n",
        "replace": "    if (_cbIsCraft(it)){ e.rn = _cbDice(base) || []; }\n",
        "matches": 1,
    },
    {
        "why": "REG-1901 - a mod picked on the crafted dialog is its range again, not the top",
        "file": "bible.html",
        "find": "    var atTop = _cbIsCraft(_cbItem(cur.id)), top = atTop ? _cbTopRolls(a[11]) : {};\n",
        "replace": "    var atTop = _cbIsCraft(_cbItem(cur.id)), top = {};\n",
        "matches": 1,
    },
    {
        "why": "REG-1901 - the card and the tooltip name a crafted item by its recipe while the Edit tab names it by its words",
        "file": "bible.html",
        "find": "    if (_cbIsCraft(it) && e && (e.rn || []).filter(Boolean).length) return { name: e.rn.filter(Boolean).join(' '), base: bn, q: 'c' };\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1901 - the recipe is no longer said once named, as the crafted line",
        "file": "bible.html",
        "find": "(crn.length ? ' \u00b7 ' + esc(it[1]) : '')",
        "replace": "''",
        "matches": 1,
    },
    {
        "why": "REG-1852 - only a whole number is a typed roll; coercing '' to 0 prints a share nobody typed",
        "file": "bible.html",
        "find": "        var t = typedN != null ? typedN : (r[0] === r[1] ? r[0] : null);\n",
        "replace": "        var t = (sv0 != null) ? +sv0 : (r[0] === r[1] ? r[0] : null);\n",
        "matches": 1,
    },
    {
        "why": "the recipe name already ends in its base; without the check the title reads 'Caster Amulet Amulet' again",
        "file": "bible.html",
        "find": "    var baseSpan = base && base[0] !== it[1] && !(craft && (' ' + it[1].toLowerCase()).slice(-(base[0].length + 1)) === ' ' + base[0].toLowerCase());\n",
        "replace": "    var baseSpan = base && base[0] !== it[1];\n",
        "matches": 1,
    },
    {
        "why": "a crafted item rolls from the affix tables; without it in the pool there is nothing to add",
        "file": "bible.html",
        "find": "    if (!b || !d.af || !(_cbIsBase(it) || _cbIsCraft(it) || (it && it[2] === 'r' && (b[22] | 0) > 0))) return out;   /* v3886 (#139) */\n    var q = _cbQ(e, it), lim = _cbLimits(q, b),",
        "replace": "    if (!b || !d.af || !(_cbIsBase(it) || (it && it[2] === 'r' && (b[22] | 0) > 0))) return out;   /* v3886 (#139) */\n    var q = _cbQ(e, it), lim = _cbLimits(q, b),",
        "matches": 1,
    },
    {
        "why": "a crafted item takes at most 4 random affixes; dropping its limit row lets it take none (or the rare's 6)",
        "file": "bible.html",
        "find": "    if (q === 'c') return { p: 3, s: 3, a: 1, q: 0, total: 4 };\n",
        "replace": "    if (q === 'c') return { p: 3, s: 3, a: 1, q: 0, total: null };\n",
        "matches": 1,
    },
    {
        "why": "a crafted item's random affixes are drawn like a rare's; without the flag magic-only rows are offered",
        "file": "bible.html",
        "find": "      if (q === 'c' && !a[6]) return;",
        "replace": "      if (false && !a[6]) return;",
        "matches": 1,
    },
    {
        "why": "a total above the recipe line is split with the mod beside it; without the split 20 is refused again",
        "file": "bible.html",
        "find": "    if (split && split.ok){ r = { ok: true, v: split.v }; t.value = String(split.v); }\n",
        "replace": "    if (false){}\n",
        "matches": 1,
    },
    {
        "why": "the refusal names the mod that supplies the rest; without the search it only says the range",
        "file": "bible.html",
        "find": "    if (can.length) return { ok: false, why: head + '; ' + v + ' is above it — the rest is a regular mod: Add Mod → ' + can.slice(0, 3).join(' / ') + ', then type ' + v + ' again' };\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "the tooltip prints one line per stat; without the crafted fold it prints the recipe's 10 and the mod's 10 apart",
        "file": "bible.html",
        "find": "    if (it && e.affixes && e.affixes.length && _cbIsCraft(it)){ it = it.slice(); it[6] = _cbMergeLines(it[6], rolls); }\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "the crafted Edit tab draws the Regular Mods block; without it the Add Mod door is gone again",
        "file": "bible.html",
        "find": "    var craft = _cbIsCraft(it), M = craft ? _cbModsHtml(e, slot, 'c', base, clvl) : null;\n",
        "replace": "    var craft = false, M = null;\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
