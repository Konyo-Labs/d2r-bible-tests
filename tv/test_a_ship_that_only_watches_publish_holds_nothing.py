# -*- coding: utf-8 -*-
"""v3898 (card #206) - A SHIP THAT ONLY WATCHES PUBLISH HOLDS NOTHING ON THIS PC.

MEASURED 11-11 by GrokBot on his Mac (#230): at 12:43, 12:48 and 13:01 IL the console's proof import read "a push is
grading on this PC - the proof import waits for it" while v3896's ship was past its main push and only polling GitHub's
Publish - an hour on a slow Publish, with nothing grading here. v3896 (REG-3678, card #200 guard 9) counts a ship like a
push for its WHOLE run, because its readiness, its rehearsal beside the CI wait and its main push's hook all grade on this
Mac. After main none of that runs.

So the ship says when it is only watching: watch_publish writes a marker naming its pid in git's common dir (one file every
checkout and worktree of this PC reads; never a tracked byte) and removes it when the watch ends, however it ends.
push_grading skips a SHIP whose pid the marker names - never a hook, never another ship. An absent or unreadable marker
leaves every ship counted, which can only hold a proof longer, never run one beside a real grade.

DRIVEN: push_grading on fixture process tables; watch_publish with a fake GitHub on a temp marker path; the two callers by
their syntax tree (the console's push check and the ship's call). RED_PROOF below. [[the-unjoined-end]] [[heart-first]]
"""
import ast
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
import self_prove as SP  # noqa: E402
import ship_when_green as S  # noqa: E402

PUBLISH = getattr(S, "PUBLISH", "Publish")
SHIP = ("901", "500", 900, "/Library/Python.app/Contents/MacOS/Python -u tv/ship_when_green.py v9999")
HOOK = ("802", "500", 300, "/bin/bash hooks/pre-push origin git@github.com:o/r.git")


def _table(*extra):
    base = [("1", "0", 999999, "/sbin/launchd"),
            ("500", "1", 50000, "/bin/zsh -l"),
            ("700", "1", 40000, "/usr/bin/python3 tv/control_app.py --open")]
    return base + list(extra)


class AShipThatOnlyWatchesPublishHoldsNothing(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tvd_ship_phase_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.path = os.path.join(self.tmp, SP.SHIP_PHASE_FILE)

    def test_a_watching_ship_holds_no_proof(self):
        """* THE POINT - and its baseline: the same ship, unmarked, still holds the proof (REG-3678 stands)"""
        self.assertIs(SP.push_grading(_table(SHIP))[0], True, "PREMISE: a ship no longer holds the proof at all")
        self.assertIs(SP.push_grading(_table(SHIP), watching={"901"})[0], False,
                      "a ship that only watches Publish still holds the proof and the proof import")

    def test_the_marker_excuses_only_the_ship_it_names(self):
        self.assertIs(SP.push_grading(_table(SHIP), watching={"777"})[0], True, "a marker for another pid excused this ship")
        self.assertIs(SP.push_grading(_table(SHIP, HOOK), watching={"901"})[0], True,
                      "a pre-push grading beside a watching ship was excused with it")
        self.assertIs(SP.push_grading(_table(HOOK), watching={"802"})[0], True, "a marker excused a HOOK, which grades here")

    def test_the_watch_writes_the_marker_and_clears_it(self):
        seen = []

        def watch(sha):
            seen.append(SP.ships_only_watching(self.path))
            return {"worked": True, "runs": [{"name": PUBLISH, "status": "completed", "conclusion": "success",
                                              "minutes": 40}]}
        said = []
        code = S.watch_publish("a" * 40, watch, lambda s: None, lambda: 0.0, said.append, 600, phase_path=self.path)
        self.assertEqual(code, 0, "PREMISE: the fake Publish did not read as green: %s" % said[-3:])
        self.assertEqual(seen, [{str(os.getpid())}], "while it watched, the ship's marker did not name it")
        self.assertFalse(os.path.exists(self.path), "the marker outlived the watch - the next ship would be excused")

    def test_the_marker_is_cleared_when_the_watch_fails(self):
        def watch(sha):
            raise RuntimeError("GitHub went away")
        with self.assertRaises(RuntimeError):
            S.watch_publish("b" * 40, watch, lambda s: None, lambda: 0.0, lambda m: None, 600, phase_path=self.path)
        self.assertFalse(os.path.exists(self.path), "a watch that raised left its marker behind")

    def test_a_marker_is_cleared_only_by_its_own_ship(self):
        self.assertTrue(SP.mark_ship_watching(self.path, pid="4242", sha="c" * 40))
        self.assertEqual(SP.ships_only_watching(self.path), {"4242"})
        self.assertFalse(SP.clear_ship_watching(self.path, pid="4243"), "another ship cleared this ship's marker")
        self.assertTrue(os.path.exists(self.path), "another ship's clear removed the marker")
        self.assertTrue(SP.clear_ship_watching(self.path, pid="4242"))

    def test_an_absent_or_broken_marker_excuses_nobody(self):
        self.assertEqual(SP.ships_only_watching(self.path), set(), "an absent marker excused a ship")
        with io.open(self.path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertEqual(SP.ships_only_watching(self.path), set(), "a broken marker excused a ship")
        with io.open(self.path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"pid": "901", "phase": "grading"}))
        self.assertEqual(SP.ships_only_watching(self.path), set(), "a ship in another phase was excused")

    def test_the_marker_lives_in_gits_common_dir(self):
        import heart2 as _h2
        d, why = _h2._git_common_dir(ROOT)
        if not d:
            self.skipTest("UNMEASURED: this checkout has no git common dir (%s)" % why)
        self.assertEqual(SP.ship_phase_path(ROOT), os.path.join(d, SP.SHIP_PHASE_FILE),
                         "the marker is not where every checkout of this PC reads it")


