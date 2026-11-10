# -*- coding: utf-8 -*-
"""REG-2944 (REG-2296 for the PROOF cache) - A LAW THAT LISTS A DIRECTORY IS KEYED BY WHAT ITS TRACED RUN LISTED.

tv/unkeyable_laws.json held 63 laws whose proofs could never be saved, most of them censuses whose denominator IS a tree
folder (every tv/*.py, every law, every spec, every workflow): heart2's static walk refused any law file that calls
os.listdir / os.walk / glob, because what it reads is decided at run time. gate_ledger already keys a gate's PASS by what
its traced run listed (REG-2296); this pins the same move for a PROOF.

THE KEY. The REG-2640 trace records every directory a run LISTS, by full path (never the import system's own listings of
sys.path). A listing law's PROVEN is banked under a v3 key: its v1/v2 material plus, for each directory any traced run of
it listed, the sorted names that directory holds and each file's bytes. Before a run nothing says what it will list, so
its pre-run key is a PENDING key no entry is ever stored under; a listing law with no complete in-tree trace runs every
push, exactly as before.

WHAT IT CAN NEVER DO: serve a proof for a tree whose listing differs. A file added, removed or changed in a directory the
law listed - tracked, or untracked and not ignored - is a new key. Nothing else is: a file elsewhere that the law neither
names nor lists leaves the key alone.

THE FLOORS, each a decision and pinned here:
  · GITIGNORED entries of a listed directory are not key material (#242: runtime data is never a key input). The proving
    sandbox DOES carry gitignored files - safe_copy copies everything outside its HEAVY dirs (measured on his tree: 151
    gitignored files in tv/, 87 of them .json) - so a gitignored newcomer does not re-key, and to keep runtime CONTENT
    out of every banked verdict, a run that read or stat'ed a gitignored entry of a directory it listed is never banked.
  · A listing OUTSIDE the tree (his home, /proc, the shared temp dir) is never banked; a listing inside the run's own
    fixture_tmp scratch adds nothing (the code that made it is keyed).
  · THE CLOSURE-LISTING FLOOR: a law that lists only through a module it imports keeps its v1/v2 key byte for byte.
    Keying those would re-key nearly every heart law on any tv/ change.

Driven through the REAL _VerdictCache / _final_key / trace reader against a real directory; the trace of a law run is
recorded through heart2's own _trace_record, and one case runs the REAL trace hook in a child python.
[[the-unjoined-end]] [[regression-guard]] RED_PROOF below.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import heart2 as H  # noqa: E402

GATE = "no-such-registered-gate"
LISTS = ("import os\nHERE = os.path.dirname(os.path.abspath(__file__))\n"
         "names = sorted(os.listdir(HERE))\nprint(len(names))\n")
QUIET = "import os\nHERE = os.path.dirname(os.path.abspath(__file__))\nprint(HERE)\n"


class _Repo(object):
    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="h2ls.")
        self.repo = os.path.join(self.root, "repo")
        self.tv = os.path.join(self.repo, "tv")
        os.makedirs(self.tv)
        os.makedirs(os.path.join(self.repo, "docs"))
        self.tracked = set()

    def put(self, rel, text, tracked=True):
        p = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        if tracked:
            self.tracked.add(rel)


class ALawThatListsIsKeyedByWhatItListed(unittest.TestCase):

    def setUp(self):
        self.r = _Repo()
        self.addCleanup(shutil.rmtree, self.r.root, True)
        self.r.put("tv/subject.py", "OK = 1\n")
        self.r.put("tv/other_law.py", "X = 1\n")
        self.r.put("docs/notes.md", "notes\n")
        self.law = "t_lists_%s.py" % self._testMethodName[-24:]
        self.r.put("tv/" + self.law, LISTS)
        self.pr = {"file": "subject.py", "find": "OK = 1", "replace": "OK = 0", "matches": 1, "why": "w"}
        self.kept = set()
        with H._TRACE_LOCK:
            H._TRACES.pop(self.law, None)
        self.addCleanup(lambda: H._TRACES.pop(self.law, None))

    def _cache(self):
        c = H._VerdictCache(path=os.path.join(self.r.root, ".heart2_cache.json"), say=lambda *a, **k: None)
        c.tracked, c.kept = frozenset(self.r.tracked), frozenset(self.kept)   # git asked of THIS fixture tree
        return c

    def _traced(self, listed=None, names=(), ok=True):
        H._trace_record(self.law, set(names), ok, listed={os.path.realpath(self.r.tv)} if listed is None else listed)

    def _bank(self, cache):
        """The bank a push does after a PROVEN: the pending key taken again, then the deferred (v3) key. -> key | None"""
        pk, rels, why = cache.key_for(self.r.tv, GATE, self.law, self.pr)
        self.assertIsNotNone(pk, why)
        entry = {"verdict": H.PROVEN, "gate": GATE, "proof": 0, "provedAt": int(time.time() * 1000), "inputs": rels}
        k = H._final_key(cache, self.r.tv, GATE, self.law, self.pr, pk, entry)()
        if k is not None:
            cache.store(k, entry)
            cache.flush()                               # the next push opens the cache from DISK
        return k

    def _served(self, cache):
        k, _r, _w = cache.key_for(self.r.tv, GATE, self.law, self.pr)
        return k is not None and cache.peek(k) is not None

    # ── 1. a planted new file in a listed dir re-keys - and so does every other change to what it holds ──────────────
    def test_the_pre_run_key_is_pending_and_never_served(self):
        c = self._cache()
        pk = c.key_for(self.r.tv, GATE, self.law, self.pr)[0]
        self.assertTrue(str(pk).startswith("pending-listing:"), "a listing law has a servable key before any run: %r" % pk)
        self.assertIsNone(c.peek(pk))

    def test_a_complete_trace_banks_it_and_an_identical_tree_serves_it(self):
        self._traced()
        c = self._cache()
        k = self._bank(c)
        self.assertIsNotNone(k, "a listing law with a complete in-tree trace was not banked: %r" % c.traced)
        self.assertFalse(str(k).startswith("pending-listing:"), "the PENDING key was banked")
        self.assertTrue(self._served(c), "an identical tree did not serve the PROVEN its listing law banked")

    def test_a_planted_new_file_in_the_listed_dir_re_keys(self):
        self._traced()
        c = self._cache()
        self._bank(c)
        self.r.put("tv/new_law.py", "Y = 1\n")
        self.assertFalse(self._served(self._cache()), "a file joined the directory the law listed and the old PROVEN "
                                                       "was served")

    def test_a_removed_file_a_changed_byte_and_a_kept_newcomer_each_re_key(self):
        self._traced()
        self._bank(self._cache())
        os.remove(os.path.join(self.r.tv, "other_law.py"))
        self.r.tracked.discard("tv/other_law.py")
        self.assertFalse(self._served(self._cache()), "a file left the listed directory and the old PROVEN was served")
        self.r.put("tv/other_law.py", "X = 1\n")
        self.assertTrue(self._served(self._cache()), "PREMISE: the tree put back did not serve again")
        self.r.put("tv/other_law.py", "X = 2\n")
        self.assertFalse(self._served(self._cache()), "a byte changed in a listed file and the old PROVEN was served")
        self.r.put("tv/other_law.py", "X = 1\n")
        self.r.put("tv/brand_new.py", "Z = 1\n", tracked=False)
        self.kept.add("tv/brand_new.py")                 # untracked, NOT ignored: a law not yet added
        self.assertFalse(self._served(self._cache()), "an untracked, unignored newcomer joined the listed directory "
                                                       "and the old PROVEN was served")

    # ── 2. an unrelated file elsewhere does not; a gitignored newcomer does not (the #242 floor, pinned) ───────────
    def test_an_unrelated_file_elsewhere_does_not_re_key(self):
        self._traced()
        self._bank(self._cache())
        self.r.put("docs/more_notes.md", "more\n")
        self.assertTrue(self._served(self._cache()), "a file the law neither names nor lists re-keyed it")

    def test_a_gitignored_newcomer_does_not_re_key_and_a_run_that_read_one_is_never_banked(self):
        """THE #242 FLOOR, a decision: the proving sandbox carries gitignored files (safe_copy copies all but its HEAVY
        dirs), and runtime data is never key material. So its presence does not re-key - and a run that READ one never
        stands under a key at all."""
        self._traced()
        self._bank(self._cache())
        self.r.put("tv/.live_store.json", "{}", tracked=False)        # neither tracked nor kept: gitignored
        self.assertTrue(self._served(self._cache()), "a gitignored runtime file re-keyed a listing law")
        H._TRACES.pop(self.law, None)
        self._traced(names={".live_store.json"})
        c = self._cache()
        self.assertIsNone(self._bank(c), "a run that read a gitignored file in a directory it listed was banked")
        self.assertIn("gitignored", " ".join(c.traced["why"]), c.traced)

    def test_a_banked_entry_says_how_many_gitignored_names_its_listed_dirs_held(self):
        """REG-2981 - the floor is a number we can audit, never a hope: each listing law's entry records ignoredSeen."""
        self.r.put("tv/.live_a.json", "{}", tracked=False)
        self.r.put("tv/.live_b.json", "{}", tracked=False)
        self._traced()
        c = self._cache()
        k = self._bank(c)
        self.assertIsNotNone(k)
        self.assertEqual(c.entries[k].get("ignoredSeen"), 2, "the entry does not count the gitignored names its listed "
                                                             "dirs held: %r" % c.entries[k])

    # ── 3. a key never matches across a listing change (through the real lookup) ────────────────────────────────────
    def test_no_key_matches_across_a_listing_change(self):
        self._traced()
        c = self._cache()
        k1 = self._bank(c)
        self.r.put("tv/joiner.py", "J = 1\n")
        c2 = self._cache()
        k2 = c2.key_for(self.r.tv, GATE, self.law, self.pr, unread=[], listed=["tv"])[0]
        self.assertNotEqual(k1, k2, "two different listings produced one key")
        self.assertFalse(self._served(c2))

    # ── 4. a listing outside the tree is never banked; the run's own scratch is ─────────────────────────────────────
    def test_a_listing_outside_the_tree_is_never_banked(self):
        self._traced(listed={os.path.realpath(self.r.tv), os.path.realpath(os.path.expanduser("~"))})
        c = self._cache()
        self.assertIsNone(self._bank(c), "a law that listed a directory outside the tree was banked")
        self.assertIn("outside the tree", " ".join(c.traced["why"]), c.traced)

    def test_a_listing_of_its_own_contained_scratch_adds_nothing_and_banks(self):
        own = tempfile.mkdtemp(prefix="own-")         # inside this process's fixture_tmp parent (d2r-test-<pid>-...)
        self.assertTrue(H._OWN_SCRATCH_RX.match(os.path.basename(os.path.dirname(os.path.realpath(own)))),
                        "PREMISE: the scratch is not a contained fixture_tmp parent")
        self._traced(listed={os.path.realpath(self.r.tv), os.path.realpath(own)})
        self.assertIsNotNone(self._bank(self._cache()), "a listing of the run's own scratch kept the law from banking")

    # ── 5. an incomplete trace banks nothing ────────────────────────────────────────────────────────────────────────
    def test_an_incomplete_trace_banks_nothing(self):
        self._traced(ok=False)
        c = self._cache()
        self.assertIsNone(self._bank(c), "a listing law whose trace was incomplete was banked")
        self.assertEqual(c.traced["refused"], 1)

    # ── the push RECORD counts what the trace keyed and why the rest were not (REG-2983) ─────────────────────────────
    def test_the_push_record_counts_banked_and_refused_listing_laws(self):
        c = self._cache()
        self._traced()
        self.assertIsNotNone(self._bank(c))
        H._TRACES.pop(self.law, None)
        self._traced(ok=False)
        self.assertIsNone(self._bank(c))
        rec = H._push_record(H._PushRun(order={}, browser=(), cache=c), [], c, 0, {})
        self.assertIn("tracedListing", rec, "the push record says nothing of the listing laws it keyed or refused")
        tl = rec["tracedListing"]
        self.assertEqual((tl["banked"], tl["refused"]), (1, 1), tl)
        self.assertIn("no complete trace of it", " ".join(tl["why"]), tl)

    # ── 6. a law that does not list keeps its key byte for byte (migration) ─────────────────────────────────────────
    def test_a_law_that_does_not_list_keeps_its_v1_key(self):
        self.r.put("tv/" + self.law, QUIET)
        c = self._cache()
        k = c.key_for(self.r.tv, GATE, self.law, self.pr)[0]
        self.assertFalse(str(k).startswith("pending-listing:"), "a law that lists nothing was given a pending key")
        self.assertEqual(k, c._key(self.r.tv, GATE, self.law, self.pr, (), ("tv",))[0],
                         "listing material reached the key of a law that lists nothing")
        self.r.put("tv/new_law.py", "Y = 1\n")
        self.assertEqual(k, self._cache().key_for(self.r.tv, GATE, self.law, self.pr)[0],
                         "a file joining tv/ moved the key of a law that does not list it - every heart law would re-key")


