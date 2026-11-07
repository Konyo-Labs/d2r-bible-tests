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

The adversarial review of this item (reproduced on his live /api/fleet at 22:08 and 22:27) found four more holes, closed
here too:
  * A BLIND GATE IS NOT LATENESS. Konyo · ALT {census stale, key running, blind 1, owed 1,130} and OLD PC ALT {blind 3}
    drew amber "locks shut · until this PC proves" - but self_arming refuses on a recorded BLIND before it looks at
    staleness and never softens it, so proving the owed laws does not open those locks. The chip stays red and says
    "· 1 gate blind"; a blind count nobody sent (no census count, no lock reason) never gets the calm words. The boot
    window now sends the boot census's own BLIND count beside its state (_BOOT_CENSUS).
  * THE IMPORT ENDING IS NOT A 10-MINUTE RED RECHECK. When _PROOF_RELEASE stopped running, the row went back to the 21:01
    red "locks shut · rechecking" with a why still saying the proofs "are being imported", until the next proof tick up to
    SELF_PROVE_EVERY_TICKS (10 min) away. The tick the import held now runs on the first rescue tick after it ends
    (_SELF_PROVE['afterImport']), and in that gap the wire says what happened: importing.landed, a why that says the
    import stopped, the row "v3864's proofs imported · the proof check runs next" in amber.
  * THE VERSION IS THE ONE IMPORTED FOR. heart.importing.ver was the RUNNING stamp, while _proof_release_tick imports
    HEAD's proofs (a held relaunch leaves them apart). The import records the stamp of the clean checkout it imports for
    (_disk_ver, the status check refuses a dirty one) as it starts; no recorded stamp says "GitHub's proofs".
  * A LANE THAT OWES 0 IS NOT A DEBT. His ALT row drew red "vault lane owes 0" beside "river stuck"; the debt chip is
    drawn only for a lane that owes something (the stuck chip's hover keeps the sentence).
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


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()
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
        self.assertIsNone(CA.heart_importing({"running": False, "done": 5, "of": 9, "ver": "v3864"}))
        self.assertIsNone(CA.heart_importing(None))
        got = CA.heart_importing({"running": True, "done": 1240, "of": 2928, "etaS": 240, "ver": "v3864"})
        self.assertEqual(got, {"done": 1240, "of": 2928, "etaS": 240, "ver": "v3864"})
        # an import that does not count says so with None - never a 0 that reads as "nothing done"
        self.assertEqual(CA.heart_importing({"running": True, "ver": "v3864"}),
                         {"done": None, "of": None, "etaS": None, "ver": "v3864"})
        self.assertEqual(CA.heart_importing({"running": True, "done": 9, "of": 3})["done"], None,
                         "a count past its own total crossed")
        self.assertIsNone(CA.heart_importing({"running": True, "ver": "v?"})["ver"])

    def test_the_version_is_the_one_imported_for_not_the_running_stamp(self):
        # the reviewer on r3: CA.heart_importing({'running': True, 'sha': 'aaaa...'}, lambda: 'v3864') named the RUNNING
        # stamp, while the import is HEAD's. No recorded stamp is no stamp - never the running one.
        with mock.patch.object(CA, "_app_ver", lambda: "v3864"):
            self.assertIsNone(CA.heart_importing({"running": True, "sha": "a" * 40})["ver"],
                              "the running stamp was named for proofs imported for HEAD")
        rel = {"state": None, "sha": None, "running": False, "why": "x"}
        sha = "b" * 40

        def git(argv, **kw):
            import subprocess as _s
            if argv[1:3] == ["rev-parse", "HEAD"]:
                return _s.CompletedProcess(argv, 0, sha + "\n", "")
            if argv[1] == "status":
                return _s.CompletedProcess(argv, 0, "", "")
            raise AssertionError(argv)
        fake = mock.MagicMock()
        fake.load_state.return_value = {}
        fake.owed.return_value = True
        held = []
        with mock.patch.dict(sys.modules, {"proof_release": fake}), mock.patch.object(CA, "_PROOF_RELEASE", rel), \
                mock.patch.object(CA, "_disk_ver", lambda: "v3866"), mock.patch.object(CA, "_app_ver", lambda: "v3864"):
            CA._proof_release_tick(_thread=held.append, _git_run=git, _busy=lambda: None)
            self.assertEqual(rel.get("ver"), "v3866", "the import did not record the stamp it imports for")
            self.assertEqual(CA.heart_importing(rel)["ver"], "v3866")

    def test_a_landed_import_is_said_as_landed_until_the_prover_ticks(self):
        rel = {"running": False, "state": "imported", "done": 2928, "of": 2928, "etaS": 3, "ver": "v3864"}
        self.assertEqual(CA.heart_importing(rel, {"afterImport": True}),
                         {"done": 2928, "of": 2928, "etaS": None, "ver": "v3864", "landed": True})
        self.assertIsNone(CA.heart_importing(rel, {}), "an import the prover already took over was still sent")
        self.assertIsNone(CA.heart_importing(dict(rel, state="refused"), {"afterImport": True}),
                          "a refused import was called landed")

    def test_the_tick_the_import_held_runs_as_soon_as_it_ends(self):
        sp = {"on": None, "lastTs": None, "key": None, "say": "not yet"}
        rel = {"running": True, "state": "importing"}
        ran, beacons = [], []

        def tick():
            ran.append(1)
            sp.clear()
            sp.update({"key": "busy", "census": "stale", "lastTs": NOW, "say": "busy"})
        with mock.patch.object(CA, "_SELF_PROVE", sp), mock.patch.object(CA, "_PROOF_RELEASE", rel), \
                mock.patch.object(CA, "_self_prove_tick", tick), \
                mock.patch.object(CA, "_console_beacon_async", beacons.append):
            n = CA.SELF_PROVE_FIRST_TICK
            self.assertEqual(CA._self_prove_dispatch(n), "tick")
            self.assertEqual(ran, [], "a proof started beside the import of the same proofs")
            self.assertTrue(sp.get("afterImport"))
            self.assertIsNone(CA._self_prove_dispatch(n + 1), "a tick ran while the import still ran")
            rel["running"] = False
            rel["state"] = "imported"
            self.assertEqual(CA._self_prove_dispatch(n + 2), "tick",
                             "the held tick waited for its 10-minute slot after the import ended")
            self.assertEqual(ran, [1])
            self.assertIsNone(CA._self_prove_dispatch(n + 3), "the held tick ran twice")
            self.assertEqual(ran, [1])

    def test_the_gap_after_the_import_says_what_happened(self):
        sp = {"on": None, "lastTs": None, "key": None, "owed": None, "afterImport": True,
              "say": "GitHub's proofs for this commit are being imported - the next proof tick starts after, on what "
                     "is still owed"}
        rel = {"running": False, "state": "imported", "why": "imported 2928 proofs", "ver": "v3864",
               "done": 2928, "of": 2928}
        with mock.patch.object(CA, "_SELF_PROVE", sp), mock.patch.object(CA, "_PROOF_RELEASE", rel), \
                mock.patch.object(CA, "_BOOT_CENSUS", {"asked": True, "state": "stale", "blind": 0}), \
                mock.patch.object(CA, "_RIVER_LOCKS_SEEN", {"ts": None, "shut": None, "why": None}), \
                mock.patch.object(CA, "_RIVER_LAST", {"good": None, "fail": None}):
            h = CA._river_for_wire(now_ms=NOW)["heart"]
        self.assertEqual(h["key"], "stale-at-boot")
        self.assertEqual(h["blind"], 0, "the boot census's BLIND count did not ride with its state")
        self.assertEqual((h["importing"] or {}).get("landed"), True, h)
        self.assertNotIn("being imported", h["why"], "a finished import was still said to be running: %r" % h["why"])
        self.assertIn("stopped importing (imported", h["why"])
        self.assertIn("still owed", h["why"])

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
        rel = {"running": True, "done": 1240, "of": 2928, "etaS": 240, "state": "importing", "ver": "v3864"}
        locks = {"ts": NOW - 30000, "shut": list(THREE), "why": "the heart census is STALE"}
        with mock.patch.object(CA, "_SELF_PROVE", sp), mock.patch.object(CA, "_PROOF_RELEASE", rel), \
                mock.patch.object(CA, "_RIVER_LOCKS_SEEN", locks), \
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

    def test_the_doors_are_not_asked_while_he_plays(self):
        # the reviewer on r3: four may() calls (~0.6 s of gate hashing) ran on every pass even while he played
        self.assertFalse(CA._river_locks_due(playing=True), "the river doors were asked while he played")
        self.assertTrue(CA._river_locks_due(playing=False))
        src = _read(os.path.join(HERE, "control_app.py"))
        self.assertEqual(src.count("            if _river_locks_due():\n                _river_locks_note()\n"), 1,
                         "the river lane asks the doors without asking whether he plays")


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
        odd = self._heart({"census": "stale", "importing": {"done": "x", "of": -1, "ver": "latest", "landed": "yes"}})
        self.assertEqual(odd["importing"], {"done": None, "of": None, "etaS": None, "ver": None})
        landed = self._heart({"census": "stale", "importing": {"done": 9, "of": 9, "ver": "v3864", "landed": True}})
        self.assertIs(landed["importing"].get("landed"), True, "a landed import crossed as a running one")

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
                {"census": "stale", "key": "start", "importing": {"done": 7, "of": 9}},
                {"census": "stale", "key": "start", "importing": {"done": 9, "of": 9, "landed": True}})) + "]));")
        self.assertNotEqual(out[0], out[1], "an import starting was not news - the row keeps its old words")
        self.assertEqual(out[1], out[2], "every import count made a KV write")
        self.assertNotEqual(out[2], out[3], "an import landing was not news - the row kept 'importing'")


