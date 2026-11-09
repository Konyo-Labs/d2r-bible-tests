# -*- coding: utf-8 -*-
"""#174 v-B2 integration — THE THREE PARTS ARE JOINED: THE BUILDER'S STATS ARE THE ENGINE'S SHEET, AND THE MULE
WINDOW'S HOVER IS THE BUILDER'S ONE IN-GAME TOOLTIP.

The order for the merge of the three v-B2 builders: "the builder's STATS column renders
D2R_CHAR_ENGINE.sheet(build, {difficulty, quests}) - their Normal / Nightmare / Hell tabs and Quests toggle drive
it, every row shows value / range + cap + source; and the mule window's hover switches to the shared in-game
tooltip window.d2Tip (keep one tooltip component)."

THE DEFECT THIS LAW WAS WRITTEN AGAINST — TWO HALVES THAT EACH PASSED THEIR OWN LAW AND NEVER MET. The builder
handed the engine its own build as it stores it, and the engine read it as a different one:
  · the builder stores quality as one letter (q: 'u'); the engine reads 'unique' | 'set' | 'runeword' | 'base', so
    'u' read as "a u item is its own roll" and EVERY row of every sheet was UNKNOWN;
  · the builder stores a typed roll under the TABLE COLUMN it came from (Crown of Ages p2 = prop2); the engine
    reads the property code ('res-all'), so every typed roll was silently summed as its range;
  · the builder names the active set `active`; the engine reads `activeSet` / opts.set, so Set 2 summed Set 1.
Each law was green: the builder's mocked the engine, the engine's was fed the engine's own shape. [[the-unjoined-end]]

DRIVEN on the SHIPPED code, cut from bible.html between real boundaries and run together in node (the builder's own
law's harness — its stand-in DOM, CHARS, LSR, fork sets and exporter — plus the stats engine's script and the
mule-window tooltip script, none re-typed here):

  · THE FIRE ROW IS THE ENGINE'S SUM, WITH ITS CAP AND ITS SOURCE. A Sorceress in Hell with quests on, wearing
    Crown of Ages, Skin of the Vipermagi, Mara's Kaleidoscope and The Oculus, worked by hand from the tables:
        Hell -100 (difficultylevels ResistPenalty) + Anya's scrolls +30 (10 per difficulty, quests on)
        + Crown res-all 20..30 + Vipermagi res-all 20..35 + Mara's res-all 20..30 + Oculus res-all 20
        untouched  = -70 + 80..115 = 10..45        Crown typed 30 = -70 + 90..115 = 20..45
    capped at 75 (75 + no max-resistance item). STATS draws "10–45%" RANGE "cap 75%" (#29(b), his answer 2026-09-28 -
    it read "≤75%"), then "20–45%" when the Crown's
    All Resistances box is typed 30 through the builder's own roll box - the engine received 'res-all': 30.
  · THEIR TABS AND THE QUESTS TOGGLE DRIVE IT: Normal = 0 + 10 + 80..115 = 90..125, capped to 75 with the raw
    beside it; Nightmare = -40 + 20 + 80..115 = 60..95 -> 60–75% (raw 60–95%); Hell with quests off = -20..15.
  · A TYPED ROLL JOINS THE ENGINE'S LINE, OR STATS SAYS IT DID NOT. Bone Break's table writes red-dmg% as -20..-10
    and this database prints it as 10-20: the two do not share a range, so a typed 15 is NOT guessed onto it - the
    engine sums the range and STATS names the roll it was not handed.
  · ONE NAME, MANY ROWS: each of the 8 Rainbow Facets reaches the engine as its own uniqueitems *ID, and resolves.
  · THE ACTIVE SET IS THE ONE SUMMED: with Set 2 on, its helm is counted and Set 1's is not.
  · THE MULE WINDOW'S HOVER IS window.d2Tip, FROM THE SAME DATABASE: a vault name opens the builder's entry for it
    (The Stone of Jordan, "Harlequin Crest (Shako)", Ber Rune by its three socket classes, Monarch's defense), a
    name that is 8 items or none says UNKNOWN, and a runeword's defense exists only when its base is named.
  · THE BOX NEVER RISES ABOVE ITS FLOOR: d2Tip.show(entry, anchor, {floor}) puts the box above the item only when
    it fits under the floor, else below it (the mule window's floor is its panel's header).
  · ONE BOX: the board's #arttip item lane and its title prose lane both ask window.D2TIP_OWNS before opening.

#174 v-B2 FIX ROUND — THE TOOLTIP AND THE SHEET AGREE ABOUT ONE ITEM (the review seat drove the shipped builder and found
the tooltip and the engine answering one item two ways, and each wrong somewhere). Worked by hand from the tables:
  · A RUNEWORD KEEPS ITS BASE. Chains of Honor on Archon Plate (armor.txt 410-524, runes.txt ac% 70): floor(410 x 1.7)
    .. floor(524 x 1.7) = 697..890 in the tooltip AND the engine's defense row. The tooltip gave every +%ED item the
    base's max + 1 and read 892 - above anything the data allows. Crown of Ages (a unique) keeps 349-399.
  · A PER-LEVEL LINE WITH A BLANK PAR IS ITS min..max ROLL. Fortitude hp/lvl par '' 8..12 at level 80:
    floor(8 x 80 / 8)..floor(12 x 80 / 8) = 80..120 in the tooltip and the life row (it printed "+0"); typed 10 through
    the builder's own box -> the engine is handed hp/lvl 10 -> 100.
  · THE SHIFT IS THE TABLE'S. Eaglehorn att/lvl 12, itemstatcost item_tohit_perlevel op param 1: 12 x 80 / 2 = 480 in
    the tooltip and the attack rating row (it printed 120 - every line was divided by 8); with no level, "6 per level".
  · ENHANCED MAXIMUM DAMAGE is its own stat. Hellslayer (Decapitator 2H 49-137, dmg% 100, dmg%/lvl 24 op 5 on
    maxdamage) at level 80: the tooltip's Two-Hand Damage = floor(49 x 2)..floor(137 x (100 + 100 + 240) / 100) =
    98 to 602 (it printed 274, the +240% dropped); the engine: Enhanced Damage 100 (it read 340) and Enhanced Maximum
    Damage 240.
  · res-all-max FEEDS FOUR STATS: Guardian Angel prints the four maximum resistances, never "Fire" alone.
  · A RANDOM CLASS IS A CLASS: Hellfire Torch prints "+3 to one random class's Skill Levels" (never "+0-7"), its Edit
    tab offers the classes, and Sorceress chosen -> the engine is handed randclassskill 1 -> Class Skills 3 EXACT.
  · A CLASS-LOCKED ITEM ON ANOTHER CLASS: a Sorceress in Herald of Zakarum (an Auric Shield) - the tooltip's
    "(Paladin Only)" is red, the doll slot is red, Calculations lists it, and the engine counts nothing on it (fire
    resistance read 10 EXACT from Herald's +50 before).
  · A SET BONUS THE TABLE GIVES NO SWITCH (Trang-Oul's Claws, add func blank) prints no "(N items)" it never had.
  · A MAGIC CHARM nobody typed: the fire row shows what is known + ? and its chip; Faster Cast Rate stays 60 EXACT
    (Vipermagi 30 + Oculus 30) - a Small Charm's affix pool (magicprefix / magicsuffix) never holds FCR.

⚠ WHAT THIS LAW CANNOT SEE: pixels and real pointer events - tv/test_the_mule_window_fits_at_every_width.py hovers
the worn weapon with a real mouse and requires #cb-tip open, #arttip shut, and the box under the EQUIPMENT header;
tv/test_the_character_builder_fits_at_every_width.py measures the STATS column at every width.
RED_PROOF below.
"""
import json
import os
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

import test_the_character_builder_is_their_builder as CB   # the builder law's harness: ONE stand-in, never a copy

NODE = CB.NODE


def _engine_js(s):
    return CB._between(s, '<script id="v174-char-engine-js">', "\n</script>")


def _tip_js(s):
    return CB._between(s, '<script id="vb2-mule-tip-js">', "\n</script>")


