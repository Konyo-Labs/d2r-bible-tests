# -*- coding: utf-8 -*-
"""#174 v-B3 — THE EDIT TAB BUILDS A MAGIC, RARE, SUPERIOR OR LOW ITEM THEIR WAY, OVER THE GAME'S OWN AFFIX TABLES.

His order (2026-09-26 ~02:30): "more items also i see need to be added to the itembase.. literally check and see how
its structured there ... charms too.. mods and buffs ranges of them all with manual additions to add so they sync to
them item within with those same buffs that were manually input there". Their flow, MEASURED (SPEC_174 §10, planner
PNGs 32 / 40-43 / 50-51): pick a BASE -> a Quality tab (Rare · Magic · Superior · Normal · Low, only what the base can
be) -> Edit with Item level · Quality ▾ · Name (a rare's two words + a dice) · Base ▾ · Defense · Sockets · Ethereal,
then REGULAR MODS and ADD MOD, a searchable list grouped PREFIXES / SUFFIXES with every option's range; a charm goes
straight to Edit as magic; a picked mod renames the item ("Grand Charm" -> "Chaotic Grand Charm").

This law drives the SHIPPED modal — the ⟦CHARACTER BUILDER JS⟧ block and the generated ⟦CB_DB⟧ block (af / rn / qm,
tv/char_builder_db.py from his install), cut from bible.html and run in node over the same DOM stand-in the builder's
own law uses (tv/test_the_character_builder_is_their_builder.py's harness, imported, never re-typed):

  · QUALITY IS THE DATA'S. A Diadem (itemtypes.txt circ: Rare 1, Magic blank) opens Quality with Rare · Magic ·
    Superior · Normal · Low, Edit greyed until one is chosen; a Ring (Magic 1, Rare 1) offers Rare · Magic only; a Grand
    Charm (lcha: Magic 1, Rare blank — its ancestor `misc` says Rare 1, which is NOT the charm's) goes straight to Edit
    as magic; a unique never sees the tab.
  · ADD MOD IS THE GAME'S RULE, EACH CLAUSE SEEN: by TYPE (a Grand Charm lists Chaotic, lcha, and never Sturdy, armo),
    by LEVEL (Chaotic is level 50: absent at item level 49, present at 50 - a Grand Charm's qlvl is 1, so its affix level
    is its item level; Crimson p665 has maxlevel 4: on a Ring present at 3, absent at 99), by GROUP (on a RARE Diadem, where three prefixes are allowed so the magic one-prefix cap cannot
    hide the rule: after Devil's, group 125, Arch-Devil's is gone and refused while Jagged, group 105, stays), by CLASS (an Eagle Orb is the Sorceress's: Expert's, tied to the Barbarian, is not offered; on a Crystal
    Sword it is), by the RARE flag (a rare Diadem never lists Bahamut's, rare 0; a magic one does), by the AUTOMOD group
    (an Eagle Orb's auto prefix 303 lists "of the Jackal" a9; a Diadem, auto prefix 0, lists no automod), and by the
    quality's LIMITS (magic: one prefix, then PREFIXES is full; rare: three; a rare jewel: four in all).
  · A ROLL OUTSIDE ITS RANGE IS REFUSED, the range shown: "of Vita" rolls 36-40 (magicsuffix.txt hp); 41 is not
    saved, 38 is saved EXACT under the mod's own key (m1) on the stored entry.
  · A PICKED MOD REACHES THE STORE AND THE TOOLTIP: d2r_charBuilds ...inv[i] = {q: 'm', affixes: [{id: 'p700',
    rolls: {}}, {id: 's338', rolls: {m1: 38}}]}; the in-game tooltip (window.d2Tip) prints "Chaotic Grand Charm of
    Vita" in the magic class with "+1 to Chaos Skills (Warlock Only)" and "+38 to Life"; the Edit tab's name is the
    same words in the same colour; a rare is its two words over its base.
  · IT REACHES THE SHEET: the builder hands the engine the picked affixes by id (the joined harness, engine included):
    STATS' Life row is 38 EXACT.
  · OLD BUILDS LOAD UNCHANGED: a build saved before this (a Diadem with q 'b', no affixes) opens on Edit as Normal and
    hands the engine a plain base.
  · Esc closes the ADD MOD list first, then the picker.
  #174 v-B3 FIX ROUND (the review's reproduced findings, each a case below and a RED_PROOF):
  · THE AFFIX LEVEL, NOT THE ITEM LEVEL: alvl = max(ilvl, qlvl) + magic lvl, or ilvl - qlvl/2, or 2 x ilvl - 99, never
    above 99. A Small Charm (qlvl 28) at item level 50 has alvl 36 and never offers of Vita s349 (level 47) - it needs
    item level 61; a Diadem (qlvl 85, magic lvl 18) at item level 85 offers the same level-90 prefixes as at 99; a
    Diadem never offers Crimson (maxlevel 4) at any item level, a Ring does at 3. A legal pick survives an item-level edit.
  · AN ITEM BORN WITH ENHANCED DEFENSE SITS AT ITS BASE'S MAX + 1: a Godly Diadem (50-60) typed +200% is 183 in the
    tooltip (floor(61 x 300 / 100)), and the Defense box shows 61, fixed; a superior Diadem +15% is 70.
  · A CLASS WEARS IT SOONER: of Magic Arrow (magicsuffix levelreq 11, class ama, classlevelreq 1) on a Short Bow asks an
    Amazon for level 1 and a Sorceress for 11; the level 5 Amazon is not told she cannot wear it.
  · A CHARGED SKILL THE TABLE GIVES AS NEGATIVE is UNKNOWN: never "Level -10" in the list, the mod row or the tooltip.
  · ONE STAT, ONE LINE: Mnemonic + of Memory on a Circlet at level 90 print "+135 to Mana" once ((6 + 6) x 90 >> 3).
  · ADD MOD IS A COMBOBOX: the first option is ACTIVE on open (painted, aria-activedescendant); ArrowDown moves it; Enter
    adds the ACTIVE one. No AUTOMOD header over nothing on a base with no automagic group (a Diadem); an Eagle Orb keeps it.
  · THE SIX RARE WORDS the item tables do not name are named by his install's other string tables and offered: Ghoul,
    Wraith, Fiend (armour), Strap (belt), Scarab (amulet), Crusher (mace).
⚠ WHAT THIS LAW CANNOT SEE: pixels — tv/test_the_character_builder_fits_at_every_width.py measures the Edit tab with its
picked mods and the open ADD MOD list at 2000 / 1280 / 375 in a real browser.
RED_PROOF below.
"""
import os
import re
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

