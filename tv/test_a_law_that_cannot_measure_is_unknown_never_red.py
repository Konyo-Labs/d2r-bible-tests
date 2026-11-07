# -*- coding: utf-8 -*-
"""#161 (REG-3061) - A LAW WHOSE BROWSER WOULD NOT START COULD NOT MEASURE: THE GATE SET READS IT UNKNOWN, NEVER RED.

MEASURED on CI 2026-10-29: test_found_ever_never_files_to_a_mule failed the gate set twice (v3837's first grade, then
v3838), "would not start on :51565" and ":59361", each FAILED (failures=1): only its first case failed - its browser
was alive and slow under the shard's load - and the five cases after it found that same browser answering and passed.
The law had nothing to say about the vault it guards, and the gate set published red=true, a red verdict nobody reached.

Now such a law raises a VenueFault (its message carries VENUE_MARK) once its launcher has given up, and run_gates reads a
gate whose EVERY unittest failure is a venue fault as VENUE: named apart from any red, and the set exits VENUE_EXIT (3)
when nothing was red - which the CI gate-set step publishes as reached=true, red=unknown (UNKNOWN: not a pass, not a red).
One failure of any other kind keeps the gate FAIL. The launcher's own retry and the browser laws' use of it are held by
tv/test_a_slow_browser_start_is_retried_and_named.py.

Driven: venue_only() over REAL unittest output (tiny unittest modules run in a subprocess, failing each way); the exit
rule; main()'s use of both, read at its lines; the CI step's real exit-code block cut from the workflow and run in bash
for exit 0, 1, 2 and 3. RED_PROOF below.
"""
import io
import os

#: #107 - this law drives hooks/pre-push or a Linux job's own bash. Neither runs on Windows (only the Mac pushes; the job
#: runs on ubuntu), and Windows' bash there is the WSL launcher or Git Bash with backslash paths - nothing to measure
_RUNS_POSIX_HOOKS = os.name != "nt"
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import run_gates as RG  # noqa: E402

WORKFLOW = os.path.join(ROOT, ".github", "workflows", "tv-tests.yml")
RUN_GATES = os.path.join(HERE, "run_gates.py")

#: tiny laws, each failing one way; the venue fault is raised the way the browser laws raise it (an AssertionError
#: subclass whose message carries the mark)
LAWS = {
    "all_venue": '''
import unittest
class VenueFault(AssertionError):
    pass
def need():
    raise VenueFault("\\u26aa VENUE FAULT - the browser would not start (:5 was alive and never answered). UNKNOWN.")
class T(unittest.TestCase):
    def test_a(self):
        need()
    def test_b(self):
        need()
unittest.main()
''',
    "setup_venue": '''
import unittest
class VenueFault(AssertionError):
    pass
class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raise VenueFault("\\u26aa VENUE FAULT - the browser would not start. UNKNOWN.")
    def test_a(self):
        pass
unittest.main()
''',
    "mixed": '''
import unittest
class VenueFault(AssertionError):
    pass
class T(unittest.TestCase):
    def test_a(self):
        raise VenueFault("\\u26aa VENUE FAULT - the browser would not start. UNKNOWN.")
    def test_b(self):
        self.assertEqual(1, 2, "the vault filed a found-ever name")
unittest.main()
''',
    "prose_only": '''
import unittest
class T(unittest.TestCase):
    def test_a(self):
        x = "VENUE FAULT"  # the words in a source line, not in the failure
        self.assertEqual(x, "red", "a real red")
unittest.main()
''',
    "green": '''
import unittest
class T(unittest.TestCase):
    def test_a(self):
        pass
unittest.main()
''',
}


def _outputs():
    d = tempfile.mkdtemp(prefix="venue-laws-")
    try:
        out = {}
        for name, src in LAWS.items():
            p = os.path.join(d, name + ".py")
            with io.open(p, "w", encoding="utf-8") as fh:
                fh.write(src)
            r = subprocess.run([sys.executable, p], capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=60)
            out[name] = (r.returncode, (r.stdout or "") + (r.stderr or ""))
        return out
    finally:
        shutil.rmtree(d, True)


_O = {}


def _o():
    if not _O:
        _O.update(_outputs())
    return _O


