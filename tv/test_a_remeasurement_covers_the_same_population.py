# -*- coding: utf-8 -*-
"""v3320 — A RE-MEASUREMENT COVERS THE POPULATION OF THE FIRST MEASUREMENT.

`test_the_cheap_subset_is_actually_CHEAP` measures the every-tick doctor roster, and when the total
goes over budget it re-measures and keeps `min(first, second)` — because a wall-clock figure moves
2.7x between runs of identical code, and for a floor-bounded quantity the minimum is the honest
estimator. That reasoning is correct. The implementation compared two different populations:

    first pass   skipped  _skip = SLOW | PERIODIC    63 checks
    the re-measure skipped  SLOW only                65 checks

MEASURED on his Mac 2026-09-18, one tick, unchanged code:

    first-pass population     4,134 ms      <- under the 9,000 ms budget
    retry population          8,859 ms
      engines corroborate     3,057 ms      ] PERIODIC — deliberately off the every-tick bill
      sweep would find        1,667 ms      ]

So `min()` ran over two different things. The retry carried a 4,725 ms surcharge the every-tick
path never pays, which meant it could only absolve a burst LARGER than 8,859 ms — and the block's
own comment calls the retry "what actually decides". It decided nothing. On 2026-09-18 it refused a
legitimate push at 10,146 ms for a subset that costs 4,134.

⚠ THIS IS THE THIRD INSTANCE OF ONE SHAPE, which is why it is a law and not a fix:
    v3313  a seed is compared only to its own population
    v3317  the heart divides by the population it counted
    v3320  a re-measurement covers the population of the first measurement
Each time the numerator was right, the denominator was a different set, and the arithmetic was
performed anyway. [[zero-needs-a-denominator]] [[unknown-stays-unknown]]

⚠ IT ASKS THE COMPILER, NOT THE TEXT. Every earlier cut of a law like this was a grep, and a grep
reads the paragraph above — which names `cd.SLOW` four times — as code. `ast` cannot see a comment
at all, so the prose that explains the defect can never satisfy the law. [[source-reading-guard]] §1

⚠ AND IT PINS WHICH SET, not merely that the sets agree. A law asserting "both loops skip the same
thing" goes green when BOTH are narrowed back to `cd.SLOW` — the defect, applied consistently. The
population must be `_skip`, and `_skip` must still be built from SLOW *and* PERIODIC.
"""
import ast
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

# Its docstrings and failure messages carry non-ASCII, and a unittest failure PRINTS them. On a
# cp1255 console that crash happens while REPORTING, so a clean tree exits non-zero for a reason
# that has nothing to do with the law. Caught by test_control's encoding-safety gate.
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

SUBJECT = os.path.join(HERE, "test_control.py")
FUNC = "test_the_cheap_subset_is_actually_CHEAP"
ROSTER = "CHECKS"          #: cd.CHECKS — the roster every population is carved out of
POPULATION = "_skip"       #: the one name every carve must use


def _is_roster(node):
    """`cd.CHECKS` — the iterable each population filters."""
    return isinstance(node, ast.Attribute) and node.attr == ROSTER


