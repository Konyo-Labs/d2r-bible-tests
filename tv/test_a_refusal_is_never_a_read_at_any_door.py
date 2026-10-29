# -*- coding: utf-8 -*-
"""#158 (REG-2976..2979, the v3834 second eye on REG-2815) - AT EVERY INTAKE DOOR, IN EVERY SHAPE IT ARRIVES, A REFUSAL IS
NEVER A READ, NEVER A PAGE, NEVER "NOTHING RECOGNISED", AND ITS SENTENCE REACHES THE REPORT.

REG-2815 gave the doors one rule, window._intakeRefused(status, body). The full-diff second eye on the shipped v3834 found
four holes in how the doors used it, each reproduced in node before anything was changed (measured on int-9):

  REG-2976  the item checker's judge answered a fetch that threw, a 200 whose body was not JSON, and a frame that could not be
            prepared as {ok:false, why} with no `refused`. The engine's one poster (control_app._fire_aic_judge_js) posts the
            judge's answer to /kai_verdict whole - measured: the cap and the error body DID arrive with refused:true - so
            these three were the hole: journaled as "judge a tooltip - UNREADABLE", which _judge_already_near takes for a
            judged hover.
  REG-2977  the Chronicle screenshot reader pushed a refused page into `pages`, beside the pages that were read, with empty
            printed/read; a thrown read was pushed as {note:'unreadable'}.
  REG-2978  the Chronicle and grail readers and the Ask box parsed the body before the rule saw the status, so a 429 or a 502
            with an empty or non-JSON body threw: an 'unreadable' page, "no FOUND items could be read", "Unexpected end of
            JSON input - is the site deployed". The item checker's upload, the tally reader, the vault grid counter and the
            vault intake asked the status first and dropped the body, so a cap said "server 429" / "HTTP 429" /
            "unreachable" and never its own sentence.
  REG-2979  the set tracker and the craft workshop said "No set pieces recognised (1 image error)" / "No crafted items read
            (1 image error)" for every refusal shape, the sentence thrown away.

Now every door reads its answer through window._intakeAnswer(resp) (the body as text, parsed if JSON, the rule asked of the
status and whatever came back; a body that is no reading is a refusal with its own sentence) and a request that never came
back says window._intakeThrew(e). Driven: every door cut from bible.html and run in node over one stubbed fetch, in seven
refusal shapes (429 cap JSON, a 402 usage limit, 502 empty, 200 + {error}, 200 HTML, a thrown fetch, a shot that could not be
prepared), beside
a clean read and a read that honestly found nothing - so the law can tell the three apart; the engine's real judge poster run
over the real judge, and its body handed to control_app's own refusal row. The vault intake's read is pinned at its line
(read, not run - it is too entangled to cut). RED_PROOF below.

REG-3021 (#158, his ruling): A CAP ENDS THE BATCH. window._intakeIsCap(status, body) is the one cap rule - the reader's
subscription cap (429 + {error:'subscription-cap'}) or an API key at its usage limit (402, or the v438 usage-limit words, the
vault intake's own test moved beside the refusal rule). Measured before it, on a five-shot batch where every answer was the
cap: the set, craft, Chronicle, grail and grid doors each asked the reader 5 times and the tally reader 15 (three passes a
shot). Now every batch door asks once: the shots after the cap are not sent, and each is "not read" for the cap's reason; the
vault intake raises its own v438 stop (_aiLimitHit) on a subscription cap too. A refusal that is not a cap (a 502) does not
end the batch.

REG-3024 (#158): THE DAILY PICK. dailyCreateAi read its answer with r.json() and kept a pick only `if (d.answer)`, so a refusal
in any shape wrote nothing and SAID nothing - the card went on calling an earlier day's sentence "Today's pick". It now reads
its answer through the answer reader; a refusal writes no pick, takes the day's stamp off (the next load asks again) and the
card says "not read - <the rule's sentence>" beside the last pick that was read.
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
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx  # noqa: E402
_fx.contain()
from cb_node_harness import NODE  # noqa: E402

BIBLE = io.open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8").read()
APP = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()

SIGS = ["window._intakeRefused = function(status, data){", "window._intakeAnswer = async function(resp){",
        "window._intakeIsCap = function(status, data){", "window._intakeThrew = function(e){",
        "    function _aiIsLimit(d){", "    function _aiLimitMsg(d){",
        "window._intakeNotReadSay = function(n, why){",
        "  window.aicJudge = async function(file){", "  window.aicUpload = async function(file){",
        "window.setIntake = async function(files){", "function _craftPrepImage(file){", "async function _craftRead(",
        "window.craftIntake = async function(files){", "  window.chronicleShotIntake = async function(files){",
        "  function _chronShotPaint(){", "  window.grailIntake=async function(files){", "  function _grailImportToastOnce(){",
        "function _askEsc(t){", "function _askMd(t){", "window.askBible = function(q){", "async function _tallyRead(",
        "  window.vaultGridCount = async function(files, opts){", "window.dailyCreateAi = function(force){",
        "window._createNowAiBanner = function(ai, notRead){"]


def _cut(src, sig):
    if src.count(sig) != 1:
        raise AssertionError("%r occurs %d times - this law cannot see its subject" % (sig[:60], src.count(sig)))
    i = src.index(sig)
    b = src.index("{", i + len(sig) - 1)
    depth = 0
    for j in range(b, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1] + ";"
    raise AssertionError("%r never closed - harness fault, not a pass" % sig[:60])


HARNESS = r"""
import { readFileSync } from 'node:fs';
const CFG = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const LSR = { _m: {}, getItem(k){ return this._m[k] == null ? null : this._m[k]; }, setItem(k, v){ this._m[k] = String(v); return true; }, removeItem(k){ delete this._m[k]; } };
const window = { LSR };
let els = {};
function el(id){
  return els[id] || (els[id] = { id, hidden: true, innerHTML: '', textContent: '', className: '', style: {}, value: '',
    scrollTop: 0, scrollHeight: 0, insertAdjacentHTML(p, h){ this.innerHTML += h; }, removeAttribute(){},
    appendChild(c){ this.innerHTML += (c && c.innerHTML) || ''; } });
}
let QUEUE = [], IMGFAIL = false, CALLS = 0, RENDERS = 0;
const msgs = [], chron = [];
function mkResp(a){
  const raw = a.raw !== undefined ? a.raw : JSON.stringify(a.body);
  return { ok: a.status >= 200 && a.status <= 299, status: a.status, text: async () => raw, json: async () => JSON.parse(raw) };
}
class Image {
  constructor(){ this.width = 100; this.height = 80; }
  set src(u){ this._s = u; setTimeout(() => { if (IMGFAIL) { if (this.onerror) this.onerror(new Error('the image could not be decoded')); } else if (this.onload) this.onload(); }, 0); }
  get src(){ return this._s; }
}
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const prep = async () => { if (IMGFAIL) throw new Error('the image could not be decoded'); return 'AAAA'; };
const env = {
  window, Image, esc, _cse: esc, console: { log(){}, warn(){}, error(){} },
  URL: { createObjectURL: () => 'blob:x', revokeObjectURL(){} },
  document: { getElementById: el, querySelectorAll: () => [], body: el('body'),
    createElement: () => ({ width: 0, height: 0, innerHTML: '', className: '', style: {}, classList: { add(){} }, remove(){},
      getContext: () => ({ drawImage(){}, imageSmoothingEnabled: true }), toDataURL: () => 'data:image/jpeg;base64,AAAA' }) },
  location: { reload(){}, protocol: 'http:' },
  setTimeout: (f, ms) => (ms && ms > 50 ? 0 : setTimeout(f, ms)),
  fetch: async () => { CALLS++; const a = QUEUE.length > 1 ? QUEUE.shift() : QUEUE[0]; if (a.throw) throw new TypeError(a.throw); return mkResp(a); },
  downscale: prep, _gDownscale: prep,
  _aicIntakeEndpoint: () => '/api/intake', __setPieceNames: () => [],
  _aicItem: {}, _aicSave(){}, _aicMsg: (m) => msgs.push(m), renderAIItemChecker(){},
  _aicApplyIntake: (d) => (d.finds && d.finds.length ? { ok: true, name: d.finds[0].name } : { ok: false, counts: { items: (d.items || []).length, finds: 0, unrec: 0, sockets: 0 } }),
  _aicVerdict: () => ({ tier: 'keep', score: 5, breakdown: [] }),
  persist(){}, renderSetTracker(){}, renderCraftWorkshop(){},
  __allSets: () => [{ name: "Tal Rasha's Wrappings", pieces: ["Tal Rasha's Horadric Crest (helm)", "Tal Rasha's Lidless Eye (orb)"] }],
  setPieces: new Set(), CRAFTS: [{ key: 'Caster' }], CRAFT_SLOTS: ['Amulet'], craftStash: {},
  findCraft: (k) => (/caster amulet/i.test(k) ? { craft: { key: 'Caster' }, slot: 'Amulet' } : null),
  _stashRaise: (store, key, c) => { const h = store[key] || 0; if (c > h) { store[key] = c; return { raised: true, delta: c - h }; } return { raised: false }; },
  buildAskSnapshot: () => ({}),
  _grailVocab: () => ({ vocab: ['Harlequin Crest'], uniq: new Set(['Harlequin Crest']), pieceMap: {} }),
  _chronShotReport: (h) => chron.push(h), _chronAlreadyUni: () => false, _chronAlreadySet: () => false, _chronShot: null,
  navigator: { webdriver: false }, rwMade: {},
  buildTopPicks: () => ({ makeNow: [{ name: 'Spirit' }], afterCubing: [], close: [] }),
};
window._d2rIntakeEndpoint = () => '/api/intake';
window._previewWrap = (f) => f();
window.__allSets = env.__allSets;
window._aiIntakeStart = () => {}; window._aiIntakeStop = () => {};
window.renderCreateNow = () => { RENDERS++; }; window._syncCreateNowAiArt = () => {};
const F = new Function('env', 'with (env) {\n' + CFG.code + '\nreturn { window: window, tally: _tallyRead, toast: _grailImportToastOnce, aiIsLimit: _aiIsLimit, aiLimitMsg: _aiLimitMsg }; }')(env);
const W = F.window;
const tick = () => new Promise((r) => setTimeout(r, 10));
const files = (n) => Array.from({ length: n }, (_, i) => ({ name: 'shot' + i + '.png' }));
function reset(shapes){
  els = {}; msgs.length = 0; chron.length = 0; env.document.body = el('body');
  env.setPieces = new Set(); env.craftStash = {}; env._chronShot = null; LSR._m = {};
  QUEUE = shapes.map((s) => CFG.shapes[s]); IMGFAIL = shapes.some((s) => CFG.shapes[s].imgfail);
}
const DOORS = {
  judge: async () => W.aicJudge({}),
  upload: async () => { await W.aicUpload({}); return msgs.slice(-1)[0] || ''; },
  set: async (n) => { await W.setIntake(files(n)); return { report: el('set-intake-report').innerHTML, marked: Array.from(env.setPieces) }; },
  craft: async (n) => { await W.craftIntake(files(n)); return { report: el('craft-intake-report').innerHTML, stash: Object.assign({}, env.craftStash) }; },
  chron: async (n) => { const p = await W.chronicleShotIntake(files(n)); return { proposal: p, report: chron.slice(-1)[0] || '' }; },
  grail: async (n) => { await W.grailIntake(files(n)); const raw = LSR._m['d2r_grailImportReport'] || null;
    let toast = '', after = ''; if (raw) { F.toast(); toast = el('forge-toasts').innerHTML; after = el('grail-intake-report').innerHTML; }
    return { report: el('grail-intake-report').innerHTML, imported: raw ? JSON.parse(raw) : null, toast, after }; },
  ask: async () => { W.askBible('what next?'); for (let i = 0; i < 8; i++) await tick(); const b = el('ask-pending'); return { bubble: b.innerHTML || b.textContent, cls: b.className }; },
  tally: async () => { const why = {}; const t = await F.tally('AAAA', [], 'runes', 'tally', why); return { result: t, why: why.text || null }; },
  grid: async (n) => W.vaultGridCount(files(n), { tab: 'personal' }),
  pick: async () => { LSR._m['d2r_createNowAi'] = 'Make Enigma - an earlier day'; window._createNowAiNotRead = ''; RENDERS = 0;
    W.dailyCreateAi(true); for (let i = 0; i < 8; i++) await tick();
    const ai = LSR._m['d2r_createNowAi'] || '';
    return { pick: ai, dated: 'd2r_createNowAiDate' in LSR._m, notRead: window._createNowAiNotRead || '', renders: RENDERS,
             banner: W._createNowAiBanner(ai, window._createNowAiNotRead) }; },
  tallyN: async (n) => { const why = {}, rs = []; for (let i = 0; i < n; i++) rs.push(await F.tally('AAAA', [], 'runes', 'tally', why)); return { results: rs, why: why.text || null, cap: !!why.cap }; },
};
const out = { doors: {}, partial: {}, poster: {}, helper: {} };
for (const s of Object.keys(CFG.shapes)) {
  out.doors[s] = {};
  for (const d of Object.keys(DOORS)) { reset([s]); out.doors[s][d] = await DOORS[d](1); }
}
for (const [d, shapes] of CFG.partial) { reset(shapes); out.partial[d + ':' + shapes.join('+')] = await DOORS[d](shapes.length); }
for (const s of Object.keys(CFG.shapes)) {
  reset([s]);
  let posted = null;
  const Wj = { aicJudge: W.aicJudge, aicJudgeApply: () => ({ mode: 'keep', actions: [] }), File: class { constructor(){} } };
  const doc = { getElementById: (id) => (id === 'tvd-eng' ? { contentWindow: Wj } : null) };
  const pf = async (url, opts) => { if (String(url).indexOf('/kai_verdict') === 0) { posted = JSON.parse(opts.body); return { ok: true }; } return { ok: true, blob: async () => 'b' }; };
  const started = new Function('document', 'fetch', 'return ' + CFG.poster)(doc, pf);
  for (let i = 0; i < 20 && posted === null; i++) await tick();
  out.poster[s] = { started, posted };
}
out.helper.okFalseNoStatus = await W._intakeAnswer({ ok: false, json: async () => ({}) });
out.helper.noBody = await W._intakeAnswer({ ok: true, status: 200 });
out.helper.arrayBody = await W._intakeAnswer(mkResp({ status: 200, body: [] }));
out.helper.jsonOnly = await W._intakeAnswer({ ok: true, status: 200, json: async () => ({ items: ['x'] }) });
out.helper.threw = W._intakeThrew(new TypeError('Failed to fetch'));
out.caps = {};
const capRun = async (key, d, shapes, n) => { reset(shapes); CALLS = 0; const r = await DOORS[d](n == null ? shapes.length : n); out.caps[key] = { calls: CALLS, r }; };
for (const d of ['set', 'craft', 'chron', 'grail', 'grid']) {
  await capRun(d + ':all', d, ['cap429'], 5);
  await capRun(d + ':mid', d, ['read', 'cap429', 'read', 'read']);
  await capRun(d + ':limit', d, ['limit402', 'read'], 2);
  await capRun(d + ':notcap', d, ['empty502', 'read', 'read']);
}
await capRun('tally:all', 'tallyN', ['cap429'], 5);
await capRun('tally:mid', 'tallyN', ['read', 'read', 'cap429', 'read'], 3);
await capRun('tally:notcap', 'tallyN', ['empty502', 'empty502', 'empty502', 'read', 'read'], 2);
out.isCap = {};
for (const [k, a] of Object.entries(CFG.shapes)) out.isCap[k] = a.body ? W._intakeIsCap(a.status, a.body) : false;
out.vault = { capIsLimit: F.aiIsLimit(CFG.shapes.cap429.body), limitIsLimit: F.aiIsLimit(CFG.shapes.limit402.body),
              errIsLimit: F.aiIsLimit(CFG.shapes.err200.body), capMsg: F.aiLimitMsg(CFG.shapes.cap429.body),
              limitMsg: F.aiLimitMsg(CFG.shapes.limit402.body) };
