# -*- coding: utf-8 -*-
"""#230 (REG-3103, GrokBot v3838 07:08-07:25) - IN A SHADOW A LOOKUP ANSWERS, AND EVERY BOX THAT WRITES STAYS DEAD.

GrokBot in the ALT's and the Mac's shadow: FIND on a mule ("Which mule holds it?") took the focus, and typing "Wraith Scarab"
or "Nightwing" left it empty with no result. The shadow's key filter passed only the keys that move the view and Ctrl+C/F/A,
and its input veil stopped every input event, so every box was dead alike - a viewer could not ask the owner's vault where an
item sits. Now the veil names its lookups: each box that only searches or filters a view over the owner's data and writes
nothing takes a typed key, a paste and the input they make, and Esc clears it before an Esc leaves. Enter in a box stays
stopped (where a box acts), and every box not named stays dead: the vault's add, a count, a note, an affix.

THE SWEEP: every <input>, <textarea>, <select> and created box in bible.html's code is found and named here, as a lookup
or as refused with the reason. A new box fails this law until it is classified, and the veil's list must be exactly the
lookups named here.

Also (GrokBot's nit): an empty inventory cell's title said "click (or Enter) to add an item from the database" in the
shadow, where both are stopped. In a shadow it says the console is theirs, in the D2JSP fg box's words (REG-3095).

Driven: (1) the sweep over bible.html's code, comments out; (2) the veil's own script (VIEW through the leave-on-Escape
listener) cut out of bible.html and run in node over a fake document - every named lookup and every refused text box gets
a typed key, a paste, an input, an Enter and an Esc; (3) the cell's title helper cut out and run outside and inside a
shadow - never a browser. RED_PROOF below.
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
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
NODE = shutil.which("node")
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")

L = "lookup"
R = "refused"
SEL = "a select: a shadow stops its change - a view filter at most, not a typed lookup"
NUM = "a number: a count or a setting he keeps"
FILE = "a file picker: it loads into his store"
TICK = "a tick box: it records what he did"
# Every box on the board, by the name the sweep reads off it (its id, else its aria-label, else its first class, else its
# handler). A lookup's name is also its selector in the veil's LOOKUP list.
CLASS = {
    # --- lookups: each searches or filters a view and writes nothing (read at v3838)
    "#vault-find-input": (L, "FIND on a mule: vaultFind is a pure read + paint (REG-2230)"),
    "#gsearch-input": (L, "the bible's search: renders results; its Enter (a jump) stays stopped"),
    "#v42-palette-input": (L, "the jump palette: filters the jump list"),
    "#item-search": (L, "uniques and sets search: sets searchQ and renders"),
    "#rwc-search": (L, "runeword chronicle filter: renders"),
    "#all-rw-filter": (L, "all runewords filter: renders"),
    "#iv-filter": (L, "item values filter: renders"),
    "#rw-bases-filter": (L, "runeword bases filter: renders"),
    "#horadric-filter": (L, "cube recipes filter: renders"),
    "#hvf-filter": (L, "high-value finds filter: renders"),
    "#d2jsp-find": (L, "the D2JSP desk's find: hides cards that do not match"),
    "#gf-found-q": (L, "filter your finds: _ledgerFilter hides chips"),
    "#gs-found-q": (L, "filter your sets: _ledgerFilter hides blocks"),
    'input[aria-label="filter the stats"]': (L, "a locker's stats filter: _mpFilter hides rows"),
    'input[aria-label="filter this wall"]': (L, "a forge wall's filter: hides tiles, keeps the typed text in view state"),
    'input[aria-label="search this list and tick items off"]': (L, "the tally search: lists matches; its tick (a click or Enter) stays stopped"),
    'input[aria-label="search the stats"]': (L, "the builder's stats filter: hides rows"),
    'input[aria-label="search the stash"]': (L, "the builder's stash search: filters the stash view"),
    # --- typed boxes that write, or feed a write
    "#d2jsp-price-q": (R, "PRICE SEARCH: asks the console's d2jsp reader, which fetches and logs reads - not a view filter (v3848)"),
    "#vault-planner-q": (R, "add an item from the planner: its picks file items"),
    "#vault-hand-q": (R, "the planner list: Enter adds the exact name"),
    "#vmk-add-input": (R, "add an item to collect spares of (GrokBot: confirmed locked)"),
    "#vme-text": (R, "edit an item's mods in place from the tile pencil - a write; a shadow has no pencil (v3849 D2)"),
    "#cb-pick-q": (R, "the builder's item picker: its Enter and its rows put an item on a build"),
    "#cb-base-q": (R, "the builder's base search: its rows set an item's base"),
    "#cb-add-q": (R, "the builder's add search: its rows add an item"),
    "#ask-input": (R, "asks the console a question: a send, not a lookup over his data"),
    "input.ui-prompt-input": (R, "the board's prompt box: it answers a write (a rename, a name)"),
    'input[aria-label="Forum gold for this item"]': (R, "the D2JSP fg price he posts (REG-3095)"),
    'input[aria-label="affix on this item"]': (R, "AI intake: writes an affix"),
    'input[aria-label="rolled name of this item"]': (R, "AI intake: writes a name"),
    'input[aria-label="base type of this item"]': (R, "AI intake: writes a base"),
    'input[aria-label="your MAIN character name"]': (R, "writes his MAIN's name"),
    'input[aria-label="which character or mule holds this"]': (R, "writes where an item is held"),
    'input[aria-label^="per-level roll "]': (R, "the builder: writes a roll"),
    'input[aria-label^="roll "]': (R, "the builder: writes a roll"),
    "#backup-textarea": (R, "a backup code: loads into his store"),
    "#rune-import-box": (R, "rune import: writes his tallies"),
    "#gem-import-box": (R, "gem import: writes his tallies"),
    "#material-import-box": (R, "material import: writes his tallies"),
    "#cb-notes": (R, "a build's notes: saved on blur"),
    'textarea[aria-label="notes on this locker \u2014 saved on Enter or when you leave the box; Shift+Enter for a new line"]':
        (R, "a locker's notes: saved on Enter"),
    "createElement:textarea": (R, "the copy-to-clipboard helper: never shown, never typed in"),
    # --- selects
    "#rune-cubeup-target": (R, SEL), "#gem-cubeup-type": (R, SEL), "#gem-cubeup-q": (R, SEL),
    "#cb-filt": (R, SEL), 'select[aria-label="filter results"]': (R, SEL),
    "#cb-build": (R, "picks the active build"), "#cb-cls": (R, "writes a build's class"),
    "#cb-base": (R, "writes an item's base"), "#cb-qual": (R, "writes an item's quality"),
    "#cb-rn0": (R, "writes a rare name"), "#cb-rn1": (R, "writes a rare name"), "#cb-lq": (R, "writes a low-quality word"),
    'select[aria-label="base (fixed)"]': (R, "a disabled base: nothing to type"),
    'select[aria-label^="socket "]': (R, "writes a socket filler"),
    'select[aria-label="quality of this item"]': (R, "AI intake: writes a quality"),
    'select[aria-label="which class it rolled - blank is one random class"]': (R, "the builder: writes a class roll"),
    'select[aria-label^="where every copy of "]': (R, "writes a keeper's destination"),
    # --- numbers, ranges, files, ticks
    "#mf": (R, "his MF setting"), "#players": (R, "his players setting"), "#mfNumberInput": (R, NUM),
    "#gic-sim-runs": (R, NUM), "#puv-runs": (R, NUM), "#cb-new-lvl": (R, NUM), "#cb-ilvl": (R, NUM),
    "#cb-def": (R, NUM), "#cb-sockets": (R, NUM), 'input[aria-label^="new count for "]': (R, NUM),
    "#backup-file": (R, FILE), "#craft-intake-file": (R, FILE), "#chron-shot-file": (R, FILE),
    "#vault-profile-file": (R, FILE), "#vault-dir-input": (R, FILE), "#aic-file": (R, FILE),
    "#cb-eth": (R, TICK), 'input[aria-label="mark moved"]': (R, TICK), 'input[aria-label="untick: not moved yet"]': (R, TICK),
    'input[aria-label^="I made "]': (R, TICK), 'input[onchange*="vaultShareToggle"]': (R, TICK),
    'input[aria-label^="I hovered every item in "]': (R, TICK),
}


def _code(src):
    """bible.html with its comments blanked, line numbers kept: HTML comments, bounded block comments (never a '/*' that
    follows a word, a quote or a slash - "image/*" is an attribute, not a comment) and // comments that are not a URL's."""
    blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))
    src = re.sub(r"<!--.{0,4000}?-->", blank, src, flags=re.S)
    src = re.sub(r"(?<![\w\"'/=*])/\*.{0,4000}?\*/", blank, src, flags=re.S)
    return re.sub(r"(?<![:'\"\\])//[^\n]*", blank, src)


