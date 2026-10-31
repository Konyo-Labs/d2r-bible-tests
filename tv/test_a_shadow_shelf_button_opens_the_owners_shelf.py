# -*- coding: utf-8 -*-
"""v3849 - THE SHELF BUTTON IN A SHADOW OPENS THE OWNER'S SHELF, READ ONLY.

Their board frame is position:fixed over the rail, and the rail does not take clicks, so the
sticky Shelf never saw the press. While a shadow board is up the button is fixed above that
frame. The press opens on shadow-on, shadow-snap or shadow-hub (the frame spends the first
click blurring itself). The opener is the owner's published sessions: one GET of the frames
digest, never this PC's theatre.

The press, the button's own handler and the opener are cut out of control_ui.html and run in
node, program on stdin. RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
NODE = shutil.which("node")
UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()

FNS = ["  function esc(s){", "  function _consoleShadowUp(){", "  function _shelfShadowRefusal(){",
       "  function _shadowSessionsHead(owner){", "  function _shadowSessionsOpen(){"]
LINES = ["  var API = '';", "  window._consoleShadowUp = _consoleShadowUp;", "  var _ssvGen = 0;"]


def _cut(src, sig):
    if src.count(sig) != 1:
        raise AssertionError("%r occurs %d times" % (sig, src.count(sig)))
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


def _line(src, start):
    if src.count(start) != 1:
        raise AssertionError("%r occurs %d times" % (start, src.count(start)))
    i = src.index(start)
    return src[i:src.index("\n", i)]


def _span(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("%r occurs %d times" % (start, src.count(start)))
    if src.count(end) != 1:
        raise AssertionError("%r occurs %d times" % (end, src.count(end)))
    i = src.index(start)
    j = src.index(end)
    if j <= i:
        raise AssertionError("%r is not after %r" % (end, start))
    return src[i:j]


def _block_z(src, start):
    if src.count(start) != 1:
        raise AssertionError("%r occurs %d times" % (start, src.count(start)))
    i = src.index(start)
    j = src.index("}", i)
    found = re.search(r"z-index:\s*(\d+)", src[i:j])
    if not found:
        raise AssertionError("no z-index in %r" % start)
    return int(found.group(1)), src[i:j]


def _code():
    return "\n".join(
        [_line(UI, x) for x in LINES]
        + [_cut(UI, x) for x in FNS]
        + [_span(UI, "  var _bshelf = $('btn-shelf');\n",
                 "  /* v3845 - THE SHELF IN A SHADOW OPENED NOTHING"),
           _span(UI, "  var _bshelfPtrTs = -1e9;\n",
                 "  /* v2446 — SAY IT, AND TELL THE DOCTOR.")]
    )


HARNESS = r"""
const CFG = JSON.parse(process.env.SSB_CFG);
const CALLS = [];
const THEATRE = [];
const classes = new Set();
const REG = {};
function El(tag) {
  this.tagName = tag || 'DIV';
  this._id = '';
  Object.defineProperty(this, 'id', {
    get() { return this._id; },
    set(v) { this._id = String(v); if (v) REG[this._id] = this; },
  });
  this.hidden = false;
  this.innerHTML = '';
  this.textContent = '';
  this.className = '';
  this.type = '';
  this.title = '';
  this.children = [];
  this.style = {};
  this.attrs = {};
  this._ls = {};
  this.addEventListener = (type, fn) => { (this._ls[type] = this._ls[type] || []).push(fn); };
  this.dispatch = (type, ev) => { (this._ls[type] || []).forEach((fn) => fn(ev)); };
  this.setAttribute = (k, v) => { this.attrs[k] = String(v); if (k === 'id') REG[String(v)] = this; };
  this.appendChild = (ch) => { this.children.push(ch); return ch; };
  this.blur = () => { this.blurred = true; };
}
const button = new El('BUTTON');
button.id = 'btn-shelf';
REG['btn-shelf'] = button;
const frame = new El('IFRAME');
frame.id = 'shadow-eng';
REG['shadow-eng'] = frame;
const env = {
  window: {},
  document: {
    body: {
      classList: { contains: (x) => classes.has(x) },
      appendChild: () => {},
    },
    getElementById: (id) => REG[id] || null,
    createElement: (tag) => new El(tag),
  },
  fetch: (url) => {
    CALLS.push(String(url));
    return new Promise(() => {});
  },
  setTimeout: () => 0,
  clearTimeout: () => {},
  TH: { open: false, shelfOpening: false },
  thOpen: () => { THEATRE.push('thOpen'); env.TH.open = true; return Promise.resolve(); },
  thClose: () => { THEATRE.push('thClose'); },
  thShelf: () => { THEATRE.push('thShelf'); },
  toast: (msg) => { THEATRE.push('toast:' + msg); },
  _shelfRefused: () => { THEATRE.push('refused'); },
};
function ev(extra) {
  return Object.assign({ button: 0, ctrlKey: false, timeStamp: 5000, preventDefault() {}, stopImmediatePropagation() {} }, extra || {});
}
function setClasses(list) { classes.clear(); list.forEach((x) => classes.add(x)); }
const run = new Function('env', 'with (env) {\nfunction $(id){ return document.getElementById(id); }\n' + CFG.code + '\n}')(env);
function press(list, who, extra) {
  setClasses(list);
  env.window._shadowWho = who;
  env.TH.open = false;
  const a = CALLS.length, b = THEATRE.length;
  button.dispatch('pointerdown', ev(extra));
  button.dispatch('click', ev({ timeStamp: (extra && extra.timeStamp || 5000) + 100 }));
  const ov = REG['shadow-sess-ov'];
  return { fetches: CALLS.slice(a), theatre: THEATRE.slice(b), hidden: ov ? ov.hidden : null, label: ov ? ov.attrs['aria-label'] : null };
}
const snap = press(['shell-open', 'shadow-snap'], 'Wife PC');
const on = press(['shadow-on'], 'Wife PC');
const none = press([], 'Wife PC');
const right = press(['shadow-on'], 'Wife PC', { button: 2, timeStamp: 9000 });
setClasses(['shadow-hub']);
env.window._shadowWho = 'Wife PC';
env.TH.open = false;
const ha = CALLS.length, hb = THEATRE.length;
const hubRet = button.onclick && button.onclick();
const hub = { fetches: CALLS.slice(ha), theatre: THEATRE.slice(hb), ret: hubRet };
setClasses([]);
env.TH.open = false;
const na = CALLS.length, nb = THEATRE.length;
Promise.resolve(button.onclick && button.onclick()).then(() => {
  const own = { fetches: CALLS.slice(na), theatre: THEATRE.slice(nb) };
  process.stdout.write(JSON.stringify({ snap, on, none, right, hub, own, blurred: !!frame.blurred }));
}).catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""


