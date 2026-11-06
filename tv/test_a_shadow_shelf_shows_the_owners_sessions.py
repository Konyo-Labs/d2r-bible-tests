# -*- coding: utf-8 -*-
"""#218 phase 3b (REG-2810, his ruling 2026-10-28) - IN A SHADOW, THE SHELF AND THE BAR OPEN THE OWNER'S SESSIONS.

His ruling: a shadow renders the owner's exact data one to one, with SUMMARIZED frames - a few small key frames per
session; full reels never leave their PC. REG-2765/2771/2772 publish that digest, REG-2773 reads it back on
GET /api/roster-cache?frames=<owner>. Until now nothing drew it: THE SHELF in a shadow answered with REG-2700's refusal
toast, and in the board rooms the owner's frame covered THE SHELF besides (GrokBot's v3817 pass).

Now THE SHELF, and a 📚 Their sessions button on the shadow bar (every tab, TV·D included), open one read-only list:
whose sessions, the record's age (the server's words, the profile view's one rule), "this PC's last copy" when the site
went unread; per session its date, span, reads, the names read (escaped) and up to 3 key frames, each an <img> built as
data:image/jpeg;base64 over a body that is base64 and nothing else - or the record's own why when it has no pictures.
ok:false prints its why as UNKNOWN, never an empty list. The only request is one GET.

Driven: esc, _lsWhenSay, _runSpanSay and the list's helpers cut out of control_ui.html and run in node - the render over
fixture answers, and the opener over a mock DOM with a recording fetch; the record's age is joined end to end from the
real shadow_sessions.view. The Shelf, the bar, enter and Leave are read at their one-line sites. RED_PROOF below.
"""
import base64
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

NODE = shutil.which("node")
UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()

FNS = ["  function esc(s){", "  function _lsWhenSay(t0){", "  function _runSpanSay(t0, t1){",
       "  function _consoleShadowUp(){", "  function _shadowSessionRow(s, ix){", "  function _shadowSessionsHead(owner){",
       "  function _shadowSessionsHtml(d){", "  function _shadowSessionsClose(){", "  function _shadowSessionsOpen(){"]
LINES = ["  var _SSV_B64 = ", "  var _ssvGen = 0;"]

GOOD = base64.b64encode(b"\xff\xd8\xff\xe0 a thumbnail's bytes \xff\xd9").decode("ascii")
T = 1793189802000                                   # 2026-10-28 12:16:42 UTC


def _cut(sig):
    if UI.count(sig) != 1:
        raise AssertionError("%r occurs %d times - this law cannot see its subject" % (sig, UI.count(sig)))
    i = UI.index(sig)
    b = UI.index("{", i)
    depth = 0
    for j in range(b, len(UI)):
        if UI[j] == "{":
            depth += 1
        elif UI[j] == "}":
            depth -= 1
            if depth == 0:
                return UI[i:j + 1]
    raise AssertionError("%r never closed - harness fault, not a pass" % sig)


def _line(start):
    if UI.count(start) != 1:
        raise AssertionError("%r occurs %d times - this law cannot see its subject" % (start, UI.count(start)))
    i = UI.index(start)
    return UI[i:UI.index("\n", i)]


