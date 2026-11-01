# -*- coding: utf-8 -*-
"""v3850 SB-1 (GB-L standing-bugs scan, pass-1204 and pass-1709, 2026-10-31) - AN NPC WORD ALREADY OWNED NEVER REACHES THE DOCK.

Seen: the ALT shadow's Unsorted dock drew Deckard Cain, Tyrael and Stash as item chips (no art, "nothing on the board
recognises this name"). v3849 B1 stopped the photo door from owning them, but a name ALREADY in an owned list (the
ALT's snapshot of Oct 29) kept drawing. window._vaultNpcWord asks the vault's one denylist (_NOT_ITEMS, exact names
only) and both the pool (_vaultKeeps) and the dock (_dockNames) ask it. `owned` itself is not edited. Real items with
those words (Tyrael's Might, Gheed's Fortune) are not refused.

RED_PROOF below.
"""
import json, os, subprocess, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
from cb_node_harness import NODE  # noqa: E402

SRC = open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8").read()
WORDS = ["Deckard Cain", "Tyrael", "Stash", "  stash ", "Shared Stash", "Akara"]
REAL = ["Tyrael's Might", "Gheed's Fortune", "Shako", "Bramble Song", "Grim Harness"]

RED_PROOF = [
    {"why": "the pool keeps an owned NPC word again",
     "file": "bible.html",
     "find": "      if (typeof window._vaultNpcWord === 'function' && window._vaultNpcWord(n)) return false;   /* v3850 SB-1 */\n      // Annihilus",
     "replace": "      // Annihilus",
     "matches": 1},
    {"why": "the dock lists an owned NPC word again",
     "file": "bible.html",
     "find": "        if (typeof window._vaultNpcWord === 'function' && window._vaultNpcWord(n)) return false;   /* v3850 SB-1 */\n        var _seamD",
     "replace": "        var _seamD",
     "matches": 1},
    {"why": "the NPC test stops reading the one denylist",
     "file": "bible.html",
     "find": "    return Object.prototype.hasOwnProperty.call(_NOT_ITEMS, f);\n  };\n",
     "replace": "    return false;\n  };\n",
     "matches": 1},
]


class TheGuard(unittest.TestCase):
    def test_pool_and_dock_ask_it(self):
        i = SRC.index("  function _vaultKeeps(n){")
        keeps = SRC[i:SRC.index("\n  }\n", i)]
        self.assertIn("window._vaultNpcWord(n)) return false;", keeps)
        j = SRC.index("  function _dockNames(){")
        dock = SRC[j:SRC.index("    } catch (e) { return null; }", j)]
        self.assertIn("window._vaultNpcWord(n)) return false;", dock)

    def test_exact_npc_words_only(self):
        if NODE is None:
            raise AssertionError("node is not on this machine - this law does not skip")
        a = SRC.index("  var _NOT_ITEMS = {")
        b = SRC.index("};", a) + 2
        c = SRC.index("  window._vaultNpcWord = function(name){")
        d = SRC.index("\n  };\n", c) + 5
        js = ("var window = {}; " + SRC[a:b] + SRC[c:d] +
              "\nconsole.log(JSON.stringify(%s.map(function(n){ return window._vaultNpcWord(n); })));"
              % json.dumps(WORDS + REAL))
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(dict(zip(WORDS + REAL, got)), dict([(w, True) for w in WORDS] + [(w, False) for w in REAL]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
