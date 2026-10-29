"""WHICH SWALLOWED EXCEPTIONS CAN PUT A CALM NUMBER ON HIS SCREEN.

Konyo, 2026-09-01, on a rule that had called a large finding "noise": "thats not logical.. it
makes a small problem bigger though... and the 238... fix them??" Then: "focus on the 537 here".

He is right that "too many to act on" is not a reason to stop looking. But 537 is also not a
to-do list — most of them are correct. `try: tab.close() except: pass` SHOULD swallow; a teardown
that takes a run down is a worse bug than the one it reports.

So this file exists to turn one big number into a ranked one, repeatably, and to keep the
unscoped total on the record beside the ranked subset. It is a MEASUREMENT, not a linter: it
prints, it never edits, and it has no opinion about any single site.

THE RANKING QUESTION, and it is the only one that matters:

    does this swallow let a number HE ACTS ON keep a calm face?

The shape behind most of this session's scars is a failed read that silently yields {} or 0, so a
screen prints a tidy figure that actually means "nobody could ask". That is worse than a crash,
because a crash gets fixed. [[unknown-stays-unknown]]

    RANK 1  the except body RETURNS or ASSIGNS a falsy default ({} , 0, [], "", None, False)
            after a read/parse/fetch. This is the class. The caller cannot tell the difference
            between "measured zero" and "could not ask".
    RANK 2  a read/parse/fetch is swallowed with a bare `pass`, and the surrounding function has
            a fallible return path. Suspicious; needs a human to say which.
    RANK 3  something else fallible is swallowed. Look eventually.
    OK      the try block only tears something down, or the except body re-raises, logs, or sets
            an explicit UNKNOWN marker.

⚠ THIS TOOL CANNOT TELL YOU A SITE IS WRONG. A rank is a place in a queue, not a verdict — every
fix still needs someone to read the site and decide. Reporting a rank as a defect would make this
the very thing it was written to stop: a confident number nobody measured.
"""

import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# Things whose failure means a FACT was not obtained.
READS = ("open", "load", "loads", "read", "get", "post", "urlopen", "request", "fetch",
         "json", "loadtxt", "execute", "fetchone", "fetchall", "check_output", "run",
         "communicate", "listdir", "glob", "stat", "getmtime", "getsize", "exists")
# Things whose failure means a cleanup did not happen — swallowing is correct.
TEARDOWNS = ("close", "quit", "kill", "terminate", "unlink", "remove", "rmtree", "shutdown",
             "join", "cleanup", "destroy", "release", "disconnect", "stop")

FALSY = ("{}", "[]", "0", "0.0", "''", '""', "None", "False", "()")


def _calls(node):
    """Every dotted call name inside a node, lowercased."""
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute):
                out.append(f.attr.lower())
            elif isinstance(f, ast.Name):
                out.append(f.id.lower())
    return out


