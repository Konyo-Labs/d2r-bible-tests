"""v3773 - FIND ON A MULE took 12.9 s for one key on his data.

Root cause, measured with the CDP profiler on a copy of his store: every key ran vaultFind, which
asked _vaultRecordsSource once per matched name, and each answer rebuilt every record; inside that,
_provAll re-parsed the whole witness store with JSON.parse on every call (29 s self time over
three keys). The fix: _provAll keeps the last parse keyed on the raw string, one FIND pass shares
one records answer, and the box paints the key at once while the list follows when the keys pause.
After: keys 13 / 3 / 2 ms, one full FIND 30 ms.

These checks run the page's own functions in node. Each RED_PROOF changes what the page does.
"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _read():
    with open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


def _cut(src, start, end):
    i = src.find(start)
    if i < 0:
        raise AssertionError("missing: %s" % start.strip())
    j = src.find(end, i)
    if j < 0:
        raise AssertionError("no end for: %s" % start.strip())
    return src[i:j + len(end)]


def _node(prog):
    out = subprocess.run(["node", "-"], input=prog, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise AssertionError(out.stderr[-1500:])
    return json.loads(out.stdout.strip().splitlines()[-1])


def problems(bible):
    bad = []
    prov = _cut(bible, "  function _provAll(){", "\n  }\n")
    src = _cut(bible, "  function _vaultRecordsSource(){", "\n  }\n")
    # v3864 (#233) - _vaultRecordsSource asks REG-3042's one source choice; the page's own function comes with it (it reads
    # _vrRecFollowLive first, which this harness sets, so the live branch is the one measured, as before)
    src = _cut(bible, "  function _vrSourceChoice(){", "\n  }\n") + src
    wrap = _cut(bible, "  /* v3773 - one FIND pass shares", "  })();\n")
    prog = r"""
var window = {}; var parses = 0; var RAW = JSON.stringify({a: {x: 1}, b: {y: 2}});
var _realParse = JSON.parse; JSON.parse = function(s){ parses++; return _realParse(s); };
function _witnessRaw(){ return RAW; }
""" + prov + r"""
for (var i = 0; i < 50; i++) _provAll();
var p1 = parses, first = _provAll(), sameObj = first === _provAll();
RAW = JSON.stringify({c: {z: 3}});
var second = _provAll();
var rebuilt = 0;
var _vrRecFollowLive = true;
function _vaultRecords(){ rebuilt++; return { ok: true, records: [rebuilt] }; }
""" + src + r"""
var timers = [];
function setTimeout(fn, ms){ timers.push({fn: fn, ms: ms, live: true}); return timers.length; }
function clearTimeout(id){ if (timers[id - 1]) timers[id - 1].live = false; }
var finds = 0, perFind = [], lastQ = null;
var INP = {value: ''}; var document = {getElementById: function(id){ return id === 'vault-find-input' ? INP : null; }};
window.vaultFind = function(q){ finds++; lastQ = q; var a = _vaultRecordsSource(); for (var k = 0; k < 20; k++) _vaultRecordsSource(); perFind.push(rebuilt); return a; };
""" + wrap + r"""
rebuilt = 0; window.vaultFind('sha'); var afterOne = rebuilt; var passAfter = window._vrFindPass;
rebuilt = 0; window.vaultFind('shak'); var afterTwo = rebuilt;
finds = 0; ['s','sh','sha','shak','shako'].forEach(function(q){ window._vaultFindSoon(q); });
var syncFinds = finds;
var live = timers.filter(function(t){ return t.live; });
live.forEach(function(t){ t.live = false; t.fn(); });
var findsAfterKeys = finds;
function fire(){ timers.forEach(function(t){ if (t.live) { t.live = false; t.fn(); } }); }
var f0 = finds; INP.value = 'sha'; window._vaultFindSoon('sha'); INP.value = ''; window.vaultFind(''); fire();
var afterClear = lastQ, clearRuns = finds - f0;
INP.value = 'sha'; window._vaultFindSoon('sh'); fire();
var liveRead = lastQ;
console.log(JSON.stringify({p1: p1, sameObj: sameObj, changed: !!(second && second.c && !second.a),
  afterOne: afterOne, afterTwo: afterTwo, passAfter: passAfter === null || passAfter === undefined,
  syncFinds: syncFinds, liveTimers: live.length, delay: live.length ? live[0].ms : null, finds: findsAfterKeys, afterClear: afterClear, clearRuns: clearRuns, liveRead: liveRead}));
