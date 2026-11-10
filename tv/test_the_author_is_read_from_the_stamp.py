# -*- coding: utf-8 -*-
"""The author of a version is the commit that stamped it, not a module constant.

AUTHOR_FAMILY was anthropic because Claude wrote every ship. Once the Grok code seat
stamps a version, two failures are the same bug:

  · a grok-cli look on that ship passes the gate (xai differs from the hardcoded
    anthropic), so the seat's own look counts as a second eye
  · a Claude look the recorder stored as model "claude" (it strips the parenthesis)
    is refused, because anthropic equals the hardcoded author

The stamp commit decides. A `Seat: Grok CLI (code)` or `Seat: Grok Bot (code)` line means the author family is xai.
A look counts only when its family differs from that.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import second_eye_ledger as L


class TestTheAuthorIsReadFromTheStamp(unittest.TestCase):

    def setUp(self):
        # REG-2360 - inside a git hook GIT_DIR points at the REAL repo and beats cwd=, so this fixture's
        # `git init` and commits landed on his push branch. Dropped for THIS test only; addCleanup puts them back.
        _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith("GIT_")}
        self.addCleanup(os.environ.update, _gitenv)
        self.d = tempfile.mkdtemp(prefix="authorstamp_")
        self.led = os.path.join(self.d, ".second_eye.jsonl")
        self._live = L.LEDGER_PATH
        L.LEDGER_PATH = self.led
        self.repo = tempfile.mkdtemp(prefix="authorrepo_")
        os.makedirs(os.path.join(self.repo, "tv"))
        subprocess.check_call(["git", "init", "-q"], cwd=self.repo)
        subprocess.check_call(["git", "config", "core.autocrlf", "false"], cwd=self.repo)  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        self._repo0 = L._REPO
        L._REPO = self.repo
        L._AUTHOR_LOADED.pop(os.path.abspath(self.repo), None)

    def tearDown(self):
        L.LEDGER_PATH = self._live
        L._REPO = self._repo0
        L._AUTHOR_LOADED.pop(os.path.abspath(self.repo), None)
        shutil.rmtree(self.d, ignore_errors=True)
        shutil.rmtree(self.repo, ignore_errors=True)

    def _commit(self, ver, message, extra=None):
        ship = os.path.join(self.repo, "tv", "WINDOWS_SHIP.json")
        with io.open(ship, "w", encoding="utf-8") as fh:
            json.dump(dict({"ver": ver}, **(extra or {})), fh)
        subprocess.check_call(["git", "add", "tv/WINDOWS_SHIP.json"], cwd=self.repo)
        subprocess.check_call(
            ["git", "-c", "user.email=seat@example.com", "-c", "user.name=Seat",
             "commit", "-q", "-m", message], cwd=self.repo)
        L._AUTHOR_LOADED.pop(os.path.abspath(self.repo), None)
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.repo, text=True).strip()

    def test_a_claude_look_counts_and_a_grok_look_does_not_on_a_grok_stamp(self):
        """The recorder stores model claude, family anthropic. The parenthesis is gone.

        On a Grok stamp that row is the other family. A grok-cli row on the same
        stamp is the author, and it must not be what lets the version through.
        On a stamp with no seat line the old rule stands: grok counts, claude does not.
        """
        self.assertIsNone(
            L.family_of("claude (cross-family: the author seat was Grok CLI)"),
            "a model line that names both families stays unnamed")
        self.assertEqual(L.family_of("claude"), "anthropic")
        self.assertEqual(L.family_of("grok-cli"), "xai")
        claude_sha = self._commit("v0001", "v0001 claude seat")
        grok_sha = self._commit(
            "v0002", "v0002 each frame keeps its reason\n\nSeat: Grok CLI (code)\n")
        self.assertEqual(L.author_family("v0001"), "anthropic")
        self.assertEqual(L.author_family("v0002"), "xai")
        self.assertFalse(L._commit_is_grok_seat(grok_sha, "v0001", repo=self.repo))

        L.record("v0002", "claude", "clean", answer_head="the shared reason is gone",
                 reached=True, sha=grok_sha, path=self.led)
        self.assertFalse(L.owes_a_look("v0002", self.led),
                         "a Claude look on a Grok stamp is the second eye")
        alone = {a["version"]: a for a in L.audit(self.led)}["v0002"]
        self.assertEqual(alone["looks"], 1, "audit did not count the Claude look: %r" % alone)
        self.assertEqual(alone["author"], 0, "audit called the Claude look the author: %r" % alone)
        L.record("v0002", "grok-cli", "clean", answer_head="same seat looking at itself",
                 reached=True, sha=grok_sha, path=self.led)
        looked = L.looked_at("v0002", self.led)
        self.assertTrue(looked, "the Claude row must still count after the Grok row is filed")
        self.assertTrue(all(L.family_of(r.get("model")) != "xai" for r in looked),
                        "a Grok look on a Grok stamp counted: %r" % looked)
        audited = {a["version"]: a for a in L.audit(self.led)}["v0002"]
        self.assertEqual(audited["looks"], 1, "the Grok row was filed as a second eye: %r" % audited)
        self.assertEqual(audited["author"], 1, "the Grok row was not filed as the author: %r" % audited)

        L.record("v0001", "grok-cli", "clean", answer_head="grok looked at a claude ship",
                 reached=True, sha=claude_sha, path=self.led)
        self.assertFalse(L.owes_a_look("v0001", self.led))
        L.record("v0001", "claude", "clean", answer_head="claude looked at claude",
                 reached=True, sha=claude_sha, path=self.led)
        v1 = L.looked_at("v0001", self.led)
        self.assertTrue(any(L.family_of(r.get("model")) == "xai" for r in v1))
        self.assertFalse(any(L.family_of(r.get("model")) == "anthropic" for r in v1),
                         "Claude reviewing Claude counted: %r" % v1)


    def test_a_later_rewrite_of_the_same_stamp_line_keeps_the_original_author(self):
        """REG-2011 (the #231 eye on v3577) - the log is newest-first and the first commit seen to ADD a version kept it,
        so a later commit that rewrote the same "ver" line (a hand-fixed half-bump, a one-line stamp file edited for
        another field) took the authorship - and with it which family's look closes the version. The stamp is the
        OLDEST commit that added the version."""
        self._commit("v0002", "v0002 each frame keeps its reason\n\nSeat: Grok CLI (code)\n")
        self._commit("v0002", "fix: the note field of the v0002 stamp", extra={"note": "rewritten"})
        self.assertEqual(L.author_family("v0002"), "xai",
                         "a later rewrite of the stamp line took the Grok seat's authorship (REG-2011)")

    def test_a_grok_bot_stamp_is_the_grok_family_too(self):
        """v3807 was stamped `Seat: Grok Bot (code)` (Grok Bot's coder seat, #230 GB-L), and its only look was grok-cli.
        The ledger read only the CLI spelling, so that stamp fell back to anthropic and the author's own family passed
        as the second eye. Both Grok seats are xai. A message that only QUOTES the seat line inside a sentence decides
        nothing, because a comment about who wrote a ship is not the commit that stamped it."""
        bot_sha = self._commit("v0003", "v0003 the small slice\n\nSeat: Grok Bot (code)\n")
        self.assertEqual(L.author_family("v0003"), "xai", "a Grok Bot stamp was read as anthropic")
        self.assertTrue(L._commit_is_grok_seat(bot_sha, "v0003", repo=self.repo),
                        "the Grok Bot stamp is not a Grok code seat to the Claude-row check")
        L.record("v0003", "grok-cli", "clean", answer_head="the seat's own family looking",
                 reached=True, sha=bot_sha, path=self.led)
        self.assertTrue(L.owes_a_look("v0003", self.led), "a grok-cli look closed a Grok Bot ship")
        L.record("v0003", "claude", "findings", answer_head="the other family looking",
                 reached=True, sha=bot_sha, path=self.led)
        self.assertFalse(L.owes_a_look("v0003", self.led), "a Claude look on a Grok Bot ship did not count")

        prose_sha = self._commit(
            "v0004", "v0004 docs: the ledger reads `Seat: Grok Bot (code)` from the stamp\n")
        self.assertEqual(L.author_family("v0004"), "anthropic",
                         "a sentence quoting the seat line took the authorship")
        self.assertFalse(L._commit_is_grok_seat(prose_sha, "v0004", repo=self.repo))


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "REG-2011 - the newest commit that re-adds a stamp line takes its authorship again",
        "file": "tv/second_eye_ledger.py",
        "find": '    for part in reversed((log.stdout or "").split("COMMIT ")[1:]):\n',
        "replace": '    for part in (log.stdout or "").split("COMMIT ")[1:]:\n',
        "matches": 1,
    },
    {
        "why": "the author is hardcoded to anthropic again, so a Grok look on a Grok stamp "
               "counts as the other family and a Claude look on it is refused",
        "file": "tv/second_eye_ledger.py",
        "find": "        # The author is whoever stamped this version, not a module constant. A Claude\n"
                "        # look on a Grok seat is the other family. A Grok look on that same seat is not.\n"
                "        author = author_family(v)\n",
        "replace": "        # The author is whoever stamped this version, not a module constant. A Claude\n"
                   "        # look on a Grok seat is the other family. A Grok look on that same seat is not.\n"
                   "        author = AUTHOR_FAMILY\n",
        "matches": 1,
    },
    {
        "why": "audit counts a Claude look on a Grok stamp as the author, so the screen the "
               "refusal names says OWED while the gate says looked",
        "file": "tv/second_eye_ledger.py",
        "find": "        elif fam and fam == author:\n",
        "replace": "        elif fam == AUTHOR_FAMILY:\n",
        "matches": 1,
    },
    {
        "why": "only the Grok CLI spelling is a Grok seat again, so a Seat: Grok Bot (code) stamp reads anthropic "
               "and a grok-cli look closes it (v3807)",
        "file": "tv/second_eye_ledger.py",
        "find": '_GROK_SEAT_LINE = re.compile(r"^Seat: Grok (?:CLI|Bot) \\(code\\)[ \\t]*$", re.M)\n',
        "replace": '_GROK_SEAT_LINE = re.compile(r"^Seat: Grok CLI \\(code\\)[ \\t]*$", re.M)\n',
        "matches": 1,
    },
    {
        "why": "the seat line is matched anywhere in the message, so a sentence that quotes it takes the authorship",
        "file": "tv/second_eye_ledger.py",
        "find": '_GROK_SEAT_LINE = re.compile(r"^Seat: Grok (?:CLI|Bot) \\(code\\)[ \\t]*$", re.M)\n',
        "replace": '_GROK_SEAT_LINE = re.compile(r"Seat: Grok (?:CLI|Bot) \\(code\\)", re.M)\n',
        "matches": 1,
    },
    {
        "why": "the Claude-row check reads the CLI literal again, so a Grok Bot stamp is not a Grok seat there",
        "file": "tv/second_eye_ledger.py",
        "find": "        if msg.returncode != 0 or not _is_grok_seat_message(msg.stdout):\n",
        "replace": "        if msg.returncode != 0 or \"Seat: Grok CLI (code)\" not in (msg.stdout or \"\"):\n",
        "matches": 1,
    },
    {
        "why": "the stamp reader takes the CLI literal again, so a Grok Bot stamp falls back to anthropic",
        "file": "tv/second_eye_ledger.py",
        "find": "        out[ver] = \"xai\" if _is_grok_seat_message(msg) else AUTHOR_FAMILY\n",
        "replace": "        out[ver] = \"xai\" if \"Seat: Grok CLI (code)\" in msg else AUTHOR_FAMILY\n",
        "matches": 1,
    },
]
