# -*- coding: utf-8 -*-
"""REG-2980 (his ruling 2026-10-29 ~01:00 IDT: "so make it ... war-A war-B") - THE BOARD NAMES A WAR MULE BY A NAME THE GAME
ACCEPTS.

agent-guide measured that a D2R character name is 2-15 letters with at most one '-' or '_' and NO digit, so the "WAR1" the
board made (REG-2803) and asked him to create in the game could never be created. Now war number n is named by letter:
1 is WAR-A, 2 WAR-B, ... 26 WAR-Z, 27 WAR-AA. The board's mule carries that exact name, and the make task asks for it.
The number still binds to the id (warN, REG-2804) and decides everything. REG-2889's take-back stays keyed by the number.
Two more parts:
  - a war mule the BOARD made under the old WAR<n> name takes its letter name once, marked on the mule; one HE named keeps
    his name;
  - a mule he creates as WAR-B is war mule 2, as one he created as WAR2 was.
This pins the RULE (a legal name derived from warN, mapped back to the same number), not one string. Whole page in node,
never a browser. RED_PROOF below.
"""
import json
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
import vault_page_node as VPN  # noqa: E402

CLAIM = "localStorage.setItem('d2r_ownerClaim', '*');\n"
SHAKO = "Harlequin Crest (Shako)"
LEGAL = re.compile(r"^[A-Za-z]+(?:[-_][A-Za-z]+)?$")     # letters, at most one '-' or '_', no digit


def _legal(name):
    return bool(LEGAL.match(name or "")) and 2 <= len(name) <= 15


RULE = r"""
var W = window;
OUT.names = []; for (var n = 1; n <= 60; n++) OUT.names.push([n, W._vaultWarName(n), W._vaultLettersN(String(W._vaultWarName(n)).replace(/^WAR[-_]/, ''))]);
"""
MADE = r"""
var W = window, SH = %s;
W._vaultAutoIntakeSet(false);
[SH, SH, SH].forEach(function(n){ W.vaultHandAdd(n); }); W.renderVault(); H.flush(60, 3); W.renderVault();
OUT.wars = JSON.parse(W.LSR.getItem('d2r_muleRoster') || '[]').filter(function(m){ return W._vaultWarRole(m) > 0; }).map(function(m){ return [m.name, W._vaultWarRole(m), !!m.auto]; });
OUT.make = []; var _mr = /Create mule <b>([^<]*)<\/b> in the game — the board made it/g, _mm, _ml = (document.getElementById('vault-move-list') || {}).innerHTML || '';
while ((_mm = _mr.exec(_ml))) OUT.make.push(_mm[1]);   /* the CHARMS mule the board makes (REG-2895) asks too */
W.prompt = function(){ return 'war-b'; }; W.vaultAddMule();
OUT.hand = JSON.parse(W.LSR.getItem('d2r_muleRoster') || '[]').filter(function(m){ return String(m.name).toUpperCase() === 'WAR-B'; }).map(function(m){ return [m.name, W._vaultWarRole(m)]; });
""" % json.dumps(SHAKO)
GUEST = r"""
var W = window, SH = %s;
W._vaultAutoIntakeSet(false);
[SH, SH, SH].forEach(function(n){ W.vaultHandAdd(n); }); W.renderVault(); H.flush(60, 3);
var ml = (document.getElementById('vault-move-list') || {}).innerHTML || '', i = ml.indexOf('vmv-warfull');
OUT.line = i < 0 ? '' : ml.slice(i, i + 700).replace(/<[^>]+>/g, '');
""" % json.dumps(SHAKO)
LEGACY = r"""
var W = window;
OUT.roster = JSON.parse(W.LSR.getItem('d2r_muleRoster') || '[]').filter(function(m){ return W._vaultWarRole(m) > 0; })
  .map(function(m){ return [m.id, m.name, W._vaultWarRole(m), !!(m.auto && m.auto.letterName)]; });
"""