def _call_kw(path, fn_name, callee):
    """-> {keyword: ast node} of the call to `callee` inside function `fn_name` of `path` (the syntax, never the prose)."""
    with io.open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.name == fn_name:
            for node in ast.walk(fn):
                if isinstance(node, ast.Call):
                    f = node.func
                    name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
                    if name == callee:
                        return {k.arg: k.value for k in node.keywords}
    return None


def _calls(node, name):
    return any(isinstance(n, ast.Call) and ((isinstance(n.func, ast.Attribute) and n.func.attr == name) or
                                            (isinstance(n.func, ast.Name) and n.func.id == name)) for n in ast.walk(node))


class BothEndsAreJoined(unittest.TestCase):
    """the ship writes the marker and the console reads it - each half alone does nothing (the unjoined end)"""

    def test_the_console_asks_with_the_marker(self):
        kw = _call_kw("tv/control_app.py", "_a_push_is_grading", "push_grading")
        self.assertIsNotNone(kw, "PREMISE: the console's push check no longer calls push_grading")
        self.assertIn("watching", kw, "the console's push check never reads the ship's marker")
        self.assertTrue(_calls(kw["watching"], "ships_only_watching") and _calls(kw["watching"], "ship_phase_path"),
                        "the console reads 'watching' from somewhere other than the ship's marker")

    def test_the_ship_watches_with_the_marker(self):
        kw = _call_kw("tv/ship_when_green.py", "ship", "watch_publish")
        self.assertIsNotNone(kw, "PREMISE: the ship no longer watches Publish")
        self.assertIn("phase_path", kw, "the ship watches Publish without saying it only watches")
        self.assertTrue(_calls(kw["phase_path"], "ship_phase_path"), "the ship's marker is not git's common-dir path")


RED_PROOF = [
    {"why": "v3898 (#206) - a ship that only watches Publish holds the proof and its import for the whole watch again",
     "file": "tv/self_prove.py",
     "find": "            if ship and pid in (watching or ()):\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "v3898 (#206) - the ship watches Publish without writing its marker",
     "file": "tv/ship_when_green.py",
     "find": "    _marked = _SP.mark_ship_watching(phase_path, sha=sha) if phase_path else False\n",
     "replace": "    _marked = False\n",
     "matches": 1},
    {"why": "v3898 (#206) - the marker outlives the watch, so the next ship is excused while it grades",
     "file": "tv/ship_when_green.py",
     "find": "            _SP.clear_ship_watching(phase_path)\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "v3898 (#206) - the marker reader excuses nobody (the console waits for the whole Publish again)",
     "file": "tv/self_prove.py",
     "find": "    return {str(d.get(\"pid\"))} if d.get(\"phase\") == SHIP_WATCHING and d.get(\"pid\") else set()\n",
     "replace": "    return set()\n",
     "matches": 1},
    {"why": "v3898 (#206) - any ship's clear removes another ship's marker",
     "file": "tv/self_prove.py",
     "find": "        if str(d.get(\"pid\")) != str(pid if pid is not None else os.getpid()):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "v3898 (#206) - the console asks push_grading without the ship's marker (the unjoined end)",
     "file": "tv/control_app.py",
     "find": "                                                  watching=_sp.ships_only_watching(_sp.ship_phase_path()))\n",
     "replace": "                                                  watching=None)\n",
     "matches": 1},
    {"why": "v3898 (#206) - the ship watches Publish with no marker path",
     "file": "tv/ship_when_green.py",
     "find": "                             phase_path=_SP.ship_phase_path(REPO),\n",   # v3900 REG-3736 re-anchor
     "replace": "                             phase_path=None,\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
