# -*- coding: utf-8 -*-
"""v3768 — A GATE CARRIES WHEN GIT SAYS ITS INPUTS HAVE NOT MOVED SINCE THE PROOF.

A version was paying for about four full `run_gates` passes, each one re-proving gates whose inputs
had not changed. Hashing every input of every gate on the way back in cost as much as running them.
This ledger does not do that.

A PASS is stored with the commit it was proved at. The next `--changed` run asks git once:

    git diff --name-only <proven_sha>..HEAD
    git status --porcelain

and intersects that set with each gate's inputs. Each stored PASS keeps its own commit. A later
PASS at a new HEAD does not discard the others: a gate carries while its commit is an ancestor
of HEAD and none of its inputs are in `diff(that commit..HEAD)` plus the dirty worktree. One
diff per distinct commit, cached for the run.

The input map is reused while `tv/run_gates.py`, `BLUEPRINT.md` and `tv/heart2.py` are the same
bytes. A row is rebuilt when the gate script, heart2.py, or any file already in its closure is
in the change set, and a PASS is stored from a fresh parse, not from that cache. The runner
file is not an input of every gate: heart2 imports it, and that walk would otherwise rerun
everything when a Gate is registered. The hashed Gate definition covers that. A gate that
itself imports or names the runner still depends on it. `bible.html` is an input of a
gate that opens it, or that reaches a function which opens it. A string in an
imported module does not count, and importing a module that only names the file
does not either.

A gate whose inputs are not in the set is printed as `proven at <sha> (<age>)` and its files
are not opened.

REG-2293 round 5 — THE PROOF REMEMBERS WHAT THE GATE READ. A static walk cannot see every read:
a glob inside an imported module, `p = path or BIBLE; open(p)`, a handler reached by dispatch. So
run_gates runs each gate with gate_trace/sitecustomize.py armed (an audit hook on open, listdir,
scandir, glob, stat, import and every child process), and the PASS stores what that run read:

    inputs   the static walk plus every repo file the run opened or stat'ed
    listed   every repo directory it listed (not the import system's own listings)
    imports  every non-stdlib module name it imported, found or not

`lookup` compares `git diff --name-status --no-renames` plus `git status --porcelain
--untracked-files=all` with the stored set AND today's walk, so a deleted input is still an
input. An added or deleted file under a listed directory, or a new module whose name the gate
imported, is a hit. `record` refuses a PASS when a dirty or untracked path is one of those
inputs, or a tracked file under a listed directory was added or deleted in the worktree, since the
commit it would be labelled with is not the bytes it ran on. An untracked file the run could only
see in a listing is kept as a snapshot (`untracked`); one that comes or goes later is a hit.
A node child carries gate_trace/node_trace.cjs and is traced the same way. A run the hook could
not follow is never stored, so the gate always runs: no trace, a child that is not python or node
(chrome, bash, a git command that reads history or the index), a child that did not trace itself,
an ES module from this checkout, a read of a gitignored file (except the two keyed caches below),
or a listing of a directory that holds no tracked file. A row stored before this change has no
`traced` mark and runs once.

Fail closed. A missing or unreachable proven sha, a diff that fails, a gate whose inputs cannot
be named, a corrupt ledger, and a FAIL are all a run. Only a PASS is stored. `--full` consults it too (v3849 GATE-BANK;
TV_FULL_FRESH=1 does not). GitHub CI does not. The changed-law red-proof (v3292) is a different
stage and does not read this file.

The files are per checkout, gitignored, and never a verdict of record. CARRY is not a fresh pass
and it does not bank Wilson evidence.

    python3 tv/gate_ledger.py --carry NAME     exit 0 and "proven at <sha> (<age>)", or exit 1
    python3 tv/gate_ledger.py --record NAME    needs suite_verdict for these bytes AND a trace, so a bare
                                               --record says why and stores nothing; run_gates stores
"""
import ast
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

LEDGER_NAME = ".gate_ledger.json"
MAP_NAME = ".gate_inputs.json"
# written by the run that reads them — treating them as inputs would rerun every gate
_SELF = frozenset((LEDGER_NAME, LEDGER_NAME + ".tmp", MAP_NAME, MAP_NAME + ".tmp"))
_MAX = 4000
_SAFE = re.compile(r"^[A-Za-z0-9_.-]+$")
_SHA = re.compile(r"^[0-9a-f]{7,40}$")
_NODE_DYNAMIC = re.compile(r"\b(readdir|readdirSync|readDir|globSync)\b|\bglob\(")
_REL_IMPORT = re.compile(
    r"""(?:from\s+|import\s+|require\(\s*)['"](\.[^'"]+)['"]""")
_PY_PLAYWRIGHT = re.compile(r"(^|\n)\s*(import playwright\b|from playwright\b)")


# v3774 — A VERSION BUMP IS NOT A CHANGE TO EVERY GATE. bump_version.py rewrites a known set of
# lines in bible.html, tv/control_app.py, tv/tv_diablo.py and tv/WINDOWS_SHIP.json, and its own
# regenerations rewrite known lines in RESUME_HERE.md, BLUEPRINT.md and the TASKS.md ship table.
# Most gates import or open one of those files, so a bump-only diff reran 760 of 1003 gates.
#
# The stamp lines are dropped from the change set ONLY for a COHERENT bump: every required surface
# changed, every one changed only its stamp lines, each stamp was swapped in place (same hunk
# position, same indentation, same kind), and every removed version is one old version U and every
# added version is one new version V != U. A partial bump, a hand edit of one stamp, a moved or
# re-indented stamp, a TASKS.md edit other than the single new top ship row, a failed git diff, or
# any line the reader does not know keeps every stamp surface changed, so every gate reruns.
# Even then a gate that reads the version (see reads_version) reruns.
_V = r"(?P<v>v\d+(?:\.\d+)*)"
_SQ = r"'(?:[^'\\\n]|\\.)*'"          # one single-quoted JS string, nothing after its close quote
STAMP_SURFACES = {  # LEDGER-STAMP-SURFACES (mirrors tv/bump_version.py bump + _rewrite_head_stamps)
    "bible.html": (
        ("build", re.compile(r"^  window\.D2R_BUILD = \{ id:'" + _V + r"', name:(?P<f>" + _SQ +
                             r"), date:'\d{4}-\d\d-\d\d', note:(?P<g>" + _SQ + r") \};$")),
        ("title", re.compile(r"^(?P<pre>\s*<title>[^<]*?)\b" + _V + r"\b(?P<post>[^<]*</title>)$")),
        ("meta", re.compile(r'^<meta name="d2r-build" content="' + _V + r'">$')),
        ("meta-date", re.compile(r'^<meta name="d2r-build-date" content="\d{4}-\d\d-\d\d">$')),
        ("meta-note", re.compile(r'^<meta name="d2r-build-note" content="(?P<f>[^"<>\n]*)">$')),
    ),
    "tv/control_app.py": (("ver", re.compile(r'^\s*"ver": "' + _V + r'",$')),),
    "tv/tv_diablo.py": (("ver", re.compile(r'^VERSION = "' + _V + r'"   # (?P<f>[^\n]*)$')),),
    "tv/WINDOWS_SHIP.json": (
        ("ver", re.compile(r'^  "ver": "' + _V + r'",$')),
        ("note", re.compile(r'^  "note": "' + _V + r': (?P<f>(?:[^"\\\n]|\\.)*)",$')),
    ),
    "BLUEPRINT.md": (("generated", re.compile(r"^    generated \d{4}-\d\d-\d\d \d\d:\d\d$")),),
    "RESUME_HERE.md": (
        ("fp", re.compile(r"^<!-- fp: ver=" + _V + r" -->$")),
        ("stamp", re.compile(r"^\| version stamp \| " + _V + r" \|$")),
        ("derived", re.compile(r"^\*Derived \d{4}-\d\d-\d\d \d\d:\d\d by `tv/resume_state\.py`\. "
                               r"Everything outside these markers is narrative a machine cannot "
                               r"measure, written by hand\.\*$")),
    ),
    "TASKS.md": (),  # handled by _tasks_row_versions: one new top ship row, exact bump format
    "tv/CHANGELOG.json": (),  # handled by _changelog_versions: one new head entry, exact bump format (v3845)
}
# v3845 (Elad 2026-10-30 11:24) - THE BUMP-ONLY RULE HAD QUIETLY STOPPED HOLDING. Since v3843 every bump also
# writes tv/CHANGELOG.json, which was no stamp surface, so every bump read as a code change and a bump-only
# commit reran the gates its parent had just passed. The changelog now leaves the change set ONLY as one
# new entry inserted at the head of the list, in json.dumps(indent=2) shape, for the bump's own new version,
# with leak-checked items - any other edit to it (a reworded old entry, a second entry, a moved line) keeps
# it changed and every gate reruns. Law: test_a_bump_only_commit_inherits_its_parents_passes.
_CL_OPEN, _CL_CLOSE, _CL_ITEMS, _CL_ITEMS_END = "  {", "  },", '    "items": [', "    ]"
_CL_VER = re.compile(r'^    "ver": "' + _V + r'",$')
_CL_DATE = re.compile(r'^    "date": "\d{4}-\d\d-\d\d",$')
_CL_ITEM = re.compile(r'^      (?P<f>"(?:[^"\\\n]|\\.)*")(?P<c>,?)$')


def _changelog_entry(hunks):
    """-> (new version, [item texts]) | None. One hunk inserted after line 1 ('['), nothing removed."""
    if not hunks or len(hunks) != 1:
        return None
    o, n, rem, add = hunks[0]
    if rem or o != 1 or n != 2 or len(add) < 7:  # CL-HEAD-INSERT-ONLY
        return None
    if add[0] != _CL_OPEN or add[3] != _CL_ITEMS or add[-2] != _CL_ITEMS_END or add[-1] != _CL_CLOSE:
        return None
    mv, md = _CL_VER.match(add[1]), _CL_DATE.match(add[2])
    if not (mv and md):
        return None
    items = []
    body = add[4:-2]
    for i, line in enumerate(body):
        m = _CL_ITEM.match(line)
        if not m or (m.group("c") == ",") != (i < len(body) - 1):  # CL-ITEM-SHAPE
            return None
        try:
            items.append(json.loads(m.group("f")))
        except Exception:
            return None
    return mv.group("v"), items
# Every coherent bump moves these. BLUEPRINT.md may or may not move (same-minute regen).
_STAMP_REQUIRED = frozenset(("bible.html", "tv/control_app.py", "tv/tv_diablo.py",
                             "tv/WINDOWS_SHIP.json", "RESUME_HERE.md", "TASKS.md"))
_TASK_NEW = re.compile(r"^\| \*\*" + _V + r"\*\* \| `\(this commit\)` \| (?P<s>v\d+(?:\.\d+)*) — (?P<f>[^|\n]*)\|$")
_TASK_OLD = re.compile(r"^\| \*\*" + _V + r"\*\* \| `\(this commit\)` \| (?P<rest>.*)$")
_TASK_BOUND = re.compile(r"^\| \*\*" + _V + r"\*\* \| `(?P<sha>[0-9a-f]{7,40})` \| (?P<rest>.*)$")
# A gate whose own name or script speaks of the version, or names a module whose job is reading
# it, reruns even on a coherent bump. The closure is NOT searched by word: measured on v3772,
# 913 of 1003 closures hold a version word and resume_state / stamp_versions / second_eye_ledger /
# console_doctor each sit in 619-633 closures through hub imports, so a closure test reruns
# everything. Closure membership is used only for _VERSION_READER_ONLY, modules that exist to read
# the version and sit in no hub. CI never consults the ledger.
# v3775 (REG-2296): build|title|status|fresh dropped from the NAME rule. They named 22 of the 107 bump
# reruns (test_the_item_edit_tab_builds_..., test_a_fresh_install_..., test_a_title_is_not_an_owner) whose
# scripts never speak of the version; such a gate is still caught by its script's words below.
_VERSION_NAME = re.compile(r"version|stamp|bump|ship|resume", re.I)  # STAMP-NAME-NARROW
_VERSION_WORDS = re.compile(
    r"D2R_BUILD|d2r-build|bump_version|WINDOWS_SHIP|stamp_versions|\bVERSION\b|"
    r"[\x27\x22]ver[\x27\x22]|<title>|resume_state|RESUME_HERE|version_stamp_gate|"
    r"second_eye_ledger|tooltip_oracle_lane|windows_boot_check|_tree_version|"
    r"_check_version_drift|current_version|_shipped_versions|bible_stamp|TASKS\.md|CHANGELOG")
_VERSION_READER_ONLY = frozenset(("tv/version_stamp_gate.py", "tv/windows_boot_check.py"))


