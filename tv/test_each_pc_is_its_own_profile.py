# -*- coding: utf-8 -*-
"""v3890 (#182) - EACH PC IS ITS OWN PROFILE: SHADOW MODE OF A PC SHOWS WHAT THAT PC'S CONSOLE RENDERS, NEVER ANOTHER'S.

His words, 11-09: "thats not good that its mixed though.. why do they have a shared profile ... i thought they were separated.
each console and whatever it itself is rendering should be showing the through the other side when looking through shadow
mode at that individual profile" - "yea so they need to separate like they were". MEASURED 11-09 (SSH GET on both ALTs and
the Mac's /roster-cache?profile=Konyo · ALT): the work ALT's console had learned 0 characters, the OLD ALT's 26 (KonyoLock,
Konyodin, Konyoress ... and the mules), and the Mac's shadow of Konyo · ALT read "another PC of this label (key a8834dcd53c5)
adds 26 character(s)" - the OLD ALT's, under the work ALT's name. v3880 (REG-3362) had let a second PC join a label's ring
("Add as another PC") and folded it into the label's shadow (console_snapshot.with_others). Now:
  * the OLD ALT is a profile of its own, under the name its Fleet row carries ("OLD PC ALT") - in all three label lists;
  * the site refuses "add", and approving a PC under its own label takes its key out of every other label's ring
    (functions/api/roster.js leaveOtherRings), so the profile it shared stops serving its rows and characters;
  * the shadow never folds another PC into a profile: one the site still serves is NAMED and left out;
  * the Mac's key request offers Approve and Deny - "Approve", not "(replace)", when nothing is replaced.
The ring code stays only so the ring that exists can drain: its security cases stay. Pinned driving the real worker in node
with real Ed25519 keys (roster_sign). RED_PROOF below. TOMBSTONE: tv/test_one_label_holds_two_pcs.py (REG-3362) left with
the sharing it held.
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
OLD = "OLD PC ALT"
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




def _ringed(cls_reg):
    """the site as it stands 11-09: Konyo · ALT holds the work ALT's key, with the OLD ALT in its ring"""
    rec = dict(cls_reg("work_alt"))
    rec["also"] = [dict(cls_reg("old_alt"), at=2, approvedBy="Konyo · Mac")]
    return rec


