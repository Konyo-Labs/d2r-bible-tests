# -*- coding: utf-8 -*-
"""v3849 B1 (the 348-item Vault batch test, 31 Oct 12:00) - THE PHOTO DOOR ASKS THE ONE DENYLIST.

Photo intake (window.vaultIntake) filed Akara, Charsi, Deckard Cain, Gold, Stash, Tyrael, Close and Horadric Cube as owned
items: its per-name loop called _ownedAdd with no catalogue check, while the typed door already refused them. Elad saw
Deckard Cain, Stash and Tyrael in the ALT shadow's Unsorted dock. Now the loop asks window._vaultNotAnItem first and a
refused word is never owned. Real items that contain those words (Tyrael's Might, Gheed's Fortune) are not refused.
"""
import json, os, subprocess, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
from cb_node_harness import NODE  # noqa: E402

SRC = open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8").read()
WORDS = ["Akara", "Charsi", "Deckard Cain", "Gold", "Stash", "Tyrael", "Close", "Horadric Cube"]
REAL = ["Tyrael's Might", "Gheed's Fortune", "Harlequin Crest", "Raven Whorl"]


def _intake_loop():
    i = SRC.index("  window.vaultIntake = async function(files, opts){")
    j = SRC.index("        (data.items || []).forEach(function(n){", i)
    k = SRC.index("            window._ownedAdd(n, _intakeRec(fname));", j)
    return SRC[j:k]


class PhotoDoorRefusesNpcWords(unittest.TestCase):
    def test_the_loop_asks_the_denylist_before_it_owns(self):
        loop = _intake_loop()
        g = loop.find("window._vaultNotAnItem(n)")
        self.assertGreater(g, 0, "the photo door files a name without asking _vaultNotAnItem")
        self.assertLess(g, loop.find("_ownedAdd("), "the photo door owns a name before it asks the denylist")
        self.assertIn("if (_niB1) {", loop)
        self.assertIn("return; } } catch (eB1) {}", loop)

    def test_every_batch_word_is_refused_and_real_items_are_not(self):
        if NODE is None:
            raise AssertionError("node is not on this machine - this law does not skip")
        a = SRC.index("  var _NOT_ITEMS = {")
        b = SRC.index("  window.vaultMaterialNames = _vaultMaterialNames;", a)
        c = SRC.index("  window._vaultNotAnItem = function(name){", b)
        d = SRC.index("\n  };\n", c) + 5
        js = ("var window = {}; " + SRC[a:b] + SRC[c:d] +
              "\nvar _vaultMaterialNames = function(){ return {}; };"
              "console.log(JSON.stringify(%s.map(function(n){ return !!window._vaultNotAnItem(n); })));"
              % json.dumps(WORDS + REAL))
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(dict(zip(WORDS + REAL, got)), dict([(w, True) for w in WORDS] + [(w, False) for w in REAL]))


RED_PROOF = [
    {"why": "v3849 B1 - the photo door owns an NPC word again (no denylist ask)",
     "file": "bible.html",
     "find": "                if (_niB1) { try { console.warn('[vault-intake] ' + fname + ': ' + _niB1); } catch(eW){} return; } } catch (eB1) {}",
     "replace": "                if (false) { } } catch (eB1) {}",
     "matches": 1},
    {"why": "v3849 B1 - Close and the Horadric Cube become items again",
     "file": "bible.html",
     "find": "    'close': 'a panel button', 'horadric cube': 'the quest cube (a container, never a stash item)' };",
     "replace": "    };",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
