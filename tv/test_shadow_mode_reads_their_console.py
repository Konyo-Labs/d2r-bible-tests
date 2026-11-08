# -*- coding: utf-8 -*-
"""Shadow mode - another console, one to one and read only, live or from its last upload.

Shadow on main drew another PC from its roster row, and that row strips every build to name/x/y/w/h: no
mods, no mule names, no vault. Now each console uploads its account stores themselves (the board's
_collectProgress export, cleaned by tv/console_snapshot.py), signed with the key its roster publish
registered, on the roster publish (functions/api/roster.js, roster:<owner>:profile). A viewer's console fetches that record (or its own last copy
when the site cannot be read) and boots the same board on it in a frame whose storage lives in memory.

Proved here, without a browser:
  * what leaves a PC: d2r_ stores only, history/evidence/debug stores and the board's own d2r_api_ names
    stay home, paths/install ids/pictures are blanked, an untouched store leaves byte for byte, and the
    size caps drop the largest stores first and name them
  * when: change-only, MIN_GAP_MS apart, one boot post, a refusal waits; the KV budget stays under 1000
  * the worker, run in node as it ships: an owner with no registered roster key, an unsigned upload,
    another key, a hash that does not match, a picture, an oversize body and the daily cap are refused
    with nothing stored; a signed upload is stored and read back byte for byte; GET never writes and
    serves a record that fails its own hash as corrupt, never as stores
  * the viewer's words: live / offline / online UNKNOWN, always with the upload's age, and the PC's
    own last copy (with its time) when the site cannot be read - shadow works with the owner offline
  * the console's doors: /api/roster-cache?profile= and /api/roster-book {kind: profile}, the roster lane, and the
    console panel's _shadowOpen falling back to the roster row when no upload exists
  * the shadow frame's boot block: memory storage, fail closed, no /api/ and no non-GET request,
    theirs-not-ours console answers, and the click/key veil - run in node on the page's own script

The headless-Chrome one-to-one proof (board A vs shadow of A's snapshot) is
tv/test_shadow_mode_draws_their_console.py.
"""
import base64
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
from console_safe import enable as _enable  # noqa: E402
_enable()
import console_snapshot as CS  # noqa: E402
import roster_publish as RP  # noqa: E402
import roster_sign as RS  # noqa: E402

NODE = shutil.which("node")
SNAPSHOT_JS = os.path.join(ROOT, "functions", "api", "roster.js")   # the profile half of the roster route
APP = os.path.join(HERE, "control_app.py")
UI = os.path.join(HERE, "control_ui.html")
BIBLE = os.path.join(ROOT, "bible.html")
OWNER = "Dean"
T0 = 1792800000000


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _stores():
    build = {"bx1": {"name": "Deansorc", "cls": "Sorceress", "level": 90, "active": 0, "sets": [{"name": "Set 1",
             "slots": {"tors": {"id": "r33", "name": "Enigma", "q": "r", "base": "aar", "rolls": {"p1": 761}}},
             "inv": [{"id": "u381", "name": "Annihilus", "rolls": {"p2": 17, "p3": 13, "p4": 7}, "x": 0, "y": 0}]}],
             "stash": [{"id": "r47", "name": "Grief", "rolls": {"p2": 371}}], "shared": []}}
    return {"d2r_charBuilds": json.dumps(build, separators=(",", ":")),
            "d2r_muleRoster": json.dumps([{"id": "fx-a", "name": "DEAN-MULE-1"}]),
            "d2r_muleAssign": json.dumps({"Harlequin Crest": "fx-a"}),
            "d2r_owned": json.dumps(["Harlequin Crest"]),
            "d2r_magicFinds": json.dumps({"Bone Eye": {"q": "rare", "mods": ["+22 to Life"]}})}


WORLD = {"machine": "windows", "profile": "main", "os": "WINDOWS", "ledger": "", "cousin": True}


def _wstores():
    """The stores as the console uploads them: the board's, plus the world they were drawn in."""
    return dict(_stores(), d2r_api_world=json.dumps(WORLD, separators=(",", ":"), sort_keys=True))


def _record(owner=OWNER, stores=None, t=T0, **extra):
    stores = _stores() if stores is None else stores
    rec = {"owner": owner, "t": t, "hash": CS.digest(stores), "stores": stores}
    rec.update(extra)
    return rec


# a home path built at run time: the repo is public and its law counts literal /Users/<name>/ paths
HOME_ = "/" + "Users/"

class WhatLeavesThePC(unittest.TestCase):

    def test_account_stores_leave_byte_for_byte(self):
        s = _stores()
        got = CS.clean({"stores": s})
        self.assertEqual(got["stores"], s, "an account store was changed on its way out")
        self.assertEqual(got["dropped"], [])

    def test_history_evidence_identity_and_debug_stores_stay_home(self):
        s = _stores()
        home = {"d2r_tvdHist": "[]", "d2r_foundEvidence": "{}", "d2r_installId": "x", "d2r_ownerClaim": "*",
                "d2r_quarantine_x": "{}", "d2r_d2jsp_draft": "{}", "d2r_api_chars_learned": "{}",
                "d2r_sessionLog": "[]", "notd2r": "1", "d2r_bad-name": "1"}
        s2 = dict(s, **home)
        s2["d2r_notAString"] = 5
        got = CS.clean({"stores": s2})
        self.assertEqual(sorted(got["stores"]), sorted(s), "a store that must stay home left the PC")
        for k in list(home) + ["d2r_notAString"]:
            self.assertIn(k[:60], got["dropped"], "a dropped store was not named: %s" % k)

    def test_paths_install_ids_and_pictures_are_blanked(self):
        dirty = {"a": HOME_ + "someone/Library/x.png", "b": "C:\\Users\\player\\Documents\\x.d2s",
                 "c": "0123456789ab4def8123456789abcdef", "hash": "0123456789abcdef0123456789abcdef", "d": "data:image/png;base64,AAAA", "keep": "Enigma"}
        got = CS.clean({"stores": {"d2r_x": json.dumps(dirty)}})["stores"]["d2r_x"]
        for bad in ("/Users/", "Users\\", "0123456789ab4def8123456789abcdef", "data:image"):
            self.assertNotIn(bad, got)
        self.assertEqual(json.loads(got)["keep"], "Enigma")
        self.assertEqual(json.loads(got)["hash"], "0123456789abcdef0123456789abcdef",
                         "a 32-hex hash that is not an install id's shape was blanked")
        for secret in ("ghp_" + "A" * 30, "github_pat_" + "B" * 30, "Some-MacBook-Pro.local",
                       "01234567-89ab-4def-8123-456789abcdef"):
            self.assertNotIn(secret, CS.clean({"stores": {"d2r_x": json.dumps({"v": "x " + secret})}})["stores"]["d2r_x"])

    def test_the_size_caps_drop_the_largest_first_and_say_so(self):
        s = _stores()
        s["d2r_huge"] = json.dumps(["x" * (CS.MAX_STORE + 10)])
        s["d2r_big1"] = json.dumps(["y" * (CS.MAX_STORE - 100)])
        s["d2r_big2"] = json.dumps(["z" * (CS.MAX_STORE - 200)])
        s["d2r_big3"] = json.dumps(["w" * (CS.MAX_STORE - 300)])
        got = CS.clean({"stores": s})
        self.assertIn("d2r_huge", got["dropped"])
        self.assertIn("d2r_big1", got["dropped"], "the largest store was not the first to go over the total")
        self.assertLessEqual(sum(len(k) + len(v) for k, v in got["stores"].items()), CS.MAX_TOTAL)
        for k in _stores():
            self.assertIn(k, got["stores"], "a small account store was dropped before a big one")

    def test_the_board_may_not_post_console_answers_but_the_console_adds_them(self):
        self.assertFalse(CS.allowed_key("d2r_api_chars_learned"))
        self.assertTrue(CS.allowed_key("d2r_api_chars_learned", board=False))
        self.assertFalse(CS.allowed_key("d2r_api_status", board=False))
        got = CS.with_api(_stores(), {"chars_learned": {"ok": True, "chars": [{"name": "Deansorc"}],
                                                        "status": {"tick": 9}, "generatedTs": 5},
                                      "main_locks": {"ok": True, "locked": [], "generatedTs": 7}})
        cl = json.loads(got["d2r_api_chars_learned"])
        self.assertEqual(cl["chars"], [{"name": "Deansorc"}])
        self.assertNotIn("status", cl, "a ticking field rides the snapshot and makes every upload 'changed'")
        self.assertNotIn("generatedTs", json.loads(got["d2r_api_main_locks"]))

    def test_the_world_rides_with_closed_values_only(self):
        w = {"machine": "windows", "profile": "ladder", "os": "WINDOWS", "ledger": "Dean ledger", "cousin": True}
        self.assertEqual(CS.world_of(w), w)
        for bad in (dict(w, machine="linux"), dict(w, profile="hc"), dict(w, os="BeOS"), dict(w, cousin=1),
                    {k: v for k, v in w.items() if k != "os"}):
            self.assertIsNone(CS.world_of(bad), bad)
        for odd in ("<img>", "x" * 41, None):
            self.assertEqual(CS.world_of(dict(w, ledger=odd)), dict(w, ledger=""),
                             "a ledger name it cannot carry lost the whole world")
        got = CS.with_api(_stores(), {"world": dict(w, extra="/Users/x")})
        self.assertEqual(json.loads(got["d2r_api_world"]), w)
        self.assertNotIn("d2r_api_world", CS.with_api(_stores(), {"world": dict(w, os="BeOS")}))
        self.assertFalse(CS.allowed_key("d2r_api_world"), "a board post may not name its own world store")

    def test_the_kv_budget_stays_under_the_ceiling(self):
        b = CS.budget()
        self.assertLessEqual(b["together"], b["ceiling"])
        # v3862 - Workers Paid: six PCs, the frames door counted too, under the fleet's own 10,000-a-day ceiling
        self.assertEqual(b["profile"], RP.budget()["pcs"] * CS.DAY_CAP)
        self.assertEqual(b["frames"], RP.budget()["pcs"] * CS.FRAMES_DAY_CAP)
        self.assertEqual(b["worst"], RP.budget()["presence"]
                         + len(CS.OWNERS) * (RP.DAY_CAP + CS.DAY_CAP + CS.FRAMES_DAY_CAP))
        _js = io.open(os.path.join(os.path.dirname(HERE), "functions", "api", "roster.js"), encoding="utf-8").read()
        for _name, _v in (("PROFILE_DAY_CAP", CS.DAY_CAP), ("FRAMES_DAY_CAP", CS.FRAMES_DAY_CAP)):
            self.assertIn("const %s = %d;" % (_name, _v), _js, "the console counts a %s the worker does not hold" % _name)
        self.assertLessEqual(b["worst"], b["ceiling"], "every owner label at both caps runs past the KV ceiling")
        self.assertGreaterEqual(CS.MIN_GAP_MS, 24 * 3600 * 1000 // CS.DAY_CAP,
                                "the console's pace would run into the worker's daily cap")


class TheShadowNamesWhatItWasNotSent(unittest.TestCase):
    """#210 (GrokBot, 2026-10-27) - a store the owner's PC could not send (too big, or carrying something private) is
    MISSING from the shadow, and nothing said which. A store kept home on purpose (DENY) is not missing."""

    def _clean(self):
        s = _stores()
        s["d2r_huge"] = json.dumps(["x" * (CS.MAX_STORE + 10)])
        s["d2r_tvdHist"] = json.dumps([{"t": 1}])
        return CS.clean({"stores": s})

    def test_too_big_is_unsent_and_kept_home_is_not(self):
        got = self._clean()
        self.assertEqual(got["unsent"], ["d2r_huge"], "the shadow cannot say what it is missing: %r" % got)
        self.assertIn("d2r_tvdHist", got["dropped"], "PREMISE: the history log is no longer kept home")

    def test_the_upload_carries_it_and_the_banner_names_it(self):
        got = self._clean()
        body, why = CS.due({}, OWNER, got["stores"], T0, True, unsent=got["unsent"])
        self.assertEqual(why, "post")
        self.assertEqual(body["unsent"], ["d2r_huge"], "the upload did not carry what it left out")
        self.assertNotIn("unsent", CS.due({}, OWNER, got["stores"], T0, True)[0], "an unknown list was sent as empty")
        v = CS.view(OWNER, _record(unsent=["d2r_huge"]), T0 + 60000, online=True)
        self.assertEqual(v["unsent"], ["d2r_huge"])
        self.assertIn("not sent (too big or private): d2r_huge", v["words"], "the banner does not say what is missing")
        old = CS.view(OWNER, _record(), T0 + 60000, online=True)
        self.assertIsNone(old["unsent"], "an upload from before the list read as 'everything was sent'")
        self.assertNotIn("not sent", old["words"])

    def test_this_pcs_last_copy_keeps_it(self):
        d = tempfile.mkdtemp(prefix="tvd_unsent_cache_")
        self.addCleanup(shutil.rmtree, d, True)
        self.assertTrue(CS.write_cache(d, _record(unsent=["d2r_huge"])))
        self.assertEqual(CS.read_cache(d, OWNER).get("unsent"), ["d2r_huge"], "the last copy lost what was not sent")


