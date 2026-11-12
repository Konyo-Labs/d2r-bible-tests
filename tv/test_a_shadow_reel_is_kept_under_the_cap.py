# -*- coding: utf-8 -*-
"""#208 (his 11-13 calls) - A PC'S SESSIONS LIVE IN A PRIVATE BUCKET, NEWEST FIRST, AND THE BUCKET NEVER PASSES ITS CAP.

His words: "when a player is offline to see his last 16 reels somehow", "maybe just the last 3 sessions recorded for each pc
so those are online and always reachable even when a user is offline", and on cost: "it doesnt stack and charge me more
for clouflare?". R2's free tier is 10 GB-month, so the bucket holds at most REEL_CAP_BYTES (9 GB): a begin whose estimate
would pass it evicts the oldest sealed sessions of ANY PC first, and refuses when nothing older is left. Per PC (slot) the
newest 16 sessions are kept; the PC sends which are full and which are summaries, and a demotion drops the frames not on
the new list. Every write rides the PC's registered roster key - the same signed gate as the profile and the frames digest.
UNKNOWN stays UNKNOWN: an index that will not read refuses the upload, and an unbound bucket answers "not bound", never an
empty list.

Driven on functions/api/roster.js as it ships, in node, on a fake KV and a fake R2 bucket, with real signing keys.
"""
import base64
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import roster_sign as RS  # noqa: E402

NODE = shutil.which("node")
ROSTER_JS = os.path.join(ROOT, "functions", "api", "roster.js")
OWNER = "Dean"
T0 = 1792800000000
GB = 1024 ** 3
JPG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"frame" * 40).decode("ascii")

_HARNESS = r"""
import { pathToFileURL } from 'node:url';
import { readFileSync } from 'node:fs';
const CFG = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const bytes = (s) => new Uint8Array(Buffer.from(s || '', 'base64'));
const kvs = new Map(Object.entries(CFG.seed || {}).map(([k, v]) => [k, typeof v === 'string' ? v : JSON.stringify(v)]));
const kv = { async get(n) { return kvs.has(n) ? kvs.get(n) : null; }, async put(n, v) { kvs.set(n, v); } };
const objs = new Map(Object.entries(CFG.r2 || {}).map(([k, v]) => [k, typeof v === 'string' ? v : JSON.stringify(v)]));
let puts = [], dels = [];
const asText = (v) => typeof v === 'string' ? v : Buffer.from(v).toString('utf8');
const r2 = {
  async get(k) { if (!objs.has(k)) return null; const v = objs.get(k); return { text: async () => asText(v), body: v }; },
  async put(k, v) { puts.push(k); objs.set(k, typeof v === 'string' ? v : new Uint8Array(v)); },
  async delete(keys) { for (const k of [].concat(keys)) { dels.push(k); objs.delete(k); } },
  async list(o) {
    const pre = o.prefix || '', set = new Set(), objects = [];
    for (const k of objs.keys()) {
      if (!k.startsWith(pre)) continue;
      const rest = k.slice(pre.length), i = o.delimiter ? rest.indexOf(o.delimiter) : -1;
      if (i >= 0) set.add(pre + rest.slice(0, i + 1)); else objects.push({ key: k });
    }
    return { objects, delimitedPrefixes: [...set], truncated: false };
  },
};
const env = CFG.unbound ? { TZ_HISTORY: kv } : { TZ_HISTORY: kv, REELS: r2 };
const mod = await import(pathToFileURL(CFG.file).href);
const out = { steps: [] };
for (const step of (CFG.steps || [])) {
  puts = []; dels = [];
  const realNow = Date.now;
  if (typeof step.now === 'number') Date.now = () => step.now;
  if (step.get) {
    const res = await mod.onRequestGet({ request: new Request('https://bull-4-u.com/api/roster?' + step.get), env });
    const ct = res.headers.get('content-type') || '';
    const body = ct.indexOf('image/') === 0 ? { jpegBytes: (await res.arrayBuffer()).byteLength } : JSON.parse(await res.text());
    out.steps.push({ get: body, ct });
  } else {
    const req = new Request('https://bull-4-u.com/api/roster', { method: 'POST', body: bytes(step.raw),
      headers: Object.assign({ 'content-type': 'application/json' }, step.headers || {}) });
    const res = await mod.onRequestPost({ request: req, env });
    out.steps.push({ reply: JSON.parse(await res.text()), puts, dels });
  }
  Date.now = realNow;
}
out.keys = [...objs.keys()].sort();
out.index = {};
for (const k of out.keys) if (k.endsWith('/index.json')) out.index[k] = JSON.parse(asText(objs.get(k)));
process.stdout.write(JSON.stringify(out));
"""


