# -*- coding: utf-8 -*-
"""#146 step 4 (REG-1821) — AN ITEM HE ADDS IN THE VAULT IS HIS, THROUGH THE ONE `owned` DOOR.

His ask (2026-10-01): a Vault '+ Add an item' that uses the planner's item list, source manual, his testimony. The
first cut wrote each pick to a NEW key, d2r_vaultHand, beside the hand ledger the board already keeps: a pick never
reached `owned` — not the dock, not a mule, not the grail count — and every visitor's Vault said "Nothing added by
hand." under a list nothing else read. This law drives the SHIPPED door end to end over the SHIPPED owned door:

  · A PICK IS OWNED, WITH HIS HAND AS ITS RECEIPT. vaultHandTake -> vaultHandAdd -> the board's name resolution
    (_vaultResolveName: "Harlequin Crest" lands on the tile the readers file, "Harlequin Crest (Shako)") ->
    window._ownedAdd(source 'hand'): the name is in `owned` and in d2r_owned, d2r_vaultProv holds a kind:'owned'
    receipt whose source is 'hand' and whose time is the pick's. Nothing is filed: d2r_muleAssign is never written
    (he files it, as every manual filing goes through vaultFile). No d2r_vaultHand key is written.
  · ONLY A NAME THE VAULT DRAWS. The list offers only what ownedPool's own rule (_vaultKeeps) keeps, SAYS how many
    matching planner rows it left out, and the door refuses a crafted recipe / a white base in words — such a name
    would sit in d2r_owned and render nowhere.
  · A SECOND ADD CHANGES NOTHING: an owned name answers 'already' and writes no store.
  · THE SECOND KEY COMES HOME ONCE: every d2r_vaultHand row is added at the time he typed it, the key is removed only
    when every row landed (a row the vault cannot take keeps the key, untouched), an unreadable list is never written
    over, and the migration runs once a page.
  · THE JOINS: renderVault asks the migration before it reads the pool; ownedPool filters by _vaultKeeps; the door
    names no mule and writes no store of its own; the side list's section is gone from the page.
  · THE PLANNER SEARCH is a second door, outside that block. It opens the character-builder picker (search, quality,
    mods) and files a pick only when suggestMule names a mule on this board: a catalogue piece through vaultHandAdd,
    a magic / rare / crafted piece through magicFinds with the real base and the mod lines, owned so the
    count moves, and not also written into the mule map. A set or unique pick is owned and filed under
    the one name the hand door resolves, never the shown name beside that key. Throw-out, keep-on-MAIN,
    a rune answered as the shared stash with no locker id, a name nothing knows, and a white base stay unfiled.
    War gear names the shared locker and is filed there; a missing locker is the same SHARED STASH the load migration
    adds, put back, then the pick is filed. A runeword keeps the base he chose. A new open of a name already filed
    stores another copy and asks the open locker to draw again. The same open does not. The old door still does not
    file, and the migration still does not file a row he typed before.

Drives the shipped ⟦OWNED PROV⟧ door, _vaultKeeps, _vaultResolveName and the ⟦VAULT HAND⟧ block in node, the program
on stdin. A missing node raises — this law does not skip. RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
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

import test_every_owned_door_writes_provenance as OWN  # noqa: E402  the ⟦OWNED PROV⟧ cut and the vault predicate

BIBLE = os.path.join(HERE, "..", "bible.html")
NODE = os.environ.get("NODE") or shutil.which("node")

HAND_A, HAND_B = "  /* ⟦VAULT HAND BEGIN⟧ */\n", "  /* ⟦VAULT HAND END⟧ */\n"
KEEPS_A, KEEPS_B = "  function _vaultKeeps(n){\n", "  function ownedPool(){\n"
KEEP_A, KEEP_B = "  var KEEP_IN_INVENTORY = /^(Annihilus|Hellfire Torch|Gheed'?s Fortune)$/i;", "  /* ══ #264"
RESOLVE_A, RESOLVE_B = "  window._vaultResolveName = function(name){\n", "  window.tvVaultRegister = function(name, witness){\n"
SHARED_A, SHARED_B = "  var SHARED_STASH_RE = ", "  try { window.isSharedStash = isSharedStash; }"
AGG = "  function isAggregate(n){ return /\\((any piece|any|set)\\)\\s*$/i.test(n); }\n"

HARNESS = r"""
var window = globalThis, STORE = {}, WRITES = [], ELS = {}, RENDERS = 0;
window.LSR = { getItem: function(k){ return Object.prototype.hasOwnProperty.call(STORE, k) ? STORE[k] : null; },
               setItem: function(k, v){ WRITES.push(k); STORE[k] = String(v); },
               removeItem: function(k){ WRITES.push('-' + k); delete STORE[k]; } };
window.localStorage = { getItem: function(){ return null; }, setItem: function(){}, removeItem: function(){} };
window.D2R_BUILD = { id: 'vTEST' }; window.D2R_PROFILE = 'main';
function El(id){ this.id = id || ''; this.hidden = true; this._html = ''; this.textContent = ''; this.value = ''; this._attrs = {}; }
El.prototype.setAttribute = function(n, v){ this._attrs[n] = String(v); };
El.prototype.getAttribute = function(n){ return Object.prototype.hasOwnProperty.call(this._attrs, n) ? this._attrs[n] : null; };
Object.defineProperty(El.prototype, 'innerHTML', {
  set: function(h){ this._html = String(h); var re = /id="([^"]+)"/g, m;
    while ((m = re.exec(this._html))){ ELS[m[1]] = new El(m[1]); ELS[m[1]].hidden = false; } },
  get: function(){ return this._html; } });
var document = { getElementById: function(id){ return ELS[id] || null; }, createElement: function(){ return new El(); },
                 body: { appendChild: function(c){ if (c.id) ELS[c.id] = c; } },
                 documentElement: { classList: { contains: function(){ return false; } } } };
var owned = new Set([]);
function persistOwned(){ STORE['d2r_owned'] = JSON.stringify(Array.from(owned)); WRITES.push('d2r_owned'); }
function renderVault(){ RENDERS++; }
var ITEMS = [{ n: 'Harlequin Crest (Shako)' }, { n: 'Stone of Jordan' }, { n: "Arachnid Mesh" }];
var EXTRA_ITEMS = {};
window.findRuneword = function(n){ return n === 'Enigma' ? { n: 'Enigma' } : null; };
window.findSetPiece = function(){ return null; };
%(lanes)s
%(region)s
%(shared)s
%(agg)s
%(keep)s
%(keeps)s
%(resolve)s
%(hand)s
var CAT = [{ id: 'u:shako', name: 'Harlequin Crest', q: 'u' }, { id: 'u:soj', name: 'Stone of Jordan', q: 'u' },
           { id: 'r:enigma', name: 'Enigma', q: 'r' }, { id: 'c88', name: 'Caster Amulet', q: 'c' },
           { id: 'b:amu', name: 'Amulet', q: 'm' }];
window._cbHandCatalog = function(q){ q = String(q || '').toLowerCase();
  return { ok: true, rows: CAT.filter(function(r){ return !q || r.name.toLowerCase().indexOf(q) >= 0; }) }; };
function prov(){ return JSON.parse(STORE['d2r_vaultProv'] || '{}'); }
var OUT = {};
%(body)s
process.stdout.write(JSON.stringify(OUT));
"""


def _src():
    with io.open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _cut(s, a, b, keep_b=False):
    if s.count(a) != 1:
        raise AssertionError("anchor %r matched %d times" % (a[:60], s.count(a)))
    i = s.index(a)
    j = s.index(b, i + len(a))
    return s[i:j + (len(b) if keep_b else 0)]


def code_only(text):
    """`text` with its /* */ and // comments blanked — a guard grades CODE, never the prose that explains it."""
    text = re.sub(r"/\*.{0,6000}?\*/", " ", text, flags=re.S)
    return "\n".join(re.sub(r"(^|\s)//.*$", r"\1", ln) for ln in text.split("\n"))


def _node(body):
    if not NODE:
        raise AssertionError("node is not on this machine — this law does not skip")
    s = _src()
    prog = HARNESS % {"lanes": OWN._lanes(s), "region": OWN.owned_prov_region(s), "shared": _cut(s, SHARED_A, SHARED_B),
                      "agg": AGG if s.count(AGG) == 1 else "/* isAggregate MISSING */",
                      "keep": _cut(s, KEEP_A, KEEP_B),
                      "keeps": _cut(s, KEEPS_A, KEEPS_B), "resolve": _cut(s, RESOLVE_A, RESOLVE_B),
                      "hand": _cut(s, HAND_A, HAND_B), "body": body}
    p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise AssertionError("the hand harness would not run — UNKNOWN, not passing: " + (p.stderr or p.stdout)[-2000:])
    return json.loads(p.stdout)