class AFailureThatCouldNotMeasureIsVenue(unittest.TestCase):

    def test_premise_each_tiny_law_failed_or_passed_as_written(self):
        o = _o()
        self.assertEqual(o["green"][0], 0, o["green"][1][-300:])
        for k in ("all_venue", "setup_venue", "mixed", "prose_only"):
            self.assertNotEqual(o[k][0], 0, "%s did not fail: %s" % (k, o[k][1][-300:]))

    def test_every_failure_a_venue_fault_is_venue(self):
        self.assertTrue(RG.venue_only(_o()["all_venue"][1]), _o()["all_venue"][1][-600:])
        self.assertTrue(RG.venue_only(_o()["setup_venue"][1]), _o()["setup_venue"][1][-600:])

    def test_one_real_red_keeps_the_gate_red(self):
        self.assertFalse(RG.venue_only(_o()["mixed"][1]), "a red hid behind a venue fault")

    def test_the_words_in_a_source_line_are_not_a_venue_fault(self):
        self.assertFalse(RG.venue_only(_o()["prose_only"][1]), "a failure's source line was read as its verdict")

    def test_no_failure_is_not_venue(self):
        self.assertFalse(RG.venue_only(_o()["green"][1]))
        self.assertFalse(RG.venue_only(""))


class AGateScriptThatCannotMeasureIsVenueToo(unittest.TestCase):
    """REG-3064 - a gate SCRIPT (not a unittest law) whose browser would not start exits VENUE_EXIT with the mark."""

    def test_the_status(self):
        st = RG.gate_status
        self.assertEqual(st(0, "ok"), "PASS")
        self.assertEqual(st(RG.SKIP_EXIT, "no browser here"), "SKIP")
        self.assertEqual(st(RG.VENUE_EXIT, "\u26aa UNKNOWN \u2014 %s - installed and would not start" % RG.VENUE_MARK), "VENUE")
        self.assertEqual(st(RG.VENUE_EXIT, "a script that happened to exit 3"), "FAIL",
                         "an exit 3 that does not say why was read as a venue fault")
        self.assertEqual(st(1, "%s in a script's ordinary failure" % RG.VENUE_MARK), "FAIL",
                         "a script's exit 1 was read as a venue fault")
        self.assertEqual(st(1, _o()["all_venue"][1]), "VENUE")
        self.assertEqual(st(1, _o()["mixed"][1]), "FAIL")


class TheGateSetExitsUnknownNotRed(unittest.TestCase):

    def test_the_exit(self):
        self.assertEqual(RG.gate_set_exit([], []), 0)
        self.assertEqual(RG.gate_set_exit([], [("a", "why")]), RG.VENUE_EXIT)
        self.assertEqual(RG.gate_set_exit(["b"], [("a", "why")]), 1, "a venue fault turned a red run green")
        self.assertEqual(RG.gate_set_exit(["b"], []), 1)
        self.assertNotIn(RG.VENUE_EXIT, (0, 1, 2, RG.SKIP_EXIT), "the venue exit collides with another verdict")

    def test_main_classifies_by_it_and_exits_by_it(self):
        with io.open(RUN_GATES, encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count('                status = gate_status(p.returncode, (p.stdout or "") + (p.stderr or ""))'), 1,
                         "a gate's result is no longer asked whether it measured")
        self.assertEqual(src.count("    return gate_set_exit(failed, _venue)\n"), 1,
                         "the gate set's verdict no longer takes the venue faults into account")
        self.assertEqual(src.count('if led is not None and status in ("PASS", "FAIL"):'), 1,
                         "PREMISE: the ledger records only what measured - a VENUE gate is never stored as proven")


