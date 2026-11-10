# -*- coding: utf-8 -*-
"""v3895 (REG-3640) - THE FLEET LAMP IS A MOOD RING.

Elad 11-10: each connection-health problem gets its own color, no guessing, and the lamp is not
the eyes. Green = online, the background console is alive, checking in on time. Teal = check-ins
are late (older than fleet_presence.FRESH_UNTIL_S, not yet past STALE_AFTER_S). Yellow = waiting
on an update (this PC's running ver is older than live st.ver). Orange = waiting on an import.
Pink = low on memory. Red = offline, nothing heard past STALE_AFTER_S. Grey = a just-added PC
that has never sent a first report. When several are true, the worst wins (red, then pink,
orange, yellow, teal, green) and the hover lists every condition that is true. A missing field
is said UNKNOWN in the hover; the lamp falls back to the next known state and never invents one.
Recorder-only and "recording" belong to the middle eye and do not color the lamp.

The Fleet help (?) names each color, the worst-wins order, that hover lists every condition, and
keeps the eyes accurate: the middle eye is lit only while a real session records; the third eye
is dark until the console window is open.

Drives the page's own _fleetLamp / _fleetHelpHtml in node, with presence stamps from
fleet_presence.presence_of. RED_PROOF below.
"""
import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from console_safe import enable; enable()

import fleet_presence as FP
from test_the_fleet_card_says_how_each_pc_films_and_drains import (  # noqa: E402
    NOW as UI_NOW, UI, _iso, _run as _ui_run,
)

HEX = {
    "ok": "#8fe6a0",
    "teal": "#3ecfc9",
    "yellow": "#f0d35a",
    "orange": "#f08a3a",
    "pink": "#f07aa8",
    "red": "#c9402e",
    "unk": "#7a7672",
}

LIVE = "v3894"
HERE_VER = "v3894"
OLD_VER = "v3890"

PROOF_NEEDS = ["../tv/control_ui.html", "../tv/fleet_presence.py"]

RED_PROOF = [
    {
        "why": "REG-3640 - offline (red) is painted green",
        "file": "control_ui.html",
        "find": "  .fleet-dot.red    { background: #c9402e; box-shadow: 0 0 8px rgba(201, 64, 46, .85); }\n",
        "replace": "  .fleet-dot.red    { background: #8fe6a0; box-shadow: 0 0 8px rgba(143, 230, 160, .9); }\n",
        "matches": 1,
    },
    {
        "why": "REG-3640 - the lamp loses its hover, so the conditions cannot be read",
        "file": "control_ui.html",
        "find": "    return '<span class=\"fleet-dot ' + cls + '\" title=\"' + escC(tip) + '\" role=\"img\" aria-label=\"' + escC(tip) + '\"></span>';\n",
        "replace": "    return '<span class=\"fleet-dot ' + cls + '\"></span>';\n",
        "matches": 1,
    },
    {
        "why": "REG-3640 - a late check-in (teal) is treated as still on time, so teal never wins",
        "file": "control_ui.html",
        "find": "      } else if (ageS > freshUntil) {\n        conds.push({ cls: 'teal', say: 'check-ins are late' + _fleetLampHeard(ageS) });\n",
        "replace": "      } else if (false && ageS > freshUntil) {\n        conds.push({ cls: 'teal', say: 'check-ins are late' + _fleetLampHeard(ageS) });\n",
        "matches": 1,
    },
    {
        "why": "REG-3640 - pink no longer beats orange, so the worst color does not win",
        "file": "control_ui.html",
        "find": "    var rank = { red: 0, pink: 1, orange: 2, yellow: 3, teal: 4, ok: 5, unk: 6 };\n",
        "replace": "    var rank = { red: 0, orange: 1, pink: 2, yellow: 3, teal: 4, ok: 5, unk: 6 };\n",
        "matches": 1,
    },
    {
        "why": "REG-3640 - the Fleet help drops the worst-wins order",
        "file": "control_ui.html",
        "find": "    return '<div class=\"fh-sec\"><b>The lamp</b> is this PC\\'s connection. One color at a time; the worst one wins (red, then pink, orange, yellow, teal, green). Hover the lamp to see every condition that is true.</div>'\n",
        "replace": "    return '<div class=\"fh-sec\"><b>The lamp</b> is this PC\\'s connection.</div>'\n",
        "matches": 1,
    },
]


def _heart(key=None, why="", importing=None):
    h = {"census": "current"}
    if key:
        h["key"] = key
    if why:
        h["why"] = why
    if importing is not None:
        h["importing"] = importing
    return {"tree": "ok", "reels": 1, "river": {"heart": h}}


def _row(console_ago_s=None, recorder_ago_s=None, ver=HERE_VER, listed=True, system=None):
    row = {"nickname": "Box", "machine": "box-1", "ver": ver}
    if console_ago_s is not None:
        row["t"] = _iso(UI_NOW - int(console_ago_s * 1000))
    if recorder_ago_s is not None:
        row["recorder"] = {"alive": True, "t": _iso(UI_NOW - int(recorder_ago_s * 1000))}
    if system is not None:
        row["system"] = system
    else:
        row["system"] = _heart()
    row["presence"] = FP.presence_of(row, listed, UI_NOW)
    return row


