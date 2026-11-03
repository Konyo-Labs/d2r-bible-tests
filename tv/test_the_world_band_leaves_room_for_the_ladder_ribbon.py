# -*- coding: utf-8 -*-
"""#218 — THE WORLD BAND LEAVES ROOM FOR THE LADDER RIBBON IT STACKS ABOVE.

Found by LOOKING at Grok Bot's native Linux pack (visual-pass-20260924T012231Z, full-bible/03a): the
🐧 LINUX band covered the top half of "🪜 LADDER ACCOUNT — separate economy · your main account is
untouched" on every tick, while every gate stayed green and the bot filed the page SAW.

MEASURED in a headless render of the same seat (Linux UA, machine=windows, profile=ladder), before:

    width   band                      ladder ribbon      overlap
    1280    top 96  h 35  font 16px   top 120  h 21      11 px
    1120    top 96  h 35  font 16px   top 120  h 21      11 px
     901    top 128 h 35  font 16px   top 152  h 21      11 px
     375    top 167 h 21  font 9px    top 191  h 21       0 px   (the <=700px rule sets a size)

The band was DECLARED `font:var(--fw-semibold) 11px/1 inherit`. `inherit` is a CSS-wide keyword, not a
font family, so the shorthand is invalid — and because it contains var() it is invalid at
COMPUTED-value time, which drops the whole `font` to the inherited value: 16px, 35px tall, painting
over a ladder ribbon whose stack offset (`body.cousin-shell #ladder-ribbon{top:24px}`, v665.1) was
sized for the 11px band the author wrote. The ladder ribbon carries the identical shorthand and is
rescued only by a later `font-size:9.5px!important`. After the longhands: band 22px, overlap 0 at all
five widths.

⚠ A GEOMETRY GATE WOULD RUN ONLY ON CI; THIS IS A PARSE, DETERMINISTIC ON EVERY MACHINE — the same
choice visual-regression-detector ④b records for the grid track that blew the page open. It pins the
RESERVE law (the band's line box + padding fits inside the stack offset, both read from the file),
never the number 22. [[visual-regression-detector]] [[two-fixes-broke-each-other]]
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

#: a font shorthand whose FAMILY slot is a CSS-wide keyword — invalid, and silently dropped
_BAD_FONT = re.compile(r"(?<![-\w])font\s*:\s*[^;{}]*?\d(?:\.\d+)?(?:px|em|rem)(?:\s*/\s*[\d.]+[a-z%]*)?\s+"
                       r"(?:inherit|initial|unset|revert)\s*(?:[;}]|!important)")


def _css():
    """Every <style> block's text, comments stripped — never the whole file.

    ⚠ The eye on the shipped v3485, finding [3]: scanning all of bible.html let a JS STRING move the
    shorthand count, and a rule QUOTED in a comment could satisfy or fail anything."""
    with io.open(BIBLE, encoding="utf-8") as fh:
        src = fh.read()
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", src, flags=re.S | re.I))
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)


def _rule(css, selector):
    """The declaration block of the FIRST rule whose selector is EXACTLY `selector`.

    ⚠ Finding [3]: `[}\\s]#id{` also matched `body.cousin-min #cousin-ribbon{`. The selector must
    begin a rule — at a line start or right after a closing brace."""
    m = re.search(r"(?:^|\})\s*" + re.escape(selector) + r"\s*\{([^}]*)\}", css, flags=re.M)
    return m.group(1) if m else None


def _tokens(css):
    """`--name: value` pairs from the :root rules — the type tokens the visual lock requires."""
    out = {}
    for blk in re.findall(r":root\s*\{([^}]*)\}", css):
        for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+)", blk):
            out.setdefault(k.strip(), v.strip())
    return out


def _value(decls, prop, tokens):
    """A declaration's value with one level of var(--token) resolved from :root. -> str | None"""
    m = re.search(r"(?<![-\w])" + re.escape(prop) + r"\s*:\s*([^;]+)", decls or "")
    if not m:
        return None
    v = m.group(1).strip()
    t = re.fullmatch(r"var\(\s*(--[\w-]+)\s*\)", v)
    return tokens.get(t.group(1)) if t else v


