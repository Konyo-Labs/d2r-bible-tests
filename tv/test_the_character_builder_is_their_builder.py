# -*- coding: utf-8 -*-
"""#174 v-B2 — THE CHARACTER BUILDER IS THEIR BUILDER: THE ENTIRE DATABASE, THEIR PICKER, EVERY ROLL HONEST.

His words (2026-09-25): "if i click on helmet lets say.. it shold give me the options from the entire database to
put as a helmet or runeword and based on the base item.. exactly like the d2r one to one", and "the mules are mules
and continue to be so the items coming in dont mix up this... this is just a simple tool for character building".

This law drives the SHIPPED builder — the ⟦CHARACTER BUILDER JS⟧ block, the ⟦CB_DB⟧ block tv/char_builder_db.py
generated from his install, the board's own CHARS, LSR and fork sets, and the Backup exporter, each CUT from
bible.html between two real boundaries and run in node over a small DOM stand-in (never re-typed here):

  · THE RAIL AND THE TABS ARE THE DATA'S, PER SLOT. The helm's rail is their Helmets · Circlets · Pelts (Druid) ·
    Primal Helms (Barbarian), from itemtypes.txt's own UI categories and class locks; every base the game wears on
    the head sits under one of them. A quality tab shows only when the data holds something for it: gloves have NO
    Runewords tab (no runeword names a glove type), exactly as theirs (06_gloves_filters). The list is the ENTIRE
    database for the slot: every unique, set item, runeword and base the tables put there, not a sample.
  · A RUNEWORD'S BASES CARRY THE SOCKET COUNT. Enigma (Jah Ith Ber) is offered only on body armor that can hold 3
    sockets — Mage Plate yes (3), Quilted Armor no (2) — and Spirit (4 runes, swords and shields) on a Crystal Sword
    and a Monarch, never a Short Sword (2 sockets) and never an axe. The runeword's sockets are its runes, locked.
  · A ROLL IS A BOX CLAMPED TO ITS RANGE. Crown of Ages rolls All Resistances 20-30 (uniqueitems.txt res-all 20 30):
    typed 28 is stored EXACT under the game's own key (p2 = prop2), 35 is REFUSED and nothing is saved, a blank box
    is the range again. Hand-checked Defense: Corona's max defense is 165 (armor.txt), an item with Enhanced
    Defense rolls its base at max + 1 = 166, x 1.5 (its +50% ED) = 249, + its 100-150 flat => untouched 349-399
    (a RANGE, never averaged), typed 150 => exactly 399 — their tooltip's number (05_hover_equipped).
  · THE STORE IS THE BRIEF'S SHAPE, FORKED PER ACCOUNT, IN BACKUP & SHARE: d2r_charBuilds {buildId: {name, cls,
    level, sets: [{name: 'Set 1', slots: {slot: {name, base, sockets, eth, rolls, socketed}}}]}} through LSR; on the
    ladder profile it is L·d2r_charBuilds; _collectProgress exports it.
  · Esc CLOSES THE TOP LAYER FIRST: the picker, then the builder — through the document's capture-phase listener,
    the same way the console's Esc probe arrives.
  · IT READS NO VAULT STORE. A whole session — open, pick, roll, an inventory charm, the stash, close — reads only
    d2r_charBuilds and its own selection key, and calls no vault or mule function (his rule: the items coming in
    do not mix with this).
  · THE TOOLTIP'S COLOUR MAP IS SPEC §8. unique rgb(199,179,119) · set rgb(0,255,0) · crafted rgb(255,168,0) ·
    base white · magic and every property rgb(105,105,255) · a failed requirement rgb(255,77,77) on rgba(8,8,8,.95)
    with 6px 9px padding — read out of the SHIPPED stylesheet — and a requirement is red only when the character is
    KNOWN to fail it: the level is the build's, strength and dexterity are UNKNOWN and never red on a guess.
  · CRAFTED IS THE GAME'S CUBE, WITNESSED BY THE BOARD: every craft the board's CRAFTS names (Caster / Blood / Safety
    / Hit Power x its nine slots) is a crafted recipe in the database, by the game's own name.
  · THE BLOCK IS THE COMMITTED TABLES' WORDS: every base, unique, set item and runeword name in ⟦CB_DB⟧ is the name
    tv/item_tables.json carries for the same code / id / key — checked here without an install. Whether the block
    is what the install says TODAY is tv/char_builder_db.py's --check (UNKNOWN, never green, without an install).

#174 v-B2 FIX ROUND — what the review and pixel seats measured, now held here:
  · THE PARENT LIST IS THE BUILD'S CLASS: a Sorceress's "Helmets" holds no pelt and no primal helm (theirs,
    01_helm_clicked); the Pelts (Druid) rail still lists its own; a build with no class keeps the whole database.
  · SOCKETS ARE WHAT THIS ITEM MAY HOLD: Crown of Ages' own line is Socketed 1-2 - the stepper is 1..2 and it IS that
    roll (typed 2 in either place -> two sockets to fill); another unique or set item takes 0..1 (Larzuk); a base its
    gemsockets band (Archon Plate 0..4).
  · THEIR INVENTORY'S All Items IS CHARMS (a jewel under Miscellaneous), and the stash tree carries Jewels > Colossal
    Jewels and the weapons in the game's own groups (itemtypes 'mele' / 'miss'), each parent folding.
  · TWO LINES OF COPY: EXACT is "fixed by the table, or typed" (a table's fixed value is EXACT too), and breakpoints are
    STILL OWED (the stats engine is wired; the frame tables are not built).
  · THE PICKER'S BLOCK IS WHAT THE INSTALL SAYS, WHERE THE INSTALL IS: tv/char_builder_db.py --check re-derives it
    (UNMEASURED, never passed, without an install) - and the shipped block itself carries the fix-round shapes a CI
    runner can read: every per-level line ["L", lo, key, hi, shift] (Fortitude hp/lvl 8..12 shift 3, Eaglehorn att/lvl
    12 shift 1), Hellfire Torch's class roll ["C", 0, key, 7], Guardian Angel's four maximum resistances.
  · ITS DOCTOR ROW: 'builder item data' - OK / MISSING (stale) / UNKNOWN (no install, never OK), registered, periodic,
    declared and explained (the picker's block had no row while its sibling 'character sheet data' had one).

⚠ WHAT THIS LAW CANNOT SEE: pixels — that is test_the_character_builder_fits_at_every_width.py, in a real browser.
RED_PROOF below.
"""
import io
import json
import os
import re
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

# ⚠ REG-1561 — the stand-in lives in tv/cb_node_harness.py now (a production lane runs it on the console's
# own cadence); every name below is RE-EXPORTED here so the nine laws that import this module keep ONE
# harness rather than a copy. NODE resolves by env, PATH, then the known install locations. [[copy-drift]]
from cb_node_harness import (NODE, BIBLE, HARNESS, _src, _between, _builder_js, _builder_css,  # noqa: E402,F401
                             _db_json, _stage, _run, _db)


