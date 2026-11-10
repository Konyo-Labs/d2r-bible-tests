# -*- coding: utf-8 -*-
"""REG-3641 - EVERY VAULT LOCKER PLATE DRAWS A SHARED CLASS AVATAR, STABLE ACROSS RELOADS.

Elad, 11-10: the Characters section's outer cards show a class figure (Sorceress, Barbarian, …)
and "this can be used in mules for the VAULT. so a small visual upgrade to the exterior mules."
Then: do not pick the mule's real class — give each locker a random class from the same art set,
stable per locker (seeded by the locker name) so it does not reshuffle on every render, and spread
so neighboring lockers do not all repeat.

The plate draws through the character-card helper (_chxCrest / _CHX_CLASS_SPRITE). A second art
map is a drift waiting to happen. The pick is _chxClassesForLockers on the locker names: a name
seed, the previous locker's class skipped, a class already used more often deferred. The inside
of the locker is unchanged. The exterior shelf is four lockers across at a 1512 desktop width, with a 64-72px crest scaled to the tile, and two or three across at 901x900. RED_PROOF below.
"""
import io
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
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
ROOT = os.path.dirname(HERE)
NODE = shutil.which("node")
REC = os.path.join(HERE, "data", "class_art.json")
CLASSES = ("Amazon", "Assassin", "Barbarian", "Druid", "Necromancer", "Paladin", "Sorceress", "Warlock")


def _src():
    with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


def _helpers(src):
    i = src.index("  var _CHX_CLASS_SPRITE = ")
    j = src.index("\n  window._CHX_CLASS_SPRITE = _CHX_CLASS_SPRITE;", i)
    return ("var own = Object.prototype.hasOwnProperty;\n"
            "var window = {};\n"
            "function esc(s){ return String(s == null ? '' : s).replace(/[&<>\"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]; }); }\n"
            + src[i:j] + "\n")


def _roster_names(src):
    m = re.search(r"var DEFAULT_ROSTER=\[(.*?)\];", src, re.S)
    if not m:
        return []
    return re.findall(r"name:'([^']+)'", m.group(1))


