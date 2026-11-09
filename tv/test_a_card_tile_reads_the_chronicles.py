# -*- coding: utf-8 -*-
"""THE REEL CARD'S LAST TWO TILES MUST READ THE CHRONICLES, AND AN ABSENT ROSTER IS NOT A ZERO.

Konyo, 2026-09-13: *"and the photo data anylasis within the video here where its says grail.. i want
it reading the chronicles.. what does cover even mean? i think it can also be rem[ov]ed visually so i
dont see it and see the chronicles sets or uniques instead of it. so 4 also"*

He was right on both counts, and the numbers say why. MEASURED over the **425 cards the shelf
actually renders** — not all 2,893 journal rows, because the shelf hides empty runs and that wrong
denominator would have overstated every figure here ([[zero-needs-a-denominator]]):

    COVER   had a value on  16 of 425 cards — and TWELVE of those sixteen read 0%.
            A real figure appeared on FOUR cards in four hundred and twenty-five. Furniture.
    GRAILS  counted `tier === 'grail'` and found 16, because `tier` is NEVER SET on 194 of the
            218 finds (89%). It was not measuring rarity. It was measuring whether one optional
            field happened to be filled in.

Every find carries a NAME, and the chronicle rosters know what a name IS — 398 uniques, 135 set
pieces. Folding the same 218 names: **57 uniques + 26 sets = 83 classified, against the old tile's
16**, and a figure on 25 cards where the old one managed 10. The 135 that match nothing are base
items and runewords ("Amulet", "Battle Staff", "Bramble") and are CORRECTLY not chronicle rows.
[[the-unjoined-end]]

⚠ IT FOLDS WITH THE LANE'S OWN RESOLVER. `chronicle_resolve.canonical` already handles apostrophe
forms, the "(amulet)" suffix, and REFUSES ambiguous near-twins like "Bone Break"/"Latent Bone
Break". Measured before trusting it: exact-fold and canonical() return the identical 57/26/135 on
his real data, zero drift. A second comparison written at the call site is how one near-twin gets
folded two different ways in two places. [[copy-drift]]

⚠⚠ AND `—` AND `?` ARE DIFFERENT ANSWERS. `—` is a measured none; `?` is the roster failing to
load. `load_roster` RAISES rather than returning `{}` in its own words because "an empty roster
would silently classify every name as debris" — which here would print a confident **0 uniques on
every card in the shelf**. [[unknown-stays-unknown]]
"""
import ast
import io
import os
import re
import unittest

from console_safe import enable as _console_safe_enable

_console_safe_enable()

HERE = os.path.dirname(os.path.abspath(__file__))


def _ui():
    with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
        return fh.read()


def _statrow():
    """The stat-grid builder, anchored at BOTH ends — never a fixed-size window."""
    s = _ui()
    a = s.find("var statRow = '<div class=\"shc-stats\">")
    assert a > 0, "the reel card's stat grid is gone"
    b = s.find("</div>';", a)
    assert b > a, "the stat grid has no end"
    return s[a:b + 8]


