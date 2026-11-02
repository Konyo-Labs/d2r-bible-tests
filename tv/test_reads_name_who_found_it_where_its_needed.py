# -*- coding: utf-8 -*-
"""v3855 - THE READS' IDENTITY IS ROUTED TO WHERE IT IS NEEDED (Elad pt1198u, 2026-11-02).

read_identity (who_at / attribute_finds) feeds three consumers, answer only, with how it is known in the hover:
  1. the Characters room: per character ONLY its Finds - the items it found, farmed or stashed, grouped like the
     session farmed summary, notable first, count on the card, where in the hover (shadow_sessions.characters_rollup
     on /api/chars_learned `identity`). No sessions / level / played / AFK text there (Elad: session rows only);
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


def _card_js():
    src = open(BIBLE, encoding="utf-8").read()
    i = src.index("  function _idFinds(t){")
    return src[i:src.index("\n  }\n", i) + 4]


class TheCharactersRoomShowsOnlyItsFinds(unittest.TestCase):

    def _journal(self):
        rows = ID._journal()
        rows.append(ID._r(9 * 60000, scene="stash", names=["Shako", "Ber Rune", "Super Healing Potion", "Gold"]))
        rows.append(ID._r(10 * 60000, scene="gameplay", intent="farmed", names=["El Rune"]))
        return rows

    def test_rollup_carries_the_characters_finds(self):
        c = SS.characters_rollup(self._journal())
        self.assertEqual(list(c), ["Blizzy"], "a session nobody named was counted under a guessed name")
        f = c["Blizzy"]["finds"]
        blob = json.dumps(f)
        self.assertIn("Shako", blob)
        for junk in ("Potion", "Gold"):
            self.assertNotIn(junk, blob, "a consumable counted as a find")
        self.assertNotIn(ID.SECRET, blob)

    def _card(self, idt):
        return _run_js("(function(){ const _w = window._identityCharFinds;"
                       " window._identityCharFinds = function(n){ return _w(n, %s); };"
                       " function esc(t){ return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\"/g, '&quot;'); }\n"
                       "%s\n return _idFinds({name: 'Blizzy'}); })()" % (json.dumps(idt), _card_js()))

    def test_the_card_says_finds_notable_first_and_where_in_the_hover(self):
        idt = {"characters": {"Blizzy": {"sessions": 3, "level": 92, "playMs": 7200000, "afkMs": 600000, "leveling": 1,
                                         "farming": 2, "finds": {
            "runes": {"El Rune": {"count": 4, "where": ["Morph2"]}, "Ber Rune": {"count": 1, "where": ["Morph5"]}},
            "uniques": {"Shako": {"count": 2, "where": ["Morph3", "Morph4"]}}}}}}
        h = self._card(idt)
        shown = re.sub(r' title="[^"]*"', '', h)
        self.assertLess(shown.index("Shako"), shown.index("Ber Rune"))
        self.assertLess(shown.index("Ber Rune"), shown.index("El Rune"), "a low rune sorted above a high rune")
        self.assertIn("Shako \u00d72", shown)
        self.assertIn('title="found in Morph3, Morph4"', h)
        for word in ("session", "AFK", "played", "level", "Morph"):
            self.assertNotIn(word, shown, "the card shows %r (it belongs on the session rows / in the hover)" % word)

    def test_no_attributed_reads_is_unknown_and_no_console_draws_nothing(self):
        self.assertIn(">Finds UNKNOWN<", self._card({"characters": {}}))
        self.assertEqual(_run_js("window._identityCharFinds('Blizzy', null)"), None)

    def test_long_lists_fold(self):
        u = {"U%d" % i: {"count": 1, "where": []} for i in range(10)}
        self.assertIn("<details", self._card({"characters": {"Blizzy": {"finds": {"uniques": u}}}}))

    def test_the_room_draws_it_and_not_the_stats(self):
        src = open(BIBLE, encoding="utf-8").read()
        self.assertIn("      + _idFinds(t);\n", src)
        self.assertNotIn("_identityCharLine", src)


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


class AttributionNeverRoutesTheVault(unittest.TestCase):
    """His ruling: an item's mule / home is identical with and without attribution data. Only two places in the page
    may ask who found an item: the evidence panel's line. A new reader anywhere else (the sorter, the
    dock, the records, the grail or chronicle tallies) fails here."""

    def test_only_the_evidence_panel_reads_who_found_it(self):
        src = open(BIBLE, encoding="utf-8").read()
        self.assertEqual(src.count("_identityFoundBy("), 1, "something besides the evidence panel reads who found an item")
        self.assertEqual(src.count("_vaultFoundByHtml("), 1)
        for fn in ("window.vaultAutoAssign = function(){", "window.vaultAutoSortByHand = function(){", "function _vaultRecords(_inPhase){"):
            i = src.index(fn)
            body = src[i:i + 12000]
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
    {"why": "a session nobody named is counted under a character",
     "file": "tv/shadow_sessions.py",
     "find": "        name = (ch or {}).get(\"name\")\n        if not name:\n            continue\n",
     "replace": "        name = (ch or {}).get(\"name\") or \"UNKNOWN\"\n",
     "matches": 1},
    {"why": "potions and gold count as a character's finds",
     "file": "tv/shadow_sessions.py",
     "find": "        for _grp, _rows in _FN.group(",
     "replace": "        for _grp, _rows in (lambda x: {'uniques': [[n, 1] for w in x for n in w]})(",
     "matches": 1},
    {"why": "a high rune is not shown with the notable finds",
     "file": "bible.html",
     "find": "        if (hi.length) top.push({ g: 'High runes', notable: true, items: hi });\n",
     "replace": "        if (hi.length) rest.push({ g: 'High runes', notable: false, items: hi });\n",
     "matches": 1, "needs": "node"},
    {"why": "a character with no attributed reads shows nothing instead of UNKNOWN",
     "file": "bible.html",
     "find": "    if (r.state !== 'seen') return '<div class=\"chx-finds\" data-state=\"unknown\">Finds UNKNOWN</div>';\n",
     "replace": "    if (r.state !== 'seen') return '';\n",
     "matches": 1, "needs": "node"},
    {"why": "the card shows where on its face instead of in the hover",
     "file": "bible.html",
     "find": "          + esc(x.n) + (x.c > 1 ?",
     "replace": "          + esc(x.n + ' ' + x.where.join(' ')) + (x.c > 1 ?",
     "matches": 1, "needs": "node"},
    {"why": "the Characters room never draws the finds",
     "file": "bible.html",
     "find": "      + _idFinds(t);\n",
     "replace": ";\n",
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