@unittest.skipIf(NODE is None, "node is not on this machine")
class TheBuilderIsTheirBuilder(unittest.TestCase):

    def test_the_rail_and_the_tabs_come_from_the_data_per_slot(self):
        out = _run(r"""
          window.openCharBuilder();
          OUT.head = window._cbRailOf('head').map(function(r){ return [r[0], r[1], r[2] >= 0 ? window._cbDb().cls[r[2]].n : null]; });
          OUT.headTabs = window._cbQTabs('head').map(function(t){ return t[0]; });
          OUT.glovTabs = window._cbQTabs('glov').map(function(t){ return t[0]; });
          OUT.invRail = window._cbRailOf('inv').map(function(r){ return r[0]; });
          OUT.invTabs = window._cbQTabs('inv').map(function(t){ return t[0]; });
          /* the ENTIRE database is what a build with no class is offered; a class's build is offered its own */
          window._cbCommit(function(b){ b.cls = null; });
          OUT.headN = window._cbForSlot('head').length;
          OUT.headQ = {}; window._cbForSlot('head').forEach(function(x){ OUT.headQ[x[2]] = (OUT.headQ[x[2]] || 0) + 1; });
          OUT.headNames = window._cbForSlot('head').map(function(x){ return x[1]; });
          /* #174 v-B2 fix round - a Sorceress's "Helmets" lists no pelt and no primal helm (theirs, 01_helm_clicked);
             the class rails still list their own */
          window._cbCommit(function(b){ b.cls = 'Sorceress'; });
          OUT.sorcHead = window._cbForSlot('head').map(function(x){ return x[1]; });
          OUT.sorcPelts = window._cbForSlot('head', 2).map(function(x){ return x[1]; });
          window._cbCommit(function(b){ b.cls = 'Druid'; });
          OUT.druidPelts = window._cbForSlot('head', 2).map(function(x){ return x[1]; });
          window._cbCommit(function(b){ b.cls = 'Sorceress'; });
          OUT.sorcRarm = window._cbForSlot('rarm').map(function(x){ return x[1]; });
          OUT.sorcLarm = window._cbForSlot('larm').map(function(x){ return x[1]; });
          OUT.glovNames = window._cbForSlot('glov').map(function(x){ return x[1]; });
          OUT.rwForGloves = window._cbForSlot('glov').filter(function(x){ return x[2] === 'r'; }).length;
        """)
        self.assertEqual(out["head"], [["Helmets", -1, None], ["Circlets", 1, None], ["Pelts", 2, "Druid"],
                                       ["Primal Helms", 3, "Barbarian"]],
                         "the helm's rail is not their Helmets / Circlets / Pelts (Druid) / Primal Helms: %s" % out["head"])
        self.assertEqual(out["headTabs"], ["all", "r", "u", "b", "c", "s", "ex"])
        self.assertEqual(out["glovTabs"], ["all", "u", "b", "c", "s", "ex"],
                         "gloves show a Runewords tab although no runeword names a glove type")
        self.assertEqual(out["rwForGloves"], 0)
        self.assertEqual(out["invRail"], ["Inventory", "Small Charms", "Large Charms", "Grand Charms",
                                          "Crafted Sunder Charms"])
        self.assertEqual(out["invTabs"], ["all", "u", "b", "m", "ex"])
        # THE ENTIRE DATABASE: every head base the block holds (spawnable), every unique / set on one, every crafted
        # helm and every runeword a helm can carry — derived here from the block's own tables, not a hand list
        db = _db()
        head_types = set()
        for row in db["rail"]["head"]:
            head_types |= set(row[1])
        want = set(b[0] for c, b in db["b"].items() if b[20] and b[1] in head_types)
        want |= set(x[1] for x in db["it"] if x[2] in ("u", "s") and db["b"].get(x[3], [None, None])[1] in head_types)
        self.assertEqual(set(out["headNames"]) & want, want, "the helm list is missing: %s" % sorted(want - set(out["headNames"]))[:10])
        for n in ("Crown of Ages", "Harlequin Crest", "Arreat's Face", "Jalal's Mane", "Tal Rasha's Horadric Crest",
                  "Corona", "Circlet", "Caster Helm", "Lore", "Dream"):
            self.assertIn(n, out["headNames"], "%s is not offered for the helm" % n)
        for n in ("The Stone of Jordan", "Windforce", "Enigma", "Stormshield"):
            self.assertNotIn(n, out["headNames"], "%s is offered for the helm" % n)
        self.assertGreater(out["headQ"].get("r", 0), 5, "helm runewords (Lore, Dream, ...) are missing: %s" % out["headQ"])
        self.assertIn("Magefist", out["glovNames"])
        # #174 v-B2 fix round - THE PARENT LIST IS THE BUILD'S CLASS: every item whose every base is another class's
        # (itemtypes.txt Class, the block's own ty table) is left out of a Sorceress's parent list, the rest stays
        ci = [c["n"] for c in db["cls"]].index("Sorceress")
        def locked_elsewhere(x):
            bs = [x[3]] if x[2] in ("u", "s", "b", "m") else []
            return bool(bs) and all(db["ty"][db["b"][c][1]][2] not in (-1, ci) for c in bs if c in db["b"])
        other = set(x[1] for x in db["it"] if x[2] in ("u", "s") and db["b"].get(x[3], [None, None])[1] in head_types
                    and locked_elsewhere(x))
        other |= set(b[0] for c, b in db["b"].items() if b[20] and b[1] in head_types and db["ty"][b[1]][2] not in (-1, ci))
        self.assertGreaterEqual(len(other), 30, "PRINT THE DENOMINATOR: the block holds too few class-locked helms: %d" % len(other))
        self.assertEqual(sorted(other & set(out["sorcHead"])), [], "a Sorceress's Helmets lists another class's helms")
        self.assertEqual(sorted((want - other) - set(out["sorcHead"]))[:10], [],
                         "the class filter dropped a helm a Sorceress can wear")
        for n in ("Arreat's Face", "Jalal's Mane"):
            self.assertIn(n, out["headNames"], "%s left the class-less list" % n)
            self.assertNotIn(n, out["sorcHead"], "%s is offered to a Sorceress" % n)
        # v3885 (#136, his 11-08 "druid helm for druids.. necromancer also has their style.. amazons") - the Pelts (Druid)
        # rail lists its pelts to a Druid and NOTHING to a Sorceress (it was #174 v-B2's "the class rails still list their own")
        self.assertIn("Jalal's Mane", out["druidPelts"], "the Pelts (Druid) rail no longer lists a Druid's own pelts")
        # a runeword a pelt OR any helm can hold (Lore, Delirium) stays - its Base tab lists only the helms she can wear;
        # every pelt and every Druid-only unique leaves
        self.assertEqual(sorted(other & set(out["sorcPelts"])), [], "the Pelts (Druid) rail offers a Sorceress what she cannot wear")
        self.assertNotIn("Jalal's Mane", out["sorcPelts"])
        for n in ("Bartuc's Cut-Throat", "Herald of Zakarum"):
            self.assertNotIn(n, out["sorcRarm"] + out["sorcLarm"], "%s (another class's) is offered to a Sorceress" % n)
        self.assertIn("Crown of Ages", out["sorcHead"])
        self.assertIn("Eschuta's Temper", out["sorcRarm"], "a Sorceress's own orb left her weapon list")

    def test_a_runewords_bases_carry_its_socket_count(self):
        out = _run(r"""
          window.openCharBuilder();
          var d = window._cbDb(), byName = function(n){ var h = null; d.it.forEach(function(x){ if (x[1] === n) h = x; }); return h; };
          var names = function(it){ return window._cbBasesOf(it).map(function(c){ return d.b[c][0]; }); };
          var en = byName('Enigma'), sp = byName('Spirit');
          OUT.enigma = names(en); OUT.spirit = names(sp);
          OUT.enigmaRunes = en[7].runes.length; OUT.spiritRunes = sp[7].runes.length;
          OUT.minSockEnigma = Math.min.apply(null, window._cbBasesOf(en).map(function(c){ return window._cbMaxSock(c, 99); }));
          OUT.minSockSpirit = Math.min.apply(null, window._cbBasesOf(sp).map(function(c){ return window._cbMaxSock(c, 99); }));
          OUT.entry = window._cbEntryFor(en);
          OUT.quilted = window._cbMaxSock('qui', 99); OUT.mage = window._cbMaxSock('xtp', 99);
        """)
        self.assertEqual((out["enigmaRunes"], out["spiritRunes"]), (3, 4))
        self.assertIn("Mage Plate", out["enigma"])
        self.assertIn("Archon Plate", out["enigma"])
        self.assertNotIn("Quilted Armor", out["enigma"], "Enigma offered on a 2-socket Quilted Armor")
        self.assertEqual((out["quilted"], out["mage"]), (2, 3), "armor.txt's socket counts moved")
        self.assertGreaterEqual(out["minSockEnigma"], 3)
        self.assertIn("Crystal Sword", out["spirit"])
        self.assertIn("Monarch", out["spirit"])
        self.assertNotIn("Short Sword", out["spirit"], "Spirit offered on a 2-socket Short Sword")
        self.assertFalse(any("Axe" in n for n in out["spirit"]), "Spirit offered on an axe: %s" % out["spirit"])
        self.assertGreaterEqual(out["minSockSpirit"], 4)
        self.assertEqual((out["entry"]["sockets"], len(out["entry"]["socketed"])), (3, 3), out["entry"])

    def test_a_roll_is_clamped_to_its_range_and_typed_is_exact(self):
        out = _run(r"""
          window.openCharBuilder();
          window._cbOpenPick('slot', 'head');
          var d = window._cbDb(), coa = null; d.it.forEach(function(x){ if (x[1] === 'Crown of Ages') coa = x; });
          window._cbChoose(coa[0]);
          OUT.pure = [window._cbRoll([20, 30], '25'), window._cbRoll([20, 30], '35'), window._cbRoll([20, 30], ''), window._cbRoll([20, 30], 'x2')];
          var box = function(k, lo, hi, v){ var cls = {}; return { value: v, classList: { contains: function(c){ return c === 'cb-roll' || !!cls[c]; }, add: function(c){ cls[c] = 1; }, remove: function(c){ delete cls[c]; }, toggle: function(c, on){ if (on) cls[c] = 1; else delete cls[c]; } },
            getAttribute: function(a){ return { 'data-key': k, 'data-lo': String(lo), 'data-hi': String(hi) }[a]; }, bad: function(){ return !!cls['cb-bad']; } }; };
          var tip = function(){ var e = slots().sets[0].slots.head; return window._cbTipEntry(e, window._cbItem(e.id), 88, 'head'); };
          OUT.untouched = tip().defense;
          var b1 = box('p2', 20, 30, '35'); window._cbRollInput({ target: b1 }); OUT.refused = [b1.bad(), JSON.stringify(slots().sets[0].slots.head.rolls)];
          var b2 = box('p2', 20, 30, '28'); window._cbRollInput({ target: b2 }); OUT.typed = slots().sets[0].slots.head.rolls;
          var b3 = box('p4', 100, 150, '150'); window._cbRollInput({ target: b3 }); OUT.defense = tip().defense;
          OUT.resLine = tip().lines.map(function(l){ return l.html; }).filter(function(h){ return /All Resistances/.test(h); })[0];
          var b4 = box('p2', 20, 30, ''); window._cbRollInput({ target: b4 }); OUT.cleared = slots().sets[0].slots.head.rolls;
          OUT.resAfter = tip().lines.map(function(l){ return l.html; }).filter(function(h){ return /All Resistances/.test(h); })[0];
        """)
        ok, bad, blank, junk = out["pure"]
        self.assertEqual(ok, {"ok": True, "v": 25})
        self.assertFalse(bad["ok"])
        self.assertIn("20–30", bad["why"])
        self.assertEqual(blank, {"ok": True, "v": None})
        self.assertFalse(junk["ok"])
        # hand-checked: Corona max 165 -> ED base 166 -> x1.5 = 249 -> + 100..150
        self.assertEqual(out["untouched"], [349, 399], "an untouched Crown of Ages must read the RANGE 349-399")
        self.assertEqual(out["refused"], [True, "{}"], "a roll outside 20-30 was saved: %s" % out["refused"])
        self.assertEqual(out["typed"], {"p2": 28})
        self.assertEqual(out["defense"], [399, 399], "typed 150 must make Defense exactly 399 (their tooltip)")
        self.assertEqual(out["resLine"], "All Resistances +28")
        self.assertEqual(out["cleared"], {"p4": 150})
        self.assertEqual(out["resAfter"], "All Resistances +20-30", "a cleared box must be the range again, never a default")

    def test_the_store_is_the_brief_shape_forked_and_backed_up(self):
        out = _run(_LEARNED_ON_THIS_CONSOLE + r"""
          window.openCharBuilder();
          window._cbOpenPick('slot', 'head');
          var d = window._cbDb(), pick = function(n){ var h = null; d.it.forEach(function(x){ if (x[1] === n) h = x; }); return h[0]; };
          window._cbChoose(pick('Crown of Ages'));
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose(pick('Annihilus'));
          OUT.main = Object.keys(RAW).filter(function(k){ return /charBuilds/.test(k); });
          OUT.build = slots();
          OUT.backup = Object.keys(_collectProgress()).filter(function(k){ return /charBuilds/.test(k); });
          OUT.forked = window._LP_FORKED.has('d2r_charBuilds');
          var mainBefore = RAW['d2r_charBuilds'];
          window.D2R_PROFILE = 'ladder';
          OUT.ladderSees = Object.keys(window._cbAll()).length;
          window._cbOpenNew(); window._cbNewCls('Sorceress'); window._cbNewGo();
          OUT.ladder = Object.keys(RAW).filter(function(k){ return /charBuilds/.test(k); }).sort();
          OUT.mainUntouched = RAW['d2r_charBuilds'] === mainBefore;
          OUT.ladderBackup = Object.keys(_collectProgress()).filter(function(k){ return /charBuilds/.test(k); });
          OUT.ladderBackupIsLadder = JSON.parse(_collectProgress()['d2r_charBuilds'] || '{}');
        """)
        self.assertTrue(out["forked"], "d2r_charBuilds is not in _LP_FORKED")
        self.assertEqual(out["main"], ["d2r_charBuilds"])
        b = out["build"]
        for k, t in (("name", str), ("cls", str), ("level", int), ("sets", list)):
            self.assertIsInstance(b.get(k), t, "build.%s: %r" % (k, b.get(k)))
        self.assertEqual((b["cls"], b["level"]), ("Warlock", 88),
                         "the first template is the character THIS console's reels learned (Konyolock, Warlock 88)")
        self.assertEqual(b["sets"][0]["name"], "Set 1")
        e = b["sets"][0]["slots"]["head"]
        for k, t in (("name", str), ("base", str), ("sockets", int), ("eth", bool), ("rolls", dict), ("socketed", list)):
            self.assertIsInstance(e.get(k), t, "slot.%s: %r" % (k, e.get(k)))
        self.assertEqual((e["name"], e["base"]), ("Crown of Ages", "urn"))
        inv = b["sets"][0]["inv"]
        self.assertEqual([(i["name"], i["x"], i["y"], i["w"], i["h"]) for i in inv], [("Annihilus", 0, 0, 1, 1)])
        self.assertEqual(out["backup"], ["d2r_charBuilds"], "Backup & Share does not carry the builds")
        self.assertEqual(out["ladderSees"], 0, "the ladder world sees the main world's builds")
        self.assertEqual(out["ladder"], ["L·d2r_charBuilds", "d2r_charBuilds"],
                         "on the ladder profile the builds did not fork: %s" % out["ladder"])
        self.assertTrue(out["mainUntouched"], "a ladder build changed the main world's builds")
        self.assertEqual(out["ladderBackup"], ["d2r_charBuilds"], "the ladder export must name the key bare")
        self.assertEqual([v["cls"] for v in out["ladderBackupIsLadder"].values()], ["Sorceress"],
                         "the ladder export must carry the ladder world's builds, not main's")

    def test_esc_closes_the_top_layer_first_then_the_builder(self):
        out = _run(r"""
          window.openCharBuilder();
          window._cbOpenPick('slot', 'head');
          OUT.before = [!!window._cbState().pick, window._cbState().open];
          OUT.stop1 = key('Escape');
          OUT.after1 = [!!window._cbState().pick, window._cbState().open];
          window._cbOpenStash();
          key('Escape');
          OUT.after2 = [!!window._cbState().stash, window._cbState().open];
          OUT.stop3 = key('Escape');
          OUT.after3 = [window._cbState().open, document.documentElement.classList.contains('cb-lock')];
          OUT.role = ELS['cb-win'].getAttribute('role');
        """)
        self.assertEqual(out["before"], [True, True])
        self.assertEqual(out["after1"], [False, True], "the first Esc must close the picker and leave the builder up")
        self.assertIn("stopped", out["stop1"], "the Esc reached other listeners on the board")
        self.assertEqual(out["after2"], [False, True], "Esc must close the stash before the builder")
        self.assertEqual(out["after3"], [False, False], "the last Esc must close the builder")
        self.assertEqual(out["role"], "dialog", "the console forwards Esc only into a [role=dialog]")

    def test_it_reads_no_vault_store_and_calls_no_mule(self):
        out = _run(r"""
          READS.length = 0;
          window.openCharBuilder();
          var d = window._cbDb(), pick = function(n){ var h = null; d.it.forEach(function(x){ if (x[1] === n) h = x; }); return h[0]; };
          window._cbOpenPick('slot', 'head'); window._cbChoose(pick('Crown of Ages'));
          window._cbOpenPick('slot', 'tors'); window._cbQt('ex'); window._cbQt('r'); window._cbChoose(pick('Enigma'));
          window._cbOpenPick('inv', null, [2, 1]); window._cbChoose(pick('Annihilus'));
          window._cbMove(0, 5, 2);
          window._cbOpenStash(); window._cbStashTab('create'); window._cbStashCat(1); window._cbStashAdd(pick('Harlequin Crest'));
          window._cbStashTab('stash'); window._cbStashCat(0);
          window._cbOpenNew(); window._cbNewCls('Sorceress'); window._cbNewGo();
          window._cbTipSlot({ getBoundingClientRect: El.prototype.getBoundingClientRect }, 'head');
          window.closeCharBuilder();
          OUT.reads = READS.filter(function(k, i){ return READS.indexOf(k) === i; });
          OUT.calls = CALLS;
          OUT.moved = slots() ? null : null;
          var all = JSON.parse(RAW['d2r_charBuilds']); OUT.nBuilds = Object.keys(all).length;
          OUT.anyInv = Object.keys(all).map(function(k){ return (all[k].sets[0].inv || []).map(function(e){ return [e.name, e.x, e.y]; }); });
          OUT.stash = Object.keys(all).map(function(k){ return (all[k].stash || []).map(function(e){ return e.name; }); });
        """)
        # #245 - the build dropdown reads d2r_cbMain (the MAIN build, set in the 👤 Characters tab) to lead with it.
        # Still an EXACT set, one key larger: d2r_cbMain is a pointer into d2r_charBuilds, the manual side's own
        # store, never a vault one - tv/test_the_characters_tab_is_manual_and_separate.py pins that side.
        self.assertEqual(sorted(out["reads"]), ["d2r_cbMain", "d2r_cbSel", "d2r_charBuilds"],
                         "the builder read a store that is not its own: %s" % out["reads"])
        self.assertEqual(out["calls"], [], "the builder called the vault / the mules: %s" % out["calls"])
        self.assertEqual(out["nBuilds"], 2)
        self.assertIn([["Annihilus", 5, 2]], out["anyInv"], "the inventory move did not stay: %s" % out["anyInv"])
        self.assertIn(["Harlequin Crest"], out["stash"])
        # and in the SOURCE: no vault store key, no mule function, anywhere in the block's code (comments stripped)
        js = _builder_js(_src())
        code = re.sub(r"/\*.{0,4000}?\*/", " ", js, flags=re.S)
        code = "\n".join(re.sub(r"(^|[^:'\"])//.*$", r"\1", l) for l in code.split("\n"))
        for bad in ("d2r_muleAssign", "d2r_muleRoster", "d2r_muleEquip", "d2r_owned", "d2r_foundLog", "d2r_vault",
                    "vaultAssign(", "openMuleCard(", "_muleLoad(", "tvVaultRegister("):
            self.assertNotIn(bad, code, "the builder's code names %s" % bad)

    def test_the_tooltip_colour_map_is_spec_8(self):
        css = _builder_css(_src())
        rules = {}
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.{0,4000}?\*/", " ", css, flags=re.S)):
            for sel in m.group(1).split(","):
                rules.setdefault(sel.strip(), []).append(m.group(2))

        def prop(sel, name):
            for body in rules.get(sel, []):
                mm = re.search(r"(?:^|;)\s*%s\s*:\s*([^;]+)" % re.escape(name), body)
                if mm:
                    return mm.group(1).strip()
            return None
        want = {".d2tip .d2t-u": "rgb(199,179,119)", ".d2tip .d2t-r": "rgb(199,179,119)", ".d2tip .d2t-s": "rgb(0,255,0)",
                ".d2tip .d2t-c": "rgb(255,168,0)", ".d2tip .d2t-b": "rgb(255,255,255)", ".d2tip .d2t-m": "rgb(105,105,255)",
                ".d2tip .d2t-rare": "rgb(255,255,100)", ".d2tip .d2t-p": "rgb(105,105,255)",
                ".d2tip .d2t-num": "rgb(105,105,255)", ".d2tip .d2t-w": "rgb(255,255,255)",
                ".d2tip .d2t-red": "rgb(255,77,77)"}
        got = dict((s, prop(s, "color")) for s in want)
        self.assertEqual(got, want)
        self.assertEqual(prop(".d2tip", "background"), "rgba(8,8,8,.95)")
        self.assertEqual(prop(".d2tip", "padding"), "6px 9px")
        # the picker's names: the same six quality colours, as custom properties of the window
        for k, v in (("--cb-q-unique", "rgb(199,179,119)"), ("--cb-q-set", "rgb(0,255,0)"), ("--cb-q-crafted", "rgb(255,168,0)"),
                     ("--cb-q-base", "rgb(255,255,255)"), ("--cb-q-magic", "rgb(105,105,255)"), ("--cb-q-rare", "rgb(255,255,100)")):
            self.assertEqual(prop(".cb-win", k), v, "%s is not %s" % (k, v))
        out = _run(r"""
          var e = function(q, lvl, clvl, str, attrs){ return window.d2Tip({ name: 'X', base: 'Y', q: q, reqs: { lvl: lvl, str: str }, clvl: clvl, attrs: attrs, lines: [{ t: 'a property' }] }); };
          OUT.q = ['u', 's', 'c', 'b', 'm', 'rare', 'r', 'unique', 'set'].map(function(q){ return /class="(d2t-[a-z]+)"/.exec(e(q, 1, 10))[1]; });
          OUT.lvlFail = /class="d2t-red">Required Level: 82/.test(e('u', 82, 80, 174, null));
          OUT.lvlOk = /class="d2t-w">Required Level: 82/.test(e('u', 82, 88, 174, null));
          OUT.strUnknown = /class="d2t-w">Required Strength: 174/.test(e('u', 82, 88, 174, null));
          OUT.strKnownFail = /class="d2t-red">Required Strength: 174/.test(e('u', 82, 88, 174, { str: 100 }));
          OUT.prop = /class="d2t-p">a property/.test(e('u', 1, 10));
        """)
        self.assertEqual(out["q"], ["d2t-u", "d2t-s", "d2t-c", "d2t-b", "d2t-m", "d2t-rare", "d2t-r", "d2t-u", "d2t-s"])
        self.assertTrue(out["lvlFail"], "a level-80 character is not told it fails a level-82 requirement in red")
        self.assertTrue(out["lvlOk"])
        self.assertTrue(out["strUnknown"], "strength is UNKNOWN, so its requirement must never be red on a guess")
        self.assertTrue(out["strKnownFail"], "a KNOWN strength below the requirement must be red")
        self.assertTrue(out["prop"])

    def test_stats_are_the_engines_with_their_source_or_all_unknown(self):
        """STATS draws window.D2R_CHAR_ENGINE.sheet(build, {difficulty, quests}) when it is loaded — each number with
        its source, a range as a range — and when it is not, every row is UNKNOWN and no number is drawn at all."""
        out = _run(_LEARNED_ON_THIS_CONSOLE + r"""
          window.openCharBuilder();
          var stats = function(){ var h = ELS['cb-win']._html; return h.slice(h.indexOf('id="cb-stats"'), h.indexOf('id="cb-modal"')); };
          var none = stats();
          OUT.noneSays = /the stats engine is not loaded/.test(none);
          OUT.noneNumbers = (none.match(/<b>[^<]*\d[^<]*<\/b>/g) || []);
          OUT.noneUnknown = (none.match(/<i>UNKNOWN<\/i>/g) || []).length;
          var seen = null;
          window.D2R_CHAR_ENGINE = { sheet: function(b, o){ seen = { cls: b.cls, level: b.level, head: b.slots && b.slots.head && b.slots.head.name, o: o };
            return { rows: [
              { key: 'res_fire', label: 'Fire Resistance', group: 'Resistances', value: { min: 20, max: 45 }, cap: 75, raw: { min: 20, max: 45 }, source: 'RANGE', why: 'rolls untouched' },
              { key: 'fhr', label: 'Faster Hit Recovery', group: 'Speed', value: { min: 30, max: 30 }, cap: null, raw: 30, source: 'EXACT', why: 'fixed' },
              { key: 'res_cold', label: 'Cold Resistance', group: 'Resistances', value: { min: 75, max: 75 }, cap: 75, raw: { min: 91, max: 91 }, source: 'EXACT', why: 'capped' },
              { key: 'str', label: 'Strength', group: 'Attributes', value: null, cap: null, raw: null, source: 'UNKNOWN', why: 'no attributes until a save is imported' } ] }; } };
          window._cbOpenPick('slot', 'head');
          var d = window._cbDb(), coa = null; d.it.forEach(function(x){ if (x[1] === 'Crown of Ages') coa = x; });
          window._cbChoose(coa[0]); window._cbClosePick();
          window._cbStatsOpt('diff', 'nightmare');
          var h = stats();
          OUT.seen = seen;
          OUT.range = /Fire Resistance<\/span><span class="cb-sv cb-sv-RANGE"[^>]*><b>20–45<\/b><i>RANGE<\/i>/.test(h);
          OUT.exact = /Faster Hit Recovery<\/span><span class="cb-sv cb-sv-EXACT"[^>]*><b>30<\/b><i>EXACT<\/i>/.test(h);
          OUT.capped = /Cold Resistance<\/span><span class="cb-sv cb-sv-EXACT"[^>]*><b>75 \(raw 91\)<\/b>/.test(h);
          OUT.unknown = /Strength<\/span><span class="cb-sv cb-sv-UNKNOWN" title="no attributes until a save is imported"><i>UNKNOWN<\/i>/.test(h);
          window.D2R_CHAR_ENGINE = { sheet: function(){ throw new Error('boom'); } };
          window._cbRender();
          OUT.threw = /the stats engine failed \(boom\)/.test(stats()) && !(stats().match(/<b>[^<]*\d[^<]*<\/b>/g) || []).length;
        """)
        self.assertTrue(out["noneSays"], "with no engine STATS does not say the engine is not loaded")
        self.assertEqual(out["noneNumbers"], [], "with no engine STATS drew a number: %s" % out["noneNumbers"])
        self.assertGreaterEqual(out["noneUnknown"], 20)
        self.assertEqual(out["seen"], {"cls": "Warlock", "level": 88, "head": "Crown of Ages",
                                       "o": {"difficulty": "nightmare", "quests": True,
                                             "bp": {"cls": "Warlock", "form": "", "weapon": "other",
                                                    "holyShield": False, "weaponWhy": "No weapon is worn."}}},
                         "the engine was not handed the build, its worn slots and the sheet's options: %s" % out["seen"])
        self.assertTrue(out["range"], "a RANGE row is not drawn as its range with its source")
        self.assertTrue(out["exact"], "an EXACT row is not drawn as its number with its source")
        self.assertTrue(out["unknown"], "an UNKNOWN row does not say UNKNOWN with its reason")
        self.assertTrue(out["capped"], "a capped row must show the raw sum the cap moved (75 (raw 91))")
        self.assertTrue(out["threw"], "an engine that throws must leave every row UNKNOWN, saying why")

    def test_crafted_is_the_games_cube_witnessed_by_the_boards_crafts(self):
        s = _src()
        crafts = _between(s, "const CRAFTS = [", "\n];")
        keys = re.findall(r"key:'([^']+)'", crafts)
        self.assertGreaterEqual(len(keys), 4, "the board's CRAFTS did not parse: %s" % keys)
        names = set(x[1] for x in _db()["it"] if x[2] == "c")
        missing = []
        for m in re.finditer(r"key:'([^']+)'.*?slots:\{(.*?)\}\s*\}", crafts, re.S):
            for q, w in re.findall(r"(?:'([^']+)'|\b([A-Z][a-z]+)\b):\{rune", m.group(2)):
                slot = q or w
                n = "%s %s" % (m.group(1), "Body" if slot == "Body Armor" else slot)
                if n not in names:
                    missing.append(n)
        self.assertEqual(missing, [], "the board names crafts the game's cube table does not hold: %s" % missing)
        self.assertEqual(len(names), 36)

    def test_the_block_speaks_the_committed_tables_words(self):
        import item_tables as IT
        t = IT.load()
        self.assertTrue(t, "tv/item_tables.json is missing")
        db = _db()
        self.assertEqual(len(db.get("sourceHash") or ""), 64, "the block carries no sourceHash")
        bad = []
        for code, b in db["b"].items():
            it = (t["items"].get(code) or {}).get("name")
            if it != b[0] and b[20]:
                # a spawnable base renamed apart from a twin (the Colossal Jewel prints "Jewel") is the one exception
                if not (it and it != b[0] and sum(1 for x in t["items"].values() if x.get("name") == it) > 1):
                    bad.append("base %s: block %r, item_tables %r" % (code, b[0], it))
        uq = dict((v.get("name"), 1) for v in t["uniques"].values())
        st = dict((v.get("name"), 1) for v in t["setItems"].values())
        rw = dict((v.get("key"), v.get("name")) for v in t["runewords"].values())
        for x in db["it"]:
            base_name = re.sub(r" \((?:[^)]*)\)$", "", x[1])
            if x[2] == "u" and base_name not in uq and x[1] not in uq:
                bad.append("unique %r is not in item_tables.json" % x[1])
            if x[2] == "s" and x[1] not in st:
                bad.append("set item %r is not in item_tables.json" % x[1])
            if x[2] == "r" and rw.get("Runeword" + x[0][1:]) != x[1]:
                bad.append("runeword %s %r vs item_tables %r" % (x[0], x[1], rw.get("Runeword" + x[0][1:])))
        self.assertEqual(bad, [], "\n  ".join(bad[:20]))
        c = db["counts"]
        self.assertGreaterEqual((c["uniques"], c["sets"], c["runewords"], c["crafted"]), (400, 140, 90, 36), c)

    def test_the_shipped_block_carries_the_fix_round_shapes(self):
        db = _db()
        T = db["T"]
        by = dict((x[1], x) for x in db["it"])
        lv = [r for x in db["it"] for l in x[6] for r in l[1] if r and r[0] == "L"]
        self.assertGreater(len(lv), 60, "PRINT THE DENOMINATOR: %d per-level lines in the block" % len(lv))
        self.assertEqual([r for r in lv if len(r) != 5], [], "a per-level line without its range and shift")
        self.assertEqual([r for r in lv if r[1] == 0 and r[3] == 0], [], "a per-level line stores 0 (a blank par read as 0)")

        def ranges(name, code):
            return [l[1] for l in by[name][6] if l[3] == code]
        self.assertEqual(ranges("Fortitude", "hp/lvl"), [[["L", 8, "p6", 12, 3]]])
        self.assertEqual(ranges("Eaglehorn", "att/lvl"), [[["L", 12, "p2", 12, 1]]], "att/lvl is shift 1 (op param)")
        self.assertEqual(ranges("Hellfire Torch", "randclassskill"), [[[3, 3, "p1"], ["C", 0, "p1", 7]]])
        ga = sorted(T[l[0]] for l in by["Guardian Angel"][6] if l[3] == "res-all-max")
        self.assertEqual(ga, ["{+0}% to Maximum Cold Resist", "{+0}% to Maximum Fire Resist",
                              "{+0}% to Maximum Lightning Resist", "{+0}% to Maximum Poison Resist"])

    def test_the_generator_still_writes_the_shipped_block_where_the_install_is(self):
        import char_builder_db as CBDB
        code, say = CBDB.check()
        if code == CBDB.SKIP:
            self.skipTest("UNMEASURED here, not passed: " + say)
        self.assertEqual(code, 0, say)

    def test_the_parent_list_sockets_tabs_tree_and_copy(self):
        out = _run(r"""
          window.openCharBuilder(); window._cbOpenNew(); window._cbNewCls('Sorceress'); window._cbNewLvl(80); window._cbNewGo();
          var cur = function(){ return window._cbAll()[window._cbState().bid]; };
          var sockIn = function(){ var h = MODAL._html, i = h.indexOf('id="cb-sockets"'); return i < 0 ? null : h.slice(h.lastIndexOf('<input', i), h.indexOf('>', i) + 1); };
          var byName = function(n){ var h = null; window._cbDb().it.forEach(function(x){ if (x[1] === n) h = x; }); return h; };
          window._cbOpenPick('slot', 'head'); window._cbChoose(byName('Crown of Ages')[0]);
          OUT.crownIn = sockIn(); OUT.crownSays = /Socketed 1-2 - type its roll/.test(MODAL._html);
          window._cbRollInput({ target: { value: '2', classList: { contains: function(c){ return c === 'cb-roll'; }, add: function(){}, remove: function(){}, toggle: function(){} },
            getAttribute: function(a){ return { 'data-key': 'p8', 'data-lo': '1', 'data-hi': '2' }[a]; } } });
          OUT.crownTyped = [cur().sets[0].slots.head.sockets, cur().sets[0].slots.head.rolls, (MODAL._html.match(/Empty Socket/g) || []).length, sockIn()];
          window._cbEdit('sockets', '1'); OUT.crownStep = [cur().sets[0].slots.head.sockets, cur().sets[0].slots.head.rolls];
          window._cbClosePick();
          window._cbOpenPick('slot', 'tors'); window._cbChoose(byName("Tyrael's Might")[0]); OUT.tyrIn = sockIn(); window._cbEdit('sockets', '4');
          OUT.tyr = cur().sets[0].slots.tors.sockets; window._cbPickTab('select'); window._cbChoose('b:utp');
          /* #174 v-B3: a base now waits on its Quality tab (their Select -> Quality -> Edit); Normal is the old pick */
          window._cbQuality('b'); OUT.archonIn = sockIn(); window._cbClosePick();
          window._cbOpenPick('inv', null, [0, 0]);
          OUT.invAll = window._cbPickRows().map(function(x){ return x[1]; });
          window._cbQt('m'); OUT.invMisc = window._cbPickRows().map(function(x){ return x[1]; }); window._cbClosePick();
          OUT.tree = window._cbStashTree();
          window._cbOpenStash(); window._cbStashTab('create'); OUT.folds = (MODAL._html.match(/class="cb-fold"/g) || []).length;
          var mi = -1; OUT.tree.forEach(function(n, i){ if (n[0] === 'Melee Weapons') mi = i; });
          window._cbStashFold(mi); OUT.foldedHides = !/>Axes<\/button>/.test(MODAL._html) && />Melee Weapons<\/button>/.test(MODAL._html);
          window._cbCloseStash();
          window.D2R_CHAR_ENGINE = { sheet: function(){ return { rows: [] }; } }; window._cbRender();
          var h = ELS['cb-win']._html; OUT.legend = /EXACT = fixed by the table, or typed/.test(h);
          window._cbView('calc');
          var calc = ELS['cb-win']._html;
          OUT.bp = /Breakpoints \(FCR \/ FHR \/ IAS \/ FBR\)\. UNKNOWN\. The stats engine did not return a breakpoint/.test(calc)
            && !/still owed/.test(calc) && !/arrive with the stats engine/.test(calc);
        """)
        self.assertIn('min="1" max="2"', out["crownIn"] or "", "Crown of Ages' stepper is not its own Socketed 1-2: %s" % out["crownIn"])
        self.assertTrue(out["crownSays"], "an untouched Socketed roll does not say how its sockets appear")
        self.assertEqual(out["crownTyped"][:3], [2, {"p8": 2}, 2], "typing Socketed 2 did not make two sockets to fill")
        self.assertIn('value="2"', out["crownTyped"][3], "the stepper disagrees with the item's own Socketed roll")
        self.assertEqual(out["crownStep"], [1, {"p8": 1}], "the stepper does not write the same roll the box writes")
        self.assertIn('min="0" max="1"', out["tyrIn"] or "", "a unique with no Socketed line takes one socket (Larzuk)")
        self.assertIn("Larzuk", out["tyrIn"] or "")
        self.assertEqual(out["tyr"], 1, "a unique was given 4 sockets")
        self.assertIn('max="4"', out["archonIn"] or "", "a base's own ceiling (Archon Plate 4) was lost")
        jewels = [n for n in out["invMisc"] if "Jewel" in n or n in ("Rainbow Facet (Cold, Level-up)",)]
        self.assertGreater(len(jewels), 1, "PRINT THE DENOMINATOR: Miscellaneous lists no jewel: %s" % out["invMisc"][:8])
        self.assertEqual([n for n in out["invAll"] if n in ("Jewel", "Colossal Jewel")], [], "All Items lists jewels (theirs: charms)")
        self.assertIn("Grand Charm", out["invAll"])
        tree = [n for n, _ in out["tree"]]
        i = tree.index("Jewels")
        self.assertEqual(out["tree"][i + 1], ["Colossal Jewels", 1], "the Jewels node has no Colossal Jewels child")
        m = tree.index("Melee Weapons")
        self.assertEqual(out["tree"][m + 1], ["Axes", 1])
        self.assertIn("Ranged Weapons", tree)
        self.assertNotIn("Weapons", tree, "the old flat Weapons parent is back")
        self.assertGreaterEqual(out["folds"], 6, "the tree's parents carry no fold chevron")
        self.assertTrue(out["foldedHides"], "folding Melee Weapons does not hide its children")
        self.assertTrue(out["legend"], "STATS still says EXACT means only a typed roll")
        self.assertTrue(out["bp"], "a stubbed engine must say the breakpoint is UNKNOWN, and the owed placeholder must stay gone")

    def test_an_active_button_keeps_its_label_under_the_pointer(self):
        css = _builder_css(_src())
        self.assertEqual(css.count(".cb-btn:hover:not([disabled]){"), 1)
        rule = re.search(r"\.cb-btn\.cb-on:hover:not\(\[disabled\]\)\{([^}]*)\}", css)
        self.assertTrue(rule, "no hover rule for an ACTIVE button: the plain hover paints gold text on its gold face")
        self.assertIn("color:#1a1208", rule.group(1))
        self.assertIn(".cb-sheet .cb-pane{min-height:0}", css, "the stacked picker's pane is unbounded, its list cannot scroll")


