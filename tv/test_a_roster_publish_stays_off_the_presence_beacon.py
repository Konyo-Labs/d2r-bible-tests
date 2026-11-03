#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REG-2166 (#39) - Fleet 3.0 phase 1 publishes on its own route.

The presence beacon stays /api/console. No item name crosses that beacon.
Roster rows go to /api/roster under the owner label, hourly and change-only,
plus one at boot. Over the daily cap the server says why and answers 200,
never a 500 that looks like the machine went offline. A section that was
not read stays absent. Pictures and frame bytes stay off the body.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
import sys
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import roster_publish as RP  # noqa: E402
from console_safe import enable  # noqa: E402

enable()

NODE = shutil.which("node")
ROSTER_JS = os.path.join(ROOT, "functions", "api", "roster.js")
CONSOLE_JS = os.path.join(ROOT, "functions", "api", "console.js")
APP = os.path.join(HERE, "control_app.py")
OWNER = "Konyo · Mac"

_HARNESS = r"""
import { pathToFileURL } from 'node:url';
const CFG = __CFG__;
const store = new Map(Object.entries(CFG.seed || {}).map(([k, v]) => [k, JSON.stringify(v)]));
const puts = [];
const kv = {
  async get(n) {
    if (CFG.throwGet) throw new Error('KV get failed');
    return store.has(n) ? store.get(n) : null;
  },
  async put(n, v) {
    if (CFG.throwPut) throw new Error('KV put failed');
    puts.push(n);
    store.set(n, v);
  },
};
const mod = await import(pathToFileURL(CFG.file).href);
const replies = [];
const statuses = [];
for (let i = 0; i < CFG.bodies.length; i++) {
  if (i > 0 && CFG.ageBetween) {
    for (const [k, raw] of store.entries()) {
      if (!k.startsWith('roster:')) continue;
      const o = JSON.parse(raw);
      o.t = Date.now() - CFG.ageBetween * 1000;
      store.set(k, JSON.stringify(o));
    }
  }
  // #95 - a body may arrive as EXACT bytes (base64) with its own headers (X-Roster-Key / X-Roster-Sig),
  // so a signature made in Python is checked over the very bytes it covers. A plain body posts as before.
  const one = CFG.bodies[i];
  const exact = one && typeof one === 'object' && typeof one.__raw === 'string';
  const req = new Request('https://bull-4-u.com/api/roster', {
    method: 'POST', body: exact ? new Uint8Array(Buffer.from(one.__raw, 'base64')) : JSON.stringify(one),
    headers: Object.assign({ 'content-type': 'application/json' }, (exact && one.__headers) || {}) });
  const res = await mod.onRequestPost({ request: req, env: { TZ_HISTORY: kv }, waitUntil(){} });
  statuses.push(res.status);
  replies.push(JSON.parse(await res.text()));
}
const records = {};
for (const [k, raw] of store.entries()) records[k] = JSON.parse(raw);
let got = null;
if (CFG.get) {
  const req = new Request('https://bull-4-u.com/api/roster', { method: 'GET' });
  const res = await mod.onRequestGet({ request: req, env: { TZ_HISTORY: kv }, waitUntil(){} });
  got = { status: res.status, body: JSON.parse(await res.text()) };
}
process.stdout.write(JSON.stringify({ replies, statuses, puts, keys: [...store.keys()], records, got }));
"""


