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


if __name__ == "__main__":
    unittest.main()
