# -*- coding: utf-8 -*-
"""v3847 - EVERY OVERLAY CLOSES THE SAME WAY (Elad 2026-10-30 14:24/14:27/14:28).

Esc closes the topmost overlay only (the one whose x is not covered), a click outside the overlay closes it,
its x closes it, and Esc with nothing open does nothing.  One contract block does this in the console and in
the board; the copies must stay identical, and every overlay x in either file must be one the contract knows.
Measured by hand in a box headless render (no window on the Mac): forensics, theatre, the Mirror key and the
help sheet all close on Esc, outside click and x; Esc on the Mirror key over the heart closes the key only.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UI = open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
BIBLE = open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()
BLOCK = re.compile(r"/\* OVERLAY-CONTRACT v3847.*?/\* /OVERLAY-CONTRACT \*/", re.S)
# x buttons that are not overlays: a banner, a status bar, chips inside a cell or a form
NOT_OVERLAYS = {"fb-x", "rs-x", "vm-cell-x", "cb-mod-x", "cb-grp-x", "mp-pick-x", "mp-bind-x", "vault-find-x",
                "eh-x", "sfp-x", "help-close", "aid-close-btn", "gic-close-btn", "aib-close"}


def _x_classes(src):
    out = set()
    for m in re.finditer(r"<button[^>]*class=\\?[\"']([^\"'\\]+)\\?[\"'][^>]*>\s*([\u00d7\u2715\u2716])", src):
        for c in m.group(1).split():
            if re.search(r"(-x|close|close-btn)$", c):
                out.add(c)
    return out


class EveryOverlayClosesTheSameWay(unittest.TestCase):
    def test_one_contract_in_both_files(self):
        a, b = BLOCK.findall(UI), BLOCK.findall(BIBLE)
        self.assertEqual(len(a), 1, "console must carry the overlay contract once")
        self.assertEqual(len(b), 1, "board must carry the overlay contract once")
        self.assertEqual(a[0], b[0], "the two copies of the overlay contract drifted")

    def test_esc_and_outside_click_close_the_topmost(self):
        c = BLOCK.findall(UI)[0]
        self.assertIn("addEventListener('keydown'", c)
        self.assertIn("e.key !== 'Escape'", c)
        self.assertIn("elementFromPoint", c, "topmost must be the overlay whose x is uncovered")
        self.assertIn("addEventListener('pointerdown'", c)
        self.assertIn("!top.box.contains(e.target)", c)
        self.assertIn("if (!top) return;", c, "Esc with nothing open must do nothing")
        self.assertNotIn("/api/window", c)

    def test_every_overlay_x_is_known_to_the_contract(self):
        sel = re.search(r"var X_SEL = (.*?);\n", BLOCK.findall(UI)[0], re.S).group(1)
        known = set(re.findall(r"\.([a-z0-9-]+)", sel))
        for name, src in (("control_ui.html", UI), ("bible.html", BIBLE)):
            missing = sorted(_x_classes(src) - known - NOT_OVERLAYS)
            self.assertEqual(missing, [], "%s has overlay x buttons the contract does not close: %s" % (name, missing))

    def test_the_help_sheet_has_a_top_right_x(self):
        self.assertRegex(BIBLE, r'<div class="help-content">\s*<button type="button" class="help-x"')

    def test_buttons_glow_and_ease_but_respect_reduced_motion(self):
        for src in (UI, BIBLE):
            css = re.search(r"/\* OVERLAY-X v3847.*?/\* /OVERLAY-X \*/", src, re.S)
            self.assertIsNotNone(css)
            self.assertIn(":hover", css.group(0))
            self.assertIn("transition:", css.group(0))
            self.assertIn("prefers-reduced-motion", css.group(0))

    # v3847 x audit (Elad 14:28): one x, at the same spot, on every overlay
    def test_every_overlay_gets_one_x_pinned_at_the_same_spot(self):
        c = BLOCK.findall(UI)[0]
        self.assertIn("var OVX_INSET = 12, OVX_SIZE = 28;", c)
        self.assertIn("ovxSet(x, 'right', ", c, "the x is not pinned from the card's right edge")
        self.assertIn("x.className = 'ovx-made'", c, "an overlay with no x does not get one")
        self.assertIn(".ovx-made'", re.search(r"var X_SEL = (.*?);\n", c, re.S).group(1),
                      "a made x is not one Esc and outside-click can close")

    def test_a_made_x_does_not_loop_its_own_escape(self):
        self.assertIn("e.__ovxPass ||", BLOCK.findall(UI)[0], "the made x's Escape re-enters the contract")

    # v3847 pin fix (Elad 18:06): one shared inset for both gaps on every card, measured on screen from the card
    def test_both_gaps_share_one_inset_from_the_card(self):
        c = BLOCK.findall(UI)[0]
        self.assertIn("(v.top + OVX_INSET) - xr.top", c, "the top gap is not the shared inset")
        self.assertIn("xr.right - (v.right - OVX_INSET)", c, "the right gap is not the shared inset")
        self.assertIn("if (best && big <= 1) return best;", c, "a panel on a scrim is not its own card")

    def test_a_button_sharing_the_x_class_is_not_the_x(self):
        # tally's RECEIPTS button carries .tly-x; pinning it hid the real x
        self.assertIn("(/^(close|esc)\\b/i.test(t) || (!t && /close/i.test(lab)))", BLOCK.findall(UI)[0])

    def test_an_overlays_own_close_is_pinned_not_doubled_and_gets_room(self):
        c = BLOCK.findall(UI)[0]
        self.assertIn("var x = xOfOverlay(ov, card);", c, "the mule window's own close gets a second made x")
        self.assertIn("ovxClear(card, x, x.getBoundingClientRect());", c, "a header button or title stays under the x")


    # v3847 full gate run: the 250 ms tick rewrote the same styles every tick, so a page never settled (the vault
    # doors law waits for 250 ms with no mutation) - and the second eye: room grew every tick, a bad selector stuck
    def test_the_tick_writes_only_a_change_and_makes_room_once(self):
        c = BLOCK.findall(UI)[0]
        self.assertIn("if (el.style.getPropertyValue(p) !== v || el.style.getPropertyPriority(p) !== 'important') el.style.setProperty(p, v, 'important');", c,
                      "the tick writes styles that did not change, so the page never settles")
        self.assertIn("if (!card.classList.contains('ovx-card')) card.classList.add('ovx-card');", c,
                      "the tick re-adds a class it already set (a mutation every tick)")
        self.assertNotIn(".style.setProperty(", c.replace("el.style.setProperty(p, v, 'important')", ""),
                         "a style write bypasses the change-only writer")
        self.assertIn("if (host.__ovxRoom) continue;", c, "room under the x grows on every tick")
        self.assertIn("try { document.querySelector(s); } catch (eS) { return; }", c,
                      "one selector this engine rejects drops every overlay to the short list")


    def test_cinema_owns_escape_above_every_overlay(self):
        # v3847 CI (v877 rinse): the contract's capture-phase Esc closed the theatre under cinema in the same press
        for name, src in (("control_ui.html", UI), ("bible.html", BIBLE)):
            self.assertIn("if (document.fullscreenElement || document.body.classList.contains('cinema')) return;", BLOCK.findall(src)[0],
                          name + ": Esc in cinema closes the overlay under it instead of leaving cinema")

    def test_a_row_control_is_not_an_overlay_x(self):
        # v3847 CI (v2267): the pinned-x size rule listed .vrg-x, the routing row's remove button; 18 -> 28 px overflowed the row at 901
        for name, src in (("control_ui.html", UI), ("bible.html", BIBLE)):
            for m in re.finditer(r":is\(([^)]*\.th-x[^)]*)\)", src):
                self.assertNotIn(".vrg-x", m.group(1).split(","), name + ": a routing row's remove button is sized as an overlay x")

    def test_the_shelf_x_rides_the_shared_pin(self):
        # v3848 eyes 10:09: #th-shelf-x sat ~30px in from the Shelf card's corner - the Shelf was no overlay to the pin
        for name, src in (("control_ui.html", UI), ("bible.html", BIBLE)):
            also = re.search(r"var OVX_ALSO = '([^']*)'", src).group(1).split(",")
            self.assertIn("#th-shelfov", also, name + ": the Shelf is not an overlay the pin knows")
            tick = src[src.index("function ovxTick()"):src.index("window.__tvOvxTick")]
            self.assertIn("cj.classList.add('ovx-card')", tick[:tick.index("var x = xOfOverlay")],
                            name + ": a nested overlay is not marked before the outer one picks its x")


    def test_a_scrollbar_never_makes_a_scrim_its_own_card(self):
        """v3861 (GrokBot #230 6646161568): the d2jsp picker showed two x at 1280-1920 in a headless guest. Its scrim
        (fixed, inset 0) is the viewport WITHOUT the scrollbar, 15 px under innerWidth, so the full-screen test failed, the
        scrim became its own card, and the tick made a second x on the screen corner. Drives the shipped cardOf in node."""
        import json, shutil, subprocess
        node = shutil.which("node")
        if not node:
            self.skipTest("node absent: UNKNOWN, not passed")
        for name, src in (("control_ui.html", UI), ("bible.html", BIBLE)):
            i = src.index("  function cardOf(ov) {")
            fn = src[i:src.index("  function isX(b) {", i)]
            js = fn + """
var innerWidth = 1280, innerHeight = 720;
function box(w, h, kids){ return { getBoundingClientRect: function(){ return { width: w, height: h }; }, children: kids || [] }; }
var picker = box(1040, 634); picker.id = 'picker';
var out = {};
var document = { documentElement: { clientWidth: 1265, clientHeight: 720 } };
var scrim = box(1265, 720, [picker]); scrim.id = 'scrim';
out.withBar = cardOf(scrim).id;
document = { documentElement: { clientWidth: 1280, clientHeight: 720 } };
var scrimMac = box(1280, 720, [picker]); scrimMac.id = 'scrim';
out.noBar = cardOf(scrimMac).id;
var panel = box(600, 400); panel.id = 'panel';
out.panel = cardOf(panel).id;
process.stdout.write(JSON.stringify(out));
"""
            r = json.loads(subprocess.check_output([node, "-"], input=js.encode("utf-8"), timeout=30).decode())
            with self.subTest(name):
                self.assertEqual(r["noBar"], "picker", name + ": the no-scrollbar premise broke - re-point this case")
                self.assertEqual(r["withBar"], "picker", name + ": with a 15 px scrollbar the scrim became its own card")
                self.assertEqual(r["panel"], "panel", name + ": a panel smaller than the screen is not its own card")

RED_PROOF = [
    {"why": "v3861 - a classic scrollbar makes every scrim its own card again: the d2jsp picker shows two x",
     "file": "bible.html",
     "find": "    var de = document.documentElement, vw = Math.min(innerWidth, (de && de.clientWidth) || innerWidth),\n",
     "replace": "    var de = document.documentElement, vw = innerWidth,\n",
     "matches": 1, "needs": "node"},
    {"why": "v3847 eye - bible.html's cinema Esc guard goes unpinned",
     "file": "bible.html",
     "find": "    if (document.fullscreenElement || document.body.classList.contains('cinema')) return;\n", "replace": "", "matches": 1},
    {"why": "v3847 CI v2267 - the routing row's remove button sized as an overlay x overflows the row",
     "file": "bible.html", "find": ".gbc-close,.cb-x,.vd-close,.vtp-x", "replace": ".gbc-close,.vrg-x,.cb-x,.vd-close,.vtp-x", "matches": 2},
    {"why": "v3847 CI - Esc in cinema also closes the theatre under it",
     "file": "tv/control_ui.html",
     "find": "    if (document.fullscreenElement || document.body.classList.contains('cinema')) return;\n", "replace": "", "matches": 1},
    {"why": "v3847 - the tick rewrites unchanged styles every 250 ms and the page never settles",
     "file": "tv/control_ui.html",
     "find": "    if (el.style.getPropertyValue(p) !== v || el.style.getPropertyPriority(p) !== 'important') el.style.setProperty(p, v, 'important');",
     "replace": "    el.style.setProperty(p, v, 'important');", "matches": 1},
    {"why": "v3847 eye - room under the x grows on every tick",
     "file": "tv/control_ui.html", "find": "        if (host.__ovxRoom) continue;", "replace": "", "matches": 1},
    {"why": "v3847 eye - one bad selector drops every overlay to the short list",
     "file": "tv/control_ui.html", "find": "          try { document.querySelector(s); } catch (eS) { return; }", "replace": "", "matches": 1},
    {"why": "an overlay with no x stays without one",
     "file": "tv/control_ui.html", "find": "x.className = 'ovx-made'", "replace": "x.className = 'ovx-gone'",
     "matches": 1},
    {"why": "the two copies of the contract drift",
     "file": "bible.html", "find": "var OVX_INSET = 12, OVX_SIZE = 28;", "replace": "var OVX_INSET = 16, OVX_SIZE = 28;",
     "matches": 1},
    {"why": "the made x's Escape loops back into the contract",
     "file": "tv/control_ui.html", "find": "e.__ovxPass || ", "replace": "", "matches": 1},
    {"why": "the top gap drifts off the shared inset",
     "file": "tv/control_ui.html", "find": "(v.top + OVX_INSET) - xr.top", "replace": "(v.top + 3) - xr.top", "matches": 1},
    {"why": "the mule window's own close is ignored and a second x is made",
     "file": "tv/control_ui.html", "find": "var x = xOfOverlay(ov, card);", "replace": "var x = xOf(card);", "matches": 1},
    {"why": "v3848 eyes - the Shelf drops off the pin's overlay list",
     "file": "tv/control_ui.html", "find": "'#roster-box,#theatre,#th-shelfov,", "replace": "'#roster-box,#theatre,", "matches": 1},
    {"why": "v3848 eyes - a nested overlay is not marked first, so the theatre takes the Shelf's x",
     "file": "tv/control_ui.html",
     "find": "      if (rj.width >= 200 && rj.height >= 100 && !cj.classList.contains('ovx-card')) cj.classList.add('ovx-card');\n",
     "replace": "", "matches": 1},
    {"why": "what sits under the x keeps sitting there",
     "file": "tv/control_ui.html", "find": "    ovxClear(card, x, x.getBoundingClientRect());\n", "replace": "", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
