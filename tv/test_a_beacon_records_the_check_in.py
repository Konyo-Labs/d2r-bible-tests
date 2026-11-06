#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3390 (#135) - A BEACON RECORDS THE CHECK-IN, NOT ONLY THE CHANGE.

Konyo, 2026-09-20, answering the one question I had left open: Dean was ON THE CONSOLE, not the
website. That retired my own retraction - there IS a beacon defect, and I had written it off.

functions/api/console.js wrote the durable last-seen key only on a material change:

    if (material) { await kv.put('lastseen:' + machine, ...) }
    else          { skipped.push('lastseen (nothing changed)') }

`material` covers ver / mode / event / diskVer / tally / masks / pull / eye.live. A console that
is OPEN and beaconing every ~4 minutes with none of those moving never refreshed it, so its
"last seen" was the last time something CHANGED. Dean idles without ticking items, so his row
froze hardest precisely because he is the least busy user - the whole 26 hours Konyo questioned.

REPRODUCED against the real handler before any fix was written:
    beacon 1 (first ever)   stored: ["console","lastseen"]
    beacon 2 (IDLE, same)   stored: []            <- checked in, left no trace
    beacon 3 (he ticked 1)  stored: ["console","lastseen"]

⚠ SHARPER THAN A FROZEN NUMBER. `console:` refreshes on a timer (`material || ageS >= REFRESH_S`);
only `lastseen:` had none. During a long idle session the machine reads ONLINE with a stale
last-seen, and the moment presence expires the offline list prints that stale stamp instead of
the session that just ended. That is exactly what he saw.

⚠⚠ THREE ARTEFACTS DISAGREED AND THE CODE WAS THE ODD ONE OUT:
  * the file header: "lastseen: - DURABLE last check-in, TTL 400d, written on EVERY beacon
    INCLUDING heartbeats" - which I read, believed, and repeated to him as proof his beacon was
    healthy. A comment describing a rule the adjacent code does not implement is worse than no
    comment: it convinced the reader the case was handled. [[measured-true-read-wrong]]
  * the budget sizing REFRESH_S: "4 x (3600/900) x 24 x 2 = 768 writes/day" - the x 2 is BOTH
    keys at the 15-minute cadence, so the fix costs nothing that was not already budgeted.
  * the code.

⚠ ANCHORING NOTE FOR ANY FUTURE SABOTAGE: after the fix, `if (material || ageS >= REFRESH_S) {`
appears TWICE - once for `console:` and once for `lastseen:`. An anchor on that line alone
matches 2 and must include the `kv.put` line beneath it. PRINT THE MATCH COUNT.
[[regression-guard]] 5a

WHAT THIS FILE PINS - behaviour, by running the REAL Cloudflare handler against a stub KV that
persists across beacons (run_handler builds a fresh store per call, so this file keeps its own):
  * an idle repeat beacon PAST REFRESH_S refreshes lastseen - the defect itself
  * an idle repeat beacon INSIDE REFRESH_S does NOT - the write budget still holds
  * a material change writes at ANY age - the BASELINE, without which a fix that wrote every
    time would pass the first case and cost him the KV ceiling
  * a first-ever beacon writes both keys - a cold console is not a repeat
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    import console_safe
    console_safe.enable()
except Exception:
    pass

from test_console_fleet import NODE                      # noqa: E402  (one source for node)

API = os.path.join(ROOT, "functions", "api", "console.js")

