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
back says window._intakeThrew(e). Driven: every door cut from bible.html and run in node over one stubbed fetch, in six
refusal shapes (429 cap JSON, 502 empty, 200 + {error}, 200 HTML, a thrown fetch, a shot that could not be prepared), beside
a clean read and a read that honestly found nothing - so the law can tell the three apart; the engine's real judge poster run
over the real judge, and its body handed to control_app's own refusal row. The vault intake's read is pinned at its line
(read, not run - it is too entangled to cut). RED_PROOF below.
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
        "window._intakeThrew = function(e){", "window._intakeNotReadSay = function(n, why){",
        "  window.aicJudge = async function(file){", "  window.aicUpload = async function(file){",
        "window.setIntake = async function(files){", "function _craftPrepImage(file){", "async function _craftRead(",
        "window.craftIntake = async function(files){", "  window.chronicleShotIntake = async function(files){",
        "  function _chronShotPaint(){", "  window.grailIntake=async function(files){", "  function _grailImportToastOnce(){",
        "function _askEsc(t){", "function _askMd(t){", "window.askBible = function(q){", "async function _tallyRead(",
        "  window.vaultGridCount = async function(files, opts){"]


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
let QUEUE = [], IMGFAIL = false;
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
  fetch: async () => { const a = QUEUE.length > 1 ? QUEUE.shift() : QUEUE[0]; if (a.throw) throw new TypeError(a.throw); return mkResp(a); },
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
};
window._d2rIntakeEndpoint = () => '/api/intake';
window._previewWrap = (f) => f();
window.__allSets = env.__allSets;
window._aiIntakeStart = () => {}; window._aiIntakeStop = () => {};
const F = new Function('env', 'with (env) {\n' + CFG.code + '\nreturn { window: window, tally: _tallyRead, toast: _grailImportToastOnce }; }')(env);
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
    "html200": {"status": 200, "raw": "<html><body>Bad gateway</body></html>"},
    "throw": {"throw": "Failed to fetch"},
    "unprepared": {"status": 200, "body": READ, "imgfail": True},
}
# the words each refusal must carry to the door's report - its own sentence, not a stand-in
SAYS = {"cap429": ["at its cap", "20/20 this hour", "HTTP 429"], "empty502": ["HTTP 502"], "err200": ["overloaded"],
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
        self.assertEqual(len(re.findall(r"window\._intakeRefused\(", code)), 1,
                         "a door asks the refusal rule of a body it parsed itself - the answer reader is the one door")


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
     "find": "    .then(function(r){ return window._intakeAnswer(r); })",
     "replace": "    .then(function(r){ return r.json().then(function(d){ return { data: d, refused: window._intakeRefused(r.status, d) }; }); })",
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
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
