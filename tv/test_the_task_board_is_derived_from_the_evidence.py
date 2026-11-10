# -*- coding: utf-8 -*-
"""v3865 (REG-3217, REG-3218) - THE TASK BOARD IS DERIVED FROM THE EVIDENCE, LIKE BLUEPRINT AND HEART.

His words, 2026-11-05: "make sure its derived always console and you and the taskboard synced.. so we are always with our
finger on the trigger and know whats still being worked on and not shipped". MEASURED that evening: the board (the task
panel's cards, published by control_app.task_board_publish_once to /d2r/tasks.html) had not been touched for 6 hours while
the work moved - 25 cards said in_progress, several describing work shipped days earlier ("v3862 ship", REG-3155's proof
bank, REG-3157's ship_when_green), none naming the fleet that was running. Nothing compared a card with the tree.

REG-3217 - every card carries a DERIVED phase (tv/task_truth.py): its keys (REG ids, ranges expanded; a version LEADING the
subject; branch names) resolved against git - no-evidence | building | graded (ci/ only) | shipped vN | live vN (the
site serves >= N, read from the newest successful Publish run) | looked (GrokBot's VISUAL seat on #230, after the ship) |
third-eyed (a SECOND-EYE row on #231) - each with its evidence. A look is about the versions and REG ids on its first line
that names any, never its evidence list or a changelog recap; the newest look about a key decides, and one that says it
FAILS refutes it. A tree that would not answer is UNKNOWN, never no-evidence; an unread lane is UNKNOWN, never "not looked".
v3866 (the review of the first cut, measured on his real board: 13 "ready to close", 0 of them real) - a Grok CLI status
note, GrokBot's coder seat and a recap line are no looks; a card is flagged only by evidence newer than the hand last set
it (touching a card accepts a reviewed flag); "shipped and still in progress" is a flag of its own.
REG-3218 - a card whose hand status disagrees is FLAGGED with the reason (ready to close / closed but never shipped / work
started on a pending card / in progress with nothing built), published on the board, and counted by the eagle row "the
board agrees with the tree" (on/worked/lastTs/owed). Nothing rewrites a card.

Fixtures only: a temp git repo (every GIT_* variable scrubbed - a git hook leaks GIT_DIR into its children), fixture GitHub
comments through a stand-in reader, temp tasks dirs and temp state files. His ~/.claude/tasks, his tree and his stores are
never read. RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()        # its temp repos and stores are made under the run's own scratch base, removed with it
import task_truth as TT  # noqa: E402
import task_board as TB  # noqa: E402

DAY = 24 * 3600 * 1000
T0 = 1793900000000                       # "now" for every fixture
# the home path is built at run time: this file is public (test_no_new_home_path_is_published counts /Users/<name>/)
DIRTY = "see " + "/" + "Users/someone/d2r_bible_tests/tv/x.py on 192.0.2.7"


def _iso(ms):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ms / 1000.0))


def _genv(at_ms=None):
    env = dict((k, v) for k, v in os.environ.items() if not k.startswith("GIT_"))
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
    if at_ms is not None:
        stamp = "@%d +0000" % (at_ms // 1000)
        env.update(GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
    return env


def _g(repo, *args, **kw):
    p = subprocess.run(["git", "-c", "user.name=law", "-c", "user.email=law@example.com", "-c", "commit.gpgsign=false"]
                       + list(args), cwd=repo, capture_output=True, encoding="utf-8", errors="replace",
                       env=_genv(kw.get("at")), timeout=60)
    if p.returncode != 0:
        raise RuntimeError("fixture git %s: %s" % (args[0], p.stderr[-300:]))
    return p.stdout.strip()


def _commit(repo, msg, at, ship=None):
    with io.open(os.path.join(repo, "work.txt"), "a", encoding="utf-8") as fh:
        fh.write(msg + "\n")
    if ship:
        os.makedirs(os.path.join(repo, "tv"), exist_ok=True)
        with io.open(os.path.join(repo, "tv", "WINDOWS_SHIP.json"), "w", encoding="utf-8") as fh:
            json.dump({"ver": ship}, fh)
    _g(repo, "add", "-A")
    _g(repo, "commit", "-q", "-m", msg, at=at)
    return _g(repo, "rev-parse", "HEAD")


def _build_repo():
    """main: v3800 (REG-100) -> fix (REG-101, body names REG-108) -> v3801 stamp (REG-105..107) -> v3802 (REG-102, stamp file
    still v3801); ci/claude-v3803 (REG-103); claude/v3804 (REG-104, local only); origin's ci/remote-only (REG-109);
    claude/merged at the v3801 stamp. origin/main = the v3802 commit."""
    repo = tempfile.mkdtemp(prefix="task-truth-repo-")
    _g(repo, "init", "-q", "-b", "main")
    _g(repo, "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
    c1 = _commit(repo, "v3800: the first fix (REG-100)", T0 - 10 * DAY, ship="v3800")
    c2 = _commit(repo, "fix: the second fix (REG-101)\n\nand it closes REG-108 too", T0 - 9 * DAY)
    c3 = _commit(repo, "v3801 stamp: the changelog names three (REG-105..107)", T0 - 8 * DAY, ship="v3801")
    c4 = _commit(repo, "v3802: on main before the site moved (REG-102)", T0 - 3 * DAY)
    _g(repo, "update-ref", "refs/remotes/origin/main", c4)
    _g(repo, "branch", "claude/merged", c3)
    _g(repo, "checkout", "-q", "-b", "ci/claude-v3803", c4)
    _commit(repo, "v3803: graded only (REG-103)", T0 - 2 * DAY)
    _g(repo, "checkout", "-q", "-b", "claude/v3804", c4)
    _commit(repo, "v3804: building only (REG-104)", T0 - 1 * DAY)
    _g(repo, "checkout", "-q", "-b", "scratch-remote", c4)
    c7 = _commit(repo, "v3805: graded on a remote ci branch only (REG-109)", T0 - 1 * DAY)
    _g(repo, "update-ref", "refs/remotes/origin/ci/remote-only", c7)
    _g(repo, "checkout", "-q", "main")
    _g(repo, "branch", "-D", "scratch-remote")
    return repo, {"c1": c1, "c2": c2, "c3": c3, "c4": c4}


#: the two lanes, as GitHub would answer them
COMMENTS = {
    230: [
        {"id": 1001, "created_at": _iso(T0 - 11 * DAY), "updated_at": _iso(T0 - 11 * DAY),
         "body": "Seat: Grok Bot (visual eyes)\n\nREG-100 checked on his screen"},                  # before REG-100 shipped
        {"id": 1002, "created_at": _iso(T0 - 7 * DAY), "updated_at": _iso(T0 - 7 * DAY),
         "body": "Seat: Grok Bot (visual eyes)\n\n# v3801 ship check\n\nEvidence: changelog-v3800-01.json, shots/\n"
                 "- REG-100: the first fix (the changelog's recap, not what was looked at)"},
        {"id": 1003, "created_at": _iso(T0 - 7 * DAY), "updated_at": _iso(T0 - 7 * DAY),
         "body": "Seat: Claude (coder) -> GrokBot\n\nACT verify REG-100 and v3800 on glass"},          # not a look
        {"id": 1004, "created_at": _iso(T0 - 6 * DAY), "updated_at": _iso(T0 - 6 * DAY),
         "body": "Seat: Grok CLI (third eye)\n\nSAW: origin/main stamp v3801, the crops stay with Grok Bot"},  # a status note
        {"id": 1005, "created_at": _iso(T0 - 9 * DAY), "updated_at": _iso(T0 - 9 * DAY),
         "body": "SECOND-EYE\nversion: v3800\nverdict: clean"},              # a second-eye row posted on #230 - not its lane
        {"id": 1006, "created_at": _iso(T0 - 6 * DAY), "updated_at": _iso(T0 - 6 * DAY),
         "body": "Seat: Grok Bot (code)\n\n## Plan addendum: v3800 REG-100 read price"},           # the coder seat's plan
        {"id": 1007, "created_at": _iso(T0 - 5 * DAY), "updated_at": _iso(T0 - 5 * DAY),
         "body": "Seat: Grok Bot (visual eyes)\n\n# REG-106 recheck: FAIL - still broken on his screen"},
        # REG-3281 (#86) - a look that names the key: only this one, never 1002's version-level ship check, looks at REG-101
        {"id": 1008, "created_at": _iso(T0 - 6 * DAY), "updated_at": _iso(T0 - 6 * DAY),
         "body": "Seat: Grok Bot (visual eyes)\n\n# REG-101 recheck: SAW the lamp on his screen"},
    ],
    231: [
        {"id": 2001, "created_at": _iso(T0 - 6 * DAY), "updated_at": _iso(T0 - 6 * DAY),
         "body": "SECOND-EYE\nversion: v3801\nverdict: findings\nmodel: grok-4.7"},
        {"id": 2002, "created_at": _iso(T0 - 9 * DAY), "updated_at": _iso(T0 - 9 * DAY),
         "body": "Seat: Grok CLI (third eye)\n\nSAW: origin/main stamp v3800. This seat has not read the v3800 range."},
        {"id": 2003, "created_at": _iso(T0 - 9 * DAY), "updated_at": _iso(T0 - 9 * DAY),
         "body": "SECOND-EYE \u00b7 v3800 (c1) \u00b7 verdict **cannot-tell** \u00b7 model grok-cli"},   # recorded, NOT a look
    ],
}


class FakeGitHub(object):
    """the two lanes and the Publish runs, as GitHub (through handoff._gh) would answer them"""
    def __init__(self, fail=False, publish_sha=None):
        self.calls, self.fail, self.publish_sha, self.pages = [], fail, publish_sha, []

    def __call__(self, api_path, paginate=True):
        self.calls.append(api_path)
        self.pages.append(paginate)
        if self.fail:
            raise RuntimeError("gh exited 1: could not resolve host")
        if "/actions/workflows/" in api_path:
            runs = ([{"id": 77, "head_sha": self.publish_sha, "updated_at": _iso(T0 - 2 * DAY)}] if self.publish_sha else [])
            return [{"total_count": len(runs), "workflow_runs": runs}]
        n = int(api_path.split("/issues/")[1].split("/")[0])
        return [dict(c) for c in COMMENTS[n]]


def _card(i, st, subject, desc="", mtime=None):
    return {"id": str(i), "subject": subject, "status": st, "activeForm": "doing " + subject, "description": desc,
            "_mtime": T0 - DAY if mtime is None else mtime}


class Fixture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo, cls.c = _build_repo()
        cls.tmp = tempfile.mkdtemp(prefix="task-truth-law-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.repo, ignore_errors=True)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def idx(self):
        return TT.read_git(self.repo, T0)

    def looks(self, fail=False, name="looks.json"):
        p = os.path.join(self.tmp, name)
        if os.path.exists(p):
            os.remove(p)
        gh = FakeGitHub(fail)
        return TT.looks_view(TT.refresh_looks(p, T0, gh), T0), gh, p


class TheKeysAreWhatTheCardIsAbout(unittest.TestCase):

    def test_ranges_and_lists_expand_and_a_possessive_is_not_a_ship(self):
        self.assertEqual(TT.regs_in("REG-3154/3156 and REG-3193..3195 and REG-3183 to REG-3186"),
                         ["REG-3154", "REG-3156", "REG-3193", "REG-3194", "REG-3195", "REG-3183", "REG-3184", "REG-3185",
                          "REG-3186"])
        self.assertEqual(TT.lead_version("v3862 ship (carries v3861)"), "v3862")
        self.assertIsNone(TT.lead_version("v3864's first GitHub run: a law wrote his live ledger"),
                          "a version a subject only talks about was read as the ship it is")
        self.assertEqual(TT.branches_in("lives on claude/v3865. and origin/ci/bless/1, ci/ only"), ["claude/v3865"])
        # v3866 (the review): a comma list kept its first id, and a range inside a slash list dropped ids
        self.assertEqual(TT.regs_in("REG-2980, 2986, 3109 were never built"), ["REG-2980", "REG-2986", "REG-3109"])
        self.assertEqual(TT.regs_in("REG-2914/2915/2976/3021/3086-3089/3098"),
                         ["REG-2914", "REG-2915", "REG-2976", "REG-3021", "REG-3086", "REG-3087", "REG-3088", "REG-3089",
                          "REG-3098"])
        self.assertEqual(TT.regs_in("REG-3090, 12 cards wait"), ["REG-3090"], "a count after a comma was read as an id")

    def test_the_subject_names_the_keys_before_the_description(self):
        self.assertEqual(TT.card_keys(_card(1, "pending", "REG-3160 proof meter", "same class as REG-2203")),
                         (["REG-3160"], "subject"))
        self.assertEqual(TT.card_keys(_card(2, "pending", "Fleet chip: the repair book", "see REG-3158 on claude/v3862")),
                         (["REG-3158"], "description"))
        self.assertEqual(TT.card_keys(_card(3, "pending", "d2jsp pricing rules from real posts")), ([], None))


class EachKeyIsResolvedAgainstGit(Fixture):

    def test_every_rung_of_the_tree(self):
        idx = self.idx()
        self.assertTrue(idx["ok"], idx.get("why"))
        self.assertEqual(idx["publishedVer"], "v3801", "the published stamp is origin/main's WINDOWS_SHIP.json")
        no_looks = {"rows": [], "known": {"grokbot": True, "third": True}, "from": T0 - 30 * DAY}
        got = dict((k, TT.resolve_key(k, idx, idx["publishedVer"], no_looks)) for k in
                   ("REG-100", "REG-101", "REG-102", "REG-103", "REG-104", "REG-106", "REG-108", "REG-109", "REG-999",
                    "claude/v3804", "ci/claude-v3803", "claude/merged", "claude/never-made", "v3802", "v3804"))
        want = {"REG-100": ("live", "v3800"), "REG-101": ("live", "v3801"), "REG-102": ("shipped", "v3802"),
                "REG-103": ("graded", None), "REG-104": ("building", None), "REG-106": ("live", "v3801"),
                "REG-108": ("live", "v3801"), "REG-109": ("graded", None), "REG-999": ("no-evidence", None),
                "claude/v3804": ("building", None), "ci/claude-v3803": ("graded", None), "claude/merged": ("live", "v3801"),
                "claude/never-made": ("no-evidence", None), "v3802": ("shipped", "v3802"), "v3804": ("building", None)}
        self.assertEqual(dict((k, (v["phase"], v["ver"])) for k, v in got.items()), want)
        self.assertEqual(got["REG-101"]["sha"], self.c["c2"][:9], "the evidence is the FIRST main commit naming the key")
        self.assertEqual((got["REG-101"]["at"], got["REG-101"]["atWhat"]), (T0 - 8 * DAY, "shipped"),
                         "a live key's time is not when its version reached main")

    def test_a_hook_leaked_git_dir_does_not_point_the_reader_at_another_repo(self):
        with mock.patch.dict(os.environ, {"GIT_DIR": os.path.join(self.tmp, "not-a-repo"),
                                          "GIT_WORK_TREE": os.path.join(self.tmp, "not-a-tree")}):
            idx = TT.read_git(self.repo, T0)
        self.assertTrue(idx.get("ok"), "a leaked GIT_DIR sent the reader somewhere else: %r" % idx.get("why"))
        self.assertEqual(idx["main"], self.c["c4"])

    def test_a_tree_that_will_not_answer_is_unknown_never_no_evidence(self):
        idx = TT.git_index(os.path.join(self.tmp, "no-such-checkout"), T0)
        self.assertFalse(idx["ok"])
        t = TT.derive([_card(1, "in_progress", "REG-100 x", mtime=T0 - 9 * DAY), _card(2, "completed", "REG-104 y")],
                      idx, None, None, T0)
        self.assertEqual([t["byCard"][i]["phase"] for i in ("1", "2")], ["unknown", "unknown"],
                         "an unread tree was published as a measured phase")
        self.assertIsNone(t["summary"]["owed"], "an unread tree counted as a board that agrees")
        self.assertEqual([t["byCard"][i]["drift"] for i in ("1", "2")], [None, None], "an unread tree disagreed with a card")

    def test_the_index_is_read_once_per_head(self):
        cache = {}
        a = TT.git_index(self.repo, T0, cache=cache)
        b = TT.git_index(self.repo, T0 + 60 * 1000, cache=cache)
        self.assertIs(a, b, "the whole history was re-read with HEAD and origin/main unchanged")


class TheLooksAreReadAndUnknownStaysUnknown(Fixture):

    def test_a_look_counts_after_the_ship_and_for_what_its_heading_names(self):
        looks, gh, _p = self.looks()
        self.assertEqual(len(gh.calls), 3)
        self.assertIn("&since=", gh.calls[0])
        idx = self.idx()
        r101 = TT.resolve_key("REG-101", idx, "v3801", looks)
        self.assertEqual((r101["phase"], (r101["look"] or {}).get("id"), (r101["third"] or {}).get("id")),
                         ("third-eyed", "1008", "2001"), "the third eye is a SECOND-EYE row on #231")
        r100 = TT.resolve_key("REG-100", idx, "v3801", looks)
        self.assertEqual(r100["phase"], "live", "a look before the ship, a look whose EVIDENCE or RECAP named v3800 / "
                                                "REG-100, or the coder seat's plan counted as a look at REG-100")
        self.assertIsNone(r100["look"])
        self.assertIsNone(r100["third"], "a Grok CLI status note, or a second-eye row off its lane, counted as the third eye")

    def test_a_look_at_the_version_is_not_a_look_at_every_card_in_it(self):
        """REG-3281 (#86) - GrokBot's #230 6677563412 re-glassed v3865 and made six cards 'ready to close', four of which
        it never looked at. A version-only visual look is 'looked at the version, not this card'."""
        looks, _gh, _p = self.looks()
        rows = [r for r in looks["rows"] if r["id"] != "1008"]
        only_version = dict(looks, rows=rows)
        r = TT.resolve_key("REG-101", self.idx(), "v3801", only_version)
        self.assertEqual(r["phase"], "live", "a version-level look closed a card it never named")
        self.assertIsNone(r["look"])
        self.assertEqual((r["versionLook"] or {}).get("id"), "1002", "the version-level look was not said")
        self.assertIn("not at this card", r["why"])

    def test_a_tally_line_and_a_card_title_are_read_as_grokbot_wrote_them(self):
        """v3882 (#117, GrokBot's v3878 pass, #230 6708917680 - his lines, verbatim). The tally named #101 under FIXED and
        the whole line read "still" for every card on it; "#24 failed river read: NOT SEEN." read "still" off its TITLE."""
        body = ("Seat: GrokBot (visual eyes / debugger) -> Claude (coder)\n\n"
                "**Tally: FIXED 4 (#96 with one STILL detail, #97, #101, REG-3349 lamp) \u00b7 STILL 2 (#56, #104) \u00b7 "
                "NOT SEEN 4 (#96/#88 lane, #13, #24 failed read, #24 held-on-shut-locks) \u00b7 #40 answers but readTs UNKNOWN**\n"
                "7. **#24 failed river read: NOT SEEN.** No row read \"a newer read failed\".\n"
                "9. **#9 the dock: NOT FIXED** - still overlaps\n")
        got = dict((c, v) for c, _k, v in TT.cards_in(body))
        self.assertEqual(got.get("101"), "fixed", "a card under the tally's FIXED read still: %r" % got)
        self.assertEqual((got.get("97"), got.get("56"), got.get("104")), ("fixed", "still", "still"), got)
        self.assertNotIn("13", got, "a card GrokBot did NOT SEE was given a verdict: %r" % got)
        self.assertNotIn("24", got, "'failed' in a card's TITLE read as its verdict: %r" % got)
        self.assertNotIn("40", got, "a segment with no verdict word answered: %r" % got)
        self.assertEqual(got.get("9"), "still", "NOT FIXED read as FIXED")

    def test_a_per_card_answer_counts_for_that_card_only(self):
        """REG-3281 (#86) - GrokBot answers per CARD ("#5 the lamp (REG-101): FIXED"); with the card's key on the line, that
        is a look at the card, not at the version."""
        body = ("Seat: Grok Bot (visual eyes)\n\n# v3801 per-card answers\n- **#5 the lamp (REG-101):** FIXED - reads off\n"
                "- #6 the fan (REG-101): STILL overlapping\n- #7 the meter (REG-101): UNKNOWN, could not open it\n"
                "- posted on #230 6677563412 FIXED")
        self.assertEqual(TT.cards_in(body), [["5", ["REG-101"], "fixed"], ["6", ["REG-101"], "still"]],
                         "the per-card tags were misread (or #230 read as a card)")
        looks, _gh, _p = self.looks()
        base = [x for x in looks["rows"] if x["id"] not in ("1008", "1002")]
        idx = self.idx()

        def one(cid, line):
            b = "Seat: Grok Bot (visual eyes)\n\n# v3801 per-card answers\n" + line
            return dict(looks, rows=base + [dict(TT.look_row({"id": cid, "created_at": _iso(T0 - 6 * DAY), "body": b}, 230))])
        fixed = one(1099, "- **#5 the lamp (REG-101):** FIXED - reads off")
        self.assertEqual((TT.resolve_key("REG-101", idx, "v3801", fixed, card=5)["look"] or {}).get("id"), "1099")
        self.assertIsNone(TT.resolve_key("REG-101", idx, "v3801", fixed, card=8)["look"], "another card's answer counted")
        still = one(1101, "- #6 the fan (REG-101): STILL overlapping")
        self.assertEqual((TT.resolve_key("REG-101", idx, "v3801", still, card=6)["refuted"] or {}).get("id"), "1101",
                         "a STILL answer for the card did not refute it")
        # a card keyed on its VERSION: refuted_in reads REG ids only, so only the per-card STILL can refute it
        still_v = one(1103, "- #6 the fan (v3801): STILL overlapping")
        rv = TT.resolve_key("v3801", idx, "v3801", still_v, card=6)
        self.assertEqual((rv["refuted"] or {}).get("id"), "1103", "a STILL answer for a version-keyed card passed it: %r"
                         % ({"look": (rv["look"] or {}).get("id"), "phase": rv["phase"], "why": rv["why"]},))
        unk = one(1102, "- #7 the meter (REG-101): UNKNOWN, could not open it")
        self.assertIsNone(TT.resolve_key("REG-101", idx, "v3801", unk, card=7)["look"], "an UNKNOWN answer passed a card")

    def test_a_card_number_without_the_cards_key_is_not_this_card(self):
        """REG-3281 - MEASURED on #230 12:05Z: GrokBot read "cards #21 · #27 · #45 · #59" as the GitHub issues of those
        numbers. "#59 ... SAW" without the card's own key must not pass board card #59."""
        body = ("Seat: Grok Bot (visual eyes / debugger)\n\n## Live checks for cards #21 · #27 · #45 · #59 (tip v3869)\n"
                "- `#59` · version key **v2090 `#vault-moved-note`** · title *Tools vault signpost* · **SAW**.\n"
                "- `#21` · version key **v2078 `status.eagle`** · **STILL (glass)**.")
        looks, _gh, _p = self.looks()
        row = dict(TT.look_row({"id": 1100, "created_at": _iso(T0 - 6 * DAY), "body": body}, 230))
        lk = dict(looks, rows=[x for x in looks["rows"] if x["id"] not in ("1008", "1002")] + [row])
        idx = self.idx()
        self.assertIsNone(TT.resolve_key("REG-101", idx, "v3801", lk, card=59)["look"],
                          "another numbering's #59 passed board card #59")
        self.assertIsNone(TT.resolve_key("REG-101", idx, "v3801", lk, card=21)["refuted"],
                          "another numbering's #21 refuted board card #21")

    def test_no_status_note_plan_or_misposted_row_is_a_look(self):
        rows = dict((c["id"], TT.look_row(c, n)) for n in (230, 231) for c in COMMENTS[n])
        self.assertEqual(dict((i, (r or {}).get("seat")) for i, r in rows.items()),
                         {1001: "grokbot", 1002: "grokbot", 1003: None, 1004: None, 1005: None, 1006: None,
                          1007: "grokbot", 1008: "grokbot", 2001: "third", 2002: None, 2003: "third"})
        self.assertEqual((rows[1002]["vers"], rows[1002]["regs"]), (["v3801"], []), "a look is about its HEADING only")

    def test_an_eye_that_could_not_judge_is_no_look(self):
        rows = dict((c["id"], TT.look_row(c, 231)) for c in COMMENTS[231])
        self.assertTrue(rows[2003]["noLook"], "a cannot-tell row was kept as a look")
        self.assertFalse(rows[2001]["noLook"])
        looks, _gh, _p = self.looks()
        r = TT.resolve_key("REG-100", self.idx(), "v3801", looks)
        self.assertIsNone(r["third"], "a cannot-tell row made v3800 third-eyed")
        self.assertIsNone(r["refuted"], "a cannot-tell row refuted the work - it judged nothing either way")

    def test_a_headline_that_names_an_unreachable_eye_does_not_hide_a_verdict(self):
        """REG-3246 (the #231 look at v3867): a row whose headline mentions an eye that was unreachable but which STATES a
        verdict, or fails, is a look - skipping it let an older passing look decide the card."""
        said = {"id": 9001, "created_at": _iso(T0), "updated_at": _iso(T0),
                "body": "SECOND-EYE\nREG-3201: the eye was unreachable twice, then answered\nverdict: findings\nmodel: grok-cli"}
        failed = {"id": 9002, "created_at": _iso(T0), "updated_at": _iso(T0),
                  "body": "SECOND-EYE\nREG-3202: unreachable last night - still FAILS on the second look"}
        self.assertFalse(TT.look_row(said, 231)["noLook"], "a stated verdict was hidden by an 'unreachable' headline")
        self.assertFalse(TT.look_row(failed, 231)["noLook"], "a failing look was hidden by an 'unreachable' headline")
        self.assertTrue(TT.look_row(COMMENTS[231][2], 231)["noLook"], "premise: an inline cannot-tell is still no look")

    def test_the_newest_look_decides_and_a_failing_one_refutes(self):
        looks, _gh, _p = self.looks()
        r = TT.resolve_key("REG-106", self.idx(), "v3801", looks)
        self.assertEqual((r["phase"], r["look"], (r["refuted"] or {}).get("id")), ("live", None, "1007"),
                         "a look that says REG-106 still FAILS read as a look that passed it")
        self.assertIn("still fails", r["why"])

    def test_github_is_asked_at_most_every_ten_minutes(self):
        _l, gh, p = self.looks()
        TT.refresh_looks(p, T0 + 5 * 60 * 1000, gh)
        self.assertEqual(len(gh.calls), 3, "GitHub was asked again inside 10 minutes")
        TT.refresh_looks(p, T0 + TT.LOOKS_EVERY_MS, gh)
        self.assertEqual(len(gh.calls), 6)
        self.assertEqual([pg for c, pg in zip(gh.calls, gh.pages) if "/actions/" in c], [False, False],
                         "the newest Publish run was asked with --paginate (every run GitHub keeps)")

    def test_live_is_what_the_site_serves_not_origin_main(self):
        p = os.path.join(self.tmp, "looks-site.json")
        if os.path.exists(p):
            os.remove(p)
        cache = TT.refresh_looks(p, T0, FakeGitHub(publish_sha=self.c["c1"]))
        site = TT.site_view(cache, T0, self.repo)
        self.assertEqual(site["ver"], "v3800", site)
        r = TT.resolve_key("REG-101", self.idx(), site, TT.looks_view(cache, T0))
        self.assertEqual(r["phase"], "shipped", "on origin/main read as live while the site still served v3800")
        self.assertEqual(TT.site_view(cache, T0 + TT.LOOKS_STALE_MS + 1, self.repo)["ver"], None,
                         "a Publish reading past its age was used as the site's version")

    def test_an_unread_lane_is_unknown_never_not_looked(self):
        looks, _gh, _p = self.looks(fail=True, name="looks-failed.json")
        self.assertEqual(looks["known"], {"grokbot": False, "third": False})
        r = TT.resolve_key("REG-101", self.idx(), "v3801", looks)
        self.assertEqual(r["phase"], "live")
        self.assertEqual(r["unknown"], ["looked", "third-eyed"], "a lane nobody read was said 'not looked'")
        t = TT.derive([_card(1, "in_progress", "REG-101 x")], self.idx(), None, looks, T0)
        self.assertIsNone(t["byCard"]["1"]["drift"], "a card was said ready or not over looks nobody read")

    def test_a_ship_older_than_the_cache_is_unknown(self):
        looks, _gh, _p = self.looks()
        looks = dict(looks, rows=[], **{"from": T0 - 5 * DAY})
        r = TT.resolve_key("REG-101", self.idx(), "v3801", looks)
        self.assertIn("looked", r["unknown"], "a ship from before the looks the cache holds was said 'not looked'")

    def test_a_cache_that_will_not_read_is_never_written_over(self):
        p = os.path.join(self.tmp, "looks-corrupt.json")
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        self.assertIsNone(TT.refresh_looks(p, T0, FakeGitHub()))
        with io.open(p, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "{ not json", "an unreadable store was written over")
        self.assertEqual(TT.looks_view(None, T0)["known"], {"grokbot": False, "third": False})


class AHandStatusThatDisagreesIsFlagged(Fixture):

    def _derive(self, cards):
        looks, _gh, _p = self.looks()
        return TT.derive(cards, self.idx(), "v3801", looks, T0)       # the site serves the fixture's v3801

    def test_each_kind_of_drift_with_its_reason(self):
        cards = [_card(1, "in_progress", "REG-101 the second fix", mtime=T0 - 10 * DAY),
                 _card(2, "completed", "REG-104 the building one"),
                 _card(3, "completed", "Shelf questions answered - no change"),
                 _card(4, "pending", "REG-103 the graded one", mtime=T0 - 3 * DAY),
                 _card(5, "in_progress", "REG-999 nothing yet", mtime=T0 - 3 * DAY),
                 _card(6, "in_progress", "REG-998 nothing yet, fresh", mtime=T0 - 1 * DAY),
                 _card(7, "in_progress", "REG-997 nothing, age unknown", mtime=None),
                 _card(8, "in_progress", "REG-100 the first fix"),
                 _card(9, "in_progress", "REG-101 is INERT", "fixed by REG-104 on claude/v3804")]
        cards[6]["_mtime"] = None
        t = self._derive(cards)
        kinds = dict((cid, (d["drift"] or {}).get("kind")) for cid, d in t["byCard"].items())
        self.assertEqual(kinds, {"1": "ready-to-close", "2": "closed-never-shipped", "3": None, "4": "work-started",
                                 "5": "nothing-built", "6": None, "7": None, "8": None, "9": None})
        self.assertIn("#230 comment 1008", t["byCard"]["1"]["drift"]["say"], "ready to close does not name the look")
        self.assertIn("#231 comment 2001", t["byCard"]["1"]["drift"]["say"], "ready to close does not name the third eye")
        self.assertIn("REG-104 building", t["byCard"]["2"]["drift"]["say"])
        self.assertEqual(t["byCard"]["9"]["phase"], "building",
                         "a fix still building in the description let an old shipped key read ready to close")
        self.assertEqual(t["summary"]["owed"], 4)
        self.assertEqual(t["summary"]["first"][0]["kind"], "closed-never-shipped", "the red flag is not named first")

    def test_evidence_older_than_the_hand_is_accepted_and_shipped_open_is_said(self):
        t = self._derive([_card(1, "in_progress", "REG-101 the second fix", mtime=T0 - 1 * DAY),
                          _card(2, "in_progress", "REG-100 the first fix", mtime=T0 - 12 * DAY),
                          _card(3, "pending", "REG-103 the graded one", mtime=T0 - 1 * DAY),
                          _card(4, "pending", "REG-100 the first fix, never moved", mtime=T0 - 12 * DAY)])
        self.assertIsNone(t["byCard"]["1"]["drift"], "a card touched after its looks (a reviewed flag) was flagged again")
        self.assertIsNone(t["byCard"]["3"]["drift"], "a card touched after its commits was flagged again")
        d2 = t["byCard"]["2"]["drift"] or {}
        self.assertEqual(d2.get("kind"), "shipped-still-open", "a card shipped 10 days ago still read as plain in progress")
        self.assertIn("left: GrokBot's look on #230", d2.get("say", ""))
        d4 = t["byCard"]["4"]["drift"] or {}
        self.assertEqual(d4.get("kind"), "shipped-still-open", "a pending card whose work is live read 'work started'")
        self.assertIn("shipped and still pending", d4.get("say", ""))

    def test_newer_work_in_the_description_holds_the_card_a_precedent_does_not(self):
        t = self._derive([_card(1, "in_progress", "REG-101 is INERT", "fixed by REG-102 (on main, not published)",
                                mtime=T0 - 10 * DAY),
                          _card(2, "in_progress", "REG-102 the third fix", "same class as REG-100", mtime=T0 - 10 * DAY)])
        self.assertEqual(t["byCard"]["1"]["phase"], "shipped",
                         "a fix on main the site does not serve yet let the old key read ready to close")
        self.assertNotEqual((t["byCard"]["1"]["drift"] or {}).get("kind"), "ready-to-close")
        self.assertEqual(t["byCard"]["2"]["phase"], "shipped", "a precedent in the description moved the card")

    def test_a_description_key_says_it_is_one(self):
        t = self._derive([_card(1, "pending", "Fleet chip: the repair book", "lives on claude/v3804", mtime=T0 - 2 * DAY)])
        self.assertEqual(t["byCard"]["1"]["drift"]["kind"], "work-started")
        self.assertIn("keyed on its description", t["byCard"]["1"]["drift"]["say"])


class TheBoardCarriesItScrubbed(Fixture):

    def test_each_card_wears_its_phase_and_flag_and_the_record_counts_them(self):
        looks, _gh, _p = self.looks()
        cards = [_card(1, "in_progress", "REG-101 the second fix", mtime=T0 - 10 * DAY),
                 _card(2, "completed", "REG-104 the building one")]
        t = TT.derive(cards, self.idx(), "v3801", looks, T0)
        b = TB.board(cards, "t", T0, truth=t)
        ph = dict((r["id"], ((r.get("phase") or {}).get("p"), (r.get("phase") or {}).get("v"),
                             (r.get("drift") or {}).get("kind"))) for r in b["cards"])
        self.assertEqual(ph, {"1": ("third-eyed", "v3801", "ready-to-close"), "2": ("building", None, "closed-never-shipped")})
        self.assertEqual((b["truth"]["owed"], b["truth"]["drift"]["ready-to-close"], b["truth"]["publishedVer"]), (2, 1, "v3801"))
        later = TB.board(cards, "t", T0 + 60 * 1000, truth=TT.derive(cards, self.idx(), "v3801", looks, T0 + 60 * 1000))
        c1 = dict((r["id"], r) for r in b["cards"])["1"]["phase"]
        self.assertEqual((c1["look"], c1["third"], c1["w"]), ("1008", "2001", "third-eyed"),
                         "the chip does not carry which comments made it third-eyed, or what its time is")
        self.assertEqual(TB.digest(later), TB.digest(b), "an unchanged board reads as a new one every minute")
        self.assertNotIn("phase", TB.board(cards, "t", T0)["cards"][0], "a phase nobody derived was published")

    def test_the_derived_words_are_scrubbed_like_the_cards(self):
        truth = {"ok": True, "byCard": {"1": {"phase": "building", "why": DIRTY, "keys": ["claude/x"], "sha": "abc1234",
                                              "drift": {"kind": "work-started", "say": DIRTY}}},
                 "summary": {"owed": 1, "drift": {"work-started": 1}, "phases": {"building": 1}}}
        b = TB.board([_card(1, "pending", "x")], "t", T0, truth=truth)
        blob = json.dumps(b)
        self.assertNotIn("/" + "Users/", blob, "a derived why carried a home path to the public board")
        self.assertNotIn("192.0.2.7", blob)


class TheConsolePublishesAndTheEagleCounts(Fixture):

    @classmethod
    def setUpClass(cls):
        super(TheConsolePublishesAndTheEagleCounts, cls).setUpClass()
        import control_app as CA
        import console_doctor as CD
        cls.CA, cls.CD = CA, CD

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="task-truth-board-", dir=self.tmp)
        os.makedirs(os.path.join(self.d, "session-x"))
        for c in (_card(1, "in_progress", "REG-101 the second fix"), _card(2, "completed", "REG-104 the building one")):
            c.pop("_mtime")
            fp = os.path.join(self.d, "session-x", "%s.json" % c["id"])
            with io.open(fp, "w", encoding="utf-8") as fh:
                json.dump(c, fh)
            os.utime(fp, ((T0 - 10 * DAY) / 1000.0, (T0 - 10 * DAY) / 1000.0))    # the hand set them before the evidence
        self.posts = []
        self._saved = dict(self.CA._TASK_BOARD)
        self._truth = dict(self.CA._TASK_TRUTH)
        self.CA._TASK_BOARD.update(state={}, posted=0)

    def tearDown(self):
        self.CA._TASK_BOARD.clear()
        self.CA._TASK_BOARD.update(self._saved)
        self.CA._TASK_TRUTH.clear()
        self.CA._TASK_TRUTH.update(self._truth)

    def _post(self, url, body, keypath):
        self.posts.append(body)
        return {"ok": True}

    def _derive(self, cards, now_ms):
        return self.CA.task_truth_derive(cards, now_ms, _repo=self.repo, _looks_path=os.path.join(self.d, "looks.json"),
                                         _gh=FakeGitHub(), _published="v3801")

    def _publish(self, derive):
        CA = self.CA
        with mock.patch.object(CA, "_beacon_suppressed_by", return_value=None), \
                mock.patch.object(CA, "_task_board_state_path", return_value=os.path.join(self.d, "state.json")):
            return CA.task_board_publish_once(now_ms=T0, _post=self._post, _tasks_dir=self.d, _label="Konyo · Mac",
                                              _platform="darwin", _derive=derive)

    def test_the_lane_publishes_the_derived_board(self):
        r = self._publish(self._derive)
        self.assertTrue(r["posted"], r)
        cards = dict((c["id"], c) for c in self.posts[0]["board"]["cards"])
        self.assertEqual(((cards["1"].get("phase") or {}).get("p"), (cards["2"].get("drift") or {}).get("kind")),
                         ("third-eyed", "closed-never-shipped"), "the posted board carries no derived phase")
        self.assertEqual(r["truth"]["summary"]["owed"], 2)

    def test_the_console_reads_the_site_from_the_publish_run(self):
        cards = [_card(1, "in_progress", "REG-101 the second fix", mtime=T0 - 10 * DAY)]
        t = self.CA.task_truth_derive(cards, T0, _repo=self.repo, _looks_path=os.path.join(self.d, "looks-site.json"),
                                      _gh=FakeGitHub(publish_sha=self.c["c1"]))
        self.assertEqual((t["publishedVer"], t["mainVer"]), ("v3800", "v3801"))
        self.assertEqual(t["byCard"]["1"]["phase"], "shipped", "the console read origin/main's stamp as what the site serves")

    def test_the_lane_derives_on_every_tick_and_settles_the_record(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        i = src.index("\ndef _task_board_loop():\n")
        self.assertEqual(src.count("\ndef _task_board_loop():\n"), 1)
        body = src[i:src.index("\ndef ", i + 10)]
        code = "\n".join(l.split("#", 1)[0] for l in body.splitlines())
        self.assertIn("            r = task_board_publish_once(_derive=task_truth_derive)\n", code + "\n",
                      "the lane publishes a board nobody derived")
        self.assertIn("            _task_truth_settle(r)\n", code + "\n", "the eagle's record is never written")

    def test_the_record_says_on_worked_last_and_owed(self):
        CA, CD = self.CA, self.CD
        path = os.path.join(self.d, "truth.json")
        self.CA._TASK_TRUTH.update(on=None, worked=0, lastTs=None, owed=None)
        rec = CA._task_truth_settle(self._publish(self._derive), now_ms=T0, _path=path)
        self.assertEqual((rec["on"], rec["worked"], rec["lastTs"], rec["owed"]), (True, 1, T0, 2))
        with mock.patch.object(CA, "_task_truth_state_path", return_value=path), \
                mock.patch.object(CD.time, "time", return_value=(T0 + 60 * 1000) / 1000.0):
            st, line = CD._check_the_board_agrees_with_the_tree()
        self.assertEqual(st, CD.MISSING, line)
        self.assertIn("1 ready to close", line)
        self.assertIn("1 closed never shipped", line)
        off = CA._task_truth_settle({"posted": False, "why": "the board lives on his Mac; this PC only reads it"},
                                    now_ms=T0, _path=path)
        self.assertIs(off["on"], False)
        self.assertEqual(CD._board_tree_verdict(off, T0)[0], CD.UNMEASURED)
        self.assertIn("Future button", CD._board_tree_verdict(off, T0)[1])
        unk = CA._task_truth_settle({"posted": False, "why": "the board dir would not list - UNKNOWN, nothing posted"},
                                    now_ms=T0, _path=path)
        self.assertIsNone(unk["on"])
        self.assertEqual(CD._board_tree_verdict(unk, T0)[0], CD.UNKNOWN)

    def test_the_eagle_row_never_calls_a_stale_or_unread_board_agreeing(self):
        CD = self.CD
        good = {"on": True, "worked": 3, "lastTs": T0, "owed": 0, "cards": 2, "head": "abc", "phases": {"live": 2},
                "looks": "read"}
        self.assertEqual(CD._board_tree_verdict(good, T0 + 60 * 1000)[0], CD.OK)
        self.assertEqual(CD._board_tree_verdict(good, T0 + 11 * 60 * 1000)[0], CD.UNKNOWN, "a stale reading read as agreement")
        self.assertEqual(CD._board_tree_verdict(dict(good, owed=None), T0)[0], CD.UNKNOWN)
        self.assertEqual(CD._board_tree_verdict(dict(good, lastTs=None), T0)[0], CD.UNKNOWN)
        with mock.patch.object(self.CA, "_task_truth_state_path", return_value=os.path.join(self.d, "never.json")):
            self.assertEqual(CD._check_the_board_agrees_with_the_tree()[0], CD.UNKNOWN)
        import corroborate as CO
        self.assertIn("the board agrees with the tree", [n for n, _f in CD.CHECKS], "the eagle never asks")
        self.assertIn("the board agrees with the tree", CD.WATCHES)
        self.assertIn("the board agrees with the tree", CO.NO_JOINT_YET)


class ThePageDrawsIt(unittest.TestCase):

    def test_the_page_draws_the_chip_the_flag_and_the_count_as_text(self):
        with io.open(os.path.join(HERE, "tasks_board.html"), encoding="utf-8") as fh:
            page = fh.read()
        script = page[page.index("<script>"):]
        for needle in ("    if (c.phase) li.appendChild(chip(c.phase));\n",
                       "    if (c.drift && c.drift.kind) { var dr = el('div', 'dr', c.drift.say || c.drift.kind);",
                       "    if (!t) tr.textContent = 'not compared with the tree (published without a derivation)';\n",
                       "    var words = ph === 'unknown' ? 'phase UNKNOWN' : ph",
                       "    if (p && p.look) words += ' \u00b7 GrokBot #230 comment ' + p.look;\n",
                       "    if (p && p.third) words += ' \u00b7 third eye #231 comment ' + p.third;\n",
                       "    words += since(p && p.at, p && p.w && p.w !== ph ? p.w : '');"):
            self.assertEqual(script.count(needle), 1, "the page no longer draws: %r" % needle)
        self.assertIn('<span id="tb-truth"></span>', page)
        self.assertNotIn("innerHTML", script)


RED_PROOF = [
    {"why": "v3882 (#117) - a tally line is judged whole again: every card on it reads 'still' (#101, FIXED, stays waiting)",
     "file": "tv/task_truth.py",
     "find": "        segs = re.split(r\"\\s+[·|]\\s+|;\\s+\", line) if (bad and good) else [line]\n",
     "replace": "        segs = [line]\n", "matches": 1},
    {"why": "v3882 (#117) - GrokBot's NOT SEEN answers for the card again ('#24 failed river read: NOT SEEN' reads still)",
     "file": "tv/task_truth.py",
     "find": "(re.compile(r\"\\b(?:NOT\\s+SEEN|CANNOT\\s+TELL|UNKNOWN)\\b\"), None),",
     "replace": "", "matches": 1},
    {"why": "v3882 (#117) - NOT FIXED reads as FIXED (the pass tag inside the fail)",
     "file": "tv/task_truth.py",
     "find": "_CAP_VERDICTS = ((re.compile(r\"\\bnot\\s+fixed\\b\", re.I), \"still\"), ",
     "replace": "_CAP_VERDICTS = (", "matches": 1},
    {"why": "REG-3281 (#86) - a GrokBot look at the VERSION counts for every card shipped in it again",
     "file": "tv/task_truth.py",
     "find": "            (about_it if by_version else ver_only).append(r)\n",
     "replace": "            about_it.append(r)\n",
     "matches": 1},
    {"why": "REG-3281 (#86) - a STILL answer for the card never refutes it",
     "file": "tv/task_truth.py",
     "find": " or (card and any(\n            a[0] == card and key in a[1] and a[2] == \"still\" for a in (last.get(\"cardAnswers\") or []))):\n",
     "replace": ":\n",
     "matches": 1},
    {"why": "REG-3281 (#86) - a per-card FIXED answer never counts for the card",
     "file": "tv/task_truth.py",
     "find": "        carded = bool(card) and any(a[0] == card and key in a[1] for a in (r.get(\"cardAnswers\") or []))\n",
     "replace": "        carded = False\n",
     "matches": 1},
    {"why": "REG-3246 - the headline alone makes a row no look again, so a stated verdict under an 'unreachable' headline is skipped",
     "file": "tv/task_truth.py",
     "find": "    if verdict:\n        no_look = bool(_NO_LOOK_RX.search(verdict))\n    else:\n        no_look = (not fail and not refutes) and bool(_NO_LOOK_RX.search(ab[\"line\"]))\n",
     "replace": "    no_look = bool(_NO_LOOK_RX.search(ab[\"line\"]) or (verdict and _NO_LOOK_RX.search(verdict)))\n",
     "matches": 1},
    {"why": "REG-3217 - a REG range on a card (REG-3193..3195) keys only its first id",
     "file": "tv/task_truth.py",
     "find": "                    got += list(range(lo + 1, hi + 1)) if hi - lo <= RANGE_MAX else [hi]\n",
     "replace": "                    got += [hi]\n",
     "matches": 1},
    {"why": "REG-3217 - a subject that only talks about a version (v3864's first run) is read as its ship",
     "file": "tv/task_truth.py",
     "find": "_LEAD_VER_RX = re.compile(r\"^\\s*v(\\d{4})\\b(?![\u2019']s)\")",
     "replace": "_LEAD_VER_RX = re.compile(r\"^\\s*v(\\d{4})\\b\")",
     "matches": 1},
    {"why": "REG-3217 - the description's precedents key the card before its own subject",
     "file": "tv/task_truth.py",
     "find": "    for basis, keys in ((\"subject\", regs_in(subj)),",
     "replace": "    for basis, keys in ((\"subject\", regs_in(desc)),",
     "matches": 1},
    {"why": "REG-3217 - work on a ci/ branch reads as local building, never graded",
     "file": "tv/task_truth.py",
     "find": "            out.update(phase=\"graded\" if on_ci else \"building\", sha=pick[0][:9], at=pick[1],",
     "replace": "            out.update(phase=\"building\", sha=pick[0][:9], at=pick[1],",
     "matches": 1},
    {"why": "REG-3217 - a commit on main reads live while the site still publishes the version before it",
     "file": "tv/task_truth.py",
     "find": "    elif pv < nv:\n        out[\"why\"] = \"on origin/main; the site still serves %s (the newest successful Publish run)\" % site.get(\"ver\")\n        return out\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3217 - an unstamped main commit loses the version it shipped in",
     "file": "tv/task_truth.py",
     "find": "        main_ver[sha] = lv or cur\n",
     "replace": "        main_ver[sha] = lv\n",
     "matches": 1},
    {"why": "REG-3217 - a GrokBot comment from BEFORE the ship counts as a look at it",
     "file": "tv/task_truth.py",
     "find": "    look, l_ref, l_ver = (_look_verdict(looks, \"grokbot\", key, ver, t_main or 0, card=card, by_version=False)\n",
     "replace": "    look, l_ref, l_ver = (_look_verdict(looks, \"grokbot\", key, ver, 0, card=card, by_version=False)\n",
     "matches": 1},
    {"why": "REG-3217 - a version in a look's evidence list counts as a look at that version (measured: 30 of 84 cards)",
     "file": "tv/task_truth.py",
     "find": "        vs, rs = versions_in(line), regs_in(line)\n",
     "replace": "        vs, rs = versions_in(str(body or \"\")[:LOOK_HEAD_CHARS]), regs_in(line)\n",
     "matches": 1},
    {"why": "REG-3217 - a lane GitHub never answered reads as read, so 'not looked' is said about nobody's reading",
     "file": "tv/task_truth.py",
     "find": "        ok = isinstance(lane.get(\"okAt\"), int) and now_ms - lane[\"okAt\"] < LOOKS_STALE_MS\n",
     "replace": "        ok = True\n",
     "matches": 1},
    {"why": "REG-3217 - a ship older than the looks the cache holds is said 'not looked' instead of UNKNOWN",
     "file": "tv/task_truth.py",
     "find": "    elif not known.get(\"grokbot\") or before_window:\n",
     "replace": "    elif not known.get(\"grokbot\"):\n",
     "matches": 1},
    {"why": "REG-3217 - an unreadable looks cache is written over",
     "file": "tv/task_truth.py",
     "find": "    cache = load_looks(path)\n    if cache is None:\n        return None\n",
     "replace": "    cache = load_looks(path) or {}\n",
     "matches": 1},
    {"why": "REG-3217 - GitHub is asked on every tick instead of at most every 10 min",
     "file": "tv/task_truth.py",
     "find": "        if isinstance(lane.get(\"triedAt\"), int) and now_ms - lane[\"triedAt\"] < every_ms:\n            continue\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3217 - a tree that would not answer is published as no-evidence",
     "file": "tv/task_truth.py",
     "find": "        d[\"why\"] = (idx or {}).get(\"why\") or \"the tree was not read - UNKNOWN\"\n        return d\n",
     "replace": "        d.update(phase=\"no-evidence\", hi=\"no-evidence\", why=\"the tree was not read\")\n        return d\n",
     "matches": 1},
    {"why": "REG-3217 - a git hook's leaked GIT_DIR points the reader at another repo",
     "file": "tv/task_truth.py",
     "find": "    env = dict((k, v) for k, v in os.environ.items() if not k.startswith(\"GIT_\"))\n",
     "replace": "    env = dict(os.environ)\n",
     "matches": 1},
    {"why": "REG-3217 - the whole history is re-read every tick with HEAD unchanged",
     "file": "tv/task_truth.py",
     "find": "    if held and held.get(\"heads\") == heads and now_ms - held.get(\"at\", 0) < GIT_TTL_MS and held[\"idx\"].get(\"ok\"):\n        return held[\"idx\"]\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3217 - a fix still moving in the description lets an old shipped key read ready to close",
     "file": "tv/task_truth.py",
     "find": "                if RANK[r[\"phase\"]] < RANK[lo[\"phase\"]]:\n",
     "replace": "                if False:\n",
     "matches": 1},
    {"why": "REG-3218 - a closed card whose work never reached main is not flagged",
     "file": "tv/task_truth.py",
     "find": "        if RANK[hi] >= RANK[\"building\"] and RANK[ph] < RANK[\"shipped\"]:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3218 - a closed card that needed no code (nothing in git) is flagged red",
     "file": "tv/task_truth.py",
     "find": "        if RANK[hi] >= RANK[\"building\"] and RANK[ph] < RANK[\"shipped\"]:\n",
     "replace": "        if RANK[ph] < RANK[\"shipped\"]:\n",
     "matches": 1},
    {"why": "REG-3218 - a card merely live (not looked, not third-eyed) is said ready to close",
     "file": "tv/task_truth.py",
     "find": "    elif ph == \"third-eyed\" and newer(d.get(\"evidenceAt\")):\n",
     "replace": "    elif RANK[ph] >= RANK[\"live\"]:\n",
     "matches": 1},
    {"why": "REG-3218 - a pending card with commits is not flagged",
     "file": "tv/task_truth.py",
     "find": "    elif status == \"pending\" and RANK[hi] >= RANK[\"building\"] and newer(d.get(\"lastCommit\")):\n",
     "replace": "    elif False:\n",
     "matches": 1},
    {"why": "REG-3218 - a fresh in_progress card is flagged as nothing built",
     "file": "tv/task_truth.py",
     "find": "            and not isinstance(age_ms, bool) and age_ms > STALE_DAYS * DAY_MS:\n",
     "replace": "            and not isinstance(age_ms, bool) and age_ms >= 0:\n",
     "matches": 1},
    {"why": "REG-3218 - a description-keyed flag does not say what it keyed on",
     "file": "tv/task_truth.py",
     "find": "    if d.get(\"basis\") == \"description\":\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3866 (review blocker) - a Grok CLI status note on #231 ('has not read the range') counts as the third eye",
     "file": "tv/task_truth.py",
     "find": "    (\"third\", re.compile(r\"^(?:second-eye\\b|grok\\s*cli\\s+second\\s+eye\\b|seat:\\s*grok\\s*cli\\s*\\(cross-family)\", re.I)),\n",
     "replace": "    (\"third\", re.compile(r\"^(?:second-eye\\b|seat:\\s*grok\\s*cli\\b)\", re.I)),\n",
     "matches": 1},
    {"why": "v3866 (review blocker) - a look counts on either lane, so a second-eye row posted on #230 is the third eye",
     "file": "tv/task_truth.py",
     "find": "    if (seat, int(issue)) not in ((\"grokbot\", GROKBOT_ISSUE), (\"third\", THIRD_ISSUE)):\n",
     "replace": "    if seat not in (\"grokbot\", \"third\"):\n",
     "matches": 1},
    {"why": "v3866 - a SECOND-EYE row that says cannot-tell counts as the third eye (the v3864 row made 4 cards ready)",
     "file": "tv/task_truth.py",
     "find": "        if r.get(\"noLook\"):\n            continue",
     "replace": "        if False:\n            continue",
     "matches": 1},
    {"why": "v3866 (review) - GrokBot's coder seat ('Seat: Grok Bot (code)', a plan) counts as a GrokBot look",
     "file": "tv/task_truth.py",
     "find": "seat:\\s*grok\\s*bot\\s*\\((?!\\s*code)",
     "replace": "seat:\\s*grok\\s*bot\\s*\\(",
     "matches": 1},
    {"why": "v3866 (review) - a REG id anywhere in a look (a changelog recap) counts as what it looked at",
     "file": "tv/task_truth.py",
     "find": "            \"regs\": ab[\"regs\"], \"vers\": ab[\"vers\"],",
     "replace": "            \"regs\": regs_in(body)[:60], \"vers\": ab[\"vers\"],",
     "matches": 1},
    {"why": "v3866 (review) - a look that says the work still FAILS counts as a look that passed it",
     "file": "tv/task_truth.py",
     "find": "    if last.get(\"fail\") or key in (last.get(\"refutes\") or []) or (card and any(\n            a[0] == card and key in a[1] and a[2] == \"still\" for a in (last.get(\"cardAnswers\") or []))):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3866 (review) - a comma list of REG ids keeps only its first",
     "file": "tv/task_truth.py",
     "find": "            if it and (it.group(1) or len(it.group(2)) == width):\n",
     "replace": "            if it and it.group(1):\n",
     "matches": 1},
    {"why": "v3866 (review) - a fix on main the site does not serve yet, named in the description, no longer holds the card",
     "file": "tv/task_truth.py",
     "find": "                if subj_first is None and r[\"phase\"] not in (\"building\", \"graded\"):\n",
     "replace": "                if r[\"phase\"] not in (\"building\", \"graded\"):\n",
     "matches": 1},
    {"why": "v3866 (review) - a card in progress whose work shipped days ago carries no flag (#5 v3862 ship, #9, #10)",
     "file": "tv/task_truth.py",
     "find": "    elif status in (\"in_progress\", \"pending\") and RANK[\"shipped\"] <= RANK[ph] < RANK[\"third-eyed\"] \\\n",
     "replace": "    elif False \\\n",
     "matches": 1},
    {"why": "v3866 - a PENDING card whose work is live reads 'work started' instead of shipped and still pending",
     "file": "tv/task_truth.py",
     "find": "    elif status in (\"in_progress\", \"pending\") and RANK[\"shipped\"] <= RANK[ph] < RANK[\"third-eyed\"] \\\n",
     "replace": "    elif status == \"in_progress\" and RANK[\"shipped\"] <= RANK[ph] < RANK[\"third-eyed\"] \\\n",
     "matches": 1},
    {"why": "v3866 (review) - a flag he reviewed (the card touched after its evidence) can never be accepted",
     "file": "tv/task_truth.py",
     "find": "        return isinstance(t, (int, float)) and (hand is None or t > hand)\n",
     "replace": "        return isinstance(t, (int, float))\n",
     "matches": 1},
    {"why": "v3866 (review) - live is origin/main's stamp again, so the hour a Publish runs reads live",
     "file": "tv/control_app.py",
     "find": "    site = _published if _published is not None else _tt.site_view(cache, now_ms, _repo or REPO, run=_run or _git_run)\n",
     "replace": "    site = _published if _published is not None else idx.get(\"publishedVer\")\n",
     "matches": 1},
    {"why": "v3866 (review) - the newest Publish run is asked with --paginate, walking every run GitHub keeps",
     "file": "tv/task_truth.py",
     "find": "                 paginate=False)\n",
     "replace": "                 paginate=True)\n",
     "matches": 1},
    {"why": "v3866 (review) - the chip publishes no time-of-what, so the page cannot say which moment its age is",
     "file": "tv/task_board.py",
     "find": "            \"w\": _cut(d.get(\"atWhat\"), 12) if d.get(\"atWhat\") else None,\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3217 - the published board drops the derived phase",
     "file": "tv/task_board.py",
     "find": "            row[\"phase\"] = _chip(d) or {\"p\": \"unknown\", \"why\": \"this card was not derived\"}\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3217 - a derived why leaves the Mac unscrubbed",
     "file": "tv/task_board.py",
     "find": "            \"unknown\": [_cut(u, 20) for u in (d.get(\"unknown\") or [])[:4]], \"why\": _cut(d.get(\"why\"), 200)}\n",
     "replace": "            \"unknown\": [_cut(u, 20) for u in (d.get(\"unknown\") or [])[:4]], \"why\": d.get(\"why\")}\n",
     "matches": 1},
    {"why": "REG-3217 - the console derives the board and publishes it without the phases",
     "file": "tv/control_app.py",
     "find": "    b = _tb.board(cards, _tb.session_name(sid, _tasks_dir) or \"the task board\", now_ms, truth=truth)\n",
     "replace": "    b = _tb.board(cards, _tb.session_name(sid, _tasks_dir) or \"the task board\", now_ms)\n",
     "matches": 1},
    {"why": "REG-3217 - the lane publishes a board nobody derived",
     "file": "tv/control_app.py",
     "find": "            r = task_board_publish_once(_derive=task_truth_derive)\n",
     "replace": "            r = task_board_publish_once()\n",
     "matches": 1},
    {"why": "REG-3218 - the lane never writes the record the eagle reads",
     "file": "tv/control_app.py",
     "find": "            _TASK_BOARD.update(at=time.time(), why=r.get(\"why\"))\n            _task_truth_settle(r)\n",
     "replace": "            _TASK_BOARD.update(at=time.time(), why=r.get(\"why\"))\n",
     "matches": 1},
    {"why": "REG-3218 - a PC that does not hold the board reads as one that derives it",
     "file": "tv/control_app.py",
     "find": "        _TASK_TRUTH.update(on=(None if \"UNKNOWN\" in why else False), owed=None, drift=None, first=None, say=why[:200])\n",
     "replace": "        _TASK_TRUTH.update(on=True, owed=None, drift=None, first=None, say=why[:200])\n",
     "matches": 1},
    {"why": "REG-3218 - the eagle row reads a disagreeing board as clear",
     "file": "tv/console_doctor.py",
     "find": "    if owed:\n        kinds = rec.get(\"drift\") or {}\n",
     "replace": "    if False:\n        kinds = rec.get(\"drift\") or {}\n",
     "matches": 1},
    {"why": "REG-3218 - a stale record reads as an agreeing board",
     "file": "tv/console_doctor.py",
     "find": "    if age > _BOARD_TRUTH_STALE_MS:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3218 - the eagle never asks",
     "file": "tv/console_doctor.py",
     "find": "    (\"the board agrees with the tree\", _check_the_board_agrees_with_the_tree),\n",
     "replace": "",
     "matches": 1},
    {"why": "v3866 (review) - the page never draws which comment made a card looked",
     "file": "tv/tasks_board.html",
     "find": "    if (p && p.look) words += ' \u00b7 GrokBot #230 comment ' + p.look;\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3217 - the page never draws the derived phase",
     "file": "tv/tasks_board.html",
     "find": "    if (c.phase) li.appendChild(chip(c.phase));\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