class TheShipReceiptNeverCallsItAPass(unittest.TestCase):
    """REG-3061 - ship_audit's gate receipt read the pass line alone, and a VENUE ending prints it too."""

    def test_an_exit_3_is_recorded_as_not_passed(self):
        import ship_audit as SA
        from unittest import mock
        saved = {}

        class P(object):
            returncode, stderr = RG.VENUE_EXIT, ""
            stdout = "\u2705 41 gate(s) passed fresh.\n\u26aa 1 gate(s) could NOT MEASURE on this venue\n"
        with mock.patch.object(SA.subprocess, "run", lambda *a, **k: P()), \
                mock.patch.object(SA, "_load", lambda: {}), \
                mock.patch.object(SA, "_save", lambda d: saved.update(d)), \
                mock.patch.object(SA, "_head", lambda: "f" * 40):
            rc = SA.record_gates()
        self.assertEqual((rc, (saved.get("gates") or {}).get("passed")), (1, False),
                         "a gate set that could not measure a law was recorded as passed: %r" % saved)
        P.returncode = 0
        with mock.patch.object(SA.subprocess, "run", lambda *a, **k: P()), \
                mock.patch.object(SA, "_load", lambda: {}), \
                mock.patch.object(SA, "_save", lambda d: saved.update(d)), \
                mock.patch.object(SA, "_head", lambda: "f" * 40):
            self.assertEqual(SA.record_gates(), 0, "PREMISE: a real pass still records as passed")


def _exit_block():
    with io.open(WORKFLOW, encoding="utf-8") as fh:
        y = fh.read()
    i = y.index('          if [ "$_rc" -eq 2 ]; then\n')
    j = y.index("          fi\n", y.index("          else\n", i)) + len("          fi\n")
    return y[i:j]


