# -*- coding: utf-8 -*-
"""REG-2867 - THE ROSTER LANE SAYS ITS PROFILE AND SESSIONS POSTS, NOT ONLY ITS ROWS.

The roster lane (control_app._roster_publish_loop) posts three things: the rows, the profile (console_snapshot) and the
summarized sessions (shadow_sessions). Each keeps its own receipt on this PC - .tvd_roster.json, .roster_profile_state.json,
.roster_frames_state.json - but GET /api/roster-cache's meLine and the console's roster panel said only the rows'. A refused
sessions post (its why, postedAt, refuseAt all on disk) was visible nowhere: GrokBot looked and could not find it.

Now the route serves laneLines - one line per post, from its own receipt, by roster_publish.lane_line - and the panel and the
route's html draw them under the rows' line. A held lane says HELD; a post that did not go through says so with its age and
the site's own words (the receipt keeps no difference between refused and unreached, so neither is claimed); a stored or
skipped post says which; a look that posted nothing says why; no receipt is UNKNOWN. The profile keeps its last POST whole,
so a later gate reason never hides its refusal.

Driven on the real apply_reply of each lane (their receipts as they write them), roster_publish.lane_line / roster_html, the
route's own lines cut from control_app.py and run with its reads stood in, and the panel's line in control_ui.html.
RED_PROOF below.
"""
import io
import os
import sys
import textwrap
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx  # noqa: E402
_fx.contain()

import console_snapshot as CS  # noqa: E402
import roster_publish as RP  # noqa: E402
import shadow_sessions as SS  # noqa: E402

APP = os.path.join(HERE, "control_app.py")
UI = os.path.join(HERE, "control_ui.html")
NOW = 1793200000000
MIN = 60000
REFUSED = "roster would not take this frames digest: the body is larger than 900000 bytes"


def _read(p):
    with io.open(p, encoding="utf-8") as fh:
        return fh.read()


def _frames(reply, at, state=None):
    return SS.apply_reply(state or {}, "h1", reply, at)


def _profile(reply, at, state=None):
    return CS.apply_reply(state or {}, {"d2r_owned": "[]"}, reply, at)


def _served(lanes):
    """What /api/roster-cache serves: the route's own lines, cut from control_app.py, its reads stood in."""
    src = _read(APP)
    head = '        if path == "/api/roster-cache":\n'
    if src.count(head) != 1:
        raise AssertionError("the roster-cache route is in control_app.py %d times - re-point this law" % src.count(head))
    at = src.index(head) + len(head)
    door = textwrap.dedent(src[at:src.index("            return\n", at)])
    sent = []
    ns = {"_roster_cache_payload": lambda: {"ok": True, "fetched": False, "owners": []},
          "_roster_state_load": lambda: None,
          "_profile_json_load": lambda path: lanes.get(path), "_profile_state_path": lambda: "profile",
          "_frames_state_path": lambda: "frames",
          "time": types.SimpleNamespace(time=lambda: NOW / 1000.0),
          "self": types.SimpleNamespace(_json=lambda code, data: sent.append((code, data)))}
    exec(compile(door, APP, "exec"), ns)
    if len(sent) != 1 or sent[0][0] != 200:
        raise AssertionError("the route served %r" % (sent,))
    return sent[0][1]


class EachPostSaysItsOwnReceipt(unittest.TestCase):

    def test_a_refused_sessions_post_is_said_with_its_age_and_the_sites_words(self):
        st = _frames({"ok": False, "why": REFUSED}, NOW - 5 * MIN)
        line = RP.lane_line("frames", st, NOW)
        self.assertEqual(line["words"], "this PC's sessions upload did NOT go through (5 min ago): " + REFUSED)
        self.assertIn("roster-refused", line["cls"])

    def test_a_stored_or_skipped_sessions_post_says_which(self):
        st = _frames({"ok": True, "stored": ["frames"]}, NOW - 2 * MIN, _frames({"ok": False, "why": "x"}, NOW - 9 * MIN))
        self.assertEqual(RP.lane_line("frames", st, NOW)["words"], "this PC's sessions upload (2 min ago): stored")
        st = _frames({"ok": True, "stored": [], "skipped": ["unchanged"]}, NOW - 3 * MIN)
        line = RP.lane_line("frames", st, NOW)
        self.assertEqual(line["words"], "this PC's sessions upload (3 min ago): skipped: unchanged")
        self.assertNotIn("roster-refused", line["cls"])

    def test_a_look_that_posted_nothing_says_why(self):
        st = dict(_frames({"ok": True, "stored": ["frames"]}, NOW - 200 * MIN), why="no session to summarize",
                  checkedAt=NOW - MIN)
        self.assertEqual(RP.lane_line("frames", st, NOW)["words"],
                         "this PC's sessions upload posted nothing (1 min ago): no session to summarize")

    def test_a_held_lane_and_no_receipt(self):
        st = dict(_frames({"ok": False, "why": REFUSED}, NOW - MIN), why="suppressed: a fixture")
        self.assertEqual(RP.lane_line("frames", st, NOW)["words"], "this PC's sessions upload is HELD: suppressed: a fixture")
        for none in (None, {}):
            self.assertEqual(RP.lane_line("frames", none, NOW)["words"],
                             "this PC's sessions upload: UNKNOWN (this PC has no receipt for it yet)")
        self.assertIn("UNKNOWN", RP.lane_line("profile", {"why": "ValueError"}, NOW)["words"])

    def test_a_refused_profile_post_survives_a_later_gate_reason(self):
        st = _profile({"ok": False, "why": "roster would not take this profile: the body is larger than 200000 bytes"},
                      NOW - 7 * MIN)
        st["why"] = "within 75 min of the last upload"          # the gate's tick after it, as _profile_publish_once writes
        line = RP.lane_line("profile", st, NOW)
        self.assertEqual(line["words"], "this PC's profile upload did NOT go through (7 min ago): roster would not take "
                                        "this profile: the body is larger than 200000 bytes")
        st = _profile({"ok": True, "stored": ["profile"]}, NOW - MIN)
        self.assertEqual(RP.lane_line("profile", st, NOW)["words"], "this PC's profile upload (1 min ago): stored")


