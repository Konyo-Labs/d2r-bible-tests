# -*- coding: utf-8 -*-
"""REG-3090 (#224, his Q12 2026-10-29: "bottom bar on phones") - ON A PHONE THE TRAY IS ONE BOTTOM BAR THAT RESERVES ITS
OWN HEIGHT, AND THE DESKTOP IS UNCHANGED.

Measured on the vault-copies and vault-find-copies renders at 375 (v3822): the v704 tray column - help, compass, the
tab-scoped S2 legend, the inbox, MOVE TASKS, 44px orbs at right:12px stacked up from the dock - sat over the right ~40px
of the vault column. The locker plates ran under it and FIND's wrapped row lost the ends of words under the compass.
The render gate reported it covered 0/1 because it samples the middle of an element, and test_control's fixed-gutter law
reserves the gutter inside one card only.

At <=600px the column now turns on its side in a bar of its own under the dock (#tray-bar). This law holds the RESERVE,
never an overlap (visual-regression-detector's rule; the pixels are the render gate's `phone-bar` target, on CI):
  * every orb of the column sits IN the bar: its phone anchor no longer climbs on --dock-h, and its inset plus its
    height fits the bar's height - all three read from the stylesheet, never remembered;
  * the row is the column turned on its side: each orb's slot from the corner is its slot up the column (the three
    tab-scoped legends still share one), and the farthest slot still fits the narrowest phone;
  * the bar reserves itself: the dock sits on it, the static band value and the collapsed padding carry it, and the
    dock's own measurement folds it into --dock-h (window._dockReserve, driven in node), so every reserve built on
    --dock-h clears it with no second number;
  * the desktop is unchanged: outside the phone band --tray-bar-h is 0 and the bar is not drawn, and the fold adds
    nothing for a bar of 0;
  * the bar's rules are the LAST word on each orb's anchor (an equal-specificity rule further down would win).
Source-reading on purpose: there is no CSS engine in node and the browser venue is CI's. The comments are stripped
(bounded) and the stripper is checked against the selectors it must keep. RED_PROOF below.
"""
import io
import os
import re
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
import vault_page_node as VPN  # noqa: E402

BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
STYLE_ID = "reg3090-phone-tray-bar"
PHONE = "@media (max-width:600px){"
SHORT_PHONE = "@media (max-width:600px) and (max-height:480px){"
NARROWEST = 320          # the narrowest phone a slot must still fit on
# the column as it stood when this law was written - a PREMISE that the finder reaches them, never the whole list
KNOWN = {".help-btn", ".nav-widget", ".forge-legend-fab", ".tools-legend-fab", ".vault-guide-fab", ".inbox-fab",
         ".vault-tasks-fab"}


def _strip(css):
    """Comments out, BOUNDED: an unbounded /*.*?*/ can run from a /* in a string to the next */ anywhere."""
    return re.sub(r"/\*.{0,8000}?\*/", " ", css, flags=re.S)


def _rules(css):
    """-> [(selector, {prop: value})] for every innermost rule (a rule inside @media included)."""
    out = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        decl = {}
        for d in m.group(2).split(";"):
            if ":" in d:
                k, v = d.split(":", 1)
                decl[k.strip()] = v.strip()
        for sel in m.group(1).split(","):
            out.append((sel.strip(), decl))
    return out


def _block(css, head):
    """The body of the one @media block that opens with `head`, brace-matched. -> str | None"""
    if css.count(head) != 1:
        return None
    i = css.find(head)
    j = k = i + len(head)
    depth = 1
    while k < len(css) and depth:
        depth += {"{": 1, "}": -1}.get(css[k], 0)
        k += 1
    return css[j:k - 1]


def _px(v):
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)px", v or "")
    return float(m.group(1)) if m else None