class WhenItUploads(unittest.TestCase):

    def test_change_only_gap_boot_and_refusal(self):
        s = _stores()
        body, why = CS.due({}, OWNER, s, T0, boot=False)
        self.assertEqual(why, "post")
        self.assertEqual(body["hash"], CS.digest(s))
        self.assertIsNone(CS.due({}, "Somebody", s, T0, False)[0])
        self.assertIsNone(CS.due({}, OWNER, {}, T0, False)[0])
        st = {"hash": CS.digest(s), "at": T0}
        self.assertEqual(CS.due(st, OWNER, s, T0 + 4 * CS.MIN_GAP_MS, False), (None, "unchanged"))
        # v3857 item 23 - past STALE_MS an unchanged board re-posts (the site may have lost the last one)
        self.assertLess(4 * CS.MIN_GAP_MS, CS.STALE_MS)
        self.assertEqual(CS.due(st, OWNER, s, T0 + CS.STALE_MS + 1, False)[1], "post")
        s2 = dict(s, d2r_owned=json.dumps(["Harlequin Crest", "Enigma"]))
        self.assertIsNone(CS.due(st, OWNER, s2, T0 + CS.MIN_GAP_MS - 1, False)[0])
        self.assertIsNotNone(CS.due(st, OWNER, s2, T0 + CS.MIN_GAP_MS, False)[0])
        # the quota (2026-10-27): every restart's boot post skipped the gap and the ALT spent the site's 20 uploads a day,
        # so the upload with its character list was refused. A boot inside the gap waits like any tick.
        self.assertEqual(CS.due(st, OWNER, s, T0 + 1, True),
                         (None, "within %d min of the last upload" % (CS.MIN_GAP_MS // 60000)),
                         "a boot inside the gap still posts - every restart spends one of the 20 uploads a day")
        self.assertIsNotNone(CS.due(st, OWNER, s, T0 + CS.MIN_GAP_MS, True)[0], "a boot past the gap was held back")
        self.assertIsNotNone(CS.due({}, OWNER, s, T0, True)[0], "a first boot with nothing uploaded yet was held back")
        refused = {"refuseAt": T0, "why": "quota"}
        self.assertEqual(CS.due(refused, OWNER, s, T0 + 1, True), (None, "quota"))
        self.assertIsNotNone(CS.due(refused, OWNER, s, T0 + CS.MIN_GAP_MS, True)[0])

    def test_the_reply_is_remembered(self):
        s = _stores()
        st = CS.apply_reply({}, s, {"ok": True, "stored": ["profile"]}, T0)
        self.assertEqual((st["hash"], st["at"]), (CS.digest(s), T0))
        st = CS.apply_reply(st, s, {"ok": False, "why": "quota"}, T0 + 5)
        self.assertEqual((st["refuseAt"], st["why"]), (T0 + 5, "quota"))
        st = CS.apply_reply(st, s, {"ok": True, "stored": ["profile"]}, T0 + 9)
        self.assertNotIn("refuseAt", st)


class WhatTheViewerIsTold(unittest.TestCase):

    def test_live_offline_unknown_always_carry_the_uploads_age(self):
        rec = _record()
        now = T0 + 42 * 60000
        live = CS.view(OWNER, rec, now, online=True)
        off = CS.view(OWNER, rec, now, online=False)
        unk = CS.view(OWNER, rec, now, online=None)
        self.assertEqual((live["state"], off["state"], unk["state"]), ("live", "offline", "unknown"))
        self.assertEqual(live["words"], "Dean · online now · board uploaded 42 min ago")
        self.assertEqual(off["words"], "Dean · offline · board uploaded 42 min ago")
        self.assertEqual(unk["words"], "Dean · online UNKNOWN · board uploaded 42 min ago")
        for v in (live, off, unk):
            self.assertEqual(v["stores"], rec["stores"], "the viewer was not handed the owner's stores verbatim")
            self.assertEqual(v["t"], T0)

    def test_no_upload_is_said_never_drawn_empty(self):
        v = CS.view(OWNER, None, T0, online=True)
        self.assertFalse(v["ok"])
        self.assertIn("has not uploaded", v["why"])
        self.assertNotIn("stores", v)
        self.assertFalse(CS.view("Somebody", _record(owner="Somebody"), T0)["ok"])

    def test_a_record_that_is_not_theirs_or_fails_its_hash_is_not_shown(self):
        self.assertTrue(CS.record_ok(_record(), OWNER))
        self.assertFalse(CS.record_ok(_record(), "Wife PC"))
        bad = _record()
        bad["stores"] = dict(bad["stores"], d2r_owned='["Shako"]')
        self.assertFalse(CS.record_ok(bad, OWNER), "a record that does not match its own hash was shown")
        self.assertFalse(CS.record_ok(_record(stores=dict(_stores(), d2r_installId="x")), OWNER))
        self.assertFalse(CS.record_ok(_record(t=True), OWNER))

    def test_the_owner_offline_and_the_site_down_still_shows_the_last_copy_with_its_time(self):
        d = tempfile.mkdtemp(prefix="tvd_snap_cache_")
        self.addCleanup(shutil.rmtree, d, True)
        self.assertTrue(CS.write_cache(d, _record(intentVerified=True, keyId="abcdef012345")))
        rec = CS.read_cache(d, OWNER)
        self.assertEqual(rec["stores"], _stores())
        v = CS.view(OWNER, rec, T0 + 3 * 3600 * 1000, online=False, source="cache")
        self.assertTrue(v["ok"])
        self.assertEqual(v["words"], "Dean · offline · board uploaded 3 hr ago · the site could not be read, "
                                     "showing this PC's last copy")
        self.assertEqual(v["t"], T0)
        path = CS.cache_path(d, OWNER)
        with io.open(path, encoding="utf-8") as fh:
            held = json.load(fh)
        held["stores"]["d2r_owned"] = '["planted"]'
        with io.open(path, "w", encoding="utf-8") as fh:
            json.dump(held, fh)
        self.assertIsNone(CS.read_cache(d, OWNER), "a tampered cache was served")

    def test_presence_names_the_owner_or_says_unknown(self):
        mac = {"ok": True, "online": [], "offline": []}
        self.assertIsNone(CS.online_of(OWNER, mac))
        self.assertIsNone(CS.online_of(OWNER, {"ok": False}))
        self.assertIsNone(CS.online_of(OWNER, None))
        nick = next(n for n in ("Dean", "dean", "Dean PC") if RP.owner_of(n, "windows") == OWNER)
        bare = {"nickname": nick, "platform": "windows"}
        self.assertIsNone(CS.online_of(OWNER, {"ok": True, "online": [bare]}))
        fresh = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(time.time() - 40))
        row = {"nickname": nick, "platform": "windows", "t": fresh}
        self.assertTrue(CS.online_of(OWNER, {"ok": True, "online": [row]}))
        self.assertFalse(CS.online_of(OWNER, {"ok": True, "offline": [dict(row)]}))


# The worker, run as it ships, on a fake KV. Each step posts exact bytes with its own headers.
_HARNESS = r"""
import { pathToFileURL } from 'node:url';
import { readFileSync } from 'node:fs';
const CFG = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const bytes = (s) => new Uint8Array(Buffer.from(s || '', 'base64'));
let store = new Map(Object.entries(CFG.seed || {}).map(([k, v]) => [k, typeof v === 'string' ? v : JSON.stringify(v)]));
let puts = [];
const kv = { async get(n) { return store.has(n) ? store.get(n) : null; },
             async put(n, v) { puts.push(n); store.set(n, v); } };
const mod = await import(pathToFileURL(CFG.file).href);
const out = { steps: [], gets: [] };
for (const step of (CFG.steps || [])) {
  if (step.seed) store = new Map(Object.entries(step.seed).map(([k, v]) => [k, typeof v === 'string' ? v : JSON.stringify(v)]));
  puts = [];
  const realNow = Date.now;
  if (typeof step.now === 'number') Date.now = () => step.now;
  if (step.get) {
    const res = await mod.onRequestGet({ request: new Request('https://bull-4-u.com/api/roster?profile=' + encodeURIComponent(step.get)),
                                         env: { TZ_HISTORY: kv } });
    out.steps.push({ get: JSON.parse(await res.text()), puts: puts });
  } else {
    const req = new Request('https://bull-4-u.com/api/roster', { method: 'POST', body: bytes(step.raw),
      headers: Object.assign({ 'content-type': 'application/json' }, step.headers || {}) });
    const res = await mod.onRequestPost({ request: req, env: { TZ_HISTORY: kv } });
    out.steps.push({ reply: JSON.parse(await res.text()), puts: puts });
  }
  Date.now = realNow;
}
out.hash = CFG.hashOf ? mod.hashOfStores(CFG.hashOf) : null;
const rec = {}; for (const [k, v] of store.entries()) { try { rec[k] = JSON.parse(v); } catch (e) { rec[k] = v; } }
out.records = rec;
process.stdout.write(JSON.stringify(out));
"""


def _node(cfg):
    cfg = dict(cfg, file=SNAPSHOT_JS)
    with tempfile.TemporaryDirectory(prefix="tvd_profile_js_") as d:
        h = os.path.join(d, "h.mjs")
        with io.open(h, "w", encoding="utf-8") as fh:
            fh.write(_HARNESS)
        c = os.path.join(d, "cfg.json")
        with io.open(c, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh)
        r = subprocess.run([NODE, h, c], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=240)
    if r.returncode != 0:
        raise AssertionError("the snapshot harness failed rc=%s\n%s" % (r.returncode, r.stderr[-2000:]))
    return json.loads(r.stdout)


def _raw(body):
    return json.dumps(body, ensure_ascii=False).encode("utf-8")


def _b64(raw):
    return base64.b64encode(raw).decode("ascii")


class TheWorker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise unittest.SkipTest("node is absent - snapshot.js cannot be run on this PC, so the worker is "
                                    "UNMEASURED here, not passed")
        cls.dir = tempfile.mkdtemp(prefix="tvd_profile_keys_")
        cls.key_a = RS.key_path_in(os.path.join(cls.dir, "a"))
        cls.key_b = RS.key_path_in(os.path.join(cls.dir, "b"))
        for p in (cls.key_a, cls.key_b):
            os.makedirs(os.path.dirname(p), exist_ok=True)
            key, why, _made = RS.load_or_create(p)
            assert key is not None, why
        with io.open(cls.key_a, encoding="utf-8") as fh:
            pub = RS.unb64u(json.load(fh)["pub"])
        cls.seed = {"rosterkey:" + OWNER: {"pub": RS.b64u(pub), "keyId": RS.key_id(pub), "at": 1}}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, True)

    def _post(self, body, key=None, seed=None, now=None):
        if body.get("signedAt") is None:
            body = dict(body, signedAt=now if now is not None else T0)
        raw = _raw(body)
        step = {"raw": _b64(raw), "headers": RS.sign_headers(key, raw)[0] if key else {}}
        if seed is not None:
            step["seed"] = seed
        if now is not None:
            step["now"] = now
        return step

    def _body(self, stores=None, boot=False, **over):
        s = _wstores() if stores is None else stores
        b = {"kind": "profile", "owner": OWNER, "boot": boot, "signedAt": None, "hash": CS.digest(s), "stores": s}
        b.update(over)
        return b

    def test_the_profile_rides_the_roster_route_under_the_owners_own_profile_key(self):
        """Elad 2026-10-24: one path. A profile posted to /api/roster lands in roster:<owner>:profile and nothing
        else; a roster-row publish on the same route never touches the profile; GET ?profile= reads it back."""
        rows = {"owner": OWNER, "boot": True, "signedAt": T0, "sections": {"owned": {"asOf": T0 - 1000, "counts": 3}}}
        out = _node({"seed": self.seed, "steps": [self._post(self._body(), self.key_a, now=T0),
                                                   self._post(rows, self.key_a, now=T0 + 5),
                                                   {"get": OWNER, "now": T0 + 9}]})
        prof, row, got = out["steps"]
        self.assertEqual(prof["puts"], ["roster:" + OWNER + ":profile"], prof["reply"])
        self.assertEqual(row["puts"], ["roster:" + OWNER], "a rows publish wrote %r (%r)" % (row["puts"], row["reply"]))
        self.assertEqual(got["get"]["stores"], _wstores())
        self.assertTrue(CS.profile_key(OWNER) == "roster:" + OWNER + ":profile")

    def test_what_was_not_sent_is_stored_and_served(self):
        """#210 - the worker keeps the upload's unsent list beside the record and GET serves it; a list that is not
        d2r_ store names is left off, never stored half-understood."""
        out = _node({"steps": [self._post(self._body(unsent=["d2r_huge"]), self.key_a, seed=self.seed, now=T0),
                               {"get": OWNER}]})
        post, got = out["steps"]
        self.assertTrue(post["reply"]["ok"], post["reply"])
        self.assertEqual(got["get"].get("unsent"), ["d2r_huge"], "the site dropped what the PC could not send")
        bad = _node({"steps": [self._post(self._body(unsent=["/" + "Users/x/secret"]), self.key_a, seed=self.seed,
                                          now=T0), {"get": OWNER}]})
        self.assertTrue(bad["steps"][0]["reply"]["ok"], bad["steps"][0]["reply"])
        self.assertNotIn("unsent", bad["steps"][1]["get"], "a list that is not store names was stored")

    def test_the_hash_is_the_same_on_both_sides(self):
        s = dict(_wstores(), d2r_emoji=json.dumps({"icon": "🛡️ ✓ ü"}))
        self.assertEqual(_node({"hashOf": s})["hash"], CS.digest(s))

    def test_a_signed_upload_is_stored_and_read_back_byte_for_byte(self):
        out = _node({"steps": [self._post(self._body(), self.key_a, seed=self.seed, now=T0), {"get": OWNER}]})
        post, got = out["steps"]
        self.assertTrue(post["reply"]["ok"], post["reply"])
        self.assertEqual(post["reply"]["stored"], ["profile"])
        self.assertTrue(post["reply"]["intentVerified"])
        self.assertEqual(got["get"]["stores"], _wstores())
        self.assertEqual(got["get"]["t"], T0)
        self.assertEqual(got["puts"], [], "a GET wrote to the store")
        self.assertTrue(CS.record_ok(dict(got["get"], owner=OWNER), OWNER),
                        "the console would not accept what the worker serves")

    def test_every_refusal_stores_nothing(self):
        big = dict(_wstores(), d2r_big=json.dumps(["x" * 210000]))
        pic = dict(_wstores(), d2r_pic=json.dumps({"art": "data:image/png;base64,AAAA"}))
        cases = [
            ("no registered key", self._post(self._body(), self.key_a, seed={}, now=T0), "no registered roster key"),
            ("unsigned", self._post(self._body(), None, seed=self.seed, now=T0), "not signed"),
            ("another key", self._post(self._body(), self.key_b, seed=self.seed, now=T0), "different key"),
            ("hash mismatch", self._post(self._body(hash="0" * 8), self.key_a, seed=self.seed, now=T0), "hash"),
            ("a picture", self._post(self._body(stores=pic), self.key_a, seed=self.seed, now=T0), "pictures"),
            ("oversize", self._post(self._body(stores=big), self.key_a, seed=self.seed, now=T0), "larger than 200000 bytes"),
            ("not an owner", self._post(self._body(owner="Somebody"), self.key_a, seed=self.seed, now=T0), "owner"),
            ("a bad store name", self._post(self._body(stores={"x": "1"}), self.key_a, seed=self.seed, now=T0), "d2r_"),
        ]
        out = _node({"steps": [c[1] for c in cases]})
        for (name, _step, said), got in zip(cases, out["steps"]):
            self.assertFalse(got["reply"]["ok"], "%s was accepted: %r" % (name, got["reply"]))
            self.assertIn(said, got["reply"]["why"], name)
            self.assertEqual(got["puts"], [], "%s wrote to the store" % name)

    def test_change_only_gap_boot_and_the_daily_cap(self):
        s2 = dict(_wstores(), d2r_owned=json.dumps(["Harlequin Crest", "Enigma"]))
        s3 = dict(_wstores(), d2r_owned=json.dumps(["Enigma"]))
        gap = 8 * 60 * 1000          # v3862 - the worker's floor (PROFILE_MIN_GAP_MS)
        steps = [self._post(self._body(), self.key_a, seed=self.seed, now=T0),
                 self._post(self._body(), self.key_a, now=T0 + 10 * gap),
                 self._post(self._body(stores=s2), self.key_a, now=T0 + gap - 1),
                 self._post(self._body(stores=s2, boot=True), self.key_a, now=T0 + gap - 1),
                 self._post(self._body(stores=s3), self.key_a, now=T0 + 3 * gap)]
        out = _node({"steps": steps})
        r = [s["reply"] for s in out["steps"]]
        self.assertEqual(r[0]["stored"], ["profile"])
        self.assertEqual(r[1]["skipped"], ["unchanged"])
        self.assertEqual(r[2]["skipped"], ["within 8 min"])
        self.assertEqual(r[3]["stored"], ["profile"], "the boot upload was held back")
        self.assertEqual(r[4]["stored"], ["profile"])
        self.assertEqual(out["records"]["roster:" + OWNER + ":profile"]["n"], 3)
        day = __import__("time").strftime("%Y-%m-%d", __import__("time").gmtime(T0 // 1000))
        full = dict(self.seed)
        full["roster:" + OWNER + ":profile"] = {"owner": OWNER, "t": T0 - 4 * gap, "day": day, "n": 150, "hash": "x",
                                     "stores": {"d2r_owned": "[]"}, "pub": None}
        capped = _node({"steps": [self._post(self._body(), self.key_a, seed=full, now=T0)]})["steps"][0]
        self.assertFalse(capped["reply"]["ok"])
        self.assertIn("quota", capped["reply"]["why"])
        self.assertEqual(capped["puts"], [])

    def test_a_captured_upload_cannot_be_replayed(self):
        s2 = dict(_wstores(), d2r_owned=json.dumps(["Enigma"]))
        first = self._post(self._body(boot=True), self.key_a, seed=self.seed, now=T0)
        newer = self._post(self._body(stores=s2, boot=True), self.key_a, now=T0 + 60000)
        replay = {k: v for k, v in first.items() if k != "seed"}
        replay["now"] = T0 + 120000
        out = _node({"steps": [first, newer, replay]})
        r = [x["reply"] for x in out["steps"]]
        self.assertEqual((r[0].get("stored"), r[1].get("stored")), (["profile"], ["profile"]))
        self.assertFalse(r[2]["ok"], "the first (boot) upload was replayed over the newer one: %r" % r[2])
        self.assertIn("replayed", r[2]["why"])
        self.assertEqual(out["records"]["roster:" + OWNER + ":profile"]["stores"], s2)
        stale = _node({"steps": [self._post(self._body(signedAt=T0), self.key_a, seed=self.seed,
                                            now=T0 + 16 * 60000),
                                 self._post(self._body(signedAt="soon"), self.key_a, now=T0)]})
        for got in stale["steps"]:
            self.assertFalse(got["reply"]["ok"], got["reply"])
            self.assertIn("signedAt", got["reply"]["why"])
            self.assertEqual(got["puts"], [])

    def test_a_signed_client_cannot_park_stores_the_console_keeps_home(self):
        cases = [dict(_wstores(), d2r_installId="x"), dict(_wstores(), d2r_api_status="{}"),
                 dict(_wstores(), d2r_quarantine_a="{}"), dict(_wstores(), d2r_tvdHist="[]")]
        out = _node({"steps": [self._post(self._body(stores=c), self.key_a, seed=self.seed, now=T0) for c in cases]})
        for c, got in zip(cases, out["steps"]):
            self.assertFalse(got["reply"]["ok"], "the worker stored %r" % sorted(c))
            self.assertEqual(got["puts"], [])
        bad = [dict(_wstores(), d2r_api_world="{}"), {k: v for k, v in _wstores().items() if k != "d2r_api_world"},
               dict(_wstores(), d2r_api_world=json.dumps(dict(WORLD, machine="linux"))),
               dict(_wstores(), d2r_api_chars_learned='{"ok":true,"status":{"tick":1}}'),
               dict(_wstores(), d2r_notes=json.dumps({"p": HOME_ + "someone/x"})),
               dict(_wstores(), d2r_notes=json.dumps({"t": "ghp_" + "A" * 30})),
               # what JSON escaping hides from a raw-text check, and the two ids the console blanks besides
               dict(_wstores(), d2r_notes='{"p":"\\/Users\\/someone\\/x"}'),
               dict(_wstores(), d2r_notes='{"t":"\\u0067hp_' + "A" * 30 + '"}'),
               dict(_wstores(), d2r_notes=json.dumps({"I·abcd1234·x": 1})),
               dict(_wstores(), d2r_notes=json.dumps(["L·0badf00d·"])),
               dict(_wstores(), d2r_notes=json.dumps({"img": "data:image/png;x"})),
               # JSON.parse keeps the last of two equal keys: the first is only in the raw text
               dict(_wstores(), d2r_notes='{"p":"' + HOME_ + 'someone/x","p":"ok"}'),
               # a store that is not JSON is its own text
               dict(_wstores(), d2r_notes='note: ' + HOME_ + 'someone/x'),
               # ...and escaped under the dropped key, which neither the raw text nor the parse shows
               dict(_wstores(), d2r_notes='{"p":"\\/Users\\/someone\\/x","p":"ok"}'),
               dict(_wstores(), d2r_notes='{"t":"\\u0067hp_' + "A" * 30 + '","t":"ok"}')]
        out = _node({"steps": [self._post(self._body(stores=c), self.key_a, seed=self.seed, now=T0) for c in bad]})
        for c, got in zip(bad, out["steps"]):
            self.assertFalse(got["reply"]["ok"], "the worker stored an uncleaned or worldless body: %r" % got["reply"])
            self.assertEqual(got["puts"], [])
        ok = _node({"steps": [self._post(self._body(), self.key_a, seed=self.seed, now=T0)]})
        self.assertEqual(ok["steps"][0]["reply"].get("stored"), ["profile"], ok["steps"][0]["reply"])

    def test_an_unreadable_stored_record_is_not_started_over(self):
        seed = dict(self.seed)
        seed["roster:" + OWNER + ":profile"] = "{not json"
        got = _node({"steps": [self._post(self._body(), self.key_a, seed=seed, now=T0)]})["steps"][0]
        self.assertFalse(got["reply"]["ok"])
        self.assertEqual(got["puts"], [])

    def test_the_worker_keeps_home_what_the_console_keeps_home(self):
        js = _read(SNAPSHOT_JS)
        deny = js[js.index("export const DENY = ["):js.index("];", js.index("export const DENY = ["))]
        self.assertEqual(set(re.findall(r'"(d2r_[A-Za-z0-9_]+)"', deny)), set(CS.DENY))
        pre = re.search(r"export const DENY_PREFIX = \[([^\]]*)\]", js).group(1)
        self.assertEqual(set(re.findall(r'"([^"]+)"', pre)), set(CS.DENY_PREFIX))
        api = re.search(r"export const API_NAMES = \[([^\]]*)\]", js).group(1)
        self.assertEqual(set(re.findall(r'"([^"]+)"', api)), set(CS.API_FIELDS))

    def test_a_record_signed_by_a_key_no_longer_theirs_is_not_served(self):
        with io.open(self.key_b, encoding="utf-8") as fh:
            pub_b = RS.unb64u(json.load(fh)["pub"])
        rotated = {"rosterkey:" + OWNER: {"pub": RS.b64u(pub_b), "keyId": RS.key_id(pub_b), "at": 2}}
        out = _node({"steps": [self._post(self._body(), self.key_a, seed=self.seed, now=T0), {"get": OWNER}]})
        self.assertEqual(out["steps"][1]["get"]["stores"], _wstores())
        rec = out["records"]["roster:" + OWNER + ":profile"]
        seed = dict(rotated)
        seed["roster:" + OWNER + ":profile"] = rec
        got = _node({"steps": [{"get": OWNER, "seed": seed}]})["steps"][0]["get"]
        self.assertTrue(got["corrupt"], got)
        self.assertNotIn("stores", got)
        self.assertIn("registered key", got["why"])

    def test_a_record_that_fails_its_own_hash_is_served_as_corrupt(self):
        seed = dict(self.seed)
        seed["roster:" + OWNER + ":profile"] = {"owner": OWNER, "t": T0, "hash": CS.digest(_wstores()),
                                     "pub": seed["rosterkey:" + OWNER]["pub"],
                                     "stores": dict(_wstores(), d2r_owned='["planted"]')}
        out = _node({"steps": [{"get": OWNER, "seed": seed}, {"get": "Wife PC"}, {"get": "Somebody"}]})
        corrupt, none, bad = (s["get"] for s in out["steps"])
        self.assertTrue(corrupt["corrupt"])
        self.assertNotIn("stores", corrupt)
        self.assertNotIn("registered key", corrupt.get("why", ""), "the key check, not the hash, refused it")
        self.assertEqual((none["ok"], none["published"]), (True, False))
        self.assertFalse(bad["ok"])


class TheConsoleDoors(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import control_app as CA
        cls.CA = CA
        cls.src = _read(APP)

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tvd_profile_console_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        p = mock.patch.object(self.CA, "_log_root", lambda: self.tmp)
        p.start()
        self.addCleanup(p.stop)
        q = mock.patch.object(self.CA, "_beacon_suppressed_by", lambda: None)
        q.start()
        self.addCleanup(q.stop)

    def _fleet(self, rows_online=(), rows_offline=()):
        return mock.patch.object(self.CA, "fleet_presence_last_good",
                                 lambda: ({"ok": True, "online": list(rows_online), "offline": list(rows_offline)}, 1))

    def test_the_site_answers_then_goes_down_and_the_last_copy_is_shown_with_its_time(self):
        rec = dict(_record(), ok=True, published=True, corrupt=False, intentVerified=True)
        with mock.patch.object(self.CA, "_roster_get", lambda url: rec), self._fleet():
            v = self.CA._profile_view(OWNER)
        self.assertEqual((v["ok"], v["source"], v["stores"]), (True, "worker", _stores()))
        with mock.patch.object(self.CA, "_roster_get", lambda url: {"ok": False, "why": "URLError", "code": None}), self._fleet():
            v = self.CA._profile_view(OWNER)
        self.assertTrue(v["ok"], "with the site down the PC's last copy was not shown")
        self.assertEqual((v["source"], v["t"], v["stores"]), ("cache", T0, _stores()))
        self.assertIn("board uploaded", v["words"])
        self.assertIn("showing this PC's last copy", v["words"])

    def test_nothing_uploaded_is_said(self):
        with mock.patch.object(self.CA, "_roster_get", lambda url: {"ok": True, "owner": OWNER, "published": False}), \
                self._fleet():
            v = self.CA._profile_view(OWNER)
        self.assertFalse(v["ok"])
        self.assertIn("has not uploaded", v["why"])

    def test_the_last_copy_stands_in_only_when_the_site_could_not_be_read(self):
        self.assertTrue(CS.write_cache(os.path.join(self.tmp, "roster_profile_cache"), _record()))
        for said in ({"ok": True, "owner": OWNER, "published": False},
                     {"ok": True, "owner": OWNER, "published": True, "corrupt": True, "t": T0,
                      "why": "the key that signed it is not Dean's registered key now"}):
            with mock.patch.object(self.CA, "_roster_get", lambda url, said=said: said), self._fleet():
                v = self.CA._profile_view(OWNER)
            self.assertFalse(v["ok"], "this PC's old copy was shown over the site's answer %r" % said)
            self.assertIn("the site says", v["why"])
        with mock.patch.object(self.CA, "_roster_get",
                               lambda url: {"ok": False, "why": "snapshot could not be read: storage unavailable"}), \
                self._fleet():
            v = self.CA._profile_view(OWNER)
        self.assertFalse(v["ok"], "this PC's old copy was drawn over the site refusing")
        with mock.patch.object(self.CA, "_roster_get", lambda url: None), self._fleet():
            v = self.CA._profile_view(OWNER)
        self.assertEqual((v["ok"], v["source"]), (True, "cache"))

    def test_the_world_the_board_drew_in_rides_with_the_upload(self):
        w = {"machine": "windows", "profile": "main", "os": "WINDOWS", "ledger": "", "cousin": True}
        self.assertTrue(self.CA._profile_book_take({"stores": _stores(), "world": w})["ok"])
        posted = []
        with mock.patch.object(self.CA, "_profile_owner", lambda: OWNER), \
                mock.patch.object(self.CA, "_profile_chars_learned", lambda: None), \
                mock.patch.object(self.CA, "main_locks_view", lambda: None), \
                mock.patch.object(self.CA, "_profile_saves", lambda: None), \
                mock.patch.object(self.CA, "_roster_post",
                                  lambda url, body, key: posted.append(body) or {"ok": True, "stored": ["profile"]}):
            self.CA._profile_publish_once(True)
        self.assertEqual(json.loads(posted[0]["stores"]["d2r_api_world"]), w)

    def test_the_book_takes_only_what_may_leave_and_the_lane_signs_with_the_roster_key(self):
        got = self.CA._profile_book_take({"stores": dict(_stores(), d2r_installId="x", d2r_tvdHist="[]")})
        self.assertTrue(got["ok"])
        with io.open(os.path.join(self.tmp, "roster_profile_book.json"), encoding="utf-8") as fh:
            book = json.load(fh)
        self.assertEqual(book["stores"], _stores())
        posted = []
        with mock.patch.object(self.CA, "_profile_owner", lambda: OWNER), \
                mock.patch.object(self.CA, "_profile_chars_learned", lambda: {"ok": True, "chars": []}), \
                mock.patch.object(self.CA, "main_locks_view", lambda: {"ok": False, "locked": None}), \
                mock.patch.object(self.CA, "_profile_saves", lambda: None), \
                mock.patch.object(self.CA, "_roster_post",
                                  lambda url, body, key: posted.append((url, body, key)) or
                                  {"ok": True, "stored": ["profile"]}):
            self.CA._profile_publish_once(True)
            self.CA._profile_publish_once(False)
        self.assertEqual(len(posted), 1, "an unchanged snapshot was uploaded again")
        url, body, key = posted[0]
        self.assertEqual(url, "https://bull-4-u.com/api/roster")
        self.assertEqual(key, os.path.join(self.tmp, ".roster_key.json"))
        self.assertIn("d2r_api_chars_learned", body["stores"])
        self.assertNotIn("d2r_api_main_locks", body["stores"], "an unreadable console answer was uploaded")
        self.assertEqual(body.get("unsent"), [], "#210 - the lane did not carry what the book left out (none here)")

    def test_a_suppressed_pc_uploads_nothing(self):
        self.CA._profile_book_take({"stores": _stores()})
        posted = []
        with mock.patch.object(self.CA, "_beacon_suppressed_by", lambda: "a fixture world"), \
                mock.patch.object(self.CA, "_roster_post", lambda *a: posted.append(a)):
            self.CA._profile_publish_once(True)
        self.assertEqual(posted, [])

    def test_the_routes_and_the_lane_are_wired(self):
        src = self.src
        # one path: the profile rides the roster doors and the roster lane; the snapshot route, doors and loop are gone
        self.assertNotIn("/api/snapshot", src)
        self.assertNotIn("_snapshot_publish_loop", src)
        self.assertFalse(os.path.exists(os.path.join(ROOT, "functions", "api", "snapshot.js")))
        view = src[src.index('if path.endswith("/roster-cache") and "profile" in _rq:'):]
        view = view[:view.index("return\n") + 7]
        self.assertLess(src.index('if path.endswith("/roster-cache") and "profile" in _rq:'),
                        src.index('if path == "/api/roster-cache":'), "the profile view must answer before the roster panel")
        self.assertIn("_profile_view(", view)
        door = src[src.index('if path == "/api/roster-book":'):]
        door = door[:door.index("return\n", door.index("_profile_book_take")) + 7]
        self.assertLess(door.index("console_may_post("), door.index("_profile_book_take("))
        self.assertIn('body.get("kind") == "profile"', door)
        lane = src[src.index("def _roster_publish_loop():"):src.index("def _roster_cache_dir():")]
        self.assertEqual(lane.count("_roster_profile_tick("), 2, "the profile goes out on the roster lane at boot and each tick")
        self.assertIn('_ROSTER_URL = "https://bull-4-u.com/api/roster"', src)
        self.assertIn('_roster_get(_ROSTER_URL + "?profile="', src)
        self.assertIn("_roster_post(_ROSTER_URL, body,", src)


class TheViewerPanel(unittest.TestCase):

    def test_a_click_asks_for_the_profile_and_falls_back_to_the_roster_row(self):
        ui = _read(UI)
        self.assertIn("(window._shadowOpen || window._shadowEnter)(btn.getAttribute('data-owner') || '')", ui)
        start = ui.index("  window._shadowOpen = function (owner) {")
        body = ui[start:ui.index("  };", start)]
        self.assertIn("/api/roster-cache?profile=", body)
        self.assertIn("window._shadowSnapEnter(owner, d)", body)
        self.assertIn("window._shadowFillFromRoster(owner, d, gen)", body)
        self.assertEqual(body.count("window._shadowEnter(owner)"), 2, "no fallback on a missing or failed snapshot")
        enter = ui[ui.index("  window._shadowSnapEnter = function"):start]
        self.assertIn("&tvd-shadow=1", enter)
        self.assertIn("' · read only'", enter)


class TheRosterRowOpensInItsOwnFrame(unittest.TestCase):
    """No upload. Dean's published row and his fleet platform fill an isolated frame. A linux row has no closed machine, so it does not invent one."""

    def _fn(self):
        ui = _read(UI)
        start = ui.index("  window._shadowRosterStores = function (row, fleet, owner) {")
        end = ui.index("  window._shadowEnter = function (owner) {", start)
        return ui[start:end]

    def test_dean_gets_his_builds_and_a_closed_windows_world_and_linux_does_not(self):
        if not NODE:
            raise AssertionError("node is absent - the roster-row frame cannot be run here, so it is UNMEASURED")
        fn = self._fn()
        js = "var window = globalThis;\n" + fn + r"""
window._fleetRosterOwner = function (m) {
  var nick = String((m && m.nickname) || '').trim();
  var owners = ['Konyo \u00b7 Mac', 'Konyo \u00b7 ALT', 'Konyo \u00b7 GrokBot', 'Dean', 'Wife PC'];
  if (owners.indexOf(nick) >= 0) return nick;
  if (nick === 'Konyo' && m && m.platform === 'mac') return 'Konyo \u00b7 Mac';
  return '';
};
var dean = { owner: 'Dean', published: true, t: 1792800000000, sections: {
  characters: { rows: [
    { name: 'A', cls: 'Sorceress', level: 90, sets: [{ name: 'Set 1', slots: { head: { name: 'Shako' } }, inv: [] }] },
    { name: 'B', sets: [{ name: 'S', slots: {}, inv: [{ name: 'Torch' }] }] },
    { name: 'C', sets: [{ name: 'S', slots: {}, inv: [] }] },
    { name: 'plain' }
  ]},
  vault: { rows: [] },
  stash: { rows: [{ name: 'Ist' }, { name: 'Mal' }, { name: 'Ist' }, { name: 'Um' }] }
}};
var host = 'not-a-store';
var fleet = { me: 'viewer', online: [], offline: [
  { nickname: 'Dean', platform: 'windows', machine: host }
]};
var out = window._shadowRosterStores(dean, fleet, 'Dean');
var builds = JSON.parse(out.stores.d2r_charBuilds);
var owned = JSON.parse(out.stores.d2r_owned);
var world = JSON.parse(out.stores.d2r_api_world);
var blob = JSON.stringify(out.stores);
var mine = window._shadowRosterStores(dean, { me: host, offline: [{ nickname: 'Dean', platform: 'windows', machine: host }] }, 'Dean');
var linux = window._shadowRosterStores(
  { sections: { characters: { rows: [{ name: 'G', sets: [{ name: 'S', slots: {}, inv: [] }] }] } } },
  { offline: [{ nickname: 'Konyo · GrokBot', platform: 'linux', machine: host }] },
  'Konyo · GrokBot');
var mac = window._shadowRosterStores({}, { offline: [{ nickname: 'Konyo', platform: 'mac', machine: host }] }, 'Konyo · Mac');
var winKonyo = window._shadowRosterStores({}, { offline: [{ nickname: 'Konyo', platform: 'windows', machine: host }] }, 'Konyo · Mac');
process.stdout.write(JSON.stringify({
  nBuilds: Object.keys(builds).length,
  gear: builds.s0.sets[0].slots.head.name,
  plainHasSets: builds.s3 ? Object.prototype.hasOwnProperty.call(builds.s3, 'sets') : null,
  plainLevel: builds.s3 ? builds.s3.level : null,
  owned: owned,
  world: world,
  leaked: blob.indexOf(host) !== -1,
  claim: !!(out.stores.d2r_ownerClaim || out.stores.d2r_installId),
  cousinWhenMine: JSON.parse(mine.stores.d2r_api_world).cousin,
  mineLeaked: JSON.stringify(mine.stores).indexOf(host) !== -1,
  linuxWorld: linux.world,
  linuxStore: Object.prototype.hasOwnProperty.call(linux.stores, 'd2r_api_world'),
  mac: mac.world && mac.world.machine,
  winKonyo: winKonyo.world
}));
"""
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got["nBuilds"], 4, got)
        self.assertEqual(got["gear"], "Shako")
        self.assertIs(got["plainHasSets"], False, "a named row with no sets was stored as an empty set, so the card counts 0 items")
        self.assertIsNone(got["plainLevel"], "a row with no level was stored as level 1")
        self.assertEqual(got["owned"], ["Ist", "Mal", "Um"])
        self.assertEqual(got["world"], {"machine": "windows", "profile": "main", "ledger": "", "os": "WINDOWS", "cousin": True})
        self.assertFalse(got["leaked"], "the fleet hostname was copied into the stores")
        self.assertFalse(got["claim"], "a claim or install id was put in the roster stores")
        self.assertIs(got["cousinWhenMine"], False)
        self.assertFalse(got["mineLeaked"])
        self.assertIsNone(got["linuxWorld"])
        self.assertFalse(got["linuxStore"])
        self.assertEqual(got["mac"], "mac")
        self.assertIsNone(got["winKonyo"])

    def test_a_missing_list_shows_the_published_total_and_a_gearless_name_stays_a_card(self):
        """A published total with no name list is not 0. A named character with no sets is still a card.

        have 0 with no list stays unknown. A snapshot that already has a named build, or a found
        list, keeps those. An empty snapshot takes the roster names and the published totals.
        """
        if not NODE:
            raise AssertionError("node is absent - the published-total frame cannot be run here, so it is UNMEASURED")
        ui = _read(UI)
        roster = ui[ui.index("  window._shadowRosterStores = function (row, fleet, owner) {"):ui.index("  window._shadowEnter = function (owner) {")]
        merge = ui[ui.index("  window._shadowStoreEmpty = function (raw) {"):ui.index("  window._shadowFillFromRoster = function (owner, snap, gen) {")]
        html = _read(BIBLE)
        lane_at = html.index("window._publishedLane = function (lane) {")
        lane = html[lane_at:html.index("\n};", lane_at) + 3]
        self.assertNotIn("_tvdShadow", lane)
        self.assertNotIn("tvd-shadow-snap", lane)
        js = "var window = globalThis;\n" + roster + "\n" + merge + "\n" + lane + r"""
window._fleetRosterOwner = function (m) {
  var nick = String((m && m.nickname) || '').trim();
  if (nick === 'Dean') return 'Dean';
  return '';
};
function lsr(map) {
  return { getItem: function (k) { return Object.prototype.hasOwnProperty.call(map, k) ? map[k] : null; } };
}
var fleet = { me: 'viewer', offline: [{ nickname: 'Dean', platform: 'windows', machine: 'host' }] };
var counts = window._shadowRosterStores({ owner: 'Dean', published: true, sections: {
  characters: { rows: [
    { name: 'A', cls: 'Sorceress', level: 90, title: 'blizz', sets: [{ name: 'Set 1', slots: { head: { name: 'Shako' } }, inv: [] }] },
    { name: 'plain', cls: 'Paladin', title: '' }
  ]},
  chronicle: { counts: { sets: { have: 132, total: 135 }, uniques: { have: 0, total: 403 }, runewords: { have: 98, total: 99 } } }
}}, fleet, 'Dean');
var cards = JSON.parse(counts.stores.d2r_charBuilds);
var progress = JSON.parse(counts.stores.d2r_shadowProgress);
var named = window._shadowRosterStores({ owner: 'Dean', published: true, sections: {
  characters: { counts: 125, rows: [{ name: 'AltOne', cls: 'Amazon', level: 88, title: 'javazon' }] },
  chronicle: {
    counts: { uniques: { have: 52, total: 403 }, sets: { have: 4, total: 135 }, runewords: { have: 0, total: 99 } },
    rows: [{ lane: 'uniques', name: 'Shako' }, { lane: 'uniques', name: 'Shako' }, { lane: 'sets', name: 'Tal Rasha' }, { lane: 'runewords', name: '' }]
  }
}}, fleet, 'Dean');
var found = JSON.parse(named.stores.d2r_foundLog);
var pieces = JSON.parse(named.stores.d2r_setPieces);
var namedProgress = JSON.parse(named.stores.d2r_shadowProgress);
var kept = window._shadowMergeStores({
  d2r_charBuilds: JSON.stringify({ keep: { name: 'Kept', sets: [{ name: 'S', slots: {} }] } }),
  d2r_foundLog: JSON.stringify({ Windforce: '' })
}, counts.stores);
var filled = window._shadowMergeStores({ d2r_charBuilds: '{}', d2r_foundLog: '{}', d2r_setPieces: '[]' }, named.stores);
window.LSR = lsr({});
var own = window._publishedLane('runewords');
window.LSR = lsr({ d2r_shadowProgress: counts.stores.d2r_shadowProgress });
var uni0 = window._publishedLane('uniques');
var setsN = window._publishedLane('sets');
var rwN = window._publishedLane('runewords');
window.LSR = lsr({ d2r_foundLog: named.stores.d2r_foundLog, d2r_shadowProgress: JSON.stringify({ uniques: { have: 52, total: 403, listed: false } }) });
var namesWin = window._publishedLane('uniques');
process.stdout.write(JSON.stringify({
  names: Object.keys(cards).map(function (k) { return cards[k].name; }),
  title: cards.s0 && cards.s0.title,
  plainTitle: !!(cards.s1 && Object.prototype.hasOwnProperty.call(cards.s1, 'title')),
  plainSets: !!(cards.s1 && Object.prototype.hasOwnProperty.call(cards.s1, 'sets')),
  plainLevel: cards.s1 ? cards.s1.level : null,
  gear: cards.s0.sets[0].slots.head.name,
  wroteFound: Object.prototype.hasOwnProperty.call(counts.stores, 'd2r_foundLog')
    || Object.prototype.hasOwnProperty.call(counts.stores, 'd2r_setPieces')
    || Object.prototype.hasOwnProperty.call(counts.stores, 'd2r_rwMade'),
  progress: progress,
  foundKeys: Object.keys(found),
  pieces: pieces,
  wroteRw: Object.prototype.hasOwnProperty.call(named.stores, 'd2r_rwMade'),
  namedProgress: namedProgress,
  altName: JSON.parse(named.stores.d2r_charBuilds).s0.name,
  altSets: Object.prototype.hasOwnProperty.call(JSON.parse(named.stores.d2r_charBuilds).s0, 'sets'),
  keptName: Object.keys(JSON.parse(kept.d2r_charBuilds))[0],
  keptFound: Object.keys(JSON.parse(kept.d2r_foundLog)),
  keptProgress: kept.d2r_shadowProgress ? Object.keys(JSON.parse(kept.d2r_shadowProgress)) : [],
  filledName: JSON.parse(filled.d2r_charBuilds).s0.name,
  filledFound: Object.keys(JSON.parse(filled.d2r_foundLog)),
  filledProgress: Object.keys(JSON.parse(filled.d2r_shadowProgress)),
  own: own,
  uni0: uni0,
  setsN: setsN,
  rwN: rwN,
  namesWin: namesWin
}));
"""
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-1200:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got["names"], ["A", "plain"])
        self.assertEqual(got["title"], "blizz")
        self.assertIs(got["plainTitle"], False)
        self.assertIs(got["plainSets"], False)
        self.assertIsNone(got["plainLevel"])
        self.assertEqual(got["gear"], "Shako")
        self.assertIs(got["wroteFound"], False, "a counts-only chronicle was stored as an empty found list")
        self.assertEqual(got["progress"]["sets"], {"have": 132, "total": 135, "listed": False})
        self.assertEqual(got["progress"]["uniques"], {"have": 0, "total": 403, "listed": False})
        self.assertEqual(got["progress"]["runewords"], {"have": 98, "total": 99, "listed": False})
        self.assertEqual(got["foundKeys"], ["Shako"])
        self.assertEqual(got["pieces"], ["Tal Rasha"])
        self.assertIs(got["wroteRw"], False, "an empty runeword name was stored as a made word")
        self.assertEqual(got["namedProgress"], {
            "uniques": {"have": 52, "total": 403, "listed": True},
            "sets": {"have": 4, "total": 135, "listed": True},
            "runewords": {"have": 0, "total": 99, "listed": False},
        })
        self.assertEqual(got["altName"], "AltOne")
        self.assertIs(got["altSets"], False)
        self.assertEqual(got["keptName"], "keep")
        self.assertEqual(got["keptFound"], ["Windforce"])
        self.assertNotIn("uniques", got["keptProgress"])
        self.assertEqual(got["filledName"], "AltOne")
        self.assertEqual(got["filledFound"], ["Shako"])
        self.assertEqual(got["filledProgress"], ["uniques", "sets", "runewords"])
        self.assertIsNone(got["own"], "his own board, with no published blob, was given a shadow total")
        self.assertIsNone(got["uni0"]["show"], "have 0 with no list was painted as 0")
        self.assertEqual(got["uni0"]["sentence"], "the list wasn't sent")
        self.assertEqual(got["setsN"]["show"], {"have": 132, "total": 135})
        self.assertEqual(got["rwN"]["show"], {"have": 98, "total": 99})
        self.assertEqual(got["rwN"]["sentence"], "the list wasn't sent")
        self.assertIsNone(got["namesWin"], "a lane that already has names was replaced by the published total")

    def test_a_name_list_cut_at_the_cap_says_newest_n_of_m(self):
        """#200 (the v3802 look) - a roster lane carries at most 400 names and <lane>Named rides beside the tally. The
        shadow built from it marked 400 of his 461 finds and called that the list; it says "the newest 400 of 461"."""
        if not NODE:
            raise AssertionError("node is absent - the roster shadow cannot be run here, so it is UNMEASURED")
        ui = _read(UI)
        start = ui.index("  window._shadowRosterStores = function (row, fleet, owner) {")
        builder = ui[start:ui.index("\n  };\n", start) + 5]
        counts = _js_fn(ui, "function _chronicleCounts(summary, progress, lists) {")
        js = "var window = globalThis;\n" + builder + "\n" + counts + r"""
var fleet = { ok: true, me: 'm1', online: [{ nickname: 'Dean', platform: 'windows', machine: 'm2' }], offline: [] };
var b = window._shadowRosterStores({ owner: 'Dean', published: true, sections: { chronicle: {
  counts: { uniques: { have: 461, total: 403 }, uniquesNamed: 461, sets: { have: 2, total: 135 }, setsNamed: 2 },
  rows: [{ lane: 'uniques', name: 'Shako' }, { lane: 'uniques', name: 'Arkaine' }, { lane: 'sets', name: 'A' }, { lane: 'sets', name: 'B' }]
} } }, fleet, 'Dean');
var prog = JSON.parse(b.stores.d2r_shadowProgress);
process.stdout.write(JSON.stringify({ prog: prog, line: _chronicleCounts(null, prog, { uniques: 2, sets: 2 }) }));
"""
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-1200:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got["prog"]["uniques"].get("named"), 461, got["prog"])
        self.assertEqual(got["prog"]["uniques"].get("sent"), 2)
        self.assertNotIn("named", got["prog"]["sets"], "a whole list was marked as cut: %r" % got["prog"])
        self.assertIn("Uniques names: the newest 2 of 461", got["line"], "a cut list read as the whole list (#200)")
        self.assertNotIn("Sets names", got["line"])

    def test_an_empty_arrived_list_is_zero_and_a_missing_list_keeps_the_sentence(self):
        """A list that arrived empty is 0. A list that was not sent keeps the sentence.

        The runeword tab and the hub both follow that. Have 98 with no list stays 98 plus
        the sentence. Have 98 with an empty list is 0, because the list did arrive.
        """
        if not NODE:
            raise AssertionError("node is absent - the empty-list frame cannot be run here, so it is UNMEASURED")
        ui = _read(UI)
        html = _read(BIBLE)
        lane_at = html.index("window._publishedLane = function (lane) {")
        lane = html[lane_at:html.index("\n};", lane_at) + 3]
        self.assertNotIn("_tvdShadow", lane)
        count = _js_fn(ui, "function _listCount(raw) {")
        counts = _js_fn(ui, "function _chronicleCounts(summary, progress, lists) {")
        doctor = html.index("(function _v42_sanitizeWishlistOwned()")
        self.assertLess(html.index("if (window._tvdShadow) return;", doctor), html.index("GRAIL FOUND-SEED floor", doctor))
        self.assertIn("mem.setItem = function () {}", html[html.index("/* SHADOW MODE BOOT"):html.index("</script>", html.index("/* SHADOW MODE BOOT"))])
        js = "var window = globalThis;\n" + lane + "\n" + count + "\n" + counts + r"""
function lsr(map) {
  return { getItem: function (k) { return Object.prototype.hasOwnProperty.call(map, k) ? map[k] : null; } };
}
function progress(have) {
  return JSON.stringify({ runewords: { have: have, total: 99, listed: false } });
}
window.LSR = lsr({ d2r_rwMade: '{}', d2r_shadowProgress: progress(0) });
var empty = window._publishedLane('runewords');
window.LSR = lsr({ d2r_shadowProgress: progress(0) });
var absent = window._publishedLane('runewords');
window.LSR = lsr({ d2r_rwMade: '{}', d2r_shadowProgress: progress(98) });
var emptyBeats = window._publishedLane('runewords');
window.LSR = lsr({ d2r_shadowProgress: progress(98) });
var unsentHave = window._publishedLane('runewords');
var line = _chronicleCounts(
  { chron: { made: 0, total: 99 }, sets: { found: 4, total: 135 }, grail: { found: 53, total: 403 } },
  { runewords: { have: 0, total: 99, listed: false }, sets: { have: 4, total: 135, listed: false }, uniques: { have: 53, total: 403, listed: false } },
  { runewords: _listCount('{}'), sets: _listCount(null), uniques: _listCount('{"Shako":""}') }
);
var unsent = _chronicleCounts(
  { chron: { made: 0, total: 99 }, sets: { found: 0, total: 135 }, grail: { found: 0, total: 403 } },
  { runewords: { have: 0, total: 99, listed: false }, sets: { have: 0, total: 135, listed: false }, uniques: { have: 0, total: 403, listed: false } },
  { runewords: _listCount(null), sets: _listCount(null), uniques: _listCount(null) }
);
process.stdout.write(JSON.stringify({
  empty: empty, absent: absent, emptyBeats: emptyBeats, unsentHave: unsentHave,
  listEmpty: _listCount('{}'), listBlank: _listCount(''), listArr: _listCount('[]'),
  listMissing: _listCount(null), listBad: _listCount('{'),
  line: line, unsent: unsent
}));
"""
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-1200:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got["empty"], {"show": {"have": 0, "total": 99}, "sentence": ""})
        self.assertIsNone(got["absent"]["show"])
        self.assertEqual(got["absent"]["sentence"], "the list wasn't sent")
        self.assertEqual(got["emptyBeats"], {"show": {"have": 0, "total": 99}, "sentence": ""})
        self.assertEqual(got["unsentHave"]["show"], {"have": 98, "total": 99})
        self.assertEqual(got["unsentHave"]["sentence"], "the list wasn't sent")
        self.assertEqual(got["listEmpty"], 0)
        self.assertEqual(got["listBlank"], 0)
        self.assertEqual(got["listArr"], 0)
        self.assertIsNone(got["listMissing"])
        self.assertIsNone(got["listBad"])
        dot = " \u00b7 "
        self.assertEqual(got["line"], "Runewords 0/99" + dot + "Sets 4/135" + dot + "Uniques 53/403")
        self.assertNotIn("wasn", got["line"])
        self.assertEqual(got["unsent"], "the list wasn\u2019t sent")
        self.assertNotIn("0/", got["unsent"])

    def test_the_missing_snapshot_does_not_open_this_browser(self):
        ui = _read(UI)
        enter = ui[ui.index("  window._shadowEnter = function (owner) {"):ui.index("  window._shadowLeave = function () {")]
        self.assertNotIn("getElementById('tvd-eng')", enter)
        self.assertNotIn("pending: true", enter)
        self.assertIn("window._shadowSnapEnter", enter)
        self.assertIn("window._shadowRosterStores", enter)
        html = _read(BIBLE)
        b0 = html.index("/* SHADOW MODE BOOT")
        boot = html[b0:html.index("</script>", b0)]
        self.assertIn("#claim-bar{display:none !important}", boot)
        self.assertIn("window._d2rClaimThisBrowser = function () { return false; }", boot)
        self.assertIn("closest('#claim-bar, #claim-btn')", boot)


