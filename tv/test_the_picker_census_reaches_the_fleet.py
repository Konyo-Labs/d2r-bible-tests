# -*- coding: utf-8 -*-
"""#41 rank 22 (REG-1564) — WHAT EACH PC'S CHARACTER PICKER OFFERS REACHES THE FLEET, BESIDE WHAT ITS OWN DATABASE HOLDS.

The heart audit's rank 22: nothing on any PC reported what the character picker offers. His ALT showed an empty
picker for every mule slot for days (#174 v-B4) and no row anywhere carried the number - the picker's offer was
measured by nobody. Four joints, each built here WITH its law, each driven for real with only the edges stubbed:

  1. THE BOARD (bible.html) - `window._cbPickerCensus('tors')`, read-only: `offers` is the picker's Base Items rows
     for the Body Armor slot counted by DRIVING the picker's own list function (_cbRowsFor, cut out of _cbPickRows so
     the picker and the census share one list), `holds` is the same page's type table counting the slot on its own
     (every spawnable base whose type is `tors` or folds to it through ty[code][4] ancestry - the JSON's structure,
     never the rail the picker reads), `all` the rows of the tab the picker opens on. st.pick is never touched and
     nothing renders. An unreadable database is ok:false with a why and null counts - never 0. The board's own tally
     tick (window.__tallyPersist) hands it to the console in the same POST as the counts, inside the http(s) guard.
  2. THE CONSOLE (control_app) - /api/board_tally banks it (accept_handed_picker -> board_picker.json) BEFORE and
     independently of the counts, shaped and never re-derived; a garbled census is refused and never lands on a good
     one; `_picker_for_wire` reads it back with its own age; the beacon posts it per PC as `picker`.
  3. THE WORKER (functions/api/console.js) - the fixed key list keeps it (the seventh-joint shape `tally` names four
     times): counts clamped, words checked, an `ok` census without counts turned to ok:false, absent kept absent.
  4. THE FLEET (control_app /api/fleet, control_ui.html, console_doctor) - every peer's census rides through and his
     own row reads the local file (as the tally does, v2760); the click box prints 'picker offers N bases · database
     holds M' per PC, UNKNOWN in words when unread or an older build, a red 'picker short' word on the row ONLY when
     the two disagree; the doctor row 'picker census' goes MISSING naming the PC when any PC's two numbers disagree,
     UNKNOWN when a PC has not reported or the roster was never asked, OK when every PC agrees.

THE CORROBORATION IS RENDERER-AGAINST-DATA, said plainly: both numbers come from one JSON block, through two routes
(the list function with its rail, class rule, spawnable flag and dedupe; the type table's ancestry alone). The
baseline below tampers the rail in the fixture and watches the two sides part - the pair CAN disagree, so an
agreement is a measurement. Measured on the shipped block: tors 45 / 45 (134 rows in all), glov 15 / 15, belt 15 / 15.
`head` is NOT a comparable slot (its key is also the voodoo-heads type code), which is why the wire carries `tors`.

⚠ NOTHING REAL IS TOUCHED: the banked files are pointed into a temp dir, the beacon's network and state file are
stubbed, the worker runs in node over an in-memory KV, the card's helpers run in node over fixture rows. No console,
no window, no network. PROOF_NEEDS brings the worker and its import into heart2's sandbox. RED_PROOF below.
[[the-unjoined-end]] [[heart-first]] [[unknown-stays-unknown]] [[stale-reading]]
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
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

#: ⚠ BEFORE control_app is imported: its per-install identity (IDENTITY_PATH) and its state root follow TV_HIST, and the
#: beacon case below calls status_payload(), which MINTS an identity where none exists. Pointed at a scratch world, so a
#: run of this law never writes into tv/ of the tree it grades. [[feedback-fixtures-never-touch-live-data]]
_WORLD = tempfile.mkdtemp(prefix="picker_world_")
os.environ["TV_HIST"] = _WORLD

import control_app as ca  # noqa: E402
import worker_source as _ws  # noqa: E402  REG-1839 - the worker's top-level helpers, lifted with the shaper
import console_doctor as CD  # noqa: E402
import test_the_character_builder_is_their_builder as CB  # noqa: E402  the builder block's cutters and node stage
import test_console_fleet as CF  # noqa: E402  the real worker handler over an in-memory KV
from test_the_fleet_card_says_how_each_pc_films_and_drains import _run as _ui_run, NOW as UI_NOW, _iso  # noqa: E402

NODE = CB.NODE
API = os.path.join(ROOT, "functions", "api", "console.js")
BIBLE = os.path.join(ROOT, "bible.html")

#: heart2's sandbox is tv/ + bible.html; the worker and the module it imports live one level up
PROOF_NEEDS = ["../functions/api/console.js", "../functions/_middleware.js"]

RED_PROOF = [
    {
        "why": "joint 1 - the census stops driving the picker's list and copies the database's count: the two sides can never part",
        "file": "bible.html",
        "find": "      out.offers = rows.filter(function(x){ return _cbInTab(x, 'b', out.slot); }).length;\n",
        "replace": "      out.offers = out.holds;\n",
        "matches": 1,
    },
    {
        "why": "joint 1 - the board's tally tick stops handing the census over",
        "file": "bible.html",
        "find": "          _body.picker = _pc;\n",
        "replace": "          _body.picker = null;\n",
        "matches": 1,
    },
    {
        "why": "joint 2 - the route no longer banks the census the board handed over",
        "file": "control_app.py",
        "find": "            _pk_saved, _pk_why = accept_handed_picker(body, _who)\n",
        "replace": "            _pk_saved, _pk_why = False, \"tampered\"\n",
        "matches": 1,
    },
    {
        "why": "joint 2 - the beacon stops carrying it per PC",
        "file": "control_app.py",
        "find": "            \"picker\": _picker_for_wire(),\n",
        "replace": "            \"picker\": None,\n",
        "matches": 1,
    },
    {
        "why": "joint 3 - the worker's fixed key list drops it on arrival (the seventh-joint shape)",
        "file": "functions/api/console.js",
        "find": "    })(body.picker),\n",
        "replace": "    })(null),\n",
        "matches": 1,
    },
    {
        "why": "joint 4 - his own row stops reading the local file and shows the round trip",
        "file": "control_app.py",
        "find": "                    _fleet_overlay_local_picker(_fl, _fl[\"me\"])\n",
        "replace": "                    pass\n",
        "matches": 1,
    },
    {
        "why": "joint 4 - the card prints the picker's number under the database's label, so a disagreement reads as agreement",
        "file": "control_ui.html",
        "find": "'database holds ' + pk.holds, pkLab];\n",
        "replace": "'database holds ' + pk.offers, pkLab];\n",
        "matches": 1,
    },
    {
        "why": "joint 4 - the row's one word never appears, however far the two numbers part",
        "file": "control_ui.html",
        "find": "    if (pk.offers === pk.holds) return '';\n    var w = pk.offers < pk.holds ? 'picker short' : 'picker over';\n",
        "replace": "    return '';\n    var w = pk.offers < pk.holds ? 'picker short' : 'picker over';\n",
        "matches": 1,
    },
    {
        "why": "joint 4 - the doctor row stops going MISSING on a PC whose picker and database disagree",
        "file": "console_doctor.py",
        "find": "    if differ:\n        return MISSING, (\"on %d PC(s) the character picker does not offer",
        "replace": "    if False:\n        return MISSING, (\"on %d PC(s) the character picker does not offer",
        "matches": 1,
    },
    # ── the h22 verifier's findings, each fix proven to be what the case measures (2026-09-30) ──
    {
        "why": "h22 - the card reads a null picker (what the worker stores for an older console) as 'could not count'",
        "file": "control_ui.html",
        "find": "    if (pk === undefined || pk === null) {\n",
        "replace": "    if (pk === undefined) {\n",
        "matches": 1,
    },
    {
        "why": "h22 - a measured broken picker folds into the grey UNKNOWN on the card",
        "file": "control_ui.html",
        "find": "    } else if (typeof pk === 'object' && pk.ok !== true && pk.broken === true) {\n",
        "replace": "    } else if (false) {\n",
        "matches": 1,
    },
    {
        "why": "h22 - the row carries no word for a measured broken picker",
        "file": "control_ui.html",
        "find": "    if (pk && pk.ok !== true && pk.broken === true) {\n",
        "replace": "    if (false) {\n",
        "matches": 1,
    },
    {
        "why": "h22 - his own census is aged by the site record again (a 20 s census printed '10m ago')",
        "file": "control_ui.html",
        "find": "      pkF.push(_fleetAgeTxt((typeof pk.at === 'number' && pk.at > 0 && pk.at <= nowMs)\n",
        "replace": "      pkF.push(_fleetAgeTxt((false)\n",
        "matches": 1,
    },
    {
        "why": "h22 - a banked ok:false no longer overlays his row, so the site's older ok:true stands over it",
        "file": "control_app.py",
        "find": "    if not isinstance(mine, dict):\n        return 0\n    at = rec.get(\"at\") if isinstance(rec, dict) else None\n",
        "replace": "    if not isinstance(mine, dict) or not mine.get(\"ok\"):\n        return 0\n    at = rec.get(\"at\") if isinstance(rec, dict) else None\n",
        "matches": 1,
    },
    {
        "why": "h22 - his overlaid row loses the census's own clock",
        "file": "control_app.py",
        "find": "            pk[\"at\"] = at\n",
        "replace": "            pk[\"at\"] = None\n",
        "matches": 1,
    },
    {
        "why": "h22 - the wire stops saying a board-reported failure is broken",
        "file": "control_app.py",
        "find": "    out[\"broken\"] = rec.get(\"ok\") is False\n",
        "replace": "    out[\"broken\"] = False\n",
        "matches": 1,
    },
    {
        "why": "h22 - the worker's shaper drops broken on arrival",
        "file": "functions/api/console.js",
        "find": "        broken: p.ok !== true && p.broken === true,\n",
        "replace": "        broken: false,\n",
        "matches": 1,
    },
    {
        "why": "h22 - a census-only change is not news again (written up to 15 min late)",
        "file": "functions/api/console.js",
        "find": "    || pickerNews(prev) !== pickerNews(rec)\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "h22 - the doctor folds a measured broken picker into UNKNOWN",
        "file": "console_doctor.py",
        "find": "        if pk.get(\"ok\") is not True and pk.get(\"broken\") is True:\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "h22 - the doctor lets the site's older ok:true stand over his banked broken census",
        "file": "console_doctor.py",
        "find": "        if me and isinstance(local, dict) and (local.get(\"ok\") or local.get(\"broken\")) \\\n",
        "replace": "        if me and isinstance(local, dict) and (local.get(\"ok\")) \\\n",
        "matches": 1,
    },
    {
        "why": "h22 - a page whose scans all fail returns before handing its census over",
        "file": "bible.html",
        "find": "      if (_anyCount) window.LSR.setItem('d2r_tally', JSON.stringify(out));\n",
        "replace": "      if (!_anyCount) return false;\n      window.LSR.setItem('d2r_tally', JSON.stringify(out));\n",
        "matches": 1,
    },
]


def _src():
    with io.open(BIBLE, encoding="utf-8") as f:
        return f.read()


def _between_once(s, start, end):
    """The text from `start` up to `end`, both anchors counted once. [[source-reading-guard]]"""
    assert s.count(start) == 1, "anchor %r occurs %d times" % (start[:70], s.count(start))
    i = s.index(start)
    j = s.index(end, i + len(start))
    assert s.count(end) == 1, "anchor %r occurs %d times" % (end[:70], s.count(end))
    return s[i:j]


def _node_json(prog, timeout=120):
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise AssertionError("node could not run the shipped code - UNKNOWN, not passing: %s"
                             % (r.stderr or r.stdout)[-1500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


GOOD = {"ok": True, "slot": "tors", "type": "tors", "label": "Body Armor",
        "offers": 45, "holds": 45, "all": 134, "why": "", "at": None}


def _census(**kw):
    d = dict(GOOD)
    d["at"] = int(time.time() * 1000) - 120000
    d.update(kw)
    return d


# ══ JOINT 1 — THE BOARD ═══════════════════════════════════════════════════════════════════════════════════════════
@unittest.skipIf(NODE is None, "node is absent - this law RUNS the shipped builder block and will not re-implement it")
class TheBoardCountsWithoutOpeningThePicker(unittest.TestCase):

    def test_the_census_counts_the_slot_and_touches_nothing(self):
        out = CB._run(r"""
          OUT.c = window._cbPickerCensus('tors');
          OUT.pick = window._cbState().pick;
          OUT.drawn = !!ELS['cb-win'];
          OUT.glov = window._cbPickerCensus('glov');
          OUT.belt = window._cbPickerCensus('belt');
        """)
        c = out["c"]
        self.assertTrue(c["ok"], c)
        self.assertEqual((c["slot"], c["type"], c["label"]), ("tors", "tors", "Body Armor"), c)
        self.assertGreater(c["offers"], 0, "the picker offers no body armor at all: %r" % c)
        self.assertEqual(c["offers"], c["holds"],
                         "on the shipped block the picker's Base Items rows and the type table disagree: %r" % c)
        self.assertGreaterEqual(c["all"], c["offers"], "the All tab lists fewer rows than its Base tab: %r" % c)
        self.assertIsNone(out["pick"], "the census opened a picker (st.pick is set)")
        self.assertFalse(out["drawn"], "the census drew the builder window")
        for k in ("glov", "belt"):
            self.assertTrue(out[k]["ok"] and out[k]["offers"] == out[k]["holds"] and out[k]["offers"] > 0,
                            "%s: %r" % (k, out[k]))

    def test_the_census_is_what_the_picker_itself_lists(self):
        """DRIVEN: the census before any picker exists, then the real picker opened on the same slot."""
        out = CB._run(r"""
          OUT.c = window._cbPickerCensus('tors');
          window.openCharBuilder();
          window._cbOpenPick('slot', 'tors');
          OUT.pickSlot = window._cbState().pick && window._cbState().pick.slot;
          OUT.all = window._cbPickRows().length;
          window._cbQt('b');
          OUT.base = window._cbPickRows().length;
          window._cbClosePick();
          OUT.after = window._cbPickerCensus('tors');
        """)
        self.assertEqual(out["pickSlot"], "tors", "premise: the picker opened on the Body Armor slot")
        self.assertEqual(out["all"], out["c"]["all"], "the census's All count is not what the open picker lists")
        self.assertEqual(out["base"], out["c"]["offers"], "the census's offer is not what the picker's Base tab lists")
        self.assertEqual(out["after"]["offers"], out["c"]["offers"], "opening and closing a picker moved the census")

    def test_an_unreadable_database_is_unknown_never_zero(self):
        out = CB._run("OUT.c = window._cbPickerCensus('tors');", db="{")
        c = out["c"]
        self.assertFalse(c["ok"], c)
        self.assertIn("would not parse", c["why"])
        self.assertIsNone(c["offers"])
        self.assertIsNone(c["holds"])
        self.assertIsNone(c["all"])
        out = CB._run("OUT.c = window._cbPickerCensus('nosuchslot');")
        self.assertFalse(out["c"]["ok"])
        self.assertIn("no rail for the slot", out["c"]["why"])
        self.assertIsNone(out["c"]["offers"])

    def test_the_two_sides_can_part_so_an_agreement_is_a_measurement(self):
        """BASELINE (regression-guard §5): the rail the picker reads is emptied in the FIXTURE; the type table is
        untouched. The picker then offers nothing while the database still holds its body armors."""
        db = CB._db()
        self.assertEqual(db["rail"]["tors"][0][1], ["tors"], "premise: the Body Armor rail names the tors type")
        db["rail"]["tors"][0][1] = []
        out = CB._run("OUT.c = window._cbPickerCensus('tors');", db=json.dumps(db))
        c = out["c"]
        self.assertTrue(c["ok"], c)
        self.assertEqual(c["offers"], 0, "the picker still offers body armor with its rail emptied: %r" % c)
        self.assertGreater(c["holds"], 0, "the type table lost its body armors when the RAIL changed: %r" % c)
        self.assertNotEqual(c["offers"], c["holds"])

    def _persist(self, census_fn, protocol="http:"):
        s = _src()
        cut = _between_once(s, "  window.__tallyPersist = function(){",
                            "  try {\n    /* once the roster is up, then on a slow beat")
        prog = r"""