def _orbs(rules):
    """The tray column: selectors placed at right:12px on a bottom anchored on --dock-h (merged across rules) - the
    same finder test_every_tray_orb_yields_on_a_short_screen uses, so a new orb in the column is a new orb here."""
    right, bottom = set(), set()
    for sel, d in rules:
        if re.match(r"12px\b", d.get("right", "")):
            right.add(sel)
        if "var(--dock-h" in d.get("bottom", ""):
            bottom.add(sel)
    return right & bottom


def _column_slot(rules, orb):
    """How far up the column this orb sits, read from its LAST --dock-h anchor: calc(... + Npx). -> px"""
    n = None
    for sel, d in rules:
        if sel == orb:
            m = re.search(r"var\(--dock-h[^)]*\)\s*\+\s*(\d+)px", d.get("bottom", ""))
            if m:
                n = int(m.group(1))
    return n


class TheTrayIsABarOnAPhone(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(BIBLE, encoding="utf-8") as fh:
            cls.src = fh.read()
        blocks = re.findall(r'<style id="%s">(.*?)</style>' % STYLE_ID, cls.src, re.S)
        if len(blocks) != 1:
            raise AssertionError("PREMISE: bible.html has %d <style id=%r> block(s), not 1" % (len(blocks), STYLE_ID))
        cls.mine = _strip(blocks[0])
        cls.css = _strip("\n".join(re.findall(r"<style\b[^>]*>(.*?)</style>", cls.src, re.S)))
        cls.phone = _block(cls.mine, PHONE)
        if cls.phone is None:
            raise AssertionError("PREMISE: the bar's stylesheet has no single %r block" % PHONE)
        cls.phone_rules = _rules(cls.phone)
        cls.all_rules = _rules(cls.css)            # parsed ONCE: the page's stylesheet is megabytes
        cls.orbs = _orbs(cls.all_rules)

    def _phone(self, sel, prop):
        vals = [d[prop] for s, d in self.phone_rules if s == sel and prop in d]
        return vals[-1] if vals else None

    def _bar_h(self):
        h = _px(self._phone(":root", "--tray-bar-h"))
        self.assertTrue(h and h > 0, "the phone band gives the bar no height: %r" % self._phone(":root", "--tray-bar-h"))
        return h

    def test_the_stripper_keeps_the_rules_it_reads(self):
        for sel in sorted(KNOWN):
            self.assertIn(sel + "{", self.css, "the comment stripper removed %s's rules" % sel)
        self.assertTrue(KNOWN <= self.orbs, "the finder misses orbs in the column: %r" % sorted(KNOWN - self.orbs))

    def test_every_orb_sits_in_the_bar(self):
        bar = self._bar_h()
        heights = [_px(d.get("height")) for s, d in self.all_rules if s in (".help-btn", ".nav-fab") and _px(d.get("height"))]
        self.assertTrue(heights, "could not read the orb height from the stylesheet")
        orb_h = heights[-1]
        self.assertLess(orb_h, 100, "measured an orb %dpx tall - the reader ran past its own rule" % orb_h)
        for orb in sorted(self.orbs):
            b = self._phone(orb, "bottom")
            self.assertIsNotNone(b, "%s has no phone anchor, so on a phone it still climbs the right edge" % orb)
            self.assertNotIn("--dock-h", b, "%s still climbs on --dock-h on a phone: %r" % (orb, b))
            inset = _px(b.replace("!important", ""))
            self.assertIsNotNone(inset, "%s's phone anchor is not a plain inset: %r" % (orb, b))
            self.assertLessEqual(inset + orb_h, bar,
                                 "%s at %spx + %spx tall does not fit a %spx bar" % (orb, inset, orb_h, bar))

    def test_the_row_is_the_column_on_its_side(self):
        slots = {}
        for orb in self.orbs:
            up = _column_slot(self.all_rules, orb)
            self.assertIsNotNone(up, "%s has no --dock-h anchor to place it in the column" % orb)
            r = _px((self._phone(orb, "right") or "").replace("!important", ""))
            self.assertIsNotNone(r, "%s has no phone slot (right:) of its own" % orb)
            slots.setdefault(up, set()).add(r)
        self.assertGreaterEqual(len(slots), 4, "PREMISE: the column has too few slots to say anything: %r" % slots)
        rows = []
        for up in sorted(slots):
            self.assertEqual(len(slots[up]), 1, "orbs that share a column slot are split across the row: %r" % slots[up])
            rows.append(list(slots[up])[0])
        self.assertEqual(rows, sorted(rows), "the row does not keep the column's order from the corner: %r" % rows)
        self.assertEqual(len(set(rows)), len(rows), "two column slots share one place in the row: %r" % rows)
        step = min(b - a for a, b in zip(rows, rows[1:]))
        self.assertGreaterEqual(step, 44, "neighbouring orbs overlap in the row (%spx apart): %r" % (step, rows))
        self.assertLessEqual(rows[-1] + 44 + 12, NARROWEST,
                             "the farthest slot (right:%spx) does not fit a %dpx phone" % (rows[-1], NARROWEST))

    def test_the_bar_reserves_its_own_height(self):
        bar = self._bar_h()
        self.assertEqual(self.src.count('<div id="tray-bar" aria-hidden="true"></div>'), 1, "the bar is missing or doubled")
        d = [dd for s, dd in self.phone_rules if s == "#tray-bar"][-1]
        self.assertEqual((d.get("display"), d.get("position"), d.get("bottom"), d.get("height")),
                         ("block", "fixed", "0", "var(--tray-bar-h)"), "the bar is not the bottom edge: %r" % d)
        z = int(d.get("z-index"))
        self.assertTrue(120 < z < 230, "the bar's z-index %d must sit over the dock (120) and under the orbs (230)" % z)
        self.assertEqual(self._phone(".control-dock", "bottom"), "var(--tray-bar-h)", "the dock does not sit on the bar")
        self.assertIn("var(--tray-bar-h)", self._phone("body:has(.control-dock.dock-collapsed)", "padding-bottom") or "",
                      "a collapsed dock's padding forgets the bar")
        # the first paint, before the dock is measured: the static band value carries the bar
        band = [v for s, dd in _rules(_block(self.css, "@media (max-width: 600px){") or "") if s == ":root"
                for k, v in dd.items() if k == "--dock-h"]
        self.assertTrue(band and "var(--tray-bar-h" in band[-1], "the static --dock-h of the phone band forgets the bar: %r" % band)
        self.assertGreater(bar, 0)

    def test_the_desktop_is_unchanged(self):
        base = [(s, d) for s, d in _rules(self.mine.replace(self.phone, "")) if s in (":root", "#tray-bar")]
        root = [d.get("--tray-bar-h") for s, d in base if s == ":root"]
        self.assertEqual(root[0], "0px", "outside the phone band the bar must have no height: %r" % root)
        self.assertEqual([d.get("display") for s, d in base if s == "#tray-bar"][0], "none",
                         "the bar is drawn on the desktop")
        # every other rule of the bar's stylesheet lives inside a phone media block
        outside = re.sub(r"@media[^{]*max-width:600px[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", " ", self.mine)
        stray = [s for s, d in _rules(outside) if s not in (":root", "#tray-bar")]
        self.assertEqual(stray, [], "these rules reach the desktop: %r" % stray)
        short = _block(self.mine, SHORT_PHONE)
        self.assertIsNotNone(short, "a short phone keeps a bar its hidden orbs no longer use")
        self.assertIn("0px", short)

    def test_the_bar_is_the_last_word_on_every_orbs_anchor(self):
        # only STYLESHEETS below the bar's: the page's scripts are megabytes of brace-free runs this reader must not walk
        at = self.src.find('<style id="%s">' % STYLE_ID)
        later = _strip("\n".join(m.group(1) for m in re.finditer(r"<style\b[^>]*>(.*?)</style>", self.src, re.S)
                                  if m.start() > at))
        self.assertGreater(at, 0)
        hits = sorted(set(s for s, d in _rules(later) if s in self.orbs and ("bottom" in d or "right" in d)))
        self.assertEqual(hits, [], "a stylesheet below the bar's re-anchors %r and would win on a phone" % hits)


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class TheDockMeasurementFoldsTheBar(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(r"""
var R = window._dockReserve;
OUT.has = typeof R === 'function' && typeof window._trayBarH === 'function';
OUT.r = OUT.has ? { phone: R(213, 56), desk: R(213, 0), collapsed: R(40, 56), hidden: R(84, 56), junk: R(213, 'x'), neg: R(213, -3) } : null;
OUT.errors = H.errors.slice(0, 5);
""", timeout=240)

    def test_the_page_booted(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertTrue(self.o["has"], "the fold helpers are not on the page")

    def test_the_bar_is_folded_into_the_dock_height(self):
        r = self.o["r"]
        self.assertEqual((r["phone"], r["collapsed"], r["hidden"]), (269, 96, 140), "the bar is not in --dock-h: %r" % r)

    def test_no_bar_measures_exactly_as_before(self):
        r = self.o["r"]
        self.assertEqual((r["desk"], r["junk"], r["neg"]), (213, 213, 213), "the fold changes a page with no bar: %r" % r)

    def test_the_measurement_asks_the_fold(self):
        with io.open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        i = src.find("  var _dockSync = function(){")
        self.assertGreater(i, 0, "_dockSync is gone - re-point this law")
        body = src[i:src.find("\n  };\n", i)]
        code = "\n".join(l.split("//", 1)[0] for l in re.sub(r"/\*.{0,4000}?\*/", " ", body, flags=re.S).split("\n"))
        self.assertIn("h = window._dockReserve(h, window._trayBarH());", code,
                      "the dock's measurement does not fold the bar into --dock-h")


RED_PROOF = [
    {"why": "REG-3090 - the help orb keeps climbing the right edge on a phone",
     "file": "bible.html",
     "find": "  .help-btn,.nav-widget,.forge-legend-fab,.tools-legend-fab,.vault-guide-fab,.inbox-fab,.vault-tasks-fab{bottom:6px!important}\n",
     "replace": "  .nav-widget,.forge-legend-fab,.tools-legend-fab,.vault-guide-fab,.inbox-fab,.vault-tasks-fab{bottom:6px!important}\n",
     "matches": 1},
    {"why": "REG-3090 - the inbox takes MOVE TASKS's slot in the row",
     "file": "bible.html",
     "find": "  .inbox-fab{right:168px!important}\n",
     "replace": "  .inbox-fab{right:220px!important}\n",
     "matches": 1},
    {"why": "REG-3090 - the dock does not sit on the bar",
     "file": "bible.html",
     "find": "  .control-dock{bottom:var(--tray-bar-h)}\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3090 - the bar is drawn on the desktop too",
     "file": "bible.html",
     "find": ":root{--tray-bar-h:0px}\n#tray-bar{display:none}\n@media (max-width:600px){\n",
     "replace": ":root{--tray-bar-h:0px}\n#tray-bar{display:block}\n@media (max-width:600px){\n",
     "matches": 1},
    {"why": "REG-3090 - the dock's measurement forgets the bar, so every reserve built on --dock-h is 56px short",
     "file": "bible.html",
     "find": "    return dockH + ((isFinite(b) && b > 0) ? Math.ceil(b) : 0);\n",
     "replace": "    return dockH;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3090 - the first paint of the phone band reserves the dock and not the bar",
     "file": "bible.html",
     "find": "  :root{ --dock-h: calc(225px + var(--tray-bar-h, 0px)); }",
     "replace": "  :root{ --dock-h: 225px; }",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
