# -*- coding: utf-8 -*-
"""2026-09-28 — THE FLEET BEACON SAYS HOW EACH PC FILMS D2R, AND HOW ITS RIVER DRAINS.

His order: "yea add those beacon fields". Dean's laptop plays D2R NATIVELY ("usually" how he plays), his
ALT streams through Boosteroid, and every console now decides from its OWN machine whether the triage
lane may run (it stands aside while a local D2R.exe runs and catches up after). From his Mac, /api/fleet
has to be able to say which way each PC films and whether its river is draining — two fields inside the
`system` block every console already sends:

    system.capture = {route: native|boosteroid|geforce-now|unknown, ageS, why, source}
    system.river   = {lanes: {STATION: n} | None, ageS, why,
                      triage: {lastKey, lastWhy, lastTs, backlog, owedSince, skips, ...}}

WHAT THIS LAW DRIVES — every end of the joint, the shipped code with only the edges stubbed:
  · the CAPTURE ROUTE: Windows reads the capture half's own pin (cap_target.json, "<proc> [<route>] - ..."),
    the Mac reads the finder's last pick (_PICK_ROUTE, written by the SHIPPED finder at the pick); a pin's
    age is the pin's; waiting / off / missing / corrupt are UNKNOWN with a why; no window title crosses;
  · the RIVER: cached WHERE /api/river computes it (the handler driven for real), carried with ITS age;
    no cache -> lanes None with a why; a newer failed read keeps the last good lanes and says so;
  · THE BEACON NEVER COMPUTES THE RIVER: every river computation is patched to count its calls — zero, and
    _system_for_wire() returns in < 0.5 s;
  · NOTHING IDENTIFYING CROSSES: a Windows path, a home path, a URL, an IP, this host's name and a reel id
    in the lane's last refusal all arrive as placeholders;
  · THE WORKER keeps them (functions/api/console.js's shaper, run in node), and /api/fleet relays them
    for every peer, online and offline — the beacon's own output, through the shaper, through the route.

⚠ NOTHING REAL IS TOUCHED: TV_HIST and HIST_DIR point at a scratch world, the capture pin is a fixture
file, the river's modules are stubbed, and no console, network or KV is contacted. RED_PROOF below.
[[the-unjoined-end]] [[unknown-stays-unknown]] [[stale-reading]] [[heart-first]]
"""
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

_WORLD = tempfile.mkdtemp(prefix="beacon_world_")
os.environ["TV_HIST"] = _WORLD

import control_app as ca  # noqa: E402
import river_lanes as RL  # noqa: E402
import river_stamp as RVS  # noqa: E402
import tv_diablo as TVD  # noqa: E402
import worker_source as _ws  # noqa: E402  REG-1839 - the worker's top-level helpers, lifted with the shaper

NODE = shutil.which("node")
NOW = lambda: int(time.time() * 1000)  # noqa: E731


def _between(src, start, end):
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i:j + len(end)]


def _node(js):
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("node could not run the shipped code - UNKNOWN, not passing: %s" % r.stderr[:400])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _shape(system):
    """The SHIPPED worker shaper for `system`, run in node."""
    with io.open(os.path.join(ROOT, "functions", "api", "console.js"), encoding="utf-8") as f:
        src = f.read()
    fn = _between(src, "    system: (function (s) {", "    })(body.system),")
    fn = "(" + fn[len("    system: "):-len("(body.system),")] + ")"
    return _node(_ws.prelude(src) + "var shape = %s; console.log(JSON.stringify(shape(%s)));" % (fn, json.dumps(system)))


class _World(unittest.TestCase):
    """A scratch world: the fixture shelf, the fixture store, a fresh lane, no cached river."""

    SAVED = ("HIST_DIR", "IS_WIN", "_CAP_TARGET_FILE", "_CAPTURE_ROUTE_SEEN", "_RIVER_LAST",
             "_TRIAGE_LANE", "_TRIAGE_STORE_SEED", "_EAGLE")

    def setUp(self):
        self.world = tempfile.mkdtemp(prefix="beacon_case_")
        self.addCleanup(shutil.rmtree, self.world, True)
        self._env = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = self.world
        self._saved = {k: getattr(ca, k) for k in self.SAVED}
        self._pick = {k: getattr(TVD, k) for k in ("_PICK_ROUTE", "_PICK_WHY", "_PICK_UNKNOWN")}
        self.addCleanup(self._restore)
        ca.HIST_DIR = self.world
        ca.IS_WIN = False
        ca._CAP_TARGET_FILE = os.path.join(self.world, "cap_target.json")
        ca._CAPTURE_ROUTE_SEEN = {"route": None, "ts": None}
        ca._RIVER_LAST = {"good": None, "fail": None}
        ca._TRIAGE_LANE = dict(self._saved["_TRIAGE_LANE"], skips={}, ticks=0, lastKey=None,
                               lastWhy=None, lastTs=None, backlog=None, owedSince=None,
                               caughtUpTs=None, upSince=NOW())
        ca._TRIAGE_STORE_SEED = {"read": False, "ts": None, "why": ""}
        ca._EAGLE = {"rows": []}
        TVD._PICK_ROUTE, TVD._PICK_WHY, TVD._PICK_UNKNOWN = None, "", False

    def _restore(self):
        for k, v in self._saved.items():
            setattr(ca, k, v)
        for k, v in self._pick.items():
            setattr(TVD, k, v)
        if self._env is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = self._env

    def pin(self, doc):
        with io.open(ca._CAP_TARGET_FILE, "w", encoding="utf-8") as fh:
            if isinstance(doc, str):
                fh.write(doc)
            else:
                json.dump(doc, fh)


