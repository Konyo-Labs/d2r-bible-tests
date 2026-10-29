# -*- coding: utf-8 -*-
"""REG-2362 — THE test_control CASES THAT READ WHAT A FOLDER HOLDS WHEN THEY RUN.

heart2 keys a proof on the bytes its law can read. A law that LISTS A DIRECTORY ITSELF (os.listdir / glob.glob /
os.walk in the law file) reads whatever is there at run time, so heart2 calls it UNKEYABLE and never saves one of its
proofs. MEASURED 2026-10-21: test_control listed directories at 40 sites, and its 27 proofs (~4 min each) re-ran on
every push of the v3783 series. 23 of those sites listed a temp dir the test had just made; they now go through
fixture_tmp.list_own / match_own, which refuse anything but this process's own scratch. The case that read his footage
for a probe image now makes one. The rest are HERE, because they genuinely read the tree, the art corpus or his footage
as it is when they run: a test file nobody registered, a class below unittest.main(), an import CI does not install, a
name nothing binds, a pkill in a shipped script, a paid lane with no memory, the art corpus shrinking, a sleep-then-read
spec, and the stash detectors end to end on whatever footage exists.

Each case is moved BYTE FOR BYTE, under its old class name. Where the class kept other cases in test_control, the
constants and helpers are borrowed from that class at import - one definition, never a copy - and test_control is
imported for its fixtures (contained scratch, isolated state paths, the suite's own ports), exactly as the cases ran
before. This file is unkeyable on purpose (tv/unkeyable_laws.json). It is cheap, and hooks/pre-push runs it in the tv
suites stage right after test_control, so nothing that used to stop a push stops pushes any less.
One case was never in test_control and lives here for the same reason: REG-3077's scan over EVERY tests/*.spec.ts,
so a NEW spec that pins a store the board writes back between two loads is held too. Its scan, the helper's promise
and the specs REG-3076 moved stay keyed in test_a_spec_pin_rides_the_reloads_boot.py - one scan, imported, never a
copy.
[[copy-drift]] [[regression-guard]] RED_PROOF below.
"""
import glob
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()       # these print non-ASCII; a cp1255 console must not crash while REPORTING
except Exception:
    pass
import test_control as _TC   # noqa: E402  its fixtures, exactly as these cases ran inside it
import stash_eye as se       # noqa: E402
import test_a_spec_pin_rides_the_reloads_boot as _pin_law   # noqa: E402  REG-3077's scan, one definition
setUpModule = _TC.setUpModule
tearDownModule = _TC.tearDownModule


class TestNoOrphanSuite(unittest.TestCase):
    """v1483 — a test suite that nobody runs is not a test suite. (REG-2362: the two cases that list tv/test_*.py; the
    registry cases of this class are still in test_control.)"""

    def test_no_suite_defines_a_class_BELOW_unittest_main(self):
        """v1533 — the trap this repo already paid for once (v1457: 7 tests in test_control.py were
        defined below the guard and had NEVER run, while the suite reported OK). It has no automated
        check, so it is still live — I walked straight into it appending a class to
        test_chronicle_chain.py: 6 tests written, 0 defined, suite green.

        unittest.main() exits the interpreter. Anything after it is dead code that LOOKS like
        coverage, which is the most expensive kind of nothing."""
        here = os.path.dirname(os.path.abspath(__file__))
        bad = []
        for path in sorted(glob.glob(os.path.join(here, "test_*.py"))):
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            # anchor on the REAL guard, not the string: this very test's own docstring mentions
            # unittest.main(), and a naive find() matched that and flagged this file (caught on the
            # first run — a guard whose first victim is itself is not yet a guard)
            m = re.search(r'^if __name__ == ["\']__main__["\']:', src, re.M)
            if not m:
                continue
            tail = src[m.start():]
            if re.search(r"^class\s+\w+", tail, re.M):
                bad.append(os.path.basename(path))
        self.assertEqual(
            bad, [],
            "these suites define a test class AFTER unittest.main(), which exits the interpreter — "
            "every class below it is NEVER DEFINED and the suite still reports OK:\n  "
            + "\n  ".join(bad) + "\nMove the class above the `if __name__` guard.")

    def test_every_suite_is_in_the_gate_set(self):
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "run_gates.py"), encoding="utf-8") as fh:
            runner = fh.read()
        suites = sorted(os.path.basename(p) for p in glob.glob(os.path.join(here, "test_*.py")))
        self.assertGreater(len(suites), 3, "suite discovery found almost nothing — check the glob")
        missing = [s for s in suites if s not in runner]
        self.assertEqual(
            missing, [],
            "these suites exist but no gate runs them, so they can rot for a hundred versions "
            "while still looking maintained (REG-079):\n  " + "\n  ".join(missing)
            + "\nAdd each to GATES in tv/run_gates.py, with a `why` saying what it protects.")


