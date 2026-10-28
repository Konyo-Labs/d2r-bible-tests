# -*- coding: utf-8 -*-
"""REG-2862 - EVERY ORB IN THE TRAY COLUMN YIELDS ON A SHORT SCREEN, AND A DOOR THAT YIELDS HAS ANOTHER WAY IN.

v1810 hid the tray at 480px tall and under because a bottom-anchored orb rides up into the top-anchored tab strip there
(measured at 640x400 and an iPhone's 844x390). Its rule named three orbs - help, compass, the Forge legend - and REG-2860
added the Vault guide. The column is seven: the Tools map (+118 above the dock), the inbox (+170) and MOVE TASKS (+222)
sit higher than any of those and were still drawn over the strip. The v1810 spec only looks at the default tab, where
the tab-scoped orbs are never displayed, so it could not see them.

This law finds the column from the stylesheet the way it is built - every selector whose declarations, merged across
rules, put it at right:12px on a bottom anchored on --dock-h - and requires each one to be hidden by the
@media (max-height:480px) block. A new orb added to the column without that line fails here by name.

Two of the seven are DOORS, not shortcuts: hiding them must not lock the panel they open. The inbox keeps its sticky
panel on Sessions (#inbox-sticky, the one tab where its orb is always hidden); MOVE TASKS gets #vault-chip-tasks in the
vault toolbar, shown only inside the same block, and the Vault guide lights whichever of its two doors is showing.

Source-reading on purpose: there is no CSS engine in node and the browser venue is CI's. The comments are stripped
(bounded) and the stripper is checked against selectors it must keep. The geometry half - no orb over the strip on the
vault and tools tabs, and the toolbar door opening MOVE TASKS at 640x400 - is tests/v1810_tray_short_viewport.spec.ts,
which CI runs. RED_PROOF below.
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
SHORT = "@media (max-height:480px){"
# the column as it stood when this law was written - a PREMISE that the finder reaches them, never the whole list
KNOWN = {".help-btn", ".nav-widget", ".forge-legend-fab", ".tools-legend-fab", ".vault-guide-fab", ".inbox-fab",
         ".vault-tasks-fab"}
CHIP = ".vault-chip.vault-chip-tasks"


def _src():
    return io.open(BIBLE, encoding="utf-8").read()


def _css(src):
    """Every <style> block, comments stripped. Bounded: an unbounded /*.*?*/ over a whole page can run from a /* in a
    string to the next */ anywhere and delete real rules (source-reading-guard 4)."""
    css = "\n".join(re.findall(r"<style\b[^>]*>(.*?)</style>", src, re.S))
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
    """The body of the one @media block that opens with `head`, brace-matched. -> str"""
    i = css.find(head)
    if i < 0:
        return None
    j = i + len(head)
    depth = 1
    k = j
    while k < len(css) and depth:
        depth += {"{": 1, "}": -1}.get(css[k], 0)
        k += 1
    return css[j:k - 1]


def _orbs(css):
    """The tray column: selectors placed at right:12px on a bottom anchored on --dock-h (merged across rules)."""
    right, bottom = set(), set()
    for sel, d in _rules(css):
        if re.match(r"12px\b", d.get("right", "")):
            right.add(sel)
        if "var(--dock-h" in d.get("bottom", ""):
            bottom.add(sel)
    return right & bottom


class EveryTrayOrbYieldsOnAShortScreen(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _src()
        cls.css = _css(cls.src)
        cls.short = _block(cls.css, SHORT)
        if cls.short is None:
            raise AssertionError("PREMISE: bible.html has no %r block - the short-screen rule is gone" % SHORT)

    def test_the_stripper_keeps_the_rules_it_reads(self):
        # a comment stripper that ate real CSS would hand every assertion below a page with fewer orbs in it
        for sel in sorted(KNOWN):
            self.assertIn(sel + "{", self.css, "the comment stripper removed %s's rules" % sel)

    def test_the_finder_sees_the_whole_column(self):
        orbs = _orbs(self.css)
        self.assertTrue(KNOWN <= orbs, "the finder misses orbs that are in the column: %r" % sorted(KNOWN - orbs))
        # the popovers beside the column (right:66px) are not orbs
        self.assertNotIn(".tools-legend-pop", orbs)

    def test_every_orb_in_the_column_is_hidden_at_480px_tall(self):
        hidden = {sel for sel, d in _rules(self.short) if d.get("display", "").replace(" ", "") == "none!important"}
        missing = sorted(_orbs(self.css) - hidden)
        self.assertEqual(missing, [], "these tray orbs still ride into the tab strip on a short screen: %r" % missing)

    def test_move_tasks_keeps_a_door_on_a_short_screen(self):
        chips = re.findall(r'<button\b[^>]*\bid="vault-chip-tasks"[^>]*>', self.src)
        self.assertEqual(len(chips), 1, "the toolbar's MOVE TASKS door is missing or doubled: %r" % chips)
        self.assertIn('onclick="window.vaultTasksTog()"', chips[0], "the toolbar door does not open MOVE TASKS")
        base = [d for sel, d in _rules(self.css) if sel == CHIP and "display" in d]
        self.assertIn("none", [d["display"] for d in base], "the toolbar door is not hidden on an ordinary screen")
        inside = [d.get("display", "") for sel, d in _rules(self.short) if sel == CHIP]
        self.assertTrue(inside and all(v and "none" not in v for v in inside),
                        "the toolbar door is not shown where the 📦 orb is hidden: %r" % inside)

    def test_the_inbox_keeps_its_sessions_panel(self):
        i, j = self.src.find('id="tab-session"'), self.src.find('<div class="tab-content" id="tab-tools"')
        k = self.src.find('id="inbox-sticky"')
        self.assertTrue(0 <= i < k < j, "the inbox's sticky panel is not on Sessions - hiding its orb would lock it")


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class TheGuideLightsTheDoorThatIsShowing(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(r"""
var W = window, VG = W._vaultGuide || { steps: [] };
OUT.step = VG.steps.filter(function(s){ return s.target === 'vault-tasks-fab'; })[0] || null;
var i = VG.steps.indexOf(VG.steps.filter(function(s){ return s.target === 'vault-tasks-fab'; })[0]);
OUT.tall = W.vaultGuideGo(i);
/* a short screen: the orb has no box, the toolbar door has one */
document.getElementById('vault-tasks-fab').getClientRects = function(){ return []; };
document.getElementById('vault-chip-tasks').getClientRects = function(){ return [{ width: 120, height: 26 }]; };
OUT.short = W.vaultGuideGo(i);
OUT.shortHtml = document.getElementById('vault-guide-pop').innerHTML;
W.vaultGuideTog(false);
""", prelude="localStorage.setItem('d2r_ownerClaim', '*');\n", timeout=300)

    def test_the_move_tasks_step_names_both_doors(self):
        self.assertEqual((self.o["step"] or {}).get("alt"), "vault-chip-tasks", "the guide does not know the second door")

    def test_it_lights_the_toolbar_door_when_the_orb_is_hidden(self):
        self.assertEqual(self.o["tall"], "vault-tasks-fab")
        self.assertEqual(self.o["short"], "vault-chip-tasks", "on a short screen the guide still points at the hidden orb")
        self.assertIn("in the toolbar", self.o["shortHtml"] or "")
        self.assertNotIn("not showing on this screen", self.o["shortHtml"] or "")


RED_PROOF = [
    {"why": "REG-2862 - the Tools map orb still rides into the tab strip on a short screen",
     "file": "bible.html",
     "find": "  .help-btn,.nav-widget,.forge-legend-fab,.tools-legend-fab,.vault-guide-fab,.inbox-fab,.vault-tasks-fab{display:none!important}\n",
     "replace": "  .help-btn,.nav-widget,.forge-legend-fab,.vault-guide-fab,.inbox-fab,.vault-tasks-fab{display:none!important}\n",
     "matches": 1},
    {"why": "REG-2862 - the inbox orb still rides into the tab strip on a short screen",
     "file": "bible.html",
     "find": "  .help-btn,.nav-widget,.forge-legend-fab,.tools-legend-fab,.vault-guide-fab,.inbox-fab,.vault-tasks-fab{display:none!important}\n",
     "replace": "  .help-btn,.nav-widget,.forge-legend-fab,.tools-legend-fab,.vault-guide-fab,.vault-tasks-fab{display:none!important}\n",
     "matches": 1},
    {"why": "REG-2862 - the MOVE TASKS orb still rides into the tab strip on a short screen",
     "file": "bible.html",
     "find": "  .help-btn,.nav-widget,.forge-legend-fab,.tools-legend-fab,.vault-guide-fab,.inbox-fab,.vault-tasks-fab{display:none!important}\n",
     "replace": "  .help-btn,.nav-widget,.forge-legend-fab,.tools-legend-fab,.vault-guide-fab,.inbox-fab{display:none!important}\n",
     "matches": 1},
    {"why": "REG-2862 - with the orb hidden, the toolbar door is not shown either: MOVE TASKS is locked on a short screen",
     "file": "bible.html",
     "find": "  .vault-chip.vault-chip-tasks{display:inline-flex}\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2862 - the toolbar door shows on every screen beside the orb",
     "file": "bible.html",
     "find": ".vault-chip.vault-chip-tasks{display:none;cursor:pointer}\n",
     "replace": ".vault-chip.vault-chip-tasks{cursor:pointer}\n",
     "matches": 1},
    {"why": "REG-2862 - the toolbar door is gone from the markup",
     "file": "bible.html",
     "find": "id=\"vault-chip-tasks\" onclick=\"window.vaultTasksTog()\"",
     "replace": "id=\"vault-chip-tasks\" onclick=\"window.vaultUndoLast()\"",
     "matches": 1},
    {"why": "REG-2862 - the guide points at the hidden orb on a short screen",
     "file": "bible.html",
     "find": "    if (other && !shows(el) && shows(other)) { el = other; id = alt; }\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
