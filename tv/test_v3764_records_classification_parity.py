# -*- coding: utf-8 -*-
"""#76 REG-2272 item 6 — the records model classifies the shared LOCKER the way production does.

_sharedNames() is assign === 'shared': the shared locker, including war gear the never-muled regex
does not match. isSharedStash() is that regex (runes, shards, sunders). The INC-2/INC-3b fixtures
stubbed isSharedStash to mean assign === 'shared' and made muleById('shared') return null, so the
two never met. In production muleById('shared') is a real roster locker, and the filed branch then
called war gear a mule home: kind filed, mule 'shared', every copy loc the mule id, rule E skipped.
FIND was given a mule. An unassigned regex material is sharedStash by the header and is NOT in the
locker, but the persist overflow view walked kind, so a 4-copy shard read as trade-stock.

This law extracts the SHIPPED functions, including the real isSharedStash and SHARED_STASH_RE, and
gives muleById the shared locker. It does not stub the two shared notions into one.

  · a locker name the regex misses (Enigma, 4 copies) is sharedStash, mule null, copyIx 0..3,
    and every persisted loc is shared (Elad 2026-10-18 13:18 IDT, same mule);
  · FIND does not give that name a mule home;
  · overflow membership is _sharedNames on the live view, the records view, and the loaded store.
    An unassigned Worldstone Shard with 4 copies is sharedStash and is NOT overflow;
  · a real mule filing stays filed;
  · carried still wins over the locker, in the header's order.

Copy-loss ids (REG-2272 item 4) are NOT this law. copies[name] is a count. Which physical copy
left is not in the source stores, and no note names the anchor. That stays open.

NOT wired: the migration stays dormant. A missing node raises. RED_PROOF below.
[[the-unjoined-end]] [[unknown-stays-unknown]] [[heart-first]] [[regression-guard]]
"""
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

BIBLE = os.path.join(HERE, "..", "bible.html")
NODE = os.environ.get("NODE") or shutil.which("node")

EXTRACT = [
    "_sharedNames", "_sharedCopyCount", "_sharedCappedCopies", "_vaultSharedOverflowCells",
    "_vaultSharedOverflowNames", "isSharedStash",
    "_vaultRecords", "_vaultRecordsSource", "_vrSourceChoice", "_vaultRecordsFind", "_vaultSameMuleCopies", "_vaultRecordsOverflow",
    "_vaultRecordsHeader",
    "_vrRecWitness", "_vrRecRow", "_vrRecRowsFrom",
    "_vrRecLoadRaw", "_vrRecGuardedSet", "_vrLocForCopy", "_vaultRecordsLoad", "_vaultRecordsPersist",
    "_vrRecHome", "_vaultRecordsViewFind", "_vaultRecordsViewOverflow", "_vaultRecordsViewHeader",
]

PREAMBLE = r"""
var window = globalThis;
window.D2R_PROFILE = 'main';
console.info = function(){ try { process.stderr.write('[info] ' + Array.prototype.join.call(arguments, ' ') + '\n'); } catch(e){} };
console.log = console.info;
console.warn = function(){ try { process.stderr.write('[warn] ' + Array.prototype.join.call(arguments, ' ') + '\n'); } catch(e){} };
var _LSRDATA = {};
window.LSR = {
  getItem: function(k){ return Object.prototype.hasOwnProperty.call(_LSRDATA, k) ? _LSRDATA[k] : null; },
  setItem: function(k, v){ _LSRDATA[k] = String(v); },
  removeItem: function(k){ delete _LSRDATA[k]; }
};
var _VR_STORE_KEY = 'd2r_vaultRecords';
var _VRM_KEY = 'd2r_vaultRecordsMigrate';
var _VRM_VER = 1;
var _vrRecUnread = {};
// Enigma is war gear filed to the shared locker and is NOT a never-muled regex name.
// Ist rune is in the locker AND matches the regex. Worldstone Shard matches the regex and is NOT filed.
// Shako is a real mule. Nagelring is loose. Grief is carried AND in the locker — carried wins.
var assign = { Enigma:'shared', 'Ist rune':'shared', Shako:'mule1', Grief:'shared', Spirit:'__keep', 'Throw Me':'__throwout' };
var copies = { Enigma:4, 'Worldstone Shard':4 };
var OWNED = ['Enigma', 'Ist rune', 'Worldstone Shard', 'Shako', 'Nagelring', 'Grief', 'Spirit', 'Throw Me', 'Annihilus', 'Plain Boots'];
var _SHARED_COPY_CAP = 2, _MULE_COPY_CAP = 3;
function ownedPool(){ return OWNED.slice(); }
function copyCount(n){ var c = copies[n]; return (c && c > 0) ? c : (OWNED.indexOf(n) >= 0 ? 1 : 0); }
function muleById(id){
  if (id === 'mule1') return { id:'mule1', name:'Mule One' };
  if (id === 'shared') return { id:'shared', name:'SHARED STASH' };
  return null;
}
function _dockNames(){ return ['Nagelring']; }
window._carriedNames = function(){ return [{ name:'Grief' }]; };
var KEEP_IN_INVENTORY = /Annihilus|Hellfire Torch|Gheed/;
function _keepName(n){ return n; }
"""


