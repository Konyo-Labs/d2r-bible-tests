# -*- coding: utf-8 -*-
"""v3774 — A COHERENT VERSION BUMP IS NOT A CHANGE TO EVERY GATE.

bump_version.py rewrites known stamp lines in bible.html, tv/control_app.py, tv/tv_diablo.py and
tv/WINDOWS_SHIP.json, and its regenerations rewrite known lines in RESUME_HERE.md, BLUEPRINT.md and
the TASKS.md ship table. Under gate memory (v3772) those paths are inputs of most gates, so a
bump-only diff reran 760 of 1003 gates.

The stamp surfaces leave the change set ONLY for a coherent bump: every required surface moved,
each only its stamp lines, each stamp swapped in place (same hunk position, kind and indentation),
all from one old version to one new version, and TASKS.md gained exactly the single new top ship
row in bump_version's format. Anything else - a partial or hand bump, a moved or re-indented stamp,
code riding on a stamp line, another row edit, an unknown diff line, a failed diff - reruns every
gate. A gate that reads the version (its name, its script, or a reader-only module in its closure)
reruns even on a coherent bump. Second look on PR #245 found test_the_resume_cannot_go_stale
carried over a one-file hand bump; that case is pinned here.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import gate_ledger as GL  # noqa: E402

PROBES = {"python": "3.9.9", "node": "v20.0.0", "playwright": "1.40.0"}
U, V = "v100", "v101"
NOTE = "Derived 2026-10-19 10:17 by `tv/resume_state.py`. Everything outside these markers is narrative a machine cannot measure, written by hand."


_SHAS = {}  # version -> the real fixture commit that shipped it (round 3: bound rows must be real)


def _files(ver, sha_row=False, note="first", title_word="Bible", shipped=None):
    shipped = list(shipped if shipped is not None else ([U] if sha_row else []))
    tasks_rows = ("| **%s** | `(this commit)` | %s — %s |\n" % (ver, ver, note)
                  + "".join("| **%s** | `%s` | %s — %s |\n" % (v, _SHAS.get(v, "abcdef12"), v, "first" if v == U else "second")
                            for v in shipped)
                  + "| **v99** | `1234567a` | v99 — older |\n")
    return {
        "bible.html": ("<html><head>\n  <title>Konyo %s %s · TV</title>\n"
                       '<meta name="d2r-build" content="%s">\n'
                       '<meta name="d2r-build-date" content="2026-10-19">\n'
                       '<meta name="d2r-build-note" content="%s">\n</head><body><script>\n'
                       "var a = 1;\n"
                       "  window.D2R_BUILD = { id:'%s', name:'%s - n', date:'2026-10-19', note:'%s' };\n"
                       "var b = 2;\n</script></body></html>\n") % (title_word, ver, ver, note, ver, ver, note),
        "tv/control_app.py": ('import os\ndef status():\n    return {\n        "ver": "%s",\n'
                              '        "ok": True,\n    }\nSALT = 1\n') % ver,
        "tv/tv_diablo.py": 'import os\nVERSION = "%s"   # %s\nX = 1\n' % (ver, note),
        "tv/WINDOWS_SHIP.json": '{\n  "platform": "windows",\n  "ver": "%s",\n  "note": "%s: %s",\n  "x": 1\n}\n' % (ver, ver, note),
        "RESUME_HERE.md": "# r\n<!-- fp: ver=%s -->\n\n| version stamp | %s |\n\n*%s*\n" % (ver, ver, NOTE),
        "BLUEPRINT.md": "# b\n    generated 2026-10-19 10:16\n",
        "TASKS.md": "# t\n\n| version | commit | commit subject |\n|---|---|---|\n" + tasks_rows,
    }


_PLAIN_LAW = "import control_app\nimport sys\nprint('OK')\nsys.exit(0)\n"
_VERSION_LAW = "import control_app\nimport sys\nassert control_app.status()['ver']\nprint('OK')\n"
_RESUME_LAW = ("import subprocess, sys, os\nimport control_app\n"
               "subprocess.call([sys.executable, os.path.join(os.path.dirname(__file__), 'resume_state.py'), '--check'])\n")
_READER_LAW = "import control_app\nimport hub_gl\nprint('OK')\n"


class _Env(object):
    def __init__(self, **kw):
        self.kw, self.old = kw, {}

    def __enter__(self):
        for k, v in self.kw.items():
            self.old[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *exc):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class _G(object):
    def __init__(self, name, argv, cwd):
        self.name, self.argv, self.cwd = name, argv, cwd
        self.timeout, self.needs_app, self.skip_ok = 30, False, ()


def _git(root, *args):
    p = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip())
    return p


def _write(root, rel, text):
    with io.open(os.path.join(root, rel), "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def _read(root, rel):
    with io.open(os.path.join(root, rel), encoding="utf-8", newline="") as fh:
        return fh.read()


def _hunk(rel, rem, add, o=5, n=None):
    n = o if n is None else n
    body = "".join("-%s\n" % r for r in rem) + "".join("+%s\n" % a for a in add)
    return ("diff --git a/%s b/%s\nindex 1..2 100644\n--- a/%s\n+++ b/%s\n@@ -%d,%d +%d,%d @@\n%s"
            % (rel, rel, rel, rel, o, len(rem), n, len(add), body))


class ACoherentBumpCarries(unittest.TestCase):
    def setUp(self):
        self.held = _Env(GITHUB_ACTIONS=None, GATE_LEDGER=None,
                         TV_SELF_ARMING_LEDGER=os.path.join(tempfile.mkdtemp(prefix="gbump-arm."), "a.json"))
        self.held.__enter__()
        self.addCleanup(self.held.__exit__, None, None, None)
        root = tempfile.mkdtemp(prefix="gbump.")
        self.addCleanup(shutil.rmtree, root, True)
        os.makedirs(os.path.join(root, "tv"))
        _write(root, ".gitignore", ".gate_ledger.json\n.gate_inputs.json\n*.tmp\n")
        for rel, text in _files(U).items():
            _write(root, rel, text)
        for rel, text in (("tv/t_plain.py", _PLAIN_LAW), ("tv/t_reads.py", _VERSION_LAW),
                          ("tv/t_resume.py", _RESUME_LAW), ("tv/t_reader.py", _READER_LAW),
                          ("tv/resume_state.py", "import sys\nsys.exit(0)\n"),
                          ("tv/version_stamp_gate.py", "X = 1\n"),
                          ("tv/hub_gl.py", "import version_stamp_gate\n")):
            _write(root, rel, text)
        _git(root, "init", "-q", "-b", "main")
        _git(root, "config", "user.email", "b@example.com")
        _git(root, "config", "user.name", "b")
        _git(root, "config", "commit.gpgsign", "false")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "base")
        self.root = root
        _SHAS.clear()
        _SHAS[U] = self.head()
        self.led = os.path.join(root, ".gate_ledger.json")

    def head(self):
        return _git(self.root, "rev-parse", "HEAD").stdout.strip()

    def ship(self, ver, msg):
        _git(self.root, "commit", "-qam", msg)
        _SHAS[ver] = self.head()

    def gate(self, script, name=None):
        return _G(name or ("fixture-" + script), [sys.executable, os.path.join(self.root, "tv", script)], self.root)

    def book(self, *gates):
        b = GL.Ledger(path=self.led, probes=dict(PROBES))
        for g in gates:
            self.assertTrue(b.record(g, True, trace={"R": set(), "W": set(), "S": set(), "L": set(), "I": set()}), "PREMISE: no PASS stored for %s" % g.name)
        return GL.Ledger(path=self.led, probes=dict(PROBES))

    def bump(self, skip=(), ver=V, override=None, shipped=None):
        new = _files(ver, sha_row=True, note="second", shipped=shipped)
        new["BLUEPRINT.md"] = "# b\n    generated 2026-10-19 13:50\n"
        for rel, text in new.items():
            if rel in skip:
                continue
            _write(self.root, rel, (override or {}).get(rel, text))

    def edit(self, rel, old, new):
        s = _read(self.root, rel)
        self.assertIn(old, s)
        _write(self.root, rel, s.replace(old, new, 1))

    def carried(self, gate, b):
        entry, why = b.lookup(gate)
        return entry is not None, why

    # --- the carry itself
    def test_premise_a_real_edit_runs(self):
        g = self.gate("t_plain.py"); b = self.book(g)
        self.edit("tv/control_app.py", "SALT = 1", "SALT = 2")
        self.assertFalse(self.carried(g, b)[0], "PREMISE: control_app.py is not an input")

    def test_a_coherent_bump_carries(self):
        g = self.gate("t_plain.py"); b = self.book(g)
        self.bump()
        ok, why = self.carried(g, b)
        self.assertTrue(ok, "a coherent bump reran a gate that never reads the version: %s" % why)

    def test_a_committed_coherent_bump_carries(self):
        g = self.gate("t_plain.py"); b = self.book(g)
        self.bump()
        _git(self.root, "commit", "-qam", "bump")
        self.assertTrue(self.carried(g, b)[0])

    def test_a_bump_plus_a_real_edit_runs(self):
        g = self.gate("t_plain.py"); b = self.book(g)
        self.bump()
        self.edit("tv/control_app.py", "SALT = 1", "SALT = 3")
        self.assertFalse(self.carried(g, b)[0], "a bump hid a real edit in the same file")

    # --- item 1: partial / hand bumps and version readers
    def test_a_one_file_hand_bump_runs(self):
        g = self.gate("t_plain.py"); b = self.book(g)
        self.edit("tv/control_app.py", '"ver": "%s"' % U, '"ver": "%s"' % V)
        self.assertFalse(self.carried(g, b)[0], "a hand edit of one stamp was carried")

    def test_a_bump_that_died_before_the_resume_runs(self):
        g = self.gate("t_plain.py"); b = self.book(g)
        self.bump(skip=("RESUME_HERE.md", "TASKS.md", "BLUEPRINT.md"))
        self.assertFalse(self.carried(g, b)[0], "a bump that never regenerated RESUME_HERE was carried")

    def test_two_new_versions_are_not_one_bump(self):
        g = self.gate("t_plain.py"); b = self.book(g)
        self.bump()
        self.edit("tv/control_app.py", '"ver": "%s"' % V, '"ver": "v102"')
        self.assertFalse(self.carried(g, b)[0], "surfaces at two different new versions were carried")

    def test_a_gate_that_reads_the_version_runs(self):
        g = self.gate("t_reads.py"); b = self.book(g)
        self.bump()
        self.assertFalse(self.carried(g, b)[0])

    def test_the_resume_check_runs_on_a_bump(self):
        g = self.gate("t_resume.py", name="fixture-plain-name"); b = self.book(g)
        self.bump()
        self.assertFalse(self.carried(g, b)[0], "a gate that runs resume_state.py was carried")

    def test_a_reader_module_in_the_closure_runs(self):
        g = self.gate("t_reader.py", name="fixture-plain-name"); b = self.book(g)
        self.assertIn("tv/version_stamp_gate.py", b._map_row(g, self.root).get("inputs") or [],
                      "PREMISE: the reader module is not in the closure")
        self.bump()
        self.assertFalse(self.carried(g, b)[0], "a closure holding version_stamp_gate was carried")

    def test_a_gate_named_for_the_build_runs(self):
        g = self.gate("t_plain.py", name="test_build_stamp_fixture"); b = self.book(g)
        self.bump()
        self.assertFalse(self.carried(g, b)[0])

    # --- round 2 B: back-to-back bumps
    def test_two_back_to_back_bumps_carry(self):
        g = self.gate("t_plain.py"); b = self.book(g)
        self.bump(ver=V)
        self.ship(V, "bump 1")
        self.bump(ver="v102", shipped=[V, U])
        ok, why = self.carried(g, b)
        self.assertTrue(ok, "two back-to-back bumps reran the gate: %s" % why)

    def test_three_back_to_back_bumps_carry(self):
        g = self.gate("t_plain.py"); b = self.book(g)
        self.bump(ver=V)
        self.ship(V, "bump 1")
        self.bump(ver="v102", shipped=[V, U])
        self.ship("v102", "bump 2")
        self.bump(ver="v105", shipped=["v102", V, U])
        self.ship("v105", "bump 3")
        ok, why = self.carried(g, b)
        self.assertTrue(ok, "three back-to-back bumps reran the gate: %s" % why)

    def test_a_middle_row_out_of_order_or_hand_written_runs(self):
        rel = "TASKS.md"
        rem = ["| **v1** | `(this commit)` | v1 — a |"]
        top = "| **v4** | `(this commit)` | v4 — d |"
        bot = "| **v1** | `abcdef12` | v1 — a |"
        self.assertEqual(GL.stamp_file_versions(rel, _hunk(rel, rem, [top, "| **v3** | `abcdef12` | v3 — c |", "| **v2** | `abcdef12` | v2 — b |", bot])), ({"v1"}, {"v4"}))
        for mid in (["| **v2** | `abcdef12` | v2 — b |", "| **v3** | `abcdef12` | v3 — c |"],
                    ["| **v3** | `abcdef12` | v3 — c | extra |"],
                    ["| **v3** | `abcdef12` | v9 — c |"],
                    ["| **v3** | `(this commit)` | v3 — c |"],
                    ["hand prose"]):
            self.assertIsNone(GL.stamp_file_versions(rel, _hunk(rel, rem, [top] + mid + [bot])), mid)

    # --- round 2 A: free text on stamp lines
    def test_a_content_scanner_carries_a_clean_bump(self):
        _write(self.root, "tv/t_scan.py", "import control_app\nopen('bible.html').read()\n")
        _git(self.root, "add", "-A"); _git(self.root, "commit", "-qm", "scan")
        g = self.gate("t_scan.py", name="fixture-plain-name"); b = self.book(g)
        self.bump()
        ok, why = self.carried(g, b)
        self.assertTrue(ok, "a clean coherent bump reran a content scanner: %s" % why)

    def _leaky_bump(self, leak):
        new = _files(V, sha_row=True, note="second")
        new["bible.html"] = new["bible.html"].replace("note:'second'", "note:'second %s'" % leak)
        self.bump(override={"bible.html": new["bible.html"]})

    def test_a_hand_pasted_leak_on_a_stamp_line_reruns_everything(self):
        _write(self.root, "tv/t_scan.py", "import control_app\nopen('bible.html').read()\n")
        _git(self.root, "add", "-A"); _git(self.root, "commit", "-qm", "scan")
        for leak in ("/Us" + "ers/someone/Library/", "10.0." + "0.7", "konyo-3" + ".local", "ghp_" + "b" * 30,
                     "glpat-" + "q" * 20):  # the last one passes the word whitelist, so only the leak check stops it
            g = self.gate("t_scan.py", name="fixture-plain-name")
            _git(self.root, "checkout", "-q", "--", ".")
            b = self.book(g)
            self._leaky_bump(leak)
            self.assertIsNotNone(GL.stamp_file_versions("bible.html", _git(self.root, "diff", "-U0", "HEAD", "--", "bible.html").stdout),
                                 "PREMISE: the leaky line is still a well-formed stamp")
            self.assertFalse(self.carried(g, b)[0], "a leak pasted into a stamp line by hand was carried: %s" % leak)

    def test_an_unloadable_leak_check_is_not_clean(self):
        held = sys.modules.get("stamp_leak")
        sys.modules["stamp_leak"] = None
        try:
            self.assertFalse(GL.free_text_clean(["a clean note"]), "a leak check that cannot load read as clean")
        finally:
            if held is None:
                sys.modules.pop("stamp_leak", None)
            else:
                sys.modules["stamp_leak"] = held
        self.assertTrue(GL.free_text_clean(["a clean note"]))

    def test_the_home_path_gate_always_reruns_on_a_bump(self):
        g = self.gate("t_plain.py", name="test_no_new_home_path_is_published"); b = self.book(g)
        self.bump()
        self.assertFalse(self.carried(g, b)[0], "the home-path gate was carried over a bump")

    def test_the_blueprint_time_line_does_not_rekey_the_map(self):
        a = GL.map_key(self.root)
        self.edit("BLUEPRINT.md", "generated 2026-10-19 10:16", "generated 2026-10-19 13:50")
        self.assertEqual(a, GL.map_key(self.root), "the generated time rebuilt the input map")
        self.edit("BLUEPRINT.md", "# b", "# b gate added")
        self.assertNotEqual(a, GL.map_key(self.root), "a real blueprint change kept the map key")

    def test_the_leak_check_uses_the_home_path_gates_own_pattern(self):
        import stamp_leak
        import test_no_new_home_path_is_published as HP
        self.assertEqual(stamp_leak.HOME.pattern, HP.HOME.pattern, "the leak check drifted from the home-path gate")

    def test_the_bump_refuses_a_leak_in_its_free_text(self):
        import bump_version as BV
        for bad in ("moved the cache out of /Us" + "ers/someone/Library/", "talks to 192.168." + "1.20 now",
                    "the konyo-3" + ".local box", "token ghp_" + "a" * 30):
            self.assertTrue(BV.leak_problem(bad), bad)
        for fine in ("gate memory carries a bump", "Wilson 0.824 against 0.722", "sha e22a1975 and v3.1.2"):
            self.assertIsNone(BV.leak_problem(fine), fine)

    # --- round 3: free text is inert words, or it is content
    REVIEW_NOTE = "see bull-4-u" + ".com/api/intake for the fix"

    def test_the_bump_refuses_free_text_that_is_not_inert_words(self):
        import stamp_leak as L
        for bad in (self.REVIEW_NOTE, "a/b", "C" + ":x", "x.y", "mail a@b", "<b>x</b>", 'say "hi"', "a`b`",
                    "k=v", "it's", "this & that", "100%", "tab\there", "x" * 121, "wilson 0.722"):
            self.assertTrue(L.free_text_problem(bad), bad)
        for fine in ("Fast version bump (gate memory) - carries #245 + more", "Shipped the fix.",
                     "One. Two.", "x" * 120, ""):
            self.assertIsNone(L.free_text_problem(fine), fine)

    def test_the_bump_writes_nothing_for_the_reviews_url_note(self):
        import types
        import bump_version as BV
        held = sys.modules.get("tree_busy")
        sys.modules["tree_busy"] = types.SimpleNamespace(why=lambda r: None)
        try:
            with self.assertRaises(SystemExit) as cm:
                BV.bump("v101", "Door test", self.REVIEW_NOTE, repo=self.root)
        finally:
            if held is None:
                sys.modules.pop("tree_busy", None)
            else:
                sys.modules["tree_busy"] = held
        self.assertIn("REFUSED", str(cm.exception))
        self.assertIn('"ver": "%s"' % U, _read(self.root, "tv/control_app.py"))

    def test_the_bump_refuses_a_note_only_the_inert_words_rule_can_see(self):
        """v3860 - THE CASE ABOVE COULD NOT SEE ITS OWN RULE. Its note carries a URL, so leak_problem (asked first,
        :313) refuses it with "REFUSED" whether or not the inert-words door exists - and the red-proof that removes
        that door (BUMP-FREE-TEXT-REFUSE) stayed GREEN on every CI prover run since 10-23 (BLIND, shard 14). This note
        is no leak and no apostrophe; only free_text_problem refuses it, and the refusal must say so."""
        import types
        import bump_version as BV
        import stamp_leak as L
        note = "100% of the gates carry"
        self.assertIsNone(L.leak_problem(note), "premise: an older refusal would catch this note first")
        self.assertTrue(L.free_text_problem(note), "premise: the inert-words rule must refuse this note")
        held = sys.modules.get("tree_busy")
        sys.modules["tree_busy"] = types.SimpleNamespace(why=lambda r: None)
        try:
            with self.assertRaises(SystemExit) as cm:
                BV.bump("v101", "Door test", note, repo=self.root)
        finally:
            if held is None:
                sys.modules.pop("tree_busy", None)
            else:
                sys.modules["tree_busy"] = held
        self.assertIn("inert words", str(cm.exception), "the bump refused for another reason, or not at all")
        self.assertIn('"ver": "%s"' % U, _read(self.root, "tv/control_app.py"), "the refused bump wrote a stamp")

    def _note_bump(self, note):
        new = _files(V, sha_row=True, note=note)
        new["BLUEPRINT.md"] = "# b\n    generated 2026-10-19 13:50\n"
        for rel, text in new.items():
            _write(self.root, rel, text)

    def test_the_reviews_url_note_pasted_by_hand_reruns_the_door_gate(self):
        _write(self.root, "tv/t_door.py", "import control_app\nURL = 'bull-4-u' + '.com/api/intake'\n")
        _git(self.root, "add", "-A"); _git(self.root, "commit", "-qm", "door")
        g = self.gate("t_door.py", name="fixture-door"); b = self.book(g)
        self._note_bump(self.REVIEW_NOTE)
        self.assertFalse(self.carried(g, b)[0], "the review's URL note carried the door gate")

    def test_a_url_note_reruns_even_a_gate_holding_none_of_its_words(self):
        _write(self.root, "tv/t_scan.py", "import control_app\nopen('bible.html').read()\n")
        _git(self.root, "add", "-A"); _git(self.root, "commit", "-qm", "scan")
        g = self.gate("t_scan.py", name="fixture-plain-name"); b = self.book(g)
        self._note_bump(self.REVIEW_NOTE)
        self.assertFalse(self.carried(g, b)[0], "a URL in the note was carried (the ledger skipped the whitelist)")

    def test_a_gate_holding_a_note_word_reruns(self):
        _write(self.root, "tv/t_word.py", "import control_app\nassert open('bible.html').read().count('Intake') < 2\n")
        _write(self.root, "tv/t_other.py", "import control_app\nprint('fine')\n")
        _git(self.root, "add", "-A"); _git(self.root, "commit", "-qm", "word")
        gw, go = self.gate("t_word.py", name="fixture-word"), self.gate("t_other.py", name="fixture-other")
        b = self.book(gw, go)
        self._note_bump("the INTAKE door now counts once")
        self.assertFalse(self.carried(gw, b)[0], "a gate holding a word of the note was carried")
        self.assertTrue(self.carried(go, b)[0], "a gate holding none of the note's words reran")

    def test_a_gate_whose_regex_or_phrase_moves_reruns(self):
        _write(self.root, "tv/t_rx.py", "import re, control_app\nassert len(re.findall(r'\\bdoor\\s+named\\b', open('bible.html').read())) < 9\n")
        _write(self.root, "tv/t_phrase.py", "import control_app\nassert open('bible.html').read().count('named twice') < 9\n")
        _git(self.root, "add", "-A"); _git(self.root, "commit", "-qm", "rx")
        gr, gp = self.gate("t_rx.py", name="fixture-rx"), self.gate("t_phrase.py", name="fixture-phrase")
        b = self.book(gr, gp)
        self._note_bump("the door is NAMED TWICE")
        self.assertFalse(self.carried(gr, b)[0], "a gate whose regex word moved was carried")
        self.assertFalse(self.carried(gp, b)[0], "a gate whose phrase moved (case-insensitive) was carried")

    def test_the_old_note_leaving_counts_too(self):
        lits = GL.script_literals("x = 'intake'\n")
        self.assertTrue(GL.literal_hit(lits, "note one", "intake note"), "a string the bump REMOVED did not count")
        self.assertIsNone(GL.literal_hit(lits, "same intake", "same intake"))
        self.assertTrue(GL.literal_hit(None, "", ""), "an unparsable script read as untouched")

    def test_a_made_up_middle_row_runs(self):
        g = self.gate("t_plain.py"); b = self.book(g)
        self.bump(ver=V)
        self.ship(V, "bump 1")
        real = _SHAS[V]
        for fake in ("abcdef12", "0" * 40):
            _SHAS[V] = fake
            self.bump(ver="v102", shipped=[V, U])
            self.assertFalse(self.carried(g, GL.Ledger(path=self.led, probes=dict(PROBES)))[0],
                             "a made-up sha %s for a middle row was carried" % fake)
        base = _SHAS[U]
        _git(self.root, "checkout", "-q", "--", ".")
        _git(self.root, "checkout", "-q", "-b", "side", base)
        self.bump(ver=V)
        _git(self.root, "commit", "-qam", "side bump")
        side = self.head()
        _git(self.root, "checkout", "-q", "main")
        _SHAS[V] = side
        self.bump(ver="v102", shipped=[V, U])
        self.assertFalse(self.carried(g, GL.Ledger(path=self.led, probes=dict(PROBES)))[0],
                         "a middle row bound to a commit outside HEAD's history was carried")
        _SHAS[V] = real
        self.bump(ver="v102", shipped=[V, U])
        tasks = _read(self.root, "TASKS.md").replace("v101 — second", "v101 — rewritten", 1)
        _write(self.root, "TASKS.md", tasks)
        self.assertFalse(self.carried(g, GL.Ledger(path=self.led, probes=dict(PROBES)))[0],
                         "a middle row whose text differs from its own commit's row was carried")
        self.bump(ver="v102", shipped=[V, U])
        self.assertTrue(self.carried(g, GL.Ledger(path=self.led, probes=dict(PROBES)))[0], "PREMISE: real rows carry")

    def test_the_leak_check_catches_the_reviews_misses(self):
        import stamp_leak as L
        for bad in ("C:" + "\\\\Users\\\\elad\\\\", "c:" + "\\users\\elad", "%2FUs" + "ers%2Felad%2F",
                    "&#47;Us" + "ers&#47;elad&#47;", "/Us" + "ers/elad", "/ro" + "ot/", "/ho" + "me/elad",
                    "fe80" + "::1", "box.home" + ".arpa", "glpat-" + "a" * 20, "AIza" + "b" * 35,
                    "ghp_" + "c" * 19, "Bear" + "er abcdefgh12"):
            self.assertTrue(L.leak_problem(bad), bad)
        for fine in ("at 12:30 today", "Wilson 0.824", "the users tab", "v3774 - fast bump", "home page"):
            self.assertIsNone(L.leak_problem(fine), fine)

    def test_the_bump_writes_nothing_when_the_note_leaks(self):
        import types
        import bump_version as BV
        held = sys.modules.get("tree_busy")
        sys.modules["tree_busy"] = types.SimpleNamespace(why=lambda r: None)
        try:
            with self.assertRaises(SystemExit) as cm:
                BV.bump("v101", "a name", "see /Us" + "ers/someone/x/", repo=self.root)
        finally:
            if held is None:
                sys.modules.pop("tree_busy", None)
            else:
                sys.modules["tree_busy"] = held
        self.assertIn("REFUSED", str(cm.exception))
        self.assertIn("home path", str(cm.exception), "the leak was not refused as a leak (only the word whitelist caught it)")
        self.assertIn('"ver": "%s"' % U, _read(self.root, "tv/control_app.py"))

    # --- item 3: nothing rides on a stamp line
    def test_code_riding_on_the_build_line_is_not_a_stamp(self):
        rel = "bible.html"
        a = "  window.D2R_BUILD = { id:'v1', name:'v1 - n', date:'2026-10-19', note:'a' };"
        for b in ("  window.D2R_BUILD = { id:'v2', name:'v2 - n', date:'2026-10-19', note:'n' }; fetch('//x').then(eval); window.Y = { note:'z' };",
                  "  window.D2R_BUILD = { id:'v2', name:'v2 - n', date:'2026-10-19', note:'x', hidden:true, note:'n' };"):
            self.assertIsNone(GL.stamp_file_versions(rel, _hunk(rel, [a], [b])), b)
        good = "  window.D2R_BUILD = { id:'v2', name:'v2 - n', date:'2026-10-19', note:'n' };"
        self.assertEqual(GL.stamp_file_versions(rel, _hunk(rel, [a], [good])), ({"v1"}, {"v2"}))

    def test_a_key_riding_on_the_ship_note_is_not_a_stamp(self):
        rel = "tv/WINDOWS_SHIP.json"
        self.assertIsNone(GL.stamp_file_versions(rel, _hunk(rel, ['  "note": "v1: a",'],
                                                            ['  "note": "v2: a", "deploy_url": "http://evil",'])))

    # --- item 4: in place only
    def test_a_moved_stamp_is_not_a_stamp(self):
        rel = "tv/control_app.py"
        d = (_hunk(rel, ['        "ver": "v1",'], [], o=4, n=3)
             + '@@ -9,0 +9,1 @@\n+        "ver": "v2",\n')
        self.assertIsNone(GL.stamp_file_versions(rel, d))
        self.assertIsNone(GL.stamp_file_versions(rel, _hunk(rel, ['        "ver": "v1",'], ['        "ver": "v2",'], o=4, n=7)))

    def test_a_reindented_stamp_is_not_a_stamp(self):
        rel = "tv/control_app.py"
        self.assertIsNone(GL.stamp_file_versions(rel, _hunk(rel, ['        "ver": "v1",'], ['    "ver": "v2",'])))

    def test_a_changed_title_word_is_not_a_stamp(self):
        rel = "bible.html"
        self.assertIsNone(GL.stamp_file_versions(rel, _hunk(rel, ["  <title>A v1 · T</title>"], ["  <title>B v2 · T</title>"])))

    # --- item 5: TASKS.md
    def test_the_ship_table_takes_one_exact_new_top_row(self):
        rel = "TASKS.md"
        rem = ["| **v1** | `(this commit)` | v1 — a |"]
        good = ["| **v2** | `(this commit)` | v2 — b |", "| **v1** | `abcdef12` | v1 — a |"]
        self.assertEqual(GL.stamp_file_versions(rel, _hunk(rel, rem, good)), ({"v1"}, {"v2"}))
        for bad in (["| **v2** | `(this commit)` | v2 — b |", "| **v1** | `abcdef12` | v1 — REWRITTEN |"],
                    ["| **v2** | `(this commit)` | v2 — b |", "| **v1** | `abcdef12` | v1 — a |", "| **v9** | `abcdef12` | v9 — fake |"],
                    ["| **v2** | `abcdef12` | v2 — b |", "| **v1** | `abcdef12` | v1 — a |"],
                    ["| **v2** | `(this commit)` | v3 — b |", "| **v1** | `abcdef12` | v1 — a |"]):
            self.assertIsNone(GL.stamp_file_versions(rel, _hunk(rel, rem, bad)), bad)
        self.assertIsNone(GL.stamp_file_versions(rel, _hunk(rel, [], ["| **v9** | `abcdef12` | v9 — hand |"])))

    # --- the diff reader
    def test_a_removed_dash_dash_line_is_not_a_header(self):
        rel = "tv/tv_diablo.py"
        d = _hunk(rel, ['VERSION = "v1"   # a', "-- x"], ['VERSION = "v2"   # b'])
        self.assertIsNone(GL.stamp_file_versions(rel, d))

    def test_unknown_lines_and_files_fail_closed(self):
        rel = "tv/tv_diablo.py"
        d = _hunk(rel, ['VERSION = "v1"   # a'], ['VERSION = "v2"   # b']) + "\\ No newline at end of file\n"
        self.assertIsNone(GL.stamp_file_versions(rel, d))
        self.assertIsNone(GL.stamp_file_versions("tv/other.py", _hunk("tv/other.py", ["a"], ["b"])))
        self.assertIsNone(GL.stamp_file_versions(rel, ""))

    def test_coherence_needs_every_required_surface_and_no_doubt(self):
        ok = dict((r, ({"v1"}, {"v2"})) for r in GL._STAMP_REQUIRED)
        self.assertTrue(GL.coherent_bump(ok))
        part = dict(ok); part.pop("tv/tv_diablo.py")
        self.assertFalse(GL.coherent_bump(part))
        doubt = dict(ok); doubt["BLUEPRINT.md"] = None
        self.assertFalse(GL.coherent_bump(doubt))
        same = dict((r, ({"v1"}, {"v1"})) for r in GL._STAMP_REQUIRED)
        self.assertFalse(GL.coherent_bump(same))
        empty = dict(ok); empty["RESUME_HERE.md"] = (set(), set())
        self.assertFalse(GL.coherent_bump(empty))

    def test_the_stamp_diff_asks_for_raw_bytes(self):
        with io.open(os.path.join(HERE, "gate_ledger.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('"--no-textconv"', src)
        self.assertIn('"--no-ext-diff"', src)

    def test_every_bump_surface_is_declared(self):
        for rel in ("bible.html", "tv/control_app.py", "tv/tv_diablo.py", "tv/WINDOWS_SHIP.json",
                    "RESUME_HERE.md", "TASKS.md"):
            self.assertIn(rel, GL._STAMP_REQUIRED)

    def test_wilson_of_these_attacks_meets_the_bar(self):
        import confidence
        self.assertGreaterEqual(confidence.wilson_lower(len(RED_PROOF), len(RED_PROOF)), 0.8)


RED_PROOF = [
    {
        'why': 'every stamp-surface path is dropped, so a real edit beside the stamp carries',
        'file': 'gate_ledger.py',
        'find': '        stamped = self.stamp_only(root, sha, changed)  # LEDGER-STAMP-ONLY\n',
        'replace': '        stamped = set(p for p in changed if p in STAMP_SURFACES)  # LEDGER-STAMP-ONLY\n',
        'matches': 1,
    },
    {
        'why': 'stamp detection is switched off, so a coherent bump reruns the gate',
        'file': 'gate_ledger.py',
        'find': '        stamped = self.stamp_only(root, sha, changed)  # LEDGER-STAMP-ONLY\n',
        'replace': '        stamped = set()  # LEDGER-STAMP-ONLY\n',
        'matches': 1,
    },
    {
        'why': 'a non-stamp changed line is accepted',
        'file': 'gate_ledger.py',
        'find': '            if ka is None or kb is None:  # STAMP-OTHER-LINE\n                return None\n',
        'replace': '            if ka is None or kb is None:  # STAMP-OTHER-LINE\n                continue\n',
        'matches': 1,
    },
    {
        'why': 'an unrecognised diff line is accepted',
        'file': 'gate_ledger.py',
        'find': '        return None  # STAMP-UNKNOWN-LINE',
        'replace': '        continue  # STAMP-UNKNOWN-LINE',
        'matches': 1,
    },
    {
        'why': "headers are skipped inside a hunk, so a removed '-- x' line vanishes",
        'file': 'gate_ledger.py',
        'find': '        if not in_hunk and line.startswith(("index ", "--- ", "+++ ")):  # STAMP-HEADER\n',
        'replace': '        if line.startswith(("index ", "--- ", "+++ ")):  # STAMP-HEADER\n',
        'matches': 1,
    },
    {
        'why': 'a moved stamp (different hunk position or count) is accepted',
        'file': 'gate_ledger.py',
        'find': '        if o != n or len(rem) != len(add) or not rem:  # STAMP-IN-PLACE\n',
        'replace': '        if not rem and not add:  # STAMP-IN-PLACE\n',
        'matches': 1,
    },
    {
        'why': 'a re-indented or kind-swapped stamp is accepted',
        'file': 'gate_ledger.py',
        'find': '            if ka[0] != kb[0] or _indent(a) != _indent(b):  # STAMP-PAIRED\n',
        'replace': '            if False:  # STAMP-PAIRED\n',
        'matches': 1,
    },
    {
        'why': 'one surface the reader doubted is ignored, the rest still count as a bump',
        'file': 'gate_ledger.py',
        'find': '    if any(v is None for v in per_file.values()):  # STAMP-ANY-DOUBT\n',
        'replace': '    per_file = dict((k, v) for k, v in per_file.items() if v is not None)\n    if not per_file:  # STAMP-ANY-DOUBT\n',
        'matches': 1,
    },
    {
        'why': 'a partial bump (a required surface missing) is accepted',
        'file': 'gate_ledger.py',
        'find': '    if not _STAMP_REQUIRED <= set(per_file):  # STAMP-REQUIRED\n',
        'replace': '    if not per_file:  # STAMP-REQUIRED\n',
        'matches': 1,
    },
    {
        'why': 'two new versions are accepted as one bump',
        'file': 'gate_ledger.py',
        'find': '    return len(olds) == 1 and len(news) == 1 and olds != news  # STAMP-ONE-VERSION\n',
        'replace': '    return bool(news)  # STAMP-ONE-VERSION\n',
        'matches': 1,
    },
    {
        'why': 'the ship table may take extra rows',
        'file': 'gate_ledger.py',
        'find': '    if o != n or len(rem) != 1 or not 2 <= len(add) <= _MAX_BUMPS + 1:  # STAMP-TASKS-SHAPE\n',
        'replace': '    if len(add) < 1:  # STAMP-TASKS-SHAPE\n',
        'matches': 1,
    },
    {
        'why': 'the bound old row may be rewritten',
        'file': 'gate_ledger.py',
        'find': '    if bound.group("rest") != old.group("rest"):  # STAMP-TASKS-REST\n',
        'replace': '    if False:  # STAMP-TASKS-REST\n',
        'matches': 1,
    },
    {
        'why': 'a gate whose script reads the version is carried',
        'file': 'gate_ledger.py',
        'find': '                    self._verdep[rel] = bool(_VERSION_WORDS.search(fh.read()))  # STAMP-VERSION-SCRIPT\n',
        'replace': '                    self._verdep[rel] = False  # STAMP-VERSION-SCRIPT\n',
        'matches': 1,
    },
    {
        'why': 'a gate named for the build is carried',
        'file': 'gate_ledger.py',
        'find': '        if _VERSION_NAME.search(str(name or "")):  # STAMP-VERSION-NAME\n',
        'replace': '        if False:  # STAMP-VERSION-NAME\n',
        'matches': 1,
    },
    {
        'why': 'a reader-only module in the closure does not mark the gate',
        'file': 'gate_ledger.py',
        'find': '        if any(p in _VERSION_READER_ONLY for p in (row.get("inputs") or [])):  # STAMP-VERSION-READER\n',
        'replace': '        if False:  # STAMP-VERSION-READER\n',
        'matches': 1,
    },
    {
        'why': 'the stamp-only set is never removed from the change set',
        'file': 'gate_ledger.py',
        'find': '            changed = changed - stamped  # STAMP-DROP\n',
        'replace': '            changed = changed  # STAMP-DROP\n',
        'matches': 1,
    },
    {
        'why': 'a greedy quoted value lets code ride on the build line',
        'file': 'gate_ledger.py',
        'find': '_SQ = r"\'(?:[^\'\\\\\\n]|\\\\.)*\'"',
        'replace': '_SQ = r"\'.*\'"',
        'matches': 1,
    },
    {
        'why': 'textconv is allowed on the stamp diff',
        'file': 'gate_ledger.py',
        'find': '"--no-ext-diff", "--no-textconv",',
        'replace': '"--no-ext-diff",',
        'matches': 1,
    },
    {
        'why': 'an IP in the note is accepted',
        'file': 'stamp_leak.py',
        'find': '    if _LEAK_IP.search(t):  # BUMP-LEAK-IP\n',
        'replace': '    if False:  # BUMP-LEAK-IP\n',
        'matches': 1,
    },
    {
        'why': 'a hostname in the note is accepted',
        'file': 'stamp_leak.py',
        'find': '    if _LEAK_HOST.search(t):  # BUMP-LEAK-HOST\n',
        'replace': '    if False:  # BUMP-LEAK-HOST\n',
        'matches': 1,
    },
    {
        'why': 'a token in the note is accepted',
        'file': 'stamp_leak.py',
        'find': '    if _LEAK_TOKEN.search(t):  # BUMP-LEAK-TOKEN\n',
        'replace': '    if False:  # BUMP-LEAK-TOKEN\n',
        'matches': 1,
    },
    {
        'why': 'the bump writes a leaking note',
        'file': 'bump_version.py',
        'find': '        if _leak:  # BUMP-LEAK-REFUSE\n',
        'replace': '        if False:  # BUMP-LEAK-REFUSE\n',
        'matches': 1,
    },
    {
        'why': 'a malformed middle ship row is accepted',
        'file': 'gate_ledger.py',
        'find': '        if not m or m.group("v") != m.group("s"):  # STAMP-TASKS-MIDDLE\n            return None\n',
        'replace': '        if not m:  # STAMP-TASKS-MIDDLE\n            continue\n',
        'matches': 1,
    },
    {
        'why': 'ship rows out of order are accepted',
        'file': 'gate_ledger.py',
        'find': '    if any(a <= b for a, b in zip(nums, nums[1:])):  # STAMP-TASKS-ORDER\n',
        'replace': '    if False:  # STAMP-TASKS-ORDER\n',
        'matches': 1,
    },
    {
        'why': 'only one bump is accepted, so back-to-back bumps rerun everything',
        'file': 'gate_ledger.py',
        'find': '    if o != n or len(rem) != 1 or not 2 <= len(add) <= _MAX_BUMPS + 1:  # STAMP-TASKS-SHAPE\n',
        'replace': '    if o != n or len(rem) != 1 or len(add) != 2:  # STAMP-TASKS-SHAPE\n',
        'matches': 1,
    },
    {
        'why': 'a leak on an added stamp line is accepted',
        'file': 'gate_ledger.py',
        'find': '        if stamp_leak.free_text_problem(t) or stamp_leak.leak_problem(t):  # STAMP-FREE-TEXT\n',
        'replace': '        if stamp_leak.free_text_problem(t):  # STAMP-FREE-TEXT\n',
        'matches': 1,
    },
    {
        'why': 'the new free text is never checked',
        'file': 'gate_ledger.py',
        'find': ' and rows_ok and free_text_clean(texts)  # STAMP-ALL-CLEAN',
        'replace': ' and rows_ok  # STAMP-ALL-CLEAN',
        'matches': 1,
    },
    {
        'why': 'the leak module failing to load counts as clean',
        'file': 'gate_ledger.py',
        'find': '    except Exception:\n        return False\n    for t in texts:',
        'replace': '    except Exception:\n        return True\n    for t in texts:',
        'matches': 1,
    },
    {
        'why': 'the home-path gate is carried over a bump',
        'file': 'gate_ledger.py',
        'find': '        return str(name or "") in _ALWAYS_RERUN  # STAMP-ALWAYS-RERUN\n',
        'replace': '        return False  # STAMP-ALWAYS-RERUN\n',
        'matches': 1,
    },
    {
        'why': 'the blueprint time line still rekeys the map',
        'file': 'gate_ledger.py',
        'find': '    raw = _BLUEPRINT_STAMP.sub(b"    generated -", raw, count=1)  # LEDGER-MAPKEY-STAMP\n',
        'replace': '    pass  # LEDGER-MAPKEY-STAMP\n',
        'matches': 1,
    },
    {
        'why': 'the whole blueprint is blanked, so a real change keeps the map',
        'file': 'gate_ledger.py',
        'find': '    raw = _BLUEPRINT_STAMP.sub(b"    generated -", raw, count=1)  # LEDGER-MAPKEY-STAMP\n',
        'replace': '    raw = b""  # LEDGER-MAPKEY-STAMP\n',
        'matches': 1,
    },
    {
        'why': 'the bump accepts a note that is not inert words',
        'file': 'bump_version.py',
        'find': '        if _inert:  # BUMP-FREE-TEXT-REFUSE\n',
        'replace': '        if False:  # BUMP-FREE-TEXT-REFUSE\n',
        'matches': 1,
    },
    {
        'why': 'the free-text whitelist lets a slash or colon through',
        'file': 'stamp_leak.py',
        'find': '_FREE_BAD = re.compile(r"[^A-Za-z0-9 ,()+#.\\-]")\n',
        'replace': '_FREE_BAD = re.compile(r"[^A-Za-z0-9 ,()+#.:/\\-]")\n',
        'matches': 1,
    },
    {
        'why': 'a period inside a word (a domain) is allowed',
        'file': 'stamp_leak.py',
        'find': '    if _FREE_DOT.search(t):  # FREE-DOT\n',
        'replace': '    if False:  # FREE-DOT\n',
        'matches': 1,
    },
    {
        'why': 'free text has no length cap',
        'file': 'stamp_leak.py',
        'find': '    if len(t) > FREE_TEXT_MAX:  # FREE-MAX\n',
        'replace': '    if False:  # FREE-MAX\n',
        'matches': 1,
    },
    {
        'why': 'the ledger checks leaks but not the whitelist, so the review URL carries',
        'file': 'gate_ledger.py',
        'find': '        if stamp_leak.free_text_problem(t) or stamp_leak.leak_problem(t):  # STAMP-FREE-TEXT\n',
        'replace': '        if stamp_leak.leak_problem(t):  # STAMP-FREE-TEXT\n',
        'matches': 1,
    },
    {
        'why': 'a gate holding a word of the note is carried',
        'file': 'gate_ledger.py',
        'find': '        return literal_hit(self._verdep[k], moved[0], moved[1]) is not None  # STAMP-WORD-HIT',
        'replace': '        return False  # STAMP-WORD-HIT',
        'matches': 1,
    },
    {
        'why': 'a made-up middle-row sha is accepted',
        'file': 'gate_ledger.py',
        'find': '            if anc is None or anc.returncode != 0:  # STAMP-ROW-ANCESTOR\n',
        'replace': '            if anc is None:  # STAMP-ROW-ANCESTOR\n',
        'matches': 1,
    },
    {
        'why': 'a middle row whose text differs from its own commit is accepted',
        'file': 'gate_ledger.py',
        'find': '            if own not in (show.stdout or "").splitlines():  # STAMP-ROW-OWN\n',
        'replace': '            if False:  # STAMP-ROW-OWN\n',
        'matches': 1,
    },
    {
        'why': 'the shipped rows are never checked against git',
        'file': 'gate_ledger.py',
        'find': ' and rows_ok and free_text_clean(texts)  # STAMP-ALL-CLEAN',
        'replace': ' and free_text_clean(texts)  # STAMP-ALL-CLEAN',
        'matches': 1,
    },
    {
        'why': 'escaped, encoded and lowercase home paths are missed',
        'file': 'stamp_leak.py',
        'find': '    if _HOME_ANY.search(t):  # BUMP-LEAK-HOME-ANY\n',
        'replace': '    if False:  # BUMP-LEAK-HOME-ANY\n',
        'matches': 1,
    },
    {
        'why': 'IPv6 addresses are missed',
        'file': 'stamp_leak.py',
        'find': '           for m in _LEAK_IP6.finditer(t)):  # BUMP-LEAK-IP6\n',
        'replace': '           for m in _LEAK_IP6.finditer(t)) and False:  # BUMP-LEAK-IP6\n',
        'matches': 1,
    },
    {
        'why': 'GitLab, Google and Bearer tokens are missed',
        'file': 'stamp_leak.py',
        'find': '                         r"glpat-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{30,}|"\n',
        'replace': '                         r""\n',
        'matches': 1,
    },
    {
        'why': 'a moved literal is ignored',
        'file': 'gate_ledger.py',
        'find': '        if _count(al, low) != _count(rl, low):  # STAMP-LITERAL-MOVED\n',
        'replace': '        if False:  # STAMP-LITERAL-MOVED\n',
        'matches': 1,
    },
    {
        'why': 'a regex word that moved is ignored',
        'file': 'gate_ledger.py',
        'find': '            if _count(al, w) != _count(rl, w):  # STAMP-REGEX-WORD-MOVED\n',
        'replace': '            if False:  # STAMP-REGEX-WORD-MOVED\n',
        'matches': 1,
    },
    {
        'why': 'a script that does not parse reads as untouched',
        'file': 'gate_ledger.py',
        'find': '        return "<script did not parse>"\n',
        'replace': '        return None\n',
        'matches': 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=1)