class TheCaptureRouteOnWindows(_World):
    """Windows: the capture half's OWN pin, as capture_win.ps1 writes it."""

    def setUp(self):
        super(TheCaptureRouteOnWindows, self).setUp()
        ca.IS_WIN = True

    def test_each_route_the_capture_half_names_crosses_as_its_route(self):
        for label, want in (("D2R.exe [local] - Diablo II: Resurrected via PrintWindow", "native"),
                            ("Boosteroid [boosteroid] - Boosteroid via PrintWindow", "boosteroid"),
                            ("chrome [geforce-now] - Diablo II on GeForce NOW via BitBlt", "geforce-now"),
                            ("D2R alive - full virtual fallback", "native")):
            self.pin({"mode": "window", "label": label, "ts": NOW() - 30000, "d2rProcess": False})
            got = ca._capture_route_for_wire()
            self.assertEqual(got["route"], want, "%r read as %r" % (label, got))
            self.assertEqual(got["source"], "capture-half")
            self.assertGreaterEqual(got["ageS"], 29.0, "the age is not the PIN's own age: %r" % got)
            self.assertLess(got["ageS"], 120.0)

    def test_a_window_title_never_crosses(self):
        self.pin({"mode": "window", "ts": NOW(),
                  "label": "chrome [boosteroid] - Boosteroid - my private tab title via BitBlt"})
        got = ca._capture_route_for_wire()
        self.assertEqual(got["route"], "boosteroid")
        self.assertNotIn("private", json.dumps(got), "a window title rode the wire")

    def test_a_pin_whose_route_is_not_named_is_unknown_not_guessed(self):
        self.pin({"mode": "window", "label": "D2R foreground - primary monitor", "ts": NOW()})
        got = ca._capture_route_for_wire()
        self.assertEqual(got["route"], "unknown", "a foreground pin (maybe a cloud window) was guessed")
        self.assertIn("without naming its route", got["why"])

    def test_waiting_after_a_pin_keeps_the_last_pin_with_its_age(self):
        self.pin({"mode": "window", "label": "Boosteroid [boosteroid] - Boosteroid via PrintWindow",
                  "ts": NOW() - 600000})
        self.assertEqual(ca._capture_route_for_wire()["route"], "boosteroid")
        self.pin({"mode": "waiting", "label": "eye held - no game window", "ts": NOW()})
        got = ca._capture_route_for_wire()
        self.assertEqual(got["route"], "boosteroid", "the last pin was forgotten between sessions")
        self.assertGreaterEqual(got["ageS"], 599.0, "the remembered pin lost its own age: %r" % got)
        self.assertIn("last pin this console read", got["why"])

    def test_unknown_with_a_why_when_nothing_was_ever_pinned(self):
        got = ca._capture_route_for_wire()
        self.assertEqual((got["route"], got["ageS"]), ("unknown", None))
        self.assertIn("written no target", got["why"])
        self.pin({"mode": "waiting", "label": "D2R.exe not found", "ts": NOW()})
        got = ca._capture_route_for_wire()
        self.assertEqual(got["route"], "unknown")
        self.assertIn("not pinned", got["why"])
        self.pin("{not json")
        got = ca._capture_route_for_wire()
        self.assertEqual(got["route"], "unknown")
        self.assertIn("could not be read", got["why"])
        self.pin({"mode": "off", "label": "capture is OFF", "ts": NOW()})
        got = ca._capture_route_for_wire()
        self.assertEqual(got["route"], "unknown")
        self.assertIn("OFF", got["why"])


class TheCaptureRouteOnTheMac(_World):
    """The Mac: the finder's last pick in THIS process, recorded by the finder when it picked.

    ⚠ 2026-09-28 (review item 2) — this class used to drive only find_d2r_window_WIN, so no law ever
    ran the Mac finder's own route recording. The Windows pick keeps its case (relabelled); the Mac
    finder is now driven for real through a fake Quartz in sys.modules."""

    def _row(self, pid, title, hwnd, w=1920, h=1080):
        return {"kCGWindowOwnerName": title, "kCGWindowOwnerPID": pid, "hwnd": hwnd, "iconic": False,
                "kCGWindowBounds": {"X": 0, "Y": 0, "Width": w, "Height": h}}

    def _pick_window(self, rows, procs):
        class _W(object):
            def rows(self):
                return rows
        return TVD.find_d2r_window_win(win=_W(), procs=procs)

    @staticmethod
    def _quartz(windows):
        """Quartz as far as find_d2r_window_mac uses it: one call and two constants."""
        q = types.ModuleType("Quartz")
        q.kCGWindowListOptionAll, q.kCGNullWindowID = 0, 0
        q.CGWindowListCopyWindowInfo = lambda option, relative_to: [dict(w) for w in windows]
        return q

    def _mac_pick(self, owner, title, wid, w=1920, h=1080):
        """The SHIPPED Mac finder over a window list holding the menu bar and one candidate. The
        platform is pinned to darwin (CI is Linux, where the finder answers before Quartz)."""
        bar = {"kCGWindowOwnerName": "Window Server", "kCGWindowName": "Menubar", "kCGWindowNumber": 3,
               "kCGWindowIsOnscreen": True, "kCGWindowBounds": {"X": 0, "Y": 0, "Width": 1920, "Height": 24}}
        win = {"kCGWindowOwnerName": owner, "kCGWindowName": title, "kCGWindowNumber": wid,
               "kCGWindowIsOnscreen": True, "kCGWindowBounds": {"X": 0, "Y": 0, "Width": w, "Height": h}}
        saved = TVD._PICK_CACHE
        self.addCleanup(setattr, TVD, "_PICK_CACHE", saved)
        TVD._PICK_CACHE = None                              # the finder's own 0.55 s cache
        with mock.patch.dict(sys.modules, {"Quartz": self._quartz([bar, win])}), \
                mock.patch.object(TVD.sys, "platform", "darwin"):
            return TVD.find_d2r_window_mac()

    def test_the_mac_finder_records_each_route_at_the_pick(self):
        for owner, title, want in (("D2R.exe", "Diablo II: Resurrected", "native"),
                                   ("wine64-preloader", "Diablo II: Resurrected", "native"),
                                   ("GeForceNOW", "Diablo II: Resurrected on GeForce NOW", "geforce-now"),
                                   ("Boosteroid", "Boosteroid", "boosteroid")):
            TVD._PICK_ROUTE = None
            hit = self._mac_pick(owner, title, 700)
            self.assertEqual(hit and hit[0], 700,
                             "premise: the shipped Mac judge pins %s %r (%s)" % (owner, title, TVD._PICK_WHY))
            self.assertEqual((TVD._PICK_ROUTE or {}).get("route"), want,
                             "the Mac finder pinned %s %r and recorded %r" % (owner, title, TVD._PICK_ROUTE))
            got = ca._capture_route_for_wire()
            self.assertEqual((got["route"], got["source"]), (want, "finder"), got)
            self.assertLess(got["ageS"], 60.0)

    def test_the_windows_finder_records_the_route_at_the_pick_and_the_wire_reads_it(self):
        self.assertIsNotNone(self._pick_window([self._row(11, "Boosteroid", 501)], {11: "Boosteroid.exe"}),
                             "premise: the shipped judge pins a bare Boosteroid app window")
        self.assertEqual(TVD._PICK_ROUTE["route"], "boosteroid")
        got = ca._capture_route_for_wire()
        self.assertEqual((got["route"], got["source"]), ("boosteroid", "finder"))
        self.assertLess(got["ageS"], 60.0)
        self.assertIsNotNone(self._pick_window([self._row(12, "Diablo II: Resurrected", 502)], {12: "D2R.exe"}))
        self.assertEqual(ca._capture_route_for_wire()["route"], "native",
                         "D2R.exe on this machine is NATIVE play")

    def test_no_look_and_a_blind_look_are_unknown_and_quote_no_title(self):
        got = ca._capture_route_for_wire()
        self.assertEqual(got["route"], "unknown")
        self.assertIn("has not looked", got["why"])
        TVD._PICK_UNKNOWN = True
        self.assertIn("could not look", ca._capture_route_for_wire()["why"])
        TVD._PICK_UNKNOWN = False
        TVD._PICK_WHY = "no game window; a cloud window is open: boosteroid Boosteroid 'my private title'"
        got = ca._capture_route_for_wire()
        self.assertEqual(got["route"], "unknown")
        self.assertNotIn("private", json.dumps(got), "_PICK_WHY quotes titles and rode the wire")

    def test_a_console_that_never_imported_the_finder_says_so(self):
        with mock.patch.dict(sys.modules):
            sys.modules.pop("tv_diablo", None)
            got = ca._capture_route_for_wire()
        self.assertEqual(got["route"], "unknown")
        self.assertIn("has not looked", got["why"])


