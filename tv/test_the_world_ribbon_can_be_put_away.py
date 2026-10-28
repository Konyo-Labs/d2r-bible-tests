#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ v3272 — A BAND HE CANNOT GET RID OF IS A TRAP, AND BOTH PLATFORMS HAD ONE.

Grok Bot, from his NATIVE Linux seat, 2026-09-17 18:06 IDT: **"Trap: persistent 🐧 LINUX toast."**

He is right about the shape. `#cousin-ribbon` is `position:fixed; top:0; z-index:2000`, appended
once on every non-Mac machine and removed by NOTHING — five references in bible.html, not one of
them a hide or a remove. It looks like a toast and behaves like furniture.

It is the exact TWIN of what Konyo reported the same day on the other platform: *"that TVdaiblo
banner lol still there uptop only on my macbook"*. Each machine had its own permanent
top-of-screen band, and neither could be put away. The Mac one belongs to pywebview's cocoa code
and its fix crashed his console at v3206 (REG-1081); **this one is ours**.

⚠ IT COLLAPSES, IT DOES NOT VANISH — and that is the whole design. Five CSS rules push
`#v687-build-badge`, `#ladder-ribbon` and `#tvf-console-return` down to clear this ribbon.
Removing the element would leave every one of those reservations holding empty space, and v2061
already measured this family colliding at 375/480/560/640. The collapsed state keeps the SAME
HEIGHT and sheds only width, so no clamp changes and no new collision surface.
[[the-unjoined-end]] [[copy-drift]]

