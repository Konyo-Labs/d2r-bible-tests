# -*- coding: utf-8 -*-
"""v2794 — THE MAP SAID IT COULD NOT GO STALE, AND IT HAD BEEN STALE FOR SIX DAYS.

`tv/blueprint.py`'s own header: *"THE MAP OF THIS SYSTEM, GENERATED FROM THE CODE SO IT CANNOT GO
STALE"* — the right idea, inherited from ~/achilles-revival along with the reverse-blueprint rule.
Nothing regenerated it. Measured 2026-09-08 against the BLUEPRINT.md then on disk:

    last written        Sep 2 (six days)
    `station` mentions  0
    `INTAKE`            0
    `TOMBSTONE`         0
    `printer`           0
    `panelFrames`       0

The river and the printer were both built AFTER that date, so the one surface meant to show the
wiring from above simply did not know they existed. Konyo: *"shouldnt this be a connected and
communicating system thats easily seen wired from a macro view"*. It should — and it was the MAP
that was missing, not the wiring. [[the-unjoined-end]]

=== ⛔ THE GATE REFUSES; IT DOES NOT REGENERATE ===
The obvious move is to have pre-push rebuild the file. That is wrong here and the repo already
knows why: **the gate grades the WORKING TREE**. A hook that rewrote BLUEPRINT.md mid-push would
dirty the tree it is grading, and the commit actually being pushed would still carry the stale
file. So it refuses, a human runs the generator, and the push is retried — the same shape the
second-eye gate uses. [[d2r-push-grades-the-working-tree]]

=== ⚠ THE TIMESTAMP LINE IS EXCLUDED, AND WITHOUT THAT THIS IS FURNITURE ON DAY ONE ===
`render()` stamps `generated YYYY-MM-DD HH:MM`, which changes every minute. A naive byte-compare
would be RED forever, everyone would learn to skim it, and the real staleness would go with it.
Compare the MAP, not the clock. [[regression-guard]]
"""
import io
import os
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

import blueprint as BP  # noqa: E402


