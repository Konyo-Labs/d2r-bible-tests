# -*- coding: utf-8 -*-
"""#181 (REG-2470, REG-2471) - A PC SHOWS ONLY ITS OWN LIVE TRIALS.

tv/.self_arming.jsonl is TRACKED: it ships to every PC with every update, while its own comment called it
untracked. MEASURED at 7285e7efc: 657 rows = sabotage 583, cross-family 25, LIVE 49, and every live row was measured
on Konyo's Mac - his running console, his shelf, his disk history, his window. Dean's heart scored them as its own:
frame.release "earned 85/85" was 35 code rows plus 50 of the Mac's live checks.

THE SPLIT. A sabotage, a cross-family refusal or a CI red is a property of the CODE and stays in the shared ledger. A
LIVE trial is a property of the PC that ran it, so bank(), record() and the deferred fold send it to THAT PC's own
ledger (TV_SELF_ARMING_HERE names it). A live row already in the shared file is LEGACY: counted on no PC, reported as a
count, until the PC that measured it runs the adoption door
`python3 tv/self_arming.py --adopt-legacy-live --reason "<why>" --confirm`. The shared file's bytes are never edited.

ONE PER PC, NOT ONE PER CHECKOUT (REG-2473, the review of the first cut). The per-PC ledger was the gitignored
tv/.self_arming.here.jsonl of whichever checkout ran - and fleet agents work only in linked worktrees, so a deliberate
live bank from one landed where his console never reads and `git worktree remove` deleted it. It now lives in git's
COMMON dir (heart2._git_common_dir, the R10 precedent), shared by the main checkout and every linked worktree; the tv/
file is used only where no git dir exists, and every surface says which of the two it is. The door's sentence names the
whole path and the checkout it ran from - a basename read as success from the wrong checkout.

Two PCs, each in this law's own scratch (TV_SELF_ARMING_LEDGER / TV_SELF_ARMING_HERE). The shared fixture is a COPY
of the tracked ledger, so the rows are real and nothing of his is written:
  * PC-B (no per-PC file) has no 'live' kind and its k/n are the code rows; byOrigin says nothing was measured there.
  * PC-A counts its own live rows, and only those; PC-B beside it still sees none of them.
  * bank()/record() of a live trial leave the shared fixture byte-identical; fold_deferred routes the same way.
  * git's own matcher ignores the per-PC name and not the shared one (a throwaway repo, GIT_* scrubbed for its scope).
  * a main checkout and its linked worktree (laid out as git lays them out, no git run) resolve ONE ledger, inside the
    common dir and inside neither work tree; a tree with no git dir keeps its own and says why; a patch is honoured.
  * adoption: no reason is refused, no --confirm writes nothing, --confirm writes marked rows that keep their age,
    a second --confirm writes nothing, the PC then reads exactly what it read before the split, and the sentence
    names the whole path and the checkout.
RED_PROOF below.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import self_arming as SA  # noqa: E402

GIT = shutil.which("git")
#: every seam this law sets, held and restored per case - a fixture never leaves one behind
_ENV = ("TV_SELF_ARMING_LEDGER", "TV_SELF_ARMING_HERE", "TV_SELF_ARMING_DEFER", "TV_HEART_CENSUS")


def _shared_bytes():
    """The tracked shared ledger, READ - the fixture is a copy of it, never the file itself."""
    with io.open(os.path.join(HERE, ".self_arming.jsonl"), "rb") as fh:
        return fh.read()


def _all_locks():
    return sorted(SA.LOCKS) + sorted(SA.ROUTES)


class _TwoPCs(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="perpc-arming-")
        self.addCleanup(shutil.rmtree, self.d, True)
        held = {k: os.environ.pop(k, None) for k in _ENV}

        def _restore():
            for k in _ENV:
                os.environ.pop(k, None)
            for k, v in held.items():
                if v is not None:
                    os.environ[k] = v
        self.addCleanup(_restore)
        raw = _shared_bytes()
        self.shared = os.path.join(self.d, "shared.jsonl")
        with io.open(self.shared, "wb") as fh:
            fh.write(raw)
        os.environ["TV_SELF_ARMING_LEDGER"] = self.shared
        # report() asks the heart; an absent census here keeps it off his real one (and off this law's subject)
        os.environ["TV_HEART_CENSUS"] = os.path.join(self.d, "no-census.json")
        self.rows = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
        self.legacy = [r for r in self.rows if r.get("kind") == "live"]
        self.code = [r for r in self.rows if r.get("kind") != "live"]

    def pc(self, name, rows=None):
        """Make <name> THIS PC: its own ledger file, absent unless rows are given. -> path"""
        p = os.path.join(self.d, name + ".here.jsonl")
        if rows is not None:
            with io.open(p, "w", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r) + "\n")
        os.environ["TV_SELF_ARMING_HERE"] = p
        return p

    @staticmethod
    def lines(p):
        if not os.path.exists(p):
            return []
        with io.open(p, encoding="utf-8") as fh:
            return [json.loads(x) for x in fh.read().splitlines() if x.strip()]

    def shared_now(self):
        with io.open(self.shared, "rb") as fh:
            return fh.read()


class APcWithNoTrialsOfItsOwn(_TwoPCs):
    def test_premise_the_shared_ledger_carries_one_installs_live_rows(self):
        self.assertTrue(self.legacy, "the shared ledger holds no live row, so PC-B below proves nothing about them")
        self.assertTrue(self.code, "the shared ledger holds no code row - the fixture is not the real ledger")

    def test_pc_b_scores_the_code_rows_and_nothing_measured_elsewhere(self):
        self.pc("pcB")
        for lock in _all_locks():
            got = SA.score(lock)
            want = SA.score(lock, rows=self.code)
            self.assertNotIn("live", got.get("kinds") or [],
                             "%s on a PC that ran no live trial still carries the 'live' kind" % lock)
            self.assertEqual((got["k"], got["n"], got["state"]), (want["k"], want["n"], want["state"]),
                             "%s on PC-B is not the code rows' score" % lock)
            self.assertEqual(got["byOrigin"]["code"], {"k": want["k"], "n": want["n"]}, lock)
            self.assertIsNone(got["byOrigin"]["here"], "%s says PC-B measured something" % lock)
            self.assertIn("nothing measured on this PC yet", got["hereSay"], lock)
            self.assertEqual(got["legacyLive"], sum(1 for r in self.legacy if r.get("lock") == lock),
                             "%s does not say how many legacy live rows it left out" % lock)

    def test_the_figure_dean_saw_included_another_pcs_trials(self):
        """The pre-split reading (every shared row counted) against PC-B's, for every lock that has legacy rows."""
        self.pc("pcB")
        touched = sorted({r.get("lock") for r in self.legacy})
        self.assertTrue(touched)
        for lock in touched:
            old = SA.score(lock, rows=self.rows)
            new = SA.score(lock)
            self.assertGreater(old["n"], new["n"],
                               "%s: the pre-split n is not larger, so the legacy rows were never in it" % lock)

    def test_the_report_says_what_it_left_out(self):
        self.pc("pcB")
        rep = SA.report()
        self.assertTrue(rep.get("ok"), rep.get("why"))
        led = rep.get("ledger") or {}
        self.assertEqual(led.get("legacyLive"), len(self.legacy))
        self.assertEqual(led.get("legacyAdoptedHere"), 0)
        self.assertEqual(led.get("hereRows"), 0)
        self.assertIn("counted on no PC", led.get("legacyLiveSay") or "")


