# -*- coding: utf-8 -*-
"""v3883 - AN IMPORT KEYS GITHUB'S PROOFS WITHOUT RE-READING THE SAME FILES FOR EVERY KEY, AND NO KEY CHANGES FOR IT.

MEASURED on the work ALT 11-08 ~10:00 IST (an i3, one import worker: 1,684 MB free over a 1,024 MB floor): GitHub's import
of v3882's proofs keyed at 0.55 entries a second - ~4.8 hours for a version's 9,463 - while its locks waited. Profiled there
(cProfile, the keyer over the real cache, read-only): 40% of a key was os.path.relpath (110,150 calls for 43 keys - every
input of every key, again for each of the up-to-8 variants key_for asks when the plain key is new), and the four
version-stamped surfaces (bible.html is 8.9 MB) were read and hashed WHOLE on every key, by _sha_file and _masked_sha, which
always read. Now a key's relative names are memoised (pure: two strings in, one out), and the stamped surfaces are served
within a quiet stretch - REG-2631's rule, the one every other input of a key already keys by: the same file identity (size,
mtime, ctime, inode) and no _prove_one started or ended since it was read.

The law keys real laws of THIS tree (each one's closure holds bible.html) with the memos and with every memo bypassed: the
keys are identical, cold and warm. A second key over unchanged surfaces reads none of them again; a proof starting (the quiet
generation moving) or a surface whose bytes moved reads it again. No live cache is opened: the cache under test has a path
that does not exist. RED_PROOF below. [[regression-guard]] [[unknown-stays-unknown]]
"""
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import heart2 as H  # noqa: E402

LAWS = ("test_every_runeword_row_fits_its_base", "test_the_tabs_stick_below_the_claim_bar",
        "test_a_dropdown_never_opens_white_on_white")
NOWHERE = os.path.join(tempfile.gettempdir(), "no-such-dir-v3883", "cache.json")


def _cache():
    return H._VerdictCache(path=NOWHERE, say=lambda *a, **k: None)


class _Counted(object):
    """counts the whole-file reads of bible.html by both readers a key uses"""

    def __enter__(self):
        self.n = self.masked = 0
        self._sf, self._mr = H._sha_file, H._VerdictCache._masked_sha_read
        me = self

        def sf(path, memo=None):
            if os.path.basename(str(path)) == "bible.html":
                me.n += 1
            return me._sf(path, memo)

        def mr(cache, path, rel):
            if os.path.basename(str(path)) == "bible.html":
                me.n += 1
                me.masked += 1
            return me._mr(cache, path, rel)
        H._sha_file, H._VerdictCache._masked_sha_read = sf, mr
        return self

    def __exit__(self, *a):
        H._sha_file, H._VerdictCache._masked_sha_read = self._sf, self._mr


