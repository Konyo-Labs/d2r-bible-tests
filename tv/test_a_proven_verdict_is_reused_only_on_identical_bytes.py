# -*- coding: utf-8 -*-
"""#42 P3 — A PUSH REUSES A PROVEN VERDICT ONLY WHEN EVERY BYTE IT DEPENDS ON IS IDENTICAL; EVERYTHING ELSE RUNS.

His order, 2026-09-28: "this is CRITICAL we need to optimize clock time". MEASURED 2026-09-29 on the v3523 push: the
render gate refused at minute 95 (twice), and every retry re-proved the same ~40 changed laws (~83 min) over a tree that
had not changed by one byte - three times. A verdict cache would have made each retry render-and-publish only (~15 min).

`heart2.py --prove NAMES --push` (hooks/pre-push's call) now banks each PROVEN under a key that digests EVERY file the
proof can depend on - the law file, the tv/ modules it imports transitively (browser_gates' AST closure), every file a
literal string in that closure names (bible.html, control_ui.html, hooks/pre-push ...), the proof's tampered target
(#41 rank 8: PROVEN was keyed to the gate file alone, so an edit to the SUBJECT could make a proof BLIND while the census
read proven), every PROOF_NEEDS file, the proof entry, the gate's spec and the prover itself - and the next push re-runs
only the proofs whose key changed. A miss runs. An unkeyable law (a helper nobody can parse, a PROOF_NEEDS directory)
runs every push and is never cached. Only PROVEN is stored and only a stored PROVEN is reused. The key is taken from the
SANDBOX (the exact tree proved), before and after the run - a tree that moved under a proof banks nothing. The plain
--prove path, run_gates and CI never open it: the verdict of record is always a run.

THE SECOND EYE ON THE FIRST CUT (2026-09-29) added four rules, each pinned below: a REUSED proof keeps the time it was
MEASURED - the census stamps a gate standing on cached proofs with the oldest provedAt among them, never this run's
clock (the first cut stamped every hit "now", the defect control_app's oldestProofMs was built against); a law that
LISTS A DIRECTORY ITSELF (os.listdir / os.walk / glob / Path.iterdir) has an input no byte key can name and is never
cached - the law file only, never the closure; the cache's OWN failure (key_for raising) costs a re-prove and never a
verdict; and a stored PROVEN with no readable provedAt is not reused, because a verdict nobody can date cannot keep its
age.

R4 (REG-2341, 2026-10-21) - the v1 file reached 320 MB because every entry kept its whole inputs list and the cap ran
before the merge with the disk, which undid it. An entry now keeps nInputs and a digest of the names; the cap runs AFTER
the merge and evicts the least useful first (an entry no reader could serve, then one superseded by a newer proof of
the same gate/proof/target/widths, then one whose gate is gone, then the least recently USED or proved); and an entry
that stands on facts - a traced kind, a facts reference - is never served by this byte key (the critic: missing or
unreadable facts are a MISS, always). The store lives in git's common dir (REG-2340), gitignored side files and all.

EVERYTHING HERE IS A FIXTURE: a throwaway repo copy holding a ten-line law, its helper, its subject and a bible.html; the
cache file lives beside them. No browser starts, the real tree is never copied, nothing of his is read or written -
except the cases that READ the real registry, .gitignore and the CI workflows, because that is where the wiring lives.
[[regression-guard]] [[unknown-stays-unknown]] [[the-unjoined-end]] [[stale-reading]]
RED_PROOF below.
"""
import ast
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import heart2 as H  # noqa: E402
# ONE copy of the fixture helpers, shared with the #42 law rather than re-derived here. [[copy-drift]]
from test_a_push_proof_runs_only_where_its_defect_shows import _Env, _Patch, _no_facts  # noqa: E402

#: the fixture law: imports helper_p3, names helper_lazy inside a function that never runs (it is in the CLOSURE but
#: never executes), reads its subject and the repo-root bible.html, logs every run (restriction | clean/tampered), and
#: goes red when its subject says BROKEN and 1280x800 is measured. P3_MUTATE=1 makes it write beside itself.
#: ⚠ THE SUBJECT IS REACHED BY A COMPUTED NAME, ON PURPOSE. Named by the literal "subject.txt" it would enter the key
#: through the closure's named files as well as through the proof's target, and the red-proof that drops the target
#: from the key came back BLIND on exactly that: an inert sabotage, not a blind law (measured 2026-09-29). Reached by
#: a computed name, the ONLY way the subject reaches the key is the tampered-target rule this law exists to pin.
_LAW = r'''
import io, os, sys
import helper_p3
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
SUBJECT = os.path.join(here, "sub" + "ject.txt")


def never():
    import helper_lazy


with io.open(SUBJECT, encoding="utf-8") as fh:
    subject = fh.read()
with io.open(os.path.join(root, "bible.html"), encoding="utf-8") as fh:
    page = fh.read()
raw = os.environ.get("TV_LAW_WIDTHS")
measured = {"1280x800", "375x812"} if raw is None else set(raw.split(","))
with io.open(os.environ["P3_LOG"], "a", encoding="utf-8") as fh:
    fh.write("%s|%s\n" % (raw if raw is not None else "ALL", "tampered" if "BROKEN" in subject else "clean"))
if os.environ.get("P3_MUTATE"):
    with io.open(SUBJECT, "a", encoding="utf-8") as fh:
        fh.write("# moved\n")
red = "BROKEN" in subject and "1280x800" in measured
print("Ran 1 tests in 0.001s")
print("")
print("FAILED (failures=1)" if red else "OK")
sys.exit(1 if red else 0)
'''
_GATE, _FILE = "p3-fixture-law", "t_p3_law.py"


def _proof(**kw):
    pr = {"why": "the fixture's defect", "file": "subject.txt", "find": "fine", "replace": "BROKEN", "matches": 1}
    pr.update(kw)
    return pr


