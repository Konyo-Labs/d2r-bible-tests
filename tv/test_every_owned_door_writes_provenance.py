# -*- coding: utf-8 -*-
"""EVERY DOOR INTO `owned` SAYS WHO FILED IT — and the live route files what he HOLDS. Driven on the shipped
board code (cut from bible.html by its markers, run in node), never re-typed.

His words, 2026-09-28: "where is the ledger proof of these two items? i cant find it.. how can i see the evidence
and picture pixels from the session it was extracted from", "its correct btw.. just want to see it and see how its
read so we can surgically fix", "make sure the others have the same logic too", "fix the route so they flow
correctly", and his ruling the same day (HANDOFF §28): a CHRONICLE-PAGE read is found-ever, NOT the vault.

MEASURED on a copy of his store (read-only): owned = [Plague, Grief] with NO d2r_vaultProv row for either — the
trail lived only in d2r_chronicleInboxLog (aic-judge, one session, two frames). The door that owned them
(aicJudgeApply's keep tier) wrote no provenance, and neither did its siblings (22 bare `owned.add(` sites). And the
live register wrote String of Ears — read WORN — only to the found list: kaiChroniclePropose returned from its
"already in the Chronicle" branch before the vault was ever asked.

WHAT THIS LAW HOLDS:
  · THE CENSUS — every `owned.add(` in CODE (a JS scanner: comments, strings, templates and regex literals are
    not code) sits inside the ⟦OWNED PROV⟧ door, except the two NAMED vaultFile sites, each with its reason.
  · THE DOOR — window._ownedAdd writes a kind:'owned' RECEIPT (source, when, session, frame, place, scene, look);
    it never clobbers a filing row (the §24 rebuild's tier / successes / trials stay); a standing receipt only
    fills what it lacks and adds a NEW look to its tally; no source → no row (never invented); a store that will
    not parse is never written over.
  · THE ROUTE — worn / stash / cube / mule files into the dock; a Chronicle page never does, even with a place on
    it; the floor never; an UNKNOWN place waits. ⚠ §31.2 (his ruling, 2026-09-28) SUPERSEDES v2346 / REG-426 for
    inventory LOOT: a name the reader placed in his inventory is CARRIED — owned right away, on that character's
    strip, never filed; it LANDS on a stash-tab / mule look and LEAVES only on a floor / vendor / trade look with its
    frame; absence asks "still have it?" after a few sessions and never un-owns. Standing kit stays §29.
  · THE REVIEW OF 77d8d8b5, each reproduced and driven here: H1 (one sighting, one tuple; the held one routes and is
    cited), M3 (the backfill stamp forks per world, a read replays only into its own world, his removals never come
    back), M4 (owned_restore and the un-seed Undo write receipts; every d2r_owned write is censused), L1 (no vault
    claim decided on the bare predicate), L2 (the backfill's side writes are journaled and undone).
  · THE BACKFILL — on a fixture store shaped like his: Grief and Plague gain their receipts from their own
    aic-judge rows; String of Ears (worn) is filed with a receipt; the seven Chronicle-page reads, the floor
    read, the unknown one, a dismissed one and one still waiting for his ruling are NOT; a second run is a
    no-op (idempotent); the undo takes back exactly what it did, through the removal door.
  · A RECEIPT IS NEVER A WITNESS — the sorter files nothing on it and the W6 prune keeps no filing on it.
  · THE EVIDENCE PANEL — who / when / session / frame / tally from the store; an item with no provenance says
    so in words; a picture that loads is shown, one that does not is said in words (the console's reason, or
    UNKNOWN) and never drawn as an <img>.
  · THE JOINS — the settled branch of kaiChroniclePropose asks the route before it returns, and aicJudgeApply's
    runeword keep writes its receipt through the door.
RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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

NODE = shutil.which("node")
BIBLE = os.path.join(ROOT, "bible.html")
BEGIN, END = "⟦OWNED PROV BEGIN⟧", "⟦OWNED PROV END⟧"
EV_BEGIN, EV_END = "⟦VAULT EVIDENCE LINE BEGIN⟧", "⟦VAULT EVIDENCE LINE END⟧"
LANES_HEAD = "  window._VAULT_LANES = ["
MAY_HEAD = "  window._vaultMayClaim = function(loc){\n"
REC_FROM = "      var _w0 = (witness && typeof witness === 'object' && !Array.isArray(witness)) ? witness : {};\n"
REC_TO = "      /* v2018 — REG-349: ASK THE PLANNER ABOUT THE ITEM"
#: round-5 review (HIGH) — the register's REAL ambiguity gate (L-4), cut into the stub as its receipt is: a stub that skipped
#: it let the L-1 law's premise (a bare Worldstone Shard is owned as "(any)") contradict what the real register refused.
#: The slice ends before `name = window._vaultResolveName(name);` — the laws that need the resolver install RESOLVE themselves.
AMB_FROM = "      /* L-4 — a bare name several known items share is refused (or settled by the read's kind), never filed as one of them.\n"
AMB_TO = "      name = window._vaultResolveName(name);\n"


def amb_gate(s=None):
    """The real L-4 gate, cut from the register — every harness stub carries it (the __AMB_GATE__ slot in HARNESS)."""
    return _between(s if s is not None else _src(), AMB_FROM, AMB_TO)


def _origin_line(s=None):
    """#41 rank 18 sibling (REG-1552) — the ONE rule for which console a board asks (_consoleOrigin: the page's own origin
    when a local console served it, null otherwise), cut from bible.html by the reset law's own anchor so this harness
    drives the shipped helper and never a re-typed copy. The evidence panel's picture ask reads it."""
    import test_a_vault_reset_clears_only_the_mules as RESET
    line = [l for l in RESET.LINES if "function _consoleOrigin(" in l][0]
    src = s if s is not None else _src()
    assert src.count(line) == 1, "the _consoleOrigin helper is not where the reset law cuts it (%d matches)" % src.count(line)
    return line + "\n"
SORT_FROM = "    var _pvS = _provAll();\n"
SORT_TO = "    /* the throw-out ADVICE is still computed for the dock"
W6_FROM = "    var _pvLive = _provAll();\n"
W6_TO = "    // v360 — shared-stash items"
WIT_FROM = "  function _provAsWitness(row){\n"
#: 2026-10-08 (REG-2022, his #267 ruling) - the cut runs to the end of the receipt's stash gatherer, which the sorter now asks,
#: and the stash-place constant it reads is cut from the page too (never re-typed here)
WIT_TO = "  window._vaultReceiptStashWitness = _receiptStashWitness;\n"
WIT_STASH_LINE = "  var _WIT_STASH = { stash: 1, mule: 1, locker: 1, tomb: 1, tombs: 1, shared: 1, 'shared stash': 1 };\n"

#: the ONLY bare `owned.add(` allowed outside the door, each with its reason
NAMED = {
    "try { if (!owned.has(nm)){ owned.add(nm); persistOwned(); } } catch (e) {}":
        (2, "window.vaultFile — the rebuild and the filing branch. The FILING ROW written two lines above IS the "
            "provenance (source, at, frame, looks, gate, tier), and it is richer than any receipt; routing this add "
            "through the door would only stamp an ownedBy note that says the same thing again."),
}


def _src():
    with io.open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _marked(s, a, b):
    assert s.count(a) == 1 and s.count(b) == 1, "markers %r / %r are not unique (%d, %d)" % (a, b, s.count(a), s.count(b))
    i = s.rfind("\n", 0, s.index(a)) + 1
    j = s.index("\n", s.index(b)) + 1
    return s[i:j]


def _between(s, a, b, include_b=False):
    assert s.count(a) == 1, "anchor %r matched %d times" % (a[:60], s.count(a))
    i = s.index(a)
    j = s.index(b, i)
    return s[i:j + (len(b) if include_b else 0)]


def owned_prov_region(s=None):
    """The ⟦OWNED PROV⟧ door, cut whole — for every law that drives a door which now calls window._ownedAdd."""
    return _marked(s if s is not None else _src(), BEGIN, END)


def _lanes(s):
    """The ONE vault predicate, cut from the board — the route asks it, so the law must too."""
    head = _between(s, LANES_HEAD, "\n", include_b=True)
    assert s.count(MAY_HEAD) == 1, "the vault predicate is not where this law cuts it"
    i = s.index(MAY_HEAD)
    return head + s[i:s.index("\n  };\n", i) + len("\n  };\n")]


# ── the JS census: which `owned.add(` occurrences are CODE ────────────────────────────────────────────
_REGEX_PREV = set("(,=:[!&|?{};+-*%<>~^")
_REGEX_KW = ("return", "typeof", "case", "in", "of", "delete", "void", "throw", "new", "else", "do")
PAT = re.compile(r"\bowned\s*(?:\.\s*add|\[\s*['\"]add['\"]\s*\])\s*\(")


def code_mask(src, keep_strings=False):
    """For each character: 1 when it is JavaScript CODE inside a <script> block — not a comment, string,
    template text, regex literal or HTML. ⚠ A regex literal with a backtick (/[‘’`]/g — this file has several)
    flipped a naive scanner into template mode for 2,300 lines and hid real sites; the regex and ${ } handling
    below are what make the count honest, and test_the_scanner_sees_every_site_the_old_board_had pins that."""
    mask = bytearray(len(src))
    i, n = 0, len(src)
    in_script, stack, mode, depth, last_sig, last_word = False, [], "code", 0, "", ""
    while i < n:
        if not in_script:
            k = src.find("<script", i)
            if k < 0:
                break
            e = src.find(">", k)
            if e < 0:
                break
            i, in_script = e + 1, True
            mode, stack, depth, last_sig, last_word = "code", [], 0, "", ""
            continue
        if mode == "tmpl":
            c = src[i]
            if c == "\\":
                i += 2
                continue
            if c == "`":
                mode, last_sig = "code", "`"
                i += 1
                continue
            if src.startswith("${", i):
                stack.append(depth)
                depth, mode, last_sig = 0, "code", "{"
                i += 2
                continue
            i += 1
            continue
        if src.startswith("</script", i):
            in_script = False
            i += 1
            continue
        c, two = src[i], src[i:i + 2]
        if two == "/*":
            e = src.find("*/", i + 2)
            i = n if e < 0 else e + 2
            continue
        if two == "//":
            e = src.find("\n", i)
            i = n if e < 0 else e
            continue
        if c in ("'", '"'):
            j = i + 1
            while j < n and src[j] != c and src[j] != "\n":
                j += 2 if src[j] == "\\" else 1
            if keep_strings:
                for q in range(i, min(j + 1, n)):
                    mask[q] = 1
            i, last_sig = j + 1, c
            continue
        if c == "`":
            mode = "tmpl"
            i += 1
            continue
        if c == "/" and (last_sig == "" or last_sig in _REGEX_PREV or last_word in _REGEX_KW):
            j, cls = i + 1, False
            while j < n and src[j] != "\n":
                ch = src[j]
                if ch == "\\":
                    j += 2
                    continue
                if ch == "[":
                    cls = True
                elif ch == "]":
                    cls = False
                elif ch == "/" and not cls:
                    break
                j += 1
            i = j + 1
            while i < n and src[i].isalpha():
                i += 1
            last_sig = "/"
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            if depth == 0 and stack:
                depth, mode = stack.pop(), "tmpl"
                i += 1
                continue
            depth -= 1
        mask[i] = 1
        if not c.isspace():
            if c.isalnum() or c in "_$":
                j = i
                while j < n and (src[j].isalnum() or src[j] in "_$"):
                    mask[j] = 1
                    j += 1
                last_word, last_sig, i = src[i:j], "a", j
                continue
            last_sig, last_word = c, ""
        i += 1
    return mask


def code_sites(src):
    mask = code_mask(src)
    out = []
    for m in PAT.finditer(src):
        if mask[m.start()]:
            ls = src.rfind("\n", 0, m.start()) + 1
            out.append((src.count("\n", 0, m.start()) + 1, m.start(), src[ls:src.find("\n", m.start())].strip()))
    return out


