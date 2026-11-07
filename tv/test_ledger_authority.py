# -*- coding: utf-8 -*-
"""v2746 — THE LEDGER AUTHORITY, and every law in it driven RED before it is trusted.

Konyo's ask, on Dean's fleet card reading "⚠ running on the OWNER'S SEED" above SETS 128/135,
UNIQUES 249/403, RUNEWORDS 94/99:

    "how does that get removed what of him to do? like it should read he hasnt yet synced his
     uniques.. sets and runewords has been verified by him already and accepted.. maybe thats like
     a little toggle also needed to bypass this?"

WHAT EACH TEST BELOW HAD TO SURVIVE. A guard that has only ever been green is measuring nothing, so
every law here was sabotaged and watched go red, and the sabotage is named in the docstring with
the number it moved. Two of them are AST laws rather than text laws, because in this repo a
text-presence suite once passed 7/7 over a write sitting under `if False:`.

⚠ THE MEASUREMENTS ARE FROM HIS LIVE BOARD, 2026-09-06, and they are what these tests are calibrated
against — but NOT what they assert. Pinning 246 would freeze today's seed into a law, and the seed
is the one thing in this feature that must be free to grow. The laws assert the RULE; the numbers
appear only in comments, as the reason the rule exists.

    uniques    292/403   246 of 311 chronicle rows carry a seed name AND the seed's own date
    sets       123/135   108 of 123                                  ->  15 earned here
    runewords   99/99     99 of 99                                   ->   0 earned here
"""
import ast
import io
import re
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

import ledger_authority as LA          # noqa: E402

with io.open(os.path.join(HERE, "ledger_authority.py"), encoding="utf-8") as _fh:
    SRC = _fh.read()


def _between(src, start, end):
    """Anchored at BOTH ends — never a fixed window. [[source-reading-guard]]"""
    i = src.find(start)
    if i < 0:
        return None
    j = src.find(end, i + len(start))
    return None if j < 0 else src[i:j + len(end)]


def _board(**kw):
    """A synthetic board_ownership payload. Everything the classifier reads, and nothing else."""
    stores = kw.pop("stores", {})
    d = {"ok": True, "boardLoaded": True, "owner": True, "onOwnerSeed": True,
         "seedsBelongHere": True, "ledgerName": "KonyoEndgame", "seedLedger": "KonyoEndgame",
         # ⚠ pfx IS PART OF THE REAL PAYLOAD and must be in the fixture. Without it
         # namespace_of() correctly answers UNKNOWN, and a fixture that cannot name its own
         # world grades a shape the board never sends. [[feedback-blind-fixture-green-gate]]
         "route": {"id": "TEST-WORLD", "p": "main", "m": "owner", "pfx": ""},
         "counts": {"chronFound": 0, "chronTotal": 403, "setPieces": 0, "setsTotal": 135,
                    "runewordsMade": 0, "runewordsTotal": 99},
         "fullStores": dict((k, json.dumps(v)) for k, v in stores.items())}
    d.update(kw)
    return d


def _led(res, name):
    return [x for x in res["ledgers"] if x["ledger"] == name][0]


# ══ 0. A LAW THAT CANNOT FIND ITS SUBJECT PASSES HAVING EXAMINED NOTHING ═══════════════════════

class TheGuardCanFindItsSubject(unittest.TestCase):

    def test_bible_html_is_where_this_guard_thinks_it_is(self):
        self.assertTrue(os.path.exists(LA.BIBLE),
                        "bible.html is not at %s — every law below would grade an empty parse "
                        "and report a clean green" % LA.BIBLE)

    def test_every_declared_seed_anchor_actually_MATCHES(self):
        """⚠ THE EXACT TRAP THIS FEATURE ALREADY FELL INTO ONCE. A first pass searched _RW_SEED /
        _RUNE_SEED / _RUNEWORD_SEED, matched nothing, and was one step from reporting "runewords
        are never seeded, the warning is over-broad" — which is false; the name is _RWC_SEED and it
        holds the entire 99-name universe. An anchor that matches nothing is indistinguishable from
        a seed that does not exist unless the code refuses to conflate them.
        [[feedback-suspect-the-instrument]]"""
        t = LA.seed_table()
        self.assertTrue(t["ok"], "the seed parse refused: %s" % t.get("why"))
        self.assertEqual(set(LA.SEED_ANCHORS), set(t["seeds"]),
                         "a declared anchor found nothing. Fix SEED_ANCHORS before trusting any "
                         "provenance answer.")
        for name, row in t["seeds"].items():
            self.assertGreater(row["n"], 0, "%s parsed to an EMPTY object — an anchor that lands "
                                            "on the wrong brace reports a seed of size 0" % name)

    def test_the_FIFTH_seed_is_in_the_table(self):
        """bible.html:18483 calls _RWV_SEED "THE FIFTH SEED ... like the other four" in its own
        words. Every list that enumerated four was wrong about the file it describes, and a seed
        left out of the table is a seed whose rows get counted as somebody's own progress."""
        self.assertIn("_RWV_SEED", LA.SEED_ANCHORS,
                      "the runeword-verdict seed is missing from the anchor table")
        self.assertIn("_RWV_SEED", LA.seed_table()["seeds"])


# ══ 1. THE PARSE — brace-matched, never regex, never a constant ════════════════════════════════

class TheSeedIsParsedNotHardcoded(unittest.TestCase):

    def test_no_seed_SIZE_appears_as_a_literal_anywhere_in_the_module(self):
        """⚠ THE LAW, AND IT IS THE ONE KONYO ASKED FOR: *"even that is so outdated.. it needs to
        auto update and not be stale"*. `_GRAIL_SEED` was 243 at v659 and is 245 today; any module
        that hardcodes a size starts publishing a wrong number the moment a name is added.

        This is an AST law, not a grep: the numbers appear in DOCSTRINGS and comments all over this
        file (they are the evidence), and a text search would either fail on the prose or be
        weakened until it matched nothing. Only executable numeric literals are graded.

        SABOTAGE: adding `return 245` inside seed_names_for -> FAILS, naming seed_names_for.
        """
        tree = ast.parse(SRC)
        sizes = {245, 246, 108, 99, 255, 292, 123, 403, 135}
        bad = []
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef,)):
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Constant) and isinstance(node.value, int) \
                        and not isinstance(node.value, bool) and node.value in sizes:
                    bad.append("%s -> %d" % (fn.name, node.value))
        self.assertFalse(bad, "a seed/tally SIZE is a live literal in the code: %s. Parse it from "
                              "bible.html instead — a constant here is a promise about a file that "
                              "someone else edits." % "; ".join(bad))

    def test_the_parse_is_brace_matched_and_string_aware(self):
        """A regex answer would be 1 (non-greedy, stopping at the first `}`) or the whole file
        (greedy). Both look like numbers. Proven directly against a hostile literal rather than by
        reading the code."""
        src = ('junk const _X_SEED = {"Verdungo\'s Hearty Cord":"a}b",'
               '"Gloom\'s Trap":"x\\"y{z","The Diggler":"?/27/2026 · ?:15 · partial"}'
               ' trailing }}}}')
        blk, line = LA._brace_object(src, "const _X_SEED = {")
        self.assertIsNotNone(blk, "the brace matcher found nothing in a valid literal")
        got = json.loads(blk)
        self.assertEqual(3, len(got),
                         "an apostrophe opened a string, or a `}` inside a value closed the object")
        self.assertEqual("a}b", got["Verdungo's Hearty Cord"])
        self.assertEqual(1, line)

    def test_a_missing_anchor_REFUSES_rather_than_reporting_an_empty_seed(self):
        """SABOTAGE: point the parser at a file with no seeds in it. `ok:False` with a named seed
        is the only acceptable answer — `{"ok": True, "seeds": {}}` would make every ledger read
        SYNCED and every inherited row read as the person's own."""
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as fh:
            fh.write("<html>no seeds here at all</html>")
            p = fh.name
        try:
            t = LA.seed_table(path=p, force=True)
            self.assertFalse(t["ok"], "a file with no seed literals parsed as OK")
            self.assertEqual({}, t["seeds"])
            for n in LA.SEED_ANCHORS:
                self.assertIn(n, t["why"], "the refusal does not name %s, so nobody can fix it" % n)
        finally:
            os.unlink(p)

    def test_a_truncated_literal_REFUSES_rather_than_parsing_half(self):
        """SABOTAGE: cut a seed literal in half. An unclosed brace must not yield a smaller seed —
        that reads as "these rows are his own" for every name past the cut."""
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as fh:
            fh.write('const _GRAIL_SEED = {"A":"1","B":"2"')      # never closed
            p = fh.name
        try:
            t = LA.seed_table(path=p, force=True)
            self.assertFalse(t["ok"])
            self.assertNotIn("_GRAIL_SEED", t["seeds"],
                             "half a literal was accepted as a whole seed")
        finally:
            os.unlink(p)

    def test_the_union_is_not_the_SUM(self):
        """MEASURED: _GRAIL_SEED (245) and _RULING_SEED (10) share 9 names, so the uniques seed is
        246 and not 255. Summing would over-state the seed's reach by nine and make nine of his own
        finds read as inherited. Asserts the RULE (union < sum when they overlap), not the 246."""
        names, meta = LA.seed_names_for("uniques")
        self.assertIsNotNone(names)
        self.assertEqual(len(names), meta["unionN"])
        self.assertLess(meta["unionN"], meta["sumN"],
                        "the two uniques seeds are being added rather than unioned")
        self.assertEqual(meta["sumN"] - meta["unionN"], meta["overlap"])

    def test_an_unknown_ledger_is_REFUSED_not_defaulted(self):
        """A typo'd ledger answering confidently about `uniques` is how a cross-reference comes
        back sure and wrong. SABOTAGE: `ledger_spec('uniqes')`."""
        spec, why = LA.ledger_spec("uniqes")
        self.assertIsNone(spec)
        self.assertIn("uniqes", why)
        self.assertIsNone(LA.seed_names_for("uniqes")[0])

    def test_the_seed_carries_no_age_and_says_so(self):
        """[[stale-reading]] — the age of the THING, not the fetch. `newestFindDate` is the newest
        date the seed RECORDS; when it was transcribed is not written anywhere, so `stampedAt` is
        None with a reason rather than being inferred from the find dates."""
        t = LA.seed_table()
        for name, row in t["seeds"].items():
            self.assertIsNone(row["stampedAt"],
                              "%s claims a transcription time nothing records" % name)
            self.assertIn("no transcription timestamp", row["stampedWhy"])
        self.assertIsNone(t["seeds"]["_RWV_SEED"]["newestFindDate"],
                          "the verdict seed holds 'fail', not dates — a parsed date there would "
                          "be invented")