# ⚠ WHY THIS FILE CARRIES ITS OWN HARNESS AND THAT IS NOT DRIFT: run_handler() in
# test_console_fleet.py builds a FRESH store per call, and this law is about what the SECOND
# beacon does to the store the FIRST one left. A defect that only appears on the repeat cannot be
# reached by a harness that never repeats. [[copy-drift]] states the rule; this is the stated
# exception, with its reason.
_HARNESS = r"""
import { pathToFileURL } from 'node:url';
const CFG = __CFG__;
const store = new Map(Object.entries(CFG.seed || {}).map(([k, v]) => [k, JSON.stringify(v)]));
const kv = {
  async get(n, t) { const v = store.get(n); return v == null ? null : (t === 'json' ? JSON.parse(v) : v); },
  async put(n, v) { store.set(n, v); },
  async list() { return { keys: [], list_complete: true }; },
  async delete(n) { store.delete(n); },
};
const mod = await import(pathToFileURL(CFG.file).href);
const out = [];
const stamps = [];
for (let i = 0; i < CFG.beacons.length; i++) {
  // ⚠ AGE THE STORED RECORD, DO NOT HAND-BUILD IT. My first fixture seeded `console:` with a
  // dict I wrote myself and every case came back "material" — the handler normalises fields, so
  // my guess at the stored shape differed from the real one on a field I never thought about.
  // Letting beacon 1 WRITE the record and then only moving its clock makes `prev` exactly what
  // production holds. [[feedback-suspect-the-instrument]]
  if (i > 0) await new Promise((r) => setTimeout(r, 20));
  if (i > 0 && CFG.ageBetween) {
    const k = 'console:' + CFG.machine;
    const cur = store.get(k);
    if (cur) {
      const o = JSON.parse(cur);
      o.t = new Date(Date.now() - CFG.ageBetween * 1000).toISOString();
      store.set(k, JSON.stringify(o));
    }
  }
  if (i > 0 && CFG.patchBetween) {          // REG-3266 - a law's seam: what the stored row already counts
    const k = 'console:' + CFG.machine;
    const cur = store.get(k);
    if (cur) store.set(k, JSON.stringify(Object.assign(JSON.parse(cur), CFG.patchBetween)));
  }
  const body = CFG.beacons[i];
  const req = new Request('https://bull-4-u.com/api/console', {
    method: 'POST', body: JSON.stringify(body),
    headers: { 'content-type': 'application/json' } });
  const res = await mod.onRequestPost({ request: req, env: { TZ_HISTORY: kv }, waitUntil(){} });
  out.push(JSON.parse(await res.text()));
  // ⚠ SNAPSHOT THE STORE, NOT THE REPLY. `stored: [...]` is the handler's own RECEIPT; the
  // stamp lives in the KV record and only that can confirm the receipt.
  const _s = store.get('lastseen:' + CFG.machine);
  stamps.push(_s ? (JSON.parse(_s).t || null) : null);
}
const seen = store.get('lastseen:' + CFG.machine);
process.stdout.write(JSON.stringify({
  replies: out, lastseen: seen ? JSON.parse(seen) : null, stamps,
}));
"""