HARNESS = r"""
var window = globalThis, STORE = {}, REG = [], RECORDS = [], REMOVED = [], FILED = [], FETCHES = [], LOGS = [];
window.LSR = {
  getItem: function(k){ return Object.prototype.hasOwnProperty.call(STORE, k) ? STORE[k] : null; },
  setItem: function(k, v){ STORE[k] = String(v); },
  removeItem: function(k){ delete STORE[k]; } };
window.D2R_BUILD = { id: 'vTEST' };
window.D2R_PROFILE = 'main';
/* #41 rank 18 sibling (REG-1552) — the console that SERVED this board: a port that is NOT his live console's, so an ask that
   lands on :17772 is the defect (a board on a scratch console reading his console's picture status). Set on window, because
   _consoleOrigin reads window.location and a top-level `var` in this CommonJS program never reaches globalThis. */
window.location = { origin: 'http://127.0.0.1:17999' };
console.info = function(){ LOGS.push(Array.prototype.join.call(arguments, ' ')); };
var owned = new Set();
var EXTRA_ITEMS = {}, _EXTRA_ITEM_SET = new Set();
function _norm(x){ return String(x == null ? '' : x).toLowerCase(); }
function esc(t){ return String(t == null ? '' : t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function jsArg(t){ return String(t).replace(/\\/g,'\\\\').replace(/'/g,"\\'"); }
function _provAll(){ try { var v = JSON.parse(window.LSR.getItem('d2r_vaultProv') || '{}'); return v || {}; } catch (e) { return {}; } }
%(lanes)s
%(furn)s
%(region)s
%(origin)s
%(evidence)s
/* the register, stubbed around its REAL receipt cut; a name in UNKNOWN mints a TV stub, a name in FILES is filed by the
   door (d2r_muleAssign) — both as the real register does — and the real wrapper's own ledger patch is imitated */
var UNKNOWN = { 'Compendium': 1 }, FILES = { 'Compendium': 'bases' };
window.tvVaultRegister = function(name, witness){
  REG.push({ name: name, witness: witness });
__AMB_GATE__
%(rec)s
  window._ownedAdd(name, _rec);
  if (UNKNOWN[name]){ var t = JSON.parse(STORE['d2r_tvExtraItems'] || '{}'); t[name] = { rarity: 'basic', val: 'tv' };
    STORE['d2r_tvExtraItems'] = JSON.stringify(t); EXTRA_ITEMS[name] = t[name]; }
  var carried = !!(witness && witness.carried);
  if (FILES[name] && !carried){ var a = JSON.parse(STORE['d2r_muleAssign'] || '{}'); a[name] = FILES[name]; STORE['d2r_muleAssign'] = JSON.stringify(a); }
  if (typeof window.kaiChronicleRecord === 'function') window.kaiChronicleRecord({ name: name, status: 'vault-registered', source: 'tv-vault' });
  return { ok: true, label: name, mode: 'new', filed: !!(FILES[name] && !carried),
           refused: carried ? 'carried' : (FILES[name] ? null : 'witness'), why: carried ? 'carried' : 'one look' };
};
window.kaiChronicleRecord = function(r){ RECORDS.push(r); return r; };
/* the removal door, as the real one behaves: only what is held, its filing and its receipt go, the batch is journaled */
window.vaultRemove = function(names, opts){
  REMOVED.push({ names: names.slice(), lane: opts && opts.lane, why: opts && opts.why, proof: (opts && opts.proof) || null });
  var p = JSON.parse(STORE['d2r_vaultProv'] || '{}'), a = JSON.parse(STORE['d2r_muleAssign'] || '{}'), took = [];
  names.forEach(function(n){ if (!owned.has(n)) return; owned['delete'](n); delete p[n]; delete a[n]; took.push(n); });
  STORE['d2r_vaultProv'] = JSON.stringify(p); STORE['d2r_muleAssign'] = JSON.stringify(a);
  if (took.length){ var lg = JSON.parse(STORE['d2r_vaultRemoved'] || '[]'); lg.push({ ts: Date.now(), names: took, lane: opts && opts.lane,
    proof: (opts && opts.proof) || null }); STORE['d2r_vaultRemoved'] = JSON.stringify(lg); }
  return { removed: took };
};
function reset(prov, own){ STORE = {}; if (prov !== undefined) STORE['d2r_vaultProv'] = (typeof prov === 'string') ? prov : JSON.stringify(prov);
  owned = new Set(own || []); REG = []; RECORDS = []; REMOVED = []; FILED = []; FETCHES = []; LOGS = []; EXTRA_ITEMS = {};
  window.D2R_PROFILE = 'main'; }
function prov(){ return JSON.parse(STORE['d2r_vaultProv'] || '{}'); }
function logRow(nm){ return (JSON.parse(STORE['d2r_chronicleInboxLog'] || '[]')).filter(function(r){ return r && r.name === nm; })[0] || null; }
var OUT = {};
(async function(){
%(script)s
process.stdout.write(JSON.stringify(OUT));
})().catch(function(e){ process.stderr.write('THREW ' + (e && e.stack || e)); process.exit(3); });
"""

SORTER = r"""
function sorter(P, A){
  STORE['d2r_vaultProv'] = JSON.stringify(P);
  var assign = A, n = 0, calls = [];
  function muleById(id){ return (id === 'uni-armor' || id === 'uni-small') ? { id: id } : null; }
  function _log(){ LOGS.push(Array.prototype.slice.call(arguments)); }
  window.vaultFile = function(name, w, o){ calls.push({ name: name, witness: w, opts: o }); return { ok: false, refused: 'witness', why: 'stub' }; };
  window._vaultProvSay = function(){ return ''; };
  function suggestMule(){ return { id: 'uni-armor' }; }          /* the router is not under test here */
  window._vaultLastSeenOnMain = function(){ return null; };
%(witstash)s
%(wit)s
%(sort)s
  return calls;
}
function w6(P, A, pool){
  var assign = A;
  function muleById(id){ return (id === 'uni-armor' || id === 'uni-small') ? { id: id } : null; }
  STORE['d2r_vaultProv'] = JSON.stringify(P);
%(w6)s
  return assign;
}
"""

#: game item names only — never his store
CHRONICLE_PAGE = ["Hellfire Torch", "Cranium Basher", "Eye of Etlich", "Nagelring", "Magefist", "Stormshield", "Windforce"]
SESSION = "s_1790543358478_35359"
LOG = ([{"name": "Grief", "status": "in-chronicle", "store": "rwMade", "source": "aic-judge", "tier": "keep",
         "sessionId": SESSION, "frameId": "9_1790543904663", "firstSeenTs": 1790543904663, "loc": None},
        {"name": "Plague", "status": "in-chronicle", "store": "rwMade", "source": "aic-judge", "tier": "keep",
         "sessionId": SESSION, "frameId": "11_1790543968521", "firstSeenTs": 1790543968521, "loc": None},
        {"name": "String of Ears", "status": "in-chronicle", "store": "foundLog", "source": "kai-register",
         "tier": "grail", "sessionId": "s_2", "frameId": "17_1790551926547", "firstSeenTs": 1790551926547,
         "loc": "equipped", "scene": "inventory"}]
       + [{"name": nm, "status": "in-chronicle", "store": "foundLog", "source": "kai-register", "tier": "grail",
           "sessionId": "s_2", "frameId": "%d_1790551%06d" % (20 + i, i), "loc": None, "scene": "chronicle"}
          for i, nm in enumerate(CHRONICLE_PAGE)]
       + [{"name": "Arachnid Mesh", "status": "accepted", "source": "kai-register", "loc": "stash", "scene": "chronicle",
           "sessionId": "s_2", "frameId": "40_1"},
          {"name": "Shako", "status": "in-chronicle", "source": "kai-register", "loc": "floor", "sessionId": "s_2", "frameId": "41_1"},
          {"name": "Gore Rider", "status": "in-chronicle", "source": "kai-register", "loc": None, "sessionId": "s_2", "frameId": "42_1"},
          {"name": "Skin of the Vipermagi", "status": "dismissed", "source": "kai-register", "loc": "equipped", "frameId": "43_1"},
          {"name": "Harlequin Crest", "status": "pending", "source": "kai-register", "loc": "stash", "frameId": "44_1"},
          # §31.2 — inventory LOOT is carried and owned (it used to be 'held' and never filed)
          {"name": "Tal Rasha's Horadric Crest", "status": "in-chronicle", "source": "kai-register", "loc": "inventory",
           "sessionId": "s_2", "frameId": "45_1"},
          # L2 — an unknown name the door files: it mints a TV stub and a filing, both journaled and undone
          {"name": "Compendium", "status": "in-chronicle", "source": "kai-register", "loc": "stash", "scene": "stash",
           "sessionId": "s_2", "frameId": "62_1"},
          # M3 — a read taken on LADDER never replays into main's vault
          {"name": "Nosferatu's Coil", "status": "in-chronicle", "source": "kai-register", "loc": "stash", "scene": "stash",
           "sessionId": "s_L", "frameId": "60_1", "profile": "ladder"}])

