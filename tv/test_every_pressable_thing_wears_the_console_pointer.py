# -*- coding: utf-8 -*-
"""REG-3205 (his words, 2026-11-05: "the mouse cursor needs fixing within the console like for buttons that are clickable
should be emphasized. right now everything is showing me a mouse cancel sign.. and it should be a custom mouse cursor
pointer for the console") - EVERY PRESSABLE THING WEARS THE CONSOLE POINTER; ONLY WHAT IS OFF SAYS NO.

COUNTED in control_ui.html on v3864, every cursor rule: 96 `cursor: pointer` and 14 `cursor: default` rules, all beaten
by the `*{cursor:<gauntlet> ... !important}` pair (v1916/v2765/v3034), so no control ever looked different from the
page around it; the only cursors that could differ from the gauntlet were the `not-allowed !important` verdicts (a thin
TZ zone, a disabled button). The last declaration of equal weight wins, so the CONTRACT is a cascade question and this
law reads the cascade, not one rule:

  1. the default stays his gauntlet (the inline PNG `*` rule) - his earlier rulings, not reopened here;
  2. every element under <body> INHERITS its cursor (`:where(body *) { cursor: inherit !important; }`, weightless,
     after the `*` pair), so a control's cursor reaches the label and icon inside it - and no rule puts a cursor on a
     universal right-hand side (`X *`), which on an 84k-element page walks every ancestor of every element;
     one pointer rule, `html :where(LIST)`, value an inline SVG (data:image/svg+xml) in the console's palette (fill
     --gold #f0c060, a dark keyline) with a hotspot and the `pointer` keyword as its fallback, `!important`;
  3. LIST holds the generic clickables (a[href], button, [role="button"], [onclick], summary, label[for], select) and
     EVERY selector this file declares `cursor: pointer` on - a new pressable class that is not added stays the
     gauntlet, and this goes red;
  4. nothing outweighs it with a system `cursor: pointer !important`;
  5. `not-allowed` is said only by what is off: the disabled rule comes AFTER the pointer rule at the same weight and
     names only [disabled] / [aria-disabled="true"]; every other `not-allowed` in the file is on `:disabled`,
     `[disabled]`, or a thin TZ zone - whose markup carries aria-disabled="true".
Pure python over the shipped CSS (comments stripped first). RED_PROOF below.
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

UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
GENERIC = ("a[href]", "button", '[role="button"]', "[onclick]", "summary", "label[for]", "select")
POINTER_OPEN = "  html :where(\n"
POINTER_VALUE_END = ") 12 2, pointer !important; }"
DISABLED = '  html :where([disabled], [aria-disabled="true"]) { cursor: not-allowed !important; }'
INHERIT = "  :where(body *) { cursor: inherit !important; }"
GAUNTLET = '*{cursor:url("data:image/png;base64,'
THIN_ATTRS = "' role=\"button\" tabindex=\"-1\" aria-disabled=\"true\" data-thin=\"1\" title=\"'"


def _css():
    """every <style> body, block comments out - a rule quoted in a comment is never a rule"""
    out = []
    for body in re.findall(r"<style[^>]*>(.*?)</style>", UI, re.S):
        out.append(re.sub(r"/\*.*?\*/", "", body, flags=re.S))
    return "\n".join(out)


def _split(sel):
    depth, cur, out = 0, "", []
    for ch in sel:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [re.sub(r"\s+", " ", x).strip() for x in out if x.strip()]


def _rules(css):
    """-> [(selector, body)] for flat rules (an @supports/@media wrapper's inner rules come through as their own)"""
    return [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css)]


def _contract():
    css = _css()
    if css.count(POINTER_VALUE_END) != 1:
        raise AssertionError("the pointer contract's value occurs %d times" % css.count(POINTER_VALUE_END))
    end = css.index(POINTER_VALUE_END)
    start = css.rfind(POINTER_OPEN, 0, end)
    if start < 0:
        raise AssertionError("the pointer contract does not open with `html :where(`")
    rule = css[start:end + len(POINTER_VALUE_END)]
    lists = re.findall(r"html :where\((.*?)\n  \)", rule, re.S)
    return css, rule, start, lists


