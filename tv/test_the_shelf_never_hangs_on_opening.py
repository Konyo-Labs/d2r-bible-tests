# -*- coding: utf-8 -*-
"""REG-3203 (GrokBot on v3864: his Mac's SHELF sat on "opening the shelf..." while the guest's Shelf filled) - THE SHELF
NEVER HANGS ON OPENING.

What could hold the words up, read in source on v3864:
  * the shelf DOOR (thOpen) awaited a fresh /api/sessions before painting anything, every time - bounded at
    TH_SESSIONS_BOUND_MS (45 s), on a Mac whose list took 44 s to build at boot (his /api/status shelfPrewarm.ms 44303)
    - and then thShelf asked a second time, so a reopen with runs already in hand still waited;
  * a wait that is overtaken (TH.gen moved) returns without painting, and a timer WebKit throttles in a hidden window
    runs late, so the placeholder had nothing that would ever replace it;
  * the placeholder is a `.sh-empty-hero` box, so the beat called it the legitimate empty shelf and console_doctor
    answered OK, "no runs to show yet - the correct state", about a shelf that was stuck.

THE LAW, on the SHIPPED thOpen / thShelf / _shelfOpeningWatch / _shelfUnknownPaint (cut from control_ui.html, run in
node on a virtual clock), the shipped beat block, and console_doctor's row:
  1. a door opened with runs in hand returns at once - it never asks /api/sessions before painting;
  2. both "opening" placeholders are marked .sh-opening with when they began, and arm the watch;
  3. a placeholder still there at TH_SHELF_OPEN_BOUND_MS becomes the UNKNOWN shelf (why, ask again, close) and the
     Doctor is told (ui_fault shelf-open-stuck); a shelf that already painted, or was closed, is left alone;
  4. the beat publishes opening + its age and never counts an opening shelf as the empty one;
  5. console_doctor: opening past its bound is MISSING, within it OK, with no start stamp UNKNOWN.
  6. (adversarial review of the first cut, reproduced) THE UNKNOWN SHELF IS NOT THE EMPTY ONE EITHER. What the watch
     turns a stuck opening into is `.sh-empty-hero.sh-unknown`, which `.sh-empty-hero:not(.sh-opening)` still matched:
     emptyHero=true, and the Doctor answered OK "no runs to show yet - the correct state" within 60 s of the stuck shelf.
     The beat now publishes unknown + the page's why, and the row says MISSING. Proven as one chain: the shipped watch's
     painted shelf -> the shipped beat (its selector matched by CLASSES, never by its spelling) -> the Doctor's row.
  7. [[stale-reading]] openingS is the age at the beat; a beat may be 300 s old. 10 s on a 280-s-old beat was printed
     "10s so far"; now past the bound only once the beat's age is added is UNKNOWN, inside it OK counting that age.
A missing node raises; this law does not skip. RED_PROOF below.
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
from cb_node_harness import NODE  # noqa: E402
import test_the_shelf_publishes_where_it_is_not_just_that_it_is_full as SHB  # noqa: E402

UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
DOC = io.open(os.path.join(HERE, "console_doctor.py"), encoding="utf-8").read()
FNS = ["  async function thOpen(){", "  function thShelf(force){", "  function _shelfUnknownPaint(ov, why){",
       "  function _shelfStaleNote(ov, why){", "  function esc(s){", "  function _shelfOpeningWatch(){"]
LINES = ["  var TH_SHELF_OPEN_BOUND_MS = "]
DOOR_MARK = ('<div class="sh-empty-hero sh-opening" data-since="\' + Date.now() + \'"><div class="she-lead">opening the '
             'shelf…</div></div>\';')
LOAD_MARK = ('<div class="sh-empty-hero sh-opening" data-since="\' + Date.now() + \'"><div class="she-lead">\'\n'
             "        + (TH.sessionsFailWhy ? 'asking the console again")


def _cut(sig):
    if UI.count(sig) != 1:
        raise AssertionError("%r occurs %d times - this law cannot see its subject" % (sig, UI.count(sig)))
    i = UI.index(sig)
    depth = 0
    for j in range(UI.index("{", i), len(UI)):
        if UI[j] == "{":
            depth += 1
        elif UI[j] == "}":
            depth -= 1
            if depth == 0:
                return UI[i:j + 1]
    raise AssertionError("%r never closed - harness fault, not a pass" % sig)


def _line(start):
    if UI.count(start) != 1:
        raise AssertionError("%r occurs %d times" % (start, UI.count(start)))
    i = UI.index(start)
    return UI[i:UI.index("\n", i)]


HARNESS = r"""
const C = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
let NOW = 1800000000000;
const RealDate = Date;
function mk(id) {
  const e = { id: id, hidden: true, textContent: '', style: {}, kids: [], btn: {}, _h: '' };
  Object.defineProperty(e, 'innerHTML', { get() { return this._h; }, set(v) { this._h = String(v); this.kids = []; this.btn = {}; } });
  Object.defineProperty(e, 'firstChild', { get() { return this.kids[0] || null; } });
  e.querySelector = function (sel) {
    if (sel === '.sh-opening') {
      if (this._h.indexOf('sh-opening') < 0) return null;
      const m = /data-since="(\d+)"/.exec(this._h);
      return { getAttribute: (k) => (k === 'data-since' && m) ? m[1] : null };
    }
    if (sel[0] !== '#') return null;
    const want = sel.slice(1);
    const kid = this.kids.find(function (k) { return k.id === want; });
    if (kid) return kid;
    if (this._h.indexOf('id="' + want + '"') < 0) return null;
    return this.btn[want] || (this.btn[want] = { id: want });
  };
  e.insertBefore = function (n) { this.kids.unshift(n); };
  e.querySelectorAll = function () { return []; };
  return e;
}
async function scene(opts) {
  const els = { 'theatre': mk('theatre'), 'th-shelfov': mk('th-shelfov'), 'th-caption': mk('th-caption') };
  const cls = new Set(), faults = [], waits = [], timers = [];
  const TH = Object.assign({ gen: 0 }, opts.TH || {});
  const document = { body: { classList: { add: (c) => cls.add(c), remove: (c) => cls.delete(c), contains: (c) => cls.has(c) },
                             getAttribute: () => null },
                     createElement: () => ({ id: '', className: '', textContent: '' }), querySelector: () => null };
  const window = { _sessionsJson: () => new Promise(function () {}) };   /* the list never arrives */
  const $ = (id) => els[id] || null;
  const FakeDate = { now: () => NOW };
  const stubs = {
    thArtInit() {}, thRibbon() {}, thCoachOnce() {}, thLit() {}, _shFilter() {},
    thSessionsWait() { waits.push(1); return new Promise(function () {}); },
    thClose() { TH.open = false; els.theatre.hidden = true; },
    _thShelfWasTheDoor() { return !!TH.shelfIsDoor; },
    fetch(url, init) { faults.push(JSON.parse((init && init.body) || '{}')); return Promise.resolve({}); },
    setTimeout(fn, ms) { timers.push({ fn: fn, at: NOW + ms }); return timers.length; },
    clearTimeout(id) { if (timers[id - 1]) timers[id - 1].fn = null; },
  };
  const names = Object.keys(stubs);
  const SHELF_F = { station: null };
  const make = new Function('document', 'window', '$', 'TH', 'SHELF_F', 'Date', ...names,
    C.code + '\nreturn { thOpen: thOpen, thShelf: thShelf, bound: TH_SHELF_OPEN_BOUND_MS };');
  const f = make(document, window, $, TH, SHELF_F, FakeDate, ...names.map((n) => stubs[n]));
  const out = { bound: f.bound };
  const fire = function (adv) {
    NOW += adv;
    timers.slice().forEach(function (t) { if (t.fn && t.at <= NOW) { const g = t.fn; t.fn = null; g(); } });
  };
  if (opts.door) {
    let settled = false;
    f.thOpen().then(function () { settled = true; });
    await new Promise((r) => RealDate && setImmediate(r));
    out.settled = settled;
    out.waits = waits.length;
    out.caption = els['th-caption'].textContent;
    out.html = els['th-shelfov'].innerHTML;
    out.armed = timers.filter((t) => t.fn).length;
    if (opts.paintFirst) els['th-shelfov'].innerHTML = '<div class="sh-grid"><div class="sh-card"></div></div>';
    if (opts.closeFirst) els['th-shelfov'].hidden = true;
    fire(opts.advance || 0);
    out.after = els['th-shelfov'].innerHTML;
    out.faults = faults.map((x) => x.kind);
    out.why = TH.sessionsFailWhy || null;
  }
  if (opts.load) {
    TH.sessions = [];
    f.thShelf(true);
    out.html = els['th-shelfov'].innerHTML;
    out.armed = timers.filter((t) => t.fn).length;
    fire(opts.advance || 0);
    out.after = els['th-shelfov'].innerHTML;
    out.faults = faults.map((x) => x.kind);
  }
  return out;
}
(async function () {
  const res = {
    inHand: await scene({ door: true, TH: { shelfAsDoor: true, sessions: [{ n: 1, sessionId: 's1' }] } }),
    stuck: await scene({ door: true, advance: 61000, TH: { shelfAsDoor: true, sessions: [] } }),
    early: await scene({ door: true, advance: 30000, TH: { shelfAsDoor: true, sessions: [] } }),
    painted: await scene({ door: true, advance: 61000, paintFirst: true, TH: { shelfAsDoor: true, sessions: [] } }),
    closed: await scene({ door: true, advance: 61000, closeFirst: true, TH: { shelfAsDoor: true, sessions: [] } }),
    load: await scene({ load: true, advance: 61000 }),
  };
  console.log(JSON.stringify(res));
})().catch(function (e) { console.error(String(e && e.stack || e)); process.exit(3); });
"""

BEAT = r"""
var CASE = %s;
var NOWB = 1800000000000;
Date.now = function(){ return NOWB; };
/* the shelf's one hero box, by its class list; a selector is matched by its classes, never by its spelling, so a selector
   the page changes is judged by what it would match, not by whether this fake knew the string */
