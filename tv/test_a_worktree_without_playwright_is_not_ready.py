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
        # no node_modules, and auto-fix cannot find the Mac install in this sandbox. v3896 (REG-3667) - MEASURED on his Mac:
        # the real ~/d2r_bible_tests/node_modules WAS found and linked in, so the case read the PC, not the tree, and went
        # red on whatever check came next (the second eye). The install it may link is pointed at nothing here.
        from unittest import mock
        with mock.patch.object(P, "MAC_NODE_MODULES", os.path.join(d, "no-install-here")):
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



class TheBrowserCheckReadsAPathAndTheHooksOwnFinder(unittest.TestCase):
    """v3896 (card #200 guard 9, REG-3666) - MEASURED 11-11 04:10: `chromium.executablePath().then(...)` threw (the path is
    a STRING), and the fallback asked Linux names - the Mac rehearsal refused v3895 with chromium AND Chrome.app installed"""

    def _root(self, finder=None):
        d = tempfile.mkdtemp(prefix="preship-browser-")
        self.addCleanup(shutil.rmtree, d, True)
        if finder is not None:
            os.makedirs(os.path.join(d, "hooks"))
            with open(os.path.join(d, "hooks", "pre-push"), "w", encoding="utf-8") as fh:
                fh.write("#!/usr/bin/env bash\n" + finder)
        return d

    def _exe(self, d, name):
        x = os.path.join(d, name)
        with open(x, "w") as fh:
            fh.write("#!/bin/sh\nexit 0\n")
        os.chmod(x, 0o755)
        return x

    def _finder(self, path):
        return (P.HOOK_BROWSER_BEGIN + "_d2r_find_render_browser() {\n  printf '%s\\n' '" + path + "'\n  return 0\n}\n"
                + P.HOOK_BROWSER_END)

    def test_the_hooks_own_finder_is_what_is_asked(self):
        d = self._root()
        exe = self._exe(d, "fake-chrome")
        os.makedirs(os.path.join(d, "hooks"))
        with open(os.path.join(d, "hooks", "pre-push"), "w", encoding="utf-8") as fh:
            fh.write("#!/usr/bin/env bash\n" + self._finder(exe))
        path, why = P.hook_browser(d)
        self.assertEqual(path, exe, why)

    def test_moved_markers_are_unknown_never_a_browser(self):
        d = self._root("#!/usr/bin/env bash\n_d2r_find_render_browser() { echo /bin/sh; }\n")
        path, why = P.hook_browser(d)
        self.assertIsNone(path, "a finder with no markers was trusted: %s" % why)
        self.assertIn("markers moved", why)

    def test_no_playwright_falls_back_to_the_hooks_finder(self):
        d = self._root()
        exe = self._exe(d, "fake-chrome")
        os.makedirs(os.path.join(d, "hooks"))
        with open(os.path.join(d, "hooks", "pre-push"), "w", encoding="utf-8") as fh:
            fh.write("#!/usr/bin/env bash\n" + self._finder(exe))
        ok, why = P.browsers_installed(d)            # no node_modules here: node cannot require playwright
        self.assertTrue(ok, why)
        self.assertIn(exe, why)

    def test_a_path_returned_as_a_string_is_read(self):
        if not shutil.which("node"):
            self.skipTest("no node on this PC - proven where node is")
        d = self._root()
        exe = self._exe(d, "fake-chromium")
        pw = os.path.join(d, "node_modules", "playwright")
        os.makedirs(pw)
        with open(os.path.join(pw, "index.js"), "w", encoding="utf-8") as fh:
            fh.write("module.exports = {chromium: {executablePath: () => %r}};\n" % exe)
        ok, why = P.browsers_installed(d)            # no hooks/ here: only Playwright's answer can make this ready
        self.assertTrue(ok, "a string from executablePath() was not read: %s" % why)
        self.assertIn("chromium at " + exe, why)



class TheReadinessAsksTheVersionMainShips(unittest.TestCase):
    """v3895 round 2 (REG-3672) - readiness read "version"/"v"/"build" from WINDOWS_SHIP.json, which says "ver": the second
    eye was asked about no version, the ledger refused, and every main push was refused as 'second eye OWED'"""

    def test_the_real_ship_file_names_its_version(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "tv", "WINDOWS_SHIP.json"), encoding="utf-8") as fh:
            got = P.ship_version(fh.read())
        self.assertIsNotNone(got, "the version this tree's WINDOWS_SHIP.json names could not be read - readiness would "
                                  "ask the second eye about no version and refuse every main push")
        self.assertRegex(got, r"^v\d+$")

    def test_each_spelling_is_read_and_nothing_is_guessed(self):
        self.assertEqual(P.ship_version('{"ver": "v3894"}'), "v3894")
        self.assertEqual(P.ship_version('{"version": "v12"}'), "v12")
        for bad in ("", "not json", "[1]", '{"ver": 3894}', '{"ver": "3894"}'):
            with self.subTest(bad=bad):
                self.assertIsNone(P.ship_version(bad))