def _px(decls, prop, tokens=None):
    v = _value(decls, prop, tokens or {})
    m = re.fullmatch(r"([\d.]+)px", v or "")
    return float(m.group(1)) if m else None


class TheWorldBandLeavesRoomForTheLadderRibbon(unittest.TestCase):

    def setUp(self):
        self.css = _css()
        self.tok = _tokens(self.css)
        self.band = _rule(self.css, "#cousin-ribbon")
        self.assertIsNotNone(self.band, "premise: the #cousin-ribbon rule is gone — this law "
                                        "judges nothing, which is UNMEASURED, not clean")

    def test_the_band_declares_a_font_the_browser_will_keep(self):
        self.assertIsNone(_BAD_FONT.search(self.band),
                          "#cousin-ribbon uses a font shorthand whose family is a CSS-wide keyword — "
                          "invalid, so the band falls back to the page font (measured 16px, 35px tall)")
        self.assertIsNotNone(_px(self.band, "font-size", self.tok),
                             "the band declares no font size that resolves to px (tokens: %r)"
                             % _value(self.band, "font-size", self.tok))

    def test_the_band_fits_inside_the_stack_offset_the_ladder_ribbon_was_given(self):
        """THE RESERVE, read from the file on both sides — never the number 22."""
        # ⚠ finding [1]: a word boundary, or `padding-top:`/`margin-top:` would be read as the offset
        m = re.search(r"body\.cousin-shell\s+#ladder-ribbon\s*\{[^}]*?(?<![-\w])top\s*:\s*([\d.]+)px",
                      self.css)
        self.assertIsNotNone(m, "premise: the ladder ribbon's stack offset is gone")
        offset = float(m.group(1))
        fs = _px(self.band, "font-size", self.tok)
        lhv = _value(self.band, "line-height", self.tok) or ""
        # ⚠ finding [2]: a unitless number or px only — `120%` or `1.2em` must REFUSE, never be
        # read as 120 and multiplied
        lh = re.fullmatch(r"([\d.]+)(px)?", lhv)
        self.assertTrue(fs and lh, "the band's font-size or line-height does not resolve to a number "
                                   "(%r / %r)" % (_value(self.band, "font-size", self.tok), lhv))
        line = float(lh.group(1)) if lh.group(2) else float(lh.group(1)) * fs
        pad = re.search(r"(?<![-\w])padding\s*:\s*([\d.]+)px\s+[\d.]+px\s+([\d.]+)px", self.band)
        self.assertIsNotNone(pad, "premise: the band's vertical padding is not in the shape read here")
        tall = line + float(pad.group(1)) + float(pad.group(2))
        self.assertLessEqual(tall, offset,
                             "the band is %.1fpx tall (line %.1f + padding %s/%s) and the ladder ribbon "
                             "is stacked %.1fpx below its top — it paints over the ribbon"
                             % (tall, line, pad.group(1), pad.group(2), offset))
        tog = _rule(self.css, "#cousin-ribbon .cr-tog")
        self.assertIsNotNone(tog, "premise: the band's toggle rule is gone")
        # ⚠ finding [2]: a DECLARED toggle size that is not px (2em, 20pt) was passed unjudged. Declared
        # and unreadable is a refusal; only an absent one inherits the band's size.
        tval = _value(tog, "font-size", self.tok)
        tfs = _px(tog, "font-size", self.tok)
        self.assertFalse(tval is not None and tval != "inherit" and tfs is None,
                         "the toggle declares font-size %r, which this law cannot resolve to px — "
                         "it may set a line box taller than the stack offset" % tval)
        self.assertTrue(tfs is None or tfs <= fs,
                        "the toggle declares a font larger than the band (%s > %s) — it sets the height"
                        % (tfs, fs))

    def test_the_invalid_font_shorthand_class_does_not_grow(self):
        """⚠ NINE OTHER SITES carry the same shorthand and were deliberately NOT changed: each renders
        at its inherited size today, and correcting it resizes text he has accepted. A ratchet, not a
        silence: the count may only fall, and every site is named."""
        sites = [m.start() for m in _BAD_FONT.finditer(self.css)]
        self.assertLessEqual(len(sites), 9,
                             "a NEW font shorthand with a CSS-wide keyword as its family arrived — it "
                             "is dropped at computed time and renders at whatever it inherits (%d sites)"
                             % len(sites))
        self.assertGreater(len(sites), 0, "premise: the scan finds none at all, so it may be blind — "
                                          "if the nine were fixed, lower the ceiling to 0 and delete "
                                          "this line")