# ══ 2. CLASSIFICATION — 0 is measured, None is nobody looked ═══════════════════════════════════

class ClassificationRefusesToGuess(unittest.TestCase):

    def test_an_undumped_store_is_UNKNOWN_not_SYNCED(self):
        """⚠ THE DIRECTION THAT MATTERS. A store the board did not send must never read as "this
        ledger has no seeded rows" — that is a clean-looking green over a question nobody asked.
        SABOTAGE: fullStores = {}. Every ledger must be UNKNOWN with rows=None."""
        r = LA.classify_local(own=_board(stores={}))
        # REG-1893 - "every ledger is UNKNOWN" over an empty list says nothing; every ledger must be in it
        self.assertEqual(sorted(x["ledger"] for x in r["ledgers"]), sorted(LA.LEDGER_NAMES),
                         "classify_local did not report every ledger, so the claim below skips some")
        for x in r["ledgers"]:
            self.assertEqual(LA.UNKNOWN, x["provenance"], x["ledger"])
            self.assertIsNone(x["rows"], "%s reported a row COUNT from a store it never "
                                         "read" % x["ledger"])
            self.assertIsNone(x["seedRows"])
            self.assertFalse(x["measured"])

    def test_a_store_that_is_present_and_EMPTY_is_zero_not_unknown(self):
        """The other half of the same law, and without it the first one is just a blanket refusal.
        An empty store is MEASURED at 0. [[unknown-stays-unknown]]

        ⚠ THE EXPECTED VALUE CHANGED ON 2026-09-07 AND THE LAW'S PURPOSE DID NOT. This asserted
        SYNCED. Konyo caught the consequence on his own fleet card — Dean's row read "UNIQUES
        SYNCED" directly above "UNIQUES 0 / 403 found": *"maybe after he reset it it should read
        UNSYCNED until he resyncs it again..?"* SYNCED means "this ledger's rows were earned on
        this board" (ledger_authority.py:98) and an empty ledger has earned nothing, so the label
        outlived its referent. A fifth provenance was added for exactly this row.

        ⚠⚠ WHAT THIS TEST IS FOR IS UNCHANGED, AND IT IS THE POINT: an empty-but-present store is
        MEASURED AT ZERO, never UNKNOWN. UNSYNCED is a measured answer — it says the store was read
        and holds nothing. Swapping the constant keeps the law; swapping it to UNKNOWN would have
        destroyed it. [[label-outlived-referent]]"""
        r = LA.classify_local(own=_board(stores={"d2r_foundLog": {}, "d2r_setPieces": [],
                                                 "d2r_rwMade": {}}))
        # REG-1893 - "every ledger is measured at zero" over an empty list says nothing
        self.assertEqual(sorted(x["ledger"] for x in r["ledgers"]), sorted(LA.LEDGER_NAMES),
                         "classify_local did not report every ledger, so the claim below skips some")
        for x in r["ledgers"]:
            self.assertEqual(0, x["rows"], x["ledger"])
            self.assertEqual(0, x["seedRows"])
            self.assertTrue(x["measured"])
            self.assertEqual(LA.UNSYNCED, x["provenance"],
                             "an empty ledger has no inherited rows so it is not SEEDED, and no "
                             "earned rows either so it is not SYNCED")
            self.assertNotEqual(LA.UNKNOWN, x["provenance"],
                                "an empty store that WAS read must never read as nobody-looked")

    def test_a_seed_row_is_recognised_by_the_seed_s_OWN_DATE(self):
        """The boot floor writes `_gfl[n] = _GRAIL_SEED[n]` and ONLY when the key is absent
        (bible.html:20595), so the seed's date string is the floor's fingerprint. A row with a seed
        NAME but a different date was ticked by the person before the floor could reach it, and it
        is theirs. SABOTAGE: re-date one seeded row -> it must move from seedRows to ownRows."""
        t = LA.seed_table()
        g = t["seeds"]["_GRAIL_SEED"]
        first, second = g["names"][0], g["names"][1]
        store = {first: g["dates"][first], second: "some date he typed himself"}
        r = LA.classify_local(own=_board(stores={"d2r_foundLog": store}))
        u = _led(r, "uniques")
        self.assertEqual(1, u["seedRows"], "the seed-dated row was not recognised")
        self.assertEqual(1, u["ownRows"], "the RE-DATED row was still counted as inherited — a "
                                          "name match alone is not provenance")
        self.assertEqual(0, u["beyondSeed"])
        self.assertEqual(2, u["rows"])

    def test_set_pieces_living_in_d2r_foundLog_are_NOT_counted_as_uniques(self):
        """⚠ MEASURED ON HIS BOARD: 108 of 419 foundLog rows are set pieces, because the set floor
        stamps _SET_SEED into d2r_foundLog as well as d2r_setPieces (bible.html:20618). Without
        `alsoWrites` the uniques ledger is inflated by the entire sets seed.
        SABOTAGE: empty LEDGERS[0]['alsoWrites'] -> beyondSeed jumps by the whole set seed."""
        t = LA.seed_table()
        s = t["seeds"]["_SET_SEED"]
        store = dict((n, s["dates"][n]) for n in s["names"][:5])
        r = LA.classify_local(own=_board(stores={"d2r_foundLog": store}))
        u = _led(r, "uniques")
        self.assertEqual(0, u["rows"], "set-piece rows were counted into the uniques ledger")
        self.assertEqual(5, u["foreignRowsExcluded"])

    def test_a_LIST_store_says_it_has_no_dates_rather_than_implying_none_are_his(self):
        """d2r_setPieces is an array of names, so the "seed name, own date" bucket cannot exist for
        it. Silence there would read as "none of his sets are his own"."""
        r = LA.classify_local(own=_board(stores={"d2r_setPieces": ["Angelic Halo (ring)", "Mine"]}))
        s = _led(r, "sets")
        self.assertFalse(s["datesAvailable"])
        self.assertEqual(0, s["ownRows"])
        self.assertEqual(1, s["beyondSeed"], "a name outside the seed was not counted as his own")

    def test_an_UNANSWERED_onOwnerSeed_is_UNKNOWN_even_when_seed_rows_are_present(self):
        """null is not false. An older console reports no flag at all, and seeing seed-dated rows
        is not permission to decide the seed belongs there."""
        t = LA.seed_table()
        g = t["seeds"]["_GRAIL_SEED"]
        store = {g["names"][0]: g["dates"][g["names"][0]]}
        r = LA.classify_local(own=_board(onOwnerSeed=None, seedsBelongHere=None,
                                         stores={"d2r_foundLog": store}))
        self.assertEqual(LA.UNKNOWN, _led(r, "uniques")["provenance"])
        self.assertEqual(1, _led(r, "uniques")["seedRows"],
                         "the count is still MEASURED — only the verdict is unknown")


# ══ 3. THE FLEET SIDE — derived, and a deficit is never clamped ════════════════════════════════

class FleetRowsAreDerivedAndSaySo(unittest.TestCase):

    def test_a_derived_figure_is_LABELLED_derived(self):
        """No item name crosses the fleet boundary (functions/api/console.js states it), so a
        remote row's seedRows is inferred from the code, not measured. Presenting it unlabelled
        would let it be read as a measurement."""
        # ⚠ v3313 — through `runewords`, whose figure IS len(d2r_rwMade) and so can genuinely be
        # split into inherited and earned. Driven through `uniques` this asserted a sentence built
        # from a subtraction that was never valid, and the enlarged seed flipped it to the deficit
        # branch — "63 seeded row(s) are MISSING" — a claim about ROWS derived from a count of
        # NAMES. The label-it-derived rule is unchanged; only the ledger carrying it moved.
        v = LA.classify_row({"ok": True, "onOwnerSeed": True,
                             "runewords": {"have": 120, "total": 135}})
        u = _led(v, "runewords")
        self.assertTrue(u["derived"])
        self.assertFalse(u["measured"])
        self.assertIn("no item name crosses", u["why"])

    def test_a_DEFICIT_is_reported_negative_and_never_clamped(self):
        """⚠⚠ MEASURED ON DEAN'S REAL ROW: runewords 94 against a seed of 99. `max(0, have-seed)`
        prints a comfortable 0; the truth is that five seeded rows are MISSING from his store,
        which is a fact about his board nobody would otherwise see.
        SABOTAGE: wrap beyondSeed in max(0, ...) -> this test fails on the sign.
        [[zero-needs-a-denominator]]"""
        n = len(LA.seed_names_for("runewords")[0])
        v = LA.classify_row({"ok": True, "onOwnerSeed": True,
                             "runewords": {"have": n - 5, "total": n}})
        rw = _led(v, "runewords")
        self.assertEqual(-5, rw["beyondSeed"])
        self.assertIn("MISSING", rw["why"])

    def test_the_subtraction_is_NOT_performed_when_the_seed_never_landed(self):
        """`beyondSeed = have - seedN` is only valid because the boot floor writes EVERY missing
        seed name when the seed belongs there (bible.html:20593). On a board that declared its own
        ledger the premise is false, so the figure is not produced at all."""
        for flag, want in ((False, LA.SYNCED), (None, LA.UNKNOWN)):
            v = LA.classify_row({"ok": True, "onOwnerSeed": flag,
                                 "sets": {"have": 128, "total": 135}})
            s = _led(v, "sets")
            self.assertEqual(want, s["provenance"], "onOwnerSeed=%r" % flag)
            self.assertIsNone(s["seedRows"], "a subtraction was performed on a false premise")
            self.assertIsNone(s["beyondSeed"])

    def test_a_row_with_no_count_produces_no_derived_figure(self):
        v = LA.classify_row({"ok": True, "onOwnerSeed": True, "sets": None})
        self.assertIsNone(_led(v, "sets")["beyondSeed"])


# ══ 4. ⛔ THE MANUAL BYPASS CANNOT CHANGE A COUNT ══════════════════════════════════════════════