def _set_name(node):
    """A readable name for the set being tested against, without ast.unparse (3.8 runs this too)."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _set_name(node.value)
        return "%s.%s" % (base, node.attr) if base else node.attr
    return None


def _membership_sets(test):
    """Every set named by an `x in S` / `x not in S` test, including inside `and`/`or`."""
    out = []
    for node in ast.walk(test):
        if isinstance(node, ast.Compare):
            for op, cmp_ in zip(node.ops, node.comparators):
                if isinstance(op, (ast.In, ast.NotIn)):
                    out.append(_set_name(cmp_))
    return out


def _the_function(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == FUNC:
            return node
    return None


def populations(fn):
    """Every place the roster is filtered, as (kind, line, set-name).

    Two shapes carve a population out of cd.CHECKS, and BOTH were wrong in different files:
      · a `for` over the roster whose body opens with `if <x> in S: continue`
      · a comprehension over the roster with an `if <x> not in S` clause
    """
    found = []
    for node in ast.walk(fn):
        if isinstance(node, ast.For) and _is_roster(node.iter):
            for stmt in node.body:
                if not isinstance(stmt, ast.If):
                    continue
                if not any(isinstance(b, ast.Continue) for b in stmt.body):
                    continue
                for s in _membership_sets(stmt.test):
                    found.append(("for-loop", stmt.lineno, s))
        if isinstance(node, ast.comprehension) and _is_roster(node.iter):
            for cond in node.ifs:
                for s in _membership_sets(cond):
                    found.append(("comprehension", getattr(cond, "lineno", -1), s))
    return found


class TestARemeasurementCoversTheSamePopulation(unittest.TestCase):

    def setUp(self):
        with io.open(SUBJECT, encoding="utf-8") as fh:
            self.tree = ast.parse(fh.read())
        self.fn = _the_function(self.tree)
        self.assertIsNotNone(
            self.fn, "%s no longer exists in test_control.py — the budget gate this law protects "
                     "has been renamed or removed, and the law is now measuring nothing." % FUNC)

    def test_every_carve_of_the_roster_names_the_same_population(self):
        """THE LAW. One measurement, one re-measurement, one denominator — one population."""
        found = populations(self.fn)

        # A zero needs a denominator: if the walk found nothing, a clean result is meaningless.
        self.assertGreaterEqual(
            len(found), 3,
            "the ast walk found only %d place(s) where %s carves a population out of cd.%s — it "
            "expects at least three (the first pass, the re-measure, and the 'measured almost "
            "nothing' denominator). Finding fewer means the walk missed them, so a PASS here is "
            "UNMEASURED, not clean. Found: %r" % (len(found), FUNC, ROSTER, found))

        names = sorted(set(s for _k, _l, s in found))
        self.assertEqual(
            names, [POPULATION],
            "%d carve(s) of the roster name %d different population(s): %s\n"
            "  %s\n"
            "Every one of them must be `%s` (= SLOW | PERIODIC). MEASURED 2026-09-18 with the "
            "re-measure narrowed to cd.SLOW: the first pass priced 63 checks at 4,134 ms and the "
            "re-measure priced 65 at 8,859 ms, so min() ran over two different things and the "
            "gate refused a legitimate push at 10,146 ms. A reading is comparable only to a "
            "reading of the same population."
            % (len(found), len(names), ", ".join(names),
               "\n  ".join("%s at line %d skips %s" % (k, l, s) for k, l, s in found),
               POPULATION))

    def test_the_population_is_still_built_from_BOTH_sets(self):
        """Agreement is not enough — narrowing BOTH loops to cd.SLOW would agree, and be the bug."""
        assigns = [n for n in ast.walk(self.fn)
                   if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == POPULATION for t in n.targets)]
        self.assertEqual(
            len(assigns), 1,
            "`%s` is assigned %d time(s) inside %s; it must be defined exactly once, or the two "
            "loops can agree on a NAME while reading different values."
            % (POPULATION, len(assigns), FUNC))

        mentioned = set()
        for node in ast.walk(assigns[0].value):
            if isinstance(node, ast.Attribute):
                mentioned.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                mentioned.add(node.value)
        for needed in ("SLOW", "PERIODIC"):
            self.assertIn(
                needed, mentioned,
                "`%s` is no longer built from %s — it reads %r. Both belong: SLOW never runs "
                "unattended, PERIODIC runs on a longer cadence, and the every-tick budget prices "
                "neither. Dropping PERIODIC puts 4,725 ms of `engines corroborate` + `sweep would "
                "find` back on a 9,000 ms bill." % (POPULATION, needed, sorted(mentioned)))

    def test_the_two_sets_actually_differ_or_this_law_measures_nothing(self):
        """BEHAVIOURAL. If PERIODIC ever empties, the populations coincide and the law is vacuous."""
        import console_doctor as cd

        periodic = set(getattr(cd, "PERIODIC", ()))
        slow = set(cd.SLOW)
        self.assertTrue(
            periodic - slow,
            "PERIODIC is empty (or a subset of SLOW), so `_skip` and `cd.SLOW` name the same "
            "population and this law can no longer distinguish the defect it exists for. That is "
            "UNMEASURED, not a pass — if the split was genuinely retired, retire this law with "
            "it rather than leaving a green that means nothing. [[zero-needs-a-denominator]]")

        names = set(n for n, _fn in cd.CHECKS)
        missing = (periodic | slow) - names
        self.assertEqual(
            missing, set(),
            "%d name(s) in SLOW/PERIODIC are not on the roster at all: %s. A skip list naming a "
            "check that does not exist excludes nothing, so the budget silently widens."
            % (len(missing), ", ".join(sorted(missing))))


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        # v3463 — RE-ANCHORED. v3456 moved this loop inside `with cd.tick_caches():`, one level
        # deeper, and the 12/16-space anchor then matched ZERO lines: the proof ran nothing and CI
        # reported `test_remeasure_population[0]` as a tamper that could not be applied. Measured
        # before this edit: the old anchor 0 matches, the 16/20-space form exactly 1.
        "why": "narrowing the re-measure back to cd.SLOW prices 2 checks the first pass never did",
        "file": "tv/test_control.py",
        "find": "                for _n, _f in cd.CHECKS:\n                    if _n in _skip:",
        "replace": "                for _n, _f in cd.CHECKS:\n                    if _n in cd.SLOW:",
        "matches": 1,
    },
    {
        "why": "the 'measured almost nothing' denominator counting a population nobody timed",
        "file": "tv/test_control.py",
        "find": "% (did_work, len([n for n, _ in cd.CHECKS if n not in _skip])), flush=True)",
        "replace": "% (did_work, len([n for n, _ in cd.CHECKS if n not in cd.SLOW])), flush=True)",
        "matches": 1,
    },
    {
        "why": "dropping PERIODIC from _skip makes every carve agree on the WRONG population",
        "file": "tv/test_control.py",
        "find": '        _skip = set(cd.SLOW) | set(getattr(cd, "PERIODIC", ()))',
        "replace": '        _skip = set(cd.SLOW)',
        "matches": 1,
    },
]
