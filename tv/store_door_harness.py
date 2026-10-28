#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""THE STORE DOOR'S NODE STAND-IN — the pieces of bible.html the store laws drive, cut by their own anchors.

#152 items 2-3 and #153 item 11 (REG-2410..REG-2413) put three things into the page: the quarantine at the one storage
door (window.LSR), the shape-aware boot reader (_storeRead) with its notice, and the tab sync that merges another tab's
write. Eight laws drive them, and they share this cut so each law asks the SHIPPED code, never a copy of it:

    test_a_store_that_will_not_read_is_kept_aside          the door, the boot readers, persist(), the notice, restore
    test_a_wrong_shaped_mule_store_never_stops_the_vault   the vault module's head, the hold and every door it holds
    test_a_corrupt_records_store_is_said_and_kept          the records store's quarantine, its undo, the task list
    test_another_tabs_write_is_merged_not_clobbered        the storage listener and the merge
    test_a_store_another_tab_removed_reads_as_its_default  a removal merged as the store's absent value (REG-2414)
    test_a_witness_store_that_will_not_read_holds_the_vault  d2r_vaultProv: vault_page(), the whole filing door (REG-2415)
    test_his_hand_spots_that_will_not_read_are_kept_aside  d2r_mulePos and the mule window's spot doors (REG-2416)
    test_what_a_mule_wears_that_will_not_read_is_kept_aside  d2r_muleEquip and its one writer (REG-2417)

`page(body, seed)` builds one node program: a localStorage stand-in (RAW) seeded with `seed`, the forked-name sets and
window.LSR exactly as bible.html declares them (cut by cb_node_harness._stage), then whatever pieces the caller adds,
then `body`; it returns the JSON the body put in OUT. The program goes to node on stdin, never on argv. A body that
waits on a promise sets window.__ASYNC and writes OUT itself (`done()` does both halves).

⚠ NODE IS `shutil.which("node")`, the same question heart2's PROOF_NEEDS_HOST probe asks, so a PC without node files
these proofs ELSEWHERE rather than BLIND. A node that is present and fails is an AssertionError, never a skip: only an
absent node may skip (test_the_node_venue_is_not_silently_absent, REG-1900).
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import cb_node_harness as _cb  # noqa: E402  the forked-name sets and LSR, cut once for every node harness

NODE = shutil.which("node")
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")

#: the vault module's head: RK/AK, the default roster, the mule store guard, the hold, the migrations
VAULT_HEAD_A = "  var RK='d2r_muleRoster', AK='d2r_muleAssign';"
VAULT_HEAD_B = "  var selectedChip = null;"


_SRC = {}


def src():
    """bible.html, read once per process for as long as its bytes do not change (a proof tampers between runs)."""
    st = os.stat(BIBLE)
    k = (st.st_mtime_ns, st.st_size)
    if _SRC.get("k") != k:
        with io.open(BIBLE, encoding="utf-8") as fh:
            _SRC["s"] = fh.read()
        _SRC["k"] = k
    return _SRC["s"]


def between(s, a, b, keep_b=True):
    """s from anchor a to the first b after it (b included unless keep_b is False). a must be unique."""
    n = s.count(a)
    if n != 1:
        raise AssertionError("the cut start %r matched %d times - the anchor moved" % (a[:70], n))
    i = s.index(a)
    j = s.find(b, i + len(a))
    if j < 0:
        raise AssertionError("the cut end %r was not found after %r" % (b[:70], a[:50]))
    return s[i:j + (len(b) if keep_b else 0)]


def fn(s, name):
    """`[async ]function NAME(...){...}` - the first declaration, brace-matched. -> str"""
    at = s.find("function %s(" % name)          # the literal first: a regex over 8.6 MB costs ~0.1 s a call
    while at > 0 and (s[at - 1].isalnum() or s[at - 1] in "_$"):
        at = s.find("function %s(" % name, at + 1)
    if at < 0:
        m = re.search(r"\bfunction %s\s*\(" % re.escape(name), s)
        if not m:
            raise AssertionError("function %s is not in bible.html" % name)
        at = m.start()
    start = at - 6 if s[max(0, at - 6):at] == "async " else at
    return start_to_close(s, start, name)