class TheManualToggleChangesALabelAndNothingElse(unittest.TestCase):

    def setUp(self):
        fd, self.p = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(self.p)
        self.who = {"id": "TEST-WORLD", "p": "main"}

    def tearDown(self):
        for f in (self.p, self.p + ".tmp"):
            if os.path.exists(f):
                os.unlink(f)

    def test_a_declaration_needs_NO_witness(self):
        """Ruling #166 — *"manual anything is enough witness obivously"*. The door takes no
        corroboration argument and cannot be given one; a signature requirement would be a witness
        requirement wearing another name."""
        r = LA.manual_accept("sets", self.who, by="Dean", why="verified in game", path=self.p)
        self.assertTrue(r["ok"], r.get("why"))
        import inspect
        sig = set(inspect.signature(LA.manual_accept).parameters)
        for forbidden in ("witness", "witnesses", "corroboration", "evidence", "proof", "attacks"):
            self.assertNotIn(forbidden, sig,
                             "manual_accept grew a %r parameter — a manual toggle is witness-free "
                             "by his ruling" % forbidden)

    def test_it_RECORDS_who_when_and_which_ledger(self):
        """Witness-free is not record-free. Without these three a declaration cannot be audited,
        cannot be attributed, and applies to a world nobody named."""
        r = LA.manual_accept("runewords", self.who, by="Konyo", why="his own board",
                             path=self.p)["record"]
        self.assertEqual("runewords", r["ledger"])
        self.assertEqual("Konyo", r["by"])
        self.assertEqual(LA.world_key(self.who), r["world"])
        self.assertTrue(r["at"] and r["atIso"])

    def test_a_declaration_with_no_WORLD_is_refused(self):
        """A record with no world would accept a ledger on every board at once, including boards
        the declarer has never seen."""
        for bad in (None, {}, {"p": "main"}, "Dean"):
            self.assertFalse(LA.manual_accept("sets", bad, path=self.p)["ok"], repr(bad))

    # ── ⛔⛔ THE LOAD-BEARING LAW ──────────────────────────────────────────────────────────────
    def test_NOT_ONE_COUNT_MOVES_ACROSS_THE_TOGGLE(self):
        """[[d2r-ladder-doctrine]] — a profile toggle must never change a count. Proven by running
        the SAME classification with and without the declaration and comparing every field that is
        not a label. Exactly three keys may differ: provenance, why, manual.

        SABOTAGE: make _label_only() also write `row["seedRows"] = 0` (a plausible "it's accepted,
        so stop calling them seeded") -> this test names seedRows and fails.
        """
        t = LA.seed_table()
        g = t["seeds"]["_GRAIL_SEED"]
        store = dict((n, g["dates"][n]) for n in g["names"][:7])
        own = _board(stores={"d2r_foundLog": store, "d2r_setPieces": ["Mine"], "d2r_rwMade": {}})

        before = LA.classify_local(own=own, path=self.p)
        for led in LA.LEDGER_NAMES:
            LA.manual_accept(led, self.who, by="Konyo", why="accepted", path=self.p)
        after = LA.classify_local(own=own, path=self.p)

        LABELS = {"provenance", "why", "manual"}
        # REG-1893 - zip() over an empty (or a shorter) side compares nothing for the ledgers it drops
        for side, rep in (("before", before), ("after", after)):
            self.assertEqual(sorted(x["ledger"] for x in rep["ledgers"]), sorted(LA.LEDGER_NAMES),
                             "the %s report does not carry every ledger, so a moved count could go "
                             "unseen" % side)
        for b, a in zip(before["ledgers"], after["ledgers"]):
            self.assertEqual(LA.MANUAL, a["provenance"], b["ledger"])
            moved = sorted(k for k in set(b) | set(a) if b.get(k) != a.get(k))
            self.assertTrue(set(moved) <= LABELS,
                            "the manual toggle changed %s on the %s ledger. A toggle may change "
                            "what a ledger is CALLED and nothing it COUNTS."
                            % ([k for k in moved if k not in LABELS], b["ledger"]))

    def test_the_toggle_touches_exactly_one_verdict_key_in_the_SOURCE(self):
        """⚠ AN AST LAW, BECAUSE A TEXT LAW HERE WOULD BE WORTHLESS. The behavioural test above
        proves today's inputs; this proves the FUNCTION cannot assign a count on any input. In this
        repo a text-presence suite once passed 7/7 over a write under `if False:`, so reachability
        and assignment targets are read from the tree, not from the characters.

        SABOTAGE: add `row["rows"] = 0` inside _label_only -> this fails naming 'rows'.
        """
        tree = ast.parse(SRC)
        fn = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "_label_only"]
        self.assertTrue(fn, "_label_only is gone or renamed — fix this guard before trusting it")
        allowed = {"provenance", "manual", "why"}
        written = set()
        for node in ast.walk(fn[0]):
            if not isinstance(node, ast.Assign):
                continue
            for tgt in node.targets:
                if isinstance(tgt, ast.Subscript) and isinstance(tgt.value, ast.Name) \
                        and tgt.value.id == "row":
                    k = tgt.slice
                    written.add(k.value if isinstance(k, ast.Constant) else "<computed>")
        self.assertTrue(written, "_label_only assigns nothing to the row — the toggle is inert")
        self.assertTrue(written <= allowed,
                        "the manual toggle writes %s onto the ledger row. Only %s may change."
                        % (sorted(written - allowed), sorted(allowed)))

    def test_the_declaration_is_per_LEDGER_and_per_WORLD(self):
        """One acceptance must not silence the other two ledgers, or another person's board."""
        LA.manual_accept("sets", self.who, by="Dean", path=self.p)
        own = _board(stores={"d2r_foundLog": {}, "d2r_setPieces": [], "d2r_rwMade": {}})
        r = LA.classify_local(own=own, path=self.p)
        self.assertEqual(LA.MANUAL, _led(r, "sets")["provenance"])
        self.assertNotEqual(LA.MANUAL, _led(r, "uniques")["provenance"])
        other = LA.classify_local(own=_board(route={"id": "SOMEONE-ELSE", "p": "main"},
                                             stores={"d2r_setPieces": []}), path=self.p)
        self.assertNotEqual(LA.MANUAL, _led(other, "sets")["provenance"],
                            "a declaration on one world silenced another world's ledger")

    def test_a_revocation_is_a_ROW_and_erases_nothing(self):
        """"he never declared it" and "he declared it and changed his mind" are different facts.
        Deleting the first row would destroy testimony."""
        LA.manual_accept("sets", self.who, by="Dean", path=self.p, at=1000)
        LA.manual_revoke("sets", self.who, by="Dean", path=self.p, at=2000)
        recs = LA.manual_load(self.p)["records"]
        self.assertEqual(2, len(recs), "the revocation overwrote the acceptance")
        self.assertTrue(recs[0]["accepted"])
        self.assertFalse(recs[1]["accepted"])
        self.assertIsNone(LA.manual_for("sets", self.who, path=self.p))

    def test_a_CORRUPT_record_refuses_to_be_written_over(self):
        """SABOTAGE: leave garbage in the file. Silently starting fresh would revoke every
        declaration a person ever made and re-flag their board, with no author."""
        with io.open(self.p, "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        doc = LA.manual_load(self.p)
        self.assertTrue(doc["corrupt"])
        self.assertIn("UNKNOWN, not absent", doc["why"])
        self.assertFalse(LA.manual_accept("sets", self.who, path=self.p)["ok"],
                         "a corrupt record was overwritten, destroying the earlier declarations")


# ══ 5. THE EXIT PATH — the half he asked for FIRST ═════════════════════════════════════════════

class TheExitPathIsRealAndOrDERED(unittest.TestCase):

    def test_every_step_names_a_real_control_in_bible_html(self):
        """⚠ A WARNING WITH NO EXIT IS A LABEL, NOT A TOOL, and an exit that names a control which
        does not exist is worse. Every anchor below is looked up in the real file.
        SABOTAGE: rename any of these handlers in bible.html -> this fails naming it."""
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8",
                     errors="replace") as fh:
            src = fh.read()
        for anchor in ("d2r_ownerClaim", "window._d2rUnseed = function(){",
                       "window._d2rUnseedRestore", "window._uniqueResetAsk",
                       "d2r_ledgerName", "d2r_unseedBackup"):
            self.assertIn(anchor, src, "the exit path cites %r and bible.html does not contain "
                                       "it — the card would send him to a control that is gone"
                                       % anchor)

    def test_the_un_seed_door_names_the_ledger_BEFORE_it_strips(self):
        """⚠ THE ORDER IS LOAD-BEARING AND bible.html:10063 records why: naming last meant a throw
        part-way through left the store STRIPPED AND UNNAMED, the heuristic re-resolved it to
        KonyoEndgame, and the floors re-seeded everything just removed. Read from the real body,
        anchored at both ends."""
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8",
                     errors="replace") as fh:
            src = fh.read()
        body = _between(src, "window._d2rUnseed = function(){", "window._d2rUnseedRestore")
        self.assertIsNotNone(body, "the un-seed door is gone or renamed")
        i_name = body.find("setItem('d2r_ledgerName'")
        i_strip = body.find("strip('d2r_foundLog'")
        self.assertGreater(i_name, -1, "the un-seed no longer names the ledger at all")
        self.assertGreater(i_strip, -1, "the un-seed no longer strips the uniques store")
        self.assertLess(i_name, i_strip,
                        "the ledger is named AFTER the strip again — a half-finished un-seed then "
                        "leaves an unnamed store that re-seeds itself on the next load")

    def test_the_uniques_reset_does_not_touch_sets_or_runewords(self):
        """Konyo's split — *"sets and runewords has been verified by him already"* — only works if
        the narrow door really is narrow."""
        steps = LA.exit_path("uniques")["steps"]
        narrow = [s for s in steps if s["ledgers"] == ["uniques"]]
        self.assertTrue(narrow, "there is no uniques-only exit, so the only way out is all three")
        self.assertNotIn("sets", LA.exit_path("sets")["steps"][0].get("ledgers", []) and [] or [])
        for s in LA.exit_path("sets")["steps"]:
            self.assertIn("sets", s["ledgers"])

    def test_the_two_kinds_of_exit_are_not_confused(self):
        """"stop it happening" and "undo what happened" are different jobs, and a card offering
        only the first leaves the rows in place while claiming they were removed."""
        steps = LA.exit_path()["steps"]
        self.assertTrue(any(s["removesRows"] is False for s in steps))
        self.assertTrue(any(s["removesRows"] is True for s in steps))
        for s in steps:
            self.assertTrue(s["reversible"], "step %d does not say whether it can be undone"
                                             % s["n"])

    def test_an_unknown_ledger_gets_no_exit_path(self):
        self.assertFalse(LA.exit_path("uniqes")["ok"])


# ══ 6. THE HEART — both halves REGISTERED, not merely defined ══════════════════════════════════