def _run(body):
    s = CB._src()
    lp, wp, lsr, chars, backup = CB._stage(s)
    prog = (CB.HARNESS.replace("__DB__", json.dumps(CB._db_json(s))) + lp + wp + lsr + chars + backup
            + _engine_js(s) + "\n" + CB._builder_js(s) + "\n" + _tip_js(s) + "\n" + JOIN
            + "\n;(function(){ var OUT = {};\n" + body + "\nprocess.stdout.write(JSON.stringify(OUT)); })();\n")
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise AssertionError("node failed: " + (r.stderr or r.stdout)[-2000:])
    return json.loads(r.stdout)


#: helpers the cases share: a Sorceress in Hell wearing the four items, each picked through the builder's own picker
JOIN = r"""
function byName(n){ var h = null; window._cbDb().it.forEach(function(x){ if (x[1] === n) h = x; }); return h; }
function wear(pairs){ pairs.forEach(function(p){ var id = byName(p[1])[0]; window._cbOpenPick('slot', p[0]); window._cbChoose(id);
  /* #174 v-B4 - a RUNEWORD now waits on its Base tab (theirs: Select | Base | Edit): it is worn on the base the pick
     used to take without asking - its first (_cbBasesOf) - so every case below reads the same item it always did */
  if (window._cbState().pick && window._cbState().pick.tab === 'base') window._cbPickBase(window._cbBasesOf(window._cbItem(id))[0]);
  window._cbClosePick(); }); }
function sorc(){
  window.openCharBuilder(); window._cbOpenNew(); window._cbNewCls('Sorceress'); window._cbNewLvl(90); window._cbNewGo();
  wear([['head', 'Crown of Ages'], ['tors', 'Skin of the Vipermagi'], ['neck', "Mara's Kaleidoscope"], ['rarm', 'The Oculus']]);
}
/* the builder's own roll box, as a typed value arrives from it (the box carries its key and its range) */
function typeRoll(slot, key, lo, hi, v){
  window._cbOpenPick('slot', slot);
  var at = { 'data-key': key, 'data-lo': String(lo), 'data-hi': String(hi) };
  var t = { value: String(v), classList: { contains: function(c){ return c === 'cb-roll'; }, add: function(){}, remove: function(){}, toggle: function(){} },
            getAttribute: function(a){ return at[a]; } };
  window._cbRollInput({ target: t }); window._cbClosePick();
}
function statsHtml(){ var h = ELS['cb-win']._html; return h.slice(h.indexOf('id="cb-stats"'), h.indexOf('id="cb-modal"')); }
function row(h, label){ var i = h.indexOf('<span class="cb-sl">' + label + '</span>'); return i < 0 ? null : h.slice(i, h.indexOf('</div>', i)); }
function cur(){ return window._cbAll()[window._cbState().bid]; }
function mk(cls, lvl){ window.openCharBuilder(); window._cbOpenNew(); window._cbNewCls(cls); window._cbNewLvl(lvl); window._cbNewGo(); }
function strip(h){ return String(h).replace(/<[^>]+>/g, '').replace(/&#39;/g, "'"); }
function tipOf(slot){ var s = cur().sets[0].slots[slot], it = window._cbItem(s.id), t = window._cbTipEntry(s, it, cur().level, slot, cur().cls);
  return { def: t.defense, dmg1: t.dmg1, dmg2: t.dmg2, lines: t.lines.map(function(l){ return strip(l.html != null ? l.html : l.t); }), set: t.set.map(function(l){ return strip(l.html); }) }; }
function eng(){ var eb = window._cbEngineBuild(cur()); return window.D2R_CHAR_ENGINE.sheet(eb.build, { difficulty: 'hell', quests: true }); }
function rowOf(sh, k){ var r = sh.rows.filter(function(r){ return r.key === k; })[0]; return r ? [r.value, r.source, r.why] : null; }
function sheetRow(key){ var eb = window._cbEngineBuild(slots()), st = window._cbState();
  var sh = window.D2R_CHAR_ENGINE.sheet(eb.build, { difficulty: st.diff, quests: !!st.quests });
  return sh.rows.filter(function(r){ return r.key === key; })[0]; }
"""


@unittest.skipIf(NODE is None, "node is not on this machine")
class TheBuilderSumsThroughTheEngine(unittest.TestCase):

    def test_the_fire_row_is_the_engines_sum_with_its_cap_and_its_source(self):
        out = _run(r"""
          sorc();
          OUT.cls = slots().cls; OUT.worn = Object.keys(slots().sets[0].slots).sort();
          var r0 = sheetRow('res-fire'); OUT.untouched = [r0.value, r0.cap, r0.source];
          OUT.rowUntouched = row(statsHtml(), 'Fire Resistance');
          typeRoll('head', 'p2', 20, 30, 30);
          OUT.stored = slots().sets[0].slots.head.rolls;
          OUT.handed = window._cbEngineBuild(slots()).build.slots.head.rolls;
          var r1 = sheetRow('res-fire'); OUT.typed = [r1.value, r1.cap, r1.source];
          OUT.rowTyped = row(statsHtml(), 'Fire Resistance');
          OUT.raw = window.D2R_CHAR_ENGINE.sheet(JSON.parse(JSON.stringify(slots())), { difficulty: 'hell', quests: true })
            .rows.filter(function(r){ return r.key === 'res-fire'; })[0].source;
        """)
        self.assertEqual(out["cls"], "Sorceress")
        self.assertEqual(out["worn"], ["head", "neck", "rarm", "tors"], "PRINT THE DENOMINATOR: the four items were not worn")
        self.assertEqual(out["untouched"], [{"min": 10, "max": 45}, {"min": 75, "max": 75}, "RANGE"],
                         "untouched: -100 + 30 + 20..30 + 20..35 + 20..30 + 20 = 10..45, cap 75: %s" % out["untouched"])
        self.assertIn('<b>10–45%</b><i>RANGE</i><em class="cb-cap" aria-label="capped at 75%">cap 75%</em>', out["rowUntouched"] or "",
                      "STATS does not draw the fire row as its range, its source and its cap: %s" % out["rowUntouched"])
        self.assertEqual(out["stored"], {"p2": 30}, "the builder stores the typed roll under its column (p2 = prop2)")
        self.assertEqual(out["handed"], {"res-all": 30}, "the typed roll did not reach the engine under the engine's key")
        self.assertEqual(out["typed"], [{"min": 20, "max": 45}, {"min": 75, "max": 75}, "RANGE"],
                         "Crown typed 30: -70 + 30 + 20..35 + 20..30 + 20 = 20..45: %s" % out["typed"])
        self.assertIn('<b>20–45%</b><i>RANGE</i><em class="cb-cap" aria-label="capped at 75%">cap 75%</em>', out["rowTyped"] or "", out["rowTyped"])
        # the witness that the join is needed at all: handed over raw, the same build reads UNKNOWN
        self.assertEqual(out["raw"], "UNKNOWN", "the builder's raw build no longer needs the join - revisit this law")

    def test_their_difficulty_tabs_and_the_quests_toggle_drive_it(self):
        out = _run(r"""
          sorc();
          var seen = {};
          window._cbStatsOpt('diff', 'normal'); seen.normal = [sheetRow('res-fire').value, sheetRow('res-fire').raw, row(statsHtml(), 'Fire Resistance')];
          window._cbStatsOpt('diff', 'nightmare'); seen.nightmare = [sheetRow('res-fire').value, sheetRow('res-fire').raw, row(statsHtml(), 'Fire Resistance')];
          window._cbStatsOpt('diff', 'hell'); window._cbStatsOpt('quests'); seen.hellOff = [sheetRow('res-fire').value, window._cbState().quests, row(statsHtml(), 'Fire Resistance')];
          OUT.seen = seen;
        """)
        n, nm, ho = out["seen"]["normal"], out["seen"]["nightmare"], out["seen"]["hellOff"]
        self.assertEqual((n[0], n[1]), ({"min": 75, "max": 75}, {"min": 90, "max": 125}), "Normal: 0 + 10 + 80..115, capped at 75")
        self.assertIn("<b>75% (raw 90–125%)</b><i>EXACT</i>", n[2], n[2])
        self.assertEqual((nm[0], nm[1]), ({"min": 60, "max": 75}, {"min": 60, "max": 95}), "Nightmare: -40 + 20 + 80..115")
        self.assertIn("<b>60–75% (raw 60–95%)</b><i>RANGE</i>", nm[2], nm[2])
        self.assertEqual((ho[0], ho[1]), ({"min": -20, "max": 15}, False), "Hell, quests off: -100 + 0 + 80..115")
        self.assertIn("<b>−20 to 15%</b><i>RANGE</i>", ho[2], "a range below zero says 'to' with a real minus: %s" % ho[2])

    def test_a_typed_roll_joins_the_engines_line_or_stats_says_it_did_not(self):
        out = _run(r"""
          window.openCharBuilder(); window._cbOpenNew(); window._cbNewCls('Barbarian'); window._cbNewLvl(90); window._cbNewGo();
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose(byName('Bone Break')[0]); window._cbClosePick();
          var b = slots(); b.sets[0].inv[0].rolls = { p2: 15 };
          OUT.mine = byName('Bone Break')[6].map(function(l){ return [l[3], l[1]]; });
          var eb = window._cbEngineBuild(b); OUT.handed = eb.build.inv[0].rolls; OUT.lost = eb.lost;
          OUT.theirs = window.D2R_CHAR_ENGINE.lines(eb.build.inv[0]).lines.filter(function(l){ return l.code === 'red-dmg%'; }).map(function(l){ return [l.min, l.max]; });
          window._cbCommit(function(x){ x.sets[0].inv[0].rolls = { p2: 15 }; }); window._cbRender();
          OUT.note = /not handed to the engine, so its range is summed: Bone Break 10-20 typed 15/.test(statsHtml());
        """)
        self.assertIn(["red-dmg%", [[20, 10, "p2"]]], out["mine"])
        self.assertEqual(out["theirs"], [[-20, -10]], "the engine's table view of Bone Break moved: %s" % out["theirs"])
        self.assertEqual(out["handed"], {}, "a roll whose range the engine does not share was guessed onto its line")
        self.assertEqual(out["lost"], ["Bone Break 10-20 typed 15"])
        self.assertTrue(out["note"], "STATS does not say which typed roll the engine was not handed")

    def test_one_name_many_rows_reaches_the_engine_by_its_table_id(self):
        out = _run(r"""
          window.openCharBuilder();
          var d = window._cbDb(), E = window.D2R_CHAR_ENGINE;
          OUT.rf = d.it.filter(function(x){ return /^Rainbow Facet/.test(x[1]); }).map(function(x){
            var e = window._cbEntryFor(x), eb = window._cbEngineBuild({ cls: 'Sorceress', level: 90, active: 0, sets: [{ slots: { neck: e }, inv: [] }] });
            var h = eb.build.slots.neck; return [x[0], h.name, h.uid, E.resolve(h).kind];
          });
        """)
        self.assertEqual(len(out["rf"]), 8, "PRINT THE DENOMINATOR: the 8 Rainbow Facets are not in the database: %s" % out["rf"])
        for iid, name, uid, kind in out["rf"]:
            self.assertEqual((name, uid, kind), ("Rainbow Facet", iid[1:], "unique"), "%s did not reach the engine as its own row" % iid)

    def test_the_active_set_is_the_one_summed(self):
        out = _run(r"""
          sorc();
          window._cbCommit(function(b){ b.sets.push({ name: 'Set 2', slots: {}, inv: [], swap: {}, ws: 1 }); b.active = 1; });
          window._cbRender();
          OUT.set2 = sheetRow('res-fire').value;
          window._cbCommit(function(b){ b.active = 0; }); window._cbRender();
          OUT.set1 = sheetRow('res-fire').value;
        """)
        self.assertEqual(out["set2"], {"min": -70, "max": -70}, "Set 2 (nothing worn) must sum Hell -100 + 30 alone: %s" % out["set2"])
        self.assertEqual(out["set1"], {"min": 10, "max": 45})