function _matches(sel, cls){
  var m = /^\.([\w-]+)((?::not\(\.[\w-]+\))*)$/.exec(String(sel));
  if (!m) return false;
  if (cls.indexOf(m[1]) < 0) return false;
  var nots = (m[2].match(/:not\(\.[\w-]+\)/g) || []).map(function(x){ return x.slice(6, -1); });
  return nots.every(function(n){ return cls.indexOf(n) < 0; });
}
var ov = {
  hidden: !!CASE.hidden, scrollHeight: 0, clientHeight: 0, scrollTop: 0,
  getBoundingClientRect: function(){ return {height: 300, width: 800, top: 40, bottom: 340, left: 0, right: 800}; },
  getClientRects: function(){ return [1]; },
  querySelectorAll: function(){ return []; },
  querySelector: function(sel){
    if (!CASE.hero || !_matches(sel, CASE.hero)) return null;
    return { getAttribute: function(k){ return (k === 'data-since' && CASE.since !== null) ? String(CASE.since) : null; } };
  }
};
var TH = { sessionsFailWhy: CASE.failWhy };
var document = { getElementById: function(id){ return id === 'th-shelfov' ? ov : null; } };
var window = { innerHeight: 800, innerWidth: 1120 };
var o = {};
%s
console.log(JSON.stringify(o.shelf || {}));
"""


def _node(prog_text, arg=None):
    if NODE is None:
        raise AssertionError("node is not installed on this PC - this law runs the shipped shelf in node and does not skip")
    d = tempfile.mkdtemp(prefix="shelf_opening_")
    try:
        h = os.path.join(d, "h.js")
        with io.open(h, "w", encoding="utf-8") as fh:
            fh.write(prog_text)
        cmd = [NODE, h]
        if arg is not None:
            c = os.path.join(d, "c.json")
            with io.open(c, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(arg))
            cmd.append(c)
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    finally:
        shutil.rmtree(d, True)
    if r.returncode != 0:
        raise AssertionError("node failed: %s" % r.stderr.decode("utf-8", "replace")[-1500:])
    return json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])


def _beat(**case):
    blk = SHB._block()
    if blk is None:
        raise AssertionError("the shelf geometry block this law drives is gone")
    base = {"hidden": False, "since": None, "hero": None, "failWhy": None}
    base.update(case)
    return _node(BEAT % (json.dumps(base), blk))


def _hero_classes(html):
    """-> the class list of the one .sh-empty-hero box in a painted shelf"""
    found = re.findall(r'class="(sh-empty-hero[^"]*)"', html)
    if len(found) != 1:
        raise AssertionError("expected one hero box in the painted shelf, found %d: %r" % (len(found), html[:300]))
    return found[0].split()


class TheShelfNeverHangsOnOpening(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        code = "\n".join([_line(x) for x in LINES] + [_cut(x) for x in FNS])
        cls.got = _node(HARNESS, {"code": code})

    def test_runs_in_hand_open_at_once(self):
        g = self.got["inHand"]
        self.assertTrue(g["settled"], "the door with runs in hand did not return at once: %r" % g)
        self.assertEqual(g["waits"], 0, "the door asked /api/sessions before painting runs it already held: %r" % g)
        self.assertEqual(g["caption"], "the shelf", g)

    def test_both_placeholders_are_marked_and_watched(self):
        self.assertEqual(UI.count(DOOR_MARK), 1, "the door's 'opening the shelf' is not marked .sh-opening with its start")
        self.assertEqual(UI.count(LOAD_MARK), 1, "thShelf's first-load placeholder is not marked .sh-opening with its start")
        g = self.got["stuck"]
        self.assertIn("sh-opening", g["html"], g)
        self.assertGreaterEqual(g["armed"], 1, "the door painted 'opening' and armed no watch: %r" % g)
        self.assertGreaterEqual(self.got["load"]["armed"], 1, "the first load armed no watch: %r" % self.got["load"])

    def test_an_opening_that_outlives_the_bound_says_why(self):
        self.assertEqual(self.got["stuck"]["bound"], 60000)
        for k in ("stuck", "load"):
            g = self.got[k]
            self.assertNotIn("sh-opening", g["after"], "%s: still 'opening' after the bound: %r" % (k, g["after"][:300]))
            self.assertIn("your runs: UNKNOWN", g["after"], "%s: the stuck shelf did not become UNKNOWN" % k)
            self.assertIn("61 s after it began", g["after"], "%s: the why does not say how long: %r" % (k, g["after"][:400]))
            self.assertIn("sh-unk-retry", g["after"])
            self.assertIn("sh-unk-x", g["after"])
            self.assertIn("shelf-open-stuck", g["faults"], "%s: the Doctor was not told: %r" % (k, g["faults"]))

    def test_a_shelf_that_painted_or_closed_or_is_still_in_bound_is_left_alone(self):
        e = self.got["early"]
        self.assertIn("opening the shelf", e["after"], "the watch fired before its bound: %r" % e)
        self.assertEqual(e["faults"], [])
        p = self.got["painted"]
        self.assertIn("sh-card", p["after"], "the watch painted over a shelf that had filled: %r" % p)
        self.assertEqual(p["faults"], [])
        c = self.got["closed"]
        self.assertEqual(c["faults"], [], "the watch reported a shelf he had closed: %r" % c)

    def test_the_beat_tells_opening_and_unknown_from_empty(self):
        opening = ["sh-empty-hero", "sh-opening"]
        op = _beat(hero=opening, since=1800000000000 - 42000)
        self.assertIs(op.get("opening"), True, op)
        self.assertEqual(op.get("openingS"), 42, op)
        self.assertIs(op.get("emptyHero"), False, "an opening shelf was published as the empty one: %r" % op)
        self.assertIs(op.get("unknown"), False, op)
        nostamp = _beat(hero=opening, since=None)
        self.assertIsNone(nostamp.get("openingS"), "an opening with no start stamp got an age: %r" % nostamp)
        empty = _beat(hero=["sh-empty-hero"])
        self.assertIs(empty.get("emptyHero"), True, empty)
        self.assertIs(empty.get("opening"), False, empty)
        self.assertIs(empty.get("unknown"), False, empty)
        shut = _beat(hidden=True, hero=opening, since=1800000000000 - 5000)
        self.assertIs(shut.get("opening"), False, "a closed shelf was published as opening: %r" % shut)
        why = "it still said opening 61 s after it began - the sessions list never arrived"
        unk = _beat(hero=["sh-empty-hero", "sh-unknown"], failWhy=why)
        self.assertIs(unk.get("emptyHero"), False, "the UNKNOWN shelf was published as the empty one: %r" % unk)
        self.assertIs(unk.get("unknown"), True, unk)
        self.assertEqual(unk.get("unknownWhy"), why, unk)
        self.assertIs(unk.get("opening"), False, unk)
        unk_shut = _beat(hidden=True, hero=["sh-empty-hero", "sh-unknown"], failWhy=why)
        self.assertIs(unk_shut.get("unknown"), False, "a closed shelf was published as unknown: %r" % unk_shut)

    def _verdict(self, shelf, age=2.0):
        import console_doctor as cd
        real = cd._get
        cd._get = lambda path, *a, **k: ({"uiBeat": {"n": 7, "ageS": age, "panels": {"shelf": shelf}}}
                                         if path == "/api/status" else real(path))
        try:
            return cd._check_the_shelf_is_where_it_says_it_is()
        finally:
            cd._get = real

    BASE = {"open": True, "filled": True, "cards": 0, "gridCards": 0, "visibleCards": 0, "box": "shown",
            "boxes": 1, "h": 300, "top": 40, "w": 800, "vh": 800, "emptyHero": False}

    def test_the_doctor_judges_an_opening_shelf_against_its_bound(self):
        import console_doctor as cd
        base = dict(self.BASE, opening=True)
        st, why = self._verdict(dict(base, openingS=200))
        self.assertEqual(st, cd.MISSING, why)
        self.assertIn("opening", why)
        st, why = self._verdict(dict(base, openingS=12))
        self.assertEqual(st, cd.OK, why)
        self.assertNotIn("no runs to show", why, "an opening shelf was called the empty one: %r" % why)
        st, why = self._verdict(dict(base, openingS=None))
        self.assertEqual(st, cd.UNKNOWN, why)
        self.assertGreater(cd.SHELF_OPENING_BOUND_S, 60, "the Doctor's bound is inside the page's own 60 s bound")

    def test_the_doctor_counts_the_beats_own_age(self):
        """[[stale-reading]] 10 s of 'opening' on a beat 280 s old is ~290 s by now if it still says so - not '10s so far'"""
        import console_doctor as cd
        st, why = self._verdict(dict(self.BASE, opening=True, openingS=10), age=280.0)
        self.assertEqual(st, cd.UNKNOWN, "a 290-s opening was judged by its 10-s reading: %r" % why)
        self.assertIn("280s old", why, why)
        st, why = self._verdict(dict(self.BASE, opening=True, openingS=10), age=30.0)
        self.assertEqual(st, cd.OK, why)
        self.assertIn("40s so far", why, why)

    def test_the_unknown_shelf_is_a_fault_from_the_page_to_the_doctor(self):
        """the joined chain: the shipped watch's own UNKNOWN shelf -> the shipped beat -> console_doctor's row"""
        import console_doctor as cd
        stuck = self.got["stuck"]
        hero = _hero_classes(stuck["after"])
        beat = _beat(hero=hero, failWhy=stuck["why"])
        self.assertIs(beat.get("emptyHero"), False, "the beat called the UNKNOWN shelf the empty one: %r" % beat)
        shelf = dict(self.BASE)
        shelf.update({k: beat.get(k) for k in ("emptyHero", "opening", "openingS", "unknown", "unknownWhy")})
        st, why = self._verdict(shelf)
        self.assertEqual(st, cd.MISSING, "the Doctor passed a shelf that says 'your runs: UNKNOWN': %r" % why)
        self.assertIn("UNKNOWN", why, why)
        self.assertIn("61 s after it began", why, "the Doctor did not carry the page's own why: %r" % why)
        self.assertNotIn("no runs to show", why, why)


class TheProofsNameOnePlace(unittest.TestCase):

    def test_each_find_matches_once(self):
        for proof in RED_PROOF:
            src = DOC if proof["file"].endswith("console_doctor.py") else UI
            self.assertEqual(src.count(proof["find"]), proof["matches"], proof["why"])


RED_PROOF = [
    {"why": "REG-3203 - the door waits for a fresh list even with runs in hand",
     "file": "tv/control_ui.html",
     "find": "    if (_shelfDoor && (TH.sessions || []).length) {\n",
     "replace": "    if (false && _shelfDoor && (TH.sessions || []).length) {\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3203 - a shelf still 'opening' at the bound is left saying so for ever",
     "file": "tv/control_ui.html",
     "find": "      var op = ov.querySelector('.sh-opening');\n      if (!op) return;\n",
     "replace": "      var op = ov.querySelector('.sh-opening');\n      return;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3203 - the door's placeholder is not marked opening, so nothing can find it",
     "file": "tv/control_ui.html",
     "find": "            + '<div class=\"sh-empty-hero sh-opening\" data-since=\"' + Date.now() + '\"><div class=\"she-lead\">opening the shelf",
     "replace": "            + '<div class=\"sh-empty-hero\" data-since=\"' + Date.now() + '\"><div class=\"she-lead\">opening the shelf",
     "matches": 1, "needs": "node"},
    {"why": "REG-3203 - the beat counts an opening shelf as the legitimate empty one",
     "file": "tv/control_ui.html",
     "find": "o.shelf.emptyHero = !!ov.querySelector('.sh-empty-hero:not(.sh-opening):not(.sh-unknown)');",
     "replace": "o.shelf.emptyHero = !!ov.querySelector('.sh-empty-hero:not(.sh-unknown)');",
     "matches": 1, "needs": "node"},
    {"why": "REG-3203 - the beat counts the UNKNOWN shelf as the legitimate empty one",
     "file": "tv/control_ui.html",
     "find": "o.shelf.emptyHero = !!ov.querySelector('.sh-empty-hero:not(.sh-opening):not(.sh-unknown)');",
     "replace": "o.shelf.emptyHero = !!ov.querySelector('.sh-empty-hero:not(.sh-opening)');",
     "matches": 1, "needs": "node"},
    {"why": "REG-3203 - the beat never says the shelf is UNKNOWN",
     "file": "tv/control_ui.html",
     "find": "o.shelf.unknown = ov.hidden ? false : !!ov.querySelector('.sh-unknown');",
     "replace": "o.shelf.unknown = false;",
     "matches": 1, "needs": "node"},
    {"why": "REG-3203 - the Doctor calls a stuck opening 'no runs yet'",
     "file": "tv/console_doctor.py",
     "find": "        if shelf.get(\"opening\") is True:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3203 - the Doctor passes the UNKNOWN shelf",
     "file": "tv/console_doctor.py",
     "find": "        if shelf.get(\"unknown\") is True:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3203 - the Doctor judges an opening by a beat's reading and not its age",
     "file": "tv/console_doctor.py",
     "find": "            if _os + _bage > SHELF_OPENING_BOUND_S:\n",
     "replace": "            if False:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