import test_the_character_builder_is_their_builder as CB  # noqa: E402  the builder's own harness

#: helpers every case shares: a build of a class, the current build, the stripped tooltip
HELP = r"""
function mk(cls, lvl){ window.openCharBuilder(); window._cbOpenNew(); window._cbNewCls(cls); window._cbNewLvl(lvl); window._cbNewGo(); }
function cur(){ return window._cbAll()[window._cbState().bid]; }
function strip(h){ return String(h).replace(/<[^>]+>/g, '|').replace(/&#39;/g, "'").replace(/\|+/g, '|'); }
function ids(e){ var P = window._cbAffixPool(e), o = {}; ['p', 's', 'a', 'q'].forEach(function(k){ o[k] = P.rows[k].map(function(a){ return a[0]; }); }); o.full = P.full; return o; }
function has(e, id){ var P = window._cbAffixPool(e); return ['p', 's', 'a', 'q'].some(function(k){ return P.rows[k].some(function(a){ return a[0] === id; }); }); }
function box(ax, key, lo, hi, v){ var at = { 'data-key': key, 'data-lo': String(lo), 'data-hi': String(hi), 'data-ax': String(ax) };
  return { target: { value: String(v), classList: { contains: function(c){ return c === 'cb-roll'; }, add: function(){}, remove: function(){}, toggle: function(){} },
           getAttribute: function(a){ return Object.prototype.hasOwnProperty.call(at, a) ? at[a] : null; } } }; }
function inv(){ var s = cur().sets[0].inv; return s[s.length - 1]; }
"""


def _run(body):
    return CB._run(HELP + body)