@unittest.skipIf(NODE is None, "node is not on this machine")
class TheMuleWindowTipsLikeTheBuilder(unittest.TestCase):

    def test_a_vault_name_opens_the_builders_entry_for_it(self):
        out = _run(r"""
          var t = function(n, slot){ var e = window._mtEntryFor(n, slot); return { name: e.name, q: e.q, base: e.base || '', defense: e.defense || null,
            lines: (e.lines || []).map(function(l){ return String(l.t || l.html || '').replace(/<[^>]+>/g, ''); }) }; };
          ['The Stone of Jordan', 'Harlequin Crest (Shako)', 'Ber Rune', 'Monarch', 'Rainbow Facet', 'Nothing Real',
           'Enigma (Mage Plate)', 'Enigma'].forEach(function(n){ OUT[n] = t(n); });
        """)
        soj = out["The Stone of Jordan"]
        self.assertEqual((soj["q"], soj["base"]), ("u", "Ring"))
        self.assertIn("+1 to All Skills", soj["lines"])
        shako = out["Harlequin Crest (Shako)"]
        self.assertEqual((shako["name"], shako["base"], shako["defense"]), ("Harlequin Crest", "Shako", [98, 141]),
                         "a vault name with its nickname does not open its item: %s" % shako)
        ber = out["Ber Rune"]
        self.assertEqual(ber["q"], "c", "a rune prints in the game's rune (crafted) colour")
        self.assertEqual([l.split(":")[0] for l in ber["lines"]], ["Weapons", "Armor / Helms", "Shields"])
        self.assertEqual(out["Monarch"]["defense"], [133, 148], "a base shows its own defense range (armor.txt)")
        self.assertIn("8 items print this name", out["Rainbow Facet"]["lines"][0], "an ambiguous name must say UNKNOWN")
        self.assertIn("UNKNOWN", out["Nothing Real"]["lines"][0])
        self.assertEqual(out["Enigma (Mage Plate)"]["base"], "Mage Plate")
        self.assertTrue(out["Enigma (Mage Plate)"]["defense"], "a runeword named with its base shows that base's defense")
        self.assertIsNone(out["Enigma"]["defense"], "a runeword with no base on record must not borrow one's defense")
        self.assertTrue(any("its base is not on record" in l for l in out["Enigma"]["lines"]))

    def test_the_box_never_rises_above_its_floor(self):
        out = _run(r"""
          var a = { getBoundingClientRect: function(){ return { left: 500, top: 350, width: 40, height: 40, right: 540, bottom: 390 }; } };
          var tip = function(){ return ELS['cb-tip']; };
          window.d2Tip.show({ name: 'X' }, a, { floor: 300 }); OUT.fits = parseFloat(tip().style.top);
          window.d2Tip.show({ name: 'X' }, a, { floor: 320 }); OUT.under = parseFloat(tip().style.top);
          window.d2Tip.show({ name: 'X' }, a); OUT.none = parseFloat(tip().style.top);
        """)
        # the stand-in box is 40 tall: above the item is 350 - 40 - 8 = 302
        self.assertEqual(out["none"], 302, "with no floor the box sits above the item")
        self.assertEqual(out["fits"], 302, "above the item fits under a floor of 300")
        self.assertEqual(out["under"], 398, "above the item would cross a floor of 320: it must go below (390 + 8)")

    def test_the_boards_two_lanes_defer_to_it(self):
        s = CB._src()
        card = CB._between(s, "    document.addEventListener('mouseover', function(e){\n      var el = e.target.closest && e.target.closest('.d2art-wrap[aria-label]",
                           "    var ARTTIP_SEL = '")
        prose = CB._between(s, "      function candidate(e){", "      document.addEventListener('mouseover', function(e){ var n = candidate(e);")
        self.assertIn("if (window.D2TIP_OWNS && window.D2TIP_OWNS(e.target)) return;", card,
                      "the board's item card still opens over the mule window's in-game box")
        self.assertIn("if (window.D2TIP_OWNS && window.D2TIP_OWNS(e.target)) return null;", prose,
                      "the board's title lane still opens over the mule window's in-game box")


