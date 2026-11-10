# -*- coding: utf-8 -*-
"""REG-2640 (#42 P3-fine) — A NAMED FILE THE LAW NEVER OPENED IS KEYED BY ITS NAME, NOT ITS BYTES; ONE IT READ RE-PROVES.

MEASURED 2026-10-24 on v3796 r6 (8 lines of CSS in control_ui.html): the P3 key moved for 5,012 of 6,327 proofs and
only 856 were reusable, so the Mac pre-prove re-proved from nothing. 3,474 of the moved proofs carried control_ui.html
only because a module in their import closure SPELLS its name; the law never opens it. heart2 now traces every
push-time law run (an audit hook installed by a sitecustomize on PYTHONPATH) and banks a PROVEN under a v2 key that
keys such a never-opened, never-stat'd named data file by name only. Every byte a run DID read is still keyed.

The cases: an edit to a file the law never touches IS reused (the point); an edit to one it opens, stats, or reaches
through a child the trace cannot see is NOT (soundness); the off switch and the v1 compatibility hold.

EVERYTHING HERE IS A FIXTURE: the throwaway repo copy of test_a_proven_verdict_is_reused_only_on_identical_bytes, with
one more file (tv/page.css) that a helper module NAMES and the law may or may not read. Nothing of his is read.
[[regression-guard]] [[unknown-stays-unknown]]
RED_PROOF below.
"""
import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import heart2 as H  # noqa: E402
import test_a_proven_verdict_is_reused_only_on_identical_bytes as P3  # noqa: E402  one fixture, never re-derived

#: what the law does with tv/page.css, spliced into the fixture law right after it knows where it is
_READS = {
    "never": "",
    "opens": "with open(os.path.join(here, 'page' + '.css')) as _fh: _fh.read()\n",
    "stats": "os.path.getsize(os.path.join(here, 'page' + '.css'))\n",
    "shell": "import subprocess; subprocess.run(['cat', os.path.join(here, 'page' + '.css')], capture_output=True)\n",
    "imports": "sys.path.insert(0, here); import named_mod\n",
    "direct": ("os.posix_spawn(sys.executable, [sys.executable, '-S', '-c', 'open(%r).read()' % "
               "os.path.join(here, 'page' + '.css')], dict(os.environ)); os.wait()\n"),
    "forkexec": ("import multiprocessing as _mp\n"
                 "if __name__ == '__main__':\n"
                 "    _mp.set_start_method('spawn'); _q = _mp.Process(target=print); _q.start(); _q.join()\n"),
    "pure": "import subprocess; subprocess.run(['true'])\n",
    "python": ("import subprocess; subprocess.run([sys.executable, '-c', 'open(%r).read()' % "
               "os.path.join(here, 'page' + '.css')])\n"),
    # -W takes a value, so a reader of the flags stops there and never sees the -S: the child is counted as traced,
    # says no hello, and only the hello count can tell
    "hidden": ("import subprocess; subprocess.run([sys.executable, '-W', 'ignore', '-S', '-c', 'open(%r).read()' % "
               "os.path.join(here, 'page' + '.css')])\n"),
    # REG-3319 - node children: the hook rides NODE_OPTIONS; a node that reads, one that does not, one without the hook
    "node_never": "import subprocess, shutil; subprocess.run([shutil.which('node'), '-e', '1'], capture_output=True)\n",
    "node_reads": ("import subprocess, shutil; subprocess.run([shutil.which('node'), '-e', "
                   "'require(\"fs\").readFileSync(process.argv[1])', os.path.join(here, 'page' + '.css')], "
                   "capture_output=True)\n"),
    "node_bare": ("import subprocess, shutil; subprocess.run([shutil.which('node'), '-e', "
                  "'require(\"fs\").readFileSync(process.argv[1])', os.path.join(here, 'page' + '.css')], "
                  "env={'PATH': os.environ.get('PATH', '')}, capture_output=True)\n"),
    "node_version": "import subprocess, shutil; subprocess.run([shutil.which('node'), '--version'], capture_output=True)\n",
    "node_shell": ("import subprocess, shutil; subprocess.run([shutil.which('node'), '-e', "
                   "'require(\"child_process\").execSync(\"cat \" + process.argv[1])', os.path.join(here, 'page' + '.css')], "
                   "capture_output=True)\n"),
}