class TheHeartIsWiredNotJustBuilt(unittest.TestCase):

    def test_the_corroborator_invariant_is_in_BUILDERS(self):
        """⚠ THE MOST REPEATED DEFECT IN THIS REPO. `_inv_the_deleter_is_never_looser_than_the_
        planner` sat in corroborate.py for its whole life, was graded proven=True by the
        self-proving surface, and was never once evaluated by run(). A check defined and not
        registered runs NEVER."""
        import corroborate as C
        names = {getattr(b, "__name__", "") for b in C.BUILDERS}
        self.assertIn("_inv_every_seed_the_authority_NAMES_has_a_door_that_can_REMOVE_it", names,
                      "the seed/exit-door invariant is defined and never RUN")

    def test_the_invariant_demands_EQUALITY_and_can_go_BOTH_ways(self):
        """`<=` would concede one direction. A door that handles a seed nobody counts deletes more
        than the card promised; a seed nobody can remove makes the card's advice fail silently."""
        import corroborate as C
        spec = C._inv_every_seed_the_authority_NAMES_has_a_door_that_can_REMOVE_it()
        self.assertEqual("==", spec[-1])
        self.assertIsNotNone(spec[4](), "the LEFT side is UNKNOWN on this tree")
        self.assertIsNotNone(spec[6](), "the RIGHT side is UNKNOWN on this tree")
        self.assertEqual(spec[4](), spec[6](),
                         "a seed exists that the un-seed door cannot remove, or the reverse")

    def test_the_invariant_goes_RED_when_a_seed_has_no_door(self):
        """⚠ THE SABOTAGE, AND IT IS THE WHOLE POINT. A law never seen red is measuring nothing.
        Declaring a sixth anchor that the un-seed door has never heard of must part the sides.
        MEASURED: 5 == 5 today; with the sabotage, 6 != 5."""
        import corroborate as C
        spec = C._inv_every_seed_the_authority_NAMES_has_a_door_that_can_REMOVE_it()
        left, right = spec[4], spec[6]
        base_l, base_r = left(), right()
        self.assertEqual(base_l, base_r)
        LA.SEED_ANCHORS["_SIXTH_SEED"] = "const _SIXTH_SEED = {"
        LA._SEED_CACHE["key"] = None
        try:
            # the anchor matches nothing, so the parse REFUSES and the left goes UNKNOWN --
            # which must also break the equality rather than quietly holding
            self.assertIsNone(left(),
                              "a declared seed that cannot be found still produced a COUNT")
            st = C.check_one(
                C._inv_every_seed_the_authority_NAMES_has_a_door_that_can_REMOVE_it)["state"]
            self.assertNotEqual(C.AGREE, st,
                                "the invariant AGREED while a declared seed could not be parsed")
        finally:
            LA.SEED_ANCHORS.pop("_SIXTH_SEED", None)
            LA._SEED_CACHE["key"] = None
        self.assertEqual(base_l, left(), "the sabotage was not cleanly reverted")

    def test_the_invariant_goes_RED_when_the_DOOR_loses_a_seed(self):
        """The other direction, driven on the right side: a door body that reaches fewer seeds than
        are declared must disagree. Sabotaged by pointing the reader at a body with one seed
        removed, which is what deleting a `strip()` call would do."""
        import corroborate as C
        import re as _re
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8",
                     errors="replace") as fh:
            src = fh.read()
        body = _between(src, "window._d2rUnseed = function(){", "window._d2rUnseedRestore")
        full = set(_re.findall(r"window\.(_[A-Z][A-Z0-9_]*_SEED)\b", body))
        maimed = set(_re.findall(r"window\.(_[A-Z][A-Z0-9_]*_SEED)\b",
                                 body.replace("window._RWC_SEED", "window.__gone")))
        self.assertEqual(len(full) - 1, len(maimed),
                         "the sabotage did not actually remove a seed from the door's reach — "
                         "PRINT THE MATCH COUNT before trusting a green sabotage")
        spec = C._inv_every_seed_the_authority_NAMES_has_a_door_that_can_REMOVE_it()
        self.assertNotEqual(spec[4](), len(maimed),
                            "a door reaching one seed fewer would still equal the declared count")

    def test_the_doctor_row_is_in_CHECKS(self):
        """Same law, other half of the heart: a doctor check that is not in CHECKS never runs."""
        import console_doctor as D
        names = [n for n, _ in D.CHECKS]
        self.assertIn("ledger provenance", names,
                      "the provenance check is defined and never registered")
        fns = dict(D.CHECKS)
        self.assertIs(fns["ledger provenance"], D._check_every_ledger_can_say_WHERE_IT_CAME_FROM)

    def test_the_doctor_row_is_a_NAME_FN_tuple(self):
        """v2228's scar: two checks were added as BARE FUNCTIONS and broke `for n, fn in CHECKS`
        unpacking in nine places at once."""
        import console_doctor as D
        for row in D.CHECKS:
            self.assertEqual(2, len(row), "a CHECKS entry is not a (name, fn) pair: %r" % (row,))
            self.assertTrue(callable(row[1]))

    def test_the_doctor_row_cannot_report_a_bare_boolean(self):
        """Every check answers OK / MISSING / UNKNOWN with a sentence. A bare True would collapse
        "I could not check" into "it is fine"."""
        import console_doctor as D
        st, say = D._check_every_ledger_can_say_WHERE_IT_CAME_FROM()
        self.assertIn(st, (D.OK, D.MISSING, D.UNKNOWN))
        self.assertIsInstance(say, str)
        self.assertGreater(len(say), 40, "the row gives no reason, so it is not actionable")

    # ── ⛔ NO WILSON LOCK ON A STATE ───────────────────────────────────────────────────────────
    def test_no_wilson_lock_was_invented_for_the_seed_state(self):
        """A wilson score belongs on a claim that can be ATTACKED. "Dean is on the owner's seed" is
        a READING the board publishes, not a claim a sabotage can refute — giving it a score means
        manufacturing attacks, which inflates n and makes a state read as proven. That is the exact
        cheat `_hardening_gap` exists to refuse, and the same law already pins the river's motion.
        """
        try:
            import self_arming as SA
        except Exception:
            self.skipTest("self_arming unavailable")
        proves = getattr(SA, "PROVES", {}) or {}
        for bad in ("ledger.seeded", "ledger.provenance", "seed.state", "authority.state",
                    "ledger.onOwnerSeed", "dean.seeded"):
            self.assertNotIn(bad, proves,
                             "%s was declared as a lock. Whose seed a board is running on is a "
                             "STATE the board reports, not a claim attacks can refute." % bad)


# ══ 8. NAMESPACES — a figure names the world it was read from, and never crosses ═══════════════

class FiguresNeverMixAcrossWorlds(unittest.TestCase):
    """Konyo: *"and also not be mixing with the other consoles and profiles related"*."""

    def test_all_six_worlds_resolve(self):
        cases = [({"pfx": "", "p": "main"}, LA.OWNER_MAIN),
                 ({"pfx": "", "p": "ladder"}, LA.OWNER_LADDER),
                 ({"pfx": "L·", "p": "main"}, LA.OWNER_LADDER),
                 ({"pfx": "I·77f64154·", "p": "main"}, LA.GUEST_MAIN),
                 ({"pfx": "IL·77f64154·", "p": "ladder"}, LA.GUEST_LADDER),
                 ({"pfx": "W·", "p": "main"}, LA.COUSIN_MAIN),
                 ({"pfx": "WL·", "p": "ladder"}, LA.COUSIN_LADDER)]
        for route, want in cases:
            self.assertEqual(want, LA.namespace_of(route)["key"], repr(route))

    def test_an_unrecognised_world_is_UNKNOWN_never_the_owners(self):
        """⚠ THE DIRECTION THAT COSTS SOMETHING. Defaulting an unreadable prefix to owner-main is
        how a GUEST world's empty keys get published under his nickname — the v2163 defect."""
        for bad in ({"pfx": "??", "p": "main"}, {"p": "main"}, {"pfx": ""}, None, "owner"):
            n = LA.namespace_of(bad)
            self.assertIsNone(n["key"], repr(bad))
            self.assertTrue(n["why"], "an unknown world gave no reason")

    def test_a_CROSS_WORLD_comparison_is_REFUSED(self):
        """SABOTAGE: ask it to compare owner-main against guest-main. It must decline, not subtract.
        A difference between two worlds is a well-formed integer describing neither board."""
        a = LA.figure(1, "x", LA.LIVE, namespace=LA.namespace_of({"pfx": "", "p": "main"}))
        b = LA.figure(1, "y", LA.LIVE,
                      namespace=LA.namespace_of({"pfx": "I·abcdef01·", "p": "main"}))
        ok, why = LA.compare_figures(a, b)
        self.assertFalse(ok)
        self.assertIn("different worlds", why)
        ok2, _ = LA.compare_figures(a, a)
        self.assertTrue(ok2, "it refuses a same-world comparison too, so it refuses everything")

    def test_an_unknown_world_cannot_be_compared_either(self):
        a = LA.figure(1, "x", LA.LIVE, namespace=LA.namespace_of({"pfx": "", "p": "main"}))
        b = LA.figure(1, "y", LA.LIVE, namespace=LA.namespace_of(None))
        self.assertFalse(LA.compare_figures(a, b)[0])

    def test_the_ledger_name_key_is_documented_as_world_INVARIANT(self):
        """⚠ A REFUTATION KEPT ON PURPOSE. d2r_ledgerName is written RAW at five sites and ROUTED at
        one (bible.html:19557), which looks like a defect: a ladder profile would name a PREFIXED
        key while the resolver reads the bare one. It is NOT — LSR.key() prefixes only keys in
        _LP_FORKED or _WP_FORKED and this key is in neither, so routed and raw are the same key in
        all six worlds. Pinned here against the real file so the refutation cannot rot."""
        self.assertIn("d2r_ledgerName", LA.NAMESPACE_INVARIANT_KEYS)
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8",
                     errors="replace") as fh:
            src = fh.read()
        lp = _between(src, "window._LP_FORKED = new Set([", "window._WP_FORKED")
        wp = _between(src, "window._WP_FORKED = new Set(", ";")
        self.assertIsNotNone(lp)
        self.assertIsNotNone(wp)
        # ⚠⚠ MEMBERSHIP, NOT TEXT — AND THIS GATE SPENT A DAY RED FOR THE WRONG REASON.
        # It asserted the key did not appear ANYWHERE in the block. v3196 then added a comment
        # INSIDE `_LP_FORKED` explaining the very thing this law protects — "`_D2R_LEDGER` reads
        # `d2r_ledgerName` from raw storage on purpose — it is the INSTALL's name, not the
        # profile's" — and the substring matched the explanation. MEASURED: `_LP_FORKED` has 52
        # members and `d2r_ledgerName` is not one of them; `_WP_FORKED` has 12 and does not
        # mention it at all. Nothing was ever world-forked.
        #
        # So a correct comment, written to stop someone making this mistake, turned the guard
        # against the code it was guarding. That is this repo's most-repeated gate defect and it
        # has its own scar: a guard that reads SOURCE fails on its own reach before it fails on
        # the product. [[feedback-comments-vs-code]] [[source-reading-guard]]
        def _members(blk):
            """The Set's actual string literals, comments stripped. -> set"""
            t = re.sub(r"/\*.*?\*/", "", blk, flags=re.S)      # block comments
            t = re.sub(r"//[^\n]*", "", t)                     # line comments
            return set(re.findall(r"""['\"]([A-Za-z0-9_\u00b7]+)['\"]""", t))
        for blk, name in ((lp, "_LP_FORKED"), (wp, "_WP_FORKED")):
            mem = _members(blk)
            self.assertGreater(
                len(mem), 5,
                "only %d member(s) parsed out of %s, so this law is measuring its own reader "
                "rather than the Set — UNKNOWN, not clean" % (len(mem), name))
            self.assertNotIn("d2r_ledgerName", mem,
                             "d2r_ledgerName has been added to %s — it is now world-forked, the "
                             "raw/routed writes really do diverge, and bible.html:19557 must be "
                             "revisited" % name)