@unittest.skipIf(NODE is None, "node is not on this machine")
class TheTooltipAndTheSheetAgree(unittest.TestCase):
    """#174 v-B2 fix round - the review seat's findings 1-8 and the pixel seat's charm finding, DRIVEN together"""

    def test_a_runeword_keeps_its_base_and_a_unique_is_born_at_max_plus_one(self):
        out = _run(r"""
          mk('Sorceress', 90); wear([['tors', 'Chains of Honor'], ['head', 'Crown of Ages']]);
          window._cbCommit(function(b){ b.sets[0].slots.tors.base = 'utp'; });
          OUT.tip = tipOf('tors').def; OUT.crown = tipOf('head').def;
          var sh = eng(); OUT.row = rowOf(sh, 'defense');
        """)
        self.assertEqual(out["tip"], [697, 890], "Chains of Honor on Archon Plate: floor(410 x 1.7)..floor(524 x 1.7)")
        self.assertEqual(out["crown"], [349, 399], "Crown of Ages is a unique: max + 1 = 166 x 1.5 + 100..150")
        self.assertIn("Chains of Honor +697..890", out["row"][2], "the engine's defense row names another range: %s" % out["row"])

    def test_a_per_level_line_is_its_roll_with_the_tables_shift(self):
        out = _run(r"""
          mk('Paladin', 80); wear([['tors', 'Fortitude']]);
          OUT.fort = tipOf('tors').lines.filter(function(l){ return /to Life/.test(l); });
          OUT.fortRow = rowOf(eng(), 'life');
          window._cbOpenPick('slot', 'tors');
          var m = MODAL._html, i = m.indexOf('aria-label="per-level roll 8 to 12');
          OUT.box = i >= 0 ? m.slice(m.lastIndexOf('<input', i), m.indexOf('>', i) + 1) : null;
          window._cbClosePick();
          typeRoll('tors', 'p6', 8, 12, 10);
          OUT.handed = window._cbEngineBuild(cur()).build.slots.tors.rolls;
          OUT.fortTyped = tipOf('tors').lines.filter(function(l){ return /to Life/.test(l); });
          OUT.fortTypedRow = rowOf(eng(), 'life');
          mk('Amazon', 80); wear([['rarm', 'Eaglehorn']]);
          OUT.eagle = tipOf('rarm').lines.filter(function(l){ return /Attack Rating/.test(l); });
          OUT.eagleRow = rowOf(eng(), 'ar');
          var e0 = cur().sets[0].slots.rarm, it0 = window._cbItem(e0.id);
          OUT.eagleNoLevel = window._cbTipEntry(e0, it0, null, 'rarm').lines.map(function(l){ return strip(l.html != null ? l.html : l.t); })
            .filter(function(l){ return /Attack Rating/.test(l); });
        """)
        self.assertEqual(out["fort"], ["+80-120 to Life (Based on Character Level)"], "Fortitude hp/lvl 8..12 at 80: %s" % out["fort"])
        self.assertEqual(out["fortRow"][0], {"min": 80, "max": 120})
        self.assertIn('data-lo="8"', out["box"] or "", "Fortitude's per-level roll has no box in the Edit tab")
        self.assertEqual(out["handed"], {"hp/lvl": 10}, "a typed per-level roll did not join the engine's line")
        self.assertEqual(out["fortTyped"], ["+100 to Life (Based on Character Level)"])
        self.assertEqual(out["fortTypedRow"][0], {"min": 100, "max": 100})
        self.assertEqual(out["eagle"], ["+480 to Attack Rating (Based on Character Level)"], "att/lvl is shift 1: 12 x 80 / 2")
        self.assertEqual(out["eagleRow"][0], {"min": 480, "max": 480})
        self.assertEqual(out["eagleNoLevel"], ["(6 per level) to Attack Rating (Based on Character Level)"])

    def test_enhanced_maximum_damage_is_its_own_stat_in_both(self):
        out = _run(r"""
          mk('Barbarian', 80); wear([['rarm', 'Hellslayer']]);
          OUT.dmg = tipOf('rarm').dmg2; var sh = eng(); OUT.ed = rowOf(sh, 'ed'); OUT.emd = rowOf(sh, 'emd');
          var e0 = cur().sets[0].slots.rarm; var t0 = window._cbTipEntry(e0, window._cbItem(e0.id), null, 'rarm');
          OUT.noLevel = [t0.dmg2, t0.lines.map(function(l){ return l.t || ''; }).filter(function(x){ return /Maximum damage/.test(x); })];
        """)
        self.assertEqual(out["dmg"], [98, 98, 602, 602], "Hellslayer 2H: floor(49 x 2) to floor(137 x 4.4) at level 80")
        self.assertEqual(out["ed"][0], {"min": 100, "max": 100}, "the per-level max damage was filed under Enhanced Damage")
        self.assertEqual(out["emd"][0], {"min": 240, "max": 240}, "Enhanced Maximum Damage: 24 x 80 / 8")
        self.assertEqual(out["noLevel"][0][2:], [None, None], "with no level the maximum is UNKNOWN, never the ED-only number")
        self.assertEqual(len(out["noLevel"][1]), 1, "the tooltip does not say why its maximum damage is UNKNOWN")

    def test_a_property_that_feeds_four_stats_names_all_four(self):
        out = _run(r"""
          mk('Paladin', 80); wear([['neck', 'Guardian Angel']]);
          OUT.lines = tipOf('neck').lines.filter(function(l){ return /Maximum/.test(l); }).sort();
        """)
        self.assertEqual(out["lines"], ["+15% to Maximum Cold Resist", "+15% to Maximum Fire Resist",
                                        "+15% to Maximum Lightning Resist", "+15% to Maximum Poison Resist"])

    def test_29b_a_max_resistance_row_is_a_signed_bonus_under_its_own_label(self):
        """#29(b) his answer 2026-09-28: the max-resistance rows read "Max Fire Resistance +0%" - a BONUS to the 75 cap, signed,
        under the label Max - and the cap chip reads "cap 75%". Driven on the shipped builder + engine: a bare Paladin reads +0%
        on all four; Guardian Angel (res-all-max 15, the four stats) reads +15% on all four and lifts the fire row's cap to 90"""
        out = _run(r"""
          mk('Paladin', 80);
          var h0 = statsHtml(); OUT.bare = ['Max Fire Resistance', 'Max Cold Resistance', 'Max Lightning Resistance', 'Max Poison Resistance'].map(function(l){ return row(h0, l); });
          OUT.oldLabel = h0.indexOf('Maximum Fire Resistance') >= 0;
          wear([['neck', 'Guardian Angel']]);
          var h1 = statsHtml(); OUT.ga = ['Max Fire Resistance', 'Max Cold Resistance', 'Max Lightning Resistance', 'Max Poison Resistance'].map(function(l){ return row(h1, l); });
          OUT.fire = row(h1, 'Fire Resistance');
        """)
        self.assertFalse(out["oldLabel"], "STATS still labels the row 'Maximum Fire Resistance'")
        for r in out["bare"]:
            self.assertIsNotNone(r, "a Max ... Resistance row is not drawn at all: %s" % out["bare"])
            self.assertIn("<b>+0%</b><i>EXACT</i>", r, "a bare max-resistance row is not the signed bonus +0%%: %s" % r)
        for r in out["ga"]:
            self.assertIn("<b>+15%</b>", r or "", "Guardian Angel's +15 max resistance is not drawn signed: " + str(r))
        self.assertIn('aria-label="capped at 90%">cap 90%</em>', out["fire"] or "",
                      "the fire row's cap is 75 + the max bonus 15, said as 'cap 90%%': %s" % out["fire"])

    def test_a_random_class_is_a_class_chosen_never_a_number(self):
        out = _run(r"""
          mk('Sorceress', 80); window._cbOpenPick('inv', null, [0, 0]); window._cbChoose(byName('Hellfire Torch')[0]);
          var m = MODAL._html, i = m.indexOf('cb-roll-cls'); OUT.select = i >= 0 ? m.slice(m.lastIndexOf('<select', i), m.indexOf('</select>', i)) : null;
          window._cbClosePick();
          var s0 = function(){ var e = cur().sets[0].inv[0]; return window._cbTipEntry(e, window._cbItem(e.id), 80, 'inv').lines.map(function(l){ return strip(l.html != null ? l.html : l.t); })
            .filter(function(l){ return /Skill Levels/.test(l); }); };
          OUT.untyped = s0(); OUT.rowUntyped = rowOf(eng(), 'class-skills');
          window._cbCommit(function(b){ b.sets[0].inv[0].rolls = { p1: 1 }; });
          OUT.handed = window._cbEngineBuild(cur()).build.inv[0].rolls; OUT.typed = s0(); OUT.rowTyped = rowOf(eng(), 'class-skills');
        """)
        self.assertEqual(out["untyped"], ["+3 to one random class's Skill Levels"], "Hellfire Torch's line: %s" % out["untyped"])
        self.assertIn('<option value="1">Sorceress</option>', out["select"] or "", "the Edit tab offers no class to choose")
        self.assertNotIn("0-7", str(out["untyped"]))
        self.assertEqual(out["rowUntyped"][0], {"min": 0, "max": 3})
        self.assertEqual(out["handed"], {"randclassskill": 1}, "the chosen class did not reach the engine's line")
        self.assertEqual(out["typed"], ["+3 to Sorceress Skill Levels"])
        self.assertEqual(out["rowTyped"][:2], [{"min": 3, "max": 3}, "EXACT"])

    def test_a_class_locked_item_on_another_class_is_said_everywhere_and_counts_nothing(self):
        out = _run(r"""
          /* v3885 (#136) - the picker now refuses another class's item on the doll, so the item reaches a Sorceress the way it
             still can: worn while the build named no class (or an older saved build), then the class is set */
          mk('Sorceress', 90); window._cbCommit(function(b){ b.cls = null; });
          wear([['larm', 'Herald of Zakarum'], ['head', "Arreat's Face"]]);
          window._cbCommit(function(b){ b.cls = 'Sorceress'; }); window._cbRender();   // the doll is drawn for the class it now has
          var e = cur().sets[0].slots.larm; OUT.only = window._cbTipEntry(e, window._cbItem(e.id), 90, 'larm', 'Sorceress').only;
          OUT.fire = rowOf(eng(), 'res-fire');
          OUT.na = eng().notApplied.map(function(n){ return n.why; });
          var h = ELS['cb-win']._html; OUT.red = /class="cb-slot cb-has cb-red"[^>]*data-slot="larm"[^>]*aria-label="[^"]*Paladin only: this Sorceress cannot wear it/.test(h);
          OUT.statsNote = /Herald of Zakarum is Paladin only/.test(statsHtml());
          window._cbView('calc'); h = ELS['cb-win']._html; OUT.calc = strip(h.slice(h.indexOf('Requirements the level'), h.indexOf('Sockets filled')));
          mk('Paladin', 90); wear([['larm', 'Herald of Zakarum']]);
          e = cur().sets[0].slots.larm; OUT.onPala = window._cbTipEntry(e, window._cbItem(e.id), 90, 'larm', 'Paladin').only;
          OUT.palaFire = rowOf(eng(), 'res-fire')[0];
        """)
        self.assertEqual(out["only"], {"t": "(Paladin Only)", "cls": "Paladin", "bad": True})
        self.assertEqual(out["fire"][0], {"min": -70, "max": -70}, "Herald's +50 / Arreat's +30 counted on a Sorceress: %s" % out["fire"])
        self.assertEqual(len([w for w in out["na"] if "cannot wear it" in w]), 2, out["na"])
        self.assertTrue(out["red"], "the doll does not mark the item this class cannot wear")
        self.assertTrue(out["statsNote"], "STATS does not say why the item counts nothing")
        self.assertIn("Herald of Zakarum is Paladin only", out["calc"])
        self.assertEqual(out["onPala"]["bad"], False, "a Paladin's own shield reads red")
        self.assertEqual(out["palaFire"], {"min": -20, "max": -20}, "-100 + 30 + Herald 50 on a Paladin")

    def test_a_set_bonus_with_no_switch_in_the_table_prints_no_count(self):
        out = _run(r"""
          mk('Necromancer', 80); wear([['glov', "Trang-Oul's Claws"], ['tors', "Trang-Oul's Scales"]]);
          OUT.claws = tipOf('glov').set; OUT.scales = tipOf('tors').set;
        """)
        self.assertEqual(out["claws"], ["+25% to Poison Skill Damage (when: not in the tables)"])
        self.assertIn("Lightning Resist +50% (3 items)", out["scales"], "add func 2 lost its count: %s" % out["scales"])

    def test_a_magic_charm_leaves_the_rows_its_affixes_cannot_touch(self):
        out = _run(r"""
          sorc(); window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('b:cm1'); window._cbClosePick();
          var h = statsHtml(); OUT.fire = row(h, 'Fire Resistance'); OUT.fcr = row(h, 'Faster Cast Rate');
          OUT.fcrRow = rowOf(eng(), 'fcr'); OUT.fireRow = rowOf(eng(), 'res-fire');
        """)
        self.assertEqual(out["fcrRow"][:2], [{"min": 60, "max": 60}, "EXACT"], "a Small Charm blanked FCR: %s" % out["fcrRow"])
        self.assertIn("<b>60%</b><i>EXACT</i>", out["fcr"] or "")
        self.assertEqual(out["fireRow"][1], "UNKNOWN", "a charm's fire resistance is unknown until typed")
        self.assertIn("Small Charm is magic", out["fireRow"][2])
        self.assertIn("<b>10–45% + ?</b><i>UNKNOWN</i>", out["fire"] or "", "an UNKNOWN row hides what is known: %s" % out["fire"])


