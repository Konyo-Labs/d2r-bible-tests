# -*- coding: utf-8 -*-
"""#230 (REG-3117, GrokBot 6489429952) - IN A SHADOW NO VAULT CELL OR TILE PROMISES AN ACTION THE SHADOW WILL NOT TAKE.

GrokBot, guest -> Fleet -> Konyo · Mac -> Vault -> UNIQUE ARMOR: a FILLED mule cell's aria-label said "Drag it to any cell
where it fits and it locks there" in a read-only shadow, where the veil stops the drag. The lock held; the words lied.
REG-3103 had fixed only the EMPTY cell (gridCellSay). Now every title and aria-label on a vault cell or tile builds its
action words through one helper beside it, gridActSay(desc, act): desc is what the thing IS and stays; act is what a
click, key or drag would do, and in a shadow it reads "Read only: this is their console, shown in a shadow". Outside a
shadow the words are desc + act, exactly as before.

THE SWEEP: every string in the surfaces below that names an action (drag, drop, click, Enter, Delete, remove, unlock,
unequip, release, assign, choose, replace, send back, throw out, pick up, place, move) is listed here and classified - an
ACT routed through gridActSay (or the one `gridShadowRo() ? '' : (...)` that drops a key list), or a VIEW a shadow lets him
take (opening a mule's window). Markup is read for its title / aria-label words only; class names and handlers are never
read aloud. A new phrase fails until it is named, and an act written inline in markup fails the routing check.

  the mule window: gridCellSay and its helpers, gridHtml (tiles he placed or the packer placed, a tile from the item
  database, an empty cell, a copy's ✕, the unlock), the doll's slots and their ✕, the Mule tabs; the shelf: a locker
  card's cells, their ✕ and lock, a Magic & Rare cell's ✕, _vaultCellXTitle, a locker's plate; the dock's chip and its ✕.

Driven: (1) the helper cut out and run outside, in a snapshot shadow and in a shadow known by its class; (2) the sweep and
its routing, over bible.html; (3) the WHOLE page in node (vault_page_node) twice - his board with a filed vault, then a
snapshot shadow of exactly those stores - every title, aria-label and aria-roledescription of the shelf and two mule
windows read: on his board the action words are there, in the shadow none is and each says read only. RED_PROOF below.
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
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import vault_page_node as VPN  # noqa: E402

NODE = shutil.which("node")
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
with io.open(BIBLE, encoding="utf-8") as _fh:
    PAGE = _fh.read()

RO = "Read only: this is their console, shown in a shadow"
REGIONS = (("  function gridCellSay(label, cx, cy){", "  function gridHtml(placed, gw, gh, cell, opt){"),
           ("  function gridHtml(placed, gw, gh, cell, opt){", "  /* ⟦STASH TABS⟧ */"),
           ("    dock.innerHTML = unsorted.map(function(n){", "    }).join('');"),
           ("        var _lockTag = !_hlk ? '' :", "_mfCells.push("),
           ("  function _vaultCellXTitle(n, cc, hlk){", "  window._vaultCellXTitle = _vaultCellXTitle;"),
           ("        + '<div class=\"vm-plate\" tabindex=\"0\"", "\n"),
           ("    for (var _i = 0; _i < _muleTotalPages; _i++) setTabs +=", "\n"),
           ("    var doll = _mpDollSlotsHtml(function(s){", "    var swap = [[16,1]"))
VERB = re.compile(r"(?i)\b(drag|drop|click|enter|delete|remove|unlock|unequip|release|assign|choose|replace|send back|throw out"
                  r"|picks? it up|place it|move it|moves it|locks there|erases)\b")
A, V = "act", "view"
CLASS = {
    ": click (or Enter) to add an item from the database": A,
    ". Drag it; a green footprint of its size, inside this inventory, is the only drop that moves it": A,
    ". Click (or Enter) for its tooltip, to replace it or remove it; Delete removes it": A,
    "remove this copy (copy ": A,
    "remove copy ": A,
    ". Drag to move it; right-click (or the lock) returns it to auto-pack": A,
    " until you place it again or unlock it": A,
    ". Drag it to any cell where it fits and it locks there": A,
    ". Enter picks it up, arrow keys move it, Enter drops, Escape cancels": A,
    "unlock — back to auto-pack (right-click the item does the same)": A,
    "unlock ": A,
    "drag onto a locker — or click, then click a locker": A,
    "not mine — remove from ✓ owned (AI misread? this erases it)": A,
    ". Hold Shift while you drop it on another locker, or Shift+click ✕, to release it.": A,
    "throw out — remove from Magic &amp; Rare": A,
    "; hold Shift and click ✕ to release it": A,
    "send back to the unsorted dock": A,
    " · with a chip selected: assign it here": A,
    " — drop an item here to move it to this mule": A,
    ". Enter to change it, Delete to unequip": A,
    ". Click (or Enter) to choose one: this locker’s items, or any item in the database": A,
    "unequip ": A,
    " (right-click the slot does the same)": A,
    "unequip the ": A,
    "SHARED STASH — accessible by ALL characters · click to open the fullscreen 5-page view": V,
    "click: open the in-game ID card of this mule": V,
}
#: the routes an ACT may take: the helper's call, or the one key list a shadow drops whole
ROUTES = ("gridActSay(", "gridShadowRo() ? '' : (")


def _literals(code, base):
    """[(absolute position, raw text)] of every single-quoted string in a stretch of the page's script, comments skipped."""
    i, out = 0, []
    while i < len(code):
        if code.startswith("/*", i):
            j = code.find("*/", i + 2)
            i = (j + 2) if j >= 0 else len(code)
            continue
        if code.startswith("//", i) and (i == 0 or code[i - 1] not in ":'\"\\"):
            j = code.find("\n", i)
            i = j if j >= 0 else len(code)
            continue
        if code[i] == "'":
            j, buf = i + 1, []
            while j < len(code) and code[j] != "'":
                if code[j] == "\\":
                    buf.append(code[j:j + 2])
                    j += 2
                    continue
                buf.append(code[j])
                j += 1
            out.append((base + i, "".join(buf)))
            i = j + 1
            continue
        i += 1
    return out


