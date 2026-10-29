# -*- coding: utf-8 -*-
"""#154 P3a (REG-2844) - EACH COPY CARRIES ITS OWN ENTRY: an Ist Shako and a Ber Shako are two copies he can tell apart.

What made a copy what it is lived in stores kept by NAME. d2r_plannerMade keeps one runeword record per name, and REG-2185
kept a second Grief from writing over the first, so the second Grief's base was kept nowhere. A unique's runes were kept
nowhere at all. Measured on the whole page in node: an Ist Shako and a Ber Shako added by hand were two copies with nothing
to tell them apart, and a typed Ber Shako was asked "same item?" against an Ist Shako it plainly was not.

Now each copy's record (d2r_vaultRecords) carries its own entry: base, quality, sockets, runes, eth, mods and rolls.
- The planner's filing of that copy writes it; his "the same item" fills what the record lacks.
- It rides every rebuild and every move written, and the profile saves it.
- The stores by name stay for their readers. Copy 0 of a runeword he built reads its planner record until it carries
  its own.
- The join question reads it, so a copy whose recorded runes plainly differ is filed as another copy with no question.
Magic and rare picks wait for their keeper record (P3b). Driven on the whole page in node. RED_PROOF below.
"""
import json
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
import vault_page_node as VPN  # noqa: E402

PRELUDE = ("Object.defineProperty(navigator, 'webdriver', { get: function(){ return true; }, configurable: true });\n"
           "localStorage.setItem('d2r_ownerClaim', '*');\n")
N = "Harlequin Crest (Shako)"
DUMP = ("OUT.dump = (function(){ var o = {}; for (var i = 0; i < localStorage.length; i++){ var k = localStorage.key(i);"
        " o[k] = localStorage.getItem(k); } return o; })();")

HELP = r"""
var W = window, DB = W._cbDb(), N = %s;
function runeId(n){ var r = DB.sk.find(function(s){ return String(s[1] || '').toLowerCase() === (n + ' rune').toLowerCase() || String(s[1] || '').toLowerCase() === n.toLowerCase(); }); return r ? r[0] : null; }
function ent(nm, k){ var e = W._vaultCopyEntry(nm, k); return e ? { base: e.base || null, socketed: e.socketed || [], sockets: e.sockets | 0 } : e; }
function stored(nm, k){ var raw = null; try { raw = JSON.parse(W.LSR.getItem('d2r_vaultRecords') || 'null'); } catch (e) {}
  var r = ((raw && raw.records) || []).filter(function(x){ return x.name === nm && (x.copyIx | 0) === k; })[0]; return r ? (r.entry ? 'entry' : 'no-entry') : 'no-record'; }
""" % json.dumps(N)

