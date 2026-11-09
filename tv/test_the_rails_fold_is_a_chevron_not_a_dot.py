# -*- coding: utf-8 -*-
"""#174 v-B4 review — THE RAIL'S FOLD IS A CHEVRON HE CAN SEE, NOT A DOT: MEASURED IN PIXELS, IN A REAL BROWSER.

The v-B4 picker drew the weapon rail as the game's type tree, each parent with a fold (open / folded). The fold was the
glyph ▴ / ▾ - the SMALL triangles - at 15px Inter: MEASURED by the review with PIL on the shipped modal at 2000x1300,
Shields' fold drew 4x3 px of ink and Axes' 4x3 (d01_weapon_select_Sorceress_2000.png); theirs, on the same rows of their
planner, 14x8 (63_botd_base_tab.png). This law's own instrument, run on the pre-fix page, read every fold at 4x4
(2000x1300, builder and mule host) and 3x4 (375x812); after the fix 14x9 and 12x8. At 1x they read as dots - the very thing the CSS comment beside them said they no
longer did. Every node law was green: the button, its aria-expanded and its glyph were all in the HTML. Only pixels see it.

This law opens the picker by REAL INPUT in its own headless Chrome and reads the PIXELS of every fold on the rail
(Page.captureScreenshot clipped to the button, once shown and once hidden - its ink is what IT draws, never a
scrollbar beside it - decoded by frozen_frames.png_rows, stdlib, no PIL):

  · THE BUILDER at 2000x1300 (the Tools tab, the Character Builder card, the right-hand slot - pressed at their centres)
    and at 375x812: every fold drawn has at least FLOOR px of ink - two thirds of their measured 14x8, and far above the
    4x3 dot - and an open fold points UP while a folded one points DOWN (the ink's top row narrower than its bottom row
    when open, wider when folded - the mean of each half of its rows), so open and folded are told apart by their shape.
  · A PRESS ON A FOLDED CHEVRON (Axes) opens its node, and its chevron now points up.
  · THE MULE HOST at 2000x1300 (the Vault tab, a mule, its right-hand slot): the same folds, the same ink.

⚠ ITS OWN BROWSER, ON ITS OWN PORT (a free one, set before render_check is imported), killed by the handle it holds.
⚠ NO CHROME ON THIS MACHINE = a DECLARED skip (exit 77), never a pass.
RED_PROOF below.
"""
import json
import os
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

# ⚠ the builder's width law picks a FREE port and sets TV_RENDER_PORT BEFORE it imports render_check (which reads the
# port once, at import) - importing it first gives this law the same discipline and its real-input press
import test_the_character_builder_fits_at_every_width as FT  # noqa: E402
import frozen_frames as FF  # noqa: E402