class _Tree(object):
    """make_sandbox stand-in: a REAL throwaway repo copy built from `files` (repo-relative) - edit `files` between two
    runs to move the tree the way an edit moves his."""

    def __init__(self):
        self.files = {"tv/control_app.py": "# sandbox marker\n", "tv/" + _FILE: _LAW, "tv/helper_p3.py": "SALT = 1\n",
                      "tv/helper_lazy.py": "OK = True\n", "tv/subject.txt": "all fine here\n",
                      "bible.html": "<html>fine</html>\n"}
        self.made = []

    def make(self, say=print):
        root = tempfile.mkdtemp(prefix="p3law.")
        repo = os.path.join(root, "repo")
        for rel, text in self.files.items():
            p = os.path.join(repo, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with io.open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
        self.made.append(root)
        return os.path.join(repo, "tv"), root


def _push_run(tree, proofs, cache_path, env=None, hold=None):
    """The REAL push-time path over the fixture tree, with a _VerdictCache opened on `cache_path` the way one push opens
    it (None: no cache, every proof runs). -> (results, per_proof, stopped, runs logged, lines said)
    `hold` (a list) receives the cache object, for the cases that read what it measured."""
    fd, log = tempfile.mkstemp(prefix="p3log.")
    os.close(fd)
    said, stopped = [], []
    kw = dict(P3_LOG=log, HEART2_PROVE_WORKERS="1", TV_LAW_WIDTHS=None, P3_MUTATE=None)
    kw.update(env or {})
    try:
        cache = H._VerdictCache(path=cache_path, say=said.append) if cache_path else None
        if hold is not None:
            hold.append(cache)
        with _Env(**kw), _Patch(make_sandbox=tree.make, _push_facts=_no_facts):
            results, per = H._prove_push([(_GATE, _FILE, proofs)], said.append, stopped, cache=cache)
        with io.open(log, encoding="utf-8") as fh:
            runs = [l.strip().split("|") for l in fh if l.strip()]
    finally:
        os.remove(log)
    return results, per, stopped, runs, said


_CLEAN_TAMPERED = [["ALL", "clean"], ["ALL", "tampered"]]


class _Case(unittest.TestCase):
    """One fixture tree and one cache file per case; a fresh _VerdictCache per 'push' (each push opens the file anew)."""

    def setUp(self):
        self.trees = []
        self.tree = self.fresh_tree()
        self.dir = tempfile.mkdtemp(prefix="p3cache.")
        self.cache_path = os.path.join(self.dir, ".heart2_cache.json")
        self.said = []

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        for t in self.trees:
            for r in t.made:
                shutil.rmtree(r, ignore_errors=True)

    def fresh_tree(self):
        """A new fixture tree, remembered so tearDown removes every sandbox it made (a replaced tree leaked its dirs)."""
        self.tree = _Tree()
        self.trees.append(self.tree)
        return self.tree

    def entries(self):
        if not os.path.exists(self.cache_path):
            return {}
        with io.open(self.cache_path, encoding="utf-8") as fh:
            return json.load(fh)["entries"]

    def push(self, proofs=None, env=None):
        return _push_run(self.tree, proofs or [_proof()], self.cache_path, env)

    def assertRan(self, runs, said, what):
        self.assertEqual(runs, _CLEAN_TAMPERED, "%s: the proof did not RUN (clean then tampered): %s\n%s"
                         % (what, runs, "\n".join(said)))

    def assertReused(self, runs, results, said, what):
        self.assertEqual(runs, [], "%s: the proof RAN although every keyed byte was identical: %s\n%s"
                         % (what, runs, "\n".join(said)))
        self.assertEqual(results, {_GATE: H.PROVEN}, "\n".join(said))
        self.assertTrue(any("PROVEN (cached" in l and "not re-run" in l for l in said),
                        "%s: the reuse is not said on the verdict line: %s" % (what, said))


class AProvenVerdictIsReusedOnlyOnIdenticalBytes(_Case):

    def test_a_second_push_over_identical_bytes_reuses_the_proven_verdict_without_a_run(self):
        """★ cold: the proof runs (clean + tampered), is PROVEN and banked; warm, same bytes: not run, PROVEN, said as
        cached - and both summaries print the denominator"""
        results, per, stopped, runs, said = self.push()
        self.assertRan(runs, said, "cold push")
        self.assertEqual((results, stopped), ({_GATE: H.PROVEN}, []), "\n".join(said))
        ent = self.entries()
        self.assertEqual(len(ent), 1, "one PROVEN was proved and %d entr(ies) were banked" % len(ent))
        e = list(ent.values())[0]
        self.assertEqual((e["verdict"], e["gate"], e["proof"], e["target"]), (H.PROVEN, _GATE, 0, "subject.txt"))
        # R4 - the key digests every byte; the entry keeps only HOW MANY inputs and a digest of their names
        self.assertNotIn("inputs", e, "the entry still carries its whole inputs list (the 320 MB file)")
        self.assertGreaterEqual(e.get("nInputs") or 0, 4, "the entry does not say how many inputs it was keyed on")
        self.assertRegex(str(e.get("inputsDigest")), r"^[0-9a-f]{16}$", "the entry carries no digest of its inputs")
        self.assertTrue(any("#42 P3 CACHE: 0 of 1 proof(s) reused" in l and "1 proved and banked" in l for l in said),
                        "PRINT THE DENOMINATOR (cold): %s" % [l for l in said if "P3 CACHE" in l])
        results, per, stopped, runs, said = self.push()
        self.assertReused(runs, results, said, "warm push")
        self.assertEqual(per[_GATE], [H.PROVEN])
        self.assertTrue(any("#42 P3 CACHE: 1 of 1 proof(s) reused" in l for l in said),
                        "PRINT THE DENOMINATOR (warm): %s" % [l for l in said if "P3 CACHE" in l])

    def test_editing_the_tampered_target_invalidates_it(self):
        """★ #41 rank 8: the SUBJECT moved (still holding the anchor) - the proof runs again, never reused"""
        self.push()
        self.tree.files["tv/subject.txt"] = "all fine here\n# an edit to the subject\n"
        results, per, stopped, runs, said = self.push()
        self.assertRan(runs, said, "the target changed")
        self.assertEqual(results, {_GATE: H.PROVEN})
        self.assertEqual(len(self.entries()), 2, "the new bytes were not banked under a NEW key")

    def test_editing_an_imported_helper_invalidates_it(self):
        """★ a module the law imports changed (its behaviour did not) - the closure is keyed, so it runs again"""
        self.push()
        self.tree.files["tv/helper_p3.py"] = "SALT = 2\n"
        results, per, stopped, runs, said = self.push()
        self.assertRan(runs, said, "an imported helper changed")
        self.tree.files["tv/helper_lazy.py"] = "OK = False\n"
        results, per, stopped, runs, said = self.push()
        self.assertRan(runs, said, "a helper imported LAZILY (inside a function that never runs) changed")

    def test_editing_the_law_file_or_the_proof_entry_invalidates_it(self):
        """★ the law's own bytes and the proof entry (why / find / replace / widths) are part of the key"""
        self.push()
        self.tree.files["tv/" + _FILE] = _LAW + "\n# a comment added to the law\n"
        results, per, stopped, runs, said = self.push()
        self.assertRan(runs, said, "the law file changed")
        results, per, stopped, runs, said = self.push([_proof(why="the same tamper, described differently")])
        self.assertRan(runs, said, "the proof entry changed")

    def test_editing_a_file_the_law_names_invalidates_it(self):
        """★ bible.html is named by a literal string in the law and read at the repo root: keyed"""
        self.push()
        self.tree.files["bible.html"] = "<html>fine, but changed</html>\n"
        results, per, stopped, runs, said = self.push()
        self.assertRan(runs, said, "a file the law names changed")

    def test_an_unkeyable_law_is_never_cached(self):
        """★ a closure module nobody can parse (never executed - the law stays PROVEN) and a PROOF_NEEDS directory: the
        proof runs on every push, nothing is banked, and the line says why"""
        self.tree.files["tv/helper_lazy.py"] = "def (:\n"
        for what in ("first", "second"):
            results, per, stopped, runs, said = self.push()
            self.assertRan(runs, said, "unparseable closure, %s push" % what)
            self.assertEqual(results, {_GATE: H.PROVEN}, "\n".join(said))
            self.assertEqual(self.entries(), {}, "an unkeyable law was banked")
            self.assertTrue(any("not cacheable" in l and "helper_lazy.py will not parse" in l for l in said),
                            "the reason it cannot be cached is not said: %s" % said)
            self.assertTrue(any("1 not cacheable" in l for l in said), "PRINT THE DENOMINATOR: %s" % said[-2:])
        self.fresh_tree()
        self.tree.files["tv/" + _FILE] = _LAW + "\nPROOF_NEEDS = ['needs_dir']\n"
        self.tree.files["tv/needs_dir/x.txt"] = "x\n"
        for what in ("first", "second"):
            results, per, stopped, runs, said = self.push()
            self.assertRan(runs, said, "PROOF_NEEDS directory, %s push" % what)
            self.assertEqual(self.entries(), {}, "a law whose PROOF_NEEDS is a directory was banked")
            self.assertTrue(any("not cacheable" in l and "is a directory" in l for l in said), said)

    def test_a_blind_or_invalid_verdict_is_never_cached(self):
        """★ only PROVEN is a shortcut: a BLIND (declared where the defect never shows) and an INVALID (a rotted anchor)
        bank nothing, and the next push finds them again"""
        for pr, verdict in ((_proof(widths=["375x812"]), H.BLIND), (_proof(find="absent"), H.INVALID)):
            self.fresh_tree()
            for what in ("first", "second"):
                results, per, stopped, runs, said = self.push([pr])
                self.assertEqual(results, {_GATE: verdict}, "%s push: %s" % (what, "\n".join(said)))
                self.assertNotEqual(runs, [], "%s: a %s was served from the cache" % (what, verdict))
                self.assertEqual(self.entries(), {}, "a %s was banked" % verdict)

    def test_only_a_stored_proven_is_reused(self):
        """★ whatever else lands in the file - an entry under the RIGHT key that does not say PROVEN - is not a shortcut"""
        self.push()
        ent = self.entries()
        key = list(ent)[0]
        ent[key]["verdict"] = H.BLIND
        with io.open(self.cache_path, "w", encoding="utf-8") as fh:
            json.dump({"entries": ent}, fh)
        results, per, stopped, runs, said = self.push()
        self.assertRan(runs, said, "a non-PROVEN entry under the right key")
        self.assertEqual(self.entries()[key]["verdict"], H.PROVEN, "the run's PROVEN did not replace the stray entry")
        # (second eye) a PROVEN nobody can DATE is not a shortcut either: it could not keep its age in the census
        ent = self.entries()
        ent[key]["provedAt"] = "yesterday"
        with io.open(self.cache_path, "w", encoding="utf-8") as fh:
            json.dump({"entries": ent}, fh)
        results, per, stopped, runs, said = self.push()
        self.assertRan(runs, said, "a PROVEN with no readable provedAt")
        self.assertIsInstance(self.entries()[key]["provedAt"], int, "the re-proof did not restore a dated entry")

    def test_a_cached_verdict_keeps_its_measured_time_in_the_census(self):
        """★ (second eye on the first cut) a hit is a verdict from an EARLIER run over the same bytes: the cache reports
        the gate's oldest reused provedAt, says so, and _write_state stamps verdictAt with THAT time - never this run's
        clock; a run that reused nothing stamps now; a stamp can never lie in the future; a gate the run did not judge
        takes none. The first cut stamped every hit "now" - the defect control_app's oldestProofMs exists to expose."""
        hold = []
        results, per, stopped, runs, said = _push_run(self.tree, [_proof()], self.cache_path, hold=hold)
        self.assertRan(runs, said, "cold push")
        self.assertEqual(hold[0].measured, {}, "a cold push reused nothing, yet the map says %s" % hold[0].measured)
        proved_at = list(self.entries().values())[0]["provedAt"]
        time.sleep(0.01)
        before = int(time.time() * 1000)
        self.assertLess(proved_at, before, "PREMISE: the entry was proved before the warm push started")
        hold = []
        results, per, stopped, runs, said = _push_run(self.tree, [_proof()], self.cache_path, hold=hold)
        self.assertReused(runs, results, said, "warm push")
        self.assertEqual(hold[0].measured, {_GATE: proved_at},
                         "the warm push does not report the time its reused proof was measured: %s" % hold[0].measured)
        self.assertTrue(any("keeps the age each was MEASURED at" in l and "never this run's clock" in l for l in said),
                        "the census rule is not said: %s" % said[-3:])
        state = os.path.join(self.dir, ".heart2.json")

        def census():
            with io.open(state, encoding="utf-8") as fh:
                return json.load(fh)["verdictAt"]

        with _Patch(STATE=state, gate_files=lambda say=None: [(_GATE, _FILE)], red_proofs_in=lambda f: [_proof()],
                    pixel_gates=lambda gates, unk=None: set(), gates_fingerprint=lambda gates: "fixture",
                    surface_verdict=lambda: {}):
            H._write_state({_GATE: H.PROVEN}, measured={_GATE: proved_at})
            self.assertEqual(census()[_GATE], proved_at,
                             "verdictAt was stamped with this run's clock, not the time the proof was measured")
            H._write_state({_GATE: H.PROVEN})
            self.assertGreaterEqual(census()[_GATE], before, "a run that reused nothing did not stamp now")
            H._write_state({_GATE: H.PROVEN}, measured={_GATE: proved_at + 10 ** 9, "unjudged": proved_at})
            got = census()
            self.assertLessEqual(got[_GATE], int(time.time() * 1000), "a stamp landed in the future")
            self.assertNotIn("unjudged", got, "a gate this run never judged took a stamp from the map")

    def test_a_law_that_lists_a_directory_itself_is_keyed_by_what_its_traced_run_listed(self):
        """★ (second eye) a law calling os.listdir / os.walk / glob.glob / Path.rglob / iterdir reads whatever is THERE
        at run time - a law file added between two pushes over otherwise identical bytes could turn it red. It used to
        be unkeyable outright; REG-2944 keys it by what its TRACED run listed: banked under a v3 key holding the names
        and bytes of every directory it listed, reused over an identical tree, and re-proved the moment a file joins a
        directory it listed. The LAW FILE ONLY: a closure module listing a directory keeps the law's v1 key (the
        closure-listing floor). And the receiver decides, never the bare name: ast.walk is a walk over a syntax tree.
        git is asked of the FIXTURE here (tracked = its files): a listed entry git neither tracks nor keeps is runtime
        data, never key material."""
        from unittest import mock
        self.tree.files["tv/" + _FILE] = _LAW.replace(
            "here = os.path.dirname", "listed = os.listdir(os.path.dirname(os.path.abspath(__file__)))\n"
                                      "here = os.path.dirname", 1)
        with mock.patch.object(H, "_tracked_files", lambda repo=None: frozenset(self.tree.files)), \
                mock.patch.object(H, "_kept_files", lambda repo=None: frozenset()):
            results, per, stopped, runs, said = self.push()
            self.assertRan(runs, said, "a law that lists a directory, cold")
            self.assertEqual(results, {_GATE: H.PROVEN}, "\n".join(said))
            ent = self.entries()
            self.assertEqual(len(ent), 1, "a listing law with a complete trace was not banked: %s" % said)
            self.assertEqual(list(ent.values())[0].get("listed"), ["tv"], "the entry does not say what it listed")
            results, per, stopped, runs, said = self.push()
            self.assertReused(runs, results, said, "a listing law over an identical tree and an identical listing")
            self.tree.files["tv/new_law_p3.py"] = "X = 1\n"
            results, per, stopped, runs, said = self.push()
            self.assertRan(runs, said, "a listing law after a file joined the directory it lists")
        self.assertIsNone(H._lists_a_directory(ast.parse(
            "import ast\nfor n in ast.walk(t):\n    pass\nx = walk(1)\ny = os.path.exists('.')\n")),
            "ast.walk, a bare walk() or os.path.exists read as a directory listing")
        for src, want in (("import os\nos.walk('.')\n", "os.walk"), ("import os as _o\n_o.scandir('.')\n", "os.scandir"),
                          ("import glob as _g\n_g.glob('*')\n", "glob.glob"), ("from glob import iglob\niglob('*')\n",
                                                                               "glob.iglob"),
                          ("from os import listdir as ld\nld('.')\n", "os.listdir"),
                          ("from pathlib import Path\nfor p in Path('.').rglob('*'):\n    pass\n", "rglob()"),
                          ("p.iterdir()\n", "iterdir()"), ("Path(x).glob('*.py')\n", "glob()")):
            got = H._lists_a_directory(ast.parse(src))
            self.assertEqual(got and got[0], want, "%r -> %r" % (src, got))
        self.fresh_tree()
        self.tree.files["tv/helper_p3.py"] = ("import os\nSALT = 1\n"
                                              "NAMES = os.listdir(os.path.dirname(os.path.abspath(__file__)))\n")
        self.push()
        results, per, stopped, runs, said = self.push()
        self.assertReused(runs, results, said, "a CLOSURE module lists a directory (the law does not)")

    def test_the_caches_own_failure_never_changes_a_verdict(self):
        """★ (second eye) key_for raising BEFORE the run: UNKEYABLE, said with the exception, the proof runs; raising
        AFTER the run: the tree is read as MOVED, nothing banked - and both times the verdict is the run's and the
        push is not refused. A cache may cost a re-prove, never a verdict."""

        def boom(path, memo=None):
            raise RuntimeError("a pathological digest")

        with _Patch(_sha_file=boom):
            results, per, stopped, runs, said = self.push()
        self.assertRan(runs, said, "the key raised before the run")
        self.assertEqual((results, stopped), ({_GATE: H.PROVEN}, []),
                         "the cache's own exception changed the verdict or refused the push:\n%s" % "\n".join(said))
        self.assertEqual(self.entries(), {}, "a proof whose key raised was banked")
        self.assertTrue(any("not cacheable" in l and "taking its key raised RuntimeError" in l for l in said), said)
        self.assertTrue(any("1 not cacheable" in l for l in said), "PRINT THE DENOMINATOR: %s" % said[-1:])
        real_key, seen = H._VerdictCache.key_for, [0]

        def flaky(self_, *a, **k):
            seen[0] += 1
            if seen[0] == 2:                      # the first key_for (before the run) works; the second raises
                raise ValueError("relpath across volumes")
            return real_key(self_, *a, **k)

        H._VerdictCache.key_for = flaky
        try:
            results, per, stopped, runs, said = self.push()
        finally:
            H._VerdictCache.key_for = real_key
        self.assertEqual(seen[0], 2, "PREMISE: key_for was not called before and after the run")
        self.assertRan(runs, said, "the key raised after the run")
        self.assertEqual((results, stopped), ({_GATE: H.PROVEN}, []),
                         "an exception after the run changed the verdict or refused the push:\n%s" % "\n".join(said))
        self.assertEqual(self.entries(), {}, "banked although the key could not be taken again")
        self.assertTrue(any("moved under this proof" in l and "could not be taken again: ValueError" in l
                            for l in said), said)
        self.assertTrue(any("1 moved under their proof" in l for l in said), "PRINT THE DENOMINATOR: %s" % said[-1:])

    def test_an_unreadable_cache_reruns_everything_says_so_and_is_rewritten(self):
        """★ garbage on disk is UNREADABLE (said), never 'empty and quiet'; the first PROVEN rewrites it"""
        with io.open(self.cache_path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        results, per, stopped, runs, said = self.push()
        self.assertRan(runs, said, "an unreadable cache")
        # the OPENER's line (R4: the writer that later sets the file aside says so too - one saying must not stand in
        # for the other, so the open's own words are asked for)
        self.assertTrue(any("#42 P3 CACHE" in l and "UNREADABLE" in l and "would not parse" in l for l in said),
                        "the unreadable cache was not said out loud when it was opened: %s" % said[:3])
        self.assertEqual(len(self.entries()), 1, "the unreadable file was not rewritten by the first PROVEN")
        with io.open(self.cache_path, "w", encoding="utf-8") as fh:
            json.dump(["a list, not the map"], fh)
        results, per, stopped, runs, said = self.push()
        self.assertRan(runs, said, "a cache of the wrong shape")
        self.assertTrue(any("#42 P3 CACHE" in l and "UNREADABLE" in l and "no 'entries' map" in l for l in said),
                        said[:3])

    def test_the_tree_moving_under_a_proof_is_not_banked(self):
        """★ the key is taken again after the run: the law writes beside itself (P3_MUTATE), the key differs, PROVEN
        stands and nothing is banked - the next push runs it again"""
        results, per, stopped, runs, said = self.push(env={"P3_MUTATE": "1"})
        self.assertEqual(results, {_GATE: H.PROVEN}, "\n".join(said))
        self.assertEqual(self.entries(), {}, "a proof the tree moved under was banked")
        self.assertTrue(any("moved under this proof" in l and "nothing is banked" in l for l in said), said)
        self.assertTrue(any("1 moved under their proof" in l for l in said), "PRINT THE DENOMINATOR: %s" % said[-1:])

    def test_the_plain_prove_path_never_opens_it_and_the_off_switch_is_honoured(self):
        """★ a warm cache and the NON-push path: the proof runs; prove(push=False) never calls _prove_push at all;
        prove(push=True) opens the cache and hands it over; HEART2_PROVE_CACHE=0 hands None and says so"""
        self.push()
        fd, log = tempfile.mkstemp(prefix="p3log.")
        os.close(fd)
        try:
            with _Env(P3_LOG=log, HEART2_PROVE_WORKERS="1", TV_LAW_WIDTHS=None, P3_MUTATE=None), \
                    _Patch(make_sandbox=self.tree.make):
                results, per = H._prove_gates([(_GATE, _FILE, [_proof()])], self.said.append)
            with io.open(log, encoding="utf-8") as fh:
                runs = [l.strip().split("|") for l in fh if l.strip()]
        finally:
            os.remove(log)
        self.assertEqual((runs, results), (_CLEAN_TAMPERED, {_GATE: H.PROVEN}),
                         "the plain --prove path served a verdict from the cache: %s" % runs)
        seen = []

        def fake_push(have, say, stopped=None, cache=None, blank=None):
            seen.append(("push", type(cache).__name__ if cache is not None else None))
            return {_GATE: H.PROVEN}, {_GATE: [H.PROVEN]}

        def fake_gates(have, say=print, workers=None, blank=None):
            seen.append(("plain", None))
            return {_GATE: H.PROVEN}, {_GATE: [H.PROVEN]}

        with _Patch(gate_files=lambda say=None: [(_GATE, _FILE)], red_proofs_in=lambda f: [_proof()],
                    red_proof_unreadable=lambda f: False, _prove_push=fake_push, _prove_gates=fake_gates,
                    _write_state=lambda r, measured=None, unmeasured=None: None, CACHE=self.cache_path):
            with _Env(HEART2_PROVE_CACHE=None):
                H.prove(only={_GATE}, say=self.said.append, push=True, stopped=[])
                H.prove(only={_GATE}, say=self.said.append)
            with _Env(HEART2_PROVE_CACHE="0"):
                H.prove(only={_GATE}, say=self.said.append, push=True, stopped=[])
        self.assertEqual(seen, [("push", "_VerdictCache"), ("plain", None), ("push", None)],
                         "prove() opened the cache on the wrong path, or ignored the off switch: %s" % seen)
        self.assertTrue(any("OFF for this run" in l and "HEART2_PROVE_CACHE=0" in l for l in self.said),
                        "the off switch was not said: %s" % self.said[-3:])

    def test_the_cache_writes_only_a_file_named_like_itself(self):
        """★ it never edits a guard: a _VerdictCache pointed at any other name refuses to write, says so, and leaves no
        file - the instruments law admits heart2's cache write on exactly that refusal"""
        other = os.path.join(self.dir, "control_app.py")
        c = H._VerdictCache(path=other, say=self.said.append)
        c.store("k", {"verdict": H.PROVEN})
        self.assertFalse(c.flush(), "a cache named like a guard was written")
        self.assertFalse(os.path.exists(other), "the refused write left a file")
        self.assertTrue(any("refusing to write" in l and "control_app.py" in l for l in self.said), self.said)
        ok = H._VerdictCache(path=self.cache_path, say=self.said.append)
        ok.store("k", {"verdict": H.PROVEN})
        self.assertTrue(ok.flush(), "the cache named like itself was not written")
        self.assertEqual(self.entries(), {"k": {"verdict": H.PROVEN}})

    def test_run_gates_and_ci_never_consult_it_and_it_lives_gitignored_beside_the_census(self):
        """★ the registry passes --push to no gate and names the cache nowhere; no workflow names either; the file is
        ignored by git and sits beside .heart2.json"""
        import run_gates as RG
        for g in RG.GATES:
            self.assertFalse(any("--push" in str(a) or ".heart2_cache" in str(a) for a in (g.argv or [])),
                             "gate %s reaches the push-time cache: %s" % (g.name, g.argv))
        with io.open(os.path.join(HERE, "run_gates.py"), encoding="utf-8") as fh:
            consts = [x.value for x in ast.walk(ast.parse(fh.read()))
                      if isinstance(x, ast.Constant) and isinstance(x.value, str)]
        self.assertFalse(any(".heart2_cache" in c for c in consts), "run_gates.py names the cache file")
        # #173 (REG-2939) - no CI WORKFLOW names the cache or runs a push-time prove: that half lists .github/workflows,
        # so it lives in test_no_ci_workflow_reaches_the_push_cache.py and this law's 27 proofs can be saved.
        with io.open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as fh:
            ignored = [l.strip() for l in fh if l.strip() and not l.startswith("#")]
        self.assertIn("tv/.heart2_cache.json", ignored, "the cache is not gitignored - one Mac's proofs would travel")
        self.assertIn("tv/.heart2_cache.json.tmp", ignored)
        # R9 (REG-2340) - no generation or side file of a store ever shows in git status: a writer's own tmp, a .prev, an
        # .unreadable-<ms> kept aside, a checkout's own fallback store dir
        import fnmatch
        for name in ("tv/.heart2_cache.json.123.4.tmp", "tv/.heart2_cache.json.prev", "tv/.heart2_cache.json.unreadable-9",
                     "tv/.heart2_red.json.123.4.tmp", "tv/.heart2_red.json.prev"):
            self.assertTrue(any(fnmatch.fnmatch(name, pat) for pat in ignored),
                            "%s would show in git status - no .gitignore pattern covers it" % name)
        self.assertIn("tv/.heart2_v2/", ignored, "a checkout's own fallback store dir would show in git status")
        # #242 (REG-1996) - ONE CACHE PER MACHINE, and REG-2340: it is in git's common dir - shared by main and every
        # worktree, never copied, never listed by git, and never the tv/ file the code before REG-2341 still writes
        self.assertEqual(H.CACHE, H._shared_cache_path(), "the cache is not the machine's one shared cache")
        self.assertEqual(os.path.basename(H.CACHE), ".heart2_cache.json")
        mine = H._shared_cache_path(env={})
        self.assertEqual(os.path.dirname(mine), H._shared_store()[0], "the cache is not in the machine's store dir")
        self.assertNotEqual(os.path.dirname(mine), H.HERE, "the cache is old code's tv/ file again")
        common, _why = H._git_common_dir(H.REPO)
        if common:                                      # a real checkout (a heart2 sandbox has no git dir)
            self.assertEqual(os.path.dirname(mine), os.path.join(common, "heart2"))


class TheStoreKeepsWhatItCanServe(unittest.TestCase):
    """R4 (REG-2341) - the cap AFTER the merge, eviction by use, and nothing served that stands on facts it cannot check."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="p3cap.")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, ".heart2_cache.json")

    def _write(self, entries):
        with io.open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"format": 2, "entries": entries}, fh)

    def _flush(self, mine, cap, live=None):
        """One run banks `mine` over what is on disk, with CACHE_MAX = cap. -> the entries on disk after"""
        with _Patch(CACHE_MAX=cap, _live_gate_names=lambda: live):
            c = H._VerdictCache(path=self.path, say=lambda *a, **k: None)
            for k, e in mine.items():
                c.store(k, e)
            self.assertTrue(c.flush(), "PREMISE: the flush failed")
        with io.open(self.path, encoding="utf-8") as fh:
            return json.load(fh)["entries"]

    @staticmethod
    def _e(gate, proof, t, **kw):
        e = {"verdict": H.PROVEN, "gate": gate, "proof": proof, "target": "s.txt", "at": "", "why": "w", "provedAt": t}
        e.update(kw)
        return e

    def test_the_cap_is_counted_after_the_merge(self):
        """★ three on disk, two banked by this run, a cap of three: three on disk after - the merge cannot undo the cap"""
        self._write(dict(("d%d" % i, self._e("g", i, i)) for i in range(3)))
        got = self._flush({"m1": self._e("g", 10, 10), "m2": self._e("g", 11, 11)}, cap=3)
        self.assertEqual(len(got), 3, "the store holds %d entries over a cap of 3 - the cap ran before the merge"
                         % len(got))
        self.assertIn("m1", got)
        self.assertIn("m2", got)

    def test_a_superseded_entry_leaves_before_an_older_live_one(self):
        """★ at the cap, a proof superseded by a newer proof of the SAME gate/proof/target/widths leaves first - even
        when an unrelated entry is older"""
        self._write({"old_x": self._e("x", 0, 2), "y": self._e("y", 0, 3), "sup": self._e("g", 0, 4)})
        got = self._flush({"new": self._e("g", 0, 5)}, cap=3)
        self.assertEqual(sorted(got), ["new", "old_x", "y"], "the superseded entry stayed while a live one left: %s"
                         % sorted(got))

    def test_a_used_entry_outlives_a_newer_unused_one(self):
        """★ eviction is by USE: an old proof a push served yesterday outlives a newer one nobody has asked for"""
        self._write({"used": self._e("a", 0, 1, usedAt=100), "idle": self._e("b", 0, 2), "z": self._e("c", 0, 3)})
        got = self._flush({"m": self._e("d", 0, 50)}, cap=3)
        self.assertEqual(sorted(got), ["m", "used", "z"], "the used entry left before an unused one: %s" % sorted(got))

    def test_a_hit_is_a_use_written_at_the_flush(self):
        """★ a lookup that serves an entry stamps its usedAt, and the next flush writes it"""
        self._write({"k": self._e("a", 0, 1)})
        c = H._VerdictCache(path=self.path, say=lambda *a, **k: None)
        self.assertIsNotNone(c.lookup("k"))
        self.assertTrue(c.flush(), "a hit alone did not reach the disk")
        with io.open(self.path, encoding="utf-8") as fh:
            self.assertIsInstance(json.load(fh)["entries"]["k"].get("usedAt"), int, "the hit was not written as a use")

    def test_an_entry_whose_gate_is_gone_leaves_before_a_live_one(self):
        """★ a gate no longer registered: its proofs leave before an older proof of a live gate"""
        self._write({"live_old": self._e("live", 0, 1), "gone_new": self._e("gone", 0, 9)})
        got = self._flush({"m": self._e("live", 1, 10)}, cap=2, live={"live"})
        self.assertEqual(sorted(got), ["live_old", "m"], "a dead gate's entry outlived a live one: %s" % sorted(got))

    def test_a_corrupt_stamp_never_blocks_a_write(self):
        """★ an entry whose usedAt is not a number is read as never used - it never raises inside the merge, where it
        would block every later write of the store"""
        self._write({"k": self._e("a", 0, 1, usedAt="never")})
        got = self._flush({"k": self._e("a", 0, 2)}, cap=10)
        self.assertEqual(got["k"]["provedAt"], 2, "a corrupt stamp on disk blocked the write of this run's proof")

    def test_an_entry_standing_on_facts_is_never_served_by_the_byte_key(self):
        """★ (critic) MISSING OR UNREADABLE FACTS ARE A MISS, ALWAYS: an entry of a kind this reader cannot check - a traced
        kind, a facts table it does not hold, a facts reference to nothing - is never a hit, never 'no requirement'"""
        c = H._VerdictCache(path=self.path, say=lambda *a, **k: None)
        c.entries = {"plain": self._e("a", 0, 1), "traced": self._e("a", 1, 1, kind="traced"),
                     "facts": self._e("a", 2, 1, facts={}), "ref": self._e("a", 3, 1, factsRef="gone")}
        self.assertIsNotNone(c.lookup("plain"), "BASELINE: a static entry is a hit")
        for k in ("traced", "facts", "ref"):
            self.assertIsNone(c.lookup(k), "an entry standing on facts was served by the byte key: %s" % k)


class TheKeyNamesEveryInput(unittest.TestCase):
    """law_inputs alone, over a fixture tv/: what is in the key and what is deliberately not."""

    def test_the_closure_the_named_files_the_target_and_the_prover_are_inputs(self):
        d = tempfile.mkdtemp(prefix="p3inputs.")
        try:
            repo = os.path.join(d, "repo")
            tv = os.path.join(repo, "tv")
            os.makedirs(os.path.join(repo, "hooks"))
            os.makedirs(os.path.join(tv, "sub"))
            files = {"tv/t_law.py": "import helper_a\nX = 'bible.html'\nY = 'hooks/pre-push'\nZ = 'sub'\n"
                                    "W = '.heart2.json'\nV = '/etc/hosts'\n",
                     "tv/helper_a.py": "import helper_b\nimport json\n", "tv/helper_b.py": "N = 'data.txt'\n",
                     "tv/helper_unused.py": "U = 1\n", "tv/data.txt": "d\n", "tv/subject.txt": "s\n",
                     "tv/.heart2.json": "{}", "tv/heart2.py": "# prover\n", "tv/law_widths.py": "# widths\n",
                     "bible.html": "<html>\n", "hooks/pre-push": "#!/bin/bash\n", "root_mod.py": "R = 1\n"}
            for rel, text in files.items():
                with io.open(os.path.join(repo, rel), "w", encoding="utf-8") as fh:
                    fh.write(text)
            got, why = H.law_inputs(tv, "t_law.py", [{"file": "subject.txt", "find": "s", "replace": "x"}])
            rels = sorted(os.path.relpath(p, repo) for p in got)
            self.assertIsNone(why)
            self.assertEqual(rels, sorted(["tv/t_law.py", "tv/helper_a.py", "tv/helper_b.py", "tv/data.txt",
                                           "tv/subject.txt", "tv/heart2.py", "tv/law_widths.py", "bible.html",
                                           "hooks/pre-push"]),
                             "the key's inputs are not the closure + named files + target + prover: %s" % rels)
            for absent in ("tv/helper_unused.py", "tv/.heart2.json", "root_mod.py"):
                self.assertNotIn(absent, rels, "%s is in the key: an unimported module, a run record or an unnamed "
                                               "root file" % absent)
            got, why = H.law_inputs(tv, "t_law.py", [{"file": "gone.txt", "find": "s", "replace": "x"}])
            self.assertIn("not a file inside the sandbox", why or "", "a missing target was keyed")
            got, why = H.law_inputs(tv, "t_law.py", [{"file": "../../etc/hosts", "find": "s", "replace": "x"}])
            self.assertIn("not a file inside the sandbox", why or "", "a target climbing out of the sandbox was keyed")
            got, why = H.law_inputs(tv, "t_gone.py", [])
            self.assertEqual((got, why), ([], "the gate file is not in the sandbox"))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_named_file_git_does_not_track_is_not_a_key_input(self):
        """#242 (2026-10-08) - MEASURED on the v3618 push: 66 proofs banked on the final bytes, 1 reused - each key held
        40+ runtime files his live console rewrites every few seconds, named as literals somewhere in control_app's
        closure, so every key moved. The push-time cache counts a NAMED file only when git tracks it."""
        # REG-2360 / REG-2392 - a push from a LINKED WORKTREE runs the pre-push hook with GIT_DIR exported (absolute,
        # <main>/.git/worktrees/<name>; git exports no GIT_WORK_TREE, and a push from the main checkout no GIT_DIR at
        # all), and GIT_DIR beats cwd= and -C. Pushed that way (the v3784 push, 2026-10-22), this case's throwaway
        # `git init` re-initialised the REAL repo's common config as core.bare=true and its `git add` staged kept.txt
        # into the push worktree's index. Dropped for THIS test only; addCleanup puts them back.
        _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith("GIT_")}
        self.addCleanup(os.environ.update, _gitenv)
        d = tempfile.mkdtemp(prefix="p3tracked.")
        try:
            repo = os.path.join(d, "repo")
            tv = os.path.join(repo, "tv")
            os.makedirs(tv)
            files = {"tv/t_law.py": "X = 'bible.html'\nY = 'state_p3.json'\n", "tv/state_p3.json": "{}",
                     "tv/subject.txt": "s\n", "bible.html": "<html>\n"}
            for rel, text in files.items():
                with io.open(os.path.join(repo, rel), "w", encoding="utf-8") as fh:
                    fh.write(text)
            pr = [{"file": "subject.txt", "find": "s", "replace": "x"}]
            every, _w = H.law_inputs(tv, "t_law.py", pr)
            some, _w2 = H.law_inputs(tv, "t_law.py", pr, tracked=frozenset(["tv/t_law.py", "tv/subject.txt", "bible.html"]))
            rel = lambda xs: sorted(os.path.relpath(p, repo) for p in xs)
            self.assertIn("tv/state_p3.json", rel(every), "BASELINE: with no tracked set the named file must be keyed")
            self.assertNotIn("tv/state_p3.json", rel(some), "an untracked runtime file is still a key input (#242)")
            self.assertIn("bible.html", rel(some), "a TRACKED named file left the key")
            self.assertIn("tv/subject.txt", rel(some), "the tampered target left the key")
        finally:
            shutil.rmtree(d, ignore_errors=True)
        # the tracked set is git's own answer for a real tree - asked of a throwaway git repo, never of this tree (a heart2
        # sandbox is a copy with no .git, where git cannot answer and the key falls back to counting every named file)
        e = tempfile.mkdtemp(prefix="p3git.")
        try:
            with io.open(os.path.join(e, "kept.txt"), "w", encoding="utf-8") as fh:
                fh.write("k\n")
            with io.open(os.path.join(e, "state.json"), "w", encoding="utf-8") as fh:
                fh.write("{}")
            for cmd in (["git", "init", "-q"], ["git", "add", "kept.txt"]):
                subprocess.run(cmd, cwd=e, capture_output=True, check=True)
            got = H._tracked_files(e)
            self.assertEqual(got, frozenset(["kept.txt"]), "git's tracked set was not read: %r" % (got,))
            self.assertIsNone(H._tracked_files(os.path.join(e, "no_such_dir")), "a tree git cannot answer for was not UNKNOWN")
        finally:
            shutil.rmtree(e, ignore_errors=True)

    def test_a_restored_target_is_hashed_again_not_served_from_before_the_tamper(self):
        """the digest memo keys on size and mtime, so the bytes a tamper wrote and restored are read again"""
        d = tempfile.mkdtemp(prefix="p3sha.")
        try:
            p = os.path.join(d, "f.txt")
            memo = {}
            with io.open(p, "w", encoding="utf-8") as fh:
                fh.write("one\n")
            a = H._sha_file(p, memo)
            with io.open(p, "w", encoding="utf-8") as fh:
                fh.write("two\n")
            b = H._sha_file(p, memo)
            self.assertNotEqual(a, b, "a rewritten file was served from the memo")
            self.assertIsNone(H._sha_file(os.path.join(d, "missing"), memo), "a missing file did not read as None")
        finally:
            shutil.rmtree(d, ignore_errors=True)


RED_PROOF = [
    {
        "why": "R4 - an entry keeps its whole inputs list again, and the store grows back to hundreds of MB",
        "file": "heart2.py",
        "find": "    out = dict((k, v) for k, v in entry.items() if k != \"inputs\")\n",
        "replace": "    out = dict(entry)\n",
        "matches": 1,
    },
    {
        "why": "R4 - the cap runs before the merge with the disk, which undoes it: the store outgrows its cap",
        "file": "heart2.py",
        "find": "                ent = _merged_cache((disk or {}).get(\"entries\"), mine, used)\n                out[\"evicted\"] = _cache_evict(ent, CACHE_MAX)\n",
        "replace": "                _cache_evict(mine, CACHE_MAX)\n                ent = _merged_cache((disk or {}).get(\"entries\"), mine, used)\n                out[\"evicted\"] = 0\n",
        "matches": 1,
    },
    {
        "why": "R4 - eviction ignores use: an old proof pushes still serve leaves before a newer one nobody asks for",
        "file": "heart2.py",
        "find": "        return (3, max(_proven_at(e), _num(e.get(\"usedAt\"))))\n",
        "replace": "        return (3, _proven_at(e))\n",
        "matches": 1,
    },
    {
        "why": "R4 - a corrupt stamp raises inside the merge, and the store can never be written again",
        "file": "heart2.py",
        "find": "            if d is not None and _num(d.get(\"usedAt\")) > _num(e.get(\"usedAt\")):\n",
        "replace": "            if d is not None and (d.get(\"usedAt\") or 0) > (e.get(\"usedAt\") or 0):\n",
        "matches": 1,
    },
    {
        "why": "R4 - a superseded proof is evicted no sooner than a live one",
        "file": "heart2.py",
        "find": "        if newest.get((e.get(\"gate\"), e.get(\"proof\"), e.get(\"target\"), e.get(\"at\"), e.get(\"why\"))) != k:\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "R4 - a gate no longer registered keeps its proofs ahead of live ones",
        "file": "heart2.py",
        "find": "        if live is not None and e.get(\"gate\") not in live:\n            return (2, _proven_at(e))\n",
        "replace": "        if False:\n            return (2, _proven_at(e))\n",
        "matches": 1,
    },
    {
        "why": "R4 - a hit is not recorded as a use, so eviction can never tell a served proof from an idle one",
        "file": "heart2.py",
        "find": "                self.used[key] = int(time.time() * 1000)       # R4 - usedAt: eviction is by use, written at the flush\n",
        "replace": "                pass\n",
        "matches": 1,
    },
    {
        "why": "(critic) an entry standing on facts is served by the byte key - absent facts read as no requirement",
        "file": "heart2.py",
        "find": "        if e.get(\"kind\", \"static\") != \"static\" or \"facts\" in e or \"factsRef\" in e:\n            return None\n",
        "replace": "        if False:\n            return None\n",
        "matches": 1,
    },
    {
        "why": "R9 - a writer's tmp is no longer ignored by git: a leftover shows in git status, one `git add -A` from public",
        "file": "../.gitignore",
        "find": "\ntv/.heart2_cache*\n",
        "replace": "\n",
        "matches": 1,
    },
    {
        "why": "#242 (2026-10-08) - an untracked runtime file named in a law's closure is a key input again, so every key moves",
        "file": "tv/heart2.py",
        "find": "            named = {q for q in named if os.path.relpath(q, repo).replace(os.sep, \"/\") in tracked}\n",
        "replace": "            pass\n",
        "matches": 1,
    },
    {
        "why": "#41 rank 8 - the tampered target never enters the key: an edit to the SUBJECT reuses a PROVEN",
        "file": "heart2.py",
        "find": "        inputs = sorted(set(base) | {tgt})\n",
        "replace": "        inputs = sorted(set(base))\n",
        "matches": 1,
    },
    {
        "why": "the import closure never enters the key: an edit to a helper the law imports reuses a PROVEN",
        "file": "heart2.py",
        "find": "            stack.append(local[dep])\n",
        "replace": "            pass  # closure not walked\n",
        "matches": 1,
    },
    {
        "why": "a file the law names (bible.html) never enters the key",
        "file": "heart2.py",
        "find": "        inputs |= named\n",
        "replace": "        pass\n",
        "matches": 1,
    },
    {
        "why": "an UNKEYABLE law is cached anyway, under a digest of the inputs that could be read",
        "file": "heart2.py",
        "find": "        if why:\n            return None, [], why\n        # the closure is shared",
        "replace": "        if False:\n            return None, [], why\n        # the closure is shared",
        "matches": 1,
    },
    {
        "why": "a BLIND / INVALID is banked as if it were PROVEN, and the next push reuses it",
        "file": "heart2.py",
        "find": "    return verdict == PROVEN\n",
        "replace": "    return verdict in (PROVEN, BLIND, INVALID)\n",
        "matches": 1,
    },
    {
        "why": "anything in the file under the right key is reused, not only a stored PROVEN",
        "file": "heart2.py",
        "find": "        return e if isinstance(e, dict) and e.get(\"verdict\") == PROVEN else None\n",
        "replace": "        return e if isinstance(e, dict) else None\n",
        "matches": 1,
    },
    {
        "why": "the plain --prove path (run_gates' and CI's verdict of record) opens the cache too",
        "file": "heart2.py",
        "find": "        results, per_proof = _prove_gates(have, say, blank=_blank)\n",
        "replace": "        results, per_proof = _prove_push(have, say, stopped, cache=open_cache(say), blank=_blank)\n",
        "matches": 1,
    },
    {
        "why": "the key is not taken again after the run: a tree that moved under a proof is banked",
        "file": "heart2.py",
        "find": "        if again == key:\n",
        "replace": "        if True:\n",
        "matches": 1,
    },
    {
        "why": "an unreadable cache reads as EMPTY and quiet - a failed read handed back as data",
        "file": "heart2.py",
        "find": "        if not self.readable:\n            say(",
        "replace": "        if False:\n            say(",
        "matches": 1,
    },
    {
        "why": "the cache writes wherever it is pointed - a guard's name included",
        "file": "heart2.py",
        "find": "        if os.path.basename(self.path) != os.path.basename(CACHE) and os.path.basename(self.path) != _RED_NAME:\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "HEART2_PROVE_CACHE=0 is ignored: the cold half of a measurement is served warm",
        "file": "heart2.py",
        "find": "    if str(os.environ.get(\"HEART2_PROVE_CACHE\", \"1\")).strip().lower() in (\"0\", \"no\", \"off\", \"false\"):\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "the census stamps a gate standing on reused proofs with THIS run's clock - forty gates read 'just now' "
               "on a retried push whose proofs ran an hour ago",
        "file": "heart2.py",
        "find": "        if _n in (results or {}) and isinstance(_ms, (int, float)) and not isinstance(_ms, bool):\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "the run never folds its hits into the per-gate measured time, so prove() hands the census nothing",
        "file": "heart2.py",
        "find": "            if results.get(_gn) == PROVEN:\n                _ages[_gn] = min(_ages[_gn], _ms) if _gn in _ages else _ms\n",
        "replace": "            if False:\n                _ages[_gn] = min(_ages[_gn], _ms) if _gn in _ages else _ms\n",
        "matches": 1,
    },
    {
        "why": "REG-2944 - a law that lists a directory itself is cached under a key that cannot name what it listed: "
               "a file joining that directory is served the old PROVEN",
        "file": "heart2.py",
        "find": "        lists = self.lists(sandbox, filename)\n        if not lists:\n",
        "replace": "        lists = False\n        if not lists:\n",
        "matches": 1,
    },
    {
        "why": "the cache's own exception before the run is recorded BLIND and refuses the push",
        "file": "heart2.py",
        "find": "        try:\n            key, rels, kwhy = cache.key_for(sandbox, name, filename, pr)\n        except Exception as _ke:\n            key, rels, kwhy = None, [], \"taking its key raised %s (%s)\" % (type(_ke).__name__, str(_ke)[:80])\n",
        "replace": "        key, rels, kwhy = cache.key_for(sandbox, name, filename, pr)\n",
        "matches": 1,
    },
    {
        "why": "the cache's own exception after the run turns a proof that just came back PROVEN into a BLIND refusal",
        "file": "heart2.py",
        "find": "        try:\n            again, rels2, _w2 = cache.key_for(sandbox, name, filename, pr)\n        except Exception as _ke:\n            again, _how = None, \"its key could not be taken again: %s\" % type(_ke).__name__\n",
        "replace": "        again, rels2, _w2 = cache.key_for(sandbox, name, filename, pr)\n",
        "matches": 1,
    },
    {
        "why": "a stored PROVEN with no readable provedAt is reused - a verdict nobody can date reaches the census",
        "file": "heart2.py",
        "find": "        if not (isinstance(e, dict) and isinstance(e.get(\"provedAt\"), (int, float))\n                and not isinstance(e.get(\"provedAt\"), bool)):\n            return None\n",
        "replace": "        if False:\n            return None\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
