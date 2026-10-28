# -*- coding: utf-8 -*-
"""v3171 (#96) — THE SWEEP MUST READ THE REELS THAT ACTUALLY SHOW A STASH.

MEASURED on his machine 2026-09-15, and it is the whole reason the vault has no receipts:

    45 sessions swept · 36 of them (80%) took NOTHING · 39 rows banked in total
    the THREE best stash-panel reels — one at 100% density — had NEVER BEEN SWEPT
    stash bank: 12 accumulator keys      chronicle bank: 8517 sightings over 324 names

The sweeper took reels in DIRECTORY ORDER filtered only by "not already sealed". The ranking it
needed already existed — vault_retro.panel_density, whose own docstring says it is free precisely
so "the sweep can afford to ask it about every reel before paying to read any of them" — and was
computed ONLY inside a doctor row that PRINTS it. Chooser built, sweeper built, never joined.
[[the-unjoined-end]] [[plumbing-with-no-tap]]

★ WHAT THIS PINS
  1. rank_by_panel orders by density, highest first;
  2. a reel whose gate RAISES sorts last, never first — "I could not measure it" must never be
     promoted over "I measured it and it is good";
  3. ties keep their original order, so ranking only ever reorders by evidence;
  4. the SWEEPER actually calls it (parsed from the function body, not grepped at file scope);
  5. the doctor and the sweeper use ONE ranker, so the console cannot hold two answers to
     "which reel next";
  6. vault_bank reports UNKNOWN rather than zero when a bank cannot be read.
"""
import ast
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable
    enable()
except Exception:
    pass


def _fn_node(path, name):
    """The named function's AST node. -> (node, source_segment)"""
    with io.open(path, encoding="utf-8") as fh:
        src = fh.read()
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n, (ast.get_source_segment(src, n) or "")
    raise AssertionError("function %r is gone from %s" % (name, os.path.basename(path)))


def _fn_src(path, name):
    return _fn_node(path, name)[1]


def _calls(path, name):
    """Every function NAME this function actually CALLS. -> set

    ⚠ PARSED, NOT GREPPED, AND THIS LAW WENT BLIND WITHOUT IT. The first cut asserted
    `"rank_by_panel" in <function source>` — and the explanatory COMMENT above the call says
    rank_by_panel, so deleting the real call left the law green. A red-proof caught it; a reader
    never would. Konyo's rule, and the reason it is a rule: parse, never grep, when a law reads
    source. [[source-reading-guard]] [[sabotage-is-usually-the-wrong-one]]
    """
    node, _ = _fn_node(path, name)
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                out.add(f.attr)
    return out


class TheRankerOrders(unittest.TestCase):

    def setUp(self):
        import vault_retro
        self.vr = vault_retro

    def test_it_orders_by_density_highest_first(self):
        dens = {"a": 0.1, "b": 0.9, "c": 0.5}
        # drive the REAL rank_by_panel with a stubbed density, so the ordering under test is the
        # shipped one and only the measurement is faked
        real = self.vr.panel_density
        try:
            self.vr.panel_density = lambda d, g, sample_every=8, cap=24: dens[d]
            out = self.vr.rank_by_panel(["a", "b", "c"], object())
        finally:
            self.vr.panel_density = real
        self.assertEqual([d for d, _ in out], ["b", "c", "a"])

    def test_a_reel_whose_gate_raises_sorts_last(self):
        def boom(d, g, sample_every=8, cap=24):
            if d == "bad":
                raise RuntimeError("gate died")
            return 0.4
        real = self.vr.panel_density
        try:
            self.vr.panel_density = boom
            out = self.vr.rank_by_panel(["bad", "good"], object())
        finally:
            self.vr.panel_density = real
        self.assertEqual(out[-1][0], "bad",
                         "a reel we could not measure must never outrank one we could")
        self.assertEqual(out[-1][1], 0.0)

    def test_ties_keep_their_original_order(self):
        real = self.vr.panel_density
        try:
            self.vr.panel_density = lambda d, g, sample_every=8, cap=24: 0.5
            out = self.vr.rank_by_panel(["x", "y", "z"], object())
        finally:
            self.vr.panel_density = real
        self.assertEqual([d for d, _ in out], ["x", "y", "z"],
                         "ranking may reorder by evidence and must never invent one")


