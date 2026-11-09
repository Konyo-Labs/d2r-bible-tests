# -*- coding: utf-8 -*-
"""v3889 (REG-3497) - A TERROR-ZONE CARD'S HOVER READS AS A SENTENCE: "open the run (the Cow King)", NEVER "open the the Cow King run".

Seen in v3889's own render of the console's TZ card (#133): Moo Moo Farm's hover said "open the the Cow King run". The title
was ' — open the ' + why + ' run', and TZ_NOTABLE's reasons are phrases - 'the Council', 'the Countess', 'the Baal run',
'the Summoner', 'the best drop tier in the game' - so seven boss zones read "the the", one "run run". The reason now stands
in brackets after the verb. Read from the source: every notable reason, put through the card's own template, must read
clean. RED_PROOF below. [[source-reading-guard]]
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass

TEMPLATE = "(_boss ? ' — open the run (' + escC((t.byItems ? t.densWhy : t.why) || _boss) + ')' : ' — open the full tracker')"


def _ui():
    with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
        return fh.read()


def _notable(ui):
    head = "    var TZ_NOTABLE = {"
    assert ui.count(head) == 1, "PREMISE: TZ_NOTABLE moved or doubled"
    i = ui.index(head)
    blk = re.sub(r"/\*.{0,4000}?\*/", "", ui[i:ui.index("};", i)], flags=re.S)
    return dict(re.findall(r"""['"]([^'"]+)['"]\s*:\s*['"]([^'"]+)['"]""", blk))


class AZoneCardTitleReadsAsASentence(unittest.TestCase):

    def test_the_card_uses_the_bracketed_template(self):
        ui = _ui()
        self.assertEqual(ui.count(TEMPLATE), 1, "the card's run title is no longer the bracketed sentence")
        self.assertNotIn("' — open the ' + escC(", ui, "the old 'open the <why> run' template is back")

    def test_every_notable_reason_reads_clean(self):
        why = _notable(_ui())
        self.assertGreater(len(why), 10, "PREMISE: TZ_NOTABLE reads almost empty: %s" % why)
        bad = []
        for z, w in sorted(why.items()):
            t = "open the run (%s)" % w   # the phrase the template builds - a zone's own name may repeat ("Moo Moo Farm")
            if re.search(r"\b(\w+) \1\b", t, re.I):
                bad.append(t)
        self.assertEqual(bad, [], "a zone title repeats a word: %s" % bad)

    def test_the_old_template_would_have_doubled(self):
        """BASELINE: the reasons really do start with 'the' / end in 'run' - the old template could not read clean"""
        why = _notable(_ui())
        old = ["open the %s run" % w for w in why.values()]
        self.assertTrue(any(re.search(r"\b(\w+) \1\b", t) for t in old), "PREMISE: no reason would double a word")


RED_PROOF = [
    {"why": "v3889 (REG-3497) - the title reads 'open the the Cow King run' again",
     "file": "tv/control_ui.html",
     "find": "(_boss ? ' — open the run (' + escC((t.byItems ? t.densWhy : t.why) || _boss) + ')' : ' — open the full tracker')",
     "replace": "(_boss ? ' — open the ' + escC((t.byItems ? t.densWhy : t.why) || _boss) + ' run' : ' — open the full tracker')",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