# v3774 round 3 — THE STAMP LINES CARRY FREE TEXT (build name, notes, the ship row). A coherent bump
# carries the content gates only when every ADDED stamp line passes stamp_leak.leak_problem (the same
# check bump_version.py refuses with), so a note pasted past the tool still reruns everything. A few
# gates that read the stamp files' text as their whole job always rerun on any stamp move.
_ALWAYS_RERUN = frozenset(("test_no_new_home_path_is_published",))


def stamp_kinds(rel, line):
    """(kind, match) of the stamp pattern a changed line matches, or None."""
    for kind, pat in STAMP_SURFACES.get(rel, ()):
        m = pat.match(line)
        if m:
            return kind, m
    return None


_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def diff_hunks(text):
    """`git diff -U0` of one path -> [(old_start, new_start, removed, added)] or None on any
    line that is not a header before the first @@, a hunk header, or a +/- line."""
    hunks, in_hunk, cur = [], False, None
    for line in (text or "").splitlines():
        if line.startswith("diff --git ") and not in_hunk:
            continue
        m = _HUNK.match(line) if line.startswith("@@ ") else None
        if m:
            in_hunk = True
            cur = (int(m.group(1)), int(m.group(3)), [], [])
            hunks.append(cur)
            continue
        if not in_hunk and line.startswith(("index ", "--- ", "+++ ")):  # STAMP-HEADER
            continue
        if in_hunk and line[:1] == "-":
            cur[2].append(line[1:])
            continue
        if in_hunk and line[:1] == "+":
            cur[3].append(line[1:])
            continue
        return None  # STAMP-UNKNOWN-LINE: rename, mode, binary, "\ No newline", a second file
    return hunks or None


def _indent(line):
    return line[:len(line) - len(line.lstrip())]


_TASK_SHIPPED = re.compile(r"^\| \*\*" + _V + r"\*\* \| `(?P<sha>[0-9a-f]{7,40})` \| (?P<s>v\d+(?:\.\d+)*) — (?P<f>[^|\n]*)\|$")
_MAX_BUMPS = 20


def _vnum(v):
    return tuple(int(x) for x in v[1:].split("."))


def _tasks_row_versions(hunks):
    """N back-to-back bumps in exact bump_version format. -> (old, new) | None

    The proof's top row `| **U** | `(this commit)` | ... |` comes back bound to a sha with its text
    byte-identical, and above it sit N new rows: the newest `(this commit)` and N-1 shipped rows, each
    `| **Vi** | `sha` | Vi — note |`, versions strictly rising toward the top."""
    if len(hunks) != 1:
        return None
    o, n, rem, add = hunks[0]
    if o != n or len(rem) != 1 or not 2 <= len(add) <= _MAX_BUMPS + 1:  # STAMP-TASKS-SHAPE
        return None
    old, new, bound = _TASK_OLD.match(rem[0]), _TASK_NEW.match(add[0]), _TASK_BOUND.match(add[-1])
    if not (old and new and bound):
        return None
    if new.group("v") != new.group("s") or bound.group("v") != old.group("v"):
        return None
    if bound.group("rest") != old.group("rest"):  # STAMP-TASKS-REST
        return None
    chain = [new.group("v")]
    for line in add[1:-1]:
        m = _TASK_SHIPPED.match(line)
        if not m or m.group("v") != m.group("s"):  # STAMP-TASKS-MIDDLE
            return None
        chain.append(m.group("v"))
    chain.append(old.group("v"))
    try:
        nums = [_vnum(v) for v in chain]
    except ValueError:
        return None
    if any(a <= b for a, b in zip(nums, nums[1:])):  # STAMP-TASKS-ORDER
        return None
    return {old.group("v")}, {new.group("v")}


def stamp_file_versions(rel, text):
    """Versions a stamp-only diff of one path swaps. -> (old set, new set) | None (not stamp-only)"""
    if rel not in STAMP_SURFACES:
        return None
    hunks = diff_hunks(text)
    if not hunks:
        return None
    if rel == "TASKS.md":
        return _tasks_row_versions(hunks)
    if rel == "tv/CHANGELOG.json":
        e = _changelog_entry(hunks)
        return (set(), {e[0]}) if e else None
    olds, news = set(), set()
    for o, n, rem, add in hunks:
        if o != n or len(rem) != len(add) or not rem:  # STAMP-IN-PLACE
            return None
        for a, b in zip(rem, add):
            ka, kb = stamp_kinds(rel, a), stamp_kinds(rel, b)
            if ka is None or kb is None:  # STAMP-OTHER-LINE
                return None
            if ka[0] != kb[0] or _indent(a) != _indent(b):  # STAMP-PAIRED
                return None
            ma, mb = ka[1], kb[1]
            if ka[0] == "title" and (ma.group("pre"), ma.group("post")) != (mb.group("pre"), mb.group("post")):
                return None
            if "v" in ma.re.groupindex:
                olds.add(ma.group("v"))
                news.add(mb.group("v"))
    return olds, news


def stamp_free_text(rel, text):
    """The NEW free text a stamp-only diff of one path adds: build name and note, meta note, ship
    note, tv_diablo comment, new ship-row subjects. The proof's own ship row is re-added byte-identical
    and is not new. -> [str] | None (not stamp-only)"""
    hunks = diff_hunks(text)
    if not hunks or stamp_file_versions(rel, text) is None:
        return None
    out = []
    if rel == "TASKS.md":
        add = hunks[0][3]
        for line in add[:-1]:
            m = _TASK_NEW.match(line) or _TASK_SHIPPED.match(line)
            if not m:
                return None
            out.append(m.group("f").strip())
        return out
    if rel == "tv/CHANGELOG.json":
        e = _changelog_entry(hunks)
        return list(e[1]) if e else None
    for _o, _n, _rem, add in hunks:
        for line in add:
            k = stamp_kinds(rel, line)
            if k is None:
                return None
            for g in ("f", "g"):
                if g in k[1].re.groupindex:
                    v = k[1].group(g)
                    if k[0] == "build":
                        v = v[1:-1]
                    out.append(v)
    return out


def tasks_bound_rows(text):
    """(version, sha, line) for every added ship row bound to a sha. -> [tuple] | None"""
    hunks = diff_hunks(text)
    if not hunks or len(hunks) != 1:
        return None
    rows = []
    for line in hunks[0][3][1:]:
        m = _TASK_BOUND.match(line)
        if not m:
            return None
        rows.append((m.group("v"), m.group("sha"), line))
    return rows


def free_text_clean(texts):
    """Every new free-text field is inert words and leaks nothing. Any doubt is dirty."""
    try:
        import stamp_leak
    except Exception:
        return False
    for t in texts:
        if stamp_leak.free_text_problem(t) or stamp_leak.leak_problem(t):  # STAMP-FREE-TEXT
            return False
    return True


_WORD = re.compile(r"[a-z0-9]{3,}")
_RE_CALLS = frozenset(("compile", "search", "findall", "match", "fullmatch", "sub", "subn", "finditer", "split"))


def script_literals(text):
    """(every string literal, the literals handed to re.*) of a gate script. -> (set, set) | None"""
    import ast
    import warnings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tree = ast.parse(text)
    except Exception:
        return None
    lits, rx = set(), set()
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in _RE_CALLS
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "re" and n.args):
            for m in ast.walk(n.args[0]):
                if isinstance(m, ast.Constant) and isinstance(m.value, str):
                    rx.add(m.value)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value.strip()) >= 3:
            lits.add(n.value)
    return lits, rx


def _count(text, needle):
    if re.fullmatch(r"[a-z0-9_]+", needle):  # a bare word counts as a whole word
        return len(re.findall(r"(?<![a-z0-9_])" + re.escape(needle) + r"(?![a-z0-9_])", text))
    return text.count(needle)


def literal_hit(lits, added, removed):
    """A literal of the gate whose count differs between the removed and the added stamp lines: a
    string-count or forbidden-string test must hold the string it checks, so its verdict can only move
    if one of its strings moves. Bare words compare as words, case-insensitive; phrases and anything
    with punctuation compare as substrings, both exact and case-insensitive; a regex's words compare
    as words. -> str|None (the literal that moved)"""
    if lits is None:
        return "<script did not parse>"
    al, rl = added.lower(), removed.lower()
    every, rx = lits
    for lit in every:
        low = lit.lower()
        if _count(al, low) != _count(rl, low):  # STAMP-LITERAL-MOVED
            return lit
        if not re.fullmatch(r"[A-Za-z0-9_]+", lit) and added.count(lit) != removed.count(lit):
            return lit
    for pat in rx:
        for w in _WORD.findall(re.sub(r"\\[A-Za-z]", " ", pat).lower()):
            if _count(al, w) != _count(rl, w):  # STAMP-REGEX-WORD-MOVED
                return pat
    return None


def coherent_bump(per_file):
    """{rel: (olds, news) | None} for every stamp surface in the change set -> bool.
    Every required surface present and stamp-only, one old version, one new version."""
    if any(v is None for v in per_file.values()):  # STAMP-ANY-DOUBT
        return False
    if not _STAMP_REQUIRED <= set(per_file):  # STAMP-REQUIRED
        return False
    olds, news = set(), set()
    for rel, (o, n) in per_file.items():
        if rel in _STAMP_REQUIRED and not n:
            return False
        olds |= o
        news |= n
    return len(olds) == 1 and len(news) == 1 and olds != news  # STAMP-ONE-VERSION


def ledger_path():
    """The repo's ONE ledger, shared by every worktree, unless TV_GATE_LEDGER names another file. -> path

    v3842 (GATE-TRIM B) - the ledger lived in each checkout's tv/, so a ship worktree's --full PASSes were
    invisible to the push from the main checkout and every fresh worktree started with an empty bank: the hook
    re-ran gates the same SHA had just passed. It now lives in the git COMMON dir (one per repo, shared by all
    worktrees). The carry rule is unchanged - a PASS carries only while its own commit is an ancestor of HEAD
    and none of its traced inputs moved, with inputs resolved against the tree the gate runs in - so sharing
    the bank widens no proof. No git, or no common dir: this checkout's tv/, as before."""
    env = os.environ.get("TV_GATE_LEDGER")
    if env:
        return env
    common = _common_ledger_dir()
    return os.path.join(common, LEDGER_NAME) if common else os.path.join(HERE, LEDGER_NAME)


def _common_ledger_dir():
    """<git common dir>/tvd-gate-ledger for this checkout, or None when git cannot say. -> path | None"""
    try:
        import git_quiet as _gq        # v3866 - on Windows a plain spawn opened a terminal over his game
        p = _gq.run(["git", "-C", HERE, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20, env=_git_free_env())
    except Exception:
        return None
    out = (p.stdout or "").strip() if p and p.returncode == 0 else ""
    if not out or not os.path.isdir(out):
        return None
    return os.path.join(out, "tvd-gate-ledger")


def ci_blocks():
    """GitHub is the full run. A ledger on the runner is not a verdict. -> bool"""
    return os.environ.get("GITHUB_ACTIONS") == "true"  # LEDGER-CI


def reuse_closed():
    """GATE_LEDGER=0 is the cold half of a measurement: nothing is carried or stored. -> bool"""
    return os.environ.get("GATE_LEDGER", "1") == "0"  # LEDGER-OFF


def load(path):
    """-> (entries, why). Missing is an empty ledger. Unreadable is why, and entries is None."""
    if not os.path.exists(path):
        return {}, None  # LEDGER-MISSING empty, so the gate runs
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        return None, "unreadable (%s)" % type(exc).__name__  # LEDGER-CORRUPT
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, dict):
        return None, "unreadable (no entries map)"
    return entries, None


