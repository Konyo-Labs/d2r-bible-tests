# -*- coding: utf-8 -*-
"""REG-2602 - A COHERENT VERSION BUMP KEEPS THE PROOF KEYS OF THE LAWS THAT NEVER READ THE VERSION.

MEASURED 2026-10-23: 824 of 1024 laws hold a stamp surface (bible.html 781, control_app 704, tv_diablo 664,
WINDOWS_SHIP 662, TASKS 660, BLUEPRINT 652, RESUME 649), and bump_version rewrites only stamp lines in them - b58879ec
(v3790) moved 15 lines in 7 files. The verdict-cache key hashed raw bytes, so a proof the census banked on the commit
before a ship was a miss on the ship itself, and the Mac re-proved ~80% of the census.

heart2 now keys those files with every WHOLE stamp line (gate_ledger.STAMP_SURFACES, plus RESUME's "gates registered"
row) replaced by its kind - for a law gate_ledger would carry over a bump (its name, its script and its closure's
reader-only modules never speak of the version; its proof's own text names no version), and only while every
required surface carries the same one version. Anything else keys raw bytes, as before.

Each case builds a fixture repo, keys one proof with the real _VerdictCache.key_for, changes the fixture, keys again.
[[feedback-fixtures-never-touch-live-data]] RED_PROOF below.
"""
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import heart2 as H  # noqa: E402

LAW = "test_fixture_law.py"
PROOF = {"why": "a fixture proof", "file": "control_app.py", "find": "SALT = 1", "replace": "SALT = 2", "matches": 1}


def _surfaces(ver, rows=1, gates=1040, page="var a = 1;", note="a note", subject="shipped",
              asked="ask run_gates for now"):
    tasks = "".join(u"| **v%d** | `abcdef1%d` | v%d \u2014 %s |\n" % (100 - i, i, 100 - i, subject) for i in range(rows))
    return {
        "bible.html": ("<html><head>\n  <title>Konyo Bible %s · TV</title>\n"
                       '<meta name="d2r-build" content="%s">\n'
                       '<meta name="d2r-build-date" content="2026-10-23">\n'
                       '<meta name="d2r-build-note" content="%s">\n</head><body><script>\n'
                       "%s\n"
                       "  window.D2R_BUILD = { id:'%s', name:'%s - n', date:'2026-10-23', note:'%s' };\n"
                       "</script></body></html>\n") % (ver, ver, note, page, ver, ver, note),
        "tv/control_app.py": ('DOCS = ("RESUME_HERE.md", "TASKS.md", "BLUEPRINT.md")\n'
                              'def status():\n    return {\n        "ver": "%s",\n    }\nSALT = 1\n') % ver,
        "tv/tv_diablo.py": 'VERSION = "%s"   # the build\n' % ver,
        "tv/WINDOWS_SHIP.json": '{\n  "ver": "%s",\n  "note": "%s: a note",\n  "x": 1\n}\n' % (ver, ver),
        "RESUME_HERE.md": ("# resume\n<!-- fp: ver=%s -->\n| version stamp | %s |\n"
                           "| gates registered | %d *(when this was written — %s)* |\n"
                           "*Derived 2026-10-23 10:24 by `tv/resume_state.py`. Everything outside these markers is "
                           "narrative a machine cannot measure, written by hand.*\nnarrative\n") % (ver, ver, gates, asked),
        "TASKS.md": "# tasks\n| ver | sha | what |\n" + tasks + "an open task\n",
        "BLUEPRINT.md": "# blueprint\n    generated 2026-10-23 10:%02d\n" % (rows % 60),
    }


