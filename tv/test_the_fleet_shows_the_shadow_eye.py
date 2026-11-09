# -*- coding: utf-8 -*-
"""#93 — EVERY PC ON THE FLEET CARRIES A SHADOW EYE, AND THE EYE IS WIRED TO WHETHER ITS READER WORKS.

His ask, 2026-09-30, over a screenshot of the fleet card: "a cool design added to it so i know and we know that the
SHADOW READER/background process is on even after closing the game out. it should still be there in the background in
the shadows" - "so a visual like online hidden eye... like glowing eye for the shadow reader to be on or off" -
"within the fleet that renders and connects to it visually if on/off.. that way we know if its working too".

FOUR JOINTS, each DRIVEN here through the shipped code (never re-implemented):
  1. THE CONSOLE - _shadow_for_wire(): his switch, local OCR and a reel rolling (_shadow_state, three facts kept apart
     since v2000) plus whether the shadow watcher is ALIVE - lane_liveness's own verdict for tvd-shadow-watch
     (FLOWING = working, LATE = stopped, never stamped = UNKNOWN), decided on that PC's own clock.
  2. THE BEACON - `shadow` rides every beacon beside `eye`.
  3. THE WORKER - the shaper keeps it (absent stays null) and a flip of on / available / recording / working is news,
     so a PC whose watcher stops is not left glowing for up to 15 min.
  4. THE CARD - _fleetShadowEye(row, online): lit (on + alive, the game may be closed) / live (reading now) / idle (on
     but not working) / off (switched off) / unk (offline, an older build, not stamped). UNKNOWN is never drawn lit or
     shut. The render gate photographs every state (render_check's fleet stub) and measures `.fleet-shadow` painted.
[[heart-first]] [[unknown-stays-unknown]] [[the-unjoined-end]] [[stale-reading]]
RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import control_app as ca  # noqa: E402
import lane_liveness as LL  # noqa: E402
import test_console_fleet as CF  # noqa: E402  the real worker handler over an in-memory KV
import test_the_picker_census_reaches_the_fleet as PK  # noqa: E402  its node runner and cutter, one copy
from test_the_fleet_card_says_how_each_pc_films_and_drains import _run as _ui_run, NOW as UI_NOW, _iso  # noqa: E402
import worker_source as _ws  # noqa: E402  REG-1839 - the worker's top-level helpers, lifted with the shaper

NODE = PK.NODE
API = os.path.join(ROOT, "functions", "api", "console.js")
UI = os.path.join(HERE, "control_ui.html")

PROOF_NEEDS = ["../functions/api/console.js", "../functions/_middleware.js"]

RED_PROOF = [
    {"why": "REG-2048 - the eye calls a row whose beacon the roster refused 'offline' again",
     "file": "tv/control_ui.html",
     "find": "        : (m && m.lastBeacon && m.lastBeacon.ok === false)\n",
     "replace": "        : false\n",
     "matches": 1},
    {
        "why": "#93 - a watcher that ticks inside its bound no longer reads as working",
        "file": "control_app.py",
        "find": "            if row.get(\"state\") == _ll.FLOWING:\n                working = True\n",
        "replace": "            if row.get(\"state\") == _ll.FLOWING:\n                working = False\n",
        "matches": 1,
    },
    {
        "why": "#93 - the beacon stops carrying the shadow reader",
        "file": "control_app.py",
        "find": "            \"shadow\": _shadow_for_wire(),\n",
        "replace": "            \"shadow\": None,\n",
        "matches": 1,
    },
    {
        "why": "v3890 (#189) - the lamp lights green for the recorder alone, the console process down",
        "file": "tv/control_ui.html",
        "find": "    } else if (pres.state === 'here' && p && p.via === 'recorder') {\n",
        "replace": "    } else if (false) {\n",
        "matches": 1,
    },
    {
        "why": "v3890 (#189) - the lamp loses its hover: nobody can read which state it is in",
        "file": "tv/control_ui.html",
        "find": "    return '<span class=\"fleet-dot' + cls + '\" title=\"' + escC(tip) + '\" role=\"img\" aria-label=\"' + escC(tip) + '\"></span>';\n",
        "replace": "    return '<span class=\"fleet-dot' + cls + '\"></span>';\n",
        "matches": 1,
    },
    {
        "why": "v3890 (#189) - the eye glows live for any rolling reel again, the idle page included",
        "file": "tv/control_ui.html",
        "find": "      st = (sh.recording && sh.game === true) ? 'live' : 'lit';\n",
        "replace": "      st = sh.recording ? 'live' : 'lit';\n",
        "matches": 1,
    },
    {
        "why": "v3890 (#189) - the worker drops whether the rolling reel shows the game",
        "file": "functions/api/console.js",
        "find": "        game: tri(s.game),   /* v3890 (#189) - the rolling reel's film shows D2R (null: not known / an older console) */\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "v3890 (#189) - the film leaving the game is not news, so the eye stays live for up to 15 min",
        "file": "functions/api/console.js",
        "find": "JSON.stringify([x.on, x.available, x.recording, x.working, x.game])",
        "replace": "JSON.stringify([x.on, x.available, x.recording, x.working])",
        "matches": 1,
    },
    {
        "why": "#93 - the worker's shaper drops whether the watcher works",
        "file": "functions/api/console.js",
        "find": "        on: s.on === true, available: tri(s.available), recording: s.recording === true, working: tri(s.working),\n",
        "replace": "        on: s.on === true, available: tri(s.available), recording: s.recording === true, working: null,\n",
        "matches": 1,
    },
    {
        "why": "#93 - a watcher that stops is not news: the eye keeps glowing for up to 15 min",
        "file": "functions/api/console.js",
        "find": "    || shadowNews(prev) !== shadowNews(rec)\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#93 - an OFFLINE PC keeps its last eye instead of UNKNOWN",
        "file": "control_ui.html",
        # REG-1833 - the branch's tip became offline-or-stale, so the anchor ends at `st = 'unk';`
        "find": "    if (!online) {\n      st = 'unk';\n",
        "replace": "    if (false) {\n      st = 'unk';\n",
        "matches": 1,
    },
    {
        "why": "#93 - a switched-OFF reader is drawn open",
        "file": "control_ui.html",
        "find": "    } else if (sh.on !== true) {\n",
        "replace": "    } else if (false) {\n",
        "matches": 1,
    },
    {
        "why": "#93 - a PC with no text reader glows although it cannot watch",
        "file": "control_ui.html",
        "find": "    } else if (sh.available === false) {\n",
        "replace": "    } else if (false) {\n",
        "matches": 1,
    },
    {
        "why": "#93 - an UNKNOWN watcher (not stamped yet) is drawn lit",
        "file": "control_ui.html",
        "find": "    } else if (sh.working === true) {\n",
        "replace": "    } else if (sh.working !== false) {\n",
        "matches": 1,
    },
    {
        "why": "#93 - the row stops drawing the eye beside the name (the helper stays, the join is gone)",
        "file": "control_ui.html",
        # 475f672e - the row passes `heard` (a presence key with a live pulse), not `online`; REG-1833 adds `pres`
        "find": "          + '<b>' + _fleetShadowEye(m, heard, undefined, pres) + _fleetWindowEye(m, heard) + escC(nameFor) + '</b>'   // v3885 - the green eye: its window is up\n",
        "replace": "          + '<b>' + _fleetWindowEye(m, heard) + escC(nameFor) + '</b>'\n",
        "matches": 1,
    },
    {
        "why": "REG-1833 - a key that outlived its pulse is called offline again (the helper ignores the presence answer)",
        "file": "control_ui.html",
        "find": "      tip = (pres && pres.state !== 'here')\n",
        "replace": "      tip = (false)\n",
        "matches": 1,
    },
    {
        "why": "REG-1833 - the row stops handing its presence answer to the eye, so a silent key reads offline again",
        "file": "control_ui.html",
        "find": "_fleetShadowEye(m, heard, undefined, pres) + _fleetWindowEye(m, heard)",
        "replace": "_fleetShadowEye(m, heard) + _fleetWindowEye(m, heard)",
        "matches": 1,
    },
    {
        "why": "v3885 (his 11-08) - a minimized console reads as a window up on its desktop (the second eye lies green)",
        "file": "control_ui.html",
        "find": "    } else if (wm === 'front' || wm === 'fullscreen') {\n",
        "replace": "    } else if (wm !== 'headless') {\n",
        "matches": 1, "needs": "node",
    },
    {
        "why": "v3885 (his 11-08) - a PC not heard is drawn with a window verdict",
        "file": "control_ui.html",
        "find": "    if (!heard || !wm) {\n      st = 'unk';",
        "replace": "    if (!wm) {\n      st = 'unk';",
        "matches": 1, "needs": "node",
    }
]


def _boom():
    raise RuntimeError("the switch file went away mid-read")


ARMED = {"ok": True, "on": True, "why": "the default", "available": True, "recording": False,
         "say": "armed - it starts watching when a reel is rolling"}


def _wire(state, rows):
    with mock.patch.object(ca, "_shadow_state", state if callable(state) else (lambda: state)), \
            mock.patch.object(LL, "rows", lambda now=None: rows):
        return ca._shadow_for_wire()


# ══ JOINT 1 — THE CONSOLE ═════════════════════════════════════════════════════════════════════════════════════════
class OneSourceOnThisPc(unittest.TestCase):

    def test_on_with_its_watcher_flowing_is_working_even_with_no_reel(self):
        w = _wire(ARMED, [{"lane": "tvd-shadow-watch", "state": LL.FLOWING, "tickAgeS": 7.0}])
        self.assertEqual((w["on"], w["available"], w["recording"], w["working"], w["beatAgeS"]),
                         (True, True, False, True, 7.0), w)
        self.assertIn("armed", w["why"])

    def test_a_late_watcher_is_stopped_and_an_unstamped_one_is_unknown(self):
        late = _wire(ARMED, [{"lane": "tvd-shadow-watch", "state": LL.LATE, "tickAgeS": 900.0}])
        self.assertIs(late["working"], False, late)
        self.assertEqual(late["beatAgeS"], 900.0)
        none = _wire(ARMED, [{"lane": "tvd-retention", "state": LL.FLOWING, "tickAgeS": 1.0}])
        self.assertIsNone(none["working"], "a watcher that never stamped read as %r, not UNKNOWN" % none["working"])
        unk = _wire(ARMED, [{"lane": "tvd-shadow-watch", "state": LL.UNKNOWN, "tickAgeS": None}])
        self.assertIsNone(unk["working"])

    def test_his_switch_off_is_off_and_an_unreadable_switch_posts_nothing(self):
        off = _wire(dict(ARMED, on=False), [{"lane": "tvd-shadow-watch", "state": LL.FLOWING, "tickAgeS": 3.0}])
        self.assertIs(off["on"], False)
        self.assertIsNone(_wire(_boom, []), "an unreadable switch posted a guessed shadow state")


# ══ JOINT 2 — THE BEACON ══════════════════════════════════════════════════════════════════════════════════════════
class TheBeaconCarriesIt(unittest.TestCase):

    def test_every_beacon_carries_the_shadow_reader(self):
        import urllib.request as _ur
        sent = {}

        def fake_urlopen(req, timeout=None):
            sent["body"] = json.loads(req.data.decode("utf-8"))

            class R(object):
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def read(self):
                    return b"{}"
            return R()
        saved_env = {k: os.environ.pop(k, None) for k in ("CI", "GITHUB_ACTIONS", "TVD_NO_BEACON")}
        bdir = tempfile.mkdtemp(prefix="shadow_beacon_")
        self.addCleanup(shutil.rmtree, bdir, True)
        self.addCleanup(setattr, ca, "_BEACON_STATE_PATH", ca._BEACON_STATE_PATH)
        ca._BEACON_STATE_PATH = os.path.join(bdir, ".tvd_beacon.json")
        try:
            with mock.patch.object(_ur, "urlopen", fake_urlopen), \
                    mock.patch.object(ca, "_shadow_state", lambda: dict(ARMED, recording=True)), \
                    mock.patch.object(LL, "rows", lambda now=None: [{"lane": "tvd-shadow-watch", "state": LL.FLOWING,
                                                                     "tickAgeS": 2.0}]):
                ca._console_beacon("hb")
        finally:
            for k, v in saved_env.items():
                if v is not None:
                    os.environ[k] = v
        sh = sent.get("body", {}).get("shadow")
        self.assertIsInstance(sh, dict, "the beacon carries no shadow reader: %r" % sorted(sent.get("body", {})))
        self.assertEqual((sh["on"], sh["recording"], sh["working"], sh["beatAgeS"]), (True, True, True, 2.0), sh)


# ══ JOINT 3 — THE WORKER ══════════════════════════════════════════════════════════════════════════════════════════
def _shape(shadow):
    """The SHIPPED worker shaper for `shadow`, run in node."""
    with io.open(API, encoding="utf-8") as f:
        src = f.read()
    fn = PK._between_once(src, "    shadow: (function (s) {", "    })(body.shadow),") + "    })"
    fn = "(" + fn[len("    shadow: "):] + ")"
    return PK._node_json(_ws.prelude(src) + "var shape = %s; console.log(JSON.stringify({ v: shape(%s) }));"
                         % (fn, json.dumps(shadow)))["v"]


@unittest.skipIf(NODE is None, "node is absent - this law RUNS the real worker and will not re-implement it")
class TheWorkerKeepsIt(unittest.TestCase):

    def test_the_shaper_keeps_the_four_facts_and_nulls_what_it_cannot_read(self):
        v = _shape({"on": True, "available": True, "recording": False, "working": True, "beatAgeS": 7.5,
                    "why": "armed   - it starts watching"})
        self.assertEqual((v["on"], v["available"], v["recording"], v["working"], v["beatAgeS"]),
                         (True, True, False, True, 7.5), v)
        self.assertEqual(v["why"], "armed - it starts watching")
        # v3890 (#189) - the rolling reel's game verdict rides the wire: true / false / null, nothing guessed
        self.assertEqual([_shape({"on": True, "game": g})["game"] for g in (True, False, None, "yes")],
                         [True, False, None, None])
        odd = _shape({"on": "yes", "working": "maybe", "available": 1, "beatAgeS": -3})
        self.assertEqual((odd["on"], odd["working"], odd["available"], odd["beatAgeS"]), (False, None, None, None), odd)
        self.assertIsNone(_shape(None), "an older console grew a shadow reader it never sent")

    def test_a_watcher_that_stops_is_news(self):
        body = {"machine": "dean-pc", "nickname": "Dean", "install": "i-dean", "ver": "v3527", "mode": "idle",
                "event": "hb", "shadow": {"on": True, "available": True, "recording": False, "working": True,
                                          "beatAgeS": 5.0}}
        first = CF.run_handler(API, method="POST", body=body)
        prior = [p for p in first["puts"] if p["name"] == "console:dean-pc"]
        self.assertEqual(len(prior), 1, "premise: the first beacon stored its record")
        seed = {"console:dean-pc": json.loads(prior[0]["value"])}   # the harness stringifies seed values itself
        same = CF.run_handler(API, method="POST", body=dict(body, shadow=dict(body["shadow"], beatAgeS=19.0)), seed=seed)
        self.assertEqual([p for p in same["puts"] if p["name"] == "console:dean-pc"], [],
                         "premise: only the beat's age moved, which is not news")
        stopped = CF.run_handler(API, method="POST", body=dict(body, shadow=dict(body["shadow"], working=False)),
                                 seed=seed)
        recs = [json.loads(p["value"]) for p in stopped["puts"] if p["name"] == "console:dean-pc"]
        self.assertEqual(len(recs), 1, "a stopped watcher was not written - the eye would glow for up to 15 min")
        self.assertIs(recs[0]["shadow"]["working"], False)
        # v3890 (#189) - the film turning from the game to a streaming page is news too: the eye must not stay live
        on_game = dict(body, shadow=dict(body["shadow"], recording=True, game=True))
        first2 = CF.run_handler(API, method="POST", body=on_game)
        seed2 = {"console:dean-pc": json.loads([p for p in first2["puts"] if p["name"] == "console:dean-pc"][0]["value"])}
        same2 = CF.run_handler(API, method="POST", body=on_game, seed=seed2)
        self.assertEqual([p for p in same2["puts"] if p["name"] == "console:dean-pc"], [], "premise: nothing moved")
        gone = CF.run_handler(API, method="POST", body=dict(on_game, shadow=dict(on_game["shadow"], game=False)), seed=seed2)
        self.assertEqual(len([p for p in gone["puts"] if p["name"] == "console:dean-pc"]), 1,
                         "the film leaving the game (only `game` moved) was not written")


# ══ JOINT 4 — THE CARD ════════════════════════════════════════════════════════════════════════════════════════════
def _eye(shadow, online=True, extra=None):
    row = {"nickname": "Box", "machine": "box-1", "ver": "v3527", "t": _iso(UI_NOW - 40000)}
    row.update(extra or {})
    if shadow != "absent":
        row["shadow"] = shadow
    out = _ui_run("var h = _fleetShadowEye(%s, %s, NOW); OUT.h = h; OUT.text = strip(h);"
                  "var m = /fleet-shadow st-([a-z]+)/.exec(h); OUT.st = m ? m[1] : null;"
                  "var t = /title=\"([^\"]*)\"/.exec(h); OUT.title = t ? t[1] : null;"
                  % (json.dumps(row), "true" if online else "false"))
    return out


LIVE = {"on": True, "available": True, "recording": False, "working": True, "beatAgeS": 6.0, "why": "armed"}


@unittest.skipIf(NODE is None, "node is absent - this law RUNS the shipped card helper and will not re-implement it")
class TheEyeOnEveryRow(unittest.TestCase):

    def test_on_and_working_with_the_game_closed_glows_and_says_background(self):
        e = _eye(LIVE)
        self.assertEqual(e["st"], "lit", e)
        self.assertIn("background", e["title"])
        self.assertEqual(e["text"], "", "the eye added words to the name cell: %r" % e["text"])
        # v3890 (#189, REG-3516) - LIVE is the game on screen, not a reel rolling: the OLD ALT glowed live over GeForce NOW's
        # idle page. A rolling reel whose film shows D2R is live; one whose film shows no D2R, or is not known yet, is ON.
        self.assertEqual(_eye(dict(LIVE, recording=True, game=True))["st"], "live")
        idle = _eye(dict(LIVE, recording=True, game=False))
        self.assertEqual(idle["st"], "lit", idle)
        self.assertIn("shows no Diablo II", idle["title"])
        unk = _eye(dict(LIVE, recording=True))
        self.assertEqual(unk["st"], "lit", "a reel nobody has looked at drew the LIVE eye: %r" % unk)
        self.assertIn("not known yet", unk["title"])

    def test_a_refused_beacon_is_not_called_offline(self):
        """#250 (REG-2048) - Wife PC: the name line said 'presence UNKNOWN, not offline' (the roster refused its last
        beacon) while the eye on the same row said 'this PC is offline'. The eye follows the name line's rule."""
        e = _eye(LIVE, online=False, extra={"lastBeacon": {"ok": False, "code": 403}})
        self.assertEqual(e["st"], "unk", e)
        self.assertIn("presence is UNKNOWN (not offline)", e["title"] or "", e)
        self.assertNotIn("this PC is offline", e["title"] or "", "the eye still calls a refused beacon offline")
        plain = _eye(LIVE, online=False)
        self.assertIn("this PC is offline", plain["title"] or "", "PREMISE: a truly offline row is still called offline")

    def test_switched_off_is_a_shut_lid(self):
        e = _eye(dict(LIVE, on=False))
        self.assertEqual(e["st"], "off", e)
        self.assertIn("sh-shut", e["h"])
        self.assertIn("OFF", e["title"])

    def test_on_but_not_working_is_open_and_says_why(self):
        e = _eye(dict(LIVE, working=False, beatAgeS=1400.0))
        self.assertEqual(e["st"], "idle", e)
        self.assertIn("STOPPED", e["title"])
        self.assertIn("restart", e["title"])
        n = _eye(dict(LIVE, available=False))
        self.assertEqual(n["st"], "idle", n)
        self.assertIn("no local text reader", n["title"])

    def test_unknown_is_never_drawn_lit_or_shut(self):
        for label, shadow, online in (("offline", LIVE, False), ("older build", "absent", True),
                                      ("not stamped", dict(LIVE, working=None), True)):
            e = _eye(shadow, online)
            self.assertEqual(e["st"], "unk", "%s drew %r: %r" % (label, e["st"], e["title"]))
            self.assertIn("UNKNOWN", e["title"])
            self.assertNotIn("sh-iris", e["h"], "%s drew an open, coloured eye" % label)

    def test_a_key_that_outlived_its_pulse_is_unknown_not_offline(self):
        """REG-1833 — REG-1772 made a presence key older than its pulse bar `heard = false`, and the eye read that as
        the offline branch: "this PC is offline" on a row the roster still holds, whose hover says presence UNKNOWN,
        not online. Driven the way the row drives it: _fleetPresence first, then the eye with what it answered."""
        def stale(t_ago_ms):
            row = {"nickname": "Box", "machine": "box-1", "ver": "v3527", "shadow": LIVE}
            if t_ago_ms is not None:
                row["t"] = _iso(UI_NOW - t_ago_ms)
            import fleet_presence as _fp   # v3850 - the server stamps presence; the eye only reads it
            row["presence"] = _fp.presence_of(row, True, UI_NOW)
            return _ui_run("var p = _fleetPresence(%s, true, NOW);"
                           "var h = _fleetShadowEye(%s, !!(p && p.state === 'here'), NOW, p);"
                           "var m = /fleet-shadow st-([a-z]+)/.exec(h); OUT.st = m ? m[1] : null;"
                           "var t = /title=\"([^\"]*)\"/.exec(h); OUT.title = t ? t[1] : null;"
                           % (json.dumps(row), json.dumps(row)))
        for label, ago, says in (("silent 40 min", 40 * 60000, "last seen 40 min ago"),
                                 ("no readable beacon time", None, "no beacon time the card can read")):
            e = stale(ago)
            self.assertEqual(e["st"], "unk", "%s drew %r: %r" % (label, e["st"], e["title"]))
            self.assertIn("UNKNOWN", e["title"], label)
            self.assertIn(says, e["title"], "%s: the eye does not say why presence is unknown" % label)
        self.assertEqual(stale(40000)["st"], "lit", "a row heard 40 s ago lost its lit eye")
        gone = _eye(LIVE, online=False)
        self.assertIn("this PC is offline", gone["title"], "a PC the roster no longer holds stopped saying offline")

    def test_the_second_eye_is_the_console_window(self):
        """* v3885 (his 11-08) - a second eye beside the reader's: GREEN while that PC's console window is up on its desktop,
        RED while it is not (minimized / hidden / headless / a second view), grey UNKNOWN when the PC is not heard"""
        def w(mode, heard=True):
            row = {"nickname": "Box", "machine": "box-1", "ver": "v3527", "t": _iso(UI_NOW - 40000)}
            if mode is not None:
                row["windowMode"] = mode
            return _ui_run("var h = _fleetWindowEye(%s, %s); OUT.h = h; var m = /fleet-winview wv-([a-z]+)/.exec(h);"
                           " OUT.st = m ? m[1] : null; var t = /title=\"([^\"]*)\"/.exec(h); OUT.title = t ? t[1] : null;"
                           % (json.dumps(row), "true" if heard else "false"))
        full = w("fullscreen")
        self.assertEqual(full["st"], "on", full)
        self.assertIn("(fullscreen)", full["title"] or "")
        self.assertEqual(w("front")["st"], "on")
        bg = w("background")
        self.assertEqual(bg["st"], "off", bg)
        self.assertIn("minimized or hidden", bg["title"] or "")
        self.assertEqual((w("headless")["st"], w("window-only")["st"]), ("off", "off"))
        self.assertEqual((w("fullscreen", heard=False)["st"], w(None)["st"]), ("unk", "unk"),
                         "a PC not heard, or one that does not report its window, was drawn as a verdict")

    def test_the_lamp_says_the_console_is_alive_behind_the_scenes(self):
        """* v3890 (#189, REG-3517 - his 11-09: "i do want a lamp to to know that it is connected and alive behind the scenes
        regardless yes") - the row's lamp draws fleet_presence's ONE verdict: green = its console's own beacon is fresh, amber
        = the console is down and only its recorder's lease lives, red = not heard, a grey ring = UNKNOWN - each with a hover"""
        import fleet_presence as _fp

        def lamp(console_ago_ms, recorder_ago_ms=None, listed=True):
            row = {"nickname": "Box", "machine": "box-1", "ver": "v3890"}
            if console_ago_ms is not None:
                row["t"] = _iso(UI_NOW - console_ago_ms)
            if recorder_ago_ms is not None:
                row["recorder"] = {"alive": True, "t": _iso(UI_NOW - recorder_ago_ms)}
            row["presence"] = _fp.presence_of(row, listed, UI_NOW)
            return _ui_run("var p = _fleetPresence(%s, %s, NOW); var h = _fleetLamp(%s, p, %s); OUT.h = h;"
                           " var m = /fleet-dot( [a-z]+)?\"/.exec(h); OUT.cls = m ? (m[1] || '').trim() : null;"
                           " var t = /title=\"([^\"]*)\"/.exec(h); OUT.title = t ? t[1] : null;"
                           % (json.dumps(row), "true" if listed else "false", json.dumps(row), "true" if listed else "false"))
        up = lamp(40000)
        self.assertEqual(up["cls"], "", up)
        self.assertIn("CONNECTED", up["title"])
        rec = lamp(40 * 60000, recorder_ago_ms=30000)
        self.assertEqual(rec["cls"], "rec", "the recorder alone lit the console's lamp green: %r" % rec)
        self.assertIn("console process DOWN", rec["title"])
        gone = lamp(40 * 60000)
        self.assertEqual(gone["cls"], "silent", gone)
        self.assertIn("NOT HEARD", gone["title"])
        unk = lamp(None)
        self.assertEqual(unk["cls"], "unk", unk)
        self.assertEqual(lamp(40000, listed=False)["cls"], "off")
        with io.open(UI, encoding="utf-8") as f:
            src = f.read()
        self.assertIn(".fleet-dot.silent { background: #c9402e;", src, "not heard is red, his rule")

    def test_on_is_green_and_off_is_red(self):
        """* v3885 (his 11-08: "when off red. when on green. same for the shadow reader. simple and clean logic")"""
        with io.open(UI, encoding="utf-8") as f:
            src = f.read()
        for rule in (".fleet-shadow.st-lit .sh-lid { stroke: #3fbf72; }", ".fleet-shadow.st-live .sh-lid { stroke: #6df0a0; }",
                     ".fleet-shadow.st-off .sh-shut { fill: none; stroke: #d0432f;", ".fleet-shadow.st-idle .sh-lid { fill: none; stroke: #c9402e;",
                     ".fleet-winview.wv-on .sh-lid { stroke: #3fbf72; }", ".fleet-winview.wv-off .sh-lid { stroke: #c9402e; }"):
            self.assertEqual(src.count(rule), 1, "the eye's colour rule is not on the page: %s" % rule)

    def test_the_row_draws_the_eye_inside_the_name_cell(self):
        """The join. The helper is driven above; this pins that the ROW calls it, inside <b> so no grid child is added
        (the row laws measure the grid), and BEFORE the name - after it, a long name wrapped and left the eye alone on
        the next line (seen on the 1440 render, 2026-09-30). The render gate measures `.fleet-shadow` painted."""
        with io.open(UI, encoding="utf-8") as f:
            src = f.read()
        # 475f672e - the row passes `heard` (a presence key with a live pulse), not `online`; REG-1833 - and `pres`,
        # so a key that outlived its pulse is said UNKNOWN, not offline
        self.assertEqual(src.count("+ '<b>' + _fleetShadowEye(m, heard, undefined, pres) + _fleetWindowEye(m, heard) + escC(nameFor) + '</b>'"), 1,
                         "the fleet row does not draw the shadow eye beside the name")


if __name__ == "__main__":
    unittest.main(verbosity=2)