GROUP = r"""
function rowT(label){ window._cbRender(); var r = row(statsHtml(), label); return r ? strip(r) : null; }
function box(key, lo, hi, v){ var at = { 'data-key': key, 'data-lo': String(lo), 'data-hi': String(hi) };
  return { value: String(v), classList: { contains: function(c){ return c === 'cb-roll'; }, add: function(){}, remove: function(){}, toggle: function(){} },
           getAttribute: function(a){ return at[a] === undefined ? null : at[a]; } }; }
function invTip(i){ var e = cur().sets[0].inv[i]; return window._cbTipEntry(e, window._cbItem(e.id), cur().level, 'inv', cur().cls).lines.map(function(l){ return [l.cls, strip(l.html)]; }); }
function hell(){ window._cbState().diff = 'hell'; window._cbState().quests = true; }
"""


@unittest.skipIf(NODE is None, "node is not on this machine")
class ARenewedSunderIsItsBuiltInLinesAndOneRowOfEachGroup(unittest.TestCase):
    """#166 (REG-1868) — Renewed Bone Break (u436) printed 'Breaching-AffixN ... the tables do not describe' five times. Each is a
    row of propertygroups.txt (the generator never pulled it): Breaching-Affix1 = dmg% 75..100 OR pierce-dmg 5..10, Affix2
    mag% 14..25 OR gold% 20..55, Affix3 hp 10..65 OR mana 10..75, Affix4 move1 5..10 OR balance1 12..24 OR all-stats 3..8,
    Affix6 red-mag 5..10 OR red-dmg 5..10 - the same OR rows the page's own SUNDER_TIP card prints. The built-in lines (the
    immunity break, Physical Damage Received 10%) stay fixed. Renewed Cold Rupture's Gelid-Affix5 is in NO table: it stays
    UNKNOWN, said."""

    def test_the_edit_tab_offers_each_groups_rows_and_keeps_the_built_ins_fixed(self):
        out = _run(GROUP + r"""
          mk('Warlock', 88); hell();
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('u436');
          var h = MODAL._html, ul = (h.match(/<ul class="cb-lines"[\s\S]*?<\/ul>/) || [''])[0];
          OUT.unk = (ul.match(/do not describe/g) || []).length;
          OUT.asks = (ul.match(/which rolled\?/g) || []).length;
          OUT.btn = (ul.match(/<button type="button" class="cb-grp-b"[^>]*>[^<]*(<[^b][^>]*>[^<]*)*<\/button>/g) || []).map(strip);
          OUT.items = (ul.match(/<li[^>]*>[\s\S]*?<\/li>/g) || []).map(strip);
          OUT.boxes = (ul.match(/class="cb-roll/g) || []).length;
          window._cbClosePick();
          window._cbOpenPick('inv', null, [2, 0]); window._cbChoose(byName('Renewed Cold Rupture')[0]);
          OUT.cold = (MODAL._html.match(/<ul class="cb-lines"[\s\S]*?<\/ul>/) || [''])[0].match(/an effect the game&#39;s tables name [A-Za-z0-9-]+ but do not describe|an effect the game's tables name [A-Za-z0-9-]+ but do not describe/g);
        """)
        self.assertEqual(out["unk"], 0, "a Breaching group still prints the do-not-describe line")
        self.assertEqual(out["asks"], 5)
        self.assertIn("+75-100% Enhanced Damage", out["btn"])
        self.assertIn("-5-10% to Enemy Physical Damage Resistance", out["btn"])
        self.assertIn("+12-24% Faster Hit Recovery", out["btn"])
        self.assertIn("+3-8 to all Attributes", out["btn"])
        self.assertIn("20-55% Extra Gold from Monsters", out["btn"])
        self.assertEqual(len(out["btn"]), 11, out["btn"])
        self.assertIn("Monster Physical Immunity is Sundered", out["items"])
        self.assertIn("Physical Damage Received Increased by 10%", out["items"])
        self.assertEqual(out["boxes"], 0, "a built-in sunder line or an unpicked group offered a roll box")
        self.assertEqual(out["cold"], ["an effect the game&#39;s tables name Gelid-Affix5 but do not describe"],
                         "Gelid-Affix5, which no table carries, was given words")

    def test_an_unpicked_group_bounds_its_stats_and_a_picked_row_sums(self):
        """v3886 (his 11-08 on a Paladin with a Renewed Bone Break: "for FHR why is it unknown ... based on charater build") -
        an unpicked row of a PickMode-2 group is BOUNDED, not UNKNOWN: each stat any row feeds reads 0 (another row rolled)
        up to the most a row adds, named; picking the row ("which rolled?") makes it exact, as REG-1868 had it."""
        out = _run(GROUP + r"""
          mk('Warlock', 88); hell();
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('u436'); window._cbClosePick();
          OUT.tip0 = invTip(0);
          var sh0 = eng(); OUT.u0 = ['fhr', 'frw', 'ed', 'life', 'mana', 'mf', 'gf', 'str', 'mdr', 'dr'].map(function(k){ var r = rowOf(sh0, k); return [k, r && r[1], r && r[2], r && r[0]]; });
          OUT.unmapped0 = sh0.rows.filter(function(r){ return r.group === 'unmapped'; }).length;
          window._cbStashInv(0);
          OUT.p4 = window._cbPickOpt('p6', 1); OUT.p1 = window._cbPickOpt('p3', 0);
          window._cbRollInput({ target: box('p6', 12, 24, 18) });
          OUT.rolls = JSON.parse(JSON.stringify(cur().sets[0].inv[0].rolls));
          window._cbClosePick();
          OUT.tip1 = invTip(0);
          var sh1 = eng(); OUT.fhr = rowOf(sh1, 'fhr'); OUT.frw = rowOf(sh1, 'frw'); OUT.ed = rowOf(sh1, 'ed'); OUT.life = rowOf(sh1, 'life');
          OUT.fhrRow = rowT('Faster Hit Recovery');
          OUT.picks = window._cbEngineBuild(cur()).build.inv[0].picks; OUT.lost = window._cbEngineBuild(cur()).lost;
          /* a new row for the group: the old row's value goes with it */
          window._cbStashInv(0); window._cbPickOpt('p6', 0); window._cbClosePick();
          OUT.rolls2 = JSON.parse(JSON.stringify(cur().sets[0].inv[0].rolls));
          var sh2 = eng(); OUT.fhr2 = rowOf(sh2, 'fhr'); OUT.frw2 = rowOf(sh2, 'frw');
          /* a value outside the picked row's range is refused, never summed */
          window._cbStashInv(0); window._cbRollInput({ target: box('p6', 5, 10, 30) }); window._cbClosePick();
          OUT.rolls3 = JSON.parse(JSON.stringify(cur().sets[0].inv[0].rolls));
        """)
        self.assertIn(["d2t-unk", "one of: +75-100% Enhanced Damage or -5-10% to Enemy Physical Damage Resistance"], out["tip0"])
        self.assertIn(["d2t-p", "Physical Damage Received Increased by 10%"], out["tip0"])
        most = {"fhr": 24, "frw": 10, "ed": 100, "life": 65, "mana": 75, "mf": 25, "gf": 55, "str": 8, "mdr": 10, "dr": 10}
        for k, src, why, val in out["u0"]:
            self.assertEqual(src, "RANGE", "%s read %s beside an unpicked Renewed Bone Break group (bounded, never UNKNOWN)" % (k, src))
            self.assertEqual(val, {"min": 0, "max": most[k]}, "%s is not 0 up to the most its group adds: %r" % (k, val))
            self.assertIn("Renewed Bone Break", why)
            self.assertIn('"which rolled?" on the item makes it exact', why)
        self.assertEqual(out["unmapped0"], 0)
        self.assertTrue(out["p4"] and out["p1"])
        self.assertEqual(out["rolls"], {"p6o": 1, "p3o": 0, "p6": 18})
        self.assertIn(["d2t-p", "+18% Faster Hit Recovery"], out["tip1"])
        self.assertIn(["d2t-p", "+75-100% Enhanced Damage"], out["tip1"])
        self.assertEqual(out["fhr"][0], {"min": 18, "max": 18})
        self.assertEqual(out["fhr"][1], "EXACT")
        self.assertIn("Renewed Bone Break +18 typed", out["fhr"][2])
        self.assertEqual(out["frw"][:2], [{"min": 0, "max": 0}, "EXACT"], "the group picked FHR and still blanked run/walk")
        self.assertEqual(out["ed"][:2], [{"min": 75, "max": 100}, "RANGE"])
        self.assertEqual(out["life"][:2], [{"min": 0, "max": 65}, "RANGE"], "an unpicked group's life row is not 0..65: %r" % (out["life"],))
        self.assertIn("18%", out["fhrRow"])
        self.assertEqual(out["picks"], {"Breaching-Affix4": {"o": 1, "v": 18}, "Breaching-Affix1": {"o": 0, "v": None}})
        self.assertEqual(out["lost"], [], "a group's own key was reported as a roll the engine was not handed")
        self.assertEqual(out["rolls2"], {"p6o": 0, "p3o": 0}, "the old row's value stayed under the new row")
        self.assertEqual(out["fhr2"][:2], [{"min": 0, "max": 0}, "EXACT"])
        self.assertEqual(out["frw2"][:2], [{"min": 5, "max": 10}, "RANGE"])
        self.assertEqual(out["rolls3"], {"p6o": 0, "p3o": 0}, "a value outside the picked row's range was saved")

    def test_a_latent_sunders_negative_resist_is_in_the_sum(self):
        """the latent sunder's player resist (Cold Rupture -90..-70, the same shape on the other five) is summed, and the
        immunity break is its own line, never a resist"""
        out = _run(GROUP + r"""
          mk('Warlock', 88); hell();
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose(byName('Latent Cold Rupture')[0]); window._cbClosePick();
          var sh = eng(); OUT.cold = rowOf(sh, 'res-cold'); OUT.fire = rowOf(sh, 'res-fire');
        """)
        self.assertEqual(out["cold"][:2], [{"min": -160, "max": -140}, "RANGE"])
        self.assertIn("Latent Cold Rupture -90..-70", out["cold"][2])
        self.assertEqual(out["fire"][:2], [{"min": -70, "max": -70}, "EXACT"])