def _lamp(row, listed=True, live=LIVE):
    return _ui_run(
        "var p = _fleetPresence(%s, %s, NOW); var h = _fleetLamp(%s, p, %s, %s); OUT.h = h;"
        " var m = /fleet-dot ([a-z]+)/.exec(h); OUT.cls = m ? m[1] : null;"
        " var t = /title=\"([^\"]*)\"/.exec(h); OUT.title = t ? t[1] : null;"
        % (json.dumps(row), "true" if listed else "false", json.dumps(row),
           "true" if listed else "false", json.dumps(live))
    )


class TheLampIsAMoodRing(unittest.TestCase):

    def test_each_color_is_pinned_and_glows(self):
        src = UI
        for cls, hx in HEX.items():
            needle = ".fleet-dot.%s" % cls
            self.assertIn(needle, src, "the %s lamp rule is gone" % cls)
            start = src.find(needle)
            chunk = src[start:src.find("}", start) + 1]
            self.assertIn(hx, chunk, "%s is not %s: %r" % (cls, hx, chunk))
            self.assertIn("box-shadow:", chunk, "%s has no glow" % cls)
        self.assertIn("transition: background-color .5s ease, box-shadow .5s ease, border-color .5s ease;", src,
                      "the lamp does not shift color like a mood ring")
        self.assertNotIn(".fleet-dot.rec {", src, "recorder-only amber is still a lamp color")
        self.assertNotIn(".fleet-dot.silent {", src, "the retired silent class is still painted")

    def test_green_is_online_on_time_and_nothing_else(self):
        got = _lamp(_row(console_ago_s=40))
        self.assertEqual(got["cls"], "ok", got)
        self.assertIn("online, the background console is alive, and it is checking in on time", got["title"])
        self.assertNotIn("UNKNOWN", got["title"] or "")
        self.assertNotIn("late", got["title"] or "")

    def test_teal_is_a_late_check_in_not_yet_offline(self):
        self.assertEqual(FP.FRESH_UNTIL_S, FP.BEACON_S + 60)
        self.assertLess(FP.FRESH_UNTIL_S, FP.STALE_AFTER_S)
        late = _lamp(_row(console_ago_s=FP.FRESH_UNTIL_S + 30))
        self.assertEqual(late["cls"], "teal", late)
        self.assertIn("check-ins are late", late["title"])
        self.assertNotIn("offline", late["title"] or "")
        still = _lamp(_row(console_ago_s=FP.FRESH_UNTIL_S))
        self.assertEqual(still["cls"], "ok", still)
        edge = _lamp(_row(console_ago_s=FP.STALE_AFTER_S))
        self.assertEqual(edge["cls"], "teal", "exactly at the offline bar must still be late, not red: %r" % edge)
        self.assertNotIn("offline", edge["title"] or "")
        gone = _lamp(_row(console_ago_s=FP.STALE_AFTER_S + 1))
        self.assertEqual(gone["cls"], "red", gone)
        self.assertIn("offline", gone["title"])

    def test_yellow_orange_pink_red_and_grey_each_have_their_field(self):
        yel = _lamp(_row(console_ago_s=40, ver=OLD_VER), live=LIVE)
        self.assertEqual(yel["cls"], "yellow", yel)
        self.assertIn("waiting on an update", yel["title"])
        self.assertIn("runs v3890", yel["title"])
        self.assertIn("live is v3894", yel["title"])
        ora = _lamp(_row(console_ago_s=40, system=_heart(importing={"done": 1, "of": 9, "ver": "v3894"})))
        self.assertEqual(ora["cls"], "orange", ora)
        self.assertIn("waiting on an import", ora["title"])
        first = _lamp(_row(console_ago_s=40, system=_heart(key="aside-cooldown", why="stood aside for GitHub's import")))
        self.assertEqual(first["cls"], "orange", first)
        pink = _lamp(_row(console_ago_s=40, system=_heart(key="low-memory", why="only 691 MB of memory left")))
        self.assertEqual(pink["cls"], "pink", pink)
        self.assertIn("low on memory", pink["title"])
        aside = _lamp(_row(console_ago_s=40,
                           system=_heart(key="aside-cooldown", why="a proof stood aside (only 691 MB of memory left)")))
        self.assertEqual(aside["cls"], "pink", aside)
        red = _lamp(_row(console_ago_s=40 * 60))
        self.assertEqual(red["cls"], "red", red)
        grey = _lamp(_row(console_ago_s=None))
        self.assertEqual(grey["cls"], "unk", grey)
        self.assertIn("never sent a first report", grey["title"])

    def test_the_worst_color_wins_and_the_hover_lists_every_condition(self):
        # late + import + low memory + old version: pink wins; hover lists all four
        row = _row(console_ago_s=FP.FRESH_UNTIL_S + 30, ver=OLD_VER,
                   system=_heart(key="low-memory", why="only 691 MB of memory left",
                                 importing={"done": 1, "of": 9, "ver": "v3894"}))
        got = _lamp(row, live=LIVE)
        self.assertEqual(got["cls"], "pink", got)
        title = got["title"] or ""
        for phrase in ("low on memory", "waiting on an import", "waiting on an update", "check-ins are late"):
            self.assertIn(phrase, title, "hover dropped %r: %r" % (phrase, title))
        self.assertLess(title.index("low on memory"), title.index("waiting on an import"))
        self.assertLess(title.index("waiting on an import"), title.index("waiting on an update"))
        self.assertLess(title.index("waiting on an update"), title.index("check-ins are late"))
        # the same row, but past the offline bar: red wins, teal is not also claimed
        dead = _row(console_ago_s=FP.STALE_AFTER_S + 30, ver=OLD_VER,
                    system=_heart(key="low-memory", why="only 691 MB of memory left",
                                  importing={"done": 1, "of": 9, "ver": "v3894"}))
        gone = _lamp(dead, live=LIVE)
        self.assertEqual(gone["cls"], "red", gone)
        t2 = gone["title"] or ""
        self.assertIn("offline", t2)
        self.assertIn("low on memory", t2)
        self.assertIn("waiting on an import", t2)
        self.assertIn("waiting on an update", t2)
        self.assertNotIn("check-ins are late", t2)

    def test_a_recorder_lease_does_not_color_the_lamp(self):
        rec = _lamp(_row(console_ago_s=40 * 60, recorder_ago_s=30))
        self.assertEqual(rec["cls"], "red", "the recorder kept the lamp from going red: %r" % rec)
        self.assertIn("offline", rec["title"])
        self.assertNotIn("recorder", rec["title"] or "")
        self.assertNotIn("recording", rec["title"] or "")
        # a fresh console with a recorder rolling is still green — the middle eye speaks for the reel
        up = _lamp(_row(console_ago_s=40, recorder_ago_s=20))
        self.assertEqual(up["cls"], "ok", up)

    def test_a_missing_field_is_unknown_and_falls_back(self):
        # no live version: do not invent yellow; stay green and say so
        got = _lamp(_row(console_ago_s=40, ver=OLD_VER), live="")
        self.assertEqual(got["cls"], "ok", got)
        self.assertIn("version UNKNOWN", got["title"])
        self.assertNotIn("waiting on an update", got["title"] or "")
        # no system/heart: do not invent pink or orange
        bare = _row(console_ago_s=40)
        del bare["system"]
        bare["presence"] = FP.presence_of(bare, True, UI_NOW)
        miss = _lamp(bare, live=LIVE)
        self.assertEqual(miss["cls"], "ok", miss)
        self.assertIn("import UNKNOWN", miss["title"])
        self.assertIn("memory UNKNOWN", miss["title"])
        self.assertNotIn("waiting on an import", miss["title"] or "")
        self.assertNotIn("low on memory", miss["title"] or "")
        # thresholds stripped from the stamp: do not invent teal or red
        row = _row(console_ago_s=40)
        row["presence"] = dict(row["presence"], staleAfterS=None, freshUntilS=None)
        unk = _lamp(row, live=LIVE)
        self.assertIn("check-in timing UNKNOWN", unk["title"])
        self.assertNotEqual(unk["cls"], "red", unk)
        self.assertNotEqual(unk["cls"], "teal", unk)
        # a clock the card cannot read is not "never sent a first report"
        future = _row(console_ago_s=-600)
        bad = _lamp(future, live=LIVE)
        self.assertNotIn("never sent a first report", bad["title"] or "")
        self.assertIn("UNKNOWN", bad["title"] or "")

    def test_the_fleet_help_names_the_lamp_and_the_eyes(self):
        html = _ui_run("OUT.h = _fleetHelpHtml();")["h"]
        self.assertIn("The lamp", html)
        self.assertIn("the worst one wins (red, then pink, orange, yellow, teal, green)", html)
        self.assertIn("Hover the lamp to see every condition that is true", html)
        for word, meaning in (
            ("Green", "checking in on time"),
            ("Teal", "check-ins are late"),
            ("Yellow", "waiting on an update"),
            ("Orange", "waiting on an import"),
            ("Pink", "low on memory"),
            ("Red", "nothing heard for a long time"),
            ("Grey", "has not sent its first report yet"),
        ):
            self.assertIn(word, html, word)
            self.assertIn(meaning, html, meaning)
        self.assertIn("The middle eye", html)
        self.assertIn("lit only while a real session records", html)
        self.assertIn("The third eye", html)
        self.assertIn("dark until the console window is open", html)
        src = UI
        self.assertIn('id="fleet-help-btn"', src)
        self.assertIn("what the lamp and the eyes mean", src)
        self.assertIn('id="fleet-help"', src)
        # the eyes themselves are unchanged: middle eye dark until a reel records; third eye dark until open
        self.assertIn("st = sh.recording ? 'live' : 'dark';", src)
        self.assertIn(".fleet-winview.wv-off .sh-lid { stroke: #6b5a48; }", src)
        self.assertIn(".fleet-shadow.st-dark .sh-lid { stroke: #6b5a48; }", src)
        self.assertIn(".fleet-shadow.st-live .sh-lid { stroke: #6df0a0; }", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