def _law(how):
    head, sep, rest = P3._LAW.partition("here = os.path.dirname(os.path.abspath(__file__))\n")
    assert sep, "the P3 fixture law moved"
    return head + sep + _READS[how] + rest


class _Case(P3._Case):

    def setUp(self):
        super(_Case, self).setUp()
        self.tree.files["tv/helper_p3.py"] = "SALT = 1\nSTYLE = 'page.css'   # named, so it is in the static key\n"
        self.tree.files["tv/page.css"] = ".a { color: red }\n"
        # a module the helper only NAMES (as run_gates names every law): no AST import, so not in the closure
        self.tree.files["tv/helper_p3.py"] += "OTHER = 'named_mod.py'\n"
        self.tree.files["tv/named_mod.py"] = "X = 1\n"
        self._tracked = H._tracked_files
        H._tracked_files = lambda repo=None: None        # the fixture is not in git: every named file counts

    def tearDown(self):
        H._tracked_files = self._tracked
        H._TRACES.clear()
        super(_Case, self).tearDown()

    def law(self, how):
        self.tree.files["tv/" + P3._FILE] = _law(how)

    def cold_then_edit(self, how, env=None):
        self.law(how)
        H._TRACES.clear()
        results, per, stopped, runs, said = self.push(env=env)
        self.assertEqual((results, stopped), ({P3._GATE: H.PROVEN}, []), "\n".join(said))
        self.tree.files["tv/page.css"] = ".a { color: blue }   /* a one-line CSS edit */\n"
        H._TRACES.clear()                                 # the next push is another process
        return self.push(env=env)


_NODE = shutil.which("node") or shutil.which("nodejs")
_HOOK = os.path.join(HERE, "gate_trace", "node_trace.cjs")


def _without_node_hook(opts):
    """REG-3350 - NODE_OPTIONS with every --require of a node_trace.cjs taken out (an outer prover's hook). -> str"""
    import re
    return re.sub(r'--require\s+(?:"[^"]*node_trace\.cjs"|\S*node_trace\.cjs)\s*', "", opts or "").strip()