class TestNoSuiteImportsSomethingCIDoesNotHave(unittest.TestCase):
    """v1911 — `import yaml` IN A TEST TOOK THE PUBLISH WORKFLOW DOWN. (REG-2362: the case that reads every suite in
    tv/; the allowlist, its helpers and the runner-install case stay in test_control, and are borrowed from there.)"""

    ALLOWED_BARE = _TC.TestNoSuiteImportsSomethingCIDoesNotHave.ALLOWED_BARE
    ALLOWED_GUARDED = _TC.TestNoSuiteImportsSomethingCIDoesNotHave.ALLOWED_GUARDED
    _is_third_party = staticmethod(_TC.TestNoSuiteImportsSomethingCIDoesNotHave._is_third_party)
    _repo_module_deps = staticmethod(_TC.TestNoSuiteImportsSomethingCIDoesNotHave._repo_module_deps)

    def test_every_third_party_import_is_one_CI_installs(self):
        import ast
        import glob
        here = os.path.dirname(os.path.abspath(__file__))
        repo_mods = {os.path.splitext(os.path.basename(p))[0]
                     for p in glob.glob(os.path.join(here, "*.py"))}
        # ⚠ #42 (2026-10-02) - ONE PARSE PER MODULE, ONE LOOKUP PER NAME. This case was 271.6 s of test_control's 435.6 s
        # (62%, measured per class): every suite that imports a repo module re-parsed that module - control_app.py, some
        # 46k lines, once per suite that imports it - and asked importlib about the same names again and again. A run
        # never changes a file under it, so each answer is computed once here. Same question, same verdict.
        _deps, _third = {}, {}

        def repo_deps(m):
            if m not in _deps:
                _deps[m] = self._repo_module_deps(here, m)
            return _deps[m]

        def third_party(m):
            if m not in _third:
                _third[m] = self._is_third_party(m)
            return _third[m]
        bad = []
        for path in sorted(glob.glob(os.path.join(here, "test_*.py"))):
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            inside_try = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Try):
                    for sub in ast.walk(node):
                        inside_try.add(id(sub))
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    mods = [node.module.split(".")[0]]
                for m in mods:
                    if m in repo_mods:
                        # ⚠ v1934 — A LOCAL MODULE IS NOT AUTOMATICALLY SAFE. It was treated as
                        # safe, and that let a suite import `conftest` — a repo module whose FIRST
                        # LINE is `import pytest`. run_gates.py runs each suite as a plain script
                        # and the agent-tests runner installs only pillow, so the gate ERRORED on CI
                        # for NINE consecutive runs while every local signal stayed green. The guard
                        # was right about its own question — "is this import third-party?" — and
                        # blind to the failure one level below it. [[the-unjoined-end]] §6
                        for dep in repo_deps(m):
                            if dep in repo_mods or not third_party(dep):
                                continue
                            if dep not in self.ALLOWED_BARE:
                                bad.append("%s:%d imports the repo module %r, which imports %r "
                                           "at module level — and the runner does not have it"
                                           % (os.path.basename(path),
                                              getattr(node, "lineno", 0), m, dep))
                        continue
                    if not third_party(m):
                        continue
                    ok = (self.ALLOWED_GUARDED if id(node) in inside_try else self.ALLOWED_BARE)
                    if m not in ok:
                        bad.append("%s:%d imports %r%s"
                                   % (os.path.basename(path), getattr(node, "lineno", 0), m,
                                      " (inside a try)" if id(node) in inside_try else ""))
        self.assertEqual(bad, [],
                         "a suite imports something the CI runner does not have — it will pass here "
                         "and take the deploy down there:\n  " + "\n  ".join(bad)
                         + "\nCI installs only what publish.yml AND tv-tests.yml pip-install. Parse it by hand, "
                           "or add the dependency to both and widen this allowlist.")


