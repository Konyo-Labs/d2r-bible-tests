# -*- coding: utf-8 -*-
"""v3887 (REG-3483) - THE ITEM CARD'S FULL SOURCE TABLE AND ITS DROP SIMULATOR COUNT RUNS, NOT KILLS.

The #231 second eye on v3886's REG-3451 (11-08 22:19): "the card's top six and the quick take rank by fewest runs and print that
run count ... The full source table on the same card, shown once there are more than six places, prints the kill count under
the heading Runs (50%), and its title says the rows are sorted by speed. On a one-kill boss the two counts match. On the Cow
Level one run is about 350 kills, so that table shows about 350 times too many runs." The same r50 (kills for an even chance)
also fed the Drop Simulator's "what N runs actually feel like" and its 1:chance - a per-KILL odds simulated as runs.

Now every count the card prints is s.runs (an area run counts one run), the table's title says its real order (fewest runs for
a 50% chance first - _qwRank), and the simulator rolls ONE RUN's odds (_gicRunOdds: a one-kill boss is its own odds, an area
run of k kills 1 - (1 - 1/c)^k). Runs the page's own helper in node; pins the card's template. RED_PROOF below.
[[unknown-stays-unknown]] [[copy-drift]]
"""
import io
import json
import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
NODE = shutil.which("node")


def _src():
    with io.open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _cut(src, a, b):
    assert src.count(a) == 1, "cut start %r occurs %d times - re-point this law" % (a[:60], src.count(a))
    i = src.index(a)
    return src[i:src.index(b, i + len(a)) + len(b)]


class TheItemCardCountsRunsNotKills(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _src()

    @unittest.skipUnless(NODE, "node is required to run the page's helper - UNMEASURED without it")
    def test_one_runs_odds_counts_every_kill_of_the_run(self):
        """* THE POINT - the Cow Level is ~350 kills a run: its run odds are ~350 times better than a kill's"""
        fn = _cut(self.src, "function _gicRunOdds(s) {", "\n}\n")
        js = fn + "\nprocess.stdout.write(JSON.stringify([_gicRunOdds({chance: 7000, kpr: 350}), _gicRunOdds({chance: 1500, kpr: 1}),"\
                  " _gicRunOdds({chance: 1500}), _gicRunOdds({chance: 7000, kpr: 110})]));"
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        cow, boss, bare, pit = json.loads(r.stdout)
        self.assertEqual((boss, bare), (1500, 1500), "a one-kill boss's run is not its own odds")
        self.assertTrue(19 < cow < 23, "a 350-kill run of a 1:7,000 kill is ~1:20.5 a run, got %r" % cow)
        self.assertTrue(63 < pit < 66, "a 110-kill run of a 1:7,000 kill is ~1:64 a run, got %r" % pit)

    def test_the_full_table_prints_runs_and_says_its_order(self):
        table = _cut(self.src, "        <div class=\"gic-section-title\">\U0001f4ca All ${sources.length} Sources", "</table>")
        self.assertIn("(fewest runs for a 50% chance first)", table, "the table's title claims an order it does not keep")
        self.assertIn("<td>${Math.round(s.runs).toLocaleString()}</td>", table, "the Runs column prints something else")
        self.assertNotIn("r50", table, "the table prints kills (r50) under the Runs heading again")

    def test_the_simulator_rolls_runs_at_one_runs_odds(self):
        sim = _cut(self.src, "\U0001f3b2 Drop Simulator — what ", "runs actually feel</span>")
        self.assertIn("what ${Math.round(best.runs).toLocaleString()} runs actually feel like", sim)
        self.assertIn('value="${Math.round(best.runs)}"', sim, "the simulator starts from kills, not runs")
        self.assertIn("onclick=\"window.runGicSim(${_gicRunOdds(best)})\"", sim, "the simulator rolls a kill's odds as a run's")
        self.assertNotIn("r50", sim)


RED_PROOF = [
    {"why": "v3887 (REG-3483) - the full table prints kills under Runs (50%) again (the Cow Level ~350x too many runs)",
     "file": "bible.html",
     "find": "                <td>${Math.round(s.runs).toLocaleString()}</td>\n",
     "replace": "                <td>${s.r50.toLocaleString()}</td>\n",
     "matches": 1},
    {"why": "v3887 (REG-3483) - the simulator rolls a kill's odds as a run's again",
     "file": "bible.html",
     "find": "onclick=\"window.runGicSim(${_gicRunOdds(best)})\"",
     "replace": "onclick=\"window.runGicSim(${best.chance})\"",
     "matches": 1},
    {"why": "v3887 (REG-3483) - one run's odds ignore the run's kills",
     "file": "bible.html",
     "find": "  return k === 1 ? c : 1 / (1 - Math.pow(1 - 1 / c, k));\n",
     "replace": "  return c;\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