def _is_falsy_const(node):
    if isinstance(node, ast.Constant):
        return not node.value or node.value == 0
    if isinstance(node, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
        return not (getattr(node, "keys", None) or getattr(node, "elts", None))
    return False


def _hands_back(handler):
    """EXACTLY what the except body hands back, because the difference decides everything.

    ⚠ THE FIRST CUT OF THIS TOOL GOT THIS WRONG AND WOULD HAVE PRODUCED A 262-ITEM QUEUE THAT WAS
    MOSTLY FINE. It treated every falsy default as the lying shape. But `return None` is usually
    the HONEST answer — None IS "I could not tell", and a caller that checks `is None` gets the
    truth. Measured over this tree: of 262 sites, 168 hand back None or False and 94 hand back
    something that reads as DATA. Only the 94 are the class where "could not ask" wears the
    costume of "measured zero". Ranking them together would have buried the real ones under
    correct code — the exact way a real finding gets ignored. [[unknown-stays-unknown]]
    """
    for st in handler.body:
        v = st.value if isinstance(st, (ast.Return, ast.Assign)) else None
        if isinstance(st, ast.Return) and v is None:
            return "None"
        if v is None:
            continue
        if isinstance(v, ast.Constant):
            if v.value is None:  return "None"
            if v.value is False: return "False"
            if v.value == 0:     return "ZERO"
            if v.value == "":    return "EMPTY-STR"
        if isinstance(v, ast.Dict) and not v.keys:            return "EMPTY-DICT"
        if isinstance(v, (ast.List, ast.Set)) and not v.elts: return "EMPTY-LIST"
        if isinstance(v, ast.Tuple) and v.elts:
            # ⚠ A TUPLE OF NONES IS THE HONEST UNKNOWN, NOT AN EMPTY CONTAINER. Caught by hand-
            # reading a sample: control_app.py:21899 does `_fw_state, _fw_say = None, None` and
            # this graded it as a lying shape. Same rule as scalar None — say so, do not lump it
            # in with `return {}`.
            if all(isinstance(e, ast.Constant) and e.value is None for e in v.elts):
                return "None"
            if all(_is_falsy_const(e) for e in v.elts):
                return "EMPTY-TUPLE"
    return "other"


# The shapes that a caller cannot distinguish from a real measurement.
LIES_AS_DATA = ("ZERO", "EMPTY-DICT", "EMPTY-LIST", "EMPTY-STR", "EMPTY-TUPLE")


def _body_shape(handler):
    """What the except body DOES. -> ('pass'|'return-falsy'|'assign-falsy'|'speaks'|'other')"""
    body = handler.body
    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return "pass"
    for st in body:
        if isinstance(st, ast.Raise):
            return "speaks"
        # a print / log / a call carrying the word warn|error|unknown counts as speaking up
        for c in _calls(st):
            if c in ("print", "warning", "warn", "error", "exception", "critical", "log"):
                return "speaks"
    for st in body:
        if isinstance(st, ast.Return) and st.value is not None and _is_falsy_const(st.value):
            return "return-falsy"
        if isinstance(st, ast.Return) and st.value is None:
            return "return-falsy"
        if isinstance(st, ast.Assign) and _is_falsy_const(st.value):
            return "assign-falsy"
        if isinstance(st, ast.Assign) and isinstance(st.value, ast.Tuple) \
                and all(_is_falsy_const(e) for e in st.value.elts):
            return "assign-falsy"
    return "other"


def _checked_right_after(handler):
    """Does the code immediately after this handler TEST the name it just defaulted?

    Only looks at the handler's own assigned names and the statements that follow it in the same
    block, because that is the whole extent of what a file-local pass can honestly establish.
    """
    names = set()
    for st in handler.body:
        if isinstance(st, ast.Assign):
            for t in st.targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        names.add(n.id)
    if not names:
        return False
    parent = getattr(handler, "_next_stmts", None) or []
    for st in parent[:3]:
        for n in ast.walk(st):
            if isinstance(n, ast.Name) and n.id in names:
                if isinstance(st, (ast.If, ast.While, ast.Assert, ast.Return)):
                    return True
    return False


#: exception classes that mean THERE IS NOTHING TO READ, as opposed to THE READ FAILED. Absence is
#: a state of the world a caller can act on; a failure is not. Kept deliberately to the one class
#: that carries no other meaning — PermissionError, IsADirectoryError and the rest are failures.
ABSENCE_ONLY = frozenset(("FileNotFoundError",))


def _catches_absence_only(handler):
    """Does this `except` clause catch absence and NOTHING wider? -> bool

    ⚠ A bare `except:` and `except Exception:` both answer False, and so does any tuple carrying
    one wider name. `IOError` is the case this exists to refuse: it IS `OSError` in Python 3, so
    it reads as absence and catches every failure there is.
    """
    t = getattr(handler, "type", None)
    if isinstance(t, ast.Name):
        names = {t.id}
    elif isinstance(t, ast.Tuple):
        names = {x.id for x in t.elts if isinstance(x, ast.Name)}
        if len(names) != len(t.elts):
            return False                     # something that is not a bare name — refuse to judge
    else:
        return False                         # bare except, or an expression we cannot read
    return bool(names) and names <= ABSENCE_ONLY


def _rank(try_node, handler):
    calls = _calls(ast.Module(body=list(try_node.body), type_ignores=[]))
    reads = [c for c in calls if c in READS]
    tears = [c for c in calls if c in TEARDOWNS]
    shape = _body_shape(handler)

    if shape == "speaks":
        return 0, "the except body reports it"
    if tears and not reads:
        return 0, "teardown only — swallowing is correct here"
    if reads and shape in ("return-falsy", "assign-falsy"):
        hb = _hands_back(handler)
        # ⚠ AND THE ONE THING THAT ACTUALLY DECIDES IT: is the default USED AS A SENTINEL —
        # assigned and then immediately tested — or handed to a caller as if it were data?
        # Hand-reading a 1-in-8 sample of the first 94 found roughly half were not defects at
        # all, and this was the most common reason: `rt = 0` followed by `if not rt: continue`
        # (control_app.py:9824) is a checked sentinel, not a lie. A static pass cannot see a
        # CALLER's contract, but it can see this. What it still cannot judge is named in the
        # module docstring, and the count is reported as a SHAPE, never as a defect total.
        if shape == "assign-falsy" and _checked_right_after(handler):
            return 2, "a failed %s assigns %s and the very next statements TEST it — a checked " \
                      "sentinel, not a claim" % (reads[0], hb)
        # ⚠⚠ v3355 — AN ABSENCE IS A MEASUREMENT; ONLY A FAILURE IS A LIE. This rule asked what
        # the handler RETURNS and never what it CATCHES, so `except FileNotFoundError: return {}`
        # ranked identically to `except OSError: return {}` — and those are opposite facts. A file
        # that has never been written and a store written as {} mean the SAME thing to a caller:
        # nothing recorded. A file that exists and cannot be opened means something else entirely.
        #
        # ⚠ IT COST A WHOLE FIX. v3355 repaired three loaders from `except IOError` (which is
        # `except OSError`, so it caught PermissionError on an existing store and returned {}) to
        # `except FileNotFoundError`. The defect was real, the fix was real — and this count did
        # not move, because the ranker could not tell the two apart. A ratchet whose number
        # survives the repair of the thing it flagged teaches its reader to re-baseline.
        #
        # ⚠ NARROW ON PURPOSE: a BARE except, `except Exception` or any tuple containing something
        # wider gets NO pass. Only a clause that catches absence and nothing else.
        # MEASURED: 6 of 76 rank-1 sites qualify, so rank 1 goes 76 -> 70 and the baseline moves
        # down with it in this same commit. [[unknown-stays-unknown]]
        if hb in LIES_AS_DATA and _catches_absence_only(handler):
            return 2, "a failed %s becomes %s, but the handler catches ABSENCE ONLY — a store " \
                      "that was never written and one written empty are the same fact" \
                      % (reads[0], hb)
        if hb in LIES_AS_DATA:
            return 1, "a failed %s becomes %s — 'could not ask' is indistinguishable from a real " \
                      "measurement" % (reads[0], hb)
        # None/False after a failed read is the honest unknown. Still worth an eye — a CALLER that
        # does `x or 0` re-creates the lie one frame up — but it is not the same defect.
        return 2, "a failed %s returns %s (honest unknown; check the CALLER does not coerce it)" \
                  % (reads[0], hb)
    if reads and shape == "pass":
        return 2, "a failed %s is swallowed silently" % reads[0]
    if reads:
        return 2, "a failed %s is swallowed" % reads[0]
    return 3, "something fallible is swallowed"


def scan(root=None):
    root = root or REPO
    rows, unreadable = [], []
    state = {"skippedDirs": []}
    for dp, dns, fns in os.walk(root):
        # ⚠ `backups/` IS A RESTORE SNAPSHOT, NOT SHIPPING CODE — a frozen copy of tv/ from
        # 2026-07-16. Counting it would put four sites at the top of the queue that no running
        # process can reach. It is SKIPPED AND COUNTED, never silently dropped: a census that
        # quietly narrows its own scope is the thing this file exists to stop. [[no-silent-caps]]
        # `.claude/worktrees` are throwaway agent worktrees; `.snapshots` and `backups` are
        # frozen restore copies. None of them is code any process can reach, and counting them
        # would put sites at the top of a queue nobody can act on. All are SKIPPED AND NAMED.
        skipped = [d for d in dns if d in ("backups", ".snapshots", "worktrees")]
        for d in skipped:
            state["skippedDirs"].append(os.path.relpath(os.path.join(dp, d), root))
        dns[:] = [d for d in dns if d not in (".git", "node_modules", "__pycache__",
                                              ".render_shots", "frames", "backups",
                                              ".snapshots", "worktrees", ".venv", "venv")]
        for fn in sorted(fns):
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dp, fn)
            got, bad = _file_rows(p, root)
            if bad is not None:
                # ⚠ A FILE THIS TOOL COULD NOT PARSE IS NOT A FILE WITH NO SWALLOWS. Naming it is
                # the whole difference between a census and a comforting number.
                unreadable.append(bad)
                continue
            rows.extend(dict(r) for r in got)
    return {"rows": rows, "unreadable": unreadable, "root": root,
            "skippedDirs": sorted(set(state["skippedDirs"]))}