class AHandAddedItemStaysHis(unittest.TestCase):

    def test_a_pick_is_owned_with_his_hand_as_its_receipt(self):
        out = _node(r"""
          OUT.open = window.vaultHandOpen();
          OUT.list = ELS['vault-hand-list']._html;
          OUT.take = window.vaultHandTake('u:shako');
          OUT.say = ELS['vault-hand-say'].textContent;
          OUT.sayState = ELS['vault-hand-say'].getAttribute('data-state');
          OUT.owned = Array.from(owned);
          OUT.stored = JSON.parse(STORE['d2r_owned'] || '[]');
          OUT.row = prov()['Harlequin Crest (Shako)'] || null;
          OUT.keys = Object.keys(STORE).sort();
          OUT.renders = RENDERS;
          OUT.after = ELS['vault-hand-list']._html;
        """)
        self.assertTrue(out["open"]["ok"])
        self.assertEqual(out["open"]["n"], 3, "the list did not offer exactly the three names the vault draws")
        self.assertEqual(out["open"]["left"], 2)
        self.assertIn('data-id="u:shako"', out["list"])
        self.assertIn('data-id="r:enigma"', out["list"])
        self.assertNotIn('data-id="c88"', out["list"], "a crafted recipe the vault cannot draw was offered")
        self.assertNotIn('data-id="b:amu"', out["list"], "a white base the vault cannot draw was offered")
        self.assertIn("2 matching planner items are not listed", out["list"])
        self.assertEqual(out["take"]["mode"], "added")
        self.assertEqual(out["take"]["name"], "Harlequin Crest (Shako)", "the pick was not filed under the register's name")
        self.assertEqual(out["owned"], ["Harlequin Crest (Shako)"])
        self.assertEqual(out["stored"], ["Harlequin Crest (Shako)"], "the add never reached d2r_owned")
        row = out["row"]
        self.assertIsNotNone(row, "no receipt in d2r_vaultProv — the pick did not go through the owned door")
        self.assertEqual(row["kind"], "owned")
        self.assertEqual(row["source"], "hand")
        self.assertEqual(row["where"], "the Vault (+ Add an item)")
        self.assertTrue(row["tsMeasured"])
        self.assertEqual(out["keys"], ["d2r_owned", "d2r_vaultProv"], "the add wrote a store beyond owned + its receipt")
        self.assertIn("is yours — a name the router already knows is homed", out["say"])
        self.assertEqual(out["sayState"], "added")
        self.assertEqual(out["renders"], 1, "the vault was not repainted after the add")
        self.assertIn("already yours", out["after"])

    def test_a_name_the_vault_cannot_draw_is_refused_and_a_second_add_changes_nothing(self):
        out = _node(r"""
          OUT.craft = window.vaultHandAdd('Caster Amulet', '2026-10-05T12:00:00.000Z');
          OUT.base = window.vaultHandAdd('Amulet', '2026-10-05T12:00:00.000Z');
          OUT.blank = window.vaultHandAdd('  ', null);
          OUT.badTime = window.vaultHandAdd('Stone of Jordan', 'not a date');
          OUT.writes0 = WRITES.slice();
          OUT.first = window.vaultHandAdd('Stone of Jordan', '2026-10-05T12:00:00.000Z');
          var raw = STORE['d2r_vaultProv'], n = WRITES.length;
          OUT.second = window.vaultHandAdd('stone of jordan', '2026-10-06T12:00:00.000Z');
          OUT.same = STORE['d2r_vaultProv'] === raw;
          OUT.writes2 = WRITES.length - n;
          OUT.at = prov()['Stone of Jordan'].at;
        """)
        self.assertEqual(out["craft"]["refused"], "not-drawn")
        self.assertIn("not an item the vault draws", out["craft"]["why"])
        self.assertEqual(out["base"]["refused"], "not-drawn")
        self.assertEqual(out["blank"]["refused"], "no-name")
        self.assertEqual(out["badTime"]["refused"], "no-time")
        self.assertEqual(out["writes0"], [], "a refused add wrote a store")
        self.assertEqual(out["first"]["mode"], "added")
        self.assertEqual(out["second"]["mode"], "already")
        self.assertTrue(out["same"])
        self.assertEqual(out["writes2"], 0, "a second add of an owned name wrote a store")
        self.assertEqual(out["at"], "2026-10-05T12:00:00.000Z", "the receipt is not the time of the first add")

    def test_the_second_key_comes_home_once_and_nothing_he_typed_is_lost(self):
        out = _node(r"""
          STORE['d2r_vaultHand'] = JSON.stringify([
            { name: 'Stone of Jordan', source: 'manual', at: '2026-10-05T12:00:00.000Z', seen: null },
            { name: 'Harlequin Crest', source: 'manual', at: '2026-10-05T13:00:00.000Z', seen: { source: 'stash', at: null } }]);
          OUT.m = window._vaultHandMigrate();
          OUT.again = window._vaultHandMigrate();
          OUT.gone = !Object.prototype.hasOwnProperty.call(STORE, 'd2r_vaultHand');
          OUT.owned = Array.from(owned).sort();
          OUT.at = [prov()['Stone of Jordan'].at, prov()['Harlequin Crest (Shako)'].at];
          OUT.src = prov()['Stone of Jordan'].source;
        """)
        self.assertEqual(out["m"], {"ok": True, "n": 2, "left": 0, "rows": []})
        self.assertIsNone(out["again"], "the migration ran twice in one page")
        self.assertTrue(out["gone"], "every row landed and the second key stayed")
        self.assertEqual(out["owned"], ["Harlequin Crest (Shako)", "Stone of Jordan"])
        self.assertEqual(out["at"], ["2026-10-05T12:00:00.000Z", "2026-10-05T13:00:00.000Z"],
                         "a migrated row was not dated when he typed it")
        self.assertEqual(out["src"], "hand")

        kept = _node(r"""
          var raw = JSON.stringify([{ name: 'Stone of Jordan', source: 'manual', at: '2026-10-05T12:00:00.000Z' },
                                    { name: 'Caster Amulet', source: 'manual', at: '2026-10-05T12:01:00.000Z' }]);
          STORE['d2r_vaultHand'] = raw;
          OUT.m = window._vaultHandMigrate();
          OUT.key = STORE['d2r_vaultHand'];
          OUT.owned = Array.from(owned);
        """)
        self.assertEqual((kept["m"]["n"], kept["m"]["left"]), (1, 1))
        self.assertEqual(kept["key"], '[{"name":"Caster Amulet","source":"manual","at":"2026-10-05T12:01:00.000Z"}]',
                         "the key does not hold exactly the row left, verbatim")
        self.assertEqual(kept["owned"], ["Stone of Jordan"])

        bad = _node(r"""
          STORE['d2r_vaultHand'] = '{';
          OUT.m = window._vaultHandMigrate();
          OUT.raw = STORE['d2r_vaultHand'];
          OUT.writes = WRITES.slice();
        """)
        self.assertFalse(bad["m"]["ok"])
        self.assertEqual(bad["raw"], "{", "an unreadable list was written over")
        self.assertEqual(bad["writes"], [])

    def test_a_row_already_owned_keeps_his_hand_and_one_owned_elsewhere_stays_said(self):
        """REG-1848 — a legacy row whose name is already owned is not landed by being owned."""
        out = _node(r"""
          ELS['vault-hand-left'] = new El('vault-hand-left');
          ['Stone of Jordan', 'Arachnid Mesh', 'Enigma'].forEach(function(n){ owned.add(n); });
          STORE['d2r_vaultProv'] = JSON.stringify({
            'Stone of Jordan': { kind: 'owned', source: 'kai-register', by: 'x', ts: 5, at: '2026-09-01T00:00:00.000Z' },
            'Enigma': { mule: 'runewords', source: 'stash', at: '2026-09-02T00:00:00.000Z' } });
          var raw = JSON.stringify([{ name: 'Stone of Jordan', source: 'manual', at: '2026-10-05T12:00:00.000Z' },
                                    { name: 'Arachnid Mesh', source: 'manual', at: '2026-10-05T12:01:00.000Z' },
                                    { name: 'Enigma', source: 'manual', at: '2026-10-05T12:02:00.000Z' }]);
          STORE['d2r_vaultHand'] = raw;
          OUT.m = window._vaultHandMigrate();
          OUT.paint = window._vaultHandLeftPaint();
          OUT.left = ELS['vault-hand-left']._html; OUT.hidden = ELS['vault-hand-left'].hidden;
          OUT.key = JSON.parse(STORE['d2r_vaultHand'] || 'null');
          OUT.prov = prov();
        """)
        self.assertEqual((out["m"]["n"], out["m"]["left"]), (2, 1))
        self.assertEqual(out["key"], [{"name": "Stone of Jordan", "source": "manual", "at": "2026-10-05T12:00:00.000Z"}],
                         "the key went while a row he typed had not joined the ledger, or kept rows that landed")
        sj = out["prov"]["Stone of Jordan"]
        self.assertEqual(sj["source"], "kai-register", "another door's receipt was overwritten")
        self.assertNotIn("where", sj, "his hand was smeared into another door's receipt")
        mesh = out["prov"]["Arachnid Mesh"]
        self.assertEqual((mesh["kind"], mesh["source"], mesh["at"]), ("owned", "hand", "2026-10-05T12:01:00.000Z"),
                         "an owned name with no receipt did not take his hand as its receipt")
        en = out["prov"]["Enigma"]
        self.assertEqual(en["source"], "stash")
        self.assertEqual((en["ownedBy"]["source"], en["ownedBy"]["at"]), ("hand", "2026-10-05T12:02:00.000Z"),
                         "a filing with no ownedBy did not take his hand")
        self.assertFalse(out["hidden"], "a row left behind is not said on the Vault")
        self.assertIn("1 item you added by hand before this version could not join the vault", out["left"])
        self.assertIn('data-name="Stone of Jordan"', out["left"])
        self.assertIn("already yours through the live reader (KAI register)", out["left"])
        quiet = _node(r"""
          ELS['vault-hand-left'] = new El('vault-hand-left'); ELS['vault-hand-left'].hidden = false;
          window._vaultHandMigrate(); window._vaultHandLeftPaint();
          OUT.hidden = ELS['vault-hand-left'].hidden; OUT.html = ELS['vault-hand-left']._html;
        """)
        self.assertTrue(quiet["hidden"], "a board with no old key shows the left-behind line")
        self.assertEqual(quiet["html"], "")

    def test_the_next_page_load_counts_the_same(self):
        """REG-1866 — two passes over two page loads: a row that joined stays landed, the banner count is stable, and a
        landed row leaves the key."""
        first = _node(r"""
          ELS['vault-hand-left'] = new El('vault-hand-left');
          ['Stone of Jordan', 'Enigma'].forEach(function(n){ owned.add(n); }); persistOwned();
          STORE['d2r_vaultProv'] = JSON.stringify({
            'Stone of Jordan': { kind: 'owned', source: 'kai-register', by: 'x', ts: 5, at: '2026-09-01T00:00:00.000Z' },
            'Enigma': { mule: 'runewords', source: 'stash', at: '2026-09-02T00:00:00.000Z' } });
          STORE['d2r_vaultHand'] = JSON.stringify([{ name: 'Stone of Jordan', source: 'manual', at: '2026-10-05T12:00:00.000Z' },
                                                   { name: 'Enigma', source: 'manual', at: '2026-10-05T12:02:00.000Z' }]);
          OUT.m = window._vaultHandMigrate(); window._vaultHandLeftPaint();
          OUT.banner = (ELS['vault-hand-left']._html.match(/<p class="vault-org-h">([^<]*)/) || [])[1] || null;
          OUT.STORE = STORE;
        """)
        second = _node(r"""
          ELS['vault-hand-left'] = new El('vault-hand-left');
          var S = %s; Object.keys(S).forEach(function(k){ STORE[k] = S[k]; });
          JSON.parse(STORE['d2r_owned']).forEach(function(n){ owned.add(n); });
          var keyBefore = STORE['d2r_vaultHand'], provBefore = STORE['d2r_vaultProv'];
          OUT.m = window._vaultHandMigrate(); window._vaultHandLeftPaint();
          OUT.banner = (ELS['vault-hand-left']._html.match(/<p class="vault-org-h">([^<]*)/) || [])[1] || null;
          OUT.keySame = STORE['d2r_vaultHand'] === keyBefore; OUT.provSame = STORE['d2r_vaultProv'] === provBefore;
          OUT.key = JSON.parse(STORE['d2r_vaultHand'] || 'null');
        """ % json.dumps(first["STORE"]))
        self.assertEqual((first["m"]["n"], first["m"]["left"]), (1, 1))
        self.assertEqual([r["name"] for r in json.loads(first["STORE"]["d2r_vaultHand"])], ["Stone of Jordan"],
                         "a row that landed stayed in the key")
        self.assertEqual(second["m"]["left"], 1, "the next page counted a landed row as left")
        self.assertEqual(second["banner"], first["banner"], "the left-behind banner grew on the next page load")
        self.assertIn("1 item you added by hand", second["banner"])
        self.assertTrue(second["keySame"] and second["provSame"], "a pass that landed nothing wrote a store")
        self.assertEqual([r["name"] for r in second["key"]], ["Stone of Jordan"])

        # and a row the pass joined, still in the key (a page that stopped between the join and the key write), is landed
        joined = _node(r"""
          ['Enigma'].forEach(function(n){ owned.add(n); });
          STORE['d2r_vaultProv'] = JSON.stringify({ 'Enigma': { mule: 'runewords', source: 'stash', at: '2026-09-02T00:00:00.000Z',
            ownedBy: { kind: 'owned', source: 'hand', at: '2026-10-05T12:02:00.000Z' } } });
          STORE['d2r_vaultHand'] = JSON.stringify([{ name: 'Enigma', source: 'manual', at: '2026-10-05T12:02:00.000Z' }]);
          OUT.m = window._vaultHandMigrate();
          OUT.gone = !Object.prototype.hasOwnProperty.call(STORE, 'd2r_vaultHand');
        """)
        self.assertEqual((joined["m"]["n"], joined["m"]["left"]), (1, 0), "a filing that carries his hand was counted left")
        self.assertTrue(joined["gone"])

    def test_a_pass_that_did_not_finish_is_asked_again(self):
        """REG-1849 — the latch closes on a finished pass, not on an attempt."""
        out = _node(r"""
          var real = window.LSR.getItem, n = 0;
          window.LSR.getItem = function(k){ if (k === 'd2r_vaultHand' && n++ === 0) throw new Error('transient'); return real(k); };
          STORE['d2r_vaultHand'] = JSON.stringify([{ name: 'Stone of Jordan', source: 'manual', at: '2026-10-05T12:00:00.000Z' }]);
          OUT.first = window._vaultHandMigrate();
          OUT.second = window._vaultHandMigrate();
          OUT.third = window._vaultHandMigrate();
          OUT.owned = Array.from(owned);
        """)
        self.assertFalse(out["first"]["ok"])
        self.assertIn("asked again on the next paint", out["first"]["why"])
        self.assertEqual((out["second"]["n"], out["second"]["left"]), (1, 0), "a failed read stopped the next paint from trying")
        self.assertIsNone(out["third"], "a finished pass ran again")
        self.assertEqual(out["owned"], ["Stone of Jordan"])

    def test_the_door_says_what_its_door_said(self):
        """REG-1847 — the owned door's answer, and a check that could not be asked, decide what is said."""
        out = _node(r"""
          STORE['d2r_vaultProv'] = '{';
          OUT.noReceipt = window.vaultHandAdd('Stone of Jordan', '2026-10-05T12:00:00.000Z');
          OUT.provRaw = STORE['d2r_vaultProv'];
        """)
        r = out["noReceipt"]
        self.assertEqual((r["mode"], r["receipt"]), ("added", False))
        self.assertIn("its receipt was not written: d2r_vaultProv would not parse", r["why"])
        self.assertEqual(out["provRaw"], "{")
        gone = _node(r"""
          window._ownedAdd = undefined;
          OUT.r = window.vaultHandAdd('Stone of Jordan', '2026-10-05T12:00:00.000Z');
          OUT.owned = Array.from(owned); OUT.keys = Object.keys(STORE);
        """)
        self.assertEqual(gone["r"]["refused"], "no-door")
        self.assertEqual((gone["owned"], gone["keys"]), ([], []))
        amb = _node(r"""
          window._vaultNameAmbiguity = function(){ throw new Error('the known list would not read'); };
          OUT.r = window.vaultHandAdd('Stone of Jordan', '2026-10-05T12:00:00.000Z');
          OUT.owned = Array.from(owned);
        """)
        self.assertEqual(amb["r"]["refused"], "unknown", "a check that raised was read as a yes")
        self.assertIn("could not be asked", amb["r"]["why"])
        self.assertEqual(amb["owned"], [])

    def test_an_unsettled_name_is_its_own_count(self):
        """REG-1850 — a planner row whose item could not be settled is not "a name the vault does not draw"."""
        out = _node(r"""
          window._vaultNameAmbiguity = function(x){ return x === 'Crescent Moon'
            ? { name: x, among: ['Crescent Moon', 'Crescent Moon (amulet)'], why: '"Crescent Moon" names 2 known items' } : null; };
          CAT.push({ id: 'u:cm', name: 'Crescent Moon', q: '' });
          OUT.open = window.vaultHandOpen();
          OUT.list = ELS['vault-hand-list']._html;
        """)
        self.assertEqual((out["open"]["left"], out["open"]["unsettled"]), (2, 1))
        self.assertIn("2 matching planner items are not listed — the vault does not draw them", out["list"])
        self.assertIn("1 matching planner item is not listed — which vault item it names could not be settled", out["list"])

    def test_the_joins(self):
        s = _src()
        code = code_only(s)
        rv = _cut(code, "  function renderVault(){\n", "    renderMultiKeep();\n")
        self.assertEqual(rv.count("window._vaultHandMigrate();"), 1, "renderVault does not bring the second key home")
        self.assertEqual(rv.count("window._vaultHandLeftPaint();"), 1, "renderVault never says what the pass left")
        self.assertEqual(s.count('id="vault-hand-left"'), 1)
        self.assertLess(rv.index("window._vaultHandMigrate();"), rv.index("var poolAll=ownedPool();"),
                        "the migration runs after the pool was read")
        # REG-3042 - the pool is still owned through _vaultKeeps; it also carries a register-held catalogue item, kept the same way
        pool_fn = _cut(code, KEEPS_B, "  function art(n, glyph, size){")
        self.assertIn("var p = Array.from(owned).filter(_vaultKeeps);", pool_fn)
        self.assertIn("_vaultCatalogueItem(n) && _vaultKeeps(n)) p.push(n);", pool_fn)
        self.assertIn("return p.sort();", pool_fn)
        hand = code_only(_cut(s, HAND_A, HAND_B))
        self.assertEqual(hand.count("try { add = window._ownedAdd(nm, { source: 'hand',"), 1, "the door does not use the owned door")
        for banned in ("vaultFile(", "assign[", "suggestMule("):
            self.assertNotIn(banned, hand, "the hand door reaches %s" % banned)
        self.assertEqual(hand.count("setItem("), 1, "the hand door writes a store of its own")
        self.assertEqual(hand.count("window.LSR.setItem(VAULT_HAND_LEGACY, JSON.stringify(kept.map(function(k){ return k.row; })));"), 1,
                         "the hand door's one write is not the legacy key keeping only what is left")
        self.assertEqual(code.count("window.LSR.removeItem(VAULT_HAND_LEGACY)"), 1)
        self.assertNotIn('id="vault-hand"', s, "the side list's section is still on the page")
        self.assertNotIn("vaultHandPaint", code)
        self.assertEqual(s.count('onclick="window.vaultHandOpen()"'), 1)
        self.assertIn('id="tab-vault"', s[:s.find('onclick="window.vaultHandOpen()"')])
        self.assertIn('"d2r_vaultHand"', s[s.find("window._LP_FORKED"):s.find("window._WP_FORKED")],
                      "the legacy key left the fork set — a ladder migration would read Main's rows")

    def test_the_door_asks_the_planner_list_with_the_class_filter_off(self):
        s = _src()
        self.assertEqual(s.count("else rows = _cbForSlot(slot, p.rail, p.host === 'hand');"), 1)
        catalog = _cut(s, "  /* ⟦VAULT HAND CATALOG BEGIN⟧ */\n", "  /* ⟦VAULT HAND CATALOG END⟧ */")
        prog = ("var window = globalThis, ASKED = null, CB_MINV = 'minv';\n"
                "function _cbRowsFor(p){ ASKED = p; return [['u:shako', 'Harlequin Crest', 'u']]; }\n" + catalog
                + "\nvar OUT = window._cbHandCatalog('crest'); OUT.asked = ASKED; process.stdout.write(JSON.stringify(OUT));\n")
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr[-1500:])
        cat = json.loads(p.stdout)
        self.assertTrue(cat["ok"])
        self.assertEqual(cat["rows"], [{"id": "u:shako", "name": "Harlequin Crest", "q": "u"}])
        self.assertEqual(cat["asked"]["host"], "hand")
        self.assertEqual(cat["asked"]["slot"], "minv")

    def test_the_planner_search_opens_the_picker_and_the_hand_door_still_does_not_file(self):
        """The vault search is the character-builder picker. The old + Add an item door still files nothing."""
        s = _src()
        self.assertEqual(s.count('id="vault-planner-q"'), 1)
        self.assertEqual(s.count('onclick="window.vaultHandOpen()"'), 1)
        add_at = s.find('id="vault-planner-q"')
        find_at = s.find('id="vault-find-input"')
        self.assertGreater(add_at, 0)
        self.assertIn('id="tab-vault"', s[:add_at])
        self.assertLess(add_at, find_at, "the add search was put after the finder, or the finder is gone")
        self.assertIn("window.vaultPlannerOpen(this.value)", s)
        self.assertIn("window.vaultFind&&window.vaultFind(this.value)", s)
        opened = _cut(s, "  /* ⟦VAULT PLANNER OPEN BEGIN⟧ */\n", "  /* ⟦VAULT PLANNER OPEN END⟧ */\n")
        filed = _cut(s, "  /* ⟦VAULT PLANNER FILE BEGIN⟧ */\n", "  /* ⟦VAULT PLANNER FILE END⟧ */\n")
        self.assertEqual(opened.count("window._cbHostOpen("), 1)
        self.assertIn("kind: 'inv'", opened)
        self.assertIn("planner: true", opened)
        self.assertIn("fits: function(){ return true; }", opened)
        self.assertIn("window.vaultPlannerFile(entry, token, wopts)", opened)   # REG-2841 - the pick passes its ask
        self.assertLess(s.find("  /* ⟦VAULT HAND END⟧ */\n"), s.find("  /* ⟦VAULT PLANNER FILE BEGIN⟧ */\n"))
        where = "the Vault planner — your search filed it where a reel of it would go"
        self.assertEqual(s.count(where), 1, "the reel-route witness is missing or was copied into a second door")
        hand = _cut(s, HAND_A, HAND_B)
        self.assertNotIn(where, hand)
        self.assertNotIn("vaultFile(", code_only(hand))
        self.assertNotIn("vaultPlannerFile", hand)
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        prog = "new Function(%s); new Function(%s);" % (json.dumps(opened), json.dumps(filed))
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr[-1500:])

    def test_a_planner_pick_files_where_a_reel_of_it_would_go(self):
        """A manual pick takes the reel road. A mule answer files it. Every other answer is said and left alone.
        A new open of a name already filed stores the next copy and asks the open locker to draw it."""
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        s = _src()
        block = _cut(s, "  /* ⟦VAULT PLANNER FILE BEGIN⟧ */\n", "  /* ⟦VAULT PLANNER FILE END⟧ */\n")
        prog = r"""
var window = globalThis, CALLS = [], SAID = [], magicFinds = {}, assign = {}, owned = new Set(), copies = {};
function copyCount(n){ var c = copies && copies[n]; return (c && c > 0) ? c : (owned.has(n) ? 1 : 0); }
function status(m){ SAID.push(String(m)); }
function renderVault(){ CALLS.push('render'); }
function refreshOpenCard(){ CALLS.push('refresh'); }
function persistOwned(){ CALLS.push('persist'); }
function saveA(){ CALLS.push('save'); }
var SHARED_ON = false;
function muleById(id){
  var names = { 'uni-armor': 'UNI-ARMOR', 'magic-rare': 'MAGIC & RARE' };
  if (id === 'shared' && SHARED_ON) return { id: id, name: 'SHARED STASH' };
  return names[id] ? { id: id, name: names[id] } : null;
}
function isSharedStash(nm){ return nm === 'El Rune'; }
function _vaultKeeps(nm){ return nm === 'Monarch'; }
function suggestMule(nm){
  var rec = magicFinds[nm];
  CALLS.push('route:' + nm + ':' + ((rec && rec.q) || '') + ':' + ((rec && rec.base) || '') + ':' + ((rec && rec.mods) ? rec.mods.join('|') : ''));
  return Object.prototype.hasOwnProperty.call(ROUTES, nm) ? ROUTES[nm] : { id: null, unsorted: true, why: 'nothing on the board recognises this name' };
}
var MADESTORE = {};
var LS = {
  getItem: function(k){ return Object.prototype.hasOwnProperty.call(MADESTORE, k) ? MADESTORE[k] : null; },
  setItem: function(k, v){ CALLS.push('ls:' + k); MADESTORE[k] = String(v); }
};
var ROUTES = {};
window._ownedAdd = function(nm, rec){
  CALLS.push('door:' + nm + ':' + ((rec && rec.source) || ''));
  if (!owned.has(nm)) owned.add(nm);
  return { added: true, prov: { ok: true } };
};
window.vaultHandAdd = function(nm, at, opts){
  CALLS.push('own:' + nm + ':' + ((opts && opts.kind) || ''));
  if (!owned.has(nm)) owned.add(nm);
  return { ok: true, mode: 'added', name: nm };
};
window.vaultFile = function(nm, wit, opts){
  CALLS.push('file:' + nm + ':' + opts.mule + ':' + wit.where);
  assign[nm] = opts.mule;
  if (!owned.has(nm)) owned.add(nm);
  return { ok: true, mode: 'filed', mule: opts.mule };
};
window.vaultUnassign = function(nm){ CALLS.push('unfile:' + nm); delete assign[nm]; return { ok: true }; };
var LEDGER = [];
window.kaiChronicleRecord = function(row){
  LEDGER.push(row.name + '|' + row.status + '|' + (row.target || '') + '|' + row.why);
  return row;
};
window._cbItem = function(id){ return { id: id }; };
window._cbShown = function(e, it){
  return { name: e._name, q: e._q, base: e._base || '' };
};
window._cbDb = function(){ return { b: { cm: ['Grand Charm'], mon: ['Monarch'], '7cr': ['Phase Blade'] } }; };
window._cbAf = function(id){ return id === 'vita' ? { _text: '+36 to Life' } : null; };
window._cbAfText = function(a){ return a._text || ''; };
""" + block + r"""
function files(nm){ return CALLS.filter(function(c){ return c.indexOf('file:' + nm + ':') === 0; }); }
var WHERE = 'the Vault planner — your search filed it where a reel of it would go';
ROUTES['Harlequin Crest'] = { id: 'uni-armor', why: 'armor slot' };
var u1 = window.vaultPlannerFile({ id: 'shako', _name: 'Harlequin Crest', _q: 'u' }, 't-u');
var u2 = window.vaultPlannerFile({ id: 'shako', _name: 'Harlequin Crest', _q: 'u' }, 't-u');
var crestSame = copies['Harlequin Crest'] || 0;
var crestAgain = window.vaultPlannerFile({ id: 'shako', _name: 'Harlequin Crest', _q: 'u' }, 't-u2');
ROUTES['Shimmering Grand Charm of Vita'] = { id: 'magic-rare', why: 'registered in Magic and Rare' };
var m1 = window.vaultPlannerFile({ id: 'charm', base: 'cm', _name: 'Shimmering Grand Charm of Vita', _q: 'm', affixes: [{ id: 'vita' }] }, 't-m');
var m2 = window.vaultPlannerFile({ id: 'charm', base: 'cm', _name: 'Shimmering Grand Charm of Vita', _q: 'm', affixes: [{ id: 'vita' }] }, 't-m');
ROUTES['Junk Charm'] = { id: '__throwout', why: 'the planner would vendor it' };
var toss = window.vaultPlannerFile({ id: 'junk', base: 'cm', _name: 'Junk Charm', _q: 'm' }, 't-toss');
ROUTES['Keep Helm'] = { id: '__keep', why: 'your MAIN wears it' };
var keep = window.vaultPlannerFile({ id: 'keep', _name: 'Keep Helm', _q: 'u' }, 't-keep');
ROUTES['El Rune'] = null;
var shared = window.vaultPlannerFile({ id: 'el', _name: 'El Rune', _q: 'u' }, 't-el');
ROUTES['Bone Visor'] = { id: null, unsorted: true, why: 'nothing on the board recognises this name' };
var loose = window.vaultPlannerFile({ id: 'bone', _name: 'Bone Visor', _q: 'u' }, 't-bone');
var white = window.vaultPlannerFile({ id: 'amu', _name: 'Amulet', _q: 'b' }, 't-white');
ROUTES['Monarch'] = { id: 'uni-armor', why: 'armor slot' };
var base = window.vaultPlannerFile({ id: 'mon', base: 'mon', _name: 'Monarch', _q: 'b' }, 't-mon');
ROUTES['Alpha Charm'] = { id: 'magic-rare', why: 'registered in Magic and Rare' };
ROUTES['Beta Charm'] = { id: 'magic-rare', why: 'registered in Magic and Rare' };
window.vaultPlannerFile({ id: 'cm', base: 'cm', _name: 'Alpha Charm', _q: 'm' }, 'same');
var moved = window.vaultPlannerFile({ id: 'cm', base: 'cm', _name: 'Beta Charm', _q: 'm' }, 'same');
var snap = { alpha: magicFinds['Alpha Charm'] || null, alphaHome: assign['Alpha Charm'] || null,
             beta: magicFinds['Beta Charm'] || null, betaHome: assign['Beta Charm'] || null };
ROUTES['Gamma Charm'] = { id: 'magic-rare', why: 'registered in Magic and Rare' };
ROUTES['Delta Charm'] = { id: 'magic-rare', why: 'registered in Magic and Rare' };
window.vaultPlannerFile({ id: 'g', base: 'cm', _name: 'Gamma Charm', _q: 'm' }, 'both');
window.vaultPlannerFile({ id: 'd', base: 'cm', _name: 'Delta Charm', _q: 'm' }, 'both');
ROUTES['Epsilon Charm'] = { id: 'magic-rare', why: 'registered in Magic and Rare' };
ROUTES['Epsilon Two'] = { id: 'magic-rare', why: 'registered in Magic and Rare' };
window.vaultPlannerFile({ id: 'eps', base: 'cm', _name: 'Epsilon Charm', _q: 'm' }, 'tok-a');
window.vaultPlannerFile({ id: 'eps', base: 'cm', _name: 'Epsilon Two', _q: 'm' }, 'tok-b');
assign['Stone of Jordan'] = 'uni-small';
owned.add('Stone of Jordan');
ROUTES['Stone of Jordan'] = { id: 'uni-armor', why: 'armor slot' };
var already = window.vaultPlannerFile({ id: 'soj', _name: 'Stone of Jordan', _q: 'u' }, 't-soj');
var sojSame = copies['Stone of Jordan'] || 0;
var sojTwo = window.vaultPlannerFile({ id: 'soj', _name: 'Stone of Jordan', _q: 'u' }, 't-soj2');
ROUTES['Clear Charm'] = { id: 'magic-rare', why: 'registered in Magic and Rare' };
window.vaultPlannerFile({ id: 'clr', base: 'cm', _name: 'Clear Charm', _q: 'm' }, 'clr');
var cleared = window.vaultPlannerFile(null, 'clr');
ROUTES['Grief'] = { id: 'shared', why: 'war gear: flat damage war weapon - in the shared stash, where every character can reach it' };
var griefNo = window.vaultPlannerFile({ id: 'grief', base: '7cr', _name: 'Grief', _q: 'r', affixes: [{ id: 'ias', rolls: { a: 31 } }], rolls: { ias: 31 } }, 't-g1');
var griefRec = window._vpMadeOf('Grief');
var griefBase = window._vpMadeBase('Grief');
var clearedG = window.vaultPlannerFile(null, 't-g1');
var griefGone = window._vpMadeOf('Grief');
window._vaultEnsureSharedLocker = function(){ CALLS.push('ensure-shared'); SHARED_ON = true; return { id: 'shared', name: 'SHARED STASH' }; };
var griefYes = window.vaultPlannerFile({ id: 'grief', base: '7cr', _name: 'Grief', _q: 'r', affixes: [{ id: 'ias', rolls: { a: 31 } }], rolls: { ias: 31 } }, 't-g2');
ROUTES['Grief Bare'] = { id: 'shared', why: 'war gear: flat damage war weapon - in the shared stash, where every character can reach it' };
var griefBare = window.vaultPlannerFile({ id: 'griefb', _name: 'Grief Bare', _q: 'r' }, 't-gb');
var griefTwo = window.vaultPlannerFile({ id: 'grief', base: '7cr', _name: 'Grief', _q: 'r', affixes: [{ id: 'ias', rolls: { a: 31 } }], rolls: { ias: 31 } }, 't-g3');
var griefSame = window.vaultPlannerFile({ id: 'grief', base: '7cr', _name: 'Grief', _q: 'r', affixes: [{ id: 'ias', rolls: { a: 31 } }], rolls: { ias: 31 } }, 't-g3');
var griefCopies = copies['Grief'] || 0;
ROUTES['Swap Helm'] = { id: 'uni-armor', why: 'armor slot' };
var swapped = window.vaultPlannerFile({ id: 'swap', _name: 'Swap Helm', _q: 'u' }, 't-g3');
var griefAfterSwap = copies['Grief'] || 0;
var griefStill = assign['Grief'] || null;
var griefOwned = owned.has('Grief');
var griefThree = window.vaultPlannerFile({ id: 'grief', base: '7cr', _name: 'Grief', _q: 'r', affixes: [{ id: 'ias', rolls: { a: 31 } }], rolls: { ias: 31 } }, 't-g4');
ROUTES['Defer Helm'] = { id: 'uni-armor', why: 'armor slot' };
window._vaultPlannerOn = true;
var rendersBefore = CALLS.filter(function(c){ return c === 'render'; }).length;
var deferred = window.vaultPlannerFile({ id: 'def', _name: 'Defer Helm', _q: 'u' }, 'defer');
var rendersDuring = CALLS.filter(function(c){ return c === 'render'; }).length;
var dirty = window._vaultPlannerDirty === true;
window._vaultPlannerOn = false;
var OUT = {
  u1: u1, u2: u2, uFiles: files('Harlequin Crest'), ownedU: owned.has('Harlequin Crest'),
  m1: m1, m2: m2, mf: magicFinds['Shimmering Grand Charm of Vita'] || null, mFiles: files('Shimmering Grand Charm of Vita'),
  ownedM: owned.has('Shimmering Grand Charm of Vita'), mAssign: assign['Shimmering Grand Charm of Vita'] || null,
  routeM: CALLS.filter(function(c){ return c.indexOf('route:Shimmering Grand Charm of Vita:') === 0; })[0] || '',
  toss: toss, tossMf: magicFinds['Junk Charm'] || null, tossFiles: files('Junk Charm'),
  keep: keep, keepFiles: files('Keep Helm'),
  shared: shared, sharedFiles: files('El Rune'),
  loose: loose, looseFiles: files('Bone Visor'),
  white: white, whiteOwn: CALLS.filter(function(c){ return c.indexOf('own:Amulet:') === 0; }), whiteFiles: files('Amulet'),
  base: base, baseOwn: CALLS.filter(function(c){ return c === 'own:Monarch:'; }), baseFiles: files('Monarch'),
  moved: moved, alpha: snap.alpha, alphaHome: snap.alphaHome, beta: snap.beta, betaHome: snap.betaHome,
  gamma: magicFinds['Gamma Charm'] || null, delta: magicFinds['Delta Charm'] || null,
  epsilon: magicFinds['Epsilon Charm'] || null, epsilonTwo: magicFinds['Epsilon Two'] || null,
  already: already, sojFiles: files('Stone of Jordan'), sojHome: assign['Stone of Jordan'] || null,
  cleared: cleared, clearMf: magicFinds['Clear Charm'] || null, clearHome: assign['Clear Charm'] || null,
  griefNo: griefNo, griefRec: griefRec, griefBase: griefBase, griefMf: magicFinds['Grief'] || null,
  clearedG: clearedG, griefGone: griefGone, griefYes: griefYes, griefFiles: files('Grief'),
  griefBare: griefBare, bareRec: window._vpMadeOf('Grief Bare'), bareBase: window._vpMadeBase('Grief Bare'),
  ensured: CALLS.filter(function(c){ return c === 'ensure-shared'; }),
  crestSame: crestSame, crestAgain: crestAgain, crestCopies: copies['Harlequin Crest'] || 0,
  sojSame: sojSame, sojTwo: sojTwo, sojCopies: copies['Stone of Jordan'] || 0,
  griefTwo: griefTwo, griefSame: griefSame, griefCopies: griefCopies,
  swapped: swapped, griefAfterSwap: griefAfterSwap, griefStill: griefStill, griefOwned: griefOwned,
  griefThree: griefThree, griefEnd: copies['Grief'] || 0,
  refreshed: CALLS.filter(function(c){ return c === 'refresh'; }).length,
  where: WHERE,
  ledger: LEDGER,
  deferred: deferred, deferHome: assign['Defer Helm'] || null,
  rendersBefore: rendersBefore, rendersDuring: rendersDuring, dirty: dirty
};
process.stdout.write(JSON.stringify(OUT));
"""
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-2000:])
        o = json.loads(p.stdout)
        self.assertTrue(o["u1"]["filed"], o["u1"])
        self.assertEqual(o["u1"]["mule"], "uni-armor")
        self.assertIn(o["where"], o["uFiles"][0])
        self.assertEqual(o["u2"]["mode"], "already")
        self.assertEqual(len(o["uFiles"]), 1, "a second look at the same pick rewrote the filing")
        self.assertTrue(o["ownedU"])
        self.assertEqual(o["mf"]["q"], "magic")
        self.assertEqual(o["mf"]["base"], "Grand Charm", "the magic record stored the shown name instead of the base")
        self.assertEqual(o["mf"]["mods"], ["+36 to Life"])
        self.assertIn(":magic:Grand Charm:+36 to Life", o["routeM"])
        self.assertLess(o["routeM"].find("route:"), 1)
        self.assertTrue(o["m1"]["filed"], o["m1"])
        self.assertIn("MAGIC & RARE", o["m1"]["why"])
        self.assertTrue(o["ownedM"], "a magic save did not count as owned")
        self.assertIsNone(o["mAssign"], "a magic save also wrote the mule map")
        self.assertEqual(o["m2"]["mode"], "already")
        self.assertEqual(len(o["mFiles"]), 0, "a magic save filed the mule map")
        self.assertIn("throw-out", o["toss"]["why"])
        self.assertFalse(o["toss"]["filed"])
        self.assertIsNone(o["tossMf"], "a throw-out pick was left in Magic and Rare")
        self.assertEqual(o["tossFiles"], [])
        self.assertIn("MAIN", o["keep"]["why"])
        self.assertEqual(o["keepFiles"], [])
        self.assertIn("shared stash", o["shared"]["why"])
        self.assertEqual(o["sharedFiles"], [])
        self.assertIn("nothing on the board recognises this name", o["loose"]["why"])
        self.assertEqual(o["looseFiles"], [])
        self.assertIn("white, superior or low base", o["white"]["why"])
        self.assertEqual(o["whiteOwn"], [])
        self.assertEqual(o["whiteFiles"], [])
        self.assertEqual(o["baseOwn"], ["own:Monarch:"])
        self.assertTrue(o["base"]["filed"], o["base"])
        self.assertIsNone(o["alpha"], "the old composed name was left beside the new one")
        self.assertIsNone(o["alphaHome"])
        self.assertEqual(o["beta"]["q"], "magic")
        self.assertIsNone(o["betaHome"], "the replacement charm was also filed on the mule map")
        self.assertTrue(o["moved"]["filed"], o["moved"])
        self.assertIsNotNone(o["gamma"], "a second pick in the same search was removed")
        self.assertIsNotNone(o["delta"])
        self.assertEqual(o["epsilon"]["q"], "magic", "a later search removed a pick from an earlier one")
        self.assertEqual(o["epsilonTwo"]["q"], "magic")
        self.assertEqual(o["already"]["mode"], "copy", o["already"])
        self.assertIn("copy 2", o["already"]["why"])
        self.assertIn("filed to", o["already"]["why"])
        self.assertEqual(o["sojFiles"], [])
        self.assertEqual(o["sojHome"], "uni-small")
        self.assertEqual(o["cleared"]["mode"], "cleared")
        self.assertIsNone(o["clearMf"])
        self.assertIsNone(o["clearHome"])
        self.assertFalse(o["griefNo"]["filed"], o["griefNo"])
        self.assertIn("no mule on this board has id shared", o["griefNo"]["why"])
        self.assertEqual(o["griefRec"]["base"], "7cr")
        self.assertEqual(o["griefRec"]["baseName"], "Phase Blade")
        self.assertEqual(o["griefRec"]["q"], "r")
        self.assertEqual(o["griefRec"]["affixes"][0]["rolls"]["a"], 31)
        self.assertEqual(o["griefBase"], "Phase Blade")
        self.assertIsNone(o["griefMf"], "a runeword was stored as a magic find")
        self.assertEqual(o["clearedG"]["mode"], "cleared")
        self.assertIsNone(o["griefGone"], "clearing the pick left the Phase Blade record behind")
        self.assertTrue(o["griefYes"]["filed"], o["griefYes"])
        self.assertEqual(o["griefYes"]["mule"], "shared")
        self.assertIn("SHARED STASH", o["griefYes"]["why"])
        self.assertEqual(o["ensured"], ["ensure-shared"])
        self.assertEqual(len(o["griefFiles"]), 1)
        self.assertIn(o["where"], o["griefFiles"][0])
        self.assertTrue(o["griefBare"]["filed"], o["griefBare"])
        self.assertIsNone(o["bareRec"], "a runeword with no chosen base was given one")
        self.assertEqual(o["bareBase"], "")
        self.assertEqual(o["crestSame"], 0, "a second look at the same open counted a new copy")
        self.assertEqual(o["crestAgain"]["mode"], "copy", o["crestAgain"])
        self.assertEqual(o["crestCopies"], 2, o["crestAgain"])
        self.assertEqual(len(o["uFiles"]), 1, "a second copy rewrote the filing")
        self.assertEqual(o["sojSame"], 2, "the first add of a name already filed left the count at one")
        self.assertEqual(o["sojTwo"]["mode"], "copy", o["sojTwo"])
        self.assertIn("copy 3", o["sojTwo"]["why"])
        self.assertEqual(o["sojCopies"], 3)
        self.assertEqual(o["sojFiles"], [])
        self.assertEqual(o["sojHome"], "uni-small")
        self.assertGreater(o["refreshed"], 0, "the open locker was not asked to draw the new copy")
        self.assertEqual(o["griefTwo"]["mode"], "copy", o["griefTwo"])
        self.assertTrue(o["griefTwo"]["filed"], o["griefTwo"])
        self.assertEqual(o["griefTwo"]["mule"], "shared")
        self.assertIn("copy 2", o["griefTwo"]["why"])
        self.assertIn("filed to", o["griefTwo"]["why"], "the Saved plate lights only when the sentence says filed to")
        self.assertEqual(o["griefSame"]["mode"], "already", "saving the same open again counted a third copy")
        self.assertEqual(o["griefCopies"], 2)
        self.assertEqual(len(o["griefFiles"]), 1, "the second Grief rewrote the filing")
        # #183 (REG-2530): a DIFFERENT item picked in the same open is a second add, never a swap - REG-2267's "0" here
        # took back the copy the Grief pick had just filed (GrokBot V0: v3740:63 / v3742r:72 red, d2r_copies lost Grief).
        # Only a re-roll or a clear of the Grief pick itself takes its copy back
        # (tv/test_a_second_planner_pick_keeps_the_first_picks_copy.py).
        self.assertEqual(o["griefAfterSwap"], 2, "a different pick in the same open took back the Grief copy it had filed")
        self.assertEqual(o["griefStill"], "shared", "leaving that open unfiled the first Grief")
        self.assertTrue(o["griefOwned"])
        self.assertTrue(o["swapped"]["filed"], o["swapped"])
        self.assertEqual(o["swapped"]["mule"], "uni-armor")
        self.assertEqual(o["griefThree"]["mode"], "copy", o["griefThree"])
        self.assertEqual(o["griefEnd"], 3, "a later open of Grief did not file the next copy beside the first two")
        filed_why = "|filed-by-hand|%s|you filed it from the vault planner"
        self.assertEqual(o["ledger"].count("Harlequin Crest" + filed_why % "uni-armor"), 1, o["ledger"])
        self.assertEqual(o["ledger"].count("Shimmering Grand Charm of Vita" + filed_why % "magic-rare"), 0, o["ledger"])
        self.assertEqual(o["ledger"].count("Grief" + filed_why % "shared"), 1, o["ledger"])
        self.assertEqual(o["ledger"].count("Monarch" + filed_why % "uni-armor"), 1, o["ledger"])
        self.assertFalse(any(row.startswith("Junk Charm|") for row in o["ledger"]), o["ledger"])
        self.assertFalse(any(row.startswith("Amulet|") for row in o["ledger"]), o["ledger"])
        self.assertTrue(o["deferred"]["filed"], o["deferred"])
        self.assertEqual(o["deferHome"], "uni-armor")
        self.assertEqual(o["rendersDuring"], o["rendersBefore"], "a planner roll redrew the vault")
        self.assertTrue(o["dirty"], "closing the planner would have nothing to draw")
        self.assertEqual(o["ledger"].count("Defer Helm" + filed_why % "uni-armor"), 1, o["ledger"])

    def test_one_set_add_owns_the_resolved_piece_and_files_only_that(self):
        """One set add used to own the slot key and file the bare name. Elad deleted the Unsorted
        copy and the mule copy stayed. The hand door's name is the only record."""
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        block = _cut(_src(), "  /* ⟦VAULT PLANNER FILE BEGIN⟧ */\n", "  /* ⟦VAULT PLANNER FILE END⟧ */\n")
        prog = r"""
var window = globalThis, CALLS = [], magicFinds = {}, assign = {}, owned = new Set(), copies = {};
function copyCount(n){ var c = copies && copies[n]; return (c && c > 0) ? c : (owned.has(n) ? 1 : 0); }
function status(){}
function renderVault(){}
function refreshOpenCard(){}
function persistOwned(){}
function saveA(){}
function muleById(id){ return id === 'sets-rest' ? { id: id, name: 'SETS-REST' } : null; }
function suggestMule(nm){
  return { id: 'sets-rest', why: 'set piece: Aldur' };
}
window._vaultResolveName = function(nm){
  if (nm === "Aldur's Deception") return "Aldur's Deception (armor)";
  if (nm === "Tal Rasha's Horadric Crest") return "Tal Rasha's Horadric Crest (helm)";
  return nm;
};
window.vaultHandAdd = function(nm){
  var resolved = window._vaultResolveName(nm);
  CALLS.push('own:' + resolved);
  if (!owned.has(resolved)) owned.add(resolved);
  return { ok: true, mode: 'added', name: resolved };
};
window.vaultFile = function(nm, wit, opts){
  CALLS.push('file:' + nm + ':' + opts.mule);
  assign[nm] = opts.mule;
  if (!owned.has(nm)) owned.add(nm);
  return { ok: true, mode: 'filed', mule: opts.mule };
};
window._cbItem = function(id){ return { id: id }; };
window._cbShown = function(e){ return { name: e._name, q: e._q, base: '' }; };
""" + block + r"""
var a1 = window.vaultPlannerFile({ id: 'aldur', _name: "Aldur's Deception", _q: 's' }, 't-set');
var a2 = window.vaultPlannerFile({ id: 'aldur', _name: "Aldur's Deception", _q: 's' }, 't-set');
var t1 = window.vaultPlannerFile({ id: 'tal', _name: "Tal Rasha's Horadric Crest", _q: 's' }, 't-tal');
var OUT = {
  a1: a1, a2: a2, t1: t1,
  owned: Array.from(owned),
  assign: assign,
  owns: CALLS.filter(function(c){ return c.indexOf('own:') === 0; }),
  files: CALLS.filter(function(c){ return c.indexOf('file:') === 0; })
};
process.stdout.write(JSON.stringify(OUT));
"""
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-2000:])
        o = json.loads(p.stdout)
        armor = "Aldur's Deception (armor)"
        bare = "Aldur's Deception"
        helm = "Tal Rasha's Horadric Crest (helm)"
        crest = "Tal Rasha's Horadric Crest"
        self.assertEqual(o["a1"]["mule"], "sets-rest", o["a1"])
        self.assertTrue(o["a1"]["filed"], o["a1"])
        self.assertIn("SETS-REST", o["a1"]["why"])
        self.assertEqual(o["a2"]["mode"], "already", o["a2"])
        self.assertEqual(o["owned"], [armor, helm], o["owned"])
        self.assertEqual(o["assign"], {armor: "sets-rest", helm: "sets-rest"}, o["assign"])
        self.assertNotIn(bare, o["owned"])
        self.assertNotIn(crest, o["owned"])
        self.assertNotIn(bare, o["assign"])
        self.assertNotIn(crest, o["assign"])
        self.assertEqual(o["owns"], ["own:" + armor, "own:" + armor, "own:" + helm], o["owns"])
        self.assertEqual(o["files"], ["file:" + armor + ":sets-rest", "file:" + helm + ":sets-rest"], o["files"])
        self.assertTrue(o["t1"]["filed"], o["t1"])

    def test_a_slow_forge_scan_serves_the_whole_draw(self):
        """A forge scan slower than the 400ms memo used to expire before it was stored, so every
        later base ran the scan again. One draw shares one scan, and the memo is counted from
        when the scan finished."""
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        block = _cut(_src(), "var _spareScanCache = null, _spareScanAt = 0, _spareScanPass = 0;\n",
                     "window._spareBaseInfo = _spareBaseInfo;\n", keep_b=True)
        prog = r"""
var window = globalThis, calls = 0;
window.forgeScan = function(){
  calls++;
  var t = Date.now();
  while (Date.now() - t < 450) {}
  return { now: [{ rw: 'Spirit', base: { name: 'Monarch' }, baseOver: false }], pipeline: [], onestep: [] };
};
""" + block + r"""
window._sparePass = 7;
var a = window._spareBaseInfo('Sacred Targe', [{ n: 'Spirit' }]);
var b = window._spareBaseInfo('Akaran Targe', [{ n: 'Spirit' }]);
var during = calls;
window._sparePass = 0;
var c = window._spareBaseInfo('Royal Shield', [{ n: 'Spirit' }]);
var after = calls;
var t = Date.now();
while (Date.now() - t < 450) {}
window._spareBaseInfo('Sacred Targe', [{ n: 'Spirit' }]);
process.stdout.write(JSON.stringify({
  during: during, after: after, later: calls,
  covered: (a.covered && a.covered.Spirit) || [],
  same: JSON.stringify(a.covered) === JSON.stringify(b.covered)
}));
"""
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-2000:])
        o = json.loads(p.stdout)
        self.assertEqual(o["during"], 1, "one draw ran the scan once per base: %s" % o)
        self.assertEqual(o["after"], 1, "a finished scan was already expired: %s" % o)
        self.assertEqual(o["later"], 2, "the memo never expired: %s" % o)
        self.assertEqual(o["covered"], ["Monarch"], o)
        self.assertTrue(o["same"], o)

    def test_one_draw_reads_the_witness_store_once(self):
        """Forty evidence reads during one vault draw hit the witness store once.
        A write during that draw is the next read. A click outside a draw reads again."""
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        s = _src()
        self.assertEqual(s.count("window._provHeld = true;"), 1)
        self.assertEqual(s.count("window._provHeld = false;"), 1)
        block = _cut(s, "  function _witnessRaw(){\n", "  function _provDrop(names){\n")
        prog = (
            "var window = globalThis, reads = 0;\n"
            "var PROV_KEY = 'd2r_vaultProv';\n"
            "var RAW = '{\"Spirit\":{\"kind\":\"filing\",\"locked\":true}}';\n"
            "window.LSR = { getItem: function(){ reads++; return RAW; },"
            " setItem: function(k, v){ RAW = String(v); } };\n"
            + block
            + "window._provHeld = true;\n"
            "window._provHoldSeen = false;\n"
            "var n = 0;\n"
            "for (var i = 0; i < 40; i++) { if (_provAll().Spirit && _provAll().Spirit.locked) n++; }\n"
            "var during = reads;\n"
            "_provWrite({ Spirit: { kind: 'filing', locked: false }, Monarch: { kind: 'filing' } });\n"
            "var afterWrite = reads;\n"
            "var row = _provAll();\n"
            "window._provHeld = false;\n"
            "window._provHoldSeen = false;\n"
            "window._provObjReady = false;\n"
            "_provAll();\n"
            "process.stdout.write(JSON.stringify({ during: during, afterWrite: afterWrite,"
            " n: n, monarch: !!row.Monarch, locked: row.Spirit.locked, after: reads }));\n"
        )
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-2000:])
        o = json.loads(p.stdout)
        self.assertEqual(o["during"], 1, o)
        self.assertEqual(o["afterWrite"], 1, o)
        self.assertEqual(o["n"], 40, o)
        self.assertTrue(o["monarch"], o)
        self.assertFalse(o["locked"], o)
        self.assertEqual(o["after"], 2, o)

    def test_a_draw_filter_keeps_the_owned_receipt(self):
        """The prune ignores an owned receipt. The same draw still reads that receipt afterwards.
        Measured on v3715: the filter deleted the receipt from the held store, and the chip line went blank."""
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        s = _src()
        live = "    var _pvLive = _provAll();\n"
        self.assertEqual(s.count(live), 1)
        chip = "window._vaultEvidenceChip(n, 'vc-ev')"
        self.assertGreater(s.index(chip), s.index(live))
        block = _cut(s, "  function _witnessRaw(){\n", "  function _provDrop(names){\n")
        filt = _cut(s, live, "    Object.keys(assign).forEach(function(n){\n")
        prog = (
            "var window = globalThis, reads = 0;\n"
            "var PROV_KEY = 'd2r_vaultProv';\n"
            "var RAW = '{\"Spirit\":{\"kind\":\"filing\",\"locked\":true},"
            "\"Monarch\":{\"kind\":\"owned\",\"source\":\"hand\",\"by\":\"+ Add an item\"}}';\n"
            "window.LSR = { getItem: function(){ reads++; return RAW; },"
            " setItem: function(k, v){ RAW = String(v); } };\n"
            + block
            + "window._provHeld = true;\n"
            "window._provHoldSeen = false;\n"
            + filt
            + "var after = _provAll();\n"
            "var line = after.Monarch ? (after.Monarch.source + ' kept') : '';\n"
            "process.stdout.write(JSON.stringify({ reads: reads, monarch: !!after.Monarch, line: line,"
            " spiritInPrune: Object.prototype.hasOwnProperty.call(_pvW6, 'Spirit'),"
            " monarchInPrune: Object.prototype.hasOwnProperty.call(_pvW6, 'Monarch'),"
            " locked: !!after.Spirit && after.Spirit.locked === true }));\n"
        )
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-2000:])
        o = json.loads(p.stdout)
        self.assertEqual(o["reads"], 1, o)
        self.assertTrue(o["monarch"], o)
        self.assertEqual(o["line"], "hand kept", o)
        self.assertTrue(o["spiritInPrune"], o)
        self.assertFalse(o["monarchInPrune"], o)
        self.assertTrue(o["locked"], o)

    def test_a_long_review_builds_only_the_open_cards(self):
        """A review of 40 names builds the first screen. The rest wait for the closed details."""
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        s = _src()
        self.assertNotIn("names.map(cardFor)", s)
        self.assertNotIn("_otherN.map(cardFor)", s)
        self.assertNotIn("_loSetN.map(cardFor)", s)
        self.assertEqual(s.count("var VAULT_REVIEW_OPEN = 12;\n"), 1)
        block = _cut(s, "  var VAULT_REVIEW_OPEN = 12;\n", "  function renderThrowoutReview(){\n")
        prog = (
            block
            + "var names = [];\n"
            "for (var i = 0; i < 40; i++) names.push('Base ' + i);\n"
            "var sl = _reviewSlice(names);\n"
            "var built = 0;\n"
            "function cardFor(){ built++; return '<div class=\"to-card\"></div>'; }\n"
            "sl.open.forEach(cardFor);\n"
            "process.stdout.write(JSON.stringify({ open: sl.open.length, rest: sl.rest.length, built: built,"
            " first: sl.open[0], lastOpen: sl.open[11], firstRest: sl.rest[0] }));\n"
        )
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-2000:])
        o = json.loads(p.stdout)
        self.assertEqual(o["open"], 12, o)
        self.assertEqual(o["rest"], 28, o)
        self.assertEqual(o["built"], 12, o)
        self.assertEqual(o["first"], "Base 0", o)
        self.assertEqual(o["lastOpen"], "Base 11", o)
        self.assertEqual(o["firstRest"], "Base 12", o)

    def test_a_vault_item_click_keeps_the_floating_card(self):
        """A locker cell, a shared-stash tile, and the other vault item chips stay on the vault.
        The floating card is the click. The runeword page is not."""
        s = _src()
        a = s.find("function renderMultiKeep(){")
        b = s.find("\nfunction renderJournal(){")
        self.assertGreater(a, 0)
        self.assertGreater(b, a)
        self.assertNotIn("window.openDrop", s[a:b], "a vault item click still leaves the vault")
        journal = s[b:s.find("\n  function persistOwned(){", b)]
        self.assertNotIn("window.openDrop", journal, "a journal chip still leaves the vault")
        self.assertNotIn(
            "onclick=\"window.openDrop&&window.openDrop('\"+jsArg(p.n)+\"')\"",
            s, "the shared-stash tile still opens the item page")
        dismiss = s.find("a click can re-render")
        self.assertGreater(dismiss, 0)
        prose = s.find("THE PROSE LANE, PURELY ADDITIVE", dismiss)
        self.assertGreater(prose, dismiss, "the click guard has no end anchor")
        keep = s[dismiss:prose]
        self.assertIn(".vd-item, .vm-cell, .vrg-row, .vmk-name, .to-name, .vj-chip", keep)
        self.assertIn("!t.closest('button, a, input, textarea, select')", keep)
        self.assertIn("!chip.classList.contains('vd-db')", keep)
        self.assertNotIn("the item's card opens as always", s)

    def test_the_shared_stash_locker_cannot_be_deleted(self):
        """SHARED STASH is the account locker. The shelf offers no delete, and the door
        returns before the confirm, so a call that names it leaves the items filed."""
        s = _src()
        self.assertIn('class="vm-lock"', s)
        self.assertIn(
            "SHARED STASH stays. It cannot be deleted, and its items do not return to the dock.",
            s)
        self.assertIn(
            "(_vmAddedMule(m) ? '<button class=\"vm-tool\" onclick=\"event.stopPropagation();window.vaultDeleteMule(",
            s)  # REG-2195 — the shelf offers delete only for a mule he added
        added = _cut(s, "  function _vmAddedMule(m){", "  window.vaultDeleteMule = async function(id){\n")
        fn = _cut(s, "  window.vaultDeleteMule = async function(id){\n",
                  "  window.vaultReset = async function(){\n")
        prog = (
            "var window = globalThis;\n"
            # REG-2195 — a deletable mule is one he ADDED (added:true / mint id). WIP is the deletable
            # stand-in. SHARED also carries added:true ON PURPOSE: it isolates the `id==='shared'` early
            # return as the SOLE thing refusing it, so the RED_PROOF that removes that line can go red —
            # without added:true the `!_vmAddedMule` guard masks the shared guard and the proof is BLIND.
            # It proves a stronger law too: shared is refused even if it looked like an added mule.
            "var roster = [{id:'shared', name:'SHARED STASH', added:true}, {id:'wip', name:'WIP', added:true}];\n"
            "var assign = { Grief: 'shared', Shako: 'wip' };\n"
            "function muleById(id){ return roster.find(function(m){ return m.id===id; }); }\n"
            "var asked = [];\n"
            "function uiConfirm(msg){ asked.push(msg); return Promise.resolve(true); }\n"
            "function saveR(){}\nfunction saveA(){}\nfunction renderVault(){}\n"
            "function _provAll(){ return {}; }\nfunction _provWrite(){}\n"
            + added + fn
            + "Promise.resolve().then(function(){ return window.vaultDeleteMule('shared'); })"
            ".then(function(){ return window.vaultDeleteMule('wip'); })"
            ".then(function(){ process.stdout.write(JSON.stringify({"
            " ids: roster.map(function(m){ return m.id; }),"
            " grief: assign.Grief || null,"
            " shako: Object.prototype.hasOwnProperty.call(assign,'Shako') ? assign.Shako : null,"
            " asked: asked })); });\n"
        )
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-1500:])
        o = json.loads(p.stdout)
        self.assertIn("shared", o["ids"])
        self.assertNotIn("wip", o["ids"], "a real mule delete stopped working")
        self.assertEqual(o["grief"], "shared")
        self.assertIsNone(o["shako"])
        self.assertEqual(o["asked"], ["Delete locker WIP? Its items return to the unsorted dock."])

    def test_the_planner_card_and_the_sort_click_meet_the_stored_base(self):
        """The hover prefers the stored Phase Blade, and his Auto-Sort click can file that pick.
        The picture gate stays the one line it was, so a found-ever receipt with no picture still stops."""
        s = _src()
        self.assertEqual(s.count("      if (!_hasPicture(row)){ out.noPicture.push(name); return; }\n"), 1)
        pic = s.find("      if (!_hasPicture(row)){ out.noPicture.push(name); return; }\n")
        hand = s.find("  function _plannerHandRow(name, row){")
        self.assertGreater(hand, 0)
        self.assertLess(hand, pic, "the planner-hand branch was placed after the picture gate")
        self.assertEqual(s.count("    var filed = window.vaultFile(nm, { by: 'hand', at: at, where: VP_WHERE }, { mule: id });\n"), 1)
        self.assertIn('"d2r_plannerMade"', s[s.find("window._LP_FORKED"):s.find("window._WP_FORKED")])
        self.assertEqual(s.count("var sh={id:'shared', name:'SHARED STASH', icon:'📦', note:SHARED_NOTE};"), 1)
        self.assertIn("Add an item", s)
        self.assertIn("Find on a mule", s)
        self.assertIn("Saved into the vault", s)
        self.assertLess(s.find('id="vault-planner-q"'), s.find('id="vault-find-input"'))
        tip = s.find("function _arttipResolve(nm){")
        built = s.find("_plannerBuiltTip(nm)", tip)
        word = s.find("findRuneword(nm)", tip)
        self.assertGreater(built, tip)
        self.assertLess(built, word, "the catalogue runeword card still wins over the stored base")
        self.assertEqual(s.count("artUrl(nm) || artUrl(r.artName)"), 1)
        self.assertIn("r.builtBase && artUrl(r.artName)", s)
        self.assertIn("window._vpMadeBase", s)
        hand_fn = _cut(s, "  function _plannerHandRow(name, row){\n", "  function _plannerPropose(name){\n")
        self.assertIn("blob.indexOf('+ Add an item')", hand_fn)
        self.assertNotIn("row.source === 'hand'", hand_fn)
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        prog = (
            "var window = globalThis;\n"
            "window._vpMadeOf = function(){ return null; };\n"
            + hand_fn
            + "process.stdout.write(JSON.stringify({\n"
            "  add: _plannerHandRow('Titan', { source: 'hand', by: '+ Add an item', where: 'the Vault (+ Add an item)', looks: [] }),\n"
            "  plan: _plannerHandRow('Spirit', { by: 'the Vault planner', where: 'the Vault planner' }),\n"
            "  ownedBy: _plannerHandRow('Grief', { kind: 'filing', ownedBy: { by: '+ Add an item', where: 'the Vault (+ Add an item)' } }),\n"
            "  receipt: _plannerHandRow('Insight', { kind: 'owned', source: 'kai-register', by: 'law', where: '', looks: [] }),\n"
            "  forge: _plannerHandRow('Monarch', { source: 'hand', by: 'forge base restore', where: 'un-marking Spirit gave its base back', looks: [] })\n"
            "}));\n"
        )
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-1500:])
        o = json.loads(p.stdout)
        self.assertTrue(o["add"], "a catalog add was treated as a sighting with no picture")
        self.assertTrue(o["plan"])
        self.assertTrue(o["ownedBy"])
        self.assertFalse(o["receipt"], "a found-ever receipt with no picture passed the hand gate")
        self.assertFalse(o["forge"], "a forge restore passed the catalog-hand gate")
        self.assertIn("html{overflow-x:clip;overflow-y:auto}", s)
        self.assertIn("setTimeout(draw, 0)", s)
        self.assertIn("setTimeout(paint, 0)", s)
        opened = _cut(s, "  /* ⟦VAULT PLANNER OPEN BEGIN⟧ */\n", "  /* ⟦VAULT PLANNER OPEN END⟧ */\n")
        self.assertIn("planner: true", opened)
        self.assertNotIn("vaultFile(", opened)

    def test_the_shared_stash_card_draws_each_copy(self):
        """The locker card draws one rectangle per copy, on the shared stash and on a mule."""
        s = _src()
        self.assertEqual(s.count("var drawn = _shelfDrawNames(items, m.id);\n"), 1)
        self.assertEqual(s.count("var itemRows = drawn.map(function(n){\n"), 1)
        self.assertEqual(s.count("var total = drawn.length + magicItems.length;\n"), 1)
        block = _cut(s, "  function _shelfCopyCount(n, muleId){\n",
                     "  try { window._shelfDrawNames = _shelfDrawNames; window._shelfCopyCount = _shelfCopyCount; } catch (e) {}\n")
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        prog = (
            "function copyCount(n){ return n === 'Grief' ? 2 : (n === 'Windforce' ? 5 : 1); }\n"
            + block
            + "process.stdout.write(JSON.stringify({\n"
            "  shared: _shelfDrawNames(['Grief', 'Shako'], 'shared'),\n"
            "  mule: _shelfDrawNames(['Windforce'], 'uni-weap'),\n"
            "  one: _shelfDrawNames(['Shako'], 'shared')\n"
            "}));\n"
        )
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-1500:])
        o = json.loads(p.stdout)
        self.assertEqual(o["shared"], ["Grief", "Grief", "Shako"])
        self.assertEqual(o["mule"], ["Windforce", "Windforce", "Windforce", "Windforce", "Windforce"])
        self.assertEqual(o["one"], ["Shako"])

    def test_the_three_keepers_are_drawn_and_stay_off_the_mule_map(self):
        """Annihilus, Hellfire Torch and Gheed's Fortune are drawn. A magic charm is not, so the registered panel cannot count it twice."""
        s = _src()
        keeps = code_only(_cut(s, KEEPS_A, KEEPS_B))
        self.assertEqual(keeps.count("KEEP_IN_INVENTORY.test(_keepName(n))"), 1)
        self.assertNotIn("magicFinds", keeps)
        out = _node(r"""
          OUT.torch = window.vaultHandAdd('Hellfire Torch', '2026-10-13T12:00:00.000Z');
          OUT.anni = window.vaultHandAdd('Annihilus', '2026-10-13T12:00:00.000Z');
          OUT.gheed = window.vaultHandAdd("Gheed's Fortune", '2026-10-13T12:00:00.000Z');
          OUT.owned = Array.from(owned).sort();
          OUT.keys = Object.keys(STORE).sort();
          var magicFinds = { 'Shimmering Grand Charm of Vita': { q: 'magic', base: 'Grand Charm', mods: ['+20 to Life'] } };
          OUT.charm = _vaultKeeps('Shimmering Grand Charm of Vita');
          OUT.plain = _vaultKeeps('Grand Charm');
          OUT.base = _vaultKeeps('Amulet');
          OUT.enigma = _vaultKeeps('Enigma');
          OUT.shako = _vaultKeeps('Harlequin Crest (Shako)');
        """)
        self.assertEqual(out["torch"]["mode"], "added", out["torch"])
        self.assertEqual(out["anni"]["mode"], "added", out["anni"])
        self.assertEqual(out["gheed"]["mode"], "added", out["gheed"])
        self.assertEqual(out["torch"]["name"], "Hellfire Torch")
        self.assertEqual(out["gheed"]["name"], "Gheed's Fortune")
        self.assertEqual(out["owned"], ["Annihilus", "Gheed's Fortune", "Hellfire Torch"])
        self.assertNotIn("d2r_muleAssign", out["keys"])
        self.assertFalse(out["charm"], "a magic charm passed the draw rule and would be counted twice")
        self.assertFalse(out["plain"])
        self.assertFalse(out["base"])
        self.assertTrue(out["enigma"])
        self.assertTrue(out["shako"])

    def test_a_curly_or_apostropheless_keeper_still_draws(self):
        """REG-2191 — the catalogue stores "Gheed’s Fortune" with a CURLY apostrophe, so the straight-quote
        KEEP_IN_INVENTORY regex matched its own canonical name NOWHERE: _vaultKeeps said false, the item fell
        out of ownedPool and was drawn on no mule and in no keep advisory, while FIND still said it "stays with
        your MAIN". Both keeper deciders (suggestMule's router and _vaultKeeps) now fold every apostrophe
        variant to a straight one through _keepName before testing, so a curly, a left-curly, a straight, a
        bare "Gheeds" and the padded form all answer the SAME — and a near-miss name still does not."""
        s = _src()
        # Both keeper-deciders fold the name the SAME way. A split here is the bug: the router files it __keep
        # while _vaultKeeps drops it from the pool, so it is drawn nowhere. Pin that BOTH call _keepName.
        # REG-2191 pins the LAW, not a count: EVERY KEEP_IN_INVENTORY.test must fold through _keepName — a raw-name
        # compare is the split that drew a curly keeper nowhere. REG-2207 added two more folders (_dockNames and
        # renderVaultRegistered), so the number grew from 2 to 4; the invariant that holds at any count is that no
        # .test compares a RAW name, plus at least the two deciders (router + _vaultKeeps) fold.
        _co = code_only(s)
        self.assertEqual(_co.count("KEEP_IN_INVENTORY.test("), _co.count("KEEP_IN_INVENTORY.test(_keepName("),
                         "every KEEP_IN_INVENTORY.test must fold through _keepName — a raw-name compare is the REG-2191 split")
        self.assertGreaterEqual(_co.count("KEEP_IN_INVENTORY.test(_keepName("), 2,
                                "at least the router and _vaultKeeps must fold the name through _keepName (REG-2191)")
        out = _node(r"""
          OUT.curly    = _vaultKeeps('Gheed’s Fortune');
          OUT.left     = _vaultKeeps('Gheed‘s Fortune');
          OUT.straight = _vaultKeeps("Gheed's Fortune");
          OUT.noApos   = _vaultKeeps('Gheeds Fortune');
          OUT.padded   = _vaultKeeps('  Gheed’s Fortune  ');
          OUT.near     = _vaultKeeps('Gheed’s Fortuna');
          OUT.other    = _vaultKeeps('Random Rare Ring');
        """)
        self.assertTrue(out["curly"], "the catalogue's own curly Gheed’s Fortune must be a keeper (REG-2191)")
        self.assertTrue(out["left"])
        self.assertTrue(out["straight"])
        self.assertTrue(out["noApos"], "a bare 'Gheeds Fortune' must be a keeper (REG-2191)")
        self.assertTrue(out["padded"])
        self.assertFalse(out["near"], "a near-miss name must NOT be folded into a keeper")
        self.assertFalse(out["other"])

    def test_a_registered_charm_is_found_and_a_keeper_says_main(self):
        """FIND searches Magic & Rare. A keep proposal says MAIN and does not open a mule."""
        s = _src()
        find = _cut(s, "  window.vaultFind = function(q){\n", "  // ── render ──\n")
        where = _cut(s, "  function _vaultWhereIs(n){\n", "  window._vaultWhereIs = _vaultWhereIs;\n", keep_b=True)
        matcher = _cut(s, "  var _VF_ALIAS = { soj:'stone of jordan',", "  window._vaultFindMatches = _vaultFindMatches;\n", keep_b=True)
        self.assertEqual(find.count("Object.keys(magicFinds)"), 1)
        self.assertEqual(find.count("_vaultFindMatches(pool, q)"), 1)  # REG-2194 — FIND delegates to the ranked matcher
        self.assertEqual(where.count("pg.kind === 'keep'"), 1)
        # REG-2895 - a register keeper's home is the one rule's (a charm on SHARED / CHARMS); this cut carries no rule,
        # so the fallback MAGIC & RARE answers here, which is what the source must still say
        self.assertEqual(where.count("mid = (typeof _mfKeeperHome === 'function' ? _mfKeeperHome(nm) : 'magic-rare')"), 1)
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        prog = (
            "var window = globalThis, assign = {};\n"
            "function isAggregate(n){ return /\\((any piece|any|set)\\)\\s*$/i.test(n); }\n"
            "function isSharedStash(n){ return n === 'Ist'; }\n"
            "function ownedPool(){ return ['Harlequin Crest (Shako)']; }\n"
            "function art(){ return ''; }\n"
            "function esc(t){ return String(t); }\n"
            "function jsArg(t){ return String(t); }\n"
            "function muleById(){ return null; }\n"
            "var box = { hidden: true, innerHTML: '' };\n"
            "var document = { getElementById: function(id){ return id === 'vault-find-results' ? box : null; } };\n"
            "var magicFinds = {\n"
            "  'Shimmering Grand Charm of Vita': { q: 'magic' },\n"
            "  'Harlequin Crest (Shako)': { q: 'magic' },\n"
            "  'Tal Rasha\\'s (set)': { q: 'set' },\n"
            "  'Ist': { q: 'rune' }\n"
            "};\n"
            "window._vaultInMagicRare = function(n){ return n === 'Shimmering Grand Charm of Vita'; };\n"
            "window._vaultLastSeenOnMain = function(){ return null; };\n"
            "window.vaultPropose = function(nm){\n"
            "  if (nm === 'Hellfire Torch') return { ok: true, moved: false, kind: 'keep', id: '__keep', why: 'keep in your inventory — only works on the character you are actively playing' };\n"
            "  if (nm === 'Enigma') return { ok: true, kind: 'mule', id: 'shared', home: 'SHARED STASH', why: 'war gear' };\n"
            "  return { ok: false };\n"
            "};\n"
            + matcher + "\n" + where + "\n" + find + "\n"
            "window.vaultFind('charm'); var charm = box.innerHTML;\n"
            "window.vaultFind('shako'); var shako = box.innerHTML;\n"
            "window.vaultFind('tal'); var tal = box.innerHTML;\n"
            "window.vaultFind('ist'); var ist = box.innerHTML;\n"
            "process.stdout.write(JSON.stringify({\n"
            "  charm: charm, shako: shako, tal: tal, ist: ist,\n"
            "  torch: _vaultWhereIs('Hellfire Torch'),\n"
            "  enigma: _vaultWhereIs('Enigma'),\n"
            "  dock: _vaultWhereIs('Amulet')\n"
            "}));\n"
        )
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-1500:])
        o = json.loads(p.stdout)
        self.assertIn("Shimmering Grand Charm of Vita", o["charm"])
        self.assertIn("1 match", o["charm"])
        self.assertIn("1 match", o["shako"])
        self.assertNotIn("Tal Rasha", o["tal"])
        self.assertIn("no vaulted item matches", o["ist"])
        self.assertEqual(o["torch"]["kind"], "main")
        self.assertIsNone(o["torch"]["mule"])
        self.assertIn("keep in your inventory", o["torch"]["why"])
        self.assertEqual(o["enigma"]["kind"], "would")
        self.assertEqual(o["enigma"]["mule"], "shared")
        self.assertEqual(o["dock"]["kind"], "dock")