class TheRouteAndThePanelDrawThem(unittest.TestCase):

    def test_the_route_serves_both_lines_and_its_html_carries_them(self):
        refused = _frames({"ok": False, "why": REFUSED + " <b>"}, NOW - 5 * MIN)
        data = _served({"profile": _profile({"ok": True, "stored": ["profile"]}, NOW - MIN), "frames": refused})
        words = [l["words"] for l in data["laneLines"]]
        self.assertEqual(words[0], "this PC's profile upload (1 min ago): stored")
        self.assertTrue(words[1].startswith("this PC's sessions upload did NOT go through (5 min ago): "), words)
        self.assertIn("did NOT go through (5 min ago): " + REFUSED + " &lt;b&gt;", data["html"],
                      "the route's html does not carry the refused sessions post")
        self.assertNotIn("<b>", data["html"])

    def test_the_panel_draws_them_under_the_rows_line(self):
        ui = _read(UI)
        lead = "      var lead = '<div class=\"' + esc(me.cls || 'roster-me') + '\">' + esc(me.words) + '</div>';\n"
        draw = ("        if (l && typeof l.words === 'string' && l.words) lead += '<div class=\"' + esc(l.cls || 'roster-me') "
                "+ '\">' + esc(l.words) + '</div>';\n")
        self.assertEqual(ui.count(lead), 1, "the panel's rows line moved - re-point this law")
        self.assertEqual(ui.count(draw), 1, "the panel no longer draws the lane's lines")
        self.assertLess(ui.index(lead), ui.index(draw))
        self.assertIn("data.laneLines", ui[ui.index(lead):ui.index(draw)])


RED_PROOF = [
    {"why": "REG-2867 - the route stops serving the profile and sessions lines (a refused post is said nowhere)",
     "file": "tv/control_app.py",
     "find": "            data[\"laneLines\"] = _rp.lane_lines(",
     "replace": "            data[\"laneLinesOff\"] = _rp.lane_lines(",
     "matches": 1},
    {"why": "REG-2867 - a post that did not go through reads as one that went",
     "file": "tv/roster_publish.py",
     "find": "    if name == \"refused\":\n        said = why[len(\"refused: \"):]",
     "replace": "    if False:\n        said = why[len(\"refused: \"):]",
     "matches": 1},
    {"why": "REG-2867 - a later gate reason hides the profile's refusal",
     "file": "tv/roster_publish.py",
     "find": "    if kind == \"profile\" and post is not None and _ms(post.get(\"at\")):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-2867 - a held lane reads as its last post",
     "file": "tv/roster_publish.py",
     "find": "    if why.startswith(\"suppressed\"):\n        return {\"kind\": kind, \"cls\": \"roster-me roster-unknown\", \"words\": \"%s is HELD: %s\" % (head, why)}\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2867 - the route's html drops the lane's lines",
     "file": "tv/roster_publish.py",
     "find": "    for line in (payload.get(\"laneLines\") or []) if isinstance(payload, dict) else []:\n",
     "replace": "    for line in []:\n",
     "matches": 1},
    {"why": "REG-2867 - no receipt reads as an empty, quiet lane instead of UNKNOWN",
     "file": "tv/roster_publish.py",
     "find": "        return {\"kind\": kind, \"cls\": \"roster-me roster-unknown\", \"words\": head + \": UNKNOWN (this PC has no receipt for it yet)\"}\n",
     "replace": "        return None\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
