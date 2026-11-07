#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REG-2510..REG-2515 (#95, #112) - a roster publish is signed, and a forgery is refused.

His ruling, 2026-10-22: deploy signed roster publishing once the cross-language (Python/JS) signature
test passes; trust-on-first-use; never stop a PC from publishing. THIS FILE IS THAT TEST. Python signs
(both signers: `cryptography` where it is installed, the RFC 8032 signer everywhere) and node runs the
REAL functions/api/roster.js onRequestPost and onRequestGet against a stand-in KV, with the two headers.

What it holds, one acceptance line of the build each:
  * unsigned, no key registered: stored intentVerified:false, so a PC that has not updated still publishes
  * signed, no key registered: the key is registered and the row is stored intentVerified:true
  * after that, unsigned / another key / one flipped bit: each refused, and the KV is byte-identical
  * RFC 8032 section 7.1 vectors pass on both signers, and node verifies them
  * 200 random bodies up to MAX_BODY sign here and verify in node; the two signers agree on every one
  * a string with an emoji no longer reads corrupt (the hash walks UTF-16 units, as the worker does)
  * the key never appears in a response, a receipt, a page, a header or a body
  * a boot publish goes even when nothing changed, so this PC's first signed publish comes at its next boot
  * a verified row holds only sections its own key signed (REG-2516): a section planted unsigned, written
    before signing, or another key's is dropped at the first signed publish, never stamped verified - the
    same key keeps what it signed before, and an unsigned write still merges, stored NOT verified
  * intentVerified travels with every view, the cache file, the panel's payload and roster_html, and a
    row published before signing reads UNKNOWN
  * the console's roster panel and shadow bar draw each row's signature and this PC's own last publish
    (REG-2517): the route's own lines serve real files, and the panel's own code, run in node, draws them
  * the boot sweep of d2jsp scratch (#112) is called exactly once, synchronously, inside a guard

VENUES. Every case that runs roster.js needs node; where node is absent it SKIPS and says so, and its
red-proofs declare needs: node. `cryptography` is needed only for the agreement half; where it is absent
that case SKIPS and says so - never a silent pass. CI's tv-tests job installs it.
"""

import ast
import base64
import html
import io
import json
import os
import random
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import roster_publish as RP  # noqa: E402
import roster_sign as RS  # noqa: E402
from console_safe import enable  # noqa: E402

enable()

NODE = shutil.which("node")
ROSTER_JS = os.path.join(ROOT, *"functions/api/roster.js".split("/"))
APP = os.path.join(HERE, "control_app.py")
UI = os.path.join(HERE, "control_ui.html")
DOCTOR = os.path.join(HERE, "console_doctor.py")
OWNER = "Konyo · Mac"
MAX_BODY = 80000
SIGNATURE_HINT = "the key registered for this owner did not sign this publish"
STORAGE_HINT = "this is the storage refusing a write"

#: RFC 8032 section 7.1: TEST 1, TEST 2, TEST 3 and TEST SHA(abc) - secret, public, message, signature.
RFC8032 = (
    ("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
     "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
     "",
     "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
    ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
     "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
     "72",
     "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
    ("c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7",
     "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025",
     "af82",
     "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"),
    ("833fe62409237b9d62ec77587520911e9a759cec1d19755b7da901b96dca3d42",
     "ec172b93ad5e563bf4932c70e1245034c35467ef2efd4d64ebf819683467e2bf",
     "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a"
     "2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f",
     "dc2a4459e7369633a52b1bf277839a00201009a3efbf3ecb69bea2186c26b58909351fc9ac90b3ecfdfbc7c66431e0303dca179c138ac17ad9bef1177331a704"),
)

# The worker, run as it ships. Each step posts EXACT bytes (base64 here, so nothing re-serialises them)
# with its own headers; `fresh` starts a new store (optionally seeded). Every step reports what it wrote
# and a digest of every KV value before and after, so "nothing was stored" is measured, not assumed.
_HARNESS = r"""
import { pathToFileURL } from 'node:url';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const CFG = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const bytes = (s) => new Uint8Array(Buffer.from(s || '', 'base64'));
const digest = (s) => createHash('sha256').update(s).digest('hex');
const seeded = (seed) => new Map(Object.entries(seed || {}).map(([k, v]) => [k, typeof v === 'string' ? v : JSON.stringify(v)]));
let store = seeded(CFG.seed);
let puts = [];
let failPut = [];
let putOpts = {};
const kv = {
  async get(n) { return store.has(n) ? store.get(n) : null; },
  // a step may name the keys whose put fails, the way a KV outage answers
  async put(n, v, o) { if (failPut.includes(n)) throw new Error('KV put failed'); puts.push(n); putOpts[n] = o || null; store.set(n, v); },
};
const snap = () => { const o = {}; for (const [k, v] of store.entries()) o[k] = digest(v); return o; };
const parsed = (v) => { try { return JSON.parse(v); } catch (e) { return v; } };
const mod = await import(pathToFileURL(CFG.file).href);
const out = { steps: [], verify: [], records: null, got: null };
for (const step of (CFG.steps || [])) {
  if (step.fresh) store = seeded(step.seed);
  puts = [];
  failPut = step.failPut || [];
  putOpts = {};
  // a step may name the server's clock (an exact-hour edge); every other step runs on the real one
  const realNow = Date.now;
  if (typeof step.now === 'number') Date.now = () => step.now;
  const before = snap();
  const req = new Request('https://bull-4-u.com/api/roster', {
    method: 'POST', body: bytes(step.raw),
    headers: Object.assign({ 'content-type': 'application/json' }, step.headers || {}) });
  const res = await mod.onRequestPost({ request: req, env: { TZ_HISTORY: kv }, waitUntil() {} });
  const reply = JSON.parse(await res.text());
  Date.now = realNow;
  const one = { status: res.status, reply: reply, puts: puts, putOpts: putOpts, before: before, after: snap() };
  if (CFG.everyRecord) { one.records = {}; for (const [k, v] of store.entries()) one.records[k] = parsed(v); }
  out.steps.push(one);
}
for (const v of (CFG.verify || [])) {
  let ok = null, err = null;
  try {
    const key = await crypto.subtle.importKey('raw', bytes(v.pub), { name: 'Ed25519' }, false, ['verify']);
    ok = await crypto.subtle.verify({ name: 'Ed25519' }, key, bytes(v.sig), bytes(v.msg));
  } catch (e) { err = String((e && e.name) || e); }
  out.verify.push({ ok: ok, err: err });
}
out.records = {};
for (const [k, v] of store.entries()) out.records[k] = parsed(v);
if (CFG.get) {
  const res = await mod.onRequestGet({ request: new Request('https://bull-4-u.com/api/roster', { method: 'GET' }),
                                       env: { TZ_HISTORY: kv }, waitUntil() {} });
  out.got = { status: res.status, body: JSON.parse(await res.text()) };
}
process.stdout.write(JSON.stringify(out));
"""


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _need_node(case):
    if not NODE:
        case.skipTest("node is absent - roster.js cannot be run on this PC, so this case is UNMEASURED "
                      "here, not passed")


def _node(cfg, timeout=240):
    cfg = dict(cfg, file=ROSTER_JS)
    with tempfile.TemporaryDirectory(prefix="tvd_roster_sig_") as d:
        harness = os.path.join(d, "h.mjs")
        with io.open(harness, "w", encoding="utf-8") as fh:
            fh.write(_HARNESS)
        conf = os.path.join(d, "cfg.json")
        with io.open(conf, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh)
        r = subprocess.run([NODE, harness, conf], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    if r.returncode != 0:
        raise AssertionError("the roster harness failed rc=%s\n%s" % (r.returncode, r.stderr[-2000:]))
    return json.loads(r.stdout)


def _b64(raw):
    return base64.b64encode(bytes(raw)).decode("ascii")


def _raw(body):
    """The bytes the console posts: _roster_post's own serialiser."""
    return json.dumps(body, ensure_ascii=False).encode("utf-8")


def _body(n=1, boot=True, signed_at=1790000000000, name="Sorceress"):
    return {"owner": OWNER, "boot": boot, "signedAt": signed_at,
            "sections": {"characters": {"asOf": 1000, "counts": n,
                                        "rows": [{"name": name, "cls": "Sorceress", "level": n}]}}}


def _step(raw, headers=None, fresh=False, seed=None, now=None, fail_put=None):
    one = {"raw": _b64(raw), "headers": dict(headers or {})}
    if fail_put:
        one["failPut"] = list(fail_put)
    if now is not None:
        one["now"] = now
    if fresh:
        one["fresh"] = True
        one["seed"] = seed or {}
    return one


def _flip_one_bit(raw):
    """One bit of one digit of signedAt: a digit XOR 1 is still a digit, so the body is still JSON and
    the only thing a refusal can be about is the signature."""
    at = raw.index(b'"signedAt":') + len(b'"signedAt":')
    while raw[at:at + 1] == b" ":
        at += 1
    at += 3
    if not raw[at:at + 1].isdigit():
        raise AssertionError("the fixture's signedAt is not a 4+ digit number")
    return raw[:at] + bytes([raw[at] ^ 1]) + raw[at + 1:]


def _key(folder):
    """A real key file made by the real code, in a fixture folder. -> (path, seed, pub)"""
    path = RS.key_path_in(folder)
    key, why, made = RS.load_or_create(path)
    if key is None:
        raise AssertionError("no fixture key could be made: %s" % why)
    with io.open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return path, RS.unb64u(data["seed"]), RS.unb64u(data["pub"])


def _registered(pub):
    return {"rosterkey:" + OWNER: {"pub": RS.b64u(pub), "keyId": RS.key_id(pub), "at": 1}}


def _secret_forms(seed):
    """Every spelling of a seed a leak could take."""
    return (RS.b64u(seed), base64.b64encode(seed).decode("ascii"), seed.hex(), seed.hex().upper())


class TheTwoSignersAgree(unittest.TestCase):
    """RFC 8032 is deterministic: two correct signers write the same 64 bytes. That pair is the
    corroborator, and node's crypto.subtle (the worker's own verifier) is the judge."""

    def test_the_rfc8032_vectors_pass_on_the_pure_signer(self):
        for secret, public, message, signature in RFC8032:
            seed, msg = bytes.fromhex(secret), bytes.fromhex(message)
            self.assertEqual(RS.pure_public(seed).hex(), public, "RFC 8032 public key, TEST %s" % public[:8])
            sig = RS.pure_sign(seed, msg)
            self.assertEqual(sig.hex(), signature, "RFC 8032 signature, TEST %s" % public[:8])
            self.assertTrue(RS.pure_verify(bytes.fromhex(public), msg, sig))
            bad = bytearray(sig)
            bad[7] ^= 1
            self.assertFalse(RS.pure_verify(bytes.fromhex(public), msg, bytes(bad)))

    def test_the_rfc8032_vectors_pass_on_cryptography(self):
        if not RS.have_cryptography():
            self.skipTest("cryptography is not installed on this PC - the second signer is UNMEASURED here, "
                          "not passed (CI's tv-tests job installs it)")
        for secret, public, message, signature in RFC8032:
            seed, msg = bytes.fromhex(secret), bytes.fromhex(message)
            self.assertEqual(RS.crypto_public(seed).hex(), public)
            self.assertEqual(RS.crypto_sign(seed, msg).hex(), signature)

    def test_node_verifies_the_rfc8032_vectors(self):
        _need_node(self)
        checks = []
        for _secret, public, message, signature in RFC8032:
            sig = bytes.fromhex(signature)
            checks.append({"pub": _b64(bytes.fromhex(public)), "sig": _b64(sig), "msg": _b64(bytes.fromhex(message))})
            bad = bytearray(sig)
            bad[40] ^= 1
            checks.append({"pub": _b64(bytes.fromhex(public)), "sig": _b64(bytes(bad)),
                           "msg": _b64(bytes.fromhex(message))})
        got = _node({"verify": checks})["verify"]
        self.assertEqual([g["ok"] for g in got], [True, False] * len(RFC8032),
                         "node's crypto.subtle did not accept the RFC 8032 vectors and refuse a flipped bit: %r" % got)

    def test_the_two_signers_agree_on_two_hundred_bodies(self):
        if not RS.have_cryptography():
            self.skipTest("cryptography is not installed on this PC - the agreement half is UNMEASURED here, "
                          "not passed (CI's tv-tests job installs it)")
        got = _sample()
        self.assertEqual(RS.crypto_public(got["seed"]), got["pub"])
        for i, raw in enumerate(got["bodies"]):
            self.assertEqual(RS.crypto_sign(got["seed"], raw), got["sigs"][i],
                             "the two signers wrote different signatures for body %d (%d bytes)" % (i, len(raw)))

    def test_a_pc_without_cryptography_still_signs(self):
        """tv/install-tvd.ps1 and tv/install-tvd.sh do not install cryptography: Dean, ALT and Wife PC
        sign with the RFC 8032 signer, and a cryptography that raises does not stop a publish."""
        with tempfile.TemporaryDirectory(prefix="tvd_roster_key_") as d:
            path, seed, pub = _key(d)
            key, _why = RS.load_key(path)
            raw = _raw(_body(3))
            real = RS.crypto_sign
            try:
                RS.crypto_sign = lambda s, m: None
                sig, signer, agree = RS.sign(key, raw)
                self.assertEqual((signer, agree), ("pure-python", None))
                self.assertTrue(RS.pure_verify(pub, raw, sig))

                def boom(s, m):
                    raise ValueError("an OpenSSL this cryptography cannot use")
                RS.crypto_sign = boom
                sig2, signer2, _agree = RS.sign(key, raw)
                self.assertIn("cryptography raised ValueError", signer2)
                self.assertEqual(sig2, sig)
            finally:
                RS.crypto_sign = real


def _random_name(rng):
    pool = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -'"
            "éüßñÆØשלום日本語★✓"
            "\U0001f9ff\U0001f525\U0001f48e\U0001f480")
    return "".join(rng.choice(pool) for _ in range(rng.randint(1, 40))).strip() or "Shako"


