# -*- coding: utf-8 -*-
"""2026-09-28 — THE FLEET CARD SAYS HOW EACH PC FILMS AND DRAINS, AND THE RIVER SAYS WHAT ITS TRIAGE LANE IS DOING.

His order: "make sure its all properly rendering everywhere". The beacon fields shipped on the wire the same day
(tv/test_the_beacon_says_how_each_pc_films_and_drains.py drives them to /api/fleet):

    system.capture = {route: native|boosteroid|geforce-now|unknown, ageS, why, source}
    system.river   = {lanes: {STATION: n} | None, ageS, why, triage: {lastKey, lastWhy, backlog, sinceLastS, ...}}
    formerMachines = [{machine, lastSeen, ver}]       (one install that reported under two host names)

and /api/river carries `triage` (triage_lane_state()). The fleet card in tv/control_ui.html drew NONE of the first
three and the river panel drew nothing of the fourth: the wire carried it and no reader spent it — the seventh-joint
shape the worker's shaper already names. [[the-unjoined-end]]

WHAT THIS LAW DRIVES — the SHIPPED helpers cut from control_ui.html between real anchors and RUN in node over fixture
rows (never re-typed here), and the SHIPPED card rendered in a real headless Chrome from a stubbed /api/fleet:
  · A ROUTE IS NAMED WITH THE AGE OF ITS PIN: native / Boosteroid / GeForce NOW, aged ageS + (now - the row's record
    time `t`) — the pin's age when the beacon left, plus how long the site has held that beacon. An offline machine's
    route keeps ageing; a row with no `t` reads "age UNKNOWN", never "just now". [[stale-reading]]
  · UNKNOWN IS NEVER 0: an unnamed route, no lane map, an unreadable triage lane and a console older than the fields
    each read UNKNOWN in words; a null backlog is "owed UNKNOWN", never "0 owed"; a null lane map never "TRIAGE 0".
  · THE RIVER'S STATIONS in the order that console counted them, zero stations left out, with the river's age.
  · THE TRIAGE LANE IN WORDS: walking / caught up / "standing aside for his game" / "last refusal: <words>", with
    the backlog and the last walk's age.
  · A RENAMED HOST is a quiet "formerly <name>" line under the row that absorbed it.
  · THE RIVER PANEL'S ONE LINE: the backlog, the last walk's age, the last refusal in words, "standing aside for his
    game" when that is the state, UNKNOWN when absent — and _shLanesRender draws it on every path, lanes or none.
  · THE JOIN, in Chrome: _fleetRefresh over a stubbed /api/fleet draws every row's films / river / triage line and
    the "formerly" line, and nothing in the card scrolls sideways at 901 and 1280 wide.
ROUND 2 (2026-09-28, three findings of the adversarial review, each reproduced on fe817ab7):
  · REG-1377 NO MIDDOT IS STRANDED BY A WRAP: the facts of a line were one middot-joined string, so at 375 a river line
    began "· CAPTURE 4 ·" and at 1280 a triage line ended "walking (53s ago) ·". Each fact is its own flex item (the
    river's own .shr-tri fix); measured in Chrome at 375 and 1280, line by line from the characters' own rects: no
    line of a fact row starts or ends with a middot, and at 375 some row really wraps (the case is not vacuous).
  · REG-1378 AN AGE THE CARD CANNOT ESTABLISH IS "age UNKNOWN": the "formerly" line took _fleetSince's age, which says
    "just now" for a lastSeen it cannot parse and for one after now; and _fleetSince itself said "just now" for any
    time it could not read. A lane that has TICKED but whose last outcome did not survive the wire said "no tick yet";
    now "last outcome unreadable" (ticks > 0), "no tick yet" only at 0 ticks, UNKNOWN when ticks were not sent - on the
    fleet row and on the river's own line.

⚠ NOTHING REAL IS TOUCHED: fixture rows only, a file:// page with fetch stubbed at document start, its own headless
Chrome on its own port (render_check's handle, killed by it). No console, no store, no network. RED_PROOF below.
[[unknown-stays-unknown]] [[heart-first]] [[visual-regression-detector]]
"""
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass


def _free_port():
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


# ⚠ BEFORE the import: render_check reads its port once. Never 9222/9223 (his).
_LAW_PORT = os.environ.get("TV_LAW_PORT", "").strip()
os.environ["TV_RENDER_PORT"] = _LAW_PORT if _LAW_PORT.isdigit() and _LAW_PORT not in ("9222", "9223") else str(_free_port())
import render_check as RC  # noqa: E402

UI_PATH = os.path.join(HERE, "control_ui.html")
UI = io.open(UI_PATH, encoding="utf-8").read()

#: the fleet helpers (second script block): _fleetSince .. _fleetSysHtml, bounded by the next section's own heading
FLEET_START = "  var _fleetSince = function (iso) {"
FLEET_END = "  /* ── v2851 — A TRANSIENT FAILURE MUST NOT BECOME A PERMANENT CARD"
#: the river panel (first script block): the triage vocabulary, its line and the whole lane renderer
RIVER_START = "  var _TRIAGE_WORDS = {"
RIVER_END = "  window._shLanesRender = _shLanesRender;"

NOW = 1790000000000          # a fixed "now" (ms) so every age below is exact
NBSP = u" "


def _iso(ms):
    import datetime
    return datetime.datetime.utcfromtimestamp(ms / 1000.0).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _node():
    for c in ("node", "/usr/local/bin/node", "/opt/homebrew/bin/node"):
        try:
            subprocess.run([c, "--version"], capture_output=True, timeout=10)
            return c
        except Exception:
            continue
    return None


NODE = _node()


def _cut(start, end, inclusive_end=False):
    """The SHIPPED text between two anchors that each occur ONCE. -> str

    ⚠ both ends anchored, counted first: a fixed window reads its own reach, and an anchor that matches twice grades the
    wrong block. [[source-reading-guard]]"""
    assert UI.count(start) == 1, "anchor %r occurs %d times in control_ui.html" % (start, UI.count(start))
    assert UI.count(end) == 1, "anchor %r occurs %d times in control_ui.html" % (end, UI.count(end))
    i = UI.find(start)
    j = UI.find(end, i)
    assert j > i, "the anchors are out of order"
    return UI[i:(j + len(end)) if inclusive_end else j]


HARNESS = r"""
var window = {}; var ELS = {};
var document = { getElementById: function(id){ return ELS[id] || null; } };
var localStorage = { getItem: function(){ return null; }, setItem: function(){} };
function esc(s){ return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
var escC = esc;
"""