class TestV2007TheEndToEndGateRunsOnWhateverFootageEXISTS(unittest.TestCase):
    """v2007 — restores what v1712 recorded as permanently lost.

    TestStashPanelOpenGuard has two real-frame tests that have not run since the corpus was pruned,
    "PERMANENTLY skipped in both venues". v1712 handled that honestly: it kept the pure-predicate
    tests covering the DECISION and wrote down exactly what was gone —

        "What is genuinely lost here is only the END-TO-END path (crop -> features -> label) on real
         pixels, which is why these are kept rather than deleted."

    THE FIXTURES WERE PINNED TO REEL NAMES, and reel names get pruned. Pin to a PROPERTY instead and
    the same coverage survives any pruning: ask his corpus for a frame that classifies not-d2r and a
    frame that classifies as an open stash, whichever reels happen to be on disk today.

    MEASURED across 199 sampled frames of his 31 current reels — every case the pruned pair covered
    is present:
        gameplay / gameplay        122
        stash    / stash            43
        stash    / stash-default    31
        gameplay / not-d2r           3     <- the wallpaper bug's exact verdict

    It still skips where there is genuinely no footage (CI, a fresh checkout), and says so. The
    difference is that it now RUNS on the machine that has the film, every push, instead of nowhere.
    [[feedback-blind-fixture-green-gate]]
    """

    HIST = os.path.join(HERE, "frames", "hist")
    _CACHE = {}

    @classmethod
    def _find(cls, shape, cap=260):
        """First frame whose measured PIXELS match `shape`. Cached so the tests scan once.

        ⚠ IT SEARCHES BY FEATURES, NOT BY VERDICT, and the first cut got this wrong. Anchoring on
        `pick == "not-d2r"` meant that breaking the predicate produced NO not-d2r frames, so the
        search found nothing and the test SKIPPED — sabotage-proven, and a skip is not a failure.
        That is the "a gate that always skips is the same defect" scar, in my own new test, the
        first time I ran it against a broken predicate.

        frac_dark and dark_cols are measurements of the picture and survive any change to the rule
        that reads them, so the frame is still found and the ASSERTION is what fails.
        [[feedback-blind-fixture-green-gate]] [[feedback-suspect-the-instrument]]
        """
        if shape in cls._CACHE:
            return cls._CACHE[shape]
        import glob
        frames = []
        for d in sorted(glob.glob(os.path.join(cls.HIST, "reel_*"))):
            frames += sorted(glob.glob(os.path.join(d, "*.jpg")))[::12]
        hit = None
        for p in frames[:cap]:
            try:
                label, detail = se.classify_stash_grid(p)
            except Exception:
                continue
            fd = (detail or {}).get("frac_dark")
            dc = (detail or {}).get("dark_cols")
            if fd is None or dc is None:
                continue
            # LIT PHOTOGRAPH — the wallpaper shape. Measured in his corpus: 2 frames at fd=0.0, 0 cols.
            if shape == "lit-photo" and fd < 0.05 and dc == 0:
                hit = (p, label, detail); break
            # OPEN PANEL — measured: 61 frames, e.g. fd=0.5302/15 cols, fd=0.3688/11 cols.
            if shape == "open-panel" and 0.15 <= fd <= 0.65 and dc >= 10:
                hit = (p, label, detail); break
        cls._CACHE[shape] = hit
        return hit

    def test_a_not_d2r_frame_never_carries_a_stash_label(self):
        """THE wallpaper bug, end to end on real pixels: 69 desktop frames sealed as stash-gems and
        fired a phantom tally that read 0. The predicate is tested at measured values elsewhere;
        this proves the whole path still agrees with it."""
        hit = self._find("lit-photo")
        if not hit:
            self.skipTest("no lit-photograph frame in this checkout's footage — the DECISION is "
                          "still covered by the _panel_open_from_features tests, which need no film")
        p, label, detail = hit
        self.assertFalse(str(label).startswith("stash"),
                         "%s: a LIT PHOTOGRAPH (frac_dark=%s, dark_cols=%s — no game content) "
                         "classified as %r. This is the wallpaper bug: 69 desktop frames sealed as "
                         "stash-gems and fired a phantom tally that read 0."
                         % (os.path.basename(p), detail.get("frac_dark"),
                            detail.get("dark_cols"), label))
        self.assertEqual(detail.get("pick"), "not-d2r")

    def test_a_real_open_panel_is_still_recognised(self):
        """The other half, and the one a too-strict guard breaks: refusing everything is not a fix.
        A gate that never says yes is the same defect as one that never says no."""
        hit = self._find("open-panel")
        if not hit:
            self.skipTest("no open-stash frame in this checkout's footage")
        p, label, detail = hit
        self.assertTrue(str(label).startswith("stash"),
                        "%s: a real open stash panel classified as %r" % (os.path.basename(p), label))

    def test_the_two_detectors_do_not_flatly_contradict_each_other(self):
        """stash_screen_open (OCR of the tab chrome) and classify_stash_grid (pixel geometry) are
        INDEPENDENT. Where the OCR one admits a frame, the pixel one must not call it not-d2r —
        that combination means one of them is badly wrong, and it is exactly the pair the vault
        sweep leans on. Reported as the finding it is, rather than averaged.
        [[feedback-contradiction-is-the-finding]]"""
        import glob
        import control_app as ca
        frames = []
        for d in sorted(glob.glob(os.path.join(self.HIST, "reel_*"))):
            frames += sorted(glob.glob(os.path.join(d, "*.jpg")))[::12]
        if not frames:
            self.skipTest("no footage in this checkout")
        clashes, looked = [], 0
        for p in frames[:120]:
            if ca.stash_screen_open(p) is None:
                continue
            looked += 1
            try:
                _label, detail = se.classify_stash_grid(p)
            except Exception:
                continue
            if str((detail or {}).get("pick") or "") == "not-d2r":
                clashes.append(os.path.basename(p))
        if not looked:
            self.skipTest("the OCR gate admitted no frame in this sample — nothing to cross-check")
        self.assertEqual(clashes, [],
                         "the tab-chrome OCR admitted these frames as a stash while the pixel "
                         "geometry called them NOT D2R: %s" % ", ".join(clashes[:5]))


