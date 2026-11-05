# -*- coding: utf-8 -*-
"""v3865 (REG-3217, REG-3218) - THE TASK BOARD IS DERIVED FROM THE EVIDENCE, LIKE BLUEPRINT AND HEART.

His words, 2026-11-05: "make sure its derived always console and you and the taskboard synced.. so we are always with our
finger on the trigger and know whats still being worked on and not shipped". MEASURED that evening: the board (the task
panel's cards, published by control_app.task_board_publish_once to /d2r/tasks.html) had not been touched for 6 hours while
the work moved - 25 cards said in_progress, several describing work shipped days earlier ("v3862 ship", REG-3155's proof
bank, REG-3157's ship_when_green), none naming the fleet that was running. Nothing compared a card with the tree.

REG-3217 - every card carries a DERIVED phase (tv/task_truth.py): its keys (REG ids, ranges expanded; a version LEADING the
subject; branch names) resolved against git - no-evidence | building | graded (ci/ only) | shipped vN | live vN (the
published stamp >= N) | looked (GrokBot on #230, after the ship) | third-eyed (#231 / the Grok CLI seat) - each with its
evidence. A look is about the versions on its first line that names one, never its evidence list. A tree that would not
answer is UNKNOWN, never no-evidence; an unread lane is UNKNOWN, never "not looked".
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
         "body": "Seat: Grok Bot (visual eyes)\n\nREG-100 is still broken on his screen"},          # before REG-100 shipped
        {"id": 1002, "created_at": _iso(T0 - 7 * DAY), "updated_at": _iso(T0 - 7 * DAY),
         "body": "Seat: Grok Bot (visual eyes)\n\n# v3801 ship check\n\nEvidence: changelog-v3800-01.json, shots/"},
        {"id": 1003, "created_at": _iso(T0 - 7 * DAY), "updated_at": _iso(T0 - 7 * DAY),
         "body": "Seat: Claude (coder) -> GrokBot\n\nACT verify REG-100 and v3800 on glass"},          # not a look
        {"id": 1004, "created_at": _iso(T0 - 6 * DAY), "updated_at": _iso(T0 - 6 * DAY),
         "body": "Seat: Grok CLI (third eye)\n\nSAW: origin/main stamp v3801, the crops stay with Grok Bot"},
    ],
    231: [
        {"id": 2001, "created_at": _iso(T0 - 6 * DAY), "updated_at": _iso(T0 - 6 * DAY),
         "body": "SECOND-EYE\nversion: v3801\nverdict: findings\nmodel: grok-4.7"},
    ],
}


class FakeGitHub(object):
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def __call__(self, api_path):
        self.calls.append(api_path)
        if self.fail:
            raise RuntimeError("gh exited 1: could not resolve host")
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
        self.assertEqual(got["REG-101"]["at"], T0 - 9 * DAY)

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
        self.assertEqual(len(gh.calls), 2)
        self.assertIn("&since=", gh.calls[0])
        idx = self.idx()
        r101 = TT.resolve_key("REG-101", idx, "v3801", looks)
        self.assertEqual((r101["phase"], r101["look"]["id"], r101["third"]["id"]), ("third-eyed", "1002", "1004"))
        r100 = TT.resolve_key("REG-100", idx, "v3801", looks)
        self.assertEqual(r100["phase"], "live",
                         "a look before the ship, or a look whose EVIDENCE named v3800, counted as a look at REG-100")
        self.assertIsNone(r100["look"])

    def test_github_is_asked_at_most_every_ten_minutes(self):
        _l, gh, p = self.looks()
        TT.refresh_looks(p, T0 + 5 * 60 * 1000, gh)
        self.assertEqual(len(gh.calls), 2, "GitHub was asked again inside 10 minutes")
        TT.refresh_looks(p, T0 + TT.LOOKS_EVERY_MS, gh)
        self.assertEqual(len(gh.calls), 4)

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
        return TT.derive(cards, self.idx(), None, looks, T0)

    def test_each_kind_of_drift_with_its_reason(self):
        cards = [_card(1, "in_progress", "REG-101 the second fix"),
                 _card(2, "completed", "REG-104 the building one"),
                 _card(3, "completed", "Shelf questions answered - no change"),
                 _card(4, "pending", "REG-103 the graded one"),
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
        self.assertIn("comment 1002", t["byCard"]["1"]["drift"]["say"], "ready to close does not name the look")
        self.assertIn("REG-104 building", t["byCard"]["2"]["drift"]["say"])
        self.assertEqual(t["byCard"]["9"]["phase"], "building",
                         "a fix still building in the description let an old shipped key read ready to close")
        self.assertEqual(t["summary"]["owed"], 4)
        self.assertEqual(t["summary"]["first"][0]["kind"], "closed-never-shipped", "the red flag is not named first")

    def test_a_description_key_says_it_is_one(self):
        t = self._derive([_card(1, "pending", "Fleet chip: the repair book", "lives on claude/v3804")])
        self.assertEqual(t["byCard"]["1"]["drift"]["kind"], "work-started")
        self.assertIn("keyed on its description", t["byCard"]["1"]["drift"]["say"])


class TheBoardCarriesItScrubbed(Fixture):

    def test_each_card_wears_its_phase_and_flag_and_the_record_counts_them(self):
        looks, _gh, _p = self.looks()
        cards = [_card(1, "in_progress", "REG-101 the second fix"), _card(2, "completed", "REG-104 the building one")]
        t = TT.derive(cards, self.idx(), None, looks, T0)
        b = TB.board(cards, "t", T0, truth=t)
        ph = dict((r["id"], ((r.get("phase") or {}).get("p"), (r.get("phase") or {}).get("v"),
                             (r.get("drift") or {}).get("kind"))) for r in b["cards"])
        self.assertEqual(ph, {"1": ("third-eyed", "v3801", "ready-to-close"), "2": ("building", None, "closed-never-shipped")})
        self.assertEqual((b["truth"]["owed"], b["truth"]["drift"]["ready-to-close"], b["truth"]["publishedVer"]), (2, 1, "v3801"))
        later = TB.board(cards, "t", T0 + 60 * 1000, truth=TT.derive(cards, self.idx(), None, looks, T0 + 60 * 1000))
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
            with io.open(os.path.join(self.d, "session-x", "%s.json" % c["id"]), "w", encoding="utf-8") as fh:
                json.dump(c, fh)
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
        self.assertIn("foot-tasks", CD._board_tree_verdict(off, T0)[1])
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
                       "    var words = ph === 'unknown' ? 'phase UNKNOWN' : ph"):
            self.assertEqual(script.count(needle), 1, "the page no longer draws: %r" % needle)
        self.assertIn('<span id="tb-truth"></span>', page)
        self.assertNotIn("innerHTML", script)


RED_PROOF = [
    {"why": "REG-3217 - a REG range on a card (REG-3193..3195) keys only its first id",
     "file": "tv/task_truth.py",
     "find": "            if lo < hi <= lo + RANGE_MAX:\n                got += list(range(lo + 1, hi + 1))\n",
     "replace": "            if lo < hi <= lo + RANGE_MAX:\n                pass\n",
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
     "find": "    if pv < nv:\n        out[\"why\"] = \"on origin/main, the published version is still %s\" % published\n        return out\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3217 - an unstamped main commit loses the version it shipped in",
     "file": "tv/task_truth.py",
     "find": "        main_ver[sha] = lv or cur\n",
     "replace": "        main_ver[sha] = lv\n",
     "matches": 1},
    {"why": "REG-3217 - a GrokBot comment from BEFORE the ship counts as a look at it",
     "file": "tv/task_truth.py",
     "find": "    look = _first_look(looks, \"grokbot\", key, ver, at or 0) if known.get(\"grokbot\") else None\n",
     "replace": "    look = _first_look(looks, \"grokbot\", key, ver, 0) if known.get(\"grokbot\") else None\n",
     "matches": 1},
    {"why": "REG-3217 - a version in a look's evidence list counts as a look at that version (measured: 30 of 84 cards)",
     "file": "tv/task_truth.py",
     "find": "    for line in str(body or \"\")[:LOOK_HEAD_CHARS].splitlines():\n        got = versions_in(line)\n        if got:\n            return got[:12]\n    return []\n",
     "replace": "    return versions_in(str(body or \"\")[:LOOK_HEAD_CHARS])[:12]\n",
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
     "find": "                if RANK[m[\"phase\"]] < RANK[lo[\"phase\"]]:\n",
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
     "find": "    elif RANK[ph] >= RANK[\"third-eyed\"]:\n",
     "replace": "    elif RANK[ph] >= RANK[\"live\"]:\n",
     "matches": 1},
    {"why": "REG-3218 - a pending card with commits is not flagged",
     "file": "tv/task_truth.py",
     "find": "    elif status == \"pending\" and RANK[hi] >= RANK[\"building\"]:\n",
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
    {"why": "REG-3217 - the page never draws the derived phase",
     "file": "tv/tasks_board.html",
     "find": "    if (c.phase) li.appendChild(chip(c.phase));\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
