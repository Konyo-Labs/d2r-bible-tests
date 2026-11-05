# -*- coding: utf-8 -*-
"""v3855 C1 (Elad 2026-11-02) - EVERY ITEM FILED IN A MULE OR THE SHARED STASH IS DRAWN ON SOME PAGE.

Measured: the seam (_vaultSeamHome) homed Harlequin Crest (owned under its bare spelling) and Ber Rune on the shared stash,
and the charm rule (_mfKeeperHome) homed Small Charm of Balance there, but the window packed only assign + records, and the
records come from ownedPool, which drops a bare legacy spelling, the shared commodities and every register keeper. So the
header said "shared stash" and the window drew nothing. Now _sharedDrawNames adds every name either rule homes on shared
(_sharedSeamExtras), and a keeper the charm rule sends to the CHARMS mule is drawn in that mule's window.
Whole page in node: renderVault, each name's home, that window's HTML.
"""
import json, os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import vault_page_node as VPN  # noqa: E402

OWNED = ["Harlequin Crest", "Arachnid Mesh", "Grief", "Ber Rune", "Annihilus"]
KEEP = {"Small Charm of Balance": {"q": "magic", "base": "Small Charm"},
        "Grand Charm of Vita": {"q": "magic", "base": "Grand Charm"}}
PRELUDE = ("localStorage.setItem('d2r_ownerClaim','*');localStorage.setItem('d2r_owned', %s);"
           "localStorage.setItem('d2r_magicFinds', %s);") % (json.dumps(json.dumps(OWNED)), json.dumps(json.dumps(KEEP)))

BODY = r"""
var W = window;
W.renderVault(); H.flush(60, 3);
function win(id){ W.openMuleCard(id); H.flush(60, 3); return String((document.getElementById('vault-detail')||{}).innerHTML||''); }
function home(n){
  var k = W._mfKeeperHome(n); if (k !== undefined) return k;
  var h = W._vaultSeamHome(n); if (!h) return null;
  if (h.loc === 'shared') return 'shared';
  if (h.loc === 'filed') return h.mule;
  return null;
}
var names = %NAMES%;
OUT.rows = {};
var cache = {};
names.forEach(function(n){
  var id = home(n);
  var html = id ? (cache[id] = cache[id] || win(id)) : '';
  var drawnIn = id === 'shared' ? W._sharedDrawNames() : (id ? W._muleNamesFor(id) : []);
  OUT.rows[n] = { home: id, listed: drawnIn.indexOf(n) >= 0, drawn: !!id && html.indexOf(n) >= 0 };
});
/* a charm the rule sends to the CHARMS mule */
W._charmHome = function(){ return { id: 'charms', why: 'test' }; };
try { _charmHome = W._charmHome; } catch (e) {}
var hc = win('charms');
OUT.charms = { home: W._mfKeeperHome('Small Charm of Balance'), listed: W._muleNamesFor('charms').indexOf('Small Charm of Balance') >= 0,
               drawn: hc.indexOf('Small Charm of Balance') >= 0 };
"""
NAMES = ["Harlequin Crest", "Arachnid Mesh", "Grief", "Ber Rune", "Annihilus", "Small Charm of Balance", "Grand Charm of Vita"]
_OUT = None


def out():
    global _OUT
    if _OUT is None:
        _OUT = VPN.run(BODY.replace('%NAMES%', json.dumps(NAMES)), prelude=PRELUDE, timeout=300)
    return _OUT


