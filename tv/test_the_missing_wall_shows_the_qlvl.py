# -*- coding: utf-8 -*-
"""v2765 — THE MISSING WALL PRINTS THE QLVL, AND REFUSES TO PRINT ONE IT DOES NOT HAVE.

Konyo: *"for MISSING when it collapses open i want the q1-87 levels of the item in white same color
based but for sets.. because sets i see they dont have it... some items here in uniques are missing
the q level of there rarity. so for sets and uniques fix the rest."*

=== ⚠⚠ `qlvl: 0` IS A SENTINEL, NOT A LEVEL ===
MEASURED across all 5,925 item rows in `bible.html`, counted DISTINCT by name:

    high     126 of 127 carry a real qlvl        set        14 of 148
    grail     78 of  91                          special     0 of 4
    common    93 of 175                          uber        1 of 2

So a 0 means "this table never recorded one". Rendering it would put a confident **q0** under 134
set pieces and 96 uniques — a fabricated figure in the longest list on the page, which is exactly
where nobody would catch it. Absent renders NOTHING. [[zero-needs-a-denominator]]

=== ⚠⚠ AND THE 14 SET ROWS THAT DO CARRY ONE ARE NOT PIECES ===
They are set-level AGGREGATES — "Trang-Oul set (any piece)", "Immortal King set (any)", "Aldur's
Watchtower (any)". Hanging one on a piece is the trap v2299 named two comments up in the same file
("not a set-level average standing in for a piece"), and it is easy to fall into because
`_etaHours` legitimately DOES take a set aggregate as its fallback source. The qlvl reader takes no
fallback at all. Proven on real pixels: `_qlvlOf("Trang-Oul's Wing (shield)")` -> null while
`_qlvlOf("Trang-Oul set (any piece)")` -> 65.

=== ⚠ HALF OF WHAT HE ASKED FOR IS A DATA GAP, NOT A RENDER GAP ===
He said *"sets is missing the q level"* and wanted it fixed for sets too. **134 of the 148 set
entries have no qlvl anywhere in this page** — the per-piece rows carry `"tc":0,"qlvl":0`, and the
set structure holds art and dates but no level field. Nothing was found to render, and 134 values
were NOT written in from memory to make the wall look complete. That needs the game's own SetItems
table, which is a sourcing job. `test_the_set_piece_gap_is_still_real` pins the gap so that the day
the data arrives, this file goes RED and says so instead of the fix sitting unnoticed.

MEASURED ON REAL PIXELS after the change: the F-Uniques wall renders 392 missing rows and **296**
carry a q-chip, computed colour `rgb(255, 255, 255)`. The sets wall renders 135 rows and 1 chip,
which is the honest picture of the data underneath.
"""
import io
import json
import os
import tempfile
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

BIBLE = io.open(os.path.join(REPO, "bible.html"), encoding="utf-8").read()

#: every item row the page ships, as (name, tc, qlvl, tier)
ROWS = re.findall(r'"n":"([^"]{2,60})","tc":(\d+),"qlvl":(\d+),"tier":"([a-z]+)"', BIBLE)


def _best():
    """name -> (max qlvl seen, tier). Rows repeat per drop source."""
    best, tier = {}, {}
    for n, _tc, q, t in ROWS:
        best[n] = max(best.get(n, 0), int(q))
        tier[n] = t
    return best, tier


def _run_real_reader(names):
    """Run the SHIPPED _etaIdx + _qlvlOf in node against the SHIPPED rows. -> dict|None

    ⚠ THE REAL FUNCTION, NOT A PYTHON RE-IMPLEMENTATION. A second copy of the sentinel rule would
    pass while the page still printed q0. The item source is stubbed — that is the seam — but the
    logic under test is the file's own bytes.

    ⚠ `window._regKey` IS DELIBERATELY LEFT UNDEFINED so the reader takes its documented fallback
    (`String(name).toLowerCase()`). That is a real branch of the real function, and stubbing a fake
    _regKey would test a key rule this file does not own.
    """
    a = BIBLE.find("  var _etaIdxCache = null;")
    b = BIBLE.find("  window._qlvlOf = _qlvlOf;")
    if a < 0 or b < 0 or b < a:
        raise AssertionError("REG-1900 - the subject this harness drives is gone (_etaIdxCache / window._qlvlOf): a renamed subject is a FAILURE, never a skip")
    slice_ = BIBLE[a:b + len("  window._qlvlOf = _qlvlOf;")]
    items = [{"n": n, "qlvl": int(q), "tier": t} for n, _tc, q, t in ROWS]
    js = ("var window = {};\n"
          "window._allDropItems = function(){ return " + json.dumps(items) + "; };\n"
          + slice_ + "\n"
          "const _q = " + json.dumps(names) + ";\n"
          "const out = {}; for (const n of _q) out[n] = window._qlvlOf(n);\n"
          "console.log(JSON.stringify(out));")
    p = os.path.join(tempfile.gettempdir(), "qlvl_probe.js")
    io.open(p, "w", encoding="utf-8").write(js)
    try:
        r = subprocess.run(["node", p], capture_output=True, text=True, timeout=90)
    except FileNotFoundError:
        return None          # REG-1900 - the ONE skip: there is no node on this venue
    if r.returncode != 0:    # the subject would not run: that is the subject's failure, not the venue's
        raise AssertionError("REG-1900 - the shipped code would not run in node: %s" % (r.stderr or "")[-400:])
    return json.loads((r.stdout or "").strip().split("\n")[-1])