SCRIPT = r"""
// ── the door ──
reset({}, []);
var r1 = window._ownedAdd('Grief', { source: 'aic-judge', by: 'aicJudgeApply (keep)', sessionId: 's_1', frameId: '9_1790543904663',
                                     ts: 1790543904663, scene: 'stash', readTier: 'keep' });
OUT.receipt = { r: r1, row: prov()['Grief'], owned: Array.from(owned) };
reset({ Shako: { mule: 'uni-armor', source: 'stash', tier: 'PROVEN', successes: 12, trials: 12,
                 looks: [{ id: 's0', frame: 'a.jpg', conf: 0.9 }] } }, []);
window._ownedAdd('Shako', { source: 'kai-register', frameId: 'b.jpg', sessionId: 's9' });
var afterOne = prov()['Shako'];
window._ownedAdd('Shako', { source: 'hand', frameId: 'c.jpg' });
OUT.noClobber = { one: afterOne, two: prov()['Shako'] };
reset({}, []);
window._ownedAdd('String of Ears', { source: 'kai-register', frameId: 'f1', sessionId: 's_2', loc: 'equipped' });
window._ownedAdd('String of Ears', { source: 'kai-register', frameId: 'f2', sessionId: 's_3', scene: 'inventory' });
window._ownedAdd('String of Ears', { source: 'kai-register', frameId: 'f1', sessionId: 's_2' });
OUT.merge = prov()['String of Ears'];
reset({}, []);
var r4 = window._ownedAdd('Nagelring', {});
OUT.noSource = { r: r4, owned: Array.from(owned), prov: prov() };
reset('{broken', []);
var r5 = window._ownedAdd('Nagelring', { source: 'hand' });
OUT.unreadable = { r: r5, raw: STORE['d2r_vaultProv'], owned: Array.from(owned) };

// ── the route (§28 + §31.2) ──
var pairs = [['equipped','inventory',null],['stash',null,null],['cube',null,null],['mule',null,null],['stash','chronicle',null],
             [null,'chronicle',null],['floor',null,null],[null,'loot',null],['inventory',null,'Shako'],[null,'inventory',null],
             [null,null,null],[null,'stash',null],[null,'gameplay',null],['EQUIPPED',null,null],['inventory',null,'Horadric Cube'],
             ['inventory',null,'Annihilus'],['inventory',null,'Small Charm of Good Luck'],['inventory',null,'Super Healing Potion'],
             ['vendor',null,null],[null,'trade',null],['inventory',null,null]];
OUT.routes = pairs.map(function(p){ var v = window._vaultHoldingRoute(p[0], p[1], p[2]); return [p[0], p[1], p[2], v.route, v.why, !!v.leave]; });
reset({}, []);
var live = window._liveReadRoute({ name: 'String of Ears', loc: 'equipped', scene: 'inventory', sessionId: 's_2',
                                   frameId: '17_1790551926547', source: 'kai-register', tier: 'grail', firstSeenTs: 1790551926547, conf: 0.91 });
var chron = window._liveReadRoute({ name: 'Hellfire Torch', loc: null, scene: 'chronicle', sessionId: 's_2', frameId: '20_1', source: 'kai-register' });
var chronStash = window._liveReadRoute({ name: 'Arachnid Mesh', loc: 'stash', scene: 'chronicle', sessionId: 's_2', frameId: '40_1', source: 'kai-register' });
var unknown = window._liveReadRoute({ name: 'Gore Rider', loc: null, scene: null, source: 'kai-register' });
OUT.live = { live: live, chron: chron, chronStash: chronStash, unknown: unknown, owned: Array.from(owned).sort(),
             row: prov()['String of Ears'], reg: REG };

// ── H1 — the HELD sighting routes, whole, and its frame is the one cited ──
reset({}, []);
var held = window._liveReadRoute({ name: 'String of Ears', loc: null, scene: 'chronicle', frameId: '20_1790551000000',
                                   heldLoc: 'equipped', heldScene: 'inventory', heldFrame: '17_1790551926547', heldTs: 1790551926547,
                                   sessionId: 's_2', source: 'kai-register', firstSeenTs: 1790551000000 });
OUT.held = { r: held, row: prov()['String of Ears'], owned: Array.from(owned) };
reset({}, []);
OUT.register = REGISTER_ITEMS.map(function(it){ var r = window._liveReadRoute(Object.assign({ source: 'kai-register' }, it));
  return { name: it.name, route: r.route, frame: r.frame, row: prov()[it.name] || null }; });

// ── §31.2 — CARRIED: owned right away, on the strip, never filed; LANDS on a stash look ──
reset({}, []);
var car = window._liveReadRoute({ name: 'Shako', loc: 'inventory', scene: 'inventory', frameId: '30_1', sessionId: 's_3',
                                  character: 'KonyoSorc', source: 'kai-register', firstSeenTs: 1790600000000 });
var carRow = prov()['Shako'];
var carNames = window._carriedNames(function(){ return false; });
var carWords = window._ownedProvWords(carRow);
var carEv = window._vaultEvidenceOf('Shako');
window._liveReadRoute({ name: 'Shako', loc: 'stash', scene: 'stash', frameId: '31_1', sessionId: 's_3', source: 'kai-register',
                        firstSeenTs: 1790600100000 });
var landed = prov()['Shako'];
OUT.carried = { r: car, row: carRow, names: carNames.map(function(c){ return c.name + '|' + c.character; }), words: carWords,
                evSeen: carEv.seen, landed: landed, after: window._carriedNames(function(){ return false; }).map(function(c){ return c.name; }),
                owned: Array.from(owned), reg: REG.map(function(x){ return { name: x.name, carried: !!(x.witness && x.witness.carried) }; }),
                landedEv: window._vaultEvidenceOf('Shako').note };
// ── §31.2 — LEAVES only on a real signal, with its frame; absence and a stash-held floor look never un-own ──
// (review of 20c0df1e, H-1: a drop leaves only what it POSTDATES, so every read here carries its own time — a drop with no
//  time cannot be put in order and changes nothing; test_carried_loot_holds_its_time_and_its_name drives that case)
reset({}, []);
window._liveReadRoute({ name: 'Shako', loc: 'inventory', frameId: '30_1', sessionId: 's_3', source: 'kai-register', character: 'KonyoSorc',
                        firstSeenTs: 1790600000000 });
var noProof = window._liveReadRoute({ name: 'Shako', loc: 'floor', frameId: '', sessionId: 's_3', source: 'kai-register', firstSeenTs: 1790600100000 });
var stillOwned = owned.has('Shako');
var left = window._liveReadRoute({ name: 'Shako', loc: 'floor', frameId: '32_1', sessionId: 's_3', source: 'kai-register', firstSeenTs: 1790600200000 });
window._ownedAdd('Nagelring', { source: 'kai-register', loc: 'stash', frameId: '33_1', ts: 1790600300000 });
var notCarried = window._liveReadRoute({ name: 'Nagelring', loc: 'floor', frameId: '34_1', source: 'kai-register', firstSeenTs: 1790600400000 });
window._liveReadRoute({ name: 'Magefist', loc: 'inventory', frameId: '35_1', sessionId: 's_3', source: 'kai-register', firstSeenTs: 1790600500000 });
var vendor = window._liveReadRoute({ name: 'Magefist', loc: null, scene: 'vendor', frameId: '36_1', sessionId: 's_3', source: 'kai-register',
                                     firstSeenTs: 1790600600000 });
OUT.leave = { noProof: noProof, stillOwned: stillOwned, left: left, owned: Array.from(owned).sort(), removed: REMOVED,
              notCarried: notCarried, vendor: vendor };
// ── §31.2 — "carried, last seen <when> - still have it?" after a few game sessions unseen ──
reset({ Shako: { kind: 'owned', source: 'kai-register', carried: true, character: 'KonyoSorc', ts: 1000, sessionId: 's_a',
                 looks: [{ id: 's_a', frame: 'f', at: new Date(1000).toISOString() }] } }, ['Shako']);
var LG = [{ name: 'X', sessionId: 's_b', firstSeenTs: 2000 }, { name: 'Y', sessionId: 's_c', firstSeenTs: 3000 },
          { name: 'Z', sessionId: 's_a', firstSeenTs: 4000 }];
STORE['d2r_chronicleInboxLog'] = JSON.stringify(LG);
var st2 = window._carriedStale('Shako');
LG.push({ name: 'L', sessionId: 's_e', firstSeenTs: 6000, profile: 'ladder' });
STORE['d2r_chronicleInboxLog'] = JSON.stringify(LG);
var stL = window._carriedStale('Shako');
LG.push({ name: 'W', sessionId: 's_d', firstSeenTs: 5000 });
STORE['d2r_chronicleInboxLog'] = JSON.stringify(LG);
var st3 = window._carriedStale('Shako');
var ownedAfterStale = owned.has('Shako');
STORE['d2r_chronicleInboxLog'] = '{broken';
var stU = window._carriedStale('Shako');
OUT.stale = { st2: st2, stL: stL, st3: st3, stU: stU, owned: ownedAfterStale };

// ── the backfill ──
reset({}, ['Plague', 'Grief']);
STORE['d2r_chronicleInboxLog'] = JSON.stringify(%(log)s);
var b1 = window._ownedProvBackfill();
var snap = JSON.stringify(STORE), ownSnap = JSON.stringify(Array.from(owned).sort());
var b2 = window._ownedProvBackfill();
OUT.backfill = { b1: b1, b2: b2, idempotent: (JSON.stringify(STORE) === snap && JSON.stringify(Array.from(owned).sort()) === ownSnap),
                 owned: Array.from(owned).sort(), prov: prov(), records: RECORDS.slice(),
                 soeRow: logRow('String of Ears'), compRow: logRow('Compendium'),
                 tvx: JSON.parse(STORE['d2r_tvExtraItems'] || '{}'), assign: JSON.parse(STORE['d2r_muleAssign'] || '{}'),
                 extra: Object.keys(EXTRA_ITEMS) };
// ── the evidence panel, on the backfilled store ──
var mG = window._vaultEvidenceOf('Grief'), mS = window._vaultEvidenceOf('String of Ears'), mN = window._vaultEvidenceOf('Nothing Here');
OUT.evidence = { grief: mG, soe: mS, none: mN,
                 griefHtml: window._vaultEvidenceHtml(mG, { state: 'checking', say: 'looking' }),
                 noneHtml: window._vaultEvidenceHtml(mN, { state: 'none', say: '' }),
                 chip: window._vaultEvidenceChip('Grief'), chipNone: window._vaultEvidenceChip('Nothing Here'),
                 line: window._vaultEvidenceLine('Grief') };
// the picture: loads -> shown; does not load -> the console's words; the console silent -> UNKNOWN
window._tvdFrameChain = function(id){ return ['http://bridge/frame?id=' + id, 'tv/frames/hist/' + id + '.jpg']; };
var LOADS = {};
window.Image = function(){ var self = this; Object.defineProperty(self, 'src', { get: function(){ return self._s; },
  set: function(v){ self._s = v; setTimeout(function(){ var f = LOADS[v] ? self.onload : self.onerror; if (f) f.call(self); }, 0); } }); };
var FETCH_IMPL = null;
window.fetch = function(url, opt){ FETCHES.push(url); return FETCH_IMPL(url); };
function pic(id){ return new Promise(function(res){ window._vaultEvidencePicture(id, res); }); }
LOADS['tv/frames/hist/9_1790543904663.jpg'] = 1;
FETCH_IMPL = function(){ return Promise.resolve({ ok: true, json: function(){ return { ok: true, pictures: {
  '17_1790551926547': { present: false, code: 'disk-floor', why: 'the recorder was under its disk floor when this read was taken — the picture was never written' } } }; } }); };
var p1 = await pic('9_1790543904663');
var p2 = await pic('17_1790551926547');
FETCH_IMPL = function(){ return Promise.reject(new Error('refused')); };
var p3 = await pic('17_1790551926547');
var p4 = await pic('');
/* #41 rank 18 sibling (REG-1552) — a board nobody served (no console origin: file://, the public site) asks NOBODY: no
   fetch at all, never his :17772 by name, and the panel says UNKNOWN */
var _o0 = window.location.origin, _f0 = FETCHES.length; window.location.origin = 'null';
var p5 = await pic('17_1790551926547');
window.location.origin = _o0;
OUT.pictures = { present: p1, gone: p2, silent: p3, none: p4, fetches: FETCHES, noOrigin: p5, noOriginFetches: FETCHES.length - _f0,
                 presentHtml: window._vaultEvidencePicHtml(mG, p1), goneHtml: window._vaultEvidencePicHtml(mS, p2),
                 silentHtml: window._vaultEvidencePicHtml(mS, p3) };
// ── the undo ──
var u1 = window._ownedProvBackfillUndo();
var u2 = window._ownedProvBackfillUndo();
OUT.undo = { u1: u1, u2: u2, owned: Array.from(owned).sort(), prov: prov(), removed: REMOVED.slice(),
             soeRow: logRow('String of Ears'), compRow: logRow('Compendium'),
             tvx: JSON.parse(STORE['d2r_tvExtraItems'] || '{}'), assign: JSON.parse(STORE['d2r_muleAssign'] || '{}'),
             extra: Object.keys(EXTRA_ITEMS) };
// ── M3 — per world: on LADDER only a row read on ladder replays; main's reads never land there ──
reset({}, ['Plague', 'Grief']);
window.D2R_PROFILE = 'ladder';
STORE['d2r_chronicleInboxLog'] = JSON.stringify(%(log)s);
var bL = window._ownedProvBackfill();
OUT.ladder = { b: bL, owned: Array.from(owned).sort(), prov: prov() };
window.D2R_PROFILE = 'main';
// ── M3 — his removals: a removed name never comes back; an owned name removed after its row gets no receipt from it ──
reset({}, ['Plague', 'Grief']);
STORE['d2r_chronicleInboxLog'] = JSON.stringify(%(log)s);
STORE['d2r_vaultRemoved'] = JSON.stringify([{ ts: 1790543968521 + 60000, names: ['Plague'] },
                                             { ts: 1790551926547 - 1, names: ['String of Ears'] }]);
var bR = window._ownedProvBackfill();
OUT.removals = { b: bR, owned: Array.from(owned).sort(), prov: prov() };
reset({}, ['Plague', 'Grief']);
STORE['d2r_chronicleInboxLog'] = JSON.stringify(%(log)s);
STORE['d2r_vaultRemoved'] = '[broken';
OUT.removalsUnread = { b: window._ownedProvBackfill(), prov: prov() };
// ── a receipt is never a witness ──
OUT.sorter = sorter({ 'Receipt Only': { kind: 'owned', source: 'hand', at: '2026-09-28T00:00:00Z', where: 'the card' },
                      'Lost Home': { mule: 'uni-armor', source: 'hand', by: 'hand', at: '2026-09-01T00:00:00Z', where: 'the mule window' },
                      /* his #267 ruling: a receipt's stash looks from two sessions ARE a witness - gathered, never the receipt itself */
                      'Two Stash Looks': { kind: 'owned', source: 'kai-register', looks: [
                          { id: 's_1', frame: 'f_1', conf: null, at: '2026-10-07T08:00:00Z', loc: 'stash' },
                          { id: 's_2', frame: 'f_2', conf: null, at: '2026-10-07T09:00:00Z', loc: 'stash' }] } }, {})
                 .map(function(c){ return { name: c.name, witnessed: !!c.witness, gathered: (c.witness && c.witness.gathered) || null }; });
OUT.w6 = w6({ 'Receipt Only': { kind: 'owned', source: 'hand' }, 'Stash Witness': { mule: 'uni-armor', source: 'stash' } },
            { 'Receipt Only': 'uni-armor', 'Stash Witness': 'uni-armor' }, []);
"""

#: the REAL register, driven: its CARRIED branch must own and never file (the law above stubs the register; this one
#: runs the shipped function with its neighbours stubbed)
REGISTER = r"""
var window = globalThis, STORE = {}, FILED = [];
window.LSR = { getItem: function(k){ return Object.prototype.hasOwnProperty.call(STORE, k) ? STORE[k] : null; },
               setItem: function(k, v){ STORE[k] = String(v); }, removeItem: function(k){ delete STORE[k]; } };
window.D2R_BUILD = { id: 'vTEST' }; window.D2R_PROFILE = 'main';
var owned = new Set(), assign = {}, ITEMS = [], EXTRA_ITEMS = {};
var document = { getElementById: function(){ return null; }, querySelector: function(){ return null; } };
function _ensureSocketBaseEntry(){} function persistOwned(){} function saveA(){} function renderVault(){}
function suggestMule(n){ return { id: 'uni-armor', why: '' }; }
function muleById(id){ return id === 'uni-armor' ? { id: id, name: 'UNI-ARMOR' } : null; }
function _vNoHomeWhy(){ return 'no home'; }
window.vaultFile = function(name, w, o){ FILED.push({ name: name, mule: o && o.mule }); assign[name] = o && o.mule; return { ok: true, mule: o && o.mule }; };
%(lanes)s
%(furn)s
%(region)s
%(rule)s
%(reg)s
var OUT = {};
/* #202 (his 2026-10-27 ruling) - a read registers on its SECOND session: each fixture brings two */
OUT.once = window.tvVaultRegister('Arachnid Mesh', { lane: 'stash', by: 'kai-register', sessions: [{ session: 's_5', frame: '50_1' }] });
OUT.carried = window.tvVaultRegister('Shako', { lane: 'inventory', by: 'kai-register', carried: true, character: 'KonyoSorc',
                                                sessions: [{ session: 's_3', frame: '30_1' }, { session: 's_4', frame: '40_1' }] });
OUT.carriedRow = JSON.parse(STORE['d2r_vaultProv'] || '{}')['Shako'];
OUT.filedAfterCarried = FILED.slice();
OUT.stash = window.tvVaultRegister('Nagelring', { lane: 'stash', by: 'kai-register', sessions: [{ session: 's_3', frame: '31_1' }, { session: 's_4', frame: '41_1' }] });
OUT.filed = FILED.slice();
OUT.owned = Array.from(owned).sort();
process.stdout.write(JSON.stringify(OUT));
"""