class TheBoardSaysItsWorld(unittest.TestCase):

    def test_the_board_posts_the_world_its_stores_were_drawn_in(self):
        html = _read(BIBLE)
        up = html[html.index("/* SHADOW MODE - THIS BOARD HANDS ITS ACCOUNT STORES TO ITS CONSOLE'S ROSTER LANE."):]
        up = up[:up.index("</script>")]
        self.assertIn("var body = JSON.stringify({ kind: 'profile', stores: stores, world: world });", up)
        for fact in ("machine: window.D2R_MACHINE", "profile: window.D2R_PROFILE", "os: window.D2R_HOST_OS",
                     "ledger: String(window._D2R_LEDGER || '')", "cousin: !!window._isCousinShell"):
            self.assertIn(fact, up)


class TheSameConsoleDrawsIt(unittest.TestCase):
    """Elad's ruling (2026-10-24): shadow is his own console with Dean's data - the same shell, the same screens, tabs
    and layout, only the data swapped. So the shadow may differ from the console in exactly two places: the boot
    block that swaps the store (and dims the controls a click cannot reach), and the upload that a shadow never
    makes. Everything that DRAWS is the one board, unbranched."""

    def _spans(self, html):
        b0 = html.index("/* SHADOW MODE BOOT")
        b1 = html.index("</script>", b0)
        u0 = html.index("/* SHADOW MODE - THIS BOARD HANDS ITS ACCOUNT STORES TO ITS CONSOLE'S ROSTER LANE.")
        u1 = html.index("</script>", u0)
        return (b0, b1), (u0, u1)

    def test_no_screen_of_the_board_branches_on_the_shadow(self):
        html = _read(BIBLE)
        (b0, b1), (u0, u1) = self._spans(html)
        # A startup writer may refuse while a shadow is open. A draw still may not branch:
        # `if (window._tvdShadow) {}` inside a render stays a failure. The allowed lines only
        # return, or they skip a floor (`if (!window._tvdShadow)` / `|| window._tvdShadow`).
        guard = re.compile(r"if \(window\._tvdShadow\) return\b|if \(!window\._tvdShadow\b|\|\| window\._tvdShadow\)")
        outside = []
        allowed = []
        for m in re.finditer(r"_tvdShadow|tvd-shadow-snap", html):
            if b0 <= m.start() < b1 or u0 <= m.start() < u1:
                continue
            line_start = html.rfind("\n", 0, m.start()) + 1
            line = html[line_start:html.find("\n", m.start())]
            if guard.search(line):
                allowed.append(line.strip())
                continue
            outside.append(html.count("\n", 0, m.start()) + 1)
        self.assertEqual(outside, [], "bible.html draws something differently in shadow at line(s) %r - the shadow "
                                      "must render through the same templates as the console" % outside)
        self.assertGreaterEqual(len(allowed), 12, allowed)
        # REG-3113 - _flShadow refuses the same way _unconfReadOnly does (return true); v3864 - REG-3095's inShadow (the
        # D2JSP desk's read-only test) is the third. Each is named by the function it opens, never a running count (REG-3049).
        for fn in ("function _unconfReadOnly(){\n  if (window._tvdShadow) return true;",
                   "  function inShadow(){\n    if (window._tvdShadow) return true;",
                   "  function _flShadow(){\n    if (window._tvdShadow) return true;"):
            self.assertEqual(html.count(fn), 1, "a return-true shadow guard went missing or doubled: %r"
                             % fn.split("\n")[0].strip())
        self.assertEqual(sum(1 for a in allowed if a.startswith("if (window._tvdShadow) return true;")), 3,
                         "a return-true shadow guard that is none of the three named above")
        # v3864 (#233) - 27: main's v3856-v3859 shadow guards and the integration chain's (the D2JSP desk, the full-look
        # asks, the saves reason) met in one tree, every one of the allowed forms above. 28: v3864's war-mule prune
        # (_vaultWarAutoPrune, his ruling 2026-11-05 (d)) refuses in a shadow exactly as _vaultWarAutoMule does - a writer that
        # returns, never a draw that branches. A 29th is an edit here, on purpose.
        self.assertIn("  function _vaultWarAutoPrune(){\n    var gone = [];\n    if (window._tvdShadow) return { gone: gone,", html)
        self.assertLessEqual(len(allowed), 28, allowed)

    def test_the_shadow_frame_is_the_consoles_own_board_document(self):
        ui = _read(UI)
        enter = ui[ui.index("  window._shadowSnapEnter = function"):ui.index("  window._shadowOpen = function")]
        srcs = re.findall(r"f\.src = '([^']*)'", enter)
        self.assertEqual(srcs, ["/board?app=1&engine=1&tvd-shadow=1&v="], "the shadow is not the board the console "
                                                                           "pane loads: %r" % srcs)
        self.assertIn("<iframe id=\"tvd-eng\" src=\"/board?app=1&engine=1&", ui)

    def test_the_consoles_own_header_routes_the_shadow(self):
        ui = _read(UI)
        route = ui[ui.index("  function _shellRoute(tab){"):ui.index("  function _shellVeil(tab){")]
        self.assertIn("document.getElementById(_snap ? 'shadow-eng' : 'tvd-eng')", route)
        go = ui[ui.index("  function _headTabGo(e){"):ui.index("  if (_ht) {", ui.index("  function _headTabGo(e){"))]
        i = go.index("contains('shadow-on')")
        self.assertLess(i, go.index("shellHome()"), "TV·D leaves the shadow for this PC's own cockpit")
        self.assertLess(i, go.index("showSessions()"), "Sessions leaves the shadow for this PC's own hub")
        self.assertIn("shellOpen(b.dataset.tab);\n      return;", go[i:])
        branch = go[i:go.index("return;", i)]
        self.assertNotIn("removeAttribute('data-view')", branch,
                         "a shadow tab must not drop Sessions, or Leave comes back on STANDBY with ADVANCED open")

    def test_leave_puts_the_sessions_view_back_after_a_vault_tab(self):
        """A Vault tab inside a shadow used to drop data-view. Leave then lit the Sessions
        button over the standby stage, and the advanced drawer (hidden on Sessions) showed open."""
        if not NODE:
            raise AssertionError("node is absent - leave cannot be run here, so it is UNMEASURED")
        ui = _read(UI)
        self.assertEqual(ui.count("  window._shadowRemember = function () {"), 1)
        self.assertEqual(ui.count("  window._shadowLeave = function () {"), 1)
        remember = ui[ui.index("  window._shadowRemember = function () {"):ui.index("  window._shadowRosterStores = function")]
        leave = ui[ui.index("  window._shadowLeave = function () {"):ui.index("  /* The board frame holds focus.")]
        js = "var window = globalThis;\nvar _shadowGen = 0;\n" + remember + "\n" + leave + r"""
function box() {
  var attrs = {};
  return {
    open: false,
    dataset: {},
    classList: { remove: function () {}, contains: function () { return false; } },
    parentNode: null,
    contentWindow: null,
    setAttribute: function (k, v) { attrs[k] = String(v); },
    getAttribute: function (k) { return Object.prototype.hasOwnProperty.call(attrs, k) ? attrs[k] : null; },
    removeAttribute: function (k) { delete attrs[k]; },
    hasAttribute: function (k) { return Object.prototype.hasOwnProperty.call(attrs, k); }
  };
}
var ids = { 'sig-adv': box() };
var body = box();
body.dataset.shellTab = 'session';
var document = { body: body, getElementById: function (id) { return ids[id] || null; } };
window.location = { origin: 'http://console.local' };
var calls = { sessions: 0 };
window._showSessions = function () { calls.sessions++; body.setAttribute('data-view', 'sessions'); };
window._shellLight = function () {};
window._shellDemotePane = function () {};
window._shellRestoreConsole = function () {};
function play(strip) {
  var before = calls.sessions;
  body.setAttribute('data-shadow-shown', '1');
  window._shadowLeave();
  return {
    view: body.getAttribute('data-view'),
    sessions: calls.sessions - before,
    adv: ids['sig-adv'].open,
    shadowView: body.getAttribute('data-shadow-view'),
    shadowTab: body.getAttribute('data-shadow-tab'),
    shadowAdv: body.getAttribute('data-shadow-adv')
  };
}
body.setAttribute('data-view', 'sessions');
ids['sig-adv'].open = false;
window._shadowRemember();
body.removeAttribute('data-view');
ids['sig-adv'].open = true;
var vault = play(true);
body.setAttribute('data-view', 'sessions');
ids['sig-adv'].open = false;
window._shadowRemember();
var dean = play(false);
body.setAttribute('data-view', 'sessions');
ids['sig-adv'].open = true;
window._shadowRemember();
body.removeAttribute('data-view');
ids['sig-adv'].open = false;
var keptOpen = play(true);
body.setAttribute('data-view', 'sessions');
ids['sig-adv'].open = false;
window._shadowRemember();
body.setAttribute('data-view', 'other');
ids['sig-adv'].open = true;
window._shadowRemember();
body.removeAttribute('data-view');
var second = play(true);
process.stdout.write(JSON.stringify({ vault: vault, dean: dean, keptOpen: keptOpen, second: second }));
"""
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got["vault"], {"view": "sessions", "sessions": 1, "adv": False,
                                         "shadowView": None, "shadowTab": None, "shadowAdv": None}, got)
        self.assertEqual(got["dean"]["sessions"], 0, got)
        self.assertEqual(got["dean"]["view"], "sessions", got)
        self.assertIs(got["dean"]["adv"], False, got)
        self.assertIs(got["keptOpen"]["adv"], True, "Leave closed a drawer that was already open")
        self.assertEqual(got["keptOpen"]["view"], "sessions", got)
        self.assertEqual(got["second"], {"view": "sessions", "sessions": 1, "adv": False,
                                          "shadowView": None, "shadowTab": None, "shadowAdv": None}, got)

    def test_the_marker_names_the_owner_and_the_profile_time(self):
        ui = _read(UI)
        enter = ui[ui.index("  window._shadowSnapEnter = function"):ui.index("  window._shadowOpen = function")]
        # #214 - one clock: the date and a 24-hour HH:MM, as the header's clock
        self.assertIn("at = ' · snapshot ' + _sd.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + _p2(_sd.getHours())", enter)
        self.assertIn("who.textContent = String(d.words || owner) + at + ' · read only';", enter)
        self.assertIn('<div id="shadow-bar" hidden><span id="shadow-who">', ui)

    def test_leave_takes_a_click_while_the_board_covers_the_rail(self):
        """Leave sits in the rail. shell-open sets pointer-events:none on that rail, so the
        bar paints over the other profile and the click lands on the frame. The window close
        hides that same page, which is why a restart comes back still inside it."""
        ui = _read(UI)
        trap = ui.index("body.shell-open .shell > :not(.topbar)")
        exempt = ui.index("body.shell-open #shadow-bar", trap)
        block = ui[exempt:ui.index("body.shell-open .topbar", exempt)]
        self.assertIn("pointer-events: auto !important", block)
        self.assertIn("#shadow-bar *", block)
        leave = ui.index("window._shadowLeave = function () {")
        arm = ui[leave:ui.index("window._shadowSnapEnter = function", leave)]
        self.assertIn("getElementById('shadow-leave')", arm)
        self.assertIn("addEventListener('pointerdown'", arm)
        self.assertIn("e.button !== 0 || e.ctrlKey", arm)
        mark = ui.index("ev.data.type !== 'tvd-shadow-leave'")
        block = ui[ui.rindex("getElementById('shadow-eng')", 0, mark):ui.index("window._shadowSnapEnter = function", mark)]
        self.assertIn("ev.source !== f.contentWindow", block)
        self.assertIn("ev.origin !== window.location.origin", block)
        self.assertIn("window._shadowLeave()", block)


