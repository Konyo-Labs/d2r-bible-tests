# -*- coding: utf-8 -*-
"""v3886 (#140, GrokBot's #28 pass 6720634931, adjudicated REAL 11-08) - A CLASS BASE CARRIES THE GAME'S STAFF MODS.

GrokBot, on the build screen: "a class-only base (helm / pelt / head / orb / Amazon weapon / claw) on a white, superior or
runeword item can carry its +1-3 class-skill lines" - and the builder offered none. The game calls them staff mods: an item
type that names a StaffMods class (itemtypes.txt, down its Equiv chain - a wand and a Necromancer head: Necromancer; a
Barbarian helm; a pelt; an orb; a claw; a scepter ...) can spawn as a normal or superior item with up to three single-skill
lines, +1 to +3 each, to skills of that class; a runeword keeps the base it was made in. tv/char_builder_db.py now carries
each type's StaffMods class (ty [6]) and each class's skills (cls sk), the Edit tab offers three rows, the tooltip prints
"+N to <Skill> (<Class> Only)", and the character sheet sums each as the game's own single-skill line - refused for another
class, exactly as a unique's is.

Drives the SHIPPED builder (the edit tab's harness) and the SHIPPED stats engine in node. RED_PROOF below.
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

import test_the_item_edit_tab_builds_magic_and_rare_items as ED  # noqa: E402  the edit tab's own harness
import test_the_character_sheet_sums_the_game_data as SHEET  # noqa: E402  the stats engine's own harness

BODY = r"""
mk('Necromancer', 90);
var d = window._cbDb();
function code(name){ var c = null; Object.keys(d.b).forEach(function(k){ if (!c && d.b[k][0] === name) c = k; }); return c; }
var head = code('Preserved Head'), monarch = code('Monarch');
OUT.tyHead = d.ty[d.b[head][1]][6]; OUT.tyMonarch = d.ty[d.b[monarch][1]][6];
OUT.necSkills = (d.cls[OUT.tyHead] || {}).sk ? d.cls[OUT.tyHead].sk.length : 0;
var bs = d.cls[OUT.tyHead].sk.filter(function(x){ return x[1] === 'Bone Spear'; })[0];
OUT.boneSpear = bs ? bs[0] : null;
var e = { id: 'b:' + head, base: head, q: 'b', ilvl: 99 };
OUT.clsWhite = window._cbStaffCls(e, window._cbItem(e.id));
OUT.clsMagic = window._cbStaffCls({ id: 'b:' + head, base: head, q: 'm', ilvl: 99 }, window._cbItem('b:' + head));
OUT.clsMonarch = window._cbStaffCls({ id: 'b:' + monarch, base: monarch, q: 'b', ilvl: 99 }, window._cbItem('b:' + monarch));
e.staff = [[OUT.boneSpear, 2]];
OUT.lines = window._cbStaffLines(e, window._cbItem(e.id)).map(function(l){ return l.t; });
OUT.block = !!window._cbStaffHtml(e, window._cbItem(e.id));
"""

SHEET_DRIVER = r"""
var window = {};
%(engine)s
var E = window.D2R_CHAR_ENGINE, out = {};
function row(s, k){ return (s.rows || []).filter(function(r){ return r.key === k; })[0] || null; }
var nec = E.sheet({ cls: 'Necromancer', level: 90, sets: [{ slots: { larm: { name: 'Preserved Head', staff: [[%(sk)d, 2]] } } }] }, {});
var sor = E.sheet({ cls: 'Sorceress', level: 90, sets: [{ slots: { larm: { name: 'Preserved Head', staff: [[%(sk)d, 2]] } } }] }, {});
var bad = E.sheet({ cls: 'Necromancer', level: 90, sets: [{ slots: { larm: { name: 'Preserved Head', staff: [[%(sk)d, 5]] } } }] }, {});
out.nec = row(nec, 'skill:%(sk)d'); out.sor = row(sor, 'skill:%(sk)d'); out.sorNot = JSON.stringify(sor.notApplied || []);
out.badProblems = JSON.stringify(bad.problems || []); out.bad = row(bad, 'skill:%(sk)d');
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipIf(ED.CB.NODE is None, "node is not on this machine")
class AClassBaseCarriesItsStaffMods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = ED._run(BODY)
        sk = cls.o.get("boneSpear")
        cls.s = None
        if sk is not None:
            js = SHEET_DRIVER % {"engine": SHEET._engine(SHEET._src()), "sk": int(sk)}
            r = subprocess.run([SHEET.NODE, "-"], input=js, capture_output=True, text=True, timeout=90)
            if r.returncode != 0:
                raise AssertionError("the shipped stats engine would not run - UNKNOWN: %s" % r.stderr[:900])
            cls.s = json.loads(r.stdout)

    def test_premise_the_data_names_the_class_and_its_skills(self):
        o = self.o
        self.assertGreaterEqual(o["tyHead"], 0, "PREMISE: a Necromancer head names no StaffMods class in the data")
        self.assertEqual(o["tyMonarch"], -1, "a Monarch (no StaffMods) names a class")
        self.assertGreater(o["necSkills"], 20, "PREMISE: the Necromancer's skills are not in the data")
        self.assertIsNotNone(o["boneSpear"], "PREMISE: Bone Spear is not a Necromancer skill in the data")

    def test_a_white_class_base_offers_and_prints_its_staff_mods(self):
        """* THE POINT - a white Preserved Head offers the rows and prints '+2 to Bone Spear (Necromancer Only)'"""
        o = self.o
        self.assertEqual(o["clsWhite"], o["tyHead"], "a white Preserved Head offers no staff mods")
        self.assertTrue(o["block"], "the Edit tab draws no staff-mod block for it")
        self.assertEqual(o["lines"], ["+2 to Bone Spear (Necromancer Only)"], "the tooltip does not print the staff mod")

    def test_only_white_superior_and_runeword_and_only_staffmod_types(self):
        """baseline: a magic head's skills are its affixes, and a Monarch has no staff mods"""
        self.assertEqual(self.o["clsMagic"], -1, "a magic item is offered staff mods (its skills come from its affixes)")
        self.assertEqual(self.o["clsMonarch"], -1, "a Monarch is offered staff mods")

    def test_the_sheet_sums_them_for_the_class_and_refuses_them_for_another(self):
        s = self.s
        self.assertIsNotNone(s, "PREMISE: the sheet did not run")
        self.assertIsNotNone(s["nec"], "the Necromancer's sheet has no Bone Spear row from the staff mod")
        self.assertEqual((s["nec"].get("value") or {}).get("min"), 2, "the staff mod's +2 is not what the sheet sums")
        self.assertIn("Necromancer only", s["sorNot"], "a Sorceress counted a Necromancer staff mod")
        self.assertIn("is not one skill at +1 to +3", s["badProblems"], "a +5 staff mod was summed instead of refused")


RED_PROOF = [
    {"why": "v3886 (#140) - a white class base offers no staff mods again (GrokBot: 0 rows)",
     "file": "bible.html",
     "find": "    if (!b || !(q === 'b' || q === 'sup' || q === 'r')) return -1;\n",
     "replace": "    if (!b || !(q === 'xx')) return -1;\n",
     "matches": 1, "needs": "node"},
    {"why": "v3886 (#140) - the sheet never reads the staff mods he picked",
     "file": "bible.html",
     "find": "        line(['skill', String(sid), sv, sv], { src: src, slot: it.slot, host: it, via: 'staff mod', unsure: it.unsure, picked: true });\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
