# -*- coding: utf-8 -*-
"""#56 - EVERY PC'S FLEET ROW SAYS WHETHER ITS LAST REAL d2jsp SEARCH READ. (The once-a-day read is RETIRED - Job E.)

His 11-05 worry: "d2jsp works on Dean's PC? the MacBook never did". A lamp says whether a sign-in exists; only a real
search says d2jsp answers. v3880 recorded every read of the refresh lane (d2jsp_refresh.run_once) on that PC
(.d2jsp_check.json: when, which item, what came back), and a day with nothing due asked CHECK_ITEM once.
Job E (Claude's #230 6849292433) - that lane is RETIRED by his 11-13 ruling ("yea you can"; "it doesnt need to redo things
for now.. it can do it in the future"), and the once-a-day read rode it, so it is retired with it: NOTHING asks the forum
on its own. The record stays and is now written by the price check's own search (the /api/d2jsp_quote door, after a real
forum read - never for a stored, paused or refused answer), and it still rides the PC's beacon ("d2jsp") to every Fleet
row: "d2jsp reads · 3 h ago", "signed out", "did not read (unread)", or UNKNOWN when it never searched (or the build is
older). Nothing is posted. The file keeps its old name so its registered gate stays found.
RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()   # v3880 - its mkdtemp scratch is collected (test_a_test_run_leaves_no_scratch_dirs)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import d2jsp_refresh as DR  # noqa: E402

NODE = shutil.which("node")
API_CONSOLE = os.path.join(ROOT, "functions", "api", "console.js")
NOW = 1794050000.0
DAY = 86400.0


NOTE = os.path.join("tv", "control_app.py")


def _door():
    with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
        src = fh.read()
    a = src.index('        if path == "/api/d2jsp_quote":')
    return src, src[a:src.index('        if path == "/api/d2jsp_price_db":', a)]


class EachPcSaysItsLastRealRead(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="tvd_d2jsp_check_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.check = os.path.join(self.d, DR.CHECK_NAME)

    def test_nothing_asks_d2jsp_on_its_own_any_more(self):
        """* Job E - was test_a_fresh_database_still_asks_once_a_day: the once-a-day read is RETIRED with its lane"""
        for gone in ("run_once", "CHECK_ITEM", "CHECK_EVERY_S", "check_due"):
            self.assertFalse(hasattr(DR, gone), "d2jsp_refresh.%s is back - something asks d2jsp on its own again" % gone)
        self.assertIn("once-a-day check read", DR.__doc__ or "", "the module no longer says the daily read is retired")

    def test_a_price_checks_search_is_the_record(self):
        """was test_a_due_item_is_the_days_read: the item the price check searched is the row's item"""
        rec = DR.check_note(self.check, "Griffon's Eye", "read", NOW)
        self.assertEqual((rec["ok"], rec["item"], rec["at"]), (True, "Griffon's Eye", int(NOW * 1000)))
        self.assertEqual(DR.check_load(self.check)["item"], "Griffon's Eye")

    def test_a_signed_out_pc_says_so(self):
        DR.check_note(self.check, "Shako", "need-login", NOW)
        wire = DR.check_for_wire(DR.check_load(self.check), NOW + 600)
        self.assertIs(wire["ok"], False)
        self.assertEqual((wire["reason"], wire["ageS"]), ("need-login", 600))
        self.assertIn("sign in through its D2JSP lamp", wire["why"])

    def test_only_a_real_search_from_his_own_page_is_recorded(self):
        """was test_every_stand_aside_holds (the lane's stand-asides went with it): the door writes the record only after
        a real forum read for this console's own page - a paused or stored answer returns before it, so neither is a
        read that never happened"""
        _src, door = _door()
        note = door.index("_dr.check_note(_d2jsp_check_path(), _item, _out.get(\"reason\"), time.time())")
        self.assertLess(door.index("_d2jsp.d2jsp_quote("), note, "the record is written before any search was made")
        self.assertLess(door.index('"reason": "paused"'), note)
        self.assertLess(door.index('if _plan["do"] == "stored":'), note)
        self.assertIn("            if _own_page:\n", door[:note], "a refused foreign request would be recorded as a read")

    def test_never_asked_is_unknown_never_a_pass(self):
        wire = DR.check_for_wire(None, NOW)
        self.assertIsNone(wire["ok"])
        self.assertIn("has not asked d2jsp", wire["why"])
        bad = os.path.join(self.d, "bad.json")
        with io.open(bad, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertIsNone(DR.check_for_wire(DR.check_load(bad), NOW)["ok"])

    def test_the_beacon_carries_it(self):
        import control_app as CA
        DR.check_note(self.check, "Shako", "read", NOW)
        with mock.patch.object(CA, "_d2jsp_check_path", lambda: self.check):
            wire = CA._d2jsp_check_for_wire()
        self.assertIs(wire["ok"], True)
        src, _door_src = _door()
        self.assertIn('            "d2jsp": _d2jsp_check_for_wire(),', src, "the beacon does not carry the check")


def _post_beacon(body):
    js = r"""
import { pathToFileURL } from 'node:url';
const store = new Map(); const puts = [];
const kv = { async list() { return { keys: [], list_complete: true }; }, async get(n) { return store.has(n) ? store.get(n) : null; },
             async put(n, v) { puts.push(n); store.set(n, v); }, async delete(n) { store.delete(n); } };
const mod = await import(pathToFileURL(%s).href);
const req = new Request('https://bull-4-u.com/api/console', { method: 'POST', body: JSON.stringify(%s),
                        headers: { 'content-type': 'application/json' } });
const res = await mod.onRequestPost({ request: req, env: { TZ_HISTORY: kv, VISITS_KEY: 'k' }, params: {}, waitUntil() {} });
await res.text();
const rec = store.get('console:' + %s);
process.stdout.write(JSON.stringify(rec ? JSON.parse(rec) : null));
""" % (json.dumps(API_CONSOLE), json.dumps(body), json.dumps(body["machine"]))
    with tempfile.TemporaryDirectory(prefix="tvd_d2jsp_beacon_") as d:
        p = os.path.join(d, "h.mjs")
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(js)
        r = subprocess.run([NODE, p], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    if r.returncode != 0:
        raise AssertionError("the console harness failed: %s" % r.stderr[-1500:])
    return json.loads(r.stdout)


@unittest.skipUnless(NODE, "node is absent - the worker and the row are UNMEASURED here, never a pass")
class TheRowSaysIt(unittest.TestCase):

    def _beacon(self, d2jsp):
        b = {"machine": "check-pc", "event": "hb", "platform": "win", "ver": "v3880", "mode": "idle"}
        if d2jsp is not None:
            b["d2jsp"] = d2jsp
        return _post_beacon(b)

    def test_the_worker_keeps_the_check_shaped(self):
        rec = self._beacon({"ok": False, "at": int(NOW * 1000), "item": "Shako", "reason": "need-login",
                            "why": "signed out " * 40})
        self.assertIsNotNone(rec, "the beacon was not stored")
        d = rec.get("d2jsp")
        self.assertEqual((d["ok"], d["at"], d["item"], d["reason"]), (False, int(NOW * 1000), "Shako", "need-login"))
        self.assertLessEqual(len(d["why"]), 160)
        odd = self._beacon({"ok": "yes", "at": 9e15, "reason": "<script>", "item": 5})["d2jsp"]
        self.assertEqual((odd["ok"], odd["at"], odd["reason"], odd["item"]), (None, None, None, None),
                         "a malformed check crossed as a pass, a future time or a raw reason")
        self.assertIsNone(self._beacon(None).get("d2jsp"), "an older console's silence became a check")

    def _part(self, m):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        i = ui.index("  var _fleetD2jspPart = function (m, nowMs) {")
        j = ui.index("\n  };", i)
        js = ("var window = {};\nvar _fleetPart = function (k, f, o) { var p = o || {}; p.k = k; p.f = f; p.t = f.join(' · '); return p; };\n"
              "var _fleetAgeTxt = function (s) { return Math.round(s / 3600) + ' h ago'; };\n" + ui[i:j + 4]
              + "\nconsole.log(JSON.stringify(_fleetD2jspPart(%s, %d)));" % (json.dumps(m), int(NOW * 1000)))
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[:400])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_the_fleet_row_says_reads_signed_out_or_unknown(self):
        at = int((NOW - 3 * 3600) * 1000)
        ok = self._part({"d2jsp": {"ok": True, "at": at, "why": "d2jsp answered"}})
        self.assertEqual(ok["t"], "reads · 3 h ago")
        self.assertFalse(ok.get("warn"))
        out = self._part({"d2jsp": {"ok": False, "at": at, "reason": "need-login", "why": "x"}})
        self.assertEqual(out["t"], "signed out · 3 h ago")
        self.assertTrue(out.get("warn"))
        bad = self._part({"d2jsp": {"ok": False, "at": at, "reason": "unread"}})
        self.assertEqual(bad["t"], "did not read (unread) · 3 h ago")
        self.assertTrue(self._part({"d2jsp": {"ok": None}}).get("unk"))
        old = self._part({})
        self.assertTrue(old.get("unk"))
        self.assertIn("an older build", old["t"])

    def test_the_box_draws_it(self):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        self.assertIn("    out.push(_fleetD2jspPart(m, nowMs));\n    return out;", ui, "the row's box never draws the d2jsp part")


RED_PROOF = [
    {"why": "Job E - the retired once-a-day read comes back (a timer asks d2jsp Shako again)",
     "file": "d2jsp_refresh.py",
     "find": "CHECK_NAME = \".d2jsp_check.json\"\n",
     "replace": "CHECK_NAME = \".d2jsp_check.json\"\nCHECK_ITEM = \"Shako\"\n",
     "matches": 1},
    {"why": "#56 / Job E - the price check's reads are never recorded (the row cannot say whether d2jsp answered)",
     "file": "control_app.py",
     "find": "                    _dr.check_note(_d2jsp_check_path(), _item, _out.get(\"reason\"), time.time())\n",
     "replace": "                    pass\n",
     "matches": 1},
    {"why": "#56 / Job E - a foreign (refused) request is recorded as this PC's read",
     "file": "control_app.py",
     "find": "            if _own_page:\n                # #56 / Job E",
     "replace": "            if True:\n                # #56 / Job E",
     "matches": 1},
    {"why": "#56 - a signed-out read is recorded as a pass",
     "file": "d2jsp_refresh.py",
     "find": "           \"ok\": reason == \"read\"}",
     "replace": "           \"ok\": True}",
     "matches": 1},
    {"why": "#56 - the worker drops the check, so every row reads an older build",
     "file": "functions/api/console.js",
     "find": "    })(body.d2jsp),",
     "replace": "    })(null),",
     "matches": 1, "needs": "node"},
    {"why": "#56 - a never-asked PC reads as passing",
     "file": "control_ui.html",
     "find": "    return _fleetPart('d2jsp', ['UNKNOWN', 'never asked'], { unk: true,",
     "replace": "    return _fleetPart('d2jsp', ['reads', 'never asked'], { unk: false,",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
