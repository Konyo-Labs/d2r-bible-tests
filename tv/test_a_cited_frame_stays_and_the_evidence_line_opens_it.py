# -*- coding: utf-8 -*-
"""A cited picture stays when its reel is released, and the evidence line opens it.

His ruling 2026-09-27: the standing line (PROVEN 12/12 · N sessions) is clickable and opens the
existing lightbox on that item's looks. A frame those looks cite is kept when the reel goes. An
uncited frame of the same reel goes. The tombstone says what it kept and why. A picture that
cannot be served says so — never a blank.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable; enable()

import frame_authority as FA
import reel_retention as RR
import vault_evidence as VE

NODE = shutil.which("node")
BIBLE = os.path.join(ROOT, "bible.html")
BEGIN = "⟦VAULT EVIDENCE LINE BEGIN⟧"
END = "⟦VAULT EVIDENCE LINE END⟧"
TILE = "window._vaultEvidenceBtn(p.n)"

HARNESS = r"""
var window = globalThis, STORE = {};
window.LSR = {
  getItem: function(k){ return Object.prototype.hasOwnProperty.call(STORE, k) ? STORE[k] : null; },
  setItem: function(k, v){ STORE[k] = String(v); } };
function _provAll(){
  try { var v = JSON.parse(window.LSR.getItem('d2r_vaultProv') || '{}'); return v || {}; }
  catch (e) { return {}; } }