class TestV2010NoCallIntoANameThatIsNotThere(unittest.TestCase):
    """v2010 — a caller with no symbol. (REG-2362: the case that scans every tv/*.py; the scanner and the case that
    proves it catches the three that shipped stay in test_control, and the scanner is borrowed from there.)"""

    _scan = staticmethod(_TC.TestV2010NoCallIntoANameThatIsNotThere._scan)

    def test_no_python_file_calls_a_name_nothing_binds(self):
        import glob
        here = os.path.dirname(os.path.abspath(__file__))
        bad = []
        for f in sorted(glob.glob(os.path.join(here, "*.py"))):
            bad += self._scan(f)
        self.assertEqual(
            bad, [],
            "these read a name that is bound NOWHERE — module scope, enclosing scope, parameter or "
            "builtin. Inside a try/except that is silent forever and the code looks wired:\n  "
            + "\n  ".join(bad))


class TestV2077HdArtCoverageDoesNotRegress(unittest.TestCase):
    """Konyo: "in general all the HD ART make sure is back."

    MEASURED by asking the page itself on 2026-08-24: of 320 ITEMS, 317 resolve real art, ZERO fall
    back to a placeholder, and 3 have none — Polaris Spear, The Scourge, and Cow King's Leathers
    (set). All three are genuinely ABSENT FILES, not lookup bugs: `ls art/ | grep -i polaris` and
    `scourge` return nothing, and for Cow King's only mr_cowkingshooves.png exists, which is a
    different piece. That is a CASC extraction job, not a code fix, and saying so is the point —
    [[unknown-stays-unknown]] applies to assets too.

    What CAN regress silently is the corpus: art is 1,233 files on disk, and a prune, a bad sync or
    a rename takes them away with nothing failing. The board would then quietly draw placeholders
    where it used to draw items — exactly the class of loss he has been catching by eye."""

    ART = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "art")
    FLOOR = 1233

    def test_the_art_corpus_has_not_shrunk(self):
        import glob as _g
        if not os.path.isdir(self.ART):
            self.skipTest("the art directory is not on this machine")
        n = len(_g.glob(os.path.join(self.ART, "*.png")))
        self.assertGreaterEqual(
            n, self.FLOOR,
            "the art corpus dropped from %d to %d file(s). Something removed artwork the board "
            "draws, and nothing else would have failed — the page just starts showing placeholders."
            % (self.FLOOR, n))

    def test_the_gem_art_every_craft_card_depends_on_is_present(self):
        """v2077 gave craft cards their gem sprite. If these four go, every craft silently reverts
        to one alembic emoji and the cards become indistinguishable again."""
        import glob as _g
        if not os.path.isdir(self.ART):
            self.skipTest("the art directory is not on this machine")
        for gem in ("amethyst", "ruby", "emerald", "saphire"):
            hits = _g.glob(os.path.join(self.ART, "hd_perfect_%s*.png" % gem))
            self.assertTrue(hits, "hd_perfect_%s is gone — the crafts that depend on it fall back "
                                  "to the generic icon" % gem)