process.stdout.write(JSON.stringify(out));
"""

CAP = {"error": "subscription-cap", "message": "20/20 this hour - intake paused", "window": "hour", "retry_s": 120}
READ = {"items": ["Tal Rasha's Horadric Crest", "Harlequin Crest"], "finds": [{"name": "Arachnid Mesh", "mods": []}],
        "found": ["Harlequin Crest"], "notFound": [], "sets": [], "witness": "none", "printed": {}, "read": {},
        "tally": {"Caster Amulet": 1, "El": 2}, "answer": "Make Spirit.", "count": 3}
EMPTY = {"items": [], "finds": [], "found": [], "notFound": [], "sets": [], "witness": "none", "printed": {}, "read": {},
         "tally": {}, "answer": "Nothing to make yet.", "count": 0, "unrecognized": []}
SHAPES = {
    "read": {"status": 200, "body": READ},
    "empty": {"status": 200, "body": EMPTY},
    "cap429": {"status": 429, "body": CAP},
    "empty502": {"status": 502, "raw": ""},
    "err200": {"status": 200, "body": {"error": "upstream", "message": "the model is overloaded"}},
    "limit402": {"status": 200, "body": {"error": "upstream", "status": 402, "tally": {}, "items": [], "unrecognized": [],
                                         "detail": "You have reached your specified API usage limits. You will regain access "
                                                   "on 2026-11-01 at 00:00 UTC."}},
    "html200": {"status": 200, "raw": "<html><body>Bad gateway</body></html>"},
    "throw": {"throw": "Failed to fetch"},
    "unprepared": {"status": 200, "body": READ, "imgfail": True},
}
# the words each refusal must carry to the door's report - its own sentence, not a stand-in
SAYS = {"cap429": ["at its cap", "20/20 this hour", "HTTP 429"], "limit402": ["usage limits"], "empty502": ["HTTP 502"],
        "err200": ["overloaded"],
        "html200": ["not JSON"], "throw": ["Failed to fetch"], "unprepared": ["could not be decoded"]}
REFUSALS = list(SAYS)
PARTIAL = [["set", ["read", "cap429"]], ["craft", ["read", "cap429"]], ["chron", ["read", "cap429"]],
           ["grail", ["read", "cap429"]], ["grail", ["empty", "cap429"]], ["grid", ["read", "empty502"]]]


def _drive():
    if NODE is None:
        raise AssertionError("node is not on this machine - this law does not skip")
    import control_app as ca
    poster = ca._fire_aic_judge_js("/hist/1_1793189802000.jpg", "s_1", "1_1793189802000", 1793189802000)
    code = "\n".join(_cut(BIBLE, s) for s in SIGS)
    d = tempfile.mkdtemp(prefix="refusal_doors_")
    try:
        h, c = os.path.join(d, "h.mjs"), os.path.join(d, "cfg.json")
        with io.open(h, "w", encoding="utf-8") as fh:
            fh.write(HARNESS)
        with io.open(c, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"code": code, "shapes": SHAPES, "partial": PARTIAL, "poster": poster}))
        r = subprocess.run([NODE, h, c], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    finally:
        shutil.rmtree(d, True)
    if r.returncode != 0:
        raise AssertionError("node failed: %s" % r.stderr[-1200:])
    return json.loads(r.stdout)


_O = {}


def _o():
    if not _O:
        _O.update(_drive())
    return _O


def _says(case, text, shape):
    for w in SAYS[shape]:
        case.assertIn(w, text or "", "%s: the refusal's own sentence (%r) never reached the report: %r" % (shape, w, text))


class AReadAndAnHonestEmptyAreStillWhatTheyWere(unittest.TestCase):
    """PREMISE: the harness tells a read, a read that found nothing, and a refusal apart."""

    def test_a_clean_read_reads(self):
        o = _o()["doors"]["read"]
        self.assertTrue(o["judge"]["ok"], o["judge"])
        self.assertIn("read <b>Arachnid Mesh</b>", o["upload"])
        self.assertEqual(o["set"]["marked"], ["Tal Rasha's Horadric Crest (helm)"])
        self.assertEqual(o["craft"]["stash"], {"Caster Amulet": 1})
        self.assertEqual(len(o["chron"]["proposal"]["pages"]), 1)
        self.assertEqual(o["chron"]["proposal"]["refused"], [])
        self.assertEqual(o["chron"]["proposal"]["wouldAdd"]["uniques"], ["Harlequin Crest"])
        self.assertEqual((o["grail"]["imported"] or {}).get("u"), 1, o["grail"])
        self.assertIn("Make Spirit.", o["ask"]["bubble"])
        self.assertEqual(o["tally"]["result"], {"Caster Amulet": 1, "El": 2})
        self.assertEqual((o["grid"]["ok"], o["grid"]["total"], o["grid"].get("errWhy")), (True, 3, None))

    def test_a_read_that_found_nothing_still_says_so(self):
        o = _o()["doors"]["empty"]
        self.assertFalse(o["judge"].get("refused"), "a real read that found nothing was called a refusal: %r" % o["judge"])
        self.assertEqual(o["judge"]["why"], "no magic/rare item readable in this frame")
        self.assertIn("found no magic/rare item", o["upload"])
        self.assertIn("No set pieces recognised", o["set"]["report"])
        self.assertNotIn("not read", o["set"]["report"])
        self.assertIn("No crafted items read", o["craft"]["report"])
        self.assertNotIn("not read", o["craft"]["report"])
        self.assertEqual(len(o["chron"]["proposal"]["pages"]), 1)
        self.assertIn("Nothing to register", o["chron"]["report"])
        self.assertIn("no FOUND items could be read", o["grail"]["report"])
        self.assertNotIn("not read", o["grail"]["report"])
        self.assertNotIn("ask-err", o["ask"]["cls"])
        self.assertEqual(o["tally"]["result"], {})
        self.assertEqual((o["grid"]["ok"], o["grid"]["errors"], o["grid"].get("errWhy")), (False, 0, None))


class EveryDoorSaysARefusalInEveryShape(unittest.TestCase):

    @staticmethod
    def _each(door, shapes=REFUSALS):
        return [(s, _o()["doors"][s][door]) for s in shapes]

    def test_the_judge_says_refused(self):   # REG-2976
        for s, j in self._each("judge"):
            with self.subTest(shape=s):
                self.assertEqual((j["ok"], j.get("refused")), (False, True), "a refusal judged as UNREADABLE: %r" % j)
                _says(self, j["why"], s)

    def test_the_upload_says_nothing_was_read(self):   # REG-2978
        for s, m in self._each("upload"):
            with self.subTest(shape=s):
                self.assertNotIn("found no magic/rare item", m)
                if s == "throw":
                    self.assertIn("couldn’t reach the AI (network)", m)
                else:
                    self.assertTrue("nothing was read" in m or "read failed (" in m, m)
                    _says(self, m, s)

    def test_the_set_tracker_never_says_nothing_recognised(self):   # REG-2979
        for s, o in self._each("set"):
            with self.subTest(shape=s):
                self.assertEqual(o["marked"], [])
                self.assertNotIn("No set pieces recognised", o["report"])
                self.assertIn("nothing was read", o["report"])
                _says(self, o["report"], s)

    def test_the_craft_workshop_never_says_no_crafted_items(self):   # REG-2979
        for s, o in self._each("craft"):
            with self.subTest(shape=s):
                self.assertEqual(o["stash"], {})
                self.assertNotIn("No crafted items read", o["report"])
                self.assertIn("nothing was read", o["report"])
                _says(self, o["report"], s)

    def test_the_chronicle_reader_keeps_a_refusal_out_of_its_pages(self):   # REG-2977 + REG-2978
        for s, o in self._each("chron"):
            with self.subTest(shape=s):
                p = o["proposal"]
                self.assertEqual(p["pages"], [], "a page the reader never read is counted as a page: %r" % p["pages"])
                self.assertEqual([x["n"] for x in p["refused"]], [1])
                _says(self, p["refused"][0]["why"], s)
                self.assertIn("page 1 — not read:", o["report"])
                self.assertIn("Nothing was read", o["report"])
                self.assertNotIn("Nothing to register", o["report"])
                _says(self, o["report"], s)

    def test_the_grail_reader_says_the_refusal(self):   # REG-2978
        for s, o in self._each("grail"):
            with self.subTest(shape=s):
                self.assertIsNone(o["imported"])
                self.assertNotIn("no FOUND items", o["report"])
                self.assertIn("nothing was read", o["report"])
                _says(self, o["report"], s)

    def test_the_ask_box_says_the_refusal_not_the_deploy(self):   # REG-2978
        for s, o in self._each("ask", [x for x in REFUSALS if x != "unprepared"]):
            with self.subTest(shape=s):
                self.assertIn("ask-err", o["cls"])
                _says(self, o["bubble"], s)
                if s != "throw":
                    self.assertNotIn("is the site deployed", o["bubble"], "a refusal blamed on the deploy: %r" % o["bubble"])

    def test_the_tally_reader_names_the_refusal(self):   # REG-2978
        for s, o in self._each("tally", [x for x in REFUSALS if x != "unprepared"]):
            with self.subTest(shape=s):
                self.assertIsNone(o["result"])
                _says(self, o["why"], s)

    def test_the_grid_counter_counts_nothing_and_says_why(self):   # REG-2978
        for s, o in self._each("grid"):
            with self.subTest(shape=s):
                self.assertEqual((o["ok"], o["total"], o["errors"]), (False, 0, 1), o)
                _says(self, o.get("errWhy"), s)



class APartBatchSaysWhatWasNotRead(unittest.TestCase):

    def test_the_read_lands_and_the_refused_shot_is_said(self):
        P = _o()["partial"]
        o = P["set:read+cap429"]
        self.assertEqual(o["marked"], ["Tal Rasha's Horadric Crest (helm)"])
        self.assertIn("1 shot not read — the reader is at its cap", o["report"])
        o = P["craft:read+cap429"]
        self.assertEqual(o["stash"], {"Caster Amulet": 1})
        self.assertIn("1 shot not read — the reader is at its cap", o["report"])
        o = P["chron:read+cap429"]
        self.assertEqual((len(o["proposal"]["pages"]), [x["n"] for x in o["proposal"]["refused"]]), (1, [2]))
        self.assertIn("page 2 — not read: the reader is at its cap", o["report"])
        self.assertIn("would be registered", o["report"])
        o = P["grid:read+empty502"]
        self.assertEqual((o["total"], o["errors"], o["errWhy"]), (3, 1, "the reader answered HTTP 502"))

    def test_the_grail_import_carries_the_refused_shot_to_its_toast_and_report(self):
        o = _o()["partial"]["grail:read+cap429"]
        self.assertEqual(((o["imported"] or {}).get("ref"), "at its cap" in str((o["imported"] or {}).get("why"))), (1, True))
        self.assertIn("1 shot not read — the reader is at its cap", o["toast"])
        self.assertIn("1 shot not read — the reader is at its cap", o["after"])

    def test_a_grail_batch_that_read_one_shot_is_not_called_unread(self):
        o = _o()["partial"]["grail:empty+cap429"]
        self.assertIn("no FOUND items could be read", o["report"])
        self.assertIn("1 shot not read — the reader is at its cap", o["report"])
        self.assertNotIn("nothing was read", o["report"])


class TheJudgePosterJournalsARefusalAsOne(unittest.TestCase):
    """REG-2976 - the engine's real poster over the real judge, its body handed to control_app's own rows."""

    def test_every_refusal_shape_posts_refused(self):
        import control_app as ca
        for s in REFUSALS:
            with self.subTest(shape=s):
                got = _o()["poster"][s]
                self.assertEqual(got["started"], 1, "PREMISE: the poster never started: %r" % got)
                body = got["posted"]
                self.assertIsNotNone(body, "the poster never posted to /kai_verdict")
                self.assertIs(body.get("refused"), True, "a refusal reaches /kai_verdict as a judge: %r" % body)
                self.assertEqual((body["sid"], body["frameId"], body["fts"]), ("s_1", "1_1793189802000", 1793189802000))
                row = ca._kai_refused_row(body, 1793189900000)
                self.assertEqual(row["mode"], "kai-judge-refused")
                _says(self, row["kai"]["judgeRefused"]["why"], s)
                self.assertFalse(ca._judge_already_near([row], 1793189802000),
                                 "a refused judge stood in for a judge of that hover")

    def test_a_read_and_an_honest_empty_post_as_judges(self):
        P = _o()["poster"]
        self.assertTrue(P["read"]["posted"]["ok"])
        self.assertFalse(P["empty"]["posted"].get("refused"), P["empty"]["posted"])
        self.assertEqual(P["empty"]["posted"]["why"], "no magic/rare item readable in this frame")


class TheAnswerReader(unittest.TestCase):

    def test_its_edges(self):
        h = _o()["helper"]
        self.assertEqual(h["okFalseNoStatus"]["refused"], "the reader answered HTTP (no status)")
        self.assertEqual(h["noBody"]["refused"], "the reader sent no answer - HTTP 200")
        self.assertIn("not a reading", h["arrayBody"]["refused"])
        self.assertIsNone(h["jsonOnly"]["refused"], "a reply with only json() (a stub, an old fetch) was refused: %r" % h)
        self.assertEqual(h["jsonOnly"]["data"], {"items": ["x"]})
        self.assertEqual(h["threw"], "the read did not happen (Failed to fetch)")

    def test_no_door_asks_the_rule_around_the_answer_reader(self):
        code = "\n".join(re.sub(r"/\*.*?\*/|//[^\n]*$", "", l) for l in BIBLE.split("\n"))
        self.assertEqual(code.count("window._intakeRefused(st, data)"), 1, "PREMISE: the answer reader asks the rule")
        own = [a for a in re.findall(r"window\._intakeRefused\(([^,)]*)", code) if re.search(r"status|\.st\b", a)]
        self.assertEqual(own, [], "a door asks the refusal rule of a response it parsed itself - the answer reader is the "
                                  "one door")


class TheDailyPickSaysARefusalAndWritesNoPick(unittest.TestCase):
    """REG-3024 - a refused daily pick writes no pick, says "not read - <why>", and the day is asked again."""

    def test_a_read_pick_is_kept(self):
        o = _o()["doors"]["read"]["pick"]
        self.assertEqual((o["pick"], o["notRead"], o["dated"]), ("Make Spirit.", "", True))
        self.assertIn("Today’s pick:</b> Make Spirit.", o["banner"])

    def test_a_refusal_writes_no_pick_and_says_so(self):
        for s in [x for x in REFUSALS if x != "unprepared"]:
            with self.subTest(shape=s):
                o = _o()["doors"][s]["pick"]
                self.assertEqual(o["pick"], "Make Enigma - an earlier day", "a refused pick wrote a pick: %r" % o)
                self.assertTrue(o["notRead"].startswith("not read — "), o)
                _says(self, o["notRead"], s)
                self.assertIn("Today’s pick:</b> not read", o["banner"])
                self.assertIn("the last pick it read: Make Enigma", o["banner"])
                self.assertFalse(o["dated"], "a refused day kept its stamp, so it is never asked again today")
                self.assertGreaterEqual(o["renders"], 1, "the card was not repainted to say it")

    def test_the_card_draws_its_pick_line_through_the_one_banner(self):
        self.assertEqual(BIBLE.count("  var aiBanner = window._createNowAiBanner(ai, window._createNowAiNotRead);   /* REG-3024 */"), 1,
                         "renderCreateNow draws the pick line by hand again, so a refused pick is not said on the card")


class ACapEndsTheBatch(unittest.TestCase):
    """REG-3021 - a cap is asked once per batch; every shot after it is not read, for the cap's reason."""

    CAP = "the reader is at its cap (20/20 this hour - intake paused) - HTTP 429"

    def test_the_cap_rule_names_a_cap_and_only_a_cap(self):
        c = _o()["isCap"]
        self.assertEqual((c["cap429"], c["limit402"]), (True, True))
        for k in ("read", "empty", "err200", "empty502", "html200"):
            self.assertFalse(c[k], "%s was called a cap - a batch would stop for a refusal that may lift" % k)

    def test_a_batch_all_at_the_cap_asks_once(self):
        C = _o()["caps"]
        for d in ("set", "craft", "chron", "grail", "grid", "tally"):
            with self.subTest(door=d):
                self.assertEqual(C[d + ":all"]["calls"], 1, "%s asked a capped reader %d times for 5 shots"
                                 % (d, C[d + ":all"]["calls"]))
        self.assertIn("5 shots not read \u2014 " + self.CAP, C["set:all"]["r"]["report"])
        self.assertIn("5 shots not read \u2014 " + self.CAP, C["craft:all"]["r"]["report"])
        self.assertEqual([(x["n"], x["why"]) for x in C["chron:all"]["r"]["proposal"]["refused"]],
                         [(n, self.CAP) for n in range(1, 6)])
        self.assertIn(self.CAP + " (5 screenshots)", C["grail:all"]["r"]["report"])
        self.assertEqual((C["grid:all"]["r"]["errors"], C["grid:all"]["r"]["errWhy"]), (5, self.CAP))
        self.assertEqual((C["tally:all"]["r"]["results"], C["tally:all"]["r"]["why"]), ([None] * 5, self.CAP))

    def test_a_cap_mid_batch_keeps_what_was_read_and_says_the_rest(self):
        C = _o()["caps"]
        for d in ("set", "craft", "chron", "grail", "grid"):
            with self.subTest(door=d):
                self.assertEqual(C[d + ":mid"]["calls"], 2, "%s asked again after the cap" % d)
        self.assertEqual(C["set:mid"]["r"]["marked"], ["Tal Rasha's Horadric Crest (helm)"])
        self.assertIn("3 shots not read \u2014 " + self.CAP, C["set:mid"]["r"]["report"])
        self.assertEqual(C["craft:mid"]["r"]["stash"], {"Caster Amulet": 1})
        self.assertIn("3 shots not read \u2014 " + self.CAP, C["craft:mid"]["r"]["report"])
        p = C["chron:mid"]["r"]["proposal"]
        self.assertEqual((len(p["pages"]), [(x["n"], x["why"]) for x in p["refused"]]),
                         (1, [(2, self.CAP), (3, self.CAP), (4, self.CAP)]))
        self.assertIn("page 4 \u2014 not read: " + self.CAP, C["chron:mid"]["r"]["report"])
        imp = C["grail:mid"]["r"]["imported"] or {}
        self.assertEqual((imp.get("u"), imp.get("ref"), imp.get("why")), (1, 3, self.CAP))
        g = C["grid:mid"]["r"]
        self.assertEqual((g["total"], g["errors"], g["errWhy"]), (3, 3, self.CAP))
        t = C["tally:mid"]
        self.assertEqual((t["calls"], t["r"]["results"][1:], t["r"]["why"]), (3, [None, None], self.CAP))
        self.assertEqual(t["r"]["results"][0], {"Caster Amulet": 1, "El": 2})

    def test_a_usage_limit_is_a_cap_too(self):
        C = _o()["caps"]
        for d in ("set", "craft", "chron", "grail", "grid"):
            with self.subTest(door=d):
                self.assertEqual(C[d + ":limit"]["calls"], 1)
        self.assertIn("2 shots not read", C["set:limit"]["r"]["report"])
        self.assertIn("usage limits", C["set:limit"]["r"]["report"])

    def test_a_refusal_that_is_not_a_cap_does_not_end_the_batch(self):
        """PREMISE: the law can tell a cap from any refusal - a 502 is said and the batch goes on."""
        C = _o()["caps"]
        for d in ("set", "craft", "chron", "grail", "grid"):
            with self.subTest(door=d):
                self.assertEqual(C[d + ":notcap"]["calls"], 3)
        self.assertEqual(C["set:notcap"]["r"]["marked"], ["Tal Rasha's Horadric Crest (helm)"])
        self.assertIn("1 shot not read \u2014 the reader answered HTTP 502", C["set:notcap"]["r"]["report"])
        t = C["tally:notcap"]
        self.assertEqual((t["calls"], t["r"]["results"][1], t["r"]["cap"]), (5, {"Caster Amulet": 1, "El": 2}, False))

    def test_the_vault_intake_stops_on_a_subscription_cap(self):
        v = _o()["vault"]
        self.assertEqual((v["capIsLimit"], v["limitIsLimit"], v["errIsLimit"]), (True, True, False))
        self.assertIn(self.CAP, v["capMsg"])
        self.assertIn("rest of this batch was not asked", v["capMsg"])
        self.assertNotIn("Anthropic", v["capMsg"], "a subscription cap was explained as the API key's monthly cap")
        self.assertIn("regains access 2026-11-01 at 00:00 UTC", v["limitMsg"])
        self.assertEqual(BIBLE.count("        if (_ansV.cap) _aiLimitSeen(_ansV.data);"), 1,
                         "the vault intake's first read does not raise its stop on a cap")


