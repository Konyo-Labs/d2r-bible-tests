# -*- coding: utf-8 -*-
"""v3881 (#27 round 2, GrokBot's v3879 pass) - A CARD'S NAME FITS ITS OWN BOX (measured at 720 since v3889 - no phone): THE BADGE WRAPS WHOLE, AND THE NAME
HAS THE CARD'S WIDTH.

GrokBot, his live console's board at 390x844 (#230, 21:24): "the Spirit card resized to 390: h2.gic-name = 'Spirit <span
class=gic-grail-badge>Runeword</span>' sits in a 102 px box ... scrollWidth 165 > 102". v3879 had fixed #27 by letting the
badge be an inline-block that "moves to the next line whole" - and a SOURCE law pinned that rule. It could not have worked:
the page-wide `h2{...display:flex...}` makes every card name a FLEX ROW, and a flex row does not wrap, so the badge stayed beside
the name and spilled past the box. MEASURED the same evening at 390 on v3880: 8 of the 10 cards that open overflowed their name
box - runewords (Spirit 165, Enigma 182, Call to Arms 157, Hand of Justice 179 in a 130px box), set pieces (Tal Rasha's
Guardianship 246, Griswold's Redemption 226), a set (Bul-Kathos' Children 222) and a unique (Herald of Zakarum 177).

Two causes, two rules: the name row wraps on a phone (the badge moves under the name whole), and below 480px the header wraps
so the name takes the card's full width (one WORD of "Tal Rasha's Guardianship" is wider than the 130px column the picture and
the close button left it; no wrapping could fit it). After: all ten fit at 390, 480 and 720.

This law looks at the PIXELS (the rects of the shipped page in a real browser, GitHub's - test-venue); the source rules are
test_a_worn_item_draws_its_slots_picture's. A browser that will not start is UNKNOWN, never a pass. RED_PROOF below.
[[visual-regression-detector]] [[source-reading-guard]]
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

#: every kind of card that wears a name + badge in its header: runewords, set pieces, a set, a unique
NAMES = ("Spirit", "Enigma", "Call to Arms", "Hand of Justice", "Tal Rasha's Guardianship", "Griswold's Redemption",
         "Bul-Kathos' Children", "Herald of Zakarum")
#: the card's narrow rule's edge (720). v3889 (#132, his 11-08 "i dont need any mobile anything"): 390 (a phone) and 481 (the
#: first width above the phone header rule) are dropped with the phone page (test_there_is_no_phone_page carries the tombstone)
WIDTHS = (720,)

MEASURE = r"""(function(){ var n = [].filter.call(document.querySelectorAll('#item-detail .gic-name'), function(e){
    return e.getBoundingClientRect().width > 0; })[0];
  if (!n) return JSON.stringify({ err: 'no card name drawn' });
  var r = n.getBoundingClientRect();
  var spill = [].filter.call(n.querySelectorAll('*'), function(k){ var b = k.getBoundingClientRect(); return b.width > 0 && b.right > r.right + 1; })
    .map(function(k){ return k.className || k.tagName; });
  var badge = n.querySelector('.gic-grail-badge, .gic-uber-badge');
  return JSON.stringify({ name: (n.firstChild && n.firstChild.nodeValue || '').trim(), w: r.width, sw: n.scrollWidth, cw: n.clientWidth,
                          spill: spill, badge: badge ? badge.textContent.trim() : null }); })()"""

_CACHE = {}


def _render():
    if "r" in _CACHE:
        return _CACHE["r"]
    port = _free_port()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=REPO,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    res = {}
    try:
        RC.require_chrome()   # REG-3061 - a browser that will not start is UNKNOWN for this law (a VenueFault), never a red
        try:
            t = RC._Tab("about:blank")
            t.send("Page.enable")
            t.send("Runtime.enable")
            for w in WIDTHS:
                t.send("Emulation.setDeviceMetricsOverride", width=w, height=844, deviceScaleFactor=1, mobile=w < 600)
                t.send("Page.navigate", url="http://127.0.0.1:%d/bible.html" % port)
                for _ in range(360):
                    time.sleep(0.25)
                    try:
                        if t.ev("document.readyState==='complete' && typeof window.openDrop === 'function'") is True:
                            break
                    except Exception:
                        pass
                else:
                    raise AssertionError("bible.html never exposed openDrop at %d - UNKNOWN, not passing" % w)
                time.sleep(1.5)
                for nm in NAMES:
                    t.ev("(function(){ try { window.openDrop(%s); } catch (e) {} return 1; })()" % json.dumps(nm))
                    got = None
                    for _ in range(40):
                        time.sleep(0.15)
                        got = json.loads(t.ev(MEASURE))
                        if got.get("name") == nm:
                            break
                    res[(w, nm)] = got
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


@unittest.skipUnless(os.path.exists(RC.CHROME or ""), "no Chrome on this machine - the cards were not rendered (declared skip 77)")
class ACardNameFitsItsBox(unittest.TestCase):

    def test_every_card_opened_with_its_name_and_badge(self):
        """PREMISE - PRINT THE DENOMINATOR: each of the eight cards opened at each width, its name drawn, with a badge"""
        bad = []
        for (w, nm), m in sorted(_render().items()):
            if m.get("err") or m.get("name") != nm or not m.get("badge"):
                bad.append("%d %r: %r" % (w, nm, m))
        self.assertEqual(bad, [], "a card did not open as itself - nothing below was measured for it: " + "; ".join(bad))
        self.assertEqual(len(_render()), len(NAMES) * len(WIDTHS))

    def test_no_card_name_spills_past_its_own_box(self):
        """* THE POINT - GrokBot's Spirit at 390 (scrollWidth 165 > 102), and the 7 more the sweep found"""
        bad = []
        for (w, nm), m in sorted(_render().items()):
            if m.get("err"):
                continue
            if m["sw"] > m["cw"] + 1:
                bad.append("%d %r: scrollWidth %d > %d" % (w, nm, m["sw"], m["cw"]))
            if m["spill"]:
                bad.append("%d %r: %s runs past the name's box" % (w, nm, ", ".join(m["spill"])))
        self.assertEqual(bad, [], "; ".join(bad))

    # v3889 (#132) - test_on_a_phone_the_name_has_the_cards_width (below 480 the name has the card's width) left with the
    # phone widths; its tombstone is in test_there_is_no_phone_page


RED_PROOF = [
    # v3889 round 3 (GitHub's proof shards, b6e17ca70: BLIND) - "cannot wrap again" spilled only at 390 / 481; at 720, the one
    # width this law still measures, every name fits unwrapped, so that tamper could only stay green. This one breaks the same
    # rule in a way 720 shows: the name no longer fits its box at all.
    {"why": "#27 round 2 - the narrow card's name is set too large to fit its box and may not wrap",
     "file": "bible.html",
     "find": "    .gic-name{font-size:20px;overflow-wrap:break-word;flex-wrap:wrap}",
     "replace": "    .gic-name{font-size:48px;white-space:nowrap}", "matches": 1},
    # v3889 (#132) - the phone header rule's proof (.gic-id-block under @media max-width:480px) left with the 390 / 481
    # widths: measured at 720 it could only stay green, and a proof that cannot fail is not one
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