class TestTheSleepThenReadFlakesDoNotGetMoreNumerous(unittest.TestCase):
    """v2108 — a ratchet on the flake class that cost two false failures in one night.

    `await page.waitForTimeout(N)` followed by an evaluate that reads a LAZILY BUILT board
    global (RUNEWORD_TIP, CRAFTS, forgeScan, funiScan, fsetsScan, _endgameFilterBases) is a
    race: bible.html is ~5.9MB and defines those after load, so on a loaded runner the global
    is absent, the customary `|| {}` swallows it, the fixture seeds NOTHING, and the assertion
    reports a PRODUCT defect that is really the harness arriving early.

    Both of tonight's false failures had that exact shape — v592 seeded an empty `d2r_rwMade`
    and then accused the loot filter; v559 read a toast before it existed. Each was green in
    four consecutive runs and red in one, with the only ship in between touching a different
    surface. That is a flake, and a gate that is sometimes red has stopped carrying
    information.

    This does not pretend to have fixed all of them. It stops the count GROWING and records
    the debt honestly, the same way TestTheSourceGuardsDoNotGetMoreDangerous does for
    byte-counted slices. `tests/_board_ready.ts` is the way to pay it down: it waits for the
    thing the test is about to read. [[feedback-blind-fixture-green-gate]]
    """

    LIMIT = 51        # measured 2026-08-25 after fixing v592 and v559. It may only go DOWN.
    GLOBALS = ("RUNEWORD_TIP", "RUNEWORDS", "CRAFTS", "_endgameFilterBases",
               "forgeScan", "funiScan", "fsetsScan")

    def test_the_count_does_not_grow(self):
        import glob
        root = os.path.join(os.path.dirname(HERE), "tests")
        pat = re.compile(r"waitForTimeout\([^)]*\);?\s*(?:const\s+\w+\s*=\s*)?await page\.evaluate")
        gpat = re.compile(r"w\.(%s)\b" % "|".join(self.GLOBALS))
        found = []
        for f in sorted(glob.glob(os.path.join(root, "*.spec.ts"))):
            with open(f, encoding="utf-8") as fh:
                src = fh.read()
            for m in pat.finditer(src):
                if gpat.search(src[m.end():m.end() + 420]):
                    found.append(os.path.basename(f))
                    break
        self.assertLessEqual(
            len(found), self.LIMIT,
            "%d specs sleep and then read a lazily-built board global, up from %d. That is a "
            "race, not a wait: on a loaded runner the global is absent, `|| {}` swallows it, "
            "and the test reports a PRODUCT defect that is really the harness arriving early. "
            "Use boardReady() from tests/_board_ready.ts. New: %s"
            % (len(found), self.LIMIT, sorted(set(found))[-6:]),
        )


