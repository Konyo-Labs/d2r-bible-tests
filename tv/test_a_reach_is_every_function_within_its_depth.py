#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3899 (REG-3733) - A LANE'S REACH IS EVERY FUNCTION WITHIN ITS DEPTH, WHATEVER ORDER THE CALLS ARE WRITTEN IN.

MEASURED in v3899's pre-flight (11-11): test_a_lane_clears_only_what_it_declares went red - "tvd-shadow-watch declares a
function its reach no longer touches: ['_stop_capture']" - after v3899 added ONE call to shadow_watch_tick and removed none.
auto_scope.reachable_source walked depth-first with a plain visited set: stop_agent was first met at the bottom of a long
path, marked seen, and the shorter path met afterwards was never walked, so _stop_capture fell past the 3-hop bound and the
shadow watch's reach shrank from 80 functions to 68. The reach was decided by the order of the calls in the source, so a
lane's delete could hide from the declaration check the same way it disappeared here.

Now each function keeps the most depth it was reached with and is walked again when a shorter path arrives.

DRIVEN: the real reachable_source over a fixture module whose long path is written FIRST. RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import auto_scope as AS  # noqa: E402

FIXTURE = '''
def target():
    return 1

def leaf():
    return target()

def deep2():
    return leaf()

def deep1():
    return deep2()

def lane():
    deep1()          # the long path is written FIRST: lane -> deep1 -> deep2 -> leaf -> target (4 hops)
    return leaf()    # the short path afterwards: lane -> leaf -> target (2 hops)
'''


def _fixture_module():
    """a real module whose functions belong to it (__module__ matches), written to a file so inspect can read them"""
    import tempfile
    import importlib.util
    d = tempfile.mkdtemp(prefix="reachfx_")
    p = os.path.join(d, "reach_fixture_mod.py")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(FIXTURE)
    spec = importlib.util.spec_from_file_location("reach_fixture_mod", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["reach_fixture_mod"] = mod
    spec.loader.exec_module(mod)
    return mod, d


class AReachIsEveryFunctionWithinItsDepth(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod, cls.dir = _fixture_module()

    @classmethod
    def tearDownClass(cls):
        import shutil
        sys.modules.pop("reach_fixture_mod", None)
        shutil.rmtree(cls.dir, True)

    def test_a_short_path_met_after_a_long_one_still_counts(self):
        """* THE POINT - target is 2 hops away by the short path; a depth-3 reach must hold it"""
        _text, names, _why = AS.reachable_source(self.mod, "lane", depth=3)
        self.assertIn("target", names, "a function within the depth fell out of the reach because a longer path to its "
                                       "caller was written first: %s" % names)

    def test_baseline_a_function_past_the_depth_stays_out(self):
        """BASELINE - at depth 1 the reach is lane, deep1, leaf; target (2 hops) is not in it"""
        _text, names, _why = AS.reachable_source(self.mod, "lane", depth=1)
        self.assertEqual(sorted(names), ["deep1", "lane", "leaf"])

    def test_each_source_is_read_once(self):
        text, names, _why = AS.reachable_source(self.mod, "lane", depth=3)
        self.assertEqual(text.count("def leaf("), 1, "a function walked twice was read twice into the reach's text")


RED_PROOF = [
    {"why": "REG-3733 - the reach walk skips a function it has already seen, so a shorter path met later is dropped again "
            "(v3899: _stop_capture fell out of the shadow watch's reach)",
     "file": "tv/auto_scope.py",
     "find": "        if d < 0 or best.get(fname, -1) >= d:\n",
     "replace": "        if d < 0 or fname in seen:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
