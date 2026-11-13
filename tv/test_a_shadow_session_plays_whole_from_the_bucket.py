# -*- coding: utf-8 -*-
"""#208 (his 11-13 calls) - A SHADOW SESSION THE BUCKET HOLDS PLAYS WHOLE, THE WINDOW FILLED, FROM WHERE PLAY STARTS.

His words (via GrokBot #230): "shadow mode must render full screen and ALL frames of that session locally, and show the
game recording from when play starts". The shadow sessions list asks THIS console which listed sessions the private reel
bucket holds; a held one offers WATCH (the whole session, or its summary), and the player opens over the whole window on
the manifest's start frame (the first D2 logo, else frame 1), steps and plays from there, and closes on Esc. A bucket that
did not answer reads UNKNOWN on every row - never "not uploaded"; a manifest that names no frame says why and plays nothing.

Driven on control_ui.html's shipped code in node, with a stub DOM and a stub fetch. RED_PROOF below.
"""
import io
import json
import os
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

NODE = shutil.which("node")
UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
S1, S2 = "s_1792000000000_1", "s_1793000000000_2"
FR = ["f_17920000%05d.jpg" % i for i in range(5)]


def _cut(src, sig):
    if src.count(sig) != 1:
        raise AssertionError("%r occurs %d times - its body is UNKNOWN, not clean" % (sig, src.count(sig)))
    i = src.index(sig)
    b = src.index("{", i)
    depth = 0
    for j in range(b, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
    raise AssertionError("%r never closed" % sig)


def _span(src, head, tail):
    if src.count(head) != 1 or src.count(tail) != 1:
        raise AssertionError("the player block's ends occur %d / %d times" % (src.count(head), src.count(tail)))
    i, j = src.index(head), src.index(tail)
    if j < i:
        raise AssertionError("the player block's end comes before its start")
    return src[i:j + len(tail)]


def _code():
    return "\n".join([_cut(UI, "  function esc(s){"), "  var _ssvGen = 0;",
                      _span(UI, "  var _SRV = { owner: ''", "  window._shadowReelClose = _shadowReelClose;")])


HARNESS = r"""
const CFG = JSON.parse(process.env.SRV_CFG);
const TIMERS = []; let tid = 1; const REG = {};
function El(tag){ this.tag = tag; this._q = {}; this.attrs = {}; this.hidden = false; this.textContent = ''; this._html = '';
  this.className = ''; this.listeners = {}; this.src = null; this.onclick = null; this.onerror = null; this.id = ''; }
El.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
El.prototype.getAttribute = function(k){ return k in this.attrs ? this.attrs[k] : null; };
El.prototype.removeAttribute = function(k){ if (k === 'src') this.src = null; delete this.attrs[k]; };
El.prototype.addEventListener = function(t, fn){ this.listeners[t] = fn; };
El.prototype.focus = function(){};
El.prototype.querySelector = function(sel){ return this._q[sel] || (this._q[sel] = new El(sel)); };
Object.defineProperty(El.prototype, 'innerHTML', { get(){ return this._html; }, set(v){ this._html = String(v); this._first = null; } });
Object.defineProperty(El.prototype, 'firstChild', { get(){ return this._first || (this._first = new El('first')); } });
const rows = (CFG.rows || []).map((sid) => { const r = new El('row'); r.attrs['data-ssv-session'] = sid; return r; });
const body = new El('body'); body.querySelectorAll = () => rows;
const doc = { getElementById: (id) => REG[id] || null, createElement: (t) => new El(t),
              body: { appendChild: (e) => { REG[e.id] = e; } } };
const fetched = [];
const env = { window: {}, document: doc, API: '', Image: function(){},
  encodeURIComponent: encodeURIComponent, Math: Math, Number: Number, String: String, Array: Array, Date: Date,
  setTimeout: (fn, ms) => { const id = tid++; TIMERS.push({ id, fn }); return id; },
  clearTimeout: (id) => { const i = TIMERS.findIndex((t) => t.id === id); if (i >= 0) TIMERS.splice(i, 1); },
  fetch: (url) => { fetched.push(url); const k = Object.keys(CFG.answers).find((s) => url.indexOf(s) >= 0);
    return k === undefined ? Promise.reject(new Error('no answer')) : Promise.resolve({ json: () => Promise.resolve(CFG.answers[k]) }); } };
const F = new Function('env', 'with (env) {\n' + CFG.code + '\nreturn { decorate: _shadowReelDecorate, open: _shadowReelOpen, close: _shadowReelClose, SRV: _SRV }; }')(env);
const flush = () => new Promise((r) => setTimeout(r, 0));
(async () => {
  const out = {};
  if (CFG.decorate) {
    F.decorate('Dean', body, 0);
    await flush(); await flush(); await flush();
    out.cells = rows.map((r) => { const c = r.querySelector('.ssv-reel'); return { cls: c.className, text: c.textContent, html: c.innerHTML,
                                                                             click: typeof c.firstChild.onclick === 'function' }; });
  }
  if (CFG.open) {
    F.open('Dean', CFG.open);
    await flush(); await flush(); await flush();
    const ov = REG['shadow-reel-ov'];
    const img = ov.querySelector('.srv-stage img');
    out.first = { src: img.src, at: ov.querySelector('.srv-at').textContent, why: ov.querySelector('.srv-why').textContent,
                  hidden: ov.hidden, playing: F.SRV.playing, title: ov.querySelector('.srv-title').textContent };
    if (TIMERS.length) TIMERS.shift().fn();
    out.next = { src: img.src, at: ov.querySelector('.srv-at').textContent };
    ov.listeners.keydown({ key: 'Escape', preventDefault(){}, stopPropagation(){} });
    out.closed = { hidden: ov.hidden, playing: F.SRV.playing, timers: TIMERS.length };
  }
  out.fetched = fetched;
  process.stdout.write(JSON.stringify(out));
})();
"""


def _node(cfg):
    env = dict(os.environ, SRV_CFG=json.dumps(dict(cfg, code=_code())))
    r = subprocess.run([NODE, "-"], input=HARNESS, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=120)
    if r.returncode != 0:
        raise AssertionError("the player harness failed rc=%s\n%s" % (r.returncode, r.stderr[-2000:]))
    return json.loads(r.stdout)


@unittest.skipUnless(NODE, "node is absent - the player is UNMEASURED here, never a pass")
class TheWholeSessionPlayer(unittest.TestCase):

    def test_a_held_session_offers_watch_and_one_not_held_says_so(self):
        out = _node({"decorate": True, "rows": [S1, S2], "answers": {"?reels=": {"ok": True, "sessions": [
            {"slot": "Dean", "session": S1, "mode": "full", "frames": 120, "start": FR[0]}]}}})
        held, absent = out["cells"]
        self.assertIn("WATCH the whole session", held["html"])
        self.assertIn("120 frames", held["html"])
        self.assertTrue(held["click"], "the WATCH button opens nothing")
        self.assertIn("not in the bucket", absent["text"])
        self.assertFalse(absent["click"])

    def test_a_summary_says_it_is_one(self):
        out = _node({"decorate": True, "rows": [S1], "answers": {"?reels=": {"ok": True, "sessions": [
            {"slot": "Dean", "session": S1, "mode": "summary", "frames": 40}]}}})
        self.assertIn("WATCH its summary", out["cells"][0]["html"])

    def test_an_unanswered_bucket_is_unknown_on_every_row_never_not_uploaded(self):
        out = _node({"decorate": True, "rows": [S1, S2],
                     "answers": {"?reels=": {"ok": False, "why": "the reel bucket D2R_ROSTER_FRAMES is not bound to the site"}}})
        for c in out["cells"]:
            self.assertIn("UNKNOWN", c["text"])
            self.assertIn("not bound", c["text"])
            self.assertNotIn("not in the bucket", c["text"], "an unanswered bucket read as a session not uploaded")

    def test_the_player_opens_on_the_start_frame_plays_on_and_closes_on_esc(self):
        x = {"slot": "Dean", "session": S1, "mode": "full", "frames": 5}
        out = _node({"open": x, "answers": {"&session=": {"ok": True, "frames": FR, "start": FR[2]}}})
        first, nxt, closed = out["first"], out["next"], out["closed"]
        self.assertFalse(first["hidden"])
        self.assertIn("frame=" + FR[2], first["src"], "the player did not open on the start frame")
        self.assertIn("frame 3 of 5", first["at"])
        self.assertIn("play starts here", first["at"])
        self.assertTrue(first["playing"], "the player opened paused")
        self.assertIn("frame=" + FR[3], nxt["src"], "playing did not step to the next frame")
        self.assertTrue(closed["hidden"] and not closed["playing"] and closed["timers"] == 0, closed)
        self.assertTrue(any("reel=Dean&session=" + S1 in u and "frame=" not in u for u in out["fetched"]),
                        "the manifest was not asked of this console: %r" % out["fetched"])

    def test_a_reel_with_no_start_opens_on_its_first_frame(self):
        x = {"slot": "Dean", "session": S1, "mode": "summary", "frames": 5}
        out = _node({"open": x, "answers": {"&session=": {"ok": True, "frames": FR, "start": None}}})
        self.assertIn("frame=" + FR[0], out["first"]["src"])

    def test_a_manifest_with_no_frames_says_why_and_plays_nothing(self):
        x = {"slot": "Dean", "session": S1, "mode": "full", "frames": 5}
        out = _node({"open": x, "answers": {"&session=": {"ok": False, "why": "not in the bucket (evicted, or never uploaded)"}}})
        self.assertIn("evicted", out["first"]["why"])
        self.assertFalse(out["first"]["playing"])
        self.assertIsNone(out["first"]["src"])


RED_PROOF = [
    {"why": "#208 - the player opens on frame 1 whatever the manifest says, so a Mac reel plays GeForce NOW's Loading page "
            "for two minutes before the game",
     "file": "tv/control_ui.html",
     "find": "        _SRV.start = st >= 0 ? st : 0;",
     "replace": "        _SRV.start = 0;",
     "matches": 1},
    {"why": "#208 - an unanswered bucket reads as every session not uploaded",
     "file": "tv/control_ui.html",
     "find": "        var ok = !!(d && d.ok === true && Array.isArray(d.sessions));",
     "replace": "        var ok = true; if (!(d && Array.isArray(d.sessions))) d = { ok: true, sessions: [] };",
     "matches": 1},
    {"why": "#208 - Esc no longer closes the player, so the window stays covered",
     "file": "tv/control_ui.html",
     "find": "        if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); _shadowReelClose(); }",
     "replace": "        if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); }",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