def _post(bodies, seed=None, throw_put=False, age_between=0, get=False, throw_get=False):
    if not NODE:
        raise AssertionError("node is absent - the worker was not run")
    cfg = {"file": ROSTER_JS, "bodies": bodies, "seed": seed or {},
           "throwPut": throw_put, "ageBetween": age_between,
           "get": get, "throwGet": throw_get}
    src = _HARNESS.replace("__CFG__", json.dumps(cfg))
    with tempfile.TemporaryDirectory(prefix="tvd_roster_") as d:
        path = os.path.join(d, "h.mjs")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(src)
        r = subprocess.run([NODE, path], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("roster harness failed rc=%s\n%s" % (r.returncode, r.stderr[-2000:]))
    return json.loads((r.stdout or "").strip().splitlines()[-1])


def _char(n, as_of=1000):
    return {"read": True, "asOf": as_of, "counts": n, "rows": [{"name": "Sorceress", "cls": "Sorceress", "level": n}]}


def _body(n=1, boot=False, as_of=1000, extra=None):
    sections = {"characters": {"asOf": as_of, "counts": n, "rows": [
        {"name": "Sorceress", "cls": "Sorceress", "level": n}]}}
    body = {"owner": OWNER, "boot": boot, "sections": sections}
    if extra:
        body.update(extra)
    return body


class RosterPublishStaysOffTheBeacon(unittest.TestCase):

    def test_the_budget_stays_under_the_ceiling(self):
        got = RP.budget()
        self.assertEqual(got["presence"], 768)
        self.assertEqual(got["pcs"] * got["perPc"], 100)
        self.assertEqual(got["together"], 868)
        self.assertLess(got["together"], got["ceiling"])
        self.assertLess(768 + 5 * 25, 1000, "the five labels at the cap would pass 1000")
        js = open(ROSTER_JS, encoding="utf-8").read()
        for line in ("const PRESENCE_WRITES = 768;", "const ROSTER_PCS = 4;",
                     "const ROSTER_CAP = 25;", "const KV_WRITES = 1000;"):
            self.assertIn(line, js)
        console = open(CONSOLE_JS, encoding="utf-8").read()
        # REG-2204 (#99) — the invariant is ENFORCED by the tally SHAPER, not the comment that
        # describes it: each count is coerced with Number() and a non-number (an item name → NaN) is
        # dropped, so only have/total cross. Anchor on that code — the comment could stay while the
        # shaping was torn out (source-reading-guard §4b).
        self.assertIn("const have = Number(p.have);", console,
                      "the tally stopped coercing have to a Number — an item name could cross")
        self.assertIn("if (!Number.isFinite(have) || have < 0) return null;", console,
                      "the tally stopped dropping a non-number (an item name becomes NaN) — it could cross")
        self.assertNotIn("roster:", console)

    def test_an_unread_section_stays_absent(self):
        self.assertIsNone(RP.section_of(None))
        self.assertIsNone(RP.section_of([]))
        self.assertIsNone(RP.section_of({"read": False, "rows": []}))
        self.assertIsNone(RP.characters_read(False, {"chars": {}}, [], 1000))
        self.assertIsNone(RP.vault_read("absent", [], 1000))
        self.assertIsNone(RP.vault_read("unreadable: no", [], 1000))
        self.assertIsNone(RP.chronicle_read({"ok": False, "why": "not read"}, 1000))
        self.assertIsNone(RP.stash_read(None, 1000))
        self.assertIsNone(RP.reels_read(None, {}, {}, 1000))
        got = RP.sections_from({"vault": [], "characters": _char(1)}, 1000)
        self.assertNotIn("vault", got)
        self.assertIn("characters", got)
        self.assertNotIn("rows", got["characters"]) if False else None
        empty = RP.section_of({"read": True, "asOf": 1000, "counts": 0, "rows": []})
        self.assertEqual(empty, {"asOf": 1000, "counts": 0})
        self.assertNotIn("rows", empty)

    def test_reels_stations_count_only_live_shelf_reels(self):
        """REG-2205 (#99) — a river stamp survives a reel's deletion, so a station count built from
        every stamp counted GONE reels (measured 198 vs 67 live). reels_read counts a station only
        for a reel still on the shelf it was handed, and skips an UNKNOWN stamp."""
        names = ["reel_a", "reel_b"]                       # the live shelf
        stamps = {"reel_a": "PRINTER", "reel_b": "UNKNOWN",   # b is live but UNKNOWN — not a station
                  "reel_gone": "PRINTER", "reel_also_gone": "RIVER"}  # stamps linger past deletion
        got = RP.reels_read(names, stamps, {"PRINTER": 3, "RIVER": 1}, 1000)
        self.assertEqual(got["counts"]["reels"], 2)
        self.assertEqual(got["counts"]["stations"], 1,
                         "a gone reel's lingering stamp or an UNKNOWN was counted as a live station (#99)")

    def test_pictures_and_frame_bytes_stay_off_the_row(self):
        row = RP._clean_row({
            "name": "Shako",
            "tier": "PROVEN",
            "frame": "data:image/png;base64,AAAA",
            "evidence": ["s_1784984019250_fx", "reel/f_1.jpg", "/tmp/shot/a.png"],
        }, ("name", "tier", "evidence"))
        self.assertEqual(row["name"], "Shako")
        self.assertNotIn("frame", row)
        self.assertEqual(row["evidence"], ["s_1784984019250_fx"])
        self.assertIsNone(RP._clean_row({"name": "data:image/png;base64,AAAA"}))

    def test_the_key_is_the_owner_label(self):
        self.assertEqual(RP.roster_key(OWNER), "roster:" + OWNER)
        self.assertIsNone(RP.roster_key("konyo-3"))
        self.assertIsNone(RP.roster_key("/tmp/host"))
        self.assertIsNone(RP.owner_of("23d0486747ce4c58"))
        self.assertEqual(len(RP.OWNERS), 5)

    def test_a_mac_named_konyo_is_the_mac_roster_label(self):
        self.assertEqual(RP.owner_of("Konyo", "mac"), OWNER)
        self.assertIsNone(RP.owner_of("Konyo", "windows"))
        self.assertIsNone(RP.owner_of("Konyo"))
        self.assertIsNone(RP.owner_of("Grok", "mac"))
        self.assertIsNone(RP.owner_of("someone", "mac"))
        self.assertEqual(RP.owner_of("Dean", "mac"), "Dean")
        self.assertEqual(RP.owner_of("Wife PC", "windows"), "Wife PC")
        with open(APP, encoding="utf-8") as fh:
            src = fh.read()
        once = src.split("def _roster_publish_once(", 1)[1].split("def _roster_publish_loop", 1)[0]
        call = "owner = _rp.owner_of(_roster_claimed_name(), _roster_platform())"
        self.assertEqual(once.count(call), 1)

    def test_change_only_hourly_and_one_boot(self):
        now = 1_000_000
        body, why = RP.due({}, OWNER, RP.sections_from({"characters": _char(1)}), now, False)
        self.assertEqual(why, "post")
        state = {"hash": RP.hash_of(RP.packed(RP.for_hash(body["sections"]))), "at": now}
        # REG-2512 (#95) - boot posts even an unchanged body (the server skips the write when its hash
        # matches, and overwrites a forged row otherwise). Only a tick stays quiet when nothing changed.
        again, why = RP.due(state, OWNER, body["sections"], now + 1000, True)
        self.assertEqual(why, "post")
        self.assertEqual(again["signedAt"], now + 1000)
        again, why = RP.due(state, OWNER, body["sections"], now + 1000, False)
        self.assertIsNone(again)
        self.assertEqual(why, "unchanged")
        moved = RP.sections_from({"characters": _char(2)})
        held, why = RP.due(state, OWNER, moved, now + 1000, False)
        self.assertIsNone(held)
        self.assertEqual(why, "within the hour")
        booted, why = RP.due(state, OWNER, moved, now + 1000, True)
        self.assertEqual(why, "post")
        self.assertEqual(booted["owner"], OWNER)
        later, why = RP.due(state, OWNER, moved, now + RP.HOUR_MS, False)
        self.assertEqual(why, "post")
        refused = dict(state, refuseAt=now, why="roster would not take this publish: quota")
        quiet, why = RP.due(refused, OWNER, moved, now + 1000, True)
        self.assertIsNone(quiet)
        self.assertIn("quota", why)

    def test_a_skip_is_not_remembered_as_a_publish(self):
        sections = RP.sections_from({"characters": _char(2)})
        state = RP.apply_reply({}, sections, {"ok": True, "stored": [], "skipped": ["within the hour"]}, 50)
        self.assertNotIn("hash", state)
        self.assertEqual(state["at"], 50)
        published = RP.apply_reply(state, sections, {"ok": True, "stored": ["roster"]}, 80)
        self.assertEqual(published["why"], "published")
        self.assertIn("hash", published)

    def test_the_worker_writes_the_owner_key_and_not_the_beacon(self):
        v = _post([_body(1, boot=True, extra={"machine": "konyo-3", "install": "abc"})])
        self.assertEqual(v["statuses"], [200])
        self.assertEqual(v["replies"][0]["stored"], ["roster"])
        self.assertEqual(v["keys"], ["roster:" + OWNER])
        rec = v["records"]["roster:" + OWNER]
        self.assertNotIn("konyo-3", json.dumps(rec))
        self.assertNotIn("install", rec)
        self.assertNotIn("machine", rec)
        self.assertEqual(v["puts"], ["roster:" + OWNER])

    def test_a_signed_publish_reads_back_verified_through_the_viewer(self):
        """#95 - the same worker, sent EXACT bytes and the two headers: a body signed by a PC's key reads
        back intentVerified:true through GET and view_of, and registers that key. The unsigned bodies the
        rest of this file posts still store, said false, so a PC that has not updated keeps publishing."""
        import base64
        import roster_sign as RS
        with tempfile.TemporaryDirectory(prefix="tvd_roster_key_") as d:
            raw = json.dumps(_body(7, boot=True), ensure_ascii=False).encode("utf-8")
            heads, signing = RS.sign_headers(RS.key_path_in(d), raw)
        self.assertIs(signing["signed"], True, signing)
        v = _post([{"__raw": base64.b64encode(raw).decode("ascii"), "__headers": heads}], get=True)
        self.assertEqual(v["replies"][0]["stored"], ["roster"])
        self.assertIs(v["replies"][0]["intentVerified"], True, v["replies"][0])
        self.assertEqual(sorted(v["keys"]), sorted(["roster:" + OWNER, "rosterkey:" + OWNER]))
        t = v["records"]["roster:" + OWNER]["t"]
        mine = [r for r in RP.view_of(v["got"]["body"]["owners"], t) if r["owner"] == OWNER][0]
        self.assertIs(mine["intentVerified"], True)
        plain = _post([_body(7, boot=True)], get=True)
        t = plain["records"]["roster:" + OWNER]["t"]
        theirs = [r for r in RP.view_of(plain["got"]["body"]["owners"], t) if r["owner"] == OWNER][0]
        self.assertIs(theirs["intentVerified"], False)
        self.assertEqual(plain["keys"], ["roster:" + OWNER], "an unsigned publish registered a key")

    def test_a_hostname_is_not_a_key(self):
        v = _post([{"owner": "konyo-3", "sections": _body()["sections"]}])
        self.assertEqual(v["statuses"], [200])
        self.assertIs(v["replies"][0]["ok"], False)
        self.assertIn("owner label", v["replies"][0]["why"])
        self.assertEqual(v["keys"], [])

    def test_an_unread_section_is_not_stored_as_an_empty_list(self):
        seed_key = "roster:" + OWNER
        seed = {seed_key: {"owner": OWNER, "t": 1, "day": "2000-01-01", "n": 1, "hash": "old",
                           "sections": {"vault": {"asOf": 1, "counts": 2, "rows": [{"name": "Shako"}]}}}}
        body = _body(1, boot=True)
        body["sections"]["vault"] = []
        v = _post([body], seed=seed)
        rec = v["records"][seed_key]
        self.assertIn("characters", rec["sections"])
        self.assertIn("vault", rec["sections"])
        self.assertNotEqual(rec["sections"]["vault"], [])
        self.assertEqual(rec["sections"]["vault"]["rows"][0]["name"], "Shako")
        self.assertNotIn("chronicle", rec["sections"])

    def test_a_measured_empty_is_a_count_and_not_a_list(self):
        body = {"owner": OWNER, "boot": True, "sections": {
            "vault": {"asOf": 1000, "counts": 0, "rows": []}}}
        v = _post([body])
        rec = v["records"]["roster:" + OWNER]
        self.assertEqual(rec["sections"]["vault"], {"asOf": 1000, "counts": 0})
        self.assertNotIn("rows", rec["sections"]["vault"])

    def test_unchanged_and_the_hour_do_not_write(self):
        first = _body(1, boot=False, as_of=1000)
        second = _body(1, boot=True, as_of=9000)
        v = _post([first, second])
        self.assertEqual(v["replies"][1]["skipped"], ["unchanged"])
        self.assertEqual(v["puts"], ["roster:" + OWNER])
        moved = _body(4, boot=False, as_of=9000)
        v2 = _post([first, moved])
        self.assertEqual(v2["replies"][1]["skipped"], ["within the hour"])
        self.assertEqual(len(v2["puts"]), 1)
        v3 = _post([first, _body(4, boot=True)])
        self.assertEqual(v3["replies"][1]["stored"], ["roster"])
        self.assertEqual(len(v3["puts"]), 2)

    def test_the_daily_cap_is_a_refusal_and_not_an_outage(self):
        bodies = [_body(i, boot=True) for i in range(1, 27)]
        v = _post(bodies)
        self.assertEqual(v["statuses"][-1], 200)
        self.assertIs(v["replies"][-1]["ok"], False)
        self.assertEqual(v["replies"][-1]["why"], "roster would not take this publish: quota")
        self.assertIn("NOT the machine being absent", v["replies"][-1]["hint"])
        self.assertEqual(len(v["puts"]), 25)
        self.assertEqual(v["records"]["roster:" + OWNER]["n"], 25)

    def test_a_new_day_is_not_still_over_the_cap(self):
        seed = {"roster:" + OWNER: {"owner": OWNER, "t": 10, "day": "2000-01-01", "n": 25,
                                    "hash": "old", "sections": {"characters": {"asOf": 1, "counts": 1}}}}
        v = _post([_body(3, boot=True)], seed=seed)
        self.assertEqual(v["replies"][0]["stored"], ["roster"])
        self.assertEqual(v["records"]["roster:" + OWNER]["n"], 1)

    def test_a_storage_throw_is_not_a_500(self):
        v = _post([_body(1, boot=True)], throw_put=True)
        self.assertEqual(v["statuses"], [200])
        self.assertIs(v["replies"][0]["ok"], False)
        self.assertIn("roster would not take this publish", v["replies"][0]["why"])
        self.assertIn("NOT the machine being absent", v["replies"][0]["hint"])
        self.assertEqual(v["keys"], [])

    def test_pictures_in_the_body_are_refused(self):
        body = _body(1, boot=True)
        body["sections"]["characters"]["rows"][0]["shot"] = "data:image/jpeg;base64,AAAA"
        v = _post([body])
        self.assertEqual(v["statuses"], [200])
        self.assertIs(v["replies"][0]["ok"], False)
        self.assertIn("pictures", v["replies"][0]["why"])
        self.assertEqual(v["keys"], [])

    def test_the_console_posts_roster_on_its_own_route(self):
        src = open(APP, encoding="utf-8").read()
        self.assertIn("https://bull-4-u.com/api/roster", src)
        self.assertEqual(src.count('target=_roster_publish_loop'), 1)
        beacon = src.split("def _console_beacon(", 1)[1].split("def _console_beacon_async", 1)[0]
        self.assertNotIn("/api/roster", beacon)
        self.assertNotIn("roster_publish", beacon)
        once = src.split("def _roster_publish_once(", 1)[1].split("def _roster_publish_loop", 1)[0]
        self.assertIn("_beacon_suppressed_by()", once)
        self.assertIn("/api/roster", once)
        self.assertNotIn("/api/console", once)
        reads = src.split("def _roster_reads(", 1)[1].split("def _roster_post", 1)[0]
        for name in ("characters_read", "vault_read", "chronicle_read", "reels_read", "stash_read"):
            self.assertIn(name, reads)
        self.assertNotIn("stash_read", beacon)
        self.assertNotIn("roster-book", beacon)
        self.assertNotIn("d2r_charBuilds", beacon)

    def test_a_fetch_is_a_read_and_a_missing_pc_is_not_an_empty_vault(self):
        got = _post([], get=True)["got"]
        self.assertEqual(got["status"], 200)
        self.assertIs(got["body"]["ok"], True)
        owners = got["body"]["owners"]
        self.assertEqual([row["owner"] for row in owners], list(RP.OWNERS))
        for row in owners:
            self.assertIs(row["published"], False)
            self.assertNotIn("sections", row)
        self.assertEqual(_post([], get=True)["puts"], [])
        seeded = {
            "roster:Dean": {"owner": "Dean", "t": 10, "day": "2000-01-01", "n": 1,
                            "hash": "dead", "sections": {"characters": {
                                "asOf": 10, "counts": 1, "rows": [{"name": "Sorceress"}]}}},
        }
        bad = _post([], seed=seeded, get=True)["got"]["body"]
        dean = [row for row in bad["owners"] if row["owner"] == "Dean"][0]
        self.assertIs(dean["corrupt"], True)
        self.assertNotIn("sections", dean)
        wife = [row for row in bad["owners"] if row["owner"] == "Wife PC"][0]
        self.assertIs(wife["published"], False)
        self.assertNotIn("sections", wife)
        thrown = _post([], get=True, throw_get=True)["got"]
        self.assertEqual(thrown["status"], 200)
        self.assertIs(thrown["body"]["ok"], False)
        self.assertIn("fetch", thrown["body"]["why"])

    def test_the_posted_hash_is_the_hash_the_viewer_checks(self):
        posted = _post([_body()], get=True)
        self.assertEqual(posted["puts"], ["roster:" + OWNER])
        rec = posted["records"]["roster:" + OWNER]
        self.assertEqual(rec["hash"], RP.hash_of(RP.packed(RP.for_hash(rec["sections"]))))
        mac = [row for row in posted["got"]["body"]["owners"] if row["owner"] == OWNER][0]
        self.assertIs(mac["corrupt"], False)
        self.assertIn("characters", mac["sections"])
        self.assertNotIn("vault", mac["sections"])
        views = RP.view_of(posted["got"]["body"]["owners"], rec["t"])
        shown = [row for row in views if row["owner"] == OWNER][0]
        self.assertIs(shown["corrupt"], False)
        self.assertEqual(shown["age"], "current")
        self.assertNotIn("vault", shown["sections"])
        stale = RP.view_of(posted["got"]["body"]["owners"], rec["t"] + 2 * RP.HOUR_MS + 1)
        old = [row for row in stale if row["owner"] == OWNER][0]
        self.assertEqual(old["age"], "stale")
        self.assertEqual(old["sections"]["characters"]["age"], "stale")
        self.assertEqual(RP._age_state(None, rec["t"]), "unknown")
        self.assertEqual(RP._age_state(True, rec["t"]), "unknown")
        quiet = [row for row in views if row["owner"] == "Dean"][0]
        self.assertIs(quiet["published"], False)
        self.assertNotIn("sections", quiet)
        self.assertEqual(RP.never_published_line("Dean", "vault"),
                         "Dean has not published its vault yet")
        self.assertIsNone(RP.cache_views({"ok": True}, rec["t"]))
        self.assertIsNone(RP.cache_views({"ok": False, "owners": []}, rec["t"]))
        empty = RP.cache_views({"ok": True, "owners": []}, rec["t"])
        self.assertEqual(len(empty), 5)
        self.assertTrue(all(row["published"] is False for row in empty))
        self.assertIsNone(RP.view_one("not-a-pc", {}, 1))
        lied = dict(mac, hash="dead")
        self.assertNotIn("sections", RP.view_one(OWNER, lied, rec["t"]))
        with tempfile.TemporaryDirectory() as d:
            ledger = os.path.join(d, "ledger.json")
            with open(ledger, "w", encoding="utf-8") as fh:
                fh.write("keep")
            names = RP.write_cache(os.path.join(d, "roster_cache"), views)
            self.assertIn("Konyo__Mac.json", names)
            self.assertIn("Dean.json", names)
            with open(ledger, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "keep")
            with open(os.path.join(d, "roster_cache", "Dean.json"), encoding="utf-8") as fh:
                saved = json.load(fh)
            self.assertIs(saved["published"], False)
            self.assertNotIn("sections", saved)

    def test_the_fetch_loop_stamps_its_tick_and_stays_off_the_beacon(self):
        with open(APP, encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count("target=_roster_fetch_loop"), 1)
        fetch = src.split("def _roster_fetch_once(", 1)[1].split("def _roster_fetch_loop", 1)[0]
        self.assertIn("_beacon_suppressed_by()", fetch,
                      "REG-2203 (#99): a suppressed console (CI, harness, scratch) must not fetch the live site every 5 min — the same guard _roster_publish_once keeps")
        self.assertEqual(fetch.count("write_cache("), 1)
        self.assertEqual(fetch.count("cache_views("), 1)
        self.assertEqual(fetch.count("if views is None:"), 1)
        self.assertNotIn("view_of(got.get", fetch)
        self.assertNotIn("char_select", fetch)
        loop = src.split("def _roster_fetch_loop(", 1)[1].split("def _console_beacon_loop", 1)[0]
        self.assertEqual(loop.count('_lane_tick("_roster_fetch_loop", 300)'), 1)
        beacon = src.split("def _console_beacon(", 1)[1].split("def _console_beacon_async", 1)[0]
        self.assertNotIn("_roster_fetch_once", beacon)

    def test_the_roster_panel_is_not_a_tenth_header_door(self):
        ui_path = os.path.join(HERE, "control_ui.html")
        with open(ui_path, encoding="utf-8") as fh:
            ui = fh.read()
        start = ui.index('<nav class="head-tabs" id="head-tabs">')
        nav = ui[start:ui.index("</nav>", start)]
        self.assertEqual(nav.count("<button"), 10)
        self.assertNotIn('data-tab="roster"', nav)
        self.assertEqual(nav.count('data-tab="d2jsp"'), 1)
        self.assertIn('id="roster-box" hidden', ui)
        open_at = ui.index('id="roster-open"')
        box_at = ui.index('id="roster-box"')
        list_at = ui.index('id="fleet-list"')
        self.assertLess(open_at, box_at)
        self.assertLess(box_at, list_at)
        rule_at = ui.index(".roster-box {")
        rule = ui[rule_at:ui.index("}", rule_at)]
        self.assertIn("max-height:", rule)
        self.assertIn("overflow-y: auto", rule)
        self.assertIn("background: #0a0908", rule)
        self.assertIn("overscroll-behavior: contain", rule)
        hide_at = ui.index(".roster-box[hidden]")
        hide = ui[hide_at:ui.index("}", hide_at)]
        self.assertIn("display: none !important", hide)
        fn = ui[ui.index("window._rosterOpen = function"):ui.index("(function _fleetKick")]
        self.assertIn("document.body.appendChild(node)", fn)
        self.assertIn("position = 'fixed'", fn)
        self.assertIn("zIndex = '40'", fn)
        self.assertIn("scrollTop", fn)
        self.assertNotIn("scrollIntoView(", fn)
        self.assertIn("window._rosterOpen", ui)
        self.assertIn("/api/roster-cache", ui)
        self.assertIn("tvd-shadow", fn)
        self.assertIn("_shellSizePane", fn)
        self.assertIn("read only", fn)
        self.assertIn('id="shadow-bar"', ui)
        self.assertNotIn('class="ht" type="button" id="shadow-leave"', ui)
        board = open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8").read()
        self.assertEqual(board.count("data.type !== 'tvd-shadow'"), 1)
        self.assertIn("if (on) { shadowMap[k] = v == null ? null : String(v); return; }", board)
        self.assertIn("d2r_charBuilds: builds.length ? storeOf(builds) : '{}'", board)
        self.assertIn("switchTab('chars')", board)
        self.assertIn("window._LP_FORKED.has(k)", board)
        # v3856 - the shadow's Characters tab draws their worn gear from their upload (the shim's chars_learned)
        self.assertNotIn("their reels stay on their console, so in-game characters are not read here", board)
        # REG-3049 - each shadow guard by its own line, never a running total: the total went 2 -> 3 with the reels refusal
        # (9daa388fe), and REG-3009's read-only guard (v3839) made it 4, red as "4 != 3", a number that named nothing.
        for site in ("    if (document.documentElement.classList.contains('tvd-shadow')) return _cbLearnedQuiet(then);\n",
                     "    if (document.documentElement.classList.contains('tvd-shadow')) return { ok: false, why: "
                     "'their reels stay on their console' };\n",
                     "  try { return document.documentElement.classList.contains('tvd-shadow'); } catch (e) { return false; }\n"):
            self.assertEqual(board.count(site), 1, "a shadow guard in the board went missing or doubled: %r" % site.strip())
        self.assertIn("shadowMap[k] = null", board)
        # A missing snapshot used to post pending:true into THIS browser's board, which is the claim trap.
        # The visit now opens their frame and never arms this board.
        enter = ui[ui.index("  window._shadowEnter = function (owner) {"):ui.index("  window._shadowLeave = function () {")]
        self.assertNotIn("pending: true", enter)
        self.assertNotIn("getElementById('tvd-eng')", enter)
        self.assertIn("window._shadowSnapEnter", enter)
        self.assertIn("window._shadowRosterStores", enter)
        self.assertEqual(board.count("if (on) { shadowMap[k] = v == null ? null : String(v); return; }"), 1)
        with open(APP, encoding="utf-8") as fh:
            app = fh.read()
        self.assertEqual(app.count('path == "/api/roster-cache"'), 1)
        self.assertIn("roster_html(", app)
        missing = RP.roster_html({"ok": True, "fetched": False, "owners": []})
        self.assertIn("has not fetched a roster yet", missing)
        self.assertNotIn("has not published", missing)
        now = 5_000_000
        quiet = {"owner": "Dean", "published": False}
        page = RP.roster_html({"ok": True, "fetched": True, "now": now, "owners": [quiet]})
        self.assertIn("Dean has not published its vault yet", page)
        self.assertNotIn("<ul></ul>", page)
        nasty = {"name": "<script>alert(1)</script>", "looks": "http://x/a.png"}
        shown = {"owner": OWNER, "published": True, "corrupt": False, "t": now,
                 "sections": {"characters": {"asOf": now, "counts": 1, "rows": [nasty]}}}
        safe = RP.roster_html({"ok": True, "fetched": True, "now": now, "owners": [shown]})
        self.assertNotIn("<script>", safe)
        self.assertIn("&lt;script&gt;", safe)
        self.assertNotIn("http://x/a.png", safe)
        self.assertIn("has not published its vault yet", safe)
        old = dict(shown, t=now - 2 * RP.HOUR_MS - 1)
        stale = RP.roster_html({"ok": True, "fetched": True, "now": now, "owners": [old]})
        self.assertIn("roster-stale", stale)
        self.assertIn("<p>roster row stored 2 hr ago</p>", stale)   # REG-3037 - the row's store, named; the class keeps stale
        self.assertIn("as of under 1 min ago", stale)
        self.assertNotIn("under 1 min ago stale", stale)
        self.assertNotIn(" stale", safe)
        old_vault = {"owner": OWNER, "published": True, "corrupt": False, "t": now,
                     "sections": {"vault": {"asOf": now - 2 * RP.HOUR_MS - 1, "counts": 2, "rows": []}}}
        vault_old = RP.roster_html({"ok": True, "fetched": True, "now": now, "owners": [old_vault]})
        self.assertIn("as of 2 hr ago stale", vault_old)
        self.assertIn("roster row stored under 1 min ago", vault_old)
        self.assertNotIn("roster row stored under 1 min ago stale", vault_old)
        self.assertNotIn("0 min", vault_old)
        unknown = {"owner": OWNER, "published": True, "corrupt": False,
                   "sections": {"characters": {"counts": 1, "rows": [{"name": "Sorceress"}]}}}
        plain = RP.roster_html({"ok": True, "fetched": True, "now": now, "owners": [unknown]})
        self.assertIn("age unknown", plain)
        self.assertNotIn("0 min", plain)
        self.assertNotIn(" stale", plain)
        bad = {"owner": "Dean", "published": True, "corrupt": True,
               "sections": {"stash": {"asOf": now, "rows": [{"name": "Shako"}]}}}
        hidden = RP.roster_html({"ok": True, "fetched": True, "now": now, "owners": [bad]})
        self.assertIn("rows are not shown", hidden)
        self.assertNotIn("Shako", hidden)
        tall = {"owner": "Dean", "published": True, "corrupt": False, "t": now,
                "sections": {
                    "characters": {"asOf": now, "counts": 1, "rows": [{"name": "Sorceress", "level": 87}]},
                    "chronicle": {"asOf": now, "counts": {"sets": {"have": 12, "total": 40},
                                                         "uniques": {"have": 3}}},
                    "reels": {"asOf": now, "counts": {"reels": 4},
                              "rows": [{"station": "TRAVEL", "date": now}]},
                    "stash": {"asOf": now, "counts": 1,
                              "rows": [{"name": "Shako", "provenance": "shared"}]},
                }}
        full = RP.roster_html({"ok": True, "fetched": True, "now": now, "owners": [tall]})
        self.assertIn("sets 12/40", full)
        self.assertIn("uniques 3", full)
        self.assertNotIn("uniques 3/0", full)
        self.assertIn("reels 4", full)
        self.assertIn("Sorceress · 87", full)
        self.assertIn("TRAVEL", full)
        self.assertNotIn(str(now), full)
        self.assertIn("shared", full)

    def test_a_published_build_keeps_the_slots_the_board_draws(self):
        book = RP.clean_book({"builds": [{
            "name": "Hammerdin", "cls": "Paladin", "level": 92,
            "sets": [{"name": "Set 1", "slots": {"head": {"name": "Harlequin Crest", "id": "u1"},
                                                 "shot": {"name": "nope.png"}},
                      "inv": [{"name": "Annihilus", "x": 0, "y": 0, "w": 1, "h": 1}]}],
            "stash": [{"name": "Ber Rune", "x": 1, "y": 2, "w": 1, "h": 1}],
        }], "owned": ["Shako"]})
        self.assertEqual(book["owned"], ["Shako"])
        sec = RP.section_of(RP.builds_read(book, 50), 50)
        row = sec["rows"][0]
        self.assertEqual(row["sets"][0]["slots"]["head"]["name"], "Harlequin Crest")
        self.assertNotIn("shot", row["sets"][0]["slots"])
        self.assertEqual(row["stash"][0]["name"], "Ber Rune")
        cells = RP.stash_rows_of(book)
        self.assertEqual(cells[0]["name"], "Ber Rune")
        self.assertEqual(cells[1]["x"], 0)
        self.assertIsNone(RP.clean_book({"builds": [{"name": "x.png"}]}))


class AShadowVisitWritesNothingIntoThisPC(unittest.TestCase):
    """REG-2186 - a visit to another PC's console must leave NOTHING in this PC's store.

    The checks above only grepped the veil's text and pinned its 'tvd-shadow' count - they stayed green with every
    write leaking (the cross-family review of v3678 made isLedger always false and nothing went red). This runs the
    SHIPPED veil (arm / disarm and its window.LSR wrapper, cut from bible.html) in node against a stand-in store and
    writes, during a visit, exactly the keys that leaked: his chronicle inbox trimmed by kaiChronicleSync, the sweep
    stamp _chronAutoAdopt sets, a ledger key, and a removal. After Leave his store must read as it did before."""

    def _cut(self, s, a, b):
        if s.count(a) != 1:
            raise AssertionError("anchor %r matched %d times - re-point this law" % (a[:40], s.count(a)))
        i = s.index(a)
        return s[i:s.index(b, i)]

    def _visit(self):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        board = open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8").read()
        veil = self._cut(board, "  var LEDGER = {\n", "  function buildsFrom(row) {\n")
        prog = r"""
var REAL = { d2r_chronicleInbox: JSON.stringify(['Harlequin Crest', 'Ber Rune']), d2r_chronAdopted: 'before-visit',
             d2r_activeTab: 'vault' };
var window = { _LP_FORKED: new Set(), _WP_FORKED: new Set(),
  LSR: { getItem: function(k){ return Object.prototype.hasOwnProperty.call(REAL, k) ? REAL[k] : null; },
         setItem: function(k, v){ REAL[k] = String(v); },
         removeItem: function(k){ delete REAL[k]; } } };
var document = { documentElement: { classList: { add: function(){}, remove: function(){}, contains: function(){ return false; } } },
                 getElementById: function(){ return null; } };
var paint = function(){};
""" + veil + r"""
arm({ d2r_owned: JSON.stringify(['Harlequin Crest']) });
// what the board's own timers did during a visit:
window.LSR.setItem('d2r_chronicleInbox', JSON.stringify(['Ber Rune']));   // kaiChronicleSync trims his inbox
window.LSR.setItem('d2r_chronAdopted', 'sweep-123');                        // _chronAutoAdopt stamps the sweep done
window.LSR.setItem('d2r_foundLog', JSON.stringify({ x: 1 }));             // a ledger write
window.LSR.removeItem('d2r_activeTab');                                    // a removal
var during = window.LSR.getItem('d2r_chronicleInbox');
disarm();
console.log(JSON.stringify({ real: REAL, during: during }));
"""
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise AssertionError("the cut veil did not run in node: %s" % r.stderr[-700:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_a_visit_leaves_his_inbox_alone(self):
        out = self._visit()
        self.assertEqual(json.loads(out["real"]["d2r_chronicleInbox"]), ["Harlequin Crest", "Ber Rune"],
                         "a visit trimmed his chronicle inbox - a find he had not ticked is gone for good")

    def test_a_sweep_during_a_visit_is_not_marked_done(self):
        out = self._visit()
        self.assertEqual(out["real"]["d2r_chronAdopted"], "before-visit",
                         "a sweep that landed during a visit was stamped done for real - it will never be applied")

    def test_no_key_of_his_is_written_or_removed(self):
        out = self._visit()
        self.assertNotIn("d2r_foundLog", out["real"], "a ledger write during the visit reached his store")
        self.assertEqual(out["real"].get("d2r_activeTab"), "vault", "a removal during the visit reached his store")

    def test_the_visit_still_reads_back_what_it_wrote(self):
        # the veil must keep the visit consistent: a key written during it reads back from the shadow map
        out = self._visit()
        self.assertEqual(json.loads(out["during"]), ["Ber Rune"], "the visit could not read back its own write")

    def test_the_roster_book_door_is_origin_gated(self):
        """REG-2199 (#116) — do_POST parses the body as JSON whatever the Content-Type, so without an
        origin gate a no-cors text/plain POST from any tab in his browser replaces roster_book.json
        and publishes his builds + stash cells under his name (the roster Basic credential is in this
        PUBLIC repo). /api/roster-book must pass the SAME console_may_post gate as the d2jsp doors,
        BEFORE it takes the body."""
        src = open(APP, encoding="utf-8").read()
        i = src.index('if path == "/api/roster-book":')
        door = src[i:src.index('if path == "/api/', i + 30)]
        self.assertIn("console_may_post(", door,
                      "/api/roster-book takes the body with no origin gate — a cross-site POST publishes under his name (#116)")
        self.assertLess(door.index("console_may_post("), door.index("_roster_book_take("),
                        "the origin gate must run BEFORE the body is taken (#116)")

    def test_a_banked_board_tally_without_ok_still_publishes(self):
        """REG-2200 (#94) — a banked board_tally.json carries the owner's sets/uniques/runewords with
        NO 'ok' key (board_tally_merge never writes one), so requiring ok:true meant chronicle_read
        returned None for every PC and no chronicle ever reached the roster. A tally with real counts
        publishes; only an explicit ok:False (a failed read, no counts) is refused."""
        board = {"sets": {"have": 117, "total": 135}, "uniques": {"have": 266, "total": 403},
                 "runewords": {"have": 40, "total": 99}, "ownerId": "abc", "at": 1790000000000}
        got = RP.chronicle_read(board, 1790000000001)
        self.assertIsNotNone(got, "a banked board_tally with no 'ok' did not publish — no PC's chronicle reaches the roster (#94)")
        self.assertEqual(got["counts"]["sets"], {"have": 117, "total": 135})
        self.assertIsNone(RP.chronicle_read({"ok": False, "why": "not read"}, 1000),
                          "a failed read (ok:False, no counts) must still be refused")

    def test_found_names_ride_the_same_chronicle_section_and_an_empty_lane_does_not(self):
        """The found-item names travel on the roster chronicle section. An empty lane is not a row.

        A failed read stays None even when a list was handed in. A list that does not fit the
        row cap is dropped and the counts stay, so the publish itself is not refused.
        """
        now = 1790000000001
        board = {"sets": {"have": 132, "total": 135}, "uniques": {"have": 52, "total": 403},
                 "runewords": {"have": 98, "total": 99}, "at": 1790000000000}
        got = RP.chronicle_read(board, now, {
            "uniques": ["Shako", "Shako", ""],
            "sets": [],
            "runewords": ["Enigma"],
        })
        sec = RP.sections_from({"chronicle": got}, now)["chronicle"]
        self.assertEqual(sec["rows"], [
            {"lane": "uniques", "name": "Shako"},
            {"lane": "runewords", "name": "Enigma"},
        ])
        self.assertEqual(sec["counts"]["sets"], {"have": 132, "total": 135})
        self.assertNotIn("sets", [row["lane"] for row in sec["rows"]])
        zero = RP.chronicle_read(
            {"uniques": {"have": 0, "total": 403}, "at": 1790000000000}, now, None)
        self.assertEqual(zero["counts"]["uniques"], {"have": 0, "total": 403})
        self.assertNotIn("rows", zero)
        self.assertIsNone(RP.chronicle_read({"ok": False, "why": "not read"}, 1000, {"uniques": ["Shako"]}))
        wide = RP.chronicle_read(board, now, {"uniques": ["Name %d" % i for i in range(40)]})
        packed = RP.sections_from({"chronicle": wide}, now)
        shrunk = RP.chronicle_within(packed, limit=80)
        self.assertNotIn("rows", shrunk["chronicle"])
        self.assertEqual(shrunk["chronicle"]["counts"]["runewords"], {"have": 98, "total": 99})
        self.assertIn("rows", RP.chronicle_within(packed, limit=60000)["chronicle"])

    def test_a_future_timestamp_is_unknown_not_fresh(self):
        """REG-2201 (#99) — a reading stamped AHEAD of now (clock skew) scored `now - as_of` negative,
        so _age_state read 'current' and _ago 'under 1 min ago'. A future clock is unknown, never
        fresh; minor skew (under a minute) is still current."""
        now = 1790000000000
        self.assertEqual(RP._age_state(now + 120000, now), "unknown", "a 2-min-future clock read as fresh (#99)")
        self.assertEqual(RP._ago(now + 120000, now), ("unknown", None), "_ago called a future clock 'under 1 min ago' (#99)")
        self.assertEqual(RP._age_state(now + 30000, now), "current", "a 30-s skew should still be current")
        self.assertEqual(RP._age_state(now - 300000, now), "current")
        self.assertEqual(RP._age_state(now - 3 * 3600 * 1000, now), "stale")

RED_PROOF = [
    {"why": "REG-2205 (#99): reels_read counts stations over EVERY stamp again, so a gone reel's lingering river stamp is counted as a live station",
     "file": "roster_publish.py",
     "find": "        for reel in named:\n",
     "replace": "        for reel in list(stamps):\n",
     "matches": 1},
    {"why": "REG-2204 (#99): the beacon's tally shaper drops its non-number guard, so an item name (NaN) crosses the counts-only boundary instead of being nulled",
     "file": "functions/api/console.js",
     "find": "        if (!Number.isFinite(have) || have < 0) return null;\n",
     "replace": "        if (have < 0) return null;\n",
     "matches": 1},
    {"why": "REG-2203 (#99): _roster_fetch_once drops its beacon-suppression guard, so a suppressed console (CI, harness, scratch) fetches the live site every 5 min",
     "file": "control_app.py",
     "find": "    held = _beacon_suppressed_by()\n    if held:\n        _roster_fetch_remember(\"suppressed: \" + str(held)[:160])\n        return\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2201 (#99): _age_state drops its future-clock check, so a reading stamped ahead of now reads 'current' / 'under 1 min ago' again",
     "file": "roster_publish.py",
     "find": "    if as_of - now_ms > 60000:\n        return \"unknown\"\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2200 (#94): chronicle_read requires ok:true again, so a banked board_tally (no 'ok') never publishes — no PC's chronicle reaches the roster",
     "file": "roster_publish.py",
     "find": "    if not isinstance(tally, dict) or tally.get(\"ok\") is False:\n",
     "replace": "    if not isinstance(tally, dict) or tally.get(\"ok\") is not True:\n",
     "matches": 1},
    {"why": "REG-2199 (#116): the roster-book door drops its origin gate, so a cross-site no-cors POST publishes his builds and stash cells under his name again",
     "file": "control_app.py",
     "find": "            import d2jsp_chrome as _d2jsp\n            if not _d2jsp.console_may_post(\n                    self.headers.get(\"Origin\"), self.headers.get(\"Host\"), CONTROL_PORT,\n                    self.headers.get(\"Sec-Fetch-Site\")):\n                self._json(403, {\"ok\": False, \"reason\": \"local\"})\n                return\n            if isinstance(body, dict) and body.get(\"kind\") == \"profile\":\n",
     "replace": "            if isinstance(body, dict) and body.get(\"kind\") == \"profile\":\n",
     "matches": 1},
    {
        "why": "REG-2166 - an unread section is stored as an empty list",
        "file": "roster_publish.py",
        "find": "    if not isinstance(raw, dict) or raw.get(\"read\") is not True:\n        return None\n",
        "replace": "    if not isinstance(raw, dict) or raw.get(\"read\") is not True:\n        return {\"counts\": 0, \"rows\": []}\n",
        "matches": 1,
    },
    {
        "why": "REG-2166 - the roster key becomes a hostname",
        "file": "roster_publish.py",
        "find": "    return \"roster:\" + owner\n",
        "replace": "    return \"roster:\" + \"hostname\"\n",
        "matches": 1,
    },
    {
        "why": "REG-2166 - the worker keys the row by the machine field",
        "file": "functions/api/roster.js",
        "find": "  const key = \"roster:\" + owner;\n",
        "replace": "  const key = \"roster:\" + String(body.machine || owner);\n",
        "matches": 1,
    },
    {
        "why": "REG-2166 - over the daily cap the worker answers 500",
        "file": "functions/api/roster.js",
        "find": "    return json({ ok: false, why: QUOTA_WHY, hint: REFUSAL_HINT }, 200);\n",
        "replace": "    return json({ ok: false, why: QUOTA_WHY, hint: REFUSAL_HINT }, 500);\n",
        "matches": 1,
    },
    {
        "why": "REG-2168 - a mac named Konyo is left with no roster label",
        "file": "roster_publish.py",
        "find": "    if name == \"Konyo\" and platform == \"mac\":\n        return \"Konyo · Mac\"\n",
        "replace": "    return None\n    if name == \"Konyo\" and platform == \"mac\":\n        return \"Konyo · Mac\"\n",
        "matches": 1,
    },
    {
        "why": "REG-2168 - the console asks for the nickname and drops the platform",
        "file": "control_app.py",
        "find": "    owner = _rp.owner_of(_roster_claimed_name(), _roster_platform())\n",
        "replace": "    owner = _rp.owner_of(_roster_claimed_name())\n",
        "matches": 1,
    },
    {
        "why": "REG-2169 - a hash mismatch is shown as that PC's rows",
        "file": "functions/api/roster.js",
        "find": "      owners.push({ owner: owner, published: true, corrupt: true, t: prev.t });\n",
        "replace": "      owners.push({ owner: owner, published: true, corrupt: false, t: prev.t, hash: prev.hash, sections: sections });\n",
        "matches": 1,
    },
    {
        "why": "REG-2169 - a PC that never published is stored as an empty section list",
        "file": "functions/api/roster.js",
        "find": "      owners.push({ owner: owner, published: false });\n",
        "replace": "      owners.push({ owner: owner, published: false, sections: [] });\n",
        "matches": 1,
    },
    {
        "why": "REG-2169 - the viewer keeps sections whose hash does not match",
        "file": "roster_publish.py",
        "find": "    if row.get(\"hash\") != digest:\n        return {\"owner\": owner, \"published\": True, \"corrupt\": True}\n",
        "replace": "    if False and row.get(\"hash\") != digest:\n        return {\"owner\": owner, \"published\": True, \"corrupt\": True}\n",
        "matches": 1,
    },
    {
        "why": "REG-2169 - the fetch loop stops stamping its tick",
        "file": "control_app.py",
        "find": "        _lane_tick(\"_roster_fetch_loop\", 300)\n",
        "replace": "        _lane_tick(\"_roster_publish_loop\", 300)\n",
        "matches": 1,
    },
    {
        "why": "REG-2169 - a success with no owners list replaces the cache",
        "file": "roster_publish.py",
        "find": "    if not isinstance(owners, list):\n        return None\n",
        "replace": "    if not isinstance(owners, list):\n        return view_of(None, now_ms)\n",
        "matches": 1,
    },
    {
        "why": "REG-2171 - a missing fetch is drawn as five empty rosters",
        "file": "roster_publish.py",
        "find": "    if not isinstance(payload, dict) or payload.get(\"fetched\") is not True:\n        return '<div class=\"roster-none\">this PC has not fetched a roster yet</div>'\n",
        "replace": "    if False and (not isinstance(payload, dict) or payload.get(\"fetched\") is not True):\n        return '<div class=\"roster-none\">this PC has not fetched a roster yet</div>'\n",
        "matches": 1,
    },
    {
        "why": "REG-2171 - a corrupt roster still shows its rows",
        "file": "roster_publish.py",
        "find": "        if row.get(\"corrupt\") is True:\n",
        "replace": "        if False and row.get(\"corrupt\") is True:\n",
        "matches": 1,
    },
    {
        "why": "REG-2171 - a row name is written into the page without escaping",
        "file": "roster_publish.py",
        "find": "                items.append(\"<li>%s</li>\" % html.escape(line, quote=True))\n",
        "replace": "                items.append(\"<li>%s</li>\" % line)\n",
        "matches": 1,
    },
    {
        "why": "REG-2172 - a chronicle tally is dropped because it is not one integer",
        "file": "roster_publish.py",
        "find": "    if not isinstance(counts, dict) or not counts:\n        return None\n",
        "replace": "    return None\n    if not isinstance(counts, dict) or not counts:\n        return None\n",
        "matches": 1,
    },
    {
        "why": "REG-2172 - a reel date is printed as a raw millisecond count",
        "file": "roster_publish.py",
        "find": "        if key == \"date\":\n",
        "replace": "        if False and key == \"date\":\n",
        "matches": 1,
    },
    {
        "why": "REG-2178 - the roster panel grows the rail instead of scrolling inside itself",
        "file": "control_ui.html",
        "find": " max-height: min(420px, 46vh); overflow-y: auto;",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-2178 - a stale roster age loses the word",
        "file": "roster_publish.py",
        "find": "    if state == \"stale\":\n        return words + \" stale\"\n",
        "replace": "    if state == \"stale\":\n        return words\n",
        "matches": 1,
    },
    {
        "why": "REG-2179 - the roster stays in the rail and opens under the shelf",
        "file": "control_ui.html",
        "find": "        if (node.parentNode !== document.body) document.body.appendChild(node);\n",
        "replace": "        /* the card stays in the rail */\n",
        "matches": 1,
    },
    {"why": "REG-2186: the veil catches only ledger keys again, so a visit writes his inbox and the sweep stamp into his store",
     "file": "bible.html",
     "find": "        if (on) { shadowMap[k] = v == null ? null : String(v); return; }\n",
     "replace": "        if (on && isLedger(k)) { shadowMap[k] = v == null ? null : String(v); return; }\n",
     "matches": 1},
    {"why": "REG-2186: a removal during a visit reaches his store again for any key that is not a ledger key",
     "file": "bible.html",
     "find": "        if (on) { shadowMap[k] = null; return; }\n",
     "replace": "        if (on && isLedger(k)) { shadowMap[k] = null; return; }\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