# REG-1599 (2026-09-30, his rule: the builder is "a personal tool for each individual console"): a console's first
# template is what ITS OWN reels learned - the page's typed CHARS are a lookup only, never offered. The cases below need
# a real character to build on, so the console answers /api/chars_learned (a synchronous stub) with one it learned,
# exactly the way the page asks it. Without this they would be testing the empty console, which
# test_characters_learn_from_the_reels pins: "New build", class UNKNOWN.
_LEARNED_ON_THIS_CONSOLE = r"""
  (function(){
    function SYNC(v){ return { then: function(f){ var x = f(v); return (x && typeof x.then === 'function') ? x : SYNC(x); },
                               'catch': function(){ return this; } }; }
    window.location = { protocol: 'http:' };
    window.fetch = function(){ return SYNC({ ok: true, json: function(){ return SYNC({ ok: true, chars: [
      { name: 'Konyolock', cls: 'Warlock', level: 88, visits: 3 } ] }); } }); };
    window._cbLearnedFetch();
  })();
"""

class TheDoctorWatchesThePickersBlock(unittest.TestCase):
    """'builder item data' - the CB_DB block's own doctor row, beside 'character sheet data'"""

    def _run(self, answer):
        import console_doctor as D
        import char_builder_db as CBDB
        real = CBDB.check
        CBDB.check = lambda *a, **k: answer
        try:
            return D._check_the_builder_database_matches_the_install()
        finally:
            CBDB.check = real

    def test_fresh_is_ok_stale_is_missing_no_install_is_unknown(self):
        import console_doctor as D
        self.assertEqual(self._run((0, "matches the install"))[0], D.OK)
        st, why = self._run((1, "the install disagrees with the block in bible.html"))
        self.assertEqual(st, D.MISSING, "a patched install still reads as a healthy picker")
        self.assertIn("last patch", why)
        self.assertEqual(self._run((77, "cannot re-derive here"))[0], D.UNKNOWN)

    def test_the_row_is_registered_periodic_declared_and_explained(self):
        import console_doctor as D
        import corroborate as C
        for reg, name in ((dict(D.CHECKS), "CHECKS"), (D.PERIODIC, "PERIODIC"), (D.WATCHES, "WATCHES"),
                          (D.MINE, "MINE"), (C.NO_JOINT_YET, "NO_JOINT_YET")):
            self.assertIn("builder item data", reg, "the row is not in %s" % name)


