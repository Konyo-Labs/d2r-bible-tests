# -*- coding: utf-8 -*-
"""v3859 (#230, Elad: "it says 100% farming"): the owner's run line no longer says 100% farming for a session that
spent most of its time in town, in the stash or AFK.

The farming share was gameplay READS over gameplay + town reads: every stash, inventory and menu read and all AFK time
fell out of it, so gameplay reads between stash visits said 100%. With the session's time split from the one digest
(shadow_sessions.session_facts) it is out-of-town TIME over all placed time, AFK included, and the line says so.

RED_PROOF below: each one, applied, turns this law red."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
ROOT = os.path.join(HERE, "..")

T = 1792000000000


def R(dt, scene, area):
    return {"ts": T + dt, "captureTs": T + dt, "sessionId": "S", "lane": "deep", "scene": scene, "area": area}


def _rows():
    # 60 s out of town in Worldstone Keep, then 2 min in Rogue Encampment's stash, then AFK in town for 20 min
    rows = [R(i * 10000, "gameplay", "Worldstone Keep Level 2") for i in range(7)]
    rows += [R(70000 + i * 10000, "stash", "Rogue Encampment") for i in range(12)]
    rows += [R(1400000, "town", "Rogue Encampment")]
    return rows


class TheShareIsTime(unittest.TestCase):

    def test_the_fingerprint_is_not_100(self):
        import control_app as ca
        import shadow_sessions as ss
        rows = _rows()
        split = ss.session_facts(rows, rows, ss.game_timeline(rows))
        fp = ca._session_scene_fingerprint(rows, split)
        print("split %s / fp %s" % ({k: split[k] for k in ("townMs", "fieldMs", "awayMs")}, fp))
        self.assertEqual("time", fp["farmingBasis"])
        self.assertLess(fp["farmingPct"], 20, "a run mostly in the stash and AFK still says %s%% farming"
                        % fp["farmingPct"])

    def test_without_a_split_it_still_says_reads(self):
        import control_app as ca
        fp = ca._session_scene_fingerprint(_rows())
        self.assertEqual("reads", fp["farmingBasis"])

    def test_the_line_names_its_basis(self):
        ui = open(os.path.join(HERE, "control_ui.html"), encoding="utf-8", errors="replace").read()
        self.assertEqual(1, ui.count("(fp.farmingBasis === 'time' ? '(of its time, AFK included)' : '(of reads)')"))
        app = open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.assertEqual(1, app.count("\"sceneFingerprint\": _session_scene_fingerprint(sess, _route),"))


RED_PROOF = [
    {"why": "the share goes back to gameplay reads over gameplay and town reads",
     "file": "tv/control_app.py",
     "find": "        pct, basis = round(100 * _f / (_t + _f + _a)), \"time\"\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "AFK time is left out of the share again",
     "file": "tv/control_app.py",
     "find": "        pct, basis = round(100 * _f / (_t + _f + _a)), \"time\"\n",
     "replace": "        pct, basis = round(100 * _f / (_t + _f or 1)), \"time\"\n",
     "matches": 1},
    {"why": "the owner row stops passing the digest's split",
     "file": "tv/control_app.py",
     "find": "\"sceneFingerprint\": _session_scene_fingerprint(sess, _route),",
     "replace": "\"sceneFingerprint\": _session_scene_fingerprint(sess),",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