# ══ 9. AGE OF THE THING, NOT THE FETCH ═════════════════════════════════════════════════════════

class AFrozenConstantIsNeverFresh(unittest.TestCase):
    """⚠⚠ THE SINGLE MOST LIKELY WAY FOR THIS WHOLE FIX TO BE QUIETLY VACUOUS."""

    def test_a_frozen_constant_is_ageKnown_False_EVEN_WITH_A_TIMESTAMP(self):
        """SABOTAGE: hand the seed figure a perfectly good `at` of right now. Re-parsing bible.html
        makes the READ fresh and leaves the VALUE as old as its transcription, so the KIND decides
        and not the presence of a timestamp. Without this the watchdog reports every seed as
        seconds old forever while it drifts by fifty finds."""
        f = LA.figure(245, "bible.html", LA.FROZEN, at=LA._now_ms())
        self.assertFalse(f["ageKnown"], "a hardcoded constant reported a KNOWN age")
        self.assertIsNone(f["ageMs"], "a hardcoded constant reported an age in ms")
        self.assertIn("exactly as old", f["why"])

    def test_a_live_read_with_a_timestamp_IS_dated(self):
        """The other direction — without it the rule above is just a blanket refusal."""
        f = LA.figure(292, "board", LA.LIVE, at=LA._now_ms())
        self.assertTrue(f["ageKnown"])
        self.assertIsNotNone(f["ageMs"])

    def test_an_UNDATED_beacon_is_UNKNOWN_not_fresh(self):
        f = LA.figure(1, "beacon:x", LA.BEACON, at=None)
        self.assertFalse(f["ageKnown"])
        self.assertIsNone(f["ageMs"])

    def test_the_stale_threshold_is_ABOVE_the_healthy_ceiling(self):
        """[[feedback-threshold-above-the-ceiling]] in both directions: a line under the floor cries
        wolf on healthy data and one over the ceiling never fires. The ceiling is the real pipeline
        — beacon period + tally TTL + fleet cache — and the line is a multiple of it."""
        c = LA.beacon_ceiling_ms()
        self.assertGreater(c["staleMs"], c["ceilingMs"],
                           "the stale line sits at or below the age a HEALTHY figure reaches, so "
                           "it would fire on every normal tick")
        self.assertGreaterEqual(c["parts"]["multiple"], 2)
        self.assertGreater(c["ceilingMs"], 0)

    def test_the_threshold_reads_the_LIVE_constant_not_a_copy(self):
        """SABOTAGE: move control_app._TALLY_TTL_S and the ceiling must move with it. A threshold
        holding its own copy of a period is a threshold that silently stops matching the pipeline
        it grades. [[copy-drift]]"""
        import control_app as CA
        real = CA._TALLY_TTL_S
        base = LA.beacon_ceiling_ms()["ceilingMs"]
        try:
            CA._TALLY_TTL_S = real + 100.0
            moved = LA.beacon_ceiling_ms()["ceilingMs"]
        finally:
            CA._TALLY_TTL_S = real
        self.assertEqual(base + 100000.0, moved,
                         "the ceiling did not follow control_app's own TTL, so it is a copy")
        self.assertEqual(base, LA.beacon_ceiling_ms()["ceilingMs"], "sabotage not reverted")

    def test_a_frozen_constant_is_graded_by_DRIFT(self):
        """You cannot date the seed; you CAN measure how far behind the live figure it has fallen.
        MEASURED on his board: uniques 246 vs a live 292. Asserts the RULE, not the 46.

        ⚠ v3313 — THE VEHICLE MOVED, THE RULE DID NOT. This drove the rule through `uniques`, and
        uniques is the one ledger whose live figure is a ROSTER WALK rather than len(store), so
        that subtraction was never valid and now reports no drift at all. `sets` is a store length
        (`usesStoreLength: True`), so a seed 40 behind it is a real 40. Pin the law, not the
        roster. [[regression-guard]]"""
        t = LA.seed_table()
        n = len(LA.seed_names_for("sets", table=t)[0])
        own = _board(counts={"chronFound": None, "setPieces": n + 40, "runewordsMade": 0,
                             "chronTotal": None, "setsTotal": None, "runewordsTotal": None})
        st = LA.staleness(own=own, fleet={}, table=t)
        row = [r for r in st["rows"] if r["name"] == "sets seed"][0]
        self.assertEqual(LA.FROZEN, row["kind"])
        self.assertEqual(40, row["drift"])
        self.assertTrue(row["stale"], "a seed 40 behind the live figure was not called stale")
        self.assertFalse(row["ageKnown"])

    def test_a_LEVEL_seed_is_not_stale_and_an_UNMEASURABLE_one_is_UNKNOWN(self):
        t = LA.seed_table()
        # ⚠ v3313 — `sets`, and `assertIs(False, ...)` rather than assertFalse. Driven through
        # `uniques` this half went INERT the moment that ledger stopped being compared: its
        # `stale` became None, and `assertFalse(None)` passes while measuring nothing. A level
        # seed must be measured-and-level, which is False — never merely not-True.
        n = len(LA.seed_names_for("sets", table=t)[0])
        st = LA.staleness(own=_board(counts={"setPieces": n}), fleet={}, table=t)
        self.assertIs(False, [r for r in st["rows"] if r["name"] == "sets seed"][0]["stale"],
                      "a seed level with its live figure must read measured-and-level; None here "
                      "would mean this case cannot tell level from ungraded")
        # nothing live to compare against -> drift None -> stale None, NEVER False
        st2 = LA.staleness(own={"ok": False}, fleet={}, table=t)
        # REG-1893 - with no FROZEN row in st2 the filter below admits nothing and the half asks nothing
        self.assertIn(LA.FROZEN, [r["kind"] for r in st2["rows"]],
                      "staleness() with nothing live published no FROZEN seed row to judge")
        for r in st2["rows"]:
            if r["kind"] == LA.FROZEN:
                self.assertIsNone(r["stale"],
                                  "%s was graded without a live figure to compare against, so a "
                                  "verdict was invented" % r["name"])

    def test_the_watchdog_walks_EVERY_ledger_not_just_the_seeds(self):
        """A seed-specific check leaves the next frozen constant to rot identically."""
        st = LA.staleness(own=_board(counts={"chronFound": 1, "setPieces": 1, "runewordsMade": 1}),
                          fleet={})
        kinds = {r["kind"] for r in st["rows"]}
        self.assertIn(LA.FROZEN, kinds)
        self.assertIn(LA.LIVE, kinds)
        for led in LA.LEDGER_NAMES:
            self.assertIn("%s seed" % led, [r["name"] for r in st["rows"]])


# ══ 10. THE CANONICAL FIGURE — which store, which rule, which world ════════════════════════════

class OneSourceForTheSetsFigure(unittest.TestCase):
    """Konyo: *"sets also needs to be fetched from the right data so it also renders like the sets
    tab 123/135 counter"*."""

    def test_the_rule_is_the_INTERSECTION_not_the_store_length(self):
        """A numerator that can exceed its own denominator is not a progress figure.
        SABOTAGE: a store holding a name absent from the roster — the exact direction his own data
        never takes, which is why it must be exercised here. [[gate-blind-to-unexercised-input]]"""
        roster, _ = LA._roster_for("sets")
        self.assertTrue(roster, "no sets roster on this machine — this law examined nothing")
        store = list(roster)[:5] + ["Not On Any Roster At All"]
        c = LA.ledger_figure("sets", own=_board(stores={"d2r_setPieces": store}))
        self.assertTrue(c["ok"])
        self.assertEqual(5, c["byIntersection"])
        self.assertEqual(6, c["byStoreLength"])
        self.assertEqual(5, c["value"], "the canonical figure is not the intersection")
        self.assertFalse(c["agree"], "the divergent direction did not register as a disagreement")
        self.assertEqual(1, c["outsideRosterN"])
        self.assertIn("Not On Any Roster At All", c["outsideRoster"])

    def test_a_missing_roster_RELABELS_the_rule_rather_than_counting_silently(self):
        """⚠ An unreadable roster is UNKNOWN, never a licence to count by another rule under the
        same label. When there is no roster the rule string itself changes and says why."""
        c = LA.ledger_figure("runewords", own=_board(stores={"d2r_rwMade": {"Spirit": "x"}},
                                                 counts={"runewordsMade": 1,
                                                         "runewordsTotal": 2}))
        if c["rule"] == "store-length":
            self.assertIn("no", c["ruleWhy"].lower())
            self.assertIsNone(c["byIntersection"],
                              "an intersection was reported with no roster to intersect against")
        else:
            self.assertEqual(LA.COUNT_RULE, c["rule"])

    def test_a_ledger_nobody_counts_by_LENGTH_is_not_graded_on_it(self):
        """`d2r_foundLog` legitimately holds set pieces and other rows, and no surface publishes its
        length as the uniques numerator. Comparing them would be a finding about a method nobody
        uses — so `agree` is None, which is UNKNOWN-by-non-applicability, never a false red."""
        c = LA.ledger_figure("uniques", own=_board(stores={"d2r_foundLog": {"Wormskull": "x"}}))
        self.assertFalse(c["usesStoreLength"])
        self.assertIsNone(c["agree"])
        self.assertIn("NOT compared", c["why"])

    def test_it_cross_checks_against_the_BOARDS_OWN_figure(self):
        """⚠ THE SECOND WITNESS. `byIntersection` is computed here from the raw store and a roster
        file on this disk; `boardHave` was computed inside the board by its own code against its own
        roster. Two independent walks over one ledger. MEASURED live: sets 123 == 123, uniques
        292 == 292 — which is what makes the figure trustworthy rather than self-consistent."""
        roster, _ = LA._roster_for("sets")
        store = list(roster)[:7]
        c = LA.ledger_figure("sets", own=_board(stores={"d2r_setPieces": store},
                                            counts={"setPieces": 7, "setsTotal": len(roster)}))
        self.assertTrue(c["boardAgrees"])
        bad = LA.ledger_figure("sets", own=_board(stores={"d2r_setPieces": store},
                                              counts={"setPieces": 8, "setsTotal": len(roster)}))
        self.assertFalse(bad["boardAgrees"],
                         "the board and this machine disagreed and it was not noticed")

    def test_a_DIFFERENT_denominator_is_flagged_not_silently_used(self):
        """MEASURED: the board counts uniques against 403 and tv/unique_roster.json holds 398. A
        percentage from one drawn against the other is wrong, so the drift is named."""
        roster, _ = LA._roster_for("sets")
        c = LA.ledger_figure("sets", own=_board(stores={"d2r_setPieces": list(roster)[:3]},
                                            counts={"setPieces": 3, "setsTotal": len(roster) + 5}))
        self.assertIn("rosterDrift", c)
        self.assertIn("different rosters", c["rosterDrift"])

    def test_every_figure_names_the_world_it_came_from(self):
        c = LA.ledger_figure("sets", own=_board(stores={"d2r_setPieces": []}))
        self.assertEqual(LA.OWNER_MAIN, c["namespace"]["key"])


