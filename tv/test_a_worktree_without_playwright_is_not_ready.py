# -*- coding: utf-8 -*-
"""REG-3646 - A SHIP WORKTREE WITHOUT PLAYWRIGHT FAILS IN SECONDS, NOT AFTER CI (attempt 8).

CI went green, then the Mac pre-push console-demos gate refused because
`node tv/demo_console.mjs` could not find playwright in ~/Desktop/verify-evidence/wt-bundle
(no node_modules; the main checkout had it). mac_ready must refuse such a tree immediately,
and may auto-fix only by symlinking node_modules to ~/d2r_bible_tests/node_modules when that
install exists. Everything else fails loudly.
"""
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import preship as P  # noqa: E402


class TheLawHolds(unittest.TestCase):
    def test_a_tree_with_no_node_modules_is_red(self):
        d = tempfile.mkdtemp(prefix="preship-ready-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        # no node_modules, and auto-fix cannot find the Mac install in this sandbox
        code, rows = P.mac_ready(root=d, auto_fix=True)
        self.assertEqual(code, 1, rows)
        say = " ".join(r.get("say") or "" for r in rows)
        self.assertIn("node_modules", say)

    def test_auto_fix_links_only_the_known_install(self):
        d = tempfile.mkdtemp(prefix="preship-link-")
        src = tempfile.mkdtemp(prefix="preship-nm-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.addCleanup(shutil.rmtree, src, ignore_errors=True)
        # a fake install directory is enough for the symlink; playwright still will not resolve
        changed, why = P.maybe_link_node_modules(d, target=src)
        self.assertTrue(changed, why)
        self.assertTrue(os.path.islink(os.path.join(d, "node_modules")))
        self.assertEqual(os.readlink(os.path.join(d, "node_modules")), src)
        # a second call is a no-op
        changed2, _ = P.maybe_link_node_modules(d, target=src)
        self.assertFalse(changed2)

    def test_require_playwright_is_the_probe(self):
        """The attempt-8 command is exactly `node -e require('playwright')` from the tree."""
        src = open(os.path.join(HERE, "preship.py"), encoding="utf-8").read()
        self.assertIn("require('playwright')", src)



class TheRehearsalRunsAChangedLawByItsGate(unittest.TestCase):
    """v3895 - MEASURED 11-11 01:52: the box rehearsal passed changed law FILE stems to run_gates --only, and the registry
    refused 'test_a_version_is_never_banked_into_a_graded_tree' (its gate is test_version_not_banked_into_graded_tree) - the
    whole rehearsal stopped on a name, not a red"""

    def test_a_changed_file_maps_to_the_gate_that_runs_it(self):
        import preship as PS
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        gates, unmapped = PS.gates_for_files(root, ["test_a_version_is_never_banked_into_a_graded_tree"])
        self.assertEqual(gates, ["test_version_not_banked_into_graded_tree"], "a changed law was asked by its file name")
        self.assertEqual(unmapped, [])
        self.assertEqual(PS.gates_for_files(root, ["test_no_such_law_file_exists"])[1], ["test_no_such_law_file_exists"],
                         "a law no gate runs was not named")



RED_PROOF = [
    {"why": "v3895 - the rehearsal asks a changed law by its FILE name again (the registry refuses every renamed gate)",
     "file": "tv/preship.py",
     "find": "        hit = [g.name for g in rg.GATES if any(os.path.basename(str(a)) == st + \".py\" for a in (getattr(g, \"argv\", None) or []))]\n",
     "replace": "        hit = [g.name for g in rg.GATES if g.name == st]\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
