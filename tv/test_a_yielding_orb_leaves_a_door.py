# -*- coding: utf-8 -*-
"""REG-3092 (his rule via the team lead; CI chain slice 1: v1800's Tools map and inbox cases red at 640x400) - AN ORB
YIELDS ON A SHORT SCREEN ONLY IF ITS FEATURE HAS ANOTHER DOOR ON THAT SCREEN.

REG-2862 hides all seven tray orbs at 480px tall and under, because a bottom-anchored orb rides into the top-anchored tab
strip there, and it named a second door for two of them (the inbox's sticky panel, MOVE TASKS' toolbar chip). The other
features had none: on a short screen the Tools map, the Vault guide, the Forge legend and the help could not be opened
at all. v1800 caught the Tools map; the rest had no case.

They do not come back as floating orbs - at these heights even the lowest slot rode into the strip, so no fixed spot is
clear (v1810, REG-2862). Each gets an IN-FLOW door where its feature lives, shown only where its orb yields (MOVE TASKS'
pattern), and this law states the rule so a future yield cannot strand a feature:
  * every orb the short-screen block hides has a door named in DOORS - an orb hidden there with no door fails by name,
    and so does a door listed for an orb that is not hidden;
  * each door exists in the page, once;
  * a button door runs what its orb runs (the same opener), and on the whole page in node it OPENS the feature;
  * each door is shown where its orb yields and hidden on an ordinary screen (one control per feature), and no door is
    a fixed overlay - in flow is the whole point;
  * the compass's door is the tab strip it is built from, and the inbox's is its sticky panel on Sessions.
Source-reading where there is no CSS engine in node; the pixels at 640x400 are tests/v1800_tray_popovers_reachable.spec.ts
(the Tools map and Vault guide through these doors, the inbox through its panel), which CI runs. RED_PROOF below.
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
# orb -> its other door on a short screen. kind: button (an in-flow control running the orb's opener), strip, panel.
DOORS = {
    ".help-btn":         {"kind": "button", "door": "tabs-help",         "css": ".tabs .tabs-help",
                          "where": "the end of the tab strip"},
    ".tools-legend-fab": {"kind": "button", "door": "ti-chip-map",       "css": ".tools-index .ti-chip.ti-chip-map",
                          "where": "the Tools index"},
    ".vault-guide-fab":  {"kind": "button", "door": "vault-chip-guide",  "css": ".vault-chip.vault-chip-guide",
                          "where": "the vault toolbar"},
    ".forge-legend-fab": {"kind": "button", "door": "forge-legend-door", "css": "#tab-forge .forge-legend-door",
                          "where": "the Runewords chip row"},
    ".vault-tasks-fab":  {"kind": "button", "door": "vault-chip-tasks",  "css": ".vault-chip.vault-chip-tasks",
                          "where": "the vault toolbar"},
    ".inbox-fab":        {"kind": "panel",  "door": "inbox-sticky",      "where": "its sticky panel on Sessions"},
    ".nav-widget":       {"kind": "strip",  "door": ".tabs .tab",        "where": "the tab strip its chips are built from"},
}
# how each orb's own opener is written in the page, and the state it changes when it runs
ORB_OPENER = {
    ".help-btn":         r'<button class="help-btn[^"]*"[^>]*onclick="([^"]+)"',
    ".tools-legend-fab": r'<button class="tools-legend-fab" id="tools-legend-fab"[^>]*onclick="([^"]+)"',
    ".vault-guide-fab":  r"f\.setAttribute\('onclick', '([^']+)'\)",
    ".forge-legend-fab": r'<button class="forge-legend-fab" id="forge-legend-fab"[^>]*onclick="([^"]+)"',
    ".vault-tasks-fab":  r'<button type="button" id="vault-tasks-fab"[^>]*onclick="([^"]+)"',
}
OPENS = {   # door -> JS that reads whether the feature is open, after the door's own code ran
    "tabs-help":         "document.getElementById('help-modal').classList.contains('show')",
    "ti-chip-map":       "document.getElementById('tools-legend-pop').classList.contains('open')",
    "vault-chip-guide":  "document.getElementById('vault-guide-pop').classList.contains('open')",
    "forge-legend-door": "document.getElementById('forge-legend-pop').classList.contains('open')",
    "vault-chip-tasks":  "!document.getElementById('vault-tasks').hidden",
}


def _src():
    with io.open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _css(src):
    css = "\n".join(re.findall(r"<style\b[^>]*>(.*?)</style>", src, re.S))
    return re.sub(r"/\*.{0,8000}?\*/", " ", css, flags=re.S)


def _rules(css):
    out = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        decl = {}
        for d in m.group(2).split(";"):
            if ":" in d:
                k, v = d.split(":", 1)
                decl[k.strip()] = v.strip()
        for sel in m.group(1).split(","):
            out.append((re.sub(r"\s+", " ", sel.strip()), decl))
    return out


def _block(css, head):
    i = css.find(head)
    if i < 0:
        return None
    j = k = i + len(head)
    depth = 1
    while k < len(css) and depth:
        depth += {"{": 1, "}": -1}.get(css[k], 0)
        k += 1
    return css[j:k - 1]


def _unent(s):
    return s.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")


def _door_onclick(src, door):
    """the door's own onclick, from the markup or the JS string that emits it"""
    m = re.search(r'id=\\?"%s\\?"[^>]*?onclick=\\?"([^"\\]+)' % re.escape(door), src) \
        or re.search(r'onclick=\\?"([^"\\]+)\\?"[^>]*?id=\\?"%s\\?"' % re.escape(door), src)
    return _unent(m.group(1)) if m else None


