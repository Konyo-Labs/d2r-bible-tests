# -*- coding: utf-8 -*-
"""#27 (v3880) - ONE LABEL HOLDS TWO PCS: THE OLD ALT'S CHARACTERS REACH KONYOLOCK'S CARD.

His 11-05 ruling for the two ALTs: "share the profile, just split the rows". MEASURED 11-07 over SSH: the OLD ALT holds
17 characters and their gear (konyolock: Enigma, Goldwrap, Raven Frost), but its profile never left the PC - its
.roster_profile_state.json read "the owner is not one of the five labels" (its nickname is "OLD PC ALT") - while the WORK
ALT, which holds the "Konyo · ALT" label and key, uploads fine and has learned 0 characters. So GrokBot's look at the
ALT's shadow read KonyoLock "No gear seen yet" (#230 6655590795). And the site kept ONE key per label: approving the old
ALT's key would have REPLACED the work ALT's.

Now (functions/api/roster.js RING): a label keeps its first key and may hold RING_MAX more, each another PC he approved
with "add" from his Mac. Each such PC publishes its rows, profile and frames digest into its own slot (record + "@" + key
id), so neither overwrites the other; a replace keeps the ring. The profile GET serves each other PC's characters answer
while its key is still in the ring; the Mac's shadow folds them into the label's (console_snapshot.with_others, gear by
REG-3069's rule) and names that PC. A PC whose nickname is not a label shares one by `sharesLabel` - only one of the five.
Pinned driving the real worker in node with real Ed25519 keys (roster_sign). RED_PROOF below.
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
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import roster_sign as RS  # noqa: E402
import console_snapshot as CS  # noqa: E402

NODE = shutil.which("node")
ROSTER_JS = os.path.join(ROOT, "functions", "api", "roster.js")
OWNER = "Konyo · ALT"
APPROVER = "Konyo · Mac"
T0 = 1792800000000
WORLD = {"machine": "windows", "profile": "main", "os": "WINDOWS", "ledger": "", "cousin": True}

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
const out = { steps: [], ringMax: mod.RING_MAX };
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
    with tempfile.TemporaryDirectory(prefix="tvd_ring_js_") as d:
        h, c = os.path.join(d, "h.mjs"), os.path.join(d, "cfg.json")
        with io.open(h, "w", encoding="utf-8") as fh:
            fh.write(_HARNESS)
        with io.open(c, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(cfg, file=ROSTER_JS)))
        r = subprocess.run([NODE, h, c], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    if r.returncode != 0:
        raise AssertionError("the roster harness failed rc=%s\n%s" % (r.returncode, r.stderr[-2000:]))
    return json.loads(r.stdout)


def _pub_of(path):
    with io.open(path, encoding="utf-8") as fh:
        return RS.unb64u(json.load(fh)["pub"])


def _chars(names, gear=None):
    """A characters answer as the console uploads it (only the fields the site allows)."""
    return {"ok": True, "chars": [{"key": n.lower(), "name": n} for n in names], "gear": gear if gear is not None else {},
            "gearWhy": None, "tierBars": {"watched": 3, "seen": 1}, "sessions": {}}


def _gear(slots, ts=1000):
    return {"name": None, "slots": [{"slot": s, "item": it, "sightings": 3, "tier": "WATCHED", "ts": ts, "reel": "r1"}
                                    for s, it in slots], "unplaced": [], "reels": 1, "lastTs": ts}


OLD_ALT = _chars(["KonyoLock", "Konyodin"], {"konyolock": _gear([("torso", "Enigma"), ("belt", "Goldwrap")]),
                                             "konyodin": _gear([("torso", "Fortitude")])})
WORK_ALT = _chars([])


@unittest.skipUnless(NODE, "node is absent - the worker is UNMEASURED here, never a pass")
class TheSiteHoldsTwoPcsUnderOneLabel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="tvd_ring_keys_")
        cls.keys = {}
        for n in ("work_alt", "old_alt", "third", "fourth", "mac"):
            p = RS.key_path_in(os.path.join(cls.dir, n))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            key, why, _m = RS.load_or_create(p)
            assert key is not None, why
            cls.keys[n] = p
        cls.ids = {n: RS.key_id(_pub_of(p)) for n, p in cls.keys.items()}

        def reg(n):
            pub = _pub_of(cls.keys[n])
            return {"pub": RS.b64u(pub), "keyId": RS.key_id(pub), "at": 1}
        cls.reg = staticmethod(reg)
        cls.seed = {"rosterkey:" + OWNER: reg("work_alt"), "rosterkey:" + APPROVER: reg("mac")}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, True)

    def _post(self, body, key, now=T0):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        return {"raw": base64.b64encode(raw).decode("ascii"), "headers": RS.sign_headers(self.keys[key], raw)[0], "now": now}

    def _rows(self, key, name, now=T0):
        return self._post({"owner": OWNER, "boot": True, "sections": {"characters": {
            "asOf": 1000, "counts": 1, "rows": [{"name": name, "cls": "Sorceress", "level": 90}]}}}, key, now)

    def _profile(self, key, answer, now=T0):
        stores = {"d2r_owned": "[]", "d2r_api_world": json.dumps(WORLD, separators=(",", ":"), sort_keys=True),
                  "d2r_api_chars_learned": json.dumps(answer, separators=(",", ":"))}
        return self._post({"kind": "profile", "owner": OWNER, "boot": True, "signedAt": now, "hash": CS.digest(stores),
                           "stores": stores}, key, now)

    def _decide(self, key_name, decision, now):
        return self._post({"kind": "approve", "approver": APPROVER, "owner": OWNER, "keyId": self.ids[key_name],
                           "decision": decision, "signedAt": now}, "mac", now)

    def _added(self, extra=()):
        """the old ALT asks, his Mac adds it as another PC; then `extra` steps"""
        return [self._rows("old_alt", "KonyoLock"), self._decide("old_alt", "add", T0 + 60000)] + list(extra)

    def test_add_keeps_the_first_key_and_rings_the_second(self):
        """* THE POINT: an added PC never replaces the label's first key"""
        out = _node({"seed": self.seed, "steps": self._added()})
        ask, add = out["steps"]
        self.assertEqual(ask["reply"].get("approval"), "requested", ask["reply"])
        self.assertTrue(add["reply"].get("ok"), add["reply"])
        held = json.loads(out["store"]["rosterkey:" + OWNER])
        self.assertEqual(held["keyId"], self.ids["work_alt"], "adding the old ALT replaced the work ALT's key")
        self.assertEqual([e["keyId"] for e in held.get("also") or []], [self.ids["old_alt"]])
        self.assertNotIn("rosterkeyreq:" + OWNER, out["store"], "the request outlived its approval")

    def test_each_pc_publishes_into_its_own_rows(self):
        out = _node({"seed": self.seed, "steps": self._added([
            self._rows("old_alt", "KonyoLock", T0 + 120000), self._rows("work_alt", "Konyobear", T0 + 130000),
            {"get": "x=1", "now": T0 + 140000}])})
        old, work, got = out["steps"][2:]
        self.assertTrue(old["reply"].get("ok"), old["reply"])
        self.assertEqual(old["reply"].get("slot"), self.ids["old_alt"])
        self.assertIn("roster:" + OWNER + "@" + self.ids["old_alt"], old["puts"])
        self.assertTrue(work["reply"].get("ok"), work["reply"])
        self.assertIn("roster:" + OWNER, work["puts"], "the first PC's rows moved")
        row = [o for o in got["get"]["owners"] if o["owner"] == OWNER][0]
        self.assertEqual(row["sections"]["characters"]["rows"][0]["name"], "Konyobear")
        others = row.get("others") or []
        self.assertEqual([o["keyId"] for o in others], [self.ids["old_alt"]])
        self.assertEqual(others[0]["sections"]["characters"]["rows"][0]["name"], "KonyoLock")

    def test_the_label_profile_serves_the_other_pcs_characters(self):
        out = _node({"seed": self.seed, "steps": self._added([
            self._profile("old_alt", OLD_ALT, T0 + 120000), self._profile("work_alt", WORK_ALT, T0 + 130000),
            {"get": "profile=" + OWNER, "now": T0 + 140000}])})
        old, work, got = out["steps"][2:]
        self.assertTrue(old["reply"].get("ok"), old["reply"])
        self.assertTrue(work["reply"].get("ok"), work["reply"])
        prof = got["get"]
        self.assertEqual(json.loads(prof["stores"]["d2r_api_chars_learned"])["chars"], [], "the first PC's answer moved")
        others = prof.get("others") or []
        self.assertEqual([o["keyId"] for o in others], [self.ids["old_alt"]])
        self.assertEqual(sorted(others[0]["stores"]), ["d2r_api_chars_learned", "d2r_api_world"],
                         "another PC's profile serves more than its characters")
        self.assertEqual(json.loads(others[0]["stores"]["d2r_api_chars_learned"])["gear"]["konyolock"]["slots"][0]["item"],
                         "Enigma")

    def test_a_replace_keeps_the_other_pcs(self):
        out = _node({"seed": self.seed, "steps": self._added([
            self._rows("third", "X", T0 + 120000), self._decide("third", "approve", T0 + 130000)])})
        held = json.loads(out["store"]["rosterkey:" + OWNER])
        self.assertEqual(held["keyId"], self.ids["third"])
        self.assertEqual([e["keyId"] for e in held.get("also") or []], [self.ids["old_alt"]],
                         "replacing the first key dropped the other PC he added")

    def test_the_ring_is_bounded(self):
        steps = self._added([self._rows("third", "X", T0 + 120000), self._decide("third", "add", T0 + 130000),
                             self._rows("fourth", "Y", T0 + 140000), self._decide("fourth", "add", T0 + 150000)])
        out = _node({"seed": self.seed, "steps": steps})
        self.assertEqual(out["ringMax"], 2)
        self.assertTrue(out["steps"][3]["reply"].get("ok"))
        self.assertFalse(out["steps"][5]["reply"].get("ok"), "a label took more PCs than the ring holds")
        self.assertEqual(len(json.loads(out["store"]["rosterkey:" + OWNER])["also"]), 2)

    def test_a_record_not_signed_by_its_ring_key_is_never_served(self):
        """a profile in a slot whose stored key is not that ring entry's key (or a slot no longer in the ring) is not the label's"""
        out = _node({"seed": self.seed, "steps": self._added([self._profile("old_alt", OLD_ALT, T0 + 120000),
                                                              self._profile("work_alt", WORK_ALT, T0 + 125000)])})
        store = dict(out["store"])
        honest = _node({"seed": store, "steps": [{"get": "profile=" + OWNER, "now": T0 + 130000}]})["steps"][0]["get"]
        self.assertEqual([o["keyId"] for o in honest.get("others") or []], [self.ids["old_alt"]],
                         "premise: the untouched slot is served (else this case proves nothing)")
        slot = "roster:" + OWNER + ":profile@" + self.ids["old_alt"]
        forged = json.loads(store[slot])
        forged["pub"] = RS.b64u(_pub_of(self.keys["third"]))
        store[slot] = forged
        got = _node({"seed": store, "steps": [{"get": "profile=" + OWNER, "now": T0 + 130000}]})["steps"][0]["get"]
        self.assertNotIn("others", got, "a slot record signed by another key was served as the label's PC")
        held = json.loads(store["rosterkey:" + OWNER])
        held.pop("also", None)
        store[slot] = json.loads(out["store"][slot])
        store["rosterkey:" + OWNER] = held
        got = _node({"seed": store, "steps": [{"get": "profile=" + OWNER, "now": T0 + 130000}]})["steps"][0]["get"]
        self.assertNotIn("others", got, "a PC no longer in the ring was still served")

    def test_a_malformed_ring_entry_is_never_trusted(self):
        seed = dict(self.seed)
        bad = dict(self.reg("work_alt"))
        bad["also"] = [{"pub": self.reg("old_alt")["pub"], "keyId": "../../x"}]
        seed["rosterkey:" + OWNER] = bad
        out = _node({"seed": seed, "steps": [self._rows("old_alt", "KonyoLock")]})
        self.assertFalse(out["steps"][0]["reply"].get("ok"), "a ring entry with no 12-hex key id signed for the label")