class APcWithItsOwnTrials(_TwoPCs):
    def test_pc_a_counts_its_own_live_rows_and_only_those(self):
        self.pc("pcA")
        before = SA.score("frame.release")
        SA.bank("frame.release", "live", "frame_release_live", n=7, k=7, attacks=1, ref="pcA-seals",
                note="PC-A's own seals")
        after = SA.score("frame.release")
        self.assertEqual(after["n"], before["n"] + 7)
        self.assertIn("live", after["kinds"])
        self.assertEqual(after["byOrigin"]["here"]["n"], 7)
        self.assertEqual(after["byOrigin"]["code"]["n"], before["n"])
        self.assertIn("measured on this PC", after["hereSay"])
        self.pc("pcB")
        self.assertEqual(SA.score("frame.release")["n"], before["n"], "PC-B counted PC-A's trial")

    def test_a_live_trial_leaves_the_shared_ledger_byte_identical(self):
        pa = self.pc("pcA")
        b0 = self.shared_now()
        SA.bank("vault.apply", "live", "vault_live", n=3, k=3, attacks=1)
        SA.record("vault.apply", "live", True, src="vault_live")
        self.assertEqual(self.shared_now(), b0, "a live trial was written into the SHARED (tracked) ledger")
        self.assertEqual([r["kind"] for r in self.lines(pa)], ["live", "live"])

    def test_a_code_proof_still_lands_in_the_shared_ledger(self):
        pa = self.pc("pcA")
        n0 = len(self.lines(self.shared))
        SA.bank("vault.apply", "sabotage", "vault_wilson", n=2, k=2, attacks=2, ref="pc-split-baseline")
        got = self.lines(self.shared)
        self.assertEqual(len(got), n0 + 1)
        self.assertEqual(got[-1]["kind"], "sabotage")
        self.assertEqual(self.lines(pa), [], "a code proof went to one PC's ledger")

    def test_the_deferred_fold_routes_a_live_row_to_this_pc(self):
        pa = self.pc("pcA")
        live = {"lock": "printer.stream", "kind": "live", "src": "printer_live", "ref": "fold", "n": 1, "k": 1,
                "refused": True, "attacks": 1, "withdrawn": False, "note": "", "ts": 1}
        code = dict(live, kind="sabotage", src="printer_wilson")
        d = os.path.join(self.d, "defer.jsonl")
        with io.open(d, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(live) + "\n" + json.dumps(code) + "\n")
        n0 = len(self.lines(self.shared))
        self.assertEqual(SA.fold_deferred(d), (2, 0))
        got = self.lines(self.shared)
        self.assertEqual(got[n0:], [code], "the fold did not put exactly the code row in the shared ledger")
        self.assertEqual(self.lines(pa), [live], "the fold did not put the live row in this PC's ledger")
        self.assertEqual(SA.LAST_FOLD, {"shared": 1, "here": 1})


