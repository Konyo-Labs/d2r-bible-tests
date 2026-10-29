# -*- coding: utf-8 -*-
"""REG-2804 (his ruling 2026-10-28 ~18:45 IDT, #154.14) - A MULE IS A WAR MULE BY ITS STORED ROLE, NEVER ITS NAME, AND THE SHARED
STASH'S FAMILY WEARS ONE LOOK WHATEVER A WAR MULE IS CALLED.

His words: "is there not a way to have a shared CSS for that renamed mule? the shared stash will stay shared stash.. and the
war1 and war2 will open and also should have that same shared css logic if we were to rename the mule it should be able to
render within the move task as a shared css for that same mule name."

MEASURED before (node, whole page): renaming UNI-ARMOR to WAR2 made it war mule 2 on the next read (_vaultWarRole fell back
to the /^war\\s*\\d*$/ name and stamped the role), its card took the war colour, and renaming it back to UNI-ARMOR KEPT the
role; the board's WAR1 renamed DEANSORC kept its role but its row's expand said "WAR1 private stash (1,1)" (the name the
plan stored); SHARED STASH renamed BIG STASH made its rows say BIG STASH while its window and its plan said SHARED STASH;
and no move row drew a target in the shared stash's colours at all.

Now: the role is read off the mule (stored by the board, by his creating a mule named WAR<n>, or stamped once from a
legacy roster), never off its name, and a core locker is never one; the shared stash keeps its name (no rename button, the
door refuses); and the shared stash's family - the shared stash and every WAR mule, by id and role - is marked
data-family="shared" on the move row's target, the row's expand, a WAR mule's window and FIND's mule name, with the card's
war colour as before. Driven on the whole page in node (vault_page_node - never a browser on his Mac). RED_PROOF below.
"""
import json
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
import vault_page_node as VPN  # noqa: E402

CLAIM = "localStorage.setItem('d2r_ownerClaim', '*');\n"
SHAKO = "Harlequin Crest (Shako)"     # big war gear: 1 in the war stash, the rest on a WAR mule

READ = r"""
var W = window, SH = %(shako)s;
function R(){ return JSON.parse(W.LSR.getItem('d2r_muleRoster') || '[]'); }
function byId(id){ return R().filter(function(m){ return m.id === id; })[0] || null; }
function card(id){ var s = (document.getElementById('vault-shelf') || {}).innerHTML || '', i = s.indexOf('data-vault-mule="' + id + '"');
  if (i < 0) return null; var j = s.lastIndexOf('<div class="vault-mule', i), k = s.indexOf('<div class="vault-mule', i + 10);
  return { cls: s.slice(j, i).replace(/\s+/g, ' '), html: s.slice(j, k < 0 ? s.length : k) }; }
function list(){ return (document.getElementById('vault-move-list') || {}).innerHTML || ''; }
function rename(id, to){ W.prompt = function(){ return to; }; W.vaultRenameMule(id); W.renderVault(); H.flush(60, 3); }
""" % {"shako": json.dumps(SHAKO)}