RED_PROOF = [
    {
        "why": "#174 v-B2 fix round (+ v3885 #136) - the parent list offers another class's items again (34 pelts for a Sorceress)",
        "file": "bible.html",
        "find": "    var bci = (_worn && !st.host) ? _cbClsIx((_cbBuild() || {}).cls)\n      : ((catIx == null || catIx < 0) ? _cbClsIx((_cbBuild() || {}).cls) : -1);\n",
        "replace": "    var bci = -1;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - a unique with an own Socketed line takes the base's ceiling again (Crown of Ages 3)",
        "file": "bible.html",
        "find": "      return { lo: lo, hi: hi, key: lo === hi ? null : r[2], why: 'its own Socketed line: ' + (lo === hi ? lo : lo + '-' + hi) };\n",
        "replace": "      return { lo: 0, hi: base, key: null, why: '' };\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - the item's own Socketed roll no longer drives its sockets (two stores disagree)",
        "file": "bible.html",
        "find": "      if (sr.key && sr.key === key){ sockKey = true; e.sockets = r.v == null ? 0 : r.v; e.socketed = (e.socketed || []).slice(0, e.sockets); } });",
        "replace": "      if (false){ sockKey = true; } });",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - any unique takes the base's full socket count (no Larzuk rule)",
        "file": "bible.html",
        "find": "    if (it[2] === 'u' || it[2] === 's') return { lo: 0, hi: Math.min(1, base), key: null, why: 'a unique or set item takes one socket, from Larzuk' };\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - the inventory's All Items lists jewels again",
        "file": "bible.html",
        "find": "    if (t === 'all') return !(slot === 'inv' && _cbIsJewel(x));\n",
        "replace": "    if (t === 'all') return true;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - the stash tree loses its Jewels > Colossal Jewels child",
        "file": "bible.html",
        "find": "    if (Object.keys(d.b).some(function(c){ return d.b[c][1] === 'cjwl' && d.b[c][20]; })) out.push(",
        "replace": "    if (false) out.push(",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - folding a parent hides nothing",
        "file": "bible.html",
        "find": "      if (!n[2]) under = i; else if (fold[under]) return '';\n",
        "replace": "      if (!n[2]) under = i;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - the STATS legend says EXACT is only a typed roll again",
        "file": "bible.html",
        "find": "EXACT = fixed by the table, or typed · RANGE",
        "replace": "EXACT = a typed roll · RANGE",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - the active button's hover paints gold on gold again",
        "file": "bible.html",
        "find": ".cb-btn.cb-on:hover:not([disabled]){color:#1a1208;border-color:var(--gold-bright)}",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - the per-level generator reads a blank par as 0 again (Fortitude L 0)",
        "file": "char_builder_db.py",
        "find": "                elif str(lo or \"\").strip():\n",
        "replace": "                elif False:\n",
        "matches": 1, "needs": "d2r-install",
    },
    {
        "why": "#174 v-B2 fix round - the generator prints res-all-max's first stat only again",
        "file": "char_builder_db.py",
        "find": "            if f1 == 1 and len(multi) > 1 and len(multi) == len([k for k in range(1, 8) if p.get(\"func%d\" % k)]):\n",
        "replace": "            if False:\n",
        "matches": 1, "needs": "d2r-install",
    },
    {
        "why": "#174 v-B2 fix round - the picker's doctor row reads a stale block as OK",
        "file": "console_doctor.py",
        "find": "        return MISSING, say + \" - the picker and every tooltip list last patch's items and ranges\"\n",
        "replace": "        return OK, say\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - with no stats engine STATS draws a number (a 0) where nothing was measured",
        "file": "bible.html",
        "find": "+ esc(why) + '\"><i>UNKNOWN</i></span></div>'; });\n",
        "replace": "+ esc(why) + '\"><b>0</b></span></div>'; });\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - the helm's rail loses its parent entry, so Helmets stops listing circlets and the rail is no longer theirs",
        "file": "bible.html",
        "find": "    return [[cats[0][0], -1, cats.length === 1 ? cats[0][2] : -1]].concat(kids(1));\n",
        "replace": "    return kids(0);\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - a runeword is offered on a base that cannot hold its runes (Enigma on a 2-socket Quilted Armor)",
        "file": "bible.html",
        "find": "        if (_cbMaxSock(c, 99) < n) return;\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - a roll outside the item's range is accepted and saved as if it were his",
        "file": "bible.html",
        "find": "    if (v < lo || v > hi) return { ok: false, why: 'this roll is ' + lo + '–' + hi + ' on this item; ' + v + ' is outside it' };\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - a typed roll never reaches the numbers, so Defense stays a range after he typed his roll",
        "file": "bible.html",
        "find": "    if (t != null && t >= Math.min(r[0], r[1]) && t <= Math.max(r[0], r[1])) return [t, t, true];\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - the builds stop forking per account: a ladder build lands in the main world's key",
        "file": "bible.html",
        "find": "  \"d2r_charBuilds\",\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - Esc skips the picker and closes the whole builder on the first press",
        "file": "bible.html",
        "find": "    if (st.pick){ window._cbClosePick(); return 'picker'; }\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - the builder reads his vault (the items coming in mix with the tool)",
        "file": "bible.html",
        "find": "    _cbDb();\n    var all = _cbAll(), sel = buildId || null;\n",
        "replace": "    _cbDb(); try { window.LSR.getItem('d2r_muleAssign'); } catch (e) {}\n    var all = _cbAll(), sel = buildId || null;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - the tooltip's properties are no longer the game's blue",
        "file": "bible.html",
        "find": ".d2tip .d2t-num,.d2tip .d2t-p,.cb-ed-base .d2t-num{color:rgb(105,105,255)}",
        "replace": ".d2tip .d2t-num,.d2tip .d2t-p,.cb-ed-base .d2t-num{color:rgb(232,232,232)}",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - an UNKNOWN strength paints the requirement red on a guess",
        "file": "bible.html",
        "find": "    var red = function(need, have){ return (have != null && need != null && have < need) ? 'd2t-red' : 'd2t-w'; };\n",
        "replace": "    var red = function(need, have){ return (need != null && !(have >= need)) ? 'd2t-red' : 'd2t-w'; };\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    if NODE is None:
        sys.stderr.write("⚪ SKIP — node is not on this machine, so the builder was not driven. UNMEASURED, declared (77).\n")
        raise SystemExit(77)
    unittest.main(verbosity=2)
