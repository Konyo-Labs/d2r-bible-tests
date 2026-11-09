# -*- coding: utf-8 -*-
"""v3894 (#103, REG-3576) - AN UNRESOLVED FAILING CLASS DOES NOT CLOSE EVERY LOCK.

_net_case_guards treated src is None as close-all (`if src is None or _guards_lock`).
An unresolvable class is now skipped; only a class that actually guards the lock closes it.
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


class AnUnresolvedFailingClassDoesNotCloseEveryLock(unittest.TestCase):

    def test_a_missing_class_is_skipped(self):
        src = _read("tv/self_arming.py")
        i = src.index("def _net_case_guards")
        body = src[i:src.index("def _guards_lock", i)]
        self.assertIn("if src is None:", body)
        self.assertIn("continue", body)
        self.assertNotIn("if src is None or _guards_lock", body)


RED_PROOF = [
    {"why": "v3894 (#103, REG-3576) - an unresolvable class closes every lock again",
     "file": "tv/self_arming.py",
     "find": "        if src is None:\n            continue\n        if _guards_lock(src, lock, stems):\n            return True\n",
     "replace": "        if src is None or _guards_lock(src, lock, stems):\n            return True\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