class AnImportKeysWithoutRereadingTheTree(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.files = dict(H.gate_files(say=lambda *a, **k: None))
        cls.pairs = []
        for g in LAWS:
            fn = cls.files.get(g)
            if not fn:
                continue
            prs = H.red_proofs_in(fn) or []
            for i in range(min(2, len(prs))):
                cls.pairs.append((g, fn, prs[i]))

    def _key(self, c, g, fn, pr):
        return c.key_for(H.HERE, g, fn, pr)[0]

    def test_premise_the_laws_key_a_stamped_surface(self):
        self.assertGreaterEqual(len(self.pairs), 4, "the chosen laws are gone - re-point LAWS: %r" % (self.pairs,))
        c = _cache()
        g, fn, pr = self.pairs[0]
        _k, rels, why = c.key_for(H.HERE, g, fn, pr)
        self.assertIsNone(why)
        self.assertIn("bible.html", rels, "PREMISE: the law's key no longer holds bible.html - re-point LAWS")

    def test_the_memos_never_change_a_key(self):
        """* THE POINT - the same bytes, the same key, served or read"""
        raw = _cache()
        keep = (H._sha_quiet, H._VerdictCache._rel, H._VerdictCache._masked_sha)
        try:
            H._sha_quiet = lambda path, memo: H._sha_file(path)
            H._VerdictCache._rel = lambda self, p, repo: os.path.relpath(p, repo).replace(os.sep, "/")
            H._VerdictCache._masked_sha = lambda self, path, rel: self._masked_sha_read(path, rel)
            want = [self._key(raw, g, fn, pr) for g, fn, pr in self.pairs]
        finally:
            H._sha_quiet, H._VerdictCache._rel, H._VerdictCache._masked_sha = keep
        c = _cache()
        cold = [self._key(c, g, fn, pr) for g, fn, pr in self.pairs]
        warm = [self._key(c, g, fn, pr) for g, fn, pr in self.pairs]
        self.assertTrue(all(want), "PREMISE: every proof keyed: %r" % (want,))
        self.assertEqual(cold, want, "a memo changed a key")
        self.assertEqual(warm, want, "a memo served a key different from the read one")

    def test_keys_after_the_first_read_none_of_the_stamped_surfaces_again(self):
        """the import's case: every entry of a version keyed over the same bytes - each surface read once per form (raw,
        masked), never once per key"""
        c = _cache()
        with _Counted() as n:
            for g, fn, pr in self.pairs:
                self._key(c, g, fn, pr)
            first = n.n
            for _round in range(2):
                for g, fn, pr in self.pairs:
                    self._key(c, g, fn, pr)
            again = n.n - first
        self.assertGreaterEqual(first, 1, "PREMISE: the first keys read bible.html")
        self.assertLessEqual(first, 2, "bible.html read %d times for %d keys - once raw and once masked is the most" % (
            first, len(self.pairs)))
        self.assertEqual(again, 0, "%d more key(s) over the same bible.html read it %d more time(s) - 8.9 MB a key" % (
            2 * len(self.pairs), again))

    def test_a_proof_starting_reads_them_again(self):
        """REG-2631: a tamper may rewrite a file and restore it; a key after a _prove_one boundary never serves the memo"""
        c = _cache()
        with _Counted() as n:
            for g, fn, pr in self.pairs:
                self._key(c, g, fn, pr)
            raw0, m0 = n.n - n.masked, n.masked
            self.assertGreaterEqual(m0, 1, "PREMISE: one of the laws keys bible.html masked - re-point LAWS")
            H._QUIET["gen"] += 1
            for g, fn, pr in self.pairs:
                self._key(c, g, fn, pr)
            self.assertGreaterEqual(n.masked - m0, 1, "a masked key after a proof boundary served bible.html from the memo")
            self.assertGreaterEqual(n.n - n.masked - raw0, 1, "a raw key after a proof boundary served bible.html from the memo")

    def test_a_surface_whose_bytes_moved_is_read_again(self):
        d = tempfile.mkdtemp(prefix="v3883-masked-")
        try:
            p = os.path.join(d, "bible.html")
            shutil.copyfile(os.path.join(os.path.dirname(H.HERE), "bible.html"), p)
            c = _cache()
            one = c._masked_sha(p, "bible.html")
            self.assertIsNotNone(one[0], "PREMISE: bible.html masks (it carries its stamp)")
            with open(p, "ab") as fh:
                fh.write(b"\n<!-- v3883 law: one more line -->\n")
            two = c._masked_sha(p, "bible.html")
            self.assertNotEqual(one[0], two[0], "a surface whose bytes moved was served its old digest")
            self.assertEqual(c._masked_sha(p, "bible.html"), two)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_relative_name_is_relpaths(self):
        c = _cache()
        repo = os.path.dirname(H.HERE)
        for p in (os.path.join(repo, "bible.html"), os.path.join(H.HERE, "heart2.py")):
            self.assertEqual(c._rel(p, repo), os.path.relpath(p, repo).replace(os.sep, "/"))
            self.assertEqual(c._rel(p, H.HERE), os.path.relpath(p, H.HERE).replace(os.sep, "/"),
                             "the memo served one repo's name for another's")


RED_PROOF = [
    {"why": "v3883 - the stamped surfaces are read whole on every key again (bible.html's 8.9 MB, up to 9 keys an entry)",
     "file": "tv/heart2.py",
     "find": "            surf = tuple(_sha_quiet(os.path.join(repo, *r.split(\"/\")), self.memo) for r in sorted(GL._STAMP_REQUIRED))\n",
     "replace": "            surf = tuple(_sha_file(os.path.join(repo, *r.split(\"/\")), self.memo) for r in sorted(GL._STAMP_REQUIRED))\n",
     "matches": 1},
    {"why": "v3883 - the masked digest is read whole on every key again",
     "file": "tv/heart2.py",
     "find": "        if qk is not None:\n            with self.lock:\n                if qk in self.memo:\n                    return self.memo[qk]\n",
     "replace": "", "matches": 1},
    {"why": "v3883 - the masked digest is served across a proof boundary (a tamper's rewrite-and-restore)",
     "file": "tv/heart2.py",
     "find": "st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino, _QUIET[\"gen\"])\n",
     "replace": "st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino)\n", "matches": 1},
    {"why": "v3883 - the masked digest is served after the surface's bytes moved",
     "file": "tv/heart2.py",
     "find": "qk = (\"REG-2602q\", path, rel, st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino,",
     "replace": "qk = (\"REG-2602q\", path, rel,", "matches": 1},
    {"why": "v3883 - the relative-name memo forgets which repo a name is relative to",
     "file": "tv/heart2.py",
     "find": "        k = (p, repo)\n        r = self.rels.get(k)\n",
     "replace": "        k = p\n        r = self.rels.get(k)\n", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