"""
    try:
        got = _node(prog)
    except Exception as e:
        return ["node run raised %s" % e]
    if got["p1"] != 1:
        bad.append("_provAll parsed the same witness store %s times in 50 calls (want 1)" % got["p1"])
    if not got["sameObj"] and got["p1"] == 1:
        bad.append("_provAll did not hand back its kept parse")
    if not got["changed"]:
        bad.append("_provAll kept an old parse after the store changed")
    if got["afterOne"] != 1 or got["afterTwo"] != 1:
        bad.append("one FIND pass rebuilt the records %s / %s times (want 1 each)" % (got["afterOne"], got["afterTwo"]))
    if not got["passAfter"]:
        bad.append("a FIND pass left its shared answer behind for the next caller")
    if got["syncFinds"] != 0:
        bad.append("typing ran FIND inside the key (%d of 5 keys)" % got["syncFinds"])
    if got["liveTimers"] != 1 or got["finds"] != 1:
        bad.append("five quick keys left %d FIND runs pending, ran %d (want 1, 1)" % (got["liveTimers"], got["finds"]))
    if got["delay"] is None or got["delay"] > 300:
        bad.append("FIND waits %s ms after the last key (want <= 300)" % got["delay"])
    if got["afterClear"] != "":
        bad.append("typed sha then cleared inside the pause: FIND came back with %r (want empty)" % got["afterClear"])
    if got["clearRuns"] != 1:
        bad.append("a clear inside the pause ran FIND %d times: the old key timer was left pending" % got["clearRuns"])
    if got["liveRead"] != "sha":
        bad.append("the pending FIND ran the key's old value %r, not the live box 'sha'" % got["liveRead"])
    tag = _cut(bible, '<input id="vault-find-input"', ">")
    if "_vaultFindSoon" not in tag:
        bad.append("the FIND box's oninput does not go through _vaultFindSoon")
    return bad


class TestVaultFindStaysCheap(unittest.TestCase):
    def test_01_find_parses_once_rebuilds_once_and_paints_the_key_first(self):
        bad = problems(_read())
        self.assertEqual(bad, [], bad)

    def test_02_distinct_attacks_clear_the_wilson_bar(self):
        from confidence import wilson_lower
        n = len(RED_PROOF)
        self.assertGreaterEqual(n, 10)
        self.assertGreaterEqual(wilson_lower(n, n), 0.722)


RED_PROOF = [
    {"why": "_provAll re-parses the witness store on every call.",
     "file": "bible.html",
     "find": "if (typeof raw === 'string' && window._provParseRaw === raw && window._provParseObj) return window._provParseObj;",
     "replace": "if (false && window._provParseRaw === raw && window._provParseObj) return window._provParseObj;",
     "matches": 1},
    {"why": "_provAll never keeps its parse.",
     "file": "bible.html",
     "find": "if (typeof raw === 'string') { window._provParseRaw = raw; window._provParseObj = v; }",
     "replace": "if (false) { window._provParseRaw = raw; window._provParseObj = v; }",
     "matches": 1},
    {"why": "_provAll hands back its kept parse whatever the store now says.",
     "file": "bible.html",
     "find": "if (typeof raw === 'string' && window._provParseRaw === raw && window._provParseObj) return window._provParseObj;",
     "replace": "if (window._provParseObj) return window._provParseObj;",
     "matches": 1},
    {"why": "_vaultRecordsSource ignores the FIND pass and rebuilds per name.",
     "file": "bible.html",
     "find": "    if (_pass && typeof _pass === 'object') {",
     "replace": "    if (false && _pass && typeof _pass === 'object') {",
     "matches": 1},
    {"why": "The FIND pass never records that it has its answer.",
     "file": "bible.html",
     "find": "_pass.v = _vaultRecordsSource(); _pass.has = true;",
     "replace": "_pass.v = _vaultRecordsSource();",
     "matches": 1},
    {"why": "vaultFind opens no pass.",
     "file": "bible.html",
     "find": "      window._vrFindPass = outer || {};",
     "replace": "      window._vrFindPass = outer || null;",
     "matches": 1},
    {"why": "vaultFind leaves its pass behind, so a later write reads a stale answer.",
     "file": "bible.html",
     "find": "try { return _vfOne(q); } finally { window._vrFindPass = outer || null; }",
     "replace": "try { return _vfOne(q); } finally { }",
     "matches": 1},
    {"why": "The FIND box runs the whole search inside the key again.",
     "file": "bible.html",
     "find": 'oninput="window._vaultFindSoon?window._vaultFindSoon(this.value):(window.vaultFind&&window.vaultFind(this.value))"',
     "replace": 'oninput="window.vaultFind&&window.vaultFind(this.value)"',
     "matches": 1},
    {"why": "_vaultFindSoon runs FIND at once instead of after the keys pause.",
     "file": "bible.html",
     "find": "      _vfT = setTimeout(function(){\n        _vfT = 0;",
     "replace": "      window.vaultFind(q); _vfT = setTimeout(function(){\n        _vfT = 0;",
     "matches": 1},
    {"why": "_vaultFindSoon never cancels the pending run, so every key still runs a FIND.",
     "file": "bible.html",
     "find": "      if (_vfT) clearTimeout(_vfT);",
     "replace": "      if (false) clearTimeout(_vfT);",
     "matches": 1},
    {"why": "_vaultFindSoon waits five seconds after the last key.",
     "file": "bible.html",
     "find": "never the value the key carried */\n      }, 140);",
     "replace": "never the value the key carried */\n      }, 5000);",
     "matches": 1},
    {"why": "Typed sha then cleared inside the pause: the x / Escape leave the key timer pending.",
     "file": "bible.html",
     "find": "      if (_vfT) { clearTimeout(_vfT); _vfT = 0; }",
     "replace": "      if (false) { clearTimeout(_vfT); _vfT = 0; }",
     "matches": 1},
    {"why": "The pending FIND runs the value its key carried, not the live box.",
     "file": "bible.html",
     "find": "        window.vaultFind(inp ? inp.value : q);",
     "replace": "        window.vaultFind(q);",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