class TestV2160NothingShippedKillsByNamePattern(unittest.TestCase):
    """HIS STANDING RULE: no shipped script kills by name pattern. (REG-2362: the case that reads every tv/*.sh and
    hooks/*; the case that the replacement asks the port stays in test_control.)"""

    def test_no_shipped_script_uses_pkill(self):
        import glob
        here = os.path.dirname(os.path.abspath(__file__))
        repo = os.path.dirname(here)
        targets = sorted(glob.glob(os.path.join(here, "*.sh"))
                         + glob.glob(os.path.join(repo, "hooks", "*")))
        checked = 0
        for path in targets:
            if os.path.isdir(path):
                continue
            try:
                with io.open(path, encoding="utf-8", errors="replace") as fh:
                    src = fh.read()
            except Exception:
                continue
            checked += 1
            for n, line in enumerate(src.split("\n"), 1):
                bare = line.split("#", 1)[0]          # CODE only — prose explains the ban
                self.assertNotIn("pkill", bare,
                                 "%s:%d kills by NAME PATTERN — it cannot tell his live console "
                                 "from a grep that happens to contain the string. Ask the PORT "
                                 "who holds it and kill that pid.\n    %s"
                                 % (os.path.basename(path), n, line.strip()[:100]))
        self.assertGreater(checked, 2, "the guard scanned almost nothing — it proves nothing")


class TestV2175EveryPaidLaneRemembersWhatItAlreadyBOUGHT(unittest.TestCase):
    """THE LAW, not the instance: a lane that SPENDS names what stops it re-buying. (REG-2362: the case that reads
    every tv/*.py for a paid reader; the registry and its other cases stay in test_control and are borrowed.)"""

    PAID_LANES = _TC.TestV2175EveryPaidLaneRemembersWhatItAlreadyBOUGHT.PAID_LANES

    def test_every_module_that_SPENDS_is_in_the_registry(self):
        """If a new module starts calling a paid reader, it appears here and this goes red until
        someone says what stops it re-buying. That is the point."""
        import glob
        here = os.path.dirname(os.path.abspath(__file__))
        spenders = set()
        for path in glob.glob(os.path.join(here, "*.py")):
            base = os.path.basename(path)
            if base.startswith("test_"):
                continue
            with io.open(path, encoding="utf-8", errors="replace") as fh:
                src = fh.read()
            code = "\n".join(l.split("#", 1)[0] for l in src.split("\n"))
            if "read_page(" in code or "_oneshot(" in code:
                spenders.add(base)
        known = {m for m, _ in self.PAID_LANES.values()} | {
            "control_app.py",          # the orchestrator: it OWNS the memories, it is not a lane
            # ⚠ FOUND BY THIS TEST ON ITS FIRST RUN, which is the whole point of writing it as a
            # law. tv_diablo is the READER, not a lane: it never decides WHAT to buy — the sweep
            # and the hunt hand it a page. Its one self-directed spend is the crop-refused retry
            # (crop first, full frame once if the crop answer is refused), bounded at exactly one
            # extra read per page and pinned by the case below. If that ever becomes a loop, this
            # module needs a memory like the others.
            "tv_diablo.py",
        }
        unregistered = spenders - known
        self.assertFalse(unregistered,
                         "these modules call a PAID reader and are not in PAID_LANES, so nothing "
                         "says what stops them buying the same thing twice: %s"
                         % sorted(unregistered))