#: #172 (2026-10-27) - ONE PARSE PER FILE, NOT ONE PER TICK. The console's doctor runs this census on every eagle tick
#: (every 10 min) and it ast.parses every .py in the repo, _archive included - about 1,500 files each time, in the
#: console's own process, whose freed parse arenas stay resident (his ALT's console holds 1.28 GB private). A file's
#: rows depend on its bytes and its path alone, so they are kept per (path, root) and re-derived only when its size or
#: mtime moved. An unreadable file is not cached: it is asked again next time and stays NAMED as unreadable.
_FILE_ROWS = {}


def _file_rows(p, root):
    """-> (rows, None) | (None, (relpath, why)). Kept per file until its size or mtime moves."""
    rel = os.path.relpath(p, root)
    try:
        st = os.stat(p)
        key = (st.st_mtime_ns, int(st.st_size))
    except OSError as e:
        return None, (rel, str(e)[:60])
    hit = _FILE_ROWS.get((p, root))
    if hit is not None and hit[0] == key:
        return hit[1], None
    # #172 phase C - a console reads the rows a short-lived child derived for this file at this stamp (audit_child); a law,
    # the gate, CI, a CLI and the child itself parse here as before
    try:
        import audit_child as _ac
        got = _ac.swallow_rows_for(p, root, key)
    except Exception:
        got = None
    if got is not None:
        rows = tuple(dict(r) for r in got)
        _FILE_ROWS[(p, root)] = (key, rows)
        return rows, None
    try:
        src = io.open(p, encoding="utf-8").read()
        tree = ast.parse(src)
    except Exception as e:
        return None, (rel, str(e)[:60])
    # give each Try the statements that FOLLOW it in its own block, so a defaulted
    # name that is tested two lines later can be recognised as a sentinel
    for parent in ast.walk(tree):
        body = getattr(parent, "body", None)
        if not isinstance(body, list):
            continue
        for i, st_ in enumerate(body):
            if isinstance(st_, ast.Try):
                for h in st_.handlers:
                    h._next_stmts = body[i + 1:i + 4]
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for h in node.handlers:
            r, why = _rank(node, h)
            out.append({
                "file": rel,
                "line": h.lineno,
                "rank": r,
                "why": why,
                "shape": _body_shape(h),
            })
    _FILE_ROWS[(p, root)] = (key, tuple(out))
    return tuple(out), None


