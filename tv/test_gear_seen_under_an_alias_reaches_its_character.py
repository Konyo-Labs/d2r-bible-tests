# -*- coding: utf-8 -*-
"""REG-3069 (#36, GrokBot 04:03) - GEAR SEEN UNDER AN ALIAS REACHES ITS CHARACTER.

The gear ledger files a reel's worn items under the name that session read, and the learner merges misread spellings
into one character (char_select.learned names them in each row's `aliases`). The two never met: on the ALT,
gear['konylock'] held Enigma on the torso (WATCHED) and konylock is KonyoLock's top alias, yet KonyoLock's card said
Armor "not seen yet" - and the same for gear['konydress'] beside its character. /api/chars_learned now folds the gear map
through the learner's own aliases (equipped_ledger.fold_aliases): an alias's gear joins its character's key, the alias key
leaves the map, and the character names the spellings it took. Never a guess by name:
  * an alias two characters claim is folded into neither - it stays under its own key, `aliasWhy` saying whose is UNKNOWN;
  * one item seen under two spellings is one item, its looks added (and its tier on the sum);
  * two different items in one slot: the one seen LAST is worn now, the other kept in `alsoSeen`; with a time missing on
    either side the slot is UNKNOWN (item None, `why`), and the card and the window say UNKNOWN with the items each
    spelling saw, never "not seen yet".
RED_PROOF below.
"""
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

import char_select as CS  # noqa: E402
import equipped_ledger as EL  # noqa: E402

PAGE = os.path.join(os.path.dirname(HERE), "bible.html")
BARS = {"proven": 5, "hardened": 10, "wilson": 0.722}
SLOTS = ["helm", "amulet", "weapon", "torso", "off-hand", "gloves", "ring1", "belt", "ring2", "boots"]


def _rec(name, worn, unplaced=(), reels=1, last=None):
    """a gear_by_key record: worn = {slot: (item, sightings, ts)}"""
    rows = []
    for s in SLOTS:
        w = worn.get(s)
        rows.append({"slot": s, "item": w[0] if w else None, "sightings": w[1] if w else 0,
                     "tier": EL._tier_of(w[1], BARS) if w else None, "ts": w[2] if w else None, "reel": "r-" + s if w else None})
    return {"name": name, "slots": rows, "unplaced": [dict(u) for u in unplaced], "reels": reels, "lastTs": last}


def _row(name, key, aliases):
    return {"name": name, "key": key, "aliases": [{"key": a, "name": a, "visits": 3} for a in aliases]}


def _slot(rec, s):
    return [r for r in rec["slots"] if r["slot"] == s][0]


