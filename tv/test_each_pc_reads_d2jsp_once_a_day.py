# -*- coding: utf-8 -*-
"""#56 - EVERY PC ASKS D2JSP FOR A REAL PRICE AT LEAST ONCE A DAY, AND ITS FLEET ROW SAYS WHETHER IT READ.

His 11-05 worry: "d2jsp works on Dean's PC? the MacBook never did". A lamp says whether a sign-in exists; only a real
search says d2jsp answers. v3878's refresh lane (d2jsp_refresh.run_once) already asks the forum for one stale item a pass on
every PC; now every such read is recorded on that PC (.d2jsp_check.json: when, which item, what came back), a day with
nothing due asks CHECK_ITEM once, and the record rides the PC's beacon ("d2jsp") to every Fleet row: "d2jsp reads · 3 h
ago", "signed out", "did not read (unread)", or UNKNOWN when it never asked (or the build is older). Every stand-aside a
refresh honours holds (checks running, he plays, a sweep reads, a push grades); nothing is posted.
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


class _World(object):
    """a price database on disk, a quote that records what it was asked, and the check's own file"""

    def __init__(self, reason="read"):
        self.d = tempfile.mkdtemp(prefix="tvd_d2jsp_check_")
        self.db = os.path.join(self.d, "d2jsp_price_db.json")
        self.check = os.path.join(self.d, DR.CHECK_NAME)
        DR.P.save(self.db, DR.P.empty())          # the database's own empty shape (its schema stamped)
        self.asked, self.reason = [], reason

    def quote(self, name):
        self.asked.append(name)
        return {"reason": self.reason, "item": name}

    def run(self, now=NOW, plays=False, checks=False, stale=()):
        with mock.patch.object(DR, "stale_items", lambda db, now: [(n.lower(), n, None) for n in stale]):
            return DR.run_once(self.db, self.quote, fold=lambda r: {}, stand_aside=lambda: plays,
                               now=now, checks=lambda: checks, check_path=self.check)

    def close(self):
        shutil.rmtree(self.d, True)


class EachPcReadsD2jspOnceADay(unittest.TestCase):

    def setUp(self):
        self.w = _World()
        self.addCleanup(self.w.close)

    def test_a_fresh_database_still_asks_once_a_day(self):
        """* THE POINT: a PC with nothing due still proves d2jsp answers - once a day, never more"""
        r = self.w.run()
        self.assertEqual(self.w.asked, [DR.CHECK_ITEM], r)
        self.assertTrue(r.get("check"))
        rec = DR.check_load(self.w.check)
        self.assertEqual((rec["ok"], rec["item"], rec["reason"], rec["at"]), (True, DR.CHECK_ITEM, "read", int(NOW * 1000)))
        self.w.run(now=NOW + 2 * 3600)
        self.assertEqual(self.w.asked, [DR.CHECK_ITEM], "a fresh check was asked again within the day")
        self.w.run(now=NOW + DAY + 60)
        self.assertEqual(self.w.asked, [DR.CHECK_ITEM, DR.CHECK_ITEM], "a day passed and nothing was asked")

    def test_a_due_item_is_the_days_read(self):
        self.w.run(stale=["Griffon's Eye"])
        self.assertEqual(self.w.asked, ["Griffon's Eye"], "the check asked its own item over a due one")
        self.assertEqual(DR.check_load(self.w.check)["item"], "Griffon's Eye")
        self.w.run(now=NOW + 3600)
        self.assertEqual(len(self.w.asked), 1, "the read of a due item did not count as the day's check")

    def test_a_signed_out_pc_says_so(self):
        self.w.reason = "need-login"
        self.w.run()
        wire = DR.check_for_wire(DR.check_load(self.w.check), NOW + 600)
        self.assertIs(wire["ok"], False)
        self.assertEqual((wire["reason"], wire["ageS"]), ("need-login", 600))
        self.assertIn("sign in through its D2JSP lamp", wire["why"])

    def test_every_stand_aside_holds(self):
        for name, kw in (("he plays", {"plays": True}), ("checks run", {"checks": True}), ("checks UNKNOWN", {"checks": None})):
            with self.subTest(case=name):
                w = _World()
                try:
                    w.run(**kw)
                    self.assertEqual(w.asked, [], "%s and the check asked d2jsp anyway" % name)
                    self.assertIsNone(DR.check_load(w.check), "%s wrote a check that never happened" % name)
                finally:
                    w.close()

    def test_never_asked_is_unknown_never_a_pass(self):
        wire = DR.check_for_wire(None, NOW)
        self.assertIsNone(wire["ok"])
        self.assertIn("has not asked d2jsp", wire["why"])
        bad = os.path.join(self.w.d, "bad.json")
        with io.open(bad, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertIsNone(DR.check_for_wire(DR.check_load(bad), NOW)["ok"])

    def test_the_beacon_carries_it(self):
        import control_app as CA
        self.w.run()
        with mock.patch.object(CA, "_d2jsp_check_path", lambda: self.w.check):
            wire = CA._d2jsp_check_for_wire()
        self.assertIs(wire["ok"], True)
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('            "d2jsp": _d2jsp_check_for_wire(),', src, "the beacon does not carry the check")
        self.assertIn("check_path=_d2jsp_check_path())", src, "the refresh lane does not record its reads")


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
    {"why": "#56 - a PC whose database is fresh never proves d2jsp answers",
     "file": "d2jsp_refresh.py",
     "find": "        elif check_path and check_due(check_load(check_path), now):",
     "replace": "        elif False:",
     "matches": 1},
    {"why": "#56 - the reads are never recorded (the row cannot say whether d2jsp answered)",
     "file": "d2jsp_refresh.py",
     "find": "        if check_path:\n            check_note(check_path, name, out[\"reason\"], now)",
     "replace": "        if False:\n            check_note(check_path, name, out[\"reason\"], now)",
     "matches": 1},
    {"why": "#56 - a signed-out read is recorded as a pass",
     "file": "d2jsp_refresh.py",
     "find": "           \"ok\": reason == \"read\"}",
     "replace": "           \"ok\": True}",
     "matches": 1},
    {"why": "#56 - the check asks d2jsp every pass, not once a day",
     "file": "d2jsp_refresh.py",
     "find": "    return now - at / 1000.0 >= CHECK_EVERY_S",
     "replace": "    return True",
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