def _js_fn(src, start_needle):
    """The function whose text begins at a unique needle, braces and strings included."""
    if src.count(start_needle) != 1:
        raise AssertionError("anchor %r occurs %d times" % (start_needle, src.count(start_needle)))
    start = src.index(start_needle)
    i = src.index("{", start)
    depth = 0
    k = i
    n = len(src)
    while k < n:
        c = src[k]
        if c in ("'", '"', "`"):
            q = c
            k += 1
            while k < n:
                if src[k] == "\\":
                    k += 2
                    continue
                if src[k] == q:
                    k += 1
                    break
                k += 1
            continue
        if c == "/" and k + 1 < n and src[k + 1] == "/":
            nl = src.find("\n", k)
            k = n if nl < 0 else nl
            continue
        if c == "/" and k + 1 < n and src[k + 1] == "*":
            end = src.find("*/", k + 2)
            if end < 0:
                raise AssertionError("unclosed comment after %r" % start_needle)
            k = end + 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[start:k + 1]
        k += 1
    raise AssertionError("no end for %r" % start_needle)


class TheShadowSessionsHub(unittest.TestCase):
    """Sessions on this console is the hunt hub. The other header tabs open a board room, and a
    shadow of those tabs opens that same room. Sessions was the one tab that opened a different
    room. It now opens this same hub, read from their frame, and a click from the hub opens
    their board."""

    def test_the_session_tab_opens_the_hub_and_the_other_tabs_open_the_board(self):
        ui = _read(UI)
        go = ui[ui.index("  function _headTabGo(e){"):ui.index("  if (_ht) {", ui.index("  function _headTabGo(e){"))]
        i = go.index("contains('shadow-on')")
        branch = go[i:go.index("return;", i)]
        self.assertIn("b.dataset.tab === 'session'", branch)
        self.assertIn("showShadowSessions()", branch)
        self.assertNotIn("showSessions()", branch)
        self.assertNotIn("removeAttribute('data-view')", branch)
        self.assertIn("document.body.classList.remove('shadow-hub');\n      shellOpen(b.dataset.tab);\n      return;", go[i:])
        self.assertEqual(ui.count("      shellOpen(b.dataset.tab);\n      return;\n"), 1)
        fn = _js_fn(ui, "function showShadowSessions(){")
        for piece in ("getElementById('shadow-eng')", "_writeGrailFarm", "_writeSetFarm",
                      "setAttribute('data-view', 'sessions')", "classList.add('shadow-hub')",
                      "hubNextGrail()", "hubNextSet()", "hdForge()", "hdTaskForce(null)",
                      "_shellRestoreConsole()"):
            self.assertIn(piece, fn, piece)
        self.assertNotIn("showSessions()", fn)
        self.assertNotIn("removeAttribute('data-view')", fn)
        self.assertNotIn("classList.remove", fn)
        css = ui.index("body.shadow-hub:not(.shell-open) #shadow-eng")
        self.assertEqual(ui.count("body.shadow-hub:not(.shell-open) #shadow-eng"), 1)
        rule = ui[css:ui.index("}", css) + 1]
        self.assertIn("display: block !important", rule)
        self.assertIn("visibility: hidden !important", rule)
        self.assertNotIn("body.shadow-hub #shadow-eng {", ui)

    def test_the_hub_shows_a_published_chronicle_total_when_the_names_were_not_sent(self):
        ui = _read(UI)
        self.assertEqual(ui.count('id="hd-chron-counts"'), 1)
        forge = _js_fn(ui, "function hdForge(){")
        self.assertIn("_paintChronicle(summary)", forge)
        paint = _js_fn(ui, "function _paintChronicle(summary) {")
        self.assertIn("lsHub('d2r_shadowProgress')", paint)
        self.assertNotIn("lsFork(", paint)
        counts = _js_fn(ui, "function _chronicleCounts(summary, progress, lists) {")
        if not NODE:
            raise AssertionError("node is absent - the chronicle line cannot be run here, so it is UNMEASURED")
        js = counts + r"""
var named = _chronicleCounts({ chron: { made: 99, total: 99 }, sets: { found: 134, total: 135 }, grail: { found: 309, total: 403 } }, null);
var published = _chronicleCounts(null, { runewords: { have: 98, total: 99, listed: false }, sets: { have: 132, total: 135, listed: false }, uniques: { have: 0, total: 403, listed: false } });
var zero = _chronicleCounts(null, { runewords: { have: 0, total: 99, listed: false } });
var listed = _chronicleCounts(null, { runewords: { have: 98, total: 99, listed: true } });
var none = _chronicleCounts(null, null);
process.stdout.write(JSON.stringify({ named: named, published: published, zero: zero, listed: listed, none: none }));
"""
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        dot = " \u00b7 "
        self.assertEqual(got["named"], "Runewords 99/99" + dot + "Sets 134/135" + dot + "Uniques 309/403")
        self.assertEqual(got["published"], "Runewords 98/99" + dot + "Sets 132/135" + dot + "the list wasn\u2019t sent")
        self.assertNotIn("0/", got["published"])
        self.assertEqual(got["zero"], "the list wasn\u2019t sent")
        self.assertNotIn("0/", got["zero"])
        self.assertEqual(got["listed"], "")
        self.assertEqual(got["none"], "")

    def test_a_zero_summary_never_hides_a_sent_list_or_a_published_total(self):
        """A shadow forge summary can read 0/99 while that PC's list, or its published total, is real.

        The line uses the sent names, then the published total. It never paints 0.
        """
        if not NODE:
            raise AssertionError("node is absent - the zero summary cannot be run here, so it is UNMEASURED")
        ui = _read(UI)
        paint = _js_fn(ui, "function _paintChronicle(summary) {")
        for key in ("lsHub('d2r_rwMade')", "lsHub('d2r_setPieces')", "lsHub('d2r_foundLog')",
                    "lsHub('d2r_shadowProgress')"):
            self.assertIn(key, paint, key)
        self.assertNotIn("lsFork(", paint)
        count = _js_fn(ui, "function _listCount(raw) {")
        counts = _js_fn(ui, "function _chronicleCounts(summary, progress, lists) {")
        zero = ("{ chron: { made: 0, total: 99 }, sets: { found: 0, total: 135 }, "
                "grail: { found: 0, total: 403 } }")
        js = count + "\n" + counts + "\n" + paint + r"""
var dot = ' \u00b7 ';
var zero = """ + zero + r""";
var listed = _chronicleCounts(zero, {
  runewords: { have: 1, total: 99, listed: false },
  sets: { have: 1, total: 135, listed: false },
  uniques: { have: 1, total: 403, listed: false }
}, { runewords: 99, sets: 135, uniques: 332 });
var published = _chronicleCounts(zero, {
  runewords: { have: 99, total: 99, listed: false },
  sets: { have: 135, total: 135, listed: false },
  uniques: { have: 332, total: 403, listed: false }
}, null);
var none = _chronicleCounts(zero, {
  runewords: { have: 0, total: 99, listed: false },
  sets: { have: 0, total: 135, listed: false },
  uniques: { have: 0, total: 403, listed: false }
}, null);
var scanned = _chronicleCounts({ chron: { made: 99, total: 99 }, sets: { found: 135, total: 135 }, grail: { found: 332, total: 403 } }, null, { runewords: 1, sets: 1, uniques: 1 });
var el = { textContent: '' };
var store = {};
function lsHub(k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; }
var document = { getElementById: function (id) { return id === 'hd-chron-counts' ? el : null; } };
function names(n) {
  var o = {};
  for (var i = 0; i < n; i++) o['n' + i] = '';
  return JSON.stringify(o);
}
store.d2r_rwMade = names(99);
store.d2r_setPieces = JSON.stringify(['a', 'b', 'c']);
store.d2r_foundLog = names(332);
_paintChronicle(zero);
var paintedLists = el.textContent;
store = { d2r_shadowProgress: JSON.stringify({
  runewords: { have: 99, total: 99, listed: false },
  sets: { have: 135, total: 135, listed: false },
  uniques: { have: 332, total: 403, listed: false }
}) };
_paintChronicle(zero);
var paintedPublished = el.textContent;
process.stdout.write(JSON.stringify({
  listed: listed, published: published, none: none, scanned: scanned,
  paintedLists: paintedLists, paintedPublished: paintedPublished
}));
"""
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        dot = " \u00b7 "
        mac = "Runewords 99/99" + dot + "Sets 135/135" + dot + "Uniques 332/403"
        self.assertEqual(got["listed"], "Runewords 99/99" + dot + "Sets 135/135" + dot + "Uniques 332/403")
        self.assertEqual(got["published"], mac)
        self.assertEqual(got["none"], "the list wasn\u2019t sent")
        self.assertEqual(got["scanned"], mac)
        self.assertEqual(got["paintedLists"], "Runewords 99/99" + dot + "Sets 3/135" + dot + "Uniques 332/403")
        self.assertEqual(got["paintedPublished"], mac)
        for key in ("listed", "published", "none", "scanned", "paintedLists", "paintedPublished"):
            self.assertNotIn("0/", got[key], key)

    def test_a_shadow_hub_counts_that_pc_and_not_the_found_log_length(self):
        """A shadow line counts that PC. The found log is longer than the chronicle.

        400 unique names beside a published 332 must paint 332, the number the pages
        already show. The found-log length is not a uniques count. A PC that sent no
        names keeps its published totals. have 0 stays the sentence and never paints 0.
        This PC's own forge summary must not appear on the line.
        """
        if not NODE:
            raise AssertionError("node is absent - the shadow chronicle line cannot be run here, so it is UNMEASURED")
        ui = _read(UI)
        roster = ui[ui.index("  window._shadowRosterStores = function (row, fleet, owner) {"):ui.index("  window._shadowEnter = function (owner) {")]
        count = _js_fn(ui, "function _listCount(raw) {")
        counts = _js_fn(ui, "function _chronicleCounts(summary, progress, lists) {")
        paint = _js_fn(ui, "function _paintChronicle(summary) {")
        forge = _js_fn(ui, "function hdForge(){")
        js = "var window = globalThis;\nvar _hdForgeSig = '';\n" + roster + "\n" + count + "\n" + counts + "\n" + paint + "\n" + forge + r"""
window._fleetRosterOwner = function (m) {
  var nick = String((m && m.nickname) || '').trim();
  if (nick === 'Mac') return 'Mac';
  if (nick === 'Alt') return 'Alt';
  if (nick === 'Dean') return 'Dean';
  return '';
};
function rows(lane, n) {
  var out = [];
  for (var i = 0; i < n; i++) out.push({ lane: lane, name: lane + '-' + i });
  return out;
}
function row(counts, nameRows) {
  var chron = { counts: counts };
  if (nameRows) chron.rows = nameRows;
  return { published: true, sections: { chronicle: chron } };
}
var fleet = { me: 'viewer', offline: [
  { nickname: 'Mac', platform: 'mac', machine: 'mac-host' },
  { nickname: 'Alt', platform: 'windows', machine: 'alt-host' },
  { nickname: 'Dean', platform: 'windows', machine: 'dean-host' }
]};
var macBuilt = window._shadowRosterStores(row({
  runewords: { have: 99, total: 99 },
  sets: { have: 135, total: 135 },
  uniques: { have: 332, total: 403 }
}, rows('runewords', 99).concat(rows('sets', 135), rows('uniques', 400))), fleet, 'Mac');
var altBuilt = window._shadowRosterStores(row({
  runewords: { have: 0, total: 99 },
  sets: { have: 4, total: 135 },
  uniques: { have: 52, total: 403 }
}, null), fleet, 'Alt');
var deanBuilt = window._shadowRosterStores(row({
  runewords: { have: 98, total: 99 },
  sets: { have: 132, total: 135 },
  uniques: { have: 0, total: 403 }
}, null), fleet, 'Dean');
var el = { textContent: '' };
var chips = { innerHTML: '' };
var when = { textContent: '' };
var hostReads = 0;
function lsHub() { hostReads++; return JSON.stringify({ chron: { made: 7, total: 99 } }); }
var classes = { 'shadow-hub': true };
var document = {
  body: { classList: { contains: function (c) { return !!classes[c]; } } },
  getElementById: function (id) {
    if (id === 'hd-chron-counts') return el;
    if (id === 'hd-forge-chips') return chips;
    if (id === 'hd-forge-when') return when;
    return null;
  }
};
var hostSummary = { chron: { made: 7, total: 99 }, sets: { found: 7, total: 135 }, grail: { found: 7, total: 403 } };
function paintOf(built) {
  window._tvdShadowSnap = { stores: built.stores };
  el.textContent = '';
  chips.innerHTML = 'stale';
  _hdForgeSig = 'stale';
  hdForge();
  return { line: el.textContent, chips: chips.innerHTML };
}
var macPaint = paintOf(macBuilt);
var altPaint = paintOf(altBuilt);
var deanPaint = paintOf(deanBuilt);
window._tvdShadowSnap = null;
el.textContent = '';
chips.innerHTML = 'stale';
_hdForgeSig = 'stale';
hdForge();
var noSnap = el.textContent;
var noSnapChips = chips.innerHTML;
var macFound = macBuilt.stores.d2r_foundLog ? Object.keys(JSON.parse(macBuilt.stores.d2r_foundLog)).length : 0;
var macProg = macBuilt.stores.d2r_shadowProgress ? JSON.parse(macBuilt.stores.d2r_shadowProgress) : null;
process.stdout.write(JSON.stringify({
  macFound: macFound,
  macProg: macProg,
  macLine: macPaint.line,
  altLine: altPaint.line,
  deanLine: deanPaint.line,
  macChips: macPaint.chips,
  altChips: altPaint.chips,
  noSnap: noSnap,
  noSnapChips: noSnapChips,
  hostReads: hostReads
}));
"""
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        dot = " \u00b7 "
        mac = "Runewords 99/99" + dot + "Sets 135/135" + dot + "Uniques 332/403"
        self.assertEqual(got["macFound"], 400, got)
        self.assertEqual(got["macProg"], {
            "runewords": {"have": 99, "total": 99, "listed": True},
            "sets": {"have": 135, "total": 135, "listed": True},
            "uniques": {"have": 332, "total": 403, "listed": True},
        }, got)
        self.assertEqual(got["macLine"], mac, got)
        self.assertNotIn("400/", got["macLine"], got)
        self.assertEqual(got["macChips"], "", got)
        self.assertEqual(got["altLine"], "Sets 4/135" + dot + "Uniques 52/403" + dot + "the list wasn\u2019t sent", got)
        self.assertEqual(got["altChips"], "", got)
        self.assertEqual(got["deanLine"], "Runewords 98/99" + dot + "Sets 132/135" + dot + "the list wasn\u2019t sent", got)
        self.assertNotIn("7/", got["macLine"] + got["altLine"] + got["deanLine"] + got["noSnap"], got)
        self.assertNotIn("0/", got["macLine"] + got["altLine"] + got["deanLine"] + got["noSnap"], got)
        self.assertEqual(got["hostReads"], 0, got)
        self.assertEqual(got["noSnap"], "", got)
        self.assertIn("the list wasn\u2019t sent", got["noSnapChips"], got)

    def test_a_sent_unique_list_counts_when_the_published_have_is_zero(self):
        """Dean sent 132 unique names and a published have of 0. The line counts 132.

        Mac's found log is longer than the published 332, so 332 stays. The missing-list
        sentence stays on the chips only when the chronicle line itself was not sent.
        """
        if not NODE:
            raise AssertionError("node is absent - the sent unique list cannot be run here, so it is UNMEASURED")
        ui = _read(UI)
        roster = ui[ui.index("  window._shadowRosterStores = function (row, fleet, owner) {"):ui.index("  window._shadowEnter = function (owner) {")]
        count = _js_fn(ui, "function _listCount(raw) {")
        counts = _js_fn(ui, "function _chronicleCounts(summary, progress, lists) {")
        paint = _js_fn(ui, "function _paintChronicle(summary) {")
        forge = _js_fn(ui, "function hdForge(){")
        task = ui[ui.index("function hdTaskForce(st){"):ui.index("function _watchdogCountSay(n){")]
        self.assertEqual(task.count("function _shadowTodayUnsent(line)"), 1)
        self.assertEqual(task.count("if (_onShadowHub && _shadowTodayUnsent("), 1)
        self.assertIn("the list wasn\\u2019t sent", task)
        pred = task[task.index("function _shadowTodayUnsent(line)"):task.index("if (_onShadowHub && _shadowTodayUnsent(")]
        js = "var window = globalThis;\nvar _hdForgeSig = '';\n" + roster + "\n" + count + "\n" + counts + "\n" + paint + "\n" + forge + "\n" + pred + r"""
window._fleetRosterOwner = function (m) {
  var nick = String((m && m.nickname) || '').trim();
  if (nick === 'Mac') return 'Mac';
  if (nick === 'Dean') return 'Dean';
  return '';
};
function rows(lane, n) {
  var out = [];
  for (var i = 0; i < n; i++) out.push({ lane: lane, name: lane + '-' + i });
  return out;
}
function row(counts, nameRows) {
  var chron = { counts: counts };
  if (nameRows) chron.rows = nameRows;
  return { published: true, sections: { chronicle: chron } };
}
var fleet = { me: 'viewer', offline: [
  { nickname: 'Mac', platform: 'mac', machine: 'mac-host' },
  { nickname: 'Dean', platform: 'windows', machine: 'dean-host' }
]};
var macBuilt = window._shadowRosterStores(row({
  runewords: { have: 99, total: 99 },
  sets: { have: 135, total: 135 },
  uniques: { have: 332, total: 403 }
}, rows('uniques', 400)), fleet, 'Mac');
var deanBuilt = window._shadowRosterStores(row({
  runewords: { have: 98, total: 99 },
  sets: { have: 132, total: 135 },
  uniques: { have: 0, total: 403 }
}, rows('uniques', 132)), fleet, 'Dean');
var el = { textContent: '' };
var chips = { innerHTML: '' };
var when = { textContent: '' };
var classes = { 'shadow-hub': true };
var document = {
  body: { classList: { contains: function (c) { return !!classes[c]; } } },
  getElementById: function (id) {
    if (id === 'hd-chron-counts') return el;
    if (id === 'hd-forge-chips') return chips;
    if (id === 'hd-forge-when') return when;
    return null;
  }
};
function paintOf(built) {
  window._tvdShadowSnap = { stores: built.stores };
  el.textContent = '';
  chips.innerHTML = 'stale';
  _hdForgeSig = 'stale';
  hdForge();
  return { line: el.textContent, chips: chips.innerHTML };
}
var macPaint = paintOf(macBuilt);
var deanPaint = paintOf(deanBuilt);
var sentence = 'the list wasn\u2019t sent';
var both = 'Runewords 98/99 \u00b7 ' + sentence;
console.log(JSON.stringify({
  macLine: macPaint.line,
  deanLine: deanPaint.line,
  deanChips: deanPaint.chips,
  empty: _shadowTodayUnsent(''),
  only: _shadowTodayUnsent(sentence),
  counts: _shadowTodayUnsent('Runewords 99/99'),
  both: _shadowTodayUnsent(both)
}));
"""
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        dot = " \u00b7 "
        self.assertEqual(got["macLine"], "Runewords 99/99" + dot + "Sets 135/135" + dot + "Uniques 332/403", got)
        self.assertNotIn("400/", got["macLine"])
        self.assertEqual(got["deanLine"], "Runewords 98/99" + dot + "Sets 132/135" + dot + "Uniques 132/403", got)
        self.assertNotIn("the list wasn\u2019t sent", got["deanLine"])
        self.assertNotIn("0/", got["deanLine"])
        self.assertEqual(got["deanChips"], "", got)
        self.assertTrue(got["empty"])
        self.assertTrue(got["only"])
        self.assertFalse(got["counts"])
        self.assertFalse(got["both"])

    def test_the_hub_reads_the_frame_and_never_this_pc(self):
        if not NODE:
            raise AssertionError("node is absent - the hub reader cannot be run here, so it is UNMEASURED")
        ui = _read(UI)
        fork = _js_fn(ui, "function lsFork(bare){")
        hub = _js_fn(ui, "function lsHub(bare){")
        self.assertNotIn("function lsHub", fork)
        board = _js_fn(ui, "function _hubBoard(){")
        tz = _js_fn(ui, "window._tzRoute = function () {")
        grail = _js_fn(ui, "async function hubNextGrail(){")
        sets = _js_fn(ui, "async function hubNextSet(){")
        forge = _js_fn(ui, "function hdForge(){")
        self.assertIn("lsHub('d2r_grailFarm')", grail)
        self.assertNotIn("lsFork(", grail)
        self.assertIn("lsHub('d2r_setFarm')", sets)
        self.assertNotIn("lsFork(", sets)
        self.assertIn("lsHub('d2r_forgeSummary')", forge)
        self.assertIn("lsHub('d2r_craftReady')", forge)
        self.assertIn("the list wasn\\u2019t sent", forge)
        task = ui[ui.index("function hdTaskForce(st){"):ui.index("function _watchdogCountSay(n){")]
        self.assertIn("lsHub('d2r_forgeSummary')", task)
        self.assertIn("lsHub('d2r_createNowAi')", task)
        self.assertIn("if (!_onShadowHub)", task)
        self.assertIn("the list wasn\\u2019t sent", task)
        self.assertLess(task.index("if (!_onShadowHub)"), task.index("lsFork('d2r_tvdTallyLog')"))
        js = "var window = globalThis;\n" + fork + "\n" + hub + "\n" + board + "\n" + tz + r"""
function mem(seed) {
  var d = {};
  Object.keys(seed || {}).forEach(function (k) { d[k] = seed[k]; });
  return { getItem: function (k) { return Object.prototype.hasOwnProperty.call(d, k) ? d[k] : null; } };
}
function route(owner, prof) {
  return { v: 2, owner: owner, id: 'abcd1234efgh', m: owner ? 'owner' : 'guest', p: prof,
           pfx: owner ? '' : 'I\u00b7abcd1234\u00b7', lpfx: owner ? 'L\u00b7' : 'IL\u00b7abcd1234\u00b7',
           lp: ['d2r_grailFarm'], wp: ['d2r_grailFarm'] };
}
var classes = {};
var frameLS = null;
var frameMissing = false;
var frameDoc = null;
var document = {
  body: { classList: { contains: function (c) { return !!classes[c]; } } },
  getElementById: function (id) {
    asked.push(id);
    if (id === 'shadow-eng') {
      if (frameMissing) return null;
      return { id: id, contentWindow: { localStorage: frameLS }, contentDocument: frameDoc };
    }
    return { id: id };
  }
};
var localStorage = mem({});
var asked = [];
function arm(parentSeed, frameSeed, on) {
  localStorage = mem(parentSeed);
  frameLS = mem(frameSeed);
  frameMissing = false;
  frameDoc = null;
  window._tvdShadowSnap = null;
  classes = on ? { 'shadow-hub': true, 'shadow-snap': true } : {};
  asked = [];
}
var macRoute = JSON.stringify(route(true, 'main'));
var out = {};
arm({ d2r_lsrRoute: macRoute, 'd2r_grailFarm': 'mac-farm' },
    { d2r_lsrRoute: JSON.stringify(route(true, 'ladder')), 'L\u00b7d2r_grailFarm': 'alt-farm', 'd2r_grailFarm': 'mac-farm' },
    false);
out.off = lsHub('d2r_grailFarm');
arm({ d2r_lsrRoute: macRoute, 'd2r_grailFarm': 'mac-farm' },
    { d2r_lsrRoute: JSON.stringify(route(true, 'ladder')), 'L\u00b7d2r_grailFarm': 'alt-farm', 'd2r_grailFarm': 'mac-farm' },
    true);
out.ladder = lsHub('d2r_grailFarm');
arm({ d2r_lsrRoute: macRoute, 'd2r_grailFarm': 'mac-farm' },
    { d2r_lsrRoute: JSON.stringify(route(false, 'main')), 'I\u00b7abcd1234\u00b7d2r_grailFarm': 'guest-farm', 'd2r_grailFarm': 'mac-farm' },
    true);
out.guest = lsHub('d2r_grailFarm');
arm({ d2r_lsrRoute: macRoute, 'd2r_grailFarm': 'mac-farm' }, { 'd2r_grailFarm': 'mac-farm' }, true);
out.noRoute = lsHub('d2r_grailFarm');
arm({ d2r_lsrRoute: macRoute, 'd2r_grailFarm': 'mac-farm' }, {}, true);
frameMissing = true;
out.noFrame = lsHub('d2r_grailFarm');
frameMissing = false;
classes = { 'shadow-on': true, 'shadow-snap': true };
frameDoc = null;
frameLS = mem({ d2r_lsrRoute: JSON.stringify(route(true, 'main')), 'd2r_grailFarm': 'their-farm' });
localStorage = mem({ 'd2r_grailFarm': 'viewer-farm' });
window._tvdShadowSnap = null;
out.tab = lsHub('d2r_grailFarm');
frameDoc = { documentElement: { classList: { contains: function () { return false; } } } };
frameLS = mem({ 'd2r_grailFarm': 'viewer-in-frame' });
out.unshimmed = lsHub('d2r_grailFarm');
window._tvdShadowSnap = { stores: { d2r_grailFarm: 'profile-farm' } };
out.snap = lsHub('d2r_grailFarm');
window._tvdShadowSnap = null;
frameDoc = { documentElement: { classList: { contains: function (c) { return c === 'tvd-shadow'; } } } };
frameLS = mem({ d2r_lsrRoute: JSON.stringify(route(true, 'main')), 'd2r_grailFarm': 'their-farm' });
classes = { 'shadow-on': true };
out.shimmedTab = lsHub('d2r_grailFarm');
classes = { 'shadow-snap': true };
asked = [];
var snapHit = _hubBoard().id;
var snapAsked = asked.slice();
classes = {};
asked = [];
var ownHit = _hubBoard().id;
var ownAsked = asked.slice();
var opened = [], shelled = [];
window.open = function (u) { opened.push(u); };
window._shellOpen = function (t) { shelled.push(t); };
classes = { 'shadow-snap': true };
window._tzRoute();
out.tzShadow = { opened: opened.slice(), shelled: shelled.slice() };
opened = []; shelled = [];
classes = {};
window._tzRoute();
out.tzOwn = { opened: opened.slice(), shelled: shelled.slice() };
out.board = { snapHit: snapHit, snapAsked: snapAsked, ownHit: ownHit, ownAsked: ownAsked };
process.stdout.write(JSON.stringify(out));
"""
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertIn("cl.contains('shadow-on')", hub)
        self.assertIn("tvd-shadow", hub)
        self.assertLess(hub.index("cl.contains('shadow-on')"), hub.index("return lsFork(bare)"))
        self.assertEqual(got["off"], "mac-farm", got)
        self.assertEqual(got["ladder"], "alt-farm", got)
        self.assertEqual(got["tab"], "their-farm", got)
        self.assertIsNone(got["unshimmed"], got)
        self.assertEqual(got["snap"], "profile-farm", got)
        self.assertEqual(got["shimmedTab"], "their-farm", got)
        self.assertEqual(got["guest"], "guest-farm", got)
        self.assertIsNone(got["noRoute"], got)
        self.assertIsNone(got["noFrame"], got)
        self.assertEqual(got["board"]["snapHit"], "shadow-eng", got)
        self.assertEqual(got["board"]["snapAsked"], ["shadow-eng"], got)
        self.assertEqual(got["board"]["ownHit"], "tvd-eng", got)
        self.assertEqual(got["board"]["ownAsked"], ["tvd-eng"], got)
        self.assertEqual(got["tzShadow"], {"opened": [], "shelled": ["tztracker"]}, got)
        self.assertEqual(got["tzOwn"], {"opened": ["/board#tztracker"], "shelled": []}, got)

    def test_leave_repaints_this_pc_after_the_shadow_hub(self):
        if not NODE:
            raise AssertionError("node is absent - leave cannot be run here, so it is UNMEASURED")
        ui = _read(UI)
        leave = ui[ui.index("  window._shadowLeave = function () {"):ui.index("  /* The board frame holds focus.")]
        self.assertLess(leave.index("classList.remove('shadow-on', 'shadow-snap', 'shadow-hub')"),
                        leave.index("_hubRepaintOwn()"))
        self.assertLess(leave.index("removeAttribute('data-shadow-hub')"), leave.index("_hubRepaintOwn()"))
        js = "var window = globalThis;\nvar _shadowGen = 0;\n" + leave + r"""
var classes = { 'shadow-on': true, 'shadow-snap': true, 'shadow-hub': true };
var attrs = { 'data-shadow-hub': '1', 'data-view': 'sessions' };
var removed = [];
var body = {
  classList: {
    remove: function () { for (var i = 0; i < arguments.length; i++) { removed.push(arguments[i]); delete classes[arguments[i]]; } },
    contains: function (c) { return !!classes[c]; }
  },
  setAttribute: function (k, v) { attrs[k] = String(v); },
  getAttribute: function (k) { return Object.prototype.hasOwnProperty.call(attrs, k) ? attrs[k] : null; },
  removeAttribute: function (k) { delete attrs[k]; }
};
var document = { body: body, getElementById: function () { return null; } };
window.location = { origin: 'http://console.local' };
var saw = { sessions: 0, repaint: 0, hubOn: null };
window._showSessions = function () { saw.sessions++; };
window._hubRepaintOwn = function () { saw.repaint++; saw.hubOn = !!classes['shadow-hub']; };
window._shadowLeave();
process.stdout.write(JSON.stringify({ saw: saw, removed: removed, view: body.getAttribute('data-view'), hub: body.getAttribute('data-shadow-hub') }));
"""
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got["saw"]["sessions"], 0, got)
        self.assertEqual(got["saw"]["repaint"], 1, got)
        self.assertIs(got["saw"]["hubOn"], False, got)
        self.assertIn("shadow-hub", got["removed"], got)
        self.assertEqual(got["view"], "sessions", got)
        self.assertIsNone(got["hub"], got)