class APlannerPickNeverOverwritesWhatHeHas(unittest.TestCase):
    """REG-2185 - a planner pick over a name he already holds must not write over that record.

    The cross-family review of v3683/v3685 reproduced both in node at HEAD: a magic pick on a name already in Magic & Rare
    replaced the record with { q, base, mods } (its reel receipt, checker verdict and his mods gone), and a second Grief on
    a Berserker Axe wrote over the first Grief's Phase Blade / IAS / sockets in d2r_plannerMade. The older planner case
    above picks the same item twice with the SAME token - a re-roll of its own fresh pick - so it never reached a record
    that existed before the pick, and stayed green over both. These two do: the record is there FIRST, the pick comes with
    a NEW token."""

    def _run(self, scenario):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        s = _src()
        block = _cut(s, "  /* ⟦VAULT PLANNER FILE BEGIN⟧ */\n", "  /* ⟦VAULT PLANNER FILE END⟧ */\n")
        prog = r"""
var window = globalThis, CALLS = [], SAID = [], magicFinds = {}, assign = {}, owned = new Set(), copies = {};
function copyCount(n){ var c = copies && copies[n]; return (c && c > 0) ? c : (owned.has(n) ? 1 : 0); }
function status(m){ SAID.push(String(m)); }
function renderVault(){} function refreshOpenCard(){} function persistOwned(){} function saveA(){}
function muleById(id){ var n = { 'uni-armor': 'UNI-ARMOR', 'magic-rare': 'MAGIC & RARE', 'shared': 'SHARED STASH' }; return n[id] ? { id: id, name: n[id] } : null; }
function isSharedStash(nm){ return false; }
function _vaultKeeps(nm){ return false; }
var ROUTES = {};
function suggestMule(nm){ return Object.prototype.hasOwnProperty.call(ROUTES, nm) ? ROUTES[nm] : { id: null, unsorted: true, why: 'stub' }; }
var MADESTORE = {};
var LS = { getItem: function(k){ return Object.prototype.hasOwnProperty.call(MADESTORE, k) ? MADESTORE[k] : null; },
           setItem: function(k, v){ MADESTORE[k] = String(v); } };
window._ownedAdd = function(nm){ if (!owned.has(nm)) owned.add(nm); return { added: true, prov: { ok: true } }; };
window.vaultHandAdd = function(nm){ if (!owned.has(nm)) owned.add(nm); return { ok: true, mode: 'added', name: nm }; };
window.vaultFile = function(nm, wit, opts){ assign[nm] = opts.mule; if (!owned.has(nm)) owned.add(nm); return { ok: true, mode: 'filed', mule: opts.mule }; };
window.vaultUnassign = function(nm){ delete assign[nm]; return { ok: true }; };
window.kaiChronicleRecord = function(row){ return row; };
window._cbItem = function(id){ return { id: id }; };
window._cbShown = function(e){ return { name: e._name, q: e._q, base: e._base || '' }; };
window._cbDb = function(){ return { b: { cm: ['Small Charm'], '7cr': ['Phase Blade'], '7wa': ['Berserker Axe'] } }; };
window._cbAf = function(id){ return id === 'vita' ? { _text: '+17 to Life' } : null; };
window._cbAfText = function(a){ return a._text || ''; };
""" + block + "\n" + scenario
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise AssertionError("the cut planner did not run in node: %s" % r.stderr[-700:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_a_magic_pick_keeps_the_record_he_already_has(self):
        out = self._run(r"""
ROUTES['Small Charm of Vita'] = { id: 'magic-rare', why: 'registered in Magic and Rare' };
magicFinds['Small Charm of Vita'] = { q: 'magic', base: 'Small Charm', mods: ['+17 to Life'], frameId: 'f123',
  sessionId: 's9', shotFile: 'shot_0042.png', checked: true, verdict: 'keep', score: 7 };
owned.add('Small Charm of Vita');
window.vaultPlannerFile({ id: 'charm', base: 'cm', _name: 'Small Charm of Vita', _q: 'm', affixes: [{ id: 'vita' }] }, 't-new');
console.log(JSON.stringify(magicFinds['Small Charm of Vita']));
""")
        self.assertEqual(out.get("frameId"), "f123", "the pick wiped the reel receipt (frameId)")
        self.assertEqual(out.get("shotFile"), "shot_0042.png", "the pick wiped the screenshot the record was read from")
        self.assertEqual(out.get("verdict"), "keep", "the pick wiped the checker verdict")
        self.assertEqual(out.get("score"), 7, "the pick wiped the checker score")

    def test_a_second_runeword_keeps_the_first_ones_build(self):
        out = self._run(r"""
MADESTORE['d2r_plannerMade'] = JSON.stringify({ Grief: { id: 'grief', base: '7cr', baseName: 'Phase Blade', q: 'r',
  affixes: [{ id: 'ias40' }], eth: false, sockets: 5, rolls: null } });
assign['Grief'] = 'shared'; owned.add('Grief');
window.vaultPlannerFile({ id: 'grief', base: '7wa', _name: 'Grief', _q: 'r', affixes: [] }, 't-g2');
console.log(MADESTORE['d2r_plannerMade']);
""")
        g = out.get("Grief") or {}
        self.assertEqual(g.get("baseName"), "Phase Blade", "the second Grief wrote over the first one's base")
        self.assertEqual(g.get("sockets"), 5, "the second Grief wrote over the first one's sockets")
        self.assertEqual(g.get("affixes"), [{"id": "ias40"}], "the second Grief wrote over the first one's affixes")

RED_PROOF = [
    {
        "why": "REG-1866 - a filing that carries his hand as ownedBy is landed on every pass; without it the next load counts it left",
        "file": "bible.html",
        "find": "    if (cur && (cur.source === 'hand' || (cur.ownedBy && cur.ownedBy.source === 'hand'))) return { ok: true, mode: 'already', name: pre.name };\n",
        "replace": "    if (cur && cur.source === 'hand') return { ok: true, mode: 'already', name: pre.name };\n",
        "matches": 1,
    },
    {
        "why": "REG-1866 - a row that landed leaves the key; without the rewrite it stays there for ever beside the row left",
        "file": "bible.html",
        "find": "    else if (n) window.LSR.setItem(VAULT_HAND_LEGACY, JSON.stringify(kept.map(function(k){ return k.row; })));\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1848 - an owned name is not landed by being owned; counting it landed deletes the hand row he typed",
        "file": "bible.html",
        "find": "    if (!owned.has(pre.name)){\n      var res = _vhCommit(pre, VH_MIGRATE);\n",
        "replace": "    if (owned.has(pre.name)) return { ok: true, mode: 'already', name: pre.name };\n    if (!owned.has(pre.name)){\n      var res = _vhCommit(pre, VH_MIGRATE);\n",
        "matches": 1,
    },
    {
        "why": "REG-1849 - the latch set before the read stops every later paint from trying again",
        "file": "bible.html",
        "find": "    if (_vhMigrated) return null;\n    var raw = null, rows = null;\n",
        "replace": "    if (_vhMigrated) return null;\n    _vhMigrated = true;\n    var raw = null, rows = null;\n",
        "matches": 1,
    },
    {
        "why": "REG-1847 - a receipt the door could not write must be said, not folded into a plain 'added'",
        "file": "bible.html",
        "find": "    var prov = (add && add.prov) || null, receipt = !!(prov && prov.ok === true);\n",
        "replace": "    var prov = (add && add.prov) || null, receipt = true;\n",
        "matches": 1,
    },
    {
        "why": "REG-1847 - an ambiguity check that raised is UNKNOWN; reading it as 'not ambiguous' adds the raw name",
        "file": "bible.html",
        "find": "    catch (e) { return { ok: false, refused: 'unknown', why: 'whether \"' + raw + '\" names one item could not be asked — nothing was added' }; }\n",
        "replace": "    catch (e) { amb = null; }\n",
        "matches": 1,
    },
    {
        "why": "REG-1850 - an unsettled name counted as 'the vault does not draw it' is a wrong reason",
        "file": "bible.html",
        "find": "      if (!c.name){ unsettled++; return; }\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1848 - a row left behind must be said on the Vault; without the paint it is invisible",
        "file": "bible.html",
        "find": "    try { if (typeof window._vaultHandLeftPaint === 'function') window._vaultHandLeftPaint(); } catch (eL) {}\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "only a name the vault draws is added; dropping the keep check files a crafted recipe that renders nowhere",
        "file": "bible.html",
        "find": "    if (!_vaultKeeps(r.name) && !_vaultHandBase(r.name)) /* L1 a catalogue base passes the hand door */\n      return { ok: false, refused: 'not-drawn', name: r.name,\n",
        "replace": "    if (false) /* L1 a catalogue base passes the hand door */\n      return { ok: false, refused: 'not-drawn', name: r.name,\n",
        "matches": 1,
    },
    {
        "why": "the add must reach d2r_owned; without the persist it lives until the next reload",
        "file": "bible.html",
        "find": "    persistOwned();\n    try { if (opts !== VH_MIGRATE && typeof _vaultMoveNoteAdded === 'function')",
        "replace": "    try { if (opts !== VH_MIGRATE && typeof _vaultMoveNoteAdded === 'function')",
        "matches": 1,
    },
    {
        "why": "the pick is filed under the register's name; skipping the resolution makes a second tile for one item",
        "file": "bible.html",
        "find": "nm = String(window._vaultResolveName(nm) || nm); }\n",
        "replace": "nm = nm; }\n",
        "matches": 1,
    },
    {
        "why": "the second key is removed only when every row landed; removing it always loses what he typed",
        "file": "bible.html",
        "find": "    if (!kept.length) window.LSR.removeItem(VAULT_HAND_LEGACY);\n",
        "replace": "    window.LSR.removeItem(VAULT_HAND_LEGACY);\n",
        "matches": 1,
    },
    {
        "why": "renderVault must bring the second key home; without the call its rows never reach owned",
        "file": "bible.html",
        "find": "    try { if (typeof window._vaultHandMigrate === 'function') window._vaultHandMigrate(); } catch (eH) {}\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "a planner pick must be filed by the reel door; skipping that call leaves the catalogue pick unfiled",
        "file": "bible.html",
        "find": "    var filed = window.vaultFile(nm, { by: 'hand', at: at, where: VP_WHERE }, { mule: id });\n",
        "replace": "    var filed = { ok: true, mode: 'skipped' };\n",
        "matches": 1,
    },
    {
        "why": "the first add of a name already filed must count another copy; without the check a new open leaves the second Grief at one",
        "file": "bible.html",
        "find": "      if (routed.mode === 'already' && assign[nm] != null && _vpCopySeen[nm] !== token){\n",
        "replace": "      if (false && routed.mode === 'already' && assign[nm] != null && _vpCopySeen[nm] !== token){\n",
        "matches": 1,
    },
    {
        "why": "a vault item click must keep the floating card; dropping the keep returns the page route",
        "file": "bible.html",
        "find": "        if (chip && !chip.classList.contains('vd-db') && !t.closest('button, a, input, textarea, select')) return;\n",
        "replace": "        if (false) return;\n",
        "matches": 1,
    },
    {
        "why": "the shared stash locker must refuse a delete; without the guard its items return to the dock",
        "file": "bible.html",
        "find": "    if (id === 'shared') return;\n",
        "replace": "    if (false) return;\n",
        "matches": 1,
    },
    {
        "why": "the locker card must draw one rectangle per copy; without the list a second Grief stays one picture",
        "file": "bible.html",
        "find": "      var drawn = _shelfDrawNames(items, m.id);\n",
        "replace": "      var drawn = items.slice();\n",
        "matches": 1,
    },
    {"why": "REG-2185: a magic planner pick writes over the record he already has and wipes its receipt and verdict",
     "file": "bible.html",
     "find": "      var _mfHad = (beforeMagic && !keepFresh && magicFinds[nm] && typeof magicFinds[nm] === 'object') ? magicFinds[nm] : null;\n      if (_mfHad){\n        if (!_mfHad.q) _mfHad.q = magicQ;\n        if (!_mfHad.base && baseName) _mfHad.base = baseName;\n        if ((!_mfHad.mods || !_mfHad.mods.length) && mods && mods.length && !_mfAnother) _mfHad.mods = mods;\n      } else {\n        magicFinds[nm] = { q: magicQ, base: baseName, mods: mods };\n      }\n",
     "replace": "      magicFinds[nm] = { q: magicQ, base: baseName, mods: mods };\n",
     "matches": 1},
    {"why": "REG-2185: a second runeword of the same name writes over the first one's base, sockets and affixes",
     "file": "bible.html",
     "find": '    if (Object.prototype.hasOwnProperty.call(map, nm) && !mayReplace) return;\n',
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
