"""v3843 - THE VERSION HISTORY. The console footer's history button opens one card per shipped version, newest first,
read from tv/CHANGELOG.json through /api/changelog. Every ship writes its own entry in the bump commit (bump_version.py
appends it beside the four version stamps), so the version this tree carries is always the top entry, and a ship that
forgot its entry fails here before it reaches the pre-push.
v3844 - the panel wears the console: the history button sits in one group with the era name (CHILIAD 843 · history),
a gold frame with an amber heading, symmetric cards (version gold, date dimmed, one bullet per change), and it closes
on ×, Esc or a click outside. Focus moves into the panel on open and back to the button on close (Elad, 2026-10-30)."""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable
enable()

ROOT = os.path.dirname(HERE)
NODE = shutil.which("node")


def _read(*p):
    with io.open(os.path.join(ROOT, *p), encoding="utf-8") as fh:
        return fh.read()


class TheBumpCarriesItsChangelogEntry(unittest.TestCase):
    def setUp(self):
        self.log = json.loads(_read("tv", "CHANGELOG.json"))
        self.ver = re.search(r'VERSION = "(v\d+(?:\.\d+)*)"', _read("tv", "tv_diablo.py")).group(1)

    def test_the_version_this_tree_carries_is_the_top_entry(self):
        self.assertIsInstance(self.log, list)
        self.assertTrue(self.log, "the changelog is empty")
        self.assertEqual(self.log[0]["ver"], self.ver,
                         "VERSION %s has no changelog entry on top - bump_version.py writes it in the bump commit" % self.ver)

    def test_each_entry_is_a_version_a_day_and_short_bullets_newest_first(self):
        nums = []
        for e in self.log:
            self.assertRegex(e["ver"], r"^v\d+$")
            self.assertRegex(e["date"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(e["items"], "%s lists nothing that shipped" % e["ver"])
            for it in e["items"]:
                self.assertIsInstance(it, str)
                self.assertTrue(it.strip())
                self.assertLessEqual(len(it), 120, "a bullet is prose, not one change: %r" % it)
            nums.append(int(e["ver"][1:]))
        self.assertEqual(nums, sorted(nums, reverse=True), "the history is not newest first")
        self.assertEqual(len(nums), len(set(nums)), "a version appears twice")
        self.assertIn("v3842", [e["ver"] for e in self.log], "the seed entry is gone")

    def test_bump_writes_the_entry_on_top_and_never_doubles_it(self):
        import bump_version
        log = bump_version.changelog_with([{"ver": "v1", "date": "2026-01-01", "items": ["a"]}], "v2",
                                          "first fix, second fix", date="2026-10-29")
        self.assertEqual(log[0], {"ver": "v2", "date": "2026-10-29", "items": ["first fix", "second fix"]})
        self.assertEqual(log[1]["ver"], "v1")
        again = bump_version.changelog_with(log, "v2", "x", items=["only this"], date="2026-10-30")
        self.assertEqual([e["ver"] for e in again], ["v2", "v1"])
        self.assertEqual(again[0]["items"], ["only this"])
        src = _read("tv", "bump_version.py")
        self.assertIn('os.path.join(repo, "tv", "CHANGELOG.json")', src)
        self.assertIn("changelog_with(", src[src.index("def bump("):src.index("def changelog_items(")])

    def test_the_console_serves_it_and_the_footer_opens_it(self):
        app = _read("tv", "control_app.py")
        self.assertIn('if path == "/api/changelog":', app)
        ui = _read("tv", "control_ui.html")
        foot = ui[ui.index('<span id="foot-ver">'):ui.index('id="heart-chip"')]
        self.assertIn('id="foot-hist"', foot, "the history button is not beside the version")
        self.assertIn("fetch('/api/changelog'", ui)
        self.assertIn("ev.key === 'Escape'", ui)
        self.assertIn("ev.target === o", ui, "a click outside the box does not close it")
        self.assertIn('id="hist-x"', ui)
        self.assertIn("if (gen !== histGen) return;", ui, "an older history answer can overwrite a newer open")

    def test_v3844_the_panel_takes_focus_and_gives_it_back_and_history_sits_with_the_era(self):
        ui = _read("tv", "control_ui.html")
        era = ui[ui.index('<span id="foot-era">'):ui.index('id="heart-chip"')]
        self.assertLess(era.index('id="foot-ver"'), era.index('id="foot-hist"'))
        self.assertLess(era.index('id="foot-hist"'), era.index('</span>', era.index('id="foot-hist"')) + 1)
        close = ui[ui.index("function histClose(){"):ui.index("var histGen = 0;")]
        self.assertIn("getElementById('foot-hist')", close, "closing does not hand focus back to the button")
        self.assertIn(".focus()", close)
        opn = ui[ui.index("function histOpen(){"):ui.index("fetch('/api/changelog'")]
        self.assertIn("querySelector('#hist-x')", opn, "opening does not move focus into the panel")
        self.assertIn(".focus()", opn)
        self.assertIn('aria-labelledby="hist-h"', ui)

    def test_the_cards_show_version_date_and_one_bullet_each(self):
        if NODE is None:
            self.skipTest("node is not on this machine")
        ui = _read("tv", "control_ui.html")
        a = ui.index("function cardsHtml(list){")
        b = ui.index("window._histCardsHtml = cardsHtml;")
        start = ui.rindex("function histEsc(t)", 0, a)
        prog = ui[start:b] + "\nprocess.stdout.write(cardsHtml(" + json.dumps(self.log) + "));"
        out = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        html = out.stdout
        top = self.log[0]
        self.assertTrue(html.startswith('<div class="hist-card" data-hist-ver="%s">' % top["ver"]))
        self.assertIn('<span class="hist-date">' + top["date"] + '</span>', html)   # v3856 item 6: a bare date, no zone label
        self.assertEqual(html.count("<li>"), sum(len(e["items"]) for e in self.log))
        self.assertIn("<li>shared gate ledger across worktrees</li>", html)


if __name__ == "__main__":
    unittest.main()