def _base():
    r = VPN.run("OUT.r = JSON.parse(window.LSR.getItem('d2r_muleRoster') || 'null') || "
                "(window._vaultRosterNow && window._vaultRosterNow());", prelude=CLAIM, timeout=300).get("r")
    if not isinstance(r, list) or not r:
        raise AssertionError("PREMISE: the page has no default roster: %r" % (r,))
    return [m for m in r if not str(m.get("name", "")).upper().startswith("WAR")]


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class TheBoardNamesAWarMuleByANameTheGameAccepts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rule = VPN.run(RULE, prelude=CLAIM, timeout=300)
        cls.made = VPN.run(MADE, prelude=CLAIM, timeout=300)
        cls.guest = VPN.run(GUEST, prelude="", timeout=300)
        roster = _base() + [
            {"id": "mboard1", "name": "WAR1", "icon": "x", "added": True, "role": "war", "warN": 1,
             "auto": {"by": "board", "at": "2026-10-28T18:00:00Z", "why": "law"}},          # the board made it, old name
            {"id": "mhis2", "name": "WAR2", "icon": "x", "added": True, "role": "war", "warN": 2}]   # he named it
        cls.legacy = VPN.run(LEGACY, prelude=CLAIM + "localStorage.setItem('d2r_muleRoster', %s);\n" % json.dumps(json.dumps(roster)), timeout=300)
        cls.again = VPN.run(LEGACY, prelude=CLAIM + "localStorage.setItem('d2r_muleRoster', %s);\n"
                            % json.dumps(json.dumps(_reloaded(cls.legacy, roster))), timeout=300)

    def test_every_war_number_has_a_legal_name_that_maps_back_to_it(self):
        names = self.rule["names"]
        self.assertEqual(self.rule["__boot"]["errors"], [], self.rule["__boot"])
        for n, name, back in names:
            self.assertTrue(_legal(name), "war mule %d's name %r is not one the game accepts" % (n, name))
            self.assertEqual(back, n, "%r does not map back to war number %d" % (name, n))
        self.assertEqual(len(set(x[1] for x in names)), len(names), "two war numbers share a name")

    def test_the_board_makes_and_asks_for_the_letter_name(self):
        m = self.made
        self.assertEqual(m["wars"], [[self.rule["names"][0][1], 1, True]], m["wars"])
        self.assertTrue(_legal(m["wars"][0][0]))
        self.assertIn(m["wars"][0][0], m["make"], "the make task does not ask for the board's mule by its name: %r" % m)
        self.assertFalse([x for x in m["make"] if re.search(r"\d", x)], "a make task asks for a name with a digit: %r" % m["make"])

    def test_a_mule_he_creates_as_war_b_is_war_mule_2(self):
        self.assertEqual(self.made["hand"], [["WAR-B", 2]], self.made["hand"])

    def test_the_no_room_line_names_the_letter_names(self):
        line = self.guest["line"]
        self.assertIn("make a mule named WAR-A (then WAR-B", line, line)
        self.assertNotRegex(line, r"WAR\d", "the no-room line still asks for a name with a digit: %r" % line)

    def test_a_board_made_war1_takes_its_letter_name_once_and_his_own_name_stays(self):
        rows = dict((r[0], r[1:]) for r in self.legacy["roster"])
        self.assertEqual(rows.get("mboard1"), ["WAR-A", 1, True], "the board's old WAR1 was not renamed to its letter name: %r" % rows)
        self.assertEqual(rows.get("mhis2"), ["WAR2", 2, False], "a war mule he named was renamed: %r" % rows)
        again = dict((r[0], r[1:]) for r in self.again["roster"])
        self.assertEqual(again.get("mboard1"), ["WAR1", 1, True], "his later rename of the board's mule was undone: %r" % again)


def _reloaded(legacy, roster):
    """the roster after the rename, then HIS rename of the board's mule back to WAR1 - the next load must not undo it"""
    out = []
    for m in roster:
        m = dict(m)
        if m["id"] == "mboard1":
            m["name"] = "WAR1"
            m["auto"] = dict(m["auto"], letterName={"from": "WAR1", "at": "2026-10-29T01:00:00Z"})
        out.append(m)
    return out


RED_PROOF = [
    {"why": "REG-2980 - the board names war mule n 'WAR<n>' again, a name the game refuses",
     "file": "bible.html",
     "find": "  function _vaultWarName(n){ return 'WAR-' + _vaultLetters((n | 0) || 1); }",
     "replace": "  function _vaultWarName(n){ return 'WAR' + ((n | 0) || 1); }",
     "matches": 1, "needs": "node"},
    {"why": "REG-2980 - war numbers past 26 share a name (the letters never carry)",
     "file": "bible.html",
     "find": "    while (k > 0) { k--; s = String.fromCharCode(65 + (k % 26)) + s; k = Math.floor(k / 26); }",
     "replace": "    while (k > 0) { k--; s = String.fromCharCode(65 + (k % 26)) + s; k = 0; }",
     "matches": 1, "needs": "node"},
    {"why": "REG-2980 - a board-made WAR1 keeps the name the game refuses",
     "file": "bible.html",
     "find": "      m.name = nm; changed = true;\n",
     "replace": "      changed = false;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2980 - his rename of the board's mule is undone on every load (no mark on the mule)",
     "file": "bible.html",
     "find": "      if (!m || !m.auto || m.auto.letterName || m.role !== 'war'",
     "replace": "      if (!m || !m.auto || m.role !== 'war'",
     "matches": 1, "needs": "node"},
    {"why": "REG-2980 - a mule he creates as WAR-B is not a war mule",
     "file": "bible.html",
     "find": "    var _wl = /^war[-_]([a-z]{1,2})$/i.exec(v.name); if (_wl) { _nm.role = 'war'; _nm.warN = _vaultLettersN(_wl[1]); }",
     "replace": "    var _wl = null;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2980 - the no-room line asks for WAR1 again",
     "file": "bible.html",
     "find": "      + ' — make a mule named ' + _vaultWarName(1) + ' (then ' + _vaultWarName(2) + '…) for: ' + _wf.map(",
     "replace": "      + ' — make a mule named WAR1 (then WAR2…) for: ' + _wf.map(",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
