# -*- coding: utf-8 -*-
"""#196 — ci_sim printed "could not be read" and then exited 0 about it.

`unread` was reported above the verdict and ignored by EVERY return: exit 1 on failures, exit 3 on
platform facts, else exit 0 — "no KNOWN host dependency in N test(s)". So a suite whose unreadable
tests all passed produced a clean verdict about work the tool never examined.

⚠ A method added on the class at RUNTIME is unreadable by construction: defining() finds it,
inspect.getfile names the class file, and _source_index only stores FunctionDef nodes that appear
in the class BODY — the AST never had it. So this is reachable, not theoretical.
"""
import ast
import inspect
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import ci_sim  # noqa: E402


def _main_code():
    src = inspect.getsource(ci_sim.main)
    t = ast.parse(src.lstrip())
    fn = t.body[0]
    if (fn.body and isinstance(fn.body[0], ast.Expr)
            and isinstance(getattr(fn.body[0], "value", None), ast.Constant)):
        fn.body = fn.body[1:]
    return ast.unparse(fn)


class _AlwaysPasses(unittest.TestCase):
    """A trivial, loadable subject for driving ci_sim.main.

    ⚠ IT MUST NOT BE THE CLASS THAT CONTAINS THE DRIVER. Pointing main() at that class makes it
    load and run the driving test, which calls main() again — MEASURED: rc=1 out of the recursion
    rather than out of the verdict, and the case failed for a reason that had nothing to do with
    the law. A driver must not be its own subject.
    """

    def test_ok(self):
        pass


class AnUnreadTestIsNotACleanVerdict(unittest.TestCase):

    def test_unread_alone_DRIVES_the_exit_code_and_does_not_exit_0(self):
        """⚠⚠ THIS IS DRIVEN, NOT READ, AND THE FIRST CUT WAS READ.

        The first version walked the AST for an `if` mentioning `unread` that CONTAINED a Return.
        Reverting the guard to `if plat:` left that Return node present but UNREACHABLE (its test
        is `unread and not plat`, which cannot hold inside `if plat`), and the case stayed GREEN
        through the exact defect it is named for. A presence-law is not a reachability-law.
        [[source-reading-guard]] §4c cause 2
        """
        # ⚠ main() applies real stubs, chdirs and imports test_control before it ever reaches the
        # verdict; unstubbed it returns 2 ("stub(s) could not bind") and would have "passed" this
        # case for the wrong reason. Neutralise exactly the preamble, then let the REAL verdict
        # logic run. [[feedback-suspect-the-instrument]]
        real = {k: getattr(ci_sim, k) for k in
                ("apply_stubs", "apply_path_stubs", "_platform_dependent", "_load_failures")}
        try:
            ci_sim.apply_stubs = lambda: []
            ci_sim.apply_path_stubs = lambda: []
            ci_sim._load_failures = lambda _s: []
            # nothing platform-dependent, but ONE test the tool could not read
            ci_sim._platform_dependent = lambda _s: ([], ["_AlwaysPasses.test_unreadable"])
            rc = ci_sim.main(["_AlwaysPasses"])
        finally:
            for k, v in real.items():
                setattr(ci_sim, k, v)
        self.assertNotEqual(rc, 0,
                            "a suite with an UNREADABLE test exited 0 — a clean verdict about "
                            "work this tool never examined. A skip is not a pass.")
        self.assertEqual(rc, 3,
                         "unread did not land in the tool's UNKNOWN answer (exit 3); got %r" % rc)

    def test_the_UNKNOWN_verdict_is_exit_3_and_not_exit_0(self):
        """It must land in the tool's existing UNKNOWN answer, not invent a green one."""
        code = _main_code()
        for node in ast.walk(ast.parse(code)):
            if isinstance(node, ast.If) and "unread" in ast.unparse(node.test):
                rets = [n for n in ast.walk(node)
                        if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)]
                if rets:
                    vals = {r.value.value for r in rets}
                    self.assertNotIn(0, vals,
                                     "an unread-guarded branch returns 0 — that is the green "
                                     "verdict this task exists to stop: %s" % vals)
                    self.assertIn(3, vals,
                                  "unread does not land in the tool's UNKNOWN answer (exit 3): %s"
                                  % vals)
                    return
        self.fail("no unread-guarded branch returns a constant at all")

    def test_the_two_UNKNOWN_reasons_stay_NAMED_apart(self):
        """A platform fact and an unreadable source are both UNKNOWN and need different action."""
        code = _main_code()
        self.assertIn("COULD NOT BE READ", code,
                      "the unread reason is no longer said in its own words, so a reader cannot "
                      "tell it from a platform-fact UNKNOWN")
        self.assertIn("PLATFORM FACT", code)

RED_PROOF = [
    {"why": "#196 - the unread guard can no longer be reached, so a suite whose unreadable tests passed exits 0",
     "file": "tv/ci_sim.py",
     "find": "    if plat or unread:\n        if unread and not plat:\n",
     "replace": "    if plat:\n        if unread and not plat:\n",
     "matches": 1},
    {"why": "#196 - the unread-only verdict returns 0, a clean verdict about work the tool never examined",
     "file": "tv/ci_sim.py",
     "find": "            print(\"   Exit 3 is UNKNOWN, not failure.\")\n            return 3\n",
     "replace": "            print(\"   Exit 3 is UNKNOWN, not failure.\")\n            return 0\n",
     "matches": 1},
    {"why": "the unreadable-source UNKNOWN is said in platform-fact words, so a reader cannot tell which action it needs",
     "file": "tv/ci_sim.py",
     "find": "                  \"COULD NOT BE READ\" % (r.testsRun, len(unread)))\n            print(\"   for platform facts at all, so this tool examined only the rest. A skip is \"\n                  \"not a pass.\")\n            for _u in list(unread)[:12]:\n                print(\"     \\u26aa %s\" % str(_u)[:70])\n            if len(unread) > 12:\n                print(\"     \\u26aa … and %d more\" % (len(unread) - 12))\n            print(\"   Exit 3 is UNKNOWN, not failure.\")\n            return 3\n        if unread:\n            print(\"\\u26aa %d test(s) COULD NOT BE READ, and are counted",
     "replace": "                  \"turn on a PLATFORM FACT\" % (r.testsRun, len(unread)))\n            print(\"   for platform facts at all, so this tool examined only the rest. A skip is \"\n                  \"not a pass.\")\n            for _u in list(unread)[:12]:\n                print(\"     \\u26aa %s\" % str(_u)[:70])\n            if len(unread) > 12:\n                print(\"     \\u26aa … and %d more\" % (len(unread) - 12))\n            print(\"   Exit 3 is UNKNOWN, not failure.\")\n            return 3\n        if unread:\n            print(\"\\u26aa %d test(s) turn on a PLATFORM FACT, and are counted",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
