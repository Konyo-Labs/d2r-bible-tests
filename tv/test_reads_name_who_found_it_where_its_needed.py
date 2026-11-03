# -*- coding: utf-8 -*-
"""v3855 - THE READS' IDENTITY IS ROUTED TO WHERE IT IS NEEDED (Elad pt1198u, 2026-11-02).

read_identity (who_at / attribute_finds) feeds three consumers, answer only, with how it is known in the hover:
  1. NOT the Characters room (Elad 2026-11-02): its cards are each character's EQUIPPED items from in-game reads only
     (synced as its worn, locked items) - no identity stats, no finds;
     the data stays on the session rows and in /api/chars_learned `identity`.
  2. the Vault's evidence panel only: "found by <character> · <game>" or UNKNOWN (read_identity.finds_index).
     Elad 2026-11-02: the Vault is ONE per-account vault - attribution is evidence, never routing, sorting, filing,
     a mule choice or whether an item is stashed. Uniques / grail and chronicles are per account: no attribution.
Unattributed says UNKNOWN. Never a password. RED_PROOF below.
"""
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import test_a_read_names_its_character_and_game_never_the_password as ID  # noqa: E402
import test_a_shadow_shelf_says_playtime_and_plays_served_frames as BASE  # noqa: E402
import read_identity as RI  # noqa: E402
import shadow_sessions as SS  # noqa: E402
import sys as _sys; _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from console_safe import enable; enable()

BIBLE = os.path.join(HERE, "..", "bible.html")


def _bible_identity_js():
    src = open(BIBLE, encoding="utf-8").read()
    i = src.index("  function _idOf(){")
    j = src.index("  window._identityFoundBy = function", i)
    j = src.index("\n  };\n", j) + len("\n  };\n")
    return src[i:j]


def _run_js(call):
    js = ("const window = {}; let _cbLearned = null;"
          " function _cbFold(n){ return String(n || '').toLowerCase().replace(/[^a-z0-9]/g, ''); }\n"
          + _bible_identity_js() + "\nprocess.stdout.write(JSON.stringify(" + call + "));")
    r = subprocess.run([BASE.NODE or "node", "-"], input=js, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-600:])
    return json.loads(r.stdout)


class TheCharactersRoomCarriesNoIdentity(unittest.TestCase):

    def test_the_cards_draw_no_stats_and_no_finds(self):
        src = open(BIBLE, encoding="utf-8").read()
        i = src.index("  function _proof(t){")
        room = src[i:src.index("  function _surfaceWitnessHtml(){", i)]
        for w in ("_identity", "_idFinds", "_idLine", "chx-idt", "chx-finds", "AFK", " played"):
            self.assertNotIn(w, room, "a Characters card carries identity (%s)" % w)
        self.assertNotIn("_identityChar", src)

    def test_the_rollup_carries_no_finds(self):
        c = SS.characters_rollup(ID._journal())
        self.assertNotIn("finds", json.dumps(c), "per-character finds came back (Elad: not on the Characters tab)")


def _found_js():
    src = open(BIBLE, encoding="utf-8").read()
    i = src.index("  window._vaultFoundByHtml = function(name){")
    return src[i:src.index("\n  };\n", i) + 5]


IDT = {"finds": {"Shako": {"character": "Blizzy", "cls": "Sorceress", "level": 92, "game": "Morph3",
                           "sessionId": "s_1", "ts": 1, "sources": ["select-screen"], "conflict": None},
                 "Arachnid Mesh": {"character": None, "cls": None, "level": None, "game": None, "sessionId": "s_2",
                                   "ts": 2, "sources": [], "conflict": ["Blizzy", "Hammy"]}}}


def _panel(name):
    return _run_js("(function(){ const _l = window._identityFoundBy; window._identityFoundBy = function(n){ return _l(n, %s); };"
                   " function _evEsc(t){ return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\"/g, '&quot;'); }\n"
                   "%s\n return window._vaultFoundByHtml(%s); })()" % (json.dumps(IDT), _found_js(), json.dumps(name)))


