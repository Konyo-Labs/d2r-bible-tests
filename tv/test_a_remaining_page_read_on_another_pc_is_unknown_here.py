# -*- coding: utf-8 -*-
"""#165 (REG-2472) - A REMAINING PAGE READ ON ANOTHER PC IS UNKNOWN HERE, NOT EVIDENCE ABOUT THIS BOARD.

counter_ledger read every page in tv/remaining/ - a TRACKED dir that ships to every PC - with no provenance, and its
judges (contradicted, arithmetic, denied, owned_by_subtraction, audit) fed the chronicle calibration and the write-path
veto, where `denied` WITHHOLDS set rows. The one page there is Konyo's 2026-08-21 Remaining filter, read by eye off a
reel only his Mac ever held. Dean's eagle, 02:44: "Your board has 130 set pieces ticked. The last Remaining page (62 days
old) still listed 19 as missing..." - his board judged by another player's page.

THE RULE, decided at read time. A shipped page counts for THIS PC's judgement only when one of this PC's stores names
its reel: the reel dir under this PC's footage root (TV_HIST or tv/frames/hist), this PC's sweep memory (TV_CHRON_SWEPT),
or its reel tombstones - read through their OWNER, reel_retention (path and read), as a declared reader in store_owners.
Every store is resolved at call time. A store that cannot be read, with no positive answer, is UNKNOWN - never "another
PC's", never "this PC's"; a page with no reel cannot be attributed. A TV_REMAINING_DIR world is that world's own. A page
in THIS PC's own dir (TV_REMAINING_HERE; by default in git's common dir, one per PC) needs no provenance. Every judge
says WHY it has no page. The base -> piece mapping (sets_base_index, bible.html's _SET_BASE_INDEX) is GAME DATA and still
reads the shipped page on every PC, through counter_ledger.reference() - never the per-PC loader.

THE REVIEW OF THE FIRST CUT (REG-2473/2474). On the Mac only the sweep memory names its own page's reel, and
chronicle_forget_swept() ("re-read everything") writes {} there - after which the PC that filmed the page read it as
"read off a reel this PC never held": an emptied store taken as proof of absence. Now:
  * "no store names it" is said as exactly that, with both things it can mean, and never as "never held";
  * a page this PC filmed is KEPT through a door - `counter_ledger.py --adopt-page NAME --reason ... --confirm` - which
    REFUSES unless a store names the reel right now (a reason alone never makes another install's page judge a board),
    dry-runs without --confirm, writes once, never overwrites, never touches the shipped file, and names the whole
    path and the checkout; a kept page survives the clear and keeps its veto;
  * whose() re-judges a SAVED reading (the sweep's saved calibration) at read time;
  * the per-PC dir is one per PC (git's common dir), shared by a main checkout and its linked worktree.

Never his live stores: footage root, sweep memory, tombstones and the per-PC dir all live in this law's own scratch.
The reel is DERIVED from the tracked page, never pinned. RED_PROOF below.
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

import counter_ledger as CL  # noqa: E402
import sets_base_index as SBI  # noqa: E402
import chronicle_resolve as _res  # noqa: E402
import reel_retention as _rr  # noqa: E402
import store_owners as SO  # noqa: E402

GIT = shutil.which("git")
#: the seams this law sets, held and restored per case
_ENV = ("TV_HIST", "TV_CHRON_SWEPT", "TV_REMAINING_DIR", "TV_REMAINING_HERE")
#: the shipped page this law is about - named so a change to it re-proves the law (heart2 keys PROOF_NEEDS)
PROOF_NEEDS = ["remaining/sets_2026-08-21.json"]


def _write(p, blob):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as fh:
        if isinstance(blob, str):
            fh.write(blob)
        else:
            json.dump(blob, fh)


class _Pcs(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="remaining-pc-")
        self.addCleanup(shutil.rmtree, self.d, True)
        held = {k: os.environ.pop(k, None) for k in _ENV}

        def _restore():
            for k in _ENV:
                os.environ.pop(k, None)
            for k, v in held.items():
                if v is not None:
                    os.environ[k] = v
        self.addCleanup(_restore)
        self.hist = os.path.join(self.d, "hist")
        os.makedirs(self.hist)
        os.environ["TV_HIST"] = self.hist
        self.swept = os.path.join(self.d, "chronicle_swept.json")
        os.environ["TV_CHRON_SWEPT"] = self.swept
        self.here_dir = os.path.join(self.d, "remaining_here")
        os.environ["TV_REMAINING_HERE"] = self.here_dir
        self.page = CL.reference("sets")
        self.assertIsNotNone(self.page, "PREMISE: tv/remaining ships no page, so nothing here is about it")
        self.reel = self.page.get("reel")
        self.assertTrue(self.reel, "PREMISE: the shipped page names no reel")

    def tombstones(self):
        return _rr._tombstone_path()

    def shipped_bytes(self):
        with io.open(os.path.join(CL._dir(), self.page["source"]), "rb") as fh:
            return fh.read()

    def kept(self):
        """The copy this PC keeps of the shipped page, if any. -> path | None"""
        p = os.path.join(self.here_dir, self.page["source"])
        return p if os.path.exists(p) else None

    def clear_sweep_memory(self):
        """What control_app.chronicle_forget_swept() ("re-read everything") writes."""
        _write(self.swept, {})

    def pc_a(self):
        """THIS PC swept the page's reel - the Mac's shape: footage released, the sweep memory remembers it."""
        _write(self.swept, {self.reel: {"ts": 1, "classified": 1, "pages": 1}})

    def pc_b(self):
        """THIS PC never held the page's reel: its sweep memory names only its own."""
        _write(self.swept, {"reel_s_1500000000001_1": {"ts": 1, "classified": 1, "pages": 1}})

    def old_sighting(self):
        """A sighting older than the page, so a page this PC owns denies it."""
        ms = CL._reading_ms(self.page)
        self.assertIsNotNone(ms, "PREMISE: the shipped page carries no usable time")
        return [{"frame": "f_%d.jpg" % (ms - 60000)}]