#: M3 — the router itself, driven: the backfill stamp forks exactly as the stores it describes
ROUTER = r"""
var window = globalThis, RAW = {};
window.localStorage = { getItem: function(k){ return Object.prototype.hasOwnProperty.call(RAW, k) ? RAW[k] : null; },
                        setItem: function(k, v){ RAW[k] = String(v); }, removeItem: function(k){ delete RAW[k]; } };
window._D2R_OWNER = true; window.D2R_PROFILE = 'ladder'; window._D2R_LPFX = 'L·'; window._D2R_PFX = 'W·';
%(router)s
var OUT = { stamp: window.LSR.key('d2r_ownedProvBackfill'), owned: window.LSR.key('d2r_owned'), prov: window.LSR.key('d2r_vaultProv') };
window.D2R_PROFILE = 'main';
OUT.mainStamp = window.LSR.key('d2r_ownedProvBackfill');
process.stdout.write(JSON.stringify(OUT));
"""

#: M4 — the un-seed undo, driven: the names it puts back carry a ledger-restore receipt stamped with the snapshot time
UNSEED = r"""
var window = globalThis, STORE = {};
window.LSR = { getItem: function(k){ return Object.prototype.hasOwnProperty.call(STORE, k) ? STORE[k] : null; },
               setItem: function(k, v){ STORE[k] = String(v); }, removeItem: function(k){ delete STORE[k]; } };
window.localStorage = { getItem: function(){ return null; }, setItem: function(){}, removeItem: function(){} };
window.D2R_BUILD = { id: 'vTEST' }; window.D2R_PROFILE = 'main';
var owned = new Set(['Grief']);
console.log = function(){}; console.warn = function(){};
var location = { reload: function(){} };
function uiConfirm(){ return Promise.resolve(true); }
%(lanes)s
%(region)s
%(unseed)s
STORE['d2r_owned'] = JSON.stringify(['Grief']);
STORE['d2r_vaultProv'] = JSON.stringify({ Grief: { kind: 'owned', source: 'aic-judge', by: 'x', ts: 5 } });
STORE['d2r_unseedBackup'] = JSON.stringify({ at: 1790000000000, d2r_owned: JSON.stringify(['Grief', 'Shako', 'Nagelring']) });
window._d2rUnseedRestore();
setTimeout(function(){
  process.stdout.write(JSON.stringify({ owned: JSON.parse(STORE['d2r_owned'] || '[]'), prov: JSON.parse(STORE['d2r_vaultProv'] || '{}'),
                                        report: JSON.parse(STORE['d2r_unseedRestoreReport'] || 'null') }));
}, 20);
"""

#: M4 — owned_restore, driven: the board script control_app sends, run against the real door
RESTORE = r"""
var window = globalThis, STORE = {};
window.LSR = { getItem: function(k){ return Object.prototype.hasOwnProperty.call(STORE, k) ? STORE[k] : null; },
               setItem: function(k, v){ STORE[k] = String(v); }, removeItem: function(k){ delete STORE[k]; } };
window.D2R_BUILD = { id: 'vTEST' }; window.D2R_PROFILE = 'main';
var document = { getElementById: function(){ return null; } };
var owned = new Set(['Grief']);
%(lanes)s
%(region)s
window._vaultReloadOwned = function(){ return 1; };
STORE['d2r_owned'] = JSON.stringify(['Grief']);
STORE['d2r_vaultProv'] = JSON.stringify({ Grief: { kind: 'owned', source: 'aic-judge', by: 'x', ts: 5 } });
var R = JSON.parse(%(js)s);
process.stdout.write(JSON.stringify({ r: R, owned: JSON.parse(STORE['d2r_owned'] || '[]'), prov: JSON.parse(STORE['d2r_vaultProv'] || '{}') }));
"""

FURN_FROM = "var _FURNITURE_WORDS = ['horadric cube'"
FURN_TO = "/* THE MAIN LEDGER, AS THE CONSOLE PUBLISHES IT"
REG_FROM = "  window.tvVaultRegister = function(name, witness){\n"


def _intake_rule(s):
    """#202 - the floor, the bar, the one look rule and the seen-once hold, cut from the page the way the register finds them."""
    import re as _re
    floor = _re.search(r"\n  var VAULT_WITNESS_FLOOR = [^;]+;", s).group(0).strip()
    bar = _re.search(r"\n  var VAULT_WITNESS_MIN = [^;]+;", s).group(0).strip()
    return "\n".join([floor, bar, _between(s, "  function _vaultLookConf(look){\n", "  window._vaultIntakePending = function(){\n"),
                      "window._vaultNotAnItem = window._vaultNotAnItem || function(){ return null; };"])
REG_TO = "\n  // v731 — reverse a mistaken vault"
#: L-1 (round 4) published the register's name resolution as window._vaultResolveName and the register calls it, so the SHIPPED
#: register cut below must carry that door too (it sits directly above the register on the page)
RESOLVER_FROM = "  window._vaultResolveName = function(name){\n"
ROUTER_FROM = "window._LP_FORKED = new Set(["
ROUTER_TO = "    raw: RAW, key: key\n  };\n})();\n"
UNSEED_FROM = "window._d2rUnseedRestore = function(){\n"
UNSEED_TO = "\n</script>"


def _node(prog, tag):
    if "__AMB_GATE__" in prog:
        prog = prog.replace("__AMB_GATE__", amb_gate())
    fd, path = tempfile.mkstemp(prefix=".owned_prov_%s_" % tag, suffix=".js", dir=HERE)
    try:
        with io.open(fd, "w", encoding="utf-8") as fh:
            fh.write(prog)
        r = subprocess.run([NODE, path], capture_output=True, text=True, timeout=60)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    if r.returncode != 0:
        raise AssertionError("the %s harness would not run — UNKNOWN, not passing: %s" % (tag, (r.stderr or r.stdout)[-1500:]))
    return json.loads(r.stdout)


def compile_register(rows):
    """The console's register compile, with main_character's LEDGER redirected into a throwaway dir. -> the register

    ⚠ REG-1583, MEASURED 2026-09-30 by the v3526 gate run's live-state watch: _kai_compile_register feeds main_character.saw()
    BY DESIGN (v2361) and saw() writes main_character.LEDGER - tv/main_character.json, bound at import. Three laws that
    called the compiler bare created that file in the tree they ran from, and on his checkout that file is HIS gear
    ledger (what he wears, Wilson-scored from sightings): fixture sightings would have counted as his. LEDGER is
    import-bound - no env var moves it - so the only redirect that takes is the attribute, asserted before the compile
    runs and restored after. Every law that compiles the register comes through here. [[feedback-fixtures-never-touch-live-data]]
    """
    import control_app as ca
    import main_character as mc
    d = tempfile.mkdtemp(prefix="owned_mc_")
    saved = mc.LEDGER
    mc.LEDGER = os.path.join(d, "main_character.json")
    try:
        if not mc.LEDGER.startswith(d):
            raise AssertionError("the main_character redirect did not take - refusing to compile into his ledger")
        return ca._kai_compile_register(rows)
    finally:
        mc.LEDGER = saved
        shutil.rmtree(d, ignore_errors=True)


def _register_items():
    """H1, END TO END: the SHIPPED register compiles a Chronicle-page sighting followed by a WORN one, and the item it hands
    the board is built exactly as the console's propose builder builds it (held fields beside the first sighting)."""
    rows = [{"lane": "deep", "ts": 1790551000000, "frameId": "20_1790551000000", "sessionId": "s_2", "scene": "chronicle",
             "names": ["String of Ears"], "names_loc": {}},
            {"lane": "deep", "ts": 1790551926547, "frameId": "17_1790551926547", "sessionId": "s_2", "scene": "inventory",
             "names": ["String of Ears"], "names_loc": {"String of Ears": "equipped"}},
            # a Chronicle page with a PLACE on it never makes a holding sighting (§28)
            {"lane": "deep", "ts": 1790551000100, "frameId": "21_1790551000100", "sessionId": "s_2", "scene": "chronicle",
             "names": ["Magefist"], "names_loc": {"Magefist": "stash"}},
            # ⚠ OUT OF ORDER: the WORN read arrives first and an EARLIER Chronicle-page read after it — the branch that
            # replaces the first sighting. The old code took that frame and scene and KEPT the worn place (the mix).
            {"lane": "deep", "ts": 1790552000000, "frameId": "18_1790552000000", "sessionId": "s_2", "scene": "inventory",
             "names": ["War Traveler"], "names_loc": {"War Traveler": "equipped"}},
            {"lane": "deep", "ts": 1790550000000, "frameId": "19_1790550000000", "sessionId": "s_2", "scene": "chronicle",
             "names": ["War Traveler"], "names_loc": {}}]
    reg = compile_register(rows)
    out = []
    for x in reg:
        it = {"name": x.get("name"), "firstSeenTs": x.get("firstSeenTs"), "frameId": x.get("frameId"), "tier": x.get("tier"),
              "sessionId": "s_2", "loc": x.get("loc"), "scene": x.get("scene")}
        if x.get("heldLoc"):
            it.update({"heldLoc": x.get("heldLoc"), "heldScene": x.get("heldScene"), "heldFrame": x.get("heldFrame"),
                       "heldTs": x.get("heldTs")})
        # H3 (review of bd976210) — and the LATEST sighting, exactly as the console's builder now hands it over
        if x.get("latestLoc") or x.get("latestScene"):
            it.update({"latestLoc": x.get("latestLoc"), "latestScene": x.get("latestScene"),
                       "latestFrame": x.get("latestFrame"), "latestTs": x.get("latestTs")})
        out.append(it)
    return reg, out


def _drive():
    s = _src()
    assert s.count(WIT_STASH_LINE) == 1, "the stash-place constant moved"
    sort_src = SORTER % {"witstash": WIT_STASH_LINE, "wit": _between(s, WIT_FROM, WIT_TO), "sort": _between(s, SORT_FROM, SORT_TO),
                         "w6": _between(s, W6_FROM, W6_TO)}
    reg, items = _register_items()
    script = ("var REGISTER_ITEMS = %s;\n" % json.dumps(items)) + sort_src + SCRIPT % {"log": json.dumps(LOG)}
    prog = HARNESS % {"lanes": _lanes(s), "furn": _between(s, FURN_FROM, FURN_TO), "region": owned_prov_region(s),
                      "origin": _origin_line(s), "evidence": _marked(s, EV_BEGIN, EV_END),
                      "rec": _between(s, REC_FROM, REC_TO), "script": script}
    out = _node(prog, "main")
    out["_register"] = reg
    return out


_CACHE = {}


def out():
    if "o" not in _CACHE:
        _CACHE["o"] = _drive()
    return _CACHE["o"]


def _code_only(text):
    """`text` as JS CODE — comments, strings and template text blanked (same length), via the census scanner."""
    m = code_mask(text.join(["<script>", "</script>"]))
    return "".join(ch if (m[k + len("<script>")] or ch == "\n") else " " for k, ch in enumerate(text))


class TheCensus(unittest.TestCase):

    def test_no_bare_owned_add_outside_the_door(self):
        s = _src()
        i = s.index(BEGIN)
        j = s.index(END)
        sites = code_sites(s)
        inside = [x for x in sites if i < x[1] < j]
        outside = [x for x in sites if not (i < x[1] < j)]
        self.assertEqual(1, len(inside), "the door itself should hold exactly one owned.add: %r" % inside)
        named = {}
        for ln, _pos, text in outside:
            if text in NAMED:
                named[text] = named.get(text, 0) + 1
        bare = [(ln, text) for ln, _pos, text in outside if text not in NAMED]
        self.assertEqual([], bare, "a door adds to `owned` without writing provenance — route it through "
                                   "window._ownedAdd(name, {source, ...}): %r" % bare[:6])
        for text, (want, why) in NAMED.items():
            self.assertEqual(want, named.get(text, 0), "a named exception no longer matches the board — prune NAMED: %r" % text)

    def test_the_scanner_sees_every_site_the_old_board_had(self):
        """The instrument, pinned: the board BEFORE this change had 22 bare sites, and a scanner that loses its way
        in a regex literal found 1. Run on a planted fixture holding every shape the file uses."""
        fixture = ("<script>\nvar re = /[‘’`]/g; owned.add(a);\n// owned.add(comment)\n/* owned.add(block) */\n"
                   "var s = 'owned.add(str)'; var t = `x ${owned.add(b)} y`; var u = `owned.add(tmpl)`;\n"
                   "if (x) owned['add'](c); var d = a / b; owned.add(e);\n</script>\n<p>owned.add(html)</p>\n")
        got = [t for _l, _p, t in code_sites(fixture)]
        self.assertEqual(4, len(got), "the census scanner miscounts code sites on a planted fixture: %r" % got)


