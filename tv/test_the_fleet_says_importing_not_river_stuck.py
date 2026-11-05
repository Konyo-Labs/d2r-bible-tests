# -*- coding: utf-8 -*-
"""REG-3197 - THE FLEET SAYS "IMPORTING" OR "PROVING", NOT A RED "RIVER STUCK", WHILE A CENSUS IS BEING MADE CURRENT.

His words 2026-11-05: "i want the river flowing and the fleet rendering it properly ... this is too long waiting and
been said dozens of times". MEASURED on his /api/fleet at 21:01: every online PC's river.heart was {census: 'stale',
key: 'stale-at-boot', why: "census stale; lane: GitHub's proofs for this commit are being imported - the next proof tick
starts after, on what is still owed; ..."}, and the row drew it as the red alarm: "locks shut · rechecking" and, beside
it, red "river stuck" for reels the shut locks hold. Nothing said the import was running, how far it was, or that the
locks were its consequence; nothing said which locks were shut.

Now, joint by joint:
  * the console (control_app): river.heart.importing = {done, of, etaS, ver} read from _PROOF_RELEASE WHILE it runs
    (None counts when the import does not count - never a 0), None when no import runs; river.heart.owedHere =
    _SELF_PROVE['owed'] only while this PC's own lane proves; river.heart.locksShut / lockWhy / locksAgeS = which of
    the four river doors may() last named shut and the first one's reason, asked on the river lane's thread
    (_river_locks_note) through the SAME reading the doctor's river_locks row uses (_river_locks_read);
  * the worker (functions/api/console.js, its REAL shaper in node) forwards each, absent stays absent, a lock name that
    is not a lock id is dropped; an import starting or ending is news, its counts are not;
  * the row (control_ui.html, the REAL _fleetStuckChip in node) says, amber and first: "importing v3864's proofs ·
    1,240 of 2,928 · ~4 min" (or "importing GitHub's proofs" with no numbers), "proving 162 owed here"; the lock chip
    after them is amber, "locks shut · until GitHub's proofs land" / "· until this PC proves", and a lock line names
    the shut locks ("3 shut: frame release · vault sweep · vault apply"). Red stays for what neither explains: a lane
    that owes, and a stale census with no import and no proving.
RED_PROOF below.
"""
import datetime
import io
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import control_app as CA  # noqa: E402
import test_one_river_chip_per_row as H  # noqa: E402  (the cut-and-run pieces for _fleetStuckChip)
import test_each_console_says_its_own_system as S  # noqa: E402  (its worker slicer)
import worker_source as _ws  # noqa: E402

NOW = 1793900000000
ALT_WHY = ("census stale; lane: GitHub's proofs for this commit are being imported - the next proof tick starts after, "
           "on what is still owed; borrows from no PC - it must prove itself")
#: the measured ALT shapes at 21:01: a row the shut locks hold, and a lane row they do not explain
LOCKED_ROW = {"station": "ROUTED", "n": 4, "oldestS": 30 * 3600,
              "why": "route shut until this PC proves its own gates (census is STALE)"}
LANE_ROW = {"station": "PRINTER", "n": 1, "oldestS": 25752, "why": "vault lane: owes 8, 2 read(s) on record"}
THREE = ["frame.release", "vault.sweep_start", "vault.apply"]


