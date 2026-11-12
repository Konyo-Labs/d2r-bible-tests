# -*- coding: utf-8 -*-
"""REG-1757 — THE SHELF OPENS ON THE LIST, AND A REEL DOES NOT BORROW ANOTHER.

GrokBot's ALT pass: the shelf's first paint was a theatre session (whichever was opened
last), an empty reel toasted that it had opened a different session and played that one,
and the dossier called journal rows "frames" beside a theatre that counts photos.

The door sets TH.shelfAsDoor and calls thOpen with no argument — the refusal law reads
that exact call. thOpen returns before thLoadSession on that path. Last session, the
button inside the shelf, asks thPickEntrySession, the same pick as the Theatre button,
not whichever dossier happens to be open.

An empty reel stays on the session he asked for. The dossier names film frames or journal
rows. It has a close that dismisses, the same function as the back label. The read panel
and the frame's inset are one width, and the panel does not open itself. The station tabs
touch, so a press between them hits a tab.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable
enable()

UI = os.path.join(HERE, "control_ui.html")
NODE = shutil.which("node")


def _body(src, sig):
    """The brace-bounded body that starts at the one occurrence of sig."""
    if src.count(sig) != 1:
        raise AssertionError("%r occurs %d times — this guard cannot see its subject"
                             % (sig, src.count(sig)))
    i = src.index(sig)
    b = src.index("{", i)
    depth, j = 0, b
    while j < len(src):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[b:j + 1]
        j += 1
    raise AssertionError("could not bound %r — harness fault, not a pass" % sig)


class TheShelfOpensOnTheList(unittest.TestCase):

    def setUp(self):
        with io.open(UI, encoding="utf-8") as fh:
            self.src = fh.read()

    def test_the_shelf_door_returns_before_a_session(self):
        # the #231 eye on v3570: the first TEXTUAL thLoadSession was read, so a comment naming it above the door
        # would have moved the anchor - the comments are cut first
        body = _code_only(_body(self.src, "async function thOpen(){"))
        self.assertIn("TH.shelfAsDoor = false", body,
                      "thOpen does not clear the shelf request, so the next open inherits it")
        door = body.find("if (_shelfDoor)")
        load = body.find("thLoadSession")
        self.assertGreater(door, 0, "the shelf path is gone from thOpen, so the door loads a session")
        self.assertGreater(load, door, "thLoadSession runs before the shelf return")
        self.assertIn("return;", body[door:load])

    def test_the_sessions_routing_stays_inside_the_spec_read(self):
        """v1612 reads the first 1600 characters of thOpen. The shelf flag stays below that."""
        i = self.src.index("async function thOpen()")
        sessions = self.src.index("data-view') === 'sessions'", i)
        route = self.src.index("window._toTVD()", i)
        clear = self.src.index("TH.shelfAsDoor = false", i)
        self.assertLessEqual(sessions - i, 1550,
                             "the Sessions check starts past the 1600 characters v1612 reads")
        self.assertLessEqual(route + len("window._toTVD()") - i, 1600,
                             "_toTVD is not inside the 1600 characters v1612 reads")
        self.assertGreater(clear, route,
                           "clearing the shelf flag above the Sessions routing pushes that routing out of the read")

    def test_the_door_asks_and_still_calls_thOpen(self):
        self.assertEqual(self.src.count("TH.shelfAsDoor = true; await thOpen();"), 1,
                         "the shelf door no longer both asks for the list and calls thOpen()")
        self.assertEqual(self.src.count("if (!TH.open && !openErr) return"), 1)

    def test_last_session_uses_the_theatre_pick(self):
        self.assertEqual(self.src.count('id="sh-last-session"'), 1)
        i = self.src.index('id="sh-last-session"')
        end = self.src.index(">", i)
        # the #231 eye on v3572: the slice started AT id=, so an onclick written before the id was outside it
        tag = self.src[self.src.rindex("<", 0, i):end]
        self.assertIn('onclick="window._shelfLastSession()"', tag)
        self.assertNotIn("_dossierToTheatre", tag)
        body = _body(self.src, "window._shelfLastSession = async function(){")
        self.assertIn("thPickEntrySession", body,
                      "Last session does not ask the Theatre button's pick")
        self.assertNotIn("DOSSIER", body,
                         "Last session follows the open dossier, which is a different session")

    def test_an_empty_reel_stays_itself(self):
        body = _body(self.src, "async function thLoadSession(")
        self.assertIn("has no film yet", body)
        self.assertNotIn("return thLoadSession", body)
        self.assertNotIn("opened session", body)
        self.assertEqual(self.src.count("return thLoadSession"), 0)
        self.assertEqual(self.src.count("opened session"), 0)

    def test_the_dossier_names_the_count(self):
        self.assertEqual(self.src.count("tile(_frameNoun, _frames)"), 1)
        self.assertIn("'film frames'", self.src)
        self.assertIn("'journal rows'", self.src)

    def test_the_dossier_has_a_close(self):
        self.assertEqual(self.src.count('id="dsr-x"'), 1)
        i = self.src.index('id="dsr-x"')
        end = self.src.index(">", i)
        self.assertIn('onclick="window._dossierClose()"', self.src[self.src.rindex("<", 0, i):end])

    def test_the_read_panel_and_the_frame_are_one_width(self):
        # #210 (v3903, the clean theatre) - while the panel is open the caption bar takes the same inset as the frame, so the
        # one width now appears three times: the panel's width, the frame's inset and the caption's inset
        self.assertEqual(self.src.count("min(280px, 30%)"), 3,
                         "the drawer, the frame inset and the caption inset drifted apart, or the panel grew back")
        self.assertEqual(self.src.count("width: min(280px, 30%)"), 1)
        self.assertEqual(self.src.count("right: min(280px, 30%)"), 2)
        self.assertEqual(self.src.count("min(380px, 44%)"), 0)

    def test_the_read_panel_does_not_open_itself(self):
        self.assertEqual(self.src.count("else CARD.autoArmed = false;"), 1)
        self.assertEqual(self.src.count("catch (e) { CARD.autoArmed = false; }"), 1)
        self.assertEqual(self.src.count("CARD.autoArmed = true"), 0)
        self.assertNotIn("pref !== 'closed'", self.src)

    def test_a_press_between_station_tabs_hits_a_tab(self):
        self.assertEqual(
            self.src.count(".sh-stationbar { display: flex; align-items: center; flex-wrap: wrap; gap: 0;"),
            1)
        self.assertEqual(self.src.count(".sh-stationbar > .sh-chip { padding: 8px 16px; }"), 1)


def _fn_text(src, sig):
    """The whole function (header + brace-bounded body) at the one occurrence of sig, or None when absent."""
    if src.count(sig) == 0:
        return None
    i = src.index(sig)
    return src[i:src.index("{", i)] + _body(src, sig)


def _code_only(text):
    """JavaScript with its /* */ and // comments cut (the bodies cut here carry no '//' inside a string)."""
    import re
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return "\n".join(l.split("//", 1)[0] for l in text.split("\n"))