# ══ 11. HOW A BOARD CAME TO BE NAMED — the three states, and the one that is actionable ════════

class TheNamingStateIsSaidOutLoud(unittest.TestCase):

    def test_the_three_states_the_card_needs(self):
        own = _board(counts={"foundLog": 10, "owned": 0, "setPieces": 0})
        self.assertEqual(LA.UNNAMED_WITH_DATA, LA.name_state(own, stored_name="")["state"])
        self.assertEqual(LA.AUTO_NAMED, LA.name_state(own, stored_name="Ledger-77f64154")["state"])
        self.assertEqual(LA.NAMED_BY_HAND, LA.name_state(own, stored_name="Deans Own")["state"])

    def test_only_the_standing_contamination_is_ACTIONABLE(self):
        """The card must point at ONE state. Auto-named and hand-named boards need nothing done."""
        own = _board(counts={"foundLog": 10, "owned": 0, "setPieces": 0})
        self.assertTrue(LA.name_state(own, stored_name="")["actionable"])
        for nm in ("Ledger-77f64154", "Deans Own"):
            self.assertFalse(LA.name_state(own, stored_name=nm)["actionable"], nm)

    def test_unnamed_and_EMPTY_is_not_the_contaminated_state(self):
        """An empty unnamed board gets a NEW ledger from the heuristic, which is honest. Calling it
        contaminated would send a new user to a danger-zone button for nothing."""
        own = _board(counts={"foundLog": 0, "owned": 0, "setPieces": 0})
        st = LA.name_state(own, stored_name="")
        self.assertEqual(LA.UNNAMED_EMPTY, st["state"])
        self.assertFalse(st["actionable"])

    def test_WITHOUT_the_raw_key_it_says_DERIVED_and_names_what_is_missing(self):
        """⚠ THE CONSOLE CANNOT ANSWER THIS TODAY AND MUST NOT PRETEND TO. board_ownership publishes
        `ledgerName = window._D2R_LEDGER` (control_app.py:11824) — the RESOLVED value — so an
        unnamed board with a chronicle reports exactly what a hand-named one reports."""
        own = _board(counts={"foundLog": 10, "owned": 0, "setPieces": 0})
        st = LA.name_state(own)                       # no stored_name supplied
        self.assertFalse(st["storedNameKnown"])
        self.assertIn("DERIVED", st["why"])
        self.assertIn("_D2R_LEDGER", st["why"],
                      "the derivation does not name the field that is standing in for the key")

    def test_an_unanswered_board_is_UNKNOWN(self):
        st = LA.name_state({"ok": True, "onOwnerSeed": None, "counts": {}})
        self.assertEqual(LA.NAME_UNKNOWN, st["state"])
        self.assertFalse(st["actionable"])

    def test_the_derivation_does_not_fire_on_a_board_off_the_seed(self):
        own = _board(onOwnerSeed=False, seedsBelongHere=False,
                     counts={"foundLog": 10, "owned": 0, "setPieces": 0})
        self.assertEqual(LA.NAME_UNKNOWN, LA.name_state(own)["state"])


# ══ 12. TWO SURFACES, ONE NAME — the disagreement class ════════════════════════════════════════

class TheHeartStatesTheDisagreement(unittest.TestCase):

    def test_every_EXCLUDED_ledger_carries_a_real_reason(self):
        """An exemption with no reason is one nobody can audit, and it silently grows. Same law the
        river's by-design station list already carries."""
        for p in LA.surface_pairs():
            if p.get("comparable") is False:
                self.assertGreater(len(p["why"]), 20,
                                   "%s is excluded from the count/mask comparison with no real "
                                   "reason given" % p["ledger"])

    def test_the_uniques_mask_and_tally_stores_are_COMPARED_not_assumed(self):
        """Reads fleet_mask's own table rather than restating it, so a fix there moves this."""
        import fleet_mask as FM
        pairs = {p["ledger"]: p for p in LA.surface_pairs()}
        self.assertIn("uniques", pairs)
        self.assertEqual(FM.LEDGERS["uniques"]["store"], pairs["uniques"]["maskStore"])

    def test_the_cross_check_parts_when_a_store_holds_an_OFF_ROSTER_name(self):
        """⚠ THE SABOTAGE, WITH ITS MATCH COUNTS. A green sabotage is usually the sabotage's fault,
        so the numbers are asserted on both sides of it.
        MEASURED: baseline agreeN 2 / comparable 2; sabotage agreeN 0 / comparable 1."""
        import fleet_mask as FM
        roster, fp = FM.load_roster_for("sets")
        owned = list(roster)[:20]
        mask = FM.encode(owned, roster, fp)
        self.assertIsNotNone(mask, "the mask could not be encoded — this law examined nothing")
        good = {"online": [{"machine": "A", "nickname": "A",
                            "tally": {"ok": True, "sets": {"have": 20, "total": len(roster)}},
                            "masks": {"sets": mask}}], "offline": []}
        bad = {"online": [{"machine": "A", "nickname": "A",
                           "tally": {"ok": True, "sets": {"have": 21, "total": len(roster)}},
                           "masks": {"sets": mask}}], "offline": []}
        g = LA.mask_cross_check(fleet=good)
        b = LA.mask_cross_check(fleet=bad)
        self.assertEqual((1, 1), (g["agreeN"], g["comparableN"]), "the honest pair did not agree")
        self.assertEqual((0, 1), (b["agreeN"], b["comparableN"]),
                         "a board posting one more than its mask encodes was not caught")

    def test_an_undecodable_mask_is_UNKNOWN_not_a_disagreement(self):
        """A mask this machine cannot decode says nothing about that machine's honesty."""
        d = LA.mask_cross_check(fleet={"online": [{"machine": "A", "nickname": "A",
                                                   "tally": {"ok": True, "sets": {"have": 5}},
                                                   "masks": {"sets": {"v": "zz", "n": "1",
                                                                      "b": "!!", "have": "5"}}}],
                                       "offline": []})
        # REG-1893 - machine A's undecodable sets mask must produce a row, or the claim below judges nothing
        self.assertTrue(d["rows"], "mask_cross_check returned no row for machine A's mask: %r" % (d,))
        for r in d["rows"]:
            self.assertIsNone(r["popcount"])
            self.assertFalse(r["agree"])
            self.assertTrue(r["why"])

    def test_both_new_invariants_are_in_BUILDERS(self):
        import corroborate as C
        names = {getattr(b, "__name__", "") for b in C.BUILDERS}
        for n in ("_inv_a_posted_COUNT_and_its_own_MASK_agree",
                  "_inv_every_figure_pair_under_ONE_NAME_reads_ONE_STORE"):
            self.assertIn(n, names, "%s is defined and never RUN" % n)

    def test_the_count_mask_invariant_can_go_RED(self):
        """Driven through the real invariant's own left(), against a sabotaged fleet."""
        import corroborate as C
        import control_app as CA
        import fleet_mask as FM
        roster, fp = FM.load_roster_for("sets")
        mask = FM.encode(list(roster)[:20], roster, fp)
        spec = C._inv_a_posted_COUNT_and_its_own_MASK_agree()
        real = CA.fleet_presence
        try:
            CA.fleet_presence = lambda *a, **k: {
                "ok": True, "offline": [],
                "online": [{"machine": "A", "nickname": "A",
                            "tally": {"ok": True, "sets": {"have": 21, "total": len(roster)}},
                            "masks": {"sets": mask}}]}
            self.assertEqual(0, spec[4](), "a disagreeing fleet still counted as agreeing")
            self.assertEqual(1, spec[6](), "the comparable count did not see the sabotaged row")
        finally:
            CA.fleet_presence = real

    def test_an_empty_fleet_is_UNKNOWN_never_0_equals_0(self):
        import corroborate as C
        import control_app as CA
        spec = C._inv_a_posted_COUNT_and_its_own_MASK_agree()
        real = CA.fleet_presence
        try:
            CA.fleet_presence = lambda *a, **k: {"ok": True, "online": [], "offline": []}
            self.assertIsNone(spec[4](), "an empty fleet produced a count, so 0 == 0 would hold")
            self.assertIsNone(spec[6]())
        finally:
            CA.fleet_presence = real

    def test_the_one_name_one_store_law_can_go_BOTH_ways(self):
        """⚠ NOT PINNED TO TODAY'S DEFECT. This law is RED on the live tree because fleet_mask's
        `uniques` mask reads d2r_owned while the tally counts chronFound — but asserting "it is red"
        would freeze the defect into a law and fail the day someone fixes it. So both directions are
        driven synthetically instead, and the live state is reported by the doctor, not pinned here.
        [[regression-guard]] — pin the LAW, not the bytes."""
        import corroborate as C
        import fleet_mask as FM
        spec = C._inv_every_figure_pair_under_ONE_NAME_reads_ONE_STORE()
        real = dict(FM.LEDGERS)
        try:
            FM.LEDGERS.clear()
            FM.LEDGERS.update({"sets": dict(real["sets"])})
            self.assertEqual(spec[4](), spec[6](),
                             "with every mask reading its tally's store the sides still parted")
            FM.LEDGERS.update({"uniques": dict(real["uniques"], store="d2r_somewhere_else")})
            self.assertNotEqual(spec[4](), spec[6](),
                                "a mask reading a different store than its tally did not part the "
                                "sides — the law cannot see the defect it exists for")
        finally:
            FM.LEDGERS.clear()
            FM.LEDGERS.update(real)
        self.assertEqual(real, FM.LEDGERS, "the sabotage was not cleanly reverted")

    def test_the_staleness_doctor_row_is_in_CHECKS(self):
        import console_doctor as D
        names = [n for n, _ in D.CHECKS]
        self.assertIn("ledger staleness", names,
                      "the staleness watchdog is defined and never registered")
        self.assertIs(dict(D.CHECKS)["ledger staleness"],
                      D._check_no_ledger_FIGURE_has_gone_stale_unnoticed)

    def test_no_wilson_lock_was_invented_for_STALENESS_either(self):
        """A figure's age is a reading, not a claim attacks can refute — same rule as the seed
        state and the river's motion."""
        try:
            import self_arming as SA
        except Exception:
            self.skipTest("self_arming unavailable")
        proves = getattr(SA, "PROVES", {}) or {}
        for bad in ("ledger.stale", "ledger.staleness", "seed.drift", "figure.age",
                    "ledger.canonical", "ledger.namespace"):
            self.assertNotIn(bad, proves, "%s was declared as a lock" % bad)