class AVersionBumpKeepsTheProofsOfLawsThatNeverReadTheVersion(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pk_reg2602_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.tv = os.path.join(self.root, "tv")
        os.makedirs(self.tv)
        for mod in ("gate_ledger.py", "stamp_leak.py"):
            shutil.copy(os.path.join(HERE, mod), os.path.join(self.tv, mod))
        self.law("import control_app\nimport tv_diablo\nPAGE = '../bible.html'\n")
        self.write(_surfaces("v100"))

    def write(self, files):
        for rel, text in files.items():
            with open(os.path.join(self.root, *rel.split("/")), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)

    def law(self, src):
        with open(os.path.join(self.tv, LAW), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(src)

    def key(self, pr=PROOF):
        """a fresh cache each time, as a second machine keys it -> (key, inputs)"""
        c = H._VerdictCache(path=os.path.join(self.root, "cache.json"), say=lambda *a, **k: None)
        k, rels, why = c.key_for(self.tv, LAW[:-3], LAW, pr)
        self.assertIsNone(why, "PREMISE: the fixture law is unkeyable: %s" % why)
        for rel in ("bible.html", "tv/control_app.py", "tv/tv_diablo.py", "RESUME_HERE.md", "TASKS.md"):
            self.assertIn(rel, rels, "PREMISE: %s is not an input of the fixture law" % rel)
        return k, rels

    def test_a_coherent_bump_keeps_the_key(self):
        before, _ = self.key()
        self.write(_surfaces("v101", rows=2, gates=1085))
        self.assertEqual(self.key()[0], before)

    def test_a_change_off_the_stamp_lines_moves_the_key(self):
        before, _ = self.key()
        self.write(_surfaces("v100", page="var a = 2;"))
        self.assertNotEqual(self.key()[0], before)

    def test_code_riding_on_a_stamp_line_moves_the_key(self):
        ride = 'var x = %d; // <meta name="d2r-build" content="v100">'
        self.write(_surfaces("v100", page=ride % 1))
        before, _ = self.key()
        self.write(_surfaces("v100", page=ride % 2))
        self.assertNotEqual(self.key()[0], before)

    def test_a_one_surface_hand_bump_moves_the_key(self):
        before, _ = self.key()
        files = _surfaces("v100")
        files["tv/tv_diablo.py"] = _surfaces("v101")["tv/tv_diablo.py"]
        self.write(files)
        self.assertNotEqual(self.key()[0], before)

    def test_a_law_whose_script_reads_the_version_keys_raw_bytes(self):
        self.law("import control_app\nimport tv_diablo\nPAGE = '../bible.html'\nV = tv_diablo.VERSION\n")
        before, rels = self.key()
        self.assertNotIn("tv/gate_ledger.py", rels)
        self.write(_surfaces("v101", rows=2, gates=1085))
        self.assertNotEqual(self.key()[0], before)

    def test_a_law_that_imports_a_version_reader_keys_raw_bytes(self):
        with open(os.path.join(self.tv, "version_stamp_gate.py"), "w", encoding="utf-8") as fh:
            fh.write("X = 1\n")
        with open(os.path.join(self.tv, "hub.py"), "w", encoding="utf-8") as fh:
            fh.write("import version_stamp_gate\n")      # the law's own script never says it: only its closure does
        self.law("import control_app\nimport tv_diablo\nimport hub\nPAGE = '../bible.html'\n")
        before, _ = self.key()
        self.write(_surfaces("v101", rows=2, gates=1085))
        self.assertNotEqual(self.key()[0], before)

    def test_a_reader_a_hub_only_names_is_not_a_read(self):
        """run_gates names tv/windows_boot_check.py in a description; 43 of 76 sampled closures held it that way"""
        with open(os.path.join(self.tv, "windows_boot_check.py"), "w", encoding="utf-8") as fh:
            fh.write("X = 1\n")
        with open(os.path.join(self.tv, "hub.py"), "w", encoding="utf-8") as fh:
            fh.write("WHY = 'tv/windows_boot_check.py'\n")
        self.law("import control_app\nimport tv_diablo\nimport hub\nPAGE = '../bible.html'\n")
        before, rels = self.key()
        self.assertIn("tv/windows_boot_check.py", rels, "PREMISE: the hub's named reader is not an input")
        self.write(_surfaces("v101", rows=2, gates=1085))
        self.assertEqual(self.key()[0], before)

    def test_a_ship_row_that_moves_a_word_the_law_counts_moves_the_key(self):
        """second eye - a law counting a word in the docs control_app names: one inert ship row gains the word"""
        self.law("import control_app\nimport tv_diablo\nPAGE = '../bible.html'\nBAD = 'FIXME'\n")
        before, _ = self.key()
        self.write(_surfaces("v100", subject="FIXME later"))
        self.assertNotEqual(self.key()[0], before)

    def test_a_same_version_note_the_law_counts_moves_the_key(self):
        self.law("import control_app\nimport tv_diablo\nPAGE = '../bible.html'\nBAD = 'FIXME'\n")
        before, _ = self.key()
        self.write(_surfaces("v100", note="FIXME note"))
        self.assertNotEqual(self.key()[0], before)

    def test_a_note_that_is_not_inert_words_is_never_masked(self):
        before, _ = self.key()
        self.write(_surfaces("v100", note="see /Users" + "/someone/x"))
        self.assertNotEqual(self.key()[0], before)

    def test_a_law_that_names_the_version_literally_keys_it(self):
        """second eye - test_page_names_current: no version word, only 'v100' in its script"""
        self.law("import control_app\nimport tv_diablo\nPAGE = '../bible.html'\nWANT = 'v100'\n")
        before, _ = self.key()
        self.write(_surfaces("v101", rows=2, gates=1085))
        self.assertNotEqual(self.key()[0], before)

    def test_one_cache_sees_a_hand_bump_made_after_its_first_key(self):
        """second eye - the coherence verdict is memoised on the surfaces' bytes, not once per cache"""
        c = H._VerdictCache(path=os.path.join(self.root, "cache.json"), say=lambda *a, **k: None)
        before = c.key_for(self.tv, LAW[:-3], LAW, PROOF)[0]
        files = _surfaces("v100")
        files["tv/tv_diablo.py"] = _surfaces("v101")["tv/tv_diablo.py"]
        self.write(files)
        self.assertNotEqual(c.key_for(self.tv, LAW[:-3], LAW, PROOF)[0], before)

    def test_the_gates_row_with_other_words_is_never_masked(self):
        """second eye - only the count of RESUME's gates row varies; any other words keep the line raw"""
        before, _ = self.key()
        self.write(_surfaces("v100", asked="see /Users/someone"))
        self.assertNotEqual(self.key()[0], before)

    def test_a_counted_word_moving_between_surfaces_moves_the_key(self):
        """second eye - literal counts are per surface: FIXME leaving a TASKS subject for the bible note is a move"""
        self.law("import control_app\nimport tv_diablo\nPAGE = '../bible.html'\nBAD = 'FIXME'\n")
        self.write(_surfaces("v100", rows=2, subject="FIXME later"))   # two rows: FIXME twice, as the page notes it
        before, _ = self.key()
        self.write(_surfaces("v100", rows=2, note="FIXME note"))
        self.assertNotEqual(self.key()[0], before)

    def test_a_counted_word_changing_case_moves_the_key(self):
        self.law("import control_app\nimport tv_diablo\nPAGE = '../bible.html'\nBAD = 'Fixme'\n")
        self.write(_surfaces("v100", note="Fixme note"))
        before, _ = self.key()
        self.write(_surfaces("v100", note="fixme note"))
        self.assertNotEqual(self.key()[0], before)

    def test_a_needle_held_only_in_a_regex_moves_the_key(self):
        self.law("import re\nimport control_app\nimport tv_diablo\nPAGE = '../bible.html'\n"
                 "HIT = re.compile(r'FI[X]ME')\n")
        before, _ = self.key()
        self.write(_surfaces("v100", note="FIXME note"))
        self.assertNotEqual(self.key()[0], before)

    def test_a_proof_naming_a_short_version_keys_raw_bytes(self):
        pr = dict(PROOF, find='"ver": "v99"', replace='"ver": "v1"')
        before, _ = self.key(pr)
        self.write(_surfaces("v101", rows=2, gates=1085))
        self.assertNotEqual(self.key(pr)[0], before)

    def test_a_proof_that_names_a_version_keys_raw_bytes(self):
        pr = dict(PROOF, find='"ver": "v100"', replace='"ver": "v1"')
        before, _ = self.key(pr)
        self.write(_surfaces("v101", rows=2, gates=1085))
        self.assertNotEqual(self.key(pr)[0], before)

    def test_a_masked_key_holds_the_stamp_rule_and_never_meets_a_raw_one(self):
        masked, rels = self.key()
        self.assertIn("tv/gate_ledger.py", rels, "the stamp rule's own file is not an input, so a rule change keeps keys")
        self.assertIn("tv/stamp_leak.py", rels, "the inert-text rule's own file is not an input, so a rule change keeps keys")
        self.law("import control_app\nimport tv_diablo\nPAGE = '../bible.html'\nV = tv_diablo.VERSION\n")
        self.assertNotEqual(self.key()[0], masked)
        c = H._VerdictCache(path=os.path.join(self.root, "cache.json"), say=lambda *a, **k: None)
        self.assertTrue(c._masked_sha(os.path.join(self.root, "bible.html"), "bible.html")[0].startswith("m:"))


if __name__ == "__main__":
    unittest.main()


RED_PROOF = [
    {
        "why": "REG-2602 - the stamp lines are never masked: every bump moves every key",
        "file": "heart2.py",
        "find": "            if mask:\n                inputs = sorted(set(inputs) | {os.path.join(sandbox, \"gate_ledger.py\"), os.path.join(sandbox, \"stamp_leak.py\")})\n",
        "replace": "            mask = False\n",
        "matches": 1,
    },
    {
        "why": "REG-2602 - masking ignores whether the tree's stamps agree, so a one-file hand bump keeps keys",
        "file": "heart2.py",
        "find": "            mask = (ver is not None and not reads",
        "replace": "            mask = (True and not reads",
        "matches": 1,
    },
    {
        "why": "REG-2602 - a law that reads the version is masked like any other",
        "file": "heart2.py",
        "find": "            mask = (ver is not None and not reads",
        "replace": "            mask = (ver is not None and True",
        "matches": 1,
    },
    {
        "why": "REG-2602 - a proof whose own text names a version is masked",
        "file": "heart2.py",
        "find": "                    and not _PROOF_VERSIONISH.search(pk))",
        "replace": "                    )",
        "matches": 1,
    },
    {
        "why": "REG-2602 - a stamp line with code riding on it is masked by a search, not a whole-line match",
        "file": "heart2.py",
        "find": "            k = GL.stamp_kinds(rel, bare)\n            if k is None:\n                k = next(",
        "replace": "            k = next(((kind, m) for kind, pat in GL.STAMP_SURFACES.get(rel, ()) for m in [re.search(pat.pattern.strip(\"^$\"), bare)] if m), None)\n            if k is None:\n                k = next(",
        "matches": 1,
    },
    {
        "why": "REG-2602 - RESUME's gates-registered row is not masked, so every bump that adds a law moves the key",
        "file": "heart2.py",
        "find": "                k = next(((kind, m) for kind, pat in _STAMP_EXTRA.get(rel, ()) for m in [pat.match(bare)] if m), None)\n",
        "replace": "                k = None\n",
        "matches": 1,
    },
    {
        "why": "REG-2602 - the stamp rules' files are not inputs of a masked key",
        "file": "heart2.py",
        "find": ", os.path.join(sandbox, \"stamp_leak.py\")})\n",
        "replace": "})\n",
        "matches": 1,
    },
    {
        "why": "REG-2602 - a masked digest carries no prefix, so it can meet a raw one",
        "file": "heart2.py",
        "find": "(\"m:\" + hashlib.sha256(m[0]).hexdigest(), m[1])",
        "replace": "(hashlib.sha256(m[0]).hexdigest(), m[1])",
        "matches": 1,
    },
    {
        "why": "REG-2602 - each ship row is its own mark, so the row a bump adds moves the key",
        "file": "heart2.py",
        "find": "                if not (out and out[-1] == \"\\0STAMP:ship\"):   # a bump ADDS a row: the run of rows is one mark\n",
        "replace": "                if True:\n",
        "matches": 1,
    },
    {
        "why": "REG-2602 - a closure that imports a version reader is masked",
        "file": "heart2.py",
        "find": "    if any(os.path.basename(r)[:-3] in imported for r in GL._VERSION_READER_ONLY):\n        return True\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-2602 - a reader a hub only names in a string counts as imported",
        "file": "heart2.py",
        "find": "            if got is not None:\n                out |= set(got[0])\n",
        "replace": "            out |= set(got[0]) if got is not None else {os.path.basename(p)[:-3]}\n",
        "matches": 1,
    },
    {
        "why": "REG-2602 - second eye: a note or ship subject that is not inert words is masked unchecked",
        "file": "heart2.py",
        "find": "            if stamp_leak.free_text_problem(t) or stamp_leak.leak_problem(t, machine=False):\n                return False\n",
        "replace": "            pass\n",
        "matches": 1,
    },
    {
        "why": "REG-2602 - second eye: a loose TASKS row (free text never checked) is masked",
        "file": "heart2.py",
        "find": "for r in (GL._TASK_NEW, GL._TASK_SHIPPED)",
        "replace": "for r in (GL._TASK_NEW, GL._TASK_OLD, GL._TASK_BOUND, GL._TASK_SHIPPED)",
        "matches": 1,
    },
    {
        "why": "REG-2602 - second eye: the law's own literals are not counted in the masked text, so a word it scans for can move unseen",
        "file": "heart2.py",
        "find": "            for rel, gone in away:   # per surface",
        "replace": "            for rel, gone in []:   # per surface",
        "matches": 1,
    },
    {
        "why": "REG-2602 - second eye: a literal's count is not taken, so only which literals exist is keyed",
        "file": "heart2.py",
        "find": "        out.append((lit, GL._count(low, lit.lower()), text.count(lit)))",
        "replace": "        out.append((lit, 0, 0))",
        "matches": 1,
    },
    {
        "why": "REG-2602 - second eye: the coherence verdict is memoised once per cache, so a hand bump mid-run keeps keys",
        "file": "heart2.py",
        "find": "vk, rk = (\"REG-2602 version\", repo) + surf,",
        "replace": "vk, rk = (\"REG-2602 version\", repo),",
        "matches": 1,
    },
    {
        "why": "REG-2602 - second eye: RESUME's gates row masks whatever words ride with the count",
        "file": "heart2.py",
        "find": "ask run_gates for now\\)\\* \\|$\")),)}",
        "replace": "[^\\n]*\\|$\")),)}",
        "matches": 1,
    },
    {
        "why": "REG-2602 - second eye: literal counts are pooled across surfaces, so a word moving file to file keeps the key",
        "file": "heart2.py",
        "find": "            for rel, gone in away:   # per surface",
        "replace": "            for rel, gone in [(\"*\", \"\\n\".join(g for _, g in away))] if away else []:   # per surface",
        "matches": 1,
    },
    {
        "why": "REG-2602 - second eye: only gate_ledger's case-free count is keyed, so a case change keeps the key",
        "file": "heart2.py",
        "find": "GL._count(low, lit.lower()), text.count(lit)))",
        "replace": "GL._count(low, lit.lower()), 0))",
        "matches": 1,
    },
    {
        "why": "REG-2602 - second eye: a regex's matches are not counted, only its leftover words",
        "file": "heart2.py",
        "find": "        out.append((\"re\", pat, hits))\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-2602 - second eye: a proof naming a short version (v99, v1.2) is masked",
        "file": "heart2.py",
        "find": "_PROOF_VERSIONISH = re.compile(r\"\\bv\\d+(?:\\.\\d+)*\\b\")",
        "replace": "_PROOF_VERSIONISH = re.compile(r\"\\bv\\d{3,}\\b\")",
        "matches": 1,
    },
]