# ══ THE RATCHET ══════════════════════════════════════════════════════════════════════════════
# Konyo, 2026-09-01: "i want it a public and not local.. why do we have github? like what can be
# unified and synced here for this not to happen future wise" — then "do this across all repos".
#
# A census that only runs when someone remembers to type it protects nothing. This half makes the
# number a RATCHET: it may go DOWN freely, and any increase fails. That is the only shape that
# answers "so it does not happen again", because it starts protecting immediately instead of
# waiting for someone to fix the standing count first.
#
# ⚠ IT RATCHETS RANK 1 ONLY. Ranks 2 and 3 are recorded for the trend and never fail a build —
# they are too broad to act on, and a gate that is red forever has stopped carrying information
# in exactly the same way as one that is green forever.
# [[feedback-blind-fixture-green-gate]] [[regression-guard]]
BASELINE_REL = os.path.join("baseline", "swallow_baseline.json")


def _baseline_path(root=None):
    return os.path.join(root or REPO, BASELINE_REL)


def _rank1_by_file(out):
    """RANK 1 sites per file. -> {relpath: count}

    ⚠⚠ REG-579 — THE RATCHET COUNTED AND COULD NOT NAME. The baseline stored ONE integer, so a
    red said *"4 NEW site(s)"* and nothing else: no file, no direction, no way to tell a real
    regression from a refactor that moved handlers around. The only cheap way to clear it was
    `--write-baseline`, which **adopts the new sites as the new normal** — the identical shape
    REG-568 found in the render coverage ratchet one file over, where a bless could write the
    floor DOWN. A ratchet whose red is unactionable trains its reader to re-baseline.

    ⚠ PER FILE, NOT PER LINE, ON PURPOSE. A line number moves whenever anything above it is
    edited, so a line-keyed baseline would report new sites on every ordinary commit and be
    re-baselined into meaninglessness within a week. The file is the smallest identity that
    survives an edit, and it is enough to send a reader to the right place.
    """
    by = {}
    for r in out["rows"]:
        if r["rank"] == 1:
            by[r["file"]] = by.get(r["file"], 0) + 1
    return by


