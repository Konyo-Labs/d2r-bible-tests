# -*- coding: utf-8 -*-
"""REG-3000..3002 (his ruling 2026-10-29 02:30, Q3) - A RUNEWORD MAY BE A MULTI-COPY KEEPER, AND EACH COPY KEEPS ITS OWN BASE.

His ruling: a runeword may be kept more than once, and its copies may sit in DIFFERENT BASES - 2x Grief in a Phase Blade and
a Berserker Axe are two copies of one keeper. Before:
  * REG-3000 - the Keepers box asked only the grail vocabulary, so "Grief" was refused ("isn't a chronicle item") while the
    hand door could raise a runeword's want. A typed runeword name is the keeper now, and it beats a grail name that only
    BEGINS that way; a name that is exactly both a runeword and a grail item is asked, never guessed;
  * REG-3001 - nothing said which base each copy sits in. The keeper row says it, off each copy's own record (REG-2844);
  * REG-3002 - a judged read of Grief only owned the name, so a Grief read in a Berserker Axe beside one in a Phase Blade was
    the same copy. The read's base names its copy now: the copy in that base, a copy whose base was never recorded, or -
    for a runeword he keeps several of and holds fewer of than he wants - another copy in that base. A base no copy has,
    on a runeword he keeps one of, is said and never counted (a misread base must not mint a copy).
Driven on the whole page in node. RED_PROOF below.
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
import vault_page_node as VPN  # noqa: E402

PRELUDE = ("Object.defineProperty(navigator, 'webdriver', { get: function(){ return true; }, configurable: true });\n"
           "localStorage.setItem('d2r_ownerClaim', '*');\n")
HELP = r"""
var W = window, DB = W._cbDb(), N = 'Grief';
function code(n){ return Object.keys(DB.b).find(function(c){ return DB.b[c][0] === n; }); }
function base(k){ var e = W._vaultCopyEntry(N, k); if (!e) return e; var b = e.base || null; return (b && DB.b[b]) ? DB.b[b][0] : b; }
function want(n){ return _mkWant(n); }
function box(text){ try { W.renderMultiKeep(); } catch (e) {} var inp = document.getElementById('vmk-add-input'); if (!inp) return 'no-input';
  inp.value = text; W.vaultMultiKeepAdd(); H.flush(60, 3); return 'typed'; }