class TheOwnedStoreIsOnlyGrownThroughTheDoor(unittest.TestCase):
    """⚠ M4 (review of 77d8d8b5) — `owned.add(` was censused and `setItem('d2r_owned', …)` was not, so a door that wrote
    the STORE grew the vault with no receipt: control_app.owned_restore wrote a union list straight into d2r_owned, and the
    un-seed Undo wrote a whole snapshot back. Every code occurrence of the key is classified here, and any write that can
    GROW the set must go through window._ownedAdd — or be named, with its reason."""

    #: setItem('d2r_owned', ARG) — the ARG shapes that cannot add a name the census above did not already see
    ALLOWED_ARGS = {
        "JSON.stringify([...owned])": "the in-memory Set, which only grows through owned.add — censused above",
        "JSON.stringify(Array.from(owned))": "the in-memory Set, which only grows through owned.add — censused above",
        "JSON.stringify(keepO)": "the un-seed strip — a FILTER of the stored list (shrink-only)",
        "JSON.stringify(own2)": "the seed ledger clean-up — a FILTER of the stored list (shrink-only)",
        "JSON.stringify(kept)": "the v2205 undo — a FILTER of the stored list (shrink-only), verified before stamping",
    }
    #: any OTHER code occurrence of the key: a read, or a list/descriptor named with its reason
    NAMED_LISTS = {
        "var _probe = ['d2r_owned', 'd2r_foundLog', 'd2r_setPieces', 'd2r_rwMade'];": (1, "a world probe — reads only"),
        "['d2r_owned', 'd2r_foundLog', 'd2r_magicFinds', 'd2r_copies'].forEach(function(k){":
            (1, "the bloodcrescent RENAME — maps one spelling to the other, never adds a name that was not there"),
        "['d2r_foundLog','d2r_setPieces','d2r_rwMade','d2r_owned','d2r_rwVerify',":
            (2, "the un-seed backup (reads) and the un-seed Undo (writes the snapshot back) — the Undo is the one write, "
                "and test_the_unseed_undo_writes_its_receipts drives it"),
        "owned:   Object.freeze({ store: 'd2r_owned', say: '✓ owned items',": (1, "the vault reset's descriptor — CLEARS"),
        "var KS = ['d2r_setPieces', 'd2r_foundLog', 'd2r_owned'];": (1, "a ledger read — reads only"),
        "if (k === 'd2r_owned'){": (1, "the un-seed Undo recognising the owned key — the growth it guards goes through "
                                       "window._ownedAdd (test_the_unseed_undo_writes_its_receipts drives it)"),
        "if (_qd('d2r_owned')) return null;": (1, "V1 merge join — the frame verdict asks the store door whether owned is "
                                                 "QUARANTINED (then UNKNOWN, never 'gone'); it reads the door's registry, "
                                                 "never the store, and writes nothing (test_a_frame_verdict_reads_a_"
                                                 "quarantined_store_as_unknown drives it)"),
        "'d2r_copies','d2r_vaultAutoIntake','d2r_vaultShareOverride','d2r_autoLanes','d2r_owned','d2r_intakeSeen','d2r_intakeLog'],":
            (1, "Vault v3 Save / Load profile (Elad t663u-t665u) - the profile's store list. Load writes back a whole "
                "snapshot HE saved, behind a Danger confirm, and restores d2r_vaultProv from the same file, so the "
                "receipts come back with the names; it never adds a name outside the saved pair"),
        "LS.quarantine('d2r_owned', 'holds '": (1, "REG-2527 — the load's doctor could not copy the entries that are not "
                                                  "names aside (a full storage), so it QUARANTINES the owned key: every "
                                                  "write of it is refused and the saved list keeps them; it grows nothing "
                                                  "(test_entries_that_are_not_names_are_kept_aside drives it)"),
    }
    READ_BEFORE = re.compile(r"(getItem|\.key|_chLsGet)\(\s*$")
    WRITE_BEFORE = re.compile(r"setItem\(\s*$")

    def _arg(self, s, j):
        """The setItem argument after the key's closing quote at j. -> str (whitespace collapsed)"""
        k = s.index(",", j) + 1
        depth, q = 0, k
        while q < len(s):
            c = s[q]
            if c in "([{":
                depth += 1
            elif c in ")]}":
                if depth == 0:
                    break
                depth -= 1
            q += 1
        return re.sub(r"\s+", "", s[k:q])

    def test_every_occurrence_of_the_key_is_a_read_a_named_list_or_a_write_that_cannot_grow_it(self):
        s = _src()
        mask = code_mask(s, keep_strings=True)
        # The ladder fork set names d2r_owned among sibling keys. Inserting a key on that
        # line used to make a name-list look unclassified, because the census matched a frozen
        # prefix of the tokens before d2r_owned. A token inside the set literal is a name.
        head = "window._LP_FORKED = new Set(["
        fork_at = s.find(head)
        fork_end = s.find("]);", fork_at) if fork_at >= 0 else -1
        self.assertGreaterEqual(fork_at, 0, "the ladder fork set is not where this census cuts it")
        self.assertGreater(fork_end, fork_at, "the ladder fork set does not close")
        bad, lists, fork_hits = [], {}, 0
        for m in re.finditer(r"""['"]d2r_owned['"]""", s):
            if not mask[m.start()]:
                continue
            if fork_at <= m.start() < fork_end:
                fork_hits += 1
                continue
            ls = s.rfind("\n", 0, m.start()) + 1
            line = s[ls:s.find("\n", m.start())].strip()
            before = s[max(ls, m.start() - 40):m.start()]
            if self.READ_BEFORE.search(before):
                continue
            if self.WRITE_BEFORE.search(before):
                arg = self._arg(s, m.end())
                if arg not in {re.sub(r"\s+", "", a) for a in self.ALLOWED_ARGS}:
                    bad.append("line %d writes d2r_owned with %r — a write that can GROW the owned set must go through "
                               "window._ownedAdd" % (s.count("\n", 0, m.start()) + 1, arg[:80]))
                continue
            key = next((k for k in self.NAMED_LISTS if line.startswith(k)), None)
            if key is None:
                bad.append("line %d names d2r_owned in a way this census cannot classify: %r" % (s.count("\n", 0, m.start()) + 1, line[:100]))
            else:
                lists[key] = lists.get(key, 0) + 1
        self.assertEqual([], bad)
        self.assertEqual(1, fork_hits,
                         "d2r_owned must be named once inside the ladder fork set — a name, never a write")
        for k, (want, why) in self.NAMED_LISTS.items():
            self.assertEqual(want, lists.get(k, 0), "a named d2r_owned list no longer matches the board — prune it: %r" % k)

    def test_a_failed_confirm_puts_the_name_back_with_the_receipt_it_carried(self):
        """The two rollbacks inside the provenance door, and the same rollback in the set-dupe
        migration, did owned.add. vaultRemove had already dropped the receipt into the batch.
        Putting the name back without that receipt leaves the item owned and the proof gone.
        The door restores the row the batch still holds, filing row included, and invents
        nothing when the batch carried no row."""
        if NODE is None:
            self.skipTest("node is absent — the put-back door was not driven")
        region = owned_prov_region()
        prog = (
            "var window = globalThis, STORE = {};\n"
            "window.LSR = { getItem: function(k){ return Object.prototype.hasOwnProperty.call(STORE, k) ? STORE[k] : null; },\n"
            "  setItem: function(k, v){ STORE[k] = String(v); }, removeItem: function(k){ delete STORE[k]; } };\n"
            "window.D2R_BUILD = { id: 'vTEST' };\n"
            "var owned = new Set();\n"
            + region +
            "STORE['d2r_vaultProv'] = '{}';\n"
            "var kept = { kind: 'owned', source: 'kai-register', frameId: 'cited.jpg', looks: [{ frame: 'cited.jpg' }] };\n"
            "var filing = { mule: 'sets', source: 'stash', tier: 'PROVEN', looks: [{ frame: 'gone.jpg' }] };\n"
            "window._ownedPutBack(['Shako', 'Tal', 'Magefist'], { prov: { Shako: kept, Tal: filing } });\n"
            "var all = JSON.parse(STORE['d2r_vaultProv'] || '{}');\n"
            "process.stdout.write(JSON.stringify({ owned: Array.from(owned).sort(), shako: all.Shako || null,\n"
            "  tal: all.Tal || null, magefist: Object.prototype.hasOwnProperty.call(all, 'Magefist') }));\n"
        )
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, r.returncode, "the put-back door would not run — UNKNOWN, not passing: %s"
                         % (r.stderr or r.stdout)[-800:])
        got = json.loads(r.stdout)
        self.assertEqual(["Magefist", "Shako", "Tal"], got["owned"])
        self.assertEqual("kai-register", got["shako"]["source"])
        self.assertEqual("cited.jpg", got["shako"]["frameId"])
        self.assertEqual("owned", got["shako"]["kind"])
        self.assertEqual("PROVEN", got["tal"]["tier"])
        self.assertEqual("stash", got["tal"]["source"])
        self.assertNotEqual("owned", got["tal"].get("kind"), "a filing row was replaced by a new receipt")
        self.assertFalse(got["magefist"], "a name the batch did not carry was given an invented row")
        src = _src()
        for anchor in (
            "the name-fold did not reach storage",
            "put them back so a healthy reload re-runs the whole fold",
            "copy-count fold did not reach storage",
        ):
            at = src.find(anchor)
            self.assertGreaterEqual(at, 0, "the rollback this law watches is gone: %s" % anchor)
            window = src[max(0, at - 400):at + 80]
            self.assertIn("_ownedPutBack(", window, "this rollback does not go through the put-back door: %s" % anchor)
            self.assertNotIn("owned.add(", window, "this rollback still adds to owned bare: %s" % anchor)

    def test_the_fork_set_is_the_only_other_occurrence(self):
        """The fork set names the key as a bare double-quoted token among fifty others; it is the one place this census
        reads the key as neither code nor a list line, so it is pinned by its own shape."""
        s = _src()
        lp = re.search(r"window\._LP_FORKED = new Set\(\[(.*?)\]\)", s, re.S).group(1)
        self.assertIn('"d2r_owned"', lp)

    def test_the_unseed_undo_grows_owned_only_through_the_door(self):
        blk = _code_only(_between(_src(), UNSEED_FROM, UNSEED_TO))
        self.assertIn("window._ownedAdd(nm,", blk.replace(" ", ""), "the un-seed Undo grows d2r_owned with no receipt")

    def test_no_python_door_writes_owned_without_the_door(self):
        """control_app sends the board JS; any function that sends a setItem('d2r_owned') must also send _ownedAdd."""
        import ast
        bad = []
        for fn in sorted(os.listdir(HERE)):
            if not fn.endswith(".py") or fn.startswith("test_") or fn.startswith("."):
                continue
            try:
                with io.open(os.path.join(HERE, fn), encoding="utf-8") as fh:
                    tree = ast.parse(fh.read())
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                strs = "".join(n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str))
                if "setItem('d2r_owned'" in strs and "window._ownedAdd(" not in strs:
                    bad.append("%s:%s" % (fn, node.name))
        self.assertEqual([], bad, "a console door writes d2r_owned on the board with no receipt: %r" % bad)

    def test_no_vault_claim_is_decided_outside_the_route(self):
        """L1 — the bare predicate decides nothing on its own: every `_vaultMayClaim(` CALL in code sits inside
        window._vaultHoldingRoute, so a Chronicle-page row with a place on it cannot file through a sibling door."""
        s = _src()
        mask = code_mask(s)
        head = "  window._vaultHoldingRoute = function(loc, scene, name){\n"
        self.assertEqual(1, s.count(head))
        a = s.index(head)
        b = s.index("\n  };\n", a)
        calls = [m.start() for m in re.finditer(r"\b_vaultMayClaim\s*\(", s) if mask[m.start()]]
        self.assertTrue(calls, "BASELINE: the route itself must call the predicate, or this census measures nothing")
        outside = [s.count("\n", 0, c) + 1 for c in calls if not (a < c < b)]
        self.assertEqual([], outside, "these lines decide a vault claim on the bare predicate, not the route (L1): %r" % outside)