HARNESS = r"""
import { readFileSync } from 'node:fs';
const CFG = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const REG = {}, CALLS = [], PENDING = [], TIMERS = [];
let CLASSES = [];
function El(tag){ this.tagName = tag; this.children = []; this.attrs = {}; this.hidden = false; this.innerHTML = '';
                  this.listeners = {}; }
El.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
El.prototype.appendChild = function(c){ this.children.push(c); if (c.id) REG[c.id] = c; return c; };
El.prototype.addEventListener = function(t, f){ (this.listeners[t] = this.listeners[t] || []).push(f); };
El.prototype.blur = function(){};
const env = {
  API: '',
  window: {},
  document: { body: Object.assign(new El('body'), { classList: { contains: (c) => CLASSES.indexOf(c) >= 0 } }),
              createElement: (t) => new El(t), getElementById: (id) => REG[id] || null, addEventListener: () => {} },
  fetch: (url, init) => { CALLS.push({ url: String(url), init: init || null });
    return new Promise((res) => PENDING.push(() => res({ json: () => Promise.resolve(CFG.answer) }))); },
  setTimeout: (f, ms) => { TIMERS.push({ f: f, ms: ms }); return TIMERS.length; },
};
const F = new Function('env', 'with (env) {\n' + CFG.code + '\nreturn { html: _shadowSessionsHtml, open: _shadowSessionsOpen,'
  + ' close: _shadowSessionsClose }; }')(env);
const flush = async () => { while (PENDING.length) PENDING.shift()(); for (let i = 0; i < 5; i++) await null; };
const out = { html: CFG.cases.map((c) => F.html(c)) };
// the opener: no shadow, then a shadow with no owner, then the owner's - then a late answer after a close
CLASSES = []; env.window._shadowWho = 'Wife PC';
out.noShadow = { opened: F.open(), calls: CALLS.length };
CLASSES = ['shadow-on']; env.window._shadowWho = '';
out.noOwner = { opened: F.open(), calls: CALLS.length };
env.window._shadowWho = 'Wife PC';
const opened = F.open();
const ov = REG['shadow-sess-ov'];
const loading = ov ? ov._ssvBody.innerHTML : null;
await flush();
out.open = { opened: opened, calls: CALLS.slice(), shown: !!(ov && !ov.hidden), inBody: env.document.body.children.indexOf(ov),
             loading: loading, drawn: ov ? ov._ssvBody.innerHTML : null, expect: F.html(CFG.answer) };
F.open(); F.close();
const before = ov._ssvBody.innerHTML;
CFG.answer = { ok: true, owner: 'Wife PC', sessions: [], ago: 'LATE' };
await flush();
out.late = { hidden: ov.hidden, before: before, after: ov._ssvBody.innerHTML };
// REG-3256 - an answer that never comes ends in words after the bound; a late one still lands
TIMERS.length = 0; PENDING.length = 0;
F.open();
const waitMs = TIMERS.length ? TIMERS[TIMERS.length - 1].ms : null;
TIMERS.splice(0).forEach((t) => t.f());
const bounded = ov._ssvBody.innerHTML;
CFG.answer = { ok: true, owner: 'Wife PC', sessions: [], ago: 'LATE-BUT-REAL' };
await flush();
out.bound = { waitMs: waitMs, said: bounded, late: ov._ssvBody.innerHTML, expectLate: F.html(CFG.answer) };
process.stdout.write(JSON.stringify(out));
"""


def _session(**k):
    s = {"sessionId": "s_1", "t0": T - 3600000, "t1": T, "reads": 42, "names": ["Shako"], "namesMore": 0,
         "frames": [{"id": "1_1", "jpg": GOOD}], "why": None}
    s.update(k)
    return s


WORKER = {"ok": True, "owner": "<i>Dean</i>", "published": True, "t": T, "ageS": 720, "ago": "12 min ago",
          "source": "worker", "why": None, "sessions": [
              _session(names=["<b>Shako</b>", "Stone of Jordan"], namesMore=3,
                       frames=[{"id": "1_1", "jpg": GOOD}, {"id": "2_2", "jpg": "javascript:alert(1)"},
                               {"id": "3_3", "jpg": 'QUJD" onerror="alert(1)'}]),
              _session(sessionId="s_2", t0=None, t1=None, reads=None, names=None, frames=[],
                       why="r_9: this PC has no thumbnail resizer, so no picture rides <here>"),
              _session(sessionId="s_3", frames=[], why=None)]}
CASES = [
    WORKER,
    {"ok": True, "owner": "Dean", "t": T, "ageS": 10800, "ago": "3 hr ago", "source": "cache",
     "why": "the sessions fetch failed", "sessions": [_session()]},
    {"ok": False, "owner": "Dean", "published": None, "sessions": None, "t": None, "ageS": None, "source": None,
     "why": "Dean has not published its sessions yet"},
    {"ok": True, "owner": "Dean", "t": T, "ago": "1 min ago", "source": "worker", "sessions": []},
    {"ok": True, "owner": "Dean", "t": T, "ago": "1 min ago", "source": "worker", "sessions": None},
    {"ok": True, "owner": "Dean", "t": T, "source": "worker", "sessions": [_session()]},
]