class TheSplitHoldsAtTheRead(_TwoPCs):
    def test_a_code_row_in_this_pcs_ledger_fails_the_read_closed(self):
        row = dict(self.code[-1])
        self.pc("pcA", rows=[row])
        rows, why = SA._rows()
        self.assertIsNone(rows, "a code row in one PC's ledger was read as evidence")
        self.assertIn("only this PC's LIVE trials", why)
        self.assertEqual(SA.score(row["lock"])["state"], SA.UNKNOWN)

    def test_a_redirected_queue_never_reaches_this_pcs_real_ledger(self):
        os.environ.pop("TV_SELF_ARMING_HERE", None)
        p = os.path.abspath(SA._here_path())
        self.assertNotEqual(p, os.path.abspath(SA.HERE_LEDGER),
                            "a fixture that moved the shared queue would read and write HIS per-PC ledger")
        self.assertTrue(p.startswith(os.path.abspath(self.d) + os.sep), p)


@unittest.skipIf(GIT is None, "git is absent - this case is UNMEASURED, not passing")
class GitIgnoresThePerPcLedger(unittest.TestCase):
    def test_the_per_pc_name_is_ignored_and_the_shared_one_is_not(self):
        # a linked-worktree push exports GIT_DIR into the hook; this case's throwaway repo must never see it
        _gitenv = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("GIT_")}
        self.addCleanup(os.environ.update, _gitenv)
        env = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))
        d = tempfile.mkdtemp(prefix="perpc-ignore-")
        self.addCleanup(shutil.rmtree, d, True)
        subprocess.run([GIT, "init", "-q", d], check=True, env=env)
        subprocess.run([GIT, "-C", d, "config", "core.autocrlf", "false"], check=True, env=env)  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        os.makedirs(os.path.join(d, "tv"))
        for rel in (".gitignore", os.path.join("tv", ".gitignore")):
            if os.path.isfile(os.path.join(ROOT, rel)):
                shutil.copyfile(os.path.join(ROOT, rel), os.path.join(d, rel))

        def ignored(rel):
            return subprocess.run([GIT, "check-ignore", "-q", "--no-index", rel], cwd=d, env=env).returncode == 0
        self.assertTrue(ignored("tv/" + os.path.basename(SA.HERE_LEDGER)),
                        "one PC's live trials are one `git add -A` away from shipping to every PC")
        self.assertFalse(ignored("tv/.self_arming.jsonl"), "the SHARED ledger must stay trackable")


def _worktree_shape(root, name="wt1"):
    """A main checkout and one linked worktree, laid out as git lays them out (heart2's own law proves this layout is
    what a real `git worktree add` makes). No git is run, so no GIT_DIR a hook exported can reach anything. -> (main, wt)"""
    main = os.path.join(root, "main")
    wt = os.path.join(root, name)
    gd = os.path.join(main, ".git", "worktrees", name)
    for d in (os.path.join(main, "tv"), gd, os.path.join(wt, "tv")):
        os.makedirs(d)
    with io.open(os.path.join(gd, "commondir"), "w", encoding="utf-8") as fh:
        fh.write("../..\n")
    with io.open(os.path.join(wt, ".git"), "w", encoding="utf-8") as fh:
        fh.write("gitdir: %s\n" % gd)
    return main, wt