@unittest.skipIf(NODE is None, "node is absent — the owned door was not driven (a declared skip, never a pass)")
class TheDoorWritesAReceipt(unittest.TestCase):

    def test_a_receipt_names_who_when_and_the_picture(self):
        o = out()["receipt"]
        row = o["row"]
        self.assertIn("Grief", o["owned"])
        self.assertEqual("owned", row["kind"])
        self.assertEqual("aic-judge", row["source"])
        self.assertEqual("s_1", row["sessionId"])
        self.assertEqual("9_1790543904663", row["frameId"])
        self.assertEqual("9_1790543904663", row["looks"][0]["frame"])
        self.assertTrue(str(row["at"]).startswith("2026-09-2"), row["at"])
        self.assertEqual("stash", row["scene"])

    def test_a_filing_row_is_never_clobbered(self):
        o = out()["noClobber"]
        for k in ("one", "two"):
            row = o[k]
            self.assertEqual(("PROVEN", 12, 12, "uni-armor", "stash"),
                             (row.get("tier"), row.get("successes"), row.get("trials"), row.get("mule"), row.get("source")),
                             "%s: the receipt overwrote the richer filing row: %r" % (k, row))
            self.assertNotEqual("owned", row.get("kind"))
        self.assertEqual("kai-register", o["one"]["ownedBy"]["source"], "the filing did not note who first owned it")
        self.assertEqual("kai-register", o["two"]["ownedBy"]["source"], "a second add replaced the ownedBy note")

    def test_a_standing_receipt_only_grows_its_tally(self):
        row = out()["merge"]
        self.assertEqual(["f1", "f2"], [k["frame"] for k in row["looks"]], "a repeat look was counted twice or a new one lost")
        self.assertEqual(2, row["seen"])
        self.assertEqual("equipped", row["loc"])
        self.assertEqual("inventory", row["scene"], "a missing field was not filled from the next read")

    def test_no_source_means_no_row_and_the_item_still_lands(self):
        o = out()["noSource"]
        self.assertIn("Nagelring", o["owned"])
        self.assertEqual({}, o["prov"])
        self.assertFalse(o["r"]["prov"]["ok"])

    def test_an_unreadable_store_is_never_written_over(self):
        o = out()["unreadable"]
        self.assertEqual("{broken", o["raw"])
        self.assertIn("Nagelring", o["owned"])


@unittest.skipIf(NODE is None, "node is absent — the route was not driven")
class TheRouteFilesWhatHeHolds(unittest.TestCase):

    def test_the_route_table(self):
        """§28 + §31.2 (his 2026-09-28 rulings). ⚠ §31.2 SUPERSEDES v2346 / REG-426 for inventory LOOT: an item the
        reader placed in his inventory is 'carried' (owned right away, never filed); standing kit stays §29 ('kit'); a
        consumable is never owned; an open inventory PANEL with no per-name place waits (the ground is beside it)."""
        got = {(a, b, c): r for a, b, c, r, _w, _l in out()["routes"]}
        want = {("equipped", "inventory", None): "vault", ("stash", None, None): "vault", ("cube", None, None): "vault",
                ("mule", None, None): "vault", ("stash", "chronicle", None): "found-only", (None, "chronicle", None): "found-only",
                ("floor", None, None): "not-held", (None, "loot", None): "not-held", ("inventory", None, "Shako"): "carried",
                (None, "inventory", None): "wait", (None, None, None): "wait", (None, "stash", None): "wait",
                (None, "gameplay", None): "not-held", ("EQUIPPED", None, None): "vault",
                ("inventory", None, "Horadric Cube"): "kit", ("inventory", None, "Annihilus"): "kit",
                ("inventory", None, "Small Charm of Good Luck"): "kit", ("inventory", None, "Super Healing Potion"): "not-held",
                ("vendor", None, None): "not-held", (None, "trade", None): "not-held", ("inventory", None, None): "carried"}
        self.assertEqual(want, got)
        for a, b, c, r, why, _l in out()["routes"]:
            self.assertTrue(why, "route %r gave no reason" % ((a, b, c),))
        waits = [w for a, b, c, r, w, _l in out()["routes"] if r == "wait"]
        self.assertTrue(all("UNKNOWN" in w or "waits" in w for w in waits), waits)
        _k = lambda t: (str(t[0]), str(t[1]))  # noqa: E731
        leaves = sorted(((a, b) for a, b, c, r, _w, l in out()["routes"] if l), key=_k)
        self.assertEqual(sorted([("floor", None), (None, "loot"), ("vendor", None), (None, "trade")], key=_k), leaves,
                         "only the floor and a vendor / trade window are leave signals")
        carried_why = [w for a, b, c, r, w, _l in out()["routes"] if r == "carried"][0]
        self.assertIn("§31.2", carried_why)

    def test_a_worn_read_files_into_the_dock_with_its_receipt(self):
        o = out()["live"]
        self.assertEqual("vault", o["live"]["route"])
        self.assertIn("String of Ears", o["owned"])
        row = o["row"]
        self.assertEqual(("owned", "kai-register", "equipped", "inventory", "17_1790551926547", "s_2"),
                         (row["kind"], row["source"], row["loc"], row["scene"], row["frameId"], row["sessionId"]))
        self.assertEqual(1, len(o["reg"]), "the register was asked for something other than the worn read")

    def test_a_chronicle_page_a_floor_and_an_unknown_read_never_file(self):
        o = out()["live"]
        self.assertEqual("found-only", o["chron"]["route"])
        self.assertEqual("found-only", o["chronStash"]["route"], "a Chronicle-page read with a place on it filed")
        self.assertEqual("wait", o["unknown"]["route"])
        for nm in ("Hellfire Torch", "Arachnid Mesh", "Gore Rider"):
            self.assertNotIn(nm, o["owned"])


@unittest.skipIf(NODE is None, "node is absent — the held sighting was not driven")
class TheHeldSightingRoutesWhole(unittest.TestCase):
    """⚠ H1 (review of 77d8d8b5, reproduced): a Chronicle-page read followed by a WORN read compiled to {loc equipped,
    scene chronicle, frame = the chronicle frame} — three facts from two frames — and the route answered found-only, so
    the worn item never filed. The register now keeps one tuple per sighting and the best HOLDING sighting beside it;
    the board routes on the held one and cites ITS frame."""

    def test_the_register_keeps_one_tuple_per_sighting_and_the_held_one_beside_it(self):
        reg = {r["name"]: r for r in out()["_register"]}
        soe = reg["String of Ears"]
        self.assertEqual((1790551000000, "20_1790551000000", None, "chronicle"),
                         (soe["firstSeenTs"], soe["frameId"], soe["loc"], soe["scene"]),
                         "the first sighting's tuple was mixed with another frame's facts: %r" % soe)
        self.assertEqual(("equipped", "inventory", "17_1790551926547", 1790551926547),
                         (soe.get("heldLoc"), soe.get("heldScene"), soe.get("heldFrame"), soe.get("heldTs")),
                         "the worn sighting was not kept whole beside the first: %r" % soe)
        self.assertNotIn("heldLoc", reg["Magefist"], "a Chronicle page with a place on it became a holding sighting")
        wt = reg["War Traveler"]
        self.assertEqual((1790550000000, "19_1790550000000", None, "chronicle"),
                         (wt["firstSeenTs"], wt["frameId"], wt["loc"], wt["scene"]),
                         "an EARLIER sighting arriving later replaced the frame and scene but kept another frame's place: %r" % wt)
        self.assertEqual(("equipped", "18_1790552000000"), (wt.get("heldLoc"), wt.get("heldFrame")))
        self.assertNotIn("_heldRank", soe, "a compile-time ranking leaked into the register row")

    def test_the_board_routes_on_the_held_sighting_and_cites_its_frame(self):
        by = {r["name"]: r for r in out()["register"]}
        self.assertEqual("vault", by["String of Ears"]["route"], "BASELINE: the worn read must file, or this proves nothing")
        self.assertEqual("17_1790551926547", by["String of Ears"]["frame"])
        row = by["String of Ears"]["row"]
        self.assertEqual(("equipped", "inventory", "17_1790551926547"), (row["loc"], row["scene"], row["frameId"]),
                         "the receipt cites a frame other than the worn one: %r" % row)
        self.assertEqual("found-only", by["Magefist"]["route"])
        self.assertIsNone(by["Magefist"]["row"])
        self.assertEqual(("vault", "18_1790552000000"), (by["War Traveler"]["route"], by["War Traveler"]["frame"]))

    def test_a_board_row_carrying_both_routes_on_the_held_one(self):
        o = out()["held"]
        self.assertEqual("vault", o["r"]["route"])
        self.assertEqual("17_1790551926547", o["row"]["frameId"])
        self.assertIn("String of Ears", o["owned"])

    def test_the_console_hands_the_held_sighting_to_the_board(self):
        """The join: the propose builder in control_app puts the held fields on the item it sends."""
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        anchor = '"heldFrame": x.get("heldFrame"), "heldTs": x.get("heldTs")}'
        self.assertEqual(1, src.count(anchor), "the console no longer hands the held sighting to kaiChroniclePropose")
        with io.open(BIBLE, encoding="utf-8") as fh:
            s = fh.read()
        base = _code_only(_between(s, "        var base = {\n          name: nm, firstSeenTs: it.firstSeenTs || 0,", "        var why = window.kaiChronicleSettledWhy(nm);"))
        self.assertIn("heldLoc:it.heldLoc", base.replace(" ", ""), "kaiChroniclePropose drops the held sighting at its whitelist")


@unittest.skipIf(NODE is None, "node is absent — the carried ruling was not driven")
class CarriedLootIsOwnedRightAway(unittest.TestCase):
    """§31.2 (his ruling, 2026-09-28): "Owned right away" + "maybe needs a logic between them both"."""

    def test_an_inventory_read_is_owned_carried_and_never_filed(self):
        o = out()["carried"]
        self.assertEqual("carried", o["r"]["route"])
        self.assertTrue(o["row"]["carried"])
        self.assertEqual(("KonyoSorc", "inventory", "30_1"), (o["row"]["character"], o["row"]["loc"], o["row"]["frameId"]))
        self.assertEqual(["Shako|KonyoSorc"], o["names"], "the carried item is not on that character's strip")
        self.assertTrue(o["reg"][0]["carried"], "the register was not told the read is carried")
        self.assertIn("carried by KonyoSorc", o["words"])
        self.assertIn("CARRIED", o["evSeen"])

    def test_it_lands_when_next_seen_in_a_stash_tab(self):
        o = out()["carried"]
        self.assertFalse(o["landed"]["carried"], "a stash look did not land the carried item")
        self.assertEqual(("stash", "31_1"), (o["landed"]["landed"]["loc"], o["landed"]["landed"]["frame"]))
        self.assertEqual([], o["after"], "a landed item is still on the carried strip")
        self.assertIn("LANDED", o["landedEv"] or "")

    def test_it_leaves_only_on_a_real_signal_with_its_frame(self):
        o = out()["leave"]
        self.assertTrue(o["stillOwned"], "a floor look with NO frame un-owned a carried item — no proof, no leave")
        self.assertIn("no proof", o["noProof"]["why"])
        self.assertEqual("left", o["left"]["route"])
        self.assertNotIn("Shako", o["owned"])
        rm = [r for r in o["removed"] if r["lane"] == "carried-left"]
        self.assertEqual(["32_1", "36_1"], [r["proof"]["frame"] for r in rm], "a leave went without its frame as proof")
        self.assertEqual("left", o["vendor"]["route"], "a vendor window did not take a carried item out")
        self.assertEqual("not-held", o["notCarried"]["route"])
        self.assertIn("Nagelring", o["owned"], "a stash-held item was un-owned by a floor look of the same name")

    def test_an_open_inventory_panel_is_still_not_a_place(self):
        """§31.2 makes inventory LOOT carried PER NAME; the timeline's open inventory panel is not a place (the ground
        is visible beside it), so reel_segments still grants no vault lane — and says why in §31.2's words, never the
        superseded v2346 ones. (test_control's v2346 pin holds the same sentence.)"""
        import reel_segments as rs
        rows = [{"lane": "deep", "sessionId": "s1", "captureTs": 1000, "scene": "inventory"},
                {"lane": "deep", "sessionId": "s1", "captureTs": 2000, "scene": "inventory"}]
        lane, why = rs.lane_at(rs.segments(rows), "s1", 1500)
        self.assertIsNone(lane)
        self.assertIn("§31.2", why)
        self.assertIn("per-name place", why)
        self.assertNotIn("holding, not owning", why)

    def test_absence_asks_after_a_few_sessions_and_never_un_owns(self):
        o = out()["stale"]
        self.assertEqual((2, False), (o["st2"]["sessionsSince"], o["st2"]["stale"]))
        self.assertEqual(2, o["stL"]["sessionsSince"], "a session read on LADDER counted against a main-world item")
        self.assertEqual((3, True), (o["st3"]["sessionsSince"], o["st3"]["stale"]))
        self.assertIn("still have it?", o["st3"]["say"])
        self.assertIn("last seen", o["st3"]["say"])
        self.assertTrue(o["owned"], "absence un-owned a carried item")
        self.assertIsNone(o["stU"]["sessionsSince"], "an unreadable ledger read as a count")
        self.assertIn("UNKNOWN", o["stU"]["say"])


@unittest.skipIf(NODE is None, "node is absent — the real register was not driven")
class TheRegisterNeverFilesCarriedLoot(unittest.TestCase):

    def test_the_shipped_register_owns_a_carried_read_and_files_a_stash_read(self):
        s = _src()
        o = _node(REGISTER % {"lanes": _lanes(s), "furn": _between(s, FURN_FROM, FURN_TO), "region": owned_prov_region(s),
                              "rule": _intake_rule(s),
                              "reg": _between(s, RESOLVER_FROM, REG_FROM) + _between(s, REG_FROM, REG_TO)}, "register")
        self.assertEqual(o["once"].get("refused"), "one-session", "a one-session read was registered (#202): %r" % o["once"])
        self.assertEqual("carried", o["carried"].get("refused"), o["carried"])
        self.assertEqual([], o["filedAfterCarried"], "the register FILED carried loot to a mule")
        self.assertTrue(o["carriedRow"]["carried"])
        self.assertEqual("KonyoSorc", o["carriedRow"]["character"])
        self.assertEqual([{"name": "Nagelring", "mule": "uni-armor"}], o["filed"],
                         "BASELINE: a stash read must still reach the filing door, or this proves nothing")
        self.assertEqual(["Nagelring", "Shako"], o["owned"])