class TheSweepWalksOneQueueFIFO(unittest.TestCase):
    """v3180 — HIS RULING SUPERSEDED THE ORDERING THIS FILE ORIGINALLY PINNED.

    v3171 sorted the sweep owed-first then by stash-panel density, to dig out of a real, measured
    backlog (45 sweeps, 36 empty, the three richest stash reels never read). It worked — and it
    made the ORDER OF WORK disagree with the ORDER ON SCREEN.

    He watched that and ruled for ONE queue, 2026-09-15: *"the sweep and the shelf and everhything
    should be a unified system... they should be fifo together"*, and *"a session ... going through
    the architcure and not getting stuck anywhere just extracted and tallied and flowing... the
    river should spit it out deleted eventually"*. On the trade-off he was explicit that the
    gating does not change: *"evedince is still going to be evedince regardless of the order they
    come in.. i want it coming in organzied and going out orgainzied"*.

    So the CLAIM this class makes is unchanged — the sweeper must pick deliberately, never in
    whatever order the filesystem hands back — and only the rule changed. rank_by_panel is still
    tested above and still used by the doctor; it simply no longer decides the sweep.
    """

    def test_the_sweep_walks_reels_oldest_first(self):
        """FIFO is oldest-unswept-first: what entered first is worked first and leaves first."""
        body = _fn_src(os.path.join(HERE, "control_app.py"), "_vault_sweep_run")
        self.assertIn("newest_first=False", body,
                      "the sweep is back on the default newest-first (or on directory order), so "
                      "the order of work no longer matches the river he watches")

    def test_it_asks_the_shared_lister_not_a_second_sort(self):
        """ONE ordering rule. A local re-sort here would drift from the order every other reader
        uses, which is the whole reason reel_dirs takes the parameter. [[copy-drift]]"""
        calls = _calls(os.path.join(HERE, "control_app.py"), "_vault_sweep_run")
        self.assertIn("reel_dirs", calls,
                      "the sweep no longer asks the shared reel lister at all")

    def test_the_fifo_order_is_a_real_argument_not_a_comment(self):
        """PARSED, NOT GREPPED — and the first cut of THIS LAW proved why. It searched the
        function text for "newest_first=False" and matched the COMMENT line above the call, so it
        would have passed with the argument deleted. Third time today a comment satisfied an
        assertion meant for code.

        It also guards the original defect: the first cut of the FIX was
        `sorted(dirs, key=_reel_t0)` against a helper that does not exist, inside a try/except
        that fell back to directory order — a NameError swallowed and FIFO silently never
        happening. An argument on the call cannot fail that way.
        [[source-reading-guard]] [[plumbing-with-no-tap]]"""
        node, _ = _fn_node(os.path.join(HERE, "control_app.py"), "_vault_sweep_run")
        found = []
        for n in ast.walk(node):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if name != "reel_dirs":
                continue
            for kw in n.keywords:
                if kw.arg == "newest_first":
                    found.append(getattr(kw.value, "value", "?"))
        self.assertTrue(found,
                        "reel_dirs is called without newest_first at all, so the sweep is back on "
                        "the default newest-first and the order of work no longer matches the "
                        "river he watches")
        self.assertIn(False, found,
                      "newest_first is not False — FIFO is oldest-unswept-first, so what entered "
                      "first is worked first and leaves first")


class TheBankNeverReadsEmptyWhenItIsUnknown(unittest.TestCase):

    def test_an_unreadable_bank_is_unknown_not_zero(self):
        import vault_bank
        real = vault_bank._load
        try:
            vault_bank._load = lambda n: (None, "%s would not parse" % n)
            word, line = vault_bank.headline()
        finally:
            vault_bank._load = real
        self.assertEqual(word, "UNKNOWN")
        self.assertIn("UNKNOWN", line)

    def test_both_empty_wordings_fold_to_one_and_the_fold_is_reported(self):
        import vault_bank
        self.assertTrue(vault_bank._is_empty_why("nothing was taken"))
        self.assertTrue(vault_bank._is_empty_why(
            "examined and there was nothing to take - recorded as a fact"))
        self.assertFalse(vault_bank._is_empty_why(None),
                         "a sweep with NO reason is UNKNOWN, never honestly empty")
        self.assertEqual(len(vault_bank.state()["whyFolded"]), 2,
                         "the fold must be declared, or two labels silently become one")


class AllFourOrgansWatchIt(unittest.TestCase):

    def test_the_doctor_registers_it(self):
        import console_doctor
        self.assertTrue(any(n == "stash bank" for n, _ in console_doctor.CHECKS))

    def test_the_heart_registers_it(self):
        import health_engine
        self.assertTrue(any(f.__name__ == "check_stash_bank" for f in health_engine.CHECKS))

    def test_the_watchdog_declares_what_it_watches(self):
        import health_engine
        self.assertIn("stashBank", health_engine.WATCHES,
                      "a row absent from WATCHES fails the coverage gate")

    def test_the_eagle_gets_it_by_calling_the_doctor(self):
        """The eagle's contract is 'call the other doctors rather than re-implement them', so a
        check registered with the doctor is on the eagle by construction. This pins the contract,
        because a future eagle that hand-lists rows would silently drop this one."""
        import console_doctor
        self.assertTrue(hasattr(console_doctor, "run"),
                        "console_doctor.run() is what /api/eagle calls")
        src = _fn_src(os.path.join(HERE, "console_doctor.py"), "run")
        self.assertIn("CHECKS", src,
                      "run() must enumerate CHECKS, or a registered organ never reaches the eagle")

RED_PROOF = [
    {"why": "v3171 - the sweep ranks reels in directory order again: the densest stash reel waits behind arbitrary footage",
     "file": "tv/vault_retro.py",
     "find": "    return sorted(out, key=lambda kv: -kv[1])\n",
     "replace": "    return list(out)\n",
     "matches": 1},
    {"why": "v3171 - a reel whose gate raises is promoted over one that was measured",
     "file": "tv/vault_retro.py",
     "find": "            v = 0.0          # a gate that raises is not a reel that is empty\n",
     "replace": "            v = 1.0          # a gate that raises is not a reel that is empty\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