@unittest.skipUnless(_NODE and os.path.isfile(_HOOK), "no node here - the node half of the trace is not measured (UNMEASURED)")
class ANodeChildIsTracedToo(_Case):
    """REG-3319 (board #92 - his 11-06 'these shards and these tests need to be smooth and work fast'). A node child used
    to be untraced (U), so every law that runs node kept the byte-for-byte key over its whole closure: 1,555 of the 4,067
    proofs keyed on >1,500 files at 219a4846c had a node child and nothing else. node_trace.cjs now writes heart2's trace
    too, and heart2 counts a hooked node child like a python child: it must say its own hello."""

    def setUp(self):
        super(ANodeChildIsTracedToo, self).setUp()
        # REG-3350 - the prover running THIS law arms its own node_trace.cjs in NODE_OPTIONS (REG-3319), and that hook
        # writes whichever HEART2_TRACE_LOG a child carries - the fixture's too. Inherited, it traces node for the
        # fixture's heart2 even when the fixture's heart2 never armed it, and a broken arming stays green. The fixture
        # measures its own heart2's arming alone.
        _opts = os.environ.get("NODE_OPTIONS")
        if _opts is not None and "node_trace.cjs" in _opts:
            _p = mock.patch.dict(os.environ, {"NODE_OPTIONS": _without_node_hook(_opts)})
            _p.start()
            self.addCleanup(_p.stop)
        with io.open(_HOOK, encoding="utf-8") as fh:
            self.tree.files["tv/gate_trace/node_trace.cjs"] = fh.read()
        self.tree.files["tv/helper_p3.py"] += "DATA = 'data_p3.json'\n"
        self.tree.files["tv/data_p3.json"] = '{"n": 1}\n'

    def edit_then_push(self, how, path, body, env=None):
        self.law(how)
        H._TRACES.clear()
        results, per, stopped, runs, said = self.push(env=env)
        self.assertEqual((results, stopped), ({P3._GATE: H.PROVEN}, []), "\n".join(said))
        self.tree.files[path] = body
        H._TRACES.clear()
        return self.push(env=env)

    def test_a_node_child_that_never_opens_the_file_lets_it_go(self):
        """★ THE POINT: the law runs node, node opens nothing of the tree - a CSS edit re-proves nothing"""
        results, per, stopped, runs, said = self.cold_then_edit("node_never")
        self.assertReused(runs, results, said, "an edit to a file no node or python run of the law opened")

    def test_a_node_child_that_reads_the_file_re_proves(self):
        """★ SOUNDNESS: node reads page.css through fs - its bytes stay a key input"""
        results, per, stopped, runs, said = self.cold_then_edit("node_reads")
        self.assertRan(runs, said, "an edit to a file a traced node child read")

    def test_a_node_child_without_the_hook_drops_nothing(self):
        """★ SOUNDNESS: a node started with a scrubbed env never loads the hook - it is untraced, nothing is dropped"""
        results, per, stopped, runs, said = self.cold_then_edit("node_bare")
        self.assertRan(runs, said, "an edit read by a node child the hook never reached")

    def test_a_shell_started_by_node_drops_nothing(self):
        """★ SOUNDNESS: node's execSync runs `cat` through a shell no hook is in"""
        results, per, stopped, runs, said = self.cold_then_edit("node_shell")
        self.assertRan(runs, said, "an edit read by a shell a node child started")

    def test_node_version_reads_nothing(self):
        """`node --version` exits before any preload says hello (REG-3127): it is pure, never an untraced child"""
        results, per, stopped, runs, said = self.cold_then_edit("node_version")
        self.assertReused(runs, results, said, "an edit beside a law that only asked node its version")

    def test_once_a_node_ran_a_named_json_file_stays_a_byte_input(self):
        """★ SOUNDNESS ON ANY NODE: a module loader may read an ES module's imports or a JSON module past fs, so after a
        node child ran no JavaScript-family input is dropped - an edit to the named JSON re-proves, read or not"""
        results, per, stopped, runs, said = self.edit_then_push("node_never", "tv/data_p3.json", '{"n": 2}\n')
        self.assertRan(runs, said, "an edit to a JSON file beside a node child")

    def test_without_a_node_the_same_json_file_is_keyed_by_name(self):
        """the contrast: a law with no node child lets the same unread JSON go, so the rule is node's, not JSON's"""
        results, per, stopped, runs, said = self.edit_then_push("never", "tv/data_p3.json", '{"n": 2}\n')
        self.assertReused(runs, results, said, "an edit to an unread JSON file, no node in the run")

    def test_a_round_says_why_a_law_kept_every_byte(self):
        """REG-3319 - the round's RECORD line: which laws traced completely, and the CAUSE for the rest (here: the shell
        child `cat`), so what keeps keys wide is measured, never estimated from source text"""
        self.law("shell")
        H._TRACES.clear()
        self.push()
        c = H._trace_why_census()
        self.assertEqual((c["laws"], c["ok"]), (1, 0), c)
        self.assertTrue(any(k.startswith("spawn cat") for k, _n in c["causes"]), "the cause is not named: %s" % c)
        self.law("node_never")
        H._TRACES.clear()
        self.push()
        c = H._trace_why_census()
        self.assertEqual((c["laws"], c["ok"], c["causes"]), (1, 1, []), "a node-only law is not counted traced: %s" % c)

    def test_an_edit_to_the_node_hook_re_proves(self):
        """★ the hook decides what a key may drop: it is a byte input of every key, like the prover"""
        hook = self.tree.files["tv/gate_trace/node_trace.cjs"]
        results, per, stopped, runs, said = self.edit_then_push("node_never", "tv/gate_trace/node_trace.cjs",
                                                                hook + "// an edit to the hook\n")
        self.assertRan(runs, said, "an edit to node_trace.cjs")