_SAMPLE = {}


def _sample():
    """200 random bodies up to MAX_BODY, each signed once by the RFC 8032 signer. Built once a run and
    shared, because both the agreement case and the node case need the same 200."""
    if not _SAMPLE:
        rng = random.Random(9501)
        seed = bytes(rng.getrandbits(8) for _ in range(32))
        bodies = [_random_body(rng, rng.randint(64, MAX_BODY)) for _ in range(200)]
        _SAMPLE.update(seed=seed, pub=RS.pure_public(seed), bodies=bodies,
                       sigs=[RS.pure_sign(seed, raw) for raw in bodies])
    return _SAMPLE


def _random_body(rng, target):
    """A roster body the worker accepts, as close under `target` bytes as its rows allow (<= MAX_BODY)."""
    base = {"owner": OWNER, "boot": True, "signedAt": rng.randint(10 ** 12, 2 * 10 ** 12),
            "sections": {"characters": {"asOf": rng.randint(1, 10 ** 12), "counts": 0, "rows": []}}}
    used = len(_raw(base)) + 8
    rows = []
    while True:
        row = {"name": _random_name(rng), "level": rng.randint(1, 99)}
        size = len(_raw(row)) + 2                      # json.dumps writes ", " between rows
        if used + size > target:
            break
        rows.append(row)
        used += size
    if not rows:
        rows.append({"name": "Shako", "level": 1})
    while True:
        base["sections"]["characters"]["rows"] = rows
        base["sections"]["characters"]["counts"] = len(rows)
        raw = _raw(base)
        if len(raw) <= min(target, MAX_BODY) or len(rows) == 1:
            break
        rows = rows[:-1]
    if len(raw) > MAX_BODY:
        raise AssertionError("the fixture built a body over MAX_BODY (%d bytes)" % len(raw))
    return raw


