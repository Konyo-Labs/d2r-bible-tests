# -*- coding: utf-8 -*-
"""v3898 (card #204, GrokBot's v3896 look 11-11) - A SHELF CLOSED WHILE IT IS STILL OPENING TAKES THE THEATRE WITH IT.

GrokBot, #230 6794132259: "pressing ✕ on the SHELF while it still says 'opening the shelf…' leaves a stuck 'THEATRE · SESSION 1
· PAST REPLAY' panel". It stayed on his Mac: at 13:4x IL the live-panel gate read "theatre OPEN AND CARRYING NO FILM" and
v3897's pre-flight went red on it until the panel was closed.

THE CAUSE: when THE SHELF opens the theatre as its door, the door handler sets TH.shelfIsDoor only after `await thOpen()`
returns. Every exit - the shelf's ✕, Escape (thEscUnwind), a click on the backdrop, the toggle - asks _thShelfWasTheDoor()
whether to close the theatre too, and during the wait it said no: the shelf hid and the empty stage stayed. The handler
already marks that wait (TH.shelfOpening: set before thOpen, cleared in its finally), so the rule now counts it.

DRIVEN: the SHIPPED _thShelfWasTheDoor, cut from tv/control_ui.html and run in node against each state; and each exit is
checked, by its own code, to ask that one rule. RED_PROOF below. [[the-unjoined-end]]
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import js_strip  # noqa: E402  (one comment stripper for the laws)
from cb_node_harness import NODE  # noqa: E402


def _ui():
    with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
        return fh.read()


def _function(src, name):
    """the shipped function's own text, from its declaration to the first two-space closing brace (bounded, never a guess)"""
    head = "  function %s(" % name
    assert src.count(head) == 1, "PREMISE: %s is declared %d times" % (name, src.count(head))
    i = src.index(head)
    j = src.index("\n  }\n", i)
    return src[i:j + 4]


def _run(states):
    if NODE is None:
        raise AssertionError("node is not installed on this PC - this law runs the shipped rule in node and does not skip")
    fn = _function(_ui(), "_thShelfWasTheDoor")
    prog = ("var TH = {};\n%s\nvar out = [];\n"
            "JSON.parse(process.argv[2]).forEach(function (s) { TH = s; out.push(_thShelfWasTheDoor()); });\n"
            "console.log(JSON.stringify(out));\n" % fn)
    d = tempfile.mkdtemp(prefix="shelf_door_")
    try:
        h = os.path.join(d, "h.js")
        with io.open(h, "w", encoding="utf-8") as fh:
            fh.write(prog)
        r = subprocess.run([NODE, h, json.dumps(states)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    finally:
        shutil.rmtree(d, True)
    if r.returncode != 0:
        raise AssertionError("node failed: %s" % r.stderr.decode("utf-8", "replace")[-800:])
    return json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])


class AShelfClosedWhileOpeningTakesTheStageWithIt(unittest.TestCase):

    def test_an_opening_door_is_the_door(self):
        """* THE POINT - ✕ / Escape during 'opening the shelf…' closes the theatre too"""
        self.assertEqual(_run([{"shelfIsDoor": False, "shelfOpening": True}]), [True],
                         "a shelf closed while still opening hid itself and left the empty theatre stage open")

    def test_the_rule_still_tells_a_door_from_a_shelf_over_a_reel(self):
        """BASELINE - a shelf opened over a reel he picked is not the door: closing it returns to the reel"""
        self.assertEqual(_run([{"shelfIsDoor": False, "shelfOpening": False}, {"shelfIsDoor": True, "shelfOpening": False},
                               {}]), [False, True, False])

    def test_every_exit_asks_the_one_rule(self):
        code = js_strip.strip_js_comments(_ui())
        for fn, call in (("thEscUnwind", "if (_thShelfWasTheDoor()) thClose();"),
                         ("thShelfToggle", "if (ov && !ov.hidden && _thShelfWasTheDoor()) {")):
            body = _function(code, fn)
            self.assertIn(call, body, "%s no longer asks _thShelfWasTheDoor - that exit can strand the stage" % fn)
        self.assertEqual(len(re.findall(r"if \(_thShelfWasTheDoor\(\)\) \{ try \{ thClose\(\); \} catch\(_e\)\{\} \}", code)), 1,
                         "the shelf's ✕ / backdrop dismiss no longer closes the theatre when the shelf was the door")

    def test_the_door_handler_marks_the_wait_and_always_clears_it(self):
        code = js_strip.strip_js_comments(_ui())
        self.assertEqual(code.count("try { TH.shelfOpening = true; } catch (e) {}"), 1,
                         "PREMISE: the door no longer marks its in-flight open")
        i = code.index("try { TH.shelfOpening = true; } catch (e) {}")
        rest = code[i:i + 12000]
        self.assertIn("} finally {\n      try { TH.shelfOpening = false; } catch (e) {}", rest,
                      "the in-flight mark is not cleared in a finally - a later shelf over a reel would close the reel's stage")


RED_PROOF = [
    {"why": "v3898 (#204) - a shelf closed while still opening leaves the empty theatre stage open again (GrokBot 11-11)",
     "file": "tv/control_ui.html",
     "find": "    try { return !!(TH.shelfIsDoor || TH.shelfOpening); } catch (e) { return false; }\n",
     "replace": "    try { return !!TH.shelfIsDoor; } catch (e) { return false; }\n",
     "matches": 1, "needs": "node"},
    {"why": "v3898 (#204) - the rule calls every shelf the door, so closing a shelf over his reel closes the reel too",
     "file": "tv/control_ui.html",
     "find": "    try { return !!(TH.shelfIsDoor || TH.shelfOpening); } catch (e) { return false; }\n",
     "replace": "    try { return true; } catch (e) { return false; }\n",
     "matches": 1, "needs": "node"},
    {"why": "v3898 (#204) - Escape stops asking the rule and strands the stage",
     "file": "tv/control_ui.html",
     "find": "      if (_thShelfWasTheDoor()) thClose();\n",
     "replace": "      if (false) thClose();\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
