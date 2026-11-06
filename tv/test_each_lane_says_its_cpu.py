# -*- coding: utf-8 -*-
"""v3867 (card #41, REG-2986 never built) - EACH LANE SAYS ITS CPU, MEASURED; WHAT CANNOT BE READ IS UNKNOWN.

MEASURED 2026-11-06 on his work ALT: /api/status 19-47 s and the heart timing out at 40 s beside the game, and no surface
could say which of the console's threads was busy. tv/lane_cpu.py reads each thread's CPU from the OS (Mach thread_info
on macOS - its thread_id is Python's native id, measured: a named busy thread read 1.00 s after 1 s of work; Windows
GetThreadTimes; Linux /proc) and diffs two samples into "the busiest lanes" on /api/status and the heart.

  1. window() is the arithmetic: busiest first, a thread born inside the window counts all its CPU, an id whose CPU went
     DOWN (reused by a new thread) is not credited, a zero-length window is no rows.
  2. state() says UNKNOWN with a reason when the OS cannot be read - never a zero - and needs two samples for a window.
  3. On this machine, a named busy thread tops the list and an idle one does not (a real reading, not a stub).
  4. On macOS the reader gives back every Mach port it takes (a console sampling all night must not leak ports).
  5. The console publishes it on /api/status and in the heart, and the heart draws UNKNOWN as UNKNOWN.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import lane_cpu as L  # noqa: E402

UI = os.path.join(HERE, "control_ui.html")
APP = os.path.join(HERE, "control_app.py")
NODE = shutil.which("node")


class TheArithmetic(unittest.TestCase):

    def test_busiest_first_with_names_and_shares_of_one_core(self):
        rows = L.window({1: 1.0, 2: 5.0}, {1: 4.0, 2: 5.5, 3: 0.2}, 10.0, {1: "tvd-eagle", 2: "tvd-river"})
        self.assertEqual([r["name"] for r in rows], ["tvd-eagle", "tvd-river", "thread 3"])
        self.assertEqual(rows[0], {"name": "tvd-eagle", "cpuS": 3.0, "pct": 30.0})
        self.assertEqual(rows[2]["cpuS"], 0.2, "a thread born inside the window lost its CPU")

    def test_an_id_reused_by_a_new_thread_is_not_credited_and_no_window_is_no_rows(self):
        self.assertEqual(L.window({7: 9.0}, {7: 0.5}, 10.0, {7: "new"}), [])
        self.assertEqual(L.window({1: 0.0}, {1: 1.0}, 0, {}), [])


class UnknownIsNeverZero(unittest.TestCase):

    def setUp(self):
        self._saved = list(L._SAMPLES)
        L._SAMPLES.clear()

    def tearDown(self):
        L._SAMPLES.clear()
        L._SAMPLES.extend(self._saved)

    def test_an_unreadable_os_is_unknown_with_its_reason(self):
        got = L.state(now=100.0, _sample=lambda plat: (None, "the OS would not list this process's threads"))
        self.assertFalse(got["ok"])
        self.assertIsNone(got["total"], "an unreadable reading carried a number")
        self.assertEqual(got["rows"], [])
        self.assertIn("would not list", got["why"])

    def test_one_sample_is_not_a_window_and_two_are(self):
        seq = [({1: 1.0}, None), ({1: 4.0}, None)]
        first = L.state(now=100.0, _sample=lambda plat: seq.pop(0))
        self.assertFalse(first["ok"])
        self.assertIn("one sample", first["why"])
        second = L.state(now=100.0 + L.SAMPLE_EVERY_S + 1, _sample=lambda plat: seq.pop(0))
        self.assertTrue(second["ok"], second)
        self.assertEqual(second["rows"][0]["cpuS"], 3.0)
        self.assertEqual(second["windowS"], round(L.SAMPLE_EVERY_S + 1, 1))

    def test_an_unknown_platform_is_said(self):
        got, why = L.sample(platform="plan9")
        self.assertIsNone(got)
        self.assertIn("plan9", why)


@unittest.skipUnless(sys.platform == "darwin" or sys.platform.startswith(("win", "linux")), "no per-thread reader here")
class ARealReadingOnThisMachine(unittest.TestCase):

    def test_a_named_busy_thread_tops_the_list(self):
        stop = []

        def burn():
            while not stop:
                pass

        def idle():
            while not stop:
                time.sleep(0.05)
        a = threading.Thread(target=burn, name="law-busy-lane", daemon=True)
        b = threading.Thread(target=idle, name="law-idle-lane", daemon=True)
        a.start(); b.start()
        try:
            s1, why1 = L.sample()
            self.assertIsNotNone(s1, why1)
            t0 = time.monotonic()
            time.sleep(1.0)
            s2, why2 = L.sample()
            dt = time.monotonic() - t0
        finally:
            stop.append(1)
            a.join(5); b.join(5)
        names = {a.native_id: a.name, b.native_id: b.name}
        rows = L.window(s1, s2, dt, names)
        self.assertTrue(rows, "no lane read any CPU over a busy second")
        self.assertEqual(rows[0]["name"], "law-busy-lane", "the busy lane was not the busiest: %r" % rows[:3])
        self.assertGreater(rows[0]["pct"], 30.0, rows[0])
        idle_row = [r for r in rows if r["name"] == "law-idle-lane"]
        self.assertTrue(not idle_row or idle_row[0]["pct"] < 10.0, idle_row)

    @unittest.skipUnless(sys.platform == "darwin", "Mach ports are a macOS question")
    def test_every_mach_port_is_given_back(self):
        def ports():
            out = subprocess.run(["top", "-l", "1", "-pid", str(os.getpid()), "-stats", "ports"],
                                 capture_output=True, text=True, timeout=30).stdout
            return int(out.strip().splitlines()[-1].strip())
        L.sample()
        before = ports()
        for _ in range(500):
            L.sample()
        self.assertLessEqual(ports(), before + 2, "the reader leaks Mach ports: %d before 500 samples" % before)


class TheConsoleSaysIt(unittest.TestCase):

    def test_status_and_heart_carry_the_reading(self):
        with io.open(APP, encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count('"laneCpu": _t("laneCpu", _lane_cpu_state),'), 1, "/api/status does not carry it")
        self.assertEqual(src.count('"laneCpu": _lane_cpu_state(),'), 1, "the heart does not carry it")

    @unittest.skipUnless(NODE, "node runs the page's own drawer")
    def test_the_heart_draws_rows_and_unknown_as_unknown(self):
        with io.open(UI, encoding="utf-8") as fh:
            ui = fh.read()
        a = ui.index("window._hrtLaneCpu = function(lc){")
        b = ui.index("var _hrtLaneCpu = window._hrtLaneCpu;", a)
        prog = "var window = {};\n" + ui[a:b] + r"""