@unittest.skipIf(H.NODE is None, "node is not on this machine - this law RUNS the shipped chip and will not re-implement it")
class TheRowSaysImportingNotStuck(unittest.TestCase):

    def test_the_measured_alt_row_reads_importing_in_amber(self):
        heart = {"census": "stale", "key": "stale-at-boot", "blind": 0, "why": ALT_WHY,
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

    def test_an_import_whose_count_is_complete_says_it_is_finishing(self):
        """#13 (GrokBot 6700580776: Dean "importing v3876's proofs · 6,166 of 6,166" after the count finished)"""
        heart = {"census": "stale", "key": "stale-at-boot", "blind": 0, "why": ALT_WHY,
                 "importing": {"done": 6166, "of": 6166, "etaS": 0, "ver": "v3876"}}
        txt = _plain(_chip(_row(heart, [])))
        self.assertIn("finishing the import of v3876’s proofs · all 6,166 checked", txt, txt)
        self.assertNotIn("6,166 of 6,166", txt, "a complete count still reads as an import in progress")
        self.assertNotIn("importing v3876", txt)

    def test_an_import_with_no_counts_says_so_without_numbers(self):
        heart = {"census": "stale", "key": "stale-at-boot", "blind": None, "why": ALT_WHY,
                 "importing": {"done": None, "of": None, "etaS": None, "ver": None}}
        txt = _plain(_chip(_row(heart, [])))
        self.assertIn("importing GitHub’s proofs", txt)
        self.assertNotIn(" of ", txt.split("importing GitHub’s proofs")[1].split("locks")[0],
                         "an import that did not count drew a count")
        self.assertNotIn("~", txt)

    def test_proving_here_reads_its_owed_count(self):  # blind 0: a known count, no blind gate
        heart = {"census": "stale", "key": "start", "blind": 0, "owedHere": 162, "why": "census stale; 162 owed"}
        html = _chip(_row(heart, []))
        txt = _plain(html)
        self.assertIn("proving 162 owed here", txt)
        self.assertIn("locks shut · until this PC proves", txt)
        self.assertNotIn("fleet-riverstuck", html)

    def test_nothing_owed_and_a_current_census_is_ready_never_proving_zero(self):
        """v3880 (his 11-07 screenshot: "proving 0 owed here" on his own row - "if im done proving it should say battle ready")"""
        txt = _plain(_chip(_row({"census": "current", "key": "current", "blind": 0, "owedHere": 0, "why": ""}, [])))
        self.assertIn("ready for battle · every law proved here", txt, txt)
        self.assertNotIn("proving 0", txt)
        blind = _plain(_chip(_row({"census": "current", "key": "current", "blind": 2, "owedHere": 0, "why": ""}, [])))
        self.assertNotIn("ready for battle", blind, "a PC with blind gates read as ready")
        stale = _plain(_chip(_row({"census": "stale", "key": "start", "blind": 0, "owedHere": 0, "why": ""}, [])))
        self.assertIn("nothing owed here · its proof check runs next", stale, stale)
        self.assertNotIn("proving 0", stale)

    def test_a_landed_import_is_amber_not_a_red_recheck(self):
        # the reviewer on r3: the import just FINISHED and the prover had not ticked - 'fleet-riverstuck | locks shut ·
        # rechecking' with a why still saying "being imported"
        heart = {"census": "stale", "key": "stale-at-boot", "blind": 0,
                 "why": "census stale; lane: GitHub's proofs for this commit stopped importing (imported) - the proof "
                        "check runs on its next 10 s tick, on what is still owed",
                 "importing": {"done": 2928, "of": 2928, "etaS": None, "ver": "v3864", "landed": True}}
        html = _chip(_row(heart, [LOCKED_ROW]))
        txt = _plain(html)
        self.assertIn("v3864’s proofs imported · the proof check runs next", txt, txt)
        self.assertIn("locks shut · until the proof check runs", txt)
        self.assertNotIn("rechecking", txt, "a landed import was drawn as the red recheck")
        self.assertNotIn("fleet-riverstuck", html)
        self.assertNotIn("importing v3864", txt, "a finished import was still said to be importing")

    def test_a_blind_gate_is_never_until_this_pc_proves(self):
        # his live Konyo · ALT at 22:27 {census stale, key running, blind 1, owed 1130}: proving does not open its locks
        heart = {"census": "stale", "key": "running", "blind": 1, "owed": 1130, "owedHere": 1130,
                 "why": "census stale; lane: a proof is running", "locksShut": ["reel.route"] + THREE,
                 "lockWhy": "the heart2 PROOF census is STALE (not the Heart panel's live census)"}
        html = _chip(_row(heart, []))
        txt = _plain(html)
        self.assertIn("proving 1,130 owed here", txt, "the proving itself stopped being said")
        self.assertIn("locks shut · 1 gate blind", txt, txt)
        self.assertNotIn("until this PC proves", txt, "a blind gate was blamed on lateness: %r" % txt)
        self.assertIn('class="fleet-riverstuck"', html)
        self.assertNotIn("fleet-riverlocked", html)
        self.assertIn("BLIND is not STALE", html, "the hover does not say why proving will not open them")
        # OLD PC ALT at 22:08: no count on the row, but the lock's own reason says BLIND
        heart = {"census": "stale", "key": "start-small", "blind": None, "owedHere": 116,
                 "lockWhy": "3 instrument(s) are BLIND (a, b, c) - a surface may not arm itself", "locksShut": THREE}
        txt = _plain(_chip(_row(heart, [])))
        self.assertIn("locks shut · gates blind", txt, txt)
        self.assertNotIn("until this PC proves", txt)
        # an import over a blind gate: the import is still said, the lock is not blamed on it
        heart = {"census": "stale", "key": "stale-at-boot", "blind": 2,
                 "importing": {"done": 1, "of": 9, "etaS": 60, "ver": "v3864"}}
        txt = _plain(_chip(_row(heart, [])))
        self.assertIn("importing v3864’s proofs", txt)
        self.assertIn("locks shut · 2 gates blind", txt)
        self.assertNotIn("until GitHub", txt)

    def test_an_unknown_blind_count_never_gets_the_calm_words(self):
        heart = {"census": "stale", "key": "stale-at-boot", "blind": None,
                 "importing": {"done": 1, "of": 9, "etaS": 60, "ver": "v3864"}}
        html = _chip(_row(heart, []))
        self.assertNotIn("fleet-riverlocked", html, "amber was drawn over a blind count nobody sent")
        self.assertNotIn("until GitHub", _plain(html))

    def test_a_lane_that_owes_nothing_is_not_a_debt(self):
        # his live Konyo · ALT at 22:27: PRINTER 1 "vault lane: owes 0, ..." drew red "vault lane owes 0"
        alt = {"station": "PRINTER", "n": 1, "oldestS": 30387,
               "why": "vault lane: owes 0, 2 read(s) on record; 14 ruled empty by the triage"}
        html = _chip(_row({"census": "current", "key": "current", "blind": 0}, [alt]))
        self.assertNotIn("owes 0", _plain(html), "a lane that owes nothing was drawn as a debt")
        self.assertIn(">river stuck<", html, "a reel 8 h at a station its lane does not owe stopped being stuck")
        self.assertIn("vault lane: owes 0", html, "the stuck chip's hover lost the lane's sentence")
        html = _chip(_row({"census": "current", "key": "current", "blind": 0}, [LANE_ROW]))
        self.assertIn(">vault lane owes 8<", html, "a real debt stopped naming itself")

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
    {"why": "v3880 - a PC with nothing owed reads 'proving 0 owed here' again (his 11-07 screenshot)",
     "file": "tv/control_ui.html",
     "find": "    if (_owedHere !== null && _owedHere > 0) {", "replace": "    if (_owedHere !== null) {", "matches": 1},
    {"why": "v3880 - a PC with blind gates reads 'ready for battle'",
     "file": "tv/control_ui.html",
     "find": "census === 'current' && !(typeof hs.blind === 'number' && hs.blind > 0)) {",
     "replace": "census === 'current') {", "matches": 1},
    {"why": "#13 - a complete count reads 'importing v3876's proofs · 6,166 of 6,166' again",
     "file": "tv/control_ui.html",
     "find": "      var _allIn = !_landed && _whole(_imp.done) && _whole(_imp.of) && _imp.of > 0 && _imp.done >= _imp.of;\n",
     "replace": "      var _allIn = false;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3197 - the beacon never says an import is running",
     "file": "tv/control_app.py",
     "find": "    if not (running or landed):\n        return None\n",
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
     "find": "    out[\"heart\"][\"importing\"] = heart_importing(_rel, _sp)\n",
     "replace": "    out[\"heart\"][\"importing\"] = None\n",
     "matches": 1},
    {"why": "REG-3197 (the reviewer on r3) - the running stamp is named for proofs imported for HEAD",
     "file": "tv/control_app.py",
     "find": "    v = rel.get(\"ver\")\n    v = v if isinstance(v, str)",
     "replace": "    v = _app_ver()\n    v = v if isinstance(v, str)",
     "matches": 1},
    {"why": "REG-3197 (the reviewer on r3) - the import never records the stamp it imports for",
     "file": "tv/control_app.py",
     "find": "    _PROOF_RELEASE.update(running=True, sha=head, state=\"importing\", ver=_for_ver,\n",
     "replace": "    _PROOF_RELEASE.update(running=True, sha=head, state=\"importing\",\n",
     "matches": 1},
    {"why": "REG-3197 (the reviewer on r3) - a landed import is dropped, so the row goes back to the red recheck",
     "file": "tv/control_app.py",
     "find": "    landed = (not running and isinstance(sp, dict) and sp.get(\"afterImport\") is True\n",
     "replace": "    landed = (False and isinstance(sp, dict) and sp.get(\"afterImport\") is True\n",
     "matches": 1},
    {"why": "REG-3197 (the reviewer on r3) - the tick the import held waits up to 10 min after it ends",
     "file": "tv/control_app.py",
     "find": "    if step != \"tick\" and _SELF_PROVE.get(\"afterImport\") is True and not _PROOF_RELEASE.get(\"running\"):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3197 (the reviewer on r3) - the skipped tick is never marked, so nothing runs it after the import",
     "file": "tv/control_app.py",
     "find": "            _SELF_PROVE[\"afterImport\"] = True   # REG-3197",
     "replace": "            _SELF_PROVE[\"afterImportX\"] = True   # REG-3197",
     "matches": 1},
    {"why": "REG-3197 (the reviewer on r3) - a finished import is still said to be 'being imported'",
     "file": "tv/control_app.py",
     "find": "    if _sp.get(\"afterImport\") is True and _rel.get(\"running\") is not True:\n        _sp[\"say\"] = (",
     "replace": "    if False:\n        _sp[\"say\"] = (",
     "matches": 1},
    {"why": "REG-3197 (the reviewer on r3) - the boot window drops its census's BLIND count",
     "file": "tv/control_app.py",
     "find": "        _blind_n = _BOOT_CENSUS.get(\"blind\")",
     "replace": "        _blind_n = None",
     "matches": 1},
    {"why": "REG-3197 (the reviewer on r3) - the river doors are asked while he plays",
     "file": "tv/control_app.py",
     "find": "        return not (_sp_playing_here() if playing is None else playing)\n",
     "replace": "        return True\n",
     "matches": 1},
    {"why": "REG-3197 - the lane never keeps which locks are shut",
     "file": "tv/control_app.py",
     "find": "        _RIVER_LOCKS_SEEN.update(ts=now, shut=[l for l, _w in shut], why=(shut[0][1] if shut else None))\n",
     "replace": "        _RIVER_LOCKS_SEEN.update(ts=now, shut=[], why=None)\n",
     "matches": 1},
    {"why": "REG-3197 - nothing asks the river doors, so the lock line never fills",
     "file": "tv/control_app.py",
     "find": "            if _river_locks_due():\n                _river_locks_note()\n",
     "replace": "            if _river_locks_due():\n                pass\n",
     "matches": 1},
    {"why": "REG-3197 - the worker drops the import on arrival",
     "file": "functions/api/console.js",
     "find": "          if (hi && typeof hi === 'object' && !Array.isArray(hi)) {\n",
     "replace": "          if (false) {\n",
     "matches": 1},
    {"why": "REG-3197 - an import starting is not news, so the row keeps its old words for a refresh",
     "file": "functions/api/console.js",
     "find": "                           (h.importing && typeof h.importing === 'object') ? (h.importing.landed === true ? 'landed' : 'importing') : null,\n",
     "replace": "                           null,\n",
     "matches": 1},
    {"why": "REG-3197 (the reviewer on r3) - the worker drops 'landed', so a finished import is stored as a running one",
     "file": "functions/api/console.js",
     "find": "            if (hi.landed === true) out.river.heart.importing.landed = true;\n",
     "replace": "\n",
     "matches": 1},
    {"why": "REG-3197 - the row says nothing about the import (his 21:01 Fleet)",
     "file": "tv/control_ui.html",
     "find": "    if (_imp) {\n      var _whose",
     "replace": "    if (false) {\n      var _whose",
     "matches": 1},
    {"why": "REG-3197 - the lock chip is the red alarm again while the import or the prover explains it",
     "file": "tv/control_ui.html",
     "find": "      var _lockCalm = !_blindHeld && _blindKnown && (!!_imp || (_owedHere !== null && !_memWait));\n",
     "replace": "      var _lockCalm = false;\n",
     "matches": 1},
    {"why": "REG-3197 (the reviewer on r3) - a BLIND gate is drawn amber 'until this PC proves' (his ALT rows, blind 1 / 3)",
     "file": "tv/control_ui.html",
     "find": "      var _blindHeld = (_blindN0 !== null && _blindN0 > 0) || !!(hs && typeof hs.lockWhy === 'string' && /are BLIND/.test(hs.lockWhy));\n",
     "replace": "      var _blindHeld = false;\n",
     "matches": 1},
    {"why": "REG-3197 (the reviewer on r3) - the calm words are said over a blind count nobody sent",
     "file": "tv/control_ui.html",
     "find": "      var _blindKnown = _blindN0 !== null || !!(hs && typeof hs.lockWhy === 'string' && hs.lockWhy);\n",
     "replace": "      var _blindKnown = true;\n",
     "matches": 1},
    {"why": "REG-3197 (the reviewer on r3) - a landed import is drawn as 'importing'",
     "file": "tv/control_ui.html",
     "find": "      var _impWords = _landed ? _whose + ' imported \\u00b7 the proof check runs next'\n",
     "replace": "      var _impWords = false ? _whose + ' imported \\u00b7 the proof check runs next'\n",
     "matches": 1},
    {"why": "REG-3197 (the reviewer on r3) - a lane that owes 0 is drawn as a red debt again",
     "file": "tv/control_ui.html",
     "find": "        return (mm && +mm[2] > 0) ? mm[1]",
     "replace": "        return mm ? mm[1]",
     "matches": 1},
    {"why": "REG-3197 - the lock line does not name which locks are shut",
     "file": "tv/control_ui.html",
     "find": "      if (_shutNames.length) {\n",
     "replace": "      if (false) {\n",
     "matches": 1},
    {"why": "REG-3197 - proving here is not said",
     "file": "tv/control_ui.html",
     "find": "    if (_owedHere !== null && _owedHere > 0) {\n      bits.push(",
     "replace": "    if (false) {\n      bits.push(",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