def start_to_close(s, start, name):
    """s from `start` to the brace that closes the first `{` after it. -> str"""
    i = s.index("{", start)
    depth = 0
    for j in range(i, len(s)):
        c = s[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start:j + 1]
    raise AssertionError("unbalanced braces extracting %s" % name)


def window_fn(s, name):
    """`window.NAME = function(...){...};` brace-matched. -> str"""
    m = re.search(r"window\.%s\s*=\s*function\s*\(" % re.escape(name), s)
    if not m:
        raise AssertionError("window.%s is not in bible.html" % name)
    return start_to_close(s, m.start(), "window." + name) + ";"


def stage(s):
    """the forked-name sets and window.LSR, as bible.html declares them. -> str"""
    lp, wp, lsr, _chars, _backup = _cb._stage(s)
    return lp + wp + lsr


def store_read(s):
    return between(s, "/* ⟦STORE READ⟧", "/* ⟦/STORE READ⟧ */")


def store_notice(s):
    return between(s, "/* ⟦STORE NOTICE⟧", "/* ⟦/STORE NOTICE⟧ */")


def tab_sync(s):
    return between(s, "/* ⟦TAB SYNC⟧", "/* ⟦/TAB SYNC⟧ */")


def vault_head(s):
    i = s.index('<script id="v203-vault-js">')
    j = s.index(VAULT_HEAD_A, i)
    if s.count(VAULT_HEAD_A) != 1:
        raise AssertionError("the vault module head anchor is not unique")
    return s[j:s.index(VAULT_HEAD_B, j)]


#: REG-2415 - the vault module's one filing door and its witness store, between the block's own markers
VAULTFILE_BEGIN = "⟦#246 VAULTFILE BEGIN⟧"
VAULTFILE_END = "⟦#246 VAULTFILE END⟧"
SAY_START = "  var MP_SRC_SAY = { manual: 'placed by hand'"


def vault_door(s):
    """the ⟦#246 VAULTFILE⟧ block, whole lines: the witness store's reader and writer, the hardened lock,
    window.vaultFile, the witness tag and the evidence lines. -> str"""
    if s.count(VAULTFILE_BEGIN) != 1 or s.count(VAULTFILE_END) != 1:
        raise AssertionError("the vaultFile markers are not unique (%d, %d)" % (s.count(VAULTFILE_BEGIN), s.count(VAULTFILE_END)))
    i = s.rfind("\n", 0, s.index(VAULTFILE_BEGIN)) + 1
    j = s.index("\n", s.index(VAULTFILE_END)) + 1
    return s[i:j]


def say_line(s):
    """MP_SRC_SAY - the words a filing's source is said in (the witness tag reads it). -> str"""
    if s.count(SAY_START) != 1:
        raise AssertionError("MP_SRC_SAY is not where the cut looks (%d)" % s.count(SAY_START))
    i = s.index(SAY_START)
    return s[i:s.index("};\n", i) + 3]


#: what the filing door leans on in the page and the laws stand in for: the owned store's writer, a router that
#: sends everything to UNI-ARMOR, no lane locks, the status line and the paints recorded, never drawn
VAULT_DOOR_STUBS = r"""
window.D2R_BUILD = { id: 'vLAW' };
var STATUS = []; function status(m){ STATUS.push(String(m)); }
var renderVault = function(){}; function refreshOpenCard(){}
window._repaintOwned = function(){};
function persistOwned(){ window.LSR.setItem('d2r_owned', JSON.stringify(Array.from(owned))); }
function suggestMule(n){ return { id: 'uni-armor', why: 'the law routes everything to UNI-ARMOR' }; }
function isSharedStash(n){ return false; }
function ownedPool(){ return Array.from(owned); }
window._laneLocked = function(){ return ''; };
window._mainTag = function(){ return 'MAIN'; };
"""


def vault_page(s, extra=""):
    """the store door, the boot and its notice, the tab sync, and the vault module's head with its filing door - one
    node program's pieces. `extra` runs inside the vault module's scope, after the door (a law exposes what it asks). -> str"""
    return (stage(s) + boot(s) + tab_sync(s) + "\n" + VAULT_DOOR_STUBS + "(function(){\n" + vault_head(s) + "\n"
            + "function muleById(id){ return roster.find(function(m){ return m.id === id; }) || null; }\n"
            + say_line(s) + vault_door(s) + "\n" + extra + "\n})();\n")