@unittest.skipIf(CB.NODE is None, "node is not on this machine")
class TheEditTabBuildsTheirItems(unittest.TestCase):

    def test_quality_is_offered_only_where_the_base_can_be_more_than_one(self):
        out = _run(r"""
          mk('Warlock', 90);
          window._cbOpenPick('slot', 'head'); window._cbChoose('b:ci3');
          OUT.diadem = { tab: window._cbState().pick.tab, pending: window._cbState().pick.pending, stored: !!cur().sets[0].slots.head,
            opts: (MODAL._html.match(/data-q="[a-z]+"/g) || []).map(function(x){ return x.slice(8, -1); }),
            rareCls: /class="cb-opt cb-c-rare" role="option" data-q="rare"[^>]*>Rare</.test(MODAL._html),
            magicCls: /class="cb-opt cb-c-m" role="option" data-q="m"[^>]*>Magic</.test(MODAL._html),
            editGrey: /role="tab" class="cb-tab" disabled aria-selected="false" onclick="window._cbPickTab\('edit'\)">Edit/.test(MODAL._html) };
          window._cbQuality('m'); OUT.afterQ = [window._cbState().pick.tab, cur().sets[0].slots.head.q, /id="cb-qual"/.test(MODAL._html)];
          window._cbClosePick();
          window._cbOpenPick('slot', 'rrin'); window._cbChoose('b:rin');
          OUT.ring = (MODAL._html.match(/data-q="[a-z]+"/g) || []).map(function(x){ return x.slice(8, -1); }); window._cbClosePick();
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('b:cm3');
          OUT.gc = [window._cbState().pick.tab, inv().q, /data-q=/.test(MODAL._html)]; window._cbClosePick();
          var coa = null; window._cbDb().it.forEach(function(x){ if (x[1] === 'Crown of Ages') coa = x[0]; });
          window._cbOpenPick('slot', 'head'); window._cbChoose(coa); OUT.unique = [window._cbState().pick.tab, /Quality</.test(MODAL._html)];
        """)
        d = out["diadem"]
        self.assertEqual((d["tab"], d["pending"], d["stored"]), ("quality", "b:ci3", False),
                         "a Diadem did not wait on its Quality tab (or was equipped before a quality was chosen): %s" % d)
        self.assertEqual(d["opts"], ["rare", "m", "sup", "b", "low"], "the Diadem's qualities are not theirs in their order")
        self.assertTrue(d["rareCls"] and d["magicCls"], "Rare / Magic are not drawn in their colours")
        self.assertTrue(d["editGrey"], "Edit is not greyed while the quality is pending")
        self.assertEqual(out["afterQ"], ["edit", "m", True], "choosing Magic did not equip it and flip to Edit with a Quality box")
        self.assertEqual(out["ring"], ["rare", "m"], "a ring can be only rare or magic (itemtypes.txt ring: Magic 1, Rare 1)")
        self.assertEqual(out["gc"], ["edit", "m", False], "a Grand Charm is always magic and goes straight to Edit")
        self.assertEqual(out["unique"], ["edit", False], "a unique must never see a Quality tab")

    def test_add_mod_lists_by_type_level_and_maxlevel(self):
        out = _run(r"""
          mk('Warlock', 90);
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('b:cm3');
          var e = inv(); OUT.gc99 = [has(e, 'p700'), has(e, 's338'), has(e, 'p143')];
          e.ilvl = 49; OUT.gc49 = has(e, 'p700'); e.ilvl = 50; OUT.gc50 = has(e, 'p700'); e.ilvl = 76; OUT.vita76 = has(e, 's338');
          var rg = { id: 'b:rin', base: 'rin', q: 'm', ilvl: 3 }; OUT.crimson3 = has(rg, 'p665'); rg.ilvl = 99; OUT.crimson99 = has(rg, 'p665');
          var dm = { id: 'b:ci3', base: 'ci3', q: 'm', ilvl: 3 }; OUT.crimsonDiadem = has(dm, 'p665'); dm.ilvl = 99;
          OUT.diademNoChaotic = !has(dm, 'p700') && has(dm, 'p712');
          OUT.firstRow = window._cbDb().af.filter(function(a){ return a[0] === 'p700'; })[0];
        """)
        self.assertEqual(out["firstRow"][:9], ["p700", "p", "Chaotic", 50, None, 42, 1, 125, 7], "the premise moved: Chaotic")
        self.assertEqual(out["gc99"], [True, True, False], "a Grand Charm's list: Chaotic and of Vita yes (lcha), Sturdy never (armo)")
        self.assertEqual((out["gc49"], out["gc50"], out["vita76"]), (False, True, False), "the affix level vs the item level")
        self.assertEqual((out["crimson3"], out["crimson99"]), (True, False), "maxlevel 4: Crimson p665 on a Ring only at item level <= 4")
        self.assertFalse(out["crimsonDiadem"], "a Diadem (qlvl 85, magic lvl 18: alvl 99 at any item level) offered Crimson, maxlevel 4")
        self.assertTrue(out["diademNoChaotic"], "a Diadem lists its own affixes (Devil's) and never a charm's (Chaotic)")

    def test_add_mod_lists_by_group_class_rare_flag_and_automod(self):
        out = _run(r"""
          mk('Warlock', 90);
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('b:cm3');
          OUT.added = window._cbAddMod('p700');
          OUT.stored = inv().affixes;
          window._cbClosePick();
          /* the GROUP on a RARE (three prefixes allowed, so the magic item's one-prefix cap cannot hide the rule): after
             Devil's (group 125) its sibling Arch-Devil's is gone while Jagged (group 105) is still offered */
          window._cbOpenPick('slot', 'head'); window._cbChoose('b:ci3'); window._cbQuality('rare');
          var h0 = cur().sets[0].slots.head; OUT.before = [has(h0, 'p713'), has(h0, 'p186')];
          window._cbAddMod('p712');
          var h = cur().sets[0].slots.head; OUT.sibs = [has(h, 'p713'), has(h, 'p186')];
          OUT.refused = window._cbAddMod('p713'); OUT.say = window._cbState().modSay;
          OUT.rareStored = cur().sets[0].slots.head.affixes;
          OUT.orb = has({ id: 'b:ob1', base: 'ob1', q: 'm', ilvl: 99 }, 'p481');
          OUT.sword = has({ id: 'b:crs', base: 'crs', q: 'm', ilvl: 99 }, 'p481');
          OUT.rareDiadem = has({ id: 'b:ci3', base: 'ci3', q: 'rare', ilvl: 99 }, 'p313');
          OUT.magicDiadem = has({ id: 'b:ci3', base: 'ci3', q: 'm', ilvl: 99 }, 'p313');
          OUT.orbAuto = has({ id: 'b:ob1', base: 'ob1', q: 'm', ilvl: 99 }, 'a9');
          OUT.diademAuto = ids({ id: 'b:ci3', base: 'ci3', q: 'm', ilvl: 99 }).a.length;
          OUT.bowAuto = has({ id: 'b:am1', base: 'am1', q: 'm', ilvl: 99 }, 'a9');
        """)
        self.assertTrue(out["added"], "Chaotic could not be added to a Grand Charm")
        self.assertEqual(out["stored"], [{"id": "p700", "rolls": {}}])
        self.assertEqual(out["before"], [True, True], "the premise moved: Arch-Devil's and Jagged on an empty rare Diadem")
        self.assertEqual(out["sibs"], [False, True], "after Devil's (group 125): Arch-Devil's (125) gone, Jagged (105) still offered")
        self.assertFalse(out["refused"], "a second affix of group 125 was added")
        self.assertIn("not added", out["say"])
        self.assertEqual(out["rareStored"], [{"id": "p712", "rolls": {}}])
        self.assertEqual((out["orb"], out["sword"]), (False, True),
                         "Expert's (tied to the Barbarian) on a Sorceress's orb / on a Crystal Sword anyone holds")
        self.assertEqual((out["rareDiadem"], out["magicDiadem"]), (False, True), "Bahamut's (rare 0) on a rare / a magic Diadem")
        self.assertEqual((out["orbAuto"], out["diademAuto"], out["bowAuto"]), (True, 0, False),
                         "an automod is the base's own automagic group (Eagle Orb 303; a Diadem none; an Amazon bow 300)")

    def test_the_qualitys_limits_hold(self):
        out = _run(r"""
          mk('Warlock', 90);
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('b:cm3'); window._cbAddMod('p700');
          var P = window._cbAffixPool(inv()); OUT.magic = [P.full.p, P.rows.p.length, P.full.s, P.rows.s.length > 0];
          OUT.magicHtml = /Prefixes <small>full · 1 of 1<\/small>/.test((function(){ window._cbModOpen(true); return MODAL._html; })());
          window._cbClosePick();
          window._cbOpenPick('slot', 'head'); window._cbChoose('b:ci3'); window._cbQuality('rare');
          ['p712', 'p374', 'p309'].forEach(function(id){ window._cbAddMod(id); });
          var h = cur().sets[0].slots.head, Q = window._cbAffixPool(h); OUT.rare = [h.affixes.length, Q.full.p, Q.rows.p.length, Q.full.s];
          OUT.fourthOk = has({ id: 'b:ci3', base: 'ci3', q: 'rare', ilvl: 99 }, 'p186');
          OUT.fourth = window._cbAddMod('p186');
          window._cbClosePick();
          window._cbOpenPick('inv', null, [5, 0]); window._cbChoose('b:jew'); OUT.jewTab = window._cbState().pick.tab; window._cbQuality('rare');
          var got = [];
          ['p', 'p', 's', 's'].forEach(function(k){ var J0 = window._cbAffixPool(inv()); got.push(J0.rows[k].length ? window._cbAddMod(J0.rows[k][0][0]) : 'none'); });
          var J = window._cbAffixPool(inv()); OUT.jewel = [got, inv().affixes.length, J.full.p, J.full.s];
        """)
        self.assertEqual(out["magic"], [True, 0, False, True], "a magic item holds one prefix, and still takes a suffix")
        self.assertTrue(out["magicHtml"], "ADD MOD does not say PREFIXES is full (1 of 1)")
        self.assertEqual(out["rare"], [3, True, 0, False], "a rare holds three prefixes, and still takes suffixes")
        self.assertTrue(out["fourthOk"], "the premise moved: Jagged p186 is not a prefix an empty rare Diadem may carry")
        self.assertFalse(out["fourth"], "a fourth prefix went onto a rare")
        self.assertEqual(out["jewTab"], "quality", "a jewel can be magic or rare: it waits on Quality")
        self.assertEqual(out["jewel"], [[True, True, True, True], 4, True, True], "a rare jewel holds four affixes in all")

    def test_a_roll_outside_its_range_is_refused_and_a_picked_mod_reaches_the_store_and_the_tooltip(self):
        out = _run(r"""
          mk('Warlock', 90);
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('b:cm3');
          window._cbAddMod('p700'); window._cbAddMod('s338');
          OUT.boxes = (MODAL._html.match(/data-ax="1" class="cb-roll[^"]*"[^>]*data-key="m1" data-lo="36"[^>]*data-hi="40"/g) || []).length;
          window._cbRollInput(box(1, 'm1', 36, 40, 41)); OUT.bad = [JSON.stringify(inv().affixes[1].rolls), window._cbState().modSay, window._cbState().modBad];
          window._cbRollInput(box(1, 'm1', 36, 40, 38)); OUT.good = inv().affixes;
          window._cbPickTab('edit');
          OUT.name = (MODAL._html.match(/<div class="cb-ed-n (cb-c-[a-z]+)" id="cb-ed-name">([^<]*)</) || []).slice(1);
          var s = inv(), t = window._cbTipEntry(s, window._cbItem(s.id), 90, 'inv', 'Warlock'); OUT.tipQ = t.q; OUT.tip = strip(window.d2Tip(t));
          OUT.tipHead = (window.d2Tip(t).match(/^<div class="(d2t-[a-z]+)">([^<]*)<\/div>/) || []).slice(1);
          OUT.stored = JSON.parse(window.LSR.getItem('d2r_charBuilds'))[window._cbState().bid].sets[0].inv[0];
          window._cbClosePick();
          window._cbOpenPick('slot', 'head'); window._cbChoose('b:ci3'); window._cbQuality('rare');
          var h = cur().sets[0].slots.head; OUT.rn = h.rn; OUT.rareName = (MODAL._html.match(/<div class="cb-ed-n (cb-c-[a-z]+)" id="cb-ed-name">([^<]*) <span/) || []).slice(1);
          var rt = window._cbTipEntry(h, window._cbItem(h.id), 90, 'head', 'Warlock'); OUT.rareTip = [rt.name, rt.base, rt.q];
        """)
        self.assertEqual(out["boxes"], 1, "of Vita's picked row has no roll box keyed m1 inside 36-40")
        self.assertEqual(out["bad"][0], "{}", "41 (outside 36-40) was saved")
        self.assertIn("36–40", out["bad"][1], "the refusal does not show the range")
        self.assertTrue(out["bad"][2], "the refusal is not said as a refusal")
        self.assertEqual(out["good"], [{"id": "p700", "rolls": {}}, {"id": "s338", "rolls": {"m1": 38}}])
        self.assertEqual(out["stored"]["q"], "m")
        self.assertEqual(out["stored"]["affixes"], [{"id": "p700", "rolls": {}}, {"id": "s338", "rolls": {"m1": 38}}],
                         "the picked mods are not on the stored entry (d2r_charBuilds)")
        self.assertEqual(out["name"], ["cb-c-m", "Chaotic Grand Charm of Vita"], "the magic name is not composed prefix + base + suffix, in blue")
        self.assertEqual(out["tipHead"], ["d2t-m", "Chaotic Grand Charm of Vita"])
        self.assertIn("|+1 to Chaos Skills (Warlock Only)|", out["tip"])
        self.assertIn("|+38 to Life|", out["tip"], "the typed roll is not what the tooltip prints")
        self.assertIn("Required Level: 69", out["tip"], "of Vita's own level requirement (69) is not the item's")
        self.assertEqual(len(out["rn"]), 2)
        self.assertTrue(all(out["rn"]), "a rare did not get its two words from the dice")
        self.assertEqual(out["rareName"], ["cb-c-rare", " ".join(out["rn"])], "a rare's Edit name is not its two words in rare yellow")
        self.assertEqual(out["rareTip"], [" ".join(out["rn"]), "Diadem", "rare"])

    def test_the_picked_mods_reach_the_sheet_and_old_builds_load_unchanged(self):
        import test_the_character_builder_is_joined_to_the_engine_and_the_mule_window as J
        out = J._run(HELP + r"""
          mk('Warlock', 90);
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('b:cm3'); window._cbAddMod('p700'); window._cbAddMod('s338');
          window._cbRollInput(box(1, 'm1', 36, 40, 38)); window._cbClosePick();
          OUT.life = rowOf(eng(), 'life'); OUT.tab = rowOf(eng(), 'tab:23');
          OUT.ent = window._cbEngineBuild(cur()).build.inv[0];
          var all = window._cbAll(), id = window._cbState().bid;
          all[id].sets[0].inv = []; all[id].sets[0].slots.head = { id: 'b:ci3', name: 'Diadem', q: 'b', base: 'ci3', sockets: 0, eth: false, rolls: {}, socketed: [], ilvl: 99 };
          window.LSR.setItem('d2r_charBuilds', JSON.stringify(all));
          window.closeCharBuilder(); window.openCharBuilder(id);
          window._cbOpenPick('slot', 'head');
          OUT.old = [window._cbState().pick.tab, (MODAL._html.match(/<option value="([a-z]+)" class="cb-c-[a-z]+" selected>/) || [])[1], /Regular Mods/.test(MODAL._html)];
          OUT.oldEnt = window._cbEngineBuild(cur()).build.slots.head;
        """)
        self.assertEqual(out["life"][:2], [{"min": 38, "max": 38}, "EXACT"], "the typed of Vita did not reach STATS' Life: %s" % out["life"])
        self.assertEqual(out["tab"][:2], [{"min": 1, "max": 1}, "EXACT"], "Chaotic did not reach the Chaos Skills row: %s" % out["tab"])
        self.assertEqual(out["ent"]["affixes"], [{"id": "p700", "rolls": {}}, {"id": "s338", "rolls": {"m1": 38}}])
        self.assertEqual(out["ent"]["quality"], "magic")
        self.assertEqual(out["old"], ["edit", "b", True], "a build saved before v-B3 does not open as a Normal Diadem")
        self.assertEqual((out["oldEnt"]["name"], out["oldEnt"]["quality"], "affixes" in out["oldEnt"]), ("ci3", "base", False),
                         "an old build's base is not handed to the engine exactly as before")

    def test_fix_round_the_affix_level_is_held_against_the_affix_not_the_item_level(self):
        out = _run(r"""
          var sc = function(il){ return has({ id: 'b:cm1', base: 'cm1', q: 'm', ilvl: il }, 's349'); };
          OUT.vita = [sc(50), sc(60), sc(61), sc(99)];
          OUT.alvl = [window._cbAlvl('cm1', 50), window._cbAlvl('cm1', 99), window._cbAlvl('ci3', 85), window._cbAlvl('ci3', 1), window._cbAlvl('cm3', 50), window._cbAlvl('ob1', 50)];
          var P90 = ['p561', 'p565', 'p571', 'p575', 'p579', 'p585', 'p589', 'p713'];
          OUT.diadem85 = P90.map(function(id){ return has({ id: 'b:ci3', base: 'ci3', q: 'm', ilvl: 85 }, id); });
          OUT.diadem99 = P90.map(function(id){ return has({ id: 'b:ci3', base: 'ci3', q: 'm', ilvl: 99 }, id); });
          mk('Amazon', 90);
          window._cbOpenPick('slot', 'head'); window._cbChoose('b:ci3'); window._cbQuality('m'); window._cbAddMod('p561');
          window._cbEdit('ilvl', 85); OUT.kept = (cur().sets[0].slots.head.affixes || []).map(function(x){ return x.id; });
        """)
        self.assertEqual(out["alvl"], [36, 99, 99, 99, 50, 51], "the affix level: Small Charm 50 -> 36 (50 - 28/2), 99 -> 99; "
                         "Diadem 85 / 1 -> 99 (85 + 18, capped); Grand Charm (qlvl 1) 50 -> 50; Eagle Orb (magic lvl 1) 50 -> 51")
        self.assertEqual(out["vita"], [False, False, True, True], "of Vita (level 47) on a Small Charm needs item level 61 (alvl 47)")
        self.assertEqual(out["diadem85"], [True] * 8, "a Diadem at item level 85 (alvl 99) lost its level-90 prefixes")
        self.assertEqual(out["diadem85"], out["diadem99"])
        self.assertEqual(out["kept"], ["p561"], "an item-level edit stripped a pick the game can still roll (Valkyrie's at 85)")

    def test_fix_round_an_item_born_with_enhanced_defense_sits_at_max_plus_one(self):
        out = _run(r"""
          mk('Sorceress', 90);
          window._cbOpenPick('slot', 'head'); window._cbChoose('b:ci3'); window._cbQuality('m'); window._cbAddMod('p150');
          window._cbRollInput(box(0, 'm1', 101, 200, 200));
          var h = cur().sets[0].slots.head; OUT.godly = window._cbTipEntry(h, window._cbItem(h.id), 90, 'head', 'Sorceress').defense;
          OUT.box = (MODAL._html.match(/<input type="number" id="cb-def"[^>]*>/) || [''])[0];
          window._cbQuality('sup'); window._cbAddMod('q2'); window._cbRollInput(box(0, 'm1', 5, 15, 15));
          h = cur().sets[0].slots.head; OUT.sup = window._cbTipEntry(h, window._cbItem(h.id), 90, 'head', 'Sorceress').defense;
          window._cbDelMod(0); window._cbEdit('def', 55);
          h = cur().sets[0].slots.head; OUT.plain = window._cbTipEntry(h, window._cbItem(h.id), 90, 'head', 'Sorceress').defense;
        """)
        self.assertEqual(out["godly"], [183, 183], "a Godly Diadem +200%: floor(61 x 300 / 100) = 183 (its base at max + 1)")
        self.assertIn("disabled", out["box"], "the Defense box can still be typed while the item carries Enhanced Defense")
        self.assertIn('value="61"', out["box"], "the Defense box does not show the max + 1 the item sits at")
        self.assertEqual(out["sup"], [70, 70], "a superior Diadem +15%: floor(61 x 115 / 100) = 70")
        self.assertEqual(out["plain"], [55, 55], "a superior Diadem with no mod: its typed base defense is that number")

    def test_fix_round_a_class_level_requirement_a_charged_skill_and_one_stat_one_line(self):
        out = _run(r"""
          mk('Amazon', 5);
          window._cbOpenPick('slot', 'rarm'); window._cbChoose('b:sbw'); window._cbQuality('m'); window._cbModOpen(true);
          OUT.listNeg = /Magic Arrow[^<]*-\d/.test(MODAL._html); OUT.listUnk = /Level \? Magic Arrow \(\?\/\? Charges\)/.test(MODAL._html);
          OUT.added = window._cbAddMod('s458');
          var s = cur().sets[0].slots.rarm; OUT.ama = window._cbTipEntry(s, window._cbItem(s.id), 5, 'rarm', 'Amazon').reqs.lvl;
          OUT.sor = window._cbTipEntry(s, window._cbItem(s.id), 5, 'rarm', 'Sorceress').reqs.lvl;
          OUT.cannot = /cannot wear it/.test(MODAL._html); OUT.editNeg = /Level -\d/.test(MODAL._html);
          var t = window._cbTipEntry(s, window._cbItem(s.id), 5, 'rarm', 'Amazon'); OUT.tip = t.lines.map(function(l){ return [strip(l.html != null ? l.html : l.t), l.cls]; });
          window._cbClosePick(); OUT.fails = /needs level/.test(ELS['cb-win']._html);
          mk('Sorceress', 90);
          window._cbOpenPick('slot', 'head'); window._cbChoose('b:ci0'); window._cbQuality('m'); window._cbAddMod('p540'); window._cbAddMod('s408');
          var c = cur().sets[0].slots.head; OUT.mana = window._cbTipEntry(c, window._cbItem(c.id), 90, 'head', 'Sorceress').lines.map(function(l){ return strip(l.html != null ? l.html : l.t); });
        """)
        self.assertFalse(out["listNeg"], "ADD MOD lists of Magic Arrow with a negative level or charge count")
        self.assertTrue(out["listUnk"], "ADD MOD does not say the charged level / charges are UNKNOWN (set by the item level)")
        self.assertTrue(out["added"])
        self.assertEqual((out["ama"], out["sor"]), (1, 11), "of Magic Arrow asks an Amazon for classlevelreq 1, anyone else for 11")
        self.assertFalse(out["cannot"], "the level 5 Amazon is told she cannot wear a bow the game lets her wear")
        self.assertFalse(out["fails"], "the Calculations list a requirement the level 5 Amazon meets")
        self.assertFalse(out["editNeg"], "the picked mod's row prints a negative skill level")
        self.assertEqual(out["tip"], [["Level ? Magic Arrow (?/? Charges) - set by the item level (the game's code, not a table value)", "d2t-unk"]],
                         "the tooltip's charged line is not the UNKNOWN one")
        self.assertEqual(out["mana"], ["+135 to Mana (Based on Character Level)"],
                         "Mnemonic + of Memory are one stat: (6 + 6) x 90 >> 3 = 135 on one line")

    def test_fix_round_add_mod_is_a_combobox_and_draws_no_empty_automod(self):
        out = _run(r"""
          mk('Warlock', 90);
          window._cbOpenPick('slot', 'head'); window._cbChoose('b:ci3'); window._cbQuality('rare'); window._cbModOpen(true);
          var act = function(){ var h = MODAL._html; return [(h.match(/id="cb-add-q"[^>]*aria-activedescendant="([^"]*)"/) || [])[1] || null,
            (h.match(/class="cb-add-o cb-act" role="option" id="([^"]*)" aria-selected="true"[^>]*data-id="([^"]*)"/) || []).slice(1),
            (h.match(/cb-add-o cb-act/g) || []).length]; };
          OUT.open = act(); OUT.automod = /Automod/.test(MODAL._html);
          window._cbModSearch('warlock'); window._cbModal(); OUT.typed = act(); OUT.u = /<u>Warlock<\/u>/i.test(MODAL._html);
          OUT.down = window._cbModKey({ key: 'ArrowDown', preventDefault: function(){} }); window._cbModal(); OUT.moved = act();
          window._cbModKey({ key: 'Enter', preventDefault: function(){} });
          OUT.picked = (cur().sets[0].slots.head.affixes || []).map(function(x){ return x.id; });
          window._cbClosePick();
          /* v3885 (#136) - an Eagle Orb is the Sorceress's: the picker refuses it on a Warlock's doll, so the orb case is a Sorceress */
          window._cbCommit(function(b){ b.cls = 'Sorceress'; });
          window._cbOpenPick('slot', 'rarm'); window._cbChoose('b:ob1'); window._cbQuality('m'); window._cbModOpen(true); OUT.orb = /Automod/.test(MODAL._html);
          OUT.words = [window._cbRareWords('uap', 0).filter(function(w){ return /^(Ghoul|Wraith|Fiend)$/.test(w); }).sort(),
                       window._cbRareWords('zlb', 1).indexOf('Strap') >= 0, window._cbRareWords('amu', 1).indexOf('Scarab') >= 0, window._cbRareWords('mac', 1).indexOf('Crusher') >= 0];
        """)
        self.assertEqual(out["open"][0], "cb-add-o-0", "on open no option is active (aria-activedescendant)")
        self.assertEqual((out["open"][1][:1], out["open"][2]), (["cb-add-o-0"], 1), "on open the first option is not the one painted")
        self.assertFalse(out["automod"], "a Diadem (no automagic group) draws an AUTOMOD header over nothing")
        self.assertTrue(out["orb"], "an Eagle Orb (automagic group 303) lost its AUTOMOD group")
        self.assertEqual(out["typed"][0], "cb-add-o-0", "a new search does not make its first match the active one")
        self.assertTrue(out["u"], "the typed match is not underlined")
        self.assertTrue(out["down"], "ArrowDown did nothing")
        self.assertEqual(out["moved"][0], "cb-add-o-1", "ArrowDown did not move the active option")
        self.assertEqual(out["moved"][1][0], "cb-add-o-1")
        self.assertEqual(out["picked"], [out["moved"][1][1]], "Enter did not add the ACTIVE option")
        self.assertEqual(out["words"], [["Fiend", "Ghoul", "Wraith"], True, True, True],
                         "the six rare words his install names outside the item tables are not offered")

    def test_round2_the_added_message_names_the_mod_and_asks_for_a_roll_only_when_there_is_one(self):
        """#174 round 2 (the Grok seat on v3509, img2): "added of the Jackal - type its roll into its box, or leave the range"
        did not say WHAT was added, and asked for a roll on affixes that have none (+10% Faster Cast Rate is fixed). Each
        of the width law's four Diadem mods is added through the builder's own door; each message names the affix and
        whether it is a prefix or a suffix, and asks for a roll - with the range - only when the affix has one"""
        out = _run(r"""
          mk('Warlock', 90);
          window._cbOpenPick('slot', 'head'); window._cbChoose('b:ci3'); window._cbQuality('rare');
          OUT.say = ['p712', 'p374', 's175', 's316'].map(function(id){
            var ok = window._cbAddMod(id), a = window._cbAf ? window._cbAf(id) : null;
            return [id, ok, window._cbState().modSay]; });
        """)
        says = out["say"]
        self.assertEqual([x[1] for x in says], [True] * 4, "PREMISE: the four mods were not all added: %s" % says)
        for id_, _ok, say in says:
            kind = "prefix" if id_.startswith("p") else "suffix"
            self.assertRegex(say, r'^Added the %s "[^"]+" - ' % kind, "%s: the message does not name what was added: %r" % (id_, say))
        ranged = [x[2] for x in says if "keep the range (" in x[2]]
        fixed = [x[2] for x in says if x[2].endswith("its value is fixed by the game")]
        self.assertEqual(len(ranged) + len(fixed), 4, "a message is neither ranged nor fixed: %s" % says)
        self.assertTrue(ranged and fixed, "PREMISE: the four mods are not a mix of ranged and fixed: %s" % says)
        for m in ranged:
            self.assertRegex(m, r"keep the range \(-?\d+--?\d+\)$", "a ranged message does not show its range: %r" % m)

    def test_round5_the_added_message_reads_each_roll_by_its_shape(self):
        """#174 round 5 (the #231 eye on v3510, grok-4.7): the round-2 message compared r[0] with r[1], so a per-level roll
        ["L", 24, key, 24, 3] - Faithful's fixed ac/lvl on body armour, a REAL prefix in his tables - read 'keep the
        range (L-24)'; and every superior row is named "Superior", so it said 'Added the automod "Superior"'. Driven
        through the builder's own doors: a magic Chain Mail takes Faithful; a superior Diadem takes q2 (5-15% ED)"""
        out = _run(r"""
          mk('Warlock', 90);
          window._cbOpenPick('slot', 'tors'); window._cbChoose('b:chn'); window._cbQuality('m');
          OUT.faith = [window._cbAddMod('p520'), window._cbState().modSay];
          window._cbClosePick();
          window._cbOpenPick('slot', 'head'); window._cbChoose('b:ci3'); window._cbQuality('sup');
          OUT.sup = [window._cbAddMod('q2'), window._cbState().modSay];
        """)
        self.assertTrue(out["faith"][0], "PREMISE: Faithful was not added to a magic Chain Mail: %s" % out["faith"])
        self.assertTrue(out["sup"][0], "PREMISE: the superior ED row was not added to a superior Diadem: %s" % out["sup"])
        f, q = out["faith"][1], out["sup"][1]
        self.assertEqual(f, 'Added the prefix "Faithful" - its value is fixed by the game',
                         "a fixed per-level prefix is not read as fixed (the eye: 'keep the range (L-24)'): %r" % f)
        self.assertNotIn("L-", f)
        self.assertRegex(q, r'^Added the superior modifier "[^"]*Enhanced Defense[^"]*" - type your roll into its box, or '
                            r'leave it blank to keep the range \(5-15\)$',
                         "a superior row does not name its property and its range: %r" % q)

    def test_esc_closes_the_add_mod_list_before_the_picker(self):
        out = _run(r"""
          mk('Warlock', 90);
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('b:cm3'); window._cbModOpen(true);
          OUT.open = /id="cb-add-list"/.test(MODAL._html);
          OUT.first = window._cbEsc(); OUT.closed = !/id="cb-add-list"/.test(MODAL._html) && !!window._cbState().pick;
          OUT.second = window._cbEsc();
        """)
        self.assertTrue(out["open"])
        self.assertEqual((out["first"], out["closed"], out["second"]), ("addmod", True, "picker"))


