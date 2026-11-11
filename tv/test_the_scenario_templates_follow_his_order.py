# -*- coding: utf-8 -*-
"""v3893 (REG-3552) - SCENARIO TEMPLATES FOLLOW HIS ORDER, WITHOUT INVENTED PIXELS.

His design, in order: login → CONNECTING → character select (character name + class) → lobby
(game name typed or seen, then chosen) → game-entry portal → in game in a TOWN (act 1–5).
Only character names and game names vary across those screens. The D2R door in front of
CONNECTING is still the fire logo then the title. The stash reader is already joined to this
walk and to the recorder window (REG-3550); a reel is tagged from the highlighted name (REG-3551).

This tree has measured templates for logo, title, char-select, lobby and in-game orbs (hud/town).
It has no real Battle.net-login, CONNECTING... or game-entry-portal frames, and no act-1–5 town
templates, so those steps are reported — not invented. Character name+class reuse selected_of /
logins; game names reuse game_name_of_row. Run counting from Konyo/Konyo55 and corner-text
(difficulty, area, act, level) vs the town are later slices.

Law: the ordered model is the one he named; lobby, portal, connecting and login never reach the
stash reader; hud/town do; character select does not flip the walk into play (that waits for a
town). RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import d2r_screens as DS  # noqa: E402
import stash_eye as SE  # noqa: E402


class TheOrderIsTheOneHeNamed(unittest.TestCase):

    def test_the_scenarios_are_in_his_order(self):
        self.assertEqual(DS.SCENARIO_ORDER, (
            "login", "logo", "title", "connecting", "char-select", "lobby", "portal", "town",
        ))

    def test_kinds_map_onto_those_scenarios(self):
        self.assertEqual(DS.scenario_of_kind("logo"), "logo")
        self.assertEqual(DS.scenario_of_kind("title"), "title")
        self.assertEqual(DS.scenario_of_kind("char-select"), "char-select")
        self.assertEqual(DS.scenario_of_kind("lobby"), "lobby")
        self.assertEqual(DS.scenario_of_kind("hud"), "town")
        self.assertEqual(DS.scenario_of_kind("town"), "town")
        self.assertIsNone(DS.scenario_of_kind(None))

    def test_steps_without_real_frames_are_reported_not_invented(self):
        for step in ("login", "portal"):   # v3898 (REG-3715) - connecting is measured now (test_the_connecting_screen_is_a_door)
            ev = DS.SCENARIO_EVIDENCE[step]
            self.assertTrue(ev.startswith("none"), (step, ev))
        self.assertIn("no act-1–5 town templates", DS.SCENARIO_EVIDENCE["town"])
        with open(os.path.join(HERE, "d2r_screens.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("CONNECTING_BAND", src)
        self.assertNotIn("PORTAL_BAND", src)
        self.assertNotIn("BATTLENET_LOGIN_BAND", src)


class TheStashReaderWaitsForTheTown(unittest.TestCase):

    def test_lobby_portal_connecting_and_login_never_run_the_readers(self):
        for kind in ("lobby", "portal", "connecting", "login"):
            self.assertFalse(DS.readers_may_run(kind, recording=True), kind)
            self.assertFalse(DS.readers_may_run(kind, chain={"entered": True}, recording=True), kind)

    def test_hud_and_town_do(self):
        self.assertTrue(DS.readers_may_run("hud", recording=True))
        self.assertTrue(DS.readers_may_run("town", recording=True))

    def test_character_select_does_not_flip_the_walk_into_play(self):
        # chain()'s entered flag means the login door (char-select after the title), not a town
        self.assertFalse(DS.play_after("char-select", {"entered": True}, False))
        self.assertFalse(DS.play_after("lobby", {"entered": True}, False))
        self.assertFalse(DS.play_after("portal", {"entered": True}, False))
        self.assertTrue(DS.play_after("hud", None, False))
        self.assertTrue(DS.play_after("town", None, False))
        self.assertTrue(DS.play_after("lobby", None, True), "once in a town, later lobby frames keep the walk")

    def test_a_lobby_frame_never_reaches_the_stash_reader(self):
        calls = []
        real = SE.classify_stash_grid
        SE.classify_stash_grid = lambda path: calls.append(path) or real(path)
        try:
            lab, det = SE.classify_when_in_play("unused.jpg", kind="lobby", recording=True)
            self.assertEqual(lab, "gameplay")
            self.assertTrue(det.get("skipped"), det)
            self.assertEqual(calls, [])
            lab, det = SE.classify_when_in_play("unused.jpg", kind="portal", recording=True)
            self.assertTrue(det.get("skipped"), det)
            self.assertEqual(calls, [])
        finally:
            SE.classify_stash_grid = real


class TheExistingReadersAreReused(unittest.TestCase):

    def test_name_and_game_readers_already_exist(self):
        import char_select as CS
        import read_identity as RI
        self.assertTrue(callable(CS.selected_of))
        self.assertTrue(callable(CS.logins))
        self.assertTrue(callable(RI.game_name_of_row))
        self.assertTrue(callable(RI.game_runs))


RED_PROOF = [
    {"why": "v3893 (REG-3552) - lobby is treated as in-game and may run the stash reader",
     "file": "tv/d2r_screens.py",
     "find": "PRE_GAME = frozenset((\"logo\", \"title\", \"char-select\", \"lobby\", \"portal\", \"connecting\", \"login\"))\n",
     "replace": "PRE_GAME = frozenset((\"logo\", \"title\", \"char-select\"))\n",
     "matches": 1},
    {"why": "v3893 (REG-3552) - character select flips the walk into play before the town",
     "file": "tv/d2r_screens.py",
     "find": "    if kind in IN_PLAY:\n        return True\n    return False\n",
     "replace": "    if kind in IN_PLAY:\n        return True\n    if isinstance(chain, dict) and chain.get(\"entered\") is True:\n        return True\n    return False\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