def head_sha(root):
    """The commit this proof is labelled with. -> sha | None

    TV_GATE_LEDGER_SHA is the fixture seam. A label that is not a commit in this checkout
    cannot be diffed, so the next lookup runs the gate."""
    forced = os.environ.get("TV_GATE_LEDGER_SHA") or ""
    if _SHA.match(forced):
        return forced
    for cwd in (root, REPO):
        try:
            import git_quiet as _gq
            proc = _gq.run(
                ["git", "-C", cwd, "rev-parse", "HEAD"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15, env=_git_free_env())
        except Exception:
            continue
        sha = (proc.stdout or "").strip()
        if proc.returncode == 0 and _SHA.match(sha):
            return sha
    return None


def _git_free_env():
    """REG-2396 - the environment of every process this file starts: run_gates.git_free_env, the one definition (no
    GIT_* variable). `git -C <tree>` loses to a leaked GIT_DIR, and a carry decided on another checkout's history is a
    PASS carried over bytes nobody proved. -> dict"""
    import run_gates as _rg
    return _rg.git_free_env()


def _git(root, args):
    """One git invocation. -> CompletedProcess | None"""
    try:
        import git_quiet as _gq
        return _gq.run(["git", "-C", root] + list(args),
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
                              env=_git_free_env())
    except Exception:
        return None


def _file_hash(path):
    """sha256 of one file, or None when it cannot be read. -> hex | None"""
    try:
        digest = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


_BLUEPRINT_STAMP = re.compile(rb"(?m)^    generated \d{4}-\d\d-\d\d \d\d:\d\d$")


def _blueprint_hash(path):
    """v3774 — sha256 of BLUEPRINT.md with its one `generated <time>` line blanked. -> hex | None

    BLUEPRINT.md is GENERATED from the code (blueprint.py) and every bump regenerates it, which moved
    only that time line and still rebuilt the whole input map (~35s). The time is not a fact about any
    gate. Every other byte is still hashed, so a gate added or removed (which changes the gate list
    and counts in the map) still rekeys. Only the FIRST such line is blanked."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return None
    raw = _BLUEPRINT_STAMP.sub(b"    generated -", raw, count=1)  # LEDGER-MAPKEY-STAMP
    return hashlib.sha256(raw).hexdigest()


def map_key(root):
    """The input map is reused while these files are the same bytes. -> hex"""
    rels = ("tv/run_gates.py", "BLUEPRINT.md", "tv/heart2.py")  # LEDGER-MAPKEY
    parts = []
    for rel in rels:
        if rel == "BLUEPRINT.md":
            parts.append(_blueprint_hash(os.path.join(root, rel)) or "absent")
            continue
        parts.append(_file_hash(os.path.join(root, rel)) or "absent")
    return hashlib.sha256(b"\0".join(p.encode("ascii") for p in parts)).hexdigest()


# Directory listings IN THE GATE FILE ITSELF that the static walk may name. test_agent only
# lists directories the test itself creates (a tempfile, or HIST_DIR pointed at one).
# test_control stays unnameable: it globs gitignored footage (tv/frames/hist, which git status
# never shows). Any other gate file that lists a directory stays unnameable. A listing inside an
# imported module is not seen by the walk; the traced run records it (`listed`), and a run that
# listed a directory holding no tracked file is not stored.
_LISTING_OK = {
    "test_agent": (),  # LEDGER-LISTING
}
# v3775 (REG-2296) — A LISTING IS KEYED BY WHAT THE TRACED RUN LISTED. 80 gates (404 s on a bump) were
# refused because the gate file itself calls os.listdir / glob / os.walk. Every PASS is now stored only
# from a traced run, and the trace records each listing (`listed`): an added or deleted tracked file
# under one is a hit (first_hit), an untracked one that comes or goes is a hit (`untracked`), and a
# listed directory that holds no tracked file is keyed by its own name list (`snaps`). So the static
# walk no longer refuses a gate file for listing; the trace keys it.


# Gitignored caches whose body is used only under a key built from mtimes the trace already
# records (frame_authority's (path, size, mtime) stamp over its globs, chronicle_routes'
# _source_key over listdir + getmtime). test_cold_caches_invalidate proves a stale key and a
# poisoned body are both ignored, so reading one is not state a diff cannot see.
_KEYED_CACHES = frozenset(("tv/.fixture_reels_cache.json", "tv/.chronicle_routes_cache.json"))  # LEDGER-KEYED-CACHE


def _doc_nodes(tree):
    nodes = set()

    def take(body):
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(getattr(body[0], "value", None), ast.Constant)):
            nodes.add(body[0].value)

    take(getattr(tree, "body", None) or [])
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            take(node.body)
    return nodes


def _script_reads_bible(script):
    """Does this gate file itself load or grep bible.html? -> bool

    Fail closed. A file that cannot be read or parsed, and that names bible.html, counts
    as a read. A docstring does not. A string in some other module does not either.
    """
    try:
        with open(script, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        return True
    if "bible.html" not in src:
        return False
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return True
    docs = _doc_nodes(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "bible.html" in node.value:
            if node not in docs:
                return True
    return False


_OPEN_NAMES = frozenset(("open", "read_text", "read_bytes"))


def _is_main_guard(node):
    if not isinstance(node, ast.If):
        return False
    test = node.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    if len(test.comparators) != 1:
        return False
    left, right = test.left, test.comparators[0]

    def _name(n):
        return isinstance(n, ast.Name) and n.id == "__name__"

    def _main(n):
        return isinstance(n, ast.Constant) and n.value == "__main__"

    return (_name(left) and _main(right)) or (_main(left) and _name(right))


def _assign_names(target):
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Starred):
        return _assign_names(target.value)
    if isinstance(target, (ast.Tuple, ast.List)):
        out = []
        for elt in target.elts:
            out.extend(_assign_names(elt))
        return out
    return []


def _qual(prefix, name):
    return name if not prefix else prefix + "." + name


def _call_name(func):
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _import_module_literal(node):
    if not isinstance(node, ast.Call) or not node.args:
        return None
    if not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
        return None
    if _call_name(node.func) not in ("__import__", "import_module"):
        return None
    head = node.args[0].value.split(".")[0]
    return head or None


def _note_import(node, aliases, stars, modules):
    if isinstance(node, ast.Import):
        for alias in node.names:
            head = alias.name.split(".")[0]
            modules.add(head)
            aliases[alias.asname or head] = ("mod", head)
    elif isinstance(node, ast.ImportFrom):
        if node.level and not node.module:
            modules.add("*relative*")
            return
        head = (node.module or "").split(".")[0]
        if head:
            modules.add(head)
        for alias in node.names:
            if alias.name == "*":
                if head:
                    stars.append(head)
            else:
                aliases[alias.asname or alias.name] = ("from", head, alias.name)


def _collect_imports(stmts, aliases, stars, modules):
    for stmt in stmts:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(stmt, ast.Import) or isinstance(stmt, ast.ImportFrom):
            _note_import(stmt, aliases, stars, modules)
        elif isinstance(stmt, ast.Assign):
            mod = _import_module_literal(stmt.value)
            if mod:
                modules.add(mod)
                for target in stmt.targets:
                    for name in _assign_names(target):
                        aliases[name] = ("mod", mod)
        if isinstance(stmt, (ast.If, ast.For, ast.While, ast.With)):
            _collect_imports(stmt.body, aliases, stars, modules)
            _collect_imports(getattr(stmt, "orelse", []) or [], aliases, stars, modules)
        elif isinstance(stmt, ast.Try):
            _collect_imports(stmt.body, aliases, stars, modules)
            _collect_imports(stmt.orelse, aliases, stars, modules)
            _collect_imports(stmt.finalbody, aliases, stars, modules)
            for handler in stmt.handlers:
                _collect_imports(handler.body, aliases, stars, modules)


def _all_import_modules(tree):
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module.split(".")[0])
            elif node.level:
                modules.add("*relative*")
        else:
            mod = _import_module_literal(node)
            if mod:
                modules.add(mod)
    modules.discard("")
    return modules


def _stored_names(stmts):
    """Names this block assigns. A nested function's assignments belong to that function."""
    names = set()

    def add(target):
        names.update(_assign_names(target))

    def walk_node(node):
        if node is None or not isinstance(node, ast.AST):
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return
        if isinstance(node, ast.NamedExpr):
            add(node.target)
        elif isinstance(node, ast.comprehension):
            add(node.target)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        for child in ast.iter_child_nodes(node):
            walk_node(child)

    def walk(stmts):
        for stmt in stmts:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    add(target)
            elif isinstance(stmt, ast.AnnAssign):
                add(stmt.target)
            elif isinstance(stmt, ast.AugAssign):
                add(stmt.target)
            elif isinstance(stmt, ast.For):
                add(stmt.target)
            elif isinstance(stmt, ast.With):
                for item in stmt.items:
                    if item.optional_vars:
                        add(item.optional_vars)
            elif isinstance(stmt, ast.ExceptHandler) and stmt.name:
                names.add(stmt.name)
            walk_node(stmt)
            if isinstance(stmt, (ast.If, ast.For, ast.While, ast.With)):
                walk(stmt.body)
                walk(getattr(stmt, "orelse", []) or [])
            elif isinstance(stmt, ast.Try):
                walk(stmt.body)
                walk(stmt.orelse)
                walk(stmt.finalbody)
                for handler in stmt.handlers:
                    walk(handler.body)

    walk(stmts)
    return names


def _arg_names(args):
    names = set()
    for arg in list(args.args) + list(args.kwonlyargs):
        names.add(arg.arg)
    if args.vararg:
        names.add(args.vararg.arg)
    if args.kwarg:
        names.add(args.kwarg.arg)
    return names


def _scope_defs(stmts, prefix):
    """Names bound by def/class directly in this block, not inside a nested def. -> {name: qual}"""
    found = {}

    def walk(stmts):
        for stmt in stmts:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                found[stmt.name] = _qual(prefix, stmt.name)
            elif isinstance(stmt, (ast.If, ast.For, ast.While, ast.With)):
                walk(stmt.body)
                walk(getattr(stmt, "orelse", []) or [])
            elif isinstance(stmt, ast.Try):
                walk(stmt.body)
                walk(stmt.orelse)
                walk(stmt.finalbody)
                for handler in stmt.handlers:
                    walk(handler.body)

    walk(stmts)
    return found


def _collect_funcs(stmts, prefix, class_qual, out):
    for stmt in stmts:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qual = _qual(prefix, stmt.name)
            out.append((qual, stmt, class_qual))
            _collect_funcs(stmt.body, qual, class_qual, out)
        elif isinstance(stmt, ast.ClassDef):
            qual = _qual(prefix, stmt.name)
            _collect_funcs(stmt.body, qual, qual, out)
        elif isinstance(stmt, (ast.If, ast.For, ast.While, ast.With)):
            _collect_funcs(stmt.body, prefix, class_qual, out)
            _collect_funcs(getattr(stmt, "orelse", []) or [], prefix, class_qual, out)
        elif isinstance(stmt, ast.Try):
            _collect_funcs(stmt.body, prefix, class_qual, out)
            _collect_funcs(stmt.orelse, prefix, class_qual, out)
            _collect_funcs(stmt.finalbody, prefix, class_qual, out)
            for handler in stmt.handlers:
                _collect_funcs(handler.body, prefix, class_qual, out)


def _attr_base(node):
    attrs = []
    cur = node
    while isinstance(cur, ast.Attribute):
        attrs.append(cur.attr)
        cur = cur.value
        if isinstance(cur, ast.Call):
            cur = cur.func
    attrs.reverse()
    if isinstance(cur, ast.Name):
        return cur.id, attrs
    return None, attrs


def _each_all(node, cb):
    if node is None or not isinstance(node, ast.AST):
        return
    cb(node)
    for child in ast.iter_child_nodes(node):
        _each_all(child, cb)


def _each_args(args, cb):
    for node in list(args.defaults) + list(args.kw_defaults):
        _each_all(node, cb)
    for arg in list(args.args) + list(args.kwonlyargs):
        _each_all(arg.annotation, cb)
    if args.vararg:
        _each_all(args.vararg.annotation, cb)
    if args.kwarg:
        _each_all(args.kwarg.annotation, cb)


def _each(node, cb):
    """Visit nodes that execute here. A nested function's body is a different function."""
    if node is None or not isinstance(node, ast.AST):
        return
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for deco in node.decorator_list:
            _each_all(deco, cb)
        _each_args(node.args, cb)
        _each_all(node.returns, cb)
        return
    if isinstance(node, ast.ClassDef):
        for deco in node.decorator_list:
            _each_all(deco, cb)
        for base in node.bases:
            _each_all(base, cb)
        for kw in node.keywords:
            _each_all(kw.value, cb)
        for stmt in node.body:
            _each(stmt, cb)
        return
    cb(node)
    for child in ast.iter_child_nodes(node):
        _each(child, cb)


def _bible_binding_names(tree, docs):
    names = set()
    for stmt in tree.body:
        value = None
        targets = []
        if isinstance(stmt, ast.Assign):
            value = stmt.value
            targets = list(stmt.targets)
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            value = stmt.value
            targets = [stmt.target]
        if value is None:
            continue
        hit = False
        for node in ast.walk(value):
            if node in docs:
                continue
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and "bible.html" in node.value:
                hit = True
                break
        if hit:
            for target in targets:
                names.update(_assign_names(target))
    return names


def _self_attr_target(target):
    """self.name or cls.name, one level deep. -> the attribute, or None."""
    if (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
            and target.value.id in ("self", "cls")):
        return target.attr
    return None


def _assign_pairs(targets, value):
    """(target, value) pairs, unpacking `a, b = x, y` element by element. -> list"""
    pairs = []
    for target in targets:
        if (isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List))
                and len(target.elts) == len(value.elts)
                and not any(isinstance(e, ast.Starred) for e in target.elts + value.elts)):
            for t, v in zip(target.elts, value.elts):
                pairs.extend(_assign_pairs([t], v))
        else:
            pairs.append((target, value))
    return pairs


# A module object handed to these is inspected or patched, never called through.
_MODULE_SAFE_CALLS = frozenset((
    "hasattr", "setattr", "delattr", "isinstance", "id", "type", "repr", "dir", "vars",
    "getsource", "getsourcefile", "getfile", "getsourcelines", "getmodule",
))