@unittest.skipIf(NODE is None, "node is not on this machine")
class TheClaimsOnHisScreenDrivenThroughTheEngine(unittest.TestCase):
    """#166 — the two claims the eyes could not settle (GrokBot #230 5981255360 / 5981232888), driven through the shipped
    builder and engine. Sentence by sentence, what the sheet actually says."""

    def test_the_paladin_claim(self):
        out = _run(GROUP + r"""
          mk('Paladin', 1); hell();
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('b:cm1'); window._cbQuality('m');
          window._cbAddMod('p322'); window._cbAddMod('s267');
          window._cbCommit(function(b){ b.sets[0].inv[0].affixes[0].rolls = { m1: 5 }; }); window._cbClosePick();
          OUT.tip = invTip(0);
          var at = function(L){ window._cbCommit(function(b){ b.level = L; }); var sh = eng();
            return { fire: rowOf(sh, 'res-fire'), cold: rowOf(sh, 'res-cold'), fhr: rowT('Faster Hit Recovery'),
                     note: (sh.notApplied || []).map(function(n){ return n.why; }) }; };
          OUT.l1 = at(1); OUT.l28 = at(28); OUT.l29 = at(29);
          window._cbCommit(function(b){ b.sets[0].inv = []; b.level = 1; });
          window._cbOpenPick('slot', 'larm'); window._cbChoose('b:buc'); window._cbQuality('m'); window._cbAddMod('p323');
          window._cbCommit(function(b){ b.sets[0].slots.larm.affixes[0].rolls = { m1: 5 }; }); window._cbClosePick();
          OUT.b1 = [rowT('Fire Resistance'), rowT('Faster Hit Recovery')];
          window._cbCommit(function(b){ b.level = 4; }); OUT.b4 = [rowT('Fire Resistance'), rowT('Faster Hit Recovery')];
          window._cbCommit(function(b){ delete b.sets[0].slots.larm; b.level = 1; });
          window._cbOpenPick('slot', 'tors'); window._cbChoose('b:qui'); window._cbQuality('m'); window._cbEdit('ilvl', 10);
          var bal = window._cbAffixPool(cur().sets[0].slots.tors).rows.s.filter(function(a){ return a[2] === 'of Balance'; })[0];
          OUT.qa = bal ? window._cbAddMod(bal[0]) : false; window._cbClosePick();
          OUT.q1 = [rowT('Faster Hit Recovery'), rowT('Fire Resistance')];
          window._cbCommit(function(b){ b.level = 3; }); OUT.q3 = [rowT('Faster Hit Recovery'), rowT('Fire Resistance')];
        """)
        self.assertEqual(out["tip"], [["d2t-p", "+5% Faster Hit Recovery"], ["d2t-p", "All Resistances +5"]])
        for L in ("l1", "l28"):
            self.assertEqual(out[L]["fire"][:2], [{"min": -70, "max": -70}, "EXACT"])
            self.assertIn("Faster Hit Recovery0%EXACT9 frames. +7% more reaches the next step.", out[L]["fhr"])
            self.assertTrue(any("needs level 29" in n for n in out[L]["note"]), out[L]["note"])
        self.assertEqual(out["l29"]["fire"][:2], [{"min": -65, "max": -65}, "EXACT"])
        self.assertEqual(out["l29"]["cold"][:2], [{"min": -65, "max": -65}, "EXACT"])
        self.assertIn("Faster Hit Recovery5%EXACT9 frames. +2% more reaches the next step.", out["l29"]["fhr"])
        self.assertEqual(out["l29"]["note"], [])
        self.assertEqual(out["b1"][0], "Fire Resistance−70%EXACTcap 75%")
        self.assertEqual(out["b4"][0], "Fire Resistance−65%EXACTcap 75%")
        self.assertIn("Faster Hit Recovery0%EXACT", out["b4"][1])
        self.assertTrue(out["qa"])
        self.assertIn("Faster Hit Recovery0%EXACT", out["q1"][0])
        self.assertIn("Faster Hit Recovery10%EXACT8 frames. +5% more reaches the next step.", out["q3"][0])
        self.assertEqual(out["q3"][1], "Fire Resistance−70%EXACTcap 75%")

    def test_the_warlocks_charms_both_reach_the_item_list(self):
        out = _run(GROUP + r"""
          mk('Warlock', 88); hell();
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('u436'); window._cbClosePick();
          window._cbOpenPick('inv', null, [2, 0]); window._cbChoose('b:cm1'); window._cbQuality('m'); window._cbAddMod('p234'); window._cbClosePick();
          var eb = window._cbEngineBuild(cur()); OUT.inv = eb.build.inv.map(function(x){ return x.name; });
          var sh = eng(); OUT.ar = rowOf(sh, 'ar'); OUT.fire = rowOf(sh, 'res-fire');
        """)
        self.assertEqual(out["inv"], ["Renewed Bone Break", "Bronze Small Charm"], "a charm in the inventory never reached the engine")
        self.assertIn("Bronze Small Charm (Bronze) +2..4 untouched roll", out["ar"][2])
        self.assertEqual(out["fire"][:2], [{"min": -70, "max": -70}, "EXACT"],
                         "a Bronze charm (attack rating only) cannot move fire resistance - -70 EXACT is the right answer")