RED_PROOF = [
    {
        "why": "#174 round 5 - a fixed per-level roll is offered as a range to type again (the eye: Faithful read 'keep the range (L-24)')",
        "file": "bible.html",
        "find": "          if (LL.lo !== LL.hi){ _ask = atTop ? 'it lands at the top of its range (",
        "replace": "          if (true){ _ask = atTop ? 'it lands at the top of its range (",
        "matches": 1,
    },
    {
        "why": "#174 round 5 - a superior row is named by its table name again: every one reads 'Added the ... Superior'",
        "file": "bible.html",
        "find": "    var _what = a[1] === 'q' ? _cbAfText(a) : a[2], _ask = null;\n",
        "replace": "    var _what = a[2], _ask = null;\n",
        "matches": 1,
    },
    {
        "why": "#174 round 2 - the added message goes back to 'added of the Jackal - type its roll', naming nothing and asking for a roll a fixed affix does not have",
        "file": "bible.html",
        "find": "    st.modSay = 'Added the ' + _kind + ' \"' + _what + '\" - ' + (_ask || 'its value is fixed by the game');\n",
        "replace": "    st.modSay = 'added ' + a[2] + ' — type its roll into its box, or leave the range';\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 - a base skips its Quality tab (their Select -> Quality -> Edit is gone)",
        "file": "bible.html",
        "find": "      if (qs.length > 1){ p.pending = id; p.tab = 'quality'; _cbModal(); return true; }\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 - ADD MOD stops filtering by item type: a charm lists armour affixes",
        "file": "bible.html",
        # the cut opens on ADD MOD's own first line: _cbSpawnPool (0a7ab41c) repeats the two type lines below it
        "find": "      if (out.full[k]) return;\n      if (!a[9].some(function(t){ return anc[t]; })) return;\n      if (a[10].some(function(t){ return anc[t]; })) return;\n",
        "replace": "      if (out.full[k]) return;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 - ADD MOD ignores the affix level and maxlevel",
        "file": "bible.html",
        "find": "      if (a[3] > alvl || (a[4] != null && alvl > a[4])) return;\n      if (used[a[7]]) return;\n",
        "replace": "      if (used[a[7]]) return;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 - two affixes of one group go on one item",
        "file": "bible.html",
        "find": "      if (used[a[7]]) return;\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 - a rare lists affixes that never spawn on a rare (the rare flag)",
        "file": "bible.html",
        "find": "      if (q === 'rare' && !a[6]) return;\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 - a class item lists another class's tied affixes",
        "file": "bible.html",
        "find": "      if (a[8] >= 0 && tcls != null && tcls >= 0 && a[8] !== tcls) return;\n      if (k === 'a' && a[7] !== (b[22] | 0)) return;\n",
        "replace": "      if (k === 'a' && a[7] !== (b[22] | 0)) return;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 - a magic item takes two prefixes",
        "file": "bible.html",
        "find": "    if (q === 'm') return { p: 1, s: 1, a: 1, q: 0, total: null };\n",
        "replace": "    if (q === 'm') return { p: 2, s: 1, a: 1, q: 0, total: null };\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 - a typed roll of a picked mod never reaches the store",
        "file": "bible.html",
        "find": "x.rolls = x.rolls || {}; if (r.v == null) delete x.rolls[key]; else x.rolls[key] = r.v; okAx = true; });",
        "replace": "x.rolls = x.rolls || {}; okAx = true; });",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 - the tooltip never prints the picked mods",
        "file": "bible.html",
        "find": "    if (it && e.affixes && e.affixes.length){ var W = _cbWithAffixes(it, e); it = W[0]; rolls = W[1]; if (isBase){ it = it.slice(); it[6] = _cbMergeLines(it[6], rolls); } }\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 - a magic item keeps its base's name (Grand Charm, never Chaotic Grand Charm of Vita)",
        "file": "bible.html",
        "find": "    if (q === 'm') return { name: pre.concat([bn], suf).join(' '), base: '', q: 'm' };\n",
        "replace": "    if (q === 'm') return { name: bn, base: '', q: 'm' };\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 - ADD MOD adds any id it is handed, whatever the list offers",
        "file": "bible.html",
        "find": "    if (!a || !(P.rows[a[1]] || []).some(function(r){ return r[0] === id; })){\n",
        "replace": "    if (!a){\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 - a charm's quality flags are inherited again and a Grand Charm offers Rare",
        "file": "bible.html",
        "find": "\"lcha\":[\"m\"]",
        "replace": "\"lcha\":[\"rare\",\"m\"]",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 fix round - ADD MOD holds an affix's level against the ITEM level again (of Vita on a Small Charm at 50)",
        "file": "bible.html",
        "find": "ilvl = e.ilvl || 99, alvl = _cbAlvl(b, ilvl);",
        "replace": "ilvl = e.ilvl || 99, alvl = ilvl;",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 fix round - a magic / rare / superior item with Enhanced Defense reads its base's min..max, not max + 1",
        "file": "bible.html",
        "find": "        if (hasEd && (it[2] === 'u' || it[2] === 's' || isBase)){ lo = hi = b[9] + 1; }\n",
        "replace": "        if (hasEd && (it[2] === 'u' || it[2] === 's')){ lo = hi = b[9] + 1; }\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 fix round - an affix's class level requirement is ignored (an Amazon told she cannot wear her bow)",
        "file": "bible.html",
        "find": "  function _cbAfReq(a, ci){ return (a && a[13] && ci >= 0 && a[13][0] === ci) ? (a[13][1] | 0) : ((a && a[5]) | 0); }\n",
        "replace": "  function _cbAfReq(a, ci){ return (a && a[5]) | 0; }\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 fix round - two affixes of one stat print two lines, each scaled apart (67 + 67, not 135)",
        "file": "bible.html",
        "find": " if (isBase){ it = it.slice(); it[6] = _cbMergeLines(it[6], rolls); } }\n",
        "replace": " }\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 fix round - ArrowDown does not move ADD MOD's active option (Enter adds a row nobody marked)",
        "file": "bible.html",
        "find": "      st.modAct = clamp(k === 'ArrowDown' ? i + 1 : k === 'ArrowUp' ? i - 1 :",
        "replace": "      st.modAct = clamp(k === 'ArrowDown' ? i : k === 'ArrowUp' ? i - 1 :",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 fix round - the active option is never painted, so what Enter adds is invisible",
        "file": "bible.html",
        "find": "        h += '<button type=\"button\" class=\"cb-add-o' + (on ? ' cb-act' : '') + '\"",
        "replace": "        h += '<button type=\"button\" class=\"cb-add-o' + (on ? '' : '') + '\"",
        "matches": 1,
    },
    {
        "why": "#174 v-B3 fix round - ADD MOD draws an AUTOMOD header over nothing on a base with no automagic group",
        "file": "bible.html",
        "find": "      if (k === 'a' && !((base && base[22]) | 0) && !P.n.a) return;\n",
        "replace": "",
        "matches": 1,
    },
]


if __name__ == "__main__":
    if CB.NODE is None:
        sys.stderr.write("⚪ SKIP — node is not on this machine, so the Edit tab was not driven. UNMEASURED, declared (77).\n")
        raise SystemExit(77)
    unittest.main(verbosity=2)
