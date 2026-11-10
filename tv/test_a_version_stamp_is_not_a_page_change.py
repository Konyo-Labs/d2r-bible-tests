# -*- coding: utf-8 -*-
"""REG-1753 (#160) - A VERSION STAMP IS NOT A PAGE CHANGE, AND ANYTHING ELSE STILL IS.

Every bump rewrites one line of bible.html (window.D2R_BUILD). The pre-push hook keyed its render (3-5 min) and its
Playwright smoke (~2 min) on the file NAME, so every console-only ship re-graded an unchanged page: measured on the
last 80 commits that touched bible.html, 46 changed nothing but that line. tv/page_delta.py now answers "changed
beyond its stamp?" for both triggers, and fails CLOSED.

This law holds four things:
  * a stamp-only commit is not a page change; a real page change, a stamp with code smuggled onto its line, and a
    change in the same commit beside the stamp all ARE (a real git repo, not a hand-built diff);
  * anything unreadable - a bad range - answers "changed", so the gates run;
  * the pattern matches the stamp line bump_version actually wrote into this tree (the join to the writer);
  * the hook asks page_delta for BOTH the render and the smoke trigger, and bible.html left the name-only lists.
Routine I asks the same question and one more: a spec, the Playwright config, the console page, a package
file or the workflow still runs the suite on its name. A schedule, a manual run, a new branch, a forced
push, and anything unreadable run it too. The fast shards are dealt by measured duration.
RED_PROOF below. [[the-unjoined-end]] [[unknown-stays-unknown]] [[source-reading-guard]]
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import page_delta as P  # noqa: E402
import routine_i_shards as S  # noqa: E402

STAMP = "  window.D2R_BUILD = { id:'%s', name:'%s - a ship', date:'2017-07-14', note:'%s' };\n"
BODY = "<html>\n<script>\n(function(){\n%s  var x = 1;\n})();\n</script>\n</html>\n"


def _git(repo, *args):
    r = subprocess.run(["git"] + list(args), cwd=repo, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError("git %s failed: %s" % (" ".join(args), r.stderr.strip()))
    return r.stdout.strip()


class _Repo(unittest.TestCase):

    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="page_delta_law_")
        self.addCleanup(shutil.rmtree, self.repo, True)
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        _git(self.repo, "config", "user.email", "law@example.invalid")
        _git(self.repo, "config", "user.name", "law")
        _git(self.repo, "config", "commit.gpgsign", "false")
        self.base = self.commit(BODY % (STAMP % ("v100", "v100", "first")))

    def commit(self, page_text, other=None):
        io.open(os.path.join(self.repo, "bible.html"), "w", encoding="utf-8").write(page_text)
        if other:
            io.open(os.path.join(self.repo, "other.txt"), "w", encoding="utf-8").write(other)
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "c", "--allow-empty")
        return _git(self.repo, "rev-parse", "HEAD")

    def changed(self, head):
        return P.page_changed(["%s..%s" % (self.base, head)], repo=self.repo)[0]


class AStampIsNotAPageChange(_Repo):

    def test_baseline_the_name_alone_says_the_page_changed(self):
        # PREMISE: the old trigger (the file's NAME in the diff) fires on a stamp-only bump - the cost this law removes
        head = self.commit(BODY % (STAMP % ("v101", "v101", "second")))
        names = _git(self.repo, "diff", "--name-only", "%s..%s" % (self.base, head))
        self.assertIn("bible.html", names.split())

    def test_a_stamp_only_bump_is_not_a_page_change(self):
        head = self.commit(BODY % (STAMP % ("v101", "v101", "a note with an escaped \\' quote")))
        self.assertFalse(self.changed(head))

    def test_two_bumps_in_one_range_are_still_only_the_stamp(self):
        self.commit(BODY % (STAMP % ("v101", "v101", "second")))
        head = self.commit(BODY % (STAMP % ("v102", "v102", "third")))
        self.assertFalse(self.changed(head))

    def test_an_untouched_page_is_not_a_page_change(self):
        head = self.commit(BODY % (STAMP % ("v100", "v100", "first")), other="console only")
        self.assertFalse(self.changed(head))


class AnythingElseStillIs(_Repo):

    def test_a_real_page_change_is_a_page_change(self):
        head = self.commit((BODY % (STAMP % ("v100", "v100", "first"))).replace("var x = 1;", "var x = 2;"))
        self.assertTrue(self.changed(head))

    def test_a_stamp_and_a_page_change_together_are_a_page_change(self):
        head = self.commit((BODY % (STAMP % ("v101", "v101", "second"))).replace("var x = 1;", "var x = 2;"))
        self.assertTrue(self.changed(head))

    def test_code_smuggled_onto_the_stamp_line_is_a_page_change(self):
        smuggled = (STAMP % ("v101", "v101", "second")).rstrip("\n") + " window.evil = 1;\n"
        head = self.commit(BODY % smuggled)
        self.assertTrue(self.changed(head))

    # REG-1942 - the #231 eye on v3568. MEASURED on real `git diff -U0` output before the fix: each of these four read
    # as stamp-only (changed=False), so the pre-push hook skipped render and smoke while the deploy published them.
    def test_a_removed_page_line_that_starts_with_two_dashes_is_a_page_change(self):
        base = BODY % (STAMP % ("v100", "v100", "first"))
        self.base = self.commit(base.replace("  var x = 1;\n", "  var x = 1;\n-->\n"))
        head = self.commit(BODY % (STAMP % ("v101", "v101", "second")))
        diff = _git(self.repo, "diff", "-U0", "%s..%s" % (self.base, head))
        self.assertIn("\n--->", diff, "PREMISE: the removed '-->' reads '--->' in the diff")
        self.assertTrue(self.changed(head), "a removed page line was skipped as a file header")

    def test_an_added_page_line_that_starts_with_two_pluses_is_a_page_change(self):
        head = self.commit((BODY % (STAMP % ("v101", "v101", "second"))).replace("  var x = 1;\n",
                                                                                 "  var x = 1;\n++i;\n"))
        self.assertTrue(self.changed(head), "an added page line was skipped as a file header")

    def test_deleting_the_stamp_is_a_page_change(self):
        head = self.commit(BODY % "")
        self.assertTrue(self.changed(head), "a page that lost its D2R_BUILD read as a stamp-only bump")

    def test_a_stamp_whose_note_closes_the_script_is_a_page_change(self):
        head = self.commit(BODY % (STAMP % ("v101", "v101", "closed the </script> tag")))
        self.assertTrue(self.changed(head), "a note that ends the <script> block read as a stamp-only bump")

    def test_a_bare_diff_still_has_its_two_header_lines_skipped(self):
        diff = ("--- a/bible.html\n+++ b/bible.html\n@@ -3 +3 @@\n-" + STAMP % ("v1", "v1", "a") +
                "+" + STAMP % ("v2", "v2", "b"))
        self.assertTrue(P.stamp_only(diff))

    def test_a_range_git_cannot_read_runs_the_gates(self):
        changed, why = P.page_changed(["no-such-ref..also-not"], repo=self.repo)
        self.assertTrue(changed)
        self.assertIn("UNKNOWN", why)

    def test_the_cli_exit_says_changed_on_a_bad_call(self):
        self.assertEqual(P.main([]), 0)


class TheJoinToTheWriter(unittest.TestCase):

    def test_the_pattern_matches_the_stamp_bump_version_wrote_into_this_tree(self):
        src = io.open(os.path.join(REPO, "bible.html"), encoding="utf-8").read()
        lines = [l for l in src.split("\n") if l.startswith("  window.D2R_BUILD = { id:'")]
        self.assertEqual(len(lines), 1, "PREMISE: the stamp line bump_version replaces is not exactly once")
        self.assertTrue(P.STAMP_LINE.match(lines[0]),
                        "the stamp line in this tree no longer matches page_delta.STAMP_LINE - bump_version's "
                        "format moved, so every bump would now read as a page change: %s" % lines[0][:160])


class TheHookAsksIt(unittest.TestCase):

    def setUp(self):
        raw = io.open(os.path.join(REPO, "hooks", "pre-push"), encoding="utf-8").read()
        self.code = "\n".join(l for l in raw.split("\n") if not l.lstrip().startswith("#"))

    def test_the_render_trigger_asks_page_delta_for_the_range_and_the_index(self):
        self.assertEqual(self.code.count('python3 "$REPO/tv/page_delta.py" --range "$_px_range"'), 1)
        self.assertEqual(self.code.count('python3 "$REPO/tv/page_delta.py" --cached'), 1)

    def test_the_smoke_trigger_asks_page_delta_for_each_ref(self):
        self.assertEqual(self.code.count(
            'python3 "$REPO/tv/page_delta.py" --range "$remote_sha..$local_sha" </dev/null'), 1)

    def test_bible_html_left_the_name_only_triggers(self):
        watch = re.findall(r"_px_watch='([^']*)'", self.code)
        self.assertEqual(len(watch), 1, "PREMISE: the render watch list is not declared exactly once")
        self.assertNotIn("bible", watch[0])
        self.assertNotIn("'^(bible\\.html|tests/.*\\.spec\\.ts)$'", self.code)


class RoutineIOnRealHistory(unittest.TestCase):
    """The two commits the workflow has to get right, on this repo, not a hand-built diff."""

    PINNED = ("debc96a5", "f5919534", "a8246cdf", "a8246cdf^")

    @classmethod
    def setUpClass(cls):
        # A checkout that does not hold these commits cannot grade them: the decision fails closed ("could not read")
        # and the page-change case would pass for THAT reason. The agent-tests runner keeps 200 commits and these sit
        # deeper every day, so there the class is UNMEASURED and says so; RoutineIFailsClosed grades the logic anywhere.
        miss = [c for c in cls.PINNED if subprocess.run(["git", "-C", REPO, "cat-file", "-e", c + "^{commit}"],
                                                         capture_output=True).returncode != 0]
        if miss:
            raise unittest.SkipTest("UNMEASURED - this checkout does not hold %s (a shallow clone)" % ", ".join(miss))

    def test_a_stamp_only_push_skips(self):
        # debc96a5..f5919534 is the v3575 stamp. bible.html moved one line; nothing under tests/ did.
        run, why = P.routine_i_decision("push", "debc96a5", "f5919534", repo=REPO)
        self.assertFalse(run)
        self.assertEqual(why, P.ROUTINE_I_SKIP)

    def test_a_real_page_change_runs(self):
        # a8246cdf edits bible.html past the stamp line (+18/-1).
        run, why = P.routine_i_decision("push", "a8246cdf^", "a8246cdf", repo=REPO)
        self.assertTrue(run)
        self.assertNotEqual(why, P.ROUTINE_I_SKIP)

    def test_the_cli_exit_matches_both(self):
        self.assertEqual(P.main(["--routine-i", "--before", "debc96a5", "--sha", "f5919534"]), 1)
        self.assertEqual(P.main(["--routine-i", "--before", "a8246cdf^", "--sha", "a8246cdf"]), 0)
        self.assertEqual(P.main(["--routine-i"]), 0)
        self.assertEqual(P.main(["--routine-i", "--before", "debc96a5"]), 0)


class RoutineIFailsClosed(_Repo):

    def test_a_schedule_and_a_manual_run_grade_the_page(self):
        for event in ("schedule", "workflow_dispatch"):
            run, why = P.routine_i_decision(event, "debc96a5", "f5919534", repo=REPO)
            self.assertTrue(run, event)
            self.assertIn("not a push", why)

    def test_a_blank_before_and_a_forced_push_run(self):
        run, why = P.routine_i_decision("push", "0" * 40, "f5919534", repo=REPO)
        self.assertTrue(run)
        self.assertIn("new branch", why)
        run, why = P.routine_i_decision("push", "", "f5919534", repo=REPO)
        self.assertTrue(run)
        head = self.commit(BODY % (STAMP % ("v101", "v101", "second")))
        run, why = P.routine_i_decision("push", self.base, head, repo=self.repo, forced=True)
        self.assertTrue(run)
        self.assertIn("forced", why)

    def test_a_stamp_only_push_skips_on_a_history_built_here(self):
        """v3860 - THE SKIP, GRADED ON ANY VENUE. Only RoutineIOnRealHistory asked for the skip, on four pinned commits a
        shallow checkout does not hold - so on the CI prover that class is UNMEASURED, and the red-proof that turns the
        skip into a run (REG-1753) stayed GREEN on every proof-keys run since 10-23 (BLIND, shard 2). Same question,
        on a history this case builds: a push whose only change is the build stamp skips the suite, and says so."""
        head = self.commit(BODY % (STAMP % ("v101", "v101", "second")))
        run, why = P.routine_i_decision("push", self.base, head, repo=self.repo)
        self.assertFalse(run, "a stamp-only push ran Routine I: %s" % why)
        self.assertEqual(why, P.ROUTINE_I_SKIP)

    def test_a_range_git_cannot_read_runs_the_suite(self):
        run, why = P.routine_i_decision("push", "no-such-before", "no-such-sha", repo=self.repo)
        self.assertTrue(run)
        self.assertIn("could not", why)

    def test_a_spec_beside_a_stamp_still_runs(self):
        os.makedirs(os.path.join(self.repo, "tests"))
        page = BODY % (STAMP % ("v101", "v101", "second"))
        io.open(os.path.join(self.repo, "bible.html"), "w", encoding="utf-8").write(page)
        io.open(os.path.join(self.repo, "tests", "added.spec.ts"), "w", encoding="utf-8").write(
            "test('added', () => {})\n")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "c")
        head = _git(self.repo, "rev-parse", "HEAD")
        run, why = P.routine_i_decision("push", self.base, head, repo=self.repo)
        self.assertTrue(run)
        self.assertIn("tests/added.spec.ts", why)

    def test_the_console_page_and_the_workflow_run_on_their_names(self):
        for rel in ("tv/control_ui.html", "playwright.config.ts",
                    ".github/workflows/routine-i-playwright.yml", "package.json",
                    "package-lock.json"):
            parent = _git(self.repo, "rev-parse", "HEAD")
            os.makedirs(os.path.dirname(os.path.join(self.repo, rel)), exist_ok=True)
            io.open(os.path.join(self.repo, rel), "w", encoding="utf-8").write("x\n")
            _git(self.repo, "add", "-A")
            _git(self.repo, "commit", "-q", "-m", "c")
            head = _git(self.repo, "rev-parse", "HEAD")
            run, why = P.routine_i_decision("push", parent, head, repo=self.repo)
            self.assertTrue(run, rel)
            self.assertIn(rel, why)


class RoutineISaysWhenItSkips(unittest.TestCase):

    def setUp(self):
        raw = io.open(os.path.join(REPO, ".github", "workflows", "routine-i-playwright.yml"),
                      encoding="utf-8").read()
        self.raw = raw
        self.code = "\n".join(l for l in raw.split("\n") if not l.lstrip().startswith("#"))

    def test_the_suite_runs_unless_the_check_says_skip(self):
        self.assertEqual(self.code.count("needs.stamp-check.outputs.run != 'false'"), 3)
        self.assertIn("git fetch --depth=1 origin", self.code)
        self.assertIn("0000000000000000000000000000000000000000", self.code)
        self.assertIn('python3 tv/page_delta.py --routine-i --before', self.code)
        self.assertIn("cron: '0 6 * * *'", self.code)
        self.assertIn("workflow_dispatch:", self.code)
        self.assertEqual(self.raw.count(P.ROUTINE_I_SKIP), 2)
        self.assertIn('name: "skipped: stamp-only"', self.code)
        self.assertNotIn("--shard=${{ matrix.shard }}/6", self.code)
        self.assertIn("--shard=${{ matrix.shard }}/2", self.code)
        self.assertIn('python3 tv/routine_i_shards.py --shard "$SHARD" --of ', self.code)

    def test_the_fast_matrix_the_dealer_and_the_blob_floor_are_one_count(self):
        """The dealer, the matrix and the merge floor are one number.

        A matrix of 10 with a merge floor still set for 8 lets a dead shard
        through: 9 fast blobs plus 2 slow is 11, and 11 is not less than 8.
        """
        # v3891 (#194) - the ONE number is the stamp check's chosen count (measured spec costs), not a hand-set 10: the
        # dealer, the matrix and the merge floor all read needs.stamp-check.outputs, and its fallback list is 1..fallback
        import re
        self.assertIn('python3 tv/routine_i_shards.py --shard "$SHARD" --of "$N"', self.code, "the fast job no longer asks the dealer")
        self.assertEqual(self.code.count("N: ${{ needs.stamp-check.outputs.n }}"), 2,
                         "the dealer and the merge floor do not both read the stamp check's one count")
        self.assertIn("shard: ${{ fromJSON(needs.stamp-check.outputs.list) }}", self.code)
        fb = re.search(r"n: \$\{\{ steps\.count\.outputs\.n \|\| '(\d+)' \}\}", self.code)
        lst = re.search(r"list: \$\{\{ steps\.count\.outputs\.list \|\| '\[([\d,]+)\]' \}\}", self.code)
        self.assertTrue(fb and lst, "the stamp check's count outputs (or their fallbacks) are gone")
        self.assertEqual([int(x) for x in lst.group(1).split(",")], list(range(1, int(fb.group(1)) + 1)))
        slow = 2
        self.assertIn("want=$(( N + %d ))" % slow, self.code)
        self.assertIn('[ "$n" -lt "$want" ]', self.code)


class TheFastShardsFollowMeasuredDuration(unittest.TestCase):

    def test_every_fast_spec_is_on_exactly_one_shard(self):
        specs = S.fast_specs(REPO)
        self.assertIsNotNone(specs)
        self.assertGreater(len(specs), 400)
        shards = S.deal(specs, 6, S.load_costs())
        self.assertEqual(len(shards), 6)
        flat = [p for shard in shards for p in shard]
        self.assertEqual(sorted(flat), specs)
        self.assertTrue(all(shards))
        for slow in ("v645_every_item_sim.spec.ts", "golden_intake.spec.ts",
                     "v42_full_ux_audit.spec.ts"):
            self.assertFalse(any(p.endswith(slow) for p in flat), slow)

    def test_the_six_heaviest_files_land_on_six_shards(self):
        costs = S.load_costs()
        self.assertGreater(max(costs.values()), 100)
        self.assertIn("37139166700", io.open(S.TABLE, encoding="utf-8").read())
        specs = S.fast_specs(REPO)
        shards = S.deal(specs, 6, costs)
        heavy = sorted((p for p in costs if p in specs), key=lambda p: (-costs[p], p))[:6]
        owners = []
        for path in heavy:
            owners.append(next(i for i, shard in enumerate(shards) if path in shard))
        self.assertEqual(len(set(owners)), 6, heavy)
        # V1: weigh each file the way deal() weighs it - a spec the table has not timed yet weighs the median,
        # not 0, or every new spec reads as an imbalance the deal never made
        loads = [sum(S.file_weight(p, specs, costs) for p in shard) for shard in shards]
        self.assertLess(max(loads) - min(loads), 30, loads)

    def test_a_file_the_table_has_not_seen_weighs_the_median(self):
        costs = {"tests/a.spec.ts": 10.0, "tests/b.spec.ts": 30.0}
        names = ["tests/a.spec.ts", "tests/b.spec.ts", "tests/new.spec.ts"]
        self.assertEqual(S.file_weight("tests/new.spec.ts", names, costs), 20.0)

    def test_an_unreadable_table_still_names_every_file(self):
        shards = S.deal(["tests/a.spec.ts", "tests/b.spec.ts"], 2, None)
        self.assertEqual(sorted(p for shard in shards for p in shard),
                         ["tests/a.spec.ts", "tests/b.spec.ts"])


RED_PROOF = [
    {"why": "REG-1753 - every changed line counted as a stamp: a real page change skips render and smoke",
     "file": "page_delta.py",
     "find": "        if not _is_stamp(line[1:]):\n            return False\n",
     "replace": "        if False:\n            return False\n",
     "matches": 1},
    {"why": "REG-1942 - every +++/--- line is skipped as a header again: a removed '-->' or an added '++i;' "
            "beside a stamp bump reads as stamp-only and render + smoke are skipped",
     "file": "page_delta.py",
     "find": "        if in_header or not line or line[0] not in \"+-\":\n",
     "replace": "        if in_header or not line or line[0] not in \"+-\" or line.startswith((\"+++\", \"---\")):\n",
     "matches": 1},
    {"why": "REG-1942 - a removed stamp no longer needs an added one: deleting D2R_BUILD reads as stamp-only",
     "file": "page_delta.py",
     "find": "    return added > 0 and added == removed\n",
     "replace": "    return added + removed > 0\n",
     "matches": 1},
    {"why": "REG-1942 - a stamp whose note closes the <script> block reads as stamp-only",
     "file": "page_delta.py",
     "find": "    return bool(STAMP_LINE.match(text)) and not _HTML_BREAK.search(text)\n",
     "replace": "    return bool(STAMP_LINE.match(text))\n",
     "matches": 1},
    {"why": "REG-1753 - a stamp-only bump answered as a page change: the skip never happens",
     "file": "page_delta.py",
     "find": "        if stamp_only(diff.stdout):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-1753 - a range git cannot read answered as unchanged: the gates skip on an UNKNOWN",
     "file": "page_delta.py",
     "find": "        if names.returncode != 0:\n            return True, ",
     "replace": "        if names.returncode != 0:\n            return False, ",
     "matches": 1},
    {"why": "REG-1753 - the stamp pattern loosened to any D2R_BUILD line: code on the stamp line skips the gates",
     "file": "page_delta.py",
     "find": "    r\"date:'\\d{4}-\\d{2}-\\d{2}', note:'(?:[^'\\\\]|\\\\.)*' \\};\\s*$\")",
     "replace": "    r\"date:'\\d{4}-\\d{2}-\\d{2}', note:'(?:[^'\\\\]|\\\\.)*' \\};\")",
     "matches": 1},
    {"why": "REG-1753 - a stamp-only push ran Routine I: the skip never happens",
     "file": "page_delta.py",
     "find": "            return False, ROUTINE_I_SKIP\n",
     "replace": "            return True, ROUTINE_I_SKIP\n",
     "matches": 1},
    {"why": "REG-1753 - a tests change beside a stamp skipped Routine I",
     "file": "page_delta.py",
     "find": "            if _routine_i_force(p):\n",
     "replace": "            if False and _routine_i_force(p):\n",
     "matches": 1},
    {"why": "REG-1753 - a push git cannot read skipped Routine I",
     "file": "page_delta.py",
     "find": "        if names.returncode != 0:\n            return (True, \"git could not list the push",
     "replace": "        if names.returncode != 0:\n            return (False, \"git could not list the push",
     "matches": 1},
    {"why": "REG-1753 - a shallow checkout could not see the base and the suite was skipped",
     "file": ".github/workflows/routine-i-playwright.yml",
     "find": "git fetch --depth=1 origin",
     "replace": "git status",
     "matches": 1},
    {"why": "REG-1753 - a skipped suite was read as a merged verdict",
     "file": ".github/workflows/routine-i-playwright.yml",
     "find": "needs.stamp-check.outputs.run != 'false'",
     "replace": "needs.stamp-check.outputs.run == 'skip'",
     "matches": 3},
    {"why": "REG-1753 - a stamp-only skip said nothing",
     "file": ".github/workflows/routine-i-playwright.yml",
     "find": "bible.html changed only its build stamp — the suite has nothing new to grade; the daily 09:00 run covers these bytes",
     "replace": "stamp-only",
     "matches": 2},
    {"why": "REG-1753 - the fast shards went back to a file-count split",
     "file": ".github/workflows/routine-i-playwright.yml",
     "find": "npx playwright test --project=chromium --reporter=blob",
     "replace": "npx playwright test --project=chromium --shard=${{ matrix.shard }}/6 --reporter=blob",
     "matches": 1},
    {"why": "REG-1753 - duration was ignored, so one heavy shard is the floor again",
     "file": "routine_i_shards.py",
     "find": "    order = sorted(names, key=lambda n: (-file_weight(n, names, costs), n))\n",
     "replace": "    order = sorted(names, key=lambda n: (0, n))\n",
     "matches": 1},
    {"why": "REG-1753 - a spec the table has not seen weighed nothing and piled onto one shard",
     "file": "routine_i_shards.py",
     "find": "        return float(med)\n",
     "replace": "        return 0.0\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