#: every boot loader of a store persist() writes back - `let NAME = ..._storeRead(kind, fallback).getItem('d2r_KEY')`
LOADER = re.compile(r"^let (\w+) = (?:new Set\()?_storeRead\('(?:list|map\??)', [^)]*\)\.getItem\('(d2r_\w+)'\).*$", re.M)


def loaders(s):
    """[(name, key, line)] for every boot loader that reads through _storeRead."""
    return [(m.group(1), m.group(2), m.group(0)) for m in LOADER.finditer(s)]


def boot(s):
    """the main script's store boot: the reader, the notice, the defaults the loaders name, every loader, persist()."""
    mk = re.search(r"^const MULTI_KEEP_DEFAULT = .*$", s, re.M)
    if not mk:
        raise AssertionError("MULTI_KEEP_DEFAULT moved")
    # REG-2900 - the default keepers are built by _mkShaped ({want, dest}), so the cut carries it ahead of the default
    return ("const LS = window.LSR;\n" + store_read(s) + "\n" + store_notice(s) + "\n" + fn(s, "_mkShaped") + "\n"
            + mk.group(0) + "\n"
            + "\n".join(line for _n, _k, line in loaders(s)) + "\n"
            + "var mf = 699, players = 1, pinnedBoss = null, _mfChosen = true; function _writeGrailFarm(){}\n"
            + between(s, "const persist = () => {", "\n};") + "\n")


PRELUDE = r"""
var RAW = %(seed)s, WARN = [], LISTEN = [], THROW_ON = null;
var localStorage = {
  getItem: function(k){ return Object.prototype.hasOwnProperty.call(RAW, k) ? RAW[k] : null; },
  setItem: function(k, v){ if (THROW_ON && THROW_ON.test(k)) throw new Error('QuotaExceededError'); RAW[k] = String(v); },
  removeItem: function(k){ delete RAW[k]; },
  key: function(i){ var ks = Object.keys(RAW); return i < ks.length ? ks[i] : null; }
};
Object.defineProperty(localStorage, 'length', { get: function(){ return Object.keys(RAW).length; } });
var window = globalThis;
window.localStorage = localStorage;
window._D2R_OWNER = %(owner)s; window.D2R_PROFILE = %(profile)s; window._D2R_LPFX = 'L·'; window._D2R_PFX = 'W·';
window._D2R_INSTALL = 'test';
window.addEventListener = function(t, f){ LISTEN.push([t, f]); };
console.warn = function(m){ WARN.push(String(m)); };
console.info = function(){};
function El(id){ this.id = id || ''; this.hidden = true; this.innerHTML = ''; this.attrs = {}; }
El.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
El.prototype.getAttribute = function(k){ return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; };
var ELS = {};
var document = {
  body: { appendChild: function(c){ if (c && c.id) ELS[c.id] = c; return c; } },
  getElementById: function(id){ return ELS[id] || null; },
  createElement: function(){ return new El(''); },
  addEventListener: function(){}
};
window.document = document;
function fire(key, oldValue, newValue){
  LISTEN.forEach(function(l){ if (l[0] === 'storage') l[1]({ key: key, oldValue: oldValue, newValue: newValue, storageArea: localStorage }); });
}
function done(){ process.stdout.write(JSON.stringify(OUT)); process.exit(0); }
function aside(){ var o = {}; Object.keys(RAW).forEach(function(k){ if (k.indexOf('d2r_quarantine~') >= 0) o[k] = RAW[k]; }); return o; }
var OUT = {};
"""


def page(pieces, body, seed=None, owner=True, profile="main", timeout=90):
    """one node program over the shipped pieces. -> dict (what the body put in OUT)"""
    if NODE is None:
        raise AssertionError("node is absent")
    prog = (PRELUDE % {"seed": json.dumps(seed or {}), "owner": "true" if owner else "false",
                       "profile": json.dumps(profile)}
            + pieces + "\n;(function(){\n" + body + "\n})();\n"
            + "if (!window.__ASYNC) process.stdout.write(JSON.stringify(OUT));\n")
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    if r.returncode != 0:
        raise AssertionError("the shipped code would not run in node - UNKNOWN, not passing: %s"
                             % (r.stderr or r.stdout)[-1500:])
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise AssertionError("node printed no verdict: %r" % (r.stdout[-600:],))
