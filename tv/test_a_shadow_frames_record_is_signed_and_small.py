# -*- coding: utf-8 -*-
"""#218 phase 2 (REG-2771, his ruling 2026-10-28) - THE OWNER'S SESSIONS RIDE THEIR OWN SIGNED RECORD, SMALL PICTURES ONLY.

A shadow renders the owner's data one to one, with SUMMARIZED frames: "a few small key frames per session". The profile
still refuses every picture (his 10-07 ruling - pictures stay on that PC); the frames digest (shadow_sessions.digest) is
the ONE record a picture rides, and the worker checks it, never trusts it: at most 16 sessions, 3 frames each, every
frame a read frame's id and a 160 px JPEG under 20 KB, no path or token anywhere, the hash the owner signed. It answers
to the same registered key, intent and replay rule as the profile through ONE shared gate (signedOwnerIntent,
signedAtRefusal, signedByRegisteredNow - moved verbatim from the profile door, so a second kind added a caller, never a
second copy of a safety routine). Stored as roster:<owner>:frames, change-only, at most every 3 h unless the console
just started, 8 a day; GET /api/roster?frames=<owner> reads it back.

Driven on functions/api/roster.js as it ships, in node, on a fake KV, with real signing keys. RED_PROOF below.
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
import console_snapshot as CS  # noqa: E402
import roster_sign as RS  # noqa: E402

NODE = shutil.which("node")
ROSTER_JS = os.path.join(ROOT, "functions", "api", "roster.js")
OWNER = "Dean"
T0 = 1792800000000
JPG = "/9j/4AAQSkZJRgABAQAAAQABAAD" + "A" * 120 + "=="

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
const out = { steps: [] };
for (const step of (CFG.steps || [])) {
  puts = [];
  const realNow = Date.now;
  if (typeof step.now === 'number') Date.now = () => step.now;
  if (step.get) {
    const res = await mod.onRequestGet({ request: new Request('https://bull-4-u.com/api/roster?frames=' + encodeURIComponent(step.get)),
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
process.stdout.write(JSON.stringify(out));
"""