def _module_safe_names(stmts):
    """Name nodes where a module alias is used but cannot escape into a call. -> set of id()

    `ca.x` is an attribute and is resolved. `self.ca = ca` is followed by _class_self_modules.
    `hasattr(ca, ...)`, `inspect.getsource(ca)`, `mock.patch.object(ca, ...)` and
    `addCleanup(setattr, ca, ...)` inspect or patch the module. Anything else (a local alias,
    an argument, a tuple, a loop) lets the module reach code this walk cannot follow.
    """
    safe = set()

    def mark(node):
        if isinstance(node, ast.Name):
            safe.add(id(node))

    for stmt in stmts:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Attribute):
                mark(node.value)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target, one in _assign_pairs(targets, node.value):
                    if _self_attr_target(target):
                        mark(one)
            elif isinstance(node, ast.Call):
                name = _call_name(node.func)
                args = list(node.args)
                if name in ("addCleanup", "enterContext", "callback") and args \
                        and _call_name(args[0]) in _MODULE_SAFE_CALLS:
                    name, args = _call_name(args[0]), args[1:]
                if name in _MODULE_SAFE_CALLS:
                    for arg in args:
                        mark(arg)
                elif (name == "object" and isinstance(node.func, ast.Attribute)
                        and _call_name(node.func.value) == "patch" and args):
                    mark(args[0])
    return safe


def _class_self_modules(class_node, mod_aliases):
    """Attributes this class stores a module on, via self.name = alias or cls.name = alias.

    The assignment and the use are different methods: setUp does `self.ca = ca` and a
    later method calls `self.ca.read()`. A name the method also assigns is not the
    import. -> {attr: set of module names}
    """
    found = {}

    def add(attr, mod):
        found.setdefault(attr, set()).add(mod)

    def scan_fn(fn):
        aliases = dict(mod_aliases)
        _collect_imports(fn.body, aliases, [], set())
        shadow = _stored_names(fn.body) | _arg_names(fn.args)

        def walk(stmts):
            for stmt in stmts:
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                value = None
                targets = ()
                if isinstance(stmt, ast.Assign):
                    value = stmt.value
                    targets = stmt.targets
                elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                    value = stmt.value
                    targets = (stmt.target,)
                for target, one in _assign_pairs(targets, value):  # LEDGER-BIBLE-TUPLE
                    mod = None
                    if isinstance(one, ast.Name) and one.id not in shadow:
                        spec = aliases.get(one.id)
                        if spec and spec[0] == "mod":
                            mod = spec[1]
                    elif one is not None:
                        mod = _import_module_literal(one)
                    attr = _self_attr_target(target) if mod else None
                    if attr:
                        add(attr, mod)
                if isinstance(stmt, (ast.If, ast.For, ast.While, ast.With)):
                    walk(stmt.body)
                    walk(getattr(stmt, "orelse", []) or [])
                elif isinstance(stmt, ast.Try):
                    walk(stmt.body)
                    walk(stmt.orelse)
                    walk(stmt.finalbody)
                    for handler in stmt.handlers:
                        walk(handler.body)

        walk(fn.body)

    def walk_body(stmts):
        for stmt in stmts:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                scan_fn(stmt)
                walk_body(stmt.body)
            elif isinstance(stmt, ast.ClassDef):
                continue
            elif isinstance(stmt, (ast.If, ast.For, ast.While, ast.With)):
                walk_body(stmt.body)
                walk_body(getattr(stmt, "orelse", []) or [])
            elif isinstance(stmt, ast.Try):
                walk_body(stmt.body)
                walk_body(stmt.orelse)
                walk_body(stmt.finalbody)
                for handler in stmt.handlers:
                    walk_body(handler.body)

    walk_body(class_node.body)
    return found


def _classes_self_modules(stmts, prefix, mod_aliases, out):
    for stmt in stmts:
        if isinstance(stmt, ast.ClassDef):
            qual = _qual(prefix, stmt.name)
            out[qual] = _class_self_modules(stmt, mod_aliases)
            _classes_self_modules(stmt.body, qual, mod_aliases, out)
        elif isinstance(stmt, (ast.If, ast.For, ast.While, ast.With)):
            _classes_self_modules(stmt.body, prefix, mod_aliases, out)
            _classes_self_modules(getattr(stmt, "orelse", []) or [], prefix, mod_aliases, out)
        elif isinstance(stmt, ast.Try):
            _classes_self_modules(stmt.body, prefix, mod_aliases, out)
            _classes_self_modules(stmt.orelse, prefix, mod_aliases, out)
            _classes_self_modules(stmt.finalbody, prefix, mod_aliases, out)
            for handler in stmt.handlers:
                _classes_self_modules(handler.body, prefix, mod_aliases, out)


class _Resolve(object):
    def __init__(self, imports, scope_names, shadow, stars, class_qual, self_mods=None):
        self.imports = imports
        self.scope_names = scope_names
        self.shadow = shadow
        self.stars = stars
        self.class_qual = class_qual
        self.self_mods = self_mods or {}

    def _spec(self, name):
        if name in self.shadow:
            return None
        if name in self.scope_names:
            return ("local", self.scope_names[name])
        return self.imports.get(name)

    def module_of(self, name):
        spec = self._spec(name)
        if spec and spec[0] == "mod":
            return spec[1]
        return None

    def name_ref(self, name):
        spec = self._spec(name)
        if spec is None:
            if self.stars and name not in self.shadow:
                return [("func", mod, name) for mod in self.stars]
            return []
        if spec[0] == "local":
            return [("local", spec[1])]
        if spec[0] == "from":
            return [("func", spec[1], spec[2])]
        return []

    def attr_ref(self, node):
        base, attrs = _attr_base(node)
        if not base or not attrs:
            return []
        if base in ("self", "cls") and self.class_qual:
            mods = self.self_mods.get(attrs[0])  # LEDGER-BIBLE-SELF
            if mods and len(attrs) > 1:
                return [("func", mod, ".".join(attrs[1:])) for mod in mods]
            return [("local", self.class_qual + "." + ".".join(attrs))]
        spec = self._spec(base)
        if spec is None:
            return []
        if spec[0] == "mod":
            return [("func", spec[1], ".".join(attrs))]
        if spec[0] == "from":
            return [("func", spec[1], spec[2] + "." + ".".join(attrs))]
        if spec[0] == "local":
            return [("local", spec[1] + "." + ".".join(attrs))]
        return []


def _is_open_call(node, resolve):
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    name = _call_name(func)
    if name in _OPEN_NAMES:
        return True
    if isinstance(func, ast.Name):
        spec = resolve.imports.get(func.id)
        if spec and spec[0] == "from" and spec[2] in _OPEN_NAMES:
            return True
    return False


def _touch(node, words, resolve):
    """A path expression names bible.html. -> (immediate, [(mod, attr)])"""
    immediate = False
    deferred = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and "bible.html" in sub.value:
            immediate = True
        elif isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load) and sub.id in words:
            immediate = True
        elif isinstance(sub, ast.Attribute) and isinstance(getattr(sub, "ctx", None), ast.Load):
            base, attrs = _attr_base(sub)
            if base and len(attrs) == 1:
                mod = resolve.module_of(base)
                if mod:
                    deferred.append((mod, attrs[0]))
    return immediate, deferred


def _open_parts(node):
    parts = list(node.args) + [kw.value for kw in node.keywords]
    func = node.func
    if isinstance(func, ast.Attribute):
        parts.append(func.value)
    return parts


def _alias_words(stmts, resolve, bible_names):
    """Names in this block that hold the bible path, including through other names."""
    pairs = []

    def walk(stmts):
        for stmt in stmts:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    for name in _assign_names(target):
                        pairs.append((name, stmt.value))
            elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                for name in _assign_names(stmt.target):
                    pairs.append((name, stmt.value))
            elif isinstance(stmt, ast.NamedExpr):
                pairs.append((stmt.target.id, stmt.value))
            if isinstance(stmt, ast.ClassDef):
                walk(stmt.body)
            elif isinstance(stmt, (ast.If, ast.For, ast.While, ast.With)):
                walk(stmt.body)
                walk(getattr(stmt, "orelse", []) or [])
            elif isinstance(stmt, ast.Try):
                walk(stmt.body)
                walk(stmt.orelse)
                walk(stmt.finalbody)
                for handler in stmt.handlers:
                    walk(handler.body)
    walk(stmts)
    words = set(bible_names) - resolve.shadow
    local = set()
    changed = True
    while changed:
        changed = False
        known = words | local
        for name, value in pairs:
            if name in local or name in resolve.shadow:
                continue
            immediate, _deferred = _touch(value, known, resolve)
            if immediate:
                local.add(name)
                changed = True
    return words | local


def _scan_block(stmts, resolve, bible_names, refs, opens):
    """Refs and bible opens in statements that execute in this block."""
    stmts = [stmt for stmt in stmts if not (isinstance(stmt, ast.If) and _is_main_guard(stmt))]
    words = _alias_words(stmts, resolve, bible_names)
    safe = _module_safe_names(stmts)

    def cb(node):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            refs.extend(resolve.name_ref(node.id))
            mod = resolve.module_of(node.id)
            if mod and id(node) not in safe:
                refs.append(("dyn", mod))  # LEDGER-BIBLE-ESCAPE
        elif isinstance(node, ast.Attribute) and isinstance(getattr(node, "ctx", None), ast.Load):
            refs.extend(resolve.attr_ref(node))
        elif isinstance(node, ast.Call) and _call_name(node.func) == "getattr" and node.args:
            mod = None
            arg = node.args[0]
            if isinstance(arg, ast.Name):
                mod = resolve.module_of(arg.id)
            if mod:
                refs.append(("dyn", mod))
        if _is_open_call(node, resolve):
            for part in _open_parts(node):
                immediate, deferred = _touch(part, words, resolve)
                if immediate:
                    opens.append(True)
                for mod, attr in deferred:
                    opens.append((mod, attr))

    for stmt in stmts:
        if isinstance(stmt, ast.If) and _is_main_guard(stmt):
            continue
        _each(stmt, cb)
    return words


def _bible_facts_from_src(src):
    """What one module does with bible.html, before other modules are joined. -> dict

    A module-level `PATH = 'bible.html'` is a binding, not an open. `open(PATH)` and
    `open('bible.html')` are opens. Fail closed when the file will not parse, or when it
    uses a relative import whose target this walk cannot name.
    """
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return {"opaque": True}
    docs = _doc_nodes(tree)
    bible_names = _bible_binding_names(tree, docs)
    modules = _all_import_modules(tree)
    if "*relative*" in modules:
        return {"opaque": True}
    mod_aliases, mod_stars = {}, []
    _collect_imports(tree.body, mod_aliases, mod_stars, set())
    mod_resolve = _Resolve(mod_aliases, _scope_defs(tree.body, ""), set(), mod_stars, None)
    mod_refs, mod_opens = [], []
    _scan_block(tree.body, mod_resolve, bible_names, mod_refs, mod_opens)
    main_refs, main_opens = [], []
    for stmt in tree.body:
        if _is_main_guard(stmt):
            _scan_block(stmt.body, mod_resolve, bible_names, main_refs, main_opens)
    for head in mod_stars:
        mod_refs.append(("import_mod", head))
    for name, spec in mod_aliases.items():
        if spec[0] == "mod":
            mod_refs.append(("import_mod", spec[1]))
        elif spec[0] == "from" and spec[1]:
            mod_refs.append(("import_mod", spec[1]))
    class_mods = {}
    _classes_self_modules(tree.body, "", mod_aliases, class_mods)
    # a subclass in this file reads what its base stored on self, so join them file-wide
    file_mods = {}
    for found in class_mods.values():
        for attr, mods in found.items():
            file_mods.setdefault(attr, set()).update(mods)
    class_mods = dict((qual, file_mods) for qual in class_mods)  # LEDGER-BIBLE-FILEWIDE
    funcs = []
    _collect_funcs(tree.body, "", None, funcs)
    direct = set()
    refs = {}
    qual_names = set()
    for qual, node, class_qual in funcs:
        qual_names.add(qual)
        aliases, stars = dict(mod_aliases), list(mod_stars)
        _collect_imports(node.body, aliases, stars, set())
        scope = _scope_defs(node.body, qual)
        if class_qual:
            # the class name is in scope for its methods; self is handled separately
            pass
        shadow = _stored_names(node.body) | _arg_names(node.args)
        resolve = _Resolve(
            aliases, scope or _scope_defs([], ""), shadow, stars, class_qual,
            class_mods.get(class_qual) if class_qual else None)
        # module-level functions and classes are visible unless this function shadows them
        resolve.scope_names = dict(_scope_defs(tree.body, ""))
        resolve.scope_names.update(scope)
        resolve.imports = dict(mod_aliases)
        resolve.imports.update(aliases)
        frefs, fopens = [], []
        _scan_block(node.body, resolve, bible_names, frefs, fopens)
        for head in stars:
            frefs.append(("import_mod", head))
        for spec in aliases.values():
            if spec[0] == "mod":
                frefs.append(("import_mod", spec[1]))
            elif spec[0] == "from" and spec[1]:
                frefs.append(("import_mod", spec[1]))
        if any(op is True for op in fopens):
            direct.add(qual)
        for op in fopens:
            if op is not True:
                frefs.append(("bible", op[0], op[1]))
        refs.setdefault(qual, []).extend(frefs)
    # An open under `if __name__` runs only when this file is the program. It is not an
    # import-time read. The gate file checks main_direct itself.
    mod_direct = any(op is True for op in mod_opens)
    for op in mod_opens:
        if op is not True:
            mod_refs.append(("bible", op[0], op[1]))
    for op in main_opens:
        if op is not True:
            main_refs.append(("bible", op[0], op[1]))
    return {
        "opaque": False,
        "bible_names": bible_names,
        "direct": direct,
        "refs": refs,
        "mod_refs": mod_refs,
        "main_refs": main_refs,
        "main_direct": any(op is True for op in main_opens),
        "mod_direct": mod_direct,
        "import_names": modules,
        "funcs": qual_names,
    }