def _band_tall(band, tok):
    """The band's line box plus its vertical padding, read from its own rule. -> float | None"""
    fs = _px(band, "font-size", tok)
    lh = re.fullmatch(r"([\d.]+)(px)?", _value(band, "line-height", tok) or "")
    pad = re.search(r"(?<![-\w])padding\s*:\s*([\d.]+)px\s+[\d.]+px\s+([\d.]+)px", band or "")
    if not (fs and lh and pad):
        return None
    line = float(lh.group(1)) if lh.group(2) else float(lh.group(1)) * fs
    return line + float(pad.group(1)) + float(pad.group(2))


class TheWorldBandLeavesRoomForTheFramedSearch(unittest.TestCase):
    """#220 (REG-2913) - inside the console frame (body.engine-driven) the tab row is hidden and the
    search is the first row, so on a Windows board the fixed band (and on a ladder profile the ribbon
    stacked under it) painted over its top. GrokBot measured ~10px of #gsearch-input covered on the
    Mac's shadow of the ALT. The reserve is read from the file on both sides, never the number 22."""

    def setUp(self):
        self.css = _css()
        self.tok = _tokens(self.css)
        self.tall = _band_tall(_rule(self.css, "#cousin-ribbon"), self.tok)
        self.assertIsNotNone(self.tall, "premise: the band's height cannot be read from its rule")

    def _top(self, selector):
        decls = _rule(self.css, selector)
        self.assertIsNotNone(decls, "no rule reserves the band's room above the framed search (%s)"
                             % selector)
        m = re.search(r"(?<![-\w])margin-top\s*:\s*([\d.]+)px\s*(!important)?", decls)
        self.assertIsNotNone(m, "%s declares no px margin-top" % selector)
        # a plain margin here is INERT: v640 sets .gsearch-wrap's margin with !important
        if re.search(r"(?:^|\})\s*\.gsearch-wrap\s*\{[^}]*(?<![-\w])margin\s*:[^;}]*!important",
                     self.css, flags=re.M):
            self.assertTrue(m.group(2), "%s reserves %spx without !important, and a .gsearch-wrap rule "
                            "sets its margin !important - the reserve never applies" % (selector, m.group(1)))
        return float(m.group(1))

    def test_the_framed_windows_search_starts_below_the_band(self):
        top = self._top("body.engine-driven.cousin-shell .gsearch-wrap")
        self.assertGreaterEqual(top, self.tall,
                                "the framed search starts %.1fpx down and the band is %.1fpx tall - "
                                "the band paints over the search" % (top, self.tall))

    def test_a_framed_ladder_search_starts_below_both_ribbons(self):
        m = re.search(r"body\.cousin-shell\s+#ladder-ribbon\s*\{[^}]*?(?<![-\w])top\s*:\s*([\d.]+)px",
                      self.css)
        self.assertIsNotNone(m, "premise: the ladder ribbon's stack offset is gone")
        top = self._top("body.engine-driven.cousin-shell.ladder-profile .gsearch-wrap")
        # the ladder ribbon's own line box is not readable (its font shorthand is invalid, so it
        # inherits); the band's is, and the two ribbons share one shape - the band bounds it
        need = float(m.group(1)) + self.tall
        self.assertGreaterEqual(top, need,
                                "the framed ladder search starts %.1fpx down; the ladder ribbon is "
                                "stacked %spx under a %.1fpx band, so it needs %.1fpx"
                                % (top, m.group(1), self.tall, need))

    def test_the_moved_search_clears_the_build_badge(self):
        """REG-2913 round 2 - the reserve moved the search down into the fixed build badge's band (CDP, 1440 and 901:
        the badge covered the magnifier). The badge's box is read from ITS rule (left + the max-width cap); the framed
        search must clear it wherever the badge shows, with !important or v640's margin wins again."""
        badge = None
        for m in re.finditer(r"(?:^|\})\s*#v687-build-badge\s*\{([^}]*)\}", self.css, flags=re.M):
            if re.search(r"(?<![-\w])max-width\s*:", m.group(1)):
                badge = m.group(1)
                break
        self.assertIsNotNone(badge, "premise: the build badge's positioned rule (with its max-width cap) is gone")
        left, cap = _px(badge, "left"), _px(badge, "max-width")
        self.assertTrue(left is not None and cap is not None, "premise: the badge's left or max-width is not in px")
        hid = re.search(r"@media\s*\(max-width:\s*(\d+)px\)\s*\{\s*#v687-build-badge\s*\{[^}]*display\s*:\s*none", self.css)
        self.assertIsNotNone(hid, "premise: the badge's narrow-width hide rule is gone")
        clear = re.search(r"@media\s*\(min-width:\s*(\d+)px\)\s*\{\s*body\.engine-driven\.cousin-shell\s+\.gsearch-wrap"
                          r"\s*\{[^}]*(?<![-\w])margin-left\s*:\s*([\d.]+)px\s*(!important)?", self.css)
        self.assertIsNotNone(clear, "the framed Windows search does not clear the build badge - it sits under it")
        self.assertLessEqual(int(clear.group(1)), int(hid.group(1)) + 1,
                             "the clearance starts at %spx but the badge shows from %dpx" % (clear.group(1), int(hid.group(1)) + 1))
        self.assertTrue(clear.group(3), "the clearance has no !important, so v640's .gsearch-wrap margin keeps it inert")
        self.assertGreater(float(clear.group(2)), left + cap,
                           "the search starts %spx in; the badge reaches %.1fpx (left %.1f + cap %.1f)"
                           % (clear.group(2), left + cap, left, cap))


