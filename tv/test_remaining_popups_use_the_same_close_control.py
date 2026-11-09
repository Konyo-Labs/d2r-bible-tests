# -*- coding: utf-8 -*-
"""v3892 (#191, REG-3544) - REMAINING POPUP DISMISS BUTTONS WEAR THE SAME CLOSE CONTROL.

His rule: every popup uses one close control (gic-close-btn). MEASURED: unique cards and the
price-search exit already wear it; zone, super-unique, bind, aura, rune-source and boss detail
dismissals still used only `gbc-close`, and the in-game character window's Close button had no
class at all. Those dismissals now also wear `gic-close-btn`. The boss card's "scroll to full
filterable drop table" button stays a scroll control, not a close.
RED_PROOF below.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

BIBLE = os.path.join(ROOT, "bible.html")


def _src():
    with io.open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


class RemainingPopupsUseTheSameCloseControl(unittest.TestCase):

    def test_every_gbc_close_that_says_close_wears_the_shared_class(self):
        src = _src()
        buttons = re.findall(r'<button class="gbc-close[^"]*"[^>]*>[^<]*</button>', src)
        self.assertGreaterEqual(len(buttons), 6, "the gbc-close buttons vanished: %r" % buttons)
        close, scroll = [], []
        for b in buttons:
            if "scroll to full" in b:
                scroll.append(b)
            elif "close" in b.lower() or "✕" in b:
                close.append(b)
        self.assertEqual(len(scroll), 1, "the scroll-to-table button is not one scroll control: %r" % scroll)
        self.assertNotIn("gic-close-btn", scroll[0], "the scroll button was styled as a close")
        self.assertGreaterEqual(len(close), 6, "dismissals went missing: %r" % close)
        for b in close:
            self.assertIn("gic-close-btn", b, "a dismiss button is not the shared close: %s" % b)

    def test_the_character_window_close_wears_the_shared_class(self):
        src = _src()
        self.assertIn(
            """+ '<button type="button" class="gic-close-btn" data-act="close" onclick="window._chxClose()">Close</button></div>';""",
            src)


RED_PROOF = [
    {"why": "v3892 (#191, REG-3544) - the boss card's dismiss is gbc-close only again",
     "file": "bible.html",
     "find": '<button class="gbc-close gic-close-btn" onclick="clearActiveBoss()">✕ close</button>',
     "replace": '<button class="gbc-close" onclick="clearActiveBoss()">✕ close</button>',
     "matches": 1},
    {"why": "v3892 (#191, REG-3544) - the character window's Close has no shared class again",
     "file": "bible.html",
     "find": """+ '<button type="button" class="gic-close-btn" data-act="close" onclick="window._chxClose()">Close</button></div>';""",
     "replace": """+ '<button type="button" data-act="close" onclick="window._chxClose()">Close</button></div>';""",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