class TheVaultDoorsSayTheReadersSentence(unittest.TestCase):
    """The vault intake is read at its line, not run (it is too entangled to cut); its grid counter's receipt is the console's."""

    def test_the_vault_intake_reads_its_answer_through_the_reader(self):
        self.assertEqual(BIBLE.count("        var _ansV = await window._intakeAnswer(resp);"), 1)
        self.assertEqual(BIBLE.count(
            "        if (!resp.ok || !_ansV.data) { errors++; fRec.err = true; if (!_aiErr) _aiErr = 'AI service · ' "
            "+ _ansV.refused; doneCount++;"), 1, "the vault intake drops the reader's sentence for 'unreachable'")
        self.assertEqual(BIBLE.count("AI service unreachable · HTTP "), 0)

    def test_the_grid_count_receipt_carries_its_reason(self):
        self.assertEqual(APP.count("kind:'vault-count',ok:!!(res&&res.ok),counts:(res&&(res.counts||res.added))||{},"
                                   "total:(res&&res.total)||0,errors:(res&&res.errors)||0,"
                                   "errWhy:(res&&res.errWhy)||undefined,frameId:%s})"), 1,
                         "the engine's vault-count receipt drops the reader's sentence")


RED_PROOF = [
    {"why": "REG-2978 - a body that is no reading (HTML on a 200) reads as a read again",
     "file": "bible.html",
     "find": "  if (!rf && !data) rf = 'the reader sent ' + bad + (st ? ' - HTTP ' + st : '');\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2978 - a non-2xx with no status is a read again",
     "file": "bible.html",
     "find": "  if (!rf && resp && resp.ok === false) rf = 'the reader answered HTTP ' + (st || '(no status)');\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2978 - the Chronicle reader parses before the status is judged again (a 502 with no body is 'unreadable')",
     "file": "bible.html",
     "find": "        var ans = await window._intakeAnswer(resp);   /* REG-2978 - a 429 or a 502 with no JSON body is still its status */\n        var _rfC",
     "replace": "        var _d0 = await resp.json(); var ans = { data: _d0, refused: window._intakeRefused(resp.status, _d0) };\n        var _rfC",
     "matches": 1, "needs": "node"},
    {"why": "REG-2977 - the Chronicle reader files a refused page among its pages again",
     "file": "bible.html",
     "find": "        if (_rfC) { refused.push({ n:i+1, why:_rfC }); continue; }   /* REG-2977 - nor a page at all */\n",
     "replace": "        if (_rfC) { pages.push({ n:i+1, note:_rfC, witness:'none', printed:{}, read:{} }); continue; }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2977 - a read that never happened is an 'unreadable' page again",
     "file": "bible.html",
     "find": "      } catch(e){ refused.push({ n:i+1, why:window._intakeThrew(e) }); }   /* REG-2977 - never an 'unreadable' page */\n",
     "replace": "      } catch(e){ pages.push({ n:i+1, note:'unreadable' }); }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2977 - the Chronicle report no longer says which page was not read, or why",
     "file": "bible.html",
     "find": "      H.push('<div class=\"chron-shot-warn chron-shot-refused\" style=\"color:#e0a860\">⚠ page ' + x.n + ' — not read: ' + _cse(x.why) + '</div>');\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2977 - a batch the reader never read says 'Nothing to register' again",
     "file": "bible.html",
     "find": "    if (!n && (p.refused || []).length && !(p.pages || []).length){",
     "replace": "    if (false){",
     "matches": 1, "needs": "node"},
    {"why": "REG-2976 - the judge answers a fetch that threw without saying it refused",
     "file": "bible.html",
     "find": "      } catch(eAsk){ return { ok:false, refused:true, why: window._intakeThrew(eAsk) }; }",
     "replace": "      } catch(eAsk){ return { ok:false, why: String(eAsk && eAsk.message || eAsk) }; }",
     "matches": 1, "needs": "node"},
    {"why": "REG-2979 - the set tracker says 'No set pieces recognised' for a batch nobody read again",
     "file": "bible.html",
     "find": "    } else if (notRead >= files.length){\n      report.innerHTML='⚠ <strong>nothing was read</strong>",
     "replace": "    } else if (false){\n      report.innerHTML='⚠ <strong>nothing was read</strong>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2979 - the set tracker drops the refusal's sentence again",
     "file": "bible.html",
     "find": "      if (ans.refused) { notRead++; notReadWhy = notReadWhy || ans.refused; continue; }   /* REG-2815 - a refusal is not a page read clean */\n",
     "replace": "      if (ans.refused) { notRead++; continue; }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2979 - the craft workshop drops the refusal's sentence again",
     "file": "bible.html",
     "find": "      if (t === null){ notRead++; notReadWhy = notReadWhy || _whyC.text || ''; continue; }",
     "replace": "      if (t === null){ notRead++; continue; }",
     "matches": 1, "needs": "node"},
    {"why": "REG-2979 - the craft reader never says why it refused",
     "file": "bible.html",
     "find": "    if (ans.refused) { if (why) why.text = ans.refused; return null; }   /* REG-2815 - a refusal is no tally, never an empty one */\n",
     "replace": "    if (ans.refused) { return null; }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2979 - the craft workshop says 'No crafted items read' for a batch nobody read again",
     "file": "bible.html",
     "find": "    } else if (notRead >= files.length){\n      report.innerHTML = '⚠ <strong>nothing was read</strong>",
     "replace": "    } else if (false){\n      report.innerHTML = '⚠ <strong>nothing was read</strong>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2978 - the grail reader forgets why a read never happened",
     "file": "bible.html",
     "find": "      } catch(e){ errs++; refusedWhy = refusedWhy || window._intakeThrew(e); }   /* REG-2978 - a read that never happened says why */\n",
     "replace": "      } catch(e){ errs++; }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2978 - a grail batch that read one shot is called 'nothing was read' again",
     "file": "bible.html",
     "find": "    if(!found.size){ show(errs >= files.length ? ('⚠ nothing was read",
     "replace": "    if(!found.size){ show(refusedWhy ? ('⚠ nothing was read",
     "matches": 1, "needs": "node"},
    {"why": "REG-2978 - the grail import drops the shots it did not read",
     "file": "bible.html",
     "find": "ref:errs,why:refusedWhy,t:Date.now()",
     "replace": "t:Date.now()",
     "matches": 1, "needs": "node"},
    {"why": "REG-2978 - the Ask box parses before the status is judged again (a 502 with no body 'is the site deployed')",
     "file": "bible.html",
     "find": "    .then(function(r){ return window._intakeAnswer(r); })   /* REG-2978 - a 429 or a 502",
     "replace": "    .then(function(r){ return r.json().then(function(d){ return { data: d, refused: window._intakeRefused(r.status, d) }; }); })   /* REG-2978 - a 429 or a 502",
     "matches": 1, "needs": "node"},
    {"why": "REG-2978 - the item checker's upload says 'server 429' and not the cap again",
     "file": "bible.html",
     "find": "      var _ansU=await window._intakeAnswer(resp);",
     "replace": "      var _ansU={ refused: resp.ok ? null : ('read failed (server ' + resp.status + ')'), data: await resp.json() };",
     "matches": 1, "needs": "node"},
    {"why": "REG-2978 - the tally reader says 'HTTP 429' and not the cap again",
     "file": "bible.html",
     "find": "      if(ans.refused) return _fail(ans.refused);",
     "replace": "      if(ans.refused) return _fail('the intake answered HTTP ' + resp.status);",
     "matches": 1, "needs": "node"},
    {"why": "REG-2978 - the vault grid counter drops the refusal's sentence",
     "file": "bible.html",
     "find": "        if (ans.refused){ errors++; errWhy = errWhy || ans.refused; continue; }\n",
     "replace": "        if (ans.refused){ errors++; continue; }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2978 - the engine's vault-count receipt drops the reader's sentence",
     "file": "tv/control_app.py",
     "find": "errors:(res&&res.errors)||0,errWhy:(res&&res.errWhy)||undefined,frameId:%s})",
     "replace": "errors:(res&&res.errors)||0,frameId:%s})",
     "matches": 1},
    {"why": "REG-2978 - the vault intake calls a cap 'unreachable' again",
     "file": "bible.html",
     "find": "if (!_aiErr) _aiErr = 'AI service · ' + _ansV.refused;",
     "replace": "if (!_aiErr) _aiErr = 'AI service unreachable · HTTP ' + resp.status;",
     "matches": 1},
    {"why": "REG-3021 - the answer reader never says a refusal is a cap",
     "file": "bible.html",
     "find": "  return { status: st, data: data, refused: rf, cap: !!rf && window._intakeIsCap(st, data) };   /* REG-3021 */\n",
     "replace": "  return { status: st, data: data, refused: rf, cap: false };\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3021 - the cap rule forgets the subscription cap",
     "file": "bible.html",
     "find": "  if (data.error === 'subscription-cap') return true;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3021 - the cap rule calls every refusal a cap",
     "file": "bible.html",
     "find": "  return +data.status === 402 || +status === 402\n",
     "replace": "  return true || +data.status === 402 || +status === 402\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3021 - the set tracker asks a capped reader for every shot again",
     "file": "bible.html",
     "find": "    if (capWhy) { notRead++; continue; }   /* REG-3021 - the reader is at its cap: the rest of the batch is not asked */\n    try{\n",
     "replace": "    try{\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3021 - the craft workshop asks a capped reader for every shot again",
     "file": "bible.html",
     "find": "      if (_whyC.cap) capWhy = notReadWhy = _whyC.text;   /* REG-3021 - and the cap is why the rest is not read */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3021 - the Chronicle reader asks a capped reader for every page again",
     "file": "bible.html",
     "find": "        if (ans.cap) capWhy = _rfC;   /* REG-3021 */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3021 - the grail reader asks a capped reader for every shot again",
     "file": "bible.html",
     "find": "        if (ans.cap) capWhy = refusedWhy = _rfG;   /* REG-3021 - and the cap is why the rest is not read */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3021 - the grid counter asks a capped reader for every shot again",
     "file": "bible.html",
     "find": "        if (ans.cap) capWhy = errWhy = ans.refused;   /* REG-3021 */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3021 - the tally reader keeps asking a capped reader for its other passes",
     "file": "bible.html",
     "find": "    if (_capT) break;   /* REG-3021 - the reader is at its cap: no more passes */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3021 - the tally reader asks a capped reader again for the next shot of the batch",
     "file": "bible.html",
     "find": "  var _capT = (why && why.cap) ? String(why.text || 'the reader is at its cap') : '';\n",
     "replace": "  var _capT = '';\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3021 - the vault intake no longer stops for a subscription cap",
     "file": "bible.html",
     "find": "    function _aiIsLimit(d){ return window._intakeIsCap(0, d); }",
     "replace": "    function _aiIsLimit(d){ return !!(d && d.error && +d.status === 402); }",
     "matches": 1, "needs": "node"},
    {"why": "REG-3021 - a subscription cap is explained as the API key's monthly cap again",
     "file": "bible.html",
     "find": "    function _aiLimitMsg(d){ if (d && d.error === 'subscription-cap') return",
     "replace": "    function _aiLimitMsg(d){ if (false) return",
     "matches": 1, "needs": "node"},
    {"why": "REG-3021 - the vault intake's first read does not raise its stop on a cap",
     "file": "bible.html",
     "find": "        if (_ansV.cap) _aiLimitSeen(_ansV.data);   /* REG-3021 - a cap stops the batch (v438): the shots after it are not asked */\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3021 - a usage limit's reason (the website's `detail`) is dropped from the refusal again",
     "file": "bible.html",
     "find": "String(data.message || data.detail || data.error)",
     "replace": "String(data.message || data.error)",
     "matches": 1, "needs": "node"},
    {"why": "REG-3024 - a refused daily pick is silent again",
     "file": "bible.html",
     "find": "      _pickNotRead(x.refused || 'the reader answered with no pick'); })",
     "replace": "      })",
     "matches": 1, "needs": "node"},
    {"why": "REG-3024 - a daily pick whose fetch threw is silent again",
     "file": "bible.html",
     "find": "    .catch(function(e){ _pickNotRead(window._intakeThrew(e)); });",
     "replace": "    .catch(function(){});",
     "matches": 1, "needs": "node"},
    {"why": "REG-3024 - the daily pick parses before the status is judged again",
     "file": "bible.html",
     "find": "    .then(function(r){ return window._intakeAnswer(r); })   /* REG-3024 - the answer is read before it is judged (REG-2978) */",
     "replace": "    .then(function(r){ return r.json().then(function(d){ return { data: d, refused: null }; }); })",
     "matches": 1, "needs": "node"},
    {"why": "REG-3024 - a refused day keeps its stamp and is not asked again until tomorrow",
     "file": "bible.html",
     "find": "    try{ window.LSR.removeItem('d2r_createNowAiDate'); }catch(e){}\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3024 - the card's pick line never says a pick was not read",
     "file": "bible.html",
     "find": "  if (notRead) return '<div class=\"cn-ai cn-ai-notread\">",
     "replace": "  if (false) return '<div class=\"cn-ai cn-ai-notread\">",
     "matches": 1, "needs": "node"},
    {"why": "REG-3024 - renderCreateNow draws the pick line by hand again",
     "file": "bible.html",
     "find": "  var aiBanner = window._createNowAiBanner(ai, window._createNowAiNotRead);   /* REG-3024 */",
     "replace": "  var aiBanner = ai ? ('<div class=\"cn-ai\">💡 <b>Today’s pick:</b> '+_askMd(ai)+'</div>') : '';",
     "matches": 1},
    {"why": "REG-3024 - the not-read line has no form for a read with no count",
     "file": "bible.html",
     "find": "  if (n == null) return 'not read' + (w ? ' \\u2014 ' + w : '');   /* REG-3024 - one read with no count (the daily pick) */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
