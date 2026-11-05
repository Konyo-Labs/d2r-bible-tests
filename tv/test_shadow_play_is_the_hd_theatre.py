# -*- coding: utf-8 -*-
"""REG-3204 (GrokBot on v3864: "Shadow Play path still _shadowSessionsPlay slideshow; not HD #th-film") - SHADOW PLAY IS
THE SAME HD THEATRE AS REGULAR PLAY.

His ask: Play on a shadow is the theatre he plays his own reels in. MEASURED in source on v3864: _shadowSessionsPlayTick
wrote `<img class="ssv-img">` - the digest's 160 px key frame - into #ssv-stage, a strip inside the sessions list
(#shadow-sess-ov). The theatre (#theatre, #th-film) never opened, and no frame was ever shown larger than its thumbnail.

THE LAW, on the SHIPPED player (the list renderer that arms it, _shadowSessionsPlay/Tick/Stop/Speed and the theatre
functions _shadowTheatreUp/Show/Down/Toggle/Step, cut from control_ui.html and run in node over a fake page):
  1. Play lifts the theatre: #theatre shown, body.theatre-open + body.shadow-theatre, their list hidden, and the stage
     holds none of this PC's reels (TH.beats empty);
  2. each step paints #th-film with that frame's served picture AT ONCE, then asks the OWNER's console (the origin on
     the shadow snapshot, the v3849 (a) leg) for the HD copy at /hist/<id>.jpg?w=1280, and the caption says which
     picture is on screen and why; an HD answer that lands after the walk moved on never paints over the next frame;
  3. no owner address (or one that is not an http origin) asks nobody and says so;
  4. ✕ goes back one layer, to their sessions list, and the walk stops; a full close (thClose) ends a shadow reel too,
     and leaving the shadow (which closes their list) closes the theatre with their reel on it;
  5. the CSS lifts the theatre above the shadow frame (945) and their list (975), and does not draw the controls that act
     on this PC's reels.
A missing node raises; this law does not skip. RED_PROOF below.
"""
import base64
import io
import json
import os
import re
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
from cb_node_harness import NODE  # noqa: E402
import test_a_shadow_shelf_says_playtime_and_plays_served_frames as BASE  # noqa: E402

UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
FNS = BASE.FNS + ["  function _shadowOwnerOrigin(){", "  function _shadowTheatreHd(id, origin){",
                  "  function _shadowTheatreUp(ix){", "  function _shadowTheatreShow(i){",
                  "  function _shadowTheatreDown(back){", "  function _shadowTheatreToggle(){",
                  "  function _shadowTheatreStep(d){"]
LINES = BASE.LINES + ["  var _SSV_ORIGIN = "]
A = base64.b64encode(b"\xff\xd8\xffA-old").decode("ascii")
B = base64.b64encode(b"\xff\xd8\xffB-new").decode("ascii")
ID_OLD, ID_NEW = "1_1792000000000", "2_1792000030000"
ORIGIN = "http://owner-pc.example:17772"
STAGE_HIDE = 'body[data-view="sessions"] .stage { display: none !important; }'
LIFT = "body.shadow-theatre #theatre { position: fixed !important; inset: 0 !important; z-index: 976 !important;"
HOOK = "    try { if (TH.shadowReel) _shadowTheatreDown(false); } catch (e) {}   /* REG-3204 - a full close ends a shadow reel too */\n"