class TheWorkerChecksTheBytesItWasSent(unittest.TestCase):
    """roster.js, run as it ships, against signatures made here."""

    def test_two_hundred_random_bodies_sign_here_and_verify_in_node(self):
        _need_node(self)
        got = _sample()
        pub = got["pub"]
        heads = {"X-Roster-Key": RS.b64u(pub)}
        steps, checks, sizes = [], [], []
        for raw, sig in zip(got["bodies"], got["sigs"]):
            sizes.append(len(raw))
            signed = dict(heads, **{"X-Roster-Sig": RS.b64u(sig)})
            steps.append(_step(raw, signed, fresh=True))                                    # no key yet
            steps.append(_step(_flip_one_bit(raw), signed, fresh=True, seed=_registered(pub)))  # key held
            checks.append({"pub": _b64(pub), "sig": _b64(sig), "msg": _b64(raw)})
        self.assertGreater(max(sizes), MAX_BODY - 2000, "the sample never came near MAX_BODY")
        v = _node({"steps": steps, "verify": checks})
        self.assertEqual([c["ok"] for c in v["verify"]], [True] * 200,
                         "node's crypto.subtle refused a signature made here")
        for i in range(200):
            good, bad = v["steps"][2 * i], v["steps"][2 * i + 1]
            self.assertEqual((good["reply"].get("ok"), good["reply"].get("intentVerified"),
                              good["reply"].get("registered")), (True, True, True),
                             "body %d (%d bytes) did not verify through roster.js: %r"
                             % (i, sizes[i], good["reply"]))
            self.assertIs(bad["reply"].get("ok"), False, "a flipped bit in body %d was stored" % i)
            self.assertIn("did not verify", bad["reply"].get("why", ""))
            self.assertEqual(bad["puts"], [], "a refused body %d wrote %r" % (i, bad["puts"]))

    def test_the_acceptance_sequence(self):
        """unsigned -> stored false; signed -> registered, true; then unsigned / another key / one flipped
        bit -> refused with the KV byte-identical; signed again -> true. GET says so."""
        _need_node(self)
        with tempfile.TemporaryDirectory(prefix="tvd_roster_key_") as d:
            path_a, seed_a, pub_a = _key(os.path.join(d, "a"))
            path_b, seed_b, pub_b = _key(os.path.join(d, "b"))
            raws = [_raw(_body(n, signed_at=1790000000000 + n)) for n in range(1, 7)]
            heads = {n: RS.sign_headers(path_a, raws[n - 1])[0] for n in (2, 5, 6)}
            other, _ = RS.sign_headers(path_b, raws[3])
            steps = [_step(raws[0]),                                  # 0 unsigned, no key
                     _step(raws[1], heads[2]),                        # 1 signed A, no key: TOFU
                     _step(raws[2]),                                  # 2 unsigned after that
                     _step(raws[3], other),                           # 3 another key
                     _step(_flip_one_bit(raws[4]), heads[5]),         # 4 one bit flipped
                     _step(raws[5], heads[6])]                        # 5 signed A again
            v = _node({"steps": steps, "get": True, "everyRecord": True})
        rk, kk = "roster:" + OWNER, "rosterkey:" + OWNER
        s = v["steps"]
        self.assertEqual((s[0]["reply"]["ok"], s[0]["reply"]["stored"], s[0]["reply"]["intentVerified"]),
                         (True, ["roster"], False), "an unsigned first publish must still be stored: %r" % s[0]["reply"])
        self.assertEqual(s[0]["puts"], [rk])
        self.assertNotIn(kk, s[0]["after"], "an unsigned publish registered a key")
        self.assertIs(s[0]["records"][rk]["intentVerified"], False)
        self.assertEqual((s[1]["reply"]["ok"], s[1]["reply"]["intentVerified"], s[1]["reply"].get("registered")),
                         (True, True, True), "the first signed publish did not register its key: %r" % s[1]["reply"])
        self.assertEqual(s[1]["reply"]["keyId"], RS.key_id(pub_a))
        self.assertEqual(s[1]["puts"], [kk, rk])
        self.assertEqual(s[1]["records"][kk]["pub"], RS.b64u(pub_a))
        for i, word in ((2, "not signed"), (3, "different key"), (4, "did not verify")):
            r = s[i]["reply"]
            self.assertEqual(s[i]["status"], 200)
            self.assertIs(r["ok"], False, "step %d was not refused: %r" % (i, r))
            self.assertIn(word, r["why"])
            self.assertIn(SIGNATURE_HINT, r["hint"], "step %d's refusal carried the wrong hint" % i)
            self.assertNotIn(STORAGE_HINT, r["hint"])
            # v3862 (REG-3163) - a VALID signature under a different key leaves ONE pending request for his approval;
            # it never touches the row or the registered key. Every other refusal writes nothing.
            req = ["rosterkeyreq:" + OWNER] if word == "different key" else []
            self.assertEqual(s[i]["puts"], req, "a refused step %d wrote %r" % (i, s[i]["puts"]))
            self.assertEqual({k: v for k, v in s[i]["after"].items() if not k.startswith("rosterkeyreq:")},
                             {k: v for k, v in s[i]["before"].items() if not k.startswith("rosterkeyreq:")},
                             "a refused step %d changed the KV beyond a pending request" % i)
        self.assertEqual(s[3]["reply"].get("offered"), RS.key_id(pub_b))
        self.assertEqual(s[3]["reply"].get("keyId"), RS.key_id(pub_a))
        self.assertEqual((s[5]["reply"]["ok"], s[5]["reply"]["intentVerified"], s[5]["reply"]["stored"]),
                         (True, True, ["roster"]))
        self.assertNotIn("registered", s[5]["reply"], "a registered key was registered again")
        rec = v["records"][rk]
        self.assertEqual((rec["intentVerified"], rec["keyId"], rec["signedAt"]),
                         (True, RS.key_id(pub_a), 1790000000006))
        mine = [r for r in v["got"]["body"]["owners"] if r["owner"] == OWNER][0]
        self.assertEqual((mine["corrupt"], mine["intentVerified"], mine["keyId"]), (False, True, RS.key_id(pub_a)))
        view = [r for r in RP.view_of(v["got"]["body"]["owners"], rec["t"]) if r["owner"] == OWNER][0]
        self.assertEqual((view["corrupt"], view["intentVerified"], view["keyId"]), (False, True, RS.key_id(pub_a)))
        # the key never leaves its file: not in a body, a header, a reply, a record or the page
        seen = json.dumps(v, ensure_ascii=False) + json.dumps(heads) + json.dumps(other)
        seen += "".join(r.decode("utf-8") for r in raws)
        seen += RP.roster_html({"ok": True, "fetched": True, "now": rec["t"], "owners": [view]})
        for seed in (seed_a, seed_b):
            for form in _secret_forms(seed):
                self.assertNotIn(form, seen, "a private key reached a body, a header, a reply or a record")

    def test_no_key_and_a_bad_signature_is_stored_unverified_and_registers_nothing(self):
        """Anyone could post that row unsigned, and a signer bug must not stop a PC from publishing - so
        it is stored, said false, and the key is NOT registered. The reply says why."""
        _need_node(self)
        with tempfile.TemporaryDirectory(prefix="tvd_roster_key_") as d:
            path, _seed, pub = _key(d)
            raw = _raw(_body(2))
            heads, _ = RS.sign_headers(path, raw)
            half = {"X-Roster-Key": heads["X-Roster-Key"]}
            v = _node({"steps": [_step(_flip_one_bit(raw), heads, fresh=True),
                                 _step(raw, half, fresh=True),
                                 _step(raw, half, fresh=True, seed=_registered(pub))]})
        rk, kk = "roster:" + OWNER, "rosterkey:" + OWNER
        for i in (0, 1):
            r = v["steps"][i]["reply"]
            self.assertEqual((r["ok"], r["intentVerified"], r["sig"]), (True, False, "bad"), r)
            self.assertTrue(r.get("sigWhy"), "a bad signature was stored without saying why")
            self.assertNotIn("registered", r)
            self.assertEqual(v["steps"][i]["puts"], [rk], "a bad signature registered a key")
        r = v["steps"][2]["reply"]
        self.assertIs(r["ok"], False, "half a signature was stored for an owner whose key is registered")
        self.assertEqual(v["steps"][2]["puts"], [])
        self.assertNotIn(kk, v["steps"][0]["after"])

    def test_a_key_konyo_put_there_by_hand_is_honoured(self):
        """A key changes only from the Mac: a pre-seeded key - the record this file writes, or the bare
        base64url string - is the owner's from then on, and a key that cannot be read refuses rather than
        letting anyone in."""
        _need_node(self)
        with tempfile.TemporaryDirectory(prefix="tvd_roster_key_") as d:
            path, _seed, pub = _key(d)
            raw = _raw(_body(3))
            heads, _ = RS.sign_headers(path, raw)
            kk = "rosterkey:" + OWNER
            v = _node({"steps": [_step(raw, heads, fresh=True, seed={kk: RS.b64u(pub)}),
                                 _step(raw, {}, fresh=True, seed={kk: RS.b64u(pub)}),
                                 _step(raw, heads, fresh=True, seed={kk: "not a key"}),
                                 _step(raw, heads, fresh=True, seed={kk: "null"})]})
        hand, bare, junk, empty = (st["reply"] for st in v["steps"])
        self.assertEqual((hand["ok"], hand["intentVerified"]), (True, True), hand)
        self.assertNotIn("registered", hand, "a key Konyo put there was registered over")
        self.assertEqual(v["steps"][0]["puts"], ["roster:" + OWNER])
        self.assertIs(bare["ok"], False, "an unsigned publish got past a hand-placed key")
        self.assertIs(junk["ok"], False, "a key that cannot be read let a publish through")
        self.assertIn("unreadable", junk["why"])
        self.assertEqual(v["steps"][2]["puts"], [])
        self.assertIs(empty["ok"], False, "a key entry holding JSON null was read as no key at all - TOFU reopened")
        self.assertEqual(v["steps"][3]["puts"], [])

    def test_a_row_published_before_signing_reads_unknown(self):
        """A record written before #95 has no intentVerified. GET passes none, and every view shows
        UNKNOWN ('published before signing') - never verified, never unverified."""
        _need_node(self)
        sections = {"characters": {"asOf": 10, "counts": 1, "rows": [{"name": "Sorceress"}]}}
        digest = RP.hash_of(RP.packed(RP.for_hash(sections)))
        seed = {"roster:Dean": {"owner": "Dean", "t": 10, "day": "2000-01-01", "n": 1, "hash": digest,
                                "sections": sections}}
        got = _node({"seed": seed, "get": True})["got"]["body"]
        dean = [r for r in got["owners"] if r["owner"] == "Dean"][0]
        self.assertIs(dean["corrupt"], False)
        self.assertNotIn("intentVerified", dean, "a row published before signing was given a verdict")
        view = [r for r in RP.view_of(got["owners"], 10) if r["owner"] == "Dean"][0]
        self.assertIsNone(view["intentVerified"])
        page = RP.roster_html({"ok": True, "fetched": True, "now": 10, "owners": [view]})
        self.assertIn("signature UNKNOWN: published before signing", page)
        self.assertNotIn("signature verified", page)
        self.assertNotIn("NOT signature-verified", page)

    def test_a_boot_publish_heals_a_forged_row(self):
        """A row someone else wrote in this PC's name (before its key was registered) is overwritten by the
        PC's next boot publish, even though nothing changed on the PC."""
        _need_node(self)
        now = 1790000000000
        mine = RP.sections_from({"characters": {"read": True, "asOf": 1000, "counts": 1,
                                                 "rows": [{"name": "Sorceress", "level": 90}]}})
        state = {"hash": RP.hash_of(RP.packed(RP.for_hash(mine))), "at": now - 60000}
        body, why = RP.due(state, OWNER, mine, now, True)
        self.assertEqual(why, "post")
        forged = _body(99, name="Forged")
        with tempfile.TemporaryDirectory(prefix="tvd_roster_key_") as d:
            path, _seed, _pub = _key(d)
            raw = _raw(body)
            heads, signing = RS.sign_headers(path, raw)
            self.assertIs(signing["signed"], True)
            v = _node({"steps": [_step(_raw(forged)), _step(raw, heads)]})
        rec = v["records"]["roster:" + OWNER]
        self.assertEqual(rec["sections"]["characters"]["rows"][0]["name"], "Sorceress",
                         "the forged row survived the PC's boot publish")
        self.assertIs(rec["intentVerified"], True)

    def test_a_verified_row_holds_only_what_its_own_key_signed(self):
        """REG-2516 (#95, the review of REG-2510) - a signed publish merged EVERY section of the stored row into the new
        one and stamped the lot intentVerified:true with its key. No PC sends `owned` (control_app._roster_reads reads
        characters, stash, vault, chronicle and reels), so a row planted with the public password before the owner's key
        was registered kept its forged `owned` for good under "signature verified (key ...)", and the doctor read OK.
        A section is carried into a verified row only from a row written under the very same key - the whole key, not
        its 48-bit id - and an unsigned write still merges, stored NOT verified."""
        _need_node(self)
        rk, kk = "roster:" + OWNER, "rosterkey:" + OWNER
        forged = {"asOf": 1000, "counts": 1, "rows": [{"name": "FORGED Zod rune", "level": 1}]}
        mine = {"asOf": 2000, "counts": 1, "rows": [{"name": "Sorceress", "cls": "Sorceress", "level": 90}]}

        def body(sections, at):
            return {"owner": OWNER, "boot": True, "signedAt": 1790000000000 + at, "sections": sections}

        def record(sections, **extra):
            """A stored row as roster.js writes one, its hash made by this file's hash_of (the same digest)."""
            rec = {"owner": OWNER, "t": 10, "day": "2000-01-01", "n": 1, "sections": sections,
                   "hash": RP.hash_of(RP.packed(RP.for_hash(sections)))}
            rec.update(extra)
            return rec

        with tempfile.TemporaryDirectory(prefix="tvd_roster_key_") as d:
            path_a, _seed_a, pub_a = _key(os.path.join(d, "a"))
            _path_b, _seed_b, pub_b = _key(os.path.join(d, "b"))
            kid_a, kid_b = RS.key_id(pub_a), RS.key_id(pub_b)
            raws = {
                "plant": _raw(body({"characters": dict(mine, rows=[{"name": "FORGED Sorceress", "level": 1}]),
                                    "owned": forged}, 1)),
                "pc": _raw(body({"characters": mine}, 2)),
                "pc+vault": _raw(body({"characters": mine, "vault": {"asOf": 2000, "counts": 3}}, 3)),
                "pc91": _raw(body({"characters": dict(mine, rows=[dict(mine["rows"][0], level=91)])}, 4)),
            }
            heads = {k: RS.sign_headers(path_a, raw)[0] for k, raw in raws.items() if k != "plant"}
            both = {"characters": mine, "owned": forged}
            steps = [
                # 0-1 (E) unsigned writes, no key registered: still merged, and stored NOT verified
                _step(raws["plant"], fresh=True), _step(raws["pc"]),
                # 2 (B) a row written before signing (no verdict at all), then this PC's first signed publish
                _step(raws["pc"], heads["pc"], fresh=True, seed={rk: record(both)}),
                # 3 (C) another key's verified row, its key since reset from the Mac, then this PC's key registers
                _step(raws["pc"], heads["pc"], fresh=True, seed={rk: record(
                    both, intentVerified=True, keyId=kid_b, pub=RS.b64u(pub_b))}),
                # 4 (C2) a verified row that carries THIS key's 48-bit id but another key: the whole key decides
                _step(raws["pc"], heads["pc"], fresh=True, seed=dict(_registered(pub_a), **{rk: record(
                    both, intentVerified=True, keyId=kid_a, pub=RS.b64u(pub_b))})),
                # 5-6 (D) the same key keeps what it signed before and did not read this time
                _step(raws["pc+vault"], heads["pc+vault"], fresh=True), _step(raws["pc91"], heads["pc91"]),
                # 7-8 (A) planted unsigned while no key was registered, then this PC's first signed (boot) publish;
                #     last, so GET reads what every viewer would be handed
                _step(raws["plant"], fresh=True), _step(raws["pc"], heads["pc"]),
            ]
            v = _node({"steps": steps, "everyRecord": True, "get": True})
        s = v["steps"]
        for i, case in ((8, "A: planted unsigned"), (2, "B: written before signing"), (3, "C: another key's row"),
                        (4, "C2: same 48-bit id, another key")):
            r, rec = s[i]["reply"], s[i]["records"][rk]
            self.assertEqual((r["ok"], r["stored"], r["intentVerified"], r.get("keyId")), (True, ["roster"], True, kid_a),
                             "%s - the signed publish was not stored verified: %r" % (case, r))
            self.assertEqual(sorted(rec["sections"]), ["characters"],
                             "%s - a section this key never signed (%s) was stored under its 'signature verified' "
                             "(REG-2516)" % (case, sorted(set(rec["sections"]) - {"characters"})))
            self.assertEqual(rec["sections"]["characters"]["rows"], mine["rows"])
            self.assertEqual((rec["intentVerified"], rec["keyId"], rec["pub"]), (True, kid_a, RS.b64u(pub_a)))
            self.assertEqual(rec["hash"], RP.hash_of(RP.packed(RP.for_hash(rec["sections"]))),
                             "%s - the stored hash is not the hash of what was stored" % case)
        self.assertIs(s[7]["records"][rk]["intentVerified"], False)
        self.assertIn("owned", s[7]["records"][rk]["sections"], "the fixture's plant was never stored")
        for i in (3, 8):
            self.assertIs(s[i]["reply"].get("registered"), True, "step %d did not register this PC's key" % i)
            self.assertEqual(s[i]["puts"], [kk, rk])
        self.assertNotIn("registered", s[4]["reply"], "a key Konyo put there was registered over")
        self.assertEqual(s[4]["puts"], [rk])
        kept = s[6]["records"][rk]
        self.assertEqual(s[6]["reply"]["stored"], ["roster"], "the same key's second publish was not written: %r" % s[6]["reply"])
        self.assertEqual(sorted(kept["sections"]), ["characters", "vault"],
                         "the same key's next publish dropped a section it signed before and did not read this time")
        self.assertEqual(kept["sections"]["characters"]["rows"][0]["level"], 91)
        self.assertEqual((kept["intentVerified"], kept["pub"]), (True, RS.b64u(pub_a)))
        merged = s[1]["records"][rk]
        self.assertEqual((s[1]["reply"]["ok"], s[1]["reply"]["intentVerified"]), (True, False), s[1]["reply"])
        self.assertEqual(sorted(merged["sections"]), ["characters", "owned"],
                         "an unsigned write no longer keeps a section it did not send")
        self.assertIs(merged["intentVerified"], False)
        self.assertNotIn("pub", merged, "an unverified row names a key")
        # what every viewer is then handed: GET, the view and the page carry no planted row, under a verified key
        got = [r for r in v["got"]["body"]["owners"] if r["owner"] == OWNER][0]
        self.assertEqual((got["corrupt"], got["intentVerified"], got["keyId"], sorted(got["sections"])),
                         (False, True, kid_a, ["characters"]), "GET still hands viewers a planted section: %r" % got)
        self.assertNotIn("pub", got, "GET hands out more than the key's id")
        view = [r for r in RP.view_of(v["got"]["body"]["owners"], s[8]["records"][rk]["t"]) if r["owner"] == OWNER][0]
        self.assertEqual((view["intentVerified"], sorted(view["sections"])), (True, ["characters"]))
        page = RP.roster_html({"ok": True, "fetched": True, "now": view.get("t"), "owners": [view]})
        self.assertNotIn("FORGED", page, "the page still draws a planted row under a verified key")
        self.assertIn("signature verified (key %s)" % kid_a, page)

    def test_a_signed_publish_of_an_unchanged_row_still_carries_the_key(self):
        """M6 T3 review - every case above signs a body that differs from the stored row, so the sameIntent/upgrade
        branch was never asked. On deploy day a PC's first signed publish usually carries the very sections its
        pre-signing row (or its own unsigned row) already holds, inside the hour and not at boot. Answered
        skipped:['unchanged'] or ['within the hour'] with intentVerified:true, no key is registered and the stored row
        stays unverified while the PC records a verified publish. An unchanged publish under the key the row was
        already written with is still skipped - that is the churn guard, not a key arriving."""
        _need_node(self)
        import time
        rk, kk = "roster:" + OWNER, "rosterkey:" + OWNER
        mine = {"asOf": 2000, "counts": 1, "rows": [{"name": "Sorceress", "cls": "Sorceress", "level": 90}]}
        recent = int(time.time() * 1000) - 60000

        def record(**extra):
            sections = {"characters": mine}
            rec = {"owner": OWNER, "t": recent, "day": "2000-01-01", "n": 1, "sections": sections,
                   "hash": RP.hash_of(RP.packed(RP.for_hash(sections)))}
            rec.update(extra)
            return rec

        with tempfile.TemporaryDirectory(prefix="tvd_roster_key_") as d:
            path_a, _seed_a, pub_a = _key(os.path.join(d, "a"))
            _path_b, _seed_b, pub_b = _key(os.path.join(d, "b"))
            kid_a, kid_b = RS.key_id(pub_a), RS.key_id(pub_b)
            raw = _raw({"owner": OWNER, "boot": False, "signedAt": 1790000000000, "sections": {"characters": mine}})
            heads = RS.sign_headers(path_a, raw)[0]
            boot_raw = _raw({"owner": OWNER, "boot": True, "signedAt": 1790000000001, "sections": {"characters": mine}})
            boot_heads = RS.sign_headers(path_a, boot_raw)[0]
            moved = {"asOf": 2001, "counts": 1, "rows": [{"name": "Sorceress", "cls": "Sorceress", "level": 91}]}
            moved_raw = _raw({"owner": OWNER, "boot": False, "signedAt": 1790000000002, "sections": {"characters": moved}})
            moved_heads = RS.sign_headers(path_a, moved_raw)[0]
            empty_raw = _raw({"owner": OWNER, "boot": False, "signedAt": 1790000000003, "sections": {}})
            empty_heads = RS.sign_headers(path_a, empty_raw)[0]
            empty_boot_raw = _raw({"owner": OWNER, "boot": True, "signedAt": 1790000000004, "sections": {}})
            empty_boot_heads = RS.sign_headers(path_a, empty_boot_raw)[0]
            empty_tick_raw = _raw({"owner": OWNER, "boot": False, "sections": {}})
            vault = {"asOf": 2000, "counts": 3}
            both = {"characters": mine, "vault": vault}
            at = int(time.time() * 1000)
            today = time.strftime("%Y-%m-%d", time.gmtime(at / 1000))
            steps = [
                # 0 a row written before signing (no verdict), no key registered: this PC's first signed publish
                _step(raw, heads, fresh=True, seed={rk: record()}),
                # 1 its own unsigned row, its key put there by hand from the Mac
                _step(raw, heads, fresh=True, seed=dict(_registered(pub_a), **{rk: record(intentVerified=False)})),
                # 2 another key's verified row, this PC's key since registered
                _step(raw, heads, fresh=True, seed=dict(_registered(pub_a), **{rk: record(
                    intentVerified=True, keyId=kid_b, pub=RS.b64u(pub_b))})),
                # 3 a verified row carrying this key's 48-bit id but another key
                _step(raw, heads, fresh=True, seed=dict(_registered(pub_a), **{rk: record(
                    intentVerified=True, keyId=kid_a, pub=RS.b64u(pub_b))})),
                # 4 already written under this very key: unchanged, inside the hour - the churn guard holds
                _step(raw, heads, fresh=True, seed=dict(_registered(pub_a), **{rk: record(
                    intentVerified=True, keyId=kid_a, pub=RS.b64u(pub_a))})),
                # 5 the documented reset: rosterkey deleted from the Mac, the row still verified under this key; the
                #   boot publish of the same sections registers the key again
                _step(boot_raw, boot_heads, fresh=True, seed={rk: record(
                    intentVerified=True, keyId=kid_a, pub=RS.b64u(pub_a))}),
                # 6 a verified row with this key's pub but a stale key id: the id is rewritten
                _step(raw, heads, fresh=True, seed=dict(_registered(pub_a), **{rk: record(
                    intentVerified=True, keyId="000000000000", pub=RS.b64u(pub_a))})),
                # 7 no key anywhere, an unsigned publish of the same sections over a pre-signing row (an old one):
                #   stored NOT verified, so the row stops reading "published before signing"
                _step(raw, {}, fresh=True, seed={rk: record(t=10)}),
                # r3 (the review of r2 found four edits that stayed green):
                # 8 a signed boot of an unchanged row already under this key, its key registered: skipped 'unchanged' -
                #   a boot is not a key arriving, and an ordinary boot must not cost a write
                _step(boot_raw, boot_heads, fresh=True, seed=dict(_registered(pub_a), **{rk: record(
                    intentVerified=True, keyId=kid_a, pub=RS.b64u(pub_a))})),
                # 9 rosterkey reset, then a TICK (not a boot) inside the hour whose sections changed, the row still
                #   verified under this key: the key arrives on the tick too - registered and stored
                _step(moved_raw, moved_heads, fresh=True, seed={rk: record(
                    intentVerified=True, keyId=kid_a, pub=RS.b64u(pub_a))}),
                # 10 a BOOT of an unchanged row with this key's pub but a stale key id: the id is rewritten on a boot too
                _step(boot_raw, boot_heads, fresh=True, seed=dict(_registered(pub_a), **{rk: record(
                    intentVerified=True, keyId="000000000000", pub=RS.b64u(pub_a))})),
                # 11 an unsigned tick of the same sections over a RECENT pre-signing row: an unsigned publish is no key
                #   arriving, so the hourly guard holds and the row keeps no verdict
                _step(raw, {}, fresh=True, seed={rk: record()}),
                # r4 (the review of r3 found four more edits that stayed green):
                # 12 a signed TICK under the registered key that wrote the row, rows changed, inside the hour: the
                #   hourly cap holds for a verified row too - only a key arriving skips it
                _step(moved_raw, moved_heads, fresh=True, seed=dict(_registered(pub_a), **{rk: record(
                    intentVerified=True, keyId=kid_a, pub=RS.b64u(pub_a))})),
                # 13 a signed TICK over another key's verified row that still holds `owned`: the row keeps only what
                #   this key signed, on a tick as on a boot (REG-2516's heal runs on a tick)
                _step(moved_raw, moved_heads, fresh=True, seed=dict(_registered(pub_a), **{rk: record(
                    intentVerified=True, keyId=kid_b, pub=RS.b64u(pub_b), sections={"characters": mine, "owned": {
                        "asOf": 1000, "counts": 1, "rows": [{"name": "FORGED Zod rune", "level": 1}]}})})),
                # 14 an unsigned BOOT of the same sections over a recent pre-signing row: stored NOT verified -
                #   the boot that comes back unsigned must say so on the row
                _step(boot_raw, {}, fresh=True, seed={rk: record()}),
                # 15 rosterkey reset, then an UNCHANGED tick (not a boot), the row still verified under this key:
                #   a registration is written even when the body is unchanged
                _step(raw, heads, fresh=True, seed={rk: record(intentVerified=True, keyId=kid_a, pub=RS.b64u(pub_a))}),
                # r5 (the review of r4 swept 108 single edits; six still stayed green):
                # 16 a signed TICK under the key that wrote the row, an hour old, sending only `characters`: the
                #   `vault` this key signed before is kept - a verified tick inherits as a boot does
                _step(moved_raw, moved_heads, fresh=True, seed=dict(_registered(pub_a), **{rk: record(
                    t=10, intentVerified=True, keyId=kid_a, pub=RS.b64u(pub_a), sections=both)})),
                # 17 an unsigned TICK over a row written before signing (no verdict on it, so not the same intent),
                #   an hour old: the write is stored NOT verified and still keeps the `vault` it did not send
                _step(moved_raw, {}, fresh=True, seed={rk: record(t=10, sections=both)}, now=at),
                # 18 an unsigned tick over a row EXACTLY one hour old: the hour is over, so it is stored
                #   (due() on the PC uses the same strict <)
                _step(moved_raw, {}, fresh=True, seed={rk: record(t=at - 3600 * 1000)}, now=at),
                # 19 a signed publish that read nothing, no key registered: 'nothing read', and no key is registered
                _step(empty_raw, empty_heads, fresh=True, seed={}),
                # 20 a stored row whose `t` is not a number: its age is unknown, so the hour does not hold it
                _step(moved_raw, {}, fresh=True, seed={rk: record(t="x")}),
                # r6 (the review of r5 swept 203 single edits; seven still stayed green):
                # 21 a signed BOOT that read nothing, no key registered: 'nothing read' on a boot too - no key, no row
                _step(empty_boot_raw, empty_boot_heads, fresh=True, seed={}),
                # 22 an unsigned tick over a row one millisecond short of the hour: held 'within the hour'
                _step(moved_raw, {}, fresh=True, seed={rk: record(t=at - 3600 * 1000 + 1)}, now=at),
                # 23 an unsigned tick over an old row that already used today's 25 writes: refused on quota, a tick too
                _step(moved_raw, {}, fresh=True, seed={rk: record(t=10, day=today, n=25)}, now=at),
                # r7 (the review of r6 swept 303 single edits; the cap, the day count, sigWhy and the put whys stayed green):
                # 24 a SIGNED tick under the row's own registered key over a row at today's 25: refused on quota
                _step(moved_raw, moved_heads, fresh=True, seed=dict(_registered(pub_a), **{rk: record(
                    t=10, day=today, n=25, intentVerified=True, keyId=kid_a, pub=RS.b64u(pub_a))}), now=at),
                # 25 the key ARRIVING (rosterkey reset) on a tick over a row at today's 25: the cap holds for it too,
                #   and no key is registered
                _step(moved_raw, moved_heads, fresh=True, seed={rk: record(
                    t=10, day=today, n=25, intentVerified=True, keyId=kid_a, pub=RS.b64u(pub_a))}, now=at),
                # 26 a signed tick under the row's own key over a row with 3 writes today: stored as the 4th
                _step(moved_raw, moved_heads, fresh=True, seed=dict(_registered(pub_a), **{rk: record(
                    t=10, day=today, n=3, intentVerified=True, keyId=kid_a, pub=RS.b64u(pub_a))}), now=at),
                # 27 a TICK whose signature does not match its bytes, no key registered: why the signature failed is
                #   said on a tick as on a boot
                _step(moved_raw, heads, fresh=True, seed={rk: record(t=10)}),
                # 28 the key arriving when the rosterkey put fails: refused with the store's own words
                _step(moved_raw, moved_heads, fresh=True, seed={rk: record(
                    t=10, intentVerified=True, keyId=kid_a, pub=RS.b64u(pub_a))}, fail_put=[kk]),
                # 29 an unsigned tick when the row put fails: refused with the store's own words
                _step(moved_raw, {}, fresh=True, seed={rk: record(t=10)}, fail_put=[rk]),
                # r8 (the review of r7 swept 290 single edits):
                # 30 an UNSIGNED publish that read nothing: 'nothing read', no row
                _step(empty_tick_raw, {}, fresh=True, seed={}),
                # 31 a signed tick under the row's own key on a NEW day, after yesterday's 25 writes: stored as today's 1st
                _step(moved_raw, moved_heads, fresh=True, seed=dict(_registered(pub_a), **{rk: record(
                    t=10, day="2000-01-01", n=25, intentVerified=True, keyId=kid_a, pub=RS.b64u(pub_a))}), now=at),
            ]
            v = _node({"steps": steps, "everyRecord": True})
        s = v["steps"]
        for i, case in ((0, "a pre-signing row, no key yet"), (1, "its own unsigned row, key placed by hand"),
                        (2, "another key's row"), (3, "same 48-bit id, another key")):
            r, rec = s[i]["reply"], s[i]["records"][rk]
            self.assertEqual((r["ok"], r["stored"], r["intentVerified"], r.get("keyId")), (True, ["roster"], True, kid_a),
                             "%s - an unchanged signed publish was answered %r, so the stored row never became this "
                             "key's" % (case, r))
            self.assertEqual((rec["intentVerified"], rec["keyId"], rec["pub"]), (True, kid_a, RS.b64u(pub_a)), case)
        self.assertIs(s[0]["reply"].get("registered"), True, "the first signed publish registered no key")
        self.assertEqual(s[0]["puts"], [kk, rk])
        self.assertEqual(s[0]["records"][kk]["pub"], RS.b64u(pub_a))
        for i in (1, 2, 3):
            self.assertNotIn("registered", s[i]["reply"], "step %d registered over a key already there" % i)
            self.assertEqual(s[i]["puts"], [rk])
        self.assertEqual((s[4]["reply"].get("stored"), s[4]["reply"].get("skipped"), s[4]["puts"]), ([], ["unchanged"], []),
                         "an unchanged publish under the row's own key was written again: %r" % s[4]["reply"])
        self.assertIs(s[4]["reply"]["intentVerified"], True)
        r5 = s[5]["reply"]
        self.assertEqual((r5.get("stored"), r5.get("registered"), s[5]["puts"]), (["roster"], True, [kk, rk]),
                         "after a rosterkey reset the boot publish of an unchanged row registered no key: %r" % r5)
        self.assertEqual(s[5]["records"][kk]["pub"], RS.b64u(pub_a))
        self.assertEqual((s[6]["reply"].get("stored"), s[6]["records"][rk]["keyId"]), (["roster"], kid_a),
                         "a verified row kept a key id that is not its key's: %r" % s[6]["reply"])
        r7, rec7 = s[7]["reply"], s[7]["records"][rk]
        self.assertEqual((r7.get("stored"), r7["intentVerified"]), (["roster"], False),
                         "an unsigned publish over a pre-signing row was skipped: %r" % r7)
        self.assertIs(rec7.get("intentVerified"), False, "the row still reads 'published before signing'")
        r8 = s[8]["reply"]
        self.assertEqual((r8.get("stored"), r8.get("skipped"), s[8]["puts"]), ([], ["unchanged"], []),
                         "a signed boot of an unchanged row under its own registered key was written again: %r" % r8)
        r9 = s[9]["reply"]
        self.assertEqual((r9.get("stored"), r9.get("registered"), s[9]["puts"]), (["roster"], True, [kk, rk]),
                         "after a rosterkey reset a changed tick inside the hour registered no key: %r" % r9)
        self.assertEqual(s[9]["records"][rk]["sections"]["characters"]["asOf"], 2001)
        r10 = s[10]["reply"]
        self.assertEqual((r10.get("stored"), s[10]["records"][rk]["keyId"]), (["roster"], kid_a),
                         "a boot kept a key id that is not its key's: %r" % r10)
        r11, rec11 = s[11]["reply"], s[11]["records"][rk]
        self.assertEqual((r11.get("stored"), r11.get("skipped"), s[11]["puts"]), ([], ["within the hour"], []),
                         "an unsigned tick inside the hour over a pre-signing row was written: %r" % r11)
        self.assertNotIn("intentVerified", rec11, "an unsigned tick inside the hour gave a pre-signing row a verdict")
        r12 = s[12]["reply"]
        self.assertEqual((r12.get("stored"), r12.get("skipped"), s[12]["puts"]), ([], ["within the hour"], []),
                         "a signed tick under the row's own registered key skipped the hourly cap: %r" % r12)
        r13, rec13 = s[13]["reply"], s[13]["records"][rk]
        self.assertEqual((r13.get("stored"), rec13.get("keyId"), sorted(rec13["sections"])),
                         (["roster"], kid_a, ["characters"]),
                         "a signed tick over another key's row kept a section this key never signed: %r" % rec13)
        r14, rec14 = s[14]["reply"], s[14]["records"][rk]
        self.assertEqual((r14.get("stored"), r14.get("intentVerified"), rec14.get("intentVerified")),
                         (["roster"], False, False),
                         "an unsigned boot over a pre-signing row left it with no verdict: %r" % r14)
        r15 = s[15]["reply"]
        self.assertEqual((r15.get("stored"), r15.get("registered"), s[15]["puts"]), (["roster"], True, [kk, rk]),
                         "after a rosterkey reset an unchanged tick registered no key: %r" % r15)
        rec16 = s[16]["records"][rk]
        self.assertEqual((s[16]["reply"].get("stored"), sorted(rec16["sections"]), rec16["sections"]["characters"]["asOf"]),
                         (["roster"], ["characters", "vault"], 2001),
                         "a signed tick under the row's own key dropped a section that key signed before: %r" % rec16)
        rec17 = s[17]["records"][rk]
        self.assertEqual((s[17]["reply"].get("stored"), sorted(rec17["sections"]), rec17["intentVerified"]),
                         (["roster"], ["characters", "vault"], False),
                         "an unsigned tick dropped a section it did not send: %r" % rec17)
        self.assertEqual(s[18]["reply"].get("stored"), ["roster"],
                         "a row exactly one hour old was held 'within the hour': %r" % s[18]["reply"])
        r19 = s[19]["reply"]
        self.assertEqual((r19.get("stored"), r19.get("skipped"), s[19]["puts"]), ([], ["nothing read"], []),
                         "a signed publish that read nothing was written or registered a key: %r" % r19)
        self.assertNotIn("registered", r19)
        self.assertEqual(s[20]["reply"].get("stored"), ["roster"],
                         "a row with no numeric time was held 'within the hour': %r" % s[20]["reply"])
        # r6: a skip is an answer, not a refusal - the PC reads ok:false as unreached and sets the refusal
        for i, one in enumerate(s):
            if one["reply"].get("skipped"):
                self.assertIs(one["reply"].get("ok"), True, "step %d skipped with ok not true: %r" % (i, one["reply"]))
        # r6: the first write of a new day counts 1, not the old day's count plus one
        self.assertEqual((rec17["day"], rec17["n"]), (today, 1), "a new day's first write was counted wrong: %r" % rec17)
        r21 = s[21]["reply"]
        self.assertEqual((r21.get("ok"), r21.get("stored"), r21.get("skipped"), s[21]["puts"]),
                         (True, [], ["nothing read"], []),
                         "a signed boot that read nothing was written or registered a key: %r" % r21)
        self.assertNotIn("registered", r21)
        r22 = s[22]["reply"]
        self.assertEqual((r22.get("ok"), r22.get("stored"), r22.get("skipped"), s[22]["puts"]),
                         (True, [], ["within the hour"], []),
                         "a row one millisecond short of the hour was not held: %r" % r22)
        r23 = s[23]["reply"]
        self.assertEqual((r23.get("ok"), r23.get("why"), s[23]["puts"]),
                         (False, "roster would not take this publish: quota", []),
                         "a tick past the day's 25 writes was stored: %r" % r23)
        quota = (False, "roster would not take this publish: quota", [])
        for i, what in ((24, "a signed tick"), (25, "the key arriving")):
            r = s[i]["reply"]
            self.assertEqual((r.get("ok"), r.get("why"), s[i]["puts"]), quota,
                             "%s past the day's 25 writes was stored: %r" % (what, r))
        rec26 = s[26]["records"][rk]
        self.assertEqual((s[26]["reply"].get("stored"), rec26["day"], rec26["n"]), (["roster"], today, 4),
                         "a signed tick did not count on from today's writes: %r" % rec26)
        r27 = s[27]["reply"]
        self.assertEqual((r27.get("sig"), r27.get("intentVerified")), ("bad", False), r27)
        self.assertEqual(r27.get("sigWhy"), "the signature does not match these bytes",
                         "a tick with a failed signature does not say why: %r" % r27)
        failed = "roster would not take this publish: KV put failed"
        for i, what in ((28, "rosterkey"), (29, "roster row")):
            r = s[i]["reply"]
            self.assertEqual((r.get("ok"), r.get("why"), s[i]["puts"]), (False, failed, []),
                             "a failed %s put was not refused in the store's own words: %r" % (what, r))
        r30 = s[30]["reply"]
        self.assertEqual((r30.get("ok"), r30.get("stored"), r30.get("skipped"), s[30]["puts"]),
                         (True, [], ["nothing read"], []),
                         "an unsigned publish that read nothing was written: %r" % r30)
        rec31 = s[31]["records"][rk]
        self.assertEqual((s[31]["reply"].get("stored"), rec31["day"], rec31["n"]), (["roster"], today, 1),
                         "a signed tick on a new day was held to yesterday's count: %r" % s[31]["reply"])
        # the row is kept 400 days in the store, then it lapses
        self.assertEqual(s[26]["putOpts"].get(rk), {"expirationTtl": 60 * 60 * 24 * 400},
                         "the roster row is not stored for 400 days: %r" % s[26]["putOpts"])

    def test_an_emoji_round_trips_without_reading_corrupt(self):
        _need_node(self)
        body = _body(1, name="Ber \U0001f9ff rune")
        v = _node({"steps": [_step(_raw(body))], "get": True})
        rec = v["records"]["roster:" + OWNER]
        self.assertEqual(rec["hash"], RP.hash_of(RP.packed(RP.for_hash(rec["sections"]))),
                         "the worker and this file hash the same emoji row differently")
        view = [r for r in RP.view_of(v["got"]["body"]["owners"], rec["t"]) if r["owner"] == OWNER][0]
        self.assertIs(view["corrupt"], False, "an emoji in a row made its owner read CORRUPT (#95)")