class TheBlueprintCannotGoStaleSilently(unittest.TestCase):

    # ── ⚠⚠ THE LAW ──────────────────────────────────────────────────────────────────────────
    def test_the_map_matches_the_code_right_now(self):
        """★★★ The whole point. If this is red, BLUEPRINT.md describes a building that has been
        renovated — run `python3 tv/blueprint.py`."""
        self.assertEqual(BP.main(["--check"]), 0,
                         "BLUEPRINT.md no longer matches the code. Regenerate it: "
                         "python3 tv/blueprint.py")

    def test_check_IGNORES_the_generated_timestamp(self):
        """★★ Without this the gate is red on every run and becomes furniture in a day. Proven by
        comparing two renders taken at different clock minutes — only the stamp may differ.

        ⚠ REG-3820 (v3904 pre-flight a, 11-13) - THIS CASE HAD ITS OWN STRIPPER, AND IT ASKED A DIFFERENT QUESTION FROM
        --check. It dropped only the stamp, so the LIVE blocks - store sizes read off disk at render time - had to hold
        still between two renders. .orphan_cpu_sample.json (REG-3774) is rewritten by every doctor pass, and while the
        pre-flight's laws ran in parallel it went 5627 B -> 5585 B between the two calls: red, on a tree whose code had
        not moved. --check compares blueprint.code_only, the ONE stripper ("two copies of this rule is how a check starts
        asking a different question"), so this asks the same question --check does. [[copy-drift]]"""
        a = BP.render()
        b = BP.render()
        strip = BP.code_only
        self.assertEqual(strip(a), strip(b),
                         "two renders of the same tree differ outside the timestamp, so --check "
                         "can never be stable")
        self.assertIn("generated ", a,
                      "the stamp is gone — if it was removed, this exclusion is now dead code and "
                      "should be removed with it")

    # ── ⚠ THE SECTIONS THAT WERE MISSING ────────────────────────────────────────────────────
    def test_the_map_knows_the_RIVER_exists(self):
        """⚠ It did not, for six days. The stations come from `reel_router.STATIONS` — quoted, not
        listed here, so a station added upstream appears on the map without a second edit.
        [[copy-drift]]"""
        t = io.open(os.path.join(REPO, "BLUEPRINT.md"), encoding="utf-8").read()
        for must in ("THE RIVER", "INTAKE", "TOMBSTONE"):
            self.assertIn(must, t, "the blueprint no longer describes the river (%r missing)" % must)

    def test_the_map_knows_the_PRINTER_exists(self):
        t = io.open(os.path.join(REPO, "BLUEPRINT.md"), encoding="utf-8").read()
        self.assertIn("THE PRINTER", t, "the blueprint no longer describes the printer")

    def test_the_map_shows_GROSS_vs_STRIPPED(self):
        """⚠ His words: *"a gross full lengthed all screenshots before the filtering ... and then
        the stripped version"*. Both exist; the stripped sets had no reader, and a map that cannot
        show that gap is a map worth fixing."""
        t = io.open(os.path.join(REPO, "BLUEPRINT.md"), encoding="utf-8").read()
        self.assertIn("GROSS vs STRIPPED", t,
                      "the blueprint no longer shows how much footage carries a panel")

    def test_the_map_NAMES_every_gate_and_does_not_merely_count_them(self):
        """⚠⚠ THE SECTION THAT COST A SESSION. Until v3020 the whole GATES section was:

            ## GATES

                322 registered in tv/run_gates.py

        322 gates, and it named NONE of them. So the one document meant to show the system from
        above could say HOW MANY laws exist and never WHICH — and on 2026-09-12 that is exactly
        what happened: I searched for laws about slot identity, tooltips and holdings, concluded
        none existed, and Konyo corrected me — "im pretty sure we already defined them too so dont
        duplicate". There were 32, across six files, written to his own 2026-08-29 spec. One
        `grep BLUEPRINT.md tooltip` would have found them.

        His ruling: "this console is complex already so you wont remember off the bat you need to
        verify... this is why 4 organs and the blueprints via the heart".

        A COUNT IS NOT KNOWLEDGE. Every gate already carried a `why` — 322 of 322 — so the material
        was always there and was simply never rendered. [[the-unjoined-end]]
        [[zero-needs-a-denominator]] [[verify-before-building-console]]"""
        import run_gates as RG
        t = io.open(os.path.join(REPO, "BLUEPRINT.md"), encoding="utf-8").read()
        names = [g.name for g in RG.GATES]
        self.assertGreater(len(names), 50,
                           "only %d gates parsed from run_gates — the reader, not the roster"
                           % len(names))
        missing = [n for n in names if ("**%s**" % n) not in t]
        self.assertFalse(
            missing,
            "%d of %d registered gate(s) are NOT NAMED in BLUEPRINT.md — the map can say how many "
            "laws exist and not which, which is the state that let 32 existing laws go unfound: %s"
            % (len(missing), len(names), missing[:5]))

    def test_the_gate_index_carries_what_each_one_GUARDS(self):
        """⚠ A list of names is barely better than a count. The index exists so that 'does a law
        already exist for this?' is answerable by READING, which needs the subject, not just the
        filename. A gate whose why is empty in the map is a row nobody can search."""
        import blueprint as BP
        idx = BP.gate_index()
        self.assertIsNotNone(idx, "gate_index() could not parse run_gates.py, so the map would "
                                  "silently fall back to a bare count — the exact regression")
        empty = [n for n, w in idx if not str(w or "").strip()]
        self.assertFalse(
            empty,
            "%d of %d gate(s) reach the map with NO why, so they are unsearchable by subject: %s"
            % (len(empty), len(idx), empty[:5]))
        #: ⚠ TWO READERS, ONE FACT — a regex count and a parsed index. A disagreement means a
        #: Gate( is written in a shape one of them cannot see, and the map would then be confidently
        #: incomplete. [[unknown-stays-unknown]]
        self.assertEqual(
            len(idx), BP.gate_count(),
            "the parsed index says %d gates and the regex count says %s — one of the two readers "
            "cannot see a Gate, so the map is incomplete without saying so"
            % (len(idx), BP.gate_count()))

    # ── ⛔ IT REPORTS; IT NEVER ASSERTS ──────────────────────────────────────────────────────
    def test_an_unreadable_subsystem_says_UNKNOWN_not_zero(self):
        """⛔ The file's own rule: *"Where something cannot be counted it says so rather than
        printing a zero, because '0 lanes' and 'I could not read the lanes' are opposite facts."*

        ⚠⚠ THE FIRST CUT OF THIS LAW READ TEXT AND A SABOTAGE WALKED PAST IT. It asserted the
        string "why" appeared somewhere in each function — and deleting `"why": None` from the
        river's initializer left the key present in its error-path assignments, so the law stayed
        GREEN while the success path stopped carrying the channel. Fourth time today a law read
        MENTION instead of behaviour. So: BREAK the dependency and demand the answer.
        [[sabotage-is-usually-the-wrong-one]] [[unknown-stays-unknown]]"""
        import builtins
        real = builtins.__import__

        def _blind(blocked):
            def _imp(name, *a, **k):
                if name == blocked:
                    raise ImportError("blinded for the test")
                return real(name, *a, **k)
            return _imp

        for fn, dep in ((BP.river, "reel_router"),
                        (BP.printer_stream, "printer")):
            builtins.__import__ = _blind(dep)
            try:
                got = fn()
            finally:
                builtins.__import__ = real
            self.assertIsInstance(got, dict,
                                  "%s() returned %r with %s unreadable — a section that cannot be "
                                  "counted must still answer" % (fn.__name__, got, dep))
            self.assertTrue(str(got.get("why") or "").strip(),
                            "%s() lost its `why` when %s could not be read, so an unreadable "
                            "subsystem now renders as an EMPTY one" % (fn.__name__, dep))

        # the stripped set reads a FILE, so blind it by pointing at a name that cannot exist
        import blueprint as _bp
        old_here = _bp.HERE
        try:
            _bp.HERE = os.path.join(HERE, "__no_such_dir_for_the_test__")
            got = _bp.stripped_sets()
        finally:
            _bp.HERE = old_here
        self.assertTrue(str((got or {}).get("why") or "").strip(),
                        "stripped_sets() reports nothing rather than UNKNOWN when the triage store "
                        "is absent — an absent store would render as zero panel frames")

    def test_the_rendered_map_SAYS_unknown_when_a_section_cannot_be_read(self):
        """⛔ The channel existing is half of it; render() must print it. A `why` nobody surfaces
        is the same silence with an extra field. [[plumbing-with-no-tap]]"""
        src = io.open(os.path.join(HERE, "blueprint.py"), encoding="utf-8").read()
        i = src.find('A("## THE RIVER')
        self.assertGreater(i, 0, "the river section is gone from render()")
        seg = src[i:i + 900]
        # REG-1504: the words now come from ONE helper (unknown_shelf.says_unknown) so five readers say
        # UNKNOWN once. Accept the literal or the helper — and DRIVE the helper, so a helper that stopped
        # saying UNKNOWN cannot hide behind its name.
        import unknown_shelf as _us
        says = "UNKNOWN" in seg or ("says_unknown(" in seg and _us.says_unknown("x").startswith("UNKNOWN"))
        self.assertTrue(says,
                        "render() prints the river without an UNKNOWN branch, so a river it could "
                        "not read would be drawn as a river with nothing in it")