class EveryVaultLockerDrawsAStableClassAvatar(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _src()
        with io.open(REC, encoding="utf-8") as fh:
            cls.rec = json.load(fh)

    def test_the_page_map_is_still_the_record(self):
        m = re.search(r"  var _CHX_CLASS_SPRITE = (\{[^\n]*\});", self.src)
        self.assertIsNotNone(m, "PREMISE: the page carries no class-figure map")
        self.assertEqual(json.loads(m.group(1)), self.rec["classes"],
                         "the page's map drifted from tv/data/class_art.json")

    def test_the_vault_plate_draws_through_the_shared_crest(self):
        self.assertIn("window._chxCrest = _chxCrest;", self.src,
                      "the character-card crest was not handed to the vault")
        self.assertIn("window._chxClassesForLockers = _chxClassesForLockers;", self.src,
                      "the name-seeded class pick was not handed to the vault")
        self.assertEqual(self.src.count("_vaultLockerCrest(_lockerCrests[_mi])"), 1,
                         "the locker plate does not draw the shared crest, or draws it twice")
        self.assertIn("window._chxCrest(c, false)", self.src,
                      "the vault crest wrapper does not call the shared helper")
        vault_i = self.src.index('<script id="v203-vault-js">')
        vault_j = self.src.find("</script>", vault_i)
        vault = self.src[vault_i:vault_j]
        self.assertNotIn("d2rw_cls_", vault,
                         "the vault script grew its own class-figure paths")
        self.assertNotIn("var _CHX_CLASS_SPRITE", vault,
                         "the vault script grew a second class-figure map")
        self.assertNotIn("_chxClassForSeed(m.cls", vault)
        self.assertNotIn("_chxCrest(m.cls", vault)

    def test_the_shelf_is_four_across_at_desktop_and_the_crest_is_bigger(self):
        """Four lockers in a row at the 1512 desktop shelf, a 64px crest floor, no blown tile."""
        # Measured 2026-11-10 on the box guest: at a 1512x982 viewport the shelf is 1382px
        # wide; at 901x900 it is 773px. gap is 12px. SHARED STASH still spans the first row.
        DESKTOP_SHELF = 1382
        NARROW_SHELF = 773
        GAP = 12
        m = re.search(
            r"\.vault-shelf\{display:grid;grid-template-columns:repeat\(auto-fill,minmax\(min\(100%,(\d+)px\),1fr\)\);gap:(\d+)px\}",
            self.src)
        self.assertIsNotNone(m, "PREMISE: the vault shelf is no longer an auto-fill grid with min(100%, Npx) (needed so a narrow pane cannot overflow)")
        min_px, gap = int(m.group(1)), int(m.group(2))
        self.assertEqual(gap, GAP, "the shelf gap changed, so the four-across arithmetic is unmeasured")
        four = 4 * min_px + 3 * gap
        five = 5 * min_px + 4 * gap
        two = 2 * min_px + 1 * gap
        self.assertLessEqual(four, DESKTOP_SHELF,
                             "four %spx lockers + gaps (%s) do not fit the 1512 shelf (%s)" % (min_px, four, DESKTOP_SHELF))
        self.assertGreater(five, DESKTOP_SHELF,
                           "five %spx lockers + gaps (%s) still fit the 1512 shelf (%s) — not four across" % (min_px, five, DESKTOP_SHELF))
        self.assertLessEqual(two, NARROW_SHELF,
                             "two %spx lockers + gaps (%s) do not fit the 901x900 shelf (%s)" % (min_px, two, NARROW_SHELF))
        # 2 or 3 per row at 901x900 is the fallback; 4 must not sneak back in.
        self.assertGreater(four, NARROW_SHELF,
                           "four lockers still fit the 901x900 shelf — the narrow fallback is gone")
        # 3-across is welcome at 901x900 if 3 * min + 2 * gap still fits; otherwise two-across is the fallback.

        self.assertIn(".vault-mule{container-type:inline-size;--vm-crest:clamp(64px,20cqi,72px);", self.src,
                      "the locker crest is no longer 20cqi of the tile, clamped 64-72px (20% was cyclic and blew the plate)")
        self.assertIn(".vault-mule .chx-crest.chx-crest-sprite{width:var(--vm-crest);height:var(--vm-crest);min-width:64px;min-height:64px;max-width:72px;max-height:72px;", self.src,
                      "the vault crest does not use the shared --vm-crest size, or lost its 64px floor")
        self.assertIn(".vault-mule .vm-crest{flex:0 0 auto;display:flex;align-items:center;min-width:0;width:var(--vm-crest);height:var(--vm-crest)}", self.src,
                      "the crest wrapper can still grow to the figure's intrinsic width and push the locker name off the plate")
        self.assertRegex(self.src, r"(?m)^\.vm-name\{[^}]*min-width:0;[^}]*text-overflow:ellipsis;[^}]*white-space:nowrap",
                         "the locker name can force the larger crest out of the tile")
        self.assertIn(".vm-plate:has(.nig-chip) .vm-name{min-width:max-content;", self.src,
                      "CHARMS would shrink to CH… beside its not-in-game chip instead of wrapping the chip")

    @unittest.skipUnless(NODE, "node is required to run the page's helper - UNMEASURED without it")
    def test_every_locker_gets_a_shared_class_and_it_is_stable(self):
        """* THE POINT"""
        names = _roster_names(self.src)
        self.assertGreaterEqual(len(names), 11, "DEFAULT_ROSTER could not be read")
        js = (_helpers(self.src)
              + "var names = " + json.dumps(names) + ";\n"
              + "var a = _chxClassesForLockers(names);\n"
              + "var b = _chxClassesForLockers(names);\n"
              + "var crests = a.map(function(c){ return _chxCrest(c, false); });\n"
              + "process.stdout.write(JSON.stringify({a:a, b:b, crests:crests, classes:_chxClassNames()}));\n")
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout)
        self.assertEqual(sorted(got["classes"]), sorted(CLASSES))
        self.assertEqual(got["a"], got["b"], "a second paint shuffled the locker figures")
        self.assertEqual(len(got["a"]), len(names))
        for i, (nm, cls, html) in enumerate(zip(names, got["a"], got["crests"])):
            self.assertIn(cls, CLASSES, "%s was handed a class the map does not name: %r" % (nm, cls))
            src = self.rec["classes"][cls]
            self.assertIn('src="' + src + '"', html,
                          "%s's crest is not the shared %s figure" % (nm, cls))
            self.assertIn("chx-crest-sprite", html, "%s's crest is a letter, not the figure" % nm)
            if i:
                self.assertNotEqual(cls, got["a"][i - 1],
                                    "neighboring lockers %s and %s both wear %s" % (names[i - 1], nm, cls))


RED_PROOF = [
    {"why": "REG-3641 - a vault locker plate draws the emoji again, not the shared class crest",
     "file": "bible.html",
     "find": "        + (_vaultLockerCrest(_lockerCrests[_mi]) || '<span class=\"vm-icon\">'+esc(m.icon||'📦')+'</span>')+'<span class=\"vm-name\">'+esc(m.name)+'</span>'+  /* REG-3641 */ ",
     "replace": "        + '<span class=\"vm-icon\">'+esc(m.icon||'📦')+'</span><span class=\"vm-name\">'+esc(m.name)+'</span>'+ ",
     "matches": 1},
    {"why": "REG-3641 - the locker class is no longer stable: a reload can pick a different figure",
     "file": "bible.html",
     "find": "      cls = _chxClassForSeed(seeds[i], prev, used);\n",
     "replace": "      cls = _chxClassForSeed(String(Date.now()) + ':' + seeds[i], prev, used);\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
