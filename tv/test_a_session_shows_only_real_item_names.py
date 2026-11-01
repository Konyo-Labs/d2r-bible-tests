# -*- coding: utf-8 -*-
"""v3850 (Elad 2026-11-01 02:40 IDT, the shadow Shelf of Dean's sessions) - A SESSION SHOWS REAL ITEM NAMES OR NOTHING.

Seen: "Resu rrected", "SKULL TauCH", "GArnE' -rz 96", "You have joined channel: Lobby", "STASH" printed as the names a
run saw - raw OCR carried as item names. farmed_names.snap is the one rule: a read word snaps to a known D2 name from
item_tables.json (exact, then case/space-blind, then a close fuzzy match) or it is dropped; UI words and NPC names
(SB-1: Deckard Cain, Tyrael, Stash) are never items. shadow_sessions.digest asks it for every session it publishes and
viewed_sessions asks it for an owner whose older console published raw words.

RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import farmed_names as F  # noqa: E402
import shadow_sessions as SS  # noqa: E402

RED_PROOF = [
    {"why": "a word that matches no item is shown as it was read",
     "file": "farmed_names.py",
     "find": "    if best is None:\n        return None\n",
     "replace": "    if best is None:\n        return (raw, \"bases\")\n",
     "matches": 1},
    {"why": "UI and NPC words pass as items again",
     "file": "farmed_names.py",
     "find": "        _NEVER = set(_norm(w) for w in tuple(SESSION_UI_WORDS) + tuple(extra))\n",
     "replace": "        _NEVER = set()\n",
     "matches": 1},
    {"why": "the session rule stops reading the vault's one denylist (NPCs and panel words pass)",
     "file": "farmed_names.py",
     "find": "        return re.findall(r\"'([^']+)'\\s*:\", body)\n",
     "replace": "        return []\n",
     "matches": 1},
    {"why": "OCR near-misses are no longer snapped to the real name",
     "file": "farmed_names.py",
     "find": "    cands = difflib.get_close_matches(letters, list(tab.keys()), n=3, cutoff=SNAP_RATIO)\n",
     "replace": "    cands = []\n",
     "matches": 1},
    {"why": "the published digest carries raw read words again",
     "file": "shadow_sessions.py",
     "find": "        names = _FN.clean([n for r in reads for n in _names(r)])\n",
     "replace": "        names = list(dict.fromkeys(n for r in reads for n in _names(r)))\n",
     "matches": 1},
    {"why": "an older owner's raw words reach the viewer's card unsnapped",
     "file": "shadow_sessions.py",
     "find": "            s[\"names\"] = _FN.clean(raw)\n",
     "replace": "            s[\"names\"] = raw\n",
     "matches": 1},
]

SEEN_JUNK = ["Resu rrected", "SKULL TauCH", "GArnE' -rz 96", "You have joined channel: Lobby", "Lobby", "STASH",
             "Diablo II: Resurrected", "HAILSTaNE HAND", "SakCEkEss", "EVEL 92", "Deckard Cain", "Tyrael", "Stash"]


class SnapOrDrop(unittest.TestCase):
    def test_the_words_seen_on_deans_cards_are_dropped(self):
        for w in SEEN_JUNK:
            self.assertIsNone(F.snap(w), "shown as an item: %r -> %r" % (w, F.snap(w)))

    def test_real_names_keep_their_spelling(self):
        for w, want in (("Large Axe", "Large Axe"), ("Harlequin Crest", "Harlequin Crest"), ("Grief", "Grief"),
                        ("ber rune", "Ber Rune"), ("GRAND CHARM", "Grand Charm")):
            self.assertEqual(F.snap(w)[0], want)

    def test_an_ocr_near_miss_snaps_to_the_real_name(self):
        self.assertEqual(F.snap("Harlequn Crest")[0], "Harlequin Crest")
        self.assertEqual(F.snap("Stormshie1d")[0], "Stormshield")

    def test_a_short_garble_is_never_guessed(self):
        self.assertIsNone(F.snap("Bxr"))


class OneDenylist(unittest.TestCase):
    def test_every_word_the_vault_refuses_a_session_refuses(self):
        words = F.vault_denylist()
        self.assertGreaterEqual(len(words), 30, "bible.html _NOT_ITEMS was not read")
        for w in words:
            self.assertIsNone(F.snap(w), "the vault refuses %r and a session shows it" % w)
        for real in ("Tyrael's Might", "Gheed's Fortune"):
            self.assertEqual(F.snap(real)[0], real)

    def test_no_second_npc_list_here(self):
        for npc in ("tyrael", "deckard cain", "akara", "stash"):
            self.assertNotIn(npc, F.SESSION_UI_WORDS, "a copy of the vault's denylist: %r" % npc)


class EveryCardAsksIt(unittest.TestCase):
    def test_the_digest_publishes_snapped_names(self):
        rows = [{"t": 1792000000000 + i * 1000, "frameId": "f%d" % i, "names": n}
                for i, n in enumerate([["Resu rrected", "Harlequn Crest"], ["STASH", "Lobby"]])]
        d = SS.digest(rows, "/nonexistent", lambda r: True, 1792000100000, make=lambda a, b: False)
        self.assertEqual(d["sessions"][0]["names"], ["Harlequin Crest"])

    def test_an_older_owners_raw_words_are_snapped_for_the_viewer(self):
        out = SS.viewed_sessions([{"names": ["SKULL TauCH", "Harlequn Crest", "Lobby"], "namesMore": 145}])
        self.assertEqual(out[0]["names"], ["Harlequin Crest"])
        self.assertIsNone(out[0]["namesMore"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