class TheShadowFoldsTheOtherPcsIn(unittest.TestCase):

    def _rec(self, others):
        stores = {"d2r_owned": "[]", "d2r_api_chars_learned": json.dumps(WORK_ALT)}
        return {"owner": OWNER, "t": T0, "hash": CS.digest(stores), "stores": stores, "others": others}

    def _other(self, answer, t=T0 - 600000):
        return {"keyId": "a8834dcd53c5", "t": t, "stores": {"d2r_api_chars_learned": json.dumps(answer)}}

    def test_konyolock_wears_the_enigma_the_old_alt_saw(self):
        """* THE POINT: GrokBot's 'No gear seen yet' - the label's first PC learned nothing, the other PC saw Enigma"""
        v = CS.view(OWNER, self._rec([self._other(OLD_ALT)]), T0)
        self.assertTrue(v["ok"], v)
        ans = json.loads(v["stores"]["d2r_api_chars_learned"])
        self.assertEqual(sorted(c["key"] for c in ans["chars"]), ["konyodin", "konyolock"])
        self.assertEqual([s["item"] for s in ans["gear"]["konyolock"]["slots"] if s["item"]], ["Enigma", "Goldwrap"])
        self.assertIn("another PC of this label (key a8834dcd53c5, uploaded 10 min ago) adds 2 character(s)", v["words"])
        self.assertEqual(v["hash"], self._rec([])["hash"], "the record's own hash was rewritten")

    def test_one_character_on_both_pcs_takes_the_later_look(self):
        first = _chars(["KonyoLock"], {"konyolock": _gear([("torso", "Chains of Honor")], ts=500)})
        rec = self._rec([self._other(OLD_ALT)])
        rec["stores"] = {"d2r_owned": "[]", "d2r_api_chars_learned": json.dumps(first)}
        rec["hash"] = CS.digest(rec["stores"])
        ans = json.loads(CS.view(OWNER, rec, T0)["stores"]["d2r_api_chars_learned"])
        torso = [s for s in ans["gear"]["konyolock"]["slots"] if s["slot"] == "torso"][0]
        self.assertEqual(torso["item"], "Enigma", "the older look won")
        self.assertEqual([a["item"] for a in torso["alsoSeen"]], ["Chains of Honor"])
        self.assertEqual(len(ans["chars"]), 2, "one character on both PCs became two rows")

    def test_an_unreadable_other_is_named_never_guessed(self):
        bad = {"keyId": "a8834dcd53c5", "t": T0, "stores": {"d2r_api_chars_learned": "{not json"}}
        v = CS.view(OWNER, self._rec([bad]), T0)
        self.assertEqual(json.loads(v["stores"]["d2r_api_chars_learned"])["chars"], [])
        self.assertIn("adds nothing: its characters answer could not be read", v["words"])

    def test_the_cache_keeps_the_other_pcs(self):
        d = tempfile.mkdtemp(prefix="tvd_ring_cache_")
        try:
            rec = self._rec([self._other(OLD_ALT)])
            self.assertTrue(CS.write_cache(d, rec))
            self.assertEqual(CS.read_cache(d, OWNER).get("others"), rec["others"])
        finally:
            shutil.rmtree(d, True)