class TheVaultEvidenceSaysWhoFoundIt(unittest.TestCase):

    def test_finds_index_names_character_game_and_session(self):
        f = RI.finds_index(ID._journal())["Shako"]
        self.assertEqual((f["character"], f["cls"], f["level"], f["game"], f["sessionId"]),
                         ("Blizzy", "Sorceress", 92, "Morph7", ID.S1))
        self.assertNotIn(ID.SECRET, json.dumps(RI.finds_index(ID._journal())))

    def test_the_panel_line_is_the_answer(self):
        h = _panel("Shako")
        self.assertIn(">found by Blizzy · Sorceress 92 · Morph3</div>", h)
        self.assertIn('title="sources: select-screen · session s_1"', h)

    def test_unattributed_is_unknown(self):
        self.assertIn(">found by UNKNOWN</div>", _panel("Arachnid Mesh"))
        self.assertIn("the reads disagree: Blizzy vs Hammy", _panel("Arachnid Mesh"))
        self.assertIn(">found by UNKNOWN</div>", _panel("Griffon's Eye"))

    def test_the_panel_draws_it(self):
        src = open(BIBLE, encoding="utf-8").read()
        self.assertEqual(src.count("window._vaultFoundByHtml(m.name)"), 1)


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

class AttributionNeverRoutesTheVault(unittest.TestCase):
    """His ruling: an item's mule / home is identical with and without attribution data. Only two places in the page
    may ask who found an item: the evidence panel's line. A new reader anywhere else (the sorter, the
    dock, the records, the grail or chronicle tallies) fails here."""

    def test_only_the_evidence_panel_reads_who_found_it(self):
        src = open(BIBLE, encoding="utf-8").read()
        self.assertEqual(src.count("_identityFoundBy("), 1, "something besides the evidence panel reads who found an item")
        self.assertEqual(src.count("_vaultFoundByHtml("), 1)
        for fn in ("window.vaultAutoAssign = function(){", "window.vaultAutoSortByHand = function(){", "function _vaultRecords(_inPhase){"):
            body = _fn_body(src, fn)
            for w in ("_identity", "finds_index", "foundBy"):
                self.assertNotIn(w, body, "%s reads the attribution (%s)" % (fn, w))

    def test_no_grail_or_chronicle_attribution(self):
        src = open(BIBLE, encoding="utf-8").read()
        self.assertNotIn("_identityTipLine", src, "uniques / chronicles are per account; they carry no character")


class TheProofsNameOnePlace(unittest.TestCase):

    def test_each_find_matches_once(self):
        for proof in RED_PROOF:
            src = open(os.path.join(HERE, "..", proof["file"]), encoding="utf-8").read()
            self.assertEqual(src.count(proof["find"]), proof["matches"], proof["why"])


RED_PROOF = [
    {"why": "a Characters card draws who found what",
     "file": "bible.html",
     "find": "      + _gearHtml(t)\n",
     "replace": "      + _gearHtml(t) + (window._identityFoundBy ? '<i>' + window._identityFoundBy(t.name).say + '</i>' : '')\n",
     "matches": 1},
    {"why": "per-character finds are rolled up again",
     "file": "tv/shadow_sessions.py",
     "find": "        o[\"sessions\"] += 1\n",
     "replace": "        o[\"sessions\"] += 1\n        o.setdefault(\"finds\", {})\n",
     "matches": 1},
    {"why": "the Vault's evidence panel never says who found the item",
     "file": "bible.html",
     "find": "    try { var _fb = window._vaultFoundByHtml(m.name);",
     "replace": "    try { var _fb = '';",
     "matches": 1},
    {"why": "a find takes the first game of the session instead of the one being played",
     "file": "tv/read_identity.py",
     "find": "            if best is None or r[\"ts\"] >= best[\"ts\"]:\n",
     "replace": "            if best is None:\n",
     "matches": 1},
    {"why": "disagreeing reads are attributed to one of them",
     "file": "bible.html",
     "find": "    if (!f || !f.character) {\n",
     "replace": "    if (f && !f.character && f.conflict) f = Object.assign({}, f, { character: f.conflict[0] });\n    if (!f || !f.character) {\n",
     "matches": 1, "needs": "node"},
    {"why": "the mule sorter files by who found the item",
     "file": "bible.html",
     "find": "window.vaultAutoAssign = function(){\n",
     "replace": "window.vaultAutoAssign = function(){ var _who = window._identityFoundBy && window._identityFoundBy('x');\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
