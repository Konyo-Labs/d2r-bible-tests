# -*- coding: utf-8 -*-
"""v3859 (#230): the owner's Sessions tab and every shadow read ONE per-session answer.

shadow_sessions.session_facts is the only place playtime, AFK, the town/field/AFK split and the route ledger (farmed,
stashed, trashed, chronicle) are worked out. The shadow digest builds its rows from it; the owner's theatre rows
(control_app._theatre_sessions) carry it as `route`, and the owner dossier draws that with the shadow's own row
renderer (_shadowSessionRow), so both sides say the same words.

RED_PROOF below: each one, applied, turns this law red."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
ROOT = os.path.join(HERE, "..")


def _read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8", errors="replace").read()


CHECKS = [
    ["tv/shadow_sessions.py", "        s.update(session_facts(g, reads, timeline))\n", 1],
    ["tv/control_app.py", "_route = _SSF.session_facts(sess, [r2 for r2 in sess if _is_a_live_read(r2)], _game_tl)\n", 1],
    ["tv/control_app.py", "                            \"route\": _route,\n", 1],
    ["tv/control_app.py", "                _game_tl = _SSF.game_timeline(_jrows)\n", 1],
    ["tv/control_ui.html", "+ window._shadowSessionRow(Object.assign({}, sm.route,", 1],
    ["tv/control_ui.html", "+ fpSec + routeSec + regretSec", 1],
    ["tv/control_ui.html", "  window._shadowSessionRow = function(s, ix){ return _shadowSessionRow(s, ix); };", 1],
]

H = 3600 * 1000


def _rows():
    return [{"ts": 1 * H, "captureTs": 1 * H, "sessionId": "A", "lane": "deep", "scene": "ground", "names": ["Shako"]},
            {"ts": 1 * H + 5000, "captureTs": 1 * H + 5000, "sessionId": "A", "lane": "deep", "scene": "inventory",
             "names": ["Shako"]},
            {"ts": 1 * H + 9000, "captureTs": 1 * H + 9000, "sessionId": "A", "lane": "deep", "scene": "stash",
             "stashTab": "personal", "names": ["Shako", "Ber Rune"]}]


class OneDigest(unittest.TestCase):

    def test_the_wiring_is_one_function(self):
        for f, nd, n in CHECKS:
            self.assertEqual(n, _read(f).count(nd), "%s: %r" % (f, nd[:90]))

    def test_the_digest_row_is_session_facts(self):
        import control_app as ca
        import replay as rp
        import shadow_sessions as ss
        rows = _rows()
        d = ss.digest(rows, "/nonexistent-hist", ca._is_a_live_read, 2 * H, make=lambda *a, **k: None)
        g = rp.split_sessions(rows)[0]
        f = ss.session_facts(g, [r for r in g if ca._is_a_live_read(r)], ss.game_timeline(rows))
        row = d["sessions"][0]
        for k, v in f.items():
            self.assertEqual(v, row.get(k), "the shadow digest's %s is not the owner's answer" % k)
        self.assertEqual({"bases": [["Shako", 1]]}, f["stashed"])


RED_PROOF = [
    {"why": "the owner's theatre rows stop carrying the shared answer",
     "file": "tv/control_app.py",
     "find": "                            \"route\": _route,\n",
     "replace": "",
     "matches": 1},
    {"why": "the owner dossier stops drawing the shared row",
     "file": "tv/control_ui.html",
     "find": "+ fpSec + routeSec + regretSec",
     "replace": "+ fpSec + regretSec",
     "matches": 1},
    {"why": "the shadow digest works its own numbers out again",
     "file": "tv/shadow_sessions.py",
     "find": "        s.update(session_facts(g, reads, timeline))\n",
     "replace": "        s.update(session_facts(g, reads, timeline)); s[\"itemsFarmed\"] = len(reads)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