@unittest.skipIf(NODE is None, "node is absent — the backfill was not driven")
class TheBackfill(unittest.TestCase):

    def test_owned_names_gain_their_receipts_and_the_held_reads_are_filed(self):
        o = out()["backfill"]
        self.assertTrue(o["b1"]["ran"], o["b1"])
        rc = o["b1"]["receipt"]
        self.assertEqual(["Grief", "Plague"], sorted(rc["wrote"]))
        self.assertEqual(["String of Ears", "Tal Rasha's Horadric Crest", "Compendium"], [f["name"] for f in rc["filed"]])
        self.assertEqual(["vault", "carried", "vault"], [f["route"] for f in rc["filed"]])
        g = o["prov"]["Grief"]
        self.assertEqual(("owned", "aic-judge", "9_1790543904663", "s_1790543358478_35359", "backfill"),
                         (g["kind"], g["source"], g["frameId"], g["sessionId"], g["by"]))
        self.assertEqual("11_1790543968521", o["prov"]["Plague"]["frameId"])
        soe = o["prov"]["String of Ears"]
        self.assertEqual(("equipped", "17_1790551926547", "backfill"), (soe["loc"], soe["frameId"], soe["by"]))
        self.assertIn("String of Ears", o["owned"])
        self.assertTrue(o["prov"]["Tal Rasha's Horadric Crest"]["carried"], "§31.2: inventory loot was not filed as carried")

    def test_nothing_else_files(self):
        o = out()["backfill"]
        never = CHRONICLE_PAGE + ["Arachnid Mesh", "Shako", "Gore Rider", "Skin of the Vipermagi", "Harlequin Crest",
                                  "Nosferatu's Coil"]
        for nm in never:
            self.assertNotIn(nm, o["owned"], "%s was filed by the backfill" % nm)
            self.assertNotIn(nm, o["prov"])
        rc = o["b1"]["receipt"]
        self.assertEqual(8, rc["routes"].get("found-only"), rc["routes"])
        self.assertEqual(1, rc["routes"].get("wait"), rc["routes"])
        self.assertEqual({"dismissed": 1, "pending": 1, "another-world": 1}, rc["skipped"])
        self.assertEqual("main", rc["world"])

    def test_it_runs_once_and_says_so(self):
        o = out()["backfill"]
        self.assertFalse(o["b2"]["ran"])
        self.assertTrue(o["b2"]["already"])
        self.assertTrue(o["idempotent"], "a second backfill changed the store")

    def test_the_read_keeps_its_own_ledger_row_and_the_verdict_is_a_separate_field(self):
        """L2 — the register's own row patch is suppressed during the replay; the verdict lands beside the row's
        own fields, never over its status or source."""
        o = out()["backfill"]
        self.assertFalse([r for r in o["records"] if r.get("name") in ("String of Ears", "Compendium")],
                         "the register's ledger patch still landed over the read's own row: %r" % o["records"][:3])
        row = o["soeRow"]
        self.assertEqual(("in-chronicle", "kai-register", "vault"), (row["status"], row["source"], row["vaultRoute"]))
        self.assertTrue(row.get("vaultBackfillTs"))

    def test_the_side_writes_are_journaled(self):
        o = out()["backfill"]
        comp = [f for f in o["b1"]["receipt"]["filed"] if f["name"] == "Compendium"][0]
        self.assertEqual((True, None, "bases"), (comp["side"]["tvxMinted"], comp["side"]["assignBefore"], comp["side"]["assignAfter"]))
        self.assertIn("Compendium", o["tvx"], "BASELINE: the stub must have minted the side write, or this proves nothing")
        self.assertEqual("bases", o["assign"].get("Compendium"))
        self.assertIsNone(comp["side"]["logPrev"]["vaultRoute"])

    def test_the_undo_takes_back_exactly_what_it_did_side_writes_included(self):
        o = out()["undo"]
        self.assertTrue(o["u1"]["ok"], o["u1"])
        self.assertEqual(["Compendium", "String of Ears", "Tal Rasha's Horadric Crest"], sorted(o["u1"]["removed"]))
        self.assertEqual(["Grief", "Plague"], sorted(o["u1"]["dropped"]))
        self.assertEqual(["Grief", "Plague"], o["owned"], "the undo removed a name it never filed")
        self.assertEqual({}, o["prov"])
        self.assertEqual("backfill-undo", [r for r in o["removed"] if r["lane"] == "backfill-undo"][0]["lane"])
        self.assertFalse(o["u2"]["ok"], "a second undo acted again")
        self.assertNotIn("Compendium", o["tvx"], "the TV stub the backfill minted survived its undo")
        self.assertNotIn("Compendium", o["extra"], "the EXTRA_ITEMS entry the backfill minted survived its undo")
        self.assertNotIn("Compendium", o["assign"], "the filing the backfill minted survived its undo")
        for k in ("vaultRoute", "vaultWhy", "vaultBackfillTs"):
            self.assertNotIn(k, o["soeRow"], "the ledger row kept the backfill's %s after the undo" % k)
        self.assertEqual("in-chronicle", o["soeRow"]["status"])


@unittest.skipIf(NODE is None, "node is absent — the per-world backfill was not driven")
class TheBackfillStaysInItsWorld(unittest.TestCase):
    """⚠ M3 (review of 77d8d8b5, reproduced)."""

    def test_on_ladder_only_a_ladder_read_replays(self):
        o = out()["ladder"]
        rc = o["b"]["receipt"]
        self.assertEqual("ladder", rc["world"])
        self.assertEqual([], rc["wrote"], "main's reads wrote receipts into ladder's vault")
        self.assertEqual(["Nosferatu's Coil"], [f["name"] for f in rc["filed"]])
        self.assertEqual(["Grief", "Nosferatu's Coil", "Plague"], o["owned"])
        self.assertGreater(rc["skipped"].get("another-world", 0), 10)

    def test_the_stamp_forks_with_the_stores_it_describes(self):
        s = _src()
        o = _node(ROUTER % {"router": _between(s, ROUTER_FROM, ROUTER_TO, include_b=True)}, "router")
        self.assertEqual(o["owned"].replace("d2r_owned", ""), o["stamp"].replace("d2r_ownedProvBackfill", ""),
                         "the backfill stamp and d2r_owned resolve to different worlds: %r" % o)
        self.assertNotEqual("d2r_ownedProvBackfill", o["stamp"], "on ladder the stamp is still BARE — shared with main")
        self.assertEqual("d2r_ownedProvBackfill", o["mainStamp"], "his main world's existing stamp moved")

    def test_his_removals_are_never_replayed(self):
        o = out()["removals"]
        rc = o["b"]["receipt"]
        self.assertNotIn("String of Ears", o["owned"], "a name he REMOVED came back through the backfill")
        self.assertNotIn("String of Ears", [f["name"] for f in rc["filed"]])
        self.assertEqual(1, rc["skipped"].get("removed-by-him"))
        self.assertNotIn("Plague", o["prov"], "an owned name removed AFTER its row was read got a receipt from that row")
        self.assertEqual(1, rc["skipped"].get("owned-again-since-a-removal"))
        self.assertIn("Grief", o["prov"], "BASELINE: an owned name nobody removed must still gain its receipt")

    def test_an_unreadable_removal_journal_backfills_nothing(self):
        o = out()["removalsUnread"]
        self.assertFalse(o["b"]["ran"])
        self.assertIn("UNKNOWN", o["b"]["why"])
        self.assertEqual({}, o["prov"])


@unittest.skipIf(NODE is None, "node is absent — the restore doors were not driven")
class EveryRestoreWritesItsReceipt(unittest.TestCase):
    """⚠ M4 (review of 77d8d8b5, reproduced): two doors wrote d2r_owned and no provenance."""

    def test_the_unseed_undo_writes_its_receipts(self):
        s = _src()
        o = _node(UNSEED % {"lanes": _lanes(s), "region": owned_prov_region(s), "unseed": _between(s, UNSEED_FROM, UNSEED_TO)},
                  "unseed")
        self.assertEqual(["Grief", "Nagelring", "Shako"], sorted(o["owned"]))
        for nm in ("Shako", "Nagelring"):
            row = o["prov"].get(nm)
            self.assertTrue(row, "%s came back with no receipt" % nm)
            self.assertEqual(("owned", "ledger-restore", "the un-seed undo", 1790000000000),
                             (row["kind"], row["source"], row["by"], row["ts"]))
        self.assertEqual("x", o["prov"]["Grief"]["by"], "a name that was already owned had its receipt replaced")

    def test_owned_restore_writes_its_receipts(self):
        import control_app as ca
        sent = []
        saved = {k: getattr(ca, k, None) for k in ("_ejs", "board_identity_drift")}
        g = ca.__dict__
        saved_g = {k: g.get(k) for k in ("_BOARD_WIN", "_WINDOW_LIVE")}
        try:
            ca._ejs = lambda w, js, timeout=None: sent.append(js) or json.dumps({"ok": True})
            ca.board_identity_drift = lambda: {"state": "ok"}
            g["_BOARD_WIN"], g["_WINDOW_LIVE"] = object(), True
            ca.owned_restore(["Grief", "Shako", "Nagelring"], confirm=True, snapshot_ts=1790000000000)
        finally:
            for k, v in saved.items():
                setattr(ca, k, v)
            for k, v in saved_g.items():
                g[k] = v
        self.assertEqual(1, len(sent), "owned_restore sent the board nothing")
        s = _src()
        o = _node(RESTORE % {"lanes": _lanes(s), "region": owned_prov_region(s), "js": sent[0]}, "restore")
        self.assertTrue(o["r"]["ok"], o["r"])
        self.assertEqual(2, o["r"]["receipts"], o["r"])
        for nm in ("Shako", "Nagelring"):
            row = o["prov"].get(nm)
            self.assertTrue(row, "%s was restored with no receipt" % nm)
            self.assertEqual(("ledger-restore", "owned_restore", 1790000000000), (row["source"], row["by"], row["ts"]))
        self.assertEqual("x", o["prov"]["Grief"]["by"], "a name that was already owned had its receipt replaced")


@unittest.skipIf(NODE is None, "node is absent — the receipt/witness line was not driven")
class AReceiptIsNeverAWitness(unittest.TestCase):

    def test_the_sorter_files_nothing_on_a_receipt(self):
        calls = out()["sorter"]
        self.assertEqual(["Lost Home", "Two Stash Looks"], [c["name"] for c in calls],
                         "the sorter handed a bare receipt to the mule door, or did not hand the gathered one")
        self.assertTrue(calls[0]["witnessed"])
        self.assertEqual("receipt", calls[1]["gathered"], "the two-session receipt reached the door on something other than "
                                                          "its gathered stash looks: %r" % calls[1])

    def test_the_prune_keeps_no_filing_on_a_receipt(self):
        a = out()["w6"]
        self.assertNotIn("Receipt Only", a, "a filing stood on a receipt")
        self.assertIn("Stash Witness", a)


@unittest.skipIf(NODE is None, "node is absent — the evidence panel was not driven")
class TheEvidenceIsVisible(unittest.TestCase):

    def test_the_panel_says_who_when_session_frame_and_tally(self):
        e = out()["evidence"]
        g = e["grief"]
        self.assertTrue(g["has"])
        self.assertIn("AI item checker", g["who"])
        self.assertEqual(("s_1790543358478_35359", "9_1790543904663"), (g["session"], g["frame"]))
        self.assertEqual("1 look", g["tallySay"])
        self.assertTrue(g["when"] and "2026" in g["when"], g["when"])
        for bit in ("Filed by", "9_1790543904663", "s_1790543358478_35359", "1 look", "AI item checker"):
            self.assertIn(bit, e["griefHtml"])
        self.assertEqual("worn (equipped) · screen: inventory", e["soe"]["seen"])
        self.assertIn('class="vc-ev"', e["chip"])
        self.assertIn("window._vaultEvidenceOpen(", e["chip"])

    def test_no_provenance_is_said_in_words(self):
        e = out()["evidence"]
        self.assertFalse(e["none"]["has"])
        self.assertIn("No provenance", e["noneHtml"])
        self.assertIn("UNKNOWN", e["noneHtml"])
        self.assertIn("ev-none", e["chipNone"])

    def test_a_picture_is_shown_only_when_it_loads(self):
        p = out()["pictures"]
        self.assertEqual("present", p["present"]["state"])
        self.assertIn("<img", p["presentHtml"])
        self.assertEqual("gone", p["gone"]["state"])
        self.assertIn("picture not on this machine", p["gone"]["say"])
        self.assertIn("disk floor", p["gone"]["say"])
        self.assertEqual("unknown", p["silent"]["state"])
        self.assertIn("UNKNOWN", p["silent"]["say"])
        self.assertEqual("none", p["none"]["state"])
        for k in ("goneHtml", "silentHtml"):
            self.assertNotIn("<img", p[k], "%s drew an image for a picture that did not load" % k)
            self.assertIn("picture not on this machine", p[k])
        asked = [u for u in p["fetches"] if "picture_status?ids=17_1790551926547" in u]
        self.assertTrue(asked, "the console was never asked why the picture is gone")
        # #41 rank 18 sibling (REG-1552) — asked of the console that SERVED the board (:17999 here), never his :17772 by name
        for u in asked:
            self.assertTrue(u.startswith("http://127.0.0.1:17999/api/picture_status?ids="),
                            "the ask did not go to the console that served the board: %s" % u)
            self.assertNotIn("17772", u, "the board asked his live console whatever console served it: %s" % u)
        # a board nobody served asks nobody and says so
        self.assertEqual("unknown", p["noOrigin"]["state"], p["noOrigin"])
        self.assertIn("nobody was asked", p["noOrigin"]["say"])
        self.assertEqual(0, p["noOriginFetches"], "a board nobody served still asked a console")


