# -*- coding: utf-8 -*-
"""v2787 — THE SET PIECES CARRY A REAL QUALITY LEVEL, FROM THE GAME'S OWN TABLE.

Before this, 1,444 of 1,598 set-tier drop records carried `qlvl: 0`. A zero on a MISSING row is a
number he farms by — it says "any monster level can drop this" — and it was not measured, it was
absent. The qlvl check is one of the two filters that decide whether an item can drop at all
(`monster mlvl >= item qlvl`), so a wrong zero sends him to the wrong zone.

=== WHERE THE NUMBERS CAME FROM, AND WHY THE DATA IS NOT IN THIS REPO ===
Extracted from his local D2R CASC store: `data\\global\\excel\\setitems.txt`, column `lvl`,
joined on column `index`. Cross-checked against `data\\global\\excel\\base\\setitems.txt` —
132 pieces in both, ZERO disagreements. Full trace, hashes and the reproduction command are in
`SET_QLVL_PROVENANCE.md`. **The game table itself is Blizzard's and this repo is PUBLIC, so it is
deliberately absent** — which is exactly why the laws below pin the SHAPE of the data rather than
its values.

=== ⚠ THESE LAWS CANNOT COMPARE AGAINST THE SOURCE, SO THEY PIN WHAT THE SOURCE IMPLIES ===
Measured across all 35 sets in the game table: **every piece of a set carries the same qlvl, with
zero exceptions.** That is a property of the data that survives without the data. A partial or
corrupted fill breaks it immediately, and no Blizzard bytes are needed to check it.

=== ⚠ ELEVEN PIECES ARE STILL 0 AND THAT IS CORRECT ===
They have no row in the game table under any spelling. Some are probably NAMING ERRORS IN THE BIBLE
(the table says `Tal Rasha's Fire-Spun Cloth`, the bible says `Fine-Spun Cloth`), and a near-
spelling is not a trace. Guessing one would be the fabrication his rule forbids.
[[unknown-stays-unknown]]
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")

try:
    from console_safe import enable
    enable()
except Exception:
    pass

SRC = io.open(BIBLE, encoding="utf-8").read()
REC = re.compile(r'\{"n":"((?:[^"\\]|\\.)*)","tc":\d+,"qlvl":(\d+),"tier":"set"')


def _records():
    """(name, qlvl) for every set-tier drop record. Parsed from the record shape, not grepped."""
    out = []
    for name, q in REC.findall(SRC):
        out.append((name.replace('\\"', '"').replace("\\'", "'"), int(q)))
    return out


class TheSetPiecesCarryARealQlvl(unittest.TestCase):

    def test_the_records_are_still_there_at_all(self):
        """⚠ THE DENOMINATOR. Every law below is a ratio over this number; if the record shape ever
        changes, they would all pass over nothing. [[zero-needs-a-denominator]]"""
        recs = _records()
        self.assertGreater(len(recs), 1500,
                           "only %d set-tier records parsed — the record shape moved and every "
                           "law in this file is now measuring almost nothing" % len(recs))

    # ── ⚠⚠ THE RATCHET ──────────────────────────────────────────────────────────────────────
    def test_the_fill_does_not_go_BACKWARDS(self):
        """★★ A regeneration of this data that silently drops the qlvls would look like a normal
        diff. 1,477 of 1,598 carried a value when this shipped; a rebuild that reverts them to 0
        must go red rather than quietly send him back to farming blind."""
        recs = _records()
        filled = [r for r in recs if r[1] > 0]
        self.assertGreaterEqual(len(filled), 1450,
                                "only %d of %d set records carry a qlvl (1,477 shipped) — the fill "
                                "was reverted or a regeneration dropped it"
                                % (len(filled), len(recs)))

    def test_every_qlvl_is_a_LEGAL_level(self):
        """A qlvl outside 1..99 is not a game value. 0 is allowed and means UNKNOWN."""
        bad = [r for r in _records() if r[1] != 0 and not (1 <= r[1] <= 99)]
        self.assertEqual(bad, [], "set records carry an impossible quality level: %s" % bad[:5])

    # ── ⚠⚠ THE LAW THAT PINS THE DATA WITHOUT SHIPPING IT ───────────────────────────────────
    def test_one_NAME_never_carries_two_different_qlvls(self):
        """★★★ THE STRUCTURAL CHECK, and the reason this gate needs no Blizzard bytes.

        A set piece appears in MANY drop records — once per boss, zone and difficulty that can drop
        it. Measured: 1,598 records over ~151 distinct names. The quality level is a property of
        the ITEM, so every record naming the same piece must agree. A partial fill, a bad join, or
        an edit that caught some records and missed others breaks this instantly — and it does so
        without the game table being present to compare against."""
        by = {}
        for name, q in _records():
            by.setdefault(name, set()).add(q)
        split = {n: sorted(v) for n, v in by.items() if len({x for x in v if x > 0}) > 1}
        self.assertEqual(split, {},
                         "the same piece carries two different quality levels in different drop "
                         "records, so the fill is partial or the join was wrong: %s"
                         % list(split.items())[:4])

    def test_a_piece_is_never_HALF_filled(self):
        """⚠ The sibling of the law above, in the direction it cannot see: a name that carries a
        real qlvl in one record and 0 in another. Both are 'no two different values' by the letter
        of the previous test, because 0 is excluded there — 0 means UNKNOWN, and a piece is either
        known or it is not."""
        by = {}
        for name, q in _records():
            by.setdefault(name, set()).add(q)
        half = {n: sorted(v) for n, v in by.items() if 0 in v and any(x > 0 for x in v)}
        self.assertEqual(half, {},
                         "these pieces are UNKNOWN in some drop records and known in others, which "
                         "means the fill reached only part of the file: %s" % list(half)[:6])

    # ── ⛔ THE UNKNOWNS STAY UNKNOWN ─────────────────────────────────────────────────────────
    def test_the_pieces_with_no_game_row_were_NOT_guessed(self):
        """⛔ ELEVEN pieces have no row in his extracted game table under any spelling, so they stayed 0 = UNKNOWN - a guess
        would trace to nothing. v3884 (REG-3440, his 11-08 ruling that silospen's level is the quality level): silospen's
        RotW 3.0 calculator DOES list all eleven, spelled as this file spells them, so each carries silospen's level now -
        a value that traces (tv/data/silospen_qlvl_rotw30.json), and every piece of each set agrees with its set-mates (the
        uniformity case above). A piece silospen also lacked would stay 0. If this goes red, a value was written that is
        neither silospen's nor UNKNOWN. [[unknown-stays-unknown]]"""
        import json as _json
        import sys as _sys
        _sys.path.insert(0, HERE)
        import silospen_tz_levels as _T
        with io.open(os.path.join(HERE, "data", "silospen_qlvl_rotw30.json"), encoding="utf-8") as fh:
            lv = dict((_T.canon(n), v["level"]) for n, v in _json.load(fh)["levels"].items())
        no_game_row = {"Aldur's Rhythm", "Dark Adherent", "Hwanin's Blessing", "Sander's Paragon",
                       "Sander's Riprap", "Sander's Superstition", "Sander's Taboo",
                       "Taebaek's Glory", "Tal Rasha's Fine-Spun Cloth",
                       "Tal Rasha's Guardianship", "Whitstan's Guard"}
        by = {}
        for name, q in _records():
            by.setdefault(name, set()).add(q)
        bad = sorted("%s: %s, silospen %s" % (n, sorted(by[n]), lv.get(_T.canon(n)))
                     for n in no_game_row if n in by and by[n] != {lv.get(_T.canon(n)) or 0})
        self.assertEqual(bad, [],
                         "a piece with no game-table row carries a level that is neither silospen's nor UNKNOWN: %s" % bad)

    def test_the_provenance_is_written_down(self):
        """⚠ His rule is that a value must TRACE. The game data cannot live in a public repo, so
        the trace is the note — the CASC paths, both file hashes, the column names, the join key,
        the cross-check result and the three aliases. Without it these are 1,477 numbers with no
        author."""
        p = os.path.join(os.path.dirname(HERE), "SET_QLVL_PROVENANCE.md")
        self.assertTrue(os.path.isfile(p), "the provenance note is gone — the numbers no longer "
                                           "trace to anything")
        t = io.open(p, encoding="utf-8").read()
        for must in ("setitems.txt", "sha256", "index", "lvl", "cross-check"):
            self.assertIn(must, t, "the provenance note no longer records %r" % must)


RED_PROOF = [
    {'why': "v3884 (REG-3440) - a level that is neither silospen's nor UNKNOWN is written onto a piece with no game-table row (Aldur's Rhythm 29 -> 50, all 11 of its records): it traces to nothing, and the law must go red", 'file': 'bible.html', 'find': '{"n":"Aldur\'s Rhythm","tc":0,"qlvl":29,"tier":"set"', 'replace': '{"n":"Aldur\'s Rhythm","tc":0,"qlvl":50,"tier":"set"', 'matches': 11},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