def _fn(src, name):
    m = re.search(r"\bfunction %s\s*\(" % re.escape(name), src)
    if not m:
        raise AssertionError("could not find function %s in bible.html" % name)
    i = src.index("{", m.start())
    depth, j = 0, i
    while j < len(src):
        c = src[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
        j += 1
    raise AssertionError("unbalanced braces extracting %s" % name)


def _var(src, name):
    m = re.search(r"^  var %s = .*;$" % re.escape(name), src, re.M)
    if not m:
        raise AssertionError("could not find var %s in bible.html" % name)
    return m.group(0)


class TestV3764RecordsClassificationParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        with open(BIBLE, encoding="utf-8") as f:
            cls.src = f.read()
        cls.fns = _var(cls.src, "SHARED_STASH_RE") + "\n" + "\n".join(_fn(cls.src, n) for n in EXTRACT)

    def _run(self, scenario):
        prog = PREAMBLE + self.fns + "\nvar out = {};\n" + scenario + "\nprocess.stdout.write(JSON.stringify(out));\n"
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-2000:])
        return json.loads(p.stdout)

    def test_the_shared_locker_matches_production_names_and_copy_locations(self):
        o = self._run(r"""
var mem = _vaultRecords();
function pack(name){
  return mem.records.filter(function(r){ return r.name === name; }).map(function(r){
    return { copyIx: r.copyIx, kind: r.kind, mule: r.mule };
  });
}
out.war = pack('Enigma');
out.rune = pack('Ist rune');
out.shard = pack('Worldstone Shard');
out.filed = pack('Shako');
out.carried = pack('Grief');
out.loose = pack('Nagelring');
out.keep = pack('Spirit');
out.throwout = pack('Throw Me');
out.charm = pack('Annihilus');
out.orphan = pack('Plain Boots');
out.findWar = _vaultRecordsFind('Enigma');
out.findFiled = _vaultRecordsFind('Shako');
out.findShard = _vaultRecordsFind('Worldstone Shard');
out.findLoose = _vaultRecordsFind('Nagelring');
out.findOrphan = _vaultRecordsFind('Plain Boots');
out.sharedNames = _sharedNames();
out.liveOverflow = _vaultSharedOverflowNames();
out.recOverflow = _vaultRecordsOverflow();
out.memOverflow = _vaultRecordsViewOverflow(mem);
var pr = _vaultRecordsPersist();
var loaded = _vaultRecordsLoad();
out.persistOk = !!pr.ok;
out.locWar = loaded.records.filter(function(r){ return r.name === 'Enigma'; }).map(function(r){ return r.loc; });
out.locKeep = loaded.records.filter(function(r){ return r.name === 'Spirit'; }).map(function(r){ return r.loc; });
out.locLoose = loaded.records.filter(function(r){ return r.name === 'Nagelring'; }).map(function(r){ return r.loc; });
out.loadedOverflow = _vaultRecordsViewOverflow(loaded);
out.regexMissesWar = !isSharedStash('Enigma');
out.regexHitsShard = !!isSharedStash('Worldstone Shard');
""")
        self.assertTrue(o["regexMissesWar"], "Enigma must stay outside the never-muled regex or this law is vacuous")
        self.assertTrue(o["regexHitsShard"], "Worldstone Shard must match the never-muled regex")
        self.assertEqual(o["sharedNames"], ["Enigma", "Grief", "Ist rune"],
                         "production _sharedNames drifted: %r" % o["sharedNames"])
        self.assertEqual(o["war"], [
            {"copyIx": 0, "kind": "sharedStash", "mule": None},
            {"copyIx": 1, "kind": "sharedStash", "mule": None},
            {"copyIx": 2, "kind": "sharedStash", "mule": None},
            {"copyIx": 3, "kind": "sharedStash", "mule": None},
        ], "a shared-locker name the regex misses was not classified as the locker: %r" % o["war"])
        self.assertEqual(o["findWar"], "shared", "FIND did not home the shared locker on itself: %r" % o["findWar"])
        self.assertTrue(o["persistOk"], "persist refused a readable store: %r" % o)
        self.assertEqual(o["locWar"], ["shared", "shared", "shared", "shared"],
                         "a shared copy left the mule: %r" % o["locWar"])
        self.assertEqual(o["rune"], [{"copyIx": 0, "kind": "sharedStash", "mule": None}], o["rune"])
        self.assertEqual(o["shard"], [
            {"copyIx": i, "kind": "sharedStash", "mule": None} for i in range(4)
        ], "an unassigned regex material left sharedStash: %r" % o["shard"])
        self.assertIsNone(o["findShard"], o["findShard"])
        self.assertEqual(o["filed"], [{"copyIx": 0, "kind": "filed", "mule": "mule1"}],
                         "a real mule filing was reclassified: %r" % o["filed"])
        self.assertEqual(o["findFiled"], "mule1", o["findFiled"])
        self.assertEqual(o["carried"], [{"copyIx": 0, "kind": "carried", "mule": None}],
                         "carried must still win over the locker: %r" % o["carried"])
        self.assertEqual(o["liveOverflow"], [], o["liveOverflow"])
        self.assertEqual(o["recOverflow"], [], o["recOverflow"])
        self.assertEqual(o["memOverflow"], [],
                         "the in-memory overflow view listed trade stock: %r" % o["memOverflow"])
        self.assertEqual(o["loadedOverflow"], [],
                         "the loaded store's overflow view listed trade stock: %r" % o["loadedOverflow"])
        self.assertEqual(o["loose"], [{"copyIx": 0, "kind": "loose", "mule": None}], o["loose"])
        self.assertIsNone(o["findLoose"], o["findLoose"])
        self.assertEqual(o["keep"], [{"copyIx": 0, "kind": "keep", "mule": None}], o["keep"])
        self.assertEqual(o["locKeep"], ["__keep"], o["locKeep"])
        # #154.20 - a THROW OUT pick is loose (off the dock, the seam's discard rule), never an orphan "filed to a mule the
        # board can't find"; and never filed
        self.assertEqual(o["throwout"], [{"copyIx": 0, "kind": "loose", "mule": None}],
                         "a throw-out was filed, or read as a lost mule: %r" % o["throwout"])
        self.assertEqual(o["charm"], [{"copyIx": 0, "kind": "keepInv", "mule": None}], o["charm"])
        self.assertEqual(o["orphan"], [{"copyIx": 0, "kind": "orphan", "mule": None}], o["orphan"])
        self.assertIsNone(o["findOrphan"], o["findOrphan"])
        self.assertEqual(o["locLoose"], ["loose"], o["locLoose"])

    def test_distinct_attacks_clear_the_write_door_wilson_bar(self):
        """Same write-door bar as the persist law. One RED_PROOF is one distinct attack.

        A wrong kind is what the migration would persist, so the bar is vault.apply, not a route.
        Sabotage alone does not clear the kinds bar, and this stamp does not open the door."""
        from confidence import confluence, wilson_lower
        import self_arming as SA
        bar = SA.LOCKS["vault.apply"]["bar"]
        kinds_bar = SA.LOCKS["vault.apply"]["kinds_bar"]
        n = len(RED_PROOF)
        w = wilson_lower(n, n)
        conf = confluence(["sabotage"], SA.KINDS)
        msg = ("vault-records classification: %d distinct attacks, wilson %.4f vs write-door bar %.3f; "
               "kinds sabotage %.2f vs %.2f" % (n, w, bar, conf, kinds_bar))
        print(msg)
        self.assertGreaterEqual(n, 10, msg)
        self.assertGreaterEqual(w, bar, msg)
        self.assertLess(conf, kinds_bar, "one sabotage family must not read as enough to open the write door")


