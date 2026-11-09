# -*- coding: utf-8 -*-
"""v3894 (#103, REG-3575) - A GIANT LAW'S NAMELESS RED DOES NOT CLOSE EVERY LOCK.

_net_case_guards used to return True when a find named no case, so one red of
test_control closed every lock the file guards. A giant law (NET_NARROW_MIN_LOCKS
or more) now returns False for a nameless red; focused laws stay fail-closed.
RED_PROOF below.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()


def _read(rel):
    path = os.path.join(HERE, os.path.basename(rel)) if rel.startswith("tv/") else os.path.join(ROOT, rel)
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


class AGiantLawsNamelessRedDoesNotCloseEveryLock(unittest.TestCase):

    def test_a_nameless_red_of_a_giant_law_stays_open(self):
        src = _read("tv/self_arming.py")
        self.assertIn("if not cases:", src)
        self.assertIn("return n_locks < NET_NARROW_MIN_LOCKS", src)
        i = src.index("def _net_case_guards")
        body = src[i:src.index("def _guards_lock", i)]
        self.assertIn("return n_locks < NET_NARROW_MIN_LOCKS", body)
        self.assertNotIn("if not cases:\n        return True", body)


RED_PROOF = [
    {"why": "v3894 (#103, REG-3575) - a nameless red of a giant law closes every lock again",
     "file": "tv/self_arming.py",
     "find": "    if not cases:\n        return n_locks < NET_NARROW_MIN_LOCKS\n",
     "replace": "    if not cases:\n        return True\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