def _name(tag, w):
    m = re.search(r'\bid="([A-Za-z0-9_-]+)"', w)
    if m:
        return "#" + m.group(1)
    m = re.search(r'aria-label="([^"\']*)"', w)
    if m:
        return '%s[aria-label="%s"]' % (tag, m.group(1))
    m = re.search(r'aria-label="([^"\']+)\'', w)
    if m:
        return '%s[aria-label^="%s"]' % (tag, m.group(1))
    m = re.search(r'class="([A-Za-z0-9_-]+)', w)
    if m:
        return "%s.%s" % (tag, m.group(1))
    m = re.search(r'\b(on(?:change|input|click|keydown))="(?:window\.)?([A-Za-z_$][\w$]*)', w)
    if m:
        return '%s[%s*="%s"]' % (tag, m.group(1), m.group(2))
    return tag


def sweep(src):
    """[(line, name)] - every box the board's code makes."""
    code = _code(src)
    out = []
    for m in re.finditer(r"<(input|textarea|select)\b|createElement\('(input|textarea|select)'\)", code):
        if m.group(2):
            name = "createElement:" + m.group(2)
        else:
            w = code[m.start():m.start() + 700]
            j = w.find(">")
            name = _name(m.group(1), w[:j] if j > 0 else w)
        out.append((code.count("\n", 0, m.start()) + 1, name))
    return out


