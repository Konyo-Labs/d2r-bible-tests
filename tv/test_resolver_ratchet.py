"""A NINTH RESOLVER MAY NOT APPEAR UNNOTICED.

⚠⚠ THIS GUARD EXISTS BECAUSE A COLD CROSS-FAMILY REVIEW PREDICTED EXACTLY HOW one_name DECAYS.
Asked how the design fails over a year, with no hint of this codebase's history:

    "The most likely decay path is new surfaces or new items appearing outside the concept table.
     Someone will add a fourth consumer (a log label, an export key, a UI label) and either
     hard-code another variant or extend the table inconsistently... the original resolvers
     continue to be patched directly because they are still the ones called in hot paths."

That is not hypothetical here. It has already happened FIVE times — A1's unreachable FLOWING, A3's
9 MISNAMED cells, the tab vocabulary, the duplicate board topics — and **I wrote two of those alias
maps myself, in one day, while fixing instances of the problem**. Nothing detected any of them; each
was found by tripping over the defect it caused, weeks or hours later.

So this is a RATCHET on resolvers: the census may FALL as they retire into one_name, and a NEW one
is a failure. Not because a local map is always wrong — sometimes it is genuinely local — but
because it must be a decision someone makes on purpose, in a diff, rather than the fifth accident.

⚠ IT ASSERTS THE CENSUS, NOT THE CODE. A file may hold whatever it needs; what may not happen is
the number quietly rising.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable  # noqa: E402

enable()

#: What a resolver looks like. Deliberately shape-based — a name is how these get missed.
PATTERNS = (
    (r"^\s*(_?[A-Z][A-Z0-9_]*(?:ALIAS|ALIASES))\s*=\s*\{", "alias map"),
    (r"^\s*(_?[A-Z][A-Z0-9_]*_TO_[A-Z0-9_]+)\s*=\s*\{", "translation map"),
    (r"^def (canonical\w*|_canon\w*)\(", "canonicaliser"),
)

#: The sanctioned one. It IS the concept table; catching it would make the ratchet self-defeating.
EXEMPT_FILES = ("one_name.py",)

#: ⚠ THE CENSUS AS MEASURED 2026-09-03, AND IT MAY ONLY FALL. Each entry is a place that answers
#: "what is this thing called" without asking one_name. Retiring one into one_name is the work;
#: when that happens, remove its line here and say so in the commit.
BASELINE = {
    ("chronicle_resolve.py", "canonical"),
    ("chronicle_template.py", "TAB_ALIASES"),
    ("chronicle_template.py", "canonical_tab"),
    ("control_app.py", "_AUTOROUTE_ESSENCE_ALIAS"),
    ("d2r_screens.py", "KIND_TO_SCENARIO"),  # #187/#185 local kind→scenario template map, not a display-name resolver
    ("lane_lock.py", "_TAB_TO_SURFACE"),
    ("lane_lock.py", "_canon_tab"),
    ("route_totals.py", "canonical"),
    ("tv_diablo.py", "_STASH_TAB_ALIASES"),
}


def census():
    """-> {(file, name)} every resolver-shaped declaration in tv/."""
    found = set()
    for fn in sorted(os.listdir(HERE)):
        if not fn.endswith(".py") or fn in EXEMPT_FILES or fn.startswith("test_"):
            continue
        try:
            s = io.open(os.path.join(HERE, fn), encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for pat, _kind in PATTERNS:
            for m in re.finditer(pat, s, re.M):
                found.add((fn, m.group(1)))
    return found


class TheResolverCountMayOnlyFall(unittest.TestCase):

    def test_no_new_resolver_has_appeared(self):
        now = census()
        added = sorted(now - BASELINE)
        self.assertFalse(
            added,
            "%d NEW resolver-shaped declaration(s) appeared: %s\n\n"
            "Each is a place that answers \"what is this thing called\" without asking "
            "tv/one_name.py. Five of these have already caused defects here — an unreachable "
            "FLOWING, nine mis-reported matrix cells, a tab that resolved on one side and not the "
            "other, a board printing one topic twice — and two of them were written in a single "
            "day BY THE SAME HAND THAT WAS FIXING THE OTHERS.\n\n"
            "If this one is genuinely local, add it to BASELINE and say why in the commit. That "
            "makes it a decision. Leaving it makes it the sixth accident." % (len(added), added))

    def test_the_baseline_is_not_stale(self):
        """A retired resolver must be removed from the list, or the debt reads larger than it is."""
        now = census()
        gone = sorted(BASELINE - now)
        self.assertFalse(
            gone,
            "%d resolver(s) in BASELINE no longer exist: %s. If they retired into one_name, that "
            "is the win — remove them here so the census reports the real remaining debt. A list "
            "that overstates what is left is as useless as one that understates it." % (len(gone), gone))

    def test_one_name_itself_is_exempt_and_present(self):
        """The ratchet must not count the thing it is protecting, and must not pass if it is gone."""
        self.assertIn("one_name.py", EXEMPT_FILES)
        self.assertTrue(os.path.isfile(os.path.join(HERE, "one_name.py")),
                        "one_name.py is gone, so every remaining resolver is now unsanctioned and "
                        "this ratchet is guarding nothing")


RED_PROOF = [
    {
        'why': 'a ninth resolver-shaped declaration appears in tv/ and the census absorbs it silently  MEASURED: untampered Ran 3 tests in 0.245s -> OK, exit 0 (clean worktree at 92feadb0); tampered (all 4) all 4 occurrences replaced in tv/tv_diablo.py (file still parses; ast.parse OK) ; reddened law test_resolver_ratchet.TheResolverCountMayOnlyFall.test_no_new_resolver; ALONE Alone under the tamper: python3 -m unittest test_resolver_ratchet.TheResolverCountMayOnlyFall.test_n.',
        'file': 'tv_diablo.py',
        'find': '_STASH_TAB_ALIASES',
        'replace': '_STASH_PANEL_ALIASES',
        'matches': 4,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