class GearUnderAnAliasReachesItsCharacter(unittest.TestCase):

    def test_the_alts_konylock_enigma_reaches_konyolock(self):
        gear = {"konylock": _rec("Konylock", {"torso": ("Enigma", 3, 2000)}, reels=2, last=2000),
                "konyolock": _rec("KonyoLock", {"helm": ("Shako", 6, 1000)}, reels=4, last=1000),
                "konydress": _rec("Konydress", {"weapon": ("Grief", 2, 1500)}, reels=1, last=1500),
                "frostnova": _rec("Frostnova", {"boots": ("Sandstorm Trek", 1, 900)})}
        chars = [_row("KonyoLock", "konyolock", ["konylock"]), _row("KonyoDress", "konyoress", ["konydress"]),
                 _row("Frostnova", "frostnova", [])]
        out = EL.fold_aliases(gear, chars, BARS)
        self.assertNotIn("konylock", out, "the alias key still holds the gear its character never shows")
        self.assertNotIn("konydress", out)
        kl = out["konyolock"]
        self.assertEqual((_slot(kl, "torso")["item"], _slot(kl, "torso")["tier"]), ("Enigma", "WATCHED"),
                         "KonyoLock's card still says Armor not seen yet beside the Enigma watched on konylock")
        self.assertEqual(_slot(kl, "helm")["item"], "Shako", "the character's own sighting was lost in the fold")
        self.assertEqual(kl["aliases"], ["konylock"])
        self.assertEqual((kl["reels"], kl["lastTs"]), (6, 2000))
        # a character with no key of its own takes its alias's gear whole (KonyoDress was only ever read as Konydress)
        self.assertEqual(_slot(out["konyoress"], "weapon")["item"], "Grief")
        self.assertEqual(out["frostnova"], gear["frostnova"], "a character with no alias was changed")

    def test_an_alias_two_characters_claim_stays_unknown(self):
        gear = {"konylock": _rec("Konylock", {"torso": ("Enigma", 3, 2000)}),
                "konyolock": _rec("KonyoLock", {"helm": ("Shako", 6, 1000)})}
        chars = [_row("KonyoLock", "konyolock", ["konylock"]), _row("Konylocke", "konylocke", ["konylock"])]
        out = EL.fold_aliases(gear, chars, BARS)
        self.assertIn("konylock", out, "a two-owner spelling was folded into one of them by guess")
        self.assertIn("UNKNOWN", out["konylock"].get("aliasWhy", ""))
        self.assertIsNone(_slot(out["konyolock"], "torso")["item"])
        self.assertNotIn("konylocke", out)

    def test_one_item_under_two_spellings_is_one_item(self):
        gear = {"konylock": _rec("Konylock", {"torso": ("Enigma", 3, 2000)}),
                "konyolock": _rec("KonyoLock", {"torso": ("Enigma", 4, 1000)})}
        out = EL.fold_aliases(gear, [_row("KonyoLock", "konyolock", ["konylock"])], BARS)
        t = _slot(out["konyolock"], "torso")
        self.assertEqual((t["item"], t["sightings"], t["tier"], t["ts"]), ("Enigma", 7, "PROVEN", 2000))
        self.assertNotIn("alsoSeen", t)

    def test_two_items_in_one_slot_the_last_seen_is_worn(self):
        gear = {"konylock": _rec("Konylock", {"torso": ("Enigma", 3, 2000)}),
                "konyolock": _rec("KonyoLock", {"torso": ("Chains of Honor", 6, 1000)})}
        out = EL.fold_aliases(gear, [_row("KonyoLock", "konyolock", ["konylock"])], BARS)
        t = _slot(out["konyolock"], "torso")
        self.assertEqual((t["item"], t["sightings"]), ("Enigma", 3))
        self.assertEqual(t["alsoSeen"], [{"item": "Chains of Honor", "sightings": 6, "ts": 1000}])

    def test_two_items_and_a_missing_time_is_unknown(self):
        gear = {"konylock": _rec("Konylock", {"torso": ("Enigma", 3, None)}),
                "konyolock": _rec("KonyoLock", {"torso": ("Chains of Honor", 6, 1000)})}
        out = EL.fold_aliases(gear, [_row("KonyoLock", "konyolock", ["konylock"])], BARS)
        t = _slot(out["konyolock"], "torso")
        self.assertIsNone(t["item"], "a slot two spellings disagree on, one with no time, was decided by guess")
        self.assertIn("UNKNOWN", t["why"])
        self.assertEqual(sorted(a["item"] for a in t["alsoSeen"]), ["Chains of Honor", "Enigma"])

    def test_unplaced_items_are_merged(self):
        gear = {"konylock": _rec("Konylock", {}, unplaced=[{"item": "Annihilus", "sightings": 2, "why": "w", "ts": 5}]),
                "konyolock": _rec("KonyoLock", {}, unplaced=[{"item": "Annihilus", "sightings": 1, "why": "w", "ts": 9}])}
        out = EL.fold_aliases(gear, [_row("KonyoLock", "konyolock", ["konylock"])], BARS)
        self.assertEqual([(u["item"], u["sightings"], u["ts"]) for u in out["konyolock"]["unplaced"]], [("Annihilus", 3, 9)])

    def test_unknown_gear_and_no_roster_pass_through(self):
        self.assertIsNone(EL.fold_aliases(None, [_row("KonyoLock", "konyolock", ["konylock"])], BARS))
        g = {"konylock": _rec("Konylock", {"torso": ("Enigma", 3, 2000)})}
        self.assertEqual(EL.fold_aliases(g, None, BARS), g, "an unreadable roster folded gear by guess")

    def test_the_console_answer_carries_the_fold(self):
        import control_app as CA
        gear = {"konylock": _rec("Konylock", {"torso": ("Enigma", 3, 2000)}),
                "konyolock": _rec("KonyoLock", {"helm": ("Shako", 6, 1000)})}
        saved = {(CS, n): getattr(CS, n) for n in ("load", "learned", "session_view", "surface_witnesses", "lobby_by_size")}
        saved.update({(EL, n): getattr(EL, n) for n in ("load", "gear_by_key")})
        try:
            CS.load = lambda: {"fixture": True}
            CS.learned = lambda d, *a, **k: [_row("KonyoLock", "konyolock", ["konylock"])]
            CS.session_view = lambda d, gd: (None, {})
            CS.surface_witnesses = lambda d: None
            CS.lobby_by_size = lambda d: None
            EL.load = lambda *a, **k: ({"fixture": True}, None)
            EL.gear_by_key = lambda gd, fold, bars: {k: dict(v) for k, v in gear.items()}
            got = CA.chars_learned_answer(full=False)
        finally:
            for (mod, n), f in saved.items():
                setattr(mod, n, f)
        g = got.get("gear") or {}
        self.assertNotIn("konylock", g, "the console's answer still files the Enigma under the alias: %r" % got.get("gearWhy"))
        self.assertEqual(_slot(g["konyolock"], "torso")["item"], "Enigma")