class TheHashWalksWhatTheWorkerWalks(unittest.TestCase):

    def test_an_emoji_hashes_as_the_worker_hashes_it(self):
        """REG-2511 - measured in node: roster.js hashOf('Ber 🧿 rune') is 83534eb3. Walking code points
        gave a8b9dc5d, so view_one called every viewer's copy of that owner CORRUPT."""
        self.assertEqual(RP.hash_of("Ber \U0001f9ff rune"), "83534eb3")
        self.assertEqual(RP.hash_of("abc"), "1a47e90b", "an ASCII digest moved")
        self.assertEqual(RP.hash_of("Tal Rune ★"), "b51575f1", "a BMP digest moved")
        sections = {"characters": {"asOf": 5, "counts": 1, "rows": [{"name": "Ber \U0001f9ff rune"}]}}
        row = {"owner": "Dean", "published": True, "corrupt": False, "t": 5,
               "hash": RP.hash_of(RP.packed(RP.for_hash(sections))), "sections": sections}
        self.assertIs(RP.view_one("Dean", row, 5)["corrupt"], False)


class TheBootPublishGoesEvenWhenUnchanged(unittest.TestCase):

    def test_boot_posts_an_unchanged_body_and_a_tick_does_not(self):
        now = 1_000_000
        sections = RP.sections_from({"characters": {"read": True, "asOf": 1000, "counts": 1,
                                                     "rows": [{"name": "Sorceress", "level": 1}]}})
        state = {"hash": RP.hash_of(RP.packed(RP.for_hash(sections))), "at": now}
        body, why = RP.due(state, OWNER, sections, now + 1000, True)
        self.assertEqual(why, "post", "REG-2512: an unchanged boot did not post, so a forged row is never healed")
        self.assertEqual((body["boot"], body["signedAt"]), (True, now + 1000))
        quiet, why = RP.due(state, OWNER, sections, now + 1000, False)
        self.assertIsNone(quiet)
        self.assertEqual(why, "unchanged")
        refused = dict(state, refuseAt=now, why="roster would not take this publish: quota")
        held, why = RP.due(refused, OWNER, sections, now + 1000, True)
        self.assertIsNone(held, "a refusal was retried inside the hour")
        self.assertIn("quota", why)