function jsArg(t){ return String(t).replace(/\\/g,'\\\\').replace(/'/g,"\\'"); }
function esc(t){ return String(t == null ? '' : t); }
var OPENED = [];
window._tvdOpenFrame = function(id, meta){
  OPENED.push({ id: id, title: meta && meta.title, src: meta && meta.src }); };
"""

BODY = r"""
STORE['d2r_vaultProv'] = JSON.stringify({
  Shako: {
    tier: 'PROVEN', successes: 12, trials: 12, sessions: ['s0', 's1', 's2'],
    source: 'stash', by: 'evidence', at: '2026-09-27T12:00:00Z',
    looks: [
      { id: 's0', frame: 'cited.jpg', conf: 0.91, cell: { tab: 'personal', x: 3, y: 4 }, at: '2026-09-27T12:00:00Z' },
      { id: 's1', frame: 'second.jpg', conf: 0.88, cell: { tab: 'personal', x: 3, y: 4 } },
      { id: 's2', frame: null, conf: 0.4 }
    ]
  },
  Gone: {
    tier: 'PROVEN', successes: 2, trials: 2, sessions: ['g0'],
    looks: [{ id: 'g0', frame: 'gone.jpg', conf: 0.9, released: true, crop: 'crops/gone.jpg' }]
  },
  Rebuilt: {
    tier: 'WATCHED', successes: 1, trials: 1, sessions: ['s_1'], source: 'stash', by: 'evidence',
    looks: [{ id: 's_1#0', frame: 'f_1787508821310.jpg', conf: 0.9 }]
  },
  Normal: {
    mule: 'uni-armor', source: 'stash', by: 'reader', at: '2026-09-28T12:00:00Z',
    looks: [{ id: 's_a', frame: 'f_1787508821311.jpg', conf: 0.9 }, { id: 's_b', frame: 'f_1787508821312.jpg', conf: 0.88 }],
    gate: { pass: true, why: 'corroborated across 2 looks', looks: 2 }
  },
  Receipt: { kind: 'owned', source: 'kai-register', looks: [{ id: 's_r', frame: 'f_1.jpg', conf: 0.9 }] },
  NoSession: { tier: 'PROVEN', successes: 12, trials: 12, looks: [{ id: null, frame: 'orphan.jpg', conf: 0.9 }] }
});
var line = window._vaultEvidenceLine('Shako');
var first = window._vaultOpenEvidence('Shako', 0);
var second = window._vaultEvidenceStep(1);
var missing = window._vaultEvidenceStep(1);
var released = window._vaultOpenEvidence('Gone', 0);
var btn = window._vaultEvidenceBtn('Shako');
var rebuilt = window._vaultOpenEvidence('Rebuilt', 0);
var orphan = window._vaultOpenEvidence('NoSession', 0);
var srcOf = window._vaultLookSrc({ frame: 'f_1.jpg', session: 'reel_s_9#3' });
var srcs = {
  bareMs: window._vaultLookSrc({ frame: '1788820373017', session: 's_1786385768689_67392' }),
  bareMsReel: window._vaultLookSrc({ frame: '1788820373017', session: 'reel_s_1786385768689_67392' }),
  fPrefixed: window._vaultLookSrc({ frame: 'f_1788820373017.jpg', session: 's_9_9' }),
  filename: window._vaultLookSrc({ frame: 'cited.jpg', session: 's0' }),
  reelRel: window._vaultLookSrc({ frame: 'reel_s_9_9/f_777' }),
  reelRelJpg: window._vaultLookSrc({ frame: 'reel_s_9_9/f_777.jpg', session: null }),
  noReel: window._vaultLookSrc({ frame: '1788820373017', session: null }),
  noFrame: window._vaultLookSrc({ frame: '', session: 's_9_9' })
};
process.stdout.write(JSON.stringify({
  line: line, first: first, second: second, missing: missing, released: released,
  opened: OPENED, btn: btn, rebuilt: rebuilt, orphan: orphan, srcOf: srcOf, srcs: srcs,
  lines: { normal: window._vaultEvidenceLine('Normal'), receipt: window._vaultEvidenceLine('Receipt') }
}));
"""


def _cut():
    with io.open(BIBLE, encoding="utf-8") as fh:
        src = fh.read()
    assert src.count(BEGIN) == 1 and src.count(END) == 1
    i = src.index(BEGIN)
    j = src.index(END, i) + len(END)
    return src[src.rfind("\n", 0, i) + 1:src.index("\n", j) + 1]


def _drive():
    prog = HARNESS + _cut() + BODY
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError("the evidence line would not run — UNKNOWN, not passing: %s"
                             % (r.stderr or r.stdout)[-800:])
    return json.loads(r.stdout)


def _look(frame, miss=False):
    row = {"session": "s-" + frame, "frame": frame, "conf": 0.91, "lane": "stash"}
    if miss:
        row["saw"] = "empty"
    return row


class ACitedFrameStaysAndTheLineOpensIt(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cited-frame-")
        self.hist = os.path.join(self.tmp, "hist")
        self.reel = os.path.join(self.hist, "reel_s_9_1")
        os.makedirs(self.reel)
        for name in ("cited.jpg", "miss.jpg", "other.jpg"):
            with io.open(os.path.join(self.reel, name), "w", encoding="utf-8") as fh:
                fh.write(name)
        self.ledger = os.path.join(self.tmp, "vault_accum.json")
        doc = {"owned": [{"name": "Shako", "lane": "stash", "kind": "item", "witnesses": [
            _look("cited.jpg"), _look("miss.jpg", miss=True)]}]}
        self.before = json.dumps(doc).encode("utf-8")
        with io.open(self.ledger, "wb") as fh:
            fh.write(self.before)
        self.his = os.path.join(HERE, "reel_tombstones.json")
        self.his_stat = os.stat(self.his) if os.path.isfile(self.his) else None

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _wit(self, frames):
        return {"ok": True, "haveIndex": True, "frames": set(), "cited": set(frames)}

    def _seal(self):
        return {"s_9_1": {"extracted": [], "rows": 0, "examinedEmpty": True,
                          "triagePanels": 0, "probedPanels": 0}}    # REG-2042 - the every-panel denominator

    def test_a_cited_frame_stays_and_an_uncited_one_goes(self):
        got = VE.cited_frames(self.ledger)
        self.assertTrue(got["ok"], got)
        self.assertEqual(["cited.jpg"], got["frames"])
        self.assertNotIn("miss.jpg", got["frames"])
        with io.open(self.ledger, "rb") as fh:
            self.assertEqual(self.before, fh.read(), "citing frames wrote the witness ledger")
        note = RR.release_uncited(self.reel, self._seal(), self._wit(got["frames"]))
        self.assertTrue(note["ok"], note)
        self.assertTrue(os.path.isfile(os.path.join(self.reel, "cited.jpg")))
        self.assertFalse(os.path.isfile(os.path.join(self.reel, "other.jpg")))
        self.assertFalse(os.path.isfile(os.path.join(self.reel, "miss.jpg")))
        self.assertEqual(["cited.jpg"], [k["frame"] for k in note["kept"]])
        self.assertIn("cited as vault evidence", note["kept"][0]["why"])
        self.assertEqual(["miss.jpg", "other.jpg"], note["gone"])
        rows = RR._tombstone(self.hist, [{
            "reel": "reel_s_9_1", "mb": 0.1, "pages": 1, "why": "released",
            "kept": note["kept"]}])
        self.assertEqual(["cited.jpg"], [k["frame"] for k in rows[0]["kept"]])
        self.assertIn("cited as vault evidence", rows[0]["kept"][0]["why"])
        stone = os.path.join(self.tmp, "reel_tombstones.json")
        self.assertTrue(os.path.isfile(stone), "the tombstone was not written beside the temp reel")
        with io.open(stone, encoding="utf-8") as fh:
            saved = json.load(fh)
        self.assertEqual("cited.jpg", saved["reels"][0]["kept"][0]["frame"])
        if self.his_stat is not None:
            now = os.stat(self.his)
            self.assertEqual(self.his_stat.st_mtime, now.st_mtime)
            self.assertEqual(self.his_stat.st_size, now.st_size)

    def test_an_unreadable_ledger_releases_nothing(self):
        with io.open(self.ledger, "wb") as fh:
            fh.write(b"{")
        got = VE.cited_frames(self.ledger)
        self.assertFalse(got["ok"])
        self.assertIsNone(got["frames"])
        note = RR.release_uncited(self.reel, self._seal(),
                                  {"ok": True, "haveIndex": True, "frames": set(), "cited": None})
        self.assertFalse(note["ok"])
        self.assertIsNone(note["gone"])
        for name in ("cited.jpg", "miss.jpg", "other.jpg"):
            self.assertTrue(os.path.isfile(os.path.join(self.reel, name)))

    def test_a_missing_ledger_cites_nothing_and_is_not_unknown(self):
        got = VE.cited_frames(os.path.join(self.tmp, "no-such.json"))
        self.assertTrue(got["ok"])
        self.assertEqual([], got["frames"])
        idx = FA.witness_index(os.path.join(self.tmp, "empty-root"))
        os.makedirs(os.path.join(self.tmp, "empty-root"), exist_ok=True)
        idx = FA.witness_index(os.path.join(self.tmp, "empty-root"))
        self.assertTrue(idx["ok"])
        self.assertEqual(set(), idx["cited"])

    @unittest.skipIf(NODE is None, "node is absent — the evidence line was not driven")
    def test_the_evidence_line_opens_the_right_frames(self):
        with io.open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(1, src.count(TILE), "the vault tile does not open the evidence line")
        out = _drive()
        self.assertEqual("PROVEN 12/12 · 3 sessions", out["line"])
        self.assertEqual("cited.jpg", out["first"]["frame"])
        self.assertEqual("second.jpg", out["second"]["frame"])
        self.assertIn("personal 3,4", out["first"]["title"])
        self.assertIn("conf 0.91", out["first"]["title"])
        self.assertEqual(["cited.jpg", "second.jpg"], [o["id"] for o in out["opened"][:2]])
        self.assertEqual("picture missing: UNKNOWN", out["missing"]["say"])
        self.assertIsNone(out["missing"]["frame"])
        self.assertNotIn("", [o["id"] for o in out["opened"]])
        self.assertEqual("frame released — crop kept", out["released"]["say"])
        self.assertEqual("crops/gone.jpg", out["released"]["frame"])
        self.assertIn("PROVEN 12/12", out["btn"])
        self.assertIn("window._vaultOpenEvidence", out["btn"])

    @unittest.skipIf(NODE is None, "node is absent — the evidence line was not driven")
    def test_the_click_names_the_reel_the_picture_lives_in(self):
        """#41 rank 3 (reproduced: 0 of 109 cited pictures reachable): every banked evidence frame lives at
        hist/reel_<session>/<frame>, the lightbox was handed the bare id, and every click opened 'frame missing'. The
        click now passes the exact path (the rebuild's visit id 's_1#0' loses its bucket), and that path resolves through
        the console's own hist server against a fixture shelf holding the real f_<ms>.jpg naming."""
        out = _drive()
        self.assertEqual("tv/frames/hist/reel_s0/cited.jpg", out["opened"][0]["src"], "the click carries no reel path (v3182 again)")
        self.assertEqual("tv/frames/hist/reel_s_1/f_1787508821310.jpg", out["rebuilt"]["src"], "the visit id's #bucket was not stripped")
        self.assertEqual(out["rebuilt"]["src"], [o for o in out["opened"] if o["id"] == "f_1787508821310.jpg"][0]["src"])
        self.assertIsNone(out["orphan"]["src"], "a look with no session was given a reel it does not name")
        self.assertEqual("tv/frames/hist/reel_s_9/f_1.jpg", out["srcOf"])
        # the JOIN: '/hist/' + the path the chain derives, served by control_app's own path join
        import control_app as CA
        hist = os.path.join(self.tmp, "hist2")
        os.makedirs(os.path.join(hist, "reel_s_1"))
        with io.open(os.path.join(hist, "reel_s_1", "f_1787508821310.jpg"), "wb") as fh:
            fh.write(b"JPEGBYTES")
        rel = out["rebuilt"]["src"][len("tv/frames/hist/"):]
        h = CA.Handler.__new__(CA.Handler)
        got = {}
        h.path = "/hist/" + rel
        h._json = lambda code, obj: got.update(code=code, body=obj)
        h.send_response = lambda code: got.update(code=code)
        h.send_header = lambda k, v: None
        h.end_headers = lambda: None
        h.wfile = io.BytesIO()
        real = CA.HIST_DIR
        CA.HIST_DIR = hist
        try:
            h._serve_hist(rel)
        finally:
            CA.HIST_DIR = real
        self.assertEqual(200, got.get("code"), "the hist server did not resolve the path the click carries: %r" % got)
        self.assertEqual(b"JPEGBYTES", h.wfile.getvalue())

    @unittest.skipIf(NODE is None, "node is absent — the evidence line was not driven")
    def test_a_stored_filename_stays_bare_and_a_bare_millisecond_is_reel_footage(self):
        """REG-2220 prefixed f_ onto every token that did not already start with it, so a
        stored filename cited.jpg was opened as f_cited.jpg. A bare millisecond is reel
        footage and lives as f_<ms>.jpg. A token that is already a filename is that file.
        An already-prefixed name is not prefixed again, and a frame with no reel stays null."""
        out = _drive()["srcs"]
        self.assertEqual("tv/frames/hist/reel_s0/cited.jpg", out["filename"])
        self.assertEqual("tv/frames/hist/reel_s_1786385768689_67392/f_1788820373017.jpg", out["bareMs"])
        self.assertEqual("tv/frames/hist/reel_s_1786385768689_67392/f_1788820373017.jpg", out["bareMsReel"])
        self.assertEqual("tv/frames/hist/reel_s_9_9/f_1788820373017.jpg", out["fPrefixed"])
        self.assertEqual("tv/frames/hist/reel_s_9_9/f_777.jpg", out["reelRel"])
        self.assertEqual("tv/frames/hist/reel_s_9_9/f_777.jpg", out["reelRelJpg"])
        self.assertIsNone(out["noReel"])
        self.assertIsNone(out["noFrame"])

    @unittest.skipIf(NODE is None, "node is absent — the evidence line was not driven")
    def test_a_witnessed_filing_says_its_gate_and_that_its_tier_is_unknown(self):
        """#41 rank 10: the normal door's row carries looks and its gate, never a tier; its line read as if tiers did not
        apply. It now says the gate beside the looks and that the tier is UNKNOWN; a receipt keeps its own words."""
        out = _drive()
        # (this harness cuts the evidence line alone, so `who` is the raw source; on the page it is _ownedProvSourceSay's words)
        self.assertEqual("filed · stash · 2 looks · gate passed on 2 · tier UNKNOWN", out["lines"]["normal"])
        self.assertEqual("kai-register · 1 look", out["lines"]["receipt"], "a receipt's line must not claim a tier or a gate")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "a cited frame is released with the rest of its reel",
        "file": "frame_authority.py",
        "find": "    if os.path.basename(frame_path) in set(_cited or ()):\n",
        "replace": "    if False and os.path.basename(frame_path) in set(_cited or ()):\n",
        "matches": 1,
    },
    {
        "why": "a miss is cited, so a frame that did not see the item is kept",
        "file": "vault_evidence.py",
        "find": "        for shot in shots:\n",
        "replace": ("        for shot in [e for row in rows for e in "
                    "(row.get('witnesses') if isinstance(row.get('witnesses'), list) else [])]:\n"),
        "matches": 1,
    },
    {
        "why": "a picture that cannot be served opens blank instead of saying UNKNOWN",
        "file": "bible.html",
        "find": "    if (!look.frame) return { ok: false, frame: null, say: 'picture missing: UNKNOWN', title: 'picture missing: UNKNOWN · ' + title, ids: looks.map(function(k){ return k.frame || null; }) };\n",
        "replace": "    if (!look.frame) return { ok: false, frame: null, say: '', title: '', ids: looks.map(function(k){ return k.frame || null; }) };\n",
        "matches": 1,
    },
    {
        "why": "the tombstone forgets which frames it kept",
        "file": "reel_retention.py",
        "find": "            rec[\"kept\"] = c[\"kept\"]\n",
        "replace": "            rec[\"why\"] = c.get(\"why\")\n",
        "matches": 1,
    },
    {
        "why": "#41 rank 3 - the click hands the lightbox the bare frame id again, so every evidence picture opens 'frame missing'",
        "file": "bible.html",
        "find": "    var srcL = window._vaultLookSrc(look);\n",
        "replace": "    var srcL = null;\n",
        "matches": 1,
    },
    {
        "why": "#41 rank 3 - the visit id's #bucket is not stripped, so the reel path names a directory that does not exist",
        "file": "bible.html",
        "find": "    var s = sid.replace(/#\\d+$/, '').replace(/^reel_/, '');\n",
        "replace": "    var s = sid.replace(/^reel_/, '');\n",
        "matches": 1,
    },
    {
        "why": "REG-2278 - every frame token is prefixed f_ again, so a stored filename no longer resolves",
        "file": "bible.html",
        "find": "(/^\\d+$/.test(stem) ? ('f_' + stem) : stem)) + '.jpg';\n",
        "replace": "('f_' + stem)) + '.jpg';\n",
        "matches": 1,
    },
    {
        "why": "#41 rank 10 - a witnessed filing's line stops saying its tier is UNKNOWN",
        "file": "bible.html",
        "find": "      + ' · tier UNKNOWN';\n",
        "replace": "      + '';\n",
        "matches": 1,
    },
]
