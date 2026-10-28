#!/usr/bin/env python3
"""THE GUEST SEAT IS GROK, NOT KONYO — and the mirror carries none of his machine.

HIS BRIEF, 2026-09-15 (GB-CLAUDE-GROK-PROFILE-SYNC): a real Grok actor for the guest seat on the
box, *"rewrite so Konyo is never the live actor"*, and *"No install ids, hostnames, tokens, or
home paths in replies"* — because this repo is PUBLIC and the guest's evidence screenshots get
posted to a public issue.

⚠ WHY THIS IS A PRIVACY GATE AND NOT A COSMETIC ONE. The guest renders a mirror of his live
console. His `/api/status` carries an install id, a `.local` hostname, a unix user and absolute
home paths; the board HTML carries them too. MEASURED on the very first sync run: the raw board
came back with FOUR of his identifiers still in it, and the leak gate refused the copy. Without
that refusal they would have gone to the box, into the fixture packs built from it, and into any
screenshot posted to #180.

⚠ AND FAIL CLOSED. His brief: *"fail closed on unreadable stores (no false HOLDS / empty wipe)"*.
An endpoint that does not answer must leave an explicit `unreadable` record. On the guest an
empty vault and an unread vault look identical, and only one of them means he owns nothing —
which is exactly what his screenshot showed before the mirror existed: every locker reading
"0 · empty locker" because there was no mirror at all. [[zero-needs-a-denominator]]
"""
import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

import guest_profile as gp

# A stand-in for his machine. Deliberately NOT his real values — a law that hard-codes the very
# identifiers it protects would be the leak it exists to prevent.
FAKE_LIVE = {
    "id": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
    "computer": "someone-2.local",
    "user": "someone",
    "platform": "mac",
    "nickname": "Konyo",
}


class TheGuestSeatIsGrokNotKonyo(unittest.TestCase):

    def test_the_actor_is_grok_on_grok_bot(self):
        p = gp.profile()
        print("   profile: %s" % json.dumps(p))
        self.assertEqual(p["nickname"], "Grok")
        self.assertEqual(p["computer"], "grok-bot")
        self.assertIs(p["guest"], True, "the box doctor asserts guest:true")

    def test_the_id_is_stable_across_runs(self):
        """A per-run id would mint a fresh empty world on every look, and the seat would report
        an empty SHELF forever."""
        a, b = gp.profile()["id"], gp.profile()["id"]
        print("   id stable: %s" % (a == b))
        self.assertEqual(a, b)
        self.assertTrue(len(a) >= 16, "an identity the board keys stores by cannot be a stub")

    def test_status_reports_grok_and_keeps_nothing_of_his(self):
        payload = {
            "identity": dict(FAKE_LIVE),
            "ver": "v3185",
            "reelPath": "/Users/someone/d2r/reels",
            "note": "Konyo owns this board",
            "nested": [{"someone-2.local": {"home": "/Users/someone"}}],
        }
        out = gp.rewrite_status(payload, FAKE_LIVE)
        print("   identity after: %s" % json.dumps(out["identity"]))
        self.assertEqual(out["identity"]["nickname"], "Grok")
        self.assertIs(out["guest"], True)
        leaked = gp.leaks(out, FAKE_LIVE)
        print("   leaks remaining: %r" % (leaked,))
        self.assertEqual(leaked, [],
                         "the mirror still carries his machine's identifiers: %r" % (leaked,))
        # ⚠⚠ AND A LITERAL CHECK, BECAUSE leaks() CANNOT SEE A SECRET IT FORGOT. The detector and
        # the scrub read the SAME pair list, so deleting a pair blinds both at once and the
        # assertion above goes green over a mirror that still says his name. Proven: a sabotage
        # removing the Konyo pair passed the leaks() check and was caught only here. A detector
        # must not be its own witness. [[feedback-blind-fixture-green-gate]]
        blob = json.dumps(out, ensure_ascii=False)
        for literal in ("Konyo", "someone-2", "/Users/someone"):
            self.assertNotIn(literal, blob,
                             "%r survived the scrub into the guest mirror" % literal)

    def test_the_scrub_reaches_dict_KEYS_not_only_values(self):
        """Per-session dumps are KEYED by path. A scrub that walked only values would leave the
        keys intact and leak the whole home directory one filename at a time."""
        obj = {"/Users/someone/reels/r1": {"ok": True}}
        out = gp.scrub(obj, FAKE_LIVE)
        print("   keys after: %r" % (list(out),))
        self.assertEqual(gp.leaks(out, FAKE_LIVE), [],
                         "a dict KEY carried his home path through the scrub")

    def test_the_identity_is_replaced_not_merged(self):
        """A merge keeps any key of his the scrub did not know about."""
        payload = {"identity": dict(FAKE_LIVE, secretField="someone-2.local")}
        out = gp.rewrite_status(payload, FAKE_LIVE)
        self.assertNotIn("secretField", out["identity"],
                         "the identity was patched rather than replaced, so an unknown key of "
                         "his survived into the guest")

    def test_an_unreadable_store_is_never_an_empty_one(self):
        u = gp.unreadable("api/vault_ledger", "the live console did not answer")
        print("   unreadable record: %s" % json.dumps(u))
        self.assertTrue(gp.is_unreadable(u))
        self.assertIs(u["ok"], False)
        self.assertTrue(u.get("why"), "an unreadable store that cannot say why is a silent zero")
        self.assertNotEqual(u, {}, "an unread vault must not be shaped like an empty one")

    def test_the_leak_detector_can_actually_find_a_leak(self):
        """⚠ A detector that never fires is indistinguishable from a clean tree. This proves the
        gate itself works before any clean result from it is believed.
        [[feedback-blind-fixture-green-gate]]"""
        dirty = {"path": "/Users/someone/d2r", "host": "someone-2.local"}
        found = gp.leaks(dirty, FAKE_LIVE)
        print("   leaks found in a deliberately dirty object: %r" % (found,))
        self.assertTrue(found, "the leak detector reported clean on an object that is not")

    def test_the_sync_script_ships_no_mutating_endpoint(self):
        """His brief puts 'mutating vault possession from guest smokes' out of scope. A mirror
        that carried a write door would let an eyes-loop change what he owns."""
        p = os.path.join(HERE, "sync_guest_api.sh")
        self.assertTrue(os.path.exists(p), "the one command does not exist")
        src = io.open(p, encoding="utf-8").read()
        i = src.find("READ_ONLY=(")
        j = src.find(")", i)
        self.assertGreater(i, 0, "the allowlist is gone")
        allow = src[i:j]
        banned = ["board_tick", "chronicle_apply", "vault_apply", "vault_forget",
                  "session/delete", "relaunch", "restart", "quit", "api/update", "api/off",
                  "api/on", "api/stop"]
        hit = [b for b in banned if b in allow]
        print("   mutating endpoints inside the allowlist: %r" % (hit,))
        self.assertEqual(hit, [],
                         "the guest mirror would carry a write door: %r" % (hit,))