class TheJoins(unittest.TestCase):
    """Structure, read as CODE (comments stripped by the same scanner) — the doors that route a live read."""

    def _block(self, s, head):
        assert s.count(head) == 1, "anchor %r matched %d times" % (head[:50], s.count(head))
        i = s.index(head) + len(head)
        depth, j = 1, i
        while j < len(s) and depth:
            depth += {"{": 1, "}": -1}.get(s[j], 0)
            j += 1
        blk = s[i:j]
        m = code_mask(blk.join(["<script>", "</script>"]), keep_strings=True)
        return "".join(ch for k, ch in enumerate(blk) if m[k + len("<script>")] or ch == "\n")

    def test_the_settled_branch_asks_the_route_before_it_returns(self):
        blk = self._block(_src(), "var why = window.kaiChronicleSettledWhy(nm);\n        if (why){")
        self.assertIn("window._liveReadRoute(base)", blk, "the settled branch never asks the route")
        self.assertLess(blk.index("window._liveReadRoute(base)"), blk.index("return;"), "the route is asked after the branch returns")
        self.assertIn("vaultRoute:_svr.route", blk.replace(" ", ""))

    def test_the_judge_keep_writes_its_receipt_through_the_door(self):
        blk = self._block(_src(), "          if (_kwRW){")
        self.assertIn("window._ownedAdd(nm,{source:'aic-judge'", blk.replace(" ", "").replace("\n", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "#41 rank 18 sibling (REG-1552) - the picture status is asked of :17772 by name again, whatever console served the board",
        "file": "bible.html",
        "find": "      var url = origin + '/api/picture_status?ids=' + encodeURIComponent(id);\n",
        "replace": "      var url = 'http://127.0.0.1:17772/api/picture_status?ids=' + encodeURIComponent(id);\n",
        "matches": 1,
    },
    {
        "why": "#41 rank 18 sibling (REG-1552) - a board nobody served asks his console anyway (the origin guard dropped)",
        "file": "bible.html",
        "find": "        origin = _consoleOrigin();\n        if (!origin) return end({ state: 'unknown', frame: id,",
        "replace": "        origin = _consoleOrigin() || 'http://127.0.0.1:17772';\n        if (false) return end({ state: 'unknown', frame: id,",
        "matches": 1,
    },
    {
        "why": "a confirm rollback adds to owned bare again and the receipt the removal carried stays dropped",
        "file": "bible.html",
        "find": "        window._ownedAdd(L, (row && typeof row === 'object' && !Array.isArray(row)) ? { restoreRow: row } : null);\n",
        "replace": "        try { owned.add(L); } catch (e3) {}\n",
        "matches": 1,
    },
    {
        "why": "a door adds to owned bare again — no receipt, the Grief/Plague defect",
        "file": "bible.html",
        "find": "    else window._ownedAdd(name, (prov && prov.source) ? prov : { source: 'hand', by: 'toggleOwned', where: 'the item card tick' });\n",
        "replace": "    else owned.add(name);\n",
        "matches": 1,
    },
    {
        "why": "the receipt clobbers a filing row (the §24 rebuild's tier/successes/trials are lost)",
        "file": "bible.html",
        "find": "    if (cur && typeof cur === 'object' && !Array.isArray(cur)){\n      if (cur.kind !== 'owned'){\n",
        "replace": "    if (cur && typeof cur === 'object' && !Array.isArray(cur) && cur.kind === 'owned'){\n      if (false){\n",
        "matches": 1,
    },
    {
        "why": "a Chronicle-page read files into the vault again (§28)",
        "file": "bible.html",
        "find": "    if (s === 'chronicle' || l === 'chronicle')\n",
        "replace": "    if (false)\n",
        "matches": 1,
    },
    {
        "why": "an UNKNOWN place files instead of waiting",
        "file": "bible.html",
        "find": "    if (!s) return { route: 'wait', why: 'where it was seen is UNKNOWN",
        "replace": "    if (!s) return { route: 'vault', why: 'where it was seen is UNKNOWN",
        "matches": 1,
    },
    {
        "why": "the settled branch stops asking the route — String of Ears reaches the found list only",
        "file": "bible.html",
        "find": "            try { _svr = window._liveReadRoute(base); } catch(eSR){ _svr = null; }\n",
        "replace": "            _svr = null;\n",
        "matches": 1,
    },
    {
        "why": "the backfill runs on every load (not one-time)",
        "file": "bible.html",
        "find": "    if (done && done.ver >= _BF_VER && !opts.force) return { ran: false, already: true, receipt: done };\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "the sorter hands an owned receipt to the mule door as a witness",
        "file": "bible.html",
        "find": "        if (!_wR) return;\n",
        "replace": "        _wR = _wR || _provAsWitness(_row) || { lane: 'receipt', sessions: [] };\n",
        "matches": 1,
    },
    {
        "why": "a picture that did not load is drawn as a broken image",
        "file": "bible.html",
        "find": "    if (pic.state === 'present' && pic.src){\n",
        "replace": "    if (pic.state !== 'none'){\n",
        "matches": 1,
    },
    {
        "why": "the backfill files a read that is still waiting for his ruling",
        "file": "bible.html",
        "find": "  var _BF_RULED = { 'dismissed': 1, 'blocked-unfound': 1, 'undone': 1, 'pending': 1 };\n",
        "replace": "  var _BF_RULED = { 'dismissed': 1, 'blocked-unfound': 1, 'undone': 1 };\n",
        "matches": 1,
    },
    # ── the review of 77d8d8b5 ──
    {
        "why": "H1: the register stops keeping the holding sighting — a Chronicle page read first buries the worn read",
        "file": "control_app.py",
        "find": "        if _hr and (_hr > cur.get(\"_heldRank\", 0)\n",
        "replace": "        if False and (_hr > cur.get(\"_heldRank\", 0)\n",
        "matches": 1,
    },
    {
        "why": "H1: the register mixes a place from one frame with the scene and frame of another again",
        "file": "control_app.py",
        "find": "            cur[\"frameId\"] = frame_id or \"\"\n            cur[\"loc\"] = loc\n            cur[\"scene\"] = scene or None\n",
        "replace": "            cur[\"frameId\"] = frame_id or cur[\"frameId\"]\n            if loc is not None:\n                cur[\"loc\"] = loc\n            if scene:\n                cur[\"scene\"] = scene\n",
        "matches": 1,
    },
    {
        "why": "H1: a missing place is filled from ANOTHER sighting again — the cross-fill that minted {equipped, chronicle, the chronicle frame}",
        "file": "control_app.py",
        "find": "        if tier and _KAI_TIER_RANK.get(tier, 0) > _KAI_TIER_RANK.get(cur.get(\"tier\") or \"\", 0):\n",
        "replace": "        if loc is not None and cur.get(\"loc\") is None:\n            cur[\"loc\"] = loc\n        if tier and _KAI_TIER_RANK.get(tier, 0) > _KAI_TIER_RANK.get(cur.get(\"tier\") or \"\", 0):\n",
        "matches": 1,
    },
    {
        "why": "H1: the board ignores the held sighting and routes on the first one (found-only for a worn item)",
        "file": "bible.html",
        "find": "    if (row.heldLoc) return { loc: row.heldLoc,",
        "replace": "    if (false) return { loc: row.heldLoc,",
        "matches": 1,
    },
    {
        "why": "§31.2: inventory loot is 'held' and never owned again (the superseded v2346 rule)",
        "file": "bible.html",
        "find": "        return { route: 'carried', why: 'seen in your inventory — §31.2",
        "replace": "        return { route: 'held', why: 'seen in your inventory — §31.2",
        "matches": 1,
    },
    {
        "why": "§31.2: the register files carried loot to a mule",
        "file": "bible.html",
        "find": "      if (!muleId && _w0.carried === true){\n",
        "replace": "      if (false){\n",
        "matches": 1,
    },
    {
        "why": "§31.2: carried loot never lands — a stash look leaves it on the carried strip",
        "file": "bible.html",
        "find": "      if (cur.carried === true && fresh.carried !== true && _landsCarried(fresh.loc)){\n",
        "replace": "      if (false){\n",
        "matches": 1,
    },
    {
        "why": "§31.2: a floor or vendor look never takes a carried item out",
        "file": "bible.html",
        "find": "    if (v.leave){\n      var lv = null;\n",
        "replace": "    if (false){\n      var lv = null;\n",
        "matches": 1,
    },
    {
        "why": "§31.2: a carried item leaves on a floor look with no frame — no proof",
        "file": "bible.html",
        "find": "    if (!fr) return { left: false, frame: null,",
        "replace": "    if (false) return { left: false, frame: null,",
        "matches": 1,
    },
    {
        "why": "§31.2: 'still have it?' never asks, however many sessions pass",
        "file": "bible.html",
        "find": "    var n = Object.keys(since).length, stale = n >= CARRIED_STALE_SESSIONS;\n",
        "replace": "    var n = Object.keys(since).length, stale = false;\n",
        "matches": 1,
    },
    {
        "why": "§31.2: the timeline's refusal for an open inventory says the superseded v2346 words again",
        "file": "reel_segments.py",
        "find": "§31.2: loot in the inventory's free space \"\n",
        "replace": "that is holding, not owning; loot in the free space \"\n",
        "matches": 1,
    },
    {
        "why": "M3: the backfill replays main's reads into ladder's vault",
        "file": "bible.html",
        "find": "      if (!_rowInWorld(r)){ _skip('another-world'); return; }\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "M3: the backfill stamp is bare again — one world's run silences every other world",
        "file": "bible.html",
        "find": "  \"d2r_ownedProvBackfill\",\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "M3: a name he removed comes back through the backfill",
        "file": "bible.html",
        "find": "      if (_rmAt[k]){ _skip('removed-by-him'); return; }\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "L2: the register's own ledger patch lands over the read's row during the backfill",
        "file": "bible.html",
        "find": "      window.kaiChronicleRecord = function(){ return null; };      /* L2",
        "replace": "      /* L2",
        "matches": 1,
    },
    {
        "why": "L2: the undo leaves the TV stub the backfill minted",
        "file": "bible.html",
        "find": "      if (sd.tvxMinted){ _bfTvxForget(nm);",
        "replace": "      if (false){ _bfTvxForget(nm);",
        "matches": 1,
    },
    {
        "why": "L1: a sibling door decides a vault claim on the bare predicate again",
        "file": "bible.html",
        "find": "      var _mayVault = (typeof window._vaultHoldingRoute === 'function')\n        && window._vaultHoldingRoute((row && row.loc) || null, (row && row.scene) || null, n).route === 'vault';\n",
        "replace": "      var _mayVault = (typeof window._vaultMayClaim === 'function')\n        && window._vaultMayClaim((row && row.loc) || '');\n",
        "matches": 1,
    },
    {
        "why": "M4: the un-seed Undo writes owned names with no receipt",
        "file": "bible.html",
        "find": "              if (typeof window._ownedAdd === 'function') _grow.forEach(function(nm){\n",
        "replace": "              if (false) _grow.forEach(function(nm){\n",
        "matches": 1,
    },
    {
        "why": "M4: a store write grows d2r_owned outside the door",
        "file": "bible.html",
        "find": "  LS.setItem('d2r_owned', JSON.stringify([...owned]));\n",
        "replace": "  LS.setItem('d2r_owned', JSON.stringify([...owned].concat(window.__extraOwned || [])));\n",
        "matches": 1,
    },
    {
        "why": "M4: owned_restore writes d2r_owned with no receipt",
        "file": "control_app.py",
        "find": "          \"if(typeof window._ownedAdd==='function'){for(var k=0;k<added.length;k++){\"\n",
        "replace": "          \"if(false){for(var k=0;k<added.length;k++){\"\n",
        "matches": 1,
    },
]
