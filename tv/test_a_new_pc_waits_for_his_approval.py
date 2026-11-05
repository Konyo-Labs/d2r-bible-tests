# -*- coding: utf-8 -*-
"""v3862 (item 11) - A NEW PC THAT ASKS FOR ONE OF HIS LABELS WAITS FOR HIS APPROVAL, AND ONLY HIS MAC CAN GIVE IT.

MEASURED 2026-11-04: the new work ALT came up as "Konyo · ALT" while the old ALT's key was registered for that label,
so every publish it made was refused - correctly (trust on first use, #95) - and the only way out was Konyo running
wrangler on the Mac by hand. Now a refused publish whose signature VERIFIES under a different key leaves one pending
request; his Mac's console (an APPROVER label) signs an approval with its OWN registered key and the worker puts the
new key in place. Pinned, driving the real worker in node with real Ed25519 keys (roster_sign):
  · a new key's refused publish leaves ONE request (asking again costs no write) and says it is waiting;
  · the requests list names labels and key ids, never a public key;
  · only an approver label, signed by ITS registered key, with a fresh signedAt, naming the pending key id, approves;
  · an approval is used once (a replay finds no request); deny drops the request and keeps the old key;
  · after approval the new PC publishes; the console offers the buttons only on an approver PC, escaped.
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
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import roster_sign as RS  # noqa: E402

NODE = shutil.which("node")
ROSTER_JS = os.path.join(ROOT, "functions", "api", "roster.js")
OWNER = "Konyo · ALT"
APPROVER = "Konyo · Mac"
T0 = 1792800000000

_HARNESS = r"""
import { pathToFileURL } from 'node:url';
import { readFileSync } from 'node:fs';
const CFG = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const bytes = (s) => new Uint8Array(Buffer.from(s || '', 'base64'));
let store = new Map(Object.entries(CFG.seed || {}).map(([k, v]) => [k, typeof v === 'string' ? v : JSON.stringify(v)]));
let puts = [];
const kv = { async get(n) { return store.has(n) ? store.get(n) : null; },
             async put(n, v) { puts.push(n); store.set(n, v); },
             async delete(n) { puts.push('-' + n); store.delete(n); } };