# The boot block of bible.html, run in node on fake window/document objects: the page's own script.
_BOOT = r"""
const fs = require('fs');
const CFG = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const html = fs.readFileSync(CFG.bible, 'utf8');
const at = html.indexOf('/* SHADOW MODE BOOT');
const s0 = html.lastIndexOf('<script>', at) + 8, s1 = html.indexOf('</script>', at);
const code = html.slice(s0, s1);
const listeners = {};
const realLS = { setItem() { throw new Error('real localStorage touched'); }, getItem() { throw new Error('real localStorage read'); } };
const sent = [];
class Resp { constructor(b, o) { this.body = b; this.status = (o && o.status) || 200; } async json() { return JSON.parse(this.body); } async text() { return this.body; } }
const doc = { readyState: 'loading', documentElement: { classList: { list: [], add(c) { this.list.push(c); } } }, head: { appendChild() {} },
  createElement() { return { textContent: '' }; }, write(t) { out.wrote = t; },
  addEventListener(t, f, cap) { (listeners[t] = listeners[t] || []).push(f); } };
const out = { wrote: null, leaves: [] };
function run(parentSnap, search) {
  const host = { _tvdShadowSnap: parentSnap, postMessage(msg) { out.leaves.push(msg && msg.type); } };
  const win = { location: { search: search, href: 'http://127.0.0.1/board' + search, origin: 'http://127.0.0.1' },
    parent: parentSnap === undefined ? null : host,
    fetch: (u, i) => { sent.push([String(u), (i && i.method) || 'GET']); return Promise.resolve(new Resp('{}')); },
    stop() { out.stopped = true; }, open() { sent.push(['open']); } };
  win.parent = win.parent || win;
  Object.defineProperty(win, 'localStorage', { configurable: true, get: () => realLS });
  Object.defineProperty(win, 'sessionStorage', { configurable: true, get: () => realLS });
  const XHR = function () {}; XHR.prototype.open = function () {}; XHR.prototype.send = function () { sent.push(['xhr']); };
  const nav = { sendBeacon() { sent.push(['beacon']); return true; } };
  const f = new Function('window', 'document', 'localStorage', 'XMLHttpRequest', 'navigator', 'Response', 'URL',
                         'with (window) {' + code + '}');
  let threw = null;
  try { f(win, doc, undefined, XHR, nav, Resp, URL); } catch (e) { threw = String(e.message || e); }
  return { win, threw, XHR, nav };
}
(async () => {
  const res = {};
  const off = run(undefined, '');
  res.offUntouched = off.threw === null && !off.win._tvdShadow;
  const closed = run({ owner: 'Dean' }, '?tvd-shadow=1');
  res.closedThrew = closed.threw; res.closedStopped = !!out.stopped; res.closedWrote = out.wrote;
  out.stopped = false;
  const r = run(CFG.snap, '?app=1&tvd-shadow=1');
  const w = r.win;
  res.threw = r.threw;
  res.memIsLocal = w.localStorage !== realLS && w.sessionStorage !== realLS;
  res.seeded = {}; for (const k of Object.keys(CFG.snap.stores)) res.seeded[k] = w.localStorage.getItem(k);
  w.localStorage.setItem('d2r_written', '1');
  w.sessionStorage.setItem('x', '1');
  res.written = w.localStorage.getItem('d2r_written');
  res.sessWritten = w.sessionStorage.getItem('x');
  const keepK = Object.keys(CFG.snap.stores)[0];
  w.localStorage.removeItem(keepK);
  res.keptKey = keepK;
  res.kept = w.localStorage.getItem(keepK);
  res.claim = w.localStorage.getItem('d2r_ownerClaim');
  res.install = w.localStorage.getItem('d2r_installId');
  const asks = [['/api/chars_learned', 'GET'], ['/api/main_locks', 'GET'], ['/api/status', 'GET'],
                ['/api/roster-book', 'POST'], ['/assets/x.png', 'POST'], ['http://evil.example/api/x', 'GET'],
                ['/api/chars_learned', 'POST'], ['/fonts/a.woff2', 'GET'],
                ['/api/d2jsp_login', 'GET']];   /* REG-3380 (v3883) - LAST, so every index above stays as it was */
  res.answers = [];
  for (const [u, m] of asks) { const resp = await w.fetch(u, { method: m }); res.answers.push(await resp.text()); }
  // GrokBot bug 5: the viewer's own capture agent (another origin) and the agent's paths here never answer a shadow
  res.agent = [];
  for (const u of ['http://127.0.0.1:17771/ping', 'http://127.0.0.1:17771/state', '/state', '/frame?id=f_1', '/hist/a.jpg']) {
    const resp = await w.fetch(u); res.agent.push(resp.status);
  }
  const x = new r.XHR(); x.open('POST', '/api/vault'); x.send();
  r.nav.sendBeacon('/api/x', '1');
  w.open('/x');
  res.sent = sent;
  res.refused = w._tvdShadowRefused;
  res.indexedDB = typeof w.indexedDB;
  res.cls = doc.documentElement.classList.list.slice();
  w._tvdBookPost = function () { sent.push(['book']); };
  w._tvdBookPost();
  // the click veil: a write button is stopped, a VIEW control and a plain tab pass
  const mk = (onclick, cls, inSummary) => ({ getAttribute: (n) => (n === 'onclick' ? onclick : null),
    matches(sel) { return cls === 'tab' && sel.indexOf('.tab') === 0; },
    closest(sel) { if (sel.indexOf('.tab') === 0) return (cls === 'tab' || inSummary) ? this : null; return this; } });
  const fire = (el) => { let stopped = false; const ev = { target: { closest: (sel) => el.closest(sel) },
    preventDefault() {}, stopImmediatePropagation() { stopped = true; } };
    for (const f of listeners.click || []) f(ev); return stopped; };
  res.veil = { del: fire(mk("_cbDelete('bx1')")), set: fire(mk('_cbMainSet(1)')), open: fire(mk("openCharBuilder('bx1')")),
               mule: fire(mk("window.openMuleCard('fx-a')")), tab: fire(mk(null, 'tab')),
               tasks: fire(mk("window.vaultTasksTog()")), adv: fire(mk("window.vaultAdvTab('ledger')")),
               inSummary: fire(mk("_cbDelete('bx1')", null, true)),
               task: fire(mk("window._vaultTaskExpand('Shako',0,this)")) };
  // GrokBot bugs 2+3 (2026-10-27): the in-page view links and the Tools chips, in the shapes the page writes them
  res.links = { runs: fire(mk("window.funiSetFilter('runs')")), sets: fire(mk("window.fsetsSetFilter('runs')")),
                recipe: fire(mk("window.forgeSetFilter&&window.forgeSetFilter('crafts');try{window.forgeCraftToggle&&window.forgeCraftToggle('blood')}catch(e){}")),
                legend: fire(mk("window.forgeLegendToggle()")), tool: fire(mk("window._toolJump('gem-stash-card')")),
                hist: fire(mk("window._tvdHistTab('last')")),
                fold: fire(mk("window.toggleCardCollapse('smart-insights-card'); window.renderSmartInsights&&window.renderSmartInsights();")),
                gotBase: fire(mk("window.forgeGotBase(this,'Spirit','Monarch',4)")),
                // REG-2860 - the Vault guide's orb, its steps and its show-me spots, in the shapes the guide writes them
                guide: fire(mk("window.vaultGuideTog()")), guideGo: fire(mk("window.vaultGuideGo(2)")),
                guideShow: fire(mk("window.vaultGuideGo('shelf')")) };
  const claimEl = { id: 'claim-btn', getAttribute() { return null; }, matches() { return false; },
    closest(sel) { return String(sel).indexOf('#claim') !== -1 ? this : null; } };
  res.claimStopped = fire(claimEl);
  const key = (k, extra) => { const ev = Object.assign({ key: k, target: { tagName: 'DIV' }, preventDefault() {},
    stopImmediatePropagation() { this.stopped = true; } }, extra || {}); for (const f of listeners.keydown || []) f(ev);
    return !!ev.stopped; };
  res.typing = key('a', { target: { tagName: 'INPUT' } });
  out.leaves = [];
  res.keys = { Delete: key('Delete'), z: key('z', { ctrlKey: true }), Enter: key('Enter'), ArrowDown: key('ArrowDown'),
               PageDown: key('PageDown'), Escape: key('Escape'), copy: key('c', { metaKey: true }), Tab: key('Tab'),
               // REG-2758 - Enter/Space on the focused view control opens what a click opens; on a write control, or
               // with a modifier, it is still stopped
               taskEnter: key('Enter', { target: mk("window._vaultTaskExpand('Shako',0,this)") }),
               taskSpace: key(' ', { target: mk("window._vaultTaskExpand('Shako',0,this)") }),
               taskCtrl: key('Enter', { ctrlKey: true, target: mk("window._vaultTaskExpand('Shako',0,this)") }),
               delEnter: key('Enter', { target: mk("_cbDelete('bx1')") }) };
  res.leaveOnEscape = out.leaves.slice();
  res.blocks = ['change', 'input', 'submit', 'drop', 'paste', 'dragstart', 'contextmenu', 'pointerdown', 'keypress', 'keyup'].filter((t) => (listeners[t] || []).length);
  // the viewer's console is out of reach by name, and the real storage cannot be put back
  res.parentSealed = w.parent === w && w.frameElement === null;
  res.reopen = [];
  for (const n of ['localStorage', 'indexedDB', 'parent']) {
    try { Object.defineProperty(w, n, { configurable: true, get: () => realLS }); res.reopen.push(n); } catch (e) {}
  }
  // THEIR WORLD: a Windows cousin on ladder with its own ledger, drawn by a Mac viewer
  const bare = Object.assign({}, CFG.snap.stores); delete bare.d2r_api_world;
  const before = run(Object.assign({}, CFG.snap, { stores: bare }), '?tvd-shadow=1').threw;
  const full = { machine: 'windows', profile: 'ladder', os: 'WINDOWS', ledger: 'Dean ledger', cousin: true };
  res.partial = [{ machine: 'windows' }, {}, Object.assign({}, full, { cousin: 1 }), Object.assign({}, full, { os: 'BeOS' }),
                 Object.assign({}, full, { ledger: null })].map((pw) =>
    run(Object.assign({}, CFG.snap, { stores: Object.assign({}, CFG.snap.stores, { d2r_api_world: JSON.stringify(pw) }) }),
        '?tvd-shadow=1').threw);
  const theirs = Object.assign({}, CFG.snap.stores, { d2r_api_world: JSON.stringify(
    { machine: 'windows', profile: 'ladder', os: 'WINDOWS', ledger: 'Dean ledger', cousin: true }) });
  const t = run(Object.assign({}, CFG.snap, { stores: theirs }), '?tvd-shadow=1').win;
  t.D2R_MACHINE = 'mac'; t.D2R_HOST_OS = 'MAC'; t.D2R_PROFILE = 'main'; t._D2R_LEDGER = 'KonyoEndgame'; t._isCousinShell = false;
  res.world = { machine: t.D2R_MACHINE, os: t.D2R_HOST_OS, profile: t.D2R_PROFILE, ledger: t._D2R_LEDGER,
                cousin: t._isCousinShell, stored: t.localStorage.getItem('d2r_activeMachine'),
                source: t.localStorage.getItem('d2r_machineSource'), ptr: t.localStorage.getItem('d2r_activeProfileWin'),
                ladderCopy: t.localStorage.getItem('L·d2r_charBuilds') === CFG.snap.stores.d2r_charBuilds,
                noWorld: before };
  const reel = { nodeType: 3, nodeValue: "from this console's reels" };
  doc.body = { nodeType: 1, childNodes: [reel] };
  (listeners.DOMContentLoaded || []).forEach(function (f) { f(); });
  res.reels = reel.nodeValue;
  process.stdout.write(JSON.stringify(res));
})();
"""