def _run(body):
    """Run `body` against the shipped helpers in node. -> the OUT object it filled"""
    # REG-2059 (#281) - the stuck tip says a shared reason once through _fleetStuckWhy, defined at the script's top level
    prog = (HARNESS + _cut("  function _fleetStuckWhy(list, label){\n", "join('  |  ');\n  }\n", inclusive_end=True) + "\n"
            + _cut(RIVER_START, RIVER_END, inclusive_end=True) + "\n" + _cut(FLEET_START, FLEET_END) + "\n"
            + "var NOW = %d; function iso(ms){ return new Date(ms).toISOString(); }\n" % NOW
            + "function plain(s){ return String(s).replace(/\\u00a0/g, ' '); }\n"
            + "function strip(h){ return plain(String(h).replace(/<[^>]+>/g, '')); }\n"
            + ";(function(){ var OUT = {};\n" + body + "\nprocess.stdout.write(JSON.stringify(OUT)); })();\n")
    fh = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
    fh.write(prog)
    fh.close()
    try:
        r = subprocess.run([NODE, fh.name], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("the shipped helpers would not run: %s" % (r.stderr or r.stdout)[-1500:])
        return json.loads(r.stdout)
    finally:
        try:
            os.unlink(fh.name)
        except Exception:
            pass


def _parts(row):
    """_fleetSysParts over one fixture row at NOW -> {films|river|triage: {t, unk, stand, why}}"""
    out = _run("var p = _fleetSysParts(%s, NOW); OUT.p = {}; p.forEach(function(x){ OUT.p[x.k] = { t: plain(x.t), unk: !!x.unk, stand: !!x.stand, why: x.why }; });"
               % json.dumps(row))
    return out["p"]


def _row(t_ago_s=None, **system):
    r = {"nickname": "Box", "machine": "box-1", "ver": "v3522"}
    if t_ago_s is not None:
        r["t"] = _iso(NOW - t_ago_s * 1000)
    r["system"] = dict({"tree": "ok", "reels": 4}, **system)
    return r


TRI_OK = {"ok": True, "lastKey": "surveyed", "lastWhy": "walked one reel", "lastTs": NOW - 90000, "sinceLastS": 60.0,
          "backlog": 2, "owedSince": None, "owedForS": None, "waitS": 60.0, "ticks": 9, "skips": {}}


def _tri(**kw):
    d = dict(TRI_OK)
    d.update(kw)
    return d


@unittest.skipIf(NODE is None, "node is not on this machine - this law RUNS the shipped helpers and will not re-implement them")
class TheFleetRowSaysHowItFilmsAndDrains(unittest.TestCase):

    def test_a_route_is_named_with_the_age_of_its_pin_not_of_the_fetch(self):
        """ageS 30 when the beacon left + 1770 s the site has held it = 30 min — never "30s ago" (the pin's age at send)"""
        p = _parts(_row(1770, capture={"route": "native", "ageS": 30.0, "why": "", "source": "finder"}))
        self.assertEqual(p["films"]["t"], "native · 30m ago", p["films"])
        self.assertFalse(p["films"]["unk"])
        for route, word in (("boosteroid", "Boosteroid"), ("geforce-now", "GeForce NOW")):
            q = _parts(_row(0, capture={"route": route, "ageS": 12.0, "why": "", "source": "capture-half"}))
            self.assertEqual(q["films"]["t"], word + " · 12s ago", q["films"])

    def test_an_unnamed_route_is_unknown_with_the_machines_own_reason(self):
        why = "the window finder could not look (no desktop was visible to it)"
        p = _parts(_row(5, capture={"route": "unknown", "ageS": None, "why": why, "source": "finder"}))
        self.assertEqual((p["films"]["t"], p["films"]["unk"]), ("UNKNOWN", True), p["films"])
        self.assertEqual(p["films"]["why"], why)

    def test_a_row_with_no_record_time_has_an_unknown_age_never_just_now(self):
        p = _parts(_row(None, capture={"route": "native", "ageS": 20.0, "why": "", "source": "finder"},
                        river={"lanes": {"TRIAGE": 1}, "ageS": 5.0, "why": "", "triage": _tri()}))
        self.assertEqual(p["films"]["t"], "native · age UNKNOWN", p["films"])
        self.assertTrue(p["river"]["t"].endswith("age UNKNOWN"), p["river"])
        self.assertIn("(age UNKNOWN)", p["triage"]["t"])
        self.assertIn("last walk age UNKNOWN", p["triage"]["t"])

    def test_the_river_names_its_stations_in_that_consoles_order_with_the_rivers_age(self):
        p = _parts(_row(60, river={"lanes": {"INTAKE": 0, "TRIAGE": 7, "PRINTER": 1, "JOIN": 0, "TOMBSTONE": 2},
                                   "ageS": 300.0, "why": "", "triage": _tri()}))
        self.assertEqual(p["river"]["t"], "TRIAGE 7 · PRINTER 1 · TOMBSTONE 2 · 6m ago", p["river"])
        z = _parts(_row(0, river={"lanes": {"TRIAGE": 0, "PRINTER": 0}, "ageS": 1.0, "why": "", "triage": _tri()}))
        self.assertTrue(z["river"]["t"].startswith("empty — 0 reels at every station"), z["river"])

    def test_no_lane_map_is_unknown_never_a_river_of_zeroes(self):
        why = "this console has not computed its river since it started"
        p = _parts(_row(5, river={"lanes": None, "ageS": None, "why": why, "triage": _tri()}))
        self.assertEqual((p["river"]["t"], p["river"]["unk"], p["river"]["why"]), ("UNKNOWN", True, why), p["river"])
        self.assertNotIn("0", p["river"]["t"])

    def test_the_triage_lane_is_said_in_words(self):
        cases = (("surveyed", "walking ("), ("done", "caught up ("), ("playing", "standing aside for his game ("),
                 ("cpu-shadow", "last refusal: a shadow reel is rolling and the CPU is busy ("),
                 ("capture-mini", "last refusal: standing aside for a live capture ("),
                 ("a-key-with-no-words", "last refusal: a-key-with-no-words ("), (None, "no tick yet ("))
        for key, want in cases:
            # round 2 (REG-1378): "no tick yet" is a lane that has ticked 0 times - its own case below holds the rest
            tri = _tri(lastKey=key, ticks=0) if key is None else _tri(lastKey=key)
            p = _parts(_row(120, river={"lanes": {"TRIAGE": 3}, "ageS": 1.0, "why": "", "triage": tri}))
            self.assertTrue(p["triage"]["t"].startswith(want), "%s: %r" % (key, p["triage"]))
            self.assertEqual(p["triage"]["stand"], key == "playing", "%s: only 'playing' is drawn standing aside" % key)
            self.assertIn("2m ago)", p["triage"]["t"], "%s: the state's age is the beacon's record age" % key)

    def test_the_backlog_and_the_last_walk_carry_their_ages_and_unknown_is_never_zero(self):
        p = _parts(_row(3600, river={"lanes": {"TRIAGE": 7}, "ageS": 1.0, "why": "",
                                     "triage": _tri(backlog=7, sinceLastS=3600.0)}))
        self.assertIn("7 owed", p["triage"]["t"])
        self.assertIn("last walk 2h ago", p["triage"]["t"], "3600 s at the beacon + 3600 s held = 2 h: %r" % p["triage"])
        q = _parts(_row(10, river={"lanes": {"TRIAGE": 7}, "ageS": 1.0, "why": "",
                                   "triage": _tri(backlog=None, sinceLastS=None)}))
        self.assertIn("owed UNKNOWN", q["triage"]["t"])
        self.assertNotIn("0 owed", q["triage"]["t"])
        self.assertIn("no walk on record", q["triage"]["t"])
        r = _parts(_row(10, river={"lanes": None, "ageS": None, "why": "x",
                                   "triage": {"ok": False, "why": "the triage lane could not be read (KeyError)"}}))
        self.assertEqual((r["triage"]["t"], r["triage"]["unk"]), ("UNKNOWN", True), r["triage"])
        self.assertIn("KeyError", r["triage"]["why"])

    def test_a_console_older_than_the_fields_says_so_rather_than_an_empty_machine(self):
        p = _parts(_row(86400))
        for k in ("films", "river", "triage"):
            self.assertEqual((p[k]["t"], p[k]["unk"]), ("UNKNOWN · an older build", True), "%s: %r" % (k, p[k]))

    def test_a_renamed_host_is_a_quiet_formerly_line(self):
        m = _row(30, capture={"route": "native", "ageS": 1.0, "why": "", "source": "finder"})
        m["formerMachines"] = [{"machine": "cursor", "lastSeen": _iso(NOW - 8 * 86400 * 1000), "ver": "v3377"},
                               {"machine": "old-box", "lastSeen": None, "ver": None}]
        out = _run("OUT.h = _fleetSysHtml(%s, NOW); OUT.none = _fleetSysHtml(%s, NOW); OUT.t = _fleetFormerTxt(%s, NOW).map(plain);"
                   % (json.dumps(m), json.dumps(_row(30)), json.dumps(m)))
        self.assertIn('class="fleet-meta fleet-sys fleet-former"', out["h"])
        # round 2 (REG-1378): lastSeen is aged against the SAME now as every other age on the card, so it is exact
        self.assertEqual(out["t"], ["formerly cursor · v3377 · last seen 8d ago",
                                    "formerly old-box · version UNKNOWN · last seen age UNKNOWN"])
        self.assertIn('<span class="fs-f">formerly cursor</span>', out["h"], "the formerly line is not drawn as facts")
        self.assertNotIn("fleet-former", out["none"], "a machine with no former name grew a 'formerly' line")

    def test_a_machines_own_words_are_escaped(self):
        m = _row(1, capture={"route": "unknown", "ageS": None, "why": '<img src=x onerror="boom">', "source": "finder"})
        h = _run("OUT.h = _fleetSysHtml(%s, NOW);" % json.dumps(m))["h"]
        self.assertNotIn("<img", h)
        self.assertIn("&lt;img", h)

    def test_r2_a_lane_that_ticked_without_a_readable_outcome_is_never_no_tick_yet(self):
        """REG-1378 (round 2, reproduced on fe817ab7): the worker nulls a lastKey it cannot read, and a lane with 9 ticks
        read "no tick yet" - a confident zero. ticks > 0 -> "last outcome unreadable"; 0 -> "no tick yet"; ticks not sent
        -> "last outcome UNKNOWN". The backlog and last walk beside it are unchanged."""
        for ticks, want in ((9, "last outcome unreadable ("), (1, "last outcome unreadable ("), (0, "no tick yet ("),
                            (None, "last outcome UNKNOWN (")):
            p = _parts(_row(120, river={"lanes": {"TRIAGE": 3}, "ageS": 1.0, "why": "", "triage": _tri(lastKey=None, ticks=ticks)}))
            self.assertTrue(p["triage"]["t"].startswith(want), "ticks=%r: %r" % (ticks, p["triage"]["t"]))
            self.assertIn("2 owed", p["triage"]["t"], "ticks=%r: the backlog left the line: %r" % (ticks, p["triage"]["t"]))
        # the river's own line, the same rule (the sibling in the first script block)
        out = _run("var d = { triage: %s }; OUT.a = strip(_shTriageLine({ triage: %s }, NOW)); OUT.z = strip(_shTriageLine({ triage: %s }, NOW));"
                   " OUT.u = strip(_shTriageLine({ triage: %s }, NOW));"
                   % (json.dumps(_lane(lastKey=None, ticks=5)), json.dumps(_lane(lastKey=None, ticks=5)),
                      json.dumps(_lane(lastKey=None, ticks=0)), json.dumps(_lane(lastKey=None, ticks=None))))
        self.assertIn("last outcome unreadable", out["a"])
        self.assertNotIn("no tick yet", out["a"], "a lane that ticked 5 times says 'no tick yet': %r" % out["a"])
        self.assertIn("no tick yet since this console started", out["z"])
        self.assertIn("last outcome UNKNOWN", out["u"])

    def test_r2_an_age_the_card_cannot_establish_is_unknown_never_just_now(self):
        """REG-1378 (round 2, reproduced on fe817ab7): the "formerly" line aged lastSeen with _fleetSince, which answers
        "just now" for a time it cannot parse and for one after now - a former name cannot have been seen later than this
        moment. Absent, unparseable and future all read "last seen age UNKNOWN"; a real one reads its age against the card's
        own now. And _fleetSince (the presence phrases) never answers "just now" for a time it cannot read."""
        m = _row(30)
        m["formerMachines"] = [{"machine": "a", "lastSeen": "sometime tuesday", "ver": "v1"},
                               {"machine": "b", "lastSeen": _iso(NOW + 3600 * 1000), "ver": "v2"},
                               {"machine": "c", "lastSeen": None, "ver": "v3"},
                               {"machine": "d", "lastSeen": _iso(NOW - 2 * 3600 * 1000), "ver": "v4"}]
        out = _run("OUT.t = _fleetFormerTxt(%s, NOW).map(plain); OUT.h = strip(_fleetSysHtml(%s, NOW));"
                   " OUT.s = _fleetSince('sometime tuesday'); OUT.v = _fleetSince(iso(Date.now() - 7200000));"
                   % (json.dumps(m), json.dumps(m)))
        self.assertEqual(out["t"], ["formerly a · v1 · last seen age UNKNOWN", "formerly b · v2 · last seen age UNKNOWN",
                                    "formerly c · v3 · last seen age UNKNOWN", "formerly d · v4 · last seen 2h ago"], out["t"])
        self.assertNotIn("just now", out["h"], "the card says 'just now' for an age it could not establish: %r" % out["h"])
        self.assertEqual(out["s"], "age UNKNOWN", "_fleetSince reads an unparseable time as %r" % out["s"])
        self.assertEqual(out["v"], "2h ago", "PREMISE: _fleetSince stopped reading a real time")

    def test_r3_one_station_inside_and_past_the_window_reads_as_two_rows(self):
        """#251 - GrokBot tick 400: 'STATION 7 for 2d · STATION 4 for 2d' with one reason twice; one station held reels
        inside the newest 16 AND past it, and nothing on the chip said which row was which."""
        H = 3600.0
        p = _parts(_row(60, river={"lanes": {"STATION": 13}, "stuckKeep": 16, "stuck": [
            {"station": "STATION", "n": 9, "oldestS": 120 * H, "window": False, "why": "older than the newest 16 - x"},
            {"station": "STATION", "n": 4, "oldestS": 40 * H, "why": "x"}],
            "heart": {"census": "current", "key": "current", "blind": 0}}))
        self.assertEqual(p["stuck"]["t"], "STATION 9 older for 5d · STATION 4 for 2d",
                         "the past-window row is not told apart from the one inside the newest 16 (#251)")
        # REG-2044 - GrokBot's eight checks on v3621: the TIP still printed both rows as "STATION: ..." with no count or
        # age, so one station read as one row twice. The tip names each row with the chip's own words.
        tip = str(p["stuck"].get("why") or "")
        self.assertIn("STATION 9 older for 5d: older than the newest 16", tip, tip)
        self.assertIn("STATION 4 for 2d: x", tip, tip)
        self.assertNotIn("as of this PC", tip, "a fresh report was dated as stale: %r" % tip)

    def test_r4_a_stale_row_dates_its_stuck_reasons(self):
        """#250 (REG-2047, GrokBot tick 415) - Dean's row, last seen 5h, said 'triage lane: he is playing - D2R.exe is running
        on this machine' in the present tense. A report older than one beacon cycle says whose moment the reasons describe."""
        H = 3600.0
        p = _parts(_row(5 * 3600, river={"lanes": {"TRIAGE": 1}, "stuckKeep": 16, "stuck": [
            {"station": "TRIAGE", "n": 1, "oldestS": 12 * H, "why": "triage lane: he is playing"}],
            "heart": {"census": "current", "key": "current", "blind": 0}}))
        tip = str(p["stuck"].get("why") or "").replace("\u00a0", " ")   # ages are written with no-break spaces
        self.assertTrue(tip.startswith("as of this PC\u2019s last report, 5h ago: "), tip)
        self.assertIn("he is playing", tip)

    def test_r2_each_fact_is_its_own_item_with_no_glyph_between_them(self):
        """REG-1377 (round 2): the line's facts are separate items, so no middot sits between two of them for a wrap to
        strand - in every part and in the formerly line. The joined text a reader gets (`t`) is unchanged."""
        m = _row(60, capture={"route": "native", "ageS": 30.0, "why": "", "source": "finder"},
                 river={"lanes": {"TRIAGE": 2, "PRINTER": 3, "CAPTURE": 4, "TOMBSTONE": 1}, "ageS": 120.0, "why": "",
                        "triage": _tri()})
        m["formerMachines"] = [{"machine": "cursor", "lastSeen": _iso(NOW - 86400 * 1000), "ver": "v3377"}]
        out = _run("var h = _fleetSysHtml(%s, NOW), F = new RegExp('<span class=\"fs-f\">[^<]*</span>', 'g');"
                   " OUT.h = h; OUT.between = h.replace(F, '').replace(new RegExp('<i class=\"fs-k\">[^<]*</i>', 'g'), '')"
                   ".replace(new RegExp('<[^>]+>', 'g'), ''); OUT.facts = (h.match(F) || []).map(strip);" % json.dumps(m))
        self.assertEqual(out["between"].strip(), "", "text outside a fact - a separator a wrap can strand: %r" % out["between"])
        self.assertIn("CAPTURE 4", out["facts"])
        self.assertIn("walking (1m ago)", out["facts"])
        self.assertEqual([f for f in out["facts"] if "\u00b7" in f], [], "a fact carries a middot inside it")


RIVER_LANES = {"ok": True, "reconciles": True, "shelf": 4, "closed": 3, "lifetime": 7, "lanes": [
    {"name": "INTAKE", "count": 2, "stations": ["INTAKE", "TRIAGE"], "byStation": {"INTAKE": 0, "TRIAGE": 2}, "why": ""},
    {"name": "TOMBSTONE", "count": 2, "stations": ["ROUTED", "TOMBSTONE"], "byStation": {"ROUTED": 2, "TOMBSTONE": 0},
     "closedCount": 3, "closedShown": 0, "closedWhy": "the ledger", "why": ""}]}


def _lane(**kw):
    t = {"ok": True, "on": True, "stoodDown": False, "lastKey": "playing", "lastWhy": "he is playing",
         "lastAt": NOW - 20000, "lastSkipKey": "playing", "lastSkipWhy": "he is playing", "lastSkipTs": NOW - 20000,
         "backlog": 7, "sinceSurveyS": 3600.0, "lastSurveyTs": NOW - 3600000, "storeWhy": "", "ticks": 5, "skips": {}}
    t.update(kw)
    return t


@unittest.skipIf(NODE is None, "node is not on this machine - this law RUNS the shipped helpers and will not re-implement them")
class TheRiverSaysWhatItsTriageLaneIsDoing(unittest.TestCase):

    def _line(self, d):
        return _run("OUT.h = _shTriageLine(%s, NOW); OUT.s = strip(OUT.h);" % json.dumps(d))

    def test_standing_aside_for_his_game_with_the_backlog_and_the_last_walks_age(self):
        d = {"triage": _lane(), "__askedAt": NOW - 1800000}
        out = self._line(d)
        self.assertIn('<b class="shr-tri-stand"', out["h"])
        self.assertIn("standing aside for his game (20s ago)", out["s"])
        self.assertIn("7 owed", out["s"])
        self.assertIn("last walk 2h ago", out["s"], "3600 s when asked + 1800 s on the page = 90 min = 2 h: %r" % out["s"])
        self.assertNotIn("last refusal", out["s"], "the state already says it - the refusal is not said twice")

    def test_the_last_refusal_is_said_in_words_with_its_age(self):
        d = {"triage": _lane(lastKey="cpu-loaded", lastSkipKey="cpu-loaded", lastSkipTs=NOW - 180000,
                             lastSkipWhy="the machine is 97% busy")}
        out = self._line(d)
        # REG-1441: the refusal's age sits in brackets (a middot inside one wrapping span could be stranded)
        self.assertIn("last refusal: the machine is too busy (3m ago)", out["s"])
        self.assertNotIn("standing aside for his game", out["s"])
        w = self._line({"triage": _lane(lastKey="surveyed", lastSkipKey=None, lastSkipTs=None)})
        self.assertIn("walking", w["s"])
        self.assertIn("no refusal since this console started", w["s"])

    def test_absent_or_unreadable_is_unknown_never_a_backlog_of_zero(self):
        self.assertIn("UNKNOWN", self._line(None)["s"])
        a = self._line({"lanes": RIVER_LANES})
        self.assertIn("UNKNOWN — this console does not publish its triage lane", a["s"])
        b = self._line({"triage": {"ok": False, "why": "the triage lane state could not be read: boom"}})
        self.assertIn("UNKNOWN — the triage lane state could not be read: boom", b["s"])
        c = self._line({"triage": _lane(backlog=None, sinceSurveyS=None, storeWhy="the survey store could not be read")})
        self.assertIn("owed UNKNOWN", c["s"])
        self.assertNotIn("0 owed", c["s"])
        self.assertIn("last walk UNKNOWN", c["s"])

    def test_the_lane_renderer_draws_it_on_every_path(self):
        """THE JOIN: _shLanesRender writes the line with the lanes, with a refused river and with no answer at all"""
        out = _run(r"""
          ELS['sh-lanes'] = { innerHTML: '', querySelector: function(){ return null; } };
          var lanes = %s, tri = %s;
          _shLanesRender({ lanes: lanes, triage: tri, __askedAt: NOW }); OUT.full = ELS['sh-lanes'].innerHTML;
          _shLanesRender({ ok: false, triage: tri }); OUT.noLanes = ELS['sh-lanes'].innerHTML;
          _shLanesRender({ lanes: { ok: false, why: 'the map stopped partitioning' }, triage: tri }); OUT.refused = ELS['sh-lanes'].innerHTML;
          _shLanesRender(null); OUT.none = ELS['sh-lanes'].innerHTML;
        """ % (json.dumps(RIVER_LANES), json.dumps(_lane())))
        for k in ("full", "noLanes", "refused", "none"):
            self.assertIn('class="shr-tri', out[k], "%s: the river drew no triage line" % k)
        self.assertIn("standing aside for his game", out["full"])
        fold_at = out["full"].find("</details>")
        self.assertNotEqual(-1, fold_at,
                            "REG-1892 - the full render drew no fold close: the order below would be vacuous")
        self.assertGreater(out["full"].find('class="shr-tri'), fold_at,
                           "the line sits inside the fold - it must read with the river shut")
        self.assertIn("UNKNOWN", out["none"])


# ── THE JOIN, IN A REAL BROWSER: the shipped card from a stubbed /api/fleet ─────────────────────────────────────────
STUB = r"""(function(){
  var FLEET = %s;
  var _f = window.fetch;
  window.fetch = function(u, o){
    var s = String(u && u.url || u), body = null;
    if (s.indexOf('/api/fleet') >= 0) body = FLEET;
    else if (s.indexOf('/api/') >= 0) body = { ok: false, why: 'law page - no console behind it' };
    if (body !== null) return Promise.resolve(new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    return _f ? _f.apply(this, arguments) : Promise.reject(new Error('no fetch'));
  };
})();"""

READ = r"""(function(){ var l = document.getElementById('fleet-list'); if (!l) return JSON.stringify({ err: 'no #fleet-list' });
  var lr = l.getBoundingClientRect();
  var rows = [].map.call(l.querySelectorAll('.fleet-row'), function(r){
    var sys = r.querySelector('.fleet-sys:not(.fleet-former)'), fm = r.querySelector('.fleet-former');
    var spill = [].filter.call(r.querySelectorAll('.fleet-sys .fs-l'), function(e){ var b = e.getBoundingClientRect(); return b.width > 0 && b.right > lr.right + 0.5; }).length;
    var chip = r.querySelector('.fleet-riverstuck'), cb = chip ? chip.getBoundingClientRect() : null;
    return { name: (r.querySelector('b') || {}).textContent || '', sys: sys ? sys.innerText.replace(/ /g, ' ') : null,
             stuck: !!chip, stuckSpill: !!(cb && cb.width > 0 && cb.right > lr.right + 0.5),
             former: fm ? fm.innerText : null, spill: spill, h: sys ? sys.getBoundingClientRect().height : 0 }; });
  return JSON.stringify({ rows: rows, sw: [l.scrollWidth, l.clientWidth], w: lr.width }); })()"""

WIDTHS = ((901, 900), (1280, 800))
#: round 2 (REG-1377) - where the reviewer saw a stranded middot: 375 ("· CAPTURE 4 ·") and 1280 ("walking (53s ago) ·")
WRAP_WIDTHS = ((375, 812), (1280, 800))
#: every rendered LINE of every fact row (films / river / triage / formerly), rebuilt from each character's own rect - the
#: key hangs in the indent and is left out; a line is the characters whose tops agree within 3px
LINES = r"""(function(){ var out = [];
  [].forEach.call(document.querySelectorAll('#fleet-xref .fx-sys .fs-l, #fleet-xref .fx-foot'), function(l){
    var ch = [], tw = document.createTreeWalker(l, NodeFilter.SHOW_TEXT), n;
    while ((n = tw.nextNode())){
      if (n.parentElement && n.parentElement.closest('.fs-k')) continue;
      for (var i = 0; i < n.data.length; i++){ var rg = document.createRange(); rg.setStart(n, i); rg.setEnd(n, i + 1);
        var rs = rg.getClientRects(); if (!rs.length) continue; ch.push({ c: n.data[i], t: rs[0].top, x: rs[0].left }); } }
    ch.sort(function(a, b){ return a.t - b.t || a.x - b.x; });
    var lines = [], cur = null;
    ch.forEach(function(c){ if (!cur || c.t > cur.t + 3){ cur = { t: c.t, cs: [] }; lines.push(cur); } cur.cs.push(c); });
    out.push(lines.map(function(L){ return L.cs.sort(function(a, b){ return a.x - b.x; }).map(function(c){ return c.c; }).join('').replace(/\u00a0/g, ' ').trim(); }));
  });
  return JSON.stringify(out); })()"""
#: 2026-09-29 - the lines live in the click box (#fleet-xref .fx-sys), not on the row: his "only if clicked on"
BOX = r"""(function(){ var x = document.getElementById('fleet-xref'); if (!x || x.hidden) return JSON.stringify({ err: 'box closed' });
  var s = x.querySelector('.fx-sys'); if (!s) return JSON.stringify({ err: 'no .fx-sys in the box' });
  var br = x.getBoundingClientRect(), sys = s.querySelector('.fleet-sys:not(.fleet-former)'), fm = s.querySelector('.fleet-former');
  var spill = [].filter.call(s.querySelectorAll('.fs-l'), function(e){ var b = e.getBoundingClientRect(); return b.width > 0 && b.right > br.right + 0.5; }).length;
  return JSON.stringify({ sys: sys ? sys.innerText.replace(/\u00a0/g, ' ') : null, former: fm ? fm.innerText : null, spill: spill,
                          facts: sys ? sys.querySelectorAll(':scope > .fs-l').length : 0,
                          sw: [document.documentElement.scrollWidth, document.documentElement.clientWidth] }); })()"""
MACHINES = (("Konyo", "box-a"), ("ALT", "box-b"), ("Wife PC", "box-c"))
_CACHE = {}


def _fixture():
    now = int(time.time() * 1000)
    iso = lambda ago_s: _iso(now - ago_s * 1000)   # noqa: E731
    return {"ok": True, "me": "box-a", "publishedVer": "v3522", "fromCache": False, "staleAgeS": 0.0, "webOnly": [],
            "online": [
                {"nickname": "Konyo", "machine": "box-a", "ver": "v3522", "mode": "idle", "t": iso(40),
                 "formerMachines": [{"machine": "cursor", "lastSeen": iso(8 * 86400), "ver": "v3377"}],
                 "system": {"tree": "ok", "reels": 9,
                            "capture": {"route": "native", "ageS": 95.0, "why": "", "source": "finder"},
                            "river": {"lanes": {"TRIAGE": 2, "PRINTER": 3, "CAPTURE": 4, "TOMBSTONE": 1}, "ageS": 120.0,
                                      "why": "", "triage": dict(TRI_OK, lastTs=now - 90000),
                                      "stuck": [], "heart": {"census": "current", "key": "current", "blind": 0}}}},
                {"nickname": "ALT", "machine": "box-b", "ver": "v3521", "mode": "live", "t": iso(20),
                 "system": {"tree": "ok", "reels": 10,
                            "capture": {"route": "boosteroid", "ageS": 12.0, "why": "", "source": "capture-half"},
                            "river": {"lanes": {"TRIAGE": 7, "PRINTER": 1, "TOMBSTONE": 2}, "ageS": 300.0, "why": "",
                                      "triage": dict(TRI_OK, lastKey="cpu-shadow", backlog=7, sinceLastS=10800.0),
                                      # #74 (REG-1461) - the ALT's real shape on 2026-09-29, found only by SSH
                                      "stuck": [{"station": "EMPTY", "n": 76, "oldestS": 40 * 3600.0,
                                                 "why": "route lane: reel.route is LOCKED - the heart has never run here"},
                                                {"station": "PRINTER", "n": 25, "oldestS": 38 * 3600.0,
                                                 "why": "vault lane: owes 0, 0 read(s) on record"}],
                                      "heart": {"census": "missing", "key": "busy", "blind": None}}}}],
            "offline": [
                {"nickname": "Wife PC", "machine": "box-c", "ver": "v3401", "mode": "idle", "t": iso(5 * 86400),
                 "system": {"tree": "ok", "reels": 3}}]}


def _render():
    if "r" in _CACHE:
        return _CACHE["r"]
    RC.require_chrome()   # REG-3061 - a browser that will not start is UNKNOWN for this law (a VenueFault), never a red
    res = {}
    try:
        t = RC._Tab("about:blank")
        t.send("Page.enable")
        t.send("Runtime.enable")
        t.send("Page.addScriptToEvaluateOnNewDocument", source=STUB % json.dumps(_fixture()))
        for (w, h) in sorted(set(WIDTHS) | set(WRAP_WIDTHS), key=lambda x: -x[0]):
            t.send("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=False)
            t.send("Page.navigate", url="file://" + UI_PATH)
            for _ in range(160):
                time.sleep(0.25)
                try:
                    if t.ev("document.readyState==='complete' && typeof window._fleetRefresh === 'function'") is True:
                        break
                except Exception:
                    pass
            else:
                raise AssertionError("control_ui.html never exposed _fleetRefresh in 40s - UNKNOWN, not passing")
            time.sleep(0.8)
            t.ev("(function(){ try { window._fleetRefresh(); } catch (e) {} return 1; })()")
            for _ in range(60):
                time.sleep(0.25)
                if t.ev("document.querySelectorAll('#fleet-list .fleet-row').length") == 3:
                    break
            time.sleep(0.3)
            res["%dx%d" % (w, h)] = json.loads(t.ev(READ))
            _lines = []
            for (nm, mach) in MACHINES:
                t.ev("(function(){ try { window._fleetCompare(%s); } catch (e) {} return 1; })()" % json.dumps(mach))
                for _ in range(60):
                    time.sleep(0.2)
                    # wait for the box's HEAD (both answer paths draw it), never for .fx-sys itself: waiting on the
                    # thing under test turned a missing box into a 180 s hang instead of a red (proof [1], measured)
                    if t.ev("!!document.querySelector('#fleet-xref .fx-head')"):
                        break
                # v3796 render block - a CLOSED fold must lay out nothing: Chrome hid its lines from paint only, so they
                # kept full-height boxes below the window and the render gate read them as 'cut by fxr-win' at 1120+
                res["closed %s %dx%d" % (nm, w, h)] = t.ev(FOLD_CLOSED)
                # GBL 2026-10-24 - the lines sit under the box's ADVANCED fold; he opens it to read them
                t.ev("(function(){ var a = document.querySelector('#fleet-xref details.fx-adv'); if (a) a.open = true; return 1; })()")
                time.sleep(0.2)
                res["foldcut %s %dx%d" % (nm, w, h)] = t.ev(FOLD_CUT)
                res["box %s %dx%d" % (nm, w, h)] = json.loads(t.ev(BOX))
                _lines += json.loads(t.ev(LINES))
                # REG-1462 (v3796) - the footer's age separator read from the DOM itself: the shadow fold moved the
                # 375 wrap off the separator, so the line-start check alone stopped seeing a breakable one
                res["fxage %s %dx%d" % (nm, w, h)] = t.ev("(function(){ var e = document.querySelector('#fleet-xref .fx-foot .fx-age'); return e ? e.textContent : null; })()")
            res["lines %dx%d" % (w, h)] = _lines
        res["errors"] = list(getattr(t, "page_errors", []) or [])
        try:
            t.close()
        except Exception:
            pass
    finally:
        RC._chrome_down()
    _CACHE["r"] = res
    return res


# v3796 render block: how many fact lines a CLOSED fold still lays out (must be 0), and, open, how many end outside the
# window while the fold does not scroll (must be 0 - the window is overflow:hidden).
FOLD_CLOSED = """(function(){ var a = document.querySelector('#fleet-xref details.fx-adv'); if (!a) return -1; a.open = false;
  return [].slice.call(a.querySelectorAll('.fs-l')).filter(function(e){ return e.getBoundingClientRect().height > 0; }).length; })()"""
FOLD_CUT = """(function(){ var w = document.querySelector('#fleet-xref .fxr-win'), a = document.querySelector('#fleet-xref details.fx-adv');
  if (!w || !a) return -1; var wr = w.getBoundingClientRect(), scrolls = a.scrollHeight > a.clientHeight + 1
    && /auto|scroll/.test(getComputedStyle(a).overflowY);
  if (scrolls) { var ar = a.getBoundingClientRect(), b = document.querySelector('#fleet-xref .fx-body');
    var sm = a.querySelector('summary'), sr = sm && sm.getBoundingClientRect();
    /* a scrolling fold still counts only when it ends inside the window, the body below it still starts inside it,
       and its summary (the close control) is still on screen at the bottom of its scroll */
    a.scrollTop = a.scrollHeight; var sr2 = sm && sm.getBoundingClientRect(); a.scrollTop = 0;
    return ((ar.bottom > wr.bottom + 1) ? 1 : 0) + ((b && b.getBoundingClientRect().top >= wr.bottom - 1) ? 1 : 0)
         + ((!sr2 || sr2.top < ar.top - 1) ? 1 : 0); }
  return [].slice.call(a.querySelectorAll('.fs-l')).filter(function(e){ var r = e.getBoundingClientRect();
    return r.height > 0 && r.bottom > wr.bottom + 1; }).length; })()"""


@unittest.skipUnless(os.path.exists(RC.CHROME), "no Chrome on this machine - the card was not rendered (declared skip 77)")
class TheShippedCardDrawsIt(unittest.TestCase):

    def test_the_rows_are_calm_and_a_click_opens_films_river_and_triage(self):
        """2026-09-29 - HIS WORDS: "i dont want it rendering to me all this here upfront. only if clicked on or something
        like a backdoor to the informational background". The row carries NO films / river / triage line; a click on the
        PC opens the box, and the box carries all three (and a renamed host's 'formerly' line)."""
        r, bad = _render(), []
        for (w, h) in WIDTHS:
            m = r["%dx%d" % (w, h)]
            self.assertNotIn("err", m, m)
            self.assertEqual(len(m["rows"]), 3, "%dx%d: PRINT THE DENOMINATOR - %d rows drawn of 3" % (w, h, len(m["rows"])))
            for row in m["rows"]:
                if row["sys"] or row["former"]:
                    bad.append("%dx%d %s: the row renders its detail upfront again (%r / %r)" % (w, h, row["name"], row["sys"], row["former"]))
            boxes = dict((nm, r.get("box %s %dx%d" % (nm, w, h)) or {}) for nm, _m in MACHINES)
            for nm, bx in boxes.items():
                if bx.get("err"):
                    bad.append("%dx%d %s: a click opened no detail (%s)" % (w, h, nm, bx.get("err")))
                    continue
                for word in ("films", "river", "triage"):
                    if word not in (bx.get("sys") or ""):
                        bad.append("%dx%d %s: no %s fact in the box (%r)" % (w, h, nm, word, bx.get("sys")))
                if bx.get("spill"):
                    bad.append("%dx%d %s: %d fact line(s) run past the box's right edge" % (w, h, nm, bx["spill"]))
                if bx.get("sw") and bx["sw"][0] > bx["sw"][1] + 1:
                    bad.append("%dx%d %s: the page scrolls sideways with the box open %s" % (w, h, nm, bx["sw"]))
            k, a, wp = boxes.get("Konyo") or {}, boxes.get("ALT") or {}, boxes.get("Wife PC") or {}
            # #74 (REG-1461) - the stuck river on the ROW (one red word) and in the BOX (stations, ages, proof)
            _rows = dict((row["name"], row) for row in m["rows"])
            if not (_rows.get("ALT") or {}).get("stuck"):
                bad.append("%dx%d ALT row: its river has been stuck 40 h and the row does not say so" % (w, h))
            if (_rows.get("ALT") or {}).get("stuckSpill"):
                bad.append("%dx%d ALT row: 'river stuck' runs past the list's right edge" % (w, h))
            if (_rows.get("Konyo") or {}).get("stuck"):
                bad.append("%dx%d Konyo row: a draining river grew an alarm" % (w, h))
            for want in ("EMPTY 76 for", "PRINTER 25 for", "never proved on this PC"):
                if want not in (a.get("sys") or ""):
                    bad.append("%dx%d ALT box: no %r (%r)" % (w, h, want, a.get("sys")))
            if "native" not in (k.get("sys") or "") or "walking" not in (k.get("sys") or ""):
                bad.append("%dx%d Konyo box: %r" % (w, h, k.get("sys")))
            if "formerly cursor" not in (k.get("former") or ""):
                bad.append("%dx%d Konyo box: no 'formerly cursor' line (%r)" % (w, h, k.get("former")))
            if "Boosteroid" not in (a.get("sys") or "") or "TRIAGE 7" not in (a.get("sys") or ""):
                bad.append("%dx%d ALT box: %r" % (w, h, a.get("sys")))
            # #74 (REG-1461) - FIVE lines, then SIX: films, river, triage, whether its river is STUCK, whether that PC
            # has PROVED its instruments, (#41 rank 22, REG-1564) what its character PICKER offers, and (#108,
            # REG-1608) whether its READERS can read. An older build knows none of them, so all seven say UNKNOWN.
            # v3880 (REG-3363) added an eighth fact, d2jsp, and this case pinned the NUMBER seven: it went red on a correct
            # box. The LAW is every fact line an older build draws says UNKNOWN - counted against the box's own fact lines
            # (at least the seven named above), never a literal. [[regression-guard]] pin the law, not the number
            _facts = int(wp.get("facts") or 0)
            if _facts < 7 or (wp.get("sys") or "").count("UNKNOWN") != _facts:
                bad.append("%dx%d Wife PC box (an older build): %d fact line(s), not every one UNKNOWN (%r)"
                           % (w, h, _facts, wp.get("sys")))
            if m["sw"][0] > m["sw"][1] + 1:
                bad.append("%dx%d the fleet list scrolls sideways %s" % (w, h, m["sw"]))
        self.assertEqual(r.get("errors"), [], "the page threw: %s" % r.get("errors"))
        self.assertEqual(bad, [], "\n  ".join(bad))

    def test_a_closed_advanced_fold_lays_out_nothing_and_an_open_one_is_never_cut(self):
        """v3796 render block (2026-10-24): the ADVANCED fold shipped closed, and a closed <details> hides its lines from
        paint, not from layout - so at 1120 and wider (the short window) 4 lines sat below the window's overflow:hidden
        edge and the render gate refused the push as 'cut by fxr-win'. Closed, no line has a box; open, a line past the
        window's bottom is only allowed when the fold itself scrolls. PREMISE: every box at every width was read."""
        r, seen, bad = _render(), 0, []
        for (w, h) in sorted(set(WIDTHS) | set(WRAP_WIDTHS)):
            for nm, _m in MACHINES:
                c, k = r.get("closed %s %dx%d" % (nm, w, h)), r.get("foldcut %s %dx%d" % (nm, w, h))
                if c is None or k is None or c < 0 or k < 0:
                    bad.append("%dx%d %s: the fold was not read (%r / %r)" % (w, h, nm, c, k))
                    continue
                seen += 1
                if c:
                    bad.append("%dx%d %s: a CLOSED fold still lays out %d fact line(s)" % (w, h, nm, c))
                if k:
                    bad.append("%dx%d %s: %d fact line(s) end below the window and nothing scrolls" % (w, h, nm, k))
        self.assertGreater(seen, 0, "PREMISE - no fold was read")
        self.assertEqual(bad, [], "\n  ".join(bad))

    def test_the_compare_footers_age_separator_cannot_break(self):
        """REG-1462 (2026-09-29, Grok's cold look at 375): the footer's age separator is glued with no-break spaces, so
        a wrap never starts a line with a lone middot. Read from the rendered footer of every box, at every width -
        it does not wait for a wrap to land on the separator. PREMISE: at least one footer drew its age."""
        r, seen, bad = _render(), 0, []
        for k, v in sorted(r.items()):
            if not k.startswith("fxage ") or v is None:
                continue
            seen += 1
            if not v.startswith(u"\u00a0\u00b7\u00a0"):
                bad.append("%s: %r" % (k, v[:24]))
        self.assertGreater(seen, 0, "PREMISE - no compare footer drew its age, so its separator was never read")
        self.assertEqual(bad, [], "the footer's age separator can break:\n  " + "\n  ".join(bad))

    def test_r2_no_line_of_a_fact_row_starts_or_ends_with_a_middot(self):
        """REG-1377 (round 2, reproduced on fe817ab7): the facts of a line were one middot-joined string, so a wrap left
        a middot alone at a line's start ("· CAPTURE 4 ·" at 375) or end ("walking (53s ago) ·" at 1280). Line by line
        from the characters' own rects: none starts or ends with one. PREMISE: every row's lines were read, and at 375 a
        row really wraps."""
        r, bad = _render(), []
        for (w, h) in WRAP_WIDTHS:
            rows = r["lines %dx%d" % (w, h)]
            self.assertGreaterEqual(len(rows), 7, "%dx%d: PRINT THE DENOMINATOR - only %d fact rows read in the boxes" % (w, h, len(rows)))
            self.assertTrue(all(rows), "%dx%d: a fact row has no rendered line: %s" % (w, h, rows))
            if w < 500:
                self.assertTrue(any(len(x) > 1 for x in rows), "%dx%d: PREMISE - no fact row wraps, so a stranded middot "
                                                                "could not have been seen: %s" % (w, h, rows))
            for lines in rows:
                for s in lines:
                    if s.startswith(u"\u00b7") or s.endswith(u"\u00b7"):
                        bad.append("%dx%d: %r (of %r)" % (w, h, s, lines))
        self.assertEqual(bad, [], "a middot is stranded at a line's end:\n  " + "\n  ".join(bad))


RED_PROOF = [
    {"why": "v3796 render block - a closed ADVANCED fold lays its lines out below the window again ('cut by fxr-win' at 1120+)",
     "file": "tv/control_ui.html",
     "find": "  .fx-adv:not([open]) > .fx-sys { display: none; }\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2047 - a stale row's stuck reasons read as the present again",
     "file": "tv/control_ui.html",
     "find": "      else if (_repAge > 900) _stuckWhy = ",
     "replace": "      else if (false) _stuckWhy = ",
     "matches": 1},
    {"why": "REG-2044 - the stuck tip names a past-window row only by its station again",
     "file": "tv/control_ui.html",
     "find": "        whyBits.push(_fleetStuckWhy(beyond, _stuckLabel));\n",
     "replace": "        whyBits.push(_fleetStuckWhy(beyond, function (e) { return e.station; }));\n",
     "matches": 1},
    {"why": "#251 - a station's past-window row reads exactly like its row inside the newest 16 again",
     "file": "tv/control_ui.html",
     "find": "             + ((e && e.window === false) ? ' older' : '') + ' for '\n",
     "replace": "             + ' for '\n",
     "matches": 1},
    {
        "why": "2026-09-29 (REG-1462) - the compare footer's age separator is breakable again, and at 375 its second line starts with a lone middot (Grok's cold look)",
        "file": "tv/control_ui.html",
        "find": "'<span class=\"fx-age\">\\u00a0·\\u00a0your list '",
        "replace": "'<span class=\"fx-age\"> · your list '",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - the fleet row renders films / river / triage upfront again (his 'only if clicked on')",
        "file": "control_ui.html",
        "find": "          + _tip(m) + _fleetOpenEyesHtml(m, !!(_me && m && m.machine === _me)) + '</div>';\n",
        "replace": "          + _fleetSysHtml(m, Date.now()) + _tip(m) + _fleetOpenEyesHtml(m, !!(_me && m && m.machine === _me)) + '</div>';\n",
        "matches": 1,
    },
    {
        "why": "2026-09-29 - a click on a PC opens the box without its films / river / triage (the backdoor is gone)",
        "file": "control_ui.html",
        "find": "      + _sys\n      + tabs;\n",
        "replace": "      + tabs;\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a route's age is the pin's age at send again, not ageS + how long the site has held the beacon",
        "file": "control_ui.html",
        "find": "    return ageS + Math.max(0, (now - rec) / 1000);\n",
        "replace": "    return ageS;\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a row with no record time reads its send-time age as if it were current",
        "file": "control_ui.html",
        "find": "    if (!isFinite(rec)) return null;\n",
        "replace": "    if (!isFinite(rec)) return ageS;\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a river with no lane map is drawn as an empty river (a confident zero)",
        "file": "control_ui.html",
        "find": "      out.push(_fleetPart('river', ['UNKNOWN'], { unk: true, why: String(rv.why || 'no lane answered') }));\n",
        "replace": "      out.push(_fleetPart('river', ['empty \\u2014 0 reels at every station'], { why: '' }));\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - 'standing aside for his game' reads as one more refusal on the fleet row",
        "file": "control_ui.html",
        "find": "      else if (lk === 'playing') st = 'standing aside for his game';\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the fleet stops drawing how its PC films and drains anywhere (the wire carries it, nothing reads it) - since 2026-09-29 it is drawn in the click box",
        "file": "control_ui.html",
        "find": "          + _fleetSysHtml(_fm, Date.now()) + '</div>';\n",
        "replace": "          + '</div>';\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - a renamed host's 'formerly' line is dropped",
        "file": "control_ui.html",
        "find": "    if (fm.length) {\n",
        "replace": "    if (false) {\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the river line prints a null backlog as a number",
        "file": "control_ui.html",
        "find": "    bits.push((typeof t.backlog === 'number')\n",
        "replace": "    bits.push((true)\n",
        "matches": 1,
    },
    {
        "why": "2026-09-28 - the river panel draws its lanes and not its triage lane (the fold's line is gone)",
        "file": "control_ui.html",
        "find": "                 /* outside the fold: the lane's one line reads with the river shut */\n                 + _shTriageLine(d);\n",
        "replace": "                 ;\n",
        "matches": 1,
    },
    {
        "why": "REG-1377 round 2 - a fact row is one middot-joined string again, and a wrap strands a middot (375: '\u00b7 CAPTURE 4 \u00b7')",
        "file": "control_ui.html",
        "find": "           + '<i class=\"fs-k\">' + escC(p.k) + '</i>' + _fleetFacts(p.f) + '</span>';\n",
        "replace": "           + '<i class=\"fs-k\">' + escC(p.k) + '</i> ' + escC(p.t) + '</span>';\n",
        "matches": 1,
    },
    {
        "why": "REG-1378 round 2 - the formerly line ages lastSeen with _fleetSince again ('just now' for an unreadable or future time)",
        "file": "control_ui.html",
        "find": "      var age = (isFinite(seen) && seen <= now) ? (now - seen) / 1000 : null;\n",
        "replace": "      var age = isFinite(seen) ? Math.max(0, (now - seen) / 1000) : 0;\n",
        "matches": 1,
    },
    {
        "why": "REG-1378 round 2 - _fleetSince reads a time it cannot parse as 'just now' again",
        "file": "control_ui.html",
        "find": "    if (!isFinite(ms)) return 'age UNKNOWN';\n",
        "replace": "    if (!isFinite(ms)) return 'just now';\n",
        "matches": 1,
    },
    {
        "why": "REG-1378 round 2 - a lane that has ticked with no readable outcome reads 'no tick yet' on the fleet row again",
        "file": "control_ui.html",
        "find": "      if (!lk) st = (tk === 0) ? 'no tick yet'\n",
        "replace": "      if (!lk) st = true ? 'no tick yet'\n",
        "matches": 1,
    },
    {
        "why": "REG-1378 round 2 - the river's own line says 'no tick yet' for a lane that has ticked",
        "file": "control_ui.html",
        "find": "      bits.push(t.ticks === 0 ? '<span class=\"shr-unk\">no tick yet since this console started</span>'\n",
        "replace": "      bits.push(true ? '<span class=\"shr-unk\">no tick yet since this console started</span>'\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
