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
        # no node_modules, and this sandbox is no worktree, so the auto-fix (REG-3743: a COPY from the worktree's own main
        # checkout) has nothing to seed from. v3896 (REG-3667) - the old symlink fix found his real install and linked it in,
        # so the case read the PC, not the tree.
        code, rows = P.mac_ready(root=d, auto_fix=True)
        self.assertEqual(code, 1, rows)
        say = " ".join(r.get("say") or "" for r in rows)
        self.assertIn("node_modules", say)

    def test_auto_fix_seeds_by_copy_never_a_link(self):
        """REG-3743 - the auto-fix COPIES node_modules from the worktree's own main checkout (tv/seed_worktree.py); the
        symlink it used to make is the v3525 shape seed_worktree refuses"""
        import subprocess
        _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith("GIT_")}
        self.addCleanup(os.environ.update, _gitenv)
        _free = os.environ.get("TV_SEED_FREE_BYTES")
        os.environ["TV_SEED_FREE_BYTES"] = str(50 * 10 ** 9)
        self.addCleanup(lambda: os.environ.pop("TV_SEED_FREE_BYTES", None) if _free is None
                        else os.environ.__setitem__("TV_SEED_FREE_BYTES", _free))
        d = tempfile.mkdtemp(prefix="preship-seed-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        main = os.path.join(d, "main")
        os.makedirs(main)
        git = lambda *a: subprocess.check_call(["git", "-C", main] + list(a), stdout=subprocess.DEVNULL)
        subprocess.check_call(["git", "init", "-q", main])
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "t")
        with open(os.path.join(main, ".gitignore"), "w") as fh:
            fh.write("/node_modules\n")
        git("add", "-A")
        git("commit", "-q", "-m", "a")
        os.makedirs(os.path.join(main, "node_modules", "playwright"))
        with open(os.path.join(main, "node_modules", "playwright", "index.js"), "w") as fh:
            fh.write("module.exports = 1;\n")
        wt = os.path.join(d, "wt")
        git("worktree", "add", "-q", "-b", "w", wt)
        changed, why = P.maybe_seed_node_modules(wt)
        self.assertTrue(changed, why)
        nm = os.path.join(wt, "node_modules")
        self.assertTrue(os.path.isdir(nm) and not os.path.islink(nm), "the worktree's node_modules is a link into main")
        with open(os.path.join(nm, "playwright", "index.js")) as fh:
            self.assertEqual(fh.read(), "module.exports = 1;\n")
        self.assertFalse(P.maybe_seed_node_modules(wt)[0], "a second call is not a no-op")
        plain = os.path.join(d, "plain")
        os.makedirs(plain)
        ok, why2 = P.maybe_seed_node_modules(plain)
        self.assertFalse(ok)
        self.assertFalse(os.path.lexists(os.path.join(plain, "node_modules")), "a tree that is no worktree got node_modules")
        self.assertIn("not a worktree root", why2)

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



class ThePreflightSeedsItsWorktreeAndNamesAMissingPlaywright(unittest.TestCase):
    """REG-3743 - MEASURED 11-12: v3899's pre-flight ran 33 min of laws in a fresh worktree, then went RED on the console
    demos with the tail "Node.js v24.13.0" - the worktree had no node_modules, and the pre-flight seeded nothing"""

    def _crash(self, *a, **k):
        class R(object):
            returncode = 1
            stdout = ""
            stderr = ("node:internal/modules/cjs/loader:1424\n  const err = new Error(message);\n\n"
                      "Error: Cannot find module 'playwright'\nRequire stack:\n- tv/demo_console.mjs\n\nNode.js v24.13.0\n")
        return R()

    def test_a_missing_playwright_is_named_never_only_the_node_banner(self):
        import preflight as PF
        ok, tail = PF.run_demos(_run=self._crash)
        self.assertFalse(ok)
        self.assertIn("no node_modules for playwright", tail, "the red does not name the missing install: %r" % tail)
        self.assertIn("Cannot find module 'playwright'", tail)
        self.assertNotEqual(tail.strip(), "Node.js v24.13.0")

    def test_the_preflight_seeds_a_worktree_before_the_demos(self):
        import inspect
        import preflight as PF
        code = "\n".join(l.split("#", 1)[0] for l in inspect.getsource(PF.run_demos).split("\n"))
        self.assertEqual(code.count("_ps.maybe_seed_node_modules(_root)"), 1, "the pre-flight no longer seeds node_modules")
        self.assertLess(code.index("_ps.maybe_seed_node_modules(_root)"), code.index("os.path.join(\"tv\", \"demo_console.mjs\")"),
                        "the seed comes after the demos it is for")


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
     "matches": 1},
    {"why": "REG-3743 - the readiness auto-fix SYMLINKS main's node_modules into a worktree again (the v3525 shape)",
     "file": "tv/preship.py",
     "find": "    rc = _sw.seed(root, say=lines.append)\n",
     "replace": "    os.symlink(os.path.join(_sw.main_checkout_of(root)[0] or root, \"node_modules\"), dest)\n    rc = 0\n",
     "matches": 1, "needs": "posix"},
    {"why": "REG-3743 - a pre-flight demos red names only node's version banner again (v3899, 11-12)",
     "file": "tv/preflight.py",
     "find": "    if r.returncode != 0 and any(\"Cannot find module 'playwright'\" in l for l in lines):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3743 - the pre-flight runs the demos in an unseeded worktree again",
     "file": "tv/preflight.py",
     "find": "            _ps.maybe_seed_node_modules(_root)\n",
     "replace": "            pass\n",
     "matches": 1}
]

if __name__ == "__main__":
    unittest.main()
