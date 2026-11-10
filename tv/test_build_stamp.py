"""v2466 — the build stamp may drop its decoration, but never half a word.

⚠ THE DEFECT, AND WHY IT COUNTS DESPITE BEING DELIBERATE. v1691.1 capped this badge at 180px and
ruled "id + date must survive; the name is the decoration that clips". That rule is right and this
guard does not touch it. What went wrong underneath it: the version NAMES grew to 45 characters in
a box that fits about 24, so the decoration was ALWAYS cut mid-word — measured on the shipped
stamp, 259px of 437 hidden, rendering "v2465 · 2026-09-03 · THE ...".

TWO INDEPENDENT COLD CROSS-FAMILY READS called that fragment an unintended cut-off. The second one
matters most: on the same screenshots it correctly identified a genuinely deliberate overlay
elsewhere as "intentional UI behaviour, not a rendering error", reversing its own earlier call that
I had refuted by measurement. It distinguishes deliberate from broken, and it called this broken.

THE LAW PINNED HERE IS NOT "the name must show". It is: **whatever the stamp renders, it renders
whole.** Dropping the decoration is allowed. Ending mid-word is not.

⚠ It SKIPS, never passes, without headless Chrome — an unmeasured stamp is UNKNOWN.

REG-1829 — THE ONE-SHOT FIT CHECK MISSED A BADGE THAT WAS NOT LAID OUT YET. GrokBot, on his live
screen at v3595: "v3595 · 2026-10-04 · buil…". The fit check ran once, right after the append; a
badge that is display:none then (below 720px, or a board frame still hidden) reads 0 against 0,
keeps the full stamp, and clips mid-word once shown. The render law above loads the page laid out
at full width, so it never meets that case. TheBuildBadgeNeverClipsAWord drives the SHIPPED badge()
and _roDefer in node over a box whose width follows its text, so it runs without Chrome: the badge
is measured again when its box changes, one frame later, never inside the observer's delivery
(the #223 rule).
"""
import io
import json
import os
import subprocess
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
BIBLE = "file://" + os.path.join(os.path.dirname(HERE), "bible.html")
SRC = io.open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8").read()

_PROBE = r"""(function(){
  var all = document.querySelectorAll('body > div'), hit = null;
  for (var i = 0; i < all.length; i++){
    if (/^v\d+ · 20\d\d-/.test((all[i].textContent || '').trim())) { hit = all[i]; break; }
  }
  if (!hit) return JSON.stringify({found:false});
  return JSON.stringify({found:true, txt:(hit.textContent||'').trim(),
    scrollW:hit.scrollWidth, clientW:hit.clientWidth,
    hasTitle:!!hit.getAttribute('title'),
    title:(hit.getAttribute('title')||'').slice(0,60)});
})()"""


def _read():
    import render_check as rc
    if not rc._chrome_up():
        return None
    try:
        tab = rc._Tab(BIBLE)
        time.sleep(9)
        raw = tab.ev(_PROBE)
        tab.close()
        return json.loads(raw) if raw else None
    finally:
        rc._chrome_down()