class ReadinessTakesSecondsAndTheRehearsalCarriesTheLessons(unittest.TestCase):
    """v3896 (REG-3679) - --mac-ready took 399 s: it ran every lesson (render_check, changed_tests, ...) at the ship's launch
    and inside every main push's hook; readiness runs readiness, and the lessons run in the rehearsal"""

    def _ran(self, fn):
        ran = []
        cat = {"mac_ready": {"cheap": True}, "render_check": {"cheap": False}, "changed_tests": {"cheap": False},
               "encoding": {"cheap": True}}
        from unittest import mock

        def fake_run_one(name, root, **kw):
            ran.append(name)
            return {"name": name, "code": 0, "ms": 0, "say": "fixture"}
        lessons = [{"check": "render_check"}, {"check": "changed_tests"}]
        with mock.patch.object(P, "catalog", lambda: cat), mock.patch.object(P, "run_one", fake_run_one), \
                mock.patch.object(P, "load_lessons", lambda root=None: lessons), \
                mock.patch.object(P, "load_auto_lessons", lambda root=None: []), \
                mock.patch.object(P, "READY_ORDER", ("mac_ready",)), mock.patch.object(P, "REHEARSE_ORDER", ("mac_ready", "encoding")):
            fn("/nonexistent-root")
        return sorted(ran)

    def test_readiness_runs_readiness_only(self):
        self.assertEqual(self._ran(P.mac_ready), ["mac_ready"], "readiness ran the lessons too - minutes, not seconds")

    def test_the_rehearsal_still_runs_every_lesson(self):
        self.assertEqual(self._ran(P.mac_rehearse), ["changed_tests", "encoding", "mac_ready", "render_check"],
                         "PREMISE: the rehearsal must carry the lessons readiness no longer runs")



RED_PROOF = [
    {"why": "v3895 - the rehearsal asks a changed law by its FILE name again (the registry refuses every renamed gate)",
     "file": "tv/preship.py",
     "find": "        hit = [g.name for g in rg.GATES if any(os.path.basename(str(a)) == st + \".py\" for a in (getattr(g, \"argv\", None) or []))]\n",
     "replace": "        hit = [g.name for g in rg.GATES if g.name == st]\n",
     "matches": 1},
    {"why": "REG-3666 - executablePath() is chained as a promise again, so the string it returns throws and is never read",
     "file": "tv/preship.py",
     "find": "Promise.resolve(p.chromium.executablePath()).then(",
     "replace": "p.chromium.executablePath().then(",
     "matches": 1, "needs": "node"},
    {"why": "REG-3666 - no Playwright chromium means not ready, even with the browser the hook's render gate would start",
     "file": "tv/preship.py",
     "find": "    path, why = hook_browser(root, timeout=timeout)\n",
     "replace": "    path, why = None, \"no finder asked\"\n",
     "matches": 1},
    {"why": "REG-3666 - a finder whose markers moved is run anyway",
     "file": "tv/preship.py",
     "find": "    if src.count(HOOK_BROWSER_BEGIN) != 1 or src.count(HOOK_BROWSER_END) != 1:\n        return None, \"the hook's browser finder markers moved - UNKNOWN\"\n",
     "replace": "    if HOOK_BROWSER_BEGIN not in src:\n        src = HOOK_BROWSER_BEGIN + src + HOOK_BROWSER_END\n",
     "matches": 1},
    {"why": "REG-3672 - readiness reads the old key names only, so the version main ships is None and every main push is refused",
     "file": "tv/preship.py",
     "find": "    for k in (\"ver\", \"version\", \"v\", \"build\"):\n",
     "replace": "    for k in (\"version\", \"v\", \"build\"):\n",
     "matches": 1},
    {"why": "REG-3679 - readiness runs every lesson again (render_check and changed_tests at every launch and main push)",
     "file": "tv/preship.py",
     "find": "    kw.setdefault(\"include_lessons\", False)\n",
     "replace": "",
     "matches": 1}
]

if __name__ == "__main__":
    unittest.main()
