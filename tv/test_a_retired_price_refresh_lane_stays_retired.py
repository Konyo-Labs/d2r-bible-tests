# -*- coding: utf-8 -*-
"""Job E item 3 (Claude's #230 6849292433; his 11-13 rulings on #96) - THE 20-MINUTE PRICE REFRESH LANE IS RETIRED, AND
EVERY PLACE A READER WOULD LOOK SAYS SO.

His words: "yea you can" (retire the timer lane tvd-price-refresh), and on a background re-read, "it doesnt need to redo
things for now.. it can do it in the future". So NO background re-read is built: a price check refreshes the item it
reads, on his click, one search a minute, only when that item's read is past 90 days. Removed: control_app's
_price_refresh_loop, its thread row, its _PRICE_REFRESH_* cadence, its harness stand-down, auto_scope's sheet and
lane-to-loop row, loop_corroborate's surface and beat, shelf_driver's NOT_SHELF_LANES entry, d2jsp_refresh.run_once /
stale_items and #56's once-a-day check read that rode it, and the BLUEPRINT lane-table row.
Held here, two ways:
  1. GONE - no file under tv/ starts, ticks, traces, scopes, corroborates or excuses the lane (only comments name it), and
     BLUEPRINT's lane table has no _price_refresh_loop row;
  2. SAID - each of those places carries the ruling ("11-13") where the lane used to sit, so the next reader finds why it
     is gone instead of re-adding it, and both of its old laws' gate lines in run_gates say RETIRED.
Pure python over the tree. RED_PROOF below (hand-proven red/green, GrokBot box build).
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
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

LANE = "tvd-price-refresh"
LOOP = "_price_refresh_loop"
RULING = "11-13"


def _read(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _code(src):
    """python source without comments or docstrings-as-comments: only lines that are not comments"""
    out = []
    for line in src.splitlines():
        s = line.lstrip()
        if s.startswith("#"):
            continue
        out.append(line.split("  #", 1)[0])
    return "\n".join(out)


class TheLaneIsGone(unittest.TestCase):

    def test_no_python_file_runs_the_lane(self):
        """no start row, no tick, no trace note, no loop, no cadence - in any tv/*.py that is not a test"""
        bad = []
        pat = re.compile(r"\(\s*['\"]" + re.escape(LANE) + r"['\"]\s*,|_lane_tick\(\s*['\"]" + re.escape(LANE)
                         + r"|\.note\(\s*['\"]" + re.escape(LANE) + r"|def " + LOOP + r"\(|_PRICE_REFRESH_(FIRST|EVERY)_S\s*=")
        for name in sorted(os.listdir(HERE)):
            if not name.endswith(".py") or name.startswith("test_"):
                continue
            code = _code(_read(os.path.join("tv", name)))
            for m in pat.finditer(code):
                bad.append("%s: %s" % (name, m.group(0)))
        self.assertEqual(bad, [], "the retired lane runs again:\n  " + "\n  ".join(bad))

    def test_no_registry_holds_it(self):
        import auto_scope as AS
        import loop_corroborate as LC
        import shelf_driver as SD
        self.assertNotIn(LANE, AS.LANES)
        self.assertNotIn(LANE, AS.LANE_FN)
        self.assertNotIn(LOOP, AS.LANE_FN.values())
        self.assertNotIn(LOOP, LC.SURFACES)
        self.assertNotIn(LOOP, LC.LOOPS)
        self.assertNotIn(LANE, SD.NOT_SHELF_LANES)
        app = _read("tv/control_app.py")
        skip = app[app.index("_HARNESS_ONLY_SKIP = ("):app.index("_LANES_STOOD_DOWN = set()")]
        self.assertFalse(LANE in _code(skip), "a harness stands down a lane that no longer exists")

    def test_blueprints_lane_table_has_no_row_for_it(self):
        bp = _read("BLUEPRINT.md")
        self.assertFalse(re.search(r"^\s+" + LOOP + r"\s+every ", bp, re.M), "BLUEPRINT still lists the retired loop's cadence")
        row = [l for l in bp.splitlines() if l.startswith("- **d2jsp_refresh.py**")]
        self.assertEqual(len(row), 1, "BLUEPRINT has no row for d2jsp_refresh.py")
        self.assertIn("RETIRED", row[0], "BLUEPRINT's d2jsp_refresh row does not say its lane is retired")


class EveryPlaceSaysWhy(unittest.TestCase):
    """where the lane used to sit, the ruling sits now - a reader who goes looking finds why, not a hole"""

    PLACES = (
        ("tv/control_app.py", "# Job E - the #96/#88 price refresh lane, tvd-price-refresh"),          # the thread list
        ("tv/control_app.py", '# Job E - "tvd-price-refresh" (#96\'s 20-minute price re-read) is no longer here'),  # harness
        ("tv/control_app.py", "#: Job E - _PRICE_REFRESH_FIRST_S / _PRICE_REFRESH_EVERY_S and _price_refresh_loop"),
        ("tv/auto_scope.py", '    # Job E - "tvd-price-refresh" (#96/#88, one due price-database item every twenty minutes) is RETIRED'),
        ("tv/auto_scope.py", '    # Job E - "tvd-price-refresh" -> _price_refresh_loop RETIRED (his 11-13 ruling)'),
        ("tv/loop_corroborate.py", "#: Job E - _price_refresh_loop (v3878 #96/#88) left SURFACES: it is RETIRED by his 11-13 ruling"),
        ("tv/loop_corroborate.py", "    # Job E - the #96/#88 price refresh (_price_refresh_loop, \"tvd-price-refresh\", 1200 s) is RETIRED by his 11-13 ruling"),
        ("tv/shelf_driver.py", "#:     (tvd-price-refresh  #96's price re-read - RETIRED by his 11-13 ruling (Job E)"),
        ("tv/control_ui.html", "the once-a-day\n     read through the refresh lane is RETIRED by his 11-13 ruling"),
    )

    def test_each_place_says_the_ruling(self):
        missing = []
        for rel, line in self.PLACES:
            src = _read(rel)
            if line not in src:
                missing.append("%s: %s" % (rel, line[:70]))
                continue
            at = src.index(line)
            if RULING not in src[at:at + len(line) + 400]:
                missing.append("%s: the note does not name his %s ruling" % (rel, RULING))
        self.assertEqual(missing, [], "a place the lane used to sit says nothing about why it is gone:\n  " + "\n  ".join(missing))

    def test_the_module_and_its_old_laws_say_it(self):
        import d2jsp_refresh as DR
        self.assertIn("RETIRED by his 11-13 ruling", DR.__doc__ or "")
        self.assertIn("it doesnt need to redo things for now.. it can do it in the future", DR.__doc__ or "")
        gates = _read("tv/run_gates.py")
        for gate in ("test_the_price_database_refreshes_itself", "test_each_pc_reads_d2jsp_once_a_day"):
            a = gates.index('Gate("%s",' % gate)
            why = gates[a:gates.index("),\n", a)]
            self.assertIn("RETIRED", why, "%s's gate line still describes the retired lane as running" % gate)
            self.assertIn(RULING, why)


RED_PROOF = [
    {"why": "Job E - the lane's thread row is put back in the console's roster",
     "file": "tv/control_app.py",
     "find": "        # re-read is built: a price check refreshes the item it reads, on his click, one search a minute.\n",
     "replace": "        # re-read is built: a price check refreshes the item it reads, on his click, one search a minute.\n"
                "        (\"tvd-price-refresh\", _prune_loop),\n",
     "matches": 1},
    {"why": "Job E - the scope sheet maps the retired lane to its loop again",
     "file": "tv/auto_scope.py",
     "find": "    # Job E - \"tvd-price-refresh\" -> _price_refresh_loop RETIRED (his 11-13 ruling): no lane, no loop\n",
     "replace": "    \"tvd-price-refresh\": \"_price_refresh_loop\",\n",
     "matches": 1},
    {"why": "Job E - the shelf excuses the retired lane again",
     "file": "tv/shelf_driver.py",
     "find": "                   \"tvd-river-warm\", \"tvd-disk-sign\")",
     "replace": "                   \"tvd-price-refresh\", \"tvd-river-warm\", \"tvd-disk-sign\")",
     "matches": 1},
    {"why": "Job E - the retirement note at the thread list is deleted (a reader finds a hole, not the ruling)",
     "file": "tv/control_app.py",
     "find": "        # Job E - the #96/#88 price refresh lane, tvd-price-refresh (one due item every 20 min), is RETIRED by his 11-13\n",
     "replace": "",
     "matches": 1},
    {"why": "Job E - the old law's gate line still says the lane refreshes every pass",
     "file": "tv/run_gates.py",
     "find": "why='v3878 #96/#88, Job E (his 11-13 ruling) - the timer lane tvd-price-refresh is RETIRED:",
     "replace": "why='v3878 #96/#88 - the price DB refreshes itself, one due item a pass:",
     "matches": 1},
    {"why": "Job E - a tick for the retired lane comes back in a helper",
     "file": "tv/d2jsp_refresh.py",
     "find": "CHECK_NAME = \".d2jsp_check.json\"\n",
     "replace": "CHECK_NAME = \".d2jsp_check.json\"\n_TICK = (\"tvd-price-refresh\", 1200.0)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
