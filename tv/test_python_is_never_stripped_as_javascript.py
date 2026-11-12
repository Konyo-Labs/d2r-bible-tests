# -*- coding: utf-8 -*-
"""v3903 (REG-3796, #200) - PYTHON SOURCE IS NEVER STRIPPED WITH THE JAVASCRIPT COMMENT RULES.

frame_authority._executable_only dispatches on the path it is given, and two laws handed it Python with a bare ".js"
("the idiom for the comment-stripping branch"). That branch strips /* .. */ and // - never Python's # - so a slash-star in
a Python string or docstring opened a block that ran to the next star-slash. MEASURED 11-12 on the v3903 tree: through
".js", console_doctor.py kept 126 of its 254 defs (45% of the file gone) and control_app.py 1,238 of 1,279; v3902's
docstring "claude/*" hid relaunch_green_light_tick and turned test_relaunch_interlock red in pre-flight d. A NEGATIVE scan
over that text (test_a_lane_has_one_work_list: "no module walks OWED_BY") passed over code it could not see.

Now Python handed in with a bare JS extension is stripped as Python, and both laws pass their real path. Fixtures plus the
real tree's two files the measurement was taken on. RED_PROOF below.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
from frame_authority import _executable_only  # noqa: E402

DEFS = re.compile(r"^\s*def \w+\(", re.M)
PY = ('def lister():\n'
      '    """this repo\'s local claude/* branch names"""\n'
      '    return 1\n\n\n'
      'def hidden_until_the_next_close():\n'
      '    return "a later */ in a string"\n')


class PythonIsNeverStrippedAsJavaScript(unittest.TestCase):

    def test_baseline_a_real_script_still_loses_its_comment(self):
        out = _executable_only("<script>var a = 1; /* a real comment */ var b = 2;</script>", ".js")
        self.assertNotIn("a real comment", out, "PREMISE: the JavaScript branch no longer strips - the case cannot distinguish")
        self.assertIn("var b = 2", out)

    def test_a_slash_star_docstring_hides_no_code(self):
        """* THE POINT - v3902's docstring shape: the def after it survives a ".js" strip"""
        out = _executable_only(PY, ".js")
        self.assertIn("def hidden_until_the_next_close(", out, "a slash-star in a docstring ate the code after it")
        self.assertNotIn("claude/*", out, "the docstring - prose - was kept")

    def test_the_real_files_keep_every_def(self):
        """the measurement: through ".js" console_doctor.py lost 128 of 254 defs and control_app.py 41 of 1,279"""
        for name in ("console_doctor.py", "control_app.py"):
            with io.open(os.path.join(HERE, name), encoding="utf-8") as fh:
                src = fh.read()
            want = len(DEFS.findall(src))
            self.assertGreater(want, 100, "PREMISE: %s holds almost no defs - the case measures nothing" % name)
            self.assertEqual(len(DEFS.findall(_executable_only(src, ".js"))), want,
                             "%s lost defs to the JavaScript strip" % name)

    def test_the_two_laws_pass_their_real_path(self):
        for law in ("test_a_held_relaunch_gets_a_green_light.py", "test_a_lane_has_one_work_list.py"):
            with io.open(os.path.join(HERE, law), encoding="utf-8") as fh:
                code = _executable_only(fh.read(), os.path.join(HERE, law))
            self.assertNotIn('_executable_only(src, ".js")', code, "%s strips Python with the JavaScript rules" % law)
            self.assertIn("_executable_only(src, path)", code)


RED_PROOF = [
    {"why": "REG-3796 - Python handed in as a bare .js is stripped with the JavaScript rules again (45% of a file vanishes)",
     "file": "tv/frame_authority.py",
     "find": "    if path in (\".ts\", \".tsx\", \".js\"):\n        try:\n            import ast as _ast\n",
     "replace": "    if False:\n        try:\n            import ast as _ast\n",
     "matches": 1},
    {"why": "REG-3796 - the lane law scans production modules through the JavaScript strip again",
     "file": "tv/test_a_lane_has_one_work_list.py",
     "find": "            body = _executable_only(src, path)",
     "replace": "            body = _executable_only(src, \".js\")",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