class APcThatHeldTheReelJudgesWithItsPage(_Pcs):
    def test_its_own_sweep_memory_makes_the_page_its_own(self):
        self.pc_a()
        r = CL.load("sets")
        self.assertIsNotNone(r, CL.provenance("sets")["why"])
        self.assertEqual(r["reel"], self.reel)
        name = self.page["names"][0]
        c = CL.contradicted([name])
        self.assertIs(c["ok"], False)
        self.assertEqual([h["name"] for h in c["contradicted"]], [CL._folder()(name)])
        roster = len(_res.load_set_roster() or {})
        self.assertIs(CL.arithmetic(roster - self.page["count"], roster)["ok"], True)
        dn = CL.denied({name: self.old_sighting()})
        self.assertEqual([x["name"] for x in dn["denied"]], [CL._folder()(name)],
                         "the page this PC owns no longer vetoes a row it denies")

    def test_its_footage_tree_makes_the_page_its_own(self):
        self.pc_b()
        os.makedirs(os.path.join(self.hist, self.reel))
        self.assertIsNotNone(CL.load("sets"), CL.provenance("sets")["why"])

    def test_its_tombstones_make_the_page_its_own(self):
        self.pc_b()
        _write(self.tombstones(), {"reels": [{"reel": self.reel, "session": self.reel[len("reel_"):]}]})
        self.assertIsNotNone(CL.load("sets"), CL.provenance("sets")["why"])

    def test_a_positive_answer_beats_an_unreadable_store(self):
        _write(self.swept, "{ not json")
        os.makedirs(os.path.join(self.hist, self.reel))
        self.assertIsNotNone(CL.load("sets"), CL.provenance("sets")["why"])