class IntentVerifiedTravelsWithEveryView(unittest.TestCase):

    def _row(self, owner, extra):
        sections = {"characters": {"asOf": 7, "counts": 1, "rows": [{"name": "Shako"}]}}
        row = {"owner": owner, "published": True, "corrupt": False, "t": 7, "sections": sections,
               "hash": RP.hash_of(RP.packed(RP.for_hash(sections)))}
        row.update(extra)
        return row

    def test_view_cache_and_page_carry_each_verdict(self):
        rows = [self._row("Konyo · Mac", {"intentVerified": True, "keyId": "0123456789ab"}),
                self._row("Dean", {"intentVerified": False}),
                self._row("Wife PC", {}),
                self._row("Konyo · ALT", {"intentVerified": "true"})]
        views = RP.view_of(rows, 7)
        by = {v["owner"]: v for v in views}
        self.assertEqual((by["Konyo · Mac"]["intentVerified"], by["Konyo · Mac"]["keyId"]), (True, "0123456789ab"))
        self.assertIs(by["Dean"]["intentVerified"], False)
        self.assertIsNone(by["Wife PC"]["intentVerified"], "a row with no verdict was given one")
        self.assertIsNone(by["Konyo · ALT"]["intentVerified"], "a string was read as a verdict")
        with tempfile.TemporaryDirectory(prefix="tvd_roster_cache_") as d:
            folder = os.path.join(d, "roster_cache")
            bare = dict(by["Konyo · Mac"])
            del bare["intentVerified"]
            RP.write_cache(folder, [bare, by["Dean"], by["Wife PC"]])
            with io.open(os.path.join(folder, RP.cache_file_name("Konyo · Mac")), encoding="utf-8") as fh:
                written = json.load(fh)
            self.assertIn("intentVerified", written, "the cache file left the verdict out, so a reader must guess")
            self.assertIsNone(written["intentVerified"])
            RP.write_cache(folder, views)
            back = {r["owner"]: r for r in RP.read_cache(folder, 7)["owners"]}
        self.assertIs(back["Konyo · Mac"]["intentVerified"], True)
        self.assertEqual(back["Konyo · Mac"]["keyId"], "0123456789ab")
        self.assertIs(back["Dean"]["intentVerified"], False)
        self.assertIsNone(back["Wife PC"]["intentVerified"])
        page = RP.roster_html({"ok": True, "fetched": True, "now": 7, "owners": list(back.values())})
        self.assertIn("signature verified (key 0123456789ab)", page)
        self.assertIn("NOT signature-verified", page)
        self.assertIn("signature UNKNOWN: published before signing", page)


class ThisPCSaysItsOwnLastPublish(unittest.TestCase):

    def test_each_outcome_is_named_with_its_why(self):
        sections = {"characters": {"asOf": 1, "counts": 1}}
        signed = {"signed": True, "keyId": "aaaaaaaaaaaa", "signer": "pure-python", "agree": None}
        cases = [
            ({"ok": True, "stored": ["roster"], "intentVerified": True, "keyId": "aaaaaaaaaaaa", "signing": signed},
             "signed", None),
            ({"ok": False, "why": "roster would not take this publish: Dean has a registered key and this "
                                  "publish was not signed", "hint": "nothing was stored",
              "signing": {"signed": False, "why": "the key file is unreadable (ValueError); it was left as it is"}},
             "refused", "registered key"),
            ({"ok": True, "stored": ["roster"], "intentVerified": False,
              "signing": {"signed": False, "why": "the key could not be written (PermissionError)"}},
             "unsigned", "PermissionError"),
            ({"ok": True, "stored": ["roster"], "intentVerified": False, "sig": "bad",
              "sigWhy": "the signature does not match these bytes", "signing": signed},
             "unverified", "does not match"),
            ({"ok": False, "why": "URLError", "code": None, "signing": signed}, "unreached", "URLError"),
        ]
        for reply, want, words in cases:
            state = RP.apply_reply({}, sections, reply, 50)
            out = RP.publish_outcome(state, 50 + 120000)
            self.assertEqual(out["state"], want, "%r read as %r" % (reply, out))
            if words:
                self.assertIn(words, out["why"])
            page = html.unescape(RP.roster_html({"ok": True, "fetched": False, "owners": [], "me": out}))
            self.assertIn("this PC's last publish", page)
            self.assertIn("this PC has not fetched a roster yet", page)
        self.assertEqual(RP.publish_outcome({"why": "unchanged"}, 1)["state"], "unknown",
                         "a receipt written before signing read as a signed publish")
        self.assertEqual(RP.publish_outcome(None, 1)["state"], "unknown")
        refused = RP.publish_outcome(RP.apply_reply({}, sections, cases[1][0], 50), 50)
        self.assertIn("REFUSED", html.unescape(RP.roster_html({"ok": True, "fetched": False, "me": refused})))
        unsigned = RP.publish_outcome(RP.apply_reply({}, sections, cases[2][0], 50), 50)
        self.assertIn("went UNSIGNED", html.unescape(RP.roster_html({"ok": True, "fetched": False, "me": unsigned})))

    def test_the_panel_route_hands_over_this_pcs_receipt(self):
        src = _read(APP)
        self.assertEqual(src.count('if path == "/api/roster-cache":'), 1)
        at = src.index('if path == "/api/roster-cache":')
        door = src[at:src.index("return\n", at)]
        me = 'data["me"] = _rp.publish_outcome(_roster_state_load(), int(time.time() * 1000))'
        self.assertIn(me, door, "the roster panel no longer carries this PC's own last publish")
        self.assertLess(door.index(me), door.index("roster_html(data)"),
                        "this PC's outcome is added after the page was drawn, so the page cannot show it")


# The panel's own code, run as it ships: cut from control_ui.html (never re-typed) and run in node against a stand-in
# page whose fetch answers with what the console's route served. No browser: the words and their order are the claim.
_PANEL = r"""
var PAYLOAD = __PAYLOAD__;
var ENTER = __ENTER__;
function El(id) { this.id = id; this.attrs = {}; this.innerHTML = ''; this.textContent = ''; this.style = {};
  this.parentNode = null; this.scrollTop = 7; this.listeners = {};
  var set = {}; this.classList = { add: function () { for (var i = 0; i < arguments.length; i++) set[arguments[i]] = 1; },
    remove: function () { for (var i = 0; i < arguments.length; i++) delete set[arguments[i]]; },
    contains: function (c) { return !!set[c]; } }; }
El.prototype.hasAttribute = function (k) { return Object.prototype.hasOwnProperty.call(this.attrs, k); };
El.prototype.getAttribute = function (k) { return this.hasAttribute(k) ? this.attrs[k] : null; };
El.prototype.setAttribute = function (k, v) { this.attrs[k] = String(v); };
El.prototype.removeAttribute = function (k) { delete this.attrs[k]; };
El.prototype.addEventListener = function (t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); };
El.prototype.appendChild = function (n) { n.parentNode = this; };
El.prototype.getBoundingClientRect = function () { return { top: 40, bottom: 60, left: 0, width: 300 }; };
var els = {};
['roster-open', 'roster-box', 'roster-body', 'shadow-bar', 'shadow-who', 'tvd-eng'].forEach(function (id) { els[id] = new El(id); });
els['roster-box'].setAttribute('hidden', '');
els['shadow-bar'].setAttribute('hidden', '');
var posted = [];
els['tvd-eng'].contentWindow = { postMessage: function (m) { posted.push(m); } };
var document = { body: new El('body'), readyState: 'complete',
  getElementById: function (id) { return els[id] || null; }, querySelector: function () { return null; } };
var window = { innerHeight: 900, location: { origin: 'http://127.0.0.1:17772', search: '' },
  addEventListener: function () {}, removeEventListener: function () {} };
var fetched = [];
function fetch(url) { fetched.push(url);
  return Promise.resolve({ json: function () { return Promise.resolve(JSON.parse(JSON.stringify(PAYLOAD))); } }); }
function setTimeout() { return 0; }
__CUT__
(async function () {
  var settle = function () { return new Promise(function (r) { setImmediate(r); }); };
  window._rosterOpen();
  for (var i = 0; i < 5; i++) await settle();
  var out = { panel: els['roster-body'].innerHTML, bars: {}, fetched: fetched };
  for (var j = 0; j < ENTER.length; j++) {
    window._shadowEnter(ENTER[j]);
    for (var k = 0; k < 5; k++) await settle();
    out.bars[ENTER[j]] = els['shadow-who'].textContent;
  }
  console.log(JSON.stringify(out));
})().catch(function (e) { console.error(String(e && e.stack || e)); process.exit(3); });
"""


