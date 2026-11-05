#!/usr/bin/env python3
# 🖥🛰 T-CONSOLE-FLEET — THE PROOF LAYER FOR THE CONSOLE/FLEET TRACKER.
#
# Konyo, 2026-08-02: "are you sure the console tracker is working? … my cousin in the states used
# it as recently as yesterday and i DONT SEE IT and also my windows PC i dont see it here logged."
#
# Two trackers answer two different questions and must never be conflated:
#   /visits      (functions/visits.js)      — BROWSER page-views of /d2r/, fed by _middleware.js
#   /console     (functions/console.js)     — TV-D console APP presence, HTML dashboard
#   /api/console (functions/api/console.js) — the same fleet as JSON, fed by tv/control_app.py's
#                                             _console_beacon()
# The console app never appears in /visits BY DESIGN. This gate only covers the console pair.
#
# THE BUG THIS GATE EXISTS FOR (A2, "the oldest-400 window"):
#   The offline/history list was built from  kv.list({prefix:'consolelog:', limit:400}).
#   Cloudflare KV returns keys in LEXICOGRAPHIC ASCENDING order and the keys are
#   'consolelog:<ISO-ts>:<machine>' — so ISO order == time order == key order. A bare limit
#   therefore returns the OLDEST 400 events, not the newest. Once the 30-day TTL window holds
#   more than 400 events, every RECENT machine falls off the end and becomes INVISIBLE. That is
#   exactly "my cousin was here yesterday and I can't see him", and it is also why `offline` came
#   back EMPTY on the live site: the oldest 400 rows all belonged to konyo-3, and konyo-3 is
#   suppressed from `offline` because it is already ONLINE. The fix is CURSOR PAGINATION (correct
#   under EITHER ordering — see test 6) plus a durable lastseen: key, not a bigger limit.
#
# NOT a bug (test 2): 'console:' is NOT a prefix of 'consolelog:' — char 8 is ':' vs 'l'. That
# collision was hypothesised and is REFUTED; the test pins the refutation so nobody "fixes" the
# bug into existence, and so a future rename of the log prefix to 'console:log:' is caught the
# moment it lands.
#
# Style: stdlib unittest only (tv/test_routes.py conventions), deterministic, OFFLINE — this gate
# makes NO network call to bull-4-u.com. A Cloudflare Pages Function is exercised by shelling out
# to `node`, importing the REAL handler over file://, and handing it a stub KV backed by an
# in-memory Map. The stub returns keys in LEXICOGRAPHIC ASCENDING order and honours `limit`
# FAITHFULLY — that ordering IS the bug, so faking it wrong would fake the test.
import json
import os
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

# v1883 — THIS FILE IMPORTS control_app IN-PROCESS, so it also imports g5_grok_eyes, and something
# in that path writes his live tv/g5_stats.json. It was the last of six harnesses still doing so
# after v1874 and v1883's fallback fix — measured with his console down, by hashing the whole tree
# before and after a gate run.
#
# It already isolates the beacon with real care, which is exactly why this is worth a comment: a
# harness can be scrupulous about the leak it KNOWS about and still have another. G5_STATS_PATH is
# the override g5_grok_eyes reads first, so this is precise — it moves the stats file and nothing
# else this suite reads. [[feedback-fixtures-never-touch-live-data]]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# #171 — CONTAINED FIRST: a scratch path made before contain() lands outside the parent it removes.
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()
_G5_STATS_SANDBOX = tempfile.mkdtemp(prefix="fleet-g5-")
_G5_STATS_KEEP = os.environ.get("G5_STATS_PATH")
os.environ["G5_STATS_PATH"] = os.path.join(_G5_STATS_SANDBOX, "g5_stats.json")  # REG-1281 — at import too: a harness that skips setUpModule must not reach his real stats


def setUpModule():
    os.environ["G5_STATS_PATH"] = os.path.join(_G5_STATS_SANDBOX, "g5_stats.json")


def tearDownModule():
    if _G5_STATS_KEEP is None:
        os.environ.pop("G5_STATS_PATH", None)
    else:
        os.environ["G5_STATS_PATH"] = _G5_STATS_KEEP
    shutil.rmtree(_G5_STATS_SANDBOX, ignore_errors=True)


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
API_CONSOLE = os.path.join(ROOT, "functions", "api", "console.js")
PAGE_CONSOLE = os.path.join(ROOT, "functions", "console.js")
PAGE_VISITS = os.path.join(ROOT, "functions", "visits.js")

sys.path.insert(0, HERE)

NODE = shutil.which("node")
NODE_TIMEOUT = 40  # a handler that never terminates must fail the gate, not hang it


# ─────────────────────────────────────────────────────────────────────────────
# The node harness. A stub KV over a Map:
#   list({prefix, limit, cursor}) — lexicographic ASCENDING (or DESCENDING when order='desc'),
#                                   `limit` truncates the matching range, `cursor` is an integer
#                                   offset returned as an opaque string.
#   get(name,'json')              — JSON.parse of the stored value, null when absent
#   put(name, value, opts)        — recorded so the tests can assert on TTLs
# Prints ONE line of JSON: {status, text, puts, listCalls}.
# ─────────────────────────────────────────────────────────────────────────────
_HARNESS = r"""
import { pathToFileURL } from 'node:url';
const CFG = __CFG__;

const store = new Map(Object.entries(CFG.seed || {}).map(([k, v]) => [k, JSON.stringify(v)]));
const puts = [];
const listCalls = [];

const kv = {
  async list(opts) {
    opts = opts || {};
    const prefix = opts.prefix || '';
    listCalls.push({ prefix, limit: opts.limit ?? null, cursor: opts.cursor ?? null });
    let names = [...store.keys()].filter((k) => k.startsWith(prefix)).sort();
    if (CFG.order === 'desc') names.reverse();
    const start = opts.cursor ? parseInt(opts.cursor, 10) : 0;
    // what the STORE is willing to hand back in one call, before the caller's limit
    const page = CFG.pageSize || names.length || 1;
    let take = Math.min(page, names.length - start);
    if (opts.limit != null) take = Math.min(take, opts.limit);   // honour limit faithfully
    if (take < 0) take = 0;
    const slice = names.slice(start, start + take);
    const end = start + slice.length;
    // A store that hands back a cursor FOREVER — proves the handler's page cap terminates.
    const forced = CFG.infiniteFor && prefix === CFG.infiniteFor;
    const complete = forced ? false : end >= names.length;
    return {
      keys: slice.map((name) => ({ name })),
      list_complete: complete,
      cursor: complete ? undefined : String(end),
    };
  },
  async get(name, type) {
    const v = store.get(name);
    if (v == null) return null;
    return type === 'json' ? JSON.parse(v) : v;
  },
  async put(name, value, opts) {
    puts.push({ name, value, opts: opts || null });
    store.set(name, value);
  },
  async delete(name) { store.delete(name); },
};

const mod = await import(pathToFileURL(CFG.file).href);
const init = CFG.method === 'POST'
  ? { method: 'POST', body: JSON.stringify(CFG.body || {}), headers: { 'content-type': 'application/json' } }
  : undefined;
const request = new Request(CFG.url, init);
const handler = CFG.method === 'POST' ? mod.onRequestPost : mod.onRequestGet;
const env = Object.assign({ TZ_HISTORY: kv }, CFG.env || {});
const res = await handler({ request, env, params: {}, waitUntil() {} });
const text = await res.text();
process.stdout.write(JSON.stringify({
  status: res.status, text, puts, listCalls,
}));
"""