def _lanes_payload():
    return {"ok": True, "reconciles": True, "shelf": 10, "hidden": [], "closed": 0, "lifetime": 10,
            "closedWhy": "", "unknown": 0,
            "lanes": [{"name": "INTAKE", "why": "w", "stations": ["INTAKE", "TRIAGE"], "count": 7,
                       "byStation": {"INTAKE": 0, "TRIAGE": 7, "STATION": 0, "EMPTY": 0},
                       "reels": [], "closedReels": None},
                      {"name": "PRINTER", "why": "w", "stations": ["PRINTER", "JOIN"], "count": 3,
                       "byStation": {"PRINTER": 3, "JOIN": 0}, "reels": [], "closedReels": None}]}


class TheRiver(_World):
    """The river rides from WHERE it is computed; the beacon never pays for it."""

    def _drive_river(self, census=None):
        h = ca.Handler.__new__(ca.Handler)
        h.path = "/api/river"
        out = []
        h._json = lambda code, obj: out.append((code, obj))
        cen = census or (lambda *a, **k: {"ok": True, "counts": {}, "visits": {}, "reels": 10})
        # v3849 — /api/river reads the last finished walk and does not wait. An empty hide is
        # the () key. Plant the walk this stub used to return on the caller.
        walked = _lanes_payload()
        RL._LAST[()] = {"at": time.time(), "out": walked}
        try:
            with mock.patch.object(RVS, "census", cen), \
                    mock.patch.object(RVS, "stations", lambda: (("INTAKE", "TRIAGE"), "")), \
                    mock.patch.object(RVS, "rows", lambda *a, **k: {"rows": [], "n": 0}), \
                    mock.patch.object(RL, "lanes", lambda *a, **k: _lanes_payload()), \
                    mock.patch.object(ca, "shelf_hidden_reels", lambda *a, **k: ([], "")), \
                    mock.patch.object(ca, "river_mouth", lambda *a, **k: {}), \
                    mock.patch.object(ca, "reel_census", lambda *a, **k: {}), \
                    mock.patch.object(ca, "_river_labels", lambda: {}), \
                    mock.patch.object(ca, "_river_vocab_facts", lambda: {}):
                h.do_GET()
        finally:
            RL._LAST.pop((), None)
            RL._REFRESH_ON.discard(())
        self.assertEqual(len(out), 1, "premise: the river route answered once")
        return out[0][1]

    def test_no_cached_river_is_lanes_none_with_a_why(self):
        got = ca._river_for_wire()
        self.assertIsNone(got["lanes"], "an uncomputed river reached the wire as a river")
        self.assertIsNone(got["ageS"])
        self.assertIn("has not computed its river", got["why"])
        self.assertTrue(got["triage"]["ok"], "the lane's own record does not depend on the river cache")

    def test_the_river_route_leaves_its_lanes_for_the_beacon(self):
        payload = self._drive_river()
        self.assertTrue(payload.get("ok"), "premise: the stubbed river computed: %r" % payload.get("why"))
        got = ca._river_for_wire()
        self.assertEqual(got["lanes"], {"INTAKE": 0, "TRIAGE": 7, "STATION": 0, "EMPTY": 0,
                                        "PRINTER": 3, "JOIN": 0},
                         "the lanes /api/river computed did not reach the beacon")
        self.assertLess(got["ageS"], 5.0)
        self.assertEqual(got["why"], "")

    def test_the_lanes_carry_their_own_age(self):
        self._drive_river()
        g = dict(ca._RIVER_LAST["good"])
        g["ts"] -= 600000
        ca._RIVER_LAST = {"good": g, "fail": None}
        self.assertGreaterEqual(ca._river_for_wire()["ageS"], 599.0,
                                "a ten-minute-old river went out as current")

    def test_a_newer_failed_read_keeps_the_last_good_lanes_and_says_so(self):
        self._drive_river()

        def _boom(*a, **k):
            raise RuntimeError("census exploded")
        payload = self._drive_river(census=_boom)
        self.assertFalse(payload.get("ok"))
        got = ca._river_for_wire()
        self.assertEqual(got["lanes"]["TRIAGE"], 7)
        self.assertIn("a newer river read failed", got["why"])

    def test_the_beacon_never_computes_the_river(self):
        self._drive_river()
        calls = []

        def _counted(name):
            def _f(*a, **k):
                calls.append(name)
                time.sleep(3.0)          # the cost the beacon must never pay
                raise AssertionError("the beacon computed the river (%s)" % name)
            return _f
        with mock.patch.object(RVS, "census", _counted("river_stamp.census")), \
                mock.patch.object(RVS, "run", _counted("river_stamp.run")), \
                mock.patch.object(RL, "lanes", _counted("river_lanes.lanes")), \
                mock.patch.object(ca, "reel_census", _counted("reel_census")), \
                mock.patch.object(ca, "shelf_hidden_reels", _counted("shelf_hidden_reels")), \
                mock.patch.object(ca, "river_mouth", _counted("river_mouth")):
            t0 = time.time()
            sysb = ca._system_for_wire()
            took = time.time() - t0
        self.assertEqual(calls, [], "the beacon called the river computation: %r" % calls)
        self.assertLess(took, 0.5, "the beacon took %.2f s" % took)
        self.assertEqual(sysb["river"]["lanes"]["TRIAGE"], 7)