_STUBS = r"""
var LOG = [], store = {}, ELS = {};
var localStorage = { getItem: function(k){ return store[k] === undefined ? null : store[k]; },
                     setItem: function(k, v){ store[k] = String(v); } };
function _el(id){ return { id: id, hidden: true, textContent: '', style: {},
                           classList: { add: function(){}, remove: function(){}, toggle: function(){},
                                        contains: function(){ return false; } } }; }
function $(id){ return ELS[id] || (ELS[id] = _el(id)); }
var document = { getElementById: function(id){ return $(id); },
                 body: { getAttribute: function(){ return null; }, removeAttribute: function(){},
                         classList: { add: function(){}, remove: function(){}, contains: function(){ return false; } } } };
var window = {};
var TH = { sessions: [], open: false };
var CARD = { open: false, autoArmed: true };
function toast(m){ LOG.push('toast:' + m); }
function thCardToggle(){ CARD.open = !CARD.open; LOG.push('cardToggle'); }
function thClose(){ TH.open = false; LOG.push('close'); }
function thShelf(f){ LOG.push('shelf'); }
function thLit(){} function thArtInit(){} function thRibbon(){} function thCoachOnce(){}
function thModePill(){} function thFilter(b){ return b; } function thClock(){} function thBuildAxis(){}
function thTimeline(){} function thPaint(){} function thSessionPhotoStats(){ return {}; } function thToast(){}
var FETCH = {};
function fetch(url){ var body = FETCH[String(url).split('?')[0]];
  return Promise.resolve({ json: function(){ return Promise.resolve(body); } }); }
function _done(extra){ process.stdout.write(JSON.stringify(Object.assign({ log: LOG, cardOpen: CARD.open }, extra || {}))); }
"""