def _node(cfg):
    with tempfile.TemporaryDirectory(prefix="tvd_reels_js_") as d:
        h, c = os.path.join(d, "h.mjs"), os.path.join(d, "cfg.json")
        io.open(h, "w", encoding="utf-8").write(_HARNESS)
        io.open(c, "w", encoding="utf-8").write(json.dumps(dict(cfg, file=ROSTER_JS)))
        r = subprocess.run([NODE, h, c], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    if r.returncode != 0:
        raise AssertionError("the reels harness failed rc=%s\n%s" % (r.returncode, r.stderr[-2000:]))
    return json.loads(r.stdout)


def _ses(k):
    return "s_%d_%d" % (T0 - 3600000 * k, k + 1)


def _fr(j):
    return "f_%d.jpg" % (T0 + j)


def _sealed_index(sessions):
    """an index of sealed sessions: {session: bytes}"""
    return {"sessions": {s: {"mode": "full", "want": [_fr(0)], "have": {_fr(0): b}, "bytes": b, "logo": None,
                             "start": None, "t": T0, "sealed": True} for s, b in sessions.items()}}


@unittest.skipUnless(NODE, "node is absent - the worker is UNMEASURED here, never a pass")
class TheReelBucket(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="tvd_reels_keys_")
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

    def _post(self, body, key=None, now=T0):
        body = dict({"kind": "reel", "owner": OWNER, "signedAt": now}, **body)
        raw = json.dumps(body).encode("utf-8")
        key = self.key_a if key is None else key
        return {"raw": base64.b64encode(raw).decode("ascii"), "headers": RS.sign_headers(key, raw)[0] if key else {},
                "now": now}

    def _begin(self, session, frames, mode="full", est=None, now=T0, key=None):
        return self._post({"op": "begin", "session": session, "mode": mode, "frames": frames, "logo": None,
                           "start": frames[0], "estBytes": est if est is not None else 1000 * len(frames)}, key=key, now=now)

    def _frames(self, session, names, now=T0, b64=JPG):
        return self._post({"op": "frames", "session": session, "frames": [{"name": n, "b64": b64} for n in names]}, now=now)

    def _seal(self, session, now=T0):
        return self._post({"op": "seal", "session": session}, now=now)

    def test_a_session_uploads_seals_and_reads_back(self):
        s, fr = _ses(0), [_fr(0), _fr(1)]
        out = _node({"seed": self.seed, "steps": [self._begin(s, fr), self._frames(s, fr), self._seal(s),
                                                  {"get": "reels=" + OWNER, "now": T0},
                                                  {"get": "reel=Dean&session=%s&frame=%s" % (s, fr[1]), "now": T0}]})
        begin, frames, seal, listing, frame = out["steps"]
        self.assertTrue(begin["reply"].get("ok"), begin["reply"])
        self.assertEqual(begin["reply"]["want"], fr)
        self.assertEqual(sorted(frames["reply"]["stored"]), fr, frames["reply"])
        self.assertTrue(seal["reply"].get("ok"), seal["reply"])
        self.assertIn("reel/Dean/%s/manifest.json" % s, out["keys"])
        self.assertEqual([x["session"] for x in listing["get"]["sessions"]], [s], listing["get"])
        self.assertEqual(frame["ct"], "image/jpeg")
        self.assertEqual(frame["get"]["jpegBytes"], len(base64.b64decode(JPG)), "the frame did not read back byte for byte")

    def test_an_unsigned_or_foreign_upload_writes_nothing(self):
        s, fr = _ses(0), [_fr(0)]
        out = _node({"seed": self.seed, "steps": [self._begin(s, fr, key=""), self._begin(s, fr, key=self.key_b)]})
        for st in out["steps"]:
            self.assertFalse(st["reply"].get("ok"), st["reply"])
            self.assertEqual(st["puts"], [], "a refused upload wrote %r" % st["puts"])
        self.assertEqual(out["keys"], [])

    def test_a_pc_keeps_its_newest_16_and_refuses_an_older_one(self):
        idx = _sealed_index({_ses(k): 1000 for k in range(16)})
        out = _node({"seed": self.seed, "r2": {"reel/Dean/index.json": idx},
                     "steps": [self._begin(_ses(-1), [_fr(0)]), self._begin(_ses(40), [_fr(0)])]})
        newer, older = out["steps"]
        self.assertTrue(newer["reply"].get("ok"), newer["reply"])
        self.assertEqual(newer["reply"]["evicted"], ["Dean/" + _ses(15)], "the 17th-newest session was not the one evicted")
        self.assertFalse(older["reply"].get("ok"), "a session older than the 16 kept was taken: %r" % older["reply"])
        self.assertEqual(len(out["index"]["reel/Dean/index.json"]["sessions"]), 16)

    def test_the_bucket_evicts_the_oldest_of_any_pc_to_stay_under_the_cap(self):
        """THE POINT of his cost question: 8.95 GB held, a 200 MB session begins - the oldest sealed session anywhere goes."""
        other = _sealed_index({_ses(30): int(4.5 * GB), _ses(2): int(4.45 * GB)})
        out = _node({"seed": self.seed, "r2": {"reel/OLD_PC_ALT/index.json": other},
                     "steps": [self._begin(_ses(0), [_fr(0)], est=200 * 1024 * 1024)]})
        st = out["steps"][0]
        self.assertTrue(st["reply"].get("ok"), st["reply"])
        self.assertEqual(st["reply"]["evicted"], ["OLD_PC_ALT/" + _ses(30)], "not the OLDEST session was evicted")
        self.assertLessEqual(st["reply"]["totalBytes"] + 200 * 1024 * 1024, 9 * GB)
        self.assertEqual(list(out["index"]["reel/OLD_PC_ALT/index.json"]["sessions"]), [_ses(2)],
                         "the other PC's index still lists the evicted session")

    def test_a_begin_that_cannot_fit_is_refused_not_stored(self):
        held = _sealed_index({_ses(1): int(8.9 * GB)})
        held["sessions"][_ses(1)]["sealed"] = False      # mid-upload: never evicted under another PC
        out = _node({"seed": self.seed, "r2": {"reel/OLD_PC_ALT/index.json": held},
                     "steps": [self._begin(_ses(0), [_fr(0)], est=200 * 1024 * 1024)]})
        st = out["steps"][0]
        self.assertFalse(st["reply"].get("ok"), "a begin past the cap with nothing to evict was accepted: %r" % st["reply"])
        self.assertIn("cap", st["reply"]["why"])

    def test_a_demotion_to_summary_drops_the_frames_not_on_it(self):
        s, fr = _ses(0), [_fr(0), _fr(1), _fr(2)]
        out = _node({"seed": self.seed, "steps": [self._begin(s, fr), self._frames(s, fr), self._seal(s),
                                                  self._begin(s, [_fr(1)], mode="summary"), self._seal(s)]})
        demote, reseal = out["steps"][3], out["steps"][4]
        self.assertEqual(sorted(demote["dels"]), ["reel/Dean/%s/%s" % (s, _fr(0)), "reel/Dean/%s/%s" % (s, _fr(2))])
        self.assertEqual(demote["reply"]["want"], [], "a frame already held was asked for again")
        self.assertEqual(reseal["reply"]["manifest"]["mode"], "summary")
        self.assertEqual(out["index"]["reel/Dean/index.json"]["sessions"][s]["bytes"], len(base64.b64decode(JPG)))

    def test_a_frame_the_begin_did_not_name_or_not_a_jpeg_is_refused(self):
        s = _ses(0)
        png = base64.b64encode(b"\x89PNG not a jpeg").decode("ascii")
        out = _node({"seed": self.seed, "steps": [self._begin(s, [_fr(0)]), self._frames(s, [_fr(9)]),
                                                  self._frames(s, [_fr(0)], b64=png), self._seal(s)]})
        for st in out["steps"][1:3]:
            self.assertFalse(st["reply"].get("ok"), st["reply"])
            self.assertEqual(st["puts"], [], "a refused frame wrote %r" % st["puts"])
        self.assertFalse(out["steps"][3]["reply"].get("ok"), "a session with a frame missing sealed")

    def test_an_unreadable_index_is_unknown_and_writes_nothing(self):
        out = _node({"seed": self.seed, "r2": {"reel/Dean/index.json": "{not json"},
                     "steps": [self._begin(_ses(0), [_fr(0)])]})
        st = out["steps"][0]
        self.assertFalse(st["reply"].get("ok"), st["reply"])
        self.assertIn("UNKNOWN", st["reply"]["why"])
        self.assertEqual(st["puts"], [], "an unreadable index was overwritten as if empty")

    def test_an_unbound_bucket_says_so_and_is_never_an_empty_list(self):
        out = _node({"seed": self.seed, "unbound": True,
                     "steps": [self._begin(_ses(0), [_fr(0)]), {"get": "reels=" + OWNER, "now": T0}]})
        post, got = out["steps"]
        self.assertFalse(post["reply"].get("ok"))
        self.assertIn("not bound", post["reply"]["why"])
        self.assertFalse(got["get"].get("ok"), "an unbound bucket answered a session list: %r" % got["get"])
        self.assertNotIn("sessions", got["get"])


RED_PROOF = [
    {"why": "#208 - the cap loop never evicts, so a full bucket refuses every new session instead of letting the oldest go",
     "file": "functions/api/roster.js",
     "find": "    while (total + need > REEL_CAP_BYTES && all.length) {",
     "replace": "    while (false) {",
     "matches": 1},
    {"why": "#208 - the per-PC keep is dropped, so a PC's sessions stack past 16",
     "file": "functions/api/roster.js",
     "find": "    for (const s of mine.slice(REEL_SESSIONS_PER_SLOT)) {",
     "replace": "    for (const s of mine.slice(10000)) {",
     "matches": 1},
    {"why": "#208 - an unreadable index reads as an empty one, and the next write overwrites what it never saw",
     "file": "functions/api/roster.js",
     "find": "  } catch (e) { return null; }\n}\n\nasync function reelIndexPut",
     "replace": "  } catch (e) { return { sessions: {} }; }\n}\n\nasync function reelIndexPut",
     "matches": 1},
    {"why": "#208 - a demotion keeps every frame it held, so a summary still costs a full session's bytes",
     "file": "functions/api/roster.js",
     "find": "        if (body.frames.indexOf(n) !== -1) { have[n] = prev.have[n]; kept += prev.have[n]; } else dropped.push(n);",
     "replace": "        { have[n] = prev.have[n]; kept += prev.have[n]; }",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