class NothingIdentifyingCrosses(_World):

    def test_the_lanes_last_refusal_is_scrubbed(self):
        ca._TRIAGE_LANE.update({
            "ticks": 3, "lastKey": "raised", "skips": {"raised": 3, "C:\\evil": 1},
            "lastWhy": ("the tick raised OSError: [Errno 13] C:\\Users\\Dean\\tv\\retro_triage.json and "
                        + _FAKE_HOME + "/d2r_bible_tests/tv/x.json via https://bull-4-u.com/api/console "
                        "from 10.0.0.4 on MYHOST-7 for reel_s_1510000000000_1")})
        with mock.patch.object(ca.socket, "gethostname", return_value="MYHOST-7"):
            wire = json.dumps(ca._system_for_wire())
            tri = ca._triage_for_wire()
        for leak in ("Dean", "fixtureuser", "bull-4-u", "10.0.0.4", "MYHOST", "reel_s_", "C:\\\\evil", "https"):
            self.assertNotIn(leak, wire, "%r crossed the wire: %s" % (leak, wire[:400]))
        self.assertIn("<path>", tri["lastWhy"])
        self.assertEqual(tri["lastKey"], "raised")
        self.assertEqual(tri["skips"], {"raised": 3}, "a key outside the lane's vocabulary crossed")

    #: ⚠ 2026-09-28 (review item 3) — a user name WITH A SPACE. Every generic path pattern stops at
    #: whitespace, so "C:\\Users\\Dean Smith\\..." crossed as "<path> Smith\\tv\\...".
    SPACED = ("the tick raised OSError: [Errno 13] C:\\Users\\Dean Smith\\tv\\retro_triage.json, then "
              "/Users/Dean Smith/d2r/tv/x.json, then 'C:/Users/Dean Smith/y.json' and /home/dean smith")

    def test_a_user_name_with_a_space_never_crosses(self):
        self.assertIn("Smith", self.SPACED, "premise: the fixture carries the name")
        for out in (ca._wire_text(self.SPACED, 400), ca._redact_for_wire(self.SPACED, 400)):
            for leak in ("Dean", "Smith", "smith", "dean"):
                self.assertNotIn(leak, out, "%r crossed: %r" % (leak, out))
        self.assertIn("<path>", ca._wire_text(self.SPACED, 400))
        self.assertIn("~", ca._redact_for_wire(self.SPACED, 400),
                      "the home fold dropped the path instead of folding it")
        ca._TRIAGE_LANE.update({"ticks": 1, "lastKey": "raised", "skips": {"raised": 1},
                                "lastWhy": self.SPACED})
        self.assertNotIn("Smith", json.dumps(ca._system_for_wire()), "the beacon carried the name")


#: ⚠ 2026-09-28, the SECOND review round - the shapes the first fixture could not see. It was a hand-typed literal
#: with single backslashes; the lane's real text comes from str(exception), which quotes the filename with repr()
#: and DOUBLES every backslash, so "one separator then a name" never matched and "Smith" crossed. Built here the
#: way the lane builds it, plus a file:// URL (scrubbed first, it stopped at the space), an apostrophe name and a
#: OneDrive-for-business folder (the employer's name and the path tail).
# A home-shaped path for the scrub cases, built at RUN time from a synthetic user: a literal one in this PUBLIC repo
# is exactly what test_no_new_home_path_is_published refuses (the first cut named his real user folder).
_FAKE_HOME = "/" + "Users" + "/fixtureuser"

REAL_SHAPES = {
    "repr": "the tick raised %s: %s" % ("PermissionError", PermissionError(
        13, "Permission denied", "C:\\Users\\Dean Smith\\tv\\retro_triage.json")),
    "url": "open file:///Users/Dean Smith/d2r/x.json failed",
    "apostrophe": "C:\\Users\\Dean O'Brien\\tv\\x.json failed",
    "onedrive": "C:\\Users\\Dean\\OneDrive - Acme Corp\\Desktop\\x.json",
    # a path with NO home folder and no backslash - only the path scrub itself can catch it (heart2 found the
    # path-scrub red-proof BLIND: every shape above was also caught by the user or backslash scrub)
    "posix": "the tick raised %s: %s" % ("FileNotFoundError", FileNotFoundError(
        2, "No such file or directory", "/var/folders/zq/Acme_T/tvd/x.json")),
    # no Users folder and no backslash: the drive pattern used to stop at the space
    "forward_drive": "fatal: Unable to create '%s': File exists." % (
        "D:/" + "Jane Doe/" + "TV/.git/index.lock"),
}
REAL_LEAKS = ("Dean", "Smith", "Brien", "Acme", "Corp", "Desktop", "Jane", "Doe")


