# -*- coding: utf-8 -*-
"""#91 - ONE ART PER MONSTER: A BOSS OR SUPER-UNIQUE WITH A SPRITE IS NEVER FILED AS SPRITELESS, AND TWO MONSTERS NEVER
SHARE ONE PICTURE UNLESS THE RECORD SAYS WHY (v3899, REG-3961 / REG-3962, GrokBot on a grok/ branch).

His card #91: on UNIQUES and the Boss cards, no boss or super-unique shows NO picture, and none shows the SAME picture as a
different monster. tv/data/monster_art_fandom.json filed Bloodwitch the Wild, Lord De Seis, Treehead WoodFist and The
Countess under noSpriteFound ("no sprite on either source"), but rankedboost has all four - the misses were the CASE of a
file name ('Lord de Seis.gif', 'Treehead Woodfist.gif', 'Blood Witch the Wild.gif'). Each was downloaded and opened before
it entered art/. And Pindleskin's sprite is byte-for-byte Bonesaw Breaker's (rankedboost serves one GIF for both - both are
Reanimated Horde): that pair is now DECLARED in sharedSprite with its reason, and any OTHER pair of monsters whose files
hold the same bytes turns this red.

The Countess's Boss card and The Summoner's are pinned in art/boss_portraits.manifest.json "_ready_to_wire" (opened, sha256
pinned) so wiring BOSS_PORTRAIT is one edit in bible.html; art/verify_boss_portraits.py hashes those rows like any portrait.
RED_PROOF below.
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REC = os.path.join(HERE, "data", "monster_art_fandom.json")
MANIFEST = os.path.join(ROOT, "art", "boss_portraits.manifest.json")

#: the four the record wrongly filed as spriteless (v3899 #91). A premise, not a census: each must carry its own sprite.
FOUND_V3899 = ("The Countess", "Bloodwitch the Wild", "Lord De Seis", "Treehead WoodFist")


def _rec():
    with io.open(REC, encoding="utf-8") as fh:
        return json.load(fh)


def _sha1(path):
    with open(path, "rb") as fh:
        return hashlib.sha1(fh.read()).hexdigest()


class OneArtPerMonster(unittest.TestCase):

    def test_a_monster_with_a_sprite_is_never_filed_as_spriteless(self):
        rec = _rec()
        named = set(r["name"] for r in rec["sprites"])
        both = sorted(named & set(rec.get("noSpriteFound") or []))
        self.assertEqual(both, [], "filed as 'no sprite found' while the record ships a sprite for it: %s" % both)

    def test_the_four_case_misses_wear_their_own_sprite(self):
        by = dict((r["name"], r) for r in _rec()["sprites"])
        missing = [n for n in FOUND_V3899 if n not in by]
        self.assertEqual(missing, [], "a boss or super-unique the sources DO draw has no sprite record: %s" % missing)
        for n in FOUND_V3899:
            r = by[n]
            self.assertTrue(os.path.isfile(os.path.join(ROOT, r["file"])), "%s's sprite is not in art/" % n)
            self.assertTrue(r.get("depicts"), "%s's sprite says nothing about what was SEEN when it was opened" % n)

    def test_every_sprite_is_the_bytes_that_were_opened(self):
        bad = []
        for r in _rec()["sprites"]:
            p = os.path.join(ROOT, r["file"])
            if not os.path.isfile(p):
                bad.append("%s: %s is not in art/" % (r["name"], r["file"]))
                continue
            if _sha1(p) != r.get("sha1") or os.path.getsize(p) != r.get("bytes"):
                bad.append("%s: %s is not the file its record names (sha1/bytes)" % (r["name"], r["file"]))
        self.assertEqual(bad, [], "\n".join(bad))

    def test_two_monsters_share_a_picture_only_when_the_record_says_why(self):
        rec = _rec()
        groups = {}
        for r in rec["sprites"]:
            p = os.path.join(ROOT, r["file"])
            if os.path.isfile(p):
                groups.setdefault(_sha1(p), set()).add(r["name"])
        shared = [g for g in groups.values() if len(g) > 1]
        declared = [set(d.get("names") or []) for d in rec.get("sharedSprite") or []]
        for d in rec.get("sharedSprite") or []:
            self.assertTrue(len(d.get("why") or "") > 40, "a declared shared sprite gives no reason: %r" % d.get("names"))
        undeclared = sorted(sorted(g) for g in shared if g not in declared)
        self.assertEqual(undeclared, [], "two monsters draw one picture and nothing says why: %s" % undeclared)
        stale = sorted(sorted(d) for d in declared if d not in shared)
        self.assertEqual(stale, [], "a declared shared sprite no longer shares (drop the declaration): %s" % stale)

    def test_the_boss_portraits_still_verify_with_the_ready_rows_pinned(self):
        with io.open(MANIFEST, encoding="utf-8") as fh:
            man = json.load(fh)
        ready = (man.get("_ready_to_wire") or {}).get("rows") or []
        self.assertIn("countess", [r["bossId"] for r in ready], "PREMISE: the Countess's opened sprite is not pinned")
        p = subprocess.run([sys.executable, os.path.join(ROOT, "art", "verify_boss_portraits.py")],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
        self.assertEqual(p.returncode, 0, "art/verify_boss_portraits.py went red:\n" + p.stdout)
        self.assertIn("+%d opened and ready to wire" % len(ready), p.stdout, "the verifier did not hash the ready rows")


RED_PROOF = [
    {"why": "#91 - The Countess is filed as spriteless again while art/ ships her sprite",
     "file": "tv/data/monster_art_fandom.json",
     "find": "\"noSpriteFound\": [\n  \"Hell Bovine\"\n ]",
     "replace": "\"noSpriteFound\": [\n  \"The Countess\",\n  \"Hell Bovine\"\n ]",
     "matches": 1},
    {"why": "#91 - Lord De Seis loses his sprite record (the old 'no sprite on either source' case miss)",
     "file": "tv/data/monster_art_fandom.json",
     "find": "\"name\": \"Lord De Seis\",",
     "replace": "\"name\": \"Lord de Seis (renamed)\",",
     "matches": 1},
    {"why": "#91 - the Countess's record no longer names the bytes that were opened",
     "file": "tv/data/monster_art_fandom.json",
     "find": "\"sha1\": \"5329480a384029cb9a0db637978f173379918928\"",
     "replace": "\"sha1\": \"0000000000000000000000000000000000000000\"",
     "matches": 1},
    {"why": "#91 - Pindleskin and Bonesaw Breaker share one picture and nothing says why",
     "file": "tv/data/monster_art_fandom.json",
     "find": "\"names\": [\n    \"Pindleskin\",\n    \"Bonesaw Breaker\"\n   ],",
     "replace": "\"names\": [\n    \"Pindleskin\"\n   ],",
     "matches": 1},
    {"why": "#91 - the Countess's ready-to-wire portrait is not the file that was opened (the verifier must hash it)",
     "file": "art/boss_portraits.manifest.json",
     "find": "\"sha256\": \"75f1a1cf6a59b0251719ae9423af5bad22aa84b73f4d92ae4c8da934376deaab\"",
     "replace": "\"sha256\": \"0000000000000000000000000000000000000000000000000000000000000000\"",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