RED_PROOF = [
    {
        "why": "#218 - the band's font shorthand restored: `inherit` as the family is invalid, the band "
               "falls back to 16px and paints over the ladder ribbon",
        "file": "bible.html",
        "find": "font-weight:var(--fw-semibold);font-size:var(--fs-meta);line-height:var(--lh-none);/* #218",
        "replace": "font:var(--fw-semibold) 11px/1 inherit;/* #218",
        "matches": 1,
    },
    {
        "why": "#218 - a band taller than its stack offset: the reserve law, not the number",
        "file": "bible.html",
        "find": "font-weight:var(--fw-semibold);font-size:var(--fs-meta);line-height:var(--lh-none);/* #218",
        "replace": "font-weight:var(--fw-semibold);font-size:16px;line-height:var(--lh-none);/* #218",
        "matches": 1,
    },
    {
        "why": "REG-2913 - the framed Windows search reserves less than the band's height",
        "file": "bible.html",
        "find": "body.engine-driven.cousin-shell .gsearch-wrap{margin-top:26px!important}",
        "replace": "body.engine-driven.cousin-shell .gsearch-wrap{margin-top:12px!important}",
        "matches": 1,
    },
    {
        "why": "REG-2913 - a plain margin is inert under v640's !important .gsearch-wrap margin",
        "file": "bible.html",
        "find": "body.engine-driven.cousin-shell .gsearch-wrap{margin-top:26px!important}",
        "replace": "body.engine-driven.cousin-shell .gsearch-wrap{margin-top:26px}",
        "matches": 1,
    },
    {
        "why": "REG-2913 - a framed ladder search reserves the band but not the ribbon stacked under it",
        "file": "bible.html",
        "find": "body.engine-driven.cousin-shell.ladder-profile .gsearch-wrap{margin-top:49px!important}",
        "replace": "body.engine-driven.cousin-shell.ladder-profile .gsearch-wrap{margin-top:26px!important}",
        "matches": 1,
    },
    {
        "why": "REG-2913 round 2 - the moved search no longer clears the build badge",
        "file": "bible.html",
        "find": "body.engine-driven.cousin-shell .gsearch-wrap{margin-left:196px!important}",
        "replace": "body.engine-driven.cousin-shell .gsearch-wrap{margin-left:100px!important}",
        "matches": 1,
    },
    {
        "why": "REG-2913 round 2 - the badge clearance without !important is inert under v640's margin",
        "file": "bible.html",
        "find": "body.engine-driven.cousin-shell .gsearch-wrap{margin-left:196px!important}",
        "replace": "body.engine-driven.cousin-shell .gsearch-wrap{margin-left:196px}",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
