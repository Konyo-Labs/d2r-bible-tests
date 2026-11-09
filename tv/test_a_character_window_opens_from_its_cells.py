# -*- coding: utf-8 -*-
"""#146 step 3c — an in-game character opens as a window of the cells a look already named.

REG-1887 — AND ITS DOLL IS THE VAULT'S. c637711e drew this window's ten cells as a 3x5 grid of its own, a third doll
beside the mule window's and the planner's. The cells are drawn by window._mpDollHtml now - the mule window's slot
markup on MULE_DOLL_SLOTS, the one geometry table - cut from bible.html by its markers and run here with the page's own
table (only the art lookup is a stub). No Vault doll on the page is UNKNOWN, never a grid of its own.

The card's Open door calls that window. The window's cells are equipped:helm and the other nine,
the same identity a vault look records. It does not open the planner and it does not write a build.
A character the ledger has not spoken about stays UNKNOWN, with no cell drawn as if it had been
looked at. Inventory, stash and belt cells are drawn as clickable surfaces (unseen until a look names them).
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import test_the_characters_tab_is_manual_and_separate as ROOM  # noqa: E402

CONSOLE = r"""
var location = { protocol: 'http:', search: '', hash: '', href: 'http://127.0.0.1:17999/', pathname: '/' };
var LEARNED_ANSWER = null, FETCHED = [];
function _syncThen(v){ return { then: function(f){ var r; try { r = f(v); } catch (e) { r = undefined; } return _syncThen(r); },
                                catch: function(){ return this; } }; }
function fetch(url){ FETCHED.push(String(url));
  if (LEARNED_ANSWER === 'FAIL') return { then: function(){ return this; }, catch: function(f){ f(new Error('down')); return this; } };
  return _syncThen({ ok: true, json: function(){ return LEARNED_ANSWER; } }); }
"""

ROSTER = r"""
var ROSTER = { ok: true, tierBars: { proven: 10, hardened: 20, wilson: 0.722 }, chars: [
  { name: 'Frostnova', cls: 'Sorceress', level: 71, pendingLevel: null, visits: 11, tier: 'PROVEN', looks: 11, trials: 11,
    title: null, lastTs: NOW - 7200000 },
  { name: 'Mulebox', cls: 'Sorceress', level: 1, pendingLevel: null, visits: 3, tier: 'WATCHED', looks: 3, trials: 3,
    title: null, lastTs: NOW - 86400000 } ] };
"""

GEAR = r"""
function withGear(){
  var A = JSON.parse(JSON.stringify(ROSTER));
  var slots = ['helm','amulet','weapon','torso','off-hand','gloves','ring1','belt','ring2','boots'].map(function(s){
    return s === 'helm' ? {slot: s, item: 'Harlequin Crest', sightings: 4, tier: 'PROVEN'}
                        : {slot: s, item: null, sightings: 0, tier: null}; });
  A.gear = { frostnova: { name: 'Frostnova', slots: slots,
    unplaced: [{item: 'String of Ears', sightings: 2, tier: 'WATCHED'}], reels: 2 } };
  return A;
}
"""


def _doll():
    """The Vault's doll from the page: its geometry table and its ONE renderer, between their own markers."""
    src = ROOM._src()
    return ("(function(){\n"
            "var esc = function(x){ return String(x == null ? '' : x).replace(/&/g,'&amp;').replace(/</g,'&lt;')"
            ".replace(/>/g,'&gt;').replace(/\"/g,'&quot;'); };\n"
            "function _mpSlotArt(e, g){ return '<i class=\"art-stub\" data-art=\"' + esc(e.name) + '\"></i>'; }\n"
            "var MULE_DOLL_SLOTS = [" + ROOM._between(src, "  var MULE_DOLL_SLOTS = [", "\n  ];") + "\n  ];\n"
            + "  /* ⟦MP DOLL BEGIN⟧" + ROOM._between(src, "  /* ⟦MP DOLL BEGIN⟧", "  /* ⟦MP DOLL END⟧ */") + "\n})();\n")