class APcSharesALabel(unittest.TestCase):

    def _claimed(self, ident):
        import control_app as CA
        d = tempfile.mkdtemp(prefix="tvd_ring_ident_")
        try:
            p = os.path.join(d, "identity.json")
            with io.open(p, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(ident))
            with mock.patch.object(CA, "IDENTITY_PATH", p):
                return CA._roster_claimed_name()
        finally:
            shutil.rmtree(d, True)

    def test_the_old_alt_publishes_as_the_label_it_shares(self):
        self.assertEqual(self._claimed({"nickname": "OLD PC ALT", "sharesLabel": OWNER}), OWNER)
        self.assertEqual(self._claimed({"nickname": "OLD PC ALT"}), "OLD PC ALT", "a PC that shares nothing changed name")

    def test_only_one_of_the_five_labels_is_shared(self):
        self.assertEqual(self._claimed({"nickname": "OLD PC ALT", "sharesLabel": "Anyone"}), "OLD PC ALT")
        self.assertEqual(self._claimed({"nickname": "Dean", "sharesLabel": OWNER}), "Dean",
                         "a PC that IS a label was moved under another")

    def test_his_mac_offers_add_beside_replace(self):
        import control_app as CA
        sent = {}
        with mock.patch.object(CA, "_roster_my_label", lambda: APPROVER):
            CA.roster_approve(OWNER, "a8834dcd53c5", "add", _post=lambda url, body, key: sent.update(body) or {"ok": True})
        self.assertEqual(sent.get("decision"), "add")
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        i = ui.index("window._fleetKeyReqHtml = function")
        card = ui[i:ui.index("window._fleetKeyReqPaint", i)]
        self.assertIn('data-decision="add" onclick="window._fleetKeyDecide(this)"', card)
        self.assertIn(">Add as another PC</button>", card)