BODY_RENAME = READ + r"""
W._vaultAutoIntakeSet(false);
[SH, SH, SH].forEach(function(n){ W.vaultHandAdd(n); }); W.renderVault(); H.flush(60, 3);
var war1 = R().filter(function(m){ return m.role === 'war' && (+m.warN || 1) === 1; })[0] || {};   /* REG-2980 war mule 1 by its number, whatever its name */
OUT.war1 = war1.id || null;
rename(war1.id, 'DEANSORC');
var d = byId(war1.id);
OUT.dean = { name: d && d.name, role: d && d.role, read: W._vaultWarRole(d), card: (card(war1.id) || {}).cls };
var rows = (list().match(/<li class="vmv-row[^>]*>[\s\S]*?<\/li>/g) || []).filter(function(r){ return /DEANSORC/.test(r); });
OUT.dean.rows = rows.map(function(r){ return { fam: /data-family="shared"/.test(r), to: ((r.match(/<span class="vtk-to">([^<]*)/) || [])[1] || null) }; });
var hx = W._vaultTaskExpandHtml(SH, 1);
OUT.dean.expandHead = ((hx.match(/<div class="vtx-h">TO · ([^<]*)/) || [])[1] || null);
OUT.dean.expandFam = /^<div class="vtk-expand"[^>]*data-family="shared"/.test(hx);
W.vaultFind('shako'); H.flush(400, 3);
var fr = (document.getElementById('vault-find-results') || {}).innerHTML || '';
OUT.dean.find = (W._vaultWhereIs(SH) || {}).cells || [];
OUT.dean.findFam = /<span class="vfr-mule" data-family="shared">/.test(fr);
W.openMuleCard(war1.id);
var box = document.getElementById('vault-detail'), bh = (box || {}).innerHTML || '';
OUT.dean.window = { fam: box ? box.getAttribute('data-family') : null, badge: /<span class="vd-name">DEANSORC[^<]*<\/span><span class="vm-warbadge"/.test(bh) };
OUT.dean.byName = (W._vaultMuleOfPlace({ holder: 'deansorc' }) || {}).id || null;
W.vaultCloseCard && W.vaultCloseCard();
// UNI-ARMOR renamed WAR2, and back
rename('uni-armor', 'WAR2');
OUT.armor = { name: (byId('uni-armor') || {}).name, read: W._vaultWarRole(byId('uni-armor')), inWars: W._vaultWarMules().some(function(w){ return w.id === 'uni-armor'; }),
              card: (card('uni-armor') || {}).cls };
rename('uni-armor', 'UNI-ARMOR');
OUT.armorBack = { stored: byId('uni-armor'), read: W._vaultWarRole(byId('uni-armor')) };
// SHARED STASH keeps its name
rename('shared', 'BIG STASH');
OUT.shared = { name: (byId('shared') || {}).name, renameButton: ((card('shared') || {}).html || '').indexOf("vaultRenameMule('shared')") >= 0,
               otherButton: ((card('uni-weap') || {}).html || '').indexOf("vaultRenameMule('uni-weap')") >= 0 };
// a mule he CREATES as WAR<n>
W.prompt = function(){ return 'war5'; }; W.vaultAddMule();
var w5 = R().filter(function(m){ return m.name === 'WAR5'; })[0] || {};
OUT.war5 = { role: w5.role || null, warN: w5.warN || null };
// REG-3027 - a mule he creates as WAR0 is no war mule (0 read back as WAR1)
W.prompt = function(){ return 'war0'; }; W.vaultAddMule();
var w0 = R().filter(function(m){ return m.name === 'WAR0'; })[0] || null;
OUT.war0 = w0 ? { role: w0.role || null, read: W._vaultWarRole(w0) } : null;
"""

BODY_LEGACY = READ + r"""
OUT.legacy = byId('war-law-0'); OUT.core = byId('uni-armor'); OUT.mark = (byId('shared') || {}).warRoleV || null;
OUT.read = { legacy: W._vaultWarRole(byId('war-law-0')), core: W._vaultWarRole(byId('uni-armor')) };
OUT.zero = { stored: byId('war-law-z'), read: W._vaultWarRole(byId('war-law-z')), wars: W._vaultWarMules().map(function(w){ return w.id; }) };
rename('mlawadded1', 'WAR3');
OUT.war3 = W._vaultWarRole(byId('mlawadded1'));
OUT.raw = {}; H.RAW.forEach(function(v, k){ OUT.raw[k] = v; });
"""

BODY_RELOAD = READ + r"""
OUT.war3 = { stored: byId('mlawadded1'), read: W._vaultWarRole(byId('mlawadded1')) };
"""

BODY_SHARED = READ + r"""
W.renderVault(); H.flush(60, 3);
OUT.stored = (byId('shared') || {}).name || null;
OUT.card = ((card('shared') || {}).html || '').indexOf('SHARED STASH') >= 0;
OUT.oldName = ((card('shared') || {}).html || '').indexOf('BIG STASH') >= 0;
"""

BODY_ZERO = READ + r"""
OUT.read = W._vaultWarRole(byId('war-law-stamped0'));
OUT.inWars = W._vaultWarMules().some(function(w){ return w.id === 'war-law-stamped0'; });
OUT.legacyWar = W._vaultWarRole(byId('war-law-bare'));
"""