class TheLedgerIsOnePerPcNotOnePerCheckout(unittest.TestCase):
    """REG-2473 - every checkout of one machine reads and writes ONE per-PC ledger, in git's common dir."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="perpc-machine-")
        self.addCleanup(shutil.rmtree, self.d, True)
        held = {k: os.environ.pop(k, None) for k in _ENV}

        def _restore():
            for k in _ENV:
                os.environ.pop(k, None)
            for k, v in held.items():
                if v is not None:
                    os.environ[k] = v
        self.addCleanup(_restore)

    @staticmethod
    def _real(p):
        return os.path.normcase(os.path.realpath(p))

    def test_a_worktree_and_its_main_checkout_share_one_ledger(self):
        main, wt = _worktree_shape(self.d)
        pm, sm, _ = SA._here_where(repo=main)
        pw, sw, _ = SA._here_where(repo=wt)
        self.assertEqual((sm, sw), ("machine", "machine"),
                         "a checkout's per-PC ledger is not the machine's: %r / %r" % (sm, sw))
        self.assertEqual(self._real(pm), self._real(pw),
                         "a live bank from the worktree lands where the main checkout's console never reads")
        common = self._real(os.path.join(main, ".git"))
        self.assertTrue(self._real(pw).startswith(common + os.sep), "the ledger is not in git's common dir: %s" % pw)
        for tree in (main, wt):
            self.assertFalse(self._real(pw).startswith(self._real(os.path.join(tree, "tv")) + os.sep),
                             "the per-PC ledger sits in a work tree, so `git worktree remove` deletes it")

    def test_a_tree_with_no_git_dir_keeps_its_own_and_says_why(self):
        plain = os.path.join(self.d, "plain")
        os.makedirs(os.path.join(plain, "tv"))
        p, scope, why = SA._here_where(repo=plain)
        self.assertEqual(scope, "checkout")
        self.assertEqual(self._real(p), self._real(os.path.join(plain, "tv", ".self_arming.here.jsonl")))
        self.assertTrue(why, "a ledger that dies with its checkout does not say why")

    def test_a_patched_HERE_LEDGER_is_honoured(self):
        """A fixture that patches the attribute must get what it patched - silently resolving past it would write the
        machine's real ledger, the direction a fixture mistake must never go."""
        mine = os.path.join(self.d, "patched.here.jsonl")
        old = SA.HERE_LEDGER
        SA.HERE_LEDGER = mine
        self.addCleanup(setattr, SA, "HERE_LEDGER", old)
        self.assertEqual(SA._here_where()[:2], (mine, "patched"))
        self.assertEqual(SA._here_path(), mine)

    def test_the_label_names_the_kind_of_place_never_a_path(self):
        main, _wt = _worktree_shape(self.d)
        old = SA._machine_dir
        SA._machine_dir = lambda repo=None: (os.path.join(main, ".git"), None)
        self.addCleanup(setattr, SA, "_machine_dir", old)
        label = SA.here_label()
        self.assertIn("git's common dir", label)
        self.assertNotIn(self.d, label, "a gate log line carries a machine's path")