def _script_reads_runner(script):
    """Does this gate file itself import or name run_gates.py? -> bool

    heart2.py sits in every closure and imports the runner, so the walk would make a new
    Gate rerun every gate. The hashed definition covers registering one. Fail closed. A
    docstring does not count. A string in some other module does not either.
    """
    try:
        with open(script, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        return True
    if "run_gates" not in src:
        return False
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return True
    docs = _doc_nodes(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any((a.name or "").split(".")[0] == "run_gates" for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "run_gates":
            return True
        elif (isinstance(node, ast.Constant) and isinstance(node.value, str)
              and "run_gates.py" in node.value and node not in docs):
            return True
    return False


def _pack_row(decl, why):
    blank = why or not decl
    return {
        "inputs": None if blank else list(decl["inputs"]),
        "why": why,
        "kinds": [] if blank else list(decl["kinds"]),
        "def": None if blank else decl["def"],
        "watch": [] if blank else list(decl.get("watch") or []),
        "script": None if blank else decl.get("script"),
    }


def _watched(path, patterns):
    """A changed path matches one of the gate's explicit globs. -> bool"""
    for pat in patterns or ():
        if fnmatch.fnmatch(path, pat):  # LEDGER-WATCH-GLOB
            return True
    return False


def _verdict_row(name, root):
    """The green suite_verdict for this tree, or why there is none. -> (ok, why)"""
    try:
        import suite_verdict as SV
    except Exception as exc:
        return False, "suite_verdict could not be imported (%s)" % type(exc).__name__
    if name not in getattr(SV, "SUITES", ()):
        return False, "no suite verdict exists for this gate"
    key, why = SV.tree_key(root)
    if not key:
        return False, why or "these bytes have no suite verdict"
    row, rwhy = SV.reusable(name, key, path=SV.store_path(root))
    if not row:
        return False, rwhy or "no green suite verdict for these bytes"
    return True, None


def verdict_allows(name, root):
    """A green suite_verdict for this commit's tree. -> (ok, why)"""
    ok, why = _verdict_row(name, root)  # LEDGER-NO-MINT
    if not ok:
        return False, why
    return True, None


def _porcelain(text):
    """Paths from `git status --porcelain`, including both sides of a rename. -> set"""
    out = set()
    for line in (text or "").splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        parts = path.split(" -> ") if " -> " in path else [path]
        for part in parts:
            part = part.strip().strip('"').replace("\\", "/")
            if part:
                out.add(part)
    return out


def _derived(paths):
    """Drop compiled bytecode: python writes it while a gate runs, and it is not a source. -> set"""
    return set(p for p in paths if "__pycache__/" not in p and not p.endswith(".pyc"))


def _churn(text, untracked=False):
    """Tracked paths added or deleted (or, with untracked=True, the `??` paths), from
    `git status --porcelain --no-renames`. -> set"""
    out = set()
    for line in (text or "").splitlines():
        if len(line) < 4:
            continue
        code = line[:2]
        if (code == "??") if untracked else (code != "??" and ("A" in code or "D" in code)):  # LEDGER-CHURN
            out.add(line[3:].strip().strip('"').replace("\\", "/"))
    return out


def covered(listed, imports, path):
    """A path whose presence or absence this gate can see: under a directory it listed (any
    ancestor, since a new folder is a new entry of its parent), or a module it imported. -> bool"""
    if any(a in listed for a in _ancestors(path)):  # LEDGER-TRACE-LIST
        return True
    return _module_stem(path) in imports  # LEDGER-TRACE-IMPORT


TRACE_DIR = os.path.join(HERE, "gate_trace")


def trace_path():
    """A fresh trace file outside the checkout. -> path"""
    fd, path = tempfile.mkstemp(prefix="gate-trace.", suffix=".tsv")
    os.close(fd)
    return path


def trace_env(env, root, path):
    """The gate's environment with gate_trace/sitecustomize.py armed. -> dict (a copy)"""
    env = dict(env)
    env["TV_GATE_TRACE"] = path
    env["TV_GATE_TRACE_ROOT"] = os.path.abspath(root)
    old = env.get("PYTHONPATH") or ""
    env["PYTHONPATH"] = TRACE_DIR + (os.pathsep + old if old else "")  # LEDGER-TRACE-ARM
    # a module served from a cached .pyc never opens its .py, so no read of it is seen: compile
    # every import from source, into a cache folder nobody has filled
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = path + ".pycache"  # LEDGER-TRACE-NOPYC
    hook = os.path.join(TRACE_DIR, "node_trace.cjs")
    node = env.get("NODE_OPTIONS") or ""
    env["NODE_OPTIONS"] = ('--require "%s"' % hook) + (" " + node if node else "")  # LEDGER-TRACE-NODE
    return env


def read_trace(path):
    """What one traced run read. -> (facts|None, why)

    No B line means the gate never ran under the hook (a node gate, `python -I`). A U line is a
    child or a call the hook cannot follow. A python child that started without writing its own B
    line ran untraced. Each of those is a run whose reads are UNKNOWN, so it is never carried."""
    try:
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return None, "the gate's reads were not traced"
    facts = {"R": set(), "W": set(), "S": set(), "A": set(), "L": set(), "I": set(), "G": set()}
    first = {}
    boots = {}
    spawns = {}
    for line in lines:
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        kind, pid, text = parts
        if kind == "U":
            return None, "the gate %s, which the trace cannot follow" % text  # LEDGER-UNTRACED
        if kind == "B":
            boots.setdefault(text, 0)
            boots[text] += 1
            boots.setdefault("pid:" + pid, 0)
        elif kind == "P":
            spawns[pid] = spawns.get(pid, 0) + 1
        elif kind in facts:
            facts[kind].add(text)
            if kind in ("R", "S", "A", "W", "L"):
                first.setdefault(text, kind)
    if not any(k.startswith("pid:") for k in boots):
        return None, "the gate's reads were not traced"  # LEDGER-UNTRACED-BOOT
    for pid, n in spawns.items():
        if boots.get(pid, 0) < n:
            return None, "a python child of the gate ran without the trace"
    # made by this run before anything looked at it, so it is not state the run found
    facts["M"] = set(p for p, k in first.items() if k == "W" or (k == "A" and p in facts["W"]))  # LEDGER-MADE-FIRST
    return facts, None


def _console_own_records():
    """The tracked records the running console rewrites itself (self_prove's ONE rule). -> set

    A dirty one is not a development edit, so it neither blocks a record nor stops a carry.
    Unreadable is the empty set: nothing is forgiven."""
    try:
        import self_prove
        return set(self_prove.CONSOLE_OWN_RECORDS)  # LEDGER-OWN-RECORDS
    except Exception:
        return set()


def _ancestors(path):
    """'tv/a/b.py' -> ['tv/a', 'tv', '']"""
    out = []
    while True:
        path = os.path.dirname(path)
        out.append(path)
        if not path:
            return out


def _module_stem(path):
    if not path.endswith(".py"):
        return None
    stem = os.path.basename(path)[:-3]
    if stem == "__init__":
        stem = os.path.basename(os.path.dirname(path))
    return stem or None


_SNAP_MAX = 2000


def listing_snap(root, rel):
    """A directory with no tracked file, keyed by what is in it: every entry under it (walked), with
    its size and mtime. Too many entries, a link, or anything unreadable is None. -> [str] | None"""
    top = os.path.join(root, rel)
    out = []
    try:
        if os.path.islink(top) or not os.path.isdir(top):
            return None
        for here, dirs, files in os.walk(top, followlinks=False):
            dirs.sort()
            for f in sorted(dirs + files):
                full = os.path.join(here, f)
                st = os.lstat(full)
                out.append("%s\t%d\t%d" % (os.path.relpath(full, top).replace(os.sep, "/"),
                                              st.st_size, st.st_mtime_ns))
                if len(out) > _SNAP_MAX:  # LEDGER-SNAP-MAX
                    return None
    except OSError:
        return None
    return out


def first_hit(inputs, listed, imports, changed, churn):
    """The first moved path that this gate's inputs cover. -> path | None

    A changed path that is an input. An added or deleted path under a listed directory (a new
    folder is a new entry of its parent, so any ancestor counts). An added or deleted module
    whose name the gate imported, because a new tv/foo.py changes what `import foo` finds."""
    inputs = set(inputs or ())
    for path in sorted(changed or ()):
        if path in inputs:  # LEDGER-STORED-INPUTS
            return path
    listed = set(listed or ())
    imports = set(imports or ())
    for path in sorted(churn or ()):
        if covered(listed, imports, path):
            return path
    return None


def _node_version():
    try:
        proc = subprocess.run(["node", "--version"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=10, env=_git_free_env())
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    line = ((proc.stdout or proc.stderr or "").strip().splitlines() or [""])[0]
    return line[:40] or None


def _playwright_version(root):
    for rel in ("node_modules/playwright/package.json",
                "node_modules/playwright-core/package.json"):
        path = os.path.join(root, rel)
        try:
            with open(path, encoding="utf-8") as fh:
                version = str(json.load(fh).get("version") or "")
        except Exception:
            continue
        if version:
            return version[:40]
    return None


def _rel(root, path):
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    if rel.startswith("../") or os.path.isabs(rel):
        return None
    return rel


class Ledger(object):
    def __init__(self, path=None, probes=None):
        self.path = path or ledger_path()
        self.probes = probes
        self._measured = None
        self.entries = None
        self.proven = None
        self.why = None
        self._loaded = False
        self.dropped = set()
        self.reds = {}
        self.reds_dropped = set()
        self.reads = 0
        self.last_why = None
        self.map = None
        self.map_hit = False
        self._parsed = {}
        self._tracked_memo = None
        self._tracked_root = None
        self._diff_cache = {}
        self._churn_cache = {}
        self._diff_root = None
        self._stamp_cache = {}
        self._stamp_words = {}
        self._verdep = {}
        self._work = None
        self._work_root = None
        self._bible_facts = {}
        self._bible_modmap = None
        self._bible_rev = {}
        self._bible_mod_root = None
        self._bible_folded = set()
        self._bible_readers = set()
        self._bible_itime = set()
        self._bible_reader_mods = set()
        self._bible_waiters = {}
        self._bible_pending = []

    def _ensure(self):
        if self._loaded:
            return
        entries, why = load(self.path)
        self.why = why
        self.entries = entries if isinstance(entries, dict) else {}
        self.proven = None
        if not why and os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as fh:
                    data = json.load(fh)
                sha = str((data or {}).get("proven_sha") or "")
                self.proven = sha if _SHA.match(sha) else None
                reds = (data or {}).get("reds")
                self.reds = dict(reds) if isinstance(reds, dict) else {}  # LEDGER-REDS-LOAD
            except Exception:
                self.proven = None
        self._loaded = True

    def _tools(self, root):
        if self._measured is None:
            if self.probes is not None:
                self._measured = dict(self.probes)
            else:
                self._measured = {
                    "python": "%d.%d.%d" % sys.version_info[:3],
                    "node": _node_version(),
                    "playwright": _playwright_version(root),
                }
        return self._measured

    def _subject(self, gate):
        """The file this gate runs, and which tools apply. -> (path|None, kinds, why|None)"""
        argv = [str(a) for a in (getattr(gate, "argv", None) or [])]
        py = node = None
        for arg in argv:
            if arg.endswith(".py") and os.path.isfile(arg):
                py = os.path.abspath(arg)
            if arg.endswith((".js", ".mjs", ".cjs")) and os.path.isfile(arg):
                node = os.path.abspath(arg)
        script = py or node
        if script is None:
            return None, set(), "the gate names no script file, so its inputs are UNKNOWN"
        parent = os.path.dirname(script)
        if os.path.basename(parent) != "tv":
            return None, set(), "the script is not in a tv/ directory, so its closure is UNKNOWN"
        kinds = set()
        bases = [os.path.basename(a) for a in argv]
        if py or any(os.path.basename(a) in ("python", "python3") or a == sys.executable for a in argv):
            kinds.add("python")
        if node or "node" in bases or "npx" in bases:
            kinds.add("node")
        try:
            with open(script, encoding="utf-8", errors="replace") as fh:
                text = fh.read(200000)
        except OSError:
            return None, set(), "the script cannot be read"
        if _PY_PLAYWRIGHT.search(text) or any("playwright" == b for b in bases):
            kinds.add("playwright")
        if "python" not in kinds and "node" not in kinds:
            kinds.add("python")
        return script, kinds, None

    def _definition(self, gate, root):
        argv = []
        for arg in (getattr(gate, "argv", None) or []):
            text = str(arg)
            if text == sys.executable or os.path.basename(text) in ("python", "python3"):
                argv.append("python")
                continue
            if os.path.isabs(text):
                rel = _rel(root, text)
                argv.append(rel if rel else os.path.basename(text))
            else:
                argv.append(text)
        try:
            cwd = os.path.abspath(getattr(gate, "cwd", None) or root)
            cwd_rel = _rel(root, cwd) or "."
        except Exception:
            cwd_rel = "."
        venue = {
            "needs_app": bool(getattr(gate, "needs_app", False)),
            "skip_ok": list(getattr(gate, "skip_ok", ()) or ()),
            "cwd": cwd_rel,
            "ci": ci_blocks(),
        }
        blob = json.dumps({"argv": argv, "timeout": int(getattr(gate, "timeout", 0) or 0),
                           "venue": venue}, sort_keys=True, default=str)  # LEDGER-DEF
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _tool_parts(self, kinds, root):
        probes = self._tools(root)
        py = probes.get("python")
        if not py:
            return None, "python version is UNKNOWN"
        parts = []
        parts.append("python:%s" % py)  # LEDGER-PY
        if "node" in kinds or "playwright" in kinds:
            node = probes.get("node")
            if not node:
                return None, "node version is UNKNOWN"
            parts.append("node:%s" % node)  # LEDGER-NODE
        if "playwright" in kinds:
            pw = probes.get("playwright")
            if not pw:
                return None, "playwright version is UNKNOWN"
            parts.append("playwright:%s" % pw)  # LEDGER-PW
        return parts, None

    def _tracked(self, root):
        if self._tracked_root != root:
            import heart2 as H
            try:
                self._tracked_memo = H._tracked_files(root)
            except Exception:
                self._tracked_memo = None
            self._tracked_root = root
        return self._tracked_memo

    def _bible_modmap_for(self, script):
        sandbox = os.path.dirname(os.path.abspath(script))
        root = os.path.dirname(sandbox)
        if self._bible_mod_root == root and self._bible_modmap is not None:
            return self._bible_modmap
        self._bible_facts = {}
        self._bible_folded = set()
        self._bible_readers = set()
        self._bible_itime = set()
        self._bible_reader_mods = set()
        self._bible_waiters = {}
        self._bible_pending = []
        local = {}
        for directory in (root, sandbox):
            try:
                listing = os.listdir(directory)
            except OSError:
                continue
            for name in listing:
                if name.endswith(".py"):
                    local[name[:-3]] = os.path.normpath(os.path.join(directory, name))
        self._bible_modmap = local
        self._bible_rev = {path: name for name, path in local.items()}
        self._bible_mod_root = root
        return local

    def _bible_get(self, path):
        path = os.path.normpath(path)
        try:
            st = os.stat(path)
            mk = (st.st_size, st.st_mtime_ns)
        except OSError:
            return {"opaque": True}
        hit = self._bible_facts.get(path)
        if hit and hit[0] == mk:
            return hit[1]
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except OSError:
            facts = {"opaque": True}
        else:
            facts = _bible_facts_from_src(src)
        self._bible_facts[path] = (mk, facts)
        return facts

    def _bible_key(self, ref, path):
        kind = ref[0]
        if kind == "local":
            return ("local", path, ref[1])
        if kind in ("func", "star"):
            return ("func", ref[1], ref[2])
        if kind == "dyn":
            return ("dyn", ref[1])
        if kind == "bible":
            return ("bible", ref[1], ref[2])
        if kind == "import_mod":
            return ("itime", ref[1])
        return None

    def _bible_index(self, path, facts, local):
        def add(qual, ref):
            key = self._bible_key(ref, path)
            if key is None:
                return
            if key[0] != "local" and key[1] not in local:
                return
            self._bible_waiters.setdefault(key, []).append((path, qual))

        for qual, rlist in facts["refs"].items():
            for ref in rlist:
                add(qual, ref)
        for ref in facts["mod_refs"]:
            add(None, ref)

    def _bible_hit(self, ref, path, local):
        kind = ref[0]
        if kind == "local":
            return (path, ref[1]) in self._bible_readers
        if kind in ("func", "star"):
            dest = local.get(ref[1])
            return bool(dest and (dest, ref[2]) in self._bible_readers)
        if kind == "dyn":
            dest = local.get(ref[1])
            return bool(dest and dest in self._bible_reader_mods)
        if kind == "bible":
            dest = local.get(ref[1])
            if not dest:
                return False
            got = self._bible_facts.get(dest)
            return bool(got and ref[2] in got[1].get("bible_names", ()))
        if kind == "import_mod":
            dest = local.get(ref[1])
            return bool(dest and dest in self._bible_itime)
        return False

    def _bible_wake(self, path, qual):
        if qual is None:
            if path in self._bible_itime:
                return
            self._bible_itime.add(path)
        else:
            if (path, qual) in self._bible_readers:
                return
            self._bible_readers.add((path, qual))
            self._bible_reader_mods.add(path)
        self._bible_pending.append((path, qual))

    def _bible_drain(self, local):
        while self._bible_pending:
            path, qual = self._bible_pending.pop()
            if qual is None:
                mod = self._bible_rev.get(path)
                keys = (("itime", mod),) if mod else ()
            else:
                keys = [("local", path, qual)]
                mod = self._bible_rev.get(path)
                if mod:
                    keys.append(("func", mod, qual))
                    keys.append(("dyn", mod))
            for key in keys:
                for waiter in self._bible_waiters.get(key, ()):
                    self._bible_wake(waiter[0], waiter[1])

    def _bible_satisfy(self, path, facts, local):
        def consider(qual, refs):
            for ref in refs:
                if self._bible_hit(ref, path, local):
                    self._bible_wake(path, qual)
                    return

        for qual, rlist in facts["refs"].items():
            consider(qual, rlist)
        consider(None, facts["mod_refs"])

    def _bible_fold(self, path, local):
        path = os.path.normpath(path)
        if path in self._bible_folded:
            return
        facts = self._bible_get(path)
        self._bible_folded.add(path)
        if not facts or facts.get("opaque"):
            return
        self._bible_index(path, facts, local)
        self._bible_satisfy(path, facts, local)
        for qual in facts["direct"]:
            self._bible_wake(path, qual)
        if facts.get("mod_direct"):
            self._bible_wake(path, None)
        mod = self._bible_rev.get(path)
        if mod:
            for attr in facts.get("bible_names", ()):
                for waiter in self._bible_waiters.get(("bible", mod, attr), ()):
                    self._bible_wake(waiter[0], waiter[1])
        self._bible_drain(local)

    def _callee_opens_bible(self, script):
        """A reached function opens bible.html. The gate file's own strings are separate. -> bool"""
        script = os.path.normpath(script)
        local = self._bible_modmap_for(script)
        stack = [script]
        seen = []
        seen_set = set()
        while stack:
            path = stack.pop()
            if path in seen_set:
                continue
            seen_set.add(path)
            facts = self._bible_get(path)
            if facts.get("opaque"):
                return True
            seen.append(path)
            for name in facts.get("import_names", ()):
                nxt = local.get(name)
                if nxt and nxt not in seen_set:
                    stack.append(nxt)
        for path in seen:
            self._bible_fold(path, local)
        facts = self._bible_facts[script][1]
        if script in self._bible_itime or facts.get("main_direct"):
            return True
        if any((script, qual) in self._bible_readers for qual in facts.get("funcs", ())):
            return True
        for ref in facts.get("main_refs", ()):
            if self._bible_hit(ref, script, local):
                return True
        return False

    def _closure_reads_bible(self, script):
        """Keep bible.html when this gate opens it, or a function it can reach does. -> bool

        Fail closed. A callee the walk cannot see is a read.
        """
        if _script_reads_bible(script):
            return True
        try:
            return self._callee_opens_bible(script)  # LEDGER-BIBLE-CALL
        except Exception:
            return True

    def _py_inputs(self, script, gate_name=None):
        import heart2 as H
        sandbox = os.path.dirname(script)
        root = os.path.dirname(sandbox)
        try:
            skip = ("run_gates",) if not _script_reads_runner(script) else ()
            found, why = H.law_inputs(
                sandbox, os.path.basename(script), [],
                parsed=self._parsed, tracked=self._tracked(root),
                allow_listing=True,  # LEDGER-LISTING-TRACED
                skip_modules=skip)
        except Exception as exc:
            return [], "inputs could not be derived (%s)" % type(exc).__name__
        if why:
            return [], why
        paths = list(found)  # LEDGER-CLOSURE-WALK
        for extra in ("gate_ledger.py",):
            path = os.path.join(sandbox, extra)
            if os.path.isfile(path):
                paths.append(path)
        if not self._closure_reads_bible(script):  # LEDGER-BIBLE
            paths = [p for p in paths if os.path.basename(p) != "bible.html"]
        if not _script_reads_runner(script):  # LEDGER-NO-RUNNER
            paths = [p for p in paths if os.path.basename(p) != "run_gates.py"]
        return paths, None

    def _node_inputs(self, script):
        try:
            with open(script, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            return [], "the script cannot be read"
        if _NODE_DYNAMIC.search(text):
            return [], "the script lists a directory, so no byte key can name its inputs"
        paths = [script]
        base = os.path.dirname(script)
        for match in _REL_IMPORT.finditer(text):
            spec = match.group(1)
            cand = os.path.normpath(os.path.join(base, spec))
            found = None
            for extra in ("", ".js", ".mjs", ".cjs"):
                path = cand + extra
                if os.path.isfile(path):
                    found = path
                    break
            if found is None:
                return [], "a relative import could not be resolved (%s)" % spec
            paths.append(found)
        return paths, None

    def _inputs(self, script, kinds, gate_name=None):
        if script.endswith(".py"):
            return self._py_inputs(script, gate_name)
        if "node" in kinds or script.endswith((".js", ".mjs", ".cjs")):
            return self._node_inputs(script)
        return [], "the script is not a python or node file"

    def _root_of(self, gates):
        for gate in gates or []:
            for arg in (getattr(gate, "argv", None) or []):
                text = str(arg)
                if not text.endswith((".py", ".js", ".mjs", ".cjs")) or not os.path.isabs(text):
                    continue
                parent = os.path.dirname(text)
                if os.path.basename(parent) == "tv":
                    return os.path.dirname(parent)
        return REPO

    def declare(self, gate):
        """Name the inputs. This is the only path that opens them. -> (decl|None, why)"""
        self.reads += 1
        script, kinds, why = self._subject(gate)
        if why:
            return None, why
        root = os.path.dirname(os.path.dirname(script))
        parts, pwhy = self._tool_parts(kinds, root)
        if pwhy:
            return None, pwhy
        found, iwhy = self._inputs(script, kinds, getattr(gate, "name", None))
        if iwhy:  # LEDGER-UNKEYABLE
            return None, iwhy
        rels = []
        for path in found:
            rel = _rel(root, path)
            if not rel or os.path.basename(rel) in _SELF:
                continue
            rels.append(rel)
        rels = list(rels)  # LEDGER-CLOSURE-ONLY
        return {
            "root": root,
            "def": self._definition(gate, root),
            "tools": list(parts),
            "inputs": sorted(set(rels)),
            "kinds": sorted(kinds),
            "watch": list(_LISTING_OK.get(getattr(gate, "name", None), ())),
            "script": _rel(root, script),
        }, None

    def key_for(self, gate):
        """-> (key|None, decl, why). The key names the declaration, not the bytes on disk."""
        decl, why = self.declare(gate)
        if why or not decl:
            return None, {}, why or "unkeyable"
        blob = json.dumps({
            "name": str(getattr(gate, "name", "")),
            "def": decl["def"],
            "tools": list(decl["tools"]),
            "inputs": list(decl["inputs"]),
        }, sort_keys=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest(), decl, None

    def _map_file(self):
        return os.path.join(os.path.dirname(self.path) or ".", MAP_NAME)

    def _load_map(self, root):
        key = map_key(root)
        if self.map is not None and self.map.get("key") == key:
            return
        data = None
        path = self._map_file()
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception:
                data = None
        if isinstance(data, dict) and data.get("key") == key and isinstance(data.get("gates"), dict):
            self.map = data
            self.map_hit = True
            return
        self.map = {"v": 1, "key": key, "gates": {}}
        self.map_hit = False

    def _write_map(self):
        path = self._map_file()
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.map, fh, sort_keys=True)
        os.replace(tmp, path)

    def prepare(self, gates):
        """Build the input map once, or load the one already cached for this runner and blueprint."""
        root = self._root_of(gates)
        self._worktree(root)  # the tree as this run found it, for record()
        self._load_map(root)
        names = [getattr(g, "name", None) for g in gates]
        if self.map_hit and all(name in self.map.get("gates", {}) for name in names):
            return
        # v3847 (REG-1877 in a prove sandbox) - DECLARE ONLY WHAT IS MISSING. A row of a map under this key is valid
        # for this key; rebuilding all ~1300 rows because one asked-for gate was absent made a cold `--only` child run
        # (test_control's lock laws, in a fresh heart2 sandbox) parse every law in the registry - >200 s, past its
        # 180 s timeout, so the clean wave read the law ALREADY RED and refused a good push.
        rows = dict(self.map.get("gates") or {}) if self.map.get("key") == map_key(root) else {}
        for gate in gates:
            if gate.name in rows:
                continue
            try:
                decl, why = self.declare(gate)
            except Exception as exc:
                decl, why = None, "inputs could not be derived (%s)" % type(exc).__name__
            rows[gate.name] = _pack_row(decl, why)
        self.map = {"v": 1, "key": map_key(root), "gates": rows}
        self.map_hit = False
        self._write_map()

    def _map_row(self, gate, root):
        self._load_map(root)
        row = (self.map.get("gates") or {}).get(gate.name)
        if isinstance(row, dict):
            return row
        try:
            decl, why = self.declare(gate)
        except Exception as exc:
            decl, why = None, "inputs could not be derived (%s)" % type(exc).__name__
        row = _pack_row(decl, why)
        self.map.setdefault("gates", {})[gate.name] = row
        try:
            self._write_map()
        except Exception:
            pass
        return row

    def _status(self, root):
        """One `git status`. -> (changed|None, churn, why)"""
        stat = _git(root, ["status", "--porcelain", "--untracked-files=all", "--no-renames"])  # LEDGER-UNTRACKED-ALL
        if stat is None or stat.returncode != 0:
            return None, set(), "the worktree cannot be read"
        status_out = stat.stdout or ""
        drop = _SELF | set("tv/" + name for name in _SELF) | _console_own_records()
        changed = set()
        changed |= _porcelain(status_out)  # LEDGER-STATUS
        changed = _derived({p.replace("\\", "/") for p in changed}) - drop
        self._status_untracked = _derived(_churn(status_out, untracked=True)) - drop
        return changed, _derived(_churn(status_out)) - drop, None

    def _worktree(self, root):
        """Dirty paths, once per run. -> (set|None, why)"""
        if self._work is not None and self._work_root == root:
            return self._work
        self._work_root = root
        changed, churn, why = self._status(root)
        self._work_churn = churn
        self._work_untracked = set(getattr(self, "_status_untracked", ()) or ())
        self._work = (changed, why)
        return self._work

    def changes_since(self, root, sha):
        """diff(sha..HEAD) plus the dirty worktree. One git diff per distinct sha. -> (set|None, why)"""
        if self._diff_root != root:
            self._diff_cache = {}
            self._churn_cache = {}
            self._diff_root = root
        key = str(sha or "")
        if key in self._diff_cache:
            return self._diff_cache[key]
        dirty, dwhy = self._worktree(root)
        if dwhy or dirty is None:
            result = (None, dwhy or "the worktree cannot be read")
            self._diff_cache[key] = result
            return result
        out = ""
        cat_rc = diff_rc = stat_rc = 1
        stat_rc = 0
        if key and _SHA.match(key):
            cat = _git(root, ["cat-file", "-e", "%s^{commit}" % key])
            if cat is not None:
                cat_rc = cat.returncode
            head = head_sha(root) or ""
            if cat_rc == 0 and key == head:
                diff_rc = 0
            elif cat_rc == 0:
                diff = _git(root, ["diff", "--name-status", "--no-renames", "%s..HEAD" % key])
                if diff is not None:
                    diff_rc = diff.returncode
                    out = diff.stdout or ""
        if cat_rc != 0 or diff_rc != 0 or stat_rc != 0:  # LEDGER-SHA
            result = (None, "the proven sha cannot be diffed")
            self._diff_cache[key] = result
            return result
        rows = [line.split("\t", 1) for line in out.splitlines() if "\t" in line]
        changed = set(p.strip() for _c, p in rows if p.strip())  # LEDGER-DIFF
        churn = set(p.strip() for c, p in rows if p.strip() and c[:1] in ("A", "D"))  # LEDGER-DIFF-CHURN
        churn |= set(getattr(self, "_work_churn", ()) or ())
        churn = {p.replace("\\", "/") for p in churn} - _SELF - set("tv/" + name for name in _SELF)
        self._churn_cache[key] = churn
        changed |= set(dirty)
        changed = {p.replace("\\", "/") for p in changed}
        changed -= _SELF
        changed -= set("tv/" + name for name in _SELF)
        result = (changed, None)
        self._diff_cache[key] = result
        return result

    def _is_ancestor(self, root, sha):
        if not sha or not _SHA.match(str(sha)):
            return False
        head = head_sha(root)
        if not head:
            return False
        if sha == head:
            return True
        proc = _git(root, ["merge-base", "--is-ancestor", sha, head])
        return proc is not None and proc.returncode == 0

    def _store_decl(self, gate, root):
        """Parse the closure now and keep that row. -> row"""
        self._load_map(root)
        try:
            decl, why = self.declare(gate)
        except Exception as exc:
            decl, why = None, "inputs could not be derived (%s)" % type(exc).__name__
        row = _pack_row(decl, why)
        self.map.setdefault("gates", {})[gate.name] = row
        try:
            self._write_map()
        except Exception:
            pass
        return row

    def _row_for(self, gate, root, changed):
        """The cached row, rebuilt when its closure or the gate script moved. -> row"""
        row = self._map_row(gate, root)
        if not isinstance(row, dict):
            return row
        moved = "script" not in row
        script_rel = row.get("script")
        inputs = row.get("inputs")
        if changed:
            if script_rel and script_rel in changed:  # LEDGER-REBUILD-SCRIPT
                moved = True
            if isinstance(inputs, list) and any(p in changed for p in inputs):  # LEDGER-REBUILD-CLOSURE
                moved = True
            if "tv/heart2.py" in changed:
                moved = True
        if not moved:
            return row
        return self._store_decl(gate, root)

    def carry_line(self, entry):
        """'proven at <sha> (<age>)', or None when the row cannot be dated."""
        sha = str((entry or {}).get("sha") or "")
        if not _SHA.match(sha):
            return None
        try:
            import heart2 as H
            age = H._age_say(float(entry.get("at")))
        except Exception:
            return None
        if not age or age == "an UNKNOWN time":
            return None
        return "proven at %s (%s)" % (sha, age)

    def lookup(self, gate, want=True):
        """-> (entry|None, why). A hit did not open the gate's inputs.

        want=False asks the RED map: a stored FAIL whose inputs have not moved since it failed. That is
        never a pass. run_gates runs it last under a short cap and its verdict is whatever that run says."""
        if reuse_closed():
            return None, "GATE_LEDGER=0 — every gate runs"
        if ci_blocks():
            return None, "CI runs the full set — the ledger is not a verdict here"
        self._ensure()
        if self.why:
            return None, self.why
        name = getattr(gate, "name", None)
        book = self.entries if want is True else self.reds
        entry = book.get(name) if isinstance(book, dict) else None
        if not isinstance(entry, dict) or entry.get("ok") is not (want is True):  # LEDGER-ONLY-PASS
            return None, "no stored PASS for this gate" if want is True else "no stored red for this gate"
        if entry.get("gate") != name:
            return None, "the stored row does not match this gate"
        root = self._root_of([gate])
        if entry.get("def") != self._definition(gate, root):
            return None, "the definition changed"
        stored = [str(t) for t in (entry.get("tools") or [])]
        live, tw = self._tools_for(stored, root)
        if tw:
            return None, tw
        if live != stored:
            return None, "a tool version changed"
        sha = str(entry.get("sha") or "")
        changed, cwhy = self.changes_since(root, sha)
        if cwhy or changed is None:
            return None, cwhy or "the proven sha cannot be diffed"
        if not self._is_ancestor(root, sha):  # LEDGER-ENTRY
            return None, "the stored sha is not an ancestor of HEAD"
        stamped = self.stamp_only(root, sha, changed)  # LEDGER-STAMP-ONLY
        try:
            row = self._row_for(gate, root, changed - stamped)
        except Exception as exc:
            return None, "taking its inputs raised %s" % type(exc).__name__
        if not isinstance(row, dict) or row.get("why") or not isinstance(row.get("inputs"), list):
            return None, (row or {}).get("why") or "inputs are UNKNOWN"
        if (stamped and not self.reads_version(row, root, name) and not self.scans_content(row, root, name)
                and not self.hits_free_text(row, root, sha)):
            changed = changed - stamped  # STAMP-DROP
        for path in changed:
            if _watched(path, row.get("watch")):
                return None, "inputs changed: %s" % path
        if entry.get("traced") is not True or not isinstance(entry.get("inputs"), list):  # LEDGER-OLD-ROW
            return None, "the stored PASS does not say what the gate read, so it runs once"
        inputs = set(row["inputs"]) | set(str(p) for p in entry["inputs"])  # LEDGER-PROOF-INPUTS
        listed, imports = set(entry.get("listed") or ()), set(entry.get("imports") or ())
        # an untracked file the proof already saw is not a change; one that came or went is
        seen = set(p for p in getattr(self, "_work_untracked", ()) or () if covered(listed, imports, p))
        moved = seen ^ set(entry.get("untracked") or ())  # LEDGER-UNTRACKED-SNAPSHOT
        hit = first_hit(inputs, listed, imports, changed, self._churn_cache.get(sha, set()) | moved)
        if hit:
            return None, "inputs changed: %s" % hit
        snaps = entry.get("snaps") or {}
        if not isinstance(snaps, dict):
            return None, "the stored listing snapshot is unreadable"
        for path in sorted(snaps):
            if listing_snap(root, path) != snaps[path]:  # LEDGER-SNAP-MOVED
                return None, "inputs changed: the listing of %s" % path
        line = self.carry_line(entry)
        if not line:
            return None, "the stored PASS has no sha or no age"
        if want is not True:
            line = "red" + line[len("proven"):]  # LEDGER-RED-LINE: "red at <sha> (<age>)", never "proven"
        shown = dict(entry)
        shown["line"] = line
        return shown, None  # LEDGER-NO-BANK

    def stamp_only(self, root, sha, changed):
        """The stamp surfaces in `changed`, when they together form one coherent bump from sha to
        the worktree with inert, leak-free new text and real shipped rows; otherwise the empty set.
        One git diff per (sha, path), cached. -> set"""
        key = str(sha)
        if key in self._stamp_cache:
            return set(self._stamp_cache[key]) & set(changed or ())
        per, texts, rows_ok, moved = {}, [], True, ([], [])
        for rel in sorted(STAMP_SURFACES):
            if rel not in (changed or ()):
                continue
            got = None
            try:
                proc = _git(root, ["diff", "-U0", "--no-color", "--no-ext-diff", "--no-textconv",
                                   "--no-renames", str(sha), "--", rel])
                if proc is not None and proc.returncode == 0:  # STAMP-GIT-OK
                    out_text = proc.stdout or ""
                    got = stamp_file_versions(rel, out_text)
                    if got is not None:
                        for _o, _n, rem_l, add_l in diff_hunks(out_text):
                            moved[0].extend(add_l)
                            moved[1].extend(rem_l)
                        ft = stamp_free_text(rel, out_text)
                        if ft is None:
                            got = None
                        else:
                            texts.extend(ft)
                    if got is not None and rel == "TASKS.md":
                        rows_ok = self._rows_are_shipped(root, tasks_bound_rows(out_text))  # STAMP-ROWS-REAL
            except Exception:
                got = None
            per[rel] = got
        ok = bool(per) and coherent_bump(per) and rows_ok and free_text_clean(texts)  # STAMP-ALL-CLEAN
        out = set(per) if ok else set()
        self._stamp_cache[key] = out
        self._stamp_words[key] = ("\n".join(moved[0]), "\n".join(moved[1])) if ok else None
        return set(out)

    def _rows_are_shipped(self, root, rows):
        """Each bound ship row names a commit in HEAD's history whose own TASKS.md holds that row as
        `(this commit)`. A made-up row is refused. -> bool"""
        if not rows:
            return False
        for ver, sha, line in rows:
            anc = _git(root, ["merge-base", "--is-ancestor", sha, "HEAD"])
            if anc is None or anc.returncode != 0:  # STAMP-ROW-ANCESTOR
                return False
            show = _git(root, ["show", "%s:TASKS.md" % sha])
            if show is None or show.returncode != 0:
                return False
            m = _TASK_BOUND.match(line)
            own = "| **%s** | `(this commit)` | %s" % (ver, m.group("rest"))
            if own not in (show.stdout or "").splitlines():  # STAMP-ROW-OWN
                return False
        return True

    def hits_free_text(self, row, root, sha):
        """Does a string the gate's own script checks move between the old and new stamp lines? -> bool"""
        moved = self._stamp_words.get(str(sha))
        if not moved:
            return False
        rel = row.get("script")
        if not rel:
            return True
        k = ("literals", rel)
        if k not in self._verdep:
            try:
                with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                    self._verdep[k] = script_literals(fh.read())
            except OSError:
                self._verdep[k] = None
        return literal_hit(self._verdep[k], moved[0], moved[1]) is not None  # STAMP-WORD-HIT

    def scans_content(self, row, root, name=""):
        """A gate whose whole job is the stamp files' text reruns on any stamp move."""
        return str(name or "") in _ALWAYS_RERUN  # STAMP-ALWAYS-RERUN

    def reads_version(self, row, root, name=""):
        """Does the gate's name or own script speak of the version, or does its closure hold a
        module that exists only to read it? Unreadable counts as yes. -> bool"""
        if _VERSION_NAME.search(str(name or "")):  # STAMP-VERSION-NAME
            return True
        if any(p in _VERSION_READER_ONLY for p in (row.get("inputs") or [])):  # STAMP-VERSION-READER
            return True
        rel = row.get("script")
        if not rel:
            return True
        if rel not in self._verdep:
            try:
                with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                    self._verdep[rel] = bool(_VERSION_WORDS.search(fh.read()))  # STAMP-VERSION-SCRIPT
            except OSError:
                self._verdep[rel] = True
        return self._verdep[rel]

    def _tools_for(self, stored, root):
        """Live versions for the tool names already stored. -> (list|None, why)"""
        probes = self._tools(root)
        live = []
        for item in stored:
            kind, _, _ver = item.partition(":")
            cur = probes.get(kind)
            if not cur:
                return None, "%s version is UNKNOWN" % (kind or "tool")
            live.append("%s:%s" % (kind, cur))
        return live, None

    def _write(self):
        if os.path.basename(self.path) != LEDGER_NAME:
            return False
        if len(self.entries) > _MAX:
            ranked = sorted(self.entries, key=lambda k: (self.entries[k] or {}).get("at") or 0)
            for old in ranked[:len(self.entries) - _MAX]:
                self.entries.pop(old, None)
        disk, why = load(self.path)
        if isinstance(disk, dict) and not why:
            for name, entry in disk.items():
                if name in self.dropped or name in self.entries:
                    continue
                if isinstance(entry, dict) and entry.get("ok") is True and entry.get("gate") == name:
                    self.entries[name] = entry
            try:
                with open(self.path, encoding="utf-8") as fh:
                    dreds = (json.load(fh) or {}).get("reds")
            except Exception:
                dreds = None
            for name, entry in (dreds.items() if isinstance(dreds, dict) else ()):
                if name in self.reds_dropped or name in self.reds or name in self.entries:
                    continue
                if isinstance(entry, dict) and entry.get("ok") is False and entry.get("gate") == name:
                    self.reds[name] = entry
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"v": 2, "proven_sha": self.proven, "entries": self.entries, "reds": self.reds}, fh,
                      sort_keys=True)
        os.replace(tmp, self.path)
        self.why = None
        return True

    def _traced_inputs(self, facts, root):
        """The repo files a traced run read, or why that run cannot be carried. -> (dict|None, why)"""
        tracked = self._tracked(root)
        if tracked is None:
            return None, "git did not list the tracked files"
        dirs = self._tracked_dirs(root, tracked)
        made = set(facts.get("M") or ())
        inputs = set()
        for path in sorted(set(facts.get("R") or ()) | set(facts.get("S") or ()) | set(facts.get("A") or ())):
            if os.path.basename(path) in _SELF or not path:
                continue
            if path == ".git" or path.startswith(".git/"):
                if path in set(facts.get("R") or ()) and path != ".git":
                    return None, "the gate read git's own files (%s)" % path
                continue  # looking for .git is how a script finds its checkout
            if path in tracked or path in dirs:
                inputs.add(path)
                continue
            if path in made or path in _KEYED_CACHES:
                continue
            full = os.path.join(root, path)
            if not os.path.lexists(full):
                inputs.add(path)  # an absent file it looked for: adding it is a change
                continue
            if os.path.isdir(full):
                continue
            ignored = _git(root, ["check-ignore", "-q", "--", path])
            if ignored is not None and ignored.returncode == 0:  # LEDGER-IGNORED-READ
                return None, "the gate read %s, which git ignores, so no diff can say it moved" % path
            inputs.add(path)
        listed = set()
        snaps = {}
        for path in sorted(facts.get("L") or ()):
            if path in dirs or path == "":
                listed.add(path)
                continue
            if path in made or not os.path.isdir(os.path.join(root, path)):
                continue  # a folder this run made, or one it removed again
            snap = listing_snap(root, path)
            if snap is None:
                return None, "the gate listed %s, which holds no tracked file, so no diff can say it moved" % path
            snaps[path] = snap  # LEDGER-LISTING-SNAP
        names = set(facts.get("I") or ())
        if names:
            # an imported name is its tracked source, however the import found it (a .pyc, a child)
            inputs.update(p for p in tracked if _module_stem(p) in names)  # LEDGER-TRACE-IMPORT-SOURCE
        if facts.get("G"):
            inputs.update(p for p in tracked if os.path.basename(p) == ".gitignore")
            listed.add("")
        return {"inputs": inputs, "listed": listed, "snaps": snaps,
                "imports": set(facts.get("I") or ())}, None

    def _tracked_dirs(self, root, tracked):
        if getattr(self, "_dirs_root", None) != root:
            dirs = set()
            for path in tracked:
                dirs.update(_ancestors(path))
            self._dirs_memo = dirs
            self._dirs_root = root
        return self._dirs_memo

    def record(self, gate, ok, trace=None):
        """Store a PASS. A FAIL deletes that gate and is never written. -> bool (stored)

        `trace` is the file gate_trace/sitecustomize.py wrote during the passing run, or its
        read_trace() facts. Without one the reads are UNKNOWN and nothing is stored."""
        self.last_why = None
        if reuse_closed() or ci_blocks():
            return False
        name = str(getattr(gate, "name", "") or "")
        root = self._root_of([gate])
        try:
            row = self._store_decl(gate, root)  # LEDGER-RECORD-FRESH
        except Exception as exc:
            self.last_why = "its inputs could not be derived (%s)" % type(exc).__name__
            return False
        why = (row or {}).get("why")
        red = ok is not True
        if red and name:
            self._drop(name)  # LEDGER-NO-FAIL: a FAIL never stays a PASS row
        if why or not isinstance((row or {}).get("inputs"), list):
            if ok is True:
                self.last_why = why or "its inputs are UNKNOWN"  # LEDGER-SAY-WHY
            if name:
                self._drop(name)
                self._drop_red(name)
            return False
        parts, pwhy = self._tool_parts(set(row.get("kinds") or []), root)
        if pwhy or not parts:
            self.last_why = pwhy or "the tool versions could not be read"
            if name:
                self._drop(name)
                self._drop_red(name)
            return False
        if not trace:
            facts, twhy = None, "no trace of what the gate read"  # LEDGER-NEEDS-TRACE
        elif isinstance(trace, dict):
            facts, twhy = trace, None
        else:
            facts, twhy = read_trace(trace)
        traced = None
        if facts is not None:
            traced, twhy = self._traced_inputs(facts, root)
        if traced is None:
            self.last_why = twhy or "no trace of what the gate read"
            if name:
                self._drop(name)
                self._drop_red(name)
            return False
        inputs = set(row["inputs"]) | traced["inputs"]  # LEDGER-TRACE-READ
        # a fresh status, plus the one taken when the run began: a file edited and put back
        # while the gate ran is in one of the two
        start = self._work[0] if (self._work is not None and self._work_root == root) else None
        dirty, churn, dwhy = self._status(root)
        untracked = set(getattr(self, "_status_untracked", ()) or ())
        if dirty is not None and start is not None:
            dirty = dirty | start
            churn = churn | set(getattr(self, "_work_churn", ()) or ())
            untracked |= set(getattr(self, "_work_untracked", ()) or ())
        hit = None if dirty is None else first_hit(
            inputs, traced["listed"], traced["imports"], dirty, churn)
        if dirty is None or hit:  # LEDGER-DIRTY-RECORD
            self.last_why = ("proved on uncommitted %s, not on the commit" % hit) if hit else (
                dwhy or "the worktree cannot be read")
            if name:
                self._drop(name)
                self._drop_red(name)
            return False
        sha = head_sha(root)
        if not sha:
            self.last_why = "HEAD could not be read"
            return False
        self._ensure()
        if self.entries is None:
            self.entries = {}
        row_out = {
            "ok": not red,
            "gate": name,
            "sha": sha,
            "at": int(time.time() * 1000),
            "def": self._definition(gate, root),
            "tools": list(parts),
            "traced": True,
            "inputs": sorted(inputs),
            "listed": sorted(traced["listed"]),
            "imports": sorted(traced["imports"]),
            "untracked": sorted(p for p in untracked
                                if covered(traced["listed"], traced["imports"], p)),
            "snaps": dict(traced.get("snaps") or {}),
        }
        if red:  # LEDGER-RED-STORE: kept in its own map, so lookup() can never carry it as a pass
            row_out["red"] = True
            self.reds[name] = row_out
            self.reds_dropped.discard(name)
            self._write()
            return False
        self.dropped.discard(name)
        self.proven = sha
        self.entries[name] = row_out
        self._drop_red(name, write=False)
        self._write()
        return True

    def _drop_red(self, name, write=True):
        self._ensure()
        if name in self.reds or write is False:
            self.reds.pop(name, None)
            self.reds_dropped.add(name)
            if write:
                try:
                    self._write()
                except Exception:
                    pass

    def _drop(self, name):
        self._ensure()
        if not isinstance(self.entries, dict):
            self.entries = {}
        self.entries.pop(name, None)  # LEDGER-DROP-FAIL
        self.dropped.add(name)
        if os.path.exists(self.path) or self.entries:
            try:
                self._write()
            except Exception:
                pass


def _gate(name):
    import run_gates
    for gate in run_gates.GATES:
        if gate.name == name:
            return gate
    return None


def main(argv):
    import argparse
    parser = argparse.ArgumentParser(description="carry or record one gate's PASS")
    parser.add_argument("--carry", metavar="GATE")
    parser.add_argument("--record", metavar="GATE")
    parser.add_argument("--trace", metavar="FILE", help="with --record: what the passing run read")
    parser.add_argument("--trace-env", metavar="FILE",
                        help="print the shell exports that arm the trace into FILE (the pre-push hook)")
    parser.add_argument("--trace-path", action="store_true", help="make and print a fresh trace file")
    args = parser.parse_args(argv[1:])
    if args.trace_path:
        print(trace_path())
        return 0
    if args.trace_env:
        import shlex
        armed = trace_env(os.environ, REPO, args.trace_env)
        for key in sorted(armed):
            if os.environ.get(key) != armed[key]:
                print("export %s=%s" % (key, shlex.quote(armed[key])))  # LEDGER-HOOK-TRACE
        return 0
    if bool(args.carry) == bool(args.record):
        print("ledger: name one of --carry or --record")
        return 2
    name = args.carry or args.record
    if not _SAFE.match(name or ""):
        print("ledger: %s is not a gate name" % name)
        return 1
    gate = _gate(name)
    if gate is None:
        print("ledger: %s is not a registered gate — it runs" % name)
        return 1
    led = Ledger()
    if args.carry:
        entry, why = led.lookup(gate)
        if entry is None:
            print("ledger: %s runs — %s" % (name, why))
            return 1
        print(entry["line"])
        return 0
    ok, why = verdict_allows(name, REPO)
    if not ok:
        print("ledger: %s was not recorded — %s" % (name, why))
        return 1
    if led.record(gate, True, trace=args.trace):
        print("ledger: %s PASS recorded" % name)
        return 0
    print("ledger: %s was not recorded (%s) — the next run will execute it"
          % (name, led.last_why or "its inputs are UNKNOWN"))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