HARNESS = r"""
const CFG = JSON.parse(process.env.SSV_CFG);
const TIMERS = []; let tid = 1;
const CLS = new Set();
function El(id){ this.id = id; this.innerHTML = ''; this.textContent = ''; this.hidden = true; this.style = {}; this.attrs = {};
  this._src = ''; }
Object.defineProperty(El.prototype, 'src', { get(){ return this._src; }, set(v){ this._src = String(v); } });
El.prototype.removeAttribute = function(k){ if (k === 'src') this._src = ''; };
const REG = {};
['ssv-stage','ssv-play','ssv-speed','theatre','th-film','th-caption','th-sess','th-ribbon','th-play','th-speed',
 'shadow-sess-ov'].forEach((k) => REG[k] = new El(k));
REG['shadow-sess-ov'].hidden = false;
REG['shadow-eng'] = { id: 'shadow-eng', contentWindow: { _tvdShadow: { origin: CFG.origin } } };
const PROBES = [];
function Image(){ PROBES.push(this); this.src = ''; this.onload = null; this.onerror = null; }
const TH = { open: false, beats: [{ frame: 'this-pc/f.jpg' }], allBeats: [{}], i: 3 };
const CALLS = [];
const env = {
  window: { _shadowWho: 'ALT' }, TH: TH, Image: Image,
  document: { getElementById: (id) => REG[id] || null,
              body: { classList: { add: (...c) => c.forEach((x) => CLS.add(x)), remove: (...c) => c.forEach((x) => CLS.delete(x)),
                                   contains: (c) => CLS.has(c) } } },
  setTimeout: (fn, ms) => { const id = tid++; TIMERS.push({ id, fn, ms }); return id; },
  clearTimeout: (id) => { const i = TIMERS.findIndex((t) => t.id === id); if (i >= 0) TIMERS.splice(i, 1); },
  fetch: (url) => { CALLS.push(String(url)); return Promise.resolve({ json: () => Promise.resolve({}) }); },
  thLit: () => {}, thClose: () => { CALLS.push('thClose'); }, thCinema: () => {}, _consoleShadowUp: () => true,
};
const F = new Function('env', 'with (env) {\n' + CFG.code + '\nreturn { html: _shadowSessionsHtml, play: _shadowSessionsPlay,'
  + ' down: _shadowTheatreDown, step: _shadowTheatreStep, toggle: _shadowTheatreToggle, close: _shadowSessionsClose }; }')(env);
function look(){ return { film: REG['th-film'].src, cap: REG['th-caption'].textContent, sess: REG['th-sess'].textContent,
  theatreHidden: REG['theatre'].hidden, listHidden: REG['shadow-sess-ov'].hidden, cls: Array.from(CLS).sort(),
  reel: !!TH.shadowReel, beats: TH.beats.length, open: TH.open, probes: PROBES.map((p) => p.src),
  on: !!(env.window._ssvPlay && env.window._ssvPlay.on) }; }
F.html(CFG.record);
const out = {};
out.started = F.play();
out.first = look();
if (PROBES[0] && PROBES[0].onload) PROBES[0].onload();
out.firstHd = look();
if (TIMERS.length) TIMERS.pop().fn();
out.second = look();
if (PROBES[1] && PROBES[1].onerror) PROBES[1].onerror();
out.secondErr = look();
if (PROBES[0] && PROBES[0].onload) PROBES[0].onload();
out.lateHd = look();
out.down = F.down(true);
out.after = look();
out.timers = TIMERS.length;
const before = CALLS.filter((c) => c === 'thClose').length;
F.play();
F.close();
out.leaveCloses = CALLS.filter((c) => c === 'thClose').length - before;
out.calls = CALLS;
process.stdout.write(JSON.stringify(out));
"""


def _record():
    return {"ok": True, "owner": "ALT", "ago": "2 min ago", "sessions": [
        {"t0": 1792000030000, "t1": 1792000090000, "reads": 2, "names": [], "frames": [{"id": ID_NEW, "jpg": B}]},
        {"t0": 1792000000000, "t1": 1792000020000, "reads": 1, "names": [], "frames": [{"id": ID_OLD, "jpg": A}]},
    ]}


def _drive(origin):
    if NODE is None:
        raise AssertionError("node is not installed on this PC - this law runs the shipped player in node and does not skip")
    code = "\n".join([BASE._line(UI, x) for x in LINES] + [BASE._cut(UI, x) for x in FNS])
    env = dict(os.environ, SSV_CFG=json.dumps({"code": code, "record": _record(), "origin": origin}))
    p = subprocess.run([NODE, "-"], input=HARNESS.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       env=env, timeout=60)
    if p.returncode != 0:
        raise AssertionError("node failed: %s" % p.stderr.decode("utf-8", "replace")[-1500:])
    return json.loads(p.stdout.decode("utf-8"))


