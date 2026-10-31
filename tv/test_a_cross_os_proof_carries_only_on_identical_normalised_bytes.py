# -*- coding: utf-8 -*-
"""Elad 17:19 — a proof key digests LF-normalised text on both sides.

The ALT checks text out with core.autocrlf=true (CRLF). The Mac leaves autocrlf unset (LF). Those are one commit, so
both hashers (the raw file and the stamp-masked file) digest the same LF bytes. A NUL means the file is not text git
converts: its bytes stay as stored, and a lone CR still differs. An entry whose key this checkout's bytes refuse is
dropped and never marked carried, including when the export was proved on darwin and imported on win32.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from unittest import mock

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
import heart2  # noqa: E402
import proof_shard  # noqa: E402

HEAD = "1234567890abcdef1234567890abcdef12345678"
HERE_RT = {"platform": "win32", "python": "3.12", "node": "22"}
MAC_RT = {"platform": "darwin", "python": "3.12", "node": "22"}
LF = b"def f():\n    return 1\n"
CRLF = LF.replace(b"\n", b"\r\n")
OTHER = b"def f():\n    return 2\n"
LONE = b"def f():\ra\n    return 1\n"
BIN_CRLF = b"a\r\n\x00b"
BIN_LF = b"a\n\x00b"


def _e(gate, proof):
    return {"verdict": "PROVEN", "gate": gate, "proof": proof, "why": "w", "tree": "/mac/repo",
            "provedAt": 1761200000000}


class TheKeyDigestsLfNormalisedBytes(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="lf-norm-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _file(self, name, data):
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    def _masked(self, path):
        cache = heart2._VerdictCache.__new__(heart2._VerdictCache)
        cache.lock = threading.Lock()
        cache.memo = {}
        return heart2._VerdictCache._masked_sha(cache, path, "tv/lf_norm_probe.py")[0]

    def test_crlf_text_matches_lf_text_and_a_real_byte_does_not(self):
        self.assertEqual(heart2.lf_normalised_bytes(CRLF), LF)
        self.assertEqual(heart2.lf_normalised_bytes(LF), LF)
        self.assertNotEqual(heart2.lf_normalised_bytes(LONE), LF)
        self.assertEqual(heart2.lf_normalised_bytes(BIN_CRLF), BIN_CRLF)
        self.assertNotEqual(heart2.lf_normalised_bytes(BIN_CRLF), BIN_LF)
        crlf, lf, other = self._file("crlf.py", CRLF), self._file("lf.py", LF), self._file("other.py", OTHER)
        lone, bcr, blf = self._file("lone.py", LONE), self._file("bcr.bin", BIN_CRLF), self._file("blf.bin", BIN_LF)
        self.assertEqual(heart2._sha_file(crlf), heart2._sha_file(lf))
        self.assertNotEqual(heart2._sha_file(lf), heart2._sha_file(other))
        self.assertNotEqual(heart2._sha_file(lone), heart2._sha_file(lf))
        self.assertNotEqual(heart2._sha_file(bcr), heart2._sha_file(blf))
        self.assertEqual(self._masked(crlf), self._masked(lf))
        self.assertNotEqual(self._masked(lf), self._masked(other))
        self.assertNotEqual(self._masked(bcr), self._masked(blf))
        self.assertIn("lf_normalised_bytes", heart2._sha_file.__code__.co_names)
        self.assertIn("lf_normalised_bytes", heart2._VerdictCache._masked_sha.__code__.co_names)


class ADarwinExportBanksOnlyTheMatchingEntry(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="xos-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.target = os.path.join(self.tmp, "home", os.path.basename(heart2.CACHE))
        os.makedirs(os.path.dirname(self.target))
        self.said, self.keys = [], {}
        for name, kw in (("_git", {"side_effect": lambda *a: (True, HEAD + "\n") if a[0] == "rev-parse" else (True, "")}),
                         ("_shard_keyer", {"return_value": lambda g, i: self.keys.get((g, i))}),
                         ("_shard_decls", {"return_value": lambda g, i: None}),
                         ("export_runtime", {"return_value": dict(HERE_RT)})):
            p = mock.patch.object(heart2, name, **kw)
            p.start()
            self.addCleanup(p.stop)

    def test_a_darwin_export_banks_the_matching_entry_and_never_marks_the_refused_one(self):
        self.keys[("g_same", 0)] = "k-same"
        self.keys[("g_diff", 0)] = "k-here"
        d = os.path.join(self.tmp, "mac")
        os.makedirs(d)
        path = os.path.join(d, os.path.basename(heart2.CACHE))
        entries = {"k-same": _e("g_same", 0), "k-filed": _e("g_diff", 0)}
        man = proof_shard.export_manifest(HEAD, False, len(entries), 1761200000000, runtime=MAC_RT)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"format": 2, "entries": entries, "export": man}))
        rc = heart2.import_proved([path], say=self.said.append, target=self.target,
                                  carried={"by": "Konyo", "key": "k-mac"}, platform="win32")
        self.assertEqual(rc, 0, self.said)
        with io.open(self.target, encoding="utf-8") as fh:
            home = (json.load(fh) or {}).get("entries") or {}
        self.assertEqual(set(home), {"k-same"})
        carried = home["k-same"].get("carried") or {}
        self.assertEqual((carried.get("by"), carried.get("platform"), carried.get("key")), ("Konyo", "darwin", "k-mac"))
        self.assertNotIn("g_diff", json.dumps(home))
        text = " ".join(self.said)
        self.assertIn("DROPPED", text)
        self.assertIn("g_diff", text)


RED_PROOF = [
    {"why": "CRLF text is hashed as stored, so a Mac LF proof and an ALT CRLF proof of one commit do not meet",
     "file": "heart2.py",
     "find": "    return data.replace(b\"\\r\\n\", b\"\\n\")\n",
     "replace": "    return data\n",
     "matches": 1},
    {"why": "a binary that contains CRLF is rewritten, so a NUL file forges the key of its LF twin",
     "file": "heart2.py",
     "find": "or b\"\\0\" in data or b\"\\r\\n\" not in data:",
     "replace": "or b\"\\r\\n\" not in data:",
     "matches": 1},
    {"why": "the raw file hasher skips LF normalisation, so the two checkouts key one text differently",
     "file": "heart2.py",
     "find": "        return None\n    data = lf_normalised_bytes(data)\n",
     "replace": "        return None\n    data = data\n",
     "matches": 1},
    {"why": "the stamp-masked hasher skips LF normalisation, so a masked proof still diverges on CRLF",
     "file": "heart2.py",
     "find": "            return None, None\n        data = lf_normalised_bytes(data)\n",
     "replace": "            return None, None\n        data = data\n",
     "matches": 1},
    {"why": "an entry this checkout's bytes refuse is banked and marked carried",
     "file": "proof_shard.py",
     "find": "            if keyer is not None and keyer(str(e.get(\"gate\")), e.get(\"proof\")) != key:\n",
     "replace": "            if False and keyer is not None and keyer(str(e.get(\"gate\")), e.get(\"proof\")) != key:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