class TheStampRendersWhole(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.d = _read()

    def setUp(self):
        if not self.d:
            self.skipTest("no headless Chrome — the stamp is UNMEASURED, which is UNKNOWN not a pass")
        if not self.d.get("found"):
            self.skipTest("no build stamp found on the page — UNKNOWN, never a pass")

    def test_the_stamp_is_not_clipped(self):
        d = self.d
        self.assertLessEqual(
            d["scrollW"], d["clientW"] + 1,
            "the build stamp renders %dpx of text in %dpx and ends mid-word: %r. v1691.1 allows the "
            "NAME to be dropped — it does not allow half of it to be shown. Two independent cold "
            "reads called this exact fragment a rendering bug."
            % (d["scrollW"], d["clientW"], d["txt"]))

    def test_the_id_and_date_always_survive(self):
        """v1691.1's actual rule, which this guard protects rather than replaces: whatever else
        goes, the answer to 'is this tab stale?' must stay on screen."""
        import re
        self.assertRegex(self.d["txt"], r"^v\d+ · 20\d\d-\d\d-\d\d",
                         "the stamp no longer leads with id and date, which is the one thing "
                         "v1691.1 said must survive: %r" % self.d["txt"])

    def test_the_full_note_is_still_recoverable(self):
        """Dropping the decoration is only honest because the whole thing is one hover away."""
        self.assertTrue(self.d["hasTitle"],
                        "the stamp drops its name and offers no title — the text would be gone "
                        "with no way back, which is worse than the truncation it replaced")


# REG-1829 — the shipped badge() and _roDefer, run in node: no Chrome, so it grades on every machine
RO_START = "  var _roDefer = function(fn){"
RO_END = "  var _dockEl = document.querySelector('#control-dock .dock-inner');"
BADGE_START = "  function badge(){"
BADGE_END = "  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', badge);"

#: the badge's real box: 10px monospace, 7px padding a side plus a 1px border, capped at 180px
CH, PAD, CAP = 6, 16, 180


def _cut(start, end):
    """The shipped text between two anchors that each occur once. -> str"""
    assert SRC.count(start) == 1, "anchor %r occurs %d times in bible.html" % (start, SRC.count(start))
    assert SRC.count(end) == 1, "anchor %r occurs %d times in bible.html" % (end, SRC.count(end))
    i = SRC.find(start)
    j = SRC.find(end, i)
    assert j > i, "the anchors are out of order"
    return SRC[i:j]


HARNESS = r"""
var LAID = %(laid)s, CH = %(ch)d, PAD = %(pad)d, CAP = %(cap)d;
var BADGE = null, OBS = [], RAF = [], LOG = [];
function Box(){ this._t = ''; this.id = ''; this.title = ''; this._attrs = {}; }
Box.prototype.getAttribute = function(n){ return Object.prototype.hasOwnProperty.call(this._attrs, n) ? this._attrs[n] : null; };
Box.prototype.setAttribute = function(n, v){ this._attrs[n] = String(v); };
Object.defineProperty(Box.prototype, 'textContent', {
  get: function(){ return this._t; }, set: function(v){ this._t = String(v); } });
Object.defineProperty(Box.prototype, 'scrollWidth', {
  get: function(){ return LAID ? this._t.length * CH + PAD : 0; } });
Object.defineProperty(Box.prototype, 'clientWidth', {
  get: function(){ return LAID ? Math.min(CAP, this._t.length * CH + PAD) : 0; } });
var document = {
  readyState: 'complete', title: '',
  getElementById: function(id){ return (BADGE && BADGE.id === id) ? BADGE : null; },
  createElement: function(){ BADGE = new Box(); return BADGE; },
  body: { appendChild: function(){} },
  querySelector: function(){ return null; }
};
var window = { D2R_BUILD: %(build)s, requestAnimationFrame: function(f){ RAF.push(f); } };
function ResizeObserver(cb){ this.cb = cb; this.els = []; OBS.push(this); }
ResizeObserver.prototype.observe = function(el){ this.els.push(el); };
function flush(){ var q = RAF.splice(0); q.forEach(function(f){ f(); }); }
function deliver(){
  OBS.forEach(function(o){
    if (o.els.indexOf(BADGE) < 0) return;
    var before = BADGE.textContent; o.cb([]);
    if (BADGE.textContent !== before) LOG.push('changed inside the delivery');
  });
}
function fits(){ return BADGE.scrollWidth <= BADGE.clientWidth + 1; }
"""


def _drive(build, laid_at_boot, script):
    """badge() at boot, then `script`. -> {text, fits, observed, log}"""
    prog = (HARNESS % {"laid": "true" if laid_at_boot else "false", "ch": CH, "pad": PAD, "cap": CAP,
                       "build": json.dumps(build)}
            + _cut(RO_START, RO_END) + "\n" + _cut(BADGE_START, BADGE_END) + "\n"
            + "badge(); flush();\n" + script + "\n"
            + "process.stdout.write(JSON.stringify({ text: BADGE.textContent, fits: fits(),"
            + " observed: OBS.some(function(o){ return o.els.indexOf(BADGE) >= 0; }), log: LOG }));\n")
    r = subprocess.run(["node", "-"], input=prog.encode("utf-8"), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=30)
    if r.returncode != 0:
        raise AssertionError("the shipped badge would not run: %s" % r.stderr.decode("utf-8", "replace")[-900:])
    return json.loads(r.stdout.decode("utf-8"))


#: the stamp GrokBot saw: 37 characters, 238px in a 180px box
LONG = {"id": "v3595", "name": "v3595 - build stash view", "date": "2026-10-04", "note": "n"}
SHORT = {"id": "v3595", "name": "v3595 - ok", "date": "2026-10-04", "note": "n"}
ID_DATE = "v3595 · 2026-10-04"


class TheBuildBadgeNeverClipsAWord(unittest.TestCase):

    def test_the_fixture_really_overflows_the_cap(self):
        """Non-vacuity: the long stamp must not fit, or every case below passes for nothing."""
        full = ID_DATE + " · build stash view"
        self.assertGreater(len(full) * CH + PAD, CAP)
        self.assertLessEqual(len(ID_DATE) * CH + PAD, CAP)

    def test_a_badge_laid_out_at_boot_still_drops_the_name(self):
        """v2466's rule, unchanged."""
        o = _drive(LONG, True, "")
        self.assertEqual(o["text"], ID_DATE)
        self.assertTrue(o["fits"])

    def test_a_badge_hidden_at_boot_drops_the_name_when_it_is_shown(self):
        """The defect: measured at 0 against 0, the full stamp stayed and clipped once shown."""
        o = _drive(LONG, False, "LAID = true; deliver(); flush();")
        self.assertTrue(o["observed"], "nothing watches the badge's box, so it is measured only once at boot")
        self.assertEqual(o["text"], ID_DATE,
                         "the badge was shown after boot and kept a stamp it cannot fit: %r" % o["text"])
        self.assertTrue(o["fits"], "the painted stamp is clipped mid-word")

    def test_the_resize_work_waits_a_frame(self):
        """#223 — a resize callback must not change the box it observes inside the delivery."""
        o = _drive(LONG, False, "LAID = true; deliver(); flush();")
        self.assertEqual(o["log"], [], "the badge's text changed inside the observer's delivery")

    def test_a_name_that_fits_is_still_shown(self):
        o = _drive(SHORT, False, "LAID = true; deliver(); flush();")
        self.assertEqual(o["text"], ID_DATE + " · ok")
        self.assertTrue(o["fits"])

    def test_a_hidden_badge_is_not_judged(self):
        """0 against 0 is no measurement. The stamp is left whole until there is a box to measure."""
        o = _drive(LONG, False, "deliver(); flush();")
        self.assertEqual(o["text"], ID_DATE + " · build stash view")

    def test_the_id_and_the_date_always_lead(self):
        for build, laid, script in ((LONG, True, ""), (LONG, False, "LAID = true; deliver(); flush();"),
                                    (SHORT, True, "")):
            with self.subTest(build["name"], laid=laid):
                self.assertTrue(_drive(build, laid, script)["text"].startswith(ID_DATE))

RED_PROOF = [
    {
        'why': 'v1691.1 caps the build badge at 180px and lets the version NAME clip; v2466 added a post-render fit check that drops the name entirely rather than ending it mid-word. Killing that check reintroduces the exact defect two cold cross-family reads called a rendering bug: 406px of text painted into a 178px box, cut mid-word.  MEASURED: untampered green — "Ran 3 tests in 10.561s / OK", all three RAN (no skip), so headless Chro; tampered (all 1) red — "FAILED (failures=1)": AssertionError: 406 not less than or equal to 179 :; reddened law test_build_stamp.TheStampRendersWhole.test_the_stamp_is_not_clipped; ALONE FAILS ALONE — python3 -m unittest test_build_stamp.TheStampRendersWhole.test_the_stamp_is_not_clippe.',
        'file': 'bible.html',
        'find': 'if (el.scrollWidth > el.clientWidth + 1) {',
        'replace': 'if (false) {',
        'matches': 1,
    },
    {
        "why": "REG-1829 - the badge is measured once at boot, so a badge shown later clips its name mid-word",
        "file": "bible.html",
        "find": "    try { if (typeof ResizeObserver !== 'undefined' && typeof _roDefer === 'function')"
                " new ResizeObserver(_roDefer(_fit)).observe(el); } catch (e) {}\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-1829 - the badge is re-measured inside the observer's delivery (#223)",
        "file": "bible.html",
        "find": "new ResizeObserver(_roDefer(_fit)).observe(el);",
        "replace": "new ResizeObserver(_fit).observe(el);",
        "matches": 1,
    },
    {
        "why": "REG-1829 - a hidden badge is judged at 0 against 0 and its stamp is cut before there is a box",
        "file": "bible.html",
        "find": "      try {\n        if (el.scrollWidth > el.clientWidth + 1) {\n",
        "replace": "      try {\n        if (el.scrollWidth >= el.clientWidth) {\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    unittest.main(verbosity=2)
