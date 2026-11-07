# -*- coding: utf-8 -*-
"""v3881 (#125) - ON A PHONE A QUICK WINS CARD'S OTHER PLACES READ: EACH NAME ON THE CARD'S WIDTH, ITS FOUR NUMBERS 2 x 2,
NOTHING OVER ANYTHING.

Found while checking his #125 ask ("top 1 should be the lowest amount of runs and the fifth should be the highest") on real
pixels at 390, the width GrokBot and he read the board at. MEASURED on v3880 (live) and v3881 alike: the Quick wins card
kept its 88px item picture BESIDE its body, so every row had ~217px of a 370px card, and the Other places rows used a phone
grid of '52px minmax(0,1fr) auto' - a number's auto column beside the place - so a name fell to one letter a line
("N o r m a l T Z T h e P i t") and its odds sat over its "runs an hour". Now the picture sits above the body on a phone,
and those rows stand like the ranked rows above them: the picture, the place across two columns, its numbers 2 x 2.

This law looks at the PIXELS (the rects of the shipped page in a real browser, GitHub's - test-venue): F-Uniques, Quick
wins, the first cards that carry Other places, at 390. A browser that will not start is UNKNOWN, never a pass. RED_PROOF
below. [[visual-regression-detector]]
"""
import json
import os
import socket
import subprocess
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass


def _free_port():
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


# ⚠ BEFORE the import: render_check reads its Chrome port once. Never 9222/9223 (his).
_LAW_PORT = os.environ.get("TV_LAW_PORT", "").strip()
os.environ["TV_RENDER_PORT"] = _LAW_PORT if _LAW_PORT.isdigit() and _LAW_PORT not in ("9222", "9223") else str(_free_port())
import render_check as RC  # noqa: E402

WIDTH = 390
CARDS = 3

MEASURE = r"""(function(n){
  var tb = document.querySelector('[data-tab="funi"]');
  if (tb) tb.click();
  if (typeof window.funiSetFilter !== 'function') return JSON.stringify({ err: 'no funiSetFilter' });
  window.funiSetFilter('low');
  var cards = [].filter.call(document.querySelectorAll('#tab-funi .qw-card'), function(c){
    return c.getBoundingClientRect().width > 0 && c.querySelector('.qw-also .qw-row'); }).slice(0, n);
  var hit = function(a, b){ return a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1; };
  return JSON.stringify({ cards: cards.map(function(c){
    var cr = c.getBoundingClientRect();
    return { card: Math.round(cr.width), rows: [].map.call(c.querySelectorAll('.qw-also .qw-row'), function(r){
      var nm = r.querySelector('.qw-name'), pl = r.querySelector('.qw-place'), nr = nm.getBoundingClientRect();
      var lh = parseFloat(getComputedStyle(nm).lineHeight) || 20;
      var parts = [pl].concat([].slice.call(r.querySelectorAll('.qw-stat'))), over = [];
      for (var i = 0; i < parts.length; i++) for (var j = i + 1; j < parts.length; j++)
        if (hit(parts[i].getBoundingClientRect(), parts[j].getBoundingClientRect())) over.push(i + 'x' + j);
      return { name: nm.textContent.trim(), w: Math.round(nr.width), lines: Math.round(nr.height / lh),
               stats: r.querySelectorAll('.qw-stat').length, over: over, right: Math.round(r.getBoundingClientRect().right),
               cardRight: Math.round(cr.right) };
    }) };
  }) });
})(%d)"""

_CACHE = {}


def _render():
    if "r" in _CACHE:
        return _CACHE["r"]
    port = _free_port()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=REPO,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        RC.require_chrome()   # REG-3061 - a browser that will not start is UNKNOWN for this law (a VenueFault), never a red
        try:
            t = RC._Tab("about:blank")
            t.send("Page.enable")
            t.send("Runtime.enable")
            t.send("Emulation.setDeviceMetricsOverride", width=WIDTH, height=5200, deviceScaleFactor=1, mobile=True)
            t.send("Page.navigate", url="http://127.0.0.1:%d/bible.html" % port)
            for _ in range(360):
                time.sleep(0.25)
                try:
                    if t.ev("document.readyState==='complete' && typeof window.funiSetFilter === 'function'") is True:
                        break
                except Exception:
                    pass
            else:
                raise AssertionError("bible.html never exposed funiSetFilter - UNKNOWN, not passing")
            time.sleep(2.0)
            raw = t.ev(MEASURE % CARDS)
            res = json.loads(raw) if raw else {"err": "the measure threw: %r" % (getattr(t, "last_exc", None),)}
            try:
                t.close()
            except Exception:
                pass
        finally:
            RC._chrome_down()
    finally:
        srv.kill()
        srv.wait(10)
    _CACHE["r"] = res
    return res


@unittest.skipUnless(os.path.exists(RC.CHROME or ""), "no Chrome on this machine - the card was not rendered (declared skip 77)")
class AQuickWinsPlaceReadsOnAPhone(unittest.TestCase):

    def test_the_cards_drew_their_other_places(self):
        """PREMISE - PRINT THE DENOMINATOR: three Quick wins cards with Other places, every row a name and four numbers"""
        r = _render()
        self.assertNotIn("err", r, r)
        self.assertEqual(len(r["cards"]), CARDS, "Quick wins drew %d card(s) with Other places at %d" % (len(r["cards"]), WIDTH))
        for c in r["cards"]:
            self.assertTrue(c["rows"], c)
            for row in c["rows"]:
                self.assertTrue(row["name"], row)
                self.assertEqual(row["stats"], 4, row)

    def test_a_place_name_has_the_cards_width(self):
        """* THE POINT - no name stands one letter a line: each gets most of the card, two lines at most"""
        bad = []
        for c in _render().get("cards") or []:
            for row in c["rows"]:
                if row["w"] < 180 or row["lines"] > 2:
                    bad.append("%r: %dpx wide, %d lines (card %dpx)" % (row["name"], row["w"], row["lines"], c["card"]))
        self.assertEqual(bad, [], "; ".join(bad))

    def test_no_number_sits_over_another_or_runs_off_the_card(self):
        bad = []
        for c in _render().get("cards") or []:
            for row in c["rows"]:
                if row["over"]:
                    bad.append("%r: parts %s overlap" % (row["name"], ",".join(row["over"])))
                if row["right"] > row["cardRight"] + 1:
                    bad.append("%r: the row runs past its card (%d > %d)" % (row["name"], row["right"], row["cardRight"]))
        self.assertEqual(bad, [], "; ".join(bad))


RED_PROOF = [
    {"why": "#125 - an Other places row keeps a number's auto column beside its name on a phone (one letter a line)",
     "file": "bible.html",
     "find": "  .qw-also .qw-row{grid-template-columns:52px repeat(2,minmax(0,1fr))}\n",
     "replace": "  .qw-also .qw-row{grid-template-columns:52px minmax(0,1fr) auto}\n  .qw-also .qw-row > .qw-place{grid-column:auto}\n",
     "matches": 1},
    {"why": "#125 - the Quick wins card keeps its picture beside the body on a phone (every row gets ~217px of 370)",
     "file": "bible.html",
     "find": "  #tab-funi .qw-card{flex-wrap:wrap}\n", "replace": "\n", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