class TheRealShapesNeverCross(_World):
    """Each shape through _wire_text (the triage lane's scrub) and _redact_for_wire (the home fold)."""

    def test_the_premise_the_repr_shape_doubles_its_backslashes(self):
        self.assertIn("\\\\Users\\\\Dean Smith", REAL_SHAPES["repr"],
                      "PREMISE: str(PermissionError) did not double the backslashes - the case tests nothing")

    def test_no_real_shape_leaks_a_name_on_the_wire(self):
        for k, v in REAL_SHAPES.items():
            out = ca._wire_text(v, 400)
            for leak in REAL_LEAKS:
                self.assertNotIn(leak, out, "%s: %r crossed the wire as %r" % (k, leak, out))

    def test_no_real_shape_leaks_through_the_home_fold(self):
        for k in ("repr", "url", "apostrophe"):
            out = ca._redact_for_wire(REAL_SHAPES[k], 400)
            for leak in ("Dean", "Smith", "Brien"):
                self.assertNotIn(leak, out, "%s: %r crossed the home fold as %r" % (k, leak, out))


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheWorkerScrubsTheRealShapes(_World):
    """The same shapes through functions/api/console.js's txt(), in node - the PUBLIC boundary's second scrub."""

    def test_the_worker_leaks_no_real_shape(self):
        for k, v in REAL_SHAPES.items():
            kept = _shape({"tree": "ok", "reels": 1,
                           "river": {"lanes": None, "ageS": None, "why": v,
                                     "triage": {"lastKey": "raised", "lastWhy": v}}})
            for field in (kept["river"]["why"], kept["river"]["triage"]["lastWhy"]):
                for leak in REAL_LEAKS:
                    self.assertNotIn(leak, field or "", "%s: %r crossed the worker as %r" % (k, leak, field))


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheWorkerScrubsASpacedUserName(_World):
    """The same name through functions/api/console.js's txt(), run in node — the second scrub on the
    PUBLIC boundary must not leak what the first one stops."""

    def test_the_worker_scrubs_the_whole_user_folder(self):
        spaced = NothingIdentifyingCrosses.SPACED
        kept = _shape({"tree": "ok", "reels": 1,
                       "capture": {"route": "native", "ageS": 1, "why": spaced, "source": "finder"},
                       "river": {"lanes": None, "ageS": None, "why": spaced,
                                 "triage": {"lastKey": "raised", "lastWhy": spaced}}})
        for field in (kept["capture"]["why"], kept["river"]["why"], kept["river"]["triage"]["lastWhy"]):
            for leak in ("Dean", "Smith", "smith", "dean"):
                self.assertNotIn(leak, field or "", "%r crossed the worker: %r" % (leak, field))
            self.assertIn("<path>", field or "")


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheWorkerKeepsThem(_World):
    """functions/api/console.js stores what the beacon posts through a fixed shaper - the joint that
    dropped `tally`'s fields four times. Run for real in node."""

    def test_the_beacons_own_block_survives_the_shaper(self):
        ca.IS_WIN = True
        self.pin({"mode": "window", "label": "D2R.exe [local] - Diablo II via PrintWindow", "ts": NOW()})
        ca._RIVER_LAST = {"good": {"ts": NOW(), "stations": {"TRIAGE": 2, "PRINTER": 1}}, "fail": None}
        ca._TRIAGE_LANE.update({"ticks": 4, "lastKey": "playing", "backlog": 2, "owedSince": NOW() - 60000,
                                "skips": {"playing": 4}, "lastWhy": "he is playing",
                                "playingSince": NOW() - 7200000})
        sent = json.loads(json.dumps(ca._system_for_wire()))
        self.assertGreater(sent["river"]["triage"]["playingForS"], 7000.0,
                           "premise: the lane's unbroken run of play reached the wire")
        kept = _shape(sent)
        self.assertEqual(kept["capture"]["route"], "native")
        self.assertEqual(kept["capture"]["source"], "capture-half")
        self.assertEqual(kept["river"]["lanes"], {"TRIAGE": 2, "PRINTER": 1})
        for k in ("lastKey", "backlog", "owedSince", "skips", "lastWhy", "waitS", "playingForS"):
            self.assertEqual(kept["river"]["triage"][k], sent["river"]["triage"][k],
                             "the worker dropped or changed triage.%s" % k)

    def test_anything_else_is_null_and_absent_stays_absent(self):
        kept = _shape({"tree": "ok", "reels": 1,
                       "capture": {"route": "local", "ageS": -5, "why": "C:\\Users\\Dean\\x", "source": "x"},
                       "river": {"lanes": {"TRIAGE": "7", "bad key": 1, "PRINTER": 3}, "ageS": "9",
                                 "triage": {"lastKey": "C:\\x", "skips": {"ok-key": 2, "Bad": 1},
                                            "backlog": -1, "lastWhy": "see " + _FAKE_HOME + "/tv/a.json"}}})
        self.assertEqual(kept["capture"], {"route": None, "ageS": None, "why": "<path>", "source": None})
        self.assertEqual(kept["river"]["lanes"], {"PRINTER": 3})
        self.assertIsNone(kept["river"]["ageS"])
        self.assertIsNone(kept["river"]["triage"]["lastKey"])
        self.assertEqual(kept["river"]["triage"]["skips"], {"ok-key": 2})
        self.assertIsNone(kept["river"]["triage"]["backlog"])
        self.assertNotIn("fixtureuser", kept["river"]["triage"]["lastWhy"])
        self.assertEqual(_shape({"tree": "ok", "reels": 1}), {"tree": "ok", "reels": 1},
                         "an older console's record changed shape")


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheRouteIsNewsAndTheAgesSayWhen(_World):
    """Review item 4 — capture.ageS / river.ageS / triage.waitS could be ~16 min older than stated:
    the worker rewrites the stored record only on a MATERIAL change or every 900 s, and /api/fleet
    caches 60 s. Driven through the REAL onRequestPost (node, an in-memory KV; the harness of
    test_a_beacon_records_the_check_in, which ages the STORED record between beacons): a capture
    route change is material, an age that merely moved is not, and the record carries `system.asOf`
    (its own time) so a reader can add (now - asOf).

    REG-1771 (#86 gap 11, the half REG-1734 left open): the census, the lane counts, the triage
    word, the shelf (own tree, reel count) and a refused beacon are news too. An age, a beacon
    clock and an unchanged census are not."""

    @staticmethod
    def _body(route, age=12.0):
        return {"machine": "dean-pc", "nickname": "Dean", "install": "i-dean", "ver": "v3342",
                "mode": "idle", "event": "hb",
                "system": {"tree": "ok", "reels": 3,
                           "capture": {"route": route, "ageS": age, "why": "", "source": "capture-half"},
                           "river": {"lanes": {"TRIAGE": 2}, "ageS": age, "why": "",
                                     "triage": {"ok": True, "lastKey": "playing", "waitS": age,
                                                "playingForS": age, "skips": {"playing": 2}}}}}

    @staticmethod
    def _run(bodies, age_between=60):
        from test_a_beacon_records_the_check_in import _beacons
        return _beacons(bodies, age_between=age_between)

    def test_an_age_that_moved_inside_the_window_is_not_rewritten(self):
        """The BASELINE: the ages move every beacon and are not news on their own."""
        v = self._run([self._body("native", 12.0), self._body("native", 95.0)])
        self.assertIn("console", v["replies"][0]["stored"], "premise: the first beacon seeded the store")
        self.assertNotIn("console", v["replies"][1]["stored"],
                         "an unchanged route with a moved age spent a KV write")

    def test_a_route_change_is_written_at_once(self):
        v = self._run([self._body("native"), self._body("boosteroid")])
        self.assertIn("console", v["replies"][1]["stored"],
                      "the PC switched from its native game to a Boosteroid stream and the fleet kept "
                      "the old route for up to 15 min: %r" % v["replies"][1])
        self.assertEqual(v["lastseen"]["system"]["capture"]["route"], "boosteroid")

    def test_REG1734_a_river_that_clears_is_written_at_once(self):
        stuck = self._body("native")
        stuck["system"]["river"]["stuck"] = [{"station": "EMPTY", "n": 9, "oldestS": 90000, "why": "route shut"}]
        clear = self._body("native", 95.0)
        clear["system"]["river"]["stuck"] = []
        v = self._run([stuck, clear])
        self.assertIn("console", v["replies"][1]["stored"],
                      "a PC's river cleared and every other PC kept drawing it 'river stuck' for up to 15 min: %r"
                      % v["replies"][1])
        self.assertEqual(v["lastseen"]["system"]["river"]["stuck"], [])

    def test_REG1734_premise_the_same_stuck_with_moved_ages_is_not_news(self):
        a, b = self._body("native", 12.0), self._body("native", 95.0)
        for x, old in ((a, 90000), (b, 90083)):
            x["system"]["river"]["stuck"] = [{"station": "EMPTY", "n": 9, "oldestS": old, "why": "route shut"}]
        v = self._run([a, b])
        self.assertNotIn("console", v["replies"][1]["stored"], "an unchanged stuck list with a moved age spent a write")

    def test_REG1771_a_census_that_goes_missing_is_written_at_once(self):
        """The row says 'locks shut' from the census. A flip that waits for REFRESH_S draws the old calm row."""
        a, b = self._body("native", 12.0), self._body("native", 95.0)
        a["system"]["river"]["heart"] = {"census": "current", "key": "current", "blind": 0}
        b["system"]["river"]["heart"] = {"census": "missing", "key": "dev", "blind": 0}
        v = self._run([a, b])
        self.assertIn("console", v["replies"][1]["stored"],
                      "a PC's proof went missing and every other PC kept the calm row for up to 15 min: %r"
                      % v["replies"][1])
        self.assertEqual(v["lastseen"]["system"]["river"]["heart"]["census"], "missing")

    def test_a_console_that_stops_starting_is_written_at_once(self):
        """#193 (his Fleet, 2026-10-28) - the row prints 'river · starting' from the prover's key. A console whose first
        proof tick raised (census still null) kept drawing 'starting' for up to 15 min, because only the census was news."""
        a, b = self._body("native", 12.0), self._body("native", 95.0)
        a["system"]["river"]["heart"] = {"census": None, "key": "starting", "blind": None}
        b["system"]["river"]["heart"] = {"census": None, "key": "raised", "blind": None}
        v = self._run([a, b])
        self.assertIn("console", v["replies"][1]["stored"],
                      "a console past its boot window kept 'river · starting' on every other PC: %r" % v["replies"][1])
        self.assertEqual(v["lastseen"]["system"]["river"]["heart"]["key"], "raised")

    def test_premise_a_prover_key_the_row_does_not_print_is_not_news(self):
        a, b = self._body("native", 12.0), self._body("native", 95.0)
        a["system"]["river"]["heart"] = {"census": "stale", "key": "running", "blind": 0}
        b["system"]["river"]["heart"] = {"census": "stale", "key": "start", "blind": 0}
        v = self._run([a, b])
        self.assertNotIn("console", v["replies"][1]["stored"], "a prover slice moving spent a KV write")

    def test_REG1771_premise_the_same_census_with_a_moved_age_is_not_news(self):
        a, b = self._body("native", 12.0), self._body("native", 95.0)
        for x in (a, b):
            x["system"]["river"]["heart"] = {"census": "current", "key": "current", "blind": 0}
        v = self._run([a, b])
        self.assertNotIn("console", v["replies"][1]["stored"],
                         "an unchanged census with a moved age spent a KV write")

    def test_REG1771_a_lane_count_that_moves_is_written_at_once(self):
        a, b = self._body("native", 12.0), self._body("native", 95.0)
        b["system"]["river"]["lanes"] = {"TRIAGE": 40, "PRINTER": 2}
        v = self._run([a, b])
        self.assertIn("console", v["replies"][1]["stored"],
                      "a PC's river filled and the click box kept the old lane counts for up to 15 min: %r"
                      % v["replies"][1])
        self.assertEqual(v["lastseen"]["system"]["river"]["lanes"], {"TRIAGE": 40, "PRINTER": 2})

    def test_REG1771_a_triage_word_that_changes_is_written_at_once(self):
        a, b = self._body("native", 12.0), self._body("native", 95.0)
        b["system"]["river"]["triage"]["lastKey"] = "done"
        b["system"]["river"]["triage"]["backlog"] = 12
        v = self._run([a, b])
        self.assertIn("console", v["replies"][1]["stored"],
                      "a PC's triage word changed and the click box kept the old one for up to 15 min: %r"
                      % v["replies"][1])
        self.assertEqual(v["lastseen"]["system"]["river"]["triage"]["lastKey"], "done")
        self.assertEqual(v["lastseen"]["system"]["river"]["triage"]["backlog"], 12)

    def test_REG1771_a_missing_tree_is_written_at_once(self):
        a, b = self._body("native", 12.0), self._body("native", 95.0)
        b["system"]["tree"] = "missing"
        v = self._run([a, b])
        self.assertIn("console", v["replies"][1]["stored"],
                      "a PC's own tree went missing and the hover kept 'established' for up to 15 min: %r"
                      % v["replies"][1])
        self.assertEqual(v["lastseen"]["system"]["tree"], "missing")
        self.assertEqual(v["lastseen"]["system"]["reels"], 3)

    def test_REG1771_a_shelf_count_that_moves_is_written_at_once(self):
        a, b = self._body("native", 12.0), self._body("native", 95.0)
        b["system"]["reels"] = 40
        v = self._run([a, b])
        self.assertIn("console", v["replies"][1]["stored"],
                      "a PC's shelf gained reels and the hover kept the old count for up to 15 min: %r"
                      % v["replies"][1])
        self.assertEqual(v["lastseen"]["system"]["reels"], 40)
        self.assertEqual(v["lastseen"]["system"]["tree"], "ok")

    def test_REG1771_a_refused_beacon_is_written_at_once(self):
        a, b = self._body("native", 12.0), self._body("native", 95.0)
        a["lastBeacon"] = {"ok": True, "code": 200, "t": "2026-10-06T00:00:00Z"}
        b["lastBeacon"] = {"ok": False, "code": 500, "t": "2026-10-06T00:04:00Z", "err": "HTTP Error 500"}
        v = self._run([a, b])
        self.assertIn("console", v["replies"][1]["stored"],
                      "the roster started refusing this PC and the row kept the old presence for up to 15 min: %r"
                      % v["replies"][1])
        self.assertIs(v["lastseen"]["lastBeacon"]["ok"], False)
        self.assertEqual(v["lastseen"]["lastBeacon"]["code"], 500)

    def test_REG1771_premise_a_beacon_clock_that_moved_is_not_news(self):
        a, b = self._body("native", 12.0), self._body("native", 95.0)
        a["lastBeacon"] = {"ok": True, "code": 200, "t": "2026-10-06T00:00:00Z"}
        b["lastBeacon"] = {"ok": True, "code": 200, "t": "2026-10-06T00:04:00Z"}
        v = self._run([a, b])
        self.assertNotIn("console", v["replies"][1]["stored"],
                         "a beacon clock that moved, with the same answer, spent a KV write")

    def test_the_record_says_when_its_ages_were_stated(self):
        v = self._run([self._body("native")])
        ls = v["lastseen"]
        self.assertEqual(ls["system"].get("asOf"), ls["t"],
                         "the stored ages carry no time they were stated at, so a reader cannot add "
                         "(now - asOf) and reads a record up to ~16 min old as current")
        older = self._run([{"machine": "dean-pc", "install": "i-dean", "ver": "v3300", "event": "hb",
                            "system": {"tree": "ok", "reels": 3}}])
        self.assertEqual(older["lastseen"]["system"], {"tree": "ok", "reels": 3},
                         "an older console's record changed shape")