class TheCardSaysUnknownForAnUndecidedSlot(unittest.TestCase):

    def test_the_card_the_window_and_its_sentence_ask_the_one_words(self):
        with open(PAGE, encoding="utf-8") as fh:
            src = fh.read()
        code = re.sub(r"/\*.{0,4000}?\*/", " ", src, flags=re.S)
        self.assertEqual(code.count("function _gearWhy(s){"), 1, "the one UNKNOWN sentence is gone - re-point this law")
        for what, call in (("the card's row", "esc(_gearWhy(s)) + '</span></li>';"),
                           ("the window's sentence", "if (!row.item && row.why) return word + ' · ' + esc(_gearWhy(row));"),
                           ("the doll's slot", "say: word + ' · ' + (s.why ? _gearWhy(s) : 'not seen yet')"),
                           ("the doll's slot state", ": (s && s.why) ? ' data-state=\"unknown\"' : ' data-state=\"unseen\"')")):
            self.assertEqual(code.count(call), 1, "%s no longer says UNKNOWN for a slot two spellings disagree on" % what)


RED_PROOF = [
    {"why": "REG-3069 - the console no longer folds the gear map through the learner's aliases",
     "file": "control_app.py",
     "find": "                out[\"gear\"] = _el.fold_aliases(out[\"gear\"], out[\"chars\"], _cs.tier_bars())\n",
     "replace": "                pass\n",
     "matches": 1},
    {"why": "REG-3069 - an alias two characters claim is folded into the first of them by guess",
     "file": "equipped_ledger.py",
     "find": "        if len(ks) != 1:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3069 - two items in one slot take the first spelling's, not the one seen last",
     "file": "equipped_ledger.py",
     "find": "        items.sort(key=lambda e: e[\"ts\"], reverse=True)\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "REG-3069 - a slot with a missing time is decided anyway",
     "file": "equipped_ledger.py",
     "find": "        if any(e[\"ts\"] is None for e in items):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3069 - the same item under two spellings keeps only one spelling's looks",
     "file": "equipped_ledger.py",
     "find": "            e[\"sightings\"] += int(c.get(\"sightings\") or 0)\n",
     "replace": "            e[\"sightings\"] = int(c.get(\"sightings\") or 0)\n",
     "matches": 1},
    {"why": "REG-3069 - the window's sentence says 'not seen yet' for a slot two spellings disagree on",
     "file": "bible.html",
     "find": "    if (!row.item && row.why) return word + ' · ' + esc(_gearWhy(row));\n",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