#: ⚠ THE ELEVEN WITH NO GAME-TABLE ROW UNDER ANY SPELLING. SET_QLVL_PROVENANCE.md records why each
#: is still 0 and refuses to map a near-spelling: the table says `Tal Rasha's Fire-Spun Cloth` where
#: the bible says `Fine-Spun Cloth`, and it holds four Aldur's pieces with no `Aldur's Rhythm` among
#: them. Some are probably naming errors in the bible rather than missing game data, and that wants
#: a HUMAN ruling — guessing would be the fabrication the sourcing rule exists to forbid.
#: v3884 (REG-3440) - EMPTY NOW. The eleven pieces with no game-table row trace to silospen (SET_QLVL_PROVENANCE.md, the
#: v3884 section; tv/data/silospen_qlvl_rotw30.json), spelled as the bible spells them. A piece that loses its level again
#: fails the ratchet below; a name added here needs its own provenance row first.
STILL_UNKNOWN_PIECES = ()
#: silospen's own quality levels (his 11-08 ruling: the qlvl is silospen's level)
SILO_LEVELS = json.load(io.open(os.path.join(HERE, "data", "silospen_qlvl_rotw30.json"), encoding="utf-8"))["levels"]


class TheMissingWallShowsTheQlvl(unittest.TestCase):

    # ── the guard can find its subject ───────────────────────────────────────────────────────
    def test_the_reader_is_still_here(self):
        self.assertIn("function _qlvlOf(name){", BIBLE, "the qlvl reader moved or was renamed")
        self.assertIn("window._qlvlOf = _qlvlOf;", BIBLE, "the reader is no longer exported")
        self.assertTrue(ROWS, "no item rows parsed out of the page — this file graded nothing")

    # ── ⚠⚠ THE LAWS, AGAINST THE REAL READER ────────────────────────────────────────────────
    def test_a_real_unique_gets_its_real_level(self):
        got = _run_real_reader(["Atma's Wail", "Stealskull", "Nagelring"])
        if got is None:
            self.skipTest("node unavailable, so the shipped reader could not be run — a skip is "
                          "NOT a pass and nothing here has been established")
        # v3884 (REG-3440) - silospen's level, read from the vendored pull. This case used to pin 51 / 35 / 7: Atma's Wail's
        # stray 51 and the WEAR levels of Stealskull (35) and Nagelring (7) - silospen's quality levels are 59 / 43 / 10.
        for n in ("Atma's Wail", "Stealskull", "Nagelring"):
            self.assertEqual(SILO_LEVELS[n]["level"], got.get(n), "%s does not read silospen's level" % n)
        self.assertEqual((59, 43, 10), tuple(SILO_LEVELS[n]["level"] for n in ("Atma's Wail", "Stealskull", "Nagelring")),
                         "premise: the vendored silospen levels moved - re-read them before trusting this case")

    def test_the_zero_sentinel_renders_NOTHING(self):
        """★ 0 is 'never recorded', and q0 under 230 rows would be a fabricated number in the one
        place nobody would check."""
        # ⚠⚠ v2795 — THE OLD PROBES STOPPED BEING ZEROS. This asked about `Death's Guard (belt)`
        # and `Arctic Binding (belt)` because, when it was written, no set piece carried a level at
        # all. v2787 sourced 1,477 of them from the game's own SetItems.txt, so those two now
        # answer 8 and 3 — REAL values from their OWN table rows, not substitutions, which
        # SET_QLVL_PROVENANCE.md traces. The law was right and its FIXTURE went stale, so it
        # reported honest data as a fabricated number.
        #
        # ⛔ THE PROBES NOW COME FROM THE ELEVEN THAT ARE STILL UNKNOWN — the pieces with no row in
        # the game table under any spelling. Those are the ones where printing anything would be
        # the fabrication, and they are re-derived from the ledger below rather than pasted, so
        # this cannot go stale the same way twice.
        # v3884 (REG-3440) - the eleven carry silospen's level now, so the probes are re-derived: every row the page
        # still records at qlvl 0 (keys, runes, whole-set aggregates), never a pasted list.
        best, _tier = _best()
        STILL_UNKNOWN = sorted(n for n, q in best.items() if int(q or 0) == 0)[:12]
        self.assertTrue(STILL_UNKNOWN, "premise: no row is recorded at qlvl 0 - this case has nothing to probe")
        # ⚠ BASELINE: the names must still BE zeros in the page, or the probe list is the stale
        # thing and this law is grading its own assumption. [[feedback-blind-fixture-green-gate]]
        not_zero = [n for n in STILL_UNKNOWN if int(best.get(n) or 0) > 0]
        self.assertEqual(not_zero, [],
                         "these were the pieces with NO game-table row and they now carry a "
                         "level: %s. Either more data was sourced (update this list AND "
                         "SET_QLVL_PROVENANCE.md) or something guessed a value." % not_zero)
        got = _run_real_reader(["Annihilus", "Key of Hate"] + STILL_UNKNOWN)
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        self.assertTrue(got, "the reader answered about nothing, so this law examined nothing")
        for n, v in got.items():
            self.assertIsNone(v, "%r resolved to %r. Its table row carries qlvl 0, which means no "
                                 "level was ever recorded — printing it states a fact the data "
                                 "does not hold" % (n, v))

    def test_a_SET_AGGREGATE_never_leaks_onto_a_PIECE(self):
        """★★ THE TRAP, AND IT IS THE ONE THIS FILE EXISTS FOR. `_etaHours` takes a set aggregate as
        its fallback source ON PURPOSE — a piece with no clock of its own borrows the set's. Doing
        the same for a LEVEL would print the set's gate under every piece of it. v2299 refused this
        two comments up in the same file; the qlvl reader takes no fallback at all."""
        got = _run_real_reader(["Trang-Oul's Wing (shield)", "Trang-Oul set (any piece)",
                                "Immortal King's Soul Cage (armor)", "Immortal King set (any)"])
        if got is None:
            self.skipTest("node unavailable — a skip is NOT a pass")
        # ⚠⚠ v2795 — `assertIsNone` WAS THE RIGHT LAW ONLY WHILE PIECES HAD NO DATA. Once the
        # pieces carry their own levels, "the piece resolves to nothing" stops being evidence of
        # anything and this law would have had to be deleted. What the docstring above actually
        # describes is narrower and permanent: the piece must not wear the SET's number.
        #
        # MEASURED, and it is the proof the join is per-PIECE: Trang-Oul's aggregate is 65 and
        # every one of its five pieces is 32; Immortal King's aggregate is 55 and its six pieces
        # are 37; Aldur's aggregate is 59 and its pieces are 29. Across the page, 25 stems carry
        # DIFFERING levels between their own entries — a per-set join could not produce that.
        for piece, agg in (("Trang-Oul's Wing (shield)", "Trang-Oul set (any piece)"),
                           ("Immortal King's Soul Cage (armor)", "Immortal King set (any)")):
            pv, av = got.get(piece), got.get(agg)
            self.assertIsNotNone(av, "%r lost its own level, so this law is now comparing against "
                                     "NOTHING — an instrument failure, not a clean result" % agg)
            self.assertIsNotNone(pv, "%r resolves to nothing. Per-piece levels shipped in v2787, "
                                     "so this is data going missing, not the gap it used to be"
                                     % piece)
            self.assertNotEqual(
                pv, av,
                "%r and its set aggregate %r BOTH read %r — the aggregate's level standing in for "
                "the piece's, which is the substitution v2299 refused. A piece sharing its set's "
                "number is the exact shape of that leak." % (piece, agg, pv))
        self.assertEqual(65, got.get("Trang-Oul set (any piece)"),
                         "the aggregate itself lost its own level, so this law is now passing "
                         "because NOTHING resolves — an instrument failure, not a clean result")

    # ── ⚠ THE FIXTURE ASSUMPTION, PINNED ────────────────────────────────────────────────────
    def test_the_set_piece_levels_ARRIVED_and_may_not_go_backwards(self):
        """★★ THIS LAW'S PREDECESSOR FIRED AS DESIGNED, AND THIS IS ITS SUCCESSOR.

        It was `test_the_set_piece_gap_is_still_real`, and its docstring promised: *"The day
        set-piece levels are sourced, this goes RED — which is the signal to render them, not a
        failure."* v2787 sourced them from the game's own SetItems.txt and it went red on
        `Arctic Binding` exactly as designed.

        ⛔ A FIRED TRIPWIRE IS REPLACED, NEVER DELETED. Deleting it would leave the coverage it
        watched unguarded in the OTHER direction — a data change that quietly empties the wall
        would then pass in silence, which is how the gap became invisible in the first place. So
        the assertion inverts: the levels are here, and they may not go backwards.

        MEASURED 2026-09-08: 124 of 135 roster pieces carry a real level, and the 11 that do not
        are EXACTLY the eleven SET_QLVL_PROVENANCE.md records as having no row in the game table
        under any spelling. Two independent extracts agree on all 132 pieces they share.
        [[unknown-stays-unknown]] [[regression-guard]]
        """
        best, tier = _best()
        sets = [(n, q) for n, q in best.items() if tier[n] == "set"]
        withq = [(n, q) for n, q in sets if q > 0]
        self.assertTrue(sets, "no set rows parsed — this law graded nothing")
        # ⚠ THE DISCRIMINATOR IS THE ROSTER, NOT A NAME PATTERN. My first cut asked whether the
        # name "looked like" an aggregate (`(any)`, `(set)`, the word set) and went red on
        # "Sigon's Complete Steel" — which IS the Sigon set's own name and simply does not contain
        # any of those tokens. A shape-guess about names is not a test; `set_roster.json` holds the
        # 135 real piece names and settles it. [[feedback-suspect-the-instrument]]
        roster = json.load(io.open(os.path.join(HERE, "set_roster.json"), encoding="utf-8"))
        pieces = roster.get("pieces") or []
        self.assertEqual(135, len(pieces),
                         "the set roster no longer holds 135 pieces (%d) — this law's authority "
                         "moved and it must be re-pointed before its green means anything"
                         % len(pieces))
        bare = set(p.split(" (")[0] for p in pieces)
        covered = sorted(p for p in bare if int(best.get(p) or 0) > 0)
        missing = sorted(p for p in bare if int(best.get(p) or 0) == 0)
        # ⚠ THE RATCHET. 124 is what the game data actually yielded; a drop means a load path
        # broke or a name drifted, and the wall would simply go quiet without saying so.
        self.assertGreaterEqual(
            len(covered), 124,
            "set-piece coverage FELL to %d of %d. The levels were sourced from SetItems.txt in "
            "v2787 and rendering them is half his ask — a drop empties the sets wall and nothing "
            "else would notice. Missing: %s" % (len(covered), len(bare), missing))
        # ⛔ AND THE UNKNOWNS STAY UNKNOWN. The eleven have no game-table row under any spelling;
        # SET_QLVL_PROVENANCE.md refuses to map a near-spelling because a near-spelling is not a
        # trace. A value appearing for any of them was GUESSED — the fabrication his sourcing rule
        # forbids — so a RISE here fails exactly as hard as a fall.
        self.assertEqual(
            missing, sorted(STILL_UNKNOWN_PIECES),
            "the set of UNKNOWN pieces changed. Newly filled: %s — each needs a traceable row in "
            "SET_QLVL_PROVENANCE.md before it may ship, because the alternative is a guessed "
            "level nobody can audit. Newly empty: %s"
            % (sorted(set(STILL_UNKNOWN_PIECES) - set(missing)),
               sorted(set(missing) - set(STILL_UNKNOWN_PIECES))))

    def test_the_unique_coverage_has_not_collapsed(self):
        """A zero needs a denominator, and so does a fix. If a data change drops unique coverage,
        the wall goes quiet and nothing else would say so."""
        best, tier = _best()
        hi = [(n, q) for n, q in best.items() if tier[n] == "high"]
        self.assertGreaterEqual(sum(1 for _n, q in hi if q > 0), 120,
                                "the 'high' tier lost its levels — the wall he asked to fill is "
                                "emptying out and only this law would notice")

    # ── ⚠ BOTH WALLS CARRY IT, AND THE RENDERER GUARDS ──────────────────────────────────────
    def test_both_walls_pass_the_level_through(self):
        """⚠ Built and not called is this repo's most repeated defect. Two walls feed one renderer;
        a level added to one only would look shipped and be half absent. [[the-unjoined-end]]"""
        # ⚠⚠ v2769 — CORRECTED, AND THE CORRECTION IS THE POINT. This first required the UNIQUES
        # wall to carry `q:` too. The post-ship review found — and the live board CONFIRMED at 220
        # of 220 rows — that it then printed the level TWICE: "Gull q4 q4". That wall's `badge` is
        # ALREADY the qlvl (`badge:(x.qlvl>0?'q'+x.qlvl:'')`), so uniques never needed a chip and
        # v2765 added a duplicate rather than a fix.
        # The uniques that show nothing are the 96 whose qlvl is 0 in the data, and sets have none
        # at all — BOTH are the data gap in task #20. The renderer was never this wall's problem.
        self.assertNotIn("q:_qlvlOf(x.n)", BIBLE,
                         "the UNIQUES wall carries a q chip again — its badge is already the "
                         "qlvl, so every row with a real level prints it twice")
        i = BIBLE.find("badge:(x.qlvl")
        self.assertGreater(i, 0,
                           "the uniques wall's badge no longer carries the qlvl — if that moved, "
                           "the chip may now be the right home and this law must be re-pointed "
                           "deliberately rather than left green")
        # ⚠⚠ v2771 — HIS CLARIFICATION, with a screenshot: "for the sets it says in white the type
        # base item it is — it needs to be switched to the q level INSTEAD of the base item in
        # white". So the level goes IN the badge, REPLACING the slot, not beside it. v2765 had it
        # as a separate chip, which would have put two white tokens on one row.
        self.assertIn("badge:(_sq?('q'+_sq):_sl)", BIBLE,
                      "the SETS wall's white badge no longer carries the q-level. He asked for the "
                      "level IN that slot, replacing the base type — not added next to it")
        self.assertNotIn("q:_qlvlOf(pp.name)", BIBLE,
                         "the sets wall carries a SECOND q token beside the badge, so a row with a "
                         "known level would print it twice — the defect the uniques wall already "
                         "had")
        # ⚠ AND IT FALLS BACK, which is why the wall is not blank today. 134 of 148 set entries
        # have no level, so `_sq` is null and the slot still shows. Dropping to an empty badge
        # would trade a true fact for a blank while waiting on data (task #20).
        self.assertIn("_sq?", BIBLE, "the badge no longer falls back to the base type, so 134 set "
                                     "rows would render an empty white space")

    def test_the_renderer_emits_nothing_when_there_is_no_level(self):
        """`e.q ? ... : ''` — a truthiness guard, so both null AND a 0 that ever slipped through
        render as absence rather than as `q0`."""
        i = BIBLE.find("entries.forEach(function(e){ H.push('<span class=\"gf-piece gf-miss\"")
        self.assertGreater(i, 0, "the shared missing-row renderer moved")
        blk = BIBLE[i:BIBLE.find("\n", i)]
        self.assertIn("e.q?", blk, "the level is rendered unconditionally, so an absent one prints")
        self.assertIn("gp-q", blk, "the level chip is gone from the renderer")

    def test_the_chip_is_white_as_he_asked(self):
        i = BIBLE.find(".gp-q{")
        self.assertGreater(i, 0, "the .gp-q style is gone")
        blk = BIBLE[i:BIBLE.find("}", i)]
        self.assertIn("color:#fff", blk, "he asked for the level in white and it is not white")



# ══ THE EXECUTABLE RED-PROOF ═════════════════════════════════════════════════
# PROPOSED by tv/heart2_candidates.py — derived from this gate's OWN assertions and
# measured against the target file (each anchor occurs exactly once). Review it: the
# question is whether deleting this text is the defect the law exists to catch.
RED_PROOF = [
    {
        "why": 'the law requires this text in bible.html, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'bible.html',
        "find": 'function _qlvlOf(name){',
        "replace": '_HEART2_TAMPERED_',
        "matches": 1,
    },
    {
        "why": 'the law requires this text in bible.html, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'bible.html',
        "find": 'window._qlvlOf = _qlvlOf;',
        "replace": '_HEART2_TAMPERED_',
        "matches": 1,
    },
    {
        "why": 'the law requires this text in bible.html, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'bible.html',
        "find": "badge:(_sq?('q'+_sq):_sl)",
        "replace": '_HEART2_TAMPERED_',
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
