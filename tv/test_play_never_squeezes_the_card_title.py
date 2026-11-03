# -*- coding: utf-8 -*-
"""LAW (v3859): the per-card ▶ PLAY stacks in the Shelf card's control cluster; it never squeezes the title.
With PLAY beside the pin and seal the title lost ~50px: 'Jan 1 · 2:00 AM' was clipped at 375 and collapsed to
zero size at 1120x628 (render target shelf-cards red). Red-proof: on bb358e0e+cherry-picks the rule is absent
and shelf-cards renders clipped 62/190 at 1120x628."""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
SRC = open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()


class TheLaw(unittest.TestCase):
    def test_the_cluster_stacks(self):
        self.assertIn("  .shc-tr { position: relative; flex: none; z-index: 2; display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }", SRC)

    def test_play_still_lives_in_the_cluster(self):
        self.assertIn('<div class="shc-tr">\' + (sm.stub ? \'\' : \'<button type="button" class="shc-play"', SRC)


if __name__ == "__main__":
    unittest.main()