class TestACardTileReadsTheChronicles(unittest.TestCase):

    def test_the_dead_cover_tile_is_gone(self):
        row = _statrow()
        self.assertNotIn("'cover'", row,
                         "the COVER tile is back. It had a value on 16 of 425 cards and twelve of "
                         "those read 0% — four real figures in four hundred and twenty-five")
        self.assertNotIn("_covPct", _ui(),
                         "_covPct is back. Its only reader was the COVER tile, so it is dead code "
                         "that will read as a live feature to the next person")
        print("cover tile: absent; _covPct: absent")

    def test_the_chronicles_box_counts_only_the_green_keyword(self):
        """v3890 (#184, his 11-09: "FOUND should be chronicle found meaning the keyword in green for unidentified items before
        being identified" - "found change to chronicles rename it"). The box is CHRONICLES and reads chroniclesFound; where the
        run carries none it is '?', never sm.registered (every registered find - the uniques and sets beside it, again)."""
        ui = _ui()
        self.assertIn(" + _scell(_chronCell, 'chronicles', '', _chronTip)", ui)
        self.assertNotIn("_scell(_foundN, 'found')", ui, "the FOUND box is back")
        self.assertIn("var _chronN = (typeof sm.chroniclesFound === 'number'", ui)
        self.assertIn("var _chronCell = (_chronN === null) ? '?'", ui, "an uncounted run reads as a number")

    def test_the_last_two_tiles_are_uniques_and_sets(self):
        row = _statrow()
        for lab in ("'uniques'", "'sets'"):
            self.assertIn(lab, row, "the card no longer shows %s" % lab)
        # ⚠ the binding lives one line ABOVE the region, so assert it where it IS rather than
        # widening the window until the string happens to fall inside. [[source-window-shortcut]]
        self.assertIn("_ch", row, "the tiles are not reading the chronicle tally variable")
        ui = _ui()
        self.assertTrue(re.search(r"var\s+_ch\s*=\s*sm\.chron", ui),
                        "_ch is not bound from sm.chron, so the tiles are showing something other "
                        "than the server's chronicle tally")
        self.assertNotIn("f.tier === 'grail'", row,
                         "a tile is counting tier === 'grail' again — that field is unset on 194 "
                         "of 218 finds, so it measures whether someone filled a field in")
        print("tiles: reads · found · uniques · sets, fed by sm.chron")

    def test_an_absent_roster_is_not_a_zero(self):
        row = _statrow()
        # ⚠ COUNT them, one per tile. Asserting `"'?'" in row` went BLIND in the red-proof drill:
        # sabotaging the UNIQUES tile left the SETS tile's '?' behind and the substring still
        # matched, so the law stayed green through its own defeat. A law that reads source must
        # pin the thing, not a character that appears elsewhere. [[sabotage-is-usually-the-wrong-one]]
        qn = row.count(": '?'")
        self.assertEqual(qn, 2,
                         "expected an UNKNOWN branch on BOTH chronicle tiles, found %d. Without "
                         "it a roster that failed to load prints a confident dash and the card "
                         "claims it added nothing to the chronicles" % qn)
        dn = row.count("'—'")
        self.assertEqual(dn, 2,
                         "expected a measured-none dash on both chronicle tiles, found %d" % dn)
        print("'?' on %d tiles, '—' on %d — no-roster and measured-none stay separate" % (qn, dn))

    def test_the_server_refuses_rather_than_reporting_zero(self):
        """_chron_tally must return None — not {0,0,0} — when the rosters cannot load."""
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        i = src.find("def _chron_tally(")
        self.assertGreater(i, 0, "_chron_tally is gone")
        j = src.find("\ndef ", i + 10)
        fn = ast.parse(src[i:j if j > i else len(src)].strip()).body[0]
        # ⚠ PIN THE ROSTER BRANCH, not "some return is None". Asking only whether a bare
        # `return None` exists anywhere went BLIND: the `except Exception` handler has one, so
        # turning the roster branch into a tally of zeros left the law green.
        guard = None
        for node in ast.walk(fn):
            if isinstance(node, ast.If) and any(
                    isinstance(c, ast.Compare) and isinstance(c.left, ast.Name)
                    and c.left.id in ("u", "sr")
                    for c in ast.walk(node.test)):
                guard = node
                break
        self.assertIsNotNone(guard,
                             "_chron_tally no longer tests whether the rosters loaded at all")
        rets = [n for n in ast.walk(guard) if isinstance(n, ast.Return)]
        self.assertTrue(rets, "the roster guard returns nothing")
        for r in rets:
            self.assertTrue(isinstance(r.value, ast.Constant) and r.value.value is None,
                            "the missing-roster branch returns %s instead of None — a tally of "
                            "zeros over an absent roster is the exact failure load_roster raises "
                            "an exception to prevent, and every card would claim it put nothing "
                            "in the chronicles" % ast.dump(r.value)[:60])
        print("_chron_tally: the roster guard returns None (%d return(s) in it)" % len(rets))

    def test_it_folds_with_the_lanes_own_resolver(self):
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        i = src.find("def _chron_tally(")
        j = src.find("\ndef ", i + 10)
        body = src[i:j if j > i else len(src)]
        code = "\n".join(ln.split("#", 1)[0] for ln in body.splitlines())
        self.assertIn("canonical(", code,
                      "the tally is comparing names itself instead of folding through "
                      "chronicle_resolve.canonical — a parallel matcher is how a near-twin pair "
                      "gets folded two different ways in two places")
        print("tally folds via chronicle_resolve.canonical")

    def test_the_rosters_are_real_and_the_split_is_the_measured_one(self):
        """No footage, no console — just the rosters, so this cannot go blind on CI."""
        try:
            import chronicle_resolve as R
            u, s = R.load_roster(), R.load_set_roster()
        except Exception as exc:
            self.skipTest("the rosters are not loadable here (%s) — UNMEASURED, not passed"
                          % type(exc).__name__)
        print("rosters: %d uniques, %d set pieces" % (len(u), len(s)))
        self.assertGreater(len(u), 300, "the uniques roster collapsed")
        self.assertGreater(len(s), 100, "the set roster collapsed")
        # the three names that made the case, each still classifying the way it did when measured
        self.assertIsNotNone(R.canonical("Andariel's Visage", u), "a known unique stopped folding")
        self.assertIsNone(R.canonical("Amulet", u),
                          "the bare base item 'Amulet' now folds onto a unique — the tally would "
                          "count ordinary drops as chronicle rows")
        self.assertIsNone(R.canonical("Amulet", s), "'Amulet' now folds onto a set piece")
        print("Andariel's Visage -> unique · Amulet -> neither (correctly not a chronicle row)")


    def test_a_reel_nobody_read_is_not_a_reel_with_nothing(self):
        """⚠⚠ THE SECOND WAY THE NUMBER CAN BE UNKNOWN, WHICH v3090's LAW MISSED.

        Found by the post-ship review, not by this file. v3090 guarded the ROSTER branch —
        "the rosters would not load" — and never the FINDS branch. But `_finds` is initialised to
        None in control_app (~:28998) and only becomes a list once a register report exists, so an
        unsealed reel, a stub, or a failed reel_report leaves it None. `(finds or [])` then fell
        through the loop and returned {0,0,0}, which is TRUTHY in JS — so the card printed the
        measured-none dash and asserted "this reel put nothing in the chronicles" about a reel
        nobody had ever read.

        A guard that covers one of the two ways a number can be unknown is not a guard. The two
        cases are DIFFERENT ANSWERS and this pins both:
            finds is None  -> None       nobody looked
            finds == []    -> {0,0,0}    looked, found nothing
        [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
        """
        import control_app as CA
        self.assertIsNone(CA._chron_tally(None),
                          "a reel whose finds were never built reports a tally of zeros — the card "
                          "then says it added nothing to the chronicles about a reel nobody read")
        empty = CA._chron_tally([])
        self.assertIsInstance(empty, dict,
                              "an EMPTY find list is a real measurement and must stay a tally, not "
                              "collapse into the same UNKNOWN as a reel nobody read")
        self.assertEqual((empty.get("uniques"), empty.get("sets")), (0, 0))
        print("finds None -> None (nobody looked) · finds [] -> %s (measured none)" % empty)