RED_PROOF = [
    {
        "why": "REG-2272 item 6 — a name in the shared locker (assign === shared) that the never-muled "
               "regex misses must be sharedStash. Dropping that branch lets muleById('shared') file Enigma "
               "as a mule, FIND returns shared, and the 3rd copy never becomes dupes.",
        "file": "bible.html",
        "find": "        else if (sharedSet[name]) kind = 'sharedStash';\n",
        "replace": "        else if (false && sharedSet[name]) kind = 'sharedStash';\n",
        "matches": 1,
    },
    {
        "why": "Nothing is GRAIL-DUPES trade stock. Returning a name puts an unassigned shard back on that list.",
        "file": "bible.html",
        "find": "return []; /* v3767 no dupes list */",
        "replace": "return ['Worldstone Shard']; /* v3767 no dupes list */",
        "matches": 1,
    },
    {
        "why": "Carried wins over the locker. Grief is assign shared and carried; dropping the carried branch files it as sharedStash.",
        "file": "bible.html",
        "find": "        else if (carriedSet[name]) kind = 'carried';\n",
        "replace": "        else if (false && carriedSet[name]) kind = 'carried';\n",
        "matches": 1,
    },
    {
        "why": "A docked name is loose. Dropping that branch makes Nagelring an orphan.",
        "file": "bible.html",
        "find": "        else if (looseSet[name]) kind = 'loose';\n",
        "replace": "        else if (false && looseSet[name]) kind = 'loose';\n",
        "matches": 1,
    },
    {
        "why": "Standing kit kept with MAIN is keep, not a mule and not an orphan.",
        "file": "bible.html",
        "find": "else if (mid === '__keep') kind = 'keep';",
        "replace": "else if (false && mid === '__keep') kind = 'keep';",
        "matches": 1,
    },
    {
        "why": "A real mule id stays filed. Disabling that branch makes Shako an orphan and FIND loses the mule.",
        "file": "bible.html",
        "find": "        else if (mid != null && mid !== '__throwout' && typeof muleById === 'function' && muleById(mid)) kind = 'filed';\n",
        "replace": "        else if (false && mid != null && mid !== '__throwout' && typeof muleById === 'function' && muleById(mid)) kind = 'filed';\n",
        "matches": 1,
    },
    {
        "why": "Annihilus, Torch and Gheed with no mule are keepInv, not orphans.",
        "file": "bible.html",
        "find": "        else if (typeof KEEP_IN_INVENTORY !== 'undefined' && typeof _keepName === 'function' && KEEP_IN_INVENTORY.test(_keepName(name)))\n",
        "replace": "        else if (false && typeof KEEP_IN_INVENTORY !== 'undefined' && typeof _keepName === 'function' && KEEP_IN_INVENTORY.test(_keepName(name)))\n",
        "matches": 1,
    },
    {
        "why": "The never-muled regex is the first shared branch. An unassigned Worldstone Shard is sharedStash only because of it.",
        "file": "bible.html",
        "find": "      if (typeof isSharedStash === 'function' && isSharedStash(name)) kind = 'sharedStash';\n",
        "replace": "      if (false && typeof isSharedStash === 'function' && isSharedStash(name)) kind = 'sharedStash';\n",
        "matches": 1,
    },
    {
        "why": "Every shared copy sits on the same mule. Sending copy 3 to dupes puts a 4-copy Enigma in GRAIL-DUPES.",
        "file": "bible.html",
        "find": "return 'shared'; /* v3767 same mule */",
        "replace": "return (copyIx < 2) ? 'shared' : 'dupes';",
        "matches": 1,
    },
    {
        "why": "FIND gives a mule only for kind filed, and the shared locker only to a name in it. "
               "Returning shared for every other kind hands a loose name that locker.",
        "file": "bible.html",
        "find": "      if (inLocker) return 'shared';\n    }\n    return null;\n",
        "replace": "      if (inLocker) return 'shared';\n    }\n    return 'shared';\n",
        "matches": 1,
    },
    {
        "why": "A name with no home is an orphan. Calling that branch filed invents a mule home for Plain Boots.",
        "file": "bible.html",
        "find": "        else { kind = 'orphan'; out.orphans.push({ name: name, assign: (mid == null ? null : String(mid)) }); }\n",
        "replace": "        else { kind = 'filed'; out.orphans.push({ name: name, assign: (mid == null ? null : String(mid)) }); }\n",
        "matches": 1,
    },
    {
        "why": "#154.20 - a THROW OUT pick falls to orphan again, 'filed to a mule the board can't find'",
        "file": "bible.html",
        "find": "        else if (mid === '__throwout') kind = 'loose';\n",
        "replace": "",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