def _drive():
    if NODE is None:
        raise AssertionError("node is not on this machine - this law does not skip")
    cfg = json.dumps({"code": _code()})
    r = subprocess.run([NODE, "-"], input=HARNESS, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=60, env=dict(os.environ, SSB_CFG=cfg, TZ="UTC", LANG="en_US.UTF-8"))
    if r.returncode != 0:
        raise AssertionError("node failed: %s" % ((r.stderr or r.stdout)[-900:]))
    return json.loads(r.stdout)


class TheShelfButtonOpensTheOwnersShelf(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.got = _drive()

    def test_a_snap_press_opens_the_owners_shelf_and_not_this_pcs_theatre(self):
        snap = self.got["snap"]
        self.assertEqual(snap["fetches"], ["/api/roster-cache?frames=Wife%20PC"], snap)
        self.assertEqual(snap["theatre"], [], "a shadow shelf reached this PC's theatre: %r" % snap["theatre"])
        self.assertIs(snap["hidden"], False, "the owner's shelf did not show")
        self.assertEqual(snap["label"], "Wife PC sessions, read only")
        self.assertTrue(self.got["blurred"], "the press did not blur their frame")

    def test_shadow_on_and_the_hub_still_open_the_same_shelf(self):
        self.assertEqual(self.got["on"]["fetches"], ["/api/roster-cache?frames=Wife%20PC"], self.got["on"])
        self.assertEqual(self.got["on"]["theatre"], [])
        self.assertEqual(self.got["hub"]["fetches"], ["/api/roster-cache?frames=Wife%20PC"], self.got["hub"])
        self.assertEqual(self.got["hub"]["theatre"], [], "the hub click opened this PC's theatre")

    def test_no_shadow_press_fetches_nothing_and_the_button_still_opens_this_pcs_shelf(self):
        self.assertEqual(self.got["none"]["fetches"], [], self.got["none"])
        self.assertEqual(self.got["none"]["theatre"], [], self.got["none"])
        self.assertEqual(self.got["right"]["fetches"], [], "a right press opened the shelf")
        self.assertIn("thOpen", self.got["own"]["theatre"], self.got["own"])
        self.assertEqual(self.got["own"]["fetches"], [], "this PC's shelf fetched the owner's frames")

    def test_the_opener_only_reads_the_published_digest(self):
        src = _cut(UI, "  function _shadowSessionsOpen(){")
        self.assertIn("fetch(API + '/api/roster-cache?frames='", src)
        for banned in ("thOpen", "/hist", "method: 'POST'", 'method: "POST"'):
            self.assertNotIn(banned, src, "the owner's shelf reaches %s" % banned)


class TheButtonSitsAboveTheirFrame(unittest.TestCase):

    def test_the_rule_clears_the_frame_and_stays_under_the_sessions_list(self):
        start = ("body.shell-open.shadow-on #btn-shelf,\n"
                 "body.shell-open.shadow-snap #btn-shelf,\n"
                 "body.shell-open.shadow-hub #btn-shelf {")
        z, blk = _block_z(UI, start)
        self.assertIn("position: fixed", blk)
        self.assertIn("pointer-events: auto !important", blk)
        eng, _ = _block_z(UI, "#shadow-eng { position: fixed;")
        bar, _ = _block_z(UI, "#shadow-bar { position: fixed;")
        ov, _ = _block_z(UI, "#shadow-sess-ov { position: fixed;")
        self.assertGreater(z, eng, "the Shelf stays under their frame")
        self.assertGreater(z, bar, "the Shelf stays under the shadow bar's stacking")
        self.assertLess(z, ov, "the sessions list no longer covers the button")
        self.assertIn("body.shell-open", start)


class TheProofsNameOnePlace(unittest.TestCase):

    def test_each_find_matches_once(self):
        for proof in RED_PROOF:
            self.assertEqual(UI.count(proof["find"]), proof["matches"], proof["why"])


RED_PROOF = [
    {"why": "a shadow-snap press never reaches the Shelf, so the button opens nothing",
     "file": "tv/control_ui.html",
     "find": "      if (!(document.body.classList && (document.body.classList.contains('shadow-on') || document.body.classList.contains('shadow-snap') || document.body.classList.contains('shadow-hub')))) return;\n",
     "replace": "      if (!(document.body.classList && document.body.classList.contains('shadow-on'))) return;\n",
     "matches": 1, "needs": "node"},
    {"why": "the Shelf stays under their frame, so the press never lands",
     "file": "tv/control_ui.html",
     "find": "body.shell-open.shadow-hub #btn-shelf {\n  position: fixed;\n  right: 14px;\n  bottom: 14px;\n  z-index: 970;\n",
     "replace": "body.shell-open.shadow-hub #btn-shelf {\n  position: fixed;\n  right: 14px;\n  bottom: 14px;\n  z-index: 3;\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