class APcThatNeverHeldTheReelHasNoPage(_Pcs):
    def test_load_is_none_and_every_judge_says_why(self):
        self.pc_b()
        self.assertIsNone(CL.load("sets"), "PC-B was handed another install's Remaining page")
        pv = CL.provenance("sets")
        self.assertEqual(pv["state"], "elsewhere", pv["why"])
        name = self.page["names"][0]
        c = CL.contradicted([name])
        self.assertIsNone(c["ok"])
        self.assertIsNone(c["reading"])
        a = CL.arithmetic(130, 135)
        self.assertIsNone(a["ok"])
        owned, meta = CL.owned_by_subtraction(_res.load_set_roster() or {})
        self.assertIsNone(owned)
        for say in (c["say"], a["say"], meta["why"], CL.audit({})["say"]):
            self.assertIn("none of this PC's stores name", say, "a judge with no page for this PC did not say why: %r"
                          % say)
            self.assertIn("UNKNOWN here", say)
            self.assertNotIn("never held", say, "a judge claimed more than it measured: %r" % say)

    def test_the_veto_withholds_nothing(self):
        self.pc_b()
        dn = CL.denied({self.page["names"][0]: self.old_sighting()})
        self.assertIsNone(dn["ok"])
        self.assertEqual(dn["denied"], [], "another install's page withheld a row from this PC's board")
        self.assertIn("none of this PC's stores name", dn["say"])

    def test_an_absent_store_everywhere_is_still_another_installs_page(self):
        """A fresh PC: no footage, no sweep memory, no tombstones. Absent is an honest empty, not UNKNOWN."""
        self.assertIsNone(CL.load("sets"))
        self.assertEqual(CL.provenance("sets")["state"], "elsewhere")


class AStoreThatWillNotReadIsUnknown(_Pcs):
    def test_an_unreadable_sweep_memory_is_unknown_not_another_pcs(self):
        _write(self.swept, "{ not json")
        self.assertIsNone(CL.load("sets"))
        pv = CL.provenance("sets")
        self.assertEqual(pv["state"], "unknown", pv["why"])
        self.assertIn("UNKNOWN", pv["why"])
        self.assertNotIn("none of this PC's stores name", pv["why"], "an unreadable store was read as 'no store names it'")
        self.assertNotIn("never held", pv["why"], "an unreadable store was read as 'this PC never held it'")
        self.assertIn("UNKNOWN", CL.contradicted([self.page["names"][0]])["say"])

    def test_an_unreadable_tombstone_ledger_is_unknown(self):
        self.pc_b()
        _write(self.tombstones(), "[[[")
        self.assertEqual(CL.provenance("sets")["state"], "unknown")

    def test_a_page_with_no_reel_cannot_be_attributed(self):
        for reel in (None, "", "   ", "../" + str(self.reel)):
            held, why = CL._held_here(reel)
            self.assertIsNone(held, "a page with reel %r was attributed: %s" % (reel, why))


class OtherWorldsAndThisPcsOwnPages(_Pcs):
    def test_a_page_filmed_here_needs_no_provenance(self):
        self.pc_b()
        later = {"ledger": "sets", "reel": "reel_s_1500000000007_7", "readAt": "2099-01-01T00:00:00Z",
                 "rows": [{"piece": self.page["names"][0]}]}
        _write(os.path.join(self.here_dir, "sets_here.json"), later)
        r = CL.load("sets")
        self.assertIsNotNone(r, "a page this PC filmed itself was not used")
        self.assertEqual(r["reel"], later["reel"])

    def test_a_fixture_world_is_its_own(self):
        world = os.path.join(self.d, "world")
        _write(os.path.join(world, "sets_w.json"),
               {"ledger": "sets", "reel": "reel_s_1500000000008_8", "readAt": "2026-08-21T10:19:13.811000Z",
                "rows": [{"piece": self.page["names"][0]}]})
        os.environ["TV_REMAINING_DIR"] = world
        self.pc_b()
        r = CL.load("sets")
        self.assertIsNotNone(r, "a TV_REMAINING_DIR world's own page was provenance-checked")
        self.assertEqual(r["reel"], "reel_s_1500000000008_8")

    def test_the_base_index_is_game_data_and_identical_on_both_pcs(self):
        self.pc_a()
        a = SBI.build()
        self.pc_b()
        b = SBI.build()
        self.assertIsNotNone(a)
        self.assertIsNotNone(b, "sets_base_index lost the base -> piece mapping on a PC that never held the reel")
        self.assertEqual(a, b)
        self.assertEqual(b["reel"], self.reel)