class TheFleetRelaysThemForEveryPeer(_World):
    """/api/fleet hands every row's `system` through, online and offline - driven through the route."""

    def _fleet(self, rows_online, rows_offline):
        h = ca.Handler.__new__(ca.Handler)
        h.path = "/api/fleet"
        out = []
        h._json = lambda code, obj: out.append(obj)
        fl = {"ok": True, "online": rows_online, "offline": rows_offline}
        with mock.patch.object(ca, "fleet_presence", lambda force=False: json.loads(json.dumps(fl))), \
                mock.patch.object(ca, "fleet_origin_status", lambda *a, **k: {"ahead": None,
                                                                               "publishedVer": None}), \
                mock.patch.object(ca, "board_tally_load", lambda: None), \
                mock.patch.object(ca, "fleet_presence_last_good", lambda: (None, None)):
            h.do_GET()
        self.assertEqual(len(out), 1)
        return out[0]

    def test_every_peer_keeps_its_capture_and_river(self):
        dean = {"capture": {"route": "native", "ageS": 12.0, "why": "", "source": "capture-half"},
                "river": {"lanes": {"TRIAGE": 3}, "ageS": 40.0, "why": "",
                          "triage": {"ok": True, "lastKey": "playing", "backlog": 3, "skips": {"playing": 9}}}}
        alt = {"capture": {"route": "boosteroid", "ageS": 5.0, "why": "", "source": "capture-half"},
               "river": {"lanes": None, "ageS": None, "why": "not computed", "triage": None}}
        got = self._fleet([{"machine": "PEER-A", "install": "aaaa", "ver": "v1", "system": dean}],
                          [{"machine": "PEER-B", "install": "bbbb", "ver": "v1", "offline": True,
                            "system": alt}])
        rows = {r["machine"]: r for r in (got.get("online") or []) + (got.get("offline") or [])}
        self.assertEqual(set(rows), {"PEER-A", "PEER-B"}, "premise: both peers reached the payload")
        self.assertEqual(rows["PEER-A"]["system"], dean, "an online peer's system block was changed")
        self.assertEqual(rows["PEER-B"]["system"], alt, "an offline peer's system block was changed")


