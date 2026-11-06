#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PROVE test_extract_gap_holding.py RED. A gate never seen red is measuring nothing.

    python3 tv/sabotage_extract_gap_holding.py

Each sabotage names an anchor, and the anchor is counted TWICE before it is applied:

  · in the source with every comment and docstring BLANKED OUT — so a law can never be
    "satisfied" by prose. This session watched that defect land six times, once where an
    assertion on `.apply(` was met by a comment reading `reel_route_lane.apply()`.
  · in the raw file, so the edit that goes to disk is the one that was counted.

Both counts must be exactly 1. Anything else and the sabotage did not apply, which makes the
law UNPROVEN rather than fine — so this refuses to report a result for it.
[[source-reading-guard]] [[sabotage-is-usually-the-wrong-one]]

⚠ THE FILE IS RESTORED BY COPY FROM A PRISTINE SNAPSHOT AND VERIFIED BY SHA-256, never by
re-editing the text back. `git checkout <file>` is banned in this repo while a fleet is running.
"""
import ast
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import tokenize

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "extract_gap.py")
GATE = os.path.join(HERE, "test_extract_gap_holding.py")


def _read(p):
    with io.open(p, encoding="utf-8") as fh:
        return fh.read()


def _sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def strip_comments(src):
    """Source with every comment and every docstring blanked to spaces. -> str

    Blanked rather than deleted so line/column offsets are unchanged and a count is still
    meaningful against the real file.
    """
    lines = src.split("\n")

    def blank(l1, c1, l2, c2):
        for ln in range(l1 - 1, min(l2, len(lines))):
            s = 0 if ln > l1 - 1 else c1
            e = len(lines[ln]) if ln < l2 - 1 else c2
            lines[ln] = lines[ln][:s] + " " * max(0, e - s) + lines[ln][e:]

    try:
        tree = ast.parse(src)
    except SyntaxError:
        return src
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None) or []
        if not body or not isinstance(body[0], ast.Expr):
            continue
        v = body[0].value
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            blank(v.lineno, v.col_offset, v.end_lineno, v.end_col_offset)
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                blank(tok.start[0], tok.start[1], tok.end[0], tok.end[1])
    except Exception:
        pass
    return "\n".join(lines)


#: (name, the law it is attacking, anchor, replacement)
SABOTAGES = [
    ("the verdict stops asking the scenario",
     "a chronicle-only sealed reel is NOT_A_HOLDING",
     "elif has_seal and n and hold is True:",
     "elif has_seal and n and hold is not None:"),

    ("a chronicle name counts as a container",
     "only a name read with a container open can carry a location",
     "panel = int(c.get(\"panel\") or 0)",
     "panel = int(c.get(\"panel\") or 0) + int(c.get(\"chronicle\") or 0)"),

    ("a floor name counts as a container",
     "an item on the ground has no cell, so no location",
     "floor = int(c.get(\"floor\") or 0)",
     "floor = 0; panel = panel + int(c.get(\"floor\") or 0)"),

    ("an unreadable journal answers False instead of None",
     "nobody-looked is not measured-zero",
     "        return None, (\"the journal ring could not be read",
     "        return False, (\"the journal ring could not be read"),

    ("the name count loses its denominator",
     "a journal that would not open must not read as zero names",
     "names_known = not nwhy",
     "names_known = True"),

    ("a dead journal falls through to the capture verdict",
     "a sealed reel with unmeasurable names is UNKNOWN, not REG-340",
     "elif has_seal and not names_known:",
     "elif False:"),

    ("the headline counts every name as recoverable work",
     "the recoverable figure counts PANEL names only",
     "_rec_names = sum(int(r.get(\"panelNames\") or 0)",
     "_rec_names = sum(int(r.get(\"names\") or 0)"),

    ("the row stops carrying its holding verdict",
     "every row publishes holdingPossible and its reason",
     "\"holdingPossible\": hold, \"holdingWhy\": hwhy,",
     ""),
]


def run_gate():
    """-> (passed, tail of output)"""
    p = subprocess.Popen([sys.executable, GATE], cwd=HERE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.communicate()[0].decode("utf-8", "replace")
    tail = [l for l in out.strip().split("\n") if l.strip()][-1:]
    return p.returncode == 0, (tail[0] if tail else "(no output)")


def main():
    pristine = os.path.join(tempfile.mkdtemp(prefix="sabotage_eg_"), "extract_gap.py.pristine")
    shutil.copy2(TARGET, pristine)
    clean_sha = _sha(TARGET)
    print("\nSABOTAGE — test_extract_gap_holding.py")
    print("  target   %s" % TARGET)
    print("  sha256   %s" % clean_sha)

    ok, tail = run_gate()
    print("\n  BASELINE (clean tree): %s   %s\n" % ("PASS" if ok else "FAIL", tail))
    if not ok:
        print("  ⛔ the gate is already red on a clean tree — nothing below would mean anything.")
        return 2

    results = []
    for name, law, anchor, repl in SABOTAGES:
        src = _read(TARGET)
        n_raw = src.count(anchor)
        n_code = strip_comments(src).count(anchor)
        print("  · %-46s anchors: code=%d raw=%d" % (name, n_code, n_raw))
        if n_code != 1 or n_raw != 1:
            print("      ⛔ UNPROVEN — the anchor is not exactly one piece of executable text, so "
                  "the sabotage never applied. The LAW is the suspect, not the file.")
            results.append((name, law, None))
            continue
        try:
            with io.open(TARGET, "w", encoding="utf-8") as fh:
                fh.write(src.replace(anchor, repl))
            passed, tail = run_gate()
        finally:
            shutil.copy2(pristine, TARGET)
            back = _sha(TARGET)
            if back != clean_sha:
                print("      ⛔ RESTORE FAILED — sha %s != %s. STOPPING." % (back[:12], clean_sha[:12]))
        # REG-3311 - the return sits OUTSIDE the finally: a return inside one swallows whatever the try raised (Python 3.14
        # warns, PEP 765), and test_the_gates_load_on_windows went red on GitHub's newer Python over it
        if back != clean_sha:
            return 3
        print("      gate went %s   %s" % ("GREEN (the law is unproven)" if passed else "RED", tail))
        print("      law: %s" % law)
        results.append((name, law, not passed))

    print("\n  ── verdict ──")
    unproven = [r for r in results if r[2] is not True]
    for name, law, red in results:
        print("  %-46s %s" % (name, "RED (proven)" if red else
                              ("GREEN — UNPROVEN" if red is False else "NOT APPLIED — UNPROVEN")))
    print("\n  %d of %d sabotages turned the gate RED." % (len(results) - len(unproven), len(results)))
    print("  final sha256 %s  %s\n" % (_sha(TARGET), "MATCHES CLEAN" if _sha(TARGET) == clean_sha
                                       else "⛔ DOES NOT MATCH"))
    return 0 if not unproven else 1


if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    sys.exit(main())