class TheShadowFrameBoot(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise unittest.SkipTest("node is absent - the boot block cannot be run here, so it is UNMEASURED")
        snap = {"owner": OWNER, "t": T0,
                "stores": dict(_wstores(), d2r_api_chars_learned='{"ok":true,"chars":[{"name":"Deansorc"}]}')}
        with tempfile.TemporaryDirectory(prefix="tvd_shadow_boot_") as d:
            h = os.path.join(d, "boot.js")
            with io.open(h, "w", encoding="utf-8") as fh:
                fh.write(_BOOT)
            c = os.path.join(d, "cfg.json")
            with io.open(c, "w", encoding="utf-8") as fh:
                json.dump({"bible": BIBLE, "snap": snap}, fh)
            r = subprocess.run([NODE, h, c], capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=120)
        if r.returncode != 0:
            raise AssertionError("the boot harness failed rc=%s\n%s" % (r.returncode, r.stderr[-2000:]))
        cls.r = json.loads(r.stdout)
        cls.snap = snap

    def test_a_normal_board_is_untouched(self):
        self.assertTrue(self.r["offUntouched"])

    def test_no_profile_fails_closed(self):
        self.assertEqual(self.r["closedThrew"], "tvd-shadow: closed")
        self.assertTrue(self.r["closedStopped"])
        self.assertIn("Nothing was read from or written to this PC", self.r["closedWrote"])

    def test_the_board_boots_on_their_stores_in_memory(self):
        self.assertIsNone(self.r["threw"])
        self.assertTrue(self.r["memIsLocal"], "the page was handed this browser's real storage")
        self.assertEqual(self.r["seeded"], self.snap["stores"])
        self.assertIsNone(self.r["written"], "a shadow accepted a storage write after it opened")
        self.assertIsNone(self.r["sessWritten"], "a shadow accepted a session write after it opened")
        self.assertEqual(self.r["kept"], self.snap["stores"][self.r["keptKey"]],
                         "a shadow removed a store that arrived with the profile")
        self.assertEqual(self.r["reels"], "from Dean's reels",
                         "the characters line still says this console inside a shadow")
        self.assertEqual((self.r["claim"], self.r["install"]), ("*", "tvdshadow0000000"))
        self.assertEqual(self.r["cls"], ["tvd-shadow-snap"],
                         "the frame took the phase-1 tvd-shadow class, which hides their reels")

    def test_no_request_but_a_plain_get_leaves_and_their_answers_are_served_from_the_snapshot(self):
        a = self.r["answers"]
        self.assertEqual(json.loads(a[0]), {"ok": True, "chars": [{"name": "Deansorc"}]})
        # #203 - an answer their console did not send says so, and still never reaches this console
        self.assertEqual(json.loads(a[1]), {"ok": False, "chars": None, "locked": None,
                                            "why": "their console did not send this with its last upload"},
                         "main_locks absent from the snapshot leaked or was called read-only")
        for i in (2, 3, 4, 5, 6):
            self.assertEqual(json.loads(a[i])["why"], "shadow: read only", "request %d left the frame" % i)
        self.assertEqual(self.r["sent"], [["/fonts/a.woff2", "GET"]],
                         "something other than a plain GET of a file left the frame")
        self.assertEqual(self.r["refused"], 13)  # #203 - the unsent main_locks answers with its reason; 5 agent asks refused
        self.assertEqual(self.r["agent"], [403] * 5,
                         "the viewer's own capture agent answered inside a shadow - TV·D could go LIVE on HIS reads (bug 5)")
        self.assertEqual(self.r["indexedDB"], "undefined")

    def test_the_lamp_asks_and_the_frame_says_whose_sign_in_it_is(self):
        """* REG-3380 (v3883) - GrokBot in Dean's shadow: the D2JSP lamp read "This machine could not read the Chrome
        login" - the frame REFUSED the lamp's ask and the lamp drew the refusal as the viewer's own failure. The frame
        answers it: UNKNOWN, and on whose PC the sign-in lives - and it is answered, never refused (the count stays 13)."""
        j = json.loads(self.r["answers"][8])
        self.assertEqual(j.get("state"), "unknown", "the snapshot answered the lamp with a state it never read: %r" % j)
        self.assertIn("lives on that PC", j.get("why") or "")
        self.assertNotIn("This machine", j.get("why") or "")
        self.assertEqual(self.r["refused"], 13, "the lamp's ask was refused - the lamp then speaks for the viewer's machine")

    def test_write_controls_and_typing_are_stopped_view_controls_pass(self):
        v = self.r["veil"]
        self.assertTrue(v["del"] and v["set"], "a write button reached the page in shadow")
        self.assertFalse(v["open"] or v["mule"] or v["tab"], "a view control was stopped: %r" % v)
        # the vault's MOVE TASKS overlay and its ADVANCED panes open, as on his own console
        self.assertFalse(v["tasks"] or v["adv"], "a vault view toggle was stopped: %r" % v)
        self.assertFalse(v["task"], "REG-2758 - a move task row's from -> to picture was stopped in the shadow: %r" % v)
        self.assertTrue(v["inSummary"], "a write button inside a fold passed the veil as if it were the fold")
        # GrokBot bugs 2+3 - "Best runs ->", "open recipe" and the Tools chips move the view in the shadow too
        lk = self.r["links"]
        # REG-2860 - and the Vault guide opens and steps in a shadow, as it does on his own board
        for k in ("runs", "sets", "recipe", "legend", "tool", "hist", "fold", "guide", "guideGo", "guideShow"):
            self.assertFalse(lk[k], "the view link %r was stopped in the shadow: %r" % (k, lk))
        self.assertTrue(lk["gotBase"], "a forge write (got the base) passed the veil: %r" % lk)
        self.assertTrue(self.r["claimStopped"], "a click on the claim button was not stopped in the shadow frame")
        self.assertTrue(self.r["typing"])
        self.assertEqual(sorted(self.r["blocks"]),
                         sorted(["change", "input", "submit", "drop", "paste", "dragstart", "contextmenu", "pointerdown",
                                 "keypress", "keyup"]))

    def test_keys_move_the_view_and_nothing_else(self):
        k = self.r["keys"]
        self.assertTrue(k["Delete"] and k["z"] and k["Enter"], "a board shortcut saw a key in shadow: %r" % k)
        self.assertFalse(k["ArrowDown"] or k["PageDown"] or k["Escape"] or k["copy"] or k["Tab"],
                         "a key that only moves the view was stopped: %r" % k)
        self.assertFalse(k["taskEnter"] or k["taskSpace"],
                         "REG-2758 - Enter/Space on a view control was stopped, so the shadow's rows open by mouse only: %r" % k)
        self.assertTrue(k["taskCtrl"] and k["delEnter"],
                        "REG-2758 - Enter reached a write control, or a modified Enter passed, in the shadow: %r" % k)
        self.assertEqual(self.r["leaveOnEscape"], ["tvd-shadow-leave"],
                         "Escape inside the shadow did not ask the console to leave: %r" % self.r.get("leaveOnEscape"))

    def test_the_viewers_console_and_real_storage_are_out_of_reach(self):
        self.assertTrue(self.r["parentSealed"], "the board can still reach the console that shows it by `parent`")
        self.assertEqual(self.r["reopen"], [], "a later script could put back: %r" % self.r["reopen"])

    def test_their_world_is_drawn_not_this_browsers(self):
        w = self.r["world"]
        self.assertEqual((w["machine"], w["os"], w["profile"], w["ledger"], w["cousin"]),
                         ("windows", "WINDOWS", "ladder", "Dean ledger", True),
                         "the shadow drew the viewer's world, or a board line re-derived it: %r" % w)
        self.assertEqual((w["stored"], w["source"], w["ptr"]), ("windows", "user", "ladder"))
        self.assertTrue(w["ladderCopy"], "a ladder owner's stores are not where the ladder board reads them")
        self.assertEqual(w["noWorld"], "tvd-shadow: closed", "a snapshot with no world opened in the viewer's world")
        self.assertEqual(self.r["partial"], ["tvd-shadow: closed"] * 5, "a half world opened, drawn half theirs half ours")


class HisKeysNeverReachThisPcThroughAShadow(unittest.TestCase):
    """#206 - GrokBot's v3808 sweep: Space while viewing another PC's shadow toggled THIS PC's ON AIR (focus stays on the
    host page after a tab or Leave click), and L / T opened this PC's log and theatre. The real handler, run in node."""

    def test_space_l_and_t_act_on_this_pc_only_with_no_shadow_up(self):
        if not NODE:
            raise AssertionError("node is absent - the hotkey law cannot be run here, so it is UNMEASURED")
        ui = _read(UI)
        start = "  // keyboard: space = cut if live/sim else ON \u00b7 L = log \u00b7 T = theatre\n"
        end = "      if (thBtn) thBtn.click();\n    }\n  });\n"
        self.assertEqual(ui.count(start), 1, "the hotkey block's anchor is not unique")
        i = ui.index(start)
        block = ui[i:ui.index(end, i) + len(end)]
        js = r"""
var posts = [], clicks = [], listeners = [];
var document = { addEventListener: function (t, fn) { if (t === 'keydown') listeners.push(fn); },
  body: { _cls: {}, classList: { contains: function (c) { return !!document.body._cls[c]; } },
          getAttribute: function () { return 'off'; } },
  getElementById: function (id) { return { click: function () { clicks.push(id); } }; } };
var window = {};
var TH = { open: false }, busy = false, thBtn = { click: function () { clicks.push('theatre'); } };
function $(id) { return document.getElementById(id); }
function post(u) { posts.push(u); }
""" + block + r"""
function press(code, key) {
  var e = { code: code, key: key, target: { tagName: 'DIV' }, preventDefault: function () {} };
  listeners.forEach(function (fn) { fn(e); });
}
function round() { posts.length = 0; clicks.length = 0; press('Space', ' '); press('KeyL', 'l'); press('KeyT', 't');
  return { posts: posts.slice(), clicks: clicks.slice() }; }
var out = { host: round() };
['shadow-on', 'shadow-snap', 'shadow-hub'].forEach(function (c) {
  document.body._cls = {}; document.body._cls[c] = true; out[c] = round(); });
console.log(JSON.stringify(out));
"""
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got["host"]["posts"], ["/api/on"], "PREMISE: Space with no shadow up did not turn ON AIR on: %r" % got)
        self.assertEqual(got["host"]["clicks"], ["btn-log", "theatre"], "PREMISE: L / T with no shadow up: %r" % got)
        for c in ("shadow-on", "shadow-snap", "shadow-hub"):
            self.assertEqual(got[c]["posts"], [], "Space under %s reached this PC's agent: %r" % (c, got))
            self.assertEqual(got[c]["clicks"], [], "L / T under %s opened this PC's log or theatre: %r" % (c, got))