def run_handler(file, method="GET", url="https://bull-4-u.com/api/console", body=None,
                seed=None, order="asc", page_size=None, infinite_for=None, env=None):
    """Import the REAL Cloudflare function in node against a stub KV; return the parsed verdict."""
    cfg = {
        "file": file, "method": method, "url": url, "body": body,
        "seed": seed or {}, "order": order, "pageSize": page_size,
        "infiniteFor": infinite_for, "env": env or {"VISITS_KEY": "testkey"},
    }
    src = _HARNESS.replace("__CFG__", json.dumps(cfg))
    with tempfile.TemporaryDirectory(prefix="tvd_console_gate_") as d:
        p = os.path.join(d, "harness.mjs")
        with open(p, "w", encoding="utf-8") as f:
            f.write(src)
        try:
            out = subprocess.run([NODE, p], capture_output=True, text=True, timeout=NODE_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise AssertionError(
                "handler did not terminate within %ds — an unbounded kv.list cursor loop?"
                % NODE_TIMEOUT)
    if out.returncode != 0:
        raise AssertionError("node harness failed (rc=%s)\nSTDERR:\n%s\nSTDOUT:\n%s"
                             % (out.returncode, out.stderr[-4000:], out.stdout[-2000:]))
    line = (out.stdout or "").strip().splitlines()[-1] if out.stdout.strip() else ""
    try:
        return json.loads(line)
    except Exception:
        raise AssertionError("harness produced no JSON verdict\nSTDOUT:\n%s\nSTDERR:\n%s"
                             % (out.stdout[-2000:], out.stderr[-2000:]))


def strip_js_comments(src):
    """Remove /* … */ and // … comments so source assertions test CODE, not PROSE. Crude but
    sufficient here: neither console file contains a string literal holding '/*' or '//'."""
    out, i, n = [], 0, len(src)
    while i < n:
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        else:
            out.append(src[i])
            i += 1
    return "".join(out)


def rec(machine, t, **kw):
    """One beacon record as the POST handler writes it."""
    d = {"t": t, "machine": machine, "platform": "mac", "ver": "v1595",
         "mode": "idle", "event": "boot", "user": "", "nickname": "",
         "install": "", "reads": 0, "ip": "", "country": "IL", "city": "Jerusalem"}
    d.update(kw)
    return d


def big_log_seed():
    """533 consolelog rows in ASCENDING key order (== time order, because the key embeds the ISO
    timestamp). The OLDEST 470 are konyo-3; 'mac' fills the middle; 'cousin-pc' appears ONLY at
    the very END with a recent timestamp — i.e. exactly outside a limit:400 oldest-first window."""
    seed = {}
    for i in range(470):                                   # June — the oldest 470
        t = "2026-06-%02dT%02d:%02d:00.000Z" % (i // 48 + 1, (i // 2) % 24, (i % 2) * 30)
        seed["consolelog:%s:konyo-3" % t] = rec("konyo-3", t)
    for i in range(60):                                    # July — the middle 60
        t = "2026-07-%02dT%02d:00:00.000Z" % (i // 2 + 1, (i % 2) * 12)
        seed["consolelog:%s:mac" % t] = rec("mac", t, platform="mac")
    for i in range(3):                                     # August — the NEWEST 3
        t = "2026-08-01T%02d:00:00.000Z" % (10 + i)
        seed["consolelog:%s:cousin-pc" % t] = rec("cousin-pc", t, platform="win",
                                                  country="US", city="Fair Lawn")
    return seed


@unittest.skipIf(NODE is None, "node is not on PATH — the Cloudflare-function harness needs it")
class TestConsoleFleetWindow(unittest.TestCase):
    """A1/A2 — the prefix collision (refuted) and the oldest-first window (real)."""

    # ── 1) THE PIN. This test is RED on the pre-fix limit:400 code and must stay green forever ──
    def test_recent_machine_survives_a_log_window_bigger_than_400(self):
        """Konyo's exact symptom: 533 events in the 30-day window, cousin-pc only in the newest 3.
        Pre-fix (limit:400, no cursor) the handler saw ONLY the oldest 400 rows — all konyo-3, and
        konyo-3 is suppressed because it is ONLINE — so `offline` came back EMPTY, which is what
        the live site actually returned. Post-fix the full log is paginated, so cousin-pc is there."""
        seed = big_log_seed()
        seed["console:konyo-3"] = rec("konyo-3", "2026-08-02T09:00:00.000Z", event="hb")
        v = run_handler(API_CONSOLE, seed=seed, page_size=250)
        self.assertEqual(v["status"], 200)
        data = json.loads(v["text"])
        names = [m["machine"] for m in data["offline"]]
        self.assertIn("cousin-pc", names,
                      "cousin-pc (newest 3 of 533 events) fell outside the log window — "
                      "offline=%r. This is THE bug Konyo reported." % (names,))
        self.assertIn("mac", names, "the mid-window machine must be visible too")
        self.assertEqual([m["machine"] for m in data["online"]], ["konyo-3"])
        # konyo-3 is ONLINE, so it must not be duplicated into offline
        self.assertNotIn("konyo-3", names)

    # ── 2) THE REFUTED COLLISION, pinned from BOTH sides ─────────────────────────────────────
    def test_console_prefix_does_not_match_consolelog_keys(self):
        """'console:' vs 'consolelog:' — char index 8 is ':' in one and 'l' in the other, so
        startsWith('console:') is FALSE for a log key. The collision does not exist. Pinned so a
        future rename of the log prefix to 'console:log:' is caught the instant it lands."""
        self.assertFalse("consolelog:2026-08-01T00:00:00Z:x".startswith("console:"))
        self.assertEqual("consolelog:"[:8], "consolel")
        self.assertEqual("console:"[7], ":")
        self.assertEqual("consolelog:"[7], "l")

    def test_log_only_keys_produce_no_online_machines(self):
        """Functional half of the same pin: seed ONLY consolelog keys, no presence keys at all.
        `online` must be EMPTY. (Non-vacuous: `offline` is non-empty in the same response, so the
        handler demonstrably read the log rows it is being asked not to promote.)"""
        seed = big_log_seed()
        v = run_handler(API_CONSOLE, seed=seed, page_size=250)
        data = json.loads(v["text"])
        self.assertEqual(data["online"], [], "consolelog rows must never be treated as presence")
        self.assertTrue(data["offline"], "the log rows must still surface as offline history")

    def test_online_list_stays_clean_when_log_keys_are_present(self):
        seed = big_log_seed()
        seed["console:konyo-3"] = rec("konyo-3", "2026-08-02T09:00:00.000Z")
        seed["console:mac-mini"] = rec("mac-mini", "2026-08-02T09:01:00.000Z")
        v = run_handler(API_CONSOLE, seed=seed, page_size=250)
        data = json.loads(v["text"])
        self.assertEqual(sorted(m["machine"] for m in data["online"]), ["konyo-3", "mac-mini"])

    # ── 6) BOTH ORDERINGS. Cursor pagination is correct whichever way KV enumerates ──────────
    def test_recent_machine_survives_under_descending_key_order(self):
        """Cloudflare documents lexicographic ASCENDING order, but the fix must not DEPEND on it.
        Same scenario, stub enumerating DESCENDING: the answer must be identical. This is the
        whole argument for paginating instead of raising the limit."""
        seed = big_log_seed()
        seed["console:konyo-3"] = rec("konyo-3", "2026-08-02T09:00:00.000Z")
        v = run_handler(API_CONSOLE, seed=seed, page_size=250, order="desc")
        data = json.loads(v["text"])
        names = [m["machine"] for m in data["offline"]]
        self.assertIn("cousin-pc", names, "descending enumeration lost the recent machine: %r" % (names,))
        self.assertIn("mac", names)


@unittest.skipIf(NODE is None, "node is not on PATH — the Cloudflare-function harness needs it")
class TestConsolePagination(unittest.TestCase):
    """5) The cursor is followed, and the follow TERMINATES."""

    def test_cursor_is_followed_past_page_one(self):
        seed = big_log_seed()
        v = run_handler(API_CONSOLE, seed=seed, page_size=50)
        data = json.loads(v["text"])
        log_lists = [c for c in v["listCalls"] if c["prefix"] == "consolelog:"]
        self.assertGreater(len(log_lists), 1,
                           "handler made ONE consolelog list call for a 533-key range — "
                           "it is not following the cursor")
        self.assertTrue(any(c["cursor"] for c in log_lists), "no call carried a cursor")
        self.assertIn("cousin-pc", [m["machine"] for m in data["offline"]],
                      "page-2+ records never reached the output")

    def test_endless_cursor_terminates_under_the_page_cap(self):
        """A store that hands back a cursor forever must not hang the worker. The handler carries a
        hard page cap (50); without it this call never returns and run_handler raises on timeout."""
        seed = big_log_seed()
        seed["console:konyo-3"] = rec("konyo-3", "2026-08-02T09:00:00.000Z")
        v = run_handler(API_CONSOLE, seed=seed, page_size=50, infinite_for="consolelog:")
        self.assertEqual(v["status"], 200)
        log_lists = [c for c in v["listCalls"] if c["prefix"] == "consolelog:"]
        self.assertLessEqual(len(log_lists), 50,
                            "page cap exceeded: %d consolelog list calls" % len(log_lists))
        self.assertGreater(len(log_lists), 1)


@unittest.skipIf(NODE is None, "node is not on PATH — the Cloudflare-function harness needs it")
class TestConsoleLastSeen(unittest.TestCase):
    """3/4) The durable lastseen: key — 'when was this machine last here' answered DIRECTLY,
    instead of being reconstructed from an event log that was never designed for it."""

    def test_heartbeat_writes_presence_and_lastseen_but_never_a_log_row(self):
        v = run_handler(API_CONSOLE, method="POST",
                        body={"machine": "cousin-pc", "event": "hb", "platform": "win",
                              "ver": "v1595", "mode": "idle"})
        self.assertEqual(v["status"], 200)
        names = [p["name"] for p in v["puts"]]
        self.assertIn("console:cousin-pc", names)
        self.assertIn("lastseen:cousin-pc", names, "heartbeat did not refresh the durable lastseen key")
        self.assertFalse([n for n in names if n.startswith("consolelog:")],
                         "heartbeats must NOT be logged — they would bloat KV: %r" % (names,))
        presence = next(p for p in v["puts"] if p["name"] == "console:cousin-pc")
        # ⚠ v2283 — THE TTL IS HALF OF A BUDGET, so it is checked against the refresh interval
        # rather than against a number typed here. Two kv.put per heartbeat every ~4 min across
        # three machines was ~2,160 writes/day against Cloudflare KV's free 1,000/day; once spent
        # every POST 500'd and three LIVE machines read as "offline · last seen 2h". Presence now
        # refreshes at most every REFRESH_S, and the TTL must outlive TWO missed refreshes or a
        # live machine is evicted between writes — which is the very symptom being fixed.
        ttl_p = (presence["opts"] or {}).get("expirationTtl")
        src = io.open(os.path.join(ROOT, "functions", "api", "console.js"),
                      encoding="utf-8").read() if "ROOT" in globals() else None
        if src is None:
            import pathlib
            src = (pathlib.Path(__file__).resolve().parent.parent
                   / "functions" / "api" / "console.js").read_text(encoding="utf-8")
        import re as _re
        refresh = int(_re.search(r"REFRESH_S\s*=\s*(\d+)", src).group(1))
        self.assertGreaterEqual(ttl_p, 2 * refresh,
                                "presence TTL %r does not cover two missed %ds refreshes, so a "
                                "live machine drops off the roster between writes" % (ttl_p, refresh))
        self.assertLessEqual(ttl_p, 3 * refresh,
                             "presence TTL %r is far longer than the refresh interval — a machine "
                             "that died would keep reading as online for %d minutes"
                             % (ttl_p, ttl_p // 60))
        ls = next(p for p in v["puts"] if p["name"] == "lastseen:cousin-pc")
        ttl = (ls["opts"] or {}).get("expirationTtl")
        self.assertIsNotNone(ttl, "lastseen must carry a long TTL, not the presence TTL")
        self.assertGreaterEqual(ttl, 60 * 60 * 24 * 300,
                                "lastseen TTL %r is too short to answer 'when was he last here'" % ttl)
        self.assertLessEqual(ttl, 60 * 60 * 24 * 400)

    def test_the_header_states_the_presence_ttl_the_code_sets(self):
        """REG-3023 (GrokBot #230) - the header said "TTL 10 min" while PRESENCE_TTL was 2400 s and REFRESH_S 900, so anyone
        reading it would expect a dead machine to leave the roster four times sooner than it does. The header's two
        figures are read against the constants, so a change to either without the header goes red."""
        import re as _re
        src = io.open(API_CONSOLE, encoding="utf-8").read()
        head = _re.sub(r"\s*\n\s*\*\s*", " ", src[:src.index("*/")])
        ttl = int(_re.search(r"const PRESENCE_TTL\s*=\s*(\d+)", src).group(1))
        refresh = int(_re.search(r"const REFRESH_S\s*=\s*(\d+)", src).group(1))
        line = head[head.index("console:<machine>"):head.index("consolelog:<ts>:<machine>")]
        self.assertIn("every REFRESH_S (%d min)" % (refresh // 60), line, "the header's refresh is not the code's: %r" % line)
        self.assertIn("TTL PRESENCE_TTL (%d min)" % (ttl // 60), line, "the header's presence TTL is not the code's: %r" % line)

    def test_lastseen_only_machine_appears_offline_with_its_timestamp(self):
        """No presence key, NO log history at all — the durable key alone must answer."""
        seed = {"lastseen:cousin-pc": rec("cousin-pc", "2026-08-01T12:00:00.000Z",
                                          platform="win", country="US", city="Fair Lawn")}
        v = run_handler(API_CONSOLE, seed=seed)
        data = json.loads(v["text"])
        row = next((m for m in data["offline"] if m["machine"] == "cousin-pc"), None)
        self.assertIsNotNone(row, "a lastseen-only machine vanished: %r" % (data["offline"],))
        self.assertEqual(row["t"], "2026-08-01T12:00:00.000Z")

    def test_online_machine_is_not_duplicated_and_suppression_is_exact_match(self):
        """Suppressing an ONLINE machine from `offline` must be an EXACT name match. 'mac' online
        must not swallow 'mac-mini' — a startsWith/includes suppression would hide it, which is the
        same class of prefix mistake as the (refuted) console:/consolelog: one."""
        seed = {
            "console:mac": rec("mac", "2026-08-02T09:00:00.000Z"),
            "lastseen:mac": rec("mac", "2026-08-02T09:00:00.000Z"),
            "lastseen:mac-mini": rec("mac-mini", "2026-07-30T08:00:00.000Z"),
            "lastseen:cousin-pc": rec("cousin-pc", "2026-08-01T12:00:00.000Z", platform="win"),
        }
        v = run_handler(API_CONSOLE, seed=seed)
        data = json.loads(v["text"])
        off = [m["machine"] for m in data["offline"]]
        self.assertEqual([m["machine"] for m in data["online"]], ["mac"])
        self.assertNotIn("mac", off, "an online machine was duplicated into offline")
        self.assertIn("mac-mini", off, "prefix-sharing machine was wrongly suppressed: %r" % (off,))
        self.assertIn("cousin-pc", off)
        self.assertEqual(len(off), len(set(off)), "duplicate rows in offline: %r" % (off,))

    # ── 7) RUNNER FILTER — CI VMs are not machines of his, in EITHER list or EITHER source ────
    def test_ci_runners_appear_in_neither_list(self):
        seed = {
            "console:fv-az123": rec("fv-az123", "2026-08-02T09:00:00.000Z", country="US", city="Boydton"),
            "console:runnervm-x": rec("runnervm-x", "2026-08-02T09:00:00.000Z"),
            "lastseen:fv-az123": rec("fv-az123", "2026-08-02T09:00:00.000Z"),
            "lastseen:runnervm-x": rec("runnervm-x", "2026-08-02T09:00:00.000Z"),
            "consolelog:2026-08-02T08:00:00.000Z:fv-az123": rec("fv-az123", "2026-08-02T08:00:00.000Z"),
            "lastseen:konyo-3": rec("konyo-3", "2026-08-02T07:00:00.000Z"),
        }
        v = run_handler(API_CONSOLE, seed=seed)
        data = json.loads(v["text"])
        blob = json.dumps(data)
        self.assertNotIn("fv-az123", blob, "a GitHub runner leaked into the fleet")
        self.assertNotIn("runnervm-x", blob)
        # non-vacuous: a real machine from the same seed DID come through
        self.assertIn("konyo-3", [m["machine"] for m in data["offline"]])

    # ── 9) lastBeacon passthrough — the honesty field must survive the round trip, and garbage
    #      in it must never throw (the beacon is fire-and-forget; a bad field cannot 500 the API) ─
    def test_lastbeacon_round_trips_and_garbage_cannot_throw(self):
        v = run_handler(API_CONSOLE, method="POST",
                        body={"machine": "konyo-3", "event": "boot",
                              "lastBeacon": {"ok": False, "code": 0, "err": "boom"}})
        self.assertEqual(v["status"], 200)
        stored = json.loads(next(p["value"] for p in v["puts"] if p["name"] == "console:konyo-3"))
        self.assertIn("lastBeacon", stored, "lastBeacon was dropped on write: %r" % (stored,))
        self.assertIs(stored["lastBeacon"]["ok"], False)
        self.assertIn("boom", json.dumps(stored["lastBeacon"]))
        out = json.loads(run_handler(API_CONSOLE, seed={
            "console:konyo-3": json.loads(next(p["value"] for p in v["puts"]
                                               if p["name"] == "console:konyo-3")),
        })["text"])
        self.assertIs(out["online"][0]["lastBeacon"]["ok"], False)
        for junk in ("not-an-object", 12345, [1, 2, 3], None):
            g = run_handler(API_CONSOLE, method="POST",
                            body={"machine": "konyo-3", "event": "boot", "lastBeacon": junk})
            self.assertEqual(g["status"], 200, "garbage lastBeacon=%r broke the beacon API" % (junk,))


@unittest.skipIf(NODE is None, "node is not on PATH — the Cloudflare-function harness needs it")
class TestConsolePageAuthAndParity(unittest.TestCase):
    """8) The key gate, and 10) no drift between the HTML page and the JSON API."""

    def test_wrong_key_and_missing_key_both_404(self):
        for url in ("https://bull-4-u.com/console?k=wrong",
                    "https://bull-4-u.com/console",
                    "https://bull-4-u.com/console?k="):
            v = run_handler(PAGE_CONSOLE, url=url, seed={
                "console:konyo-3": rec("konyo-3", "2026-08-02T09:00:00.000Z")})
            self.assertEqual(v["status"], 404, "auth leak at %s" % url)
            self.assertEqual(v["text"], "Not found")
            self.assertNotIn("konyo-3", v["text"])

    def test_right_key_returns_html(self):
        v = run_handler(PAGE_CONSOLE, url="https://bull-4-u.com/console?k=testkey", seed={
            "console:konyo-3": rec("konyo-3", "2026-08-02T09:00:00.000Z")})
        self.assertEqual(v["status"], 200)
        self.assertIn("<!doctype html>", v["text"].lower())
        self.assertIn("konyo-3", v["text"])

    def test_html_page_paginates_and_shows_lastseen_machines_too(self):
        """No drift: the dashboard Konyo actually looks at must answer the same as the JSON."""
        seed = big_log_seed()
        seed["console:konyo-3"] = rec("konyo-3", "2026-08-02T09:00:00.000Z")
        seed["lastseen:only-lastseen-box"] = rec("only-lastseen-box", "2026-07-29T12:00:00.000Z")
        v = run_handler(PAGE_CONSOLE, url="https://bull-4-u.com/console?k=testkey",
                        seed=seed, page_size=50)
        self.assertEqual(v["status"], 200)
        self.assertIn("cousin-pc", v["text"], "the HTML dashboard still shows the oldest-400 window")
        self.assertIn("only-lastseen-box", v["text"], "HTML page ignores the durable lastseen keys")
        log_lists = [c for c in v["listCalls"] if c["prefix"] == "consolelog:"]
        self.assertGreater(len(log_lists), 1, "HTML page is not following the cursor")

    def test_neither_source_still_carries_a_bare_limit_400(self):
        """CODE only. Both files deliberately DOCUMENT the old `limit: 400` in a comment so the
        next maintainer knows why the pagination exists — stripping comments first is the
        difference between pinning the fix and forbidding the explanation of it."""
        for path in (API_CONSOLE, PAGE_CONSOLE):
            with open(path, encoding="utf-8") as f:
                code = strip_js_comments(f.read())
            self.assertNotIn("limit: 400", code, "%s still caps the log at the oldest 400" % path)
            self.assertNotIn("limit:400", code, "%s still caps the log at the oldest 400" % path)
            # non-vacuous: the stripper must not have eaten the whole file
            self.assertIn("kv.list", code, "comment stripper removed real code from %s" % path)

    def test_prose_no_longer_claims_the_log_is_the_only_history(self):
        """Rule 3 — kill the stale claim. Both files must name the durable lastseen key, so the
        comments/UI copy describe the storage that actually exists."""
        for path in (API_CONSOLE, PAGE_CONSOLE):
            with open(path, encoding="utf-8") as f:
                src = f.read()
            self.assertIn("lastseen:", src, "%s never mentions the lastseen key" % path)


class TestBeaconHonesty(unittest.TestCase):
    """11) A beacon that has failed every time for months looks IDENTICAL to a machine that was
    never turned on. Konyo must be able to SEE his own machine's last beacon result — without the
    beacon ever becoming blocking."""

    @classmethod
    def setUpClass(cls):
        try:
            import control_app as ca
        except Exception as e:                                   # pragma: no cover
            raise unittest.SkipTest("control_app not importable: %s" % e)
        cls.ca = ca

    def setUp(self):
        """FULL isolation, both ways round. (a) the three suppressor env vars are cleared so the
        beacon genuinely runs — under CI they are SET, and a test that silently early-returns
        proves nothing. (b) the recorded beacon state is snapshotted and its on-disk path is
        redirected into a tempdir: this gate must never leave a .tvd_beacon.json in tv/ nor let
        one test's recorded failure decide the next test's verdict (it did exactly that on the
        first run of this file)."""
        ca = self.ca
        self._env = {k: os.environ.get(k) for k in ("CI", "GITHUB_ACTIONS", "TVD_NO_BEACON")}
        for k in self._env:
            os.environ.pop(k, None)
        self._tmp = tempfile.TemporaryDirectory(prefix="tvd_beacon_state_")
        self._path = getattr(ca, "_BEACON_STATE_PATH", None)
        if self._path is not None:
            ca._BEACON_STATE_PATH = os.path.join(self._tmp.name, "beacon.json")
        self._last = dict(getattr(ca, "_BEACON_LAST", {}) or {})
        if hasattr(ca, "_BEACON_LAST"):
            ca._BEACON_LAST.clear()
        # REG-1788 — doctor_payload now asks the extract. This class is about the beacon,
        # and the ask must not walk his shelf or his sweep memory.
        self._extract = mock.patch.object(
            ca, "_extract_moving_facts",
            lambda: {"owed": 0, "memory": "absent", "ageKnown": True})
        self._extract.start()

    def tearDown(self):
        ca = self.ca
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        if self._path is not None:
            ca._BEACON_STATE_PATH = self._path
        if hasattr(ca, "_BEACON_LAST"):
            ca._BEACON_LAST.clear()
            ca._BEACON_LAST.update(self._last)
        self._extract.stop()
        self._tmp.cleanup()

    def _check(self):
        d = self.ca.doctor_payload()
        c = next((c for c in d["checks"] if c["id"] == "console_beacon"), None)
        self.assertIsNotNone(
            c, "doctor has no console_beacon check — a silently dead beacon stays invisible; "
               "check ids present: %r" % ([x["id"] for x in d["checks"]],))
        return d, c

    def test_beacon_swallows_every_exception(self):
        """Fire-and-forget must stay fire-and-forget. urlopen is monkeypatched to raise, so this
        test makes NO network call — and the env suppressors are cleared in setUp, so the beacon
        genuinely reaches the patched call instead of returning early (non-vacuous)."""
        import urllib.request
        calls = []
        orig = urllib.request.urlopen

        def boom(*a, **k):
            calls.append(1)
            raise OSError("simulated network failure")

        urllib.request.urlopen = boom
        try:
            self.ca._console_beacon("boot")      # must not raise
        finally:
            urllib.request.urlopen = orig
        self.assertEqual(len(calls), 1, "the beacon never attempted the HTTP call — test was vacuous")

    def test_failed_beacon_is_reported_as_a_warn_never_a_block(self):
        import urllib.request
        orig = urllib.request.urlopen

        def boom(*a, **k):
            raise OSError("simulated network failure")

        urllib.request.urlopen = boom
        try:
            self.ca._console_beacon("boot")
            d, c = self._check()
        finally:
            urllib.request.urlopen = orig
        self.assertFalse(c["ok"], "a beacon that just failed reported ok — that is the dishonesty")
        self.assertEqual(c["severity"], "warn",
                         "beacon severity must be 'warn': a machine offline overnight is normal "
                         "and must never fail the doctor")
        self.assertNotIn(c["severity"], ("block", "fail"))
        self.assertTrue(str(c.get("detail") or ""), "the failure must say something readable")

    def test_env_suppression_is_reported_by_name_and_is_not_a_failure(self):
        """The beacon must RUN under suppression (and return without touching the network) for the
        doctor to know it was suppressed rather than broken — that ordering is the real-world one:
        the app beacons, notices the variable, records why."""
        os.environ["TVD_NO_BEACON"] = "1"
        import urllib.request
        orig = urllib.request.urlopen

        def never(*a, **k):
            raise AssertionError("a SUPPRESSED beacon must not touch the network")

        urllib.request.urlopen = never
        try:
            self.ca._console_beacon("hb")
        finally:
            urllib.request.urlopen = orig
        d, c = self._check()
        self.assertTrue(c["ok"], "a deliberately suppressed beacon is not a fault")
        self.assertIn("TVD_NO_BEACON", str(c.get("detail") or ""),
                      "suppression must name the variable so Konyo knows WHY he sees nothing")


@unittest.skipIf(NODE is None, "node is not on PATH — the Cloudflare-function harness needs it")
class TestVisitsPageCarriesConsoleMachines(unittest.TestCase):
    """12) v1687 — THE MACHINES ARE ON /visits NOW, AND THEY ARE STILL NOT PAGE-VIEWS.

    Konyo asked twice, seven days apart, why a console session was not on /visits. Both times the
    honest answer was "different tracker, here is the link", and both times he went back to
    /visits. A pointer is not a tracker. So the machines are rendered here — and the danger of
    that fix is the opposite failure: quietly folding beacons into the page-view counts, which
    would make every number on the page describe something it does not measure.
    """

    def _visits(self, seed, **kw):
        return run_handler(PAGE_VISITS, url="https://bull-4-u.com/visits?k=testkey",
                           seed=seed, **kw)

    def test_a_console_machine_appears_on_the_visits_page(self):
        v = self._visits({
            "lastseen:LAPTOP-COUSIN": rec("LAPTOP-COUSIN", "2026-08-09T17:03:06.347Z",
                                          platform="windows", ver="v1686",
                                          nickname="Dean", country="US", city="Monroe"),
        })
        self.assertEqual(v["status"], 200)
        self.assertIn("Dean", v["text"], "the machine's nickname is not on /visits")
        self.assertIn("LAPTOP-COUSIN", v["text"], "the machine's hostname is not on /visits")
        self.assertIn("Monroe", v["text"], "the machine is listed without where it is")

    def test_presence_key_marks_a_machine_online_and_its_absence_does_not(self):
        """ONLINE is the live `console:` key, never an inference from a recent timestamp."""
        stamp = "2026-08-09T17:03:06.347Z"
        # ⚠ COUNT THE ROW MARKUP, NOT THE WORDS. The first version of this test asserted on the
        # phrase "online now", which also appears in the section's own explanation of what the
        # badge means — so it matched a page with zero online machines and measured nothing.
        both = self._visits({"lastseen:box-a": rec("box-a", stamp),
                             "console:box-a": rec("box-a", stamp)})
        self.assertEqual(1, both["text"].count('class="on-now"'),
                         "a live presence key did not render as an online row")
        durable_only = self._visits({"lastseen:box-a": rec("box-a", stamp)})
        self.assertEqual(0, durable_only["text"].count('class="on-now"'),
                         "a machine with no live presence key was still rendered as online")
        self.assertIn("box-a", durable_only["text"], "an offline machine must still be listed")

    def test_machines_are_never_counted_as_page_views(self):
        """THE FAILURE THIS FIX COULD CAUSE. One page-view and three machines is one page-view."""
        seed = {"visit:1": {"t": "2026-08-09T10:00:00.000Z", "user": "konyo", "ip": "1.2.3.4",
                            "country": "IL", "city": "Jerusalem", "ua": "", "ref": ""}}
        for name in ("box-a", "box-b", "box-c"):
            seed["lastseen:" + name] = rec(name, "2026-08-09T17:00:00.000Z")
            seed["console:" + name] = rec(name, "2026-08-09T17:00:00.000Z")
        v = self._visits(seed)
        self.assertIn("<b>1</b><i>page-views logged</i>", v["text"].replace("\n", ""),
                      "the page-view card moved when only console machines were added")
        self.assertIn("box-c", v["text"], "the machines were not rendered at all")

    def test_ci_runners_stay_off_the_visits_page_too(self):
        v = self._visits({"lastseen:fv-az123-4": rec("fv-az123-4", "2026-08-09T17:00:00.000Z"),
                          "lastseen:konyo-3": rec("konyo-3", "2026-08-09T17:00:00.000Z")})
        self.assertNotIn("fv-az123-4", v["text"], "a GitHub CI runner is listed as one of his machines")
        self.assertIn("konyo-3", v["text"])

    def test_the_page_no_longer_claims_the_console_can_never_appear(self):
        """Rule 3, applied to this change: the copy that was true until v1687 is now the lie.

        Reads the RENDERED page, not the source — a stale sentence in a comment is a comment; a
        stale sentence on screen is what sent him to the wrong page twice.
        """
        v = self._visits({"lastseen:box-a": rec("box-a", "2026-08-09T17:00:00.000Z")})
        flat = " ".join(v["text"].split()).lower()
        for dead in ("can never appear here",
                     "console sessions never appear here",
                     "are not on this page"):
            self.assertNotIn(dead, flat, "stale scope copy still on the page: %r" % dead)

    def test_the_visits_page_does_not_grow_a_third_consolelog_reader(self):
        """The lexicographic trap lives in `consolelog:`. This page must not read it at all —
        a third copy of that helper is how a fix lands in two files out of three."""
        v = self._visits({"lastseen:box-a": rec("box-a", "2026-08-09T17:00:00.000Z")})
        prefixes = {c["prefix"] for c in v["listCalls"]}
        self.assertNotIn("consolelog:", prefixes,
                         "/visits started reading the log prefix — use /console for events")
        # WIDENED DELIBERATELY IN v1694. The INVARIANT this test exists for is unchanged and is
        # asserted above: /visits must never read 'consolelog:'. The set below is a roster of every
        # prefix the page is ALLOWED to read, and v1694 added two of them — 'hvisitor:' (durable
        # per-person identity) and 'hhit:' (30-day per-hit log), both written by the new
        # functions/api/hello.js. Anything NOT in this roster is still a failure, so a third
        # consolelog reader still trips the line above and an unannounced new prefix still trips
        # this one. Widened by hand, never by loosening the comparison.
        self.assertEqual({"visit:", "console:", "lastseen:", "hvisitor:", "hhit:"}, prefixes,
                         "unexpected KV prefixes read by /visits: %r" % (prefixes,))



#: REG-1839 — the sentence a cross-family look found cut on the fleet row (maskWhy, built by control_app at up to 400)
_LONG_WHY = ("this console has no native window (headless or --no-open), so it can COUNT its pieces but can never NAME "
             "them - relaunch it WITH a window; and the board has not handed its stores over either (no board window yet)")
#: the cut's cases, each with its room: a long sentence, one that lands on punctuation, a fit, an exact fit, one over,
#: a single giant token, and an empty one
_CUT_CASES = [(_LONG_WHY, 160), (_LONG_WHY, 140), ("short and whole", 160), ("x" * 160, 160), ("ab " * 54, 160),
              ("y" * 400, 160), ("", 160), ("relaunch it WITH a window; and the board", 27)]


def _js_cut(cases):
    """The SHIPPED cutAtWord, lifted from the worker, over every (text, room). -> [str]"""
    import worker_source as _ws
    prog = (_ws.prelude() + "process.stdout.write(JSON.stringify(%s.map(function (c) { return cutAtWord(c[0], c[1]); })));"
            % json.dumps([list(c) for c in cases]))
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("the worker's cut would not run: %s" % r.stderr[-800:])
    return json.loads(r.stdout)


def _ends_at_a_word(original, got):
    """True when `got` is a prefix of `original` that ends where a word ends, plus one ellipsis."""
    if not got.endswith("…"):
        return False
    kept = got[:-1]
    return original.startswith(kept) and (len(kept) == len(original) or not original[len(kept)].isalnum())


@unittest.skipIf(NODE is None, "node is not on PATH — this law RUNS the shipped worker")
class TheCutEndsAtAWordAndSaysSo(unittest.TestCase):
    """REG-1839 — A SENTENCE CUT WITH NO MARK READS AS A WHOLE ONE. The beacon worker cut a console's own words with a
    bare slice at 160 (eight sites) and 120-200 (five more), so the fleet row read "...relaunch it WITH a window; and
    the board has not" and stopped, as if that were the reason. Its twin on the console, control_app, cut the git
    sentences and three beacon reasons the same way at 160, and a text at or under the worker's room was never cut
    again there. One rule on both sides: the last word that fits, and an ellipsis."""

    def test_the_cut_ends_at_a_word_with_an_ellipsis(self):
        got = _js_cut(_CUT_CASES)
        for (text, n), g in zip(_CUT_CASES, got):
            with self.subTest(text=text[:40], n=n):
                self.assertLessEqual(len(g), n, "the cut is longer than its room: %r" % g)
                if len(text) <= n:
                    self.assertEqual(g, text, "text that fits came back changed")
                elif len(set(text)) == 1:
                    self.assertEqual(g, text[:n - 1] + "…", "one giant token must keep its hard cut and say so")
                else:
                    self.assertTrue(_ends_at_a_word(text, g), "the cut landed mid-word or said nothing: %r" % g)
        self.assertEqual(got[-1], "relaunch it WITH a window…",
                         "a cut that lands after punctuation keeps the punctuation: %r" % got[-1])

    def test_the_console_cuts_the_same_way(self):
        import control_app as ca
        for (text, n), g in zip(_CUT_CASES, _js_cut(_CUT_CASES)):
            with self.subTest(text=text[:40], n=n):
                self.assertEqual(ca._word_cut(text, n), g, "control_app._word_cut and the worker's cut disagree")

    def test_every_reason_the_worker_keeps_ends_at_a_word(self):
        """Through the REAL handler: a beacon whose every reason is the long sentence."""
        body = {"machine": "cut-pc", "event": "hb", "platform": "win", "ver": "v1", "mode": "idle",
                "maskWhy": {"sets": _LONG_WHY, "uniques": _LONG_WHY},
                "tally": {"ok": False, "why": _LONG_WHY},
                "shadow": {"on": True, "why": _LONG_WHY},
                "readers": {"claude": {"state": "off", "why": _LONG_WHY}, "grok": {"state": "off", "why": _LONG_WHY}},
                "relaunch": {"armed": True, "may": False, "why": _LONG_WHY, "err": "fatal: " + _LONG_WHY},
                "pull": {"can": False, "behind": 2, "why": _LONG_WHY, "err": "fatal: " + _LONG_WHY},
                "system": {"tree": "ok", "reels": 1,
                           "river": {"lanes": {"PRINTER": 1}, "ageS": 1.0, "why": _LONG_WHY + " " + _LONG_WHY}}}
        v = run_handler(API_CONSOLE, method="POST", body=body)
        self.assertEqual(v["status"], 200)
        rec = json.loads(next(p for p in v["puts"] if p["name"] == "console:cut-pc")["value"])
        kept = {"maskWhy.sets": (rec["maskWhy"]["sets"], 160), "maskWhy.uniques": (rec["maskWhy"]["uniques"], 160),
                "tally.why": (rec["tally"]["why"], 160), "shadow.why": (rec["shadow"]["why"], 160),
                "readers.claude.why": (rec["readers"]["claude"]["why"], 160),
                "readers.grok.why": (rec["readers"]["grok"]["why"], 160),
                "relaunch.why": (rec["relaunch"]["why"], 160), "pull.why": (rec["pull"]["why"], 160),
                "relaunch.err": (rec["relaunch"]["err"], 160), "pull.err": (rec["pull"]["err"], 160),
                "system.river.why": (rec["system"]["river"]["why"], 200)}
        for name, (g, n) in kept.items():
            with self.subTest(name):
                self.assertIsInstance(g, str, "%s did not cross" % name)
                self.assertLessEqual(len(g), n)
                src = ("fatal: " + _LONG_WHY) if name.endswith(".err") else (
                    (_LONG_WHY + " " + _LONG_WHY) if name.startswith("system") else _LONG_WHY)
                self.assertTrue(_ends_at_a_word(src, g), "%s was cut mid-word or without a mark: %r" % (name, g))

    def test_the_console_ends_its_own_reasons_at_a_word(self):
        """The three beacon reasons and the git sentence the console cuts itself, at or under the worker's room."""
        from unittest import mock as _m
        import control_app as ca
        with _m.patch.object(ca, "_reader_health", return_value={"claude": {"state": "off", "why": _LONG_WHY}}):
            rd = ca._readers_for_wire()["claude"]["why"]
        with _m.patch.object(ca, "_shadow_state", return_value={"on": True, "say": _LONG_WHY}):
            sh = ca._shadow_for_wire()["why"]
        with _m.patch.object(ca, "_auto_relaunch_state", return_value={"effective": True}), \
                _m.patch.object(ca, "drift_may_relaunch", return_value=(False, _LONG_WHY)), \
                _m.patch.object(ca, "_beacon_git_diag", side_effect=lambda d: d):
            rl = ca._relaunch_report()["why"]
        with _m.patch.dict(os.environ, {"TV_NO_AUTO_PULL": ""}), \
                _m.patch.object(ca, "fleet_origin_status", return_value={"ok": False, "howTo": _LONG_WHY}), \
                _m.patch.object(ca, "_beacon_git_diag", side_effect=lambda d: d):
            pl = ca._pull_report()["why"]
        git = ca._public_git_text("fatal: " + _LONG_WHY, 160)
        for name, g, n, src in (("readers", rd, 160, _LONG_WHY), ("shadow", sh, 160, _LONG_WHY),
                                ("relaunch", rl, 160, _LONG_WHY), ("pull", pl, 120, _LONG_WHY),
                                ("git text", git, 160, "fatal: " + _LONG_WHY)):
            with self.subTest(name):
                self.assertLessEqual(len(g), n)
                self.assertTrue(_ends_at_a_word(src, g), "the console cut its %s reason mid-word: %r" % (name, g))


RED_PROOF = [
    {
        "why": "REG-3023 - the header names a presence TTL the code does not set",
        "file": "functions/api/console.js",
        "find": " *                               TTL PRESENCE_TTL (10 min) → key alive",
        "replace": " *                               TTL 40 min → key alive",
        "matches": 1,
    },
    {
        "why": "REG-3023 - the presence TTL moves and the header does not",
        "file": "functions/api/console.js",
        "find": "  const PRESENCE_TTL = 600; ",
        "replace": "  const PRESENCE_TTL = 1200; ",
        "matches": 1,
    },
    {
        'why': 'The fleet roster only sees every machine because listAll() FOLLOWS THE KV CURSOR — a single kv.list() page returns the OLDEST rows and made Konyo\'s cousin invisible. This line is the loop\'s continue/stop decision; replacing it with a bare `break` collapses listAll to page one, which is the pre-fix oldest-window bug restored. It is executable code, not a comment, not a message string, and not a constant read by both sides of an agreement law (PAGE_CAP/PAGE_SIZE are untouched, and the byte-identical twin in functions/console.js is a different file so no parity law masks it).  MEASURED: untampered python3 tv/test_console_fleet.py -> OK, "Ran 26 tests in 2.750s", 0 skipped (nod; tampered (all 1) python3 tv/test_console_fleet.py -> FAILED (failures=3): TestConsoleFleetWindow.; reddened law test_console_fleet.TestConsolePagination.test_cursor_is_followed_past_; ALONE python3 -m unittest test_console_fleet.TestConsolePagination.test_cursor_is_followed_past_page_one (.',
        'file': 'functions/api/console.js',
        'find': 'if (page.list_complete || !page.cursor) break;',
        'replace': 'break;',
        'matches': 1,
    },
    {
        "why": "REG-1839 - the worker's cut is a bare slice again, so a reason stops mid-word with no mark",
        "file": "functions/api/console.js",
        "find": "  if (s.length <= n) return s;\n  let head = s.slice(0, Math.max(1, n - 1));\n",
        "replace": "  if (s.length <= n) return s;\n  return s.slice(0, n);\n  let head = s.slice(0, Math.max(1, n - 1));\n",
        "matches": 1,
    },
    {
        "why": "REG-1839 - the console's cut is a bare slice again, so its own reasons stop mid-word",
        "file": "control_app.py",
        "find": "    head = s[:max(1, limit - 1)]\n",
        "replace": "    return s[:limit]\n    head = s[:max(1, limit - 1)]\n",
        "matches": 1,
    },
    {
        "why": "REG-1839 - the maskWhy shaper slices bare again: the exact sentence the fleet row showed cut",
        "file": "functions/api/console.js",
        "find": "        if (typeof v === 'string' && v) out[k] = cutAtWord(v, 160);",
        "replace": "        if (typeof v === 'string' && v) out[k] = v.slice(0, 160);",
        "matches": 1,
    },
    {
        "why": "REG-1839 - the system shaper's text cut is bare again, so a river reason stops mid-word",
        "file": "functions/api/console.js",
        "find": "        return x ? cutAtWord(x, cap) : null;\n",
        "replace": "        return x ? x.slice(0, cap) : null;\n",
        "matches": 1,
    },
    {
        "why": "REG-1839 - the console cuts a reader's reason bare at the worker's own room, so the worker never re-cuts it",
        "file": "control_app.py",
        "find": "                  \"why\": _word_cut(\" \".join(str(why).split()), 160) if why else None}",
        "replace": "                  \"why\": \" \".join(str(why).split())[:160] if why else None}",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