BUILD = HELP + r"""
(function(){
var SH = DB.it.find(function(x){ return x[1] === 'Harlequin Crest' && x[2] === 'u'; });
var grief = DB.it.find(function(x){ return x[1] === 'Grief' && x[2] === 'r'; });
var gx = Object.keys(DB.b).find(function(c){ return DB.b[c][0] === 'Giant Axe'; });
var pb = Object.keys(DB.b).find(function(c){ return DB.b[c][0] === 'Phase Blade'; });
/* 1 - an Ist Shako, then a Ber Shako, by hand through the planner */
W.vaultPlannerOpen(''); W._cbChoose(SH[0]); W._cbEdit('sockets', '1'); W._cbSocket(0, runeId('Ist')); H.flush(60, 3);
OUT.c1 = W.vaultPlannerClose(); H.flush(60, 3);
W.vaultPlannerOpen(''); W._cbChoose(SH[0]); W._cbEdit('sockets', '1'); W._cbSocket(0, runeId('Ber')); H.flush(60, 3);
OUT.c2 = W.vaultPlannerClose(); H.flush(60, 3);
OUT.shako = { copies: copyCount(N), e0: ent(N, 0), e1: ent(N, 1), s0: stored(N, 0), s1: stored(N, 1),
              ist: runeId('Ist'), ber: runeId('Ber') };
/* 2 - an Ist Shako typed again is the same as copy 0, so it is asked, and nothing is added */
W.vaultPlannerOpen(''); W._cbChoose(SH[0]); W._cbEdit('sockets', '1'); W._cbSocket(0, runeId('Ist')); H.flush(60, 3);
OUT.c3 = W.vaultPlannerClose(); H.flush(60, 3);
OUT.c3copies = copyCount(N);
W.vaultPlannerAnswer(0); H.flush(60, 3); W.vaultPlannerClose(); H.flush(60, 3);
/* 3 - two Griefs on two bases: the second keeps its own */
W.vaultPlannerOpen(''); W._cbChoose(grief[0]); W._cbPickBase(gx); W.vaultPlannerClose(); H.flush(60, 3);
W.vaultPlannerOpen(''); W._cbChoose(grief[0]); W._cbPickBase(pb); OUT.g2 = W.vaultPlannerClose(); H.flush(60, 3);
OUT.grief = { copies: copyCount('Grief'), named: W._vpMadeBase('Grief'), e0: ent('Grief', 0), e1: ent('Grief', 1), gx: gx, pb: pb };
/* 4 - a rebuild that adds a name, and a move written on the copy, keep every entry */
W.vaultHandAdd("Nightwing's Veil", new Date().toISOString(), {}); H.flush(60, 3);
OUT.persist = W._vaultRecordsPersist(); H.flush(60, 3);
W._vaultMoveMark(N, 1); H.flush(60, 3);
OUT.after = { e0: ent(N, 0), e1: ent(N, 1), g1: ent('Grief', 1) };
OUT.text = W._vaultProfileBuild();
OUT.errors = H.errors.slice();
})();
"""

AFTER = HELP + r"""
try { W.renderVault(); } catch (e) {} H.flush(60, 3);
OUT.loaded = { e0: ent(N, 0), e1: ent(N, 1), g0: ent('Grief', 0), g1: ent('Grief', 1) };
"""

# a world from before this rule: a runeword he built, kept only in d2r_plannerMade
OLD = (PRELUDE + "localStorage.setItem('d2r_owned', '[\"Grief\"]'); localStorage.setItem('d2r_muleAssign', '{\"Grief\":\"runewords\"}');\n"
       "localStorage.setItem('d2r_plannerMade', JSON.stringify({ Grief: { id: 'OLD', base: 'gax', baseName: 'Giant Axe', q: 'r',"
       " affixes: [], eth: false, sockets: 5, rolls: null } }));\n")
OLD_BODY = HELP + r"""
var grief = DB.it.find(function(x){ return x[1] === 'Grief' && x[2] === 'r'; });
OUT.old = ent('Grief', 0);
"""


def _load_body(text):
    return ("(function(){ var P = window._vaultProfileParse(" + json.dumps(text) + "); OUT.ok = !!(P && P.ok);"
            " Object.keys((P && P.stores) || {}).forEach(function(k){ var v = P.stores[k];"
            " if (v === null) window.LSR.removeItem(k); else window.LSR.setItem(k, v); }); })();" + DUMP)


