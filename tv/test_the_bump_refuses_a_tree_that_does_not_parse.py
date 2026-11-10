# -*- coding: utf-8 -*-
"""THE VERSION STAMP IS THE MOMENT THE TREE BECOMES SOMETHING HE EXECUTES, SO IT MUST PARSE FIRST.

⚠⚠ THIS EXISTS BECAUSE I PUT A SyntaxError ON HIS LIVE SCREEN THROUGH THIS EXACT DOOR.
2026-09-14: a splice in bible.html used `} catch(e){}` as its END anchor and left it behind, so the
file carried a bare catch closing nothing. I then ran `bump_version.py`, which cheerfully stamped
v3100 onto a file the browser refuses to parse — and HIS CONSOLE EXECS THE WORKING TREE, so
`window.renderSubMeter` was never assigned on his screen until the second eye found it on the
shipped diff.

**The gate that catches this already existed.** `js-syntax` is registered in run_gates and parses
every surface in a real engine. I ran `visual_lock_invariant` after the edit — because that is what
had refused the push — and not the one that asks whether the file still parses. A law nobody runs
is a law nobody applied, and no amount of adding laws fixes that.
[[carved-skill-unloaded-is-unapplied]] [[execs-the-working-tree]]

⚠ SO THE CHECK MOVED TO THE CHOKE POINT INSTEAD. Every change passes through the version bump — the
four stamps move together or none do — and the block there already promised *"nothing touches disk
until all four are known good"*. Until v3103 "known good" meant only that a regex matched. Parsing
is what that sentence was always claiming. [[the-unjoined-end]]

⚠ AND IT PARSES THE ONE LINE THE TOOL ITSELF WRITES. `note` is free text landing inside a
single-quoted JS string literal. Two guards above it refuse an apostrophe and a callable CSS token
— the two spellings that have actually bitten — but neither is a parser, and a guard list of past
accidents does not cover the next one.
"""
import ast
import io
import os
import sys
import unittest

from console_safe import enable as _console_safe_enable

_console_safe_enable()

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bump_version as B        # noqa: E402