def _run(body, doll=True):
    return ROOM._run(ROSTER + GEAR + body, raw_patch=CONSOLE + (_doll() if doll else ""))


class ACharacterWindowOpensFromItsCells(unittest.TestCase):

    def test_open_is_the_window_and_not_the_planner(self):
        out = _run(r"""
          seed(null); LEARNED_ANSWER = withGear(); window.renderCharsTab();
          var ing = ELS['chars-list']._html;
          var ghost = (/<article class="chx-card chx-ghost" data-learned="seen:frostnova">([\s\S]*?)<\/article>/.exec(ing) || [])[1] || '';
          OUT.door = /data-act="window" onclick="window\._chxOpen\('seen:frostnova'\)"/.test(ghost);
          OUT.plans = (ing.match(/data-act="plan"/g) || []).length;
          var before = RAW['d2r_charBuilds'];
          window._chxOpen('seen:frostnova');
          OUT.html = ELS['chx-win'] ? ELS['chx-win']._html : '';
          OUT.hidden = ELS['chx-win'] ? ELS['chx-win'].hidden : null;
          OUT.opened = OPENED.slice();
          OUT.wrote = RAW['d2r_charBuilds'] !== before;
        """)
        self.assertTrue(out["door"], "the character card does not open its window")
        self.assertEqual(out["plans"], 0, "an in-game card still offers the planner")
        self.assertFalse(out["hidden"])
        self.assertIn('data-cell="equipped:helm"', out["html"])
        self.assertIn("Harlequin Crest", out["html"])
        self.assertIn('data-cell="equipped:boots" data-state="unseen"', out["html"])
        # REG-1887 - the Vault's doll draws them: its slots, on its geometry, and no grid of this window's own
        self.assertIn('data-doll="vault"', out["html"], "the window does not draw the Vault's doll")
        self.assertEqual(out["html"].count('class="mp-slot'), 10, "the Vault's doll did not draw its ten slots")
        self.assertNotIn('class="chx-cell"', out["html"], "the window drew a doll of its own again")
        self.assertIn('data-slot="head" style="left:calc(131*var(--du));top:calc(50*var(--du))', out["html"],
                      "the helm is not on MULE_DOLL_SLOTS' geometry")
        self.assertIn('data-slot="head" style="left:calc(131*var(--du));top:calc(50*var(--du));width:calc(60*var(--du));'
                      'height:calc(60*var(--du))" data-cell="equipped:helm"', out["html"], "the helm cell is not the head slot")
        self.assertIn('data-art="Harlequin Crest"', out["html"], "a seen item is not drawn with its art")
        self.assertIn('data-cell="inventory:', out["html"])
        self.assertIn('data-cell="stash:', out["html"])
        self.assertIn('data-grid="inventory" data-state="open"', out["html"])
        self.assertIn("String of Ears", out["html"])
        self.assertEqual(out["opened"], [], "opening the window opened the planner")
        self.assertFalse(out["wrote"], "opening the window wrote a build")

    def test_a_cell_says_what_was_seen_there(self):
        out = _run(r"""
          seed(null); LEARNED_ANSWER = withGear(); window.renderCharsTab();
          window._chxOpen('seen:frostnova');
          window._chxPick('equipped:helm');
          OUT.say = ELS['chx-win']._html;
          OUT.picked = ELS['chx-win'].getAttribute('data-picked');
          window._chxPick('equipped:boots');
          OUT.boots = ELS['chx-win']._html;
        """)
        self.assertEqual(out["picked"], "equipped:helm")
        self.assertIn("Helm · Harlequin Crest · Not confirmed yet · 4 looks", out["say"])
        self.assertIn("Boots · not seen yet", out["boots"])

    def test_no_vault_doll_is_unknown_never_a_grid_of_its_own(self):
        out = _run(r"""
          seed(null); LEARNED_ANSWER = withGear(); window.renderCharsTab();
          window._chxOpen('seen:frostnova');
          OUT.html = ELS['chx-win']._html;
        """, doll=False)
        self.assertIn("doll is not on this page", out["html"])
        self.assertIn('data-state="unknown"', out["html"])
        self.assertNotIn("data-cell=", out["html"], "with no Vault doll the window drew cells of its own")

    def test_unknown_and_unseen_draw_no_cell(self):
        out = _run(r"""
          seed(null); LEARNED_ANSWER = ROSTER; window.renderCharsTab();
          window._chxOpen('seen:frostnova');
          OUT.unknown = ELS['chx-win']._html;
          LEARNED_ANSWER = withGear(); window.renderCharsTab();
          window._chxOpen('seen:mulebox');
          OUT.none = ELS['chx-win']._html;
          window._chxClose();
          OUT.hidden = ELS['chx-win'].hidden;
        """)
        self.assertIn('data-state="unknown"', out["unknown"])
        self.assertNotIn("data-cell=", out["unknown"], "an unspoken ledger drew cells")
        self.assertIn('data-state="none"', out["none"])
        self.assertIn("No gear seen yet", out["none"])
        self.assertNotIn("data-cell=", out["none"], "a character with no gear drew cells")
        self.assertTrue(out["hidden"])