RC = FT.RC
NO_BROWSER = "no Chrome/Chromium on this machine, so the rail's folds were not rendered"
#: theirs, measured by the review with PIL (63_botd_base_tab.png): the Shields and Axes chevrons, w x h px of ink
THEIRS = (14, 8)
#: two thirds of theirs; the dot this law exists for measured 4x3
FLOOR = (THEIRS[0] * 2 // 3, THEIRS[1] * 2 // 3)
#: a pixel is INK when a channel differs, fold shown vs fold hidden, by more than this
INK = 48

#: the folds a person can see: on screen AND inside the rail's own scroll box (a fold scrolled out of the rail is on
#: screen by its rect and draws nothing - it read 0x0 at 375 before this)
FOLDS = r"""(function(){ var o = [], fs = document.querySelectorAll('#cb-modal .cb-tree .cb-fold'), rl = document.querySelector('#cb-modal .cb-tree');
  var rb = rl ? rl.getBoundingClientRect() : null, top = rb ? rb.top + rl.clientTop : 0, bot = rb ? top + rl.clientHeight : 0;
  for (var i = 0; i < fs.length; i++){ var r = fs[i].getBoundingClientRect(); if (r.width < 1 || r.height < 1) continue;
    if (r.top < 0 || r.bottom > innerHeight || r.left < 0 || r.right > innerWidth) continue;
    if (!rb || r.top < top || r.bottom > bot) continue;
    o.push({ i: i, x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height,   // a clip is in PAGE coordinates (the phone sheet scrolls the page)
             open: fs[i].getAttribute('aria-expanded') === 'true',
             label: fs[i].getAttribute('aria-label') }); }
  return JSON.stringify(o); })()"""

_CACHE = {}


def _png(t, f):
    """the fold's clip, decoded -> (w, h, channels, rows)"""
    import base64
    shot = t.send("Page.captureScreenshot", format="png",
                  clip={"x": f["x"], "y": f["y"], "width": f["w"], "height": f["h"], "scale": 1})
    fd, path = tempfile.mkstemp(suffix=".png")
    try:
        os.write(fd, base64.b64decode(shot["data"]))
        os.close(fd)
        return FF.png_rows(path)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


#: hide / show ONE fold (visibility only - nothing around it moves), so its ink is what IT draws and nothing else: the
#: phone's overlay scrollbar runs through the fold's box at 375 and read as 18 px of "ink" before this
VIS = "(function(i, v){ var f = document.querySelectorAll('#cb-modal .cb-tree .cb-fold')[i]; if (!f) return 0; f.style.visibility = v; return 1; })(%d, %s)"


def _ink(t, f):
    """the ink ONE fold draws: its clip with the fold shown, against the same clip with the fold hidden -> {w, h, top,
    bottom} (top / bottom: the mean span of the ink's upper and lower half of rows - never a single row, whose span is
    whatever the anti-aliasing left there: an up chevron's last row measured 1 px at 375), or {err}"""
    try:
        w, h, ch, shown = _png(t, f)
        if t.ev(VIS % (f["i"], json.dumps("hidden"))) != 1:
            return {"err": "the fold left the page before it was measured - UNKNOWN"}
        try:
            w2, h2, ch2, bare = _png(t, f)
        finally:
            t.ev(VIS % (f["i"], json.dumps("")))
    except FF.Unreadable as e:
        return {"err": "the fold's pixels could not be read (%s) - UNKNOWN" % e}
    if (w, h, ch) != (w2, h2, ch2):
        return {"err": "the two clips differ in size (%dx%d vs %dx%d) - UNKNOWN" % (w, h, w2, h2)}
    n = min(ch, 3)
    ink = [[max(abs(a - b) for a, b in zip(shown[y][x * ch:x * ch + n], bare[y][x * ch:x * ch + n])) > INK for x in range(w)]
           for y in range(h)]
    ys = [y for y in range(h) if any(ink[y])]
    xs = [x for x in range(w) if any(ink[y][x] for y in range(h))]
    if not ys:
        return {"w": 0, "h": 0, "top": 0, "bottom": 0}
    span = lambda y: (max(x for x in range(w) if ink[y][x]) - min(x for x in range(w) if ink[y][x]) + 1)
    half = len(ys) // 2 or 1
    mean = lambda rs: round(sum(span(y) for y in rs) / float(len(rs)), 1)
    return {"w": xs[-1] - xs[0] + 1, "h": ys[-1] - ys[0] + 1, "top": mean(ys[:half]), "bottom": mean(ys[-half:])}


def _read(t, where):
    out = []
    for f in json.loads(t.ev(FOLDS)):
        m = _ink(t, f)
        m.update({"label": f["label"], "open": f["open"], "where": where})
        out.append(m)
    return out


def _load(t, w, h):
    FT._set_size(t, w, h)
    t.send("Page.navigate", url="file://" + os.path.join(ROOT, "bible.html"))
    for _ in range(200):
        time.sleep(0.25)
        try:
            if t.ev("document.readyState==='complete' && !!window.openCharBuilder && !!window.openMuleCard && !!window.LSR") is True:
                break
        except Exception:
            pass
    else:
        raise AssertionError("bible.html never exposed openCharBuilder / openMuleCard in 50s - UNKNOWN, not passing")
    for _ in range(60):
        try:
            if t.ev("document.fonts.status") == "loaded":
                break
        except Exception:
            pass
        time.sleep(0.25)
    time.sleep(0.4)


def _measure():
    if "r" in _CACHE:
        return _CACHE["r"]
    RC.require_chrome()   # REG-3061 - a browser that will not start is UNKNOWN for this law (a VenueFault), never a red
    res = {"input": [], "folds": []}
    try:
        t = RC._Tab("about:blank")
        t.send("Page.enable")
        t.send("Runtime.enable")
        for (w, h) in ((2000, 1300), (901, 900)):   # v3889 (#132) - the narrowest desktop width, where 375 was
            _load(t, w, h)
            # THE BUILDER, BY REAL INPUT: the Tools tab, the Character Builder card, the right-hand slot
            res["input"].append(FT._press(t, '.tab[data-tab="tools"]'))
            time.sleep(0.8)
            res["input"].append(FT._press(t, "#char-builder-card .boss-header"))
            time.sleep(0.6)
            res["input"].append(FT._press(t, '#cb-win .cb-slot[data-slot="rarm"]'))
            time.sleep(0.5)
            res["folds"] += _read(t, "builder %dx%d" % (w, h))
            if w == 2000:
                # a folded chevron pressed: Axes opens, and its chevron turns up
                i = t.ev("(function(){ var fs = document.querySelectorAll('#cb-modal .cb-tree .cb-fold'); for (var i = 0; i < fs.length; i++)"
                         " if (fs[i].getAttribute('aria-label') === 'open Axes') return i; return -1; })()")
                res["input"].append("no folded Axes chevron" if i is None or i < 0 else FT._press(t, "#cb-modal .cb-tree .cb-fold", i))
                time.sleep(0.3)
                res["axes"] = [f for f in _read(t, "builder after the press") if f["label"] in ("fold Axes", "open Axes")]
        # THE MULE HOST, BY REAL INPUT: the Vault tab, a mule, its right-hand slot
        _load(t, 2000, 1300)
        res["input"].append(FT._press(t, '.tab[data-tab="vault"]'))
        time.sleep(1.0)
        res["input"].append(FT._press(t, '.vault-mule[data-vault-mule="uni-weap"] .vm-plate'))
        time.sleep(0.8)
        res["input"].append(FT._press(t, '#vault-detail .mp-slot[data-slot="rarm"]'))
        time.sleep(0.5)
        res["host"] = t.ev("(function(){ var m = document.getElementById('cb-modal'); return !!(m && m.classList.contains('cb-host')); })()")
        res["folds"] += _read(t, "mule 2000x1300")
        try:
            t.close()
        except Exception:
            pass
    finally:
        RC._chrome_down()
    _CACHE["r"] = res
    return res


class TheFoldIsAChevron(unittest.TestCase):

    def test_the_fixture_reached_the_rail_by_real_input(self):
        """PRINT THE DENOMINATOR: a rail with no folds on screen passes every check below"""
        r = _measure()
        self.assertEqual([x for x in r["input"] if x], [], "a real press did not land: %s" % r["input"])
        self.assertIs(r["host"], True, "the mule's slot did not open the builder's picker in the mule host")
        for where in ("builder 2000x1300", "builder 901x900", "mule 2000x1300"):
            n = [f for f in r["folds"] if f["where"] == where]
            self.assertGreaterEqual(len(n), 5, "%s: only %d folds were on screen to measure" % (where, len(n)))
            self.assertTrue(any(f["open"] for f in n) and any(not f["open"] for f in n),
                            "%s: the rail showed no open AND folded chevron to compare" % where)

    def test_every_fold_has_their_chevrons_ink_not_a_dots(self):
        r = _measure()
        bad = ["%s %s: %s" % (f["where"], f["label"], f.get("err") or "%dx%d px of ink" % (f["w"], f["h"]))
               for f in r["folds"] if f.get("err") or f["w"] < FLOOR[0] or f["h"] < FLOOR[1]]
        self.assertEqual(bad, [], "a fold draws less than %dx%d px of ink (theirs %dx%d; the dot was 4x3):\n  %s"
                         % (FLOOR + THEIRS + ("\n  ".join(bad),)))

    def test_open_points_up_and_folded_points_down(self):
        r = _measure()
        bad = []
        for f in r["folds"]:
            if f.get("err") or not f["w"]:
                continue
            up = f["top"] < f["bottom"]
            if f["open"] != up:
                bad.append("%s %s: %s but points %s (upper rows %s px, lower rows %s px)"
                           % (f["where"], f["label"], "open" if f["open"] else "folded", "up" if up else "down", f["top"], f["bottom"]))
        self.assertEqual(bad, [], "a chevron points the wrong way:\n  " + "\n  ".join(bad))

    def test_a_pressed_folded_chevron_opens_and_turns_up(self):
        a = _measure().get("axes") or []
        self.assertEqual(len(a), 1, "Axes' fold is not on screen after the press: %s" % a)
        f = a[0]
        self.assertEqual((f["label"], f["open"]), ("fold Axes", True), "pressing Axes' chevron did not open it")
        self.assertLess(f["top"], f["bottom"], "the opened Axes chevron does not point up: %s" % f)


RED_PROOF = [
    {
        "why": "#174 v-B4 review - the fold is the small-triangle glyph again: ~4x3 px of ink, a dot (theirs 14x8)",
        "file": "bible.html",
        "find": ".cb-fold{display:flex;align-items:center;justify-content:center}\n.cb-tree .cb-fold{color:var(--gold-bright)}\n",
        "replace": ".cb-tree .cb-fold{font-size:var(--fs-cb-title);color:var(--gold-bright)}\n.cb-fold::before{display:none}\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B4 review - open and folded draw the same chevron (only aria-expanded tells them apart)",
        "file": "bible.html",
        "find": ".cb-fold[aria-expanded=\"false\"]::before{transform:translateY(-25%) rotate(135deg)}",
        "replace": ".cb-fold[aria-expanded=\"false\"]::before{}",
        "matches": 1,
    },
]


if __name__ == "__main__":
    if not os.path.exists(RC.CHROME):
        sys.stderr.write("⚪ SKIP — %s. UNMEASURED, declared as a skip (77), never a pass.\n" % NO_BROWSER)
        raise SystemExit(77)
    unittest.main(verbosity=2)