class TestReg3077NoSpecInTheFolderPinsBetweenLoads(unittest.TestCase):
    """REG-3077 - no spec on disk pins a store the board writes back between two loads. The keyed law holds the specs
    it names; this holds the ones nobody has named yet."""

    def test_no_spec_pins_a_written_back_store_between_two_loads(self):
        paths = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tests", "*.spec.ts")))
        raw, unchecked, n_pin = _pin_law.verdict(paths, _pin_law.persisted_stores())
        self.assertGreaterEqual(n_pin, _pin_law.MOVED, "PREMISE: the folder scan found %d pins of the %d REG-3076 moved"
                                % (n_pin, _pin_law.MOVED))
        self.assertEqual(raw, [], "a spec pins a store the board writes back between two loads - use pinEvaluate and "
                         "reloadPinned/gotoPinned (tests/_pin.ts): %s" % "; ".join(raw[:8]))
        self.assertEqual(unchecked, [], "a pin reaches a plain reload or goto, which never checks it arrived: %s"
                         % "; ".join(unchecked[:8]))


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "REG-079 - a suite on disk is registered by no gate: it can rot for a hundred versions looking maintained",
        "file": "run_gates.py",
        "find": "         [sys.executable, os.path.join(HERE, \"test_folder_scans.py\")], 600,\n",
        "replace": "         [sys.executable, os.path.join(HERE, \"test_folder_scan.py\")], 600,\n",
        "matches": 1,
    },
    {
        "why": "v1911 - a suite imports a package CI does not install (yaml): green here, the publish workflow down there",
        "file": "test_every_cli_that_prints_non_ascii_is_encoding_safe.py",
        "find": "if __name__ == \"__main__\":\n    unittest.main(verbosity=2)\n",
        "replace": "def _never_called():\n    import yaml  # noqa: F401\n\n\nif __name__ == \"__main__\":\n"
                   "    unittest.main(verbosity=2)\n",
        "matches": 1,
    },
    {
        "why": "v2010 - a shipped module calls a name nothing binds: inside a try it is silent forever",
        "file": "page_delta.py",
        "find": "from console_safe import enable as _console_safe_enable\n",
        "replace": "from console_safe import enable as _console_safe_enable\n\n\ndef _never_called():\n"
                   "    try:\n        return _no_such_name_is_bound_anywhere()\n    except Exception:\n"
                   "        return None\n",
        "matches": 1,
    },
    {
        "why": "his standing rule - a shipped script kills by NAME PATTERN and can take his live console down",
        "file": "hooks/pre-push",
        "find": "  echo \"          if CI is down, publish by hand: bash deploy.sh\"\nfi\n\nexit 0\n",
        "replace": "  echo \"          if CI is down, publish by hand: bash deploy.sh\"\nfi\npkill -f \"control_app.py "
                   "--no-open\" || true\n\nexit 0\n",
        "matches": 1,
    },
    {
        "why": "v2175 - a module starts spending paid reads with nothing that stops it re-buying",
        "file": "page_delta.py",
        "find": "from console_safe import enable as _console_safe_enable\n",
        "replace": "from console_safe import enable as _console_safe_enable\n\n\ndef _spends(p):\n"
                   "    return read_page(p)  # noqa: F821\n",
        "matches": 1,
    },
    {
        "why": "REG-3077 - a spec no law names pins rwMade between two loads",
        "file": "../tests/v2208_the_registrar_must_not_shadow_a_real_catalogue_entry.spec.ts",
        "find": "    await page.evaluate(() => localStorage.setItem('d2r_vaultBackfillUndo_v2205',\n",
        "replace": "    await page.evaluate(() => localStorage.setItem('d2r_rwMade',\n",
        "matches": 1,
    },
]