BODY_CORE = READ + r"""
OUT.read = W._vaultWarRole(byId('uni-armor')); OUT.inWars = W._vaultWarMules().some(function(w){ return w.id === 'uni-armor'; });
OUT.stored = byId('uni-armor');
"""

BODY_TAKEN = READ + r"""
W._vaultAutoIntakeSet(false);
rename('uni-armor', W._vaultWarName(1));   /* REG-2980 a normal mule holds the board's letter name for war mule 1 */
[SH, SH, SH].forEach(function(n){ W.vaultHandAdd(n); }); W.renderVault(); H.flush(60, 3);
OUT.wars = W._vaultWarMules().map(function(w){ return [w.id, w.name, w.n]; });
OUT.w2 = W._vaultWarName(2);
OUT.auto = W._vaultWarAuto || null;
"""


def _base():
    r = VPN.run("OUT.r = JSON.parse(window.LSR.getItem('d2r_muleRoster') || 'null') || "
                "(window._vaultRosterNow && window._vaultRosterNow());", prelude=CLAIM, timeout=300).get("r")
    if not isinstance(r, list) or not r:
        raise AssertionError("PREMISE: the page has no default roster: %r" % (r,))
    return [m for m in r if not str(m.get("name", "")).upper().startswith("WAR")]


def _seed(roster):
    return CLAIM + "localStorage.setItem('d2r_muleRoster', %s);\n" % json.dumps(json.dumps(roster))


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AMuleIsAWarMuleByItsRoleNeverItsName(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.r = VPN.run(BODY_RENAME, prelude=CLAIM, timeout=300)
        base = _base()
        legacy = [dict(m, **({"role": "war", "warN": 2} if m.get("id") == "uni-armor" else {})) for m in base]
        legacy += [{"id": "war-law-0", "name": "WAR1"}, {"id": "mlawadded1", "name": "UNI-WEAP-2", "icon": "📦", "added": True},
                   {"id": "war-law-z", "name": "WAR0", "icon": "📦", "added": True}]
        cls.l = VPN.run(BODY_LEGACY, prelude=_seed(legacy), timeout=300)
        raw = cls.l.pop("raw")
        carry = "".join("localStorage.setItem(%s, %s);\n" % (json.dumps(k), json.dumps(v)) for k, v in raw.items())
        cls.reload = VPN.run(BODY_RELOAD, prelude=carry, timeout=300)
        core = [dict(m, **({"role": "war", "warN": 2} if m.get("id") == "uni-armor" else {})
                       , **({"warRoleV": 1} if m.get("id") == "shared" else {})) for m in base]
        cls.c = VPN.run(BODY_CORE, prelude=_seed(core), timeout=300)
        cls.t = VPN.run(BODY_TAKEN, prelude=CLAIM, timeout=300)
        renamed = [dict(m, **({"name": "BIG STASH", "warRoleV": 1} if m.get("id") == "shared" else {})) for m in base]
        cls.s = VPN.run(BODY_SHARED, prelude=_seed(renamed), timeout=300)
        stamped0 = [dict(m, **({"warRoleV": 1} if m.get("id") == "shared" else {})) for m in base]
        stamped0 += [{"id": "war-law-stamped0", "name": "WAR0", "role": "war", "warN": 0, "added": True},
                     {"id": "war-law-bare", "name": "WAR", "role": "war", "added": True}]
        cls.z = VPN.run(BODY_ZERO, prelude=_seed(stamped0), timeout=300)

    def test_a_renamed_war1_keeps_its_role_and_the_shared_familys_look_everywhere(self):
        r = self.r
        self.assertEqual(r["__boot"]["errors"], [], r["__boot"])
        self.assertTrue(r["war1"], "PREMISE: the board made no WAR1: %r" % r)
        d = r["dean"]
        self.assertEqual((d["name"], d["role"], d["read"]), ("DEANSORC", "war", 1), "the rename took the war role away: %r" % d)
        self.assertIn("vm-war", d["card"] or "", "the renamed WAR1's card lost the shared colour: %r" % d["card"])
        self.assertTrue(d["rows"], "PREMISE: no move row goes to the renamed WAR1: %r" % d)
        for row in d["rows"]:
            self.assertTrue(row["fam"], "a move row to the renamed WAR1 is not drawn in the shared family: %r" % d["rows"])
            self.assertIn("DEANSORC (SHARED STASH · overflow)", row["to"] or "", d["rows"])
        self.assertIn("DEANSORC (SHARED STASH · overflow)", d["expandHead"] or "", "the expand names another mule: %r" % d["expandHead"])
        self.assertTrue(d["expandFam"], "the expand is not drawn in the shared family")
        self.assertTrue(any(c.startswith("DEANSORC · ") for c in d["find"]), "FIND does not name the renamed WAR1: %r" % d["find"])
        self.assertTrue(d["findFam"], "FIND's mule name is not drawn in the shared family")
        self.assertEqual(d["window"], {"fam": "shared", "badge": True}, "the renamed WAR1's window is not the shared family's: %r" % d["window"])
        self.assertEqual(d["byName"], r["war1"], "a holder named by its new name does not find the mule")

    def test_uni_armor_renamed_war2_stays_a_normal_mule(self):
        a, b = self.r["armor"], self.r["armorBack"]
        self.assertEqual(a["name"], "WAR2", "PREMISE: the rename did not land: %r" % a)
        self.assertEqual((a["read"], a["inWars"]), (0, False), "a name made UNI-ARMOR a war mule: %r" % a)
        self.assertNotIn("vm-war", a["card"] or "", "UNI-ARMOR named WAR2 wears the shared colour: %r" % a["card"])
        self.assertEqual(b["read"], 0, b)
        self.assertNotIn("role", b["stored"] or {}, "renaming UNI-ARMOR left a war role in the store: %r" % b["stored"])

    def test_the_shared_stash_keeps_its_name(self):
        s = self.r["shared"]
        self.assertEqual(s["name"], "SHARED STASH", "the shared stash was renamed: %r" % s)
        self.assertFalse(s["renameButton"], "the shared stash's card still offers a rename")
        self.assertTrue(s["otherButton"], "PREMISE: no other card offers a rename either - the check reads nothing")

    def test_a_shared_stash_renamed_before_the_rule_gets_its_name_back(self):
        """REG-3026 (the v3836 second eye) - the door refuses every rename of the shared stash, so one renamed BIG STASH
        before REG-2804 could never be put back: its card and rows printed BIG STASH, its lock and plan SHARED STASH."""
        s = self.s
        self.assertEqual(s["__boot"]["errors"], [], s["__boot"])
        self.assertEqual(s["stored"], "SHARED STASH", "a shared stash renamed before REG-2804 kept the old name: %r" % s)
        self.assertTrue(s["card"] and not s["oldName"], "the shared stash's card still prints the old name: %r" % s)

    def test_war0_is_never_a_war_number(self):
        """REG-3027 (the v3836 second eye) - WAR0 stored warN 0, which _vaultWarRole read back as 1: it collided with WAR1."""
        self.assertIsNotNone(self.r["war0"], "PREMISE: the board would not make a mule named WAR0: %r" % self.r)
        self.assertEqual(self.r["war0"], {"role": None, "read": 0}, "a mule he creates as WAR0 is a war mule: %r" % self.r["war0"])
        z = self.l["zero"]
        self.assertIsNotNone(z["stored"], "PREMISE: the legacy WAR0 mule is not in the roster: %r" % z)
        self.assertNotIn("role", z["stored"], "an old roster's WAR0 was stamped a war mule: %r" % z)
        self.assertEqual(z["read"], 0, z)
        self.assertNotIn("war-law-z", z["wars"], "WAR0 counts among the war mules: %r" % z)

    def test_a_war_number_0_stored_before_the_fix_reads_as_no_war_mule(self):
        """REG-3078 (the v3838 second eye, #231) - v3836 stamped a mule named WAR0 as role war with warN 0, and the reader's
        `+m.warN || 1` read that 0 as missing: a second war mule 1 beside WAR1. REG-3027 stopped new stamps, not stored ones,
        and the one-time stamp never revisits a stamped roster. A stored warN 0 is now no war number; a role with no number
        (the legacy bare WAR) is still war mule 1."""
        z = self.z
        self.assertEqual(z["__boot"]["errors"], [], z["__boot"])
        self.assertEqual((z["read"], z["inWars"]), (0, False), "a stored warN 0 still reads as a war mule: %r" % z)
        self.assertEqual(z["legacyWar"], 1, "PREMISE: a war role with no number no longer reads as war mule 1: %r" % z)

    def test_a_mule_he_creates_as_war5_is_a_war_mule(self):
        self.assertEqual(self.r["war5"], {"role": "war", "warN": 5}, "creating WAR5 by hand stored no war role: %r" % self.r["war5"])

    def test_a_legacy_war1_is_stamped_once_and_a_core_lockers_role_is_taken_off(self):
        l = self.l
        self.assertEqual(l["__boot"]["errors"], [], l["__boot"])
        self.assertEqual(((l["legacy"] or {}).get("role"), l["read"]["legacy"]), ("war", 1), "the hand-made WAR1 of an old roster lost its role: %r" % l)
        self.assertNotIn("role", l["core"] or {}, "a core locker kept the war role the old rule stamped: %r" % l["core"])
        self.assertEqual(l["read"]["core"], 0, l)
        self.assertEqual(l["mark"], 1, "the one-time stamp is not marked done: %r" % l["mark"])
        self.assertEqual(l["war3"], 0, "renaming a mule WAR3 made it a war mule: %r" % l["war3"])

    def test_a_name_never_makes_a_war_mule_across_a_reload(self):
        w = self.reload["war3"]
        self.assertEqual(((w["stored"] or {}).get("name"), w["read"]), ("WAR3", 0), "a reload read WAR3 as a war mule: %r" % w)
        self.assertNotIn("role", w["stored"] or {}, w)

    def test_a_core_locker_is_never_a_war_mule_whatever_its_store_says(self):
        c = self.c
        self.assertEqual((c["stored"] or {}).get("role"), "war", "PREMISE: the store does not carry the stray role: %r" % c["stored"])
        self.assertEqual((c["read"], c["inWars"]), (0, False), "a core locker with a stray war role reads as a war mule: %r" % c)

    def test_the_board_takes_the_next_free_war_name(self):
        t = self.t
        self.assertEqual(t["__boot"]["errors"], [], t["__boot"])
        names = [w[1] for w in t["wars"]]
        self.assertNotIn("uni-armor", [w[0] for w in t["wars"]], "UNI-ARMOR named like war mule 1 became a war mule: %r" % t["wars"])
        self.assertEqual(names, [t["w2"]], "with war mule 1's name on a normal mule, the board did not take the next: %r / %r" % (t["wars"], t["auto"]))


RED_PROOF = [
    {"why": "REG-3078 - a stored war number 0 reads as war mule 1 again",
     "file": "bible.html",
     "find": "    if (m.role === 'war' && m.warN != null && m.warN !== '' && !(+m.warN >= 1)) return 0;",
     "replace": "    if (false) return 0;",
     "matches": 1, "needs": "node"},
    {"why": "REG-3026 - a shared stash renamed before REG-2804 keeps its old name",
     "file": "bible.html",
     "find": "    if (!sh || sh.name === 'SHARED STASH') return;\n",
     "replace": "    return;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3027 - an old roster's WAR0 is stamped war number 0, which reads back as WAR1",
     "file": "bible.html",
     "find": "      var x = /^war\\s*([1-9]\\d*)?$/i.exec(",
     "replace": "      var x = /^war\\s*(\\d*)$/i.exec(",
     "matches": 1, "needs": "node"},
    {"why": "REG-3027 - a mule he creates as WAR0 is a war mule numbered 0, read as WAR1",
     "file": "bible.html",
     "find": "    var _wx = /^war\\s*([1-9]\\d*)?$/i.exec(v.name);",
     "replace": "    var _wx = /^war\\s*(\\d*)$/i.exec(v.name);",
     "matches": 1, "needs": "node"},
    {"why": "REG-2804 - a name makes a war mule again (UNI-ARMOR renamed WAR2)",
     "file": "bible.html",
     "find": "    if (m.role === 'war') return +m.warN || 1;\n    return 0;\n",
     "replace": "    if (m.role === 'war') return +m.warN || 1;\n    var _xn = /^war\\s*(\\d*)$/i.exec(String(m.name || '').trim()); if (_xn) return _xn[1] ? +_xn[1] : 1;\n    return 0;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2804 - a core locker with a stray war role reads as a war mule",
     "file": "bible.html",
     "find": "    if (!m || (typeof _WAR_CORE === 'object' && _WAR_CORE[m.id])) return 0;",
     "replace": "    if (!m) return 0;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2804 - an old roster's hand-made WAR1 is not stamped, so it stops being a war mule",
     "file": "bible.html",
     "find": "      if (x) { m.role = 'war'; m.warN = x[1] ? +x[1] : 1; changed = true; }\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2804 - the one-time stamp runs on every load, so a mule renamed WAR3 becomes a war mule on reload",
     "file": "bible.html",
     "find": "    if (!sh || sh.warRoleV >= 1) return;\n",
     "replace": "    if (!sh) return;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2804 - the old rule's war role is left on a core locker",
     "file": "bible.html",
     "find": "      if (_WAR_CORE[m.id]) { if (m.role === 'war') { delete m.role; delete m.warN; changed = true; } return; }\n",
     "replace": "      if (_WAR_CORE[m.id]) return;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2804 - the shared stash can be renamed again",
     "file": "bible.html",
     "find": "    if (id === 'shared'){ try { status(",
     "replace": "    if (false){ try { status(",
     "matches": 1, "needs": "node"},
    {"why": "REG-2804 - the shared stash's card offers a rename again",
     "file": "bible.html",
     "find": "(m.id === 'shared' ? '' : '<button class=\"vm-tool\"",
     "replace": "(false ? '' : '<button class=\"vm-tool\"",
     "matches": 1, "needs": "node"},
    {"why": "REG-2804 - a move row to a WAR mule is not drawn in the shared family",
     "file": "bible.html",
     "find": "+ '\"' + (fam ? ' data-family=\"shared\"' : '')",
     "replace": "+ '\"'",
     "matches": 1, "needs": "node"},
    {"why": "REG-2804 - a holder named by the mule's name today finds no mule",
     "file": "bible.html",
     "find": "    return list.filter(function(m){ return m && String(m.name || '').trim().toUpperCase() === h; })[0] || null;\n",
     "replace": "    return null;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2804 - the expand says the name the plan stored, not the mule's name today",
     "file": "bible.html",
     "find": "var pm = _vaultMuleOfPlace(place), nm = (pm && pm.name) ? String(pm.name) : String(place.holder || 'not seen yet');",
     "replace": "var pm = _vaultMuleOfPlace(place), nm = String(place.holder || 'not seen yet');",
     "matches": 1, "needs": "node"},
    {"why": "REG-2804 - a WAR mule's window is not drawn in the shared family",
     "file": "bible.html",
     "find": "    if (_vaultSharedFamily(m)) box.setAttribute('data-family', 'shared'); else box.removeAttribute('data-family');",
     "replace": "    box.removeAttribute('data-family');",
     "matches": 1, "needs": "node"},
    {"why": "REG-2804 - FIND's mule name is not drawn in the shared family",
     "file": "bible.html",
     "find": "'<span class=\"vfr-arrow\">→</span><span class=\"vfr-mule\"'+((typeof _vaultSharedFamily",
     "replace": "'<span class=\"vfr-arrow\">→</span><span class=\"vfr-mule\"'+((false && typeof _vaultSharedFamily",
     "matches": 1, "needs": "node"},
    {"why": "REG-2804 - a mule he creates as WAR5 stores no war role",
     "file": "bible.html",
     "find": "if (_wx) { _nm.role = 'war'; _nm.warN = _wx[1] ? +_wx[1] : 1; }",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2804 - the board stops when a normal mule is called WAR1 instead of taking WAR2",
     "file": "bible.html",
     "find": "      for (var _wn = 0; _wn < 20 && !_vmNameOk(name, null).ok; _wn++) { n++; name = _vaultWarName(n); }\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