function row(n){ try { W.renderMultiKeep(); } catch (e) { return 'render: ' + String(e && e.message || e); }
  var h = String((document.getElementById('vault-multikeep') || {}).innerHTML || ''), at = h.indexOf('data-mk="' + n + '"');
  if (at < 0) return null; var nx = h.indexOf('class="vmk-row"', at + 5); var seg = h.slice(at, nx < 0 ? h.length : nx);
  var m = /class="vmk-bases"[^>]*>([^<]*)</.exec(seg); return m ? m[1].replace(/&#39;/g, "'").replace(/&amp;/g, '&') : ''; }
"""
BOX = HELP + r"""
(function(){
try { W.renderVault(); } catch (e) {} H.flush(60, 3);
OUT.typed = box('grief');
OUT.grief = want('Grief');
box('Spirit');
OUT.spirit = { spirit: want('Spirit'), keys: Object.keys(multiKeep).filter(function(k){ return /^spirit/i.test(k); }) };
var before = Object.keys(multiKeep).length;
box('Not An Item At All');
OUT.junk = Object.keys(multiKeep).length - before;
/* a name that is exactly a runeword AND a grail item is asked, never guessed (a fixture item, never a real one) */
window.EXTRA_ITEMS = window.EXTRA_ITEMS || {}; window.EXTRA_ITEMS['INSIGHT'] = { rarity: 'unique', base: 'Ring', cat: 'Rings' };
OUT.ask = W._vmkRuneword('Insight');
box('Insight');
OUT.insight = { Insight: want('Insight'), INSIGHT: want('INSIGHT') };
/* two Griefs from the planner, one in a Phase Blade and one in a Berserker Axe: the row says each copy's base */
var grief = DB.it.find(function(x){ return x[1] === 'Grief' && x[2] === 'r'; });
W.vaultPlannerOpen(''); W._cbChoose(grief[0]); W._cbPickBase(code('Phase Blade')); W.vaultPlannerClose(); H.flush(60, 3);
W.vaultPlannerOpen(''); W._cbChoose(grief[0]); W._cbPickBase(code('Berserker Axe')); W.vaultPlannerClose(); H.flush(60, 3);
OUT.planner = { copies: copyCount(N), b0: base(0), b1: base(1), row: row(N) };
OUT.errors = H.errors.slice(0, 5);
})();
"""
READS = HELP + r"""
(function(){
function judge(b, sid){ var r = W.aicJudgeApply({ ok: true, verdict: { tier: 'keep', score: 90 }, q: 'runeword', base: b, name: N, mods: [] },
                                                 { sid: sid, frameId: sid + '_f', fts: Date.now(), loc: 'stash', scene: 'stash' });
  H.flush(60, 3); try { W.renderVault(); } catch (e) {} H.flush(60, 3);
  return { mode: r && r.mode, copy: r && r.copy !== undefined ? r.copy : 'unset', newCopy: !!(r && r.newCopy), why: !!(r && r.copyWhy),
           owned: owned.has(N), copies: copyCount(N), b0: base(0), b1: base(1) }; }
OUT.a = judge('Phase Blade', 's1');
OUT.b = judge('Berserker Axe', 's2');
_mkSetWant(N, 2);
OUT.c = judge('Berserker Axe', 's3');
OUT.d = judge('Phase Blade', 's4');
OUT.e = judge('Crystal Sword', 's5');
OUT.f = judge('', 's6');
OUT.row = row(N);
OUT.errors = H.errors.slice(0, 5);
})();
"""


class ARunewordKeeperKeepsABasePerCopy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.box = VPN.run(BOX, prelude=PRELUDE, timeout=300)
        cls.reads = VPN.run(READS, prelude=PRELUDE, timeout=300)

    def test_the_page_booted(self):
        for o in (self.box, self.reads):
            self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
            self.assertEqual(o["errors"], [])
        self.assertEqual(self.box["typed"], "typed", "PREMISE: the Keepers box is not on the page")

    def test_the_keepers_box_takes_a_runeword(self):
        self.assertEqual(self.box["grief"], 2, "the Keepers box refused Grief: %r" % self.box)

    def test_a_typed_runeword_beats_a_grail_name_that_only_begins_that_way(self):
        s = self.box["spirit"]
        self.assertEqual((s["spirit"], s["keys"]), (2, ["Spirit"]), s)

    def test_a_name_that_is_not_an_item_is_still_refused(self):
        self.assertEqual(self.box["junk"], 0, self.box)

    def test_a_name_that_is_exactly_both_is_asked(self):
        self.assertTrue((self.box["ask"] or {}).get("ask"), self.box["ask"])
        self.assertEqual(self.box["insight"], {"Insight": 0, "INSIGHT": 0}, "a name that is both was guessed: %r" % self.box["insight"])

    def test_the_keeper_row_says_each_copys_base(self):
        p = self.box["planner"]
        self.assertEqual((p["copies"], p["b0"], p["b1"]), (2, "Phase Blade", "Berserker Axe"), "PREMISE: %r" % p)
        self.assertEqual(p["row"], "bases: 1 Phase Blade · 2 Berserker Axe", p)

    def test_a_read_in_a_base_records_it_on_its_copy(self):
        a = self.reads["a"]
        self.assertEqual((a["owned"], a["copies"], a["copy"], a["b0"]), (True, 1, 0, "Phase Blade"), a)

    def test_another_base_of_a_runeword_kept_once_is_said_and_never_counted(self):
        b = self.reads["b"]
        self.assertEqual((b["copies"], b["copy"], b["why"], b["b0"]), (1, None, True, "Phase Blade"), b)

    def test_another_base_of_a_runeword_he_wants_more_of_is_another_copy(self):
        c = self.reads["c"]
        self.assertEqual((c["copies"], c["copy"], c["newCopy"], c["b0"], c["b1"]), (2, 1, True, "Phase Blade", "Berserker Axe"), c)

    def test_the_same_base_is_that_copy(self):
        d = self.reads["d"]
        self.assertEqual((d["copies"], d["copy"], d["newCopy"]), (2, 0, False), d)

    def test_a_base_past_what_he_wants_is_never_counted(self):
        e = self.reads["e"]
        self.assertEqual((e["copies"], e["copy"], e["why"]), (2, None, True), e)

    def test_a_read_with_no_base_names_no_copy(self):
        f = self.reads["f"]
        self.assertEqual((f["copies"], f["copy"]), (2, "unset"), f)

    def test_the_row_says_the_bases_the_reads_gave(self):
        self.assertEqual(self.reads["row"], "bases: 1 Phase Blade · 2 Berserker Axe", self.reads["row"])


RED_PROOF = [
    {"why": "REG-3000 - the Keepers box refuses a runeword",
     "file": "bible.html",
     "find": "if(_rwMk) n=_rwMk.name;   /* REG-3000 a runeword is a keeper */",
     "replace": "   /* REG-3000 a runeword is a keeper */",
     "matches": 1, "needs": "node"},
    {"why": "REG-3000 - a name that is exactly a runeword and a grail item is guessed",
     "file": "bible.html",
     "find": "    if (both && both !== rw) return { ask:",
     "replace": "    if (false) return { ask:",
     "matches": 1, "needs": "node"},
    {"why": "REG-3001 - the keeper row says nothing of its copies' bases",
     "file": "bible.html",
     "find": "'+dst.tail+_vmkBases(n, have)+'</div>';",
     "replace": "'+dst.tail+'</div>';",
     "matches": 1, "needs": "node"},
    {"why": "REG-3002 - a judged runeword read never names its copy by base",
     "file": "bible.html",
     "find": "                var _rjR = (base && typeof window._vaultRunewordReadJoin === 'function')",
     "replace": "                var _rjR = (false && typeof window._vaultRunewordReadJoin === 'function')",
     "matches": 1, "needs": "node"},
    {"why": "REG-3002 - a runeword read in another base is never counted as another copy",
     "file": "bible.html",
     "find": "    if (r.mode === 'new') copies[nm] = n + 1;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3002 - a misread base mints a copy of a runeword he keeps one of",
     "file": "bible.html",
     "find": "((typeof _mkWant === 'function' && _mkWant(nm) > n) ? { mode: 'new', copyIx: n } : null)",
     "replace": "({ mode: 'new', copyIx: n })",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