class AClearedSweepMemoryIsNotProofOfAbsence(_Pcs):
    """REG-2474 - the Mac's own shape: footage released, no tombstone, ONLY the sweep memory names the page's reel -
    and "re-read everything" (control_app.chronicle_forget_swept) empties it."""

    def test_the_sentence_says_what_was_measured_not_never_held(self):
        self.pc_a()
        name = self.page["names"][0]
        self.assertEqual([x["name"] for x in CL.denied({name: self.old_sighting()})["denied"]], [CL._folder()(name)],
                         "PREMISE: the page this PC's sweep memory names does not veto")
        self.clear_sweep_memory()
        pv = CL.provenance("sets")
        self.assertEqual(pv["state"], "elsewhere", pv["why"])
        self.assertIn("none of this PC's stores name", pv["why"])
        self.assertIn("no longer remembers", pv["why"],
                      "the sentence hides that a cleared store reads exactly like another install's page")
        self.assertNotIn("never held", pv["why"], "an emptied store was read as proof this PC never held the reel")
        self.assertIsNone(CL.load("sets"))

    def test_a_page_kept_through_the_door_survives_the_clear_and_keeps_its_veto(self):
        self.pc_a()
        name = self.page["names"][0]
        res = CL.adopt_page(self.page["source"], "this PC filmed it", confirm=True)
        self.assertTrue(res["ok"], res["say"])
        self.assertEqual(res["wrote"], 1)
        self.assertEqual(len(CL.readings("sets")), 1, "the kept copy and the shipped page it copies are both listed")
        self.clear_sweep_memory()
        r = CL.load("sets")
        self.assertIsNotNone(r, "a cleared sweep memory unmade the page this PC kept: %s" % CL.provenance("sets")["why"])
        self.assertEqual((r["reel"], r["readAt"], r["shelf"]), (self.reel, self.page["readAt"], "per-pc"))
        self.assertEqual(CL.provenance("sets")["state"], "here")
        dn = CL.denied({name: self.old_sighting()})
        self.assertEqual([x["name"] for x in dn["denied"]], [CL._folder()(name)], "the kept page lost its veto")


class TheKeepDoor(_Pcs):
    """REG-2474 - `python3 tv/counter_ledger.py --adopt-page NAME --reason WHY --confirm`."""

    def test_no_reason_is_refused_and_writes_nothing(self):
        self.pc_a()
        for reason in (None, "", "   ", "--confirm"):
            res = CL.adopt_page(self.page["source"], reason, confirm=True)
            self.assertFalse(res["ok"], reason)
            self.assertTrue(res["refused"], reason)
            self.assertIn("REFUSED", res["say"])
        self.assertIsNone(self.kept(), "a refused door wrote this PC's dir")

    def test_a_dry_run_writes_nothing_and_says_which_store_vouched(self):
        self.pc_a()
        b0 = self.shipped_bytes()
        res = CL.adopt_page(self.page["source"], "this PC filmed it", confirm=False)
        self.assertTrue(res["ok"], res["say"])
        self.assertTrue(res["dryRun"])
        self.assertEqual(res["wrote"], 0)
        self.assertIn("DRY RUN", res["say"])
        self.assertIn("sweep memory", res["say"], "the dry run does not say which store vouched")
        self.assertIsNone(self.kept(), "a dry run wrote this PC's dir")
        self.assertEqual(self.shipped_bytes(), b0)

    def test_it_refuses_a_page_no_store_of_this_pc_names(self):
        """A reason is a person's word; the door only pins what this PC's stores already show."""
        self.pc_b()
        res = CL.adopt_page(self.page["source"], "this PC filmed it", confirm=True)
        self.assertFalse(res["ok"], res["say"])
        self.assertIn("REFUSED", res["say"])
        self.assertIn("none of this PC's stores name", res["say"])
        self.assertNotIn("never held", res["say"], "the refusal claimed more than it measured")
        self.assertIsNone(self.kept(), "another install's page was kept as this PC's own")
        _write(self.swept, "{ not json")
        res = CL.adopt_page(self.page["source"], "this PC filmed it", confirm=True)
        self.assertFalse(res["ok"], "an UNKNOWN store vouched for a page: %s" % res["say"])
        self.assertIsNone(self.kept())

    def test_it_refuses_a_name_that_is_not_a_shipped_page(self):
        self.pc_a()
        for nm in ("", "nope.json", "../" + self.page["source"], os.path.join("x", self.page["source"])):
            res = CL.adopt_page(nm, "this PC filmed it", confirm=True)
            self.assertFalse(res["ok"], nm)
            self.assertIn("REFUSED", res["say"])
        self.assertIsNone(self.kept())

    def test_confirm_writes_one_marked_copy_once(self):
        self.pc_a()
        b0 = self.shipped_bytes()
        res = CL.adopt_page(self.page["source"], "this PC filmed it", confirm=True)
        self.assertTrue(res["ok"], res["say"])
        with io.open(self.kept(), encoding="utf-8") as fh:
            got = json.load(fh)
        ad = got.pop("adopted")
        self.assertEqual((ad["by"], ad["reason"]), ("--adopt-page", "this PC filmed it"))
        self.assertIn("sweep memory", ad["vouchedBy"])
        self.assertEqual(got, json.loads(b0.decode("utf-8")), "the kept copy is not the shipped page")
        self.assertEqual(self.shipped_bytes(), b0, "the door touched the shipped file")
        again = CL.adopt_page(self.page["source"], "this PC filmed it", confirm=True)
        self.assertTrue(again["ok"], again["say"])
        self.assertEqual(again["wrote"], 0, "a second keep wrote the page again")
        self.assertIn("already kept", again["say"])

    def test_a_different_file_of_that_name_is_never_overwritten(self):
        self.pc_a()
        other = {"ledger": "sets", "reel": "reel_s_1500000000009_9", "readAt": "2099-01-01T00:00:00Z",
                 "rows": [{"piece": self.page["names"][0]}]}
        _write(os.path.join(self.here_dir, self.page["source"]), other)
        res = CL.adopt_page(self.page["source"], "this PC filmed it", confirm=True)
        self.assertFalse(res["ok"], res["say"])
        with io.open(os.path.join(self.here_dir, self.page["source"]), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), other, "the door overwrote a page this PC already kept")

    def test_the_command_line_door_names_the_whole_path_and_the_checkout(self):
        self.pc_a()

        def run(*argv):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = CL.main(list(argv))
            return rc, buf.getvalue()
        rc, out = run("--adopt-page", self.page["source"], "--confirm")
        self.assertEqual(rc, 2, out)
        self.assertIn("REFUSED", out)
        rc, out = run("--adopt-page", self.page["source"], "--reason", "this PC filmed it")
        self.assertEqual(rc, 0, out)
        self.assertIn("DRY RUN", out)
        self.assertIsNone(self.kept())
        rc, out = run("--adopt-page", self.page["source"], "--reason", "this PC filmed it", "--confirm")
        self.assertEqual(rc, 0, out)
        self.assertIn(os.path.join(self.here_dir, self.page["source"]), out, "the door did not name the whole path")
        self.assertIn(CL.REPO, out, "the door did not name the checkout whose stores it asked")
        self.assertIsNotNone(self.kept())


