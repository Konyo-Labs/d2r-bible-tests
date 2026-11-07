# -*- coding: utf-8 -*-
"""v3768 — A GATE CARRIES WHEN GIT SAYS ITS INPUTS HAVE NOT MOVED SINCE THE PROOF.

The ledger stores the commit a PASS was proved at. The next run diffs that commit once and
intersects the result with the gate's inputs. It does not hash those files again. A miss runs.
A FAIL is never stored. A corrupt ledger is unreadable, never empty. An unreachable sha runs.
--full (v3849) consults it unless TV_FULL_FRESH=1. CI does not. A carried line says `proven at <sha> (<age>)`
and is not a fresh pass and not new evidence.

The changed-law red-proof (v3292) is a different stage and does not read this file.
"""
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import gate_ledger as GL  # noqa: E402

SHA = "abcdef123456"
PROBES = {"python": "3.9.9", "node": "v20.0.0", "playwright": "1.40.0"}
_LAW = "import helper_gl\nimport sys\nprint('OK')\nsys.exit(0)\n"
_HELPER = "SALT = 1\n"
_PLAIN = "import sys\nprint('OK')\nsys.exit(0)\n"
_LISTING = "import os, sys, tempfile\nos.listdir(tempfile.mkdtemp())\nprint('OK')\nsys.exit(0)\n"
_NODE = "console.log('ok')\n"
_PW = "import playwright" + "\nprint('ok')\n"


class _Env(object):
    def __init__(self, **kw):
        self.kw = kw
        self.old = {}

    def __enter__(self):
        for key, val in self.kw.items():
            self.old[key] = os.environ.get(key)
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
        return self

    def __exit__(self, *exc):
        for key, val in self.old.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val


class _G(object):
    def __init__(self, name, argv, timeout=30, cwd=".", needs_app=False, skip_ok=()):
        self.name = name
        self.argv = argv
        self.timeout = timeout
        self.cwd = cwd
        self.needs_app = needs_app
        self.skip_ok = tuple(skip_ok)


def _git(root, *args):
    proc = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "git failed").strip())
    return proc


def _tree(files):
    root = tempfile.mkdtemp(prefix="gledger.")
    tv = os.path.join(root, "tv")
    os.makedirs(tv)
    with io.open(os.path.join(root, ".gitignore"), "w", encoding="utf-8") as fh:
        fh.write(".gate_ledger.json\n.gate_inputs.json\n*.tmp\n")
    for name, text in files.items():
        with io.open(os.path.join(tv, name), "w", encoding="utf-8") as fh:
            fh.write(text)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "ledger@example.com")
    _git(root, "config", "user.name", "ledger")
    _git(root, "config", "commit.gpgsign", "false")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    led = os.path.join(root, ".gate_ledger.json")
    return root, led


def _gate(root, filename, timeout=30, argv_head=None):
    script = os.path.join(root, "tv", filename)
    head = argv_head or [sys.executable]
    return _G("carry-fixture", head + [script], timeout=timeout, cwd=root)


def _open(path, probes=None):
    return GL.Ledger(path=path, probes=dict(probes or PROBES))


def _run_traced(gate, root=None):
    """Run the fixture gate the way run_gates does with the ledger on. -> (rc, trace path)"""
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(
        [a for a in gate.argv if str(a).endswith(".py")][0])))
    trace = GL.trace_path()
    base = dict(os.environ)
    # REG-3350 - the prover running THIS law arms its own node_trace.cjs in NODE_OPTIONS (heart2, REG-3319), and that one
    # hook file writes the ledger's trace too: inherited, it traces node for the ledger even when trace_env never armed
    # it, and a broken arming stays green. The fixture measures the ledger's own arming alone.
    if "node_trace.cjs" in (base.get("NODE_OPTIONS") or ""):
        base["NODE_OPTIONS"] = re.sub(r'--require\s+(?:"[^"]*node_trace\.cjs"|\S*node_trace\.cjs)\s*', "",
                                      base["NODE_OPTIONS"]).strip()
    env = GL.trace_env(base, root, trace)
    proc = subprocess.run(list(gate.argv), cwd=gate.cwd, env=env, capture_output=True, text=True)
    return proc.returncode, trace


def _prove_static(book, gate):
    """Store a PASS whose run read nothing, so the static walk alone has to name the input."""
    return book.record(gate, True, trace={"R": set(), "W": set(), "S": set(), "L": set(), "I": set()})


def _prove(book, gate):
    """Store a PASS for what one traced run of this fixture read (its verdict is the test's premise)."""
    _rc, trace = _run_traced(gate)
    try:
        return book.record(gate, True, trace=trace)
    finally:
        os.remove(trace)


def _drop_git_env(case):
    """REG-2360 / REG-2392 - a push from a LINKED WORKTREE runs the hook with GIT_DIR exported (absolute,
    <main>/.git/worktrees/<name>), and GIT_DIR beats cwd= and -C: `_tree`'s throwaway `git init` / `config` / `add` /
    `commit` would re-initialise the REAL repo's common config (core.bare=true) and write its index and push branch, and
    the ledger's own git calls would answer for the real repo. Dropped for THIS case only; addCleanup puts them back."""
    _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith("GIT_")}
    case.addCleanup(os.environ.update, _gitenv)