@unittest.skipUnless(NODE, "node is absent - the worker is UNMEASURED here, never a pass")
class TheSiteKeepsEachPcItsOwnProfile(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="tvd_own_keys_")
        cls.keys = {}
        for n in ("work_alt", "old_alt", "third", "mac"):
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
        cls.seed = {"rosterkey:" + OWNER: _ringed(reg), "rosterkey:" + APPROVER: reg("mac")}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, True)

    def _post(self, body, key, now=T0):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        return {"raw": base64.b64encode(raw).decode("ascii"), "headers": RS.sign_headers(self.keys[key], raw)[0], "now": now}

    def _rows(self, key, name, owner=OWNER, now=T0):
        return self._post({"owner": owner, "boot": True, "sections": {"characters": {
            "asOf": 1000, "counts": 1, "rows": [{"name": name, "cls": "Sorceress", "level": 90}]}}}, key, now)

    def _profile(self, key, answer, owner=OWNER, now=T0):
        stores = {"d2r_owned": "[]", "d2r_api_world": json.dumps(WORLD, separators=(",", ":"), sort_keys=True),
                  "d2r_api_chars_learned": json.dumps(answer, separators=(",", ":"))}
        return self._post({"kind": "profile", "owner": owner, "boot": True, "signedAt": now, "hash": CS.digest(stores),
                           "stores": stores}, key, now)

    def _decide(self, key_name, decision, owner, now):
        return self._post({"kind": "approve", "approver": APPROVER, "owner": owner, "keyId": self.ids[key_name],
                           "decision": decision, "signedAt": now}, "mac", now)

    def test_the_old_alt_publishing_as_itself_leaves_the_profile_it_shared(self):
        """* THE POINT: the OLD ALT's first publish as OLD PC ALT registers that profile (first key wins - no approval to
        press) and takes it out of Konyo · ALT's ring, so Konyo · ALT stops serving its characters"""
        steps = [self._profile("old_alt", OLD_ALT, OWNER, T0),            # as it publishes today, into its slot
                 self._profile("work_alt", WORK_ALT, OWNER, T0 + 1000),
                 {"get": "profile=" + OWNER, "now": T0 + 2000},
                 self._rows("old_alt", "KonyoLock", OLD, T0 + 60000),         # v3890 on the OLD ALT: its own label
                 self._profile("old_alt", OLD_ALT, OLD, T0 + 120000),
                 {"get": "profile=" + OWNER, "now": T0 + 180000},
                 {"get": "profile=" + OLD, "now": T0 + 180000}]
        out = _node({"seed": self.seed, "steps": steps})
        before, first, own, after, its_own = (out["steps"][2]["get"], out["steps"][3]["reply"], out["steps"][4]["reply"],
                                              out["steps"][5]["get"], out["steps"][6]["get"])
        self.assertEqual([o["keyId"] for o in before.get("others") or []], [self.ids["old_alt"]],
                         "PREMISE: the shared profile served the OLD ALT before (else this proves nothing)")
        self.assertTrue(first.get("ok") and first.get("registered"), first)
        self.assertEqual(first.get("leftRings"), [OWNER], first)
        self.assertTrue(own.get("ok"), own)
        self.assertNotIn("others", after, "Konyo · ALT still serves the OLD ALT after it became its own profile")
        held = json.loads(out["store"]["rosterkey:" + OWNER])
        self.assertEqual((held["keyId"], held.get("also")), (self.ids["work_alt"], None), "the work ALT's key moved, or the ring stayed")
        self.assertEqual(json.loads(out["store"]["rosterkey:" + OLD])["keyId"], self.ids["old_alt"])
        self.assertEqual([c["name"] for c in json.loads(its_own["stores"]["d2r_api_chars_learned"])["chars"]],
                         ["KonyoLock", "Konyodin"], "the OLD ALT's own profile does not carry its own characters")

    def test_an_approved_pc_leaves_the_other_rings_too(self):
        """the other door to a label - his Mac approving a key that asked for it - takes it out of every other ring as well"""
        seed = dict(self.seed)
        seed["rosterkey:" + OLD] = self.reg("third")          # a label already held, so the OLD ALT must ask
        out = _node({"seed": seed, "steps": [self._rows("old_alt", "KonyoLock", OLD, T0),
                                              self._decide("old_alt", "approve", OLD, T0 + 60000)]})
        self.assertEqual(out["steps"][0]["reply"].get("approval"), "requested", out["steps"][0]["reply"])
        self.assertTrue(out["steps"][1]["reply"].get("ok"), out["steps"][1]["reply"])
        self.assertIsNone(json.loads(out["store"]["rosterkey:" + OWNER]).get("also"), "an approved PC stayed in another ring")

    def test_add_is_refused_with_its_reason(self):
        out = _node({"seed": self.seed, "steps": [self._rows("third", "X", OWNER, T0), self._decide("third", "add", OWNER, T0 + 60000)]})
        reply = out["steps"][1]["reply"]
        self.assertFalse(reply.get("ok"), "a second PC joined a profile")
        self.assertIn("each PC is its own profile", json.dumps(reply))
        self.assertEqual([e["keyId"] for e in json.loads(out["store"]["rosterkey:" + OWNER]).get("also") or []],
                         [self.ids["old_alt"]], "a refused add changed the ring")

    def test_a_record_not_signed_by_its_ring_key_is_never_served(self):
        """the ring that still exists keeps its guard: a slot whose stored key is not that ring entry's is not the label's"""
        out = _node({"seed": self.seed, "steps": [self._profile("old_alt", OLD_ALT, OWNER, T0),
                                                  self._profile("work_alt", WORK_ALT, OWNER, T0 + 1000)]})
        store = dict(out["store"])
        honest = _node({"seed": store, "steps": [{"get": "profile=" + OWNER, "now": T0 + 2000}]})["steps"][0]["get"]
        self.assertEqual([o["keyId"] for o in honest.get("others") or []], [self.ids["old_alt"]],
                         "premise: the untouched slot is served (else this case proves nothing)")
        slot = "roster:" + OWNER + ":profile@" + self.ids["old_alt"]
        forged = json.loads(store[slot])
        forged["pub"] = RS.b64u(_pub_of(self.keys["third"]))
        store[slot] = forged
        got = _node({"seed": store, "steps": [{"get": "profile=" + OWNER, "now": T0 + 2000}]})["steps"][0]["get"]
        self.assertNotIn("others", got, "a slot record signed by another key was served as the label's PC")

    def test_a_malformed_ring_entry_is_never_trusted(self):
        seed = dict(self.seed)
        bad = dict(self.reg("work_alt"))
        bad["also"] = [{"pub": self.reg("old_alt")["pub"], "keyId": "../../x"}]
        seed["rosterkey:" + OWNER] = bad
        out = _node({"seed": seed, "steps": [self._rows("old_alt", "KonyoLock")]})
        self.assertFalse(out["steps"][0]["reply"].get("ok"), "a ring entry with no 12-hex key id signed for the label")