def _node(cfg):
    with tempfile.TemporaryDirectory(prefix="tvd_frames_js_") as d:
        h, c = os.path.join(d, "h.mjs"), os.path.join(d, "cfg.json")
        io.open(h, "w", encoding="utf-8").write(_HARNESS)
        io.open(c, "w", encoding="utf-8").write(json.dumps(dict(cfg, file=ROSTER_JS)))
        r = subprocess.run([NODE, h, c], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    if r.returncode != 0:
        raise AssertionError("the frames harness failed rc=%s\n%s" % (r.returncode, r.stderr[-2000:]))
    return json.loads(r.stdout)


def _digest(n=2, frames=2, jpg=JPG, name="Shako"):
    return {"v": 1, "at": T0, "bytes": 0, "dropped": 0, "left": [],
            "sessions": [{"sessionId": "s_17928000%05d_%d" % (k, k + 1), "t0": T0 - 60000 * (k + 1), "t1": T0 - 60000 * k,
                          "reads": 5, "names": [name], "namesMore": 0, "why": None,
                          "frames": [{"id": "%d_17927999%05d" % (j + 1, k * 10 + j), "jpg": jpg} for j in range(frames)]}
                         for k in range(n)]}


@unittest.skipUnless(NODE, "node is absent - the worker is UNMEASURED here, never a pass")
class TheFramesRecord(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="tvd_frames_keys_")
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

    def _post(self, digest, key, now=T0, signed_at=None, boot=False, hash_=None):
        body = {"kind": "frames", "owner": OWNER, "boot": boot, "signedAt": now if signed_at is None else signed_at,
                "hash": CS.digest(digest) if hash_ is None else hash_, "digest": digest}
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        return {"raw": base64.b64encode(raw).decode("ascii"), "headers": RS.sign_headers(key, raw)[0] if key else {},
                "now": now}

    def test_a_signed_digest_lands_in_its_own_record_and_reads_back(self):
        d = _digest()
        out = _node({"seed": self.seed, "steps": [self._post(d, self.key_a), {"get": OWNER, "now": T0 + 5}]})
        post, got = out["steps"]
        self.assertEqual(post["puts"], ["roster:%s:frames" % OWNER], post["reply"])
        self.assertTrue(got["get"].get("published") and not got["get"].get("corrupt"), got["get"])
        self.assertEqual(got["get"]["digest"], d, "the digest did not read back byte for byte")

    def test_a_digest_past_the_profile_cap_reaches_its_own_door(self):
        """REG-2794 (the v3829 second eye) - the door's first check was the profile's 200 KB, so any real digest past it
        (16 sessions with one small thumbnail each is ~290 KB) was refused as "too large to be rows"."""
        d = _digest(n=16, frames=1, jpg="/9j/" + "A" * 18000)
        post = self._post(d, self.key_a)
        self.assertGreater(len(base64.b64decode(post["raw"])), 200000, "PREMISE: the digest is not past the profile cap")
        out = _node({"seed": self.seed, "steps": [post]})
        st = out["steps"][0]
        self.assertTrue(st["reply"].get("ok"), "a digest within its own 900 KB cap was refused: %r" % st["reply"])
        self.assertEqual(st["puts"], ["roster:%s:frames" % OWNER])

    def test_an_unsigned_or_foreign_upload_stores_nothing(self):
        out = _node({"seed": self.seed, "steps": [self._post(_digest(), None), self._post(_digest(), self.key_b)]})
        for st in out["steps"]:
            self.assertFalse(st["reply"].get("ok"), st["reply"])
            self.assertEqual(st["puts"], [], "a frames upload not signed by the owner's key was stored")

    def test_only_small_jpeg_thumbnails_of_read_frames_ride(self):
        bad = {
            "big": _digest(jpg="/9j/" + "A" * 27500),
            "png": _digest(jpg="iVBORw0KGgoAAAANSUhEUg" + "A" * 40),
            "four": _digest(frames=4),
            "seventeen": _digest(n=17, frames=1),
            "path": _digest(name="/" + "Users/x/secret"),
        }
        steps = [self._post(d, self.key_a, now=T0 + i) for i, d in enumerate(bad.values())]
        out = _node({"seed": self.seed, "steps": steps})
        for name, st in zip(bad, out["steps"]):
            self.assertFalse(st["reply"].get("ok"), "%s was accepted: %r" % (name, st["reply"]))
            self.assertEqual(st["puts"], [], "%s was stored" % name)

    def test_a_digest_that_is_not_what_was_signed_is_refused(self):
        out = _node({"seed": self.seed, "steps": [self._post(_digest(), self.key_a, hash_="deadbeef")]})
        self.assertFalse(out["steps"][0]["reply"].get("ok"))
        self.assertIn("hash", out["steps"][0]["reply"].get("why", ""))

    def test_change_only_every_3_hours_and_never_a_replay(self):
        d, d2 = _digest(), _digest(name="Harlequin Crest")
        steps = [self._post(d, self.key_a, now=T0),
                 self._post(d, self.key_a, now=T0 + 60000),                    # the same digest: unchanged
                 self._post(d2, self.key_a, now=T0 + 120000),                  # changed, within 50 min
                 self._post(d2, self.key_a, now=T0 + 180000, boot=True),       # a console start may publish now
                 self._post(d2, self.key_a, now=T0 + 240000, signed_at=T0 + 1)]  # an older signature: a replay
        out = _node({"seed": self.seed, "steps": steps})
        r = [s["reply"] for s in out["steps"]]
        self.assertEqual(out["steps"][0]["puts"], ["roster:%s:frames" % OWNER])
        self.assertEqual(r[1].get("skipped"), ["unchanged"], r[1])
        self.assertEqual(r[2].get("skipped"), ["within 50 min"], r[2])
        self.assertEqual(out["steps"][3]["puts"], ["roster:%s:frames" % OWNER], "a console start could not publish: %r" % r[3])
        self.assertFalse(r[4].get("ok"), "a replayed (older) signature was accepted: %r" % r[4])

    def test_the_profile_still_refuses_every_picture(self):
        src = io.open(ROSTER_JS, encoding="utf-8").read()
        self.assertEqual(src.count('return pRefuse("pictures stay on that PC")'), 1,
                         "the profile door lost its picture refusal - a frame may ride only the frames record")


RED_PROOF = [
    {"why": "REG-2794 - the door's first cap is the profile's 200 KB again, so a real digest never reaches its own door",
     "file": "functions/api/roster.js",
     "find": "  if (bytes.byteLength > FRAMES_MAX_BODY) {\n    return refuse(\"roster would not take this publish: the body is larger than any record it keeps\");\n",
     "replace": "  if (bytes.byteLength > PROFILE_MAX_BODY) {\n    return refuse(\"roster would not take this publish: the body is larger than any record it keeps\");\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2771 - the frames door does not exist (a digest is refused or lost)",
     "file": "functions/api/roster.js",
     "find": "  if (body.kind === \"frames\") return framesPost(env, bytes, sig, body);\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2771 - a large picture rides as a thumbnail",
     "file": "functions/api/roster.js",
     "find": "      if (!f || typeof f !== \"object\" || !FID_RX.test(String(f.id || \"\"))) return \"a frame id is not a read frame's\";\n      if (typeof f.jpg !== \"string\" || f.jpg.length > FRAMES_MAX_JPG_B64 || f.jpg.indexOf(\"/9j/\") !== 0\n",
     "replace": "      if (!f || typeof f !== \"object\" || !FID_RX.test(String(f.id || \"\"))) return \"a frame id is not a read frame's\";\n      if (typeof f.jpg !== \"string\" || f.jpg.indexOf(\"/9j/\") !== 0\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2771 - any picture format rides",
     "file": "functions/api/roster.js",
     "find": "      if (!f || typeof f !== \"object\" || !FID_RX.test(String(f.id || \"\"))) return \"a frame id is not a read frame's\";\n      if (typeof f.jpg !== \"string\" || f.jpg.length > FRAMES_MAX_JPG_B64 || f.jpg.indexOf(\"/9j/\") !== 0\n",
     "replace": "      if (!f || typeof f !== \"object\" || !FID_RX.test(String(f.id || \"\"))) return \"a frame id is not a read frame's\";\n      if (typeof f.jpg !== \"string\" || f.jpg.length > FRAMES_MAX_JPG_B64\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2771 - a path or token in a session's names rides",
     "file": "functions/api/roster.js",
     "find": "  if (privateIn(text)) return \"the digest carries a path, an install id or a token\";\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2771 - the frames door skips the owner's key",
     "file": "functions/api/roster.js",
     "find": "  const intent = await signedOwnerIntent(kv, owner, sig);\n  if (intent instanceof Response) return intent;\n  const why = framesWhy(body.digest);\n",
     "replace": "  const intent = { keyId: null };\n  const why = framesWhy(body.digest);\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2771 - every change publishes at once, no 3 h gap",
     "file": "functions/api/roster.js",
     "find": "  if (prev && samePub && age < FRAMES_MIN_GAP_MS && body.boot !== true) {\n",
     "replace": "  if (false) {\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2771 - more than 3 frames ride a session",
     "file": "functions/api/roster.js",
     "find": "    if (!Array.isArray(s.frames) || s.frames.length > FRAMES_MAX_PER) return",
     "replace": "    if (!Array.isArray(s.frames)) return",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