def _panel_code():
    """The roster panel's code as it ships: _rosterSig, _rosterOpen, _shadowGen and _shadowEnter, in file order."""
    ui = _read(UI)
    start, end = "  var _rosterSig = function (row) {", "  window._shadowLeave = function () {"
    for anchor in (start, end):
        if ui.count(anchor) != 1:
            raise AssertionError("%r is in control_ui.html %d times - re-point this law" % (anchor, ui.count(anchor)))
    return ui[ui.index(start):ui.index(end)]


def _panel(payload, enter=()):
    """-> what the panel drew (`panel`, innerHTML) and the shadow bar's sentence per owner entered (`bars`)."""
    js = (_PANEL.replace("__PAYLOAD__", json.dumps(payload)).replace("__ENTER__", json.dumps(list(enter)))
          .replace("__CUT__", _panel_code()))
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=60)
    if r.returncode != 0:
        raise AssertionError("node could not run the panel's shipped code - UNKNOWN, not passing: %s" % r.stderr[-800:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _served(cache_dir, receipt, now_ms):
    """What /api/roster-cache serves: the route's own lines, cut from control_app.py and run with its two reads stood in.
    -> the dict it handed to _json"""
    src = _read(APP)
    head = '        if path == "/api/roster-cache":\n'
    if src.count(head) != 1:
        raise AssertionError("the roster-cache route is in control_app.py %d times - re-point this law" % src.count(head))
    at = src.index(head) + len(head)
    door = textwrap.dedent(src[at:src.index("            return\n", at)])
    sent = []
    ns = {"_roster_cache_payload": lambda: RP.read_cache(cache_dir, now_ms),
          "_roster_state_load": lambda: receipt,
          # REG-2867 - the route also reads the profile's and the sessions' receipts; none here (they read UNKNOWN)
          "_profile_json_load": lambda path: None, "_profile_state_path": lambda: "profile",
          "_frames_state_path": lambda: "frames",
          "time": types.SimpleNamespace(time=lambda: now_ms / 1000.0),
          "self": types.SimpleNamespace(_json=lambda code, data: sent.append((code, data)))}
    exec(compile(door, APP, "exec"), ns)
    if len(sent) != 1 or sent[0][0] != 200:
        raise AssertionError("the route served %r" % (sent,))
    return sent[0][1]


class TheSignatureReachesHisScreen(unittest.TestCase):
    """REG-2517 (#95, the review of REG-2513) - every owner's verdict and this PC's own last publish rode /api/roster-cache
    and the panel dropped them: _rosterOpen drew '<owner> · published' from data.owners alone and the shadow bar said
    '<owner> · published · read only', so a forged, NOT-verified row looked exactly like his own. Here the route's own
    lines serve real cache files and a real receipt, and the panel's own code draws them."""

    NOW = 1790000000000

    def _world(self, folder, me_reply):
        sections = {"characters": {"asOf": self.NOW - 60000, "counts": 1, "rows": [{"name": "Shako"}]}}
        digest = RP.hash_of(RP.packed(RP.for_hash(sections)))

        def row(owner, **extra):
            out = {"owner": owner, "published": True, "corrupt": False, "t": self.NOW - 60000, "hash": digest,
                   "sections": sections}
            out.update(extra)
            return out
        rows = [row("Konyo · Mac", intentVerified=True, keyId="0123456789ab"),
                row("Dean", intentVerified=False),
                row("Wife PC"),
                {"owner": "Konyo · ALT", "published": True, "corrupt": True, "t": self.NOW - 60000},
                {"owner": "Konyo · GrokBot", "published": False}]
        RP.write_cache(os.path.join(folder, "roster_cache"), RP.view_of(rows, self.NOW))
        return RP.apply_reply({}, sections, me_reply, self.NOW - 120000)

    def test_each_row_and_this_pcs_publish_are_drawn_with_their_words(self):
        refused = {"ok": False, "why": "roster would not take this publish: Konyo · Mac has a registered key and this "
                                       "publish was not signed", "hint": "nothing was stored",
                   "signing": {"signed": False, "why": "the key file is unreadable (ValueError); it was left as it is"}}
        with tempfile.TemporaryDirectory(prefix="tvd_roster_panel_") as d:
            receipt = self._world(d, refused)
            data = _served(os.path.join(d, "roster_cache"), receipt, self.NOW)
        self.assertEqual(data["me"]["state"], "refused")
        # what the route hands the panel - measured here without node, so a PC with no node still asks it
        self.assertEqual(data.get("meLine", {}).get("cls"), "roster-me roster-refused",
                         "the route no longer hands the panel this PC's own last publish as a line")
        self.assertEqual({r["owner"]: (r.get("sig") or {}).get("words") for r in data["owners"]},
                         {"Konyo · Mac": "signature verified (key 0123456789ab)",
                          "Dean": "NOT signature-verified: published without a signature its owner's key made",
                          "Wife PC": "signature UNKNOWN: published before signing",
                          "Konyo · ALT": RP.CORRUPT_SIGNATURE, "Konyo · GrokBot": None},
                         "the route no longer hands the panel each row's signature in words")
        _need_node(self)
        drawn = _panel(data, ["Konyo · Mac", "Dean", "Wife PC", "Konyo · ALT", "Konyo · GrokBot"])
        self.assertEqual(drawn["fetched"], ["/api/roster-cache"] + ["/api/roster-cache", "/api/fleet"] * 5)
        panel = html.unescape(drawn["panel"])
        self.assertTrue(panel.startswith('<div class="roster-me roster-refused">this PC\'s last publish (2 min ago) '
                                         'was REFUSED: roster would not take this publish: Konyo · Mac has a registered key'),
                        "this PC's refused publish does not lead the panel: %s" % panel[:300])
        buttons = panel.split('<button type="button" class="roster-person" data-owner="')[1:]
        self.assertEqual([b.split('"', 1)[0] for b in buttons], list(RP.OWNERS), panel)
        by = {b.split('"', 1)[0]: b for b in buttons}
        want = {"Konyo · Mac": ("roster-verified", "signature verified (key 0123456789ab)"),
                "Dean": ("roster-unverified", "NOT signature-verified: published without a signature its owner's key made"),
                "Wife PC": ("roster-unknown", "signature UNKNOWN: published before signing"),
                "Konyo · ALT": ("roster-unknown", RP.CORRUPT_SIGNATURE)}
        for owner, (cls, words) in want.items():
            self.assertIn('<span class="roster-sig %s">%s</span></button>' % (cls, words), by[owner],
                          "%s's button does not say whose signature its row carries: %s" % (owner, by[owner]))
        self.assertIn("Konyo · GrokBot · not published</button>", by["Konyo · GrokBot"])
        self.assertNotIn("roster-sig", by["Konyo · GrokBot"], "a row nobody published was given a signature")
        bars = drawn["bars"]
        # REG-3037 - the row's own age, named as the row's store (a corrupt row carries no clock: UNKNOWN)
        ages = {o: "roster row stored 1 min ago" for o in ("Konyo · Mac", "Dean", "Wife PC")}
        ages["Konyo · ALT"] = "roster row stored, age UNKNOWN"
        self.assertEqual({r["owner"]: r.get("ageWords") for r in data["owners"] if r.get("published")}, ages)
        for owner, (_cls, words) in want.items():
            self.assertEqual(bars[owner], "%s · %s · %s · read only" % (owner, ages[owner], words),
                             "the shadow bar inside %s's console does not say its signature" % owner)
            self.assertIn("%s · %s<span" % (owner, ages[owner]), by[owner], "%s's button does not date its row" % owner)
        self.assertEqual(bars["Konyo · GrokBot"], "Konyo · GrokBot has not published a console · read only")

    def test_a_console_that_sent_no_words_reads_unknown_never_silent(self):
        """The panel and the route ship together, but a payload without the words (an older console answering) must
        not draw a NOT-verified row the way it draws a verified one: UNKNOWN, and this PC's publish UNKNOWN too."""
        _need_node(self)
        old = {"ok": True, "fetched": True, "owners": [
            {"owner": "Konyo · Mac", "published": True, "corrupt": False, "intentVerified": True, "age": "current"},
            {"owner": "Dean", "published": True, "corrupt": False, "intentVerified": False, "age": "stale"}]}
        drawn = _panel(old, ["Dean"])
        panel = html.unescape(drawn["panel"])
        self.assertTrue(panel.startswith('<div class="roster-me roster-unknown">this PC\'s last publish: UNKNOWN'), panel)
        self.assertEqual(panel.count('<span class="roster-sig roster-unknown">signature UNKNOWN: the console did not say'
                                     '</span>'), 2, panel)
        self.assertEqual(drawn["bars"]["Dean"],
                         "Dean · roster row stored, age UNKNOWN (the console did not say) · signature UNKNOWN: the "
                         "console did not say · read only")

    def test_no_owners_still_leads_with_this_pcs_publish(self):
        _need_node(self)
        with tempfile.TemporaryDirectory(prefix="tvd_roster_panel_") as d:
            unsigned = {"ok": True, "stored": ["roster"], "intentVerified": False,
                        "signing": {"signed": False, "why": "the key could not be written (PermissionError)"}}
            receipt = RP.apply_reply({}, {"characters": {"asOf": 1, "counts": 1}}, unsigned, self.NOW)
            data = _served(os.path.join(d, "never_fetched"), receipt, self.NOW)
        self.assertIs(data["fetched"], False)
        panel = html.unescape(_panel(data)["panel"])
        self.assertTrue(panel.startswith('<div class="roster-me roster-unverified">this PC\'s last publish '
                                         '(under 1 min ago) went UNSIGNED: the key could not be written (PermissionError)'),
                        panel)
        self.assertIn('<div class="roster-none">the roster answer had no owners</div>', panel)

    def test_every_word_the_panel_draws_has_a_colour(self):
        """The four verdict classes roster_publish hands the panel are styled, so NOT-verified does not draw in the
        verified colour."""
        ui = _read(UI)
        for cls in ("roster-sig", "roster-me", "roster-verified", "roster-unverified", "roster-refused", "roster-unknown"):
            self.assertEqual(ui.count("  .%s {" % cls), 1, "control_ui.html has no single rule for .%s" % cls)


class TheConsoleSignsTheBytesItPosts(unittest.TestCase):
    """_roster_post, cut from control_app.py as it ships and run against a stand-in urllib: what it
    sends is what it signed, and a key it cannot use posts unsigned and says why."""

    @staticmethod
    def _post_fn(sent, answer=b'{"ok": true, "stored": ["roster"]}', fail=None):
        src = _read(APP)
        if src.count("\ndef _roster_post(") != 1:
            raise AssertionError("_roster_post is defined %d times - re-point this law" % src.count("\ndef _roster_post("))
        start = src.index("\ndef _roster_post(") + 1
        code = src[start:src.index("\ndef ", start)]

        class Req(object):
            def __init__(self, url, data=None, headers=None, method=None):
                sent.append({"url": url, "data": data, "headers": dict(headers or {}), "method": method})

        class Resp(object):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return answer

        def urlopen(req, timeout=None):
            if fail:
                raise fail
            return Resp()

        request = types.SimpleNamespace(Request=Req, urlopen=urlopen)
        ns = {"json": json, "urllib": types.SimpleNamespace(request=request)}
        exec(compile(code, APP, "exec"), ns)
        return ns["_roster_post"]

    def test_the_exact_bytes_posted_are_the_bytes_signed(self):
        sent = []
        body = _body(4, name="Ber \U0001f9ff rune")
        with tempfile.TemporaryDirectory(prefix="tvd_roster_key_") as d:
            path = RS.key_path_in(d)
            reply = self._post_fn(sent)("https://bull-4-u.com/api/roster", body, path)
            _p, seed, pub = _key(d)
        self.assertEqual(len(sent), 1)
        data, heads = sent[0]["data"], sent[0]["headers"]
        self.assertEqual(data, _raw(body), "the console posted bytes other than its own serialisation")
        self.assertIn("X-Roster-Sig", heads, "the console posted unsigned with a usable key (#95)")
        self.assertEqual(RS.unb64u(heads["X-Roster-Key"]), pub)
        self.assertTrue(RS.pure_verify(pub, data, RS.unb64u(heads["X-Roster-Sig"])),
                        "the signature does not cover the bytes that were posted")
        self.assertEqual((reply["signing"]["signed"], reply["signing"]["keyId"]), (True, RS.key_id(pub)))
        state = RP.apply_reply({}, body["sections"], reply, 1)
        out = RP.publish_outcome(state, 1)
        seen = json.dumps([heads, reply, state, out], ensure_ascii=False) + data.decode("utf-8")
        for form in _secret_forms(seed):
            self.assertNotIn(form, seen, "the private key left its file")
        if NODE:
            v = _node({"steps": [_step(data, heads)]})
            self.assertIs(v["steps"][0]["reply"]["intentVerified"], True,
                          "roster.js did not verify what the console sent: %r" % v["steps"][0]["reply"])

    def test_a_key_it_cannot_use_posts_unsigned_and_says_why(self):
        with tempfile.TemporaryDirectory(prefix="tvd_roster_key_") as d:
            path = RS.key_path_in(d)
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write("{not a key")
            sent = []
            reply = self._post_fn(sent)("https://bull-4-u.com/api/roster", _body(1), path)
            with io.open(path, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "{not a key", "an unreadable key file was replaced")
        self.assertNotIn("X-Roster-Sig", sent[0]["headers"])
        self.assertIs(reply["signing"]["signed"], False)
        self.assertIn("unreadable", reply["signing"]["why"])
        sent = []
        none = self._post_fn(sent)("https://bull-4-u.com/api/roster", _body(1))
        self.assertEqual((none["signing"]["signed"], none["signing"]["why"]), (False, "no key path was given"))
        failed = self._post_fn([], fail=OSError("down"))("https://bull-4-u.com/api/roster", _body(1), None)
        self.assertIs(failed["ok"], False)
        self.assertIn("signing", failed, "a failed post lost what the signing did")

    def test_the_publish_loop_hands_over_this_pcs_key_path(self):
        """The path is spelled out in control_app so test_every_decision_file_is_ignored asks git's own
        matcher about it; this pins that spelling to roster_sign.KEY_FILE, which the doctor reads."""
        src = _read(APP)
        once = src.split("def _roster_publish_once(", 1)[1].split("def _roster_publish_loop", 1)[0]
        call = 'reply = _roster_post("https://bull-4-u.com/api/roster", body, os.path.join(_log_root(), "%s"))'
        self.assertEqual(once.count(call % RS.KEY_FILE), 1,
                         "the publish loop no longer hands this PC's key path (roster_sign.KEY_FILE) to the post")
        self.assertEqual(RS.key_path_in("root"), os.path.join("root", RS.KEY_FILE))

    def test_the_key_file_is_never_committed(self):
        """This repo is PUBLIC: a committed seed lets anyone sign as that PC for good."""
        lines = [ln.strip() for ln in _read(os.path.join(ROOT, ".gitignore")).splitlines()]
        for name in ("tv/" + RS.KEY_FILE, "tv/" + RS.KEY_FILE + ".tmp"):
            self.assertIn(name, lines, "%s is not ignored - one `git add -A` publishes a private key" % name)
            self.assertNotIn("!" + name, lines)


class TheKeyStaysOnThisPC(unittest.TestCase):

    def test_a_key_is_made_once_kept_private_and_never_replaced(self):
        with tempfile.TemporaryDirectory(prefix="tvd_roster_key_") as d:
            path = RS.key_path_in(d)
            key, why, made = RS.load_or_create(path, 123)
            self.assertIsNotNone(key, why)
            self.assertTrue(made)
            again, _why, made2 = RS.load_or_create(path)
            self.assertFalse(made2, "a second load made a second key")
            self.assertEqual(again.pub, key.pub)
            with io.open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(sorted(data), ["created", "pub", "seed", "v"])
            self.assertEqual(data["created"], 123)
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600, "the key file is readable by others")
            seed = RS.unb64u(data["seed"])
            shown = repr(key) + str(key) + json.dumps(key.view()) + json.dumps(RS.public_view(path)[0])
            for form in _secret_forms(seed):
                self.assertNotIn(form, shown, "the key's own repr or view carries its seed")
            self.assertFalse(os.path.exists(path + ".tmp"), "the atomic-write partner was left behind")
            with io.open(path, "w", encoding="utf-8") as fh:
                json.dump(dict(data, pub=RS.b64u(b"\x01" * 32)), fh)
            broken, why, made3 = RS.load_or_create(path)
            self.assertIsNone(broken)
            self.assertFalse(made3)
            self.assertIn("does not match its seed", why)
            with io.open(path, encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["pub"], RS.b64u(b"\x01" * 32),
                                 "a key file that does not add up was replaced - a registered owner would "
                                 "then be refused with the evidence gone")


class TheDoctorAsksIt(unittest.TestCase):

    def test_the_verdict_names_what_is_wrong(self):
        ok_me = {"state": "signed", "intentVerified": True, "keyId": "aaaaaaaaaaaa", "agree": True}
        fetched = {"ok": True, "fetched": True, "owners": [
            {"owner": OWNER, "published": True, "corrupt": False, "intentVerified": True, "keyId": "aaaaaaaaaaaa"},
            {"owner": "Dean", "published": True, "corrupt": False, "intentVerified": True, "keyId": "bbbbbbbbbbbb"},
            {"owner": "Wife PC", "published": False}]}
        st, why = RP.signing_verdict(fetched, ok_me, OWNER, "aaaaaaaaaaaa")
        self.assertEqual(st, "ok", why)
        unsigned = json.loads(json.dumps(fetched))
        unsigned["owners"][1]["intentVerified"] = False
        st, why = RP.signing_verdict(unsigned, ok_me, OWNER, "aaaaaaaaaaaa")
        self.assertEqual(st, "missing")
        self.assertIn("Dean", why)
        before = json.loads(json.dumps(fetched))
        del before["owners"][1]["intentVerified"]
        self.assertEqual(RP.signing_verdict(before, ok_me, OWNER, "aaaaaaaaaaaa")[0], "unknown",
                         "a row published before signing read as verified")
        st, why = RP.signing_verdict(fetched, dict(ok_me, state="refused", why="no"), OWNER, "aaaaaaaaaaaa")
        self.assertEqual(st, "missing")
        self.assertIn("REFUSED", why)
        st, why = RP.signing_verdict(fetched, ok_me, OWNER, "cccccccccccc")
        self.assertEqual(st, "missing")
        self.assertIn("resets that owner's key", why)
        self.assertEqual(RP.signing_verdict({"ok": True, "fetched": False}, ok_me, OWNER, None)[0], "unknown")
        self.assertEqual(RP.signing_verdict(fetched, dict(ok_me, agree=False), OWNER, "aaaaaaaaaaaa")[0], "missing")
        self.assertEqual(RP.signing_verdict(fetched, {"state": "unknown"}, None, None)[0], "ok",
                         "a PC with no roster label publishes nothing and is asked only about the others")

    def test_the_doctor_row_reads_this_pcs_own_stores(self):
        with tempfile.TemporaryDirectory(prefix="tvd_roster_doctor_") as d:
            key_path, _seed, pub = _key(d)
            kid = RS.key_id(pub)
            receipt = RP.apply_reply({}, {}, {"ok": True, "stored": ["roster"], "intentVerified": True, "keyId": kid,
                                              "signing": {"signed": True, "keyId": kid, "agree": True}}, 5)
            views = RP.view_of([{"owner": OWNER, "published": True, "corrupt": False, "t": 5,
                                 "hash": RP.hash_of(RP.packed(RP.for_hash({}))), "intentVerified": True,
                                 "keyId": kid}], 5)
            RP.write_cache(os.path.join(d, "roster_cache"), views)
            ca = types.SimpleNamespace(
                _roster_state_load=lambda: receipt,
                _roster_cache_payload=lambda: RP.read_cache(os.path.join(d, "roster_cache"), 5),
                _roster_claimed_name=lambda: "Konyo", _roster_platform=lambda: "mac", _log_root=lambda: d)
            self.assertEqual(RP.doctor_row(ca, 5)[0], "ok")
            refused = RP.apply_reply(receipt, {}, {"ok": False, "why": "roster would not take this publish: x",
                                                   "hint": "nothing was stored", "signing": {"signed": True}}, 6)
            ca._roster_state_load = lambda: refused
            st, why = RP.doctor_row(ca, 6)
            self.assertEqual(st, "missing")
            self.assertIn("REFUSED", why)
            self.assertFalse(os.path.exists(key_path + ".tmp"))
        doctor = _read(DOCTOR)
        self.assertEqual(doctor.count('    ("every roster publish is signed", _check_every_roster_publish_is_signed),\n'), 1,
                         "the doctor no longer asks whether every roster publish is signed")
        fn = doctor[doctor.index("def _check_every_roster_publish_is_signed("):]
        fn = fn[:fn.index("\ndef ")]
        self.assertIn("_rp.doctor_row(_serving_console(_ca)", fn)


class TheBootSweepsD2jspScratch(unittest.TestCase):
    """#112 - a console killed mid d2jsp op leaves a scratch Chrome holding his session. main() calls the
    existing d2jsp_chrome._sweep_stale_scratch() once, synchronously, inside a guard that never raises."""

    def test_the_sweep_is_called_once_and_guarded(self):
        src = _read(APP)
        self.assertEqual(src.count("_sweep_stale_scratch("), 1, "the boot sweep is called more or less than once")
        self.assertEqual(src.count("\ndef main("), 1)
        start = src.index("\ndef main(") + 1
        main = ast.parse(src[start:src.index('\nif __name__ == "__main__":', start)]).body[0]
        hits = []
        for st in main.body:
            for node in ast.walk(st):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "_sweep_stale_scratch"):
                    hits.append(st)
        self.assertEqual(len(hits), 1, "main() does not call the sweep exactly once at its own level")
        guard = hits[0]
        self.assertIsInstance(guard, ast.Try, "the boot sweep is not inside a try: a failure would stop the boot")
        self.assertTrue(any(isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "_sweep_stale_scratch"
                            for b in guard.body for n in ast.walk(b)))
        catches = [h for h in guard.handlers if isinstance(h.type, ast.Name) and h.type.id == "Exception"]
        self.assertTrue(catches, "the guard does not catch Exception")
        for h in catches:
            self.assertFalse(any(isinstance(n, ast.Raise) for n in ast.walk(h)), "the guard re-raises")
            self.assertTrue(any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "print"
                                for n in ast.walk(h)), "a failed sweep is not recorded")
        index_sweep = src.index('_reel_sweep_indexes(why="console boot")')
        self.assertLess(index_sweep, src.index("_sweep_stale_scratch("))
        self.assertLess(src.index("_sweep_stale_scratch("), src.index("target=_roster_publish_loop"),
                        "the sweep runs after the lanes have started")