class TheAdoptionDoor(_TwoPCs):
    def test_no_reason_is_refused_and_writes_nothing(self):
        pa = self.pc("pcA")
        b0 = self.shared_now()
        for reason in (None, "", "   ", "--confirm"):
            res = SA.adopt_legacy_live(reason, confirm=True)
            self.assertFalse(res["ok"], reason)
            self.assertTrue(res["refused"], reason)
            self.assertIn("REFUSED", res["say"])
        self.assertFalse(os.path.exists(pa), "a refused adoption wrote this PC's ledger")
        self.assertEqual(self.shared_now(), b0)

    def test_a_dry_run_writes_nothing_and_says_what_it_would_adopt(self):
        pa = self.pc("pcA")
        b0 = self.shared_now()
        res = SA.adopt_legacy_live("this Mac measured them", confirm=False)
        self.assertTrue(res["ok"])
        self.assertTrue(res["dryRun"])
        self.assertEqual(res["wrote"], 0)
        self.assertEqual(res["would"], len(self.legacy))
        self.assertIn("DRY RUN", res["say"])
        self.assertFalse(os.path.exists(pa), "a dry run wrote this PC's ledger")
        self.assertEqual(self.shared_now(), b0)

    def test_confirm_writes_marked_rows_that_keep_their_age_and_only_once(self):
        pa = self.pc("pcA")
        b0 = self.shared_now()
        pre = dict((lock, SA.score(lock, rows=self.rows)) for lock in _all_locks())
        res = SA.adopt_legacy_live("this Mac measured them", confirm=True)
        self.assertTrue(res["ok"], res["say"])
        self.assertEqual(res["wrote"], len(self.legacy))
        got = self.lines(pa)
        self.assertEqual(len(got), len(self.legacy))
        for g, src in zip(got, self.legacy):
            self.assertEqual(g["adopted"]["reason"], "this Mac measured them")
            self.assertEqual(g["ts"], src["ts"], "an adopted trial took the copy's age, not the measurement's")
            self.assertEqual(dict((k, v) for k, v in g.items() if k != "adopted"), src)
        self.assertEqual(self.shared_now(), b0, "adoption edited the shared (tracked) ledger")
        for lock in _all_locks():
            post = SA.score(lock)
            self.assertEqual((post["k"], post["n"], post["state"]), (pre[lock]["k"], pre[lock]["n"], pre[lock]["state"]),
                             "%s: after adoption this PC does not read what it read before the split" % lock)
        again = SA.adopt_legacy_live("this Mac measured them", confirm=True)
        self.assertEqual(again["wrote"], 0, "a second adoption copied the same trials again")
        self.assertEqual(len(self.lines(pa)), len(self.legacy))
        led = SA.report().get("ledger") or {}
        self.assertEqual(led.get("legacyAdoptedHere"), len(self.legacy))
        self.assertIn("adopted all", led.get("legacyLiveSay") or "")

    def test_the_command_line_door(self):
        pa = self.pc("pcA")

        def run(*argv):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = SA.main(list(argv))
            return rc, buf.getvalue()
        rc, out = run("--adopt-legacy-live", "--confirm")
        self.assertEqual(rc, 2, out)
        self.assertIn("REFUSED", out)
        self.assertFalse(os.path.exists(pa))
        rc, out = run("--adopt-legacy-live", "--reason", "measured on this Mac")
        self.assertEqual(rc, 0, out)
        self.assertIn("DRY RUN", out)
        self.assertFalse(os.path.exists(pa))
        rc, out = run("--adopt-legacy-live", "--reason", "measured on this Mac", "--confirm")
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.lines(pa)), len(self.legacy))

    def test_the_door_names_the_whole_path_and_the_checkout(self):
        """REG-2473 - a basename reads as success from the wrong checkout; the whole path and the checkout cannot."""
        pa = self.pc("pcA")
        checkout = os.path.dirname(SA.HERE)
        for confirm in (False, True):
            res = SA.adopt_legacy_live("measured on this Mac", confirm=confirm)
            self.assertTrue(res["ok"], res["say"])
            self.assertEqual(res.get("dest"), pa)
            self.assertIn(pa, res["say"], "the door did not name the whole path it wrote")
            self.assertIn(checkout, res["say"], "the door did not name the checkout it ran from")

    def test_the_report_alone_adopts_nothing(self):
        pa = self.pc("pcA")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(SA.main([]), 0)
        self.assertFalse(os.path.exists(pa), "printing the report wrote this PC's ledger")


class TheseAttacksMeetTheBar(unittest.TestCase):
    def test_wilson_of_these_attacks_meets_the_bar(self):
        import confidence
        self.assertGreaterEqual(len(RED_PROOF), 10)
        self.assertGreaterEqual(confidence.wilson_lower(len(RED_PROOF), len(RED_PROOF)), 0.722)