def _drive(src, names, scenario, extra_stubs=""):
    """Run the named functions of `src` (the real control_ui.html text) in node over the stubs above. -> dict"""
    fns = []
    for sig in names:
        t = _fn_text(src, sig)
        if t is not None:
            fns.append(t)
    prog = _STUBS + extra_stubs + "\n" + "\n".join(fns) + "\n" + scenario
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("node failed: %s" % (r.stderr[-600:] or r.stdout[-600:]))
    return json.loads(r.stdout)


# REG-2790 - the strict pick asks _lastSessionRow (the one "last session" the home digest names too), so it rides along
# REG-2811 - and the sentence both doors say when that run has nothing to play
_LAST = ["function _lastSessionRow(", "function _lastSessionNoFilmSay(", "function thPickEntrySession(",
         "window._shelfLastSession = async function(){"]
# REG-2698 - thOpen's /api/sessions wait is thSessionsWait now; it rides with thOpen, and so do its two bounds (_bounds)
_OPEN = ["async function thOpen(){", "async function thSessionsWait(", "async function thLoadSession(",
         "function thApplyCardPref(){", "function _lastSessionRow(", "function _lastSessionNoFilmSay(",
         "function thPickEntrySession(",
         # GrokBot v3817 - the wait shares one /api/sessions request in flight (_sessionsJson over _sessionsFetchOnce)
         "async function _sessionsFetchOnce(", "function _sessionsJson("]


def _bounds(src):
    """The page's own TH_SESSIONS_BOUND_MS / TH_SLOW_SAY_MS line, never a copy of its numbers. [[copy-drift]]"""
    for line in src.split("\n"):
        if line.startswith("  var TH_SESSIONS_BOUND_MS = "):
            return line.strip() + "\n"
    raise AssertionError("PREMISE: the sessions wait's bounds moved - re-point this harness")
_TOGGLE = ["function _thShelfWasTheDoor(){", "function thShelfToggle(){"]


def last_session_with_no_film(src):
    return _drive(src, _LAST, "TH.sessions = [{n: 5, frames: 0, footageN: 0}, {n: 6, stub: true}];\n"
                              "window._shelfLastSession().then(function(){ _done(); });",
                  extra_stubs="function thLoadSession(n, e){ LOG.push('load:' + n); }\n"
                              "async function thOpen(){ LOG.push('open'); }\n")


def last_session_when_the_theatre_will_not_open(src):
    return _drive(src, _LAST, "TH.sessions = [];\nwindow._shelfLastSession().then(function(){ _done(); });",
                  extra_stubs="function thLoadSession(n, e){ LOG.push('load:' + n); }\n"
                              "async function thOpen(){ throw new Error('law: no stage'); }\n")


def a_reel_opened_from_the_shelf_door(src):
    return _drive(src, _OPEN, (
        "store['tvd_card_pref'] = 'open';\n"
        "FETCH['/api/sessions'] = { sessions: [{n: 7, frames: 3, footageN: 20, named: 1}] };\n"
        "FETCH['/api/session'] = { beats: [{frame: 'f_1790000000000.jpg', ts: 1}], sessionId: 's7' };\n"
        "TH.shelfAsDoor = true;\n"
        "(async function(){ await thOpen(); var atShelf = CARD.open; await thLoadSession(7);\n"
        "  _done({atShelf: atShelf}); })();"), extra_stubs=_bounds(src) + "var _sessFlight = null, API = '';\n")


def hiding_the_shelf(src, was_door):
    return _drive(src, _TOGGLE, (
        "ELS['th-shelfov'] = _el('th-shelfov'); ELS['th-shelfov'].hidden = false;\n"
        "TH.open = true; TH.shelfIsDoor = %s;\n"
        "if (typeof thShelfToggle === 'function') thShelfToggle(); else thShelf();\n"
        "_done({shelfHidden: ELS['th-shelfov'].hidden, theatreOpen: TH.open});") % ("true" if was_door else "false"))