RED_PROOF = [
    {"why": "v3890 (#184) - the CHRONICLES box shows every registered find again (the old FOUND, under the new name)",
     "file": "tv/control_ui.html",
     "find": "      var _chronCell = (_chronN === null) ? '?' : ",
     "replace": "      var _chronCell = (_chronN === null) ? _foundN : ",
     "matches": 1},
    {
        "why": "the dead COVER tile comes back — a figure that was absent on 409 of 425 cards and "
               "read 0% on 12 of the 16 that had one",
        "file": "control_ui.html",
        "find": "        + _scell(_ch ? (_ch.sets > 0 ? ('🧩 ' + _ch.sets) : '—') : '?', 'sets',",
        "replace": "        + _scell(_covPct != null ? (_covPct + '%') : '—', 'cover') + '</div>';",
        "matches": 1,
    },
    {
        "why": "the UNKNOWN branch collapses into the measured-none dash, so a roster that failed "
               "to load prints a confident '—' and every card claims it added nothing",
        "file": "control_ui.html",
        "find": "        + _scell(_ch ? (_ch.uniques > 0 ? ('🏆 ' + _ch.uniques) : '—') : '?', 'uniques',",
        "replace": "        + _scell(_ch && _ch.uniques > 0 ? ('🏆 ' + _ch.uniques) : '—', 'uniques',",
        "matches": 1,
    },
    {
        "why": "the None-finds guard is removed, so a reel whose finds were never built reports a "
               "tally of zeros and the card claims it put nothing in the chronicles — the exact "
               "0-vs-None collapse the post-ship review caught in v3090",
        "file": "control_app.py",
        "find": "    if finds is None:\n        return None\n    u, sr = _chron_rosters()",
        "replace": "    u, sr = _chron_rosters()",
        "matches": 1,
    },
    {
        "why": "the server tally reports zeros instead of refusing when the rosters cannot load — "
               "the exact failure load_roster raises an exception to prevent",
        "file": "control_app.py",
        "find": "    u, sr = _chron_rosters()\n    if u is None or sr is None:\n        return None",
        "replace": "    u, sr = _chron_rosters()\n    if u is None or sr is None:\n        return {\"uniques\": 0, \"sets\": 0, \"other\": 0}",
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