def _between(src, start, end):
    i = src.index(start)
    return src[i:src.index(end, i + len(start))]


with open(BIBLE, encoding="utf-8") as _fh:
    PAGE = _fh.read()


_ro0 = PAGE.index("function _unconfReadOnly(){")
RO_FN = PAGE[_ro0:PAGE.index("\n}\n", _ro0) + 3]   # the page's one read-only test, which gridShadowRo asks

class EveryBoxIsNamedALookupOrRefused(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sites = sweep(PAGE)
        cls.names = set(n for _, n in cls.sites)
        m = re.search(r"    var LOOKUP = \[(.*?)\]\.join\(', '\);", PAGE, re.S)
        cls.veil = re.findall(r"'([^']+)'", m.group(1)) if m else None

    def test_premise_the_sweep_sees_the_boards_boxes(self):
        self.assertGreater(len(self.sites), 80, "premise: the sweep found %d boxes - it is blind" % len(self.sites))
        for must in ("#vault-find-input", "#vmk-add-input", 'input[aria-label="Forum gold for this item"]'):
            self.assertIn(must, self.names, "premise: the sweep did not find %s" % must)

    def test_every_box_is_classified(self):
        new = sorted("%s (line %d)" % (n, ln) for ln, n in self.sites if n not in CLASS)
        self.assertEqual(new, [], "a box nobody classified - name it a lookup (it searches a view and writes nothing) "
                                  "or refused, with the reason")

    def test_no_class_names_a_box_that_is_gone(self):
        self.assertEqual(sorted(set(CLASS) - self.names), [], "a classified box is no longer on the board")

    def test_the_veil_lets_exactly_the_named_lookups_type(self):
        self.assertIsNotNone(self.veil, "the shadow veil has no LOOKUP list")
        self.assertEqual(sorted(self.veil), sorted(k for k, (c, _) in CLASS.items() if c == L))
        for s in self.veil:
            self.assertRegex(s, r'^(#[\w-]+|input\[aria-label="[^",]+"\])$', "a lookup selector the veil cannot match safely")


FAKES = r"""
var LISTEN = {}, POSTS = [], CLASSES = {};
var document = { addEventListener: function(t, f){ (LISTEN[t] = LISTEN[t] || []).push(f); },
                 documentElement: { classList: { contains: function(c){ return !!CLASSES[c]; } } } };
var window = { location: { origin: 'http://127.0.0.1' } };
var host = { postMessage: function(m){ POSTS.push(m.type); } };
function Event(type, o){ this.type = type; this.bubbles = !!(o && o.bubbles); }
function split(s){ return String(s).split(',').map(function(x){ return x.trim(); }); }
function box(sel, value){
  return { tagName: 'INPUT', value: value || '', sel: sel, fired: [],
    matches: function(s){ var me = this.sel; return split(s).some(function(x){ return x === me; }); },
    closest: function(s){ return (this.matches(s) || split(s).indexOf('input') >= 0) ? this : null; },
    getAttribute: function(){ return null; },
    dispatchEvent: function(e){ this.fired.push(e.type); return true; } };
}
function fire(type, target, extra){
  var ev = { type: type, key: (extra && extra.key) || '', target: target, ctrlKey: false, metaKey: false, altKey: false,
             stopped: false, prevented: false,
             preventDefault: function(){ this.prevented = true; }, stopImmediatePropagation: function(){ this.stopped = true; } };
  for (var k in (extra || {})) ev[k] = extra[k];
  (LISTEN[type] || []).forEach(function(f){ if (!ev.stopped) f(ev); });
  return ev;
}
"""

SCENARIO = r"""
var out = { lookup: {}, refused: {} };
function probe(sel){
  var b = box(sel), r = {};
  r.key = !fire('keydown', b, { key: 'W' }).stopped;
  r.press = !fire('keypress', b, { key: 'W' }).stopped;
  r.back = !fire('keydown', b, { key: 'Backspace' }).stopped;
  r.input = !fire('input', b).stopped;
  r.paste = !fire('paste', b).stopped;
  r.cmdV = !fire('keydown', b, { key: 'v', metaKey: true }).stopped;
  r.enter = !fire('keydown', b, { key: 'Enter' }).stopped;
  r.cmdZ = !fire('keydown', b, { key: 'z', metaKey: true }).stopped;
  r.altKey = !fire('keydown', b, { key: 'w', altKey: true }).stopped;
  r.change = !fire('change', b).stopped;
  return r;
}
LOOK.forEach(function(s){ out.lookup[s] = probe(s); });
REFUSE.forEach(function(s){ out.refused[s] = probe(s); });
out.plain = probe('div.not-a-box');
// Esc: a typed lookup is cleared (its input event re-filters the view) and stays; an empty one leaves
var f = box('#vault-find-input', 'Nightwing');
var e1 = fire('keydown', f, { key: 'Escape' });
out.esc1 = { value: f.value, fired: f.fired.slice(), posts: POSTS.slice(), stopped: e1.stopped };
fire('keydown', f, { key: 'Escape' });
out.esc2 = { posts: POSTS.slice() };
POSTS.length = 0;
var w = box('#vmk-add-input', 'Gore Rider');
fire('keydown', w, { key: 'Escape' });
out.escWrite = { value: w.value, posts: POSTS.slice() };
process.stdout.write(JSON.stringify(out));
"""

REFUSED_BOXES = sorted(k for k, (c, _) in CLASS.items() if c == R and not k.startswith("createElement:"))


class TheVeilLetsALookupAnswerAndKeepsTheWritesDead(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        veil = _between(PAGE, "    var VIEW = ['switchTab'",
                        "    window._tvdShadow = { owner: String((snap && snap.owner) || ''), t: snap && snap.t, mem: mem };")
        look = sorted(k for k, (c, _) in CLASS.items() if c == L)
        head = "var LOOK = %s, REFUSE = %s;\n" % (json.dumps(look), json.dumps(REFUSED_BOXES))
        seen = {}

        def _node(argv, **kw):
            seen["encoding"] = kw.get("encoding")
            return subprocess.run(argv, **kw)

        r = _node([NODE, "-"], input=FAKES + head + veil + "\n" + SCENARIO, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if r.returncode != 0:
            raise AssertionError("the shadow veil did not run in node: %s" % r.stderr[-900:])
        cls.o = json.loads(r.stdout)
        cls.node_encoding = seen.get("encoding")

    def test_premise_every_lookup_and_every_refused_text_box_was_driven(self):
        self.assertEqual(len(self.o["lookup"]), 18)
        self.assertGreater(len(self.o["refused"]), 30)

    def test_find_answers_in_a_shadow(self):
        f = self.o["lookup"]["#vault-find-input"]
        self.assertTrue(f["key"] and f["press"] and f["back"], "FIND did not take a typed key: %r" % f)
        self.assertTrue(f["input"], "FIND's input event was stopped, so vaultFind never ran: %r" % f)
        self.assertTrue(f["paste"] and f["cmdV"], "a name could not be pasted into FIND: %r" % f)

    def test_every_lookup_takes_keys_input_and_paste(self):
        bad = dict((s, r) for s, r in self.o["lookup"].items() if not (r["key"] and r["press"] and r["back"] and r["input"]
                                                                        and r["paste"] and r["cmdV"]))
        self.assertEqual(bad, {}, "a named lookup stayed dead in a shadow")

    def test_a_lookups_enter_and_its_shortcuts_stay_stopped(self):
        bad = dict((s, r) for s, r in self.o["lookup"].items() if r["enter"] or r["cmdZ"] or r["altKey"] or r["change"])
        self.assertEqual(bad, {}, "a lookup's Enter, Cmd+Z, Alt key or change reached the board in a shadow")

    def test_every_box_that_writes_stays_dead(self):
        live = dict((s, [k for k, v in r.items() if v]) for s, r in self.o["refused"].items() if any(r.values()))
        self.assertEqual(live, {}, "a write box took a key, an input or a paste in a shadow")
        self.assertFalse(any(self.o["plain"].values()), "a key on no box reached the board: %r" % self.o["plain"])

    def test_the_veil_goes_to_node_as_utf8(self):
        self.assertEqual(self.node_encoding, "utf-8")

    def test_esc_clears_a_typed_lookup_then_leaves(self):
        e1 = self.o["esc1"]
        self.assertEqual(e1["value"], "", "Esc did not clear the typed FIND")
        self.assertIn("input", e1["fired"], "the cleared FIND was not re-run")
        self.assertEqual(e1["posts"], [], "Esc in a typed FIND left the shadow instead of clearing it")
        self.assertEqual(self.o["esc2"]["posts"], ["tvd-shadow-leave"], "Esc in an empty FIND no longer leaves")
        self.assertEqual(self.o["escWrite"], {"value": "Gore Rider", "posts": ["tvd-shadow-leave"]},
                         "Esc in a write box did something other than leave")


CELL = r"""
var CLASSES = {};
var document = { documentElement: { classList: { contains: function(c){ return !!CLASSES[c]; } } } };
var window = {};
"""

CELL_SCENARIO = r"""
var out = { own: gridCellSay('Inventory', 2, 0) };
window._tvdShadow = { owner: 'Konyo · Mac' }; out.snap = gridCellSay('Inventory', 2, 0);
delete window._tvdShadow; CLASSES['tvd-shadow'] = true; out.cls = gridCellSay(null, 0, 3);
process.stdout.write(JSON.stringify(out));
"""


class AnEmptyCellSaysItIsReadOnlyInAShadow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        fn = RO_FN + _between(PAGE, "  function gridCellSay(label, cx, cy){", "  function gridHtml(placed, gw, gh, cell, opt){")
        cls.cell_src = CELL + fn + "\n" + CELL_SCENARIO
        seen = {}

        def _node(argv, **kw):
            seen["encoding"] = kw.get("encoding")
            return subprocess.run(argv, **kw)

        r = _node([NODE, "-"], input=cls.cell_src, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if r.returncode != 0:
            raise AssertionError("the cell title did not run in node: %s" % r.stderr[-900:])
        cls.o = json.loads(r.stdout)
        cls.node_encoding = seen.get("encoding")

    def test_the_grid_asks_this_helper(self):
        self.assertIn("var _csay = gridCellSay(opt.label, cx, cy);", PAGE)

    def test_outside_a_shadow_the_cell_offers_the_add(self):
        self.assertEqual(self.o["own"], "Inventory · col 3 · row 1 — empty: click (or Enter) to add an item from the database")

    def test_in_a_shadow_the_cell_says_it_is_read_only(self):
        for k, where in (("snap", "Inventory · col 3 · row 1"), ("cls", "Inventory · col 1 · row 4")):
            self.assertEqual(self.o[k], where + " — empty. Read only: this is their console, shown in a shadow",
                             "the %s shadow's empty cell still offered the add" % k)

    def test_the_cell_slice_is_handed_to_node_as_utf8(self):
        # Same slice as the shadow-cell law: the ✕ in the gridActSay comment is not cp1255.
        self.assertEqual(self.node_encoding, "utf-8")
        self.assertIn("\u2715", self.cell_src)
        with self.assertRaises(UnicodeEncodeError):
            self.cell_src.encode("cp1255")


RED_PROOF = [
    {"why": "REG-3103 - a new box lands on the board and nobody classified it",
     "file": "bible.html",
     "find": "<input id=\"vault-find-input\" class=\"vault-find-input\"",
     "replace": "<input id=\"vault-find-new\" class=\"vault-find-input\"",
     "matches": 1},
    {"why": "REG-3103 - FIND takes no key in a shadow again",
     "file": "bible.html",
     "find": "    var LOOKUP = ['#vault-find-input', '#gsearch-input',",
     "replace": "    var LOOKUP = ['#gsearch-input',",
     "matches": 1},
    {"why": "REG-3103 - a lookup's typed key is stopped again",
     "file": "bible.html",
     "find": "      if (lookupBox(ev.target) && ev.key !== 'Enter' && !ev.altKey\n",
     "replace": "      if (false && ev.key !== 'Enter' && !ev.altKey\n",
     "matches": 1},
    {"why": "REG-3103 - a lookup's input event is stopped again (the box fills, the find never runs)",
     "file": "bible.html",
     "find": "        if ((type === 'input' || type === 'paste') && lookupBox(ev.target)) return;   // REG-3103 - a lookup takes it\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3103 - a lookup's Enter reaches the board (the tally ticks, the add adds)",
     "file": "bible.html",
     "find": "      if (lookupBox(ev.target) && ev.key !== 'Enter' && !ev.altKey\n",
     "replace": "      if (lookupBox(ev.target) && !ev.altKey\n",
     "matches": 1},
    {"why": "REG-3103 - Cmd+Z and every shortcut reach the board from a lookup",
     "file": "bible.html",
     "find": "          && (!(ev.ctrlKey || ev.metaKey) || /^v$/i.test(String(ev.key || '')))) return true;\n",
     "replace": "          ) return true;\n",
     "matches": 1},
    {"why": "REG-3103 - a paste into a lookup is stopped",
     "file": "bible.html",
     "find": "        if ((type === 'input' || type === 'paste') && lookupBox(ev.target)) return;",
     "replace": "        if ((type === 'input') && lookupBox(ev.target)) return;",
     "matches": 1},
    {"why": "REG-3103 - every box takes keys in a shadow (the write boxes too)",
     "file": "bible.html",
     "find": "      try { return !!(el && el.matches && el.matches(LOOKUP)); } catch (e) { return false; }\n",
     "replace": "      return !!(el && el.matches);\n",
     "matches": 1},
    {"why": "REG-3103 - Esc in a typed FIND leaves the shadow instead of clearing it",
     "file": "bible.html",
     "find": "      if (lookupBox(ev.target) && ev.target.value) {   // REG-3103 - Esc clears a typed lookup first; the next Esc leaves\n",
     "replace": "      if (false) {\n",
     "matches": 1},
    {"why": "REG-3103 - Esc empties the lookup and the view is never re-filtered",
     "file": "bible.html",
     "find": "        try { ev.target.dispatchEvent(new Event('input', { bubbles: true })); } catch (e) {}\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3103 - the empty cell offers the add in a snapshot shadow",
     "file": "bible.html",
     "find": "  if (window._tvdShadow) return true;   /* the shadow law's guard form: a shadow refuses, it never draws differently */\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3103 - the empty cell offers the add in a shadow known by its class",
     "file": "bible.html",
     "find": "    return typeof _unconfReadOnly === 'function' ? !!_unconfReadOnly() : false;   /* the page's one read-only test */\n",
     "replace": "    return false;\n",
     "matches": 1},
    {"why": "REG-3103 - the grid writes its own title and never asks the helper",
     "file": "bible.html",
     "find": "        var _csay = gridCellSay(opt.label, cx, cy);   /* REG-3103 */\n",
     "replace": "        var _csay = (opt.label || 'Inventory') + ' · col ' + (cx + 1) + ' · row ' + (cy + 1) + ' — empty: click (or Enter) to add an item from the database';\n",
     "matches": 1},
    {"why": "v3849 - the veil goes to node in the console encoding",
     "file": "test_a_lookup_answers_in_a_shadow.py",
     "find": "r = _node([NODE, \"-\"], input=FAKES + head + veil + \"\\n\" + SCENARIO, capture_output=True, text=True, encoding=\"utf-8\", errors=\"replace\", timeout=60)\n",
     "replace": "r = _node([NODE, \"-\"], input=FAKES + head + veil + \"\\n\" + SCENARIO, capture_output=True, text=True, timeout=60)\n",
     "matches": 1},
    {"why": "v3849 - the cell slice goes to node in the console encoding and cp1255 dies on the mark in the comment",
     "file": "test_a_lookup_answers_in_a_shadow.py",
     "find": "r = _node([NODE, \"-\"], input=cls.cell_src, capture_output=True, text=True, encoding=\"utf-8\", errors=\"replace\", timeout=60)\n",
     "replace": "r = _node([NODE, \"-\"], input=cls.cell_src, capture_output=True, text=True, timeout=60)\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