def _counts(out):
    b = {0: 0, 1: 0, 2: 0, 3: 0}
    for r in out["rows"]:
        b[r["rank"]] += 1
    return {"rank1": b[1], "rank2": b[2], "rank3": b[3], "ok": b[0],
            "handlers": len(out["rows"]), "unparsed": len(out["unreadable"])}


def write_baseline(root=None):
    import json
    _scanned = scan(root)
    c = _counts(_scanned)
    p = _baseline_path(root)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump({"_why": "RANK 1 is a ratchet: it may fall, never rise. Regenerate with "
                           "swallow_census.py --write-baseline after a DELIBERATE reduction, and "
                           "name the sites you fixed in the commit.",
                   "counts": c,
                   "rank1ByFile": _rank1_by_file(_scanned)}, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote %s" % p)
    print("  rank1=%(rank1)d rank2=%(rank2)d rank3=%(rank3)d ok=%(ok)d handlers=%(handlers)d" % c)
    return 0


def check(root=None):
    """Fail ONLY when rank 1 grew. -> exit code."""
    import json
    p = _baseline_path(root)
    _scan_now = scan(root)
    now = _counts(_scan_now)
    try:
        with io.open(p, encoding="utf-8") as fh:
            was = (json.load(fh) or {}).get("counts") or {}
    except FileNotFoundError:
        # ⚠ NO BASELINE IS NOT A PASS. An unconfigured gate that exits 0 is indistinguishable
        # from a clean tree, which is the whole failure this file exists to name.
        print("🔴 no baseline at %s — this gate is UNCONFIGURED, which is not the same as clean."
              % p)
        print("   run:  python3 tv/swallow_census.py --write-baseline")
        return 1
    except Exception as e:
        print("🔴 the baseline at %s would not parse (%s) — refusing to grade against it." % (p, e))
        return 1

    # ⚠ v2389 — A MALFORMED BASELINE IS NOT A BASELINE OF ZERO. `int(was.get("rank1", 0))` turned
    # a missing or non-integer key into 0, so a perfectly healthy tree reported "74 NEW sites" and
    # the message pointed at the code instead of at the file. Found by a cross-family read of the
    # v2387 gate. [[unknown-stays-unknown]]
    if not isinstance(was.get("rank1"), int):
        print("🔴 the baseline at %s has no integer counts.rank1 (%r) — it is MALFORMED, not a "
              "count of zero. Refusing to grade against it." % (p, was.get("rank1")))
        print("   regenerate:  python3 tv/swallow_census.py --write-baseline")
        return 1

    b_now, b_was = now["rank1"], was["rank1"]
    _now_by = _rank1_by_file(_scan_now)
    _was_by = (json.load(io.open(p, encoding="utf-8")) or {}).get("rank1ByFile")
    u_now, u_was = now.get("unparsed", 0), int(was.get("unparsed", 0) or 0)
    print("swallow ratchet — RANK 1 (a failed read handed back as DATA)")
    print("   baseline %d   now %d" % (b_was, b_now))

    # ⚠ v2389 — AN UNPARSEABLE FILE HIDES ITS OWN SWALLOWS. The census records files it cannot
    # parse, and this used to only PRINT about them: rank1 stayed flat while the new handlers went
    # uncounted, so adding a broken file was a way to smuggle sites past the gate. Unparsed
    # ratchets too. A file that will not parse is also, separately, a file that will not run.
    if u_now > u_was:
        print()
        print("🔴 %d file(s) newly UNPARSEABLE (baseline %d, now %d). Their handlers are in "
              "NEITHER number, so this gate cannot see them at all — an uncounted site is not a "
              "clean one." % (u_now - u_was, u_was, u_now))
        return 1
    if u_now:
        print("   (%d file(s) unparseable, same as the baseline — still uncounted)" % u_now)

    if b_now > b_was:
        print()
        print("🔴 %d NEW site(s) where a failed read becomes DATA (0 / {} / [] / '')."
              % (b_now - b_was))
        print("   A caller cannot tell that from a real measurement. Either make the failure")
        print("   report UNKNOWN, or — if the caller genuinely treats the default as failure —")
        print("   say so in a comment AT THE SITE and lower the baseline deliberately.")
        # ⚠⚠ REG-579 — SAY WHERE. Until now this printed a number and stopped, so the only cheap
        # way to clear a red was to re-baseline, which adopts the new sites. Name the files.
        if not isinstance(_was_by, dict):
            print()
            print("   ⚠ WHICH FILES ROSE IS UNKNOWN — this baseline predates the per-file map and")
            print("     records only a total. That is NOT 'no file rose': nobody can tell. Run")
            print("     --write-baseline in a commit that states what changed, and the next red")
            print("     will name the files.")
        else:
            rose = sorted(((f, n, int(_was_by.get(f, 0)))
                           for f, n in _now_by.items() if n > int(_was_by.get(f, 0))),
                          key=lambda t: (t[2] - t[1], t[0]))
            fell = sorted(((f, int(_was_by.get(f, 0)), _now_by.get(f, 0))
                           for f in _was_by if _now_by.get(f, 0) < int(_was_by.get(f, 0))))
            print()
            if rose:
                print("   WHERE IT ROSE:")
                for f, n, w in rose:
                    print("     %-44s %d -> %d  (+%d)" % (f, w, n, n - w))
            else:
                print("   ⚠ NO FILE ROSE, yet the total did. That means sites moved between files,")
                print("     or a file appeared that the baseline never had — read the two lists.")
            if fell:
                print("   and it FELL in %d file(s), so the total understates both movements:"
                      % len(fell))
                for f, w, n in fell[:8]:
                    print("     %-44s %d -> %d" % (f, w, n))
        return 1

    # ⚠ v2389 — A DROP FAILS TOO, AND THAT IS THE POINT. The count can fall with nobody fixing
    # anything: delete a file, move one under a skipped directory, and the gate used to print
    # "down N, please lower the baseline" and PASS. Nothing enforced the lowering, so slack
    # accumulated silently and a later real regression fitted inside it unnoticed.
    # An EXACT-MATCH baseline has no slack to hide in. The cost is one command in the same commit,
    # which is also the moment to say in the message WHICH sites went and why each was real.
    if b_now < b_was:
        print()
        print("🟡 down %d — good, and the baseline must move with it or the gap becomes slack "
              "a future regression can hide inside." % (b_was - b_now))
        print("   run, in this same commit:  python3 tv/swallow_census.py --write-baseline")
        return 1
    print("✅ held.")
    return 0


def main(argv=None):
    try:
        import console_safe
        console_safe.enable()
    except Exception:
        pass
    argv = list(argv or [])
    # the two CI doors, before any printing
    _root = None
    for i, a in enumerate(argv):
        if a == "--root" and i + 1 < len(argv):
            _root = argv[i + 1]
    if "--write-baseline" in argv:
        return write_baseline(_root)
    if "--check" in argv:
        return check(_root)
    out = scan(_root)
    rows = out["rows"]
    by = {}
    for r in rows:
        by.setdefault(r["rank"], []).append(r)

    print("\nSWALLOWED EXCEPTIONS in %s" % out["root"])
    print("  %d handlers examined across the tree" % len(rows))
    if out.get("skippedDirs"):
        print("  (skipped, and not represented above: %s — a restore snapshot, not shipping code)"
              % ", ".join(out["skippedDirs"]))
    if out["unreadable"]:
        # never let an unparsed file read as a clean one
        print("  ⚠ %d file(s) COULD NOT BE PARSED and are not represented below:"
              % len(out["unreadable"]))
        for f, e in out["unreadable"][:5]:
            print("       %s — %s" % (f, e))
    print()
    LABEL = {1: "RANK 1  a failed read becomes DATA (0 / {} / [] / '')  ← the class that lies",
             2: "RANK 2  a failed read is swallowed silently",
             3: "RANK 3  something else fallible is swallowed",
             0: "OK      teardown, or the body speaks up"}
    for r in (1, 2, 3, 0):
        print("  %-64s %4d" % (LABEL[r], len(by.get(r) or [])))
    # ⚠ THE LINE THAT STOPS THIS NUMBER BEING QUOTED AS A DEFECT COUNT. It has already been
    # wrong three times in one day — 537 (a grep that missed `except: return {}`), 262 (every
    # falsy default called a lie, including the honest `return None`), 94 (a tuple of Nones
    # graded as an empty container, and checked sentinels graded as claims). Each correction
    # came from READING SITES, never from the tool. [[unknown-stays-unknown]]
    print()
    print("  ⚠ RANK 1 IS A SHAPE, NOT A DEFECT COUNT. A hand-read of a 1-in-8 sample graded")
    print("    2 solid / 4 mild / 6 not-defects out of 12 — most often because the CALLER")
    print("    treats the default as failure, which no file-local pass can see. Read the site.")

    top = sorted(by.get(1) or [], key=lambda r: (r["file"], r["line"]))
    if top:
        n = 25 if "--all" not in argv else len(top)
        print("\n  RANK 1 sites%s:" % ("" if n >= len(top) else " (first %d of %d — --all for the rest)"
                                       % (n, len(top))))
        for r in top[:n]:
            print("     %-38s :%-6d %s" % (r["file"], r["line"], r["why"]))
        if n < len(top):
            # no silent caps: say what was dropped
            print("     … %d more not printed" % (len(top) - n))
    print()
    return 0


RED_PROOF = [
    {
        'why': 'The gate (tv/swallow_census.py --check) ratchets RANK 1 — a failed read handed back to a caller as DATA (0 / {} / [] / \'\'). tv/human_eyes_ledger.py is the purest instance of the honest shape it protects: all three of its file-IO handlers return None ("None propagates rather than flattening to []", its own docstring, line ~138), so a caller can tell "could not ask" from "no briefs". Turning those three `return None` into `return []` converts three honest unknowns into three empty containers a caller cannot distinguish from a real measurement — exactly the class the ratchet exists to stop — and the count rises 74 -> 77. The anchor is real code, not prose: line 53 mentions the literal string `except OSError: return []` in a comment and does NOT match, because the anchor pins the two-line, 8-space-indented handler body. It is not a shared constant and not a derived-set union — the census recomputes rank 1 from the AST while the baseline stays fixed on disk, so only the tampered side moves.  MEASURED: untampered GREEN before: `perl -e \'alarm 200; exec @ARGV\' python3 tv/swallow_census.py --ch; tampered (all 3) All 3 occurrences replaced (counted first: MATCHES: 3; tampered file re-parsed w; reddened law the rank-1 GROWTH branch of swallow_census.check() — `if b_now > b_was; ALONE This gate is a SCRIPT, not a unittest suite, so "alone" = a fresh process invoking exactly that one .',
        'file': 'human_eyes_ledger.py',
        'find': '    except OSError:\n        return None',
        'replace': '    except OSError:\n        return []',
        'matches': 3,
    },
]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
