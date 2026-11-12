# -*- coding: utf-8 -*-
"""v3901 (REG-3763, #213) - THE SHELF HEADER SAYS EACH PC'S REAL RUN COUNT, NOT THE WINDOW IT PUBLISHES.

GrokBot (#230, 11-12, his live Mac console): "counts every PC · Konyo · ALT 16 (as of 25 min ago) · Dean 16 · OLD PC ALT
16" - every other PC counted at exactly 16, the MAX_SESSIONS newest each publishes, while the work ALT's own console lists
134 runs; and "131 runs logged" was this Mac's 83 plus 3 x 16. The header passed the window off as the PC's count. Now each
PC's digest publishes `runs` (every game run it holds), the fleet shelf hands it on as `total`, and the header says
"Konyo · ALT 134 runs (16 shown, as of 25 min ago)"; a copy from before v3901 says its 16 are the newest shown and its total
is UNKNOWN; "runs logged" adds each PC's total (a floor, "at least", when one is unknown).

DRIVEN: the real shadow_sessions.digest over 20 sessions, control_app._shelf_fleet over fixture copies, _shFleetSay and
_shHighlights cut from tv/control_ui.html and run in node. RED_PROOF below.
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
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
from cb_node_harness import NODE  # noqa: E402

NOW = 1794412000000


class TheShelfSaysEachPcsRealRunCount(unittest.TestCase):

    def test_the_digest_publishes_every_run_beyond_its_window(self):
        import shadow_sessions as SS
        rows = []
        for i in range(20):
            t = NOW - (20 - i) * 3600000
            rows += [{"sessionId": "s_%d" % i, "ts": t, "captureTs": t, "frameId": "f_%d" % i, "scene": "town"},
                     {"sessionId": "s_%d" % i, "ts": t + 1000, "captureTs": t + 1000, "scene": "session_end"}]
        d = SS.digest(rows, tempfile.gettempdir(), lambda r: False, NOW, make=lambda *a, **k: None)
        self.assertEqual(len(d["sessions"]), SS.MAX_SESSIONS, "PREMISE: the digest no longer windows its sessions")
        self.assertEqual(d.get("runs"), 20, "the digest does not say how many runs the PC holds")

    def test_the_server_hands_on_the_total_and_an_old_copy_reads_unknown(self):
        import control_app as CA
        import shadow_sessions as SS
        import console_snapshot as CS
        owners = [o for o in CS.OWNERS if o != "Konyo · Mac"]
        alt, dean = owners[0], owners[-1]
        d = tempfile.mkdtemp(prefix="shelf_total_")
        self.addCleanup(shutil.rmtree, d, True)
        row = {"sessionId": "s_a1", "t0": NOW - 7200000, "t1": NOW - 3600000, "reads": 40, "chroniclesFound": 1}
        SS.write_cache(d, {"owner": alt, "t": NOW - 60000, "hash": "x", "digest": {"sessions": [row], "runs": 134}})
        SS.write_cache(d, {"owner": dean, "t": NOW - 60000, "hash": "y", "digest": {"sessions": [dict(row, sessionId="s_d1")]}})
        with mock.patch.object(CA, "_frames_cache_dir", lambda: d), \
                mock.patch.object(CA, "_profile_owner", lambda: "Konyo · Mac"):
            CA._SHELF_FLEET_MEMO.clear()
            out = CA._shelf_fleet(refresh=False, now_ms=NOW)
        self.assertEqual((out["owners"][alt]["n"], out["owners"][alt]["total"]), (1, 134))
        self.assertIsNone(out["owners"][dean]["total"], "a copy that publishes no total was given the window's length")

    def test_the_header_says_the_real_count(self):
        """* THE POINT - GrokBot 11-12: every PC read 16 against the work ALT's own 134"""
        if NODE is None:
            raise AssertionError("node is not installed on this PC - this law runs the shipped header in node and does not skip")
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()

        def fn(name):
            head = "  function %s(" % name
            self.assertEqual(ui.count(head), 1, name)
            i = ui.index(head)
            return ui[i:ui.index("\n  }\n", i) + 4]
        prog = ("function esc(s){ return String(s); }\nfunction _kpiFmt(n){ return String(n); }\nvar TH = {};\n"
                + "\n".join(fn(n) for n in ("_cmpList", "_shFleetRuns", "_shFleetSay", "_shHighlights")) + r"""
var now = Date.now();
TH.sessions = [{ n: 1, sessionId: 's_m1', t0: now - 864e5, t1: now - 864e5 + 3600e3, reads: 5, finds: [] }];
var s16 = [];
for (var i = 0; i < 16; i++) s16.push({ owner: 'ALT', sessionId: 's_a' + i, t0: now - (i + 2) * 3600e3, t1: now - (i + 1) * 3600e3, reads: 4, chron: 0 });
window = { _shFleet: { ok: true, sessions: s16, owners: { 'ALT': { n: 16, total: 134, ageMs: 25 * 60000 }, 'OLD': { n: 16, total: null, ageMs: 60000 } } } };
var say = _shFleetSay(), hi = _shHighlights();
console.log(JSON.stringify({ say: say, hi: hi }));
""")
        d = tempfile.mkdtemp(prefix="shelf_total_ui_")
        try:
            h = os.path.join(d, "h.js")
            with io.open(h, "w", encoding="utf-8") as fh:
                fh.write(prog)
            r = subprocess.run([NODE, h], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace")[-700:])
        out = json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])
        self.assertIn("ALT 134 runs (16 shown, as of 25 min ago)", out["say"])
        self.assertIn("OLD 16 newest shown, total UNKNOWN", out["say"], "a copy with no total passed its window off as its count")
        # REG-3806 - the floor is written 151+ so it fits its one-line card at 1512; the hover says "at least" in words
        self.assertIn("151+ runs logged", out["hi"], "runs logged is not this PC's runs + each PC's own total")
        self.assertIn('title="at least 151 runs logged', out["hi"], "the floor's words left the hover")


RED_PROOF = [
    {"why": "REG-3763 - the digest stops publishing how many runs the PC holds",
     "file": "tv/shadow_sessions.py",
     "find": "    out[\"runs\"] = len(groups)\n",
     "replace": "    out[\"runs\"] = None\n",
     "matches": 1},
    {"why": "REG-3763 - the header passes the published window off as the PC's run count again",
     "file": "tv/control_ui.html",
     "find": "      if (typeof r.total === 'number' && r.total >= r.n)\n",
     "replace": "      if (false)\n",
     "matches": 1},
    {"why": "REG-3763 - runs logged counts the rows held, not each PC's own total",
     "file": "tv/control_ui.html",
     "find": "          if (typeof r.total === 'number' && typeof r.n === 'number' && r.total >= r.n) _logged += r.total;\n",
     "replace": "          if (false) _logged += r.total;\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