RED_PROOF = [
    {"why": "REG-2510 (#95): roster.js takes a signature that does not match the bytes as valid, so a flipped bit "
            "is stored for a registered owner and registers a key for an unregistered one",
     "file": "functions/api/roster.js",
     "find": "  if (ok !== true) return { state: \"bad\", keyId: keyId, why: \"the signature does not match these bytes\" };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2510 (#95): a refused publish still writes the row before it answers ok:false",
     "file": "functions/api/roster.js",
     "find": "    return refuseSignature(intent, sig, asked);\n",
     "replace": "  if (intent.refused) { await kv.put(key, JSON.stringify({ owner: owner, t: Date.now(), day: \"2000-01-01\", "
                "n: 1, hash: \"forged\", sections: shaped }), { expirationTtl: TTL_S }); return refuseSignature(intent, sig); }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2510 (#95): the registered-key check is skipped, so a publish signed by another key overwrites the owner's row",
     "file": "functions/api/roster.js",
     "find": "    if (sig.pub !== b64uOfBytes(regPub)) {\n",
     "replace": "    if (false) {\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2510 (#95): GET calls a row published before signing unverified instead of passing no verdict (UNKNOWN)",
     "file": "functions/api/roster.js",
     "find": "    if (typeof prev.intentVerified === \"boolean\") row.intentVerified = prev.intentVerified;\n",
     "replace": "    row.intentVerified = prev.intentVerified === true;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2516 (#95): a signed publish merges every section of the stored row again, so a section planted "
            "unsigned before the key was registered is stamped 'signature verified' under the owner's key for good",
     "file": "functions/api/roster.js",
     "find": "  const sections = Object.assign(inherit ? priorSections(prev) : {}, shaped);\n",
     "replace": "  const sections = Object.assign(priorSections(prev), shaped);\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2516 (#95): 'the same key' is asked of the 48-bit key id instead of the key, so another key's row "
            "that shares the id is carried into a verified row",
     "file": "functions/api/roster.js",
     "find": "prevPub === pub && ",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review: the origin/main unchanged check returns, so a PC's first signed publish of the sections its "
            "pre-signing row already holds is skipped 'unchanged' - no key registered, the row stays unverified",
     "file": "functions/api/roster.js",
     "find": "  if (prev && prev.hash === hash && sameIntent && !upgrade) {\n",
     "replace": "  if (prev && prev.hash === hash) {\n",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review: the hourly guard skips a key arriving, so a signed publish inside the hour is answered "
            "'within the hour' and the row never becomes the key's",
     "file": "functions/api/roster.js",
     "find": "  if (prev && age < HOUR_MS && !boot && !upgrade) {\n",
     "replace": "  if (prev && age < HOUR_MS && !boot) {\n",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review: only a first registration counts as a key arriving, so a key placed by hand (or a row "
            "written under another key) is never stamped onto an unchanged row",
     "file": "functions/api/roster.js",
     "find": "  const upgrade = verified && (!sameIntent || intent.register === true);\n",
     "replace": "  const upgrade = verified && intent.register === true;\n",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review: every signed publish counts as a key arriving, so an unchanged row under its own key is "
            "rewritten on every tick (the churn guard is gone)",
     "file": "functions/api/roster.js",
     "find": "  const upgrade = verified && (!sameIntent || intent.register === true);\n",
     "replace": "  const upgrade = verified;\n",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r2: a first registration no longer counts as a key arriving, so after a rosterkey reset the "
            "boot publish of an unchanged verified row registers nothing",
     "file": "functions/api/roster.js",
     "find": "(!sameIntent || intent.register === true)",
     "replace": "(!sameIntent)",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r2: the unchanged check ignores a key arriving, so the reset's boot publish is skipped 'unchanged'",
     "file": "functions/api/roster.js",
     "find": "prev.hash === hash && sameIntent && !upgrade) {",
     "replace": "prev.hash === hash && sameIntent) {",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r2: 'the same intent' stops asking the key id, so a stale id stays on a verified row",
     "file": "functions/api/roster.js",
     "find": " && (prev.keyId || null) === keyId;",
     "replace": ";",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r2: 'the same intent' stops asking the verdict, so an unsigned publish over a pre-signing row is "
            "skipped and the row keeps no verdict",
     "file": "functions/api/roster.js",
     "find": "!!prev && prev.intentVerified === verified && prevPub",
     "replace": "!!prev && prevPub",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r3: every boot counts as a key arriving, so an ordinary boot of an unchanged row costs a write",
     "file": "functions/api/roster.js",
     "find": "(!sameIntent || intent.register === true)",
     "replace": "(!sameIntent || intent.register === true || boot)",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r3: a key registers only on a boot, so after a rosterkey reset a changed tick inside the hour "
            "is skipped and registers nothing",
     "file": "functions/api/roster.js",
     "find": "(!sameIntent || intent.register === true)",
     "replace": "(!sameIntent || (intent.register === true && boot))",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r3: a boot counts as the same key id, so a boot of an unchanged row keeps a stale key id",
     "file": "functions/api/roster.js",
     "find": " && (prev.keyId || null) === keyId;",
     "replace": " && ((prev.keyId || null) === keyId || boot);",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r3: an unsigned publish counts as a key arriving, so an unsigned tick inside the hour over a "
            "pre-signing row is written",
     "file": "functions/api/roster.js",
     "find": "  const upgrade = verified && (!sameIntent",
     "replace": "  const upgrade = (!sameIntent",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r4: a verified row skips the hourly cap, so every signed tick with a change is written",
     "file": "functions/api/roster.js",
     "find": "  if (prev && age < HOUR_MS && !boot && !upgrade) {",
     "replace": "  if (prev && age < HOUR_MS && !boot && !upgrade && !verified) {",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r4: a signed tick inherits every prior section, so another key's `owned` stays under this key",
     "file": "functions/api/roster.js",
     "find": "  const inherit = !verified || sameIntent;",
     "replace": "  const inherit = !verified || sameIntent || !boot;",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r4: a boot counts as the same verdict, so an unsigned boot over a pre-signing row is skipped "
            "and the row keeps no verdict",
     "file": "functions/api/roster.js",
     "find": "!!prev && prev.intentVerified === verified && prevPub",
     "replace": "!!prev && (prev.intentVerified === verified || boot) && prevPub",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r4: the unchanged check lets any boot through as the same intent, so an unsigned boot over a "
            "pre-signing row is skipped 'unchanged'",
     "file": "functions/api/roster.js",
     "find": "prev.hash === hash && sameIntent && !upgrade) {",
     "replace": "prev.hash === hash && (sameIntent || boot) && !upgrade) {",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r4: a registration counts only on a boot or a change, so after a rosterkey reset an "
            "unchanged tick is skipped and the key stays unregistered",
     "file": "functions/api/roster.js",
     "find": "(!sameIntent || intent.register === true)",
     "replace": "(!sameIntent || (intent.register === true && (boot || prev.hash !== hash)))",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r5: a verified tick inherits only on a boot, so a signed tick drops every section its own key "
            "signed before and did not send this time",
     "file": "functions/api/roster.js",
     "find": "  const inherit = !verified || sameIntent;",
     "replace": "  const inherit = !verified || (sameIntent && boot);",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r5: an unsigned write merges only on a boot, so an unsigned tick drops what it did not send",
     "file": "functions/api/roster.js",
     "find": "  const inherit = !verified || sameIntent;",
     "replace": "  const inherit = (!verified && boot) || sameIntent;",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r5: a tick inherits nothing at all",
     "file": "functions/api/roster.js",
     "find": "Object.assign(inherit ? priorSections(prev) : {}, shaped)",
     "replace": "Object.assign((inherit && boot) ? priorSections(prev) : {}, shaped)",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r5: a row exactly one hour old is still held 'within the hour', against the PC's strict <",
     "file": "functions/api/roster.js",
     "find": "  if (prev && age < HOUR_MS && !boot && !upgrade) {",
     "replace": "  if (prev && age <= HOUR_MS && !boot && !upgrade) {",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r5: a publish that read nothing goes on, so an empty signed publish registers a key",
     "file": "functions/api/roster.js",
     "find": "  if (!Object.keys(sections).length) {",
     "replace": "  if (false) {",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r5: a row with no numeric time counts as written just now, so the hour holds it",
     "file": "functions/api/roster.js",
     "find": "typeof prev.t === \"number\" ? (now - prev.t) : HOUR_MS;",
     "replace": "typeof prev.t === \"number\" ? (now - prev.t) : 0;",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r6: a boot that read nothing goes on, registers the key and writes an empty row",
     "file": "functions/api/roster.js",
     "find": "  if (!Object.keys(sections).length) {",
     "replace": "  if (!Object.keys(sections).length && !boot) {",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r6: 'nothing read' answers ok:false, which the PC reads as a refusal",
     "file": "functions/api/roster.js",
     "find": "ok: true, owner: owner, stored: [], skipped: [\"nothing read\"]",
     "replace": "ok: false, owner: owner, stored: [], skipped: [\"nothing read\"]",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r6: 'unchanged' answers ok:false, which the PC reads as a refusal",
     "file": "functions/api/roster.js",
     "find": "return json(Object.assign({ ok: true, owner: owner, stored: [], skipped: [\"unchanged\"]",
     "replace": "return json(Object.assign({ ok: false, owner: owner, stored: [], skipped: [\"unchanged\"]",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r6: 'within the hour' answers ok:false, which the PC reads as a refusal",
     "file": "functions/api/roster.js",
     "find": "ok: true, owner: owner, stored: [], skipped: [\"within the hour\"]",
     "replace": "ok: false, owner: owner, stored: [], skipped: [\"within the hour\"]",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r6: the hour ends a millisecond early, so a row 1 ms short of it is written again",
     "file": "functions/api/roster.js",
     "find": "  if (prev && age < HOUR_MS && !boot && !upgrade) {",
     "replace": "  if (prev && age < (HOUR_MS - 1) && !boot && !upgrade) {",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r6: a tick carries the old day's count into a new day",
     "file": "functions/api/roster.js",
     "find": "(prev && prev.day === today && typeof prev.n === \"number\") ? prev.n : 0;",
     "replace": "(prev && (prev.day === today || !boot) && typeof prev.n === \"number\") ? prev.n : 0;",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r6: the daily cap holds only on a boot, so ticks past 25 are written",
     "file": "functions/api/roster.js",
     "find": "  if (n >= ROSTER_CAP) {",
     "replace": "  if (n >= ROSTER_CAP && boot) {",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r7: the daily cap holds only for an unsigned publish, so a signed one past 25 is written",
     "file": "functions/api/roster.js",
     "find": "  if (n >= ROSTER_CAP) {",
     "replace": "  if (n >= ROSTER_CAP && !verified) {",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r7: the daily cap does not hold for a key arriving",
     "file": "functions/api/roster.js",
     "find": "  if (n >= ROSTER_CAP) {",
     "replace": "  if (n >= ROSTER_CAP && !upgrade) {",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r7: a signed publish restarts the day's count at 0",
     "file": "functions/api/roster.js",
     "find": "(prev && prev.day === today && typeof prev.n === \"number\") ? prev.n : 0;",
     "replace": "(prev && prev.day === today && typeof prev.n === \"number\" && !verified) ? prev.n : 0;",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r7: a key arriving restarts the day's count at 0",
     "file": "functions/api/roster.js",
     "find": "(prev && prev.day === today && typeof prev.n === \"number\") ? prev.n : 0;",
     "replace": "(prev && prev.day === today && typeof prev.n === \"number\" && !upgrade) ? prev.n : 0;",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r7: why a signature failed is said only on a boot",
     "file": "functions/api/roster.js",
     "find": "  if (sig.state === \"bad\") said.sigWhy = sig.why;",
     "replace": "  if (sig.state === \"bad\" && boot) said.sigWhy = sig.why;",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r8: sigWhy says only 'bad', not why the signature failed",
     "file": "functions/api/roster.js",
     "find": "  if (sig.state === \"bad\") said.sigWhy = sig.why;",
     "replace": "  if (sig.state === \"bad\") said.sigWhy = sig.state;",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r8: a signed publish under the same key keeps yesterday's count on a new day",
     "file": "functions/api/roster.js",
     "find": "(prev && prev.day === today && typeof prev.n === \"number\") ? prev.n : 0;",
     "replace": "(prev && (prev.day === today || sameIntent) && typeof prev.n === \"number\") ? prev.n : 0;",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r8: 'nothing read' holds only for a signed publish, so an unsigned empty one writes a row",
     "file": "functions/api/roster.js",
     "find": "  if (!Object.keys(sections).length) {",
     "replace": "  if (!Object.keys(sections).length && verified) {",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r8: the roster row is stored with no lapse",
     "file": "functions/api/roster.js",
     "find": "    await kv.put(rowKey, JSON.stringify(rec), { expirationTtl: TTL_S });",
     "replace": "    await kv.put(rowKey, JSON.stringify(rec));",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r7: a failed put is refused as 'Error: ...' rather than the store's own words",
     "file": "functions/api/roster.js",
     "find": "  } catch (e) {\n    return refuse(\"roster would not take this publish: \" + String((e && e.message) || e).slice(0, 140));\n  }\n  return json(",
     "replace": "  } catch (e) {\n    return refuse(\"roster would not take this publish: \" + String((e || e.message) && e).slice(0, 140));\n  }\n  return json(",
     "matches": 1, "needs": "node"},
    {"why": "M6 T3 review r7: a failed rosterkey put is refused as 'Error: ...' rather than the store's own words",
     "file": "functions/api/roster.js",
     "find": "      return refuse(\"roster would not take this publish: \" + String((e && e.message) || e).slice(0, 140));\n    }\n    said.registered = true;",
     "replace": "      return refuse(\"roster would not take this publish: \" + String((e || e.message) && e).slice(0, 140));\n    }\n    said.registered = true;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2516 (#95): a verified row stops recording its key, so the same PC's next signed publish drops every "
            "section it signed before and could not read this time",
     "file": "functions/api/roster.js",
     "find": "  if (pub) rec.pub = pub;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2517 (#95): the roster buttons drop each row's signature again, so a forged NOT-verified row draws "
            "exactly like his own",
     "file": "control_ui.html",
     "find": "          + (sig ? '<span class=\"roster-sig ' + esc(sig.cls) + '\">' + esc(sig.words) + '</span>' : '') + '</button>';\n",
     "replace": "          + '</button>';\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2517 (#95): the shadow bar says '<owner> · published · read only' again, whoever signed the row",
     "file": "control_ui.html",
     "find": "      var say = owner + ' · ' + rowAge + signed + ' · read only';\n",
     "replace": "      var say = owner + ' · ' + rowAge + ' · read only';\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2517 (#95): this PC's own last publish no longer leads the panel, so a refused or unsigned publish is "
            "said only by the doctor",
     "file": "control_ui.html",
     "find": "      else body.innerHTML = lead + owners.map(function (row) {\n",
     "replace": "      else body.innerHTML = owners.map(function (row) {\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2517 (#95): a published row the console sent no words for draws silent instead of UNKNOWN",
     "file": "control_ui.html",
     "find": "    return { cls: 'roster-unknown', words: 'signature UNKNOWN: the console did not say' };\n",
     "replace": "    return null;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2517 (#95): panel_words stops giving a published row its signature words",
     "file": "roster_publish.py",
     "find": "        row[\"sig\"] = {\"cls\": cls, \"words\": words}\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2517 (#95): the roster-cache route stops calling panel_words, so the panel has no words to draw",
     "file": "control_app.py",
     "find": "            _rp.panel_words(data)\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2517 (#95): NOT signature-verified loses its colour and draws like any other line",
     "file": "control_ui.html",
     "find": "  .roster-unverified { color: var(--st-needs); }\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2513 (#95): view_one drops intentVerified, so no viewer can show whether a row was its owner's",
     "file": "roster_publish.py",
     "find": "    out[\"intentVerified\"] = verified_of(row)\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2511 (#95): hash_of walks code points again, so an emoji row reads CORRUPT for every viewer",
     "file": "roster_publish.py",
     "find": "    data = text.encode(\"utf-16-le\", \"surrogatepass\")\n    for i in range(0, len(data), 2):\n"
             "        h ^= data[i] | (data[i + 1] << 8)\n",
     "replace": "    for ch in text:\n        h ^= ord(ch)\n",
     "matches": 1},
    {"why": "REG-2512 (#95): due() answers 'unchanged' before it looks at boot, so a forged row is never healed",
     "file": "roster_publish.py",
     "find": "    if state.get(\"hash\") == digest and not boot:\n",
     "replace": "    if state.get(\"hash\") == digest:\n",
     "matches": 1},
    {"why": "REG-2510 (#95): the console builds the signature headers and posts without them",
     "file": "control_app.py",
     "find": "            headers.update(signed)\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2510 (#95): a key file that cannot be read is replaced by a new key, so a registered owner is refused "
            "with the evidence gone",
     "file": "roster_sign.py",
     "find": "    if why != \"absent\":\n        return None, why, False\n",
     "replace": "    if why != \"absent\":\n        os.remove(path)\n",
     "matches": 1},
    {"why": "REG-2515 (#112): the boot sweep of d2jsp scratch loses its guard, so one failure stops the console booting",
     "file": "control_app.py",
     "find": "    try:\n        import d2jsp_chrome as _d2jsp_boot\n",
     "replace": "    import d2jsp_chrome as _d2jsp_boot\n    _d2jsp_boot._sweep_stale_scratch()\n    try:\n",
     "matches": 1},
    {"why": "REG-2514 (#95): the doctor stops asking whether every roster publish is signed",
     "file": "console_doctor.py",
     "find": "    (\"every roster publish is signed\", _check_every_roster_publish_is_signed),\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