class ASavedReadingIsJudgedAtReadTime(_Pcs):
    """REG-2474 - whose(): a sweep's SAVED calibration carries the page's reel, and its reader asks at READ time."""

    def saved(self):
        return {"readAt": self.page["readAt"], "reel": self.reel, "ageDays": 62.0, "source": self.page["source"]}

    def test_another_installs_saved_reading_is_unknown_here(self):
        self.pc_b()
        w = CL.whose(self.saved())
        self.assertIs(w["held"], False, w["why"])
        self.assertIn("UNKNOWN here", w["why"])
        self.assertIn("none of this PC's stores name", w["why"])
        self.assertNotIn("never held", w["why"])

    def test_this_pcs_saved_reading_is_its_own(self):
        self.pc_a()
        self.assertIs(CL.whose(self.saved())["held"], True)

    def test_an_unreadable_store_makes_a_saved_reading_unknown(self):
        _write(self.swept, "{ not json")
        w = CL.whose(self.saved())
        self.assertIsNone(w["held"], w["why"])
        self.assertIn("UNKNOWN", w["why"])

    def test_a_kept_page_answers_for_its_saved_reading_after_the_clear(self):
        self.pc_a()
        self.assertTrue(CL.adopt_page(self.page["source"], "this PC filmed it", confirm=True)["ok"])
        self.clear_sweep_memory()
        w = CL.whose(self.saved())
        self.assertIs(w["held"], True, w["why"])
        self.assertIn("per-PC dir", w["why"])


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