def _chip(row, now=NOW):
    """The SHIPPED _fleetStuckChip over one fleet row, run in node (TZ=UTC). -> html"""
    with io.open(H.UI, encoding="utf-8") as fh:
        src = fh.read()
    boot = src[src.index(H.BOOT[0]):src.index("  var _fleetSay = function (k) {")]
    js = ("var window = {};\n"
          "function escC(x){ return String(x).replace(/&/g,'&amp;').replace(/\"/g,'&quot;')"
          ".replace(/</g,'&lt;').replace(/>/g,'&gt;'); }\n%s\n%s\n%s\n%s\n"
          "console.log(JSON.stringify(_fleetStuckChip(%s, %d)));") % (
        H._cut(src, H.AGO[0], H.AGO[1]), boot, H._cut(src, H.WHY[0], H.WHY[1]), H._cut(src, H.CHIP[0], H.CHIP[1]),
        json.dumps(row), now)
    r = subprocess.run([H._need_node(), "-"], input=js, capture_output=True, text=True, timeout=30,
                       env=dict(os.environ, TZ="UTC"))
    if r.returncode != 0:
        raise AssertionError("the cut chip did not run in node: %s" % r.stderr[-600:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _row(heart, stuck, age_s=60):
    t = datetime.datetime.fromtimestamp((NOW / 1000.0) - age_s, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return {"t": t, "presence": {"state": "online", "online": True, "via": "console", "ageS": age_s},
            "system": {"river": {"lanes": {"ROUTED": 17, "PRINTER": 3}, "ageS": 30, "stuck": stuck, "heart": heart}}}


def _plain(html):
    import re
    return re.sub(r"<[^>]+>", " ", html)


class TheConsoleSaysWhatTheCensusWaitsOn(unittest.TestCase):

    def test_the_import_is_read_only_while_it_runs(self):
        self.assertIsNone(CA.heart_importing({"running": False, "done": 5, "of": 9}, "v3864"))
        self.assertIsNone(CA.heart_importing(None, "v3864"))
        got = CA.heart_importing({"running": True, "done": 1240, "of": 2928, "etaS": 240}, lambda: "v3864")
        self.assertEqual(got, {"done": 1240, "of": 2928, "etaS": 240, "ver": "v3864"})
        # an import that does not count says so with None - never a 0 that reads as "nothing done"
        self.assertEqual(CA.heart_importing({"running": True}, "v3864"),
                         {"done": None, "of": None, "etaS": None, "ver": "v3864"})
        self.assertEqual(CA.heart_importing({"running": True, "done": 9, "of": 3}, "v?")["done"], None,
                         "a count past its own total crossed")
        self.assertIsNone(CA.heart_importing({"running": True}, "v?")["ver"])

    def test_owed_here_only_while_this_pc_proves(self):
        self.assertEqual(CA.heart_owed_here({"owed": 162, "running": True, "key": "busy"}), 162)
        self.assertEqual(CA.heart_owed_here({"owed": 162, "running": False, "key": "start"}), 162)
        self.assertIsNone(CA.heart_owed_here({"owed": 162, "running": False, "key": "busy"}),
                          "a PC that is not proving reported its owed laws as being worked off")
        self.assertIsNone(CA.heart_owed_here({"owed": None, "running": True, "key": "running"}))
        self.assertIsNone(CA.heart_owed_here({"owed": True, "running": True}))

    def test_the_beacon_carries_them_from_memory(self):
        sp = {"on": True, "worked": 0, "lastTs": NOW, "owed": 162, "key": "start", "census": "stale",
              "running": True, "say": "proving a slice"}
        rel = {"running": True, "done": 1240, "of": 2928, "etaS": 240, "state": "importing"}
        locks = {"ts": NOW - 30000, "shut": list(THREE), "why": "the heart census is STALE"}
        with mock.patch.object(CA, "_SELF_PROVE", sp), mock.patch.object(CA, "_PROOF_RELEASE", rel), \
                mock.patch.object(CA, "_RIVER_LOCKS_SEEN", locks), mock.patch.object(CA, "_app_ver", lambda: "v3864"), \
                mock.patch.object(CA, "_RIVER_LAST", {"good": None, "fail": None}):
            h = CA._river_for_wire(now_ms=NOW)["heart"]
        self.assertEqual(h["importing"], {"done": 1240, "of": 2928, "etaS": 240, "ver": "v3864"})
        self.assertEqual(h["owedHere"], 162)
        self.assertEqual(h["locksShut"], THREE)
        self.assertIn("STALE", h["lockWhy"])
        self.assertEqual(h["locksAgeS"], 30.0)
        with mock.patch.object(CA, "_SELF_PROVE", dict(sp, running=False, key="busy")), \
                mock.patch.object(CA, "_PROOF_RELEASE", dict(rel, running=False)), \
                mock.patch.object(CA, "_RIVER_LOCKS_SEEN", {"ts": None, "shut": None, "why": None}), \
                mock.patch.object(CA, "_RIVER_LAST", {"good": None, "fail": None}):
            h = CA._river_for_wire(now_ms=NOW)["heart"]
        self.assertIsNone(h["importing"])
        self.assertIsNone(h["owedHere"])
        self.assertIsNone(h["locksShut"], "locks never asked were sent as a list")

    def test_the_lane_asks_the_doors_through_the_doctors_one_reading(self):
        seen = {"ts": None, "shut": None, "why": None}

        def ask(lock):
            return (lock == "reel.route"), ("open on merit" if lock == "reel.route" else "the heart census is STALE")
        with mock.patch.object(CA, "_RIVER_LOCKS_SEEN", seen):
            got = CA._river_locks_note(now_ms=NOW, ask=ask)
        self.assertEqual(got["shut"], THREE)
        self.assertEqual(got["why"], "the heart census is STALE")
        self.assertEqual(got["ts"], NOW)

        def boom(lock):
            raise OSError("census unreadable")
        with mock.patch.object(CA, "_RIVER_LOCKS_SEEN", {"ts": None, "shut": ["x.y"], "why": None}) as s2:
            got = CA._river_locks_note(now_ms=NOW, ask=boom)
        self.assertIsNone(got["shut"], "an ask that raised was kept as a lock list")
        self.assertIn("OSError", got["why"])
        self.assertIn("_river_locks_read", CA._river_locks_doctor_row.__code__.co_names,
                      "the doctor row and the Fleet's lock line read the locks two ways")
        self.assertIn("_river_locks_note", CA._river_warm_loop.__code__.co_names,
                      "nothing asks the river doors, so the lock line never fills")


class TheWorkerForwardsThem(unittest.TestCase):

    def _heart(self, heart):
        return S.TheRelayShapesIt._shape(self, {"tree": "ok", "reels": 1, "river": {
            "lanes": None, "stuck": None, "heart": heart}})["river"]["heart"]

    def test_each_crosses_and_absent_stays_absent(self):
        got = self._heart({"census": "stale", "key": "stale-at-boot", "blind": None, "why": ALT_WHY,
                           "importing": {"done": 1240, "of": 2928, "etaS": 240, "ver": "v3864"}, "owedHere": 162,
                           "locksShut": THREE + ["<b>", "a b.c", "x"], "lockWhy": "the heart census is STALE",
                           "locksAgeS": 30})
        self.assertEqual(got["importing"], {"done": 1240, "of": 2928, "etaS": 240, "ver": "v3864"})
        self.assertEqual(got["owedHere"], 162)
        self.assertEqual(got["locksShut"], THREE, "a lock name that is not a lock id crossed")
        self.assertEqual(got["lockWhy"], "the heart census is STALE")
        self.assertEqual(got["locksAgeS"], 30)
        bare = self._heart({"census": "stale", "key": "stale-at-boot", "blind": None})
        for k in ("importing", "owedHere", "locksShut", "lockWhy"):
            self.assertNotIn(k, bare, "%s arrived on a beacon that never sent it" % k)
        odd = self._heart({"census": "stale", "importing": {"done": "x", "of": -1, "ver": "latest"}})
        self.assertEqual(odd["importing"], {"done": None, "of": None, "etaS": None, "ver": None})

    def test_an_import_starting_is_news_and_its_counts_are_not(self):
        with io.open(os.path.join(ROOT, "functions", "api", "console.js"), encoding="utf-8") as fh:
            src = fh.read()
        i = src.index("  const riverNews = (r) => {")
        j = src.index("\n  };\n", i) + len("\n  };\n")
        fn = src[i:j]
        out = S._node(_ws.prelude(src) + fn + "\nconsole.log(JSON.stringify([" + ",".join(
            "riverNews(%s)" % json.dumps({"system": {"river": {"lanes": None, "heart": h}}}) for h in (
                {"census": "stale", "key": "start"},
                {"census": "stale", "key": "start", "importing": {"done": 1, "of": 9}},
                {"census": "stale", "key": "start", "importing": {"done": 7, "of": 9}})) + "]));")
        self.assertNotEqual(out[0], out[1], "an import starting was not news - the row keeps its old words")
        self.assertEqual(out[1], out[2], "every import count made a KV write")


@unittest.skipIf(H.NODE is None, "node is not on this machine - this law RUNS the shipped chip and will not re-implement it")
class TheRowSaysImportingNotStuck(unittest.TestCase):

    def test_the_measured_alt_row_reads_importing_in_amber(self):
        heart = {"census": "stale", "key": "stale-at-boot", "blind": None, "why": ALT_WHY,
                 "importing": {"done": 1240, "of": 2928, "etaS": 240, "ver": "v3864"},
                 "locksShut": THREE, "lockWhy": "the heart census is STALE"}
        html = _chip(_row(heart, [LOCKED_ROW]))
        txt = _plain(html)
        self.assertIn("importing v3864’s proofs · 1,240 of 2,928 · ~4 min", txt, txt)
        self.assertIn('class="fleet-riverimport"', html)
        self.assertIn("locks shut · until GitHub’s proofs land", txt)
        self.assertIn('class="fleet-riverlocked"', html)
        self.assertNotIn("fleet-riverstuck", html, "the import's consequence was drawn as the red alarm: %r" % txt)
        self.assertNotIn("river stuck", txt)
        self.assertNotIn("rechecking", txt, "an import was called a recheck")
        self.assertIn("3 shut: frame release · vault sweep · vault apply", txt, "the lock line did not name the locks")
        self.assertIn("wait on the locks", txt, "the reels the locks hold lost their muted line")
        self.assertLess(txt.index("importing"), txt.index("locks shut"), "the cause was not said before its consequence")

    def test_an_import_with_no_counts_says_so_without_numbers(self):
        heart = {"census": "stale", "key": "stale-at-boot", "blind": None, "why": ALT_WHY,
                 "importing": {"done": None, "of": None, "etaS": None, "ver": None}}
        txt = _plain(_chip(_row(heart, [])))
        self.assertIn("importing GitHub’s proofs", txt)
        self.assertNotIn(" of ", txt.split("importing GitHub’s proofs")[1].split("locks")[0],
                         "an import that did not count drew a count")
        self.assertNotIn("~", txt)

    def test_proving_here_reads_its_owed_count(self):
        heart = {"census": "stale", "key": "start", "blind": 0, "owedHere": 162, "why": "census stale; 162 owed"}
        html = _chip(_row(heart, []))
        txt = _plain(html)
        self.assertIn("proving 162 owed here", txt)
        self.assertIn("locks shut · until this PC proves", txt)
        self.assertNotIn("fleet-riverstuck", html)

    def test_what_neither_explains_stays_red(self):
        # a stale census with no import and nothing proving: the lock chip is the alarm it was
        html = _chip(_row({"census": "stale", "key": "busy", "blind": None}, []))
        self.assertIn('class="fleet-riverstuck"', html)
        self.assertNotIn("fleet-riverlocked", html)
        # a lane that owes is not explained by an import: it stays red beside the amber import
        heart = {"census": "stale", "key": "stale-at-boot", "blind": None,
                 "importing": {"done": 1, "of": 2, "etaS": 60, "ver": "v3864"}}
        html = _chip(_row(heart, [LANE_ROW, LOCKED_ROW]))
        self.assertIn(">river stuck<", html, "a lane's own debt was hidden behind the import")
        self.assertIn(">vault lane owes 8<", html)

    def test_the_red_proof_finds_match_once(self):
        for p in RED_PROOF:
            with io.open(os.path.join(ROOT, p["file"]), encoding="utf-8") as fh:
                self.assertEqual(fh.read().count(p["find"]), p["matches"], p["why"])


RED_PROOF = [
    {"why": "REG-3197 - the beacon never says an import is running",
     "file": "tv/control_app.py",
     "find": "    if not isinstance(rel, dict) or rel.get(\"running\") is not True:\n        return None\n",
     "replace": "    if True:\n        return None\n",
     "matches": 1},
    {"why": "REG-3197 - the import's own counts are dropped",
     "file": "tv/control_app.py",
     "find": "    done, of, eta = _n(rel.get(\"done\")), _n(rel.get(\"of\")), _n(rel.get(\"etaS\"))\n",
     "replace": "    done, of, eta = None, None, None\n",
     "matches": 1},
    {"why": "REG-3197 - owed laws are reported as being worked off on a PC that is not proving",
     "file": "tv/control_app.py",
     "find": "    if sp.get(\"running\") is True or sp.get(\"key\") in SP_PROVING_KEYS:\n        return owed\n    return None\n",
     "replace": "    return owed\n",
     "matches": 1},
    {"why": "REG-3197 - the wire carries no import",
     "file": "tv/control_app.py",
     "find": "    out[\"heart\"][\"importing\"] = heart_importing(_PROOF_RELEASE, _app_ver)\n",
     "replace": "    out[\"heart\"][\"importing\"] = None\n",
     "matches": 1},
    {"why": "REG-3197 - the lane never keeps which locks are shut",
     "file": "tv/control_app.py",
     "find": "        _RIVER_LOCKS_SEEN.update(ts=now, shut=[l for l, _w in shut], why=(shut[0][1] if shut else None))\n",
     "replace": "        _RIVER_LOCKS_SEEN.update(ts=now, shut=[], why=None)\n",
     "matches": 1},
    {"why": "REG-3197 - nothing asks the river doors, so the lock line never fills",
     "file": "tv/control_app.py",
     "find": "            _river_locks_note()\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "REG-3197 - the worker drops the import on arrival",
     "file": "functions/api/console.js",
     "find": "          if (hi && typeof hi === 'object' && !Array.isArray(hi)) {\n",
     "replace": "          if (false) {\n",
     "matches": 1},
    {"why": "REG-3197 - an import starting is not news, so the row keeps its old words for a refresh",
     "file": "functions/api/console.js",
     "find": "                           (h.importing && typeof h.importing === 'object') ? 'importing' : null,\n",
     "replace": "                           null,\n",
     "matches": 1},
    {"why": "REG-3197 - the row says nothing about the import (his 21:01 Fleet)",
     "file": "tv/control_ui.html",
     "find": "    if (_imp) {\n      var _impWords",
     "replace": "    if (false) {\n      var _impWords",
     "matches": 1},
    {"why": "REG-3197 - the lock chip is the red alarm again while the import or the prover explains it",
     "file": "tv/control_ui.html",
     "find": "      var _lockCalm = !!_imp || (_owedHere !== null && !_memWait);\n",
     "replace": "      var _lockCalm = false;\n",
     "matches": 1},
    {"why": "REG-3197 - the lock line does not name which locks are shut",
     "file": "tv/control_ui.html",
     "find": "      if (_shutNames.length) {\n",
     "replace": "      if (false) {\n",
     "matches": 1},
    {"why": "REG-3197 - proving here is not said",
     "file": "tv/control_ui.html",
     "find": "    if (_owedHere !== null) {\n      bits.push(",
     "replace": "    if (false) {\n      bits.push(",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