@unittest.skipUnless(os.name == "posix", "the REG-2640 trace runs only on POSIX - declared, never a pass")
class TheTraceRecordsWhatALawListed(unittest.TestCase):
    """The REAL trace hook, in a child python: a listing and a glob are recorded by full path; the import system's own
    listing of a sys.path directory is not."""

    def test_the_hook_records_a_listing_and_a_glob_and_not_an_import(self):
        d = tempfile.mkdtemp(prefix="h2trace-law-")
        self.addCleanup(shutil.rmtree, d, True)
        listed, globbed, mods = (os.path.join(d, x) for x in ("listed", "globbed", "mods"))
        for x in (listed, globbed, mods):
            os.makedirs(x)
        with io.open(os.path.join(mods, "only_imported_mod.py"), "w", encoding="utf-8") as fh:
            fh.write("X = 1\n")
        site = H._trace_site()
        self.assertIsNotNone(site, "PREMISE: the trace sitecustomize could not be written")
        fd, log = tempfile.mkstemp(prefix="h2trace-", suffix=".log", dir=site)
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(log) and os.unlink(log))
        child = ("import os, glob, sys\nsys.path.insert(0, %r)\nimport only_imported_mod\n"
                 "os.listdir(%r)\nglob.glob(os.path.join(%r, '*.txt'))\n" % (mods, listed, globbed))
        env = dict(os.environ, PYTHONPATH=site, HEART2_TRACE_LOG=log, HEART2_TRACE_SITE=site)
        r = subprocess.run([sys.executable, "-c", child], env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        got = set()
        _seen, ok = H._trace_read(log, os.getpid(), listed=got)
        self.assertTrue(ok, "PREMISE: the child's trace was not complete")
        self.assertIn(os.path.realpath(listed), got, "an os.listdir was not recorded: %r" % sorted(got))
        self.assertIn(os.path.realpath(globbed), got, "a glob was not recorded: %r" % sorted(got))
        self.assertNotIn(os.path.realpath(mods), got, "the import system's own listing was recorded as the law's")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "REG-2944 - the listing material leaves the v3 key: a file joining a listed directory is served the old PROVEN",
     "file": "heart2.py",
     "find": "            h.update(b\"REG-2944 listed\\0\" + lmat + b\"\\0\")\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "REG-2944 - the PENDING key is banked: a listing law is served before anything says what it listed",
     "file": "heart2.py",
     "find": "        if (isinstance(key, str) and key.startswith(\"pending-listing:\")) or cache.lists(sandbox, filename):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-2944 - an untracked, unignored newcomer (a law not yet added) is left out of a listed directory's key",
     "file": "heart2.py",
     "find": "        if rel in self.tracked or rel in self.kept:\n",
     "replace": "        if rel in self.tracked:\n",
     "matches": 1},
    {"why": "REG-2944 - a run that read a gitignored file in a directory it listed is banked: runtime content stands "
            "under a key",
     "file": "heart2.py",
     "find": "            hit = sorted(set(got) & names)\n",
     "replace": "            hit = []\n",
     "matches": 1},
    {"why": "REG-2944 - a listing outside the tree is banked: his home or the shared temp dir is read and never keyed",
     "file": "heart2.py",
     "find": "        return None, \"it listed a directory outside the tree (%s)\" % os.path.basename(d)\n",
     "replace": "        continue\n",
     "matches": 1},
    {"why": "REG-2944 - an incomplete trace banks a listing law",
     "file": "heart2.py",
     "find": "        if t is None or not t[\"ok\"] or t[\"runs\"] < 1:\n            return None, \"no complete trace of it\"\n",
     "replace": "        if t is None:\n            return None, \"no complete trace of it\"\n",
     "matches": 1},
    {"why": "REG-2944 - the closure-listing floor breaks: every law is keyed as if it listed, so a law that lists "
            "nothing loses its v1 key (and every heart law would re-key on any tv/ change)",
     "file": "heart2.py",
     "find": "        lists = self.lists(sandbox, filename)\n        if not lists:\n",
     "replace": "        lists = True\n        if not lists:\n",
     "matches": 1},
    {"why": "REG-2944 - the trace records no listing: a listing law can never be keyed",
     "file": "heart2.py",
     "find": "        elif ev in (\"os.listdir\", \"os.scandir\"):\n            if not by_importer():\n",
     "replace": "        elif ev in ():\n            if not by_importer():\n",
     "matches": 1,
     "needs": "posix"},
    {"why": "REG-2944 - the import system's own listing of sys.path is recorded as the law's",
     "file": "heart2.py",
     "find": "            if c.startswith(\"<frozen importlib\") or c.endswith((\"importlib/_bootstrap_external.py\", \"pkgutil.py\",\n",
     "replace": "            if False and c.endswith((\"importlib/_bootstrap_external.py\", \"pkgutil.py\",\n",
     "matches": 1,
     "needs": "posix"},
    {"why": "REG-2983 - the push record says nothing of the listing laws its trace keyed or refused",
     "file": "heart2.py",
     "find": "        \"tracedListing\": (None if cache is None else           # REG-2944 - listing laws: banked under v3, or why not\n",
     "replace": "        \"tracedListingGone\": (None if cache is None else\n",
     "matches": 1},
    {"why": "REG-2981 - a banked listing entry no longer counts the gitignored names its listed dirs held",
     "file": "heart2.py",
     "find": "                entry.update(ident=cache.ident(name, filename, pr), listed=list(ls), unread=list(un), ignoredSeen=seen)\n",
     "replace": "                entry.update(ident=cache.ident(name, filename, pr), listed=list(ls), unread=list(un))\n",
     "matches": 1},
]