class ShadowPlayIsTheHdTheatre(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.hd = _drive(ORIGIN)
        cls.bare = _drive(None)
        cls.bad = _drive("javascript:alert(1)")

    def test_play_lifts_the_theatre_and_holds_none_of_this_pcs_reels(self):
        f = self.hd["first"]
        self.assertTrue(self.hd["started"])
        self.assertFalse(f["theatreHidden"], "the theatre never opened: %r" % f)
        self.assertIn("theatre-open", f["cls"], f)
        self.assertIn("shadow-theatre", f["cls"], f)
        self.assertTrue(f["listHidden"], "their sessions list stayed over the theatre: %r" % f)
        self.assertTrue(f["reel"] and f["open"], f)
        self.assertEqual(f["beats"], 0, "this PC's reel stayed on the stage under theirs: %r" % f)
        self.assertIn("ALT", f["sess"])
        self.assertIn("read only", f["sess"])

    def test_each_step_shows_the_served_frame_then_the_owners_hd_copy(self):
        f = self.hd["first"]
        self.assertEqual(f["film"], "data:image/jpeg;base64," + A, "the frame's own picture was not on the film at once: %r" % f)
        self.assertEqual(f["probes"], [ORIGIN + "/hist/" + ID_OLD + ".jpg?w=1280"], f)
        self.assertIn("asking ALT", f["cap"])
        h = self.hd["firstHd"]
        self.assertEqual(h["film"], ORIGIN + "/hist/" + ID_OLD + ".jpg?w=1280", "the HD copy never reached the film: %r" % h)
        self.assertIn("HD, from ALT", h["cap"])
        self.assertIn("frame 1 of 2", h["cap"])
        s = self.hd["second"]
        self.assertEqual(s["film"], "data:image/jpeg;base64," + B, s)
        self.assertEqual(s["probes"][-1], ORIGIN + "/hist/" + ID_NEW + ".jpg?w=1280", s)
        e = self.hd["secondErr"]
        self.assertEqual(e["film"], "data:image/jpeg;base64," + B, e)
        self.assertIn("did not answer", e["cap"])
        late = self.hd["lateHd"]
        self.assertEqual(late["film"], "data:image/jpeg;base64," + B,
                         "a late HD answer for frame 1 painted over frame 2: %r" % late)
        self.assertEqual([c for c in self.hd["calls"] if c != "thClose"], [], "play fetched: %r" % self.hd["calls"])

    def test_no_owner_address_asks_nobody_and_says_so(self):
        for run in (self.bare, self.bad):
            f = run["first"]
            self.assertEqual(f["probes"], [], "a shadow with no owner address asked: %r" % f)
            self.assertEqual(f["film"], "data:image/jpeg;base64," + A, f)
            self.assertIn("address is not on this snapshot", f["cap"], f)

    def test_close_goes_back_to_their_list(self):
        a = self.hd["after"]
        self.assertTrue(self.hd["down"])
        self.assertNotIn("shadow-theatre", a["cls"], a)
        self.assertNotIn("theatre-open", a["cls"], a)
        self.assertTrue(a["theatreHidden"], a)
        self.assertFalse(a["listHidden"], "close did not go back to their sessions list: %r" % a)
        self.assertFalse(a["reel"], a)
        self.assertFalse(a["on"], "the walk kept running after close: %r" % a)
        self.assertEqual(a["film"], "", "their frame stayed on the film after close")
        self.assertEqual(self.hd["timers"], 0)
        self.assertEqual(UI.count(HOOK), 1, "thClose does not end a shadow reel")
        self.assertEqual(self.hd["leaveCloses"], 1, "leaving the shadow left their reel on the theatre")

    def test_the_theatre_sits_above_the_shadow_and_hides_this_pcs_controls(self):
        self.assertEqual(UI.count(STAGE_HIDE), 1)
        self.assertEqual(UI.count(LIFT), 1, "the shadow theatre is not lifted to a fixed full window")
        self.assertGreater(UI.index(LIFT), UI.index(STAGE_HIDE),
                           "the lift must come after the rule that hides the stage on Sessions")
        z = int(re.search(r"z-index: (\d+) !important;", LIFT).group(1))
        self.assertGreater(z, 975, "the theatre would sit under their sessions list (975) or frame (945)")
        rule = UI[UI.index(LIFT):]
        rule = rule[:rule.index("{ display: none !important; }") + 1]
        for ctl in ("#th-open-reel", "#th-reclose", "#th-prev-s", "#th-next-s", "#th-mode", "#th-shelf", ".th-more-wrap"):
            self.assertIn(ctl, rule, "%s acts on this PC's reels and is still drawn over a shadow" % ctl)


class TheProofsNameOnePlace(unittest.TestCase):

    def test_each_find_matches_once(self):
        for proof in RED_PROOF:
            self.assertEqual(UI.count(proof["find"]), proof["matches"], proof["why"])


RED_PROOF = [
    {"why": "REG-3204 - Play walks the frames without ever opening the theatre",
     "file": "tv/control_ui.html",
     "find": "    if (typeof _shadowTheatreUp === 'function') _shadowTheatreUp(ix);\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3204 - the walk never paints the theatre's film",
     "file": "tv/control_ui.html",
     "find": "    if (typeof _shadowTheatreShow === 'function') _shadowTheatreShow(p.at - 1);   /* REG-3204 */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3204 - the owner is never asked for the HD frame",
     "file": "tv/control_ui.html",
     "find": "    return origin + '/hist/' + id + '.jpg?w=1280';\n",
     "replace": "    return null;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3204 - a late HD answer paints over the frame the walk has moved to",
     "file": "tv/control_ui.html",
     "find": "    probe.onload = function(){ if (film.__ssvWant === hd) {",
     "replace": "    probe.onload = function(){ if (true) {",
     "matches": 1, "needs": "node"},
    {"why": "REG-3204 - close leaves him on a bare console instead of their list",
     "file": "tv/control_ui.html",
     "find": "      if (ov && _consoleShadowUp()) ov.hidden = false;",
     "replace": "      if (false) ov.hidden = false;",
     "matches": 1, "needs": "node"},
    {"why": "REG-3204 - the shadow theatre sits under their sessions list",
     "file": "tv/control_ui.html",
     "find": "inset: 0 !important; z-index: 976 !important;\n    border-radius: 0; pointer-events: auto !important;",
     "replace": "inset: 0 !important; z-index: 940 !important;\n    border-radius: 0; pointer-events: auto !important;",
     "matches": 1},
    {"why": "REG-3204 - leaving the shadow leaves their reel on this PC's theatre",
     "file": "tv/control_ui.html",
     "find": "    try { if (typeof TH !== 'undefined' && TH.shadowReel && typeof thClose === 'function') thClose(); } catch (eT) {}\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3204 - a full close leaves the shadow reel running",
     "file": "tv/control_ui.html",
     "find": "    try { if (TH.shadowReel) _shadowTheatreDown(false); } catch (e) {}   /* REG-3204",
     "replace": "    try { void 0; } catch (e) {}   /* REG-3204",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