def _words(t):
    """What a string would SAY: itself, or - when it is markup - only the title / aria-label / aria-roledescription values it
    carries (a trailing one left open counts). Class names, handlers and data attributes are never read aloud."""
    if "<" not in t and '="' not in t:
        return t
    vals = re.findall(r'(?:title|aria-label|aria-roledescription)="([^"]*)(?:"|$)', t)
    return " ".join(vals)


def sweep():
    """{phrase: [positions]} - every string in the swept surfaces whose words name an action."""
    found = {}
    for a, b in REGIONS:
        if PAGE.count(a) != 1:
            raise AssertionError("%r occurs %d times - this law cannot find its surface" % (a, PAGE.count(a)))
        s0 = PAGE.index(a)
        s1 = PAGE.index(b, s0 + len(a))
        for pos, t in _literals(PAGE[s0:s1], s0):
            if VERB.search(_words(t)):
                found.setdefault(t, []).append(pos)
    return found


def _routed(pos):
    """Is the string at pos an argument of a route that is still open there (its parenthesis not yet closed)?"""
    best = max(PAGE.rfind(r, max(0, pos - 900), pos) for r in ROUTES)
    if best < 0:
        return False
    route = [r for r in ROUTES if PAGE.startswith(r, best)][0]
    depth, i, q = 1, best + len(route), None
    while i < pos:
        c = PAGE[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = None
        elif c in "'\"":
            q = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return False
        i += 1
    return depth > 0


class EveryActionPhraseIsNamedAndRouted(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.found = sweep()

    def test_premise_the_sweep_sees_the_words(self):
        self.assertIn(". Drag it to any cell where it fits and it locks there", self.found, "premise: GrokBot's words not found")
        self.assertGreater(len(self.found), 20, "premise: the sweep found %d phrases - it is blind" % len(self.found))

    def test_every_action_phrase_is_classified(self):
        self.assertEqual(sorted(set(self.found) - set(CLASS)), [], "an action phrase nobody classified (act / view / code)")

    def test_no_class_names_a_phrase_that_is_gone(self):
        self.assertEqual(sorted(set(CLASS) - set(self.found)), [], "a classified phrase is no longer on these surfaces")

    def test_every_act_goes_through_the_helper(self):
        bad = sorted("%s (at %d)" % (t, p) for t, ps in self.found.items() if CLASS.get(t) == A for p in ps if not _routed(p))
        self.assertEqual(bad, [], "an action phrase a shadow would still say")


HELPER = r"""
var CLASSES = {};
var document = { documentElement: { classList: { contains: function(c){ return !!CLASSES[c]; } } } };
var window = {};
"""

HELPER_SCENARIO = r"""
var out = { own: [gridActSay('Mule 1', ' — drop'), gridActSay('', 'unlock X'), gridCellSay('Inventory', 2, 0)] };
window._tvdShadow = { owner: 'Konyo · Mac' };
out.snap = [gridActSay('Mule 1', ' — drop'), gridActSay('', 'unlock X'), gridShadowRo()];
delete window._tvdShadow; CLASSES['tvd-shadow'] = true;
out.cls = [gridActSay('Mule 1', ' — drop'), gridShadowRo()];
process.stdout.write(JSON.stringify(out));
"""


class TheHelperSaysReadOnlyOnlyInAShadow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        i = PAGE.index("  function gridCellSay(label, cx, cy){")
        fn = PAGE[i:PAGE.index("  function gridHtml(placed, gw, gh, cell, opt){", i)]
        r = subprocess.run([NODE, "-"], input=HELPER + fn + "\n" + HELPER_SCENARIO, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("the helper did not run in node: %s" % r.stderr[-900:])
        cls.o = json.loads(r.stdout)

    def test_outside_a_shadow_the_words_are_unchanged(self):
        self.assertEqual(self.o["own"], ["Mule 1 — drop", "unlock X",
                                         "Inventory · col 3 · row 1 — empty: click (or Enter) to add an item from the database"])

    def test_in_a_shadow_the_action_reads_read_only(self):
        self.assertEqual(self.o["snap"], ["Mule 1. " + RO, RO, True])
        self.assertEqual(self.o["cls"], ["Mule 1. " + RO, True], "a shadow known only by its class still promised the action")


# ---- the whole page, twice: his board, then a snapshot shadow of it ----
REBIND = (("const localStorage = {", "const __vpnLocalStorage = {"),
          ("{ value: localStorage, configurable: true", "{ value: __vpnLocalStorage, configurable: true"))

OWNER = r"""
if (!/tvd-shadow/.test(String(location.search))) localStorage.setItem('d2r_ownerClaim', '*');
"""

SHADOW_PRE = r"""
document.write = function (t) { OUT.shadowRefused = String(t).replace(/<[^>]*>/g, '').slice(0, 300); };
window.stop = function () {};
location.search = '?tvd-shadow=1'; location.href = 'http://127.0.0.1/bible.html?tvd-shadow=1';
window.parent = { _tvdShadowSnap: SNAP, postMessage: function () {} };
"""

SEED = r"""
var W = window;
try { W._vaultAutoIntakeSet(false); } catch (e) {}
['Harlequin Crest', 'Arachnid Mesh', 'Skin of the Vipermagi', 'Gull', 'Gull'].forEach(function (n) { try { W.vaultHandAdd(n); } catch (e) {} });
[['Harlequin Crest (Shako)', 'uni-armor'], ['Arachnid Mesh', 'uni-armor'], ['Skin of the Vipermagi', 'uni-armor'], ['Gull (dagger)', 'uni-weap']].forEach(function (a) {
  try { W.vaultAssign(a[0], a[1]); } catch (e) {} });
try { W._mpPlace('uni-armor', 'Skin of the Vipermagi', { tab: 'personal', page: 0, x: 0, y: 0 }); } catch (e) {}
try { W.renderVault(); } catch (e) {}
H.flush(60, 3);
OUT.snap = {}; H.RAW.forEach(function (v, k) { if (/^d2r_[A-Za-z0-9_]{1,60}$/.test(k)) OUT.snap[k] = v; });
"""

READ = r"""
var W = window;
(function () { var qs = document.querySelector, btns = {};
  document.querySelector = function (sel) { var m = /^\.tab\[data-tab="([\w-]+)"\]$/.exec(String(sel).trim());
    if (m) return btns[m[1]] || (btns[m[1]] = document.createElement('button')); return qs.call(document, sel); }; })();
function words(html) {
  var out = [], re = /\s(title|aria-label|aria-roledescription)="([^"]*)"/g, m;
  while ((m = re.exec(String(html || '')))) out.push(m[2]);
  return out;
}
OUT.shadow = !!W._tvdShadow;
try { W.switchTab('vault'); W.renderVault(); } catch (e) {}
H.flush(1000, 3);
var shelf = H.ELS.get('vault-shelf');
OUT.shelf = words(shelf && shelf._html);
OUT.windows = {};
['uni-armor', 'uni-weap'].forEach(function (id) {
  try { W.openMuleCard(id); } catch (e) {}
  H.flush(1000, 3);
  var d = H.ELS.get('vault-detail');
  OUT.windows[id] = words(d && d._html);
});
"""


def _run(body, prelude):
    prog = VPN.program(body, prelude=prelude)
    for a, b in REBIND:
        if prog.count(a) != 1:
            raise AssertionError("vault_page_node moved: %r occurs %d times - this law cannot rebind its store" % (a, prog.count(a)))
        prog = prog.replace(a, b)
    r = subprocess.run([VPN.NODE, "-"], input=prog, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    if r.returncode != 0:
        raise AssertionError("the page did not run in node (exit %s): %s" % (r.returncode, (r.stderr or r.stdout)[-2500:]))
    lines = [ln[len("__VAULT_PAGE_NODE_OUT__"):] for ln in (r.stdout or "").splitlines() if ln.startswith("__VAULT_PAGE_NODE_OUT__")]
    if len(lines) != 1:
        raise AssertionError("the page printed %d result lines, not 1" % len(lines))
    return json.loads(lines[0])


def _key(phrase):
    """An ACT phrase as it reads on screen: its leading punctuation off, the page's escapes back."""
    return phrase.strip(" .;:·—").replace("&amp;", "&")


#: the ACT phrases this fixture paints on his board (a filed vault, a tile placed by hand, a copy held twice)
PAINTED = (". Drag it to any cell where it fits and it locks there", ". Drag to move it; right-click (or the lock) returns it to auto-pack",
           ". Enter picks it up, arrow keys move it, Enter drops, Escape cancels", "unlock — back to auto-pack (right-click the item does the same)",
           " — drop an item here to move it to this mule", ". Click (or Enter) to choose one: this locker’s items, or any item in the database",
           "send back to the unsorted dock", " · with a chip selected: assign it here")


class OnTheWholePageAShadowSaysReadOnly(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.own = _run(SEED + READ, OWNER)
        snap = dict(cls.own.get("snap") or {})
        snap["d2r_api_world"] = json.dumps({"machine": "mac", "profile": "main", "os": "MAC", "ledger": "KonyoEndgame", "cousin": False})
        cls.sh = _run(READ, "var SNAP = %s;\n" % json.dumps({"owner": "Konyo · Mac", "t": 1, "stores": snap}) + SHADOW_PRE + OWNER)
        cls.own_words = cls.own["shelf"] + sum(cls.own["windows"].values(), [])
        cls.sh_words = cls.sh["shelf"] + sum(cls.sh["windows"].values(), [])

    def test_premise_his_board_and_the_shadow_both_painted(self):
        self.assertIs(self.own["shadow"], False)
        self.assertIs(self.sh["shadow"], True, "the snapshot shadow did not open: %r" % self.sh.get("shadowRefused"))
        for side in (self.own, self.sh):
            self.assertGreater(len(side["shelf"]), 10, "premise: the shelf painted no locker card")
            for k, w in side["windows"].items():
                self.assertGreater(len(w), 30, "premise: the %s window painted %d words" % (k, len(w)))

    def test_on_his_board_the_action_words_are_there(self):
        text = "\n".join(self.own_words)
        missing = [_key(p) for p in PAINTED if _key(p) not in text]
        self.assertEqual(missing, [], "baseline: his board no longer says these")
        self.assertIn('movable item', text)

    def test_in_a_shadow_no_cell_or_tile_promises_an_action(self):
        text = "\n".join(self.sh_words)
        said = sorted(set(_key(p) for p, c in CLASS.items() if c == A and len(_key(p)) >= 12 and _key(p) in text))
        self.assertEqual(said, [], "a shadow cell or tile still promises these")
        short = [w for w in self.sh_words if re.match(r"^(unlock|remove copy|unequip) ", w)]
        self.assertEqual(short, [], "a shadow button still names its action")
        self.assertNotIn("movable item", text, "a shadow tile still calls itself movable")

    def test_in_a_shadow_each_says_it_is_read_only(self):
        n = sum(1 for w in self.sh_words if RO in w)
        self.assertGreaterEqual(n, 20, "only %d of the shadow's words say read only" % n)
        self.assertTrue(any(w.startswith("Skin of the Vipermagi (2×3) — placed by hand at") and RO in w for w in self.sh_words),
                        "the tile he placed does not say read only in the shadow")


RED_PROOF = [
    {"why": "REG-3117 - a filled tile says 'Drag it to any cell where it fits and it locks there' in a shadow again",
     "file": "bible.html",
     "find": "                 : gridActSay(' — packed automatically at ' + esc(_spot(p)), '. Drag it to any cell where it fits and it locks there')) : '')",
     "replace": "                 : ' — packed automatically at ' + esc(_spot(p)) + '. Drag it to any cell where it fits and it locks there') : '')",
     "matches": 1},
    {"why": "REG-3117 - a tile's key list (Enter picks it up...) is read in a shadow again",
     "file": "bible.html",
     "find": "               + (gridShadowRo() ? '' : ('. Enter picks it up, arrow keys move it, Enter drops, Escape cancels'",
     "replace": "               + (false ? '' : ('. Enter picks it up, arrow keys move it, Enter drops, Escape cancels'",
     "matches": 1},
    {"why": "REG-3117 - a shadow tile calls itself a movable item",
     "file": "bible.html",
     "find": "aria-roledescription=\"' + (gridShadowRo() ? 'item' : 'movable item') + '\"",
     "replace": "aria-roledescription=\"movable item\"",
     "matches": 1},
    {"why": "REG-3117 - the helper promises the action in a shadow",
     "file": "bible.html",
     "find": "    return gridShadowRo() ? (desc ? desc + '. ' : '') + 'Read only: this is their console, shown in a shadow' : desc + act;\n",
     "replace": "    return desc + act;\n",
     "matches": 1},
    {"why": "REG-3117 - the helper changes the words outside a shadow",
     "file": "bible.html",
     "find": "    return gridShadowRo() ? (desc ? desc + '. ' : '') + 'Read only: this is their console, shown in a shadow' : desc + act;\n",
     "replace": "    return (desc ? desc + '. ' : '') + 'Read only: this is their console, shown in a shadow';\n",
     "matches": 1},
    {"why": "REG-3117 - a Mule tab says 'drop an item here' in a shadow again",
     "file": "bible.html",
     "find": "title=\"'+gridActSay('Mule '+(_i+1), ' — drop an item here to move it to this mule')+'\">",
     "replace": "title=\"Mule '+(_i+1)+' — drop an item here to move it to this mule\">",
     "matches": 1},
    {"why": "REG-3117 - a locker card cell's ✕ says 'send back to the unsorted dock' in a shadow again",
     "file": "bible.html",
     "find": "    return gridActSay('', 'send back to the unsorted dock' + ((typeof cc === 'number' && cc > 1)",
     "replace": "    return ('' + 'send back to the unsorted dock' + ((typeof cc === 'number' && cc > 1)",
     "matches": 1},
    {"why": "REG-3117 - a new action phrase lands on a tile and nobody classified it",
     "file": "bible.html",
     "find": "'. Drag it to any cell where it fits and it locks there'",
     "replace": "'. Drag it to any cell where it fits and it locks there - or drop it on a Mule tab'",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