RED_PROOF = [
    {"why": "v3886 - an unpicked property-group row is UNKNOWN again: his Paladin's FHR reads UNKNOWN beside a Renewed Bone Break",
     "file": "bible.html",
     "find": "      if (mode === 2 && opts.length){\n        var seen = {}, bad = false,",
     "replace": "      if (false){\n        var seen = {}, bad = false,",
     "matches": 1, "needs": "node"},
    {
        "why": "#166 - a property group line is rendered as its rows; without the dispatch it prints its own placeholder",
        "file": "bible.html",
        "find": "    if (line && line[2] === 4) return _cbGroupHtml(line, rolls, clvl, mode, slot);   /* #166 (REG-1868) a property group */\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#166 - the engine sums a group's picked row; without the dispatch the group is an unmapped line and FHR reads 0 EXACT",
        "file": "bible.html",
        "find": "      if (!fs && D.pgroups && Object.prototype.hasOwnProperty.call(D.pgroups, code)){ group(l, ctx); return; }\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#166 - the row he picked is summed; ignoring the pick leaves every group UNKNOWN",
        "file": "bible.html",
        "find": "      var o = (mode === 2 && pk && typeof pk.o === 'number') ? opts[pk.o] : null;\n",
        "replace": "      var o = null;\n",
        "matches": 1,
    },
    {
        "why": "#166 - the builder hands the engine which row rolled; without it the picked FHR never reaches the sheet",
        "file": "bible.html",
        "find": "      (out.picks = out.picks || {})[l[3]] = { o: pk, v: v };\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#166 - the tooltip prints the picked row; without the expansion it still says 'one of'",
        "file": "bible.html",
        "find": "    it = _cbExpandPicks(it, e && e.rolls);   /* #166 (REG-1868) — a picked property group is its row's own lines */\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#166 - a new row for a group drops the old row's value; keeping it sums 18 under a row that rolls 5-10",
        "file": "bible.html",
        "find": "    _cbCommit(function(b){ var e = _cbCur(b); if (!e) return; e.rolls = e.rolls || {}; delete e.rolls[key];\n",
        "replace": "    _cbCommit(function(b){ var e = _cbCur(b); if (!e) return; e.rolls = e.rolls || {};\n",
        "matches": 1,
    },
    {
        "why": "#29(b) 2026-09-28 - the cap chip reads as a comparison again ('≤75%'), not the cap he asked for ('cap 75%')",
        "file": "bible.html",
        "find": "'\">cap ' + esc(span(cp.min, cp.max)) + '</em>' : '') + '</span>' + _cbBpHtml(eng, r.bp, r.key, r, b) + _cbResParts(r) + '</div>';",
        "replace": "'\">≤' + esc(span(cp.min, cp.max)) + '</em>' : '') + '</span>' + _cbBpHtml(eng, r.bp, r.key, r, b) + _cbResParts(r) + '</div>';",
        "matches": 1,
    },
    {
        "why": "#29(b) 2026-09-28 - a max-resistance row loses its sign and reads as a resistance of its own ('0%')",
        "file": "bible.html",
        "find": "          if (/^res-[a-z]+-max$/.test(String(r.key || '')) && r.value.min >= 0) v = '+' + v;\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#29(b) 2026-09-28 - the max-resistance row is labelled 'Maximum Fire Resistance' again",
        "file": "bible.html",
        "find": "    ['res-fire-max', 'Max Fire Resistance', 'resistances', '%', 'maxfireresist'],\n",
        "replace": "    ['res-fire-max', 'Maximum Fire Resistance', 'resistances', '%', 'maxfireresist'],\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - a runeword is born at its base's max + 1 again (Chains of Honor 892, above the data)",
        "file": "bible.html",
        "find": "        if (hasEd && (it[2] === 'u' || it[2] === 's' || isBase)){ lo = hi = b[9] + 1; }\n",
        "replace": "        if (hasEd){ lo = hi = b[9] + 1; }\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - every per-level line divided by 8 again (Eaglehorn's attack rating a quarter of itself)",
        "file": "bible.html",
        "find": "  function _cbLvl(r){ return { lo: r[1], hi: r[3] == null ? r[1] : r[3], sh: Math.pow(2, r[4] == null ? 3 : r[4]) }; }",
        "replace": "  function _cbLvl(r){ return { lo: r[1], hi: r[3] == null ? r[1] : r[3], sh: 8 }; }",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - the engine files +% max damage per level under Enhanced Damage again (Hellslayer ED 340)",
        "file": "bible.html",
        "find": "    if (pl[0] === 'maxdamage') return 'item_maxdamage_percent';\n",
        "replace": "    if (pl[0] === 'maxdamage') return 'damagepercent';\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - the tooltip drops Enhanced Maximum Damage from the weapon's maximum (Hellslayer 98-274)",
        "file": "bible.html",
        "find": "        var pLo = (edd ? edd[0] : 0), pHi = (edd ? edd[1] : 0), xLo = pLo + (emd ? emd[0] : 0), xHi = pHi + (emd ? emd[1] : 0);",
        "replace": "        var pLo = (edd ? edd[0] : 0), pHi = (edd ? edd[1] : 0), xLo = pLo, xHi = pHi;",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - Hellfire Torch's class roll prints as a skill number again ('+0-7')",
        "file": "bible.html",
        "find": "        return cc ? esc(cc.n) : 'one random class\\'s';\n",
        "replace": "        return r[1] + '-' + r[3];\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - a class-locked item worn by another class is summed again (Herald on a Sorceress)",
        "file": "bible.html",
        "find": "        if (cls && lock.id !== cls.id){ res.notApplied.push({",
        "replace": "        if (false){ res.notApplied.push({",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - the tooltip stops marking another class's item red",
        "file": "bible.html",
        "find": "        out.only = { t: d.cls[oc].only || ('(' + d.cls[oc].n + ' Only)'), cls: d.cls[oc].n, bad: bi >= 0 && bi !== oc };",
        "replace": "        out.only = { t: d.cls[oc].only || ('(' + d.cls[oc].n + ' Only)'), cls: d.cls[oc].n, bad: false };",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - a set bonus with no switch prints a count the table never gave",
        "file": "bible.html",
        "find": "        + (af === 2 ? ' (' + (l[4] || 2) + ' items)' : af === 1 ? ' (with a certain other piece)' : ' (when: not in the tables)'), cls: 'd2t-set' }); });",
        "replace": "        + ' (' + (l[4] || 2) + ' items)', cls: 'd2t-set' }); });",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - a magic charm makes every row UNKNOWN again (its affix pool ignored)",
        "file": "bible.html",
        "find": "        return { name: nm, kind: 'affixed', q: q, code: baseCode, base: D.bases[baseCode], own: [], lvlreq: D.bases[baseCode][7] };\n",
        "replace": "        return { name: nm, kind: null, why: nm + ' is ' + q + ' - its own roll' };\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - an UNKNOWN row hides the part that is known again (a bare UNKNOWN beside a real sum)",
        "file": "bible.html",
        "find": "v = kr ? span(kr.min, kr.max) + ' + ?' : ''; }",
        "replace": "v = ''; }",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 integration - the builder hands its one-letter quality to the engine again, so every row reads UNKNOWN",
        "file": "bible.html",
        "find": "var CB_ENGINE_Q = { u: 'unique', s: 'set', r: 'runeword', c: 'crafted', b: 'base', m: 'magic', rare: 'rare', sup: 'superior', low: 'low' };",
        "replace": "var CB_ENGINE_Q = {};",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 integration - a typed roll is handed over under the builder's column key, so the engine sums its range",
        "file": "bible.html",
        "find": "if (hit && !used[hit.k]){ used[hit.k] = 1; out.rolls[hit.k] = typed[k]; }",
        "replace": "if (hit && !used[hit.k]){ used[hit.k] = 1; out.rolls[k] = typed[k]; }",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 integration - a roll the engine does not share a range with is guessed onto its line",
        "file": "bible.html",
        "find": "        var fits = function(t){ return t.rolled && Math.min(t.min, t.max) === me.lo && Math.max(t.min, t.max) === me.hi; };\n",
        "replace": "        var fits = function(t){ return t.rolled; };\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 integration - the Rainbow Facets reach the engine without their table *ID and none resolves",
        "file": "bible.html",
        "find": "      out.uid = it[0].slice(1);\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 integration - STATS drops the cap the game holds a stat to",
        "file": "bible.html",
        "find": "          + (cp && r.value ? '<em class=\"cb-cap\" aria-label=\"capped at ' + esc(span(cp.min, cp.max)) + '\">cap ' + esc(span(cp.min, cp.max)) + '</em>' : '') + '</span>' + _cbBpHtml(eng, r.bp, r.key, r, b) + _cbResParts(r) + '</div>';",
        "replace": "          + '</span>' + _cbBpHtml(eng, r.bp, r.key, r, b) + _cbResParts(r) + '</div>';",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 integration - STATS drops the unit, so 45 reads as a count, not a percent",
        "file": "bible.html",
        "find": "        var span = function(a, z){ return a === z ? sn(a) + u : (sn(a) + (a < 0 || z < 0 ? ' to ' : '–') + sn(z) + u); };",
        "replace": "        var span = function(a, z){ return a === z ? sn(a) : (sn(a) + (a < 0 || z < 0 ? ' to ' : '–') + sn(z)); };",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 integration - the engine is told nothing about the active set, so Set 2 sums Set 1",
        "file": "bible.html",
        "find": "return { name: b.name, cls: b.cls, level: b.level, sets: sets, activeSet: act, set: act, slots: cur.slots, inv: cur.inv };",
        "replace": "return { name: b.name, cls: b.cls, level: b.level, sets: sets, slots: cur.slots, inv: cur.inv };",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 integration - STATS no longer says which typed roll the engine was not handed",
        "file": "bible.html",
        "find": "      var notes = lost.map(function(x){ return 'not handed to the engine, so its range is summed: ' + x; })\n",
        "replace": "      var notes = [].map(function(x){ return x; })\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 integration - a vault name with its nickname ('Harlequin Crest (Shako)') opens no item",
        "file": "bible.html",
        "find": "    var tries = [name, bare(name)], paren = /\\(([^()]*)\\)\\s*$/.exec(String(name || ''));\n",
        "replace": "    var tries = [name], paren = /\\(([^()]*)\\)\\s*$/.exec(String(name || ''));\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 integration - a runeword with no base on record borrows its first base's defense",
        "file": "bible.html",
        "find": "          e.base = bc.length === 1 && window._cbBasesOf(it).indexOf(bc[0]) >= 0 ? bc[0] : '';\n",
        "replace": "          e.base = bc.length === 1 ? bc[0] : window._cbBasesOf(it)[0];\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 integration - the in-game box ignores its floor and rises over the mule window's header",
        "file": "bible.html",
        "find": '    if (r.top - th - g >= floor) return',
        "replace": '    if (r.top - th - g >= 8) return',
        "matches": 1,
    },
    {
        "why": "#174 v-B2 integration - the board's item card opens over the mule window's in-game box again (two boxes)",
        "file": "bible.html",
        "find": "      try { if (window.D2TIP_OWNS && window.D2TIP_OWNS(e.target)) return; } catch (_e) {}\n",
        "replace": "",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