class TheShadowNeverFoldsAnotherPcIn(unittest.TestCase):

    def test_a_profile_is_its_own_pcs_answer_and_another_pc_is_named(self):
        stores = {"d2r_owned": "[]", "d2r_api_chars_learned": json.dumps(WORK_ALT)}
        rec = {"owner": OWNER, "t": T0, "hash": CS.digest(stores), "stores": stores,
               "others": [{"keyId": "a8834dcd53c5", "t": T0 - 600000,
                           "stores": {"d2r_api_chars_learned": json.dumps(OLD_ALT)}}]}
        out = CS.view(OWNER, rec, T0 + 60000, online=True)
        self.assertEqual(json.loads(out["stores"]["d2r_api_chars_learned"])["chars"], [],
                         "the shadow of the work ALT shows another PC's characters")
        self.assertIn("another PC still shares this profile on the site (key a8834dcd53c5) - not shown here", out["words"])
        self.assertEqual(out.get("others"), [{"keyId": "a8834dcd53c5", "folded": False}])
        self.assertFalse(hasattr(CS, "with_others"), "the fold is back")


class EachPcPublishesAsItself(unittest.TestCase):

    def _claimed(self, ident):
        import control_app as CA
        d = tempfile.mkdtemp(prefix="tvd_own_ident_")
        try:
            p = os.path.join(d, "identity.json")
            with io.open(p, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(ident))
            with mock.patch.object(CA, "IDENTITY_PATH", p):
                return CA._roster_claimed_name()
        finally:
            shutil.rmtree(d, True)

    def test_the_old_alt_publishes_as_its_own_profile(self):
        """its identity still says sharesLabel Konyo · ALT (set 11-08): a name that IS a label is never moved under another"""
        self.assertIn(OLD, CS.OWNERS)
        self.assertEqual(self._claimed({"nickname": "OLD PC ALT", "sharesLabel": OWNER}), OLD)
        self.assertEqual(self._claimed({"nickname": "Dean", "sharesLabel": OWNER}), "Dean")

    def test_his_mac_offers_approve_and_deny_only(self):
        import control_app as CA
        with mock.patch.object(CA, "_roster_my_label", lambda: APPROVER):
            got = CA.roster_approve(OWNER, "a8834dcd53c5", "add", _post=lambda url, body, key: {"ok": True, "sent": body})
        self.assertFalse(got.get("ok"), "the Mac sent an add")
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        i = ui.index("window._fleetKeyReqHtml = function")
        card = ui[i:ui.index("window._fleetKeyReqPaint", i)]
        self.assertNotIn('data-decision="add"', card)
        self.assertNotIn("Add as another PC</button>", card)
        self.assertIn("(q.replaces ? 'Approve (replace)' : 'Approve')", card)


RED_PROOF = [
    {"why": "v3890 (#182) - the site lets a second PC join a profile again",
     "file": "functions/api/roster.js",
     "find": "  if (decision === \"add\") {\n    return refuse(\"roster would not take this approval: each PC is its own profile now - approve it under its own label\");\n  }\n",
     "replace": "",
     "matches": 1},
    {"why": "v3890 (#182) - a PC approved under its own label stays in the ring of the profile it shared",
     "file": "functions/api/roster.js",
     "find": "    await leaveOtherRings(kv, owner, req.keyId);\n",
     "replace": "",
     "matches": 1},
    {"why": "v3890 (#182) - a PC registering its own label stays in the ring of the profile it shared",
     "file": "functions/api/roster.js",
     "find": "      const left = await leaveOtherRings(kv, owner, sig.keyId);\n",
     "replace": "      const left = [];\n",
     "matches": 1},
    {"why": "v3890 (#182) - the shadow folds the other PC's characters into the profile again",
     "file": "tv/console_snapshot.py",
     "find": "        out[\"others\"] = [{\"keyId\": k, \"folded\": False} for k in keys]\n",
     "replace": "        out[\"others\"] = [{\"keyId\": k, \"folded\": False} for k in keys]\n        out[\"stores\"] = dict(out[\"stores\"], d2r_api_chars_learned=(rec[\"others\"][0].get(\"stores\") or {}).get(\"d2r_api_chars_learned\"))\n",
     "matches": 1},
    {"why": "v3890 (#182) - the OLD ALT is no profile of its own: it publishes as Konyo · ALT again",
     "file": "tv/roster_publish.py",
     "find": "    \"OLD PC ALT\",\n)",
     "replace": ")",
     "matches": 1},
    {"why": "v3890 (#182) - the Mac offers to add a second PC to a profile again",
     "file": "tv/control_app.py",
     "find": "    if decision not in (\"approve\", \"deny\") or not isinstance(owner, str) or not isinstance(key_id, str):\n",
     "replace": "    if decision not in (\"approve\", \"add\", \"deny\") or not isinstance(owner, str) or not isinstance(key_id, str):\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