RED_PROOF = [
    {"why": "the guest seat reports as Konyo, so the live actor on the box is him again",
     "file": "tv/guest_profile.py",
     "find": "        \"nickname\": GROK_NICKNAME,\n",
     "replace": "        \"nickname\": \"Konyo\",\n",
     "matches": 1},
    {"why": "a per-run id mints a fresh empty world on every look, and the seat reads an empty SHELF forever",
     "file": "tv/guest_profile.py",
     "find": "        \"id\": GROK_ID,\n",
     "replace": "        \"id\": os.urandom(16).hex(),\n",
     "matches": 1},
    {"why": "the scrub walks values only, so a dump keyed by his home path leaks it one filename at a time",
     "file": "tv/guest_profile.py",
     "find": "        return dict((scrub(k, None, pairs), scrub(v, None, pairs)) for k, v in obj.items())\n",
     "replace": "        return dict((k, scrub(v, None, pairs)) for k, v in obj.items())\n",
     "matches": 1},
    {"why": "the identity is merged rather than replaced, so a key of his the scrub did not know survives",
     "file": "tv/guest_profile.py",
     "find": "        out[\"identity\"] = profile()\n",
     "replace": "        out[\"identity\"] = dict(out.get(\"identity\") or {}, **profile())\n",
     "matches": 1},
    {"why": "an unreadable store is shaped like an empty one, so an unread vault reads as owning nothing",
     "file": "tv/guest_profile.py",
     "find": "    return {\"ok\": False, \"guest\": True, \"unreadable\": True, \"what\": what, \"why\": str(why)[:300]}\n",
     "replace": "    return {}\n",
     "matches": 1},
    {"why": "the leak detector only fires on an exact whole-blob match, so it reports clean on a dirty object",
     "file": "tv/guest_profile.py",
     "find": "        if old and old in blob:\n",
     "replace": "        if old and old == blob:\n",
     "matches": 1},
    {"why": "his unix user is not among the secrets, so his home path rides into the guest mirror",
     "file": "tv/guest_profile.py",
     "find": "    for key, repl in ((\"id\", GROK_ID), (\"computer\", GROK_COMPUTER), (\"user\", GROK_USER)):\n",
     "replace": "    for key, repl in ((\"id\", GROK_ID), (\"computer\", GROK_COMPUTER)):\n",
     "matches": 1},
    {"why": "his name is not rewritten, so prose saying Konyo owns the board reaches the public guest mirror",
     "file": "tv/guest_profile.py",
     "find": "    out.append((\"Konyo\", GROK_NICKNAME))\n",
     "replace": "    pass\n",
     "matches": 1},
    {"why": "the guest mirror's allowlist carries a write door into his vault",
     "file": "tv/sync_guest_api.sh",
     "find": "\"api/vault_ledger\" \"api/vault_sweep\" \"api/tallies\" \"api/board_tally\"",
     "replace": "\"api/vault_ledger\" \"api/vault_apply\" \"api/vault_sweep\" \"api/tallies\" \"api/board_tally\"",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