def _drive(cases=CASES, answer=None):
    if NODE is None:
        raise AssertionError("node is not on this machine - this law does not skip")
    code = "\n".join([_line(x) for x in LINES] + [_cut(x) for x in FNS])
    d = tempfile.mkdtemp(prefix="shadow_sessions_")
    try:
        h, c = os.path.join(d, "h.mjs"), os.path.join(d, "cfg.json")
        io.open(h, "w", encoding="utf-8").write(HARNESS)
        io.open(c, "w", encoding="utf-8").write(json.dumps({"code": code, "cases": cases,
                                                            "answer": answer or CASES[1]}))
        r = subprocess.run([NODE, h, c], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=60, env=dict(os.environ, TZ="UTC", LANG="en_US.UTF-8"))
    finally:
        shutil.rmtree(d, True)
    if r.returncode != 0:
        raise AssertionError("node failed: %s" % r.stderr[-900:])
    return json.loads(r.stdout)


class TheListDrawsTheirRecord(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.got = _drive()
        cls.worker, cls.cache, cls.refused, cls.empty, cls.nolist, cls.noage = cls.got["html"]

    def test_a_picture_is_a_jpeg_data_uri_and_nothing_else(self):
        srcs = re.findall(r'src="([^"]*)"', self.worker)
        self.assertEqual(srcs, ["data:image/jpeg;base64," + GOOD],
                         "the pictures are not exactly the one JPEG data URI: %r" % srcs)
        for bad in ("javascript:", "onerror"):
            self.assertNotIn(bad, self.worker, "a frame body escaped its data URI: %r" % self.worker)
        self.assertIn("2 of its pictures would not draw", self.worker)

    def test_names_and_the_owner_are_escaped(self):
        self.assertIn("&lt;b&gt;Shako&lt;/b&gt; · Stone of Jordan +3 more", self.worker)
        self.assertNotIn("<b>Shako", self.worker)
        self.assertIn("&lt;i&gt;Dean&lt;/i&gt;’s sessions", self.worker)
        self.assertIn("&lt;here&gt;", self.worker, "a session's why went into the page unescaped")

    def test_a_session_says_when_how_long_and_how_many(self):
        self.assertIn("Oct 28 · 11:16 AM · 60m00s · 42 reads", self.worker.replace(" ", " "))
        self.assertIn("date UNKNOWN · span UNKNOWN · reads UNKNOWN", self.worker)
        self.assertIn("names UNKNOWN", self.worker)

    def test_no_pictures_says_the_records_why(self):
        self.assertIn("no pictures - r_9: this PC has no thumbnail resizer", self.worker)
        self.assertIn("no pictures - why UNKNOWN, the record names none", self.worker)

    def test_the_header_says_whose_how_old_and_whether_it_is_a_copy(self):
        self.assertIn("uploaded 12 min ago", self.worker)
        self.assertNotIn("last copy", self.worker)
        self.assertIn("full reels stay on their PC", self.worker)
        self.assertIn("uploaded 3 hr ago · this PC’s last copy - the site could not be read "
                      "(the sessions fetch failed)", self.cache)
        self.assertIn("upload age UNKNOWN", self.noage)

    def test_a_refusal_is_unknown_never_an_empty_list(self):
        self.assertIn("sessions UNKNOWN - Dean has not published its sessions yet", self.refused)
        for row in ("ssv-row", "ssv-none", "ssv-list"):
            self.assertNotIn(row, self.refused)
        self.assertIn("their record holds no session", self.empty)
        self.assertIn("sessions UNKNOWN - the record carried no session list", self.nolist)


class TheListOpensReadOnly(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.got = _drive()

    def test_no_shadow_or_no_owner_opens_nothing_and_asks_nothing(self):
        self.assertEqual(self.got["noShadow"], {"opened": False, "calls": 0})
        self.assertEqual(self.got["noOwner"], {"opened": False, "calls": 0})

    def test_one_get_for_that_owner_and_its_answer_drawn(self):
        o = self.got["open"]
        self.assertTrue(o["opened"] and o["shown"] and o["inBody"] >= 0, o)
        self.assertEqual(len(o["calls"]), 1, o["calls"])
        call = o["calls"][0]
        self.assertEqual(call["url"], "/api/roster-cache?frames=Wife%20PC")
        init = call["init"] or {}
        self.assertNotIn("body", init)
        self.assertIn(str(init.get("method", "GET")).upper(), ("GET",), "the list sent something other than a GET")
        self.assertIn("reading their published sessions", o["loading"])
        self.assertEqual(o["drawn"], o["expect"], "the opener did not draw the answer it fetched")

    def test_a_late_answer_does_not_paint_a_closed_list(self):
        late = self.got["late"]
        self.assertTrue(late["hidden"])
        self.assertEqual(late["after"], late["before"], "an answer that landed after Close was drawn anyway")


class TheWaitHasABound(unittest.TestCase):
    """REG-3256 (#81) - GrokBot on the work ALT: the list sat on 'reading their published sessions...' for good."""

    @classmethod
    def setUpClass(cls):
        cls.got = _drive()["bound"]

    def test_an_answer_that_never_comes_ends_in_words(self):
        self.assertIsNotNone(self.got["waitMs"], "the opener set no bound on its wait")
        self.assertLessEqual(self.got["waitMs"], 30000, self.got)
        self.assertNotIn("reading their published sessions", self.got["said"], "still 'reading...' after the bound")
        self.assertIn("has not answered in 30 s", self.got["said"])

    def test_a_late_answer_still_lands(self):
        self.assertEqual(self.got["late"], self.got["expectLate"], "an answer after the bound was dropped")


class TheAgeIsTheServersOneRule(unittest.TestCase):

    def test_the_view_carries_the_profiles_age_words_and_the_list_prints_them(self):
        import console_snapshot as CS
        import shadow_sessions as SS
        rec = {"owner": "Dean", "published": True, "t": T, "digest": {"sessions": [_session()]}}
        v = SS.view("Dean", rec, T + 3 * 3600000 + 5000)
        self.assertEqual(v["ago"], CS._ago_words(3 * 3600000 + 5000))
        html = _drive(cases=[json.loads(json.dumps(v))])["html"][0]
        self.assertIn("uploaded " + v["ago"], html)


class TheDoorsAreJoined(unittest.TestCase):

    def test_the_shelf_opens_the_list_in_a_shadow_before_its_refusal(self):
        ask = "    var _shR = _shelfShadowRefusal();\n"
        opn = "    if (_shR && _shadowSessionsOpen()) return;   /* #218 phase 3b (REG-2810) - in a shadow THE SHELF is their sessions, summarized */\n"
        self.assertEqual(UI.count(opn), 1, "THE SHELF no longer opens their sessions in a shadow")
        self.assertEqual(UI.count(ask + opn), 1, "the list is not asked right after the shadow check")

    def test_in_a_shadow_the_shelf_opens_on_the_press(self):
        """v3845 - the shadow frame holds focus and WebKit spends the first click blurring it (#142): the Shelf must
        open on the primary press in a shadow, and that press's click must not open it twice."""
        i = UI.index("    _bshelf.addEventListener('pointerdown', function(e){\n")
        j = UI.index("\n  }", UI.index("}, true);", i))
        blk = UI[i:j]
        self.assertIn("if (e.button !== 0 || e.ctrlKey) return;", blk, "a right press opens the Shelf")
        self.assertIn("contains('shadow-on')", blk)
        self.assertIn("      _bshelf.onclick();\n", blk, "the press in a shadow opens nothing")
        self.assertIn("e.stopImmediatePropagation()", blk, "the press's own click opens the Shelf a second time")

    def test_the_bar_carries_the_pointer_and_binds_it(self):
        self.assertIn('<span id="shadow-who">read only</span><button type="button" id="shadow-sessions"', UI)
        i = UI.index("    var b = document.getElementById('shadow-sessions');\n")
        j = UI.index("\n  })();", i)   # the binding's own block, never a guessed length (test_a_source_window_must_reach_its_subject)
        self.assertIn("window._shadowSessionsOpen()", UI[i:j], "the bar's button opens nothing")

    def test_entering_names_the_owner_and_leave_closes_the_list(self):
        self.assertEqual(UI.count("    window._shadowWho = owner;"), 2, "a shadow door no longer says whose it is")
        self.assertEqual(UI.count("    window._shadowWho = null;   /* REG-2810 - and their sessions list goes with the shadow */\n"
                                  "    try { if (typeof window._shadowSessionsClose === 'function') window._shadowSessionsClose(); } catch (eSs) {}\n"),
                         1, "Leave keeps the owner's list (or name) after the shadow is gone")


RED_PROOF = [
    {"why": "REG-3256 - the wait has no bound again, so a busy console leaves 'reading...' up for good",
     "file": "tv/control_ui.html",
     "find": "      if (gen === _ssvGen && !ov.hidden && String(ov._ssvBody.innerHTML).indexOf('reading their published sessions') >= 0)\n",
     "replace": "      if (false)\n",
     "matches": 1},
    {"why": "v3845 - in a shadow the Shelf's press opens nothing (the first click is spent blurring their frame)",
     "file": "tv/control_ui.html", "find": "      _bshelf.onclick();\n", "replace": "", "matches": 1},
    {"why": "REG-2810 - the names read go into the page unescaped",
     "file": "tv/control_ui.html",
     "find": "nm.map(function(x){ return esc(x); }).join(' · ')",
     "replace": "nm.map(function(x){ return x; }).join(' · ')",
     "matches": 1, "needs": "node"},
    {"why": "REG-2810 - a frame body that is not base64 rides into the img tag (an attribute breaks out)",
     "file": "tv/control_ui.html",
     "find": "      if (!b || !_SSV_B64.test(b)) { bad++; return; }\n",
     "replace": "      if (!b) { bad++; return; }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2810 - the img takes the record's string as its src, whatever scheme it names",
     "file": "tv/control_ui.html",
     "find": "src=\"data:image/jpeg;base64,' + b + '\">",
     "replace": "src=\"' + b + '\">",
     "matches": 1, "needs": "node"},
    {"why": "REG-2810 - this PC's last copy is drawn as if the site had answered",
     "file": "tv/control_ui.html",
     "find": "      + (d.source === 'cache' ? ' · this PC\\u2019s last copy'",
     "replace": "      + (false ? ' · this PC\\u2019s last copy'",
     "matches": 1, "needs": "node"},
    {"why": "REG-2810 - ok:false loses its why",
     "file": "tv/control_ui.html",
     "find": "    if (d.ok !== true)\n      return head + '<div class=\"ssv-unk\">sessions UNKNOWN - '",
     "replace": "    if (d.ok === 'never')\n      return head + '<div class=\"ssv-unk\">sessions UNKNOWN - '",
     "matches": 1, "needs": "node"},
    {"why": "REG-2810 - a session with no pictures says nothing about why",
     "file": "tv/control_ui.html",
     "find": "    if (!imgs.length) note = '<div class=\"ssv-why\">no pictures - '",
     "replace": "    if (false) note = '<div class=\"ssv-why\">no pictures - '",
     "matches": 1, "needs": "node"},
    {"why": "REG-2810 - the record's age leaves the server's answer, so the list says UNKNOWN",
     "file": "tv/shadow_sessions.py",
     "find": "            \"ago\": _cs._ago_words(int(now_ms) - t) if isinstance(t, int) else None,\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2810 - the list opens (and fetches) with no shadow up",
     "file": "tv/control_ui.html",
     "find": "    if (!owner || !_consoleShadowUp()) return false;\n",
     "replace": "    if (!owner) return false;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2810 - an answer that lands after Close paints the list anyway",
     "file": "tv/control_ui.html",
     "find": "      .then(function(d){ if (gen === _ssvGen) ov._ssvBody.innerHTML = _shadowSessionsHtml(d); })\n",
     "replace": "      .then(function(d){ ov._ssvBody.innerHTML = _shadowSessionsHtml(d); })\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2810 - THE SHELF goes back to the refusal toast in a shadow",
     "file": "tv/control_ui.html",
     "find": "    if (_shR && _shadowSessionsOpen()) return;   /* #218 phase 3b (REG-2810) - in a shadow THE SHELF is their sessions, summarized */\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2810 - Leave keeps the owner's name, so the list could open for a shadow that is gone",
     "file": "tv/control_ui.html",
     "find": "    window._shadowWho = null;   /* REG-2810 - and their sessions list goes with the shadow */\n",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