var out = {
  rows: window._hrtLaneCpu({ok: true, windowS: 60, total: 41.5, rows: [{name: 'tvd-eagle', cpuS: 21.0, pct: 35.0},
                                                                      {name: 'tvd-river', cpuS: 3.9, pct: 6.5}]}),
  unk: window._hrtLaneCpu({ok: false, why: 'the OS would not list this process’s threads', rows: [], total: null}),
  old: window._hrtLaneCpu(undefined)
};
process.stdout.write(JSON.stringify(out));
"""
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        o = json.loads(r.stdout)
        self.assertIn("tvd-eagle", o["rows"])
        self.assertIn("35%", o["rows"])
        self.assertIn("41.5% of one core", o["rows"])
        for k in ("unk", "old"):
            self.assertIn("UNKNOWN", o[k])
            self.assertNotIn("0%", o[k], "an unknown reading was drawn as a zero")
        self.assertIn("would not list", o["unk"])


RED_PROOF = [
    {"why": "v3867 - a thread born inside the window loses its CPU (only threads seen twice count)",
     "file": "tv/lane_cpu.py",
     "find": "        used = cpu - (old or {}).get(tid, 0.0)\n",
     "replace": "        used = cpu - (old or {}).get(tid, cpu)\n",
     "matches": 1},
    {"why": "v3867 - an unreadable OS reads as a zero total instead of UNKNOWN",
     "file": "tv/lane_cpu.py",
     "find": "                return {\"ok\": False, \"windowS\": None, \"rows\": [], \"total\": None, \"why\": why}\n",
     "replace": "                return {\"ok\": False, \"windowS\": None, \"rows\": [], \"total\": 0.0, \"why\": why}\n",
     "matches": 1},
    {"why": "v3867 - the Mach ports are never given back (a port per thread per sample, all night)",
     "file": "tv/lane_cpu.py",
     "find": "                libc.mach_port_deallocate(task, port)\n",
     "replace": "                pass\n",
     "matches": 1},
    {"why": "v3867 - the heart draws an unknown reading as a zero",
     "file": "tv/control_ui.html",
     "find": "  if (!lc.ok) return '<div class=\"hrt-sec\"><div class=\"hrt-h\">The busiest lanes · UNKNOWN</div><div class=\"hrt-note\">'\n",
     "replace": "  if (!lc.ok) return '<div class=\"hrt-sec\"><div class=\"hrt-h\">The busiest lanes · 0%</div><div class=\"hrt-note\">'\n",
     "matches": 1},
    {"why": "v3867 - /api/status stops carrying the reading",
     "file": "tv/control_app.py",
     "find": "        \"laneCpu\": _t(\"laneCpu\", _lane_cpu_state),",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