class ThePerPcDirIsOnePerPc(unittest.TestCase):
    """REG-2473 - a main checkout and its linked worktree keep ONE per-PC dir, in git's common dir."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="remaining-machine-")
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

    def test_a_worktree_and_its_main_checkout_share_one_dir(self):
        main, wt = _worktree_shape(self.d)
        dm, sm, _ = CL._here_where(repo=main)
        dw, sw, _ = CL._here_where(repo=wt)
        self.assertEqual((sm, sw), ("machine", "machine"))
        self.assertEqual(self._real(dm), self._real(dw), "a page kept from a worktree is not where his console reads")
        self.assertTrue(self._real(dw).startswith(self._real(os.path.join(main, ".git")) + os.sep), dw)
        for tree in (main, wt):
            self.assertFalse(self._real(dw).startswith(self._real(os.path.join(tree, "tv")) + os.sep),
                             "the per-PC dir sits in a work tree, so `git worktree remove` deletes it")

    def test_a_tree_with_no_git_dir_keeps_its_own_and_says_why(self):
        plain = os.path.join(self.d, "plain")
        os.makedirs(os.path.join(plain, "tv"))
        d, scope, why = CL._here_where(repo=plain)
        self.assertEqual(scope, "checkout")
        self.assertEqual(self._real(d), self._real(os.path.join(plain, "tv", "remaining_here")))
        self.assertTrue(why, "a dir that dies with its checkout does not say why")


class TheTombstonesAreReadThroughTheirOwner(_Pcs):
    """REG-2473 - the review's blocker: counter_ledger read the tombstones with its own json.load and nothing declared
    it, so test_store_owners went red - on CI, after the push had published (store_owners finds its modules by listing
    tv/, which no law key can name, so a push re-proving this module never re-ran it). It reads through reel_retention
    now, as a declared reader - and THIS law, which every change to counter_ledger re-proves, checks the declaration."""

    def test_counter_ledger_is_a_declared_reader_with_a_reason(self):
        spec = SO.STORES["reel_tombstones.json"]
        self.assertEqual(spec["owner"], "reel_retention")
        self.assertIn("counter_ledger", spec["readers"], "counter_ledger reads the tombstones and nothing declares it")
        self.assertGreater(len(spec["readers"]["counter_ledger"].strip()), 15)

    def test_the_owner_reads_them(self):
        self.pc_b()
        seen = []
        real = _rr._load_state

        def spy(path):
            seen.append(os.path.abspath(path))
            return real(path)
        _rr._load_state = spy
        self.addCleanup(setattr, _rr, "_load_state", real)
        _write(self.tombstones(), {"reels": [{"reel": self.reel}]})
        held, why = CL._held_here(self.reel)
        self.assertIs(held, True, why)
        self.assertIn(os.path.abspath(self.tombstones()), seen,
                      "counter_ledger read the tombstones with its own json.load, not through their owner")


@unittest.skipIf(GIT is None, "git is absent - this case is UNMEASURED, not passing")
class GitIgnoresThePerPcPages(unittest.TestCase):
    def test_the_per_pc_dir_is_ignored_and_the_shipped_one_is_not(self):
        # a linked-worktree push exports GIT_DIR into the hook; this case's throwaway repo must never see it
        _gitenv = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("GIT_")}
        self.addCleanup(os.environ.update, _gitenv)
        env = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))
        d = tempfile.mkdtemp(prefix="remaining-ignore-")
        self.addCleanup(shutil.rmtree, d, True)
        subprocess.run([GIT, "init", "-q", d], check=True, env=env)
        subprocess.run([GIT, "-C", d, "config", "core.autocrlf", "false"], check=True, env=env)  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        os.makedirs(os.path.join(d, "tv"))
        for rel in (".gitignore", os.path.join("tv", ".gitignore")):
            if os.path.isfile(os.path.join(ROOT, rel)):
                shutil.copyfile(os.path.join(ROOT, rel), os.path.join(d, rel))

        def ignored(rel):
            return subprocess.run([GIT, "check-ignore", "-q", "--no-index", rel], cwd=d, env=env).returncode == 0
        self.assertTrue(ignored("tv/remaining_here/sets_2026-10-22.json"),
                        "a page one PC filmed is one `git add -A` away from judging every PC's board")
        self.assertFalse(ignored("tv/remaining/sets_2026-10-22.json"), "the SHIPPED pages must stay trackable")


class TheseAttacksMeetTheBar(unittest.TestCase):
    def test_wilson_of_these_attacks_meets_the_bar(self):
        import confidence
        self.assertGreaterEqual(len(RED_PROOF), 10)
        self.assertGreaterEqual(confidence.wilson_lower(len(RED_PROOF), len(RED_PROOF)), 0.722)


RED_PROOF = [
    {"why": "#165 - provenance bypassed: a PC that never held the reel is judged by another install's page",
     "file": "counter_ledger.py",
     "find": "            held, why = _held_here(p.get(\"reel\"))  # PROVENANCE\n",
     "replace": "            held, why = True, \"bypassed\"  # PROVENANCE\n", "matches": 1},
    {"why": "#165 - an unreadable store is read as 'this PC never held it' instead of UNKNOWN",
     "file": "counter_ledger.py",
     "find": "    if unread:  # UNREAD-IS-UNKNOWN\n", "replace": "    if False:  # UNREAD-IS-UNKNOWN\n", "matches": 1},
    {"why": "#165 - sets_base_index switched to the per-PC loader: the base index vanishes on a PC without the reel",
     "file": "sets_base_index.py",
     "find": "    r = _cl.reference(ledger)  # REFERENCE-PAGE\n", "replace": "    r = _cl.load(ledger)  # REFERENCE-PAGE\n",
     "matches": 1},
    {"why": "#165 - the per-PC page dir's ignore line is gone: one PC's page ships to every PC again",
     "file": ".gitignore",
     "find": "/remaining_here/\n", "replace": "", "matches": 1},
    {"why": "#165 - a page with no reel is attributed to this PC",
     "file": "counter_ledger.py",
     "find": "    if not ids:  # NO-REEL\n        return None,", "replace": "    if not ids:  # NO-REEL\n        return True,",
     "matches": 1},
    {"why": "#165 - this PC's footage tree is no longer asked",
     "file": "counter_ledger.py",
     "find": "        if got is True:  # FOOTAGE-ARM\n", "replace": "        if False:  # FOOTAGE-ARM\n", "matches": 1},
    {"why": "#165 - this PC's sweep memory is no longer asked",
     "file": "counter_ledger.py",
     "find": "        if any(i in blob for i in ids):  # SWEPT-ARM\n", "replace": "        if False:  # SWEPT-ARM\n",
     "matches": 1},
    {"why": "#165 - this PC's reel tombstones are no longer asked",
     "file": "counter_ledger.py",
     "find": "    elif any(_names_of(x) & set(ids) for x in rows):  # TOMBSTONE-ARM\n",
     "replace": "    elif False:  # TOMBSTONE-ARM\n", "matches": 1},
    {"why": "#165 - a TV_REMAINING_DIR world is provenance-checked against stores it does not own",
     "file": "counter_ledger.py",
     "find": "    if os.environ.get(\"TV_REMAINING_DIR\"):  # WORLD-OWN\n", "replace": "    if False:  # WORLD-OWN\n",
     "matches": 1},
    {"why": "#165 - a page this PC filmed itself is not used",
     "file": "counter_ledger.py",
     "find": "            p[\"origin\"], p[\"shelf\"] = \"here\", \"per-pc\"  # PER-PC-DIR\n",
     "replace": "            p[\"origin\"], p[\"shelf\"] = \"elsewhere\", \"per-pc\"  # PER-PC-DIR\n",
     "matches": 1},
    {"why": "#165 - a judge with no page for this PC no longer says why",
     "file": "counter_ledger.py",
     "find": "    if pv[\"state\"] in (\"elsewhere\", \"unknown\"):  # SAY-WHY\n", "replace": "    if False:  # SAY-WHY\n",
     "matches": 1},
    {"why": "#165 - every judge reads the shipped page whoever filmed it (the leak, at its widest)",
     "file": "counter_ledger.py",
     "find": "    r = reading or load(ledger)\n", "replace": "    r = reading or reference(ledger)\n", "matches": 5},
    {"why": "REG-2474 - an emptied store is said as proof of absence again: 'this PC never held' it",
     "file": "counter_ledger.py",
     "find": "        return {\"state\": \"elsewhere\", \"pages\": brief, \"why\": _say_elsewhere(len(far))}  # SAY-MEASURED\n",
     "replace": "        return {\"state\": \"elsewhere\", \"pages\": brief, \"why\": \"the only Remaining page on file was read off "
                "a reel this PC never held - UNKNOWN here, not evidence about this board\"}  # SAY-MEASURED\n",
     "matches": 1},
    {"why": "REG-2474 - 'no store names it' becomes 'this PC never held it' at its source",
     "file": "counter_ledger.py",
     "find": "    return False, \"none of this PC's stores name its reel (%s)\" % _STORES_ASKED  # NONE-NAME-IT\n",
     "replace": "    return False, \"this PC never held its reel\"  # NONE-NAME-IT\n", "matches": 1},
    {"why": "REG-2474 - the keep door takes a person's word alone: another install's page is kept as this PC's own",
     "file": "counter_ledger.py",
     "find": "    held, vouch = _held_here(page.get(\"reel\"))  # PAGE-VOUCHED\n",
     "replace": "    held, vouch = True, \"a person said so\"  # PAGE-VOUCHED\n", "matches": 1},
    {"why": "REG-2474 - the keep door writes with no reason",
     "file": "counter_ledger.py",
     "find": "    if not why:  # PAGE-REASON\n", "replace": "    if False:  # PAGE-REASON\n", "matches": 1},
    {"why": "REG-2474 - the keep door writes without --confirm",
     "file": "counter_ledger.py",
     "find": "    if not confirm:  # PAGE-DRY\n", "replace": "    if False:  # PAGE-DRY\n", "matches": 1},
    {"why": "REG-2474 - a page already kept is refused as a stranger instead of recognised",
     "file": "counter_ledger.py",
     "find": "        if same:  # PAGE-ONCE\n", "replace": "        if False:  # PAGE-ONCE\n", "matches": 1},
    {"why": "REG-2474 - the keep door overwrites a page this PC already kept under that name",
     "file": "counter_ledger.py",
     "find": "    if os.path.exists(dest):  # PAGE-NEVER-OVERWRITE\n",
     "replace": "    if False:  # PAGE-NEVER-OVERWRITE\n", "matches": 1},
    {"why": "REG-2474 - a kept page and the shipped page it copies are both listed",
     "file": "counter_ledger.py",
     "find": "            if (p.get(\"reel\"), p.get(\"readAt\")) in kept:  # KEPT-ONCE\n",
     "replace": "            if False:  # KEPT-ONCE\n", "matches": 1},
    {"why": "REG-2474 - a SAVED reading is trusted whoever filmed it: Dean's doctor keeps printing Konyo's 19",
     "file": "counter_ledger.py",
     "find": "    held, why = _held_here(r.get(\"reel\"))  # SAVED-PROVENANCE\n",
     "replace": "    held, why = True, \"saved, so trusted\"  # SAVED-PROVENANCE\n", "matches": 1},
    {"why": "REG-2474 - a saved reading of a page this PC kept is judged by the clearable stores alone",
     "file": "counter_ledger.py",
     "find": "            if p.get(\"reel\") == r.get(\"reel\") and p.get(\"readAt\") == r.get(\"readAt\"):  # SAVED-KEPT\n",
     "replace": "            if False:  # SAVED-KEPT\n", "matches": 1},
    {"why": "REG-2473 - the per-PC dir is one per CHECKOUT again: a page kept from a worktree never reaches his console",
     "file": "counter_ledger.py",
     "find": "    if common:  # PER-MACHINE\n", "replace": "    if False:  # PER-MACHINE\n", "matches": 1},
    {"why": "REG-2473 - the tombstones are read with a second json.load instead of through their owner",
     "file": "counter_ledger.py",
     "find": "        blob, st = _rr._load_state(_rr._tombstone_path())  # OWNER-READS\n",
     "replace": "        blob, st = _read_store(_rr._tombstone_path())  # OWNER-READS\n", "matches": 1},
    {"why": "REG-2473 - the tombstone read is an undeclared coupling again (test_store_owners red on CI only)",
     "file": "store_owners.py",
     "find": "            \"counter_ledger\": \"READS it (_tombstone_rows) for ONE question: is the reel a shipped Remaining "
             "page\\n\"\n",
     "replace": "            \"counter_ledger_undeclared\": \"READS it (_tombstone_rows) for ONE question: is the reel a shipped "
                "Remaining page\\n\"\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=1)