class ThisPcsRowOffersNoShadowOfItself(unittest.TestCase):
    """GrokBot's 21:09 pass (v3809): each console offered "see <its own profile>'s console" on its own Fleet row."""

    def test_the_own_row_has_no_shadow_button_and_the_others_keep_theirs(self):
        if not NODE:
            raise AssertionError("node is absent - the Fleet button law cannot be run here, so it is UNMEASURED")
        ui = _read(UI)
        call = "_fleetOpenEyesHtml(m, !!(_me && m && m.machine === _me))"
        self.assertEqual(ui.count(call), 1, "the Fleet row does not tell the button whether it is this PC's row")
        start = "  var _FLEET_ROSTER_OWNERS = "
        end = "  window._fleetOpenEyesHtml = _fleetOpenEyesHtml;\n"
        self.assertEqual(ui.count(start), 1)
        i = ui.index(start)
        block = ui[i:ui.index(end, i) + len(end)]
        js = "var window = {};\nfunction escC(s) { return String(s); }\n" + block + """
var me = { nickname: 'Konyo', platform: 'mac', machine: 'm1' };
var alt = { nickname: 'Konyo \\u00b7 ALT', platform: 'windows', machine: 'm2' };
var stranger = { nickname: 'nobody', platform: 'windows', machine: 'm3' };
console.log(JSON.stringify({ me: _fleetOpenEyesHtml(me, true), alt: _fleetOpenEyesHtml(alt, false),
                             none: _fleetOpenEyesHtml(stranger, false), legacy: _fleetOpenEyesHtml(alt) }));
"""
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got["me"], "", "this PC's own row offered a shadow of itself: %r" % got)
        self.assertIn("see Konyo · ALT’s console", got["alt"], got)
        self.assertIn("no roster profile", got["none"], got)
        self.assertIn("data-roster-owner", got["legacy"], "a caller that does not say isMe lost the button: %r" % got)


