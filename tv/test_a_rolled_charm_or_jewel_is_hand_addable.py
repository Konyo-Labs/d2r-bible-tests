# -*- coding: utf-8 -*-
"""v3895 (#38, REG-3594) - A ROLLED CHARM OR JEWEL IS HAND-ADDABLE.

"Shimmering Small Charm of Vita" and "Ruby Jewel of Fervor" have no catalogue
name, so the hand door refused them as "not an item the vault draws". They are
real stash items. Bare "Jewel" and "Grand Charm" stay ghost bases and are still
refused. The door now asks _vaultHandRolled before that refusal.
RED_PROOF below.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()

BIBLE = os.path.join(HERE, "..", "bible.html")
NODE = os.environ.get("NODE") or shutil.which("node")


def _fn(src, name):
    m = re.search(r"\bfunction %s\s*\(" % re.escape(name), src)
    if not m:
        raise AssertionError("could not find function %s" % name)
    i = src.index("{", m.start())
    depth, j = 0, i
    while j < len(src):
        c = src[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
        j += 1
    raise AssertionError("unbalanced %s" % name)


class ARolledCharmOrJewelIsHandAddable(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        with open(BIBLE, encoding="utf-8") as fh:
            cls.src = fh.read()
        body = _fn(cls.src, "_vaultHandRolled")
        names = [
            "Shimmering Small Charm of Vita",
            "Ruby Jewel of Fervor",
            "Small Charm of Vita",
            "Shimmering Small Charm",
            "Grand Charm",
            "Jewel",
            "Small Charm",
            "Large Charm",
            "Harlequin Crest",
            "Spirit",
            "",
        ]
        prog = body + """
var window = {};
try { window._vaultHandRolled = _vaultHandRolled; } catch (e) {}
var names = %s;
var out = {};
names.forEach(function(n){ out[n] = _vaultHandRolled(n); });
process.stdout.write(JSON.stringify(out));
""" % json.dumps(names)
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=15)
        if p.returncode != 0:
            raise AssertionError((p.stderr or p.stdout)[-1500:])
        cls.f = json.loads(p.stdout)

    def test_a_rolled_name_passes_and_a_bare_base_does_not(self):
        for n in ("Shimmering Small Charm of Vita", "Ruby Jewel of Fervor",
                  "Small Charm of Vita", "Shimmering Small Charm"):
            self.assertEqual(self.f[n], n, n)
        for n in ("Grand Charm", "Jewel", "Small Charm", "Large Charm",
                  "Harlequin Crest", "Spirit", ""):
            self.assertIsNone(self.f[n], n)

    def test_the_hand_door_asks_the_rolled_rule(self):
        self.assertIn(
            "if (!_vaultKeeps(r.name) && !_vaultHandBase(r.name) && !_vaultHandRolled(r.name)) "
            "/* L1 a catalogue base passes the hand door */",
            self.src)


RED_PROOF = [
    {"why": "v3895 (#38, REG-3594) - the hand door stops asking whether a name is a rolled charm or jewel",
     "file": "bible.html",
     "find": "if (!_vaultKeeps(r.name) && !_vaultHandBase(r.name) && !_vaultHandRolled(r.name)) "
             "/* L1 a catalogue base passes the hand door */",
     "replace": "if (!_vaultKeeps(r.name) && !_vaultHandBase(r.name)) "
                "/* L1 a catalogue base passes the hand door */",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