RED_PROOF = [
    {
        "why": "2026-09-28 round 2 - one separator only again: a repr()-quoted path (doubled backslashes) leaks the name",
        "file": "control_app.py",
        "find": "_WIRE_USER_PAT = r\"\\b(?:Users|home)[\\\\/]+(?:[^'\\\"]|'(?=\\w))*\"\n",
        "replace": "_WIRE_USER_PAT = r\"\\b(?:Users|home)[\\\\/][^\\\\/'\\\"]+\"\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 round 2 - the URL scrub runs first again and stops at the space: a file:// path leaks the surname",
        "file": "control_app.py",
        "find": "    txt = _WIRE_USER_RX.sub(\"<user>\", txt)           # FIRST: a user folder with spaces, quoted or not\n    txt = _WIRE_URL_RX.sub(\"<url>\", txt)\n",
        "replace": "    txt = _WIRE_URL_RX.sub(\"<url>\", txt)\n    txt = _WIRE_USER_RX.sub(\"<user>\", txt)\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 round 2 - the worker's user scrub stops at a space again: the PUBLIC boundary leaks the name",
        "file": "functions/api/console.js",
        "find": "          .replace(/\\b(?:Users|home)[\\\\/]+(?:[^'\"]|'(?=\\w))*/gi, '<user>')\n",
        "replace": "          .replace(/\\b(?:Users|home)[\\\\/][^\\\\/\\s'\"]+/gi, '<user>')\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - /api/river stops leaving its lanes for the beacon: the fleet can never see a river",
        "file": "control_app.py",
        "find": "                _river_remember(_lanes)\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the beacon computes the river itself (2-4 s on every heartbeat)",
        "file": "control_app.py",
        "find": "    g, f = _RIVER_LAST.get(\"good\"), _RIVER_LAST.get(\"fail\")\n",
        "replace": "    import river_lanes as _RL0\n    _RL0.lanes(hide=None)\n"
                   "    g, f = _RIVER_LAST.get(\"good\"), _RIVER_LAST.get(\"fail\")\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a cached river goes out wearing the heartbeat's age, not its own",
        "file": "control_app.py",
        "find": "        out[\"ageS\"] = round(max(0.0, (now - int(g[\"ts\"])) / 1000.0), 1)\n",
        "replace": "        out[\"ageS\"] = 0.0\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the capture half's 'local' crosses raw instead of as native play",
        "file": "control_app.py",
        "find": "                route = \"native\" if m.group(1) == \"local\" else m.group(1)\n",
        "replace": "                route = m.group(1)\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a capture pin's age is the read, not the pin",
        "file": "control_app.py",
        "find": "                out.update(route=route, ageS=_age(d.get(\"ts\")))\n",
        "replace": "                out.update(route=route, ageS=0.0)\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - an unread capture route is guessed as native instead of UNKNOWN",
        "file": "control_app.py",
        "find": "    out = {\"route\": \"unknown\", \"ageS\": None, \"why\": \"\", \"source\": None}\n",
        "replace": "    out = {\"route\": \"native\", \"ageS\": None, \"why\": \"\", \"source\": None}\n",
        "matches": 1,
    },
    {
        # ⚠ relabelled 2026-09-28 (review item 2): this tampers the WINDOWS finder (`_rows`); it was
        # labelled as the Mac's, and no proof touched the Mac finder's own call at all
        "why": "2026-09-28 - the WINDOWS finder picks a window and records no route, so the finder's "
               "wire is always UNKNOWN",
        "file": "tv_diablo.py",
        "find": "    if best:\n        _note_pick_route(_rows, best)\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "review 2 - the MAC finder (Quartz) picks a window and records no route, so a Mac PC's "
               "capture route is always UNKNOWN on the fleet",
        "file": "tv_diablo.py",
        "find": "    if best:\n        _note_pick_route(rows, best)\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "review 3 - the user-folder scrub is dropped: 'C:\\\\Users\\\\Dean Smith\\\\...' leaks 'Smith' "
               "to the fleet",
        "file": "control_app.py",
        "find": "    txt = _WIRE_USER_RX.sub(\"<user>\", txt)           # FIRST: a user folder with spaces, quoted or not\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "review 3 (sibling) - the home fold stops at a space again and misses a Windows home",
        "file": "control_app.py",
        "find": "    txt = _WIRE_HOME_FOLD_RX.sub(\"~\", txt)\n",
        "replace": "    txt = re.sub(r\"/(?:Users|home)/[^/\\s]+\", \"~\", txt)\n",
        "matches": 1,
    },
    {
        "why": "review 3 - the worker's second scrub stops at a space: a spaced user name crosses the PUBLIC boundary",
        "file": "functions/api/console.js",
        "find": "          .replace(/\\b(?:Users|home)[\\\\/]+(?:[^'\"]|'(?=\\w))*/gi, '<user>')\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "review 4 - a capture route change is not material: the fleet keeps the old route up to 15 min",
        "file": "functions/api/console.js",
        "find": "    || capRoute(prev) !== capRoute(rec)\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "review 4 - the stored ages carry no record time, so a reader reads a ~16 min old age as current",
        "file": "functions/api/console.js",
        "find": "  if (rec.system && (rec.system.capture || rec.system.river)) rec.system.asOf = rec.t;\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "review 1 - the lane's unbroken run of play never reaches the wire",
        "file": "control_app.py",
        "find": "            \"playingForS\": s.get(\"playingForS\"),\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "review 1 - the worker drops the lane's unbroken run of play on arrival",
        "file": "functions/api/console.js",
        "find": "              playingForS: num(x.playingForS, DAY400),\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a path in the lane's last refusal crosses to the fleet (a PUBLIC repo's worker)",
        "file": "control_app.py",
        "find": "    txt = _WIRE_PATH_RX.sub(\"<path>\", txt)\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the worker's shaper drops the river on arrival (tally's seventh-joint shape)",
        "file": "functions/api/console.js",
        "find": "        out.river = { lanes: lanes, ageS: num(rv.ageS, DAY400), why: txt(rv.why, 200), triage: tri };\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the worker's shaper drops the capture route on arrival",
        "file": "functions/api/console.js",
        "find": "      if (s.capture && typeof s.capture === 'object') {\n",
        "replace": "      if (false) {\n",
        "matches": 1,
    },
    {"why": "REG-1734 - a river that clears is not news again: other PCs draw it 'river stuck' for up to 15 min",
     "file": "functions/api/console.js",
     "find": "    || riverNews(prev) !== riverNews(rec)\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-1771 - the census, the lane counts and the triage word are not news again: other PCs keep the old row for up to 15 min",
     "file": "functions/api/console.js",
     # c35a3036 added placeWord (REG-1775) and wrapped the line; the tamper drops only the three REG-1771 words
     "find": "    return JSON.stringify([stuckWord === undefined ? 'absent' : stuckWord, heartWord, laneWord,\n"
             "                           triageWord, placeWord]);\n",
     "replace": "    return JSON.stringify([stuckWord === undefined ? 'absent' : stuckWord,\n"
                "                           placeWord]);\n",
     "matches": 1},
    {"why": "#193 - the row's 'river · starting' is not news again: a console past its boot window keeps it for up to 15 min",
     "file": "functions/api/console.js",
     "find": "                           (h.key === 'starting' || h.key === 'low-memory') ? h.key : null] : null;\n",
     "replace": "                           null] : null;\n",
     "matches": 1},
    {"why": "REG-1771 - a tree or a shelf count that changes is not news again: the hover keeps the old words for up to 15 min",
     "file": "functions/api/console.js",
     "find": "    || shelfNews(prev) !== shelfNews(rec)\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-1771 - a refused beacon is not news again: the row keeps the old presence for up to 15 min",
     "file": "functions/api/console.js",
     "find": "    || beaconNews(prev) !== beaconNews(rec)\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