class TheCIStepPublishesUnknown(unittest.TestCase):

    def _run(self, rc):
        bash = shutil.which("bash")
        if not bash:
            raise AssertionError("no bash on this venue - the CI step's own block could not be run (UNKNOWN)")
        script = "_rc=%d\n%s\necho \"reached=$_reached red=$_red\"\n" % (rc, _exit_block())
        r = subprocess.run([bash, "--noprofile", "--norc", "-e", "-c", script], capture_output=True, text=True,
                           timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip().splitlines()[-1]

    def test_each_exit_publishes_its_own_fact(self):
        self.assertEqual(self._run(0), "reached=true red=false")
        self.assertEqual(self._run(1), "reached=true red=true")
        self.assertEqual(self._run(2), "reached=false red=unknown")
        self.assertEqual(self._run(RG.VENUE_EXIT), "reached=true red=unknown",
                         "a gate set that could not measure a law was published as a verdict")


def _run_block(name):
    """The `run: |` script of the workflow step called `name`, de-indented, exactly as the runner gets it."""
    with io.open(WORKFLOW, encoding="utf-8") as fh:
        y = fh.read()
    i = y.index("- name: " + name)
    j = y.index("run: |", i)
    ind = len(y[y.rindex("\n", 0, j) + 1:j])
    out = []
    for ln in y[j:].split("\n")[1:]:
        if ln.strip() and (len(ln) - len(ln.lstrip())) <= ind:
            break
        out.append(ln[ind + 2:] if len(ln) > ind + 2 else ln.strip())
    return "\n".join(out)


class AVenueEndingNeverConcludesGreen(unittest.TestCase):
    """REG-3061 - exit 3 stops a law reading RED; it must never let the WORKFLOW read green. Driven end to end on the
    workflow's own scripts: the gate-set step's exit block, the verdict job's shard aggregator and its conclusion."""

    @unittest.skipUnless(_RUNS_POSIX_HOOKS, "the verdict job runs on ubuntu - its script never runs on Windows")
    def test_exit_3_through_the_verdict_job_is_no_verdict_and_fails(self):
        bash = shutil.which("bash")
        if not bash:
            raise AssertionError("no bash on this venue - the workflow's own scripts could not be run (UNKNOWN)")
        d = tempfile.mkdtemp(prefix="venue-verdict-")
        self.addCleanup(shutil.rmtree, d, True)
        facts = {1: RG.VENUE_EXIT, 2: 0, 3: 0, 4: 0, 5: 0}
        for k, rc in facts.items():
            r = subprocess.run([bash, "--noprofile", "--norc", "-e", "-c",
                                "_rc=%d\n%s\nprintf 'reached=%%s\\nred=%%s\\n' \"$_reached\" \"$_red\" > %s/shard-%d.txt"
                                % (rc, _exit_block(), d, k)], capture_output=True, text=True, timeout=30)
            self.assertEqual(r.returncode, 0, r.stderr)
        out = os.path.join(d, "out.txt")
        env = dict(os.environ, GATE_SHARDS="1 2 3 4 5", VERDICT_DIR=d, GITHUB_OUTPUT=out)
        r = subprocess.run([bash, "--noprofile", "--norc", "-e", "-c",
                            _run_block("Every shard must have reached its end, and one red shard is a red gate set")],
                           capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        with io.open(out, encoding="utf-8") as fh:
            got = dict(ln.split("=", 1) for ln in fh.read().split() if "=" in ln)
        self.assertEqual((got.get("reached"), got.get("red")), ("true", "unknown"), got)
        # the gate-set step exits 3, so the job concludes failure - and the verdict must say NO VERDICT and fail
        env = dict(os.environ, SUITE_RESULT="failure", GATE_SET_REACHED=got["reached"], GATE_SET_RED=got["red"])
        r = subprocess.run([bash, "--noprofile", "--norc", "-e", "-c",
                            _run_block("A conclusion that is not a pass must not read like one")],
                           capture_output=True, text=True, env=env, timeout=30)
        self.assertNotEqual(r.returncode, 0, "a gate set that could not measure a law concluded green: %s" % r.stdout)
        self.assertIn("title=NO VERDICT", r.stdout)
        self.assertNotIn("title=GATES RED", r.stdout, "a law that could not measure was called RED")


RED_PROOF = [
    {"why": "REG-3061 - a gate whose browser would not start reads RED again (never asked whether it measured)",
     "file": "run_gates.py",
     "find": "                status = gate_status(p.returncode, (p.stdout or \"\") + (p.stderr or \"\"))   # REG-3061 / REG-3064\n",
     "replace": "                status = \"PASS\" if p.returncode == 0 else (\"SKIP\" if p.returncode == SKIP_EXIT else \"FAIL\")\n",
     "matches": 1},
    {"why": "REG-3064 - a gate script whose installed browser would not start (exit 3 + the mark) reads RED",
     "file": "run_gates.py",
     "find": "    if returncode == VENUE_EXIT and VENUE_MARK in (out or \"\"):\n        return \"VENUE\"\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3064 - any script that exits 3 is read as a venue fault, mark or not",
     "file": "run_gates.py",
     "find": "    if returncode == VENUE_EXIT and VENUE_MARK in (out or \"\"):\n",
     "replace": "    if returncode == VENUE_EXIT:\n",
     "matches": 1},
    {"why": "REG-3061 - a gate with one real red and one venue fault is called VENUE, hiding the red",
     "file": "run_gates.py",
     "find": "        if not exc or not re.match(r\"^(?:[\\w.]+\\.)?VenueFault: \", exc[-1]) or VENUE_MARK not in exc[-1]:\n",
     "replace": "        if not exc:\n",
     "matches": 1},
    {"why": "REG-3061 - any exception whose text holds the words (an assertEqual on the string, a source line) is read as a venue fault",
     "file": "run_gates.py",
     "find": "not re.match(r\"^(?:[\\w.]+\\.)?VenueFault: \", exc[-1]) or ",
     "replace": "",
     "matches": 1},
    {"why": "REG-3061 - a run that could not measure a law exits 0, read as a pass",
     "file": "run_gates.py",
     "find": "    return 1 if failed else (VENUE_EXIT if venue else 0)\n",
     "replace": "    return 1 if failed else 0\n",
     "matches": 1},
    {"why": "REG-3061 - a venue fault turns a red run into an UNKNOWN one",
     "file": "run_gates.py",
     "find": "    return 1 if failed else (VENUE_EXIT if venue else 0)\n",
     "replace": "    return VENUE_EXIT if venue else (1 if failed else 0)\n",
     "matches": 1},
    {"why": "REG-3061 - ship_audit's receipt calls a gate set that could not measure a law PASSED",
     "file": "ship_audit.py",
     "find": "    passed = bool(m) and p.returncode == 0\n",
     "replace": "    passed = bool(m)\n",
     "matches": 1},
    {"why": "REG-3061 - CI publishes a gate set that could not measure a law as a verdict (red=true)",
     "file": "../.github/workflows/tv-tests.yml",
     "find": "          elif [ \"$_rc\" -eq 3 ]; then\n            _reached=true; _red=unknown\n",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