class EachCopyCarriesItsOwnEntry(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.b = VPN.run(BUILD, prelude=PRELUDE, timeout=300)
        loaded = VPN.run(_load_body(cls.b["text"]), prelude=PRELUDE, timeout=300)
        cls.loaded_ok = loaded.get("ok")
        seed = PRELUDE + "var __D = " + json.dumps(loaded["dump"]) + "; Object.keys(__D).forEach(function(k){ localStorage.setItem(k, __D[k]); });\n"
        cls.a = VPN.run(AFTER, prelude=seed, timeout=300)
        cls.old = VPN.run(OLD_BODY, prelude=OLD, timeout=300)

    def test_the_page_booted(self):
        self.assertEqual(self.b["__boot"]["errors"], [], self.b["__boot"])
        self.assertEqual(self.b["errors"], [])
        self.assertTrue(self.loaded_ok, "PREMISE: the profile did not parse")

    def test_an_ist_shako_and_a_ber_shako_are_two_copies_told_apart(self):
        s = self.b["shako"]
        self.assertEqual((self.b["c1"], self.b["c2"]), (True, True), "PREMISE: a planner close was held: %r" % self.b)
        self.assertEqual(s["copies"], 2, s)
        self.assertEqual((s["s0"], s["s1"]), ("entry", "entry"), "a copy's record carries no entry: %r" % s)
        self.assertEqual(s["e0"]["socketed"], [s["ist"]], s)
        self.assertEqual(s["e1"]["socketed"], [s["ber"]], s)

    def test_the_same_runes_again_are_asked_not_counted(self):
        self.assertEqual((self.b["c3"], self.b["c3copies"]), (False, 2), "an Ist Shako typed again was counted or guessed: %r" % self.b)

    def test_a_second_grief_keeps_its_own_base(self):
        g = self.b["grief"]
        self.assertEqual(g["copies"], 2, g)
        self.assertEqual(g["named"], "Giant Axe", "PREMISE: the planner's record by name moved: %r" % g)
        self.assertEqual((g["e0"] or {}).get("base"), g["gx"], g)
        self.assertEqual((g["e1"] or {}).get("base"), g["pb"], "the second Grief's base was kept nowhere: %r" % g)

    def test_a_rebuild_and_a_move_keep_every_entry(self):
        a, s = self.b["after"], self.b["shako"]
        self.assertTrue((self.b["persist"] or {}).get("ok"), self.b["persist"])
        self.assertEqual(a["e0"], s["e0"], a)
        self.assertEqual(a["e1"], s["e1"], "a rebuild or a move dropped the copy's entry: %r" % a)
        self.assertEqual(a["g1"], self.b["grief"]["e1"], a)

    def test_the_profile_round_trips_each_copy(self):
        lo, s, g = self.a["loaded"], self.b["shako"], self.b["grief"]
        self.assertEqual((lo["e0"], lo["e1"]), (s["e0"], s["e1"]), "the profile lost a copy's entry: %r" % lo)
        self.assertEqual((lo["g0"], lo["g1"]), (g["e0"], g["e1"]), lo)

    def test_an_older_world_reads_the_planner_record_for_copy_0(self):
        self.assertEqual(self.old["old"], {"base": "gax", "socketed": [], "sockets": 5}, self.old)


RED_PROOF = [
    {"why": "REG-2844 - the planner files a copy and records nothing that tells it apart",
     "file": "bible.html",
     "find": "    if (kept && _vpMade.copyIx != null && typeof window._vaultCopyEntrySet === 'function'){\n",
     "replace": "    if (false){\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2844 - the record row drops the entry",
     "file": "bible.html",
     "find": "    if (spec.entry && typeof spec.entry === 'object' && !Array.isArray(spec.entry)) row.entry = spec.entry;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2844 - a rebuild drops every copy's entry",
     "file": "bible.html",
     "find": "          entry: priorEntry[String(r.name) + '\\u0000' + (r.copyIx || 0)] || null, /* REG-2844 entry carry */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2844 - a move written drops the copy's entry",
     "file": "bible.html",
     "find": "          entry: row.entry, looseWhere: row.looseWhere   /* REG-2844 - a move written never drops the copy's entry (or its loose place) */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2844 - the join question ignores the copy's own entry, so plainly different runes are asked",
     "file": "bible.html",
     "find": "      return { copyIx: k, how: how, at: at, place: place, entry: own || (mine ? mine.entry : null) };\n",
     "replace": "      return { copyIx: k, how: how, at: at, place: place, entry: mine ? mine.entry : null };\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2844 - the profile leaves the records (and every copy's entry) out",
     "file": "bible.html",
     "find": "'d2r_muleEquip','d2r_vaultRecords','d2r_vaultProv',",
     "replace": "'d2r_muleEquip','d2r_vaultProv',",
     "matches": 1, "needs": "node"},
    {"why": "REG-2844 - an older world's runeword reads no entry for copy 0",
     "file": "bible.html",
     "find": "      if (m) return _vrEntryOf({ id: m.id, base: m.base, q: m.q, eth: m.eth, sockets: m.sockets, affixes: m.affixes, rolls: m.rolls });\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