class TheLedgerCarriesOnlyIdenticalBytes(unittest.TestCase):
    def setUp(self):
        _drop_git_env(self)
        self.held = _Env(GITHUB_ACTIONS=None, GATE_LEDGER=None,
                         TV_SELF_ARMING_LEDGER=os.path.join(tempfile.mkdtemp(prefix="gledger-arm."), "arm.json"))
        self.held.__enter__()
        self.addCleanup(self.held.__exit__, None, None, None)

    def _law(self, extra=None):
        files = {"t_carry.py": _LAW, "helper_gl.py": _HELPER, "unrelated.py": "a\n"}
        if extra:
            files.update(extra)
        root, led = _tree(files)
        self.addCleanup(shutil.rmtree, root, True)
        return root, led, _gate(root, "t_carry.py")

    def test_an_edited_input_runs_again(self):
        root, led, gate = self._law()
        book = _open(led)
        self.assertTrue(_prove(book, gate), "PREMISE: the PASS was not stored")
        with io.open(os.path.join(root, "tv", "helper_gl.py"), "a", encoding="utf-8") as fh:
            fh.write("# moved\n")
        entry, why = book.lookup(gate)
        self.assertIsNone(entry, "an edited input was carried: %s" % why)

    def test_an_unrelated_edit_is_carried(self):
        root, led, gate = self._law()
        book = _open(led)
        self.assertTrue(_prove(book, gate), "PREMISE: the PASS was not stored")
        with io.open(os.path.join(root, "tv", "unrelated.py"), "a", encoding="utf-8") as fh:
            fh.write("b\n")
        entry, why = book.lookup(gate)
        self.assertIsNotNone(entry, why)
        self.assertTrue(str(entry.get("line") or "").startswith("proven at "), entry)
        self.assertNotIn("PASS", entry["line"])
        with io.open(led, encoding="utf-8") as fh:
            self.assertNotIn(root, fh.read())

    def test_a_fail_is_not_stored_and_a_later_fail_drops_the_pass(self):
        root, led, gate = self._law()
        book = _open(led)
        self.assertFalse(book.record(gate, False))
        entry, _why = book.lookup(gate)
        self.assertIsNone(entry, "record(False) left a row that carries")
        self.assertTrue(_prove(book, gate))
        self.assertFalse(book.record(gate, False))
        entry, _why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a FAIL left the earlier PASS in place")

    def test_a_stored_fail_row_is_not_carried(self):
        root, led, gate = self._law()
        book = _open(led)
        self.assertTrue(_prove(book, gate), "PREMISE: the PASS was not stored")
        with io.open(led, encoding="utf-8") as fh:
            data = json.load(fh)
        data["entries"][gate.name]["ok"] = False
        with io.open(led, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        entry, _why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a row with ok false was carried")

    def test_a_tampered_row_and_a_corrupt_ledger_both_run(self):
        root, led, gate = self._law()
        book = _open(led)
        self.assertTrue(_prove(book, gate))
        with io.open(led, encoding="utf-8") as fh:
            data = json.load(fh)
        data["entries"][gate.name]["def"] = "0" * 64
        with io.open(led, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        entry, _why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a row whose definition was rewritten was carried")
        with io.open(led, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        entries, why = GL.load(led)
        self.assertIsNone(entries)
        self.assertIn("unreadable", why or "")
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry)
        self.assertIn("unreadable", why or "")

    def test_a_missing_ledger_is_empty_and_an_unknown_key_runs(self):
        root, led, gate = self._law()
        self.assertEqual(GL.load(led + ".absent"), ({}, None))
        entry, _why = _open(led).lookup(gate)
        self.assertIsNone(entry)

    def test_python_node_and_playwright_versions_enter_the_key(self):
        root, led, gate = self._law()
        a = _open(led, {"python": "3.9.9", "node": "v20.0.0", "playwright": "1.40.0"})
        b = _open(led, {"python": "3.12.1", "node": "v20.0.0", "playwright": "1.40.0"})
        ka, _m, wa = a.key_for(gate)
        kb, _m, wb = b.key_for(gate)
        self.assertIsNone(wa, wa)
        self.assertIsNone(wb, wb)
        self.assertNotEqual(ka, kb, "two python versions produced one key")
        node = _gate(root, "t_node.js", argv_head=["node"])
        with io.open(os.path.join(root, "tv", "t_node.js"), "w", encoding="utf-8") as fh:
            fh.write(_NODE)
        na = _open(led).key_for(node)[0]
        nb = _open(led, {"python": "3.9.9", "node": "v18.0.0", "playwright": "1.40.0"}).key_for(node)[0]
        self.assertTrue(na and nb)
        self.assertNotEqual(na, nb, "two node versions produced one key")
        pw = _gate(root, "t_pw.py")
        with io.open(os.path.join(root, "tv", "t_pw.py"), "w", encoding="utf-8") as fh:
            fh.write(_PW)
        pa = _open(led).key_for(pw)[0]
        pb = _open(led, {"python": "3.9.9", "node": "v20.0.0", "playwright": "1.41.0"}).key_for(pw)[0]
        self.assertTrue(pa and pb)
        self.assertNotEqual(pa, pb, "two playwright versions produced one key")

    def test_a_missing_tool_version_is_unkeyable(self):
        root, led, _gate_py = self._law()
        bare = _open(led, {"python": None, "node": "v20.0.0", "playwright": "1.40.0"})
        key, _m, why = bare.key_for(_gate(root, "t_carry.py"))
        self.assertIsNone(key)
        self.assertIn("python", why or "")
        with io.open(os.path.join(root, "tv", "t_node.js"), "w", encoding="utf-8") as fh:
            fh.write(_NODE)
        key, _m, why = _open(led, {"python": "3.9.9", "node": None, "playwright": "1.40.0"}).key_for(
            _gate(root, "t_node.js", argv_head=["node"]))
        self.assertIsNone(key)
        self.assertIn("node", why or "")
        with io.open(os.path.join(root, "tv", "t_pw.py"), "w", encoding="utf-8") as fh:
            fh.write(_PW)
        key, _m, why = _open(led, {"python": "3.9.9", "node": "v20.0.0", "playwright": None}).key_for(
            _gate(root, "t_pw.py"))
        self.assertIsNone(key)
        self.assertIn("playwright", why or "")

    def test_a_definition_change_and_a_listing_law_do_not_carry(self):
        root, led, gate = self._law()
        slow = _G(gate.name, gate.argv, timeout=31, cwd=gate.cwd)
        ka, _m, wa = _open(led).key_for(gate)
        kb, _m, wb = _open(led).key_for(slow)
        self.assertIsNone(wa, wa)
        self.assertNotEqual(ka, kb, "timeout 30 and 31 produced one key")
        with io.open(os.path.join(root, "tv", "t_list.py"), "w", encoding="utf-8") as fh:
            fh.write(_LISTING)
        listing = _gate(root, "t_list.py")
        key, _m, why = _open(led).key_for(listing)
        # v3775 (REG-2296): a listing law is keyed by what its traced run listed
        self.assertIsNotNone(key, why)

    def test_ci_and_the_off_switch_never_carry(self):
        root, led, gate = self._law()
        book = _open(led)
        self.assertTrue(_prove(book, gate), "PREMISE: the PASS was not stored")
        os.environ["GATE_LEDGER"] = "0"
        try:
            entry, why = _open(led).lookup(gate)
        finally:
            os.environ.pop("GATE_LEDGER", None)
        self.assertIsNone(entry, "GATE_LEDGER=0 carried a PASS")
        self.assertIn("GATE_LEDGER", why or "")
        os.environ["GITHUB_ACTIONS"] = "true"
        try:
            entry, why = _open(led).lookup(gate)
        finally:
            os.environ.pop("GITHUB_ACTIONS", None)
        self.assertIsNone(entry, "CI carried a PASS")
        self.assertIn("CI", why or "")

    def test_a_committed_input_edit_runs_again(self):
        root, led, gate = self._law()
        book = _open(led)
        self.assertTrue(_prove(book, gate), "PREMISE: the PASS was not stored")
        with io.open(os.path.join(root, "tv", "helper_gl.py"), "a", encoding="utf-8") as fh:
            fh.write("# committed\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "edit the input")
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a committed input edit was carried: %s" % why)

    def test_an_unreachable_proven_sha_runs(self):
        root, led, gate = self._law()
        book = _open(led)
        self.assertTrue(_prove(book, gate), "PREMISE: the PASS was not stored")
        with io.open(led, encoding="utf-8") as fh:
            data = json.load(fh)
        data["proven_sha"] = "deadbeef" * 5
        data["entries"][gate.name]["sha"] = data["proven_sha"]
        with io.open(led, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "an unreachable sha was carried: %s" % why)
        self.assertIn("diffed", why or "")

    def test_a_carry_does_not_open_the_inputs(self):
        root, led, gate = self._law()
        book = _open(led)
        self.assertTrue(_prove(book, gate), "PREMISE: the PASS was not stored")
        self.assertGreater(book.reads, 0, "PREMISE: recording never named the inputs")
        import heart2
        fresh = _open(led)

        def _boom(*_a, **_k):
            raise AssertionError("a carry hashed an input file")

        old = heart2._sha_file
        heart2._sha_file = _boom
        try:
            entry, why = fresh.lookup(gate)
        finally:
            heart2._sha_file = old
        self.assertIsNotNone(entry, why)
        self.assertEqual(fresh.reads, 0, "a carry opened the gate's inputs")

    def test_the_input_map_key_covers_the_runner_and_the_blueprint(self):
        root, led, _gate_py = self._law()
        tv = os.path.join(root, "tv")
        with io.open(os.path.join(tv, "run_gates.py"), "w", encoding="utf-8") as fh:
            fh.write("RUN = 1\n")
        with io.open(os.path.join(root, "BLUEPRINT.md"), "w", encoding="utf-8") as fh:
            fh.write("blue\n")
        first = GL.map_key(root)
        with io.open(os.path.join(root, "BLUEPRINT.md"), "a", encoding="utf-8") as fh:
            fh.write("more\n")
        second = GL.map_key(root)
        self.assertNotEqual(first, second, "editing the blueprint left the map key unchanged")
        with io.open(os.path.join(tv, "run_gates.py"), "a", encoding="utf-8") as fh:
            fh.write("RUN = 2\n")
        third = GL.map_key(root)
        self.assertNotEqual(second, third, "editing the runner left the map key unchanged")
        with io.open(os.path.join(tv, "heart2.py"), "w", encoding="utf-8") as fh:
            fh.write("H = 1\n")
        fourth = GL.map_key(root)
        with io.open(os.path.join(tv, "heart2.py"), "a", encoding="utf-8") as fh:
            fh.write("H = 2\n")
        fifth = GL.map_key(root)
        self.assertNotEqual(fourth, fifth, "editing heart2.py left the map key unchanged")

    def test_a_carry_does_not_bank_evidence(self):
        root, led, gate = self._law()
        book = _open(led)
        self.assertTrue(_prove(book, gate))
        import self_arming
        import vault_wilson
        seen = {"bank": 0, "queue": 0}

        def _bank(*a, **k):
            seen["bank"] += 1
            return {}

        def _queue(*a, **k):
            seen["queue"] += 1
            return None

        old_b, old_q = self_arming.bank, vault_wilson.bank_into_proof_queue
        self_arming.bank = _bank
        vault_wilson.bank_into_proof_queue = _queue
        try:
            entry, why = book.lookup(gate)
            self.assertIsNotNone(entry, why)
            self.assertEqual(seen["bank"], 0, "a carry called self_arming.bank")
            self.assertEqual(seen["queue"], 0, "a carry called vault_wilson.bank_into_proof_queue")
        finally:
            self_arming.bank = old_b
            vault_wilson.bank_into_proof_queue = old_q

    def _commit_import(self, root, filename):
        with io.open(os.path.join(root, "tv", filename), "a", encoding="utf-8") as fh:
            fh.write("import newbie\n")
        with io.open(os.path.join(root, "tv", "newbie.py"), "w", encoding="utf-8") as fh:
            fh.write("N = 1\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "gain an import")

    def test_a_script_that_gained_an_import_is_not_carried_from_a_stale_map(self):
        root, led, gate = self._law()
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the PASS was not stored")
        self._commit_import(root, "t_carry.py")
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the refreshed PASS was not stored")
        with io.open(os.path.join(root, "tv", "newbie.py"), "a", encoding="utf-8") as fh:
            fh.write("N = 2\n")
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a new import's file was carried: %s" % why)

    def test_a_helper_that_grew_an_import_is_not_carried_from_a_stale_map(self):
        root, led, gate = self._law()
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the PASS was not stored")
        self._commit_import(root, "helper_gl.py")
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the refreshed PASS was not stored")
        with io.open(os.path.join(root, "tv", "newbie.py"), "a", encoding="utf-8") as fh:
            fh.write("N = 2\n")
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a helper's new import was carried: %s" % why)

    def test_a_fresh_pass_at_a_new_head_does_not_drop_the_other_carries(self):
        root, led, gate = self._law()
        other = _gate(root, "unrelated.py")
        other.name = "other-fixture"
        book = _open(led)
        self.assertTrue(_prove(book, gate), "PREMISE: the first PASS was not stored")
        self.assertTrue(_prove(book, other), "PREMISE: the second PASS was not stored")
        with io.open(os.path.join(root, "tv", "note.py"), "w", encoding="utf-8") as fh:
            fh.write("x = 1\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "unrelated commit")
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the new HEAD did not store a PASS")
        entry, why = _open(led).lookup(other)
        self.assertIsNotNone(entry, why)
        self.assertTrue(str(entry.get("line") or "").startswith("proven at "), entry)

    def test_bible_html_is_not_inherited_from_an_imported_string(self):
        root, led, gate = self._law(extra={"namer.py": "PATH = 'bible.html'\n"})
        bible = os.path.join(root, "bible.html")
        with io.open(bible, "w", encoding="utf-8") as fh:
            fh.write("<html></html>\n")
        with io.open(os.path.join(root, "tv", "t_carry.py"), "w", encoding="utf-8") as fh:
            fh.write("import namer\nimport sys\nsys.exit(0)\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "name the page")
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the PASS was not stored")
        with io.open(bible, "a", encoding="utf-8") as fh:
            fh.write("<!-- moved -->\n")
        entry, why = _open(led).lookup(gate)
        self.assertIsNotNone(entry, why)
        with io.open(os.path.join(root, "tv", "t_carry.py"), "w", encoding="utf-8") as fh:
            fh.write("import namer\nopen('bible.html')\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "the gate opens the page")
        reader = _gate(root, "t_carry.py")
        self.assertTrue(_prove(_open(led), reader), "PREMISE: the reader was not stored")
        with io.open(bible, "a", encoding="utf-8") as fh:
            fh.write("<!-- again -->\n")
        entry, why = _open(led).lookup(reader)
        self.assertIsNone(entry, "a gate that opens bible.html carried the edit: %s" % why)

    def test_a_callee_in_an_imported_module_opens_bible(self):
        opener = (
            "PATH = 'bible.html'\n"
            "def read():\n"
            "    open('bible.html')\n"
            "def mid():\n"
            "    read()\n"
            "def read_path():\n"
            "    open(PATH)\n"
        )
        root, led, _gate_py = self._law(extra={"opener.py": opener})
        bible = os.path.join(root, "bible.html")
        tv = os.path.join(root, "tv")
        with io.open(bible, "w", encoding="utf-8") as fh:
            fh.write("<html></html>\n")
        with io.open(os.path.join(tv, "gate_call.py"), "w", encoding="utf-8") as fh:
            fh.write("import opener\ndef go():\n    opener.mid()\ngo()\n")
        with io.open(os.path.join(tv, "gate_path.py"), "w", encoding="utf-8") as fh:
            fh.write("import opener\ndef go():\n    opener.read_path()\ngo()\n")
        with io.open(os.path.join(tv, "gate_dyn.py"), "w", encoding="utf-8") as fh:
            fh.write("import opener\ndef go():\n    getattr(opener, 'mid')()\ngo()\n")
        with io.open(os.path.join(tv, "gate_import.py"), "w", encoding="utf-8") as fh:
            fh.write("import opener\nimport sys\nsys.exit(0)\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "callee opens the page")
        call = _gate(root, "gate_call.py")
        call.name = "call-mid"
        path = _gate(root, "gate_path.py")
        path.name = "call-path"
        dyn = _gate(root, "gate_dyn.py")
        dyn.name = "call-dyn"
        only = _gate(root, "gate_import.py")
        only.name = "import-only"
        book = _open(led)
        self.assertTrue(_prove(book, call), "PREMISE: the transitive call was not stored")
        self.assertTrue(_prove(book, path), "PREMISE: the path open was not stored")
        self.assertTrue(_prove(book, dyn), "PREMISE: the dynamic call was not stored")
        self.assertTrue(_prove(book, only), "PREMISE: the import was not stored")
        with io.open(bible, "a", encoding="utf-8") as fh:
            fh.write("<!-- moved -->\n")
        book = _open(led)
        entry, why = book.lookup(call)
        self.assertIsNone(entry, "a callee in an imported module opens bible.html and the edit carried: %s" % why)
        entry, why = book.lookup(path)
        self.assertIsNone(entry, "open(PATH) in an imported module carried the edit: %s" % why)
        entry, why = book.lookup(dyn)
        self.assertIsNone(entry, "getattr on a module that opens bible.html carried the edit: %s" % why)
        entry, why = book.lookup(only)
        self.assertIsNotNone(entry, why)

    def test_a_self_attribute_holding_an_imported_module_opens_bible(self):
        opener = (
            "PATH = 'bible.html'\n"
            "def read():\n"
            "    open('bible.html')\n"
        )
        root, led, _gate_py = self._law(extra={"opener.py": opener})
        bible = os.path.join(root, "bible.html")
        tv = os.path.join(root, "tv")
        with io.open(bible, "w", encoding="utf-8") as fh:
            fh.write("<html></html>\n")
        with io.open(os.path.join(tv, "gate_self.py"), "w", encoding="utf-8") as fh:
            fh.write(
                "import opener\n"
                "class Box(object):\n"
                "    def setUp(self):\n"
                "        self.ca = opener\n"
                "    def go(self):\n"
                "        self.ca.read()\n"
                "Box().go()\n"
            )
        with io.open(os.path.join(tv, "gate_alias.py"), "w", encoding="utf-8") as fh:
            fh.write(
                "class Box(object):\n"
                "    def setUp(self):\n"
                "        import opener as ca\n"
                "        self.ca = ca\n"
                "    def go(self):\n"
                "        self.ca.read()\n"
                "Box().go()\n"
            )
        with io.open(os.path.join(tv, "gate_cls.py"), "w", encoding="utf-8") as fh:
            fh.write(
                "import opener\n"
                "class Box(object):\n"
                "    def setUp(cls):\n"
                "        cls.ca = opener\n"
                "    def go(cls):\n"
                "        cls.ca.read()\n"
                "Box().go()\n"
            )
        with io.open(os.path.join(tv, "gate_hold.py"), "w", encoding="utf-8") as fh:
            fh.write(
                "import opener\n"
                "class Box(object):\n"
                "    def setUp(self):\n"
                "        self.ca = opener\n"
                "    def go(self):\n"
                "        return 1\n"
                "Box().go()\n"
            )
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "self holds the module")
        gates = []
        for name, label in (
            ("gate_self.py", "self-ca"),
            ("gate_alias.py", "self-alias"),
            ("gate_cls.py", "cls-ca"),
            ("gate_hold.py", "hold-only"),
        ):
            gate = _gate(root, name)
            gate.name = label
            gates.append(gate)
        book = _open(led)
        for gate in gates:
            self.assertTrue(_prove(book, gate), "PREMISE: %s was not stored" % gate.name)
        with io.open(bible, "a", encoding="utf-8") as fh:
            fh.write("<!-- moved -->\n")
        book = _open(led)
        for gate in gates[:3]:
            entry, why = book.lookup(gate)
            self.assertIsNone(
                entry, "self.ca = opener; self.ca.read() carried the bible.html edit (%s): %s" % (gate.name, why))
        entry, why = book.lookup(gates[3])
        self.assertIsNotNone(entry, why)

    def test_a_module_that_escapes_into_code_the_walk_cannot_follow_opens_bible(self):
        opener = (
            "PATH = 'bible.html'\n"
            "def read():\n"
            "    open('bible.html')\n"
        )
        root, led, _gate_py = self._law(extra={"opener.py": opener})
        bible = os.path.join(root, "bible.html")
        tv = os.path.join(root, "tv")
        with io.open(bible, "w", encoding="utf-8") as fh:
            fh.write("<html></html>\n")
        shapes = (
            ("gate_tuple.py", "tuple-self",
             "import opener\n"
             "class Box(object):\n"
             "    def setUp(self):\n"
             "        self.ca, self.n = opener, 1\n"
             "    def go(self):\n"
             "        self.ca.read()\n"
             "Box().go()\n"),
            ("gate_kid.py", "subclass",
             "import opener\n"
             "class Base(object):\n"
             "    def setUp(self):\n"
             "        self.ca = opener\n"
             "class Kid(Base):\n"
             "    def go(self):\n"
             "        self.ca.read()\n"
             "Kid().go()\n"),
            ("gate_ret.py", "returned",
             "def _ca():\n"
             "    import opener as ca\n"
             "    return ca\n"
             "_ca().read()\n"),
            ("gate_local.py", "local-alias",
             "import opener\n"
             "def go():\n"
             "    c = opener\n"
             "    c.read()\n"
             "go()\n"),
            ("gate_arg.py", "argument",
             "import opener\n"
             "def run(m):\n"
             "    m.read()\n"
             "run(opener)\n"),
            ("gate_look.py", "inspect-only",
             "import inspect\n"
             "import opener\n"
             "assert hasattr(opener, 'read')\n"
             "inspect.getsource(opener)\n"),
        )
        for name, _label, body in shapes:
            with io.open(os.path.join(tv, name), "w", encoding="utf-8") as fh:
                fh.write(body)
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "the module escapes")
        gates = []
        for name, label, _body in shapes:
            gate = _gate(root, name)
            gate.name = label
            gates.append(gate)
        book = _open(led)
        for gate in gates:
            self.assertTrue(_prove_static(book, gate), "PREMISE: %s was not stored" % gate.name)
        with io.open(bible, "a", encoding="utf-8") as fh:
            fh.write("<!-- moved -->\n")
        book = _open(led)
        for gate in gates[:-1]:
            entry, why = book.lookup(gate)
            self.assertIsNone(
                entry, "the module escaped (%s) and the bible.html edit was carried: %s" % (gate.name, why))
        entry, why = book.lookup(gates[-1])
        self.assertIsNotNone(entry, "hasattr/getsource never call the module, so it carries: %s" % why)

    def test_the_runner_file_is_not_an_input_of_every_gate(self):
        root, led, _gate_py = self._law(extra={"namer.py": "PATH = 'run_gates.py'\n"})
        tv = os.path.join(root, "tv")
        with io.open(os.path.join(tv, "t_carry.py"), "w", encoding="utf-8") as fh:
            fh.write("import namer\nimport sys\nsys.exit(0)\n")
        with io.open(os.path.join(tv, "run_gates.py"), "w", encoding="utf-8") as fh:
            fh.write("GATES = []\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "name the runner")
        gate = _gate(root, "t_carry.py")
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the PASS was not stored")
        with io.open(os.path.join(tv, "run_gates.py"), "a", encoding="utf-8") as fh:
            fh.write("GATES.append(1)\n")
        entry, why = _open(led).lookup(gate)
        self.assertIsNotNone(entry, why)
        with io.open(os.path.join(tv, "t_carry.py"), "w", encoding="utf-8") as fh:
            fh.write("import namer\nimport run_gates\nimport sys\nsys.exit(0)\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "the gate imports the runner")
        reader = _gate(root, "t_carry.py")
        self.assertTrue(_prove(_open(led), reader), "PREMISE: the importer was not stored")
        with io.open(os.path.join(tv, "run_gates.py"), "a", encoding="utf-8") as fh:
            fh.write("GATES.append(2)\n")
        entry, why = _open(led).lookup(reader)
        self.assertIsNone(entry, "a gate that imports the runner carried the edit: %s" % why)

    def test_a_file_named_only_inside_the_runner_is_not_every_gates_input(self):
        root, led, _gate_py = self._law(extra={"namer.py": "import run_gates\n"})
        tv = os.path.join(root, "tv")
        with io.open(os.path.join(tv, "t_carry.py"), "w", encoding="utf-8") as fh:
            fh.write("import namer\nimport sys\nsys.exit(0)\n")
        with io.open(os.path.join(tv, "run_gates.py"), "w", encoding="utf-8") as fh:
            fh.write("OTHER = 'other_gate.py'\n")
        with io.open(os.path.join(tv, "other_gate.py"), "w", encoding="utf-8") as fh:
            fh.write("N = 1\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "the runner names another file")
        gate = _gate(root, "t_carry.py")
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the PASS was not stored")
        with io.open(os.path.join(tv, "other_gate.py"), "a", encoding="utf-8") as fh:
            fh.write("N = 2\n")
        entry, why = _open(led).lookup(gate)
        self.assertIsNotNone(entry, why)

    def test_a_declared_glob_matches_a_new_file(self):
        self.assertTrue(GL._watched("tv/brand_new.py", ("tv/*.py",)))
        self.assertFalse(GL._watched("bible.html", ("tv/*.py",)))

    def test_test_agent_is_nameable_because_its_listings_are_temp_dirs(self):
        root, led, _gate_py = self._law(extra={"t_list.py": _LISTING})
        gate = _gate(root, "t_list.py")
        gate.name = "test_agent"
        self.assertTrue(_prove(_open(led), gate), "PREMISE: test_agent was not stored")
        with io.open(os.path.join(root, "tv", "brand_new.py"), "w", encoding="utf-8") as fh:
            fh.write("N = 1\n")
        entry, why = _open(led).lookup(gate)
        self.assertIsNotNone(entry, why)

    def test_test_control_is_keyed_by_its_traced_listings(self):
        """v3775 (REG-2296): test_control's footage listing is keyed by the trace's snapshot."""
        root, led, _gate_py = self._law(extra={"t_list.py": _LISTING})
        gate = _gate(root, "t_list.py")
        gate.name = "test_control"
        self.assertTrue(_prove(_open(led), gate), "a listing of temp dirs only was refused")

    def test_record_does_not_mint_a_pass_without_a_suite_verdict(self):
        root, _led, _gate_py = self._law()
        ok, why = GL.verdict_allows("test_agent", root)
        self.assertFalse(ok, why)
        import suite_verdict as SV
        key, why = SV.tree_key(root)
        self.assertTrue(key, why)
        path = SV.store_path(root)
        self.assertTrue(path, "the fixture has no suite-verdict store")
        self.assertTrue(SV.record("test_agent", key, True, path=path))
        ok, why = GL.verdict_allows("test_agent", root)
        self.assertTrue(ok, why)
        self.assertFalse(GL.verdict_allows("test_control", root)[0])
        self.assertFalse(GL.verdict_allows("test_tz_art", root)[0])


def _write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _commit(root, msg="change"):
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", msg)


class TheProofRemembersWhatTheGateRead(unittest.TestCase):
    """REG-2293 round 5: the four carries the round-4 look reproduced, plus an untracked folder.

    Each one is the reviewer's scenario cut down to a fixture: the inputs a gate is checked
    against are the ones its passing run read (stored with the PASS) together with today's walk."""

    def setUp(self):
        _drop_git_env(self)
        self.held = _Env(GITHUB_ACTIONS=None, GATE_LEDGER=None)
        self.held.__enter__()
        self.addCleanup(self.held.__exit__, None, None, None)

    def _tree(self, files, extra=None):
        root, led = _tree(files)
        self.addCleanup(shutil.rmtree, root, True)
        for rel, text in (extra or {}).items():
            _write(root, rel, text)
        if extra:
            _commit(root, "extra")
        return root, led

    def test_a_deleted_fixture_the_gate_read_runs_again(self):
        law = ("import os, sys\nHERE = os.path.dirname(os.path.abspath(__file__))\n"
               "p = os.path.join(HERE, 'seed_gl.json')\n"
               "sys.exit(0 if os.path.exists(p) and open(p).read() else 1)\n")
        root, led = self._tree({"t_seed.py": law, "seed_gl.json": "{}\n"})
        gate = _gate(root, "t_seed.py")
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the PASS was not stored")
        _git(root, "rm", "-q", "tv/seed_gl.json")
        _commit(root, "drop the seed")
        self.assertNotEqual(_run_traced(gate)[0], 0, "PREMISE: the gate is not red without its seed")
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a deleted input carried a red gate")
        self.assertIn("seed_gl.json", why or "")

    def test_a_deleted_module_runs_again(self):
        root, led = self._tree({"t_mod.py": "import helper_gl\nprint('OK')\n", "helper_gl.py": "X = 1\n"})
        gate = _gate(root, "t_mod.py")
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the PASS was not stored")
        _git(root, "rm", "-q", "tv/helper_gl.py")
        _commit(root, "drop the module")
        self.assertNotEqual(_run_traced(gate)[0], 0, "PREMISE: the gate is not red without its module")
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a deleted module carried a ModuleNotFoundError")

    def test_a_new_module_the_gate_tried_to_import_runs_again(self):
        law = ("import sys\ntry:\n    import maybe_gl\nexcept ImportError:\n    maybe_gl = None\n"
               "sys.exit(0 if maybe_gl is None or maybe_gl.OK else 1)\n")
        root, led = self._tree({"t_try.py": law})
        gate = _gate(root, "t_try.py")
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the PASS was not stored")
        _write(root, "tv/maybe_gl.py", "OK = False\n")
        _commit(root, "the import now resolves")
        self.assertNotEqual(_run_traced(gate)[0], 0, "PREMISE: the gate is not red with the new module")
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a module that now resolves was carried")
        self.assertIn("maybe_gl.py", why or "")

    def test_a_submodule_served_from_a_cached_pyc_is_an_input(self):
        """r5 B: with the bytecode cache warm, importlib opens only the .pyc, so the .py read was never seen.

        The cache is warmed under a prefix this case owns, set for the whole case, so a trace run that lost
        LEDGER-TRACE-NOPYC reads exactly the cache warmed here. It was `__pycache__`, and his Mac's python3 has a
        BUILT-IN pycache_prefix (~/Library/Caches/com.apple.python; an empty PYTHONPYCACHEPREFIX does not clear it):
        there `__pycache__` is never written, so this premise failed on every run on his Mac."""
        law = ("import importlib, os\n"
               "m = importlib.import_module('pkg_gl.sub' + '_gl')\n"
               "os._exit(0 if m.OK else 1)\n")
        root, led = self._tree({"t_pyc.py": law}, {"tv/pkg_gl/__init__.py": "", "tv/pkg_gl/sub_gl.py": "OK = True\n"})
        gate = _gate(root, "t_pyc.py")
        prefix = tempfile.mkdtemp(prefix="gl-pyc.")
        self.addCleanup(shutil.rmtree, prefix, True)
        held = _Env(PYTHONPYCACHEPREFIX=prefix)
        held.__enter__()
        self.addCleanup(held.__exit__, None, None, None)
        warm = subprocess.run(list(gate.argv), cwd=root, capture_output=True,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE=""))
        self.assertEqual(warm.returncode, 0, "PREMISE: the gate is not green")
        # realpath: python puts a script's own folder on sys.path resolved (/var is /private/var on his Mac)
        pyc = subprocess.run([sys.executable, "-c", "import importlib.util, sys; "
                              "print(importlib.util.cache_from_source(sys.argv[1]))",
                              os.path.realpath(os.path.join(root, "tv", "pkg_gl", "sub_gl.py"))],
                             capture_output=True, encoding="utf-8", errors="replace", env=dict(os.environ)).stdout.strip()
        self.assertTrue(pyc.startswith(prefix) and os.path.isfile(pyc), "PREMISE: no .pyc cache (%s)" % pyc)
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the PASS was not stored")
        _write(root, "tv/pkg_gl/sub_gl.py", "OK = False\n")
        _commit(root, "break the submodule")
        self.assertNotEqual(_run_traced(gate)[0], 0, "PREMISE: the gate is not red after the edit")
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a module imported from its .pyc carried a red gate")
        self.assertIn("sub_gl.py", why or "")

    def test_an_imported_name_is_its_tracked_source(self):
        """r5 B2: a python child imported dep_gl; the name alone must make tv/dep_gl.py an input."""
        root, _led = self._tree({"t_x.py": "print('OK')\n", "dep_gl.py": "X = 1\n"})
        traced, why = _open(os.path.join(root, ".gate_ledger.json"))._traced_inputs(
            {"R": set(), "S": set(), "A": set(), "L": set(), "I": {"dep_gl"}, "M": set()}, root)
        self.assertIsNone(why)
        self.assertIn("tv/dep_gl.py", traced["inputs"], "an imported module's source is not an input")

    def test_reads_on_other_threads_are_all_seen(self):
        """r5 A: one process-wide busy flag dropped opens made on thread B while A was in the hook."""
        law = ("import os, sys\nfrom concurrent.futures import ThreadPoolExecutor\n"
               "HERE = os.path.dirname(os.path.abspath(__file__))\n"
               "import threading\nGO = threading.Barrier(64)\n"
               "def rd(i):\n    GO.wait()\n    with open(os.path.join(HERE, 'th', 'f%d.txt' % i)) as fh:\n        return fh.read()\n"
               "with ThreadPoolExecutor(64) as ex:\n    out = list(ex.map(rd, range(64)))\n"
               "sys.exit(0 if all(x == 'ok' for x in out) else 1)\n")
        root, led = self._tree({"t_th.py": law}, dict(("tv/th/f%d.txt" % i, "ok") for i in range(64)))
        gate = _gate(root, "t_th.py")
        _rc, trace = _run_traced(gate)
        try:
            facts, why = GL.read_trace(trace)
        finally:
            os.remove(trace)
        self.assertIsNone(why)
        missing = [i for i in range(64) if "tv/th/f%d.txt" % i not in facts["R"]]
        self.assertEqual(missing, [], "reads made on other threads were not traced")

    def test_os_access_on_an_absent_file_is_an_input(self):
        """r5 C: `not os.access(p, F_OK)` stored nothing, so adding the file carried a red gate."""
        law = ("import os, sys\nHERE = os.path.dirname(os.path.abspath(__file__))\n"
               "sys.exit(1 if os.access(os.path.join(HERE, 'zz_flag'), os.F_OK) else 0)\n")
        root, led = self._tree({"t_acc.py": law})
        gate = _gate(root, "t_acc.py")
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the PASS was not stored")
        _write(root, "tv/zz_flag", "x\n")
        _commit(root, "the flag appears")
        self.assertNotEqual(_run_traced(gate)[0], 0, "PREMISE: the gate is not red with the flag")
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a file probed with os.access carried a red gate")

    def test_readlink_and_realpath_are_probes(self):
        law = ("import os\nHERE = os.path.dirname(os.path.abspath(__file__))\n"
               "os.path.realpath(os.path.join(HERE, 'zz_rp'))\n"
               "try:\n    os.readlink(os.path.join(HERE, 'zz_rl'))\nexcept OSError:\n    pass\nprint('OK')\n")
        root, _led = self._tree({"t_rp.py": law})
        _rc, trace = _run_traced(_gate(root, "t_rp.py"))
        try:
            facts, _why = GL.read_trace(trace)
        finally:
            os.remove(trace)
        seen = facts["S"] | facts["A"]
        self.assertIn("tv/zz_rp", seen, "os.path.realpath is not traced")
        self.assertIn("tv/zz_rl", seen, "os.readlink is not traced")

    def test_the_consoles_own_dirty_record_neither_blocks_nor_stops_a_carry(self):
        """r5 speed: the running console rewrites tv/.status_worst.json, which 29 of 32 real gates read."""
        law = ("import os\nHERE = os.path.dirname(os.path.abspath(__file__))\n"
               "open(os.path.join(HERE, '.status_worst.json')).read()\nprint('OK')\n")
        root, led = self._tree({"t_sw.py": law, ".status_worst.json": "{}\n"})
        gate = _gate(root, "t_sw.py")
        _write(root, "tv/.status_worst.json", '{"ms": 9}\n')
        book = _open(led)
        self.assertTrue(_prove(book, gate), "the console's own record blocked the record: %s" % book.last_why)
        entry, why = _open(led).lookup(gate)
        self.assertIsNotNone(entry, "the console's own record stopped the carry: %s" % why)

    def test_a_pass_dropped_for_a_listing_law_says_why(self):
        """r5: 8 real passes were dropped for "lists a directory itself" and run_gates printed nothing."""
        root, led = self._tree({"t_ls.py": _LISTING})
        book = _open(led)
        # v3775 (REG-2296): a listing law is stored from its trace now, and says nothing
        self.assertTrue(_prove(book, _gate(root, "t_ls.py")), book.last_why)
        self.assertIsNone(book.last_why)
        # a gate that still cannot be named (a node script that lists a directory) is dropped AND says why
        _write(root, "tv/t_ls.js", "require('fs').readdirSync('.');\n")
        _commit(root, "a node listing")
        node = _gate(root, "t_ls.js", argv_head=["node"])
        key, _m, why = _open(led).key_for(node)
        self.assertIsNone(key, "a node listing got a key")
        self.assertIn("lists a directory", why or "")
        book = _open(led)
        self.assertFalse(_prove_static(book, node), "an unnameable gate was stored")
        self.assertIn("lists a directory", book.last_why or "", "a dropped PASS gave no reason")

    def test_the_pre_push_hook_traces_the_suites_it_records(self):
        """r6: the hook's --record had no trace, so it could never store; now it arms one and hands it over."""
        out = tempfile.mkdtemp(prefix="gl-hook.")
        self.addCleanup(shutil.rmtree, out, True)
        trace = os.path.join(out, "t.tsv")
        buf = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(buf):
            self.assertEqual(GL.main(["gate_ledger.py", "--trace-env", trace]), 0)
        proc = subprocess.run(["bash", "-c", buf.getvalue() + "\n" + shlex.quote(sys.executable) + " -c 'print(1)'"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        facts, why = GL.read_trace(trace)
        self.assertIsNone(why, "the exports the hook evals do not arm the trace")
        with io.open(os.path.join(os.path.dirname(HERE), "hooks", "pre-push"), encoding="utf-8") as fh:
            hook = fh.read()
        for suite in ("test_agent", "test_control"):
            self.assertIn('gate_ledger.py" --record %s --trace "$_tr"' % suite, hook)

    def test_a_pass_proved_on_a_dirty_tree_is_not_stored_under_head(self):
        root, led = self._tree({"t_mod.py": "import sys, helper_gl\nsys.exit(0 if helper_gl.OK else 1)\n",
                                "helper_gl.py": "OK = False\n"})
        gate = _gate(root, "t_mod.py")
        self.assertNotEqual(_run_traced(gate)[0], 0, "PREMISE: the gate is not red at HEAD")
        _write(root, "tv/helper_gl.py", "OK = True\n")
        book = _open(led)
        self.assertFalse(_prove(book, gate), "a PASS on uncommitted bytes was stored under the clean HEAD")
        self.assertIn("uncommitted", book.last_why or "")
        _git(root, "checkout", "-q", "--", "tv/helper_gl.py")
        entry, _why = _open(led).lookup(gate)
        self.assertIsNone(entry, "the red HEAD was carried")

    def test_a_dirty_file_the_gate_does_not_read_does_not_stop_the_record(self):
        root, led = self._tree({"t_mod.py": "import helper_gl\nprint('OK')\n", "helper_gl.py": "X = 1\n",
                                "unrelated.py": "a\n"})
        _write(root, "tv/unrelated.py", "b\n")
        self.assertTrue(_prove(_open(led), _gate(root, "t_mod.py")), "an unrelated dirty file stopped the record")

    def test_a_glob_inside_an_imported_module_sees_a_new_file(self):
        helper = ("import glob, os\nROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
                  "def pinned():\n    out = []\n"
                  "    for p in glob.glob(os.path.join(ROOT, 'tests', '*.spec.ts')):\n"
                  "        out += [l for l in open(p) if 'reel_s_' in l]\n    return out\n")
        law = "import sys, scan_gl\nsys.exit(1 if scan_gl.pinned() else 0)\n"
        root, led = self._tree({"t_pin.py": law, "scan_gl.py": helper}, {"tests/a.spec.ts": "ok\n"})
        gate = _gate(root, "t_pin.py")
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the PASS was not stored")
        _write(root, "tests/zz_pin.spec.ts", "'reel_s" + "_1790000000000_12345'\n")  # split: frame_authority scans tv/*.py
        _commit(root, "pin a reel")
        self.assertNotEqual(_run_traced(gate)[0], 0, "PREMISE: the gate is not red with the pinned reel")
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a new file under a directory the closure globs was carried")
        self.assertIn("zz_pin.spec.ts", why or "")

    def test_a_deleted_file_under_a_listed_directory_runs_again(self):
        helper = ("import os\nROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
                  "def count():\n    return len(os.listdir(os.path.join(ROOT, 'tests')))\n")
        law = "import sys, scan_gl\nsys.exit(0 if scan_gl.count() == 2 else 1)\n"
        root, led = self._tree({"t_cnt.py": law, "scan_gl.py": helper},
                               {"tests/a.spec.ts": "a\n", "tests/b.spec.ts": "b\n"})
        gate = _gate(root, "t_cnt.py")
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the PASS was not stored")
        _git(root, "rm", "-q", "tests/b.spec.ts")
        _commit(root, "drop one")
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a deleted file under a listed directory was carried")

    def test_bible_html_through_a_local_alias_or_a_default_arg_is_an_input(self):
        helper = ("import os\nBIBLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"
                  " 'bible.html')\n"
                  "def seed_table(path=None):\n    p = path or BIBLE\n    return open(p).read()\n"
                  "def size(path=BIBLE):\n    return len(open(path).read())\n")
        law = "import sys, ledger_gl\nsys.exit(0 if 'ok' in ledger_gl.seed_table() and ledger_gl.size() else 1)\n"
        root, led = self._tree({"t_bible.py": law, "ledger_gl.py": helper}, {"bible.html": "<p>ok</p>\n"})
        gate = _gate(root, "t_bible.py")
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the PASS was not stored")
        _write(root, "bible.html", "<p>gone</p>\n")
        _commit(root, "edit the bible")
        self.assertNotEqual(_run_traced(gate)[0], 0, "PREMISE: the gate is not red over the edit")
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a bible.html read through a local alias was carried")
        self.assertIn("bible.html", why or "")

    def test_an_input_inside_an_untracked_folder_is_dirty(self):
        law = ("import os, sys\nHERE = os.path.dirname(os.path.abspath(__file__))\n"
               "sys.exit(0 if open(os.path.join(HERE, 'newpkg_gl', 'seed.json')).read() else 1)\n")
        root, led = self._tree({"t_new.py": law})
        _write(root, "tv/newpkg_gl/seed.json", "{}\n")
        book = _open(led)
        self.assertFalse(_prove(book, _gate(root, "t_new.py")),
                         "a PASS that read a file in an untracked folder was stored")
        self.assertIn("newpkg_gl/seed.json", book.last_why or "")

    def test_no_trace_a_lost_child_and_an_old_row_all_run(self):
        root, led = self._tree({"t_mod.py": "import helper_gl\nprint('OK')\n", "helper_gl.py": "X = 1\n",
                                "t_sh.py": "import subprocess\nsubprocess.run(['uname'])  # not a machine meter: REG-3124 made true inert\n"})
        gate = _gate(root, "t_mod.py")
        book = _open(led)
        self.assertFalse(book.record(gate, True), "a PASS with no trace of its reads was stored")
        self.assertFalse(_prove(_open(led), _gate(root, "t_sh.py")), "a non-python child was carried")
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the PASS was not stored")
        with io.open(led, encoding="utf-8") as fh:
            data = json.load(fh)
        for row in data["entries"].values():
            row.pop("traced", None)
        with io.open(led, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a row stored before reads were traced was carried")

    def test_an_ignored_file_the_gate_read_is_never_carried(self):
        law = ("import os, sys\nHERE = os.path.dirname(os.path.abspath(__file__))\n"
               "sys.exit(0 if os.path.exists(os.path.join(HERE, 'live_gl.json')) else 1)\n")
        root, led = self._tree({"t_live.py": law}, {".gitignore": ".gate_ledger.json\n.gate_inputs.json\n"
                                                                 "*.tmp\nlive_gl.json\n"})
        _write(root, "tv/live_gl.json", "{}\n")
        book = _open(led)
        self.assertFalse(_prove(book, _gate(root, "t_live.py")), "a read of ignored local state was carried")
        self.assertIn("ignores", book.last_why or "")
        cache = ("import os, sys\nHERE = os.path.dirname(os.path.abspath(__file__))\n"
                 "p = os.path.join(HERE, 'live_gl.json')\n"
                 "old = open(p).read() if os.path.exists(p) else ''\n"
                 "open(p + '.tmp', 'w').write('{}')\nos.replace(p + '.tmp', p)\n"
                 "sys.exit(0 if open(p).read() else 1)\n")
        _write(root, "tv/t_cache.py", cache)
        _commit(root, "a gate that builds its own cache")
        os.remove(os.path.join(root, "tv", "live_gl.json"))
        self.assertTrue(_prove(_open(led), _gate(root, "t_cache.py")),
                        "a cache this run built before reading it was called local state")
        self.assertFalse(_prove(_open(led), _gate(root, "t_cache.py")),
                         "a cache an earlier run left behind was carried")

    def test_git_ls_files_is_a_listing_and_git_history_is_never_carried(self):
        lister = ("import os, subprocess, sys\nROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
                  "out = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True).stdout\n"
                  "sys.exit(0 if len(out.split()) < 9 else 1)\n")
        history = "import subprocess\nsubprocess.run(['git', 'log', '-1'], capture_output=True)\n"
        aside = ("import subprocess, tempfile\nd = tempfile.mkdtemp()\n"
                 "subprocess.run(['git', 'init', '-q', d], capture_output=True)\n"
                 "subprocess.run(['git', '-C', d, 'status'], capture_output=True)\n")
        root, led = self._tree({"t_ls.py": lister, "t_log.py": history, "t_aside.py": aside})
        gate = _gate(root, "t_ls.py")
        log, aside_gate = _gate(root, "t_log.py"), _gate(root, "t_aside.py")
        log.name, aside_gate.name = "git-log-fixture", "git-aside-fixture"
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the ls-files gate was not stored")
        self.assertFalse(_prove(_open(led), log), "a gate that reads git history was stored")
        self.assertTrue(_prove(_open(led), aside_gate), "git in a tempdir repository is not a read")
        for n in range(5):
            _write(root, "docs/n%d.md" % n, "n\n")
        _commit(root, "five new files")
        self.assertNotEqual(_run_traced(gate)[0], 0, "PREMISE: the gate is not red with five more files")
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "git ls-files saw new files and the gate was carried")

    def test_a_process_table_probe_is_not_a_read_unless_it_names_a_file(self):
        probe = "import subprocess\nsubprocess.run(['ps', '-o', 'pid='], capture_output=True)\n"
        named = ("import os, subprocess\nHERE = os.path.dirname(os.path.abspath(__file__))\n"
                 "subprocess.run(['lsof', os.path.join(HERE, 'helper_gl.py')], capture_output=True)\n")
        root, led = self._tree({"t_ps.py": probe, "t_lsof.py": named, "helper_gl.py": "X = 1\n"})
        ps, lsof = _gate(root, "t_ps.py"), _gate(root, "t_lsof.py")
        ps.name, lsof.name = "ps-fixture", "lsof-fixture"
        self.assertTrue(_prove(_open(led), ps), "ps reads the process table, not this checkout")
        self.assertFalse(_prove(_open(led), lsof), "lsof was handed a file in this checkout and was carried")

    @unittest.skipUnless(shutil.which("node"), "node is not installed here")
    def test_a_node_child_traces_what_it_read(self):
        reader = ("import os, subprocess, sys\nHERE = os.path.dirname(os.path.abspath(__file__))\n"
                  "js = \"process.exit(require('fs').readFileSync(process.argv[1], 'utf8').includes('ok') ? 0 : 1)\"\n"
                  "sys.exit(subprocess.run(['node', '-e', js, os.path.join(HERE, 'page' + '_gl.txt')]).returncode)\n")
        shell = "import subprocess\nsubprocess.run(['node', '-e', \"require('child_process').spawnSync('true')\"])\n"
        root, led = self._tree({"t_node.py": reader, "t_nsh.py": shell, "page_gl.txt": "ok\n"})
        gate, sh = _gate(root, "t_node.py"), _gate(root, "t_nsh.py")
        sh.name = "node-shell-fixture"
        self.assertTrue(_prove(_open(led), gate), "PREMISE: the node reader was not stored")
        self.assertFalse(_prove(_open(led), sh), "a node child that started a non-node child was stored")
        _write(root, "tv/page_gl.txt", "gone\n")
        _commit(root, "edit what node read")
        self.assertNotEqual(_run_traced(gate)[0], 0, "PREMISE: the gate is not red over the edit")
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a file only node read was carried over an edit")
        self.assertIn("page_gl.txt", why or "")

    def test_an_untracked_file_the_proof_saw_carries_and_a_new_one_does_not(self):
        helper = ("import os\nROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
                  "def count():\n    return len(os.listdir(os.path.join(ROOT, 'tests')))\n")
        law = "import sys, scan_gl\nsys.exit(0 if scan_gl.count() < 3 else 1)\n"
        root, led = self._tree({"t_cnt.py": law, "scan_gl.py": helper}, {"tests/a.spec.ts": "a\n"})
        _write(root, "tests/local_notes.txt", "his, untracked\n")
        gate = _gate(root, "t_cnt.py")
        self.assertTrue(_prove(_open(led), gate), "an untracked file the gate only listed stopped the record")
        entry, why = _open(led).lookup(gate)
        self.assertIsNotNone(entry, "the same untracked file, still there, stopped the carry: %s" % why)
        _write(root, "tests/zz_new.txt", "new\n")
        self.assertNotEqual(_run_traced(gate)[0], 0, "PREMISE: the gate is not red with one more file")
        entry, why = _open(led).lookup(gate)
        self.assertIsNone(entry, "a new untracked file under a listed directory was carried")
        self.assertIn("zz_new.txt", why or "")

    def test_old_ledger_shapes_still_parse(self):
        self.assertEqual(GL._churn("?? tv/a/b.py\n M tv/c.py\nD  tv/d.py\n"), {"tv/d.py"})
        self.assertEqual(GL._churn("?? tv/a/b.py\n M tv/c.py\n", untracked=True), {"tv/a/b.py"})
        self.assertEqual(GL.first_hit((), ("tv",), (), {"tv/x/y.py"}, {"tv/x/y.py"}), "tv/x/y.py")
        self.assertIsNone(GL.first_hit(("tv/a.py",), ("tests",), ("foo",), {"tv/b.py"}, {"tv/b.py"}))


class TheRunnerSeparatesFreshFromCarried(unittest.TestCase):
    def setUp(self):
        _drop_git_env(self)

    def test_the_ledger_file_is_not_blamed_as_live_state(self):
        import run_gates as rg
        root = tempfile.mkdtemp(prefix="gledger-watch.")
        self.addCleanup(shutil.rmtree, root, True)
        tv = os.path.join(root, "tv")
        os.makedirs(tv)
        with io.open(os.path.join(tv, ".gate_ledger.json"), "w", encoding="utf-8") as fh:
            fh.write("{}\n")
        with io.open(os.path.join(tv, ".gate_inputs.json"), "w", encoding="utf-8") as fh:
            fh.write("{}\n")
        with io.open(os.path.join(tv, "tooltip_find.json"), "w", encoding="utf-8") as fh:
            fh.write("{}\n")
        old = rg.HERE
        rg.HERE = tv
        try:
            state = rg._state_fingerprint()
            tree = rg._tree_fingerprint()
        finally:
            rg.HERE = old
        self.assertNotIn(".gate_ledger.json", state)
        self.assertNotIn(".gate_ledger.json", tree)
        self.assertNotIn(".gate_inputs.json", state)
        self.assertNotIn(".gate_inputs.json", tree)
        self.assertIn("tooltip_find.json", state)
        self.assertIn("tooltip_find.json", tree)

    def test_the_totals_do_not_call_a_carry_a_fresh_pass(self):
        import run_gates as rg
        text = rg.format_totals(0, 4, 0)
        self.assertIn("0 gate(s) passed fresh", text)
        self.assertIn("4 gate(s) carried", text)
        self.assertNotIn("4 gate(s) passed", text)
        skipped = rg.format_totals(2, 0, 1)
        self.assertIn("2 gate(s) passed fresh", skipped)
        self.assertIn("skipped for a DECLARED reason", skipped)
        self.assertFalse(rg.counts_as_ran("CARRY"))
        self.assertTrue(rg.counts_as_ran("PASS"))

    def test_full_runs_and_changed_carries_and_a_fail_is_not_carried(self):
        import run_gates as rg
        # v3849 GATE-BANK: a plain --full now reuses an unmoved PASS; TV_FULL_FRESH=1 is the run-everything --full
        _fresh = os.environ.get("TV_FULL_FRESH")
        os.environ["TV_FULL_FRESH"] = "1"
        self.addCleanup(lambda: os.environ.pop("TV_FULL_FRESH", None) if _fresh is None else os.environ.__setitem__("TV_FULL_FRESH", _fresh))
        mark_src = ("import os, sys\n"
                    "p = os.environ['GL_MARK']\n"
                    "fh = open(p, 'a', encoding='utf-8')\n"
                    "fh.write('ran\\n')\n"
                    "fh.close()\n"
                    "print('OK')\n"
                    "sys.exit(0)\n")
        root, led = _tree({
            "mark_gate.py": mark_src,
            "fail_gate.py": "import os, sys\nprint('OK')\nsys.exit(0 if os.environ.get('GL_OK') == '1' else 1)\n",
        })
        self.addCleanup(shutil.rmtree, root, True)
        mark = os.path.join(root, "mark.txt")
        script = os.path.join(root, "tv", "mark_gate.py")
        gate = _G("mark-gate", [sys.executable, script], timeout=30, cwd=root)
        fail = _G("fail-gate", [sys.executable, os.path.join(root, "tv", "fail_gate.py")],
                  timeout=30, cwd=root)
        old_gates, old_up = rg.GATES, rg._app_up
        rg.GATES = [gate, fail]
        rg._app_up = lambda *a, **k: False
        env = _Env(TV_GATE_LEDGER=led, GL_MARK=mark,
                   GITHUB_ACTIONS=None, GATE_LEDGER=None, GL_OK="1")
        env.__enter__()
        try:
            first = rg.run(only=set(["mark-gate"]), live_watch=False, ledger="full")
            self.assertEqual(first[0][1], "PASS", first)
            carried = rg.run(only=set(["mark-gate"]), live_watch=False, ledger="changed")
            self.assertEqual(carried[0][1], "CARRY", carried)
            self.assertTrue(str(carried[0][3]).startswith("proven at "), carried)
            self.assertNotIn("PASS", carried[0][3])
            with io.open(mark, "w", encoding="utf-8") as fh:
                fh.write("")
            again = rg.run(only=set(["mark-gate"]), live_watch=False, ledger="full")
            self.assertEqual(again[0][1], "PASS", again)
            with io.open(mark, encoding="utf-8") as fh:
                self.assertIn("ran", fh.read(), "--full did not execute the gate")
            os.environ["GL_OK"] = "1"
            passed = rg.run(only=set(["fail-gate"]), live_watch=False, ledger="changed")
            self.assertEqual(passed[0][1], "PASS", passed)
            os.environ["GL_OK"] = "0"
            failed = rg.run(only=set(["fail-gate"]), live_watch=False, ledger="full")
            self.assertEqual(failed[0][1], "FAIL", failed)
            again_fail = rg.run(only=set(["fail-gate"]), live_watch=False, ledger="changed")
            self.assertEqual(again_fail[0][1], "FAIL", again_fail)
        finally:
            env.__exit__(None, None, None)
            rg.GATES = old_gates
            rg._app_up = old_up


class TheHookAndTheWorkflowStayHonest(unittest.TestCase):
    def _hook(self):
        with io.open(os.path.join(ROOT, "hooks", "pre-push"), encoding="utf-8") as fh:
            raw = fh.read()
        code = "\n".join(re.sub(r"(^|\s)#.*$", "", line) for line in raw.split("\n"))
        return raw, code

    def test_each_suite_asks_the_ledger_before_it_runs(self):
        raw, code = self._hook()
        self.assertIn("ledger_carry()", raw)
        names = ("test_agent", "test_control", "test_tz_art", "test_chronicle_retro", "test_chronicle_seal")
        for name in names:
            call = "ledger_carry %s" % name
            run = 'gate_run "%s"' % name
            self.assertEqual(code.count(call), 1, call)
            self.assertLess(code.index(call), code.index(run), "%s runs before it asks the ledger" % name)

    def test_the_changed_law_proof_is_not_a_carry(self):
        raw, _code = self._hook()
        line = 'if python3 "$REPO/tv/heart2.py" --prove $_gates --push > "$_prove_log" 2>&1; then'
        self.assertIn(line, raw)
        self.assertNotIn('ledger_carry "$_gates"', raw)

    def test_ci_does_not_pass_the_changed_flag(self):
        with io.open(os.path.join(ROOT, ".github", "workflows", "tv-tests.yml"), encoding="utf-8") as fh:
            raw = fh.read()
        self.assertIn("python3 tv/run_gates.py --shard ${{ matrix.shard }}/5", raw)
        self.assertNotIn("run_gates.py --changed", raw)

    def test_the_carry_comment_does_not_say_input_bytes(self):
        raw, _code = self._hook()
        self.assertNotIn("input bytes", raw)

    def test_wilson_of_these_attacks_meets_the_bar_and_one_kind_does_not_open_a_door(self):
        import confidence
        n = len(RED_PROOF)
        self.assertGreaterEqual(n, 10)
        low = confidence.wilson_lower(n, n)
        self.assertGreaterEqual(low, 0.722)
        self.assertLess(1.0, 1.3)


RED_PROOF = [
    {
        "why": "the diff is discarded, so a committed input edit still carries",
        "file": "gate_ledger.py",
        "find": "        changed = set(p.strip() for _c, p in rows if p.strip())  # LEDGER-DIFF\n",
        "replace": "        changed = set()  # LEDGER-DIFF\n",
        "matches": 1,
    },
    {
        "why": "the dirty worktree is ignored, so an uncommitted input edit still carries",
        "file": "gate_ledger.py",
        "find": "        changed |= _porcelain(status_out)  # LEDGER-STATUS\n",
        "replace": "        changed |= set()  # LEDGER-STATUS\n",
        "matches": 1,
    },
    {
        "why": "an unreachable proven sha is treated as an empty diff, so the stored PASS carries",
        "file": "gate_ledger.py",
        "find": "        if cat_rc != 0 or diff_rc != 0 or stat_rc != 0:  # LEDGER-SHA\n",
        "replace": "        if False:  # LEDGER-SHA\n",
        "matches": 1,
    },
    {
        "why": "the blueprint is not part of the input-map key, so a stale map is reused",
        "file": "gate_ledger.py",
        "find": "    rels = (\"tv/run_gates.py\", \"BLUEPRINT.md\", \"tv/heart2.py\")  # LEDGER-MAPKEY\n",
        "replace": "    rels = (\"tv/run_gates.py\", \"tv/heart2.py\")  # LEDGER-MAPKEY\n",
        "matches": 1,
    },
    {
        "why": "an unrelated file is pulled into every input set, so editing it refuses a carry that was still valid",
        "file": "gate_ledger.py",
        "find": "        rels = list(rels)  # LEDGER-CLOSURE-ONLY\n",
        "replace": "        rels = list(rels) + [\"tv/unrelated.py\"]  # LEDGER-CLOSURE-ONLY\n",
        "matches": 1,
    },
    {
        "why": "a corrupt ledger is read as an empty one, and an empty one is not unreadable",
        "file": "gate_ledger.py",
        "find": "        return None, \"unreadable (%s)\" % type(exc).__name__  # LEDGER-CORRUPT\n",
        "replace": "        return {}, None  # LEDGER-CORRUPT\n",
        "matches": 1,
    },
    {
        "why": "a stored row with ok false is carried",
        "file": "gate_ledger.py",
        "find": "        if not isinstance(entry, dict) or entry.get(\"ok\") is not (want is True):  # LEDGER-ONLY-PASS\n",
        "replace": "        if False:  # LEDGER-ONLY-PASS\n",
        "matches": 1,
    },
    {
        "why": "record(False) stores the row as a PASS",
        "file": "gate_ledger.py",
        "find": "        red = ok is not True\n",
        "replace": "        red = False\n",
        "matches": 1,
    },
    {
        "why": "a later FAIL leaves the earlier PASS in the ledger",
        "file": "gate_ledger.py",
        "find": "        self.entries.pop(name, None)  # LEDGER-DROP-FAIL\n",
        "replace": "        self.entries.get(name, None)  # LEDGER-DROP-FAIL\n",
        "matches": 1,
    },
    {
        "why": "the python version is not part of the key",
        "file": "gate_ledger.py",
        "find": "        parts.append(\"python:%s\" % py)  # LEDGER-PY\n",
        "replace": "        parts.append(\"python:fixed\")  # LEDGER-PY\n",
        "matches": 1,
    },
    {
        "why": "the node version is not part of the key",
        "file": "gate_ledger.py",
        "find": "            parts.append(\"node:%s\" % node)  # LEDGER-NODE\n",
        "replace": "            parts.append(\"node:fixed\")  # LEDGER-NODE\n",
        "matches": 1,
    },
    {
        "why": "the playwright version is not part of the key",
        "file": "gate_ledger.py",
        "find": "            parts.append(\"playwright:%s\" % pw)  # LEDGER-PW\n",
        "replace": "            parts.append(\"playwright:fixed\")  # LEDGER-PW\n",
        "matches": 1,
    },
    {
        "why": "a missing python version still produces a key",
        "file": "gate_ledger.py",
        "find": "            return None, \"python version is UNKNOWN\"\n",
        "replace": "            py = \"missing\"\n",
        "matches": 1,
    },
    {
        "why": "a missing node version still produces a key",
        "file": "gate_ledger.py",
        "find": "                return None, \"node version is UNKNOWN\"\n",
        "replace": "                node = \"missing\"\n",
        "matches": 1,
    },
    {
        "why": "a missing playwright version still produces a key",
        "file": "gate_ledger.py",
        "find": "                return None, \"playwright version is UNKNOWN\"\n",
        "replace": "                pw = \"missing\"\n",
        "matches": 1,
    },
    {
        "why": "a gate whose inputs cannot be named (a node listing) is cached",
        "file": "gate_ledger.py",
        "find": "        if iwhy:  # LEDGER-UNKEYABLE\n",
        "replace": "        if False:  # LEDGER-UNKEYABLE\n",
        "matches": 1,
    },
    {
        "why": "CI carries a stored PASS",
        "file": "gate_ledger.py",
        "find": "    return os.environ.get(\"GITHUB_ACTIONS\") == \"true\"  # LEDGER-CI\n",
        "replace": "    return False  # LEDGER-CI\n",
        "matches": 1,
    },
    {
        "why": "GATE_LEDGER=0 still carries",
        "file": "gate_ledger.py",
        "find": "    return os.environ.get(\"GATE_LEDGER\", \"1\") == \"0\"  # LEDGER-OFF\n",
        "replace": "    return False  # LEDGER-OFF\n",
        "matches": 1,
    },
    {
        "why": "a missing ledger is not the empty ledger the next run expects",
        "file": "gate_ledger.py",
        "find": "        return {}, None  # LEDGER-MISSING empty, so the gate runs\n",
        "replace": "        return None, \"missing\"  # LEDGER-MISSING empty, so the gate runs\n",
        "matches": 1,
    },
    {
        "why": "a carry banks a Wilson row",
        "file": "gate_ledger.py",
        "find": "        return shown, None  # LEDGER-NO-BANK\n",
        "replace": "        import self_arming as _sa\n        _sa.bank(\"vault.apply\", \"sabotage\", \"gate-ledger\", 1, 1)\n        return shown, None  # LEDGER-NO-BANK\n",
        "matches": 1,
    },
    {
        "why": "the timeout is not part of the definition hash",
        "file": "gate_ledger.py",
        "find": "        blob = json.dumps({\"argv\": argv, \"timeout\": int(getattr(gate, \"timeout\", 0) or 0),\n                           \"venue\": venue}, sort_keys=True, default=str)  # LEDGER-DEF\n",
        "replace": "        blob = json.dumps({\"argv\": argv, \"venue\": venue}, sort_keys=True, default=str)  # LEDGER-DEF\n",
        "matches": 1,
    },
    {
        "why": "--full with TV_FULL_FRESH=1 consults the ledger and skips a gate",
        "file": "run_gates.py",
        "find": "(ledger == \"full\" and full_banks())",
        "replace": "(ledger == \"full\")",
        "matches": 1,
    },
    {
        "why": "carried gates are added into the fresh-pass count",
        "file": "run_gates.py",
        "find": "    shown = n_fresh  # LEDGER-FRESH\n",
        "replace": "    shown = n_fresh + n_carry  # LEDGER-FRESH\n",
        "matches": 1,
    },
    {
        "why": "a carried gate is counted as a gate that ran",
        "file": "run_gates.py",
        "find": "    return status not in (\"SKIP\", \"CARRY\")  # LEDGER-CENSUS\n",
        "replace": "    return status not in (\"SKIP\",)  # LEDGER-CENSUS\n",
        "matches": 1,
    },
    {
        "why": "a FAIL is recorded as a PASS, and the next run carries it",
        "file": "run_gates.py",
        "find": "                    if not led.record(g, status == \"PASS\", trace=_trace) and status == \"PASS\" and led.last_why:\n",
        "replace": "                    if not led.record(g, True, trace=_trace) and status == \"PASS\" and led.last_why:\n",
        "matches": 1,
    },
    {
        "why": "test_agent is carried without asking the ledger",
        "file": "hooks/pre-push",
        "find": "ledger_carry test_agent",
        "replace": "true  # ledger_carry test_agent",
        "matches": 1,
    },
    {
        "why": "the changed-law red-proof is skipped when a carry says so",
        "file": "hooks/pre-push",
        "find": "if python3 \"$REPO/tv/heart2.py\" --prove $_gates --push > \"$_prove_log\" 2>&1; then\n",
        "replace": "if ledger_carry \"$_gates\" || python3 \"$REPO/tv/heart2.py\" --prove $_gates --push > \"$_prove_log\" 2>&1; then\n",
        "matches": 1,
    },
    {
        "why": "the ledger file is watched as live state, so every gate is blamed for the runner writing it",
        "file": "run_gates.py",
        "find": "_LEDGER_SELF = frozenset((\".gate_ledger.json\", \".gate_ledger.json.tmp\", \".gate_inputs.json\", \".gate_inputs.json.tmp\"))  # LEDGER-WATCH\n",
        "replace": "_LEDGER_SELF = frozenset()  # LEDGER-WATCH\n",
        "matches": 1,
    },
    {
        "why": "script gained an import, map not rebuilt",
        "file": "gate_ledger.py",
        "find": "            row = self._store_decl(gate, root)  # LEDGER-RECORD-FRESH\n",
        "replace": "            row = self._map_row(gate, root)  # LEDGER-RECORD-FRESH\n",
        "matches": 1,
    },
    {
        "why": "helper grew a new import",
        "file": "gate_ledger.py",
        "find": "        paths = list(found)  # LEDGER-CLOSURE-WALK\n",
        "replace": "        paths = [p for p in found if os.path.basename(p) == os.path.basename(script)]  # LEDGER-CLOSURE-WALK\n",
        "matches": 1,
    },
    {
        "why": "one fresh PASS at the new HEAD makes every other gate rerun",
        "file": "gate_ledger.py",
        "find": "        if not self._is_ancestor(root, sha):  # LEDGER-ENTRY\n",
        "replace": "        if sha != self.proven:  # LEDGER-ENTRY\n",
        "matches": 1,
    },
    {
        "why": "bible.html is inherited from a string constant in an import",
        "file": "gate_ledger.py",
        "find": "        if not self._closure_reads_bible(script):  # LEDGER-BIBLE\n",
        "replace": "        if False:  # LEDGER-BIBLE\n",
        "matches": 1,
    },
    {
        "why": "a callee in an imported module opens bible.html",
        "file": "gate_ledger.py",
        "find": "            return self._callee_opens_bible(script)  # LEDGER-BIBLE-CALL\n",
        "replace": "            return False  # LEDGER-BIBLE-CALL\n",
        "matches": 1,
    },
    {
        "why": "a module alias passed, returned or re-bound is not a read, so a bible.html edit carries",
        "file": "gate_ledger.py",
        "find": "                refs.append((\"dyn\", mod))  # LEDGER-BIBLE-ESCAPE\n",
        "replace": "                pass  # LEDGER-BIBLE-ESCAPE\n",
        "matches": 1,
    },
    {
        "why": "self.ca, self.n = opener, 1 is not unpacked, so self.ca.read() carries a bible.html edit",
        "file": "gate_ledger.py",
        "find": "                for target, one in _assign_pairs(targets, value):  # LEDGER-BIBLE-TUPLE\n",
        "replace": "                for target, one in [(t, value) for t in targets]:  # LEDGER-BIBLE-TUPLE\n",
        "matches": 1,
    },
    {
        "why": "a subclass does not see what its base stored on self, so self.ca.read() carries",
        "file": "gate_ledger.py",
        "find": "    class_mods = dict((qual, file_mods) for qual in class_mods)  # LEDGER-BIBLE-FILEWIDE\n",
        "replace": "    class_mods = class_mods  # LEDGER-BIBLE-FILEWIDE\n",
        "matches": 1,
    },
    {
        "why": "self.ca = opener is not followed, so self.ca.read() carries a bible.html edit",
        "file": "gate_ledger.py",
        "find": "            mods = self.self_mods.get(attrs[0])  # LEDGER-BIBLE-SELF\n",
        "replace": "            mods = None  # LEDGER-BIBLE-SELF\n",
        "matches": 1,
    },
    {
        "why": "a file the runner names is an input of every gate, so a new gate reruns them all",
        "file": "heart2.py",
        "find": "            if dep in skip_modules and p != law:  # LEDGER-SKIP-RUNNER\n",
        "replace": "            if False and dep in skip_modules and p != law:  # LEDGER-SKIP-RUNNER\n",
        "matches": 1,
    },
    {
        "why": "the whole runner is an input of every gate, so editing it reruns them all",
        "file": "gate_ledger.py",
        "find": "        if not _script_reads_runner(script):  # LEDGER-NO-RUNNER\n",
        "replace": "        if False:  # LEDGER-NO-RUNNER\n",
        "matches": 1,
    },
    {
        "why": "a new file matching a declared glob is carried",
        "file": "gate_ledger.py",
        "find": "        if fnmatch.fnmatch(path, pat):  # LEDGER-WATCH-GLOB\n",
        "replace": "        if False:  # LEDGER-WATCH-GLOB\n",
        "matches": 1,
    },
    {
        "why": "a listing law is refused by the static walk again (v3775 keys it by its trace)",
        "file": "gate_ledger.py",
        "find": "                allow_listing=True,  # LEDGER-LISTING-TRACED\n",
        "replace": "                allow_listing=False,  # LEDGER-LISTING-TRACED\n",
        "matches": 1,
    },
    {
        "why": "--record mints a PASS with no suite verdict for these bytes",
        "file": "gate_ledger.py",
        "find": "    ok, why = _verdict_row(name, root)  # LEDGER-NO-MINT\n",
        "replace": "    ok, why = (True, None)  # LEDGER-NO-MINT\n",
        "matches": 1,
    },
    {
        "why": "heart2.py is not part of the input-map key, so a stale closure map is reused",
        "file": "gate_ledger.py",
        "find": "    rels = (\"tv/run_gates.py\", \"BLUEPRINT.md\", \"tv/heart2.py\")  # LEDGER-MAPKEY\n",
        "replace": "    rels = (\"tv/run_gates.py\", \"BLUEPRINT.md\")  # LEDGER-MAPKEY\n",
        "matches": 1,
    },
    {
        "why": "CI passes the changed flag and can carry a PASS it did not produce",
        "file": ".github/workflows/tv-tests.yml",
        "find": "          python3 tv/run_gates.py --shard ${{ matrix.shard }}/5\n",
        "replace": "          python3 tv/run_gates.py --changed --shard ${{ matrix.shard }}/5\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5 hole 1: only today's walk is compared, so a deleted input carries a red gate",
        "file": "gate_ledger.py",
        "find": "        inputs = set(row[\"inputs\"]) | set(str(p) for p in entry[\"inputs\"])  # LEDGER-PROOF-INPUTS\n",
        "replace": "        inputs = set(row[\"inputs\"])  # LEDGER-PROOF-INPUTS\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5 hole 2: a PASS proved on uncommitted bytes is stored under the clean HEAD",
        "file": "gate_ledger.py",
        "find": "        if dirty is None or hit:  # LEDGER-DIRTY-RECORD\n",
        "replace": "        if dirty is None:  # LEDGER-DIRTY-RECORD\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5 hole 3: a glob inside an imported module is not a listing, so a new file carries",
        "file": "gate_ledger.py",
        "find": "    if any(a in listed for a in _ancestors(path)):  # LEDGER-TRACE-LIST\n",
        "replace": "    if False:  # LEDGER-TRACE-LIST\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5 hole 4: what the run opened is thrown away, so bible.html through a local alias carries",
        "file": "gate_ledger.py",
        "find": "        inputs = set(row[\"inputs\"]) | traced[\"inputs\"]  # LEDGER-TRACE-READ\n",
        "replace": "        inputs = set(row[\"inputs\"])  # LEDGER-TRACE-READ\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5: an untracked folder is one status line, so a file inside it is not dirty",
        "file": "gate_ledger.py",
        "find": "        stat = _git(root, [\"status\", \"--porcelain\", \"--untracked-files=all\", \"--no-renames\"])  # LEDGER-UNTRACKED-ALL\n",
        "replace": "        stat = _git(root, [\"status\", \"--porcelain\", \"--no-renames\"])  # LEDGER-UNTRACKED-ALL\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5: a committed deletion under a listed directory is not churn",
        "file": "gate_ledger.py",
        "find": "        churn = set(p.strip() for c, p in rows if p.strip() and c[:1] in (\"A\", \"D\"))  # LEDGER-DIFF-CHURN\n",
        "replace": "        churn = set()  # LEDGER-DIFF-CHURN\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5: a module the gate failed to import is not watched, so the file that now resolves carries",
        "file": "gate_ledger.py",
        "find": "    return _module_stem(path) in imports  # LEDGER-TRACE-IMPORT\n",
        "replace": "    return False  # LEDGER-TRACE-IMPORT\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5: a PASS with no trace is stored, so its reads are UNKNOWN and it carries",
        "file": "gate_ledger.py",
        "find": "            facts, twhy = None, \"no trace of what the gate read\"  # LEDGER-NEEDS-TRACE\n",
        "replace": "            facts, twhy = {}, None  # LEDGER-NEEDS-TRACE\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5: a non-python child is ignored, so what it read is never checked",
        "file": "gate_ledger.py",
        "find": "            return None, \"the gate %s, which the trace cannot follow\" % text  # LEDGER-UNTRACED\n",
        "replace": "            continue  # LEDGER-UNTRACED\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5: a row stored before reads were traced is carried",
        "file": "gate_ledger.py",
        "find": "        if entry.get(\"traced\") is not True or not isinstance(entry.get(\"inputs\"), list):  # LEDGER-OLD-ROW\n",
        "replace": "        if not isinstance(entry.get(\"inputs\"), list):  # LEDGER-OLD-ROW\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5: a read of gitignored local state is carried, and no diff can say it moved",
        "file": "gate_ledger.py",
        "find": "            if ignored is not None and ignored.returncode == 0:  # LEDGER-IGNORED-READ\n",
        "replace": "            if False:  # LEDGER-IGNORED-READ\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5: run_gates does not trace the gate, so nothing it runs is ever stored",
        "file": "run_gates.py",
        "find": "            if led is not None:  # LEDGER-TRACE-RUN — what this run reads is what a later carry is checked against\n",
        "replace": "            if False:  # LEDGER-TRACE-RUN — what this run reads is what a later carry is checked against\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5: `git ls-files` is not a listing, so a new tracked file carries",
        "file": "gate_trace/sitecustomize.py",
        "find": "            emit(\"L\", \"\")  # the tracked set: any added or deleted file\n",
        "replace": "            pass  # the tracked set: any added or deleted file\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5: a file the run found already there is treated as one it made, so ignored state carries",
        "file": "gate_ledger.py",
        "find": "    facts[\"M\"] = set(p for p, k in first.items() if k == \"W\" or (k == \"A\" and p in facts[\"W\"]))  # LEDGER-MADE-FIRST\n",
        "replace": "    facts[\"M\"] = set(facts[\"W\"])  # LEDGER-MADE-FIRST\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5: lsof handed a file in the checkout is waved through as a process-table probe",
        "file": "gate_trace/sitecustomize.py",
        "find": '        if head == "lsof" and not any(\n                rel(a) is not None for a in args[1:] if "/" in a):\n',
        "replace": '        if head == "lsof" and not any(\n                False for a in args[1:] if "/" in a):\n',
        "matches": 1,
    },
    {
        "why": "REG-2293 r5: node children are not armed, so every gate that shells out to node is never stored",
        "file": "gate_ledger.py",
        "find": "    env[\"NODE_OPTIONS\"] = ('--require \"%s\"' % hook) + (\" \" + node if node else \"\")  # LEDGER-TRACE-NODE\n",
        "replace": "    env[\"NODE_OPTIONS\"] = node  # LEDGER-TRACE-NODE\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r5: node's readFileSync is not traced, so a file only node read carries over an edit",
        "file": "gate_trace/node_trace.cjs",
        "find": "  const R = (p) => { note('R', p); base2('R', p); };\n",
        "replace": "  const R = (p) => { base2('R', p); };\n",   # REG-3319 - the gate's half alone goes blind
        "matches": 1,
    },
    {
        "why": "REG-2293 r5: the untracked snapshot is not compared, so a new untracked file under a listed directory carries",
        "file": "gate_ledger.py",
        "find": "        moved = seen ^ set(entry.get(\"untracked\") or ())  # LEDGER-UNTRACKED-SNAPSHOT\n",
        "replace": "        moved = set()  # LEDGER-UNTRACKED-SNAPSHOT\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r6 (B): a gate's imports come from a warm .pyc again, so the .py it ran is never read",
        "file": "gate_ledger.py",
        "find": "    env[\"PYTHONPYCACHEPREFIX\"] = path + \".pycache\"  # LEDGER-TRACE-NOPYC\n",
        "replace": "    env.pop(\"PYTHONDONTWRITEBYTECODE\")  # LEDGER-TRACE-NOPYC\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r6 (B2): an imported name is not its source, so a module a child imported carries over an edit",
        "file": "gate_ledger.py",
        "find": "            inputs.update(p for p in tracked if _module_stem(p) in names)  # LEDGER-TRACE-IMPORT-SOURCE\n",
        "replace": "            pass  # LEDGER-TRACE-IMPORT-SOURCE\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r6 (A): one busy flag for every thread, so an open on another thread is dropped",
        "file": "gate_trace/sitecustomize.py",
        "find": "    local = _thread._local()  # LEDGER-TRACE-THREAD\n",
        "replace": "    local = type(\"Shared\", (), {})()  # LEDGER-TRACE-THREAD\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r6 (C): os.access is not a probe, so a file a gate checked was absent carries when it appears",
        "file": "gate_trace/sitecustomize.py",
        "find": "    os.access = probe_wrap(os.access)\n",
        "replace": "    pass\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r6 (C): os.readlink is not a probe",
        "file": "gate_trace/sitecustomize.py",
        "find": "    os.readlink = probe_wrap(os.readlink)  # LEDGER-TRACE-PROBE\n",
        "replace": "    pass  # LEDGER-TRACE-PROBE\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r6 (speed): the running console's own record blocks every record and every carry",
        "file": "gate_ledger.py",
        "find": "        return set(self_prove.CONSOLE_OWN_RECORDS)  # LEDGER-OWN-RECORDS\n",
        "replace": "        return set()  # LEDGER-OWN-RECORDS\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r6: a PASS dropped for a listing law says nothing, so the runner prints no reason",
        "file": "gate_ledger.py",
        "find": "                self.last_why = why or \"its inputs are UNKNOWN\"  # LEDGER-SAY-WHY\n",
        "replace": "                pass  # LEDGER-SAY-WHY\n",
        "matches": 1,
    },
    {
        "why": "REG-2293 r6: the hook's --trace-env arms nothing, so its --record can never store",
        "file": "gate_ledger.py",
        "find": "                print(\"export %s=%s\" % (key, shlex.quote(armed[key])))  # LEDGER-HOOK-TRACE\n",
        "replace": "                pass  # LEDGER-HOOK-TRACE\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main()