RED_PROOF = [
    {"why": "#27 - another PC he added for the label is refused as a stranger",
     "file": "functions/api/roster.js",
     "find": "      const slot = ringSlotOf(registered, sig.pub);\n",
     "replace": "      const slot = null;\n",
     "matches": 1, "needs": "node"},
    {"why": "#27 - adding the old ALT replaces the work ALT's key",
     "file": "functions/api/roster.js",
     "find": "    const rec = Object.assign({}, held, { also: ring.concat([{ pub: req.pub, keyId: req.keyId, at: now, approvedBy: approver }]) });",
     "replace": "    const rec = { pub: req.pub, keyId: req.keyId, at: now, approvedBy: approver };",
     "matches": 1, "needs": "node"},
    {"why": "#27 - two PCs of one label overwrite each other's rows",
     "file": "functions/api/roster.js",
     "find": "  const rowKey = slotName(key, intent.slot);",
     "replace": "  const rowKey = key;",
     "matches": 1, "needs": "node"},
    {"why": "#27 - replacing the first key drops the other PCs",
     "file": "functions/api/roster.js",
     "find": "    if (kept.length) rec.also = kept;",
     "replace": "    if (false) rec.also = kept;",
     "matches": 1, "needs": "node"},
    {"why": "#27 - a slot record signed by another key is served as the label's PC",
     "file": "functions/api/roster.js",
     "find": "    if (b64uKey(rec.pub) !== b64uKey(e.pub)) continue;\n    const stores = {};",
     "replace": "    const stores = {};",
     "matches": 1, "needs": "node"},
    {"why": "#27 - the shadow drops the other PC's gear (KonyoLock: No gear seen yet)",
     "file": "console_snapshot.py",
     "find": "        g = _el.merge_pcs([base.get(\"gear\"), ans.get(\"gear\")], bars)",
     "replace": "        g = base.get(\"gear\")",
     "matches": 1},
    {"why": "#27 - a PC shares a name that is no label",
     "file": "control_app.py",
     "find": "            if isinstance(shares, str) and shares.strip() in _rpl.OWNERS:",
     "replace": "            if isinstance(shares, str) and shares.strip():",
     "matches": 1},
    {"why": "#27 - the Mac offers no way to add a second PC (only replace)",
     "file": "control_ui.html",
     "find": "           + '\" data-decision=\"add\" onclick=\"window._fleetKeyDecide(this)\" title=\"both PCs keep publishing as '",
     "replace": "           + '\" data-decision=\"approve\" onclick=\"window._fleetKeyDecide(this)\" title=\"both PCs keep publishing as '",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
