# -*- coding: utf-8 -*-
"""v2760 — HIS OWN FLEET ROW CAME BACK FROM CLOUDFLARE TO TELL HIM WHAT WAS ON HIS OWN DISK.

Konyo, seconds after ticking a set piece: *"i just changed my sets from a 123/135 to 124/135 but
how come THE FLEET is delayed? maybe it still has not fetched the data? should it not be SHARING A
CSS so its rendered is always the same?"*

MEASURED at that moment, on his live machine:

    tv/board_tally.json      sets {have:124, total:135}    written 6 SECONDS ago
    THE FLEET card           SETS 123 / 135                "as of 1m ago"
    Forge · Sets             124 / 135 pieces · 91%

The data was never late. The RENDER was. His own row arrives the way a cousin's does — published
to the server by the beacon, read back through `fleet_presence`, which is 60s cached — so his own
number went out to the network and came home to be shown to him, while the true figure sat in a
file on the same disk. Re-measured 2.5 minutes later: the row said 124. A transient, and a
structural one: the lag is a publish cadence plus a 60s cache, every single time he ticks.

⚠⚠ AND THE ANSWER TO HIS ACTUAL QUESTION IS NO. Sharing a stylesheet would make the two surfaces
LOOK identical while still printing 123 and 124 — the disagreement would survive in matching
fonts, which is worse, because two surfaces that look like one source and disagree are harder to
disbelieve than two that look different. What they have to share is the SOURCE.

=== THE TWO DIRECTIONS THAT MAKE THIS SAFE ===
HIS row is local because it CAN be. A PEER's row must stay on the beacon, because a peer's numbers
are knowable no other way — overlaying local figures onto Dean's row would publish Konyo's board as
Dean's, the same class of defect as rendering one machine's roster as another's denominator.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

import control_app as CA  # noqa: E402


def _fleet(mine_sets, theirs_sets, at=1000):
    """A fleet payload with HIS row and a PEER's row, both carrying beacon figures."""
    return {
        "me": "konyo-3",
        "online": [{"machine": "konyo-3",
                    "tally": {"sets": {"have": mine_sets, "total": 135},
                              "uniques": {"have": 292, "total": 403}, "at": at}}],
        "offline": [{"machine": "LAPTOP-QNFL8",
                     "tally": {"sets": {"have": theirs_sets, "total": 135},
                               "uniques": {"have": 0, "total": 403}, "at": at}}],
    }


