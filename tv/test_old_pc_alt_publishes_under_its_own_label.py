# -*- coding: utf-8 -*-
"""#27 (REG-3586) - OLD PC ALT PUBLISHES AS OLD PC ALT, NEVER UNDER Konyo · ALT'S LABEL.

His later ruling (#182 / v3890 REG-3507): the ALTs get separate names. The work ALT is
"Konyo · ALT" and the old ALT is "OLD PC ALT". A leftover sharesLabel of "Konyo · ALT" on the
old ALT's identity must not override a nickname that is already a label - that was how the old
ALT's 17 characters vanished into the work ALT's ring.

Held here: OLD PC ALT is a label; publish_owner("OLD PC ALT", "Konyo · ALT") stays "OLD PC ALT";
sharesLabel is only read for a name that is still no label; the console asks publish_owner.
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
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import roster_publish as RP  # noqa: E402


class OldPcAltPublishesUnderItsOwnLabel(unittest.TestCase):

    def test_old_pc_alt_is_its_own_label(self):
        self.assertIn("OLD PC ALT", RP.OWNERS)
        self.assertIn("Konyo · ALT", RP.OWNERS)
        self.assertEqual(RP.owner_of("OLD PC ALT"), "OLD PC ALT")
        with io.open(os.path.join(ROOT, "functions", "api", "roster.js"), encoding="utf-8") as fh:
            js = fh.read()
        self.assertIn('"OLD PC ALT"', js)

    def test_a_stale_share_does_not_override_the_label(self):
        self.assertEqual(RP.publish_owner("OLD PC ALT", "Konyo · ALT"), "OLD PC ALT")
        self.assertEqual(RP.publish_owner("OLD PC ALT", None), "OLD PC ALT")
        # a name that is still no label may share one
        self.assertEqual(RP.publish_owner("something-else", "Konyo · ALT"), "Konyo · ALT")
        self.assertEqual(RP.publish_owner("something-else", None), "something-else")

    def test_the_console_asks_publish_owner(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        fn = src.split("def _roster_claimed_name(", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("publish_owner(", fn, "the console no longer asks publish_owner for the roster label")
        self.assertNotIn("if name not in _rpl.OWNERS:", fn,
                         "the console still branches on OWNERS itself instead of publish_owner")


RED_PROOF = [
    {"why": "REG-3586 - a leftover sharesLabel overrides OLD PC ALT back onto Konyo · ALT",
     "file": "tv/roster_publish.py",
     "find": "    if name in OWNERS:\n        return name\n",
     "replace": "    if False and name in OWNERS:\n        return name\n",
     "matches": 1},
    {"why": "REG-3586 - the console no longer asks publish_owner",
     "file": "tv/control_app.py",
     "find": "        return _rpl.publish_owner(name, shares)\n",
     "replace": "        return name\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