var window = globalThis;
var RAW = { d2r_lsrRoute: JSON.stringify({ v: 2, id: 'abc', p: 'main', pfx: '' }), d2r_rwMade: '{"Enigma":1}',
            d2r_setPieces: '["a"]', d2r_foundLog: '["b"]', d2r_owned: '["c"]' };
window.LSR = { getItem: function(k){ return RAW[k] == null ? null : RAW[k]; }, setItem: function(k, v){ RAW[k] = String(v); } };
window.funiScan = function(){ return { found: 3 }; };
window.fsetsScan = function(){ return { havePieces: 2, totalPieces: 135 }; };
window.d2rChronTotal = function(){ return 397; };
var RUNEWORD_CHRONICLE_TOTAL = 99;
var location = { protocol: %s };
var SENT = [], CALLS = 0;
var fetch = function(u, o){ SENT.push({ u: u, body: JSON.parse(o.body) }); return { catch: function(){} }; };
%s
%s
var r = window.__tallyPersist();
console.log(JSON.stringify({ r: r, sent: SENT, calls: CALLS, tally: JSON.parse(RAW['d2r_tally'] || 'null') }));
""" % (json.dumps(protocol), census_fn, cut)
        return _node_json(prog)

    def test_the_tally_tick_hands_the_census_to_the_console(self):
        good = "window._cbPickerCensus = function(slot){ CALLS++; return { ok: true, slot: slot, type: slot, label: 'Body Armor', offers: 45, holds: 45, all: 134, why: '', at: 5 }; };"
        v = self._persist(good)
        self.assertTrue(v["r"], "premise: the tally persisted")
        self.assertEqual(len(v["sent"]), 1, "premise: one hand-over went to the console: %r" % v["sent"])
        self.assertEqual(v["sent"][0]["u"], "/api/board_tally")
        pk = v["sent"][0]["body"].get("picker")
        self.assertEqual((pk or {}).get("offers"), 45, "the hand-over carries no picker census: %r" % pk)
        self.assertEqual((pk["slot"], pk["holds"], pk["all"]), ("tors", 45, 134))
        self.assertEqual(v["sent"][0]["body"]["sets"], {"have": 2, "total": 135}, "the counts stopped riding")
        self.assertNotIn("picker", v["tally"] or {}, "the census leaked into the LSR tally key (its shape is the counts')")
        # a page whose builder block is not up SAYS so
        v = self._persist("")
        pk = v["sent"][0]["body"].get("picker")
        self.assertEqual((pk or {}).get("ok"), False, "a page without the builder block sent no refusal: %r" % pk)
        self.assertIn("_cbPickerCensus", pk["why"])
        # h22 verifier: a page whose scans ALL fail still hands its census over - only the local tally write is skipped
        good_no_counts = good + " window.funiScan = undefined; window.fsetsScan = undefined; delete RAW.d2r_rwMade;"
        v = self._persist(good_no_counts)
        self.assertFalse(v["r"], "premise: no scan answered, so nothing was persisted")
        self.assertIsNone(v["tally"], "a row of nulls landed in the LSR tally")
        self.assertEqual(len(v["sent"]), 1, "a page whose scans all failed never handed its census over: %r" % v["sent"])
        self.assertEqual((v["sent"][0]["body"].get("picker") or {}).get("offers"), 45)
        # off disk: nothing is posted and the database is never parsed for it
        v = self._persist(good, protocol="file:")
        self.assertEqual(v["sent"], [], "a file:// page posted a hand-over")
        self.assertEqual(v["calls"], 0, "a file:// page computed the census (and parsed the database) for nothing")


# ══ JOINT 2 — THE CONSOLE ═════════════════════════════════════════════════════════════════════════════════════════
class _Banked(unittest.TestCase):
    """the three banked files pointed into a temp dir, the tally cache reset"""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="picker_bank_")
        self.addCleanup(shutil.rmtree, self.d, True)
        for name in ("_board_picker_path", "_board_tally_path", "_board_stores_path"):
            fn = os.path.join(self.d, name.replace("_board_", "board_").lstrip("_") + ".json")
            self.addCleanup(setattr, ca, name, getattr(ca, name))
            setattr(ca, name, (lambda p: (lambda: p))(fn))
        self._cache = dict(ca._TALLY_CACHE)
        self.addCleanup(lambda: ca._TALLY_CACHE.update(self._cache))

    @staticmethod
    def _post(path, doc):
        h = ca.Handler.__new__(ca.Handler)
        h.path = path
        body = json.dumps(doc).encode("utf-8")
        h.headers = {"Content-Length": str(len(body)), "Content-Type": "application/json"}
        h.rfile = io.BytesIO(body)
        out = []
        h._json = lambda code, obj: out.append((code, obj))
        h.do_POST()
        assert len(out) == 1, "the route answered %d times" % len(out)
        return out[0][1]

    WHO = {"id": "abc", "p": "main", "pfx": ""}


class TheConsoleBanksTheCensusBesideTheTally(_Banked):

    def test_the_route_banks_the_census_and_says_so(self):
        doc = {"v": 1, "who": self.WHO, "sets": {"have": 2, "total": 135}, "picker": _census()}
        reply = self._post("/api/board_tally", doc)
        self.assertTrue(reply.get("pickerSaved"), "the route did not bank the census: %r" % reply)
        self.assertIsNone(reply.get("pickerWhy"))
        rec = ca.board_picker_load()
        self.assertIsNotNone(rec, "nothing landed in board_picker.json")
        self.assertEqual((rec["ok"], rec["slot"], rec["offers"], rec["holds"], rec["all"]), (True, "tors", 45, 45, 134))
        self.assertEqual(rec["who"], self.WHO, "the census does not say whose it is")
        self.assertEqual(rec["at"], doc["picker"]["at"], "the board's own stamp was replaced")
        self.assertTrue(rec.get("bankedAt"))

    def test_a_census_is_banked_even_when_the_counts_are_refused(self):
        reply = self._post("/api/board_tally", {"v": 1, "who": self.WHO, "picker": _census(offers=44)})
        self.assertFalse(reply.get("ok"), "premise: a tally with no counts is refused")
        self.assertTrue(reply.get("pickerSaved"), "the refusal of the counts took the census with it: %r" % reply)
        self.assertEqual(ca.board_picker_load()["offers"], 44)

    def test_a_garbled_census_never_lands_on_a_good_one(self):
        self._post("/api/board_tally", {"v": 1, "who": self.WHO, "sets": {"have": 2, "total": 135}, "picker": _census()})
        for bad in ({"ok": True, "slot": "tors", "offers": "45", "holds": 45},
                    {"ok": True, "slot": "tors", "offers": True, "holds": 45},
                    {"ok": True, "slot": "Body Armor!", "offers": 45, "holds": 45},
                    "45/45", 7):
            reply = self._post("/api/board_tally", {"v": 1, "who": self.WHO, "sets": {"have": 2, "total": 135},
                                                    "picker": bad})
            self.assertFalse(reply.get("pickerSaved"), "a garbled census was banked: %r -> %r" % (bad, reply))
            self.assertTrue(reply.get("pickerWhy"), "the refusal names no reason: %r" % reply)
            self.assertEqual(ca.board_picker_load()["offers"], 45, "the garbled hand-over replaced the good census")
        # an older page hands nothing over: nothing banked, said as such, the good one stands
        reply = self._post("/api/board_tally", {"v": 1, "who": self.WHO, "sets": {"have": 2, "total": 135}})
        self.assertFalse(reply.get("pickerSaved"))
        self.assertIn("older", reply.get("pickerWhy") or "")
        self.assertEqual(ca.board_picker_load()["offers"], 45)

    def test_an_ok_false_census_is_banked_with_its_why(self):
        why = "the builder database would not parse (Unexpected token)"
        reply = self._post("/api/board_tally", {"v": 1, "who": self.WHO, "sets": {"have": 2, "total": 135},
                                                "picker": {"ok": False, "slot": "tors", "why": why,
                                                           "offers": None, "holds": None, "all": None}})
        self.assertTrue(reply.get("pickerSaved"), reply)
        rec = ca.board_picker_load()
        self.assertFalse(rec["ok"])
        self.assertEqual(rec["why"], why)
        self.assertIsNone(rec["offers"])
        wire = ca._picker_for_wire()
        self.assertFalse(wire["ok"])
        self.assertEqual(wire["why"], why, "the board's own reason did not reach the wire")

    def test_the_wire_reads_it_back_with_its_own_age(self):
        wire = ca._picker_for_wire()
        self.assertFalse(wire["ok"], "an unbanked census went out as a census: %r" % wire)
        self.assertIn("has not handed", wire["why"])
        self.assertIsNone(wire["offers"])
        self._post("/api/board_tally", {"v": 1, "who": self.WHO, "sets": {"have": 2, "total": 135}, "picker": _census()})
        wire = ca._picker_for_wire()
        self.assertTrue(wire["ok"], wire)
        self.assertEqual((wire["slot"], wire["label"], wire["offers"], wire["holds"], wire["all"]),
                         ("tors", "Body Armor", 45, 45, 134))
        self.assertGreaterEqual(wire["ageS"], 119.0, "the age is not the census's own (stamped 120 s ago): %r" % wire)
        self.assertLess(wire["ageS"], 600.0)
        # an unreadable file is UNKNOWN with a why, never a census
        with io.open(ca._board_picker_path(), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        wire = ca._picker_for_wire()
        self.assertFalse(wire["ok"])
        self.assertIn("will not read", wire["why"])

    def test_the_beacon_carries_it_per_pc(self):
        import urllib.request as _ur
        self._post("/api/board_tally", {"v": 1, "who": self.WHO, "sets": {"have": 2, "total": 135}, "picker": _census()})
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
        bdir = tempfile.mkdtemp(prefix="picker_beacon_")
        self.addCleanup(shutil.rmtree, bdir, True)
        self.addCleanup(setattr, ca, "_BEACON_STATE_PATH", ca._BEACON_STATE_PATH)
        ca._BEACON_STATE_PATH = os.path.join(bdir, ".tvd_beacon.json")
        try:
            with mock.patch.object(_ur, "urlopen", fake_urlopen):
                ca._console_beacon("hb")
        finally:
            for k, v in saved_env.items():
                if v is not None:
                    os.environ[k] = v
        pk = sent.get("body", {}).get("picker")
        self.assertIsInstance(pk, dict, "the beacon carries no picker census: %r" % sorted(sent.get("body", {})))
        self.assertEqual((pk["ok"], pk["slot"], pk["offers"], pk["holds"], pk["all"]), (True, "tors", 45, 45, 134))
        self.assertGreaterEqual(pk["ageS"], 119.0)
        self.assertNotIn("who", pk, "the board's route identity rode the public wire")


# ══ JOINT 3 — THE WORKER ══════════════════════════════════════════════════════════════════════════════════════════
def _shape(picker):
    """The SHIPPED worker shaper for `picker`, run in node."""
    with io.open(API, encoding="utf-8") as f:
        src = f.read()
    fn = _between_once(src, "    picker: (function (p) {", "    })(body.picker),") + "    })"
    fn = "(" + fn[len("    picker: "):] + ")"
    return _node_json(_ws.prelude(src) + "var shape = %s; console.log(JSON.stringify({ v: shape(%s) }));"
                      % (fn, json.dumps(picker)))["v"]


@unittest.skipIf(NODE is None, "node is absent - this law RUNS the real worker and will not re-implement it")
class TheWorkerKeepsIt(unittest.TestCase):

    def test_the_shaper_keeps_a_census_and_nulls_what_it_cannot_read(self):
        kept = _shape({"ok": True, "slot": "tors", "type": "tors", "label": "Body Armor", "offers": 45, "holds": 45,
                       "all": 134, "ageS": 130.5, "why": ""})
        self.assertEqual((kept["ok"], kept["slot"], kept["offers"], kept["holds"], kept["all"], kept["ageS"]),
                         (True, "tors", 45, 45, 134, 130.5), kept)
        self.assertEqual(kept["label"], "Body Armor")
        garbled = _shape({"ok": True, "slot": "Body Armor!", "offers": "45", "holds": -1, "all": 1e9, "ageS": -3,
                          "why": "  see   /Users/x  "})
        self.assertFalse(garbled["ok"], "an ok census without readable counts stayed ok: %r" % garbled)
        self.assertEqual((garbled["slot"], garbled["offers"], garbled["holds"], garbled["all"], garbled["ageS"]),
                         (None, None, None, None, None), garbled)
        self.assertTrue(garbled["why"])
        self.assertIsNone(_shape(None), "absent did not stay absent")
        self.assertIsNone(_shape("45/45"))
        refused = _shape({"ok": False, "why": "the builder database would not parse"})
        self.assertFalse(refused["ok"])
        self.assertIn("would not parse", refused["why"])

    def test_the_real_handler_stores_it(self):
        v = CF.run_handler(API, method="POST", body={"machine": "dean-pc", "nickname": "Dean", "install": "i-dean",
                                                     "ver": "v3526", "mode": "idle", "event": "hb",
                                                     "picker": _census(ageS=12.0)})
        self.assertEqual(v["status"], 200, v["text"][:300])
        recs = [json.loads(p["value"]) for p in v["puts"] if p["name"].startswith("console:")]
        self.assertEqual(len(recs), 1, "premise: the presence record was written once: %r" % [p["name"] for p in v["puts"]])
        pk = recs[0].get("picker")
        self.assertIsInstance(pk, dict, "the stored record carries no picker census: %r" % sorted(recs[0]))
        self.assertEqual((pk["ok"], pk["slot"], pk["offers"], pk["holds"], pk["all"], pk["ageS"]),
                         (True, "tors", 45, 45, 134, 12.0), pk)
        older = CF.run_handler(API, method="POST", body={"machine": "old-pc", "install": "i-old", "ver": "v3300",
                                                         "event": "hb"})
        rec = [json.loads(p["value"]) for p in older["puts"] if p["name"].startswith("console:")][0]
        self.assertIsNone(rec.get("picker"), "an older console's record grew a census it never sent")


    def test_a_census_only_change_is_news_and_broken_rides(self):
        """h22 verifier, on the real worker: `picker` was not in the MATERIAL list, so a beacon whose only change was the
        census (45/45 -> 40/45) wrote NOTHING for up to REFRESH_S. The record a first beacon stores is fed back as the
        prior, so every other field is identical and only the census moves."""
        body = {"machine": "dean-pc", "nickname": "Dean", "install": "i-dean", "ver": "v3526", "mode": "idle",
                "event": "hb", "picker": _census(ageS=12.0)}
        first = CF.run_handler(API, method="POST", body=body)
        prior = [p for p in first["puts"] if p["name"] == "console:dean-pc"]
        self.assertEqual(len(prior), 1, "premise: the first beacon stored its record")
        seed = {"console:dean-pc": json.loads(prior[0]["value"])}   # the harness stringifies seed values itself
        same = CF.run_handler(API, method="POST", body=dict(body, picker=_census(ageS=30.0)), seed=seed)
        self.assertEqual([p for p in same["puts"] if p["name"] == "console:dean-pc"], [],
                         "premise: an unchanged census (only its age moved) is not news")
        moved = CF.run_handler(API, method="POST", body=dict(body, picker=_census(offers=40, ageS=30.0)), seed=seed)
        recs = [json.loads(p["value"]) for p in moved["puts"] if p["name"] == "console:dean-pc"]
        self.assertEqual(len(recs), 1, "a census-only change was not written: %r" % [p["name"] for p in moved["puts"]])
        self.assertEqual(recs[0]["picker"]["offers"], 40)
        self.assertIs(_shape({"ok": False, "broken": True, "why": "the builder database would not parse"})["broken"], True,
                      "the shaper dropped a board-reported failure")
        self.assertIs(_shape(_census(broken=True))["broken"], False, "an ok census was stored as broken")


# ══ JOINT 4 — THE FLEET ═══════════════════════════════════════════════════════════════════════════════════════════
class TheFleetRelaysEveryPeerAndHisOwnRowReadsTheLocalFile(_Banked):

    def _fleet(self, online, offline):
        h = ca.Handler.__new__(ca.Handler)
        h.path = "/api/fleet"
        out = []
        h._json = lambda code, obj: out.append(obj)
        fl = {"ok": True, "online": online, "offline": offline}
        with mock.patch.object(ca, "fleet_presence", lambda force=False: json.loads(json.dumps(fl))), \
                mock.patch.object(ca, "fleet_origin_status", lambda *a, **k: {"ahead": None, "publishedVer": None}), \
                mock.patch.object(ca, "board_tally_load", lambda: None), \
                mock.patch.object(ca, "fleet_presence_last_good", lambda: (None, None)):
            h.do_GET()
        self.assertEqual(len(out), 1)
        return out[0]

    def test_a_peers_census_rides_through_and_his_own_row_reads_the_local_file(self):
        me = socket.gethostname().split(".")[0]
        self._post("/api/board_tally", {"v": 1, "who": self.WHO, "sets": {"have": 2, "total": 135}, "picker": _census()})
        peer = {"ok": True, "slot": "tors", "type": "tors", "label": "Body Armor", "offers": 44, "holds": 45,
                "all": 130, "ageS": 9.0, "why": None}
        stale_me = {"ok": True, "slot": "tors", "offers": 1, "holds": 1, "all": 1, "ageS": 3000.0, "why": None}
        got = self._fleet([{"machine": "PEER-A", "install": "aaaa", "ver": "v1", "picker": peer},
                           {"machine": me, "install": "mmmm", "ver": "v1", "picker": stale_me}],
                          [{"machine": "PEER-B", "install": "bbbb", "ver": "v1", "offline": True}])
        rows = {r["machine"]: r for r in (got.get("online") or []) + (got.get("offline") or [])}
        self.assertEqual(set(rows), {"PEER-A", me, "PEER-B"}, "premise: every row reached the payload")
        self.assertEqual(rows["PEER-A"]["picker"], peer, "a peer's census was changed on the way through")
        self.assertNotIn("picker", rows["PEER-B"], "an older peer grew a census")
        mine = rows[me]["picker"]
        self.assertEqual((mine["offers"], mine["holds"], mine["all"]), (45, 45, 134),
                         "his own row shows the round trip, not the local file: %r" % mine)
        self.assertTrue(mine.get("localRead"))
        self.assertLess(mine["ageS"], 600.0)

    def test_a_banked_broken_census_overlays_his_row_on_its_own_clock(self):
        """h22 verifier, driven through the real route: his board handed over ok:false ("the builder database would not
        parse"), it was banked, and /api/fleet still showed the site's older ok:true 45/45 on his row."""
        me = socket.gethostname().split(".")[0]
        at = int(time.time() * 1000) - 5000
        self._post("/api/board_tally", {"v": 1, "who": self.WHO,
                                        "picker": {"ok": False, "why": "the builder database would not parse", "at": at}})
        site_ok = {"ok": True, "slot": "tors", "offers": 45, "holds": 45, "all": 134, "ageS": 700.0, "why": None}
        got = self._fleet([{"machine": me, "install": "mmmm", "ver": "v1", "picker": site_ok}], [])
        mine = got["online"][0]["picker"]
        self.assertIs(mine.get("ok"), False, "the site's older ok:true stood over his banked ok:false: %r" % mine)
        self.assertIs(mine.get("broken"), True, "a board-reported failure lost its broken flag: %r" % mine)
        self.assertTrue(mine.get("localRead"))
        self.assertEqual(mine.get("at"), at, "his row does not carry the census's own clock: %r" % mine)

    def test_no_local_census_leaves_the_round_trip_in_place(self):
        me = socket.gethostname().split(".")[0]
        wire = {"ok": True, "slot": "tors", "offers": 45, "holds": 45, "all": 134, "ageS": 30.0, "why": None}
        got = self._fleet([{"machine": me, "install": "mmmm", "ver": "v1", "picker": wire}], [])
        self.assertEqual(got["online"][0]["picker"], wire, "an absent local file blanked or changed his row")


def _ui_parts(row):
    """_fleetSysParts over one fixture row -> {k: {t, unk, warn, why}}, plus the row's one-word chip"""
    out = _ui_run("var p = _fleetSysParts(%s, NOW); OUT.p = {}; p.forEach(function(x){ OUT.p[x.k] = { t: plain(x.t), f: x.f.map(plain), unk: !!x.unk, warn: !!x.warn, why: x.why }; });"
                  "OUT.chip = strip(_fleetPickerChip(%s));" % (json.dumps(row), json.dumps(row)))
    return out["p"], out["chip"]


def _ui_row(picker, t_ago_s=40):
    r = {"nickname": "Box", "machine": "box-1", "ver": "v3526", "t": _iso(UI_NOW - t_ago_s * 1000),
         "system": {"tree": "ok", "reels": 4}}
    if picker != "absent":
        r["picker"] = picker
    return r


@unittest.skipIf(NODE is None, "node is absent - this law RUNS the shipped card helpers and will not re-implement them")
class TheCardPrintsItPerPc(unittest.TestCase):

    def test_agreeing_numbers_print_both_and_the_row_stays_one_word(self):
        p, chip = _ui_parts(_ui_row({"ok": True, "slot": "tors", "label": "Body Armor", "offers": 45, "holds": 45,
                                     "all": 134, "ageS": 20.0, "why": None}))
        pk = p["picker"]
        self.assertEqual(pk["f"][:3], ["offers 45 bases", "database holds 45", "Body Armor"], pk)
        self.assertIn("134 rows on its All tab", pk["f"])
        self.assertEqual(pk["f"][-1], "1m ago", "the age is not the census's own plus the record's: %r" % pk["f"])
        self.assertFalse(pk["warn"] or pk["unk"], pk)
        self.assertEqual(chip, "", "the row grew a word while the two numbers agree")
        for f in pk["f"]:
            self.assertNotIn("·", f, "a fact carries a middot a wrap can strand (REG-1377): %r" % f)

    def test_disagreeing_numbers_warn_and_the_row_gets_one_word(self):
        p, chip = _ui_parts(_ui_row({"ok": True, "slot": "tors", "label": "Body Armor", "offers": 40, "holds": 45,
                                     "all": 130, "ageS": 20.0, "why": None}))
        pk = p["picker"]
        self.assertEqual(pk["f"][:2], ["offers 40 bases", "database holds 45"], pk)
        self.assertTrue(pk["warn"], "a disagreement did not warn: %r" % pk)
        self.assertFalse(pk["unk"])
        self.assertIn("hiding rows", pk["why"])
        self.assertEqual(chip.strip(), "picker short", "the row carries no word for a disagreeing PC: %r" % chip)
        _p, over = _ui_parts(_ui_row({"ok": True, "slot": "tors", "offers": 50, "holds": 45, "ageS": 1.0}))
        self.assertEqual(over.strip(), "picker over")

    def test_unread_and_older_builds_read_unknown_in_words(self):
        p, chip = _ui_parts(_ui_row("absent"))
        self.assertEqual((p["picker"]["t"], p["picker"]["unk"]), ("UNKNOWN · an older build", True), p["picker"])
        self.assertEqual(chip, "")
        why = "the builder database would not parse (Unexpected token)"
        p, chip = _ui_parts(_ui_row({"ok": False, "slot": "tors", "offers": None, "holds": None, "why": why}))
        self.assertEqual((p["picker"]["t"], p["picker"]["unk"], p["picker"]["why"]), ("UNKNOWN", True, why), p["picker"])
        self.assertEqual(chip, "")
        # h22 verifier: the REAL worker stores picker:null for a console older than the field, so null reads "an older
        # build" - the doctor's words for the same row - never "could not count" (a count nobody attempted)
        p, chip = _ui_parts(_ui_row(None))
        self.assertEqual((p["picker"]["t"], p["picker"]["unk"]), ("UNKNOWN · an older build", True), p["picker"])
        # an `ok` that arrives without its counts is UNKNOWN, never "offers 0"
        p, chip = _ui_parts(_ui_row({"ok": True, "slot": "tors", "offers": None, "holds": 45}))
        self.assertEqual(p["picker"]["t"], "UNKNOWN", p["picker"])
        self.assertEqual(chip, "")


    def test_a_measured_broken_picker_warns_in_its_board_s_words(self):
        """h22 verifier: ok:false WITH broken (the board counted and the count failed) is the empty-picker symptom - a
        warn line in the board's own words and a word on the row, never the grey UNKNOWN of 'nothing handed over'."""
        why = "the builder database would not parse (Unexpected token)"
        p, chip = _ui_parts(_ui_row({"ok": False, "broken": True, "slot": "tors", "offers": None, "holds": None,
                                     "why": why}))
        self.assertTrue(p["picker"]["warn"], "a measured broken picker did not warn: %r" % p["picker"])
        self.assertFalse(p["picker"]["unk"], "a measured broken picker read UNKNOWN: %r" % p["picker"])
        self.assertIn(why, p["picker"]["t"])
        self.assertEqual(chip.strip(), "picker broken", "the row carries no word for a broken picker: %r" % chip)

    def test_his_own_row_ages_the_census_on_its_own_clock(self):
        """h22 verifier: his own row carries the board's absolute `at` (read off this disk seconds ago); adding the site
        record's age to it printed '10m ago' for a 20 s census. The record here is 10 min old, the census 20 s."""
        pk = {"ok": True, "slot": "tors", "label": "Body Armor", "offers": 45, "holds": 45, "all": 134, "ageS": 20.0,
              "why": None, "localRead": True, "at": UI_NOW - 20000}
        p, _chip = _ui_parts(_ui_row(pk, t_ago_s=600))
        self.assertEqual(p["picker"]["f"][-1], "20s ago", "his census was aged by the site record: %r" % p["picker"]["f"])


class TheDoctorRowSaysWhichPcDisagrees(unittest.TestCase):

    def _row(self, name, picker):
        r = {"machine": name.lower() + "-pc", "nickname": name, "install": "i-" + name.lower()}
        if picker != "absent":
            r["picker"] = picker
        return r

    def test_missing_when_any_pc_disagrees_naming_it(self):
        st, why = CD.picker_census_verdict([
            self._row("Dean", {"ok": True, "slot": "tors", "label": "Body Armor", "offers": 40, "holds": 45}),
            self._row("Konyo", {"ok": True, "slot": "tors", "label": "Body Armor", "offers": 45, "holds": 45})])
        self.assertEqual(st, CD.MISSING, why)
        self.assertIn("Dean", why)
        self.assertIn("40", why)
        self.assertIn("45", why)
        self.assertNotIn("Konyo:", why)

    def test_unknown_when_a_pc_has_not_reported_never_ok(self):
        agree = {"ok": True, "slot": "tors", "label": "Body Armor", "offers": 45, "holds": 45}
        st, why = CD.picker_census_verdict([self._row("Konyo", agree), self._row("Dean", "absent")])
        self.assertEqual(st, CD.UNKNOWN, why)
        self.assertIn("Dean", why)
        self.assertIn("older build", why)
        self.assertIn("Konyo 45/45", why)
        st, why = CD.picker_census_verdict([self._row("Konyo", agree),
                                            self._row("ALT", {"ok": False, "why": "the builder database would not parse"})])
        self.assertEqual(st, CD.UNKNOWN, why)
        self.assertIn("would not parse", why)
        st, why = CD.picker_census_verdict([])
        self.assertEqual(st, CD.UNKNOWN, why)
        # an `ok` census without its counts is UNKNOWN, not an agreement and not a disagreement
        st, why = CD.picker_census_verdict([self._row("Dean", {"ok": True, "slot": "tors", "offers": None, "holds": 45})])
        self.assertEqual(st, CD.UNKNOWN, why)

    def test_ok_when_every_pc_agrees_with_the_numbers(self):
        agree = {"ok": True, "slot": "tors", "label": "Body Armor", "offers": 45, "holds": 45}
        st, why = CD.picker_census_verdict([self._row("Konyo", agree), self._row("Dean", agree)])
        self.assertEqual(st, CD.OK, why)
        self.assertIn("Konyo 45/45", why)
        self.assertIn("Dean 45/45", why)

    def test_his_own_row_is_read_from_the_local_census(self):
        me = socket.gethostname().split(".")[0]
        rows = [{"machine": me, "nickname": "Me", "picker": {"ok": True, "slot": "tors", "offers": 1, "holds": 1}}]
        local = {"ok": True, "slot": "tors", "label": "Body Armor", "offers": 40, "holds": 45}
        st, why = CD.picker_census_verdict(rows, me=me, local=local)
        self.assertEqual(st, CD.MISSING, "the local census did not override the round trip: %s" % why)
        st, _why = CD.picker_census_verdict(rows, me=me, local={"ok": False, "why": "not handed over"})
        self.assertEqual(st, CD.OK, "an unbanked local census blanked a row the wire could answer")
        # h22 verifier: a BANKED ok:false (his board measured it broken) overlays the site's older ok:true
        st, why = CD.picker_census_verdict(rows, me=me, local={"ok": False, "broken": True,
                                                                "why": "the builder database would not parse"})
        self.assertEqual(st, CD.MISSING, "his banked broken census lost to the round trip: %s" % why)

    def test_a_measured_broken_picker_is_missing_naming_it(self):
        rows = [self._row("Dean", {"ok": True, "slot": "tors", "offers": 45, "holds": 45}),
                self._row("Laptop", {"ok": False, "broken": True, "why": "the builder database would not parse"})]
        st, why = CD.picker_census_verdict(rows)
        self.assertEqual(st, CD.MISSING, "a measured broken picker folded into UNKNOWN: %s" % why)
        self.assertIn("Laptop", why)
        self.assertIn("would not parse", why)
        # the same row WITHOUT broken (nobody measured) stays UNKNOWN - the two are different facts
        rows[1]["picker"] = {"ok": False, "why": "the board has not handed a picker census over yet"}
        self.assertEqual(CD.picker_census_verdict(rows)[0], CD.UNKNOWN)

    def test_the_row_is_registered_reads_the_cache_and_never_fetches(self):
        names = [n for n, _fn in CD.CHECKS]
        self.assertIn("picker census", names, "the doctor carries no picker row")
        fn = dict(CD.CHECKS)["picker census"]
        self.assertEqual(CD.owner_of("picker census"), "me")
        fetches = []
        with mock.patch.object(ca, "fleet_presence", lambda *a, **k: fetches.append(1)), \
                mock.patch.object(ca, "_FLEET_PRESENCE_CACHE", {"t": 0.0, "d": None, "goodT": 0.0, "goodD": None}):
            st, why = fn()
        self.assertEqual(st, CD.UNKNOWN, why)
        self.assertIn("not asked", why)
        roster = {"ok": True, "online": [self._row("Dean", {"ok": True, "slot": "tors", "offers": 40, "holds": 45})],
                  "offline": []}
        with mock.patch.object(ca, "fleet_presence", lambda *a, **k: fetches.append(1)), \
                mock.patch.object(ca, "_picker_for_wire", lambda: {"ok": False, "why": "none"}), \
                mock.patch.object(ca, "_FLEET_PRESENCE_CACHE", {"t": time.time(), "d": roster, "goodT": time.time(),
                                                                "goodD": roster}):
            st, why = fn()
        self.assertEqual(st, CD.MISSING, why)
        self.assertIn("Dean", why)
        # unreachable now, but a roster was received earlier: that roster is what the card shows, so it is graded
        with mock.patch.object(ca, "fleet_presence", lambda *a, **k: fetches.append(1)), \
                mock.patch.object(ca, "_picker_for_wire", lambda: {"ok": False, "why": "none"}), \
                mock.patch.object(ca, "_FLEET_PRESENCE_CACHE", {"t": time.time(), "d": {"ok": False, "error": "x"},
                                                                "goodT": time.time(), "goodD": roster}):
            st, why = fn()
        self.assertEqual(st, CD.MISSING, why)
        self.assertEqual(fetches, [], "the doctor row fetched the roster instead of reading the cache")


if __name__ == "__main__":
    unittest.main(verbosity=2)