class HisOwnRowIsNotARoundTrip(unittest.TestCase):

    def setUp(self):
        self.real = CA.board_tally_load

    def tearDown(self):
        CA.board_tally_load = self.real

    def _local(self, doc):
        CA.board_tally_load = lambda: doc

    # ── ⚠⚠ THE LAW ───────────────────────────────────────────────────────────────────────────
    def test_his_row_takes_the_LOCAL_figure_over_the_beacons(self):
        """The exact case: the beacon still says 123, the disk already says 124."""
        self._local({"sets": {"have": 124, "total": 135}, "at": 9999})
        fl = _fleet(mine_sets=123, theirs_sets=130)
        n = CA._fleet_overlay_local_tally(fl, "konyo-3")
        self.assertEqual(1, n, "no row was overlaid")
        self.assertEqual(124, fl["online"][0]["tally"]["sets"]["have"],
                         "his own row still shows the beacon's stale count, so the card can lag "
                         "his own Forge page by a publish cadence plus a 60s cache")
        self.assertEqual(9999, fl["online"][0]["tally"]["at"],
                         "the row kept the beacon's timestamp beside a local figure — the age "
                         "would describe a different reading than the number")
        self.assertTrue(fl["online"][0]["tally"].get("localRead"),
                        "nothing marks the row as read locally, so a reader cannot tell which "
                        "rows are round-tripped and which are not")

    # ── ⚠ THE DIRECTION THAT KEEPS A PEER HONEST ─────────────────────────────────────────────
    def test_a_PEER_row_is_NEVER_overlaid(self):
        """★ THE SAFETY LAW. A peer's numbers are knowable only through the beacon. Overlaying
        local figures onto Dean's row would publish Konyo's board as Dean's."""
        self._local({"sets": {"have": 124, "total": 135}, "at": 9999})
        fl = _fleet(mine_sets=123, theirs_sets=130)
        CA._fleet_overlay_local_tally(fl, "konyo-3")
        peer = fl["offline"][0]["tally"]
        self.assertEqual(130, peer["sets"]["have"],
                         "the PEER's row was overwritten with this machine's tally — his cousin's "
                         "card would show Konyo's board as Dean's")
        self.assertNotIn("localRead", peer)

    def test_it_matches_on_the_machine_NAME_not_position(self):
        self._local({"sets": {"have": 124, "total": 135}})
        fl = _fleet(123, 130)
        self.assertEqual(0, CA._fleet_overlay_local_tally(fl, "some-other-box"),
                         "a row was overlaid for a machine that is not this one")
        self.assertEqual(123, fl["online"][0]["tally"]["sets"]["have"])

    # ── ⚠ ABSENT IS NOT ZERO ─────────────────────────────────────────────────────────────────
    def test_a_ledger_the_local_file_lacks_KEEPS_the_beacon_figure(self):
        """Blanking a row that was reporting fine, because the local file happens not to carry
        that ledger, replaces a real number with a worse one. [[unknown-stays-unknown]]"""
        self._local({"sets": {"have": 124, "total": 135}})      # no uniques key at all
        fl = _fleet(123, 130)
        CA._fleet_overlay_local_tally(fl, "konyo-3")
        t = fl["online"][0]["tally"]
        self.assertEqual(124, t["sets"]["have"])
        self.assertEqual(292, t["uniques"]["have"],
                         "uniques was blanked because the local file did not carry it — an absent "
                         "local figure must leave the beacon's alone")

    def test_a_total_of_ZERO_is_not_treated_as_a_reading(self):
        """`{'have': 0, 'total': 0}` is an unwritten store, not a board that owns nothing."""
        self._local({"sets": {"have": 0, "total": 0}})
        fl = _fleet(123, 130)
        CA._fleet_overlay_local_tally(fl, "konyo-3")
        self.assertEqual(123, fl["online"][0]["tally"]["sets"]["have"],
                         "a zero-total local figure overwrote a real beacon count")

    def test_an_UNREADABLE_local_tally_leaves_every_row_alone(self):
        def boom():
            raise IOError("simulated")
        CA.board_tally_load = boom
        fl = _fleet(123, 130)
        self.assertEqual(0, CA._fleet_overlay_local_tally(fl, "konyo-3"))
        self.assertEqual(123, fl["online"][0]["tally"]["sets"]["have"],
                         "an unreadable local tally damaged the row it could not improve")

    def test_a_MISSING_local_tally_file_leaves_every_row_alone(self):
        self._local(None)
        fl = _fleet(123, 130)
        self.assertEqual(0, CA._fleet_overlay_local_tally(fl, "konyo-3"))

    # ── ⚠ THE PATH AUTHORITY, NOT A SECOND JOIN OF ITS OWN ───────────────────────────────────
    def test_it_reads_through_board_tally_load_not_its_own_path(self):
        """★ `_fleet_show_total` hardcoded os.path.join(HERE, 'board_tally.json') and thereby
        bypassed the TV_HIST isolation override, so an isolated run read his live state. Proven by
        SUBSTITUTION rather than by grepping for a string: if this function had its own path, the
        stub below could not change what it sees."""
        seen = {"n": 0}

        def counting():
            seen["n"] += 1
            return {"sets": {"have": 124, "total": 135}}
        CA.board_tally_load = counting
        fl = _fleet(123, 130)
        CA._fleet_overlay_local_tally(fl, "konyo-3")
        self.assertEqual(1, seen["n"],
                         "the overlay never called board_tally_load, so it is reading a path of "
                         "its own and is blind to the isolation override")

    def test_every_row_divides_uniques_by_the_chronicle_pin(self):
        fl = _fleet(mine_sets=123, theirs_sets=130)
        n = CA._fleet_apply_unique_pin(fl, 397)
        self.assertEqual(2, n)
        self.assertEqual({"have": 292, "total": 397}, fl["online"][0]["tally"]["uniques"])
        self.assertEqual({"have": 0, "total": 397}, fl["offline"][0]["tally"]["uniques"])
        self.assertEqual(135, fl["online"][0]["tally"]["sets"]["total"])
        self.assertEqual(130, fl["offline"][0]["tally"]["sets"]["have"])

    def test_a_missing_pin_leaves_the_published_total_alone(self):
        fl = _fleet(123, 130)
        self.assertEqual(0, CA._fleet_apply_unique_pin(fl, None))
        self.assertEqual(403, fl["online"][0]["tally"]["uniques"]["total"])
        self.assertEqual(0, CA._fleet_apply_unique_pin(fl, 0))
        self.assertEqual(403, fl["offline"][0]["tally"]["uniques"]["total"])

    def test_a_row_with_no_uniques_pair_is_left_alone(self):
        fl = {"online": [{"machine": "x", "tally": {"sets": {"have": 1, "total": 135}}}],
              "offline": []}
        self.assertEqual(0, CA._fleet_apply_unique_pin(fl, 397))
        self.assertNotIn("uniques", fl["online"][0]["tally"])

    def test_the_route_applies_the_pin_and_does_not_fall_back_to_the_roster(self):
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        i = src.find('if path == "/api/fleet":')
        j = src.find('if path.startswith("/api/fleet_compare")', i)
        body = src[i:j]
        self.assertLess(body.find("_fleet_overlay_local_tally("),
                        body.find("_fleet_apply_unique_pin("))
        self.assertIn('"uniques": _pinU,', body)
        self.assertNotIn('unique_roster.json", "count"', body)
        ui = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8",
                     errors="replace").read()
        self.assertEqual(ui.count("var t = shared || own;"), 1)

    def test_the_route_actually_calls_it(self):
        """⚠ Built and not called is this repo's most repeated defect. [[the-unjoined-end]]"""
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        i = src.find('if path == "/api/fleet":')
        self.assertGreater(i, 0, "the fleet route is gone")
        j = src.find('if path.startswith("/api/fleet_compare")', i)
        self.assertIn("_fleet_overlay_local_tally(", src[i:j],
                      "the /api/fleet route never calls the overlay, so his own row is still a "
                      "round trip and every law above grades a function nothing runs")


RED_PROOF = [
    {
        'why': "His own fleet row must take the LOCAL board_tally figure over the beacon's round-tripped one — deleting the overlay write puts his card back a publish cadence plus a 60s cache behind his own disk (123 while board_tally.json already says 124).  MEASURED: untampered 9 tests, OK (green) — perl -e 'alarm 200; exec @ARGV' python3 tv/test_his_own_fleet_row_is; tampered (all 1) FAILED (failures=2): test_his_row_takes_the_LOCAL_figure_over_the_beacons (AssertionError:; reddened law HisOwnRowIsNotARoundTrip.test_his_row_takes_the_LOCAL_figure_over_the_; ALONE RED ALONE — python3 -m unittest test_his_own_fleet_row_is_not_a_round_trip.HisOwnRowIsNotARoundTrip.test_his_r.",
        'file': 'control_app.py',
        'find': 't[led] = dict(v)',
        'replace': 'v = dict(v)',
        'matches': 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