class TestTheBumpRefusesATreeThatDoesNotParse(unittest.TestCase):

    # ── 1. the tree as it stands is accepted ──────────────────────────────────────────────────
    def test_the_preflight_accepts_a_parsing_tree(self):
        """And when it is sabotaged, THIS is the assertion that goes red."""
        try:
            B._preflight()
        except SystemExit as e:
            self.fail("the bump refuses to stamp the CURRENT tree — something in it does not "
                      "parse:\n%s" % e)
        print("   preflight: the working tree parses, so a stamp is allowed")

    # ── 2. the ARTIFACT is parsed, not a line of it ───────────────────────────────────────────
    def test_the_spliced_page_is_parsed_not_just_the_line(self):
        """⚠⚠ v3103 CHECKED THE LINE AND THAT WAS NOT THE FILE. A cross-family read found it the
        same night it shipped: `note` lands inside a `<script>` block, so a note containing
        `</script>` is PERFECTLY VALID JAVASCRIPT in isolation and still ends the block. The old
        `_parses_as_js` returned None for it while the extractor fed node an unterminated string
        and an unclosed IIFE. The v1478 apostrophe failure wearing an HTML tag.
        [[the-unjoined-end]]"""
        s = io.open(os.path.join(B.REPO, "bible.html"), encoding="utf-8").read()
        a = s.index("  window.D2R_BUILD = { id:'")
        b = s.index("\n", a)
        def spliced(note):
            return s[:a] + ("  window.D2R_BUILD = { id:'v1', name:'a', date:'b', note:'%s' };"
                            % note) + s[b:]
        ok = B._parses_as_page(spliced("a clean note"))
        tag = B._parses_as_page(spliced("closed the </script> tag"))
        esc = B._parses_as_page(spliced("ends with a backslash \\"))
        print("   spliced page: clean=%r · </script>=%r · backslash=%r"
              % (ok, (tag or "")[:48], (esc or "")[:48]))
        self.assertIsNone(ok, "a clean note was rejected: %r" % ok)
        self.assertTrue(tag, "a note containing </script> was ACCEPTED — it is valid JS in "
                             "isolation and terminates the script block in the page")
        self.assertTrue(esc, "a note ending in a backslash was ACCEPTED — it escapes the closing "
                             "quote of the string it lands in")

    # ── 3. and it runs BEFORE anything is computed or written ─────────────────────────────────
    def test_the_preflight_runs_before_the_first_write(self):
        """⚠ ORDER IS THE WHOLE POINT. A check after the writes is a report about damage already
        done, on a tree his console is already executing."""
        with io.open(os.path.join(HERE, "bump_version.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        fn = next((n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "bump"), None)
        self.assertIsNotNone(fn, "bump() is gone")
        pre_lines = [n.lineno for n in ast.walk(fn)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                     and n.func.id == "_preflight"]
        append_lines = [n.lineno for n in ast.walk(fn)
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "append"
                        and isinstance(n.func.value, ast.Name) and n.func.value.id == "pending"]
        print("   _preflight() call line(s): %s · first pending.append at %s"
              % (pre_lines, min(append_lines) if append_lines else None))
        self.assertEqual(len(pre_lines), 1,
                         "bump() calls _preflight %d time(s) — expected exactly once"
                         % len(pre_lines))
        self.assertTrue(append_lines, "bump() no longer builds a pending list")
        self.assertLess(pre_lines[0], min(append_lines),
                        "_preflight runs AFTER the first pending write is computed — a check that "
                        "lands after the damage is a report, not a guard")

    # ── 4. it reuses the existing parser rather than growing a second one ─────────────────────
    def test_it_reuses_the_js_syntax_gate(self):
        with io.open(os.path.join(HERE, "bump_version.py"), encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src)
        imports = [n for n in ast.walk(tree)
                   if isinstance(n, ast.Import)
                   and any(a.name == "js_syntax_gate" for a in n.names)]
        print("   `import js_syntax_gate` sites in bump_version: %d" % len(imports))
        self.assertGreaterEqual(
            len(imports), 1,
            "bump_version no longer reuses js_syntax_gate — a second copy of the <script> block "
            "extractor is exactly the drift that lets two parsers disagree about one file")


    # ── 5. AND IT REFUSES A BROKEN ONE — the half the first cut could not prove ────────────────
    def _temp_repo(self):
        """A throwaway tree holding only the four files the bump touches."""
        import shutil
        import tempfile
        d = tempfile.mkdtemp(prefix="bumptree-")
        self.addCleanup(shutil.rmtree, d, True)
        os.makedirs(os.path.join(d, "tv"), exist_ok=True)
        for rel in ("bible.html", "tv/control_app.py", "tv/tv_diablo.py", "tv/WINDOWS_SHIP.json"):
            shutil.copy2(os.path.join(B.REPO, rel), os.path.join(d, rel))
        return d

    def test_the_preflight_refuses_the_v3100_defect(self):
        """⚠⚠ THE FIRST CUT OF THIS LAW HAD TWO **BLIND** RED-PROOFS, AND THE REASON IS worth more
        than the fix: every assertion only checked that the guard PASSES on a good tree, so
        disabling the guard changed nothing observable. A check you never see REFUSE is a check you
        have not tested. [[feedback-blind-fixture-green-gate]] [[regression-guard]]
        """
        d = self._temp_repo()
        bib = os.path.join(d, "bible.html")
        s = io.open(bib, encoding="utf-8").read()
        broken = s.replace("    paintGrok();\n    return j;",
                           "    paintGrok();\n    } catch(e){}\n    return j;", 1)
        self.assertNotEqual(broken, s, "the fixture did not actually break anything — the anchor "
                                       "it splices on has moved, so this test proves nothing")
        io.open(bib, "w", encoding="utf-8").write(broken)
        with self.assertRaises(SystemExit) as cm:
            B._preflight(d)
        msg = str(cm.exception)
        print("   broken tree refused: %s" % msg.splitlines()[0][:90])
        self.assertIn("does not parse", msg)
        self.assertIn("bible.html", msg)

    def test_the_bump_refuses_a_note_that_breaks_the_page(self):
        """A trailing backslash escapes the closing quote of the JS string `note` lands in. It
        contains no apostrophe and no CSS token, so BOTH existing guards wave it through — which is
        why a parser had to sit behind them rather than a third spelling."""
        d = self._temp_repo()
        before = io.open(os.path.join(d, "bible.html"), encoding="utf-8").read()
        with self.assertRaises(SystemExit) as cm:
            B.bump("v99999", "fixture", "closed the </script> tag", repo=d)
        msg = str(cm.exception)
        print("   bad note refused: %s" % msg.splitlines()[0][:90])
        self.assertIn("does not parse", msg)
        self.assertEqual(io.open(os.path.join(d, "bible.html"), encoding="utf-8").read(), before,
                         "the bump REFUSED and still wrote — 'nothing written' must mean nothing")

    def test_the_bump_refuses_a_name_that_repeats_the_version(self):
        """REG-1689 — v3545 and v3546 were bumped with the version as their name, so the badge read
        "v3546 · 2026-10-01 · v3546" and CI's badge spec (v1748) went red after the publish. The
        name is the badge's words; it must say what the version does. Baseline first: a real name
        passes THIS guard (it may still stop later, at the parse), so a refusal below is the name's."""
        d = self._temp_repo()
        before = io.open(os.path.join(d, "bible.html"), encoding="utf-8").read()
        for bad in ("v99999", "V99999 ", "v99999 - again", ""):
            with self.assertRaises(SystemExit) as cm:
                B.bump("v99999", bad, "a plain note", repo=d)
            self.assertIn("never repeat the version", str(cm.exception), "name %r: %s" % (bad, cm.exception))
        self.assertEqual(io.open(os.path.join(d, "bible.html"), encoding="utf-8").read(), before,
                         "the bump REFUSED a name and still wrote")
        try:
            B.bump("v99999", "the river reopens", "closed the </script> tag", repo=d)
        except SystemExit as e:
            self.assertNotIn("never repeat the version", str(e), "a real name was refused as a repeat")


    def test_the_bump_refuses_a_note_that_opens_with_the_version(self):
        """REG-1741 - the tool prefixes the version itself, so a note opening "v99999 — ..." printed it twice."""
        d = self._temp_repo()
        before = io.open(os.path.join(d, "bible.html"), encoding="utf-8").read()
        for bad in ("v99999 — the river reopens", "V99999: again", "  v99999 - x"):
            with self.assertRaises(SystemExit) as cm:
                B.bump("v99999", "the river reopens", bad, repo=d)
            self.assertIn("must not open with", str(cm.exception), "note %r: %s" % (bad, cm.exception))
        self.assertEqual(io.open(os.path.join(d, "bible.html"), encoding="utf-8").read(), before,
                         "the bump REFUSED a note and still wrote")
        try:
            B.bump("v99999", "the river reopens", "REG-1 - the river reopens after v99998", repo=d)
        except SystemExit as e:
            self.assertNotIn("must not open with", str(e), "a note that only MENTIONS a version was refused")


class TheHeartGateGradesTheTreeBeingBumped(unittest.TestCase):
    """#223 — `bump(repo=...)` stamps the tree it is handed, and its heart gate ran `git diff` beside
    the SCRIPT regardless: a bump aimed at a temp tree was refused for uncommitted edits in the LIVE
    repo. Two throwaway git trees, so whichever state the live tree is in, one of these goes red if
    the gate reads the wrong tree."""

    def _git_tree(self, dirty):
        import shutil, subprocess, tempfile
        d = tempfile.mkdtemp(prefix="bump-heart-")
        self.addCleanup(shutil.rmtree, d, True)
        os.makedirs(os.path.join(d, "tv"))
        io.open(os.path.join(d, "bible.html"), "w").write("<html>fixture</html>\n")
        g = ["git", "-C", d, "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(g + ["init", "-q"], check=True)
        subprocess.run(g + ["config", "core.autocrlf", "false"], check=True)  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        subprocess.run(g + ["add", "-A"], check=True)
        subprocess.run(g + ["commit", "-q", "-m", "fixture"], check=True)
        if dirty:
            io.open(os.path.join(d, "bible.html"), "a").write("<!-- a surface edit, no watcher -->\n")
        return d

    def test_a_dirty_temp_tree_is_refused(self):
        with self.assertRaises(SystemExit) as cm:
            B._heart_gate("no heart note here", repo=self._git_tree(dirty=True))
        self.assertIn("changes nothing that WATCHES it", str(cm.exception))

    def test_a_clean_temp_tree_is_not_refused_for_the_live_repos_edits(self):
        B._heart_gate("no heart note here", repo=self._git_tree(dirty=False))   # must not raise


RED_PROOF = [
    {
        "why": "#223 - the bump's heart gate grades the LIVE repo instead of the tree it stamps again",
        "file": "bump_version.py",
        "find": "        here = os.path.join(os.path.abspath(repo), \"tv\")\n",
        "replace": "        pass\n",
        "matches": 1,
    },
    {
        "why": "the EXACT v3100 defect is put back into bible.html — a bare `} catch(e){}` closing "
               "nothing — and the bump must refuse to stamp it. This is the shape that reached his "
               "live console and stayed there until a cross-family review of the shipped diff "
               "found it",
        "file": "../bible.html",
        "find": "    paintGrok();\n    return j;",
        "replace": "    paintGrok();\n    } catch(e){}\n    return j;",
        "matches": 1,
    },
    {
        "why": "the preflight stops looking at bible.html, so a broken page can be stamped and "
               "handed to a console that execs the working tree",
        "file": "bump_version.py",
        "find": '        probs, why = _js.check_with_node(["bible.html"])',
        "replace": '        probs, why = [], None',
        "matches": 1,
    },
    {
        "why": "the spliced page stops being parsed, so a note carrying `</script>` — valid JS "
               "in isolation — terminates the script block and blanks the board",
        "file": "bump_version.py",
        "find": "    _page_problem = _parses_as_page(_new_page)",
        "replace": "    _page_problem = None",
        "matches": 1,
    },
    {
        "why": "the preflight moves AFTER the pending writes are computed, which is a report about "
               "damage rather than a guard against it",
        "file": "bump_version.py",
        "find": "    _preflight(repo)\n\n    today = datetime.date.today().isoformat()",
        "replace": "    today = datetime.date.today().isoformat()",
        "matches": 1,
    },
    {
        "why": "REG-1689 - the bump stamps a name that repeats the version, and the badge prints it twice",
        "file": "bump_version.py",
        "find": "    if not _nm or _nm.startswith(str(ver).strip().lower()):\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-1741 - the bump stamps a note that opens with the version, and it prints twice",
        "file": "bump_version.py",
        "find": "    if _nt.startswith(str(ver).strip().lower()):\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
