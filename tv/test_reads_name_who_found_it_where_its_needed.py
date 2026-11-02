# -*- coding: utf-8 -*-
"""v3855 - THE READS' IDENTITY IS ROUTED TO WHERE IT IS NEEDED (Elad pt1198u, 2026-11-02).

read_identity (who_at / attribute_finds) feeds three consumers, answer only, with how it is known in the hover:
  1. the Characters room / builder: per character its sessions, last level, played and AFK time, Baal leveling vs
     farming runs (shadow_sessions.characters_rollup, on /api/chars_learned `identity` and the shadow digest);
  2. the Vault hover card: which character found or stashed the item, in which game (read_identity.finds_index);
  3. the uniques / grail ledger and chronicles: the same attribution, which never adds, drops or counts an item.
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
    i = src.index("  function _idHours(ms)")
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


class TheCharactersRoomSaysEachCharactersSessions(unittest.TestCase):

    def test_rollup_counts_sessions_level_and_runs(self):
        c = SS.characters_rollup(ID._journal())
        self.assertEqual(list(c), ["Blizzy"], "a session nobody named was counted under a guessed name")
        b = c["Blizzy"]
        self.assertEqual((b["sessions"], b["level"], b["cls"], b["farming"], b["leveling"]), (2, 92, "Sorceress", 2, 0))

    def test_the_room_line_is_the_answer_and_unknown_when_unseen(self):
        idt = {"characters": {"Blizzy": {"sessions": 3, "level": 92, "playMs": 2 * 3600000, "afkMs": 600000,
                                         "leveling": 1, "farming": 2}}}
        got = _run_js("[window._identityCharLine('blizzy', %s), window._identityCharLine('Hammy', %s),"
                      " window._identityCharLine('Blizzy', null)]" % (json.dumps(idt), json.dumps(idt)))
        self.assertEqual(got[0]["say"], "3 sessions · last seen level 92 · 2h played · 10m AFK · 1 leveling (Baal) · 2 farming")
        self.assertEqual(got[1]["say"], "sessions UNKNOWN")
        self.assertIsNone(got[2], "no console answered, yet the room drew a line")

    def test_the_room_draws_it(self):
        src = open(BIBLE, encoding="utf-8").read()
        self.assertIn("      + _idLine(t);\n", src)
        self.assertIn('<div class="chx-idt" title="\' + esc(r.hover) + \'">\' + esc(r.say) + \'</div>', src)


def _tip_js():
    src = open(BIBLE, encoding="utf-8").read()
    i = src.index("function _identityTipLine(nm, el){")
    return src[i:src.index("\n}\n", i) + 3]


IDT = {"finds": {"Shako": {"character": "Blizzy", "cls": "Sorceress", "level": 92, "game": "Morph3",
                           "sessionId": "s_1", "ts": 1, "sources": ["select-screen"], "conflict": None},
                 "Arachnid Mesh": {"character": None, "cls": None, "level": None, "game": None, "sessionId": "s_2",
                                   "ts": 2, "sources": [], "conflict": ["Blizzy", "Hammy"]}}}


def _tip(name, in_vault):
    call = ("_identityTipLine(%s, {closest: function(){ return %s; }})" % (json.dumps(name), "true" if in_vault else "null"))
    return _run_js("(function(){ const _l = window._identityFoundBy; window._identityFoundBy = function(n){ return _l(n, %s); };"
                   " %s\n return %s; })()" % (json.dumps(IDT), _tip_js(), call))


class TheVaultCardSaysWhoFoundIt(unittest.TestCase):

    def test_finds_index_names_character_game_and_session(self):
        f = RI.finds_index(ID._journal())["Shako"]
        self.assertEqual((f["character"], f["cls"], f["level"], f["game"], f["sessionId"]),
                         ("Blizzy", "Sorceress", 92, "Morph7", ID.S1))
        self.assertNotIn(ID.SECRET, json.dumps(RI.finds_index(ID._journal())))

    def test_the_card_line_is_the_answer(self):
        h = _tip("Shako", True)
        self.assertIn(">found by Blizzy · Sorceress 92 · Morph3</div>", h)
        self.assertIn('title="sources: select-screen · session s_1"', h)

    def test_unattributed_in_the_vault_is_unknown(self):
        self.assertIn(">found by UNKNOWN</div>", _tip("Arachnid Mesh", True))
        self.assertIn("the reads disagree: Blizzy vs Hammy", _tip("Arachnid Mesh", True))
        self.assertIn(">found by UNKNOWN</div>", _tip("Griffon's Eye", True))

    def test_the_card_draws_it(self):
        src = open(BIBLE, encoding="utf-8").read()
        self.assertIn("      desc.innerHTML = r.desc + _identityTipLine(nm, el);", src)


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
    {"why": "a Morph run is not counted as farming",
     "file": "tv/shadow_sessions.py",
     "find": "        o[\"farming\"] += 1 if sc.startswith(\"Farming\") else 0\n",
     "replace": "",
     "matches": 1},
    {"why": "an older session's level overwrites the newest",
     "file": "tv/shadow_sessions.py",
     "find": "        if t1 >= o[\"lastT\"]:\n",
     "replace": "        if True:\n",
     "matches": 1},
    {"why": "a character no read named shows a line of zeros instead of UNKNOWN",
     "file": "bible.html",
     "find": "    if (!c) return { say: 'sessions UNKNOWN',",
     "replace": "    if (!c) c = { sessions: 0, playMs: 0, afkMs: 0 }; if (!c) return { say: 'sessions UNKNOWN',",
     "matches": 1, "needs": "node"},
    {"why": "the Characters room never draws the line",
     "file": "bible.html",
     "find": "      + _idLine(t);\n",
     "replace": ";\n",
     "matches": 1},
    {"why": "the Vault card never says who found the item",
     "file": "bible.html",
     "find": "      desc.innerHTML = r.desc + _identityTipLine(nm, el);",
     "replace": "      desc.innerHTML = r.desc;",
     "matches": 1},
    {"why": "a find takes the first game of the session instead of the one being played",
     "file": "tv/read_identity.py",
     "find": "            if best is None or r[\"ts\"] >= best[\"ts\"]:\n",
     "replace": "            if best is None:\n",
     "matches": 1},
    {"why": "a Vault item nobody named draws no line instead of UNKNOWN",
     "file": "bible.html",
     "find": "  if (!inVault && f.say === 'found by UNKNOWN') return '';\n",
     "replace": "  if (f.say === 'found by UNKNOWN') return '';\n",
     "matches": 1, "needs": "node"},
    {"why": "disagreeing reads are attributed to one of them",
     "file": "bible.html",
     "find": "    if (!f || !f.character) {\n",
     "replace": "    if (f && !f.character && f.conflict) f = Object.assign({}, f, { character: f.conflict[0] });\n    if (!f || !f.character) {\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main()
