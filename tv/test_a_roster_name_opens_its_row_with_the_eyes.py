# -*- coding: utf-8 -*-
"""GBL 2026-10-24 - A ROSTER NAME OPENS ITS ROW WITH THE EYES, AND THE CROSS-REFERENCE STILL OPENS EXACTLY AS IT DID.

Elad's rulings, in order (mock: two frames, row then modal):
  · the hover card is NOT changed;
  · clicking a name does two things: the row opens inline with an HD two-eyes button (and STAYS open), and the
    cross-reference modal opens exactly as today, same place, same template, SETS/UNIQUES and its three columns;
  · the eyes are NOT inside the modal; they route to shadow for THAT profile (roster:<owner>:profile);
  · only the modal's diagnostic block changes: every line kept, folded under ADVANCED and set as data, and no fact
    of it (the 'last walk' age was clipped in the mock) is cut off.

HOW: the SHIPPED control_ui.html and the same file at BASE (the commit before this change) are rendered in one
headless Chrome over the same stubbed /api/fleet with the clock frozen, and their DOM is compared - the hover card
byte for byte, the modal byte for byte once the ADVANCED fold is unwrapped. A clone without BASE in its history
fetches that one commit by its full sha (REG-2739); only when the fetch fails too does it fail loudly - it never skips. Nothing real is touched: file:// pages, fetch stubbed, its own Chrome port.
[[unknown-stays-unknown]] [[visual-regression-detector]]
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import test_the_fleet_card_says_how_each_pc_films_and_drains as F  # noqa: E402  (sets the law's own Chrome port)

RC = F.RC
# gbl/shadow before the row eyes (control_ui.html as Elad knows it; also what the v3796 stamp sat on). The FULL sha, because a
# shallow clone can only fetch a commit by its full name (REG-2739).
BASE = "694e4378a2eeb6c31fd9a3f07e32bdcb57c657c1"
NOW_MS = 1790000000000
OWNERS = {"box-a": "Konyo \u00b7 Mac", "box-b": "Konyo \u00b7 ALT", "box-c": "Wife PC", "box-d": ""}
# GrokBot's 21:09 pass (v3809): a console never offers a shadow of ITSELF - this PC's own row carries no eyes. The fleet
# fixture's "me" is box-a; read from it, so a fixture that moves "me" moves this law with it.
ME = F._fixture()["me"]

CLOCK = r"""(function(){ var N = %d, D = Date;
  function FD(){ if (!arguments.length) return new D(N);
    return new (Function.prototype.bind.apply(D, [null].concat([].slice.call(arguments))))(); }
  FD.now = function(){ return N; }; FD.parse = D.parse; FD.UTC = D.UTC; FD.prototype = D.prototype; window.Date = FD; })();"""

SNAP = r"""(function(){
  var rows = [].map.call(document.querySelectorAll('#fleet-list .fleet-row'), function(r){
    var c = r.cloneNode(true), e = c.querySelector('.fleet-open-eyes'); if (e) e.remove();
    c.classList.remove('fleet-open'); ['onclick', 'onkeydown', 'aria-expanded'].forEach(function(a){ c.removeAttribute(a); });
    var t = r.querySelector('.ftt');
    return { m: r.getAttribute('data-fleet-machine'), ftt: t ? t.outerHTML : null, row: c.outerHTML }; });
  return JSON.stringify(rows); })()"""

XREF = r"""(function(){ var x = document.getElementById('fleet-xref'); if (!x || x.hidden) return JSON.stringify({ err: 'closed' });
  var c = x.cloneNode(true), adv = c.querySelector('details.fx-adv'), inside = !!c.querySelector('.fleet-hd-eyes');
  var summ = adv ? adv.querySelector('summary').textContent : null, open = adv ? adv.open : null;
  if (adv) adv.replaceWith(adv.querySelector('.fx-sys'));
  return JSON.stringify({ html: c.innerHTML, adv: summ, open: open, eyesInside: inside }); })()"""

CLIP = r"""(function(){ var x = document.getElementById('fleet-xref'), adv = x && x.querySelector('details.fx-adv');
  if (!adv) return JSON.stringify({ err: 'no fold' }); adv.open = true;
  var win = x.querySelector('.fxr-win'), wr = win.getBoundingClientRect(), bad = [], n = 0;
  function clippedBy(f) { for (var a = f.parentElement; a && a !== document.body; a = a.parentElement) {
      var cs = getComputedStyle(a); if (cs.overflowX !== 'visible' || cs.overflowY !== 'visible') {
        var r = a.getBoundingClientRect(), b = f.getBoundingClientRect();
        if (b.right > r.right + 0.5 || b.left < r.left - 0.5 || b.bottom > r.bottom + 0.5 || b.top < r.top - 0.5) return a.className || a.tagName; }
      if (cs.position === 'fixed') break; }
    return null; }
  [].forEach.call(adv.querySelectorAll('.fs-f, .fs-k'), function(f){ n++; var b = f.getBoundingClientRect(), cs = getComputedStyle(f);
    if (b.width === 0) { bad.push('unrendered: ' + f.textContent); return; }
    if (f.scrollWidth > f.clientWidth + 1) bad.push('wider than its box: ' + f.textContent);
    if (cs.textOverflow === 'ellipsis' || cs.whiteSpace === 'nowrap') bad.push('cut style: ' + f.textContent);
    if (b.right > wr.right + 0.5 || b.left < wr.left - 0.5 || b.bottom > wr.bottom + 0.5 || b.top < wr.top - 0.5)
      bad.push('outside the modal window: ' + f.textContent);
    var by = clippedBy(f); if (by) bad.push('clipped by ' + by + ': ' + f.textContent); });
  var walk = [].filter.call(adv.querySelectorAll('.fs-f'), function(f){ return /last walk/.test(f.textContent); }).length;
  adv.open = false;
  return JSON.stringify({ bad: bad, n: n, walk: walk }); })()"""


# The public history. A heart2 sandbox's origin is the checkout it was cloned from, and on the prove
# shards that checkout is 200 commits deep, so BASE (622 back by v3849) is not in it. Fetching "origin"
# then asks a shallow parent and fails in a fraction of a second, and the law reads ALREADY RED.
_PUBLIC_HISTORY = "https://github.com/KonyoDigital/d2r-bible-tests.git"


def _show_base():
    return subprocess.check_output(["git", "-C", ROOT, "show", BASE + ":tv/control_ui.html"], stderr=subprocess.STDOUT)


def _history_urls():
    """Where BASE may be fetched. origin first (a full checkout), then that remote's own origin when
    origin is a local path (the sandbox), then the public repo."""
    urls = ["origin"]
    seen = set(urls)
    try:
        r = subprocess.run(["git", "-C", ROOT, "remote", "get-url", "origin"],
                           capture_output=True, text=True, timeout=30)
        url = (r.stdout or "").strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        url = ""
    if url and not url.startswith(("http://", "https://", "git@")):
        try:
            parent = subprocess.run(["git", "-C", url, "remote", "get-url", "origin"],
                                    capture_output=True, text=True, timeout=30)
            got = (parent.stdout or "").strip() if parent.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            got = ""
        if got and got not in seen:
            urls.append(got)
            seen.add(got)
    if _PUBLIC_HISTORY not in seen:
        urls.append(_PUBLIC_HISTORY)
    return urls


def _base_ui():
    """BASE's control_ui.html, written beside the law. REG-2739: tv-tests.yml clones 200 commits deep and BASE fell to 216
    back when v3820 landed, so every CI run failed UNKNOWN on a law that passed on the Mac, which holds the full history -
    the #227 cliff (test_a_stamp_is_not_a_blind_spot) one law over. A clone that lacks BASE fetches that one commit by its
    full sha and reads it; only when the fetch fails as well is the answer UNKNOWN."""
    try:
        src = _show_base()
    except Exception as first:
        errors = []
        src = None
        for url in _history_urls():
            try:
                subprocess.run(["git", "-C", ROOT, "fetch", "--no-tags", "--depth=1", url, BASE],
                               capture_output=True, timeout=180, check=True)
                src = _show_base()
                break
            except Exception as e:
                errors.append("%s: %s" % (url, e))
        if src is None:
            raise AssertionError("BASE %s is not in this clone's history and could not be fetched, so 'unchanged' cannot "
                                 "be proved - UNKNOWN, not passing (%s / %s)" % (BASE, first, " | ".join(errors)))
    fd, p = tempfile.mkstemp(suffix=".html", dir=HERE, prefix=".law_base_ui_")
    with os.fdopen(fd, "wb") as fh:
        fh.write(src)
    return p


def _fixture():
    real = F.time.time
    F.time.time = lambda: NOW_MS / 1000.0
    try:
        fx = F._fixture()
    finally:
        F.time.time = real
    fx["online"][0]["platform"] = "mac"                 # Konyo on a mac publishes as Konyo · Mac
    fx["online"][1]["nickname"] = "Konyo \u00b7 ALT"
    # v3850 paints presence from the fleet stamp. A fresh online row the card at BASE called "here"
    # still is, once the stamp says online. A row with no stamp is UNKNOWN, and that is a different law.
    for row in fx["online"]:
        row["presence"] = {"state": "online", "via": "beacon", "ageS": 40, "words": "", "staleAfterS": 2040}
    fx["offline"].append({"nickname": "Laptop", "machine": "box-d", "ver": "v3401", "mode": "idle",
                          "t": F._iso(NOW_MS - 6 * 86400 * 1000), "system": {"tree": "ok", "reels": 1}})
    return fx


_CACHE = {}


def _open(t, path, w, h):
    t.send("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=False)
    t.send("Page.navigate", url="file://" + path)
    for _ in range(160):
        time.sleep(0.25)
        try:
            if t.ev("document.readyState==='complete' && typeof window._fleetRefresh === 'function'") is True:
                break
        except Exception:
            pass
    else:
        raise AssertionError("%s never exposed _fleetRefresh in 40s - UNKNOWN, not passing" % path)
    time.sleep(0.8)
    t.ev("(function(){ try { window._fleetRefresh(); } catch (e) {} return 1; })()")
    for _ in range(60):
        time.sleep(0.25)
        if t.ev("document.querySelectorAll('#fleet-list .fleet-row').length") == 4:
            return
    raise AssertionError("%s drew %r fleet rows of 4" % (path, t.ev("document.querySelectorAll('#fleet-list .fleet-row').length")))


def _wait_head(t):
    for _ in range(60):
        time.sleep(0.2)
        if t.ev("!!document.querySelector('#fleet-xref:not([hidden]) .fx-head')"):
            return True
    return False


def _render():
    if "r" in _CACHE:
        return _CACHE["r"]
    base = _base_ui()
    res = {"base": {}, "ship": {}}
    try:
        RC.require_chrome()   # REG-3061 - a browser that will not start is UNKNOWN for this law (a VenueFault), never a red
    except RC.VenueFault:
        os.unlink(base)
        raise
    try:
        t = RC._Tab("about:blank")
        t.send("Page.enable")
        t.send("Runtime.enable")
        t.send("Page.addScriptToEvaluateOnNewDocument", source=(CLOCK % NOW_MS) + F.STUB % json.dumps(_fixture()))
        for which, path in (("base", base), ("ship", F.UI_PATH)):
            for (w, h) in ((1440, 900), (375, 812)):
                k = "%dx%d" % (w, h)
                _open(t, path, w, h)
                out = {"rows": json.loads(t.ev(SNAP)), "xref": {}, "clip": {}}
                for mach in OWNERS:
                    t.ev("(function(){ window._fleetCompare(%s); return 1; })()" % json.dumps(mach))
                    _wait_head(t)
                    time.sleep(0.2)
                    out["xref"][mach] = json.loads(t.ev(XREF))
                    if which == "ship":
                        out["clip"][mach] = json.loads(t.ev(CLIP))
                    t.ev("document.getElementById('fleet-xref').hidden = true")
                if which == "ship":
                    # a REAL click on each row: the modal opens, the row opens and stays open through a second click
                    # and a fleet refresh; its eyes route to that profile and do not reopen the modal
                    out["click"] = json.loads(t.ev(r"""(function(){
                      var calls = [], opened = [], real = window._fleetCompare;
                      window._shadowOpen = function(o){ opened.push(o); };
                      window._fleetCompare = function(m, l){ calls.push(m); return real.apply(this, arguments); };
                      var out = {};
                      [].forEach.call(document.querySelectorAll('#fleet-list .fleet-row'), function(r){
                        var m = r.getAttribute('data-fleet-machine'), before = r.classList.contains('fleet-open');
                        var eb = r.querySelector('.fleet-hd-eyes'), vis0 = eb ? eb.getBoundingClientRect().height : -1;
                        r.scrollIntoView({ block: 'center' });
                        var q0 = r.getBoundingClientRect(), x0 = q0.left + q0.width / 2, y0 = q0.top + q0.height / 2;
                        r.click(); var c1 = calls.length;
                        var vis1 = eb ? eb.getBoundingClientRect().height : -1;
                        /* REG-2768 - where a second click lands: the spot of the first, and the open row's own centre */
                        var q1 = r.getBoundingClientRect();
                        var onEyes = function(x, y){ var h = document.elementFromPoint(x, y); return !!(h && h.closest && h.closest('.fleet-hd-eyes')); };
                        var eyesAt = [onEyes(x0, y0), onEyes(q1.left + q1.width / 2, q1.top + q1.height / 2)];
                        r.click();
                        var modal = !document.getElementById('fleet-xref').hidden, esc = null;
                        if (eb && !eb.disabled) { eb.focus();
                          eb.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }));
                          esc = document.getElementById('fleet-xref').hidden; }
                        out[m] = { esc: esc, before: before, open: r.classList.contains('fleet-open'),
                                   aria: r.getAttribute('aria-expanded'), calls: c1, calls2: calls.length,
                                   modal: modal, vis0: vis0, vis1: vis1, eyesAt: eyesAt,
                                   owner: eb ? eb.getAttribute('data-roster-owner') : null, disabled: eb ? eb.disabled : null };
                        document.getElementById('fleet-xref').hidden = true;
                        calls.length = 0;
                        if (eb && !eb.disabled) { eb.click(); out[m].routed = opened.slice(); out[m].callsOnEyes = calls.length; }
                        opened.length = 0; calls.length = 0;
                      });
                      window._fleetCompare = real;
                      return JSON.stringify(out); })()"""))
                    t.ev("(function(){ window._fleetRefresh(); return 1; })()")
                    time.sleep(1.5)
                    out["afterRefresh"] = t.ev("[].map.call(document.querySelectorAll('#fleet-list .fleet-row'), "
                                               "function(r){ return r.classList.contains('fleet-open'); })")
                res[which][k] = out
        res["errors"] = list(getattr(t, "page_errors", []) or [])
        try:
            t.close()
        except Exception:
            pass
    finally:
        RC._chrome_down()
        os.unlink(base)
    _CACHE["r"] = res
    return res


@unittest.skipUnless(os.path.exists(RC.CHROME), "no Chrome on this machine - the card was not rendered (declared skip 77)")
class ARosterNameOpensItsRowWithTheEyes(unittest.TestCase):

    def test_a_stuck_row_names_its_oldest_wait(self):
        # v3845 - heart2 found the REG-3051 pin BLIND: its guard asked the hover CARD for "river stuck", but the chip lives
        # in the ROW, so the "oldest reel waiting" assert never ran. Ask every river-stuck chip on the rows themselves.
        r = _render()
        tips = [t for k in r["ship"] for x in r["ship"][k]["rows"]
                for t in re.findall(r'title="(river stuck on this PC - [^"]*)"', x["row"] or "")]
        self.assertTrue(tips, "PREMISE: no rendered row carries the river-stuck chip - the REG-3051 clause is unexercised")
        for t in tips:
            self.assertRegex(t, u" \u00b7 oldest reel waiting: \\S+ \\d+ (min|h|d)",
                             "the river-stuck chip does not say what waited (REG-3051): %r" % t[:300])

    def test_the_hover_card_is_byte_for_byte_what_it_was(self):
        r = _render()
        for k in r["ship"]:
            b = dict((x["m"], x) for x in r["base"][k]["rows"])
            s = dict((x["m"], x) for x in r["ship"][k]["rows"])
            self.assertEqual(sorted(b), sorted(s), k)
            for m in s:
                self.assertTrue(s[m]["ftt"], "%s %s: no hover card at all" % (k, m))
                # #225 (his ruling 2026-10-28) changed ONE line of the card - what a click opens. Everything else in it
                # is still byte for byte; that line is pinned to its new words on its own.
                cut = re.compile(r'<div class="ftt-click">[^<]*</div>')
                # REG-3051 (GrokBot 6486545342) changed ONE clause of the river-stuck chip's tip - it now ends naming how
                # long each station's oldest reel has waited. Caught by CI on v3841 as this case. That clause is cut from
                # the ship side here and pinned on its own below; its words are REG-3051's law's to prove.
                waited = re.compile(u' \u00b7 oldest reel waiting: [^"<]*')
                # v3859 (5b4b316b, his 17:27 Fleet ruling) ADDED one chip beside river-stuck - a lane's own debt, "route
                # lane owes 76". Its span is cut from the ship side and pinned on the row below; its words are
                # test_a_held_reel_is_not_river_stuck's to prove. Nothing else in the card may move.
                owes = re.compile(r'<span class="fleet-riverowes" title="[^"]*">[^<]*</span>')
                # v3861 (his fleet screenshot, "a lot more to the point") MOVED the river chips: a reel held by a shut
                # lock left red "river stuck" for a muted "N reels wait on the locks" after the lock chip, and the lock
                # chip gained its few words of why. The river chips are cut from BOTH sides here; their words are
                # test_the_fleet_says_where_a_river_is_stuck's and test_starting_never_hides_a_known_stale_census's to
                # prove. Nothing else in the card or the row may move.
                river = re.compile(r'<span class="fleet-river(?:stuck|wait|owes)" title="[^"]*"[^>]*>[^<]*</span>')
                # v3880 (his 11-07 ask, GrokBot #6707144313) ADDED the PC's status under the card's name - ONE element,
                # .pcs, whose words are test_each_pc_reads_in_a_few_words' to prove - and moved the verdict word's run-on
                # paragraph off its NATIVE tooltip (a hovered [title] hides this card) onto aria-label. The .pcs element is
                # cut from the ship side and the word's tooltip attribute from both; nothing else in the card may move.
                pcs = re.compile(r'<div class="pcs [^"]*">(?:(?!</div>).)*</div>', re.S)
                word = re.compile(r'(<span class="fleet-meta fleet-word[^>]*?) (?:title|aria-label)="[^"]*"')
                self.assertEqual(len(pcs.findall(s[m]["ftt"])), 1, "%s %s: the card does not lead with the PC's status" % (k, m))
                self.assertIsNone(re.search(r'<span class="fleet-meta fleet-word[^>]*? title="', s[m]["row"]),
                                  "%s %s: the verdict word carries a native tooltip again - it hides this card" % (k, m))
                self.assertEqual(river.sub("", owes.sub("", waited.sub("", cut.sub("", pcs.sub("", s[m]["ftt"]))))),
                                 river.sub("", cut.sub("", b[m]["ftt"])),
                                 "%s %s: the hover card changed" % (k, m))
                if "river stuck" in b[m]["ftt"] and "river stuck" in s[m]["ftt"]:
                    self.assertIn(u" \u00b7 oldest reel waiting: ", s[m]["ftt"],
                                  "%s %s: the river-stuck chip no longer says what waited (REG-3051)" % (k, m))
                self.assertIn('<div class="ftt-click">click: open the row \u00b7 click it again: how this PC films and drains, '
                              'and their set pieces against yours</div>', s[m]["ftt"],
                              "%s %s: the card does not say what each click opens" % (k, m))
                # the row carries the card, so its #225 click line is cut from both (SNAP already strips the row's own
                # click and key handlers; the two clicks are proven by test_the_first_click_opens_the_row_and_a_second_opens_the_compare)
                self.assertEqual(river.sub("", owes.sub("", waited.sub("", cut.sub("", word.sub(r"\1", pcs.sub("", s[m]["row"])))))),
                                 river.sub("", cut.sub("", word.sub(r"\1", b[m]["row"]))),
                                 "%s %s: the row changed beyond its eyes" % (k, m))
                # v3865 (the r3 review, his ALT row: a red "vault lane owes 0") - a lane that owes NOTHING has no debt to
                # name, so the chip is asked for only when a lane owes one or more reels, and never drawn for owes 0
                if re.search(r'river stuck on this PC - [^"]*\b[A-Za-z][\w -]{0,30}? lane: owes [1-9]\d*', s[m]["row"]):
                    self.assertTrue(owes.search(s[m]["row"]),
                                    "%s %s: a lane that owes reels is no longer named beside river-stuck (v3859)" % (k, m))
                elif re.search(r'river stuck on this PC - [^"]*\b[A-Za-z][\w -]{0,30}? lane: owes 0\b', s[m]["row"]):
                    self.assertIsNone(owes.search(s[m]["row"]),
                                      "%s %s: a lane that owes 0 reels is drawn as a debt (the r3 review)" % (k, m))

    def test_the_cross_reference_is_unchanged_but_for_the_folded_diagnostics(self):
        r = _render()
        for k in r["ship"]:
            for m in OWNERS:
                b, s = r["base"][k]["xref"][m], r["ship"][k]["xref"][m]
                self.assertNotIn("err", s, "%s %s: the modal did not open" % (k, m))
                # v3847 overlay contract (Elad 14:28, one x at one spot on every overlay) marks the card ovx-card and
                # pins its own x with an inline fixed style. Caught by the v3847 full gate run as this case. Exactly those
                # marks are cut from the ship side and pinned on their own; everything else stays byte for byte.
                ovx = re.compile(r'(?<=fxr-win) ovx-card| ovx(?=")|" style="position: fixed !important; inset: \d+px \d+px auto auto !important; '
                                 r'margin: 0px !important; z-index: 2147483000 !important;(?=")'
                                 r'| style="padding-right: \d+px !important;"')
                # (on a narrow screen the contract also makes room under the x - that inline padding is its fourth mark)
                self.assertIn(len(ovx.findall(s["html"])), (3, 4), "%s %s: the modal is not under the overlay contract" % (k, m))
                self.assertEqual(ovx.sub("", s["html"]), b["html"], "%s %s: the modal changed beyond the ADVANCED fold" % (k, m))
                self.assertEqual(s["adv"], u"ADVANCED \u00b7 DIAGNOSTICS", "%s %s: no ADVANCED fold" % (k, m))
                self.assertFalse(s["open"], "%s %s: the diagnostics are not collapsed" % (k, m))
                self.assertFalse(s["eyesInside"], "%s %s: the eyes are inside the modal" % (k, m))
                self.assertIn("fxr-tab", s["html"])

    def test_every_profile_row_has_its_eyes_and_they_route_to_that_profile(self):
        r = _render()
        for k in r["ship"]:
            c = r["ship"][k]["click"]
            self.assertEqual(sorted(c), sorted(OWNERS), k)
            for m, owner in OWNERS.items():
                got = c[m]
                if m == ME:
                    self.assertIsNone(got["owner"], "%s %s: this PC's own row offered a shadow of itself (v3809)" % (k, m))
                    self.assertEqual(got["vis1"], -1, "%s %s: this PC's own row grew eyes" % (k, m))
                    self.assertNotIn("routed", got)
                    continue
                if owner:
                    self.assertTrue(got["esc"], "%s %s: Escape on the eyes did not close the modal" % (k, m))
                    self.assertEqual(got["owner"], owner, "%s %s: the eyes name another profile" % (k, m))
                    self.assertEqual(got["routed"], [owner], "%s %s: the eyes routed to %r" % (k, m, got.get("routed")))
                    self.assertEqual(got["callsOnEyes"], 0, "%s %s: pressing the eyes reopened the modal" % (k, m))
                else:
                    self.assertTrue(got["disabled"], "%s %s: a PC with no roster profile got live eyes" % (k, m))
                    self.assertNotIn("routed", got)

    def test_the_first_click_opens_the_row_and_a_second_opens_the_compare(self):
        """#225 (his ruling 2026-10-28, "do B") - the first click opens the row and its eyes and opens NO compare window
        (it covered the eyes it had just shown); a click on the open row opens the compare; the row stays open."""
        r = _render()
        for k in r["ship"]:
            for m, got in r["ship"][k]["click"].items():
                self.assertFalse(got["before"], "%s %s: a row was open before any click" % (k, m))
                if m != ME:                       # this PC's own row has no eyes at all (v3809), the rest show on click
                    self.assertEqual(got["vis0"], 0, "%s %s: the eyes showed before the click" % (k, m))
                    self.assertGreater(got["vis1"], 0, "%s %s: the click did not show the eyes on the row" % (k, m))
                self.assertEqual(got["calls"], 0, "%s %s: the first click also opened the compare window, over the eyes it "
                                                  "had just shown (#225)" % (k, m))
                self.assertEqual(got["calls2"], 1, "%s %s: a click on the open row did not open the compare" % (k, m))
                self.assertEqual(got.get("eyesAt"), [False, False],
                                 "%s %s: a second click where the first landed, or at the open row's centre, hits the eyes "
                                 "and enters the shadow instead of the compare (REG-2768): %r" % (k, m, got.get("eyesAt")))
                self.assertTrue(got["modal"], "%s %s: the modal is not open after the second click" % (k, m))
                self.assertTrue(got["open"] and got["aria"] == "true", "%s %s: a second click shut the row" % (k, m))
            self.assertEqual(r["ship"][k]["afterRefresh"], [True] * 4, "%s: a fleet refresh shut the open rows" % k)

    def test_no_diagnostic_fact_is_clipped_last_walk_included(self):
        r = _render()
        walks = 0
        for k in r["ship"]:
            for m, c in r["ship"][k]["clip"].items():
                self.assertNotIn("err", c, "%s %s" % (k, m))
                self.assertGreater(c["n"], 0, "%s %s: PRINT THE DENOMINATOR - no fact read" % (k, m))
                self.assertEqual(c["bad"], [], "%s %s: %s" % (k, m, c["bad"]))
                walks += c["walk"]
        self.assertGreater(walks, 0, "PREMISE - no 'last walk' fact was rendered, so its clipping was never measured")
        self.assertEqual(r.get("errors"), [], "the page threw: %s" % r.get("errors"))



class TheRouteIsWitnessedWithoutAWindow(unittest.TestCase):
    """REG-2721 - WHICH PROFILE A ROW'S EYES OPEN, asked of the shipped _fleetRosterOwner itself, in node.

    The window cases above skip THIS PC's own row (v3809: no shadow of yourself), and the fixture's "me" is the only
    Konyo-on-a-mac machine - so after REG-2699 nothing observed the mac route, and red-proof [2] (route Konyo's Mac to
    Dean) came back BLIND at the v3817 push. The rule is a pure function; it is witnessed here directly."""

    def owner(self, m):
        from cb_node_harness import NODE
        if NODE is None:
            raise AssertionError("node is not on this machine - this case does not skip")
        with open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        a, b = "  var _FLEET_ROSTER_OWNERS = [", "  window._fleetRosterOwner = _fleetRosterOwner;\n"
        self.assertEqual((ui.count(a), ui.count(b)), (1, 1), "the route is not where this case cuts it")
        i = ui.index(a)
        js = "var window = {};\n" + ui[i:ui.index(b, i) + len(b)] + "\nprocess.stdout.write(JSON.stringify(window._fleetRosterOwner(%s)));" % json.dumps(m)
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise AssertionError("the shipped route would not run in node: %s" % r.stderr[-400:])
        return json.loads(r.stdout)

    def test_konyo_on_a_mac_is_konyo_mac_and_nowhere_else(self):
        self.assertEqual(self.owner({"nickname": "Konyo", "platform": "mac"}), "Konyo \u00b7 Mac")
        self.assertEqual(self.owner({"nickname": "Konyo", "platform": "win"}), "", "a guess named another PC's profile")
        self.assertEqual(self.owner({"nickname": "Dean"}), "Dean")
        self.assertEqual(self.owner({"nickname": "someone"}), "")

RED_PROOF = [
    {"why": "v3865 (the r3 review) - a lane that owes 0 reels is drawn as a red debt again (his ALT row: vault lane owes 0); "
            "the fixture's lane owes 0, so this is the debt rule it can judge - the owes>=1 chip is test_a_held_reel_is_not_river_stuck's",
     "file": "tv/control_ui.html",
     "find": "return (mm && +mm[2] > 0) ? mm[1] + ' owes ' + mm[2]",
     "replace": "return mm ? mm[1] + ' owes ' + mm[2]",
     "matches": 1},
    {"why": "REG-3051 follow-up - the river-stuck chip's tip stops naming what waited, and the byte-for-byte pin would not see it",
     "file": "tv/control_ui.html",
     "find": "      if (_waits.length) tip += ' · oldest reel waiting: ' + _waits.join(', ');",
     "replace": "      if (false) tip += ' · oldest reel waiting: ' + _waits.join(', ');",
     "matches": 1},
    {"why": "REG-2768 - the open row's eyes sit across its middle, so a second click enters the shadow",
     "file": "tv/control_ui.html",
     "find": "  .fleet-row.fleet-open > .fleet-open-eyes { display: flex; justify-content: flex-end; margin-right: 14px; }",
     "replace": "  .fleet-row.fleet-open > .fleet-open-eyes { display: flex; justify-content: center; }  .fleet-hd-eyes { min-width: 70%; }",
     "matches": 1},
    {"why": "Grok r1 - the eyes swallow every key again, so Escape no longer closes the cross-reference",
     "file": "tv/control_ui.html",
     "find": "window._shadowOpen(this.getAttribute(\\'data-roster-owner\\'))\">'",
     "replace": "window._shadowOpen(this.getAttribute(\\'data-roster-owner\\'))\" onkeydown=\"event.stopPropagation()\">'",
     "matches": 1},
    {"why": "GBL 2026-10-24 - the click opens the compare but no longer opens the row with its eyes",
     "file": "tv/control_ui.html",
     "find": "    window._fleetRowOpen(row);\n    if (wasOpen) window._fleetCompare(mach);\n",
     "replace": "    window._fleetCompare(mach);\n",
     "matches": 1},
    {"why": "#225 - the first click opens the compare window over the eyes again (one click, two things)",
     "file": "tv/control_ui.html",
     "find": "    if (wasOpen) window._fleetCompare(mach);\n",
     "replace": "    window._fleetCompare(mach);\n",
     "matches": 1},
    {"why": "GBL 2026-10-24 - the eyes route to the wrong profile",
     "file": "tv/control_ui.html",
     "find": "    if (nick === 'Konyo' && m && m.platform === 'mac') return 'Konyo \\u00b7 Mac';\n",
     "replace": "    if (nick === 'Konyo' && m && m.platform === 'mac') return 'Dean';\n",
     "matches": 1},
    {"why": "GBL 2026-10-24 - the diagnostics are not collapsed under ADVANCED",
     "file": "tv/control_ui.html",
     "find": "        _sys = '<details class=\"fx-adv\"><summary>",
     "replace": "        _sys = '<details open class=\"fx-adv\"><summary>",
     "matches": 1},
    {"why": "GBL 2026-10-24 - a fleet refresh shuts the row he opened",
     "file": "tv/control_ui.html",
     "find": "    if (mach) window._fleetOpenRows[mach] = 1;\n",
     "replace": "",
     "matches": 1},
    {"why": "GBL 2026-10-24 - a diagnostic fact is clipped with an ellipsis again",
     "file": "tv/control_ui.html",
     "find": "grid-column: 2; white-space: normal; overflow: visible; text-overflow: clip; }",
     "replace": "grid-column: 2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }",
     "matches": 1},
    {"why": "GBL 2026-10-24 - the hover card's words change with the eyes",
     "file": "tv/control_ui.html",
     "find": "click it again: how this PC films and drains, and their set pieces against yours</div>';",
     "replace": "click it again: how this PC films and drains, their set pieces against yours, and the eyes</div>';",
     "matches": 1},
    {"why": "GrokBot 21:09 (v3809) - this PC's own row offers a shadow of itself again",
     "file": "tv/control_ui.html",
     "find": "    if (isMe) return '';\n",
     "replace": "    if (false) return '';\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=1)