RED_PROOF = [
    {
        #: ⚠ THE v3019-AND-EARLIER STATE, RESTORED. Emptying the index loop returns the GATES
        #: section to a bare count — the exact shape that let 32 existing laws go unfound on
        #: 2026-09-12 while the map reported "322 registered" and named none of them.
        "why": "rendering no gate names returns the blueprint to a COUNT standing where knowledge "
               "belongs, and 'does a law already exist for this?' stops being answerable by reading",
        "file": "blueprint.py",
        "find": "        for _n, _w in idx:",
        "replace": "        for _n, _w in []:",
        "matches": 1,
    },
    {
        "why": "⚠ RE-AIMED — MY FIRST ANCHOR WAS THE WRONG SIDE OF THE DOOR, and heart2 measured it "
               "BLIND (1 match, still green). river() has FOUR why-writes; I picked the one that "
               "handles a router which IMPORTS AND THEN THROWS, while this law blinds the IMPORT "
               "and so returns early through a different line entirely. Verified the replacement "
               "by shadowing a tampered blueprint and calling river() with reel_router blinded: "
               "why='' -> the law fails. Third instance of this shape today. "
               "[[sabotage-is-usually-the-wrong-one]] "
               "v2888 — the tamper makes river() LOSE ITS `why` when reel_router cannot be imported, "
               "so an unreadable subsystem renders as an EMPTY one — 'the router could not be read' "
               "and '0 lanes' become the same pixels, which is the single rule this file exists to "
               "enforce: \"Where something cannot be counted it says so rather than printing a zero, "
               "because '0 lanes' and 'I could not read the lanes' are opposite facts.\" It reddens "
               "test_an_unreadable_subsystem_says_UNKNOWN_not_zero, which does NOT read text — it "
               "blinds the import and demands the answer, after an earlier text-reading cut of the "
               "same law let a sabotage walk straight past it. The replacement keeps the code valid "
               "and simply files the reason under a key nobody reads, which is exactly how this "
               "defect looks in the wild. [[unknown-stays-unknown]] [[zero-needs-a-denominator]]",
        "file": 'blueprint.py',
        "find": 'return {"why": "reel_router is not importable (%s)" % type(e).__name__}',
        "replace": 'return {}',
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
