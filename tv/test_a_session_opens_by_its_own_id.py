# -*- coding: utf-8 -*-
"""#135 — A SESSION OPENS BY ITS OWN ID, AT EVERY DOOR.

GrokBot's live passes on v3544 and v3546 (#230, 2026-10-01): pick "Session 28" -> the dossier of 46, then of 175, every
tick ("theatre open WRONG / reopen WRONG"). Every door that opens a dossier - a shelf card, the Best run / Most reads
highlight cards, the hero row, the route link, the re-renders - handed _sessionDossier a NUMBER, and a number is a
position when a session carries none: in whichever list that door painted from (the highlights paint from a
newest-first copy without the ghosts), looked up again in TH.sessions. The cards already carried the id (data-sid);
nothing passed it.

  · DRIVEN in node, the real page code cut by its markers: opened by id, the dossier is THAT session's even when the
    number would point elsewhere; the box carries the id it shows; a number still opens a door that has no id; an id
    the shelf does not hold opens nothing (never a neighbour by number).
  · Every door passes the id it carries (the shipped click handlers and card templates, read for the exact calls).
No node on this PC = the page half SKIPS with its reason; a skip is not a pass. RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

UI = os.path.join(HERE, "control_ui.html")
NODE = shutil.which("node")


def _src():
    with io.open(UI, encoding="utf-8") as fh:
        return fh.read()


def _code():
    """the page with // line comments dropped, so a guard reads calls, never the prose about them"""
    out = []
    for ln in _src().split("\n"):
        i = ln.find("   // ")
        out.append(ln[:i] if i >= 0 else ln)
    return "\n".join(out)


def _open_fn():
    s = _src()
    i = s.index("/* ⟦SESSION DOSSIER BEGIN⟧ */")
    j = s.index("/* ⟦SESSION DOSSIER END⟧ */", i)
    return s[i:j]


_FAKE = r"""
var attrs = {};
var OV = { hidden: true, innerHTML: '', scrollTop: 0,
  setAttribute: function(k, v){ attrs[k] = String(v); }, getAttribute: function(k){ return attrs[k] === undefined ? null : attrs[k]; },
  querySelector: function(){ return null; } };
var document = { getElementById: function(id){ return id === 'th-dossier-ov' ? OV : null; } };
var DOSSIER = {}; function _dossierHtml(sm){ return 'DOSSIER ' + sm.sessionId; } function _animCounts(){}
"""


def _run(sessions, calls):
    prog = (_FAKE + "var TH = {sessions: " + json.dumps(sessions) + "};\n" + _open_fn() + "\n" + calls + "\n"
            "console.log(JSON.stringify({html: OV.innerHTML, hidden: OV.hidden, n: attrs['data-n'] || null,"
            " sid: attrs['data-sid'] || null}));\n")
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, encoding="utf-8", timeout=60)
    if r.returncode != 0:
        raise AssertionError("the page code would not run in node: %s" % r.stderr[-500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


#: sessions with NO number of their own (the shape that made the number a position), newest last
SHELF = [{"sessionId": "s_100_1"}, {"sessionId": "s_200_2"}, {"sessionId": "s_300_3"}, {"sessionId": "s_400_4"}]


@unittest.skipIf(NODE is None, "no node on this PC - the page half is UNMEASURED here, not passing")
class TheDossierOpensTheSessionItWasHanded(unittest.TestCase):

    def test_by_id_it_is_that_session_whatever_the_number_says(self):
        # the highlight cards number from a newest-first copy: s_400_4 is "1" there, and 1 here is s_100_1
        got = _run(SHELF, "_sessionDossier(1, 's_400_4');")
        self.assertEqual(got["html"], "DOSSIER s_400_4", "the dossier opened the session the NUMBER points at: %r" % got)
        self.assertEqual(got["sid"], "s_400_4", "the box does not say which session it shows")
        self.assertEqual(got["n"], "4", "the box's number is not this list's number for that session")

    def test_a_number_alone_still_opens_a_door_that_has_no_id(self):
        got = _run(SHELF, "_sessionDossier(2);")
        self.assertEqual(got["html"], "DOSSIER s_200_2")

    def test_an_id_the_shelf_does_not_hold_opens_nothing(self):
        got = _run(SHELF, "_sessionDossier(2, 's_999_9');")
        self.assertTrue(got["hidden"], "an unknown id fell back to a neighbour by number: %r" % got)

    def test_a_route_that_hands_an_id_as_its_target_opens_it(self):
        got = _run(SHELF, "_sessionDossier('s_300_3');")
        self.assertEqual(got["html"], "DOSSIER s_300_3")


class EveryDoorPassesTheIdItCarries(unittest.TestCase):

    def test_the_cards_pass_their_id(self):
        code = _code()
        for call in ("_sessionDossier(Number(hi.dataset.n) || 1, hi.dataset.sid || '')",
                     "_sessionDossier(Number(c.dataset.n) || 1, c.dataset.sid || '')",
                     "_sessionDossier(Number(c.dataset.hn) || 1, c.dataset.sid || '')"):
            self.assertEqual(code.count(call), 1, "a door opens by number alone again: %s" % call)

    def test_the_rerenders_keep_the_session_they_show(self):
        code = _code()
        self.assertEqual(code.count("_sessionDossier(DOSSIER.n);"), 0, "a re-render opens by number alone")
        self.assertGreaterEqual(code.count("_sessionDossier(DOSSIER.n, DOSSIER.sid)"), 3)

    def test_every_highlight_card_carries_its_id(self):
        code = _code()
        self.assertIn("data-sid=\"' + esc(sid || '') + '\"", code, "the highlight card template carries no id")
        for who in ("bGrail", "bReads", "bRph", "bCov"):
            # v3902 (REG-3768) - a card may also hand its tooltip after the id: "<x>.n, <x>.sid, _shRunTip(<x>)))"
            n = code.count("%s.n, %s.sid))" % (who, who)) + code.count("%s.n, %s.sid, _shRunTip(%s)))" % (who, who, who))
            self.assertEqual(n, 1, "%s's card is painted without its id" % who)


RED_PROOF = [
    {"why": "#135 - the dossier looks the NUMBER up again, whatever id it was handed (pick 28 -> 175)",
     "file": "control_ui.html",
     "find": "    if (sid){ for (var j = 0; j < list.length; j++){ if (list[j] && list[j].sessionId === sid){",
     "replace": "    if (false){ for (var j = 0; j < list.length; j++){ if (list[j] && list[j].sessionId === sid){",
     "matches": 1},
    {"why": "#135 - an id the shelf does not hold falls back to a neighbour by number",
     "file": "control_ui.html",
     "find": "    if (!sm && !sid){ for (var i = 0; i < list.length; i++){",
     "replace": "    if (!sm){ for (var i = 0; i < list.length; i++){",
     "matches": 1},
    {"why": "#135 - the shelf card opens by number alone again",
     "file": "control_ui.html",
     "find": "      _sessionDossier(Number(c.dataset.n) || 1, c.dataset.sid || '');",
     "replace": "      _sessionDossier(Number(c.dataset.n) || 1);",
     "matches": 1},
    {"why": "#135 - the Best run card is painted without its id",
     "file": "control_ui.html",
     "find": "bGrail.n, bGrail.sid, _shRunTip(bGrail)));",
     "replace": "bGrail.n, null, _shRunTip(bGrail)));",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