def _opener(code):
    """what a click runs, reduced to the call that opens: window.fnName, or the modal it shows"""
    m = re.search(r"window\.([A-Za-z_]\w*)\s*\(", code or "")
    if m:
        return "window." + m.group(1)
    m = re.search(r"getElementById\('([^']+)'\)\.classList\.add\('show'\)", code or "")
    return ("show#" + m.group(1)) if m else None


class AYieldingOrbLeavesADoor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _src()
        cls.css = _css(cls.src)
        cls.short = _block(cls.css, SHORT)
        if cls.short is None:
            raise AssertionError("PREMISE: bible.html has no %r block - the short-screen yield is gone" % SHORT)
        cls.short_rules = _rules(cls.short)
        cls.hidden = {s for s, d in cls.short_rules if d.get("display", "").replace(" ", "") == "none!important"}

    def test_every_yielding_orb_has_a_named_door(self):
        self.assertGreaterEqual(len(self.hidden), 7, "PREMISE: the short-screen block hides %r" % sorted(self.hidden))
        stranded = sorted(o for o in self.hidden if o not in DOORS)
        self.assertEqual(stranded, [], "these orbs yield on a short screen and their feature has no other door there: %r"
                         % stranded)
        unhidden = sorted(o for o in DOORS if o not in self.hidden)
        self.assertEqual(unhidden, [], "a door is listed for an orb the short-screen block does not hide: %r" % unhidden)

    def test_each_door_exists_once(self):
        for orb, d in sorted(DOORS.items()):
            if d["kind"] == "strip":
                self.assertGreaterEqual(len(re.findall(r'<button class="tab[^"]*" data-tab="', self.src)), 8,
                                        "the tab strip is gone - the compass has no door")
                continue
            n = len(re.findall(r'id=\\?"%s\\?"' % re.escape(d["door"]), self.src))
            self.assertEqual(n, 1, "%s's door #%s is in the page %d times, not once" % (orb, d["door"], n))

    def test_a_button_door_runs_what_its_orb_runs(self):
        for orb, d in sorted(DOORS.items()):
            if d["kind"] != "button":
                continue
            m = re.search(ORB_OPENER[orb], self.src)
            self.assertIsNotNone(m, "could not read %s's own onclick - re-point this law" % orb)
            want = _opener(_unent(m.group(1)))
            got = _opener(_door_onclick(self.src, d["door"]))
            self.assertIsNotNone(want, "%s's opener is not a call this law can read: %r" % (orb, m.group(1)))
            self.assertEqual(got, want, "#%s does not open what %s opens: %r vs %r" % (d["door"], orb, got, want))

    def test_each_door_shows_where_its_orb_yields_and_only_there(self):
        for orb, d in sorted(DOORS.items()):
            if d["kind"] == "button":
                base = [dd.get("display") for s, dd in _rules(self.css.replace(self.short, "")) if s == d["css"]
                        and "display" in dd]
                self.assertIn("none", base, "#%s shows on an ordinary screen too - two controls for one feature" % d["door"])
                there = [dd.get("display", "") for s, dd in self.short_rules if s == d["css"] and "display" in dd]
                self.assertTrue(there and all(v and "none" not in v for v in there),
                                "#%s is not shown where %s yields: %r" % (d["door"], orb, there))
            else:
                gone = [s for s in self.hidden if s in (".tabs", ".tabs .tab", ".tab", ".inbox-sticky", "#inbox-sticky",
                                                       ".inbox-sticky.has")]
                self.assertEqual(gone, [], "%s's door is hidden by the same block: %r" % (orb, gone))

    def test_no_door_is_a_fixed_overlay(self):
        for orb, d in sorted(DOORS.items()):
            if d["kind"] != "button":
                continue
            fixed = [s for s, dd in _rules(self.css) if s == d["css"] and "fixed" in dd.get("position", "")]
            self.assertEqual(fixed, [], "#%s floats like the orb it replaces, so it rides into the strip too" % d["door"])

    def test_the_compass_is_built_from_the_strip_and_the_inbox_panel_is_on_sessions(self):
        i = self.src.find("function buildNavWidget() {")
        body = self.src[i:self.src.find("\n}\n", i)]
        self.assertIn('document.querySelectorAll(".tabs .tab")', body, "the compass no longer offers the strip's tabs")
        a, b = self.src.find('id="tab-session"'), self.src.find('<div class="tab-content" id="tab-tools"')
        k = self.src.find('id="inbox-sticky"')
        self.assertTrue(0 <= a < k < b, "the inbox's sticky panel is not on Sessions - its orb's yield would lock it")


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class EachButtonDoorOpensItsFeature(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        src = _src()
        codes = dict((d["door"], _door_onclick(src, d["door"])) for d in DOORS.values() if d["kind"] == "button")
        body = ["var R = {};",
                "try { window.renderForge(); } catch (e) { R.forgeErr = String(e); }",
                "H.flush(60, 3);",
                "R.forgeDoor = !!document.getElementById('forge-legend-door');",
                # the node page does not parse markup attributes: MOVE TASKS' panel ships `hidden` (asserted below), so
                # it starts that way here, or its toggle would read 'open' before anything was pressed
                "var vt = document.getElementById('vault-tasks'); if (vt) vt.hidden = true;"]
        for door, code in sorted(codes.items()):
            body.append("try { R[%r] = { before: !!(%s) }; (new Function(%r))(); H.flush(30, 2); R[%r].after = !!(%s); }"
                        " catch (e) { R[%r] = { err: String(e) }; }" % (door, OPENS[door], code or "throw new Error('no code')",
                                                                       door, OPENS[door], door))
        body.append("OUT.r = R; OUT.errors = H.errors.slice(0, 5);")
        cls.o = VPN.run("\n".join(body), prelude="localStorage.setItem('d2r_ownerClaim', '*');\n", timeout=300)

    def test_the_page_booted(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertRegex(_src(), r'<aside id="vault-tasks"[^>]*\bhidden>', "MOVE TASKS' panel no longer ships hidden")
        self.assertTrue(self.o["r"].get("forgeDoor"), "the Runewords chip row draws no legend door: %r" % self.o["r"])

    def test_each_door_opens_what_was_shut(self):
        r = self.o["r"]
        for door in sorted(OPENS):
            self.assertEqual(r.get(door), {"before": False, "after": True},
                             "#%s did not open its feature: %r" % (door, r.get(door)))


RED_PROOF = [
    {"why": "REG-3092 - the Tools map's orb yields and nothing else opens it on a short screen",
     "file": "bible.html",
     "find": "<button class=\"ti-chip ti-chip-map\" id=\"ti-chip-map\" onclick=\"window.toolsLegendToggle&amp;&amp;window.toolsLegendToggle()\"",
     "replace": "<button class=\"ti-chip ti-chip-map\" id=\"ti-chip-map-gone\" onclick=\"window.toolsLegendToggle&amp;&amp;window.toolsLegendToggle()\"",
     "matches": 1},
    {"why": "REG-3092 - the Vault guide's door opens MOVE TASKS instead of the guide",
     "file": "bible.html",
     "find": "<button type=\"button\" class=\"vault-chip vault-chip-guide\" id=\"vault-chip-guide\" onclick=\"window.vaultGuideTog()\"",
     "replace": "<button type=\"button\" class=\"vault-chip vault-chip-guide\" id=\"vault-chip-guide\" onclick=\"window.vaultTasksTog()\"",
     "matches": 1},
    {"why": "REG-3092 - the help's door is never shown where the ? orb yields",
     "file": "bible.html",
     "find": "  .tabs .tabs-help{display:inline-flex}\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3092 - the Forge legend's door shows on an ordinary screen too, a second control for one feature",
     "file": "bible.html",
     "find": "#tab-forge .forge-legend-door{display:none;flex:0 0 auto;",
     "replace": "#tab-forge .forge-legend-door{display:flex;flex:0 0 auto;",
     "matches": 1},
    {"why": "REG-3092 - the Runewords chip row stops drawing the Forge legend's door",
     "file": "bible.html",
     "find": "      + (_isCrafts ? '' : '<button type=\"button\" class=\"forge-legend-door\"",
     "replace": "      + (true ? '' : '<button type=\"button\" class=\"forge-legend-door\"",
     "matches": 1, "needs": "node"},
    {"why": "REG-3092 - a new orb yields with no door named",
     "file": "bible.html",
     "find": "  .help-btn,.nav-widget,.forge-legend-fab,.tools-legend-fab,.vault-guide-fab,.inbox-fab,.vault-tasks-fab{display:none!important}\n",
     "replace": "  .help-btn,.nav-widget,.forge-legend-fab,.tools-legend-fab,.vault-guide-fab,.inbox-fab,.vault-tasks-fab,.tools-legend-btn{display:none!important}\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