# ══ 13. THE BACKUP IS THE LIVE TRUTH; THE SEED IS A FLOOR ══════════════════════════════════════

class PreferTheBackupOverTheSeed(unittest.TestCase):
    """Konyo: the seed must not be "refreshed"; the card must stop presenting a June constant as his
    current chronicle. MEASURED on his tree: 62 restore points, newest 45 min old, cadence 15-25
    min, counts chronFound 292 / setPieces 123 / runewordsMade 99 — against a seed of 246/108/99
    with no timestamp anywhere."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.route = {"id": "W1", "p": "main", "pfx": ""}

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d, ignore_errors=True)

    def _point(self, name, taken, route, counts=None, stores=None):
        with io.open(os.path.join(self.d, name), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"takenAt": taken, "route": route,
                                 "counts": counts or {"chronFound": 1},
                                 "allStores": stores if stores is not None else {}}))

    # ── ⚠⚠ THE LAW THAT MAKES AN ABSENCE READABLE ────────────────────────────────────────────
    def test_an_absence_means_two_OPPOSITE_things_and_the_code_tells_them_apart(self):
        """`d2r_ownerClaim` is missing from every dump on his board and he is unquestionably the
        owner — `_collectProgress()` strips six pointer keys by design. `d2r_ledgerName` is NOT one
        of them, and the exporter's rule (`if LSR.key(bare) === rk`) it satisfies in every world.
        So the SAME missing-key observation is worthless for one and decisive for the other, and
        without this distinction nothing could tell them apart.
        [[feedback-silence-is-not-evidence]] [[zero-needs-a-denominator]]"""
        self.assertIn("d2r_ownerClaim", LA.PROGRESS_DUMP_EXCLUDES)
        self.assertNotIn("d2r_ledgerName", LA.PROGRESS_DUMP_EXCLUDES)
        v, known = LA.stored_name_from_dump({"d2r_foundLog": "{}"})
        self.assertIsNone(v)
        self.assertTrue(known, "an exportable key's absence was not treated as evidence")
        v2, known2 = LA.stored_name_from_dump(None)
        self.assertFalse(known2, "a non-dump was read as proof the key is unset")

    def test_the_exclusion_list_matches_bible_htmls_OWN_pointer_map(self):
        """SABOTAGE-PROOF BY CONSTRUCTION: read the six keys out of `_collectProgress`'s PTRS map in
        the real file. If bible.html adds a seventh, this fails rather than silently treating a
        newly-stripped key's absence as evidence."""
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8",
                     errors="replace") as fh:
            src = fh.read()
        blk = _between(src, "const PTRS = {", "};")
        self.assertIsNotNone(blk, "the PTRS map is gone or renamed — fix this guard first")
        import re as _re
        keys = set(_re.findall(r"'([A-Za-z0-9_]+)'\s*:\s*1", blk))
        self.assertEqual(keys, set(LA.PROGRESS_DUMP_EXCLUDES),
                         "bible.html's pointer map and PROGRESS_DUMP_EXCLUDES have diverged: %s. "
                         "A key stripped by the exporter but not declared here would have its "
                         "absence read as proof it is unset."
                         % sorted(keys ^ set(LA.PROGRESS_DUMP_EXCLUDES)))

    def test_restore_points_are_filtered_BY_ROUTE(self):
        """Reading another world's backup as this board's is the cross-namespace mix arriving
        through a directory listing instead of a subtraction."""
        self._point("a.json", "2026-09-06_120000", self.route)
        self._point("b.json", "2026-09-06_130000", {"id": "OTHER", "p": "main", "pfx": ""})
        mine = LA.backup_points(directory=self.d, route=self.route)
        self.assertEqual(1, len(mine["points"]), "another world's restore point was included")
        self.assertEqual(2, len(LA.backup_points(directory=self.d)["points"]))

    def test_the_NEWEST_point_wins_and_carries_a_REAL_age(self):
        self._point("old.json", "2026-09-06_120000", self.route, {"chronFound": 1})
        self._point("new.json", "2026-09-06_130000", self.route, {"chronFound": 2})
        n = LA.newest_backup(directory=self.d, route=self.route)
        self.assertEqual("2026-09-06_130000", n["takenAt"])
        self.assertIsNotNone(n["at"], "a restore point carried no usable timestamp")
        self.assertIsNotNone(n["ageMs"])

    def test_an_unparseable_stamp_is_UNKNOWN_never_now(self):
        """SABOTAGE: a corrupt `takenAt`. Dating it `now()` would make the stalest possible record
        look like the freshest — the exact inversion this whole watchdog exists to prevent."""
        self.assertIsNone(LA._backup_ts("not a date"))
        self.assertIsNone(LA._backup_ts(None))
        self._point("bad.json", "garbage", self.route)
        n = LA.newest_backup(directory=self.d, route=self.route)
        self.assertIsNone(n["at"])
        self.assertIsNone(n["ageMs"], "an undated restore point was given an age")

    def test_an_unreadable_point_is_SKIPPED_not_counted_as_empty(self):
        with io.open(os.path.join(self.d, "broken.json"), "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        self._point("ok.json", "2026-09-06_130000", self.route)
        d = LA.backup_points(directory=self.d, route=self.route)
        self.assertEqual(1, len(d["points"]))

    def test_a_missing_directory_is_UNKNOWN_not_zero(self):
        d = LA.backup_points(directory=os.path.join(self.d, "__nope__"))
        self.assertFalse(d["ok"])
        self.assertIn("UNAVAILABLE", d["why"])

    # ── ⛔ THE SEED IS NEVER OFFERED AS A READING ─────────────────────────────────────────────
    def test_with_no_reading_available_the_SEED_is_REFUSED_as_a_source(self):
        """⚠ THE LOAD-BEARING REFUSAL. The seed is the floor the boot path re-asserts, not a record
        of what he has found. Quoting 246 as his uniques when the live figure is 292 IS the defect,
        and a fallback chain that ends at the seed would re-create it in the name of robustness."""
        p = LA.preferred_source(own={"ok": False, "route": {"id": "NOBODY", "p": "main", "pfx": ""}},
                                directory=self.d)
        self.assertIsNone(p["source"], "a source was named when neither reading existed")
        self.assertIsNone(p["counts"], "counts were produced with no reading behind them")
        self.assertIn("floor", p["why"])
        self.assertFalse(p["ageKnown"])

    def test_the_order_is_live_then_BACKUP(self):
        self._point("n.json", "2026-09-06_130000", self.route, {"chronFound": 7})
        live = LA.preferred_source(own={"ok": True, "boardLoaded": True, "route": self.route,
                                        "counts": {"chronFound": 9}}, directory=self.d)
        self.assertEqual(LA.LIVE, live["source"])
        closed = LA.preferred_source(own={"ok": False, "route": self.route}, directory=self.d)
        self.assertEqual(LA.BACKUP, closed["source"])
        self.assertEqual(7, closed["counts"]["chronFound"])
        self.assertTrue(closed["ageKnown"], "the backup was quoted without an age")

    def test_the_backup_is_a_DATED_reading_while_the_seed_is_not(self):
        """The distinction in one assertion: both describe his chronicle, only one can be dated."""
        self._point("n.json", "2026-09-06_130000", self.route, {"chronFound": 7})
        st = LA.staleness(own={"ok": True, "boardLoaded": True, "route": self.route,
                               "counts": {"chronFound": 7}}, fleet={})
        by = {r["name"]: r for r in st["rows"]}
        self.assertIn("uniques seed", by)
        self.assertFalse(by["uniques seed"]["ageKnown"],
                         "the frozen seed reported a known age")
        self.assertIn("newest restore point", by,
                      "the watchdog does not grade the restore point at all")

    def test_a_world_with_NO_restore_point_says_so_and_does_not_promote_the_seed(self):
        st = LA.staleness(own={"ok": True, "boardLoaded": True,
                               "route": {"id": "NOBODY", "p": "main", "pfx": ""},
                               "counts": {"chronFound": 1}}, fleet={})
        row = [r for r in st["rows"] if r["name"] == "newest restore point"][0]
        self.assertIsNone(row["value"])
        self.assertIsNone(row["stale"], "a missing restore point was graded rather than UNKNOWN")
        self.assertIn("not a substitute", row["why"])


# ══ 7. the module's own self-test, and it must parse ═══════════════════════════════════════════

class TheModuleProvesItself(unittest.TestCase):

    def test_selftest_is_green_and_every_row_is_a_sabotage(self):
        ok, rows = LA.selftest()
        self.assertTrue(rows, "selftest examined nothing")
        self.assertTrue(ok, "selftest rows failed: %s" % [w for w, p in rows if not p])

    def test_it_still_parses(self):
        ast.parse(SRC)


RED_PROOF = [
    {"why": "REG-3376 - an offline peer's sentence prints its machine's host name again (GrokBot read it on his State panel)",
     "file": "tv/ledger_authority.py",
     "find": "\"again.\" % (who, _local_when(f[\"lastSeen\"])))",
     "replace": "\"again.\" % (who + \" (\" + f[\"machine\"] + \")\", _local_when(f[\"lastSeen\"])))",
     "matches": 1},
    {"why": "REG-3376 - a peer's last report is printed as raw UTC ISO again",
     "file": "tv/ledger_authority.py",
     "find": "    return d.astimezone().strftime(\"%Y-%m-%d %H:%M\") + \" (this PC's clock)\"\n",
     "replace": "    return s\n", "matches": 1},
    {"why": "REG-3376 - a stamp with no zone is guessed into this PC's clock",
     "file": "tv/ledger_authority.py",
     "find": "    if d.tzinfo is None:\n        return s\n", "replace": "", "matches": 1},
    {
        "why": "#227 - a peer that went silent mid-relaunch reads 'cannot tell which' again: the ALT box's relaunch death looks like a machine that was switched off",
        "file": "ledger_authority.py",
        "find": "            f[\"diedRelaunching\"] = bool(_ver and _dv and _dv != _ver and _rl.get(\"armed\") and _rl.get(\"may\"))\n",
        "replace": "            f[\"diedRelaunching\"] = False\n",
        "matches": 1,
    },
    {
        'why': 'ledger_authority.classify_row computes the fleet-side deficit as the SIGNED `row["have"] - seed_n` — the one expression that lets Dean\'s runewords read -5 ("five seeded rows are MISSING from his store") instead of a comfortable 0. Clamping it with max(0, ...) is the exact real-world defect the law exists for: the figure stays a number, but the sign and the "MISSING" sentence both vanish. It is the live expression, not a comment and not a shared constant — the test derives its own seed size from LA.seed_names_for("runewords"), so only the subtraction moves. MATCHES=1 in ledger_authority.py.  MEASURED: untampered python3 test_ledger_authority.py -> Ran 89 tests in 0.872s / OK (green); tampered (all 1) python3 test_ledger_authority.py -> Ran 89 tests / FAILED (failures=2): FleetRowsAreDerive; reddened law test_ledger_authority.FleetRowsAreDerivedAndSaySo.test_a_DEFICIT_is_re; ALONE python3 -m unittest test_ledger_authority.FleetRowsAreDerivedAndSaySo.test_a_DEFICIT_is_reported_negative_and_.',
        'file': 'ledger_authority.py',
        'find': 'row["have"] - seed_n',
        'replace': 'max(0, row["have"] - seed_n)',
        'matches': 1,
    },
]


class AMachineThatIsOffIsNotAFigureGoingStale(unittest.TestCase):
    """★ v3268 — THE DOCTOR COUNTED A SWITCHED-OFF LAPTOP AS A LEDGER FIGURE OUT OF DATE.

    MEASURED on his console 2026-09-17, from `/api/fleet`:

        online   GrokBot  v3266  uniques 310/403   age    0.5 min
        online   Konyo    v3267  uniques 309/403   age    1.0 min
        offline  Dean     v3156  uniques   0/403   age 3625 min   (last event: `boot`)

    The row said **"3 of 10 ledger figure(s) are out of date"**, and the third was Dean's Windows
    machine, off since 2026-09-15. `/api/fleet` ALREADY publishes that fact — it puts him in
    `offline`, not `online` — and `staleness()` concatenated the two rosters on its first line,
    discarding the one authority that knew before any grading happened.

    ⚠ And the figure it was grading is itself a placeholder: Dean's last beacon was a `boot`, so
    `uniques.have` was **0** while `sets.have` on the same payload was **131**. A board with 131
    of 135 sets does not have 0 of 403 uniques. So the sentence inflated a count he acts on with a
    number no action of his could fix, and buried the two he CAN act on. The `Wife PC` row is the
    proof the schema supports the honest shape: all of its figures are `null`, not 0.
    [[zero-needs-a-denominator]] [[label-outlived-referent]]

    This is the third time in one day that a thing which is correctly NOT RUNNING was graded as a
    thing that is BROKEN — v3265 (BLOCKED vs STOPPED), v3267 (UNBUILT vs DRY), and now this.
    """

    @staticmethod
    def _peer(nick, at_ms, have, offline):
        return {"nickname": nick, "machine": "%s-BOX" % nick, "t": "2026-09-15T00:24:28.324Z",
                "tally": {"ok": True, "at": at_ms,
                          "uniques": {"have": have, "total": 403}}}

    def _fleet(self, now_ms):
        fresh = now_ms - 30_000
        ancient = now_ms - 220_000_000          # ~61 hours
        return {
            "online": [self._peer("Konyo", fresh, 309, False)],
            "offline": [self._peer("Dean", ancient, 0, True)],
        }

    def _rows(self, fleet):
        """⚠⚠ v3270 — AND THIS FIXTURE READ HIS LIVE BACKUP DIRECTORY, which is the v2308 scar I
        cited while writing v3266 and then walked into inside my own test. `staleness()` calls
        `newest_backup()` unconditionally, so a "newest restore point" row from HIS MACHINE joined
        the fixture's rows — and when his last backup happened to be 83 minutes old, `staleHereN`
        came back 1 instead of 0 and both laws failed. They passed when I wrote them purely
        because a backup had run minutes earlier.

        A test whose verdict depends on when a daemon last ran on the machine it happens to
        execute on is not measuring the fixture. The beacon rows are what these laws are about, so
        the backup row is stubbed out — named and deliberate, never silently filtered.
        [[feedback-fixtures-never-touch-live-data]] [[a-gate-can-perturb-what-it-measures]]
        """
        _real = LA.newest_backup
        LA.newest_backup = lambda *a, **k: None
        try:
            st = LA.staleness(own=None, fleet=fleet, table={})
        finally:
            LA.newest_backup = _real
        # ⚠ the row still EXISTS — with no backup readable, `staleness` appends its honest
        # "no restore point for this world could be read ... UNKNOWN" row, which is correct and
        # carries stale=None so it counts toward nothing. What must be gone is its INFLUENCE:
        # a stale=True backup from his live machine. Asserting the NAME was absent was the wrong
        # law and it went red immediately, which is the test doing its job.
        _bk = [r for r in st["rows"] if r["name"] == "newest restore point"]
        # REG-1893 - the row still EXISTS (above); if it is renamed, the influence check below sees nothing
        self.assertTrue(_bk, "no 'newest restore point' row, so whether his live backup decides this "
                             "fixture is no longer checked")
        for r in _bk:
            self.assertIsNone(r.get("stale"),
                              "his live backup directory is still deciding this fixture's verdict")
        return {r["name"]: r for r in st["rows"]}, st

    def test_an_OFFLINE_peer_is_marked_and_kept_out_of_the_stale_count(self):
        import time
        now = int(time.time() * 1000)
        rows, st = self._rows(self._fleet(now))
        self.assertTrue(rows["Dean tally"]["machineOff"])
        self.assertFalse(rows["Konyo tally"]["machineOff"])
        self.assertEqual(st["staleHereN"], 0,
                         "a switched-off laptop was counted as a figure THIS console must fix")
        self.assertEqual(st["machineOffN"], 1)

    def test_an_ONLINE_peer_that_HAS_gone_quiet_is_still_STALE(self):
        """⚠⚠ THE LAW THE WHOLE CHANGE TURNS ON. A machine that is ON and has stopped reporting is
        the real fault this beacon check exists to catch, and it must not be able to hide behind
        the offline flag."""
        import time
        now = int(time.time() * 1000)
        fl = self._fleet(now)
        fl["online"] = [self._peer("Konyo", now - 220_000_000, 309, False)]
        rows, st = self._rows(fl)
        self.assertTrue(rows["Konyo tally"]["stale"])
        self.assertFalse(rows["Konyo tally"]["machineOff"])
        self.assertEqual(st["staleHereN"], 1,
                         "an ONLINE peer that went quiet stopped counting as stale")

    def test_machineOff_is_declared_by_the_ROSTER_not_inferred_from_age(self):
        """If age defined offline, the distinction would be circular: every stale beacon would
        excuse itself as 'switched off' and the check would grade nothing."""
        import time
        now = int(time.time() * 1000)
        fl = {"online": [self._peer("Dean", now - 220_000_000, 0, False)], "offline": []}
        rows, _ = self._rows(fl)
        self.assertFalse(rows["Dean tally"]["machineOff"],
                         "a peer on the ONLINE roster was called switched-off because it was old")
        self.assertTrue(rows["Dean tally"]["stale"])

    def test_a_peer_silent_MID_RELAUNCH_is_named_as_that(self):
        """#227 — the ALT box's last beacon (MEASURED 2026-09-24) ran v3417 with v3419 on disk and a
        relaunch armed, then went silent: its console died relaunching, and the heart called the
        machine switched off. Only a peer whose last word was 'about to replace myself' gets that
        diagnosis — a peer silent on matching versions stays 'cannot tell which'. DRIVEN."""
        import time
        now = int(time.time() * 1000)
        fleet = self._fleet(now)
        mid = self._peer("ALT", now - 220_000_000, 4, True)
        mid.update({"ver": "v3417", "diskVer": "v3419", "relaunch": {"armed": True, "may": True}})
        fleet["offline"].append(mid)
        fleet["offline"][0].update({"ver": "v3404", "diskVer": "v3404",
                                    "relaunch": {"armed": True, "may": True}})
        rows, _st = self._rows(fleet)
        self.assertTrue(rows["ALT tally"]["diedRelaunching"])
        self.assertIn("MID-RELAUNCH", rows["ALT tally"]["why"])
        self.assertIn("v3417", rows["ALT tally"]["why"])
        self.assertFalse(rows["Dean tally"]["diedRelaunching"],
                         "a peer silent on MATCHING versions was diagnosed as a relaunch death")
        self.assertIn("cannot tell which", rows["Dean tally"]["why"])

    def test_the_offline_peer_is_NAMED_and_never_merely_dropped(self):
        """⚠ the guard against the quiet corner — the same one v3267's UNBUILT needed. Removing a
        row from a count is only honest if the row still reaches him in words."""
        import time
        now = int(time.time() * 1000)
        rows, st = self._rows(self._fleet(now))
        self.assertIn("Dean tally", st["machineOff"])
        why = rows["Dean tally"]["why"]
        # #225 — the sentence may not GUESS the cause. "switched off" was measured false on 2026-09-24
        # (the ALT box was up; only its console had died). It must say what is known and that the
        # cause is not knowable from here.
        self.assertIn("has not reported since", why)
        self.assertIn("console is down OR the machine is off", why)
        self.assertNotIn("switched off", why, "the row guesses a cause it cannot see again")
        self.assertIn("LAST KNOWN", why)
        self.assertIn("2026-09-15", why, "the sentence does not say WHEN it was last heard from")
        # v3880 (REG-3376, GrokBot #6707144313) - his panel printed the peer's raw host name and a UTC ISO stamp
        self.assertNotIn("Dean-BOX", why, "the sentence prints the machine's host name again")
        self.assertNotIn("T00:24:28", why, "the sentence prints a raw UTC ISO stamp again")
        self.assertIn("(this PC's clock)", why)
        self.assertNotIn("0 of 403", why,
                         "it republished the boot-time placeholder as if it were Dean's tally")

    def test_a_last_report_reads_in_this_pcs_clock_and_an_unzoned_one_is_left_alone(self):
        """REG-3376 - a zoned stamp is said in local time; a stamp with no zone is never guessed into one"""
        import datetime as _dt
        z = LA._local_when("2026-09-15T00:24:28.324Z")
        want = _dt.datetime(2026, 9, 15, 0, 24, 28, tzinfo=_dt.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
        self.assertEqual(z, want + " (this PC's clock)")
        self.assertEqual(LA._local_when("2026-09-15T00:24:28"), "2026-09-15T00:24:28", "a zoneless stamp was guessed")
        self.assertEqual(LA._local_when("not a time"), "not a time")
        self.assertEqual(LA._local_when(""), "unknown")
        self.assertEqual(LA._local_when(None), "unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
