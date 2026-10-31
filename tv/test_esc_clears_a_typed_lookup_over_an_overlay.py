# -*- coding: utf-8 -*-
"""v3849 (v3848 second eye #3) - ESC CLEARS A TYPED LOOKUP FIRST, EVEN WITH AN OVERLAY OPEN.

The overlay contract listens on window in the capture phase and closed the top card before the veil's (or FIND's)
own Esc ran, so a typed lookup never cleared while a mule card or dialog was up. A typed lookup now owns its first
Esc; an empty one, or any other field, still closes the top overlay. Driven in node on the contract's own source.
"""
import json
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(HERE, "..", "bible.html")
NODE = shutil.which("node")


def _contract():
    with open(BIBLE, encoding="utf-8") as fh:
        src = fh.read()
    f = re.search(r"  function escClearsField\(e\) \{.*?\n  \}\n", src, re.S)
    k = re.search(r"  window\.addEventListener\('keydown', function \(e\) \{\n    if \(e\.key !== 'Escape' \|\| e\.__ovxPass.*?\n  \}, true\);", src, re.S)
    return (f.group(0) if f else ""), (k.group(0) if k else "")


def _drive(target):
    fn, kd = _contract()
    js = """
var closed = 0, handler = null;
var window = { _tvdTypedLookup: '.lookup', addEventListener: function (t, h) { handler = h; } };
var document = { fullscreenElement: null, body: { classList: { contains: function () { return false; } } } };
function typingInPlainField() { return false; }
function topmost() { return { x: { click: function () { closed++; } } }; }
%s
%s
var T = %s;
var tgt = { id: T.id, value: T.value, matches: function (sel) { return sel === '.lookup' && T.lookup; } };
var ev = { key: 'Escape', target: tgt, preventDefault: function () {}, stopImmediatePropagation: function () {} };
handler(ev);
console.log(JSON.stringify({ closed: closed }));
""" % (fn, kd, json.dumps(target))
    out = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", timeout=30)
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout.strip().splitlines()[-1])["closed"]


@unittest.skipIf(NODE is None, "node is not installed")
class EscClearsATypedLookupOverAnOverlay(unittest.TestCase):
    def test_the_contract_source_is_found(self):
        fn, kd = _contract()
        self.assertTrue(fn and kd, "the overlay contract's Esc handler or escClearsField moved")

    def test_a_typed_veil_lookup_keeps_its_esc(self):
        self.assertEqual(_drive({"id": "", "value": "shako", "lookup": True}), 0)

    def test_a_typed_find_keeps_its_esc(self):
        self.assertEqual(_drive({"id": "vault-find-input", "value": "shako", "lookup": False}), 0)

    def test_an_empty_lookup_closes_the_overlay(self):
        self.assertEqual(_drive({"id": "", "value": "", "lookup": True}), 1)

    def test_another_field_closes_the_overlay(self):
        self.assertEqual(_drive({"id": "note", "value": "x", "lookup": False}), 1)


RED_PROOF = [
    {"why": "the contract closes the card before the typed lookup clears", "file": "bible.html",
     "find": "typingInPlainField(e) || escClearsField(e)) return;", "replace": "typingInPlainField(e)) return;", "matches": 1},
    {"why": "FIND loses its first Esc", "file": "bible.html",
     "find": "|| t.id === 'vault-find-input'));", "replace": "));", "matches": 1},
    {"why": "an empty lookup swallows the Esc that should close the card", "file": "bible.html",
     "find": "t.matches && t.value && ((L", "replace": "t.matches && ((L", "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