#: v3864 (prover BLIND on [1] and [2], GitHub v3864): REG-2971 made every keeper a record, so on the live model a keeper's record
#: already sits on its mule and the keeper-span lines never decide. They still do on a board whose SAVED records were written
#: before REG-2971 - a v3863 board's store holds no keeper record - until a write refreshes them. That board here: the page's
#: own store with its keeper rows taken out, read back after the whole body (the pencil law's twin case).
SAVED_BEFORE_KEEPER_RECORDS = r"""
window._vaultRecordsMigrate({ force: true });
(function(){ var st = JSON.parse(window.LSR.getItem('d2r_vaultRecords')), K = %s;
  st.records = st.records.filter(function(r){ return !Object.prototype.hasOwnProperty.call(K, r.name); });
  window.LSR.setItem('d2r_vaultRecords', JSON.stringify(st)); })();
""" % json.dumps(KEEP)
SAVED_READ = r"""
OUT.savedSource = !!window._vrSourceChoice().store;
OUT.keeperRecords = window._vaultRecordsSource().records.filter(function(r){ return r && Object.prototype.hasOwnProperty.call(%s, r.name); }).length;
""" % json.dumps(KEEP)
_SAVED = None


def out_saved():
    global _SAVED
    if _SAVED is None:
        _SAVED = VPN.run(SAVED_BEFORE_KEEPER_RECORDS + BODY.replace('%NAMES%', json.dumps(NAMES)) + SAVED_READ, prelude=PRELUDE, timeout=300)
    return _SAVED


class KeepersDrawFromRecordsSavedBeforeKeepersWere(unittest.TestCase):
    def test_a_keeper_is_drawn_where_it_is_homed_on_a_v3863_store(self):
        o = out_saved()
        self.assertTrue(o["savedSource"] and o["keeperRecords"] == 0,
                        "PREMISE: the saved records are not the source, or still hold keeper rows (%r, %r)" % (o["savedSource"], o["keeperRecords"]))
        r = o["rows"]["Small Charm of Balance"]
        self.assertEqual(r["home"], "shared", r)
        self.assertTrue(r["listed"] and r["drawn"], "a charm keeper homed on shared is not drawn from records saved before keepers were: %r" % r)
        c = o["charms"]
        self.assertTrue(c["listed"] and c["drawn"], "the CHARMS mule drew no charm keeper from records saved before keepers were: %r" % c)


class EveryFiledItemIsDrawn(unittest.TestCase):
    def test_the_fixture_homes_them_on_shared(self):
        rows = out()["rows"]
        for n in ("Harlequin Crest", "Ber Rune", "Small Charm of Balance"):
            self.assertEqual(rows[n]["home"], "shared", (n, rows[n]))

    def test_every_homed_name_is_listed_and_drawn(self):
        rows = out()["rows"]
        homed = [n for n in NAMES if rows[n]["home"]]
        self.assertGreaterEqual(len(homed), 6, rows)
        for n in homed:
            self.assertTrue(rows[n]["listed"], (n, rows[n]))
            self.assertTrue(rows[n]["drawn"], (n, rows[n]))

    def test_a_charm_on_the_charms_mule_is_drawn_there(self):
        c = out()["charms"]
        self.assertEqual(c["home"], "charms", c)
        self.assertTrue(c["listed"], c)
        self.assertTrue(c["drawn"], c)

    def test_one_name_once(self):
        src = open(os.path.join(HERE, "..", "bible.html"), encoding="utf-8").read()
        self.assertIn("_sharedSeamExtras(names).forEach", src)


RED_PROOF = [
    {"why": "the shared window drops the seam's shared names", "file": "bible.html",
     "find": "    try { _sharedSeamExtras(names).forEach(function(n){ names.push(n); }); } catch (e4) {}\n", "replace": "", "matches": 1},
    {"why": "a charm keeper homed on shared is not drawn there", "file": "bible.html",
     "find": "if (!seen[n] && _mfKeeperHome(n) === 'shared') { seen[n] = 1; out.push(n); }", "replace": "", "matches": 1},
    {"why": "the CHARMS mule packs no keeper span", "file": "bible.html",
     "find": "if (n && _mfKeeperHome(n) === muleId && !Object", "replace": "if (false && n && _mfKeeperHome(n) === muleId && !Object", "matches": 1},
    {"why": "a bare legacy spelling / rune homed shared is not drawn", "file": "bible.html",
     "find": "      if (!h || h.loc !== 'shared') return;\n      seen[n] = 1; seen[rn] = 1; out.push(n);", "replace": "      return;", "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