class ANamedFileTheLawNeverOpenedIsKeyedByName(_Case):

    def test_an_edit_to_a_named_file_the_law_never_opened_reuses_the_proven(self):
        """★ THE POINT: page.css is in the key by name (a helper spells it), the law never opens it, and a CSS edit to
        it re-proves nothing - while the entry says which input it keyed by name"""
        results, per, stopped, runs, said = self.cold_then_edit("never")
        self.assertReused(runs, results, said, "an edit to a file no run of the law opened")
        unread = [e.get("unread") for e in self.entries().values()]
        self.assertEqual(unread, [["tv/named_mod.py", "tv/page.css"]], "the banked entry does not name what it keyed by name: %s" % unread)

    def test_an_edit_to_a_file_the_law_opened_is_proved_again(self):
        """★ SOUNDNESS: the law reads page.css - its bytes are an input, and the edit re-proves"""
        results, per, stopped, runs, said = self.cold_then_edit("opens")
        self.assertRan(runs, said, "an edit to a file the law opened")

    def test_an_edit_to_a_file_the_law_only_stats_is_proved_again(self):
        """★ os.path.getsize reads a size without an open: a stat is a read"""
        results, per, stopped, runs, said = self.cold_then_edit("stats")
        self.assertRan(runs, said, "an edit to a file the law stat'd")

    def test_a_child_the_trace_cannot_see_drops_nothing(self):
        """★ `cat` reads page.css in a process no hook is in: nothing is dropped, the edit re-proves"""
        results, per, stopped, runs, said = self.cold_then_edit("shell")
        self.assertRan(runs, said, "an edit read through an untraced child")

    def test_a_python_child_is_traced_too(self):
        """★ a python child inherits the hook: its open counts, the edit re-proves"""
        results, per, stopped, runs, said = self.cold_then_edit("python")
        self.assertRan(runs, said, "an edit read by a traced python child")

    def test_a_python_child_that_never_says_hello_drops_nothing(self):
        """★ a python child started with -S never loads the hook; the flags reader misses it (-W takes a value), so
        only the hello count stands between it and a stale PROVEN"""
        results, per, stopped, runs, said = self.cold_then_edit("hidden")
        self.assertRan(runs, said, "an edit read by a python child that was never traced")

    def test_an_edit_to_a_named_module_nothing_imported_reuses_the_proven(self):
        """★ the third input of v3796 r6: a law .py run_gates only names. Not imported, not opened: keyed by name"""
        self.law("never")
        H._TRACES.clear()
        r0 = self.push()
        self.assertEqual(r0[0], {P3._GATE: H.PROVEN}, "\n".join(r0[4]))
        self.tree.files["tv/named_mod.py"] = "X = 2   # another law's 47 new lines\n"
        H._TRACES.clear()
        results, per, stopped, runs, said = self.push()
        self.assertReused(runs, results, said, "an edit to a module the law never imported")

    def test_an_edit_to_a_named_module_the_law_imports_at_run_time_is_proved_again(self):
        """★ SOUNDNESS: a module the AST walk cannot see imported (sys.path + import) is read through the hook"""
        self.law("imports")
        H._TRACES.clear()
        r0 = self.push()
        self.assertEqual(r0[0], {P3._GATE: H.PROVEN}, "\n".join(r0[4]))
        self.tree.files["tv/named_mod.py"] = "X = 2\n"
        H._TRACES.clear()
        results, per, stopped, runs, said = self.push()
        self.assertRan(runs, said, "an edit to a module imported at run time")

    def test_the_static_closure_is_never_dropped(self):
        """a module the law imports by AST (helper_p3) stays a byte input even with an empty trace"""
        self.law("never")
        sandbox, root = self.tree.make()
        try:
            keep = H._keep_for(sandbox, P3._FILE, P3._proof())
            self.assertIn("tv/helper_p3.py", keep, keep)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_python_child_spawned_directly_is_counted(self):
        """★ os.posix_spawn without subprocess: the child is counted, says no hello (-S), and nothing is dropped"""
        results, per, stopped, runs, said = self.cold_then_edit("direct")
        self.assertRan(runs, said, "an edit read by a directly spawned python child")

    def test_a_multiprocessing_child_is_traced(self):
        """a multiprocessing spawn child (fork_exec, no Popen event) inherits the hook and says hello: still complete"""
        results, per, stopped, runs, said = self.cold_then_edit("forkexec")
        self.assertReused(runs, results, said, "a law that started a multiprocessing child that read nothing")

    def test_a_multiprocessing_child_is_traced_under_an_outer_trace(self):
        """the push-time prover runs THIS law traced: the fixture law's site then chains into the outer trace site, and
        a process hooked twice counts its one child twice (2 P, 1 hello) - incomplete, so nothing was ever reused"""
        own = H._trace_site()
        self.assertIsNotNone(own)
        site = tempfile.mkdtemp(prefix="h2-outer-site-")      # the OUTER prover's site: another process, another dir
        shutil.copy(os.path.join(own, "sitecustomize.py"), site)
        log = os.path.join(site, "outer.log")
        try:
            pp = os.environ.get("PYTHONPATH")
            outer = {"PYTHONPATH": site + ((os.pathsep + pp) if pp else ""),
                     "HEART2_TRACE_LOG": log, "HEART2_TRACE_SITE": site}
            with mock.patch.dict(os.environ, outer):
                results, per, stopped, runs, said = self.cold_then_edit("forkexec")
            self.assertReused(runs, results, said, "a multiprocessing child under an outer trace")
        finally:
            shutil.rmtree(site, ignore_errors=True)

    def test_a_pure_tool_child_still_lets_an_unread_file_go(self):
        """`true` opens no file of the tree: the trace stays complete and the unread file is still keyed by name"""
        results, per, stopped, runs, said = self.cold_then_edit("pure")
        self.assertReused(runs, results, said, "a law that only ran `true`")

    def test_the_off_switch_keeps_every_byte_in_the_key(self):
        """HEART2_TRACE=0: no trace, nothing dropped - the edit re-proves, as before REG-2640"""
        results, per, stopped, runs, said = self.cold_then_edit("never", env={"HEART2_TRACE": "0"})
        self.assertRan(runs, said, "HEART2_TRACE=0")

    def test_a_proof_with_nothing_to_drop_keeps_its_v1_key(self):
        """compatible: the key every bank on every machine already holds is unchanged when nothing is unread"""
        self.law("opens")
        self.tree.files["tv/helper_p3.py"] = self.tree.files["tv/helper_p3.py"].replace("OTHER = 'named_mod.py'\n", "")
        self.push()
        ent = self.entries()
        self.assertEqual(len(ent), 1)
        self.assertNotIn("unread", list(ent.values())[0])
        sandbox, root = self.tree.make()
        try:
            c = H._VerdictCache(path=self.cache_path, say=lambda *a: None)
            k_lookup = c.key_for(sandbox, P3._GATE, P3._FILE, P3._proof())[0]
            k_v1 = c.key_for(sandbox, P3._GATE, P3._FILE, P3._proof(), unread=[])[0]
            self.assertEqual(k_lookup, k_v1)
            self.assertIn(k_v1, ent, "the v1 key is not the key it was banked under")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_the_target_the_needs_and_the_prover_are_never_dropped(self):
        """the tampered target, every PROOF_NEEDS file and the prover are keyed by bytes, traced or not"""
        sandbox, root = self.tree.make()
        try:
            keep = H._keep_for(sandbox, P3._FILE, P3._proof())
            self.assertTrue({"tv/subject.txt", "tv/heart2.py", "tv/law_widths.py"} <= keep, keep)
            with H._TRACE_LOCK:
                H._TRACES[P3._FILE] = {"names": set(), "ok": True, "runs": 1}
            got = H._trace_unread(P3._FILE, ["tv/subject.txt", "tv/heart2.py", "tv/page.css", "tv/x.py"], keep)
            self.assertEqual(got, ["tv/page.css", "tv/x.py"], "a kept input was dropped, or a named one kept: %s" % got)
            with H._TRACE_LOCK:
                H._TRACES[P3._FILE]["ok"] = False
            self.assertEqual(H._trace_unread(P3._FILE, ["tv/page.css"], keep), [], "an incomplete trace dropped")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_the_trace_leaves_the_law_its_own_sys_path_and_sitecustomize(self):
        """the hook's directory leaves sys.path before the law's first line, and a sitecustomize it shadows still runs"""
        d = tempfile.mkdtemp(prefix="h2trace-fx.")
        try:
            other = os.path.join(d, "other")
            os.makedirs(other)
            with io.open(os.path.join(other, "sitecustomize.py"), "w", encoding="utf-8") as fh:
                fh.write("import builtins\nbuiltins.H2_OTHER_SITE = True\n")
            site = H._trace_site()
            log = os.path.join(d, "log")
            env = dict(os.environ, PYTHONPATH=site + os.pathsep + other, HEART2_TRACE_LOG=log, HEART2_TRACE_SITE=site)
            import subprocess
            r = subprocess.run([sys.executable, "-c", "import sys, builtins; print(%r in sys.path, "
                                "getattr(builtins, 'H2_OTHER_SITE', False))" % site], env=env,
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.stdout.split(), ["False", "True"], r.stdout + r.stderr)
            seen, ok = H._trace_read(log, os.getpid())
            self.assertTrue(ok, "a plain python run was not a complete trace")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_site_that_chains_into_the_trace_boots_once(self):
        """v3796 bank red: gate_trace's sitecustomize (a ledger law's fixture child) chains INTO this one; re-importing
        `sitecustomize` booted gate_trace a second time, every spawn was counted twice and the node law went red"""
        d = tempfile.mkdtemp(prefix="h2trace-fx.")
        try:
            first = os.path.join(d, "first")
            os.makedirs(first)
            with io.open(os.path.join(first, "sitecustomize.py"), "w", encoding="utf-8") as fh:
                fh.write("import builtins, os, sys, importlib.machinery, importlib.util\n"
                         "builtins.H2_BOOTS = getattr(builtins, 'H2_BOOTS', 0) + 1\n"
                         "here = os.path.dirname(os.path.abspath(__file__))\n"
                         "spec = importlib.machinery.PathFinder.find_spec('sitecustomize', "
                         "[p for p in sys.path if os.path.abspath(p or '.') != here])\n"
                         "if spec is not None:\n    spec.loader.exec_module(importlib.util.module_from_spec(spec))\n")
            site = H._trace_site()
            env = dict(os.environ, PYTHONPATH=first + os.pathsep + site, HEART2_TRACE_LOG=os.path.join(d, "log"),
                       HEART2_TRACE_SITE=site)
            import subprocess
            r = subprocess.run([sys.executable, "-c", "import builtins; print(getattr(builtins, 'H2_BOOTS', 0))"],
                               env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(r.stdout.split(), ["1"], "the site that chained into the trace booted again: " + r.stdout + r.stderr)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_chainer_between_the_gate_and_the_trace_runs_once(self):
        """v3796 review: gate -> mid -> trace; mid is not sys.modules['sitecustomize'], so a front-to-back scan from
        the trace picked mid again and booted the trace a second time"""
        d = tempfile.mkdtemp(prefix="h2trace-mid.")
        chain = ("import builtins, os, sys, importlib.machinery, importlib.util\n"
                 "builtins.H2_%s = getattr(builtins, 'H2_%s', 0) + 1\n"
                 "here = os.path.dirname(os.path.abspath(__file__))\n"
                 "spec = importlib.machinery.PathFinder.find_spec('sitecustomize', sys.path[sys.path.index(here) + 1:] "
                 "if here in sys.path else [])\n"
                 "if spec is not None:\n    spec.loader.exec_module(importlib.util.module_from_spec(spec))\n")
        try:
            dirs = []
            for name in ("GATE", "MID"):
                p = os.path.join(d, name.lower())
                os.makedirs(p)
                with io.open(os.path.join(p, "sitecustomize.py"), "w", encoding="utf-8") as fh:
                    fh.write(chain % (name, name))
                dirs.append(p)
            site = H._trace_site()
            env = dict(os.environ, PYTHONPATH=os.pathsep.join(dirs + [site]), HEART2_TRACE_LOG=os.path.join(d, "log"),
                       HEART2_TRACE_SITE=site)
            import subprocess
            r = subprocess.run([sys.executable, "-c", "import builtins; print(builtins.H2_GATE, builtins.H2_MID)"],
                               env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(r.stdout.split(), ["1", "1"], "a site in the chain booted twice: " + r.stdout + r.stderr)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def _gate_boots(self, order):
        """B lines per process when python starts under `order` (a list of 'gateA' / 'gateB' / 'h2') -> list of counts"""
        d = tempfile.mkdtemp(prefix="h2gt-")
        try:
            src = os.path.join(HERE, "gate_trace")
            dirs = {"h2": H._trace_site()}
            for n in ("gateA", "gateB"):
                dirs[n] = os.path.join(d, n)
                shutil.copytree(src, dirs[n], ignore=shutil.ignore_patterns("__pycache__"))
            gt = os.path.join(d, "gate.log")
            env = dict(os.environ, PYTHONPATH=os.pathsep.join(dirs[n] for n in order), TV_GATE_TRACE=gt,
                       TV_GATE_TRACE_ROOT=d, HEART2_TRACE_LOG=os.path.join(d, "h2.log"), HEART2_TRACE_SITE=dirs["h2"])
            import subprocess
            subprocess.run([sys.executable, "-c", "pass"], env=env, capture_output=True, timeout=60)
            with io.open(gt, encoding="utf-8") as fh:
                return [l for l in fh.read().splitlines() if l.startswith("B\t")]
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_gate_copy_that_chained_into_the_trace_is_never_booted_again(self):
        """v3796 node law red: a sandbox's gate_trace -> the trace -> heart2's own kill-watch copy booted the gate twice"""
        self.assertEqual(len(self._gate_boots(["gateA", "h2", "gateB"])), 1)

    def test_the_trace_first_still_boots_the_gate_copy_behind_it(self):
        """the push-time order (trace, then heart2's kill-watch gate_trace): the gate copy must still load"""
        self.assertEqual(len(self._gate_boots(["h2", "gateA"])), 1)

    def test_a_killed_provers_trace_dir_is_swept_and_a_live_ones_is_kept(self):
        """the trace dir of a prover SIGKILL ended (no atexit ran) leaves on the next run; a live prover's stays"""
        base = tempfile.mkdtemp(prefix="h2sweep-fx.")
        try:
            import subprocess
            dead = subprocess.Popen([sys.executable, "-c", "pass"]); dead.wait()
            for pid in (dead.pid, os.getpid(), os.getppid()):
                os.makedirs(os.path.join(base, "heart2-trace-%d-x" % pid, "sub"))
            gone = H._trace_sweep(base)
            self.assertEqual(gone, ["heart2-trace-%d-x" % dead.pid])
            self.assertEqual(sorted(_fx_tmp.list_own(base)), sorted("heart2-trace-%d-x" % p for p in (os.getpid(), os.getppid())))
        finally:
            shutil.rmtree(base, ignore_errors=True)


RED_PROOF = [
    {
        "why": "REG-3319 - the round's census names no cause: what keeps keys wide goes back to being estimated",
        "file": "heart2.py",
        "find": "                    if why is not None:\n                        why.add(rest[:60])\n",
        "replace": "                    pass\n",
        "matches": 1,
    },
    {
        "why": "REG-3319 - node's reads never reach heart2's trace: a CSS edit a node child read reuses a PROVEN",
        "file": "gate_trace/node_trace.cjs",
        "find": "  const R = (p) => { note('R', p); base2('R', p); };\n",
        "replace": "  const R = (p) => { note('R', p); };\n",
        "matches": 1,
    },
    {
        # REG-3350 - the ask itself is broken, not the Popen line that calls it: on Linux under Python 3.13+ a child
        # also raises os.posix_spawn, whose branch asks node_version_only again, and an untouched ask there said U
        # (BLIND on GitHub's 3.14 shard while RED on the Mac's 3.9)
        "why": "REG-3319 - every node child is called pure: one with no hook reads page.css and the edit reuses a PROVEN",
        "file": "heart2.py",
        "find": "        return b in (\"node\", \"nodejs\") and a in ([\"--version\"], [\"-v\"])\n",
        "replace": "        return b in (\"node\", \"nodejs\")\n",
        "matches": 1,
    },
    {
        "why": "REG-3319 - after a node ran, an unread JSON is dropped: a loader that reads past fs leaves a stale key",
        "file": "heart2.py",
        "find": "                  and not (node_ran and r.lower().endswith(_NODE_KEEP_EXT)))\n",
        "replace": "                  )\n",
        "matches": 1,
    },
    {
        "why": "REG-3319 - the node hook is not a key input: an edit to what decides a drop serves every narrowed PROVEN",
        "file": "heart2.py",
        "find": "    for prover in (\"heart2.py\", \"law_widths.py\", os.path.join(\"gate_trace\", \"node_trace.cjs\")):\n",
        "replace": "    for prover in (\"heart2.py\", \"law_widths.py\"):\n",
        "matches": 1,
    },
    {
        "why": "REG-3319 - a traced law run never arms NODE_OPTIONS: every node child stays untraced (narrowing lost)",
        "file": "heart2.py",
        "find": "                if os.path.isfile(_ntr) and \"node_trace.cjs\" not in str(env.get(\"NODE_OPTIONS\") or \"\"):\n",
        "replace": "                if False:\n",
        "matches": 1,
    },
    {
        "why": "v3796 node law red - the trace chains into a second gate_trace copy while one already runs",
        "file": "heart2.py",
        "find": "                                        and not (_ran and _gt(p))])",
        "replace": "                                        ])",
        "matches": 1,
    },
    {
        "why": "v3796 review r4 - the trace skips every gate_trace copy, so the kill watch behind it never arms",
        "file": "heart2.py",
        "find": "        _ran = any(_gt(d) for d in _skip)",
        "replace": "        _ran = True",
        "matches": 1,
    },
    {
        "why": "v3796 pre-prove red - a law run under an outer trace hooks its children twice: every child counted twice",
        "file": "heart2.py",
        "find": "    if getattr(_s, \"_h2_trace_on\", False):",
        "replace": "    if False:",
        "matches": 1,
    },
    {
        "why": "v3796 review - a chainer BETWEEN the gate and the trace is not sys.modules' entry, so the trace re-ran it",
        "file": "heart2.py",
        "find": "                _skip.add(_o.path.dirname(_o.path.abspath(_f.f_code.co_filename)))\n",
        "replace": "                pass\n",
        "matches": 1,
    },
    {
        "why": "v3796 bank red - the trace re-imports `sitecustomize`, so a site that chained into it boots twice",
        "file": "heart2.py",
        "find": "    if _nxt is not None and _nxt.loader is not None:   # a successor that raises propagates, as `import` did\n        _nxt.loader.exec_module(_iu.module_from_spec(_nxt))\n",
        "replace": "    _s.modules.pop(\"sitecustomize\", None)\n    import sitecustomize  # noqa: F401\n",
        "matches": 1,
    },
    {
        "why": "REG-2640 - a direct os.posix_spawn python child is never counted, so its missing hello goes unseen",
        "file": "heart2.py",
        "find": "                emit(\"P\" if py else \"U\", ev + \" \" + what)\n",
        "replace": "                emit(\"p\", ev + \" \" + what)\n",
        "matches": 1,
    },
    {
        "why": "REG-2640 - the static import closure is dropped like a merely named file",
        "file": "heart2.py",
        "find": "    keep |= {rel(p) for p in closure}\n",
        "replace": "    keep |= set()\n",
        "matches": 1,
    },
    {
        "why": "REG-2640 - every named data file is keyed by name, read or not: a CSS edit the law reads reuses a PROVEN",
        "file": "heart2.py",
        "find": "                  and r.rsplit(\"/\", 1)[-1] not in names\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-2640 - a stat is not a read: a law that asks a file's size is reused over a new size",
        "file": "heart2.py",
        "find": "    for n in (\"stat\", \"lstat\", \"access\", \"readlink\"):\n",
        "replace": "    for n in ():\n",
        "matches": 1,
    },
    {
        "why": "REG-2640 - a child no hook is in (cat, git, node) still lets files go",
        "file": "heart2.py",
        "find": "                elif tag:\n                    untraced = True\n",
        "replace": "                elif tag:\n                    pass\n",
        "matches": 1,
    },
    {
        "why": "REG-2640 - a counted python child that never said hello is taken as traced",
        "file": "heart2.py",
        "find": "    return seen, bool(root and not untraced and len(hellos) >= py)\n",
        "replace": "    return seen, bool(root and not untraced)\n",
        "matches": 1,
    },
    {
        "why": "REG-2640 - an incomplete trace still drops what it did not see",
        "file": "heart2.py",
        "find": "        if not t or not t[\"ok\"] or t[\"runs\"] < 1:\n",
        "replace": "        if not t or t[\"runs\"] < 1:\n",
        "matches": 1,
    },
    {
        "why": "REG-2640 - a python child does not inherit the hook's reads (its opens are lost)",
        "file": "heart2.py",
        "find": "        elif ev == \"open\":\n            names(\"R\", args[0] if args else None)\n",
        "replace": "        elif ev == \"open\" and _o.getppid() != int(_o.environ.get(\"H2_NOPE\", \"0\")) and _s.argv[0] != \"-c\":\n            names(\"R\", args[0] if args else None)\n",
        "matches": 1,
    },
    {
        "why": "REG-2640 - the unread file is hashed by bytes again: the CSS edit re-proves (the fix undone)",
        "file": "heart2.py",
        "find": "            if rel in unread:                         # REG-2640 - no traced run opened it: its name, never its bytes\n",
        "replace": "            if False:\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
