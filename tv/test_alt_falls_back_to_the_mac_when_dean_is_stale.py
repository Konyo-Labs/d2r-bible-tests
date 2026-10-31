# -*- coding: utf-8 -*-
"""Elad 17:19 — the ALT takes Dean's proof when it is at this HEAD and fresh, else the Mac's.

Dean stays first. Konyo (the Mac) is the backup. A proof older than PROOF_CARRIER_FRESH_S, missing, at another HEAD,
or of UNKNOWN age is not fresh, and the next peer is asked. Both missing or both stale imports nobody: a proof is
never forged. The Mac's roster label is Konyo · Mac; the ALT's list says Konyo. darwin is allowed only for that peer.
Without now_ms the older "import every same-platform peer" loop is unchanged.
"""
import inspect
import os
import sys
import unittest
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import proof_carrier as PC  # noqa: E402

HEAD = "1234567890abcdef1234567890abcdef12345678"
OTHER = "abcdefabcdefabcdefabcdefabcdefabcdefabcd"
NOW = 1_700_000_000_000


def _owners(urls):
    out = []
    for url in urls:
        owner = urllib.parse.unquote(url.split("owner=", 1)[1].split("&", 1)[0])
        out.append(owner)
    return out


class TheAltFallsBackToTheMacWhenDeanIsStale(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import control_app as CA
        cls.CA = CA

    def _drive(self, metas, run_rc=None):
        asked, ran = [], []

        def get(url):
            asked.append(url)
            owner = urllib.parse.unquote(url.split("owner=", 1)[1].split("&", 1)[0])
            meta = metas.get(owner, {"ok": True, "have": False})
            if url.endswith("&body=1"):
                return {"ok": True, "export": {"format": 2, "entries": {}, "export": {"head": meta.get("head")}}}
            return meta

        def run(args, timeout):
            ran.append(list(args))
            who = args[args.index("--carried-by") + 1]
            rc = 0 if run_rc is None else run_rc.get(who, 0)
            if rc == 0:
                return 0, "REG-3045 CARRIED from %s: 2 banked" % who
            return rc, "IMPORT REFUSED"
        peers = self.CA._proof_carrier_peers("Konyo · ALT")
        out = PC.take(peers, HEAD, platform="win32", get=get, run=run, now_ms=NOW)
        return out, asked, ran

    def _meta(self, platform, at, head=HEAD, have=True):
        return {"ok": True, "have": have, "platform": platform, "head": head, "count": 2, "at": at, "keyId": "k"}

    def _fresh(self):
        return NOW - PC.PROOF_CARRIER_FRESH_S * 1000

    def _stale(self):
        return self._fresh() - 1

    def test_the_threshold_is_named_and_a_night_fits_inside_it(self):
        self.assertEqual(PC.PROOF_CARRIER_FRESH_S, 26 * 3600)
        self.assertIn("PROOF_CARRIER_FRESH_S", PC._proof_age_refusal.__code__.co_names)
        self.assertIsNone(PC._proof_age_refusal(self._fresh(), NOW))
        self.assertIn("stale", PC._proof_age_refusal(self._stale(), NOW))
        self.assertIn("UNKNOWN", PC._proof_age_refusal(None, NOW))
        self.assertIn("UNKNOWN", PC._proof_age_refusal("yesterday", NOW))
        self.assertIn("UNKNOWN", PC._proof_age_refusal(NOW + 1, NOW))

    def test_the_alt_asks_dean_then_the_mac(self):
        self.assertEqual(self.CA.PROOF_CARRIER_PLATFORMS, ("win32",))
        self.assertEqual(self.CA._proof_carrier_peers("Konyo · ALT"), ("Dean", "Konyo"))
        self.assertEqual(self.CA._proof_carrier_peers("Konyo"), ())
        self.assertEqual(self.CA._proof_carrier_peers("Konyo · Mac"), ())
        self.assertTrue(self.CA._proof_carrier_source("Konyo · Mac"))

    def test_a_fresh_dean_is_taken_and_the_mac_is_not_asked(self):
        metas = {"Dean": self._meta("win32", self._fresh()),
                 "Konyo · Mac": self._meta("darwin", self._fresh())}
        out, asked, ran = self._drive(metas)
        self.assertEqual([r["owner"] for r in out["imported"]], ["Dean"])
        self.assertEqual(set(_owners(asked)), {"Dean"})
        self.assertEqual(ran[0][ran[0].index("--carried-by") + 1], "Dean")
        self.assertEqual(out["skipped"], [])

    def test_a_stale_or_missing_dean_falls_back_to_the_mac(self):
        mac = self._meta("darwin", self._fresh())
        cases = {
            "stale": self._meta("win32", self._stale()),
            "other head": self._meta("win32", self._fresh(), head=OTHER),
            "missing": self._meta("win32", self._fresh(), have=False),
            "unknown age": {"ok": True, "have": True, "platform": "win32", "head": HEAD, "count": 2, "keyId": "k"},
            "clock ahead": self._meta("win32", NOW + 1),
        }
        for name, dean in cases.items():
            out, asked, ran = self._drive({"Dean": dean, "Konyo · Mac": mac})
            self.assertEqual([r["owner"] for r in out["imported"]], ["Konyo"], name)
            self.assertIn("Konyo · Mac", _owners(asked), name)
            self.assertEqual(ran[-1][ran[-1].index("--carried-by") + 1], "Konyo", name)
            self.assertTrue(any(s["owner"] == "Dean" for s in out["skipped"]), name)

    def test_a_refused_dean_import_falls_through_to_the_mac(self):
        metas = {"Dean": self._meta("win32", self._fresh()),
                 "Konyo · Mac": self._meta("darwin", self._fresh())}
        out, asked, ran = self._drive(metas, run_rc={"Dean": 2})
        self.assertEqual([r["owner"] for r in out["imported"]], ["Konyo"])
        self.assertIn("Konyo · Mac", _owners(asked))
        self.assertTrue(any(s["owner"] == "Dean" for s in out["skipped"]))

    def test_both_fresh_takes_only_dean_and_both_stale_takes_nobody(self):
        mac = self._meta("darwin", self._fresh())
        out, asked, ran = self._drive({"Dean": self._meta("win32", self._fresh()), "Konyo · Mac": mac})
        self.assertEqual([r["owner"] for r in out["imported"]], ["Dean"])
        self.assertNotIn("Konyo · Mac", _owners(asked))
        out, asked, ran = self._drive({"Dean": self._meta("win32", self._stale()),
                                        "Konyo · Mac": self._meta("darwin", self._stale())})
        self.assertEqual(out["imported"], [])
        self.assertEqual(ran, [], "a proof was imported when neither peer was fresh")
        self.assertEqual(sorted(s["owner"] for s in out["skipped"]), ["Dean", "Konyo"])
        out, asked, ran = self._drive({"Dean": self._meta("win32", self._fresh(), have=False),
                                        "Konyo · Mac": self._meta("darwin", self._fresh(), have=False)})
        self.assertEqual(out["imported"], [])
        self.assertEqual(ran, [])

    def test_another_darwin_peer_is_still_refused(self):
        out = PC.take(["Wife PC"], HEAD, platform="win32", now_ms=NOW, get=lambda url: {
            "ok": True, "have": True, "platform": "darwin", "head": HEAD, "count": 1, "at": self._fresh()},
            run=lambda args, timeout: (0, "should not run"))
        self.assertEqual(out["imported"], [])
        self.assertIn("darwin", out["skipped"][0]["why"])

    def test_the_carrier_run_asks_the_age(self):
        src = inspect.getsource(self.CA._proof_carrier_run)
        needle = "_pc.take(peers, head, now_ms=int(time.time() * 1000))"
        self.assertEqual(src.count(needle), 1)


RED_PROOF = [
    {"why": "the ALT's list names only Dean, so a stale Dean has no Mac to fall back to",
     "file": "control_app.py",
     "find": "PROOF_CARRIER_ACCEPTS = {\"Dean\": (\"Konyo · ALT\",), \"Konyo · ALT\": (\"Dean\", \"Konyo\")}\n",
     "replace": "PROOF_CARRIER_ACCEPTS = {\"Dean\": (\"Konyo · ALT\",), \"Konyo · ALT\": (\"Dean\",)}\n",
     "matches": 1},
    {"why": "a stale export is treated as fresh, so the ALT never asks the Mac",
     "file": "proof_carrier.py",
     "find": "            if _age:\n",
     "replace": "            if False and _age:\n",
     "matches": 1},
    {"why": "the Mac's darwin export is skipped like any other platform, so the ALT cannot take it",
     "file": "proof_carrier.py",
     "find": "            if owner != \"Konyo\":\n",
     "replace": "            if True:\n",
     "matches": 1},
    {"why": "a fresh import does not stop the list, so a fresh Dean and a fresh Mac are both taken",
     "file": "proof_carrier.py",
     "find": "        if now_ms is not None and rc == 0:\n",
     "replace": "        if False and now_ms is not None and rc == 0:\n",
     "matches": 1},
    {"why": "the carrier run takes without asking the age, so a stale Dean still stands",
     "file": "control_app.py",
     "find": "            out = _pc.take(peers, head, now_ms=int(time.time() * 1000))\n",
     "replace": "            out = _pc.take(peers, head)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