RED_PROOF = [
    {"why": "#181 - the shared ledger's legacy live rows are counted again, so Dean's heart reads the Mac's trials",
     "file": "self_arming.py",
     "find": "        if _is_per_pc(r):  # PER-PC-LEGACY\n", "replace": "        if False:  # PER-PC-LEGACY\n",
     "matches": 1},
    {"why": "#181 - bank()/record() send a live trial to the shared (tracked) ledger, which ships it to every PC",
     "file": "self_arming.py",
     "find": "    if _is_per_pc(row):  # PER-PC-ROUTE\n", "replace": "    if False:  # PER-PC-ROUTE\n",
     "matches": 2},
    {"why": "#181 - the deferred fold sends a live row to the shared ledger",
     "file": "self_arming.py",
     "find": "        (here if _line_is_per_pc(ln) else shared).append(ln)  # PER-PC-FOLD\n",
     "replace": "        shared.append(ln)  # PER-PC-FOLD\n", "matches": 1},
    {"why": "#181 - the per-PC ledger's ignore line is gone: one `git add -A` ships one PC's trials to every PC",
     "file": ".gitignore",
     "find": "/.self_arming.here.jsonl\n", "replace": "", "matches": 1},
    {"why": "REG-2471 - adoption writes without --confirm",
     "file": "self_arming.py",
     "find": "    if not confirm:  # ADOPT-DRY\n", "replace": "    if False:  # ADOPT-DRY\n", "matches": 1},
    {"why": "REG-2471 - adoption with no reason is not refused",
     "file": "self_arming.py",
     "find": "    if not why:  # ADOPT-REASON\n", "replace": "    if False:  # ADOPT-REASON\n", "matches": 1},
    {"why": "REG-2471 - an adopted trial takes the copy's age instead of the measurement's",
     "file": "self_arming.py",
     "find": "    rows = [dict(r, adopted=dict(stamp)) for r in todo]  # ADOPT-KEEPS-TS\n",
     "replace": "    rows = [dict(r, adopted=dict(stamp), ts=stamp[\"at\"]) for r in todo]  # ADOPT-KEEPS-TS\n",
     "matches": 1},
    {"why": "REG-2471 - a second adoption copies the same trials again",
     "file": "self_arming.py",
     "find": "    todo = [r for r in sp[\"legacy\"] if _identity(r) not in have]  # ADOPT-ONCE\n",
     "replace": "    todo = list(sp[\"legacy\"])  # ADOPT-ONCE\n", "matches": 1},
    {"why": "#181 - a code row in one PC's ledger is read as evidence instead of failing the read closed",
     "file": "self_arming.py",
     "find": "        if not _is_per_pc(r):  # PER-PC-ONLY\n", "replace": "        if False:  # PER-PC-ONLY\n",
     "matches": 1},
    {"why": "#181 - a fixture that redirected the shared queue reads and writes his real per-PC ledger",
     "file": "self_arming.py",
     "find": "    if os.path.abspath(shared) != os.path.abspath(os.path.join(HERE, \".self_arming.jsonl\")):  # PER-PC-FOLLOWS\n",
     "replace": "    if False:  # PER-PC-FOLLOWS\n", "matches": 1},
    {"why": "#181 - score() hides that a figure was measured on this PC (byOrigin.here stays None)",
     "file": "self_arming.py",
     "find": "    if here:  # PER-PC-ORIGIN\n", "replace": "    if False:  # PER-PC-ORIGIN\n", "matches": 1},
    {"why": "#181 - score() stops saying how many legacy live rows it left out",
     "file": "self_arming.py",
     "find": "        legacy = sp[\"legacy\"]  # LEGACY-COUNT\n", "replace": "        legacy = []  # LEGACY-COUNT\n",
     "matches": 1},
    {"why": "#181 - the deferred fold's split is not recorded, so the runner's line names the wrong file",
     "file": "self_arming.py",
     "find": "    LAST_FOLD.update(shared=len(shared), here=len(here))  # FOLD-SAID\n",
     "replace": "    LAST_FOLD.update(shared=len(good), here=0)  # FOLD-SAID\n", "matches": 1},
    {"why": "REG-2473 - the per-PC ledger is one per CHECKOUT again: a live bank from a worktree never reaches his "
            "console, and `git worktree remove` deletes it",
     "file": "self_arming.py",
     "find": "    if common:  # PER-MACHINE\n", "replace": "    if False:  # PER-MACHINE\n", "matches": 1},
    {"why": "REG-2473 - a fixture's patched HERE_LEDGER is resolved past, so its live rows land in the machine's ledger",
     "file": "self_arming.py",
     "find": "    if os.path.abspath(HERE_LEDGER) != os.path.abspath(_HERE_LEDGER_DEFAULT):  # PER-PC-PATCHED\n",
     "replace": "    if False:  # PER-PC-PATCHED\n", "matches": 1},
    {"why": "REG-2473 - the adoption door names only the file's basename, so the wrong checkout reads as success",
     "file": "self_arming.py",
     "find": "    where = \"%s (%s; run from the checkout at %s)\" % (dest, here_label(), os.path.dirname(HERE))"
             "  # ADOPT-WHERE\n",
     "replace": "    where = os.path.basename(dest)  # ADOPT-WHERE\n", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=1)