class ThereIsOneDoll(unittest.TestCase):
    """REG-1887 — the page draws a doll slot in ONE place: _mpDollSlotsHtml. The mule window hands it its slots (proved
    byte-identical to the inline map it replaced, on empty, equipped, picked, database and gone slots, before the commit)
    and the character window asks it through window._mpDollHtml. Read off the code with comments blanked."""

    def _code(self):
        import re
        src = ROOM._src()
        src = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), src, flags=re.S)
        return src

    def test_one_producer_of_a_doll_slot(self):
        code = self._code()
        self.assertEqual(code.count('class="mp-slot\''), 1, "a doll slot is drawn in more than one place")
        self.assertEqual(code.count("MULE_DOLL_SLOTS.map("), 1, "a second loop draws the doll's slots")
        self.assertEqual(code.count('class="chx-cell"'), 0, "the character window draws a doll of its own again")
        i = code.index("window.openMuleCard = function(muleId){")
        self.assertIn("var doll = _mpDollSlotsHtml(function(s){", code[i:i + 20000],
                      "the mule window no longer draws its slots with the one doll")
        self.assertEqual(code.count("window._mpDollHtml("), 1, "the character window does not ask the one doll")


RED_PROOF = [
    {
        "why": "the card must open the character window; sending it to the planner is the door he ruled out",
        "file": "bible.html",
        "find": 'data-act="window" onclick="window._chxOpen(\\\'',
        "replace": 'data-act="plan" onclick="window._charsPlan(\\\'',
        "matches": 1,
    },
    {
        "why": "a slot is addressed by the cell a look records; dropping data-cell leaves a button that is not that cell",
        "file": "bible.html",
        "find": "      var attrs = ' data-cell=\"' + esc(cell) + '\"' + ",
        "replace": "      var attrs = '' + ",
        "matches": 1,
    },
    {
        "why": "REG-1887 - the character window draws no doll from the Vault's renderer (a third doll would have to stand in)",
        "file": "bible.html",
        "find": "    if (typeof window._mpDollHtml !== 'function') return null;\n",
        "replace": "    return null;\n",
        "matches": 1,
    },
    {
        "why": "REG-1887 - the mule window draws its slots with a loop of its own again (a second doll)",
        "file": "bible.html",
        "find": "    var doll = _mpDollSlotsHtml(function(s){   /* REG-1887 — the one doll's markup; this window hands it the state and its doors */\n",
        "replace": "    var doll = MULE_DOLL_SLOTS.map(function(s){ return ''; }).join('') + _mpDollSlotsHtml(function(s){\n",
        "matches": 1,
    },
    {
        "why": "REG-1887 - the one doll drops each slot's doors, so neither window's cells open anything",
        "file": "bible.html",
        "find": "        + (x.attrs || '')\n",
        "replace": "",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
