# -*- coding: utf-8 -*-
"""v3855 (Elad) - EVERY VAULT RESET LIVES IN ONE COLLAPSED DANGER GROUP, SAYS WHAT IT DOES, AND STILL ASKS.

Delete unsorted, Reset assignments, Reset vault and Wipe items are pressed only from the rows of #vault-danger-menu
(hidden until its toggle opens it). Each row has a one-line description, red styling, and its handler asks first with
Cancel focused. Static: read from bible.html. This law never presses one of them.
"""
import os, re, unittest
import sys as _sys; _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from console_safe import enable; enable()
HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
ACTIONS = ["vaultClearUnsorted", "vaultReset", "vaultClearHistory", "vaultWipeItems"]


def _fn_body(src, head):
    """The JS function that opens with `head`, to its own matching close brace - both ends anchored, so the window
    grows with the function and never stops short of it (test_a_source_window_must_reach_its_subject). The walk
    skips braces inside quotes, template literals and comments."""
    i = src.index(head)
    k, depth, n = src.index("{", i), 0, len(src)
    while k < n:
        c = src[k]
        if c in "'\"`":
            k += 1
            while k < n and src[k] != c:
                k += 2 if src[k] == "\\" else 1
        elif src.startswith("//", k):
            k = src.find("\n", k)
            k = n if k < 0 else k
        elif src.startswith("/*", k):
            k = src.find("*/", k) + 1
            k = n if k <= 0 else k
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
        k += 1
    raise AssertionError("the function %r never closes - its body is UNKNOWN, not clean" % head)

class DangerGroup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(BIBLE, encoding="utf-8") as f:
            cls.src = f.read()
        i = cls.src.index('<div class="vault-danger-menu" id="vault-danger-menu"')
        cls.menu = cls.src[i:cls.src.index('<div class="vdm-foot">', i)]

    def test_menu_is_collapsed(self):
        self.assertRegex(self.menu[:200], r'role="menu"[^>]*hidden>')

    def test_each_action_is_pressed_only_from_its_row(self):
        for a in ACTIONS:
            calls = re.findall(r'onclick="window\.%s\(' % a, self.src)
            self.assertEqual(len(calls), 1, a)
            row = [r for r in self.menu.split('<div class="vdm-row"') if 'onclick="window.%s(' % a in r]
            self.assertEqual(len(row), 1, a)
            self.assertIn('class="vdm-scope"', row[0], a)
            self.assertIn("vault-btn-danger", row[0], a)

    def test_each_handler_still_asks_with_cancel_first(self):
        for a in ACTIONS:
            body = _fn_body(self.src, "window.%s = async function(){" % a)
            first = re.search(r"uiConfirm\([^;]*", body)
            self.assertTrue(first, a)
            self.assertIn("cancelFirst:true", first.group(0), a)


RED_PROOF = [
    {"why": "Reset vault is pressable from a second place", "file": "bible.html",
     "find": '<div class="vault-toolbar">', "replace": '<div class="vault-toolbar"><button onclick="window.vaultClearHistory()">x</button>', "matches": 1},
    {"why": "the danger menu opens expanded", "file": "bible.html",
     "find": 'role="menu" aria-label="clear and reset" hidden>', "replace": 'role="menu" aria-label="clear and reset">', "matches": 1},
    {"why": "Wipe items stops asking with Cancel first", "file": "bible.html",
     "find": "{cancelFirst:true, title:'⚠ Danger — Wipe items'}", "replace": "{title:'⚠ Danger — Wipe items'}", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