def _beacons(bodies, seed=None, machine="dean-pc", age_between=0, patch_between=None):
    cfg = {"file": API, "beacons": bodies, "seed": seed or {}, "machine": machine,
           "ageBetween": age_between, "patchBetween": patch_between}
    src = _HARNESS.replace("__CFG__", json.dumps(cfg))
    with tempfile.TemporaryDirectory(prefix="tvd_beacon_") as d:
        p = os.path.join(d, "h.mjs")
        io.open(p, "w", encoding="utf-8").write(src)
        r = subprocess.run([NODE, p], capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        raise AssertionError("beacon harness failed (rc=%s)\nSTDERR:\n%s"
                             % (r.returncode, r.stderr[-3000:]))
    return json.loads((r.stdout or "").strip().splitlines()[-1])


BASE = {"machine": "dean-pc", "nickname": "Dean", "install": "i-dean", "ver": "v3342",
        "mode": "idle", "event": "hb", "tally": {"ok": True, "sets": {"have": 0, "total": 135}}}


def _two_beacons(age_between, second=None):
    """Beacon, age the STORED record, beacon again. -> the second reply and the final lastseen.

    The first beacon is what seeds the store, so `prev` is exactly the shape production writes
    rather than a shape I guessed at.
    """
    v = _beacons([dict(BASE), dict(second or BASE)], age_between=age_between)
    return v["replies"][1], v["lastseen"], v["replies"][0], v.get("stamps") or []


class ABeaconRecordsTheCheckIn(unittest.TestCase):

    def setUp(self):
        if not NODE:
            self.skipTest("no node on PATH - this law RUNS the real Cloudflare handler")

    def test_an_idle_console_past_the_refresh_window_is_still_recorded(self):
        """THE DEFECT ITSELF. Dean sat in the console for hours changing nothing; every one of
        those beacons was discarded and his row froze at the last CHANGE."""
        reply, _ls, first, _st = _two_beacons(1800)
        self.assertIn("lastseen", (first or {}).get("stored") or [],
                      "the FIRST beacon did not seed the store, so the second proves nothing")
        stored = (reply or {}).get("stored") or []
        self.assertIn("lastseen", stored,
                      "an idle beacon 30 minutes after the last write STILL did not refresh "
                      "lastseen - the row stays frozen and he is told the machine is absent "
                      "(stored=%r)" % (stored,))

    def test_an_idle_console_inside_the_window_is_not_rewritten(self):
        """THE BUDGET HALF, and the BASELINE that stops the case above being satisfied by a fix
        that simply writes every time. The KV ceiling is 1,000 writes/day and the comment sizing
        REFRESH_S spends it deliberately."""
        reply, _ls, _first, _st = _two_beacons(60)
        stored = (reply or {}).get("stored") or []
        self.assertNotIn("lastseen", stored,
                         "an idle beacon 60s after the last write spent a KV write anyway - at "
                         "~4 minute heartbeats that is 4x the budgeted rate (stored=%r)"
                         % (stored,))

    def test_a_material_change_is_recorded_at_any_age(self):
        """BASELINE in the other direction: news must never wait for a timer."""
        moved = dict(BASE)
        moved["tally"] = {"ok": True, "sets": {"have": 1, "total": 135}}
        reply, _ls, _first, _st = _two_beacons(60, second=moved)
        stored = (reply or {}).get("stored") or []
        self.assertIn("lastseen", stored,
                      "he ticked a piece 60s after the last beacon and the roster did not "
                      "record it (stored=%r)" % (stored,))

    def test_a_pc_past_its_daily_material_writes_waits_for_the_refresh(self):
        """REG-3266 - a windowMode that kept differing stored both keys every 60 s: 17,280 writes a day for six PCs."""
        import datetime
        today = datetime.datetime.utcnow().date().isoformat()
        moved = dict(BASE, tally={"ok": True, "sets": {"have": 1, "total": 135}})
        v = _beacons([dict(BASE), moved], age_between=60, patch_between={"wDay": today, "wN": 600})
        stored = (v["replies"][1] or {}).get("stored") or []
        self.assertNotIn("lastseen", stored, "a PC past its daily material writes still wrote at once (stored=%r)" % stored)
        v = _beacons([dict(BASE), moved], age_between=1800, patch_between={"wDay": today, "wN": 600})
        self.assertIn("lastseen", (v["replies"][1] or {}).get("stored") or [], "the refresh cadence stopped too")
        v = _beacons([dict(BASE), moved], age_between=60, patch_between={"wDay": "2000-01-01", "wN": 600})
        self.assertIn("lastseen", (v["replies"][1] or {}).get("stored") or [], "yesterday's count held today's news back")

    def test_a_first_ever_beacon_is_recorded(self):
        """A cold console is not a repeat; `ageS` falls back to 1e9 and `material` is true."""
        v = _beacons([dict(BASE)])
        stored = (v["replies"][0] or {}).get("stored") or []
        self.assertIn("lastseen", stored)
        self.assertIsNotNone(v["lastseen"], "the very first beacon left no durable record")

    def test_the_stamp_actually_advances(self):
        """⚠ `stored` is the handler's own RECEIPT of what it did. A receipt is a claim; the
        STORE is the other side's record, and only that can confirm it. [[unknown-stays-unknown]]"""
        _reply, _after_rec, _first, stamps = _two_beacons(1800)
        self.assertEqual(len(stamps), 2, "expected one stored-stamp snapshot per beacon")
        before, after = stamps[0], stamps[1]
        # ⚠ MY FIRST CUT TOOK `before` FROM THE REPLY, WHICH HAS NO `t` AT ALL (its keys are
        # fleet/machine/ok/recorded/stored). So `before` was "" and `after > ""` passed for any
        # value whatsoever — a GREEN law asserting nothing. Measured, then fixed to read the
        # STORE on both sides. [[regression-guard]] section 5
        self.assertTrue(before, "the first beacon stored no stamp, so there is no baseline")
        self.assertTrue(after, "no lastseen record survived the second beacon")
        self.assertGreater(str(after), str(before),
                           "the receipt said it wrote, but the stored stamp did not move: "
                           "%r -> %r" % (before, after))

    def test_a_presence_patch_updates_the_window_and_keeps_the_row(self):
        """A window change must land without rebuilding the row, and must not refresh the
        measurement clock. The ages in system were taken at the last full beacon."""
        first = dict(BASE)
        first["windowMode"] = "front"
        first["system"] = {"tree": "ok", "reels": 2,
                           "capture": {"route": "native", "ageS": 12, "source": "capture-half"}}
        second = {"machine": "dean-pc", "event": "hb", "presenceOnly": True,
                  "windowMode": "background",
                  "shadow": {"on": True, "available": True, "recording": False, "working": True}}
        v = _beacons([first, second])
        reply = v["replies"][1]
        self.assertIn("lastseen", (reply or {}).get("stored") or [],
                      "a window change was not stored (stored=%r skipped=%r)"
                      % ((reply or {}).get("stored"), (reply or {}).get("skipped")))
        self.assertFalse([n for n in ((reply or {}).get("stored") or []) if str(n).startswith("consolelog")],
                         "a presence patch wrote a consolelog row")
        row = v["lastseen"]
        self.assertIsNotNone(row, "the patch left no durable record")
        self.assertEqual(row.get("ver"), "v3342", "the patch replaced the row instead of overlaying it")
        self.assertEqual(row.get("windowMode"), "background")
        self.assertEqual((row.get("tally") or {}).get("sets"), {"have": 0, "total": 135})
        self.assertIs((row.get("shadow") or {}).get("on"), True)
        self.assertIs((row.get("shadow") or {}).get("recording"), False)
        # The first beacon's asOf is the first record's t. The patch must leave it there.
        # Re-read it off the stored row: asOf stays, t moves.
        as_of = ((row.get("system") or {}).get("asOf"))
        self.assertTrue(as_of, "the full beacon did not stamp system.asOf, so this proves nothing")
        self.assertEqual(as_of, v["stamps"][0],
                         "the patch refreshed the measurement clock, so ages now read as if they "
                         "were taken at the window change")
        self.assertGreater(row.get("t"), as_of)

    def test_a_presence_patch_with_no_row_stores_nothing(self):
        v = _beacons([{"machine": "dean-pc", "event": "hb", "presenceOnly": True,
                       "windowMode": "background"}])
        reply = v["replies"][0]
        self.assertEqual((reply or {}).get("stored") or [], [])
        self.assertIn("presence patch with no row yet", (reply or {}).get("skipped") or [])
        self.assertIsNone(v["lastseen"], "a patch with no row wrote a thin record")


RED_PROOF = [
    {"why": "REG-3266 - every material beacon writes both keys again, whatever the PC spent today",
     "file": "functions/api/console.js",
     "find": "  const writeNow = (material && !wOver) || ageS >= REFRESH_S;\n",
     "replace": "  const writeNow = material || ageS >= REFRESH_S;\n",
     "matches": 1, "needs": "node"},
    {
        # ⚠ THE ONE-LINE ANCHOR MATCHES 2 AFTER THE FIX - `console:` has the identical condition.
        # Measured before writing this: 2 for the bare line, 1 with the kv.put beneath it.
        # [[regression-guard]] 5a
        "why": "restoring `if (material)` is the exact defect: an idle console stops being "
               "recorded and its row freezes at the last change",
        "file": "functions/api/console.js",
        # v3873 (REG-3266) - both keys follow one decision now (writeNow), so the sabotage aims at it
        "find": "  const writeNow = (material && !wOver) || ageS >= REFRESH_S;\n",
        "replace": "  const writeNow = (material && !wOver);\n",
        "matches": 1,
    },
    {
        "why": "dropping the material arm makes news wait for a timer, so a tick he just made "
               "would not reach the roster for up to 15 minutes",
        "find": "  const writeNow = (material && !wOver) || ageS >= REFRESH_S;\n",
        "file": "functions/api/console.js",
        "replace": "  const writeNow = ageS >= REFRESH_S;\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