class EveryPressableThingWearsTheConsolePointer(unittest.TestCase):

    def test_the_default_is_still_his_gauntlet(self):
        css = _css()
        self.assertEqual(css.count(GAUNTLET), 1, "the console's default is no longer his inline gauntlet")
        self.assertRegex(css, r'\*\{cursor:url\("data:image/png;base64,[A-Za-z0-9+/=]+"\) 2 1, auto !important\}')

    def test_what_is_inside_a_control_inherits_its_cursor(self):
        css, rule, start, lists = _contract()
        self.assertEqual(css.count(INHERIT), 1, "elements no longer inherit their control's cursor")
        self.assertGreater(css.index(INHERIT), css.index(GAUNTLET), "the inherit rule must come after the gauntlet pair")
        self.assertLess(css.index(INHERIT), start, "the inherit rule must come before the pointer rule")
        heavy = []
        for sel, body in _rules(css):
            if re.search(r"(^|;|\s)cursor\s*:", body):
                heavy += [x for x in _split(sel) if re.search(r"\)\s*\*$|\s\*$", x)
                          and x not in (".tzz.tzz-thin *", ":where(body *)")]
        self.assertEqual(heavy, [], "a cursor rule on a universal right-hand side walks every ancestor of every "
                                    "element on each style pass: %r" % heavy)

    def test_one_pointer_rule_an_svg_in_the_palette(self):
        css, rule, start, lists = _contract()
        self.assertEqual(len(lists), 1, "the pointer rule must carry one list (descendants inherit)")
        self.assertIn("\n  ) { cursor: url(\"data:image/svg+xml,%3Csvg ", rule, "the pointer is not an inline SVG")
        self.assertIn("fill='%23f0c060'", rule, "the pointer is not the console's gold")
        self.assertIn("stroke='%231a1206'", rule, "the pointer lost its dark keyline")
        self.assertIn("--gold: #f0c060;", UI, "the console's --gold moved; the pointer's fill must follow it")
        self.assertTrue(rule.endswith(POINTER_VALUE_END), "the pointer has no hotspot or no `pointer` fallback")
        for g in GENERIC:
            self.assertIn(g, _split(lists[0]), "%s is clickable and not in the pointer list" % g)

    def test_every_authored_pointer_selector_is_in_the_contract(self):
        css, rule, start, lists = _contract()
        listed = set(_split(lists[0]))
        missing = []
        for sel, body in _rules(css.replace(rule, "")):
            if re.search(r"cursor\s*:\s*pointer\b", body):
                missing += [s for s in _split(sel) if s not in listed]
        self.assertEqual(missing, [], "these selectors declare cursor: pointer and still wear the gauntlet: %r" % missing)

    def test_nothing_outweighs_it_with_the_system_pointer(self):
        css = _css()
        self.assertIsNone(re.search(r"cursor\s*:\s*pointer\s*!important", css),
                          "a system `cursor: pointer !important` outweighs the console pointer")

    def test_only_what_is_off_says_no(self):
        css, rule, start, lists = _contract()
        self.assertEqual(css.count(DISABLED), 1, "the disabled rule is not the one that names only disabled things")
        self.assertGreater(css.index(DISABLED), start + len(rule) - 1,
                           "the disabled rule must come after the pointer rule, or a disabled button shows the pointer")
        bad = []
        for sel, body in _rules(css):
            if not re.search(r"cursor\s*:\s*not-allowed", body):
                continue
            for s in _split(sel):
                if not re.search(r":disabled|\[disabled\]|\[aria-disabled=\"true\"\]|\.tzz\.tzz-thin", s):
                    bad.append(s)
        self.assertEqual(bad, [], "not-allowed on a control that is not off: %r" % bad)
        self.assertEqual(UI.count(THIN_ATTRS), 1, "a thin TZ zone shows not-allowed but no longer says aria-disabled")


class TheProofsNameOnePlace(unittest.TestCase):

    def test_each_find_matches_once(self):
        for proof in RED_PROOF:
            self.assertEqual(UI.count(proof["find"]), proof["matches"], proof["why"])


RED_PROOF = [
    {"why": "REG-3205 - a pressable class is added and still wears the gauntlet",
     "file": "tv/control_ui.html",
     "find": "  .tzz-live { cursor: pointer; transition:",
     "replace": "  .tzz-live, .tzz-new-door { cursor: pointer; transition:",
     "matches": 1},
    {"why": "REG-3205 - the pointer rule falls back to the cancel sign",
     "file": "tv/control_ui.html",
     "find": "\") 12 2, pointer !important; }",
     "replace": "\") 12 2, not-allowed !important; }",
     "matches": 1},
    {"why": "REG-3205 - every button says no, not only the disabled ones",
     "file": "tv/control_ui.html",
     "find": "  html :where([disabled], [aria-disabled=\"true\"]) { cursor: not-allowed !important; }",
     "replace": "  html :where([disabled], [aria-disabled=\"true\"], button) { cursor: not-allowed !important; }",
     "matches": 1},
    {"why": "REG-3205 - the label inside a button shows the gauntlet, not the button's pointer",
     "file": "tv/control_ui.html",
     "find": "  :where(body *) { cursor: inherit !important; }\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3205 - the header tabs get the system pointer back over the console's",
     "file": "tv/control_ui.html",
     "find": "body.shell-open #head-tabs .ht {\n  pointer-events: auto !important;\n",
     "replace": "body.shell-open #head-tabs .ht {\n  pointer-events: auto !important;\n  cursor: pointer !important;\n",
     "matches": 1},
    {"why": "REG-3205 - a thin zone says no without being disabled",
     "file": "tv/control_ui.html",
     "find": "' role=\"button\" tabindex=\"-1\" aria-disabled=\"true\" data-thin=\"1\" title=\"'",
     "replace": "' role=\"button\" tabindex=\"-1\" data-thin=\"1\" title=\"'",
     "matches": 1},
    {"why": "REG-3205 - the console's default stops being his gauntlet",
     "file": "tv/control_ui.html",
     "find": "*{cursor:url(\"data:image/png;base64,",
     "replace": "*{cursor:default;--was:url(\"data:image/png;base64,",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