⚠ AND THE BAND STAYS `pointer-events:none`. It is 442px wide at top-centre and v2061 measured it
crossing ⌂CONSOLE below 684px; making the whole band clickable would hand it the power to eat that
click. Only the badge takes pointer events.
"""

import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")

SRC = io.open(BIBLE, encoding="utf-8").read()


def _js_only(src):
    """Drop /* ... */ comments so a law never reads its own commentary. -> str

    ⚠ This repo's comments routinely NAME the thing being asserted; four laws in one session went
    green over prose. [[presence-law-vs-reachability-law]]
    """
    out, i = [], 0
    while True:
        j = src.find("/" + "*", i)
        if j < 0:
            out.append(src[i:]); break
        out.append(src[i:j])
        k = src.find("*" + "/", j)
        if k < 0:
            break
        i = k + 2
    return "".join(out)


def _between(src, start, end):
    """Text between two REAL anchors, or None. Never a fixed-size window. -> str|None"""
    i = src.find(start)
    if i < 0:
        return None
    j = src.find(end, i + len(start))
    return src[i:j + len(end)] if j > i else None


CODE = _js_only(SRC)


class TheWorldRibbonCanBePutAway(unittest.TestCase):

    def _block(self):
        blk = _between(CODE, "_wr.id='cousin-ribbon'", "document.body.appendChild(_wr);")
        self.assertIsNotNone(blk, "the world ribbon is gone or renamed — this law found nothing")
        return blk

    def test_the_ribbon_HAS_a_control_that_puts_it_away(self):
        """⚠ BEHAVIOURAL SHAPE, not a string: a handler that toggles the body class is what makes
        it dismissible. Asserting the class NAME appears would stay green over a dead button."""
        blk = self._block()
        self.assertIn("cr-tog", blk, "there is no badge control, so the band cannot be put away")
        self.assertIn("onclick", blk, "the badge is decoration — nothing is wired to it")
        self.assertIn("classList.toggle('cousin-min')", blk,
                      "the click does not actually change the ribbon's state")

    def test_the_choice_SURVIVES_A_RELOAD(self):
        """A dismiss he has to repeat on every load is not a dismiss."""
        blk = self._block()
        self.assertIn("localStorage.setItem", blk, "the choice is forgotten the moment he reloads")
        self.assertIn("localStorage.getItem", blk, "the remembered choice is never read back")

    def test_the_BAND_never_takes_a_click_only_the_badge_does(self):
        """⚠⚠ THE LAW THAT KEEPS THIS FROM BECOMING A WORSE TRAP. v2061 measured this ribbon
        crossing ⌂CONSOLE's right edge below 684px. A band with pointer-events:auto at top-centre
        would swallow that click, which is a navigation trap traded for a cosmetic one."""
        rule = _between(CODE, "#cousin-ribbon{position:fixed", "}")
        self.assertIsNotNone(rule, "the ribbon's own rule is gone")
        self.assertIn("pointer-events:none", rule,
                      "the whole band now takes clicks and can eat the console button")
        tog = _between(CODE, "#cousin-ribbon .cr-tog{", "}")
        self.assertIsNotNone(tog, "the badge has no rule, so it cannot receive the click")
        self.assertIn("pointer-events:auto", tog, "the badge cannot be clicked")

    def test_COLLAPSING_SHEDS_WIDTH_ONLY_so_every_clamp_stays_valid(self):
        """⚠⚠ THE REASON THIS COLLAPSES RATHER THAN HIDES. Five rules reserve room for this
        ribbon. A collapsed state that changed HEIGHT — or `display:none` on the ribbon itself —
        would leave all five holding space for something that is not there."""
        blk = _between(CODE, "body.cousin-min #cousin-ribbon", "\n#") or ""
        self.assertIn("display:none", blk,
                      "nothing is hidden when collapsed, so the band never shrinks")
        self.assertIn(".cr-txt", blk,
                      "the collapse does not target the TEXT, so it may be hiding the whole band")
        # the ribbon itself must never be display:none — that is the clamp-breaking form
        self.assertNotRegex(
            blk, r"body\.cousin-min\s+#cousin-ribbon\s*\{[^}]*display\s*:\s*none",
            "the collapsed state hides the RIBBON, which leaves five clamps reserving empty space")

    def test_the_collapsed_badge_LEAVES_THE_CENTRE_and_the_controls_alone(self):
        """★ MEASURED ON REAL PIXELS, and the first two placements were both wrong.

            centre (original)   onTitle TRUE  · hits []                 ← sits on his own title
            right:10px          onTitle false · hits ['pp-btn pp-ladder'] ← sits on the profile
                                                                          switcher, and the badge
                                                                          is the part that TAKES
                                                                          clicks: a navigation trap
            left:10px           onTitle false · hits []                 ← clean at 1440 and 901

        The geometry check passed on the centred version — height unchanged, width shrank — and
        only LOOKING at the frame showed a blue blob over "Konyo's D2R Farming Bible".
        [[visual-regression-detector]] He must not be the detector.
        """
        rule = _between(CODE, "body.cousin-min #cousin-ribbon{", "}")
        self.assertIsNotNone(rule, "the collapsed rule is gone")
        self.assertIn("left:10px", rule,
                      "the collapsed badge is not pinned to the clear edge the measurement chose")
        self.assertIn("transform:none", rule,
                      "the centring transform survives, so the badge still lands mid-title")
        self.assertNotIn("right:10px", rule,
                         "the badge is back on the right edge, where it covers .pp-ladder — and "
                         "the badge is the one part that takes clicks")

    def test_the_badge_LOOKS_like_a_control(self):
        """★ v3276 — A CONTROL HE CANNOT SEE IS A CONTROL HE DOES NOT HAVE.

        v3272 made this band collapsible. GrokBot's NEXT native LOOKED, on **v3274**, still filed
        it: *"LINUX toast persistent (informational) — NOT CLICKED."* The fix had shipped and was
        unreachable in practice, because the badge was styled `background:none; border:0` —
        visually identical to an emoji sitting in a sentence. `cursor:pointer` and a `title` only
        announce themselves to someone already hovering the right pixel, and he had no reason to
        hover it. [[the-unjoined-end]]
        """
        rule = _between(CODE, "#cousin-ribbon .cr-tog{", "}")
        self.assertIsNotNone(rule, "the badge rule is gone")
        self.assertNotIn("background:none", rule,
                         "the badge is painted like plain text again, so nothing marks it as "
                         "something he can press")
        self.assertIn("box-shadow:inset", rule, "the badge has no visible ring")
        self.assertIn("border-radius", rule, "the badge is not shaped like a control")

    def test_the_affordance_CANNOT_change_the_ribbon_height(self):
        """⚠⚠ THE GUARD ON THAT FIX, and the reason this rule looks the way it does. Five CSS
        rules reserve VERTICAL room for this ribbon. A `border` or vertical padding on the badge
        would grow the line box and every one of those clamps would be measuring the wrong height —
        undoing the whole reason v3272 collapses rather than hides.

        `inset box-shadow` paints no layout, and left/right padding cannot change a line box's
        height. Measured after the change at 1440: ribbon 35px expanded, 35px collapsed, top 96
        both ways — identical to before.
        """
        rule = _between(CODE, "#cousin-ribbon .cr-tog{", "}")
        self.assertIn("border:0", rule,
                      "the badge grew a border, which adds height and breaks five clamps")
        self.assertIn("padding:0 5px", rule,
                      "the badge's padding is no longer horizontal-only, so it can change the "
                      "ribbon's height")

    def test_the_information_is_RECOVERABLE_and_the_badge_still_names_the_world(self):
        """⚠ Collapsing must not destroy the fact. The badge stays, it carries the platform
        glyph, and its title says which world this is so the answer is one hover away."""
        blk = self._block()
        self.assertIn("_wb.textContent=_wm.i", blk,
                      "the collapsed badge does not carry the platform glyph, so it says nothing")
        self.assertIn("_wm.w", blk, "the world NAME is not reachable from the collapsed state")
        self.assertIn("aria-expanded", blk,
                      "the control does not tell assistive tech whether it is open or closed")

    def test_the_TEXT_still_says_what_it_always_said(self):
        """⚠ this fix is about reachability, not wording. The sentence he has read for 2600
        versions must survive untouched. [[design-is-fine-until-he-says]]"""
        blk = self._block()
        self.assertIn("its own world", blk, "the world sentence was rewritten by a dismiss fix")
        self.assertIn("Mac untouched", blk, "the isolation reassurance was dropped")

RED_PROOF = [
    {"why": "v3272 - the world ribbon's put-away choice is forgotten on every reload",
     "file": "bible.html",
     "find": "    try { localStorage.setItem(_wkey, min ? '1' : '0'); } catch(e){}\n",
     "replace": "    try { void 0; } catch(e){}\n",
     "matches": 1},
    {"why": "v3272 - the whole band takes clicks and can eat the console button below 684px",
     "file": "bible.html",
     "find": "box-shadow:0 2px 10px rgba(0,0,0,.45);pointer-events:none;white-space:nowrap;max-width:92vw",
     "replace": "box-shadow:0 2px 10px rgba(0,0,0,.45);pointer-events:auto;white-space:nowrap;max-width:92vw",
     "matches": 1},
]


if __name__ == "__main__":
    # ⚠ this file's own docstring carries 🐧 and ⚠. On a cp1255 console (his Windows PC) printing
    # them raises mid-REPORT, so a clean tree exits non-zero and the failure looks like the code.
    # [[windows-powershell-gotchas]]
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    unittest.main(verbosity=2)