const mod = await import(pathToFileURL(CFG.file).href);
const out = { steps: [], approvers: mod.APPROVERS };
for (const step of (CFG.steps || [])) {
  puts = [];
  const realNow = Date.now;
  if (typeof step.now === 'number') Date.now = () => step.now;
  if (step.get) {
    const res = await mod.onRequestGet({ request: new Request('https://bull-4-u.com/api/roster?' + step.get),
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
out.store = Object.fromEntries(store);
process.stdout.write(JSON.stringify(out));
"""


def _node(cfg):
    with tempfile.TemporaryDirectory(prefix="tvd_approve_js_") as d:
        h, c = os.path.join(d, "h.mjs"), os.path.join(d, "cfg.json")
        io.open(h, "w", encoding="utf-8").write(_HARNESS)
        io.open(c, "w", encoding="utf-8").write(json.dumps(dict(cfg, file=ROSTER_JS)))
        r = subprocess.run([NODE, h, c], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    if r.returncode != 0:
        raise AssertionError("the roster harness failed rc=%s\n%s" % (r.returncode, r.stderr[-2000:]))
    return json.loads(r.stdout)


def _pub_of(path):
    with io.open(path, encoding="utf-8") as fh:
        return RS.unb64u(json.load(fh)["pub"])


@unittest.skipUnless(NODE, "node is absent - the worker is UNMEASURED here, never a pass")
class TheWorkerWaitsForHim(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="tvd_approve_keys_")
        cls.keys = {}
        for n in ("old_alt", "new_alt", "mac", "dean"):
            p = RS.key_path_in(os.path.join(cls.dir, n))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            key, why, _m = RS.load_or_create(p)
            assert key is not None, why
            cls.keys[n] = p
        cls.ids = {n: RS.key_id(_pub_of(p)) for n, p in cls.keys.items()}

        def reg(n):
            pub = _pub_of(cls.keys[n])
            return {"pub": RS.b64u(pub), "keyId": RS.key_id(pub), "at": 1}
        cls.seed = {"rosterkey:" + OWNER: reg("old_alt"), "rosterkey:" + APPROVER: reg("mac"), "rosterkey:Dean": reg("dean")}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, True)

    def _post(self, body, key, now=T0):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        return {"raw": base64.b64encode(raw).decode("ascii"), "headers": RS.sign_headers(self.keys[key], raw)[0],
                "now": now}

    def _rows(self, key, now=T0):
        return self._post({"owner": OWNER, "boot": True, "sections": {"characters": {
            "asOf": 1000, "counts": 1, "rows": [{"name": "Sorceress", "cls": "Sorceress", "level": 90}]}}}, key, now)

    def _approve(self, key, decision="approve", approver=APPROVER, key_id=None, signed_at=T0 + 60000, now=T0 + 60000):
        return self._post({"kind": "approve", "approver": approver, "owner": OWNER,
                           "keyId": key_id or self.ids["new_alt"], "decision": decision, "signedAt": signed_at}, key, now)

    def test_a_new_key_asks_once_and_says_it_is_waiting(self):
        out = _node({"seed": self.seed, "steps": [self._rows("new_alt"), self._rows("new_alt", T0 + 5000)]})
        a, b = out["steps"]
        self.assertFalse(a["reply"]["ok"], "a second PC's key was taken for a label another PC holds")
        self.assertEqual(a["reply"].get("approval"), "requested")
        self.assertIn("waiting for " + APPROVER, a["reply"]["why"])
        self.assertEqual(a["puts"], ["rosterkeyreq:" + OWNER])
        self.assertEqual(b["puts"], [], "the same key asking again spent a write")

    def test_the_list_names_labels_and_ids_never_a_key(self):
        out = _node({"seed": self.seed, "steps": [self._rows("new_alt"), {"get": "requests=1"}]})
        got = out["steps"][1]["get"]
        self.assertEqual([(r["owner"], r["keyId"]) for r in got["requests"]], [(OWNER, self.ids["new_alt"])])
        self.assertNotIn("pub", json.dumps(got["requests"]), "the requests list carries a public key")

    def test_his_mac_approves_once_and_the_new_pc_publishes(self):
        out = _node({"seed": self.seed, "steps": [
            self._rows("new_alt"), self._approve("mac"), self._approve("mac", now=T0 + 70000, signed_at=T0 + 70000),
            self._rows("new_alt", T0 + 90000)]})
        ask, ok, replay, pub = out["steps"]
        self.assertTrue(ok["reply"].get("ok"), ok["reply"])
        self.assertEqual(json.loads(out["store"]["rosterkey:" + OWNER])["keyId"], self.ids["new_alt"])
        self.assertNotIn("rosterkeyreq:" + OWNER, out["store"], "the request outlived its approval")
        self.assertFalse(replay["reply"].get("ok"), "an approval was used twice")
        self.assertNotEqual(pub["reply"].get("ok"), False, "the approved PC still cannot publish: %r" % pub["reply"])

    def test_only_an_approver_signed_by_its_own_key_with_a_fresh_clock_naming_the_key(self):
        for name, step in (("not an approver label", self._approve("dean", approver="Dean")),
                           ("the approver label, another key", self._approve("dean")),
                           ("the new PC approving itself", self._approve("new_alt")),
                           ("another key id", self._approve("mac", key_id="0" * 12)),
                           ("a stale signature", self._approve("mac", signed_at=T0 - 3600000))):
            with self.subTest(case=name):
                out = _node({"seed": self.seed, "steps": [self._rows("new_alt"), step]})
                self.assertFalse(out["steps"][1]["reply"].get("ok"), "%s approved a key" % name)
                self.assertEqual(json.loads(out["store"]["rosterkey:" + OWNER])["keyId"], self.ids["old_alt"])

    def test_deny_drops_the_request_and_keeps_the_old_key(self):
        out = _node({"seed": self.seed, "steps": [self._rows("new_alt"), self._approve("mac", decision="deny")]})
        self.assertTrue(out["steps"][1]["reply"].get("ok"))
        self.assertNotIn("rosterkeyreq:" + OWNER, out["store"])
        self.assertEqual(json.loads(out["store"]["rosterkey:" + OWNER])["keyId"], self.ids["old_alt"])

    def test_the_two_sides_name_the_same_approvers(self):
        import control_app as CA
        out = _node({"seed": {}, "steps": []})
        self.assertEqual(tuple(out["approvers"]), CA.ROSTER_APPROVERS)


class TheConsoleOffersIt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import control_app as CA
        cls.CA = CA

    def setUp(self):
        self._saved = self.CA._roster_my_label
        self.CA._KEY_REQUESTS.update(at=0.0, v=None)

    def tearDown(self):
        self.CA._roster_my_label = self._saved
        self.CA._KEY_REQUESTS.update(at=0.0, v=None)

    def test_only_an_approver_pc_asks_and_offers(self):
        self.CA._roster_my_label = lambda: "Dean"

        def boom(*a, **k):
            raise AssertionError("a PC that approves nothing asked the roster")
        r = self.CA.roster_key_requests(force=True, _get=boom)
        self.assertFalse(r["approver"])
        self.assertEqual(self.CA.roster_approve(OWNER, "abc", "approve", _post=boom)["ok"], False)
        self.CA._roster_my_label = lambda: APPROVER
        r = self.CA.roster_key_requests(force=True, _get=lambda url: {"ok": True, "requests": [
            {"owner": OWNER, "keyId": "aaaaaaaaaaaa", "at": T0}]})
        self.assertTrue(r["approver"])
        self.assertEqual(r["requests"][0]["owner"], OWNER)
        self.assertIsNone(self.CA.roster_key_requests(force=True, _get=lambda url: {"ok": False, "why": "x"})["requests"],
                          "a failed read became an empty list")

    def test_the_approval_is_signed_as_this_pc(self):
        self.CA._roster_my_label = lambda: APPROVER
        sent = {}

        def post(url, body, key_path):
            sent.update(url=url, body=body, key=key_path)
            return {"ok": True}
        self.assertFalse(self.CA.roster_approve(OWNER, "aaaaaaaaaaaa", "maybe", _post=post)["ok"])
        self.assertEqual(sent, {}, "a decision that is neither approve nor deny was posted")
        self.CA.roster_approve(OWNER, "aaaaaaaaaaaa", "approve", _post=post, now_ms=T0)
        self.assertEqual(sent["body"], {"kind": "approve", "approver": APPROVER, "owner": OWNER,
                                        "keyId": "aaaaaaaaaaaa", "decision": "approve", "signedAt": T0})
        self.assertTrue(sent["key"].endswith(".roster_key.json"))

    @unittest.skipUnless(NODE, "node is absent - the card is UNMEASURED here")
    def test_the_card_is_escaped_and_only_for_an_approver(self):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        i = ui.index("  window._fleetKeyReqHtml = function (kr, nowMs) {")
        j = ui.index("\n  };", i)
        fn = "var window = {};\n" + ui[i:j + 4]
        kr = {"approver": True, "requests": [{"owner": "<img src=x>", "keyId": "aaaaaaaaaaaa", "at": T0 - 120000}]}
        js = fn + "\nconsole.log(JSON.stringify([window._fleetKeyReqHtml(%s, %d), window._fleetKeyReqHtml(%s, %d)]));" % (
            json.dumps(kr), T0, json.dumps(dict(kr, approver=False)), T0)
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[:400])
        html, none = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertNotIn("<img", html, "a label from the network reached the card unescaped")
        self.assertIn("2 min ago", html)
        self.assertIn('data-decision="approve"', html)
        self.assertIn('data-decision="deny"', html)
        self.assertEqual(none, "", "a PC that approves nothing drew the buttons")


RED_PROOF = [
    {"why": "v3862 - an approval signed by ANY key is taken (the approver's registered key is never asked)",
     "file": "functions/api/roster.js",
     "find": "  if (intent.refused || intent.verified !== true || intent.register) {\n"
             "    return refuse(\"roster would not take this approval: \"",
     "replace": "  if (false) {\n    return refuse(\"roster would not take this approval: \"",
     "matches": 1},
    {"why": "v3862 - an approval is used twice (the request outlives it)",
     "file": "functions/api/roster.js",
     "find": "  await kv.delete(name);\n  return json({ ok: true, owner: owner, keyId: req.keyId, decision: decision, by: approver }, 200);\n",
     "replace": "  return json({ ok: true, owner: owner, keyId: req.keyId, decision: decision, by: approver }, 200);\n",
     "matches": 1},
    {"why": "v3862 - any label may approve a PC",
     "file": "functions/api/roster.js",
     "find": "  if (APPROVERS.indexOf(approver) === -1) return refuse(",
     "replace": "  if (false) return refuse(",
     "matches": 1},
    {"why": "v3862 - a refused new key leaves no request: he is never asked and the PC stays refused",
     "file": "functions/api/roster.js",
     "find": "      ? await noteKeyRequest(kv, owner, sig, intent.registeredKeyId, Date.now()) : false;\n",
     "replace": "      ? false : false;\n",
     "matches": 1},
    {"why": "v3862 - the card paints a label unescaped",
     "file": "tv/control_ui.html",
     "find": "      return '<div class=\"fleet-none\" data-keyreq=\"' + esc(q.owner) + '\">\\ud83d\\udd11 A new PC asks to be <b>'\n"
             "           + esc(q.owner) + '</b>",
     "replace": "      return '<div class=\"fleet-none\" data-keyreq=\"' + esc(q.owner) + '\">\\ud83d\\udd11 A new PC asks to be <b>'\n"
                "           + q.owner + '</b>",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