@unittest.skipUnless(NODE, "no node on this machine - the shelf-door residue is UNMEASURED here, not passing")
class TheShelfDoorLeavesTheWayItCame(unittest.TestCase):
    """REG-1944 - the #231 eye on v3570. DRIVEN in node on the real control_ui.html functions. MEASURED on the
    shipped v3602 page before the fix: Last session with sessions but no film loaded session 1 ('load:1') instead of
    saying 'no session has film yet'; with a theatre that would not open it toasted 'no session has film yet'; a reel
    opened from the shelf door never got his saved read panel (cardOpen false with tvd_card_pref 'open'); and `s` or
    the stage's shelf button hid a shelf that WAS the door and left the theatre open on an empty stage."""

    def setUp(self):
        with io.open(UI, encoding="utf-8") as fh:
            self.src = fh.read()

    def test_last_session_with_no_film_says_so_and_loads_nothing(self):
        got = last_session_with_no_film(self.src)
        self.assertNotIn("load:1", got["log"], "Last session loaded 'session 1' onto an empty stage: %r" % got["log"])
        self.assertIn("toast:no session has film yet", got["log"])

    def test_a_theatre_that_will_not_open_is_not_called_no_film(self):
        got = last_session_when_the_theatre_will_not_open(self.src)
        self.assertNotIn("toast:no session has film yet", got["log"], "a failed open was reported as 'no film'")
        self.assertTrue(any(x.startswith("toast:the theatre could not open") for x in got["log"]), got["log"])

    def test_the_theatre_button_asks_the_same_run_as_last_session(self):
        """REG-2811 (his ruling 2026-10-28: "yea join same logic why not") - the Theatre button no longer keeps REG-1944's
        fallback to session 1: with nothing to play it answers 0, as Last session does, and with a run to play both name it."""
        out = _drive(self.src, ["function _lastSessionRow(", "function thPickEntrySession("],
                     "TH.sessions = [{n: 5, frames: 0}];\nvar a = {loose: thPickEntrySession(), strict: thPickEntrySession(true)};\n"
                     "TH.sessions = [{n: 3, frames: 2, footageN: 0}, {n: 4, footageN: 900, named: 6}];\n"
                     "_done({none: a, run: {loose: thPickEntrySession(), strict: thPickEntrySession(true)}});")
        self.assertEqual(out["none"], {"loose": 0, "strict": 0}, "a pick with nothing to play fell back to a session")
        self.assertEqual(out["run"], {"loose": 3, "strict": 3},
                         "the Theatre button and Last session name different runs: %r" % out["run"])

    def test_a_reel_opened_from_the_shelf_door_gets_his_saved_panel(self):
        got = a_reel_opened_from_the_shelf_door(self.src)
        self.assertFalse(got["atShelf"], "PREMISE: the shelf itself opens no panel")
        self.assertTrue(got["cardOpen"], "his saved 'open' read panel was not honoured on a reel from the shelf door")
        self.assertEqual(1, got["log"].count("cardToggle"))

    def test_hiding_a_shelf_that_was_the_door_closes_the_theatre(self):
        got = hiding_the_shelf(self.src, was_door=True)
        self.assertFalse(got["theatreOpen"], "hiding the door's shelf left an empty stage open: %r" % got)
        self.assertTrue(got["shelfHidden"])
        kept = hiding_the_shelf(self.src, was_door=False)
        self.assertTrue(kept["theatreOpen"], "a shelf opened over a reel took the reel with it")

    def test_both_toggles_ask_the_door_rule(self):
        # whole statements on their own line - a comment that quotes one is not the statement
        lines = [l.strip() for l in self.src.split("\n")]
        self.assertEqual(1, lines.count("$('th-shelf').onclick = function(){ thShelfToggle(); };"),
                         "the stage's shelf button toggles the shelf bare")
        self.assertEqual(1, lines.count("else if (e.key === 's' || e.key === 'S'){ thShelfToggle(); e.preventDefault(); }"),
                         "the s key toggles the shelf bare")


