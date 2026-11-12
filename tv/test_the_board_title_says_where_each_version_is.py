# -*- coding: utf-8 -*-
"""v3902 (REG-3781) - THE BOARD'S TITLE SAYS WHERE EACH VERSION IS, DERIVED BY THE CONSOLE, NEVER TYPED.

His 11-12 ~09:20, with a screenshot of the board: "the task list board still needs updating?" - it read "v3894 shipping (main
push 11-10 ~23:50)" while v3900 was LIVE, v3901 in its pre-flight and v3902 building. Then: "this should be the flow per
version you should update it" and "the console also for future should be updating to that section". The title was a hand-typed
name, true on the day it was typed. Now: the words before " ▸ " stay as written; after it the console writes, every tick,
task_board.version_line - what main ships, and each newer claude/vNNNN branch with its stage read off .git/ship_logs (LIVE,
on main, pushing main, on GitHub, ship stopped, pre-flight, pre-flight red/green, building). UNKNOWN main writes nothing.

DRIVEN: the real task_board.version_line / retitle over a fixture repo and names file, and the real control_app.board_retitle
with its seams (platform, label, branches, main) handed in. RED_PROOF below.
"""
import inspect
import io
import json
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
import task_board as TB  # noqa: E402

BRANCHES = ["claude/v3891", "claude/v3901", "claude/v3902", "claude/ship-system-on-v3894"]
BOARD = "session-387c905b"


class TheBoardTitleSaysWhereEachVersionIs(unittest.TestCase):

    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="tvd-board-title-law-")
        self.addCleanup(shutil.rmtree, self.repo, True)
        self.logs = os.path.join(self.repo, ".git", "ship_logs")
        os.makedirs(self.logs)
        self._log("ship_v3900.log", "ship: v3900 is on main\nship: Publish on e0513929e SUCCEEDED after 26 min\n")
        self._log("preflight_v3901_d.log", "preflight: 1763 law(s) here\npreflight: [12m] 1000 of 1661 laws\n")
        self.tasks = os.path.join(self.repo, "tasks")
        os.makedirs(os.path.join(self.tasks, BOARD))
        io.open(os.path.join(self.tasks, BOARD, "1.json"), "w", encoding="utf-8").write(
            json.dumps({"id": "1", "subject": "a card", "status": "pending"}))
        self.names = os.path.join(self.tasks, TB.NAMES_FILE)
        io.open(self.names, "w", encoding="utf-8").write(json.dumps({
            BOARD: "D2R — the board · ⭐ #200 ship in 1-2 attempts ▸ v3894 shipping (main push 11-10)",
            "session-other": "another board"}, ensure_ascii=False))

    def _log(self, name, text):
        io.open(os.path.join(self.logs, name), "w", encoding="utf-8").write(text)

    def _names(self):
        return json.load(io.open(self.names, encoding="utf-8"))

    def test_the_line_is_the_versions_as_they_stand(self):
        """* THE POINT - 11-12 09:20: the board said v3894 while v3900 was live"""
        self.assertEqual(TB.version_line(self.repo, "v3900", BRANCHES),
                         "v3900 LIVE · v3901 pre-flight · v3902 building")

    def test_each_stage_is_read_off_its_own_log(self):
        cases = (("ship: v3901 at x -> ci/claude-v3901\nship: both ci branches already point at x; reading GitHub's verdict\n",
                  "on GitHub"),
                 ("ship: GitHub vouches for x - pushing main\n", "pushing main"),
                 ("ship: GitHub graded x RED - main is NOT pushed: proof-keys shards\n", "ship stopped"))
        for text, want in cases:
            self._log("ship_v3901.log", text)
            self.assertEqual(TB.version_stage(3901, self.logs, 3900), want, text)
        os.remove(os.path.join(self.logs, "ship_v3901.log"))
        self._log("preflight_v3901_d.log", "preflight: GREEN recorded for abc1234\n")
        self.assertEqual(TB.version_stage(3901, self.logs, 3900), "pre-flight green")
        self._log("ship_v3900.log", "ship: v3900 is on main\n")
        self.assertEqual(TB.version_stage(3900, self.logs, 3900), "on main, publishing")

    def test_retitle_keeps_his_words_and_the_other_boards(self):
        changed, title = TB.retitle(BOARD, "v3900 LIVE · v3901 pre-flight", self.tasks)
        self.assertTrue(changed)
        self.assertEqual(title, "D2R — the board · ⭐ #200 ship in 1-2 attempts ▸ v3900 LIVE · v3901 pre-flight")
        self.assertEqual(self._names()[BOARD], title)
        self.assertEqual(self._names()["session-other"], "another board", "another board's title was touched")
        self.assertEqual(TB.retitle(BOARD, "v3900 LIVE · v3901 pre-flight", self.tasks)[0], False,
                         "an unchanged line was written again")

    def test_an_unknown_main_writes_nothing(self):
        before = io.open(self.names, encoding="utf-8").read()
        self.assertIsNone(TB.version_line(self.repo, None, BRANCHES))
        self.assertEqual(TB.retitle(BOARD, None, self.tasks), (False, None))
        self.assertEqual(io.open(self.names, encoding="utf-8").read(), before)

    def test_the_console_retitles_before_it_publishes(self):
        import control_app as CA
        lab = sorted(CA.ROSTER_APPROVERS)[0]
        real = CA.REPO
        CA.REPO = self.repo
        try:
            got = CA.board_retitle(_tasks_dir=self.tasks, _branches=BRANCHES, _main="v3900", _platform="darwin", _label=lab)
            self.assertTrue(got and got[0], got)
            self.assertIn("▸ v3900 LIVE · v3901 pre-flight · v3902 building", self._names()[BOARD])
            self.assertIsNone(CA.board_retitle(_tasks_dir=self.tasks, _branches=BRANCHES, _main="v3900", _platform="win32",
                                               _label=lab), "a PC that does not hold the board retitled it")
        finally:
            CA.REPO = real
        loop = inspect.getsource(CA._task_board_loop)
        code = "\n".join(l.split("#", 1)[0] for l in loop.split("\n"))
        self.assertLess(code.index("board_retitle()"), code.index("task_board_publish_once("),
                        "the loop publishes before the title knows the versions")


RED_PROOF = [
    {"why": "REG-3781 - the console's retitle throws away the words before the mark",
     "file": "tv/task_board.py",
     "find": "    hand = (old.split(VERSION_MARK, 1)[0]).strip() or \"the task board\"\n",
     "replace": "    hand = \"the task board\"\n",
     "matches": 1},
    {"why": "REG-3781 - the board loop stops retitling: the title says whatever version was typed last",
     "file": "tv/control_app.py",
     "find": "            board_retitle()            # REG-3781 - the title's version line first, so the publish below carries it\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "REG-3781 - the branches being built here are never named in the title",
     "file": "tv/task_board.py",
     "find": "    parts += [\"v%d %s\" % (n, version_stage(n, logs, main_n)) for n in newer[:VERSIONS_SHOWN]]\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