RED_PROOF = [
    {"why": "REG-3380 (v3883) - the snapshot refuses the lamp's ask again: Dean's shadow says THIS machine could not read the login",
     "file": "bible.html",
     "find": "      if (path === '/api/d2jsp_login') {\n",
     "replace": "      if (false) {\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2860 - the Vault guide is stopped in a shadow (its two doors are not view controls)",
     "file": "bible.html",
     "find": "                'vaultGuideTog', 'vaultGuideGo',\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "Shadow: the worker does not decode each string literal, so an escaped path or token (even under a dropped duplicate key) is stored",
     "file": "functions/api/roster.js",
     "find": "    if (PRIVATE.some((rx) => rx.test(t))) return true;\n  }\n",
     "replace": "  }\n", "matches": 1, "needs": "node"},
    {"why": "Shadow: the worker skips the raw text, so a store that is not JSON carries a path out",
     "file": "functions/api/roster.js",
     "find": "  if (PRIVATE.some((rx) => rx.test(raw))) return true;\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "the quota - a boot post skips the 75 min gap again, so restarts spend the site's 20 uploads a day",
     "file": "tv/console_snapshot.py",
     "find": "    if isinstance(last, int) and not isinstance(last, bool) and now_ms - last < MIN_GAP_MS:   # the quota - boot too\n",
     "replace": "    if not boot and isinstance(last, int) and not isinstance(last, bool) and now_ms - last < MIN_GAP_MS:\n",
     "matches": 1},
    {"why": "GrokBot bug 5 - the viewer's own capture agent on another origin answers inside a shadow again",
     "file": "bible.html",
     "find": "      if (foreign(url)) return true;\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "GrokBot bug 5 - a refused agent probe reads 200 again, so TV·D thinks an agent is there",
     "file": "bible.html",
     "find": "return refused(foreign(url) ? 403 : 200); }",
     "replace": "return refused(); }", "matches": 1, "needs": "node"},
    {"why": "GrokBot bugs 2+3 - the Tools chips and the forge/uniques/sets filters are stopped in the shadow again",
     "file": "bible.html",
     "find": "                'funiSetFilter', 'fsetsSetFilter', 'forgeSetFilter', 'forgeCraftToggle', 'forgeLegendToggle', '_toolJump',\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "GrokBot 22:07 - TV·D's LIVE / LAST SESSION and the Tools card folds are stopped in the shadow again",
     "file": "bible.html",
     "find": "                '_tvdHistTab', 'toggleCardCollapse',\n",
     "replace": "\n", "matches": 1, "needs": "node"},
    {"why": "Shadow: MOVE TASKS and the ADVANCED panes stay shut in the vault",
     "file": "bible.html",
     "find": "                'vaultTasksTog', 'vaultAdvTab',\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "Shadow: the worker stores a board install id the console blanks",
     "file": "functions/api/roster.js",
     "find": "  /\\bI?L?·[0-9a-f]{8}·/,\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "Shadow: the frame opens on a world with one fact wrong or missing",
     "file": "bible.html",
     "find": "        typeof world.ledger === 'string' && typeof world.cousin === 'boolean')) world = null;\n",
     "replace": "        true)) world = world;\n", "matches": 1, "needs": "node"},
    {"why": "Shadow: a right-click reaches the board (a mule item's context unlock)",
     "file": "bible.html",
     "find": "    ['change', 'input', 'submit', 'drop', 'paste', 'dragstart', 'contextmenu'].forEach(",
     "replace": "    ['change', 'input', 'submit', 'drop', 'paste', 'dragstart'].forEach(", "matches": 1, "needs": "node"},
    {"why": "Shadow: the worker stores a signed body that still carries a path or a token",
     "file": "functions/api/roster.js",
     "find": "    if (privateIn(stores[k])) return pRefuse(",
     "replace": "    if (false) return pRefuse(", "matches": 1, "needs": "node"},
    {"why": "Shadow: the worker stores a snapshot that does not say which world it was drawn in",
     "file": "functions/api/roster.js",
     "find": "  if (typeof stores.d2r_api_world !== \"string\") return pRefuse(",
     "replace": "  if (false) return pRefuse(", "matches": 1, "needs": "node"},
    {"why": "Shadow: an unreadable stored record lets a post start the replay and quota checks over",
     "file": "functions/api/roster.js",
     "find": "    return pRefuse(\"the stored profile could not be read\");\n",
     "replace": "    prev = null;\n", "matches": 1, "needs": "node"},
    {"why": "Shadow: a snapshot with no world opens in the viewer's own world",
     "file": "bible.html",
     "find": "    if (!ok || !stores || !world) {\n",
     "replace": "    if (!ok || !stores) {\n", "matches": 1, "needs": "node"},
    {"why": "Shadow: this PC's old copy is drawn over the site refusing",
     "file": "tv/control_app.py",
     "find": "            why, unread = str(got.get(\"why\") or \"the site refused\")[:120], False\n",
     "replace": "            why = str(got.get(\"why\") or \"the site refused\")[:120]\n", "matches": 1},
    {"why": "Shadow: the board can reach the console that shows it through `parent`",
     "file": "bible.html",
     "find": "      Object.defineProperty(window, 'parent', { configurable: false, get: function () { return window; } });\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "Shadow: a later script can put this browser's real storage back (the getter is configurable)",
     "file": "bible.html",
     "find": "      Object.defineProperty(window, 'indexedDB', { configurable: false, get: function () { return undefined; } });\n",
     "replace": "      Object.defineProperty(window, 'indexedDB', { configurable: true, get: function () { return undefined; } });\n",
     "matches": 1, "needs": "node"},
    {"why": "Shadow: a Windows cousin is drawn as the viewer's own (owner) world, so the Mac's seeds land in it",
     "file": "bible.html",
     "find": "      if (typeof world.cousin === 'boolean') pin('_isCousinShell', world.cousin);\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "Shadow: a ladder owner is drawn on the viewer's main profile",
     "file": "bible.html",
     "find": "seed.d2r_activeProfileWin = world.profile; pin('D2R_PROFILE', world.profile);",
     "replace": "seed.d2r_activeProfileWin = world.profile;", "matches": 1, "needs": "node"},
    {"why": "Shadow: the board's own shortcuts see every key press",
     "file": "bible.html",
     "find": "      if (NAV.test(String(ev.key || ''))) return true;\n",
     "replace": "      return true;\n", "matches": 1, "needs": "node"},
    {"why": "Shadow: a write button inside a fold passes the veil as the fold",
     "file": "bible.html",
     "find": "      if (el.matches && el.matches('.tab, summary, [data-shadow-view]')) return true;\n",
     "replace": "      if (el.closest('.tab, summary, [data-shadow-view]')) return true;\n", "matches": 1, "needs": "node"},
    {"why": "Shadow: a shadow frame posts a roster book",
     "file": "bible.html",
     "find": "    pin('_tvdBookPost', function () { return false; });\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "Shadow: the board stops saying which world its stores were drawn in",
     "file": "bible.html",
     "find": "    var body = JSON.stringify({ kind: 'profile', stores: stores, world: world });\n",
     "replace": "    var body = JSON.stringify({ stores: stores });\n", "matches": 1},
    {"why": "Shadow: the worker takes a replayed (older) upload over a newer one",
     "file": "functions/api/roster.js",
     "find": "  if (prev && typeof prev.signedAt === \"number\" && signedAt <= prev.signedAt) {\n",
     "replace": "  if (false) {\n", "matches": 1, "needs": "node"},
    {"why": "Shadow: the worker stores an identity or debug store a signed client sent",
     "file": "functions/api/roster.js",
     "find": " && typeof stores[k] === \"string\" && nameOk(k));",
     "replace": " && typeof stores[k] === \"string\");", "matches": 1, "needs": "node"},
    {"why": "Shadow: GET serves a record signed by a key that is no longer the owner's",
     "file": "functions/api/roster.js",
     "find": "  if (!registered || !registered.pub || b64uKey(registered.pub) !== b64uKey(prev.pub)) {\n",
     "replace": "  if (false) {\n", "matches": 1, "needs": "node"},
    {"why": "Shadow: this PC's old copy is shown over the site saying nothing is uploaded or the record is corrupt",
     "file": "tv/control_app.py",
     "find": "    if rec is None and unread:\n",
     "replace": "    if rec is None:\n", "matches": 1},
    {"why": "Shadow: a world value outside the closed set rides the upload",
     "file": "tv/console_snapshot.py",
     "find": "        if raw.get(k) not in allowed:\n            return None\n",
     "replace": "        pass\n", "matches": 1},
    {"why": "Shadow: the console drops the board's world before the upload",
     "file": "tv/control_app.py",
     "find": "        clean[\"world\"] = world\n",
     "replace": "        pass\n", "matches": 1},
    {"why": "Shadow: a board screen draws differently in shadow (a render branch on _tvdShadow)",
     "file": "bible.html",
     "find": "  function renderVault(){\n",
     "replace": "  function renderVault(){ if (window._tvdShadow) {}\n", "matches": 1},
    {"why": "Shadow: the shadow frame loads a viewer page of its own instead of the console's board",
     "file": "control_ui.html",
     "find": "    f.src = '/board?app=1&engine=1&tvd-shadow=1&v=' + Date.now() + '#chars';\n",
     "replace": "    f.src = '/shadow?tvd-shadow=1&v=' + Date.now() + '#chars';\n", "matches": 1},
    {"why": "Shadow: TV·D in shadow drops to this PC's own cockpit",
     "file": "control_ui.html",
     "find": "    if (document.body.classList && document.body.classList.contains('shadow-on')) {\n",
     "replace": "    if (b.dataset.tab === 'tvd'){ document.body.removeAttribute('data-view'); shellHome(); return; }\n    if (document.body.classList && document.body.classList.contains('shadow-on')) {\n",
     "matches": 1},
    {"why": "Shadow: a shadow tab drops the sessions view, so Leave returns on standby",
     "file": "control_ui.html",
     "find": "      shellOpen(b.dataset.tab);\n      return;\n",
     "replace": "      document.body.removeAttribute('data-view');\n      shellOpen(b.dataset.tab);\n      return;\n",
     "matches": 1},
    {"why": "Shadow: the marker loses the snapshot time",
     "file": "control_ui.html",
     "find": "    if (who) who.textContent = String(d.words || owner) + at + ' · read only';\n",
     "replace": "    if (who) who.textContent = String(d.words || owner) + ' · read only';\n", "matches": 1},
    {"why": "Shadow: the boot block hands the page the browser's real localStorage, so a shadow writes his own store",
     "file": "bible.html",
     "find": "      Object.defineProperty(window, 'localStorage', { configurable: false, get: function () { return mem; } });\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "Shadow: the fetch guard lets a POST to the console through",
     "file": "bible.html",
     "find": "      if (m !== 'GET' && m !== 'HEAD') return true;\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "Shadow: the frame boots with no snapshot instead of failing closed",
     "file": "bible.html",
     "find": "    if (!ok || !stores || !world) {\n",
     "replace": "    if (!ok) {\n", "matches": 1, "needs": "node"},
    {"why": "Shadow: a write button is let through the click veil",
     "file": "bible.html",
     "find": "      if (!ctl || viewOnly(ctl)) return;\n",
     "replace": "      return;\n", "matches": 1, "needs": "node"},
    {"why": "Shadow: the frame takes the phase-1 tvd-shadow class and hides their in-game characters",
     "file": "bible.html",
     "find": "    document.documentElement.classList.add('tvd-shadow-snap');\n",
     "replace": "    document.documentElement.classList.add('tvd-shadow-snap'); document.documentElement.classList.add('tvd-shadow');\n",
     "matches": 1, "needs": "node"},
    {"why": "Shadow: the worker stores a snapshot for an owner with no registered key (registers one)",
     "file": "functions/api/roster.js",
     "find": "  if (registered === null) return pRefuse(",
     "replace": "  if (registered === 'never') return pRefuse(", "matches": 1, "needs": "node"},
    {"why": "Shadow: the worker stores a snapshot whose stores do not match the signed hash",
     "file": "functions/api/roster.js",
     "find": "  if (body.hash !== hash) return pRefuse(",
     "replace": "  if (false) return pRefuse(", "matches": 1, "needs": "node"},
    {"why": "Shadow: the worker's daily cap is gone",
     "file": "functions/api/roster.js",
     "find": "  if (n >= PROFILE_DAY_CAP) return pRefuse(",
     "replace": "  if (false) return pRefuse(", "matches": 1, "needs": "node"},
    {"why": "Shadow: GET serves a record that fails its own hash as stores",
     "file": "functions/api/roster.js",
     "find": "  if (!storesOk(prev.stores) || prev.hash !== hashOfStores(prev.stores)) {\n",
     "replace": "  if (!storesOk(prev.stores)) {\n", "matches": 1, "needs": "node"},
    {"why": "Shadow: the install id store leaves the PC",
     "file": "tv/console_snapshot.py",
     "find": "    \"d2r_grailFarm\", \"d2r_storeEmptied\", \"d2r_installId\", ",
     "replace": "    \"d2r_grailFarm\", \"d2r_storeEmptied\", ", "matches": 1},
    {"why": "Shadow: a path on disk leaves the PC inside a store",
     "file": "tv/console_snapshot.py",
     "find": "    re.compile(r\"(?:/Users/|/home/|/private/|/var/folders/)[^\\s\\\"']*\"),\n",
     "replace": "", "matches": 1},
    {"why": "Shadow: the viewer is told 'live' with no age of the upload",
     "file": "tv/console_snapshot.py",
     "find": "        state, words = \"live\", \"%s · online now · board uploaded %s\" % (owner, ago)\n",
     "replace": "        state, words = \"live\", \"%s · live\" % owner\n", "matches": 1},
    {"why": "Shadow: with the site down the viewer gets nothing instead of the PC's last copy",
     "file": "tv/control_app.py",
     "find": "        rec = _cs.read_cache(cdir, owner)\n",
     "replace": "        rec = None\n", "matches": 1},
    {"why": "Shadow: a tampered record is shown",
     "file": "tv/console_snapshot.py",
     "find": "    return rec.get(\"hash\") == digest(stores)\n",
     "replace": "    return True\n", "matches": 1},
    {"why": "Shadow: an unchanged snapshot is uploaded every pass",
     "file": "tv/console_snapshot.py",
     "find": "    if state.get(\"hash\") == d and not boot and not stale:\n",
     "replace": "    if False:\n", "matches": 1},
    {"why": "Shadow: the console panel never falls back to the roster row",
     "file": "tv/control_ui.html",
     "find": "      .catch(function () { if (gen === _shadowGen) window._shadowEnter(owner); });\n",
     "replace": "      .catch(function () {});\n", "matches": 1},
    {"why": "Shadow: a sent unique list is ignored when the published count is zero.",
     "file": "tv/control_ui.html",
     "find": "uniques: (shadow && uniHave != null && uniHave >= 1) ? null : _listCount(shadow ? readHub('d2r_foundLog') : lsHub('d2r_foundLog'))",
     "replace": "uniques: shadow ? null : _listCount(lsHub('d2r_foundLog'))",
     "matches": 1},
    {"why": "Shadow: the chips repeat the missing-list sentence whenever the line contains an apostrophe.",
     "file": "tv/control_ui.html",
     "find": "var _blank = (!chronText || chronText === _unsentLine)",
     "replace": "var _blank = (!chronText || chronText.indexOf('\\u2019') !== -1)",
     "matches": 1},
    {"why": "Shadow: today repeats the missing-list sentence even when the chronicle line already counts.",
     "file": "tv/control_ui.html",
     "find": "        return s === '' || s === 'the list wasn\\u2019t sent';",
     "replace": "        return true;",
     "matches": 1},
    {"why": "#206 - Space while viewing a shadow posts /api/on or /api/off to this PC's agent again",
     "file": "tv/control_ui.html",
     "find": "    if (_consoleShadowUp()) return;   /* #206 - never this PC's ON AIR from a shadow */\n",
     "replace": "    void 0;\n",
     "matches": 1},
    {"why": "#206 - the shadow hub is not counted as a shadow, so the keys reach this PC from it",
     "file": "tv/control_ui.html",
     "find": "    return !!(cl && (cl.contains('shadow-on') || cl.contains('shadow-snap') || cl.contains('shadow-hub')));\n  }\n  window._consoleShadowUp",
     "replace": "    return !!(cl && (cl.contains('shadow-on') || cl.contains('shadow-snap')));\n  }\n  window._consoleShadowUp",
     "matches": 1},
    {"why": "GrokBot 21:09 - this PC's Fleet row offers a shadow of itself again",
     "file": "tv/control_ui.html",
     "find": "    if (isMe) return '';\n    var owner = _fleetRosterOwner(m);",
     "replace": "    var owner = _fleetRosterOwner(m);",
     "matches": 1},
    {"why": "GrokBot 21:09 - the Fleet row stops telling the button it is this PC's row",
     "file": "tv/control_ui.html",
     "find": "_fleetOpenEyesHtml(m, !!(_me && m && m.machine === _me)) + '</div>';",
     "replace": "_fleetOpenEyesHtml(m) + '</div>';",
     "matches": 1},
    {"why": "#200 - the roster shadow stops carrying how many names there were",
     "file": "tv/control_ui.html",
     "find": "      if (list.length && whole(namedN, 1) && namedN > list.length) { pair.sent = list.length; pair.named = namedN; }\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "#200 - the chronicle line calls a cut name list the whole list again",
     "file": "tv/control_ui.html",
     "find": "    if (partial.length) line = line ? (line + ' \\u00b7 ' + partial.join(' \\u00b7 ')) : partial.join(' \\u00b7 ');\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "#210 - the snapshot stops naming what it could not send",
     "file": "tv/console_snapshot.py",
     "find": "    return {\"stores\": out, \"dropped\": dropped, \"unsent\": unsent_of(dropped)}\n",
     "replace": "    return {\"stores\": out, \"dropped\": dropped, \"unsent\": []}\n",
     "matches": 1},
    {"why": "#210 - a store kept home on purpose is reported as missing",
     "file": "tv/console_snapshot.py",
     "find": "        if isinstance(k, str) and _KEY.match(k) and k not in DENY and not any(k.startswith(p) for p in DENY_PREFIX):\n",
     "replace": "        if isinstance(k, str) and _KEY.match(k):\n",
     "matches": 1},
    {"why": "#210 - the upload leaves the unsent list behind",
     "file": "tv/console_snapshot.py",
     "find": "        body[\"unsent\"] = unsent_of(list(unsent or []) + fit_out)\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "#210 - the banner stops saying what is missing",
     "file": "tv/console_snapshot.py",
     "find": "    if unsent:\n        words += \" · not sent (too big or private): \"",
     "replace": "    if False:\n        words += \" · not sent (too big or private): \"",
     "matches": 1},
    {"why": "#210 - an upload from before the list reads as everything sent",
     "file": "tv/console_snapshot.py",
     "find": "    unsent = unsent_of(rec.get(\"unsent\")) if isinstance(rec.get(\"unsent\"), list) else None\n",
     "replace": "    unsent = unsent_of(rec.get(\"unsent\") or [])\n",
     "matches": 1},
    {"why": "#210 - this PC's last copy drops the unsent list",
     "file": "tv/console_snapshot.py",
     "find": "\"keyId\", \"dropped\", \"unsent\", \"others\")\n",
     "replace": "\"keyId\", \"dropped\", \"others\")\n",
     "matches": 1},
    {"why": "#210 - the console's lane leaves the book's unsent list behind",
     "file": "tv/control_app.py",
     "find": "                           unsent=book.get(\"unsent\") if isinstance(book.get(\"unsent\"), list) else None)   # #210\n",
     "replace": "                           unsent=None)\n",
     "matches": 1},
    {"why": "#210 - the site stops keeping the unsent list",
     "file": "functions/api/roster.js",
     "find": "  if (unsent) rec.unsent = unsent;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "#210 - the site stores any list as unsent, paths included",
     "file": "functions/api/roster.js",
     "find": "  for (const k of v) if (typeof k !== \"string\" || !/^d2r_[A-Za-z0-9_]{1,60}$/.test(k)) return null;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2758 - a move task row's picture is stopped in the shadow again",
     "file": "bible.html",
     "find": "                '_vaultTaskExpand',\n",
     "replace": "                \n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2758 - Enter/Space on a view control is stopped again (the shadow's rows open by mouse only)",
     "file": "bible.html",
     "find": "        if (kc && kc === kt && viewOnly(kc)) return true;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2758 - Enter reaches any focused control in the shadow, a write one included",
     "file": "bible.html",
     "find": "        if (kc && kc === kt && viewOnly(kc)) return true;\n",
     "replace": "        if (kc && kc === kt) return true;\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