RED_PROOF = [
    {"why": "REG-1944 - Last session's pick falls back to session 1 again, so 'no session has film yet' is unreachable",
     "file": "control_ui.html",
     "find": "    var pick = (typeof thPickEntrySession === 'function') ? thPickEntrySession(true) : 0;\n",
     # REG-2811 re-aimed: the loose pick answers the same run now, so the sabotage restores the fallback itself
     "replace": "    var pick = (typeof thPickEntrySession === 'function') ? (thPickEntrySession(true) || 1) : 0;\n",
     "matches": 1},
    {"why": "REG-1944 - a theatre that would not open is toasted as 'no session has film yet'",
     "file": "control_ui.html",
     "find": "      try { toast('the theatre could not open (' + String(e && e.message || e).slice(0, 80) + ')'); } catch (e3) {}\n"
             "      return;\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-1944 - a reel opened from the shelf door never gets his saved read panel",
     "file": "control_ui.html",
     "find": "    if (TH.cardPrefOwed) { TH.cardPrefOwed = false; thApplyCardPref(); }",
     "replace": "",
     "matches": 1},
    {"why": "REG-1944 - hiding a shelf that was the door leaves an empty stage open",
     "file": "control_ui.html",
     "find": "    if (ov && !ov.hidden && _thShelfWasTheDoor()) {\n",
     "replace": "    if (false) {\n",
     "matches": 1},
    {"why": "REG-1944 - the s key toggles the shelf bare again",
     "file": "control_ui.html",
     "find": "else if (e.key === 's' || e.key === 'S'){ thShelfToggle(); e.preventDefault(); }",
     "replace": "else if (e.key === 's' || e.key === 'S'){ thShelf(); e.preventDefault(); }",
     "matches": 1},
    {"why": "REG-1757 - the shelf door loads a session again",
     "file": "control_ui.html",
     "find": "    if (_shelfDoor) {\n"
             "      try { $('th-caption').textContent = 'the shelf'; } catch (e) {}\n"
             "      TH.cardPrefOwed = true;   // REG-1944 - the first reel he opens from this shelf gets his saved panel\n"
             "      thLit();\n"
             "      return;\n"
             "    }\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-1757 - the shelf button opens the theatre without asking for the list",
     "file": "control_ui.html",
     "find": "TH.shelfAsDoor = true; await thOpen();",
     "replace": "await thOpen();",
     "matches": 1},
    {"why": "REG-1757 - an empty reel opens a different session",
     "file": "control_ui.html",
     "find": "    if (!framed){\n"
             "      $('th-caption').textContent = '🎞 session ' + n + ' has no film yet — nothing else was opened';\n"
             "      TH.sn = n; TH.beats = []; TH.allBeats = []; TH.sessionId = j.sessionId || '';\n",
     # REG-2135 grew this branch (it now clears the last reel's frame and line), so the tamper anchors on its head
     # and puts the old hop to another session first - everything after that return is dead, as in the defect.
     "replace": "    if (!framed){\n"
                "      return thLoadSession(alt2, isEntry);\n",
     "matches": 1},
    {"why": "REG-1757 - the dossier calls both counts frames",
     "file": "control_ui.html",
     "find": "tile(_frameNoun, _frames)",
     "replace": "tile('frames', _frames)",
     "matches": 1},
    {"why": "REG-1757 - Last session plays the open dossier",
     "file": "control_ui.html",
     "find": 'onclick="window._shelfLastSession()"',
     "replace": 'onclick="window._dossierToTheatre()"',
     "matches": 1},
    {"why": "REG-1757 - the dossier close is gone",
     "file": "control_ui.html",
     "find": "               + (_onShelf ? 'back to the shelf' : 'back') + '</button>'\n"
             "               + '<button type=\"button\" class=\"dsr-x\" id=\"dsr-x\" title=\"close this dossier\" '\n"
             "               + 'onclick=\"window._dossierClose()\">\\u2715</button></div>';\n",
     "replace": "               + (_onShelf ? 'back to the shelf' : 'back') + '</button></div>';\n",
     "matches": 1},
    {"why": "REG-1757 - the read panel grows back and no longer matches the frame",
     "file": "control_ui.html",
     "find": "width: min(280px, 30%);",
     "replace": "width: min(380px, 44%);",
     "matches": 1},
    {"why": "REG-1757 - the frame inset stays wide after the panel was narrowed",
     "file": "control_ui.html",
     "find": "#theatre.card-open .th-film { right: min(280px, 30%)",
     "replace": "#theatre.card-open .th-film { right: min(380px, 44%)",
     "matches": 1},
    {"why": "REG-1757 - a session with no saved preference opens the read panel on the first named beat",
     "file": "control_ui.html",
     "find": "else CARD.autoArmed = false;",
     "replace": "else CARD.autoArmed = (pref !== 'closed');",
     "matches": 1},
    {"why": "REG-1757 - a failed preference read arms the read panel",
     "file": "control_ui.html",
     "find": "catch (e) { CARD.autoArmed = false; }",
     "replace": "catch (e) { CARD.autoArmed = true; }",
     "matches": 1},
    {"why": "REG-1757 - the gap between station tabs is a miss again",
     "file": "control_ui.html",
     "find": ".sh-stationbar { display: flex; align-items: center; flex-wrap: wrap; gap: 0;",
     "replace": ".sh-stationbar { display: flex; align-items: center; flex-wrap: wrap; gap: 6px;",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
