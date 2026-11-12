# -*- coding: utf-8 -*-
"""v3899 (#213) - THE SHELF HEADER COUNTS EVERY PC, EACH WITH ITS COPY'S AGE.

GrokBot #230 6798971834 (11-11, his answer (a)): his Mac's OWN Shelf ("THE SHELF — your reels") header - best run, most
reads, streak, the 14-day chart - stopped at Nov 3 while the work ALT played on Nov 11. The header read only this PC's own
runs (TH.sessions). Every other PC's published sessions are already on his Mac as the shadow lane's cached copy; the
console now summarises those copies (/api/roster-cache?shelf=fleet, light, never the site on the request) and the header
counts them, naming a fleet run's PC instead of a session number, and saying how old each PC's copy is.

DRIVEN: the shipped _shelf_fleet over a fixture cache dir; the shipped _shFleetRuns / _shHighlights cut from
tv/control_ui.html and run in node. RED_PROOF below.
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
from cb_node_harness import NODE  # noqa: E402

NOW = 1794412000000
DAY = 86400000


def _fixture(d):
    import shadow_sessions as SS
    import console_snapshot as CS
    owners = [o for o in CS.OWNERS if o not in ("Konyo · Mac",)]
    alt, dean = owners[0], owners[2] if len(owners) > 2 else owners[-1]
    for owner, rows, at in ((alt, [{"sessionId": "s_a1", "t0": NOW - 2 * 3600000, "t1": NOW - 3600000, "reads": 40,
                                    "chroniclesFound": 3}], NOW - 5 * 60000),
                            (dean, [{"sessionId": "s_d1", "t0": NOW - 3 * DAY, "t1": NOW - 3 * DAY + 600000, "reads": 7,
                                     "chroniclesFound": None}], NOW - 20 * 3600000)):
        SS.write_cache(d, {"owner": owner, "t": at, "hash": "x", "digest": {"sessions": rows}})
    return alt, dean


class TheShelfHeaderCountsEveryPc(unittest.TestCase):

    def test_the_server_reads_every_other_pcs_copy_with_its_age(self):
        """* THE POINT - another PC's sessions reach this PC's header, light, each copy aged"""
        import control_app as CA
        d = tempfile.mkdtemp(prefix="shelf_fleet_")
        try:
            alt, dean = _fixture(d)
            with mock.patch.object(CA, "_frames_cache_dir", lambda: d), \
                    mock.patch.object(CA, "_profile_owner", lambda: "Konyo · Mac"):
                CA._SHELF_FLEET_MEMO.clear()
                out = CA._shelf_fleet(refresh=False, now_ms=NOW)
            got = sorted((x["owner"], x["sessionId"], x["reads"], x["chron"]) for x in out["sessions"])
            self.assertEqual(got, sorted([(alt, "s_a1", 40, 3), (dean, "s_d1", 7, None)]), out)
            self.assertEqual(out["owners"][alt]["ageMs"], 5 * 60000, "a PC's copy does not say how old it is")
            self.assertNotIn("Konyo · Mac", out["owners"], "this PC counted itself twice")
            nocopy = [o for o, r in out["owners"].items() if r.get("n") is None]
            self.assertTrue(nocopy, "PREMISE: every owner has a copy in the fixture")
            for o in nocopy:
                self.assertIn("no copy", out["owners"][o]["why"], "a PC with no copy reads as zero runs, not UNKNOWN")
            self.assertTrue(all("frames" not in x for x in out["sessions"]), "the summary carries the digest's pictures")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_the_header_names_a_fleet_run_and_counts_its_day(self):
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
                + "\n".join(fn(n) for n in ("_cmpList", "_shFleetRuns", "_shHighlights")) + r"""
var now = Date.now();
TH.sessions = [{ n: 1, sessionId: 's_m1', t0: now - 10 * 864e5, t1: now - 10 * 864e5 + 3600e3, reads: 5, finds: [] }];
window = { _shFleet: { ok: true, sessions: [{ owner: 'Konyo · ALT', sessionId: 's_a1', t0: now - 3600e3, t1: now - 600e3, reads: 40, chron: 3 }] } };
var with_ = _shHighlights();
window._shFleet = null;
var without = _shHighlights();
console.log(JSON.stringify({ withFleet: with_, without: without }));
""")
        d = tempfile.mkdtemp(prefix="shelf_fleet_ui_")
        try:
            h = os.path.join(d, "h.js")
            with io.open(h, "w", encoding="utf-8") as fh:
                fh.write(prog)
            r = subprocess.run([NODE, h], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace")[-700:])
        out = json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])
        # REG-3768 - on the card's VALUE line (">...</div>"): the tooltip carries the name too, and must not satisfy this
        self.assertIn(">Konyo · ALT</div>", out["withFleet"], "the best run on another PC is not named in the header")
        self.assertIn("2 runs logged", out["withFleet"], "the header does not count the other PC's run")
        self.assertIn("1 run logged", out["without"], "BASELINE - with no fleet answer the header is this PC's own runs")
        self.assertIn("_shFleetLoad(); } catch (eFl) {}", ui, "the shelf no longer asks every PC's sessions")
        self.assertIn("var runs = (TH.sessions || []).filter(function(s){ return !s.stub && s.t0; }).concat(_shFleetRuns());", ui,
                      "the 14-day chart no longer counts every PC")


RED_PROOF = [
    {"why": "v3899 (#213) - the header counts only this PC's own runs again",
     "file": "tv/control_ui.html",
     "find": "    var runs = _cmpList().concat(_shFleetRuns()); if (!runs.length) return '';\n",
     "replace": "    var runs = _cmpList(); if (!runs.length) return '';\n",
     "matches": 1, "needs": "node"},
    {"why": "v3899 (#213) - a fleet run's card says 'Session 0' instead of its PC",
     "file": "tv/control_ui.html",
     "find": "    function _shRunName(m){ return m.n ? 'Session ' + m.n : esc(String(m.owner || 'another PC')); }\n",
     "replace": "    function _shRunName(m){ return 'Session ' + m.n; }\n",
     "matches": 1, "needs": "node"},
    {"why": "v3899 (#213) - the server stops reading the other PCs' copies",
     "file": "tv/control_app.py",
     "find": "        out[\"sessions\"].extend(summ[\"rows\"])\n",
     "replace": "",
     "matches": 1},
    {"why": "v3899 (#213) - a PC with no copy reads as zero runs",
     "file": "tv/control_app.py",
     "find": "            out[\"owners\"][owner] = {\"cachedAt\": None, \"ageMs\": None, \"n\": None,\n                                    \"why\": \"this PC holds no copy of their published sessions yet\"}\n",
     "replace": "            out[\"owners\"][owner] = {\"cachedAt\": None, \"ageMs\": None, \"n\": 0, \"why\": \"\"}\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
